import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from urllib.parse import parse_qs,urlparse
from muhely import mining
from muhely.catalog import Catalog
from muhely.esi import EveConnection,INDUSTRY_SCOPES,MINING_SCOPES,SKILL_SCOPES,EsiError,AuthenticationError
from muhely.store import Store
from muhely.planner import PlanningError

ROOT=Path(__file__).resolve().parents[1]
NOW=1792497600  # 2026-10-20 UTC

def entry(q=120,day='2026-10-20',tid=1230,system=30000142):
    return {'date':day,'solar_system_id':system,'type_id':tid,'quantity':q}
def snap(rows,checked=NOW,expires=NOW+600):return {'data':rows,'fetched':checked,'expires':expires,'etag':None}

class MiningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.catalog=Catalog(ROOT/'data/catalog.sqlite3')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
        self.store.add_character(1,'Alice');self.store.add_character(2,'Bob')
        self.eve=EveConnection(self.store,vault=Mock(),transport=Mock());self.eve.token=Mock(return_value='not-a-real-token')
    def view(self,**kw):return mining.dashboard(self.store,self.catalog,now=NOW,**kw)
    def test_history_upserts_corrections_without_double_counting_and_survives_rolling_window(self):
        self.store.save_mining(1,snap([entry(120),entry(50,'2026-09-01')]))
        self.store.save_mining(1,snap([entry(130)]));self.store.save_mining(1,snap([entry(130)]))
        self.assertEqual(self.view()['summary']['quantity'],130)
        self.assertEqual(self.view(start='2003-01-01')['summary']['quantity'],180)
        self.store.save_mining(1,snap([entry(110)]))
        self.assertEqual(self.view()['summary']['quantity'],110)
        self.assertEqual(self.view()['summary']['volume'],11)
        reopened=Store(self.tmp.name)
        self.assertEqual(mining.dashboard(reopened,self.catalog,now=NOW)['summary']['quantity'],110)
    def test_character_ore_day_filters_and_finishing_portions(self):
        self.store.save_mining(1,snap([entry(50,'2026-10-19'),entry(70)]))
        self.store.save_mining(2,snap([entry(220),entry(100,tid=1228)]))
        d=self.view();self.assertEqual(d['summary']['quantity'],440)
        self.assertEqual(sum(c['quantity'] for c in d['by_character']),440)
        self.assertEqual(sum(o['quantity'] for o in d['by_ore']),440)
        self.assertEqual(len(d['by_day']),2)
        refined={m['id']:m['quantity'] for m in d['summary']['materials']}
        totals={}
        for c in d['by_character']:
            for m in c['materials']:totals[m['id']]=totals.get(m['id'],0)+m['quantity']
        self.assertEqual(refined,totals)
        self.assertGreater(d['refining_yield'],.9);self.assertEqual(d['implant'],4)
        only=self.view(character_id=1,ore_id=1230,start='2026-10-20')
        self.assertEqual(only['summary']['quantity'],70);self.assertTrue(all(m['quantity']==0 for m in only['summary']['materials']))
        combined=self.view(character_id=1);ore=self.catalog.mining_types[1230]
        expected=int(mining.Decimal(ore['materials'][0]['quantity'])*mining.reprocessing_yield(self.catalog.moon_rules,mining.preferences(self.store)))
        self.assertEqual(combined['summary']['materials'][0]['quantity'],expected)
    def test_unknown_volumes_and_nonrefinable_gas_are_not_invented(self):
        gas=next(t for t,r in self.catalog.mining_types.items() if not r['materials'])
        self.store.save_mining(1,snap([entry(tid=gas),entry(tid=999999999)]))
        d=self.view();self.assertEqual(d['summary']['unknown_volume'],1);self.assertEqual(d['summary']['unrefinable'],2)
        self.assertEqual(d['summary']['materials'],[])
    def test_scope_errors_are_independent_of_industry_and_prior_history_survives(self):
        self.store.save_mining(1,snap([entry()]));self.eve.token.side_effect=AuthenticationError('Authorize mining')
        result=mining.sync(self.eve)
        self.assertFalse(any(r['ok'] for r in result));self.assertIsNone(self.store.characters()[0]['error'])
        d=self.view(access_scopes={});self.assertTrue(d['characters'][0]['needs_auth']);self.assertEqual(d['summary']['quantity'],120)
    def test_validates_dates_quantities_and_duplicate_rows(self):
        for value in [[entry(-1)],[entry(True)],[entry(day='2026-02-30')],[entry(tid=0)],[entry(),entry()],{}]:
            with self.subTest(value=value),self.assertRaises(EsiError):mining.validate(value)
        for kwargs in [dict(start='2026-20-01'),dict(start='2026-10-21',end='2026-10-20'),dict(character_id=99)]:
            with self.assertRaises(PlanningError):self.view(**kwargs)
    def test_all_pages_commit_together_and_cache_avoids_network(self):
        self.eve.http.request.side_effect=[([entry(100)],{'X-Pages':'2','Cache-Control':'max-age=600','Age':'10','Last-Modified':'same'}),
                                           ([entry(200,tid=1228)],{'X-Pages':'2','Cache-Control':'max-age=600','Age':'20','Last-Modified':'same'})]
        with patch('muhely.mining.time.time',return_value=NOW):
            self.store.save_mining(1,mining.resource(self.eve,1,'fake'))
            self.assertEqual(mining.resource(self.eve,1,'fake')['expires'],NOW+580)
        self.assertEqual(self.eve.http.request.call_count,2)
        self.eve.http.request.side_effect=[([entry(777)],{'X-Pages':'2'}),EsiError('Offline'),EsiError('Offline')]
        with patch('muhely.mining.time.time',return_value=NOW+601):result=mining.sync(self.eve)
        self.assertFalse(result[0]['ok']);self.assertEqual(self.view()['summary']['quantity'],300)
    def test_changed_pagination_and_changed_page_date_are_rejected(self):
        for second in [{'X-Pages':'3','Last-Modified':'one'},{'X-Pages':'2','Last-Modified':'two'}]:
            self.eve.http.request.side_effect=[([entry()],{'X-Pages':'2','Last-Modified':'one'}),([entry(tid=1228)],second)]
            with self.assertRaises(EsiError):mining.resource(self.eve,1,'fake')
    def test_authorization_preserves_other_features_and_requests_only_mining_in_addition(self):
        self.store.save_settings({'client_id':'public-client'})
        self.eve.vault.read.return_value={'1':{'scopes':INDUSTRY_SCOPES+SKILL_SCOPES}}
        q=parse_qs(urlparse(self.eve.start('session','http://127.0.0.1:8765/callback',1,'mining')).query)
        scopes=set(q['scope'][0].split())
        self.assertEqual(scopes,set(INDUSTRY_SCOPES+SKILL_SCOPES+MINING_SCOPES))
    def test_forgetting_character_removes_history(self):
        self.store.save_mining(1,snap([entry()]));self.store.forget_character(1)
        self.assertEqual(self.view()['summary']['quantity'],0)
        with self.store.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM mining_ledger').fetchone()[0],0)
    def test_bundled_catalogue_has_general_moon_and_ice_refining_data(self):
        for tid in [1230,1228,45492,16262]:
            self.assertGreater(self.catalog.mining_types[tid]['volume'],0)
            self.assertTrue(self.catalog.mining_types[tid]['materials'])
        self.assertGreater(len(self.catalog.mining_types),400)

import tests.test_server as server_fixture
class MiningApiTests(unittest.TestCase):
    setUp=server_fixture.ServerTests.setUp
    close=server_fixture.ServerTests.close
    request=server_fixture.ServerTests.request
    def test_private_endpoints_filters_and_trigger(self):
        self.assertEqual(self.request('/api/mining',Cookie='')[0],403)
        self.assertEqual(self.request('/api/mining')[0],200)
        self.assertEqual(self.request('/api/mining?start=wrong')[0],400)
        self.assertEqual(self.request('/mining.js')[0],200)
        self.app.start_task=Mock()
        self.assertEqual(self.request('/api/mining/sync',{},Origin='https://other.invalid')[0],403)
        self.app.start_task.assert_not_called()
        self.assertEqual(self.request('/api/mining/sync',{})[0],200);self.app.start_task.assert_called_once_with('mining')
        self.app.eve.start=Mock(return_value='https://login.eveonline.com/v2/oauth/authorize')
        self.assertEqual(self.request('/api/auth/start',{'feature':'mining'})[0],200)
