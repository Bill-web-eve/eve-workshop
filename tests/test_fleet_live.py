"""Live-feed ordering, recovery, relevance filtering and request etiquette."""
from datetime import datetime,timezone
from unittest.mock import patch
from email.message import Message
import gzip,json,unittest,urllib.error
from muhely import fleet,fleet_live
from muhely.esi import EsiError
import test_fleet
from test_fleet import BASE,kill


def package(sequence,row):
    return {'killmail_id':row['killmail_id'],'sequence_id':sequence,'uploaded_at':BASE,
            'esi':{k:v for k,v in row.items() if k!='zkb'},'zkb':row['zkb']}


class LiveTests(unittest.TestCase):
    setUp=test_fleet.FleetTests.setUp
    def ids(self):
        with self.s.db() as db:return {r[0] for r in db.execute('SELECT id FROM fleet_kills')}
    def cursor(self,sequence=10,**changes):
        self.f.live.cursor={'sequence':sequence,'polled_at':BASE,**changes};self.f.live.next_check=0
    def test_stream_consumes_in_order_stops_at_404_and_resumes_after_restart(self):
        with patch('muhely.fleet_live.time.time',return_value=BASE),patch.object(self.f.live,'_read',side_effect=[{'sequence':10},package(10,kill(1)),None]) as read:
            self.assertEqual(self.f.live.step(),6)
            self.assertEqual([c.args[0] for c in read.call_args_list],['sequence.json','10.json','11.json'])
            self.assertEqual(self.ids(),{1});self.assertEqual(self.f.live.status()['saved'],1)
            self.f.live.step();self.assertEqual(read.call_count,3)
        consumer=fleet_live.LiveFeed(self.f)
        with patch('muhely.fleet_live.time.time',return_value=BASE+7),patch.object(consumer,'_read',return_value=None) as read:
            consumer.step();self.assertEqual(read.call_args.args[0],'11.json')
    def test_surrounding_losses_received_before_own_kill_are_recovered_without_global_archive(self):
        with patch('muhely.fleet.time.time',return_value=BASE):
            self.assertEqual(self.f.ingest_live([kill(1,-899,cid=77),kill(2,-901,cid=77),kill(3,0,sid=2,cid=77)]),0)
            self.assertEqual(self.ids(),set())
            self.assertEqual(self.f.ingest_live([kill(4)]),2)
            self.assertEqual(self.ids(),{1,4})
            self.f.ingest_live([kill(5,899,cid=77),kill(6,901,cid=77)])
            self.assertEqual(self.ids(),{1,4,5})
    def test_position_samples_expand_live_context_and_selected_characters_are_respected(self):
        with patch('muhely.fleet.time.time',return_value=BASE):
            fleet.save_preferences(self.s,{'character_ids':[11]})
            self.f.ingest_live([kill(1),kill(2,100,sid=2,cid=77),kill(3,sid=3,cid=12)])
            self.assertEqual(self.ids(),{1})
            fleet.record_position(self.s,11,2,BASE+100);self.f.ingest_live([])
            self.assertEqual(self.ids(),{1,2})
            fleet.save_preferences(self.s,{'character_ids':[11,12]});self.f.ingest_live([])
            self.assertEqual(self.ids(),{1,2,3})
    def test_reprocessed_kills_update_once_and_duplicate_sequences_do_not_inflate_losses(self):
        self.cursor();first=kill(1);changed=kill(1);changed['zkb']['totalValue']=123.45
        with patch('muhely.fleet_live.time.time',return_value=BASE),patch.object(self.f.live,'_read',side_effect=[package(10,first),package(11,changed),None]):self.f.live.step()
        self.assertEqual(self.ids(),{1})
        with self.s.db() as db:self.assertEqual(json.loads(db.execute('SELECT data FROM fleet_kills').fetchone()[0])['zkb']['totalValue'],123.45)
        self.assertEqual(self.f.live.cursor['sequence'],12)
    def test_disabled_live_or_empty_selection_makes_no_network_requests(self):
        from muhely import intel
        intel.save_preferences(self.s,{'killfeed_enabled':False},self.f.universe)
        for changes in [{'live':False},{'live':True,'character_ids':[]}]:
            fleet.save_preferences(self.s,changes)
            with patch.object(self.f.live,'_read') as read:self.assertEqual(self.f.live.step(),5);read.assert_not_called()
        with self.assertRaises(Exception):fleet.save_preferences(self.s,{'live':1})
    def test_http_rate_limit_persists_retry_and_does_not_advance_cursor(self):
        self.cursor();headers=Message();headers['Retry-After']='1200'
        error=urllib.error.HTTPError('https://r2z2.zkillboard.com/',429,'Rate limit',headers,None)
        with patch('muhely.fleet_live.time.time',return_value=BASE),patch.object(self.f.live,'_read',side_effect=error) as read:
            self.assertEqual(self.f.live.step(),1200);self.assertEqual(self.f.live.cursor['sequence'],10)
            self.f.live.step();self.assertEqual(read.call_count,1)
        consumer=fleet_live.LiveFeed(self.f)
        with patch('muhely.fleet_live.time.time',return_value=BASE+60),patch.object(consumer,'_read') as read:
            consumer.step();read.assert_not_called()
        self.assertIsNotNone(consumer.status()['error'])
    def test_partial_batch_is_saved_before_retry_and_next_sequence_is_checkpointed(self):
        self.cursor()
        with patch('muhely.fleet_live.time.time',return_value=BASE),patch.object(self.f.live,'_read',side_effect=[package(10,kill(1)),OSError('offline')]):
            self.assertEqual(self.f.live.step(),30)
        self.assertEqual(self.ids(),{1});self.assertEqual(fleet.cache(self.s,fleet_live.CURSOR)['data']['sequence'],11)
    def test_invalid_payload_is_not_committed_or_skipped(self):
        self.cursor();bad=package(10,kill(1));bad['sequence_id']=11
        with patch('muhely.fleet_live.time.time',return_value=BASE),patch.object(self.f.live,'_read',return_value=bad):self.f.live.step()
        self.assertEqual(self.ids(),set());self.assertEqual(self.f.live.cursor['sequence'],10);self.assertEqual(self.f.live.status()['phase'],'retrying')
    def test_cursor_advances_only_after_successful_ingestion(self):
        self.cursor()
        with patch('muhely.fleet_live.time.time',return_value=BASE),patch.object(self.f.live,'_read',side_effect=[package(10,kill(1)),None]),patch.object(self.f,'ingest_live',side_effect=OSError('disk')):
            with self.assertRaises(OSError):self.f.live.step()
        self.assertEqual(self.f.live.cursor['sequence'],10);self.assertIsNone(fleet.cache(self.s,fleet_live.CURSOR))
    def test_long_absence_reseeds_and_reports_a_gap(self):
        self.cursor(polled_at=BASE-24*3600)
        with patch('muhely.fleet_live.time.time',return_value=BASE),patch.object(self.f.live,'_read',side_effect=[{'sequence':100},None]):self.f.live.step()
        self.assertEqual(self.f.live.cursor['sequence'],100);self.assertEqual(self.f.live.status()['gap_at'],BASE)
    def test_staging_buffer_has_time_and_size_limits_without_removing_kept_kills(self):
        with patch('muhely.fleet.time.time',return_value=BASE):self.f.ingest_live([kill(1),kill(2,cid=77,sid=2)])
        with patch('muhely.fleet.time.time',return_value=BASE+6*3600+1):self.f.ingest_live([])
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM fleet_live_buffer').fetchone()[0],0)
        self.assertEqual(self.ids(),{1})
        with self.s.db() as db:
            db.executemany('INSERT INTO fleet_live_buffer VALUES(?,?,?,?,?,?)',[(i,BASE,2,BASE,'',json.dumps(kill(i,cid=77,sid=2))) for i in range(100,10110)])
        with patch('muhely.fleet.time.time',return_value=BASE):self.f.ingest_live([])
        with self.s.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM fleet_live_buffer').fetchone()[0],10000)
        self.assertEqual(self.ids(),{1})
    def test_request_is_fixed_host_compressed_public_and_throttled(self):
        class Response:
            headers={'Content-Encoding':'gzip'}
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return gzip.compress(b'{"sequence":10}')
        self.f.live.last_request=100
        with patch('muhely.fleet_live.time.monotonic',return_value=100.05),patch.object(self.f.stop_event,'wait',return_value=False) as wait,patch.object(self.f.live.opener,'open',return_value=Response()) as opened:
            self.assertEqual(self.f.live._pointer(),10);self.assertAlmostEqual(wait.call_args.args[0],.15)
            request=opened.call_args.args[0]
            self.assertEqual(request.full_url,'https://r2z2.zkillboard.com/ephemeral/sequence.json');self.assertNotIn('Authorization',request.headers)
            self.assertIn('User-agent',request.headers);self.assertEqual(request.headers['Accept-encoding'],'gzip')
        with self.assertRaises(EsiError):self.f.live._read('../secret')
    def test_regional_intel_keeps_feed_active_without_fleet_pilots_and_saves_public_kill(self):
        from muhely import intel
        fleet.save_preferences(self.s,{'character_ids':[]});self.cursor()
        with patch('muhely.fleet_live.time.time',return_value=BASE),patch.object(self.f.live,'_read',side_effect=[package(10,kill(1,cid=77)),None]):self.f.live.step()
        self.assertEqual(self.ids(),set())
        with self.s.db() as db:self.assertEqual(db.execute('SELECT id FROM intel_kill_events').fetchone()[0],1)
        self.assertTrue(intel.preferences(self.s)['killfeed_enabled']);self.assertEqual(self.f.live.cursor['sequence'],11)
