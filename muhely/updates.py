"""Opt-in installation of authenticated, public GitHub release updates.

No remote filename, URL, process command or install directory is accepted from UI.
The Ed25519 trust anchor ships with the application, not with the downloaded feed.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
import threading
import time
import urllib.error
import urllib.request
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from . import __version__

REPO = 'https://github.com/Bill-web-eve/eve-workshop'
FEED = REPO + '/releases/latest/download/update.json'
MAX_ARCHIVE = 150 * 1024 * 1024
INTERVAL = 24 * 3600
ROOT = Path(__file__).resolve().parent.parent

class UpdateError(ValueError):
    pass

def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})\.(0|[1-9]\d{0,3})', value):
        raise UpdateError('invalid_update')
    return tuple(map(int, value.split('.')))

def strict_json(raw):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out: raise UpdateError('invalid_update')
            out[k] = v
        return out
    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(UpdateError('invalid_update')))
    except (ValueError, TypeError, UnicodeError):
        raise UpdateError('invalid_update') from None

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')

def trust_key(root=ROOT):
    try:
        value = strict_json((Path(root)/'data/update-public-key.json').read_bytes())
        raw = base64.b64decode(value['ed25519'], validate=True)
        return Ed25519PublicKey.from_public_bytes(raw)
    except (OSError, ValueError, KeyError, TypeError):
        raise UpdateError('missing_update_key') from None

def verify_document(document, key=None):
    """Verify before interpreting executable locations; every asset field is signed."""
    try:
        if not isinstance(document, dict) or set(document) != {'payload', 'signature'}: raise UpdateError('invalid_update')
        payload = document['payload']
        signature = base64.b64decode(document['signature'], validate=True)
        (key or trust_key()).verify(signature, canonical(payload))
        if not isinstance(payload, dict) or set(payload) != {'schema', 'version', 'notes_url', 'assets'}: raise UpdateError('invalid_update')
        if type(payload['schema']) is not int or payload['schema'] != 1: raise UpdateError('invalid_update')
        version(payload['version'])
        tag = 'v'+payload['version']
        if payload['notes_url'] != REPO+'/releases/tag/'+tag: raise UpdateError('invalid_update')
        assets = payload['assets']
        if not isinstance(assets, dict) or set(assets) != {'macos-arm64', 'windows-x64'}: raise UpdateError('invalid_update')
        for platform, a in assets.items():
            expected = 'EVE_Muhely-'+payload['version']+('-macOS-AppleSilicon-update.zip' if platform == 'macos-arm64' else '-Windows11-x64.zip')
            if not isinstance(a, dict) or set(a) != {'name', 'url', 'size', 'sha256'}: raise UpdateError('invalid_update')
            if a['name'] != expected or a['url'] != REPO+'/releases/download/'+tag+'/'+expected: raise UpdateError('invalid_update')
            if type(a['size']) is not int or not 0 < a['size'] <= MAX_ARCHIVE: raise UpdateError('invalid_update')
            if not isinstance(a['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', a['sha256']): raise UpdateError('invalid_update')
        return payload
    except InvalidSignature:
        raise UpdateError('invalid_signature') from None
    except (KeyError, TypeError, ValueError) as e:
        if isinstance(e, UpdateError): raise
        raise UpdateError('invalid_update') from None

def asset_valid(path, asset):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != asset['size']: raise UpdateError('invalid_archive')
    h = hashlib.sha256()
    with path.open('rb') as f:
        while block := f.read(1024*1024): h.update(block)
    if h.hexdigest() != asset['sha256']: raise UpdateError('invalid_archive')

def atomic_json(path, value):
    path = Path(path);path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.'+secrets.token_hex(8)+'.tmp')
    fd = os.open(temp, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f: json.dump(value, f, ensure_ascii=True, allow_nan=False)
        # A Windows reader/antivirus can briefly deny replacing a JSON file.
        # Keep the old complete file until the replacement succeeds, and let
        # persistent permission/disk errors propagate after a bounded retry.
        delays=(0,.02,.05,.1,.2,.4)
        for attempt,delay in enumerate(delays):
            if delay:time.sleep(delay)
            try:
                os.replace(temp,path);break
            except PermissionError:
                if attempt==len(delays)-1:raise
    finally: temp.unlink(missing_ok=True)

def installation(executable=None, platform=None, frozen=None):
    """Determine the target solely from the running, packaged executable."""
    platform = platform or sys.platform
    executable = Path(executable or sys.executable).resolve()
    if platform == 'darwin' and (getattr(sys, 'frozen', False) if frozen is None else frozen):
        if executable.name != 'eve-backend' or executable.parent.name != 'MacOS' or executable.parent.parent.name != 'Contents': raise UpdateError('manual_install_required')
        root = executable.parents[2]
        validate_installation(root, 'macos-arm64')
        return root, 'macos-arm64'
    if platform == 'win32' and executable.parent.name == 'runtime' and executable.name.lower() in {'python.exe', 'pythonw.exe'}:
        root = executable.parent.parent
        validate_installation(root, 'windows-x64')
        return root, 'windows-x64'
    raise UpdateError('manual_install_required')

def validate_installation(root, platform):
    root = Path(root)
    if root.is_symlink() or not root.is_dir(): raise UpdateError('manual_install_required')
    if platform == 'macos-arm64':
        import plistlib
        try: info = plistlib.loads((root/'Contents/Info.plist').read_bytes())
        except (OSError, ValueError): raise UpdateError('manual_install_required') from None
        if root.suffix != '.app' or info.get('CFBundleIdentifier') != 'hu.eve.muhely.local' or not (root/'Contents/MacOS/eve-backend').is_file(): raise UpdateError('manual_install_required')
    elif platform == 'windows-x64':
        if not all((root/p).is_file() for p in ['EVE_Muhely.exe','runtime/pythonw.exe','app/windows_desktop.py','app/muhely/updates.py']): raise UpdateError('manual_install_required')
    else: raise UpdateError('manual_install_required')

class Updates:
    def __init__(self, store, clock=time.time, opener=None, key=None, install=None):
        self.store, self.clock, self.key = store, clock, key
        self.open = opener or urllib.request.build_opener().open
        self.lock = threading.RLock();self.busy = False;self.closed = False
        self.cache = Path(store.folder)/'updates';self.document = None;self.ticket = None
        try: self.target, self.platform = install or installation();self.installable = os.access(self.target.parent, os.W_OK)
        except UpdateError: self.target, self.platform, self.installable = None, ('windows-x64' if sys.platform == 'win32' else 'macos-arm64'), False
        prefs = store.settings().get('updates', {})
        if not isinstance(prefs,dict):prefs={}
        self.automatic = prefs.get('automatic', True) is True
        self.checked = prefs.get('checked_at') if type(prefs.get('checked_at')) in {int,float} else None
        self.status = {'phase':'idle', 'error':None, 'progress':0, 'bytes':0, 'total':0}
        try:
            doc = strict_json((self.cache/'verified.json').read_bytes());verify_document(doc, self.key);self.document = doc
        except (OSError, UpdateError): pass

    def snapshot(self):
        with self.lock:
            payload = self.document['payload'] if self.document else None
            latest = payload['version'] if payload else None
            return {**self.status, 'current_version':__version__, 'latest_version':latest,
                    'available':bool(latest and version(latest)>version(__version__)),
                    'notes_url':payload['notes_url'] if payload else None,
                    'automatic':self.automatic, 'checked_at':self.checked,
                    'next_check':self.checked+INTERVAL if self.checked else None,
                    'installable':self.installable, 'busy':self.busy,
                    'ticket':self.ticket, 'platform':self.platform, 'last_result':self.last_result()}

    def last_result(self):
        try:
            path=self.cache/'last-result.json'
            if path.stat().st_size>4096:return None
            value=strict_json(path.read_bytes())
            return {k:value[k] for k in ['ok','version','error'] if k in value}
        except (OSError,ValueError,TypeError):return None

    def configure(self, data):
        if set(data) != {'automatic'} or type(data['automatic']) is not bool: raise UpdateError('invalid_update_settings')
        with self.lock:
            self.automatic = data['automatic'];self._save()
        return self.snapshot()

    def _save(self): self.store.save_settings({'updates':{'automatic':self.automatic, 'checked_at':self.checked}})

    def request(self, action, manual=True):
        with self.lock:
            if action not in {'check','download'}: raise UpdateError('invalid_update')
            if self.closed or self.busy: return self.snapshot()
            if action == 'check' and not manual and (not self.automatic or self.checked and self.clock()-self.checked<INTERVAL): return self.snapshot()
            if action == 'download' and (not self.installable or not self.document or not self.snapshot()['available']): raise UpdateError('manual_install_required')
            self.busy = True;self.ticket = None
            self.status.update(phase='checking' if action=='check' else 'downloading', error=None, progress=0, bytes=0, total=0)
            threading.Thread(target=self._work, args=(action,), daemon=True).start()
        return self.snapshot()

    def _work(self, action):
        try:
            if action == 'check': self._check()
            else: self._download()
        except Exception as e:
            with self.lock:self.status.update(phase='error', error=str(e) if isinstance(e, UpdateError) else 'update_network_error')
        finally:
            with self.lock:
                if action=='check':self.checked = self.clock();self._save()
                self.busy = False

    def _check(self):
        try:
            with self.open(urllib.request.Request(FEED, headers={'User-Agent':'EVEWorkshop-updater','Accept':'application/json'}), timeout=20) as response:
                raw = response.read(65537)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                with self.lock:self.status.update(phase='unpublished', error=None)
                return
            raise
        if len(raw)>65536: raise UpdateError('invalid_update')
        document = strict_json(raw);verify_document(document, self.key)
        with self.lock:
            # A replayed older feed cannot replace an already verified newer one.
            if self.document and version(document['payload']['version'])<version(self.document['payload']['version']): raise UpdateError('older_update')
            atomic_json(self.cache/'verified.json', document);self.document = document
            self.status['phase'] = 'available' if self.snapshot()['available'] else 'current'

    def _download(self):
        with self.lock:
            document = self.document;payload = verify_document(document, self.key);asset = payload['assets'][self.platform]
        ticket = secrets.token_hex(16);folder = self.cache/ticket;folder.mkdir(mode=0o700, parents=True)
        partial = folder/'archive.part';archive = folder/'archive.zip'
        try:
            with self.open(urllib.request.Request(asset['url'], headers={'User-Agent':'EVEWorkshop-updater'}), timeout=30) as response, partial.open('xb') as out:
                size = 0
                while block := response.read(1024*1024):
                    if self.closed: raise UpdateError('update_cancelled')
                    size += len(block)
                    if size>asset['size']: raise UpdateError('invalid_archive')
                    out.write(block)
                    with self.lock:self.status.update(bytes=size, total=asset['size'], progress=int(100*size/asset['size']))
            with self.lock:self.status['phase']='verifying'
            asset_valid(partial, asset);os.replace(partial, archive)
            atomic_json(folder/'receipt.json', {'document':document, 'platform':self.platform, 'target':str(self.target), 'backend_pid':os.getpid(), 'created':self.clock(), 'current_version':__version__})
            with self.lock:self.ticket=ticket;self.status.update(phase='ready', progress=100)
        except Exception:
            partial.unlink(missing_ok=True);archive.unlink(missing_ok=True);raise

    def close(self): self.closed=True
