#import <Cocoa/Cocoa.h>
#include <sys/stat.h>

// Finder launches this native executable. All runtime sources are inside the
// installed application, rather than loaded from a protected cloud folder.
int main(int argc, const char *argv[]) {
    @autoreleasepool {
        umask(0077);
        NSFileManager *files = [NSFileManager defaultManager];
        NSString *folder = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/EVE Muhely"];
        [files createDirectoryAtPath:folder withIntermediateDirectories:YES attributes:nil error:nil];
        NSString *log = [folder stringByAppendingPathComponent:@"launcher.log"];
        [files createFileAtPath:log contents:nil attributes:nil];
        NSFileHandle *output = [NSFileHandle fileHandleForWritingAtPath:log];
        NSTask *task = [[NSTask alloc] init];
        task.executableURL = [NSURL fileURLWithPath:@"/bin/bash"];
        NSString *script = [[[NSBundle mainBundle] resourcePath] stringByAppendingPathComponent:@"eve_muhely/Inditas.command"];
        task.arguments = @[script, @"--no-browser"];
        task.standardOutput = output;
        task.standardError = output;
        task.standardInput = [NSFileHandle fileHandleWithNullDevice];
        NSError *error = nil;
        BOOL launched = [task launchAndReturnError:&error];
        if (launched) [task waitUntilExit];
        [output closeFile];
        if (!launched || task.terminationStatus != 0) {
            [NSApplication sharedApplication];
            [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
            [NSApp activateIgnoringOtherApps:YES];
            NSAlert *alert = [[NSAlert alloc] init];
            alert.messageText = @"Az EVE Műhely nem indult el";
            alert.informativeText = [NSString stringWithFormat:@"Az indítás részleteit itt találod:\n%@", log];
            [alert addButtonWithTitle:@"Napló megnyitása"];
            [alert addButtonWithTitle:@"Bezárás"];
            if ([alert runModal] == NSAlertFirstButtonReturn)
                [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:log]];
            return 1;
        }
        BOOL noBrowser = NO;
        for (int i=1; i<argc; i++) if (strcmp(argv[i], "--no-browser") == 0) noBrowser = YES;
        if (!noBrowser) [[NSWorkspace sharedWorkspace] openURL:[NSURL URLWithString:@"http://127.0.0.1:8765"]];
        return 0;
    }
}
