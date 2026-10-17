'use strict';
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const fmt = n => new Intl.NumberFormat('hu-HU', {maximumFractionDigits: 0}).format(n || 0);
const hours = n => new Intl.NumberFormat('hu-HU', {maximumFractionDigits: 1}).format((n || 0) / 3600);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const verbatim=value=>`<span data-i18n-skip>${esc(value)}</span>`;
const confirmUI=message=>confirm(EveI18n.t(message));
const date = n => n ? EveI18n.date(n * 1000, {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : 'Még nem frissült';
let state, plan, productId = null, productName = '', view = 'queue', dirty = {}, searchTimer, taskTimer, lastTaskFinished;
let planGeneration = 0;
let blueprintDetailId = null;
let activePlanId = null, reservationDetailId = null;
let corporationId=null,manufacturerId=0,productActivity=null;
const targetQuantity=()=>EveNumbers.parse($('#target-quantity').value);
const manufacturerValue=()=>manufacturerId?String(manufacturerId):'manual';
let graphOptions={purchases:false,covered:false}, graphSelected=null, graphZoom=.75;
let graphExpanded=false;
let deliveryWait=null,deliveryTimer=null,deliveryRetryAfter=0;
let shoppingMode="current",shoppingData=null,shoppingRequest=null,shoppingRevision=0;
function scoped(path){return corporationId?path+(path.includes('?')?'&':'?')+'corporation_id='+encodeURIComponent(corporationId):path;}
async function setProductionScope(id){
  if((id||null)===corporationId)return;
  if(Object.keys(dirty).length){$('#production-scope').value=corporationId||'';return error('Előbb alkalmazd a még nem mentett készlet- vagy blueprintmódosításokat.');}
  planGeneration++;corporationId=id||null;manufacturerId=0;activePlanId=null;reservationDetailId=null;plan=null;graphSelected=null;blueprintDetailId=null;deliveryWait=null;
  const generation=planGeneration;
  $('#queue-count').textContent='–';
  $('#view-content').innerHTML=empty('A kiválasztott készlet betöltése…');
  error('');
  try{
    await reloadState();if(generation!==planGeneration)return;
    if(productId&&view!=='saved')await calculate(false);
    else{
      localStorage.setItem('eve-muhely-last-plan',JSON.stringify({id:productId,name:productName,quantity:targetQuantity(),saved_plan_id:null,corporation_id:corporationId,manufacturer_id:manufacturerId,activity:productActivity}));
      render();
    }
  }catch(e){if(generation===planGeneration)error(e.message);}
}

async function api(path, body) {
  const options = body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':state?.csrf || ''}, body:JSON.stringify(body)};
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok){const failure=new Error(result.error || 'A kérés nem sikerült.');failure.delivery_wait=result.delivery_wait;throw failure;}
  return result;
}
function error(message) { const el=$('#global-error'); el.textContent=message; el.hidden=!message; }
function toast(message) { const el=$('#toast'); el.textContent=message; el.hidden=false; setTimeout(()=>el.hidden=true,3500); }
function empty(title, description='') { return `<div class="empty"><div class="empty-icon">◈</div><h2>${esc(title)}</h2><p>${esc(description)}</p></div>`; }
function table(headers, rows, cls='') { return EveTables.markup(headers,rows,cls,JSON.stringify([view,corporationId,view==='shopping'?shoppingMode:'',cls,headers])); }
function panel(title, note, body, copyValue=null) { const heading=typeof title==='object'?verbatim(title.name)+esc(title.suffix):copyValue&&title.startsWith(copyValue)?itemName(copyValue)+esc(title.slice(copyValue.length)):esc(title);return `<div class="panel"><div class="panel-head"><h2>${heading}</h2><small>${esc(note)}</small></div>${body}</div>`; }
function itemName(name){
  if(name==null||name==='–')return esc(name);
  return `<button type="button" class="copy-item-name" data-copy-item="${esc(name)}" aria-label="${esc(name)} – Név másolása" title="Név másolása: ${esc(name)}">${esc(name)}</button>`;
}
async function copyItemName(name){
  try{
    let copied=false;
    if(navigator.clipboard?.writeText){try{await navigator.clipboard.writeText(name);copied=true;}catch{}}
    if(!copied){
      const active=document.activeElement,selection=document.getSelection();
      const ranges=selection?[...Array(selection.rangeCount)].map((_,i)=>selection.getRangeAt(i).cloneRange()):[];
      const inputSelection=active&&typeof active.selectionStart==='number'?[active.selectionStart,active.selectionEnd,active.selectionDirection]:null;
      const area=document.createElement('textarea');area.className='copy-item-fallback';area.value=name;area.setAttribute('readonly','');area.setAttribute('aria-hidden','true');
      document.body.append(area);
      try{area.select();copied=document.execCommand('copy');}
      finally{
        area.remove();if(active?.isConnected)active.focus({preventScroll:true});
        if(inputSelection)active.setSelectionRange(...inputSelection);
        else if(selection){selection.removeAllRanges();ranges.forEach(range=>selection.addRange(range));}
      }
      if(!copied)throw new Error('clipboard');
    }
    toast('Másolva: '+name);
  }catch{toast('A név másolását a böngésző nem engedte.');}
}
// Capture the canonical name before an existing detail/search action rerenders.
// Only text/plain is written; item IDs, counts and visible styling stay out.
document.addEventListener('click',event=>{
  const target=event.target.closest?.('[data-copy-item]');
  if(target&&event.button===0)void copyItemName(target.dataset.copyItem);
},true);
document.addEventListener('keydown',event=>{
  const target=event.target.closest?.('.graph-node[data-copy-item]');
  if(target&&!event.repeat&&['Enter',' '].includes(event.key))void copyItemName(target.dataset.copyItem);
},true);
function planLabel(saved){const product=saved.product_name||state?.plans.find(p=>p.id===saved.id)?.product_name;return saved.name===product?itemName(product):verbatim(saved.name);}
function scopedPlans(){return state.plans.filter(p=>(p.corporation_id??null)===corporationId);}
function badge(row) { return `<span class="badge ${row.activity==='reaction'?'reaction':'manufacturing'}">${row.activity==='reaction'?'Reakció':'Gyártás'}</span>`; }
function batchText(row) { return row.batches.map(g=>`${fmt(g.count)} × ${fmt(g.runs)} run`).join(' + '); }
function item(row) { return `<div class="item-name">${itemName(row.name)}<small>${row.id}</small></div>`; }
function characterCell(id) { const name=state.characters.find(c=>c.id===id)?.name||String(id||'–');return `<td data-filter-value="${esc(name)}">${esc(name)}</td>`; }
function actions(html='') { $('#view-actions').innerHTML=`<div class="actions">${html}</div>`; }
function exportButton(label='CSV mentése') { return `<button class="button compact" id="export-csv">↓ ${label}</button>`; }
function setHead(eyebrow,title,description) { $('#page-eyebrow').textContent=eyebrow; $('#page-title').textContent=title; $('#page-description').textContent=description; }

async function reloadState() {
  if(!state&&corporationId){
    const initial=await api('/api/state');
    if(!initial.corporations.some(c=>c.id===corporationId)){corporationId=null;activePlanId=null;productId=null;productName='';}
  }
  const requestedScope=corporationId,nextState=await api(scoped('/api/state'));
  if(requestedScope!==corporationId)return;
  state=nextState;corporationData=null;
  shoppingData=null;shoppingRevision++;
  deliveryWait=state.delivery_wait||null;scheduleDeliveryCheck();
  if(activePlanId && !state.plans.some(p=>p.id===activePlanId&&(p.corporation_id??null)===corporationId)) activePlanId=null;
  updatePlanControls();
  $('#version').textContent=state.version;
  $('#footer-scope').textContent=corporationId?'Corp: '+state.scope_label:'Személyes készlet';
  $('#sde-side').textContent=`SDE ${state.sde.buildNumber} · ${fmt(state.recipe_count)} termék`;
  const eve=state.settings.source==='eve';
  $('#source-pill').textContent=corporationId?'Corp: '+state.scope_label:eve?'Személyes EVE-készlet':'Kézi készlet'; $('#source-pill').classList.toggle('eve',eve);
  $('#connection-dot').classList.toggle('online',state.characters.length>0);
  $('#sync').disabled=state.task.running;
  const task=$('#task-banner'); task.hidden=!state.task.running;
  if(state.task.running) { task.textContent=state.task.message; scheduleTaskPoll(); }
  return state;
}
function scheduleDeliveryCheck(){
  clearTimeout(deliveryTimer);if(!deliveryWait)return;
  const next=Math.max(deliveryWait.retry_at*1000,deliveryRetryAfter);
  const delay=document.hidden||state.task.running?60000:Math.min(60000,Math.max(1000,next-Date.now()));
  deliveryTimer=setTimeout(async()=>{
    if(!deliveryWait)return;
    const now=Date.now();
    if(!document.hidden&&!state.task.running&&!Object.keys(dirty).length&&now>=deliveryWait.retry_at*1000&&now>=deliveryRetryAfter){
      deliveryRetryAfter=now+60000;await startTask('/api/sync');
    }
    scheduleDeliveryCheck();
  },delay);
}
function deliveryTimestamp(value){return value?EveI18n.date(value*1000,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'}):'–';}
function deliveryWaitMarkup(wait){
  const retry=wait.retry_at;
  return `<div class="banner delivery-wait"><strong>Készletfrissítésre várunk${wait.plan_name?' · '+esc(wait.plan_name):''}</strong><p>A jobok már át vannak véve, de az EVE még az átvétel előtti készletet adja vissza. Az ismételt frissítés a gyorsítótár lejártáig ezt nem változtatja meg.</p><p><strong>Új adat legkorábban: ${esc(date(retry))}</strong>. Ha ez az ablak előtérben marad, a lejárat után automatikusan újra próbáljuk.</p>${table(['Anyag','Karakter','Készletpillanatkép','Job átvétele'],wait.items.map(i=>`<tr><td>${itemName(i.name)}</td><td>${esc(i.character_name||i.character_id||'–')}</td><td data-sort-value="${i.assets_as_of??''}">${esc(deliveryTimestamp(i.assets_as_of))}</td><td data-sort-value="${i.completed_at??''}">${esc(deliveryTimestamp(i.completed_at))}</td></tr>`))}<p>A mentett tervek és foglalások megmaradnak. Az átvett kimenetet nem adjuk hozzá még egyszer a készlethez. Az időpont a CCP által jelzett lejárat; nem garantálja, hogy rögtön új adat érkezik.</p></div>`;
}
function renderDeliveryWait(content){
  setHead('EVE-KÉSZLET','Az átvett jobok készletadata még frissül','A számítást az új EVE-készlet megérkezése után folytatjuk.');
  $('#plan-status').hidden=true;actions('<button id="delivery-refresh" class="button compact">EVE-adatok ellenőrzése</button>');
  content.innerHTML=(view==='shopping'?shoppingTabs():'')+deliveryWaitMarkup(deliveryWait);
  if(view==='shopping')bindShoppingTabs();
  $('#delivery-refresh').disabled=state.task.running;
  $('#delivery-refresh').onclick=()=>startTask('/api/sync');
}
function renderPlanShortcuts(){
  const target=$('#saved-plan-shortcuts'),plans=scopedPlans();
  target.innerHTML='<span>Mentett tervek</span>'+plans.map(p=>`<button data-saved-shortcut="${esc(p.id)}" class="${p.id===activePlanId?'selected':''}" aria-pressed="${p.id===activePlanId}" title="${esc(p.product_name)} · ${fmt(p.quantity)} db">${verbatim(p.name)} · ${fmt(p.quantity)} db</button>`).join('')+(plans.length?'':'<span>Ebben a gyártási körben még nincs mentett terv</span>');
  $$('[data-saved-shortcut]').forEach(el=>el.onclick=()=>openSavedPlan(el.dataset.savedShortcut));
}
async function openSavedPlan(id){
  const saved=state.plans.find(p=>p.id===id);if(!saved)return;
  if(!navigate('queue'))return;
  planGeneration++;corporationId=saved.corporation_id??null;plan=null;$('#view-content').innerHTML=empty('A mentett terv saját készletének betöltése…');
  activePlanId=saved.id;productId=saved.product_id;productName=saved.product_name;
  $('#product-search').value=productName;EveNumbers.set($('#target-quantity'),saved.quantity);manufacturerId=saved.manufacturer_id??0;productActivity=saved.activity||null;
  $('#search-results').hidden=true;updatePlanControls();await calculate();
}
function updatePlanControls() {
  if(state)renderPlanShortcuts();
  if(state){
    $('#production-scope').innerHTML='<option value="">Személyes gyártás</option>'+state.corporations.map(c=>`<option value="${c.id}">Corp gyártás · ${esc(c.name)}${c.ready?'':' · frissítés szükséges'}</option>`).join('');
    $('#production-scope').value=corporationId||'';
    $('#manufacturer').innerHTML='<option value="manual">Válassz karaktert · addig kézi időbecslés</option>'+state.production_characters.map(c=>`<option data-i18n-name="${esc(c.name)}" value="${c.id}">${esc(c.name)}${c.available?'':' · nincs skilladat'}</option>`).join('');
    if(manufacturerId&&!state.production_characters.some(c=>c.id===manufacturerId))$('#manufacturer').insertAdjacentHTML('beforeend',`<option value="${manufacturerId}">Nem elérhető karakter · ${manufacturerId}</option>`);
    $('#manufacturer').value=manufacturerValue();
    $('#target-quantity').dataset.numberMax=productActivity==='manufacturing'?'1000000':'100000000';EveNumbers.validate($('#target-quantity'));
    $('#scope-hint').textContent=corporationId?'Csak '+state.scope_label+' készlete és jobjai.':'Csak személyes készlet és jobok; corp készlet nélkül.';
  }
  updateReadyJobs();
  const target=$('#product-search');
  if(productId&&productName&&target.value===productName){target.dataset.copyItem=productName;target.title='Kattintás: terméknév másolása';}
  else{delete target.dataset.copyItem;target.removeAttribute('title');}
  $('#save-plan').textContent=activePlanId?'↻ Terv és foglalás frissítése':'＋ Terv mentése és foglalás';
  $('#save-plan').title='Mentés ide: '+(corporationId?'Corp · '+state.scope_label:'Személyes');
  $('#new-plan').hidden=!activePlanId;
}
function scheduleTaskPoll() {
  clearTimeout(taskTimer);
  taskTimer=setTimeout(async()=>{
    try {
      await reloadState();
      if(!state.task.running && state.task.finished!==lastTaskFinished) {
        lastTaskFinished=state.task.finished; toast(state.task.message);
        if(!['skills','pi'].includes(state.task.kind) && state.task.results.some(r=>!r.ok)) error(state.task.message);
        if(state.task.kind==='corporations'){corporationData=null;if(view==='corporations')await refreshCorporations();else await calculate(false);}
        else if(state.task.kind==='skills') await refreshSkills();
        else if(state.task.kind==='pi')await refreshPI();
      else if(['moons','extractions'].includes(state.task.kind))await refreshMoons();
        else {skillData=null;piData=null;moonData=null;await calculate(false);}
      }
    } catch(e) { error(e.message); }
  },1200);
}
async function calculate(refreshState=true) {
  if(Object.keys(dirty).length && !confirmUI('Az új számítás eldobja a még nem alkalmazott módosításokat. Folytatod?')) return;
  const generation=++planGeneration;
  const targetId=productId, targetName=productName, quantity=targetQuantity();
  $('#calculate').disabled=true;
  error('');
  try {
    if(refreshState) await reloadState();
    if(generation!==planGeneration)return;
    if(activePlanId && !state.plans.some(p=>p.id===activePlanId&&p.product_id===targetId))activePlanId=null;
    const owner=activePlanId;
    const next=await api(scoped(`/api/plan?product_id=${encodeURIComponent(targetId)}&quantity=${encodeURIComponent(quantity)}${owner?'&saved_plan_id='+encodeURIComponent(owner):''}&manufacturer_id=${encodeURIComponent(manufacturerValue())}`));
    if(generation!==planGeneration) return;
    plan=next;productActivity=next.activity; dirty={};
    updatePlanControls();
    localStorage.setItem('eve-muhely-last-plan',JSON.stringify({id:targetId,name:targetName,quantity,saved_plan_id:owner,corporation_id:corporationId,manufacturer_id:manufacturerId,activity:productActivity}));
    $('#calculated-at').textContent='Számítás: '+date(plan.calculated_at);
    $('#queue-count').textContent=plan.summary.items;
    const status=$('#plan-status');
    status.hidden=!plan.stale_characters.length;
    status.className='banner warn';
    status.textContent='Korábbi EVE-adatokból számolunk: '+plan.stale_characters.join(', ')+'. Frissítsd az EVE-adatokat; a legutóbbi sikeres pillanatkép addig megmarad.';
    render();
    return next;
  } catch(e) {
    if(generation!==planGeneration) return;
    plan=null;
    if(e.delivery_wait){deliveryWait=e.delivery_wait;scheduleDeliveryCheck();error('');}else error(e.message);
    $('#queue-count').textContent='–';
    $('#calculated-at').textContent='A számítás nem frissült';
    $('#plan-status').hidden=true;
    render();
    return null;
  } finally { if(generation===planGeneration) $('#calculate').disabled=false; }
}
function navigate(next) {
  if(Object.keys(dirty).length && !confirmUI('Vannak még nem alkalmazott módosítások. Elhagyod ezt az oldalt?')) return false;
  if(view==='moons'){moonEditing=false;moonSystemGeneration++;moonSearchGeneration++;clearTimeout(moonSearchTimer);}
  view=next; dirty={};
  clearTimeout(skillTimer);
  clearTimeout(piTimer);
  if(['skills','pi'].includes(next))error('');
  $$('.nav').forEach(n=>n.classList.toggle('active',n.dataset.view===view));
  const names={queue:'Gyártási terv',graph:'Gyártási gráf',shopping:'Alapanyaghiány',inventory:'Készlet',blueprints:'Blueprint',jobs:'Folyamatban',skills:'Skillek és tanulás',pi:'Bolygók és PI',moons:'Holdak és kitermelés',corporations:'Corporationok',settings:'Struktúrák és bónuszok',connection:'EVE-kapcsolat',saved:'Mentett tervek'};
  $('#breadcrumb').textContent='Műhely / '+names[view]; render();return true;
}
function render() {
  if(!state) return;
  if(view==='settings'&&dirty.facilities&&$('#settings-form'))return;
  if(view==='moons'&&(moonEditing&&$('#moon-form')||dirty.moon_settings&&$('#moon-settings')||dirty.moon_fuel&&$('#moon-fuel-settings')||dirty.moon_crystals&&$('#crystal-settings')))return;
  const content=$('#view-content'); actions();
  $('.plan-selector').hidden=['skills','pi','corporations','moons'].includes(view);
  $('#plan-status').hidden=!plan?.stale_characters.length;
  if(view==='skills') return renderSkills(content);
  if(view==='pi') return renderPI(content);
  if(view==='moons')return renderMoons(content);
  if(view==='corporations')return renderCorporations(content);
  if(view==='settings') return renderSettings(content);
  if(view==='connection') return renderConnection(content);
  if(view==='saved') return renderSaved(content);
  if(view==='jobs'){renderJobs(content);if(corporationId)content.insertAdjacentHTML('afterbegin',scopeBanner());return;}
  if(view==='shopping'&&shoppingMode==='all')return renderAllShopping(content);
  if(!plan&&deliveryWait)return renderDeliveryWait(content);
  if(view==='shopping'&&!plan){
    setHead('BESZERZÉS','Alapanyaghiány','Válassz tervet, vagy nézd meg az összes mentett terv hiányát.');
    content.innerHTML=shoppingTabs()+empty('A kiválasztott terv most nem számolható','Az összes mentett terv nézet külön is megnyitható.');bindShoppingTabs();return;
  }
  if(!plan) {
    setHead('GYÁRTÁSTERVEZŐ','Válassz terméket és készletforrást','A kapcsolatot és a struktúrabeállításokat a bal oldali menüben találod.');
    content.innerHTML=empty('A számításhoz még adatok szükségesek','Kézi készlettel EVE-belépés nélkül is tervezhetsz. EVE-módban adj hozzá karaktert, és frissítsd az adatait.');
    return;
  }
  if(view==='queue') renderQueue(content);
  if(view==='graph') renderGraph(content);
  if(view==='shopping') renderShopping(content);
  if(view==='inventory') renderInventory(content);
  if(view==='blueprints') renderBlueprints(content);
  if(!(view==='shopping'&&shoppingMode==='all'))renderReservationContext(content);
  if(corporationId&&!(view==='shopping'&&shoppingMode==='all'))content.insertAdjacentHTML('afterbegin',scopeBanner());
  if(state.settings.source==='manual' && state.characters.length) {
    content.insertAdjacentHTML('afterbegin','<div class="banner warn stock-source-notice"><div><strong>A terv kézi készlettel számol.</strong><br>A letöltött személyes EVE-készletet és a jobok kimenetét jelenleg nem vonja le.</div><button class="button compact" id="enable-eve-stock">Személyes EVE-készlet használata</button></div>');
    $('#enable-eve-stock').onclick=async()=>{
      try {
        if(Object.keys(dirty).length) throw new Error('A készletforrás váltása előtt alkalmazd a beírt módosításokat.');
        await api('/api/settings',{source:'eve'});await calculate();toast('A készletforrás most személyes EVE-készlet.');
      }catch(e){error(e.message);}
    };
  }
}
function scopeBanner(){return `<div class="banner"><strong>Corp gyártás · ${esc(state.scope_label)}</strong><div>Kizárólag ennek a corporationnek a készlete, jobjai, blueprintjei és saját kézi beállításai számítanak. A személyes készlet és más corporation készlete elkülönül.</div></div>`;}
function renderReservationContext(content) {
  const saved=plan.saved_plan, count=plan.reservation_summary.other_plan_count;
  if(!saved&&!count)return;
  let message=saved?`<strong>Mentett terv: ${planLabel(saved)} · ${fmt(plan.quantity)} db</strong><br>${saved.reserve_active?'A saját foglalását felhasználhatja.':'Ennek a tervnek a foglalása fel van oldva.'}`:
    '<strong>Új, még nem mentett terv</strong>';
  if(count)message+=`<div>${fmt(count)} másik aktív terv foglalását levontuk az elérhető készletből és jobkimenetekből.</div>`;
  if(saved?.preview_changed)message+='<div class="warning-text">Módosított mennyiség vagy gyártó karakter előnézete. A Terv és foglalás frissítése gombbal érvényesítheted.'+(count?' A későbbi tervek kiosztása is változhat.':'')+'</div>';
  content.insertAdjacentHTML('afterbegin',`<div class="banner reservation-context"><div>${message}</div><button class="button compact" id="show-saved-plans">Foglalások megtekintése</button></div>`);
  $('#show-saved-plans').onclick=()=>navigate('saved');
}
function productionTime(row){
  const p=row.producer;if(!p)return '–';
  const details=[...p.bonuses.map(b=>`${b.name} ${b.level}: ${b.percent_per_level*b.level}%`),...p.missing_skills.map(m=>`${m.name}: ${m.active}/${m.required}`),p.warning].filter(Boolean).join(' · ');
  return `<span class="badge ${p.status==='verified'?'good':'warn'}" title="${esc(details)}">${p.name?verbatim(p.name):esc('Kézi becslés')}</span>`;
}
function blueprintSupply(row){return row.unit==='run'?`${fmt(Math.ceil(row.buy/(row.copy_runs||1)))} db, ${fmt(row.copy_runs||1)} run/BPC mellett`:row.category==='Reakcióformula'?'Beszerzendő, nem másolható':'–';}
function renderQueue(content) {
  setHead('GYÁRTÁSI SORREND','A hátralévő munkák','Az alapreakcióktól a kész termékig, a készlet és az elindított jobok levonásával.');
  actions(exportButton());
  const s=plan.summary;
  content.innerHTML=`<div class="metrics"><div class="metric"><div class="metric-label">Gyártandó tételek</div><strong>${fmt(s.items)}</strong><small>termék</small></div><div class="metric"><div class="metric-label">Elindítandó jobok</div><strong>${fmt(s.jobs)}</strong><small>job</small></div><div class="metric"><div class="metric-label">Hátralévő runok</div><strong>${fmt(s.runs)}</strong><small>run</small></div><div class="metric"><div class="metric-label">Összes munkaóra</div><strong>${hours(s.seconds)}</strong><small>óra</small></div></div>`;
  const materialValues=EveCosts.materials(plan);
  content.innerHTML+=costSummary('plan-materials',materialValues,'A gyártás anyagköltsége','A hátralévő gyártáshoz felhasznált anyagok Jita-értéke, a meglévő és folyamatban lévő bemenetekkel együtt. A helyben gyártott köztes terméket nem számoljuk el még egyszer az alapanyagai mellett. A job cost külön sorban jelenik meg a rendszer indexével és a struktúra díjaival.',true,planEconomics(plan));
  const rows=plan.queue.map(r=>`<tr><td><span class="stage">${r.stage}</span></td><td>${item(r)}</td><td>${badge(r)}</td><td class="num">${fmt(r.available)}</td><td class="num">${fmt(r.wip)}</td><td class="num">${fmt(r.missing)}</td><td class="num"><strong>${fmt(r.runs)}</strong></td><td class="num">${fmt(r.manufactured)}</td><td class="num">${fmt(r.jobs)}<div class="batch-note">${esc(batchText(r))}</div></td><td><span class="badge ${r.warning.length?'warn':'good'}" title="${esc(r.warning.join(' '))}">${r.parameters.kind}${r.warning.length?' · ellenőrizd':''}</span></td><td>${productionTime(r)}</td><td class="num" data-sort-value="${r.seconds}">${hours(r.seconds)}</td></tr>`);
  const target=plan.rows.find(r=>r.id===plan.product_id);
  if(target && (target.used_stock || target.used_wip || target.manual_reserved)) {
    const coverage=`A ${fmt(plan.quantity)} db ${plan.name} célból ${fmt(target.used_stock)} db-ot meglévő késztermék, ${fmt(target.used_wip)} db-ot folyamatban lévő gyártás fedez. ${fmt(target.missing)} db van még hátra.`;
    content.innerHTML+=`<div class="banner reservation-context"><div><strong>${esc(coverage).replace(esc(plan.name),itemName(plan.name))}</strong>${target.manual_reserved?`<div>A kész ${itemName(plan.name)} készletéből ${fmt(target.manual_reserved)} db kézzel félretéve; ezt a terv nem használja fel.</div>`:''}<div>Ha a meglévő késztermékeket megtartanád, a Készlet oldalon a Másra foglalva (kézi) mezőben teheted félre őket. Ez minden tervre érvényes.</div></div><button class="button compact" id="target-stock-settings">Késztermék-készlet beállítása</button></div>`;
  }
  content.innerHTML+=panel(`${plan.name} · ${fmt(plan.quantity)} db`,`${fmt(s.items)} tétel a hátralévő gyártásban`, rows.length?table(['Szint','Termék','Tevékenység','Elérhető (db)','Folyamatban (db)','Hiány (db)','Run','Kimenet (db)','Jobfelosztás','Blueprint','Gyártó / skillidő','Munkaóra'],rows,'queue-table'):empty('Nincs több gyártandó tétel','A célmennyiséget a meglévő készlet és a folyamatban lévő kimenetek fedezik.'),plan.name);
  content.innerHTML+='<p class="footnote">A szint a receptfüggőségeket jelzi: az alacsonyabb szintű tételekkel kezdd. A munkaórák összege nem naptári átfutási idő; a jobok párhuzamosan is futhatnak. A kézi vagy hiányzó blueprintadatokat a Blueprint oldalon ellenőrizd.</p>';
  if(plan.queue.some(r=>r.producer?.status!=='verified'))content.insertAdjacentHTML('afterbegin','<div class="banner warn">Egyes gyártási idők becslések: hiányzó skilladat, hiányzó gyártási skill vagy kézi időszorzó miatt. A Gyártó / skillidő oszlop jelzi a forrást. A Skillek és tanulás menüben engedélyezheted és frissítheted a karakteradatokat.</div>');
  bindJita([...materialValues.map(r=>r.id),plan.product_id]);bindEconomics();
  $('#export-csv').onclick=()=>csv(plan.queue.map(r=>[r.stage,r.name,r.available,r.wip,r.missing,r.runs,r.manufactured,r.jobs,batchText(r),r.producer?.name||'Kézi becslés',r.seconds]),['Szint','Termék','Elérhető (db)','Folyamatban (db)','Hiány (db)','Run','Kimenet (db)','Jobok','Jobfelosztás','Gyártó karakter','Idő (másodperc)'],'gyartasi-lista');
  if($('#target-stock-settings'))$('#target-stock-settings').onclick=()=>{
    if(!navigate('inventory'))return;
    $('#row-filter').value=plan.name;
    $('#row-filter').dispatchEvent(new Event('input'));
  };
}
function renderGraph(content) {
  setHead('GYÁRTÁSI KAPCSOLATOK','A terv gyártási gráfja','Balról jobbra: reakciók és komponensek → kész termék. A nyilak az anyagok útját mutatják.');
  actions('<button class="button compact" id="graph-list">Táblázatos lista</button>');
  const graph=EvePlanGraph.build(plan,graphOptions);
  if(!graph.nodes.some(n=>n.id===graphSelected))graphSelected=null;
  const labels={reaction:'Reakció',manufacturing:'Gyártás',buy:'Beszerzés',covered:'Fedezett'};
  const cards=graph.nodes.map(n=>{
    const lines=EvePlanGraph.wrap(n.name), detail=n.runs?`${fmt(n.runs)} run`:n.buy?`${fmt(n.buy)} db hiány`:'Készlet / folyamatban';
    const output=n.runs?`Gyártandó: ${fmt(n.manufactured)} db · Hiány: ${fmt(n.missing)} db`:`Szükséglet: ${fmt(n.required)} db`;
    return `<g class="graph-node ${n.kind}${n.id===plan.product_id?' graph-target':''}" data-graph-id="${n.id}" data-copy-item="${esc(n.name)}" transform="translate(${n.x} ${n.y})" role="button" tabindex="0" aria-pressed="false" aria-label="${esc(n.name+' – '+labels[n.kind]+', '+detail)}"><title>${esc(n.name+'\n'+output+'\nElérhető: '+fmt(n.available)+' db; folyamatban: '+fmt(n.wip)+' db'+(n.warning.length?'\n'+n.warning.join(' '):''))}</title><rect class="graph-card" width="${n.width}" height="${n.height}" rx="10"/><rect class="graph-stripe" width="5" height="${n.height-20}" x="0" y="10" rx="2"/><text class="graph-kind" x="16" y="23">${n.id===plan.product_id?'CÉLTERMÉK · ':''}${labels[n.kind].toLocaleUpperCase('hu')}</text>${n.warning.length?'<text class="graph-warning" x="240" y="23">!</text>':''}${lines.map((line,i)=>`<text data-i18n-skip class="graph-name" x="16" y="${48+i*18}">${esc(line)}</text>`).join('')}<text class="graph-amount" x="16" y="94">${esc(detail)}</text><text class="graph-note" x="16" y="117">${esc(output)}</text><text class="graph-note" x="16" y="136">Készlet: ${fmt(n.available)} · Folyamatban: ${fmt(n.wip)}</text></g>`;
  }).join('');
  const edges=graph.edges.map(e=>`<path class="graph-edge" data-from="${e.from}" data-to="${e.to}" d="${EvePlanGraph.path(graph,e)}" marker-end="url(#graph-arrow)"><title>${esc(plan.rows.find(r=>r.id===e.from).name)} → ${esc(plan.rows.find(r=>r.id===e.to).name)}: ${fmt(e.quantity)} db bemenet</title></path>`).join('');
  const toolbar=`<div class="graph-toolbar"><div class="graph-options"><label><input id="graph-purchases" type="checkbox" ${graphOptions.purchases?'checked':''}> Beszerzendő anyagok</label><label><input id="graph-covered" type="checkbox" ${graphOptions.covered?'checked':''}> Fedezett elemek</label></div><div class="graph-navigation"><button class="button compact" id="graph-minus" aria-label="Gráf kicsinyítése">−</button><output id="graph-scale" aria-label="Gráf nagyítása"></output><button class="button compact" id="graph-plus" aria-label="Gráf nagyítása">＋</button><button class="button compact" id="graph-fit">Teljes gráf</button><button class="button compact" id="graph-actual">100%</button></div></div><div class="graph-toolbar graph-secondary"><select id="graph-jump" aria-label="Ugrás egy gráfelemhez"><option value="">Ugrás egy tételhez…</option>${[...graph.nodes].sort((a,b)=>a.name.localeCompare(b.name,'hu')).map(n=>`<option data-i18n-skip value="${n.id}">${esc(n.name)}</option>`).join('')}</select><button class="text-button" id="graph-clear">Kijelölés törlése</button><span class="muted">${fmt(graph.nodes.length)} elem · ${fmt(graph.edges.length)} kapcsolat</span></div>`;
  const picture=graph.nodes.length?`<div class="graph-viewport" id="graph-viewport" role="region" tabindex="0" aria-label="Gyártási kapcsolatok; görgethető és húzással mozgatható gráf"><svg id="plan-graph" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${graph.width} ${graph.height}" aria-label="${esc(plan.name)} gyártási gráfja"><defs><marker id="graph-arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M 0 0 L 9 4.5 L 0 9 z"/></marker></defs>${graph.layers.map(l=>`<text class="graph-layer" x="${l.x}" y="30">${l.stage?l.stage+'. SZINT':'BESZERZÉS'} · ${l.count} ELEM</text>`).join('')}<g class="graph-edges">${edges}</g><g class="graph-cards">${cards}</g></svg></div>`:empty('Nincs megjeleníthető gyártandó tétel',plan.queue.length?'Kapcsold be a beszerzendő vagy fedezett elemeket.':'A gyártási lista is üres. A Beszerzendő anyagok és Fedezett elemek kapcsolóval a további tételeket is láthatod.');
  content.innerHTML=`<div id="graph-shell" class="graph-shell${graphExpanded?' graph-expanded':''}">`+panel(`${plan.name} · ${fmt(plan.quantity)} db`,'Az aktuális gyártási terv alapján',toolbar+picture,plan.name)+`<div class="graph-legend"><span class="reaction">● Reakció</span><span class="manufacturing">● Gyártás</span><span class="buy">● Beszerzés</span><span class="covered">● Fedezett</span><span>→ Bemenetből készülő termék</span></div><p class="footnote">Kattints egy elemre: a neve a vágólapra kerül, és a kapcsolódó gyártási ág kiemelést kap. Az ismétlődő anyagok egyszer szerepelnek, a teljes tervre összesített mennyiséggel. Nagyítás: a + / − gombokkal vagy Ctrl/⌘ + görgetéssel; mozgatás: görgetéssel vagy az üres terület húzásával. A nyíl fölött látható a felhasznált bemenet mennyisége.</p><div id="graph-details"></div></div>`;
  $('.graph-navigation').insertAdjacentHTML('beforeend',`<button class="button compact" id="graph-expand" aria-expanded="${graphExpanded}">${graphExpanded?'Normál nézet':'Nagy nézet'}</button>`);
  $('#graph-clear').insertAdjacentHTML('afterend','<button class="text-button" id="graph-show-details">Részletek</button>');
  const expand=()=>{graphExpanded=!graphExpanded;$('#graph-shell').classList.toggle('graph-expanded',graphExpanded);$('#graph-expand').textContent=graphExpanded?'Normál nézet':'Nagy nézet';$('#graph-expand').setAttribute('aria-expanded',String(graphExpanded));};
  $('#graph-expand').onclick=expand;
  $('#graph-shell').onkeydown=event=>{if(event.key==='Escape'&&graphExpanded){expand();$('#graph-expand').focus();}};
  $('#graph-show-details').onclick=()=>$('#graph-details').scrollIntoView({block:'start',behavior:'smooth'});
  $('#graph-list').onclick=()=>navigate('queue');
  for(const key of ['purchases','covered'])$('#graph-'+key).onchange=event=>{graphOptions[key]=event.target.checked;render();};
  const viewport=$('#graph-viewport'),svg=$('#plan-graph');
  function zoom(value, anchor) {
    const old=graphZoom;
    graphZoom=Math.max(.03,Math.min(1.8,value));
    $('#graph-scale').textContent=Math.round(graphZoom*100)+'%';
    if(!svg)return;
    const x=anchor?.x??viewport.clientWidth/2,y=anchor?.y??viewport.clientHeight/2;
    const centerX=(viewport.scrollLeft+x)/old, centerY=(viewport.scrollTop+y)/old;
    svg.setAttribute('width',Math.round(graph.width*graphZoom));
    svg.setAttribute('height',Math.round(graph.height*graphZoom));
    viewport.scrollLeft=centerX*graphZoom-x;viewport.scrollTop=centerY*graphZoom-y;
  }
  function select(id,center=false) {
    graphSelected=graph.nodes.some(n=>n.id===id)?id:null;
    const connected=graphSelected?EvePlanGraph.branch(graph,graphSelected):null;
    $$('.graph-node').forEach(el=>{
      const nodeId=Number(el.dataset.graphId);
      el.classList.toggle('graph-selected',nodeId===graphSelected);
      el.classList.toggle('graph-dim',!!connected&&!connected.has(nodeId));
      el.setAttribute('aria-pressed',String(nodeId===graphSelected));
    });
    $$('.graph-edge').forEach(el=>{
      const active=!!connected&&connected.has(Number(el.dataset.from))&&connected.has(Number(el.dataset.to));
      el.classList.toggle('graph-highlight',active);el.classList.toggle('graph-dim',!!connected&&!active);
    });
    $('#graph-jump').value=graphSelected||'';
    $('#graph-clear').disabled=!graphSelected;
    $('#graph-show-details').disabled=!graphSelected;
    renderGraphDetails(graphSelected);
    if(center && graphSelected && viewport){
      const node=graph.nodes.find(n=>n.id===graphSelected);
      zoom(Math.max(.75,graphZoom));
      viewport.scrollLeft=(node.x+node.width/2)*graphZoom-viewport.clientWidth/2;
      viewport.scrollTop=(node.y+node.height/2)*graphZoom-viewport.clientHeight/2;
    }
  }
  $('#graph-plus').onclick=()=>zoom(graphZoom*1.25);
  $('#graph-minus').onclick=()=>zoom(graphZoom/1.25);
  $('#graph-actual').onclick=()=>zoom(1);
  $('#graph-fit').onclick=()=>{if(viewport){zoom(Math.min((viewport.clientWidth-24)/graph.width,(viewport.clientHeight-24)/graph.height,1));viewport.scrollLeft=0;viewport.scrollTop=0;}};
  $('#graph-jump').onchange=event=>select(Number(event.target.value)||null,true);
  $('#graph-clear').onclick=()=>select(null);
  $$('.graph-node').forEach(el=>{
    el.onclick=()=>select(Number(el.dataset.graphId));
    el.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(Number(el.dataset.graphId));}if(event.key==='Escape')select(null);};
  });
  if(viewport){
    let drag=null;
    viewport.onpointerdown=event=>{
      if(event.button!==0||event.target.closest('.graph-node'))return;
      drag={x:event.clientX,y:event.clientY,left:viewport.scrollLeft,top:viewport.scrollTop,id:event.pointerId};
      viewport.setPointerCapture(event.pointerId);viewport.classList.add('graph-dragging');
    };
    viewport.onpointermove=event=>{if(drag){viewport.scrollLeft=drag.left+drag.x-event.clientX;viewport.scrollTop=drag.top+drag.y-event.clientY;}};
    const end=()=>{if(drag&&viewport.hasPointerCapture(drag.id))viewport.releasePointerCapture(drag.id);drag=null;viewport.classList.remove('graph-dragging');};
    viewport.onpointerup=end;viewport.onpointercancel=end;viewport.onlostpointercapture=()=>{drag=null;viewport.classList.remove('graph-dragging');};
    viewport.addEventListener('wheel',event=>{if(event.ctrlKey||event.metaKey){event.preventDefault();const box=viewport.getBoundingClientRect();zoom(graphZoom*(event.deltaY<0?1.1:1/1.1),{x:event.clientX-box.left,y:event.clientY-box.top});}},{passive:false});
  }
  zoom(graphZoom);select(graphSelected);
}
function renderGraphDetails(id) {
  const target=$('#graph-details'),row=plan.rows.find(r=>r.id===id);
  if(!row){target.innerHTML='<div class="graph-detail-hint">Válassz egy elemet a gráfon vagy az Ugrás egy tételhez listából a részletekhez.</div>';return;}
  const materials=row.materials.filter(m=>m.quantity>0),parents=plan.rows.filter(r=>r.materials.some(m=>m.id===id&&m.quantity>0));
  const status=r=>r.runs?`${fmt(r.runs)} run gyártandó`:r.buy?`${fmt(r.buy)} db beszerzendő`:'Készletből / folyamatban fedezett';
  target.innerHTML=panel(row.name+' – részletek','A mennyiségek a teljes tervre vonatkoznak',`<div class="graph-detail-body"><div class="chip-list"><span class="chip">Szükséglet: ${fmt(row.required)} db</span><span class="chip">Elérhető: ${fmt(row.available)} db</span><span class="chip">Folyamatban: ${fmt(row.wip)} db</span><span class="chip">Hiány: ${fmt(row.missing)} db</span><span class="chip">${esc(status(row))}</span>${row.runs?`<span class="chip">Kimenet: ${fmt(row.manufactured)} db</span><span class="chip">${fmt(row.parameters.output)} db/run</span><span class="chip">${fmt(row.jobs)} job · ${esc(batchText(row))}</span>`:''}</div>${row.warning.length?`<p class="warning-text">${esc(row.warning.join(' '))}</p>`:''}<div class="graph-detail-grid"><div><h3>A hátralévő gyártás bemenetei</h3>${materials.length?table(['Anyag','Ehhez a gyártáshoz','Teljes tervben'],materials.map(m=>{const r=plan.rows.find(r=>r.id===m.id);return `<tr><td>${itemName(m.name)}</td><td class="num">${fmt(m.quantity)} db</td><td>${esc(status(r))}</td></tr>`;})):'<p>Nincs további gyártási bemenet: fedezett vagy beszerzendő tétel.</p>'}</div><div><h3>Ezekhez használjuk fel</h3>${parents.length?table(['Termék','Bemenet ebből'],parents.map(p=>`<tr><td>${itemName(p.name)}</td><td class="num">${fmt(p.materials.find(m=>m.id===id).quantity)} db</td></tr>`)):'<p>Ez a terv célterméke.</p>'}</div></div></div>`,row.name);
}
function renderShopping(content) {
  setHead('BESZERZÉS','Ami még hiányzik','A hátralévő gyártás anyagai, hiányzó BPC-runjai és reakcióformulái.');
  actions(`<button id="copy-shopping" class="button compact">Beszerzési lista másolása</button>${exportButton()}`);
  const rows=plan.shopping.map(r=>`<tr><td>${item(r)}</td><td><span class="badge">${r.category}</span></td><td class="num">${fmt(r.required)}</td><td class="num">${fmt(r.available)}</td><td class="num">${fmt(r.wip)}</td><td class="num"><strong>${fmt(r.buy)}</strong></td><td>${r.unit||'db'}</td><td>${esc(blueprintSupply(r))}</td>${costCell(r.id,r.buy,r.unit||'db')}</tr>`);
  content.innerHTML=shoppingTabs()+costSummary('shopping-current',plan.shopping.map(r=>({...r,quantity:r.buy})),'A hiányzó anyagok költsége','Csak a még beszerzendő mennyiségek Jita-értéke.')+panel('Alapanyaghiány',`${fmt(rows.length)} beszerzendő termék`,rows.length?table(['Termék','Típus','Szükséglet','Elérhető','Folyamatban','Beszerzendő','Egység','Blueprint beszerzés','Jita-egységár','Beszerzési érték'],rows):empty('Nincs alapanyaghiány','A hátralévő gyártás minden szükséges anyagát fedezi a készlet.'));
  content.innerHTML+='<p class="footnote">A már meglévő vagy folyamatban lévő komponensek anyagait a terv nem kéri újra. A PI-termékek itt beszerzendő tételek. A BPC-hiány a kiválasztott ME/TE-csoport még felhasználható runjai alapján számolódik; a db-becslés a jelzett run/BPC feltételezéssel értendő. BPC másolással (ha a BPO másolható), inventionnel vagy vásárlással szerezhető; ezek külön jobjait és anyagait nem tervezzük. A reakcióformula nem másolható.</p>';
  bindShoppingTabs();bindJita(plan.shopping.filter(r=>r.unit!=='run').map(r=>r.id));
  $('#copy-shopping').onclick=async()=>{try{await navigator.clipboard.writeText(plan.shopping.map(r=>`${r.name}\t${r.buy}\t${r.unit||'db'}`).join('\n'));toast('A beszerzési lista a vágólapon.');}catch{error('A böngésző nem engedte a másolást. A CSV-mentést használhatod.');}};
  $('#export-csv').onclick=()=>csv(plan.shopping.map(r=>[r.name,r.buy,r.unit||'db',blueprintSupply(r),...jitaCsv(r.id,r.buy,r.unit)]),['Termék','Mennyiség','Egység','Blueprint beszerzés','Árazás','Jita-egységár','Beszerzési érték'],'alapanyaghiany');
}
function shoppingTabs(){
  return `<div class="shopping-tabs"><button class="button compact" data-shopping-mode="current" aria-pressed="${shoppingMode==='current'}">Kiválasztott terv</button><button class="button compact" data-shopping-mode="all" aria-pressed="${shoppingMode==='all'}">Összes mentett terv</button></div>`;
}
function bindShoppingTabs(){
  $$('[data-shopping-mode]').forEach(el=>el.onclick=()=>{shoppingMode=el.dataset.shoppingMode;render();});
}
async function refreshAllShopping(){
  if(shoppingRequest)return;
  const revision=shoppingRevision;shoppingRequest=api('/api/plans/shopping');
  try{const result=await shoppingRequest;if(revision===shoppingRevision)shoppingData=result;}
  catch(e){if(revision===shoppingRevision){shoppingData={error:e.message,delivery_wait:e.delivery_wait};if(e.delivery_wait){deliveryWait=e.delivery_wait;scheduleDeliveryCheck();}}}
  finally{shoppingRequest=null;if(view==='shopping'&&shoppingMode==='all')render();}
}
function renderAllShopping(content){
  setHead('KÖZÖS BESZERZÉS','Az összes mentett terv anyaghiánya','A tervek közös készletből és jobkimenetekből számított, egyesített beszerzési listája.');
  $('#plan-status').hidden=true;
  actions('<button class="button compact" id="refresh-all-shopping">Összesítés frissítése</button>');
  $('#refresh-all-shopping').onclick=async()=>{await reloadState();render();};
  content.innerHTML=shoppingTabs();bindShoppingTabs();
  if(!shoppingData){content.innerHTML+=empty('Az összes terv számítása','A közös készletet és a foglalások elsőbbségét ellenőrizzük…');bindShoppingTabs();void refreshAllShopping();return;}
  const data=shoppingData;
  if(data.error){content.innerHTML+=data.delivery_wait?deliveryWaitMarkup(data.delivery_wait):`<div class="banner error">${esc(data.error)}</div>`;bindShoppingTabs();return;}
  actions('<button class="button compact" id="refresh-all-shopping">Összesítés frissítése</button><button class="button compact" id="copy-all-shopping">Összesített lista másolása</button>'+exportButton());
  $('#refresh-all-shopping').onclick=async()=>{await reloadState();render();};
  content.innerHTML+=`<div class="banner"><strong>${data.plans.length} mentett terv · ${data.separate_pools?'Elkülönített személyes és corp készletek':data.source==='eve'?'Személyes EVE-készlet':'Kézi készlet'}</strong><div>A közös készletet és a folyamatban lévő kimeneteket egyszer használjuk fel. Először az aktív foglalások, utánuk a foglalás nélküli mentett tervek kapnak készletet. Ez az összesítés nem kapcsol be új foglalást.</div></div>`;
  if(data.stale_characters.length)content.innerHTML+=`<div class="banner warn">Korábbi EVE-pillanatképből számolunk: ${esc(data.stale_characters.join(', '))}. Frissítsd az EVE-adatokat.</div>`;
  const rows=data.rows.map(r=>`<tr><td>${item(r)}</td><td><span class="badge">${esc(r.category)}</span></td><td class="num"><strong>${fmt(r.buy)}</strong></td><td>${r.unit||'db'}</td><td>${esc(blueprintSupply(r))}</td><td>${r.plans.map(p=>`${planLabel(p)}${p.corporation_id?' · '+esc(p.scope_label):' · Személyes'} (${fmt(p.quantity)} db cél): <strong>${fmt(p.buy)} ${r.unit||'db'}</strong>`).join('<br>')}</td>${costCell(r.id,r.buy,r.unit||'db')}</tr>`);
  content.innerHTML+=costSummary('shopping-all',data.rows.map(r=>({...r,quantity:r.buy})),'A hiányzó anyagok összköltsége','Az összes mentett terv egyesített beszerzési mennyiségének Jita-értéke.');
  content.innerHTML+=panel('Összesített alapanyaghiány',`${rows.length} beszerzendő termék`,rows.length?table(['Termék','Típus','Összesen beszerzendő','Egység','Blueprint beszerzés','Hiány tervenként','Jita-egységár','Beszerzési érték'],rows):empty(data.plans.length?'Nincs alapanyaghiány':'Még nincs mentett terv',data.plans.length?'A közös készlet és jobkimenetek minden mentett tervhez elegendők.':'Ments el egy gyártási tervet az összesítéshez.'));
  content.innerHTML+=`<details class="panel shopping-included"><summary>Beszámított tervek · ${data.plans.length}</summary>${table(['Elsőbbség','Terv','Gyártási kör','Célmennyiség','Foglalás'],data.plans.map(p=>`<tr><td>${p.priority}</td><td>${planLabel(p)}</td><td>${p.corporation_id?verbatim(p.scope_label):esc(p.scope_label||'Személyes gyártás')}</td><td>${fmt(p.quantity)} db</td><td>${p.reserve_active?'Aktív':'Nincs aktív foglalás; beleszámít'}</td></tr>`))}</details><p class="footnote">A kész komponensek és hajók alapanyagai nem kerülnek vissza a hiányba. A közösen használható reakcióformula készlettulajdonosonként egyszer szerepel. Azonos anyag egy sorban szerepel; a tervenkénti bontás a még hiányzó mennyiségeket mutatja. A termékmezőben végzett, még nem mentett módosításokat ez az összesítés nem tartalmazza. Számítás: ${esc(date(data.calculated_at))}.</p>`;
  bindShoppingTabs();
  bindJita(data.rows.filter(r=>r.unit!=='run').map(r=>r.id));
  $('#copy-all-shopping').onclick=async()=>{try{await navigator.clipboard.writeText(data.rows.map(r=>`${r.name}\t${r.buy}\t${r.unit||'db'}`).join('\n'));toast('Az összesített beszerzési lista a vágólapon.');}catch{error('A másolás nem sikerült. Használd a CSV-mentést.');}};
  $('#export-csv').onclick=()=>csv(data.rows.map(r=>[r.name,r.buy,r.unit||'db',r.plans.map(p=>`${p.name} (${p.quantity} db cél): ${p.buy}`).join(' | '),...jitaCsv(r.id,r.buy,r.unit)]),['Termék','Összesen beszerzendő','Egység','Hiány tervenként','Árazás','Jita-egységár','Beszerzési érték'],'osszes-terv-alapanyaghiany');
}
function numberInput(row,key,value,placeholder='0',extra='') {
  return `<input class="table-input ${extra}" type="text" inputmode="numeric" data-grouped-number data-number-max="1000000000000" data-id="${row.id}" data-key="${key}" value="${value==null?'':EveNumbers.format(value)}" placeholder="${esc(placeholder)}" aria-label="${esc(row.name)} – ${esc({quantity:'Kézi készlet',reserved:'Másra foglalva',wip:'Kézi folyamatban'}[key]||key)}">`;
}
function renderInventory(content) {
  setHead('KÉSZLETELSZÁMOLÁS','Amivel már rendelkezel','A kézi készlet és folyamatban mennyiség felülírja az EVE-adatot. A 0 is érvényes felülírás.');
  actions('<button id="apply-inventory" class="button primary compact">Módosítások alkalmazása</button>');
  const held=(stock,wip)=>`${fmt(stock)}<div class="batch-note">${fmt(wip)} folyamatban</div>`;
  const rows=plan.rows.map(r=>{const local=state.inventory[r.id]||{}; return `<tr data-search="${esc(r.name.toLowerCase())}"><td>${item(r)}</td><td class="num">${fmt(r.required)}</td><td class="num">${fmt(r.available)}${r.manual_stock?'<div class="batch-note">kézi</div>':''}</td><td class="num" aria-label="${esc(r.name)} – Más tervek foglalása">${held(r.plan_reserved,r.plan_wip_reserved)}</td><td class="num" aria-label="${esc(r.name)} – Saját terv foglalása">${held(r.own_reserved,r.own_wip_reserved)}</td><td>${numberInput(r,'quantity',local.quantity,state.settings.source==='eve'?'EVE':'0')}</td><td>${numberInput(r,'reserved',local.reserved??0)}</td><td class="num">${fmt(r.wip)}${r.manual_wip?'<div class="batch-note">kézi</div>':''}</td><td>${numberInput(r,'wip',local.wip,state.settings.source==='eve'?'EVE-job':'0')}</td></tr>`;});
  content.innerHTML=panel('A terv készlete',`${fmt(rows.length)} termék és alapanyag`, `<div class="panel-head"><div class="inline-filter"><input type="search" id="row-filter" placeholder="Szűrés terméknévre…" aria-label="Készlet szűrése"><span class="muted">Forrás: ${corporationId?'Corp: '+esc(state.scope_label):state.settings.source==='eve'?'személyes EVE-készlet':'kézi készlet'}</span></div></div>`+table(['Termék','Szükséglet','Elérhető','Más tervek foglalása','Saját terv foglalása','Kézi készlet','Másra foglalva (kézi)','Folyamatban','Kézi folyamatban'],rows,'inventory-table'));
  content.innerHTML+='<p class="footnote">Az Elérhető és a Folyamatban oszlopból más aktív tervek foglalásait már levontuk; a saját mentett terv foglalása felhasználható. A foglalási oszlopok felső értéke a készlet, az alsó a folyamatban lévő kimenet. Az üres kézi mező az EVE-adatot használja, kézi módban 0. A kézi Másra foglalva ezen felüli, külön levonás. Frissítéskor a tervfoglalások újraszámolódnak, a kézi felülírások megmaradnak.</p>';
  bindDirty(); bindFilter(); $('#apply-inventory').onclick=()=>applyMapping('inventory');
}
function renderBlueprints(content) {
  setHead('BLUEPRINTPARAMÉTEREK','ME, TE és runbeállítások','Automatikus választás: BPO elsőbbség, majd a legjobb azonos ME/TE-jű BPC-csoport.');
  actions('<button id="apply-parameters" class="button primary compact">Beállítások alkalmazása</button>');
  const rows=plan.rows.filter(r=>r.parameters).map(r=>{
    const p=r.parameters, o={mode:r.activity==='buy'?'buy':'build',...(state.parameters[r.id]||{})}, manual=o.source==='manual', reaction=r.activity==='reaction';
    return `<tr data-search="${esc(r.name.toLowerCase())}">
      <td>${item(r)}<small class="muted">${manual?'Kézi felülírás':p.source==='auto'?p.kind+' · '+fmt(p.group_count)+' példány a számításban':'Nincs használható EVE-blueprint'}</small>
      ${p.instances.length?`<button class="text-button bp-details" data-bp-details="${r.id}" aria-label="${esc(r.name)} – Blueprintpéldányok">Példányok megtekintése</button>`:''}
      ${p.other_groups?'<div class="row-warning warning-text">Eltérő ME/TE-jű példányok is vannak.</div>':''}</td>
      <td class="num" aria-label="${esc(r.name)} – BPO darabszám">${fmt(p.bpo_count)}</td>
      <td class="num" aria-label="${esc(r.name)} – BPC darabszám"><strong>${fmt(p.bpc_count)}</strong>${p.bpc_count?`<div class="batch-note">${fmt(p.bpc_runs)} run összesen</div>`:''}</td>
      <td><select class="table-select" data-id="${r.id}" data-key="source" aria-label="${esc(r.name)} – Paraméterforrás"><option value="auto" ${!manual?'selected':''}>Automatikus</option><option value="manual" ${manual?'selected':''}>Kézi</option></select></td>
      <td><input class="table-input" type="number" data-id="${r.id}" data-key="me" min="0" max="10" step="1" value="${p.me}" ${!manual||reaction?'disabled':''} aria-label="${esc(r.name)} – ME százalék"></td>
      <td><input class="table-input" type="number" data-id="${r.id}" data-key="te" min="0" max="20" step="1" value="${p.te}" ${!manual||reaction?'disabled':''} aria-label="${esc(r.name)} – TE százalék"></td>
      <td><input class="table-input" type="text" inputmode="numeric" data-grouped-number data-id="${r.id}" data-key="job_runs" data-number-min="1" data-number-max="1000000" value="${EveNumbers.format(p.job_runs)}" aria-label="${esc(r.name)} – Run jobonként"></td>
      <td><input class="table-input run-capacity" type="text" inputmode="numeric" data-grouped-number data-id="${r.id}" data-key="total_runs" data-number-max="1000000000000" value="${(manual?o.total_runs:p.available_runs)==null?'':EveNumbers.format(manual?o.total_runs:p.available_runs)}" placeholder="${p.kind==='BPO'?'Korlátlan':'Ismeretlen'}" ${!manual?'disabled':''} aria-label="${esc(r.name)} – Összes BPC run"></td>
      <td class="num">${fmt(p.output)}</td>
      <td><select class="table-select" data-id="${r.id}" data-key="mode" aria-label="${esc(r.name)} – Gyártás vagy vétel"><option value="build" ${o.mode!=='buy'?'selected':''}>Gyártás</option><option value="buy" ${o.mode==='buy'?'selected':''}>Vétel</option></select></td>
      <td><input class="table-input wide" type="number" data-id="${r.id}" data-key="item_id" min="1" max="9007199254740991" step="1" value="${o.item_id??''}" placeholder="Automatikus" aria-label="${esc(r.name)} – Kiválasztott blueprint Item ID"></td></tr>`;
  });
  const chars=state.characters.filter(c=>!state.settings.character_ids.length||state.settings.character_ids.includes(c.id));
  const complete=corporationId?state.corporations.find(c=>c.id===corporationId)?.ready:chars.length && chars.every(c=>c.data_times.blueprints&&!c.error);
  content.innerHTML=`<div class="banner ${complete?'':'warn'}">${complete?(corporationId?'Az automatikus ME/TE és BPC-run a kiválasztott corporation saját blueprintjeiből származik.':'Az automatikus ME/TE és BPC-run a letöltött személyes blueprintekből származik, kézi készletmódban is.'):chars.length?'A blueprintadatok egy része hiányzik vagy a frissítés hibát jelzett. Ellenőrizd az EVE-kapcsolat oldalt.':'Még nincs hozzáadott EVE-karakter. Az automatikus blueprintértékekhez adj hozzá karaktert és frissíts; addig kézi paraméterekkel tervezhetsz.'}</div>`;
  content.innerHTML+=panel('A receptlánc blueprintjei',`${fmt(rows.length)} termék`, '<div class="panel-head"><input type="search" id="row-filter" placeholder="Szűrés terméknévre…" aria-label="Blueprintok szűrése"></div>'+table(['Termék','BPO (db)','BPC (db)','ME/TE forrás','ME %','TE %','Run/job','Felhasználható run','Kimenet/run','Gyártás/vétel','Item ID'],rows,'blueprint-table'));
  content.innerHTML+='<p class="footnote">A BPO/BPC-darabszám és a BPC alatti összes run minden letöltött, karakter- és helyszűrésbe tartozó példányt tartalmaz. A Felhasználható run az ME/TE-hez kiválasztott csoport runkerete. A Run/job a tervezett jobméret, automatikus BPC-nél alapból legfeljebb 100 és a leghosszabb másolat runja. Egy BPC határán új job kezdődik. A Példányok megtekintése gomb minden BPC saját ME/TE-jét és runját megmutatja. Kézi runkeret üresen: ismeretlen/korlátlan; 0: nincs run. Reakciónál az ME/TE 0; a struktúrabónusz külön érvényesül.</p><div id="blueprint-detail"></div>';
  $$('[data-bp-details]').forEach(button=>button.onclick=()=>{blueprintDetailId=Number(button.dataset.bpDetails);renderBlueprintDetails();$('#blueprint-detail').scrollIntoView({block:'nearest',behavior:'smooth'});});
  renderBlueprintDetails();
  bindDirty(); bindFilter();
  $$('[data-key="source"]').forEach(select=>select.addEventListener('change',()=>{
    const row=select.closest('tr');
    for(const key of ['me','te','total_runs']) {
      const input=row.querySelector(`[data-key="${key}"]`);
      input.disabled=select.value!=='manual'||(['me','te'].includes(key)&&plan.rows.find(r=>r.id===Number(select.dataset.id))?.activity==='reaction');
      if(select.value==='manual') recordDirty(input);
    }
  }));
  $('#apply-parameters').onclick=()=>applyMapping('parameters');
}
function renderBlueprintDetails() {
  const target=$('#blueprint-detail');
  const row=plan.rows.find(r=>r.id===blueprintDetailId);
  if(!target||!row?.parameters?.instances.length) {if(target)target.innerHTML='';return;}
  const p=row.parameters;
  const rows=p.instances.map(b=>`<tr><td><span class="badge">${esc(b.kind)}</span></td><td class="num">${fmt(b.count)}</td><td class="num">${fmt(b.me)}%</td><td class="num">${fmt(b.te)}%</td><td class="num">${b.runs===null?'Korlátlan':fmt(b.runs)}</td><td><span class="badge ${b.selected?'good':''}">${b.selected?'Kiválasztva':'Nincs kiválasztva'}</span></td><td>${b.busy?'<span class="badge warn">Foglalt</span>':'Szabad'}</td>${characterCell(b.character_id)}<td class="num">${b.location_id||'–'}</td><td class="num">${b.item_id}</td></tr>`);
  target.innerHTML=panel(row.name+' – blueprintpéldányok',`${fmt(p.bpo_count)} BPO · ${fmt(p.bpc_count)} BPC · ${fmt(p.bpc_runs)} BPC-run`,table(['Típus','Darab','ME','TE','Hátralévő run / példány','Számításban','Állapot','Karakter','Hely-ID','Item ID'],rows),row.name);
}
function recordDirty(el) {
  const id=el.dataset.id, key=el.dataset.key;
  dirty[id]??={};
  dirty[id][key]=el.value===''?null:el.tagName==='SELECT'?el.value:el.hasAttribute('data-grouped-number')?EveNumbers.parse(el.value):Number(el.value);
  el.classList.add('edited');
}
function bindDirty() { $$('[data-id][data-key]').forEach(el=>{
  el.addEventListener(el.tagName==='SELECT'?'change':'input',()=>recordDirty(el));
}); }
function bindFilter() { const el=$('#row-filter'); if(el) el.oninput=()=>EveTables.setSearch(el.closest('.panel').querySelector('table'),el.value); }
async function applyMapping(kind) {
  const button=$(`#apply-${kind}`); button.disabled=true; error('');
  try {
    $$('input[data-id][data-key]:not(:disabled)').forEach(el=>{if(!el.checkValidity()) throw new Error('Ellenőrizd a megadott mennyiségeket: '+el.getAttribute('aria-label'));});
    await api(scoped('/api/'+kind),dirty); dirty={}; await calculate(); toast('Módosítások alkalmazva. A gyártási terv frissült.');
  } catch(e) {error(e.message); button.disabled=false;}
}
function jobReady(j){return j.status==='ready'||j.status==='active'&&Number.isFinite(Date.parse(j.end_date))&&Date.parse(j.end_date)<=Date.now();}
function updateReadyJobs(){const badge=$('#jobs-ready-count');if(!badge||!state)return;const count=state.jobs.filter(jobReady).length;badge.hidden=!count;badge.textContent=count?String(count):'';badge.title=EveI18n.t('Átvehető vagy várhatóan elkészült jobok');}
setInterval(()=>{updateReadyJobs();if(view==='jobs'&&state)render();},30000);
function renderJobs(content) {
  updateReadyJobs();
  setHead('IPARI JOBOK','Ami már folyamatban van',corporationId?'A kiválasztott corporation saját ipari jobjai.':'Személyes gyártási, reakciós és egyéb aktív jobok a legutóbbi EVE-frissítésből.');
  const labels={active:'Fut',paused:'Szünetel',ready:'Átvehető'};
  const ready=state.jobs.filter(jobReady);
  const readyBanner=ready.length?`<div class="banner warn" role="alert"><strong>Van kész vagy várhatóan elkészült job.</strong> <span>${fmt(ready.length)}</span> <span>job átvehető vagy lejárt a befejezési ideje. Vedd át az EVE-ben, majd frissítsd az adatokat.</span></div>`:'';
  const rows=state.jobs.map(j=>`<tr class="${jobReady(j)?'ready-job':''}"><td>${item({name:j.name,id:j.product_type_id||0})}</td><td><span class="badge ${j.status==='ready'?'good':'reaction'}">${esc(j.status==='active'&&jobReady(j)?'Várhatóan elkészült · frissíts':labels[j.status]||j.status)}</span></td><td class="num">${fmt(j.runs)}</td><td class="num"><strong>${fmt(j.expected_output)}</strong></td>${characterCell(j.character_id)}<td class="num">${j.output_location_id||'–'}</td><td data-sort-value="${j.end_date?Date.parse(j.end_date):''}">${j.end_date?esc(EveI18n.date(new Date(j.end_date))):'–'}</td></tr>`);
  content.innerHTML=readyBanner+panel('Aktív és át nem vett jobok',`${fmt(rows.length)} job`,rows.length?table(['Termék','Állapot','Run','Beszámítható kimenet','Karakter','Kimeneti Hely-ID','Befejezés'],rows):empty('Nincs betöltött aktív job','Adj hozzá karaktert az EVE-kapcsolat oldalon, majd indíts EVE-frissítést.'));
  content.innerHTML+='<p class="footnote">A kimenet csak gyártási és reakciós jobnál, a kiválasztott helyszíneken számít. A delivered, cancelled és reverted jobokat nem adja a folyamatban készlethez. Kutatás, invention és másolás kimenete itt 0. Kézi készletmódban a terv a Készlet oldalon megadott kézi folyamatban mennyiségekkel számol.</p>';
}
function renderSettings(content) {
  setHead('GYÁRTÁSI KÖRNYEZET','Struktúrák és bónuszok','A közös beállítások a terv minden megfelelő gyártási lépésére érvényesek.');
  const group=(key,title)=>{
    const s=state.settings[key];
    const fields=[['material_role','Struktúra anyagbónusz (%)'],['material_rig','Rig anyagbónusz (%)'],['time_role','Struktúra időbónusz (%)'],['time_rig','Rig időbónusz (%)'],['skill_time','Kézi skill időszorzó'],['job_cost_role','Struktúra job cost kedvezmény (%)'],['facility_tax','Facility tax (%)'],['scc_surcharge','SCC-pótdíj (%)'],['alpha_surcharge','Alpha-pótdíj (%)']];
    return panel(title,key==='reaction'?'Reakciók':'Gyártás',`<div class="panel-body"><label for="${key}-system-search">Gyártási rendszer</label><div class="search-wrap"><input id="${key}-system-search" type="search" data-facility-system="${key}" data-system-id="${s.system_id||''}" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="${key}-system-results" autocomplete="off" placeholder="Gépelj rendszernevet…" value="${esc(state.industry_facilities?.[key]?.system_name||'')}"><div class="search-results" id="${key}-system-results" data-system-results="${key}" role="listbox" hidden></div></div><div class="factor facility-index"><span>System cost index · ${key==='reaction'?'Reakció':'Gyártás'}</span><strong data-system-index="${key}">–</strong><small></small></div><div class="fields">${fields.map(([field,label])=>`<div><label for="${key}-${field}">${label}</label><input id="${key}-${field}" data-facility="${key}" data-field="${field}" type="number" step="${['skill_time','facility_tax','scc_surcharge','alpha_surcharge'].includes(field)?'0.01':'0.1'}" min="${field==='skill_time'?'0.01':'0'}" max="${field==='skill_time'?'1':field==='facility_tax'?'10':'99'}" value="${s[field]}"></div>`).join('')}</div><div class="factor"><span>Anyagszorzó</span><strong>${((1-s.material_role/100)*(1-s.material_rig/100)).toLocaleString('hu-HU',{maximumFractionDigits:5})}</strong></div><div class="factor"><span>Időszorzó ME/TE nélkül</span><strong>${((1-s.time_role/100)*(1-s.time_rig/100)*s.skill_time).toLocaleString('hu-HU',{maximumFractionDigits:5})}</strong></div></div>`);
  };
  content.innerHTML=`<form id="settings-form"><div class="grid-two">${group('manufacturing','Manufacturing')}${group('reaction','Reakció')}</div><p class="footnote">Job cost = EIV × (system index × job cost bónusz + facility tax + SCC + Alpha). Az EIV az eredeti, ME és rig előtti recept és az ESI adjusted price alapján számít; a Jita-árazástól független. Manufacturing és reakció külön rendszert és adót használhat.</p><div class="section-actions"><button class="button primary" type="submit">Bónuszok mentése</button><small>A kézi időszorzó csak kézi módban vagy hiányzó skilladatnál érvényesül; karakterből számolt skillekkel nem szorozzuk újra.</small></div></form><div class="section-actions"><button type="button" class="button compact" data-industry-refresh>↻ Ipari költségadatok frissítése</button><small data-industry-status></small></div>`;
  content.innerHTML+=panel('Készletforrás és helyszín','A karakterek kiválasztása az EVE-kapcsolat oldalon',`<div class="panel-body"><div class="source-choices"><label><input type="radio" name="stock-source" value="manual" ${state.settings.source==='manual'?'checked':''}>Kézi készlet</label><label><input type="radio" name="stock-source" value="eve" ${state.settings.source==='eve'?'checked':''}>Személyes EVE-készlet</label></div><label for="location-ids">Hely-ID-k, vesszővel elválasztva</label><input id="location-ids" class="connection-input" value="${state.settings.location_ids.join(', ')}" placeholder="Üresen minden hely"><p class="footnote">Állomás vagy struktúra ID-t adj meg. A benne lévő konténerek készletét is számolja. A jobok kimeneti helyére ugyanez a szűrés érvényes.</p><div class="chip-list">${state.locations.slice(0,20).map(id=>`<span class="chip">${id}</span>`).join('')}</div><div class="section-actions"><button id="save-source" class="button compact">Készletforrás mentése</button></div></div>`);
  content.innerHTML+=panel('Receptadatbázis',`SDE ${state.sde.buildNumber}`,`<div class="panel-body"><p>${fmt(state.recipe_count)} választható gyártható termék. Adatcsomag kiadása: ${esc(state.sde.releaseDate)}. Az anyag-, idő- és becsült jobköltséget számolja; ütemezett slotkiosztást nem készít.</p><button id="update-sde" class="button compact">Receptadatok frissítése</button></div>`);
  $('#settings-form').oninput=()=>{dirty.facilities=true;};
  $('#settings-form').onsubmit=async event=>{event.preventDefault();try{const body={manufacturing:{},reaction:{}};$$('[data-facility]').forEach(el=>body[el.dataset.facility][el.dataset.field]=Number(el.value));$$('[data-facility-system]').forEach(el=>{if(el.value.trim()&&!el.dataset.systemId)throw new Error('Válassz rendszert a találati listából.');body[el.dataset.facilitySystem].system_id=el.dataset.systemId?Number(el.dataset.systemId):null;});await api('/api/settings',body);dirty={};await reloadState();if(productId)await calculate(false);else render();toast('Bónuszok mentve.');}catch(e){error(e.message);}};
  bindFacilitySystems();
  $('#save-source').onclick=async()=>{try{const raw=$('#location-ids').value.trim();const ids=raw?raw.split(/[,;\s]+/).filter(Boolean).map(Number):[];await api(scoped('/api/settings'),{source:$('input[name="stock-source"]:checked').value,location_ids:ids});await calculate();toast('Készletforrás mentve.');}catch(e){error(e.message);}};
  if(corporationId){$('input[name="stock-source"][value="manual"]').disabled=true;$('.source-choices').insertAdjacentHTML('afterend','<p>Corp módban kizárólag a kiválasztott corporation EVE-készlete számít; a helyszűrés corporationönként külön mentődik.</p>');}
  $('#update-sde').onclick=()=>startTask('/api/sde/update');
}
function renderConnection(content) {
  setHead('SZEMÉLYES EVE-ADATOK','Kapcsold össze a karaktereidet','Személyes készlet, blueprintek, ipari jobok, skillek, tanulási sor és bolygóadatok olvasása.');
  const characters=state.characters.map(c=>`<div class="character"><div class="char-select"><input type="checkbox" data-char="${c.id}" ${!state.settings.character_ids.length||state.settings.character_ids.includes(c.id)?'checked':''} aria-label="${esc(c.name)} beszámítása"><div><span class="character-name">${esc(c.name)}</span><small>${c.id} · Ellenőrizve: ${date(c.synced_at)}</small><small>Asset: ${date(c.data_times.assets)} · BP: ${date(c.data_times.blueprints)} · Job: ${date(c.data_times.jobs)}</small>${c.error?`<small class="danger">${esc(c.error)}</small>`:''}</div></div><button class="text-button danger" data-remove-character="${c.id}">Eltávolítás</button></div>`).join('');
  content.innerHTML=`<div class="grid-two">${panel('Hozzáadott karakterek',`${state.characters.length} karakter`, `<div class="panel-body">${characters||'<p>Még nincs hozzáadott karakter. A Bejelentkezés EVE Online-nal gombbal add hozzá a saját karaktereidet.</p>'}<div class="section-actions"><button id="add-character" class="button primary">Bejelentkezés EVE Online-nal</button></div>${characters?'<div class="section-actions"><button id="save-characters" class="button compact">Karakterválasztás mentése</button></div>':''}<p class="footnote">Üres karakterlista a beállításokban: minden hozzáadott karakter. A belépés az EVE hivatalos oldalán történik. A jelszavad nem kerül ebbe az alkalmazásba.</p></div>`)}${panel('Alkalmazásazonosító',state.settings.client_id?'Azonosító megadva':'Egyszeri beállítás',`<div class="panel-body"><p>${state.settings.client_id?'A nyilvános Client ID már meg van adva. A Bejelentkezés EVE Online-nal gombbal engedélyezd a saját karaktereidet; új EVE Developer alkalmazást nem kell létrehoznod.':'Az EVE Developer alkalmazásod nyilvános Client ID-ja szükséges.'} Client Secretet nem kell megadni.</p><label for="client-id">Client ID</label><div class="connection-input"><input id="client-id" autocomplete="off" spellcheck="false" value="${esc(state.settings.client_id)}" placeholder="Az EVE Developer oldalon kapott azonosító"><button id="save-client" class="button compact">Mentés</button></div>${!state.crypto_available?'<p class="danger">A belépéshez futtasd az egyszeri telepítőt: hiányzik a cryptography csomag.</p>':''}</div>`)}</div>`;
  const setupHelp=panel('Így hozd létre a saját EVE-alkalmazásodat','Ezt egyszer kell elvégezni',`<div class="panel-body"><ol class="steps"><li>Nyisd meg az <a href="https://developers.eveonline.com/applications" target="_blank" rel="noopener noreferrer">EVE Developer alkalmazásoldalát</a>, jelentkezz be, és válaszd a <strong>Create New Application</strong> lehetőséget.</li><li>Névnek megadhatod: <strong>EVE Muhely</strong>. Válaszd az ESI-t használó alkalmazást, és ha van választás, a helyi / native / PKCE típust. Nevet és leírást a portál kérésének megfelelően adj meg.</li><li>A <strong>Callback URL</strong> pontosan ez legyen:<code>${esc(state.callback)}</code></li><li>Válaszd ki ezeket az olvasási jogosultságokat:<code>${state.scopes.map(esc).join('\n')}</code></li><li>Mentsd az alkalmazást. A kapott <strong>Client ID</strong>-t másold a fenti mezőbe, és nyomd meg a Mentést. Az esetleg megjelenő Client Secretet nem használjuk.</li><li>A <strong>Bejelentkezés EVE Online-nal</strong> gombbal add hozzá egyenként a karaktereket. Ezután indíts <strong>EVE-frissítést</strong>, és a Struktúrák és bónuszok oldalon válaszd az EVE-készletet.</li></ol><p class="footnote">A belépési adatokat titkosítva, a Maceden tároljuk; a titkosítókulcs a macOS Kulcskarikába kerül. A hozzáférés az EVE fiókodban visszavonható. A CCP gyorsítótárazása miatt az ismételt frissítés nem mindig ad újabb adatot.</p></div>`);
  content.innerHTML+=state.settings.client_id?`<details class="panel skill-permissions"><summary>Másik Client ID beállítása – választható</summary>${setupHelp}</details>`:setupHelp;
  $('#save-client').onclick=async()=>{try{await api('/api/settings',{client_id:$('#client-id').value.trim()});await reloadState();toast('Client ID mentve.');render();}catch(e){error(e.message);}};
  $('#add-character').onclick=async()=>{try{error('');const result=await api('/api/auth/start',{});window.location.assign(result.url);}catch(e){error(e.message);}};
  $$('[data-remove-character]').forEach(el=>el.onclick=async()=>{if(!confirmUI('Eltávolítod ezt a karaktert és a helyben mentett adatait?'))return;try{await api('/api/characters/remove',{id:Number(el.dataset.removeCharacter)});await reloadState();render();}catch(e){error(e.message);}});
  if($('#save-characters')) $('#save-characters').onclick=async()=>{try{const checked=$$('[data-char]:checked').map(el=>Number(el.dataset.char));if(!checked.length)throw new Error('Válassz legalább egy karaktert.');await api('/api/settings',{character_ids:checked.length===state.characters.length?[]:checked});await calculate();toast('Karakterválasztás mentve.');}catch(e){error(e.message);}};
}
function renderSaved(content) {
  const plans=scopedPlans(),scopes=[{id:null,name:'Személyes'},...state.corporations.map(c=>({id:c.id,name:'Corp · '+c.name}))];
  const category=corporationId?'Corp · '+state.scope_label:'Személyes';
  setHead('MENTETT TERVEK','Tervek és készletfoglalások','Csak a kiválasztott kategória tervei láthatók. A mentés és a készletfoglalás is ehhez a gyártási körhöz tartozik.');
  content.innerHTML=`<div class="saved-categories" role="group" aria-label="Mentett tervek kategóriái">${scopes.map(s=>`<button type="button" class="button compact${s.id===corporationId?' selected':''}" data-saved-scope="${s.id??''}" aria-pressed="${s.id===corporationId}">${esc(s.name)} <span class="badge">${state.plans.filter(p=>(p.corporation_id??null)===s.id).length}</span></button>`).join('')}</div><p class="saved-category-note">Mentés helye: <strong>${esc(category)}</strong> · ${plans.length} mentett terv</p>`;
  content.innerHTML+=state.delivery_wait?deliveryWaitMarkup(state.delivery_wait):state.reservation_error?`<div class="banner error">${esc(state.reservation_error)}</div>`:'';
  content.innerHTML+=plans.length?`<div class="saved-list">${plans.map(p=>`<div class="saved-plan-card"><div class="saved-plan"><div><strong>${planLabel(p)}</strong><div class="reservation-badges"><span class="badge">${p.corporation_id?'Corp: '+esc(p.scope_label):'Személyes gyártás'}</span></div>${p.allocation_error?`<div class="warning-text">${esc(p.allocation_error)}</div>`:''}<small>${itemName(p.product_name)} · ${fmt(p.quantity)} db · ${date(p.created)}</small><div class="saved-producer">Gyártó: ${p.manufacturer_id?verbatim(state.characters.find(c=>c.id===p.manufacturer_id)?.name||String(p.manufacturer_id)):esc('még nincs kiválasztva')}</div><div class="reservation-badges"><span class="badge ${p.reserve_active?'good':''}">${p.reserve_active?'Foglalás aktív':'Nincs aktív foglalás'}</span>${p.allocation?`<span class="badge">${p.allocation.priority}. elsőbbség</span><span class="badge">${fmt(p.allocation.reserved_types)} terméktípus foglalva</span>`:''}</div>${p.allocation?`<small>Hátralévő gyártás: ${fmt(p.allocation.summary.items)} tétel · Beszerzési hiány: ${fmt(p.allocation.summary.shopping_items)} tétel</small>`:''}</div><div class="saved-actions"><button class="button compact" data-load-plan="${esc(p.id)}" aria-label="${esc(p.name)} – Terv megnyitása">Terv megnyitása</button><button class="button compact" data-toggle-reservation="${esc(p.id)}" aria-label="${esc(p.name)} – ${p.reserve_active?'Foglalás feloldása':'Foglalás bekapcsolása'}">${p.reserve_active?'Foglalás feloldása':'Foglalás bekapcsolása'}</button>${p.reserve_active?`<button class="text-button" data-reservation-detail="${esc(p.id)}" aria-label="${esc(p.name)} – Lefoglalt tételek">Lefoglalt tételek</button>`:''}<button class="text-button danger" data-remove-plan="${esc(p.id)}" aria-label="${esc(p.name)} – Terv törlése">Törlés</button></div></div></div>`).join('')}</div>`:empty('Ebben a kategóriában még nincs mentett terv','Válassz terméket, majd kattints a Terv mentése és foglalás gombra. A terv ide kerül: '+category+'.');
  content.innerHTML+='<p class="footnote">A terv a hozzá felhasznált meglévő készletet és várható jobkimenetet foglalja le; a még hiányzó anyag beszerzendő marad. A kész komponens alapanyagait nem foglalja külön. Beérkező anyagokból és a közös beállítások változásakor újraszámolódik a kiosztás. Feloldás vagy tervtörlés után a mennyiségek más tervekhez felhasználhatók. A korábbi verzióban mentett tervekhez a Foglalás bekapcsolása gombbal indítható a foglalás.</p><div id="reservation-detail"></div>';
  $$('[data-saved-scope]').forEach(el=>el.onclick=()=>setProductionScope(Number(el.dataset.savedScope)||null));
  $$('[data-load-plan]').forEach(el=>el.onclick=()=>openSavedPlan(el.dataset.loadPlan));
  $$('[data-toggle-reservation]').forEach(el=>el.onclick=async()=>{
    el.disabled=true;
    try {
      const saved=state.plans.find(p=>p.id===el.dataset.toggleReservation);
      await api('/api/plans/reservation',{id:saved.id,active:!saved.reserve_active});
      await calculate();toast(saved.reserve_active?'A foglalás feloldva.':'A foglalás bekapcsolva.');
    }catch(e){error(e.message);el.disabled=false;}
  });
  $$('[data-reservation-detail]').forEach(el=>el.onclick=()=>{
    reservationDetailId=el.dataset.reservationDetail;renderReservationDetails();
    $('#reservation-detail').scrollIntoView({block:'nearest',behavior:'smooth'});
  });
  $$('[data-remove-plan]').forEach(el=>el.onclick=async()=>{
    if(!confirmUI('Törlöd ezt a mentett tervet? A foglalása is felszabadul.'))return;
    try{await api('/api/plans/remove',{id:el.dataset.removePlan});if(activePlanId===el.dataset.removePlan)activePlanId=null;await calculate();toast('A terv törölve, a foglalása felszabadult.');}catch(e){error(e.message);}
  });
  renderReservationDetails();
}
function renderReservationDetails() {
  const target=$('#reservation-detail'), saved=state.plans.find(p=>p.id===reservationDetailId);
  if(!target)return;
  if(!saved?.reserve_active||(saved.corporation_id??null)!==corporationId){target.innerHTML='';return;}
  const a=saved.allocation;
  target.innerHTML=panel({name:saved.name,suffix:' – lefoglalt tételek'},`${fmt(saved.quantity)} db céltermék`,a?
    a.items.length?table(['Termék','Készletből (db)','Folyamatban lévő kimenetből (db)'],a.items.map(r=>`<tr><td>${item(r)}</td><td class="num">${fmt(r.stock)}</td><td class="num">${fmt(r.wip)}</td></tr>`)):
    empty('Jelenleg nincs lefoglalható készlet','A foglalás aktív. Beérkező anyagokból a terv elsőbbsége szerint részesül.'):
    empty('A foglalás most nem számolható','Ellenőrizd a fenti üzenetet és az EVE-adatokat.'));
  if(a?.blueprint_usage?.length)target.innerHTML+=panel('Lefoglalt BPC-runok', 'Csak ennek a gyártási körnek a másolatai',table(['Blueprint','Item ID','Lefoglalt run'],a.blueprint_usage.map(u=>`<tr><td>${itemName(u.name)}</td><td>${u.item_id||'Kézi runkeret'}</td><td class="num">${fmt(u.runs)}</td></tr>`)));
}
async function startTask(path) {
  if(path==='/api/sync'&&corporationId)path='/api/corporations/sync';
  try {
    error('');
    if(Object.keys(dirty).length) throw new Error('A frissítés előtt alkalmazd a megadott módosításokat.');
    await api(path,{}); await reloadState();
    if(['skills','pi','corporations','moons'].includes(view))render();
    if(!state.task.running) {
      toast(state.task.message);
      if(!['skills','pi'].includes(state.task.kind) && state.task.results.some(r=>!r.ok)) error(state.task.message);
      if(state.task.kind==='corporations'){corporationData=null;if(view==='corporations')await refreshCorporations();else await calculate(false);}
      else if(state.task.kind==='skills')await refreshSkills();
      else if(state.task.kind==='pi')await refreshPI();
      else if(['moons','extractions'].includes(state.task.kind))await refreshMoons();
      else if(state.task.kind!=='skills'){skillData=null;piData=null;await calculate(false);}
    }
  } catch(e){error(e.message);}
}
function csv(rows, headers, name) {
  const quote=value=>{let s=String(value??'');if(/^[=+@-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
  headers=headers.map(EveI18n.t);
  const blob=new Blob(['\ufeff'+[headers,...rows].map(row=>row.map(quote).join(';')).join('\r\n')],{type:'text/csv;charset=utf-8'});
  const url=URL.createObjectURL(blob), a=document.createElement('a');a.href=url;a.download='eve-'+name+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}

$('#plan-form').onsubmit=event=>{event.preventDefault();if(!productId)return error('Előbb válassz egy terméket a találatok közül.');calculate();};
$$('.nav').forEach(el=>el.onclick=()=>navigate(el.dataset.view));

$('#sync').onclick=()=>startTask('/api/sync');
$('#production-scope').onchange=event=>setProductionScope(Number(event.target.value)||null);
$('#manufacturer').onchange=async event=>{manufacturerId=event.target.value==='manual'?0:Number(event.target.value);if(productId)await calculate();};
$('#save-plan').onclick=async()=>{
  const button=$('#save-plan');button.disabled=true;
  try {
    if(Object.keys(dirty).length)throw new Error('A terv mentése előtt alkalmazd a beírt módosításokat.');
    if(!productId)throw new Error('Előbb válassz terméket a találatok közül.');
    const next=await calculate();if(!next)return;
    const saved=await api('/api/plans/save',{id:next.saved_plan?.id||null,product_id:next.product_id,quantity:next.quantity,name:next.saved_plan?.name||next.name,corporation_id:next.corporation_id,manufacturer_id:next.manufacturer_id});
    if(productId===next.product_id&&corporationId===next.corporation_id&&manufacturerId===next.manufacturer_id&&targetQuantity()===next.quantity)activePlanId=saved.id;
    await calculate();toast('A terv mentve, a készletfoglalás aktív.');
  }catch(e){error(e.message);}
  finally{button.disabled=false;}
};
$('#new-plan').onclick=async()=>{
  if(Object.keys(dirty).length)return error('Az új terv előtt alkalmazd a beírt módosításokat.');
  activePlanId=null;updatePlanControls();await calculate();
};
$('#shutdown').onclick=async()=>{if(!confirmUI('Leállítod a helyi alkalmazást? A mentett adatok megmaradnak.'))return;try{await api('/api/shutdown',{});document.body.innerHTML='<main><section class="content"><h1>A műhely leállt.</h1><p>Az indítóikonnal újra megnyithatod. Ezt a böngészőlapot bezárhatod.</p></section></main>';}catch(e){error(e.message);}};
$('#product-search').oninput=()=>{
  productId=null;activePlanId=null;updatePlanControls();clearTimeout(searchTimer);
  const q=$('#product-search').value;
  searchTimer=setTimeout(async()=>{try{
    const results=await api('/api/search?q='+encodeURIComponent(q));
    if($('#product-search').value!==q)return;
    const box=$('#search-results');box.hidden=false;$('#product-search').setAttribute('aria-expanded','true');
    box.innerHTML=results.length?results.map(r=>`<button type="button" class="search-result" role="option" data-copy-item="${esc(r.name)}" data-search-activity="${r.activity}" data-search-id="${r.id}" data-search-name="${esc(r.name)}"><span>${esc(r.name)}</span><small>${r.activity==='reaction'?'Reakció':'Gyártás'} · ${r.id}</small></button>`).join(''):'<div class="search-no-results">Nincs ilyen gyártható termék.</div>';
    $$('[data-search-id]').forEach(el=>el.onclick=()=>{productId=Number(el.dataset.searchId);productName=el.dataset.searchName;productActivity=el.dataset.searchActivity;$('#product-search').value=productName;box.hidden=true;$('#product-search').setAttribute('aria-expanded','false');$('#target-quantity').focus();updatePlanControls();});
  }catch(e){error(e.message);}},200);
};
$('#product-search').onkeydown=event=>{if(event.key==='ArrowDown'){event.preventDefault();$('#search-results button')?.focus();}if(event.key==='Escape')$('#search-results').hidden=true;};
$('#search-results').onkeydown=event=>{if(event.key==='ArrowDown'){event.preventDefault();event.target.nextElementSibling?.focus();}if(event.key==='ArrowUp'){event.preventDefault();event.target.previousElementSibling?.focus();}if(event.key==='Escape'){$('#search-results').hidden=true;$('#product-search').focus();}};
document.addEventListener('click',event=>{if(!event.target.closest('.search-wrap')){$('#search-results').hidden=true;$('#product-search').setAttribute('aria-expanded','false');}});

(async()=>{
  try {
    const saved=JSON.parse(localStorage.getItem('eve-muhely-last-plan')||'null');
    corporationId=Number(saved?.corporation_id)||null;manufacturerId=saved?.manufacturer_id??0;productActivity=saved?.activity||null;
    if(saved?.id && saved?.quantity){productId=saved.id;productName=saved.name;activePlanId=saved.saved_plan_id||null;EveNumbers.set($('#target-quantity'),saved.quantity);}
  }catch{}
  $('#product-search').value=productName;
  try {await reloadState();if(productId)await calculate(false);else render();if(new URLSearchParams(location.search).has('connected')){history.replaceState(null,'','/');const back=sessionStorage.getItem('eve-muhely-auth-return');sessionStorage.removeItem('eve-muhely-auth-return');navigate(['skills','pi','corporations'].includes(back)?back:'connection');if(back==='corporations')void startTask('/api/corporations/sync');toast('Karakter engedélyezve. Frissítsd az EVE-adatokat.');}}
  catch(e){error(e.message);}
})();
