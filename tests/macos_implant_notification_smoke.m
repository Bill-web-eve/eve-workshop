#define EVE_WINDOW_NO_MAIN
#import "../tools/macos_launcher.m"
@interface FakeNotificationSettings : NSObject
@property UNAuthorizationStatus authorizationStatus;
@end
@implementation FakeNotificationSettings
@end
@interface FakeNotificationCenter : NSObject
@property UNNotificationRequest *request;
@end
@implementation FakeNotificationCenter
- (void)getNotificationSettingsWithCompletionHandler:(void (^)(UNNotificationSettings *))block {
    FakeNotificationSettings *settings=[FakeNotificationSettings new];settings.authorizationStatus=UNAuthorizationStatusAuthorized;block((UNNotificationSettings *)settings);
}
- (void)addNotificationRequest:(UNNotificationRequest *)request withCompletionHandler:(void (^)(NSError *))block {self.request=request;block(nil);}
@end
static void require(BOOL ok,NSString *why){if(!ok){fprintf(stderr,"Implant notification smoke failed: %s\n",why.UTF8String);exit(1);}}
int main(){@autoreleasepool{
    [NSApplication sharedApplication];EveWindow *window=[EveWindow new];FakeNotificationCenter *center=[FakeNotificationCenter new];window.notificationCenter=(UNUserNotificationCenter *)center;
    __block BOOL replied=NO;__block NSString *failure=nil;
    [window notificationAction:@{@"action":@"notify",@"id":@"eve.implant-test",@"title":@"EVE Workshop",@"body":@"Pilot undocked · 1 100 000 000 ISK",@"scope":@"personal",@"category":@"implants",@"sound":@YES} reply:^(id result,NSString *error){replied=YES;failure=error;}];
    NSDate *limit=[NSDate dateWithTimeIntervalSinceNow:2];while(!replied&&limit.timeIntervalSinceNow>0)[NSRunLoop.mainRunLoop runMode:NSDefaultRunLoopMode beforeDate:limit];
    require(replied&&!failure,@"implant category rejected");require([center.request.content.userInfo[@"category"] isEqual:@"implants"],@"wrong notification target");require(center.request.content.sound!=nil,@"no notification sound");
    puts("Native implant notification: validated category, personal target and sound passed without sending an OS alert.");
}return 0;}
