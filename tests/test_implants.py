from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import tempfile,threading,unittest
from muhely import implants,notifications
from muhely.store import Store
from muhely.esi import EsiError,IMPLANT_SCOPES
from muhely.planner import PlanningError

NOW=1800000000

class ImplantTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.store=Store(Path(tmp.name));self.store.add_character(11,'Pilot');self.store.add_character(22,'Other')
        self.now=NOW;self.location={'solar_system_id':30000001,'station_id':60000001};self.ids=[10,20];self.calls=[];self.failure=None;self.headers={}
        def request(url,**kwargs):
            self.calls.append(url)
            if self.failure:raise self.failure
            return (self.ids if url.endswith('/implants/') else self.location),self.headers
        self.eve=SimpleNamespace(http=SimpleNamespace(request=request),granted_scopes=lambda:{11:IMPLANT_SCOPES},token=Mock(return_value='not-a-real-token'))
        self.quotes={'10':{'sell':'600000000','buy':'1','checked':NOW},'20':{'sell':'500000000','buy':'2','checked':NOW}}
        self.market=SimpleNamespace(start=Mock(),snapshot=lambda ids:{'quotes':self.quotes})
        self.watch=implants.ImplantWatch(self.store,SimpleNamespace(),self.eve,self.market,clock=lambda:self.now);self.stop=threading.Event()
    def enable(self,**kwargs):
        implants.save_preferences(self.store,{'characters':[{'id':11,'enabled':True,'threshold':'1000000000',**kwargs}]})
    def tick(self,delta=0):self.now+=delta;self.watch.tick(self.stop)
    def undock(self,delta=5):self.location={'solar_system_id':30000001};self.tick(delta)
    def events(self):return implants.events(self.store,self.now)
    def test_disabled_characters_make_no_requests(self):
        self.tick();self.assertEqual(self.calls,[]);self.eve.token.assert_not_called()
    def test_transition_above_limit_prices_only_active_implants_at_sell_once(self):
        self.enable();self.tick();self.assertEqual(self.events(),[]);self.undock()
        first=self.events();self.assertEqual(len(first),1);self.assertEqual(Decimal(first[0]['value']),1100000000)
        self.assertEqual(first[0]['character_id'],11);self.assertTrue(first[0]['sound']);self.assertFalse(first[0]['partial'])
        self.tick(5);self.tick(5);self.assertEqual(len(self.events()),1)
        self.location={'solar_system_id':30000001,'structure_id':1000000000001};self.tick(5);self.undock()
        self.assertEqual(len(self.events()),2);self.assertNotEqual(self.events()[0]['id'],self.events()[1]['id'])
    def test_below_or_equal_threshold_and_empty_clone_do_not_alert(self):
        for ids,threshold in [([10,20],'1100000000'),([10,20],'2000000000'),([],'0')]:
            self.ids=ids;self.enable(threshold=threshold);self.tick(125);self.undock();self.assertEqual(self.events(),[])
            self.location={'solar_system_id':30000001,'station_id':60000001}
    def test_initial_space_and_restart_never_invent_an_undock(self):
        self.enable();self.location={'solar_system_id':30000001};self.tick();self.assertEqual(self.events(),[])
        self.watch=implants.ImplantWatch(self.store,SimpleNamespace(),self.eve,self.market,clock=lambda:self.now);self.tick(5);self.assertEqual(self.events(),[])
    def test_missing_scope_blocks_polling_and_is_visible(self):
        self.enable();self.eve.granted_scopes=lambda:{};self.tick();self.assertEqual(self.calls,[])
        row=next(c for c in self.watch.dashboard()['characters'] if c['id']==11);self.assertFalse(row['authorized']);self.assertIn('engedély',row['error'])
    def test_five_second_location_and_120_second_implant_cache(self):
        self.enable();self.tick();self.tick(1);self.tick(4);self.tick(5)
        self.assertEqual(sum(u.endswith('/location/') for u in self.calls),3);self.assertEqual(sum(u.endswith('/implants/') for u in self.calls),1)
        self.tick(110);self.assertEqual(sum(u.endswith('/implants/') for u in self.calls),2)
    def test_failed_or_stale_location_is_not_an_undock(self):
        self.enable();self.tick();self.failure=EsiError('offline');self.undock();self.assertEqual(self.events(),[])
        self.failure=None;self.tick(31);self.assertEqual(self.events(),[])
        self.location={'solar_system_id':30000001,'station_id':60000001};self.tick(5)
        self.headers={'age':'120'};self.undock();self.assertEqual(self.events(),[])
    def test_bad_location_and_stale_implants_are_not_priced_as_current(self):
        self.enable();self.tick();self.location={};self.tick(5);self.assertEqual(self.events(),[])
        self.location={'solar_system_id':30000001,'station_id':60000001};self.headers={'age':'240'};self.tick(125)
        self.assertEqual(self.events(),[]);self.assertTrue(next(c for c in self.watch.dashboard()['characters'] if c['id']==11)['error'])
    def test_prices_can_arrive_after_undock_without_repeating_event(self):
        self.enable();quotes=self.quotes;self.quotes={};self.tick();self.undock();self.assertEqual(self.events(),[])
        self.quotes=quotes;self.tick(5);self.assertEqual(len(self.events()),1)
    def test_partial_prices_only_alert_when_known_subtotal_already_exceeds_limit(self):
        self.enable(threshold='100');self.quotes.pop('20');self.tick();self.undock()
        self.assertEqual(len(self.events()),1);self.assertTrue(self.events()[0]['partial']);self.assertEqual(self.events()[0]['value'],'600000000')
    def test_changing_settings_does_not_alert_on_a_previous_space_state(self):
        self.enable();self.tick();self.enable(threshold='10');self.undock();self.assertEqual(self.events(),[])
    def test_events_have_persistent_once_only_delivery_and_expire(self):
        self.enable();self.tick();self.undock();notifications.save_preferences(self.store,{'os_enabled':True})
        data={'items':self.events(),'observed_domains':['implants:11']};first=notifications.claim(self.store,data,self.now)
        self.assertEqual(len(first),1);notifications.acknowledge(self.store,[first[0]['receipt']]);self.assertEqual(notifications.claim(self.store,data,self.now+1),[])
        notifications.claim(self.store,{'items':[],'observed_domains':['implants:11']},self.now+2)
        self.assertEqual(notifications.claim(self.store,data,self.now+3),[])
        self.now+=301;self.assertEqual(self.events(),[])
    def test_stop_prevents_network_and_invalid_preferences_are_atomic(self):
        self.enable();self.stop.set();self.tick();self.assertEqual(self.calls,[])
        for row in [{'id':99,'enabled':True,'threshold':'10'},{'id':11,'enabled':True,'threshold':'NaN'},{'id':11,'enabled':1,'threshold':'0'},{'id':11,'enabled':True,'threshold':'-1'}]:
            with self.assertRaises(PlanningError):implants.save_preferences(self.store,{'characters':[row]})
        self.assertEqual(implants.preferences(self.store)[11]['threshold'],'1000000000')

if __name__=='__main__':unittest.main()
