'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
const payload='A & <img src="x" onerror="alert(1)"> \' "><svg onload="alert(2)">';
async function fixture(){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 const state={csrf:'test',characters:[],corporations:[],production_characters:[],plans:[],jobs:[],settings:{source:'manual'},task:{running:false},sde:{buildNumber:1},recipe_count:1};
 w.fetch=async url=>({ok:true,json:async()=>url==='/api/state'?state:url==='/api/notifications'?{items:[],counts:{},task:{running:false},corporations:[],preferences:{os_enabled:false,categories:{intel:false}}}:{enabled:false,items:[]}});
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();return {w,d,run};
}
test('shared text encoding preserves literal characters in HTML text and quoted attributes',async t=>{
 const {w,d,run}=await fixture();t.after(()=>w.close());w.securityPayload=payload;
 run(`$('#view-content').innerHTML='<div id="security-sample" data-value="'+esc(securityPayload)+'">'+esc(securityPayload)+'</div>'`);
 const sample=d.querySelector('#security-sample');assert.equal(sample.textContent,payload);assert.equal(sample.getAttribute('data-value'),payload);
 assert.equal(sample.children.length,0);assert.equal(sample.attributes.length,2);
});
test('exception details and empty-state text cannot become HTML or event attributes',async t=>{
 const {w,d,run}=await fixture();t.after(()=>w.close());w.securityPayload=payload;
 run('const securityFailure=new Error(securityPayload);shoppingData={error:securityFailure.message};renderAllShopping($("#view-content"))');
 assert.equal(d.querySelector('#view-content .banner.error').textContent,payload);
 assert.equal(d.querySelector('#view-content img,#view-content svg,#view-content script,#view-content [onerror]'),null);
 run('$("#view-content").innerHTML=empty(securityPayload,securityPayload)');
 assert.equal(d.querySelector('.empty h2').textContent,payload);assert.equal(d.querySelector('.empty p').textContent,payload);
 assert.equal(d.querySelector('.empty img,.empty svg,.empty [onload]'),null);
});
test('appending the combined-shortfall error does not read and reparse previous DOM markup',async t=>{
 const {w,d,run}=await fixture();t.after(()=>w.close());const content=d.querySelector('#view-content');
 const descriptor=Object.getOwnPropertyDescriptor(w.Element.prototype,'innerHTML');
 Object.defineProperty(content,'innerHTML',{configurable:true,get(){throw Error('Existing DOM must not be read as HTML');},set(value){descriptor.set.call(this,value);}});
 w.securityPayload=payload;run('shoppingData={error:securityPayload};renderAllShopping($("#view-content"))');
 assert.equal(content.querySelector('.banner.error').textContent,payload);
});
test('translated attributes remain literal text and never become URL or event-handler attributes',async t=>{
 const dom=new JSDOM('<html lang="hu"><body><input title="Cím" placeholder="Cím" aria-label="Cím"><img alt="Cím"></body></html>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'});t.after(()=>dom.window.close());
 const w=dom.window,d=w.document;w.EveEnglish={'Cím':payload};
 vm.runInContext(fs.readFileSync(path.join(root,'i18n.js'),'utf8'),dom.getInternalVMContext());await tick();w.EveI18n.setLanguage('en');await tick();
 const input=d.querySelector('input');for(const name of ['title','placeholder','aria-label'])assert.equal(input.getAttribute(name),payload);
 assert.equal(d.querySelector('img').getAttribute('alt'),payload);
 assert.equal(d.querySelectorAll('img').length,1);assert.equal(d.querySelector('[onerror],[onload],a,script,svg'),null);
 w.EveI18n.setLanguage('hu');assert.equal(input.title,'Cím');
});

test('table headers and metadata use the same text-only encoding boundary',async t=>{
 const {w,d,run}=await fixture();t.after(()=>w.close());w.securityPayload=payload;
 run(`$('#view-content').innerHTML=table([securityPayload],['<tr><td>safe</td></tr>'],'security-table')`);
 const heading=d.querySelector('#view-content th');assert(heading.textContent.includes(payload));assert.equal(heading.getAttribute('data-label'),payload);
 assert.equal(d.querySelector('#view-content img,#view-content svg,#view-content [onerror]'),null);
});

test('inventory-wait timestamps from an exception cannot inject sorting attributes',async t=>{
 const {w,d,run}=await fixture();t.after(()=>w.close());w.securityPayload=payload;
 run(`deliveryWait={plan_name:securityPayload,retry_at:Date.now()/1000+100,items:[{name:securityPayload,character_name:securityPayload,assets_as_of:securityPayload,completed_at:securityPayload}]};renderDeliveryWait($('#view-content'));`);
 const cells=[...d.querySelectorAll('#view-content td[data-sort-value]')];assert.equal(cells.length,2);
 assert(cells.every(cell=>cell.getAttribute('data-sort-value')===payload));
 assert.equal(d.querySelector('#view-content img,#view-content svg,#view-content [onerror],#view-content [onload]'),null);
});
