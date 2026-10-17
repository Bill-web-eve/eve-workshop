'use strict';
let moonCalendarMonth=new Date().toISOString().slice(0,7),crystalMoonId='',crystalEventId='',crystalGeneration=0;
const moonTime=value=>value?new Intl.DateTimeFormat(EveI18n.locale,{dateStyle:'medium',timeStyle:'short',timeZone:'UTC'}).format(new Date(typeof value==='number'?value*1000:value))+' UTC':'–';
function moonWarnings(d){
  const applicable=d.moons.filter(m=>m.enabled&&m.structure==='Athanor');
  const missing=applicable.filter(m=>m.extraction_status==='missing'),unknown=applicable.filter(m=>['unknown','stale','calendar_only'].includes(m.extraction_status));
  return (missing.length?`<div class="banner warn" role="alert"><strong>Nem található beállított extraction a hozzáférhető ESI-adatokban:</strong> ${missing.map(m=>verbatim(m.name)).join(', ')}. <span>Ellenőrizd a fúró időzítését és a tulajdonos corporation hozzáférését.</span></div>`:'')+(unknown.length?`<div class="banner warn"><strong>A kitermelés nem ellenőrizhető vagy az adat elavult:</strong> ${unknown.map(m=>verbatim(m.name)).join(', ')}. <span>A Kitermelési naptár fülön engedélyezd és frissítsd a holdadatokat.</span></div>`:'');
}
function moonAuthPanel(){
  const access=moonData.extractions.access;
  return panel('Holdadatok hozzáférése','Naptár és corporation kitermelési időzítők',`<div class="panel-body"><button id="extraction-refresh" class="button compact" ${state.task.running?'disabled':''}>↻ Naptár és extraction frissítése</button><p data-i18n-skip>Scopes: esi-calendar.read_calendar_events.v1 · esi-industry.read_corporation_mining.v1</p><p>Ha az EVE invalid_scope hibát ad, az EVE Developer alkalmazásban is engedélyezni kell ezt a két scope-ot.</p><p>Az ESI időzítő nem ad ércösszetételt. Ha a naptárszövegben nincs egyértelmű ércenkénti m³, a kézi arány marad.</p><p>A naptárhoz olvasási engedély, a corporation időzítőihez a tulajdonos corporation megfelelő szerepköre is szükséges. Bérelt, más corporation tulajdonában lévő fúró nem feltétlenül látható.</p>${access.length?access.map(c=>`<div class="moon-access"><strong>${verbatim(c.name)}</strong><span>Naptár</span> ${c.moon_calendar.error?esc(c.moon_calendar.error):date(c.moon_calendar.fetched)} · <span>Időzítők</span> ${c.moon_timers.error?esc(c.moon_timers.error):date(c.moon_timers.fetched)} <button class="text-button" data-moon-auth="${c.id}">Holdadatok engedélyezése</button></div>`).join(''):'<p>Előbb adj hozzá karaktert az EVE-kapcsolat oldalon.</p>'}</div>`);
}
function bindMoonAuth(){
  $('#extraction-refresh').onclick=()=>startTask('/api/moons/extractions/sync');
  $$('[data-moon-auth]').forEach(b=>b.onclick=async()=>{try{b.disabled=true;const data=await api('/api/auth/start',{feature:'moons',character_id:Number(b.dataset.moonAuth)});sessionStorage.setItem('eve-muhely-auth-return','moons');window.location.assign(data.url);}catch(e){b.disabled=false;error(e.message);}});
}
function renderMoonCalendar(target,moons){
  const ids=new Set(moons.filter(m=>m.structure==='Athanor').map(m=>m.id)),events=moonData.extractions.events.filter(e=>ids.has(e.moon_record_id));
  const first=new Date(moonCalendarMonth+'-01T00:00:00Z'),start=new Date(first);start.setUTCDate(1-(first.getUTCDay()+6)%7);
  const dayKey=d=>d.toISOString().slice(0,10);
  const cells=Array.from({length:42},(_,i)=>{const day=new Date(start.getTime()+i*86400000),key=dayKey(day),entries=events.filter(e=>e.date.slice(0,10)===key);return `<div class="moon-calendar-day ${day.getUTCMonth()===first.getUTCMonth()?'':'outside'}"><time datetime="${key}">${day.getUTCDate()}</time>${entries.map(e=>`<button class="moon-calendar-event ${e.stale?'stale':''}" data-calendar-event="${esc(e.id)}"><span data-i18n-skip>${esc(e.date.slice(11,16))} · ${esc(e.moon_name)}</span><small>${e.volume==null?'–':fmt(e.volume)} m³</small></button>`).join('')}</div>`;}).join('');
  target.innerHTML=moonAuthPanel()+`<div class="banner">A naptár UTC időt mutat. Az ESI natural_decay_time az automatikus széttörés időpontja. Az ércek eltűnését a széttörés és a holdnál megadott élettartam alapján becsüljük; a korábbi kézi széttörés és a rig módosíthatja.</div><div class="moon-toolbar"><button id="moon-prev-month" class="button compact" aria-label="Előző hónap">←</button><label>Hónap<input id="moon-calendar-month" type="month" value="${moonCalendarMonth}"></label><button id="moon-next-month" class="button compact" aria-label="Következő hónap">→</button></div><div class="moon-calendar" aria-label="Kitermelési naptár">${Array.from({length:7},(_,i)=>`<div class="moon-calendar-weekday" data-i18n-skip>${new Intl.DateTimeFormat(EveI18n.locale,{weekday:'short',timeZone:'UTC'}).format(new Date(Date.UTC(2026,0,5+i)))}</div>`).join('')}${cells}</div><div id="extraction-details"></div>`;
  target.innerHTML+=panel('Kitermelések és várható ércek','Az ércarányok forrása minden sorban látható',events.length?moonTable(['Hold','Érkezés · UTC','Automatikus széttörés · UTC','Érctérfogat (m³)','Összetétel forrása','Ércek eltűnése · becsült tartomány'],events.map(e=>`<tr><td><button class="text-button" data-calendar-event="${esc(e.id)}">${verbatim(e.moon_name)}</button></td><td data-sort-value="${Date.parse(e.date)}">${moonTime(e.date)}</td><td>${moonTime(e.natural_decay_time)}</td><td class="num">${e.volume==null?'–':fmt(e.volume)}</td><td>${e.composition_source==='esi_calendar'?'ESI naptár · automatikus':e.composition_source==='manual'?'Kézi arány × ESI időtartam':'Nincs ércadat'}${e.kind.includes('history')?' · Korábbi esemény':''}${e.stale?' · Régi adat':''}</td><td>${moonTime(e.belt_earliest_expiry)} — ${moonTime(e.belt_latest_expiry)}</td></tr>`),'extraction-events'):empty('Nincs hozzáférhető kitermelési esemény'));
  bindMoonAuth();
  const change=amount=>{const date=new Date(moonCalendarMonth+'-01T00:00:00Z');date.setUTCMonth(date.getUTCMonth()+amount);moonCalendarMonth=date.toISOString().slice(0,7);renderMoonBody();};
  $('#moon-prev-month').onclick=()=>change(-1);$('#moon-next-month').onclick=()=>change(1);
  $('#moon-calendar-month').onchange=e=>{if(/^\d{4}-\d{2}$/.test(e.target.value)){moonCalendarMonth=e.target.value;renderMoonBody();}};
  $$('[data-calendar-event]').forEach(b=>b.onclick=()=>showExtraction(events.find(e=>e.id===b.dataset.calendarEvent)));
}
function showExtraction(event){
  if(!event)return;
  $('#extraction-details').innerHTML=panel(event.moon_name,moonTime(event.date),`<div class="panel-body"><p>${event.volume_source==='esi_calendar'?'ESI naptárból kiolvasott érctérfogatok.':event.volume_source==='duration_estimate'?'Becslés az ESI kitermelési időtartamából, kézi ércarányokkal.':'A naptárbejegyzés nem ad ércmennyiséget.'}</p>${event.stale?'<p class="warning-text">Régi adat · frissítés szükséges.</p>':''}${event.ores.length?moonTable(['Érc','Arány','Érctérfogat (m³)'],event.ores.map(o=>`<tr><td>${itemName(o.name)}</td><td>${moonPercent(o.percent)}</td><td class="num">${fmt(o.volume)}</td></tr>`),'extraction-detail'):''}<button id="crystals-for-event" class="button compact">Kristályterv ehhez a kitermeléshez</button></div>`);
  $('#crystals-for-event').onclick=()=>{crystalMoonId=event.moon_record_id;crystalEventId=event.id;moonTab='crystals';render();};
  $('#extraction-details').scrollIntoView?.({block:'nearest'});
}
function renderCrystalPlanner(target,moons){
  const d=moonData,p=d.settings;
  if(!moons.some(m=>m.id===crystalMoonId)){crystalMoonId=moons.find(m=>m.structure==='Athanor')?.id||moons[0]?.id||'';crystalEventId='';}
  const events=d.extractions.events.filter(e=>e.moon_record_id===crystalMoonId);
  if(crystalEventId&&!events.some(e=>e.id===crystalEventId))crystalEventId='';
  target.innerHTML=`<div class="banner">A kristálydarabszám a felhozott ércek térfogatarányának legkisebb egész számaránya. Például 75% és 25% esetén 3 és 1 darab. Az azonos kristályt használó érceket összevonjuk; kopást nem számolunk.</div><div class="moon-toolbar"><label>Hold<select id="crystal-moon">${moons.map(m=>`<option data-i18n-skip value="${esc(m.id)}">${esc(m.name)} · ${m.structure}</option>`).join('')}</select></label><label>Számítási időszak<select id="crystal-event"><option value="">30 napos becslés</option>${events.map(e=>`<option data-i18n-skip value="${esc(e.id)}">${moonTime(e.date)}${e.stale?' · '+EveI18n.t('Régi adat'):''}</option>`).join('')}</select></label></div><form id="crystal-settings" class="panel-body moon-settings"><label>Kristályváltozat<select name="crystal_variant">${d.crystal_variants.map(v=>`<option data-i18n-skip value="${v}" ${p.crystal_variant===v?'selected':''}>${v}</option>`).join('')}</select></label><button class="button primary compact">Kristályszámítás mentése</button></form><div id="crystal-result"></div>`;
  $('#crystal-moon').value=crystalMoonId;$('#crystal-event').value=crystalEventId;
  const change=fn=>e=>{if(dirty.moon_crystals&&!confirmUI('Vannak még nem alkalmazott módosítások. Elhagyod ezt az oldalt?')){e.target.value=e.target.id==='crystal-moon'?crystalMoonId:crystalEventId;return;}dirty={};fn(e);renderMoonBody();};
  $('#crystal-moon').onchange=change(e=>{crystalMoonId=e.target.value;crystalEventId='';});$('#crystal-event').onchange=change(e=>{crystalEventId=e.target.value;});
  const form=$('#crystal-settings');form.oninput=()=>dirty.moon_crystals=true;
  form.onsubmit=async e=>{e.preventDefault();const f=new FormData(form);try{await api('/api/moons/settings',{crystal_variant:f.get('crystal_variant')});dirty={};await refreshMoons();}catch(e){error(e.message);}};
  void loadCrystalPlan();
}
async function loadCrystalPlan(){
  const generation=++crystalGeneration;if(!crystalMoonId)return;
  try{const result=await api('/api/moons/crystals?moon_id='+encodeURIComponent(crystalMoonId)+(crystalEventId?'&event_id='+encodeURIComponent(crystalEventId):''));if(generation!==crystalGeneration||moonTab!=='crystals'||!$('#crystal-result'))return;
    $('#crystal-result').innerHTML=result.automatic?'<div class="banner">A Metenox nem igényel bányászkristályt.</div>':result.unavailable?'<div class="banner warn">Nincs használható érctérfogat; ellenőrizd a hold összetételét és a kitermelési adatot.</div>':panel('Szükséges kristályok a kiválasztott holdhoz','Legkisebb egész arány · kopás nélkül',moonTable(['Kristály','Ércek','Érctérfogat (m³)','Arány','Arányos kristálydarabszám'],result.rows.map(c=>`<tr><td>${itemName(c.name)}</td><td>${c.ores.map(itemName).join(', ')}</td><td class="num">${fmt(c.volume)}</td><td class="num">${moonPercent(c.share)}</td><td class="num"><strong>${fmt(c.count)}</strong></td></tr>`),'selected-crystals'))+'<p class="footnote">Ez arányos készletjavaslat. A töredezett százalékok miatt a legkisebb pontos egész arány nagy darabszámot is adhat.</p>' ;
  }catch(e){if(generation===crystalGeneration&&moonTab==='crystals')error(e.message);}
}
