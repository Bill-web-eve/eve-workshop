const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
const tick=()=>new Promise(r=>setImmediate(r));
async function setup(){
 const dom=new JSDOM('<body><main></main></body>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),run=s=>vm.runInContext(s,dom.getInternalVMContext());
 run(`const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),fmt=String,itemName=s=>'<button class="copy-item-name" data-copy-item="'+esc(s)+'">'+esc(s)+'</button>';globalThis.EveLocations={markup:id=>'<span data-i18n-skip>Station '+id+'</span>'};`);
 for(const name of ['i18n-en.js','i18n.js','readiness.js'])run(fs.readFileSync(__dirname+'/../static/'+name,'utf8'));
 await tick();return {dom,w:dom.window,d:dom.window.document};
}
const ready=(status='stock',location_status='local')=>({status,location_status,target_location_id:6001,blueprint_locations:[6001],has_wip:true,materials:[{name:'Ore <script>',quantity:5,stock:2,wip:1,missing:2,allocations:[{source:'stock',quantity:2,location_id:6001},{source:'wip',quantity:1,location_id:6002},{source:'missing',quantity:2,location_id:null}]}]});
test('compact material details escape names, show exact places and preserve copying across languages',async t=>{
 const {dom,w,d}=await setup();t.after(()=>dom.window.close());d.querySelector('main').innerHTML=w.EveReadiness.markup(ready('missing','transfer'))+w.EveReadiness.legend();await tick();
 assert.equal(d.querySelectorAll('script').length,0);assert.equal(d.querySelector('.copy-item-name').dataset.copyItem,'Ore <script>');
 assert.equal(d.querySelectorAll('.input-readiness>span.badge').length,2);assert(d.body.textContent.includes('Részben folyamatban'));
 assert(d.body.textContent.includes('Station 6002'));assert.equal(d.querySelectorAll('.input-dot').length,5);
 d.querySelector('details').open=true;w.EveI18n.setLanguage('en');await tick();
 assert(d.body.textContent.includes('Materials missing'));assert(d.body.textContent.includes('Transfer required'));assert(d.body.textContent.includes('Material details'));assert(d.body.textContent.includes('From stock:'));
 assert(!/[áéíóöőúüű]/i.test(d.body.textContent));assert(d.querySelector('details').open);
 assert.equal(d.querySelector('.copy-item-name').textContent,'Ore <script>');
 assert.equal(w.EveReadiness.title(ready('wip','local')),'Materials in progress · At blueprint location');
 w.EveI18n.setLanguage('hu');await tick();assert(d.body.textContent.includes('Alapanyag hiányzik'));
});
test('unknown and multiple blueprint locations never imply that materials are on site',async t=>{
 const {dom,w,d}=await setup();t.after(()=>dom.window.close());
 const r={...ready(),target_location_id:null,blueprint_locations:[6001,6002],location_status:'unknown'};
 d.querySelector('main').innerHTML=w.EveReadiness.markup(r)+w.EveReadiness.markup(null);await tick();w.EveI18n.setLanguage('en');await tick();
 assert(d.body.textContent.includes('Multiple blueprint locations'));assert(d.body.textContent.includes('Location unverified'));assert(d.body.textContent.includes('Material status unknown'));
 assert.equal(w.EveReadiness.tone(r),'unknown');assert.equal(w.EveReadiness.tone(ready('stock','transfer')),'transfer');assert.equal(w.EveReadiness.tone(ready('wip')),'wip');
});
