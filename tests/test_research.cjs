const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function fixture(){
 const dom=new JSDOM('<body><div id="actions"></div><main></main></body>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=code=>vm.runInContext(code,dom.getInternalVMContext());
 const now=Date.now()/1000;
 w.DATA={characters:[{id:1,name:'Pilot <A>',authorized:true,checked_at:now,next_refresh:now+86400},{id:2,name:'Pilot B',authorized:false}],
   rows:[{character_id:1,character_name:'Pilot <A>',agent_id:10,agent_name:'Agent <script>',field:'Caldari Starship Engineering',rp:'299.99',rp_per_day:100,datacore_id:25887,datacore_name:'Datacore - Caldari Starship Engineering',quantity:2,redemption_cost:20000,checked_at:now}],
   totals:[{id:25887,name:'Datacore - Caldari Starship Engineering',quantity:2,rp_per_day:100}],quantity:2,redemption_cost:20000,at:now,rp_per_day:100,calculated_at:now,next_refresh:now+86400,
   prices:{quotes:{25887:{buy:'15000',sell:'25000',checked:now}}},scopes:['esi-characters.read_agents_research.v1']};
 w.calls=[];w.api=async(path,body)=>{w.calls.push({path,body});return structuredClone(w.DATA);};
 run(`const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),fmt=s=>new Intl.NumberFormat('hu-HU').format(s),date=s=>'DATE';
 const verbatim=s=>'<span data-i18n-skip>'+esc(s)+'</span>',itemName=s=>'<span class="copy-item-name">'+esc(s)+'</span>';
 let view='research',state={task:{running:false}},lastError='',auth=null;
 function error(s){lastError=s;}function setHead(){}function empty(s){return '<p>'+s+'</p>';}function actions(s){$('#actions').innerHTML=s;}
 function panel(title,note,body){return '<section><h2>'+esc(title)+'</h2>'+body+'</section>';}function table(heads,rows,cls){return EveTables.markup(heads,rows,cls,cls);}
 function csv(){}async function openEveAuthorization(value){auth=value;}async function startTask(path,manual=true){calls.push({path,manual});}function render(){renderResearch(document.querySelector('main'));}
 `);
 for(const file of ['i18n-en.js','i18n.js','costs.js','tables.js','research.js'])run(fs.readFileSync(__dirname+'/../static/'+file,'utf8'));
 await tick();run('researchData=DATA;render();');await tick();
 return {w,d,run,close:()=>w.close()};
}
test('research combines agents, uses fee-adjusted Jita values and escapes EVE names in both languages',async t=>{
 const f=await fixture();t.after(f.close);const {d,w}=f;
 assert.equal(d.querySelector('script'),null);assert(d.body.textContent.includes('Agent <script>'));
 w.EveI18n.setLanguage('en');await tick();
 assert(d.body.textContent.includes('Redeemable datacores'));assert(d.body.textContent.includes('Jita value after redemption fee'));
 const metrics=[...d.querySelectorAll('.research-metrics strong')].map(el=>el.textContent.replace(/\s/g,''));
 assert.equal(metrics[1],'50000,00ISK');assert.equal(metrics[2],'20000,00ISK');assert.equal(metrics[3],'30000,00ISK');
 assert(d.body.textContent.includes('Partial summary'));assert(d.body.textContent.includes('ESI provides no halt status or RP cap'));
 assert(!/[áéíóöőúüű]/i.test(d.body.textContent.replace('Pilot <A>','')));
 w.EveI18n.setLanguage('hu');await tick();assert(d.body.textContent.includes('Beváltható datacore'));
});
test('pricing and summary tabs recalculate without new ESI or market requests',async t=>{
 const f=await fixture();t.after(f.close);const {d,w}=f;
 const mode=d.querySelector('#research-pricing');mode.value='buy';mode.dispatchEvent(new w.Event('change'));
 assert.equal(d.querySelectorAll('.research-metrics strong')[3].textContent.replace(/\s/g,''),'10000,00ISK');
 d.querySelector('[data-research-tab=cores]').click();assert(d.querySelector('.research-cores'));
 d.querySelector('[data-research-tab=characters]').click();assert(d.querySelector('.research-characters'));
 assert.equal(w.calls.length,0);
});
test('forecast and character filtering query local snapshots, and missing prices remain unknown',async t=>{
 const f=await fixture();t.after(f.close);const {w,d,run}=f;
 const form=d.querySelector('#research-filter');form.elements.character.value='1';form.elements.at.value='2026-11-06T12:30';form.dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();await tick();
 const url=new URL(w.calls[0].path,'http://127.0.0.1');assert.equal(url.searchParams.get('character_id'),'1');assert(Number.isFinite(Number(url.searchParams.get('at'))));
 assert(!w.calls.some(r=>r.path.includes('/sync')||r.path.includes('/prices')));
 run('DATA.prices.quotes={};researchData=DATA;render();');
 assert.equal(d.querySelectorAll('.research-metrics strong')[1].textContent,'–');assert.equal(d.querySelectorAll('.research-metrics strong')[3].textContent,'–');
});
test('per-character authorization requests only the research feature and preserves its return view',async t=>{
 const f=await fixture();t.after(f.close);const {d,w}=f;
 d.querySelector('[data-research-auth="2"]').click();await tick();
 assert.deepEqual(JSON.parse(JSON.stringify(w.calls[0])),{path:'/api/auth/start',body:{character_id:2,feature:'research'}});
 assert.equal(w.sessionStorage.getItem('eve-muhely-auth-return'),'research');
});
