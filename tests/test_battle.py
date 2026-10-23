from copy import deepcopy
from itertools import combinations
import tempfile,unittest
from muhely import battle,fleet
from muhely.store import Store
from muhely.planner import PlanningError

CONFIG={'side_count':None,'assignments':{},'names':{}}
def pilot(char,alliance=None,corp=None):return {k:v for k,v in {'character_id':char,'alliance_id':alliance,'corporation_id':corp,'ship_type_id':590}.items() if v is not None}
def kill(kid,victim,attackers,value=100):return {'killmail_id':kid,'killmail_time':'2026-10-23T10:00:00Z','solar_system_id':30000142,'victim':victim,'attackers':attackers,'zkb':{'totalValue':value,'destroyedValue':value/2}}
def build(rows,config=None):return battle.build(rows,11,config or CONFIG,{},fleet.session_value)
def assignments(report):return {g['key']:s['id'] for s in [*report['sides'],report['unassigned']] for g in s['groups']}
A=pilot(11,1001);B=pilot(21,1002);C=pilot(31,1003);D=pilot(41,1004)
class BattleTests(unittest.TestCase):
    def test_coattackers_share_side_and_opponents_do_not(self):
        r=build([kill(1,C,[A,B]),kill(2,A,[C])]);a=assignments(r)
        self.assertEqual(a['alliance:1001'],a['alliance:1002']);self.assertNotEqual(a['alliance:1001'],a['alliance:1003']);self.assertEqual(r['side_count'],2)
    def test_three_and_four_mutually_hostile_parties_are_separate(self):
        for parties in [[A,B,C],[A,B,C,D]]:
            rows=[kill(i+1,v,[a]) for i,(a,v) in enumerate(combinations(parties,2))]
            r=build(rows);a=assignments(r)
            self.assertEqual(r['side_count'],len(parties));self.assertEqual(len(set(a.values())),len(parties));self.assertNotIn(-1,a.values())
    def test_unrelated_fight_stays_unassigned_instead_of_inventing_allies(self):
        r=build([kill(1,C,[A]),kill(2,D,[B])]);a=assignments(r)
        self.assertEqual(a['alliance:1002'],-1);self.assertEqual(a['alliance:1004'],-1)
        self.assertEqual(r['unassigned']['loss_value']['count'],1)
    def test_loss_values_are_deduplicated_and_conserve_total(self):
        rows=[kill(1,C,[A,B],101.25),kill(2,A,[C],50.50),kill(3,{},[],10)]
        r=build([*rows,rows[0]]);self.assertEqual(sum(int(s['loss_value']['cents']) for s in [*r['sides'],r['unassigned']]),16175)
        self.assertEqual(sum(s['loss_value']['count'] for s in [*r['sides'],r['unassigned']]),3)
        self.assertEqual(r['sides'][0]['pilot_count'],2)
    def test_manual_move_changes_only_one_group_and_is_not_overridden_by_inference(self):
        rows=[kill(1,C,[A,B]),kill(2,A,[C])];original=assignments(build(rows))
        cfg=deepcopy(CONFIG);cfg['assignments']['alliance:1002']=original['alliance:1003']
        r=build(rows,cfg);a=assignments(r)
        self.assertEqual(a['alliance:1002'],original['alliance:1003']);self.assertEqual(a['alliance:1001'],original['alliance:1001']);self.assertEqual(a['alliance:1003'],original['alliance:1003'])
        self.assertTrue(any(s['friendly_fire'] for s in r['sides']))
    def test_requested_two_sides_cannot_hide_third_party_conflict(self):
        cfg=deepcopy(CONFIG);cfg['side_count']=2;r=build([kill(1,B,[A]),kill(2,C,[B]),kill(3,A,[C])],cfg)
        self.assertEqual(r['side_count'],2);self.assertTrue(r['unassigned']['groups'])
    def test_no_alliance_uses_player_corporation_or_individual_npc_corp_pilot(self):
        self.assertEqual(battle.group_key(pilot(11,corp=98000001)),'corporation:98000001')
        self.assertEqual(battle.group_key(pilot(11,corp=1000127)),'character:11');self.assertIsNone(battle.group_key({'corporation_id':1000127}))
    def test_known_alliance_name_uses_historical_killmail_affiliation(self):
        r=battle.build([kill(1,C,[A])],11,CONFIG,{'1001':{'name':'Fleet friends','category':'alliance'}},fleet.session_value)
        self.assertEqual(next(g for s in r['sides'] for g in s['groups'] if g['id']==1001)['name'],'Fleet friends')
    def test_group_can_have_no_loss_but_remains_a_participant(self):
        r=build([kill(1,C,[A])]);side=next(s for s in r['sides'] if any(g['id']==1001 for g in s['groups']))
        self.assertEqual(side['loss_value']['cents'],'0');self.assertEqual(side['pilot_count'],1);self.assertEqual(side['kill_count'],1)
    def test_same_alliance_internal_fire_does_not_split_alliance(self):
        r=build([kill(1,pilot(12,1001),[A])]);self.assertEqual(len(assignments(r)),1);self.assertEqual(r['sides'][0]['friendly_fire'],1)
    def test_configuration_validation_and_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);battle.schema(store)
            for changes in [{'side_count':1},{'side_count':True},{'group':'alliance:99','side':0},{'group':'alliance:1001','side':4}]:
                with self.assertRaises(PlanningError):battle.save(store,'11:1',changes,{'alliance:1001'})
            battle.save(store,'11:1',{'side_count':4,'group':'alliance:1001','side':3},{'alliance:1001'})
            self.assertEqual(battle.configuration(store,'11:1')['assignments'],{'alliance:1001':3})
            self.assertEqual(battle.configuration(store,'12:1')['assignments'],{})
            battle.save(store,'11:1',{'side_count':2},{'alliance:1001'});self.assertEqual(battle.configuration(store,'11:1')['assignments'],{'alliance:1001':-1})
            battle.save(store,'11:1',{'reset':True},{'alliance:1001'});self.assertEqual(battle.configuration(store,'11:1'),CONFIG)

    def test_fifth_mutually_hostile_party_is_marked_unassigned(self):
        parties=[A,B,C,D,pilot(51,1005)]
        r=build([kill(i+1,v,[a]) for i,(a,v) in enumerate(combinations(parties,2))])
        self.assertEqual(r['side_count'],4);self.assertTrue(r['unassigned']['groups'])
    def test_manual_group_can_move_to_fourth_side_and_survive_new_killmails(self):
        cfg=deepcopy(CONFIG);cfg['assignments']={'alliance:1002':3}
        r=build([kill(1,C,[A,B]),kill(2,A,[C])],cfg)
        self.assertEqual(r['side_count'],4);self.assertEqual(assignments(r)['alliance:1002'],3)
        r=build([kill(1,C,[A,B]),kill(2,A,[C]),kill(3,D,[B])],cfg)
        self.assertEqual(assignments(r)['alliance:1002'],3)

    def test_late_killmail_does_not_drop_saved_assignments_or_affect_another_pilot(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);battle.schema(store)
            battle.save(store,'11:2',{'group':'alliance:1001','side':1},{'alliance:1001'})
            self.assertEqual(battle.configuration(store,'11:1',[1,2])['assignments'],{'alliance:1001':1})
            self.assertEqual(battle.configuration(store,'12:1',[1,2])['assignments'],{})
            battle.save(store,'11:1',{'reset':True},{'alliance:1001'},battle.configuration(store,'11:1',[1,2]))
            self.assertEqual(battle.configuration(store,'11:1',[1,2])['assignments'],{})
