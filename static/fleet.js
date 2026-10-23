'use strict';
let fleetData=null,fleetRequest=null,fleetTimer=null,fleetError='',fleetCharacter='',fleetDays=30,fleetTab='sessions',fleetSession='',fleetPage=0;
const fleetAt=at=>at?esc(EveI18n.date(new Date(at*1000))):'–';
const fleetUTC=at=>new Date(at*1000).toISOString().replace('T',' ').slice(0,19)+' UTC';
function scheduleFleet(){clearTimeout(fleetTimer);if(view==='fleet')fleetTimer=setTimeout(()=>void loadFleet(true),fleetData?.status.running?1500:10000);}
async function loadFleet(background=false){
  if(fleetRequest)return;
  fleetRequest=api('/api/fleet'+(background?'?background=1':''));
  try{const next=await fleetRequest;const stamp=d=>d?JSON.stringify([d.preferences,d.characters,d.sessions,d.kills,d.status,d.location_status.running,d.location_status.character]):'';const changed=stamp(next)!==stamp(fleetData)||!!fleetError;fleetData=next;fleetError='';if(view==='fleet'&&changed)render();}
  catch(e){fleetError=e.message;if(view==='fleet')error(e.message);}
  finally{fleetRequest=null;scheduleFleet();}
}
async function refreshFleet(sessionId=null){
  try{error('');await api('/api/fleet/refresh',sessionId?{session_id:sessionId}:{character_id:fleetCharacter?Number(fleetCharacter):null});if(fleetRequest)await fleetRequest.catch(()=>{});await loadFleet();}
  catch(e){error(e.message);}
}
function fleetLeaveEdits(){
  if(!dirty.fleet_settings)return true;
  if(!confirmUI('Vannak még nem alkalmazott módosítások. Elhagyod ezt az oldalt?'))return false;
  delete dirty.fleet_settings;return true;
}
function fleetLink(k){
  const label=EveI18n.t('Killmail megnyitása a zKillboardon')+' · '+k.ship+' · #'+k.id;
  const icon=Number.isSafeInteger(k.ship_id)&&k.ship_id>0?`<img src="https://images.evetech.net/types/${k.ship_id}/icon?size=64" alt="${esc(k.ship)}" width="32" height="32" loading="lazy">`:`<span role="img" aria-label="${esc(k.ship)}">◇</span>`;
  return `<a class="fleet-killmail-link" href="https://zkillboard.com/kill/${Number(k.id)}/" target="_blank" rel="noopener noreferrer" title="${esc(label)}" aria-label="${esc(label)}" data-i18n-skip>${icon}</a>`;
}
function fleetRole(r){return esc(EveI18n.t(r==='kill'?'Kill':r==='loss'?'Veszteség':'Környező esemény'));}
function fleetTable(rows,id){
  return table(['Időpont','Rendszer','Esemény','Megsemmisült hajó','Résztvevő támadók','Érték (ISK)','Killmail'],rows.map(k=>`<tr><td data-sort-value="${k.at}" title="${fleetUTC(k.at)}">${fleetAt(k.at)}</td><td data-i18n-skip>${esc(k.system)}</td><td>${k.characters?.length?k.characters.map(c=>`<span data-i18n-skip>${esc(c.name)}</span> · ${fleetRole(c.role)}`).join('<br>'):fleetRole(k.role)}</td><td>${itemName(k.ship)}</td><td class="num">${fmt(k.attackers)}</td><td class="num">${k.value==null?'–':fmt(Math.round(k.value))}</td><td data-sort-value="${k.id}" data-filter-value="${esc(k.ship)} #${k.id}">${fleetLink(k)}</td></tr>`),id);
}
function renderFleet(content){
  setHead('HARCOK ÉS ÚTVONAL','Flottatevékenység','A karakterek nyilvános killjei és veszteségei, ESI-pozíciókkal kiegészített flottamenetek.');
  actions('<button class="button compact" id="fleet-refresh">Killmailek frissítése</button>');$('#fleet-refresh').onclick=()=>void refreshFleet();
  const opened=[...content.querySelectorAll('details')].map((el,i)=>el.open?i:-1).filter(i=>i>=0);
  const d=fleetData;if(!d){content.innerHTML=empty(fleetError||'Flottaadatok betöltése…');if(!fleetRequest)void loadFleet();return;}
  const p=d.preferences,busy=d.status.running;
  $('#fleet-refresh').disabled=busy;
  content.innerHTML=`<section class="panel panel-body fleet-controls"><label>Karakter<select id="fleet-character"><option value="">Minden karakter</option>${d.characters.map(c=>`<option value="${c.id}" data-i18n-skip>${esc(c.name)}</option>`).join('')}</select></label><label>Időszak<select id="fleet-days">${[7,30,90].map(n=>`<option value="${n}">${n} ${EveI18n.t('nap')}</option>`).join('')}</select></label><div class="footnote"><span>ESI-helykövetés:</span> <strong>${EveI18n.t(p.tracking?'Bekapcsolva':'Kikapcsolva')}</strong> · ${fmt(p.interval_seconds)} s${d.location_status.running?' · '+EveI18n.t('Lekérés folyamatban')+' '+esc(d.location_status.character):''}</div></section>`;
  const task=d.status;
  if(busy){const total=Number(task.total)||0,done=Number(task.completed)||0;content.innerHTML+=`<div class="banner" role="status" aria-live="polite"><strong>${EveI18n.t(task.kind==='report'?'Kapcsolódó killmailek betöltése…':'Killmailek betöltése…')}</strong><span data-i18n-skip> ${esc(task.subject||'')}</span> · ${done}/${total||'…'}${task.page?' · '+EveI18n.t('Oldal')+' '+task.page:''}<progress ${total?`value="${done}" max="${total}"`:''}></progress></div>`;}
  if(task.error)content.innerHTML+=`<div class="banner error" role="alert">${esc(EveI18n.t(task.error))}</div>`;
  if(task.results.some(r=>!r.ok||r.partial))content.innerHTML+='<div class="banner warn">A lekérés részleges. Ellenőrizd az adatforrásokat; a hiányzó események nem számítanak nulla aktivitásnak.</div>';
  const cutoff=Date.now()/1000-fleetDays*86400;
  const sessions=d.sessions.filter(s=>s.last>=cutoff&&(!fleetCharacter||String(s.character_id)===fleetCharacter));
  const kills=d.kills.filter(k=>k.at>=cutoff&&(!fleetCharacter||k.characters.some(c=>String(c.id)===fleetCharacter)));
  content.innerHTML+=`<div class="shopping-tabs"><button data-fleet-tab="sessions" aria-pressed="${fleetTab==='sessions'}">Flottamenetek</button><button data-fleet-tab="kills" aria-pressed="${fleetTab==='kills'}">Killmailek</button></div>`;
  if(fleetTab==='kills'){
    content.innerHTML+=panel('Killmailek',`${fmt(kills.length)}`,kills.length?fleetTable(kills.slice(fleetPage*100,(fleetPage+1)*100),'fleet-kills'):empty('Még nincs betöltött killmail','Indítsd el a killmailek frissítését.'));
    if(kills.length>100)content.innerHTML+=`<div class="fleet-pager"><button class="button compact" id="fleet-prev" ${fleetPage?'':'disabled'}>←</button> ${fleetPage+1}/${Math.ceil(kills.length/100)} <button class="button compact" id="fleet-next" ${(fleetPage+1)*100<kills.length?'':'disabled'}>→</button></div>`;
  }else{
    const selected=sessions.find(s=>s.id===fleetSession);
    content.innerHTML+=panel('Flottamenetek',fmt(sessions.length),sessions.length?table(['Karakter','Első kill','Utolsó kill','Rendszerek','Kill / veszteség','ESI-minták','Riport'],sessions.map(s=>`<tr><td data-i18n-skip>${esc(s.character_name)}</td><td data-sort-value="${s.first}">${fleetAt(s.first)}</td><td data-sort-value="${s.last}">${fleetAt(s.last)}</td><td data-i18n-skip>${esc([...new Set(s.visits.map(v=>v.name))].join(', '))}</td><td class="num">${s.kills} / ${s.losses}</td><td class="num">${s.esi_samples}</td><td><button class="button compact" data-fleet-session="${esc(s.id)}" aria-pressed="${selected?.id===s.id}">Megnyitás</button></td></tr>`),'fleet-sessions'):empty('Még nincs flottamenet','Indítsd el a killmailek frissítését.'));
    if(selected)content.innerHTML+=renderFleetSession(selected,busy);
  }
  content.innerHTML+=`<details class="panel panel-body"><summary>Követés és csoportosítás beállításai</summary><form id="fleet-settings"><div class="fleet-controls"><label><input type="checkbox" name="tracking" ${p.tracking?'checked':''}> ESI-helykövetés bekapcsolva</label><label>Helylekérés időköze (másodperc)<input name="interval_seconds" type="number" min="30" max="900" value="${p.interval_seconds}" required></label><label>Flottamenetek elválasztása (perc)<input name="gap_minutes" type="number" min="15" max="180" value="${p.gap_minutes}" required></label><label>Kill előtti és utáni ablak (perc)<input name="padding_minutes" type="number" min="15" max="60" value="${p.padding_minutes}" required></label></div><div class="skill-character-options">${d.characters.map(c=>`<label data-i18n-skip><input type="checkbox" name="character_ids" value="${c.id}" ${c.selected?'checked':''}> ${esc(c.name)}</label>`).join('')}</div><button class="button compact" type="submit">Beállítások mentése</button></form><p class="footnote">Csak a kijelölt karakterek helyadatait és killjeit kérjük le. A korábbi helyi előzmény megmarad. Az ESI-pozíció utolsó ismert helyzet, nem bizonyítja az online állapotot. Az útvonal követése csak futó alkalmazásnál működik.</p></details>`;
  content.innerHTML+=`<details class="panel panel-body"><summary>Adatforrás és lefedettség</summary><p>Az első letöltés az utolsó 30 napot keresi, karakterenként legfeljebb 1000 killmailből. A letöltött történet helyben megmarad; a nézet az utolsó 90 napot mutatja. A zKillboard nem tartalmaz minden harcot, és nem ad biztos flottaazonosítót. A flottamenet időbeli csoportosítás, a köztes ugrások útvonala ismeretlen.</p><p>A zKillboard-lekérések egy órán át gyorsítótárazottak; a kézi frissítés ezt sem kerüli meg. A kapcsolódó riport csak a kijelölt rendszerek időablakaiban látható publikus killmaileket tartalmazza; idegen harcok is beleeshetnek.</p>${table(['Karakter','Killmailek ellenőrizve','Következő killmail-lekérés','Lefedettség','ESI-helyzet ideje','Rendszer','Helyhozzáférés'],d.characters.map(c=>`<tr><td data-i18n-skip>${esc(c.name)}</td><td>${fleetAt(c.checked)}</td><td>${fleetAt(c.next_check)}</td><td>${esc(EveI18n.t(c.error||(!c.checked?'Még nincs adat':c.complete?'30 nap lekérdezve':'Részleges adatok')))}</td><td>${fleetAt(c.location_checked)}</td><td data-i18n-skip>${esc(c.system||'–')}</td><td>${esc(EveI18n.t(c.location_error||(!c.location_access?'Engedélyezés szükséges':c.selected?'Olvasási engedély megadva':'Nincs követve')))}</td></tr>`),'fleet-access')}<button class="button compact" data-open-settings="access">Adathozzáférések megnyitása</button><p><a href="https://zkillboard.com/api/docs/" target="_blank" rel="noopener noreferrer">zKillboard API</a> · <a href="https://br.evetools.org/recent-brs" target="_blank" rel="noopener noreferrer">Battle Report Tool</a></p></details>`;
  $('#fleet-character').value=fleetCharacter;$('#fleet-days').value=String(fleetDays);
  $('#fleet-character').onchange=e=>{if(!fleetLeaveEdits()){e.target.value=fleetCharacter;return;}fleetCharacter=e.target.value;fleetSession='';fleetPage=0;render();};$('#fleet-days').onchange=e=>{if(!fleetLeaveEdits()){e.target.value=String(fleetDays);return;}fleetDays=Number(e.target.value);fleetSession='';fleetPage=0;render();};
  $$('[data-fleet-tab]').forEach(b=>b.onclick=()=>{if(!fleetLeaveEdits())return;fleetTab=b.dataset.fleetTab;render();});
  $$('[data-fleet-session]').forEach(b=>b.onclick=()=>{if(!fleetLeaveEdits())return;fleetSession=b.dataset.fleetSession;render();$('#fleet-session')?.scrollIntoView?.({block:'nearest'});});
  if($('#fleet-context'))$('#fleet-context').onclick=()=>void refreshFleet(fleetSession);
  if($('#fleet-windows'))$('#fleet-windows').onclick=()=>{const s=sessions.find(s=>s.id===fleetSession);csv(s.windows.map(w=>[w.name,fleetUTC(w.start),fleetUTC(w.end),w.kill_ids.length,w.esi_samples]),['Rendszer','Kezdés (UTC)','Vége (UTC)','Killmailek','ESI-minták'],'fleet-windows');};
  if($('#fleet-prev'))$('#fleet-prev').onclick=()=>{fleetPage--;render();};if($('#fleet-next'))$('#fleet-next').onclick=()=>{fleetPage++;render();};
  $('#fleet-settings').oninput=()=>{dirty.fleet_settings=true;};
  $('#fleet-settings').onchange=()=>{dirty.fleet_settings=true;};
  $('#fleet-settings').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.currentTarget);try{await api('/api/fleet/preferences',{tracking:f.has('tracking'),interval_seconds:Number(f.get('interval_seconds')),gap_minutes:Number(f.get('gap_minutes')),padding_minutes:Number(f.get('padding_minutes')),character_ids:f.getAll('character_ids').map(Number)});delete dirty.fleet_settings;fleetSession='';await loadFleet();toast('Flottakövetés beállításai mentve.');}catch(error_){error(error_.message);}};
  opened.forEach(i=>{const el=content.querySelectorAll('details')[i];if(el)el.open=true;});
  scheduleFleet();
}
function fleetValueSummary(s,coverageIncomplete){
  const summary=s.value_summary;if(!summary)return '';
  const money=(b,field='cents',missing='missing')=>b[missing]===b.count&&b.count>0?'–':(b[missing]?'≥ ':'')+EveCosts.format(BigInt(b[field]));
  const card=(key,label)=>{const b=summary[key];return `<div class="metric" data-fleet-value="${key}"><div class="metric-label">${EveI18n.t(label)}</div><strong>${money(b)}</strong><small>${fmt(b.count)} <span>killmail</span>${key==='participation'&&summary.participation_percent!==null?' · '+esc(summary.participation_percent)+'%':''}</small><div class="footnote"><span>Ténylegesen megsemmisült:</span> ${money(b,'destroyed_cents','destroyed_missing')}</div></div>`;};
  const unknown=Object.values(summary).some(b=>b&&typeof b==='object'&&(b.missing||b.destroyed_missing));
  return `<div class="metrics fleet-value-summary">${card('total','A session teljes veszteségértéke')}${card('participation','A karakter részvételével elért killek')}${card('losses','A karakter saját vesztesége')}</div>${coverageIncomplete?'<p class="footnote warn">A session értéke még részösszeg: a kapcsolódó riport hiányzik, részleges vagy frissítésre vár.</p>':''}${unknown?'<p class="footnote warn">Néhány killmail értékadata hiányzik; az ismert értékek részösszege látszik. A hiányzó megsemmisült értéket nem helyettesítjük a loot-tal együtt számolt értékkel.</p>':''}<p class="footnote">A fő összegek a zKillboard becsült teljes killmailértékei, a kihullott loot-tal együtt. A megsemmisült sor csak a destroyedValue értéket mutatja. Részvételnél minden olyan kill teljes értéke egyszer számít, amelyen a karakter támadóként szerepel; nem sebzésarányos részesedés.</p>`;
}
function renderFleetSession(s,busy){
  const p=fleetData.preferences,source=s.report,changed=source&&JSON.stringify(source.data.windows)!==JSON.stringify(s.windows);
  const partial=source?.data.results.some(r=>!r.ok||r.partial);
  const route=s.visits.map((v,i)=>`<li><span class="badge">${i+1}</span><strong data-i18n-skip>${esc(v.name)}</strong><span>${fleetAt(v.first)}${v.last!==v.first?' – '+fleetAt(v.last):''}</span><small>${v.kill_ids.length} kill · ${v.esi_samples} ESI</small></li>`).join('');
  return `<section id="fleet-session" class="panel"><div class="panel-head"><h2><span data-i18n-skip>${esc(s.character_name)}</span> · <span>Flottamenet</span></h2><div><button class="button compact" id="fleet-context" ${busy?'disabled':''}>Kapcsolódó killmailek betöltése</button> <button class="button compact" id="fleet-windows">Időablakok CSV</button></div></div><div class="panel-body">${fleetValueSummary(s,!source||changed||partial)}<p><span>Riport időablaka:</span> ${fleetAt(s.start)} – ${fleetAt(s.end)}</p><ol class="fleet-route" aria-label="Megfigyelt rendszerlátogatások">${route}</ol><p class="footnote">A sorrend killmailekből és ESI-mintákból áll össze; a rendszerek közti tényleges út és a flottatagság nem bizonyított. Egy ESI-minta nem bizonyítja a teljes időablakban való jelenlétet.</p>${table(['Rendszer','Kezdés','Vége','Killmailek','ESI-minták'],s.windows.map(w=>`<tr><td data-i18n-skip>${esc(w.name)}</td><td title="${fleetUTC(w.start)}">${fleetAt(w.start)}</td><td title="${fleetUTC(w.end)}">${fleetAt(w.end)}</td><td class="num">${w.kill_ids.length}</td><td class="num">${w.esi_samples}</td></tr>`),'fleet-windows')}<p class="footnote"><span>A kill helyszínei legalább ennyi perc ráhagyást kapnak előtte és utána:</span> ${p.padding_minutes}. <span>A képernyőn helyi idő látszik, az export UTC.</span></p>${!source?'<div class="banner">A teljes környező harcanyag még nincs betöltve. Jelenleg a már ismert események látszanak.</div>':changed?'<div class="banner warn">Az időablak megváltozott; töltsd be újra a kapcsolódó killmaileket.</div>':partial?'<div class="banner warn">A kapcsolódó riport részleges; a lekérdezési keret vagy egy adatforrás korlátozta a letöltést.</div>':'<p class="footnote"><span>Kapcsolódó riport ellenőrizve:</span> '+fleetAt(source.checked)+'</p>'}${fleetTable(s.rows,'fleet-report-kills')}</div></section>`;
}
