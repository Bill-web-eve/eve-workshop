#!/usr/bin/env python3
"""Publish source/catalogue and lightweight macOS launchers; never copy user data."""
from pathlib import Path
import argparse
import hashlib
import plistlib
import shutil
import subprocess
import runpy

SOURCE = Path(__file__).resolve().parents[1]


def build_app(application):
    bundle = Path(application)/'Contents'
    (bundle/'MacOS').mkdir(parents=True, exist_ok=True)
    (bundle/'Resources').mkdir(exist_ok=True)
    shutil.copytree(SOURCE, bundle/'Resources/eve_muhely', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.venv', '.git', 'node_modules', 'release-assets', 'test-results', '*.building.sqlite3'))
    info = {'CFBundleName': 'EVE Muhely', 'CFBundleDisplayName': 'EVE Műhely',
            'CFBundleIdentifier': 'hu.eve.muhely.local', 'CFBundleExecutable': 'EVE Muhely',
            'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': runpy.run_path(str(SOURCE/'muhely/__init__.py'))['__version__'],
            'CFBundleVersion': '22', 'LSMinimumSystemVersion': '11.0', 'LSUIElement': False,
            'CFBundleIconFile': 'app-window.icns',
            'NSAppTransportSecurity': {'NSAllowsLocalNetworking': True},
            'NSHighResolutionCapable': True}
    shutil.copy2(SOURCE/'static/app-window.icns',bundle/'Resources/app-window.icns')
    (bundle/'Info.plist').write_bytes(plistlib.dumps(info))
    executable = bundle/'MacOS/EVE Muhely'
    subprocess.run(['xcrun', 'clang', '-fobjc-arc', '-framework', 'Cocoa', '-framework', 'WebKit', '-framework', 'UserNotifications',
                    '-mmacosx-version-min=11.0', str(SOURCE/'tools/macos_launcher.m'),
                    '-o', str(executable)], check=True)
    executable.chmod(0o755)
    subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(application)], check=True,
                   stdout=subprocess.DEVNULL)
    return application


def publish(destination):
    destination = Path(destination).expanduser().resolve()
    target = destination/'workdir/eve_muhely'
    if target == SOURCE:
        raise SystemExit('Choose a destination outside this source folder.')
    ignored = shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.venv', '.git', 'node_modules', 'release-assets', 'test-results', '*.building.sqlite3')
    shutil.copytree(SOURCE, target, dirs_exist_ok=True, ignore=ignored)
    verified = 0
    for path in SOURCE.rglob('*'):
        if not path.is_file() or any(part in ['__pycache__', '.venv', '.git', 'node_modules', 'release-assets', 'test-results'] for part in path.parts) or path.name in ['.DS_Store'] or path.suffix == '.pyc':
            continue
        relative = path.relative_to(SOURCE)
        copied = target/relative
        if not copied.exists() or hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(copied.read_bytes()).digest():
            raise SystemExit('Copy verification failed: '+str(relative))
        verified += 1
    for name in ['Inditas.command', 'Telepites.command']:
        (target/name).chmod(0o755)
    root_launcher = destination/'EVE Muhely.command'
    root_launcher.write_text('''#!/bin/bash
set -e
eve_root="$(cd "$(dirname "$0")" && pwd)"
eve_local="$HOME/Applications/EVE Muhely.app/Contents/MacOS/EVE Muhely"
if [ -x "$eve_local" ]; then exec "$eve_local" "$@"; fi
exec "$eve_root/EVE Muhely.app/Contents/MacOS/EVE Muhely" "$@"
''')
    root_launcher.chmod(0o755)
    shutil.copy2(SOURCE/'Hasznalat.md', destination/'EVE Muhely - Hasznalat.md')
    build_app(destination/'EVE Muhely.app')
    print(f'Published {verified} verified files to {target}')
    print(f'Launcher: {destination / "EVE Muhely.app"}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    parser.add_argument('--install-local', action='store_true')
    args=parser.parse_args()
    publish(args.destination)
    if args.install_local:
        local=Path.home()/'Applications/EVE Muhely.app'
        if local.exists():
            existing=plistlib.loads((local/'Contents/Info.plist').read_bytes())
            if existing.get('CFBundleIdentifier') != 'hu.eve.muhely.local':
                raise SystemExit('A different application already exists at '+str(local))
        build_app(local)
        shortcut=Path.home()/'Desktop/EVE Műhely.app'
        if shortcut.exists() or shortcut.is_symlink():
            if not shortcut.is_symlink() or shortcut.resolve() not in [(args.destination/'EVE Muhely.app').resolve(), local.resolve()]:
                raise SystemExit('An unrelated desktop item was not overwritten: '+str(shortcut))
            shortcut.unlink()
        shortcut.symlink_to(local, target_is_directory=True)
        print('Installed local app and Desktop shortcut: '+str(local))
