import ctypes
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import Mock,patch
import zipfile
import sqlite3

from cryptography.fernet import Fernet
import desktop
import windows_desktop
from muhely.esi import Vault,EsiError
from muhely.store import default_data_dir
from muhely import windows_security
from tools.build_windows_release import pe_info,extract,stage
from tools.build_macos_release import audit_bundle
from muhely.catalog import Catalog,import_sde
from muhely.server import ROOT


class WindowsSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
    def fake(self,data,decrypt=False):
        if decrypt:
            if not data.startswith(b'PROTECTED:'):raise OSError('Wrong Windows user or corrupted key')
            return data[len(b'PROTECTED:'):]
        return b'PROTECTED:'+data

    def test_dpapi_marshalling_uses_current_user_flags_and_frees_output(self):
        buffers=[];flags=[]
        def protect(*args):
            incoming=args[0]._obj;outgoing=args[-1]._obj
            data=ctypes.string_at(incoming.pbData,incoming.cbData)
            flags.append(args[-2]);buffer=ctypes.create_string_buffer(b'protected:'+data);buffers.append(buffer)
            outgoing.cbData=len(b'protected:'+data);outgoing.pbData=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte))
            self.assertEqual(args[2]._obj.cbData,len(windows_security.ENTROPY))
            return 1
        crypt=Mock();crypt.CryptProtectData=Mock(side_effect=protect)
        kernel=Mock();kernel.LocalFree=Mock(return_value=None)
        with patch.object(windows_security.os,'name','nt'),patch.object(ctypes,'WinDLL',side_effect=[crypt,kernel],create=True):
            self.assertEqual(windows_security.transform(b'a\0b'),b'protected:a\0b')
        self.assertEqual(flags,[1]) # UI forbidden; machine-wide protection is never enabled.
        kernel.LocalFree.assert_called_once()

    def test_new_key_is_protected_and_reused_without_plaintext_file(self):
        key=Fernet.generate_key();generate=Mock(return_value=key)
        with patch.object(windows_security,'transform',side_effect=self.fake):
            self.assertEqual(windows_security.vault_key(self.folder,generate,lambda k:None),key)
            self.assertEqual(windows_security.vault_key(self.folder,generate,lambda k:None),key)
        generate.assert_called_once();self.assertFalse((self.folder/'vault.key').exists())
        self.assertTrue((self.folder/'vault.key.dpapi').read_bytes().startswith(b'PROTECTED:'))

    def test_existing_protected_key_failure_never_replaces_credentials(self):
        path=self.folder/'vault.key.dpapi';path.write_bytes(b'bad')
        with patch.object(windows_security,'transform',side_effect=self.fake):
            with self.assertRaises(OSError):windows_security.vault_key(self.folder,Fernet.generate_key,lambda k:None)
        self.assertEqual(path.read_bytes(),b'bad');self.assertFalse((self.folder/'vault.key').exists())

    def test_orphaned_encrypted_tokens_never_generate_a_new_key(self):
        (self.folder/'characters.enc').write_bytes(b'keep')
        generate=Mock()
        with self.assertRaises(OSError):windows_security.vault_key(self.folder,generate,lambda k:None)
        generate.assert_not_called();self.assertEqual((self.folder/'characters.enc').read_bytes(),b'keep')

    def test_legacy_key_is_validated_and_migrated_before_plaintext_is_removed(self):
        key=Fernet.generate_key();(self.folder/'vault.key').write_bytes(key);validate=Mock()
        with patch.object(windows_security,'transform',side_effect=self.fake):
            self.assertEqual(windows_security.vault_key(self.folder,Fernet.generate_key,validate),key)
        validate.assert_called_once_with(key);self.assertFalse((self.folder/'vault.key').exists())
        self.assertTrue((self.folder/'vault.key.dpapi').exists())

    def test_invalid_legacy_key_does_not_overwrite_or_delete_anything(self):
        key=Fernet.generate_key();(self.folder/'vault.key').write_bytes(key)
        with self.assertRaises(ValueError):windows_security.vault_key(self.folder,Fernet.generate_key,Mock(side_effect=ValueError('bad key')))
        self.assertEqual((self.folder/'vault.key').read_bytes(),key)
        self.assertFalse((self.folder/'vault.key.dpapi').exists())

    def test_vault_windows_branch_encrypts_tokens_and_keeps_failures_closed(self):
        key=Fernet.generate_key()
        with patch('muhely.esi.sys.platform','win32'),patch.object(windows_security,'vault_key',return_value=key) as provider:
            Vault(self.folder).set(123,{'access_token':'private-test-token'})
            self.assertEqual(Vault(self.folder).read()['123']['access_token'],'private-test-token')
            self.assertEqual(provider.call_count,2)
        payload=(self.folder/'characters.enc').read_bytes();self.assertNotIn(b'private-test-token',payload)
        with patch('muhely.esi.sys.platform','win32'),patch.object(windows_security,'vault_key',side_effect=OSError('denied')):
            with self.assertRaises(EsiError):Vault(self.folder).set(123,{'access_token':'replacement'})
        self.assertEqual((self.folder/'characters.enc').read_bytes(),payload)
        self.assertFalse((self.folder/'vault.key').exists())


class WindowsDistributionTests(unittest.TestCase):
    def test_windows_data_directory_is_per_user_and_override_remains_supported(self):
        with patch('muhely.store.sys.platform','win32'),patch.dict(os.environ,{'LOCALAPPDATA':'/tmp/user-local'},clear=True):
            self.assertEqual(default_data_dir(),Path('/tmp/user-local/EVE Muhely'))
            with patch.dict(os.environ,{'EVE_MUHELY_DATA':'/tmp/custom-profile'}):
                self.assertEqual(default_data_dir(),Path('/tmp/custom-profile'))

    def test_windows_spawn_uses_background_flags_and_posix_keeps_session(self):
        with patch.object(desktop.sys,'platform','win32'),patch.object(desktop.subprocess,'CREATE_NO_WINDOW',0x08000000,create=True),patch.object(desktop.subprocess,'CREATE_NEW_PROCESS_GROUP',0x200,create=True):
            self.assertEqual(desktop.background_options(),{'creationflags':0x08000200})
            self.assertEqual(desktop.process_command(8765,Path('/tmp/profile'))[1:4],['-I','-X','utf8'])
        with patch.object(desktop.sys,'platform','darwin'):
            self.assertEqual(desktop.background_options(),{'start_new_session':True})

    def test_windowless_startup_errors_are_logged_and_streams_are_restored(self):
        with tempfile.TemporaryDirectory() as folder,patch('muhely.store.default_data_dir',return_value=Path(folder)),patch('muhely.windows_window.main',side_effect=RuntimeError('startup test')):
            original=windows_desktop.sys.stderr
            self.assertEqual(windows_desktop.main(),1)
            self.assertIs(windows_desktop.sys.stderr,original)
            self.assertIn('startup test',(Path(folder)/'launcher.log').read_text())

    def test_portable_stage_only_contains_allowlisted_app_and_public_defaults(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);stage(root,{'client_id':'public-only'});audit_bundle(root)
            for name in ['Hasznalat.md','UserGuide.en.md']:
                self.assertEqual((root/'app'/name).read_bytes(),(ROOT/name).read_bytes())
            self.assertEqual(json.loads((root/'app/data/defaults.json').read_text()),{'client_id':'public-only'})
            self.assertTrue((root/'app/windows_smoke_test.py').exists())
            self.assertFalse((root/'app/tests').exists())
            (root/'vault.key.dpapi').write_bytes(b'private')
            with self.assertRaises(RuntimeError):audit_bundle(root)

    def test_unsafe_dependency_archive_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            archive=Path(folder)/'unsafe.zip'
            for name in ['../escaped','/absolute','C:bad','folder\\bad']:
                with zipfile.ZipFile(archive,'w') as output:output.writestr(name,b'bad')
                with self.assertRaises(ValueError):extract(archive,Path(folder)/'out')

    def test_pe_audit_accepts_only_amd64_pe32_plus(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'app.exe';data=bytearray(512);data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,128)
            data[128:132]=b'PE\0\0';struct.pack_into('<H',data,132,0x8664);struct.pack_into('<H',data,152,0x20b);struct.pack_into('<H',data,220,2)
            file.write_bytes(data);self.assertEqual(pe_info(file)['subsystem'],2)
            struct.pack_into('<H',data,132,0xaa64);file.write_bytes(data)
            with self.assertRaises(ValueError):pe_info(file)

    def test_managed_anycpu_assemblies_are_allowed_but_32bit_required_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'managed.dll';data=bytearray(1024)
            data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,128);data[128:132]=b'PE\0\0'
            struct.pack_into('<HH',data,132,0x14c,1);struct.pack_into('<H',data,148,224)
            struct.pack_into('<H',data,152,0x10b);struct.pack_into('<H',data,220,2)
            struct.pack_into('<II',data,152+96+14*8,0x2000,72)
            struct.pack_into('<IIII',data,152+224+8,512,0x2000,512,512)
            struct.pack_into('<I',data,512+16,1);path.write_bytes(data)
            self.assertEqual(pe_info(path)['machine'],'AnyCPU')
            for flags in [0,3,0x20001]:
                struct.pack_into('<I',data,512+16,flags);path.write_bytes(data)
                with self.subTest(flags=flags),self.assertRaises(ValueError):pe_info(path)

    def test_x64_package_preserves_loader_search_directories_without_foreign_binaries(self):
        from tools.build_windows_release import trim_other_architectures
        with tempfile.TemporaryDirectory() as folder:
            packages=Path(folder)
            for arch in ['win-arm64','win-x86','win-x64']:
                path=packages/'webview/lib/runtimes'/arch/'native';path.mkdir(parents=True)
                (path/'WebView2Loader.dll').write_bytes(arch.encode())
            trim_other_architectures(packages)
            for arch in ['win-arm64','win-x86']:
                native=packages/'webview/lib/runtimes'/arch/'native'
                self.assertTrue(native.is_dir());self.assertTrue((native/'README.txt').is_file())
                self.assertFalse((native/'WebView2Loader.dll').exists())
            self.assertTrue((packages/'webview/lib/runtimes/win-x64/native/WebView2Loader.dll').is_file())
            archive=packages/'test.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for path in packages.rglob('README.txt'):z.write(path,path.relative_to(packages))
            with zipfile.ZipFile(archive) as z:
                self.assertIn('webview/lib/runtimes/win-arm64/native/README.txt',z.namelist())
                self.assertIn('webview/lib/runtimes/win-x86/native/README.txt',z.namelist())

    def test_catalog_read_connections_are_closed_for_windows_file_replacement(self):
        connect=sqlite3.connect;connections=[]
        def track(*args,**kwargs):
            db=connect(*args,**kwargs);connections.append(db);return db
        with patch('muhely.catalog.sqlite3.connect',side_effect=track):Catalog(ROOT/'data/catalog.sqlite3')
        self.assertTrue(connections)
        for db in connections:
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')

    def test_sde_import_closes_temporary_database_before_replacing_file(self):
        connect=sqlite3.connect;replace=os.replace;connections=[]
        def track(*args,**kwargs):
            db=connect(*args,**kwargs);connections.append(db);return db
        def check_replace(source,target):
            for db in connections:
                with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
            replace(source,target)
        with tempfile.TemporaryDirectory() as folder:
            archive=Path(folder)/'sde.zip';target=Path(folder)/'catalog.sqlite3'
            with zipfile.ZipFile(archive,'w') as output:
                output.writestr('_sde.jsonl',json.dumps({'_key':'sde','buildNumber':1,'releaseDate':'2026-10-16'}))
                types=[{'_key':34,'published':True,'name':{'en':'Material'}}]
                recipes=[]
                for i in range(1001):
                    types.extend({'_key':tid,'published':True,'name':{'en':str(tid)}} for tid in [10000+i,20000+i])
                    recipes.append({'blueprintTypeID':20000+i,'activities':{'manufacturing':{'materials':[{'typeID':34,'quantity':1}],'products':[{'typeID':10000+i,'quantity':1}]}}})
                output.writestr('groups.jsonl','')
                output.writestr('typeMaterials.jsonl','')
                output.writestr('types.jsonl','\n'.join(json.dumps(r) for r in types))
                output.writestr('blueprints.jsonl','\n'.join(json.dumps(r) for r in recipes))
            with patch('muhely.catalog.sqlite3.connect',side_effect=track),patch('muhely.catalog.os.replace',side_effect=check_replace):import_sde(archive,target)
            self.assertTrue(target.exists())
