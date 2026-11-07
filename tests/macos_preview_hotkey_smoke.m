#import <Cocoa/Cocoa.h>
#import "../tools/macos_eve_preview.m"
static void require(BOOL ok,NSString *message){if(!ok){fprintf(stderr,"Hotkey test failed: %s\n",message.UTF8String);exit(1);}}
@interface PreviewHotkeyTest : EvePreview
@property NSInteger direction,count;
@end
@implementation PreviewHotkeyTest
- (BOOL)captureAllowed{return NO;}
- (BOOL)accessibilityAllowed{return NO;}
- (void)refresh:(void(^)(void))done {if(done)done();}
- (BOOL)cycle:(NSInteger)direction {self.direction=direction;self.count++;return YES;}
@end
static CGEventRef key(CGKeyCode code,CGEventFlags flags,BOOL down,BOOL repeat){CGEventRef event=CGEventCreateKeyboardEvent(NULL,code,down);CGEventSetFlags(event,flags);CGEventSetIntegerValueField(event,kCGKeyboardEventAutorepeat,repeat);return event;}
static void pump(void){NSDate *limit=[NSDate dateWithTimeIntervalSinceNow:.03];while(limit.timeIntervalSinceNow>0)[NSRunLoop.mainRunLoop runMode:NSDefaultRunLoopMode beforeDate:limit];}
int main(){@autoreleasepool{
 [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
 NSString *suite=[@"EVEPreviewHotkeyTest-" stringByAppendingString:NSUUID.UUID.UUIDString];NSUserDefaults *defaults=[[NSUserDefaults alloc] initWithSuiteName:suite];
 PreviewHotkeyTest *p=[[PreviewHotkeyTest alloc] initWithDefaults:defaults];p.enabled=YES;
 EvePreviewKeys *keys=[EvePreviewKeys new];keys.owner=p;keys.nextKey=@{@"code":@116,@"modifiers":@(controlKey|optionKey)};keys.previousKey=@{@"code":@121,@"modifiers":@(controlKey|optionKey)};keys.hasTargets=YES;p.keys=keys;
 CGEventFlags flags=kCGEventFlagMaskControl|kCGEventFlagMaskAlternate;
 CGEventRef unrelated=key(0,flags,YES,NO);require([keys handleType:kCGEventKeyDown event:unrelated]==unrelated,@"unrelated typing swallowed");CFRelease(unrelated);
 CGEventRef wrong=key(116,flags|kCGEventFlagMaskCommand,YES,NO);require([keys handleType:kCGEventKeyDown event:wrong]==wrong,@"extra modifier matched");CFRelease(wrong);
 CGEventRef next=key(116,flags|kCGEventFlagMaskSecondaryFn|kCGEventFlagMaskAlphaShift,YES,NO);require([keys handleType:kCGEventKeyDown event:next]==NULL,@"configured next shortcut not intercepted");pump();require(p.count==1&&p.direction==1&&p.shortcutCount==1,@"next did not reach main-thread client switching");
 require([keys handleType:kCGEventKeyDown event:next]==NULL,@"held key leaked");CGEventSetIntegerValueField(next,kCGKeyboardEventAutorepeat,1);require([keys handleType:kCGEventKeyDown event:next]==NULL,@"repeat leaked");pump();require(p.count==1,@"held key switched multiple times");
 CGEventRef up=key(116,0,NO,NO);require([keys handleType:kCGEventKeyUp event:up]==NULL,@"key-up not swallowed after modifier release");CFRelease(up);CGEventSetIntegerValueField(next,kCGKeyboardEventAutorepeat,0);[keys handleType:kCGEventKeyDown event:next];pump();require(p.count==2,@"released shortcut could not be used again");CFRelease(next);
 CGEventRef previous=key(121,flags,YES,NO);require([keys handleType:kCGEventKeyDown event:previous]==NULL,@"previous not intercepted");pump();require(p.count==3&&p.direction==-1,@"previous direction");CFRelease(previous);
 keys.hasTargets=NO;CGEventRef empty=key(116,flags,YES,NO);require([keys handleType:kCGEventKeyDown event:empty]==empty,@"no-client shortcut swallowed");CFRelease(empty);
 keys.hasTargets=YES;CGEventRef queued=key(116,flags,YES,NO);[keys.pressed removeAllIndexes];[keys handleType:kCGEventKeyDown event:queued];[p releaseKeys];pump();require(p.count==3&&!p.keys,@"queued switch survived shutdown or replacement");require([keys handleType:kCGEventKeyDown event:queued]==queued,@"stopped listener handled a key");CFRelease(queued);
 [p receivedShortcut:1];require(p.count==4,@"enabled switch");p.enabled=NO;[p receivedShortcut:1];require(p.count==4,@"disabled switch");[p stop];
 [defaults removePersistentDomainForName:suite];puts("eve-preview shortcuts: exact matching, both directions, Fn/Caps Lock, key repeat, key-up, unrelated typing and shutdown passed.");
}return 0;}
