"""Run the real WebView2 window against a disposable profile, never user data."""
import argparse
import faulthandler
import json
import os
import socket
import subprocess
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch


def check_overlay(host,window,folder):
    """Real HWND, GDI painting, click-through flags, expiry and cleanup on Windows."""
    from muhely.windows_overlay import OverlayState
    def send(action,**body):return host.dispatch(window,host.origin,{'action':action,**body})
    info=send('intelOverlayStatus');assert info['available'] and info['screens']
    send('configureIntelOverlay',options={'screen_id':info['screen_id'],'x':40,'y':60,'width':330,'editing':True})
    overlay=host.overlay
    def native_check(editing):
        hwnd=overlay.form.Handle.ToInt64();style=overlay.user.GetWindowLongPtrW(hwnd,-20)
        assert overlay.user.IsWindowVisible(hwnd)
        assert style&0x8 and style&0x80000 and style&0x8000000 and style&0x80
        assert bool(style&0x20) is not editing
        assert not overlay.form.ShowInTaskbar
    host._ui(window,lambda:native_check(True))
    send('configureIntelOverlay',options={'editing':False})
    def display():
        from ctypes import wintypes
        from System.Drawing import Bitmap,Rectangle
        overlay.user.GetForegroundWindow.argtypes=[];overlay.user.GetForegroundWindow.restype=wintypes.HWND
        before=overlay.user.GetForegroundWindow()
        row={'key':'ci:1','system':'J5A-IX','pilots':'Smoke test pilot','ships':'Buzzard','character':'Smoke character','jumps':2,'when':time.time()}
        overlay.sync({'enabled':True,'seconds':2,'items':[row,{**row,'key':'ci:2','system':'C-N4OD'}]})
        native_check(False);assert overlay.user.GetForegroundWindow()==before,'Overlay stole keyboard focus'
        bitmap=Bitmap(overlay.form.ClientSize.Width,overlay.form.ClientSize.Height)
        try:
            overlay.form.DrawToBitmap(bitmap,Rectangle(0,0,bitmap.Width,bitmap.Height))
            assert overlay.failure is None,str(overlay.failure)
            paper=bitmap.GetPixel(2,2);gap=bitmap.GetPixel(2,88)
            assert (paper.R,paper.G,paper.B)==(19,39,52),'Overlay cards were not painted'
            assert gap.ToArgb()==overlay.form.TransparencyKey.ToArgb(),'Card gaps are not transparent'
        finally:bitmap.Dispose()
    host._ui(window,display)
    time.sleep(2.5)  # Worker thread only: the STA timer continues running.
    assert not host._ui(window,lambda:overlay.user.IsWindowVisible(overlay.form.Handle.ToInt64())),'Expired overlay stayed visible'
    stale={'key':'old','system':'J5A-IX','pilots':'Old','ships':'','character':'Smoke','jumps':1,'when':time.time()-10}
    send('syncIntelOverlay',data={'enabled':True,'seconds':1,'items':[stale]})
    assert not host._ui(window,lambda:overlay.user.IsWindowVisible(overlay.form.Handle.ToInt64()))
    fresh={**stale,'when':time.time()}
    send('syncIntelOverlay',data={'enabled':True,'seconds':60,'items':[fresh]})
    send('syncIntelOverlay',data={'enabled':False,'seconds':60,'items':[]})
    assert not host._ui(window,lambda:overlay.user.IsWindowVisible(overlay.form.Handle.ToInt64())),'Disabled overlay stayed visible'
    # Theme/language and the sample's Done action use the same real drawing path.
    def light_sample():
        from System.Drawing import Bitmap,Rectangle
        from System.Windows.Forms import MouseButtons,MouseEventArgs
        overlay.preferences('light','hu');overlay.configure({'editing':True})
        bitmap=Bitmap(overlay.form.Width,overlay.form.Height)
        try:
            overlay.form.DrawToBitmap(bitmap,Rectangle(0,0,bitmap.Width,bitmap.Height))
            assert overlay.failure is None,str(overlay.failure)
        finally:bitmap.Dispose()
        overlay._mouse_down(None,MouseEventArgs(MouseButtons.Left,1,overlay.form.Width-20,15,0))
        assert not overlay.state.editing
    host._ui(window,light_sample)
    reloaded=OverlayState(folder)
    assert reloaded.settings(host._ui(window,overlay.screens))['placement']=={'x':40,'y':60,'width':330}
    assert not reloaded.items and not reloaded.enabled
    return {'native_overlay':True,'overlay_expiry':True,'overlay_no_focus':True,'overlay_click_through':True,'overlay_placement':True}


def check_preview(host,window):
    """Exercise real DWM/WinForms against our own test surfaces, never an EVE client."""
    from muhely.windows_preview import Win32,PreviewState
    from System.Windows.Forms import Form,MouseButtons,MouseEventArgs
    from System.Drawing import Bitmap,Rectangle,Color
    sources=[];forms=[];actions=[]
    def create():
        for index in range(2):
            form=Form();form.Text='EVE - Preview CI '+str(index);form.Width=800;form.Height=500
            form.BackColor=Color.FromArgb(10+index*30,60,100);form.Show()
            forms.append(form);sources.append({'key':'ci-preview-'+str(index),'title':str(form.Text),'hwnd':form.Handle.ToInt64()})
    host._ui(window,create)
    with patch.object(Win32,'discover',return_value=sources):
        def exercise():
            preview=host.preview
            assert preview is not None and not preview.disposed
            preview.refresh();preview.last_poll=time.monotonic()+100
            preview.configure({'enabled':True,'only_eve':False,'next_key':{'code':75,'modifiers':0},'previous_key':{'code':72,'modifiers':0}})
            assert preview.state.hotkeys_active,'Native shortcut hook did not start'
            assert len(preview.tiles)==2
            for tile in preview.tiles.values():
                hwnd=tile['form'].Handle.ToInt64();style=preview.api.user.GetWindowLongPtrW(hwnd,-20)
                assert preview.api.user.IsWindowVisible(hwnd),'Preview is not visible'
                assert style&0x8 and style&0x80 and style&0x8000000,'Preview native styles are missing'
                assert not style&0x80000,'DWM thumbnails require an opaque destination window'
                assert not tile['form'].ShowInTaskbar
                assert tile['thumbnail'],'DWM did not register the live source'
                size=preview.api.W.SIZE()
                import ctypes
                assert preview.api.dwm.DwmQueryThumbnailSourceSize(tile['thumbnail'],ctypes.byref(size))==0
                assert size.cx>0 and size.cy>0
            first=preview.tiles[sources[0]['key']];slot=preview.state.slots[0]
            preview.configure({'editing':True})
            from muhely.windows_overlay import NativeOverlay
            screens=NativeOverlay.screens()
            screen=screens[0]
            preview.state.place(slot,screen['left']+70,screen['top']+90,330,screens)
            preview._bounds(slot,first)
            reloaded=PreviewState(host.folder)
            assert reloaded.slots[0]['width']==330 and reloaded.slots[0]['screen']==screen['id']
            assert not reloaded.editing,'Layout edit mode must not be restored at startup'
            preview.configure({'editing':False})
            real_callback=preview.callback
            preview.callback=lambda kind,data=None:actions.append((kind,data))
            try:
                preview.sync({'enabled':True,'characters':[{'name':'Preview CI 0','alerts':[{'kind':'crystal_broken','id':'ci-break'}],'last_damage':None}]})
                alert,x=preview._icons(slot,first)[0]
                assert x>=first['form'].Width-24,'Badge is not in the name bar right edge'
                preview._mouse(slot,first,MouseEventArgs(MouseButtons.Left,1,x+5,12,0))
                assert actions[-1]==('mining',{'name':'Preview CI 0','kind':'crystal_broken','id':'ci-break'})
                preview.sync({'enabled':True,'characters':[{'name':'Preview CI 0','alerts':[{'kind':'module_stopped','id':'ci-pause'}],'last_damage':None}]})
                preview._mouse(slot,first,MouseEventArgs(MouseButtons.Left,1,x+5,12,0))
                assert actions[-1][1]['kind']=='module_stopped'
                with patch.object(preview.state,'clock',return_value=1000.1):
                    preview.sync({'enabled':True,'characters':[{'name':'Preview CI 0','alerts':[],'last_damage':1000}]})
                    bitmap=Bitmap(first['form'].Width,first['form'].Height)
                    try:
                        first['form'].DrawToBitmap(bitmap,Rectangle(0,0,bitmap.Width,bitmap.Height))
                        assert preview.failure is None,str(preview.failure)
                        assert any((lambda c:c.R>180 and c.G<130 and c.B<130)(bitmap.GetPixel(x,y)) for x in range(7,150) for y in range(2,22)),'Damaged name did not paint red'
                    finally:bitmap.Dispose()
                with patch.object(preview.state,'clock',return_value=1011):assert not preview.state.flashing(slot['key'])
                # A click uses the same native activation path as a real thumbnail.
                preview._mouse(slot,first,MouseEventArgs(MouseButtons.Left,1,40,40,0))
                assert preview.api.user.GetForegroundWindow()==sources[0]['hwnd']
                preview.cycle(1);assert preview.api.user.GetForegroundWindow()==sources[1]['hwnd']
                preview.capture_key(True);assert not preview.hook.process(75,True,0,True)
                preview.capture_key(False);assert preview.hook.process(75,True,0,True)
                assert preview.events.get_nowait()==1
                assert preview.hook.process(75,False,0,True)
                # only_eve must hide behind the workshop and show for a game source.
                preview.configure({'only_eve':True})
                assert preview.api.user.SetForegroundWindow(window.native.Handle.ToInt64())
                preview._visibility();assert not preview.api.user.IsWindowVisible(first['form'].Handle.ToInt64())
                preview.activate(slot['key']);preview._visibility()
                assert preview.api.user.IsWindowVisible(first['form'].Handle.ToInt64())
                preview.configure({'enabled':False})
                assert not preview.tiles and not preview.state.hotkeys_active
                assert not preview.hook.thread.is_alive(),'Preview hook survived disable'
            finally:preview.callback=real_callback
        try:host._ui(window,exercise)
        finally:
            def cleanup():
                if host.preview is not None:host.preview.configure({'enabled':False})
                for form in forms:form.Dispose()
            host._ui(window,cleanup)
    return {'native_preview':True,'preview_dwm':True,'preview_activation':True,'preview_shortcuts':True,'preview_badges':True,'preview_damage':True,'preview_saved_layout':True}


def check(report_path=None):
    if sys.platform!='win32':raise RuntimeError('Windows is required for the native window test')
    import certifi
    os.environ['SSL_CERT_FILE']=certifi.where()
    import webview
    faulthandler.dump_traceback_later(55)
    from muhely.windows_window import WindowHost,webview_runtime_present,ensure_backend
    from desktop import stop_backend
    from muhely.windows_network import listener_present
    if not webview_runtime_present():raise RuntimeError('WebView2 Runtime is missing')
    with tempfile.TemporaryDirectory(prefix='eve-window-smoke-',ignore_cleanup_errors=True) as folder:
        # Use the production topology: the UI must not own the server's socket.
        # WebView2 child processes are then created only by the UI process.
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
        processes=[];popen=subprocess.Popen
        def spawn(*args,**kwargs):
            process=popen(*args,**kwargs);processes.append(process);return process
        with patch('muhely.windows_window.subprocess.Popen',side_effect=spawn):origin=ensure_backend(port,folder)
        assert len(processes)==1,'The test must own its separate backend process'
        assert listener_present(port),'Windows did not report the running backend listener'
        print('Separate production backend started.',flush=True)
        host=WindowHost(webview,origin,folder);window=host.create_main();results={};finished=threading.Event();external=[]
        window.events.closed+=finished.set
        def confirm(title,message):
            print(json.dumps({'close_confirmation':'accepted for disposable test profile'}),flush=True)
            return True
        window.create_confirmation_dialog=confirm
        original_dispatch=host.dispatch
        def traced_dispatch(target,source,body):
            action=body.get('action') if isinstance(body,dict) else None
            if action in {'quitCheck','quitFailed','stopped'}:
                print(json.dumps({'close_action':action,'phase':'start','dirty':body.get('dirty'),'running':body.get('running')}),flush=True)
            value=original_dispatch(target,source,body)
            if action in {'quitCheck','quitFailed','stopped'}:print(json.dumps({'close_action':action,'phase':'done'}),flush=True)
            return value
        host.dispatch=traced_dispatch
        def dialog(kind,**kwargs):return (str(Path(folder)/('native-export.csv' if 'save_filename' in kwargs else '')),)
        window.create_file_dialog=dialog
        original_clipboard=[]
        def restore_clipboard():
            from System.Windows.Forms import Clipboard
            if original_clipboard:
                host._ui(window,lambda:Clipboard.SetDataObject(original_clipboard[0],True) if original_clipboard[0] is not None else Clipboard.Clear())
                original_clipboard.clear()
        def result(body):
            print('Native bridge checks completed; checking overlay and window close.',flush=True)
            results.update(body.get('result',{}))
            try:
                if not results.get('error'):
                    assert (Path(folder)/'native-export.csv').read_text(encoding='utf-8-sig')=='Ferrofluid;25\n'
                    assert set(host.children)=={'map','chat'}
                    results['separate_windows']=len(host.children)
                    results['external_link_count']=len(external)
                    from System.Windows.Forms import Clipboard
                    assert host._ui(window,Clipboard.GetText)=='EVE window smoke'
                    results['clipboard_readback']=True
                    results.update(check_overlay(host,window,folder))
                    results.update(check_preview(host,window))
            except Exception as error:results['error']=str(error) or 'Native assertion failed'
            finally:
                restore_clipboard()
                print('Sending the same Form.Close request as the main window close button.',flush=True)
                # Window.destroy is the library's final-disposal API. Its extra
                # JS-semaphore teardown must not run on a cancellable close.
                host._ui(window,lambda:window.native.Close())
        host.self_test_callback=result
        script=r'''(async()=>{
          try{
            const wait=ms=>new Promise(r=>setTimeout(r,ms));
            for(let i=0;i<400&&(typeof state==='undefined'||!state);i++)await wait(50);
            if(!EveDesktop.active||EveDesktop.platform!=='windows')throw Error('Windows native bridge missing');
            if(state.characters.length||state.plans.length)throw Error('Profile is not empty');
            EveI18n.setLanguage('en');EveTheme.setTheme('dark');
            await navigator.clipboard.writeText('EVE window smoke');
            await EveDesktop.saveBlob(new Blob(['\ufeffFerrofluid;25\n']),'native-export.csv');
            await EveDesktop.openIntelWindow('map',{});await EveDesktop.openIntelWindow('chat',{});
            await EveDesktop.openExternal('https://zkillboard.com/character/359618261/');
            const realApi=api;globalThis.api=async(path,...args)=>path.startsWith('/api/desktop/auth?ticket=window-smoke')?{status:'complete'}:realApi(path,...args);
            sessionStorage.setItem('eve-muhely-auth-return','settings:access');
            await EveDesktop.authorize({url:location.origin+'/desktop/auth/window-smoke',ticket:'window-smoke'});
            globalThis.api=realApi;
            if(view!=='settings'||settingsTab!=='access')throw Error('OAuth return view changed');
            const policy=(await fetch('/')).headers.get('Content-Security-Policy')||'';if(!policy.includes("script-src 'self'")||policy.includes("'unsafe-eval'"))throw Error('Application CSP changed');
            // Native expiry must be tested without the empty profile's regular
            // intel poll clearing the synthetic report before the timer does.
            clearInterval(intelTick);intelNotificationRevision++;
            for(let i=0;i<100&&intelAlertBusy;i++)await wait(20);
            if(intelAlertBusy)throw Error('Intel polling did not settle');
            const overlay=await EveDesktop.intelOverlayStatus();
            if(!EveDesktop.overlayAvailable||!overlay.available||!overlay.screens.length)throw Error('Windows overlay bridge missing');
            await EveDesktop.configureIntelOverlay({editing:false});
            await EveDesktop.syncIntelOverlay({enabled:false,seconds:60,items:[]});
            await chrome.webview.postMessage({eveDesktop:1,id:900000,payload:{action:'selfTestResult',result:{native_webview2:true,empty_profile:true,export:true,oauth_return:true,csp_no_eval:true,theme:document.documentElement.dataset.theme,language:document.documentElement.lang}}});
          }catch(e){chrome.webview.postMessage({eveDesktop:1,id:900001,payload:{action:'selfTestResult',result:{error:String(e)}}});}
        })();'''
        def loaded():
            print('Main WebView2 page loaded.',flush=True)
            from System.Windows.Forms import Clipboard
            original_clipboard.append(host._ui(window,Clipboard.GetDataObject))
            host._script(window,script)
        window.events.loaded+=loaded
        def timeout():
            if not finished.wait(75):
                results['error']='Native window test timed out';restore_clipboard();host.stopped=True
                if host.overlay is not None:host._ui(window,host.overlay.dispose)
                if host.preview is not None:host._ui(window,host.preview.dispose)
                for child in list(host.children.values()):child.destroy()
                window.destroy()
        threading.Thread(target=timeout,daemon=True).start()
        webview.settings['ALLOW_FILE_URLS']=False;webview.settings['ALLOW_DOWNLOADS']=False;webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']=False
        try:
            with patch('muhely.windows_window.webbrowser.open',side_effect=lambda url:external.append(url) or True):
                webview.start(gui='edgechromium',debug=False,private_mode=False,storage_path=str(Path(folder)/'webview2'),user_agent='EVEWorkshopDesktop/Windows')
        finally:
            faulthandler.cancel_dump_traceback_later()
            results['backend_stopped']=stop_backend(origin)
            for process in processes:process.wait(timeout=10)
            results['backend_process_exited']=all(p.returncode==0 for p in processes)
            results['backend_listener_closed']=not listener_present(port)
        results['overlay_disposed']=host.overlay is not None and host.overlay.disposed
        results['preview_disposed']=host.preview is not None and host.preview.disposed
        if report_path:Path(report_path).write_text(json.dumps(results,indent=2))
        if results.get('error') or not results.get('clipboard_readback') or not results.get('native_overlay') or not results['overlay_disposed'] or not results.get('native_preview') or not results['preview_disposed'] or not results['backend_stopped'] or not results['backend_process_exited'] or not results['backend_listener_closed']:raise RuntimeError(results.get('error','Native result incomplete'))
        return results


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path);args=parser.parse_args()
    print(json.dumps(check(args.report)))
