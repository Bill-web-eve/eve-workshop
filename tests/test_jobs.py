from pathlib import Path
from types import SimpleNamespace
import tempfile,unittest
from muhely.store import Store
from muhely import jobs
import test_server as server_tests
NOW=1800000000

def snap(data,at=NOW):return {'data':data,'fetched':at,'expires':NOW+900,'etag':None}
def job(jid,installer=1,**kw):return {'job_id':jid,'installer_id':installer,'product_type_id':590,'blueprint_type_id':100,'activity_id':1,'status':'active','runs':3,'output_location_id':999,**kw}
cat=SimpleNamespace(name=lambda tid:{590:'Ship',100:'Ship Blueprint'}.get(tid,str(tid)),recipes={590:{'bp_id':100,'output':1,'activity':'manufacturing'}})
class JobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=Store(self.tmp.name)
        for cid,name in [(1,'Alice'),(2,'Bob')]:self.s.add_character(cid,name)
        self.s.character_corporation(1,99,'Corp A');self.s.character_corporation(2,98,'Corp B')
        self.s.save_settings({'source':'manual','character_ids':[1],'location_ids':[100]})
    def test_all_personal_jobs_ignore_plan_character_location_and_asset_filters(self):
        self.s.save_snapshots(1,{'jobs':snap([job(1),job(9,status='delivered')])})
        self.s.save_snapshots(2,{'jobs':snap([job(2,2),job(8,2,status='ready')])})
        data=jobs.dashboard(self.s,cat,now=NOW)
        self.assertEqual({r['job_id'] for r in data['rows']},{1,2,8})
        self.assertEqual({r['character_name'] for r in data['rows']},{'Alice','Bob'})
        self.assertTrue(all(r['expected_output']==3 for r in data['rows']))
        self.assertIsNone(self.s.snapshot(1,'assets'))
        self.assertEqual(self.s.settings()['character_ids'],[1])
    def test_corporation_jobs_and_aliases_never_enter_personal_list(self):
        self.s.save_snapshots(1,{'jobs':snap([job(1),job(2),job(3,corporation_id=99)])})
        self.s.save_corporation_snapshots(99,1,{'jobs':snap([job(2)])})
        self.s.set_corporation_monitoring(99,False)
        self.assertEqual([r['job_id'] for r in jobs.dashboard(self.s,cat,now=NOW)['rows']],[1])
        self.assertEqual([r['job_id'] for r in jobs.dashboard(self.s,cat,99,now=NOW)['rows']],[2])
        self.s.save_corporation_snapshots(98,2,{'jobs':snap([job(4,2)])})
        self.assertEqual([r['job_id'] for r in jobs.dashboard(self.s,cat,98,now=NOW)['rows']],[4])
    def test_newest_duplicate_status_wins_and_research_output_is_zero(self):
        self.s.save_snapshots(1,{'jobs':snap([job(1),job(2,activity_id=5)],NOW-10)})
        self.s.save_snapshots(2,{'jobs':snap([job(1,status='delivered')])})
        rows=jobs.dashboard(self.s,cat,now=NOW)['rows'];self.assertEqual([r['job_id'] for r in rows],[2]);self.assertEqual(rows[0]['expected_output'],0)
    def test_missing_and_old_job_data_are_not_claimed_to_be_fresh_empty_inventory(self):
        self.s.save_snapshots(1,{'jobs':dict(snap([]),expires=NOW-1)})
        sources={r['id']:r for r in jobs.dashboard(self.s,cat,now=NOW)['sources']}
        self.assertTrue(sources[1]['stale']);self.assertFalse(sources[2]['available'])

class JobApiTests(unittest.TestCase):
    setUp=server_tests.ServerTests.setUp;close=server_tests.ServerTests.close;request=server_tests.ServerTests.request
    def test_job_routes_are_local_authenticated_and_plan_independent(self):
        self.app.store.add_character(1,'Alice');self.app.store.add_character(2,'Bob')
        self.app.store.save_settings({'character_ids':[1],'location_ids':[100]})
        bp=self.app.catalog.recipes[590]['bp_id']
        for cid in [1,2]:self.app.store.save_snapshots(cid,{'jobs':snap([job(cid,cid,blueprint_type_id=bp)])})
        self.assertEqual(self.request('/api/jobs',Cookie='')[0],403)
        status,data,_=self.request('/api/jobs');self.assertEqual(status,200);self.assertEqual(len(data['rows']),2)
        self.assertEqual(self.request('/api/jobs?corporation_id=999')[0],400)
        self.assertEqual(self.request('/jobs.js')[0],200)
