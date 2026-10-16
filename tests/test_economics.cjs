const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
function setup(){
 const dom=new JSDOM('<body><main></main></body>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),context=dom.getInternalVMContext();
 const run=s=>vm.runInContext(s,context);
 run(`const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],esc=v=>String(v??''),verbatim=esc,itemName=esc,date=String;
 const EveTables={markup:(headers,rows)=>'<table><tbody>'+rows.join('')+'</tbody></table>'};const table=EveTables.markup;
 let view='queue',state={settings:{manufacturing:{system_id:1},reaction:{system_id:2}}},jitaMode='sell',jitaData={quotes:{1:{buy:'10',sell:'20'},2:{buy:'2',sell:'4'},3:{buy:'2',sell:'5'}}},jitaGroups=new Map();
 let moonData={settings:{fuel_block_id:2,fuel_block_price:'3',sales_tax:3,broker_fee:1},magmatic_gas:{id:3}};`);
 for(const f of ['costs.js','economics.js'])run(fs.readFileSync(__dirname+'/../static/'+f,'utf8'));
 return {dom,run,d:dom.window.document};
}
test('moon profit includes fuel, gas, rent, other and mode-dependent selling fees',()=>{
 const {dom,run,d}=setup();
 run(`jitaGroups.set('moon-production',[{id:1,quantity:10}]);$('main').innerHTML=moonEconomics([{fuel:5,online_fuel:1,gas:2,rent_isk:'10',other_cost_isk:'20'}]);applyEconomics();`);
 const value=k=>d.querySelector('[data-economic-value='+k+']').textContent;
 assert.equal(value('fuel'),'28,00 ISK');assert.equal(value('total'),'66,00 ISK');assert.equal(value('profit'),'134,00 ISK');
 run(`jitaMode='buy';applyEconomics();`);assert.equal(value('sales'),'3,00 ISK');assert.equal(value('total'),'55,00 ISK');assert.equal(value('profit'),'45,00 ISK');
 run(`jitaMode='sell';economicPanels.get('moon-production').moons[0].rent_isk='1000';applyEconomics();`);
 assert.equal(value('profit'),'-856,00 ISK');assert(d.querySelector('[data-economic-value=profit]').classList.contains('danger'));dom.window.close();
});
test('missing fuel quote never turns a partial total into a positive profit',()=>{
 const {dom,run,d}=setup();run(`jitaGroups.set('moon-production',[{id:1,quantity:10}]);delete jitaData.quotes[3];$('main').innerHTML=moonEconomics([{fuel:5,online_fuel:1,gas:2,rent_isk:'10',other_cost_isk:'20'}]);applyEconomics();`);
 assert.equal(d.querySelector('[data-economic-value=total]').textContent,'–');assert.equal(d.querySelector('[data-economic-value=profit]').textContent,'–');assert.match(d.querySelector('[data-economic-warning]').textContent,/Hiányzó üzemanyagár/);dom.window.close();
});
test('plan job costs add to materials; target buy and sell values remain independent of material mode',()=>{
 const {dom,run,d}=setup();run(`jitaGroups.set('plan-materials',[{id:2,quantity:10}]);$('main').innerHTML=planEconomics({product_id:1,quantity:3,queue:[]});jobCostKey=economicPanels.get('plan-materials').key;jobCostData={complete:true,cents:'500',rows:[]};applyEconomics();`);
 const value=k=>d.querySelector('[data-economic-value='+k+']').textContent;
 assert.equal(value('total'),'45,00 ISK');assert.equal(value('buy'),'30,00 ISK');assert.equal(value('sell'),'60,00 ISK');
 run(`jitaMode='buy';applyEconomics();`);assert.equal(value('jobs'),'5,00 ISK');assert.equal(value('total'),'25,00 ISK');assert.equal(value('buy'),'30,00 ISK');assert.equal(value('sell'),'60,00 ISK');
 run(`state.settings.manufacturing.system_id=99;$('main').innerHTML=planEconomics({product_id:1,quantity:3,queue:[]});applyEconomics();`);
 assert.equal(value('jobs'),'–');assert.equal(value('total'),'–');dom.window.close();
});
