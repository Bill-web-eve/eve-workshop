'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function setup(){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765/',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[];
 const state={csrf:'test',version:'1.5.0',settings:{source:'manual'},characters:[],corporations:[{id:99,name:'Corp'}],plans:[],production_characters:[],jobs:[],task:{running:false},sde:{buildNumber:1},recipe_count:1};
 const row=(id,corp)=>({id,domain:'jobs:'+id,category:'jobs',kind:'job_ready',subject:'Test item',corporation_id:corp,scope_name:corp?'Corp':'Personal',character_name:'Pilot',reliable:true,when:1800000000,checked_at:1800000000,dismissal_key:id.padEnd(64,'a')});
 const data={items:[row('personal',null),row('corporate',99)],corporations:state.corporations,moons:[],counts:{jobs:2,data:0},task:state.task,next_sync_at:9999999999,preferences:{os_enabled:false,auto_refresh:true,moon_days:3,personal:true,corporations:true,categories:{intel:true,skills:true,jobs:true,pi:true,moons:true,contracts:true,implants:true}}};
 let dismissFail=false,toggleFail=false;
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 w.fetch=async(url,opts)=>{
  const body=opts?.body?JSON.parse(opts.body):null;calls.push({url,body});let value;
  if(url==='/api/state')value=state;
  else if(url==='/api/notifications')value=data;
  else if(url==='/api/intel/alerts')value={enabled:false,items:[]};
  else if(url==='/api/notifications/dismiss'){
   if(dismissFail)return {ok:false,json:async()=>({error:'Acknowledgment failed'})};
   data.items=data.items.filter(a=>a.id!==body.id);data.counts.jobs=data.items.length;value={ok:true};
  }else if(url==='/api/notifications/preferences'){
   if(toggleFail)return {ok:false,json:async()=>({error:'Preference failed'})};
   Object.assign(data.preferences.categories,body.categories);value=data.preferences;
  }else if(url==='/api/notifications/claim')value={items:[]};
  else throw Error('Unexpected request '+url);
  return {ok:true,json:async()=>JSON.parse(JSON.stringify(value))};
 };
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();run('navigate("notifications")');await tick();
 return {w,d,run,calls,data,failDismiss:()=>{dismissFail=true;},failToggle:()=>{toggleFail=true;}};
}
test('each personal/corporation alert can be acknowledged and disappears with updated counts',async t=>{
 const {w,d,run,calls}=await setup();t.after(()=>w.close());
 const button=d.querySelector('[data-notification-dismiss=personal]');assert.equal(button.textContent,'Acknowledge');assert.equal(d.querySelector('#notification-count').textContent,'2');
 button.click();await tick();await tick();
 assert.equal(d.querySelector('[data-notification-dismiss=personal]'),null);assert.equal(d.querySelector('#notification-count').textContent,'1');
 assert.deepEqual(calls.find(c=>c.url==='/api/notifications/dismiss').body,{id:'personal',dismissal_key:'personal'.padEnd(64,'a')});
 d.querySelector('[data-notification-scope=corporations]').click();d.querySelector('[data-notification-dismiss=corporate]').click();await tick();await tick();
 assert.equal(d.querySelectorAll('[data-notification-dismiss]').length,0);assert.equal(d.querySelector('#notification-count').hidden,true);
 await run('refreshNotifications(false)');assert.equal(d.querySelectorAll('[data-notification-dismiss]').length,0);
});
test('failed acknowledgment keeps the alert visible and available for retry',async t=>{
 const {w,d,failDismiss}=await setup();t.after(()=>w.close());failDismiss();d.querySelector('[data-notification-dismiss=personal]').click();await tick();await tick();
 assert.equal(d.querySelector('[data-notification-dismiss=personal]').disabled,false);assert.equal(d.querySelector('#notification-count').textContent,'2');assert(d.querySelector('#global-error').textContent.includes('Acknowledgment failed'));
});
test('Intel slider sits directly below the brand, stops overlay and preserves all other preferences',async t=>{
 const {w,d,run,calls,data}=await setup();t.after(()=>w.close());
 const button=d.querySelector('#sidebar-intel-toggle');assert.equal(d.querySelector('.brand').nextElementSibling,button);assert.equal(button.getAttribute('role'),'switch');assert.equal(button.textContent,'Intel');assert.equal(button.getAttribute('aria-checked'),'true');assert.equal(button.getAttribute('aria-label'),'Intel notifications');
 const before=JSON.parse(JSON.stringify(data.preferences)),overlays=[];w.EveDesktop.active=true;w.EveDesktop.syncIntelOverlay=async p=>overlays.push(p);
 button.click();await tick();await tick();assert.equal(button.getAttribute('aria-checked'),'false');assert(overlays.some(p=>p.enabled===false&&p.items.length===0));
 assert.deepEqual(calls.find(c=>c.url==='/api/notifications/preferences').body,{categories:{intel:false}});
 assert.deepEqual(data.preferences,{...before,categories:{...before.categories,intel:false}});
 await run('refreshNotifications(false)');assert.equal(button.getAttribute('aria-checked'),'false');
 button.click();await tick();await tick();assert.equal(button.getAttribute('aria-checked'),'true');assert.deepEqual(data.preferences,before);
 w.EveI18n.setLanguage('hu');await tick();assert.equal(button.textContent,'Intel');assert.equal(button.getAttribute('aria-label'),'Intelértesítések');assert.equal(d.querySelector('[data-notification-dismiss=personal]').textContent,'Tudomásul vettem');
});
test('failed quick-toggle restores the authoritative state and cannot disable other notifications',async t=>{
 const {w,d,data,failToggle}=await setup();t.after(()=>w.close());failToggle();const button=d.querySelector('#sidebar-intel-toggle');button.click();assert.equal(button.disabled,true);await tick();await tick();
 assert.equal(button.disabled,false);assert.equal(button.getAttribute('aria-checked'),'true');assert.equal(data.preferences.categories.intel,true);assert(d.querySelector('#global-error').textContent.includes('Preference failed'));
});
