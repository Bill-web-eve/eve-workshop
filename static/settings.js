'use strict';
let settingsTab='appearance',settingsAccessData=null,settingsAccessRequest=null;
const settingsSections={market:'Marketek és értékesítés',intel:'Intelbeállítások',notifications:'Értesítések',appearance:'Megjelenés és nyelv',structures:'Struktúrák és bónuszok',connection:'EVE-kapcsolat',access:'Adathozzáférések',moons:'Holdak számítási beállításai',calendar:'Naptárszinkron',accounts:'Accountok és tanulás'};
function settingsShortcut(message,tab='access'){
  return `<div class="banner"><span>${esc(message)}</span> <button class="text-button" data-open-settings="${tab}">Beállítások megnyitása</button></div>`;
}
function setSettingsMenu(open){
  $('#settings-submenu').hidden=!open;
  $('[data-view="settings"]').setAttribute('aria-expanded',String(open));
}
function syncSettingsNavigation(){
  $$('[data-settings-nav]').forEach(button=>{
    const active=view==='settings'&&settingsTab===button.dataset.settingsNav;
    button.classList.toggle('active',active);
    if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
  });
}
function openSettingsTab(tab){
  if(!Object.prototype.hasOwnProperty.call(settingsSections,tab))return false;
  if(view==='settings'&&settingsTab===tab){setSettingsMenu(true);return true;}
  if(view!=='settings'){
    const previous=settingsTab;settingsTab=tab;
    if(!navigate('settings')){settingsTab=previous;return false;}
    return true;
  }
  if(Object.keys(dirty).length&&!confirmUI('Vannak még nem alkalmazott módosítások. Elhagyod ezt az oldalt?'))return false;
  if(settingsTab==='accounts')accountDraft=null;
  dirty={};settingsTab=tab;setSettingsMenu(true);render();return true;
}
function renderSettings(content){
  content.innerHTML=`<div class="shopping-tabs" role="group" aria-label="Beállításcsoportok">${Object.entries(settingsSections).map(([key,label])=>`<button data-settings-tab="${key}" aria-pressed="${key===settingsTab}">${esc(label)}</button>`).join('')}</div><div id="settings-content"></div>`;
  $$('[data-settings-tab]').forEach(button=>button.onclick=()=>openSettingsTab(button.dataset.settingsTab));
  const target=$('#settings-content');
  $('#plan-status').hidden=true;
  if(settingsTab==='market')renderTradeSettings(target);
  else if(settingsTab==='notifications')renderNotificationSettings(target);
  else if(settingsTab==='intel')renderIntelSettings(target);
  else if(settingsTab==='appearance')renderAppearanceSettings(target);
  else if(settingsTab==='structures')renderStructureSettings(target);
  else if(settingsTab==='connection')renderConnection(target);
  else if(settingsTab==='accounts')renderAccounts(target);
  else if(!moonData){target.innerHTML=empty('Holdadatok betöltése');void refreshMoons();}
  else if(settingsTab==='moons')renderMoonSettings(target);
  else if(settingsTab==='calendar'){target.innerHTML=calendarIntegrationPanel();bindCalendarIntegration();}
  else{
    target.innerHTML=moonAuthPanel()+generalAccessPanel();bindMoonAuth();bindGeneralAccess();
    if(!settingsAccessData)void loadSettingsAccess();
  }
  setHead('BEÁLLÍTÁSOK',settingsSections[settingsTab],'Az alkalmazás kapcsolatai, jogosultságai és közös számítási beállításai.');
  $('#breadcrumb').textContent='Műhely / Beállítások / '+settingsSections[settingsTab];
}
function generalAccessPanel(){
  const d=settingsAccessData;
  const feature=(char,key)=>{
    if(!d)return '<span>Adatok betöltése…</span>';
    const entry=d[key]?.characters.find(c=>c.id===char.id),status=key==='corporations'?entry?.access:entry;
    const label=['contracts','implants'].includes(key)?(entry?.authorized?'Olvasási engedély megadva':'Engedélyezés szükséges'):key==='markets'?(entry?.market_access&&entry?.standings_access?'Olvasási engedély megadva':'Engedélyezés szükséges'):!status?'Még nincs lekérdezés':status.error?status.error:status.needs_auth?'Engedélyezés szükséges':'Olvasási engedély megadva';
    return `<span>${esc(label)}</span>`;
  };
  const labels={markets:'Market-hozzáférés engedélyezése',contracts:'Szerződések engedélyezése',implants:'Implantfigyelés engedélyezése',skills:'Skillek engedélyezése',pi:'PI engedélyezése',corporations:'Corp-hozzáférés engedélyezése',mining:'Bányászati napló engedélyezése'};
  return panel('Karakterek adathozzáférései','Karakterenkénti ESI-olvasási engedélyek',`<div class="panel-body"><div class="section-actions"><button class="button compact" id="access-status-refresh">Hozzáférések ellenőrzése</button>${Object.entries({skills:'Skilladatok frissítése',pi:'PI-adatok frissítése',corporations:'Corp-adatok frissítése',mining:'Bányászati naplók frissítése'}).map(([key,label])=>`<button class="button compact" data-access-sync="${key}" ${state.task.running?'disabled':''}>${esc(label)}</button>`).join('')}</div><p>Minden hozzáférés: készlet, blueprintek, jobok, skillek, PI, corporationadatok, holdadatok, intel, bányászati napló, marketek, standingek, implantok és szerződések egyetlen EVE-jóváhagyással.</p>${d?.error?'<p class="warning-text">Néhány hozzáférési állapot nem olvasható. Próbáld újra az ellenőrzést.</p>':''}</div>`+
    (state.characters.length?table(['Karakter','Minden hozzáférés','Marketek és standingek','Szerződések','Implantfigyelés','Skillek és tanulás','Bolygók és PI','Corporationok','Bányászati napló'],state.characters.map(char=>`<tr><td>${verbatim(char.name)}</td><td><button class="button compact" data-access-feature="all" data-access-character="${char.id}">Minden hozzáférés engedélyezése</button></td>${Object.entries(labels).map(([key,label])=>`<td>${feature(char,key)}<div><button class="text-button" data-access-feature="${key}" data-access-character="${char.id}">${esc(label)}</button></div></td>`).join('')}</tr>`),'access-overview'):empty('Még nincs hozzáadott karakter','Az EVE-kapcsolat oldalon add hozzá a karaktereidet.'))+
    `<details class="panel-body"><summary>Szükséges jogosultságok</summary>${Object.entries(labels).map(([key,label])=>`<h3>${esc(label)}</h3><code>${(state[{contracts:'contract_scopes',implants:'implant_scopes',markets:'market_scopes',skills:'skill_scopes',pi:'pi_scopes',corporations:'corporation_scopes',mining:'mining_scopes'}[key]]||[]).map(esc).join('\n')}</code>`).join('')}<p>Az új scope-okat az EVE Developer alkalmazásban is engedélyezni kell. A meglévő karaktert válaszd újra az engedélyezéskor.</p><p>A corp készlethez és blueprintekhez Director, a jobokhoz Factory Manager szerepkör szükséges.</p></details>`);
}
async function loadSettingsAccess(){
  if(settingsAccessRequest)return settingsAccessRequest;
  settingsAccessRequest=(async()=>{
    const keys=['skills','pi','corporations','mining','markets','implants','contracts'];
    const results=await Promise.allSettled(keys.map(key=>api('/api/'+(key==='markets'?'trade':key))));
    settingsAccessData={error:results.some(r=>r.status==='rejected')};
    results.forEach((result,i)=>{if(result.status==='fulfilled')settingsAccessData[keys[i]]=result.value;});
    if(view==='settings'&&settingsTab==='access')render();
  })();
  try{await settingsAccessRequest;}finally{settingsAccessRequest=null;}
}
function bindGeneralAccess(){
  $('#access-status-refresh').onclick=()=>void loadSettingsAccess();
  $$('[data-access-sync]').forEach(button=>button.onclick=async()=>{await startTask('/api/'+button.dataset.accessSync+'/sync');await loadSettingsAccess();});
  $$('[data-access-feature]').forEach(button=>button.onclick=async()=>{
    try{button.disabled=true;error('');const auth=await api('/api/auth/start',{character_id:Number(button.dataset.accessCharacter),feature:button.dataset.accessFeature});sessionStorage.setItem('eve-muhely-auth-return','settings:access');await openEveAuthorization(auth);}
    catch(e){error(e.message);button.disabled=false;}
  });
}

function renderAppearanceSettings(target){
  const dark=EveTheme.theme==='dark';
  target.innerHTML=panel('Megjelenés és nyelv','',`<div class="panel-body appearance-settings"><section><h3>Téma</h3><p>A sötét és világos mód a teljes felületre érvényes.</p><button type="button" class="theme-toggle" data-theme-toggle aria-label="Sötét mód" aria-pressed="${dark}"><span class="nav-icon" aria-hidden="true">☾</span><span>Sötét mód</span><span class="theme-switch" aria-hidden="true"></span></button></section><section><h3>A felület nyelve</h3><p>A választás azonnal érvényesül, a beírt adatok megmaradnak.</p><div class="language-control" role="group" aria-label="Nyelv / Language" data-i18n-skip><button type="button" data-ui-language="hu" lang="hu" aria-pressed="${EveI18n.language==='hu'}">Magyar</button><button type="button" data-ui-language="en" lang="en" aria-pressed="${EveI18n.language==='en'}">English</button></div></section><p class="footnote">A beállításokat ez az alkalmazásablak megjegyzi a következő indításhoz.</p></div>`);
}
