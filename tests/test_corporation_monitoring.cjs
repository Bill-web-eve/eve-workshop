'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function fixture(){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[];
 const corp={id:99,name:'Corp A',monitoring_enabled:true,members:[{id:1,name:'Alice'}],ready:true,stale:false,asset_count:7,blueprint_count:2,job_count:3,synced_at:1000};
 const state={csrf:'test',version:'1.2.0',characters:[{id:1,name:'Alice'}],corporations:[corp],production_characters:[],plans:[],jobs:[],settings:{source:'manual'},task:{running:false,results:[],kind:'pi',message:''},sde:{buildNumber:1},recipe_count:1};
 w.localStorage.setItem('eve-muhely-language','en');
 w.fetch=async(url,options)=>{const body=options?.body?JSON.parse(options.body):null;calls.push({url,body});let value;
  if(url==='/api/state')value=state;
  else if(url==='/api/notifications')value={items:[],counts:{data:0},task:{running:false},corporations:[],moons:[],preferences:{os_enabled:false,categories:{intel:true}}};
  else if(url==='/api/intel/alerts')value={enabled:false,items:[]};
  else if(url==='/api/corporations')value={corporations:[corp],characters:state.characters};
  else if(url==='/api/corporations/monitoring'){corp.monitoring_enabled=body.enabled;value={corporations:[corp],characters:state.characters};}
  else if(url==='/api/pi/sync')value={};
  else throw Error('Unexpected request '+url);
  return {ok:true,json:async()=>value};
 };
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();run('navigate("corporations")');await tick();await tick();return {w,d,run,calls,corp};
}
test('corporation monitoring toggles persist and keep the previous inventory visible',async t=>{
 const {w,d,calls,corp}=await fixture();t.after(()=>w.close());
 assert.equal(d.querySelector('[data-corp-monitor]').checked,true);
 d.querySelector('[data-corp-monitor]').click();await tick();await tick();await tick();
 assert.deepEqual(calls.find(c=>c.url==='/api/corporations/monitoring').body,{id:99,enabled:false});
 assert.equal(d.querySelector('[data-corp-monitor]').checked,false);assert.equal(corp.asset_count,7);
 assert(d.querySelector('#view-content').textContent.includes('Monitoring disabled'));
 assert(!/[áéőű]/i.test(d.querySelector('#view-content').textContent));
});
test('manual refresh buttons pass the exception while automatic refreshes do not',async t=>{
 const {w,run,calls}=await fixture();t.after(()=>w.close());w.refreshPI=async()=>{};
 await run('startTask("/api/pi/sync",false)');await tick();
 await run('startTask("/api/pi/sync")');await tick();
 const requests=calls.filter(c=>c.url==='/api/pi/sync');
 assert.deepEqual(requests.map(c=>c.body),[{manual:false},{manual:true}]);
});

test('In progress hides the whole plan selector in personal and corporation scopes and restores it elsewhere',async t=>{
 const {w,d,run}=await fixture();t.after(()=>w.close());
 run('productId=92822;productName="Salvation";$("#product-search").value="Salvation";EveNumbers.set($("#target-quantity"),3);plan={stale_characters:["Old snapshot"],activity:"manufacturing",rows:[]};');
 const selector=d.querySelector('.plan-selector'),target=d.querySelector('#target-quantity');
 run('navigate("jobs")');await tick();assert.equal(selector.hidden,true);assert.equal(d.querySelector('#plan-status').hidden,true);
 assert.equal(d.querySelector('#page-title').textContent,'What is already in progress');
 run('corporationId=99;state.scope_label="Corp A";render()');await tick();assert.equal(selector.hidden,true);assert(d.querySelector('#view-content').textContent.includes('Corp A'));
 run('navigate("saved")');await tick();assert.equal(selector.hidden,false);assert.equal(d.querySelector('.plan-selector'),selector);
 assert.equal(target.value,'3');assert.equal(d.querySelector('#product-search').value,'Salvation');
});
