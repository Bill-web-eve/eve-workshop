'use strict';
let inventionKey='',inventionOptions=null,inventionResult=null,inventionBusy=false,inventionTimer=null,inventionGeneration=0,inventionError='';
let financeInvention=null,financeInventionRequest=null,financeInventionKey='';
const inventionNumber=v=>Number(v).toLocaleString(EveI18n.locale,{maximumFractionDigits:6});
const inventionMoney=v=>v==null?'–':EveCosts.format(BigInt(v));
function inventionTargetKey(){return JSON.stringify([productId,activePlanId,corporationId,targetQuantity()]);}
function inventionProfileActive(c,f){return !!(f?.invention?.enabled&&f.invention.product_id===c.plan.product_id&&c.plan.queue.find(r=>r.id===c.plan.product_id)?.parameters?.kind!=='BPO');}
async function loadFinanceInvention(){
 if(!financeContext||!financePrefs||!inventionProfileActive(financeContext,financePrefs)){financeInvention=null;financeInventionKey='';return;}
 const c=financeContext,f=financePrefs,key=JSON.stringify([financeKey,f.invention,f.materials,c.quantity]);
 if(financeInventionRequest)return;
 financeInventionKey=key;financeInventionRequest=key;
 try{const data=c.quantity?await api('/api/invention/estimate',{config:f.invention,quantity:c.quantity,corporation_id:corporationId,manufacturing_prices:f.materials}):{selected:{bpc_total_cents:'0'},price_ids:[]};
  if(key===JSON.stringify([financeKey,financePrefs?.invention,financePrefs?.materials,financeContext?.quantity])){financeInvention={...data,key};applyProductionFinance();}
 }catch(e){if(key===financeInventionKey){financeInvention={key,error:e.message};applyProductionFinance();}}
 finally{financeInventionRequest=null;}
}
function financeInventionCost(c,f){
 if(!inventionProfileActive(c,f))return {active:false};
 const key=JSON.stringify([financeKey,f.invention,f.materials,c.quantity]),data=financeInvention?.key===key?financeInvention:null;
 return {active:true,cents:data?.selected?.bpc_total_cents!=null?BigInt(data.selected.bpc_total_cents):null,data};
}
function renderInvention(content){
 setHead('BLUEPRINTKÖLTSÉG','Invention és BPC-költség','Másolás, invention és teljes gyártási lánc összehasonlítása decryptoronként.');$('#plan-status').hidden=true;
 if(!productId||!(state.invention_products||[]).includes(productId)){content.innerHTML=empty('Válassz inventálható T2 hajót','A céltermék mezőben keress T2 hajót.');return;}
 const key=inventionTargetKey();
 if(key!==inventionKey){inventionKey=key;inventionGeneration++;inventionOptions=null;inventionResult=null;inventionError='';delete dirty.invention;clearTimeout(inventionTimer);}
 if(!inventionOptions){content.innerHTML=empty('Invention-adatok betöltése…');const generation=inventionGeneration;
  void api('/api/invention/options?'+new URLSearchParams({product_id:productId,...(activePlanId?{plan_id:activePlanId}:{})})).then(data=>{if(generation!==inventionGeneration)return;if(!data.configured&&!data.config.inventor_id&&manufacturerId&&data.characters.some(c=>c.id===manufacturerId))data.config.inventor_id=manufacturerId;inventionOptions=data;render();}).catch(e=>{if(generation===inventionGeneration){inventionError=e.message;content.innerHTML=empty('Az invention-adatok nem tölthetők be');error(e.message);}});return;}
 if(dirty.invention&&$('#invention-form'))return;
 const o=inventionOptions,p=o.config;
 const facilities=['copying','invention'].map(activity=>`<section><h3>${activity==='copying'?'Másolás':'Invention'}</h3><label>Rendszer<div class="search-wrap"><input type="search" data-invention-system="${activity}" data-system-id="${p[activity].system_id||''}" value="${esc(o.systems[p[activity].system_id]||'')}" placeholder="Gépelj rendszernevet…" autocomplete="off"><div class="search-results" data-invention-results="${activity}" hidden></div></div></label><div class="invention-fees">${[['facility_tax','Létesítményi adó (%)'],['job_cost_role','Jobköltség-csökkentés (%)'],['scc_surcharge','SCC (%)'],['alpha_surcharge','Alpha pótdíj (%)']].map(([field,label])=>`<label>${esc(label)}<input name="${activity}_${field}" type="number" min="0" max="100" step="0.0001" value="${esc(p[activity][field])}" required></label>`).join('')}</div></section>`).join('');
 content.innerHTML=panel('Invention-beállítások',o.base_name+' → '+o.product_name,`<form id="invention-form" class="panel-body"><div class="invention-controls"><label>Inventáló karakter<select name="inventor_id"><option value="">Válassz karaktert</option>${o.characters.map(c=>`<option value="${c.id}" data-i18n-skip>${esc(c.name)}</option>`).join('')}</select></label><label>Invention-anyagok árforrása<select name="prices">${pricingOptions(p.prices)}</select></label><label>Gyártási anyagárforrás<select name="manufacturing_prices">${pricingOptions(o.manufacturing_prices)}</select></label><label>Próbálkozások<input name="attempts" type="number" min="1" max="1000000" value="${p.attempts}" required></label><label>Run / T1 másolat<input name="copy_runs" type="number" min="1" max="${o.recipe.copy_limit}" value="${p.copy_runs}" required></label></div><div class="invention-facilities">${facilities}</div><div class="invention-controls"><label>Decryptor<select name="decryptor_id"><option value="0">Nincs decryptor</option>${o.decryptors.map(d=>`<option value="${d.id}" data-i18n-skip>${esc(d.name)}</option>`).join('')}</select></label><label class="invention-enable"><input name="enabled" type="checkbox" ${p.enabled?'checked':''}>Invention-költség beszámítása a tervbe</label></div><div class="section-actions"><button type="submit" class="button primary compact" ${inventionBusy?'disabled':''}>Összehasonlítás</button><button type="button" class="button compact" id="invention-refresh" ${inventionBusy?'disabled':''}>Árak és indexek frissítése</button><button type="button" class="button compact" id="invention-save" ${inventionBusy?'disabled':''}>Beállítás mentése a tervhez</button><span role="status">${inventionBusy?'Invention számítása…':''}</span></div></form>`)+`<div id="invention-result"></div>`;
 const form=$('#invention-form');form.elements.inventor_id.value=p.inventor_id||'';form.elements.decryptor_id.value=p.decryptor_id;
 form.oninput=()=>{dirty.invention=true;};form.onchange=()=>{dirty.invention=true;};
 form.onsubmit=e=>{e.preventDefault();if(form.reportValidity())void calculateInvention(false);};
 $('#invention-refresh').onclick=()=>{if(form.reportValidity())void calculateInvention(true);};
 $('#invention-save').onclick=()=>{if(form.reportValidity())void saveInventionProfile();};
 bindInventionSystems();renderInventionResult();
}
function readInventionForm(){
 const form=$('#invention-form'),p=JSON.parse(JSON.stringify(inventionOptions.config));
 p.inventor_id=Number(form.elements.inventor_id.value)||null;p.decryptor_id=Number(form.elements.decryptor_id.value);p.prices=form.elements.prices.value;p.attempts=Number(form.elements.attempts.value);p.copy_runs=Number(form.elements.copy_runs.value);p.enabled=form.elements.enabled.checked;
 for(const activity of ['copying','invention']){p[activity].system_id=Number(form.querySelector(`[data-invention-system=${activity}]`).dataset.systemId)||null;for(const field of ['facility_tax','job_cost_role','scc_surcharge','alpha_surcharge'])p[activity][field]=form.elements[activity+'_'+field].value;}
 inventionOptions.manufacturing_prices=form.elements.manufacturing_prices.value;inventionOptions.config=p;return p;
}
async function calculateInvention(manual=false,read=true){
 if(inventionBusy)return;const key=inventionKey,generation=inventionGeneration,config=read?readInventionForm():inventionOptions.config;
 delete dirty.invention;inventionBusy=true;inventionError='';render();
 try{
  const body={config,quantity:targetQuantity(),corporation_id:corporationId,manufacturing_prices:inventionOptions.manufacturing_prices,check_data:read||manual,refresh_all:manual};
  const data=await api('/api/invention/estimate',body);
  if(key!==inventionKey||generation!==inventionGeneration)return;inventionResult=data;
  if(data.refresh_pending||data.price_running||data.industry.running||data.skill_refresh?.running){clearTimeout(inventionTimer);inventionTimer=setTimeout(()=>{if(view==='invention'&&!dirty.invention)void calculateInvention(false,false);},1600);}
 }catch(e){if(key===inventionKey){inventionError=e.message;error(e.message);}}
 finally{inventionBusy=false;if(view==='invention'&&key===inventionKey)render();}
}
async function saveInventionProfile(decryptor=null){
 if(inventionBusy)return;const config=readInventionForm();if(decryptor!==null){config.decryptor_id=decryptor;config.enabled=true;}
 const key=inventionKey;inventionBusy=true;delete dirty.invention;render();
 try{await api('/api/trade/plan',{plan_id:activePlanId,invention:config,materials:inventionOptions.manufacturing_prices});if(key===inventionKey){financePrefs=null;financeKey='';financeInvention=null;toast('Invention-beállítás mentve.');}}
 catch(e){error(e.message);}finally{inventionBusy=false;if(view==='invention'&&key===inventionKey)render();}
}
function inventionMissingReason(row,data){
 const reasons=[];
 if(!data.config.inventor_id)reasons.push(EveI18n.t('Válassz inventáló karaktert.'));
 else if(!data.skills_ready)reasons.push(EveI18n.t('Hiányzó invention-skilladat vagy szükséges skill.'));
 if(!data.copying.complete)reasons.push(EveI18n.t('A másolás költségadata hiányzik.'));
 if(!data.invention.complete)reasons.push(EveI18n.t('Az invention-job költségadata hiányzik.'));
 for(const d of row.missing_details||[])reasons.push(EveI18n.t('Hiányzó piaci ár')+': '+d.name+' · '+(d.source==='jita'?'Jita':EveI18n.t('Helyi market'))+' '+d.mode);
 if(row.missing_jobs)reasons.push(EveI18n.t('A gyártási jobköltség hiányos.'));
 return reasons.join(' ');
}
function renderInventionResult(){
 const target=$('#invention-result');if(!target)return;const data=inventionResult;
 if(!data){target.innerHTML=empty('Számítsd ki a decryptorok költségét','A készletet és a foglalásokat az összehasonlítás nem módosítja.');return;}
 const missing=new Map();for(const row of data.rows)for(const detail of row.missing_details||[])missing.set(JSON.stringify([detail.id,detail.source,detail.mode]),detail);
 const skills=data.skills.map(s=>`${s.name} ${s.active}/${s.required}`).join(' · '),selected=data.selected;
 let warnings=[];if(!data.config.inventor_id)warnings.push('Válassz inventáló karaktert az esély és a BPC-költség kiszámításához.');else if(!data.skills_ready)warnings.push('A kiválasztott karakter skilladata hiányzik, vagy nem tudja elindítani ezt az inventiont.');if(data.skill_refresh?.error)warnings.push(data.skill_refresh.error);if(!data.copying.complete||!data.invention.complete)warnings.push('Hiányzó másolási vagy invention-index / korrigált ár. Frissítsd az ipari költségadatokat.');if(data.stale)warnings.push('Korábbi skill-, piaci vagy ipari adatokkal is számolunk.');if(data.rows.some(r=>r.missing_prices.length))warnings.push('Néhány piaci ár hiányzik; a hiányos sorok nem kapnak legjobb jelölést.');
 target.innerHTML=`<div class="banner"><strong>Várható érték alapú összehasonlítás</strong><div>${verbatim(skills)}</div><div>Az esély szerinti sikeresség nincs egészre kerekítve. A játékbeli eredmény ettől eltérhet.</div></div>${data.price_running||data.industry.running||data.skill_refresh?.running?'<div class="banner" role="status">Invention-adatok ellenőrzése: árak, ipari indexek és karakter-skillek…</div>':''}${warnings.length?`<div class="banner warn">${warnings.map(esc).join('<br>')}${missing.size?`<ul class="invention-missing-prices">${[...missing.values()].map(d=>`<li>${verbatim(d.name)} · ${esc(d.source==='jita'?'Jita':EveI18n.t('Helyi market'))} ${esc(d.mode)} · <span>${esc(d.reason==='not_loaded'?'Az ár még nincs letöltve.':d.reason==='quote_error'?'Az árlekérés nem sikerült.':'A kiválasztott ártípus nem érhető el.')}</span></li>`).join('')}</ul>`:''}</div>`:''}`+panel('Decryptorok összehasonlítása',`${fmt(data.quantity)} db`,table(['Decryptor','Esély','BPC-költség / run','Gyártási anyagok','Gyártási jobok','BPC a hajókra','Összes bekerülés','Művelet'],data.rows.map(r=>`<tr class="${r.decryptor_id===data.best_decryptor_id?'invention-best':''}"><td>${r.decryptor_id?itemName(r.name):esc('Nincs decryptor')}<div class="batch-note">ME ${r.me}% · TE ${r.te}% · ${r.runs_per_bpc} run/BPC</div>${r.decryptor_id===data.best_decryptor_id?'<div class="badge good">Legolcsóbb teljes gyártás</div>':''}</td><td class="num">${r.probability===null?'–':inventionNumber(Number(r.probability)*100)+'%'}<div class="batch-note" title="${esc(r.expected_successes??'')}"><span>Várható siker</span>: ${r.expected_successes===null?'–':inventionNumber(r.expected_successes)}</div></td>${['per_run_cents','manufacturing_materials_cents','manufacturing_jobs_cents','bpc_total_cents'].map(k=>`<td class="num" data-sort-value="${r[k]??''}" title="${r[k]==null?esc(inventionMissingReason(r,data)):''}">${inventionMoney(r[k])}</td>`).join('')}<td class="num" data-sort-value="${r.total_cents??''}" title="${r.total_cents==null?esc(inventionMissingReason(r,data)):''}"><strong>${inventionMoney(r.total_cents)}</strong><div class="batch-note"><span>Eltérés a legjobbtól</span>: ${inventionMoney(r.saving_cents)}</div></td><td><button class="button compact" data-invention-use="${r.decryptor_id}" ${inventionBusy?'disabled':''}>Ezt használom</button></td></tr>`),'invention-comparison'));
 target.innerHTML+=`<details class="invention-cost-details"><summary>Próbálkozások és költségrészletek</summary>${table(['Decryptor','Próba anyagára','Másolás / próba','Invention job / próba','Próbálkozások','Várható siker','Várható BPC-run','Próbák teljes költsége'],data.rows.map(r=>`<tr><td>${r.decryptor_id?itemName(r.name):esc('Nincs decryptor')}</td>${['materials_cents','copy_per_attempt_cents','invention_job_cents'].map(k=>`<td class="num">${inventionMoney(r[k])}</td>`).join('')}<td class="num">${data.config.attempts}</td><td class="num" title="${esc(r.expected_successes??'')}">${r.expected_successes===null?'–':inventionNumber(r.expected_successes)}</td><td class="num" title="${esc(r.expected_runs??'')}">${r.expected_runs===null?'–':inventionNumber(r.expected_runs)}</td><td class="num">${inventionMoney(r.attempts_cents)}</td></tr>`),'invention-attempts')}</details>`;
 target.innerHTML+=`<p class="footnote">Azonos mennyiségű új hajót hasonlítunk össze a teljes gyártási lánccal, készlet és folyamatban lévő jobok levonása nélkül. A decryptor ME-je és runhatára módosítja az anyagkerekítést; a gyártási struktúrák beállításait használjuk. Szállítás, eladási díjak és a T1 BPO vételára nem része ennek az összehasonlításnak. A BPO újrahasználható; a T1 másolás költségét minden próbálkozásra felosztjuk. A tervben az invention BPC-költséget csak az újonnan gyártandó hajókra számítjuk fel. A valódi BPC-k ME/TE értékei megmaradnak.</p>`;
 $$('[data-invention-use]').forEach(b=>b.onclick=()=>void saveInventionProfile(Number(b.dataset.inventionUse)));
}
function bindInventionSystems(){
 $$('[data-invention-system]').forEach(input=>{const activity=input.dataset.inventionSystem,box=$(`[data-invention-results=${activity}]`);let timer,generation=0;
 input.oninput=()=>{input.dataset.systemId='';dirty.invention=true;clearTimeout(timer);const current=++generation;if(!input.value.trim()){box.hidden=true;return;}timer=setTimeout(async()=>{try{const rows=await api('/api/moons/systems?q='+encodeURIComponent(input.value));if(current!==generation||!input.isConnected)return;box.innerHTML=rows.map(s=>`<button type="button" data-invention-system-choice="${s.id}">${verbatim(s.name)}</button>`).join('');box.hidden=false;box.querySelectorAll('button').forEach(b=>b.onclick=()=>{const system=rows.find(s=>s.id===Number(b.dataset.inventionSystemChoice));input.value=system.name;input.dataset.systemId=system.id;inventionOptions.systems[system.id]=system.name;box.hidden=true;dirty.invention=true;});}catch(e){error(e.message);}},180);};
 });
}
