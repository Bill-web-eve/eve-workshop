'use strict';
const intelParams=new URLSearchParams(location.search),intelWindowMode=['map','chat'].includes(intelParams.get('intel_window'))?intelParams.get('intel_window'):null;
if(intelWindowMode)document.documentElement.dataset.intelWindow=intelWindowMode;
let intelFingerprint=null,intelData=null,intelRequest=null,intelEnabled=null,intelAlertBusy=false,intelTick=null,intelCharacter=Number(intelParams.get('character_id'))||null,intelCenter=Number(intelParams.get('center'))||null,intelRegion=Number(intelParams.get('region'))||null,intelHistory=intelParams.get('history')==='1',intelSelected=null,intelZoom=1,intelPan={x:0,y:0},intelMapDragging=false,intelDiscovered=[],intelChatAuto=true,intelViewportHeight=720,intelResizeObserver=null;
const intelDate=at=>at?date(at):'–';
const intelLabels={contact:'Bejelentett aktivitás',clear:'Clear · tiszta',query:'Kérdés',unparsed:'Nem értelmezett',old:'Lejárt intel',quiet:'Nincs friss bejelentés'};
const intelAge=at=>at==null?'–':EveI18n.t('{0} perce').replace('{0}',fmt(Math.max(0,Math.floor((Date.now()/1000-at)/60))));
const intelSource=p=>p.source==='manual'?'Kézi referencia':p.source==='esi'?p.online===false?'ESI · offline':p.alertable?'ESI · élő helyzet':'ESI · korábbi adat':p.source==='local'?'Local napló · utolsó ismert hely':'Nincs helyzetadat';
const intelPilotUrl=p=>Number.isSafeInteger(p.id)&&p.id>0?'https://zkillboard.com/character/'+p.id+'/':null;
const intelCardLifetime=180000;
let intelCardTimer=null,intelNotificationRevision=0;
function intelPilotName(p){const url=intelPilotUrl(p);return url?`<a class="intel-pilot-link" data-intel-pilot href="${url}" target="_blank" rel="noopener noreferrer" data-i18n-skip>${esc(p.name)}</a>`:`<span class="intel-pilot-unresolved" data-i18n-skip>${esc(p.name)}</span><span class="intel-id-note"> · <span>Azonosító még nem ismert</span></span>`;}
function intelShips(ships=[]){return ships.length?ships.map(s=>`<span class="intel-ship">${Number.isSafeInteger(s.type_id)&&s.type_id>0?`<img src="https://images.evetech.net/types/${s.type_id}/icon?size=32" alt="" data-intel-image loading="lazy" referrerpolicy="no-referrer">`:'<span class="intel-ship-placeholder" aria-hidden="true">◇</span>'}${verbatim(s.name)}</span>`).join(''):'<span class="muted">Nincs megadott hajó</span>';}
async function refreshIntel(background=false){
  if(intelRequest)return intelRequest;
  intelRequest=(async()=>{try{
    intelData=await api('/api/intel?'+new URLSearchParams({...(intelCenter?{center:intelCenter}:{}),...(intelCharacter?{character_id:intelCharacter}:{}),...(intelRegion?{region:intelRegion}:{}),...(intelHistory?{history:'1'}:{}),...(background?{background:'1'}:{})}));intelEnabled=intelData.preferences.enabled;
    if(!intelData.characters.some(c=>c.id===intelCharacter)&&intelData.characters.length)intelCharacter=intelData.reference?.id||intelData.characters[0].id;
    const fingerprint=JSON.stringify([intelData.preferences,intelData.characters,intelData.nodes,intelData.reports,intelData.edges,intelData.kill_regions,intelData.kill_feed?.enabled,intelData.kill_feed?.error,!!intelData.kill_feed?.checked,intelData.status.error,intelData.status.file_errors,intelData.status.files,intelData.status.resolving_characters,intelData.status.names_error,Math.floor(Date.now()/60000)]);
    if(intelWindowMode==='chat'){
      if(!$('#intel-chat-feed'))render();else updateIntelChat();
    }else if((view==='intel'&&!intelMapDragging)||(view==='settings'&&settingsTab==='intel')){
      // A live update must not dismiss a native region/character dropdown.
      if(background&&document.activeElement?.matches('.intel-toolbar select')){updateIntelStatus();return;}
      if(!background||fingerprint!==intelFingerprint){render();intelFingerprint=fingerprint;}
      else updateIntelStatus();
    }
  }catch(e){if(view==='intel'||view==='settings'&&settingsTab==='intel')error(e.message);}finally{intelRequest=null;}})();return intelRequest;
}
function updateIntelStatus(){if($('#intel-watcher-time'))$('#intel-watcher-time').textContent=intelDate(intelData.status.checked);}
async function pollIntelAlerts(){
  if(intelWindowMode){if(state&&!intelMapDragging)await refreshIntel(true);return;}
  if(!state||intelAlertBusy)return;intelAlertBusy=true;
  try{
    const revision=intelNotificationRevision,data=await api('/api/intel/alerts');
    if(revision!==intelNotificationRevision)return;
    intelEnabled=data.enabled;
    if(EveDesktop.active)await syncIntelOverlay(data);
    const badge=$('#intel-count');if(badge){badge.textContent=fmt(data.items.length);badge.hidden=!data.items.length;}
    if(data.enabled&&data.notifications_enabled!==false&&EveDesktop.active&&notificationData?.preferences.os_enabled&&notificationData.preferences.categories.intel!==false){const status=await EveDesktop.notificationStatus();if(status.status==='authorized')await deliverNotifications('/api/intel/claim');}
    if(view==='intel'&&!intelMapDragging&&!Object.keys(dirty).length)await refreshIntel(true);
  }catch(e){if(view==='intel')error(e.message);}finally{intelAlertBusy=false;}
}
async function syncIntelOverlay(data){
  if(EveDesktop.platform==='windows')return;
  const prefs=data.overlay||{},items=[],enabled=!!(data.enabled&&prefs.enabled&&data.notifications_enabled!==false&&notificationData?.preferences?.categories?.intel!==false);
  if(enabled)for(const alert of data.items||[])for(const report of alert.overlay_reports||[]){items.push({key:alert.system_id+':'+report.id,system:alert.system_name,pilots:(report.kind==='kill'?fmt(report.kill_count)+' kill':((report.pilots||[]).join(', ')||EveI18n.t('Nem megnevezett pilóta'))).slice(0,1900),ships:(report.ships||[]).join(', ').slice(0,1900),character:alert.kind==='intel_kill'?alert.region_name||'':alert.character_name,jumps:alert.jumps??null,when:report.when});}
  await EveDesktop.syncIntelOverlay({enabled,seconds:prefs.seconds||60,items:items.slice(0,3000)});
}
async function applyIntelNotificationPreferences(preferences){
  // Invalidate an alert fetch begun before this explicit preference change.
  intelNotificationRevision++;
  if(notificationData)notificationData.preferences=preferences;
  const enabled=preferences.categories.intel!==false;
  if(intelData)intelData.notifications_enabled=enabled;
  if(!enabled&&EveDesktop.active)await syncIntelOverlay({enabled:false,notifications_enabled:false,items:[]});
}
function startIntelMonitor(){clearInterval(intelTick);intelTick=setInterval(()=>{if(!document.hidden)void pollIntelAlerts();},2000);void pollIntelAlerts();}
function resetIntelMap(){intelZoom=1;intelPan={x:0,y:0};}
function showIntelSystem(id){intelCenter=Number(id);intelRegion=null;intelSelected=Number(id);resetIntelMap();if(intelWindowMode==='chat'){void openIntelWindow('map',{center:intelCenter});return;}if(view!=='intel')navigate('intel');void refreshIntel();}
async function openIntelWindow(kind,overrides={}){
  try{await EveDesktop.openIntelWindow(kind,{character_id:intelCharacter||0,region:intelRegion||0,center:intelCenter||0,history:intelHistory,...overrides});}catch(e){error(e.message);}
}
async function applyIntelWindowOptions(options){
  for(const key of ['character_id','region','center'])if(options[key]!==undefined){const value=Number(options[key]);if(!Number.isSafeInteger(value)||value<0)return;}
  if(options.character_id!==undefined)intelCharacter=Number(options.character_id)||null;if(options.region!==undefined)intelRegion=Number(options.region)||null;if(options.center!==undefined){intelCenter=Number(options.center)||null;intelSelected=intelCenter;}if(options.history!==undefined)intelHistory=options.history===true;resetIntelMap();await refreshIntel();
}
function intelStatusBanner(){const d=intelData,p=d.preferences,s=d.status;return `<div class="banner ${s.error?'error':''}"><strong>${p.enabled?'Chatlogfigyelés bekapcsolva':'Chatlogfigyelés kikapcsolva'}</strong><span> · ${fmt(s.done||0)} / ${fmt(s.files||0)} <span>napló</span> · <span>Utolsó ellenőrzés:</span> <span id="intel-watcher-time">${intelDate(s.checked)}</span></span>${s.error?'<div>'+esc(s.error)+'</div>':''}${s.file_errors?'<p>Legalább egy naplófájl nem olvasható; ellenőrizd a mappa és a fájlok hozzáférését.</p>':''}<div data-i18n-skip>${esc(p.channels.join(' · '))}</div></div>`;}
function intelKillMoney(row){return row.missing===row.count&&row.count?'–':(row.missing?'≥ ':'')+EveCosts.format(BigInt(row.cents||0));}
function intelKillSummary(groups){
  const kills=[...new Map(groups.flatMap(g=>g.kills).map(k=>[k.id,k])).values()],types=new Map();let cents=0n,missing=0;
  for(const k of kills){const key=k.ship_id||k.ship;if(!types.has(key))types.set(key,{name:k.ship,type_id:k.ship_id,count:0});types.get(key).count++;if(k.cents===null)missing++;else cents+=BigInt(k.cents);}
  return {count:kills.length,cents,missing,ships:[...types.values()].sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name)),last_at:Math.max(...kills.map(k=>k.at))};
}
function intelKillShips(ships){return intelShips(ships.map(s=>({...s,name:s.count+' × '+s.name})));}
function intelKillTable(groups){
  return table(['Időpont','Rendszer','Elvesztett hajók','Darabszám','Érték (ISK)','Killmailek'],groups.map(g=>`<tr><td data-sort-value="${g.last_at}">${intelDate(g.last_at)}</td><td><button class="text-button" data-intel-locate="${g.system_id}">${verbatim(g.system_name)}</button></td><td>${intelKillShips(g.ships)}</td><td class="num">${fmt(g.count)}</td><td class="num" data-sort-value="${g.missing===g.count?'':g.cents}">${intelKillMoney(g)}</td><td class="intel-kill-links">${g.kills.map(k=>fleetLink(k)).join('')}</td></tr>`),'intel-kills');
}
function intelKillStatus(d){
  if(!d.kill_feed)return '';
  const enabled=d.preferences.killfeed_enabled&&d.kill_feed.enabled,names=d.regions.filter(([id])=>d.kill_regions?.includes(id)).map(([,name])=>name);
  return `<div class="banner"><strong>zKillboard · R2Z2</strong> · <span>${EveI18n.t(!enabled?'Kikapcsolva':d.kill_feed.error?'Újracsatlakozásra vár':d.kill_feed.checked?'Élő kapcsolat aktív':'Kapcsolódás…')}</span><div><span>Killértesítések régiója:</span> ${names.length?names.map(verbatim).join(', '):EveI18n.t('Nincs ismert régió')}</div><small>Régión belüli killjelzés; nem igazol jelenlegi ellenséges jelenlétet.</small></div>`;
}
function renderIntel(content){
  if(intelWindowMode==='chat')return renderIntelChat(content);
  setHead('HELYI INTEL','Inteltérkép','Teljes régiótérkép, jelölt jumptávolság és jelentett pilóták hajóadatokkal.');$('#plan-status').hidden=true;
  actions(intelWindowMode==='map'?'':`<button class="button compact" id="intel-refresh">Állapot frissítése</button><button class="button compact" data-intel-window="map">Térkép külön ablakban</button><button class="button compact" data-intel-window="chat">Intelchat külön ablakban</button><button class="button compact" data-open-settings="intel">Intelbeállítások</button><button class="button compact" id="intel-notifications" aria-pressed="${intelData?.notifications_enabled!==false}">${intelData?.notifications_enabled===false?'Intelértesítések: kikapcsolva':'Intelértesítések: bekapcsolva'}</button>`);
  if($('#intel-notifications'))$('#intel-notifications').onclick=async()=>{const button=$('#intel-notifications');button.disabled=true;try{const preferences=await api('/api/notifications/preferences',{categories:{intel:intelData?.notifications_enabled===false}});await applyIntelNotificationPreferences(preferences);await refreshNotifications(false);await refreshIntel();toast('Intelértesítések beállítása mentve.');}catch(e){error(e.message);button.disabled=false;}};
  if($('#intel-refresh'))$('#intel-refresh').onclick=()=>void refreshIntel();bindIntelLinks();
  if(!intelData){content.innerHTML=empty('Inteladatok betöltése');void refreshIntel();return;}
  const d=intelData,p=d.preferences,current=d.reference||d.characters.find(c=>c.id===intelCharacter);
  if(intelWindowMode==='map'){actions();content.innerHTML=intelMapPanel(d,current,true);bindIntelMapControls();return;}
  content.innerHTML=intelStatusBanner();
  content.innerHTML+=intelKillStatus(d);
  if(!p.enabled)content.innerHTML+=intelWindowMode?empty('Chatlogfigyelés kikapcsolva'):settingsShortcut('Az intel használatához válassz mappát és csatornákat, majd kapcsold be a figyelést.','intel');
  if(current&&!current.alertable)content.innerHTML+=`<div class="banner"><span>A körzet az utolsó ismert helyet mutatja; ebből nem indul élő közelségi riasztás.</span>${intelWindowMode?'':' <button class="text-button" data-open-settings="intel">Beállítások megnyitása</button>'}</div>`;
  if(d.alerts.length)content.innerHTML+=`<div class="banner intel-danger" role="alert"><strong>Inteljelzések</strong>${d.alerts.map(a=>`<div>${a.kind==='intel_kill'?fmt(a.kill_count)+' kill · ':verbatim(a.character_name)+' · '+esc(fmt(a.jumps))+' jump · '}<button class="text-button" data-intel-locate="${a.system_id}">${verbatim(a.subject)}</button></div>`).join('')}</div>`;
  content.innerHTML+=`<div class="panel panel-body intel-toolbar"><label>Karakter<select id="intel-character">${d.characters.map(c=>`<option data-i18n-skip value="${c.id}">${esc(c.name)}</option>`).join('')}</select></label><label>Régió<select id="intel-region"><option value="">A kiválasztott hely régiója</option>${d.regions.map(([id,name])=>`<option data-i18n-skip value="${id}">${esc(name)}</option>`).join('')}</select></label><label class="intel-history"><input type="checkbox" id="intel-history" ${intelHistory?'checked':''}> Korábbi intel a térképen</label><button class="button compact" id="intel-follow">Karakter követése</button><span class="intel-region-summary">${verbatim(d.region_name||'–')} · ${fmt(d.nodes.length)} <span>rendszer</span> · <strong>≤ ${p.jumps} jump</strong></span></div>`;
  if(current)content.innerHTML+=`<p class="footnote">${verbatim(current.name)} · <span>${esc(intelSource(current))}</span> · ${verbatim(current.system_name||'–')} · ${intelDate(current.as_of)} · <span>Riasztási távolság:</span> ${p.jumps} jump</p>`;
  content.innerHTML+=intelMapPanel(d,current);
  if(!intelWindowMode){
    const selected=intelSelected||d.center;const reports=d.reports.filter(r=>r.systems.includes(selected));
    content.innerHTML+=panel('Kijelölt rendszer','',reports.length?intelReportTable(reports,'intel-selected'):empty('Nincs bejelentés a kijelölt rendszerhez'));
    if(d.kill_groups?.length)content.innerHTML+=panel('Killek a régióban',EveI18n.t('Rövid időn belül érkezett killmailek rendszerenként összevonva.'),intelKillTable(d.kill_groups));
    content.innerHTML+=panel('Intelüzenetek','Legfeljebb 24 óra · a bejelentő nem a jelentett pilóta',d.reports.length?intelReportTable(d.reports,'intel-feed'):empty('Még nincs feldolgozott intelüzenet','Az új üzenetek a kiválasztott csatornák naplóiból jelennek meg.'));
  }
  $('#intel-character').value=String(intelCharacter||'');$('#intel-character').onchange=e=>{intelCharacter=Number(e.target.value);intelCenter=null;intelRegion=null;resetIntelMap();void refreshIntel();};
  $('#intel-region').value=intelRegion||'';$('#intel-region').onchange=e=>{intelRegion=Number(e.target.value)||null;resetIntelMap();void refreshIntel();};
  $('#intel-history').onchange=e=>{intelHistory=e.target.checked;void refreshIntel();};$('#intel-follow').onclick=()=>{intelCenter=null;intelRegion=null;resetIntelMap();void refreshIntel();};
  bindIntelMapControls();
}
function intelMapPanel(d,current,mapOnly=false){
  const p=d.preferences;
  return panel('Rendszertérkép',[d.region_name,mapOnly?current?.name:null].filter(Boolean).join(' · '),`<div class="intel-map-controls"><button class="button compact" id="intel-zoom-in" aria-label="Nagyítás">＋</button><button class="button compact" id="intel-zoom-out" aria-label="Kicsinyítés">−</button><button class="button compact" id="intel-fit">Teljes nézet</button>${mapOnly?'':`<button class="text-button" id="intel-resolve">Pilótaazonosítók frissítése</button><span id="intel-resolve-status">${d.status.resolving_characters?'Pilótaazonosítók ellenőrzése…':d.status.names_error||'Húzás: mozgatás · görgetés: nagyítás'}</span>`}</div><div id="intel-map" class="intel-map ${current?.alertable?'':'intel-range-stale'}"></div><div class="panel-body intel-legend"><span class="intel-dot contact"></span> Bejelentett aktivitás <span class="intel-dot kill"></span> Killaktivitás <span class="intel-dot clear"></span> Clear · tiszta <span class="intel-dot old"></span> Lejárt intel <span class="intel-dot own"></span> Saját karakter <span class="intel-range-key"></span><span>Jelölt körzet:</span> ≤ ${p.jumps} jump${mapOnly&&current&&!current.alertable?`<span class="intel-map-provenance">A körzet az utolsó ismert helyet mutatja; ebből nem indul élő közelségi riasztás.</span>`:''}</div>${mapOnly?'':`<p class="footnote panel-body">A jelölés kaputávolságot mutat, nem geometriai kört. A teljes régió látható; a távolság a teljes kapuhálózaton számolódik.</p>`}`);
}
function bindIntelMapControls(){
  $('#intel-fit').onclick=()=>{resetIntelMap();applyIntelTransform();};$('#intel-zoom-in').onclick=()=>{intelZoom=Math.min(5,intelZoom*1.25);applyIntelTransform();};$('#intel-zoom-out').onclick=()=>{intelZoom=Math.max(.25,intelZoom/1.25);applyIntelTransform();};
  if($('#intel-resolve'))$('#intel-resolve').onclick=async()=>{try{await api('/api/intel/characters',{});await refreshIntel();}catch(e){error(e.message);}};
  drawIntelMap();bindIntelLinks();
}
function bindIntelLinks(){
  $$('button[data-intel-window]').forEach(b=>b.onclick=()=>void openIntelWindow(b.dataset.intelWindow));
  $$('[data-intel-locate]').forEach(b=>b.onclick=()=>showIntelSystem(b.dataset.intelLocate));
  if(EveDesktop.active)$$('[data-intel-pilot],[data-intel-kill],.intel-kill-links a').forEach(a=>a.onclick=e=>{e.preventDefault();void EveDesktop.openExternal(a.href).catch(e=>error(e.message));});
  $$('img[data-intel-image]').forEach(img=>img.onerror=()=>{img.hidden=true;});
}
function intelReportTable(rows,key){
  return table(['Időpont','Csatorna','Rendszer','Jelentett pilóták','Hajók','Állapot','Bejelentő','Eredeti üzenet','Művelet'],rows.map(r=>`<tr><td data-sort-value="${r.timestamp}">${intelDate(r.timestamp)}<div>${intelAge(r.timestamp)}</div></td><td>${verbatim(r.channel)}</td><td>${r.system_names.map(verbatim).join(', ')}</td><td>${r.pilots.map(p=>intelPilotName(p)+(p.verified?'':' <span class="badge">Szövegből felismert</span>')).join('<br>')||'–'}</td><td>${intelShips(r.ships)}</td><td><span class="badge ${r.state==='clear'?'good':r.state==='contact'?'warn':''}">${esc(intelLabels[r.state])}</span>${r.historical?'<div class="batch-note">Korábbi naplóbejegyzés</div>':''}${r.ambiguous?'<div class="batch-note">Több rendszer említve · ellenőrizd a forrást</div>':''}</td><td>${verbatim(r.reporter)}</td><td class="intel-raw" data-i18n-skip>${esc(r.message)}</td><td>${r.systems.map((sid,i)=>`<button class="text-button" data-intel-locate="${sid}">${verbatim(r.system_names[i])}</button>`).join('')}</td></tr>`),key);
}
function applyIntelTransform(){const group=$('#intel-map-transform');if(group)group.setAttribute('transform',`translate(${intelPan.x} ${intelPan.y}) scale(${intelZoom})`);}
function intelCard(node){
  const contacts=node.contacts||[],rows=contacts.map(r=>`<div class="intel-card-report"><div>${r.pilots.length?r.pilots.map(intelPilotName).join('<br>'):'<span>Nem megnevezett pilóta</span>'}</div>${r.ships?.length?`<div class="intel-card-ships">${intelShips(r.ships)}</div>`:''}${r.pilots.length>1&&(r.ships||[]).length?'<small>Több pilóta · közös hajójelentés</small>':''}<small>${intelAge(r.timestamp)}${r.ambiguous?' · <span>Bizonytalan helyszín</span>':''}</small></div>`).join('');
  const killed=node.kill_groups?.length?intelKillSummary(node.kill_groups):null;
  const killRow=killed?`<div class="intel-card-report intel-kill-summary"><strong>☠ ${fmt(killed.count)} kill</strong><div class="intel-card-ships">${intelKillShips(killed.ships)}</div><small>${intelAge(killed.last_at)} · <span>zKillboard-veszteségek</span></small><a data-intel-kill href="https://zkillboard.com/system/${node.id}/" target="_blank" rel="noopener noreferrer">zKillboard</a></div>`:'';
  return `<div xmlns="http://www.w3.org/1999/xhtml" class="intel-activity-card ${node.state==='old'?'old':''}"><div class="intel-card-header">${verbatim(node.name)}<span>${node.distance==null?'–':node.distance+'j'}</span></div><div class="intel-card-body">${rows}${killRow}</div></div>`;
}
function drawIntelMap(){
  clearTimeout(intelCardTimer);intelCardTimer=null;
  const target=$('#intel-map'),d=intelData;if(!target)return;
  const now=Date.now(),visibleNodes=d.nodes.map(n=>({...n,kill_count:(n.kill_groups||[]).reduce((sum,g)=>sum+g.count,0),kill_groups:(n.kill_groups||[]).filter(g=>now>=g.received*1000&&now<g.received*1000+intelCardLifetime),contacts:(n.contacts||[]).filter(r=>Number.isFinite(r.timestamp)&&now>=r.timestamp*1000&&now<r.timestamp*1000+intelCardLifetime)}));
  const expiries=visibleNodes.flatMap(n=>[...n.contacts.map(r=>r.timestamp*1000+intelCardLifetime),...n.kill_groups.map(g=>g.received*1000+intelCardLifetime)]);
  if(expiries.length){const expire=()=>{if(intelMapDragging){intelCardTimer=setTimeout(expire,100);return;}drawIntelMap();};intelCardTimer=setTimeout(expire,Math.max(1,Math.ceil(Math.min(...expiries)-now)));}
  const box=target.getBoundingClientRect();intelViewportHeight=box.width>0&&box.height>0?Math.max(260,Math.min(1100,1200*box.height/box.width)):720;
  const size={width:1200,height:intelViewportHeight},nodes=EveIntelMap.layout(visibleNodes,size),byId=new Map(nodes.map(n=>[n.id,n])),cards=EveIntelMap.callouts(nodes,size);
  target.innerHTML=nodes.length?`<svg viewBox="0 0 1200 ${intelViewportHeight}" role="group" aria-label="${esc(EveI18n.t('Inteltérkép'))}"><g id="intel-map-transform">${d.edges.map(([a,b])=>byId.has(a)&&byId.has(b)?`<line class="intel-gate ${byId.get(a).in_range&&byId.get(b).in_range?'in-range':''}" x1="${byId.get(a).lx}" y1="${byId.get(a).ly}" x2="${byId.get(b).lx}" y2="${byId.get(b).ly}"/>`:'').join('')}${nodes.map(n=>`<g class="intel-node ${n.state} ${n.in_range?'in-range':''} ${n.kill_count?'kill-activity':''} ${n.characters.length?'own':''} ${n.id===intelSelected?'selected':''}" role="button" tabindex="0" data-intel-system="${n.id}" aria-label="${esc(n.name+' · '+(n.distance==null?'–':n.distance)+' jump · '+EveI18n.t(intelLabels[n.state]))}" transform="translate(${n.lx},${n.ly})"><title>${esc([n.name,...n.characters,...n.pilots].join(' · '))}</title>${n.in_range?'<circle class="intel-range-halo" r="15"/>':''}${n.characters.length?'<circle class="intel-own-ring" r="10"/>':''}${n.kill_count?'<circle class="intel-kill-ring" r="8"/>':''}<circle class="intel-system-dot" r="5"/>${n.kill_count?`<text class="intel-kill-count" x="-9" y="-13">☠ ${n.kill_count}</text>`:''}<text data-i18n-skip x="10" y="3">${esc(n.name)}</text>${n.distance!=null&&n.in_range?`<text class="intel-jump-label" x="10" y="15">${n.distance}j</text>`:''}</g>`).join('')}${cards.map(c=>`<line class="intel-callout-line" x1="${c.node.lx}" y1="${c.node.ly}" x2="${c.x}" y2="${c.y+18}"/><foreignObject x="${c.x}" y="${c.y}" width="${c.width}" height="${c.height}">${intelCard(c.node)}</foreignObject>`).join('')}</g></svg>`:empty('Nincs kiválasztott rendszer','Válassz karaktert vagy kattints egy intelüzenet rendszerére.');
  applyIntelTransform();const svg=target.querySelector('svg');if(!svg)return;
  let drag=null,moved=false;
  svg.onpointerdown=e=>{if(e.button!==0||e.target.closest('.intel-activity-card'))return;drag={x:e.clientX,y:e.clientY,px:intelPan.x,py:intelPan.y,node:e.target.closest('[data-intel-system]')};moved=false;intelMapDragging=true;svg.setPointerCapture?.(e.pointerId);};
  svg.onpointermove=e=>{if(!drag)return;const rect=svg.getBoundingClientRect(),scale=Math.max(1200/rect.width,intelViewportHeight/rect.height),dx=(e.clientX-drag.x)*scale,dy=(e.clientY-drag.y)*scale;if(Math.abs(dx)+Math.abs(dy)>4)moved=true;intelPan={x:drag.px+dx,y:drag.py+dy};applyIntelTransform();};
  svg.onpointerup=e=>{const node=drag?.node;drag=null;intelMapDragging=false;svg.releasePointerCapture?.(e.pointerId);if(!moved&&node){intelSelected=Number(node.dataset.intelSystem);render();}};svg.onpointercancel=()=>{drag=null;intelMapDragging=false;};
  svg.addEventListener('wheel',e=>{if(e.target.closest('.intel-activity-card'))return;e.preventDefault();const old=intelZoom;intelZoom=Math.max(.25,Math.min(5,intelZoom*(e.deltaY<0?1.12:1/1.12)));const rect=svg.getBoundingClientRect(),scale=Math.min(rect.width/1200,rect.height/intelViewportHeight),x=(e.clientX-rect.left-(rect.width-1200*scale)/2)/scale,y=(e.clientY-rect.top-(rect.height-intelViewportHeight*scale)/2)/scale;intelPan={x:x-(x-intelPan.x)*intelZoom/old,y:y-(y-intelPan.y)*intelZoom/old};applyIntelTransform();},{passive:false});
  $$('[data-intel-system]').forEach(node=>{node.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();intelSelected=Number(node.dataset.intelSystem);render();}};});
  bindIntelLinks();intelResizeObserver?.disconnect();if(globalThis.ResizeObserver){intelResizeObserver=new ResizeObserver(entries=>{const r=entries[0]?.contentRect;if(r&&(Math.abs(r.width-box.width)>2||Math.abs(r.height-box.height)>2))drawIntelMap();});intelResizeObserver.observe(target);}
}
function intelChatMessage(r){
  const text=r.message.replace(/<[^>]*>/g,''),tokens=[];
  for(const p of r.pilots){if(intelPilotUrl(p))tokens.push({text:p.name,html:intelPilotName(p)});}
  r.systems.forEach((id,index)=>tokens.push({text:r.system_names[index],html:`<button class="intel-chat-system" data-intel-locate="${id}">${verbatim(r.system_names[index])}</button>`}));
  const matches=[],lower=text.toLocaleLowerCase('en');
  for(const token of tokens){let at=0;while(token.text&&(at=lower.indexOf(token.text.toLocaleLowerCase('en'),at))!==-1){const end=at+token.text.length;if(!/[\wÀ-ž-]/.test(text[at-1]||' ')&&!/[\wÀ-ž-]/.test(text[end]||' '))matches.push({at,end,html:token.html});at=end;}}
  matches.sort((a,b)=>a.at-b.at||b.end-a.end);let out='',last=0;for(const m of matches){if(m.at<last)continue;out+=esc(text.slice(last,m.at))+m.html;last=m.end;}return out+esc(text.slice(last));
}
function renderIntelChat(content){
  setHead('HELYI INTEL','Összevont intelchat','A kiválasztott csatornák közös, csak olvasható üzenetfolyama.');$('#plan-status').hidden=true;
  actions('<button class="button compact" data-intel-window="map">Térkép külön ablakban</button><button class="button compact" id="intel-refresh">Állapot frissítése</button>');$('#intel-refresh').onclick=()=>void refreshIntel();bindIntelLinks();
  if(!intelData){content.innerHTML=empty('Inteladatok betöltése');void refreshIntel();return;}
  content.innerHTML=`<div class="intel-chat-toolbar"><div data-i18n-skip>${esc(intelData.preferences.channels.join(' · '))}</div><label><input id="intel-chat-auto" type="checkbox" ${intelChatAuto?'checked':''}> Automatikus görgetés</label></div><div id="intel-chat-feed" class="intel-chat-feed" role="log" aria-live="polite" aria-relevant="additions"></div><div class="intel-chat-status"><span id="intel-chat-count"></span><span id="intel-chat-state"></span> · <span>Utolsó ellenőrzés:</span> <span id="intel-watcher-time"></span></div>`;
  $('#intel-chat-auto').onchange=e=>{intelChatAuto=e.target.checked;if(intelChatAuto){const feed=$('#intel-chat-feed');feed.scrollTop=feed.scrollHeight;}};
  $('#intel-chat-feed').onscroll=()=>{const feed=$('#intel-chat-feed');intelChatAuto=feed.scrollHeight-feed.scrollTop-feed.clientHeight<40;$('#intel-chat-auto').checked=intelChatAuto;};updateIntelChat();
}
function updateIntelChat(){
  const feed=$('#intel-chat-feed');if(!feed||!intelData)return;
  const anchor=[...feed.children].find(r=>r.getBoundingClientRect().bottom>feed.getBoundingClientRect().top),anchorTop=anchor?.getBoundingClientRect().top;
  const rows=[...intelData.reports].sort((a,b)=>a.timestamp-b.timestamp||a.id.localeCompare(b.id)),known=new Map([...feed.children].map(el=>[el.dataset.reportId,el])),keep=new Set(rows.map(r=>r.id));
  for(const [id,el] of known)if(!keep.has(id))el.remove();
  for(const r of rows){let el=known.get(r.id);const signature=JSON.stringify([r,EveI18n.language]);
    if(!el){el=document.createElement('div');el.className='intel-chat-line '+r.state;el.dataset.reportId=r.id;feed.append(el);}
    if(el.dataset.signature!==signature){el.dataset.signature=signature;el.innerHTML=`<time>${EveI18n.date(r.timestamp*1000,{hour:'2-digit',minute:'2-digit',second:'2-digit'})}</time><span class="intel-chat-channel" data-i18n-skip>[${esc(r.channel)}]</span><span class="intel-chat-reporter" data-i18n-skip>${esc(r.reporter)} &gt;</span><span class="intel-chat-message" data-i18n-skip>${intelChatMessage(r)}</span>${r.ships?.length?'<span class="intel-chat-ships">'+intelShips(r.ships)+'</span>':''}`;}
  }
  if(intelChatAuto)feed.scrollTop=feed.scrollHeight;else if(anchor?.isConnected)feed.scrollTop+=anchor.getBoundingClientRect().top-anchorTop;
  $('#intel-chat-count').textContent=EveI18n.t('{0} üzenet').replace('{0}',fmt(rows.length));$('#intel-chat-state').textContent=EveI18n.t(intelData.status.error||(!intelData.preferences.enabled?'Chatlogfigyelés kikapcsolva':'Chatlogfigyelés bekapcsolva'));updateIntelStatus();bindIntelLinks();
}

function bindIntelSystemInput(input){
  let timer,revision=0;const box=document.createElement('div');box.className='intel-system-results';box.hidden=true;input.after(box);
  input.oninput=()=>{input.dataset.systemId='';const rev=++revision;clearTimeout(timer);if(!input.value.trim()){box.hidden=true;return;}timer=setTimeout(async()=>{try{const rows=await api('/api/intel/systems?q='+encodeURIComponent(input.value));if(rev!==revision||!input.isConnected)return;box.innerHTML=rows.map(s=>`<button type="button" data-system-id="${s.id}">${verbatim(s.name)} <small>${verbatim(s.region)}</small></button>`).join('');box.hidden=!rows.length;box.querySelectorAll('button').forEach(b=>b.onclick=()=>{revision++;input.dataset.systemId=b.dataset.systemId;input.value=rows.find(s=>s.id===Number(b.dataset.systemId)).name;box.hidden=true;input.dispatchEvent(new Event('change',{bubbles:true}));});}catch(e){error(e.message);}},180);};
  input.onkeydown=e=>{if(e.key==='Escape'){box.hidden=true;}else if(e.key==='Enter'&&!box.hidden){e.preventDefault();box.querySelector('button')?.click();}else if(e.key==='ArrowDown'){e.preventDefault();box.querySelector('button')?.focus();}};
}
function renderIntelSettings(target){
  if(!intelData){target.innerHTML=empty('Inteladatok betöltése');void refreshIntel();return;}
  const d=intelData,p=d.preferences;
  target.innerHTML=panel('Chatlog és riasztás','',`<form id="intel-settings" class="panel-body"><div class="intel-preferences"><label class="field-full">Chatlogmappa<div class="intel-folder-row"><input name="folder" type="text" value="${esc(p.folder)}" placeholder="Documents/EVE/logs/Chatlogs"><button type="button" class="button compact" id="intel-folder-pick" ${EveDesktop.active?'':'disabled'}>Mappa kiválasztása</button><button type="button" class="button compact" id="intel-discover">Csatornák keresése</button></div></label><label class="field-full">Figyelt csatornák · soronként egy<textarea name="channels" rows="3" data-i18n-skip>${esc(p.channels.join('\n'))}</textarea></label><div id="intel-channel-options" class="field-full"></div><label><input name="enabled" type="checkbox" ${p.enabled?'checked':''}> Chatlogfigyelés bekapcsolva</label><label><input name="killfeed_enabled" type="checkbox" ${p.killfeed_enabled?'checked':''}> zKillboard-killek az intelben</label><label>Killértesítések régiója<select name="kill_region"><option value="">A figyelt karakterek régiói</option>${d.regions.map(([id,name])=>`<option data-i18n-skip value="${id}">${esc(name)}</option>`).join('')}</select></label><label>Riasztási távolság (jump)<input name="jumps" type="number" min="0" max="30" value="${p.jumps}" required></label><label>Intel érvényessége (perc)<input name="ttl_minutes" type="number" min="1" max="120" value="${p.ttl_minutes}" required></label><label>Riasztási szünet azonos rendszerhez (mp)<input name="cooldown_seconds" type="number" min="0" max="600" value="${p.cooldown_seconds}" required></label><label><input name="allow_local_alerts" type="checkbox" ${p.allow_local_alerts?'checked':''}> Friss Local-napló helyzetével is riasszon</label><label><input name="sound" type="checkbox" ${p.sound?'checked':''}> Hang az intel rendszerértesítésében</label><label>Rövidített rendszernevek régiója<select name="region"><option value="">Összes régió · csak egyértelmű rövidítés</option>${d.regions.map(([id,name])=>`<option data-i18n-skip value="${id}">${esc(name)}</option>`).join('')}</select></label></div><p class="footnote">Csak a kiválasztott csatornákat olvassuk, és saját karakterek Local-rendszerváltásait használjuk. A chatlog nem kerül külső szolgáltatáshoz. A Local-napló nem igazolja az online állapotot; riasztáshoz legfeljebb 5 perces Local-adat használható. A kézi referencia nem követi a mozgást.</p><p class="footnote">Az ESI-helyzeteket és pilótaazonosítókat automatikusan legfeljebb 15 percenként kérjük le. A helyi chatlog olvasása folyamatos marad; a kézi frissítés külön indítható.</p>${table(['Figyelt karakter','Helyzet forrása','Utolsó helyzet','Kézi referenciarendszer','EVE-hozzáférés'],state.characters.map(c=>{const pos=d.characters.find(x=>x.id===c.id),manual=p.manual_locations[c.id];return `<tr><td><label><input type="checkbox" data-intel-character="${c.id}" ${p.character_ids===null||p.character_ids.includes(c.id)?'checked':''}> ${verbatim(c.name)}</label></td><td>${esc(pos?intelSource(pos):'Nincs helyzetadat')}</td><td>${verbatim(pos?.system_name||'–')}<div>${intelDate(pos?.as_of)}</div></td><td class="intel-system-cell"><input type="search" data-intel-manual="${c.id}" data-system-id="${manual||''}" value="${esc(manual?d.manual_system_names[c.id]||'':'')}" placeholder="Üres: automatikus helyzet" autocomplete="off"></td><td><div>${esc(pos?.error||(pos?.needs_auth?'Engedélyezés szükséges':''))}</div><button class="text-button" type="button" data-intel-authorize="${c.id}">Intelhelyzet engedélyezése</button></td></tr>`;}),'intel-characters')}<div class="actions"><button class="button primary" type="submit">Intelbeállítások mentése</button><button class="button" type="button" id="intel-location-refresh">ESI-helyzetek frissítése</button><button class="text-button" type="button" data-open-settings="notifications">Rendszerértesítések beállítása</button></div></form><div class="panel-body"><details><summary>Szükséges ESI-jogosultságok</summary><code>esi-location.read_location.v1 · esi-location.read_online.v1</code><p>A Client ID EVE Developer alkalmazásában is engedélyezni kell a két scope-ot, majd a karaktert egyszer újra kell engedélyezni. A korábbi jogosultságok megmaradnak.</p></details><p>A chatintelhez íródó EVE-chatlog kell. A killintelhez a Fleet activity élő zKillboard-követése szükséges. A killértesítések az egész kijelölt régióra vonatkoznak, a chatriasztások a megadott jumptávolságra. Mindkettő csak futó appnál működik, és az Intelértesítések kapcsolót követi.</p></div>`);
  target.innerHTML+=panel('Átlátszó inteljelző','',`<div class="panel-body" id="intel-overlay-settings"></div>`);renderIntelOverlaySettings($('#intel-overlay-settings'));if(intelOverlayNative)void loadIntelOverlaySettings();
  const form=$('#intel-settings');form.elements.region.value=p.region_ids[0]||'';form.elements.kill_region.value=p.kill_region_ids?.[0]||'';form.oninput=()=>dirty.intel=true;form.onchange=()=>dirty.intel=true;
  $$('[data-intel-manual]').forEach(bindIntelSystemInput);
  form.onsubmit=async e=>{e.preventDefault();try{
    const manual={};for(const input of $$('[data-intel-manual]')){if(input.value.trim()&&!input.dataset.systemId)throw Error('Válassz rendszert a találati listából, vagy töröld a kézi helyszínt.');if(input.dataset.systemId)manual[input.dataset.intelManual]=Number(input.dataset.systemId);}
    const body={folder:form.elements.folder.value,channels:form.elements.channels.value.split('\n').map(s=>s.trim()).filter(Boolean),character_ids:$$('[data-intel-character]:checked').map(c=>Number(c.dataset.intelCharacter)),manual_locations:manual,region_ids:form.elements.region.value?[Number(form.elements.region.value)]:[]};
    body.kill_region_ids=form.elements.kill_region.value?[Number(form.elements.kill_region.value)]:[];for(const key of ['enabled','killfeed_enabled','allow_local_alerts','sound'])body[key]=form.elements[key].checked;for(const key of ['jumps','ttl_minutes','cooldown_seconds'])body[key]=Number(form.elements[key].value);
    await api('/api/intel/preferences',body);intelEnabled=body.enabled;delete dirty.intel;await refreshIntel();toast('Intelbeállítások mentve.');void pollIntelAlerts();
  }catch(e){error(e.message);}};
  $('#intel-folder-pick').onclick=async()=>{try{const result=await EveDesktop.chooseIntelFolder();if(result.path){form.elements.folder.value=result.path;dirty.intel=true;}}catch(e){error(e.message);}};
  $('#intel-discover').onclick=async()=>{try{const result=await api('/api/intel/channels?folder='+encodeURIComponent(form.elements.folder.value));intelDiscovered=result.channels;$('#intel-channel-options').innerHTML=intelDiscovered.map(name=>`<button type="button" class="button compact" data-intel-add="${esc(name)}">${verbatim(name)}</button>`).join('');$$('[data-intel-add]').forEach(b=>b.onclick=()=>{const names=new Set(form.elements.channels.value.split('\n').filter(Boolean));names.add(b.dataset.intelAdd);form.elements.channels.value=[...names].join('\n');dirty.intel=true;});}catch(e){error(e.message);}};
  $('#intel-location-refresh').onclick=async()=>{try{await api('/api/intel/locations',{});await refreshIntel();}catch(e){error(e.message);}};
  $$('[data-intel-authorize]').forEach(b=>b.onclick=async()=>{try{const auth=await api('/api/auth/start',{character_id:Number(b.dataset.intelAuthorize),feature:'intel'});sessionStorage.setItem('eve-muhely-auth-return','settings:intel');await openEveAuthorization(auth);await refreshIntel();}catch(e){error(e.message);}});
}

let intelOverlayNative=null;
async function loadIntelOverlaySettings(){
  const target=$('#intel-overlay-settings');if(!target||!EveDesktop.active||EveDesktop.platform==='windows')return;
  try{const info=await EveDesktop.intelOverlayStatus();if(!target.isConnected||dirty.intel_overlay)return;intelOverlayNative=info;renderIntelOverlaySettings(target);}catch(e){target.textContent=EveI18n.t(e.message);}
}
function renderIntelOverlaySettings(target){
  if(EveDesktop.platform==='windows'){target.innerHTML='<p>Az átlátszó inteljelző ebben a Windows-verzióban még nem érhető el. A külön térkép- és chatablak használható.</p>';return;}
  if(!EveDesktop.active){target.innerHTML='<p>Az átlátszó inteljelző a Mac-alkalmazásban érhető el.</p>';return;}
  const info=intelOverlayNative,p=intelData.preferences;if(!info){target.innerHTML='<p>Betöltés…</p>';void loadIntelOverlaySettings();return;}
  const pos=info.placement;
  target.innerHTML=`<form id="intel-overlay-form"><div class="intel-preferences"><label><input name="overlay_enabled" type="checkbox" ${p.overlay_enabled!==false?'checked':''}> Átlátszó inteljelző bekapcsolva</label><label>Megjelenítési idő (másodperc)<input name="overlay_seconds" type="number" min="1" max="3600" step="1" required value="${p.overlay_seconds||60}"></label><label>Monitor<select name="screen_id">${info.screens.map(s=>`<option value="${esc(s.id)}" data-i18n-skip>${esc(s.name)} · ${fmt(s.width)} × ${fmt(s.height)}</option>`).join('')}</select></label><label>Szélesség<input name="width" type="number" min="260" max="600" required value="${pos.width}"></label><label>X · a bal széltől<input name="x" type="number" min="0" max="20000" required value="${Math.round(pos.x)}"></label><label>Y · a felső széltől<input name="y" type="number" min="0" max="20000" required value="${Math.round(pos.y)}"></label></div><div class="actions"><button type="submit" class="button primary">Inteljelző mentése</button><button type="button" class="button" id="intel-overlay-move">Inteljelző mozgatása</button><button type="button" class="button" id="intel-overlay-lock">Elhelyezés kész · pozíció beolvasása</button></div></form><p class="footnote">Üresen nem látható, normál módban átengedi az egérkattintásokat. Csak friss, a riasztási jumptávolságon belüli jelentéseket mutat, legfeljebb ötöt egyszerre. A jelentés az üzenet időpontjától számított megjelenítési idő után eltűnik.</p><p class="footnote">A normál és teljes képernyős alkalmazások felett jelenik meg. A macOS rendszer- és biztonsági felületei elsőbbséget élvezhetnek. A monitor és a pozíció ezen a Macen mentődik.</p>`;
  const form=$('#intel-overlay-form');form.elements.screen_id.value=info.screen_id;
  const placement=()=>({screen_id:form.elements.screen_id.value,x:Number(form.elements.x.value),y:Number(form.elements.y.value),width:Number(form.elements.width.value)});
  form.oninput=()=>dirty.intel_overlay=true;
  form.elements.screen_id.onchange=()=>{const saved=info.screens.find(s=>s.id===form.elements.screen_id.value)?.placement;if(saved)for(const k of ['x','y','width'])form.elements[k].value=Math.round(saved[k]);dirty.intel_overlay=true;};
  form.onsubmit=async e=>{e.preventDefault();if(!form.reportValidity())return;try{
    await EveDesktop.configureIntelOverlay({...placement(),editing:false});
    const body={overlay_enabled:form.elements.overlay_enabled.checked,overlay_seconds:Number(form.elements.overlay_seconds.value)};
    await api('/api/intel/preferences',body);Object.assign(intelData.preferences,body);delete dirty.intel_overlay;
    await syncIntelOverlay(await api('/api/intel/alerts'));await loadIntelOverlaySettings();toast('Inteljelző mentve.');
  }catch(e){error(e.message);}};
  $('#intel-overlay-move').onclick=async()=>{try{if(!form.reportValidity())return;await EveDesktop.configureIntelOverlay({...placement(),editing:true});toast('Húzd az inteljelzőt a helyére, majd válaszd a Kész gombot.');}catch(e){error(e.message);}};
  $('#intel-overlay-lock').onclick=async()=>{try{const latest=await EveDesktop.configureIntelOverlay({editing:false});intelOverlayNative=latest;for(const key of ['x','y','width'])form.elements[key].value=Math.round(latest.placement[key]);form.elements.screen_id.value=latest.screen_id;toast('Az ablak pozíciója elmentve.');}catch(e){error(e.message);}};
}
