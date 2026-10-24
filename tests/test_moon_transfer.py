import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from muhely.catalog import Catalog
from muhely.store import Store,moon_revision
from muhely.planner import PlanningError
from muhely import moon_transfer as transfer

ROOT=Path(__file__).resolve().parents[1]
SCAN='''Moon\tMoon Product\tQuantity\tOre TypeID\tSolarSystemID\tPlanetID\tMoonID
4X0-8B XI - Moon 13\t\t\t\t\t\t
\tCobaltite\t0.0975508913398\t45494\t30004736\t40299828\t40299845
\tCoesite\t0.31070920825\t45493\t30004736\t40299828\t40299845
\tSperrylite\t0.258988469839\t45499\t30004736\t40299828\t40299845
\tSylvite\t0.33275142312\t45491\t30004736\t40299828\t40299845'''
class TransferTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.catalog=Catalog(ROOT/'data/catalog.sqlite3')
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
 def body(self,**kw):return {'format':'scan','text':SCAN,'existing':'skip','structure':'Metenox','rent_isk':'100',**kw}
 def apply(self,body):
  preview=transfer.preview(self.store,self.catalog,body)
  return transfer.apply_import(self.store,self.catalog,{**body,'revision':preview['revision']})
 def exported(self):return transfer.export_register(self.store,self.catalog)
 def test_game_scan_ratios_ids_and_planet_are_resolved_without_writing_preview(self):
  p=transfer.preview(self.store,self.catalog,self.body());self.assertFalse(self.store.moon_records())
  self.assertEqual(p['counts'],{'new':1,'update':0,'skip':0});r=p['rows'][0]
  self.assertEqual(r['name'],'4X0-8B XI - Moon 13');self.assertEqual(r['rent_isk'],'100.00')
  self.assertAlmostEqual(r['ores'][0]['percent'],9.75508913398);self.assertAlmostEqual(r['percent_total'],100,places=5)
  self.apply(self.body());self.assertEqual(len(self.store.moon_records()),1)
 def test_markdown_and_decimal_comma_scans_and_multiple_moons(self):
  cells=[line.split('\t') for line in SCAN.splitlines()]
  markdown='\n'.join('| '+' | '.join(row)+' |' for row in cells[:1])+ '\n|---|---|---|---|---|---|---|\n'+'\n'.join('| '+' | '.join(row)+' |' for row in cells[1:])
  self.assertEqual(transfer.preview(self.store,self.catalog,self.body(text=markdown))['counts']['new'],1)
  # A second moon on the same planet has a distinct authoritative MoonID.
  second=next(m for m in self.catalog.moon_locations(30004736) if m['name']=='4X0-8B XI - Moon 12')
  scan2=SCAN.replace('Moon 13','Moon 12').replace('40299845',str(second['id'])).replace('0.0975508913398','0,0975508913398')
  self.apply(self.body(text=SCAN+'\n'+scan2));self.assertEqual(len(self.store.moon_records()),2)
 def test_skip_and_update_rescan_keep_costs_notes_and_structure(self):
  self.apply(self.body())
  old=self.store.moon_records()[0];old.update(rent_isk='1234.56',other_cost_isk='99.00',notes='Keep me',structure='Athanor',enabled=False,online_starts=2,belt_lifetime_hours=72);self.store.save_moon(old)
  self.apply(self.body());self.assertEqual(self.store.moon_records()[0],old)
  self.apply(self.body(existing='update',text=SCAN.replace('0.0975508913398','0.09'),rent_isk='0'))
  new=self.store.moon_records()[0]
  for key in ['id','rent_isk','other_cost_isk','notes','structure','enabled','online_starts','belt_lifetime_hours']:self.assertEqual(new[key],old[key])
  self.assertEqual(new['ores'][0]['percent'],9)
 def test_all_manual_fields_roundtrip_in_bulk_json_without_auth_or_profile_data(self):
  self.apply(self.body());record=self.store.moon_records()[0];record.update(rent_isk='1234.56',other_cost_isk='78.90',notes='Árvíztűrő <notes> \n line',enabled=False,online_starts=3,belt_lifetime_hours=72);self.store.save_moon(record);self.store.add_character(11,'Private character')
  doc=self.exported();self.assertEqual(doc['format'],transfer.FORMAT)
  text=json.dumps(doc);self.assertNotIn('Private character',text);self.assertNotIn('csrf',text);self.assertNotIn('character_id',text)
  with tempfile.TemporaryDirectory() as folder:
   target=Store(folder);body={'format':'json','text':text}
   p=transfer.preview(target,self.catalog,body);transfer.apply_import(target,self.catalog,{**body,'revision':p['revision']})
   a=self.store.moon_records()[0];b=target.moon_records()[0]
   self.assertEqual({k:v for k,v in a.items() if k!='id'},{k:v for k,v in b.items() if k!='id'})
 def test_json_updates_require_selection_and_do_not_delete_omitted_moons(self):
  self.apply(self.body());doc=self.exported();doc['moons'][0]['rent_isk']='999'
  body={'format':'json','text':json.dumps(doc)};self.apply(body)
  self.assertEqual(self.store.moon_records()[0]['rent_isk'],'100.00')
  self.apply({**body,'existing':'update'});self.assertEqual(self.store.moon_records()[0]['rent_isk'],'999.00')
 def test_stale_preview_and_late_bad_rows_cannot_partially_import(self):
  body=self.body();p=transfer.preview(self.store,self.catalog,body);self.apply(body)
  with self.assertRaises(PlanningError):transfer.apply_import(self.store,self.catalog,{**body,'revision':p['revision']})
  before=self.store.moon_records();doc=self.exported();other=copy.deepcopy(doc['moons'][0]);other['moon_id']=-1;doc['moons'].append(other)
  with self.assertRaises(PlanningError):self.apply({'format':'json','text':json.dumps(doc),'existing':'update'})
  self.assertEqual(before,self.store.moon_records())
  update=self.body(existing='update');p=transfer.preview(self.store,self.catalog,update)
  changed=self.store.moon_records()[0];changed['rent_isk']='321.00';self.store.save_moon(changed)
  with self.assertRaises(PlanningError):transfer.apply_import(self.store,self.catalog,{**update,'revision':p['revision']})
  self.assertEqual(self.store.moon_records()[0]['rent_isk'],'321.00')
 def test_database_transaction_rolls_back_an_entire_batch_on_duplicate_moon(self):
  p,values=transfer.prepare(self.store,self.catalog,self.body());bad=copy.deepcopy(values[0]);bad['id']='another'
  with self.assertRaises(sqlite3.IntegrityError):self.store.import_moons([*values,bad],p['revision'])
  self.assertFalse(self.store.moon_records())
 def test_duplicate_ore_bad_ids_bad_quantities_and_overfour_ores_reject_whole_import(self):
  for text in [SCAN+'\n'+SCAN.splitlines()[2],SCAN.replace('40299828','40299829'),SCAN.replace('30004736','30000142'),SCAN.replace('45494','34'),SCAN.replace('0.0975508913398','9.75'),SCAN.replace('0.0975508913398','NaN')]:
   with self.subTest(text=text[-70:]),self.assertRaises(PlanningError):self.apply(self.body(text=text))
   self.assertFalse(self.store.moon_records())
 def test_name_mismatch_warns_and_ids_remain_authoritative(self):
  p=transfer.preview(self.store,self.catalog,self.body(text=SCAN.replace('XI - Moon','IX - Moon').replace('Cobaltite','Wrong ore name')))
  self.assertEqual(p['rows'][0]['name'],'4X0-8B XI - Moon 13');self.assertEqual(len(p['rows'][0]['warnings']),2)
 def test_wrong_json_versions_duplicates_unknown_fields_and_limits_rejected(self):
  self.apply(self.body());doc=self.exported()
  bads=[{**doc,'version':True},{**doc,'version':2},{**doc,'moons':[]},{**doc,'moons':doc['moons']*2},{**doc,'moons':[{**doc['moons'][0],'script':'untrusted'}]}]
  for bad in bads:
   with self.assertRaises(PlanningError):transfer.preview(self.store,self.catalog,{'format':'json','text':json.dumps(bad)})
  for text in ['', 'x'* (transfer.MAX_TEXT+1)]:
   with self.assertRaises(PlanningError):transfer.preview(self.store,self.catalog,self.body(text=text))

import test_server as base
class TransferApiTests(unittest.TestCase):
 setUp=base.ServerTests.setUp
 close=base.ServerTests.close
 request=base.ServerTests.request
 def test_end_to_end_bulk_preview_commit_export_and_csrf(self):
  body={'format':'scan','text':SCAN,'structure':'Metenox','existing':'skip'}
  self.assertEqual(self.request('/api/moons/export',Cookie='')[0],403)
  self.assertEqual(self.request('/api/moons/import/preview',body,**{'X-CSRF-Token':'wrong'})[0],403)
  code,preview,_=self.request('/api/moons/import/preview',body);self.assertEqual(code,200);self.assertFalse(self.app.store.moon_records())
  self.assertEqual(self.request('/api/moons/import',{**body,'revision':'wrong'})[0],400)
  self.assertEqual(self.request('/api/moons/import',{**body,'revision':preview['revision']})[0],200)
  code,doc,_=self.request('/api/moons/export');self.assertEqual(code,200);self.assertEqual(len(doc['moons']),1)
  self.assertEqual(self.request('/moon-transfer.js')[0],200)
  self.assertFalse(self.app.store.characters());self.assertFalse(self.app.store.plans())
