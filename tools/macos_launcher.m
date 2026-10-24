#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>
#import <UserNotifications/UserNotifications.h>
#include <sys/stat.h>
#import "macos_intel_overlay.m"

// macOS-only window shell. The Python service and shared UI remain portable.
@interface EveWindow : NSObject <NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandlerWithReply, UNUserNotificationCenterDelegate>
@property NSWindow *window;
@property WKWebView *web;
@property NSURL *origin;
@property BOOL ready, quitting, stopped, startupFailed, starting, stopping, quitAfterStartup;
@property NSString *language;
@property NSMenuItem *settingsItem, *quitItem, *reloadItem, *editRoot, *viewRoot, *windowRoot, *minimizeItem, *zoomItem, *frontItem;
@property NSMenu *editMenu;
@property UNUserNotificationCenter *notificationCenter;
@property NSTimer *notificationMonitor;
@property NSTimer *intelMonitor;
@property NSDictionary *pendingNotification;
@property EveIntelOverlay *intelOverlay;
@property NSMutableDictionary<NSString *,NSWindow *> *intelWindows;
@property NSMutableDictionary<NSString *,WKWebView *> *intelViews;
- (BOOL)localURL:(NSURL *)url;
- (BOOL)managedWeb:(WKWebView *)web;
- (BOOL)openIntelWindow:(NSString *)kind options:(NSDictionary *)options;
- (void)openExternalURL:(NSURL *)url;
- (void)startBackend:(void (^)(BOOL))completion;
- (void)stopServiceAndTerminate;
- (void)completeStop:(NSNumber *)success;
- (void)saveFile:(NSDictionary *)body reply:(void (^)(id, NSString *))reply;
@end

static BOOL RunBackend(NSString **logPath, NSArray<NSString *> *arguments) {
    umask(0077);
    NSString *folder = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/EVE Muhely"];
    NSFileManager *files = NSFileManager.defaultManager;
    [files createDirectoryAtPath:folder withIntermediateDirectories:YES attributes:nil error:NULL];
    NSString *log = [folder stringByAppendingPathComponent:@"launcher.log"];
    if (logPath) *logPath = log;
    if (![files fileExistsAtPath:log]) [files createFileAtPath:log contents:nil attributes:nil];
    NSFileHandle *output = [NSFileHandle fileHandleForWritingAtPath:log];
    [output seekToEndOfFile];
    NSTask *task = [NSTask new];
    NSString *backend = [NSBundle.mainBundle.executablePath.stringByDeletingLastPathComponent stringByAppendingPathComponent:@"eve-backend"];
    if ([files isExecutableFileAtPath:backend]) {
        // Public releases carry their own frozen Python service.
        task.executableURL = [NSURL fileURLWithPath:backend];
        task.arguments = arguments;
    } else {
        // Developer installations retain their existing source/runtime launcher.
        task.executableURL = [NSURL fileURLWithPath:@"/bin/bash"];
        task.arguments = [@[[NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"eve_muhely/Inditas.command"]] arrayByAddingObjectsFromArray:arguments];
    }
    task.standardOutput = output; task.standardError = output;
    task.standardInput = NSFileHandle.fileHandleWithNullDevice;
    NSError *failure = nil;
    BOOL ok = [task launchAndReturnError:&failure];
    if (ok) [task waitUntilExit];
    [output closeFile];
    return ok && task.terminationStatus == 0;
}
static BOOL StartService(NSString **logPath) {return RunBackend(logPath,@[@"--no-browser"]);}

@implementation EveWindow
- (BOOL)managedWeb:(WKWebView *)web {return web==self.web || [self.intelViews.allValues containsObject:web];}
- (void)registerWindow:(NSWindow *)window {
    window.excludedFromWindowsMenu=NO;window.tabbingMode=NSWindowTabbingModeDisallowed;
    [NSApp addWindowsItem:window title:window.title filename:NO];
}
- (void)openExternalURL:(NSURL *)url {[NSWorkspace.sharedWorkspace openURL:url];}
- (BOOL)openIntelWindow:(NSString *)kind options:(NSDictionary *)options {
    if(![@[@"map",@"chat"] containsObject:kind]||!self.ready)return NO;
    if(!self.intelWindows){self.intelWindows=[NSMutableDictionary new];self.intelViews=[NSMutableDictionary new];}
    NSURLComponents *url=[NSURLComponents componentsWithURL:self.origin resolvingAgainstBaseURL:NO];
    NSMutableArray<NSURLQueryItem *> *query=[NSMutableArray arrayWithObject:[NSURLQueryItem queryItemWithName:@"intel_window" value:kind]];
    NSMutableDictionary *safe=[NSMutableDictionary new];
    for(NSString *key in @[@"character_id",@"center",@"region"]){id value=options[key];if([value isKindOfClass:NSNumber.class]&&[value longLongValue]>=0&&[value longLongValue]<=INT32_MAX&&[value doubleValue]==[value longLongValue]){safe[key]=value;if([value longLongValue]>0)[query addObject:[NSURLQueryItem queryItemWithName:key value:[value stringValue]]];}}
    safe[@"history"]=@([options[@"history"] isEqual:@YES]);if([safe[@"history"] boolValue])[query addObject:[NSURLQueryItem queryItemWithName:@"history" value:@"1"]];
    if(self.intelWindows[kind]){[self.intelViews[kind] callAsyncJavaScript:@"if(typeof applyIntelWindowOptions==='function')await applyIntelWindowOptions(options)" arguments:@{ @"options":safe } inFrame:nil inContentWorld:WKContentWorld.pageWorld completionHandler:nil];[self.intelWindows[kind] makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];return YES;}
    url.queryItems=query;
    BOOL map=[kind isEqual:@"map"];
    NSWindow *window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,map?1280:750,map?880:680) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable|NSWindowStyleMaskResizable backing:NSBackingStoreBuffered defer:NO];
    window.title=[self english]?(map?@"EVE Workshop · System map":@"EVE Workshop · Intel chat"):(map?@"EVE Műhely · Rendszertérkép":@"EVE Műhely · Intelchat");window.minSize=NSMakeSize(map?720:440,400);window.delegate=self;window.releasedWhenClosed=NO;window.appearance=self.window.appearance;window.backgroundColor=self.window.backgroundColor;
    WKWebViewConfiguration *config=[WKWebViewConfiguration new];config.websiteDataStore=self.web.configuration.websiteDataStore;config.processPool=self.web.configuration.processPool;
    [config.userContentController addScriptMessageHandlerWithReply:self contentWorld:WKContentWorld.pageWorld name:@"eveDesktop"];
    WKWebView *web=[[WKWebView alloc] initWithFrame:window.contentView.bounds configuration:config];web.autoresizingMask=NSViewWidthSizable|NSViewHeightSizable;web.navigationDelegate=self;web.UIDelegate=self;window.contentView=web;
    self.intelWindows[kind]=window;self.intelViews[kind]=web;[self registerWindow:window];[window center];[window setFrameAutosaveName:[@"EVEWorkshopIntel-" stringByAppendingString:kind]];[window makeKeyAndOrderFront:nil];[web loadRequest:[NSURLRequest requestWithURL:url.URL]];return YES;
}
- (BOOL)localURL:(NSURL *)url {
    return [url.scheme isEqualToString:@"http"] && [url.host isEqualToString:@"127.0.0.1"] &&
        [url.port isEqual:self.origin.port] && !url.user && !url.password;
}
- (NSString *)notificationStatusName:(UNAuthorizationStatus)status {
    switch(status){
        case UNAuthorizationStatusAuthorized:case UNAuthorizationStatusProvisional:return @"authorized";
        case UNAuthorizationStatusDenied:return @"denied";
        default:return @"notDetermined";
    }
}
- (void)showNotificationTarget:(NSDictionary *)target {
    self.pendingNotification=target;
    [self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];
    if(!self.ready)return;
    self.pendingNotification=nil;
    [self.web callAsyncJavaScript:@"for(let i=0;i<100&&(typeof state==='undefined'||!state);i++)await new Promise(r=>setTimeout(r,50));if(typeof state!=='undefined'&&state)openNotificationCenter(scope,category);"
        arguments:@{ @"scope":target[@"scope"]?:@"personal",@"category":target[@"category"]?:@"all" } inFrame:nil inContentWorld:WKContentWorld.pageWorld completionHandler:nil];
}
- (void)userNotificationCenter:(UNUserNotificationCenter *)center willPresentNotification:(UNNotification *)notification withCompletionHandler:(void (^)(UNNotificationPresentationOptions))done {
    done(UNNotificationPresentationOptionBanner|UNNotificationPresentationOptionList|(notification.request.content.sound?UNNotificationPresentationOptionSound:0));
}
- (void)userNotificationCenter:(UNUserNotificationCenter *)center didReceiveNotificationResponse:(UNNotificationResponse *)response withCompletionHandler:(void (^)(void))done {
    NSDictionary *target=response.notification.request.content.userInfo;
    dispatch_async(dispatch_get_main_queue(),^{[self showNotificationTarget:target];done();});
}
- (void)notificationAction:(NSDictionary *)body reply:(void (^)(id,NSString *))reply {
    BOOL english=[self english];
    if(!self.notificationCenter){if([body[@"action"] isEqual:@"notify"])reply(nil,(english?@"macOS notifications are not authorized.":@"A macOS-értesítések nincsenek engedélyezve."));else reply(@{ @"status":@"unavailable" },nil);return;}
    NSString *action=body[@"action"];
    if([action isEqual:@"requestNotifications"]){
        [self.notificationCenter requestAuthorizationWithOptions:(UNAuthorizationOptionAlert|UNAuthorizationOptionSound) completionHandler:^(BOOL allowed,NSError *error){
            [self.notificationCenter getNotificationSettingsWithCompletionHandler:^(UNNotificationSettings *settings){dispatch_async(dispatch_get_main_queue(),^{reply(error?nil:@{ @"status":[self notificationStatusName:settings.authorizationStatus] },error?(english?@"Could not authorize macOS notifications.":@"A macOS-értesítések engedélyezése nem sikerült."):nil);});}];
        }];return;
    }
    [self.notificationCenter getNotificationSettingsWithCompletionHandler:^(UNNotificationSettings *settings){
        if([action isEqual:@"notificationStatus"]){dispatch_async(dispatch_get_main_queue(),^{reply(@{ @"status":[self notificationStatusName:settings.authorizationStatus] },nil);});return;}
        if(![[self notificationStatusName:settings.authorizationStatus] isEqual:@"authorized"]){dispatch_async(dispatch_get_main_queue(),^{reply(nil,(english?@"macOS notifications are not authorized.":@"A macOS-értesítések nincsenek engedélyezve."));});return;}
        NSString *identifier=body[@"id"],*title=body[@"title"],*text=body[@"body"],*scope=body[@"scope"],*category=body[@"category"];
        BOOL valid=[identifier isKindOfClass:NSString.class]&&identifier.length<=128&&identifier.length>0&&
            [identifier rangeOfCharacterFromSet:[NSCharacterSet characterSetWithCharactersInString:@"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-"].invertedSet].location==NSNotFound&&
            [title isKindOfClass:NSString.class]&&title.length<=200&&[text isKindOfClass:NSString.class]&&text.length<=1500&&
            [scope isKindOfClass:NSString.class]&&scope.length<=20&&([scope isEqual:@"personal"]||[scope rangeOfCharacterFromSet:NSCharacterSet.decimalDigitCharacterSet.invertedSet].location==NSNotFound)&&
            [@[@"skills",@"jobs",@"pi",@"moons",@"intel",@"implants",@"all"] containsObject:category];
        if(!valid){dispatch_async(dispatch_get_main_queue(),^{reply(nil,(english?@"Invalid system notification.":@"Hibás rendszerértesítés."));});return;}
        UNMutableNotificationContent *content=[UNMutableNotificationContent new];content.title=title;content.body=text;
        content.userInfo=@{ @"scope":scope,@"category":category };
        if([body[@"sound"] isEqual:@YES])content.sound=UNNotificationSound.defaultSound;
        UNNotificationRequest *request=[UNNotificationRequest requestWithIdentifier:identifier content:content trigger:nil];
        [self.notificationCenter addNotificationRequest:request withCompletionHandler:^(NSError *error){dispatch_async(dispatch_get_main_queue(),^{reply(error?nil:@{ @"queued":@YES },error?(english?@"macOS could not queue the notification.":@"A macOS nem tudta sorba állítani az értesítést."):nil);});}];
    }];
}
- (BOOL)english { return [self.language isEqualToString:@"en"]; }
- (void)menu {
    NSMenu *menu = [NSMenu new], *app = [NSMenu new], *edit = [NSMenu new], *view = [NSMenu new];
    NSMenuItem *appRoot = [NSMenuItem new]; appRoot.submenu = app; [menu addItem:appRoot];
    self.settingsItem = [app addItemWithTitle:([self english]?@"Settings…":@"Beállítások…") action:@selector(settings:) keyEquivalent:@","];
    self.settingsItem.target = self;
    [app addItem:NSMenuItem.separatorItem];
    self.quitItem = [app addItemWithTitle:([self english]?@"Quit EVE Workshop":@"EVE Műhely bezárása") action:@selector(terminate:) keyEquivalent:@"q"];
    NSMenuItem *editRoot = [[NSMenuItem alloc] initWithTitle:([self english]?@"Edit":@"Szerkesztés") action:nil keyEquivalent:@""]; editRoot.submenu = edit; [menu addItem:editRoot];
    for (NSArray *item in @[@[([self english]?@"Undo":@"Visszavonás"),@"undo:",@"z"],@[([self english]?@"Cut":@"Kivágás"),@"cut:",@"x"],@[([self english]?@"Copy":@"Másolás"),@"copy:",@"c"],@[([self english]?@"Paste":@"Beillesztés"),@"paste:",@"v"],@[([self english]?@"Select All":@"Összes kijelölése"),@"selectAll:",@"a"]])
        [edit addItemWithTitle:item[0] action:NSSelectorFromString(item[1]) keyEquivalent:item[2]];
    NSMenuItem *viewRoot = [[NSMenuItem alloc] initWithTitle:([self english]?@"View":@"Nézet") action:nil keyEquivalent:@""]; viewRoot.submenu = view; [menu addItem:viewRoot];
    self.reloadItem = [view addItemWithTitle:([self english]?@"Reload":@"Újratöltés") action:@selector(reload:) keyEquivalent:@"r"]; self.reloadItem.target = self;
    self.editRoot=editRoot;self.viewRoot=viewRoot;self.editMenu=edit;NSApp.mainMenu = menu;
    NSMenu *windows=[[NSMenu alloc] initWithTitle:([self english]?@"Window":@"Ablak")];
    self.windowRoot=[[NSMenuItem alloc] initWithTitle:([self english]?@"Window":@"Ablak") action:nil keyEquivalent:@""];self.windowRoot.submenu=windows;[menu addItem:self.windowRoot];NSApp.windowsMenu=windows;
    self.minimizeItem=[windows addItemWithTitle:([self english]?@"Minimize":@"Kis méret") action:@selector(performMiniaturize:) keyEquivalent:@"m"];
    self.zoomItem=[windows addItemWithTitle:([self english]?@"Zoom":@"Nagyítás") action:@selector(performZoom:) keyEquivalent:@""];
    [windows addItem:NSMenuItem.separatorItem];
    self.frontItem=[windows addItemWithTitle:([self english]?@"Bring All to Front":@"Összes ablak előre") action:@selector(arrangeInFront:) keyEquivalent:@""];
}
- (void)settings:(id)sender { [self.web evaluateJavaScript:@"openSettingsTab('appearance')" completionHandler:nil]; }
- (void)reload:(id)sender {
    [self.web evaluateJavaScript:@"typeof dirty==='undefined'||!Object.keys(dirty).length||confirm(EveI18n.t('Az új számítás eldobja a még nem alkalmazott módosításokat. Folytatod?'))" completionHandler:^(id yes,NSError *error){ if(!error && [yes boolValue]) [self.web reload]; }];
}
- (void)startBackend:(void (^)(BOOL))completion {
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0), ^{
        BOOL ok = StartService(NULL);
        dispatch_async(dispatch_get_main_queue(), ^{ completion(ok); });
    });
}
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    self.origin = [NSURL URLWithString:@"http://127.0.0.1:8765"];
    NSString *savedLanguage=[NSUserDefaults.standardUserDefaults stringForKey:@"EVEUILanguage"];
    self.language=savedLanguage?:([NSLocale.preferredLanguages.firstObject hasPrefix:@"en"]?@"en":@"hu");
    // Bare CLI smoke tests have no application identity; the installed app does.
    if(NSBundle.mainBundle.bundleIdentifier){self.notificationCenter=UNUserNotificationCenter.currentNotificationCenter;self.notificationCenter.delegate=self;}
    __weak EveWindow *weakSelf=self;
    self.notificationMonitor=[NSTimer scheduledTimerWithTimeInterval:60 repeats:YES block:^(NSTimer *timer){
        EveWindow *app=weakSelf;
        if(app.ready&&!app.quitting)[app.web evaluateJavaScript:@"if(typeof refreshNotifications==='function'&&!notificationSettingsBusy)void refreshNotifications()" completionHandler:nil];
    }];
    self.intelMonitor=[NSTimer scheduledTimerWithTimeInterval:2 repeats:YES block:^(NSTimer *timer){EveWindow *app=weakSelf;if(app.ready&&!app.quitting){[app.web evaluateJavaScript:@"if(typeof pollIntelAlerts==='function')void pollIntelAlerts();if(typeof pollImplantAlerts==='function')void pollImplantAlerts()" completionHandler:nil];for(WKWebView *web in app.intelViews.allValues)[web evaluateJavaScript:@"if(typeof pollIntelAlerts==='function')void pollIntelAlerts()" completionHandler:nil];}}];
    [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular]; [self menu];
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,1320,860) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable|NSWindowStyleMaskResizable backing:NSBackingStoreBuffered defer:NO];
    self.window.title = [self english]?@"EVE Workshop":@"EVE Műhely"; self.window.minSize = NSMakeSize(900,650); self.window.delegate = self;
    [self registerWindow:self.window];
    self.window.backgroundColor = [NSColor colorWithSRGBRed:0.071 green:0.137 blue:0.192 alpha:1];
    self.window.appearance = [NSAppearance appearanceNamed:NSAppearanceNameDarkAqua];
    [self.window center]; [self.window setFrameAutosaveName:@"EVEWorkshopMainWindow"];
    NSTextField *loading = [NSTextField labelWithString:([self english]?@"EVE Workshop · Starting…":@"EVE Műhely · Indítás…")];
    loading.textColor = NSColor.whiteColor; loading.frame = NSMakeRect(36,42,500,30); [self.window.contentView addSubview:loading];
    [self.window makeKeyAndOrderFront:nil]; [NSApp activateIgnoringOtherApps:YES];
    self.starting=YES;
    [self startBackend:^(BOOL ok){
        self.starting=NO;
        if(self.quitAfterStartup){self.quitAfterStartup=NO;[NSApp terminate:nil];return;}
        if (!ok) {
            self.startupFailed = YES;
            NSAlert *alert = [NSAlert new]; alert.messageText = ([self english]?@"EVE Workshop could not start":@"Az EVE Műhely nem indult el");
            alert.informativeText = ([self english]?@"Details: ~/Library/Application Support/EVE Muhely/launcher.log":@"Részletek: ~/Library/Application Support/EVE Muhely/launcher.log");
            [alert runModal]; [NSApp terminate:nil]; return;
        }
        WKWebViewConfiguration *config = [WKWebViewConfiguration new];
        [config.userContentController addScriptMessageHandlerWithReply:self contentWorld:WKContentWorld.pageWorld name:@"eveDesktop"];
        self.web = [[WKWebView alloc] initWithFrame:self.window.contentView.bounds configuration:config];
        self.web.autoresizingMask = NSViewWidthSizable|NSViewHeightSizable; self.web.navigationDelegate = self; self.web.UIDelegate = self;
        self.web.allowsBackForwardNavigationGestures = NO; self.window.contentView = self.web;
        [self.web loadRequest:[NSURLRequest requestWithURL:self.origin]];
    }];
}
- (void)webView:(WKWebView *)webView didFinishNavigation:(WKNavigation *)navigation {if(webView==self.web){self.ready = [self localURL:webView.URL]; self.startupFailed=NO;if(self.pendingNotification)[self showNotificationTarget:self.pendingNotification];}}
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView {if(webView==self.web)self.ready=NO;[webView reload]; }
- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    if (error.code==NSURLErrorCancelled) return;
    if(webView==self.web)self.startupFailed=YES;
    NSAlert *alert=[NSAlert new];alert.messageText=([self english]?@"Could not load the interface":@"A felület nem tölthető be");alert.informativeText=([self english]?@"Restart EVE Workshop.":@"Indítsd újra az EVE Műhely alkalmazást.");[alert runModal];
}
- (void)webView:(WKWebView *)web decidePolicyForNavigationAction:(WKNavigationAction *)action decisionHandler:(void (^)(WKNavigationActionPolicy))decide {
    NSURL *url=action.request.URL;
    if ([self localURL:url]) { decide(WKNavigationActionPolicyAllow); return; }
    decide(WKNavigationActionPolicyCancel);
    if ([@[@"https",@"http",@"webcal"] containsObject:url.scheme.lowercaseString]) [self openExternalURL:url];
}
- (WKWebView *)webView:(WKWebView *)web createWebViewWithConfiguration:(WKWebViewConfiguration *)config forNavigationAction:(WKNavigationAction *)action windowFeatures:(WKWindowFeatures *)features {
    NSURL *url=action.request.URL;
    if ([self localURL:url]) [self.web loadRequest:action.request];
    else if ([@[@"https",@"http",@"webcal"] containsObject:url.scheme.lowercaseString]) [self openExternalURL:url];
    return nil;
}
- (void)webView:(WKWebView *)web runJavaScriptConfirmPanelWithMessage:(NSString *)message initiatedByFrame:(WKFrameInfo *)frame completionHandler:(void (^)(BOOL))done {
    NSAlert *alert=[NSAlert new];alert.messageText=@"EVE Műhely";alert.informativeText=message;
    [alert addButtonWithTitle:[self english]?@"Continue":@"Folytatás"];[alert addButtonWithTitle:[self english]?@"Cancel":@"Mégse"];
    [alert beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse response){done(response==NSAlertFirstButtonReturn);}];
}
- (void)webView:(WKWebView *)web runJavaScriptAlertPanelWithMessage:(NSString *)message initiatedByFrame:(WKFrameInfo *)frame completionHandler:(void (^)(void))done {
    NSAlert *alert=[NSAlert new];alert.messageText=@"EVE Műhely";alert.informativeText=message;
    [alert beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse response){done();}];
}
- (void)webView:(WKWebView *)web runOpenPanelWithParameters:(WKOpenPanelParameters *)parameters initiatedByFrame:(WKFrameInfo *)frame completionHandler:(void (^)(NSArray<NSURL *> *))done {
    if(web!=self.web || !frame.mainFrame || ![self localURL:frame.request.URL]){done(nil);return;}
    NSOpenPanel *panel=NSOpenPanel.openPanel;panel.canChooseFiles=YES;panel.canChooseDirectories=NO;
    panel.allowsMultipleSelection=parameters.allowsMultipleSelection;panel.canCreateDirectories=NO;
    panel.allowedFileTypes=@[@"json",@"txt",@"tsv"];panel.allowsOtherFileTypes=NO;
    [panel beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse response){done(response==NSModalResponseOK?panel.URLs:nil);}];
}
- (void)saveFile:(NSDictionary *)body reply:(void (^)(id, NSString *))reply {
    NSString *name=body[@"filename"],*encoded=body[@"base64"];
    if (![name isKindOfClass:NSString.class] || ![encoded isKindOfClass:NSString.class] || encoded.length>45*1024*1024) {reply(nil,([self english]?@"Invalid file":@"Érvénytelen fájl."));return;}
    name=name.lastPathComponent;
    if (![@[@"csv",@"ics",@"md",@"json"] containsObject:name.pathExtension.lowercaseString] || name.length>200) {reply(nil,([self english]?@"Invalid file name":@"Hibás fájlnév."));return;}
    NSData *data=[[NSData alloc] initWithBase64EncodedString:encoded options:0];
    if (!data || data.length>32*1024*1024) {reply(nil,([self english]?@"Invalid file data":@"Hibás fájltartalom."));return;}
    NSSavePanel *panel=NSSavePanel.savePanel;panel.nameFieldStringValue=name;panel.canCreateDirectories=YES;
    [panel beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse response){
        if(response!=NSModalResponseOK){reply(@{ @"saved":@NO },nil);return;}
        NSError *failure=nil;BOOL ok=[data writeToURL:panel.URL options:NSDataWritingAtomic error:&failure];
        reply(ok?@{ @"saved":@YES }:nil,ok?nil:([self english]?@"The file could not be saved.":@"A fájl mentése nem sikerült."));
    }];
}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message replyHandler:(void (^)(id, NSString *))reply {
    if (!message.frameInfo.mainFrame || ![self localURL:message.frameInfo.request.URL] || ![self managedWeb:message.webView] || ![message.body isKindOfClass:NSDictionary.class]) {reply(nil,([self english]?@"Untrusted origin":@"Nem megbízható eredet."));return;}
    NSDictionary *body=message.body;NSString *action=body[@"action"];
    if(message.webView!=self.web && ![@[@"clipboard",@"preferences",@"external",@"activate",@"openIntelWindow"] containsObject:action]){reply(nil,([self english]?@"Main window action required":@"Ez a művelet csak a főablakból érhető el."));return;}
    if([@[@"intelOverlayStatus",@"configureIntelOverlay",@"syncIntelOverlay"] containsObject:action]){
        if(!self.intelOverlay)self.intelOverlay=[[EveIntelOverlay alloc] initWithDefaults:NSUserDefaults.standardUserDefaults];
        self.intelOverlay.english=[self english];self.intelOverlay.light=[self.window.appearance.name isEqual:NSAppearanceNameAqua];
        BOOL ok=YES;if([action isEqual:@"configureIntelOverlay"])ok=[self.intelOverlay configure:body[@"options"]];else if([action isEqual:@"syncIntelOverlay"])ok=[self.intelOverlay sync:body[@"data"]];
        reply(ok?[self.intelOverlay settings]:nil,ok?nil:([self english]?@"Invalid intel overlay settings":@"Érvénytelen inteljelző-beállítás."));return;
    }
    if([action isEqual:@"openIntelWindow"]){BOOL opened=[self openIntelWindow:body[@"kind"] options:[body[@"options"] isKindOfClass:NSDictionary.class]?body[@"options"]:@{}];reply(opened?@{ @"opened":@YES }:nil,opened?nil:([self english]?@"Invalid intel window.":@"Hibás intelablak."));return;}
    if([@[@"notificationStatus",@"requestNotifications",@"notify"] containsObject:action]){[self notificationAction:body reply:reply];return;}
    if ([action isEqual:@"clipboard"] && [body[@"text"] isKindOfClass:NSString.class] && [body[@"text"] length]<8*1024*1024) {
        [NSPasteboard.generalPasteboard clearContents];[NSPasteboard.generalPasteboard setString:body[@"text"] forType:NSPasteboardTypeString];reply(@YES,nil);
    } else if ([action isEqual:@"chooseIntelFolder"]) {
        NSOpenPanel *panel=[NSOpenPanel openPanel];panel.canChooseFiles=NO;panel.canChooseDirectories=YES;panel.allowsMultipleSelection=NO;panel.canCreateDirectories=NO;
        panel.message=[self english]?@"Choose the EVE Chatlogs folder to monitor.":@"Válaszd ki a figyelendő EVE Chatlogs mappát.";
        [panel beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse result){reply(result==NSModalResponseOK?@{ @"path":panel.URL.path }:@{},nil);}];
    } else if ([action isEqual:@"save"]) [self saveFile:body reply:reply];
    else if ([action isEqual:@"preferences"]) {
        self.language=[body[@"language"] isEqual:@"en"]?@"en":@"hu";
        self.window.title=[self english]?@"EVE Workshop":@"EVE Műhely";
        [NSUserDefaults.standardUserDefaults setObject:self.language forKey:@"EVEUILanguage"];
        self.window.appearance=[NSAppearance appearanceNamed:[body[@"theme"] isEqual:@"light"]?NSAppearanceNameAqua:NSAppearanceNameDarkAqua];
        for(NSString *key in self.intelWindows){NSWindow *window=self.intelWindows[key];window.appearance=self.window.appearance;BOOL map=[key isEqual:@"map"];window.title=[self english]?(map?@"EVE Workshop · System map":@"EVE Workshop · Intel chat"):(map?@"EVE Műhely · Rendszertérkép":@"EVE Műhely · Intelchat");[NSApp changeWindowsItem:window title:window.title filename:NO];}
        self.windowRoot.title=[self english]?@"Window":@"Ablak";NSApp.windowsMenu.title=self.windowRoot.title;
        self.minimizeItem.title=[self english]?@"Minimize":@"Kis méret";self.zoomItem.title=[self english]?@"Zoom":@"Nagyítás";self.frontItem.title=[self english]?@"Bring All to Front":@"Összes ablak előre";
        self.intelOverlay.english=[self english];self.intelOverlay.light=[self.window.appearance.name isEqual:NSAppearanceNameAqua];[self.intelOverlay refresh];
        self.editRoot.title=[self english]?@"Edit":@"Szerkesztés";self.viewRoot.title=[self english]?@"View":@"Nézet";
        NSArray *labels=[self english]?@[@"Undo",@"Cut",@"Copy",@"Paste",@"Select All"]:@[@"Visszavonás",@"Kivágás",@"Másolás",@"Beillesztés",@"Összes kijelölése"];
        for(NSUInteger i=0;i<labels.count;i++)[self.editMenu itemAtIndex:i].title=labels[i];
        self.settingsItem.title=[self english]?@"Settings…":@"Beállítások…";self.quitItem.title=[self english]?@"Quit EVE Workshop":@"EVE Műhely bezárása";self.reloadItem.title=[self english]?@"Reload":@"Újratöltés";reply(@YES,nil);
    } else if ([action isEqual:@"external"] && [body[@"url"] isKindOfClass:NSString.class]) {
        NSURL *url=[NSURL URLWithString:body[@"url"]];BOOL allowed=[url.scheme isEqual:@"https"] || ([self localURL:url] && [url.path hasPrefix:@"/desktop/auth/"]);
        if(allowed){[self openExternalURL:url];reply(@YES,nil);}else reply(nil,([self english]?@"Blocked URL":@"Letiltott hivatkozás."));
    } else if ([action isEqual:@"activate"]) {[self.window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];reply(@YES,nil);}
    else if ([action isEqual:@"print"]) {[[self.web printOperationWithPrintInfo:NSPrintInfo.sharedPrintInfo] runOperationModalForWindow:self.window delegate:nil didRunSelector:NULL contextInfo:NULL];reply(@YES,nil);}
    else if ([action isEqual:@"quitCheck"] && self.quitting) {
        reply(@YES,nil);
        if ([body[@"dirty"] boolValue] || [body[@"running"] boolValue]) {
            NSAlert *alert=[NSAlert new];alert.messageText=[self english]?@"Quit EVE Workshop?":@"Bezárod az EVE Műhelyt?";
            alert.informativeText=[self english]?@"There are unapplied edits or an EVE refresh is running.":@"Vannak nem alkalmazott módosítások, vagy EVE-frissítés van folyamatban.";
            [alert addButtonWithTitle:[self english]?@"Cancel":@"Mégse"];[alert addButtonWithTitle:[self english]?@"Quit":@"Bezárás"];
            if([alert runModal]!=NSAlertSecondButtonReturn){self.quitting=NO;[NSApp replyToApplicationShouldTerminate:NO];return;}
        }
        [self.web evaluateJavaScript:@"void EveDesktop.shutdown()" completionHandler:nil];
    } else if ([action isEqual:@"stopped"]) {
        reply(@YES,nil);[self stopServiceAndTerminate];
    } else if ([action isEqual:@"quitFailed"]) {
        reply(@YES,nil);self.quitting=NO;[NSApp replyToApplicationShouldTerminate:NO];
        NSAlert *alert=[NSAlert new];alert.messageText=[self english]?@"Could not stop the local service. Try again.":@"A helyi szolgáltatás nem állt le. Próbáld újra.";[alert runModal];
    } else reply(nil,([self english]?@"Unknown desktop action":@"Ismeretlen asztali művelet."));
}
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)app {
    if(self.stopped)return NSTerminateNow;
    if(self.starting){self.quitAfterStartup=YES;return NSTerminateCancel;}
    if(self.quitting)return NSTerminateCancel;
    self.quitting=YES;
    if(!self.ready){if(!self.starting)[self stopServiceAndTerminate];return NSTerminateLater;}
    [self.web evaluateJavaScript:@"void EveDesktop.prepareQuit()" completionHandler:^(id value,NSError *error){if(error)[self stopServiceAndTerminate];}];
    return NSTerminateLater;
}
- (void)stopServiceAndTerminate {
    if(self.stopping)return;self.stopping=YES;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
        BOOL ok=RunBackend(NULL,@[@"--shutdown",@"--port",self.origin.port.stringValue?:@"8765"]);
        // NSTerminateLater runs a modal run loop. A plain main-queue block can
        // remain pending there, especially before a WKWebView has been created.
        [self performSelectorOnMainThread:@selector(completeStop:) withObject:@(ok) waitUntilDone:NO modes:@[NSDefaultRunLoopMode,NSModalPanelRunLoopMode,NSEventTrackingRunLoopMode]];
    });
}
- (void)completeStop:(NSNumber *)success {
    self.stopping=NO;
    if(!success.boolValue){BOOL pending=self.quitting;self.quitting=NO;if(pending)[NSApp replyToApplicationShouldTerminate:NO];NSAlert *alert=[NSAlert new];alert.messageText=[self english]?@"Could not stop the local service. Try again.":@"A helyi szolgáltatás nem állt le. Próbáld újra.";[alert runModal];return;}
    self.stopped=YES;[self.notificationMonitor invalidate];[self.intelMonitor invalidate];[self.intelOverlay.timer invalidate];[self.intelOverlay.panel orderOut:nil];
    for(NSWindow *window in [self.intelWindows.allValues copy])[window close];
    [self.web stopLoading];
    if(self.quitting)[NSApp replyToApplicationShouldTerminate:YES];else[NSApp terminate:nil];
}
- (BOOL)windowShouldClose:(NSWindow *)window {if(window!=self.window)return YES;[NSApp terminate:nil];return NO;}
- (void)windowWillClose:(NSNotification *)note {
    [NSApp removeWindowsItem:note.object];
    for(NSString *key in [self.intelWindows.allKeys copy])if(self.intelWindows[key]==note.object){WKWebView *web=self.intelViews[key];[web stopLoading];[web.configuration.userContentController removeScriptMessageHandlerForName:@"eveDesktop"];web.navigationDelegate=nil;web.UIDelegate=nil;[self.intelViews removeObjectForKey:key];[self.intelWindows removeObjectForKey:key];break;}
}
- (BOOL)applicationShouldHandleReopen:(NSApplication *)app hasVisibleWindows:(BOOL)visible { [self.window makeKeyAndOrderFront:nil];return YES; }
@end

#ifndef EVE_WINDOW_NO_MAIN
int main(int argc,const char *argv[]) {
    @autoreleasepool {
        for(int i=1;i<argc;i++)if(strcmp(argv[i],"--no-browser")==0)return StartService(NULL)?0:1;
        NSApplication *app=NSApplication.sharedApplication;EveWindow *delegate=[EveWindow new];app.delegate=delegate;[app run];
    }
    return 0;
}
#endif
