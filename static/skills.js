'use strict';
let skillData=null,skillRequest=null,skillTimer=null,skillSelectedId=null,skillTab='queue',skillFilter='',skillShowCompleted=false;
const skillLevel=n=>n==null?'–':['0','I','II','III','IV','V'][n]||String(n);
const skillDate=n=>n==null?'–':EveI18n.date(n*1000,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
function skillDuration(seconds){
  if(seconds==null)return '–';
  const minutes=Math.max(0,Math.ceil(seconds/60)),days=Math.floor(minutes/1440),hours=Math.floor(minutes%1440/60);
  return days?`${days} nap ${hours} óra`:hours?`${hours} óra ${minutes%60} perc`:`${minutes} perc`;
}
async function refreshSkills(auto=false){
  if(skillRequest)return skillRequest;
  clearTimeout(skillTimer);
  skillRequest=api('/api/skills');
  let shouldSync=false;
  try{
    skillData=await skillRequest;
    const alerts=skillData.summary.idle+skillData.summary.soon;
    $('#skill-count').textContent=alerts?fmt(alerts):skillData.summary.unknown?'?':'0';
    $('#skill-count').title=`Nem tanul: ${skillData.summary.idle}; 5 napon belül leáll: ${skillData.summary.soon}; ismeretlen: ${skillData.summary.unknown}`;
    shouldSync=auto&&!state.task.running&&skillData.characters.some(c=>!c.needs_auth&&(!c.skills_as_of||c.stale));
    if(view==='skills')render();
  }catch(e){if(view==='skills'){error(e.message);$('#view-content').innerHTML=empty('A skilladatok nem olvashatók','Próbáld újra a Skilladatok frissítése gombbal.');}}
  finally{skillRequest=null;}
  if(shouldSync&&view==='skills')void startTask('/api/skills/sync');
}
function renderSkills(content){
  setHead('MINDEN KARAKTER','Skillek és tanulási sor','Minden hozzáadott karakter, a gyártási karakter- és helyszűréstől függetlenül. Figyelmeztetés: nem tanul, vagy 120 órán belül megszakad a tanulás.');
  $('#plan-status').hidden=true;
  actions(`<button class="button primary compact" id="skills-sync" ${state.task.running?'disabled':''}>↻ Skilladatok frissítése</button>`);
  $('#skills-sync').onclick=()=>startTask('/api/skills/sync');
  if(!skillData){content.innerHTML=empty('Skilladatok betöltése','A helyben tárolt adatokat ellenőrizzük…');void refreshSkills(true);return;}
  const chars=skillData.characters,s=skillData.summary;
  if(!chars.length){content.innerHTML=empty('Még nincs hozzáadott karakter','Az EVE-kapcsolat oldalon add hozzá a karaktereidet, majd frissítsd a skilladatokat.');return;}
  if(!chars.some(c=>c.id===skillSelectedId))skillSelectedId=chars[0].id;
  const label=c=>`<span class="badge skill-${c.status}">${esc(c.label)}</span>`;
  content.innerHTML=`<div class="metrics"><div class="metric"><div class="metric-label">Karakterek</div><strong>${fmt(chars.length)}</strong><small>${fmt(s.training)} rendben tanul</small></div><div class="metric"><div class="metric-label">Nem tanul</div><strong class="danger">${fmt(s.idle)}</strong><small>karakter</small></div><div class="metric"><div class="metric-label">5 napon belül leáll</div><strong class="warning-text">${fmt(s.soon)}</strong><small>karakter</small></div><div class="metric"><div class="metric-label">Nem ellenőrizhető</div><strong>${fmt(s.unknown)}</strong><small>karakter</small></div></div>`;
  if(chars.some(c=>c.needs_auth))content.innerHTML+=`<details class="panel skill-permissions" ${chars.every(c=>c.needs_auth)?'open':''}><summary>Új olvasási jogosultságok szükségesek a skilladatokhoz</summary><div class="panel-body"><p>Az <a href="https://developers.eveonline.com/applications" target="_blank" rel="noopener noreferrer">EVE Developer alkalmazásoldalán</a> szerkeszd a meglévő EVE Műhely alkalmazást, és a korábbi három mellé add hozzá ezt a két jogosultságot:</p><code>${(state.skill_scopes||[]).map(esc).join('\n')}</code><p>Ezután karakterenként kattints a <strong>Skillek engedélyezése</strong> gombra, és az EVE hivatalos oldalán ugyanazt a karaktert válaszd. A mentett terveket és a meglévő ipari hozzáférést megőrizzük. Client Secretet nem kell megadni.</p></div></details>`;
  const rows=chars.map(c=>`<tr class="skill-character skill-state-${c.status}"><td data-filter-value="${esc(c.name)}"><button class="text-button skill-character-name" data-skill-character="${c.id}" aria-label="${esc(c.name)} – Skillek és tanulási sor">${esc(c.name)}</button><div class="batch-note">${c.id}</div></td><td>${label(c)}${c.error?`<div class="skill-error">${esc(c.error)}</div>`:''}</td><td>${c.current?`${itemName(c.current.name)} ${skillLevel(c.current.level)}<div class="batch-note">Befejezés: ${esc(skillDate(c.current.finish))}</div>`:'–'}</td><td data-sort-value="${c.stops_at??''}">${c.stops_at?`${esc(skillDate(c.stops_at))}<div class="batch-note">${esc(skillDuration(c.seconds_left))}${c.gap?' · megszakadás':''}</div>`:c.status==='idle'?'Most nem tanul':'–'}${c.status==='unknown'&&c.stops_at?'<div class="batch-note">Korábbi sor alapján</div>':''}</td><td class="num">${c.queue_as_of==null?'–':fmt(c.queue_count)}</td><td class="num">${c.total_sp==null?'–':fmt(c.total_sp)}<div class="batch-note">SP</div></td><td><button class="button compact" data-skill-character="${c.id}" aria-label="${esc(c.name)} – Részletek">Részletek</button>${c.needs_auth?`<button class="text-button" data-skill-auth="${c.id}" aria-label="${esc(c.name)} – Skillek engedélyezése">Skillek engedélyezése</button>`:''}<div class="batch-note">Adat: ${esc(skillDate(c.queue_as_of))}</div></td></tr>`);
  content.innerHTML+=panel('Karakterek tanulási állapota','Piros: nem tanul · Sárga: 5 napon belül leáll · Szürke: nem ellenőrizhető',table(['Karakter','Állapot','Aktuális tanulás','Folyamatos tanulás vége','Sorban','Skillpont','Művelet'],rows,'skill-overview'));
  content.innerHTML+='<p class="footnote">A jelzés a jelenleg betöltött sorból számolt első megszakadásra vonatkozik, nem csak a legutolsó sorvégre. Lejárt vagy hibás adatból nem állítjuk, hogy a karakter biztosan nem tanul. Az 5 percnél régebben ellenőrzött adatok elavultnak számítanak. Nyitott, előtérben lévő nézetnél percenként frissítjük az engedélyezett karakterek adatait; bezárt alkalmazás mellett nincs figyelés.</p><div id="skill-detail"></div>';
  $$('[data-skill-character]').forEach(el=>el.onclick=()=>{skillSelectedId=Number(el.dataset.skillCharacter);skillFilter='';renderSkillDetail();$('#skill-detail').scrollIntoView({block:'start',behavior:'smooth'});});
  $$('[data-skill-auth]').forEach(el=>el.onclick=async()=>{
    try{el.disabled=true;error('');const auth=await api('/api/auth/start',{character_id:Number(el.dataset.skillAuth),feature:'skills'});sessionStorage.setItem('eve-muhely-auth-return','skills');window.location.assign(auth.url);}
    catch(e){error(e.message);el.disabled=false;}
  });
  renderSkillDetail();
  clearTimeout(skillTimer);
  skillTimer=setTimeout(()=>{
    if(view!=='skills')return;
    if(!document.hidden&&!state.task.running&&skillData.characters.some(c=>!c.needs_auth))void startTask('/api/skills/sync');
    else void refreshSkills();
  },60000);
}
function renderSkillDetail(){
  const target=$('#skill-detail'),c=skillData?.characters.find(c=>c.id===skillSelectedId);
  if(!target||!c)return;
  const labels={training:'Éppen tanulja',scheduled:'Sorban',paused:'Szünetel / nincs időzítés',completed:'Befejezve',uncertain:'Időzítés nem ismert'};
  const tabs=`<div class="skill-tabs"><button class="button compact" id="skill-queue-tab" aria-pressed="${skillTab==='queue'}">Tanulási sor (${c.queue_as_of==null?'–':fmt(c.queue_count)})</button><button class="button compact" id="skill-trained-tab" aria-pressed="${skillTab==='trained'}">Összes skill (${c.skills_as_of==null?'–':fmt(c.skills.length)})</button></div>`;
  let body=tabs;
  if(c.status==='unknown')body+=`<div class="banner warn">${esc(c.label)}. ${c.skills_as_of?'Az alábbi adatok a korábbi pillanatképből származnak.':'Az engedélyezés és az első sikeres frissítés után itt jelennek meg az adatok.'}</div>`;
  body+=`<div class="skill-detail-summary"><span>Skillpont: <strong>${c.total_sp==null?'–':fmt(c.total_sp)}</strong></span><span>Szabad SP: <strong>${c.unallocated_sp==null?'–':fmt(c.unallocated_sp)}</strong></span><span>Sor utolsó ismert vége: <strong>${esc(skillDate(c.queue_end))}</strong></span></div>`;
  if(skillTab==='queue'){
    body+=`<div class="skill-filter"><label><input type="checkbox" id="skill-completed" ${skillShowCompleted?'checked':''}> Befejezett sorok megjelenítése (${fmt(c.completed_count)})</label></div>`;
    const entries=c.queue.filter(e=>skillShowCompleted||e.phase!=='completed');
    body+=entries.length?table(['Sorrend','Skill','Célszint','Állapot','Kezdés','Befejezés','Befejezésig'],entries.map(e=>`<tr class="${e.phase==='training'?'skill-queue-current':''}"><td>${e.position+1}</td><td>${itemName(e.name)}<div class="batch-note">${e.id}</div></td><td data-sort-value="${e.level??''}">${skillLevel(e.level)}</td><td><span class="badge ${e.phase==='training'?'good':''}">${esc(labels[e.phase])}</span></td><td data-sort-value="${e.start??''}">${esc(skillDate(e.start))}</td><td data-sort-value="${e.finish??''}">${esc(skillDate(e.finish))}</td><td data-sort-value="${e.phase==='completed'?'':e.seconds_left??''}">${e.phase==='completed'?'–':esc(skillDuration(e.seconds_left))}</td></tr>`)):
      empty(c.skills_as_of?'Nincs hátralévő tanulás a betöltött sorban':'Még nincs betöltött tanulási sor',c.needs_auth?'Előbb engedélyezd a skilladatok olvasását, majd frissíts.':'A friss, üres sor azt jelenti, hogy a karakter nem tanul.');
  }else{
    body+=`<div class="skill-filter"><input id="skill-filter" type="search" aria-label="Skillek szűrése" placeholder="Skill neve vagy azonosítója…" value="${esc(skillFilter)}"><span class="muted">Tanult és jelenleg aktív szint külön</span></div>`;
    body+=c.skills.length?table(['Skill','Tanult szint','Aktív szint','Skillpont','Megjegyzés'],c.skills.map(s=>`<tr data-skill-search="${esc((s.name+' '+s.id).toLowerCase())}"><td>${itemName(s.name)}<div class="batch-note">${s.id}</div></td><td data-sort-value="${s.trained_level??''}">${skillLevel(s.trained_level)}</td><td data-sort-value="${s.active_level??''}">${skillLevel(s.active_level)}</td><td class="num">${fmt(s.sp)}</td><td>${s.queue_adjusted?'Befejezett sorból frissítve; aktív szint az ESI-ből':s.active_level!==s.trained_level?'Az aktív szint eltér a tanulttól':'–'}</td></tr>`)):
      empty('Még nincs betöltött skilllista','Engedélyezd a skilladatokat, és indíts frissítést.');
    body+='<p class="footnote">A már befejezett, de az EVE skilllistájában még át nem vezetett szinteket a tanulási sor alapján hozzáadjuk a tanult szinthez és az ismert skillpontokhoz. Az aktív szintet külön, az EVE adata alapján mutatjuk; az Alpha/Omega állapotát nem találgatjuk.</p>';
  }
  target.innerHTML=panel({name:c.name,suffix:' – skillek és sor'},`Skilladat: ${skillDate(c.skills_as_of)} · Sor: ${skillDate(c.queue_as_of)}`,`<div class="skill-detail-body">${body}</div>`);
  $('#skill-queue-tab').onclick=()=>{skillTab='queue';renderSkillDetail();};
  $('#skill-trained-tab').onclick=()=>{skillTab='trained';renderSkillDetail();};
  if($('#skill-completed'))$('#skill-completed').onchange=e=>{skillShowCompleted=e.target.checked;renderSkillDetail();};
  if($('#skill-filter')){
    const filter=()=>EveTables.setSearch(target.querySelector('table'),skillFilter,'skillSearch');
    $('#skill-filter').oninput=e=>{skillFilter=e.target.value;filter();};filter();
  }
}
