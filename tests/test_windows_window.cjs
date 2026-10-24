'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),code=fs.readFileSync(path.join(__dirname,'../static/desktop.js'),'utf8');
function fixture(marker=true){
 const dom=new JSDOM('<html lang=en data-theme=dark><body></body></html>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,messages=[];let received;
 Object.defineProperty(w.navigator,'userAgent',{value:marker?'EVEWorkshopDesktop/Windows':'Edge browser'});
 w.chrome={webview:{addEventListener:(name,callback)=>{received=callback;},postMessage:message=>{messages.push(message);queueMicrotask(()=>received?.({data:{eveDesktop:1,id:message.id,value:{saved:true}}}));}}};
 const run=s=>vm.runInContext(s,dom.getInternalVMContext());run(code);return {w,run,messages,receive:data=>received({data})};
}
test('Windows WebView2 bridge supports clipboard and native file export without changing CSP',async t=>{
 const {w,messages}=fixture();t.after(()=>w.close());assert(w.EveDesktop.active);assert.equal(w.EveDesktop.platform,'windows');assert.equal(w.document.documentElement.dataset.desktop,'windows');
 await w.navigator.clipboard.writeText('Ferrofluid');assert.equal(messages.find(m=>m.payload.action==='clipboard').payload.text,'Ferrofluid');
 await w.EveDesktop.saveBlob(new w.Blob(['\ufeffFerrofluid;25\r\n']),'materials.csv');
 const saved=messages.find(m=>m.payload.action==='save').payload;assert.equal(saved.filename,'materials.csv');assert.equal(Buffer.from(saved.base64,'base64').toString(),'\ufeffFerrofluid;25\r\n');
 assert.equal(w.EveDesktop.overlayAvailable,true);
});
test('Windows overlay settings and reports use the checked native message bridge',async t=>{
 const {w,messages}=fixture();t.after(()=>w.close());
 await w.EveDesktop.intelOverlayStatus();await w.EveDesktop.configureIntelOverlay({editing:true,screen_id:'monitor',x:20,y:50,width:330});
 await w.EveDesktop.syncIntelOverlay({enabled:false,seconds:60,items:[]});
 assert(messages.some(m=>m.payload.action==='intelOverlayStatus'));
 assert.equal(messages.find(m=>m.payload.action==='configureIntelOverlay').payload.options.screen_id,'monitor');
 assert.equal(messages.find(m=>m.payload.action==='syncIntelOverlay').payload.data.enabled,false);
});
test('a normal Edge browser never acquires the desktop bridge',t=>{
 const {w,messages}=fixture(false);t.after(()=>w.close());assert.equal(w.EveDesktop.active,false);assert.equal(w.navigator.clipboard,undefined);assert.equal(messages.length,0);
});
test('Windows authorization preserves the current settings view and reactivates the native app',async t=>{
 const {w,run,messages}=fixture();t.after(()=>w.close());const timer=w.setTimeout;w.setTimeout=(cb,ms)=>timer(cb,ms===2000?0:ms);
 run('globalThis.toast=()=>{};globalThis.api=async()=>({status:"complete"});globalThis.reloadState=async()=>{};globalThis.openSettingsTab=tab=>globalThis.returnedTab=tab;globalThis.render=()=>{};');
 w.sessionStorage.setItem('eve-muhely-auth-return','settings:access');await w.EveDesktop.authorize({url:'http://127.0.0.1:8765/desktop/auth/ticket',ticket:'ticket'});
 assert.equal(w.returnedTab,'access');assert.equal(w.location.pathname,'/');assert(messages.some(m=>m.payload.action==='external'));assert(messages.some(m=>m.payload.action==='activate'));
});
test('unrelated bridge messages cannot resolve a native call; native errors are surfaced',async t=>{
 const {w,receive}=fixture();t.after(()=>w.close());let message;
 w.chrome.webview.postMessage=body=>{if(body.payload.action==='preferences'){queueMicrotask(()=>receive({eveDesktop:1,id:body.id,value:true}));return;}message=body;};
 const promise=w.EveDesktop.openExternal('https://zkillboard.com/character/359618261/');let settled=false;promise.then(()=>{settled=true;},()=>{settled=true;});
 receive({id:message.id,value:true});await Promise.resolve();assert.equal(settled,false);
 receive({eveDesktop:1,id:message.id+100,value:true});await Promise.resolve();assert.equal(settled,false);
 receive({eveDesktop:1,id:message.id,error:'Native action unavailable'});await assert.rejects(promise,/Native action unavailable/);
});
