import copy
import sqlite3
import tempfile
from pathlib import Path
import unittest

from muhely.planner import Planner, PlanningError
from muhely.reservations import allocate_plans, except_owner
from muhely.store import Store, DEFAULT_SETTINGS


class Catalog:
    def __init__(self):
        self.types={i:{'name':str(i),'group_id':0,'pi':0} for i in [100,101,110,200,201]}
        self.meta={}
        self.recipes={}
        for tid,materials in [(100,{110:2,200:3}),(101,{110:1,200:4}),(110,{200:5,201:2})]:
            self.recipes[tid]={'bp_id':tid+1000,'activity':'manufacturing','output':1,'seconds':1,
                               'copy_limit':100,'materials':[{'typeID':i,'quantity':q} for i,q in materials.items()]}
    def name(self,tid):return str(tid)


def saved(plan_id,product=100,quantity=1,order=1,active=True):
    return {'id':plan_id,'name':plan_id,'product_id':product,'quantity':quantity,
            'created':order,'reserved_at':order if active else None,'reserve_active':active}


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.planner=Planner(Catalog())
        self.settings=copy.deepcopy(DEFAULT_SETTINGS)
        for activity in ['manufacturing','reaction']:
            self.settings[activity].update(material_role=0,material_rig=0,time_role=0,time_rig=0)
        self.stock={200:20,201:20}
        self.wip={}
        self.inventory={}

    def calculate(self,product,quantity,held=None,own=None):
        return self.planner.calculate(product,quantity,self.settings,stock=self.stock,wip=self.wip,
                                      inventory=self.inventory,reservations=held,own_reservations=own)

    def allocate(self,*plans):return allocate_plans(plans,self.calculate)
    def rows(self,plan):return {r['id']:r for r in plan['rows']}

    def test_shared_material_is_unavailable_to_a_second_plan(self):
        self.stock={200:13,201:4}
        allocations=self.allocate(saved('A'))
        other,_=except_owner(allocations,None)
        second=self.rows(self.calculate(101,1,other))
        self.assertEqual((second[200]['plan_reserved'],second[200]['available'],second[200]['buy']),(13,0,9))

    def test_owner_can_use_own_allocations_without_double_deduction(self):
        a=self.allocate(saved('A'),saved('B',product=101,order=2))
        other,own=except_owner(a,'A')
        owner=self.rows(self.calculate(100,1,other,own))
        self.assertEqual((owner[200]['own_reserved'],owner[200]['plan_reserved'],owner[200]['available'],owner[200]['buy']),(13,7,13,0))
        self.assertEqual(a['totals'][200]['stock'],20)

    def test_never_reserves_nonexistent_material(self):
        self.stock={200:10,201:4}
        a=self.allocate(saved('A'),saved('B',product=101,order=2))
        self.assertEqual(a['totals'][200]['stock'],10)
        self.assertEqual([(r['id'],r['buy']) for r in a['by_plan']['A']['shopping'] if r['category']!='BPC-run'],[(200,3)])
        self.assertEqual(a['by_plan']['A']['summary']['shopping_items'],3) # Mineral and two missing BPC run capacities.
        self.assertFalse(any(r['id']==200 for r in a['by_plan']['B']['items']))

    def test_reserves_existing_component_instead_of_its_raw_materials(self):
        self.stock={110:2,200:20,201:20}
        a=self.allocate(saved('A'))
        self.assertEqual(a['totals'],{110:{'stock':2,'wip':0},200:{'stock':3,'wip':0}})

    def test_wip_is_not_promised_to_two_plans(self):
        self.wip={110:2}
        a=self.allocate(saved('A'),saved('B',product=101,order=2))
        self.assertEqual(a['totals'][110]['wip'],2)
        self.assertEqual(a['by_plan']['A']['items'][0]['id'],110)
        other,own=except_owner(a,'B')
        second=self.rows(self.calculate(101,1,other,own))
        self.assertEqual((second[110]['wip'],second[110]['plan_wip_reserved'],second[110]['runs']),(0,2,1))

    def test_finishing_a_component_releases_its_raw_reservations(self):
        before=self.allocate(saved('A'))
        self.assertEqual(before['totals'][200]['stock'],13)
        self.stock[110]=2
        after=self.allocate(saved('A'))
        self.assertEqual(after['totals'][200]['stock'],3)
        self.assertNotIn(201,after['totals'])

    def test_manual_reservations_are_additional_and_zero_overrides_remain_valid(self):
        self.inventory={200:{'reserved':2},201:{'quantity':0}}
        a=self.allocate(saved('A'),saved('B',product=101,order=2))
        self.assertEqual(a['totals'][200]['stock'],18)
        self.assertNotIn(201,a['totals'])
        other,_=except_owner(a,None)
        row=self.rows(self.calculate(100,1,other))[200]
        self.assertEqual((row['manual_reserved'],row['plan_reserved'],row['available']),(2,18,0))

    def test_released_plan_holds_nothing_and_reactivation_order_matters(self):
        self.stock={200:13,201:4}
        a=self.allocate(saved('A',active=False),saved('B',product=101,order=2))
        self.assertNotIn('A',a['by_plan'])
        later=self.allocate(saved('A',order=3),saved('B',product=101,order=2))
        self.assertEqual(later['by_plan']['B']['priority'],1)
        self.assertEqual(next(r['stock'] for r in later['by_plan']['A']['items'] if r['id']==200),4)

    def test_stock_changes_reallocate_without_oversubscription(self):
        plans=[saved('A'),saved('B',product=101,order=2)]
        self.stock={200:5}
        a=self.allocate(*plans)
        self.assertEqual(a['totals'][200]['stock'],5)
        self.stock={200:100,201:100}
        b=self.allocate(*plans)
        self.assertEqual(b['totals'][200]['stock'],22)
        self.assertEqual(b['totals'][201]['stock'],6)

    def test_saved_finished_product_is_reserved_without_reserving_inputs(self):
        self.stock={100:1,200:20,201:20}
        a=self.allocate(saved('A'))
        self.assertEqual(a['totals'],{100:{'stock':1,'wip':0}})

    def test_invalid_active_plan_fails_closed_but_inactive_plan_is_allowed(self):
        with self.assertRaisesRegex(PlanningError,'A mentett terv'):
            self.allocate(saved('A',product=999))
        self.assertEqual(self.allocate(saved('A',product=999,active=False))['active_count'],0)


class MigrationTests(unittest.TestCase):
    def test_old_saved_plans_and_inputs_survive_schema_upgrade_without_automatic_holds(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'muhely.sqlite3'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE plans(id TEXT PRIMARY KEY,name TEXT,product_id INTEGER,quantity INTEGER,created REAL,saved_inputs TEXT)')
                db.execute('INSERT INTO plans VALUES (?,?,?,?,?,?)',('old','Old Salvation',92822,1,1,'retained'))
            store=Store(folder)
            self.assertEqual(store.plans()[0]['name'],'Old Salvation')
            self.assertFalse(store.plans()[0]['reserve_active'])
            store.save_plan({**store.plans()[0],'reserve_active':True,'reserved_at':2})
            with store.db() as db:
                self.assertEqual(db.execute('SELECT saved_inputs FROM plans').fetchone()[0],'retained')
            self.assertTrue(Store(folder).plans()[0]['reserve_active'])


if __name__=='__main__':unittest.main()
