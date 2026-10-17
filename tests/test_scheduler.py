import copy
import tempfile
import unittest
from datetime import datetime,timezone
from test_planner import FakeCatalog
from muhely.planner import Planner,PlanningError
from muhely.scheduler import build,Materials
from muhely.store import Store,DEFAULT_SETTINGS

NOW=1800000000
def iso(value):return datetime.fromtimestamp(value,timezone.utc).isoformat()
def bp(item,product=100,owner=1,runs=-1,me=0):
    return dict(item_id=item,type_id=product+1000,character_id=owner,quantity=-1 if runs==-1 else -2,runs=runs,material_efficiency=me,time_efficiency=0)


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
        self.catalog=FakeCatalog();self.catalog.skill_time_bonuses={};self.recipe(100,{200:2})
        self.planner=Planner(self.catalog);settings=copy.deepcopy(DEFAULT_SETTINGS)
        for a in ['manufacturing','reaction']:settings[a].update(material_role=0,material_rig=0,time_role=0,time_rig=0)
        workers=[]
        for i in [1,2]:
            self.store.add_character(i,'Pilot '+str(i));self.jobs(i,[])
            workers.append(dict(id=i,name='Pilot '+str(i),available=True,as_of=NOW,stale=False,levels={3380:5,45746:5}))
        self.context=dict(settings=settings,stock={},wip={},blueprints=[bp(1),bp(2,owner=2)],jobs=[],stale=[],skill_profiles=workers,corporation_id=None,inventory={},parameters={},reservations={})
    def recipe(self,tid,materials,**kw):
        self.catalog.recipe(tid,materials,**kw);self.catalog.recipes[tid]['skills']=[]
    def jobs(self,cid,rows):self.store.save_snapshots(cid,{'jobs':dict(data=rows,fetched=NOW,expires=NOW+3600,etag=None)})
    def run_plan(self,quantity=10,product=100,**opts):
        def calc(ctx):
            result=self.planner.calculate(product,quantity,ctx['settings'],ctx['inventory'],ctx['parameters'],ctx['stock'],ctx['wip'],ctx['blueprints'],ctx['jobs'],reservations=ctx['reservations'],skill_profiles=ctx['skill_profiles'])
            return dict(result,source='manual',scope_label='Personal')
        return build(self.context,self.store,self.catalog,calc,opts,NOW)
    def test_two_characters_run_in_parallel_without_overlapping_slots_or_blueprints(self):
        result=self.run_plan();self.assertTrue(result['complete']);self.assertEqual(len(result['jobs']),2)
        self.assertEqual({j['character_id'] for j in result['jobs']},{1,2});self.assertEqual(result['seconds'],400)
        self.assertTrue(all(j['start']==NOW for j in result['jobs']))
        self.assertTrue(all(not j['procure_blueprint'] for j in result['jobs']))
    def test_one_original_is_serial_and_procuring_copies_improves_finish(self):
        self.context['blueprints']=[bp(1)]
        serial=self.run_plan();parallel=self.run_plan(owned_only=False)
        self.assertGreater(serial['seconds'],parallel['seconds']);self.assertTrue(parallel['blueprint_shortages'])
        self.assertEqual(parallel['blueprint_shortages'][0]['copies'],1)
        self.assertTrue(any(j['procure_blueprint'] for j in parallel['jobs']))
    def test_missing_skills_are_not_assigned_and_unknown_job_data_is_excluded(self):
        self.catalog.recipes[100]['skills']=[{'typeID':999,'level':3}]
        self.context['skill_profiles'][1]['levels'][999]=3
        result=self.run_plan(transfer_blueprints=True);self.assertEqual({j['character_id'] for j in result['jobs']},{2})
        with self.store.db() as db:db.execute("DELETE FROM snapshots WHERE character_id=2 AND kind='jobs'")
        result=self.run_plan();self.assertFalse(result['complete']);self.assertTrue(result['blocked'])
    def test_owner_transfer_is_explicit(self):
        self.context['blueprints']=[bp(1,owner=1)];self.context['skill_profiles'][0]['levels'][3380]=0
        self.assertFalse(self.run_plan()['complete'])
        result=self.run_plan(transfer_blueprints=True);self.assertTrue(result['complete']);self.assertTrue(result['jobs'][0]['transfer_required'])
    def test_other_plan_bpc_holds_are_deducted_and_owned_mode_is_partial(self):
        self.context['blueprints']=[bp(1,runs=5)];self.context['reservations']={1100:{'blueprint_runs':{1:2}}}
        result=self.run_plan();self.assertFalse(result['complete']);self.assertEqual(result['runs'],3)
        self.assertEqual(result['blueprint_shortages'][0]['runs'],7)
        self.assertTrue(self.run_plan(owned_only=False)['complete'])
    def test_busy_original_and_character_slot_wait_for_current_job(self):
        self.context['blueprints']=[bp(1)];self.context['skill_profiles']=self.context['skill_profiles'][:1]
        self.jobs(1,[dict(job_id=1,activity_id=1,status='active',blueprint_id=1,runs=2,end_date=iso(NOW+500))])
        result=self.run_plan();self.assertEqual(result['jobs'][0]['start'],NOW+500)
        self.jobs(1,[dict(job_id=1,activity_id=1,status='paused',blueprint_id=1,runs=2)])
        self.assertFalse(self.run_plan()['complete'])
    def test_existing_jobs_outside_inventory_scope_still_occupy_slots(self):
        self.context['blueprints']=[bp(1)];self.context['skill_profiles']=self.context['skill_profiles'][:1]
        self.jobs(1,[dict(job_id=999,activity_id=1,status='active',blueprint_id=999,runs=1,end_date=iso(NOW+1000))])
        result=self.run_plan();self.assertEqual(result['jobs'][0]['start'],NOW+1000)
    def test_reaction_and_manufacturing_slots_are_independent(self):
        self.recipe(130,{200:1},activity='reaction');self.recipe(100,{130:1})
        self.context['blueprints']=[bp(1),bp(3,product=130)]
        self.context['skill_profiles']=self.context['skill_profiles'][:1]
        result=self.run_plan(quantity=2);self.assertTrue(result['complete'])
        parent=next(j for j in result['jobs'] if j['product_id']==100);child=next(j for j in result['jobs'] if j['product_id']==130)
        self.assertGreaterEqual(parent['start'],child['end'])
    def test_split_material_rounding_is_recomputed_and_shared_materials_not_double_spent(self):
        self.context['settings']['manufacturing']['material_role']=20
        self.recipe(100,{200:11});self.context['skill_profiles'][0]['levels'][3387]=2
        self.context['skill_profiles'][1]['levels'][3387]=1
        self.context['blueprints']=[bp(1),bp(2),bp(3),bp(4,owner=2),bp(5,owner=2)]
        result=self.run_plan(quantity=5);self.assertTrue(result['complete'])
        raw=next(r for r in result['material_shortfall'] if r['id']==200)
        self.assertEqual(raw['buy'],45)  # a single five-run job would need only 44
        self.assertEqual(sum(j['runs'] for j in result['jobs']),5)
    def test_wip_is_not_available_before_job_end_and_manual_unknown_is_not_assumed(self):
        self.recipe(100,{110:1});self.recipe(110,{200:2})
        self.context['wip']={110:10};self.context['jobs']=[dict(product_type_id=110,expected_output=10,status='active',end_date=iso(NOW+1200))]
        result=self.run_plan();self.assertTrue(result['complete']);self.assertEqual(result['jobs'][0]['start'],NOW+1200)
        self.context['inventory']={110:{'wip':10}}
        result=self.run_plan();self.assertFalse(result['complete']);self.assertTrue(result['material_warnings'])
    def test_finished_target_wip_still_sets_completion_time(self):
        self.context['wip']={100:10};self.context['jobs']=[dict(product_type_id=100,expected_output=10,status='active',end_date=iso(NOW+500))]
        result=self.run_plan();self.assertTrue(result['complete']);self.assertEqual(result['finish'],NOW+500);self.assertEqual(result['jobs'],[])
    def test_future_start_does_not_make_current_job_snapshots_stale(self):
        result=self.run_plan(start=NOW+3*86400)
        self.assertTrue(result['complete']);self.assertEqual(result['jobs'][0]['start'],NOW+3*86400)
    def test_procurement_arrival_and_invalid_options(self):
        result=self.run_plan(supply_at=NOW+1000);self.assertEqual(result['jobs'][0]['start'],NOW+1000)
        for opts in [dict(characters=[999]),dict(characters=[True]),dict(owned_only=1),dict(start=float('nan'))]:
            with self.subTest(opts=opts),self.assertRaises(PlanningError):self.run_plan(**opts)
    def test_finer_batches_balance_unequal_character_speeds(self):
        self.context['skill_profiles'][1]['levels'][3380]=1
        result=self.run_plan(quantity=100)
        self.assertTrue(result['complete']);self.assertGreater(result['strategies_compared'],1)
        self.assertLess(result['seconds'],4800)
    def test_active_skill_slot_counts_and_intervals_are_consistent(self):
        self.context['skill_profiles'][0]['levels'].update({3387:2,24625:1})
        self.context['blueprints']=[bp(i) for i in range(1,5)]
        result=self.run_plan(quantity=36)
        self.assertTrue(result['complete']);self.assertEqual(result['workers'][0]['capacity']['manufacturing'],4)
        for key in ['blueprint_key']:
            grouped={}
            for job in result['jobs']:grouped.setdefault(job[key],[]).append(job)
            for jobs in grouped.values():
                jobs.sort(key=lambda j:j['start'])
                self.assertTrue(all(a['end']<=b['start'] for a,b in zip(jobs,jobs[1:])))
        grouped={}
        for job in result['jobs']:grouped.setdefault((job['character_id'],job['activity'],job['slot']),[]).append(job)
        for jobs in grouped.values():
            jobs.sort(key=lambda j:j['start']);self.assertTrue(all(a['end']<=b['start'] for a,b in zip(jobs,jobs[1:])))
    def test_stale_skills_are_excluded_until_refreshed(self):
        for worker in self.context['skill_profiles']:worker['stale']=True
        result=self.run_plan();self.assertFalse(result['complete']);self.assertTrue(all(w['excluded'] for w in result['workers']))
    def test_training_exclusion_does_not_remove_industry_capacity(self):
        from muhely.accounts import save
        save(self.store,{'accounts':[],'characters':{'1':{'account_id':None,'training_mode':'disabled'}}})
        result=self.run_plan();self.assertTrue(any(j['character_id']==1 for j in result['jobs']))

    def test_material_ledger_never_reuses_a_consumed_quantity(self):
        materials=Materials();materials.add(1,2,NOW);materials.add(1,3,NOW+100)
        self.assertEqual(materials.ready(1,3),NOW+100);materials.consume(1,2,NOW)
        self.assertEqual(materials.ready(1,3),NOW+100)
        with self.assertRaises(PlanningError):materials.consume(1,4,NOW+100)
