'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=__dirname+'/../static/',source=fs.readFileSync(root+'app.js','utf8');
const tick=()=>new Promise(r=>setImmediate(r));
async function setup(){
 const dom=new JSDOM(fs.readFileSync(root+'index.html','utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 for(const f of ['i18n-en.js','i18n.js','numbers.js'])run(fs.readFileSync(root+f,'utf8'));
 run(`const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=String,fmt=String,date=String;
 let plan=null,planGeneration=0,planLoadedKey=null,productId=100,productName='Ship',activePlanId=null,corporationId=null,manufacturerId=0,dirty={},deliveryWait=null,productActivity='manufacturing',view='schedule';
 let state={plans:[{id:'skipped',product_id:100,product_name:'Ship',name:'Ship',quantity:1,skip_reactions:true,reserve_active:true,manufacturer_id:0},{id:'normal',product_id:100,product_name:'Ship',name:'Ship',quantity:1,skip_reactions:false,reserve_active:true,manufacturer_id:0}],corporations:[],production_characters:[],settings:{source:'manual'},inventory:{},parameters:{},reservation_revision:'r1'};
 const targetQuantity=()=>EveNumbers.parse($('#target-quantity').value),manufacturerValue=()=>String(manufacturerId||'manual'),scoped=s=>s;
 function renderPlanShortcuts(){} function updateReadyJobs(){} function scheduleDeliveryCheck(){} function confirmUI(){return true;}
 function error(message){$('#global-error').textContent=message;}function toast(){}function render(){}function restorePlanSelector(){}function empty(){return '';}
 async function reloadState(){}
 `);
 run(source.slice(source.indexOf('async function openSavedPlan('),source.indexOf('function scheduleTaskPoll()')));
 run(source.slice(source.indexOf('function currentPlanKey('),source.indexOf('function navigate(')));
 run(source.slice(source.indexOf("$('#skip-reactions').onchange="),source.indexOf("$('#manufacturer').onchange=")));
 run(source.slice(source.indexOf("$('#save-plan').onclick="),source.indexOf("$('#new-plan').onclick=")));
 const calls=[];w.api=async(url,body)=>{calls.push({url,body});if(url==='/api/plans/save')return {id:'saved'};
  const args=new URL(url,w.location.href).searchParams;return {product_id:100,name:'Ship',quantity:1,manufacturer_id:0,corporation_id:null,activity:'manufacturing',skip_reactions:args.get('skip_reactions')==='1',summary:{items:1},rows:[],queue:[],stale_characters:[],calculated_at:1700000000};};
 return {w,d,run,calls};
}
test('shared selector switches immediately, persists the mode, and translates both ways',async t=>{
 const {w,d,run,calls}=await setup();t.after(()=>w.close());
 const box=d.querySelector('#skip-reactions');assert.equal(box.checked,false);assert.equal(box.type,'checkbox');
 w.EveI18n.setLanguage('en');await tick();assert(d.querySelector('.plan-options').textContent.includes('Skip reactions'));assert(box.parentElement.title.includes('their reaction inputs are not expanded'));
 const key=run('currentPlanKey()');box.checked=true;await box.onchange();assert.notEqual(key,run('currentPlanKey()'));
 assert.equal(new URL(calls.at(-1).url,w.location.href).searchParams.get('skip_reactions'),'1');
 assert.equal(JSON.parse(w.localStorage.getItem('eve-muhely-last-plan')).skip_reactions,true);
 assert.equal(run('view'),'schedule');w.EveI18n.setLanguage('hu');await tick();assert(d.querySelector('.plan-options').textContent.includes('Reakciók kihagyása'));assert.equal(box.checked,true);
 box.checked=false;await box.onchange();assert.equal(new URL(calls.at(-1).url,w.location.href).searchParams.get('skip_reactions'),'0');
});
test('opening different saved plans restores each mode and saving sends the calculated mode',async t=>{
 const {w,d,run,calls}=await setup();t.after(()=>w.close());
 await w.openSavedPlan('skipped');assert(d.querySelector('#skip-reactions').checked);assert.equal(run('view'),'schedule');
 await w.openSavedPlan('normal');assert(!d.querySelector('#skip-reactions').checked);
 d.querySelector('#skip-reactions').checked=true;await d.querySelector('#save-plan').onclick();
 const save=calls.find(c=>c.url==='/api/plans/save');assert.equal(save.body.skip_reactions,true);assert.equal(save.body.product_id,100);
});
test('scheduler invalidates an older result and sends the current material mode',async t=>{
 const {w,d,run,calls}=await setup();t.after(()=>w.close());
 w.EveScheduleGraph={DEFAULT_DAYS:7,validDays:()=>false};
 run(`function setHead(){} function panel(){return '';} function verbatim(v){return v;} function renderScheduleResult(){};`);
 run(fs.readFileSync(root+'schedule.js','utf8'));
 const key=run('scheduleKey()');d.querySelector('#skip-reactions').checked=true;assert.notEqual(key,run('scheduleKey()'));
 run(`renderSchedule($('#view-content'));`);await d.querySelector('#schedule-form').onsubmit({preventDefault(){}});
 const request=calls.find(c=>c.url==='/api/schedule');assert.equal(request.body.skip_reactions,true);
});
