// Native, three-window integration test with synthetic local logs. Never grants OS permission.
#define EVE_WINDOW_NO_MAIN
#import "../tools/macos_launcher.m"
static NSString *PreviewOrigin,*PreviewOutput;
@interface IntelWindowsSmoke : EveWindow
@property NSMutableArray *openedURLs;
@property NSMutableDictionary *results;
@end
@implementation IntelWindowsSmoke
- (void)fail:(NSString *)why {fprintf(stderr,"Intel windows test failed: %s\n",why.UTF8String);exit(1);}
- (void)startBackend:(void (^)(BOOL))done {self.origin=[NSURL URLWithString:PreviewOrigin];self.openedURLs=[NSMutableArray new];self.results=[NSMutableDictionary new];done(YES);}
- (void)openExternalURL:(NSURL *)url {[self.openedURLs addObject:url.absoluteString];}
- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message replyHandler:(void (^)(id,NSString *))reply {
    if([message.body[@"action"] isEqual:@"requestNotifications"]||[message.body[@"action"] isEqual:@"notify"]){[self fail:@"Unexpected permission or OS notification"];return;}
    [super userContentController:controller didReceiveScriptMessage:message replyHandler:reply];
}
- (void)snapshot:(WKWebView *)web suffix:(NSString *)suffix done:(void (^)(void))done {
    [web takeSnapshotWithConfiguration:nil completionHandler:^(NSImage *img,NSError *error){if(error){[self fail:error.description];return;}NSBitmapImageRep *bitmap=[[NSBitmapImageRep alloc] initWithData:img.TIFFRepresentation];[[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}] writeToFile:[PreviewOutput stringByAppendingString:suffix] atomically:YES];done();}];
}
- (void)checkChat {
    WKWebView *chat=self.intelViews[@"chat"];if(![self localURL:chat.URL]||chat.loading){dispatch_after(dispatch_time(DISPATCH_TIME_NOW,80*NSEC_PER_MSEC),dispatch_get_main_queue(),^{[self checkChat];});return;}
    NSString *script=@"const wait=ms=>new Promise(r=>setTimeout(r,ms));for(let i=0;i<100&&(typeof state==='undefined'||!state);i++)await wait(40);await refreshIntel();if(intelWindowMode!=='chat'||$('#intel-chat-feed').children.length<2)throw Error('Combined chat');if(!$('#intel-chat-feed').textContent.includes('Second Intel')||!$('#intel-chat-feed').textContent.includes('Test Intel'))throw Error('Missing channel');if(getComputedStyle($('.sidebar')).display!=='none')throw Error('Detached shell');const initialCount=$('#intel-chat-feed').children.length,first=$('#intel-chat-feed').firstElementChild;await api('/api/test/intel-append',{});for(let i=0;i<80&&$('#intel-chat-feed').children.length<=initialCount;i++){await wait(80);await refreshIntel(true);}if($('#intel-chat-feed').children.length!==initialCount+1||first!==$('#intel-chat-feed').firstElementChild)throw Error('Live stable chat');return {messages:$('#intel-chat-feed').children.length,read_only:!$('#intel-chat-feed').querySelector('textarea,input')};";
    [chat callAsyncJavaScript:script arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld completionHandler:^(id result,NSError *error){
        if(error){[self fail:[@"Chat: " stringByAppendingString:error.description]];return;}self.results[@"chat"]=result;
        [self snapshot:chat suffix:@".chat.png" done:^{
            NSWindow *map=self.intelWindows[@"map"];NSString *closedTitle=map.title;[map performClose:nil];if([NSApp.windowsMenu.itemArray filteredArrayUsingPredicate:[NSPredicate predicateWithFormat:@"title == %@",closedTitle]].count){[self fail:@"Closed window still in native menu"];return;}if(self.intelViews.count!=1||self.quitting){[self fail:@"Closing map stopped the application"];return;}
            [self.web callAsyncJavaScript:@"if(!(await (await fetch('/health')).json()).app)throw Error('Service stopped');EveTheme.setTheme('light');await new Promise(r=>setTimeout(r,150));if(intelWindowMode)throw Error('Main window replaced');return true;" arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld completionHandler:^(id result,NSError *error){
                if(error){[self fail:error.description];return;}
                if(![self.intelWindows[@"chat"].appearance.name isEqual:NSAppearanceNameAqua]){[self fail:@"Theme did not propagate"];return;}
                if(![self.openedURLs containsObject:@"https://zkillboard.com/character/359618261/"]){[self fail:@"Wrong zKillboard link"];return;}
                self.results[@"native_windows"]=@YES;self.results[@"closing_child_keeps_service"]=@YES;self.results[@"opened_urls"]=self.openedURLs;
                [[NSJSONSerialization dataWithJSONObject:self.results options:NSJSONWritingPrettyPrinted error:nil] writeToFile:PreviewOutput atomically:YES];puts("Native region map, ship icons, zKillboard links and live combined chat windows passed.");exit(0);
            }];
        }];
    }];
}
- (void)checkMap {
    WKWebView *map=self.intelViews[@"map"];if(![self localURL:map.URL]||map.loading){dispatch_after(dispatch_time(DISPATCH_TIME_NOW,80*NSEC_PER_MSEC),dispatch_get_main_queue(),^{[self checkMap];});return;}
    NSString *script=@"const wait=ms=>new Promise(r=>setTimeout(r,ms));for(let i=0;i<100&&(typeof state==='undefined'||!state);i++)await wait(40);await refreshIntel();if(intelData.nodes.length!==115)throw Error('Not the full Fountain region');if($('#intel-map').getBoundingClientRect().bottom>innerHeight+1)throw Error('Map exceeds the window');if(!document.querySelector('.intel-range-halo')||!document.querySelector('.intel-activity-card'))throw Error('Missing range/card');const link=document.querySelector('a[href=\"https://zkillboard.com/character/359618261/\"]');if(!link)throw Error('Missing pilot link');link.click();const img=document.querySelector('.intel-activity-card img');for(let i=0;i<60&&!img.naturalWidth;i++)await wait(80);if(!img.naturalWidth)throw Error('Ship icon did not load');if(getComputedStyle($('.sidebar')).display!=='none')throw Error('Detached map shell');return {systems:intelData.nodes.length,range:document.querySelectorAll('.intel-range-halo').length,ship_icon_loaded:img.naturalWidth>0};";
    [map callAsyncJavaScript:script arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld completionHandler:^(id result,NSError *error){if(error){[self fail:[@"Map: " stringByAppendingString:error.description]];return;}self.results[@"map"]=result;[self snapshot:map suffix:@".map.png" done:^{[self checkChat];}];}];
}
- (void)webView:(WKWebView *)web didFinishNavigation:(WKNavigation *)navigation {
    [super webView:web didFinishNavigation:navigation];if(web!=self.web)return;
    NSString *script=@"const wait=ms=>new Promise(r=>setTimeout(r,ms));for(let i=0;i<100&&(typeof state==='undefined'||!state);i++)await wait(40);EveI18n.setLanguage('en');EveTheme.setTheme('dark');navigate('intel');await refreshIntel();await EveDesktop.openIntelWindow('map',{character_id:1});await EveDesktop.openIntelWindow('chat',{character_id:1});await EveDesktop.openIntelWindow('map',{character_id:1});let rejected=false;try{await EveDesktop.openIntelWindow('bad')}catch{rejected=true}if(!rejected)throw Error('Window kind not validated');return true;";
    [web callAsyncJavaScript:script arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld completionHandler:^(id result,NSError *error){if(error){[self fail:[@"Main: " stringByAppendingString:error.description]];return;}if(self.intelViews.count!=2){[self fail:@"Did not create or reuse separate windows"];return;}
        for(NSWindow *window in @[self.window,self.intelWindows[@"map"],self.intelWindows[@"chat"]]){if(window.excludedFromWindowsMenu||window.tabbingMode!=NSWindowTabbingModeDisallowed||![NSApp.windowsMenu.itemArray filteredArrayUsingPredicate:[NSPredicate predicateWithFormat:@"title == %@",window.title]].count){[self fail:@"Missing native window menu entry"];return;}}
        self.results[@"native_window_menu"]=@YES;[self checkMap];}];
}
@end
int main(int argc,const char *argv[]){@autoreleasepool{
    if(argc!=3)return 2;PreviewOrigin=@(argv[1]);PreviewOutput=@(argv[2]);if(![PreviewOrigin hasPrefix:@"http://127.0.0.1:"]||[PreviewOrigin isEqual:@"http://127.0.0.1:8765"])return 2;
    NSApplication *app=NSApplication.sharedApplication;IntelWindowsSmoke *delegate=[IntelWindowsSmoke new];app.delegate=delegate;dispatch_after(dispatch_time(DISPATCH_TIME_NOW,50*NSEC_PER_SEC),dispatch_get_main_queue(),^{[delegate fail:@"Timed out"];});[app run];
}return 0;}
