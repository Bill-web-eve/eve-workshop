import copy
import tempfile
import unittest
from muhely.accounts import load,save,apply_tracking,dashboard
from muhely.store import Store
from muhely.planner import PlanningError

NOW=1800000000
def account(**patch):return dict(id='one',name='Account 1',omega_status='omega',omega_expires=NOW+10*86400,mct1_expires=NOW+86400,mct2_expires=None,**patch)
def row(cid,current=None,sp=10000000,**patch):
    return dict(id=cid,name=str(cid),current=current,status='training' if current else 'idle',label='x',stale=False,total_sp=sp,stops_at=NOW+10*86400,seconds_left=10*86400,**patch)

class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
        for cid in range(1,5):self.store.add_character(cid,str(cid))
        self.data={'accounts':[account()],'characters':{'1':{'account_id':'one','training_mode':'primary'},'2':{'account_id':'one','training_mode':'mct1'}}}
    def test_round_trip_dates_are_private_profile_metadata_not_client_defaults(self):
        self.assertEqual(load(self.store),{'accounts':[],'characters':{}})
        result=save(self.store,self.data);self.assertEqual(load(Store(self.tmp.name)),result)
        self.assertNotIn('accounts',self.store.settings())
    def test_validation_is_atomic_and_account_limit_is_three(self):
        save(self.store,self.data)
        for invalid in [dict(self.data,accounts=[dict(account(),omega_expires=float('nan'))]),dict(self.data,characters={str(i):{'account_id':'one','training_mode':'auto'} for i in range(1,5)}),dict(self.data,characters={'1':{'account_id':'missing'}}),dict(self.data,characters={'1':{'account_id':'one','training_mode':'primary'},'2':{'account_id':'one','training_mode':'primary'}})]:
            with self.subTest(invalid=invalid),self.assertRaises(PlanningError):save(self.store,invalid)
            self.assertEqual(load(self.store),self.data)
    def test_expired_mct_and_manual_exclusion_never_trigger_idle_alarm(self):
        data=copy.deepcopy(self.data);data['accounts'][0]['mct1_expires']=NOW-1
        data['characters']['3']={'account_id':None,'training_mode':'disabled'}
        rows=[row(1,{'id':1}),row(2),row(3)];apply_tracking(rows,data,NOW)
        self.assertEqual([r['status'] for r in rows],['training','excluded','excluded'])
    def test_alpha_below_sp_cap_can_train_but_over_cap_is_excluded(self):
        data=copy.deepcopy(self.data);data['accounts'][0]['omega_status']='alpha'
        rows=[row(1,sp=4999999),row(2,sp=5000000)];apply_tracking(rows,data,NOW)
        self.assertEqual(rows[0]['status'],'idle');self.assertEqual(rows[1]['status'],'excluded')
    def test_expiry_caps_an_active_queue_and_reminds_per_account(self):
        save(self.store,self.data);rows=[row(1,{'id':1}),row(2,{'id':2})];apply_tracking(rows,self.data,NOW)
        self.assertEqual(rows[1]['stops_at'],NOW+86400);self.assertEqual(rows[1]['status'],'soon')
        self.assertEqual(dashboard(self.store,NOW)['expiring'][0]['kind'],'MCT 1')
    def test_automatic_idle_is_suppressed_when_other_character_uses_only_slot(self):
        data=copy.deepcopy(self.data);data['accounts'][0]['mct1_expires']=None;data['characters']['2']['training_mode']='auto'
        rows=[row(1,{'id':1}),row(2)];apply_tracking(rows,data,NOW)
        self.assertEqual(rows[1]['status'],'excluded')
    def test_unknown_accounts_do_not_silently_suppress_real_idle(self):
        rows=[row(1)];apply_tracking(rows,{'accounts':[],'characters':{}},NOW)
        self.assertEqual(rows[0]['status'],'idle');self.assertEqual(rows[0]['training_eligibility'],'unknown')
