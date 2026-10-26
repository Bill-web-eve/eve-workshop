'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),tick=()=>new Promise(r=>setImmediate(r));
function setup(){
 const dom=new JSDOM('<div id="production-finance"></div><main></main>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 run(`const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=v=>String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),verbatim=esc,itemName=esc,fmt=String;const table=(headers,rows)=>'<table><tbody>'+rows.join('')+'</tbody></table>';let activePlanId=null,corporationId=null,view='queue',state={characters:[{id:11,name:'Seller'},{id:12,name:'Other seller'}]},dirty={};const economicPanels=new Map();let jobCostKey='job',jobCostData={complete:true,cents:'10000',rows:[]};const planEconomics=p=>economicPanels.set('plan-materials',{key:'job',plan:p});const error=()=>{},toast=()=>{},openSettingsTab=()=>{};`);
 for(const file of ['i18n-en.js','i18n.js','costs.js','trade.js'])run(fs.readFileSync(__dirname+'/../static/'+file,'utf8'));
 run(`const c={materials:[{id:2,name:'Material',quantity:10}],quantity:2,plan:{product_id:1,quantity:10,queue:[{id:1,manufactured:2}],blueprint_shortages:[{id:3,buy:1,unit:'run'}]}};const f={materials:'local:sell',sale:'jita:sell',seller_id:11,sale_order:'auto',other_isk:'10',blueprints_isk:'50'};const books={jita:{quotes:{1:{buy:'50000',sell:'100000'},2:{buy:'10',sell:'20'}}},local:{quotes:{1:{buy:'50000',sell:'80000'},2:{buy:'30',sell:'40'}}}};const profile={sales_tax:'3.375',broker_fee:'1.04',warnings:[],accounting:5,broker_relations:5,location:{name:'Jita'}};`);
 return {dom,w,run,d:w.document};
}
test('material and sale sources are independent and include all configured costs and seller fees',t=>{
 const {dom,run}=setup();t.after(()=>dom.window.close());
 const out=run(`financeValues(c,f,books,profile,{complete:true,cents:'10000'})`);
 assert.equal(out.values.materials,40000n);assert.equal(out.values.blueprints,5000n);assert.equal(out.values.total,56000n);
 assert.equal(out.values.gross,20000000n);assert.equal(out.values.sales_tax,675000n);assert.equal(out.values.broker_fee,208000n);assert.equal(out.values.profit,19061000n);
 const buy=run(`financeValues(c,{...f,sale:'local:buy'},books,profile,{complete:true,cents:'10000'})`);
 assert.equal(buy.values.broker_fee,0n);assert.equal(buy.values.gross,10000000n);assert.equal(buy.values.profit,9606500n);
});
test('missing local prices, job costs or seller rates prevent a fake complete profit',t=>{
 const {dom,run}=setup();t.after(()=>dom.window.close());
 for(const expression of [
 `financeValues(c,f,{...books,local:{quotes:{}}},profile,{complete:true,cents:'10000'})`,
 `financeValues(c,f,books,null,{complete:true,cents:'10000'})`,
 `financeValues(c,f,books,profile,null)`])assert.equal(run(expression).values.profit,null);
});
test('immediate selling skips broker fees; new orders apply the 100 ISK floor exactly once',t=>{
 const {dom,run}=setup();t.after(()=>dom.window.close());
 const result=run(`financeValues({...c,quantity:1},{...f,sale_order:'order'}, {...books,jita:{quotes:{1:{sell:'100'}}}},profile,{complete:true,cents:'0'})`);
 assert.equal(result.values.broker_fee,10000n);
 assert.equal(run(`financeFee(123456789n,'1.12345678')`),1386984n);
 assert.equal(run(`financeValues(c,{...f,sale_order:'instant'},books,{sales_tax:'3.375',broker_fee:null},{complete:true,cents:'0'}).values.broker_fee`),0n);
});
test('an explicit zero broker estimate stays zero while sales tax is retained',t=>{
 const {dom,run}=setup();t.after(()=>dom.window.close());
 const result=run(`financeValues(c,f,books,{...profile,broker_fee:'0'},{complete:true,cents:'10000'})`);
 assert.equal(result.values.broker_fee,0n);assert.equal(result.values.sales_tax,675000n);
 assert.equal(result.values.net,19325000n);assert.equal(result.values.profit,19269000n);
 const small=run(`financeValues({...c,quantity:1},f,{...books,jita:{quotes:{1:{sell:'0.01'}}}},{...profile,broker_fee:'0.0001'},{complete:true,cents:'0'})`);
 assert.equal(small.values.broker_fee,10000n);
});
test('the compact card prices only newly planned target output and exposes independent controls',t=>{
 const {dom,run,d}=setup();t.after(()=>dom.window.close());
 run(`financePrefs=f;document.querySelector('#production-finance').innerHTML=productionFinance(c.plan,c.materials);financePrefs=f;financeBooks=books;financeProfile=profile;applyProductionFinance();`);
 assert.equal(run('financeContext.quantity'),2);
 assert(d.querySelector('#production-finance').textContent.includes('Munkaköltség'));
 assert(d.querySelector('#production-finance').textContent.includes('Közvetítői díj'));
 assert.equal(d.querySelectorAll('.finance-grid>section').length,3);
 assert.equal(d.querySelectorAll('[data-finance-field=materials] option').length,6);
 assert.equal(d.querySelectorAll('[data-finance-field=sale] option').length,6);
 assert.equal(d.querySelector('[data-finance-value=profit]').textContent,'190 610,00 ISK');
 assert.equal(d.querySelectorAll('.finance-details').length,1);
 run(`EveI18n.setLanguage('en');EveI18n.translate(document.documentElement);`);
 const text=d.querySelector('#production-finance').textContent;
 assert.match(text,/Production cost and expected revenue/);assert(!/[áéíóöőúüű]/i.test(text),text);
});
test('each saved plan loads its own preferences and fields keep the saved plan ID on updates',async t=>{
 const {dom,w,run,d}=setup();t.after(()=>w.close());const calls=[];
 w.api=async(path,body)=>{calls.push([path,body]);if(path.startsWith('/api/trade/plan'))return {materials:'local:buy',sale:'jita:sell',seller_id:null,sale_order:'auto',other_isk:'10',blueprints_isk:'50'};if(path==='/api/trade')return {settings:{},status:{running:false}};return {quotes:{},errors:{},retry_after:{},running:false};};
 run(`activePlanId='plan-a';document.querySelector('#production-finance').innerHTML=productionFinance(c.plan,c.materials);bindProductionFinance();`);
 await tick();await tick();await tick();
 assert(calls.some(([p])=>p==='/api/trade/plan?plan_id=plan-a'));
 const input=d.querySelector('[data-finance-field=sale]');input.value='local:buy';input.dispatchEvent(new w.Event('change'));
 await new Promise(r=>setTimeout(r,350));
 const saved=calls.find(([path,body])=>path==='/api/trade/plan'&&body);assert.equal(saved[1].plan_id,'plan-a');assert.equal(saved[1].materials,'local:buy');assert.equal(saved[1].sale,'local:buy');
});
test('refreshing only missing items retains already fresh target and material quotes',async t=>{
 const {w,run}=setup();t.after(()=>w.close());const calls=[];
 w.api=async(path,body)=>{calls.push([path,body]);return body?{quotes:{4:{buy:'5',sell:'6'}},errors:{},retry_after:{},running:false}:{quotes:{1:{buy:'50000',sell:'100000',stale:false},2:{buy:'10',sell:'20',stale:false}},errors:{},retry_after:{},running:false};};
 run(`document.querySelector('#production-finance').innerHTML=productionFinance(c.plan,[...c.materials,{id:4,name:'New material',quantity:1}]);financePrefs={...f,materials:'jita:sell'};`);
 await run('loadFinancePrices()');
 assert.equal(run("financeBooks.jita.quotes['1'].sell"),'100000');assert.equal(run("financeBooks.jita.quotes['2'].sell"),'20');assert.equal(run("financeBooks.jita.quotes['4'].sell"),'6');
 assert.deepEqual(Array.from(calls.find(([path,body])=>body)[1].ids),[4]);
});

test('unspecified BPC costs use zero and a note, including owned copies; BPO-only plans have neither cost nor note',t=>{
 const {dom,run}=setup();t.after(()=>dom.window.close());
 const missing=run(`financeValues(c,{...f,blueprints_isk:null},books,profile,{complete:true,cents:'10000'})`);
 assert.equal(missing.values.blueprints,0n);assert.equal(missing.bpcUnspecified,true);assert.notEqual(missing.values.profit,null);
 const owned=run(`financeValues({...c,plan:{...c.plan,blueprint_shortages:[],queue:[{activity:'manufacturing',parameters:{kind:'BPC'}}]}},{...f,blueprints_isk:null},books,profile,{complete:true,cents:'10000'})`);
 assert.equal(owned.values.blueprints,0n);assert.equal(owned.bpcUnspecified,true);
 const bpo=run(`financeValues({...c,plan:{...c.plan,blueprint_shortages:[],queue:[{activity:'manufacturing',parameters:{kind:'BPO'}}]}},f,books,profile,{complete:true,cents:'10000'})`);
 assert.equal(bpo.values.blueprints,0n);assert.equal(bpo.bpcUnspecified,false);
 assert.equal(run(`financeValues(c,{...f,blueprints_isk:'0'},books,profile,{complete:true,cents:'10000'}).bpcUnspecified`),false);
 run(`financePrefs={...f,blueprints_isk:null};document.querySelector('#production-finance').innerHTML=productionFinance(c.plan,c.materials);financePrefs={...f,blueprints_isk:null};financeBooks=books;financeProfile=profile;applyProductionFinance();EveI18n.setLanguage('en');EveI18n.translate(document.documentElement);`);
 assert.match(dom.window.document.querySelector('[data-finance-bpc-note]').textContent,/BPC cost not provided; calculated as 0 ISK/);
 assert.notEqual(dom.window.document.querySelector('[data-finance-value=total]').textContent,'–');
});
test('hauling uses only outstanding non-blueprint purchases, rounds once, and is part of total and profit',t=>{
 const {dom,run}=setup();t.after(()=>dom.window.close());
 const h=run(`financeHauling({shopping:[{id:1,buy:3,volume:.005},{id:2,buy:2,volume:.005},{id:3,buy:100,volume:1,is_blueprint:true},{id:4,buy:0,volume:100}]},'1')`);
 assert.equal(h.volume,2500000n);assert.equal(h.cents,3n);
 const missing=run(`financeHauling({shopping:[{buy:2}]},'100')`);assert.equal(missing.cents,null);
 assert.equal(run(`financeHauling({shopping:[{buy:2}]},'0').cents`),0n);
 run(`tradeData={settings:{hauling_isk_per_m3:'125.4321'}}`);
 const out=run(`financeValues({...c,plan:{...c.plan,shopping:[{id:2,buy:10,volume:.01}]}},f,books,profile,{complete:true,cents:'10000'})`);
 assert.equal(out.values.hauling,1254n);assert.equal(out.values.total,57254n);assert.equal(out.values.profit,19059746n);
});
test('missing reaction formulas remain priced separately from optional BPC estimates',t=>{
 const {dom,run}=setup();t.after(()=>dom.window.close());
 const out=run(`financeValues({...c,plan:{...c.plan,blueprint_shortages:[...c.plan.blueprint_shortages,{id:2,buy:1,unit:'db'}]}},{...f,blueprints_isk:null},books,profile,{complete:true,cents:'10000'})`);
 assert.equal(out.values.blueprints,4000n);assert.equal(out.bpcUnspecified,true);
});
test('the hauling setting can be saved before market setup without changing selected hub or reader',async t=>{
 const {dom,w,run,d}=setup();t.after(()=>w.close());const calls=[];
 w.api=async(path,body)=>{calls.push([path,body]);return {settings:{hauling_rates:body.hauling_rates},status:{running:false},characters:[],scopes:[]};};
 run(`const panel=(title,sub,body)=>'<section><h2>'+title+'</h2>'+body+'</section>';tradeData={settings:{hauling_isk_per_m3:'0'},status:{running:false},characters:[],scopes:[]};renderTradeSettings(document.querySelector('main'));`);
 const form=d.querySelector('#hauling-settings');form.elements.hauling_jita_import.value='250.1234';form.elements.hauling_jita_export.value='500';form.elements.hauling_local_import.value='0';form.elements.hauling_local_export.value='200';form.dispatchEvent(new w.Event('submit',{cancelable:true}));await tick();
 assert.equal(calls[0][0],'/api/trade/hauling');assert.deepEqual(JSON.parse(JSON.stringify(calls[0][1])),{hauling_rates:{jita:{import:'250.1234',export:'500'},local:{import:'0',export:'200'}}});
 run(`EveI18n.setLanguage('en');EveI18n.translate(document.documentElement);`);assert.match(form.textContent,/Import.*raw materials/);assert.match(form.textContent,/Export.*finished product/);assert(!/[áéíóöőúüű]/i.test(form.textContent));
});

test('import follows material market and export follows selling market independently, using only new packaged output',t=>{
 const {dom,run}=setup();t.after(()=>dom.window.close());
 run(`tradeData={settings:{hauling_rates:{jita:{import:'100',export:'400'},local:{import:'200',export:'800'}}}};const transport={...c,plan:{...c.plan,rows:[{id:1,volume:100}],shopping:[{id:2,buy:10,volume:.01}]}};`);
 for(const material of ['jita','local'])for(const sale of ['jita','local']){
  const result=run(`financeValues(transport,{...f,materials:'${material}:sell',sale:'${sale}:sell'},books,profile,{complete:true,cents:'10000'})`);
  assert.equal(result.values.hauling_import,material==='jita'?1000n:2000n);
  assert.equal(result.values.hauling_export,sale==='jita'?8000000n:16000000n);
  assert.equal(result.values.hauling,result.values.hauling_import+result.values.hauling_export);
  assert.equal(result.values.total,result.values.materials+5000n+10000n+1000n+result.values.hauling);
  assert.equal(result.values.profit,result.values.net-result.values.total);
 }
 const empty=run(`financeValues({...transport,quantity:0},{...f,sale:'local:sell'},books,profile,{complete:true,cents:'10000'})`);
 assert.equal(empty.values.hauling_export,0n);
 const partial=run(`financeValues({...transport,plan:{...transport.plan,rows:[]} },f,books,profile,{complete:true,cents:'10000'})`);
 assert.equal(partial.values.hauling_export,null);assert.equal(partial.values.total,null);
 const rounded=run(`financeHauling({...transport.plan,rows:[{id:1,volume:50000}]},'400',3)`);
 assert.equal(rounded.volume,15000000000000n);assert.equal(rounded.cents,6000000000n);
 run(`financePrefs=f;document.querySelector('#production-finance').innerHTML=productionFinance(transport.plan,transport.materials);financePrefs=f;financeBooks=books;financeProfile=profile;financeContext.quantity=2;applyProductionFinance();EveI18n.setLanguage('en');EveI18n.translate(document.documentElement);`);
 const d=dom.window.document;assert.match(d.querySelector('.finance-grid').textContent,/Import hauling/);assert.match(d.querySelector('.finance-grid').textContent,/Export hauling/);
 assert.match(d.querySelector('[data-finance-hauling=import]').textContent,/200 ISK/);assert.match(d.querySelector('[data-finance-hauling=export]').textContent,/400 ISK/);
});

test('high-precision ESI standing fees calculate the screenshot revenue and profit instead of reporting unknown',async t=>{
 const {dom,run,d}=setup();t.after(()=>dom.window.close());
 assert.equal(run("financeFee(82400000000n,'1.31781059532')"),1085875931n);
 // Round only the monetary result: a tiny percentage on a large order must survive.
 assert.equal(run("financeFee(1000000000000000000n,'0.0000000000001')"),1000n);
 assert.equal(run("financeFee(500n,'0.1')"),1n);
 for(const value of ['','NaN','-1','100.0000000000001','1e-10','1'.repeat(129)])assert.equal(run('financeFee(100n,'+JSON.stringify(value)+')'),null);
 run(`tradeData={settings:{hauling_rates:{jita:{import:'500',export:'650'},local:{import:'0',export:'0'}}}};
 const screenshot={materials:[{id:2,name:'Materials',quantity:1}],quantity:50,plan:{product_id:1,quantity:50,queue:[{id:1,manufactured:50,activity:'manufacturing',parameters:{kind:'BPC'}}],rows:[{id:1,volume:2500}],shopping:[{id:2,buy:1,volume:313.2}],blueprint_shortages:[]}};
 const preciseProfile={...profile,broker_fee:'1.31781059532'};
 const screenshotPrefs={...f,materials:'jita:sell',sale:'jita:sell',sale_order:'order',other_isk:'0',blueprints_isk:null};
 const screenshotBooks={jita:{quotes:{1:{sell:'16480000',stale:true},2:{sell:'573799495.60'}}}};
 const screenshotJobs={complete:true,cents:'22097347269'};
 const precise=financeValues(screenshot,screenshotPrefs,screenshotBooks,preciseProfile,screenshotJobs);
 document.querySelector('#production-finance').innerHTML=productionFinance(screenshot.plan,screenshot.materials);
 financeContext.quantity=50;financePrefs=screenshotPrefs;financeBooks=screenshotBooks;financeProfile=preciseProfile;
 economicPanels.set('plan-materials',{key:'screenshot'});jobCostKey='screenshot';jobCostData=screenshotJobs;applyProductionFinance();
 EveI18n.setLanguage('en');EveI18n.translate(document.documentElement);`);
 await tick();const out=run('precise.values');assert.equal(out.gross,82400000000n);assert.equal(out.sales_tax,2781000000n);assert.equal(out.broker_fee,1085875931n);assert.equal(out.net,78533124069n);assert.equal(out.total,87617956829n);assert.equal(out.profit,-9084832760n);
 assert.equal(d.querySelector('[data-finance-value=broker_fee]').textContent,'10 858 759,31 ISK');
 assert.equal(d.querySelector('[data-finance-value=net]').textContent,'785 331 240,69 ISK');
 assert(!d.querySelector('[data-finance-warning]').textContent.includes('Broker fee is unknown'));
 assert(d.querySelector('[data-finance-warning]').textContent.includes('Some market quotes are from an older snapshot'));
});

test('hauling switch excludes both directions, preserves rates and missing volumes only block when enabled',t=>{
 const {w,run}=setup();t.after(()=>w.close());
 run(`tradeData={settings:{hauling_rates:{jita:{import:'500',export:'650'},local:{import:'100',export:'200'}}}};const transport={...c,plan:{...c.plan,rows:[{id:1,volume:2500}],shopping:[{id:2,buy:10,volume:.01}]}};`);
 const before=run('JSON.stringify(tradeData.settings.hauling_rates)');
 const on=run('financeValues(transport,f,books,profile,{complete:true,cents:"10000"})');
 const off=run('financeValues(transport,{...f,hauling_enabled:false},books,profile,{complete:true,cents:"10000"})');
 assert.equal(on.values.hauling_import,1000n);assert.equal(on.values.hauling_export,325000000n);
 assert.equal(off.values.hauling_import,0n);assert.equal(off.values.hauling_export,0n);assert.equal(off.values.total,on.values.total-on.values.hauling);assert.equal(off.values.profit,on.values.profit+on.values.hauling);
 assert.equal(run('JSON.stringify(tradeData.settings.hauling_rates)'),before);
 const missing=run('financeValues({...transport,plan:{...transport.plan,rows:[],shopping:[{id:2,buy:10}]}},{...f,hauling_enabled:false},books,profile,{complete:true,cents:"10000"})');assert.notEqual(missing.values.profit,null);
 assert.equal(run('financeValues({...transport,plan:{...transport.plan,rows:[],shopping:[{id:2,buy:10}]}},f,books,profile,{complete:true,cents:"10000"}).values.profit'),null);
});

test('import and export checkboxes restore, change costs immediately and save only the selected plan',async t=>{
 const {w,run,d}=setup();t.after(()=>w.close());const calls=[];
 w.api=async(path,body)=>{calls.push({path,body});if(path.startsWith('/api/trade/plan'))return {...run('f'),hauling_enabled:false};if(path==='/api/trade')return {settings:{hauling_rates:{jita:{import:'500',export:'650'},local:{import:'100',export:'200'}}},status:{running:false}};if(path.startsWith('/api/trade/seller?'))return run('profile');return {...run('books.jita'),errors:{},retry_after:{},running:false};};
 run(`activePlanId='plan-hauling';document.querySelector('#production-finance').innerHTML=productionFinance({...c.plan,rows:[{id:1,volume:2500}],shopping:[{id:2,buy:1,volume:313.2}]},c.materials);bindProductionFinance();`);
 await tick();await tick();await tick();
 const inbound=d.querySelector('[data-finance-field=hauling_import_enabled]'),outbound=d.querySelector('[data-finance-field=hauling_export_enabled]');assert.equal(inbound.checked,false);assert.equal(outbound.checked,false);
 inbound.checked=true;inbound.dispatchEvent(new w.Event('change'));assert.equal(run('financePrefs.hauling_import_enabled'),true);assert.equal(d.querySelector('[data-finance-value=hauling_export]').textContent,'0,00 ISK');assert.notEqual(d.querySelector('[data-finance-value=hauling_import]').textContent,'0,00 ISK');
 await new Promise(r=>setTimeout(r,350));let saved=calls.filter(c=>c.path==='/api/trade/plan'&&c.body).at(-1);assert.equal(saved.body.plan_id,'plan-hauling');assert.equal(saved.body.hauling_import_enabled,true);assert.equal(saved.body.hauling_export_enabled,false);
 outbound.checked=true;outbound.dispatchEvent(new w.Event('change'));inbound.checked=false;inbound.dispatchEvent(new w.Event('change'));
 await new Promise(r=>setTimeout(r,350));saved=calls.filter(c=>c.path==='/api/trade/plan'&&c.body).at(-1);assert.equal(saved.body.hauling_import_enabled,false);assert.equal(saved.body.hauling_export_enabled,true);assert.equal(d.querySelector('[data-finance-value=hauling_import]').textContent,'0,00 ISK');assert.notEqual(d.querySelector('[data-finance-value=hauling_export]').textContent,'0,00 ISK');assert(!calls.some(c=>c.path==='/api/trade/hauling'));
 w.EveI18n.setLanguage('en');await tick();assert.match(inbound.closest('label').textContent,/Import hauling/);assert.match(outbound.closest('label').textContent,/Export hauling/);assert.equal(inbound.checked,false);assert.equal(outbound.checked,true);
});
test('independent hauling switches calculate all four combinations including unknown volumes',t=>{
 const {w,run}=setup();t.after(()=>w.close());run(`tradeData={settings:{hauling_rates:{jita:{import:'100',export:'400'},local:{import:'200',export:'800'}}}};const transport={...c,plan:{...c.plan,rows:[{id:1,volume:100}],shopping:[{id:2,buy:10,volume:.01}]}};`);
 const baseline=run('financeValues(transport,f,books,profile,{complete:true,cents:"10000"})');
 for(const inbound of [false,true])for(const outbound of [false,true]){
  const out=run(`financeValues(transport,{...f,hauling_import_enabled:${inbound},hauling_export_enabled:${outbound}},books,profile,{complete:true,cents:'10000'})`);
  assert.equal(out.values.hauling_import,inbound?2000n:0n);assert.equal(out.values.hauling_export,outbound?8000000n:0n);assert.equal(out.values.total,baseline.values.total-baseline.values.hauling+out.values.hauling);assert.equal(out.values.profit,baseline.values.profit+baseline.values.hauling-out.values.hauling);
 }
 const missingInbound=run(`financeValues({...transport,plan:{...transport.plan,shopping:[{id:2,buy:10}]}},{...f,hauling_import_enabled:false,hauling_export_enabled:true},books,profile,{complete:true,cents:'10000'})`);assert.notEqual(missingInbound.values.total,null);
 const missingOutbound=run(`financeValues({...transport,plan:{...transport.plan,rows:[]}},{...f,hauling_import_enabled:true,hauling_export_enabled:false},books,profile,{complete:true,cents:'10000'})`);assert.notEqual(missingOutbound.values.total,null);
});
