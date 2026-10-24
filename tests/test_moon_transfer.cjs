'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),tick=()=>new Promise(r=>setImmediate(r));
function setup(){
 const dom=new JSDOM('<div id="moon-transfer"></div>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext());w.Blob=Blob;
 run(`const $=s=>document.querySelector(s),esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),verbatim=esc,itemName=esc,fmt=String,moonPercent=n=>n+'%';const panel=(title,sub,body)=>'<section><h2>'+title+'</h2>'+body+'</section>';const moonTable=(headers,rows)=>'<table><tbody>'+rows.join('')+'</tbody></table>';let moonEditing=false,dirty={},refreshed=0;const refreshMoons=async()=>{refreshed++},toast=()=>{},error=()=>{};`);
 for(const name of ['i18n-en.js','i18n.js','costs.js','moon-transfer.js'])run(fs.readFileSync(__dirname+'/../static/'+name,'utf8'));
 return {dom,w,d:w.document,run};
}
const preview={revision:'first',counts:{new:2,update:0,skip:0},rows:[{moon_id:1,name:'<img src=x onerror=alert(1)>',structure:'Metenox',action:'new',percent_total:100,ores:[{name:'Coesite',percent:100}],rent_isk:'100',other_cost_isk:'0',warnings:[]}]};
test('bulk import has a non-writing preview and requires the separate apply button',async t=>{
 const {dom,w,d,run}=setup();t.after(()=>w.close());const calls=[];
 w.api=async(path,body)=>{calls.push([path,body]);return path.endsWith('/preview')?preview:{ok:true,counts:preview.counts};};
 run('openMoonTransfer()');const text=d.querySelector('[name=text]');text.value='two moon survey blocks';text.dispatchEvent(new w.Event('input',{bubbles:true}));
 d.querySelector('#moon-import-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();
 assert.equal(calls.length,1);assert.equal(calls[0][0],'/api/moons/import/preview');assert.equal(calls[0][1].existing,'skip');
 assert.equal(d.querySelector('#moon-import-result img'),null);assert.match(d.querySelector('#moon-import-result').textContent,/<img src=x/);
 assert.equal(d.querySelector('#moon-import-apply').disabled,false);d.querySelector('#moon-import-apply').click();await tick();
 assert.equal(calls[1][0],'/api/moons/import');assert.equal(calls[1][1].revision,'first');assert.equal(run('refreshed'),1);assert.equal(run('moonTransferDraft'),null);assert.equal(run('dirty.moon_import'),undefined);
});
test('changing import options invalidates the old preview and English preserves the pasted content',async t=>{
 const {w,d,run}=setup();t.after(()=>w.close());w.api=async()=>preview;
 run(`openMoonTransfer();`);let text=d.querySelector('[name=text]');text.value='literal </textarea><script>data only</script>';text.dispatchEvent(new w.Event('input',{bubbles:true}));
 d.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();
 d.querySelector('[name=existing]').value='update';d.querySelector('[name=existing]').dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.equal(d.querySelector('#moon-import-apply').disabled,true);
 run(`EveI18n.setLanguage('en');EveI18n.translate(document.documentElement);`);
 assert.match(d.body.textContent,/Bulk moon import/);assert(!/[áéíóöőúüű]/i.test(d.body.textContent.replace(d.querySelector('[name=text]').textContent,'')));
 assert.match(d.querySelector('[name=text]').placeholder,/Paste the complete in-game survey table/);
 assert.equal(d.querySelector('[name=text]').value,'literal </textarea><script>data only</script>');assert.equal(d.querySelector('script'),null);
 assert.match(run(`EveI18n.t('Hibás scansor: 7 · Ismételt érc ugyanannál a holdnál.')`),/Invalid scan row: 7.*Duplicate ore/);
});
test('a bulk JSON file loads without applying it and stale preview errors preserve the draft',async t=>{
 const {w,d,run}=setup();t.after(()=>w.close());const calls=[];w.api=async(path,body)=>{calls.push(path);if(path.endsWith('/preview'))return preview;throw Error('The moon register has changed; request a new import preview.');};
 run('openMoonTransfer()');const file=d.querySelector('#moon-import-file');Object.defineProperty(file,'files',{value:[{name:'moons.json',size:100,text:async()=>'{"moons":[{},{}]}'}]});file.dispatchEvent(new w.Event('change',{bubbles:true}));await tick();
 assert.match(d.querySelector('form').textContent,/moons.json/);assert.equal(calls.length,0);assert.equal(d.querySelector('[name=format]').value,'json');assert.equal(d.querySelector('[name=text]').value,'{"moons":[{},{}]}');
 d.querySelector('form').dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();d.querySelector('#moon-import-apply').click();await tick();
 assert.match(d.querySelector('#moon-import-status').textContent,/register has changed/);assert.equal(d.querySelector('#moon-import-apply').disabled,true);assert.notEqual(run('moonTransferDraft'),null);assert.equal(run('refreshed'),0);
});
test('export uses all backend moons and the existing native save bridge',async t=>{
 const {w,run}=setup();t.after(()=>w.close());const calls=[],saved=[];w.api=async p=>{calls.push(p);return {format:'eve-workshop-moons',version:1,moons:[{moon_id:1},{moon_id:2}]};};
 w.EveDesktop={active:true,saveBlob:async(blob,name)=>saved.push([await blob.text(),name])};
 await run('exportMoons({disabled:false})');assert.deepEqual(calls,['/api/moons/export']);assert.equal(JSON.parse(saved[0][0]).moons.length,2);assert.match(saved[0][1],/^eve-moons-.*\.json$/);
});
