"""Windows WebView2 shell. Native APIs are limited to our exact loopback origin."""
from __future__ import annotations
import argparse
import base64
import binascii
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser

LOG=logging.getLogger(__name__)
MAX_FILE=32*1024*1024
CHILD_ACTIONS={'clipboard','preferences','external','activate','openIntelWindow','print'}


def local_url(url,origin):
    try:
        value=urllib.parse.urlsplit(url);expected=urllib.parse.urlsplit(origin)
        return value.scheme=='http' and value.hostname=='127.0.0.1' and value.port==expected.port and not value.username and not value.password
    except (ValueError,TypeError):return False


def external_url(value):
    if not isinstance(value,str) or len(value)>16384 or any(ord(c)<32 for c in value):return False
    try:
        url=urllib.parse.urlsplit(value)
        return url.scheme in {'http','https','webcal'} and bool(url.hostname) and not url.username and not url.password
    except ValueError:return False


def file_payload(body):
    name=body.get('filename');encoded=body.get('base64')
    if not isinstance(name,str) or not name or len(name)>200 or name in {'.','..'} or any(c in name for c in '/\\:') or any(ord(c)<32 for c in name):
        raise ValueError('Hibás fájlnév.')
    if Path(name).suffix.lower() not in {'.csv','.ics','.md','.txt','.json','.svg','.png','.pdf'}:
        raise ValueError('Ez a fájltípus nem menthető.')
    if not isinstance(encoded,str) or len(encoded)>4*((MAX_FILE+2)//3):raise ValueError('A fájl túl nagy a mentéshez.')
    try:data=base64.b64decode(encoded,validate=True)
    except (ValueError,binascii.Error):raise ValueError('Hibás fájltartalom.') from None
    if len(data)>MAX_FILE:raise ValueError('A fájl túl nagy a mentéshez.')
    return name,data


def intel_url(origin,kind,options):
    if kind not in {'map','chat'}:raise ValueError('Hibás intelablak.')
    query={'intel_window':kind}
    for key in ['character_id','region','center']:
        value=options.get(key)
        if type(value) is int and 0<value<=2**31-1:query[key]=value
    if options.get('history') is True:query['history']=1
    return origin+'/?'+urllib.parse.urlencode(query)


class WindowHost:
    def __init__(self,webview,origin,folder):
        self.webview=webview;self.origin=origin;self.folder=Path(folder)
        self.main=None;self.children={};self.lock=threading.RLock()
        self.quitting=False;self.stopped=False;self.ready=False
        self.theme='dark';self.language='hu';self.tray=None;self.notification_granted=False
        self.self_test_callback=None;self.overlay=None
        try:
            prefs=json.loads((self.folder/'windows-shell.json').read_text())
            self.language='en' if prefs.get('language')=='en' else 'hu'
            self.notification_granted=prefs.get('notifications') is True
        except (OSError,ValueError):pass

    def _save_preferences(self):
        self.folder.mkdir(parents=True,exist_ok=True)
        path=self.folder/'windows-shell.json';temp=path.with_suffix('.tmp')
        with self.lock:
            temp.write_text(json.dumps({'language':self.language,'notifications':self.notification_granted}))
            os.replace(temp,path)

    def _ui(self,window,fn):
        # All WinForms and WebView2 COM access stays on the GUI's STA thread.
        from System import Action
        form=window.native
        if form.IsDisposed:raise RuntimeError('Az alkalmazásablak már bezárult.')
        result=[];failure=[]
        def call():
            try:result.append(fn())
            except Exception as e:failure.append(e)
        if form.InvokeRequired:form.Invoke(Action(call))
        else:call()
        if failure:raise failure[0]
        return result[0] if result else None

    def _script(self,window,script):
        # ExecuteScriptAsync runs the script directly: CSP does not need unsafe-eval.
        self._ui(window,lambda:window.native.webview.CoreWebView2.ExecuteScriptAsync(script))

    def _activate(self):
        self.main.restore();self.main.show()
        self._ui(self.main,lambda:self.main.native.Activate())
        return True

    def _preferences(self,body,window):
        self.language='en' if body.get('language')=='en' else 'hu'
        self.theme='light' if body.get('theme')=='light' else 'dark'
        self._save_preferences()
        self.main.set_title('EVE Workshop' if self.language=='en' else 'EVE Műhely')
        def frame():
            import ctypes
            from System.Drawing import Color
            form=window.native;form.BackColor=Color.FromArgb(16,29,39) if self.theme=='dark' else Color.White
            try:
                dark=ctypes.c_int(self.theme=='dark')
                ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(form.Handle.ToInt64()),20,ctypes.byref(dark),ctypes.sizeof(dark))
            except OSError:pass
        self._ui(window,frame)
        if self.overlay is not None:self._ui(self.main,lambda:self.overlay.preferences(self.theme,self.language))
        return True

    def _overlay_action(self,action,body):
        def apply():
            if self.overlay is None:
                from .windows_overlay import NativeOverlay
                self.overlay=NativeOverlay(self.folder,self.theme,self.language)
            if action=='intelOverlayStatus':return self.overlay.settings()
            if action=='configureIntelOverlay':return self.overlay.configure(body.get('options'))
            return self.overlay.sync(body.get('data'))
        return self._ui(self.main,apply)

    def _notification(self,body):
        title=body.get('title');message=body.get('body')
        if not self.notification_granted:raise ValueError('Előbb engedélyezd a rendszerértesítéseket a fenti gombbal.')
        if not isinstance(title,str) or not isinstance(message,str) or len(title)>256 or len(message)>2000:raise ValueError('Hibás értesítés.')
        def show():
            from System.Windows.Forms import NotifyIcon,ToolTipIcon
            from System.Drawing import SystemIcons
            if self.tray is None:
                self.tray=NotifyIcon();self.tray.Icon=self.main.native.Icon or SystemIcons.Application
                self.tray.Text='EVE Workshop';self.tray.Visible=True
                def clicked(*_):
                    self._activate()
                    target=json.dumps({'scope':self._notification_target[0],'category':self._notification_target[1]})
                    self._script(self.main,'(()=>{const t='+target+';if(typeof openNotificationCenter==="function")openNotificationCenter(t.scope,t.category);})()')
                self.tray.BalloonTipClicked+=clicked
            self._notification_target=(str(body.get('scope','personal'))[:30],str(body.get('category','all'))[:30])
            self.tray.ShowBalloonTip(10000,title[:63],message[:1000],ToolTipIcon.Info)
            # Windows controls alert audio; an explicitly requested sound is best-effort.
            if body.get('sound') is True:
                import winsound
                winsound.PlaySound('SystemNotification',winsound.SND_ALIAS|winsound.SND_ASYNC)
        self._ui(self.main,show)
        return {'queued':True}

    def dispatch(self,window,source,body):
        if not local_url(source,self.origin) or not isinstance(body,dict):raise ValueError('Local application window required')
        action=body.get('action')
        if window is not self.main and action not in CHILD_ACTIONS:raise ValueError('Main window action required')
        if action=='clipboard':
            text=body.get('text')
            if not isinstance(text,str) or len(text)>4*1024*1024:raise ValueError('Hibás vágólaptartalom.')
            def copy():
                from System.Windows.Forms import Clipboard
                if text:Clipboard.SetText(text)
                else:Clipboard.Clear()
            self._ui(window,copy);return True
        if action=='save':
            name,data=file_payload(body)
            selected=window.create_file_dialog(self.webview.FileDialog.SAVE,save_filename=name)
            if not selected:return {'saved':False}
            path=selected if isinstance(selected,str) else selected[0]
            Path(path).write_bytes(data);return {'saved':True}
        if action=='chooseIntelFolder':
            selected=window.create_file_dialog(self.webview.FileDialog.FOLDER)
            return {'path':(selected if isinstance(selected,str) else selected[0]) if selected else ''}
        if action=='external':
            url=body.get('url')
            if not external_url(url):raise ValueError('Hibás külső hivatkozás.')
            webbrowser.open(url);return True
        if action=='preferences':return self._preferences(body,window)
        if action=='activate':return self._activate()
        if action=='print':self._ui(window,lambda:window.native.webview.CoreWebView2.ShowPrintUI());return True
        if action=='openIntelWindow':
            kind=body.get('kind');options=body.get('options') or {}
            if not isinstance(options,dict):raise ValueError('Hibás intelablak.')
            url=intel_url(self.origin,kind,options)
            with self.lock:
                if kind in self.children:
                    child=self.children[kind];child.load_url(url);child.restore();child.show()
                else:
                    title=('System map' if kind=='map' else 'Intel chat') if self.language=='en' else ('Rendszertérkép' if kind=='map' else 'Intelchat')
                    child=self.create_window('EVE Workshop · '+title,url,width=1200 if kind=='map' else 750,height=800)
                    self.children[kind]=child
                    child.events.closed+=lambda:self.children.pop(kind,None)
            return {'opened':True}
        if action=='notificationStatus':return {'status':'authorized' if self.notification_granted else 'notDetermined'}
        if action=='requestNotifications':
            self.notification_granted=True;self._save_preferences();return {'status':'authorized'}
        if action=='notify':return self._notification(body)
        if action in {'intelOverlayStatus','configureIntelOverlay','syncIntelOverlay'}:return self._overlay_action(action,body)
        if action=='quitCheck':
            if not self.quitting:raise ValueError('No close request is pending')
            message=('Unsaved changes or EVE requests are still in progress. Close EVE Workshop?' if self.language=='en' else 'Még nem mentett módosítás vagy folyamatban lévő lekérés van. Bezárod az EVE Műhelyt?')
            if (body.get('dirty') or body.get('running')) and not window.create_confirmation_dialog('EVE Workshop',message):
                self.quitting=False;return {'cancelled':True}
            self._script(self.main,'void EveDesktop.shutdown()');return True
        if action=='quitFailed':self.quitting=False;return True
        if action=='stopped':
            from desktop import stop_backend
            if not stop_backend(self.origin):
                self.quitting=False
                raise ValueError('Could not stop the local service. Please try again.' if self.language=='en' else 'A helyi szolgáltatás nem állt le. Próbáld újra.')
            self.stopped=True
            if self.overlay is not None:self._ui(self.main,self.overlay.dispose)
            for child in list(self.children.values()):child.destroy()
            if self.tray is not None:self._ui(self.main,self.tray.Dispose)
            self.main.destroy();return True
        if action=='selfTestResult' and self.self_test_callback is not None:
            self.self_test_callback(body);return True
        raise ValueError('Unknown desktop action')

    def _message(self,window,args):
        source=str(args.Source)
        if not local_url(source,self.origin):return
        try:
            raw=str(args.WebMessageAsJson)
            if len(raw)>4*((MAX_FILE+2)//3)+4096:return
            message=json.loads(raw)
            if not isinstance(message,dict) or message.get('eveDesktop')!=1 or type(message.get('id')) is not int:return
            ident=message['id']
            if not 0<ident<=2**53-1:return
        except (ValueError,TypeError):return
        def work():
            try:value=self.dispatch(window,source,message.get('payload'));reply={'value':value}
            except Exception as e:
                LOG.exception('Native window action failed')
                reply={'error':str(e) if isinstance(e,ValueError) else ('The desktop action failed. Please try again.' if self.language=='en' else 'A művelet nem sikerült. Próbáld újra.')}
            try:self._ui(window,lambda:window.native.webview.CoreWebView2.PostWebMessageAsJson(json.dumps({'eveDesktop':1,'id':ident,**reply})))
            except Exception:
                if not self.stopped:LOG.exception('Native window reply failed')
        threading.Thread(target=work,daemon=True).start()

    def _attach(self,window):
        form=window.native;control=form.webview
        def ready(sender,args):
            if not args.IsSuccess:return
            core=control.CoreWebView2
            # We use an origin-checked WebMessage bridge, never pywebview.js_api.
            control.WebMessageReceived-=form.browser.on_script_notify
            core.NewWindowRequested-=form.browser.on_new_window_request
            core.Settings.AreHostObjectsAllowed=False
            core.Settings.AreDevToolsEnabled=False
            def navigation(_sender,event):
                if not local_url(str(event.Uri),self.origin):event.Cancel=True
            def popup(_sender,event):
                event.Handled=True
                if external_url(str(event.Uri)):webbrowser.open(str(event.Uri))
            core.NavigationStarting+=navigation;core.FrameNavigationStarting+=navigation
            core.NewWindowRequested+=popup
            core.WebMessageReceived+=lambda _sender,event:self._message(window,event)
        control.CoreWebView2InitializationCompleted+=ready
        if control.CoreWebView2 is not None:
            class Initialized:IsSuccess=True
            ready(control,Initialized())

    def create_window(self,title,url,**kwargs):
        window=self.webview.create_window(title,url,min_size=(720,500),background_color='#101d27',**kwargs)
        window.events.before_show+=lambda:self._attach(window)
        return window

    def _closing(self):
        if self.stopped:return True
        if self.quitting:return False
        self.quitting=True
        def close():
            try:
                if self.ready:self._script(self.main,'void EveDesktop.prepareQuit()')
                else:self.dispatch(self.main,self.origin,{'action':'stopped'})
            except Exception:
                LOG.exception('Window close could not finish');self.quitting=False
        threading.Thread(target=close,daemon=True).start()
        return False

    def create_main(self):
        self.main=self.create_window('EVE Workshop',self.origin+'/',width=1320,height=860)
        self.main.events.closing+=self._closing
        def loaded():self.ready=True
        self.main.events.loaded+=loaded
        return self.main


def ensure_backend(port,folder):
    from desktop import health,process_command,background_options
    from . import __version__
    origin='http://127.0.0.1:'+str(port);current=health(origin)
    if current:
        if current.get('version')!=__version__:raise RuntimeError('Frissítés előtt állítsd le a korábbi EVE Műhely alkalmazást. / Stop the previous EVE Workshop before updating.')
        return origin
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    with (folder/'server.log').open('ab') as log:
        process=subprocess.Popen(process_command(port,folder),stdin=subprocess.DEVNULL,stdout=log,stderr=log,**background_options())
    for _ in range(150):
        if health(origin):return origin
        if process.poll() is not None:raise RuntimeError('Az EVE Műhely nem indult el. / EVE Workshop could not start.')
        time.sleep(.1)
    raise RuntimeError('Az alkalmazás indítása túl sokáig tart. / Application startup timed out.')



def webview_runtime_present():
    import winreg
    # Microsoft's Evergreen WebView2 runtime registration (both install scopes/views).
    key=r'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    for hive in [winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE]:
        for view in [winreg.KEY_WOW64_32KEY,winreg.KEY_WOW64_64KEY]:
            try:
                with winreg.OpenKey(hive,key,0,winreg.KEY_READ|view) as handle:
                    value=winreg.QueryValueEx(handle,'pv')[0]
                    if isinstance(value,str) and value and value!='0.0.0.0':return True
            except OSError:pass
    return False


def _main():
    parser=argparse.ArgumentParser(description='EVE Workshop – Windows desktop')
    parser.add_argument('--browser',action='store_true',help='Open the optional browser fallback')
    parser.add_argument('--port',type=int,default=8765);parser.add_argument('--data-dir',type=Path)
    args=parser.parse_args()
    if args.browser:
        from desktop import main as browser
        sys.argv=[sys.argv[0],*(['--data-dir',str(args.data_dir)] if args.data_dir else []),'--port',str(args.port)]
        browser();return 0
    if sys.platform!='win32':raise RuntimeError('Windows 11 x64 szükséges. / Windows 11 x64 is required.')
    if not 1024<=args.port<=65535:raise ValueError('Invalid local port')
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('EVEWorkshop.Desktop')
    import certifi
    os.environ.setdefault('SSL_CERT_FILE',certifi.where())
    from .store import default_data_dir
    folder=(args.data_dir or default_data_dir()).expanduser()
    # Fail visibly instead of silently opening an obsolete renderer/browser.
    import webview
    if not webview_runtime_present():raise RuntimeError('Microsoft Edge WebView2 Runtime szükséges. / Microsoft Edge WebView2 Runtime is required: https://developer.microsoft.com/microsoft-edge/webview2/')
    origin=ensure_backend(args.port,folder)
    host=WindowHost(webview,origin,folder);host.create_main()
    webview.settings['ALLOW_DOWNLOADS']=False
    webview.settings['ALLOW_FILE_URLS']=False
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']=False
    webview.start(gui='edgechromium',debug=False,private_mode=False,storage_path=str(folder/'webview2'),user_agent='EVEWorkshopDesktop/Windows',icon=str(Path(__file__).resolve().parent.parent/'data/app.ico'))
    return 0


def main():
    if sys.platform!='win32' or '--browser' in sys.argv:return _main()
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateMutexW(None,False,'Local\\EVEWorkshopDesktopWindow')
    if not handle:raise OSError(ctypes.get_last_error(),'Could not create application lock')
    try:
        if ctypes.get_last_error()==183:
            user=ctypes.WinDLL('user32',use_last_error=True)
            user.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR];user.FindWindowW.restype=wintypes.HWND
            user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int];user.SetForegroundWindow.argtypes=[wintypes.HWND]
            for title in ['EVE Workshop','EVE Műhely']:
                window=user.FindWindowW(None,title)
                if window:user.ShowWindow(window,9);user.SetForegroundWindow(window);break
            return 0
        return _main()
    finally:kernel.CloseHandle(handle)
