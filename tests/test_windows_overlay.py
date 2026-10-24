import json
from pathlib import Path
import tempfile
import unittest
from muhely.windows_overlay import OverlayState


SCREENS=[{'id':'main','name':'Main','left':0,'top':0,'width':1920,'height':1080,'primary':True,'work':(0,0,1920,1040)},
         {'id':'left','name':'Left','left':-1280,'top':-200,'width':1280,'height':1024,'work':(-1280,-200,1280,984)}]


def report(key='one',when=1000,jumps=2,**kw):
    return {'key':key,'when':when,'system':'J5A-IX','pilots':'A pilot','ships':'Buzzard','character':'Own pilot','jumps':jumps,**kw}


class WindowsOverlayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.now=1000;self.model=OverlayState(self.tmp.name,lambda:self.now)

    def sync(self,items,**kw):self.model.sync({'enabled':True,'seconds':60,'items':items,**kw})

    def test_expiry_uses_original_timestamp_not_poll_or_launch_time(self):
        self.sync([report(when=950)]);self.assertEqual(len(self.model.cards()),1)
        self.now=1009.99;self.assertEqual(len(self.model.cards()),1)
        self.now=1010;self.assertEqual(self.model.cards(),[])
        self.sync([report(when=950)]);self.assertEqual(self.model.cards(),[])

    def test_disable_immediately_clears_reports_and_future_reports_stay_hidden(self):
        self.sync([report()]);self.assertTrue(self.model.cards())
        self.sync([report()],enabled=False);self.assertEqual(self.model.items,[]);self.assertEqual(self.model.cards(),[])
        self.sync([report(when=1001)]);self.assertEqual(self.model.cards(),[])

    def test_five_newest_unique_reports_choose_nearest_character(self):
        rows=[report(str(i),when=1000-i) for i in range(10)]
        rows.extend([report('0',jumps=1),report('0',jumps=None)])
        self.sync(rows);cards=self.model.cards()
        self.assertEqual([r['key'] for r in cards],['0','1','2','3','4']);self.assertEqual(cards[0]['jumps'],1)

    def test_null_distance_kill_batch_has_no_currency_or_unknown_fields(self):
        self.sync([report(jumps=None,cents='99999')]);self.assertIsNone(self.model.cards()[0]['jumps'])
        self.assertNotIn('cents',self.model.cards()[0])

    def test_invalid_sync_never_mutates_a_visible_report(self):
        self.sync([report()])
        invalid=[{'enabled':'yes'},{'seconds':0},{'seconds':3601},{'seconds':1.2},{'seconds':True},
                 {'items':[report(when=float('nan'))]},{'items':[report(jumps=-1)]},{'items':[report(jumps=True)]},
                 {'items':[report(pilots='x'*2001)]},{'items':[None]},{'items':[report()]*3001}]
        for patch in invalid:
            with self.subTest(patch=list(patch)),self.assertRaises(ValueError):self.model.sync({'enabled':True,'seconds':60,'items':[report()],**patch})
            self.assertEqual(self.model.cards()[0]['key'],'one');self.assertEqual(self.model.seconds,60)

    def test_seconds_can_be_one_or_one_hour(self):
        self.sync([report()],seconds=1);self.now=1001;self.assertEqual(self.model.cards(),[])
        self.sync([report()],seconds=3600);self.now=4599;self.assertTrue(self.model.cards())
        self.now=4600;self.assertEqual(self.model.cards(),[])

    def test_per_display_placement_persists_without_reports_or_edit_mode(self):
        self.model.configure({'screen_id':'left','x':25,'y':50,'width':400,'editing':True},SCREENS)
        self.sync([report()]);reloaded=OverlayState(self.tmp.name)
        self.assertEqual(reloaded.settings(SCREENS)['screen_id'],'left')
        self.assertEqual(reloaded.placement(SCREENS[1]),{'x':25,'y':50,'width':400})
        self.assertFalse(reloaded.editing);self.assertFalse(reloaded.enabled);self.assertEqual(reloaded.items,[])
        saved=json.loads(self.model.path.read_text());self.assertEqual(set(saved),{'screen_id','placements'})
        self.assertNotIn('pilot',self.model.path.read_text())

    def test_drag_to_negative_coordinate_monitor_uses_relative_coordinates(self):
        self.model.dragged(-1200,-150,330,SCREENS)
        self.assertEqual(self.model.settings(SCREENS)['screen_id'],'left')
        self.assertEqual(self.model.placement(SCREENS[1]),{'x':80,'y':50,'width':330})
        self.assertEqual(self.model.bounds(SCREENS[1],86),(-1200,-150,330,86))

    def test_offscreen_placement_clamps_to_work_area_and_disconnected_display_falls_back(self):
        self.model.configure({'screen_id':'left','x':20000,'y':20000,'width':600},SCREENS)
        self.assertEqual(self.model.bounds(SCREENS[1],112),(-600,672,600,112))
        self.assertEqual(self.model.settings(SCREENS[:1])['screen_id'],'main')
        self.assertEqual(self.model.bounds(SCREENS[0],500),(1570,80,330,500))
        self.assertEqual(self.model.placement(SCREENS[1])['x'],20000)

    def test_invalid_placement_or_display_does_not_change_saved_position(self):
        for options in [{'x':float('inf')},{'x':True},{'x':-1},{'width':601},{'width':259},{'screen_id':'gone'},{'editing':1},{'file':'arbitrary'}]:
            with self.subTest(options=options),self.assertRaises(ValueError):self.model.configure(options,SCREENS)
            self.assertEqual(self.model.placements,{})
        self.assertFalse(self.model.path.exists())

    def test_corrupt_local_placement_can_be_replaced(self):
        self.model.path.write_text('{bad json');model=OverlayState(self.tmp.name)
        self.assertEqual(model.settings(SCREENS)['screen_id'],'main')
        model.configure({'x':20,'width':330},SCREENS);self.assertEqual(json.loads(model.path.read_text())['placements']['main']['x'],20)


if __name__=='__main__':unittest.main()
