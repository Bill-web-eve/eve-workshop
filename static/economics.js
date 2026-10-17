'use strict';
const economicPanels=new Map();let industryData=null,industryRequest=null,industryTimer=null,jobCostData=null,jobCostKey='',jobCostRequest=null;
function economicRow(label,key){return `<tr><td>${esc(label)}</td><td class="num" data-economic-value="${key}">–</td></tr>`;}
function economicFuelRows(moons){
  const d=moonData,fuel=d.settings.fuel_block_id;
  return moons.flatMap(m=>[{id:fuel,quantity:m.fuel+m.online_fuel,manual_price:d.settings.fuel_block_price},{id:d.magmatic_gas.id,quantity:m.gas}].filter(r=>r.quantity>0));
}
function moonEconomics(moons){
  economicPanels.set('moon-production',{type:'moon',moons,fuel:economicFuelRows(moons),settings:moonData.settings});
  return `<div data-economic-panel="moon-production">${EveTables.markup(['Költség és eredmény · 30 nap','ISK'],[
    economicRow('Fuel Block és Magmatic Gas','fuel'),economicRow('Bérlet','rent'),economicRow('Bányászat, finomítás, szállítás és egyéb','other'),economicRow('Értékesítési díjak','sales'),economicRow('Összes költség','total'),economicRow('Profit / 30 nap','profit')],'economic-table','moon-economics')}<p class="warning-text" data-economic-warning></p><p class="footnote">A bérlet és az egyéb költségek holdanként szerkeszthetők. Az eladási adó és a broker fee a Számítási beállítások fülön adható meg. A profit a megadott költségekkel számol; nulla díj esetén azt nem vonjuk le.</p></div>`;
}
function planEconomics(p){
  const key=JSON.stringify([p.queue.map(r=>({id:r.id,batches:r.batches})),state.settings.manufacturing,state.settings.reaction]);
  economicPanels.set('plan-materials',{type:'plan',plan:p,key});
  return `<div data-economic-panel="plan-materials">${EveTables.markup(['Gyártási és eladási összesítés','ISK'],[
    economicRow('Eladási egységár · Jita sell','sell_unit'),economicRow('Job cost','jobs'),economicRow('Összes gyártási költség','total'),economicRow('Célmennyiség eladási értéke · Jita buy','buy'),economicRow('Célmennyiség eladási értéke · Jita sell','sell')],'economic-table','plan-economics')}<p class="warning-text" data-economic-warning></p><p class="footnote">Az eladási érték a terv teljes célmennyiségének bruttó értéke, piaci díjak nélkül. A gyártási költség csak a hátralévő munkákra és bemeneteikre vonatkozik; a már kész céltermék értékét nem adja hozzá.</p><button type="button" class="button compact" data-industry-refresh>↻ Ipari költségadatok frissítése</button> <small data-industry-status></small><p><button type="button" class="text-button" data-cost-settings>Gyártási hely és adók beállítása</button></p><details><summary>Job cost részletezése</summary><div data-job-cost-details></div></details></div>`;
}
function applyEconomics(){
  $$('[data-economic-panel]').forEach(el=>{
    const key=el.dataset.economicPanel,c=economicPanels.get(key);if(!c)return;
    const v=EveCosts.value(jitaGroups.get(key)||[],jitaData.quotes,jitaMode),values={},warnings=[];
    if(c.type==='moon'){
      const fuel=EveCosts.value(c.fuel,jitaData.quotes,jitaMode);
      values.fuel=fuel.missing?null:fuel.cents;
      values.rent=c.moons.reduce((s,m)=>s+(EveCosts.money(m.rent_isk||'0')||0n),0n);
      values.other=c.moons.reduce((s,m)=>s+(EveCosts.money(m.other_cost_isk||'0')||0n),0n);
      values.sales=v.missing?null:EveCosts.percent(v.cents,c.settings.sales_tax||0)+EveCosts.percent(v.cents,jitaMode==='buy'?0:c.settings.broker_fee||0);
      values.total=values.fuel===null||values.sales===null?null:values.fuel+values.rent+values.other+values.sales;
      values.profit=v.missing||values.total===null?null:v.cents-values.total;
      if(fuel.missing)warnings.push('Hiányzó üzemanyagár miatt a teljes költség és a profit nem számolható.');
      if(v.missing)warnings.push('Hiányzó termékár miatt a profit nem számolható.');
      if(fuel.stale)warnings.push('Korábbi üzemanyagárat használunk.');
    }else{
      const current=jobCostData&&jobCostKey===c.key?jobCostData:null;
      values.jobs=current?.complete?BigInt(current.cents):null;
      values.total=v.missing||values.jobs===null?null:v.cents+values.jobs;
      values.sell_unit=EveCosts.unit(jitaData.quotes[String(c.plan.product_id)],'sell');
      for(const mode of ['buy','sell']){const sale=EveCosts.value([{id:c.plan.product_id,quantity:c.plan.quantity}],jitaData.quotes,mode);values[mode]=sale.missing?null:sale.cents;}
      if(values.buy===null||values.sell===null)warnings.push('A céltermék Jita buy vagy sell ára hiányzik; az eladási érték részben nem számolható.');
      if(!current)warnings.push('A job cost adatai még töltődnek.');
      else if(current.missing)warnings.push('Hiányzó system index vagy adjusted price miatt a job cost és a teljes költség még nem számolható.');
      if(current?.stale)warnings.push('Korábbi ipari indexet vagy adjusted price adatot használunk.');
      const detail=el.querySelector('[data-job-cost-details]');
      if(current&&detail&&detail.dataset.revision!==JSON.stringify(current)){
        detail.dataset.revision=JSON.stringify(current);
        detail.innerHTML=table(['Termék','Tevékenység','Rendszer','System index','EIV / run','Index díja','Facility tax','SCC','Alpha','Job cost'],current.rows.map(r=>`<tr><td>${itemName(r.name)}</td><td>${r.activity==='reaction'?'Reakció':'Gyártás'}</td><td>${r.system_name?verbatim(r.system_name):'Nincs kiválasztva'}</td><td class="num">${r.system_index===null?'–':(Number(r.system_index)*100).toLocaleString('hu-HU',{maximumFractionDigits:6})+'%'}</td><td class="num">${r.eiv_per_run===null?'–':EveCosts.format(EveCosts.money(r.eiv_per_run))}</td>${['system','facility','scc','alpha'].map(k=>`<td class="num">${r.components?EveCosts.format(BigInt(r.components[k])):'–'}</td>`).join('')}<td class="num">${r.cents===null?'–':EveCosts.format(BigInt(r.cents))}</td></tr>`),'job-cost-table');
      }
    }
    el.querySelectorAll('[data-economic-value]').forEach(cell=>{const amount=values[cell.dataset.economicValue];const unit=cell.dataset.economicValue==='sell_unit';cell.textContent=unit?EveCosts.formatUnit(amount):EveCosts.format(amount);cell.dataset.sortValue=amount==null?'':String(Number(amount)/(unit?10000:100));cell.classList.toggle('danger',amount!=null&&amount<0n);});
    el.querySelector('[data-economic-warning]').textContent=warnings.join(' ');
  });
  if(industryData)$$('[data-industry-status]').forEach(el=>el.textContent=industryData.running?'Ipari költségadatok betöltése…':Object.keys(industryData.errors||{}).length?'Az ipari költségadatok nem frissültek; korábbi adatokkal számolhatunk.':industryData.resources.systems.checked?'Ipari adatok ellenőrizve: '+date(Math.min(industryData.resources.systems.checked,industryData.resources.prices.checked||Infinity)):'Az ipari költségadatok még nem érkeztek meg.');
}
async function refreshJobCosts(){
  const c=economicPanels.get('plan-materials');if(view!=='queue'||!c||jobCostRequest)return;
  const revision=JSON.stringify([c.key,state.settings.manufacturing,state.settings.reaction,industryData?.resources]);
  if(jobCostData?.revision===revision)return;
  jobCostRequest=api('/api/industry/estimate',{rows:c.plan.queue.map(r=>({id:r.id,batches:r.batches}))});
  try{const data=await jobCostRequest;if(economicPanels.get('plan-materials')?.key===c.key){jobCostData={...data,revision};jobCostKey=c.key;applyJita();}}
  catch(e){if(view==='queue')error(e.message);}
  finally{jobCostRequest=null;if(economicPanels.get('plan-materials')?.key!==c.key)void refreshJobCosts();}
}
async function loadIndustry(){
  if(industryRequest)return;
  clearTimeout(industryTimer);industryRequest=api('/api/industry');
  try{
    industryData=await industryRequest;
    if(!industryData.running&&Object.values(industryData.resources).some(r=>r.stale)&&(industryData.retry_after||0)<=Date.now()/1000)industryData=await api('/api/industry/refresh',{});
    applyEconomics();if(view==='settings')void updateFacilityIndices();
    await refreshJobCosts();
  }catch(e){if(view==='queue'||view==='settings')error(e.message);}
  finally{industryRequest=null;if(industryData?.running&&['queue','settings'].includes(view))industryTimer=setTimeout(()=>void loadIndustry(),1500);}
}
function bindEconomics(){
  $$('[data-industry-refresh]').forEach(b=>b.onclick=()=>void loadIndustry());
  $$('[data-cost-settings]').forEach(b=>b.onclick=()=>navigate('settings'));
  applyEconomics();void loadIndustry();
}
async function updateFacilityIndices(){
  const fields=$$('[data-system-index]');
  await Promise.allSettled(fields.map(async field=>{
    const activity=field.dataset.systemIndex,input=$(`[data-facility-system="${activity}"]`),sid=input?.dataset.systemId;
    if(!sid){field.textContent='Válassz gyártási rendszert';return;}
    try{const data=await api('/api/industry/system?id='+sid);if(!field.isConnected||input.dataset.systemId!==sid)return;
      const index=data.indices[activity];field.textContent=index===undefined?'Még nincs ESI-index':(Number(index)*100).toLocaleString('hu-HU',{maximumFractionDigits:6})+'%';
      field.closest('.facility-index').querySelector('small').textContent=data.checked?(data.stale?'Korábbi index · ':'ESI · ')+date(data.checked):'Az ipari költségadatok még nem érkeztek meg.';
    }catch(e){field.textContent='Még nincs ESI-index';}
  }));
}
function bindFacilitySystems(){
  $$('[data-facility-system]').forEach(input=>{
    const activity=input.dataset.facilitySystem,result=$(`[data-system-results="${activity}"]`);let generation=0,timer;
    input.oninput=()=>{input.dataset.systemId='';input.setAttribute('aria-expanded','false');clearTimeout(timer);const current=++generation;
      void updateFacilityIndices();
      if(!input.value.trim()){result.hidden=true;return;}
      timer=setTimeout(async()=>{try{const rows=await api('/api/moons/systems?q='+encodeURIComponent(input.value));if(current!==generation||!input.isConnected)return;
        result.innerHTML=rows.map(s=>`<button type="button" role="option" data-system-choice="${s.id}">${verbatim(s.name)} <small>${verbatim(s.constellation)}</small></button>`).join('')||'<p>Nincs találat.</p>';
        result.hidden=false;input.setAttribute('aria-expanded','true');result.querySelectorAll('button').forEach(b=>b.onclick=()=>{generation++;input.value=rows.find(r=>r.id===Number(b.dataset.systemChoice)).name;input.dataset.systemId=b.dataset.systemChoice;result.hidden=true;input.setAttribute('aria-expanded','false');dirty.facilities=true;void updateFacilityIndices();});
      }catch(e){error(e.message);}},180);
    };
    input.onkeydown=e=>{if(e.key==='Escape'){result.hidden=true;input.setAttribute('aria-expanded','false');}else if(e.key==='ArrowDown'){e.preventDefault();result.querySelector('button')?.focus();}else if(e.key==='Enter'&&!result.hidden){e.preventDefault();result.querySelector('button')?.click();}};
    result.onkeydown=e=>{const bs=[...result.querySelectorAll('button')],i=bs.indexOf(document.activeElement);if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();bs[(i+(e.key==='ArrowDown'?1:-1)+bs.length)%bs.length]?.focus();}if(e.key==='Escape'){result.hidden=true;input.focus();input.setAttribute('aria-expanded','false');}};
  });
  $$('[data-industry-refresh]').forEach(b=>b.onclick=()=>void loadIndustry());
  void updateFacilityIndices();void loadIndustry();
}
