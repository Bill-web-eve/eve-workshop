import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest

from muhely.catalog import Catalog
from muhely.planner import Planner, PlanningError, material_for_batch, live_inventory, integer
from muhely.store import DEFAULT_SETTINGS

ROOT = Path(__file__).resolve().parents[1]


class FakeCatalog:
    def __init__(self):
        self.types = {n: {'name': str(n), 'pi': 0, 'group_id': 0} for n in [100,110,120,130,200]}
        self.recipes = {}
        self.meta = {}
    def name(self, n):return self.types.get(n, {}).get('name', str(n))
    def recipe(self, n, materials, output=1, activity='manufacturing', copy_limit=100):
        self.recipes[n] = {'bp_id': n+1000, 'activity': activity, 'output': output,
                           'seconds': 100, 'copy_limit': copy_limit,
                           'materials': [{'typeID': key, 'quantity': value} for key, value in materials.items()]}


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.catalog = FakeCatalog()
        self.catalog.recipe(100, {110:2,120:3})
        self.catalog.recipe(110, {130:5})
        self.catalog.recipe(120, {130:7})
        self.catalog.recipe(130, {200:2}, activity='reaction')
        self.p = Planner(self.catalog)
        self.settings = copy.deepcopy(DEFAULT_SETTINGS)
        for activity in ['manufacturing', 'reaction']:
            self.settings[activity].update(material_role=0,material_rig=0,time_role=0,time_rig=0)

    def plan(self, **kw):return self.p.calculate(100, 1, self.settings, **kw)
    def rows(self, result):return {r['id']:r for r in result['rows']}

    def test_shared_stock_is_deducted_once_after_all_parent_demand(self):
        r=self.rows(self.plan(stock={130:10}))
        self.assertEqual(r[130]['required'],31)
        self.assertEqual(r[130]['runs'],21)
        self.assertEqual(r[200]['buy'],42)

    def test_finished_component_does_not_recreate_its_materials(self):
        r=self.rows(self.plan(stock={110:2,130:10}))
        self.assertEqual(r[110]['runs'],0)
        self.assertEqual(r[130]['required'],21)
        self.assertEqual(r[200]['buy'],22)

    def test_in_progress_component_has_the_same_netting_rule(self):
        result=self.plan(wip={110:2},stock={130:10})
        self.assertNotIn(110,[r['id'] for r in result['queue']])
        self.assertEqual(self.rows(result)[200]['buy'],22)

    def test_finished_or_in_progress_root_has_no_remaining_work(self):
        for kw in [{'stock':{100:1}},{'wip':{100:1}}]:
            with self.subTest(kw=kw):
                result=self.plan(**kw)
                self.assertEqual(result['queue'],[])
                self.assertEqual(result['shopping'],[])

    def test_zero_override_replaces_real_stock_and_wip(self):
        result=self.plan(stock={110:2},wip={120:3},inventory={110:{'quantity':0},120:{'wip':0}})
        self.assertEqual(self.rows(result)[200]['buy'],62)

    def test_reserved_stock_is_not_available(self):
        result=self.plan(stock={110:2},inventory={110:{'reserved':2}})
        self.assertEqual(self.rows(result)[110]['runs'],2)

    def test_queue_is_topologically_ordered_and_reacts_to_stock(self):
        result=self.plan()
        index={r['id']:i for i,r in enumerate(result['queue'])}
        for r in result['queue']:
            for material in r['materials']:
                if material['id'] in index:
                    self.assertLess(index[material['id']],index[r['id']])
        self.assertEqual(result['queue'][0]['activity'],'reaction')

    def test_buy_override_cuts_the_subtree(self):
        result=self.plan(parameters={130:{'mode':'buy'}})
        self.assertNotIn(200,self.rows(result))
        self.assertEqual(self.rows(result)[130]['buy'],31)
        self.assertEqual(self.rows(result)[130]['category'],'Vételre állított köztes')

    def test_multi_output_uses_ceiling_runs_and_keeps_surplus(self):
        self.catalog.recipe(110,{130:5},output=3)
        row=self.rows(self.plan())[110]
        self.assertEqual((row['missing'],row['runs'],row['manufactured'],row['surplus']),(2,1,3,1))

    def test_bpc_boundary_splits_jobs_before_material_rounding(self):
        self.catalog.recipe(100,{200:2})
        bp=lambda item:dict(item_id=item,type_id=1100,quantity=-2,runs=3,material_efficiency=10,time_efficiency=20)
        result=self.p.calculate(100,6,self.settings,blueprints=[bp(1),bp(2)],parameters={100:{'job_runs':5}})
        row=self.rows(result)[100]
        self.assertEqual(row['batches'],[{'runs':3,'count':2}])
        self.assertEqual(row['jobs'],2)
        self.assertEqual(self.rows(result)[200]['buy'],12)

    def test_manual_run_capacity_is_reported(self):
        result=self.plan(parameters={110:{'source':'manual','total_runs':1}})
        self.assertTrue(any('Kevés BPC-run' in text for text in self.rows(result)[110]['warning']))

    def test_blueprint_counts_preserve_mixed_parameters_and_packaged_originals(self):
        bp=dict(item_id=1,type_id=1100,quantity=-2,runs=2,material_efficiency=3,time_efficiency=2)
        copies=[bp,dict(bp,item_id=2),dict(bp,item_id=3,material_efficiency=2,runs=7)]
        p=self.rows(self.plan(blueprints=copies))[100]['parameters']
        self.assertEqual((p['bpo_count'],p['bpc_count'],p['bpc_runs']),(0,3,11))
        self.assertEqual((p['me'],p['te'],p['available_runs'],p['group_count'],p['job_runs']),(3,2,4,2,2))
        self.assertEqual(sum(b['selected'] for b in p['instances']),2)
        self.assertEqual([b['runs'] for b in p['instances']],[2,2,7])
        packaged=dict(bp,item_id=4,quantity=5,runs=-1,material_efficiency=0,time_efficiency=0)
        p=self.rows(self.plan(blueprints=copies+[packaged]))[100]['parameters']
        self.assertEqual((p['kind'],p['bpo_count'],p['bpc_count'],p['group_count']),('BPO',5,3,5))
        self.assertIsNone(p['available_runs'])
        self.assertEqual(p['instances'][0]['count'],5)

    def test_manual_parameters_keep_owned_blueprint_details(self):
        bp=dict(item_id=1,type_id=1100,quantity=-2,runs=2,material_efficiency=3,time_efficiency=2)
        p=self.rows(self.plan(blueprints=[bp],parameters={100:{'source':'manual','me':7,'te':12,'total_runs':8}}))[100]['parameters']
        self.assertEqual((p['me'],p['te'],p['available_runs']),(7,12,8))
        self.assertEqual((p['bpc_count'],p['instances'][0]['me'],p['instances'][0]['runs']),(1,3,2))
        self.assertFalse(p['instances'][0]['selected'])

    def test_specific_blueprint_retains_total_owned_counts(self):
        bp=dict(item_id=1,type_id=1100,quantity=-2,runs=2,material_efficiency=3,time_efficiency=2)
        p=self.rows(self.plan(blueprints=[bp,dict(bp,item_id=2)],parameters={100:{'item_id':2}}))[100]['parameters']
        self.assertEqual((p['bpc_count'],p['group_count'],p['available_runs']),(2,1,2))
        self.assertEqual([b['item_id'] for b in p['instances'] if b['selected']],[2])

    def test_original_priority_and_group_isolation(self):
        self.catalog.recipe(100,{200:2})
        originals=[dict(item_id=1,type_id=1100,quantity=-1,runs=-1,material_efficiency=0,time_efficiency=0)]
        copies=[dict(item_id=2,type_id=1100,quantity=-2,runs=5,material_efficiency=10,time_efficiency=20)]
        row=self.rows(self.plan(blueprints=originals+copies))[100]
        self.assertEqual((row['parameters']['kind'],row['parameters']['me']),('BPO',0))
        row=self.rows(self.plan(blueprints=copies+[dict(copies[0],item_id=3,material_efficiency=9)]))[100]
        self.assertEqual(row['parameters']['available_runs'],5)
        self.assertTrue(row['parameters']['other_groups'])

    def test_specific_item_selection_and_busy_warning(self):
        self.catalog.recipe(100,{200:2})
        bp=dict(item_id=8,type_id=1100,quantity=-2,runs=5,material_efficiency=7,time_efficiency=12)
        row=self.rows(self.plan(blueprints=[bp],parameters={100:{'item_id':8}},jobs=[{'blueprint_id':8,'status':'active'}]))[100]
        self.assertEqual(row['parameters']['me'],7)
        self.assertTrue(row['parameters']['busy'])
        with self.assertRaises(PlanningError):self.plan(parameters={100:{'item_id':999}})

    def test_reaction_ignores_blueprint_me_te_but_uses_structure(self):
        self.settings['reaction'].update(material_rig=2.6,time_role=25,time_rig=26.4)
        row=self.rows(self.plan(parameters={130:{'source':'manual','me':10,'te':20}}))[130]
        self.assertEqual((row['parameters']['me'],row['parameters']['te']),(0,0))
        self.assertAlmostEqual(row['seconds'],31*100*.552)

    def test_minimum_one_material_per_run(self):
        self.assertEqual(material_for_batch(1,100,Decimal('.1')),100)
        self.assertEqual(material_for_batch(100,1,Decimal('.974')),98)

    def test_cycle_and_invalid_numbers_fail_visibly(self):
        self.catalog.recipe(130,{100:1})
        with self.assertRaises(PlanningError):self.plan()
        for value in [True,-1,float('nan'),float('inf'),1.2,'1']:
            with self.subTest(value=value),self.assertRaises(PlanningError):integer(value,'Test')

    def test_fuel_is_purchased_as_input_but_buildable_as_target(self):
        self.catalog.types[110]['group_id']=1136
        result=self.plan()
        self.assertEqual(self.rows(result)[110]['activity'],'buy')
        own=self.p.calculate(110,1,self.settings)
        self.assertEqual(self.rows(own)[110]['activity'],'manufacturing')


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.c=FakeCatalog();self.c.recipe(130,{200:2},output=200,activity='reaction')
    def test_jobs_use_activity_nine_and_exclude_delivered_and_research(self):
        jobs=[]
        for i,(status,activity,runs) in enumerate([('active',9,11),('paused',9,2),('ready',9,3),('delivered',9,80),('cancelled',9,20),('reverted',9,30),('active',8,100),('active',11,100)]):
            jobs.append(dict(job_id=i,product_type_id=130,blueprint_type_id=1130,blueprint_id=5,
                             status=status,activity_id=activity,runs=runs,output_location_id=900))
        snapshot=dict(character_id=1,assets=[],blueprints=[],jobs=jobs)
        _,wip,_,rows,locations=live_inventory(self.c,[snapshot,snapshot])
        self.assertEqual(wip[130],3200)
        self.assertEqual(sum(r['expected_output'] for r in rows),3200)
        self.assertFalse(live_inventory(self.c,[snapshot],[901])[1])
        self.assertEqual(live_inventory(self.c,[snapshot],[900])[1][130],3200)

    def test_nested_containers_and_duplicate_assets(self):
        assets=[dict(item_id=10,type_id=1000,location_id=900,quantity=1),
                dict(item_id=20,type_id=1001,location_id=10,quantity=1),
                dict(item_id=30,type_id=200,location_id=20,quantity=57),
                dict(item_id=40,type_id=200,location_id=901,quantity=80)]
        snap=dict(character_id=1,assets=assets,blueprints=[],jobs=[])
        stock,*_=live_inventory(self.c,[snap,snap],[900])
        self.assertEqual(stock[200],57)
        bad=dict(snap,assets=[dict(item_id=10,type_id=200,location_id=20),dict(item_id=20,type_id=200,location_id=10)])
        with self.assertRaises(PlanningError):live_inventory(self.c,[bad])


class RealCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=Catalog(ROOT/'data/catalog.sqlite3');cls.p=Planner(cls.catalog)
    def test_regression_against_both_verified_excel_baselines(self):
        for name,tid in [('salvation',92822),('redeemer',22428)]:
            expected=json.loads((ROOT/'tests/fixtures'/f'{name}_baseline.json').read_text())
            result=self.p.calculate(tid,1,DEFAULT_SETTINGS)
            actual={r['id']:r for r in result['rows']}
            for old in expected['nodes']:
                row=actual.get(old['id'])
                values=[row['required'],row['available'],row['wip'],row['missing'],row['runs'],row['manufactured'],row['buy'],row['surplus'],row['seconds']/3600] if row else [0]*9
                for column,(a,b) in enumerate(zip(values,old['values'])):
                    with self.subTest(ship=name,type_id=old['id'],column=column):self.assertAlmostEqual(a,b,places=7)
    def test_catalog_excludes_unpublished_tungsten_recipe(self):
        self.assertEqual(self.catalog.recipes[16672]['output'],10000)
        self.assertEqual(self.catalog.recipes[16672]['bp_id'],46207)
        self.assertEqual(self.catalog.meta['duplicateRecipes'],'0')
    def test_general_product_search_and_extra_products(self):
        for query in ['Salvation','Redeemer','Hulk','Tritanium','Tungsten Carbide','Nanite Repair Paste']:
            results=self.catalog.search(query,all_types=query=='Tritanium')
            with self.subTest(query=query):self.assertTrue(results)
        for query in ['Hulk','Nanite Repair Paste','Helium Fuel Block']:
            tid=self.catalog.search(query)[0]['id']
            self.assertTrue(self.p.calculate(tid,1,DEFAULT_SETTINGS)['queue'])
    def test_real_stock_and_jobs_remove_component_materials(self):
        before=self.p.calculate(22428,1,DEFAULT_SETTINGS)
        after=self.p.calculate(22428,1,DEFAULT_SETTINGS,stock={643:1},wip={11532:1000})
        rows={r['id']:r for r in after['rows']}
        self.assertEqual(rows[643]['runs'],0)
        self.assertEqual(rows[11532]['runs'],0)
        self.assertLess(sum(r['buy'] for r in after['shopping']),sum(r['buy'] for r in before['shopping']))


if __name__=='__main__':unittest.main()
