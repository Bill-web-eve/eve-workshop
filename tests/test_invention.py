from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
import tempfile,time,unittest,copy
from unittest.mock import Mock,patch
from muhely import invention as inv
from muhely.catalog import Catalog
from muhely.store import Store
from muhely.trade import Trade
from muhely.industry_costs import IndustryCosts,normalize
from muhely.planner import PlanningError

ROOT=Path(__file__).resolve().parents[1]
class InventionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name);self.catalog=Catalog(ROOT/'data/catalog.sqlite3');self.now=time.time();self.sid=next(iter(self.catalog.moon_systems));self.product=11985
  self.store.add_character(1,'Inventor');self.recipe=self.catalog.inventions[self.product]
  skills={'skills':[{'skill_id':s['typeID'],'active_skill_level':5,'trained_skill_level':5,'skillpoints_in_skill':1000} for s in self.recipe['skills']],'total_sp':3000}
  self.store.save_snapshots(1,{'skills':{'data':skills,'fetched':self.now,'expires':self.now+600}})
  settings=self.store.settings()
  for a in ['manufacturing','reaction']:settings[a]['system_id']=self.sid
  self.store.save_settings(settings);self.industry=IndustryCosts(self.store);self.config=inv.defaults(self.store,self.catalog,self.product);self.config['inventor_id']=1
  self.store.save_universe_cache('industry-prices',0,{'values':{str(m['typeID']):'100' for r in self.catalog.recipes.values() for m in r['materials']},'expires':self.now+600},self.now)
  self.store.save_universe_cache('industry-systems',0,{'values':{str(self.sid):{'manufacturing':'.01','reaction':'.02','copying':'.03','invention':'.04'}},'expires':self.now+600},self.now)
 def quotes(self,source,ids):return {'quotes':{str(i):{'buy':'1000','sell':'2000'} for i in ids}}
 def compare(self,quantity=10,quotes=None):return inv.compare(self.store,self.catalog,self.industry,self.config,quantity,quotes or self.quotes,'jita:sell')
 def test_official_same_build_data_and_all_current_decryptors(self):
  self.assertEqual(len(self.catalog.decryptors),8);self.assertGreater(len(self.catalog.inventions),100)
  self.assertEqual(self.recipe['base_blueprint_id'],686);self.assertEqual(self.recipe['base_probability'],.26)
  self.assertEqual(self.catalog.decryptors[34205]['me'],3);self.assertEqual(self.catalog.decryptors[34202]['probability_multiplier'],1.8)
 def test_expected_successes_exact_and_active_skills(self):
  recipe={'base_probability':'.26','skills':[{'typeID':10},{'typeID':11},{'typeID':21790}]}
  p=inv.chance(recipe,{10:3,11:3,21790:2},2);self.assertEqual(p,Decimal('.65'));self.assertEqual(p*100,Decimal(65))
  result=self.compare();row=result['rows'][0];p=Decimal(row['probability']);self.assertEqual(p,Decimal('.26')*(1+Decimal(10)/30+Decimal(5)/40))
  self.assertEqual(Decimal(row['expected_successes']),p*100);self.assertEqual(row['me'],2);self.assertEqual(row['te'],4)
  self.assertEqual(len(result['rows']),9);self.assertTrue(result['skills_ready'])
 def test_copy_and_invention_eiv_and_failure_cost_are_amortized_per_successful_run(self):
  result=self.compare();row=result['rows'][0];runs=self.config['copy_runs']
  copy_fee=Decimal(result['copying']['cents'])/100/runs;job_fee=Decimal(result['invention']['cents'])/100
  cost=Decimal(row['materials_cents'])/100+copy_fee+job_fee
  self.assertEqual(Decimal(row['per_run_isk']),cost/Decimal(row['probability']))
  self.assertEqual(row['bpc_total_cents'],inv.cents(Decimal(row['per_item_isk'])*10))
  other=self.compare(20)['rows'][0];self.assertEqual(other['bpc_total_cents'],inv.cents(Decimal(row['per_item_isk'])*20))
  # Copy EIV uses T1 manufacturing inputs, invention EIV uses T2 output inputs.
  self.assertNotEqual(result['copying']['eiv_per_run'],result['invention']['eiv_per_run'])
 def test_more_expensive_decryptor_can_win_by_me_across_the_full_chain(self):
  core_ids={m['typeID'] for m in self.recipe['materials']};decr=set(self.catalog.decryptors)
  def quotes(source,ids):return {'quotes':{str(i):{'buy':str(100 if i in core_ids else 1000000 if i==34205 else 1 if i in decr else 1000000),'sell':str(100 if i in core_ids else 1000000 if i==34205 else 1 if i in decr else 1000000)} for i in ids}}
  result=self.compare(100,quotes);process=next(r for r in result['rows'] if r['decryptor_id']==34205);symmetry=next(r for r in result['rows'] if r['decryptor_id']==34206)
  self.assertGreater(int(process['per_run_cents']),int(symmetry['per_run_cents']));self.assertLess(int(process['total_cents']),int(symmetry['total_cents']));self.assertEqual(result['best_decryptor_id'],34205)
 def test_unknown_prices_indices_or_skills_never_become_zero_or_a_best_choice(self):
  result=self.compare(quotes=lambda s,ids:{'quotes':{}});self.assertIsNone(result['best_decryptor_id']);self.assertTrue(all(r['total_cents'] is None for r in result['rows']))
  self.config['invention']['system_id']=None;self.assertFalse(self.compare()['invention']['complete'])
  self.config['inventor_id']=None;result=self.compare();self.assertFalse(result['skills_ready']);self.assertIsNone(result['selected']['per_run_cents'])
 def test_separate_price_source_plan_persistence_validation_and_no_reservation_mutation(self):
  trade=Trade(self.store,self.catalog,Mock());self.store.save_plan({'id':'a','name':'a','product_id':self.product,'quantity':10,'created':1,'reserve_active':False,'reserved_at':None})
  before=self.store.plans();conf=copy.deepcopy(self.config);conf.update(enabled=True,prices='local:buy',decryptor_id=34207)
  trade.save_finance({'plan_id':'a','invention':conf});self.assertEqual(trade.finance('a')['invention'],conf);self.assertIsNone(trade.finance()['invention'])
  calls=[]
  def quotes(source,ids):calls.append(source);return self.quotes(source,ids)
  inv.compare(self.store,self.catalog,self.industry,conf,10,quotes,'jita:sell');self.assertEqual(set(calls),{'jita','local'});self.assertEqual(self.store.plans(),before)
  for patch in [{'enabled':'yes'},{'decryptor_id':999},{'inventor_id':999},{'copy_runs':0},{'attempts':True}]:
   with self.assertRaises(PlanningError):trade.save_finance({'plan_id':'a','invention':{**conf,**patch}})
   self.assertEqual(trade.finance('a')['invention'],conf)
 def test_missing_datacore_is_named_and_only_absent_prices_are_requested(self):
  missing_id=self.recipe['materials'][-1]['typeID']
  def partial(source,ids):
   book=self.quotes(source,ids);book['quotes'].pop(str(missing_id),None);return book
  result=self.compare(quotes=partial)
  self.assertEqual(result['price_requests'],{'jita':[missing_id]})
  self.assertIsNone(result['best_decryptor_id'])
  self.assertEqual(result['selected']['missing_details'],[{'id':missing_id,'name':self.catalog.name(missing_id),'source':'jita','mode':'sell','reason':'not_loaded'}])
  complete=self.compare();self.assertEqual(complete['price_requests'],{});self.assertIsNotNone(complete['best_decryptor_id'])
 def test_a_loaded_quote_without_a_buy_price_is_not_continually_refetched(self):
  self.config['prices']='jita:buy';missing_id=self.recipe['materials'][-1]['typeID']
  def partial(source,ids):
   book=self.quotes(source,ids);book['quotes'][str(missing_id)]['buy']=None;return book
  result=self.compare(quotes=partial)
  self.assertEqual(result['price_requests'],{})
  self.assertEqual(result['selected']['missing_details'][0]['reason'],'unavailable_buy')
  self.assertIsNone(result['selected']['per_run_cents'])
 def test_normalization_retains_copy_and_invention_indices(self):
  data=normalize('systems',[{'solar_system_id':1,'cost_indices':[{'activity':'copying','cost_index':.01},{'activity':'invention','cost_index':.02}]}])
  self.assertEqual(data['1'],{'copying':'0.01','invention':'0.02'})

class InventionApiTests(unittest.TestCase):
 import test_server as base
 setUp=base.ServerTests.setUp;close=base.ServerTests.close;request=base.ServerTests.request
 def test_api_auth_no_false_costs_and_saved_profile_product_boundary(self):
  self.assertEqual(self.request('/api/invention/options?product_id=11985',Cookie='')[0],403)
  status,data,_=self.request('/api/invention/options?product_id=11985');self.assertEqual(status,200);self.assertEqual(len(data['decryptors']),8)
  body={'config':data['config'],'quantity':10,'corporation_id':None,'manufacturing_prices':'jita:sell'}
  self.assertEqual(self.request('/api/invention/estimate',body,Origin='https://outside.invalid')[0],403)
  status,result,_=self.request('/api/invention/estimate',body);self.assertEqual(status,200);self.assertEqual(len(result['rows']),9);self.assertFalse(result['skills_ready']);self.assertIsNone(result['best_decryptor_id'])
  self.assertEqual(self.request('/api/trade/plan',{'invention':data['config']})[0],200)
  self.assertEqual(self.request('/api/invention/options?product_id=1')[0],400)
  self.assertEqual(self.request('/invention.js')[0],200)
  self.assertNotIn('access_token',str(result));self.assertNotIn('refresh_token',str(result))

if __name__=='__main__':unittest.main()
