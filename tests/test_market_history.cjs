'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),tick=()=>new Promise(resolve=>setImmediate(resolve));
function setup(){
 const dom=new JSDOM('<div id="production-finance"></div>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 run(`const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),fmt=n=>Number(n).toLocaleString('hu-HU');let view='queue',activePlanId=null,corporationId=null,state={characters:[]};const planEconomics=()=>{};`);
 for(const file of ['i18n-en.js','i18n.js','trade.js','market-history.js'])run(fs.readFileSync(__dirname+'/../static/'+file,'utf8'));
 run(`financePrefs={...financeDefaults};financeContext={plan:{product_id:11985},quantity:50};tradeData={settings:{location:{id:123,region_id:10000058,system_name:'C-N4OD'}}};`);
 w.document.querySelector('#production-finance').innerHTML=run('financeHistoryMarkup()');w.EveI18n.setLanguage('en');
 return {dom,w,run,d:w.document};
}
function snapshot(overrides={}){
 return {checked:1234,complete:true,stale:false,running:false,daily:Array.from({length:7},(_,i)=>({date:'2026-10-'+(24+i),volume:i*10})),month_start:'2026-10-01',month_end:'2026-10-30',weekly_average:105,latest_date:'2026-10-30',...overrides};
}
test('compact history sits immediately under gross selling value and labels ESI scope honestly',t=>{
 const {dom,run,d}=setup();t.after(()=>dom.window.close());
 d.querySelector('#production-finance').innerHTML=run(`productionFinance({product_id:11985,quantity:50,queue:[{id:11985,runs:50,manufactured:50}]},[])`);
 assert.equal(d.querySelector('[data-finance-value=gross]').parentElement.nextElementSibling.dataset.financeHistory,'');
 assert.equal(d.querySelectorAll('[data-finance-history]').length,1);
 assert(d.body.textContent.includes('ESI'));
});
test('seven daily totals and 30-day weekly average use EVE dates and switch language',async t=>{
 const {dom,run,d,w}=setup();t.after(()=>dom.window.close());w.api=async()=>snapshot();
 run('syncFinanceHistory()');await tick();
 assert.equal(d.querySelectorAll('.history-day').length,7);
 assert.equal(d.querySelectorAll('[data-finance-history] [style]').length,0,'The app CSP forbids inline styles');
 assert.equal(d.querySelectorAll('.history-bar rect').length,7);
 assert.equal(d.querySelector('[data-history-refresh]').textContent,'↻ Refresh');
 assert.equal(d.querySelector('.history-day:last-child .history-bar rect').getAttribute('height'),'25');
 assert.equal(d.querySelector('.history-day:first-child .history-bar rect').getAttribute('height'),'0');
 assert.equal(d.querySelector('.history-day strong').textContent,'0');
 assert(d.body.textContent.includes('105 units / week'));
 assert(d.body.textContent.includes('Jita region · The Forge'));
 assert(d.body.textContent.includes('Total regional trades, buy and sell combined.'));
 assert(d.body.textContent.includes('30-day total volume ÷ 30 × 7'));
 assert(!d.body.textContent.includes('betöltése'));
 w.EveI18n.setLanguage('hu');assert(d.body.textContent.includes('Heti átlag · előző 30 nap'));
});
test('shifted available-day window shows its actual dates without an unpublished-day warning',async t=>{
 const {dom,run,d,w}=setup();t.after(()=>dom.window.close());const data=snapshot({complete:false,latest_date:'2026-10-29',month_end:'2026-10-29'});data.daily=data.daily.map((r,i)=>({...r,date:'2026-10-'+(23+i)}));w.api=async()=>data;
 run('syncFinanceHistory()');await tick();
 assert(d.body.textContent.includes('Last 7 available days'));assert(d.querySelector('.history-day:last-child strong').title.startsWith('2026-10-29'));
 assert(!d.body.textContent.includes('30 Oct'));assert(!d.body.textContent.includes('has not been published yet'));
});
test('unknown days and incomplete average stay unknown while valid zero stays zero',async t=>{
 const {dom,run,d,w}=setup();t.after(()=>dom.window.close());const data=snapshot({complete:false,weekly_average:null});data.daily[6].volume=null;w.api=async()=>data;
 run('syncFinanceHistory()');await tick();
 assert.equal(d.querySelector('.history-day:last-child strong').textContent,'–');
 assert(d.querySelector('.history-average').textContent.includes('–'));
 assert(!d.body.textContent.includes('has not been published yet'));
 assert.equal(d.querySelector('.history-day strong').textContent,'0');
});
test('changing sell/buy mode does not refetch same regional volume and local source changes do',async t=>{
 const {dom,run,d,w}=setup();t.after(()=>dom.window.close());const calls=[];w.api=async(url,body)=>{calls.push([url,body]);return snapshot();};
 run('syncFinanceHistory()');await tick();
 run(`financePrefs.sale='jita:buy';syncFinanceHistory()`);await tick();assert.equal(calls.length,1);
 run(`financePrefs.sale='local:sell';syncFinanceHistory()`);await tick();assert(calls[1][0].includes('source=local'));
 assert(d.body.textContent.includes('Region containing C-N4OD'));
 run(`tradeData.settings.location={id:456,region_id:10000060,system_name:'Other'};syncFinanceHistory()`);await tick();assert.equal(calls.length,3);
 d.querySelector('[data-history-refresh]').click();await tick();assert.equal(calls[3][0],'/api/market/history/refresh');assert.equal(calls[3][1].type_id,11985);
});
test('late response for another product or region cannot replace current history',async t=>{
 const {dom,run,d,w}=setup();t.after(()=>dom.window.close());let first;w.api=()=>new Promise(r=>first=r);
 run('syncFinanceHistory()');assert.equal(d.querySelector('[data-finance-history]').getAttribute('aria-busy'),'true');
 w.api=async()=>snapshot({weekly_average:777});run(`financeContext.plan.product_id=12005;syncFinanceHistory()`);await tick();
 first(snapshot({weekly_average:999}));await tick();assert(d.body.textContent.includes('777 units / week'));assert(!d.body.textContent.includes('999 units / week'));
});
test('history failures are inline, do not throw, and cannot write HTML',async t=>{
 const {dom,run,d,w}=setup();t.after(()=>dom.window.close());w.api=async()=>{throw Error('<img src=x> unavailable');};
 run('syncFinanceHistory()');await tick();assert(d.body.textContent.includes('<img src=x> unavailable'));assert.equal(d.querySelector('img'),null);
 assert.equal(d.querySelector('[data-finance-history]').getAttribute('aria-busy'),'false');
});
