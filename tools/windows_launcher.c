#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include <stdio.h>

static int fail(const wchar_t *message) {
    MessageBoxW(NULL,message,L"EVE M\u0171hely",MB_OK|MB_ICONERROR);
    return 1;
}

int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,LPWSTR arguments,int show) {
    wchar_t root[32768],python[32768],script[32768],command[32768];
    DWORD length=GetModuleFileNameW(NULL,root,32768);
    if (!length || length>=32768) return fail(L"Az alkalmaz\u00e1s el\u00e9r\u00e9si \u00fatja nem olvashat\u00f3.");
    wchar_t *slash=wcsrchr(root,L'\\');
    if (!slash) return fail(L"Az alkalmaz\u00e1s mapp\u00e1ja nem tal\u00e1lhat\u00f3.");
    *slash=L'\0';
    if (swprintf(python,32768,L"%ls\\runtime\\pythonw.exe",root)<0 ||
        swprintf(script,32768,L"%ls\\app\\windows_desktop.py",root)<0)
        return fail(L"T\u00fal hossz\u00fa el\u00e9r\u00e9si \u00fat.");
    if (GetFileAttributesW(python)==INVALID_FILE_ATTRIBUTES || GetFileAttributesW(script)==INVALID_FILE_ATTRIBUTES)
        return fail(L"Hi\u00e1nyos alkalmaz\u00e1smappa. El\u0151bb csomagold ki a teljes ZIP-et, majd az EVE_Muhely.exe f\u00e1jlt ind\u00edtsd.");
    if (swprintf(command,32768,L"\"%ls\" -I -X utf8 \"%ls\" %ls",python,script,arguments)<0)
        return fail(L"T\u00fal hossz\u00fa ind\u00edt\u00e1si parancs.");
    STARTUPINFOW startup={0};startup.cb=sizeof(startup);
    PROCESS_INFORMATION process={0};
    if (!CreateProcessW(python,command,NULL,NULL,FALSE,CREATE_NO_WINDOW,NULL,root,&startup,&process))
        return fail(L"A be\u00e9p\u00edtett futtat\u00f3k\u00f6rnyezet nem indult. Csomagold ki \u00fajra a teljes kiad\u00e1st egy helyi mapp\u00e1ba.");
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess,INFINITE);
    DWORD code=1;GetExitCodeProcess(process.hProcess,&code);CloseHandle(process.hProcess);
    if (code) return fail(L"Az EVE M\u0171hely nem indult el. R\u00e9szletek: %LOCALAPPDATA%\\EVE Muhely\\launcher.log \u00e9s server.log. Az Ellenorzes.cmd diagnosztik\u00e1t is futtathatod.");
    return 0;
}
