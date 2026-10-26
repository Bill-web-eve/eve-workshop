'use strict';
let notificationData=null,notificationRequest=null,notificationScope='personal',notificationCategory='all',notificationTimer=null,notificationPermission='unknown',notificationSettingsBusy=false;
const notificationLabels={contracts:'Szerződések',intel:'Inteljelzések',implants:'Implantfigyelés',skills:'Tanulás',jobs:'Elkészült jobok',pi:'PI-termelés',moons:'Holdkitermelések',data:'Ellenőrizendő adatok'};
const notificationKinds={contract_new:'Új bejövő szerződés',contract_accepted:'Elfogadott kiadott szerződés',implant_undock:'Kidokkolás drága implantokkal',intel_near:'Közeli bejelentés',intel_kill:'Kill a régióban',training_idle:'Nem tanul',training_soon:'5 napon belül leáll a tanulás',job_ready:'Átvehető job',job_expected:'Várhatóan elkészült job',pi_idle:'A bolygó nem termel',pi_estimated:'Becsült PI-leállás',pi_extractor:'Lejárt kitermelőprogram',moon_soon:'Közelgő holdkitermelés',moon_ready:'A holdkitermelés elkészült',unknown:'Frissítés vagy engedélyezés szükséges'};
let implantAlertTimer=null,implantAlertBusy=false,implantAlertChecked=0;
function implantValue(a){return (a.partial?EveI18n.t('Legalább')+' ':'')+fmt(Number(a.value))+' ISK · '+EveI18n.t('Értékhatár')+': '+fmt(Number(a.threshold))+' ISK';}
async function pollImplantAlerts(){
  const p=notificationData?.preferences;
  if(implantAlertBusy||Date.now()-implantAlertChecked<5000||!EveDesktop.active||!p?.os_enabled||p.categories.implants===false)return;
  implantAlertBusy=true;implantAlertChecked=Date.now();
  try{const permission=await EveDesktop.notificationStatus();if(permission.status==='authorized')await deliverNotifications('/api/implants/claim');}catch{}finally{implantAlertBusy=false;}
}
function notificationDate(value){return value==null?'–':EveI18n.date(value*1000,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});}
function notificationMatches(a){return notificationScope==='personal'?!a.corporation_id:notificationScope==='corporations'?!!a.corporation_id:a.corporation_id===Number(notificationScope);}
async function refreshNotifications(deliver=true){
  if(notificationRequest)return notificationRequest;
  notificationRequest=(async()=>{
    try{
      notificationData=await api('/api/notifications');
      syncIntelNotificationSwitch();
      const count=notificationData.items.filter(a=>a.category!=='data'&&a.reliable).length;
      const badge=$('#notification-count');if(badge){badge.textContent=count?fmt(count):notificationData.counts.data?'?':'0';badge.hidden=!count&&!notificationData.counts.data;}
      if(view==='notifications'||view==='settings'&&settingsTab==='notifications'&&!Object.keys(dirty).length)render();
      if(deliver&&EveDesktop.active&&notificationData.preferences.os_enabled){
        const permission=await EveDesktop.notificationStatus();notificationPermission=permission.status;
        if(permission.status==='authorized')await deliverNotifications();
        if(notificationData.preferences.auto_refresh&&!notificationData.task.running&&state.characters.length&&Date.now()/1000>=notificationData.next_sync_at){
          await api('/api/notifications/sync',{});await reloadState();scheduleTaskPoll();
        }
      }
    }catch(e){if(view==='notifications'||view==='settings'&&settingsTab==='notifications')error(e.message);}
    finally{notificationRequest=null;}
  })();return notificationRequest;
}
function scheduleNotificationMonitor(){
  clearInterval(notificationTimer);
  notificationTimer=setInterval(()=>{if(!document.hidden&&!notificationSettingsBusy)void refreshNotifications();},60000);
  clearInterval(implantAlertTimer);implantAlertTimer=setInterval(()=>void pollImplantAlerts(),5000);
}
async function deliverNotifications(path='/api/notifications/claim'){
  const data=await api(path,{}),groups=new Map();
  for(const item of data.items){const key=JSON.stringify([item.corporation_id,item.category]);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(item);}
  for(const batch of groups.values()){
    const first=batch[0],scope=first.corporation_id?first.scope_name:EveI18n.t('Személyes');
    const body=batch.slice(0,3).map(a=>EveI18n.t(notificationKinds[a.kind])+': '+a.subject+(a.category==='contracts'?' · #'+a.contract_id+' · '+a.owner_name:'')+(a.kind==='implant_undock'?' · '+implantValue(a):a.kind==='intel_kill'?' · '+fmt(a.kill_count)+' kill'+(a.ships?.length?' · '+a.ships.map(s=>s.count+' × '+s.name).join(', '):'')+' · '+a.region_name:a.category==='intel'?' · '+a.character_name+' · '+a.jumps+' jump':'')+(a.when!=null?' · '+EveI18n.t(notificationDate(a.when)):'')).join('\n')+(batch.length>3?'\n'+EveI18n.t('További {0} jelzés'.replace('{0}',fmt(batch.length-3))):'');
    try{
      await EveDesktop.notify({id:'eve.'+first.notification_id,title:'EVE '+EveI18n.t('Műhely')+' · '+scope,body:body.slice(0,1400),scope:first.corporation_id?String(first.corporation_id):'personal',category:first.category,sound:batch.some(a=>a.sound===true)});
      await api('/api/notifications/sent',{receipts:batch.map(a=>a.receipt)});
    }catch(e){notificationPermission='error';if(view==='notifications')error(EveI18n.t('A rendszerértesítés nem küldhető el. A jelzések az alkalmazásban megmaradnak.'));break;}
  }
}
function openNotificationCenter(scope='personal',category='all'){
  if(category==='intel'){navigate('intel');void refreshIntel();return;}
  if(!navigate('notifications'))return;
  notificationScope=scope==='personal'||scope==='corporations'||/^\d+$/.test(String(scope))?String(scope):'personal';
  notificationCategory=Object.prototype.hasOwnProperty.call(notificationLabels,category)?category:'all';render();
}
function renderNotifications(content){
  setHead('ÁTTEKINTÉS','Értesítések','Tanulás, átvehető jobok, leálló PI-termelés és közelgő holdkitermelések egy helyen.');$('#plan-status').hidden=true;
  actions('<button class="button compact" id="notification-reload">Összesítés frissítése</button><button class="button primary compact" id="notification-sync">EVE-adatok ellenőrzése</button>');
  $('#notification-reload').onclick=()=>void refreshNotifications();$('#notification-sync').disabled=!!state.task.running||!state.characters.length;$('#notification-sync').onclick=async()=>{try{await api('/api/notifications/sync',{manual:true});await reloadState();render();scheduleTaskPoll();}catch(e){error(e.message);}};
  if(!notificationData){content.innerHTML=empty('Értesítések betöltése');void refreshNotifications();return;}
  const data=notificationData,items=data.items.filter(notificationMatches),corp=notificationScope!=='personal';
  content.innerHTML=`<div class="shopping-tabs"><button data-notification-scope="personal" aria-pressed="${!corp}">Személyes</button><button data-notification-scope="corporations" aria-pressed="${corp}">Corp</button><button class="text-button" data-open-settings="notifications">Értesítési beállítások</button></div>`;
  if(corp)content.innerHTML+=`<label class="notification-corp">Corporation<select id="notification-corp"><option value="corporations">Összes corporation</option>${data.corporations.map(c=>`<option data-i18n-skip value="${c.id}">${esc(c.name)}</option>`).join('')}</select></label><p class="footnote">A tanulás és a PI a karakterek személyes adata; ezeket a Személyes fülön találod. Itt corp jobok, szerződések és a corporationhöz rendelt holdak látszanak.</p>`;
  content.innerHTML+=`<div class="notification-categories">${[['all','Összes'],...Object.entries(notificationLabels)].map(([key,label])=>`<button class="button compact" data-notification-category="${key}" aria-pressed="${notificationCategory===key}">${esc(label)} <span class="badge">${fmt(key==='all'?items.length:items.filter(a=>a.category===key).length)}</span></button>`).join('')}</div>`;
  const visible=items.filter(a=>notificationCategory==='all'||a.category===notificationCategory);
  content.innerHTML+=panel('Aktuális jelzések',`${fmt(visible.length)} jelzés`,visible.length?table(['Jelzés','Tétel','Karakter','Időpont','Adat ideje','Állapot','Művelet'],visible.map(a=>`<tr><td><strong>${esc(notificationKinds[a.kind])}</strong><div class="batch-note">${esc(notificationLabels[a.source_category||a.category])}</div></td><td>${['jobs','pi','moons'].includes(a.category)?itemName(a.subject):verbatim(a.subject)}${a.kind==='intel_kill'?`<div>${fmt(a.kill_count)} kill${a.ships?.length?' · '+esc(a.ships.map(s=>s.count+' × '+s.name).join(', ')):''}</div>`:''}${a.category==='contracts'?'<div>#'+a.contract_id+' · '+esc(a.owner_name)+'</div>':''}${a.kind==='implant_undock'?'<div>'+esc(implantValue(a))+'</div>':''}${a.volume!=null?`<div>${fmt(a.volume)} m³${a.estimated?' · <span>Becslés</span>':''}</div>`:''}${a.ownership_unknown?'<div class="batch-note">Nincs corp-hozzárendelés</div>':''}</td><td data-filter-value="${esc(a.character_name||a.category==='skills'&&a.subject||'–')}">${esc(a.character_name||a.category==='skills'&&a.subject||'–')}${a.corporation_id?`<div data-i18n-skip>${esc(a.scope_name)}</div>`:''}</td><td data-sort-value="${a.when??''}">${esc(notificationDate(a.when))}</td><td data-sort-value="${a.checked_at??''}">${esc(notificationDate(a.checked_at))}</td><td><span class="badge ${a.reliable?'warn':''}">${a.reliable?a.estimated||a.kind==='job_expected'?'Becslés':'Jelzett állapot':'Korábbi / nem ellenőrizhető adat'}</span></td><td><div class="notification-row-actions"><button class="text-button" data-notification-open="${esc(a.id)}">Megnyitás</button><button class="button compact" data-notification-dismiss="${esc(a.id)}">Tudomásul vettem</button></div></td></tr>`),'notification-table'):empty('Nincs ilyen jelzés','Az ismeretlen adatok nem jelentenek igazolt hibamentes működést.'));
  content.innerHTML+=`<p class="footnote">A lista a helyben betöltött EVE-adatokból és jelölt becslésekből készül. A lejárt, hibás vagy hiányzó adatok külön ellenőrizendők. Holdelőrejelzés: ${fmt(data.preferences.moon_days)} nap. Rendszerértesítés és automatikus ellenőrzés csak futó alkalmazás mellett működik, háttérben is.</p>`;
  $$('[data-notification-scope]').forEach(b=>b.onclick=()=>{notificationScope=b.dataset.notificationScope;render();});
  if($('#notification-corp')){$('#notification-corp').value=notificationScope;$('#notification-corp').onchange=e=>{notificationScope=e.target.value;render();};}
  $$('[data-notification-category]').forEach(b=>b.onclick=()=>{notificationCategory=b.dataset.notificationCategory;render();});
  $$('[data-notification-dismiss]').forEach(b=>b.onclick=async()=>{
    const a=data.items.find(a=>a.id===b.dataset.notificationDismiss);if(!a)return;
    b.disabled=true;try{await api('/api/notifications/dismiss',{id:a.id,dismissal_key:a.dismissal_key});await refreshNotifications(false);toast('Az értesítés tudomásul véve.');}catch(e){error(e.message);b.disabled=false;}
  });
  $$('[data-notification-open]').forEach(b=>b.onclick=()=>{
    const a=data.items.find(a=>a.id===b.dataset.notificationOpen);
    if(a.category==='contracts'){contractScope=a.contract_scope;contractOwner=String(a.owner_id);contractStart='';contractEnd='';contractError='';contractSelected=a.contract_id;contractDetail=null;contractDetailRequest=null;contractData=null;contractRevision++;navigate('contracts');}
    else if(a.category==='implants')openSettingsTab('notifications');
    else if(a.category==='intel')showIntelSystem(a.system_id);
    else if(a.category==='skills'){skillSelectedId=a.character_id;navigate('skills');}
    else if(a.category==='pi'){piSelected=`${a.character_id}:${a.planet_id}`;navigate('pi');}
    else if(a.category==='moons')selectMoonTab('calendar');
    else if(a.category==='jobs'){if(Object.keys(dirty).length)return;navigate('jobs');void setProductionScope(a.corporation_id||null);}
    else openSettingsTab('access');
  });
}
function renderNotificationSettings(target){
  if(!notificationData){target.innerHTML=empty('Értesítések betöltése');void refreshNotifications(false);return;}
  const p=notificationData.preferences;
  const status={unknown:'Még nincs ellenőrizve',authorized:'Engedélyezve',denied:'Az operációs rendszer letiltotta',notDetermined:'Még nincs engedélyezve',unavailable:'Ebben az ablakban nem támogatott',error:'Az értesítés nem küldhető el'};
  target.innerHTML=panel('Rendszerértesítések','',`<div class="panel-body"><p>A rendszerértesítéseket külön engedélyezheted. Ugyanazt az eseményt egy aktív időszakban egyszer jelezzük; az újraindítás és az ismételt adatfrissítés nem küldi újra. Több egyidejű jelzést típusonként és tulajdonosonként összevonunk.</p><p>${esc(status[EveDesktop.active?notificationPermission:'unavailable']||status.error)}</p><div class="actions"><button class="button primary" id="notification-permission" ${!EveDesktop.active?'disabled':''}>Rendszerértesítések engedélyezése</button><button class="button" id="notification-test" ${!EveDesktop.active?'disabled':''}>Tesztértesítés</button></div><form id="notification-preferences" class="notification-preferences"><label><input type="checkbox" name="os_enabled" ${p.os_enabled?'checked':''}> Rendszerértesítések bekapcsolva</label><label><input type="checkbox" name="auto_refresh" ${p.auto_refresh?'checked':''}> EVE-adatok automatikus ellenőrzése 15 percenként</label><label><input type="checkbox" name="personal" ${p.personal?'checked':''}> Személyes jelzések</label><label><input type="checkbox" name="corporations" ${p.corporations?'checked':''}> Corp jelzések</label>${Object.entries(notificationLabels).filter(([k])=>k!=='data').map(([key,label])=>`<label><input type="checkbox" name="category-${key}" ${p.categories[key]?'checked':''}> ${esc(label)}</label>`).join('')}<label>Holdelőrejelzés (nap)<input type="number" name="moon_days" min="1" max="30" required value="${p.moon_days}"></label><div class="field-full"><button class="button primary" type="submit">Beállítások mentése</button></div></form><p class="footnote">Bezárt alkalmazás mellett nincs új EVE-ellenőrzés és nincs új rendszerértesítés. Az operációs rendszer Fókusz / Ne zavarjanak módja és értesítési beállításai befolyásolják a megjelenést. Az EVE gyorsítótárát tiszteletben tartjuk.</p></div>`);
  target.innerHTML+=implantSettingsPanel(notificationData.implants);
  if(notificationData.moons.length)target.innerHTML+=panel('Holdak értesítési tulajdonosa','Automatikus: ESI corporation-időzítő alapján; ismeretlen tulajdonos a Személyes fülön marad.',`<form id="notification-moon-owners" class="panel-body">${table(['Hold','Értesítési kör'],notificationData.moons.map(m=>`<tr><td>${verbatim(m.name)}</td><td><select data-notification-moon="${esc(m.id)}"><option value="auto">Automatikus</option><option value="personal">Személyes</option>${notificationData.corporations.map(c=>`<option data-i18n-skip value="${c.id}">${esc(c.name)}</option>`).join('')}</select></td></tr>`))}<button class="button compact" type="submit">Hold-hozzárendelések mentése</button></form>`);
  // Bind after all panel markup is added; innerHTML += replaces existing nodes.
  bindImplantSettings();
  $('#notification-preferences').onsubmit=async e=>{e.preventDefault();notificationSettingsBusy=true;try{
    const form=e.target,body={};for(const key of ['os_enabled','auto_refresh','personal','corporations'])body[key]=form.elements[key].checked;
    body.moon_days=Number(form.elements.moon_days.value);body.categories=Object.fromEntries(Object.keys(p.categories).map(k=>[k,form.elements['category-'+k].checked]));
    if(body.os_enabled&&EveDesktop.active){const permission=await EveDesktop.notificationStatus();if(permission.status!=='authorized')throw Error('Előbb engedélyezd a rendszerértesítéseket a fenti gombbal.');}
    const preferences=await api('/api/notifications/preferences',body);
    if(typeof applyIntelNotificationPreferences==='function')await applyIntelNotificationPreferences(preferences);
    delete dirty.notification_preferences;await refreshNotifications();toast('Beállítások mentve.');
  }catch(e){error(e.message);}finally{notificationSettingsBusy=false;}};
  $('#notification-preferences').oninput=()=>{dirty.notification_preferences=true;};
  const savePermission=async()=>{notificationSettingsBusy=true;try{const result=await EveDesktop.requestNotifications();notificationPermission=result.status;if(result.status==='authorized'){if(Object.keys(dirty).length){$('#notification-preferences').elements.os_enabled.checked=true;dirty.notification_preferences=true;}else await api('/api/notifications/preferences',{os_enabled:true});}await refreshNotifications();render();}catch(e){error(e.message);}finally{notificationSettingsBusy=false;}};
  $('#notification-permission').onclick=savePermission;
  $('#notification-test').onclick=async()=>{try{const result=await EveDesktop.notificationStatus();notificationPermission=result.status;if(result.status!=='authorized')throw Error('Előbb engedélyezd a rendszerértesítéseket a fenti gombbal.');await EveDesktop.notify({id:'eve-test-'+Date.now(),title:'EVE '+EveI18n.t('Műhely'),body:EveI18n.t('A rendszerértesítések működnek.'),scope:'personal',category:'all',sound:true});}catch(e){error(e.message);}};
  $$('[data-notification-moon]').forEach(el=>{const owner=p.moon_owners[el.dataset.notificationMoon];el.value=owner===undefined?'auto':owner===null?'personal':String(owner);el.onchange=()=>dirty.notification_owners=true;});
  if($('#notification-moon-owners'))$('#notification-moon-owners').onsubmit=async e=>{e.preventDefault();try{const owners={};$$('[data-notification-moon]').forEach(el=>{if(el.value!=='auto')owners[el.dataset.notificationMoon]=el.value==='personal'?null:Number(el.value);});await api('/api/notifications/preferences',{moon_owners:owners});delete dirty.notification_owners;await refreshNotifications();}catch(e){error(e.message);}};
  if(EveDesktop.active&&notificationPermission==='unknown')void EveDesktop.notificationStatus().then(p=>{notificationPermission=p.status;if(view==='settings'&&settingsTab==='notifications')render();});
}
function implantSettingsPanel(data){
  if(!data)return '';
  return panel('Implantfigyelés kidokkoláskor','Jita sell',`<div class="panel-body"><p>A figyelt karakter kidokkolásakor jelez, ha az aktív klón implantjainak becsült összértéke meghaladja az értékhatárt. A helyzetet 5 másodpercenként, az implantokat az EVE legalább 120 másodperces gyorsítótárához igazodva ellenőrizzük. Klónváltás után még korábbi adat érkezhet.</p><form id="implant-preferences">${table(['Karakter','Figyelés','Értékhatár (ISK)','Becsült implantérték','Állapot','Hozzáférés'],data.characters.map(c=>`<tr><td>${verbatim(c.name)}</td><td><input type="checkbox" aria-label="${esc(c.name)}" data-implant-enabled="${c.id}" ${c.enabled?'checked':''}></td><td><input type="text" inputmode="decimal" data-grouped-money data-implant-threshold="${c.id}" aria-label="${esc(c.name)} ISK" required value="${esc(EveNumbers.moneyFormat(c.threshold))}"></td><td>${c.value==null?'–':fmt(Number(c.value))+' ISK'}${c.missing?.length?'<div class="warning-text">Hiányos árbecslés</div>':''}${c.implants_at?'<div class="batch-note">'+esc(notificationDate(c.implants_at))+'</div>':''}</td><td>${!c.enabled?'Kikapcsolva':!c.authorized?'Implantfigyelési engedély szükséges.':c.checking?'Implantadatok ellenőrzése…':c.error?esc(c.error):c.checked_at?c.docked?'Dokkolva':'Űrben':'Várakozás helyzetadatra'}</td><td><button class="text-button" type="button" data-implant-authorize="${c.id}">Implantfigyelés engedélyezése</button></td></tr>`),'implant-settings')}<div class="actions"><button class="button primary compact" type="submit">Implantfigyelés mentése</button><button class="button compact" type="button" id="implant-status-refresh">Állapot frissítése</button></div></form><p class="footnote">A rendszerértesítések, a Személyes jelzések és az Implantfigyelés kapcsolója is legyen bekapcsolva. Kidokkolásonként egyszer jelez. Indításkor már űrben lévő karakterre nem küld visszamenőleges riasztást. Hiányzó ár esetén csak az ismert részösszeggel számol.</p><details><summary>Szükséges jogosultságok</summary><code>${data.scopes.map(esc).join('\n')}</code><p>Az új scope-okat az EVE Developer alkalmazásban is engedélyezni kell. A meglévő karaktert válaszd újra az engedélyezéskor.</p></details></div>`);
}
function bindImplantSettings(){
  const form=$('#implant-preferences');if(!form)return;
  form.oninput=()=>dirty.implant_preferences=true;
  form.onsubmit=async event=>{event.preventDefault();notificationSettingsBusy=true;try{
    const characters=$$('[data-implant-enabled]').map(input=>({id:Number(input.dataset.implantEnabled),enabled:input.checked,threshold:EveNumbers.moneyParse($(`[data-implant-threshold="${input.dataset.implantEnabled}"]`).value)}));
    await api('/api/implants/preferences',{characters});delete dirty.implant_preferences;await refreshNotifications(false);toast('Implantfigyelés mentve.');
  }catch(e){error(e.message);}finally{notificationSettingsBusy=false;}};
  $('#implant-status-refresh').onclick=()=>void refreshNotifications(false);
  $$('[data-implant-authorize]').forEach(button=>button.onclick=async()=>{try{
    const auth=await api('/api/auth/start',{character_id:Number(button.dataset.implantAuthorize),feature:'implants'});
    sessionStorage.setItem('eve-muhely-auth-return','settings:notifications');await openEveAuthorization(auth);
  }catch(e){error(e.message);}});
}
