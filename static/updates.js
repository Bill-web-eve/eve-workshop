'use strict';
// Only the MAIN native window schedules checks; the service deduplicates them.
let updateData=null,updatePoll=null,updateDaily=null,updateInstallRequested=false;
const updatePhases={idle:'Még nincs ellenőrzés',checking:'Frissítések keresése…',available:'Új verzió érhető el',current:'A legújabb verziót használod',unpublished:'Még nincs közzétett, aláírt frissítés',downloading:'Frissítés letöltése…',verifying:'Aláírás és fájltartalom ellenőrzése…',ready:'A frissítés telepítésre kész',preparing:'Telepítés előkészítése…',installing:'Az alkalmazás újraindul…',error:'A frissítés nem sikerült'};
const updateErrors={invalid_update:'A frissítési adatok érvénytelenek.',invalid_signature:'A frissítés aláírása nem érvényes. A telepítés letiltva.',invalid_archive:'A letöltött fájl nem egyezik az aláírt csomaggal.',unsafe_archive:'A frissítési csomag nem biztonságos. A telepítés letiltva.',missing_update_key:'Hiányzik a frissítések ellenőrzőkulcsa.',older_update:'Régebbi frissítési adatok érkeztek. A korábban ellenőrzött verzió megmaradt.',manual_install_required:'Ehhez a példányhoz kézi telepítés szükséges. Telepítsd a frissítőt tartalmazó teljes csomagot.',update_network_error:'A frissítési szolgáltatás nem érhető el. Próbáld újra később.',update_close_timeout:'Az alkalmazás nem állt le időben. A fájlok változatlanok.',update_install_failed:'A telepítés nem sikerült. Ellenőrizd az írási jogosultságot és a szabad helyet.',update_restart_failed:'A frissítés telepítve, de az újraindítás nem sikerült. Indítsd el az alkalmazást.',expired_update:'A letöltött frissítés lejárt. Töltsd le újra.',update_already_started:'A frissítés előkészítése már elindult. Ha nem állt le az app, keress újra frissítést.',update_task_running:'Várd meg a folyamatban lévő adatfrissítés végét.'};
function updateText(s){return EveI18n.t(s);}
function updateMessage(d){return updateText(updateErrors[d?.error]||updatePhases[d?.phase]||updatePhases.idle);}
function updateNativeMain(){return !!globalThis.EveDesktop?.active&&!new URLSearchParams(location.search).has('intel_window');}
function paintUpdateBanner(){
 const box=document.querySelector('#update-banner');if(!box)return;
 box.replaceChildren();box.hidden=!updateData?.available||!updateNativeMain();if(box.hidden)return;
 const label=document.createElement('span');label.textContent=updateText('Új verzió érhető el')+': '+updateData.latest_version+' · '+updateMessage(updateData);box.append(label);
 const button=document.createElement('button');button.type='button';button.className='button compact';button.textContent=updateText('Frissítések megnyitása');button.onclick=()=>openSettingsTab('updates');box.append(button);
}
function updatePanelHTML(){
 const d=updateData,active=updateNativeMain(),busy=!!d?.busy;
 const progress=d&&['downloading','verifying','ready'].includes(d.phase)?`<progress max="100" value="${Math.max(0,Math.min(100,Number(d.progress)||0))}" aria-label="${esc(updateText('Frissítés állapota'))}"></progress><span>${Math.round((d.bytes||0)/1048576)} / ${Math.round((d.total||0)/1048576)} MB</span>`:'';
 const checked=d?.checked_at?new Date(d.checked_at*1000).toLocaleString(EveI18n.language==='en'?'en-GB':'hu-HU'):updateText('Még nincs ellenőrzés');
 return `<div class="panel-body" data-i18n-skip><div class="section-actions"><strong>${esc(updateText('Telepített verzió'))}: ${esc(d?.current_version||state?.version||'–')}</strong>${d?.latest_version?`<span>${esc(updateText('Elérhető verzió'))}: ${esc(d.latest_version)}</span>`:''}<label><input id="updates-automatic" type="checkbox" ${d?.automatic!==false?'checked':''} ${!active||busy?'disabled':''}> ${esc(updateText('Frissítések automatikus keresése naponta'))}</label></div><p role="status">${esc(d?updateMessage(d):updateText('Adatok betöltése…'))}</p><div class="section-actions">${progress}<button class="button compact" id="updates-check" ${!active||busy?'disabled':''}>${esc(updateText('Frissítések keresése'))}</button><button class="button primary compact" id="updates-install" ${!active||!d?.available||!d.installable||busy?'disabled':''}>${esc(updateText(d?.phase==='ready'?'Telepítés és újraindítás':'Letöltés és újraindítás'))}</button>${d?.notes_url?`<button class="text-button" id="updates-notes">${esc(updateText('Kiadási megjegyzések'))}</button>`:''}</div><p class="footnote">${esc(updateText('Utolsó ellenőrzés'))}: ${esc(checked)}</p>${!active?`<p>${esc(updateText('Az alkalmazáson belüli frissítés a saját Mac- vagy Windows-ablakban használható.'))}</p>`:d&&!d.installable?`<p class="warning-text">${esc(updateText(updateErrors.manual_install_required))}</p>`:''}<p>${esc(updateText('A telepítés bezárja az alkalmazást és az összes külön ablakát. A karakterek, tervek és beállítások megmaradnak; előtte adatbázismentés készül.'))}</p><p class="footnote">${esc(updateText('Csak saját kulccsal hitelesített stabil kiadások telepíthetők. Macen a preview engedélyeit a rendszer újra kérheti.'))}</p>${d?.last_result?.error?`<p class="warning-text">${esc(updateText(updateErrors[d.last_result.error]||updateErrors.update_install_failed))}</p>`:''}</div>`;
}
function renderUpdateSettings(target){
 target.innerHTML=panel('Frissítések','',updatePanelHTML());bindUpdateSettings();if(!updateData)void refreshUpdates();
}
function bindUpdateSettings(){
 const q=s=>document.querySelector(s);
 if(q('#updates-check'))q('#updates-check').onclick=()=>void requestUpdates('check',true);
 if(q('#updates-install'))q('#updates-install').onclick=()=>void installUpdate();
 if(q('#updates-notes'))q('#updates-notes').onclick=()=>void EveDesktop.openExternal(updateData.notes_url).catch(e=>error(e.message));
 if(q('#updates-automatic'))q('#updates-automatic').onchange=async e=>{try{updateData=await api('/api/updates/preferences',{automatic:e.target.checked});paintUpdates();}catch(ex){error(ex.message);}};
}
function paintUpdates(){
 paintUpdateBanner();scheduleNextUpdateCheck();
 const locked=!!updateData?.busy&&['preparing','installing'].includes(updateData.phase);
 document.body.classList.toggle('update-installing',locked);
 let blocker=document.querySelector('#update-install-blocker');
 if(locked&&!blocker){blocker=document.createElement('div');blocker.id='update-install-blocker';blocker.setAttribute('role','status');blocker.tabIndex=-1;document.body.append(blocker);blocker.focus();}
 if(blocker){blocker.textContent=updateMessage(updateData);blocker.hidden=!locked;}

 if(typeof view!=='undefined'&&view==='settings'&&settingsTab==='updates'){
  const target=document.querySelector('#settings-content');if(target){target.innerHTML=panel('Frissítések','',updatePanelHTML());bindUpdateSettings();}
 }
}
function scheduleUpdatePoll(){
 clearTimeout(updatePoll);if(!updateData?.busy)return;
 updatePoll=setTimeout(()=>void refreshUpdates(),1000);
}
async function refreshUpdates(){
 try{updateData=await api('/api/updates');paintUpdates();scheduleUpdatePoll();if(updateInstallRequested&&!updateData.busy){updateInstallRequested=false;if(updateData.phase==='ready')void installUpdate();}}catch(e){if(typeof error==='function')error(e.message);}
}
async function requestUpdates(action,manual=true){
 if(!updateNativeMain())return;
 try{updateData=await api('/api/updates/'+action,{manual});paintUpdates();scheduleUpdatePoll();}catch(e){error(e.message);}
}
async function installUpdate(){
 if(!updateNativeMain()||!updateData?.installable||!updateData.available||updateData.busy)return;
 if(typeof dirty!=='undefined'&&Object.keys(dirty).length){error(updateText('Előbb mentsd vagy alkalmazd a módosításaidat.'));return;}
 try{
  const current=await api('/api/state');if(current.task?.running){error(updateText(updateErrors.update_task_running));return;}
  if(updateData.phase!=='ready'){updateInstallRequested=true;await requestUpdates('download');if(!updateData.busy)updateInstallRequested=false;return;}
  const ticket=updateData.ticket;updateData.phase='preparing';updateData.busy=true;paintUpdates();
  const result=await EveDesktop.installUpdate(ticket);
  if(!result?.started)throw Error(updateText(updateErrors.update_install_failed));
  updateData.phase='installing';updateData.busy=true;paintUpdates();if(await EveDesktop.shutdown()===false)throw Error(updateText(updateErrors.update_close_timeout));
 }catch(e){updateInstallRequested=false;updateData.busy=false;updateData.phase='ready';paintUpdates();error(updateText(updateErrors[e.message]||e.message));}
}
function scheduleNextUpdateCheck(){
 clearTimeout(updateDaily);if(!updateNativeMain()||!updateData||!updateData.automatic)return;
 const delay=Math.min(24*60*60*1000,Math.max(60000,(updateData.next_check||Date.now()/1000)*1000-Date.now()));
 updateDaily=setTimeout(()=>void requestUpdates('check',false),delay);
}
async function startUpdateChecks(){
 if(!updateNativeMain())return;
 await requestUpdates('check',false);
 scheduleNextUpdateCheck();
}
window.addEventListener('DOMContentLoaded',()=>void startUpdateChecks(),{once:true});
window.addEventListener('eve-language-change',()=>{if(updateData)paintUpdates();});
window.addEventListener('pagehide',()=>{clearTimeout(updatePoll);clearTimeout(updateDaily);});

document.addEventListener('keydown',event=>{if(document.body.classList.contains('update-installing')){event.preventDefault();event.stopImmediatePropagation();}},true);
