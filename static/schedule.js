'use strict';
let scheduleResult=null,scheduleRequest=null,scheduleRevision=0,schedulePage=0,scheduleSelected=null,scheduleCharacter=null,scheduleTablePages={reaction:0,manufacturing:0},scheduleOptions={owned_only:true,transfer_blueprints:false,characters:null,start:'',supply_at:'',min_job_hours:12};
try{Object.assign(scheduleOptions,JSON.parse(localStorage.getItem('eve-muhely-schedule-options')||'{}'));}catch{}
if(typeof scheduleOptions.min_job_hours!=='number'||!Number.isFinite(scheduleOptions.min_job_hours)||scheduleOptions.min_job_hours<0||scheduleOptions.min_job_hours>720)scheduleOptions.min_job_hours=12;
if(!Array.isArray(scheduleOptions.characters))scheduleOptions.characters=null;
for(const key of ['start','supply_at'])if(typeof scheduleOptions[key]!=='string')scheduleOptions[key]='';
// Timeline span is a local display preference, separate from job scheduling.
let scheduleTimelineDays=EveScheduleGraph.DEFAULT_DAYS,scheduleWindow=0;
try{const saved=JSON.parse(localStorage.getItem('eve-muhely-schedule-timeline')||'{}');if(EveScheduleGraph.validDays(saved.days))scheduleTimelineDays=saved.days;}catch{}
const scheduleViewport=()=>({days:scheduleTimelineDays,window:scheduleWindow});
function saveScheduleTimeline(){try{localStorage.setItem('eve-muhely-schedule-timeline',JSON.stringify({days:scheduleTimelineDays}));}catch{}}
const scheduleKey=()=>JSON.stringify([productId,targetQuantity(),corporationId,activePlanId,scheduleRevision]);
const scheduleTime=n=>n?EveI18n.date(n*1000,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'–';
function readScheduleOptions(){
  const form=$('#schedule-form');
  scheduleOptions={owned_only:form.elements.owned_only.checked,transfer_blueprints:form.elements.transfer_blueprints.checked,
    characters:$$('[data-schedule-character]:checked').map(input=>Number(input.dataset.scheduleCharacter)),start:form.elements.start.value,supply_at:form.elements.supply_at.value,min_job_hours:Number(form.elements.min_job_hours.value)};
  try{localStorage.setItem('eve-muhely-schedule-options',JSON.stringify(scheduleOptions));}catch{}
  return scheduleOptions;
}
function renderSchedule(content){
  setHead('PÁRHUZAMOS GYÁRTÁS','Gyártásütemező','Karakterenkénti gyártási és reakciós slotok, aktív skillek, anyagérkezés és egyedi blueprintek alapján.');
  $('#plan-status').hidden=true;
  if(scheduleResult?.key!==scheduleKey()){scheduleResult=null;schedulePage=0;scheduleSelected=null;scheduleCharacter=null;scheduleWindow=0;scheduleTablePages={reaction:0,manufacturing:0};}
  const chars=state.production_characters||[];
  content.innerHTML=`<div class="schedule-setup"><div id="schedule-plan-slot"></div><form id="schedule-form" class="panel panel-body"><div class="schedule-options"><label class="schedule-flag"><input type="checkbox" name="owned_only" ${scheduleOptions.owned_only?'checked':''}> Csak a meglévő BPO/BPC készlettel</label><label class="schedule-flag"><input type="checkbox" name="transfer_blueprints" ${scheduleOptions.transfer_blueprints?'checked':''} ${corporationId?'disabled':''}> Személyes blueprintek átadhatók a karakterek között</label><label>Kezdés · üresen most<input type="datetime-local" name="start" value="${esc(scheduleOptions.start||'')}"></label><label>Beszerzendő anyagok és új blueprintek érkezése<input type="datetime-local" name="supply_at" value="${esc(scheduleOptions.supply_at||'')}"></label><label>Minimum jobhossz (óra)<input type="number" name="min_job_hours" min="0" max="720" step="any" required value="${scheduleOptions.min_job_hours}"></label></div><h3>Bevonható karakterek</h3><div class="schedule-characters">${chars.map(c=>`<label><input type="checkbox" data-schedule-character="${c.id}" ${scheduleOptions.characters===null||scheduleOptions.characters.includes(c.id)?'checked':''}> ${verbatim(c.name)}${!c.available?' · <span>Nincs skilladat</span>':''}</label>`).join('')||'<p>Még nincs hozzáadott karakter.</p>'}</div><details class="schedule-help"><summary>Ütemezési tudnivalók</summary><p class="footnote">A minimum a Run/job felosztást is növelheti. A hiányzó mennyiség vagy a blueprint korlátja miatt rövidebb job megmaradhat; nem gyártunk többletet. A jobok közé nem kerül várakozás. 0: nincs minimum.</p><p class="footnote">A dátumok helyi időben értendők. Üres anyagérkezés: a kezdés ideje. A személyes és corp készlet elkülönül; corp tervhez csak annak tagkaraktereit használjuk. A tanulási hely nem korlátozza az industry slotokat.</p></details><button class="button primary" type="submit" ${!productId||scheduleRequest?'disabled':''}>${scheduleRequest?'Ütemezés készül…':'Ütemterv kiszámítása'}</button></form></div><div id="schedule-result"></div>`;
  const selector=$('.plan-selector');if(selector)$('#schedule-plan-slot').replaceWith(selector);
  $('#schedule-form').oninput=readScheduleOptions;
  $('#schedule-form').onsubmit=async event=>{
    event.preventDefault();if(!productId||scheduleRequest)return;
    const opts=readScheduleOptions(),key=scheduleKey(),body={product_id:productId,quantity:targetQuantity(),corporation_id:corporationId,saved_plan_id:activePlanId,
      characters:opts.characters,owned_only:opts.owned_only,transfer_blueprints:opts.transfer_blueprints,min_job_hours:opts.min_job_hours};
    for(const field of ['start','supply_at'])if(opts[field])body[field]=new Date(opts[field]).getTime()/1000;
    scheduleRequest=api('/api/schedule',body);render();
    try{const data=await scheduleRequest;if(key===scheduleKey()){scheduleResult={key,data};schedulePage=0;scheduleSelected=null;scheduleCharacter=null;scheduleWindow=0;scheduleTablePages={reaction:0,manufacturing:0};}}
    catch(e){error(e.message);}finally{scheduleRequest=null;if(view==='schedule')render();}
  };
  if(scheduleResult)renderScheduleResult($('#schedule-result'),scheduleResult.data);
}
function renderScheduleResult(target,data){
  target.innerHTML=`<div class="banner ${data.complete?'':'warn'}"><strong>${data.complete?'Teljes ütemterv':'Részleges ütemterv · hiányzó feltételek'}</strong><p>Az ütemező a rövidebb átfutásra törekszik, heurisztikus módszerrel. Nem garantál matematikailag optimális megoldást. Az alábbi jobok kézzel indíthatók; az app nem indít EVE-jobot.</p></div><div class="metrics"><div class="metric"><div class="metric-label">Ütemezett jobok</div><strong>${fmt(data.jobs.length)}</strong></div><div class="metric"><div class="metric-label">Ütemezett runok</div><strong>${fmt(data.runs)}</strong></div><div class="metric"><div class="metric-label">Várható befejezés</div><strong class="schedule-date">${scheduleTime(data.finish)}</strong></div><div class="metric"><div class="metric-label">Átfutás · óra</div><strong>${data.complete?hours(data.seconds):'–'}</strong></div></div>`;
  if(data.blueprint_shortages.length)target.innerHTML+=panel('Szükséges további blueprintek','A kiszámított ütemtervhez; a jelzett run/BPC feltételezéssel',table(['Blueprint','Típus','További példány','Szükséges BPC-run','Run/BPC feltételezés'],data.blueprint_shortages.map(b=>`<tr><td>${itemName(b.name)}</td><td>${b.category==='Reakcióformula'?'Reakcióformula':'BPC'}</td><td class="num">${fmt(b.copies)}</td><td class="num">${b.category==='Reakcióformula'?'–':fmt(b.runs)}</td><td class="num">${b.category==='Reakcióformula'?'–':fmt(b.copy_runs)}</td></tr>`)));
  if(data.blocked.length||data.material_warnings.length)target.innerHTML+=panel('Nem ütemezhető tételek','Ezek miatt a teljes terv befejezése nem állapítható meg',table(['Termék','Hátralévő run','Ok'],[...data.blocked,...data.material_warnings].map(b=>`<tr><td>${itemName(b.name)}</td><td>${b.runs==null?'–':fmt(b.runs)}</td><td>${esc(b.reason)}</td></tr>`)));
  target.innerHTML+=panel('Karakterek ipari kapacitása','Az aktív skillek szerinti slotkeret',table(['Karakter','Gyártási slot','Reakciós slot','Skilladat ideje','Jobadat ideje','Állapot'],data.workers.map(w=>`<tr><td>${verbatim(w.name)}</td><td>${w.capacity.manufacturing}</td><td>${w.capacity.reaction}</td><td>${date(w.as_of)}</td><td>${date(w.jobs_as_of)}</td><td>${esc(w.excluded|| (w.stale?'Korábbi skilladatok':'Bevonható'))}</td></tr>`)));
  target.innerHTML+=scheduleGraphMarkup(data);
  target.innerHTML+=`<div class="section-actions"><button id="schedule-csv" class="button compact">Ütemterv CSV mentése</button></div>`;
  for(const activity of ['reaction','manufacturing'])target.innerHTML+=scheduleActivityTable(data,activity);
  const materials=data.material_shortfall.filter(r=>!r.is_blueprint&&r.unit!=='run'&&r.category!=='Reakcióformula');
  target.innerHTML+=panel('Ütemezés anyaghiánya','Az ütemezett jobfelosztás szerint újraszámolva',`<div class="panel-body"><button class="button compact" id="schedule-copy-materials">Multibuy másolása</button></div>`+table(['Anyag','Beszerzendő'],materials.map(m=>`<tr><td>${itemName(m.name)}</td><td class="num">${fmt(m.buy)}</td></tr>`)));
  bindScheduleGraph(target,data);
  updateRunningJobMarkers(data,target);
  target.querySelectorAll('[data-schedule-table-page]').forEach(button=>button.onclick=()=>{
    scheduleTablePages[button.dataset.activity]+=Number(button.dataset.scheduleTablePage);renderScheduleResult(target,data);
  });
  $('#schedule-copy-materials').onclick=async()=>{try{await navigator.clipboard.writeText(EveMultibuy.text(materials));toast('Multibuy lista másolva.');}catch{error('A másolás nem sikerült.');}};
  $('#schedule-csv').onclick=()=>csv(data.jobs.map(j=>[j.name,j.character_name,j.activity,j.slot,j.runs,j.output,new Date(j.start*1000).toISOString(),new Date(j.end*1000).toISOString(),j.blueprint_item_id||'',j.procure_blueprint,j.me,j.te]),['Termék','Karakter','Művelet','Slot','Run','Kimenet','Kezdés UTC','Befejezés UTC','Blueprint Item ID','Beszerzendő blueprint','ME','TE'],'utemterv');
}

function scheduleActivityTable(data,activity){
  const jobs=data.jobs.filter(j=>j.activity===activity),pages=Math.max(1,Math.ceil(jobs.length/100));
  const page=scheduleTablePages[activity]=Math.min(scheduleTablePages[activity],pages-1);
  const title=activity==='reaction'?'Reakciók ütemterve':'Gyártás ütemterve';
  const controls=`<div class="panel-body schedule-paging"><button class="button compact" data-schedule-table-page="-1" data-activity="${activity}" ${page===0?'disabled':''}>←</button><span>${page+1} / ${pages}</span><button class="button compact" data-schedule-table-page="1" data-activity="${activity}" ${page+1===pages?'disabled':''}>→</button><span>100 job / oldal</span></div>`;
  return panel(title,'Külön slotkeret · a másik tevékenységgel párhuzamosan futhat',controls+table(['Job','Termék','Karakter','Slot','Run','Kimenet','Anyagok rendelkezésre állnak','Kezdés','Befejezés','Blueprint Item ID','Blueprint forrás','ME / TE'],jobs.slice(page*100,(page+1)*100).map(j=>`<tr><td><button class="text-button" data-schedule-select="${j.id}">#${j.id}</button></td><td>${itemName(j.name)}</td><td>${verbatim(j.character_name)}</td><td>${j.slot}</td><td>${fmt(j.runs)}</td><td>${fmt(j.output)}</td><td data-sort-value="${j.materials_ready}">${scheduleTime(j.materials_ready)}</td><td data-sort-value="${j.start}">${scheduleTime(j.start)}</td><td data-sort-value="${j.end}">${scheduleTime(j.end)}${j.below_minimum?'<div class="batch-note">Minimum alatti · maradék / BP-korlát</div>':''}</td><td>${j.blueprint_item_id??'–'}</td><td><span>${j.procure_blueprint?'Beszerzendő / másolandó':j.transfer_required?'Átadás szükséges':'Meglévő'}</span> · <span data-i18n-skip>${j.blueprint_kind}</span></td><td>${j.me} / ${j.te}</td></tr>`),'schedule-'+activity));
}
function runningJobState(job,now=Date.now()/1000){
  if(now>=job.end)return {label:'Várhatóan elkészült',style:'ready',progress:100};
  return {label:job.stale?'Folyamatban · korábbi EVE-adat':'Folyamatban az EVE-ben',style:job.stale?'stale':'running',progress:Math.max(0,Math.min(100,(now-job.start)/(job.end-job.start)*100))};
}
function scheduleJobTitle(job){
  const status=job.existing?' · '+EveI18n.t(runningJobState(job).label):'';
  return (job.existing?'EVE #'+job.eve_job_id:'#'+job.id)+' '+job.name+' · '+job.runs+' run · '+EveI18n.t(scheduleTime(job.start))+' – '+EveI18n.t(scheduleTime(job.end))+status;
}
function runningJobDetail(job){
  return `<h3>EVE #${job.eve_job_id} · ${itemName(job.name)}</h3><p><span class="badge good" data-running-status="${job.id}">${runningJobState(job).label}</span> · ${verbatim(job.character_name)}</p><div class="running-job-progress"><progress max="100" value="${runningJobState(job).progress}" data-running-progress="${job.id}" aria-label="Gyártás előrehaladása"></progress><span data-running-percent="${job.id}">${Math.floor(runningJobState(job).progress)}%</span></div><p><span>Kezdés</span>: ${scheduleTime(job.start)} · <span>Befejezés</span>: ${scheduleTime(job.end)} · ${fmt(job.runs)} run · ${fmt(job.output)} <span>db</span></p><p class="footnote"><span>EVE-jobadat ideje</span>: ${date(job.observed_at)}. <span>A zöld jelölés a betöltött EVE-jobadatból származik. A tervezett jobokat az idő múlása nem indítja el.</span></p>`;
}
function updateRunningJobMarkers(data=scheduleResult?.data,target=document.querySelector('#schedule-result')){
  if(!data||!target)return;
  const graph=EveScheduleGraph.build(data,schedulePage,scheduleCharacter,scheduleViewport());
  target.querySelectorAll('.schedule-tick').forEach((el,i)=>{if(graph.ticks[i])el.textContent=EveI18n.t(scheduleTime(graph.ticks[i].time));});
  const range=target.querySelector('.schedule-window-range');if(range)range.textContent=EveI18n.t(scheduleTime(graph.start))+' — '+EveI18n.t(scheduleTime(graph.end));
  for(const job of data.running_jobs||[]){
    const status=runningJobState(job);
    const node=target.querySelector(`.schedule-job[data-schedule-select="${job.id}"]`);
    if(node){node.classList.toggle('existing-ready',status.style==='ready');node.classList.toggle('existing-stale',status.style==='stale');node.setAttribute('aria-label',scheduleJobTitle(job));node.querySelector('title').textContent=scheduleJobTitle(job);}
    target.querySelectorAll(`[data-running-status="${job.id}"]`).forEach(el=>{el.textContent=status.label;el.classList.toggle('good',status.style==='running');el.classList.toggle('warn',status.style!=='running');});
    target.querySelectorAll(`[data-running-progress="${job.id}"]`).forEach(el=>el.value=status.progress);
    target.querySelectorAll(`[data-running-percent="${job.id}"]`).forEach(el=>el.textContent=Math.floor(status.progress)+'%');
  }
}
setInterval(()=>{if(typeof view!=='undefined'&&view==='schedule')updateRunningJobMarkers();},30000);
window.addEventListener('eve-language-change',()=>{if(typeof view!=='undefined'&&view==='schedule')updateRunningJobMarkers();});
function scheduleGraphMarkup(data){
  const characters=[...new Map(EveScheduleGraph.allJobs(data).map(j=>[j.character_id,{id:j.character_id,name:j.character_name}])).values()].sort((a,b)=>a.name.localeCompare(b.name,EveI18n.locale));
  if(scheduleCharacter!==null&&!characters.some(c=>c.id===scheduleCharacter))scheduleCharacter=null;
  const filtered=EveScheduleGraph.visibleJobs(data,scheduleCharacter,scheduleViewport());
  if(!filtered.some(j=>j.id===scheduleSelected))scheduleSelected=filtered.length?filtered.reduce((last,j)=>j.end>=last.end?j:last).id:null;
  const graph=EveScheduleGraph.build(data,schedulePage,scheduleCharacter,scheduleViewport());schedulePage=graph.page;scheduleWindow=graph.window;
  const selected=EveScheduleGraph.allJobs(data).find(j=>j.id===scheduleSelected);
  const sourceNames={stock:'Készlet',wip:'Folyamatban lévő job',purchase:'Beszerzés',job:'Ütemezett job'};
  const consumers=selected?data.jobs.filter(j=>(j.dependencies||[]).some(d=>d.job_id===selected.id)):[];
  const downstream=consumers.length?`<h3>Kimenetet felhasználó jobok</h3><div class="schedule-paging">${consumers.map(j=>`<button class="button compact" data-schedule-select="${j.id}" data-i18n-skip>#${j.id} · <span data-copy-item="${esc(j.name)}">${esc(j.name)}</span></button>`).join('')}</div>`:'';
  const detail=selected?.existing?runningJobDetail(selected):selected?`<h3>#${selected.id} · ${itemName(selected.name)}</h3><p><span>Anyagok rendelkezésre állnak</span>: ${scheduleTime(selected.materials_ready)} · <span>Kezdés</span>: ${scheduleTime(selected.start)}</p>`+table(['Anyag','Mennyiség','Forrás','Érkezés'],selected.materials.flatMap(m=>m.allocations.map(a=>`<tr><td>${itemName(m.name)}</td><td class="num">${fmt(a.quantity)}</td><td><span>${sourceNames[a.source]}</span>${a.job_id?` <button class="text-button" data-schedule-select="${a.job_id}">#${a.job_id}</button>`:''}</td><td data-sort-value="${a.available_at}">${scheduleTime(a.available_at)}</td></tr>`))):'<p>Válassz egy jobot az anyagforrások és függőségek megtekintéséhez.</p>';
  return panel('Ütemezési gráf és idővonal','Közös időtengely · reakció és gyártás külön sávokon',`<div class="panel-body"><div class="schedule-paging"><label for="schedule-character-filter"><span>Karakter</span><select id="schedule-character-filter"><option value="">Összes karakter</option>${characters.map(c=>`<option value="${c.id}" ${c.id===scheduleCharacter?'selected':''} data-i18n-skip>${esc(c.name)}</option>`).join('')}</select></label><label for="schedule-timeline-days"><span>Látható napok</span><input id="schedule-timeline-days" type="number" min="1" max="3650" step="1" placeholder="Teljes időtáv" value="${scheduleTimelineDays??''}" aria-describedby="schedule-timeline-help"></label><button class="button compact" id="schedule-timeline-full" ${scheduleTimelineDays===null?'disabled':''}>Teljes időtáv</button></div><div class="schedule-paging"><button class="button compact" id="schedule-window-prev" ${graph.window===0?'disabled':''}>← Előző időszak</button><span>${graph.window+1} / ${graph.windows} <span>időszak</span></span><button class="button compact" id="schedule-window-next" ${graph.window+1===graph.windows?'disabled':''}>Következő időszak →</button><span class="schedule-window-range" data-i18n-skip>${esc(EveI18n.t(scheduleTime(graph.start)))} — ${esc(EveI18n.t(scheduleTime(graph.end)))}</span></div><p class="footnote" id="schedule-timeline-help">A napok száma csak az idővonalat nagyítja. Üresen a teljes időtáv látszik; az időszakgombokkal léphetsz előre és hátra.</p><div class="schedule-paging"><button class="button compact" id="schedule-graph-prev" ${graph.page===0?'disabled':''}>←</button><span>${graph.page+1} / ${graph.pages}</span><button class="button compact" id="schedule-graph-next" ${graph.page+1===graph.pages?'disabled':''}>→</button><span>100 job / oldal</span><span>${graph.total_jobs} <span>job az időszakban</span></span><span class="schedule-legend reaction">Reakció</span><span class="schedule-legend manufacturing">Gyártás</span>${data.running_jobs?.length?'<span class="schedule-legend running">Folyamatban az EVE-ben</span>':''}</div>${!graph.total_jobs?'<p class="footnote">Ebben az időszakban nincs ütemezett job.</p>':''}</div><div class="schedule-timeline"><svg width="${graph.width}" height="${graph.height}" role="group" aria-label="${esc(EveI18n.t('Ütemezési gráf és idővonal'))}">${graph.ticks.map(t=>`<line class="schedule-grid" x1="${t.x}" x2="${t.x}" y1="40" y2="${graph.height-10}"/><text class="schedule-tick" x="${t.x}" y="24" text-anchor="${t.x===graph.left?'start':t.x===graph.ticks[4].x?'end':'middle'}" data-i18n-skip>${esc(EveI18n.t(scheduleTime(t.time)))}</text>`).join('')}${graph.lanes.map(l=>`<text class="schedule-lane" x="12" y="${l.y+17}"><title data-i18n-skip>${esc(l.name)}</title><tspan>${l.existing?'EVE':l.activity==='reaction'?'Reakció':'Gyártás'}</tspan><tspan data-i18n-skip> · ${esc(l.name.slice(0,19))} · ${l.slot}</tspan></text>`).join('')}${graph.nodes.map(j=>`<g class="schedule-job ${j.activity}${j.existing?' existing':''}${selected?.id===j.id?' selected':''}" data-schedule-select="${j.id}" data-copy-item="${esc(j.name)}" tabindex="0" role="button" aria-pressed="${selected?.id===j.id}" aria-label="${esc(scheduleJobTitle(j))}"><title data-i18n-skip>${esc(scheduleJobTitle(j))}</title><rect x="${j.x}" y="${j.y}" width="${j.width}" height="25" rx="4"/>${j.continues_before&&j.width>12?`<path class="schedule-continuation" d="M ${j.x+3} ${j.y+5} v 15"/>`:''}${j.continues_after&&j.width>12?`<path class="schedule-continuation" d="M ${j.x+j.width-3} ${j.y+5} v 15"/>`:''}${j.width>45?`<text x="${j.x+(j.continues_before?12:5)}" y="${j.y+17}" data-i18n-skip>${esc(((j.existing?'EVE · ':'#'+j.id+' ')+j.name).slice(0,Math.floor((j.width-(j.continues_before?17:10)-(j.continues_after?7:0))/7)))}</text>`:''}</g>`).join('')}</svg></div><div class="panel-body" id="schedule-job-detail">${detail}${downstream}</div>`);
}
function bindScheduleGraph(target,data){
  const redraw=()=>{const positions=['.schedule-timeline'].map(selector=>{const el=target.querySelector(selector);return [selector,el?.scrollLeft||0,el?.scrollTop||0];});renderScheduleResult(target,data);for(const [selector,left,top] of positions){const el=target.querySelector(selector);if(el){el.scrollLeft=left;el.scrollTop=top;}}};
  $('#schedule-timeline-days').onchange=event=>{
    const field=event.target,value=field.value.trim(),days=value===''?null:Number(value);
    if(!field.validity.valid||!EveScheduleGraph.validDays(days)){
      field.setCustomValidity(EveI18n.t('A látható napok száma 1 és 3650 közötti egész szám lehet.'));field.reportValidity();return;
    }
    field.setCustomValidity('');
    const previous=EveScheduleGraph.range(data,scheduleViewport());scheduleTimelineDays=days;
    scheduleWindow=days?Math.floor((previous.start-previous.fullStart)/(days*EveScheduleGraph.DAY)):0;
    schedulePage=0;saveScheduleTimeline();redraw();
  };
  $('#schedule-timeline-days').oninput=event=>event.target.setCustomValidity('');
  $('#schedule-timeline-full').onclick=()=>{scheduleTimelineDays=null;scheduleWindow=0;schedulePage=0;saveScheduleTimeline();redraw();};
  $('#schedule-window-prev').onclick=()=>{scheduleWindow--;schedulePage=0;redraw();};
  $('#schedule-window-next').onclick=()=>{scheduleWindow++;schedulePage=0;redraw();};
  $('#schedule-character-filter').onchange=event=>{
    scheduleCharacter=event.target.value?Number(event.target.value):null;schedulePage=0;
    scheduleSelected=EveScheduleGraph.visibleJobs(data,scheduleCharacter,scheduleViewport())[0]?.id??null;redraw();
  };
  $('#schedule-graph-prev').onclick=()=>{schedulePage--;redraw();};$('#schedule-graph-next').onclick=()=>{schedulePage++;redraw();};
  target.querySelectorAll('[data-schedule-select]').forEach(node=>{
    const select=()=>{scheduleSelected=node.dataset.scheduleSelect.startsWith('eve:')?node.dataset.scheduleSelect:Number(node.dataset.scheduleSelect);const job=EveScheduleGraph.allJobs(data).find(j=>j.id===scheduleSelected);if(!job)return;if(scheduleCharacter!==null&&job.character_id!==scheduleCharacter)scheduleCharacter=job.character_id;const bounds=EveScheduleGraph.range(data,scheduleViewport());if(scheduleTimelineDays&&(job.end<=bounds.start||job.start>=bounds.end))scheduleWindow=Math.max(0,Math.floor((job.start-bounds.fullStart)/(scheduleTimelineDays*EveScheduleGraph.DAY)));const filtered=EveScheduleGraph.visibleJobs(data,scheduleCharacter,scheduleViewport());schedulePage=Math.max(0,Math.floor(filtered.findIndex(j=>j.id===scheduleSelected)/EveScheduleGraph.PAGE_SIZE));redraw();const next=target.querySelector(`g[data-schedule-select="${scheduleSelected}"]`);next?.focus({preventScroll:true});};
    node.onclick=select;if(node.tagName.toLowerCase()==='g')node.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();if(node.classList.contains('schedule-job')&&node.dataset.copyItem&&typeof copyItemName==='function')void copyItemName(node.dataset.copyItem);select();}};
  });
}
