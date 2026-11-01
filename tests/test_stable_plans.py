import copy
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import threading
import unittest

from muhely.server import App
from muhely.store import Store,DEFAULT_SETTINGS
from muhely.planner import Planner,AssetSnapshotPending
from muhely import stable_plans
from test_planner import FakeCatalog

NOW=1800000000
def iso(t):return datetime.fromtimestamp(t,timezone.utc).isoformat()

class StablePlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=App.__new__(App);self.app.store=Store(self.tmp.name);self.app.store.add_character(1,'Pilot')
        c=FakeCatalog();c.lock=threading.RLock();c.recipe(100,{110:1});c.recipe(101,{200:5});c.recipe(110,{200:5});c.recipe(200,{201:1},activity='reaction')
        self.app.catalog=c;self.app.planner=Planner(c);self.app.planning_lock=threading.RLock()
        settings=copy.deepcopy(DEFAULT_SETTINGS);settings['source']='eve'
        for a in ['manufacturing','reaction']:settings[a].update(material_role=0,material_rig=0,time_role=0,time_rig=0)
        self.context=dict(settings=settings,stock={200:5},wip={110:1},blueprints=[],jobs=[dict(job_id=1,product_type_id=110,blueprint_type_id=1110,activity_id=1,status='active',runs=1,start_date=iso(NOW-600),end_date=iso(NOW+60),assets_as_of=NOW-300,assets_expires=NOW+3600,character_id=1,character_name='Pilot',expected_output=1)],stale=[],material_locations={'stock':{200:{6001:5}},'wip':{110:{6001:1}}},skill_profiles=[],corporation_id=None,inventory={},parameters={})
        self.app._context=lambda cid=None:self.context
        for i,product in enumerate([100,101]):
            self.app.store.save_plan(dict(id=str(i),name='Salvation' if i==0 else 'Purifier 50',product_id=product,quantity=1,created=i+1,reserved_at=i+1,reserve_active=True,corporation_id=None,manufacturer_id=None))
    def rows(self,p):return {r['id']:r for r in p['rows']}
    def plan(self,product=101,**kw):return self.app.plan(product,1,saved_plan_id='0' if product==100 else '1',**kw)
    def delivered(self):
        self.context['wip']={};self.context['jobs'][0].update(status='delivered',completed_date=iso(NOW-10),expected_output=0)
    def prime_all(self):
        plans=self.app.store.plans();allocation=self.app._allocate(plans,self.context)
        self.app._remember_allocations(plans,self.context,allocation)
    def test_delivery_lag_does_not_steal_reactions_from_the_other_plan(self):
        self.prime_all();before=self.app.store.plans();normal=self.plan()
        self.assertEqual(self.rows(normal)[200]['missing'],0)
        self.delivered()
        with self.assertRaises(AssetSnapshotPending):self.plan()
        preview=self.plan(allow_preview=True)
        self.assertTrue(preview['preview_only']);self.assertTrue(preview['frozen_snapshot']);self.assertTrue(preview['reservation_summary']['provisional'])
        self.assertEqual(self.rows(preview)[200]['used_stock'],5);self.assertEqual(self.rows(preview)[200]['runs'],0)
        self.assertEqual(preview['inventory_wait']['frozen_snapshot_at'],normal['calculated_at'])
        first=self.plan(100,allow_preview=True);self.assertEqual(self.rows(first)[110]['used_wip'],1)
        self.assertEqual(self.rows(first)[110]['on_hand'],0)  # Historical WIP, never invented live stock.
        self.assertEqual(self.app.store.plans(),before)
        with self.assertRaises(AssetSnapshotPending):self.app.set_reservation('1',True)
        self.assertEqual(self.app.store.plans(),before)
    def test_fresh_inventory_replaces_the_frozen_view_and_preserves_other_plan_coverage(self):
        self.prime_all();self.delivered();self.assertTrue(self.plan(allow_preview=True)['frozen_snapshot'])
        self.context['stock'][110]=1;self.context['jobs'][0]['assets_as_of']=NOW
        result=self.plan(allow_preview=True);self.assertFalse(result.get('preview_only',False));self.assertFalse(result.get('frozen_snapshot',False))
        self.assertEqual(self.rows(result)[200]['missing'],0)
        self.assertEqual(self.rows(self.plan(100))[110]['used_stock'],1)
    def test_new_running_job_with_coherent_assets_releases_only_its_own_inputs(self):
        self.context['wip']={};self.context['jobs']=[];self.context['stock']={200:10}
        self.prime_all();self.assertEqual(self.rows(self.plan())[200]['used_stock'],5)
        self.context['stock']={200:5};self.context['wip']={110:1}
        self.assertEqual(self.rows(self.plan())[200]['used_stock'],5);self.assertEqual(self.rows(self.plan(100))[110]['used_wip'],1)
    def test_cached_views_never_cross_scope_target_settings_parameters_or_priority(self):
        self.prime_all();plans=self.app.store.plans()
        original=self.app._stable_key(self.context,plans,101,1,'1',None)
        self.assertIsNotNone(stable_plans.load(self.app.store,original))
        variants=[]
        for section,field,value in [('settings','location_ids',[42]),('parameters',100,{'me':5}),('inventory',200,{'quantity':1})]:
            ctx=copy.deepcopy(self.context);ctx[section][field]=value;variants.append((ctx,plans,101,1,'1',None))
        ctx=copy.deepcopy(self.context);ctx['corporation_id']=42;variants.append((ctx,plans,101,1,'1',None))
        other=copy.deepcopy(plans);other[0]['reserved_at']=999;variants.append((self.context,other,101,1,'1',None))
        variants.extend([(self.context,plans,100,1,'1',None),(self.context,plans,101,2,'1',None),(self.context,plans,101,1,'0',None),(self.context,plans,101,1,'1',1)])
        for args in variants:self.assertIsNone(stable_plans.load(self.app.store,self.app._stable_key(*args)))
    def test_preview_never_replaces_confirmed_cache_and_new_targets_keep_uncertain_preview(self):
        self.prime_all();self.delivered();preview=self.plan(allow_preview=True)
        key=self.app._stable_key(self.context,self.app.store.plans(),101,1,'1',None)
        stable_plans.remember(self.app.store,key,'bad',preview)
        self.assertFalse(stable_plans.load(self.app.store,key).get('preview_only',False))
        uncached=self.app.plan(101,2,saved_plan_id='1',allow_preview=True)
        self.assertTrue(uncached['preview_only']);self.assertFalse(uncached.get('frozen_snapshot',False))
    def test_matching_snapshots_do_not_rewrite_the_cached_allocations(self):
        self.prime_all()
        with self.app.store.db() as db:before=[tuple(r) for r in db.execute('SELECT * FROM stable_plan_views ORDER BY key')]
        self.prime_all()
        with self.app.store.db() as db:after=[tuple(r) for r in db.execute('SELECT * FROM stable_plan_views ORDER BY key')]
        self.assertEqual(before,after)
