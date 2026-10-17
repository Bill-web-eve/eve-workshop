import copy
import tempfile
import unittest
from datetime import datetime,timezone
from test_planner import FakeCatalog
from muhely.planner import Planner,PlanningError
from muhely.scheduler import build,Materials,_strategy
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
        opts.setdefault('min_job_hours',0)
        def calc(ctx):
            result=self.planner.calculate(product,quantity,ctx['settings'],ctx['inventory'],ctx['parameters'],ctx['stock'],ctx['wip'],ctx['blueprints'],ctx['jobs'],reservations=ctx['reservations'],skill_profiles=ctx['skill_profiles'])
            return dict(result,source='manual',scope_label='Personal')
        if '_granularity' in opts:return _strategy(self.context,self.store,self.catalog,calc,opts,NOW,opts.pop('_granularity'))
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

    def test_independent_manufacturing_and_reaction_overlap_on_same_character(self):
        self.recipe(100,{110:1,130:1});self.recipe(110,{200:1});self.recipe(130,{200:1},activity='reaction')
        self.context['blueprints']=[bp(1),bp(2,product=110),bp(3,product=130)]
        self.context['skill_profiles']=self.context['skill_profiles'][:1]
        result=self.run_plan(quantity=1);self.assertTrue(result['complete'])
        jobs={j['product_id']:j for j in result['jobs']}
        self.assertEqual(jobs[110]['start'],NOW);self.assertEqual(jobs[130]['start'],NOW)
        self.assertEqual(jobs[110]['slot'],jobs[130]['slot'])
        self.assertEqual(jobs[110]['character_id'],jobs[130]['character_id'])
        self.assertGreaterEqual(jobs[100]['start'],max(jobs[110]['end'],jobs[130]['end']))
        self.assertEqual({d['job_id'] for d in jobs[100]['dependencies']},{jobs[110]['id'],jobs[130]['id']})

    def test_every_input_arrival_and_shared_output_allocation_gate_downstream_jobs(self):
        self.recipe(100,{110:1,120:1});self.recipe(110,{130:1});self.recipe(120,{130:1});self.recipe(130,{200:1},activity='reaction')
        self.catalog.recipes[120]['seconds']=300
        self.context['blueprints']=[bp(1),bp(2,product=110),bp(3,product=120),bp(4,product=130)]
        self.context['stock']={130:1}
        result=self.run_plan(quantity=1);self.assertTrue(result['complete'])
        jobs={j['id']:j for j in result['jobs']};spent={}
        for j in result['jobs']:
            latest=NOW
            for m in j['materials']:
                self.assertEqual(sum(a['quantity'] for a in m['allocations']),m['quantity'])
                for a in m['allocations']:
                    latest=max(latest,a['available_at']);self.assertLessEqual(a['available_at'],j['start'])
                    if a['source']=='job':
                        source=jobs[a['job_id']];self.assertEqual(source['product_id'],m['id'])
                        self.assertEqual(a['available_at'],source['end'])
                        spent[source['id']]=spent.get(source['id'],0)+a['quantity']
            self.assertEqual(j['materials_ready'],latest)
            self.assertEqual(j['material_wait'],latest-NOW)
        self.assertTrue(all(n<=jobs[k]['output'] for k,n in spent.items()))
        parent=next(j for j in result['jobs'] if j['product_id']==100)
        self.assertEqual(parent['start'],max(j['end'] for j in result['jobs'] if j['product_id'] in [110,120]))
        self.assertEqual(len(parent['dependencies']),2)

    def test_existing_wip_and_purchase_arrivals_are_visible_material_sources(self):
        self.recipe(100,{110:1,200:1});self.recipe(110,{200:1})
        self.context['wip']={110:1};self.context['jobs']=[dict(product_type_id=110,expected_output=1,status='active',end_date=iso(NOW+900))]
        result=self.run_plan(quantity=1,supply_at=NOW+500);job=result['jobs'][0]
        self.assertEqual(job['materials_ready'],NOW+900);self.assertEqual(job['start'],NOW+900)
        allocations={m['id']:m['allocations'][0] for m in job['materials']}
        self.assertEqual(allocations[110]['source'],'wip');self.assertEqual(allocations[200]['source'],'purchase')
        self.assertEqual(job['dependencies'],[])

    def test_failed_ledger_consumption_does_not_destroy_future_material(self):
        materials=Materials();materials.add(1,2,NOW,'stock');materials.add(1,3,NOW+100,'job',5)
        with self.assertRaises(PlanningError):materials.consume(1,4,NOW)
        self.assertEqual(materials.consume(1,4,NOW+100),[
            dict(quantity=2,available_at=NOW,source='stock',job_id=None),
            dict(quantity=2,available_at=NOW+100,source='job',job_id=5)])
        self.assertEqual(materials.consume(1,1,NOW+100)[0]['quantity'],1)

    def test_multi_stage_reactions_gate_manufacturing_and_partial_output_can_pipeline(self):
        self.recipe(100,{110:1});self.recipe(110,{120:2});self.recipe(120,{130:2},activity='reaction');self.recipe(130,{200:1},activity='reaction')
        self.context['blueprints']=[bp(1),bp(2,product=110),bp(3,product=120),bp(4,product=130)]
        self.context['skill_profiles']=self.context['skill_profiles'][:1]
        # Small installed batches let downstream jobs use only completed output.
        self.context['parameters']={tid:{'job_runs':1} for tid in [100,110,120,130]}
        result=self.run_plan(quantity=2);self.assertTrue(result['complete']);jobs={j['id']:j for j in result['jobs']}
        reactions=[j for j in result['jobs'] if j['activity']=='reaction']
        components=[j for j in result['jobs'] if j['product_id']==110]
        self.assertTrue(components);self.assertGreaterEqual(components[0]['start'],NOW+400)
        # All dependency edges, including reaction -> reaction, must obey time.
        pairs=set()
        for job in result['jobs']:
            for dep in job['dependencies']:
                source=jobs[dep['job_id']];self.assertLessEqual(source['end'],job['start']);pairs.add((source['product_id'],job['product_id']))
        self.assertEqual(pairs,{(130,120),(120,110),(110,100)})
        self.assertLess(components[0]['start'],max(j['end'] for j in reactions))

    def test_partial_stock_only_covers_its_own_jobs_not_the_rest_of_the_chain(self):
        self.recipe(100,{130:1});self.recipe(130,{200:1},activity='reaction')
        self.context['blueprints']=[bp(1),bp(2,product=130)];self.context['skill_profiles']=self.context['skill_profiles'][:1]
        self.context['parameters']={100:{'job_runs':1},130:{'job_runs':1}};self.context['stock']={130:1}
        result=self.run_plan(quantity=3);jobs={j['id']:j for j in result['jobs']};manufacturing=[j for j in result['jobs'] if j['activity']=='manufacturing']
        self.assertTrue(result['complete']);self.assertEqual(manufacturing[0]['start'],NOW)
        stock_uses=0;reaction_uses=0
        for job in manufacturing:
            for m in job['materials']:
                for a in m['allocations']:
                    if a['source']=='stock':stock_uses+=a['quantity']
                    if a['source']=='job':reaction_uses+=a['quantity'];self.assertGreaterEqual(job['start'],jobs[a['job_id']]['end'])
        self.assertEqual(stock_uses,1);self.assertEqual(reaction_uses,2)

    def test_real_fusion_thruster_waits_for_all_three_reaction_products(self):
        from pathlib import Path
        from muhely.catalog import Catalog
        self.catalog=Catalog(Path(__file__).resolve().parents[1]/'data/catalog.sqlite3');self.planner=Planner(self.catalog)
        product=next(tid for tid in self.catalog.recipes if self.catalog.name(tid)=='Fusion Thruster')
        levels={s['typeID']:5 for recipe in self.catalog.recipes.values() for s in recipe.get('skills',[])}
        levels.update({3380:5,3388:5,45746:5})
        for w in self.context['skill_profiles']:w['levels']=levels
        self.context['blueprints']=[]
        result=self.run_plan(quantity=10,product=product,owned_only=False)
        self.assertTrue(result['complete']);jobs={j['id']:j for j in result['jobs']}
        fusion=[j for j in result['jobs'] if j['product_id']==product]
        self.assertTrue(fusion)
        for job in fusion:
            self.assertGreater(job['start'],NOW)
            self.assertEqual({m['name'] for m in job['materials']},{'Tungsten Carbide','Phenolic Composites','Ferrogel'})
            self.assertEqual({d['material_id'] for d in job['dependencies']},{m['id'] for m in job['materials']})
            for m in job['materials']:
                self.assertEqual(sum(a['quantity'] for a in m['allocations']),m['quantity'])
                for a in m['allocations']:
                    self.assertEqual(a['source'],'job');source=jobs[a['job_id']]
                    self.assertEqual(source['activity'],'reaction');self.assertLessEqual(source['end'],job['start'])
        # With enough existing inputs, early manufacturing is intentional.
        self.context['stock']={m['typeID']:1000000 for m in self.catalog.recipes[product]['materials']}
        covered=self.run_plan(quantity=10,product=product,owned_only=False)
        self.assertTrue(covered['complete']);self.assertTrue(all(j['start']==NOW for j in covered['jobs']))

    def test_serial_terminal_reactions_combine_and_recompute_real_material_rounding(self):
        self.recipe(100,{200:11},activity='reaction');self.context['skill_profiles']=self.context['skill_profiles'][:1]
        self.context['blueprints']=[bp(1)];self.context['settings']['reaction']['material_rig']=2.6
        result=self.run_plan(quantity=20,_granularity=4)
        self.assertTrue(result['complete']);self.assertEqual(len(result['jobs']),1)
        self.assertEqual(result['merged_reaction_jobs'],3);self.assertEqual(result['jobs'][0]['runs'],20)
        self.assertEqual(result['jobs'][0]['materials'][0]['quantity'],215)
        self.assertEqual(next(r['buy'] for r in result['material_shortfall'] if r['id']==200),215)
        self.assertEqual(result['seconds'],1600)

    def test_useful_early_reaction_output_is_not_delayed_by_combining_jobs(self):
        from unittest.mock import patch
        self.recipe(100,{130:1});self.recipe(130,{200:1},activity='reaction')
        self.context['parameters']={100:{'job_runs':1}}
        self.context['skill_profiles']=self.context['skill_profiles'][:1];self.context['blueprints']=[bp(1),bp(2,product=130)]
        with patch('muhely.scheduler.compact_reactions',side_effect=lambda jobs,initial,catalog,settings,limits,start,shopping:(jobs,shopping,0)):
            original=self.run_plan(quantity=10,_granularity=4)
        result=self.run_plan(quantity=10,_granularity=4);self.assertEqual(result['finish'],original['finish'])
        self.assertGreater(len([j for j in result['jobs'] if j['activity']=='reaction']),1)
        before={j['id']:j for j in original['jobs'] if j['activity']=='manufacturing'};jobs={j['id']:j for j in result['jobs']}
        for j in result['jobs']:
            if j['activity']=='manufacturing':self.assertEqual(j['start'],before[j['id']]['start'])
            for d in j['dependencies']:self.assertLessEqual(jobs[d['job_id']]['end'],j['start'])

    def test_reaction_input_arrivals_prevent_combining_even_when_output_can_wait(self):
        self.recipe(100,{120:1});self.recipe(120,{130:1},activity='reaction');self.recipe(130,{200:1},activity='reaction')
        self.context['skill_profiles']=self.context['skill_profiles'][:1];self.context['blueprints']=[bp(1),bp(2,product=120),bp(3,product=130)]
        result=self.run_plan(quantity=12,_granularity=4);self.assertTrue(result['complete']);jobs={j['id']:j for j in result['jobs']}
        self.assertGreater(len([j for j in result['jobs'] if j['product_id']==120]),1)
        for j in result['jobs']:
            for m in j['materials']:
                self.assertEqual(sum(a['quantity'] for a in m['allocations']),m['quantity'])
                for a in m['allocations']:self.assertLessEqual(a['available_at'],j['start'])
            for d in j['dependencies']:self.assertLessEqual(jobs[d['job_id']]['end'],j['start'])

    def test_combined_reactions_respect_user_run_cap_and_thirty_day_duration(self):
        self.recipe(100,{200:1},activity='reaction');self.context['skill_profiles']=self.context['skill_profiles'][:1]
        self.context['blueprints']=[bp(1)];self.context['parameters']={100:{'job_runs':5}}
        result=self.run_plan(quantity=20,_granularity=4);self.assertEqual(len(result['jobs']),4)
        self.assertTrue(all(j['runs']<=5 for j in result['jobs']))
        self.context['parameters']={};self.catalog.recipes[100]['seconds']=100000
        result=self.run_plan(quantity=50,_granularity=4);self.assertTrue(result['complete'])
        self.assertEqual(sum(j['runs'] for j in result['jobs']),50);self.assertEqual(len(result['jobs']),2)
        self.assertTrue(all(j['seconds']<=30*86400 for j in result['jobs']))

    def test_minimum_duration_makes_longer_batches_without_padding_or_extra_output(self):
        self.catalog.recipes[100].update(seconds=4500,copy_limit=13)  # One hour per run; at most 13 runs/job
        self.context['blueprints']=[bp(1)]
        result=self.run_plan(quantity=25,min_job_hours=12)
        self.assertTrue(result['complete']);self.assertEqual(sum(j['runs'] for j in result['jobs']),25)
        self.assertTrue(all(j['seconds']>=12*3600 for j in result['jobs']))
        self.assertEqual(result['jobs'][0]['start'],NOW)
        self.assertEqual(result['jobs'][1]['start'],result['jobs'][0]['end'])
        self.assertNotIn('available_at',result['jobs'][0])
        self.assertEqual(result['seconds'],25*3600);self.assertEqual(result['short_jobs'],0)

    def test_minimum_can_raise_ordinary_run_split_and_zero_restores_it(self):
        self.catalog.recipes[100]['seconds']=4500
        self.context['blueprints']=[bp(1)];self.context['parameters']={100:{'job_runs':2}}
        result=self.run_plan(quantity=24,min_job_hours=12)
        self.assertTrue(all(j['runs']>=12 for j in result['jobs']));self.assertEqual(result['runs'],24)
        legacy=self.run_plan(quantity=24,min_job_hours=0)
        self.assertTrue(all(j['runs']<=2 for j in legacy['jobs']))

    def test_unavoidable_short_job_does_not_overproduce_or_add_idle_time(self):
        self.catalog.recipes[100]['seconds']=4500;self.context['blueprints']=[bp(1,runs=7)]
        result=self.run_plan(quantity=7,min_job_hours=12)
        self.assertTrue(result['complete']);self.assertEqual(result['runs'],7)
        self.assertEqual(len(result['jobs']),1);self.assertEqual(result['jobs'][0]['seconds'],7*3600)
        self.assertEqual(result['finish'],NOW+7*3600);self.assertEqual(result['short_jobs'],1)
        self.assertTrue(result['jobs'][0]['below_minimum'])

    def test_minimum_keeps_bpc_boundaries_and_material_dependencies(self):
        self.recipe(100,{130:1});self.recipe(130,{200:1},activity='reaction')
        self.catalog.recipes[100]['seconds']=4500;self.catalog.recipes[130]['seconds']=4500
        self.context['blueprints']=[bp(1,runs=10),bp(2,runs=10),bp(3,product=130)]
        result=self.run_plan(quantity=20,min_job_hours=12);self.assertTrue(result['complete'])
        jobs={j['id']:j for j in result['jobs']};bp_runs={}
        for j in result['jobs']:
            bp_runs[j['blueprint_item_id']]=bp_runs.get(j['blueprint_item_id'],0)+j['runs']
            for d in j['dependencies']:self.assertGreaterEqual(j['start'],jobs[d['job_id']]['end'])
        self.assertLessEqual(bp_runs.get(1,0),10);self.assertLessEqual(bp_runs.get(2,0),10)
        self.assertTrue(any(j['below_minimum'] for j in result['jobs'] if j['product_id']==100))

    def test_minimum_option_validation_and_default(self):
        from muhely.scheduler import minimum_hours
        self.assertEqual(minimum_hours({}),12);self.assertEqual(minimum_hours({'min_job_hours':1.5}),1.5)
        for value in [True,False,'12',None,-1,721,float('nan'),float('inf')]:
            with self.subTest(value=value),self.assertRaises(PlanningError):self.run_plan(min_job_hours=value)
