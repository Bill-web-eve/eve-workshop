import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from muhely.catalog import Catalog
from muhely.esi import EsiError
from muhely.moons import dashboard,validate_moon,validate_preferences,composition_state,system_search,system_info
from muhely.planner import PlanningError
from muhely.store import Store

ROOT=Path(__file__).resolve().parents[1]
class MoonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=Catalog(ROOT/'data/catalog.sqlite3')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=Store(self.tmp.name)
        self.sid=next(s['id'] for s in self.c.moon_systems.values() if s['name']=='RP2-OQ')
        self.mid=next(m['id'] for m in self.c.moon_locations(self.sid) if m['name']=='RP2-OQ VI - Moon 7')
    def value(self,**kw):return dict(system_id=self.sid,moon_id=self.mid,structure='Athanor',ores=[{'id':45490,'percent':100}],**kw)
    def save(self,**kw):
        v=validate_moon({**self.value(),**kw},self.c,self.s.moon_records());self.s.save_moon(v);return v
    def report(self):return dashboard(self.s,self.c)
    def test_public_catalog(self):
        self.assertEqual((len(self.c.moon_ores),len(self.c.moon_crystals)),(20,30))
        self.assertGreater(len(self.c.moon_systems),8000)
        self.assertEqual((self.c.moon_ores[45490]['portion'],self.c.moon_ores[45490]['volume']),(100,10))
        self.assertEqual(self.c.moon_rules['metenox']['reagentsConsumedPerCycle'],200)
        self.assertEqual(self.c.moon_rules['tatara_bonus'],5.5)
        self.assertEqual(system_search(self.c,'rp2')[0]['name'],'RP2-OQ');self.assertFalse(system_search(self.c,''))
    def test_empty_profile_and_implant(self):
        r=self.report();self.assertEqual(r['summary']['count'],0);self.assertFalse(r['totals']['all'])
        self.assertEqual(r['settings']['implant'],4);self.assertAlmostEqual(r['refining_yield'],.90628105568)
    def test_athanor_full_portions_and_rounding(self):
        self.save();r=self.report();m=r['moons'][0];o={v['id']:v['quantity'] for v in m['outputs']}
        self.assertEqual(m['ores'][0]['volume'],21_600_000)
        self.assertEqual(o[16634],1_272_418);self.assertEqual(o[35],156605366)
        self.assertEqual(r['totals']['all'],r['totals']['Athanor']);self.assertFalse(r['totals']['Metenox'])
        self.assertEqual((m['fuel'],m['gas'],m['online_fuel']),(3600,0,0))
    def test_metenox_current_rates_ignore_implant_and_recovery(self):
        self.save(structure='Metenox');r=self.report();m=r['moons'][0]
        self.assertEqual(next(v['quantity'] for v in m['outputs'] if v['id']==16634),780*720)
        self.assertEqual((m['fuel'],m['gas'],m['online_fuel']),(3600,144000,0));self.assertFalse(m['crystals'])
        self.assertNotIn(35,[o['id'] for o in m['outputs']]);self.assertNotIn(36,[o['id'] for o in m['outputs']])
        self.s.save_moon_preferences({'implant':0,'mining_recovery':0})
        self.assertEqual(m['outputs'],self.report()['moons'][0]['outputs'])
    def test_partial_keeps_raw_shares_excess_excluded_but_fueled(self):
        v=self.save(ores=[{'id':45490,'percent':34.18},{'id':45492,'percent':19.14},{'id':45500,'percent':26.68}])
        m=self.report()['moons'][0];self.assertEqual((m['percent_total'],m['status']),(80,'partial'))
        self.assertEqual(sum(o['volume'] for o in m['ores']),17_280_000)
        v['ores']=[{'id':45490,'percent':70},{'id':45492,'percent':57.15}];self.s.save_moon(v)
        r=self.report();m=r['moons'][0];self.assertEqual(m['status'],'invalid');self.assertFalse(m['included'])
        self.assertFalse(r['totals']['all']);self.assertTrue(all(v['quantity']==0 for v in m['outputs']))
        self.assertTrue(all(c['share'] is None for c in m['crystals']));self.assertEqual(r['consumption']['all']['fuel'],3600)
    def test_rounding_tolerance(self):
        for total,state in [(100.01,'ok'),(100.03,'invalid'),(99,'partial')]:self.assertEqual(composition_state([{'percent':total}])[1],state)
    def test_crystal_classes_and_known_volume_share(self):
        self.save(ores=[{'id':45490,'percent':20},{'id':45492,'percent':20},{'id':45496,'percent':30},{'id':45500,'percent':10}])
        r=self.report();c={v['rarity']:v for v in r['moons'][0]['crystals']}
        self.assertEqual({k:v['share'] for k,v in c.items()},{4:50,8:37.5,16:12.5})
        self.assertEqual(c[4]['name'],'Ubiquitous Moon Mining Crystal Type A II')
        self.assertEqual(c[4]['ores'],['Zeolites','Bitumens']);self.assertAlmostEqual(sum(x['share'] for x in r['crystals']),100)
        self.s.save_moon_preferences({'crystal_variant':'B I'})
        self.assertTrue(all('Type B I' in c['name'] for c in self.report()['crystals']))
    def test_stopped_onlining_and_combined_consumption(self):
        v=self.save(enabled=False,online_starts=1);m=self.report()['moons'][0]
        self.assertFalse(m['included']);self.assertEqual((m['fuel'],m['online_fuel']),(0,360))
        v['enabled']=True;self.s.save_moon(v);self.mid=self.c.moon_locations(self.sid)[0]['id']
        self.save(structure='Metenox',online_starts=2);c=self.report()['consumption']['all']
        self.assertEqual((c['fuel'],c['online_fuel'],c['gas'],c['count']),(7200,2360,144000,2))
    def test_recovery(self):
        self.save();self.s.save_moon_preferences(validate_preferences({'mining_recovery':50}))
        self.assertEqual(next(x['quantity'] for x in self.report()['moons'][0]['outputs'] if x['id']==16634),636209)
    def test_validation_duplicate_restart_update_remove(self):
        v=self.save()
        for patch in [{'system_id':1},{'moon_id':1},{'ores':[]},{'ores':[{'id':45490,'percent':20}]*2},
            {'ores':[{'id':45490,'percent':float('nan')}]},{'ores':[{'id':45490,'percent':101}]},
            {'structure':'Tatara'},{'id':'missing'},{'enabled':'yes'},{'online_starts':-1}]:
            with self.subTest(patch=patch),self.assertRaises(PlanningError):validate_moon({**self.value(),**patch},self.c,self.s.moon_records())
        with self.assertRaises(PlanningError):self.save()
        self.assertEqual(len(Store(self.tmp.name).moon_records()),1)
        v['ores'][0]['percent']=75;self.s.save_moon(validate_moon(v,self.c,self.s.moon_records()))
        self.assertEqual(self.s.moon_records()[0]['ores'][0]['percent'],75)
        self.s.remove_moon(v['id']);self.assertFalse(self.s.moon_records())
    def test_preferences(self):
        for value in [{'implant':5},{'implant':True},{'mining_recovery':101},{'crystal_variant':'D II'},{'client_secret':'x'}]:
            with self.subTest(value=value),self.assertRaises(PlanningError):validate_preferences(value)
    def test_esi_cache_overrides_sde_and_304(self):
        http=Mock();http.request.side_effect=[({'name':'RP2-OQ','constellation_id':123,'security_status':-.5},{'ETag':'sys'}),({'name':'ESI constellation'},{'ETag':'const'})]
        info=system_info(self.s,self.c,http,self.sid);self.assertEqual(info['source'],'esi');self.assertEqual(info['system']['constellation'],'ESI constellation')
        self.assertEqual(http.request.call_count,2);self.assertNotIn('token',http.request.call_args.kwargs)
        self.assertEqual(system_info(self.s,self.c,http,self.sid)['source'],'esi');self.assertEqual(http.request.call_count,2)
        http.request.side_effect=[(None,{}),(None,{})]
        self.assertEqual(system_info(self.s,self.c,http,self.sid,True)['source'],'esi')
        self.assertEqual(http.request.call_args.kwargs['headers'],{'If-None-Match':'const'})
        self.save();self.assertEqual(self.report()['moons'][0]['system']['constellation'],'ESI constellation')
    def test_offline_fallback(self):
        http=Mock();http.request.side_effect=EsiError('offline')
        info=system_info(self.s,self.c,http,self.sid);self.assertEqual(info['source'],'sde');self.assertTrue(info['moons'])
        self.s.save_universe_cache('systems',self.sid,{'name':'RP2-OQ','constellation_id':123},0,'x')
        self.s.save_universe_cache('constellations',123,{'name':'Previous constellation'},0,'y')
        info=system_info(self.s,self.c,http,self.sid);self.assertEqual(info['source'],'stale');self.assertEqual(info['system']['constellation'],'Previous constellation')

import test_server as server_base
class MoonApiTests(unittest.TestCase):
    setUp=server_base.ServerTests.setUp
    close=server_base.ServerTests.close
    request=server_base.ServerTests.request
    def test_http_moon_crud_and_csrf(self):
        self.assertEqual(self.request('/moons.js')[0],200)
        code,data,_=self.request('/api/moons');self.assertEqual(code,200);self.assertFalse(data['moons'])
        _,systems,_=self.request('/api/moons/systems?q=rp2');sid=systems[0]['id']
        self.app.eve.http.request=Mock(side_effect=EsiError('offline'))
        code,data,_=self.request('/api/moons/system?id='+str(sid));self.assertEqual(code,200);self.assertEqual(data['source'],'sde')
        body={'system_id':sid,'moon_id':data['moons'][0]['id'],'structure':'Athanor','ores':[{'id':45490,'percent':75}]}
        self.assertEqual(self.request('/api/moons/save',body,**{'X-CSRF-Token':'wrong'})[0],403)
        code,result,_=self.request('/api/moons/save',body);self.assertEqual(code,200);mid=result['id']
        self.assertEqual(self.request('/api/moons/save',body)[0],400)
        self.assertEqual(len(self.request('/api/moons')[1]['moons']),1)
        self.assertEqual(self.request('/api/moons/settings',{'implant':2})[0],200)
        self.assertEqual(self.request('/api/moons')[1]['settings']['implant'],2)
        self.assertEqual(self.request('/api/moons/remove',{'id':mid})[0],200)
        self.assertFalse(self.request('/api/moons')[1]['moons'])
        self.assertFalse(self.app.store.characters());self.assertFalse(self.app.store.plans())

class MoonCatalogueFallbackTests(unittest.TestCase):
    def test_old_profile_catalog_uses_public_moon_fallback_without_overwriting(self):
        import shutil,sqlite3
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.sqlite3';shutil.copy2(ROOT/'data/catalog.sqlite3',path)
            with sqlite3.connect(path) as db:
                for table in ['moon_systems','moon_locations','moon_ores','moon_crystals']:db.execute('DROP TABLE '+table)
                db.execute("DELETE FROM meta WHERE key='moonRules'")
            c=Catalog(path,pi_fallback=ROOT/'data/catalog.sqlite3')
            self.assertEqual(len(c.moon_ores),20);self.assertTrue(c.moon_locations(30000001))
            with sqlite3.connect(path) as db:self.assertFalse(db.execute("SELECT name FROM sqlite_master WHERE name='moon_ores'").fetchone())
