from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import json,os,tempfile,unittest
from muhely import intel as i,intel_universe as u,notifications as n
from muhely.store import Store
from muhely.esi import AuthenticationError,INTEL_SCOPES,SCOPES,MOON_SCOPES,Vault,EveConnection,LocationScopeError
from muhely.planner import PlanningError
from cryptography.fernet import Fernet
import urllib.parse
NOW=1800000000

def universe():
    return u.Universe({'build':1,'systems':[{'id':a,'name':b,'region_id':r,'region':'Region '+str(r),'security':0,'x':a,'y':a} for a,b,r in [(1,'J5A-IX',10),(2,'L-A5XP',10),(3,'Jita',20),(4,'ABC-12',20),(5,'ABC-13',10),(6,'Isolated',20)]],'edges':[[1,2],[2,3],[3,4],[2,5]],'ships':['Buzzard','Caracal Navy Issue','Falcon']})
def line(body,at=NOW,speaker='Reporter'):
    return '\ufeff[ '+datetime.fromtimestamp(at,timezone.utc).strftime('%Y.%m.%d %H:%M:%S')+' ] '+speaker+' > '+body

def snapshot(data,expires=NOW+60,fetched=NOW):return {'data':data,'fetched':fetched,'expires':expires,'etag':'etag'}

class ParserTests(unittest.TestCase):
    def setUp(self):self.u=universe()
    def parse(self,body,**kw):return i.parse_message(line(body,**kw),self.u,'Intel','channel-id',NOW)
    def test_clr_clear_and_queries(self):
        for s in ['J5A-IX clr','J5A-IX clear','L-A5XP* CLR needle']:
            p=self.parse(s);self.assertEqual(p['state'],'clear');self.assertEqual(p['pilots'],[])
        for s in ['J5A-IX clr?','J5A-IX clear ?']:self.assertEqual(self.parse(s)['state'],'query')
        self.assertEqual(self.parse('J5A-IX not clear')['state'],'contact')
        self.assertIsNone(self.parse('J5A-IX clr',speaker='EVE System'))
    def test_reports_do_not_put_reporter_or_ships_in_pilot_list(self):
        p=self.parse('L-A5XP* Alti UX Buzzard*');self.assertEqual([x['name'] for x in p['pilots']],['Alti UX']);self.assertEqual(p['reporter'],'Reporter');self.assertFalse(p['pilots'][0]['verified'])
        self.assertEqual([x['name'] for x in self.parse('NuvoTeo J5A-IX carcacal NI')['pilots']],['NuvoTeo'])
    def test_ship_names_are_not_systems_and_counts_are_not_pilots(self):
        self.u=u.Universe({'systems':[{'id':1,'name':'Amarr','region_id':1},{'id':2,'name':'J5A-IX','region_id':1}],'edges':[[1,2]],'ships':['Amarr Shuttle','Hecate']})
        p=self.parse('Pilot One J5A-IX Amarr Shuttle');self.assertEqual(p['systems'],[2]);self.assertEqual([x['name'] for x in p['pilots']],['Pilot One'])
        p=self.parse('J5A-IX Hecate 3x');self.assertEqual(p['pilots'],[])
        p=self.parse('J5A-IX  Pilot One  Pilot Two');self.assertEqual([x['name'] for x in p['pilots']],['Pilot One','Pilot Two'])
    def test_linked_character_named_after_system_is_not_a_location(self):
        p=self.parse('L-A5XP <url=showinfo:1373//999>Jita</url> Buzzard');self.assertEqual(p['systems'],[2]);self.assertEqual(p['pilots'],[{'name':'Jita','id':999,'verified':True}])
    def test_unambiguous_abbreviations_and_routes(self):
        self.assertEqual(self.parse('J5A Pilot One')['systems'],[1]);self.assertEqual(self.parse('ABC- Pilot One')['systems'],[])
        p=i.parse_message(line('ABC- Pilot One'),self.u,'Intel','id',NOW,[10]);self.assertEqual(p['systems'],[5]);self.assertTrue(p['abbreviated'])
        p=self.parse('J5A-IX -> L-A5XP Pilot One');self.assertEqual(p['systems'],[2]);self.assertFalse(p['ambiguous'])
        self.assertTrue(self.parse('J5A-IX L-A5XP Pilot One')['ambiguous'])
    def test_future_rows_and_ambiguous_reports_cannot_clear_or_move_a_pilot(self):
        rows=[self.parse('J5A-IX Pilot One',at=NOW-4),self.parse('L-A5XP Jita Pilot One',at=NOW-3),self.parse('J5A-IX clr',at=NOW+10)]
        active,cleared=i.active_state(rows,NOW,120);self.assertIn(1,[r['system_id'] for r in active]);self.assertNotIn(1,cleared)
        rows.append(self.parse('J5A-IX clear',at=NOW-1));active,_=i.active_state(rows,NOW,120);self.assertNotIn(1,[r['system_id'] for r in active])
    def test_bfs_is_shortest_stargate_route_and_keeps_disconnected_systems_unknown(self):
        self.assertEqual(self.u.distances(1),{1:0,2:1,3:2,5:2,4:3});self.assertEqual(self.u.route(1,4),[1,2,3,4]);self.assertEqual(self.u.route(1,6),[])

class IntelStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.store=Store(self.root/'profile');self.store.add_character(11,'Own Pilot');self.logs=self.root/'logs';self.logs.mkdir();self.u=universe();self.eve=Mock();self.monitor=i.IntelMonitor(self.store,None,self.eve,self.u);self.addCleanup(self.monitor.stop)
        self.p=i.save_preferences(self.store,{'folder':str(self.logs),'channels':['Test Intel'],'manual_locations':{'11':1}},self.u);self.monitor.started=NOW-5
    def write_log(self,body,cid=11,channel='Test Intel',listener='Own Pilot',suffix='120000',encoding='utf-16'):
        path=self.logs/f'{channel}_20270115_{suffix}_{cid}.txt';text=f'Channel ID: shared-id\nChannel Name: {channel}\nListener: {listener}\n\n'+body
        path.write_text(text,encoding=encoding);os.utime(path,(NOW,NOW));return path
    def enable(self,**settings):self.p=i.save_preferences(self.store,{'enabled':True,**settings},self.u)
    def scan(self):
        for p in self.logs.glob('*.txt'):
            if not p.is_symlink():os.utime(p,(NOW,NOW))
        self.monitor.scan(self.p,NOW)
    def alerts(self):return i.collect_alerts(self.store,self.u,NOW)
    def test_intel_notification_disable_also_disables_overlay_without_hiding_map_reports(self):
        self.enable(overlay_enabled=True,jumps=1)
        self.write_log(line('L-A5XP Pilot One Buzzard')+'\n');self.scan()
        self.assertTrue(self.alerts()['overlay']['enabled'])
        n.save_preferences(self.store,{'categories':{'intel':False}})
        disabled=self.alerts()
        self.assertFalse(disabled['notifications_enabled']);self.assertFalse(disabled['overlay']['enabled'])
        self.assertEqual(len(disabled['items']),1);self.assertEqual(len(self.monitor.dashboard(now=NOW)['reports']),1)
        self.assertTrue(i.preferences(self.store)['enabled']);self.assertTrue(i.preferences(self.store)['overlay_enabled'])
        n.save_preferences(self.store,{'categories':{'intel':True}})
        self.assertTrue(self.alerts()['overlay']['enabled'])

    def test_overlay_preferences_validate_exact_seconds_and_alert_payload_keeps_report_detail(self):
        self.enable(overlay_enabled=True,overlay_seconds=75,jumps=1)
        self.write_log(line('L-A5XP Pilot One Buzzard')+'\n'+line('Jita Far Pilot')+'\n');self.scan()
        alerts=self.alerts();self.assertEqual(alerts['overlay'],{'enabled':True,'seconds':75});self.assertEqual(len(alerts['items']),1)
        report=alerts['items'][0]['overlay_reports'][0];self.assertEqual(report['pilots'],['Pilot One']);self.assertEqual(report['ships'],['Buzzard']);self.assertEqual(report['when'],NOW);self.assertEqual(alerts['items'][0]['system_name'],'L-A5XP')
        for value in [0,3601,1.5,True]:
            with self.assertRaises(PlanningError):i.save_preferences(self.store,{'overlay_seconds':value},self.u)
        with self.assertRaises(PlanningError):i.save_preferences(self.store,{'overlay_enabled':1},self.u)
        self.enable(overlay_enabled=False);self.assertFalse(self.alerts()['overlay']['enabled'])

    def test_utf16_partial_lines_duplicate_listeners_and_incremental_reads(self):
        path=self.write_log(line('L-A5XP Pilot One')+'\n'+line('Jita Pilot Two')[:-3]);self.scan();self.assertEqual(len(i.read_reports(self.store,self.p,NOW)),1)
        with path.open('ab') as f:f.write((line('Jita Pilot Two')[-3:]+'\n').encode('utf-16-le'))
        self.write_log(line('L-A5XP Pilot One')+'\n',cid=22,listener='Other Pilot');self.scan();self.assertEqual(len(i.read_reports(self.store,self.p,NOW)),2)
        self.scan();self.assertEqual(self.monitor.status['new_messages'],0)
    def test_clr_clears_alert_and_query_does_not(self):
        self.enable();p=self.write_log(line('L-A5XP Pilot One',NOW-3)+'\n');self.scan();self.assertEqual(len(self.alerts()['items']),1)
        with p.open('ab') as f:f.write((line('L-A5XP clr?',NOW-2)+'\n').encode('utf-16-le'))
        self.scan();self.assertEqual(len(self.alerts()['items']),1)
        with p.open('ab') as f:f.write((line('L-A5XP clr',NOW-1)+'\n').encode('utf-16-le'))
        self.scan();self.assertEqual(self.alerts()['items'],[])
    def test_history_remains_visible_without_alerting_and_own_pilot_is_excluded(self):
        self.enable();self.monitor.started=NOW
        self.write_log(line('L-A5XP Pilot One',NOW-10)+'\n'+line('Jita Own Pilot')+'\n');self.scan();self.assertEqual(self.alerts()['items'],[])
        self.assertEqual(len(self.monitor.dashboard(now=NOW)['reports']),2)
    def test_jump_radius_is_inclusive_and_stale_heartbeat_cannot_alert(self):
        self.enable(jumps=1);self.write_log(line('L-A5XP Pilot One')+'\n'+line('Jita Pilot Two')+'\n');self.scan();self.assertEqual([a['system_id'] for a in self.alerts()['items']],[2])
        self.enable(jumps=2);self.assertEqual(len(self.alerts()['items']),2)
        self.assertEqual(i.collect_alerts(self.store,self.u,NOW+11)['items'],[])
    def test_rotation_truncation_and_nonselected_channels(self):
        path=self.write_log(line('L-A5XP Pilot One')+'\n');self.scan();path.unlink();self.write_log(line('Jita Pilot Two')+'\n');self.scan();self.assertEqual(len(i.read_reports(self.store,self.p,NOW)),2)
        self.write_log(line('Jita Pilot Three')+'\n',channel='Other');self.scan();self.assertEqual(len(i.read_reports(self.store,self.p,NOW)),2)
        self.write_log(line('J5A-IX clr')+'\n');self.scan();self.assertEqual(len(i.read_reports(self.store,self.p,NOW)),3)
    def test_symlinks_are_not_followed(self):
        outside=self.root/'outside';outside.write_text(line('Jita Bad')+'\n');(self.logs/'Test Intel_20270115_120000_11.txt').symlink_to(outside);self.scan();self.assertEqual(self.monitor.status['files'],0)
    def test_local_fallback_is_explicit_and_limited_to_own_matching_listener(self):
        self.p=i.save_preferences(self.store,{'manual_locations':{}},self.u)
        self.write_log(line('Channel changed to Local : Jita',speaker='EVE System')+'\n',channel='Local');self.scan();pos=i.positions(self.store,self.u,self.p,NOW)[0];self.assertEqual(pos['system_id'],3);self.assertFalse(pos['alertable'])
        self.p=i.save_preferences(self.store,{'allow_local_alerts':True},self.u);self.assertTrue(i.positions(self.store,self.u,self.p,NOW)[0]['alertable']);self.assertFalse(i.positions(self.store,self.u,self.p,NOW+301)[0]['alertable'])
        self.write_log(line('Channel changed to Local : L-A5XP',speaker='EVE System')+'\n',channel='Local',listener='Impostor',suffix='130000');self.scan();self.assertEqual(i.positions(self.store,self.u,self.p,NOW)[0]['system_id'],3)
    def test_esi_online_cache_and_errors_keep_industry_snapshots_untouched(self):
        self.p=i.save_preferences(self.store,{'manual_locations':{}},self.u);self.store.save_snapshots(11,{'assets':snapshot([{'id':99}])})
        self.eve.http.request.side_effect=[({'solar_system_id':2},{'Cache-Control':'max-age=120','Age':'20','ETag':'location'}),({'online':True},{'Cache-Control':'max-age=60','ETag':'online'})]
        self.monitor.refresh_locations(self.p,NOW);self.assertEqual(self.eve.http.request.call_count,2);self.assertTrue(i.positions(self.store,self.u,self.p,NOW)[0]['alertable']);self.assertEqual(self.store.snapshot(11,'intel_location')['expires'],NOW+100)
        self.monitor.refresh_locations(self.p,NOW+10);self.assertEqual(self.eve.http.request.call_count,2)
        self.eve.http.request.side_effect=AuthenticationError('No grant');self.monitor.refresh_locations(self.p,NOW+121);self.assertTrue(self.store.resource_status(11,'intel_location')['needs_auth']);self.assertFalse(i.positions(self.store,self.u,self.p,NOW+121)[0]['alertable']);self.assertEqual(self.store.snapshot(11,'assets')['data'],[{'id':99}])
    def test_esi_offline_never_alerts_despite_recent_local_log(self):
        self.p=i.save_preferences(self.store,{'manual_locations':{},'allow_local_alerts':True},self.u);self.store.save_snapshots(11,{'intel_position':snapshot({'solar_system_id':2,'online':False})},domain='intel_location')
        self.write_log(line('Channel changed to Local : Jita',speaker='EVE System')+'\n',channel='Local');self.scan();self.assertFalse(i.positions(self.store,self.u,self.p,NOW)[0]['alertable'])
    def test_durable_alert_leases_clear_rearm_and_cooldown(self):
        self.enable(cooldown_seconds=20);n.save_preferences(self.store,{'os_enabled':True});path=self.write_log(line('L-A5XP Pilot One',NOW-3)+'\n');self.scan()
        first=n.claim(self.store,self.alerts(),NOW);self.assertEqual(len(first),1);self.assertEqual(n.claim(self.store,self.alerts(),NOW+1),[])
        with patch('muhely.notifications.time.time',return_value=NOW):n.acknowledge(self.store,[first[0]['receipt']])
        self.assertEqual(n.claim(self.store,self.alerts(),NOW+121),[])
        # Even when clear and the next contact arrive between two UI polls, the episode changes.
        with path.open('ab') as f:f.write((line('L-A5XP clr',NOW-2)+'\n'+line('L-A5XP Pilot One',NOW-1)+'\n').encode('utf-16-le'))
        self.scan();self.assertEqual(n.claim(self.store,self.alerts(),NOW+1),[]);new=n.claim(self.store,self.alerts(),NOW+21);self.assertEqual(len(new),1);self.assertNotEqual(new[0]['notification_id'],first[0]['notification_id'])
    def test_strict_preferences_and_region_view(self):
        for data in [{'enabled':'yes'},{'jumps':31},{'character_ids':[999]},{'manual_locations':{'11':999}},{'channels':'Intel'},{'bogus':1}]:
            with self.subTest(data=data),self.assertRaises(PlanningError):i.save_preferences(self.store,data,self.u)
        self.assertEqual({x['id'] for x in self.monitor.dashboard(now=NOW,region=20)['nodes']},{3,4,6})
    def test_entire_region_is_visible_and_range_is_measured_from_character(self):
        self.p=i.save_preferences(self.store,{'jumps':1},self.u)
        data=self.monitor.dashboard(now=NOW,center=3,region=10,character_id=11)
        self.assertEqual({n['id'] for n in data['nodes']},{1,2,5})
        self.assertEqual({n['id'] for n in data['nodes'] if n['in_range']},{1,2})
        self.assertEqual(next(n for n in data['nodes'] if n['id']==5)['distance'],2)
        large=u.Universe({'systems':[{'id':x,'name':'Sys-'+str(x),'region_id':1,'region':'Full','x':x,'y':0} for x in range(1,502)],'edges':[[x,x+1] for x in range(1,501)]})
        self.monitor.universe=large;data=self.monitor.dashboard(now=NOW,center=1)
        self.assertEqual(len(data['nodes']),501);self.assertFalse(data['clipped'])
    def test_exact_character_lookup_is_cached_and_does_not_resolve_corporations_as_pilots(self):
        self.write_log(line('L-A5XP Steve Hluskan')+'\n');self.scan()
        self.eve.http.request.return_value=({'characters':[{'id':359618261,'name':'Steve Hluskan'},{'id':999,'name':'Unrequested Name'}],'corporations':[{'id':333,'name':'Steve Hluskan'}]}, {})
        self.monitor.resolve_characters(NOW);self.eve.http.request.assert_called_once_with(i.ESI+'/universe/ids/',json_body=['Steve Hluskan'])
        row=self.monitor.dashboard(now=NOW)['reports'][0];self.assertEqual(row['pilots'][0]['zkill_url'],'https://zkillboard.com/character/359618261/');self.assertFalse(row['pilots'][0]['verified'])
        self.monitor.resolve_characters(NOW+10);self.assertEqual(self.eve.http.request.call_count,1)
        with self.store.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM intel_characters').fetchone()[0],1)
    def test_failed_lookup_keeps_intel_and_unknown_names_have_no_fake_link(self):
        self.write_log(line('L-A5XP Unknown Pilot')+'\n');self.scan();self.eve.http.request.side_effect=i.EsiError('offline');self.monitor.resolve_characters(NOW)
        data=self.monitor.dashboard(now=NOW);self.assertEqual(len(data['reports']),1);self.assertIsNone(data['reports'][0]['pilots'][0]['zkill_url']);self.assertIsNotNone(data['status']['names_error']);self.assertIsNone(data['status']['error'])
        self.eve.http.request.side_effect=None;self.eve.http.request.return_value=({'characters':[]},{})
        self.monitor.resolve_characters(NOW);self.monitor.resolve_characters(NOW+100);self.assertEqual(self.eve.http.request.call_count,2)
    def test_contact_cards_include_ship_ids_and_keep_report_association(self):
        self.u.ship_types['buzzard']=11192;self.write_log(line('L-A5XP <url=showinfo:1373//999>Visitor</url> Buzzard')+'\n');self.scan()
        node=next(n for n in self.monitor.dashboard(now=NOW)['nodes'] if n['id']==2)
        card=node['contacts'][0];self.assertEqual(card['ships'],[{'name':'Buzzard','type_id':11192}]);self.assertEqual(card['pilots'][0]['zkill_url'],'https://zkillboard.com/character/999/')

    def test_intel_authorization_preserves_other_feature_grants(self):
        (self.root/'vault').mkdir();self.store.save_settings({'client_id':'client'});key=Fernet.generate_key();vault=Vault(self.root/'vault',key_provider=lambda:key);vault.set(11,{'scopes':SCOPES+MOON_SCOPES,'expires_at':NOW+9999999999,'access_token':'secret'})
        eve=EveConnection(self.store,vault=vault,transport=Mock());url=eve.start('session','http://127.0.0.1:8765/callback',character_id=11,feature='intel');scopes=urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['scope'][0].split();self.assertTrue(set(SCOPES+MOON_SCOPES+INTEL_SCOPES).issubset(scopes))
        with self.assertRaises(LocationScopeError):eve.token(11,INTEL_SCOPES)

if __name__=='__main__':unittest.main()
