// Run on macOS against a temporary, synthetic local App profile.
#define EVE_WINDOW_NO_MAIN
#import "../tools/macos_launcher.m"
static NSString *TestOrigin, *TestOutput;
@interface WindowSmoke : EveWindow <NSURLSessionTaskDelegate>
@property NSMutableArray *savedFiles;
@property NSString *copied;
@property BOOL passed;
@property BOOL progressCaptured;
@property NSMutableArray *testNotifications;
@end
@implementation WindowSmoke
- (void)fail:(NSString *)why {fprintf(stderr,"Native window smoke failed: %s\n",why.UTF8String);exit(1);}
- (void)startBackend:(void (^)(BOOL))completion {self.origin=[NSURL URLWithString:TestOrigin];self.savedFiles=[NSMutableArray new];self.testNotifications=[NSMutableArray new];completion(YES);}
- (void)URLSession:(NSURLSession *)session task:(NSURLSessionTask *)task willPerformHTTPRedirection:(NSHTTPURLResponse *)response newRequest:(NSURLRequest *)request completionHandler:(void (^)(NSURLRequest *))completion {completion(nil);}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message replyHandler:(void (^)(id,NSString *))reply {
    if (![self localURL:message.frameInfo.request.URL] || !message.frameInfo.mainFrame) {[super userContentController:controller didReceiveScriptMessage:message replyHandler:reply];return;}
    NSDictionary *body=message.body;
    if ([body[@"action"] isEqual:@"notificationStatus"]) {reply(@{ @"status":@"authorized" },nil);return;}
    if ([body[@"action"] isEqual:@"notify"]) {[self.testNotifications addObject:body];reply(@{ @"queued":@YES },nil);return;}
    if ([body[@"action"] isEqual:@"requestNotifications"]) {[self fail:@"Unexpected OS permission request"];return;}
    if ([body[@"action"] isEqual:@"activitySnapshot"]) {
        [self.web takeSnapshotWithConfiguration:nil completionHandler:^(NSImage *img,NSError *error){
            if(error){[self fail:error.description];return;}
            NSBitmapImageRep *bitmap=[[NSBitmapImageRep alloc] initWithData:img.TIFFRepresentation];
            self.progressCaptured=[[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}] writeToFile:[TestOutput stringByAppendingString:@".progress.png"] atomically:YES];reply(@YES,nil);
        }];return;
    }
    if ([body[@"action"] isEqual:@"clipboard"]) {self.copied=body[@"text"];reply(@YES,nil);return;}
    if ([body[@"action"] isEqual:@"save"]) {[self.savedFiles addObject:body];reply(@{ @"saved":@YES },nil);return;}
    if ([body[@"action"] isEqual:@"external"]) {
        NSURL *url=[NSURL URLWithString:body[@"url"]];if(![self localURL:url]){[self fail:@"External access attempted"];return;}
        NSURLSession *session=[NSURLSession sessionWithConfiguration:NSURLSessionConfiguration.ephemeralSessionConfiguration delegate:self delegateQueue:NSOperationQueue.mainQueue];
        [[session dataTaskWithURL:url completionHandler:^(NSData *data,NSURLResponse *response,NSError *error){
            NSString *location=((NSHTTPURLResponse *)response).allHeaderFields[@"Location"];
            NSURLComponents *components=[NSURLComponents componentsWithString:location];NSString *state=nil;
            for(NSURLQueryItem *item in components.queryItems)if([item.name isEqual:@"state"])state=item.value;
            if(error || !state){[self fail:@"Browser handoff failed"];return;}
            NSURL *callback=[NSURL URLWithString:[NSString stringWithFormat:@"%@/callback?state=%@&code=synthetic",TestOrigin,state]];
            [[session dataTaskWithURL:callback completionHandler:^(NSData *result,NSURLResponse *r,NSError *e){
                dispatch_async(dispatch_get_main_queue(),^{if(e || ((NSHTTPURLResponse *)r).statusCode!=200)[self fail:@"Callback failed"];else reply(@YES,nil);});
            }] resume];
        }] resume];return;
    }
    [super userContentController:controller didReceiveScriptMessage:message replyHandler:reply];
}
- (void)webView:(WKWebView *)web didFinishNavigation:(WKNavigation *)navigation {
    [super webView:web didFinishNavigation:navigation];
    NSString *script=@"const wait=ms=>new Promise(r=>setTimeout(r,ms));for(let i=0;i<100&&(!state);i++)await wait(40);if(!state)throw Error('No state');"
    "EveI18n.setLanguage('hu');EveTheme.setTheme('dark');if(document.querySelector('.sidebar [data-ui-language]'))throw Error('Sidebar language control');"
    "openSettingsTab('appearance');document.querySelector('[data-ui-language=en]').click();document.querySelector('[data-theme-toggle]').click();await wait(50);"
    "if(document.documentElement.lang!=='en'||EveTheme.theme!=='light')throw Error('Preferences');"
    "productId=590;productName='Inquisitor';productActivity='manufacturing';EveNumbers.set($('#target-quantity'),5);await calculate();navigate('schedule');"
    "const saved=await api('/api/plans/save',{product_id:590,quantity:5,name:'Native test plan',manufacturer_id:0});await reloadState();render();await openSavedPlan(saved.id);"
    "if(view!=='schedule'||!document.querySelector('.schedule-setup>.plan-selector'))throw Error('Plan navigation');"
    "await copyItemName('Ferrofluid');csv([['Ferrofluid',25]],['Product','Quantity'],'native-test');await wait(100);"
    "const a=document.createElement('a');a.href='/api/moons/calendar.ics?lang=en';a.download='eve-moons.ics';document.body.append(a);a.click();await wait(100);a.remove();"
    "sessionStorage.setItem('eve-muhely-auth-return','settings:connection');const auth=await api('/api/auth/start',{});await openEveAuthorization(auth);"
    "if(view!=='settings'||settingsTab!=='connection')throw Error('Authorization return');"
    "await refreshNotifications(false);openNotificationCenter('personal','skills');await wait(50);if(!$('.notification-table')||!$('#view-content').textContent.includes('Test Pilot 2'))throw Error('Personal notifications');"
    "openNotificationCenter('99','jobs');await wait(50);if(!$('.notification-table')||!$('#view-content').textContent.includes('Inquisitor'))throw Error('Corp notifications');if($('#view-content').textContent.includes('Megnyitás'))throw Error('Untranslated notification action');"
    "await api('/api/notifications/preferences',{os_enabled:true,auto_refresh:false});await refreshNotifications();await refreshNotifications();"
    "openSettingsTab('notifications');await wait(50);if(!$('#notification-test')||document.querySelector('#view-content').textContent.includes('Értesítések'))throw Error('Notification settings/language');"
    "$('#notification-test').click();await wait(100);await api('/api/notifications/sync',{manual:true});await wait(900);"
    "if($('#activity-panel').hidden||$('#activity-panel').getAttribute('aria-busy')!=='true'||!$('#activity-panel').textContent.includes('Test Pilot'))throw Error('Missing live activity progress');"
    "await window.webkit.messageHandlers.eveDesktop.postMessage({action:'activitySnapshot'});"
    "for(let i=0;i<100;i++){const a=await api('/api/activity');if(!a.task.running){EveActivity.task(a.task);break;}await wait(100);}"
    "if(!$('#activity-panel').textContent.includes('Warning'))throw Error('Missing partial outcome');return {native:EveDesktop.active,language:EveI18n.language,theme:EveTheme.theme,characters:state.characters.length};";
    [web callAsyncJavaScript:script arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld completionHandler:^(id result,NSError *error){
        if(error){[self fail:error.description];return;}
        if(![self.copied isEqual:@"Ferrofluid"] || self.savedFiles.count!=2){[self fail:@"Copy/export bridge"];return;}
        if(![self.window.appearance.name isEqual:NSAppearanceNameAqua] || ![self.settingsItem.title isEqual:@"Settings…"]){[self fail:@"Native appearance/menu"];return;}
        for(NSString *bad in @[@"https://127.0.0.1:8765",@"http://127.0.0.1.evil:8765",@"file:///tmp/test",@"http://user@127.0.0.1:8765"])
            if([self localURL:[NSURL URLWithString:bad]]){[self fail:@"Origin validation"];return;}
        NSDictionary *csv=self.savedFiles[0],*ics=self.savedFiles[1];
        NSString *text=[[NSString alloc] initWithData:[[NSData alloc] initWithBase64EncodedString:csv[@"base64"] options:0] encoding:NSUTF8StringEncoding];
        if(![csv[@"filename"] isEqual:@"eve-native-test.csv"]||![text containsString:@"Ferrofluid"]||![ics[@"filename"] isEqual:@"eve-moons.ics"]){[self fail:@"Export contents"];return;}
        if(self.testNotifications.count!=3){[self fail:[NSString stringWithFormat:@"Expected two alert groups and a test, got %lu",(unsigned long)self.testNotifications.count]];return;}
        [self showNotificationTarget:@{ @"scope":@"99",@"category":@"jobs" }];
        [web takeSnapshotWithConfiguration:nil completionHandler:^(NSImage *image,NSError *error){
            if(error){[self fail:error.description];return;}
            NSBitmapImageRep *bitmap=[[NSBitmapImageRep alloc] initWithData:image.TIFFRepresentation];
            [[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}] writeToFile:[TestOutput stringByAppendingString:@".png"] atomically:YES];
            self.passed=YES;[NSApp terminate:nil];
        }];
    }];
}
- (void)applicationWillTerminate:(NSNotification *)notification {
    NSDictionary *report=@{ @"native_webkit":@(self.passed),@"live_activity_progress":@(self.progressCaptured),@"notification_bridge_submissions":@(self.testNotifications.count),@"notification_deep_links":@(self.passed),@"settings_language_and_theme":@(self.passed),@"copy":@(self.copied!=nil),@"exports":@(self.savedFiles.count),@"oauth_return":@(self.passed),@"quit_service":@YES };
    [[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:NULL] writeToFile:TestOutput atomically:YES];
}
@end
int main(int argc,const char *argv[]){
    @autoreleasepool {
        if(argc!=3)return 2;TestOrigin=@(argv[1]);TestOutput=@(argv[2]);
        if(![TestOrigin hasPrefix:@"http://127.0.0.1:"]||[TestOrigin isEqual:@"http://127.0.0.1:8765"])return 2;
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW,45*NSEC_PER_SEC),dispatch_get_main_queue(),^{fprintf(stderr,"Native smoke timed out\n");exit(1);});
        NSApplication *app=NSApplication.sharedApplication;WindowSmoke *delegate=[WindowSmoke new];app.delegate=delegate;[app run];return delegate.passed?0:1;
    }
}
