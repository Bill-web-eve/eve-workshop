from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import patch
import tempfile,unittest,time,json,threading
from muhely.store import Store
from muhely import fleet
from muhely.esi import EsiError
from muhely.planner import PlanningError

BASE=1800000000
U=SimpleNamespace(systems={1:{'name':'Alpha','region':'Region'},2:{'name':'Beta','region':'Region'},3:{'name':'Gamma','region':'Region'}})
def kill(kid,at=0,sid=1,cid=11,loss=False):
    return {'killmail_id':kid,'killmail_time':datetime.fromtimestamp(BASE+at,timezone.utc).isoformat(),'solar_system_id':sid,
            'victim':{'character_id':cid if loss else 99,'ship_type_id':590},'attackers':[{'character_id':99 if loss else cid},{'character_id':55}],'zkb':{'totalValue':1000000}}
class FleetTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.s=Store(tmp.name);self.s.add_character(11,'Pilot');self.s.add_character(12,'Other')
        fleet.schema(self.s)
        self.http=SimpleNamespace(request=lambda *a,**k:({'solar_system_id':1},{'cache-control':'max-age=5','date':'Fri, 15 Jan 2027 08:00:00 GMT'}))
        eve=SimpleNamespace(granted_scopes=lambda:{11:[fleet.LOCATION_SCOPE]},token=lambda *a,**k:'secret',http=self.http)
        with patch('muhely.fleet.intel_universe.load',return_value=U):self.f=fleet.Fleet(self.s,SimpleNamespace(name=lambda tid:'Ship'),eve)
        self.addCleanup(self.f.stop)
    def test_sessions_have_per_system_padding_and_do_not_add_unobserved_transit(self):
        rows=[kill(1),kill(2,600,2),kill(3,1200,1)]
        pos=[{'character_id':11,'ts':BASE+300,'system_id':3},{'character_id':12,'ts':BASE+300,'system_id':2},{'character_id':11,'ts':BASE-901,'system_id':2}]
        s=fleet.sessions(rows,pos,11,fleet.DEFAULTS,U)[0]
        self.assertEqual([v['system_id'] for v in s['visits']],[1,3,2,1]);self.assertEqual(s['esi_samples'],1)
        self.assertEqual(s['start'],BASE-900);self.assertEqual(s['end'],BASE+2100)
        for k in rows:
            at=fleet.timestamp(k['killmail_time']);w=next(w for w in s['windows'] if k['killmail_id'] in w['kill_ids'])
            self.assertLessEqual(w['start'],at-900);self.assertGreaterEqual(w['end'],at+900)
    def test_nearby_position_samples_bound_transit_without_shrinking_kill_padding(self):
        pos=[{'character_id':11,'ts':BASE+t,'system_id':sid} for t,sid in [(60,2),(120,3)]]
        s=fleet.sessions([kill(1),kill(2,180,1)],pos,11,fleet.DEFAULTS,U)[0]
        w=next(w for w in s['windows'] if w['system_id']==2)
        self.assertEqual((w['start'],w['end']),(BASE,BASE+120))
        first=next(w for w in s['windows'] if w['system_id']==1)
        self.assertEqual(first['start'],BASE-900);self.assertEqual(first['end'],BASE+1080)
    def test_revisits_keep_separate_nonoverlapping_windows(self):
        rows=[kill(1),kill(2,1800,2),kill(3,3600,2),kill(4,5400)]
        s=fleet.sessions(rows,[],11,fleet.DEFAULTS,U)[0]
        self.assertEqual(len([w for w in s['windows'] if w['system_id']==1]),2)
        self.assertEqual([v['system_id'] for v in s['visits']],[1,2,1])
    def test_sessions_split_at_inactivity_gap_and_cannot_mix_characters(self):
        rows=[kill(1),kill(2,2701),kill(3,100,cid=12),kill(4,2800,loss=True)]
        sessions=fleet.sessions(rows,[],11,fleet.DEFAULTS,U)
        self.assertEqual(len(sessions),2);self.assertEqual(sessions[1]['kill_ids'],[2,4]);self.assertEqual(sessions[1]['losses'],1)
    def test_one_hour_cache_prevents_repeat_network_and_failures_keep_kills(self):
        class Response:
            headers={}
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return json.dumps([kill(1)]).encode()
        with patch.object(self.f.zkill.opener,'open',return_value=Response()) as request:
            self.f.zkill.query('characterID/11/page/1/');self.f.zkill.query('characterID/11/page/1/')
            self.assertEqual(request.call_count,1);self.assertNotIn('Authorization',request.call_args.args[0].headers)
        fleet.save_kills(self.s,[kill(1)])
        with patch.object(self.f.zkill.opener,'open',side_effect=OSError()):
            with self.assertRaises(EsiError):self.f.zkill.query('characterID/12/page/1/')
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM fleet_kills').fetchone()[0],1)
    def test_validation_is_atomic_and_deduplicates_shared_kill(self):
        fleet.save_kills(self.s,[kill(1)]);fleet.save_kills(self.s,[kill(1)])
        broken=kill(2);del broken['attackers']
        with self.assertRaises(EsiError):fleet.save_kills(self.s,[kill(3),broken])
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM fleet_kills').fetchone()[0],1)
    def test_location_sampling_is_independent_of_15_minute_gate_and_honors_cache(self):
        with patch.object(self.http,'request',wraps=self.http.request) as request:
            self.f.locations();self.f.locations();self.assertEqual(request.call_count,1)
        row=fleet.cache(self.s,'location:11');self.assertGreaterEqual(row['expires']-row['checked'],60)
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM fleet_positions').fetchone()[0],1)
        fleet.save_preferences(self.s,{'tracking':False});self.f.locations()
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM fleet_positions').fetchone()[0],1)
    def test_location_cache_age_is_not_recorded_as_a_new_position(self):
        with patch('muhely.fleet.time.time',return_value=1800000000),patch.object(self.http,'request',return_value=({'solar_system_id':1},{'cache-control':'max-age=3600','age':'300','date':'Fri, 15 Jan 2027 08:00:00 GMT'})):
            self.f.locations()
        row=fleet.cache(self.s,'location:11');self.assertEqual(row['data']['observed'],datetime(2027,1,15,7,55,tzinfo=timezone.utc).timestamp());self.assertGreaterEqual(row['expires']-row['checked'],3300)
    def test_preferences_enforce_15_minute_minimum_padding_and_known_characters(self):
        for changes in [{'padding_minutes':14},{'interval_seconds':29},{'character_ids':[99]},{'tracking':1}]:
            with self.assertRaises(PlanningError):fleet.save_preferences(self.s,changes)
        fleet.save_preferences(self.s,{'character_ids':[12],'interval_seconds':30})
        self.assertEqual([r['id'] for r in self.f.actors()],[12])
    def test_context_is_filtered_to_each_system_window_and_deduped(self):
        own=kill(1);fleet.save_kills(self.s,[own]);s=fleet.sessions([own],[],11,fleet.DEFAULTS,U)[0]
        with patch.object(self.f.zkill,'query',return_value=[kill(2,-899),kill(3,901),kill(4,0,2),own]):results=self.f.context(s)
        self.assertFalse(results[0]['partial'])
        with self.s.db() as db:self.assertEqual({r[0] for r in db.execute('SELECT id FROM fleet_kills')},{1,2})
    def test_dashboard_counts_each_public_kill_once_for_multiple_own_pilots(self):
        k=kill(1);k['attackers'].append({'character_id':12});fleet.save_kills(self.s,[k])
        with patch('muhely.fleet.time.time',return_value=BASE+100):d=self.f.dashboard()
        self.assertEqual(len(d['kills']),1);self.assertEqual(len(d['kills'][0]['characters']),2);self.assertEqual(len(d['sessions']),2)
    def test_context_request_budget_and_limit_are_marked_partial(self):
        s={'id':'11:1','windows':[{'system_id':1,'start':BASE-900,'end':BASE+900}]}
        with patch.object(self.f.zkill,'query',side_effect=lambda path:[kill(i+10,1) for i in range(200)]):result=self.f.context(s)
        self.assertTrue(result[0]['partial'])
    def test_refresh_rejects_unknown_character_and_session(self):
        for kw in [{'cid':99},{'session_id':'11:missing'},{'session_id':[]}]:
            with self.assertRaises(PlanningError):self.f.start_refresh(**kw)

import test_server as server_tests
class FleetApiTests(unittest.TestCase):
    setUp=server_tests.ServerTests.setUp;close=server_tests.ServerTests.close;request=server_tests.ServerTests.request
    def test_local_routes_protect_history_and_settings(self):
        self.app.store.add_character(11,'Pilot')
        self.assertEqual(self.request('/api/fleet',Cookie='')[0],403)
        self.assertEqual(self.request('/api/fleet/preferences',{'tracking':False},Origin='https://other.invalid')[0],403)
        self.assertEqual(self.request('/api/fleet/preferences',{'interval_seconds':20})[0],400)
        self.assertEqual(self.request('/api/fleet/preferences',{'interval_seconds':60,'tracking':False})[0],200)
        status,data,_=self.request('/api/fleet');self.assertEqual(status,200);self.assertEqual(data['characters'][0]['name'],'Pilot');self.assertEqual(data['sessions'],[])
        self.assertNotIn('task',data);self.assertIn('status',data)
        self.assertEqual(self.request('/api/fleet/refresh',{'session_id':'unknown'})[0],400)
        self.assertEqual(self.request('/fleet.js')[0],200)
        self.assertIn('fleet',self.request('/api/activity')[1])
