from pathlib import Path
import tempfile,threading,time,unittest
from unittest.mock import Mock
from muhely import progress
from muhely.store import Store
from muhely.esi import EveConnection,EsiError

class ProgressTests(unittest.TestCase):
    def test_progress_is_thread_local_nested_and_silent_after_context_exit(self):
        a=[];b=[]
        with progress.listen(a.append):
            progress.report(resource='outer')
            thread=threading.Thread(target=lambda:progress.report(resource='other thread'));thread.start();thread.join()
            with progress.listen(b.append):progress.report(resource='inner')
            progress.report(resource='restored')
        progress.report(resource='outside')
        self.assertEqual([r['resource'] for r in a],['outer','restored']);self.assertEqual([r['resource'] for r in b],['inner'])

    def test_character_resource_pagination_and_cache_progress_do_not_change_requests(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder));store.add_character(1,'Pilot One');eve=EveConnection(store);eve.token=Mock(return_value='test-token')
            store.save_snapshots(1,{'blueprints':{'data':[],'fetched':time.time(),'expires':time.time()+600,'etag':None}})
            eve.http=Mock();eve.http.request.side_effect=[([],{'X-Pages':'2'}),([],{'X-Pages':'2'}),([],{})]
            updates=[]
            with progress.listen(updates.append):result=eve.sync()
            self.assertTrue(result[0]['ok']);self.assertEqual(eve.http.request.call_count,3)
            self.assertTrue(any(r.get('subject')=='Pilot One' and r['completed']==0 and r['total']==1 for r in updates))
            self.assertTrue(any(r.get('resource')=='Blueprintok' and r['mode']=='cache' for r in updates))
            self.assertTrue(any(r.get('page')==2 and r.get('pages')==2 for r in updates));self.assertEqual(updates[-1]['completed'],1)
            self.assertNotIn('test-token',str(updates))

    def test_failed_characters_advance_checked_count_and_continue(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder));store.add_character(1,'Pilot One');store.add_character(2,'Pilot Two');eve=EveConnection(store)
            eve.token=Mock(side_effect=EsiError('No access'));updates=[]
            with progress.listen(updates.append):result=eve.sync()
            self.assertEqual([row['ok'] for row in result],[False,False]);self.assertEqual(updates[-1]['completed'],2)
