const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),graph=require('../static/schedule-graph.js');
const j=(id,activity,start,end,dependencies=[])=>({id,activity,start,end,name:'Item '+id,product_id:id,character_id:1,character_name:'Pilot <one>',slot:1,runs:1,output:1,materials_ready:start,materials:[],dependencies,blueprint_kind:'BPO',blueprint_item_id:id,me:0,te:0});
const fixture=()=>({start:1000,partial_finish:1400,finish:1400,seconds:400,complete:true,runs:3,assumptions:[],supply_at:1000,workers:[],blueprint_shortages:[],blocked:[],material_warnings:[],material_shortfall:[],jobs:[j(1,'reaction',1000,1200),j(2,'manufacturing',1000,1100),j(3,'manufacturing',1200,1400,[{job_id:1,material_id:1,quantity:1},{job_id:2,material_id:2,quantity:1}])]});
test('same character reaction and manufacturing use distinct lanes and the same time axis',()=>{
 const g=graph.build(fixture(),0),[a,b,c]=g.nodes;
 assert.equal(g.lanes.length,2);assert.equal(a.x,b.x);assert.notEqual(a.y,b.y);assert.equal(b.y,c.y);
 assert.equal(a.x+a.width,c.x);assert.equal(c.start,1200);assert.equal(c.dependencies.length,2);
});
test('pagination bounds nodes while keeping global scale and IDs',()=>{
 const data=fixture();data.jobs=Array.from({length:10000},(_,i)=>j(i+1,i%2?'reaction':'manufacturing',1000+i,1001+i));data.partial_finish=11000;
 const g=graph.build(data,500),first=graph.build(data,0);
 assert.equal(g.nodes.length,100);assert.equal(g.pages,100);assert.equal(g.page,99);assert.equal(g.nodes[0].id,9901);assert.equal(g.end,first.end);assert.equal(g.start,first.start);
 data.jobs.forEach((j,i)=>{j.character_id=i%2+1;});const filtered=graph.build(data,80,2);assert.equal(filtered.pages,50);assert.equal(filtered.page,49);assert.equal(filtered.nodes.length,100);assert(filtered.nodes.every(j=>j.character_id===2));assert.equal(filtered.end,first.end);assert.equal(filtered.start,first.start);
 const empty=graph.build({...data,jobs:[],partial_finish:1000});assert.equal(empty.pages,1);assert.equal(empty.nodes.length,0);assert(empty.height>=120);
});
async function setup(data,preference){
 const dom=new JSDOM('<html lang="hu"><body><main></main></body></html>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),ctx=dom.getInternalVMContext(),run=s=>vm.runInContext(s,ctx);
 dom.window.fixture=data;
 if(preference!==undefined)dom.window.localStorage.setItem('eve-muhely-schedule-timeline',preference);
 run(`const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),verbatim=v=>'<span data-i18n-skip>'+esc(v)+'</span>',itemName=verbatim,fmt=String,date=String,hours=String;
 const panel=(title,sub,body)=>'<section><h2>'+title+'</h2><small>'+sub+'</small>'+body+'</section>',table=(h,r,cls='')=>'<table class="'+cls+'"><thead><tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>'+r.join('')+'</tbody></table>';`);
 for(const f of ['i18n-en.js','i18n.js','graph.js','schedule-graph.js','schedule.js'])run(fs.readFileSync(__dirname+'/../static/'+f,'utf8'));
 await new Promise(r=>setImmediate(r));run(`renderScheduleResult($('main'),fixture);`);await new Promise(r=>setImmediate(r));
 return {dom,d:dom.window.document,run};
}
test('separate activity tables, keyboard selection, material details and translation work',async()=>{
 const data=fixture();data.blueprint_shortages=[{name:'Example Blueprint',category:'BPC-run',copies:1,runs:2,copy_runs:2}];data.jobs[2].materials=[{id:1,name:'Raw <ore>',quantity:1,allocations:[{source:'job',job_id:1,quantity:1,available_at:1200}]}];
 const {dom,d}=await setup(data);
 assert.equal(d.querySelectorAll('table.schedule-reaction tbody tr').length,1);assert.equal(d.querySelectorAll('table.schedule-manufacturing tbody tr').length,2);
 assert(d.body.textContent.includes('Example Blueprint'));assert.equal(d.querySelector('script'),null);assert(d.querySelector('.schedule-lane').textContent.includes('Pilot <one>'));
 d.querySelector('g[data-schedule-select="3"]').dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
 assert.equal(d.querySelectorAll('.schedule-link,marker,.schedule-flow').length,0);assert(!d.body.textContent.includes('Sz'+'ámítási feltételek'));assert(!d.body.textContent.includes('Full production dependency chain'));assert.match(d.querySelector('#schedule-job-detail').textContent,/Raw <ore>/);
 d.querySelector('#schedule-job-detail button[data-schedule-select="1"]').click();assert(d.querySelector('g[data-schedule-select="1"]').classList.contains('selected'));
 assert(d.querySelector('#schedule-job-detail button[data-schedule-select="3"]'));
 dom.window.EveI18n.setLanguage('en');await new Promise(r=>setImmediate(r));
 assert(d.body.textContent.includes('Reaction schedule'));assert(d.body.textContent.includes('Manufacturing schedule'));assert(d.body.textContent.includes('Jobs consuming this output'));
 const texts=[...d.querySelectorAll('h2,h3,p,th,tspan,.schedule-legend')].filter(e=>!e.closest('[data-i18n-skip]')).map(e=>e.textContent);
 assert.equal(texts.filter(s=>/[áéíóöőúüű]/i.test(s)).join('\n'),'');
 dom.window.EveI18n.setLanguage('hu');await new Promise(r=>setImmediate(r));assert(d.body.textContent.includes('Reakciók ütemterve'));dom.window.close();
});
test('off-page dependency selection opens its graph page without mixing activity pagination',async()=>{
 const data=fixture();data.jobs=Array.from({length:101},(_,i)=>j(i+1,'reaction',1000+i,1001+i));
 data.jobs.push({...j(102,'manufacturing',1300,1400),character_id:2,character_name:'Pilot two'});
 data.jobs[100].materials=[{id:1,name:'Material',quantity:1,allocations:[{source:'job',job_id:102,quantity:1,available_at:1001}]}];
 const {dom,d}=await setup(data);
 const choose=id=>{const field=d.querySelector('#schedule-character-filter');field.value=String(id);field.dispatchEvent(new dom.window.Event('change',{bubbles:true}));};
 assert.equal(d.querySelector('#schedule-character-filter').options.length,3);choose(2);assert.equal(d.querySelectorAll('.schedule-job').length,1);assert(d.querySelector('g[data-schedule-select="102"]'));assert(d.querySelector('#schedule-graph-next').disabled);
 choose(1);assert.equal(d.querySelectorAll('.schedule-job').length,100);assert.equal(d.querySelectorAll('table.schedule-manufacturing tbody tr').length,1);
 d.querySelector('#schedule-graph-next').click();assert(d.querySelector('g[data-schedule-select="101"]'));
 d.querySelector('g[data-schedule-select="101"]').dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true}));assert(d.querySelector('#schedule-job-detail button[data-schedule-select="102"]'));
 d.querySelector('#schedule-job-detail button[data-schedule-select="102"]').click();assert(d.querySelector('g[data-schedule-select="102"].selected'));
 assert.equal(d.querySelector('#schedule-character-filter').value,'2');assert.equal(d.querySelectorAll('.schedule-job').length,1);
 choose('');assert.equal(d.querySelector('#schedule-character-filter').value,'');
 assert.equal(d.querySelectorAll('table.schedule-reaction tbody tr').length,100);
 d.querySelector('[data-schedule-table-page="1"][data-activity="reaction"]').click();assert.equal(d.querySelectorAll('table.schedule-reaction tbody tr').length,1);assert.equal(d.querySelectorAll('.schedule-job').length,100);
 dom.window.EveI18n.setLanguage('en');await new Promise(r=>setImmediate(r));assert.equal(d.querySelector('#schedule-character-filter option[value=""]').textContent,'All characters');assert.equal(d.querySelector('#schedule-character-filter option[value="2"]').textContent,'Pilot two');dom.window.close();
});

test('day windows clip crossing jobs, exclude exact boundaries and clamp periods',()=>{
 const day=graph.DAY,data=fixture();data.partial_finish=data.start+4*day;
 data.jobs=[j(1,'reaction',data.start,data.start+day),j(2,'manufacturing',data.start+day,data.start+2*day),j(3,'reaction',data.start+day/2,data.start+3*day)];
 const first=graph.build(data,0,null,{days:1,window:0}),second=graph.build(data,0,null,{days:1,window:1});
 assert.deepEqual(first.nodes.map(n=>n.id),[1,3]);assert.deepEqual(second.nodes.map(n=>n.id),[2,3]);assert.equal(first.end,second.start);
 const crossing=second.nodes.find(n=>n.id===3);assert(crossing.continues_before&&crossing.continues_after);assert.equal(crossing.start,data.jobs[2].start);assert.equal(crossing.end,data.jobs[2].end);assert.equal(crossing.x,second.left);assert.equal(crossing.x+crossing.width,second.width-30);
 assert.equal(graph.range(data,{days:1,window:999}).window,3);assert.equal(graph.range(data,{days:1,window:-1}).window,0);
 assert.equal(graph.range(data,{days:null,window:999}).windows,1);assert.equal(graph.range(data,{days:null}).end,data.partial_finish);
 for(const value of [0,-1,1.5,3651,NaN,Infinity,'7',true,undefined])assert(!graph.validDays(value));
 for(const value of [null,1,7,3650])assert(graph.validDays(value));
 assert.equal(graph.build(data,0,null,{days:1,window:3}).nodes.length,0);
});
test('time filtering precedes pagination and keeps the same axis across characters',()=>{
 const day=graph.DAY,data=fixture();data.partial_finish=data.start+3*day;
 data.jobs=Array.from({length:300},(_,i)=>({...j(i+1,'reaction',data.start+(i<150?0:day)+i,data.start+(i<150?0:day)+i+1),character_id:i%2+1}));
 const g=graph.build(data,1,null,{days:1,window:1}),pilot=graph.build(data,0,2,{days:1,window:1});
 assert.equal(g.total_jobs,150);assert.equal(g.pages,2);assert.equal(g.nodes.length,50);assert.equal(g.nodes[0].id,251);
 assert.equal(pilot.total_jobs,75);assert(pilot.nodes.every(j=>j.character_id===2));assert.equal(pilot.start,g.start);assert.equal(pilot.end,g.end);
});
test('day controls navigate, select distant jobs, validate input and persist the display preference',async()=>{
 const day=graph.DAY,data=fixture(),start=data.start;
 data.partial_finish=start+12*day;data.jobs=[j(1,'reaction',start+3600,start+7200),j(2,'manufacturing',start+day+3600,start+day+7200),j(3,'reaction',start+3*day,start+5*day),{...j(4,'manufacturing',start+11*day,start+12*day),character_id:2,character_name:'Pilot two'}];
 const {dom,d,run}=await setup(data),change=value=>{const field=d.querySelector('#schedule-timeline-days');field.value=value;field.dispatchEvent(new dom.window.Event('input',{bubbles:true}));field.dispatchEvent(new dom.window.Event('change',{bubbles:true}));};
 assert.equal(d.querySelector('#schedule-timeline-days').value,'7');assert.equal(d.querySelectorAll('.schedule-job').length,3);assert(!d.querySelector('g[data-schedule-select="4"]'));
 change('1');assert.equal(d.querySelectorAll('.schedule-job').length,1);assert(d.querySelector('#schedule-window-prev').disabled);
 const wholeJob=JSON.stringify(data.jobs);assert.equal(JSON.parse(dom.window.localStorage.getItem('eve-muhely-schedule-timeline')).days,1);
 d.querySelector('#schedule-window-next').click();assert(d.querySelector('g[data-schedule-select="2"]'));d.querySelector('#schedule-window-next').click();assert.equal(d.querySelectorAll('.schedule-job').length,0);assert(d.body.textContent.includes('Ebben az időszakban nincs ütemezett job.'));
 d.querySelector('table.schedule-manufacturing button[data-schedule-select="4"]').click();assert(d.querySelector('g[data-schedule-select="4"].selected'));assert(d.querySelector('#schedule-window-next').disabled);assert.equal(run('scheduleWindow'),11);
 assert.equal(d.querySelectorAll('table.schedule-manufacturing tbody tr').length,2);assert.equal(JSON.stringify(data.jobs),wholeJob);
 change('0');assert(!d.querySelector('#schedule-timeline-days').validity.valid);assert.equal(run('scheduleTimelineDays'),1);change('1.5');assert(!d.querySelector('#schedule-timeline-days').validity.valid);assert.equal(run('scheduleTimelineDays'),1);
 change('3');assert.equal(run('scheduleTimelineDays'),3);assert(d.querySelector('#schedule-timeline-days').validity.valid);
 d.querySelector('#schedule-timeline-full').click();assert.equal(d.querySelector('#schedule-timeline-days').value,'');assert.equal(d.querySelectorAll('.schedule-job').length,4);assert(d.querySelector('#schedule-window-prev').disabled&&d.querySelector('#schedule-window-next').disabled);assert.equal(JSON.parse(dom.window.localStorage.getItem('eve-muhely-schedule-timeline')).days,null);
 change('1');const character=d.querySelector('#schedule-character-filter');character.value='1';character.dispatchEvent(new dom.window.Event('change',{bubbles:true}));d.querySelector('table.schedule-manufacturing button[data-schedule-select="4"]').click();assert.equal(d.querySelector('#schedule-character-filter').value,'2');assert(d.querySelector('g[data-schedule-select="4"].selected'));
 dom.window.EveI18n.setLanguage('en');await new Promise(r=>setImmediate(r));assert(d.body.textContent.includes('Visible days'));assert(d.body.textContent.includes('Next period'));assert(d.body.textContent.includes('jobs in this period'));assert(!d.querySelector('#schedule-timeline-help').textContent.includes('idővonal'));
 dom.window.close();
});

test('timeline span reloads independently and ignores malformed saved preferences',async()=>{
 for(const [saved,expected] of [['{"days":3}',3],['{"days":null}',null],['{"days":0}',7],['null',7],['broken',7]]){
  const {dom,d,run}=await setup(fixture(),saved);
  assert.equal(run('scheduleTimelineDays'),expected);assert.equal(d.querySelector('#schedule-timeline-days').value,expected===null?'':String(expected));dom.window.close();
 }
});

test('actual EVE jobs have separate lanes and IDs; planned start times do not imply running',async()=>{
 const now=Date.now()/1000,data=fixture();data.start=now;data.calculated_at=now;data.partial_finish=now+500;
 data.jobs=[j(1,'manufacturing',now,now+500)];
 data.running_jobs=[{...j('eve:1','manufacturing',now-100,now+100),existing:true,eve_job_id:1,observed_at:now-10,stale:false}];
 const pure=graph.build(data);assert.equal(pure.lanes.length,2);assert.notEqual(pure.nodes[0].y,pure.nodes[1].y);assert.equal(pure.nodes[0].x,pure.left);
 const {dom,d,run}=await setup(data);
 assert.equal(d.querySelectorAll('.schedule-job.existing').length,1);assert(!d.querySelector('g[data-schedule-select="1"]').classList.contains('existing'));
 d.querySelector('g[data-schedule-select="eve:1"]').dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true}));
 assert(d.querySelector('g[data-schedule-select="eve:1"].selected'));assert(d.querySelector('#schedule-job-detail').textContent.includes('Folyamatban az EVE-ben'));assert.equal(Math.floor(d.querySelector('progress').value),50);
 assert.equal(d.querySelectorAll('table.schedule-manufacturing tbody tr').length,1);assert.equal(data.jobs.length,1);
 dom.window.fixture.running_jobs[0].end=now-1;run('updateRunningJobMarkers(fixture,document.querySelector("main"))');
 assert(d.querySelector('.schedule-job.existing-ready'));assert(d.querySelector('#schedule-job-detail').textContent.includes('Várhatóan elkészült'));
 dom.window.fixture.running_jobs[0].end=now+100;dom.window.fixture.running_jobs[0].stale=true;run('updateRunningJobMarkers(fixture,document.querySelector("main"))');assert(d.querySelector('.schedule-job.existing-stale'));
 dom.window.EveI18n.setLanguage('en');await new Promise(r=>setImmediate(r));assert(d.body.textContent.includes('Running in EVE'));assert(d.querySelector('#schedule-job-detail').textContent.includes('Running · older EVE data'));run('updateRunningJobMarkers(fixture,document.querySelector("main"))');assert(!d.querySelector('.schedule-window-range').textContent.includes('okt.'));
 dom.window.close();
});
test('running-only plans show the current window even when the next planned start is in the future',()=>{
 const data={...fixture(),start:200000,calculated_at:1000,jobs:[],running_jobs:[{...j('eve:77','reaction',500,5000),existing:true,eve_job_id:77}]};
 const g=graph.build(data,0,null,{days:1,window:0});assert.equal(g.start,1000);assert.equal(g.nodes.length,1);assert.equal(g.nodes[0].id,'eve:77');assert.equal(g.nodes[0].x,g.left);
});
