#!/usr/bin/env python3
"""Build a clean portable Windows x64 ZIP from pinned official binaries."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import runpy
import shutil
import struct
import tarfile
import subprocess
import urllib.parse
import urllib.request
import zipfile

if __package__:
    from .build_macos_release import public_config,audit_bundle
    from .audit_windows_imports import audit as audit_imports
else:
    from build_macos_release import public_config,audit_bundle
    from audit_windows_imports import audit as audit_imports

SOURCE=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(record,cache):
    url=urllib.parse.urlsplit(record['url'])
    if url.scheme!='https' or url.hostname not in ['www.python.org','files.pythonhosted.org']:
        raise ValueError('Only official Python and PyPI download hosts are allowed.')
    target=cache/Path(url.path).name
    if not target.exists():
        with urllib.request.urlopen(record['url'],timeout=60) as response,target.open('xb') as out:
            total=0
            while data:=response.read(1024*1024):
                total+=len(data)
                if total>512*1024*1024:raise ValueError('Unexpectedly large dependency.')
                out.write(data)
    if sha(target)!=record['sha256']:raise ValueError('Dependency checksum mismatch: '+target.name)
    return target


def extract(archive,target):
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            path=PurePosixPath(item.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in item.filename or ':' in item.filename:
                raise ValueError('Unsafe archive path.')
            if (item.external_attr>>16)&0o170000==0o120000:raise ValueError('Archive symlinks are not allowed.')
        source.extractall(target)


def pe_info(path):
    data=Path(path).read_bytes()
    if data[:2]!=b'MZ':raise ValueError('Not a PE executable: '+str(path))
    offset=struct.unpack_from('<I',data,0x3c)[0]
    if data[offset:offset+4]!=b'PE\0\0':raise ValueError('Invalid PE header.')
    machine=struct.unpack_from('<H',data,offset+4)[0]
    magic=struct.unpack_from('<H',data,offset+24)[0]
    subsystem=struct.unpack_from('<H',data,offset+24+68)[0]
    if machine==0x8664 and magic==0x20b:return {'machine':'AMD64','format':'PE32+','subsystem':subsystem}
    # AnyCPU managed assemblies are valid in an x64 CLR, unlike x86 native DLLs.
    if machine==0x14c and magic==0x10b:
        directory=offset+24+96
        cli_rva,cli_size=struct.unpack_from('<II',data,directory+14*8)
        sections=offset+24+struct.unpack_from('<H',data,offset+20)[0]
        for index in range(struct.unpack_from('<H',data,offset+6)[0]):
            size,va,rawsize,raw=struct.unpack_from('<IIII',data,sections+index*40+8)
            if cli_rva and cli_size>=20 and va<=cli_rva<va+max(size,rawsize):
                flags=struct.unpack_from('<I',data,raw+cli_rva-va+16)[0]
                if flags&1 and not flags&(2|0x20000):return {'machine':'AnyCPU','format':'managed IL','subsystem':subsystem}
    raise ValueError('Non-x64/non-AnyCPU binary: '+str(path))


def stage_source_package(record,cache,packages):
    if record['name']!='proxy_tools' or record['version']!='0.1.0':raise ValueError('Unreviewed source dependency')
    with tarfile.open(fetch(record,cache)) as archive:
        member=archive.getmember('proxy_tools-0.1.0/proxy_tools/__init__.py')
        if not member.isfile() or member.size>100000:raise ValueError('Unsafe source dependency')
        target=packages/'proxy_tools';target.mkdir()
        (target/'__init__.py').write_bytes(archive.extractfile(member).read())
        license_info=archive.getmember('proxy_tools-0.1.0/PKG-INFO')
        if not license_info.isfile() or license_info.size>100000:raise ValueError('Unsafe license metadata')
        (target/'PACKAGE-INFO.txt').write_bytes(archive.extractfile(license_info).read())


def trim_other_architectures(packages):
    # Universal wheels contain optional x86/ARM and unused legacy browser helpers.
    for name in ['webview/lib/runtimes/win-arm64','webview/lib/runtimes/win-x86',
                 'clr_loader/ffi/dlls/x86']:
        path=packages/name
        if path.exists():shutil.rmtree(path)
    # pywebview enumerates all loader directories during import, including other
    # architectures. Keep inert placeholders so ZIP extraction preserves them.
    for arch in ['win-arm64','win-x86']:
        native=packages/'webview/lib/runtimes'/arch/'native';native.mkdir(parents=True,exist_ok=True)
        (native/'README.txt').write_text('Directory required by WebView2 discovery. No non-x64 binary is distributed.\n')
    for name in ['WebBrowserInterop.x86.dll','WebBrowserInterop.x64.dll']:
        (packages/'webview/lib'/name).unlink(missing_ok=True)



def stage(root,config):
    app=root/'app';(app/'muhely').mkdir(parents=True);(app/'data').mkdir()
    for file in (SOURCE/'muhely').glob('*.py'):shutil.copy2(file,app/'muhely'/file.name)
    for name in ['desktop.py','windows_desktop.py','windows_smoke_test.py','windows_window_smoke.py']:shutil.copy2(SOURCE/name,app/name)
    shutil.copytree(SOURCE/'static',app/'static',ignore=shutil.ignore_patterns('.DS_Store','__pycache__'))
    for name in ['Hasznalat.md','UserGuide.en.md']:shutil.copy2(SOURCE/name,app/name)
    shutil.copy2(SOURCE/'data/catalog.sqlite3',app/'data/catalog.sqlite3')
    shutil.copy2(SOURCE/'data/intel_universe.json',app/'data/intel_universe.json')
    (app/'data/defaults.json').write_text(json.dumps(config)+'\n',encoding='utf-8')


def build(config_file,work,output,zig,cache):
    work=Path(work).resolve();output=Path(output).resolve();cache=Path(cache).resolve()
    work.mkdir(parents=True,exist_ok=True);output.mkdir(parents=True,exist_ok=True);cache.mkdir(parents=True,exist_ok=True)
    root=work/'EVE Muhely'
    if root.exists():raise ValueError('Use a new, empty build directory.')
    lock=json.loads((SOURCE/'tools/windows-runtime-lock.json').read_text())
    config=public_config(config_file);stage(root,config)
    runtime=root/'runtime';runtime.mkdir();extract(fetch(lock['python'],cache),runtime)
    packages=runtime/'Lib/site-packages';packages.mkdir(parents=True)
    for wheel in lock['wheels']:extract(fetch(wheel,cache),packages)
    for record in lock.get('sources',[]):stage_source_package(record,cache,packages)
    trim_other_architectures(packages)
    # _pth isolation ignores global Python, user site-packages and registry paths.
    pth=runtime/'python313._pth'
    if not pth.exists():raise ValueError('Unexpected embedded runtime layout.')
    pth.write_text('python313.zip\n.\nLib\\site-packages\n..\\app\n',encoding='ascii')
    version=runpy.run_path(str(root/'app/muhely/__init__.py'))['__version__']
    from PIL import Image
    icon=work/'app.ico'
    with Image.open(SOURCE/'static/app-window.icns') as source:source.save(icon,sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    shutil.copy2(icon,root/'app/data/app.ico')
    resource=work/'windows.rc';numbers=version.replace('.',',')+',0'
    resource.write_text(f'''1 ICON "app.ico"
1 VERSIONINFO
FILEVERSION {numbers}
PRODUCTVERSION {numbers}
FILEOS 0x40004
FILETYPE 1
BEGIN
 BLOCK "StringFileInfo"
 BEGIN
  BLOCK "040904b0"
  BEGIN
   VALUE "FileDescription", "EVE Muhely Windows launcher"
   VALUE "FileVersion", "{version}"
   VALUE "ProductName", "EVE Muhely"
   VALUE "ProductVersion", "{version}"
  END
 END
 BLOCK "VarFileInfo"
 BEGIN
  VALUE "Translation", 0x409, 1200
 END
END
''',encoding='ascii')
    env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(cache.parent/'zig-global'),ZIG_LOCAL_CACHE_DIR=str(work/'zig-local'))
    subprocess.run([str(zig),'cc','-target','x86_64-windows-gnu','-municode','-Wl,--subsystem,windows','-O2','-s','-static','-mcpu=baseline',
                    str(SOURCE/'tools/windows_launcher.c'),str(resource),'-o',str(root/'EVE_Muhely.exe')],env=env,cwd=work,check=True)
    (root/'Inditas.cmd').write_bytes(b'@echo off\r\nstart "" "%~dp0runtime\\pythonw.exe" -I -X utf8 "%~dp0app\\windows_desktop.py"\r\n')
    (root/'Ellenorzes.cmd').write_bytes(b'@echo off\r\n"%~dp0runtime\\python.exe" -I -X utf8 "%~dp0app\\windows_smoke_test.py" --online\r\necho.\r\npause\r\n')
    (root/'Ellenorzes_ablak.cmd').write_bytes(b'@echo off\r\n"%~dp0runtime\\python.exe" -I -X utf8 "%~dp0app\\windows_window_smoke.py" --report "%TEMP%\\eve-window-smoke.json"\r\necho.\r\npause\r\n')
    instructions=f'''EVE MŰHELY {version} – WINDOWS 11 64 BIT

1. A ZIP-en jobb kattintás → Az összes kibontása.
2. Nyisd meg a kibontott EVE Muhely mappát.
3. Indítsd el az EVE_Muhely.exe fájlt. A teljes mappát tartsd együtt.
4. A műhely saját Windows-ablakban nyílik meg. Az EVE-belépéshez
   ideiglenesen a rendszerböngészőt használja, majd az appba térsz vissza.
5. Windows 11-en a Microsoft Edge WebView2 Runtime és a .NET Framework
   szükséges (általában már telepítve vannak). WebView2 hiányakor az app
   jelzi a Microsoft hivatalos letöltési oldalát:
   https://developer.microsoft.com/microsoft-edge/webview2/

Külön Python, Excel és Codex telepítése nem szükséges. Rendszergazdai
telepítés nem kell. Internet az EVE-belépéshez és frissítéshez szükséges.
Az Inditas.cmd ugyanazt az alkalmazást indítja tartalék indítóként.
Parancsikont az EVE_Muhely.exe fájlhoz készíthetsz az Asztalon.

Ez a kiadás üres: nincs benne karakter, mentett terv, személyes készlet,
belépési token vagy Client Secret. Csak a nyilvános EVE Client ID van
előre megadva. Az EVE-kapcsolat menüben a saját karaktereidet engedélyezd.

SAJÁT ADATOK ÉS LEÁLLÍTÁS
Adatok: %LOCALAPPDATA%\\EVE Muhely
Frissítés előtt használd az Alkalmazás leállítása gombot, utána cseréld
az alkalmazás mappáját. A saját adatok megmaradnak. Az EVE-tokenek
titkosítva tárolódnak, a kulcsot a Windows DPAPI az adott Windows-fiókhoz
védi. Másik gépen vagy másik Windows-fiókkal új EVE-belépés szükséges.
Leállítás: a bal oldali Alkalmazás leállítása gombbal.

ELLENŐRZÉS ÉS NAPLÓK
Az Ellenorzes_ablak.cmd külön, üres tesztprofillal ellenőrzi a saját ablakot,
a vágólapot, exportot, külön intelablakokat és a belépés visszatérését.
Az Ellenorzes.cmd ideiglenes, üres tesztprofillal ellenőrzi a futtatást,
a Windows titkosítását, a helyi API-t, a tervmentést és az EVE HTTPS-t.
A saját karaktereidet és mentett terveidet nem módosítja.
Hiba esetén: %LOCALAPPDATA%\\EVE Muhely\\launcher.log és server.log.

A program nincs kiadói tanúsítvánnyal aláírva. Ha a Windows figyelmeztet,
csak megbízható forrásból származó csomagnál engedélyezd a futtatást.
Sem a SmartScreent, sem a vírusvédelmet nem kell kikapcsolni.

Ellenőrzés állapota: a Windows x64 binárisok és a csomag szerkezete
ellenőrizve; ezen a Macen natív Windows 11 futtatási próba nem történt.
'''
    (root/'Olvass_el.txt').write_text(instructions,encoding='utf-8-sig')
    (root/'Licenses.txt').write_text('Python: runtime/LICENSE.txt\nThird-party licenses: runtime/Lib/site-packages/*.dist-info/licenses\nEVE Online game data and trademarks belong to their respective owners.\nThis independent application is not endorsed by CCP.\nhttps://developers.eveonline.com/docs/services/static-data/\n',encoding='utf-8')
    (root/'licenses').mkdir()
    shutil.copy2(Path(zig).parent/'lib/libc/mingw/COPYING',root/'licenses/MinGW-w64.txt')
    shutil.copy2(Path(zig).parent/'LICENSE',root/'licenses/Zig.txt')
    audit_bundle(root)
    binaries=[p for p in root.rglob('*') if p.suffix.lower() in ['.exe','.dll','.pyd']]
    for path in binaries:pe_info(path)
    if pe_info(root/'EVE_Muhely.exe')['subsystem']!=2:raise ValueError('Launcher must be a Windows GUI application.')
    dependencies=audit_imports(root)
    (work/'import-audit.json').write_text(json.dumps(dependencies,indent=2)+'\n')
    hashes=''.join(sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in sorted(root.rglob('*')) if p.is_file())
    (root/'FILE_SHA256SUMS.txt').write_text(hashes,encoding='utf-8')
    name=f'EVE_Muhely-{version}-Windows11-x64';archive=output/(name+'.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as package:
        for path in sorted(root.rglob('*')):
            if path.is_file():package.write(path,path.relative_to(work).as_posix())
    with zipfile.ZipFile(archive) as package:
        if package.testzip():raise ValueError('ZIP verification failed.')
    checksum=sha(archive);(output/(name+'.sha256')).write_text(checksum+'  '+archive.name+'\n')
    (output/'EVE_Muhely-Windows-Telepites.txt').write_text(instructions,encoding='utf-8-sig')
    manifest={'version':version,'platform':'Windows 11','architecture':'x86_64','portable':True,'publisher_signed':False,
        'python':lock['python'],'wheels':lock['wheels'],'zig':subprocess.check_output([str(zig),'version'],text=True).strip(),
        'pe64_binaries_checked':len(binaries),'dll_dependencies_checked':True,'characters':0,'saved_plans':0,'client_id_only':True,'windows_runtime_test':'not_run','interface':'native WinForms/WebView2 window',
        'managed_assemblies_checked':sum(pe_info(p)['machine']=='AnyCPU' for p in binaries),
        'archive_sha256':checksum}
    (work/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Clean Windows x64 release: '+str(archive),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--client-id-file',type=Path,required=True)
    parser.add_argument('--work-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--cache-dir',type=Path,required=True);parser.add_argument('--zig',type=Path,required=True)
    args=parser.parse_args();build(args.client_id_file,args.work_dir,args.output_dir,args.zig,args.cache_dir)
