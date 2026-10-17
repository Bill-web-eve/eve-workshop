const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),graph=require('../static/schedule-graph.js'),planGraph=require('../static/graph.js');
const j=(id,activity,start,end,dependencies=[])=>({id,activity,start,end,name:'Item '+id,product_id:id,character_id:1,character_name:'Pilot <one>',slot:1,runs:1,output:1,materials_ready:start,materials:[],dependencies,blueprint_kind:'BPO',blueprint_item_id:id,me:0,te:0});
const fixture=()=>({start:1000,partial_finish:1400,finish:1400,seconds:400,complete:true,runs:3,assumptions:[],supply_at:1000,workers:[],blueprint_shortages:[],blocked:[],material_warnings:[],material_shortfall:[],jobs:[j(1,'reaction',1000,1200),j(2,'manufacturing',1000,1100),j(3,'manufacturing',1200,1400,[{job_id:1,material_id:1,quantity:1},{job_id:2,material_id:2,quantity:1}])]});
test('same character reaction and manufacturing use distinct lanes and the same time axis',()=>{
 const g=graph.build(fixture(),0,3),[a,b,c]=g.nodes;
 assert.equal(g.lanes.length,2);assert.equal(a.x,b.x);assert.notEqual(a.y,b.y);assert.equal(b.y,c.y);
 assert.equal(a.x+a.width,c.x);assert.equal(g.links.length,2);assert.deepEqual(g.links.map(l=>l.from),[1,2]);assert(g.links.every(l=>l.to===3));
});
test('pagination bounds nodes while keeping global scale and IDs',()=>{
 const data=fixture();data.jobs=Array.from({length:10000},(_,i)=>j(i+1,i%2?'reaction':'manufacturing',1000+i,1001+i));data.partial_finish=11000;
 const g=graph.build(data,500,10000),first=graph.build(data,0);
 assert.equal(g.nodes.length,100);assert.equal(g.pages,100);assert.equal(g.page,99);assert.equal(g.nodes[0].id,9901);assert.equal(g.end,first.end);assert.equal(g.start,first.start);
 const empty=graph.build({...data,jobs:[],partial_finish:1000});assert.equal(empty.pages,1);assert.equal(empty.nodes.length,0);assert(empty.height>=120);
});
async function setup(data){
 const dom=new JSDOM('<html lang="hu"><body><main></main></body></html>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),ctx=dom.getInternalVMContext(),run=s=>vm.runInContext(s,ctx);
 dom.window.fixture=data;
 run(`const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),verbatim=v=>'<span data-i18n-skip>'+esc(v)+'</span>',itemName=verbatim,fmt=String,date=String,hours=String;
 const panel=(title,sub,body)=>'<section><h2>'+title+'</h2><small>'+sub+'</small>'+body+'</section>',table=(h,r,cls='')=>'<table class="'+cls+'"><thead><tr>'+h.map(x=>'<th>'+x+'</th>').join('')+'</tr></thead><tbody>'+r.join('')+'</tbody></table>';`);
 for(const f of ['i18n-en.js','i18n.js','graph.js','schedule-graph.js','schedule.js'])run(fs.readFileSync(__dirname+'/../static/'+f,'utf8'));
 await new Promise(r=>setImmediate(r));run(`renderScheduleResult($('main'),fixture);`);await new Promise(r=>setImmediate(r));
 return {dom,d:dom.window.document,run};
}
test('separate activity tables, keyboard selection, dependency arrows and translation work',async()=>{
 const data=fixture();data.jobs[2].materials=[{id:1,name:'Raw <ore>',quantity:1,allocations:[{source:'job',job_id:1,quantity:1,available_at:1200}]}];
 const {dom,d}=await setup(data);
 assert.equal(d.querySelectorAll('table.schedule-reaction tbody tr').length,1);assert.equal(d.querySelectorAll('table.schedule-manufacturing tbody tr').length,2);
 assert.equal(d.querySelector('script'),null);assert(d.querySelector('.schedule-lane').textContent.includes('Pilot <one>'));
 d.querySelector('g[data-schedule-select="3"]').dispatchEvent(new dom.window.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
 assert.equal(d.querySelectorAll('.schedule-link').length,2);assert.match(d.querySelector('#schedule-job-detail').textContent,/Raw <ore>/);
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
 data.jobs[100].materials=[{id:1,name:'Material',quantity:1,allocations:[{source:'job',job_id:1,quantity:1,available_at:1001}]}];
 const {dom,d}=await setup(data);
 d.querySelector('#schedule-graph-next').click();assert(d.querySelector('g[data-schedule-select="101"]'));
 d.querySelector('g[data-schedule-select="101"]').dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true}));assert(d.querySelector('#schedule-job-detail button[data-schedule-select="1"]'));
 d.querySelector('#schedule-job-detail button[data-schedule-select="1"]').click();assert(d.querySelector('g[data-schedule-select="1"].selected'));
 assert.equal(d.querySelectorAll('table.schedule-reaction tbody tr').length,100);
 d.querySelector('[data-schedule-table-page="1"][data-activity="reaction"]').click();assert.equal(d.querySelectorAll('table.schedule-reaction tbody tr').length,1);assert(d.querySelector('g[data-schedule-select="1"].selected'));
 dom.window.close();
});

test('full product flow preserves reaction-to-reaction-to-manufacturing links across job pages',()=>{
 const data=fixture();data.jobs=Array.from({length:100},(_,i)=>({...j(i+1,'reaction',1000,1200),product_id:10,name:'Base reaction'}));
 data.jobs.push({...j(101,'reaction',1200,1300,[{job_id:1,quantity:1},{job_id:100,quantity:1}]),product_id:20,name:'Compound reaction'});
 data.jobs.push({...j(102,'manufacturing',1300,1400,[{job_id:101,quantity:1}]),product_id:30,name:'Component'});
 data.jobs.push({...j(103,'manufacturing',1400,1500,[{job_id:102,quantity:1}]),product_id:40,name:'Ship'});
 const f=graph.flow(data,planGraph);assert.equal(f.nodes.length,4);assert.equal(f.edges.length,3);
 assert.deepEqual(f.edges.map(e=>[e.from,e.to,e.quantity]),[[10,20,2],[20,30,1],[30,40,1]]);
 assert.equal(f.nodes.find(n=>n.id===10).job_ids.length,100);
 for(const e of f.edges)assert(f.nodes.find(n=>n.id===e.from).x<f.nodes.find(n=>n.id===e.to).x);
 assert.deepEqual([...graph.related(data,103)].sort((a,b)=>a-b),[1,100,101,102,103]);
 assert(f.nodes.some(n=>n.id===40));assert.equal(graph.build(data,0,103).nodes.some(n=>n.id===103),false);
});
test('timeline shows all visible links and highlights the entire ancestor chain',()=>{
 const data=fixture();data.jobs=[j(1,'reaction',1000,1100),j(2,'reaction',1100,1200,[{job_id:1,quantity:1}]),j(3,'manufacturing',1200,1300,[{job_id:2,quantity:1}]),j(4,'manufacturing',1300,1400,[{job_id:3,quantity:1}]),j(5,'reaction',1000,1100),j(6,'manufacturing',1100,1200,[{job_id:5,quantity:1}])];
 const g=graph.build(data,0,4);assert.equal(g.links.length,4);assert.deepEqual(g.links.filter(l=>l.highlight).map(l=>[l.from,l.to]),[[1,2],[2,3],[3,4]]);
 assert.equal(graph.build(data,0).links.length,4);
});
test('source shared with another branch does not highlight that sibling branch',()=>{
 const data=fixture();data.jobs=[j(1,'reaction',1000,1100),j(2,'manufacturing',1100,1200,[{job_id:1,quantity:1}]),j(3,'manufacturing',1100,1200,[{job_id:1,quantity:1}])];
 assert.deepEqual([...graph.related(data,2)].sort(),[1,2]);assert.equal(graph.flow(data,planGraph).nodes.length,3);
});
test('full flow and cross-page card selection work with Hungarian and English UI',async()=>{
 const data=fixture();data.jobs=Array.from({length:101},(_,i)=>({...j(i+1,'reaction',1000,1200),product_id:10,name:'Reaction'}));
 data.jobs.push({...j(102,'manufacturing',1200,1400,[{job_id:101,quantity:1}]),product_id:20,name:'Component'});
 const {dom,d}=await setup(data);
 assert.equal(d.querySelectorAll('.schedule-flow .graph-node').length,2);assert.equal(d.querySelectorAll('.schedule-flow .graph-edge').length,1);
 d.querySelector('.schedule-flow [data-schedule-flow-select="102"]').dispatchEvent(new dom.window.MouseEvent('click',{bubbles:true}));
 assert(d.querySelector('.schedule-timeline g[data-schedule-select="102"].selected'));assert(d.querySelector('#schedule-job-detail'));
 d.querySelector('[data-schedule-zoom="fit"]').click();assert(Number(d.querySelector('.schedule-flow svg').getAttribute('width'))>0);
 dom.window.EveI18n.setLanguage('en');await new Promise(r=>setImmediate(r));
 assert(d.body.textContent.includes('Full production dependency chain'));assert(d.body.textContent.includes('First start'));assert(!d.querySelector('.schedule-flow').textContent.includes('Gyártás'));
 dom.window.close();
});
