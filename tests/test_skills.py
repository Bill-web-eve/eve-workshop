from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest

from muhely.esi import EsiError
from muhely.skills import FIVE_DAYS,character_view,dashboard,validate_resource
from muhely.store import Store

NOW=1800000000
def iso(value):return datetime.fromtimestamp(value,timezone.utc).isoformat()
def entry(position=0,start=-1,end=10*86400,**patch):
    result={'skill_id':1,'finished_level':3,'queue_position':position,
            'start_date':iso(NOW+start),'finish_date':iso(NOW+end)}
    result.update(patch);return result
def snapshot(data,checked=NOW):return {'data':data,'fetched':checked,'expires':NOW+60,'etag':None}
def skill_data():return {'skills':[{'skill_id':1,'trained_skill_level':2,'active_skill_level':1,'skillpoints_in_skill':100}],'total_sp':100,'unallocated_sp':20}


class SkillViewTests(unittest.TestCase):
    def view(self,queue,skills=None,status=None,checked=NOW):
        return character_view({'id':123,'name':'Pilot'},snapshot(skills or skill_data(),checked),
                              snapshot(queue,checked),status or {'needs_auth':0},lambda i:'Skill '+str(i),NOW)

    def test_active_long_queue_is_healthy_and_identifies_current_skill(self):
        r=self.view([entry()]);self.assertEqual((r['status'],r['current']['id'],r['queue_count']),('training',1,1))
        self.assertEqual(r['seconds_left'],10*86400)

    def test_empty_paused_and_finished_queues_are_idle(self):
        for queue in [[],[{'skill_id':1,'finished_level':3,'queue_position':0}],
                      [entry(start=-100,end=-1)]]:
            with self.subTest(queue=queue):self.assertEqual(self.view(queue)['status'],'idle')

    def test_five_day_boundary_is_inclusive_and_not_just_current_skill_length(self):
        for end,status in [(60,'soon'),(FIVE_DAYS,'soon'),(FIVE_DAYS+1,'training')]:
            self.assertEqual(self.view([entry(end=end)])['status'],status)
        r=self.view([entry(end=86400),entry(1,start=86400,end=7*86400,finished_level=4)])
        self.assertEqual(r['status'],'training');self.assertEqual(r['stops_at'],NOW+7*86400)

    def test_gap_with_later_skills_warns_at_first_interruption(self):
        r=self.view([entry(end=3*86400),entry(1,start=4*86400,end=20*86400,finished_level=4)])
        self.assertEqual((r['status'],r['stops_at'],r['queue_end'],r['gap']),
                         ('soon',NOW+3*86400,NOW+20*86400,True))

    def test_started_skill_without_an_end_is_paused_but_missing_start_is_unknown(self):
        self.assertEqual(self.view([entry(finish_date=None)])['status'],'idle')
        self.assertEqual(self.view([entry(start_date=None)])['status'],'unknown')
        self.assertEqual(self.view([entry(start=100,end=200)])['status'],'idle')

    def test_old_failed_or_unauthorized_data_never_claims_character_is_idle(self):
        for status,checked in [({'needs_auth':1},NOW),({'needs_auth':0,'error':'Offline'},NOW),
                               ({'needs_auth':0},NOW-1200)]:
            r=self.view([],status=status,checked=checked)
            self.assertEqual(r['status'],'unknown');self.assertEqual(r['training_status'],'idle')
        fresh=self.view([]);self.assertEqual(fresh['status'],'idle')

    def test_completed_entries_update_trained_level_and_sp_once_without_guessing_active_level(self):
        queue=[entry(start=-100,end=-1,finished_level=3,level_end_sp=200),
               entry(1,start=0,end=1000,finished_level=4)]
        r=self.view(queue);skill=r['skills'][0]
        self.assertEqual((skill['trained_level'],skill['active_level'],skill['sp'],r['total_sp']),(3,1,200,200))
        self.assertTrue(skill['queue_adjusted']);self.assertEqual((r['queue_count'],r['completed_count']),(1,1))
        data=skill_data();data['total_sp']=200;data['skills'][0].update(trained_skill_level=3,skillpoints_in_skill=200)
        self.assertEqual(self.view(queue,skills=data)['total_sp'],200)

    def test_bad_records_are_rejected_and_no_cache_response_is_still_fresh(self):
        for data in [[entry(finish_date='nonsense')],[entry(),entry()],
                     [entry(start=10,end=1)],[entry(finished_level=6)]]:
            with self.subTest(data=data),self.assertRaises(EsiError):validate_resource('skillqueue',data)
        r=character_view({'id':1,'name':'Pilot'},dict(snapshot(skill_data()),expires=NOW),
                         dict(snapshot([]),expires=NOW),{'needs_auth':0},str,NOW)
        self.assertEqual(r['status'],'idle');self.assertFalse(r['stale'])

    def test_missing_data_and_overlapping_active_entries_are_unknown(self):
        r=character_view({'id':1,'name':'Pilot'},None,None,None,str,NOW)
        self.assertEqual(r['status'],'unknown');self.assertTrue(r['needs_auth'])
        self.assertEqual(self.view([entry(),entry(1,finished_level=4)])['status'],'unknown')

    def test_dashboard_includes_all_characters_ignores_industry_filters_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);store.save_settings({'character_ids':[1],'location_ids':[6001]})
            for char_id in [1,2]:
                store.add_character(char_id,'Pilot '+str(char_id))
                store.save_snapshots(char_id,{'skills':snapshot(skill_data()),'skillqueue':snapshot([] if char_id==1 else [entry()])},domain='skills')
            class Catalog:
                name=staticmethod(str)
            r=dashboard(Store(folder),Catalog(),NOW)
            self.assertEqual({c['id'] for c in r['characters']},{1,2})
            self.assertEqual(r['summary'],{'idle':1,'soon':0,'training':1,'unknown':0,'excluded':0})
            store.forget_character(1)
            self.assertIsNone(store.resource_status(1,'skills'))
            self.assertIsNone(store.snapshot(1,'skills'))


if __name__=='__main__':unittest.main()
