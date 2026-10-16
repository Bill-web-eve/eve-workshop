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
  content.innerHTML+=`<details class="panel skill-permissions" ${data.corporations.some(c=>c.ready)?'':'open'}><summary>Corp-hozzáférés beállítása</summary><div class="panel-body"><p>Az <a href="https://developers.eveonline.com/applications" target="_blank" rel="noopener noreferrer">EVE Developer oldalon</a> a meglévő alkalmazáshoz add hozzá az alábbi olvasási jogosultságokat, majd az arra jogosult karakter mellett kattints a <strong>Corp-hozzáférés engedélyezése</strong> gombra.</p><code>${state.corporation_scopes.map(esc).join('\n')}</code><p>A corp készlethez és blueprintekhez <strong>Director</strong>, a jobokhoz <strong>Factory Manager</strong> szerepkör kell. Egy corporationből egy megfelelő hozzáférésű karakter elegendő; több karakterrel sem számoljuk többször a készletet.</p></div></details>`;
  const rows=data.corporations.map(c=>`<tr><td><strong>${verbatim(c.name)}</strong><div class="batch-note">${c.id}</div></td><td>${c.ready?`<span class="badge ${c.stale?'warn':'good'}">${c.stale?'Korábbi pillanatkép':'Betöltve'}</span>`:'<span class="badge warn">Hozzáférés / frissítés szükséges</span>'}${c.error?`<div class="row-warning">${esc(c.error)}</div>`:''}${!c.members.length?'<div class="row-warning">Nincs hozzáadott tagkarakter.</div>':''}</td><td class="num">${c.asset_count==null?'–':fmt(c.asset_count)}</td><td class="num">${c.blueprint_count==null?'–':fmt(c.blueprint_count)}</td><td class="num">${c.job_count==null?'–':fmt(c.job_count)}</td><td data-sort-value="${c.synced_at??''}">${esc(date(c.synced_at))}</td><td><button type="button" class="button compact" data-corp-use="${c.id}">Corp gyártás kiválasztása</button></td></tr>`);
  content.innerHTML+=data.corporations.length?panel('Corporationonkénti adatok',`${rows.length} corporation`,table(['Corporation','Adatállapot','Assettételek','Blueprintok','Aktív jobok','Ellenőrizve','Művelet'],rows)):
    empty('Még nincs felderített corporation','Add hozzá a karaktereket, majd indítsd el a corp-adatok felderítését.');
  content.innerHTML+=panel('Hozzáadott karakterek corp-hozzáférése','A személyes karakterválasztó nem korlátozza a corp lekérést',table(['Karakter','Corporation','Hozzáférés','Művelet'],data.characters.map(c=>`<tr><td data-filter-value="${esc(c.name)}">${esc(c.name)}<div class="batch-note">${c.id}</div></td><td>${data.corporations.some(x=>x.id===c.corporation_id)?verbatim(data.corporations.find(x=>x.id===c.corporation_id).name):esc('Még nincs felderítve')}</td><td>${esc(c.access?.error||(c.access&&!c.access.needs_auth?'Olvasási engedély megadva':'Corp-engedélyezés szükséges'))}</td><td><button type="button" class="button compact" data-corp-auth="${c.id}" aria-label="${esc(c.name)} – Corp-hozzáférés engedélyezése">Corp-hozzáférés engedélyezése</button></td></tr>`)));
  $$('[data-corp-auth]').forEach(button=>button.onclick=async()=>{
    try{button.disabled=true;error('');const auth=await api('/api/auth/start',{character_id:Number(button.dataset.corpAuth),feature:'corporations'});sessionStorage.setItem('eve-muhely-auth-return','corporations');window.location.assign(auth.url);}
    catch(e){error(e.message);button.disabled=false;}
  });
  $$('[data-corp-use]').forEach(button=>button.onclick=async()=>{await setProductionScope(Number(button.dataset.corpUse));if(corporationId===Number(button.dataset.corpUse))navigate('inventory');});
}
