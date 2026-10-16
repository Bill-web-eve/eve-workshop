'use strict';
let piData=null,piRequest=null,piRequestHours=null,piGeneration=0,piTimer=null,piHours=24,piCharacter='all',piOnlyAlerts=false,piSelected=null,piFactory=null;
const piKey=c=>`${c.character_id}:${c.id}`;
const piType=value=>({temperate:'Mérsékelt',barren:'Kopár',oceanic:'Óceáni',ice:'Jég',gas:'Gáz',lava:'Láva',storm:'Vihar',plasma:'Plazma'}[value]||value);
const piState=value=>({alert:'Beavatkozás jelzett',warning:'Figyelmeztetés',unknown:'Ellenőrizendő adatok',ok:'Aktív termelési jel'}[value]||value);
const piBadge=(status,text)=>`<span class="badge pi-${status}">${esc(text||piState(status))}</span>`;
async function refreshPI(auto=false){
  if(piRequest&&piRequestHours===piHours)return piRequest;
  clearTimeout(piTimer);const generation=++piGeneration,hours=piHours;
  const request=api('/api/pi?hours='+hours);piRequest=request;piRequestHours=hours;
  let shouldSync=false;
  try{
    const data=await request;if(generation!==piGeneration)return;
    piData=data;
    const alerts=data.summary.alert+data.summary.warning;
    $('#pi-count').textContent=alerts?fmt(alerts):data.summary.unknown||data.characters.some(c=>c.status==='unknown')?'?':'0';
    $('#pi-count').title=`Beavatkozás: ${data.summary.alert}; figyelmeztetés: ${data.summary.warning}; ellenőrizendő kolónia: ${data.summary.unknown}`;
    shouldSync=auto&&!state.task.running&&data.characters.some(c=>!c.needs_auth&&(!c.checked_at||c.expires<=Date.now()/1000));
    if(view==='pi')render();
  }catch(e){if(view==='pi'&&generation===piGeneration){error(e.message);$('#view-content').innerHTML=empty('A PI-adatok most nem olvashatók','Indíts PI-frissítést a fenti gombbal.');}}
  finally{if(generation===piGeneration){piRequest=null;piRequestHours=null;}}
  if(shouldSync&&view==='pi')void startTask('/api/pi/sync');
}
function renderPI(content){
  setHead('PLANETARY INDUSTRY','Bolygók és PI','Karakterenkénti bolygónyilvántartás, kitermelőprogramok és a gyárak útvonalon elérhető alapanyag-ellátása.');
  $('#plan-status').hidden=true;
  actions(`<label class="pi-horizon">Ellátási időtáv<select id="pi-hours" aria-label="PI ellátási időtáv">${[1,6,24,72].map(n=>`<option value="${n}" ${n===piHours?'selected':''}>${n} óra</option>`).join('')}</select></label><button class="button primary compact" id="pi-sync" ${state.task.running?'disabled':''}>↻ PI-adatok frissítése</button>`);
  $('#pi-sync').onclick=()=>startTask('/api/pi/sync');
  $('#pi-hours').onchange=e=>{piHours=Number(e.target.value);void refreshPI();};
  if(!piData){content.innerHTML=empty('Bolygóadatok betöltése','A helyben mentett kolóniákat ellenőrizzük…');void refreshPI(true);return;}
  if(!piData.characters.length){content.innerHTML=empty('Még nincs hozzáadott karakter','Az EVE-kapcsolat oldalon add hozzá a karaktereidet és engedélyezd a PI-adatok olvasását.');return;}
  const chars=piData.characters,all=piData.colonies,s=piData.summary;
  const missingChars=chars.filter(c=>c.status==='unknown').length;
  content.innerHTML=`<div class="metrics"><div class="metric"><div class="metric-label">Nyilvántartott bolygók</div><strong>${fmt(all.length)}</strong><small>${chars.length-missingChars}/${chars.length} karakter betöltve</small></div><div class="metric"><div class="metric-label">Beavatkozás jelzett</div><strong class="danger">${fmt(s.alert)}</strong><small>bolygó</small></div><div class="metric"><div class="metric-label">Figyelmeztetés</div><strong class="warning-text">${fmt(s.warning)}</strong><small>bolygó</small></div><div class="metric"><div class="metric-label">Ellenőrizendő kolóniák</div><strong>${fmt(s.unknown)}</strong><small>${missingChars} karakter adata hiányos</small></div></div>`;
  content.innerHTML+='<div class="banner warn"><strong>A PI állapota dátumhoz kötött.</strong> Az EVE a kolónia állapotát a bolygó játékbeli megnyitásakor számolja újra. A lenti készletfedezet a jelzett kolónia-pillanatképre vonatkozik. Régi gyáradatnál nyisd meg a bolygót a játékban, majd frissíts itt; a CCP gyorsítótára miatt ez nem mindig azonnali.</div>';
  if(chars.some(c=>c.needs_auth))content.innerHTML+=`<details class="panel skill-permissions" ${chars.every(c=>c.needs_auth)?'open':''}><summary>PI-hozzáférés engedélyezése</summary><div class="panel-body"><p>Az <a href="https://developers.eveonline.com/applications" target="_blank" rel="noopener noreferrer">EVE Developer oldalon</a> a meglévő alkalmazásodhoz add hozzá ezt a jogosultságot:</p><code>${(state.pi_scopes||[]).map(esc).join('\n')}</code><p>A CCP ezt a nevű jogosultságot használja a bolygóadatokhoz. A Műhelyben adatlekérésre szolgál. Ezután karakterenként a <strong>PI engedélyezése</strong> gombbal lépj be ugyanazzal a karakterrel. A korábbi gyártási és skillengedélyeket megőrizzük.</p></div></details>`;
  content.innerHTML+=`<details class="panel pi-characters" ${!all.length?'open':''}><summary>Karakterek PI-hozzáférése · ${chars.length-missingChars}/${chars.length} betöltve</summary>${table(['Karakter','Bolygók','Adatállapot','Művelet'],chars.map(c=>`<tr><td>${esc(c.name)}</td><td>${c.planet_count==null?'–':fmt(c.planet_count)}</td><td>${c.needs_auth?'Engedélyezés szükséges':c.error?esc(c.error):c.stale?'Elavult adat':c.planet_count==null?'Még nincs frissítve':'Betöltve'}<div class="batch-note">Lekérdezés: ${esc(skillDate(c.checked_at))}</div></td><td>${c.needs_auth?`<button class="button compact" data-pi-auth="${c.id}" aria-label="${esc(c.name)} – PI engedélyezése">PI engedélyezése</button>`:''}</td></tr>`))}</details>`;
  const filtered=all.filter(c=>(piCharacter==='all'||c.character_id===Number(piCharacter))&&(!piOnlyAlerts||c.status!=='ok'));
  const controls=`<div class="panel-head pi-filters"><select id="pi-character" aria-label="PI karakter szűrése"><option value="all">Minden karakter</option>${chars.map(c=>`<option value="${c.id}" ${String(c.id)===piCharacter?'selected':''}>${esc(c.name)}</option>`).join('')}</select><label><input id="pi-only-alerts" type="checkbox" ${piOnlyAlerts?'checked':''}> Csak jelzések és ellenőrizendők</label></div>`;
  const row=c=>`<tr class="pi-state-${c.status}"><td><button class="text-button pi-planet-name" data-pi-open="${piKey(c)}" aria-label="${esc(c.character_name+' – '+c.name)} – PI-részletek">${esc(c.name)}</button><div class="batch-note">${esc(piType(c.type))}</div></td><td data-filter-value="${esc(c.character_name)}">${esc(c.character_name)}</td><td>${piBadge(c.status)}<div class="pi-row-note">${esc(c.alerts[0]||'A kitermelőprogram vagy a jelzett gyári ciklus aktív.')}</div></td><td>${c.extractors.filter(e=>e.active).length}/${c.extractors.length} program<div class="batch-note">${c.factories.filter(f=>f.running_evidence).length}/${c.factories.length+c.unassigned.length+c.unknown_recipes.length} jelzett gyári ciklus</div></td><td>${c.factories.length?c.next_enough==null?'–':c.next_enough?'Következő ciklus fedezett':'Készlet / utánpótlás ellenőrzendő':'–'}<div class="batch-note">Készletből: ${c.stock_coverage_seconds==null?'–':(c.stock_coverage_seconds>=30*86400?'legalább ':'')+skillDuration(c.stock_coverage_seconds)}</div></td><td data-sort-value="${c.last_update??''}">${esc(skillDate(c.last_update))}<div class="batch-note">Lekérdezés: ${esc(skillDate(c.checked_at))}</div></td><td><button class="button compact" data-pi-open="${piKey(c)}" aria-label="${esc(c.character_name+' – '+c.name)} – Részletek">Részletek</button></td></tr>`;
  content.innerHTML+=panel('Kolóniák',`${filtered.length}/${all.length} bolygó`,controls+(filtered.length?table(['Bolygó','Karakter','Jelzés','Termelési adatok','Gyártási fedezet','Kolóniaállapot ideje','Művelet'],filtered.map(row),'pi-overview'):empty(all.length?'Nincs ilyen bolygó a szűrésben':'Még nincs betöltött kolónia',missingChars?'Engedélyezd a PI-adatokat, majd indíts frissítést.':'A sikeres, üres bolygólista azt jelenti, hogy ezeknek a karaktereknek nincs PI-kolóniájuk.')));
  content.innerHTML+='<p class="footnote">A fedezet a meglévő raktárkészletet, gyári bemeneti puffereket, termékútvonalakat és a közös készletekért versengő gyárakat veszi figyelembe. A még el nem készült kitermelés és köztes termelés utánpótlásfüggésként szerepel. A linkek sávszélességét és a későbbi importot nem szimuláljuk. Más bolygó vagy karakter készletét nem számoljuk ide.</p><div id="pi-detail"></div>';
  $('#pi-character').onchange=e=>{piCharacter=e.target.value;render();};
  $('#pi-only-alerts').onchange=e=>{piOnlyAlerts=e.target.checked;render();};
  $$('[data-pi-open]').forEach(el=>el.onclick=()=>{piSelected=el.dataset.piOpen;piFactory=null;renderPIDetail();$('#pi-detail').scrollIntoView({block:'start',behavior:'smooth'});});
  $$('[data-pi-auth]').forEach(el=>el.onclick=async()=>{
    try{el.disabled=true;error('');const auth=await api('/api/auth/start',{character_id:Number(el.dataset.piAuth),feature:'pi'});sessionStorage.setItem('eve-muhely-auth-return','pi');window.location.assign(auth.url);}
    catch(e){error(e.message);el.disabled=false;}
  });
  if(!filtered.some(c=>piKey(c)===piSelected))piSelected=filtered[0]?piKey(filtered[0]):null;
  renderPIDetail();clearTimeout(piTimer);
  piTimer=setTimeout(()=>{
    if(view!=='pi')return;
    const due=piData.characters.some(c=>!c.needs_auth&&(!c.expires||c.expires<=Date.now()/1000));
    if(!document.hidden&&!state.task.running&&due)void startTask('/api/pi/sync');else void refreshPI();
  },60000);
}
function renderPIDetail(){
  const target=$('#pi-detail'),c=piData?.colonies.find(c=>piKey(c)===piSelected);
  if(!target)return;if(!c){target.innerHTML='';return;}
  const extractorRows=c.extractors.map(e=>`<tr><td>${itemName(e.name)}<div class="batch-note">${e.id}</div></td><td>${itemName(e.product)}</td><td>${piBadge(e.active?'ok':'alert',e.label)}</td><td>${e.heads}</td><td data-sort-value="${e.cycle_time??''}">${e.cycle_time?skillDuration(e.cycle_time):'–'}</td><td data-sort-value="${e.program_end??''}">${esc(skillDate(e.program_end))}<div class="batch-note">${esc(skillDuration(e.seconds_left))}</div></td></tr>`);
  const factories=[...c.factories.map(f=>`<tr><td><button class="text-button" data-pi-factory="${f.id}" data-copy-item="${esc(f.product)}" aria-label="${esc(f.product)} – Gyári bemenetek ${f.id}">${esc(f.product)}</button><div class="batch-note">${itemName(f.name)} · ${f.id}</div></td><td data-sort-value="${f.cycle_time??''}">${esc(skillDuration(f.cycle_time))}</td><td data-sort-value="${f.last_cycle_start??''}">${f.running_evidence?'A jelzett ciklus még tarthat':'Futás nem igazolt'}<div class="batch-note">Utolsó ciklus: ${esc(skillDate(f.last_cycle_start))}</div></td><td>${piBadge(f.supply_status==='ready'?'ok':f.supply_status==='incoming'?'warning':'alert',f.supply_label)}${f.missing_materials.length?`<div class="pi-row-note">${f.missing_materials.map(m=>itemName(m.name)).join(', ')}</div>`:''}</td><td>${f.output_routed?'Útvonal beállítva':piBadge('alert','Kimeneti útvonal hiányzik')}</td></tr>`),
    ...[...c.unassigned,...c.unknown_recipes].map(f=>`<tr><td>${itemName(f.name)}<div class="batch-note">${f.id}</div></td><td>–</td><td>${esc(f.label)}</td><td>–</td><td>–</td></tr>`)];
  const materials=c.period_materials.map(m=>`<tr class="${m.missing?'pi-material-short':''}"><td>${itemName(m.name)}</td><td class="num">${fmt(m.required)}</td><td class="num">${fmt(m.on_planet)}</td><td class="num">${fmt(m.usable)}</td><td class="num"><strong>${fmt(m.missing)}</strong></td></tr>`);
  const stores=c.storages.map(s=>`<tr><td>${itemName(s.name)}<div class="batch-note">${s.id}</div></td><td data-sort-value="${s.used??''}">${s.used==null?'–':s.used.toLocaleString('hu-HU',{maximumFractionDigits:1})} / ${s.capacity==null?'–':fmt(s.capacity)} m³ ${s.full?piBadge('warning','Tele'):''}</td><td>${s.contents.length?s.contents.map(i=>`${itemName(i.name)}: ${fmt(i.amount)} db`).join('<br>'):'Üres'}</td></tr>`);
  target.innerHTML=panel(c.name+' – PI-részletek',`${c.character_name} · CC ${c.upgrade_level} · ${c.pin_count} épület`,`<div class="pi-detail-body"><div class="chip-list"><span class="chip">Kolóniaállapot: ${esc(skillDate(c.last_update))}</span><span class="chip">Lekérdezés: ${esc(skillDate(c.checked_at))}</span>${piBadge(c.status)}</div>${c.alerts.length?`<div class="banner warn pi-alert-list">${c.alerts.map(a=>`<p>${esc(a)}</p>`).join('')}</div>`:''}<h3>Kitermelőprogramok</h3>${extractorRows.length?table(['Kitermelő','Termék','Program','Fejek','Ciklus','Program vége'],extractorRows):'<p class="muted">Nincs kitermelő a betöltött kolónián.</p>'}<h3>Gyárak</h3>${factories.length?table(['Termék / gyár','Ciklus','Termelési időbélyeg','Következő ciklus ellátása','Termékkimenet'],factories):'<p class="muted">Nincs gyár a betöltött kolónián.</p>'}<div id="pi-factory-detail"></div><div class="pi-section-title"><h3>Tárolt alapanyagok fedezete · ${piHours} óra</h3><button class="button compact" id="pi-export" ${materials.length?'':'disabled'}>Ellátási hiányok CSV</button></div>${materials.length?table(['Anyag','Szükséges (db)','Bolygón összesen (db)','Felhasználható ebből (db)','Hiány a fedezethez (db)'],materials):'<p class="muted">Nincs ellenőrizhető, beállított gyártási bemenet.</p>'}<p class="footnote">A szükséglet az összes ellenőrizhető gyár ${piHours} órányi teljes ciklusára vonatkozik, a következő ciklustól. A már elindított ciklus bemeneteire nem adunk új készletjóváírást. Ha a bolygón van elegendő anyag, mégis hiány látszik, ellenőrizd a termékútvonalakat és az egyes gyárak puffereit. Közös raktárkészletet egyszer számolunk.</p><h3>Raktárak és kilövőállások</h3>${stores.length?table(['Épület','Térfogat a pillanatképben','Tárolt termékek'],stores):'<p class="muted">Nincs betöltött tároló.</p>'}</div>`);
  $('#pi-export').onclick=()=>csv(c.period_materials.filter(m=>m.missing).map(m=>[c.character_name,c.name,piHours,m.name,m.required,m.on_planet,m.usable,m.missing]),['Karakter','Bolygó','Óra','Anyag','Szükséges','Bolygón','Felhasználható','Fedezeti hiány'],'pi-ellatasi-hiany');
  $$('[data-pi-factory]').forEach(el=>el.onclick=()=>{piFactory=Number(el.dataset.piFactory);renderPIFactory(c);$('#pi-factory-detail').scrollIntoView({block:'nearest',behavior:'smooth'});});
  renderPIFactory(c);
}
function renderPIFactory(colony){
  const target=$('#pi-factory-detail'),f=colony.factories.find(f=>f.id===piFactory);
  if(!target)return;if(!f){target.innerHTML='';return;}
  target.innerHTML=`<div class="pi-factory-box"><h3>${itemName(f.product)} · ${f.id} · bemenetek</h3>${table(['Anyag','Egy ciklushoz','Saját gyári puffer','Utánpótlási forrás'],f.inputs.map(m=>`<tr><td>${itemName(m.name)}</td><td class="num">${fmt(m.per_cycle)}</td><td class="num">${fmt(m.buffer)}</td><td>${m.suppliers.length?'Kitermelő / másik gyár: '+m.suppliers.map(esc).join(', '):'Tárolt készletből, a beállított útvonalakon'}</td></tr>`))}<p class="footnote">Kimenet ciklusonként: ${f.outputs.map(o=>`${itemName(o.name)} ${fmt(o.per_cycle)} db`).join(', ')}. A közös raktárak fedezetét az összes gyárral együtt, a bolygó anyagösszesítőjében ellenőrizzük.</p></div>`;
}
