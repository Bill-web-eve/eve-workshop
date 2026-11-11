"""Regression checks for the concrete CodeQL report boundaries."""
import contextlib
import io
import unittest
from unittest.mock import Mock,patch
from muhely.server import Handler
import desktop


class ResponseHeaderTests(unittest.TestCase):
    def handler(self):
        handler=Handler.__new__(Handler)
        handler.send_response=Mock();handler.send_header=Mock();handler.end_headers=Mock();handler.wfile=io.BytesIO()
        return handler

    def test_invalid_headers_fail_before_any_response_is_written(self):
        for kwargs in [
            {'content_type':'text/plain\r\nX-Injected: true'},
            {'content_type':'text/plain\n\nsecond response'},
            {'content_type':'text/plain\x00'},
            {'content_type':None},
            {'headers':{'Location':'/ok\r\nSet-Cookie: stolen=1'}},
            {'headers':{'X-Test\r\nInjected':'yes'}},
            {'headers':{'X:Test':'yes'}},
            {'headers':{'X-Test':'bad\x7fvalue'}},
            {'headers':{'Location':'/snowman-\u2603'}},
        ]:
            handler=self.handler()
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):handler.send(200,{'ok':True},**kwargs)
            handler.send_response.assert_not_called();handler.send_header.assert_not_called()
            self.assertEqual(handler.wfile.getvalue(),b'')

    def test_valid_ics_disposition_and_encoded_redirect_are_preserved(self):
        handler=self.handler()
        handler.send(200,'BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n','text/calendar; charset=utf-8',headers={'Content-Disposition':'attachment; filename="eve-moon-extractions.ics"'})
        handler.send_header.assert_any_call('Content-Type','text/calendar; charset=utf-8')
        handler.send_header.assert_any_call('Content-Disposition','attachment; filename="eve-moon-extractions.ics"')
        self.assertIn(b'BEGIN:VCALENDAR',handler.wfile.getvalue())
        handler=self.handler();handler.send(303,b'',headers={'Location':'/callback?value=%0D%0A'})
        handler.send_header.assert_any_call('Location','/callback?value=%0D%0A')


class SsoDiagnosticTests(unittest.TestCase):
    def check(self,issuer):
        catalog=Mock(recipes={92822:None},pi_schematics={66:None})
        with patch('sys.argv',['desktop.py','--self-test']),patch('muhely.catalog.Catalog',return_value=catalog),patch('muhely.esi.Transport.request',return_value=({'issuer':issuer},{})),contextlib.redirect_stdout(io.StringIO()):
            desktop.main()

    def test_expected_sso_issuer_in_diagnostic(self):
        for issuer in ['https://login.eveonline.com','https://login.eveonline.com/']:
            with self.subTest(issuer=issuer):self.check(issuer)

    def test_diagnostic_rejects_prefix_spoofs_paths_credentials_and_wrong_schemes(self):
        for issuer in ['https://login.eveonline.com.evil.example','https://login.eveonline.com@evil.example',
                       'https://login.eveonline.com/evil','http://login.eveonline.com','https://login.eveonline.com:8443',None]:
            with self.subTest(issuer=issuer),self.assertRaises(AssertionError):self.check(issuer)


if __name__=='__main__':unittest.main()
