import copy
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from muhely.planner import Planner,PlanningError
from muhely.server import App
from muhely.store import Store,DEFAULT_SETTINGS
from muhely.reservations import revision
from muhely import stable_plans
from test_planner import FakeCatalog


class SkipReactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=App.__new__(App);self.app.store=Store(self.tmp.name)
        c=FakeCatalog();c.lock=threading.RLock()
        c.recipe(100,{110:2,120:3});c.recipe(110,{130:5});c.recipe(120,{130:7})
        c.recipe(130,{200:2},activity='reaction')
        self.app.catalog=c;self.app.planner=Planner(c);self.app.planning_lock=threading.RLock()
        settings=copy.deepcopy(DEFAULT_SETTINGS)
        for a in ['manufacturing','reaction']:settings[a].update(material_role=0,material_rig=0,time_role=0,time_rig=0)
        self.context=dict(settings=settings,stock={130:10,200:1000},wip={130:3},blueprints=[],jobs=[],stale=[],
            material_locations={},skill_profiles=[],corporation_id=None,inventory={},parameters={})
        self.app._context=lambda cid=None:{**self.context,'corporation_id':cid}
        self.app.scope_id=lambda cid:cid
    def rows(self,p):return {r['id']:r for r in p['rows']}
    def save(self,name='A',skip=False,corp=None):
        result=self.app.save_plan(dict(product_id=100,quantity=1,name=name,skip_reactions=skip,corporation_id=corp))
        return result['id']
    def test_reaction_becomes_terminal_input_with_stock_and_wip_netted_once(self):
        p=self.app.plan(100,1,skip_reactions=True);r=self.rows(p)
        self.assertEqual((r[130]['required'],r[130]['used_stock'],r[130]['used_wip'],r[130]['buy']),(31,10,3,18))
        self.assertEqual((r[130]['activity'],r[130]['runs'],r[130]['seconds'],r[130]['materials']),('buy',0,0,[]))
        self.assertNotIn(200,r);self.assertFalse(any(x['activity']=='reaction' for x in p['queue']))
        self.assertNotIn(1130,[b['id'] for b in p['blueprint_shortages']+p['blueprint_usage']])
        self.assertTrue(p['skip_reactions'])
        normal=self.app.plan(100,1)
        self.assertEqual(self.rows(normal)[130]['runs'],18);self.assertIn(200,self.rows(normal))
    def test_force_build_cannot_reenable_skipped_reaction_and_manual_stock_still_works(self):
        self.context['parameters']={130:{'mode':'build'}};self.context['inventory']={130:{'quantity':30,'wip':0}}
        p=self.app.plan(100,1,skip_reactions=True)
        self.assertEqual(self.rows(p)[130]['buy'],1);self.assertNotIn(200,self.rows(p))
    def test_a_reaction_selected_as_target_is_also_purchased(self):
        p=self.app.plan(130,50,skip_reactions=True)
        self.assertEqual(p['queue'],[]);self.assertEqual(self.rows(p)[130]['buy'],37)
    def test_saved_mode_reserves_products_not_reaction_inputs_and_survives_reload(self):
        a=self.save(skip=True);saved=self.app.store.plans()[0];self.assertIs(saved['skip_reactions'],True)
        a_plan=self.app.plan(100,1,a);self.assertFalse(a_plan['saved_plan']['preview_changed'])
        allocation=self.app._allocate(self.app.store.plans(),self.context)
        self.assertNotIn(200,allocation['totals']);self.assertEqual(allocation['totals'][130]['stock'],10)
        b=self.save('B',False)
        other=self.app.plan(100,1,b);self.assertEqual(self.rows(other)[130]['runs'],31)
        own=self.app.plan(100,1,a);self.assertEqual(self.rows(own)[130]['used_wip'],3)
        self.assertIs(next(p for p in Store(self.tmp.name).plans() if p['id']==a)['skip_reactions'],True)
        self.context['stock'][200]=0
        shopping=self.app.shopping_summary();self.assertIn(130,[r['id'] for r in shopping['rows']]);self.assertIn(200,[r['id'] for r in shopping['rows']])
    def test_preview_does_not_mutate_reservations_and_saving_false_restores_reaction(self):
        a=self.save(skip=False);before=self.app.store.plans()
        preview=self.app.plan(100,1,a,skip_reactions=True)
        self.assertTrue(preview['saved_plan']['preview_changed']);self.assertEqual(self.app.store.plans(),before)
        self.app.save_plan(dict(id=a,product_id=100,quantity=1,skip_reactions=True))
        self.assertTrue(self.app.plan(100,1,a)['skip_reactions'])
        self.app.save_plan(dict(id=a,product_id=100,quantity=1))  # Missing option inherits saved mode.
        self.assertTrue(self.app.plan(100,1,a)['skip_reactions'])
        self.app.save_plan(dict(id=a,product_id=100,quantity=1,skip_reactions=False))
        self.assertIn(200,self.rows(self.app.plan(100,1,a)))
    def test_corporation_mode_is_independent_of_personal_plan(self):
        a=self.save(skip=True);b=self.save('Corp',False,42)
        corp=self.app.plan(100,1,b,corporation_id=42)
        self.assertFalse(corp['skip_reactions']);self.assertEqual(self.rows(corp)[130]['used_stock'],10)
        self.assertTrue(self.app.plan(100,1,a)['skip_reactions'])
    def test_cache_and_reservation_revision_change_with_mode(self):
        a=self.save();plans=self.app.store.plans()
        key=self.app._stable_key(self.context,plans,100,1,a,None)
        new=self.app._stable_key(self.context,plans,100,1,a,None,True);self.assertNotEqual(key,new)
        changed=[{**p,'skip_reactions':True} for p in plans]
        self.assertNotEqual(revision(plans),revision(changed))
        self.assertNotEqual(key,self.app._stable_key(self.context,changed,100,1,a,None))
        self.app.store.save_reservation_order(None,revision(plans),plans)
    def test_invalid_option_cannot_mutate_plan(self):
        a=self.save();before=self.app.store.plans()
        for value in ['true',1,[],{}]:
            with self.assertRaises(PlanningError):self.app.plan(100,1,a,skip_reactions=value)
            with self.assertRaises(PlanningError):self.app.save_plan(dict(id=a,product_id=100,quantity=1,skip_reactions=value))
        self.assertEqual(self.app.store.plans(),before)
    def test_scheduler_inherits_saved_mode_and_draft_override(self):
        a=self.save(skip=True)
        def build(context,store,catalog,calculate,data):return calculate(context)
        with patch('muhely.server.scheduler.build',side_effect=build):
            p=self.app.schedule(dict(product_id=100,quantity=1,saved_plan_id=a))
            self.assertTrue(p['skip_reactions']);self.assertNotIn(200,self.rows(p))
            p=self.app.schedule(dict(product_id=100,quantity=1,saved_plan_id=a,skip_reactions=False))
            self.assertFalse(p['skip_reactions']);self.assertIn(200,self.rows(p))
        self.assertTrue(self.app.store.plans()[0]['skip_reactions'])
    def test_legacy_database_migration_defaults_to_reactions_enabled(self):
        with tempfile.TemporaryDirectory() as folder:
            with sqlite3.connect(Path(folder)/'muhely.sqlite3') as db:
                db.execute('CREATE TABLE plans(id TEXT PRIMARY KEY,name TEXT,product_id INTEGER,quantity INTEGER,created REAL,saved_inputs TEXT)')
                db.execute("INSERT INTO plans VALUES('old','Legacy',100,1,1,NULL)")
            store=Store(folder);self.assertIs(store.plans()[0]['skip_reactions'],False)

    def test_scheduler_waits_for_purchased_reaction_output_without_scheduling_its_inputs(self):
        import test_scheduler
        from muhely import scheduler
        f=test_scheduler.SchedulerTests();f.setUp();self.addCleanup(f.doCleanups)
        f.recipe(200,{130:3},activity='reaction')
        def calculate(ctx):return dict(source='manual',scope_label='Personal',**f.planner.calculate(100,10,ctx['settings'],ctx['inventory'],ctx['parameters'],ctx['stock'],ctx['wip'],ctx['blueprints'],ctx['jobs'],skip_reactions=True,skill_profiles=ctx['skill_profiles']))
        result=scheduler.build(f.context,f.store,f.catalog,calculate,dict(owned_only=True,min_job_hours=0,supply_at=test_scheduler.NOW+3600),test_scheduler.NOW)
        self.assertTrue(result['complete']);self.assertTrue(result['jobs'])
        self.assertTrue(all(j['activity']=='manufacturing' and j['start']>=test_scheduler.NOW+3600 for j in result['jobs']))
        self.assertEqual([(r['id'],r['buy']) for r in result['material_shortfall']],[(200,20)])


class SkipReactionsApiTests(unittest.TestCase):
    from test_saved_plans import SavedPlanApiTests as _base
    setUp=_base.setUp
    close=_base.close
    request=_base.request
    def test_query_save_reload_and_legacy_default(self):
        url='/api/plan?product_id=22428&quantity=1'
        status,p=self.request(url+'&skip_reactions=1');self.assertEqual(status,200,p)
        self.assertTrue(p['skip_reactions']);self.assertFalse(any(r['activity']=='reaction' for r in p['queue']))
        status,saved=self.request('/api/plans/save',dict(product_id=22428,quantity=1,skip_reactions=True))
        self.assertEqual(status,200,saved)
        status,p=self.request(url+'&saved_plan_id='+saved['id']);self.assertEqual(status,200,p);self.assertTrue(p['skip_reactions'])
        status,p=self.request(url+'&skip_reactions=0');self.assertEqual(status,200,p)
        self.assertTrue(any(r['activity']=='reaction' for r in p['queue']))
        self.assertFalse(self.request('/api/plan?product_id=590&quantity=1')[1]['skip_reactions'])
    def test_unknown_query_and_non_boolean_save_are_rejected(self):
        for value in ['true','2']:
            self.assertEqual(self.request('/api/plan?product_id=22428&quantity=1&skip_reactions='+value)[0],400)
        self.assertEqual(self.request('/api/plans/save',dict(product_id=22428,quantity=1,skip_reactions='true'))[0],400)
        self.assertEqual(self.app.store.plans(),[])
