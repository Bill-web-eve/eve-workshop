import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from muhely.windows_window import WindowHost,local_url,external_url,file_payload,intel_url


class WindowsWindowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.webview=Mock();self.host=WindowHost(self.webview,'http://127.0.0.1:8765',self.tmp.name)
        self.window=Mock();self.host.main=self.window

    def test_bridge_requires_exact_loopback_origin(self):
        self.assertTrue(local_url('http://127.0.0.1:8765/?intel_window=map',self.host.origin))
        for url in ['http://127.0.0.1:8766','https://127.0.0.1:8765','http://127.0.0.1.evil:8765','http://user@127.0.0.1:8765','file:///tmp/local','javascript:alert(1)','http://127.0.0.1:bad']:
            with self.subTest(url=url):
                self.assertFalse(local_url(url,self.host.origin))
                with self.assertRaises(ValueError):self.host.dispatch(self.window,url,{'action':'activate'})

    def test_child_window_cannot_save_files_send_notifications_or_quit_app(self):
        for action in ['save','chooseIntelFolder','notify','requestNotifications','stopped','quitCheck','intelOverlayStatus','configureIntelOverlay','syncIntelOverlay']:
            with self.subTest(action=action),self.assertRaises(ValueError):self.host.dispatch(Mock(),self.host.origin,{'action':action})

    def test_external_links_exclude_file_scripts_credentials_and_control_characters(self):
        self.assertTrue(external_url('https://zkillboard.com/character/359618261/'))
        self.assertTrue(external_url('http://127.0.0.1:8765/desktop/auth/one-use-ticket'))
        for url in ['file:///C:/Windows/test.exe','javascript:alert(1)','https://user:password@host/','https://host/\nvalue',None]:
            self.assertFalse(external_url(url))
        with patch('muhely.windows_window.webbrowser.open') as browser:
            for url in ['file:///private','javascript:bad']:
                with self.assertRaises(ValueError):self.host.dispatch(self.window,self.host.origin,{'action':'external','url':url})
            browser.assert_not_called()

    def test_save_uses_native_selection_and_preserves_exact_utf8_content(self):
        path=Path(self.tmp.name)/'export.csv';data='\ufeffFerrofluid;25\r\n'.encode()
        self.window.create_file_dialog.return_value=(str(path),)
        body={'action':'save','filename':'materials.csv','base64':base64.b64encode(data).decode()}
        self.assertEqual(self.host.dispatch(self.window,self.host.origin,body),{'saved':True})
        self.assertEqual(path.read_bytes(),data)
        self.window.create_file_dialog.return_value=None
        self.assertEqual(self.host.dispatch(self.window,self.host.origin,body),{'saved':False})

    def test_bulk_moon_json_uses_native_save_without_changing_encoding(self):
        path=Path(self.tmp.name)/'moons.json';data=b'{"format":"eve-workshop-moons","version":1,"moons":[{"moon_id":1},{"moon_id":2}]}\n'
        self.window.create_file_dialog.return_value=(str(path),)
        body={'action':'save','filename':'eve-moons.json','base64':base64.b64encode(data).decode()}
        self.assertEqual(self.host.dispatch(self.window,self.host.origin,body),{'saved':True})
        self.assertEqual(path.read_bytes(),data)

    def test_save_rejects_paths_executables_and_bad_base64_before_showing_dialog(self):
        for patch_value in [{'filename':'../tokens.txt'},{'filename':'C:\\private.txt'},{'filename':'run.exe'},{'base64':'not base64'}]:
            body={'filename':'test.csv','base64':'YQ==',**patch_value}
            with self.subTest(body=body),self.assertRaises(ValueError):file_payload(body)
        self.window.create_file_dialog.assert_not_called()

    def test_intel_options_are_allowlisted_and_never_become_arbitrary_urls(self):
        url=intel_url(self.host.origin,'map',{'character_id':123,'region':100,'history':True,'url':'https://evil.invalid','center':True})
        self.assertEqual(url,self.host.origin+'/?intel_window=map&character_id=123&region=100&history=1')
        with self.assertRaises(ValueError):intel_url(self.host.origin,'settings',{})

    def test_close_waits_for_dirty_and_running_confirmation_before_shutdown(self):
        self.host.quitting=True;self.window.create_confirmation_dialog.return_value=False
        with patch.object(self.host,'_script') as script:
            self.assertEqual(self.host.dispatch(self.window,self.host.origin,{'action':'quitCheck','dirty':True}),{'cancelled':True})
            script.assert_not_called();self.assertFalse(self.host.quitting)
            self.host.quitting=True;self.window.create_confirmation_dialog.return_value=True
            self.host.dispatch(self.window,self.host.origin,{'action':'quitCheck','running':True})
            script.assert_called_once_with(self.window,'void EveDesktop.shutdown()')

    def test_notifications_remain_opt_in_and_save_only_local_shell_preferences(self):
        self.assertEqual(self.host.dispatch(self.window,self.host.origin,{'action':'notificationStatus'}),{'status':'notDetermined'})
        with self.assertRaises(ValueError):self.host.dispatch(self.window,self.host.origin,{'action':'notify','title':'test','body':'body'})
        self.assertEqual(self.host.dispatch(self.window,self.host.origin,{'action':'requestNotifications'}),{'status':'authorized'})
        saved=json.loads((Path(self.tmp.name)/'windows-shell.json').read_text())
        self.assertEqual(set(saved),{'language','notifications'})
        self.assertTrue(WindowHost(self.webview,self.host.origin,self.tmp.name).notification_granted)

    def test_unknown_native_actions_and_non_dict_messages_are_rejected(self):
        for body in [{},[],{'action':'execute'},{'action':'selfTestResult'}]:
            with self.subTest(body=body),self.assertRaises(ValueError):self.host.dispatch(self.window,self.host.origin,body)

    def test_overlay_is_lazy_and_all_native_calls_use_main_ui_thread(self):
        with patch('desktop.stop_backend',return_value=True),patch('muhely.windows_overlay.NativeOverlay') as factory,patch.object(self.host,'_ui',side_effect=lambda window,fn:fn()) as ui:
            self.assertIsNone(self.host.overlay)
            self.host.dispatch(self.window,self.host.origin,{'action':'intelOverlayStatus'})
            factory.assert_called_once_with(self.host.folder,'dark','hu')
            factory.return_value.settings.assert_called_once()
            self.host.dispatch(self.window,self.host.origin,{'action':'configureIntelOverlay','options':{'editing':True}})
            factory.return_value.configure.assert_called_once_with({'editing':True})
            self.host.dispatch(self.window,self.host.origin,{'action':'syncIntelOverlay','data':{'enabled':False,'seconds':60,'items':[]}})
            factory.return_value.sync.assert_called_once_with({'enabled':False,'seconds':60,'items':[]})
            self.host.dispatch(self.window,self.host.origin,{'action':'stopped'})
            factory.return_value.dispose.assert_called_once()
            self.assertTrue(all(c.args[0] is self.window for c in ui.call_args_list))

if __name__=='__main__':unittest.main()
