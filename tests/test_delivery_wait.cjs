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
 const notificationFixture={items:[],counts:{skills:0,jobs:0,pi:0,moons:0,data:0},task:{running:false},next_sync_at:9999999999,corporations:[],moons:[],preferences:{os_enabled:false,auto_refresh:true,personal:true,corporations:true,moon_days:3,categories:{skills:true,jobs:true,pi:true,moons:true},moon_owners:{}},claims:[]};
 const calls=[],scrolls=[];let currentWait=wait;
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 w.HTMLElement.prototype.scrollIntoView=function(){scrolls.push(this.id);};
 w.fetch=async (url,options)=>{
  calls.push(url);
  if(url==='/api/notifications')return {ok:true,json:async()=>notificationFixture};
  if(url==='/api/notifications/claim')return {ok:true,json:async()=>({items:notificationFixture.claims})};
  if(url==='/api/notifications/sent'){notificationFixture.receipts=JSON.parse(options.body).receipts;return {ok:true,json:async()=>({ok:true})};}
  if(url==='/api/notifications/preferences'){Object.assign(notificationFixture.preferences,JSON.parse(options.body));return {ok:true,json:async()=>notificationFixture.preferences};}
  if(url==='/api/state')return {ok:true,json:async()=>({...fixture,delivery_wait:currentWait})};
  if(url.startsWith('/api/plan?'))return currentWait?{ok:false,json:async()=>({error:'untranslated server fallback',delivery_wait:currentWait})}:{ok:true,json:async()=>({product_id:Number(new URL(url,w.location.href).searchParams.get('product_id')),activity:'manufacturing',summary:{items:1},stale_characters:[],calculated_at:1000})};
  throw Error('Unexpected request: '+url);
 };
 for(const script of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,script.getAttribute('src')),'utf8'));
 await tick();await tick();
 run('productId=22428;productName="Redeemer";activePlanId="saved-redeemer";$("#product-search").value="Redeemer";EveNumbers.set($("#target-quantity"),3);navigate("schedule");');
 await tick();
 return {dom,w,d,run,calls,scrolls,saved,fixture,notificationFixture,setWait:value=>{currentWait=value;}};
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

test('saved-plan shortcuts keep the scheduler open and retain options while discarding the old schedule',async t=>{
 const {w,d,run,fixture,calls}=await setup(null);t.after(()=>w.close());
 fixture.plans.push({...fixture.plans[0],id:'saved-salvation',name:'Salvation',product_name:'Salvation',product_id:92822,quantity:2});
 run('updatePlanControls()');
 const selector=d.querySelector('.plan-selector'),calculate=d.querySelector('#calculate'),form=d.querySelector('#schedule-form');
 form.elements.min_job_hours.value='24';form.elements.owned_only.checked=false;form.dispatchEvent(new w.Event('input',{bubbles:true}));
 run('scheduleResult={key:scheduleKey(),data:{}};scheduleSelected=99;');
 d.querySelector('[data-saved-shortcut="saved-salvation"]').click();await tick();await tick();
 assert.equal(run('view'),'schedule');assert.equal(run('activePlanId'),'saved-salvation');assert.equal(run('productId'),92822);assert.equal(run('plan.product_id'),92822);
 assert.equal(d.querySelector('.schedule-setup>.plan-selector'),selector);assert.equal(d.querySelector('#calculate'),calculate);
 assert.equal(d.querySelector('#product-search').value,'Salvation');assert.equal(d.querySelector('#target-quantity').value,'2');
 assert.equal(d.querySelector('#schedule-form').elements.min_job_hours.value,'24');assert.equal(d.querySelector('#schedule-form').elements.owned_only.checked,false);
 assert.equal(run('scheduleResult'),null);assert.equal(d.querySelector('#schedule-result').textContent,'');
 assert(d.querySelector('[data-view=schedule]').classList.contains('active'));
 const query=new URL(calls.find(p=>p.startsWith('/api/plan?')),w.location.href).searchParams;
 assert.equal(query.get('saved_plan_id'),'saved-salvation');assert.equal(query.get('quantity'),'2');
 assert.equal(d.querySelector('[data-saved-shortcut="saved-salvation"]').getAttribute('aria-pressed'),'true');
 // Calculate plan remains bound to the original selector after moving it.
 calculate.click();await tick();await tick();assert.equal(calls.filter(p=>p.startsWith('/api/plan?')).length,2);assert.equal(run('view'),'schedule');
});
test('every plan shortcut and the saved-plan Open action retain the current view even during an inventory wait',async t=>{
 const {w,d,run,fixture}=await setup();t.after(()=>w.close());
 fixture.plans.push({...fixture.plans[0],id:'saved-salvation',name:'Salvation',product_name:'Salvation',product_id:92822,quantity:2});
 run('updatePlanControls()');
 const selector=d.querySelector('.plan-selector');
 for(const view of ['schedule','queue','graph','shopping','inventory','blueprints','jobs','saved']){
  run('navigate('+JSON.stringify(view)+')');await tick();
  const id=run('activePlanId')==='saved-salvation'?'saved-redeemer':'saved-salvation';
  d.querySelector('[data-saved-shortcut="'+id+'"]').click();await tick();await tick();
  assert.equal(run('view'),view,view);assert.equal(run('activePlanId'),id,view);
  assert.equal(d.querySelector('.plan-selector'),selector);assert(d.querySelector('[data-view="'+view+'"]').classList.contains('active'),view);
  assert.equal(d.querySelector('[data-saved-shortcut="'+id+'"]').getAttribute('aria-pressed'),'true');
 }
 d.querySelector('[data-load-plan="saved-salvation"]').click();await tick();await tick();
 assert.equal(run('view'),'saved');assert.equal(run('activePlanId'),'saved-salvation');assert(d.querySelector('[data-load-plan="saved-salvation"]'));
});
test('cancelled dirty-plan switches leave the current view, target and unsaved inputs intact',async t=>{
 const {w,d,run,fixture,calls}=await setup(null);t.after(()=>w.close());
 fixture.plans.push({...fixture.plans[0],id:'saved-salvation',name:'Salvation',product_name:'Salvation',product_id:92822,quantity:2});run('updatePlanControls();dirty={inventory:true};');
 let prompts=0;w.confirm=()=>{prompts++;return false;};
 const selector=d.querySelector('.plan-selector'),before=calls.length;d.querySelector('#target-quantity').value='73';
 d.querySelector('[data-saved-shortcut="saved-salvation"]').click();await tick();
 assert.equal(prompts,1);assert.equal(calls.length,before);assert.equal(run('view'),'schedule');assert.equal(run('activePlanId'),'saved-redeemer');assert.equal(run('productId'),22428);assert.equal(run('dirty.inventory'),true);
 assert.equal(d.querySelector('.plan-selector'),selector);assert.equal(d.querySelector('#target-quantity').value,'73');
 w.confirm=()=>{prompts++;return true;};await run('openSavedPlan("saved-salvation")');await tick();
 assert.equal(prompts,2);assert.equal(run('view'),'schedule');assert.equal(run('activePlanId'),'saved-salvation');assert.equal(run('Object.keys(dirty).length'),0);
});

test('appearance and language controls work in Settings across repeated renders and launches',async t=>{
 const {w,d,run}=await setup(null);t.after(()=>w.close());
 assert.equal(d.querySelector('.sidebar [data-ui-language]'),null);assert.equal(d.querySelector('.sidebar [data-theme-toggle]'),null);
 run('openSettingsTab("appearance")');await tick();
 assert(d.querySelector('#settings-content [data-theme-toggle]'));assert.equal(d.querySelector('.plan-selector').hidden,true);
 const toggle=d.querySelector('[data-theme-toggle]');toggle.click();await tick();
 assert.equal(d.documentElement.dataset.theme,'light');assert.equal(toggle.getAttribute('aria-pressed'),'false');assert.equal(w.localStorage.getItem('eve-muhely-theme'),'light');
 d.querySelector('[data-ui-language=hu]').click();await tick();assert.equal(d.documentElement.lang,'hu');assert.equal(d.querySelector('#page-title').textContent,'Megjelenés és nyelv');
 run('navigate("jobs");openSettingsTab("appearance")');await tick();
 assert.equal(d.querySelector('[data-theme-toggle]').getAttribute('aria-pressed'),'false');assert.equal(d.querySelector('[data-ui-language=hu]').getAttribute('aria-pressed'),'true');
 d.querySelector('[data-ui-language=en]').click();await tick();assert.equal(d.querySelector('#page-title').textContent,'Appearance and language');assert.equal(w.localStorage.getItem('eve-muhely-language'),'en');
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#settings-content').textContent.replace('Magyar','')));
});

function notificationItem(id,corp=null,kind='job_ready'){
 return {id:'job:'+id,domain:'jobs:'+id,category:'jobs',kind,subject:'Item '+id,corporation_id:corp,scope_name:corp?'Corp A':'Personal',when:1000,checked_at:2000,reliable:true,character_name:'Test Pilot',receipt:'receipt-'+id,notification_id:'notification-'+id};
}
test('the notification hub keeps personal and corporation alerts separate from the production scope',async t=>{
 const {w,d,run,notificationFixture:n}=await setup(null);t.after(()=>w.close());
 n.items=[notificationItem(1),notificationItem(2,99),{...notificationItem(3),category:'skills',kind:'training_idle',subject:'Test Pilot'},{...notificationItem(4),category:'skills',kind:'training_soon',subject:'Test Pilot'},{...notificationItem(5),category:'pi',kind:'pi_idle',subject:'Planet'},{...notificationItem(6),category:'pi',kind:'pi_estimated',subject:'Planet'},{...notificationItem(7),category:'pi',kind:'pi_extractor',subject:'Planet'},{...notificationItem(8),category:'moons',kind:'moon_soon',subject:'Moon'}];n.corporations=[{id:99,name:'Corp A'}];n.counts.jobs=2;
 run('corporationId=99;openNotificationCenter()');await tick();
 assert.equal(d.querySelector('#page-title').textContent,'Notifications');assert(d.querySelector('[data-notification-open="job:1"]'));assert.equal(d.querySelector('[data-notification-open="job:2"]'),null);
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#view-content').textContent));
 d.querySelector('[data-notification-scope=corporations]').click();await tick();
 assert(d.querySelector('[data-notification-open="job:2"]'));assert.equal(d.querySelector('[data-notification-open="job:1"]'),null);assert.equal(run('corporationId'),99);
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#view-content').textContent));
 d.querySelector('[data-notification-category=data]').click();await tick();assert(d.querySelector('.empty').textContent.includes('No matching alerts'));
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#view-content').textContent));
});
test('OS delivery groups by owner and category and acknowledges only accepted notifications',async t=>{
 const {w,run,notificationFixture:n}=await setup(null);t.after(()=>w.close());
 n.preferences.os_enabled=true;n.preferences.auto_refresh=false;n.claims=[notificationItem(1),notificationItem(2),notificationItem(3,99)];n.items=n.claims;
 const sent=[];w.EveDesktop.active=true;w.EveDesktop.notificationStatus=async()=>({status:'authorized'});w.EveDesktop.notify=async body=>sent.push(body);
 await run('refreshNotifications()');assert.equal(sent.length,2);assert.equal(sent[0].scope,'personal');assert.equal(sent[1].scope,'99');assert(sent[0].body.includes('Item 1'));assert(sent[0].body.includes('Item 2'));assert(!sent[0].body.includes('Item 3'));
 assert.deepEqual(n.receipts,['receipt-3']);assert(!/[áéíóöőúüű]/i.test(sent.map(s=>s.title+s.body).join('')));
 n.receipts=null;w.EveDesktop.notify=async()=>{throw Error('denied');};await run('refreshNotifications()');assert.equal(n.receipts,null);assert.equal(n.items.length,3);
});
test('notification settings preserve unsaved preferences while saving moon ownership',async t=>{
 const {w,d,run,notificationFixture:n}=await setup(null);t.after(()=>w.close());
 n.moons=[{id:'moon1',name:'Test I - Moon 1'}];n.corporations=[{id:99,name:'Corp A'}];run('openSettingsTab("notifications")');await tick();
 const prefs=d.querySelector('#notification-preferences');prefs.elements.moon_days.value='7';prefs.dispatchEvent(new w.Event('input',{bubbles:true}));
 const owner=d.querySelector('[data-notification-moon=moon1]');owner.value='99';owner.dispatchEvent(new w.Event('change',{bubbles:true}));
 d.querySelector('#notification-moon-owners').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();
 assert.equal(n.preferences.moon_owners.moon1,99);assert.equal(d.querySelector('#notification-preferences').elements.moon_days.value,'7');assert.equal(run('dirty.notification_preferences'),true);
 prefs.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();
 assert.equal(n.preferences.moon_days,7);assert.equal(run('Object.keys(dirty).length'),0);assert(!/[áéíóöőúüű]/i.test(d.querySelector('#settings-content').textContent));
});
