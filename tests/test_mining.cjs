'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
function bucket(n){return {quantity:n,volume:n*10,unknown_volume:0,records:1,raw:[{id:1,name:'Sylvite',quantity:n}],materials:[{id:34,name:'Tritanium',quantity:n*9/100}],unrefinable:0};}
const fixture={characters:[{id:11,name:'Alice',needs_auth:false,checked_at:1792497600,expires:9999999999},{id:22,name:'Bob',needs_auth:false,checked_at:1792497600,expires:9999999999}],ores:[{id:1,name:'Sylvite'}],start:'2026-09-21',end:'2026-10-20',summary:bucket(300),by_character:[{id:11,name:'Alice',...bucket(100)},{id:22,name:'Bob',...bucket(200)}],by_ore:[{id:1,name:'Sylvite',...bucket(300)}],by_day:[{date:'2026-10-20',...bucket(300)}],records:[{date:'2026-10-20',character_id:11,character_name:'Alice',solar_system_id:30000142,system_name:'Jita',type_id:1,name:'Sylvite',quantity:300,volume:3000}],refining_yield:.906281,implant:4};
async function setup(data=fixture){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 const state={csrf:'test',version:'1.0.0',corporations:[],plans:[],production_characters:[],characters:data.characters.map(c=>({id:c.id,name:c.name})),jobs:[],settings:{source:'eve'},task:{running:false},sde:{buildNumber:1},recipe_count:1,delivery_wait:null};
 const notifications={items:[],counts:{skills:0,jobs:0,pi:0,moons:0,data:0},task:{running:false},next_sync_at:9999999999,corporations:[],moons:[],preferences:{os_enabled:false,auto_refresh:false,personal:true,corporations:true,moon_days:3,categories:{skills:true,jobs:true,pi:true,moons:true},moon_owners:{}},claims:[]};
 const calls=[];w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 w.fetch=async(url,options)=>{
  calls.push(url);let value;
  if(url==='/api/state')value=state;
  else if(url==='/api/intel/alerts')value={enabled:false,items:[]};
  else if(url.startsWith('/api/notifications'))value=notifications;
  else if(url.startsWith('/api/mining?'))value=data;
  else if(url.startsWith('/api/prices?'))value={quotes:{1:{buy:'10',sell:'14',checked:1792497600,stale:false},34:{buy:'2',sell:'4',checked:1792497600,stale:false}},running:false,errors:{},retry_after:{}};
  else throw Error('Unexpected request '+url);
  return {ok:true,json:async()=>structuredClone(value)};
 };
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();run('navigate("mining")');await tick();await tick();await tick();
 return {dom,w,d,run,calls};
}
test('mining menu, totals, raw/refined values and Jita modes work without any residue UI',async t=>{
 const {w,d,run}=await setup();t.after(()=>w.close());
 assert(d.querySelector('[data-view=mining]').classList.contains('active'));assert(d.querySelector('.plan-selector').hidden);
 assert.equal(d.querySelector('#page-title').textContent,'Mining ledger');
 assert.equal(d.querySelector('[data-mining-value=summary][data-mining-basis=raw]').textContent,'4 200,00 ISK');
 assert.equal(d.querySelector('[data-mining-value=summary][data-mining-basis=refined]').textContent,'108,00 ISK');
 const mode=d.querySelector('[data-jita-mode]');mode.value='buy';mode.dispatchEvent(new w.Event('change'));
 assert.equal(d.querySelector('[data-mining-value=summary][data-mining-basis=raw]').textContent,'3 000,00 ISK');
 assert.equal(d.querySelector('[data-mining-value=summary][data-mining-basis=refined]').textContent,'54,00 ISK');
 mode.value='split';mode.dispatchEvent(new w.Event('change'));
 assert.equal(d.querySelector('[data-mining-value=summary][data-mining-basis=raw]').textContent,'3 600,00 ISK');
 assert.equal(d.querySelector('[data-mining-value=summary][data-mining-basis=refined]').textContent,'81,00 ISK');
 assert(!/residue|waste/i.test(d.body.textContent));
 for(const tab of ['ores','days','records']){d.querySelector('[data-mining-tab='+tab+']').click();await tick();assert(d.querySelector('.mining-'+(tab==='records'?'records':tab)));}
 assert.equal(d.querySelector('[data-mining-tab=records]').getAttribute('aria-pressed'),'true');
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#view-content').textContent),d.querySelector('#view-content').textContent);
 w.EveI18n.setLanguage('hu');await tick();assert.equal(d.querySelector('#page-title').textContent,'Bányászati napló');
 w.EveI18n.setLanguage('en');await tick();assert.equal(d.querySelector('#page-title').textContent,'Mining ledger');
});
test('character, ore and date filters go into the API query and refined mode changes the main valuation',async t=>{
 const {w,d,calls}=await setup();t.after(()=>w.close());
 const form=d.querySelector('#mining-filters');form.elements.character.value='11';form.elements.ore.value='1';form.elements.period.value='7';form.elements.basis.value='refined';
 form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();
 const query=new URL(calls.filter(u=>u.startsWith('/api/mining?')).at(-1),'http://localhost').searchParams;
 assert.equal(query.get('character_id'),'11');assert.equal(query.get('ore_id'),'1');assert(query.has('start'));assert(query.has('end'));
 assert(d.querySelector('.cost-summary h2').textContent.includes('Refined material'));
 assert.equal(d.querySelector('[data-cost-grand]').textContent,'108,00 ISK');
 d.querySelector('#mining-filters').elements.period.value='custom';d.querySelector('#mining-filters').elements.period.dispatchEvent(new w.Event('change'));await tick();
 assert(d.querySelector('[name=start]'));assert(d.querySelector('[name=end]'));
});
test('missing access and missing prices are marked incomplete rather than presented as a complete total',async t=>{
 const data=structuredClone(fixture);data.characters[0].needs_auth=true;data.summary.raw.push({id:999,name:'Unknown ore',quantity:10});
 const {w,d}=await setup(data);t.after(()=>w.close());
 assert(d.querySelector('[data-open-settings=access]'));assert(d.querySelector('.banner.warn').textContent.includes('totals may be incomplete'));
 assert(d.querySelector('[data-cost-warning]').textContent.includes('subtotal'));
 assert(d.querySelector('[data-mining-value=summary][data-mining-basis=raw]').textContent.startsWith('≥ '));
});
