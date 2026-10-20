from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from muhely.store import Store
from muhely import notifications as n
from muhely.planner import PlanningError
NOW=1800000000
iso=lambda value:datetime.fromtimestamp(value,timezone.utc).isoformat()
snap=lambda data,old=0:{'data':data,'fetched':NOW-old,'expires':NOW+60 if not old else NOW-10,'etag':None}

def skill(cid=1,status='idle'):
    return {'id':cid,'name':'Pilot '+str(cid),'status':status,'queue_as_of':NOW,'stops_at':NOW+86400 if status=='soon' else None}
def job(jid,status='active',end=-1):
    return {'job_id':jid,'status':status,'end_date':iso(NOW+end),'product_type_id':590,'runs':2,'installer_id':1}

class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.s=Store(Path(self.tmp.name))
        self.s.add_character(1,'Pilot 1');self.s.add_character(2,'Pilot 2');self.s.character_corporation(1,99,'Corp A')
        self.s.save_corporation_snapshots(99,1,{'jobs':snap([])})
        self.sd={'characters':[]};self.pd={'characters':[],'colonies':[]};self.md={'events':[]}
        self.cat=SimpleNamespace(name=lambda tid:'Item '+str(tid),moon_locations=lambda sid:[{'id':10,'name':'Test I - Moon 1'}])
        for target,value in [('skills.dashboard',self.sd),('pi.dashboard',self.pd),('extractions.report',self.md)]:
            p=patch('muhely.notifications.'+target,return_value=value);p.start();self.addCleanup(p.stop)
        for cid in [1,2]:self.s.save_snapshots(cid,{'jobs':snap([])})
    def data(self):return n.collect(self.s,self.cat,NOW)
    def enable(self,**kw):n.save_preferences(self.s,{'os_enabled':True,**kw})
    def test_training_uses_account_filtered_status_and_never_notifies_unknown_or_excluded(self):
        self.sd['characters']=[skill(1,'idle'),skill(2,'soon'),skill(3,'excluded'),skill(4,'unknown'),skill(5,'training')]
        data=self.data();alerts=[a for a in data['items'] if a['category']=='skills']
        self.assertEqual([a['kind'] for a in alerts],['training_soon','training_idle'])
        self.enable();claims=n.claim(self.s,data,NOW);self.assertEqual(len(claims),2);self.assertTrue(all(a['corporation_id'] is None for a in claims))
        self.assertEqual(sum(a['category']=='data' for a in data['items']),1)
    def test_jobs_are_separate_and_corporate_aliases_do_not_duplicate(self):
        self.s.save_snapshots(1,{'jobs':snap([job(1),job(2,'ready'),job(3,'paused'),job(4,'delivered'),job(5,'active',100)])})
        self.s.save_corporation_snapshots(99,1,{'jobs':snap([job(2,'ready')])})
        rows=[a for a in self.data()['items'] if a['category']=='jobs']
        self.assertEqual({(a['job_id'],a['corporation_id']) for a in rows},{(1,None),(2,99)})
        self.enable(corporations=False);self.assertEqual([a['job_id'] for a in n.claim(self.s,self.data(),NOW)],[1])
    def test_stale_or_failed_job_data_are_visible_but_not_sent(self):
        self.s.save_snapshots(1,{'jobs':snap([job(1,'ready')],old=86400)})
        self.enable();data=self.data();self.assertFalse(next(a for a in data['items'] if a['category']=='jobs')['reliable']);self.assertEqual(n.claim(self.s,data,NOW),[])
    def test_pi_reports_expired_extractors_and_explicit_conditional_estimates(self):
        base={'id':10,'character_id':1,'character_name':'Pilot 1','name':'Planet','checked_at':NOW,'cached':False,'last_update':NOW-5000,'status':'unknown','extractors':[]}
        self.pd['colonies']=[{**base,'projection':{'available':True,'first_stop':NOW-50,'factories':[{'running_now':False,'products_next_period':[]}]}}]
        self.enable();rows=n.claim(self.s,self.data(),NOW);self.assertEqual(rows[0]['kind'],'pi_estimated');self.assertTrue(rows[0]['estimated'])
        self.pd['colonies'][0]['cached']=True;self.assertEqual(n.claim(self.s,self.data(),NOW),[])
        self.pd['colonies']=[{**base,'id':11,'projection':{},'extractors':[{'program_end':NOW-100}]}]
        rows=n.claim(self.s,self.data(),NOW);self.assertEqual(rows[0]['kind'],'pi_extractor')
    def test_three_day_moon_window_corp_ownership_and_stale_guards(self):
        self.s.save_moon({'id':'moon1','moon_id':10,'system_id':100,'structure':'Athanor','enabled':True,'ores':[]})
        base={'moon_record_id':'moon1','moon_name':'Moon','structure_id':50,'date':iso(NOW+3*86400),'kind':'extraction','stale':False,'checked':NOW,'corporation_id':99,'volume':1000}
        self.md['events']=[base,{**base,'structure_id':51,'date':iso(NOW+3*86400+1)}]
        rows=[a for a in self.data()['items'] if a['category']=='moons'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['corporation_id'],99)
        self.enable();self.assertEqual(len(n.claim(self.s,self.data(),NOW)),1)
        n.save_preferences(self.s,{'moon_owners':{'moon1':None}});self.assertIsNone(next(a for a in self.data()['items'] if a['category']=='moons')['corporation_id'])
        self.md['events'][0]['stale']=True;self.assertEqual(n.claim(self.s,self.data(),NOW),[])
    def test_claims_have_leases_acknowledgments_and_restart_deduplication(self):
        self.sd['characters']=[skill()];self.enable();data=self.data()
        first=n.claim(self.s,data,NOW);self.assertEqual(len(first),1);self.assertEqual(n.claim(self.s,data,NOW+1),[])
        retry=n.claim(self.s,data,NOW+121);self.assertEqual(retry[0]['notification_id'],first[0]['notification_id']);self.assertNotEqual(retry[0]['receipt'],first[0]['receipt'])
        n.acknowledge(self.s,[first[0]['receipt']]);self.assertEqual(len(n.claim(self.s,data,NOW+242)),1)
        last=n.claim(self.s,data,NOW+363);n.acknowledge(self.s,[last[0]['receipt']]);self.s=Store(Path(self.tmp.name));self.assertEqual(n.claim(self.s,data,NOW+500),[])
    def test_unknown_does_not_resolve_an_episode_but_healthy_recovery_does(self):
        self.sd['characters']=[skill()];self.enable();first=n.claim(self.s,self.data(),NOW);n.acknowledge(self.s,[first[0]['receipt']])
        self.sd['characters']=[skill(status='unknown')];n.claim(self.s,self.data(),NOW+10)
        self.sd['characters']=[skill()];self.assertEqual(n.claim(self.s,self.data(),NOW+20),[])
        self.sd['characters']=[skill(status='training')];n.claim(self.s,self.data(),NOW+30)
        self.sd['characters']=[skill()];again=n.claim(self.s,self.data(),NOW+40);self.assertNotEqual(again[0]['notification_id'],first[0]['notification_id'])
    def test_settings_are_validated_and_os_is_opt_in(self):
        self.sd['characters']=[skill()];self.assertEqual(n.claim(self.s,self.data(),NOW),[])
        for bad in [{'moon_days':0},{'moon_days':31},{'moon_days':True},{'os_enabled':1},{'categories':{'bad':True}},{'moon_owners':{'missing':99}}]:
            with self.assertRaises(PlanningError):n.save_preferences(self.s,bad)
        self.enable(categories={'skills':False});self.assertEqual(n.claim(self.s,self.data(),NOW),[])

    def test_unknown_pi_rows_keep_the_character_and_resource_identifiable(self):
        self.pd['characters']=[{'id':1,'name':'Pilot 1','status':'unknown','checked_at':NOW}]
        self.pd['colonies']=[{'id':10,'name':'Planet','character_id':2,'character_name':'Pilot 2','checked_at':NOW,'cached':True,'status':'unknown','extractors':[],'last_update':NOW}]
        rows=[a for a in self.data()['items'] if a.get('source_category')=='pi']
        self.assertEqual({a['character_name'] for a in rows},{'Pilot 1','Pilot 2'});self.assertTrue(all(not a['reliable'] for a in rows))
