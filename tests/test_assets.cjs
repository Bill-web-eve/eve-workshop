'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function fixture(){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[];
 const state={csrf:'test',version:'1.2.0',characters:[{id:1,name:'Alice'},{id:2,name:'Bob'}],corporations:[{id:99,name:'Corp A'},{id:98,name:'Corp B'}],production_characters:[],plans:[],jobs:[],settings:{source:'manual'},task:{running:false},sde:{buildNumber:1},recipe_count:1};
 const sources=[{id:1,name:'Alice',available:true,fetched:100,stale:false},{id:2,name:'Bob',available:true,fetched:100,stale:false}];
 const row=(name,id,owner=1,quantity=1)=>({name,type_id:id,owner_id:owner,owner_name:owner===1?'Alice':'Bob',quantity,location_id:6001,location_flag:'Hangar',state:'packaged'});
 const personal={sources,rows:Array.from({length:150},(_,i)=>row('Item '+String(i).padStart(3,'0'),1000+i,i%2+1,i+1))};
 personal.rows[140]={...personal.rows[140],name:'Needle <script>fake</script>',state:'singleton'};
 const corpA={sources:[{id:99,name:'Corp A',available:true,fetched:100}],rows:[{...row('Corp A asset',2000),owner_id:99,owner_name:'Corp A'}]};
 const corpB={sources:[{id:98,name:'Corp B',available:true,fetched:100}],rows:[{...row('Corp B asset',3000),owner_id:98,owner_name:'Corp B'}]};
 let assetsDelay=null,failAssets=false;
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 w.fetch=async url=>{
  calls.push(url);let value;
  if(url==='/api/state')value=state;
  else if(url==='/api/notifications')value={items:[],counts:{data:0},task:{running:false},corporations:[],moons:[],preferences:{os_enabled:false,categories:{intel:true}}};
  else if(url==='/api/intel/alerts')value={enabled:false,items:[]};
  else if(url.startsWith('/api/assets')){if(assetsDelay)await assetsDelay;if(failAssets)return {ok:false,json:async()=>({error:'Network unavailable'})};value=url.endsWith('99')?corpA:url.endsWith('98')?corpB:personal;}
  else throw Error('Unexpected request: '+url);
  return {ok:true,json:async()=>value};
 };
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();run('navigate("inventory")');await tick();
 return {w,d,run,calls,personal,delay:p=>{assetsDelay=p;},fail:value=>{failAssets=value;}};
}
test('full personal inventory works without a plan, searches all pages and copies plain item names',async t=>{
 const {w,d,run,calls}=await fixture();t.after(()=>w.close());
 assert(d.querySelector('[data-inventory-mode=personal]'));
 d.querySelector('[data-inventory-mode=personal]').click();await tick();await tick();
 assert.equal(d.querySelector('.plan-selector').hidden,true);
 assert.equal(d.querySelectorAll('.all-assets-table tbody tr').length,100);
 const input=d.querySelector('#asset-query');input.value='Needle';input.dispatchEvent(new w.Event('input'));await tick();
 assert.equal(d.querySelectorAll('.all-assets-table tbody tr').length,1);
 const row=d.querySelector('.all-assets-table tbody tr');assert(row.textContent.includes('Individual / assembled'));
 assert.equal(row.querySelector('script'),null);assert.equal(row.querySelector('[data-copy-item]').dataset.copyItem,'Needle <script>fake</script>');
 assert.equal(run('plan'),undefined);assert(!calls.some(url=>url.startsWith('/api/plan')));
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#view-content').textContent));
 let exported;w.csv=(rows,heads)=>{exported={rows,heads};};d.querySelector('#export-csv').click();assert.equal(exported.rows.length,1);assert.equal(exported.rows[0][0],'Needle <script>fake</script>');
});
test('character dropdowns and global numeric sorting work beyond the current page',async t=>{
 const {w,d}=await fixture();t.after(()=>w.close());d.querySelector('[data-inventory-mode=personal]').click();await tick();await tick();
 assert.equal(d.querySelector('.table-filters').hidden,true);
 d.querySelector('[data-asset-sort=quantity]').click();d.querySelector('[data-asset-sort=quantity]').click();
 assert.equal(d.querySelector('.all-assets-table tbody tr td:nth-child(3)').textContent,'150');
 const owner=d.querySelector('#asset-owner');owner.value='1';owner.dispatchEvent(new w.Event('change'));
 assert.equal(d.querySelectorAll('.all-assets-table tbody tr').length,75);
 assert([...d.querySelectorAll('.all-assets-table tbody tr td:nth-child(2)')].every(c=>c.textContent==='Alice'));
 d.querySelector('#asset-filters').click();assert.equal(d.querySelector('.table-filters').hidden,false);
 const filter=d.querySelector('[data-asset-owner-filter]');assert.equal(filter.tagName,'SELECT');assert.equal(filter.value,'1');
 filter.value='2';filter.dispatchEvent(new w.Event('change'));assert.equal(d.querySelector('#asset-owner').value,'2');
 d.querySelector('#asset-filters').click();assert.equal(d.querySelector('.table-filters').hidden,true);assert.equal(d.querySelectorAll('.all-assets-table tbody tr').length,75);
});
test('corporation selection stays independent of the production scope and never mixes personal assets',async t=>{
 const {w,d,run,calls}=await fixture();t.after(()=>w.close());run('corporationId=99;manufacturerId=1;activePlanId="existing";');
 d.querySelector('[data-inventory-mode=corporation]').click();await tick();await tick();
 assert(d.querySelector('.all-assets-table').textContent.includes('Corp A asset'));
 const select=d.querySelector('#asset-corporation');select.value='98';select.dispatchEvent(new w.Event('change'));await tick();await tick();
 const text=d.querySelector('.all-assets-table').textContent;assert(text.includes('Corp B asset'));assert(!text.includes('Corp A asset'));assert(!text.includes('Alice'));
 assert.equal(run('corporationId'),99);assert.equal(run('manufacturerId'),1);assert.equal(run('activePlanId'),'existing');
 d.querySelector('[data-inventory-mode=personal]').click();await tick();await tick();assert(d.querySelector('.all-assets-table').textContent.includes('Alice'));
 assert(calls.includes('/api/assets'));assert(!calls.includes('/api/assets?corporation_id=1'));
});
test('plan waiting for delivered assets does not block full inventory; dirty edits are protected',async t=>{
 const {w,d,run}=await fixture();t.after(()=>w.close());
 run('deliveryWait={retry_at:200,items:[],plan_name:"Waiting plan"};render();');
 assert(d.querySelector('.delivery-wait'));
 run('dirty={123:{quantity:5}};');d.querySelector('[data-inventory-mode=personal]').click();assert.equal(run('inventoryMode'),'plan');
 run('dirty={};');d.querySelector('[data-inventory-mode=personal]').click();await tick();await tick();assert(d.querySelector('.all-assets-table'));assert(!d.querySelector('.delivery-wait'));
});
test('loading and errors never expose data from another scope, and old responses cannot overwrite new ones',async t=>{
 const {w,d,run,delay}=await fixture();t.after(()=>w.close());
 let release;delay(new Promise(r=>{release=r;}));d.querySelector('[data-inventory-mode=personal]').click();
 d.querySelector('[data-inventory-mode=corporation]').click();release();await tick();await tick();
 assert.equal(run('assetData.key'),'corporation:99');assert(!d.querySelector('#asset-results').textContent.includes('Alice'));
});
test('failed asset loads remain visible and can be retried without changing production settings',async t=>{
 const {w,d,run,fail}=await fixture();t.after(()=>w.close());fail(true);
 d.querySelector('[data-inventory-mode=personal]').click();await tick();await tick();
 assert(d.querySelector('#asset-results').textContent.includes('Network unavailable'));assert.equal(d.querySelector('.all-assets-table'),null);
 fail(false);d.querySelector('#asset-reload').click();await tick();await tick();
 assert(d.querySelector('.all-assets-table'));assert.equal(run('corporationId'),null);assert.equal(run('state.settings.source'),'manual');
});
