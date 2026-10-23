from pathlib import Path
import tempfile,threading,time,unittest
from unittest.mock import Mock,patch
from muhely.store import Store
from muhely.refresh_policy import RefreshPolicy
from muhely.server import App
import test_server as server_tests

ROOT=Path(__file__).resolve().parents[1]
class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name);self.policy=RefreshPolicy(self.store)
    def test_exact_interval_restart_manual_override_and_failed_attempts(self):
        self.assertEqual(self.policy.claim(['pi'],now=1000),{'pi'})
        again=RefreshPolicy(Store(self.tmp.name))
        self.assertEqual(again.claim(['pi'],now=1899.99),set())
        self.assertEqual(again.claim(['pi'],now=1900),{'pi'})
        self.assertEqual(again.claim(['pi'],manual=True,now=1901),{'pi'})
        self.assertEqual(again.next_at(['pi']),2801)
        self.assertEqual(again.claim(['pi'],now=2800),set())
        # Claim before the request means failures also observe the interval.
        self.assertEqual(again.claim(['failing'],now=3000),{'failing'})
        self.assertEqual(again.claim(['failing'],now=3001),set())
    def test_parallel_windows_cannot_both_claim_same_source(self):
        barrier=threading.Barrier(4);results=[]
        def work():barrier.wait();results.append(self.policy.claim(['pi'],now=1000))
        workers=[threading.Thread(target=work) for _ in range(4)]
        for worker in workers:worker.start()
        for worker in workers:worker.join()
        self.assertEqual(sum(bool(r) for r in results),1)
    def test_independent_sources_do_not_block_each_other(self):
        self.policy.claim(['skills'],now=1000)
        self.assertEqual(self.policy.claim(['skills','pi'],now=1100),{'pi'})
    def test_long_batch_cooldown_starts_after_its_last_request(self):
        app=App(self.tmp.name,ROOT/'data/catalog.sqlite3',0);self.addCleanup(app.intel.stop)
        app.store.add_character(1,'Pilot');clock=[1000]
        def slow_sync():clock[0]=1600;return []
        app.eve.sync=slow_sync;app.eve.sync_skills=Mock(return_value=[]);app.eve.sync_pi=Mock(return_value=[])
        with patch('muhely.refresh_policy.time.time',side_effect=lambda:clock[0]):
            app.start_task('notifications',manual=False)
            deadline=time.monotonic()+3
            while app.task['running'] and time.monotonic()<deadline:time.sleep(.01)
            self.assertFalse(app.task['running'])
            self.assertEqual(app.refresh_policy.next_at(['industry']),2500)
            self.assertFalse(app.start_task('sync',manual=False))

    def test_corporation_monitoring_survives_metadata_rediscovery(self):
        self.store.add_character(1,'Pilot');self.store.character_corporation(1,99,'Corp')
        self.store.set_corporation_monitoring(99,False)
        self.store.character_corporation(1,99,'Renamed')
        self.assertFalse(Store(self.tmp.name).corporation_monitored(99))
        self.assertEqual(self.store.corporation(99)['name'],'Renamed')

class RefreshApiTests(unittest.TestCase):
    setUp=server_tests.ServerTests.setUp;close=server_tests.ServerTests.close;request=server_tests.ServerTests.request
    def finish(self):
        deadline=time.monotonic()+3
        while self.app.task['running'] and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(self.app.task['running'])
    def test_routes_limit_automatic_but_allow_explicit_manual_refresh(self):
        self.app.store.add_character(1,'Pilot');self.app.eve.sync_pi=Mock(return_value=[{'id':1,'ok':True}])
        self.request('/api/pi/sync',{});self.finish();self.app.eve.sync_pi.assert_called_once()
        self.request('/api/pi/sync',{});self.finish();self.app.eve.sync_pi.assert_called_once()
        self.request('/api/pi/sync',{'manual':True});self.finish();self.assertEqual(self.app.eve.sync_pi.call_count,2)
        self.app.eve.sync=Mock(return_value=[]);self.app.eve.sync_skills=Mock(return_value=[])
        self.request('/api/notifications/sync',{});self.finish()
        self.assertEqual(self.app.eve.sync_pi.call_count,2)
        self.app.eve.sync.assert_called_once();self.app.eve.sync_skills.assert_called_once()
        self.request('/api/notifications/sync',{});self.finish();self.app.eve.sync.assert_called_once()
    def test_corporation_toggle_validates_auth_and_preserves_cached_data(self):
        self.app.store.add_character(1,'Pilot');self.app.store.character_corporation(1,99,'Corp')
        snap={'data':[],'fetched':1000,'expires':2000,'etag':None}
        self.app.store.save_corporation_snapshots(99,1,{'assets':snap})
        self.assertEqual(self.request('/api/corporations/monitoring',{'id':99,'enabled':False},Origin='https://invalid.example')[0],403)
        self.assertEqual(self.request('/api/corporations/monitoring',{'id':99,'enabled':'false'})[0],400)
        status,result,_=self.request('/api/corporations/monitoring',{'id':99,'enabled':False})
        self.assertEqual(status,200);self.assertFalse(result['corporations'][0]['monitoring_enabled'])
        self.assertEqual(self.app.store.corporation_snapshot(99,'assets')['data'],[])
