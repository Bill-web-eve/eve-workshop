"""Detached updater: reverify, wait for both processes, back up data, swap app.

Only launch_helper accepts a ticket ID from the native shell. Paths and commands
are derived from our own packaged executable; no executable URL is UI-controlled.
"""
from __future__ import annotations
import ast
from contextlib import closing
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
import zipfile
from . import __version__
from .updates import UpdateError, asset_valid, atomic_json, installation, strict_json, validate_installation, verify_document, version


def ticket_folder(profile, ticket):
    if not isinstance(ticket, str) or not re.fullmatch('[a-f0-9]{32}', ticket): raise UpdateError('invalid_update')
    folder = Path(profile)/'updates'/ticket
    if folder.is_symlink() or not folder.is_dir(): raise UpdateError('invalid_update')
    return folder


def read_receipt(folder, key=None):
    folder = Path(folder);receipt = strict_json((folder/'receipt.json').read_bytes())
    payload = verify_document(receipt['document'], key)
    if receipt.get('platform') not in payload['assets']: raise UpdateError('invalid_update')
    if version(payload['version']) <= version(receipt['current_version']): raise UpdateError('older_update')
    if type(receipt.get('created')) not in {int,float} or not 0 <= time.time()-receipt['created'] < 24*3600: raise UpdateError('expired_update')
    if type(receipt.get('backend_pid')) is not int or receipt['backend_pid'] <= 0: raise UpdateError('invalid_update')
    asset_valid(folder/'archive.zip', payload['assets'][receipt['platform']])
    return receipt, payload


def extract_archive(archive, destination, platform):
    """Reject aliases/traversal/devices/zip bombs and symlink-parent writes.

Mac framework symlinks are preserved only when every target stays inside the app.
No symlink is created until all regular files have been written.
"""
    root = Path(destination).resolve();root.mkdir(mode=0o700, parents=True, exist_ok=False)
    prefix = 'EVE Muhely.app' if platform == 'macos-arm64' else 'EVE Muhely'
    links = {};entries = {};total = 0;aliases = set()
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if len(infos)>30000: raise UpdateError('unsafe_archive')
        for entry in infos:
            name = entry.filename.rstrip('/');p = PurePosixPath(name)
            if not name or '\\' in name or ':' in name or any(ord(c)<32 for c in name) or p.is_absolute() or any(c in {'','.','..'} for c in name.split('/')) or p.parts[0] != prefix: raise UpdateError('unsafe_archive')
            if platform=='windows-x64':
                reserved={'CON','PRN','AUX','NUL'}|{f'{p}{n}' for p in ['COM','LPT'] for n in range(1,10)}
                if any(part.rstrip(' .')!=part or part.split('.')[0].upper() in reserved for part in p.parts): raise UpdateError('unsafe_archive')
            alias = str(p).casefold()
            if alias in aliases: raise UpdateError('unsafe_archive')
            aliases.add(alias)
            mode = entry.external_attr>>16;kind = stat.S_IFMT(mode)
            if kind not in {0,stat.S_IFREG,stat.S_IFDIR,stat.S_IFLNK} or entry.flag_bits&1: raise UpdateError('unsafe_archive')
            total += entry.file_size
            if total>1024*1024*1024 or entry.file_size>300*1024*1024: raise UpdateError('unsafe_archive')
            entries[p] = entry
            if kind == stat.S_IFLNK:
                if platform != 'macos-arm64' or entry.file_size>4096: raise UpdateError('unsafe_archive')
                target = z.read(entry).decode('utf-8')
                if not target or '\\' in target or ':' in target or '\0' in target or target.startswith('/'): raise UpdateError('unsafe_archive')
                resolved = Path(os.path.abspath(root.joinpath(*p.parts).parent/target))
                if not resolved.is_relative_to(root/prefix): raise UpdateError('unsafe_archive')
                links[p] = target
        for p, entry in entries.items():
            if any(parent in links for parent in p.parents): raise UpdateError('unsafe_archive')
            if p in links: continue
            target = root.joinpath(*p.parts)
            if entry.is_dir(): target.mkdir(mode=0o755, parents=True, exist_ok=True)
            else:
                target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
                with z.open(entry) as source, target.open('xb') as out: shutil.copyfileobj(source, out, 1024*1024)
                target.chmod(((entry.external_attr>>16)&0o755) or 0o644)
        for p, target in links.items():
            path = root.joinpath(*p.parts);path.parent.mkdir(mode=0o755, parents=True, exist_ok=True);path.symlink_to(target)
        for p in links:
            try: resolved = root.joinpath(*p.parts).resolve(strict=True)
            except (OSError, RuntimeError): raise UpdateError('unsafe_archive') from None
            if not resolved.is_relative_to(root/prefix): raise UpdateError('unsafe_archive')
    return root/prefix


def payload_version(root, platform, expected):
    validate_installation(root, platform)
    try:
        if platform == 'macos-arm64':
            info = plistlib.loads((Path(root)/'Contents/Info.plist').read_bytes())
            actual = info.get('CFBundleShortVersionString', info.get('CFBundleVersion'))
        else:
            tree = ast.parse((Path(root)/'app/muhely/__init__.py').read_text())
            actual = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='__version__' for t in n.targets))
        if actual != expected: raise UpdateError('invalid_archive')
    except (OSError, ValueError, StopIteration, SyntaxError): raise UpdateError('invalid_archive') from None


def wait_process(pid, timeout=90):
    if type(pid) is not int or pid <= 0 or pid == os.getpid(): raise UpdateError('invalid_update')
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];api.OpenProcess.restype=wintypes.HANDLE
        api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];api.WaitForSingleObject.restype=wintypes.DWORD
        api.CloseHandle.argtypes=[wintypes.HANDLE]
        handle = api.OpenProcess(0x00100000, False, pid)
        if not handle:
            if ctypes.get_last_error()==87:return
            raise UpdateError('update_process_wait_failed')
        try:
            if api.WaitForSingleObject(handle,int(timeout*1000)) != 0: raise UpdateError('update_close_timeout')
        finally: api.CloseHandle(handle)
    else:
        deadline = time.monotonic()+timeout
        while time.monotonic()<deadline:
            try: os.kill(pid,0)
            except ProcessLookupError: return
            time.sleep(.2)
        raise UpdateError('update_close_timeout')


def backup_database(profile):
    profile = Path(profile);source = profile/'muhely.sqlite3'
    if not source.exists(): return None
    if source.is_symlink(): raise UpdateError('invalid_update')
    directory = profile/'backups';directory.mkdir(mode=0o700, exist_ok=True)
    target = directory/('before-update-'+time.strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(4)+'.sqlite3')
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro', uri=True)) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
    target.chmod(0o600);return target


def replace_application(target, payload, platform):
    """Prepare on the destination filesystem. Failed swaps restore the old app."""
    target, payload = Path(target), Path(payload);validate_installation(target, platform)
    token = secrets.token_hex(8)
    staged = target.with_name('.'+target.name+'.new-'+token)
    previous = target.with_name('.'+target.name+'.previous-'+token)
    try:
        shutil.copytree(payload, staged, symlinks=True)
        os.replace(target, previous)
        try: os.replace(staged, target)
        except Exception:
            os.replace(previous, target);raise
        return previous
    finally:
        if staged.exists(): shutil.rmtree(staged)


def launch_helper(profile, ticket, origin, parent_pid, executable=None):
    root, platform = installation(executable=executable)
    folder = ticket_folder(profile, ticket);receipt, payload = read_receipt(folder)
    if Path(receipt['target']).resolve() != root or receipt['platform'] != platform or receipt['current_version'] != __version__: raise UpdateError('invalid_update')
    if Path(profile).resolve().is_relative_to(root): raise UpdateError('manual_install_required')
    if type(parent_pid) is not int or parent_pid<=0: raise UpdateError('invalid_update')
    from urllib.parse import urlsplit
    url=urlsplit(origin)
    if url.scheme!='http' or url.hostname!='127.0.0.1' or url.path or url.query or url.username or url.password or not url.port: raise UpdateError('invalid_update')
    helper=folder/'helper'
    if helper.exists(): raise UpdateError('update_already_started')
    try:
        # Run from a private COPY: Windows locks the executing Python/DLL files.
        if platform=='macos-arm64':
            shutil.copytree(root, helper/'EVE Muhely.app', symlinks=True)
            command=[str(helper/'EVE Muhely.app/Contents/MacOS/eve-backend')]
        else:
            shutil.copytree(root/'runtime', helper/'runtime');shutil.copytree(root/'app', helper/'app')
            command=[str(helper/'runtime/pythonw.exe'),'-I','-X','utf8',str(helper/'app/desktop.py')]
        atomic_json(folder/'handoff.json', {'parent_pid':parent_pid,'profile':str(Path(profile).resolve()),'origin':origin})
        env=dict(os.environ,PYINSTALLER_RESET_ENVIRONMENT='1')
        options={'creationflags':subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform=='win32' else {'start_new_session':True}
        with (folder/'install.log').open('ab') as log:
            subprocess.Popen([*command,'--apply-update',str(folder)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,env=env,cwd=str(folder),**options)
    except Exception:
        if helper.exists():shutil.rmtree(helper)
        raise
    return {'started':True}


def verify_restart(origin, expected, timeout=45):
    import json,urllib.request
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            with opener.open(origin+'/health',timeout=1) as response:info=json.load(response)
            if info.get('app')=='eve-muhely' and info.get('version')==expected:return
        except (OSError,ValueError):pass
        time.sleep(.2)
    raise UpdateError('update_restart_failed')


def apply_update(folder):
    """Entry point of the detached copied runtime. Never touches credential files."""
    folder=Path(folder).resolve();result=folder.parent/'last-result.json'
    try:
        receipt,payload=read_receipt(folder)
        handoff=strict_json((folder/'handoff.json').read_bytes())
        profile=Path(handoff['profile']).resolve()
        if folder.parent != profile/'updates': raise UpdateError('invalid_update')
        target=Path(receipt['target']);validate_installation(target,receipt['platform'])
        if profile.is_relative_to(target.resolve()): raise UpdateError('invalid_update')
        extracted=extract_archive(folder/'archive.zip',folder/'extracted',receipt['platform'])
        payload_version(extracted,receipt['platform'],payload['version'])
        # Do not close/kill the app ourselves: native shell uses normal full quit.
        wait_process(handoff['parent_pid']);wait_process(receipt['backend_pid'])
        backup=backup_database(profile)
        previous=replace_application(target,extracted,receipt['platform'])
        atomic_json(result,{'ok':True,'phase':'restarting','version':payload['version'],'previous':str(previous),'backup':str(backup) if backup else None})
        command=['/usr/bin/open','-n',str(target)] if receipt['platform']=='macos-arm64' else [str(target/'EVE_Muhely.exe')]
        try:
            subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            verify_restart(handoff['origin'],payload['version'])
            atomic_json(result,{'ok':True,'phase':'installed','version':payload['version'],'previous':str(previous),'backup':str(backup) if backup else None})
        except (OSError,UpdateError):
            # The replacement is valid; retain both copies and report restart.
            atomic_json(result,{'ok':False,'phase':'restart','error':'update_restart_failed','version':payload['version'],'previous':str(previous)})
        return 0
    except Exception as error:
        atomic_json(result,{'ok':False,'error':str(error) if isinstance(error,UpdateError) else 'update_install_failed'})
        return 1
