#import <Cocoa/Cocoa.h>
#import "../tools/macos_eve_preview.m"
static void require(BOOL ok,NSString *message){if(!ok){fprintf(stderr,"Preview test failed: %s\n",message.UTF8String);exit(1);}}
@interface PreviewTest : EvePreview
@property NSString *selected;
@end
@implementation PreviewTest
- (BOOL)captureAllowed{return YES;}
- (BOOL)accessibilityAllowed{return NO;}
- (void)refresh:(void(^)(void))done {if(done)done();}
- (void)startCapture:(NSString *)key {}
- (BOOL)activate:(NSString *)key {self.selected=key;return self.sources[key]!=nil;}
@end
// Regression: NSRunningApplication reports -1 for real EVE clients while
// ScreenCaptureKit correctly identifies the window owner process.
@interface PreviewApplicationStub : NSObject
@property NSString *bundleIdentifier;
@property pid_t processIdentifier;
@end
@implementation PreviewApplicationStub
@end
@interface PreviewOwnerTest : EvePreview
@property PreviewApplicationStub *application;
@property pid_t requestedPID;
@end
@implementation PreviewOwnerTest
- (BOOL)captureAllowed{return NO;}
- (BOOL)accessibilityAllowed{return YES;}
- (NSRunningApplication *)applicationForPID:(pid_t)pid{return (id)self.application;}
- (BOOL)activateApplication:(NSRunningApplication *)app ownerPID:(pid_t)pid title:(NSString *)title {self.requestedPID=pid;return app.processIdentifier==-1&&pid==11903;}
@end
int main(int argc,const char *argv[]){@autoreleasepool{
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
 NSString *suite=[@"EVEPreviewTest-" stringByAppendingString:NSUUID.UUID.UUIDString];NSUserDefaults *defaults=[[NSUserDefaults alloc] initWithSuiteName:suite];
 PreviewTest *p=[[PreviewTest alloc] initWithDefaults:defaults];p.english=YES;
 require(!p.enabled&&p.onlyEVE&&p.fps==5,@"safe disabled defaults");
 require(![p configure:@{@"enabled":@1}],@"numeric boolean accepted");
 require(![p configure:@{@"fps":@0}]&&![p configure:@{@"fps":@11}]&&![p configure:@{@"fps":@1.5}],@"invalid frame rates");
 require([p configure:@{@"next_key":@{@"code":@40,@"modifiers":@0}}],@"single K shortcut rejected");
 for(NSNumber *invalid in @[@(-1),@1.5,@YES,@1])require(![p configure:@{@"next_key":@{@"code":@40,@"modifiers":invalid}}],@"invalid modifier accepted");
 require(![p configure:@{@"next_key":p.previousKey}],@"identical shortcuts");
 require(![p configure:@{@"unrecognized":@YES}],@"unknown fields");
 p.slots=[@[[ @{@"key":@"a",@"title":@"EVE - Pilot A",@"label":@"A",@"enabled":@YES,@"width":@260} mutableCopy],[@{@"key":@"b",@"title":@"EVE - Pilot B",@"label":@"B",@"enabled":@YES,@"width":@260} mutableCopy],[@{@"key":@"c",@"title":@"EVE - Offline",@"label":@"",@"enabled":@YES,@"width":@260} mutableCopy]] mutableCopy];
 p.sources=[@{@"a":@{@"pid":@(-101),@"id":@1,@"ratio":@.5625},@"b":@{@"pid":@(-102),@"id":@2,@"ratio":@.75}} mutableCopy];
 require([p configure:@{@"enabled":@YES,@"editing":@YES}],@"valid enable");
 require(p.panels.count==2&&p.panels[@"a"].visible&&p.panels[@"b"].visible,@"enabled online clients only");
 EvePreviewPanel *panel=p.panels[@"a"];
 require(!panel.canBecomeKeyWindow&&!panel.canBecomeMainWindow&&!panel.hidesOnDeactivate&&panel.floatingPanel,@"preview must not steal focus");
 require(!(panel.styleMask&NSWindowStyleMaskTitled)&&panel.level>=NSScreenSaverWindowLevel&&(panel.collectionBehavior&NSWindowCollectionBehaviorFullScreenAuxiliary),@"fullscreen frameless panel");
 require([p cycle:1]&&[p.selected isEqual:@"a"],@"next starts with first online slot");require([p cycle:-1]&&[p.selected isEqual:@"b"],@"previous starts with last online slot");
 NSRect frame=panel.frame;frame.origin.x+=30;frame.size.width=330;[panel setFrame:frame display:YES];[p savePanel:panel];require([p.slots[0][@"width"] intValue]==330,@"drag/resize not saved");
 NSMutableArray *ordered=[NSMutableArray new];for(NSDictionary *slot in @[p.slots[1],p.slots[0],p.slots[2]])[ordered addObject:@{@"key":slot[@"key"],@"label":slot[@"label"],@"enabled":slot[@"enabled"],@"width":slot[@"width"]}];
 require([p configure:@{@"slots":ordered}],@"reorder rejected");[p cycle:1];require([p.selected isEqual:@"b"],@"cycle ignored configured order");
 NSMutableDictionary *bad=[ordered[0] mutableCopy];bad[@"width"]=@999;require(![p configure:@{@"slots":@[bad,ordered[1],ordered[2]]}],@"invalid width accepted");
 p.slots[0][@"screen"]=@"disconnected";p.slots[0][@"x"]=@1e8;p.slots[0][@"y"]=@1e8;[p renderPanels];require(NSContainsRect(NSScreen.mainScreen.visibleFrame,p.panels[@"b"].frame),@"disconnected monitor fallback outside screen");
 NSArray *alerts=@[@{@"kind":@"cargo_full",@"at":@1,@"id":@"123456789012345678901234",@"module":@"Strip Miner"},@{@"kind":@"crystal_broken",@"at":@2,@"id":@"223456789012345678901234",@"crystal":@"Common Crystal"},@{@"kind":@"rock_depleted",@"at":@3,@"id":@"323456789012345678901234"}];
 require([p syncMining:@{@"enabled":@YES,@"characters":@[@{@"name":@"PILOT A",@"alerts":alerts}]}],@"mining sync rejected");
 EvePreviewTile *warning=(id)p.panels[@"a"].contentView;require(warning.miningAlerts.count==3&&[(EvePreviewTile *)p.panels[@"b"].contentView miningAlerts].count==0,@"mining alerts attached to wrong character");require([warning.toolTip containsString:@"Cargo full"]&&[warning.toolTip containsString:@"Common Crystal"],@"missing localized mining tooltip");
 __block NSString *clicked=nil;p.miningAction=^(NSString *name,NSString *kind,NSString *identifier){clicked=[NSString stringWithFormat:@"%@/%@/%@",name,kind,identifier];};
 NSPoint crystal=NSMakePoint(NSMidX([warning miningBadgeRect:1]),NSMidY([warning miningBadgeRect:1]));NSPoint local=[warning convertPoint:crystal toView:nil];NSEvent *click=[NSEvent mouseEventWithType:NSEventTypeLeftMouseDown location:local modifierFlags:0 timestamp:0 windowNumber:warning.window.windowNumber context:nil eventNumber:1 clickCount:1 pressure:1];warning.editing=NO;[warning mouseDown:click];require([clicked isEqual:@"Pilot A/crystal_broken/223456789012345678901234"],@"crystal icon did not report replacement for correct pilot");
 require(![p syncMining:@{@"enabled":@YES,@"characters":@[@{@"name":@"Pilot A",@"alerts":@[@{@"kind":@"injected",@"at":@1}]}]}],@"unknown mining icon accepted");require(warning.miningAlerts.count==3,@"bad sync damaged existing badges");
 require([p setKeyCaptureValue:@YES]&&p.keyCapture,@"key capture rejected");require(![p setKeyCaptureValue:@1],@"numeric capture flag accepted");require([p setKeyCaptureValue:@NO]&&!p.keyCapture,@"key capture did not end");
 for(NSUInteger i=0;i<warning.miningAlerts.count;i++){NSRect badge=[warning miningBadgeRect:i];require(NSMinY(badge)>=0&&NSMaxY(badge)<=24,@"badge outside character name bar");require(NSMaxX([warning captionRect])<NSMinX([warning miningBadgeRect:0]),@"name overlaps mining badges");if(i)require(!NSIntersectsRect(badge,[warning miningBadgeRect:i-1]),@"badges overlap");}
 NSSize original=warning.frame.size;[warning setFrameSize:NSMakeSize(160,original.height)];require(NSWidth([warning captionRect])>0&&NSMaxX([warning captionRect])<NSMinX([warning miningBadgeRect:0]),@"narrow name bar layout");[warning setFrameSize:original];warning.caption=@"EVE - Alpha Joey";
 if(argc>1){EvePreviewTile *tile=(id)panel.contentView;[tile display];NSRect sample=NSMakeRect(0,0,tile.bounds.size.width,24);NSBitmapImageRep *image=[tile bitmapImageRepForCachingDisplayInRect:sample];[tile cacheDisplayInRect:sample toBitmapImageRep:image];[[image representationUsingType:NSBitmapImageFileTypePNG properties:@{}] writeToFile:@(argv[1]) atomically:YES];}
 require([p syncMining:@{@"enabled":@NO,@"characters":@[]}],@"disable mining sync failed");require(warning.miningAlerts.count==0,@"disabled mining badges retained");
 require([p configure:@{@"enabled":@NO}],@"disable failed");require(!panel.visible&&!p.editing&&p.captures.count==0&&!p.keys,@"disable did not clean up");
 PreviewTest *restored=[[PreviewTest alloc] initWithDefaults:defaults];require([restored.nextKey[@"code"] intValue]==40&&[restored.nextKey[@"modifiers"] intValue]==0,@"single-key shortcut persistence");require(restored.slots.count==3&&[restored.slots[0][@"key"] isEqual:@"b"]&&[restored.slots[1][@"width"] intValue]==330,@"layout/order persistence");
 [restored stop];[p stop];require(!p.timer.valid&&p.observers.count==0,@"shutdown cleanup");
 [defaults setObject:@{@"slots":@[@{@"key":@"bad",@"title":@"EVE",@"width":@"invalid",@"label":@42}],@"fps":@"invalid",@"enabled":@"invalid"} forKey:@"EVEPreview"];
 PreviewTest *safe=[[PreviewTest alloc] initWithDefaults:defaults];require(!safe.enabled&&safe.fps==5&&[safe.slots[0][@"width"] intValue]==260,@"malformed saved data");[safe stop];
 PreviewOwnerTest *owner=[[PreviewOwnerTest alloc] initWithDefaults:defaults];owner.application=[PreviewApplicationStub new];owner.application.bundleIdentifier=@"com.ccpgames.eveonline";owner.application.processIdentifier=-1;
 owner.sources[@"game"]=@{@"pid":@11903};require([owner activate:@"game"]&&owner.requestedPID==11903,@"activation must use the real window owner, not the invalid application PID");
 owner.requestedPID=0;owner.application.bundleIdentifier=@"unrelated.app";require(![owner activate:@"game"]&&owner.requestedPID==0,@"unrelated application activation");[owner stop];
 [defaults removePersistentDomainForName:suite];puts("eve-preview: settings validation, ordered cycling, native panels, geometry, persistence and shutdown passed.");
}return 0;}
