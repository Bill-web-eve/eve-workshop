// Frameless, click-through intel panel. Uses only public AppKit window APIs.
@interface EveOverlayPanel : NSPanel
@end
@implementation EveOverlayPanel
- (BOOL)canBecomeKeyWindow { return NO; }
- (BOOL)canBecomeMainWindow { return NO; }
@end

@interface EveOverlayCanvas : NSView
@property NSArray<NSDictionary *> *cards;
@property BOOL editing, light, english;
@property NSButton *done;
@end
@implementation EveOverlayCanvas
- (BOOL)isFlipped {return YES;}
- (BOOL)isOpaque {return NO;}
- (BOOL)mouseDownCanMoveWindow {return YES;}
- (void)label:(NSString *)text rect:(NSRect)rect size:(CGFloat)size color:(NSColor *)color bold:(BOOL)bold {
    NSMutableParagraphStyle *style=[NSMutableParagraphStyle new];style.lineBreakMode=NSLineBreakByTruncatingTail;
    [text drawInRect:rect withAttributes:@{NSFontAttributeName:[NSFont systemFontOfSize:size weight:bold?NSFontWeightSemibold:NSFontWeightRegular],NSForegroundColorAttributeName:color,NSParagraphStyleAttributeName:style}];
}
- (void)drawRect:(NSRect)dirtyRect {
    [NSColor.clearColor set];NSRectFillUsingOperation(self.bounds,NSCompositingOperationCopy);
    NSColor *paper=self.light?[NSColor colorWithWhite:.97 alpha:.98]:[NSColor colorWithSRGBRed:.07 green:.13 blue:.18 alpha:.98];
    NSColor *ink=self.light?NSColor.labelColor:[NSColor colorWithWhite:.91 alpha:1];
    NSColor *muted=self.light?NSColor.secondaryLabelColor:[NSColor colorWithWhite:.66 alpha:1];
    NSColor *accent=[NSColor colorWithSRGBRed:.48 green:.78 blue:.86 alpha:1];
    CGFloat width=self.bounds.size.width,y=0;
    if(self.editing){
        NSBezierPath *box=[NSBezierPath bezierPathWithRoundedRect:NSInsetRect(self.bounds,1,1) xRadius:8 yRadius:8];[paper setFill];[box fill];[accent setStroke];box.lineWidth=2;[box stroke];
        [self label:self.english?@"Intel overlay · positioning":@"Inteljelző · elhelyezés" rect:NSMakeRect(12,12,width-105,22) size:13 color:ink bold:YES];
        [self label:self.english?@"Drag this panel to any monitor.":@"Húzd ezt az ablakot a kívánt monitorra." rect:NSMakeRect(12,44,width-24,20) size:12 color:accent bold:NO];
        [self label:self.english?@"Done saves the position and restores click-through.":@"A Kész elmenti a helyet és átengedi a kattintásokat." rect:NSMakeRect(12,70,width-24,32) size:10 color:muted bold:NO];
        return;
    }
    for(NSDictionary *card in self.cards){
        BOOL ships=[card[@"ships"] length]>0;CGFloat height=ships?86:68;
        NSRect rect=NSMakeRect(1,y+1,width-2,height-2);NSBezierPath *box=[NSBezierPath bezierPathWithRoundedRect:rect xRadius:7 yRadius:7];[paper setFill];[box fill];[[NSColor colorWithSRGBRed:.9 green:.51 blue:.44 alpha:1] setStroke];[box stroke];
        [self label:card[@"system"] rect:NSMakeRect(11,y+7,width-66,18) size:13 color:ink bold:YES];
        [self label:[card[@"jumps"] isKindOfClass:NSNumber.class]?[NSString stringWithFormat:@"%@j",card[@"jumps"]]:@"–" rect:NSMakeRect(width-42,y+8,34,16) size:11 color:muted bold:YES];
        [self label:card[@"pilots"] rect:NSMakeRect(11,y+28,width-22,18) size:12 color:accent bold:YES];
        if(ships)[self label:card[@"ships"] rect:NSMakeRect(11,y+47,width-22,16) size:11 color:ink bold:NO];
        [self label:card[@"character"] rect:NSMakeRect(11,y+height-19,width-22,14) size:10 color:muted bold:NO];
        y+=height+6;
    }
}
- (void)layout {[super layout];self.done.frame=NSMakeRect(self.bounds.size.width-82,8,70,26);}
@end

@interface EveIntelOverlay : NSObject <NSWindowDelegate>
@property EveOverlayPanel *panel;
@property EveOverlayCanvas *canvas;
@property NSUserDefaults *defaults;
@property NSTimer *timer;
@property NSArray<NSDictionary *> *items;
@property NSMutableDictionary *placements;
@property NSString *screenID;
@property BOOL enabled,editing,applyingFrame,english,light;
@property NSInteger seconds;
@property NSTimeInterval (^clock)(void);
- (instancetype)initWithDefaults:(NSUserDefaults *)defaults;
- (NSDictionary *)settings;
- (BOOL)configure:(NSDictionary *)options;
- (BOOL)sync:(NSDictionary *)data;
- (void)refresh;
@end
@implementation EveIntelOverlay
- (instancetype)initWithDefaults:(NSUserDefaults *)defaults {
    if((self=[super init])){
        self.defaults=defaults;self.placements=[[defaults dictionaryForKey:@"EVEIntelOverlayPlacements"] mutableCopy]?:[NSMutableDictionary new];self.screenID=[defaults stringForKey:@"EVEIntelOverlayScreen"];
        self.items=@[];self.seconds=60;self.clock=^{return NSDate.date.timeIntervalSince1970;};
        __weak EveIntelOverlay *weakSelf=self;self.timer=[NSTimer timerWithTimeInterval:.25 repeats:YES block:^(NSTimer *timer){[weakSelf refresh];}];
        [NSRunLoop.mainRunLoop addTimer:self.timer forMode:NSRunLoopCommonModes];
        [NSRunLoop.mainRunLoop addTimer:self.timer forMode:NSEventTrackingRunLoopMode];
        [NSRunLoop.mainRunLoop addTimer:self.timer forMode:NSModalPanelRunLoopMode];
        [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(screensChanged:) name:NSApplicationDidChangeScreenParametersNotification object:nil];
        [NSWorkspace.sharedWorkspace.notificationCenter addObserver:self selector:@selector(screensChanged:) name:NSWorkspaceDidActivateApplicationNotification object:nil];
        [NSWorkspace.sharedWorkspace.notificationCenter addObserver:self selector:@selector(screensChanged:) name:NSWorkspaceActiveSpaceDidChangeNotification object:nil];
    }return self;
}
- (void)dealloc {[self.timer invalidate];[NSNotificationCenter.defaultCenter removeObserver:self];[NSWorkspace.sharedWorkspace.notificationCenter removeObserver:self];}
- (NSString *)identifier:(NSScreen *)screen {return [screen.deviceDescription[@"NSScreenNumber"] stringValue]?:@"main";}
- (NSScreen *)selectedScreen {for(NSScreen *screen in NSScreen.screens)if([[self identifier:screen] isEqual:self.screenID])return screen;return NSScreen.mainScreen?:NSScreen.screens.firstObject;}
- (NSDictionary *)placement:(NSScreen *)screen {
    NSDictionary *saved=self.placements[[self identifier:screen]];
    return saved?:@{@"x":@(MAX(0,screen.frame.size.width-350)),@"y":@80,@"width":@330};
}
- (NSDictionary *)settings {
    NSMutableArray *screens=[NSMutableArray new];for(NSScreen *screen in NSScreen.screens){NSDictionary *pos=[self placement:screen];[screens addObject:@{@"id":[self identifier:screen],@"name":screen.localizedName,@"width":@(screen.frame.size.width),@"height":@(screen.frame.size.height),@"placement":pos}];}
    NSScreen *selected=[self selectedScreen];return @{@"screens":screens,@"screen_id":selected?[self identifier:selected]:@"",@"placement":selected?[self placement:selected]:@{},@"editing":@(self.editing)};
}
- (void)ensurePanel {
    if(self.panel)return;
    self.panel=[[EveOverlayPanel alloc] initWithContentRect:NSMakeRect(0,0,330,120) styleMask:NSWindowStyleMaskBorderless|NSWindowStyleMaskNonactivatingPanel backing:NSBackingStoreBuffered defer:NO];
    self.panel.title=@"EVE Intel Overlay";self.panel.opaque=NO;self.panel.backgroundColor=NSColor.clearColor;self.panel.hasShadow=NO;self.panel.hidesOnDeactivate=NO;self.panel.becomesKeyOnlyIfNeeded=YES;
    self.panel.floatingPanel=YES;self.panel.canHide=NO;self.panel.level=NSScreenSaverWindowLevel+1;
    self.panel.collectionBehavior=NSWindowCollectionBehaviorCanJoinAllSpaces|NSWindowCollectionBehaviorFullScreenAuxiliary|NSWindowCollectionBehaviorIgnoresCycle;
    if(@available(macOS 13.0,*))self.panel.collectionBehavior|=NSWindowCollectionBehaviorCanJoinAllApplications;
    self.panel.excludedFromWindowsMenu=YES;self.panel.tabbingMode=NSWindowTabbingModeDisallowed;self.panel.releasedWhenClosed=NO;self.panel.delegate=self;
    self.canvas=[[EveOverlayCanvas alloc] initWithFrame:self.panel.contentView.bounds];self.canvas.autoresizingMask=NSViewWidthSizable|NSViewHeightSizable;self.panel.contentView=self.canvas;
    self.canvas.done=[NSButton buttonWithTitle:@"Done" target:self action:@selector(finish:)];[self.canvas addSubview:self.canvas.done];
}
- (void)persist {
    [self.defaults setObject:self.placements forKey:@"EVEIntelOverlayPlacements"];if(self.screenID)[self.defaults setObject:self.screenID forKey:@"EVEIntelOverlayScreen"];
}
- (void)saveDraggedPosition {
    if(!self.editing||self.applyingFrame)return;
    NSRect frame=self.panel.frame;NSScreen *screen=self.panel.screen;
    for(NSScreen *candidate in NSScreen.screens)if(NSPointInRect(NSMakePoint(NSMidX(frame),NSMidY(frame)),candidate.frame)){screen=candidate;break;}
    if(!screen)return;self.screenID=[self identifier:screen];self.placements[self.screenID]=@{@"x":@(MAX(0,NSMinX(frame)-NSMinX(screen.frame))),@"y":@(MAX(0,NSMaxY(screen.frame)-NSMaxY(frame))),@"width":@(frame.size.width)};[self persist];
}
- (void)windowDidMove:(NSNotification *)note {[self saveDraggedPosition];}
- (void)windowDidChangeScreen:(NSNotification *)note {[self saveDraggedPosition];}
- (void)screensChanged:(NSNotification *)note {[self refresh];}
- (void)finish:(id)sender {[self saveDraggedPosition];self.editing=NO;[self refresh];}
- (BOOL)configure:(NSDictionary *)options {
    if(![options isKindOfClass:NSDictionary.class])return NO;
    NSSet *keys=[NSSet setWithArray:@[@"screen_id",@"x",@"y",@"width",@"editing"]];for(id key in options)if(![keys containsObject:key])return NO;
    NSScreen *screen=[self selectedScreen];if(options[@"screen_id"]){screen=nil;for(NSScreen *candidate in NSScreen.screens)if([[self identifier:candidate] isEqual:options[@"screen_id"]])screen=candidate;}
    if(!screen)return NO;
    NSMutableDictionary *pos=[[self placement:screen] mutableCopy];
    for(NSString *key in @[@"x",@"y",@"width"]){id value=options[key];if(!value)continue;if(![value isKindOfClass:NSNumber.class]||!isfinite([value doubleValue])||[value doubleValue]<0||[value doubleValue]>20000)return NO;pos[key]=value;}
    if([pos[@"width"] doubleValue]<260||[pos[@"width"] doubleValue]>600)return NO;
    if(options[@"editing"]&&![options[@"editing"] isKindOfClass:NSNumber.class])return NO;
    self.screenID=[self identifier:screen];self.placements[self.screenID]=pos;if(options[@"editing"])self.editing=[options[@"editing"] boolValue];[self persist];[self refresh];return YES;
}
- (BOOL)sync:(NSDictionary *)data {
    if(![data isKindOfClass:NSDictionary.class]||![data[@"enabled"] isKindOfClass:NSNumber.class]||![data[@"seconds"] isKindOfClass:NSNumber.class]||![data[@"items"] isKindOfClass:NSArray.class]||[data[@"items"] count]>3000)return NO;
    double seconds=[data[@"seconds"] doubleValue];if(!isfinite(seconds)||seconds<1||seconds>3600||floor(seconds)!=seconds)return NO;
    NSMutableArray *items=[NSMutableArray new];
    for(id row in data[@"items"]){
        if(![row isKindOfClass:NSDictionary.class])return NO;
        for(NSString *key in @[@"key",@"system",@"pilots",@"ships",@"character"]){if(![row[key] isKindOfClass:NSString.class]||[row[key] length]>2000)return NO;}
        if(![row[@"when"] isKindOfClass:NSNumber.class]||!isfinite([row[@"when"] doubleValue]))return NO;
        id jumps=row[@"jumps"];if(jumps!=NSNull.null&&(![jumps isKindOfClass:NSNumber.class]||!isfinite([jumps doubleValue])||[jumps doubleValue]<0||[jumps doubleValue]>10000||floor([jumps doubleValue])!=[jumps doubleValue]))return NO;
        [items addObject:row];
    }
    self.enabled=[data[@"enabled"] boolValue];self.seconds=(NSInteger)seconds;self.items=items;[self refresh];return YES;
}
- (void)refresh {
    NSTimeInterval now=self.clock();NSMutableDictionary *unique=[NSMutableDictionary new];
    if(self.enabled)for(NSDictionary *row in self.items){NSTimeInterval at=[row[@"when"] doubleValue];if(at<=now&&now<at+self.seconds){NSDictionary *old=unique[row[@"key"]];NSInteger jumps=[row[@"jumps"] isKindOfClass:NSNumber.class]?[row[@"jumps"] integerValue]:NSIntegerMax,oldJumps=[old[@"jumps"] isKindOfClass:NSNumber.class]?[old[@"jumps"] integerValue]:NSIntegerMax;if(!old||jumps<oldJumps)unique[row[@"key"]]=row;}}
    NSArray *cards=[[unique allValues] sortedArrayUsingComparator:^NSComparisonResult(NSDictionary *a,NSDictionary *b){NSComparisonResult order=[b[@"when"] compare:a[@"when"]];return order==NSOrderedSame?[a[@"key"] compare:b[@"key"]]:order;}];
    if(cards.count>5)cards=[cards subarrayWithRange:NSMakeRange(0,5)];
    if(!self.editing&&!cards.count){[self.panel orderOut:nil];return;}
    NSScreen *screen=[self selectedScreen];if(!screen)return;[self ensurePanel];NSDictionary *pos=[self placement:screen];
    CGFloat width=MIN(screen.frame.size.width,[pos[@"width"] doubleValue]),height=self.editing?112:0;
    if(!self.editing)for(NSDictionary *card in cards)height+=([card[@"ships"] length]?86:68)+6;
    if(!self.editing)height-=6;height=MIN(MAX(60,height),screen.frame.size.height-10);
    CGFloat x=MAX(0,MIN(screen.frame.size.width-width,[pos[@"x"] doubleValue])),y=MAX(0,MIN(screen.frame.size.height-height,[pos[@"y"] doubleValue]));
    NSRect frame=NSMakeRect(NSMinX(screen.frame)+x,NSMaxY(screen.frame)-y-height,width,height);
    self.applyingFrame=YES;if(!NSEqualRects(frame,self.panel.frame))[self.panel setFrame:frame display:YES];self.applyingFrame=NO;
    self.panel.ignoresMouseEvents=!self.editing;self.panel.movableByWindowBackground=self.editing;
    self.panel.appearance=[NSAppearance appearanceNamed:self.light?NSAppearanceNameAqua:NSAppearanceNameDarkAqua];
    BOOL changed=self.canvas.editing!=self.editing||self.canvas.english!=self.english||self.canvas.light!=self.light||![self.canvas.cards isEqual:cards];
    self.canvas.cards=cards;self.canvas.editing=self.editing;self.canvas.english=self.english;self.canvas.light=self.light;self.canvas.done.hidden=!self.editing;self.canvas.done.title=self.english?@"Done":@"Kész";
    // Another app can raise a borderless game window without making this panel
    // invisible. Reassert its order while cards are alive, without taking focus.
    if(changed)self.canvas.needsDisplay=YES;[self.panel orderFrontRegardless];
}
@end
