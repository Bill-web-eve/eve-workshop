import tempfile,time,unittest,json,urllib.error
from pathlib import Path
from unittest.mock import Mock
from datetime import datetime,timezone
from muhely.catalog import Catalog
from muhely.store import Store
from muhely.moons import validate_moon,dashboard
from muhely.extractions import report,sync,crystal_plan
from muhely.moon_notifications import parse,text_fields,eve_time,SCOPE
from muhely.esi import EveConnection,Transport,AuthenticationError,EsiError,MOON_SCOPES,MoonScopeError
ROOT=Path(__file__).resolve().parents[1]
iso=lambda t:datetime.fromtimestamp(t,timezone.utc).isoformat()
def ticks(t):return str(round((t+11644473600)*10_000_000))
def snap(data,when=None):return {'data':data,'fetched':when or time.time(),'expires':time.time()+600,'etag':'notify-etag'}

class NotificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=Catalog(ROOT/'data/catalog.sqlite3')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=Store(self.tmp.name);self.s.add_character(1,'Reader')
        self.now=round(time.time());self.ready=self.now+86400;self.auto=self.ready+10800
        sid=next(i for i,s in self.c.moon_systems.items() if s['name']=='RP2-OQ');self.mid=next(m['id'] for m in self.c.moon_locations(sid) if m['name']=='RP2-OQ VI - Moon 7')
        self.moon=validate_moon(dict(system_id=sid,moon_id=self.mid,structure='Athanor',ores=[{'id':45490,'percent':50},{'id':45494,'percent':50}]),self.c,[]);self.s.save_moon(self.moon)
    def note(self,kind='MoonminingExtractionStarted',nid=10,when=None,ore=None,ready=None):
        body=f"moonID: {self.mid}\nstructureID: 9001\n"
        if kind=='MoonminingExtractionStarted':body+=f'readyTime: {ticks(ready or self.ready)}\n'
        if kind in ['MoonminingExtractionStarted','MoonminingExtractionFinished']:body+=f'autoTime: {ticks(self.auto)}\n'
        if kind!='MoonminingExtractionCancelled':body+='oreVolumeByType:\n'+''.join(f'  {k}: {v}\n' for k,v in (ore or {45490:750000,45494:250000}).items())
        return dict(notification_id=nid,type=kind,timestamp=iso(when or self.now-86400),text=body)
    def seed(self,rows,reader=1):self.s.save_snapshots(reader,{'moon_notifications':snap({'notifications':rows})},domain='moon_notifications')
    def timer(self):return dict(moon_id=self.mid,structure_id=9001,extraction_start_time=iso(self.now-86400),chunk_arrival_time=iso(self.ready),natural_decay_time=iso(self.auto))
    def test_parser_reads_precise_volume_map_and_filetime(self):
        n=parse(self.note(),self.c);self.assertEqual(n['moon_id'],self.mid);self.assertAlmostEqual(n['ready_time'],self.ready,places=5);self.assertEqual(sum(o['volume'] for o in n['ores']),1_000_000)
    def test_inline_yaml_and_scientific_volume(self):
        n=self.note();n['text']=n['text'].split('oreVolumeByType:')[0]+'oreVolumeByType: {45490: 7.5e5, 45494: 250000}'
        self.assertEqual([o['volume'] for o in parse(n,self.c)['ores']],[750000,250000])
    def test_reject_duplicate_negative_nonfinite_aliases_and_unknown_ores(self):
        for content in ['  45490: 1\n  45490: 2','  45490: -1','  45490: .nan','  45490: *alias','  1: 99']:
            n=self.note();n['text']=n['text'].split('oreVolumeByType:')[0]+'oreVolumeByType:\n'+content
            with self.subTest(content=content),self.assertRaises(ValueError):parse(n,self.c)
    def test_never_interprets_yaml_tags_or_executes_text(self):
        n=self.note();n['text']=n['text'].replace('moonID:','moonID: !!python/object/apply:os.system ')
        with self.assertRaises(ValueError):parse(n,self.c)
    def test_actual_enriched_and_jackpot_types_map_to_crystal_class(self):
        self.assertEqual(len(self.c.moon_variants),60)
        n=self.note(ore={46280:500000,46281:250000,45494:250000});self.seed([n]);r=report(self.s,self.c,self.now);event=r['events'][0]
        self.assertEqual(event['composition_source'],'esi_notification');self.assertEqual([o['percent'] for o in event['ores']],[75,25]);self.assertEqual(event['raw_ores'][0]['name'],'Brimful Zeolites')
        self.assertEqual([r['count'] for r in crystal_plan(self.s,self.c,self.moon['id'],event['id'])['rows']],[3,1])
    def test_decimal_volumes_preserve_exact_smallest_integer_ratio(self):
        self.seed([self.note(ore={46280:0.1,46281:0.2,45494:0.4})]);event=report(self.s,self.c,self.now)['events'][0]
        self.assertEqual([r['count'] for r in crystal_plan(self.s,self.c,self.moon['id'],event['id'])['rows']],[3,4])

    def test_notification_alone_schedules_without_corporation_timer_access(self):
        self.seed([self.note()]);r=report(self.s,self.c,self.now);self.assertEqual(len(r['events']),1);self.assertEqual(r['moons'][self.moon['id']]['status'],'scheduled')
    def test_notification_quantities_override_calendar_and_manual_percentages(self):
        self.seed([self.note()]);self.s.save_snapshots(1,{'moon_timers':snap({'corporation_id':98,'rows':[self.timer()]}),'moon_calendar':snap([dict(event_id=77,title='RP2-OQ VI - Moon 7',date=iso(self.ready),text='Zeolites 5 m³<br>Cobaltite 5 m³')])},domain='moon_timers')
        r=report(self.s,self.c,self.now);self.assertEqual(len(r['events']),1);self.assertEqual(r['events'][0]['volume'],1_000_000)
        moon=dashboard(self.s,self.c)['moons'][0];self.assertEqual(moon['composition_source'],'esi_notification');self.assertEqual([o['percent'] for o in moon['ores']],[75,25]);self.assertEqual(self.s.moon_records()[0]['ores'][0]['percent'],50)
    def test_observed_laser_fire_anchors_ore_expiry(self):
        start=self.note(ready=self.now-100,when=self.now-86400);fired=self.note(kind='MoonminingLaserFired',nid=12,when=self.now-50,ore={46281:1_500_000,45494:250000})
        self.seed([start,fired]);e=report(self.s,self.c,self.now)['events'][0];self.assertEqual(e['fractured_at'],self.now-50);self.assertEqual(e['belt_earliest_expiry'],self.now-50+48*3600);self.assertEqual(e['belt_latest_expiry'],e['belt_earliest_expiry'])
    def test_finished_without_started_notification_still_exposes_ore(self):
        self.seed([self.note(kind='MoonminingExtractionFinished',when=self.now-100)]);e=report(self.s,self.c,self.now)['events'][0];self.assertEqual(e['volume'],1_000_000)
    def test_finished_and_fracture_merge_when_start_notification_is_missing(self):
        self.seed([self.note(kind='MoonminingExtractionFinished',nid=10,when=self.now-100),self.note(kind='MoonminingLaserFired',nid=11,when=self.now-50)])
        events=report(self.s,self.c,self.now)['events'];self.assertEqual(len(events),1);self.assertEqual(events[0]['fractured_at'],self.now-50)

    def test_cancellation_suppresses_stale_timer(self):
        self.seed([self.note(),self.note(kind='MoonminingExtractionCancelled',nid=11,when=self.now)])
        self.s.save_snapshots(1,{'moon_timers':snap({'corporation_id':98,'rows':[self.timer()]})},domain='moon_timers')
        self.assertFalse(report(self.s,self.c,self.now)['events'])
    def test_cancel_without_start_suppresses_existing_pull_only(self):
        self.seed([self.note(kind='MoonminingExtractionCancelled',nid=11,when=self.now)])
        self.s.save_snapshots(1,{'moon_timers':snap({'corporation_id':98,'rows':[self.timer()]})},domain='moon_timers')
        self.assertFalse(report(self.s,self.c,self.now)['events'])
        timer=dict(self.timer(),extraction_start_time=iso(self.now+1),chunk_arrival_time=iso(self.ready+86400),natural_decay_time=iso(self.auto+86400))
        self.s.save_snapshots(1,{'moon_timers':snap({'corporation_id':98,'rows':[timer]})},domain='moon_timers');self.assertEqual(len(report(self.s,self.c,self.now)['events']),1)
    def test_multiple_readers_do_not_duplicate_a_pull(self):
        self.seed([self.note()]);self.s.add_character(2,'Second Reader');self.seed([self.note(nid=999)],2)
        self.assertEqual(len(report(self.s,self.c,self.now)['events']),1)
    def test_malformed_notification_is_an_issue_not_a_false_scan(self):
        n=self.note(ore={1:999});self.seed([n]);r=report(self.s,self.c,self.now);self.assertEqual(len(r['notification_issues']),1);self.assertIsNone(r['moons'][self.moon['id']]['composition'])
    def test_authorized_but_not_synced_is_exposed_without_tokens(self):
        r=report(self.s,self.c,self.now,access_scopes={1:MOON_SCOPES});self.assertTrue(r['access'][0]['moon_notifications']['scope_granted']);self.assertIsNone(r['access'][0]['moon_notifications']['fetched'])
    def test_sync_persists_only_moon_notifications_and_honors_cache(self):
        eve=EveConnection(self.s,vault=Mock(),transport=Mock());eve.token=Mock(return_value='private-never-print')
        def request(url,**kw):
            if url.endswith('/notifications'):return ([self.note(),dict(notification_id=999,type='Other',timestamp=iso(self.now),text='unrelated private text')],{'Cache-Control':'max-age=600'})
            if url.endswith('/calendar'):return ([],{'Cache-Control':'max-age=600'})
            if '/mining/extractions' in url:return ([],{'X-Pages':'1','Cache-Control':'max-age=1800'})
            return ({'corporation_id':98},{})
        eve.http.request.side_effect=request;self.assertTrue(all(r['ok'] for r in sync(eve)))
        for kind in ['moon_notifications','moon_notification_response']:
            self.assertNotIn('unrelated private text',json.dumps(self.s.snapshot(1,kind)))
        count=eve.http.request.call_count;sync(eve);self.assertEqual(eve.http.request.call_count,count+1)
    def test_http_403_identifies_station_manager_instead_of_consent(self):
        transport=Transport();transport.opener=Mock();transport.opener.open.side_effect=urllib.error.HTTPError('https://esi.evetech.net/a',403,'Forbidden',{},None)
        with self.assertRaises(AuthenticationError) as caught:transport.request('https://esi.evetech.net/a')
        self.assertEqual(caught.exception.status_code,403)
        eve=EveConnection(self.s,vault=Mock(),transport=Mock());eve.token=Mock(return_value='private');denied=caught.exception
        def request(url,**kw):
            if '/mining/extractions' in url:raise denied
            if '/notifications' in url or '/calendar' in url:return ([],{})
            return ({'corporation_id':98},{})
        eve.http.request.side_effect=request;results=sync(eve);status=self.s.resource_status(1,'moon_timers');self.assertFalse(status['needs_auth']);self.assertIn('Station Manager',status['error'])
        timer=next(r for r in results if r['kind']=='timers');self.assertFalse(timer['warning']);self.assertEqual(timer['reason'],'role_denied')
        self.assertTrue(report(self.s,self.c)['access'][0]['moon_timers']['optional_unavailable'])
        self.s.save_snapshots(1,{'moon_timers':snap({'corporation_id':98,'rows':[self.timer()]})},domain='moon_timers')
        timer=next(r for r in sync(eve) if r['kind']=='timers');self.assertTrue(timer['warning'])
        self.assertEqual(self.s.snapshot(1,'moon_timers')['data']['rows'],[self.timer()])
        self.assertFalse(report(self.s,self.c)['access'][0]['moon_timers']['optional_unavailable'])

    def test_never_authorized_sources_are_skipped_but_lost_access_remains_a_warning(self):
        eve=EveConnection(self.s,vault=Mock(),transport=Mock());eve.token=Mock(side_effect=MoonScopeError('Missing moon permission'))
        results=sync(eve);self.assertEqual(len(results),3)
        self.assertTrue(all(not r['ok'] and not r['warning'] and r['reason']=='missing_scope' for r in results))
        eve.http.request.assert_not_called()
        self.seed([self.note()]);results=sync(eve)
        self.assertTrue(next(r for r in results if r['kind']=='notifications')['warning'])
        self.assertEqual(len(self.s.snapshot(1,'moon_notifications')['data']['notifications']),1)

    def test_network_and_sso_failures_are_not_masked_as_optional_access(self):
        for error in [EsiError('offline'),AuthenticationError('Login expired')]:
            eve=EveConnection(self.s,vault=Mock(),transport=Mock());eve.token=Mock(side_effect=error)
            self.assertTrue(all(r['warning'] and r['reason']=='request_failed' for r in sync(eve)))
        denied=AuthenticationError('SSO rejected');denied.status_code=403
        eve.token.side_effect=denied
        self.assertTrue(all(r['warning'] and r['reason']=='request_failed' for r in sync(eve)))
    def test_scope_metadata_does_not_expose_tokens(self):
        vault=Mock();vault.read.return_value={'1':dict(scopes=MOON_SCOPES,access_token='never-expose',refresh_token='secret')};eve=EveConnection(self.s,vault=vault)
        self.assertEqual(eve.granted_scopes(),{1:MOON_SCOPES});self.assertNotIn('never-expose',json.dumps(eve.granted_scopes()))
    def test_invalid_filetime_is_not_guessed(self):
        self.assertIsNone(eve_time('not a time'));self.assertIsNone(eve_time(42));self.assertIsNone(eve_time('2026-10-17T10:00:00'))
