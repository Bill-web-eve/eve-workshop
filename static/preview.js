'use strict';
// Mac-only native window previews. No ESI requests or game input forwarding.
let previewData=null,previewBusy=false,previewAction=false,previewTimer=null,previewDraft=null,previewRevision=0;
const previewKeys=[[0,'A'],[11,'B'],[8,'C'],[2,'D'],[14,'E'],[3,'F'],[5,'G'],[4,'H'],[34,'I'],[38,'J'],[40,'K'],[37,'L'],[46,'M'],[45,'N'],[31,'O'],[35,'P'],[12,'Q'],[15,'R'],[1,'S'],[17,'T'],[32,'U'],[9,'V'],[13,'W'],[7,'X'],[16,'Y'],[6,'Z'],[29,'0'],[18,'1'],[19,'2'],[20,'3'],[21,'4'],[23,'5'],[22,'6'],[26,'7'],[28,'8'],[25,'9'],[123,'←'],[124,'→'],[125,'↓'],[126,'↑'],[116,'Page Up'],[121,'Page Down'],[115,'Home'],[119,'End'],[122,'F1'],[120,'F2'],[99,'F3'],[118,'F4'],[96,'F5'],[97,'F6'],[98,'F7'],[100,'F8'],[101,'F9'],[109,'F10'],[103,'F11'],[111,'F12']];
const previewModifiers=[[4096,'Control'],[2048,'Option'],[256,'Command'],[512,'Shift']];
function previewSupported(){return EveDesktop.active&&EveDesktop.platform==='mac';}
function previewSchedule(){clearTimeout(previewTimer);if(view==='preview')previewTimer=setTimeout(()=>void loadPreview(),2000);}
async function loadPreview(refresh=false){
 if(previewBusy||previewAction||!previewSupported())return;previewBusy=true;const revision=previewRevision;
 try{const data=await (refresh?EveDesktop.refreshPreview():EveDesktop.previewStatus());if(revision!==previewRevision)return;previewData=data;if(view==='preview')renderPreview($('#view-content'));}
 catch(e){if(view==='preview')error(e.message);}
 finally{previewBusy=false;previewSchedule();}
}
function previewReadDraft(){
 const form=$('#preview-settings');if(!form)return;
 const shortcut=kind=>({code:Number(form.elements[kind+'_code'].value),modifiers:previewModifiers.reduce((n,[mask])=>n|(form.elements[kind+'_'+mask].checked?mask:0),0)});
 previewDraft={enabled:form.elements.enabled.checked,only_eve:form.elements.only_eve.checked,fps:Number(form.elements.fps.value),next_key:shortcut('next'),previous_key:shortcut('previous'),slots:[...form.querySelectorAll('[data-preview-row]')].map(row=>({key:row.dataset.previewRow,label:row.querySelector('[data-label]').value,enabled:row.querySelector('[data-enabled]').checked,width:Number(row.querySelector('[data-width]').value)}))};
 dirty.preview=true;
}
function previewShortcut(kind,key){return `<fieldset class="preview-shortcut"><legend>${kind==='next'?'Következő EVE-ablak':'Előző EVE-ablak'}</legend><select name="${kind}_code" aria-label="${kind==='next'?'Következő billentyű':'Előző billentyű'}">${[...previewKeys,...(previewKeys.some(([code])=>code===key.code)?[]:[[key.code,String(key.code)]])].map(([code,label])=>`<option data-i18n-skip value="${code}" ${code===key.code?'selected':''}>${label}</option>`).join('')}</select>${previewModifiers.map(([mask,label])=>`<label><input type="checkbox" name="${kind}_${mask}" ${key.modifiers&mask?'checked':''}>${label}</label>`).join('')}</fieldset>`;}
function renderPreview(content){
 setHead('KLIENSABLAKOK','eve-preview','Élő EVE-előnézetek, kattintásos ablakváltás és mentett elrendezés.');
 if(!previewSupported()){content.innerHTML=empty('Az eve-preview első változata a Mac asztali alkalmazásban használható.','A Windows-támogatás későbbi változatban készül el.');return;}
 if(!previewData){content.innerHTML=empty('EVE-ablakok betöltése…');void loadPreview();return;}
 const data=previewData;
 if(!data.supported){content.innerHTML=empty('Az eve-preview macOS 12.3 vagy újabb rendszert igényel.');return;}
 if(!$('#preview-settings')){
  const draft=previewDraft||data;
  content.innerHTML=`<section class="panel"><header class="panel-head"><h2>Hozzáférés és állapot</h2><button type="button" id="preview-refresh" class="button compact">Ablaklista frissítése</button></header><div class="panel-body preview-permissions"><div><strong>Képernyőfelvétel</strong><span id="preview-screen"></span><button type="button" class="button compact" data-preview-permission="screen">Képernyő-hozzáférés engedélyezése</button></div><div><strong>Akadálymentesítés</strong><span id="preview-accessibility"></span><button type="button" class="button compact" data-preview-permission="accessibility">Ablakváltás engedélyezése</button></div></div><p class="footnote preview-note">macOS: System Settings → Privacy & Security → Screen & System Audio Recording / Device Control and Data Access (Accessibility). Engedélyezd az EVE Műhely alkalmazást; a képernyőengedély módosítása után újraindításra is szükség lehet.</p><div id="preview-status" class="preview-note" role="status"></div></section>
  <form id="preview-settings" class="panel"><header class="panel-head"><h2>Előnézet és ablakváltás</h2><div class="actions"><button type="button" id="preview-layout" class="button compact"></button><button type="submit" class="button primary compact">Beállítások mentése</button></div></header><div class="panel-body"><div class="preview-options"><label><input name="enabled" type="checkbox" ${draft.enabled?'checked':''}>Előnézetek bekapcsolása</label><label><input name="only_eve" type="checkbox" ${draft.only_eve?'checked':''}>Csak az EVE előtt jelenjen meg</label><label>Képfrissítés / másodperc<input name="fps" type="number" min="1" max="10" step="1" required value="${draft.fps}"></label></div><div class="preview-shortcuts">${previewShortcut('next',draft.next_key)}${previewShortcut('previous',draft.previous_key)}</div><p class="footnote"><span>Felismert gyorsbillentyűk:</span> <strong id="preview-key-count">0</strong></p><p class="footnote">A billentyűk a bekapcsolt, elérhető kliensek között váltanak a lista sorrendjében. Az ütköző gyorsbillentyűt a rendszer elutasítja.</p><p class="footnote">Önálló billentyűhöz válassz például K-t, és kapcsold ki mind a négy módosítót. A módosító nélküli és a csak Shiftet használó billentyű csak az EVE előtt aktív; ott váltásra szolgál, a chatbe nem ír betűt.</p><div class="preview-table-wrap"><table class="preview-table"><thead><tr><th>EVE-ablak / saját név</th><th>Állapot</th><th>Szélesség (px)</th><th>Bekapcsolva</th><th>Sorrend</th><th>Művelet</th></tr></thead><tbody id="preview-windows"></tbody></table></div><p id="preview-no-windows" class="footnote" hidden>Nincs elérhető EVE-ablak. Indítsd el a klienst, add meg a képernyőengedélyt, majd frissítsd az ablaklistát.</p><p class="footnote">Elrendezés szerkesztésekor húzd a képeket a kívánt monitorra; a jobb alsó sarokkal méretezheted őket. A helyük és méretük automatikusan mentődik. Normál módban kattintásra az EVE-ablak kerül előre.</p><p class="footnote">A kitakart ablak követhető; a minimalizált kliens képe szünetelhet. Az előnézet nem rögzít videót és nem küld játékbeli műveleteket. A kliensek az ablakcím alapján azonosíthatók; azonos címeknél újraindítás után új bejegyzés jelenhet meg.</p></div></form>`;
  const form=$('#preview-settings');form.oninput=previewReadDraft;form.onchange=previewReadDraft;
  form.onsubmit=e=>{e.preventDefault();if(!form.reportValidity())return;previewReadDraft();if(previewDraft.next_key.code===previewDraft.previous_key.code&&previewDraft.next_key.modifiers===previewDraft.previous_key.modifiers)return error('Az előző és következő gyorsbillentyű legyen eltérő.');void previewCommand(()=>EveDesktop.configurePreview(previewDraft),true);};
  $('#preview-refresh').onclick=()=>void loadPreview(true);
  content.querySelectorAll('[data-preview-permission]').forEach(button=>button.onclick=()=>void previewCommand(()=>EveDesktop.previewPermission(button.dataset.previewPermission)));
  $('#preview-layout').onclick=()=>{if(!previewData.enabled)return error('Előbb kapcsold be és mentsd az előnézeteket.');void previewCommand(()=>EveDesktop.configurePreview({editing:!previewData.editing}));};
 }
 updatePreview();previewSchedule();
}
function updatePreview(){
 if(!$('#preview-settings')||!previewData)return;const data=previewData;
 if(previewDraft){for(const row of data.windows)if(!previewDraft.slots.some(r=>r.key===row.key))previewDraft.slots.push({key:row.key,label:row.label,enabled:row.enabled,width:row.width});}
 const rows=previewDraft?.slots||data.windows;
 $('#preview-screen').textContent=data.screen_permission?'Engedélyezve':'Engedély szükséges';$('#preview-accessibility').textContent=data.accessibility_permission?'Engedélyezve':'Engedély szükséges';
 const errors={hotkey_unavailable:'A gyorsbillentyűk fogadása nem indult el. Ellenőrizd az ablakváltási engedélyt.',hotkey_conflict:'A gyorsbillentyű már foglalt. Válassz másikat.',capture_failed:'Az EVE-ablak képe nem olvasható. Ellenőrizd a képernyőengedélyt.',activate_failed:'Az ablak nem váltható. Ellenőrizd az akadálymentesítési engedélyt.'};
 $('#preview-status').textContent=errors[data.error]||(data.editing?'Elrendezés szerkesztése: mozgatás és átméretezés engedélyezve.':data.enabled?(data.hotkeys_active?'Előnézet bekapcsolva; gyorsbillentyűk aktívak.':'Előnézet bekapcsolva; az ablakváltáshoz engedély szükséges.'):'Előnézet kikapcsolva.');
 $('#preview-key-count').textContent=fmt(data.shortcut_count||0);
 $('#preview-layout').textContent=data.editing?'Elrendezés kész':'Elrendezés szerkesztése';
 // Keep focused/unsaved inputs intact during native status polling.
 const body=$('#preview-windows'),keys=rows.map(row=>row.key).join('|');
 if(body.dataset.keys!==keys){
  body.dataset.keys=keys;body.innerHTML=rows.map(row=>{const live=data.windows.find(w=>w.key===row.key)||row;return `<tr data-preview-row="${esc(row.key)}"><td><strong data-i18n-skip>${esc(live.title)}</strong><input data-label aria-label="Saját ablaknév" maxlength="80" value="${esc(row.label||'')}" placeholder="Saját ablaknév"></td><td data-preview-state></td><td><input data-width aria-label="Előnézet szélessége" type="number" min="160" max="900" step="1" required value="${row.width}"></td><td><input data-enabled aria-label="Előnézet bekapcsolva" type="checkbox" ${row.enabled?'checked':''}></td><td><button type="button" class="button compact" data-up aria-label="Feljebb">↑</button> <button type="button" class="button compact" data-down aria-label="Lejjebb">↓</button></td><td><button type="button" class="button compact" data-activate>Ablak kiválasztása</button></td></tr>`;}).join('');
  body.querySelectorAll('[data-preview-row]').forEach(row=>{for(const [selector,delta] of [['[data-up]',-1],['[data-down]',1]])row.querySelector(selector).onclick=()=>{const sibling=delta<0?row.previousElementSibling:row.nextElementSibling;if(!sibling)return;if(delta<0)body.insertBefore(row,sibling);else body.insertBefore(sibling,row);previewReadDraft();body.dataset.keys=previewDraft.slots.map(r=>r.key).join('|');};row.querySelector('[data-activate]').onclick=()=>void previewCommand(()=>EveDesktop.activatePreview(row.dataset.previewRow));});
 }
 for(const row of body.children){const live=data.windows.find(w=>w.key===row.dataset.previewRow);if(!dirty.preview&&live){row.querySelector('[data-label]').value=live.label;row.querySelector('[data-width]').value=live.width;row.querySelector('[data-enabled]').checked=live.enabled;}row.querySelector('[data-preview-state]').textContent=live?.online?(live.active?'Aktív EVE-ablak':live.capturing?(live.has_frame?'Élő előnézet':'Előnézet indítása…'):'Elérhető'):'Offline';row.querySelector('[data-activate]').disabled=!live?.online||!data.accessibility_permission;row.querySelector('[data-up]').disabled=!row.previousElementSibling;row.querySelector('[data-down]').disabled=!row.nextElementSibling;}
 $('#preview-no-windows').hidden=data.windows.some(w=>w.online);EveI18n.translate($('#view-content'));
}
async function previewCommand(command,saved=false){
 if(previewAction)return;previewAction=true;previewRevision++;
 const save=$('#preview-settings [type=submit]');if(save)save.disabled=true;
 try{previewData=await command();if(saved){delete dirty.preview;previewDraft=null;$('#preview-settings')?.remove();toast('Előnézet-beállítások mentve.');}error('');if(view==='preview')renderPreview($('#view-content'));}
 catch(e){error(e.message);}finally{previewAction=false;if(save?.isConnected)save.disabled=false;previewSchedule();}
}
