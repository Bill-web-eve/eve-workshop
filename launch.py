#!/usr/bin/env python3
"""One-click local launcher; no global packages or system settings are changed."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('EVE_MUHELY_DATA', Path.home()/'Library/Application Support/EVE Muhely'))
URL = 'http://127.0.0.1:8765'


def ready():
    try:
        with urllib.request.urlopen(URL+'/health', timeout=1) as r:
            return json.load(r).get('app') == 'eve-muhely'
    except Exception:
        return False


def python_path(setup=False):
    venv = DATA/'runtime/bin/python3'
    if venv.exists():
        check = subprocess.run([str(venv), '-c', 'import cryptography'], capture_output=True)
        if check.returncode == 0:
            return str(venv)
    # The application can run manually without cryptography. EVE SSO needs it.
    check = subprocess.run([sys.executable, '-c', 'import cryptography'], capture_output=True)
    if check.returncode == 0:
        return sys.executable
    if not setup:
        print('Az első indításhoz telepítjük a belépéshez szükséges csomagot egy saját környezetbe.', flush=True)
    if not venv.exists():
        subprocess.run([sys.executable, '-m', 'venv', str(DATA/'runtime')], check=True)
    subprocess.run([str(venv), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(ROOT/'requirements.txt')], check=True)
    return str(venv)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        raise SystemExit('Python 3.9 vagy újabb szükséges: https://www.python.org/downloads/macos/')
    os.umask(0o077)
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.setup:
        python_path(True)
        print('A telepítés elkészült. Az Inditas.command fájllal indul az alkalmazás.')
        return
    if not ready():
        python = python_path()
        log = DATA/'server.log'
        # Keep the small local log bounded across launches; requests/tokens are not logged.
        if log.exists() and log.stat().st_size > 1024*1024:
            log.replace(DATA/'server.previous.log')
        with log.open('ab') as output:
            subprocess.Popen([python, str(ROOT/'run.py'), '--no-browser', '--data-dir', str(DATA)],
                             cwd=ROOT, stdout=output, stderr=output, start_new_session=True)
        for _ in range(100):
            if ready():
                break
            time.sleep(.2)
        else:
            raise SystemExit(f'Az alkalmazás nem indult el. A napló itt található: {log}')
    if not args.no_browser:
        webbrowser.open(URL)
    print('EVE Műhely: '+URL)


if __name__ == '__main__':
    main()
