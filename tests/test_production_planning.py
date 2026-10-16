import copy
import tempfile
import time
import unittest
import sqlite3
import shutil
from pathlib import Path

from muhely.catalog import Catalog
from muhely.planner import Planner,PlanningError
from muhely.production import duration_skills,profiles
from muhely.reservations import allocate_plans,except_owner
from muhely.server import App,ROOT
from muhely.store import DEFAULT_SETTINGS,Store
from test_planner import FakeCatalog


def bp(item=1,runs=2,me=0,te=0,original=False):
    return dict(item_id=item,type_id=1100,quantity=-1 if original else -2,runs=-1 if original else runs,
                material_efficiency=me,time_efficiency=te)


class ProductionPlanningTests(unittest.TestCase):
    def setUp(self):
        self.c=FakeCatalog();self.c.recipe(100,{200:2});self.c.recipe(130,{200:2},activity='reaction')
        self.c.recipes[100]['skills']=[];self.c.recipes[130]['skills']=[];self.c.skill_time_bonuses={11452:-1}
        self.p=Planner(self.c);self.settings=copy.deepcopy(DEFAULT_SETTINGS)
        for activity in ['manufacturing','reaction']:
            self.settings[activity].update(material_role=0,material_rig=0,time_role=0,time_rig=0)
    def plan(self,q=5,**kw):return self.p.calculate(100,q,self.settings,**kw)
    def shortage(self,plan):return next((r for r in plan['shopping'] if r['id']==1100),None)
    def character(self,cid=1,industry=5,advanced=5,reactions=5,science=5):
        return {'id':cid,'name':f'Pilot {cid}','available':True,'levels':{3380:industry,3388:advanced,45746:reactions,11452:science},'as_of':time.time(),'stale':False}

    def test_reaction_limit_100_million_and_manufacturing_limit(self):
        result=self.p.calculate(130,100_000_000,self.settings)
        self.assertEqual(result['quantity'],100_000_000)
        self.assertLess(len(result['queue'][0]['batches']),3)
        for product,q in [(130,100_000_001),(100,1_000_001)]:
            with self.assertRaises(PlanningError):self.p.calculate(product,q,self.settings)

    def test_missing_copy_runs_are_procurement_not_physical_output(self):
        result=self.plan(blueprints=[bp()]);s=self.shortage(result)
        self.assertEqual((s['required'],s['used_stock'],s['buy'],s['unit']),(5,2,3,'run'))
        self.assertNotIn(1100,[r['id'] for r in result['rows']])
        self.assertEqual(result['blueprint_usage'][0]['runs'],2)

    def test_bpo_or_sufficient_bpcs_have_no_blueprint_shortage(self):
        for bps in [[bp(original=True)],[bp(runs=5)],[bp(runs=2),bp(2,runs=3)]]:
            self.assertIsNone(self.shortage(self.plan(blueprints=bps)))
        original=self.plan(blueprints=[bp(original=True)],parameters={100:{'source':'manual','total_runs':1}})
        self.assertFalse(original['blueprint_usage'])
        self.assertIsNone(self.shortage(original))

    def test_finished_and_wip_outputs_do_not_need_bpc_again(self):
        self.assertFalse(self.plan(stock={100:5})['blueprint_shortages'])
        self.assertFalse(self.plan(wip={100:5})['blueprint_shortages'])
        self.assertIsNone(self.shortage(self.plan(wip={100:3},blueprints=[bp(runs=2)])))

    def test_multi_output_counts_runs_not_units_and_manual_run_capacity(self):
        self.c.recipes[100]['output']=3
        self.assertEqual(self.shortage(self.plan(blueprints=[bp(runs=1)]))['buy'],1)
        self.assertEqual(self.shortage(self.plan(parameters={100:{'total_runs':1}}))['buy'],1)

    def test_other_me_groups_are_not_misrepresented_as_same_blueprint(self):
        s=self.shortage(self.plan(blueprints=[bp(runs=2,me=10),bp(2,runs=20,me=0)]))
        self.assertEqual(s['buy'],3)

    def test_reaction_formula_is_one_reusable_noncopyable_item(self):
        result=self.p.calculate(130,50,self.settings)
        s=next(r for r in result['shopping'] if r['id']==1130)
        self.assertEqual((s['buy'],s['unit'],s['category']),(1,'db','Reakcióformula'))

    def test_bpc_runs_are_reserved_once_and_owner_can_reuse_own_runs(self):
        calc=lambda product,q,held:self.p.calculate(product,q,self.settings,blueprints=[bp(runs=4)],reservations=held)
        plans=[dict(id=i,name=i,product_id=100,quantity=3,reserve_active=True,created=n,reserved_at=n) for n,i in enumerate(['A','B'],1)]
        allocation=allocate_plans(plans,calc)
        self.assertEqual(allocation['totals'][1100]['blueprint_runs'],{1:4})
        self.assertEqual(next(r for r in allocation['by_plan']['B']['shopping'] if r['id']==1100)['buy'],2)
        held,own=except_owner(allocation,'A')
        self.assertIsNone(self.shortage(calc(100,3,held)))
        held,own=except_owner(allocation,None)
        self.assertEqual(self.shortage(calc(100,3,held))['buy'],3)

    def test_industry_advanced_and_required_science_are_multiplicative(self):
        self.c.recipes[100]['skills']=[{'typeID':11452,'level':1}]
        self.settings['manufacturing']['skill_time']=.25
        row=self.plan(1,skill_profiles=[self.character()],manufacturer_id=1)['queue'][0]
        self.assertAlmostEqual(row['seconds'],100*.8*.85*.95)
        self.assertEqual(row['producer']['character_id'],1)

    def test_reactions_only_use_reaction_skill_and_explicit_manual_mode(self):
        r=self.p.calculate(130,1,self.settings,skill_profiles=[self.character()],manufacturer_id=1)['queue'][0]
        self.assertAlmostEqual(r['seconds'],80)
        self.settings['reaction']['skill_time']=.5
        r=self.p.calculate(130,1,self.settings,skill_profiles=[self.character()],manufacturer_id=0)['queue'][0]
        self.assertEqual(r['seconds'],50)

    def test_selected_character_is_retained_and_no_character_means_manual(self):
        self.c.recipes[100]['skills']=[{'typeID':11452,'level':3}]
        characters=[self.character(1,science=1),self.character(2,industry=3),self.character(3)]
        self.assertEqual(self.plan(1,skill_profiles=characters)['queue'][0]['producer']['status'],'manual')
        self.assertEqual(self.plan(1,skill_profiles=characters,manufacturer_id=3)['queue'][0]['producer']['character_id'],3)
        fixed=self.plan(1,skill_profiles=characters,manufacturer_id=1)['queue'][0]['producer']
        self.assertEqual((fixed['character_id'],fixed['status']),(1,'missing'))
        self.assertEqual(fixed['missing_skills'][0]['active'],1)

    def test_missing_skill_data_falls_back_with_visible_warning(self):
        row=self.plan(1,manufacturer_id=1)['queue'][0]
        self.assertEqual(row['seconds'],100)
        self.assertEqual(row['producer']['status'],'manual')
        self.assertIn('skilladat',row['producer']['warning'])


class ProductionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=App(self.tmp.name,ROOT/'data/catalog.sqlite3',0)
    def skills(self,cid,active=3):
        self.app.store.add_character(cid,f'Pilot {cid}')
        data={'total_sp':1000,'skills':[{'skill_id':3380,'trained_skill_level':5,'active_skill_level':active,'skillpoints_in_skill':1000}]}
        self.app.store.save_snapshots(cid,{'skills':{'data':data,'fetched':time.time(),'expires':time.time()+3600,'etag':None}})

    def test_profiles_use_active_levels_and_corporation_membership(self):
        self.skills(1,2);self.skills(2,5)
        self.app.store.character_corporation(1,9001,'Alpha');self.app.store.character_corporation(2,9002,'Beta')
        result=profiles(self.app.store,self.app.store.settings(),9001)
        self.assertEqual([r['id'] for r in result],[1]);self.assertEqual(result[0]['levels'][3380],2)

    def test_saved_manufacturer_survives_restart_and_manual_does_not_double_skills(self):
        self.skills(1,5)
        saved=self.app.save_plan({'product_id':590,'quantity':2,'manufacturer_id':1})['id']
        other=App(self.tmp.name,ROOT/'data/catalog.sqlite3',0)
        self.assertEqual(other.store.plans()[0]['manufacturer_id'],1)
        plan=other.plan(590,2,saved)
        self.assertEqual(plan['manufacturer_id'],1)
        self.assertEqual(next(r for r in plan['queue'] if r['id']==590)['producer']['character_id'],1)

    def test_catalog_carries_required_skill_metadata_and_bonuses(self):
        self.assertTrue(self.app.catalog.recipes[92822]['skills'])
        self.assertEqual(self.app.catalog.skill_time_bonuses[77725],-1)

    def test_same_build_old_local_catalog_is_augmented_without_overwriting_it(self):
        target=Path(self.tmp.name)/'old-catalog.sqlite3'
        shutil.copy2(ROOT/'data/catalog.sqlite3',target)
        with sqlite3.connect(target) as db:
            db.execute('ALTER TABLE recipes DROP COLUMN skills')
            db.execute("DELETE FROM meta WHERE key='requiredSkillTimeBonuses'")
        catalog=Catalog(target,pi_fallback=ROOT/'data/catalog.sqlite3')
        self.assertTrue(catalog.recipes[92822]['skills'])
        self.assertEqual(catalog.skill_time_bonuses[11452],-1)

    def test_removed_producer_does_not_break_existing_material_reservations(self):
        self.skills(1,5)
        saved=self.app.save_plan({'product_id':590,'quantity':1,'manufacturer_id':1})['id']
        self.app.store.forget_character(1)
        plan=self.app.plan(590,1,saved,manufacturer_id='1')
        self.assertEqual(next(r for r in plan['queue'] if r['id']==590)['producer']['status'],'manual')

    def test_large_reaction_can_be_saved(self):
        product=next(tid for tid,r in self.app.catalog.recipes.items() if r['activity']=='reaction' and len(r['materials'])<4)
        saved=self.app.save_plan({'product_id':product,'quantity':100_000_000})['id']
        self.assertEqual(next(p for p in self.app.store.plans() if p['id']==saved)['quantity'],100_000_000)

    def test_combined_shortage_preserves_bpc_run_unit(self):
        self.app.save_plan({'product_id':590,'quantity':2})
        summary=self.app.shopping_summary()
        bp_id=self.app.catalog.recipes[590]['bp_id']
        row=next(r for r in summary['rows'] if r['id']==bp_id)
        self.assertEqual((row['buy'],row['unit']),(2,'run'))

    def test_shared_reaction_formula_is_only_purchased_once_per_pool(self):
        product=next(tid for tid,r in self.app.catalog.recipes.items() if r['activity']=='reaction' and len(r['materials'])<4)
        for _ in range(2):self.app.save_plan({'product_id':product,'quantity':100})
        row=next(r for r in self.app.shopping_summary()['rows'] if r['id']==self.app.catalog.recipes[product]['bp_id'])
        self.assertEqual((row['buy'],row['unit']),(1,'db'))
