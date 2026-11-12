import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import Mock,patch
import unittest

from muhely.server import App,Server

ROOT=Path(__file__).resolve().parents[1]


class ServerTests(unittest.TestCase):
    def test_update_routes_require_local_session_csrf_and_never_accept_urls(self):
        self.assertEqual(self.request('/api/updates',Cookie='')[0],403)
        self.assertEqual(self.request('/updates.js')[0],200)
        self.app.updates.request=Mock(return_value={'phase':'checking'})
        self.assertEqual(self.request('/api/updates/check',{'manual':True},Origin='https://other.invalid')[0],403)
        self.assertEqual(self.request('/api/updates/check',{'url':'https://other.invalid'})[0],400)
        self.app.updates.request.assert_not_called()
        self.assertEqual(self.request('/api/updates/check',{'manual':True})[0],200)
        self.app.updates.request.assert_called_once_with('check',manual=True)
        self.app.task['running']=True
        self.assertEqual(self.request('/api/updates/download',{})[0],400)
        self.app.updates.request.assert_called_once()
        self.app.task['running']=False
        self.assertEqual(self.request('/api/updates/preferences',{'automatic':False})[0],200)
        self.assertFalse(self.app.store.settings()['updates']['automatic'])

    def test_preview_script_is_served_without_running_production_or_esi(self):
        with patch.object(self.app,'plan',side_effect=AssertionError('Preview must not calculate production')):
            status,body,headers=self.request('/preview.js')
        self.assertEqual(status,200)
        self.assertIn('javascript',headers['Content-Type'])
        self.assertIn(b'function renderPreview',body)
        self.assertIn(b'/preview.js',self.request('/')[1])

    def test_static_types_are_constants_and_request_paths_cannot_inject_headers(self):
        with patch('mimetypes.guess_type',return_value=('text/plain\r\nX-Injected: yes',None)):
            for path,expected in [('/app.js','text/javascript; charset=utf-8'),('/style.css','text/css; charset=utf-8'),('/icon.svg','image/svg+xml'),('/app-window-icon.png','image/png')]:
                status,_,headers=self.request(path)
                self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],expected)
                self.assertNotIn('X-Injected',headers)
        status,_,headers=self.request('/app.js%0d%0aX-Injected:%20yes')
        self.assertEqual(status,404);self.assertNotIn('X-Injected',headers)

    def test_preview_mining_routes_require_local_session_and_csrf_without_esi(self):
        self.assertEqual(self.request('/api/preview/mining',Cookie='')[0],403)
        self.app.preview_mining.snapshot=Mock(return_value={'enabled':True,'characters':[]})
        self.app.preview_mining.configure=Mock(return_value={'enabled':False,'characters':[]})
        self.app.preview_mining.replace_crystal=Mock(return_value={'enabled':True,'characters':[]})
        self.app.preview_mining.acknowledge=Mock(return_value={'enabled':True,'characters':[]})
        with patch.object(self.app,'plan',side_effect=AssertionError('Log badges must not plan or fetch ESI')):
            self.assertEqual(self.request('/api/preview/mining')[0],200)
            self.assertEqual(self.request('/api/preview/mining/configure',{'enabled':False,'folder':'test'},Origin='https://other.invalid')[0],403)
            self.app.preview_mining.configure.assert_not_called()
            self.assertEqual(self.request('/api/preview/mining/configure',{'enabled':False,'folder':'test'})[0],200)
            self.assertEqual(self.request('/api/preview/mining/replace-crystal',{'name':'Pilot','id':'a'*24})[0],200)
            self.assertEqual(self.request('/api/preview/mining/acknowledge',{'name':'Pilot','ids':['b'*24]})[0],200)
        self.app.preview_mining.replace_crystal.assert_called_once_with({'name':'Pilot','id':'a'*24})

    def test_learning_clone_routes_are_local_read_only_and_csrf_protected_for_refresh(self):
        self.assertEqual(self.request('/api/learning-clones',Cookie='')[0],403)
        self.assertEqual(self.request('/learning-clones.js')[0],200)
        with patch.object(self.app,'plan',side_effect=AssertionError('Monitoring must not calculate a plan')):
            status,data,_=self.request('/api/learning-clones')
        self.assertEqual(status,200);self.assertEqual(data['characters'],[])
        self.app.learning_clones.request=Mock(return_value={'status':{'running':True}})
        self.assertEqual(self.request('/api/learning-clones/refresh',{},Origin='https://other.invalid')[0],403)
        self.app.learning_clones.request.assert_not_called()
        self.assertEqual(self.request('/api/learning-clones/refresh',{})[0],200)
        self.app.learning_clones.request.assert_called_once()
        self.assertEqual(self.request('/api/learning-clones/claim',{})[1]['items'],[])

    def test_shared_locations_endpoint_validates_scope_and_ids_without_planning(self):
        self.assertEqual(self.request('/api/locations?ids=30000142',Cookie='')[0],403)
        with patch.object(self.app,'plan',side_effect=AssertionError('Location labels must not calculate a plan')):
            status,data,_=self.request('/api/locations?ids=30000142,30000142')
        self.assertEqual(status,200);self.assertEqual(data['locations_total'],1)
        self.assertEqual(data['locations']['30000142']['name'],'Jita')
        for query in ['ids=0','ids=no','ids=-1','ids=9007199254740992','ids=30000142&corporation_id=999','ids='+','.join(['30000142']*201)]:
            self.assertEqual(self.request('/api/locations?'+query)[0],400,query)
        self.assertEqual(self.request('/locations.js')[0],200)

    def test_market_history_is_public_esi_but_app_authenticated_region_scoped_and_no_planning(self):
        self.app.market_history.start=Mock()
        self.app.market_history.snapshot=Mock(return_value={'daily':[],'running':False})
        self.assertEqual(self.request('/api/market/history?type_id=35',Cookie='')[0],403)
        with patch.object(self.app,'plan',side_effect=AssertionError('History must not calculate a plan')):
            self.assertEqual(self.request('/api/market/history?type_id=35')[0],200)
        self.app.market_history.start.assert_called_once_with(10000002,35)
        for query in ['type_id=0','type_id=no','type_id=35&source=invalid','type_id=35&source=local']:
            self.assertEqual(self.request('/api/market/history?'+query)[0],400)
        self.app.trade.settings=Mock(return_value={'location':{'id':1234,'region_id':10000058}})
        self.assertEqual(self.request('/api/market/history?type_id=35&source=local')[0],200)
        self.app.market_history.start.assert_called_with(10000058,35)
        self.assertEqual(self.request('/api/market/history/refresh',{'type_id':35,'source':'local'},Origin='https://other.invalid')[0],403)
        self.assertEqual(self.request('/api/market/history/refresh',{'type_id':35,'source':'local'})[0],200)
        self.app.market_history.start.assert_called_with(10000058,35,manual=True)
        self.assertEqual(self.request('/market-history.js')[0],200)

    def test_contract_routes_are_authenticated_scoped_and_independent_of_planning(self):
        from muhely import contracts
        from test_contracts import contract,NOW
        self.app.store.add_character(1,'Pilot');self.app.store.character_corporation(1,99,'Corp')
        contracts.ingest(self.app.store,'personal',1,1,{'rows':[contract()],'fetched':NOW,'expires':NOW+300},now=NOW)
        self.assertEqual(self.request('/api/contracts',Cookie='')[0],403)
        with patch.object(self.app,'plan',side_effect=AssertionError('Contracts must not calculate production')):
            status,data,_=self.request('/api/contracts')
        self.assertEqual(status,200);self.assertEqual(data['rows'][0]['contract_id'],1)
        self.assertEqual(self.request('/api/contracts?scope=corporation')[1]['rows'],[])
        for path in ['/api/contracts?scope=invalid','/api/contracts?owner=999','/api/contracts?start=invalid','/api/contracts?start=2026-10-25&end=2026-10-01','/api/contracts/details?owner=999&id=1','/api/contracts/details?owner=no&id=1']:
            self.assertEqual(self.request(path)[0],400,path)
        self.assertEqual(self.request('/contracts.js')[0],200)
        self.app.start_task=Mock()
        self.assertEqual(self.request('/api/contracts/sync',{},Origin='https://other.invalid')[0],403);self.app.start_task.assert_not_called()
        self.assertEqual(self.request('/api/contracts/sync',{})[0],200);self.app.start_task.assert_called_once_with('contracts',manual=False)
        self.app.start_task.reset_mock();self.app.eve.finish=Mock(return_value=1);self.app.eve.authorized_feature='contracts'
        self.assertEqual(self.request('/callback?state=test&code=test')[0],303);self.app.start_task.assert_called_once_with('contracts')

    def test_implant_routes_require_session_and_csrf_and_reject_unknown_characters(self):
        self.app.store.add_character(123,'Pilot')
        self.assertEqual(self.request('/api/implants',Cookie='')[0],403)
        body={'characters':[{'id':123,'enabled':True,'threshold':'1000000000'}]}
        self.assertEqual(self.request('/api/implants/preferences',body,Origin='https://other.invalid')[0],403)
        status,data,_=self.request('/api/implants/preferences',body)
        self.assertEqual(status,200);self.assertTrue(data['characters'][0]['enabled']);self.assertFalse(data['characters'][0]['authorized'])
        self.assertEqual(self.request('/api/implants/claim',{})[1]['items'],[])
        self.assertEqual(self.request('/api/implants/preferences',{'characters':[dict(body['characters'][0],id=999)]})[0],400)

    def test_full_asset_browser_is_authenticated_and_independent_of_planning(self):
        self.app.store.add_character(123,'Asset Pilot')
        now=time.time();snapshot={'data':[dict(item_id=1,type_id=23757,quantity=1,location_id=6001,is_singleton=True,location_flag='Hangar')],'fetched':now,'expires':now+600,'etag':None}
        self.app.store.save_snapshots(123,{'assets':snapshot})
        self.assertEqual(self.request('/api/assets',Cookie='')[0],403)
        with patch.object(self.app,'plan',side_effect=AssertionError('Must not calculate a plan')):
            status,data,_=self.request('/api/assets')
        self.assertEqual(status,200);self.assertEqual(data['quantity'],1)
        self.assertEqual(data['rows'][0]['name'],'Archon')
        self.assertEqual(self.request('/api/assets?corporation_id=999')[0],400)
        self.app.store.character_corporation(123,99,'Corp A')
        self.app.store.save_corporation_snapshots(99,123,{'assets':dict(snapshot,data=[dict(snapshot['data'][0],quantity=7)])})
        status,data,_=self.request('/api/assets?corporation_id=99')
        self.assertEqual(status,200);self.assertEqual(data['quantity'],7)
        self.assertEqual(data['rows'][0]['owner_name'],'Corp A')
        self.assertEqual(self.request('/assets.js')[0],200)

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
        return status,json.loads(raw) if raw and 'application/json' in h.get('Content-Type','') else raw,h

    def test_all_access_route_is_character_bound_and_preserves_individual_routes(self):
        self.app.store.add_character(123,'Test')
        self.app.eve.start=Mock(return_value='https://login.eveonline.com/authorize')
        for feature in ['all','skills','pi','corporations','moons','intel','mining','implants','contracts']:
            status,data,_=self.request('/api/auth/start',{'character_id':123,'feature':feature})
            self.assertEqual(status,200)
            self.assertEqual(data['url'],'https://login.eveonline.com/authorize')
            self.app.eve.start.assert_called_with(self.app.cookie,self.app.origin+'/callback',123,feature)
        self.app.eve.start.reset_mock()
        self.assertEqual(self.request('/api/auth/start',{'character_id':456,'feature':'all'})[0],400)
        self.assertEqual(self.request('/api/auth/start',{'character_id':123,'feature':'invalid'})[0],400)
        self.app.eve.start.assert_not_called()

    def test_intel_routes_keep_settings_private_and_validate_scope(self):
        self.assertEqual(self.request('/api/intel',Cookie='')[0],403)
        self.assertEqual(self.request('/api/intel/preferences',{'enabled':False},Origin='https://other.invalid')[0],403)
        self.assertEqual(self.request('/api/intel/preferences',{'jumps':100})[0],400)
        status,data,_=self.request('/api/intel');self.assertEqual(status,200);self.assertFalse(data['preferences']['enabled']);self.assertEqual(data['reports'],[])
        self.assertEqual(self.request('/api/intel?radius=13')[0],400)
        status,data,_=self.request('/api/intel/systems?q=Jita');self.assertEqual(status,200);self.assertEqual(data[0]['name'],'Jita')
        # Chat monitoring starts disabled; the independent public kill feed is enabled.
        status,data,_=self.request('/api/intel/alerts');self.assertEqual(status,200);self.assertTrue(data['enabled']);self.assertEqual(data['items'],[])
        self.assertEqual(self.request('/api/intel/preferences',{'killfeed_enabled':False})[0],200)
        self.assertFalse(self.request('/api/intel/alerts')[1]['enabled'])
        self.assertEqual(self.request('/api/intel/claim',{})[1]['items'],[])
        self.assertEqual(self.request('/intel.js')[0],200)

    def test_pilot_lookup_trigger_is_local_and_ship_images_use_only_the_ccp_cdn(self):
        self.app.intel.request_characters=Mock()
        self.assertEqual(self.request('/api/intel/characters',{},Origin='https://other.invalid')[0],403);self.app.intel.request_characters.assert_not_called()
        self.assertEqual(self.request('/api/intel/characters',{})[0],200);self.app.intel.request_characters.assert_called_once_with(manual=True,preload=True)
        _,_,headers=self.request('/');self.assertIn("img-src 'self' data: https://images.evetech.net",headers['Content-Security-Policy']);self.assertIn("script-src 'self'",headers['Content-Security-Policy'])
        self.assertEqual(self.request('/api/intel?region=999')[0],400)

    def test_intel_location_refresh_is_a_separate_background_worker(self):
        self.app.intel.request_locations=Mock()
        status,data,_=self.request('/api/intel/locations',{});self.assertEqual(status,200);self.assertIn('intel',data);self.app.intel.request_locations.assert_called_once()
        self.assertFalse(self.app.task['running'])
        self.app.eve.finish=Mock(return_value=1);self.app.eve.authorized_feature='intel'
        self.assertEqual(self.request('/callback?state=test&code=test')[0],303);self.assertEqual(self.app.intel.request_locations.call_count,2)

    def test_moon_calendar_and_crystal_routes_are_local_and_validate_ids(self):
        status,body,_=self.request('/extractions.js');self.assertEqual(status,200);self.assertIn(b'renderMoonCalendar',body)
        status,data,_=self.request('/api/moons');self.assertEqual(status,200);self.assertEqual(data['extractions']['events'],[])
        status,_,_=self.request('/api/moons/crystals?moon_id=unknown');self.assertEqual(status,400)
        self.app.start_task=Mock()
        status,_,_=self.request('/api/moons/extractions/sync',{},Origin='http://other.local');self.assertEqual(status,403);self.app.start_task.assert_not_called()
        status,_,_=self.request('/api/moons/extractions/sync',{});self.assertEqual(status,200);self.app.start_task.assert_called_once_with('extractions',manual=False)

    def test_accounts_and_scheduler_routes_require_local_authorization(self):
        self.assertEqual(self.request('/api/accounts')[0],200)
        self.assertEqual(self.request('/api/accounts',{'accounts':[],'characters':{}},Origin='https://evil.invalid')[0],403)
        self.assertEqual(self.request('/api/accounts',{'accounts':[],'characters':{}})[0],200)
        self.assertEqual(self.request('/api/schedule',{'product_id':590,'quantity':1},Origin='https://evil.invalid')[0],403)
        status,result,_=self.request('/api/schedule',{'product_id':590,'quantity':1})
        self.assertEqual(status,200);self.assertFalse(result['complete']);self.assertTrue(result['blocked'])
        self.assertEqual(self.request('/api/schedule',{'product_id':590,'quantity':1,'characters':[999]})[0],400)
        self.assertEqual(self.request('/api/schedule',{'product_id':590,'quantity':1,'owned_only':'yes'})[0],400)

    def test_moon_authorization_callback_starts_refresh_and_handles_invalid_scope(self):
        self.app.eve.finish=Mock(return_value=1);self.app.eve.authorized_feature='moons';self.app.start_task=Mock()
        status,_,headers=self.request('/callback?state=test&code=test')
        self.assertEqual(status,303);self.assertEqual(headers['Location'],'/?connected=1');self.app.start_task.assert_called_once_with('extractions')
        status,body,_=self.request('/callback?error=invalid_scope')
        self.assertEqual(status,400);self.assertIn(b'Developer',body)

    def test_bundled_user_guides_are_available_without_characters_but_require_a_local_session(self):
        for language,title in [('hu','teljes felhasználói kézikönyv'),('en','complete user guide')]:
            status,data,headers=self.request('/api/documentation?lang='+language)
            self.assertEqual(status,200);self.assertEqual(data['language'],language)
            self.assertIn(title,data['markdown']);self.assertGreater(len(data['markdown']),30000)
            self.assertIn('no-store',headers['Cache-Control'])
        self.assertEqual(self.app.store.characters(),[])
        self.assertEqual(self.request('/api/documentation?lang=en',Cookie='')[0],403)
        self.assertEqual(self.request('/api/documentation?lang=../../characters.enc')[0],400)
        self.assertEqual(self.request('/api/documentation?lang=hu',Host='evil.invalid')[0],403)

    def test_manual_plan_and_search_work_without_any_eve_account(self):
        status,plan,_=self.request('/api/plan?product_id=22428&quantity=1')
        self.assertEqual(status,200);self.assertTrue(plan['queue'])
        self.assertEqual(plan['summary']['items'],45)
        for row in plan['queue']:
            self.assertEqual(row['input_readiness']['status'],'missing')
            self.assertEqual(row['input_readiness']['location_status'],'unknown')
        status,rows,_=self.request('/api/search?q=Hulk')
        self.assertEqual(status,200);self.assertTrue(rows)
        status,_,headers=self.request('/')
        self.assertIn('HttpOnly',headers['Set-Cookie'])
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        for path in ['/readiness.js','/graph.js','/graph.css','/skills.js','/pi.js','/numbers.js','/i18n.js','/i18n-en.js','/settings.js','/accounts.js','/schedule.js','/schedule-graph.js','/multibuy.js','/documentation.js']:
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

    def test_confirmed_allocations_survive_delivered_job_inventory_lag_for_every_saved_plan(self):
        from datetime import datetime,timezone
        now=time.time();self.seed_archon_stock();self.request('/api/settings',{'source':'eve'})
        ids={}
        for product,quantity in [(92822,1),(12038,50)]:
            code,data,_=self.request('/api/plans/save',{'product_id':product,'quantity':quantity})
            self.assertEqual(code,200);ids[product]=data['id']
        old=self.request('/api/state')[1]
        original={p['id']:p['allocation'] for p in old['plans']};before=self.app.store.plans()
        parts={k:self.app.store.snapshot(123,k) for k in ['assets','blueprints','jobs']}
        parts['assets']['fetched']=now-300;parts['assets']['expires']=now+3600
        recipe=self.app.catalog.recipes[16678]
        parts['jobs']['data']=[{'job_id':19,'product_type_id':16678,'blueprint_type_id':recipe['bp_id'],'activity_id':9,'status':'delivered','runs':10,'output_location_id':6001,'completed_date':datetime.fromtimestamp(now-60,timezone.utc).isoformat()}]
        self.app.store.save_snapshots(123,parts)
        state=self.request('/api/state')[1];self.assertIsNotNone(state['delivery_wait'])
        for saved in state['plans']:
            self.assertEqual(saved['allocation'],original[saved['id']]);self.assertTrue(saved['allocation_frozen_at'])
        for product,quantity in [(92822,1),(12038,50)]:
            code,plan,_=self.request(f'/api/plan?product_id={product}&quantity={quantity}&saved_plan_id={ids[product]}&preview=1')
            self.assertEqual(code,200);self.assertTrue(plan['frozen_snapshot']);self.assertTrue(plan['preview_only'])
            self.assertEqual(plan['reservation_summary']['own'],original[ids[product]])
        self.assertEqual(self.app.store.plans(),before)
        self.assertEqual(self.request('/api/plans/save',{'id':ids[12038],'product_id':12038,'quantity':50})[0],400)
        parts['assets']['fetched']=now;self.app.store.save_snapshots(123,parts)
        fresh=self.request('/api/state')[1];self.assertIsNone(fresh['delivery_wait']);self.assertTrue(all(not p.get('allocation_frozen_at') for p in fresh['plans']))

    def test_pending_delivery_allows_previews_for_all_personal_plans_but_never_commits_holds(self):
        from datetime import datetime,timezone
        now=time.time();self.seed_archon_stock();self.request('/api/settings',{'source':'eve'})
        ids={}
        for product,quantity in [(92822,1),(12038,50),(12034,50)]:
            code,value,_=self.request('/api/plans/save',{'product_id':product,'quantity':quantity})
            self.assertEqual(code,200);ids[product]=value['id']
        before=self.app.store.plans();parts={k:self.app.store.snapshot(123,k) for k in ['assets','blueprints','jobs']}
        parts['assets']['fetched']=now-300;parts['assets']['expires']=now+3600
        parts['assets']['data'].append({'item_id':2,'type_id':16678,'quantity':25,'location_id':6001})
        recipe=self.app.catalog.recipes[16678]
        parts['jobs']['data']=[{'job_id':19,'product_type_id':16678,'blueprint_type_id':recipe['bp_id'],'activity_id':9,'status':'delivered','runs':10,'output_location_id':6001,'completed_date':datetime.fromtimestamp(now-60,timezone.utc).isoformat()}]
        self.app.store.save_snapshots(123,parts)
        for product,quantity in [(92822,1),(12038,50),(12034,50),(590,10)]:
            path=f'/api/plan?product_id={product}&quantity={quantity}'+('&saved_plan_id='+ids[product] if product in ids else '')
            self.assertEqual(self.request(path)[0],400)
            code,preview,_=self.request(path+'&preview=1');self.assertEqual(code,200)
            self.assertTrue(preview['preview_only']);self.assertTrue(preview['reservation_summary']['provisional']);self.assertTrue(preview['queue'])
            self.assertEqual(preview['inventory_wait']['retry_at'],now+3600)
            row=next((r for r in preview['rows'] if r['id']==16678),None)
            if row:self.assertEqual((row['on_hand'],row['wip_total']),(25,0))
        self.assertEqual(self.request('/api/plans/shopping')[0],400)
        code,summary,_=self.request('/api/plans/shopping?preview=1');self.assertEqual(code,200);self.assertTrue(summary['preview_only']);self.assertTrue(summary['rows'])
        # A client cannot bypass strict saving/activation/scheduling with flags.
        for data in [{'product_id':590,'quantity':10,'preview_only':True},{'id':ids[12038],'product_id':12038,'quantity':51,'preview_only':True}]:self.assertEqual(self.request('/api/plans/save',data)[0],400)
        self.assertEqual(self.request('/api/plans/reservation',{'id':ids[12038],'active':True,'preview_only':True})[0],400)
        self.assertEqual(self.request('/api/schedule',{'product_id':12038,'quantity':50,'saved_plan_id':ids[12038],'preview_only':True})[0],400)
        self.assertEqual(self.app.store.plans(),before)
        parts['assets']['fetched']=now;parts['assets']['data'][-1]['quantity']=10025;self.app.store.save_snapshots(123,parts)
        code,final,_=self.request('/api/plan?product_id=12038&quantity=50&saved_plan_id='+ids[12038]+'&preview=1')
        self.assertEqual(code,200);self.assertFalse(final.get('preview_only',False));self.assertFalse(final['reservation_summary']['provisional'])
        row=next(r for r in final['rows'] if r['id']==16678);self.assertEqual((row['on_hand'],row['wip_total']),(10025,0))
        self.assertEqual(self.app.store.plans(),before)

    def test_personal_pending_previews_do_not_contaminate_corporation_plans(self):
        from datetime import datetime,timezone
        now=time.time();self.seed_archon_stock();self.request('/api/settings',{'source':'eve'})
        code,value,_=self.request('/api/plans/save',{'product_id':92822,'quantity':1});self.assertEqual(code,200)
        parts={k:self.app.store.snapshot(123,k) for k in ['assets','blueprints','jobs']};parts['assets']['fetched']=now-300
        tid=16678;recipe=self.app.catalog.recipes[tid]
        parts['jobs']['data']=[{'job_id':19,'product_type_id':tid,'blueprint_type_id':recipe['bp_id'],'activity_id':9,'status':'delivered','runs':10,'output_location_id':6001,'completed_date':datetime.fromtimestamp(now-60,timezone.utc).isoformat()}]
        self.app.store.save_snapshots(123,parts);self.app.store.character_corporation(123,99,'Other Corp')
        self.app.store.save_corporation_snapshots(99,123,{k:{'data':[],'fetched':now,'expires':now+3600} for k in ['assets','blueprints','jobs']})
        code,preview,_=self.request('/api/plan?product_id=590&quantity=1&preview=1');self.assertEqual(code,200);self.assertTrue(preview['preview_only'])
        code,corp,_=self.request('/api/plan?product_id=590&quantity=1&corporation_id=99&preview=1');self.assertEqual(code,200);self.assertFalse(corp.get('preview_only',False));self.assertEqual(corp['corporation_id'],99)

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

    def test_notification_dismiss_requires_session_csrf_and_a_current_event(self):
        from muhely import notifications
        self.app.store.add_character(1,'Pilot')
        data=self.request('/api/notifications')[1]
        item=next(a for a in data['items'] if a['category']=='data')
        body={'id':item['id'],'dismissal_key':item['dismissal_key']}
        self.assertEqual(self.request('/api/notifications/dismiss',body,Cookie='')[0],403)
        self.assertEqual(self.request('/api/notifications/dismiss',body,Origin='https://other.invalid')[0],403)
        self.assertEqual(self.request('/api/notifications/dismiss',{'id':'missing','dismissal_key':'0'*64})[0],400)
        self.assertEqual(self.request('/api/notifications/dismiss',body)[0],200)
        self.assertFalse(any(a['id']==item['id'] for a in self.request('/api/notifications')[1]['items']))
        self.assertEqual(self.request('/api/notifications/dismiss',body)[0],200)

    def test_notification_api_separates_owners_and_persists_os_receipts(self):
        from datetime import datetime,timezone
        self.app.store.add_character(1,'Pilot');self.app.store.character_corporation(1,99,'Corp A')
        now=time.time();snap=lambda data:{'data':data,'fetched':now,'expires':now+600}
        job={'job_id':123,'status':'ready','product_type_id':590,'runs':1,'installer_id':1,'end_date':datetime.fromtimestamp(now-10,timezone.utc).isoformat()}
        self.app.store.save_snapshots(1,{'jobs':snap([job,{**job,'job_id':124}])})
        self.app.store.save_corporation_snapshots(99,1,{'jobs':snap([job])})
        self.assertEqual(self.request('/api/notifications',Cookie='')[0],403)
        status,data,_=self.request('/api/notifications');self.assertEqual(status,200)
        rows=[a for a in data['items'] if a['category']=='jobs']
        self.assertEqual({(a['job_id'],a['corporation_id']) for a in rows},{(123,99),(124,None)})
        self.assertEqual(self.request('/api/notifications/claim',{})[1]['items'],[])
        self.assertEqual(self.request('/api/notifications/preferences',{'os_enabled':True},Origin='https://other.example')[0],403)
        self.assertEqual(self.request('/api/notifications/preferences',{'moon_days':31})[0],400)
        self.request('/api/notifications/preferences',{'os_enabled':True})
        self.app.task['running']=True
        self.assertEqual(self.request('/api/notifications/claim',{})[1]['items'],[])
        self.app.task['running']=False
        claims=self.request('/api/notifications/claim',{})[1]['items'];self.assertEqual(len(claims),2)
        self.request('/api/notifications/sent',{'receipts':[a['receipt'] for a in claims]})
        self.assertEqual(self.request('/api/notifications/claim',{})[1]['items'],[])
        self.assertIn(b'renderNotifications',self.request('/notifications.js')[1])
        self.assertNotIn('access_token',json.dumps(data));self.assertNotIn('refresh_token',json.dumps(data))

    def test_background_notification_sync_respects_cooldown_and_keeps_inventory_mode(self):
        self.app.store.add_character(1,'Pilot')
        self.app.eve.sync=Mock(return_value=[{'id':1,'ok':True}]);self.app.eve.sync_skills=Mock(return_value=[]);self.app.eve.sync_pi=Mock(return_value=[])
        self.request('/api/notifications/sync',{})
        for _ in range(100):
            if not self.app.task['running']:break
            time.sleep(.01)
        self.request('/api/notifications/sync',{})
        self.assertEqual(self.app.eve.sync.call_count,1)
        self.assertEqual(self.app.store.settings()['source'],'manual')
        self.request('/api/notifications/sync',{'manual':True})
        for _ in range(100):
            if not self.app.task['running']:break
            time.sleep(.01)
        self.assertEqual(self.app.eve.sync.call_count,2)

    def test_desktop_auth_handoff_is_one_use_and_browser_callback_resumes_window(self):
        from urllib.parse import urlsplit,parse_qs
        self.request('/api/settings',{'client_id':'public-client'})
        status,auth,_=self.request('/api/auth/start',{'desktop':True})
        self.assertEqual(status,200);self.assertTrue(auth['url'].startswith(self.app.origin+'/desktop/auth/'))
        path=urlsplit(auth['url']).path
        # The external browser has no application's session cookie yet.
        code,_,headers=self.request(path,Cookie='')
        self.assertEqual(code,303);self.assertIn('eve_session=',headers['Set-Cookie'])
        self.assertTrue(headers['Location'].startswith('https://login.eveonline.com/v2/oauth/authorize?'))
        state=parse_qs(urlsplit(headers['Location']).query)['state'][0]
        self.assertEqual(self.request(path,Cookie='')[0],404)
        poll='/api/desktop/auth?ticket='+auth['ticket']
        self.assertEqual(self.request(poll,Cookie='')[0],403)
        self.assertEqual(self.request(poll)[1],{'status':'pending','error':None})
        self.app.eve.finish=Mock();self.app.eve.authorized_feature=None
        code,page,_=self.request('/callback?state='+state+'&code=fake')
        self.assertEqual(code,200);self.assertIn(b'Return to the EVE Workshop application',page)
        self.app.eve.finish.assert_called_once_with(state,'fake',self.app.cookie)
        data=self.request(poll)[1];self.assertEqual(data,{'status':'complete','error':None})
        self.assertNotIn('access_token',str(data));self.assertNotIn('code',str(data))

    def test_desktop_auth_expiry_failures_and_untrusted_starts(self):
        from urllib.parse import urlsplit,parse_qs
        self.assertEqual(self.request('/api/auth/start',{'desktop':True},Origin='https://other.example')[0],403)
        self.request('/api/settings',{'client_id':'public-client'})
        auth=self.request('/api/auth/start',{'desktop':True})[1]
        ticket=auth['ticket'];entry=self.app.desktop_auth[ticket]
        state=entry['oauth_state']
        code,_,_=self.request('/callback?state='+state+'&error=invalid_scope')
        self.assertEqual(code,400)
        result=self.request('/api/desktop/auth?ticket='+ticket)[1]
        self.assertEqual(result['status'],'error');self.assertIn('scope',result['error'])
        entry['expires']=time.time()-1
        self.assertEqual(self.request(urlsplit(auth['url']).path,Cookie='')[0],404)
        self.assertEqual(self.request('/api/desktop/auth?ticket='+ticket)[1]['status'],'error')
        self.assertEqual(self.request('/desktop/auth/not-a-ticket',Cookie='')[0],404)

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

    def test_activity_is_authenticated_and_reports_real_background_phases(self):
        from muhely import progress
        entered=threading.Event();release=threading.Event()
        self.app.store.add_character(1,'Progress Pilot')
        self.assertEqual(self.request('/api/activity',Cookie='')[0],403)
        def industry():
            progress.report(subject='Progress Pilot',completed=2,total=10,resource='Készlet',mode='cache',page=2,pages=5,access_token='must not appear')
            entered.set();release.wait(5)
            return [{'id':1,'ok':True}]
        self.app.eve.sync=industry
        self.app.eve.sync_skills=Mock(return_value=[{'id':1,'ok':False,'error':'Missing skills grant'}])
        self.app.eve.sync_pi=Mock(return_value=[])
        self.app.start_task('notifications')
        try:
            self.assertTrue(entered.wait(2));status,data,_=self.request('/api/activity')
            self.assertEqual(status,200);task=data['task'];p=task['progress']
            self.assertTrue(task['running']);self.assertEqual(p['stage'],'Személyes ipari adatok')
            self.assertEqual((p['completed'],p['total'],p['page'],p['pages'],p['mode']),(2,10,2,5,'cache'))
            self.assertEqual(p['stages'],3);self.assertNotIn('must not appear',json.dumps(data));self.assertNotIn('access_token',json.dumps(data))
        finally:release.set()
        for _ in range(200):
            if not self.app.task['running']:break
            time.sleep(.01)
        done=self.request('/api/activity')[1]['task']
        self.assertFalse(done['running']);self.assertEqual(done['id'],task['id']);self.assertEqual(done['outcome'],'warning')
        self.assertEqual(self.app.store.settings()['source'],'manual')
        self.assertEqual(self.request('/activity.js')[0],200)

    def test_activity_marks_failed_tasks_without_false_completion(self):
        self.app.start_task('skills')
        for _ in range(200):
            if not self.app.task['running']:break
            time.sleep(.01)
        task=self.request('/api/activity')[1]['task']
        self.assertFalse(task['running']);self.assertEqual(task['outcome'],'error');self.assertFalse(task['results'][0]['ok'])

    def test_optional_moon_sources_do_not_mark_refresh_failed_but_real_errors_do(self):
        self.app.store.add_character(1,'Moon Reader')
        optional=[{'id':1,'kind':'calendar','ok':True}, {'id':1,'kind':'notifications','ok':True},
                  {'id':1,'kind':'timers','ok':False,'warning':False,'reason':'role_denied','error':'Station Manager'}]
        for kind in ['extractions','sync']:
            self.app.eve.sync=Mock(return_value=[{'id':1,'ok':True}])
            self.app.eve.sync_skills=Mock(return_value=[]);self.app.eve.sync_pi=Mock(return_value=[])
            self.app.store.save_snapshots(1,{'moon_calendar':{'data':[],'fetched':time.time(),'expires':time.time()+600,'etag':None}},domain='moon_calendar')
            for fail in [False,True]:
                # Each scenario exercises a real request; daily spacing itself
                # is covered separately by the refresh-policy tests.
                with self.app.store.db() as db:db.execute("DELETE FROM refresh_attempts WHERE domain='extractions'")
                rows=optional+[{'id':1,'kind':'calendar','ok':False,'error':'offline'}] if fail else optional
                with self.subTest(kind=kind,fail=fail),patch('muhely.server.extractions.sync',return_value=rows):
                    self.app.start_task(kind)
                    for _ in range(200):
                        if not self.app.task['running']:break
                        time.sleep(.01)
                    task=self.app.task_snapshot()
                    self.assertFalse(task['running']);self.assertEqual(task['outcome'],'warning' if fail else 'success')
                    self.assertIn('naptár 1, értesítések 1',task['message'])
                    self.assertIn('Station Manager',task['message'])
                    self.assertNotIn('Néhány holdadat nem frissült',task['message'])
                    if fail:self.assertIn('Moon Reader · Naptár: offline',task['message'])


if __name__=='__main__':unittest.main()
