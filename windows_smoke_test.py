"""Recipient-run diagnostics using an isolated temporary profile, never real tokens."""
import argparse
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import threading
import time
import urllib.request
import http.cookiejar


def check(online=False):
    if sys.platform!='win32' or struct.calcsize('P')!=8:raise RuntimeError('64 bites Windows Python szukseges.')
    import certifi
    os.environ['SSL_CERT_FILE']=certifi.where()
    from muhely import __version__
    from muhely.server import App,Server,ROOT
    from muhely.esi import Vault,Transport
    from muhely.windows_security import transform
    assert transform(transform(b'Windows DPAPI\0roundtrip'),decrypt=True)==b'Windows DPAPI\0roundtrip'
    with tempfile.TemporaryDirectory(prefix='eve-windows-test-') as folder:
        folder=Path(folder);app=App(folder,ROOT/'data/catalog.sqlite3',0)
        assert not app.store.characters() and not app.store.plans()
        assert app.store.settings()['client_id']
        # Dummy credentials in a disposable profile only.
        vault=Vault(folder);vault.set(1,{'test':'disposable'})
        assert Vault(folder).read()=={'1':{'test':'disposable'}}
        assert (folder/'vault.key.dpapi').exists() and not (folder/'vault.key').exists()
        server=Server(app);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base=app.origin;jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
            opener.open(base+'/').read()
            state=json.load(opener.open(base+'/api/state'))
            assert not state['characters'] and not state['plans']
            for script in ['numbers.js','tables.js','app.js']:
                assert opener.open(base+'/'+script).read()
            plan=json.load(opener.open(base+'/api/plan?product_id=16678&quantity=100000000&manufacturer_id=manual'))
            assert plan['quantity']==100000000 and plan['queue']
            assert plan['blueprint_shortages']
            request=urllib.request.Request(base+'/api/plans/save',data=json.dumps({'product_id':16678,'quantity':100000000,'manufacturer_id':0}).encode(),
                headers={'Content-Type':'application/json','Origin':base,'X-CSRF-Token':state['csrf']},method='POST')
            assert json.load(opener.open(request))['ok']
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
    if online:
        metadata,_=Transport().request('https://login.eveonline.com/.well-known/oauth-authorization-server')
        assert metadata['issuer'].startswith('https://login.eveonline.com')
    return {'version':__version__,'windows_x64':True,'python':sys.version.split()[0],
        'empty_profile':True,'dpapi':True,'http_api':True,'large_reaction':True,'plan_save':True,'https':online}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--online',action='store_true');args=parser.parse_args()
    print(json.dumps(check(args.online),ensure_ascii=False))
