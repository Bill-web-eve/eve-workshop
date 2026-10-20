'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
const root=path.join(__dirname,'../static'),wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function fixture(){
 const dom=new JSDOM('<html><body><header class=topbar><div></div></header><input id=draft value=unchanged><section id=view></section></body></html>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 for(const f of ['i18n-en.js','i18n.js','activity.js'])run(fs.readFileSync(path.join(root,f),'utf8'));
 w.fetch=async()=>({ok:true,json:async()=>({task:{running:false},market:{running:false},industry:{running:false}})});
 w.EveI18n.setLanguage('en');return {w,d,run};
}
function background(id='job1',overrides={}){return {id,kind:'notifications',running:true,started:Date.now()/1000,progress:{stage:'Személyes ipari adatok',stage_index:0,stages:5,subject:'Pilot <Test>',completed:3,total:10,resource:'Készlet',page:2,pages:7,mode:'request'},...overrides};}

test('concurrent requests stay busy until the last one completes and failures remain visible',async t=>{
 const {w,d}=fixture();t.after(()=>w.close());let resolveA,rejectB;
 const a=w.EveActivity.run('/api/plan',()=>new Promise(r=>resolveA=r));
 const b=w.EveActivity.run('/api/skills',()=>new Promise((r,e)=>rejectB=e));b.catch(()=>{});
 await wait(150);assert(!d.querySelector('#activity-panel').hidden);assert(d.querySelector('#activity-toggle').textContent.includes('2 operations'));
 resolveA({});await a;assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'true');assert(d.body.textContent.includes('Summarizing skills'));
 rejectB(Error('Synthetic API failure'));await assert.rejects(b);assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'false');assert(d.body.textContent.includes('Synthetic API failure'));
 assert(d.querySelector('[data-state=error]'));assert.equal(d.querySelector('#draft').value,'unchanged');
});
test('a fast failed request is shown even when the spinner delay has not elapsed',async t=>{
 const {w,d}=fixture();t.after(()=>w.close());await assert.rejects(w.EveActivity.run('/api/search',async()=>{throw Error('Offline');}));
 assert(!d.querySelector('#activity-panel').hidden);assert(d.body.textContent.includes('Offline'));
});
test('server stages, names, page counts and cache status survive navigation and live language changes',async t=>{
 const {w,d}=fixture();t.after(()=>w.close());w.fetch=()=>new Promise(()=>{});
 const task=background();w.EveActivity.task(task);await wait(150);
 assert(d.body.textContent.includes('Stage 1 of 5'));assert(d.body.textContent.includes('Checked: 3 / 10'));assert(d.body.textContent.includes('Page 2 of 7'));assert(d.body.textContent.includes('Pilot <Test>'));assert.equal(d.querySelector('test'),null);
 const progress=d.querySelector('progress');assert.equal(progress.max,10);assert.equal(progress.value,3);
 d.querySelector('#view').innerHTML='<h1>Another view</h1>';assert(!d.querySelector('#activity-panel').hidden);
 w.EveI18n.setLanguage('hu');assert(d.body.textContent.includes('Ellenőrizve: 3 / 10'));w.EveI18n.setLanguage('en');assert(d.body.textContent.includes('Checked: 3 / 10'));
 w.EveActivity.task({...task,progress:{...task.progress,mode:'cache'}});assert(d.body.textContent.includes('Valid EVE cache'));
 w.EveActivity.task({...task,running:false,outcome:'warning',message:'Néhány ipari költségadat nem frissült.'});assert(d.body.textContent.includes('Some industry cost data could not be refreshed.'));assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'false');
 w.EveActivity.task(task);assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'false');
});
test('a successful refresh-start response does not claim the background work is finished',async t=>{
 const {w,d}=fixture();t.after(()=>w.close());w.fetch=()=>new Promise(()=>{});
 await w.EveActivity.run('/api/notifications/sync',async()=>({ok:true}));await wait(150);
 assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'true');assert(d.body.textContent.includes('Checking operation status'));
 w.EveActivity.task(background('fast',{running:false,outcome:'success',message:'Az EVE-adatok frissítve.'}));assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'false');assert(d.body.textContent.includes('EVE data refreshed.'));
});
test('market and industry progress remain visible independently of each other',async t=>{
 const {w,d}=fixture();t.after(()=>w.close());w.fetch=()=>new Promise(()=>{});
 w.EveActivity.observe('/api/prices/refresh',{running:true,done:4,total:25,errors:{},current_name:'Ferrofluid',page:2,pages:3});
 w.EveActivity.observe('/api/industry/refresh',{running:true,done:1,current:'prices',errors:{}});await wait(150);
 assert(d.body.textContent.includes('Ferrofluid'));assert(d.body.textContent.includes('Prices checked: 4 / 25'));assert(d.body.textContent.includes('ESI adjusted prices'));
 w.EveActivity.observe('/api/prices',{running:false,done:25,total:25,errors:{}});assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'true');
 w.EveActivity.observe('/api/industry',{running:false,done:2,errors:{prices:'offline'}});assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'false');assert(d.body.textContent.includes('Some industry cost data could not be refreshed.'));
});
test('lost progress polling never claims success and explains that it will retry',async t=>{
 const {w,d}=fixture();t.after(()=>w.close());w.fetch=async()=>{throw Error('Offline');};
 w.EveActivity.task(background());await w.EveActivity.poll();await wait(150);
 assert(d.body.textContent.includes('completion has not yet been confirmed'));assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'true');assert(!d.querySelector('#activity-toggle').textContent.includes('All operations completed'));
});

test('a cached refresh-start response cannot leave a completed task waiting forever',async t=>{
 const {w,d}=fixture();t.after(()=>w.close());w.fetch=()=>new Promise(()=>{});
 const task=background();w.EveActivity.task(task);w.EveActivity.task({...task,running:false,outcome:'success',message:'Az EVE-adatok frissítve.'});
 await w.EveActivity.run('/api/notifications/sync',async()=>({ok:true}));w.EveActivity.task({...task,running:false,outcome:'success'});
 assert.equal(d.querySelector('#activity-panel').getAttribute('aria-busy'),'false');assert(d.body.textContent.includes('No data refresh is running.'));
});
