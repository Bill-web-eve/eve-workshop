'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),tick=()=>new Promise(r=>setTimeout(r,10));
function setup(){
 const dom=new JSDOM('<table><tbody id="places"></tbody></table><input id="draft" value="keep me">',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 run('let corporationId=null;');
 for(const f of ['i18n-en.js','i18n.js','locations.js'])run(fs.readFileSync(__dirname+'/../static/'+f,'utf8'));
 w.EveI18n.setLanguage('en');let refreshes=0;w.EveTables={refreshAll:()=>refreshes++};
 return {dom,w,run,d:w.document,refreshes:()=>refreshes};
}
test('duplicate job and blueprint destinations resolve once and preserve focused input',async t=>{
 const {dom,w,d}=setup();t.after(()=>w.close());const calls=[];
 w.api=async url=>{calls.push(url);return {locations:{60003760:{name:'Jita IV - Moon 4',status:'resolved'}}};};
 d.querySelector('#places').innerHTML=Array.from({length:8},()=>'<tr><td>'+w.EveLocations.markup(60003760)+'</td></tr>').join('');
 const input=d.querySelector('#draft');input.focus();await w.EveLocations.load();await tick();
 assert.equal(calls.length,1);assert.equal(calls[0],'/api/locations?ids=60003760');
 assert([...d.querySelectorAll('[data-location-id]')].every(n=>n.textContent==='Jita IV - Moon 4'));
 assert.equal(d.activeElement,input);assert.equal(input.value,'keep me');
 assert.equal(d.querySelector('td').dataset.sortValue,'Jita IV - Moon 4');
 assert.equal(d.querySelector('td').dataset.filterValue,'Jita IV - Moon 4 60003760');
 assert(d.querySelector('[data-location-id]').title.includes('60003760'));
});
test('late personal response never puts its private name on another corporation label',async t=>{
 const {dom,w,d}=setup();t.after(()=>w.close());let release;const calls=[];
 w.api=url=>{calls.push(url);if(!url.includes('corporation_id'))return new Promise(r=>release=r);return Promise.resolve({locations:{1000000000001:{name:'Corp place',status:'resolved'}}});};
 d.querySelector('#places').innerHTML='<tr><td>'+w.EveLocations.markup(1000000000001,null,null)+'</td></tr>';
 const first=w.EveLocations.load();
 d.querySelector('#places').innerHTML='<tr><td>'+w.EveLocations.markup(1000000000001,null,99)+'</td></tr>';
 await w.EveLocations.load();release({locations:{1000000000001:{name:'Personal place',status:'resolved'}}});await first;await tick();
 assert.equal(d.querySelector('[data-location-id]').textContent,'Corp place');assert(calls.some(s=>s.endsWith('&corporation_id=99')));
});
test('known names reuse cache, stay escaped and language changes translate only unavailable statuses',async t=>{
 const {dom,w,d}=setup();t.after(()=>w.close());let calls=0;
 w.api=async()=>{calls++;return {locations:{1000000000001:{status:'access'}}};};
 d.querySelector('#places').innerHTML='<tr><td>'+w.EveLocations.markup(60003760,'Station <script>fake</script>')+'</td><td>'+w.EveLocations.markup(1000000000001)+'</td></tr>';
 await w.EveLocations.load();await tick();assert.equal(calls,1);assert.equal(d.querySelector('script'),null);
 assert.equal(d.querySelector('[data-location-id="60003760"]').textContent,'Station <script>fake</script>');
 assert(d.querySelector('[data-location-id="1000000000001"]').textContent.includes('access required'));
 w.EveI18n.setLanguage('hu');assert(d.querySelector('[data-location-id="1000000000001"]').textContent.includes('hozzáférés szükséges'));
 assert.equal(d.querySelector('[data-location-id="60003760"]').textContent,'Station <script>fake</script>');
});
test('large location lists use bounded batches and failures never create retry loops',async t=>{
 const {dom,w,d}=setup();t.after(()=>w.close());const calls=[];
 w.api=async url=>{calls.push(url);const ids=new URL(url,w.location.href).searchParams.get('ids').split(',');return {locations:Object.fromEntries(ids.map(id=>[id,{name:'Place '+id,status:'resolved'}]))};};
 d.querySelector('#places').innerHTML=Array.from({length:201},(_,i)=>'<tr><td>'+w.EveLocations.markup(60000000+i)+'</td></tr>').join('');
 await w.EveLocations.load();await tick();assert.equal(calls.length,2);assert.equal(new URL(calls[0],w.location.href).searchParams.get('ids').split(',').length,200);
 d.querySelector('#places').innerHTML='<tr><td>'+w.EveLocations.markup(999)+'</td></tr>';let failures=0;w.api=async()=>{failures++;throw Error('offline');};
 await w.EveLocations.load();await w.EveLocations.load();await tick();assert.equal(failures,1);assert(d.body.textContent.includes('temporarily unavailable'));
});
test('an unresolved location polls until its name arrives without a view reload',async t=>{
 const {dom,w,d}=setup();t.after(()=>w.close());let loaded=false;
 w.api=async()=>({locations:{60003760:loaded?{name:'Resolved later',status:'resolved'}:{status:'pending'}}});
 d.querySelector('#places').innerHTML='<tr><td>'+w.EveLocations.markup(60003760)+'</td></tr>';
 await w.EveLocations.load();assert(d.body.textContent.includes('Loading location name'));
 loaded=true;const now=w.Date.now();w.Date.now=()=>now+2000;await w.EveLocations.load();
 assert.equal(d.querySelector('[data-location-id]').textContent,'Resolved later');
});
test('a late lookup before an inventory refresh cannot overwrite the new container destination',async t=>{
 const {dom,w,d}=setup();t.after(()=>w.close());let release;
 w.api=()=>new Promise(r=>release=r);d.querySelector('#places').innerHTML='<tr><td>'+w.EveLocations.markup(1000000000001)+'</td></tr>';
 const first=w.EveLocations.load();w.EveLocations.refresh();w.api=async()=>({locations:{1000000000001:{name:'New station',status:'resolved'}}});
 await w.EveLocations.load();release({locations:{1000000000001:{name:'Old station',status:'resolved'}}});await first;await tick();
 assert.equal(d.querySelector('[data-location-id]').textContent,'New station');
});
