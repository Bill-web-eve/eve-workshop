'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function fixture(){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[];
 const characters=[{id:1,name:'Alice',corporation_id:99},{id:2,name:'Bob',corporation_id:99},{id:3,name:'Cara',corporation_id:98}];
 const corporations=[{id:99,name:'Corp A',members:characters.slice(0,2)},{id:98,name:'Corp B',members:characters.slice(2)}];
 const state={csrf:'test',version:'1.2.0',characters,corporations,production_characters:[],plans:[],jobs:[],settings:{source:'manual',character_ids:[1],location_ids:[100]},task:{running:false,results:[]},sde:{buildNumber:1},recipe_count:1,scope_label:'Personal'};
 const job=(id,name,cid,status='active')=>({job_id:id,name,character_id:cid,character_name:characters.find(c=>c.id===cid).name,product_type_id:590,status,runs:3,expected_output:3,output_location_id:999,end_date:'2099-01-01T00:00:00Z'});
 const data={personal:{rows:[job(1,'Personal A',1),job(2,'Personal B',2,'ready'),job(3,'Personal C',3)],sources:characters.map(c=>({...c,available:true}))},99:{rows:[job(10,'Corp A item',2)],sources:[{id:99,name:'Corp A',available:true}]},98:{rows:[job(20,'Corp B item',3)],sources:[{id:98,name:'Corp B',available:true}]}};
 let delayed=null,fail=false;w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 w.fetch=async(url,options)=>{calls.push(url);let value;
  if(url.startsWith('/api/state')){const cid=Number(new URL(url,w.location.href).searchParams.get('corporation_id'))||null;value={...state,corporation_id:cid,scope_label:cid?corporations.find(c=>c.id===cid).name:'Personal'};}
  else if(url==='/api/notifications')value={items:[],counts:{data:0},task:{running:false},corporations:[],moons:[],preferences:{os_enabled:false,categories:{intel:true}}};
  else if(url==='/api/intel/alerts')value={enabled:false,items:[]};
  else if(url.startsWith('/api/jobs')){const cid=new URL(url,w.location.href).searchParams.get('corporation_id')||'personal';value=data[cid];if(delayed){const gate=delayed;delayed=null;await gate;}if(fail)return {ok:false,json:async()=>({error:'Try again'})};}
  else throw Error('Unexpected request '+url);
  return {ok:true,json:async()=>value};
 };
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();run('productId=590;productName="Saved target";$("#product-search").value=productName;navigate("jobs")');await tick();await tick();
 return {w,d,run,calls,data,delay:p=>{delayed=p;},fail:value=>{fail=value;}};
}
const rows=d=>[...d.querySelectorAll('#job-results tbody tr:not(.table-empty-row)')].map(r=>r.cells[0].textContent);
test('personal All characters shows everyone despite production selection; character dropdown filters locally',async t=>{
 const {w,d,run,calls}=await fixture();t.after(()=>w.close());
 assert.equal(d.querySelector('.plan-selector').hidden,true);assert(d.querySelector('#job-scope'));assert(d.querySelector('#job-character'));
 assert.equal(d.querySelector('#job-character').options[0].textContent,'All characters');assert.equal(rows(d).length,3);
 assert(d.querySelector('#job-results [role=alert]'));const before=calls.filter(c=>c.startsWith('/api/jobs')).length;
 const character=d.querySelector('#job-character');character.value='1';character.dispatchEvent(new w.Event('change'));
 assert.equal(rows(d).length,1);assert(rows(d)[0].includes('Personal A'));assert(!d.querySelector('#job-results [role=alert]'));
 character.value='';character.dispatchEvent(new w.Event('change'));await tick();assert.equal(rows(d).length,3);
 assert.equal(calls.filter(c=>c.startsWith('/api/jobs')).length,before);assert.equal(run('manufacturerId'),0);
 assert(!calls.some(c=>c.startsWith('/api/plan')));assert(!/[áéőű]/i.test(d.querySelector('#view-content').textContent),d.querySelector('#view-content').textContent);
});
test('corporation scope stays on In progress, uses installer character and keeps personal jobs separate',async t=>{
 const {w,d,run,calls}=await fixture();t.after(()=>w.close());
 let select=d.querySelector('#job-scope');select.value='99';select.dispatchEvent(new w.Event('change'));await tick();await tick();await tick();
 assert.equal(run('view'),'jobs');assert.equal(rows(d).length,1);assert(rows(d)[0].includes('Corp A item'));assert(!rows(d)[0].includes('Personal'));
 assert.equal(d.querySelector('#job-results tbody tr td:nth-child(5)').textContent,'Bob');
 assert(!calls.some(c=>c.startsWith('/api/plan')));
 select=d.querySelector('#job-scope');select.value='';select.dispatchEvent(new w.Event('change'));await tick();await tick();await tick();
 assert.equal(rows(d).length,3);assert.equal(d.querySelector('#job-character').value,'');assert.equal(d.querySelector('#product-search').value,'Saved target');
});
test('late scope responses cannot replace current jobs and failures have a retry',async t=>{
 const {w,d,run,delay,fail}=await fixture();t.after(()=>w.close());let release;delay(new Promise(r=>{release=r;}));
 let select=d.querySelector('#job-scope');select.value='99';select.dispatchEvent(new w.Event('change'));await tick();await tick();
 select=d.querySelector('#job-scope');select.value='98';select.dispatchEvent(new w.Event('change'));await tick();await tick();await tick();
 assert(rows(d)[0].includes('Corp B item'));release();await tick();await tick();assert(rows(d)[0].includes('Corp B item'));
 fail(true);run('jobData=null;jobRevision++;render()');await tick();await tick();assert(d.querySelector('#job-retry'));assert.equal(rows(d).length,0);
 fail(false);d.querySelector('#job-retry').click();await tick();await tick();assert(rows(d)[0].includes('Corp B item'));
});
