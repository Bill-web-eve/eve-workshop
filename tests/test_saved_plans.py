import concurrent.futures
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from muhely.server import App, Server

ROOT=Path(__file__).resolve().parents[1]


class SavedPlanApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.app=App(self.tmp.name,ROOT/'data/catalog.sqlite3',port=0)
        self.server=Server(self.app)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close)
        self.app.store.save_mapping('inventory',{34:{'quantity':100}})

    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2)

    def request(self,path,body=None):
        c=http.client.HTTPConnection('127.0.0.1',self.app.port,timeout=10)
        headers={'Cookie':'eve_session='+self.app.cookie}
        if body is not None:headers.update({'Content-Type':'application/json','Origin':self.app.origin,'X-CSRF-Token':self.app.csrf})
        c.request('GET' if body is None else 'POST',path,body=None if body is None else json.dumps(body),headers=headers)
        response=c.getresponse();result=json.loads(response.read());status=response.status;c.close()
        return status,result

    def save(self,product=590,quantity=1,plan_id=None):
        status,result=self.request('/api/plans/save',{'id':plan_id,'product_id':product,'quantity':quantity})
        self.assertEqual(status,200,result)
        return result['id']

    def plan(self,product=590,quantity=1,owner=None):
        path=f'/api/plan?product_id={product}&quantity={quantity}'
        if owner:path+='&saved_plan_id='+owner
        status,p=self.request(path);self.assertEqual(status,200,p)
        return p

    @staticmethod
    def row(plan,tid):return next(r for r in plan['rows'] if r['id']==tid)
    def plans(self):return self.request('/api/state')[1]['plans']

    def test_save_reserves_stock_for_owner_and_excludes_it_from_another_ship(self):
        a=self.save()
        saved=self.plans()[0]
        self.assertTrue(saved['reserve_active'])
        self.assertEqual(next(r['stock'] for r in saved['allocation']['items'] if r['id']==34),100)
        other=self.row(self.plan(product=597),34)
        own=self.row(self.plan(owner=a),34)
        self.assertEqual((other['available'],other['plan_reserved']),(0,100))
        self.assertEqual((own['available'],own['own_reserved'],own['plan_reserved']),(100,100,0))
        self.assertEqual(own['buy'],own['required']-100)
        self.assertEqual(self.row(self.plan(),34)['available'],0)  # Same product is still a different draft.

    def test_update_keeps_id_and_previews_quantity_without_writing_on_get(self):
        a=self.save();old=self.plans()[0]
        preview=self.plan(quantity=2,owner=a)
        self.assertTrue(preview['saved_plan']['preview_changed'])
        self.assertEqual(self.plans()[0]['quantity'],1)
        self.assertEqual(self.save(quantity=2,plan_id=a),a)
        updated=self.plans()
        self.assertEqual(len(updated),1)
        self.assertEqual((updated[0]['quantity'],updated[0]['reserved_at']),(2,old['reserved_at']))
        self.assertFalse(self.plan(quantity=2,owner=a)['saved_plan']['preview_changed'])

    def test_release_resume_and_delete_free_and_redistribute_stock(self):
        a=self.save();b=self.save(product=597)
        self.assertEqual(self.request('/api/plans/reservation',{'id':a,'active':False})[0],200)
        self.assertEqual(self.row(self.plan(product=597,owner=b),34)['own_reserved'],100)
        self.request('/api/plans/reservation',{'id':a,'active':True})
        self.assertEqual(self.row(self.plan(owner=a),34)['own_reserved'],0)
        self.assertEqual(self.request('/api/plans/remove',{'id':b})[0],200)
        self.assertEqual(self.row(self.plan(owner=a),34)['own_reserved'],100)
        self.request('/api/plans/remove',{'id':a})
        self.assertEqual(self.row(self.plan(product=597),34)['available'],100)

    def test_quantity_preview_includes_priority_effect_on_later_plans(self):
        self.app.store.save_mapping('inventory',{34:{'quantity':30000}})
        a=self.save();b=self.save(product=597)
        before=next(p for p in self.plans() if p['id']==b)['allocation']['items']
        self.assertGreater(next(r['stock'] for r in before if r['id']==34),0)
        preview=self.row(self.plan(quantity=2,owner=a),34)
        self.assertEqual(preview['own_reserved'],30000)
        self.assertEqual(next(p for p in self.plans() if p['id']==a)['quantity'],1)
        self.save(quantity=2,plan_id=a)
        after=self.row(self.plan(quantity=2,owner=a),34)
        self.assertEqual([preview[k] for k in ['required','available','buy','own_reserved']],
                         [after[k] for k in ['required','available','buy','own_reserved']])
        self.assertEqual(next(p for p in self.plans() if p['id']==b)['allocation']['items'],[])

    def test_invalid_update_and_wrong_owner_target_do_not_change_saved_plan(self):
        a=self.save();before=self.plans()
        for patch in [{'id':a,'product_id':590,'quantity':0},
                      {'id':'missing','product_id':590,'quantity':1},
                      {'id':a,'product_id':597,'quantity':1}]:
            self.assertEqual(self.request('/api/plans/save',patch)[0],400)
        self.assertEqual(self.request(f'/api/plan?product_id=597&saved_plan_id={a}')[0],400)
        self.assertEqual(self.request('/api/plans/reservation',{'id':a,'active':'true'})[0],400)
        self.assertEqual(self.plans(),before)

    def test_saved_reservations_survive_app_restart(self):
        a=self.save()
        reloaded=App(self.tmp.name,ROOT/'data/catalog.sqlite3',port=0)
        self.assertTrue(reloaded.store.plans()[0]['reserve_active'])
        self.assertEqual(self.row(reloaded.plan(597,1),34)['available'],0)
        self.assertEqual(self.row(reloaded.plan(590,1,a),34)['own_reserved'],100)

    def test_wip_reservation_transfers_to_delivered_stock(self):
        now=time.time();self.app.store.add_character(123,'Test')
        job={'job_id':1,'product_type_id':590,'blueprint_type_id':self.app.catalog.recipes[590]['bp_id'],
             'activity_id':1,'status':'active','runs':2,'output_location_id':6001}
        parts={k:{'data':[],'fetched':now,'expires':now+300} for k in ['assets','blueprints','jobs']}
        parts['jobs']['data']=[job]
        self.app.store.save_snapshots(123,parts)
        self.request('/api/settings',{'source':'eve'})
        a=self.save(quantity=2)
        own=self.row(self.plan(quantity=2,owner=a),590)
        self.assertEqual((own['wip'],own['own_wip_reserved'],own['runs']),(2,2,0))
        other=self.row(self.plan(),590)
        self.assertEqual((other['wip'],other['plan_wip_reserved'],other['runs']),(0,2,1))
        parts['jobs']['data']=[{**job,'status':'delivered'}]
        parts['assets']['data']=[{'item_id':999,'type_id':590,'quantity':2,'location_id':6001}]
        self.app.store.save_snapshots(123,parts)
        own=self.row(self.plan(quantity=2,owner=a),590)
        self.assertEqual((own['own_reserved'],own['own_wip_reserved'],own['runs']),(2,0,0))
        self.assertEqual(self.row(self.plan(),590)['available'],0)

    def test_parallel_saves_never_reserve_the_same_stock_twice(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda tid:self.request('/api/plans/save',{'product_id':tid,'quantity':1}),[590,597]))
        self.assertEqual([s for s,_ in results],[200,200])
        reserved=sum(r['stock'] for p in self.plans() for r in p['allocation']['items'] if r['id']==34)
        self.assertEqual(reserved,100)

    def test_existing_redeemer_fleet_can_be_kept_while_building_three_more(self):
        now=time.time();self.app.store.add_character(123,'Test')
        parts={k:{'data':[],'fetched':now,'expires':now+300} for k in ['assets','blueprints','jobs']}
        parts['assets']['data']=[{'item_id':99,'type_id':22428,'quantity':3,'location_id':6001},
                                 {'item_id':100,'type_id':23757,'quantity':1,'location_id':6001},
                                 {'item_id':101,'type_id':16672,'quantity':10000,'location_id':6001}]
        self.app.store.save_snapshots(123,parts)
        self.request('/api/settings',{'source':'eve'})
        salvation=self.save(product=92822)
        before=self.plan(product=92822,owner=salvation)['summary']
        redeemer=self.save(product=22428,quantity=3)
        self.assertEqual(self.plan(product=22428,quantity=3,owner=redeemer)['queue'],[])
        self.assertEqual(self.request('/api/inventory',{'22428':{'reserved':3}})[0],200)
        own=self.plan(product=22428,quantity=3,owner=redeemer)
        target=self.row(own,22428)
        self.assertEqual((target['on_hand'],target['manual_reserved'],target['available'],target['runs']),(3,3,0,3))
        self.assertTrue(own['shopping'])
        self.assertGreater(self.row(own,16672)['plan_reserved'],0)
        self.assertEqual(self.plan(product=92822,owner=salvation)['summary'],before)
        parts['jobs']['data']=[{'job_id':1,'product_type_id':22428,'blueprint_type_id':
            self.app.catalog.recipes[22428]['bp_id'],'activity_id':1,'status':'active',
            'runs':1,'output_location_id':6001}]
        self.app.store.save_snapshots(123,parts)
        self.assertEqual(self.row(self.plan(product=22428,quantity=3,owner=redeemer),22428)['runs'],2)
        parts['jobs']['data'][0]['status']='delivered'
        parts['assets']['data'][0]['quantity']=4
        self.app.store.save_snapshots(123,parts)
        target=self.row(self.plan(product=22428,quantity=3,owner=redeemer),22428)
        self.assertEqual((target['available'],target['own_reserved'],target['runs']),(1,1,2))
        parts['assets']['data'][0]['quantity']=6
        self.app.store.save_snapshots(123,parts)
        self.assertEqual(self.plan(product=22428,quantity=3,owner=redeemer)['queue'],[])
        self.assertEqual(self.row(self.plan(product=22428,quantity=3),22428)['runs'],3)
        restarted=App(self.tmp.name,ROOT/'data/catalog.sqlite3',port=0)
        self.assertEqual(restarted.store.mapping('inventory')[22428]['reserved'],3)

    def test_combined_shopping_sums_owned_plan_shortages_with_shared_stock_once(self):
        a=self.save();b=self.save(product=597)
        before=self.plans()
        status,combined=self.request('/api/plans/shopping');self.assertEqual(status,200)
        expected={}
        for tid,owner in [(590,a),(597,b)]:
            for row in self.plan(product=tid,owner=owner)['shopping']:
                expected[row['id']]=expected.get(row['id'],0)+row['buy']
        self.assertEqual({r['id']:r['buy'] for r in combined['rows']},expected)
        mineral=next(r for r in combined['rows'] if r['id']==34)
        self.assertEqual(sum(p['buy'] for p in mineral['plans']),mineral['buy'])
        no_stock=App(self.tmp.name,ROOT/'data/catalog.sqlite3',port=0)
        no_stock.store.save_mapping('inventory',{34:{'quantity':0}})
        without=no_stock.shopping_summary()
        self.assertEqual(next(r['buy'] for r in without['rows'] if r['id']==34)-mineral['buy'],100)
        no_stock.store.save_mapping('inventory',{34:{'quantity':100}})
        self.assertEqual(self.plans(),before)
        self.assertEqual(combined['plans'][0]['id'],a)

    def test_combined_unreserved_plan_uses_leftovers_without_persisting_reservations(self):
        a=self.save();b=self.save(product=597)
        self.request('/api/plans/reservation',{'id':a,'active':False})
        before=self.plans()
        combined=self.request('/api/plans/shopping')[1]
        self.assertEqual([p['id'] for p in combined['plans']],[b,a])
        self.assertFalse(combined['plans'][1]['reserve_active'])
        mineral=next(r for r in combined['rows'] if r['id']==34)
        self.assertEqual(mineral['used_stock'],100)
        self.assertEqual(self.plans(),before)
        # Deleting a plan immediately removes its contribution.
        self.request('/api/plans/remove',{'id':a})
        self.assertEqual([p['id'] for p in self.request('/api/plans/shopping')[1]['plans']],[b])

    def test_combined_finished_archon_prunes_its_exclusive_inputs_and_wip_counts_once(self):
        now=time.time();self.app.store.add_character(123,'Pilot')
        parts={k:{'data':[],'fetched':now,'expires':now+300} for k in ['assets','blueprints','jobs']}
        parts['assets']['data']=[{'item_id':99,'type_id':23757,'quantity':1,'location_id':6001}]
        self.app.store.save_snapshots(123,parts);self.request('/api/settings',{'source':'eve'})
        a=self.save(product=92822);b=self.save(product=22428)
        result=self.request('/api/plans/shopping')[1]
        expected={}
        for tid,owner in [(92822,a),(22428,b)]:
            for row in self.plan(product=tid,owner=owner)['shopping']:
                expected[row['id']]=max(expected.get(row['id'],0),row['buy']) if row['category']=='Reakcióformula' else expected.get(row['id'],0)+row['buy']
        self.assertEqual({r['id']:r['buy'] for r in result['rows']},expected)
        salvation=self.plan(product=92822,owner=a)
        self.assertEqual(self.row(salvation,23757)['runs'],0)
        self.assertEqual(self.row(salvation,21025)['required'],0)
        job={'job_id':99,'product_type_id':590,'blueprint_type_id':self.app.catalog.recipes[590]['bp_id'],
             'activity_id':1,'status':'active','runs':1,'output_location_id':6001}
        parts['jobs']['data']=[job];self.app.store.save_snapshots(123,parts)
        c=self.save(product=590);d=self.save(product=590)
        all_result=self.request('/api/plans/shopping')[1]
        self.assertEqual(self.row(self.plan(product=590,owner=c),590)['runs'],0)
        self.assertEqual(self.row(self.plan(product=590,owner=d),590)['runs'],1)
        self.assertEqual(len(all_result['plans']),4)

    def test_combined_empty_does_not_require_live_connection_and_endpoint_is_private(self):
        self.request('/api/settings',{'source':'eve'})
        status,result=self.request('/api/plans/shopping')
        self.assertEqual(status,200);self.assertEqual(result['rows'],[]);self.assertEqual(result['plans'],[])
        c=http.client.HTTPConnection('127.0.0.1',self.app.port);c.request('GET','/api/plans/shopping')
        response=c.getresponse();self.assertEqual(response.status,403);response.read();c.close()

    def test_invalid_active_recipe_blocks_planning_but_can_be_released(self):
        a=self.save()
        with self.app.store.db() as db:db.execute('UPDATE plans SET product_id=999999999 WHERE id=?',(a,))
        status,state=self.request('/api/state')
        self.assertEqual(status,200);self.assertTrue(state['reservation_error'])
        self.assertEqual(self.request('/api/plan?product_id=597&quantity=1')[0],400)
        self.assertEqual(self.request('/api/plans/reservation',{'id':a,'active':False})[0],200)
        self.assertIsNone(self.request('/api/state')[1]['reservation_error'])
        self.assertEqual(self.row(self.plan(product=597),34)['available'],100)


if __name__=='__main__':unittest.main()
