'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
const code=fs.readFileSync(path.join(__dirname,'../static/desktop.js'),'utf8');
function fixture(native=true){
 const dom=new JSDOM('<html lang=en data-theme=dark><body></body></html>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,messages=[];
 if(native)w.webkit={messageHandlers:{eveDesktop:{postMessage:async body=>{messages.push(body);return {saved:true};}}}};
 vm.runInContext(code,dom.getInternalVMContext());return {w,messages,run:s=>vm.runInContext(s,dom.getInternalVMContext())};
}
test('native clipboard is plain text and exports preserve exact UTF-8 bytes',async t=>{
 const {w,messages}=fixture();t.after(()=>w.close());
 await w.navigator.clipboard.writeText('Ferrofluid');
 assert.equal(messages.find(m=>m.action==='clipboard').text,'Ferrofluid');
 const text='\ufeff"Termék";"Mennyiség"\r\n"Ferrofluid";"25"';
 await w.EveDesktop.saveBlob(new w.Blob([text],{type:'text/csv'}),'eve-list.csv');
 const file=messages.find(m=>m.action==='save');assert.equal(file.filename,'eve-list.csv');assert.equal(Buffer.from(file.base64,'base64').toString('utf8'),text);
 assert.equal(w.document.documentElement.dataset.desktop,'mac');
});
test('browser clients do not acquire a native bridge or a clipboard replacement',t=>{
 const {w}=fixture(false);t.after(()=>w.close());assert.equal(w.EveDesktop.active,false);assert.equal(w.document.documentElement.dataset.desktop,undefined);assert.equal(w.navigator.clipboard,undefined);
});
test('native authorization returns to the requested Settings section without navigating the app',async t=>{
 const {w,messages,run}=fixture();t.after(()=>w.close());
 const timer=w.setTimeout;w.setTimeout=(cb,ms)=>timer(cb,ms===2000?0:ms);
 run("globalThis.toast=()=>{};globalThis.api=async()=>({status:'complete'});globalThis.reloadState=async()=>{};globalThis.openSettingsTab=tab=>globalThis.returnedTab=tab;globalThis.render=()=>{};");
 w.sessionStorage.setItem('eve-muhely-auth-return','settings:access');
 await w.EveDesktop.authorize({url:'http://127.0.0.1:8765/desktop/auth/test-ticket',ticket:'test-ticket'});
 assert.equal(w.location.pathname,'/');assert.equal(w.returnedTab,'access');assert.equal(w.sessionStorage.getItem('eve-muhely-auth-return'),null);
 assert.equal(messages.find(m=>m.action==='external').url,'http://127.0.0.1:8765/desktop/auth/test-ticket');assert(messages.some(m=>m.action==='activate'));
});
test('quit checks pending work and shuts down with the current CSRF token',async t=>{
 const {w,messages,run}=fixture();t.after(()=>w.close());const requests=[];
 run('let dirty={stock:true};');
 w.fetch=async(path,options)=>{requests.push({path,options});return {ok:true,json:async()=>({csrf:'fresh-csrf',task:{running:true}})};};
 await w.EveDesktop.prepareQuit();const check=messages.find(m=>m.action==='quitCheck');assert(check.dirty);assert(check.running);
 await w.EveDesktop.shutdown();assert.equal(requests.find(r=>r.path==='/api/shutdown').options.headers['X-CSRF-Token'],'fresh-csrf');assert(messages.some(m=>m.action==='stopped'));
});
test('a rejected shutdown does not silently quit the native window',async t=>{
 const {w,messages}=fixture();t.after(()=>w.close());
 w.fetch=async path=>({ok:path!=='/api/shutdown',json:async()=>({csrf:'test'})});
 await w.EveDesktop.shutdown();assert(messages.some(m=>m.action==='quitFailed'));assert(!messages.some(m=>m.action==='stopped'));
});

test('desktop windows are limited to map/chat and include only public view options',async t=>{
 const {w,messages}=fixture();t.after(()=>w.close());await w.EveDesktop.openIntelWindow('map',{character_id:123,region:10000001});const call=messages.find(m=>m.action==='openIntelWindow');assert(call);assert.equal(call.kind,'map');
 await assert.rejects(w.EveDesktop.openIntelWindow('settings'));
});

test('test notification requests the default OS notification sound',async t=>{
 const {w,messages,run}=fixture();t.after(()=>w.close());
 run(`globalThis.$=s=>document.querySelector(s);globalThis.$$=s=>[...document.querySelectorAll(s)];globalThis.EveI18n={t:s=>s};globalThis.esc=s=>String(s);globalThis.panel=(title,subtitle,html)=>html;globalThis.error=message=>{throw Error(message)};let dirty={};`);
 run(fs.readFileSync(path.join(__dirname,'../static/notifications.js'),'utf8'));
 w.EveDesktop.notificationStatus=async()=>({status:'authorized'});
 run(`notificationData={preferences:{os_enabled:true,auto_refresh:true,personal:true,corporations:true,categories:{jobs:true},moon_days:3,moon_owners:{}},moons:[]};notificationPermission='authorized';renderNotificationSettings(document.body);`);
 await w.document.querySelector('#notification-test').onclick();
 const notification=messages.find(m=>m.action==='notify');assert(notification);assert.equal(notification.sound,true);assert.equal(notification.category,'all');
});
