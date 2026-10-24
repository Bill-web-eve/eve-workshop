#import <Cocoa/Cocoa.h>
#import "../tools/macos_intel_overlay.m"
static void require(BOOL ok,NSString *message){if(!ok){fprintf(stderr,"Overlay test failed: %s\n",message.UTF8String);exit(1);}}
int main(int argc,const char *argv[]){@autoreleasepool{
    [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
    NSString *suite=[@"EVEOverlayTest-" stringByAppendingString:NSUUID.UUID.UUIDString];NSUserDefaults *defaults=[[NSUserDefaults alloc] initWithSuiteName:suite];
    EveIntelOverlay *overlay=[[EveIntelOverlay alloc] initWithDefaults:defaults];overlay.english=YES;__block NSTimeInterval now=NSDate.date.timeIntervalSince1970;overlay.clock=^{return now;};
    NSDictionary *report=@{@"key":@"30000:synthetic-report",@"system":@"AC2E-3",@"pilots":@"Test Pilot",@"ships":@"Buzzard",@"character":@"Own Pilot · test",@"jumps":@2,@"when":@(now-59.9)};
    NSDictionary *(^payload)(NSArray *,NSInteger)=^NSDictionary *(NSArray *rows,NSInteger seconds){return @{@"enabled":@YES,@"seconds":@(seconds),@"items":rows};};
    require([overlay sync:payload(@[report],60)],@"valid payload");require(overlay.panel.visible,@"fresh report not visible");
    require(!overlay.panel.opaque&&!overlay.panel.hasShadow&&overlay.panel.ignoresMouseEvents&&!overlay.panel.canBecomeKeyWindow,@"transparency/click-through/focus");
    require(!(overlay.panel.styleMask&NSWindowStyleMaskTitled)&&overlay.panel.level>=NSStatusWindowLevel,@"frameless top level");
    require((overlay.panel.collectionBehavior&NSWindowCollectionBehaviorCanJoinAllSpaces)&&(overlay.panel.collectionBehavior&NSWindowCollectionBehaviorFullScreenAuxiliary),@"full-screen spaces");
    require(!overlay.panel.hidesOnDeactivate&&!overlay.panel.canHide&&overlay.panel.floatingPanel,@"game activation must not hide the panel");
    NSWindow *game=[[NSWindow alloc] initWithContentRect:NSMakeRect(20,20,400,300) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO];
    game.level=NSScreenSaverWindowLevel;[game makeKeyAndOrderFront:nil];
    [NSWorkspace.sharedWorkspace.notificationCenter postNotificationName:NSWorkspaceDidActivateApplicationNotification object:nil];
    require(overlay.panel.visible&&overlay.panel.level>game.level,@"active fullscreen-style game covered the report");
    require(NSApp.keyWindow!=overlay.panel,@"overlay stole focus on activation");
    [overlay.panel orderOut:nil];
    NSDate *limit=[NSDate dateWithTimeIntervalSinceNow:.4];
    while(!overlay.panel.visible&&limit.timeIntervalSinceNow>0)[NSRunLoop.mainRunLoop runMode:NSEventTrackingRunLoopMode beforeDate:limit];
    require(overlay.panel.visible,@"overlay timer did not restore ordering during event tracking");
    [game orderOut:nil];
    if(argc>1){[overlay.canvas display];NSBitmapImageRep *image=[overlay.canvas bitmapImageRepForCachingDisplayInRect:overlay.canvas.bounds];[overlay.canvas cacheDisplayInRect:overlay.canvas.bounds toBitmapImageRep:image];[[image representationUsingType:NSBitmapImageFileTypePNG properties:@{}] writeToFile:@(argv[1]) atomically:YES];}
    now+=.11;[overlay refresh];require(!overlay.panel.visible,@"expiry without a sync");[overlay sync:payload(@[report],60)];require(!overlay.panel.visible,@"expired report reappeared");
    [NSWorkspace.sharedWorkspace.notificationCenter postNotificationName:NSWorkspaceDidActivateApplicationNotification object:nil];require(!overlay.panel.visible,@"activation revived an expired report");
    NSMutableDictionary *fresh=[report mutableCopy];fresh[@"when"]=@(now);[overlay sync:payload(@[report,fresh],1)];require(overlay.canvas.cards.count==1,@"duplicate report");now+=1;[overlay refresh];require(!overlay.panel.visible,@"one-second duration");
    [overlay sync:@{@"enabled":@NO,@"seconds":@60,@"items":@[fresh]}];require(!overlay.panel.visible,@"disabled panel visible");
    NSMutableDictionary *regional=[fresh mutableCopy];regional[@"when"]=@(now);regional[@"jumps"]=NSNull.null;regional[@"pilots"]=@"3 kills";
    require([overlay sync:payload(@[regional],60)],@"unknown regional distance rejected");[overlay.canvas display];
    regional[@"jumps"]=@45;require([overlay sync:payload(@[regional],60)],@"regional distance above chat alert limit rejected");
    regional[@"jumps"]=@(-1);require(![overlay sync:payload(@[regional],60)],@"negative regional distance accepted");
    [overlay sync:@{@"enabled":@NO,@"seconds":@60,@"items":@[]}];
    NSDictionary *screen=[overlay settings][@"screens"][0];NSString *screenID=screen[@"id"];
    require(![overlay configure:@{@"screen_id":@"missing-screen"}],@"invalid screen accepted");require(![overlay configure:@{@"width":@900}],@"invalid width accepted");require(![overlay sync:payload(@[],0)],@"invalid duration accepted");
    require([overlay configure:@{@"screen_id":screenID,@"x":@40,@"y":@70,@"width":@340,@"editing":@YES}],@"position edit");
    require(overlay.panel.visible&&!overlay.panel.ignoresMouseEvents&&!overlay.canvas.done.hidden,@"move placeholder");
    NSRect frame=overlay.panel.frame;frame.origin.x+=15;[overlay.panel setFrame:frame display:YES];[overlay saveDraggedPosition];[overlay finish:nil];require(!overlay.panel.visible,@"empty edit mode did not close");
    NSDictionary *saved=[overlay settings][@"placement"];require(fabs([saved[@"x"] doubleValue]-55)<1,@"dragged X not saved");require([saved[@"width"] integerValue]==340,@"width not saved");
    EveIntelOverlay *restored=[[EveIntelOverlay alloc] initWithDefaults:defaults];require([[[restored settings] objectForKey:@"placement"] isEqual:saved],@"position not restored");
    overlay.screenID=@"disconnected";[overlay configure:@{@"editing":@YES}];require(NSContainsRect([overlay selectedScreen].frame,overlay.panel.frame),@"monitor fallback out of bounds");[overlay finish:nil];
    [overlay.panel orderOut:nil];[defaults removePersistentDomainForName:suite];puts("Intel overlay: exact expiry, transparent empty state, native full-screen level, click-through and saved placement passed.");
}return 0;}
