import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch

import desktop
from muhely.store import Store
from tools.build_macos_release import public_config,audit_bundle


class CleanReleaseTests(unittest.TestCase):
    def test_distributable_seeds_only_public_client_id_into_empty_store(self):
        with tempfile.TemporaryDirectory() as folder:
            defaults=Path(folder)/'defaults.json'
            defaults.write_text(json.dumps({'client_id':'public-client','characters':[123],'plans':['private'],
                                           'source':'eve','inventory':{'34':100}}))
            with patch('muhely.store.BUNDLED_DEFAULTS',defaults):
                store=Store(Path(folder)/'user')
                self.assertEqual(store.settings()['client_id'],'public-client')
                self.assertEqual(store.settings()['source'],'manual')
                self.assertEqual(store.characters(),[]);self.assertEqual(store.plans(),[])
                self.assertEqual(store.mapping('inventory'),{})
                store.save_settings({'client_id':'own-client'})
                self.assertEqual(Store(Path(folder)/'user').settings()['client_id'],'own-client')
                self.assertFalse((store.folder/'characters.enc').exists())

    def test_build_config_never_copies_other_settings_and_rejects_bad_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'client.json';path.write_text(json.dumps({'client_id':'public123','client_secret':'DO-NOT-COPY'}))
            self.assertEqual(public_config(path),{'client_id':'public123'})
            for value in ['',None,123,'spaces not allowed']:
                path.write_text(json.dumps({'client_id':value}))
                with self.assertRaises(ValueError):public_config(path)

    def test_bundle_audit_rejects_private_database_and_tokens(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'defaults.json').write_text('{"client_id":"public123"}')
            audit_bundle(root)
            for name in ['muhely.sqlite3','characters.enc','server.log','Salvation.xlsx']:
                path=root/name;path.write_bytes(b'private')
                with self.assertRaises(RuntimeError):audit_bundle(root)
                path.unlink()

    def test_local_health_only_accepts_our_service_and_never_uses_a_proxy(self):
        for raw,valid in [(b'[]',False),(b'{"app":"other"}',False),(b'{"app":"eve-muhely"}',True),(b'not JSON',False)]:
            response=Mock();response.read.return_value=raw
            opener=Mock();opener.open.return_value.__enter__=Mock(return_value=response)
            opener.open.return_value.__exit__=Mock(return_value=False)
            with patch('desktop.urllib.request.build_opener',return_value=opener) as build:
                self.assertEqual(bool(desktop.health('http://127.0.0.1:8767')),valid)
                self.assertEqual(build.call_args.args[0].proxies,{})

    def test_frozen_launcher_spawns_bundled_executable_and_keeps_data_dir(self):
        with patch.object(desktop.sys,'frozen',True,create=True),patch.object(desktop.sys,'executable','/Applications/EVE Muhely.app/Contents/MacOS/EVE Muhely'):
            command=desktop.process_command(8766,Path('/tmp/eve clean'))
            self.assertEqual(command[0],'/Applications/EVE Muhely.app/Contents/MacOS/EVE Muhely')
            self.assertEqual(command[1:],[ '--serve','--no-browser','--port','8766','--data-dir','/tmp/eve clean'])

if __name__=='__main__':unittest.main()
