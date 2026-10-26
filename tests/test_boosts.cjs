'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function setup(){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[];
 const types=[[42694,'Active Shielding Charge','Shield'],[42695,'Shield Harmonizing Charge','Shield'],[42696,'Shield Extension Charge','Shield'],[42838,'Evasive Maneuvers Charge','Skirmish'],[42839,'Interdiction Maneuvers Charge','Skirmish'],[42840,'Rapid Deployment Charge','Skirmish'],[42835,'Sensor Optimization Charge','Information'],[42836,'Electronic Superiority Charge','Information'],[42837,'Electronic Hardening Charge','Information']];
 const state={csrf:'test',version:'1.5.0',characters:[],corporations:[],production_characters:[],plans:[],jobs:[],settings:{source:'manual'},task:{running:false},sde:{buildNumber:1},recipe_count:1};
 let data={running:false,folder:'/logs',channel:'',started:null,stopped:null,checked:null,providers:[],rows:types.map(([id,name,group])=>({id,name,group,count:0,providers:[]})),file_errors:0,error:null};
 const copy=()=>{data.copy_text=data.rows.map(r=>r.name+'\t'+r.count+(r.providers.length?'\t'+r.providers.join(', '):'')).join('\n');};copy();
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;let clipboard='',pending=null;
 Object.defineProperty(w.navigator,'clipboard',{value:{writeText:async text=>{clipboard=text;}}});
 w.fetch=async(url,opts)=>{const body=opts?.body?JSON.parse(opts.body):null;calls.push({url,body});let result;
  if(url==='/api/state')result=state;
  else if(url==='/api/intel/alerts')result={enabled:false,items:[]};
  else if(url==='/api/notifications')result={items:[],counts:{data:0},task:state.task,moons:[],corporations:[],preferences:{os_enabled:false,categories:{intel:false}}};
  else if(url==='/api/boosts'){if(pending){const p=pending;pending=null;return p;}result=data;}
  else if(url.startsWith('/api/boosts/channels'))result={channels:['I. Boost V','I. Boost X2']};
  else if(url==='/api/boosts/start'){data={...data,folder:body.folder,channel:body.channel,running:true,started:100,checked:100};result=data;}
  else if(url==='/api/boosts/stop'){data={...data,running:false,stopped:200};result=data;}
  else throw Error('Unexpected '+url);
  return {ok:true,json:async()=>JSON.parse(JSON.stringify(result))};
 };
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();run('navigate("boosts")');for(let i=0;i<5;i++)await tick();
 return {w,d,run,calls,data:()=>data,setData:newData=>{data=newData;copy();},clipboard:()=>clipboard,setPending:p=>pending=p};
}
test('Boost view is independent of plans and displays all nine game icons and translated zero state',async t=>{
 const f=await setup();t.after(()=>f.w.close());const {d}=f;
 assert(d.querySelector('.plan-selector').hidden);assert.equal(d.querySelector('#page-title').textContent,'Boost counter');
 assert.equal(d.querySelectorAll('.boost-card').length,9);assert.equal(d.querySelectorAll('.boost-badge').length,0);
 assert.equal(d.querySelectorAll('img[src^="https://images.evetech.net/types/"]').length,9);
 assert.equal(d.querySelector('#boost-form').elements.channel.options.length,3);
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#boost-view').textContent));
 assert(!f.calls.some(c=>c.url.startsWith('/api/plan')));
});
test('start uses the selected channel, polling updates badges and copy includes all nine names with zeros',async t=>{
 const f=await setup();t.after(()=>f.w.close());const {w,d,run}=f,form=d.querySelector('#boost-form');
 form.elements.channel.value='I. Boost X2';form.elements.channel.dispatchEvent(new w.Event('input',{bubbles:true}));
 form.dispatchEvent(new w.Event('submit',{cancelable:true}));for(let i=0;i<4;i++)await tick();
 assert.deepEqual(f.calls.find(c=>c.url==='/api/boosts/start').body,{folder:'/logs',channel:'I. Boost X2'});assert(form.elements.channel.disabled);assert(!d.querySelector('#boost-stop').disabled);
 const data=JSON.parse(JSON.stringify(f.data()));data.rows[0].count=2;data.rows[0].providers=['Pilot A','Pilot B'];data.providers=[{name:'Pilot A',charges:[42694],at:100},{name:'Pilot B',charges:[42694],at:101}];f.setData(data);
 await run('loadBoosts()');await tick();assert.equal(d.querySelectorAll('.boost-badge').length,1);assert.equal(d.querySelector('.boost-badge').textContent,'2');assert(d.querySelector('#boost-providers').textContent.includes('Pilot B'));
 d.querySelector('#boost-copy').click();await tick();assert.equal(f.clipboard().split('\n').length,9);assert(f.clipboard().startsWith('Active Shielding Charge\t2\tPilot A, Pilot B\n'));assert(f.clipboard().includes('Electronic Hardening Charge\t0'));
 d.querySelector('#boost-stop').click();for(let i=0;i<3;i++)await tick();assert(!form.elements.channel.disabled);assert(d.querySelector('#boost-stop').disabled);
});
test('polling preserves an edited folder and the view refreshes again after leaving and returning',async t=>{
 const f=await setup();t.after(()=>f.w.close());const {d,w,run}=f,form=d.querySelector('#boost-form');
 form.elements.folder.value='/new logs';form.elements.folder.dispatchEvent(new w.Event('input',{bubbles:true}));
 await run('loadBoosts()');assert.equal(form.elements.folder.value,'/new logs');
 run('navigate("jobs")');await tick();run('navigate("boosts")');await tick();await run('loadBoosts()');assert.equal(d.querySelector('#boost-form').elements.folder.value,'/new logs');
});
test('a late polling response cannot reactivate a stopped counter',async t=>{
 const f=await setup();t.after(()=>f.w.close());const {w,d,run}=f;let resolve;
 f.setPending(new Promise(r=>{resolve=r;}));const loading=run('loadBoosts()');await tick();
 d.querySelector('#boost-stop').disabled=false;d.querySelector('#boost-stop').click();await tick();
 resolve({ok:true,json:async()=>({...f.data(),running:true})});await loading;await tick();
 assert(d.querySelector('#boost-status').textContent.includes('stopped'));
});
