'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
const source=fs.readFileSync(__dirname+'/../static/app.js','utf8');
const message='Pehra Qirna: Ipari jobok: Az EVE-adatok most nem érhetők el. A korábbi adatok megmaradtak. Kézi módban folytathatod a tervezést.';
const good=(items=3)=>({product_id:100,name:'Salvation',quantity:1,activity:'manufacturing',stale_characters:[],calculated_at:1700000000,summary:{items},rows:[],queue:[{id:1,name:'Material'}]});
async function setup(){
 const dom=new JSDOM('<body><button id=calculate></button><div id=calculation-feedback></div><div id=calculated-at></div><div id=queue-count></div><div id=plan-status></div><div id=global-error></div><button id=save-plan></button><button id=new-plan></button><input id=target-quantity value=1><input id=product-search value=Salvation><select id=production-scope></select><select id=manufacturer></select><span id=scope-hint></span><main></main></body>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 for(const f of ['i18n-en.js','i18n.js'])run(fs.readFileSync(__dirname+'/../static/'+f,'utf8'));
 run(`const $=s=>document.querySelector(s),esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),fmt=String,date=String;
 let plan=null,planGeneration=0,planLoadedKey=null,productId=100,productName='Salvation',activePlanId='a',corporationId=null,manufacturerId=1,dirty={},deliveryWait=null,productActivity=null;
 let state={plans:[{id:'a',product_id:100,reserve_active:true}],corporations:[],production_characters:[{id:1,name:'Pilot',available:true}],settings:{source:'eve'},inventory:{},parameters:{},reservation_revision:'r1'};
 const targetQuantity=()=>Number($('#target-quantity').value),manufacturerValue=()=>String(manufacturerId||'manual'),scoped=s=>s;
 function renderPlanShortcuts(){} function updateReadyJobs(){} function scheduleDeliveryCheck(){} function confirmUI(){return true;}
 const EveNumbers={validate(){}};
 function error(message){$('#global-error').textContent=message;}
 function render(){document.querySelector('main').innerHTML=plan?(plan.refresh_error?planRefreshFailureMarkup(plan):'')+'<p>Previous production rows</p>':'';}
 async function reloadState(){}
 `);
 run(source.slice(source.indexOf('function updatePlanControls()'),source.indexOf('function scheduleTaskPoll()')));
 run(source.slice(source.indexOf('function currentPlanKey('),source.indexOf('function navigate(')));
 w.api=async()=>good();await new Promise(r=>setImmediate(r));
 return {w,d:w.document,run};
}
test('temporary refresh errors retain exactly the open result, block saving and recover on success',async t=>{
 const {w,d,run}=await setup();t.after(()=>w.close());await w.calculate(false);
 w.api=async()=>{throw Error(message);};assert.equal(await w.calculate(false),null);
 assert.equal(run('plan.summary.items'),3);assert.equal(run('plan.refresh_error'),message);assert(d.querySelector('[data-plan-refresh-failed]'));
 assert.equal(d.querySelector('#save-plan').disabled,true);assert.equal(d.querySelector('#queue-count').textContent,'3');assert.equal(d.querySelector('#calculate').disabled,false);
 w.EveI18n.setLanguage('en');w.EveI18n.translate(d.body);
 assert(d.body.textContent.includes('Recalculation failed; showing the last successful plan.'));assert(d.body.textContent.includes('Industry jobs: EVE data is currently unavailable. Previous data has been preserved.'));
 assert(!/[áéíóöőúüű]/i.test(d.body.textContent));assert.equal(run('state.reservation_revision'),'r1');
 w.api=async()=>good(5);await w.calculate(false);
 assert.equal(run('plan.summary.items'),5);assert.equal(run('plan.refresh_error'),undefined);assert.equal(d.querySelector('#save-plan').disabled,false);assert.equal(d.querySelector('[data-plan-refresh-failed]'),null);
});
test('previous results cannot leak to another target, scope, producer, saved plan or changed calculation inputs',async t=>{
 for(const mutation of ["productId=200","$('#target-quantity').value='2'","corporationId=99","manufacturerId=2","activePlanId='b';state.plans.push({id:'b',product_id:100})","state.settings.source='manual'","state.inventory[1]={quantity:99}","state.parameters[100]={me:5}","state.reservation_revision='r2'"]){
  const {w,d,run}=await setup();await w.calculate(false);run(mutation);w.api=async()=>{throw Error(message);};await w.calculate(false);
  assert.equal(run('plan'),null,mutation);assert.equal(d.querySelector('[data-plan-refresh-failed]'),null);w.close();
 }
});
test('first load failures cannot invent a result, and late failures cannot erase a newer successful calculation',async t=>{
 const {w,run}=await setup();t.after(()=>w.close());w.api=async()=>{throw Error(message);};await w.calculate(false);assert.equal(run('plan'),null);
 let rejectOld;w.api=()=>new Promise((_,reject)=>rejectOld=reject);const old=w.calculate(false);
 w.api=async()=>good(9);await w.calculate(false);rejectOld(Error(message));await old;
 assert.equal(run('plan.summary.items'),9);assert.equal(run('plan.refresh_error'),undefined);
});
test('the real scheduler refuses a retained failed result without issuing a scheduling request',async t=>{
 const {w,d,run}=await setup();t.after(()=>w.close());await w.calculate(false);w.api=async()=>{throw Error(message);};await w.calculate(false);
 run(`let view='schedule';const $$=s=>[...document.querySelectorAll(s)];function setHead(){}function panel(){return '';}function itemName(s){return s;}function verbatim(s){return esc(s);}`);
 w.EveScheduleGraph={DEFAULT_DAYS:7,validDays:()=>false};
 run(fs.readFileSync(__dirname+'/../static/schedule.js','utf8'));run(`renderSchedule(document.querySelector('main'));`);
 assert(d.querySelector('#schedule-form button[type=submit]').disabled);assert(d.querySelector('[data-plan-refresh-failed]'));
 let calls=0;w.api=async()=>{calls++;return {};};await d.querySelector('#schedule-form').onsubmit({preventDefault(){}});assert.equal(calls,0);
});
test('completion of the background EVE refresh retries a failed plan and restores normal controls',async t=>{
 const {w,d,run}=await setup();t.after(()=>w.close());await w.calculate(false);
 w.api=async()=>{throw Error(message);};await w.calculate(false);assert(d.querySelector('#save-plan').disabled);
 run(`let taskTimer,lastTaskFinished,view='queue',skillData,piData,moonData,settingsAccessData;function refreshNotifications(){};state.task={running:false,finished:42,kind:'notifications',results:[]};`);
 run(source.slice(source.indexOf('function scheduleTaskPoll()'),source.indexOf('function currentPlanKey(')));
 let callback,calls=0;w.setTimeout=fn=>{callback=fn;return 1;};w.clearTimeout=()=>{};
 w.api=async()=>{calls++;return good(8);};w.scheduleTaskPoll();await callback();
 assert.equal(run('plan.summary.items'),8);assert.equal(run('plan.refresh_error'),undefined);assert(!d.querySelector('#save-plan').disabled);
 w.scheduleTaskPoll();await callback();assert.equal(calls,1);
});
test('inventory lag labels the confirmed historical allocation without claiming new live shortages',async t=>{
 const {w,d,run}=await setup();t.after(()=>w.close());
 run(`function deliveryRetryTimestamp(){return '1 Nov at 09:16';}`);
 run(source.slice(source.indexOf('function deliveryPreviewMarkup('),source.indexOf('function renderDeliveryWait(')));
 w.waitData={frozen_snapshot_at:1700000000,retry_at:1700000900,items:[]};
 run(`document.querySelector('main').innerHTML=deliveryPreviewMarkup(waitData);`);
 w.EveI18n.setLanguage('en');w.EveI18n.translate(d.body);
 assert(d.body.textContent.includes('Showing the last confirmed plan allocation.'));assert(d.body.textContent.includes('Conflicting data is not used to reallocate materials between plans.'));
 assert(!d.body.textContent.includes('shortfall and production quantities may be overestimated'));
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('main').textContent));
});
