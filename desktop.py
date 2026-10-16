#!/usr/bin/env python3
"""Desktop entry point for self-contained macOS and Windows distributions."""
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


def health(url):
    try:
        # Local startup detection must not pass through a user's HTTP proxy.
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url+'/health',timeout=1) as response:
            result=json.load(response)
            return result if isinstance(result,dict) and result.get('app')=='eve-muhely' else None
    except (OSError,ValueError):return None


def process_command(port,folder):
    args=['--serve','--no-browser','--port',str(port),'--data-dir',str(folder)]
    if getattr(sys,'frozen',False):return [sys.executable,*args]
    if sys.platform=='win32':return [sys.executable,'-I','-X','utf8',str(Path(__file__).resolve()),*args]
    return [sys.executable,str(Path(__file__).resolve()),*args]


def background_options():
    if sys.platform=='win32':
        return {'creationflags':subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP}
    return {'start_new_session':True}


def main():
    parser=argparse.ArgumentParser(description='EVE Műhely')
    parser.add_argument('--serve',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--data-dir',type=Path)
    parser.add_argument('--self-test',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('A port 1024 és 65535 közé essen.')
    # Ship a trust store so HTTPS works on Macs without a Python installation.
    import certifi
    os.environ.setdefault('SSL_CERT_FILE',certifi.where())
    from muhely.server import App,Server,ROOT
    from muhely.store import default_data_dir
    from muhely import __version__
    folder=(args.data_dir or default_data_dir()).expanduser()
    if args.self_test:
        # No private data, Keychain write or local server needed for this check.
        import cryptography
        from cryptography.fernet import Fernet
        from muhely.catalog import Catalog
        from muhely.esi import Transport
        cipher=Fernet(Fernet.generate_key());assert cipher.decrypt(cipher.encrypt(b'EVE'))==b'EVE'
        catalog=Catalog(ROOT/'data/catalog.sqlite3')
        assert 92822 in catalog.recipes and 66 in catalog.pi_schematics
        assert (ROOT/'static/index.html').exists()
        # Verify certificate validation against the public EVE SSO service.
        metadata,_=Transport().request('https://login.eveonline.com/.well-known/oauth-authorization-server')
        assert metadata.get('issuer','').startswith('https://login.eveonline.com')
        result={'version':__version__,'architecture':__import__('platform').machine(),
                'python':__import__('platform').python_version(),'cryptography':cryptography.__version__,
                'recipes':len(catalog.recipes),'https_verified':True}
        print(json.dumps(result),flush=True);return
    os.umask(0o077)
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    catalog=folder/'catalog.sqlite3'
    if not catalog.exists():catalog=ROOT/'data/catalog.sqlite3'
    if args.serve:
        app=App(folder,catalog,args.port)
        server=Server(app)
        try:server.serve_forever()
        finally:server.server_close()
        return
    url=f'http://127.0.0.1:{args.port}'
    if not health(url):
        log=folder/'server.log'
        if log.exists() and log.stat().st_size>1024*1024:log.replace(folder/'server.previous.log')
        env=dict(os.environ)
        if getattr(sys,'frozen',False):
            # A new long-lived app instance must outlive this launcher process.
            env['PYINSTALLER_RESET_ENVIRONMENT']='1'
        with log.open('ab') as output:
            child=subprocess.Popen(process_command(args.port,folder),stdin=subprocess.DEVNULL,
                stdout=output,stderr=output,env=env,**background_options())
        for _ in range(100):
            if health(url):break
            if child.poll() is not None:raise RuntimeError('Az EVE Műhely nem indult el. Napló: '+str(log))
            time.sleep(.2)
        else:raise RuntimeError('Az EVE Műhely indítása túl sokáig tart. Napló: '+str(log))
    if not args.no_browser:webbrowser.open(url)


if __name__=='__main__':main()
