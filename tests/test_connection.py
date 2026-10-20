import base64
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock
import urllib.parse
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

from muhely.esi import EveConnection, Vault, EsiError, SCOPES, INDUSTRY_SCOPES, SKILL_SCOPES, SkillScopeError, verify_jwt, compatibility_date, Transport
from muhely.store import Store


def b64(value):return base64.urlsafe_b64encode(value).decode().rstrip('=')


class ConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = rsa.generate_private_key(public_exponent=65537,key_size=2048)
        public=cls.private.public_key().public_numbers()
        cls.jwks={'keys':[{'kid':'unit-test','kty':'RSA','alg':'RS256',
                           'e':b64(public.e.to_bytes(3,'big')),
                           'n':b64(public.n.to_bytes(256,'big'))}]}

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name);self.store.save_settings({'client_id':'client123'})
        key=Fernet.generate_key()
        self.vault=Vault(self.tmp.name,key_provider=lambda:key)
        self.http=Mock()
        self.eve=EveConnection(self.store,vault=self.vault,transport=self.http)
        self.eve.keys=self.jwks;self.eve.keys_expires=time.time()+3600

    def token(self, **patch):
        claims={'iss':'https://login.eveonline.com/','aud':['client123','EVE Online'],
                'exp':time.time()+1200,'sub':'CHARACTER:EVE:123','name':'Test Character',
                'scp':SCOPES,'owner':'original-owner',**patch}
        header=b64(json.dumps({'alg':'RS256','kid':'unit-test'}).encode())
        payload=b64(json.dumps(claims).encode())
        signature=self.private.sign((header+'.'+payload).encode(),padding.PKCS1v15(),hashes.SHA256())
        return header+'.'+payload+'.'+b64(signature)

    def test_jwt_requires_signature_issuer_both_audiences_scopes_and_expiry(self):
        self.assertEqual(verify_jwt(self.token(),self.jwks,'client123')['name'],'Test Character')
        for patch in [{'iss':'https://attacker.invalid'},{'aud':['EVE Online']},{'aud':['client123']},
                      {'exp':0},{'scp':[]},{'sub':'CORPORATION:EVE:123'},{'nbf':time.time()+1000}]:
            with self.subTest(patch=patch),self.assertRaises(EsiError):verify_jwt(self.token(**patch),self.jwks,'client123')
        token=self.token();parts=token.split('.');parts[1]=b64(json.dumps({'exp':time.time()+99999}).encode())
        with self.assertRaises(EsiError):verify_jwt('.'.join(parts),self.jwks,'client123')

    def test_pkce_state_is_single_use_session_bound_and_expires(self):
        url=self.eve.start('browser1','http://127.0.0.1:8765/callback');query=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        self.assertEqual(query['code_challenge_method'],['S256'])
        self.assertNotIn('client_secret',query)
        with self.assertRaises(EsiError):self.eve.finish(query['state'][0],'code','other-browser')
        with self.assertRaises(EsiError):self.eve.finish(query['state'][0],'code','browser1')
        url=self.eve.start('browser1','http://127.0.0.1:8765/callback');state=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['state'][0]
        self.eve.pending[state]['expires']=0
        with self.assertRaises(EsiError):self.eve.finish(state,'code','browser1')

    def test_compatibility_uses_esi_day_and_never_advances_beyond_reviewed_schema(self):
        for instant,expected in [('2026-10-15T08:00:00','2026-10-14'),
                                 ('2026-10-15T10:59:59','2026-10-14'),
                                 ('2026-10-15T11:00:00','2026-10-15'),
                                 ('2026-11-02T12:00:00','2026-10-15')]:
            with self.subTest(instant=instant):
                self.assertEqual(compatibility_date(datetime.fromisoformat(instant).replace(tzinfo=timezone.utc)),expected)

    def test_transport_sends_compatibility_only_to_esi(self):
        from unittest.mock import patch
        http=Transport()
        response=Mock();response.read.return_value=b'{}';response.headers={}
        http.opener=Mock();http.opener.open.return_value.__enter__=Mock(return_value=response)
        http.opener.open.return_value.__exit__=Mock(return_value=False)
        with patch('muhely.esi.compatibility_date',return_value='2026-10-14'):
            http.request('https://esi.evetech.net/status/')
            self.assertEqual(http.opener.open.call_args.args[0].get_header('X-compatibility-date'),'2026-10-14')
            http.request('https://login.eveonline.com/.well-known/oauth-authorization-server')
            self.assertIsNone(http.opener.open.call_args.args[0].get_header('X-compatibility-date'))

    def test_transport_can_send_public_json_name_lookup_without_a_token(self):
        http=Transport();response=Mock();response.read.return_value=b'{"characters":[]}';response.headers={};http.opener=Mock();http.opener.open.return_value.__enter__=Mock(return_value=response);http.opener.open.return_value.__exit__=Mock(return_value=False)
        http.request('https://esi.evetech.net/universe/ids/',json_body=['Steve Hluskan'])
        request=http.opener.open.call_args.args[0];self.assertEqual(request.get_method(),'POST');self.assertEqual(json.loads(request.data),['Steve Hluskan']);self.assertEqual(request.get_header('Content-type'),'application/json');self.assertIsNone(request.get_header('Authorization'))

    def test_successful_callback_stores_only_encrypted_tokens(self):
        url=self.eve.start('browser','http://127.0.0.1:8765/callback')
        state=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['state'][0]
        self.http.request.return_value=({'access_token':self.token(),'refresh_token':'secret-refresh'},{})
        self.assertEqual(self.eve.finish(state,'code','browser'),123)
        self.assertEqual(self.store.characters()[0]['name'],'Test Character')
        raw=(Path(self.tmp.name)/'characters.enc').read_bytes()
        self.assertNotIn(b'secret-refresh',raw)
        self.assertEqual(self.vault.read()['123']['refresh_token'],'secret-refresh')
        self.assertEqual((Path(self.tmp.name)/'characters.enc').stat().st_mode & 0o777,0o600)

    def test_refresh_keeps_rotated_token_and_original_client(self):
        self.vault.set(123,{'access_token':'expired','refresh_token':'old','expires_at':0,
                            'client_id':'client123','owner':'original-owner'})
        self.http.request.return_value=({'access_token':self.token(),'refresh_token':'rotated'},{})
        self.eve.token(123)
        self.assertEqual(self.vault.read()['123']['refresh_token'],'rotated')
        self.assertEqual(self.http.request.call_args.kwargs['form']['client_id'],'client123')
        self.http.reset_mock();self.eve.token(123);self.http.request.assert_not_called()

    def test_character_owner_change_does_not_overwrite_original_token(self):
        self.vault.set(123,{'access_token':'expired','refresh_token':'old','expires_at':0,
                            'client_id':'client123','owner':'original-owner'})
        self.http.request.return_value=({'access_token':self.token(owner='new-owner'),'refresh_token':'new'},{})
        with self.assertRaises(EsiError):self.eve.token(123)
        self.assertEqual(self.vault.read()['123']['refresh_token'],'old')

    def test_cache_prevents_repeated_api_requests(self):
        self.store.add_character(123,'Test')
        saved={'data':[{'item_id':1}], 'fetched':time.time(), 'expires':time.time()+300}
        self.store.save_snapshots(123,{'assets':saved})
        value=self.eve.resource(123,'assets','token')
        self.assertEqual(value['data'],saved['data']);self.http.request.assert_not_called()

    def test_pagination_collects_every_page_and_rejects_mixed_snapshots(self):
        self.http.request.side_effect=[([{'item_id':1}],{'X-Pages':'2','Last-Modified':'same'}),
                                       ([{'item_id':2}],{'X-Pages':'2','Last-Modified':'same'})]
        self.assertEqual(len(self.eve.resource(123,'assets','token')['data']),2)
        self.http.request.side_effect=[([],{'X-Pages':'2','Last-Modified':'first'}),
                                       ([],{'X-Pages':'2','Last-Modified':'second'})]
        with self.assertRaises(EsiError):self.eve.resource(123,'assets','token')

    def test_failed_resource_does_not_half_update_character(self):
        self.store.add_character(123,'Test')
        old={'data':[{'old':True}], 'fetched':1,'expires':2}
        self.store.save_snapshots(123,{k:old for k in ['assets','blueprints','jobs']})
        self.eve.token=Mock(return_value='token')
        self.eve.resource=Mock(side_effect=[dict(old,data=[{'new':True}]),EsiError('offline')])
        result=self.eve.sync()
        self.assertFalse(result[0]['ok'])
        self.assertEqual(self.store.snapshot(123,'assets')['data'],old['data'])
        self.assertEqual(self.store.characters()[0]['error'],'Blueprintok: offline')

    def test_legacy_industry_token_keeps_working_but_skill_scope_is_explicit(self):
        self.vault.set(123,{'access_token':'expired','refresh_token':'old','expires_at':0,
                            'client_id':'client123','owner':'original-owner'})
        self.http.request.return_value=({'access_token':self.token(scp=INDUSTRY_SCOPES),'refresh_token':'rotated'},{})
        self.eve.token(123)
        self.http.reset_mock()
        with self.assertRaises(SkillScopeError):self.eve.token(123,required_scopes=SKILL_SCOPES)
        self.http.request.assert_not_called()
        self.eve.token(123);self.http.request.assert_not_called()

    def test_feature_specific_consent_preserves_grants_without_forcing_unrelated_scopes(self):
        from muhely.esi import PI_SCOPES,PlanetScopeError
        self.vault.set(123,{'access_token':'fresh','refresh_token':'refresh','expires_at':time.time()+1200,
                            'client_id':'client123','owner':'original-owner','scopes':INDUSTRY_SCOPES})
        def requested(feature):
            url=self.eve.start('browser','http://127.0.0.1:8765/callback',123,feature)
            return set(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['scope'][0].split())
        self.assertEqual(requested('skills'),set(INDUSTRY_SCOPES+SKILL_SCOPES))
        self.assertEqual(requested('pi'),set(INDUSTRY_SCOPES+PI_SCOPES))
        with self.assertRaises(PlanetScopeError):self.eve.token(123,required_scopes=PI_SCOPES)
        data=self.vault.read()['123'];data['scopes']+=SKILL_SCOPES;self.vault.set(123,data)
        self.assertEqual(requested('pi'),set(SCOPES))
        url=self.eve.start('browser','http://127.0.0.1:8765/callback',123,'skills')
        state=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['state'][0]
        self.http.request.return_value=({'access_token':self.token(scp=INDUSTRY_SCOPES+SKILL_SCOPES),'refresh_token':'new'},{})
        self.assertEqual(self.eve.finish(state,'code','browser'),123)
        self.assertEqual(self.store.resource_status(123,'skills')['needs_auth'],0)
        self.assertIsNone(self.store.resource_status(123,'pi'))

    def test_all_access_requests_every_scope_once_and_marks_all_domains(self):
        from muhely.esi import ALL_SCOPES
        self.vault.set(456,{'refresh_token':'other-character'})
        url=self.eve.start('browser','http://127.0.0.1:8765/callback',123,'all')
        query=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        scopes=query['scope'][0].split()
        self.assertEqual(set(scopes),set(ALL_SCOPES))
        self.assertEqual(len(scopes),len(set(scopes)))
        pending=self.eve.pending[query['state'][0]]
        self.assertEqual(pending['character_id'],123)
        self.assertEqual(pending['feature'],'all')
        self.http.request.return_value=({'access_token':self.token(scp=ALL_SCOPES),'refresh_token':'new'},{})
        self.assertEqual(self.eve.finish(query['state'][0],'code','browser'),123)
        self.assertEqual(self.eve.authorized_feature,'all')
        for domain in ['skills','pi','corporations','intel_location','mining','moon_calendar','moon_timers','moon_notifications']:
            with self.subTest(domain=domain):
                self.assertEqual(self.store.resource_status(123,domain)['needs_auth'],0)
        self.assertEqual(self.vault.read()['456'],{'refresh_token':'other-character'})

    def test_all_access_rejects_wrong_character_and_incomplete_consent(self):
        from muhely.esi import ALL_SCOPES
        original={'refresh_token':'original','scopes':INDUSTRY_SCOPES}
        self.vault.set(123,original)
        for claims in [dict(sub='CHARACTER:EVE:456',scp=ALL_SCOPES),dict(scp=SCOPES)]:
            with self.subTest(claims=claims):
                url=self.eve.start('browser','http://127.0.0.1:8765/callback',123,'all')
                state=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['state'][0]
                self.http.request.return_value=({'access_token':self.token(**claims),'refresh_token':'new'},{})
                with self.assertRaises(EsiError):self.eve.finish(state,'code','browser')
                self.assertEqual(self.vault.read(),{'123':original})

    def test_skill_resource_uses_dict_shape_etag_cache_control_and_handles_304(self):
        data={'skills':[],'total_sp':0}
        old={'data':data,'fetched':1,'expires':2,'etag':'"old"'}
        self.store.save_snapshots(123,{'skills':old},domain='skills')
        self.http.request.return_value=(None,{'cache-control':'max-age=60','etag':'"new"','Expires':'Thu, 01 Jan 2100 00:00:00 GMT'})
        value=self.eve.skill_resource(123,'skills','token')
        self.assertEqual(value['data'],data);self.assertEqual(value['etag'],'"new"')
        self.assertLessEqual(value['expires'],time.time()+61)
        self.assertEqual(self.http.request.call_args.kwargs['headers'],{'If-None-Match':'"old"'})
        self.assertTrue(self.http.request.call_args.args[0].endswith('/skills'))
        self.store.save_snapshots(123,{'skills':value},domain='skills');self.http.reset_mock()
        self.eve.skill_resource(123,'skills','token');self.http.request.assert_not_called()

    def test_skill_failure_preserves_both_old_resources_and_industry_error(self):
        self.store.add_character(123,'Test');self.store.character_error(123,'Existing industry error')
        old={'data':[],'fetched':1,'expires':2}
        self.store.save_snapshots(123,{'skillqueue':old,'skills':dict(old,data={'skills':[],'total_sp':0})},domain='skills')
        self.eve.token=Mock(return_value='token')
        self.eve.skill_resource=Mock(side_effect=[dict(old,data={'skills':[],'total_sp':100}),EsiError('Offline')])
        self.assertFalse(self.eve.sync_skills()[0]['ok'])
        self.assertEqual(self.store.snapshot(123,'skills')['data']['total_sp'],0)
        self.assertEqual(self.store.snapshot(123,'skillqueue')['fetched'],1)
        self.assertEqual(self.store.characters()[0]['error'],'Existing industry error')
        self.assertEqual(self.store.resource_status(123,'skills')['error'],'Offline')

    def test_skill_sync_records_missing_scope_without_changing_industry_access(self):
        self.store.add_character(123,'Test')
        self.eve.token=Mock(side_effect=SkillScopeError('New permission required'))
        self.assertFalse(self.eve.sync_skills()[0]['ok'])
        self.assertTrue(self.store.resource_status(123,'skills')['needs_auth'])
        self.assertIsNone(self.store.characters()[0]['error'])

    def test_reauthorization_rejects_wrong_character_and_requires_new_scopes(self):
        for token in [self.token(sub='CHARACTER:EVE:456'),self.token(scp=INDUSTRY_SCOPES)]:
            url=self.eve.start('browser','http://127.0.0.1:8765/callback',character_id=123)
            state=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['state'][0]
            self.http.request.return_value=({'access_token':token,'refresh_token':'secret'},{})
            with self.assertRaises(EsiError):self.eve.finish(state,'code','browser')
            self.assertEqual(self.vault.read(),{})


if __name__=='__main__':unittest.main()
