'use strict';
// Native Mac and Windows window previews. No ESI requests or game input forwarding.
let previewKeyFocused=false;
let previewMiningData=null,previewMiningBusy=false,previewMiningSaving=false;
let previewData=null,previewBusy=false,previewAction=false,previewTimer=null,previewDraft=null,previewRevision=0;
const previewKeys=[[0,'A'],[11,'B'],[8,'C'],[2,'D'],[14,'E'],[3,'F'],[5,'G'],[4,'H'],[34,'I'],[38,'J'],[40,'K'],[37,'L'],[46,'M'],[45,'N'],[31,'O'],[35,'P'],[12,'Q'],[15,'R'],[1,'S'],[17,'T'],[32,'U'],[9,'V'],[13,'W'],[7,'X'],[16,'Y'],[6,'Z'],[29,'0'],[18,'1'],[19,'2'],[20,'3'],[21,'4'],[23,'5'],[22,'6'],[26,'7'],[28,'8'],[25,'9'],[123,'←'],[124,'→'],[125,'↓'],[126,'↑'],[116,'Page Up'],[121,'Page Down'],[115,'Home'],[119,'End'],[122,'F1'],[120,'F2'],[99,'F3'],[118,'F4'],[96,'F5'],[97,'F6'],[98,'F7'],[100,'F8'],[101,'F9'],[109,'F10'],[103,'F11'],[111,'F12']];
const previewModifiers=[[4096,'Control'],[2048,'Option'],[256,'Command'],[512,'Shift']];
function previewSupported(){return EveDesktop.active&&['mac','windows'].includes(EveDesktop.platform);}
function previewSchedule(){clearTimeout(previewTimer);if(view==='preview')previewTimer=setTimeout(()=>void loadPreview(),2000);}
async function loadPreview(refresh=false){
 if(previewBusy||previewAction||!previewSupported())return;previewBusy=true;const revision=previewRevision;
 try{const data=await (refresh?EveDesktop.refreshPreview():EveDesktop.previewStatus());if(revision!==previewRevision)return;previewData=data;if(view==='preview')renderPreview($('#view-content'));}
 catch(e){if(view==='preview')error(e.message);}
 finally{previewBusy=false;previewSchedule();}
}
function previewReadDraft(){
 const form=$('#preview-settings');if(!form)return;
 const shortcut=kind=>({code:Number(form.elements[kind+'_code'].value),modifiers:Number(form.elements[kind+'_modifiers'].value)});
 previewDraft={enabled:form.elements.enabled.checked,only_eve:form.elements.only_eve.checked,fps:Number(form.elements.fps.value),next_key:shortcut('next'),previous_key:shortcut('previous'),slots:[...form.querySelectorAll('[data-preview-row]')].map(row=>({key:row.dataset.previewRow,label:row.querySelector('[data-label]').value,enabled:row.querySelector('[data-enabled]').checked,width:Number(row.querySelector('[data-width]').value)}))};
 dirty.preview=true;
}
const previewMacCodeMap=Object.fromEntries([
 ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map((letter,index)=>['Key'+letter,[0,11,8,2,14,3,5,4,34,38,40,37,46,45,31,35,12,15,1,17,32,9,13,7,16,6][index]]),
 ...'0123456789'.split('').map((digit,index)=>['Digit'+digit,[29,18,19,20,21,23,22,26,28,25][index]]),
 ...['ArrowLeft','ArrowRight','ArrowDown','ArrowUp','PageUp','PageDown','Home','End','Space','Enter','Backspace','Delete','Escape','Minus','Equal','BracketLeft','BracketRight','Backslash','Semicolon','Quote','Comma','Period','Slash','Backquote'].map((code,index)=>[code,[123,124,125,126,116,121,115,119,49,36,51,117,53,27,24,33,30,42,41,39,43,47,44,50][index]]),
 ...Array.from({length:12},(_,i)=>['F'+(i+1),[122,120,99,118,96,97,98,100,101,109,103,111][i]]),
 ...'0123456789'.split('').map((digit,index)=>['Numpad'+digit,[82,83,84,85,86,87,88,89,91,92][index]]),
 ['NumpadEnter',76],['NumpadAdd',69],['NumpadSubtract',78],['NumpadMultiply',67],['NumpadDivide',75],['NumpadDecimal',65],['NumpadEqual',81],['IntlBackslash',10]
]);
const previewExtraKeys=[[49,'Space'],[36,'Enter'],[51,'Backspace'],[117,'Delete'],[53,'Escape'],[48,'Tab'],[27,'-'],[24,'='],[33,'['],[30,']'],[42,'\\'],[41,';'],[39,"'"],[43,','],[47,'.'],[44,'/'],[50,'`'],[10,'§'],...[82,83,84,85,86,87,88,89,91,92].map((code,i)=>[code,'Numpad '+i]),[76,'Numpad Enter'],[69,'Numpad +'],[78,'Numpad -'],[67,'Numpad *'],[75,'Numpad /'],[65,'Numpad .'],[81,'Numpad =']];
const previewWindowsCodeMap=Object.fromEntries([
 ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map(letter=>['Key'+letter,letter.charCodeAt(0)]),
 ...'0123456789'.split('').map(digit=>['Digit'+digit,digit.charCodeAt(0)]),
 ...['ArrowLeft','ArrowRight','ArrowDown','ArrowUp','PageUp','PageDown','Home','End','Space','Enter','Backspace','Delete','Escape','Minus','Equal','BracketLeft','BracketRight','Backslash','Semicolon','Quote','Comma','Period','Slash','Backquote'].map((code,i)=>[code,[37,39,40,38,33,34,36,35,32,13,8,46,27,189,187,219,221,220,186,222,188,190,191,192][i]]),
 ...Array.from({length:12},(_,i)=>['F'+(i+1),112+i]),
 ...Array.from({length:10},(_,i)=>['Numpad'+i,96+i]),
 ['NumpadEnter',13],['NumpadAdd',107],['NumpadSubtract',109],['NumpadMultiply',106],['NumpadDivide',111],['NumpadDecimal',110],['IntlBackslash',226]
]);
function previewCodeMap(){return EveDesktop.platform==='windows'?previewWindowsCodeMap:previewMacCodeMap;}
const previewWindowsNames={ArrowLeft:'←',ArrowRight:'→',ArrowUp:'↑',ArrowDown:'↓',PageUp:'Page Up',PageDown:'Page Down',Space:'Space',Minus:'-',Equal:'=',BracketLeft:'[',BracketRight:']',Backslash:'\\',Semicolon:';',Quote:"'",Comma:',',Period:'.',Slash:'/',Backquote:'`',IntlBackslash:'§'};
function previewKeyLabel(key){const windows=EveDesktop.platform==='windows',domCode=Object.keys(previewWindowsCodeMap).find(code=>previewWindowsCodeMap[code]===key.code);const label=windows?(previewWindowsNames[domCode]||domCode?.replace(/^Key|^Digit/,'').replace(/^Numpad/,'Numpad ')||String(key.code)):([...previewKeys,...previewExtraKeys].find(([code])=>code===key.code)?.[1]||String(key.code));return [...previewModifiers.filter(([mask])=>key.modifiers&mask).map(([,name])=>windows?({Option:'Alt',Command:'Windows'}[name]||name):name),label].join(' + ');}
function previewShortcut(kind,key){return `<fieldset class="preview-shortcut"><legend>${kind==='next'?'Következő EVE-ablak':'Előző EVE-ablak'}</legend><input type="text" readonly name="${kind}_shortcut" class="preview-key-input" aria-label="${kind==='next'?'Következő billentyű':'Előző billentyű'}" value="${esc(previewKeyLabel(key))}"><input type="hidden" name="${kind}_code" value="${key.code}"><input type="hidden" name="${kind}_modifiers" value="${key.modifiers}"></fieldset>`;}
function previewBindShortcut(form,kind){
 const input=form.elements[kind+'_shortcut'];
 input.onfocus=()=>{previewKeyFocused=true;void EveDesktop.capturePreviewKey(true).catch(e=>error(e.message));};
 input.onblur=()=>{previewKeyFocused=false;void EveDesktop.capturePreviewKey(false).catch(e=>error(e.message));};
 input.onkeydown=event=>{
  if(event.key==='Tab')return;
  event.preventDefault();event.stopPropagation();if(event.repeat||['Control','Alt','Meta','Shift','Fn','CapsLock'].includes(event.key))return;
  const code=previewCodeMap()[event.code];if(code===undefined)return error('Ez a billentyű nem támogatott. Válassz másikat.');
  const modifiers=(event.ctrlKey?4096:0)|(event.altKey?2048:0)|(event.metaKey?256:0)|(event.shiftKey?512:0);
  form.elements[kind+'_code'].value=code;form.elements[kind+'_modifiers'].value=modifiers;input.value=previewKeyLabel({code,modifiers});previewReadDraft();error('');
 };
}
window.addEventListener('blur',()=>{if(previewKeyFocused)void EveDesktop.capturePreviewKey(false).catch(()=>{});});
window.addEventListener('focus',()=>{if(previewKeyFocused&&document.activeElement?.classList.contains('preview-key-input'))void EveDesktop.capturePreviewKey(true).catch(()=>{});});
function renderPreview(content){
 setHead('KLIENSABLAKOK','eve-preview','Élő EVE-előnézetek, kattintásos ablakváltás és mentett elrendezés.');
 if(!previewSupported()){content.innerHTML=empty('Az eve-preview a Mac vagy Windows asztali alkalmazásban használható.');return;}
 if(!previewData){content.innerHTML=empty('EVE-ablakok betöltése…');void loadPreview();return;}
 const data=previewData,windows=EveDesktop.platform==='windows';
 if(!data.supported){content.innerHTML=empty('Az eve-preview macOS 12.3 vagy újabb rendszert igényel.');return;}
 if(!$('#preview-settings')){
  const draft=previewDraft||data;
  content.innerHTML=`<section class="panel"><header class="panel-head"><h2>Hozzáférés és állapot</h2><button type="button" id="preview-refresh" class="button compact">Ablaklista frissítése</button></header>${windows?'<p class=\"footnote preview-note\">Windows: az élő képet a Desktop Window Manager adja; külön macOS-engedély nem szükséges. Az EVE és az EVE Workshop azonos jogosultsági szinten fusson.</p>':`<div class="panel-body preview-permissions"><div><strong>Képernyőfelvétel</strong><span id="preview-screen"></span><button type="button" class="button compact" data-preview-permission="screen">Képernyő-hozzáférés engedélyezése</button></div><div><strong>Akadálymentesítés</strong><span id="preview-accessibility"></span><button type="button" class="button compact" data-preview-permission="accessibility">Ablakváltás engedélyezése</button></div></div><p class="footnote preview-note">macOS: System Settings → Privacy & Security → Screen & System Audio Recording / Device Control and Data Access (Accessibility). Engedélyezd az EVE Műhely alkalmazást; a képernyőengedély módosítása után újraindításra is szükség lehet.</p>`}<div id="preview-status" class="preview-note" role="status"></div></section>
  <form id="preview-settings" class="panel"><header class="panel-head"><h2>Előnézet és ablakváltás</h2><div class="actions"><button type="button" id="preview-layout" class="button compact"></button><button type="submit" class="button primary compact">Beállítások mentése</button></div></header><div class="panel-body"><div class="preview-options"><label><input name="enabled" type="checkbox" ${draft.enabled?'checked':''}>Előnézetek bekapcsolása</label><label><input name="only_eve" type="checkbox" ${draft.only_eve?'checked':''}>Csak az EVE előtt jelenjen meg</label><label ${windows?'hidden':''}>Képfrissítés / másodperc<input name="fps" type="number" min="1" max="10" step="1" required value="${draft.fps}"></label></div><div class="preview-shortcuts">${previewShortcut('next',draft.next_key)}${previewShortcut('previous',draft.previous_key)}</div><p class="footnote"><span>Felismert gyorsbillentyűk:</span> <strong id="preview-key-count">0</strong></p><p class="footnote">A billentyűk a bekapcsolt, elérhető kliensek között váltanak a lista sorrendjében. Az ütköző gyorsbillentyűt a rendszer elutasítja.</p><p class="footnote">Kattints a billentyűmezőbe, és nyomd le a kívánt billentyűt vagy kombinációt, például K vagy Control + K. Tabbal léphetsz ki a mezőből. A módosító nélküli és a csak Shiftet használó billentyű csak az EVE előtt aktív; ott váltásra szolgál, a chatbe nem ír betűt.</p><div class="preview-table-wrap"><table class="preview-table"><thead><tr><th>EVE-ablak / saját név</th><th>Állapot</th><th>Szélesség (px)</th><th>Bekapcsolva</th><th>Sorrend</th><th>Művelet</th></tr></thead><tbody id="preview-windows"></tbody></table></div><p id="preview-no-windows" class="footnote" hidden>Nincs elérhető EVE-ablak. Indítsd el a klienst, add meg a képernyőengedélyt, majd frissítsd az ablaklistát.</p><p class="footnote">Elrendezés szerkesztésekor húzd a képeket a kívánt monitorra; a jobb alsó sarokkal méretezheted őket. A helyük és méretük automatikusan mentődik. Normál módban kattintásra az EVE-ablak kerül előre.</p><p class="footnote">A kitakart ablak követhető; a minimalizált kliens képe szünetelhet. Az előnézet nem rögzít videót és nem küld játékbeli műveleteket. A kliensek az ablakcím alapján azonosíthatók; azonos címeknél újraindítás után új bejegyzés jelenhet meg.</p></div></form>`;
  const form=$('#preview-settings');for(const kind of ['next','previous'])previewBindShortcut(form,kind);form.oninput=previewReadDraft;form.onchange=previewReadDraft;
  form.onsubmit=e=>{e.preventDefault();if(!form.reportValidity())return;previewReadDraft();if(previewDraft.next_key.code===previewDraft.previous_key.code&&previewDraft.next_key.modifiers===previewDraft.previous_key.modifiers)return error('Az előző és következő gyorsbillentyű legyen eltérő.');void previewCommand(()=>EveDesktop.configurePreview(previewDraft),true);};
  $('#preview-refresh').onclick=()=>void loadPreview(true);
  content.querySelectorAll('[data-preview-permission]').forEach(button=>button.onclick=()=>void previewCommand(()=>EveDesktop.previewPermission(button.dataset.previewPermission)));
  $('#preview-layout').onclick=()=>{if(!previewData.enabled)return error('Előbb kapcsold be és mentsd az előnézeteket.');void previewCommand(()=>EveDesktop.configurePreview({editing:!previewData.editing}));};
 }
 updatePreview();renderPreviewMining();void pollPreviewMining();previewSchedule();
}
function updatePreview(){
 if(!$('#preview-settings')||!previewData)return;const data=previewData;
 if(previewDraft){for(const row of data.windows)if(!previewDraft.slots.some(r=>r.key===row.key))previewDraft.slots.push({key:row.key,label:row.label,enabled:row.enabled,width:row.width});}
 const rows=previewDraft?.slots||data.windows;
 if($('#preview-screen'))$('#preview-screen').textContent=data.screen_permission?'Engedélyezve':'Engedély szükséges';if($('#preview-accessibility'))$('#preview-accessibility').textContent=data.accessibility_permission?'Engedélyezve':'Engedély szükséges';
 const errors={hotkey_unavailable:'A gyorsbillentyűk fogadása nem indult el. Ellenőrizd az ablakváltási engedélyt.',hotkey_conflict:'A gyorsbillentyű már foglalt. Válassz másikat.',capture_failed:'Az EVE-ablak képe nem olvasható. Ellenőrizd a képernyőengedélyt.',activate_failed:'Az ablak nem váltható. Ellenőrizd az akadálymentesítési engedélyt.'};
 if(EveDesktop.platform==='windows')Object.assign(errors,{hotkey_unavailable:'A Windows gyorsbillentyű-figyelése nem indult el. Kapcsold ki, majd be az előnézeteket.',capture_failed:'A Windows nem tudja megjeleníteni az EVE-ablak élő képét.',activate_failed:'A Windows nem tudta előrehozni az EVE-ablakot. Ellenőrizd, hogy azonos jogosultsággal futnak-e az alkalmazások.'});
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
 try{previewData=await command();if(saved){void EveDesktop.capturePreviewKey(false).catch(()=>{});delete dirty.preview;previewDraft=null;$('#preview-settings')?.remove();toast('Előnézet-beállítások mentve.');}error('');if(view==='preview')renderPreview($('#view-content'));}
 catch(e){error(e.message);}finally{previewAction=false;if(save?.isConnected)save.disabled=false;previewSchedule();}
}

const previewMiningNames={cargo_full:'Megtelt raktér',crystal_broken:'Elkopott kristály',rock_depleted:'Elfogyott kő',module_stopped:'Modul nem fut'};
async function pollPreviewMining(){
 if(!previewSupported()||previewMiningBusy||previewMiningSaving)return;previewMiningBusy=true;
 try{
  const native=await EveDesktop.previewStatus();if(!native.enabled&&view!=='preview')return;
  previewMiningData=await api('/api/preview/mining');if(!globalThis.document)return;await EveDesktop.syncPreviewMining(native.enabled?previewMiningData:{enabled:false,characters:[]});
  if(globalThis.document&&view==='preview')renderPreviewMining();
 }catch(e){if(globalThis.document&&view==='preview')error(e.message);}finally{previewMiningBusy=false;}
}
function renderPreviewMining(){
 if(!previewMiningData||!$('#preview-settings'))return;
 let panel=$('#preview-mining');if(!panel){panel=document.createElement('section');panel.id='preview-mining';panel.className='panel';$('#preview-settings').after(panel);}
 // Polling must not replace a half-entered folder path.
 if(!panel.querySelector('form')){
  panel.innerHTML=`<header class="panel-head"><h2>Bányászati és sebzésjelzések</h2></header><form id="preview-mining-settings" class="panel-body preview-mining-config"><label><input type="checkbox" name="enabled" ${previewMiningData.enabled?'checked':''}>Naplófigyelés</label><label>Gamelogs mappa<input type="text" name="folder" value="${esc(previewMiningData.folder)}" required></label><button class="button compact" type="submit">Beállítások mentése</button></form><p class="footnote preview-note">Csak a figyelés indítása utáni új eseményeket jelöli. A modul neve az utolsó említésből származik; az egyes lézerek működése és a raktér százaléka nem olvasható ki biztosan. A raktér-, kristály- és kőhibák nyugtázásig vagy új játéknapló-munkamenetig maradnak meg; másik lézer termelése nem törli őket.</p><p class="footnote preview-note">Beérkező sebzésnél a karakter neve 10 másodpercig pirosan villog; újabb találat újraindítja az időt. Saját támadás és mellélövés nem vált ki villogást.</p><p class="footnote preview-note">Az előnézet kristályikonjára kattintva jelzed a kristálycserét; ekkor szünetjel marad. A szünetjel a következő sikeres bányászati naplóeseménynél automatikusan eltűnik; kattintással is törölhető. Ez karakterenként jelzi a bányászat folytatását, nem az egyes lézerek állapotát.</p><div id="preview-mining-status" class="preview-note" role="status"></div><div id="preview-mining-rows" class="panel-body"></div>`;
  panel.querySelector('form').onsubmit=async e=>{e.preventDefault();if(previewMiningSaving)return;previewMiningSaving=true;const form=e.currentTarget;
   try{previewMiningData=await api('/api/preview/mining/configure',{enabled:form.elements.enabled.checked,folder:form.elements.folder.value});await EveDesktop.syncPreviewMining(previewMiningData);error('');renderPreviewMining();toast('Bányászati jelzések beállításai mentve.');}catch(e){error(e.message);}finally{previewMiningSaving=false;}
  };
 }
 const data=previewMiningData;$('#preview-mining-status').textContent=data.error==='folder_unavailable'?'A Gamelogs mappa nem érhető el.':data.file_errors?'Néhány játéknapló nem olvasható.':data.enabled?'Új játéknapló-események figyelése aktív.':'Naplófigyelés kikapcsolva.';
 $('#preview-mining-rows').innerHTML=`<div class="preview-mining-legend"><span>▣ Megtelt raktér</span><span>◇ Elkopott kristály</span><span>⬡ Elfogyott kő</span><span>Ⅱ Modul nem fut</span></div>`+data.characters.map((row,index)=>`<div class="preview-mining-row"><strong data-i18n-skip>${esc(row.name)}</strong><span data-i18n-skip>${esc(row.last_module||'–')}</span><span>${row.alerts.map(a=>`<span class="tag warn" title="${esc(a.crystal||a.module||'')}"><span>${previewMiningNames[a.kind]}</span> · ${date(a.at)}</span>`).join(' ')||'<span>Nincs új jelzés</span>'}</span>${row.alerts.length?`<button class="button compact" data-mining-ack="${index}">Tudomásul vettem</button>`:''}</div>`).join('');
 panel.querySelectorAll('[data-mining-ack]').forEach(button=>button.onclick=async()=>{const row=data.characters[Number(button.dataset.miningAck)];try{previewMiningData=await api('/api/preview/mining/acknowledge',{name:row.name,ids:row.alerts.map(a=>a.id)});await EveDesktop.syncPreviewMining(previewMiningData);renderPreviewMining();}catch(e){error(e.message);}});
 EveI18n.translate(panel);
}

async function previewMiningAction(payload){
 if(!previewSupported()||previewMiningSaving||!payload||!['crystal_broken','module_stopped'].includes(payload.kind))return;previewMiningSaving=true;
 try{
  const replace=payload.kind==='crystal_broken';
  previewMiningData=await api(replace?'/api/preview/mining/replace-crystal':'/api/preview/mining/acknowledge',replace?{name:payload.name,id:payload.id}:{name:payload.name,ids:[payload.id]});
  await EveDesktop.syncPreviewMining(previewMiningData);if(view==='preview')renderPreviewMining();
 }catch(e){error(e.message);}finally{previewMiningSaving=false;}
}
