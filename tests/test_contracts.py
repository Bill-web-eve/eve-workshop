from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import tempfile,threading,unittest,json
from muhely import contracts as c,notifications as n
from muhely.store import Store
from muhely.esi import EsiError,CONTRACT_SCOPES
from muhely.planner import PlanningError
NOW=1800000000
iso=lambda at:datetime.fromtimestamp(at,timezone.utc).isoformat()
def contract(rid=1,**kw):
 return dict(contract_id=rid,issuer_id=900,issuer_corporation_id=901,assignee_id=1,acceptor_id=0,type='item_exchange',status='outstanding',for_corporation=False,availability='personal',date_issued=iso(NOW+10),date_expired=iso(NOW+86400),title='A <test> contract',price=1000,**kw)
def updated(r,**kw):return dict(r,**kw)

class ContractTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.s=Store(Path(tmp.name));self.s.add_character(1,'Pilot One');self.s.add_character(2,'Pilot Two');self.s.character_corporation(1,99,'Test Corp');self.s.character_corporation(2,99,'Test Corp');c.schema(self.s)
  self.http=Mock();self.eve=SimpleNamespace(store=self.s,sync_lock=threading.Lock(),http=self.http,token=Mock(return_value='synthetic-only'),granted_scopes=lambda:{1:CONTRACT_SCOPES,2:[]})
 def put(self,rows,at=NOW,scope='personal',owner=1,provider=1):c.ingest(self.s,scope,owner,provider,{'rows':rows,'fetched':at,'expires':at+300},now=at)
 def baseline(self,**kw):self.put([],**kw)
 def events(self):return c.alerts(self.s,NOW+1000)
 def test_first_import_never_sends_historical_alerts_and_empty_baseline_is_valid(self):
  self.put([contract()]);self.assertEqual(self.events(),[])
  self.baseline(scope='corporation',owner=99);self.put([updated(contract(2),assignee_id=99)],NOW+600,scope='corporation',owner=99)
  self.assertEqual(len(self.events()),1);self.assertEqual(self.events()[0]['corporation_id'],99)
 def test_incoming_and_outgoing_acceptance_are_once_only_and_belong_to_the_right_owner(self):
  outgoing=updated(contract(2),issuer_id=1,assignee_id=777)
  self.put([outgoing]);self.put([outgoing,contract()],NOW+600)
  self.assertEqual([a['kind'] for a in self.events()],['contract_new'])
  done=updated(outgoing,status='finished',acceptor_id=777,date_accepted=iso(NOW+700),date_completed=iso(NOW+700))
  self.put([done,contract()],NOW+800);self.put([done,contract()],NOW+900)
  self.assertEqual({a['kind'] for a in self.events()},{'contract_new','contract_accepted'})
  n.save_preferences(self.s,{'os_enabled':True});data={'items':self.events(),'observed_domains':['contracts:personal:1']}
  first=n.claim(self.s,data,NOW+1000);self.assertEqual(len(first),2);n.acknowledge(self.s,[a['receipt'] for a in first]);self.assertEqual(n.claim(self.s,data,NOW+1001),[])
 def test_corporate_issuer_alias_does_not_pollute_personal_contracts(self):
  r=updated(contract(),issuer_id=1,issuer_corporation_id=99,for_corporation=True,assignee_id=0,availability='public')
  self.put([r]);self.put([r],scope='corporation',owner=99)
  self.assertEqual(c.dashboard(self.s)['rows'],[]);self.assertEqual(len(c.dashboard(self.s,'corporation')['rows']),1)
  incoming_from_corp=updated(r,contract_id=2,assignee_id=1,availability='personal')
  self.put([incoming_from_corp],NOW+600);self.assertEqual(c.dashboard(self.s)['rows'][0]['contract_id'],2)
 def test_fast_contract_issued_and_accepted_between_polls_still_notifies_issuer(self):
  self.baseline();r=updated(contract(),issuer_id=1,assignee_id=777,acceptor_id=777,status='finished',date_accepted=iso(NOW+50))
  self.put([r],NOW+600);self.assertEqual([e['kind'] for e in self.events()],['contract_accepted'])
 def test_archived_history_survives_esi_retention_and_stale_snapshots_do_not_revert_status(self):
  r=updated(contract(),issuer_id=1,assignee_id=777);self.put([r]);done=updated(r,status='in_progress',acceptor_id=777,date_accepted=iso(NOW+60))
  self.put([done],NOW+600);self.put([r],NOW+100);self.put([],NOW+40*86400)
  rows=c.dashboard(self.s)['rows'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['status'],'in_progress')
  with self.s.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM contract_history').fetchone()[0],2)
 def test_old_newly_visible_rows_and_expired_offers_do_not_trigger_new_incoming(self):
  self.baseline();self.put([updated(contract(),date_issued=iso(NOW-100)),updated(contract(2),date_expired=iso(NOW+20))],NOW+600);self.assertEqual(self.events(),[])
 def test_personal_all_characters_deduplicates_same_contract(self):
  r=updated(contract(),issuer_id=1,assignee_id=2);self.put([r]);self.put([r],NOW+1,owner=2,provider=2)
  rows=c.dashboard(self.s)['rows'];self.assertEqual(len(rows),1);self.assertEqual({o['id'] for o in rows[0]['owners']},{1,2})
  self.assertEqual(len(c.dashboard(self.s,owner='2')['rows']),1)
 def test_disabled_corporation_never_requests_corp_data_and_hides_alerts(self):
  self.baseline(scope='corporation',owner=99);self.put([updated(contract(),assignee_id=99)],NOW+600,scope='corporation',owner=99)
  self.s.set_corporation_monitoring(99,False);self.eve.granted_scopes=lambda:{1:[CONTRACT_SCOPES[1]]}
  self.assertEqual(c.sync(self.eve),[]);self.http.request.assert_not_called();self.assertEqual(self.events(),[])
  self.assertEqual(len(c.dashboard(self.s,'corporation')['rows']),1)
 def test_pagination_failure_is_atomic_and_preserves_previous_history(self):
  self.put([contract()]);self.http.request.side_effect=[([updated(contract(3),date_issued=iso(NOW+400))],{'x-pages':'2'}),EsiError('offline')]
  with patch('muhely.contracts.time.time',return_value=NOW+600):
   with self.assertRaises(EsiError):c.resource(self.eve,'personal',1,'synthetic')
  self.assertEqual([r['contract_id'] for r in c.dashboard(self.s)['rows']],[1]);self.assertEqual(self.events(),[])
 def test_duplicate_pages_and_invalid_fields_are_rejected(self):
  for rows in [[contract(),contract()],[updated(contract(),price=-1)],[updated(contract(),date_issued='bad')],[updated(contract(),status='invented')],[updated(contract(),for_corporation=1)]]:
   with self.assertRaises(EsiError):self.put(rows)
  self.assertEqual(c.dashboard(self.s)['rows'],[])
 def test_unexpired_esi_cache_avoids_network(self):
  self.put([contract()])
  with patch('muhely.contracts.time.time',return_value=NOW+10):self.assertIsNone(c.resource(self.eve,'personal',1,'synthetic'))
  self.http.request.assert_not_called()
 def test_sync_falls_back_to_another_authorized_corp_member(self):
  self.eve.granted_scopes=lambda:{1:[CONTRACT_SCOPES[1]],2:[CONTRACT_SCOPES[1]]}
  self.http.request.side_effect=[({'corporation_id':99},{}),EsiError('403'),({'corporation_id':99},{}),([],{'x-pages':'1'})]
  result=c.sync(self.eve);self.assertTrue(result[0]['ok']);self.assertEqual(c.source(self.s,'corporation',99)['provider_id'],2)
 def test_membership_change_prevents_corp_access(self):
  self.eve.granted_scopes=lambda:{1:[CONTRACT_SCOPES[1]]};self.http.request.return_value=({'corporation_id':100},{})
  self.assertFalse(c.sync(self.eve)[0]['ok']);self.assertEqual(self.http.request.call_count,1)
 def test_details_preserve_items_after_expiry_and_expose_status_history(self):
  self.put([contract()]);items=[{'record_id':1,'type_id':34,'quantity':100,'is_singleton':False,'is_included':True}]
  self.http.request.return_value=(items,{})
  first=c.details(self.eve,SimpleNamespace(name=lambda i:'Tritanium'),'personal',1,1)
  self.assertEqual(first['items'][0]['name'],'Tritanium');self.assertEqual(len(first['history']),1)
  second=c.details(self.eve,SimpleNamespace(name=lambda i:'Tritanium'),'personal',1,1);self.assertEqual(second['items'][0]['name'],'Tritanium');self.assertEqual(self.http.request.call_count,1)
  self.http.request.side_effect=EsiError('old contract unavailable')
  with patch('muhely.contracts.time.time',return_value=NOW+100000000):
   third=c.details(self.eve,SimpleNamespace(name=lambda i:'Tritanium'),'personal',1,1)
  self.assertTrue(third['items']);self.assertTrue(third['error'])
 def test_date_filter_uses_inclusive_utc_days_and_rejects_reversed_range_even_when_empty(self):
  self.put([contract()]);day=datetime.fromtimestamp(NOW+10,timezone.utc).strftime('%Y-%m-%d')
  self.assertEqual(len(c.dashboard(self.s,start=day,end=day)['rows']),1)
  with self.assertRaises(PlanningError):c.dashboard(self.s,start='2026-10-25',end='2026-10-01')
  with self.assertRaises(PlanningError):c.dashboard(self.s,'corporation',start='invalid')
 def test_disabled_corp_details_keep_archive_without_any_network_access(self):
  self.put([updated(contract(),assignee_id=99)],scope='corporation',owner=99)
  self.s.set_corporation_monitoring(99,False)
  result=c.details(self.eve,SimpleNamespace(name=lambda i:'Tritanium'),'corporation',99,1)
  self.assertTrue(result['error']);self.http.request.assert_not_called()

 def test_foreign_detail_and_invalid_owner_are_not_read(self):
  with self.assertRaises(PlanningError):c.details(self.eve,SimpleNamespace(),'personal',999,1)
  with self.assertRaises(PlanningError):c.dashboard(self.s,'corporation',owner='123')
  self.http.request.assert_not_called()

if __name__=='__main__':unittest.main()
