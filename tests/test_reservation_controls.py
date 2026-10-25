"""Reservation controls preserve saved goals and change one pool atomically."""
import copy,time,unittest
from datetime import datetime,timezone
from muhely.planner import PlanningError
from muhely.reservations import ordered_active,revision,reorder
import test_server as server_tests

class ReservationControlTests(unittest.TestCase):
    setUp=server_tests.ServerTests.setUp;close=server_tests.ServerTests.close;request=server_tests.ServerTests.request
    def goals(self,count=3):
        result=[]
        for i in range(count):
            status,data,_=self.request('/api/plans/save',{'product_id':590,'quantity':1,'name':'Plan '+str(i+1)})
            self.assertEqual(status,200);result.append(data['id'])
        return result
    def rows(self):
        with self.app.store.db() as db:return [tuple(r) for r in db.execute('SELECT * FROM plans ORDER BY id')]
    def test_reorder_changes_stock_and_wip_priority_without_deleting_or_overbooking(self):
        self.request('/api/inventory',{'590':{'quantity':1,'wip':1}});ids=self.goals();state=self.request('/api/state')[1]
        before={p['id']:{k:p[k] for k in ['name','product_id','quantity','reserve_active','created','corporation_id','manufacturer_id']} for p in self.app.store.plans()}
        with self.app.store.db() as db:db.execute('UPDATE plans SET saved_inputs=? WHERE id=?',('retained',ids[0]))
        status,data,_=self.request('/api/plans/reservations/order',{'corporation_id':None,'ids':list(reversed(ids)),'revision':state['reservation_revision']})
        self.assertEqual(status,200);self.assertTrue(data['ok'])
        after=self.request('/api/state')[1];plans={p['id']:p for p in after['plans']}
        self.assertEqual([p['id'] for p in ordered_active(self.app.store.plans())],list(reversed(ids)))
        held={pid:next((i for i in plans[pid]['allocation']['items'] if i['id']==590),{'stock':0,'wip':0}) for pid in ids}
        self.assertEqual((held[ids[2]]['stock'],held[ids[1]]['wip'],held[ids[0]]['stock']+held[ids[0]]['wip']),(1,1,0))
        self.assertEqual(sum(i['stock'] for i in held.values()),1);self.assertEqual(sum(i['wip'] for i in held.values()),1)
        self.assertEqual(before,{p['id']:{k:p[k] for k in before[p['id']]} for p in self.app.store.plans()})
        with self.app.store.db() as db:self.assertEqual(db.execute('SELECT saved_inputs FROM plans WHERE id=?',(ids[0],)).fetchone()[0],'retained')
        self.assertEqual(after['reservation_revision'],data['revision'])
    def test_switch_off_retains_plan_edit_stays_off_and_reactivation_appends(self):
        ids=self.goals();state=self.request('/api/state')[1]
        self.assertEqual(self.request('/api/plans/reservation',{'id':ids[0],'active':False,'revision':state['reservation_revision']})[0],200)
        self.assertEqual(len(self.app.store.plans()),3)
        status,data,_=self.request('/api/plans/save',{'id':ids[0],'product_id':590,'quantity':5,'name':'Retained plan'})
        self.assertEqual(status,200);self.assertIsNone(data['allocation'])
        edited=next(p for p in self.app.store.plans() if p['id']==ids[0]);self.assertFalse(edited['reserve_active']);self.assertIsNone(edited['reserved_at']);self.assertEqual(edited['quantity'],5)
        state=self.request('/api/state')[1];self.assertEqual(self.request('/api/plans/reservation',{'id':ids[0],'active':True,'revision':state['reservation_revision']})[0],200)
        self.assertEqual([p['id'] for p in ordered_active(self.app.store.plans())],[ids[1],ids[2],ids[0]])
    def test_stale_incomplete_duplicate_or_foreign_order_never_partially_changes_plans(self):
        ids=self.goals();state=self.request('/api/state')[1];before=self.rows()
        for order in [ids[:2],[ids[0],ids[0],ids[2]],[ids[0],ids[1],'foreign'],[True,ids[1],ids[2]],None]:
            self.assertEqual(self.request('/api/plans/reservations/order',{'corporation_id':None,'ids':order,'revision':state['reservation_revision']})[0],400)
            self.assertEqual(self.rows(),before)
        self.assertEqual(self.request('/api/plans/reservations/order',{'corporation_id':None,'ids':ids,'revision':'old'})[0],400);self.assertEqual(self.rows(),before)
        self.assertEqual(self.request('/api/plans/reservation',{'id':ids[0],'active':False,'revision':'old'})[0],400);self.assertEqual(self.rows(),before)
        self.assertEqual(self.request('/api/plans/reservations/order',{'corporation_id':None,'ids':ids,'revision':state['reservation_revision']},Origin='https://other.invalid')[0],403)
        # Verify the commit transaction rechecks after an intervening edit.
        plans=self.app.store.plans();proposal=reorder(plans,list(reversed(ids)),None,state['reservation_revision'])
        self.app.store.save_plan({**plans[0],'quantity':2});latest=self.rows()
        with self.assertRaises(PlanningError):self.app.store.save_reservation_order(None,state['reservation_revision'],proposal)
        self.assertEqual(self.rows(),latest)
    def test_personal_order_keeps_corporation_priority_and_data_unchanged(self):
        ids=self.goals(2);self.app.store.add_character(123,'Corp pilot');self.app.store.character_corporation(123,99,'Separate Corp')
        now=time.time();self.app.store.save_corporation_snapshots(99,123,{k:{'data':[],'fetched':now,'expires':now+3600} for k in ['assets','blueprints','jobs']})
        corp=[]
        for _ in range(2):
            status,data,_=self.request('/api/plans/save',{'product_id':590,'quantity':1,'corporation_id':99});self.assertEqual(status,200);corp.append(data['id'])
        before=[copy.deepcopy(p) for p in self.app.store.plans() if p['corporation_id']==99]
        state=self.request('/api/state')[1]
        self.assertEqual(self.request('/api/plans/reservations/order',{'corporation_id':None,'ids':list(reversed(ids)),'revision':state['reservation_revision']})[0],200)
        self.assertEqual([p for p in self.app.store.plans() if p['corporation_id']==99],before)
        state=self.request('/api/state?corporation_id=99')[1]
        self.assertEqual(self.request('/api/plans/reservations/order',{'corporation_id':99,'ids':corp+ids,'revision':state['reservation_revision']})[0],400)
        self.assertEqual(self.request('/api/plans/reservations/order',{'corporation_id':99,'ids':list(reversed(corp)),'revision':state['reservation_revision']})[0],200)
        self.assertEqual([p['id'] for p in ordered_active([p for p in self.app.store.plans() if p['corporation_id']==99])],list(reversed(corp)))
    def test_inventory_wait_allows_release_but_rejects_priority_or_activation_changes(self):
        ids=self.goals(2);self.app.store.add_character(123,'Pilot');now=time.time();recipe=self.app.catalog.recipes[590]
        parts={k:{'data':[],'fetched':now-300,'expires':now+3600} for k in ['assets','blueprints','jobs']}
        parts['jobs']['data']=[{'job_id':1,'product_type_id':590,'blueprint_type_id':recipe['bp_id'],'activity_id':1,'status':'delivered','runs':1,'output_location_id':6001,'completed_date':datetime.fromtimestamp(now-10,timezone.utc).isoformat()}]
        self.app.store.save_snapshots(123,parts);self.app.store.save_settings({'source':'eve'})
        state=self.request('/api/state')[1];self.assertTrue(state['delivery_wait']);before=self.rows()
        self.assertEqual(self.request('/api/plans/reservations/order',{'corporation_id':None,'ids':list(reversed(ids)),'revision':state['reservation_revision']})[0],400);self.assertEqual(self.rows(),before)
        self.assertEqual(self.request('/api/plans/reservation',{'id':ids[0],'active':False,'revision':state['reservation_revision']})[0],200)
        state=self.request('/api/state')[1];before=self.rows()
        self.assertEqual(self.request('/api/plans/reservation',{'id':ids[0],'active':True,'revision':state['reservation_revision']})[0],400);self.assertEqual(self.rows(),before)
        self.assertEqual(self.request('/reservations.js')[0],200)

class PriorityTieTests(unittest.TestCase):
    def test_reordering_moves_the_single_owned_bpc_run_without_allocating_it_twice(self):
        from test_reservations import Catalog,saved
        from muhely.planner import Planner
        from muhely.store import DEFAULT_SETTINGS
        from muhely.reservations import allocate_plans
        planner=Planner(Catalog());settings=copy.deepcopy(DEFAULT_SETTINGS)
        bp={'item_id':444,'type_id':1100,'runs':1,'quantity':-2,'material_efficiency':0,'time_efficiency':0}
        def calculate(product,quantity,held):return planner.calculate(product,quantity,settings,stock={200:100,201:100},blueprints=[bp],reservations=held)
        plans=[saved('a'),saved('b',order=2)]
        before=allocate_plans(plans,calculate);self.assertEqual(sum(u['runs'] for u in before['by_plan']['a']['blueprint_usage']),1)
        after=allocate_plans(reorder(plans,['b','a'],None,revision(plans)),calculate)
        self.assertEqual(sum(u['runs'] for u in after['by_plan']['b']['blueprint_usage']),1)
        self.assertEqual(sum(u['runs'] for p in after['by_plan'].values() for u in p['blueprint_usage']),1)

    def test_duplicate_legacy_timestamps_reorder_exactly_and_remain_before_new_activation(self):
        rows=[{'id':n,'product_id':590,'quantity':1,'created':100,'reserved_at':100,'reserve_active':True} for n in ['a','b','c']]
        result=reorder(rows,['c','b','a'],None,revision(rows))
        self.assertEqual([p['id'] for p in ordered_active(result)],['c','b','a'])
        self.assertEqual(len({p['reserved_at'] for p in result}),3)
        self.assertTrue(all(p['reserved_at']<=time.time() for p in result))
        self.assertEqual([p['reserved_at'] for p in rows],[100,100,100])

if __name__=='__main__':unittest.main()
