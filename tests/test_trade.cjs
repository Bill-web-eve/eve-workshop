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
test('missing local prices, BPC costs, job costs or seller rates prevent a fake complete profit',t=>{
 const {dom,run}=setup();t.after(()=>dom.window.close());
 for(const expression of [
 `financeValues(c,{...f,blueprints_isk:null},books,profile,{complete:true,cents:'10000'})`,
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
