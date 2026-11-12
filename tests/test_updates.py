import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import plistlib
import sqlite3
import stat
import tempfile
import time
import unittest
from unittest.mock import patch, Mock
import urllib.error
import zipfile
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
# A fixed old-client fixture keeps upgrade/rollback cases stable across releases.
FIXTURE_CURRENT_VERSION = '1.8.0'
from muhely.store import Store
from muhely.updates import Updates, UpdateError, REPO, canonical, verify_document, strict_json, installation, asset_valid, atomic_json
from muhely.update_install import extract_archive, payload_version, replace_application, backup_database, launch_helper, wait_process, ticket_folder

class UpdateTests(unittest.TestCase):
    def setUp(self):
        baseline=patch('muhely.updates.__version__',FIXTURE_CURRENT_VERSION);baseline.start();self.addCleanup(baseline.stop)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.store=Store(self.root/'profile');self.private=Ed25519PrivateKey.generate();self.key=self.private.public_key()
        self.bytes=b'verified archive';self.now=time.time()
        self.payload={'schema':1,'version':'1.9.0','notes_url':REPO+'/releases/tag/v1.9.0','assets':{}}
        for platform,suffix in [('macos-arm64','macOS-AppleSilicon-update.zip'),('windows-x64','Windows11-x64.zip')]:
            name='EVE_Muhely-1.9.0-'+suffix
            self.payload['assets'][platform]={'name':name,'url':REPO+'/releases/download/v1.9.0/'+name,'size':len(self.bytes),'sha256':hashlib.sha256(self.bytes).hexdigest()}
        self.doc=self.sign(self.payload)
    def sign(self,p):return {'payload':p,'signature':base64.b64encode(self.private.sign(canonical(p))).decode()}
    def manager(self,opener=None):
        target=self.root/'application';target.mkdir(exist_ok=True)
        return Updates(self.store,clock=lambda:self.now,opener=opener,key=self.key,install=(target.resolve(),'windows-x64'))
    def done(self,m):
        for _ in range(200):
            if not m.busy:return m.snapshot()
            time.sleep(.01)
        self.fail('update worker did not finish')
    def archive(self,entries):
        path=self.root/('archive-'+str(time.time_ns())+'.zip')
        with zipfile.ZipFile(path,'w') as z:
            for name,data,*mode in entries:
                info=zipfile.ZipInfo(name);info.create_system=3
                info.external_attr=(mode[0] if mode else stat.S_IFREG|0o644)<<16
                z.writestr(info,data)
        return path
    def windows(self,path,v='1.8.0'):
        for name in ['EVE_Muhely.exe','runtime/pythonw.exe','app/windows_desktop.py','app/muhely/updates.py']:
            p=path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('old')
        (path/'app/muhely/__init__.py').write_text("__version__ = '"+v+"'\n")
        return path
    def test_verifies_pinned_key_and_rejects_tampering(self):
        self.assertEqual(verify_document(self.doc,self.key)['version'],'1.9.0')
        for change in [lambda p:p.update(version='2.0.0'),lambda p:p['assets']['windows-x64'].update(url='https://evil.example/evil.zip'),lambda p:p['assets']['windows-x64'].update(sha256='a'*64)]:
            doc=copy.deepcopy(self.doc);change(doc['payload'])
            with self.assertRaisesRegex(UpdateError,'invalid_signature'):verify_document(doc,self.key)
        with self.assertRaisesRegex(UpdateError,'invalid_signature'):verify_document(self.doc,Ed25519PrivateKey.generate().public_key())
    def test_signed_metadata_still_requires_exact_repository_and_asset_names(self):
        for field,value in [('url',REPO+'.evil/releases/download/v1.9.0/EVE_Muhely-1.9.0-Windows11-x64.zip'),('url',REPO+'/releases/download/v1.9.0/../evil.zip'),('name','../other.zip'),('size',True),('size',2**40),('sha256','NaN')]:
            p=copy.deepcopy(self.payload);p['assets']['windows-x64'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(UpdateError):verify_document(self.sign(p),self.key)
    def test_prereleases_invalid_versions_and_extra_fields_rejected(self):
        for v in ['1.9.0-beta','01.9.0','1.9','1.9.0.1',9]:
            p=copy.deepcopy(self.payload);p['version']=v
            with self.assertRaises(UpdateError):verify_document(self.sign(p),self.key)
        p=copy.deepcopy(self.payload);p['command']='calc.exe'
        with self.assertRaises(UpdateError):verify_document(self.sign(p),self.key)
    def test_strict_json_rejects_duplicate_keys_and_nonfinite_numbers(self):
        for raw in [b'{"payload":1,"payload":2}',b'{"a":NaN}',b'{"a":Infinity}',b'\xff']:
            with self.assertRaises(UpdateError):strict_json(raw)
    def test_daily_check_manual_override_and_opt_out_persist(self):
        opened=[]
        def fetch(*a,**k):opened.append(a);return io.BytesIO(json.dumps(self.doc).encode())
        m=self.manager(fetch);self.assertTrue(self.done_after(m,'check',False)['available']);self.assertEqual(len(opened),1)
        m.request('check',False);self.assertEqual(len(opened),1)
        self.done_after(m,'check',True);self.assertEqual(len(opened),2)
        m.configure({'automatic':False});self.now+=86401;m.request('check',False);self.assertEqual(len(opened),2)
        self.assertFalse(self.manager(fetch).automatic)
        self.done_after(m,'check',True);self.assertEqual(len(opened),3)
    def done_after(self,m,action,manual=True):m.request(action,manual);return self.done(m)
    def test_404_is_unpublished_not_proof_of_latest_version(self):
        def fetch(*a,**k):raise urllib.error.HTTPError(REPO,404,'not found',{},None)
        m=self.manager(fetch);self.assertEqual(self.done_after(m,'check')['phase'],'unpublished')
    def test_network_failure_keeps_verified_available_update(self):
        m=self.manager(lambda *a,**k:io.BytesIO(json.dumps(self.doc).encode()));self.done_after(m,'check')
        def fail(*a,**k):raise OSError('network down')
        m.open=fail;d=self.done_after(m,'check');self.assertTrue(d['available']);self.assertEqual(d['error'],'update_network_error')
        self.assertTrue(self.manager().snapshot()['available'])
    def test_replayed_older_feed_never_replaces_cached_newer_feed(self):
        m=self.manager();m.document=self.doc;p=copy.deepcopy(self.payload);p['version']='1.8.1';p['notes_url']=REPO+'/releases/tag/v1.8.1'
        for a in p['assets'].values():
            a['name']=a['name'].replace('1.9.0','1.8.1');a['url']=a['url'].replace('1.9.0','1.8.1')
        m.open=lambda *a,**k:io.BytesIO(json.dumps(self.sign(p)).encode());d=self.done_after(m,'check');self.assertEqual(d['error'],'older_update');self.assertEqual(d['latest_version'],'1.9.0')
    def test_download_checks_size_hash_and_receipt_no_install_yet(self):
        m=self.manager(lambda *a,**k:io.BytesIO(self.bytes));m.document=self.doc
        d=self.done_after(m,'download');self.assertEqual(d['phase'],'ready');self.assertRegex(d['ticket'],'^[a-f0-9]{32}$')
        receipt=json.loads((m.cache/d['ticket']/'receipt.json').read_text());self.assertEqual(receipt['document'],self.doc)
        self.assertEqual(list(m.target.iterdir()),[]);self.assertEqual(d['progress'],100)
    def test_truncated_modified_and_oversize_downloads_never_produce_ticket(self):
        for content in [self.bytes[:-1],b'x'*len(self.bytes),self.bytes+b'extra']:
            m=self.manager(lambda *a,**k:io.BytesIO(content));m.document=self.doc
            d=self.done_after(m,'download');self.assertEqual(d['phase'],'error');self.assertIsNone(d['ticket']);self.assertEqual(d['error'],'invalid_archive')
    def test_source_checkout_and_wrong_roots_never_self_replace(self):
        with self.assertRaises(UpdateError):installation('/usr/bin/python3','darwin',False)
        with self.assertRaises(UpdateError):installation('/tmp/runtime/pythonw.exe','win32')
        target=self.windows(self.root/'win');self.assertEqual(installation(target/'runtime/pythonw.exe','win32'),(target.resolve(),'windows-x64'))
    def test_unsafe_ticket_and_child_source_paths_are_rejected(self):
        for token in ['../profile','a'*31,'A'*32,'a'*32+'/file',None]:
            with self.assertRaises(UpdateError):ticket_folder(self.store.folder,token)
    def test_archive_preserves_executable_mode_and_internal_mac_symlinks(self):
        a=self.archive([('EVE Muhely.app/Contents/Frameworks/A/Versions/A/bin',b'bin',stat.S_IFREG|0o755),('EVE Muhely.app/Contents/Frameworks/A/Versions/Current',b'A',stat.S_IFLNK|0o777)])
        root=extract_archive(a,self.root/'extract','macos-arm64')
        self.assertTrue((root/'Contents/Frameworks/A/Versions/Current').is_symlink())
        self.assertEqual((root/'Contents/Frameworks/A/Versions/Current/bin').read_bytes(),b'bin')
        self.assertTrue((root/'Contents/Frameworks/A/Versions/A/bin').stat().st_mode&0o100)
    def test_archive_rejects_traversal_absolute_drive_and_case_alias_paths(self):
        for name in ['../outside','/EVE Muhely/file','EVE Muhely/../outside','EVE Muhely/a/./b','EVE Muhely/C:file','EVE Muhely/a\\b','other/file']:
            a=self.archive([(name,b'x')])
            with self.subTest(name=name),self.assertRaises(UpdateError):extract_archive(a,self.root/str(time.time_ns()),'windows-x64')
        a=self.archive([('EVE Muhely/A',b'a'),('EVE Muhely/a',b'b')])
        with self.assertRaises(UpdateError):extract_archive(a,self.root/'alias','windows-x64')
    def test_archive_rejects_escaping_symlinks_and_symlink_parent_writes(self):
        for entries in [[('EVE Muhely.app/a',b'../../outside',stat.S_IFLNK|0o777)],[('EVE Muhely.app/a',b'/tmp',stat.S_IFLNK|0o777)],[('EVE Muhely.app/a',b'b',stat.S_IFLNK|0o777),('EVE Muhely.app/a/overwrite',b'x')]]:
            a=self.archive(entries)
            with self.assertRaises(UpdateError):extract_archive(a,self.root/str(time.time_ns()),'macos-arm64')
    def test_windows_symlinks_and_device_nodes_are_rejected(self):
        for mode in [stat.S_IFLNK|0o777,stat.S_IFCHR|0o600]:
            a=self.archive([('EVE Muhely/unsafe',b'elsewhere',mode)])
            with self.assertRaises(UpdateError):extract_archive(a,self.root/str(time.time_ns()),'windows-x64')
    def test_swap_is_whole_directory_and_preserves_old_copy(self):
        old=self.windows(self.root/'old');new=self.windows(self.root/'new','1.9.0');(new/'EVE_Muhely.exe').write_text('new')
        previous=replace_application(old,new,'windows-x64');self.assertEqual((old/'EVE_Muhely.exe').read_text(),'new');self.assertEqual((previous/'EVE_Muhely.exe').read_text(),'old')
    def test_failed_swap_restores_original_without_touching_profile(self):
        old=self.windows(self.root/'old');new=self.windows(self.root/'new','1.9.0');original=os.replace;calls=[]
        def replace(src,dst):
            calls.append((src,dst))
            if len(calls)==2:raise PermissionError('file locked')
            return original(src,dst)
        with patch('muhely.update_install.os.replace',side_effect=replace),self.assertRaises(PermissionError):replace_application(old,new,'windows-x64')
        self.assertEqual((old/'EVE_Muhely.exe').read_text(),'old');self.assertTrue(self.store.path.exists())
    def test_backup_contains_committed_data_and_never_moves_credentials(self):
        self.store.save_settings({'updates':{'automatic':False}});secret=self.store.folder/'characters.enc';secret.write_bytes(b'untouched')
        backup=backup_database(self.store.folder)
        with sqlite3.connect(backup) as db:self.assertIn('updates',[r[0] for r in db.execute('select key from settings')])
        self.assertEqual(secret.read_bytes(),b'untouched');self.assertEqual(backup.stat().st_mode&0o777,0o600)
    def test_backup_closes_both_sqlite_connections_before_return(self):
        connections=[];connect=sqlite3.connect
        def tracked(*args,**kwargs):
            db=connect(*args,**kwargs);connections.append(db);return db
        with patch('muhely.update_install.sqlite3.connect',side_effect=tracked):
            backup=backup_database(self.store.folder)
        self.assertEqual(len(connections),2)
        for db in connections:
            with self.assertRaisesRegex(sqlite3.ProgrammingError,'closed'):db.execute('select 1')
        # Also immediately rename/delete the backup, as the Windows test does.
        renamed=backup.with_suffix('.moved');backup.rename(renamed);renamed.unlink()

    def test_payload_version_is_read_without_executing_source(self):
        root=self.windows(self.root/'new','1.9.0');payload_version(root,'windows-x64','1.9.0')
        with self.assertRaises(UpdateError):payload_version(root,'windows-x64','2.0.0')
    def test_wait_never_terminates_a_process_and_timeout_prevents_swap(self):
        with patch('muhely.update_install.sys.platform','darwin'),patch('muhely.update_install.os.kill') as kill,self.assertRaisesRegex(UpdateError,'update_close_timeout'):wait_process(987654,timeout=.001)
        self.assertTrue(all(call.args[1]==0 for call in kill.call_args_list))
    def test_invalid_preferences_and_closed_manager(self):
        m=self.manager()
        for body in [{'automatic':1},{'automatic':True,'url':'evil'},{}]:
            with self.assertRaises(UpdateError):m.configure(body)
        m.close();self.assertFalse(m.request('check')['busy'])


class RestartAndInstallTests(unittest.TestCase):
    setUp=UpdateTests.setUp
    sign=UpdateTests.sign
    windows=UpdateTests.windows
    archive=UpdateTests.archive
    def test_restart_requires_exact_new_version_from_our_loopback_service(self):
        from muhely.update_install import verify_restart
        response=io.BytesIO(b'{"app":"eve-muhely","version":"1.9.0"}')
        with patch('urllib.request.build_opener') as factory:
            factory.return_value.open.return_value=response
            verify_restart('http://127.0.0.1:8765','1.9.0',timeout=.1)
        with patch('urllib.request.build_opener') as factory:
            factory.return_value.open.side_effect=lambda *a,**k:io.BytesIO(b'{"app":"eve-muhely","version":"1.8.0"}')
            with self.assertRaisesRegex(UpdateError,'update_restart_failed'):verify_restart('http://127.0.0.1:8765','1.9.0',timeout=.01)
    def test_whole_install_revalidates_archive_waits_both_processes_and_backs_up(self):
        from muhely.update_install import apply_update
        target=self.windows(self.root/'target');folder=self.store.folder/'updates'/('a'*32);folder.mkdir(parents=True)
        entries=[('EVE Muhely/'+p,b'new') for p in ['EVE_Muhely.exe','runtime/pythonw.exe','app/windows_desktop.py','app/muhely/updates.py']]
        entries.append(('EVE Muhely/app/muhely/__init__.py',b"__version__='1.9.0'\n"))
        archive=self.archive(entries);(folder/'archive.zip').write_bytes(archive.read_bytes())
        p=copy.deepcopy(self.payload);p['assets']['windows-x64'].update(size=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        atomic_json(folder/'receipt.json',{'document':self.sign(p),'platform':'windows-x64','target':str(target),'backend_pid':12345,'created':time.time(),'current_version':FIXTURE_CURRENT_VERSION})
        atomic_json(folder/'handoff.json',{'parent_pid':23456,'profile':str(self.store.folder),'origin':'http://127.0.0.1:8765'})
        with patch('muhely.updates.trust_key',return_value=self.key),patch('muhely.update_install.wait_process') as wait,patch('muhely.update_install.subprocess.Popen') as start,patch('muhely.update_install.verify_restart') as healthy:
            self.assertEqual(apply_update(folder),0)
            self.assertEqual([c.args[0] for c in wait.call_args_list],[23456,12345]);start.assert_called_once();healthy.assert_called_once_with('http://127.0.0.1:8765','1.9.0')
        result=json.loads((folder.parent/'last-result.json').read_text());self.assertEqual(result['phase'],'installed');self.assertTrue(Path(result['backup']).exists());self.assertTrue(Path(result['previous']).exists());self.assertEqual((target/'EVE_Muhely.exe').read_bytes(),b'new')
    def test_windows_reserved_device_and_trailing_dot_aliases_are_rejected(self):
        for name in ['CON','NUL.txt','COM1','LPT9.bin','name.','name ']:
            a=self.archive([('EVE Muhely/'+name,b'x')])
            with self.assertRaises(UpdateError):extract_archive(a,self.root/str(time.time_ns()),'windows-x64')

if __name__=='__main__':unittest.main()
