'use strict';
let moonCalendarMonth=new Date().toISOString().slice(0,7),crystalMoonId='',crystalEventId='',crystalGeneration=0;
const moonTime=value=>value?new Intl.DateTimeFormat(EveI18n.locale,{dateStyle:'medium',timeStyle:'short',timeZone:'UTC'}).format(new Date(typeof value==='number'?value*1000:value))+' UTC':'–';
function moonWarnings(d){
  const applicable=d.moons.filter(m=>m.enabled&&m.structure==='Athanor');
  const calendar=applicable.filter(m=>m.extraction_status==='calendar_only');
  const missing=applicable.filter(m=>m.extraction_status==='missing'),unknown=applicable.filter(m=>['unknown','stale'].includes(m.extraction_status));
  return (missing.length?`<div class="banner warn" role="alert"><strong>Nem található beállított extraction a hozzáférhető ESI-adatokban:</strong> ${missing.map(m=>verbatim(m.name)).join(', ')}. <span>Ellenőrizd a fúró időzítését és a tulajdonos corporation hozzáférését.</span></div>`:'')+(unknown.length?`<div class="banner warn"><strong>A kitermelés nem ellenőrizhető vagy az adat elavult:</strong> ${unknown.map(m=>verbatim(m.name)).join(', ')}. <span>A Beállítások → Adathozzáférések oldalon engedélyezd és frissítsd a holdadatokat.</span></div>`:'')+(calendar.length?`<div class="banner"><strong>ESI-naptárból ismert kitermelési időpont:</strong> ${calendar.map(m=>verbatim(m.name)).join(', ')}. <span>A naptár az érkezés idejét közli; ércmennyiséget és széttörési időt nem feltétlenül ad meg.</span></div>`:'');
}
function moonSource(source){return source==='esi_notification'?'ESI értesítés · automatikus':source==='esi_calendar'?'ESI naptár · automatikus':source==='manual'?'Kézi arány × ESI időtartam':'Nincs ércadat';}
function moonAccessStatus(resource){
  if(!resource)return '<span class="muted">Még nincs lekérdezés</span>';
  if(resource.scope_granted===false)return '<span class="muted">Nincs engedélyezve</span>';
  if(resource.error)return `<span class="${resource.scope_granted===false?'muted':'warning-text'}">${esc(resource.error)}</span>`;
  if(!resource.fetched)return `<span>${resource.scope_granted?'Engedélyezve · frissítésre vár':'Még nincs lekérdezés'}</span>`;
  return `<span class="badge ${resource.stale?'warn':'good'}">${resource.stale?'Frissítés szükséges':'Rendben'}</span> <span>${fmt(resource.count||0)}</span> <span>bejegyzés</span> · ${date(resource.fetched)}`;
}
function moonAuthPanel(){
  const access=[...moonData.extractions.access].sort((a,b)=>Number([b.moon_calendar,b.moon_timers,b.moon_notifications].some(r=>r?.scope_granted))-Number([a.moon_calendar,a.moon_timers,a.moon_notifications].some(r=>r?.scope_granted))),issues=moonData.extractions.notification_issues||[];
  return panel('Holdadatok hozzáférése','Naptár, kitermelési időzítők és ércértesítések',`<div class="panel-body"><button id="extraction-refresh" class="button compact" ${state.task.running?'disabled':''}>↻ Holdadatok frissítése</button><p><span>Engedélyezett olvasók</span>: <span>Naptár</span> ${access.filter(c=>c.moon_calendar?.scope_granted).length} · <span>Corporation időzítők</span> ${access.filter(c=>c.moon_timers?.scope_granted).length} · <span>Ércértesítések</span> ${access.filter(c=>c.moon_notifications?.scope_granted).length}</p><p>Az ércmennyiségek elsődleges forrása a karakter holdkitermelési értesítése. A naptár és a corporation időzítő külön hozzáférés.</p><details id="moon-access-characters"><summary>Karakterek hozzáférése és engedélyezése</summary>${access.length?access.map(c=>`<div class="moon-access"><strong>${verbatim(c.name)}</strong><div><span>Naptár</span>: ${moonAccessStatus(c.moon_calendar)}</div><div><span>Corporation időzítők</span>: ${moonAccessStatus(c.moon_timers)}</div><div><span>Ércértesítések</span>: ${moonAccessStatus(c.moon_notifications)}</div><button class="text-button" data-moon-auth="${c.id}">${[c.moon_calendar,c.moon_timers,c.moon_notifications].every(r=>r?.scope_granted)?'Hozzáférés újraengedélyezése':'Holdadatok engedélyezése'}</button></div>`).join(''):'<p>Előbb adj hozzá karaktert az EVE-kapcsolat oldalon.</p>'}</details>${issues.length?'<div class="banner warn">Néhány holdértesítés ércadata nem értelmezhető. Ezek nem írják felül a kézi összetételt.</div>':''}<details><summary>Technikai részletek és szükséges jogosultságok</summary><p data-i18n-skip>esi-calendar.read_calendar_events.v1<br>esi-industry.read_corporation_mining.v1<br>esi-characters.read_notifications.v1</p><p>A corporation időzítőkhöz a fúró tulajdonos corporationjében Station Manager szerepkör kell. Az értesítésekhez olyan karakter szükséges, aki megkapja a holdkitermelési értesítéseket.</p><p>Ha invalid_scope hibát kapsz, az EVE Developer alkalmazásban is engedélyezd a felsorolt scope-okat. Az új értesítési engedélyhez egyszeri újrabelépés szükséges.</p></details></div>`);
}
function bindMoonAuth(){
  $('#extraction-refresh').onclick=()=>startTask('/api/moons/extractions/sync');
  $$('[data-moon-auth]').forEach(b=>b.onclick=async()=>{try{b.disabled=true;const data=await api('/api/auth/start',{feature:'moons',character_id:Number(b.dataset.moonAuth)});sessionStorage.setItem('eve-muhely-auth-return','settings:access');await openEveAuthorization(data);}catch(e){b.disabled=false;error(e.message);}});
}
let moonCalendarFeed=null,moonCalendarFeedRequest=null;
function calendarFeedURL(url){return url+'?lang='+EveI18n.language;}
function calendarIntegrationPanel(){
  const feed=moonCalendarFeed;
  return `<section class="panel calendar-subscription" id="moon-calendar-integration"><div class="panel-head"><h2>Helyi naptár szinkronizálása</h2></div><div class="panel-body">
    <p>A hold neve és a kőzet megérkezése kerül a naptárba. Az összes működő Athanor betöltött kitermelése szerepel benne, a nézet szűrőjétől és hónapjától függetlenül.</p>
    <a class="button compact" href="/api/moons/calendar.ics?lang=${EveI18n.language}" download="eve-moon-extractions.ics">ICS letöltése</a>
    ${feed?.enabled?`<a class="button primary compact" id="moon-calendar-subscribe" href="${esc(calendarFeedURL(feed.webcal_url))}">Feliratkozás a helyi naptárban</a><label>Feliratkozási hivatkozás<input id="moon-calendar-url" data-i18n-skip readonly value="${esc(calendarFeedURL(feed.url))}"></label><button class="button compact" id="moon-calendar-copy">Hivatkozás másolása</button><button class="text-button" data-feed-action="reset">Új hivatkozás</button><button class="text-button" data-feed-action="disable">Szinkronizálás letiltása</button>`:`<button class="button primary compact" data-feed-action="enable" ${feed?'':'disabled'}>Naptárszinkron engedélyezése</button>`}
    <p class="footnote">Macen a Naptár alkalmazásban válaszd a helyi, Saját Mac naptárat és az óránkénti frissítést. Az appnak futnia kell a lekéréskor; csak az EVE-ből már betöltött adatok frissülnek. A localhost hivatkozást felhős naptárszolgáltatás nem tudja lekérni. Az ICS letöltése egyszeri másolat, nem automatikus szinkron.</p>
    <p class="footnote">Az időpontokat a naptár a saját időzónájában jeleníti meg. A feliratkozás csak olvasható. Az új hivatkozás érvényteleníti a régit; utána újra fel kell iratkozni.</p>
  </div></section>`;
}
window.addEventListener('eve-language-change',()=>{
  const download=$('#moon-calendar-integration a[download]');if(download)download.href='/api/moons/calendar.ics?lang='+EveI18n.language;
  const subscribe=$('#moon-calendar-subscribe'),input=$('#moon-calendar-url');
  if(moonCalendarFeed?.enabled){if(subscribe)subscribe.href=calendarFeedURL(moonCalendarFeed.webcal_url);if(input)input.value=calendarFeedURL(moonCalendarFeed.url);}
});
function bindCalendarIntegration(){
  if(moonCalendarFeed===null&&!moonCalendarFeedRequest){
    moonCalendarFeedRequest=api('/api/moons/calendar').then(feed=>{moonCalendarFeed=feed;if(view==='settings'&&settingsTab==='calendar'&&$('#moon-calendar-integration')){const panel=$('#moon-calendar-integration');panel.outerHTML=calendarIntegrationPanel();bindCalendarIntegration();}}).catch(e=>{if(view==='settings'&&settingsTab==='calendar')error(e.message);}).finally(()=>{moonCalendarFeedRequest=null;});
  }
  $$('[data-feed-action]').forEach(button=>button.onclick=async()=>{
    const action=button.dataset.feedAction;
    if(action!=='enable'&&!confirmUI('A korábbi naptárhivatkozás nem fog tovább frissülni. Folytatod?'))return;
    try{button.disabled=true;moonCalendarFeed=await api('/api/moons/calendar',{action});const panel=$('#moon-calendar-integration');if(panel){panel.outerHTML=calendarIntegrationPanel();bindCalendarIntegration();}}
    catch(e){button.disabled=false;error(e.message);}
  });
  const copy=$('#moon-calendar-copy');if(copy)copy.onclick=async()=>{
    const input=$('#moon-calendar-url');
    try{if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(input.value);else{input.focus();input.select();if(!document.execCommand('copy'))throw Error();}toast('Naptárhivatkozás másolva.');}
    catch{input.focus();input.select();error('A másolás nem sikerült. Másold ki a kijelölt hivatkozást.');}
  };
}
function renderMoonCalendar(target,moons){
  const ids=new Set(moons.filter(m=>m.structure==='Athanor').map(m=>m.id)),events=moonData.extractions.events.filter(e=>ids.has(e.moon_record_id));
  const first=new Date(moonCalendarMonth+'-01T00:00:00Z'),start=new Date(first);start.setUTCDate(1-(first.getUTCDay()+6)%7);
  const dayKey=d=>d.toISOString().slice(0,10);
  const cells=Array.from({length:42},(_,i)=>{const day=new Date(start.getTime()+i*86400000),key=dayKey(day),entries=events.filter(e=>e.date.slice(0,10)===key);return `<div class="moon-calendar-day ${day.getUTCMonth()===first.getUTCMonth()?'':'outside'}"><time datetime="${key}">${day.getUTCDate()}</time>${entries.map(e=>`<button class="moon-calendar-event ${e.stale?'stale':''}" data-calendar-event="${esc(e.id)}"><span data-i18n-skip>${esc(e.date.slice(11,16))} · ${esc(e.moon_name)}</span><small>${e.volume==null?'–':fmt(e.volume)} m³</small></button>`).join('')}</div>`;}).join('');
  const calendarGrid=`<div class="banner">A naptár UTC időt mutat. Az ESI natural_decay_time az automatikus széttörés időpontja. Az ércek eltűnését a széttörés és a holdnál megadott élettartam alapján becsüljük; a korábbi kézi széttörés és a rig módosíthatja.</div><div class="moon-toolbar"><button id="moon-prev-month" class="button compact" aria-label="Előző hónap">←</button><label>Hónap<input id="moon-calendar-month" type="month" value="${moonCalendarMonth}"></label><button id="moon-next-month" class="button compact" aria-label="Következő hónap">→</button></div><div class="moon-calendar" aria-label="Kitermelési naptár">${Array.from({length:7},(_,i)=>`<div class="moon-calendar-weekday" data-i18n-skip>${new Intl.DateTimeFormat(EveI18n.locale,{weekday:'short',timeZone:'UTC'}).format(new Date(Date.UTC(2026,0,5+i)))}</div>`).join('')}${cells}</div><div id="extraction-details"></div>`;
  const extractionTable=panel('Kitermelések és várható ércek','Az ércarányok forrása minden sorban látható',events.length?moonTable(['Hold','Érkezés · UTC','Automatikus széttörés · UTC','Érctérfogat (m³)','Összetétel forrása','Ércek eltűnése · becsült tartomány'],events.map(e=>`<tr><td><button class="text-button" data-calendar-event="${esc(e.id)}">${verbatim(e.moon_name)}</button></td><td data-sort-value="${Date.parse(e.date)}">${moonTime(e.date)}${e.timing_source==='esi_calendar'?'<div class="muted">ESI naptár · kitermelési időpont</div>':''}</td><td>${moonTime(e.natural_decay_time)}</td><td class="num">${e.volume==null?'–':fmt(e.volume)}</td><td><span>${moonSource(e.composition_source)}</span>${e.kind.includes('history')?' · <span>Korábbi esemény</span>':''}${e.stale?' · <span>Régi adat</span>':''}</td><td>${moonTime(e.belt_earliest_expiry)} — ${moonTime(e.belt_latest_expiry)}</td></tr>`),'extraction-events'):empty('Nincs hozzáférhető kitermelési esemény'));
  target.innerHTML='<p><button class="text-button" data-open-settings="access">Holdadatok hozzáférésének beállítása</button> · <button class="text-button" data-open-settings="calendar">Naptárszinkron beállítása</button></p>'+extractionTable+calendarGrid;
  const change=amount=>{const date=new Date(moonCalendarMonth+'-01T00:00:00Z');date.setUTCMonth(date.getUTCMonth()+amount);moonCalendarMonth=date.toISOString().slice(0,7);renderMoonBody();};
  $('#moon-prev-month').onclick=()=>change(-1);$('#moon-next-month').onclick=()=>change(1);
  $('#moon-calendar-month').onchange=e=>{if(/^\d{4}-\d{2}$/.test(e.target.value)){moonCalendarMonth=e.target.value;renderMoonBody();}};
  $$('[data-calendar-event]').forEach(b=>b.onclick=()=>showExtraction(events.find(e=>e.id===b.dataset.calendarEvent)));
}
function showExtraction(event){
  if(!event)return;
  $('#extraction-details').innerHTML=panel(event.moon_name,moonTime(event.date),`<div class="panel-body"><p>${event.timing_source==='esi_calendar'?'A kitermelés időpontja az EVE naptáreseményéből származik. A holdat az ESI-azonosítója alapján párosítjuk.':''}</p><p>${event.volume_source==='esi_notification'?'A kitermelési értesítésben közölt érctérfogatok.':event.volume_source==='esi_calendar'?'ESI naptárból kiolvasott érctérfogatok.':event.volume_source==='duration_estimate'?'Becslés az ESI kitermelési időtartamából, kézi ércarányokkal.':'A naptárbejegyzés nem ad ércmennyiséget.'}</p>${event.stale?'<p class="warning-text">Régi adat · frissítés szükséges.</p>':''}${event.fractured_at?`<p><span>Megfigyelt széttörés</span>: ${moonTime(event.fractured_at)}</p>`:''}${event.notification_id?`<p><span>Értesítés ideje</span>: ${moonTime(event.notification_observed_at)} · <span>Értesítés ID</span>: ${event.notification_id}</p>`:''}${event.ores.length?moonTable(['Érc','Arány','Érctérfogat (m³)'],(event.raw_ores||event.ores).map(o=>`<tr><td>${itemName(o.name)}</td><td>${moonPercent(o.percent??o.volume/event.volume*100)}</td><td class="num">${fmt(o.volume)}</td></tr>`),'extraction-detail'):''}<button id="crystals-for-event" class="button compact">Kristályterv ehhez a kitermeléshez</button></div>`);
  $('#crystals-for-event').onclick=()=>{crystalMoonId=event.moon_record_id;crystalEventId=event.id;moonTab='crystals';render();};
  $('#extraction-details').scrollIntoView?.({block:'nearest'});
}
function renderCrystalPlanner(target,moons){
  const d=moonData,p=d.settings;
  if(!moons.some(m=>m.id===crystalMoonId)){crystalMoonId=moons.find(m=>m.structure==='Athanor')?.id||moons[0]?.id||'';crystalEventId='';}
  const events=d.extractions.events.filter(e=>e.moon_record_id===crystalMoonId);
  if(crystalEventId&&!events.some(e=>e.id===crystalEventId))crystalEventId='';
  target.innerHTML=`<div class="banner">A kristályarányt 1–9 közötti egész számokkal mutatjuk. A kis pontos arányokat megtartjuk, például 75% és 25% esetén 3:1. Egyébként a legnagyobb értéket 9-re skálázzuk, minden értéket felfelé kerekítünk, majd egyszerűsítünk. Kopást nem számolunk.</div><div class="moon-toolbar"><label>Hold<select id="crystal-moon">${moons.map(m=>`<option data-i18n-skip value="${esc(m.id)}">${esc(m.name)} · ${m.structure}</option>`).join('')}</select></label><label>Számítási időszak<select id="crystal-event"><option value="">30 napos becslés</option>${events.map(e=>`<option data-i18n-skip value="${esc(e.id)}">${moonTime(e.date)}${e.stale?' · '+EveI18n.t('Régi adat'):''}</option>`).join('')}</select></label></div><p><span>Kristályváltozat</span>: ${verbatim(p.crystal_variant)} · <button class="text-button" data-open-settings="moons">Kristálybeállítások</button></p><div id="crystal-result"></div>`;
  $('#crystal-moon').value=crystalMoonId;$('#crystal-event').value=crystalEventId;
  const change=fn=>e=>{if(dirty.moon_crystals&&!confirmUI('Vannak még nem alkalmazott módosítások. Elhagyod ezt az oldalt?')){e.target.value=e.target.id==='crystal-moon'?crystalMoonId:crystalEventId;return;}dirty={};fn(e);renderMoonBody();};
  $('#crystal-moon').onchange=change(e=>{crystalMoonId=e.target.value;crystalEventId='';});$('#crystal-event').onchange=change(e=>{crystalEventId=e.target.value;});
  void loadCrystalPlan();
}
async function loadCrystalPlan(){
  const generation=++crystalGeneration;if(!crystalMoonId)return;
  try{const result=await api('/api/moons/crystals?moon_id='+encodeURIComponent(crystalMoonId)+(crystalEventId?'&event_id='+encodeURIComponent(crystalEventId):''));if(generation!==crystalGeneration||moonTab!=='crystals'||!$('#crystal-result'))return;
    $('#crystal-result').innerHTML=result.automatic?'<div class="banner">A Metenox nem igényel bányászkristályt.</div>':result.unavailable?'<div class="banner warn">Nincs használható érctérfogat; ellenőrizd a hold összetételét és a kitermelési adatot.</div>':panel('Szükséges kristályok a kiválasztott holdhoz','1–9 közötti kristályarány · kopás nélkül',moonTable(['Kristály','Ércek','Érctérfogat (m³)','Arány','Arányos kristálydarabszám'],result.rows.map(c=>`<tr><td>${itemName(c.name)}</td><td>${c.ores.map(itemName).join(', ')}</td><td class="num">${fmt(c.volume)}</td><td class="num">${moonPercent(c.share)}</td><td class="num"><strong>${fmt(c.count)}</strong></td></tr>`),'selected-crystals'))+'<p class="footnote">Ez közelítő készletarány, nem a bányászat során elkopó kristályok száma. Minden szükséges kristálytípus legalább 1 darabot kap.</p>' ;
  }catch(e){if(generation===crystalGeneration&&moonTab==='crystals')error(e.message);}
}
