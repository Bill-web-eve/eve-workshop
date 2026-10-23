'use strict';
let corporationData=null,corporationRequest=null;
async function refreshCorporations(){
  if(corporationRequest)return;
  corporationRequest=api('/api/corporations');
  try{corporationData=await corporationRequest;if(view==='corporations')render();}
  catch(e){error(e.message);}
  finally{corporationRequest=null;}
}
function renderCorporations(content){
  setHead('CORPORATION KÉSZLETEK','Corporationok','Külön készlet, blueprintek és ipari jobok minden corporationhöz. A személyes tervekkel nincs közös készletfoglalás.');
  $('#plan-status').hidden=true;
  actions(`<button class="button primary compact" id="corp-sync" ${state.task.running?'disabled':''}>Corp-adatok felderítése és frissítése</button>`);
  $('#corp-sync').onclick=()=>startTask('/api/corporations/sync');
  if(!corporationData){content.innerHTML=empty('Corp-adatok betöltése');void refreshCorporations();return;}
  const data=corporationData;
  content.innerHTML='<div class="banner"><strong>Corp gyártás = egyetlen corporation készlete és jobjai.</strong><div>A gyártási körben válaszd ki a corporationt. A személyes készlet és más corporation készlete nem használható fel. A korábbi mentett tervek személyesek maradtak.</div></div>';
  content.innerHTML+=settingsShortcut('A corporation hozzáféréseit a Beállítások → Adathozzáférések oldalon kezelheted.');
  const rows=data.corporations.map(c=>`<tr><td><strong>${verbatim(c.name)}</strong><div class="batch-note">${c.id}</div></td><td>${!c.monitoring_enabled?'<span class="badge">Figyelés kikapcsolva</span>':c.ready?`<span class="badge ${c.stale?'warn':'good'}">${c.stale?'Korábbi pillanatkép':'Betöltve'}</span>`:'<span class="badge warn">Hozzáférés / frissítés szükséges</span>'}${c.monitoring_enabled&&c.error?`<div class="row-warning">${esc(c.error)}</div>`:''}${!c.members.length?'<div class="row-warning">Nincs hozzáadott tagkarakter.</div>':''}</td><td><label><input type="checkbox" data-corp-monitor="${c.id}" ${c.monitoring_enabled?'checked':''} ${state.task.running?'disabled':''}> Figyelés</label></td><td class="num">${c.asset_count==null?'–':fmt(c.asset_count)}</td><td class="num">${c.blueprint_count==null?'–':fmt(c.blueprint_count)}</td><td class="num">${c.job_count==null?'–':fmt(c.job_count)}</td><td data-sort-value="${c.synced_at??''}">${esc(date(c.synced_at))}</td><td><button type="button" class="button compact" data-corp-use="${c.id}">Corp gyártás kiválasztása</button></td></tr>`);
  content.innerHTML+=data.corporations.length?panel('Corporationonkénti adatok',`${rows.length} corporation`,table(['Corporation','Adatállapot','Figyelés','Assettételek','Blueprintok','Aktív jobok','Ellenőrizve','Művelet'],rows)):
    empty('Még nincs felderített corporation','Add hozzá a karaktereket, majd indítsd el a corp-adatok felderítését.');

  content.innerHTML+='<p class="footnote">Kikapcsolt figyelésnél nem kérünk le corporationkészletet, blueprinteket, jobokat vagy corp holdidőzítőket. A korábbi helyi adatok megmaradnak. Az automatikus ESI-frissítések között legalább 15 perc telik el; a frissítés gomb kézi ellenőrzést indít.</p>';
  $$('[data-corp-monitor]').forEach(input=>input.onchange=async()=>{const enabled=input.checked;input.disabled=true;try{corporationData=await api('/api/corporations/monitoring',{id:Number(input.dataset.corpMonitor),enabled});await reloadState();render();toast(enabled?'Corporationfigyelés bekapcsolva.':'Corporationfigyelés kikapcsolva.');}catch(e){input.checked=!enabled;error(e.message);input.disabled=false;}});
  $$('[data-corp-use]').forEach(button=>button.onclick=async()=>{await setProductionScope(Number(button.dataset.corpUse));if(corporationId===Number(button.dataset.corpUse))navigate('inventory');});
}
