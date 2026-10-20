'use strict';
// Platform adapter. Browser and future Windows clients keep their current paths.
globalThis.EveDesktop=(()=>{
  const handler=globalThis.webkit?.messageHandlers?.eveDesktop;
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
    document.documentElement.dataset.desktop='mac';
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:text=>send('clipboard',{text:String(text)})}});
    document.addEventListener('click',event=>{
      const link=event.target.closest('a[download]');if(!link)return;
      const url=new URL(link.href,location.href);if(url.origin!==location.origin)return;
      event.preventDefault();event.stopImmediatePropagation();
      void fetch(url).then(response=>{if(!response.ok)throw Error('A fájl mentése nem sikerült.');return response.blob();}).then(blob=>saveBlob(blob,link.download)).catch(e=>error(e.message));
    },true);
    window.print=()=>void send('print');
    window.addEventListener('eve-theme-change',preferences);window.addEventListener('eve-language-change',preferences);
    document.addEventListener('DOMContentLoaded',preferences,{once:true});
  }
  return {active,saveBlob,authorize,prepareQuit,shutdown,quit:()=>send('stopped')};
})();
async function openEveAuthorization(auth){return EveDesktop.authorize(auth);}
