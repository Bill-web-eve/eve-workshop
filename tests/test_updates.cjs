'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
function fixture(){
 const dom=new JSDOM('<html><body><div id="update-banner" hidden></div><div id="settings-content"></div></body></html>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext()),requests=[],actions=[];
 run(`let state={version:'1.8.0'},view='settings',settingsTab='updates',dirty={};globalThis.EveI18n={language:'en',t:s=>s};globalThis.esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');globalThis.panel=(title,subtitle,body)=>body;globalThis.error=e=>globalThis.lastError=e;globalThis.openSettingsTab=tab=>globalThis.openedTab=tab;`);
 w.EveDesktop={active:true,installUpdate:async ticket=>{actions.push(['install',ticket]);return {started:true};},shutdown:async()=>actions.push(['shutdown']),openExternal:async url=>actions.push(['external',url])};
 let data={current_version:'1.8.0',latest_version:'1.9.0',available:true,automatic:true,installable:true,busy:false,phase:'available',notes_url:'https://github.com/Bill-web-eve/eve-workshop/releases/tag/v1.9.0'};
 w.api=async(url,body)=>{requests.push([url,body]);if(url==='/api/state')return {task:{running:false}};return {...data};};
 const on=w.addEventListener.bind(w);w.addEventListener=(event,...args)=>{if(event!=='DOMContentLoaded')on(event,...args);};
 run(fs.readFileSync(path.join(__dirname,'../static/updates.js'),'utf8'));w.addEventListener=on;
 return {w,run,requests,actions,close:()=>w.close(),set:d=>{data={...data,...d};run('updateData='+JSON.stringify(data));}};
}
test('an available update appears without changing the production view or inputs',t=>{
 const f=fixture();t.after(f.close);f.run("view='queue';");f.set({latest_version:'1.9.0<script>alert(1)</script>'});f.run('paintUpdates()');
 assert.equal(f.run('view'),'queue');assert(f.w.document.querySelector('#update-banner').textContent.includes('<script>'));assert.equal(f.w.document.querySelector('#update-banner script'),null);
 f.w.document.querySelector('#update-banner button').click();assert.equal(f.w.openedTab,'updates');
});
test('daily check and manual check are distinct and preferences persist through the API',async t=>{
 const f=fixture();t.after(f.close);await f.w.requestUpdates('check',false);await f.w.requestUpdates('check',true);
 assert.deepEqual(f.requests.slice(0,2).map(r=>[r[0],r[1].manual]),[['/api/updates/check',false],['/api/updates/check',true]]);
 f.w.document.querySelector('#updates-automatic').checked=false;await f.w.document.querySelector('#updates-automatic').onchange({target:{checked:false}});
 assert.equal(f.requests.at(-1)[0],'/api/updates/preferences');assert.equal(f.requests.at(-1)[1].automatic,false);
});
test('install blocks unsaved changes and running data checks before downloading',async t=>{
 const f=fixture();t.after(f.close);f.set({});f.run('dirty={pending:1}');await f.w.installUpdate();assert.equal(f.actions.length,0);assert.equal(f.requests.length,0);
 f.run('dirty={}');f.w.api=async()=>({task:{running:true}});await f.w.installUpdate();assert.equal(f.actions.length,0);assert(f.w.lastError);
});
test('ready update sends only the opaque ticket then uses complete application shutdown',async t=>{
 const f=fixture();t.after(f.close);f.set({phase:'ready',ticket:'a'.repeat(32)});await f.w.installUpdate();
 assert.deepEqual(f.actions,[['install','a'.repeat(32)],['shutdown']]);assert.equal(f.run('updateData.phase'),'installing');assert.equal(f.run('updateData.busy'),true);
});
test('one click downloads first and automatically proceeds only after verified ready status',async t=>{
 const f=fixture();t.after(f.close);f.set({});let ready=false;
 f.w.api=async url=>{f.requests.push([url]);if(url==='/api/state')return {task:{running:false}};return {current_version:'1.8.0',available:true,installable:true,busy:!ready,phase:ready?'ready':'downloading',ticket:'b'.repeat(32)};};
 await f.w.installUpdate();assert.equal(f.requests.at(-1)[0],'/api/updates/download');assert.equal(f.actions.length,0);
 ready=true;await f.w.refreshUpdates();await new Promise(r=>setImmediate(r));assert.deepEqual(f.actions,[['install','b'.repeat(32)],['shutdown']]);
});
test('a failed native preparation never closes the application',async t=>{
 const f=fixture();t.after(f.close);f.set({phase:'ready',ticket:'c'.repeat(32)});f.w.EveDesktop.installUpdate=async()=>{throw Error('not enough space');};await f.w.installUpdate();
 assert.equal(f.actions.length,0);assert.equal(f.w.lastError,'not enough space');assert.equal(f.run('updateData.busy'),false);
});
test('browser, detached windows and source installations cannot initiate replacement',async t=>{
 const f=fixture();t.after(f.close);f.set({installable:false});f.run('paintUpdates()');assert(f.w.document.querySelector('#updates-install').disabled);await f.w.installUpdate();assert.equal(f.actions.length,0);
 f.set({installable:true});f.w.history.replaceState({},'','/?intel_window=map');await f.w.installUpdate();assert.equal(f.actions.length,0);
 f.w.history.replaceState({},'','/');f.w.EveDesktop.active=false;await f.w.requestUpdates('check');assert.equal(f.requests.length,0);
});
test('untrusted error text is never inserted as markup or exposed as a download URL',t=>{
 const f=fixture();t.after(f.close);f.set({error:'<img src=x onerror=alert(1)>',phase:'error'});f.run('paintUpdates()');assert.equal(f.w.document.querySelector('#settings-content img'),null);
 assert.equal(f.w.document.querySelectorAll('#settings-content a').length,0);
});

test('startup waits for the authenticated app state and starts only once',async t=>{
 const f=fixture();t.after(f.close);
 await f.w.startUpdateChecks();assert.equal(f.requests.length,0);
 f.run("state.csrf='ready-token'");await f.w.startUpdateChecks();await f.w.startUpdateChecks();
 assert.equal(f.requests.length,1);assert.equal(f.requests[0][0],'/api/updates/check');assert.equal(f.requests[0][1].manual,false);
});
