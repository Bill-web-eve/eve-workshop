from types import SimpleNamespace
from unittest.mock import patch
import unittest,json
from muhely import intel,intel_kills,notifications,fleet
import test_intel
from test_fleet import kill,BASE

NOW=BASE
CATALOG=SimpleNamespace(name=lambda tid:{590:'Rifter',591:'Slasher'}.get(tid,str(tid)))


class IntelKillTests(unittest.TestCase):
    setUp=test_intel.IntelStoreTests.setUp
    def ingest(self,rows,at=NOW):intel_kills.ingest(self.store,rows,CATALOG,at)
    def alerts(self,at=NOW+11):return intel.collect_alerts(self.store,self.u,at)
    def groups(self,at=NOW,regions=(10,)):return intel_kills.groups(self.store,self.u,intel.preferences(self.store),at,set(regions))
    def test_burst_is_one_alert_after_ten_seconds_with_exact_total_and_ship_counts(self):
        a=kill(1,-30);a['zkb']['totalValue']=0.1;b=kill(2,-20);b['zkb']['totalValue']=0.2
        self.ingest([a,b]);self.assertEqual(self.alerts(NOW+9)['items'],[])
        alerts=self.alerts();self.assertEqual(len(alerts['items']),1)
        a=alerts['items'][0];self.assertEqual(a['kill_count'],2);self.assertEqual(a['cents'],'30');self.assertEqual(a['ships'],[{'type_id':590,'name':'Rifter','count':2}])
        self.assertEqual(a['kind'],'intel_kill');self.assertEqual(a['when'],NOW-20);self.assertEqual(a['overlay_reports'][0]['when'],NOW+10)
        self.assertEqual(a['overlay_reports'][0]['pilots'],[])
    def test_regions_are_independent_of_chat_jump_limit_and_no_duplicate_per_character(self):
        self.store.add_character(12,'Second Pilot')
        intel.save_preferences(self.store,{'manual_locations':{'11':1,'12':1},'jumps':0},self.u)
        self.ingest([kill(1,-1,2,cid=77),kill(2,-1,3,cid=77)])
        alerts=self.alerts()['items'];self.assertEqual(len(alerts),1);self.assertEqual(alerts[0]['system_id'],2);self.assertEqual(alerts[0]['jumps'],1)
        intel.save_preferences(self.store,{'kill_region_ids':[20]},self.u)
        alerts=self.alerts()['items'];self.assertEqual([a['system_id'] for a in alerts],[3])
    def test_different_systems_or_event_times_are_not_combined_and_closed_batch_stays_closed(self):
        self.ingest([kill(1,-1),kill(2,-1,2),kill(3,-122)])
        self.assertEqual(len(self.groups()),3)
        self.ingest([kill(4,-5)],NOW+5);self.assertEqual(sorted(g['count'] for g in self.groups(NOW+5)),[1,1,2])
        self.ingest([kill(5,-1)],NOW+11);self.assertEqual(len(self.groups(NOW+11)),4)
        first=next(g for g in self.groups(NOW+11) if any(k['id']==1 for k in g['kills']));self.assertEqual(first['count'],2)
    def test_replay_and_metadata_updates_keep_identity_and_do_not_resend(self):
        self.ingest([kill(1,-1)]);data=self.alerts();identity=data['items'][0]['id']
        notifications.save_preferences(self.store,{'os_enabled':True})
        claimed=notifications.claim(self.store,data,NOW+11);self.assertEqual(len(claimed),1)
        with patch('muhely.notifications.time.time',return_value=NOW+11):notifications.acknowledge(self.store,[claimed[0]['receipt']])
        updated=kill(1,-1);updated['zkb']['totalValue']=123.45;self.ingest([updated],NOW+40)
        data=self.alerts(NOW+41);self.assertEqual(data['items'][0]['id'],identity);self.assertEqual(data['items'][0]['kill_count'],1);self.assertEqual(data['items'][0]['cents'],'12345')
        self.assertEqual(notifications.claim(self.store,data,NOW+41),[])
        intel.save_preferences(self.store,{'kill_region_ids':[20]},self.u);notifications.claim(self.store,self.alerts(NOW+42),NOW+42)
        intel.save_preferences(self.store,{'kill_region_ids':[10]},self.u);self.assertEqual(notifications.claim(self.store,self.alerts(NOW+43),NOW+43),[])
    def test_kills_remain_on_clear_map_without_becoming_current_hostile_pilots(self):
        self.ingest([kill(1,-5)])
        clear=intel.parse_message(test_intel.line('J5A-IX clr',NOW-1),self.u,'Test Intel','id',NOW)
        with self.store.db() as db:db.execute('INSERT INTO intel_reports VALUES(?,?,?,?,?,?,?)',(clear['id'],clear['timestamp'],clear['channel'],clear['reporter'],clear['message'],json.dumps(clear),NOW))
        data=self.monitor.dashboard(now=NOW+11,region=10);node=next(n for n in data['nodes'] if n['id']==1)
        self.assertEqual(node['state'],'clear');self.assertEqual(node['pilots'],[]);self.assertEqual(node['contacts'],[]);self.assertEqual(node['kill_groups'][0]['count'],1)
        self.assertEqual(len(data['kill_groups']),1);self.assertEqual(data['reports'][0]['state'],'clear')
    def test_notifications_off_blocks_os_and_overlay_without_hiding_kills(self):
        self.ingest([kill(1,-1)]);notifications.save_preferences(self.store,{'os_enabled':True,'categories':{'intel':False}})
        data=self.alerts();self.assertFalse(data['overlay']['enabled']);self.assertFalse(data['notifications_enabled']);self.assertEqual(len(data['items']),1)
        self.assertEqual(notifications.claim(self.store,data,NOW+11),[]);self.assertEqual(len(self.monitor.dashboard(now=NOW+11,region=10)['kill_groups']),1)
    def test_kill_switch_and_feed_master_switch_block_alerts_without_changing_chat(self):
        self.ingest([kill(1,-1)]);intel.save_preferences(self.store,{'killfeed_enabled':False},self.u)
        self.assertEqual(self.alerts()['items'],[]);self.assertEqual(self.groups(),[])
        intel.save_preferences(self.store,{'killfeed_enabled':True},self.u);fleet.schema(self.store);fleet.save_preferences(self.store,{'live':False})
        self.assertEqual(self.alerts()['items'],[]);self.assertEqual(len(self.groups()),1)
        self.assertEqual(intel.preferences(self.store)['channels'],['Test Intel'])
    def test_old_or_future_events_do_not_notify_as_current_activity(self):
        self.ingest([kill(1,-1201),kill(2,50),kill(3,-86401)])
        self.assertEqual(self.alerts()['items'],[])
        self.assertEqual([k['id'] for g in self.groups(NOW+51) for k in g['kills']],[2])
        with self.store.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM intel_kill_events').fetchone()[0],2)
        self.ingest([],NOW+86401)
        with self.store.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM intel_kill_groups').fetchone()[0],0)
    def test_unknown_prices_are_not_zero_and_one_day_storage_is_bounded(self):
        a=kill(1,-1);a['zkb']={};self.ingest([a,kill(2,-1)])
        group=self.groups()[0];self.assertEqual(group['count'],2);self.assertEqual(group['missing'],1);self.assertEqual(group['cents'],'100000000')
        self.ingest([],NOW+86401);self.assertEqual(self.groups(NOW+86401),[])
    def test_invalid_settings_are_rejected_and_region_does_not_change_chat_abbreviations(self):
        from muhely.planner import PlanningError
        for data in [{'killfeed_enabled':1},{'kill_region_ids':[999]},{'kill_region_ids':[True]}]:
            with self.assertRaises(PlanningError):intel.save_preferences(self.store,data,self.u)
        intel.save_preferences(self.store,{'kill_region_ids':[20]},self.u);self.assertEqual(intel.preferences(self.store)['region_ids'],[])
