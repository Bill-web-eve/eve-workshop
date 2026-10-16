from copy import deepcopy
import unittest
from unittest.mock import patch
from test_pi import record,catalog,pin,content,route,link,iso,NOW
from muhely.pi import colony_view

class ForecastTests(unittest.TestCase):
    def projection(self,r=None,now=NOW,hours=24,c=None):
        return colony_view(r or record(80),c or catalog(),now,hours)['projection']

    def test_phase_already_paid_inputs_and_absolute_deadline(self):
        p=self.projection();f=p['factories'][0]
        # Running cycle has already paid its inputs; 80 funds two MORE cycles.
        self.assertEqual(f['stock_stop'],NOW+3*3600-10)
        self.assertEqual(f['products_next_period'][0]['quantity'],15)
        self.assertEqual(f['current_cycle_end'],NOW+3590)

    def test_old_snapshot_consumes_elapsed_time_not_http_check_time(self):
        r=record(80);before=deepcopy(r)
        a=self.projection(r,now=NOW+4000,hours=2)
        r['layout_checked_at']=NOW+4000
        b=self.projection(r,now=NOW+4600,hours=2)
        self.assertEqual(a['first_stop'],b['first_stop'])
        self.assertEqual(a['seconds_left']-b['seconds_left'],600)
        self.assertEqual(a['factories'][0]['completed_cycles'],1)
        self.assertEqual(a['factories'][0]['products_next_period'][0]['quantity'],10)
        self.assertEqual(r['layout'],before['layout'])
        self.assertEqual({m['id']:m['quantity'] for m in a['materials_now']},{1:40,2:40,3:5})

    def test_expired_stock_stays_expired_after_refresh_and_counts_no_future_output(self):
        r=record(40)
        p=self.projection(r,now=NOW+10000)
        self.assertEqual(p['seconds_left'],0)
        self.assertFalse(p['factories'][0]['running_now'])
        self.assertFalse(p['factories'][0]['products_next_period'])
        self.assertEqual(p['factories'][0]['completed_cycles'],2)
        self.assertEqual(p['first_stop'],NOW+7190)

    def test_missing_cycle_start_is_explicit_assumption(self):
        r=record(40);r['layout']['pins'][1].pop('last_cycle_start')
        p=self.projection(r)
        self.assertIn('assumed_restart',p['warnings'])
        self.assertEqual(p['first_stop'],NOW+3600)
        self.assertEqual(p['factories'][0]['products_next_period'][0]['quantity'],5)

    def test_intermediate_factory_products_fund_downstream_once(self):
        c=catalog();c.pi_types[4]={'volume':1}
        c.pi_schematics[67]=dict(name='Final',cycle_time=3600,pins=[101],inputs={3:5},outputs={4:1})
        r=record(40);r['layout']['pins'][1].pop('last_cycle_start')
        r['layout']['pins'].append(pin(3,101,schematic_id=67));r['planet']['num_pins']=3
        r['layout']['links'].append(link(1,3));r['layout']['routes'] += [route(4,1,3,3,5),route(5,3,1,4,1)]
        p=self.projection(r,c=c);a,b=p['factories']
        self.assertEqual(a['stock_stop'],NOW+3600)
        self.assertEqual(b['stock_stop'],NOW+7200)
        self.assertEqual(b['products_next_period'],[{'id':4,'name':'4','quantity':1}])

    def test_shared_stock_is_never_spent_twice(self):
        r=record(40);r['layout']['pins'][1].pop('last_cycle_start')
        r['layout']['pins'].append(pin(3,101,schematic_id=66));r['planet']['num_pins']=3
        r['layout']['links'].append(link(1,3));r['layout']['routes'] += [route(4,1,3,1),route(5,1,3,2),route(6,3,1,3,5)]
        p=self.projection(r)
        self.assertIn('shared_priority',p['warnings'])
        self.assertEqual(sum(m['quantity'] for f in p['factories'] for m in f['products_next_period']),5)

    def test_unreachable_stock_and_limited_routes_cannot_fund_a_cycle(self):
        r=record(80);r['layout']['pins'][1].pop('last_cycle_start')
        r['layout']['routes'][0]['quantity']=20
        p=self.projection(r)
        self.assertFalse(p['factories'][0]['running_now']);self.assertEqual(p['first_stop'],NOW)
        self.assertFalse(p['factories'][0]['products_next_period'])

    def test_bad_layout_or_future_times_disable_projection(self):
        r=record();r['planet']['num_pins']=99
        self.assertFalse(self.projection(r)['available'])
        r=record();r['layout']['pins'][1]['last_cycle_start']=iso(NOW+10)
        self.assertFalse(self.projection(r)['available'])
        r=record();r['planet']['last_update']=iso(NOW+10)
        self.assertFalse(self.projection(r)['available'])

    def test_extraction_deadline_advances_but_future_mining_not_credited_as_stock(self):
        r=record(0);r['layout']['pins'].append(pin(3,102,install_time=iso(NOW-100),expiry_time=iso(NOW+800),extractor_details=dict(heads=[{}],cycle_time=100,product_type_id=1,qty_per_cycle=100)))
        r['layout']['links'].append(link(1,3));r['layout']['routes'].append(route(4,3,1,1,100));r['planet']['num_pins']=3
        a=colony_view(r,catalog(),NOW,24);b=colony_view(r,catalog(),NOW+850,24)
        self.assertEqual(a['extractors'][0]['program_duration'],900)
        self.assertEqual(a['extractors'][0]['cycles_remaining'],8)
        self.assertEqual(b['extractors'][0]['cycles_remaining'],0)
        self.assertFalse(b['extractors'][0]['program_active'])
        self.assertEqual(a['factories'][0]['extractor_sources'],[3])
        self.assertEqual(a['projection']['materials_now'],[])

    def test_capacity_prevents_phantom_intermediate_inventory(self):
        c=catalog();c.pi_types[100]['capacity']=0
        p=self.projection(c=c)
        self.assertIn('output_capacity',p['warnings'])
        self.assertNotIn(3,[m['id'] for m in self.projection(now=NOW+4000,c=c)['materials_now']])

    def test_event_limit_is_explicit_and_never_claims_completed_forecast(self):
        with patch('muhely.pi_forecast.MAX_EVENTS',1):p=self.projection(record(10000))
        self.assertFalse(p['available']);self.assertIn('simulation_limit',p['warnings'])

    def test_newer_real_snapshot_reanchors_but_unchanged_http_timestamp_does_not(self):
        r=record(40);a=self.projection(r)
        r['planet']['last_update']=iso(NOW+10000);r['layout']['pins'][1].pop('last_cycle_start')
        b=self.projection(r,now=NOW+10000)
        self.assertEqual(b['first_stop'],NOW+13600);self.assertNotEqual(a['first_stop'],b['first_stop'])

    def test_shared_routes_reassign_flexible_sources_without_false_starvation(self):
        r=record(40);r['layout']['pins'][1].pop('last_cycle_start')
        r['layout']['pins'] += [pin(3,101,schematic_id=66),pin(4,100,contents=[content(1,40),content(2,40)])]
        r['planet']['num_pins']=4
        r['layout']['links'] += [link(1,3),link(4,2)]
        r['layout']['routes'] += [route(4,1,3,1),route(5,1,3,2),route(6,3,1,3,5),route(7,4,2,1),route(8,4,2,2)]
        p=self.projection(r)
        self.assertNotIn('shared_priority',p['warnings'])
        self.assertTrue(all(f['running_now'] for f in p['factories']))
        self.assertEqual(sum(m['quantity'] for f in p['factories'] for m in f['products_next_period']),10)

    def test_extractor_dependency_follows_material_types_not_just_shared_storage(self):
        r=record(80);r['layout']['pins'].append(pin(3,102,install_time=iso(NOW-100),expiry_time=iso(NOW+800),extractor_details=dict(heads=[{}],cycle_time=100,product_type_id=3,qty_per_cycle=100)))
        r['layout']['links'].append(link(1,3));r['layout']['routes'].append(route(4,3,1,3,100));r['planet']['num_pins']=3
        self.assertEqual(colony_view(r,catalog(),NOW,24)['factories'][0]['extractor_sources'],[])
        r['layout']['routes'][-1]['content_type_id']=1;r['layout']['pins'][-1]['extractor_details']['product_type_id']=1
        self.assertEqual(colony_view(r,catalog(),NOW,24)['factories'][0]['extractor_sources'],[3])

    def mining_record(self,cycles=3):
        r=record(0);r['layout']['pins'][0]['contents']=[content(2,200)]
        r['layout']['pins'][1].pop('last_cycle_start')
        r['layout']['pins'].append(pin(3,102,install_time=iso(NOW),expiry_time=iso(NOW+cycles*3600),extractor_details=dict(heads=[{}],cycle_time=3600,product_type_id=1,qty_per_cycle=100)))
        r['layout']['links'].append(link(1,3));r['layout']['routes'].append(route(4,3,1,1,40));r['planet']['num_pins']=3
        return r

    def test_ccp_curve_uses_cycle_duration_and_variable_yield(self):
        from muhely.pi_forecast import extraction_yield
        self.assertEqual([extraction_yield(6965,1800,i) for i in [0,1,2,94]],[24261,20481,16053,5389])
        self.assertEqual(extraction_yield(0,900,0),0)
        self.assertGreater(extraction_yield(100,3600,0),40)

    def test_modeled_extraction_feeds_factories_until_program_end(self):
        p=self.projection(self.mining_record())
        self.assertIn('modeled_yield',p['warnings'])
        self.assertEqual(p['stock_only_first_stop'],NOW)
        self.assertEqual(p['first_stop'],NOW+4*3600)
        self.assertEqual(p['factories'][0]['products_next_period'][0]['quantity'],15)
        self.assertFalse(p['factories'][0]['running_now'])
        self.assertEqual(p['extraction_since_snapshot'],[])
        self.assertGreater(p['extraction_next_period'][0]['quantity'],120)

    def test_expired_program_still_reconstructs_past_production_without_new_extraction(self):
        r=self.mining_record(2);p=self.projection(r,now=NOW+8000,hours=1)
        self.assertEqual(p['first_stop'],NOW+10800)
        self.assertEqual(p['factories'][0]['completed_cycles'],1)
        self.assertEqual(p['factories'][0]['products_next_period'][0]['quantity'],5)
        self.assertEqual(p['extraction_next_period'],[])
        self.assertTrue(p['factories'][0]['running_now'])
        later=self.projection(r,now=NOW+20000)
        self.assertEqual(later['first_stop'],p['first_stop'])
        self.assertFalse(later['factories'][0]['running_now'])
        self.assertEqual(later['factories'][0]['products_next_period'],[])

    def test_cached_state_does_not_recredit_extraction_before_baseline(self):
        r=self.mining_record();r['planet']['last_update']=iso(NOW+4000)
        p=self.projection(r,now=NOW+4000)
        self.assertEqual(p['extraction_since_snapshot'],[])
        # Only the two remaining extractor cycles can fund new factory output.
        self.assertEqual(p['factories'][0]['products_next_period'][0]['quantity'],10)
        self.assertEqual(p['first_stop'],NOW+14400)

    def test_shortened_age_limit_never_promises_unexamined_thirty_day_coverage(self):
        with patch('muhely.pi_forecast.MAX_SECONDS',3600):p=self.projection(record(10000))
        self.assertFalse(p['available']);self.assertIn('simulation_limit',p['warnings'])

    def test_fully_exhausted_old_snapshot_remains_calculable_after_age_limit(self):
        p=self.projection(record(40),now=NOW+100*86400)
        self.assertTrue(p['available']);self.assertEqual(p['seconds_left'],0)
        self.assertEqual(p['first_stop'],NOW+7190)
