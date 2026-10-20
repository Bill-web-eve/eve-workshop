#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>
#include <sys/stat.h>

// macOS-only window shell. The Python service and shared UI remain portable.
@interface EveWindow : NSObject <NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandlerWithReply>
@property NSWindow *window;
@property WKWebView *web;
@property NSURL *origin;
@property BOOL ready, quitting, stopped, startupFailed;
@property NSString *language;
@property NSMenuItem *settingsItem, *quitItem, *reloadItem, *editRoot, *viewRoot;
@property NSMenu *editMenu;
- (BOOL)localURL:(NSURL *)url;
- (void)startBackend:(void (^)(BOOL))completion;
- (void)saveFile:(NSDictionary *)body reply:(void (^)(id, NSString *))reply;
@end

static BOOL StartService(NSString **logPath) {
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
    task.executableURL = [NSURL fileURLWithPath:@"/bin/bash"];
    task.arguments = @[[NSBundle.mainBundle.resourcePath stringByAppendingPathComponent:@"eve_muhely/Inditas.command"], @"--no-browser"];
    task.standardOutput = output; task.standardError = output;
    task.standardInput = NSFileHandle.fileHandleWithNullDevice;
    NSError *failure = nil;
    BOOL ok = [task launchAndReturnError:&failure];
    if (ok) [task waitUntilExit];
    [output closeFile];
    return ok && task.terminationStatus == 0;
}

@implementation EveWindow
- (BOOL)localURL:(NSURL *)url {
    return [url.scheme isEqualToString:@"http"] && [url.host isEqualToString:@"127.0.0.1"] &&
        [url.port isEqual:self.origin.port] && !url.user && !url.password;
}
- (BOOL)english { return [self.language isEqualToString:@"en"]; }
- (void)menu {
    NSMenu *menu = [NSMenu new], *app = [NSMenu new], *edit = [NSMenu new], *view = [NSMenu new];
    NSMenuItem *appRoot = [NSMenuItem new]; appRoot.submenu = app; [menu addItem:appRoot];
    self.settingsItem = [app addItemWithTitle:@"Beállítások…" action:@selector(settings:) keyEquivalent:@","];
    self.settingsItem.target = self;
    [app addItem:NSMenuItem.separatorItem];
    self.quitItem = [app addItemWithTitle:@"EVE Műhely bezárása" action:@selector(terminate:) keyEquivalent:@"q"];
    NSMenuItem *editRoot = [[NSMenuItem alloc] initWithTitle:@"Edit" action:nil keyEquivalent:@""]; editRoot.submenu = edit; [menu addItem:editRoot];
    for (NSArray *item in @[@[@"Undo",@"undo:",@"z"],@[@"Cut",@"cut:",@"x"],@[@"Copy",@"copy:",@"c"],@[@"Paste",@"paste:",@"v"],@[@"Select All",@"selectAll:",@"a"]])
        [edit addItemWithTitle:item[0] action:NSSelectorFromString(item[1]) keyEquivalent:item[2]];
    NSMenuItem *viewRoot = [[NSMenuItem alloc] initWithTitle:@"View" action:nil keyEquivalent:@""]; viewRoot.submenu = view; [menu addItem:viewRoot];
    self.reloadItem = [view addItemWithTitle:@"Újratöltés" action:@selector(reload:) keyEquivalent:@"r"]; self.reloadItem.target = self;
    self.editRoot=editRoot;self.viewRoot=viewRoot;self.editMenu=edit;NSApp.mainMenu = menu;
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
    self.origin = [NSURL URLWithString:@"http://127.0.0.1:8765"]; self.language = @"hu";
    [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular]; [self menu];
    self.window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,1320,860) styleMask:NSWindowStyleMaskTitled|NSWindowStyleMaskClosable|NSWindowStyleMaskMiniaturizable|NSWindowStyleMaskResizable backing:NSBackingStoreBuffered defer:NO];
    self.window.title = @"EVE Műhely"; self.window.minSize = NSMakeSize(900,650); self.window.delegate = self;
    self.window.backgroundColor = [NSColor colorWithSRGBRed:0.071 green:0.137 blue:0.192 alpha:1];
    self.window.appearance = [NSAppearance appearanceNamed:NSAppearanceNameDarkAqua];
    [self.window center]; [self.window setFrameAutosaveName:@"EVEWorkshopMainWindow"];
    NSTextField *loading = [NSTextField labelWithString:@"EVE Műhely · Indítás / Starting…"];
    loading.textColor = NSColor.whiteColor; loading.frame = NSMakeRect(36,42,500,30); [self.window.contentView addSubview:loading];
    [self.window makeKeyAndOrderFront:nil]; [NSApp activateIgnoringOtherApps:YES];
    [self startBackend:^(BOOL ok){
        if (!ok) {
            self.startupFailed = YES;
            NSAlert *alert = [NSAlert new]; alert.messageText = @"Az EVE Műhely nem indult el / Startup failed";
            alert.informativeText = @"Részletek / Details: ~/Library/Application Support/EVE Muhely/launcher.log";
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
- (void)webView:(WKWebView *)webView didFinishNavigation:(WKNavigation *)navigation { self.ready = [self localURL:webView.URL]; self.startupFailed=NO; }
- (void)webViewWebContentProcessDidTerminate:(WKWebView *)webView { self.ready=NO;[webView reload]; }
- (void)webView:(WKWebView *)webView didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error {
    if (error.code==NSURLErrorCancelled) return;
    self.startupFailed=YES;
    NSAlert *alert=[NSAlert new];alert.messageText=@"A felület nem tölthető be / Could not load the interface";alert.informativeText=@"Indítsd újra az EVE Műhely alkalmazást / Restart EVE Workshop.";[alert runModal];
}
- (void)webView:(WKWebView *)web decidePolicyForNavigationAction:(WKNavigationAction *)action decisionHandler:(void (^)(WKNavigationActionPolicy))decide {
    NSURL *url=action.request.URL;
    if ([self localURL:url]) { decide(WKNavigationActionPolicyAllow); return; }
    decide(WKNavigationActionPolicyCancel);
    if ([@[@"https",@"http",@"webcal"] containsObject:url.scheme.lowercaseString]) [NSWorkspace.sharedWorkspace openURL:url];
}
- (WKWebView *)webView:(WKWebView *)web createWebViewWithConfiguration:(WKWebViewConfiguration *)config forNavigationAction:(WKNavigationAction *)action windowFeatures:(WKWindowFeatures *)features {
    NSURL *url=action.request.URL;
    if ([self localURL:url]) [self.web loadRequest:action.request];
    else if ([@[@"https",@"http",@"webcal"] containsObject:url.scheme.lowercaseString]) [NSWorkspace.sharedWorkspace openURL:url];
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
- (void)saveFile:(NSDictionary *)body reply:(void (^)(id, NSString *))reply {
    NSString *name=body[@"filename"],*encoded=body[@"base64"];
    if (![name isKindOfClass:NSString.class] || ![encoded isKindOfClass:NSString.class] || encoded.length>45*1024*1024) {reply(nil,@"Invalid file");return;}
    name=name.lastPathComponent;
    if (![@[@"csv",@"ics",@"md"] containsObject:name.pathExtension.lowercaseString] || name.length>200) {reply(nil,@"Invalid file name");return;}
    NSData *data=[[NSData alloc] initWithBase64EncodedString:encoded options:0];
    if (!data || data.length>32*1024*1024) {reply(nil,@"Invalid file data");return;}
    NSSavePanel *panel=NSSavePanel.savePanel;panel.nameFieldStringValue=name;panel.canCreateDirectories=YES;
    [panel beginSheetModalForWindow:self.window completionHandler:^(NSModalResponse response){
        if(response!=NSModalResponseOK){reply(@{ @"saved":@NO },nil);return;}
        NSError *failure=nil;BOOL ok=[data writeToURL:panel.URL options:NSDataWritingAtomic error:&failure];
        reply(ok?@{ @"saved":@YES }:nil,ok?nil:([self english]?@"The file could not be saved.":@"A fájl mentése nem sikerült."));
    }];
}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message replyHandler:(void (^)(id, NSString *))reply {
    if (!message.frameInfo.mainFrame || ![self localURL:message.frameInfo.request.URL] || message.webView!=self.web || ![message.body isKindOfClass:NSDictionary.class]) {reply(nil,@"Untrusted origin");return;}
    NSDictionary *body=message.body;NSString *action=body[@"action"];
    if ([action isEqual:@"clipboard"] && [body[@"text"] isKindOfClass:NSString.class] && [body[@"text"] length]<8*1024*1024) {
        [NSPasteboard.generalPasteboard clearContents];[NSPasteboard.generalPasteboard setString:body[@"text"] forType:NSPasteboardTypeString];reply(@YES,nil);
    } else if ([action isEqual:@"save"]) [self saveFile:body reply:reply];
    else if ([action isEqual:@"preferences"]) {
        self.language=[body[@"language"] isEqual:@"en"]?@"en":@"hu";
        self.window.appearance=[NSAppearance appearanceNamed:[body[@"theme"] isEqual:@"light"]?NSAppearanceNameAqua:NSAppearanceNameDarkAqua];
        self.editRoot.title=[self english]?@"Edit":@"Szerkesztés";self.viewRoot.title=[self english]?@"View":@"Nézet";
        NSArray *labels=[self english]?@[@"Undo",@"Cut",@"Copy",@"Paste",@"Select All"]:@[@"Visszavonás",@"Kivágás",@"Másolás",@"Beillesztés",@"Összes kijelölése"];
        for(NSUInteger i=0;i<labels.count;i++)[self.editMenu itemAtIndex:i].title=labels[i];
        self.settingsItem.title=[self english]?@"Settings…":@"Beállítások…";self.quitItem.title=[self english]?@"Quit EVE Workshop":@"EVE Műhely bezárása";self.reloadItem.title=[self english]?@"Reload":@"Újratöltés";reply(@YES,nil);
    } else if ([action isEqual:@"external"] && [body[@"url"] isKindOfClass:NSString.class]) {
        NSURL *url=[NSURL URLWithString:body[@"url"]];BOOL allowed=[url.scheme isEqual:@"https"] || ([self localURL:url] && [url.path hasPrefix:@"/desktop/auth/"]);
        if(allowed)reply(@([NSWorkspace.sharedWorkspace openURL:url]),nil);else reply(nil,@"Blocked URL");
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
        reply(@YES,nil);self.stopped=YES;
        dispatch_async(dispatch_get_main_queue(),^{if(self.quitting)[NSApp replyToApplicationShouldTerminate:YES];else[NSApp terminate:nil];});
    } else if ([action isEqual:@"quitFailed"]) {
        reply(@YES,nil);self.quitting=NO;[NSApp replyToApplicationShouldTerminate:NO];
        NSAlert *alert=[NSAlert new];alert.messageText=[self english]?@"Could not stop the local service. Try again.":@"A helyi szolgáltatás nem állt le. Próbáld újra.";[alert runModal];
    } else reply(nil,@"Unknown desktop action");
}
- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)app {
    if(self.stopped || self.startupFailed)return NSTerminateNow;
    if(!self.ready || self.quitting)return NSTerminateCancel;
    self.quitting=YES;
    [self.web evaluateJavaScript:@"void EveDesktop.prepareQuit()" completionHandler:^(id value,NSError *error){if(error){self.quitting=NO;[NSApp replyToApplicationShouldTerminate:NO];}}];
    return NSTerminateLater;
}
- (BOOL)windowShouldClose:(NSWindow *)window { [NSApp terminate:nil];return NO; }
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
