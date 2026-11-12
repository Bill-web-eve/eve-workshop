"""Exercise a signed Windows update with copied runtimes and disposable data.
No real signing key, user profile, EVE window or published release is involved.
"""
import base64
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from muhely import __version__
from muhely.updates import REPO,canonical,atomic_json
from muhely.store import Store

def check():
    if sys.platform!='win32':raise RuntimeError('Windows required')
    package=Path(sys.executable).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix='eve-signed-update-') as tmp:
        root=Path(tmp);old=root/'EVE Muhely';profile=root/'profile';store=Store(profile)
        store.save_settings({'update_fixture':'preserved'})
        (profile/'characters.enc').write_bytes(b'opaque synthetic credential fixture')
        shutil.copytree(package/'runtime',old/'runtime');shutil.copytree(package/'app',old/'app')
        key=Ed25519PrivateKey.generate()
        pub=base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
        atomic_json(old/'app/data/update-public-key.json',{'ed25519':pub})
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        new_version='9999.0.0'
        # A tiny synthetic launcher serves the health handshake, not the real app.
        cs=root/'Launcher.cs'
        body=json.dumps({'app':'eve-muhely','version':new_version})
        response='HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body.encode()))+'\r\nConnection: close\r\n\r\n'+body
        source='using System;using System.IO;using System.Net;using System.Net.Sockets;using System.Text;class Launcher{static void Main(){File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"restarted.txt"),"yes");var listener=new TcpListener(IPAddress.Loopback,'+str(port)+');listener.Start();using(var client=listener.AcceptTcpClient()){var stream=client.GetStream();stream.Read(new byte[8192],0,8192);var response=Encoding.UTF8.GetBytes('+json.dumps(response)+');stream.Write(response,0,response.Length);}listener.Stop();}}'
        cs.write_text(source)
        csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        subprocess.run([str(csc),'/nologo','/target:winexe','/out:'+str(old/'EVE_Muhely.exe'),str(cs)],check=True,capture_output=True)
        ticket='a'*32;folder=profile/'updates'/ticket;folder.mkdir(parents=True)
        archive=folder/'archive.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
            z.write(old/'EVE_Muhely.exe','EVE Muhely/EVE_Muhely.exe')
            for name in ['runtime/pythonw.exe','app/windows_desktop.py','app/muhely/updates.py']:z.writestr('EVE Muhely/'+name,b'fixture')
            z.writestr('EVE Muhely/app/muhely/__init__.py',"__version__ = '"+new_version+"'\n")
        assets={}
        for platform,suffix in [('macos-arm64','macOS-AppleSilicon-update.zip'),('windows-x64','Windows11-x64.zip')]:
            name='EVE_Muhely-'+new_version+'-'+suffix
            assets[platform]={'name':name,'url':REPO+'/releases/download/v'+new_version+'/'+name,'size':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
        payload={'schema':1,'version':new_version,'notes_url':REPO+'/releases/tag/v'+new_version,'assets':assets}
        document={'payload':payload,'signature':base64.b64encode(key.sign(canonical(payload))).decode()}
        coordinator=old/'app/update_coordinator.py'
        coordinator.write_text('''import os,subprocess,sys,time
from pathlib import Path
from muhely.update_install import launch_helper
from muhely.updates import atomic_json
import json
profile=Path(sys.argv[1]);folder=profile/'updates'/('a'*32)
receipt=json.loads((folder/'receipt.json').read_text())
backend=subprocess.Popen([sys.executable,'-c','import time;time.sleep(2)'])
receipt['backend_pid']=backend.pid
atomic_json(folder/'receipt.json',receipt)
launch_helper(profile,'a'*32,sys.argv[2],os.getpid())
''')
        atomic_json(folder/'receipt.json',{'document':document,'platform':'windows-x64','target':str(old.resolve()),'backend_pid':1,'created':time.time(),'current_version':__version__})
        subprocess.run([str(old/'runtime/python.exe'),'-I',str(coordinator),str(profile),'http://127.0.0.1:'+str(port)],check=True,timeout=45,capture_output=True,cwd=str(old))
        result=profile/'updates/last-result.json'
        for _ in range(200):
            if result.exists() and json.loads(result.read_text()).get('phase')=='installed' and (old/'restarted.txt').exists():break
            if result.exists() and not json.loads(result.read_text()).get('ok'):
                raise AssertionError(result.read_text()+'\n'+(folder/'install.log').read_text(errors='replace')[-4000:])
            time.sleep(.1)
        else:raise AssertionError('Update did not finish: '+((folder/'install.log').read_text(errors='replace')[-4000:] if (folder/'install.log').exists() else 'no helper log'))
        status=json.loads(result.read_text());assert status['ok'] and status['version']==new_version
        assert (old/'app/muhely/__init__.py').read_text().find(new_version)>0
        assert Path(status['previous']).exists() and Path(status['backup']).exists()
        assert (profile/'characters.enc').read_bytes()==b'opaque synthetic credential fixture'
        assert Store(profile).settings()['update_fixture']=='preserved'
        with closing(sqlite3.connect(status['backup'])) as db:assert db.execute("select value from settings where key='update_fixture'").fetchone()[0]=='"preserved"'
        # Detached helper can finish releasing its copied DLLs after marker write.
        for _ in range(60):
            try:shutil.rmtree(folder/'helper');break
            except PermissionError:time.sleep(.1)
        return {'signed_update':True,'copied_runtime':True,'process_exit_wait':True,'whole_app_swap':True,'restart':True,'profile_preserved':True,'database_backup':True,'old_copy_retained':True}
if __name__=='__main__':print(json.dumps(check()),flush=True)
