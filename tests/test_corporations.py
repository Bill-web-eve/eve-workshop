import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock
import urllib.parse

from cryptography.fernet import Fernet
from muhely.server import App,Server
from muhely.esi import (EveConnection,Vault,EsiError,AuthenticationError,CorporationScopeError,
                       SCOPES,INDUSTRY_SCOPES,CORPORATION_SCOPES,ALL_SCOPES)
from muhely.planner import PlanningError,AssetSnapshotPending

ROOT=Path(__file__).resolve().parents[1]
A,B=98000001,98000002

def snapshot(data):return {'data':data,'fetched':time.time()-10,'expires':time.time()+3600,'etag':None}
def asset(item,quantity,tid=34):return {'item_id':item,'type_id':tid,'location_id':6001,'quantity':quantity}
def blueprint(item,bp,me=10,te=20):return {'item_id':item,'type_id':bp,'location_id':6001,'quantity':-1,'runs':-1,'material_efficiency':me,'time_efficiency':te}
def job(jid,bp,runs,installer=1):return {'job_id':jid,'blueprint_type_id':bp,'blueprint_id':900+jid,'output_location_id':6001,'product_type_id':590,'activity_id':1,'status':'active','runs':runs,'installer_id':installer}
def seed(app):
    store=app.store;bp=app.catalog.recipes[590]['bp_id'];store.save_settings({'source':'eve'})
    for char,cid,qty in [(1,A,100),(2,A,200),(3,B,300)]:
        store.add_character(char,'Karakter '+str(char));store.character_corporation(char,cid,'Alpha Corp' if cid==A else 'Beta Corp')
        store.save_snapshots(char,{'assets':snapshot([asset(char,qty)]),'blueprints':snapshot([blueprint(100+char,bp)]),
                                  'jobs':snapshot([job(11,bp,1)] if char==1 else [])})
    for cid,provider,qty,me,te in [(A,1,1000,2,4),(B,3,3000,5,10)]:
        store.save_corporation_snapshots(cid,provider,{'assets':snapshot([asset(cid,qty)]),
           'blueprints':snapshot([blueprint(cid+100,bp,me,te)]),
           'jobs':snapshot([job(21,bp,2)] if cid==A else [])})

class CorporationPlanningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=App(self.tmp.name,ROOT/'data/catalog.sqlite3',0);seed(self.app)
    def plan(self,cid=None,owner=None):return self.app.plan(590,10,owner,cid)
    @staticmethod
    def row(plan,tid=34):return next(r for r in plan['rows'] if r['id']==tid)
    def save(self,cid=None):return self.app.save_plan({'product_id':590,'quantity':10,'corporation_id':cid})['id']
    def test_three_pools_never_mix_assets_jobs_or_blueprint_research(self):
        personal,a,b=self.plan(),self.plan(A),self.plan(B)
        self.assertEqual([self.row(p)['available'] for p in [personal,a,b]],[600,1000,3000])
        self.assertEqual([self.row(p,590)['wip'] for p in [personal,a,b]],[1,2,0])
        self.assertEqual([self.row(p,590)['parameters']['me'] for p in [personal,a,b]],[10,2,5])
        self.assertEqual([self.row(p,590)['parameters']['te'] for p in [personal,a,b]],[20,4,10])
    def test_manual_overrides_are_separate_even_when_personal_mode_is_manual(self):
        self.app.store.save_settings({'source':'manual'})
        self.app.store.save_mapping('inventory',{34:{'quantity':9999}})
        self.app.store.save_mapping('parameters',{590:{'source':'manual','me':9}})
        self.assertEqual(self.row(self.plan())['available'],9999)
        self.assertEqual(self.row(self.plan(A))['available'],1000)
        self.assertEqual(self.row(self.plan(A),590)['parameters']['me'],2)
        self.app.store.save_mapping('inventory',{34:{'quantity':77}},A)
        self.assertEqual([self.row(self.plan(c))['available'] for c in [None,A,B]],[9999,77,3000])
    def test_reservations_only_reduce_the_owning_pool(self):
        a=self.save(A);personal=self.save();b=self.save(B)
        self.assertEqual([self.row(self.plan(c))['available'] for c in [None,A,B]],[0,0,0])
        self.assertEqual([self.row(self.plan(c,o))['available'] for c,o in [(None,personal),(A,a),(B,b)]],[600,1000,3000])
        self.app.set_reservation(a,False)
        self.assertEqual([self.row(self.plan(c))['available'] for c in [None,A,B]],[0,1000,0])
    def test_reopen_update_and_restart_keep_corporation_identity(self):
        saved=self.save(A)
        result=self.app.save_plan({'id':saved,'product_id':590,'quantity':11,'corporation_id':A})
        self.assertEqual(result['id'],saved)
        reload=App(self.tmp.name,ROOT/'data/catalog.sqlite3',0)
        self.assertEqual(reload.store.plans()[0]['corporation_id'],A)
        self.assertEqual(reload.plan(590,11,saved,A)['corporation_id'],A)
        for cid in [None,B]:
            with self.assertRaises(PlanningError):self.plan(cid,saved)
            with self.assertRaises(PlanningError):self.app.save_plan({'id':saved,'product_id':590,'quantity':10,'corporation_id':cid})
        self.assertEqual(reload.store.plans()[0]['corporation_id'],A)
    def test_combined_shopping_uses_each_pool_once_and_sums_only_deficits(self):
        owners=[(cid,self.save(cid)) for cid in [None,A,B]]
        expected=sum(self.row(self.plan(cid,owner))['buy'] for cid,owner in owners)
        summary=self.app.shopping_summary()
        self.assertEqual(next(r['buy'] for r in summary['rows'] if r['id']==34),expected)
        self.assertEqual({p['corporation_id'] for p in summary['plans']},{None,A,B})
        self.assertTrue(summary['separate_pools'])
    def test_corporation_failure_never_blocks_personal_or_other_corporation(self):
        saved=self.save(A);self.app.store.corporation_error(A,'Nincs Director szerepkör')
        with self.assertRaises(PlanningError):self.plan(A)
        self.assertEqual(self.row(self.plan())['available'],600)
        self.assertEqual(self.row(self.plan(B))['available'],3000)
        state=self.app.state();self.assertIsNone(state['reservation_error'])
        self.assertIn('Director',next(p for p in state['plans'] if p['id']==saved)['allocation_error'])
        self.app.set_reservation(saved,False)
    def test_membership_change_or_removed_provider_cannot_reuse_corp_stock(self):
        self.app.store.character_corporation(1,B,'Beta Corp')
        with self.assertRaises(PlanningError):self.plan(A)
        self.assertEqual(self.row(self.plan())['available'],600)
        self.assertEqual(self.row(self.plan(B))['available'],3000)
    def test_personal_location_filter_is_not_inherited_by_corporation(self):
        self.app.store.save_settings({'location_ids':[999999]})
        self.assertEqual(self.row(self.plan())['available'],0)
        self.assertEqual(self.row(self.plan(A))['available'],1000)
    def test_unknown_or_malformed_owner_never_falls_back_to_personal(self):
        for cid in [True,0,-1,'wrong',98009999]:
            with self.assertRaises(PlanningError):self.plan(cid)
    def test_delivered_corporate_jobs_wait_for_own_assets_without_blocking_personal(self):
        from datetime import datetime,timezone
        self.save(A);parts={k:self.app.store.corporation_snapshot(A,k) for k in ['assets','blueprints','jobs']}
        completed=time.time();parts['assets']['fetched']=completed-30
        parts['jobs']['data'][0].update(status='delivered',completed_date=datetime.fromtimestamp(completed,timezone.utc).isoformat())
        self.app.store.save_corporation_snapshots(A,1,parts)
        with self.assertRaises(AssetSnapshotPending):self.plan(A)
        self.assertEqual(self.row(self.plan())['available'],600)
        self.assertIsNone(self.app.state()['delivery_wait'])
        parts['assets']['fetched']=completed+1;parts['assets']['data'].append(asset(A+10,2,590))
        self.app.store.save_corporation_snapshots(A,1,parts)
        target=self.row(self.plan(A,self.app.store.plans()[0]['id']),590)
        self.assertEqual((target['available'],target['wip'],target['missing']),(2,0,8))

class CorporationApiTests(unittest.TestCase):
    row=staticmethod(CorporationPlanningTests.row)
    def setUp(self):
        CorporationPlanningTests.setUp(self);self.server=Server(self.app)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close)
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(2)
    def request(self,path,data=None):
        c=http.client.HTTPConnection('127.0.0.1',self.app.port,timeout=10)
        headers={'Cookie':'eve_session='+self.app.cookie}
        if data is not None:headers.update({'Content-Type':'application/json','Origin':self.app.origin,'X-CSRF-Token':self.app.csrf})
        c.request('POST' if data is not None else 'GET',path,None if data is None else json.dumps(data),headers)
        response=c.getresponse();raw=json.loads(response.read());status=response.status;c.close();return status,raw
    def test_http_scope_routes_and_mapping_updates_are_isolated(self):
        status,p=self.request(f'/api/plan?product_id=590&quantity=10&corporation_id={A}')
        self.assertEqual(status,200,p);self.assertEqual(self.row(p)['available'],1000)
        self.assertEqual(self.request(f'/api/inventory?corporation_id={A}',{'34':{'quantity':88}})[0],200)
        self.assertEqual(self.request(f'/api/parameters?corporation_id={A}',{'590':{'source':'manual','me':7}})[0],200)
        personal=self.request('/api/state')[1];corp=self.request(f'/api/state?corporation_id={A}')[1]
        self.assertEqual(corp['inventory']['34']['quantity'],88);self.assertEqual(corp['parameters']['590']['me'],7)
        self.assertEqual(personal['inventory'],{});self.assertEqual(personal['parameters'],{})
        self.assertNotIn('access_token',json.dumps(corp));self.assertNotIn('refresh_token',json.dumps(corp))
    def test_scope_locations_and_source_cannot_modify_personal_settings(self):
        self.assertEqual(self.request(f'/api/settings?corporation_id={A}',{'source':'eve','location_ids':[6002]})[0],200)
        self.assertEqual(self.app.store.settings()['location_ids'],[])
        self.assertEqual(self.app.scope_settings(A)['location_ids'],[6002]);self.assertEqual(self.app.scope_settings(B)['location_ids'],[])
        self.assertEqual(self.request(f'/api/settings?corporation_id={A}',{'source':'manual'})[0],400)
        self.assertEqual(self.request('/api/plan?product_id=590&corporation_id=98009999')[0],400)

class CorporationConnectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=App(self.tmp.name,ROOT/'data/catalog.sqlite3',0)
        for cid in [1,2]:self.app.store.add_character(cid,'Member '+str(cid))
        key=Fernet.generate_key();self.vault=Vault(self.tmp.name,key_provider=lambda:key);self.http=Mock()
        self.eve=EveConnection(self.app.store,vault=self.vault,transport=self.http)
        for cid in [1,2]:self.vault.set(cid,{'access_token':'private-'+str(cid),'expires_at':time.time()+3600,'client_id':'client','scopes':ALL_SCOPES})
        self.app.store.save_settings({'client_id':'client'});self.bp=self.app.catalog.recipes[590]['bp_id'];self.fail=None;self.calls=[]
    def response(self,url,**kwargs):
        self.calls.append(url)
        path=urllib.parse.urlsplit(url).path
        if path.startswith('/characters/'):return {'corporation_id':A},{}
        if path==f'/corporations/{A}':return {'name':'Alpha Corp'},{}
        if self.fail and self.fail in path:raise AuthenticationError('Forbidden')
        page=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get('page',['1'])[0]
        headers={'X-Pages':'2' if path.endswith('/assets') else '1','Cache-Control':'max-age=60','Last-Modified':'Thu, 15 Oct 2026 10:00:00 GMT'}
        if path.endswith('/assets'):return [asset(int(page),100)],headers
        if path.endswith('/blueprints'):return [blueprint(9,self.bp)],headers
        if path.endswith('/industry/jobs'):return [job(1,self.bp,2)],headers
        raise AssertionError(url)
    def test_sync_pages_once_per_corporation_and_never_writes_personal_snapshots(self):
        self.http.request.side_effect=self.response;result=self.eve.sync_corporations()
        self.assertTrue(result[0]['ok']);self.assertEqual(len(result),1)
        self.assertEqual(len([u for u in self.calls if '/assets?' in u]),2)
        self.assertEqual(len(self.app.store.corporation_snapshot(A,'assets')['data']),2)
        self.assertIsNone(self.app.store.snapshot(1,'assets'));self.assertIsNone(self.app.store.characters()[0]['error'])
    def test_permission_failure_and_partial_fetch_preserve_all_old_corporation_data(self):
        self.http.request.side_effect=self.response;self.eve.sync_corporations()
        before={k:self.app.store.corporation_snapshot(A,k) for k in ['assets','blueprints','jobs']}
        with self.app.store.db() as db:db.execute('UPDATE corporation_snapshots SET expires=0')
        self.fail='/industry/jobs';result=self.eve.sync_corporations()
        self.assertFalse(result[0]['ok']);self.assertIn('Director',result[0]['error'])
        for k in before:self.assertEqual(self.app.store.corporation_snapshot(A,k)['data'],before[k]['data'])
        self.assertIsNone(self.app.store.characters()[0]['error'])
    def test_feature_consent_preserves_personal_grants_and_does_not_require_corp_for_personal(self):
        url=self.eve.start('session','http://127.0.0.1/callback',1,'corporations')
        scopes=set(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['scope'][0].split())
        self.assertEqual(scopes,set(ALL_SCOPES))
        token=self.vault.read()['1'];token['scopes']=SCOPES;self.vault.set(1,token)
        self.assertEqual(self.eve.token(1),'private-1')
        with self.assertRaises(CorporationScopeError):self.eve.token(1,CORPORATION_SCOPES)
        url=self.eve.start('session','http://127.0.0.1/callback',1,'corporations')
        self.assertEqual(set(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['scope'][0].split()),set(SCOPES+CORPORATION_SCOPES))
    def test_malformed_page_and_changed_snapshot_do_not_commit(self):
        self.app.store.character_corporation(1,A,'Alpha Corp')
        self.http.request.side_effect=[([asset(1,100)],{'X-Pages':'2','Last-Modified':'A'}),([asset(2,100)],{'X-Pages':'2','Last-Modified':'B'})]
        with self.assertRaises(EsiError):self.eve.corporation_resource(A,'assets','token')
        self.http.request.side_effect=[([{'item_id':1,'type_id':34,'location_id':6001,'quantity':True}],{})]
        with self.assertRaises(EsiError):self.eve.corporation_resource(A,'assets','token')
    def test_another_member_can_supply_corporation_data_after_role_failure(self):
        def response(url,**kwargs):
            if '/corporations/' in url and kwargs.get('token')=='private-1':raise AuthenticationError('Forbidden')
            return self.response(url,**kwargs)
        self.http.request.side_effect=response
        result=self.eve.sync_corporations();self.assertTrue(result[0]['ok'])
        self.assertEqual(self.app.store.corporation(A)['provider_id'],2)
        self.assertEqual(len(self.app.store.corporation_snapshot(A,'assets')['data']),2)
