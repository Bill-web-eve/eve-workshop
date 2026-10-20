#!/usr/bin/env python3
"""Build a clean, self-contained Apple Silicon app; never copy a user database."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import plistlib
import runpy
import shutil
import subprocess
import sys

SOURCE=Path(__file__).resolve().parents[1]


def public_config(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    client=data.get('client_id')
    if not isinstance(client,str) or not client or len(client)>200 or not all(c.isalnum() or c in '-_' for c in client):
        raise ValueError('A nyilvános EVE Client ID szükséges.')
    return {'client_id':client}


def stage_source(target,config):
    target=Path(target);target.mkdir(parents=True,exist_ok=False)
    (target/'muhely').mkdir();(target/'data').mkdir()
    # Allowlist only: tests, logs, developer files and user data cannot enter.
    for path in (SOURCE/'muhely').glob('*.py'):shutil.copy2(path,target/'muhely'/path.name)
    shutil.copy2(SOURCE/'desktop.py',target/'desktop.py')
    shutil.copytree(SOURCE/'static',target/'static',ignore=shutil.ignore_patterns('.DS_Store','__pycache__'))
    for name in ['Hasznalat.md','UserGuide.en.md']:shutil.copy2(SOURCE/name,target/name)
    shutil.copy2(SOURCE/'data/catalog.sqlite3',target/'data/catalog.sqlite3')
    shutil.copy2(SOURCE/'data/intel_universe.json',target/'data/intel_universe.json')
    (target/'data/defaults.json').write_text(json.dumps({'client_id':config['client_id']})+'\n',encoding='utf-8')
    licenses=target/'licenses';licenses.mkdir()
    runtime_license=Path(sys.base_prefix)/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'LICENSE.txt'
    shutil.copy2(runtime_license,licenses/'Python.txt')
    for package in ['cryptography','cffi','pycparser','certifi','pyinstaller']:
        distribution=importlib.metadata.distribution(package)
        folder=licenses/package;folder.mkdir()
        for record in distribution.files or []:
            if 'license' in str(record).lower() or 'copying' in str(record).lower():
                path=Path(distribution.locate_file(record))
                if path.is_file():shutil.copy2(path,folder/path.name)
    (licenses/'CCP.txt').write_text('EVE Online and all related trademarks are the property of CCP hf. This independent application is not endorsed by CCP. Static game data is provided by CCP through the EVE Online Static Data Export.\nhttps://developers.eveonline.com/docs/services/static-data/\n',encoding='utf-8')


def audit_bundle(app):
    app=Path(app)
    forbidden={'muhely.sqlite3','characters.enc','vault.key','vault.key.dpapi','server.log','launcher.log','saved_inputs.json'}
    for path in app.rglob('*'):
        if path.name in forbidden or path.name.endswith('.xlsx') or path.name=='backups':
            raise RuntimeError('Private or unrelated data entered bundle: '+path.name)
        if path.is_file() and path.suffix in ['.sqlite3','.db'] and path.name!='catalog.sqlite3':
            raise RuntimeError('Unexpected database in distribution: '+path.name)
    defaults=list(app.rglob('defaults.json'))
    if not defaults:raise RuntimeError('Missing public Client ID')
    for path in defaults:
        if set(json.loads(path.read_text()))!={'client_id'}:raise RuntimeError('Unexpected defaults')


def build(config_file,work,output):
    if sys.platform!='darwin' or platform.machine()!='arm64':raise SystemExit('Apple Silicon Mac szükséges az összeállításhoz.')
    work=Path(work).resolve();output=Path(output).resolve()
    work.mkdir(parents=True,exist_ok=True);output.mkdir(parents=True,exist_ok=True)
    staging=work/'source'
    if staging.exists():raise SystemExit('Használj új, üres build munkamappát.')
    config=public_config(config_file);stage_source(staging,config)
    version=runpy.run_path(str(staging/'muhely/__init__.py'))['__version__']
    spec=work/'EVE Muhely.spec'
    spec.write_text(f'''# Generated clean release, no Developer ID or notarization.
import os
os.environ['MACOSX_DEPLOYMENT_TARGET']='11.0'
a=Analysis([{str(staging/'desktop.py')!r}],pathex=[{str(staging)!r}],
    binaries=[],datas=[({str(staging/'static')!r},'static'),({str(staging/'data')!r},'data'),({str(staging/'licenses')!r},'licenses'),({str(staging/'Hasznalat.md')!r},'.'),({str(staging/'UserGuide.en.md')!r},'.')],
    hiddenimports=['cryptography.hazmat.bindings._rust','certifi'],
    excludes=['tkinter','unittest','PIL','numpy','pandas','pytest','IPython'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='EVE Muhely',debug=False,
    bootloader_ignore_signals=False,strip=False,upx=False,console=False,
    target_arch='arm64',codesign_identity=None,entitlements_file=None)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='EVE Muhely')
app=BUNDLE(coll,name='EVE Muhely.app',icon={str(staging/'static/app.icns')!r},
    bundle_identifier='hu.eve.muhely.local',version={version!r},
    info_plist={{'CFBundleDisplayName':'EVE Műhely','LSMinimumSystemVersion':'11.0','LSUIElement':True,
        'NSHighResolutionCapable':True,'NSLocalNetworkUsageDescription':'A Műhely a saját böngésződdel a helyi gépen kapcsolódik.'}})
''',encoding='utf-8')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--distpath',str(work/'dist'),
                    '--workpath',str(work/'build'),str(spec)],check=True,cwd=staging)
    app=work/'dist/EVE Muhely.app';audit_bundle(app)
    subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True)
    disk=work/'disk';disk.mkdir();shutil.copytree(app,disk/app.name,symlinks=True)
    (disk/'Applications').symlink_to('/Applications',target_is_directory=True)
    instructions=f'''EVE MŰHELY {version} – APPLE SILICON MAC

Feltétel: Apple Silicon (M1 vagy újabb), macOS 11 vagy újabb.
Intel Macre nem használható. Python, Excel és Codex telepítése nem kell.

TELEPÍTÉS
1. Húzd az EVE Muhely alkalmazást az Applications / Alkalmazások mappába.
2. Az alkalmazást az Alkalmazások mappából indítsd el.
3. Ha a macOS blokkolja, a Rendszerbeállítások → Adatvédelem és biztonság
   oldalon válaszd a Megnyitás mindenképpen lehetőséget, majd erősítsd meg.
   Az alkalmazásnak nincs Apple Developer ID aláírása és nincs notarizálva.
   Az ARM-kód kötelező helyi technikai aláírása nem fejlesztői tanúsítvány.
4. A Műhely a saját böngésződben nyílik meg: http://127.0.0.1:8765

ELSŐ HASZNÁLAT
A kiadás üres: nincs benne karakter, mentett terv, készlet, belépési token,
Client Secret vagy személyes adatbázis. Csak a nyilvános EVE Client ID
van előre megadva. Az EVE-kapcsolat menüben mindenki a saját karaktereit
engedélyezi. Az API használatához internet kell; a helyi tervezéshez nem.
A Client ID nem jelent hozzáférést más karakteréhez: saját EVE-belépés kell.
A Client ID a kapcsolat oldalon átírható. Callback: http://127.0.0.1:8765/callback

HELYI ADATOK ÉS FRISSÍTÉS
Saját adatok: ~/Library/Application Support/EVE Muhely/
Ezek csak az adott Macen jönnek létre. A tokenek titkosítva tárolódnak,
a kulcsot a macOS Kulcskarika őrzi. A Kulcskarika első belépéskor
hozzáférést kérhet. Ha már használtad a Műhelyt ezen a Macen,
a korábbi saját adataid megmaradnak; a tiszta csomag ezeket nem törli.
Leállítás: a Műhely bal oldali „Alkalmazás leállítása” gombjával.

Az app nem módosít Gatekeeper-beállítást és nem távolít el karanténjelölést.
Hivatalos Apple-útmutató: https://support.apple.com/102445
'''
    (disk/'Telepites.txt').write_text(instructions,encoding='utf-8')
    name=f'EVE_Muhely-{version}-macOS-AppleSilicon'
    dmg=output/(name+'.dmg')
    subprocess.run(['/usr/bin/hdiutil','create','-volname',f'EVE Muhely {version}','-srcfolder',str(disk),'-fs','HFS+','-format','UDZO','-ov',str(dmg)],check=True)
    subprocess.run(['/usr/bin/hdiutil','verify',str(dmg)],check=True)
    checksum=hashlib.sha256(dmg.read_bytes()).hexdigest()
    (output/(name+'.sha256')).write_text(checksum+'  '+dmg.name+'\n')
    (output/'EVE_Muhely-Telepites.txt').write_text(instructions,encoding='utf-8')
    (work/'release-manifest.json').write_text(json.dumps({'version':version,'architecture':'arm64','minimum_macos':'11.0',
        'signing':'ad-hoc only; no Developer ID; no notarization','client_id_only':True,'characters':0,'saved_plans':0,
        'python':platform.python_version(),'pyinstaller':importlib.metadata.version('pyinstaller'),
        'cryptography':importlib.metadata.version('cryptography'),'sha256':checksum},indent=2)+'\n')
    print('Clean Apple Silicon release: '+str(dmg),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--client-id-file',type=Path,required=True)
    parser.add_argument('--work-dir',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();build(args.client_id_file,args.work_dir,args.output_dir)
