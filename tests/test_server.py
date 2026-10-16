import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import Mock
import unittest

from muhely.server import App,Server

ROOT=Path(__file__).resolve().parents[1]


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=App(self.tmp.name,ROOT/'data/catalog.sqlite3',port=0)
        self.server=Server(self.app)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close)
        self.cookie='eve_session='+self.app.cookie

    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)

    def request(self,path,body=None,**headers):
        connection=http.client.HTTPConnection('127.0.0.1',self.app.port,timeout=10)
        data=None if body is None else json.dumps(body)
        defaults={'Cookie':self.cookie}
        if body is not None:
            defaults.update({'Content-Type':'application/json','Origin':self.app.origin,'X-CSRF-Token':self.app.csrf})
        connection.request('GET' if body is None else 'POST',path,body=data,headers={**defaults,**headers})
        response=connection.getresponse();raw=response.read();status=response.status;h=dict(response.getheaders());connection.close()
        return status,json.loads(raw) if 'application/json' in h.get('Content-Type','') else raw,h

    def test_manual_plan_and_search_work_without_any_eve_account(self):
        status,plan,_=self.request('/api/plan?product_id=22428&quantity=1')
        self.assertEqual(status,200);self.assertTrue(plan['queue'])
        self.assertEqual(plan['summary']['items'],45)
        status,rows,_=self.request('/api/search?q=Hulk')
        self.assertEqual(status,200);self.assertTrue(rows)
        status,_,headers=self.request('/')
        self.assertIn('HttpOnly',headers['Set-Cookie'])
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        for path in ['/graph.js','/graph.css','/skills.js','/pi.js','/numbers.js']:
            status,content,headers=self.request(path)
            self.assertEqual(status,200)
            self.assertTrue(content)
            self.assertIn('no-store',headers['Cache-Control'])

    def test_producer_selection_uses_active_skills_in_api(self):
        self.app.store.add_character(456,'Producer')
        now=time.time()
        self.app.store.save_snapshots(456,{'skills':{'data':{'total_sp':1000,'skills':[
            {'skill_id':3380,'trained_skill_level':5,'active_skill_level':3,'skillpoints_in_skill':1000}]},
            'fetched':now,'expires':now+3600}},domain='skills')
        status,manual,_=self.request('/api/plan?product_id=590&quantity=2&manufacturer_id=manual')
        self.assertEqual(status,200)
        status,skilled,_=self.request('/api/plan?product_id=590&quantity=2&manufacturer_id=456')
        self.assertEqual(status,200)
        before=next(r for r in manual['queue'] if r['id']==590)
        after=next(r for r in skilled['queue'] if r['id']==590)
        self.assertAlmostEqual(after['seconds']/before['seconds'],.88)
        self.assertEqual(after['producer']['character_id'],456)
        self.assertEqual(self.request('/api/plan?product_id=590&quantity=2&manufacturer_id=999')[0],400)

    def test_other_origin_host_or_missing_csrf_cannot_change_data(self):
        for headers in [{'Origin':'https://evil.invalid'},{'Host':'evil.invalid'},
                        {'X-CSRF-Token':'wrong'},{'Cookie':''}]:
            with self.subTest(headers=headers):
                status,_,_=self.request('/api/settings',{'source':'eve'},**headers)
                self.assertEqual(status,403)
        self.assertEqual(self.app.store.settings()['source'],'manual')
        self.assertEqual(self.request('/api/state',Host='evil.invalid')[0],403)

    def test_zero_overrides_and_persistence_and_replanning(self):
        self.assertEqual(self.request('/api/inventory',{'22428':{'quantity':1}})[0],200)
        result=self.request('/api/plan?product_id=22428&quantity=1')[1]
        self.assertEqual(result['queue'],[]);self.assertEqual(result['shopping'],[])
        self.request('/api/inventory',{'22428':{'quantity':0}})
        self.assertTrue(self.request('/api/plan?product_id=22428&quantity=1')[1]['queue'])
        self.request('/api/inventory',{'22428':{'quantity':None}})
        self.assertEqual(self.app.store.mapping('inventory'),{})

    def test_invalid_input_is_rejected_atomically(self):
        for body in [{'22428':{'quantity':-1}},{'22428':{'quantity':'1'}},
                     {'22428':{'quantity':1},'643':{'reserved':-2}}]:
            self.assertEqual(self.request('/api/inventory',body)[0],400)
            self.assertEqual(self.app.store.mapping('inventory'),{})
        self.assertEqual(self.request('/api/settings',{'manufacturing':{'material_rig':100}})[0],400)
        self.assertEqual(self.request('/api/settings',{'client_id':'secret with whitespace'})[0],400)

    def test_live_mode_never_silently_becomes_empty_stock(self):
        self.request('/api/settings',{'source':'eve'})
        status,data,_=self.request('/api/plan?product_id=22428&quantity=1')
        self.assertEqual(status,400);self.assertIn('karaktert',data['error'])

    def seed_archon_stock(self):
        now=time.time()
        self.app.store.add_character(123,'Test character')
        parts={k:{'data':[],'fetched':now,'expires':now+300} for k in ['assets','blueprints','jobs']}
        parts['assets']['data']=[{'item_id':1,'type_id':23757,'quantity':1,'location_id':6001},
                                 {'item_id':2,'type_id':23757,'quantity':1,'location_id':6002}]
        self.app.store.save_snapshots(123,parts)
        self.app.eve.sync=Mock(return_value=[{'id':123,'ok':True}])

    def run_sync(self):
        self.assertEqual(self.request('/api/sync',{})[0],200)
        deadline=time.monotonic()+3
        while self.app.task['running'] and time.monotonic()<deadline:
            time.sleep(.01)
        self.assertFalse(self.app.task['running'])

    def test_first_successful_sync_activates_stock_and_removes_archon_subtree(self):
        self.seed_archon_stock()
        self.run_sync()
        self.assertEqual(self.app.store.settings()['source'],'eve')
        status,p,_=self.request('/api/plan?product_id=92822&quantity=1')
        self.assertEqual(status,200)
        rows={r['id']:r for r in p['rows']}
        self.assertEqual((rows[23757]['required'],rows[23757]['available'],rows[23757]['runs']),(1,2,0))
        self.assertNotIn(23757,[r['id'] for r in p['queue']])
        self.assertEqual(rows[21025]['required'],0)  # Capital Jump Drive: Archon input only.
        self.assertEqual(p['source'],'eve')

    def test_explicit_manual_source_is_preserved_by_later_successful_sync(self):
        self.seed_archon_stock()
        self.request('/api/settings',{'source':'manual'})
        self.run_sync()
        settings=self.app.store.settings()
        self.assertEqual(settings['source'],'manual');self.assertTrue(settings['source_explicit'])
        _,p,_=self.request('/api/plan?product_id=92822&quantity=1')
        row=next(r for r in p['rows'] if r['id']==23757)
        self.assertEqual((row['available'],row['runs']),(0,1))

    def test_failed_sync_does_not_activate_live_stock(self):
        self.seed_archon_stock()
        self.app.eve.sync.return_value=[{'id':123,'ok':False,'error':'offline'}]
        self.run_sync()
        self.assertEqual(self.app.store.settings()['source'],'manual')

    def test_delivered_job_waits_for_assets_but_respects_location_and_manual_stock(self):
        now=time.time()
        self.app.store.add_character(123,'Test character')
        snapshots={kind:{'data':[],'fetched':now-300,'expires':now+300} for kind in ['assets','blueprints','jobs']}
        snapshots['jobs']['data']=[{'job_id':1,'product_type_id':22428,'blueprint_type_id':22429,
            'activity_id':1,'status':'delivered','runs':1,'output_location_id':6001,
            'completed_date':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now-60))}]
        self.app.store.save_snapshots(123,snapshots)
        self.request('/api/settings',{'source':'eve'})
        self.assertEqual(self.request('/api/plan?product_id=22428&quantity=1')[0],400)
        self.request('/api/settings',{'location_ids':[6002]})
        self.assertEqual(self.request('/api/plan?product_id=22428&quantity=1')[0],200)
        self.request('/api/settings',{'location_ids':[]})
        self.request('/api/inventory',{'22428':{'quantity':1}})
        self.assertEqual(self.request('/api/plan?product_id=22428&quantity=1')[1]['queue'],[])
        self.request('/api/inventory',{'22428':{'quantity':None}})
        snapshots['assets']['fetched']=now
        snapshots['assets']['data']=[{'item_id':999,'type_id':22428,'quantity':1,'location_id':6001}]
        self.app.store.save_snapshots(123,snapshots)
        self.assertEqual(self.request('/api/plan?product_id=22428&quantity=1')[1]['queue'],[])

    def test_delivery_wait_exposes_real_cache_expiry_without_changing_saved_holds(self):
        from datetime import datetime,timezone
        now=time.time();self.seed_archon_stock();self.request('/api/settings',{'source':'eve'})
        status,result,_=self.request('/api/plans/save',{'product_id':92822,'quantity':1})
        self.assertEqual(status,200);plan_id=result['id'];before=self.app.store.plans()
        parts={k:{'data':[],'fetched':now-300,'expires':now+3600} for k in ['assets','blueprints','jobs']}
        parts['assets']['data']=[{'item_id':1,'type_id':23757,'quantity':1,'location_id':6001}]
        tid=16663;recipe=self.app.catalog.recipes[tid]
        parts['jobs']['data']=[{'job_id':7,'product_type_id':tid,'blueprint_type_id':recipe['bp_id'],
            'activity_id':9,'status':'delivered','runs':20,'output_location_id':6001,
            'completed_date':datetime.fromtimestamp(now-60,timezone.utc).isoformat()}]
        self.app.store.save_snapshots(123,parts)
        status,data,_=self.request('/api/plan?product_id=92822&quantity=1&saved_plan_id='+plan_id)
        self.assertEqual(status,400);wait=data['delivery_wait']
        self.assertEqual(wait['retry_at'],now+3600);self.assertEqual(wait['plan_name'],'Salvation')
        self.assertEqual(wait['items'][0]['id'],tid)
        self.assertNotIn('feloldhatod',data['error']);self.assertEqual(self.app.store.plans(),before)
        self.assertEqual(self.request('/api/state')[1]['delivery_wait'],wait)
        self.assertEqual(self.request('/api/plans/shopping')[1]['delivery_wait'],wait)
        # The exact same delivered jobs cease to block after an asset snapshot
        # newer than delivery arrives. Never add delivered output a second time.
        parts['assets']['fetched']=now
        parts['assets']['data'].append({'item_id':2,'type_id':tid,'quantity':4000,'location_id':6001})
        self.app.store.save_snapshots(123,parts)
        status,data,_=self.request('/api/plan?product_id=92822&quantity=1&saved_plan_id='+plan_id)
        self.assertEqual(status,200)
        row=next(r for r in data['rows'] if r['id']==tid)
        self.assertEqual(row['on_hand'],4000);self.assertEqual(row['wip_total'],0)
        self.assertIsNone(self.request('/api/state')[1]['delivery_wait'])

    def test_delivery_guard_ignores_covered_outputs_and_incompatible_job_recipes(self):
        from datetime import datetime,timezone
        now=time.time();self.app.store.add_character(123,'Pilot')
        job={'job_id':1,'product_type_id':22428,'blueprint_type_id':22429,'activity_id':1,'status':'delivered',
             'runs':1,'output_location_id':6001,'completed_date':datetime.fromtimestamp(now-10,timezone.utc).isoformat()}
        parts={k:{'data':[],'fetched':now-300,'expires':now+300} for k in ['assets','blueprints','jobs']}
        parts['jobs']['data']=[job]
        parts['assets']['data']=[{'item_id':1,'type_id':22428,'quantity':1,'location_id':6001}]
        self.app.store.save_snapshots(123,parts);self.request('/api/settings',{'source':'eve'})
        self.assertEqual(self.request('/api/plan?product_id=22428&quantity=1')[1]['queue'],[])
        parts['assets']['data']=[];parts['jobs']['data']=[{**job,'blueprint_type_id':999}]
        self.app.store.save_snapshots(123,parts)
        self.assertEqual(self.request('/api/plan?product_id=22428&quantity=1')[0],200)

    def test_blueprint_buy_and_saved_plans(self):
        self.request('/api/parameters',{'643':{'mode':'buy'}})
        result=self.request('/api/plan?product_id=22428&quantity=1')[1]
        self.assertIn(643,[row['id'] for row in result['shopping']])
        self.request('/api/plans/save',{'product_id':22428,'quantity':1,'name':'My Redeemer'})
        saved=self.request('/api/state')[1]['plans'][0]
        self.assertEqual(saved['name'],'My Redeemer')
        self.request('/api/plans/remove',{'id':saved['id']})
        self.assertEqual(self.request('/api/state')[1]['plans'],[])

    def test_manual_stock_still_uses_owned_salvation_bpcs_and_job_occupancy(self):
        now=time.time()
        self.app.store.add_character(123,'Test character')
        bp=dict(item_id=1,type_id=94072,quantity=-2,runs=2,material_efficiency=3,
                time_efficiency=2,location_id=6001)
        parts={kind:{'data':[],'fetched':now,'expires':now+300} for kind in ['assets','blueprints','jobs']}
        parts['blueprints']['data']=[bp,dict(bp,item_id=2)]
        parts['assets']['data']=[{'item_id':3,'type_id':92822,'quantity':10,'location_id':6001}]
        parts['jobs']['data']=[{'job_id':1,'product_type_id':92822,'blueprint_type_id':94072,'blueprint_id':1,
                              'runs':1,'activity_id':1,'status':'active','output_location_id':6001}]
        self.app.store.save_snapshots(123,parts)
        status,result,_=self.request('/api/plan?product_id=92822&quantity=4')
        self.assertEqual(status,200)
        row=next(r for r in result['rows'] if r['id']==92822);p=row['parameters']
        self.assertEqual((p['kind'],p['me'],p['te'],p['bpc_count'],p['available_runs']),('BPC',3,2,2,4))
        self.assertEqual((p['job_runs'],row['batches']),(2,[{'runs':2,'count':2}]))
        self.assertEqual((row['available'],row['wip'],row['missing']),(0,0,4))
        self.assertTrue(p['busy'])
        self.request('/api/settings',{'source':'eve'})
        row=next(r for r in self.request('/api/plan?product_id=92822&quantity=4')[1]['rows'] if r['id']==92822)
        self.assertEqual((row['available'],row['wip'],row['runs']),(10,1,0))
        self.assertEqual(row['parameters']['bpc_count'],2)
        self.request('/api/settings',{'source':'manual','location_ids':[6002]})
        p=next(r for r in self.request('/api/plan?product_id=92822&quantity=4')[1]['rows'] if r['id']==92822)['parameters']
        self.assertEqual((p['bpc_count'],p['source']),(0,'manual'))

    def test_auth_configuration_is_actionable_and_tokens_never_reach_browser(self):
        status,result,_=self.request('/api/auth/start',{})
        self.assertEqual(status,400);self.assertIn('Client ID',result['error'])
        self.request('/api/settings',{'client_id':'public-client'})
        result=self.request('/api/auth/start',{})[1]
        self.assertTrue(result['url'].startswith('https://login.eveonline.com/v2/oauth/authorize?'))
        self.assertNotIn('client_secret',result['url'])
        data=self.request('/api/state')[1]
        self.assertEqual(data['callback'],self.app.origin+'/callback')
        self.assertNotIn('access_token',json.dumps(data))

    def test_pi_routes_are_authenticated_and_independent_of_industry_source(self):
        from urllib.parse import urlsplit,parse_qs
        self.app.store.add_character(123,'Pilot')
        self.request('/api/settings',{'source':'eve','client_id':'public-client'})
        status,data,_=self.request('/api/pi?hours=6')
        self.assertEqual(status,200);self.assertEqual(data['characters'][0]['planet_count'],None)
        self.assertTrue(data['characters'][0]['needs_auth']);self.assertNotIn('access_token',json.dumps(data))
        self.assertEqual(self.request('/api/pi?hours=2')[0],400)
        self.assertEqual(self.request('/api/pi',Cookie='')[0],403)
        self.assertEqual(self.request('/api/pi/sync',{},Origin='https://evil.invalid')[0],403)
        self.app.eve.sync_pi=Mock(return_value=[{'id':123,'ok':True}])
        self.assertEqual(self.request('/api/pi/sync',{})[0],200)
        deadline=time.monotonic()+3
        while self.app.task['running'] and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(self.app.task['running']);self.assertEqual(self.app.store.settings()['source'],'eve')
        status,data,_=self.request('/api/auth/start',{'character_id':123,'feature':'pi'})
        self.assertEqual(status,200);query=parse_qs(urlsplit(data['url']).query)
        self.assertIn('esi-planets.manage_planets.v1',query['scope'][0])
        self.assertNotIn('esi-skills.read_skills.v1',query['scope'][0])

    def test_skill_endpoint_is_independent_of_missing_industry_data_and_character_filters(self):
        from datetime import datetime,timezone
        now=time.time()
        data={'skills':[],'total_sp':0,'unallocated_sp':0}
        queue=[{'skill_id':3300,'finished_level':3,'queue_position':0,
                'start_date':datetime.fromtimestamp(now-10,timezone.utc).isoformat(),
                'finish_date':datetime.fromtimestamp(now+86400,timezone.utc).isoformat()}]
        for char_id in [1,2]:
            self.app.store.add_character(char_id,'Pilot '+str(char_id))
            self.app.store.save_snapshots(char_id,{kind:{'data':payload,'fetched':now,'expires':now+60}
                for kind,payload in [('skills',data),('skillqueue',[] if char_id==1 else queue)]},domain='skills')
        self.request('/api/settings',{'source':'eve','character_ids':[1]})
        status,result,_=self.request('/api/skills')
        self.assertEqual(status,200);self.assertEqual(len(result['characters']),2)
        self.assertEqual((result['summary']['idle'],result['summary']['soon']),(1,1))
        self.assertNotIn('access_token',json.dumps(result))
        self.assertEqual(self.request('/api/skills',Cookie='')[0],403)
        self.assertEqual(self.request('/api/skills/sync',{},Origin='https://evil.invalid')[0],403)
        self.assertIsNone(self.app.store.characters()[0]['synced_at'])

    def test_skill_sync_does_not_switch_inventory_mode_and_auth_targets_existing_character(self):
        from urllib.parse import urlsplit,parse_qs
        self.app.store.add_character(123,'Pilot')
        self.app.eve.sync_skills=Mock(return_value=[{'id':123,'ok':True}])
        self.assertEqual(self.request('/api/skills/sync',{})[0],200)
        deadline=time.monotonic()+3
        while self.app.task['running'] and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(self.app.task['running'])
        self.assertEqual(self.app.store.settings()['source'],'manual')
        self.request('/api/settings',{'client_id':'public-client'})
        status,result,_=self.request('/api/auth/start',{'character_id':123})
        self.assertEqual(status,200)
        query=parse_qs(urlsplit(result['url']).query)
        self.assertIn('esi-skills.read_skills.v1',query['scope'][0])
        self.assertIn('esi-skills.read_skillqueue.v1',query['scope'][0])
        self.assertEqual(self.app.eve.pending[query['state'][0]]['character_id'],123)
        self.assertEqual(self.request('/api/auth/start',{'character_id':456})[0],400)


if __name__=='__main__':unittest.main()
