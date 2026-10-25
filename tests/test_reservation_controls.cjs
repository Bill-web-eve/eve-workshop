'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {JSDOM}=require('jsdom'),tick=()=>new Promise(r=>setImmediate(r));
function setup(){
 const dom=new JSDOM('<div id="plan-status"></div><div id="actions"></div><main></main>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[],errors=[];
 w.$=s=>w.document.querySelector(s);w.$$=s=>[...w.document.querySelectorAll(s)];w.esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');w.verbatim=s=>'<span data-i18n-skip>'+w.esc(s)+'</span>';w.itemName=w.verbatim;
 w.panel=(a,b,c)=>'<section><h2>'+a+'</h2><small>'+b+'</small>'+c+'</section>';w.empty=(a,b)=>'<h3>'+a+'</h3><p>'+b+'</p>';w.fmt=String;w.actions=s=>w.$('#actions').innerHTML=s;w.setHead=()=>{};
 w.dirty={};w.corporationId=null;w.productId=null;w.reservationDetailId=null;
 w.state={reservation_revision:'r1',corporations:[{id:99,name:'Corp'}],plans:[
 {id:'a',name:'A <safe>',product_name:'Product A',quantity:2,created:1,reserved_at:1,reserve_active:true,corporation_id:null},
 {id:'b',name:'B',product_name:'Product B',quantity:3,created:2,reserved_at:2,reserve_active:true,corporation_id:null},
 {id:'c',name:'Inactive',product_name:'Product C',quantity:4,created:3,reserved_at:null,reserve_active:false,corporation_id:null},
 {id:'corp',name:'Corp plan',product_name:'Product D',quantity:5,created:4,reserved_at:4,reserve_active:true,corporation_id:99}]};
 w.scopedPlans=()=>w.state.plans.filter(p=>p.corporation_id===w.corporationId);w.render=()=>w.renderReservations(w.$('main'));w.renderReservationDetails=()=>{};w.deliveryRetryTimestamp=()=> '25 Oct 2026 at 13:07';w.error=s=>errors.push(s);w.toast=()=>{};
 w.reloadState=async()=>{};w.calculate=async()=>{};w.setProductionScope=id=>{w.corporationId=id;w.render();};
 w.api=async(url,body)=>{calls.push({url,body});if(url.endsWith('/order'))body.ids.forEach((id,i)=>w.state.plans.find(p=>p.id===id).reserved_at=i+1);else w.state.plans.find(p=>p.id===body.id).reserve_active=body.active;w.state.reservation_revision='r2';return {ok:true};};
 for(const f of ['i18n-en.js','i18n.js','reservations.js'])run(fs.readFileSync(path.join(__dirname,'../static',f),'utf8'));
 w.render();return {w,run,calls,errors};
}
test('priority edits are drafts, cancel performs no request, and save sends one complete scoped revision',async t=>{
 const {w,calls}=setup();t.after(()=>w.close());assert.equal(w.$('safe'),null);assert.match(w.$('main').textContent,/A <safe>/);assert(!w.$('main').textContent.includes('Corp plan'));
 w.$('[data-reservation-move=b][data-direction="-1"]').click();assert.equal(calls.length,0);assert(w.dirty.reservation_order);assert.equal(w.$('[data-reservation-active]').dataset.reservationActive,'b');
 w.$('#reservation-order-cancel').click();assert.equal(calls.length,0);assert(!w.dirty.reservation_order);assert.equal(w.$('[data-reservation-active]').dataset.reservationActive,'a');
 w.$('[data-reservation-move=b][data-direction="-1"]').click();await w.$('#reservation-order-save').onclick();
 assert.equal(calls.length,1);assert.equal(calls[0].url,'/api/plans/reservations/order');assert.deepEqual(JSON.parse(JSON.stringify(calls[0].body)),{corporation_id:null,ids:['b','a'],revision:'r1'});assert(!w.dirty.reservation_order);
});
test('switch off keeps the saved plan, and corporation scope shows only that corporations controls',async t=>{
 const {w,calls}=setup();t.after(()=>w.close());const before=w.state.plans.length;
 w.$('[data-reservation-active=a]').click();await tick();await tick();assert.equal(calls[0].url,'/api/plans/reservation');assert.equal(calls[0].body.active,false);assert.equal(calls[0].body.id,'a');assert.equal(calls[0].body.revision,'r1');assert.equal(w.state.plans.length,before);assert(!w.$('[data-reservation-active=a]').checked);
 w.$('[data-reservation-scope="99"]').click();assert(w.$('[data-reservation-active=corp]'));assert.equal(w.$('[data-reservation-active=a]'),null);assert.equal(w.$('#plan-status').hidden,true);
});
test('inventory waits permit releasing holds while activation and order saving remain blocked',async t=>{
 const {w,calls}=setup();t.after(()=>w.close());w.state.delivery_wait={retry_at:1800000000};w.render();
 assert.equal(w.$('[data-reservation-active=a]').disabled,false);assert.equal(w.$('[data-reservation-active=c]').disabled,true);
 w.$('[data-reservation-move=b][data-direction="-1"]').click();assert.equal(w.$('#reservation-order-save').disabled,true);await w.$('#reservation-order-save').onclick();assert.equal(calls.length,0);
});
test('stale drafts and failed saves preserve order intent, and Hungarian/English labels switch safely',async t=>{
 const {w,errors}=setup();t.after(()=>w.close());w.$('[data-reservation-move=b][data-direction="-1"]').click();w.state.reservation_revision='changed';w.render();assert(w.$('#reservation-order-save').disabled);
 w.$('#reservation-order-cancel').click();w.$('[data-reservation-move=b][data-direction="-1"]').click();w.api=async()=>{throw Error('Changed in another window');};await w.$('#reservation-order-save').onclick();assert.equal(errors.at(-1),'Changed in another window');assert(w.dirty.reservation_order);
 w.EveI18n.setLanguage('en');await tick();assert.match(w.$('main').textContent,/Active reservations/);assert.match(w.$('#reservation-order-save').textContent,/Save order/);assert(!/[áéíóöőúüű]/i.test(w.$('main').textContent),w.$('main').textContent);
});
