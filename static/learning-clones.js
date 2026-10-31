'use strict';
let learningCloneTimer=null,learningCloneAlertTimer=null,learningCloneBusy=false,learningCloneClaimBusy=false;
function learningCloneSummary(a){
 const name=a.best_clone_name||EveI18n.t('Klón #{0}').replace('{0}',a.best_clone_id);
 return a.skill_name+' · '+name+' · '+a.active_bonus+' → '+a.best_bonus;
}
function learningCloneSettingsPanel(data){
 if(!data)return '';
 const status=data.status||{},gate=!data.enabled?'Kikapcsolva':status.running?'Tanulóklónok ellenőrzése…':data.gate==='online'?'Van online karakter; nincs tanulóklón-riasztás.':data.gate==='offline'&&data.online_fresh?'Minden hozzáadott karakter offline.':'Nem igazolt, hogy minden karakter offline.';
 const onlineLabels={access:'Onlineállapot-olvasási engedély szükséges.',missing:'Onlineállapot-adat hiányzik.',stale:'Korábbi onlineállapot; frissítés szükséges.',online:'Online',offline:'Offline'};
 const blockers=data.online_blockers||[];
 const gateNotice=data.enabled&&data.gate!=='online'&&blockers.length?'<div class="banner warn" data-learning-blockers><strong>Az értesítés várakozik: nem igazolt, hogy minden karakter offline.</strong><ul>'+blockers.map(c=>'<li>'+verbatim(c.name)+' · <span>'+esc(onlineLabels[c.reason])+'</span></li>').join('')+'</ul></div>':'';
 const nextCheck=data.next_check>Date.now()/1000?'<p class="footnote"><span>Következő automatikus ellenőrzés:</span> '+EveI18n.date(data.next_check*1000,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})+'</p>':'';
 const labels={better:'Gyorsabb saját klón érhető el',optimal:'Az aktív klón azonos vagy jobb',not_training:'Jelenleg nem tanul',unknown:'Hiányos vagy korábbi adat',waiting:'Várakozás az ellenőrzésre'};
 return panel('Tanulóklónok offline állapotban','',`<div class="panel-body"><p>Csak akkor jelez, ha minden hozzáadott karakter igazoltan offline, és az aktuálisan tanult skillhez valamelyik saját jump clone gyorsabb az aktív klónnál. Azonos sebességnél és aktív tanulás nélkül nincs riasztás.</p>${gateNotice}<div class="section-actions"><button class="button compact" id="learning-clone-refresh" ${status.running||!data.enabled||!data.characters.length?'disabled':''}>Tanulóklónok ellenőrzése most</button><span role="status" data-learning-status>${esc(gate)}${status.running?' · '+fmt(status.done||0)+' / '+fmt(status.total||0)+(status.current?' · '+esc(status.current):''):''}</span></div>${data.online_characters?.length?'<p data-i18n-skip>'+esc(data.online_characters.join(', '))+'</p>':''}${nextCheck}${table(['Karakter','Online állapot','Tanult skill','Implantbónusz · aktív → legjobb','Jobb saját klón','Klón helye','Állapot','Hozzáférés'],data.characters.map(c=>`<tr><td>${verbatim(c.name)}</td><td>${esc(onlineLabels[c.online_status]||'–')}</td><td>${verbatim(c.skill_name||'–')}</td><td class="num">${c.active?esc(c.active.score+' → '+(c.best?.score??c.active.score)):'–'}</td><td>${c.best?verbatim(c.best.name||EveI18n.t('Klón #{0}').replace('{0}',c.best.jump_clone_id)):'–'}</td><td>${c.best&&typeof EveLocations!=='undefined'?EveLocations.markup(c.best.location_id,null,null):'–'}</td><td>${esc(!c.authorized?'Tanulóklón-olvasási engedély szükséges.':c.error||labels[c.status]||labels.waiting)}${c.authorized&&c.fresh===false?'<div class="batch-note">Korábbi klónadat; frissítés szükséges.</div>':''}</td><td><button type="button" class="text-button" data-learning-authorize="${c.id}">Tanulóklónok engedélyezése</button></td></tr>`),'learning-clone-settings')}<p class="footnote">A súlyozott implantbónusz: elsődleges attribútum + másodlagos / 2. A klónok azonos karakterhez tartoznak, ezért ez határozza meg a sebességi sorrendet. Az online állapotot és a klónadatokat automatikusan legfeljebb 15 percenként ellenőrizzük; az EVE gyorsítótárát kézi ellenőrzéskor is megtartjuk. Kijelentkezés előtti implantadatból nem riasztunk. A kapcsoló a fenti értesítéstípusok között található.</p><details><summary>Szükséges jogosultságok</summary><code>${data.scopes.map(esc).join('\n')}</code><p>A klónok olvasásához új ESI-engedély szükséges. Az EVE Developer alkalmazásban is engedélyezd a felsorolt scope-okat.</p></details></div>`);
}
function bindLearningClones(){
 const button=$('#learning-clone-refresh');if(!button)return;
 button.onclick=()=>void refreshLearningClones(true);
 $$('[data-learning-authorize]').forEach(b=>b.onclick=async()=>{try{const data=await api('/api/auth/start',{character_id:Number(b.dataset.learningAuthorize),feature:'learning_clones'});sessionStorage.setItem('eve-muhely-auth-return','settings:notifications');await openEveAuthorization(data);}catch(e){error(e.message);}});
 clearTimeout(learningCloneTimer);
 if(notificationData?.learning_clones?.status.running)learningCloneTimer=setTimeout(()=>void refreshLearningClones(),1000);
}
async function refreshLearningClones(manual=false){
 if(learningCloneBusy)return;learningCloneBusy=true;
 try{
  const data=manual?await api('/api/learning-clones/refresh',{}):await api('/api/learning-clones');
  if(notificationData)notificationData.learning_clones=data;
  if(view==='settings'&&settingsTab==='notifications'){
   if(!Object.keys(dirty).length)render();
   else{const status=$('[data-learning-status]');if(status)status.textContent=EveI18n.t(data.status.phase||'Várakozás az ellenőrzésre')+' · '+(data.status.done||0)+' / '+(data.status.total||0);const button=$('#learning-clone-refresh');if(button)button.disabled=!!data.status.running;clearTimeout(learningCloneTimer);if(data.status.running)learningCloneTimer=setTimeout(()=>void refreshLearningClones(),1000);}
  }
 }catch(e){error(e.message);}finally{learningCloneBusy=false;}
}
async function pollLearningCloneAlerts(){
 const p=notificationData?.preferences;
 if(learningCloneClaimBusy||!EveDesktop.active||!p?.os_enabled||p.categories.learning_clones!==true)return;
 learningCloneClaimBusy=true;
 try{const permission=await EveDesktop.notificationStatus();if(permission.status==='authorized')await deliverNotifications('/api/learning-clones/claim');}catch{}finally{learningCloneClaimBusy=false;}
}
function scheduleLearningCloneAlerts(){
 clearInterval(learningCloneAlertTimer);learningCloneAlertTimer=setInterval(()=>void pollLearningCloneAlerts(),30000);
}
