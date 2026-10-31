import copy
import tempfile
import unittest
from muhely.material_readiness import annotate_plan, annotate_schedule, locations
from muhely.planner import Planner
from muhely.store import Store, DEFAULT_SETTINGS
from test_planner import FakeCatalog


def blueprint(item, product, loc, runs=-1):
    return dict(item_id=item,type_id=product+1000,location_id=loc,root_location_id=loc,quantity=-1 if runs==-1 else -2,
                runs=runs,material_efficiency=0,time_efficiency=0,character_id=1)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.catalog=FakeCatalog();self.catalog.recipe(100,{110:2,120:3});self.catalog.recipe(110,{200:5});self.catalog.recipe(120,{200:7})
        self.settings=copy.deepcopy(DEFAULT_SETTINGS)
        for kind in ['manufacturing','reaction']:self.settings[kind].update(material_role=0,material_rig=0,time_role=0,time_rig=0)
        self.bps=[blueprint(1,100,6001),blueprint(2,110,6001),blueprint(3,120,6001)]
    def plan(self,**kw):
        return Planner(self.catalog).calculate(100,1,self.settings,blueprints=self.bps,**kw)
    def state(self,p,tid=100):return next(r for r in p['queue'] if r['id']==tid)['input_readiness']
    def test_three_source_states_and_physical_destination(self):
        p=self.plan(stock={110:2,120:3},material_locations={'stock':{110:{6001:2},120:{6001:3}}})
        r=self.state(p);self.assertEqual(r['status'],'stock');self.assertEqual(r['location_status'],'local');self.assertTrue(r['can_start_here'])
        p=self.plan(stock={110:2},wip={120:3},material_locations={'stock':{110:{6001:2}},'wip':{120:{6002:3}}})
        r=self.state(p);self.assertEqual(r['status'],'wip');self.assertEqual(r['location_status'],'transfer');self.assertFalse(r['can_start_here'])
        p=self.plan(stock={110:2},wip={120:1})
        r=self.state(p);self.assertEqual(r['status'],'missing');self.assertTrue(r['has_wip']);self.assertEqual(r['materials'][1]['missing'],2)
    def test_shared_stock_and_running_output_are_allocated_only_once(self):
        p=self.plan(stock={200:12},wip={200:8},material_locations={'stock':{200:{6001:12}},'wip':{200:{6001:8}}})
        states=[self.state(p,i) for i in [110,120]]
        self.assertEqual(sum(m['stock'] for r in states for m in r['materials']),12)
        self.assertEqual(sum(m['wip'] for r in states for m in r['materials']),8)
        self.assertEqual(sum(m['missing'] for r in states for m in r['materials']),11)
        self.assertEqual(states[0]['status'],'stock');self.assertEqual(states[1]['status'],'missing')
    def test_reservations_never_claim_the_same_material_or_unproven_station(self):
        p=self.plan(stock={110:4,120:3},reservations={110:{'stock':2}},material_locations={'stock':{110:{6001:2,6002:2},120:{6001:3}}})
        r=self.state(p);self.assertEqual(r['status'],'stock');self.assertEqual(r['location_status'],'unknown')
        self.assertEqual(r['materials'][0]['stock'],2);self.assertIsNone(r['materials'][0]['allocations'][0]['location_id'])
        p=self.plan(stock={110:2,120:3},reservations={110:{'stock':2}})
        self.assertEqual(self.state(p)['status'],'missing')
    def test_manual_inventory_does_not_claim_real_asset_location(self):
        p=self.plan(stock={110:2,120:3},inventory={110:{'quantity':2}},material_locations={'stock':{110:{6001:2},120:{6001:3}}})
        r=self.state(p);self.assertEqual(r['status'],'stock');self.assertEqual(r['location_status'],'unknown')
    def test_bpc_target_follows_consumed_copies_and_is_conservative_for_mixed_places(self):
        self.bps=[blueprint(10,100,6001,1),blueprint(11,100,6002,1)]
        p=self.plan(stock={110:2,120:3});self.assertEqual(self.state(p)['target_location_id'],6001)
        p=Planner(self.catalog).calculate(100,2,self.settings,blueprints=self.bps)
        r=self.state(p);self.assertEqual(r['blueprint_locations'],[6001,6002]);self.assertIsNone(r['target_location_id'])
        self.bps=[blueprint(10,100,6001,1)]
        p=Planner(self.catalog).calculate(100,2,self.settings,blueprints=self.bps)
        self.assertIsNone(self.state(p)['target_location_id'])
    def test_unknown_manual_and_multiple_bpo_locations(self):
        self.bps=[];self.assertIsNone(self.state(self.plan())['target_location_id'])
        self.bps=[blueprint(1,100,6001),blueprint(2,100,6002)]
        self.assertIsNone(self.state(self.plan())['target_location_id'])
    def test_annotations_do_not_change_math_and_are_repeatable(self):
        p=self.plan(stock={200:10});before=copy.deepcopy(p)
        annotate_plan(p,{'stock':{200:{6001:10}}});annotate_plan(p,{'stock':{200:{6001:10}}})
        for row in p['rows']:row.pop('input_readiness',None)
        for row in before['rows']:row.pop('input_readiness',None)
        self.assertEqual(p,before)
    def test_scheduler_follows_exact_blueprint_and_actual_allocations_without_mutation(self):
        p=self.plan(stock={200:12},wip={200:8})
        def material(n,source,job=None):return {'id':200,'name':'Raw <ore>','quantity':n,'allocations':[{'quantity':n,'source':source,'job_id':job,'available_at':99}]}
        jobs=[{'id':1,'blueprint_item_id':2,'materials':[material(10,'stock')]},
              {'id':2,'blueprint_item_id':3,'materials':[material(2,'stock'),material(8,'wip'),material(1,'job',1),material(10,'purchase')]}]
        self.bps[1]['root_location_id']=6002
        result={'jobs':copy.deepcopy(jobs)}
        context={'blueprints':self.bps,'material_locations':{'stock':{200:{6002:12}},'wip':{200:{6001:8}}}}
        annotate_schedule(result,p,context)
        a,b=result['jobs'];self.assertEqual(a['input_readiness']['status'],'stock');self.assertTrue(a['input_readiness']['can_start_here'])
        self.assertEqual(b['input_readiness']['status'],'missing');self.assertTrue(b['input_readiness']['has_wip']);self.assertEqual(b['input_readiness']['location_status'],'transfer')
        self.assertEqual(b['input_readiness']['materials'][2]['allocations'][0]['location_id'],6002)
        for job in result['jobs']:job.pop('input_readiness')
        self.assertEqual(result['jobs'],jobs)
    def test_physical_inventory_resolves_nested_packaged_assets_and_keeps_scopes_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.add_character(1,'Pilot');store.add_character(2,'Other')
            rows=[dict(item_id=9,type_id=999,location_id=6001,quantity=1,is_singleton=True),
                  dict(item_id=10,type_id=200,location_id=9,quantity=12,is_singleton=False),
                  dict(item_id=11,type_id=200,location_id=6002,quantity=99,is_singleton=True)]
            def snap(data):return dict(data=data,fetched=1,expires=2,etag=None)
            for cid in [1,2]:store.save_snapshots(cid,{'assets':snap(rows if cid==1 else [dict(item_id=12,type_id=200,location_id=6003,quantity=100,is_singleton=False)]),'blueprints':snap([]),'jobs':snap([])})
            settings={**self.settings,'source':'eve','character_ids':[1],'location_ids':[]}
            physical=locations(store,settings,jobs=[dict(product_type_id=200,expected_output=8,output_location_id=9)])
            self.assertEqual(physical,{'stock':{200:{6001:12}},'wip':{200:{6001:8}}})
            settings['location_ids']=[6002];self.assertEqual(locations(store,settings)['stock'],{})
            class Corp:
                def corporation_snapshot(self,cid,kind):self.cid=cid;return snap([dict(item_id=13,type_id=200,location_id=6004,quantity=7,is_singleton=False)])
            settings['location_ids']=[];corp=Corp();self.assertEqual(locations(corp,settings,42)['stock'],{200:{6004:7}});self.assertEqual(corp.cid,42)
            settings['source']='manual';self.assertEqual(locations(store,settings),{})

    def test_real_scheduler_marks_covered_inputs_and_retains_existing_times(self):
        from test_scheduler import SchedulerTests
        fixture=SchedulerTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.context['stock']={200:10};fixture.context['wip']={200:10}
        fixture.context['jobs']=[fixture.live_job(product=200,expected_output=10)]
        fixture.context['blueprints'][0]['root_location_id']=6001
        fixture.context['blueprints'][1]['root_location_id']=6002
        without=fixture.run_plan()
        fixture.context['material_locations']={'stock':{200:{6001:10}},'wip':{200:{6002:10}}}
        actual=fixture.run_plan()
        self.assertTrue(actual['complete'])
        self.assertEqual(sum(m['stock'] for j in actual['jobs'] for m in j['input_readiness']['materials']),10)
        self.assertEqual(sum(m['wip'] for j in actual['jobs'] for m in j['input_readiness']['materials']),10)
        self.assertTrue(any(j['input_readiness']['status']=='wip' for j in actual['jobs']))
        for result in [actual,without]:
            for job in result['jobs']:job.pop('input_readiness')
        self.assertEqual(actual,without)
