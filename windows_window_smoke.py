"""Run the real WebView2 window against a disposable profile, never user data."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import patch


def check(report_path=None):
    if sys.platform!='win32':raise RuntimeError('Windows is required for the native window test')
    import certifi
    os.environ['SSL_CERT_FILE']=certifi.where()
    import webview
    from muhely.server import App,Server,ROOT
    from muhely.windows_window import WindowHost,webview_runtime_present
    if not webview_runtime_present():raise RuntimeError('WebView2 Runtime is missing')
    with tempfile.TemporaryDirectory(prefix='eve-window-smoke-',ignore_cleanup_errors=True) as folder:
        app=App(folder,ROOT/'data/catalog.sqlite3',0);server=Server(app)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        host=WindowHost(webview,app.origin,folder);window=host.create_main();results={};finished=threading.Event();external=[]
        def dialog(kind,**kwargs):return (str(Path(folder)/('native-export.csv' if 'save_filename' in kwargs else '')),)
        window.create_file_dialog=dialog
        original_clipboard=[]
        def restore_clipboard():
            from System.Windows.Forms import Clipboard
            if original_clipboard:
                host._ui(window,lambda:Clipboard.SetDataObject(original_clipboard[0],True) if original_clipboard[0] is not None else Clipboard.Clear())
                original_clipboard.clear()
        def result(body):
            results.update(body.get('result',{}));finished.set()
            try:
                if not results.get('error'):
                    assert (Path(folder)/'native-export.csv').read_text(encoding='utf-8-sig')=='Ferrofluid;25\n'
                    assert set(host.children)=={'map','chat'}
                    results['separate_windows']=len(host.children)
                    results['external_link_count']=len(external)
                    from System.Windows.Forms import Clipboard
                    assert host._ui(window,Clipboard.GetText)=='EVE window smoke'
                    results['clipboard_readback']=True
            except Exception as error:results['error']=str(error) or 'Native assertion failed'
            finally:
                restore_clipboard();host._script(window,'void EveDesktop.shutdown()')
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
            await chrome.webview.postMessage({eveDesktop:1,id:900000,payload:{action:'selfTestResult',result:{native_webview2:true,empty_profile:true,export:true,oauth_return:true,csp_no_eval:true,theme:document.documentElement.dataset.theme,language:document.documentElement.lang}}});
          }catch(e){chrome.webview.postMessage({eveDesktop:1,id:900001,payload:{action:'selfTestResult',result:{error:String(e)}}});}
        })();'''
        def loaded():
            from System.Windows.Forms import Clipboard
            original_clipboard.append(host._ui(window,Clipboard.GetDataObject))
            host._script(window,script)
        window.events.loaded+=loaded
        def timeout():
            if not finished.wait(75):
                results['error']='Native window test timed out';restore_clipboard();host.stopped=True
                for child in list(host.children.values()):child.destroy()
                window.destroy()
        threading.Thread(target=timeout,daemon=True).start()
        webview.settings['ALLOW_FILE_URLS']=False;webview.settings['ALLOW_DOWNLOADS']=False;webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER']=False
        try:
            with patch('muhely.windows_window.webbrowser.open',side_effect=lambda url:external.append(url) or True):
                webview.start(gui='edgechromium',debug=False,private_mode=False,storage_path=str(Path(folder)/'webview2'),user_agent='EVEWorkshopDesktop/Windows')
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
        if report_path:Path(report_path).write_text(json.dumps(results,indent=2))
        if results.get('error') or not results.get('clipboard_readback'):raise RuntimeError(results.get('error','Native result incomplete'))
        return results


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',type=Path);args=parser.parse_args()
    print(json.dumps(check(args.report)))
