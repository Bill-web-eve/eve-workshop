from pathlib import Path
from datetime import datetime, timezone
import tempfile, unittest
from muhely.store import Store
from muhely.preview_mining import PreviewMining, event

NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc).timestamp()
CARGO = "Your Abyssal Modulated Strip Miner has completed operations. Ship's cargo hold is full."
CRYSTAL = 'Abyssal Modulated Strip Miner deactivates due to the destruction of the Common Moon Mining Crystal Type B II it was fitted with. '
ROCK = 'Abyssal Modulated Strip Miner deactivates as it finds the resource it was harvesting a pale shadow of its former glory.'
MINED = 'You mined 75 units of Twinkling Scheelite'
def line(body, seconds=1, category='notify'):
    stamp = datetime.fromtimestamp(NOW+seconds, timezone.utc).strftime('%Y.%m.%d %H:%M:%S')
    return f'[ {stamp} ] ({category}) {body}\n'
def header(name='Pilot A'):
    return f'----------------\n  Gamelog\n  Listener: {name}\n  Session Started: 2026.11.07 12:00:00\n----------------\n'

class PreviewMiningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.logs = self.root/'Gamelogs';self.logs.mkdir()
        self.store = Store(self.root/'profile');self.store.save_settings({'preview_mining':{'enabled':True,'folder':str(self.logs)}})
        self.now=NOW;self.monitor=PreviewMining(self.store, lambda:self.now)
    def log(self, cid=1, session='120000', name='Pilot A', text='', enc='utf-8'):
        path=self.logs/f'20261107_{session}_{cid}.txt';path.write_bytes((header(name)+text).encode(enc));return path
    def append(self, path, text, enc='utf-8'):
        with path.open('ab') as f:f.write(text.encode(enc))
    def data(self):
        self.now+=2;return self.monitor.snapshot(force=True)
    def alerts(self, row=0):return {a['kind']:a for a in self.data()['characters'][row]['alerts']}
    def test_actual_client_messages_and_false_positives(self):
        for body,kind in [(CARGO,'cargo_full'),(CRYSTAL,'crystal_broken'),(ROCK,'rock_depleted')]:
            result=event(line('<b>'+body+'</b>'),NOW+2);self.assertEqual(result['kind'],kind);self.assertEqual(result['module'],'Abyssal Modulated Strip Miner')
        self.assertEqual(event(line(CRYSTAL),NOW+2)['crystal'],'Common Moon Mining Crystal Type B II')
        for body,category in [('Asteroid is too far away','notify'),(CRYSTAL,'combat'),(CARGO,'question'),('Cargo is too far away.','notify'),('The Miner will not activate because its crystal is not calibrated to mine Coesite.','notify')]:self.assertIsNone(event(line(body,category=category),NOW+2))
        self.assertIsNone(event(line(CARGO,seconds=300),NOW));self.assertIsNone(event('invalid',NOW))
    def test_existing_history_is_skipped_then_each_warning_is_independent(self):
        p=self.log(text=line(CARGO,-1));self.monitor.snapshot();self.assertEqual(self.alerts(),{})
        self.append(p,line(CARGO)+line(CRYSTAL,2)+line(ROCK,3));alerts=self.alerts();self.assertEqual(set(alerts),{'cargo_full','crystal_broken','rock_depleted'})
        self.append(p,line(MINED,5,'mining'));self.assertEqual(set(self.alerts()),set(alerts));self.assertIsNotNone(self.data()['characters'][0]['last_mined'])
        self.assertEqual(self.data()['characters'][0]['last_module'],'Abyssal Modulated Strip Miner')
    def test_acknowledgement_only_removes_event_ids_seen_by_user(self):
        p=self.log();self.monitor.snapshot();self.append(p,line(CARGO)+line(CRYSTAL,2));old=self.alerts()
        self.append(p,line(CARGO,3));self.data();self.monitor.acknowledge({'name':'PILOT A','ids':[v['id'] for v in old.values()]})
        self.assertEqual(set(self.alerts()),{'cargo_full'});new=self.alerts()['cargo_full'];self.monitor.acknowledge({'name':'Pilot A','ids':[new['id']]});self.assertEqual(self.alerts(),{})
    def test_names_are_matched_to_character_sessions_without_mixing(self):
        a=self.log();b=self.log(cid=2,name='Pilot B');self.monitor.snapshot();self.append(a,line(CRYSTAL));self.append(b,line(CARGO));rows=self.data()['characters']
        self.assertEqual([(r['name'],[a['kind'] for a in r['alerts']]) for r in rows],[('Pilot A',['crystal_broken']),('Pilot B',['cargo_full'])])
    def test_utf16_and_partial_lines_are_not_lost_or_read_twice(self):
        for index,enc in enumerate(['utf-16-le','utf-16-be','utf-8']):
            with self.subTest(enc=enc):
                self.now=NOW
                m=PreviewMining(self.store,lambda:self.now);p=self.log(cid=index+10,name='Pilot '+str(index),enc='utf-16' if enc=='utf-16-le' else enc)
                if enc=='utf-16-be':p.write_bytes(b'\xfe\xff'+p.read_bytes())
                m.snapshot();body=line(CRYSTAL).encode(enc);half=len(body)//2
                with p.open('ab') as f:f.write(body[:half])
                self.now+=2;m.snapshot(force=True)
                with p.open('ab') as f:f.write(body[half:])
                result=m.snapshot(force=True);row=next(r for r in result['characters'] if r['name']=='Pilot '+str(index));self.assertEqual(len(row['alerts']),1)
                self.assertEqual(m.snapshot(force=True)['characters'],result['characters'])
    def test_partial_old_line_at_start_is_never_reported_as_new(self):
        p=self.log(text=line(CARGO)[:-5]);self.monitor.snapshot();self.append(p,line(CARGO)[-5:]+line(ROCK,3));self.assertEqual(set(self.alerts()),{'rock_depleted'})
    def test_new_session_clears_previous_badges_and_reads_new_events(self):
        a=self.log();self.monitor.snapshot();self.append(a,line(CARGO));self.assertEqual(set(self.alerts()),{'cargo_full'})
        self.log(session='120010',text=line(ROCK,10));self.now=NOW+11;self.assertEqual(set(self.alerts()),{'rock_depleted'})
    def test_truncation_is_detected_and_future_or_old_events_are_ignored(self):
        p=self.log();self.monitor.snapshot();self.append(p,line(CARGO));self.alerts()
        p.write_text(header()+line(ROCK,-10)+line(CRYSTAL,300));self.assertEqual(self.alerts(),{})
        self.append(p,line(ROCK,3));self.assertEqual(set(self.alerts()),{'rock_depleted'})
    def test_symlinks_and_wrong_headers_do_not_supply_alerts(self):
        target=self.root/'outside';target.write_text(header()+line(CARGO));(self.logs/'20261107_120000_1.txt').symlink_to(target)
        self.log(cid=2).write_text('Chatlog\nListener: Pilot A\n'+line(CARGO));data=self.monitor.snapshot()
        self.assertEqual(data['characters'],[]);self.assertEqual(data['file_errors'],1)
    def test_folder_failure_is_visible_and_prior_alerts_are_preserved(self):
        p=self.log();self.monitor.snapshot();self.append(p,line(CARGO));self.alerts();self.logs.rename(self.root/'moved')
        data=self.data();self.assertEqual(data['error'],'folder_unavailable');self.assertEqual(data['characters'][0]['alerts'][0]['kind'],'cargo_full')
    def test_disable_and_configuration_validation(self):
        p=self.log();self.monitor.snapshot();self.append(p,line(CARGO));self.alerts()
        self.assertEqual(self.monitor.configure({'enabled':False,'folder':str(self.logs)})['characters'],[])
        self.assertFalse(PreviewMining(self.store).config['enabled'])
        for data in [{},{'enabled':1,'folder':str(self.logs)},{'enabled':True,'folder':'/missing/folder'},{'enabled':True,'folder':''}]:
            with self.assertRaises(ValueError):self.monitor.configure(data)
        with self.assertRaises(ValueError):self.monitor.acknowledge({'name':'Pilot A','ids':['not-valid']})
    def test_crystal_click_becomes_paused_and_next_mining_event_clears_only_pause(self):
        p=self.log();self.monitor.snapshot();self.append(p,line(CRYSTAL)+line(ROCK,2));old=self.alerts()['crystal_broken']
        self.monitor.replace_crystal({'name':'Pilot A','id':old['id']});alerts=self.alerts()
        self.assertEqual(set(alerts),{'module_stopped','rock_depleted'})
        # Historical mining, critical bonus lines and unrelated messages cannot clear pause.
        self.append(p,line(MINED,1,'mining')+line('Critical mining success! You mined an additional 22 units of Coesite',9,'mining'))
        self.assertIn('module_stopped',self.alerts())
        self.append(p,line(MINED,20,'mining'));self.now=NOW+21;self.assertEqual(set(self.alerts()),{'rock_depleted'})
    def test_explicit_active_message_can_clear_pause_before_next_mining_cycle(self):
        p=self.log();self.monitor.snapshot();self.append(p,line(CRYSTAL));old=self.alerts()['crystal_broken'];self.monitor.replace_crystal({'name':'Pilot A','id':old['id']})
        self.append(p,line('Different Miner is already active',20,'hint'));self.now=NOW+21;self.assertIn('module_stopped',self.alerts())
        self.append(p,line('Abyssal Modulated Strip Miner is already active',30,'hint'));self.now=NOW+31;self.assertEqual(self.alerts(),{})
    def test_stale_crystal_click_does_not_replace_a_new_break(self):
        p=self.log();self.monitor.snapshot();self.append(p,line(CRYSTAL));old=self.alerts()['crystal_broken'];self.append(p,line(CRYSTAL,3))
        self.monitor.replace_crystal({'name':'Pilot A','id':old['id']});self.assertEqual(set(self.alerts()),{'crystal_broken'})
    def test_closed_monitor_does_not_read_logs(self):
        self.log();self.monitor.closed=True
        self.assertIsNone(self.monitor.snapshot()['checked'])
