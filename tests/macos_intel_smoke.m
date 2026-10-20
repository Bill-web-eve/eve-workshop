// Native WebKit integration against a synthetic, temporary local intel profile.
#define EVE_WINDOW_NO_MAIN
#import "../tools/macos_launcher.m"
static NSString *IntelOrigin,*IntelOutput;
@interface IntelSmoke : EveWindow
@property NSMutableArray *alerts;
@end
@implementation IntelSmoke
- (void)fail:(NSString *)why {fprintf(stderr,"Intel native test failed: %s\n",why.UTF8String);exit(1);}
- (void)startBackend:(void (^)(BOOL))done {self.origin=[NSURL URLWithString:IntelOrigin];self.alerts=[NSMutableArray new];done(YES);}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message replyHandler:(void (^)(id,NSString *))reply {
    if([self localURL:message.frameInfo.request.URL]&&message.frameInfo.mainFrame){
        NSString *action=message.body[@"action"];
        if([action isEqual:@"requestNotifications"]){[self fail:@"Unexpected permission request"];return;}
        if([action isEqual:@"notificationStatus"]){reply(@{ @"status":@"authorized" },nil);return;}
        if([action isEqual:@"notify"]){[self.alerts addObject:message.body];reply(@{ @"queued":@YES },nil);return;}
        if([action isEqual:@"chooseIntelFolder"]){reply(@{ @"path":@"/test/Chatlogs" },nil);return;}
    }
    [super userContentController:controller didReceiveScriptMessage:message replyHandler:reply];
}
- (void)webView:(WKWebView *)web didFinishNavigation:(WKNavigation *)navigation {
    [super webView:web didFinishNavigation:navigation];
    NSString *script=@"const wait=ms=>new Promise(r=>setTimeout(r,ms));for(let i=0;i<100&&(typeof state==='undefined'||!state);i++)await wait(40);if(!state)throw Error('No state');"
    "EveI18n.setLanguage('en');EveTheme.setTheme('dark');navigate('intel');await refreshIntel();await wait(80);"
    "if($('#page-title').textContent!=='Intel map'||!$('.plan-selector').hidden)throw Error('Intel view');"
    "if(!document.querySelector('.intel-node.contact')||!$('#view-content').textContent.includes('Synthetic Visitor'))throw Error('Map report');"
    "if(document.querySelector('#view-content script'))throw Error('Unsafe log text');"
    "$('#intel-zoom-in').click();if(intelZoom!==1.25)throw Error('Zoom');$('#intel-fit').click();"
    "const node=document.querySelector('.intel-node.contact');node.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));if(!intelSelected)throw Error('Map selection');"
    "openSettingsTab('intel');await wait(80);if(!$('#intel-settings'))throw Error('Intel settings');"
    "$('#intel-folder-pick').click();await wait(60);if($('#intel-settings').elements.folder.value!=='/test/Chatlogs')throw Error('Directory picker bridge');"
    "dirty={};navigate('intel');await refreshIntel();await api('/api/notifications/preferences',{os_enabled:true,auto_refresh:false});await refreshNotifications(false);await pollIntelAlerts();"
    "openNotificationCenter('personal','intel');if(view!=='intel')throw Error('Notification target');await refreshIntel();await wait(80);return {nodes:intelData.nodes.length,reports:intelData.reports.length,alerts:intelData.alerts.length,language:EveI18n.language};";
    [web callAsyncJavaScript:script arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld completionHandler:^(id result,NSError *error){
        if(error){[self fail:error.description];return;}
        if(self.alerts.count!=1||![self.alerts[0][@"category"] isEqual:@"intel"]||![self.alerts[0][@"body"] containsString:@"Test Pilot"]){[self fail:@"Intel notification content/deduplication"];return;}
        [web takeSnapshotWithConfiguration:nil completionHandler:^(NSImage *image,NSError *error){
            if(error){[self fail:error.description];return;}
            NSBitmapImageRep *bitmap=[[NSBitmapImageRep alloc] initWithData:image.TIFFRepresentation];
            [[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}] writeToFile:[IntelOutput stringByAppendingString:@".png"] atomically:YES];
            [[NSJSONSerialization dataWithJSONObject:result options:0 error:nil] writeToFile:IntelOutput atomically:YES];
            puts("Native intel map, directory bridge and notification integration passed.");exit(0);
        }];
    }];
}
@end
int main(int argc,const char *argv[]){@autoreleasepool{
    if(argc!=3)return 2;IntelOrigin=@(argv[1]);IntelOutput=@(argv[2]);
    if(![IntelOrigin hasPrefix:@"http://127.0.0.1:"]||[IntelOrigin isEqual:@"http://127.0.0.1:8765"])return 2;
    NSApplication *app=NSApplication.sharedApplication;[app setActivationPolicy:NSApplicationActivationPolicyRegular];IntelSmoke *delegate=[IntelSmoke new];app.delegate=delegate;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,45*NSEC_PER_SEC),dispatch_get_main_queue(),^{[delegate fail:@"Timed out"];});[app run];
}return 0;}
