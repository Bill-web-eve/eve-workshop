'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function setup(){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[];
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 const config={enabled:false,product_id:11985,inventor_id:1,decryptor_id:0,prices:'jita:sell',attempts:100,copy_runs:10,copying:{system_id:10,facility_tax:'2.5',job_cost_role:'0',scc_surcharge:'4',alpha_surcharge:'0'},invention:{system_id:10,facility_tax:'2.5',job_cost_role:'0',scc_surcharge:'4',alpha_surcharge:'0'}};
 const state={csrf:'test',version:'1.5.0',settings:{source:'manual'},characters:[{id:1,name:'Inventor'}],production_characters:[],corporations:[],jobs:[],plans:[{id:'basilisk',product_id:11985,product_name:'Basilisk',name:'Basilisk',quantity:10,reserve_active:true}],invention_products:[11985],sde:{buildNumber:1},task:{running:false},recipe_count:1};
 const options={config,manufacturing_prices:'jita:sell',recipe:{copy_limit:10},base_name:'Osprey',product_name:'Basilisk',characters:[{id:1,name:'Inventor',available:true}],decryptors:[{id:34205,name:'Process Decryptor'},{id:34206,name:'Symmetry Decryptor'}],systems:{10:'System'}};
 const row=(id,total)=>({decryptor_id:id,name:id?'Process Decryptor':'No decryptor',probability:'.65',me:id?5:2,te:10,runs_per_bpc:1,expected_successes:'65',expected_runs:'65',materials_cents:'2000',copy_per_attempt_cents:'100',invention_job_cents:'200',per_run_cents:'3538',bpc_total_cents:'35380',manufacturing_materials_cents:'100000',manufacturing_jobs_cents:'1000',total_cents:total,saving_cents:'0',missing_prices:[]});
 let fail=false,pending=null;
 w.fetch=async(url,opts)=>{const body=opts?.body?JSON.parse(opts.body):null;calls.push({url,body});let data;
  if(url==='/api/state')data=state;
  else if(url==='/api/intel/alerts')data={enabled:false,items:[]};
  else if(url==='/api/notifications')data={items:[],counts:{data:0},task:state.task,moons:[],corporations:[],preferences:{os_enabled:false,categories:{intel:false}}};
  else if(url.startsWith('/api/invention/options'))data=options;
  else if(url==='/api/invention/estimate'){
   if(pending)return pending;
   if(fail)return {ok:false,json:async()=>({error:'Calculation failed'})};
   const rows=[row(0,'200000'),row(34205,'136380')];data={config:body.config,quantity:body.quantity,skills:[{name:'Science',active:5,required:1}],skills_ready:true,rows,selected:rows.find(r=>r.decryptor_id===body.config.decryptor_id)||rows[0],best_decryptor_id:34205,copying:{complete:true},invention:{complete:true},industry:{running:false},price_ids:[1,2],price_sources:['jita']};
  }else if(url==='/api/trade/plan'){data={ok:true};}
  else if(url.startsWith('/api/moons/systems'))data=[{id:11,name:'New System'}];
  else if(url==='/api/prices/refresh'||url==='/api/industry/refresh')data={running:false};
  else throw Error('Unexpected '+url);
  return {ok:true,json:async()=>JSON.parse(JSON.stringify(data))};};
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();run('productId=11985;productName="Basilisk";activePlanId="basilisk";EveNumbers.set($("#target-quantity"),10);navigate("invention")');await tick();await tick();
 return {w,d,run,calls,fail:()=>{fail=true;},setPending:p=>{pending=p;}};
}
test('invention has a dedicated translated view, all cost columns, expected fractional outcomes and lowest full cost',async t=>{
 const {w,d,calls}=await setup();t.after(()=>w.close());assert.equal(d.querySelector('#page-title').textContent,'Invention and BPC cost');assert.equal(d.querySelector('[data-view=invention]').classList.contains('active'),true);
 d.querySelector('#invention-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();await tick();
 const text=d.querySelector('#invention-result').textContent;assert(text.includes('65'));assert(text.includes('Lowest full production cost'));assert(text.includes('Copying / attempt'));assert(text.includes('Manufacturing materials'));assert(!/[áéíóöőúüű]/i.test(text),text);
 const request=calls.find(c=>c.url==='/api/invention/estimate');assert.equal(request.body.config.inventor_id,1);assert.equal(request.body.quantity,10);
 w.EveI18n.setLanguage('hu');await tick();assert(d.querySelector('#invention-result').textContent.includes('Várható siker'));
});
test('chosen decryptor saves an enabled per-plan profile and can subsequently be disabled',async t=>{
 const {w,d,calls}=await setup();t.after(()=>w.close());d.querySelector('#invention-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();await tick();
 d.querySelector('[data-invention-use="34205"]').click();await tick();await tick();let saved=calls.filter(c=>c.url==='/api/trade/plan').at(-1).body;assert.equal(saved.plan_id,'basilisk');assert.equal(saved.invention.decryptor_id,34205);assert.equal(saved.invention.enabled,true);
 const form=d.querySelector('#invention-form');form.elements.enabled.checked=false;form.elements.prices.value='local:split';d.querySelector('#invention-save').click();await tick();await tick();saved=calls.filter(c=>c.url==='/api/trade/plan').at(-1).body;assert.equal(saved.invention.enabled,false);assert.equal(saved.invention.prices,'local:split');
 assert(!calls.some(c=>c.url==='/api/plans/reservation'||c.url==='/api/inventory'));
});
test('refresh fetches market prices and industry indices explicitly, and errors leave configuration available',async t=>{
 const {w,d,calls,fail}=await setup();t.after(()=>w.close());d.querySelector('#invention-refresh').click();await tick();await tick();await tick();assert(calls.some(c=>c.url==='/api/prices/refresh'&&c.body.manual));assert(calls.some(c=>c.url==='/api/industry/refresh'&&c.body.manual));
 fail();d.querySelector('#invention-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();await tick();assert.equal(d.querySelector('#invention-form [type=submit]').disabled,false);assert(d.querySelector('#global-error').textContent.includes('Calculation failed'));assert.equal(d.querySelector('#invention-form').elements.inventor_id.value,'1');
});
test('a late comparison response cannot replace another product view',async t=>{
 const {w,d,run,setPending}=await setup();t.after(()=>w.close());let resolve;setPending(new Promise(r=>{resolve=r;}));d.querySelector('#invention-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();run('productId=1;render()');resolve({ok:true,json:async()=>({rows:[],selected:{},industry:{running:false},price_sources:[]})});await tick();await tick();assert(d.querySelector('#view-content').textContent.includes('Choose an inventable T2 ship'));assert.equal(d.querySelector('#invention-result'),null);
});
