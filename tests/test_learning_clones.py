from datetime import datetime, timezone
import copy
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from muhely import learning_clones as lc, notifications
from muhely.esi import EsiError, LEARNING_CLONE_SCOPES
from muhely.store import Store

NOW=1800000000
def iso(t):return datetime.fromtimestamp(t,timezone.utc).isoformat()


class LearningCloneTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
        self.store.add_character(11,'Pilot');self.store.add_character(22,'Other')
        self.now=NOW;self.online=False;self.logout=NOW-300;self.fail_online=False;self.age=0;self.scopes={cid:list(LEARNING_CLONE_SCOPES) for cid in [11,22]};self.calls=[]
        self.active=[1,2];self.clones=[{'jump_clone_id':101,'location_id':60003760,'name':'Training clone','implants':[3,4]},
            {'jump_clone_id':102,'location_id':60003760,'name':'Wrong attributes','implants':[5]}]
        self.queue=[{'skill_id':99,'queue_position':0,'finished_level':4,'start_date':iso(NOW-600),'finish_date':iso(NOW+100000)}]
        self.types={1:{178:3},2:{179:3},3:{178:5},4:{179:5},5:{175:50},99:{180:167,181:168}}
        def request(url,**kwargs):
            self.calls.append(url);path=url.split('?')[0].rstrip('/');part=path.split('/')[-1]
            if '/universe/types/' in url and int(part) not in self.types:raise EsiError('missing metadata')
            if '/universe/types/' in url:return {'name':'Gunnery' if part=='99' else 'Implant '+part,'dogma_attributes':[{'attribute_id':k,'value':v} for k,v in self.types[int(part)].items()]},{}
            if part=='online':
                if self.fail_online:raise EsiError('online unavailable')
                body={'online':self.online,'last_logout':iso(self.logout)}
            elif part=='implants':body=self.active
            elif part=='clones':body={'jump_clones':self.clones}
            elif part=='skillqueue':body=self.queue
            else:raise AssertionError(url)
            return copy.deepcopy(body),{'Cache-Control':'max-age=120','Age':str(self.age),'ETag':'test'}
        self.eve=SimpleNamespace(http=SimpleNamespace(request=request),token=Mock(return_value='synthetic'),granted_scopes=lambda:self.scopes)
        self.watch=lc.LearningCloneWatch(self.store,self.eve,lambda:self.now);self.addCleanup(self.watch.stop)

    def alerts(self):return lc.alerts(self.store,self.now)

    def test_best_owned_clone_uses_current_skill_weights_not_total_or_price(self):
        self.watch.tick();data=self.alerts();self.assertEqual(len(data['items']),2)
        item=data['items'][0];self.assertTrue(item['reliable']);self.assertTrue(item['sound'])
        self.assertEqual((item['active_bonus'],item['best_bonus']),(4.5,7.5))
        self.assertEqual(item['best_clone_id'],101);self.assertEqual(item['skill_name'],'Gunnery')

    def test_any_online_character_suppresses_every_alert_and_skips_clone_requests(self):
        self.online=True;self.watch.tick();self.assertEqual(self.alerts()['items'],[])
        self.assertEqual(len(self.calls),2);self.assertTrue(all('/online/' in u for u in self.calls))

    def test_missing_online_scope_for_one_character_blocks_all_reliable_alerts(self):
        self.scopes[22].remove(lc.ONLINE_SCOPE);self.watch.tick()
        self.assertEqual(self.alerts()['items'],[])
        self.assertFalse(next(c for c in self.watch.dashboard()['characters'] if c['id']==22)['online_access'])
        self.assertFalse(any('/clones/' in u for u in self.calls))

    def test_equal_better_active_and_empty_queue_do_not_alert(self):
        for active,queue in [([3,4],self.queue),([3,4,2],self.queue),([1,2],[])]:
            with self.subTest(active=active,queue=queue):
                self.active=active;self.queue=queue;self.now+=901;self.watch.tick()
                self.assertEqual(self.alerts()['items'],[])

    def test_polling_is_fifteen_minutes_and_manual_keeps_valid_esi_cache(self):
        self.watch.tick();calls=len(self.calls);self.now+=10;self.watch.tick();self.assertEqual(len(self.calls),calls)
        self.watch.tick(manual=True);self.assertEqual(len(self.calls),calls)
        self.now+=130;self.watch.tick(manual=True);self.assertEqual(len(self.calls),calls+8)
        self.now+=100;self.watch.tick();self.assertEqual(len(self.calls),calls+8)

    def test_stale_online_and_stale_implants_never_create_reliable_notification(self):
        self.age=130;self.watch.tick();self.assertFalse(any(a['reliable'] for a in self.alerts()['items']))
        self.now+=901;self.age=0;self.watch.tick();self.assertEqual(len(self.alerts()['items']),2)
        self.now+=121;self.assertFalse(any(a['reliable'] for a in self.alerts()['items']))

    def test_implant_snapshot_before_last_logout_waits_for_post_logout_data(self):
        self.watch.tick()
        old=self.store.snapshot(11,'active_implants');old['fetched']=self.now-400
        self.store.save_snapshots(11,{'active_implants':old})
        self.assertEqual([a['character_id'] for a in self.alerts()['items']],[22])
        row=next(c for c in self.watch.dashboard()['characters'] if c['id']==11);self.assertEqual(row['status'],'unknown')
        self.assertIn('kijelentkezés előtti',row['error'])

    def test_failed_metadata_is_not_replaced_with_zero_bonus(self):
        self.types.pop(3);self.watch.tick();self.assertEqual(self.alerts()['items'],[])
        self.assertTrue(self.watch.dashboard()['status']['errors'])

    def test_notifications_deduplicate_restart_and_rearm_after_new_logout(self):
        notifications.save_preferences(self.store,{'os_enabled':True});self.watch.tick()
        data=self.alerts();first=notifications.claim(self.store,data,self.now);self.assertEqual(len(first),2)
        notifications.acknowledge(self.store,[a['receipt'] for a in first]);self.assertEqual(notifications.claim(self.store,data,self.now),[])
        restart=lc.LearningCloneWatch(self.store,self.eve,lambda:self.now);self.addCleanup(restart.stop)
        restart.tick();self.assertEqual(notifications.claim(self.store,self.alerts(),self.now),[])
        self.now+=901;self.logout=self.now-300;self.watch.tick();self.assertEqual(len(notifications.claim(self.store,self.alerts(),self.now)),2)

    def test_unchanged_offline_episode_is_not_sent_again_after_regular_refresh(self):
        notifications.save_preferences(self.store,{'os_enabled':True});self.watch.tick()
        first=notifications.claim(self.store,self.alerts(),self.now);notifications.acknowledge(self.store,[a['receipt'] for a in first])
        self.now+=901;self.watch.tick();self.assertEqual(notifications.claim(self.store,self.alerts(),self.now),[])

    def test_acknowledged_warning_stays_hidden_until_new_episode(self):
        self.watch.tick();data=self.alerts();items=notifications.visible_items(self.store,data['items'],data['observed_domains'],self.now)
        notifications.dismiss(self.store,{'items':items},{'id':items[0]['id'],'dismissal_key':items[0]['dismissal_key']},self.now)
        self.assertEqual(len(notifications.visible_items(self.store,self.alerts()['items'],self.alerts()['observed_domains'],self.now)),1)
        self.now+=901;self.logout=self.now-300;self.watch.tick();self.assertEqual(len(notifications.visible_items(self.store,self.alerts()['items'],self.alerts()['observed_domains'],self.now)),2)

    def test_disabled_and_stopped_monitors_make_no_requests(self):
        notifications.save_preferences(self.store,{'categories':{'learning_clones':False}});self.watch.tick();self.assertEqual(self.calls,[])
        notifications.save_preferences(self.store,{'categories':{'learning_clones':True}});self.watch.stop_event.set();self.watch.tick();self.assertEqual(self.calls,[])

    def test_manually_excluded_training_character_does_not_get_a_clone_warning(self):
        from muhely import accounts
        with self.store.db() as db:
            accounts.load(self.store)
            import json
            db.execute('INSERT OR REPLACE INTO account_tracking VALUES(1,?)',(json.dumps({'accounts':[],'characters':{'11':{'training_mode':'disabled'}}}),))
        self.watch.tick();self.assertEqual([a['character_id'] for a in self.alerts()['items']],[22])

    def test_corrupt_payload_is_rejected_before_cache_replacement(self):
        for kind,data in [('learning_online',{'online':0}),('active_implants',[1,1]),('jump_clones',{'jump_clones':[{}]})]:
            with self.subTest(kind=kind),self.assertRaises(EsiError):lc.validate(kind,data)


if __name__=='__main__':unittest.main()
