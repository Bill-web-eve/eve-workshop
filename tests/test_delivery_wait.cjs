'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
const root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
const expiry=Date.parse('2099-10-18T15:42:56Z')/1000;
function pending(retry=expiry){return {plan_name:'Redeemer',retry_at:retry,items:['Caesarium Cadmide','Carbon Polymers','Fluxed Condensates','Prometium'].map((name,id)=>({id,name,character_name:'Test Pilot',assets_as_of:retry-3600,completed_at:retry-600}))};}
async function setup(wait=pending()){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 const saved={id:'saved-redeemer',name:'Redeemer',product_name:'Redeemer',product_id:22428,quantity:3,reserve_active:true,manufacturer_id:0};
 const fixture={csrf:'test',version:'1.0.0',corporations:[],plans:[saved],production_characters:[],characters:[],jobs:[],settings:{source:'eve'},task:{running:false},sde:{buildNumber:1},recipe_count:1,delivery_wait:wait};
 const calls=[],scrolls=[];let currentWait=wait;
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 w.HTMLElement.prototype.scrollIntoView=function(){scrolls.push(this.id);};
 w.fetch=async url=>{
  calls.push(url);
  if(url==='/api/state')return {ok:true,json:async()=>({...fixture,delivery_wait:currentWait})};
  if(url.startsWith('/api/plan?'))return currentWait?{ok:false,json:async()=>({error:'untranslated server fallback',delivery_wait:currentWait})}:{ok:true,json:async()=>({product_id:22428,activity:'manufacturing',summary:{items:1},stale_characters:[],calculated_at:1000})};
  throw Error('Unexpected request: '+url);
 };
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();
 run('productId=22428;productName="Redeemer";activePlanId="saved-redeemer";$("#product-search").value="Redeemer";EveNumbers.set($("#target-quantity"),3);navigate("schedule");');
 await tick();
 return {dom,w,d,run,calls,scrolls,saved,fixture,setWait:value=>{currentWait=value;}};
}
test('Calculate plan visibly reports the wait and exact local retry time from the scheduler',async t=>{
 const {dom,w,d,run,calls,scrolls,fixture}=await setup();t.after(()=>w.close());
 const selector=d.querySelector('.plan-selector'),button=d.querySelector('#calculate'),before=JSON.stringify(fixture.plans);
 button.click();await tick();await tick();
 assert.equal(calls.filter(p=>p.startsWith('/api/plan?')).length,1);
 const alert=d.querySelector('#global-error'),text=alert.textContent;
 assert.equal(alert.hidden,false);assert.equal(alert.getAttribute('role'),'alert');
 assert(text.includes('Plan Redeemer is waiting for an inventory update.'));
 assert(text.includes('Caesarium Cadmide, Carbon Polymers, Fluxed Condensates, Prometium'));
 const options={year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZoneName:'short'};
 assert(text.includes('Earliest refresh attempt: '+new Date(expiry*1000).toLocaleString('en-GB',options)+'.'),text);
 assert(text.includes('Your reservations are preserved.'));assert(text.includes('cache expiry does not guarantee new data.'));
 assert(!/[áéíóöőúüű]/i.test(text));assert.equal(button.disabled,false);assert.deepEqual(scrolls,['global-error']);
 assert.equal(JSON.stringify(fixture.plans),before);assert.equal(d.querySelector('.schedule-setup>.plan-selector'),selector);
 w.EveI18n.setLanguage('hu');await tick();assert(alert.textContent.includes('A(z) Redeemer terv készletfrissítésre vár.'));
 assert(alert.textContent.includes(new Date(expiry*1000).toLocaleString('hu-HU',options)));
 w.EveI18n.setLanguage('en');await tick();assert.equal(alert.textContent,text);
 // The same click in the production view shows both the alert and detailed wait.
 run('navigate("queue")');button.click();await tick();await tick();
 const detail=d.querySelector('.delivery-wait');assert(detail);assert(detail.textContent.includes('Earliest refresh attempt:'));assert(detail.textContent.includes('2099'));assert(!/[áéíóöőúüű]/i.test(detail.textContent));
 assert.equal(d.querySelector('#calculate'),button);
});
test('expired caches allow retry now, dynamic names stay plain text, and fresh data clears the error',async t=>{
 const wait=pending(1000);wait.plan_name='Plan <img src=x onerror=alert(1)>.';wait.items[0].name='Raw <script>alert(1)</script>';
 const {w,d,run,setWait,scrolls}=await setup(wait);t.after(()=>w.close());
 await run('calculate(false)');await tick();
 const alert=d.querySelector('#global-error');assert(!alert.hidden);assert(alert.textContent.includes('you can try refreshing EVE data now.'));assert(alert.textContent.includes(wait.plan_name));assert(alert.textContent.includes(wait.items[0].name));assert.equal(alert.querySelector('img,script'),null);assert.deepEqual(scrolls,[]);
 setWait(null);await run('calculate()');await tick();
 assert(alert.hidden);assert.equal(alert.textContent,'');assert.equal(run('plan.product_id'),22428);assert.equal(run('deliveryWait'),null);assert.equal(d.querySelector('#calculate').disabled,false);
 assert.equal(run('activePlanId'),'saved-redeemer');
});
