'use strict';
let moonData=null,moonTab='register',moonFilter='all',moonEditing=false,moonRequest=null,moonSelected=null,moonSystemGeneration=0,moonSearchGeneration=0,moonSearchTimer;
const moonDecimal=n=>new Intl.NumberFormat('hu-HU',{maximumFractionDigits:4}).format(n??0);
const moonPercent=n=>`${moonDecimal(n)}%`;
const moonStatus=m=>!m.enabled?'Leállítva':m.status==='invalid'?'100% felett · javítandó':m.status==='partial'?'Részleges összetétel':'Rendben';
const moonNumber=value=>Number(String(value).replace(/\s/g,'').replace(',','.'));
async function refreshMoons(){
  if(moonRequest)return moonRequest;
  moonRequest=api('/api/moons');
  try{moonData=await moonRequest;if(view==='moons'&&!moonEditing&&!dirty.moon_settings)render();}
  catch(e){if(view==='moons')error(e.message);}
  finally{moonRequest=null;}
}
function moonTable(headers,rows,key){return EveTables.markup(headers,rows,'moon-table','moons:'+key);}
function renderMoons(content){
  setHead('HOLDGAZDÁLKODÁS','Holdak és kitermelés','Kézi holdnyilvántartás, 30 napos termelés, üzemanyag és bányászkristály-arányok.');
  $('#plan-status').hidden=true;
  actions('<button id="moon-refresh" class="button compact">↻ Rendszeradatok ellenőrzése</button>');
  $('#moon-refresh').disabled=state.task.running||moonEditing||!!dirty.moon_settings;
  $('#moon-refresh').onclick=()=>startTask('/api/moons/sync');
  if(!moonData){content.innerHTML=empty('Holdadatok betöltése');void refreshMoons();return;}
  const d=moonData,s=d.summary;
  content.innerHTML=`<div class="shopping-tabs moon-tabs" role="group" aria-label="Holdnézet"><button data-moon-tab="register" aria-pressed="${moonTab==='register'}">Holdnyilvántartás</button><button data-moon-tab="production" aria-pressed="${moonTab==='production'}">30 napos termelés</button><button data-moon-tab="consumption" aria-pressed="${moonTab==='consumption'}">Fogyasztás</button><button data-moon-tab="crystals" aria-pressed="${moonTab==='crystals'}">Bányászkristályok</button><button data-moon-tab="settings" aria-pressed="${moonTab==='settings'}">Számítási beállítások</button></div>
    <div class="metrics"><div class="metric"><div class="metric-label">Nyilvántartott holdak</div><strong>${fmt(s.count)}</strong><small>hold</small></div><div class="metric"><div class="metric-label">Termelésbe beszámítva</div><strong>${fmt(s.included)}</strong><small>hold</small></div><div class="metric"><div class="metric-label">Javítandó összetétel</div><strong>${fmt(s.invalid)}</strong><small>100% feletti arány</small></div><div class="metric"><div class="metric-label">Tatara kihozatal</div><strong>${moonPercent(d.refining_yield*100)}</strong><small>Nullsec · T2 rig · minden skill V · ${d.settings.implant}% implant</small></div></div>
    <div class="moon-toolbar"><label>Struktúraszűrő <select id="moon-filter"><option value="all">Összes struktúra</option><option value="Athanor">Athanor</option><option value="Metenox">Metenox</option></select></label><span>Időszak: 30 nap · 720 óra</span></div><div id="moon-body"></div>`;
  $('#moon-filter').value=moonFilter;
  $('#moon-filter').onchange=e=>{moonFilter=e.target.value;renderMoonBody();};
  $$('[data-moon-tab]').forEach(b=>b.onclick=()=>{if(Object.keys(dirty).length&&!confirmUI('Vannak még nem alkalmazott módosítások. Elhagyod ezt az oldalt?'))return;dirty={};moonEditing=false;moonSystemGeneration++;moonSearchGeneration++;moonTab=b.dataset.moonTab;render();});
  renderMoonBody();
}
function renderMoonBody(){
  const target=$('#moon-body');if(!target)return;
  if(moonEditing)return;
  const d=moonData,moons=d.moons.filter(m=>moonFilter==='all'||m.structure===moonFilter);
  if(moonTab==='settings')return renderMoonSettings(target);
  if(moonTab==='register'){
    target.innerHTML=`<div class="moon-toolbar"><p class="muted">A nyilvántartás közös ezen a gépen. A becsült termelés nem kerül automatikusan a gyártási készletbe.</p><button id="moon-add" class="button primary compact">＋ Hold felvétele</button></div><div id="moon-editor"></div>`;
    target.innerHTML+=panel('Bérelt holdak',`${fmt(moons.length)} hold`,moons.length?moonTable(['Hold','Rendszer','Csillagkép','Struktúra','Ércek és arányok','Arányösszeg','Állapot','Megjegyzés','Művelet'],moons.map(m=>`<tr><td>${verbatim(m.name)}</td><td>${verbatim(m.system.name)}</td><td>${verbatim(m.system.constellation)}<small class="sub">${m.esi_checked?'ESI · '+esc(date(m.esi_checked)):'SDE · ESI-ellenőrzés szükséges'}</small></td><td>${esc(m.structure)}</td><td>${m.ores.map(o=>`${itemName(o.name)} ${moonPercent(o.percent)}`).join('<br>')}</td><td class="num" data-sort-value="${m.percent_total}">${moonPercent(m.percent_total)}</td><td><span class="badge ${m.status==='invalid'?'warn':''}">${moonStatus(m)}</span></td><td>${verbatim(m.notes)}</td><td><button data-edit-moon="${esc(m.id)}" class="text-button">Szerkesztés</button></td></tr>`),'register'):empty('Még nincs hold ebben a nézetben','A Hold felvétele gombbal válassz rendszert és holdat, majd add meg az érceket.'));
    $('#moon-add').onclick=()=>openMoonEditor();
    $$('[data-edit-moon]').forEach(b=>b.onclick=()=>openMoonEditor(d.moons.find(m=>m.id===b.dataset.editMoon)));
    return;
  }
  const invalid=moons.filter(m=>m.status==='invalid'),partial=moons.filter(m=>m.status==='partial');
  target.innerHTML=(invalid.length?`<div class="banner warn"><strong>Javításig kimaradnak a termelésből:</strong> ${invalid.map(m=>verbatim(m.name)).join(', ')}. <span>A megadott ércarányok összege meghaladja a 100%-ot.</span></div>`:'')+(partial.length?'<div class="banner">A részleges összetételű holdaknál csak a megadott ércekkel számolunk. Az arányokat nem növeljük fel 100%-ra.</div>':'');
  if(moonTab==='production'){
    target.innerHTML+=`<div class="banner">Az Athanor becslése a beállított begyűjtési aránnyal és a Tatara finomításával számol. A Metenox a saját, skillektől és implanttól független 40%-os kihozatalát használja. Folyamatos működést feltételezünk; ez előrejelzés, nem ESI-ben látott készlet.</div>`;
    const ids=[...new Set(['Athanor','Metenox'].flatMap(k=>d.totals[k].map(r=>r.id)))].sort((a,b)=>d.totals.all.find(r=>r.id===a).name.localeCompare(d.totals.all.find(r=>r.id===b).name));
    const amount=(k,id)=>d.totals[k].find(r=>r.id===id)?.quantity||0;
    const rows=ids.map(id=>`<tr><td>${itemName(d.totals.all.find(r=>r.id===id).name)}</td>${(moonFilter==='all'?['Athanor','Metenox','all']:[moonFilter]).map(k=>`<td class="num">${fmt(amount(k,id))}</td>`).join('')}</tr>`);
    target.innerHTML+=panel('Összesített anyagtermelés','30 nap · csak a beszámítható holdak',moonTable(moonFilter==='all'?['Anyag','Athanor (db)','Metenox (db)','Összesen (db)']:['Anyag','Mennyiség (db)'],rows,'production-'+moonFilter));
    target.innerHTML+=panel('Termelés holdanként','30 nap',moonTable(['Hold','Struktúra','Anyag','Mennyiség (db)','Állapot'],moons.flatMap(m=>m.outputs.length?m.outputs.map(r=>`<tr><td>${verbatim(m.name)}</td><td>${m.structure}</td><td>${itemName(r.name)}</td><td class="num" data-sort-value="${m.included?r.quantity:''}">${m.included?fmt(r.quantity):'–'}</td><td>${moonStatus(m)}</td></tr>`):[]),'production-moons-'+moonFilter));
    target.innerHTML+=panel('Érctérfogat és feldolgozás','Athanor: teljes 100 darabos adagok finomítása; Metenox: órás ciklusok',moonTable(['Hold','Érc','Arány','Érctérfogat (m³)','Nyers érc (db)'],moons.flatMap(m=>m.ores.map(o=>`<tr><td>${verbatim(m.name)}</td><td>${itemName(o.name)}</td><td class="num">${moonPercent(o.percent)}</td><td class="num" data-sort-value="${o.volume??''}">${o.volume===null?'–':fmt(o.volume)}</td><td class="num" data-sort-value="${o.units??''}">${o.units===null?'–':fmt(o.units)}</td></tr>`)),'ore-volumes-'+moonFilter));
  }else if(moonTab==='consumption'){
    target.innerHTML+='<div class="banner">Csak a holdfúró fogyasztása szerepel itt. Más szolgáltatásmodulok, a külön Tatara üzemanyaga és a bérleti díj nincsenek benne. A hibás ércösszetételű, működő holdak üzemanyagát is számoljuk. A bekapcsolási költséget külön kell megadni.</div>';
    const keys=moonFilter==='all'?['Athanor','Metenox','all']:[moonFilter];
    target.innerHTML+=panel('Összesített fogyasztás','30 nap',moonTable(['Struktúra','Működő holdak','Fuel Block / nap','Fuel Block / 30 nap','Magmatic Gas / nap','Magmatic Gas / 30 nap','Bekapcsolási Fuel Block','Teljes Fuel Block'],keys.map(k=>{const c=d.consumption[k];return `<tr><td>${k==='all'?'Összesen':k}</td><td class="num">${fmt(c.count)}</td><td class="num">${fmt(c.fuel/30)}</td><td class="num">${fmt(c.fuel)}</td><td class="num">${fmt(c.gas/30)}</td><td class="num">${fmt(c.gas)}</td><td class="num">${fmt(c.online_fuel)}</td><td class="num">${fmt(c.fuel+c.online_fuel)}</td></tr>`;}),'consumption-'+moonFilter));
    target.innerHTML+=panel('Fogyasztás holdanként','A hold szerkesztésénél állítható az üzem és a bekapcsolások száma',moonTable(['Hold','Struktúra','Fuel Block / nap','Fuel Block / 30 nap','Magmatic Gas / nap','Magmatic Gas / 30 nap','Bekapcsolások','Bekapcsolási Fuel Block'],moons.map(m=>`<tr><td>${verbatim(m.name)}</td><td>${m.structure}</td><td class="num">${fmt(m.fuel/30)}</td><td class="num">${fmt(m.fuel)}</td><td class="num">${fmt(m.gas/30)}</td><td class="num">${fmt(m.gas)}</td><td class="num">${fmt(m.online_starts)}</td><td class="num">${fmt(m.online_fuel)}</td></tr>`),'consumption-moons-'+moonFilter));
  }else{
    target.innerHTML+='<div class="banner">A kristályarány az Athanorok megadott, bányászandó érctérfogatának megoszlása. Nem kristálydarabszám vagy kopási becslés. A Metenox automatikusan dolgozik, bányászkristályt nem igényel.</div>';
    if(moonFilter!=='Metenox')target.innerHTML+=panel('Kristálytípusok összesítve','Csak a működő, beszámítható Athanorok',moonTable(['Kristály','Érckategória','Érctérfogat (m³)','Arány'],d.crystals.map(c=>`<tr><td>${itemName(c.name)}</td><td>R${c.rarity}</td><td class="num">${fmt(c.volume)}</td><td class="num">${moonPercent(c.share)}</td></tr>`),'crystals-total'));
    target.innerHTML+=panel('Kristályterv holdanként','A kristályváltozat a Számítási beállítások fülön választható',moonTable(['Hold','Struktúra','Kristály','Ércek','Érctérfogat (m³)','Megadott érceken belüli arány'],moons.flatMap(m=>m.structure==='Metenox'?[`<tr><td>${verbatim(m.name)}</td><td>Metenox</td><td>Nincs szükség kristályra</td><td>–</td><td>–</td><td>–</td></tr>`]:m.crystals.map(c=>`<tr><td>${verbatim(m.name)}</td><td>Athanor</td><td>${itemName(c.name)}</td><td>${c.ores.map(itemName).join(', ')}</td><td class="num" data-sort-value="${c.volume??''}">${c.volume===null?'–':fmt(c.volume)}</td><td class="num" data-sort-value="${c.share??''}">${c.share===null?'–':moonPercent(c.share)}</td></tr>`)),'crystals-moons-'+moonFilter));
  }
}
function renderMoonSettings(target){
  const d=moonData;
  target.innerHTML=panel('Finomítás és kristályváltozat','A beállítások az összes holdra érvényesek',`<form id="moon-settings" class="panel-body moon-settings"><label>Finomítási implant<select name="implant">${[0,1,2,4].map(n=>`<option value="${n}" ${d.settings.implant===n?'selected':''}>${n}%</option>`).join('')}</select></label><label>Begyűjtött arány (%)<input name="mining_recovery" type="text" inputmode="decimal" required value="${moonDecimal(d.settings.mining_recovery)}"></label><label>Kristályváltozat<select name="crystal_variant">${d.crystal_variants.map(v=>`<option data-i18n-skip value="${v}" ${d.settings.crystal_variant===v?'selected':''}>${v}</option>`).join('')}</select></label><button class="button primary compact">Beállítások mentése</button><p>A begyűjtött arány a kézi bányászat utáni, finomításra ténylegesen megmaradó érc. 100% esetén teljes begyűjtést feltételezünk; a bányászati veszteséget, a kihagyott érceket és az állásidőt ezzel csökkentheted.</p></form>`);
  target.innerHTML+=panel('Számítási alapok','CCP-adatok és látható feltételezések',`<div class="panel-body"><p>30 nap = 720 óra. Alap kitermelés: ${fmt(d.rules.extraction_m3_hour)} m³/óra, megszorozva a megadott ércaránnyal. Az ismeretlen részt nem pótoljuk, a 100,02% feletti összeget javításig kihagyjuk.</p><p>Tatara · nullsec · T2 reprocessing rig · Reprocessing V · Reprocessing Efficiency V · megfelelő Moon Ore Processing V.</p><p data-i18n-skip>${d.rules.rig_base} × (1 + ${d.rules.tatara_bonus}/100) × ${d.rules.rig_nullsec} × 1.15 × 1.10 × 1.10 × (1 + ${d.settings.implant}/100) = ${moonPercent(d.refining_yield*100)}</p><p>Az Athanor-érceknél teljes finomítási adagokkal és anyagonként lefelé kerekítéssel számolunk. A Metenox órás kihozatalát külön lefelé kerekítjük; a finomítási implant rá nem hat. A Metenox csak holdanyagokat ad, Pyerite és Mexallon nem keletkezik.</p><p>Csak az alapérceket vesszük figyelembe. A gazdagabb változatokat, jackpotot, bányászati kritikus találatokat és kompressziós veszteséget nem feltételezzük.</p><p>SDE build: ${esc(d.sde.buildNumber)}</p><ul>${d.sources.map(s=>`<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer" data-i18n-skip>${esc(s.name)}</a></li>`).join('')}</ul></div>`);
  const form=$('#moon-settings');form.oninput=()=>{dirty.moon_settings=true;};
  form.onsubmit=async e=>{e.preventDefault();try{const f=new FormData(form);await api('/api/moons/settings',{implant:Number(f.get('implant')),mining_recovery:moonNumber(f.get('mining_recovery')),crystal_variant:f.get('crystal_variant')});dirty={};await refreshMoons();toast('Holdbeállítások mentve.');}catch(e){error(e.message);}};
}
function openMoonEditor(record){
  moonEditing=true;moonSelected=record?{id:record.system_id,name:record.system.name}:null;
  const target=$('#moon-editor');if(!target)return;
  const d=moonData,entries=record?.ores||[];
  target.innerHTML=panel(record?'Hold szerkesztése':'Új hold','Legfeljebb négy különböző érc; vesszős és pontos tizedes is megadható',`<form id="moon-form" class="panel-body"><div class="moon-form-grid"><label class="moon-system-field">Rendszer<div class="search-wrap"><input id="moon-system" type="search" autocomplete="off" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="moon-system-results" placeholder="Gépelj rendszernevet…" value="${esc(record?.system.name||'')}"><div class="search-results" id="moon-system-results" role="listbox" hidden></div></div></label><label>Csillagkép<input id="moon-constellation" readonly value="${esc(record?.system.constellation||'')}"></label><label>Hold<select id="moon-location" required>${record?`<option value="${record.moon_id}" data-i18n-skip>${esc(record.name)}</option>`:'<option value="">Előbb válassz rendszert</option>'}</select></label><label>Struktúra<select id="moon-structure"><option value="Athanor">Athanor</option><option value="Metenox">Metenox</option></select></label></div><p id="moon-system-status" class="footnote" role="status"></p><div class="moon-ore-grid">${[0,1,2,3].map(i=>`<div><label>Érc ${i+1}<select data-moon-ore="${i}"><option value="">Nincs megadva</option>${d.ores.map(o=>`<option data-i18n-skip value="${o.id}" ${entries[i]?.id===o.id?'selected':''}>R${o.rarity} · ${esc(o.name)}</option>`).join('')}</select></label><label>Ércarány (%)<input data-moon-density="${i}" type="text" inputmode="decimal" value="${entries[i]?moonDecimal(entries[i].percent):''}"></label></div>`).join('')}</div><p id="moon-composition-status" role="status"></p><div class="moon-form-grid"><label class="check"><input id="moon-enabled" type="checkbox" ${record?.enabled===false?'':'checked'}> Működő holdfúró</label><label>Bekapcsolások a 30 nap alatt<input id="moon-starts" type="number" min="0" max="1000" value="${record?.online_starts||0}" required></label><label>Megjegyzés<textarea id="moon-notes" maxlength="2000" rows="2">${esc(record?.notes||'')}</textarea></label></div><div class="moon-toolbar"><button class="button primary compact" id="moon-save">Hold mentése</button><button class="button compact" type="button" id="moon-cancel">Mégse</button>${record?'<button class="text-button danger" type="button" id="moon-remove">Hold törlése</button>':''}</div><p class="footnote">A 100% feletti adatot ellenőrizendőként is elmentheted; a termelésbe csak javítás után kerül be. A fogyasztása működőként továbbra is számít.</p></form>`);
  $('#moon-structure').value=record?.structure||'Athanor';
  const form=$('#moon-form');form.oninput=()=>{dirty.moon_editor=true;updateMoonComposition();};
  $('#moon-cancel').onclick=()=>closeMoonEditor();
  if(record)$('#moon-remove').onclick=async()=>{if(!confirmUI('Törlöd ezt a holdat a nyilvántartásból?'))return;try{await api('/api/moons/remove',{id:record.id});await closeMoonEditor(true);toast('Hold törölve.');}catch(e){error(e.message);}};
  form.onsubmit=async e=>{e.preventDefault();if(!moonSelected)return error('Válassz rendszert a találati listából.');
    const ores=[];for(let i=0;i<4;i++){const id=$(`[data-moon-ore="${i}"]`).value,v=$(`[data-moon-density="${i}"]`).value;if(id||v.trim())ores.push({id:Number(id),percent:moonNumber(v)});}
    const body={system_id:moonSelected.id,moon_id:Number($('#moon-location').value),structure:$('#moon-structure').value,ores,notes:$('#moon-notes').value,enabled:$('#moon-enabled').checked,online_starts:Number($('#moon-starts').value)};
    if(record)body.id=record.id;$('#moon-save').disabled=true;
    try{await api('/api/moons/save',body);await closeMoonEditor(true);toast('Hold mentve.');}catch(e){error(e.message);if($('#moon-save'))$('#moon-save').disabled=false;}
  };
  const input=$('#moon-system'),results=$('#moon-system-results');
  input.oninput=()=>{moonSelected=null;moonSystemGeneration++;$('#moon-constellation').value='';$('#moon-location').innerHTML='<option value="">Előbb válassz rendszert</option>';$('#moon-system-status').textContent='Válassz rendszert a találati listából.';clearTimeout(moonSearchTimer);const generation=++moonSearchGeneration;moonSearchTimer=setTimeout(async()=>{try{const rows=await api('/api/moons/systems?q='+encodeURIComponent(input.value));if(generation!==moonSearchGeneration||!input.isConnected)return;results.innerHTML=rows.length?rows.map(s=>`<button type="button" role="option" data-moon-system-id="${s.id}">${verbatim(s.name)} <small>${verbatim(s.constellation)}</small></button>`).join(''):'<p>Nincs találat.</p>';results.hidden=false;input.setAttribute('aria-expanded','true');results.querySelectorAll('button').forEach(b=>b.onclick=()=>{dirty.moon_editor=true;const s=rows.find(r=>r.id===Number(b.dataset.moonSystemId));void selectMoonSystem(s);});}catch(e){if(generation===moonSearchGeneration)error(e.message);}},180);};
  input.onkeydown=e=>{if(e.key==='Escape'){results.hidden=true;input.setAttribute('aria-expanded','false');}else if(e.key==='ArrowDown'){e.preventDefault();results.querySelector('button')?.focus();}else if(e.key==='Enter'&&!results.hidden){e.preventDefault();results.querySelector('button')?.click();}};
  results.onkeydown=e=>{const buttons=[...results.querySelectorAll('button')],i=buttons.indexOf(document.activeElement);if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();buttons[(i+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}if(e.key==='Escape'){results.hidden=true;input.focus();input.setAttribute('aria-expanded','false');}};
  updateMoonComposition();
  if(record)void selectMoonSystem(moonSelected,record.moon_id);
  target.scrollIntoView?.({block:'nearest',behavior:'smooth'});
}
function updateMoonComposition(){
  const target=$('#moon-composition-status');if(!target)return;
  let total=0;for(let i=0;i<4;i++)if($(`[data-moon-ore="${i}"]`).value)total+=moonNumber($(`[data-moon-density="${i}"]`).value)||0;
  target.textContent='Ércarányok összege: '+moonPercent(total)+(total>100.02?' · 100% felett · javítandó':total<99.98?' · Részleges összetétel':' · Rendben');
  target.className=total>100.02?'warning-text':'muted';
}
async function selectMoonSystem(system,moonId){
  const generation=++moonSystemGeneration;moonSearchGeneration++;clearTimeout(moonSearchTimer);moonSelected={id:system.id,name:system.name};
  $('#moon-system').value=system.name;$('#moon-system-results').hidden=true;$('#moon-system').setAttribute('aria-expanded','false');$('#moon-constellation').value=system.constellation||'';$('#moon-system-status').textContent='Rendszeradatok ellenőrzése az ESI-ben…';$('#moon-save').disabled=true;
  try{const data=await api('/api/moons/system?id='+system.id);if(generation!==moonSystemGeneration||!moonEditing||!$('#moon-form'))return;
    $('#moon-constellation').value=data.system.constellation;$('#moon-location').innerHTML='<option value="">Válassz holdat</option>'+data.moons.map(m=>`<option data-i18n-skip value="${m.id}">${esc(m.name)}</option>`).join('');
    if(moonId)$('#moon-location').value=moonId;
    $('#moon-system-status').textContent=data.error?'Az ESI most nem érhető el; a korábbi ESI- vagy SDE-adatot használjuk.':('ESI ellenőrizve: '+date(data.checked));$('#moon-save').disabled=false;
  }catch(e){if(generation===moonSystemGeneration){error(e.message);$('#moon-system-status').textContent='A rendszeradat nem tölthető be. Válaszd ki újra a rendszert.';}}
}
async function closeMoonEditor(refresh=false){moonSystemGeneration++;moonSearchGeneration++;clearTimeout(moonSearchTimer);moonEditing=false;dirty={};error('');if(refresh)await refreshMoons();else render();}
