'use strict';
let jobData=null,jobError='',jobRequest=null,jobRevision=0,jobCharacter='';
function renderJobs(content){
  const key=corporationId||'personal';
  if(jobData?.key!==key)jobData=null;
  setHead('IPARI JOBOK','Ami már folyamatban van',corporationId?'A kiválasztott corporation saját ipari jobjai.':'Az összes karakter személyes ipari jobjai, a gyártási terv szűrőitől függetlenül.');
  $('#plan-status').hidden=true;
  const corp=state.corporations.find(c=>c.id===corporationId);
  const actors=corporationId?(corp?.members||state.characters.filter(c=>c.corporation_id===corporationId)):state.characters;
  const names=new Map(actors.map(c=>[String(c.id),c.name]));
  for(const row of jobData?.rows||[])if(row.character_id)names.set(String(row.character_id),row.character_name);
  if(jobCharacter&&!names.has(jobCharacter))jobCharacter='';
  content.innerHTML=`<div class="panel panel-body job-controls"><label>Gyártási kör<select id="job-scope" aria-label="Jobok gyártási köre"><option value="">Személyes gyártás</option>${state.corporations.map(c=>`<option data-i18n-skip value="${c.id}">${esc(c.name)}</option>`).join('')}</select></label><label>Karakter<select id="job-character" aria-label="Jobok karaktere"><option value="">Minden karakter</option>${[...names].sort((a,b)=>a[1].localeCompare(b[1])).map(([id,name])=>`<option data-i18n-skip value="${id}">${esc(name)}</option>`).join('')}</select></label></div><div id="job-results" aria-live="polite"></div>`;
  $('#job-scope').value=corporationId||'';$('#job-character').value=jobCharacter;
  $('#job-scope').onchange=e=>{jobCharacter='';jobError='';jobData=null;jobRevision++;void setProductionScope(Number(e.target.value)||null);};
  $('#job-character').onchange=e=>{jobCharacter=e.target.value;drawJobs();};
  if(jobData){drawJobs();return;}
  $('#job-results').innerHTML=jobError?empty('A jobok nem tölthetők be',jobError):empty('Ipari jobok betöltése…');
  if(jobError){$('#job-results').insertAdjacentHTML('beforeend','<button id="job-retry" class="button compact">Újrapróbálás</button>');$('#job-retry').onclick=()=>{jobError='';jobRevision++;render();};return;}
  if(jobRequest?.key===key&&jobRequest.revision===jobRevision)return;
  const request={key,revision:jobRevision};jobRequest=request;
  api('/api/jobs'+(corporationId?'?corporation_id='+corporationId:'')).then(data=>{
    if(jobRequest!==request||request.revision!==jobRevision)return;
    jobData={...data,key};jobError='';if(view==='jobs'&&(corporationId||'personal')===key)render();
  }).catch(e=>{if(jobRequest===request&&request.revision===jobRevision){jobError=e.message;if(view==='jobs'&&(corporationId||'personal')===key)render();}}).finally(()=>{if(jobRequest===request)jobRequest=null;});
}
function drawJobs(){
  if(!jobData||!$('#job-results'))return;
  updateReadyJobs();
  const jobs=jobData.rows.filter(j=>!jobCharacter||String(j.character_id)===jobCharacter),ready=jobs.filter(jobReady),labels={active:'Fut',paused:'Szünetel',ready:'Átvehető'};
  const sources=jobData.sources.filter(s=>corporationId||!jobCharacter||String(s.id)===jobCharacter),missing=sources.filter(s=>!s.available),stale=sources.filter(s=>s.stale);
  const notes=[];
  if(missing.length)notes.push('Még nincs betöltött jobadat: '+missing.map(s=>s.name).join(', ')+'.');
  if(stale.length)notes.push('Korábbi jobadatok láthatók: '+stale.map(s=>s.name).join(', ')+'.');
  const warning=ready.length?`<div class="banner warn" role="alert"><strong>Van kész vagy várhatóan elkészült job.</strong> <span>${fmt(ready.length)}</span> <span>job átvehető vagy lejárt a befejezési ideje. Vedd át az EVE-ben, majd frissítsd az adatokat.</span></div>`:'';
  const rows=jobs.map(j=>`<tr class="${jobReady(j)?'ready-job':''}"><td>${item({name:j.name,id:j.product_type_id||j.blueprint_type_id||0})}</td><td><span class="badge ${j.status==='ready'?'good':'reaction'}">${esc(j.status==='active'&&jobReady(j)?'Várhatóan elkészült · frissíts':labels[j.status]||j.status)}</span></td><td class="num">${fmt(j.runs)}</td><td class="num"><strong>${fmt(j.expected_output)}</strong></td><td data-filter-value="${esc(j.character_name)}">${esc(j.character_name)}</td><td class="num">${j.output_location_id||'–'}</td><td data-sort-value="${j.end_date?Date.parse(j.end_date):''}">${j.end_date?esc(EveI18n.date(new Date(j.end_date))):'–'}</td></tr>`);
  $('#job-results').innerHTML=(notes.length?`<div class="banner warn">${notes.map(n=>`<p>${esc(n)}</p>`).join('')}</div>`:'')+warning+panel('Aktív és át nem vett jobok',`${fmt(rows.length)} job`,rows.length?table(['Termék','Állapot','Run','Várható kimenet','Karakter','Kimeneti Hely-ID','Befejezés'],rows,'industry-jobs'):empty('Nincs ilyen folyamatban lévő job','A lista a kiválasztott gyártási kör és karakter letöltött jobadataiból készül.'))+'<p class="footnote">A Minden karakter nézet az összes hozzáadott karakter személyes jobjait mutatja, corp jobok nélkül. A listát a gyártási terv karakter- és helyszűrése nem korlátozza. A karakterválasztás csak ezt a listát szűri.</p>';
}
