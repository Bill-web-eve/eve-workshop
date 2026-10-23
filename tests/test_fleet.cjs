'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function fixture(){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[];
 const characters=[{id:11,name:'Alice'},{id:12,name:'Bob'}];
 const state={csrf:'test',version:'1.2.0',characters,corporations:[],production_characters:[],plans:[],jobs:[],settings:{source:'manual',character_ids:[],location_ids:[]},task:{running:false,results:[]},sde:{buildNumber:1},recipe_count:1,scope_label:'Personal'};
 const at=Date.now()/1000-1000,windows=[{system_id:1,name:'Alpha',start:at-900,end:at+900,kill_ids:[123],esi_samples:1}];
 const row={id:123,at,system_id:1,system:'Alpha',ship_id:590,ship:'Ship',value:1000,attackers:3,role:'kill',characters:[{id:11,name:'Alice',role:'kill'}]};
 const data={preferences:{tracking:true,interval_seconds:60,gap_minutes:45,padding_minutes:15,character_ids:null},characters:characters.map(c=>({...c,selected:true,location_access:true,complete:true,checked:at,next_check:at+3600,location_checked:at,system:'Alpha'})),sessions:[{id:'11:123',character_id:11,character_name:'Alice',first:at,last:at,start:at-900,end:at+900,kills:1,losses:0,esi_samples:1,visits:[{...windows[0],first:at,last:at}],windows,rows:[row],report:null}],kills:[row],status:{running:false,results:[],revision:0},location_status:{running:false}};
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 w.fetch=async(url,opts)=>{calls.push([url,opts?.body?JSON.parse(opts.body):null]);let value;
  if(url.startsWith('/api/state'))value=state;
  else if(url.startsWith('/api/fleet?')||url==='/api/fleet')value=data;
  else if(url==='/api/fleet/preferences'){data.preferences={...data.preferences,...JSON.parse(opts.body)};value=data.preferences;}
  else if(url==='/api/fleet/refresh')value={started:true};
  else if(url==='/api/notifications')value={items:[],counts:{data:0},task:{running:false},corporations:[],moons:[],preferences:{os_enabled:false,categories:{intel:false}}};
  else if(url==='/api/intel/alerts')value={enabled:false,items:[]};
  else if(url==='/api/activity')value={task:{},market:{},industry:{},intel:{},fleet:{task:data.status,location:data.location_status}};
  else throw Error('Unexpected request '+url);
  return {ok:true,json:async()=>value};
 };
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();run('navigate("fleet")');await tick();await tick();return {w,d,run,calls,data};
}
test('fleet page is independent of the current plan, translated, and can open system windows',async t=>{
 const {w,d,run,calls}=await fixture();t.after(()=>w.close());
 assert(d.querySelector('.plan-selector').hidden);assert.equal(d.querySelector('#fleet-character').options[0].textContent,'All characters');
 assert(!calls.some(c=>c[0].startsWith('/api/plan')));
 d.querySelector('[data-fleet-session]').click();await tick();await tick();
 assert(d.querySelector('#fleet-session'));assert.match(d.querySelector('#fleet-session').textContent,/Alpha/);assert.match(d.querySelector('#fleet-session').textContent,/Surrounding battle data|surrounding battle data/);
 const text=d.querySelector('#view-content').textContent;
 assert(!/[áéíóöőúüű]/i.test(text),text);
 assert(d.querySelector('a[href="https://zkillboard.com/kill/123/"]'));
 assert.match(d.querySelector('.fleet-route').textContent,/Alpha/);
});
test('per-character refresh and related report actions use the intended scopes',async t=>{
 const {w,d,calls}=await fixture();t.after(()=>w.close());
 const select=d.querySelector('#fleet-character');select.value='11';select.dispatchEvent(new w.Event('change'));
 d.querySelector('#fleet-refresh').click();await tick();await tick();
 assert.deepEqual(calls.find(c=>c[0]==='/api/fleet/refresh')[1],{character_id:11});
 d.querySelector('[data-fleet-session]').click();d.querySelector('#fleet-context').click();await tick();await tick();
 assert.deepEqual(calls.filter(c=>c[0]==='/api/fleet/refresh').at(-1)[1],{session_id:'11:123'});
});
test('tracking settings allow a one-minute interval and do not alter inventory or intel settings',async t=>{
 const {w,d,calls}=await fixture();t.after(()=>w.close());
 const form=d.querySelector('#fleet-settings');form.elements.interval_seconds.value='60';form.elements.tracking.checked=false;
 form.dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();await tick();
 const body=calls.find(c=>c[0]==='/api/fleet/preferences')[1];assert.equal(body.interval_seconds,60);assert.equal(body.tracking,false);assert.deepEqual(body.character_ids,[11,12]);
 assert(!calls.some(c=>c[0]==='/api/settings'||c[0]==='/api/intel/preferences'));
});
test('visible progress includes current system and page; incomplete reports remain explicit',async t=>{
 const {w,d,run,data}=await fixture();t.after(()=>w.close());
 data.status={running:true,kind:'report',total:3,completed:1,subject:'Alpha',page:2,results:[]};run('render()');
 assert(d.querySelector('progress'));assert(d.querySelector('#fleet-refresh').disabled);assert.match(d.querySelector('#view-content [role=status]').textContent,/Alpha/);
 data.status.running=false;data.status.results=[{ok:true,partial:true}];run('render()');await tick();assert.match(d.querySelector('#view-content .banner.warn').textContent,/partial/);
});

test('successful related report labels are English and periodic local reads stay quiet',async t=>{
 const {w,d,run,data}=await fixture();t.after(()=>w.close());
 data.sessions[0].report={checked:Date.now()/1000,data:{results:[],windows:data.sessions[0].windows}};
 d.querySelector('[data-fleet-session]').click();await tick();
 assert.match(d.querySelector('#fleet-session').textContent,/Related report checked:/);
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#fleet-session').textContent));
 d.querySelector('details').open=true;await run('loadFleet(true)');
 assert(d.querySelector('details').open);
});

test('session summary shows full ISK, own involvement, losses and partial coverage',async t=>{
 const {w,d,run,data}=await fixture();t.after(()=>w.close());
 data.sessions[0].value_summary={total:{count:3,cents:'20000',missing:0,destroyed_cents:'15000',destroyed_missing:0},participation:{count:1,cents:'10025',missing:0,destroyed_cents:'7010',destroyed_missing:0},losses:{count:1,cents:'5025',missing:0,destroyed_cents:'4000',destroyed_missing:0},participation_percent:'50.13'};
 d.querySelector('[data-fleet-session]').click();await tick();
 const total=d.querySelector('[data-fleet-value=total]'),part=d.querySelector('[data-fleet-value=participation]');
 assert.match(total.textContent,/200,00 ISK/);assert.match(total.textContent,/150,00 ISK/);assert.match(part.textContent,/100,25 ISK/);assert.match(part.textContent,/50.13%/);
 assert.match(d.querySelector('[data-fleet-value=losses]').textContent,/50,25 ISK/);assert.match(d.querySelector('#fleet-session').textContent,/still a subtotal/);
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#fleet-session').textContent));
 data.sessions[0].value_summary.total.missing=1;data.sessions[0].value_summary.participation.destroyed_missing=1;run('render()');await tick();
 assert.match(d.querySelector('#fleet-session').textContent,/Some killmail values are missing/);
});
test('killmail links are ship icons in session and combined kill lists',async t=>{
 const {w,d}=await fixture();t.after(()=>w.close());
 d.querySelector('[data-fleet-session]').click();await tick();
 let a=d.querySelector('a[href="https://zkillboard.com/kill/123/"]');
 assert.equal(a.textContent,'');assert.equal(a.querySelector('img').getAttribute('src'),'https://images.evetech.net/types/590/icon?size=64');assert.match(a.getAttribute('aria-label'),/Open killmail on zKillboard/);
 d.querySelector('[data-fleet-tab=kills]').click();await tick();
 a=d.querySelector('a[href="https://zkillboard.com/kill/123/"]');assert(a.querySelector('img'));assert.equal(a.getAttribute('target'),'_blank');
});
