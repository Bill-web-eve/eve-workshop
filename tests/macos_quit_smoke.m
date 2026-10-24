#define EVE_WINDOW_NO_MAIN
#import "../tools/macos_launcher.m"
static NSString *TestOrigin,*TestOutput;
static BOOL Early;
@interface QuitSmoke : EveWindow
@property BOOL checked;
@end
@implementation QuitSmoke
- (void)startBackend:(void (^)(BOOL))completion {
    self.origin=[NSURL URLWithString:TestOrigin];
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,300*NSEC_PER_MSEC),dispatch_get_main_queue(),^{completion(YES);});
}
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    [super applicationDidFinishLaunching:notification];
    if(Early)dispatch_after(dispatch_time(DISPATCH_TIME_NOW,50*NSEC_PER_MSEC),dispatch_get_main_queue(),^{[self.window performClose:nil];});
}
- (void)webView:(WKWebView *)web didFinishNavigation:(WKNavigation *)navigation {
    [super webView:web didFinishNavigation:navigation];if(Early||web!=self.web||self.checked)return;self.checked=YES;
    [web callAsyncJavaScript:@"const wait=ms=>new Promise(r=>setTimeout(r,ms));for(let i=0;i<100&&(typeof state==='undefined'||!state);i++)await wait(50);await EveDesktop.openIntelWindow('map',{});await EveDesktop.openIntelWindow('chat',{});return true;" arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld completionHandler:^(id value,NSError *error){if(error){fprintf(stderr,"%s\n",error.description.UTF8String);exit(1);}[self.window performClose:nil];}];
}
- (void)applicationWillTerminate:(NSNotification *)notification {
    BOOL clean=self.stopped&&!self.notificationMonitor.valid&&!self.intelMonitor.valid&&!self.intelOverlay.timer.valid&&!self.intelWindows.count;
    NSDictionary *result=@{@"native_close":@(clean),@"early_close":@(Early)};
    [[NSJSONSerialization dataWithJSONObject:result options:0 error:NULL] writeToFile:TestOutput atomically:YES];
    if(!clean)exit(1);
}
@end
int main(int argc,const char *argv[]){@autoreleasepool{
    if(argc<3)return 2;TestOrigin=@(argv[1]);TestOutput=@(argv[2]);Early=argc>3;
    if([TestOrigin isEqual:@"http://127.0.0.1:8765"])return 2;
    NSApplication *app=NSApplication.sharedApplication;QuitSmoke *delegate=[QuitSmoke new];app.delegate=delegate;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,35*NSEC_PER_SEC),dispatch_get_main_queue(),^{fputs("Native quit timed out\n",stderr);exit(1);});[app run];return 0;
}}
