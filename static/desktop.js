'use strict';
// Shared native adapter: Cocoa/WKWebView on Mac, WebView2 messages on Windows.
globalThis.EveDesktop=(()=>{
  const macHandler=globalThis.webkit?.messageHandlers?.eveDesktop;
  const windows=!!globalThis.chrome?.webview&&/EVEWorkshopDesktop\/Windows/.test(navigator.userAgent);
  const pending=new Map();let sequence=0;
  if(windows)chrome.webview.addEventListener('message',event=>{
    const reply=event.data;if(!reply||reply.eveDesktop!==1||!Number.isSafeInteger(reply.id))return;
    const call=pending.get(reply.id);if(!call)return;pending.delete(reply.id);clearTimeout(call.timer);
    if(reply.error)call.reject(Error(reply.error));else call.resolve(reply.value);
  });
  const handler=macHandler||(windows?{postMessage:payload=>new Promise((resolve,reject)=>{
    const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(Error('Az alkalmazásablak nem válaszol. Próbáld újra.'));},180000);
    pending.set(id,{resolve,reject,timer});
    try{chrome.webview.postMessage({eveDesktop:1,id,payload});}catch(e){clearTimeout(timer);pending.delete(id);reject(e);}
  })}:null);
  const active=!!handler;let authGeneration=0;
  const send=(action,data={})=>handler?Promise.resolve(handler.postMessage({action,...data})):Promise.reject(Error('Desktop window unavailable'));
  const preferences=()=>{if(active)void send('preferences',{theme:document.documentElement.dataset.theme||'dark',language:document.documentElement.lang||'hu'}).catch(()=>{});};
  async function saveBlob(blob,filename){
    if(blob.size>32*1024*1024)throw Error('A fájl túl nagy a mentéshez.');
    const base64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=reject;reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.readAsDataURL(blob);});
    return send('save',{filename,base64});
  }
  async function authorize(auth){
    if(!active){window.location.assign(auth.url);return;}
    const generation=++authGeneration;
    await send('external',{url:auth.url});
    toast('Az EVE-belépés a böngésződben nyílt meg. Jóváhagyás után térj vissza ide.');
    const end=Date.now()+11*60*1000;
    while(generation===authGeneration&&Date.now()<end){
      await new Promise(resolve=>setTimeout(resolve,2000));
      const result=await api('/api/desktop/auth?ticket='+encodeURIComponent(auth.ticket));
      if(generation!==authGeneration)return;
      if(result.status==='pending')continue;
      if(result.status!=='complete')throw Error(result.error||'Az EVE-belépés lejárt. Próbáld újra.');
      await reloadState();
      const back=sessionStorage.getItem('eve-muhely-auth-return');sessionStorage.removeItem('eve-muhely-auth-return');
      if(typeof settingsAccessData!=='undefined')settingsAccessData=null;
      if(back?.startsWith('settings:'))openSettingsTab(back.split(':')[1]);
      if(back==='mining'){navigate('mining');void refreshMining();}
      render();
      preferences();await send('activate');toast('Karakter engedélyezve. Frissítsd az EVE-adatokat.');return;
    }
    if(generation===authGeneration)throw Error('Az EVE-belépés lejárt. Próbáld újra.');
  }
  async function prepareQuit(){
    let running=false;
    try{const response=await fetch('/api/state');if(response.ok)running=(await response.json()).task.running;}catch{}
    await send('quitCheck',{dirty:typeof dirty!=='undefined'&&Object.keys(dirty).length>0,running});
  }
  async function shutdown(){
    try{
      // Refresh the local cookie/CSRF pair if the backend was restarted.
      await fetch('/');const response=await fetch('/api/state');
      if(!response.ok)throw Error('shutdown');
      {const current=await response.json();const stopped=await fetch('/api/shutdown',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':current.csrf},body:'{}'});if(!stopped.ok)throw Error('shutdown');}
      await send('stopped');
    }catch(e){if(e instanceof TypeError)await send('stopped');else await send('quitFailed');}
  }
  if(active){
    document.documentElement.dataset.desktop=windows?'windows':'mac';
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:text=>send('clipboard',{text:String(text)})}});
    document.addEventListener('click',event=>{
      const link=event.target.closest('a[download]');if(!link)return;
      const url=new URL(link.href,location.href);if(url.origin!==location.origin)return;
      event.preventDefault();event.stopImmediatePropagation();
      const download=()=>fetch(url).then(response=>{if(!response.ok)throw Error('A fájl mentése nem sikerült.');return response.blob();});
      void (globalThis.EveActivity?EveActivity.run('/api/export',download):download()).then(blob=>saveBlob(blob,link.download)).catch(e=>error(e.message));
    },true);
    window.print=()=>void send('print');
    window.addEventListener('eve-theme-change',preferences);window.addEventListener('eve-language-change',preferences);
    document.addEventListener('DOMContentLoaded',preferences,{once:true});
  }
  function openIntelWindow(kind,options={}){
    if(!['map','chat'].includes(kind))return Promise.reject(Error('Hibás intelablak.'));
    if(active)return send('openIntelWindow',{kind,options});
    const query=new URLSearchParams({intel_window:kind});for(const key of ['character_id','region','center'])if(Number.isSafeInteger(options[key])&&options[key]>0)query.set(key,options[key]);if(options.history)query.set('history','1');
    const child=window.open('/?'+query,'eve-intel-'+kind,'popup,width='+(kind==='map'?1200:700)+',height=800');return child?Promise.resolve({opened:true}):Promise.reject(Error('A külön ablakot a böngésző letiltotta. Engedélyezd a felugró ablakokat.'));
  }
  return {active,platform:windows?'windows':macHandler?'mac':'browser',overlayAvailable:!!macHandler,saveBlob,openIntelWindow,intelOverlayStatus:()=>send('intelOverlayStatus'),configureIntelOverlay:options=>send('configureIntelOverlay',{options}),syncIntelOverlay:data=>send('syncIntelOverlay',{data}),openExternal:url=>send('external',{url}),chooseIntelFolder:()=>send('chooseIntelFolder'),authorize,prepareQuit,shutdown,notificationStatus:()=>send('notificationStatus'),requestNotifications:()=>send('requestNotifications'),notify:content=>send('notify',content),quit:()=>send('stopped')};
})();
async function openEveAuthorization(auth){return EveDesktop.authorize(auth);}
