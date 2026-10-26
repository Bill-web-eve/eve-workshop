from pathlib import Path
from datetime import datetime,timezone
import tempfile,unittest,copy
from unittest.mock import patch
from muhely.boosts import BoostCounter,CHARGES,declaration,discover
from muhely.store import Store
from muhely.planner import PlanningError

NOW=datetime(2026,10,26,20,0,tzinfo=timezone.utc).timestamp()
def message(seconds,name,body):
 stamp=datetime.fromtimestamp(NOW+seconds,timezone.utc).strftime('%Y.%m.%d %H:%M:%S')
 return '\ufeff[ '+stamp+' ] '+name+' > '+body+'\r\n'
def header(channel='I. Boost X2',listener='Steve'):
 return '\r\n Channel ID: player_test\r\n Channel Name: '+channel+'\r\n Listener: '+listener+'\r\n'

class BoostTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.logs=self.root/'logs';self.logs.mkdir();self.store=Store(self.root/'profile');self.now=NOW
  self.counter=BoostCounter(self.store,lambda:self.now);self.counter.resume=lambda:None;self.addCleanup(self.counter.close)
 def log(self,name='I. Boost X2',character=1,text='',encoding='utf-16',stamp='200000'):
  path=self.logs/(name+'_20261026_'+stamp+'_'+str(character)+'.txt');path.write_bytes((header(name)+text).encode(encoding));return path
 def append(self,path,text,encoding='utf-16-le'):
  with path.open('ab') as f:f.write(text.encode(encoding))
 def start(self):return self.counter.start(str(self.logs),'I. Boost X2')
 def counts(self):return {r['id']:r['count'] for r in self.counter.snapshot()['rows']}
 def test_only_nine_supported_types_and_boost_channels(self):
  self.assertEqual(len(CHARGES),9);self.log();self.log('Local');self.log('Friendly BOOST Room');self.log('I. Boost X2',2)
  self.assertEqual(discover(str(self.logs)),['Friendly BOOST Room','I. Boost X2'])
  with self.assertRaises(PlanningError):self.counter.start(str(self.logs),'Local')
 def test_existing_lines_are_skipped_and_new_declarations_are_counted_once(self):
  p=self.log(text=message(-10,'Old','Active Shielding Charge'));self.start()
  self.append(p,message(1,'Pilot','Active Shielding Charge Shield Harmonizing Charge'));self.now+=2;self.counter.scan()
  self.assertEqual(self.counts()[42694],1);self.assertEqual(self.counts()[42695],1)
  self.append(p,message(2,'Pilot','Active Shielding Charge Shield Harmonizing Charge'));self.counter.scan();self.counter.scan()
  self.assertEqual(self.counts()[42694],1);self.assertEqual(len(self.counter.snapshot()['providers']),1)
 def test_last_declaration_replaces_previous_set_and_missing_summary_is_ignored(self):
  p=self.log();self.start()
  self.append(p,message(1,'Pilot','Active Shielding Charge Shield Harmonizing Charge')+message(2,'Pilot','Sensor Optimization Charge')+message(3,'FC','missing: Evasive Maneuvers Charge Electronic Hardening Charge'))
  self.now+=4;self.counter.scan()
  self.assertEqual(self.counts()[42694],0);self.assertEqual(self.counts()[42835],1);self.assertEqual(self.counts()[42838],0)
 def test_duplicate_logs_and_out_of_order_messages_do_not_restore_old_boosts(self):
  p=self.log();q=self.log(character=2);self.start()
  old=message(1,'Pilot','Active Shielding Charge');new=message(2,'Pilot','Sensor Optimization Charge')
  self.append(p,old+new);self.now+=3;self.counter.scan();self.append(q,old+new);self.counter.scan()
  self.assertEqual(self.counts()[42694],0);self.assertEqual(self.counts()[42835],1)
 def test_utf8_and_utf16_partial_lines_wait_for_completion(self):
  for enc in ['utf-8','utf-16']:
   with self.subTest(enc=enc):
    self.counter.stop();self.now=NOW;p=self.log(encoding=enc);self.start();line=message(1,'Pilót','Active Shielding Charge').encode('utf-8' if enc=='utf-8' else 'utf-16-le')
    cut=len(line)-4
    with p.open('ab') as f:f.write(line[:cut])
    self.now=NOW+2;self.counter.scan();self.assertEqual(self.counts()[42694],0)
    with p.open('ab') as f:f.write(line[cut:])
    self.counter.scan();self.assertEqual(self.counts()[42694],1)
 def test_start_mid_line_ignores_its_completion_and_counts_next_line(self):
  p=self.log();raw=message(0,'Old','Active Shielding Charge').encode('utf-16-le');cut=13
  with p.open('ab') as f:f.write(raw[:cut])
  self.start()
  with p.open('ab') as f:f.write(raw[cut:])
  self.append(p,message(1,'New','Shield Extension Charge'));self.now+=2;self.counter.scan()
  self.assertEqual(self.counts()[42694],0);self.assertEqual(self.counts()[42696],1)
 def test_new_log_after_start_old_messages_and_system_notices_are_ignored(self):
  self.log();self.start()
  self.log(character=2,text=message(-20,'Old','Active Shielding Charge')+message(1,'EVE System','Shield Harmonizing Charge')+message(1,'New','Shield Extension Charge'))
  self.now+=2;self.counter.scan();self.assertEqual(self.counts()[42694],0);self.assertEqual(self.counts()[42695],0);self.assertEqual(self.counts()[42696],1)
 def test_log_rotation_and_truncation_are_safe(self):
  p=self.log();self.start();self.append(p,message(1,'Pilot','Active Shielding Charge'));self.now+=2;self.counter.scan()
  p.unlink();self.log(text=message(1,'Pilot','Active Shielding Charge')+message(2,'Other','Active Shielding Charge'));self.counter.scan()
  self.assertEqual(self.counts()[42694],2)
 def test_stop_retains_counts_new_start_resets_and_restart_retains_offsets(self):
  p=self.log();self.start();self.append(p,message(1,'Pilot','Active Shielding Charge'));self.now+=2;self.counter.scan()
  restored=BoostCounter(self.store,lambda:self.now);self.addCleanup(restored.close);restored.scan();self.assertEqual(restored.snapshot()['rows'][0]['count'],1)
  self.counter.stop();self.append(p,message(2,'Other','Active Shielding Charge'));self.counter.scan();self.assertEqual(self.counts()[42694],1)
  self.start();self.assertEqual(self.counts()[42694],0);self.counter.scan();self.assertEqual(self.counts()[42694],0)
 def test_copy_contains_all_nine_names_including_zeros(self):
  self.log();data=self.start();lines=data['copy_text'].splitlines()
  self.assertEqual(len(lines),9);self.assertTrue(all(line.endswith('\t0') for line in lines))
  self.assertTrue(all(declaration(message(0,'FC',line),NOW) is None for line in lines))
  self.assertIsNone(declaration(message(0,'FC',' '.join(lines)),NOW))
 def test_wrong_header_and_symlink_cannot_supply_declarations(self):
  self.log();self.start();bad=self.log(character=2,text=message(1,'Bad','Active Shielding Charge'));bad.write_bytes((header('Other')+message(1,'Bad','Active Shielding Charge')).encode('utf-16'))
  external=self.root/'outside.txt';external.write_text(header()+message(1,'External','Active Shielding Charge'));(self.logs/'I. Boost X2_20261026_200001_3.txt').symlink_to(external)
  self.now+=2;self.counter.scan();self.assertEqual(self.counts()[42694],0);self.assertEqual(self.counter.snapshot()['file_errors'],1)
 def test_linked_item_repeated_names_and_unrecognized_boosts(self):
  item=declaration(message(0,'Pilot','<url=showinfo:42694>boost</url> Active Shielding Charge Active Shielding Charge + ML'),NOW)
  self.assertEqual(item['charges'],[42694]);self.assertIsNone(declaration(message(0,'P','Mining Laser Optimization Charge'),NOW));self.assertIsNone(declaration(message(0,'P','missing: Active Shielding Charge'),NOW))

class BoostApiTests(unittest.TestCase):
 import test_server as base
 setUp=base.ServerTests.setUp;close=base.ServerTests.close;request=base.ServerTests.request
 def test_scoped_routes_are_authenticated_and_do_not_touch_planning(self):
  logs=Path(self.tmp.name)/'logs';logs.mkdir();(logs/'I. Boost X2_20261026_200000_1.txt').write_text(header())
  self.assertEqual(self.request('/api/boosts',Cookie='')[0],403)
  self.assertEqual(self.request('/api/boosts/start',{'folder':str(logs),'channel':'I. Boost X2'},Origin='https://other.invalid')[0],403)
  with patch.object(self.app,'plan',side_effect=AssertionError('No planning')):
   self.assertEqual(self.request('/api/boosts/channels?folder='+str(logs))[1]['channels'],['I. Boost X2'])
   status,data,_=self.request('/api/boosts/start',{'folder':str(logs),'channel':'I. Boost X2'});self.assertEqual(status,200);self.assertTrue(data['running'])
   self.assertFalse(self.request('/api/boosts/stop',{})[1]['running'])
   self.assertEqual(len(self.request('/api/boosts')[1]['rows']),9)
  self.assertEqual(self.request('/boosts.js')[0],200)
  self.assertEqual(self.app.store.plans(),[])
