// Local EVE window previews. No recording, network, game injection or input forwarding.
#import <ScreenCaptureKit/ScreenCaptureKit.h>
#import <ApplicationServices/ApplicationServices.h>
#import <Carbon/Carbon.h>
#import <CoreImage/CoreImage.h>
#import <CoreMedia/CoreMedia.h>

@class EvePreview;
@interface EvePreviewPanel : NSPanel
@property NSString *slotID;
@end
@implementation EvePreviewPanel
- (BOOL)canBecomeKeyWindow{return NO;}
- (BOOL)canBecomeMainWindow{return NO;}
@end

@interface EvePreviewTile : NSView
@property(weak) EvePreview *owner;
@property NSString *slotID,*caption,*message;
@property NSImage *image;
@property NSArray<NSDictionary *> *miningAlerts;
@property BOOL editing,active,light;
@property NSTimeInterval damageUntil;
@property NSPoint dragStart;
@property NSRect initialFrame;
@property BOOL resizing,dragging;
- (NSRect)miningBadgeRect:(NSUInteger)index;
- (NSRect)captionRect;
- (BOOL)damageHighlightAt:(NSTimeInterval)now;
@end

API_AVAILABLE(macos(12.3))
@interface EvePreviewCapture : NSObject <SCStreamOutput,SCStreamDelegate>
@property SCStream *stream;
@property CIContext *context;
@property NSUInteger frames;
@property(weak) EvePreviewTile *tile;
@property BOOL closed,english,paused;
- (void)stopFeed;
@end
@implementation EvePreviewCapture
- (void)stopFeed {self.closed=YES;[self.stream stopCaptureWithCompletionHandler:nil];self.stream=nil;}
- (void)stream:(SCStream *)stream didStopWithError:(NSError *)error {dispatch_async(dispatch_get_main_queue(),^{if(!self.closed){self.paused=YES;self.tile.message=self.english?@"Capture paused":@"Előnézet szünetel";self.tile.needsDisplay=YES;}});}
- (void)stream:(SCStream *)stream didOutputSampleBuffer:(CMSampleBufferRef)sample ofType:(SCStreamOutputType)type {
    if(self.closed||type!=SCStreamOutputTypeScreen||!CMSampleBufferIsValid(sample))return;
    NSArray *attachments=(__bridge NSArray *)CMSampleBufferGetSampleAttachmentsArray(sample,NO);
    NSNumber *state=attachments.firstObject[SCStreamFrameInfoStatus];
    if(state&&state.integerValue!=SCFrameStatusComplete&&state.integerValue!=SCFrameStatusStarted)return;
    CVPixelBufferRef buffer=CMSampleBufferGetImageBuffer(sample);if(!buffer)return;
    @autoreleasepool{
        CIImage *source=[CIImage imageWithCVPixelBuffer:buffer];CGImageRef frame=[self.context createCGImage:source fromRect:source.extent];
        if(!frame)return;NSImage *image=[[NSImage alloc] initWithCGImage:frame size:NSZeroSize];CGImageRelease(frame);
        dispatch_async(dispatch_get_main_queue(),^{if(!self.closed){self.frames++;self.paused=NO;self.tile.image=image;self.tile.message=@"";self.tile.needsDisplay=YES;}});
    }
}
@end

// Match only the configured key codes/modifiers. No typed text is read or saved.
@interface EvePreviewKeys : NSObject
@property(weak) EvePreview *owner;
@property NSDictionary *nextKey,*previousKey;
@property NSMutableIndexSet *pressed;
@property NSSet<NSNumber *> *gamePIDs;
@property NSThread *thread;
@property CFMachPortRef tap;
@property CFRunLoopSourceRef source;
@property CFRunLoopRef loop;
@property BOOL stopped,hasTargets,suspended;
- (BOOL)start;
- (void)stop;
- (BOOL)active;
- (pid_t)foregroundPID;
- (CGEventRef)handleType:(CGEventType)type event:(CGEventRef)event;
@end
static CGEventRef EvePreviewKeyTap(CGEventTapProxy proxy,CGEventType type,CGEventRef event,void *context){return [(__bridge EvePreviewKeys *)context handleType:type event:event];}

@interface EvePreview : NSObject <NSWindowDelegate>
@property NSUserDefaults *defaults;
@property NSMutableArray<NSMutableDictionary *> *slots;
@property NSMutableDictionary<NSString *,NSDictionary *> *sources;
@property NSMutableDictionary<NSString *,EvePreviewPanel *> *panels;
@property NSMutableDictionary *captures;
@property NSMutableArray *observers;
@property NSTimer *timer,*damageTimer;
@property dispatch_queue_t frames;
@property BOOL enabled,editing,onlyEVE,english,light,busy,closed,applyingFrame;
@property NSInteger fps;
@property NSDictionary *nextKey,*previousKey;
@property NSString *error;
@property EvePreviewKeys *keys;
@property NSUInteger shortcutCount;
@property BOOL keyCapture;
@property NSDictionary<NSString *,NSArray *> *miningByName;
@property NSDictionary<NSString *,NSNumber *> *damageByName;
@property(copy) void (^miningAction)(NSString *,NSString *,NSString *);
- (instancetype)initWithDefaults:(NSUserDefaults *)defaults;
- (NSDictionary *)status;
- (void)refresh:(void(^)(void))done;
- (BOOL)configure:(NSDictionary *)options;
- (BOOL)activate:(NSString *)key;
- (BOOL)cycle:(NSInteger)direction;
- (void)receivedShortcut:(NSInteger)direction;
- (BOOL)syncMining:(NSDictionary *)data;
- (BOOL)updateDamageAnimation;
- (BOOL)setKeyCaptureValue:(id)value;
- (void)savePanel:(EvePreviewPanel *)panel;
- (void)stop;
@end

static BOOL EvePreviewBoolean(id value){return [value isKindOfClass:NSNumber.class]&&CFGetTypeID((__bridge CFTypeRef)value)==CFBooleanGetTypeID();}
static BOOL EvePreviewShortcut(id value){return [value isKindOfClass:NSDictionary.class]&&[value[@"code"] isKindOfClass:NSNumber.class]&&[value[@"modifiers"] isKindOfClass:NSNumber.class]&&!EvePreviewBoolean(value[@"code"])&&!EvePreviewBoolean(value[@"modifiers"])&&[value[@"modifiers"] doubleValue]==[value[@"modifiers"] integerValue]&&[value[@"code"] integerValue]>=0&&[value[@"code"] integerValue]<=126&&[value[@"code"] doubleValue]==[value[@"code"] integerValue]&&[value[@"modifiers"] integerValue]>=0&&([value[@"modifiers"] unsignedIntValue]&~(cmdKey|optionKey|controlKey|shiftKey))==0;}
static BOOL EvePreviewGlobalShortcut(NSDictionary *key){return ([key[@"modifiers"] unsignedIntValue]&(cmdKey|controlKey|optionKey))!=0;}
// Public compatibility APIs for EVE clients whose AppKit process ID is -1.
// These are used only after validating the window owner's EVE bundle identity.
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
static BOOL EvePreviewLegacyActivate(pid_t pid){ProcessSerialNumber psn;return GetProcessForPID(pid,&psn)==noErr&&SetFrontProcessWithOptions(&psn,kSetFrontProcessFrontWindowOnly|kSetFrontProcessCausedByUser)==noErr;}
static pid_t EvePreviewLegacyFrontPID(void){ProcessSerialNumber psn;pid_t pid=-1;if(GetFrontProcess(&psn)==noErr)GetProcessPID(&psn,&pid);return pid;}
#pragma clang diagnostic pop

@implementation EvePreview
- (instancetype)initWithDefaults:(NSUserDefaults *)defaults {
    if((self=[super init])){
        self.defaults=defaults;self.miningByName=@{};self.damageByName=@{};self.slots=[NSMutableArray new];self.sources=[NSMutableDictionary new];self.panels=[NSMutableDictionary new];self.captures=[NSMutableDictionary new];
        self.frames=dispatch_queue_create("EVEWorkshop.preview.frames",DISPATCH_QUEUE_SERIAL);self.fps=5;self.onlyEVE=YES;
        self.nextKey=@{@"code":@124,@"modifiers":@(controlKey|optionKey)};self.previousKey=@{@"code":@123,@"modifiers":@(controlKey|optionKey)};
        NSDictionary *saved=[defaults dictionaryForKey:@"EVEPreview"];
        if(saved){
            self.enabled=EvePreviewBoolean(saved[@"enabled"])?[saved[@"enabled"] boolValue]:NO;self.onlyEVE=EvePreviewBoolean(saved[@"only_eve"])?[saved[@"only_eve"] boolValue]:YES;
            if([saved[@"fps"] isKindOfClass:NSNumber.class]&&[saved[@"fps"] integerValue]>=1&&[saved[@"fps"] integerValue]<=10)self.fps=[saved[@"fps"] integerValue];
            if(EvePreviewShortcut(saved[@"next_key"]))self.nextKey=saved[@"next_key"];
            if(EvePreviewShortcut(saved[@"previous_key"]))self.previousKey=saved[@"previous_key"];
            for(id slot in ([saved[@"slots"] isKindOfClass:NSArray.class]?saved[@"slots"]:@[]))if([slot isKindOfClass:NSDictionary.class]&&[slot[@"key"] isKindOfClass:NSString.class]&&[slot[@"title"] isKindOfClass:NSString.class]){NSMutableDictionary *safe=[@{@"key":slot[@"key"],@"title":slot[@"title"],@"enabled":@YES,@"width":@260,@"label":@""} mutableCopy];
                if([slot[@"label"] isKindOfClass:NSString.class])safe[@"label"]=[slot[@"label"] substringToIndex:MIN(80,[slot[@"label"] length])];
                if(EvePreviewBoolean(slot[@"enabled"]))safe[@"enabled"]=slot[@"enabled"];
                for(NSString *field in @[@"width",@"x",@"y"])if([slot[field] isKindOfClass:NSNumber.class]&&isfinite([slot[field] doubleValue]))safe[field]=slot[field];
                safe[@"width"]=@(MAX(160,MIN(900,[safe[@"width"] doubleValue])));
                if([slot[@"screen"] isKindOfClass:NSString.class])safe[@"screen"]=slot[@"screen"];
                [self.slots addObject:safe];if(self.slots.count==64)break;}
        }
        __weak EvePreview *weakSelf=self;
        self.timer=[NSTimer scheduledTimerWithTimeInterval:3 repeats:YES block:^(NSTimer *t){EvePreview *p=weakSelf;if(p.enabled)[p refresh:nil];}];
        [NSRunLoop.mainRunLoop addTimer:self.timer forMode:NSRunLoopCommonModes];
        self.observers=[NSMutableArray new];
        for(NSString *name in @[NSWorkspaceDidActivateApplicationNotification,NSWorkspaceActiveSpaceDidChangeNotification]){
            id token=[NSWorkspace.sharedWorkspace.notificationCenter addObserverForName:name object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *note){[weakSelf renderPanels];}];[self.observers addObject:token];
        }
        [self.observers addObject:[NSNotificationCenter.defaultCenter addObserverForName:NSApplicationDidChangeScreenParametersNotification object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *note){[weakSelf renderPanels];}]];
        if(self.enabled)[self refresh:nil];
    }return self;
}
- (pid_t)frontPID {
    pid_t pid=NSWorkspace.sharedWorkspace.frontmostApplication.processIdentifier;
    // EVE can have a valid window owner but an NSRunningApplication PID of -1.
    if(pid<=0&&[self accessibilityAllowed]){
        AXUIElementRef system=AXUIElementCreateSystemWide();CFTypeRef focused=NULL;
        AXUIElementSetMessagingTimeout(system,.35);
        if(AXUIElementCopyAttributeValue(system,kAXFocusedApplicationAttribute,&focused)==kAXErrorSuccess){AXUIElementGetPid((AXUIElementRef)focused,&pid);CFRelease(focused);}CFRelease(system);
    }if(pid<=0)pid=EvePreviewLegacyFrontPID();return pid;
}
- (NSRunningApplication *)applicationForPID:(pid_t)pid{return [NSRunningApplication runningApplicationWithProcessIdentifier:pid];}
- (BOOL)captureAllowed{return CGPreflightScreenCaptureAccess();}
- (BOOL)accessibilityAllowed{return AXIsProcessTrusted();}
- (void)persist {[self.defaults setObject:@{@"enabled":@(self.enabled),@"only_eve":@(self.onlyEVE),@"fps":@(self.fps),@"next_key":self.nextKey,@"previous_key":self.previousKey,@"slots":self.slots} forKey:@"EVEPreview"];}
- (NSDictionary *)status {
    NSMutableArray *rows=[NSMutableArray new];pid_t front=[self frontPID];
    for(NSDictionary *slot in self.slots){NSDictionary *source=self.sources[slot[@"key"]];id capture=self.captures[slot[@"key"]];BOOL hasFrame=[(EvePreviewTile *)self.panels[slot[@"key"]].contentView image]!=nil;[rows addObject:@{@"key":slot[@"key"],@"title":slot[@"title"],@"label":slot[@"label"]?:@"",@"enabled":slot[@"enabled"]?:@YES,@"online":@(source!=nil),@"active":@(source&&[source[@"pid"] intValue]==front),@"width":slot[@"width"]?:@260,@"screen":slot[@"screen"]?:@"",@"has_frame":@(hasFrame),@"capturing":@(capture!=nil)}];}
    BOOL supported=NO;if(@available(macOS 12.3,*))supported=YES;
    return @{@"supported":@(supported),@"enabled":@(self.enabled),@"editing":@(self.editing),@"only_eve":@(self.onlyEVE),@"fps":@(self.fps),@"screen_permission":@([self captureAllowed]),@"accessibility_permission":@([self accessibilityAllowed]),@"refreshing":@(self.busy),@"error":self.error?:@"",@"next_key":self.nextKey,@"previous_key":self.previousKey,@"hotkeys_active":@([self.keys active]),@"shortcut_count":@(self.shortcutCount),@"windows":rows};
}
- (void)releaseKeys {[self.keys stop];self.keys=nil;}
- (BOOL)registerKeys {
    if(!self.enabled||![self accessibilityAllowed]){[self releaseKeys];return YES;}
    if([self.keys active])return YES;
    [self releaseKeys];
    // Reserve briefly to validate conflicts; actual delivery uses Quartz before
    // the game receives the key, rather than depending on Carbon dispatch.
    EventHotKeyRef nextRef=NULL,previousRef=NULL;EventHotKeyID next={'EVEP',1},previous={'EVEP',2};
    OSStatus first=noErr,second=noErr;
    if(EvePreviewGlobalShortcut(self.nextKey))first=RegisterEventHotKey([self.nextKey[@"code"] unsignedIntValue],[self.nextKey[@"modifiers"] unsignedIntValue],next,GetEventDispatcherTarget(),0,&nextRef);
    if(first==noErr&&EvePreviewGlobalShortcut(self.previousKey))second=RegisterEventHotKey([self.previousKey[@"code"] unsignedIntValue],[self.previousKey[@"modifiers"] unsignedIntValue],previous,GetEventDispatcherTarget(),0,&previousRef);
    if(nextRef)UnregisterEventHotKey(nextRef);if(previousRef)UnregisterEventHotKey(previousRef);
    if(first!=noErr||second!=noErr){self.error=@"hotkey_conflict";return NO;}
    EvePreviewKeys *keys=[EvePreviewKeys new];keys.owner=self;keys.nextKey=[self.nextKey copy];keys.previousKey=[self.previousKey copy];keys.suspended=self.keyCapture;self.keys=keys;
    if(![keys start]){[self releaseKeys];self.error=@"hotkey_unavailable";return NO;}return YES;
}
- (void)receivedShortcut:(NSInteger)direction {if(self.closed||!self.enabled)return;self.shortcutCount++;if(![self cycle:direction])self.error=@"activate_failed";}
- (BOOL)setKeyCaptureValue:(id)value {if(!EvePreviewBoolean(value))return NO;self.keyCapture=[value boolValue];self.keys.suspended=self.keyCapture;return YES;}
- (BOOL)syncMining:(NSDictionary *)data {
    if(![data isKindOfClass:NSDictionary.class]||!EvePreviewBoolean(data[@"enabled"])||![data[@"characters"] isKindOfClass:NSArray.class]||[data[@"characters"] count]>128)return NO;
    NSMutableDictionary *rows=[NSMutableDictionary new],*damage=[NSMutableDictionary new];
    if([data[@"enabled"] boolValue])for(id row in data[@"characters"]){
        if(![row isKindOfClass:NSDictionary.class]||![row[@"name"] isKindOfClass:NSString.class]||![row[@"name"] length]||[row[@"name"] length]>100||![row[@"alerts"] isKindOfClass:NSArray.class]||[row[@"alerts"] count]>4)return NO;
        id stamp=row[@"last_damage"];
        if(stamp&&stamp!=NSNull.null){if(![stamp isKindOfClass:NSNumber.class]||EvePreviewBoolean(stamp)||!isfinite([stamp doubleValue])||[stamp doubleValue]<0||[stamp doubleValue]>NSDate.date.timeIntervalSince1970+2)return NO;damage[[row[@"name"] lowercaseString]]=@([stamp doubleValue]+10);}
        NSMutableArray *alerts=[NSMutableArray new];NSMutableSet *kinds=[NSMutableSet new];
        for(id alert in row[@"alerts"]){
            if(![alert isKindOfClass:NSDictionary.class]||![@[@"cargo_full",@"crystal_broken",@"rock_depleted",@"module_stopped"] containsObject:alert[@"kind"]]||[kinds containsObject:alert[@"kind"]]||![alert[@"at"] isKindOfClass:NSNumber.class]||!isfinite([alert[@"at"] doubleValue])||[alert[@"at"] doubleValue]<0)return NO;
            if(![alert[@"id"] isKindOfClass:NSString.class]||[alert[@"id"] length]!=24)return NO;
            NSMutableDictionary *safe=[@{@"kind":alert[@"kind"],@"at":alert[@"at"],@"id":alert[@"id"]} mutableCopy];
            for(NSString *field in @[@"module",@"crystal"]){if(alert[field]&&(![alert[field] isKindOfClass:NSString.class]||[alert[field] length]>160))return NO;safe[field]=alert[field]?:@"";}
            [alerts addObject:safe];[kinds addObject:alert[@"kind"]];
        }
        rows[[row[@"name"] lowercaseString]]=[alerts copy];
    }
    self.miningByName=[rows copy];self.damageByName=[damage copy];[self renderPanels];return YES;
}
- (BOOL)configure:(NSDictionary *)options {
    if(![options isKindOfClass:NSDictionary.class])return NO;
    for(NSString *key in options)if(![@[@"enabled",@"editing",@"only_eve",@"fps",@"next_key",@"previous_key",@"slots"] containsObject:key])return NO;
    for(NSString *key in @[@"enabled",@"editing",@"only_eve"])if(options[key]&&!EvePreviewBoolean(options[key]))return NO;
    if(options[@"fps"]&&(![options[@"fps"] isKindOfClass:NSNumber.class]||[options[@"fps"] doubleValue]!=[options[@"fps"] integerValue]||[options[@"fps"] integerValue]<1||[options[@"fps"] integerValue]>10))return NO;
    NSDictionary *next=options[@"next_key"]?:self.nextKey,*previous=options[@"previous_key"]?:self.previousKey;
    if(!EvePreviewShortcut(next)||!EvePreviewShortcut(previous)||[next isEqual:previous])return NO;
    NSMutableArray *slots=[NSMutableArray new];
    if(options[@"slots"]){
        if(![options[@"slots"] isKindOfClass:NSArray.class]||[options[@"slots"] count]!=self.slots.count)return NO;
        NSMutableSet *seen=[NSMutableSet new];
        for(id value in options[@"slots"]){
            if(![value isKindOfClass:NSDictionary.class]||![value[@"key"] isKindOfClass:NSString.class]||[seen containsObject:value[@"key"]]||!EvePreviewBoolean(value[@"enabled"])||![value[@"label"] isKindOfClass:NSString.class]||[value[@"label"] length]>80||![value[@"width"] isKindOfClass:NSNumber.class]||!isfinite([value[@"width"] doubleValue])||[value[@"width"] doubleValue]<160||[value[@"width"] doubleValue]>900)return NO;
            NSDictionary *old=nil;for(NSDictionary *slot in self.slots)if([slot[@"key"] isEqual:value[@"key"]])old=slot;if(!old)return NO;
            NSMutableDictionary *slot=[old mutableCopy];for(NSString *key in @[@"label",@"enabled",@"width"])slot[key]=value[key];[slots addObject:slot];[seen addObject:value[@"key"]];
        }
    }else for(NSDictionary *slot in self.slots)[slots addObject:[slot mutableCopy]];
    NSDictionary *oldNext=self.nextKey,*oldPrevious=self.previousKey;BOOL oldEnabled=self.enabled;
    [self releaseKeys];self.nextKey=next;self.previousKey=previous;if(options[@"enabled"])self.enabled=[options[@"enabled"] boolValue];
    if(![self registerKeys]){NSString *failure=self.error;self.nextKey=oldNext;self.previousKey=oldPrevious;self.enabled=oldEnabled;[self registerKeys];self.error=failure;return NO;}
    BOOL restart=options[@"fps"]&&[options[@"fps"] integerValue]!=self.fps;
    if(options[@"fps"])self.fps=[options[@"fps"] integerValue];if(options[@"only_eve"])self.onlyEVE=[options[@"only_eve"] boolValue];if(options[@"editing"])self.editing=[options[@"editing"] boolValue];
    if(!self.enabled)self.editing=NO;self.slots=slots;self.error=nil;if(restart||!self.enabled)[self stopCaptures];[self persist];[self renderPanels];if(self.enabled)[self refresh:nil];return YES;
}
- (void)refresh:(void(^)(void))done {
    if(self.closed||self.busy){if(done)done();return;}
    if(![self captureAllowed]){[self renderPanels];if(done)done();return;}
    if(@available(macOS 12.3,*)){
        self.busy=YES;
        [SCShareableContent getShareableContentExcludingDesktopWindows:YES onScreenWindowsOnly:NO completionHandler:^(SCShareableContent *content,NSError *error){dispatch_async(dispatch_get_main_queue(),^{
            self.busy=NO;if(self.closed){if(done)done();return;}
            if(error){self.error=@"capture_failed";if(done)done();return;}
            NSMutableDictionary *found=[NSMutableDictionary new];NSMutableDictionary *counts=[NSMutableDictionary new];NSMutableSet *namedClients=[NSMutableSet new];
            for(SCWindow *window in content.windows)if([window.owningApplication.bundleIdentifier isEqual:@"com.ccpgames.eveonline"]&&[window.title hasPrefix:@"EVE - "]&&window.frame.size.width>=160&&window.frame.size.height>=100)[namedClients addObject:@(window.owningApplication.processID)];
            for(SCWindow *window in content.windows)if([window.owningApplication.bundleIdentifier isEqual:@"com.ccpgames.eveonline"]&&window.frame.size.width>=160&&window.frame.size.height>=100){NSString *title=window.title?:@"";counts[title]=@([counts[title] integerValue]+1);}
            for(SCWindow *window in content.windows){
                if(![window.owningApplication.bundleIdentifier isEqual:@"com.ccpgames.eveonline"]||window.frame.size.width<160||window.frame.size.height<100)continue;
                if([namedClients containsObject:@(window.owningApplication.processID)]&&![window.title hasPrefix:@"EVE - "])continue;
                NSString *title=window.title.length?window.title:@"EVE";BOOL ambiguous=[counts[window.title?:@""] integerValue]>1||[title isEqual:@"EVE"];
                NSString *identity=ambiguous?[NSString stringWithFormat:@"%@ · PID %d",title,window.owningApplication.processID]:title;
                NSMutableDictionary *slot=nil;for(NSMutableDictionary *candidate in self.slots)if([candidate[@"title"] isEqual:identity])slot=candidate;
                if(!slot){if(self.slots.count>=64)continue;slot=[@{@"key":NSUUID.UUID.UUIDString,@"title":identity,@"label":@"",@"enabled":@YES,@"width":@260} mutableCopy];[self.slots addObject:slot];}
                found[slot[@"key"]]=@{@"window":window,@"pid":@(window.owningApplication.processID),@"id":@(window.windowID),@"ratio":@(window.frame.size.height/window.frame.size.width),@"ambiguous":@(ambiguous)};
            }
            for(NSString *key in self.captures.allKeys)if(![self.sources[key][@"id"] isEqual:found[key][@"id"]]){[self.captures[key] stopFeed];[self.captures removeObjectForKey:key];}
            // Discard only untouched anonymous helper-window entries superseded by
            // the named client in the same process. User-labelled layouts survive.
            for(NSMutableDictionary *slot in [self.slots copy])if(![slot[@"label"] length]&&[slot[@"title"] hasPrefix:@"EVE · PID "]){NSString *suffix=[slot[@"title"] substringFromIndex:[@"EVE · PID " length]];if([namedClients containsObject:@(suffix.intValue)]){[self.panels[slot[@"key"]] orderOut:nil];[self.panels removeObjectForKey:slot[@"key"]];[self.slots removeObject:slot];}}
            self.sources=found;self.error=nil;[self persist];[self registerKeys];[self renderPanels];if(done)done();
        });}];
    }else if(done)done();
}
- (NSScreen *)screenForSlot:(NSDictionary *)slot {for(NSScreen *screen in NSScreen.screens)if([[screen.deviceDescription[@"NSScreenNumber"] stringValue] isEqual:slot[@"screen"]])return screen;return NSScreen.mainScreen?:NSScreen.screens.firstObject;}
- (NSRect)frameForSlot:(NSDictionary *)slot index:(NSUInteger)index {
    NSScreen *screen=[self screenForSlot:slot];NSRect bounds=screen.visibleFrame;CGFloat width=MIN([slot[@"width"] doubleValue],bounds.size.width),ratio=[self.sources[slot[@"key"]][@"ratio"] doubleValue];if(ratio<=0)ratio=.5625;
    CGFloat height=MIN(bounds.size.height,width*ratio+24),x=slot[@"x"]?[slot[@"x"] doubleValue]:MAX(0,bounds.size.width-width-12-(index/5)*(width+10)),y=slot[@"y"]?[slot[@"y"] doubleValue]:12+(index%5)*(height+10);
    return NSMakeRect(NSMinX(bounds)+MAX(0,MIN(x,bounds.size.width-width)),NSMaxY(bounds)-height-MAX(0,MIN(y,bounds.size.height-height)),width,height);
}
- (void)savePanel:(EvePreviewPanel *)panel {
    if(self.applyingFrame||!self.editing)return;NSScreen *screen=panel.screen?:NSScreen.mainScreen;
    for(NSMutableDictionary *slot in self.slots)if([slot[@"key"] isEqual:panel.slotID]){slot[@"screen"]=[screen.deviceDescription[@"NSScreenNumber"] stringValue]?:@"";slot[@"x"]=@(panel.frame.origin.x-NSMinX(screen.visibleFrame));slot[@"y"]=@(NSMaxY(screen.visibleFrame)-NSMaxY(panel.frame));slot[@"width"]=@(panel.frame.size.width);[self persist];break;}
}
- (void)windowDidMove:(NSNotification *)note {[self savePanel:note.object];}
- (void)windowDidResize:(NSNotification *)note {[self savePanel:note.object];}
- (BOOL)updateDamageAnimation {
    BOOL running=NO;NSTimeInterval now=NSDate.date.timeIntervalSince1970;
    for(EvePreviewPanel *panel in self.panels.allValues){EvePreviewTile *tile=(id)panel.contentView;if(tile.damageUntil>0)tile.needsDisplay=YES;if(self.enabled&&!self.closed&&panel.visible&&tile.damageUntil>now)running=YES;}
    if(!running){[self.damageTimer invalidate];self.damageTimer=nil;}
    return running;
}
- (void)renderPanels {
    BOOL hasTargets=NO;for(NSDictionary *slot in self.slots)if([slot[@"enabled"] boolValue]&&self.sources[slot[@"key"]])hasTargets=YES;self.keys.hasTargets=hasTargets;NSMutableSet *gamePIDs=[NSMutableSet new];for(NSDictionary *source in self.sources.allValues)if([source[@"pid"] intValue]>0)[gamePIDs addObject:source[@"pid"]];self.keys.gamePIDs=[gamePIDs copy];
    BOOL visible=self.enabled&&[self captureAllowed];pid_t front=[self frontPID];BOOL game=NO;
    for(NSDictionary *source in self.sources.allValues)if([source[@"pid"] intValue]==front)game=YES;
    for(NSUInteger index=0;index<self.slots.count;index++){
        NSMutableDictionary *slot=self.slots[index];NSString *key=slot[@"key"];NSDictionary *source=self.sources[key];EvePreviewPanel *panel=self.panels[key];
        if(!visible||![slot[@"enabled"] boolValue]||!source){[panel orderOut:nil];if(self.captures[key]){[self.captures[key] stopFeed];[self.captures removeObjectForKey:key];}continue;}
        if(!panel){panel=[[EvePreviewPanel alloc] initWithContentRect:[self frameForSlot:slot index:index] styleMask:NSWindowStyleMaskBorderless|NSWindowStyleMaskNonactivatingPanel backing:NSBackingStoreBuffered defer:NO];panel.slotID=key;panel.title=[@"eve-preview · " stringByAppendingString:slot[@"title"]];panel.delegate=self;panel.releasedWhenClosed=NO;panel.hidesOnDeactivate=NO;panel.canHide=NO;panel.floatingPanel=YES;panel.level=NSScreenSaverWindowLevel;panel.collectionBehavior=NSWindowCollectionBehaviorCanJoinAllSpaces|NSWindowCollectionBehaviorFullScreenAuxiliary|NSWindowCollectionBehaviorIgnoresCycle;if(@available(macOS 13.0,*))panel.collectionBehavior|=NSWindowCollectionBehaviorCanJoinAllApplications;panel.excludedFromWindowsMenu=YES;
            EvePreviewTile *tile=[[EvePreviewTile alloc] initWithFrame:panel.contentView.bounds];tile.owner=self;tile.slotID=key;tile.autoresizingMask=NSViewWidthSizable|NSViewHeightSizable;panel.contentView=tile;self.panels[key]=panel;}
        if(![(EvePreviewTile *)panel.contentView dragging]){self.applyingFrame=YES;[panel setFrame:[self frameForSlot:slot index:index] display:YES];self.applyingFrame=NO;}
        EvePreviewTile *tile=(id)panel.contentView;tile.caption=[slot[@"label"] length]?slot[@"label"]:slot[@"title"];tile.editing=self.editing;tile.active=[source[@"pid"] intValue]==front;tile.light=self.light;NSString *pilot=[slot[@"title"] hasPrefix:@"EVE - "]?[slot[@"title"] substringFromIndex:6]:slot[@"title"];tile.miningAlerts=self.miningByName[pilot.lowercaseString]?:@[];tile.damageUntil=[self.damageByName[pilot.lowercaseString] doubleValue];
        NSMutableArray *tips=[NSMutableArray new];NSDictionary *labels=self.english?@{@"cargo_full":@"Cargo full",@"crystal_broken":@"Crystal destroyed",@"rock_depleted":@"Asteroid depleted",@"module_stopped":@"Module not running"}:@{@"cargo_full":@"Megtelt raktér",@"crystal_broken":@"Elkopott kristály",@"rock_depleted":@"Elfogyott kő",@"module_stopped":@"Modul nem fut"};
        for(NSDictionary *alert in tile.miningAlerts){NSString *detail=[alert[@"crystal"] length]?alert[@"crystal"]:alert[@"module"];NSString *stamp=[NSDateFormatter localizedStringFromDate:[NSDate dateWithTimeIntervalSince1970:[alert[@"at"] doubleValue]] dateStyle:NSDateFormatterShortStyle timeStyle:NSDateFormatterMediumStyle];[tips addObject:[NSString stringWithFormat:@"%@ · %@ · %@",labels[alert[@"kind"]],detail,stamp]];}
        if(tile.miningAlerts.count)[tips addObject:self.english?@"Click crystal: replaced; click pause: module restarted.":@"Kristályra kattintás: kicserélve; szünetjelre kattintás: modul újraindítva."];tile.toolTip=[tips componentsJoinedByString:@"\n"];tile.needsDisplay=YES;
        if(!self.onlyEVE||game||self.editing)[panel orderFrontRegardless];else[panel orderOut:nil];
        if(!self.captures[key])[self startCapture:key];
    }
    if([self updateDamageAnimation]&&!self.damageTimer){__weak EvePreview *weakSelf=self;self.damageTimer=[NSTimer scheduledTimerWithTimeInterval:.5 repeats:YES block:^(NSTimer *timer){[weakSelf updateDamageAnimation];}];[NSRunLoop.mainRunLoop addTimer:self.damageTimer forMode:NSRunLoopCommonModes];}
}
- (void)startCapture:(NSString *)key {
    if(@available(macOS 12.3,*)){
        NSDictionary *source=self.sources[key];if(!source)return;
        EvePreviewCapture *capture=[EvePreviewCapture new];capture.english=self.english;capture.tile=(id)self.panels[key].contentView;capture.context=[CIContext contextWithOptions:@{kCIContextCacheIntermediates:@NO}];
        SCStreamConfiguration *config=[SCStreamConfiguration new];config.width=480;config.height=MAX(120,MIN(720,480*[source[@"ratio"] doubleValue]));config.minimumFrameInterval=CMTimeMake(1,(int32_t)self.fps);config.queueDepth=3;config.showsCursor=NO;
        if(@available(macOS 13.0,*))config.capturesAudio=NO;
        SCContentFilter *filter=[[SCContentFilter alloc] initWithDesktopIndependentWindow:source[@"window"]];capture.stream=[[SCStream alloc] initWithFilter:filter configuration:config delegate:capture];NSError *error=nil;
        if(![capture.stream addStreamOutput:capture type:SCStreamOutputTypeScreen sampleHandlerQueue:self.frames error:&error]){self.error=@"capture_failed";return;}
        self.captures[key]=capture;
        [capture.stream startCaptureWithCompletionHandler:^(NSError *error){if(error)dispatch_async(dispatch_get_main_queue(),^{if(self.captures[key]==capture){[capture stopFeed];[self.captures removeObjectForKey:key];self.error=@"capture_failed";}});}];
    }
}
- (BOOL)activate:(NSString *)key {
    NSDictionary *source=self.sources[key];pid_t pid=[source[@"pid"] intValue];if(!source||pid<=0||![self accessibilityAllowed])return NO;
    NSRunningApplication *game=[self applicationForPID:pid];
    if(![game.bundleIdentifier isEqual:@"com.ccpgames.eveonline"])return NO;
    NSString *title=nil;if(@available(macOS 12.3,*))title=[source[@"window"] title];
    BOOL ok=[self activateApplication:game ownerPID:pid title:title];
    self.error=ok?nil:@"activate_failed";[self renderPanels];return ok;
}
- (BOOL)activateApplication:(NSRunningApplication *)game ownerPID:(pid_t)pid title:(NSString *)title {
    // Some EVE clients expose no AX windows. Activating the verified game
    // process still focuses that client; AX raising is an optional refinement.
    BOOL ok=game.processIdentifier>0?[game activateWithOptions:0]:NO;
    if(!ok)ok=EvePreviewLegacyActivate(pid);
    // Never use game.processIdentifier here: it is -1 for some real EVE clients.
    AXUIElementRef app=AXUIElementCreateApplication(pid);AXUIElementSetMessagingTimeout(app,.35);
    if(AXUIElementSetAttributeValue(app,kAXFrontmostAttribute,kCFBooleanTrue)==kAXErrorSuccess)ok=YES;
    CFTypeRef value=NULL;AXUIElementRef target=NULL;
    if(AXUIElementCopyAttributeValue(app,kAXWindowsAttribute,&value)==kAXErrorSuccess){
        NSArray *windows=CFBridgingRelease(value);
        for(id item in windows){CFTypeRef candidate=NULL;AXUIElementSetMessagingTimeout((__bridge AXUIElementRef)item,.35);if(AXUIElementCopyAttributeValue((__bridge AXUIElementRef)item,kAXTitleAttribute,&candidate)==kAXErrorSuccess){NSString *name=CFBridgingRelease(candidate);if([name isEqual:title]){if(target){CFRelease(target);target=NULL;break;}target=(AXUIElementRef)CFRetain((__bridge CFTypeRef)item);}}}
        if(!target&&windows.count==1)target=(AXUIElementRef)CFRetain((__bridge CFTypeRef)windows.firstObject);
    }
    if(target){AXUIElementSetAttributeValue(target,kAXMinimizedAttribute,kCFBooleanFalse);if(AXUIElementPerformAction(target,kAXRaiseAction)==kAXErrorSuccess)ok=YES;CFRelease(target);}CFRelease(app);
    return ok;
}
- (BOOL)cycle:(NSInteger)direction {
    NSMutableArray *online=[NSMutableArray new];for(NSDictionary *slot in self.slots)if([slot[@"enabled"] boolValue]&&self.sources[slot[@"key"]])[online addObject:slot];if(!online.count)return NO;
    pid_t front=[self frontPID];NSInteger current=NSNotFound;
    for(NSUInteger i=0;i<online.count;i++)if([self.sources[online[i][@"key"]][@"pid"] intValue]==front)current=i;
    NSInteger next=current==NSNotFound?(direction>0?0:online.count-1):(current+direction+online.count)%online.count;
    return [self activate:online[next][@"key"]];
}
- (void)stopCaptures {for(id capture in self.captures.allValues)[capture stopFeed];[self.captures removeAllObjects];}
- (void)stop {self.closed=YES;for(id token in self.observers){[NSWorkspace.sharedWorkspace.notificationCenter removeObserver:token];[NSNotificationCenter.defaultCenter removeObserver:token];}[self.observers removeAllObjects];[self.timer invalidate];[self.damageTimer invalidate];self.damageTimer=nil;[self releaseKeys];[self stopCaptures];for(NSPanel *panel in self.panels.allValues)[panel orderOut:nil];}
@end

@implementation EvePreviewKeys
- (instancetype)init {if((self=[super init])){self.pressed=[NSMutableIndexSet new];self.gamePIDs=[NSSet new];}return self;}
- (pid_t)foregroundPID {return EvePreviewLegacyFrontPID();}
- (BOOL)active {return !self.stopped&&self.tap&&CGEventTapIsEnabled(self.tap);}
- (BOOL)start {
    _tap=CGEventTapCreate(kCGSessionEventTap,kCGHeadInsertEventTap,kCGEventTapOptionDefault,CGEventMaskBit(kCGEventKeyDown)|CGEventMaskBit(kCGEventKeyUp),EvePreviewKeyTap,(__bridge void *)self);
    if(!self.tap)return NO;
    _source=CFMachPortCreateRunLoopSource(NULL,self.tap,0);if(!self.source){[self stop];return NO;}
    self.thread=[[NSThread alloc] initWithBlock:^{@autoreleasepool{
        BOOL run=NO;CFRunLoopRef loop=CFRunLoopGetCurrent();
        @synchronized(self){if(!self.stopped){self.loop=(CFRunLoopRef)CFRetain(loop);CFRunLoopAddSource(loop,self.source,kCFRunLoopCommonModes);run=YES;}}
        if(run){CFRunLoopRun();@synchronized(self){CFRunLoopRemoveSource(loop,self.source,kCFRunLoopCommonModes);CFRelease(self.loop);self.loop=NULL;}}
        self.thread=nil;
    }}];self.thread.name=@"EVEWorkshop.preview.shortcuts";[self.thread start];return YES;
}
- (CGEventRef)handleType:(CGEventType)type event:(CGEventRef)event {
    if(self.stopped)return event;
    if(type==kCGEventTapDisabledByTimeout||type==kCGEventTapDisabledByUserInput){[self.pressed removeAllIndexes];if(self.tap)CGEventTapEnable(self.tap,true);return event;}
    if(!event||(type!=kCGEventKeyDown&&type!=kCGEventKeyUp))return event;
    NSUInteger code=(NSUInteger)CGEventGetIntegerValueField(event,kCGKeyboardEventKeycode);
    if(type==kCGEventKeyUp){if([self.pressed containsIndex:code]){[self.pressed removeIndex:code];return NULL;}return event;}
    if([self.pressed containsIndex:code])return NULL;
    if(!self.hasTargets||self.suspended)return event;
    CGEventFlags flags=CGEventGetFlags(event);UInt32 modifiers=0;
    if(flags&kCGEventFlagMaskControl)modifiers|=controlKey;if(flags&kCGEventFlagMaskAlternate)modifiers|=optionKey;
    if(flags&kCGEventFlagMaskCommand)modifiers|=cmdKey;if(flags&kCGEventFlagMaskShift)modifiers|=shiftKey;
    NSInteger direction=code==[self.nextKey[@"code"] unsignedIntegerValue]&&modifiers==[self.nextKey[@"modifiers"] unsignedIntValue]?1:code==[self.previousKey[@"code"] unsignedIntegerValue]&&modifiers==[self.previousKey[@"modifiers"] unsignedIntValue]?-1:0;
    if(!direction)return event;
    NSDictionary *shortcut=direction>0?self.nextKey:self.previousKey;
    // Bare letters and Shift-only shortcuts must never consume normal typing
    // in another app. Focus is queried here, not from a stale UI timer.
    if(!EvePreviewGlobalShortcut(shortcut)&&![self.gamePIDs containsObject:@([self foregroundPID])])return event;
    if(CGEventGetIntegerValueField(event,kCGKeyboardEventAutorepeat))return NULL;
    [self.pressed addIndex:code];
    dispatch_async(dispatch_get_main_queue(),^{EvePreview *owner=self.owner;if(!self.stopped&&owner.keys==self)[owner receivedShortcut:direction];});
    return NULL;
}
- (void)stop {@synchronized(self){self.stopped=YES;if(self.tap)CFMachPortInvalidate(self.tap);if(self.loop){CFRunLoopStop(self.loop);CFRunLoopWakeUp(self.loop);}}}
- (void)dealloc {if(_tap){CFMachPortInvalidate(_tap);CFRelease(_tap);}if(_source)CFRelease(_source);}
@end

@implementation EvePreviewTile
- (BOOL)isFlipped{return YES;}
- (BOOL)damageHighlightAt:(NSTimeInterval)now {return self.damageUntil>now&&fmod(now,1.0)<.5;}
- (NSRect)miningBadgeRect:(NSUInteger)index {return NSMakeRect(self.bounds.size.width-22*(self.miningAlerts.count-index)-4,2,20,20);}
- (NSRect)captionRect {CGFloat right=self.miningAlerts.count?NSMinX([self miningBadgeRect:0])-6:self.bounds.size.width-7;return NSMakeRect(7,4,MAX(0,right-7),17);}
- (void)drawRect:(NSRect)dirty {
    NSColor *paper=self.light?[NSColor colorWithWhite:.95 alpha:1]:[NSColor colorWithSRGBRed:.07 green:.13 blue:.18 alpha:1],*ink=self.light?NSColor.labelColor:[NSColor colorWithWhite:.9 alpha:1];[paper setFill];NSRectFill(self.bounds);
    if(self.image)[self.image drawInRect:NSInsetRect(NSMakeRect(0,24,self.bounds.size.width,self.bounds.size.height-24),2,2) fromRect:NSZeroRect operation:NSCompositingOperationSourceOver fraction:1 respectFlipped:YES hints:nil];
    NSColor *captionInk=[self damageHighlightAt:NSDate.date.timeIntervalSince1970]?(self.light?NSColor.systemRedColor:[NSColor colorWithSRGBRed:1 green:.35 blue:.35 alpha:1]):ink;
    NSString *caption=[self.caption stringByAppendingString:self.editing?@" · ↔":@""];NSMutableParagraphStyle *paragraph=[NSMutableParagraphStyle new];paragraph.lineBreakMode=NSLineBreakByTruncatingTail;[caption drawInRect:[self captionRect] withAttributes:@{NSFontAttributeName:[NSFont systemFontOfSize:11 weight:NSFontWeightSemibold],NSForegroundColorAttributeName:captionInk,NSParagraphStyleAttributeName:paragraph}];
    NSDictionary *symbols=@{@"cargo_full":@"shippingbox.fill",@"crystal_broken":@"diamond.fill",@"rock_depleted":@"mountain.2.fill",@"module_stopped":@"pause.fill"};
    for(NSUInteger i=0;i<self.miningAlerts.count;i++){
        NSDictionary *alert=self.miningAlerts[i];NSRect badge=[self miningBadgeRect:i];
        NSColor *color=[alert[@"kind"] isEqual:@"rock_depleted"]?[NSColor colorWithSRGBRed:.28 green:.37 blue:.45 alpha:.96]:[alert[@"kind"] isEqual:@"module_stopped"]?[NSColor colorWithSRGBRed:.15 green:.42 blue:.6 alpha:.96]:[alert[@"kind"] isEqual:@"cargo_full"]?[NSColor colorWithSRGBRed:.75 green:.19 blue:.18 alpha:.96]:[NSColor colorWithSRGBRed:.64 green:.38 blue:.10 alpha:.96];[color setFill];[[NSBezierPath bezierPathWithRoundedRect:badge xRadius:5 yRadius:5] fill];
        NSImage *symbol=[NSImage imageWithSystemSymbolName:symbols[alert[@"kind"]] accessibilityDescription:alert[@"kind"]];if(!symbol)symbol=[NSImage imageWithSystemSymbolName:@"triangle.fill" accessibilityDescription:alert[@"kind"]];
        [NSGraphicsContext saveGraphicsState];[[NSColor whiteColor] set];NSImage *white=[NSImage imageWithSize:NSMakeSize(16,16) flipped:NO drawingHandler:^BOOL(NSRect rect){[symbol drawInRect:rect];[NSColor.whiteColor setFill];NSRectFillUsingOperation(rect,NSCompositingOperationSourceAtop);return YES;}];[white drawInRect:NSInsetRect(badge,3,3) fromRect:NSZeroRect operation:NSCompositingOperationSourceOver fraction:1 respectFlipped:YES hints:nil];
        if([@[@"crystal_broken",@"rock_depleted"] containsObject:alert[@"kind"]]){NSBezierPath *slash=[NSBezierPath bezierPath];slash.lineWidth=2;[slash moveToPoint:NSMakePoint(NSMinX(badge)+5,NSMaxY(badge)-5)];[slash lineToPoint:NSMakePoint(NSMaxX(badge)-5,NSMinY(badge)+5)];[slash stroke];}[NSGraphicsContext restoreGraphicsState];
    }
    if(self.message.length)[self.message drawInRect:NSMakeRect(8,32,self.bounds.size.width-16,20) withAttributes:@{NSFontAttributeName:[NSFont systemFontOfSize:10],NSForegroundColorAttributeName:ink}];
    [(self.active?[NSColor colorWithSRGBRed:.94 green:.68 blue:.29 alpha:1]:[NSColor colorWithWhite:.4 alpha:1]) setStroke];NSBezierPath *border=[NSBezierPath bezierPathWithRect:NSInsetRect(self.bounds,1,1)];border.lineWidth=self.active?3:1;[border stroke];
    if(self.editing){[ink setStroke];NSBezierPath *grip=[NSBezierPath bezierPath];[grip moveToPoint:NSMakePoint(self.bounds.size.width-15,self.bounds.size.height-4)];[grip lineToPoint:NSMakePoint(self.bounds.size.width-4,self.bounds.size.height-15)];[grip stroke];}
}
- (void)mouseDown:(NSEvent *)event {
    if(!self.editing){
        NSPoint at=[self convertPoint:event.locationInWindow fromView:nil];
        for(NSUInteger i=0;i<self.miningAlerts.count;i++)if(NSPointInRect(at,[self miningBadgeRect:i])){
            NSDictionary *alert=self.miningAlerts[i];if([@[@"crystal_broken",@"module_stopped"] containsObject:alert[@"kind"]]&&self.owner.miningAction){
                NSDictionary *slot=nil;for(NSDictionary *row in self.owner.slots)if([row[@"key"] isEqual:self.slotID])slot=row;
                NSString *title=slot[@"title"];NSString *name=[title hasPrefix:@"EVE - "]?[title substringFromIndex:6]:title;
                if(name.length)self.owner.miningAction(name,alert[@"kind"],alert[@"id"]);
            }break;
        }
        [self.owner activate:self.slotID];return;
    }
    NSPoint at=[self convertPoint:event.locationInWindow fromView:nil];self.resizing=at.x>self.bounds.size.width-24&&at.y>self.bounds.size.height-24;
    self.dragging=YES;
    if(!self.resizing){[self.window performWindowDragWithEvent:event];self.dragging=NO;[self.owner savePanel:(id)self.window];return;}
    self.dragStart=NSEvent.mouseLocation;self.initialFrame=self.window.frame;
}
- (void)mouseDragged:(NSEvent *)event {
    if(!self.editing||!self.resizing)return;CGFloat width=MAX(160,MIN(900,self.initialFrame.size.width+NSEvent.mouseLocation.x-self.dragStart.x));CGFloat ratio=(self.initialFrame.size.height-24)/self.initialFrame.size.width;CGFloat height=width*ratio+24;
    [self.window setFrame:NSMakeRect(self.initialFrame.origin.x,NSMaxY(self.initialFrame)-height,width,height) display:YES];
}
- (void)mouseUp:(NSEvent *)event {if(self.editing)[self.owner savePanel:(id)self.window];self.resizing=NO;self.dragging=NO;}
@end
