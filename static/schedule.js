'use strict';
let scheduleResult=null,scheduleRequest=null,scheduleRevision=0,schedulePage=0,scheduleOptions={owned_only:true,transfer_blueprints:false,characters:null,start:'',supply_at:''};
try{Object.assign(scheduleOptions,JSON.parse(localStorage.getItem('eve-muhely-schedule-options')||'{}'));}catch{}
if(!Array.isArray(scheduleOptions.characters))scheduleOptions.characters=null;
for(const key of ['start','supply_at'])if(typeof scheduleOptions[key]!=='string')scheduleOptions[key]='';
const scheduleKey=()=>JSON.stringify([productId,targetQuantity(),corporationId,activePlanId,scheduleRevision]);
const scheduleTime=n=>n?EveI18n.date(n*1000,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'–';
function readScheduleOptions(){
  const form=$('#schedule-form');
  scheduleOptions={owned_only:form.elements.owned_only.checked,transfer_blueprints:form.elements.transfer_blueprints.checked,
    characters:$$('[data-schedule-character]:checked').map(input=>Number(input.dataset.scheduleCharacter)),start:form.elements.start.value,supply_at:form.elements.supply_at.value};
  try{localStorage.setItem('eve-muhely-schedule-options',JSON.stringify(scheduleOptions));}catch{}
  return scheduleOptions;
}
function renderSchedule(content){
  setHead('PÁRHUZAMOS GYÁRTÁS','Gyártásütemező','Karakterenkénti gyártási és reakciós slotok, aktív skillek, anyagérkezés és egyedi blueprintek alapján.');
  $('#plan-status').hidden=true;
  if(scheduleResult?.key!==scheduleKey()){scheduleResult=null;schedulePage=0;}
  const chars=state.production_characters||[];
  content.innerHTML=`<form id="schedule-form" class="panel panel-body"><div class="schedule-options"><label class="schedule-flag"><input type="checkbox" name="owned_only" ${scheduleOptions.owned_only?'checked':''}> Csak a meglévő BPO/BPC készlettel</label><label class="schedule-flag"><input type="checkbox" name="transfer_blueprints" ${scheduleOptions.transfer_blueprints?'checked':''} ${corporationId?'disabled':''}> Személyes blueprintek átadhatók a karakterek között</label><label>Kezdés · üresen most<input type="datetime-local" name="start" value="${esc(scheduleOptions.start||'')}"></label><label>Beszerzendő anyagok és új blueprintek érkezése<input type="datetime-local" name="supply_at" value="${esc(scheduleOptions.supply_at||'')}"></label></div><h3>Bevonható karakterek</h3><div class="schedule-characters">${chars.map(c=>`<label><input type="checkbox" data-schedule-character="${c.id}" ${scheduleOptions.characters===null||scheduleOptions.characters.includes(c.id)?'checked':''}> ${verbatim(c.name)}${!c.available?' · <span>Nincs skilladat</span>':''}</label>`).join('')||'<p>Még nincs hozzáadott karakter.</p>'}</div><p class="footnote">A dátumok helyi időben értendők. Üres anyagérkezés: a kezdés ideje. A személyes és corp készlet elkülönül; corp tervhez csak annak tagkaraktereit használjuk. A tanulási hely nem korlátozza az industry slotokat.</p><button class="button primary" type="submit" ${!productId||scheduleRequest?'disabled':''}>${scheduleRequest?'Ütemezés készül…':'Ütemterv kiszámítása'}</button></form><div id="schedule-result"></div>`;
  $('#schedule-form').oninput=readScheduleOptions;
  $('#schedule-form').onsubmit=async event=>{
    event.preventDefault();if(!productId||scheduleRequest)return;
    const opts=readScheduleOptions(),key=scheduleKey(),body={product_id:productId,quantity:targetQuantity(),corporation_id:corporationId,saved_plan_id:activePlanId,
      characters:opts.characters,owned_only:opts.owned_only,transfer_blueprints:opts.transfer_blueprints};
    for(const field of ['start','supply_at'])if(opts[field])body[field]=new Date(opts[field]).getTime()/1000;
    scheduleRequest=api('/api/schedule',body);render();
    try{const data=await scheduleRequest;if(key===scheduleKey()){scheduleResult={key,data};schedulePage=0;}}
    catch(e){error(e.message);}finally{scheduleRequest=null;if(view==='schedule')render();}
  };
  if(scheduleResult)renderScheduleResult($('#schedule-result'),scheduleResult.data);
}
function renderScheduleResult(target,data){
  const pages=Math.max(1,Math.ceil(data.jobs.length/100));schedulePage=Math.min(schedulePage,pages-1);
  const jobs=data.jobs.slice(schedulePage*100,(schedulePage+1)*100);
  target.innerHTML=`<div class="banner ${data.complete?'':'warn'}"><strong>${data.complete?'Teljes ütemterv':'Részleges ütemterv · hiányzó feltételek'}</strong><p>Az ütemező a rövidebb átfutásra törekszik, heurisztikus módszerrel. Nem garantál matematikailag optimális megoldást. Az alábbi jobok kézzel indíthatók; az app nem indít EVE-jobot.</p></div><div class="metrics"><div class="metric"><div class="metric-label">Ütemezett jobok</div><strong>${fmt(data.jobs.length)}</strong></div><div class="metric"><div class="metric-label">Ütemezett runok</div><strong>${fmt(data.runs)}</strong></div><div class="metric"><div class="metric-label">Várható befejezés</div><strong class="schedule-date">${scheduleTime(data.finish)}</strong></div><div class="metric"><div class="metric-label">Átfutás · óra</div><strong>${data.complete?hours(data.seconds):'–'}</strong></div></div>`;
  target.innerHTML+=panel('Számítási feltételek','A hiányzó inputok miatt a tényleges befejezés későbbi lehet',`<div class="panel-body">${data.assumptions.map(a=>`<p>${esc(a)}</p>`).join('')}<p>Anyagérkezés: ${esc(scheduleTime(data.supply_at))}</p><p>A jobfelosztás az anyagkerekítést is módosíthatja. Az ütemezés saját anyaghiányát lent külön mutatjuk; az eredeti mentett terv foglalása ettől nem módosul.</p></div>`);
  if(data.blueprint_shortages.length)target.innerHTML+=panel('Szükséges további blueprintek','A kiszámított ütemtervhez; a jelzett run/BPC feltételezéssel',table(['Blueprint','Típus','További példány','Szükséges BPC-run','Run/BPC feltételezés'],data.blueprint_shortages.map(b=>`<tr><td>${itemName(b.name)}</td><td>${b.category==='Reakcióformula'?'Reakcióformula':'BPC'}</td><td class="num">${fmt(b.copies)}</td><td class="num">${b.category==='Reakcióformula'?'–':fmt(b.runs)}</td><td class="num">${b.category==='Reakcióformula'?'–':fmt(b.copy_runs)}</td></tr>`)));
  if(data.blocked.length||data.material_warnings.length)target.innerHTML+=panel('Nem ütemezhető tételek','Ezek miatt a teljes terv befejezése nem állapítható meg',table(['Termék','Hátralévő run','Ok'],[...data.blocked,...data.material_warnings].map(b=>`<tr><td>${itemName(b.name)}</td><td>${b.runs==null?'–':fmt(b.runs)}</td><td>${esc(b.reason)}</td></tr>`)));
  target.innerHTML+=panel('Karakterek ipari kapacitása','Az aktív skillek szerinti slotkeret',table(['Karakter','Gyártási slot','Reakciós slot','Skilladat ideje','Jobadat ideje','Állapot'],data.workers.map(w=>`<tr><td>${verbatim(w.name)}</td><td>${w.capacity.manufacturing}</td><td>${w.capacity.reaction}</td><td>${date(w.as_of)}</td><td>${date(w.jobs_as_of)}</td><td>${esc(w.excluded|| (w.stale?'Korábbi skilladatok':'Bevonható'))}</td></tr>`)));
  target.innerHTML+=`<div class="section-actions"><button id="schedule-csv" class="button compact">Ütemterv CSV mentése</button><button id="schedule-prev" class="button compact" ${schedulePage===0?'disabled':''}>←</button><span>${schedulePage+1} / ${pages}</span><button id="schedule-next" class="button compact" ${schedulePage+1===pages?'disabled':''}>→</button><span>100 job / oldal</span></div>`+
    panel('Indítási ütemterv','Kezdési idő szerint',table(['Termék','Karakter','Művelet','Slot','Run','Kimenet','Kezdés','Befejezés','Blueprint Item ID','Blueprint forrás','ME / TE'],jobs.map(j=>`<tr><td>${itemName(j.name)}</td><td>${verbatim(j.character_name)}</td><td>${j.activity==='reaction'?'Reakció':'Gyártás'}</td><td>${j.slot}</td><td>${fmt(j.runs)}</td><td>${fmt(j.output)}</td><td data-sort-value="${j.start}">${scheduleTime(j.start)}</td><td data-sort-value="${j.end}">${scheduleTime(j.end)}</td><td>${j.blueprint_item_id??'–'}</td><td><span>${j.procure_blueprint?'Beszerzendő / másolandó':j.transfer_required?'Átadás szükséges':'Meglévő'}</span> · <span data-i18n-skip>${j.blueprint_kind}</span></td><td>${j.me} / ${j.te}</td></tr>`),'schedule-jobs'));
  const materials=data.material_shortfall.filter(r=>!r.is_blueprint&&r.unit!=='run'&&r.category!=='Reakcióformula');
  target.innerHTML+=panel('Ütemezés anyaghiánya','Az ütemezett jobfelosztás szerint újraszámolva',`<div class="panel-body"><button class="button compact" id="schedule-copy-materials">Multibuy másolása</button></div>`+table(['Anyag','Beszerzendő'],materials.map(m=>`<tr><td>${itemName(m.name)}</td><td class="num">${fmt(m.buy)}</td></tr>`)));
  $('#schedule-prev').onclick=()=>{schedulePage--;renderScheduleResult(target,data);};$('#schedule-next').onclick=()=>{schedulePage++;renderScheduleResult(target,data);};
  $('#schedule-copy-materials').onclick=async()=>{try{await navigator.clipboard.writeText(EveMultibuy.text(materials));toast('Multibuy lista másolva.');}catch{error('A másolás nem sikerült.');}};
  $('#schedule-csv').onclick=()=>csv(data.jobs.map(j=>[j.name,j.character_name,j.activity,j.slot,j.runs,j.output,new Date(j.start*1000).toISOString(),new Date(j.end*1000).toISOString(),j.blueprint_item_id||'',j.procure_blueprint,j.me,j.te]),['Termék','Karakter','Művelet','Slot','Run','Kimenet','Kezdés UTC','Befejezés UTC','Blueprint Item ID','Beszerzendő blueprint','ME','TE'],'utemterv');
}
