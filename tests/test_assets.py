import tempfile
import unittest
from types import SimpleNamespace

from muhely.assets import dashboard,root_locations
from muhely.store import Store
from muhely.planner import PlanningError


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.s=Store(self.tmp.name);self.c=SimpleNamespace(name=lambda tid:{10:'Unrelated item',20:'Ship',30:'Blueprint'}.get(tid,f'Type {tid}'))
        for cid in [1,2]:self.s.add_character(cid,f'Pilot {cid}')
    def asset(self,item=1,tid=10,quantity=2,location=6001,**kw):
        return dict(item_id=item,type_id=tid,quantity=quantity,location_id=location,location_flag='Hangar',is_singleton=False,**kw)
    def seed(self,cid,rows,expires=200):
        self.s.save_snapshots(cid,{'assets':{'data':rows,'fetched':100,'expires':expires,'etag':None}})
    def test_all_characters_and_items_ignore_plan_filters_and_overrides(self):
        self.seed(1,[self.asset()]);self.seed(2,[self.asset(quantity=3,location=6002)])
        self.s.save_settings({'source':'manual','character_ids':[1],'location_ids':[6001]})
        self.s.save_mapping('inventory',{10:{'quantity':0,'reserved':9999}})
        r=dashboard(self.s,self.c,now=150)
        self.assertEqual(len(r['rows']),2);self.assertEqual(r['quantity'],5)
        self.assertEqual({x['owner_id'] for x in r['rows']},{1,2})
        self.assertEqual(r['type_count'],1)
    def test_includes_assembled_ships_bpc_and_unknown_types_without_jobs_or_blueprints(self):
        ship=self.asset(item=2,tid=20);ship['is_singleton']=True
        bpc=self.asset(item=3,tid=30,is_blueprint_copy=True)
        self.seed(1,[ship,bpc,self.asset(item=4,tid=999)])
        rows=dashboard(self.s,self.c,now=150)['rows']
        self.assertEqual({r['state'] for r in rows},{'singleton','blueprint_copy','packaged'})
        self.assertIn('Type 999',[r['name'] for r in rows])
        self.assertIsNone(self.s.snapshot(1,'jobs'))
    def test_nested_containers_deduplicate_per_owner_and_group_same_place(self):
        self.seed(1,[self.asset(),self.asset(),self.asset(item=2,location=99),self.asset(item=99,tid=20,location=6001),self.asset(item=3,location=6002)])
        self.seed(2,[self.asset()])
        rows=dashboard(self.s,self.c,now=150)['rows']
        row=next(r for r in rows if r['owner_id']==1 and r['type_id']==10 and r['location_id']==6001)
        self.assertEqual(row['quantity'],4)
        self.assertEqual(sum(r['quantity'] for r in rows if r['type_id']==10),8)
    def test_container_cycles_do_not_hang_or_corrupt_other_locations(self):
        self.assertEqual(root_locations([self.asset(item=1,location=2),self.asset(item=2,location=1),self.asset(item=3)]),{1:None,2:None,3:6001})
    def test_corporations_remain_separate_and_are_not_multiplied_by_readers(self):
        for cid,corp in [(1,99),(2,99)]:self.s.character_corporation(cid,corp,'Corp A')
        self.s.character_corporation(2,98,'Corp B')
        self.s.add_character(3,'Another corporate reader');self.s.character_corporation(3,99,'Corp A')
        for corp,quantity in [(99,100),(98,700)]:
            self.s.save_corporation_snapshots(corp,1,{'assets':{'data':[self.asset(quantity=quantity)],'fetched':100,'expires':200,'etag':None}})
        self.seed(1,[self.asset(quantity=999)])
        self.assertEqual(dashboard(self.s,self.c,99,150)['quantity'],100)
        self.assertEqual(dashboard(self.s,self.c,98,150)['quantity'],700)
        self.assertEqual(dashboard(self.s,self.c,now=150)['quantity'],999)
        with self.assertRaises(PlanningError):dashboard(self.s,self.c,97,150)
    def test_partial_stale_snapshots_remain_visible_with_explicit_source_status(self):
        self.seed(1,[self.asset()],expires=110)
        r=dashboard(self.s,self.c,now=150)
        self.assertEqual(r['quantity'],2)
        by_id={s['id']:s for s in r['sources']}
        self.assertTrue(by_id[1]['stale']);self.assertFalse(by_id[2]['available'])
        self.assertEqual(by_id[1]['fetched'],100)
