import tempfile,time,unittest,sqlite3,shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from muhely.catalog import Catalog
from muhely.esi import EsiError,MARKET_SCOPES
from muhely.market import Market,STATION
from muhely.planner import PlanningError
from muhely.store import Store
from muhely.trade import Trade,StructureMarket,rate,ACCOUNTING,BROKER_RELATIONS

LOC={'id':1040000000001,'name':'C-N4OD - Fountain of Life','system_id':30004600,'system_name':'C-N4OD','region_id':10000058,'kind':'structure','owner_id':123,'faction_id':None}
def order(tid,price,buy=False,lid=LOC['id']):return {'type_id':tid,'price':price,'is_buy_order':buy,'location_id':lid,'volume_remain':10}

class TradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.catalog=Catalog(Path(__file__).resolve().parents[1]/'data/catalog.sqlite3')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name);self.store.add_character(11,'Seller');self.now=1000
        self.eve=Mock();self.eve.http=Mock(blocked_until=0);self.eve.granted_scopes.return_value={11:MARKET_SCOPES}
        self.trade=Trade(self.store,self.catalog,self.eve,lambda:self.now)
    def settings(self,fee=None):
        self.store.save_universe_cache('trade-location:11',LOC['id'],LOC,self.now)
        return self.trade.save({'system_id':30004600,'reader_id':11,'location_id':LOC['id'],'search':LOC['name'],'structure_broker_fee':fee})
    def skills(self,a=5,b=5):
        skills={'data':{'total_sp':100,'skills':[{'skill_id':sid,'active_skill_level':level,'trained_skill_level':level,'skillpoints_in_skill':50} for sid,level in [(ACCOUNTING,a),(BROKER_RELATIONS,b)]]},'fetched':time.time(),'expires':time.time()+300}
        self.store.save_snapshots(11,{'skills':skills,'skillqueue':{**skills,'data':[]}},domain='skills')
    def test_npc_rates_use_raw_standings_and_accounting(self):
        self.assertEqual(rate(5,5,8,10),{'sales_tax':'3.375','broker_fee':'1.04'})
        self.assertEqual(rate(0,0,-10,-10),{'sales_tax':'7.500','broker_fee':'3.50'})
        with self.assertRaises(PlanningError):rate(6,0)
    def test_local_configuration_is_validated_before_mutation(self):
        self.settings('2.5');old=self.trade.settings()
        for data in [{'system_id':30000142,'reader_id':11,'location_id':LOC['id']},{'system_id':30004600,'reader_id':12},{'system_id':30004600,'reader_id':11,'structure_broker_fee':'-0.1'}]:
            with self.assertRaises(PlanningError):self.trade.save(data)
            self.assertEqual(old,self.trade.settings())
    def test_hauling_rate_persists_without_requiring_a_market_and_preserves_hub(self):
        self.assertEqual(self.trade.settings()['hauling_isk_per_m3'],'0')
        self.trade.save_hauling({'hauling_isk_per_m3':'125.4321'})
        self.assertEqual(Trade(self.store,self.catalog,self.eve).settings()['hauling_isk_per_m3'],'125.4321')
        self.settings('0');self.assertEqual(self.trade.settings()['hauling_isk_per_m3'],'125.4321')
        old=self.trade.settings()
        for value in ['-1','NaN','Infinity','0.00001',True,'1000000000001']:
            with self.assertRaises(PlanningError):self.trade.save_hauling({'hauling_isk_per_m3':value})
            self.assertEqual(self.trade.settings(),old)
        self.trade.save_hauling({'hauling_isk_per_m3':'1.230000'})
        self.assertEqual(self.trade.settings()['hauling_isk_per_m3'],'1.2300')
        self.trade.save_hauling({'hauling_isk_per_m3':'0'})
        self.assertEqual(self.trade.settings()['location'],LOC)

    def test_four_hauling_rates_are_independent_and_bad_updates_are_atomic(self):
        self.settings('0')
        rates={'jita':{'import':'100.12','export':'200'},'local':{'import':'0','export':'350.4321'}}
        self.trade.save_hauling({'hauling_rates':rates})
        saved=self.trade.settings()
        self.assertEqual(saved['hauling_rates'],{'jita':{'import':'100.1200','export':'200.0000'},'local':{'import':'0.0000','export':'350.4321'}})
        self.assertEqual(Trade(self.store,self.catalog,self.eve).settings(),saved)
        for bad in [None,{}, {'jita':{'import':'1','export':'2'},'local':{'import':'3','export':'NaN'}}]:
            with self.assertRaises(PlanningError):self.trade.save_hauling({'hauling_rates':bad})
            self.assertEqual(self.trade.settings(),saved)
        self.trade.save_hauling({'hauling_isk_per_m3':'25'})
        updated=self.trade.settings()
        self.assertEqual(updated['hauling_rates']['jita'],{'import':'25.0000','export':'200.0000'})
        self.assertEqual(updated['hauling_rates']['local'],{'import':'25.0000','export':'350.4321'})
        self.assertEqual(updated['location'],LOC)

    def test_single_rate_profile_migrates_to_both_imports_with_zero_exports(self):
        with self.store.db() as db:db.execute('INSERT INTO trade_settings VALUES(1,?)',('{"hauling_isk_per_m3":"150"}',))
        rates=self.trade.settings()['hauling_rates']
        self.assertEqual(rates,{'jita':{'import':'150','export':'0'},'local':{'import':'150','export':'0'}})
        rates['local']['import']='99'
        self.assertEqual(self.trade.settings()['hauling_rates']['local']['import'],'150')

    def test_old_downloaded_catalogue_gets_matching_packaged_volumes_without_mutation(self):
        old=Path(self.tmp.name)/'old.sqlite3';shutil.copy2(self.catalog.path,old)
        with sqlite3.connect(old) as db:
            db.execute('ALTER TABLE types DROP COLUMN volume');db.execute('ALTER TABLE types DROP COLUMN packaged_volume')
        before=old.read_bytes();catalog=Catalog(old,self.catalog.path)
        self.assertEqual(catalog.types[643]['packaged_volume'],50000)
        self.assertEqual(catalog.types[643]['volume'],470000)
        self.assertEqual(catalog.types[34]['volume'],.01)
        self.assertEqual(before,old.read_bytes())

    def test_unconfigured_local_quotes_never_fall_back_to_jita(self):
        self.store.save_market_quote(34,{'buy':'1','sell':'2','id':34,'checked':1000,'expires':2000})
        data=self.trade.prices([34],True)
        self.assertEqual(data['quotes'],{});self.assertIn('34',data['errors'])
    def test_public_and_private_location_cache_keys_are_isolated(self):
        self.eve.http.request.return_value=([order(34,20,lid=60000001)],{})
        local=Market(self.store,self.eve.http,lambda:self.now,10000058,60000001,'local-A')
        local.quote(34)
        self.assertIsNone(self.store.market_quote(34));self.assertEqual(local.cached(34)['sell'],'20')
        self.assertEqual(Market(self.store,self.eve.http,lambda:self.now,10000058,60000001,'local-B').snapshot([34])['quotes'],{})
    def test_structure_pages_are_aggregated_once_for_multiple_types(self):
        market=StructureMarket(self.store,self.eve,LOC,11,lambda:self.now)
        self.eve.http.request.side_effect=[([order(34,12,True),order(34,20),order(35,30),order(34,1,lid=STATION)],{'X-Pages':'2','ETag':'one'}),([order(34,15,True),order(34,18)],{'X-Pages':'2','ETag':'two'})]
        q=market.quote(34);self.assertEqual((q['buy'],q['sell']),('15','18'))
        self.assertEqual(market.quote(35)['sell'],'30');self.assertEqual(self.eve.http.request.call_count,2)
        self.eve.token.assert_called_once_with(11,required_scopes=[MARKET_SCOPES[0]])
        self.assertIsNone(self.store.market_quote(34))
    def test_structure_304_and_failed_partial_page_keep_last_complete_prices(self):
        market=StructureMarket(self.store,self.eve,LOC,11,lambda:self.now)
        self.eve.http.request.side_effect=[([order(34,20)],{'X-Pages':'2','ETag':'one'}),([order(34,18)],{'X-Pages':'2','ETag':'two'})]
        market.quote(34);self.now=1901
        self.eve.http.request.side_effect=[(None,{'X-Pages':'2'}),(None,{'X-Pages':'2'})]
        self.assertEqual(market.quote(34)['sell'],'18');self.assertEqual(self.eve.http.request.call_args.kwargs['headers'],{'If-None-Match':'two'})
        old=market.cached(34);self.now=2802
        self.eve.http.request.side_effect=[([order(34,9)],{'X-Pages':'2'}),EsiError('offline')]
        with self.assertRaises(EsiError):market.quote(34)
        self.assertEqual(market.cached(34),old)
    def test_manual_refresh_honors_esi_cache_and_does_not_replace_unknown_side(self):
        market=StructureMarket(self.store,self.eve,LOC,11,lambda:self.now)
        self.eve.http.request.return_value=([order(34,20)],{'Cache-Control':'max-age=300'})
        self.assertIsNone(market.quote(34)['buy']);self.now=1100;market.quote(34,True)
        self.assertEqual(self.eve.http.request.call_count,1)
        self.now=1301;market.quote(34);self.assertEqual(self.eve.http.request.call_count,1)
        market.quote(34,True);self.assertEqual(self.eve.http.request.call_count,2)
    def test_profile_uses_seller_and_npc_owner_standings(self):
        self.skills();loc={**LOC,'id':STATION,'kind':'npc','owner_id':1000035,'faction_id':500001}
        self.store.save_universe_cache('trade-location:11',STATION,loc,1000)
        self.store.save_universe_cache('trade-standings',11,{'rows':[{'from_type':'npc_corp','from_id':1000035,'standing':8},{'from_type':'faction','from_id':500001,'standing':10},{'from_type':'npc_corp','from_id':5,'standing':-10}],'expires':2000},1000)
        result=self.trade.profile(11,'jita');self.assertEqual(result['broker_fee'],'1.04');self.assertEqual(result['sales_tax'],'3.375')
        self.assertEqual((result['corp_standing'],result['faction_standing']),(8,10))
    def test_structure_broker_fee_does_not_receive_npc_skill_reductions(self):
        self.settings('2.5');self.skills(4,5)
        result=self.trade.profile(11,'local');self.assertEqual(result['broker_fee'],'2.5');self.assertEqual(result['sales_tax'],'4.200')
        self.assertIsNone(result['corp_standing'])
    def test_explicit_zero_structure_broker_fee_is_persisted_without_removing_sales_tax(self):
        self.settings('0');self.skills()
        trade=Trade(self.store,self.catalog,self.eve,lambda:self.now)
        self.assertEqual(trade.settings()['structure_broker_fee'],'0')
        result=trade.profile(11,'local')
        self.assertEqual(result['broker_fee'],'0');self.assertEqual(result['sales_tax'],'3.375')
    def test_missing_seller_skills_or_structure_fee_stay_unknown(self):
        self.settings();result=self.trade.profile(11,'local')
        self.assertIsNone(result['sales_tax']);self.assertIsNone(result['broker_fee']);self.assertTrue(result['warnings'])
    def test_plan_settings_are_separate_and_invalid_updates_are_atomic(self):
        for pid in ['a','b']:self.store.save_plan({'id':pid,'name':pid,'product_id':590,'quantity':1,'created':1000,'reserve_active':False,'reserved_at':None})
        self.trade.save_finance({'plan_id':'a','materials':'local:sell','sale':'jita:buy','seller_id':11,'blueprints_isk':'100','other_isk':'20'})
        self.assertEqual(self.trade.finance('b')['materials'],'jita:sell');self.assertIsNone(self.trade.finance()['seller_id'])
        self.assertEqual(Trade(self.store,self.catalog,self.eve).finance('a')['other_isk'],'20')
        for patch in [{'materials':'bad'},{'seller_id':99},{'other_isk':'NaN'},{'blueprints_isk':-1}]:
            with self.assertRaises(PlanningError):self.trade.save_finance({'plan_id':'a',**patch})
        self.assertEqual(self.trade.finance('a')['materials'],'local:sell')
    def test_hauling_switch_is_plan_specific_persists_and_defaults_on_for_existing_plans(self):
        for pid in ['a','b']:self.store.save_plan({'id':pid,'name':pid,'product_id':590,'quantity':1,'created':1000,'reserve_active':False,'reserved_at':None})
        with self.store.db() as db:db.execute('INSERT INTO trade_plans VALUES(?,?)',('plan:a','{"materials":"jita:buy"}'))
        self.assertTrue(self.trade.finance('a')['hauling_enabled']);self.assertTrue(self.trade.finance('b')['hauling_enabled'])
        self.trade.save_hauling({'hauling_rates':{'jita':{'import':'500','export':'650'},'local':{'import':'100','export':'200'}}});rates=self.trade.settings()['hauling_rates']
        self.trade.save_finance({'plan_id':'a','hauling_enabled':False})
        again=Trade(self.store,self.catalog,self.eve)
        self.assertFalse(again.finance('a')['hauling_enabled']);self.assertTrue(again.finance('b')['hauling_enabled']);self.assertTrue(again.finance()['hauling_enabled'])
        self.trade.save_finance({'plan_id':'a','other_isk':'50'});self.assertFalse(self.trade.finance('a')['hauling_enabled'])
        for value in ['false',0,1,None,{}]:
            with self.assertRaises(PlanningError):self.trade.save_finance({'plan_id':'a','hauling_enabled':value})
            self.assertFalse(self.trade.finance('a')['hauling_enabled'])
        self.trade.save_finance({'plan_id':'a','hauling_enabled':True});self.assertEqual(self.trade.settings()['hauling_rates'],rates)

    def test_discovery_checks_system_and_does_not_auto_select_an_unregistered_hub(self):
        self.trade.public=Mock(return_value={'stations':[]})
        self.trade.location=Mock(side_effect=lambda lid,*args:LOC if lid==LOC['id'] else {**LOC,'id':lid,'system_id':30000142})
        self.eve.http.request.return_value=({'structure':[LOC['id'],1040000000002]}, {})
        self.trade.discover({'system_id':30004600,'reader_id':11,'search':'Fountain of Life'})
        for _ in range(100):
            if not self.trade.state['running']:break
            time.sleep(.01)
        self.assertIsNone(self.trade.state['error']);self.assertEqual(self.trade.state['candidates'],[LOC]);self.assertIsNone(self.trade.settings()['location_id'])

    def test_import_export_switches_migrate_and_persist_independently_without_changing_rates(self):
        for pid in ['a','b']:self.store.save_plan({'id':pid,'name':pid,'product_id':590,'quantity':1,'created':1000,'reserve_active':False,'reserved_at':None})
        with self.store.db() as db:db.execute('INSERT INTO trade_plans VALUES(?,?)',('plan:a','{"hauling_enabled":false}'))
        self.assertFalse(self.trade.finance('a')['hauling_import_enabled']);self.assertFalse(self.trade.finance('a')['hauling_export_enabled'])
        rates=self.trade.settings()['hauling_rates']
        self.trade.save_finance({'plan_id':'a','hauling_import_enabled':True})
        again=Trade(self.store,self.catalog,self.eve);self.assertTrue(again.finance('a')['hauling_import_enabled']);self.assertFalse(again.finance('a')['hauling_export_enabled'])
        self.assertTrue(again.finance('b')['hauling_export_enabled']);self.assertTrue(again.finance()['hauling_import_enabled'])
        self.trade.save_finance({'plan_id':'a','other_isk':'75'});self.assertFalse(self.trade.finance('a')['hauling_export_enabled'])
        for field in ['hauling_import_enabled','hauling_export_enabled']:
            before=self.trade.finance('a')
            for value in ['false',0,None,{}]:
                with self.assertRaises(PlanningError):self.trade.save_finance({'plan_id':'a',field:value})
                self.assertEqual(self.trade.finance('a'),before)
        self.trade.save_finance({'plan_id':'a','hauling_import_enabled':False,'hauling_export_enabled':True})
        self.assertFalse(self.trade.finance('a')['hauling_import_enabled']);self.assertTrue(self.trade.finance('a')['hauling_export_enabled'])
        self.assertEqual(self.trade.settings()['hauling_rates'],rates)

import test_server as base
class TradeApiTests(unittest.TestCase):
    setUp=base.ServerTests.setUp
    close=base.ServerTests.close
    request=base.ServerTests.request
    def test_auth_validation_and_no_public_fallback(self):
        self.assertEqual(self.request('/api/trade',Cookie='')[0],403)
        self.assertEqual(self.request('/api/trade')[0],200)
        self.assertEqual(self.request('/api/trade/plan',{'materials':'local:buy'},Origin='https://other.invalid')[0],403)
        self.assertEqual(self.request('/api/trade/plan',{'materials':'local:buy'})[0],200)
        self.assertEqual(self.request('/api/trade/plan')[1]['materials'],'local:buy')
        self.assertEqual(self.request('/api/prices?ids=34&source=bad')[0],400)
        data=self.request('/api/prices?ids=34&source=local')[1];self.assertEqual(data['quotes'],{});self.assertIn('34',data['errors'])
        self.assertEqual(self.request('/api/trade/hauling',{'hauling_isk_per_m3':'123.45'},Origin='https://other.invalid')[0],403)
        self.assertEqual(self.request('/api/trade/hauling',{'hauling_isk_per_m3':'123.45'})[0],200)
        self.assertEqual(self.request('/api/trade')[1]['settings']['hauling_isk_per_m3'],'123.4500')
        self.assertEqual(self.request('/trade.js')[0],200)
