from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock

from muhely.catalog import Catalog
from muhely.esi import EsiError,EveConnection,PlanetScopeError,PI_SCOPES
from muhely.pi import colony_view,dashboard,maxflow,validate_layout,validate_planets
from muhely.store import Store

NOW=1800000000
ROOT=Path(__file__).resolve().parents[1]
def iso(n):return datetime.fromtimestamp(n,timezone.utc).isoformat()
def planet(pid=1):return dict(planet_id=pid,solar_system_id=10,owner_id=123,planet_type='barren',num_pins=2,upgrade_level=4,last_update=iso(NOW))
def pin(pid,tid,**kw):return dict(pin_id=pid,type_id=tid,latitude=0,longitude=0,**kw)
def content(tid,amount):return dict(type_id=tid,amount=amount)
def route(i,a,b,tid,quantity=40,**kw):return dict(route_id=i,source_pin_id=a,destination_pin_id=b,content_type_id=tid,quantity=quantity,**kw)
def link(a,b):return dict(source_pin_id=a,destination_pin_id=b,link_level=0)
def catalog():
    return SimpleNamespace(name=lambda i:{1:'Water',2:'Electrolytes',3:'Coolant'}.get(i,str(i)),types={},
        pi_types={100:{'group_id':1029,'capacity':1000},101:{'group_id':1028},102:{'group_id':1063},1:{'volume':1},2:{'volume':1},3:{'volume':1}},
        pi_schematics={66:dict(name='Coolant',cycle_time=3600,pins=[101],inputs={1:40,2:40},outputs={3:5})},
        pi_planets={1:{'name':'Test I'}},pi_systems={10:'Test'},pi_meta={})
def record(amount=1000):
    return {'planet':planet(),'layout_checked_at':NOW,'layout':{'pins':[
        pin(1,100,contents=[content(1,amount),content(2,amount)]),
        pin(2,101,schematic_id=66,last_cycle_start=iso(NOW-10))],
        'links':[link(1,2)],'routes':[route(1,1,2,1),route(2,1,2,2),route(3,2,1,3,5)]}}
def view(r=None,hours=24):return colony_view(r or record(),catalog(),NOW,hours)
def snap(data,fetched=NOW):return dict(data=data,fetched=fetched,expires=NOW+600,etag=None)

class PlanetTests(unittest.TestCase):
    def test_actual_stock_covers_full_cycles_and_different_horizons(self):
        r=view(record(10000));self.assertTrue(r['next_enough']);self.assertTrue(r['period_enough']);self.assertEqual(r['stock_coverage_seconds'],250*3600)
        for hours in [1,6,24,72]:
            p=view(record(100),hours);self.assertEqual(p['period_materials'][0]['required'],40*hours)
            self.assertEqual(p['period_materials'][0]['missing'],max(0,40*hours-100))
        self.assertEqual(view(record(100))['stock_coverage_seconds'],7200)

    def test_missing_route_or_physical_link_does_not_use_stock(self):
        for change in ['routes','links']:
            r=record();r['layout'][change]=[];p=view(r)
            self.assertFalse(p['next_enough']);self.assertEqual(p['next_materials'][0]['on_planet'],1000)
            self.assertEqual(p['next_materials'][0]['usable'],0)
        r=record();r['layout']['routes'][0]['quantity']=20
        self.assertEqual(view(r)['next_materials'][0]['missing'],20)
        r['layout']['routes'][0].update(source_pin_id=2,destination_pin_id=1)
        self.assertEqual(view(r)['next_materials'][0]['usable'],0)

    def test_valid_waypoints_and_invalid_link_are_distinguished(self):
        r=record();r['layout']['pins'].append(pin(4,100));r['planet']['num_pins']=3
        r['layout']['links']=[link(1,4),link(4,2)]
        for x in r['layout']['routes']:x['waypoints']=[x['source_pin_id'],4,x['destination_pin_id']]
        self.assertTrue(view(r)['next_enough']);self.assertEqual(view(r)['bad_routes'],0)
        r['layout']['links'].pop();self.assertFalse(view(r)['next_enough'])

    def test_common_stock_is_counted_once_and_all_competitors_warn(self):
        r=record(40);r['layout']['pins'].append(pin(3,101,schematic_id=66));r['planet']['num_pins']=3
        r['layout']['links'].append(link(1,3));r['layout']['routes'] += [route(4,1,3,1),route(5,1,3,2),route(6,3,1,3,5)]
        p=view(r);self.assertEqual(p['next_materials'][0]['missing'],40)
        self.assertEqual([f['supply_status'] for f in p['factories']],['shortage','shortage'])
        r['layout']['pins'][1]['contents']=[content(1,40),content(2,40)]
        self.assertTrue(view(r)['next_enough'])
        # Other factories cannot steal an isolated factory's buffer.
        r['layout']['pins'][0]['contents']=[];r['layout']['pins'][1]['contents']=[content(1,80),content(2,80)]
        p=view(r);self.assertEqual(p['next_materials'][0]['missing'],40)
        self.assertEqual([f['supply_status'] for f in p['factories']],['ready','shortage'])

    def test_flow_reassigns_shared_sources_instead_of_greedy_false_shortage(self):
        self.assertEqual(maxflow({1:40,2:40},{3:40,4:40},{(1,3):40,(1,4):40,(2,3):40}),(80,set()))

    def extraction_record(self):
        r=record(0);r['layout']['pins'].append(pin(3,102,install_time=iso(NOW-100),expiry_time=iso(NOW+90000),
            extractor_details=dict(heads=[{'head_id':1}],cycle_time=900,product_type_id=1,qty_per_cycle=100)))
        r['layout']['links'].append(link(1,3));r['layout']['routes'].append(route(4,3,1,1,100));r['planet']['num_pins']=3
        return r

    def test_extraction_timer_is_independent_of_local_factory_shortages(self):
        r=self.extraction_record();p=view(r)
        self.assertEqual(p['monitor_mode'],'extraction');self.assertEqual(p['status'],'ok')
        self.assertEqual(p['extraction']['next_end'],NOW+90000)
        self.assertEqual(p['extraction']['seconds_left'],90000)
        self.assertIsNone(p['projection']);self.assertEqual(p['factories'],[])
        self.assertEqual(p['period_materials'],[])
        # A missing output route cannot alter the program deadline.
        r['layout']['routes']=[];p=view(r)
        self.assertFalse(p['extractors'][0]['active']);self.assertTrue(p['extractors'][0]['program_active'])
        self.assertEqual(p['status'],'ok');self.assertEqual(p['extraction']['next_end'],NOW+90000)

    def test_restart_replaces_expired_timer_without_reusing_old_factory_date(self):
        r=self.extraction_record();e=r['layout']['pins'][-1]
        e['install_time']=iso(NOW-86400);e['expiry_time']=iso(NOW-1)
        self.assertEqual(view(r)['status'],'alert')
        # The planet's last_update can be older than the ECU restart.
        r['planet']['last_update']=iso(NOW-86400)
        e['install_time']=iso(NOW);e['expiry_time']=iso(NOW+7*86400)
        before=deepcopy(r);p=view(r)
        self.assertEqual(p['status'],'ok');self.assertFalse(p['state_old'])
        self.assertEqual(p['extractors'][0]['program_start'],NOW)
        self.assertEqual(p['extraction']['next_end'],NOW+7*86400)
        r['layout_checked_at']=NOW+3600
        later=colony_view(r,catalog(),NOW+3600,24)
        self.assertEqual(later['extraction']['next_end'],p['extraction']['next_end'])
        self.assertEqual(later['extraction']['seconds_left'],p['extraction']['seconds_left']-3600)
        self.assertEqual(r['layout'],before['layout'])

    def test_multiple_extractors_and_exact_expiry_boundary(self):
        r=self.extraction_record();other=deepcopy(r['layout']['pins'][-1]);other['pin_id']=4
        other['expiry_time']=iso(NOW+100);r['layout']['pins'].append(other);r['planet']['num_pins']=4
        p=view(r);self.assertEqual(p['status'],'warning');self.assertEqual(p['extraction']['next_end'],NOW+100)
        p=colony_view(r,catalog(),NOW+100,24)
        self.assertEqual(p['extraction']['expired_count'],1);self.assertEqual(p['extraction']['active_count'],1)
        self.assertEqual(p['extraction']['next_end'],NOW+90000)
        p=colony_view(r,catalog(),NOW+90000,24)
        self.assertEqual(p['status'],'alert');self.assertIsNone(p['extraction']['next_end'])

    def test_factory_planets_use_only_their_own_stock(self):
        poor=record(40);rich=record(10000)
        before=view(poor)
        self.assertEqual(before['monitor_mode'],'factory');self.assertEqual(before['projection']['first_stop'],NOW+7190)
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.add_character(123,'Pilot')
            # Large supplies on a separate planet must not extend the poor planet.
            rich['planet']['planet_id']=2
            store.save_snapshots(123,{'pi':snap({'colonies':[poor,rich,self.extraction_record()]})},domain='pi')
            rows=dashboard(store,catalog(),now=NOW)['colonies']
            poor_row=next(r for r in rows if r['id']==1 and r['monitor_mode']=='factory')
            rich_row=next(r for r in rows if r['id']==2)
            self.assertEqual(poor_row['projection'],before['projection'])
            self.assertGreater(rich_row['projection']['first_stop'],poor_row['projection']['first_stop'])
            self.assertIsNone(next(r for r in rows if r['monitor_mode']=='extraction')['projection'])

    def test_expired_extractors_alert_and_fresh_http_does_not_make_old_factory_current(self):
        r=record(0);r['layout']['pins'][1].pop('last_cycle_start')
        self.assertEqual(view(r)['status'],'alert')
        r['planet']['last_update']=iso(NOW-1801)
        self.assertEqual(view(r)['status'],'unknown');self.assertTrue(view(r)['state_old'])
        r=record();r['layout']['pins'][1]['schematic_id']=999
        self.assertIsNone(view(r)['next_enough']);self.assertEqual(view(r)['status'],'unknown')
        r=record();r['planet']['num_pins']=10;self.assertEqual(view(r)['status'],'unknown')

    def test_storage_volume_and_full_warning(self):
        p=view(record(600));self.assertTrue(p['storages'][0]['full']);self.assertEqual(p['storages'][0]['used'],1200)

    def test_bad_data_rejected_before_it_can_replace_cache(self):
        for data in [dict(record()['layout'],pins=[pin(1,101),pin(1,101)]),
                     dict(record()['layout'],routes=[route(1,1,2,1,float('nan'))])]:
            with self.assertRaises(EsiError):validate_layout(data)
        with self.assertRaises(EsiError):validate_planets([dict(planet(),last_update='bad')])

    def test_all_characters_and_same_planet_separate_and_corruption_marks_whole_character_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.save_settings({'character_ids':[123]})
            for i in [123,456,789]:store.add_character(i,str(i))
            for i in [123,456]:store.save_snapshots(i,{'pi':snap({'colonies':[record()]})},domain='pi')
            store.save_snapshots(789,{'pi':snap({'colonies':[]})},domain='pi')
            p=dashboard(store,catalog(),now=NOW);self.assertEqual(len(p['characters']),3);self.assertEqual(len(p['colonies']),2)
            self.assertEqual({c['character_id'] for c in p['colonies']},{123,456});self.assertEqual(p['characters'][2]['status'],'loaded')
            store.save_snapshots(123,{'pi':snap({'colonies':[record(),{}]})},domain='pi')
            self.assertEqual(next(c for c in dashboard(store,catalog(),now=NOW)['colonies'] if c['character_id']==123)['status'],'unknown')
            store.resource_error(456,'pi','Offline')
            self.assertEqual(next(c for c in dashboard(store,catalog(),now=NOW)['colonies'] if c['character_id']==456)['status'],'unknown')

    def test_official_pi_sde_and_manufacturing_baselines_present(self):
        c=Catalog(ROOT/'data/catalog.sqlite3')
        self.assertEqual(c.pi_schematics[66]['inputs'],{2390:40,3645:40})
        self.assertEqual(c.pi_schematics[66]['outputs'],{9832:5});self.assertGreater(len(c.pi_planets),50000)
        self.assertIn(92822,c.recipes);self.assertIn(22428,c.recipes)

class PlanetSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
        self.store.add_character(123,'Pilot');self.eve=EveConnection(self.store,vault=Mock(),transport=Mock())
        self.eve.token=Mock(return_value='token')

    def test_atomic_failure_preserves_pi_and_industry(self):
        self.store.save_snapshots(123,{'pi':snap({'colonies':[record()]},1)},domain='pi')
        self.store.character_error(123,'Industry error')
        self.eve.pi_resource=Mock(side_effect=[snap([planet()]),EsiError('Offline')])
        self.assertFalse(self.eve.sync_pi()[0]['ok']);self.assertEqual(self.store.snapshot(123,'pi')['fetched'],1)
        self.assertEqual(self.store.characters()[0]['error'],'Industry error')
        self.assertEqual(self.store.resource_status(123,'pi')['error'],'Offline')

    def test_scope_failure_is_separate_and_wrong_owner_rejected(self):
        self.eve.token.side_effect=PlanetScopeError('PI permission required')
        self.assertFalse(self.eve.sync_pi()[0]['ok']);self.assertTrue(self.store.resource_status(123,'pi')['needs_auth'])
        self.assertIsNone(self.store.characters()[0]['error'])
        self.eve.token.side_effect=None;self.eve.pi_resource=Mock(return_value=snap([dict(planet(),owner_id=999)]))
        self.assertFalse(self.eve.sync_pi()[0]['ok']);self.assertIsNone(self.store.snapshot(123,'pi'))

    def test_successful_and_empty_colonies_commit_and_etag_cache_honored(self):
        self.eve.pi_resource=Mock(side_effect=[snap([planet()]),snap(record()['layout'])])
        self.assertTrue(self.eve.sync_pi()[0]['ok']);self.eve.token.assert_called_with(123,required_scopes=PI_SCOPES)
        self.assertEqual(len(self.store.snapshot(123,'pi')['data']['colonies']),1)
        self.eve.pi_resource=Mock(return_value=snap([]));self.assertTrue(self.eve.sync_pi()[0]['ok'])
        self.assertEqual(self.store.snapshot(123,'pi')['data']['colonies'],[])

    def test_304_uses_validated_old_data_with_ten_minute_cache_ceiling(self):
        self.store.save_snapshots(123,{'pi_planets':dict(snap([planet()],1),expires=2,etag='old')},domain='pi')
        self.eve.http.request.return_value=(None,{'Cache-Control':'max-age=3600','ETag':'new'})
        result=self.eve.pi_resource(123,'pi_planets','https://esi.evetech.net/test','token')
        self.assertEqual(result['data'],[planet()]);self.assertEqual(result['expires']-result['fetched'],600)
        self.assertEqual(self.eve.http.request.call_args.kwargs['headers'],{'If-None-Match':'old'})
        self.store.save_snapshots(123,{'pi_planets':result},domain='pi');self.eve.http.reset_mock()
        self.eve.pi_resource(123,'pi_planets','https://esi.evetech.net/test','token');self.eve.http.request.assert_not_called()

if __name__=='__main__':unittest.main()
