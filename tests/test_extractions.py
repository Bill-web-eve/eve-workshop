import json,tempfile,time,unittest,urllib.parse
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import Mock
from muhely.catalog import Catalog
from muhely.store import Store
from muhely.esi import EveConnection,EsiError,MOON_SCOPES,SCOPES
from muhely.extractions import report,sync,event_ores,validate_timers,crystal_plan,cached
from muhely.moons import validate_moon,dashboard
ROOT=Path(__file__).resolve().parents[1]
def iso(n):return datetime.fromtimestamp(n,timezone.utc).isoformat()
def snap(data,when=None,expires=None):
    now=time.time();return {'data':data,'fetched':when or now,'expires':expires or now+600,'etag':'test'}

class ExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=Catalog(ROOT/'data/catalog.sqlite3')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=Store(self.tmp.name)
        self.s.add_character(1,'Test');self.now=time.time()
        self.sid=next(i for i,s in self.c.moon_systems.items() if s['name']=='RP2-OQ')
        self.mid=next(m['id'] for m in self.c.moon_locations(self.sid) if m['name']=='RP2-OQ VI - Moon 7')
        self.moon=validate_moon({'system_id':self.sid,'moon_id':self.mid,'structure':'Athanor','ores':[{'id':45490,'percent':75},{'id':45494,'percent':25}]},self.c,[]);self.s.save_moon(self.moon)
        self.timer={'moon_id':self.mid,'structure_id':900001,'extraction_start_time':iso(self.now-7*86400),'chunk_arrival_time':iso(self.now+7*86400),'natural_decay_time':iso(self.now+7*86400+10800)}
        self.event={'event_id':50,'title':'RP2-OQ VI - Moon 7 extraction','text':'Zeolites: 750,000 m³<br>Cobaltite: 250,000 m³','date':self.timer['chunk_arrival_time']}
    def seed(self,rows=None,event=True):
        parts={'moon_timers':snap({'corporation_id':98,'rows':[self.timer] if rows is None else rows})}
        if event:parts['moon_calendar']=snap([self.event])
        self.s.save_snapshots(1,parts,domain='moon_timers')
    def calendar_completion(self,moon_id=None,**updates):
        return dict(self.event,title='Moon extraction for RP2-OQ - Private - 0',
            text='The moon chunk extraction for <a href="showinfo:35835//900001">RP2-OQ - Private drill</a> at '
                 f'<a href="showinfo:14//{moon_id or self.mid}">RP2-OQ VI - Moon 7</a> in '
                 f'<a href="showinfo:5//{self.sid}">RP2-OQ</a> will complete at this time. '
                 'The moon chunk will be available for fracturing after this time into a minable asteroid field.',**updates)

    def test_standard_truncated_calendar_title_matches_moon_id_without_timer_or_ore_scan(self):
        self.s.save_snapshots(1,{'moon_calendar':snap([self.calendar_completion()])},domain='moon_calendar')
        result=report(self.s,self.c,self.now)
        self.assertEqual(len(result['events']),1)
        event=result['events'][0]
        self.assertEqual(event['date'],self.timer['chunk_arrival_time'])
        self.assertEqual(event['timing_source'],'esi_calendar')
        self.assertIsNone(event['volume']);self.assertEqual(event['ores'],[])
        self.assertEqual(result['moons'][self.moon['id']]['status'],'calendar_only')

    def test_unregistered_moon_is_not_added_even_if_link_caption_matches_registered_name(self):
        self.s.save_snapshots(1,{'moon_calendar':snap([self.calendar_completion(moon_id=99999999)])},domain='moon_calendar')
        self.assertEqual(report(self.s,self.c,self.now)['events'],[])
        self.assertEqual(len(self.s.moon_records()),1)

    def test_fuel_alarm_at_registered_moon_is_not_an_extraction(self):
        event=dict(self.calendar_completion(),title='Control tower in RP2-OQ goes offline')
        event['text']=f'Shadow Control Tower will run out of fuel. Moon: <a href="showinfo:14//{self.mid}">RP2-OQ VI - Moon 7</a>'
        self.s.save_snapshots(1,{'moon_calendar':snap([event])},domain='moon_calendar')
        self.assertEqual(report(self.s,self.c,self.now)['events'],[])

    def test_explicit_moon_id_takes_priority_over_caption_and_conflicting_system_is_rejected(self):
        event=self.calendar_completion();event['text']=event['text'].replace('RP2-OQ VI - Moon 7','renamed link caption')
        self.s.save_snapshots(1,{'moon_calendar':snap([event])},domain='moon_calendar')
        self.assertEqual(len(report(self.s,self.c,self.now)['events']),1)
        event['text']=event['text'].replace('showinfo:5//'+str(self.sid),'showinfo:5//30000142')
        self.s.save_snapshots(1,{'moon_calendar':snap([event])},domain='moon_calendar')
        self.assertEqual(report(self.s,self.c,self.now)['events'],[])

    def test_calendar_readers_and_local_calendar_export_do_not_duplicate_the_pull(self):
        from muhely.moon_calendar import export
        self.s.add_character(2,'Second calendar reader')
        for cid in [1,2]:self.s.save_snapshots(cid,{'moon_calendar':snap([self.calendar_completion()])},domain='moon_calendar')
        raw=export(self.s,self.c)
        self.assertEqual(raw.count(b'BEGIN:VEVENT'),1)
        self.assertIn(b'Extraction time source: ESI calendar event.',raw)
        self.assertIn(self.timer['chunk_arrival_time'][:10].replace('-','').encode(),raw)

    def test_natural_decay_is_not_ore_expiry(self):
        self.seed();e=report(self.s,self.c,self.now)['events'][0]
        self.assertEqual(e['volume'],1000000);self.assertEqual(e['volume_source'],'esi_calendar')
        self.assertAlmostEqual(e['belt_latest_expiry'],self.now+7*86400+10800+48*3600,places=5)
        self.assertNotEqual(e['belt_latest_expiry'],__import__('muhely.extractions',fromlist=['stamp']).stamp(e['natural_decay_time']))
    def test_calendar_composition_overlays_without_mutating_manual_input(self):
        self.moon['ores']=[{'id':45490,'percent':99}];self.s.save_moon(self.moon);self.seed()
        m=dashboard(self.s,self.c)['moons'][0]
        self.assertEqual(m['composition_source'],'esi_calendar');self.assertEqual([r['percent'] for r in m['ores']],[75,25])
        self.assertEqual(m['manual_ores'],[{'id':45490,'percent':99}]);self.assertEqual(self.s.moon_records()[0]['ores'],m['manual_ores'])
    def test_no_volume_never_turns_manual_scan_into_esi_scan(self):
        self.event['text']='No scan in this calendar';self.seed();e=report(self.s,self.c,self.now)['events'][0]
        self.assertEqual(e['composition_source'],'manual');self.assertAlmostEqual(e['volume'],14*24*30000)
        self.assertEqual(dashboard(self.s,self.c)['moons'][0]['composition_source'],'manual')
    def test_manual_ratio_is_three_to_one(self):
        plan=crystal_plan(self.s,self.c,self.moon['id']);self.assertEqual([r['count'] for r in plan['rows']],[3,1])
    def test_explicit_extraction_volume_ratio_is_three_to_one(self):
        self.seed();e=report(self.s,self.c)['events'][0];plan=crystal_plan(self.s,self.c,self.moon['id'],e['id'])
        self.assertEqual([r['count'] for r in plan['rows']],[3,1]);self.assertEqual(plan['total_count'],4)
    def test_same_class_ores_are_combined_before_ratio(self):
        self.moon['ores']=[{'id':45490,'percent':50},{'id':45492,'percent':25},{'id':45494,'percent':25}];self.s.save_moon(self.moon)
        plan=crystal_plan(self.s,self.c,self.moon['id']);self.assertEqual([r['count'] for r in plan['rows']],[3,1]);self.assertEqual(len(plan['rows'][0]['ores']),2)
    def test_exact_decimal_ratio_and_no_false_wear(self):
        self.moon['ores']=[{'id':45490,'percent':37.5},{'id':45494,'percent':12.5}];self.s.save_moon(self.moon)
        self.assertEqual([r['count'] for r in crystal_plan(self.s,self.c,self.moon['id'])['rows']],[3,1])
    def test_crystal_counts_are_single_digit_upward_rounded_ratios(self):
        for percentages,expected in [([75,25],[3,1]),([90,10],[9,1]),([99.99,.01],[9,1]),([37.3,62.7],[2,3]),([51,49],[1,1])]:
            with self.subTest(percentages=percentages):
                self.moon['ores']=[{'id':45490,'percent':percentages[0]},{'id':45494,'percent':percentages[1]}]
                self.s.save_moon(self.moon)
                result=crystal_plan(self.s,self.c,self.moon['id'])
                self.assertEqual([r['count'] for r in result['rows']],expected)
                self.assertTrue(all(1<=r['count']<=9 for r in result['rows']))
                self.assertAlmostEqual(sum(r['share'] for r in result['rows']),100)
                self.assertEqual(result['total_count'],sum(expected))
    def test_notification_volume_ratio_is_bounded_without_zeroing_small_ore(self):
        self.event['text']='Zeolites 999,999 m³<br>Cobaltite 1 m³';self.seed()
        event=report(self.s,self.c)['events'][0]
        result=crystal_plan(self.s,self.c,self.moon['id'],event['id'])
        self.assertEqual([r['count'] for r in result['rows']],[9,1])
        self.assertTrue(result['approximate'])
    def test_four_crystal_groups_stay_present_and_at_most_nine(self):
        ids=[];skills=set()
        for ore in self.c.moon_ores.values():
            if ore['skill_id'] not in skills:ids.append(ore['id']);skills.add(ore['skill_id'])
            if len(ids)==4:break
        self.moon['ores']=[{'id':i,'percent':p} for i,p in zip(ids,[.01,10.12,30.34,59.53])]
        self.s.save_moon(self.moon)
        rows=crystal_plan(self.s,self.c,self.moon['id'])['rows']
        self.assertEqual(len(rows),4)
        self.assertTrue(all(1<=r['count']<=9 for r in rows))
    def test_metenox_never_warns_or_needs_crystals(self):
        self.moon['structure']='Metenox';self.s.save_moon(self.moon)
        self.assertEqual(report(self.s,self.c)['moons'][self.moon['id']]['status'],'not_applicable')
        self.assertEqual(crystal_plan(self.s,self.c,self.moon['id'])['rows'],[])
    def test_stopped_drill_not_missing(self):
        self.moon['enabled']=False;self.s.save_moon(self.moon)
        self.assertEqual(report(self.s,self.c)['moons'][self.moon['id']]['status'],'not_applicable')
    def test_missing_and_unavailable_are_distinct(self):
        self.assertEqual(report(self.s,self.c)['moons'][self.moon['id']]['status'],'unknown')
        self.seed(rows=[],event=False);self.assertEqual(report(self.s,self.c)['moons'][self.moon['id']]['status'],'missing')
    def test_stale_calendar_cannot_overwrite_scan(self):
        self.seed();self.s.resource_error(1,'moon_calendar','offline')
        self.assertIsNone(report(self.s,self.c)['moons'][self.moon['id']]['composition'])
    def test_new_empty_corp_snapshot_supersedes_old_member_timer(self):
        self.seed(event=False);self.s.add_character(2,'Other');self.s.save_snapshots(2,{'moon_timers':snap({'corporation_id':98,'rows':[]},self.now+5)},domain='moon_timers')
        self.assertFalse(report(self.s,self.c,self.now)['events'])
    def test_calendar_meeting_does_not_confirm_drill(self):
        self.s.save_snapshots(1,{'moon_calendar':snap([dict(self.event,text='Meet to mine')])},domain='moon_calendar')
        self.assertEqual(report(self.s,self.c)['moons'][self.moon['id']]['status'],'calendar_only')
    def test_conflicting_scans_are_not_auto_applied(self):
        self.seed();self.s.save_snapshots(1,{'moon_calendar':snap([self.event,dict(self.event,event_id=51,text='Zeolites 500 m³<br>Cobaltite 500 m³')])},domain='moon_calendar')
        self.assertIsNone(report(self.s,self.c)['moons'][self.moon['id']]['composition'])
    def test_parser_refuses_ambiguous_unknown_and_duplicate_data(self):
        for body in ['Zeolites 7,5 m³','Unknown 100 m³','Zeolites 5 m³<br>Zeolites 2 m³','Zeolites -5 m³','Zeolites 1e6 m³','Zeolites 100 m³<br>Cobaltite 25%']:
            self.assertFalse(event_ores(dict(self.event,text=body),self.c),body)
    def test_table_calendar_and_two_to_one_exact_volume(self):
        ores=event_ores(dict(self.event,text='<table><tr><td>Zeolites</td><td>2 m³</td></tr><tr><td>Cobaltite</td><td>1 m³</td></tr></table>'),self.c)
        self.assertEqual([o['volume'] for o in ores],[2,1])
    def test_timers_validation(self):
        for row in [dict(self.timer,moon_id=True),dict(self.timer,natural_decay_time='bad'),dict(self.timer,chunk_arrival_time=iso(self.now-9*86400))]:
            with self.assertRaises(EsiError):validate_timers([row])
    def test_cache_and_304_preserve_snapshot(self):
        eve=EveConnection(self.s,vault=Mock(),transport=Mock());self.s.save_snapshots(1,{'test':snap([])})
        self.assertEqual(cached(eve,1,'test','url','token',lambda x:None)['data'],[]);eve.http.request.assert_not_called()
        self.s.save_snapshots(1,{'test':snap([],expires=self.now-1)});eve.http.request.return_value=(None,{'Cache-Control':'max-age=300'})
        self.assertEqual(cached(eve,1,'test','url','token',lambda x:None)['data'],[])
    def test_dedicated_consent_keeps_existing_scopes(self):
        self.s.save_settings({'client_id':'public'});vault=Mock();vault.read.return_value={'1':{'scopes':SCOPES}}
        eve=EveConnection(self.s,vault=vault,transport=Mock());url=eve.start('cookie','http://127.0.0.1/callback',1,'moons')
        granted=set(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['scope'][0].split());self.assertEqual(granted,set(SCOPES+MOON_SCOPES))
    def test_sync_does_not_modify_industry_data_or_inventory(self):
        eve=EveConnection(self.s,vault=Mock(),transport=Mock());eve.token=Mock(return_value='private')
        def respond(url,**kw):
            if url.endswith('/notifications'):return ([],{'Cache-Control':'max-age=600'})
            if url.endswith('/calendar'):return ([dict(event_id=50,event_date=self.event['date'])],{'Cache-Control':'max-age=600'})
            if '/calendar/50' in url:return (self.event,{'Cache-Control':'max-age=600'})
            if '/mining/extractions' in url:return ([self.timer],{'X-Pages':'1'})
            return ({'corporation_id':98},{})
        eve.http.request.side_effect=respond
        self.assertTrue(all(r['ok'] for r in sync(eve)));self.assertIsNone(self.s.snapshot(1,'assets'));self.assertEqual(self.s.mapping('inventory'),{})
        self.assertEqual(report(self.s,self.c)['moons'][self.moon['id']]['status'],'scheduled')
        calls=eve.http.request.call_count;self.assertTrue(all(r['ok'] for r in sync(eve)));self.assertEqual(eve.http.request.call_count,calls+1) # membership checked
    def test_failed_sync_retains_old_snapshot_and_marks_stale(self):
        self.seed();eve=EveConnection(self.s,vault=Mock(),transport=Mock());eve.token=Mock(side_effect=EsiError('offline'))
        self.assertTrue(all(not r['ok'] for r in sync(eve)));self.assertEqual(self.s.snapshot(1,'moon_timers')['data']['rows'],[self.timer])
        self.assertEqual(report(self.s,self.c)['moons'][self.moon['id']]['status'],'stale')
    def test_cache_control_ignores_cached_age_and_honors_server_ttl(self):
        from muhely.extractions import cache_expiry
        self.assertEqual(cache_expiry({'Cache-Control':'max-age=3600','Age':'100'},1000),4500)
        self.assertEqual(cache_expiry({'Cache-Control':'max-age=0'},1000),1060)
    def test_previous_belt_does_not_count_as_a_scheduled_next_extraction(self):
        previous=dict(self.timer,extraction_start_time=iso(self.now-16*86400),chunk_arrival_time=iso(self.now-86400),natural_decay_time=iso(self.now-86400+10800))
        self.s.save_snapshots(1,{'moon_timers':snap({'corporation_id':98,'rows':[],'history':[previous]})},domain='moon_timers')
        r=report(self.s,self.c,self.now);self.assertEqual(r['moons'][self.moon['id']]['status'],'missing');self.assertEqual(r['events'][0]['kind'],'history')
    def test_cancelled_future_history_does_not_reappear(self):
        self.s.save_snapshots(1,{'moon_timers':snap({'corporation_id':98,'rows':[],'history':[self.timer]})},domain='moon_timers')
        self.assertFalse(report(self.s,self.c,self.now)['events'])
    def test_invalid_excess_scan_has_no_crystal_suggestion(self):
        self.moon['ores']=[{'id':45490,'percent':100},{'id':45494,'percent':100}];self.s.save_moon(self.moon)
        result=crystal_plan(self.s,self.c,self.moon['id']);self.assertEqual(result['rows'],[]);self.assertTrue(result['unavailable'])
