'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {JSDOM}=require('jsdom');
function setup(){
 const dom=new JSDOM('<main></main>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[],sent=[],opened=[];
 w.$=s=>w.document.querySelector(s);w.$$=s=>[...w.document.querySelectorAll(s)];w.esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');w.verbatim=w.esc;
 w.table=(heads,rows)=>'<table><thead><tr>'+heads.map(h=>'<th>'+h+'</th>').join('')+'</tr></thead><tbody>'+rows.join('')+'</tbody></table>';
 w.panel=(a,b,html)=>'<h2>'+a+'</h2><p>'+b+'</p>'+html;
 w.fmt=n=>Number(n).toLocaleString('en-US');w.EveI18n={t:s=>s,date:()=>''};w.EveDesktop={active:true,notificationStatus:async()=>({status:'authorized'}),notify:async data=>sent.push(data)};
 w.dirty={};w.error=message=>{throw Error(message);};w.toast=()=>{};w.openEveAuthorization=async data=>opened.push(data);
 w.api=async(url,body)=>{calls.push({url,body});return {items:[],url:'https://login.eveonline.com/authorize'};};
 for(const name of ['numbers.js','notifications.js','i18n-en.js'])run(fs.readFileSync(path.join(__dirname,'../static',name),'utf8'));
 run(`document.querySelector('main').innerHTML=implantSettingsPanel({scopes:['esi-clones.read_implants.v1'],characters:[{id:11,name:'Pilot <safe>',enabled:true,threshold:'1000000000',authorized:false},{id:22,name:'Other',enabled:false,threshold:'2000000000',authorized:true}]});bindImplantSettings();`);
 return {w,run,calls,sent,opened};
}
test('per-character grouped threshold, switches and authorization preserve character identity',async t=>{
 const {w,calls,opened}=setup();t.after(()=>w.close());
 assert.equal(w.$('[data-implant-threshold="11"]').value,'1 000 000 000');assert(w.$('[data-implant-enabled="11"]').checked);assert(!w.$('[data-implant-enabled="22"]').checked);
 assert(w.$('main').textContent.includes('Pilot <safe>'));assert.equal(w.$('safe'),null);
 await w.$('[data-implant-authorize="11"]').onclick();assert.equal(calls[0].url,'/api/auth/start');assert.equal(calls[0].body.feature,'implants');assert.equal(calls[0].body.character_id,11);assert.equal(opened.length,1);assert.equal(w.sessionStorage.getItem('eve-muhely-auth-return'),'settings:notifications');
});
test('saving sends all characters and plain numeric ISK without losing unrelated dirty state',async t=>{
 const {w,calls}=setup();t.after(()=>w.close());
 w.$('[data-implant-threshold="11"]').value='1 250 000 000';w.dirty.other=true;w.$('#implant-preferences').oninput();
 w.refreshNotifications=async()=>{};
 await w.$('#implant-preferences').onsubmit({preventDefault(){}});
 assert.equal(calls[0].url,'/api/implants/preferences');assert.equal(calls[0].body.characters[0].threshold,'1250000000');assert.equal(calls[0].body.characters[1].enabled,false);assert(!w.dirty.implant_preferences);assert(w.dirty.other);
});
test('implant notifications include value and threshold even when intel notifications are off',async t=>{
 const {w,run,calls,sent}=setup();t.after(()=>w.close());
 const item={id:'implants:a',category:'implants',kind:'implant_undock',subject:'Pilot',corporation_id:null,notification_id:'a',receipt:'r',value:'1100000000',threshold:'1000000000',when:null,sound:true};
 w.api=async(url,body)=>{calls.push({url,body});return {items:url.endsWith('/claim')?[item]:[]};};
 run('notificationData={preferences:{os_enabled:true,categories:{intel:false,implants:true}}};');
 await w.pollImplantAlerts();assert.equal(sent.length,1);assert(sent[0].body.includes('1,100,000,000 ISK'));assert(sent[0].body.includes('1,000,000,000 ISK'));assert.equal(sent[0].sound,true);assert(calls.some(c=>c.url==='/api/notifications/sent'));
});
test('disabled implant alerts do not claim, missing-price estimates say at least, translations exist',async t=>{
 const {w,run,calls}=setup();t.after(()=>w.close());run('notificationData={preferences:{os_enabled:true,categories:{implants:false}}};');
 await w.pollImplantAlerts();assert.equal(calls.length,0);assert(w.implantValue({partial:true,value:'10',threshold:'5'}).startsWith('Legalább'));
 for(const label of ['Implantfigyelés','Kidokkolás drága implantokkal','Implantfigyelés engedélyezése','Értékhatár (ISK)'])assert(w.EveEnglish[label]);
});
