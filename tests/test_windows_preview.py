import json
from pathlib import Path
import queue
import tempfile
import unittest
from muhely.windows_preview import PreviewState,ShortcutHook,shortcut


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.now=1000.;self.state=PreviewState(self.temp.name,lambda:self.now)
        self.sources=[{'key':'a','title':'EVE - Pilot A','hwnd':12},{'key':'b','title':'EVE - Pilot B','hwnd':13}]
        self.state.reconcile(self.sources)
        self.screens=[{'id':'left','left':-1920,'top':0,'width':1920,'height':1080,'work':(-1920,0,1920,1040)},
                      {'id':'right','left':0,'top':0,'width':1920,'height':1080,'work':(0,0,1920,1040)}]

    def test_state_survives_restart_but_not_transient_game_data(self):
        self.state.configure({'enabled':True,'editing':True,'next_key':{'code':75,'modifiers':0}})
        self.state.place(self.state.slots[0],-1800,130,340,self.screens)
        self.state.sync_mining({'enabled':True,'characters':[{'name':'Pilot A','alerts':[],'last_damage':1000}]})
        other=PreviewState(self.temp.name)
        self.assertTrue(other.enabled);self.assertFalse(other.editing)
        self.assertEqual(other.next_key,{'code':75,'modifiers':0})
        self.assertEqual((other.slots[0]['screen'],other.slots[0]['x'],other.slots[0]['y'],other.slots[0]['width']),('left',120,130,340))
        self.assertFalse(other.sources);self.assertFalse(other.mining);self.assertFalse(other.hotkeys_active)
        saved=json.loads(other.path.read_text());self.assertNotIn('last_damage',str(saved));self.assertNotIn('hwnd',str(saved))

    def test_reconnect_preserves_order_labels_disabled_state_and_placement(self):
        rows=[{k:v for k,v in r.items() if k in {'key','label','enabled','width'}} for r in reversed(self.state.slots)]
        rows[0].update(label='My pilot',enabled=False,width=400)
        self.state.configure({'slots':rows})
        self.state.reconcile([]);self.assertFalse(self.state.candidates())
        self.state.reconcile([{**self.sources[1],'hwnd':99},self.sources[0]])
        self.assertEqual([r['key'] for r in self.state.slots],['b','a'])
        self.assertEqual(self.state.slots[0]['label'],'My pilot');self.assertEqual([r['key'] for r in self.state.candidates()],['a'])
        with self.assertRaises(ValueError):self.state.configure({'slots':rows[:1]})

    def test_drag_after_saving_a_narrow_width_survives_refresh_done_and_restart(self):
        # The native MouseDown closure still holds the row from tile creation.
        bound_slot=self.state.slots[0]
        self.state.configure({'enabled':True})
        rows=[{k:r[k] for k in ['key','label','enabled','width']} for r in self.state.slots]
        rows[0]['width']=160
        self.state.configure({'slots':rows,'editing':True})
        self.state.place(bound_slot,180,230,160,self.screens)
        self.state.configure({'editing':False})
        self.state.reconcile(self.sources)
        current=next(r for r in self.state.slots if r['key']==bound_slot['key'])
        self.assertEqual(self.state.bounds(current,self.screens,2),(180,230,160,104))
        restored=PreviewState(self.temp.name)
        self.assertEqual(restored.bounds(restored.slots[0],self.screens,2),(180,230,160,104))

    def test_minimum_width_repeated_moves_and_saved_reorder_keep_callback_current(self):
        bound=self.state.slots[0]
        for width in [100,160,400,100]:
            rows=[{k:r[k] for k in ['key','label','enabled','width']} for r in reversed(self.state.slots)]
            next(row for row in rows if row['key']==bound['key']).update(width=width,label='Updated pilot')
            self.state.configure({'enabled':True,'slots':rows,'editing':True})
            self.state.place(bound,-1700,180,width,self.screens)
            self.state.configure({'editing':False})
            live=next(row for row in self.state.slots if row['key']==bound['key'])
            self.assertEqual(self.state.bounds(live,self.screens,2),(-1700,180,width,round(width/2)+24))
            self.assertEqual(bound['label'],'Updated pilot')
        self.assertEqual(PreviewState(self.temp.name).slots,[dict(row) for row in self.state.slots])
        saved=self.state.path.read_bytes()
        rows=[dict(row) for row in self.state.slots];rows[0]['width']=99
        with self.assertRaises(ValueError):self.state.configure({'slots':rows})
        self.assertEqual(self.state.path.read_bytes(),saved)
        self.assertEqual(next(row for row in self.state.slots if row['key']==bound['key'])['width'],100)

    def test_cycling_skips_offline_and_disabled_sources_and_wraps_both_ways(self):
        self.assertEqual(self.state.next_slot('a',1)['key'],'b');self.assertEqual(self.state.next_slot('a',-1)['key'],'b')
        self.assertEqual(self.state.next_slot(None,1)['key'],'a');self.assertEqual(self.state.next_slot(None,-1)['key'],'b')
        self.state.slots[1]['enabled']=False
        self.assertEqual(self.state.next_slot('b',1)['key'],'a')
        self.state.reconcile([]);self.assertIsNone(self.state.next_slot('a',1))
        with self.assertRaises(ValueError):self.state.next_slot('a',0)

    def test_bad_settings_are_atomic_and_never_overwrite_saved_settings(self):
        saved=self.state.path.read_bytes()
        for options in [{'enabled':1},{'fps':True},{'fps':11},{'next_key':{'code':17,'modifiers':0}},
                        {'next_key':{'code':65,'modifiers':1}}, {'next_key':self.state.previous_key},
                        {'slots':[self.state.slots[0]]},{'slots':[self.state.slots[0],self.state.slots[0]]},
                        {'only_eve':False,'slots':[]},{'slots':[{},{}]},{'unknown':1}]:
            with self.subTest(options=options),self.assertRaises(ValueError):self.state.configure(options)
            self.assertEqual(self.state.path.read_bytes(),saved);self.assertTrue(self.state.only_eve)
        for key in [{'code':True,'modifiers':0},{'code':256,'modifiers':0},{'code':65,'modifiers':-1}]:
            with self.assertRaises(ValueError):shortcut(key)

    def test_disconnected_monitor_bounds_remain_visible(self):
        slot=self.state.slots[0]
        self.state.place(slot,-1800,130,340,self.screens)
        self.assertEqual(self.state.bounds(slot,self.screens,2),(-1800,130,340,194))
        left,top,width,height=self.state.bounds(slot,self.screens[1:],2)
        self.assertTrue(0<=left<=1920-width);self.assertTrue(0<=top<=1040-height)
        slot.update(x=20000,y=20000,width=900)
        self.assertEqual(self.state.bounds(slot,self.screens[1:],2),(1020,566,900,474))

    def test_single_key_shortcuts_only_apply_to_foreground_eve_and_capture_suspends(self):
        self.state.configure({'enabled':True,'next_key':{'code':75,'modifiers':0},'previous_key':{'code':72,'modifiers':512}})
        self.assertEqual(self.state.match(75,0,False),0);self.assertEqual(self.state.match(75,0,True),1)
        self.assertEqual(self.state.match(72,512,False),0);self.assertEqual(self.state.match(72,512,True),-1)
        self.assertEqual(self.state.match(75,4096,True),0)
        self.state.capturing_key=True;self.assertEqual(self.state.match(75,0,True),0)
        self.state.capturing_key=False;self.state.editing=True;self.assertEqual(self.state.match(75,0,True),0)
        self.state.editing=False;self.state.enabled=False;self.assertEqual(self.state.match(75,0,True),0)

    def test_hook_consumes_only_matching_physical_keys_without_repeating_cycles(self):
        self.state.configure({'enabled':True,'next_key':{'code':75,'modifiers':0}})
        events=queue.SimpleQueue();hook=ShortcutHook(None,self.state,events)
        self.assertFalse(hook.process(65,True,0,True));self.assertFalse(hook.process(75,True,0,False))
        self.assertFalse(hook.process(75,True,0,True,injected=True))
        self.assertTrue(hook.process(75,True,0,True));self.assertTrue(hook.process(75,True,0,True))
        self.assertEqual(events.get_nowait(),1);self.assertTrue(events.empty())
        # Release still consumed after focus/modifiers change, never types into chat.
        self.assertTrue(hook.process(75,False,4096,False));self.assertFalse(hook.process(75,False,0,True))
        self.assertTrue(hook.process(75,True,0,True));self.assertEqual(events.get_nowait(),1)

    def test_modified_shortcut_can_work_globally_but_exact_modifiers_required(self):
        self.state.configure({'enabled':True})
        self.assertEqual(self.state.match(34,6144,False),1);self.assertEqual(self.state.match(33,6144,False),-1)
        self.assertEqual(self.state.match(34,6144|512,False),0)

    def test_damage_clock_uses_original_character_name_and_expires_after_ten_seconds(self):
        self.state.slots[0]['label']='Custom label'
        self.state.sync_mining({'enabled':True,'characters':[{'name':'PILOT A','alerts':[{'kind':'crystal_broken','id':'break'}],'last_damage':1000}]})
        self.now=1000.1;self.assertTrue(self.state.flashing('a'));self.assertFalse(self.state.flashing('b'))
        self.now=1000.6;self.assertFalse(self.state.flashing('a'))
        self.now=1010.1;self.assertFalse(self.state.flashing('a'))
        self.assertEqual(self.state.alerts('a')['alerts'][0]['kind'],'crystal_broken')
        self.state.sync_mining({'enabled':True,'characters':[{'name':'Pilot A','alerts':[],'last_damage':1010}]})
        self.assertTrue(self.state.flashing('a'))
        self.state.sync_mining({'enabled':False,'characters':[]});self.assertFalse(self.state.flashing('a'))

    def test_invalid_mining_snapshots_never_change_existing_alerts(self):
        self.state.sync_mining({'enabled':True,'characters':[{'name':'Pilot A','alerts':[{'kind':'module_stopped','id':'pause'}]}]})
        old=self.state.mining
        for row in [{'last_damage':True},{'last_damage':float('nan')},{'last_damage':1003},{'alerts':[{'kind':'execute','id':'x'}]},{'name':None}]:
            with self.subTest(row=row),self.assertRaises(ValueError):self.state.sync_mining({'enabled':True,'characters':[{'name':'Pilot A','alerts':[],**row}]})
            self.assertIs(self.state.mining,old)



class DiscoveryTests(unittest.TestCase):
    def test_discovery_rejects_spoofed_titles_and_uses_executable_identity(self):
        import ctypes
        from ctypes import wintypes
        from unittest.mock import Mock
        from muhely.windows_preview import Win32
        api=Win32.__new__(Win32);api.W=wintypes;api.enum_proc=lambda fn:fn
        api.user=Mock();api.kernel=Mock()
        titles={11:'EVE - Real pilot',12:'EVE - Spoofed pilot',13:'Other application',14:'EVE - Real pilot'}
        api.user.IsWindowVisible.return_value=True
        api.user.GetWindowTextLengthW.side_effect=lambda hwnd:len(titles[hwnd])
        api.user.GetWindowTextW.side_effect=lambda hwnd,out,size:setattr(out,'value',titles[hwnd])
        api.user.GetWindowThreadProcessId.side_effect=lambda hwnd,out:setattr(out._obj,'value',hwnd+100)
        api.user.EnumWindows.side_effect=lambda callback,param:[callback(hwnd,param) for hwnd in titles]
        api.kernel.OpenProcess.side_effect=lambda flags,inherit,pid:pid
        def image(handle,flags,out,size):
            out.value='/fake/exefile.exe' if handle in (111,114) else '/fake/python.exe';return True
        api.kernel.QueryFullProcessImageNameW.side_effect=image
        rows=api.discover()
        self.assertEqual([r['hwnd'] for r in rows],[11,14])
        self.assertNotEqual(rows[0]['key'],rows[1]['key'])
        self.assertTrue(rows[1]['key'].endswith(':114'))
        self.assertEqual(api.kernel.CloseHandle.call_count,3)

    def test_pending_shortcut_cannot_switch_after_disable_editing_or_key_capture(self):
        from unittest.mock import Mock
        from muhely.windows_preview import NativePreview
        with tempfile.TemporaryDirectory() as folder:
            state=PreviewState(folder)
            for changes in [{'enabled':False},{'enabled':True,'editing':True},{'enabled':True,'editing':False,'capturing_key':True}]:
                preview=NativePreview.__new__(NativePreview)
                preview.disposed=False;preview.tiles={};preview.events=queue.SimpleQueue();preview.events.put(1)
                preview.state=state;preview.cycle=Mock();preview.refresh=Mock();preview._visibility=Mock()
                preview.callback=Mock();preview.last_poll=preview.last_scan=10**20;preview.last_phase=None
                for key,value in changes.items():setattr(state,key,value)
                preview._tick();preview.cycle.assert_not_called();self.assertTrue(preview.events.empty())


if __name__=='__main__':unittest.main()
