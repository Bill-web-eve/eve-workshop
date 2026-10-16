from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import tempfile,time,unittest
from muhely.industry_costs import IndustryCosts,normalize,cache_expiry
from muhely.store import Store
from muhely.server import validated_settings
from muhely.esi import EsiError
from muhely.planner import PlanningError

def systems():return [{'solar_system_id':10,'cost_indices':[{'activity':'manufacturing','cost_index':.1},{'activity':'reaction','cost_index':.2}]}]
def prices():return [{'type_id':35,'adjusted_price':2.5},{'type_id':36,'adjusted_price':3}]
def catalog():return SimpleNamespace(name=lambda i:str(i),moon_systems={10:{'name':'Test'}},recipes={1:{'activity':'manufacturing','materials':[{'typeID':35,'quantity':10},{'typeID':36,'quantity':4}]},2:{'activity':'reaction','materials':[{'typeID':35,'quantity':20}]}})
class IndustryCostTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=Store(self.tmp.name);self.now=1000
        self.http=Mock(blocked_until=0);self.http.request.side_effect=[(systems(),{'ETag':'systems','Cache-Control':'max-age=3600'}),(prices(),{'ETag':'prices','Cache-Control':'max-age=3600'})]
        self.service=IndustryCosts(self.s,self.http,lambda:self.now);self.c=catalog()
        self.settings=self.s.settings()
        for a in ['manufacturing','reaction']:self.settings[a]['system_id']=10
    def test_public_caching_etag_and_restart(self):
        self.service.refresh();self.service.refresh();self.assertEqual(self.http.request.call_count,2)
        self.assertNotIn('token',self.http.request.call_args.kwargs)
        self.assertFalse(self.service.status()['resources']['prices']['stale'])
        self.now=4601;self.http.request.side_effect=[(None,{'Cache-Control':'max-age=3600'}),(None,{'Cache-Control':'max-age=3600'})]
        self.service.refresh();self.assertEqual(self.http.request.call_args.kwargs['headers'],{'If-None-Match':'prices'})
        other=IndustryCosts(Store(self.tmp.name),Mock(),lambda:self.now)
        self.assertEqual(other.system(10,self.c)['indices']['reaction'],'0.2')
        self.assertEqual(other.status()['resources']['prices']['checked'],4601)
    def test_post_viridian_eiv_and_component_taxes_per_job(self):
        self.service.refresh();rows=[{'id':1,'batches':[{'runs':2,'count':3}]},{'id':2,'batches':[{'runs':1,'count':2}]}]
        result=self.service.estimate(rows,self.settings,self.c)
        self.assertEqual(result['cents'],'6202');self.assertTrue(result['complete'])
        mfg=result['rows'][0];self.assertEqual(mfg['eiv_per_run'],'37.0');self.assertEqual(mfg['cents'],'3552')
        self.assertEqual(mfg['components'],{'system':'2109','facility':'555','scc':'888','alpha':'0'})
        self.assertEqual(result['rows'][1]['cents'],'2650')
        # Material bonuses and Jita order prices are not part of the fee basis.
        self.settings['manufacturing']['material_role']=90;self.settings['manufacturing']['material_rig']=90
        self.assertEqual(self.service.estimate(rows,self.settings,self.c)['cents'],result['cents'])
    def test_missing_index_or_adjusted_price_is_not_a_zero_job_cost(self):
        row=[{'id':1,'batches':[{'runs':1,'count':1}]}]
        self.assertFalse(self.service.estimate(row,self.settings,self.c)['complete'])
        self.service.refresh();self.settings['manufacturing']['system_id']=None
        result=self.service.estimate(row,self.settings,self.c);self.assertIsNone(result['rows'][0]['cents']);self.assertTrue(result['rows'][0]['missing_system'])
        self.settings['manufacturing']['system_id']=10
        self.s.save_universe_cache('industry-prices',0,{'values':{'35':'2.5'},'expires':5000},1000)
        result=self.service.estimate(row,self.settings,self.c);self.assertEqual(result['rows'][0]['missing_prices'],[36]);self.assertFalse(result['complete'])
    def test_alpha_and_separate_activity_systems(self):
        self.service.refresh();row=[{'id':1,'batches':[{'runs':1,'count':1}]}]
        self.settings['manufacturing']['alpha_surcharge']=.25
        self.assertEqual(self.service.estimate(row,self.settings,self.c)['rows'][0]['components']['alpha'],'9')
        self.settings['reaction']['system_id']=None
        self.assertTrue(self.service.estimate(row,self.settings,self.c)['complete'])
        self.assertFalse(self.service.estimate([{'id':2,'batches':[{'runs':1,'count':1}]}],self.settings,self.c)['complete'])
    def test_failed_snapshot_retains_old_prices_and_retries_with_backoff(self):
        self.service.refresh();old=self.service.cached('prices');self.now=5000
        self.http.request.side_effect=[(systems(),{}),([{'type_id':35,'adjusted_price':float('nan')}],{})]
        self.service.refresh();self.assertEqual(self.service.cached('prices'),old)
        self.assertTrue(self.service.status()['resources']['prices']['stale']);self.assertEqual(self.service.status()['retry_after'],5060)
        self.assertIn('prices',self.service.status()['errors'])
        calls=self.http.request.call_count;self.service.start();self.assertEqual(self.http.request.call_count,calls)
    def test_empty_no_jobs_is_zero_without_requiring_facilities(self):
        self.assertEqual(self.service.estimate([],self.s.settings(),self.c)['cents'],'0')
        self.assertTrue(self.service.estimate([],self.s.settings(),self.c)['complete'])
    def test_invalid_data_and_batches_rejected(self):
        for kind,data in [('systems',[]),('prices',[]),('prices',[{'type_id':35,'adjusted_price':True}]),('systems',[{'solar_system_id':10,'cost_indices':[{'activity':'reaction','cost_index':2}]}]),('prices',prices()+prices())]:
            with self.subTest(kind=kind,data=data),self.assertRaises(EsiError):normalize(kind,data)
        for rows in [[{'id':1,'batches':[{'runs':0,'count':1}]}],[{'id':1,'batches':[{'runs':100000000,'count':2}]}],[{'id':99,'batches':[]}],[{'id':1,'batches':[None]}],[{'id':1,'batches':[]}]*2]:
            with self.subTest(rows=rows),self.assertRaises(PlanningError):self.service.estimate(rows,self.settings,self.c)
    def test_legacy_settings_merge_new_fields_without_replacing_bonuses(self):
        self.s.save_settings({'manufacturing':{'material_role':7,'skill_time':.8}})
        settings=Store(self.tmp.name).settings();self.assertEqual(settings['manufacturing']['material_role'],7);self.assertEqual(settings['manufacturing']['skill_time'],.8)
        self.assertEqual(settings['manufacturing']['scc_surcharge'],4);self.assertIsNone(settings['manufacturing']['system_id'])
        edited=validated_settings({'manufacturing':{'system_id':10,'facility_tax':.25}},settings)
        self.assertEqual(edited['manufacturing']['material_role'],7);self.assertEqual(edited['manufacturing']['facility_tax'],.25)
        for n in [True,-1,0]:
            with self.assertRaises(PlanningError):validated_settings({'manufacturing':{'system_id':n}},settings)
    def test_expired_server_cache_is_not_repeated_in_a_tight_loop(self):
        self.http.request.side_effect=[(systems(),{'Cache-Control':'max-age=0'}),(prices(),{'Cache-Control':'max-age=0'})]
        self.service.refresh();self.service.start();self.assertFalse(self.service.running);self.assertEqual(self.http.request.call_count,2)

import test_server as base
class IndustryCostApiTests(unittest.TestCase):
    setUp=base.ServerTests.setUp
    close=base.ServerTests.close
    request=base.ServerTests.request
    def test_endpoints_csrf_selection_and_unknown_system(self):
        self.assertEqual(self.request('/economics.js')[0],200)
        self.assertEqual(self.request('/api/industry')[0],200)
        self.assertEqual(self.request('/api/industry/refresh',{},**{'X-CSRF-Token':'wrong'})[0],403)
        self.assertEqual(self.request('/api/industry/estimate',{'rows':[]})[1]['cents'],'0')
        self.assertEqual(self.request('/api/industry/system?id=1')[0],400)
        self.assertEqual(self.request('/api/settings',{'manufacturing':{'system_id':1}})[0],400)
        self.assertEqual(self.request('/api/settings',{'manufacturing':{'system_id':30000142,'facility_tax':.25}})[0],200)
        self.assertEqual(self.request('/api/state')[1]['industry_facilities']['manufacturing']['system_name'],'Jita')
        self.assertEqual(self.request('/api/industry/estimate',{'rows':[{'id':92822,'batches':[{'runs':1,'count':1}]}]})[1]['missing'],1)
