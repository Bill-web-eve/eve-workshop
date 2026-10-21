'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static');
function page(){
 const dom=new JSDOM('<main></main>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window;
 const run=s=>vm.runInContext(s,dom.getInternalVMContext());
 w.$=s=>w.document.querySelector(s);w.$$=s=>Array.from(w.document.querySelectorAll(s));
 w.esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');w.verbatim=w.esc;
 w.fmt=String;w.panel=(title,sub,html)=>`<section><h2>${w.esc(title)}</h2><p>${sub}</p>${html}</section>`;
 w.moonTable=(heads,rows)=>`<table><thead><tr>${heads.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table>`;
 for(const name of ['i18n-en.js','i18n.js','extractions.js'])run(fs.readFileSync(path.join(root,name),'utf8'));
 return {w,run};
}
test('calendar-only timing is informative, with no missing-extraction warning',async t=>{
 const {w}=page();t.after(()=>w.close());
 await new Promise(setImmediate);
 const data={moons:[{enabled:true,structure:'Athanor',extraction_status:'calendar_only',name:'RP2-OQ VI - Moon 7'}]};
 w.document.querySelector('main').innerHTML=w.moonWarnings(data);
 assert.equal(w.document.querySelector('.warn'),null);
 assert.match(w.document.querySelector('main').textContent,/ESI-naptárból ismert/);
 w.EveI18n.setLanguage('en');
 assert.match(w.document.querySelector('main').textContent,/Extraction time known from the ESI calendar:/);
 assert.match(w.document.querySelector('main').textContent,/RP2-OQ VI - Moon 7/);
 assert.match(w.document.querySelector('main').textContent,/may not provide ore quantities or fracture time/);
});
test('calendar renders ESI time and details without inventing ore volume',async t=>{
 const {w,run}=page();t.after(()=>w.close());
 await new Promise(setImmediate);
 w.moonData={extractions:{events:[{id:'calendar:1',moon_record_id:'registered',moon_name:'RP2-OQ VI - Moon 7',date:'2026-10-22T14:31:00Z',timing_source:'esi_calendar',kind:'calendar',volume:null,ores:[],volume_source:'unknown',composition_source:'unknown',stale:false}]}};
 run("moonCalendarMonth='2026-10';renderMoonCalendar(document.querySelector('main'),[{id:'registered',structure:'Athanor'}]);");
 assert.equal(w.document.querySelectorAll('.moon-calendar-event').length,1);
 assert.match(w.document.querySelector('.moon-calendar-event').textContent,/14:31/);
 assert.equal(w.document.querySelector('.moon-calendar-event small').textContent,'– m³');
 assert.match(w.document.querySelector('tbody').textContent,/ESI naptár · kitermelési időpont/);
 w.document.querySelector('[data-calendar-event]').click();
 assert.match(w.document.querySelector('#extraction-details').textContent,/ESI-azonosítója alapján/);
 assert.match(w.document.querySelector('#extraction-details').textContent,/nem ad ércmennyiséget/);
 w.EveI18n.setLanguage('en');
 assert.match(w.document.querySelector('tbody').textContent,/ESI calendar · extraction time/);
 assert.match(w.document.querySelector('#extraction-details').textContent,/matched using its ESI ID/);
 assert.match(w.document.querySelector('#extraction-details').textContent,/does not provide ore quantities/);
});
