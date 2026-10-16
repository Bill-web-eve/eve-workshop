'use strict';
let jitaMode='sell',jitaData={quotes:{},running:false,errors:{},retry_after:{}},jitaWanted=[],jitaRequest=null,jitaTimer=null,jitaAttempted=new Map();
try{const saved=localStorage.getItem('eve-muhely-jita-mode');if(['buy','sell','split'].includes(saved))jitaMode=saved;}catch{}
const jitaGroups=new Map();
function jitaControls(){return `<div class="jita-controls"><label>Árazás <select data-jita-mode><option value="sell">Jita sell</option><option value="buy">Jita buy</option><option value="split">Jita split</option></select></label><button type="button" class="button compact" data-jita-refresh>↻ Jita-árak frissítése</button><small data-jita-status role="status"></small></div>`;}
function costCell(id,quantity,kind='db',manual=null){const attr=manual===null?'':` data-cost-manual="${esc(manual)}"`;return `<td class="num" data-cost-unit="${id}"${attr} data-cost-kind="${esc(kind)}">–</td><td class="num" data-cost-total="${id}"${attr} data-cost-quantity="${quantity}" data-cost-kind="${esc(kind)}" data-sort-value="">–</td>`;}
function costSummary(key,rows,title,description,details=false,extra=''){
  jitaGroups.set(key,rows);
  return `<section class="cost-summary panel" data-cost-group="${esc(key)}"><div class="panel-head"><h2>${esc(title)}</h2></div><div class="panel-body">${jitaControls()}<strong class="cost-grand" data-cost-grand>–</strong><p class="warning-text" data-cost-warning></p><p>${esc(description)}</p>${extra}<p class="footnote">Jita 4-4 · buy: legmagasabb vételi ajánlat · sell: legalacsonyabb eladási ajánlat · split: (buy + sell) / 2. Tájékoztató egységárak; a piaci mennyiségi mélységet nem számoljuk.</p><p class="footnote">Az árlekérés tiszteletben tartja az ESI ötperces gyorsítótárát. Frissítéskor sem kérjük le újra az érvényes árakat.</p>${details?`<details><summary>Anyagérték részletezése</summary>${EveTables.markup(['Anyag','Mennyiség','Egységár','Anyagérték'],rows.map(r=>`<tr><td>${itemName(r.name)}${r.context?`<small class="sub" data-i18n-skip>${esc(r.context)}</small>`:''}</td><td class="num">${fmt(r.quantity)}</td>${costCell(r.id,r.quantity,r.unit,r.manual_price??null)}</tr>`),'cost-details',key+'-details')}</details>`:''}</div></section>`;
}
function applyJita(){
  $$('[data-jita-mode]').forEach(el=>el.value=jitaMode);
  $$('[data-cost-unit]').forEach(el=>{
    const p=el.dataset.costKind==='run'?null:el.hasAttribute('data-cost-manual')?EveCosts.scaled(el.dataset.costManual,true):EveCosts.unit(jitaData.quotes[el.dataset.costUnit],jitaMode);
    el.textContent=EveCosts.formatUnit(p);el.dataset.sortValue=p===null?'':String(Number(p)/10000);
  });
  $$('[data-cost-total]').forEach(el=>{
    const v=EveCosts.value([{id:Number(el.dataset.costTotal),quantity:Number(el.dataset.costQuantity),unit:el.dataset.costKind,manual_price:el.dataset.costManual}],jitaData.quotes,jitaMode).rows[0];
    el.textContent=EveCosts.format(v.cents);el.dataset.sortValue=v.cents===null?'':String(Number(v.cents)/100);
  });
  $$('[data-cost-group]').forEach(el=>{
    const v=EveCosts.value(jitaGroups.get(el.dataset.costGroup)||[],jitaData.quotes,jitaMode);
    const hasPricedQuantity=v.rows.some(r=>r.quantity>0&&r.cents!==null);
    el.querySelector('[data-cost-grand]').textContent=v.missing&&!hasPricedQuantity?'–':EveCosts.format(v.cents);
    const note=[];
    if(v.missing)note.push(`${v.missing} tétel ára hiányzik; a megjelenített összeg részösszeg.`);
    if(v.stale)note.push(`${v.stale} tételnél korábbi piaci árat használunk.`);
    if((jitaGroups.get(el.dataset.costGroup)||[]).some(r=>r.unit==='run'))note.push('A BPC-runokhoz nincs megbízható piaci egységár; ezek nincsenek beárazva.');
    el.querySelector('[data-cost-warning]').textContent=note.join(' ');
  });
  $$('[data-cost-lines]').forEach(el=>{
    const v=EveCosts.value(jitaGroups.get(el.dataset.costLines)||[],jitaData.quotes,jitaMode);
    el.textContent=v.missing?(v.rows.some(r=>r.quantity>0&&r.cents!==null)?EveCosts.format(v.cents)+' *':'–'):EveCosts.format(v.cents);
    el.dataset.sortValue=v.missing?'':String(Number(v.cents)/100);
  });
  const requested=jitaWanted.map(id=>jitaData.quotes[id]).filter(Boolean),oldest=requested.length?Math.min(...requested.map(q=>q.checked)):null;
  $$('[data-jita-status]').forEach(el=>el.textContent=!jitaWanted.length?'Nincs lekérendő piaci ár.':jitaData.fetch_error?'A Jita-árak most nem érhetők el.':jitaData.running?`Jita-árak betöltése: ${jitaData.done||0}/${jitaData.total||0}`:Object.keys(jitaData.errors||{}).some(id=>jitaWanted.includes(Number(id)))?'Néhány Jita-ár nem frissült; a korábbi adatok megmaradtak.':oldest?'Árak ellenőrizve: '+date(oldest):'A Jita-árak még nem érkeztek meg.');
  $$('[data-jita-refresh]').forEach(el=>el.disabled=!jitaWanted.length||jitaData.running||!!jitaRequest);
  if(typeof applyEconomics==='function')applyEconomics();
  globalThis.EveTables?.refreshAll();
}
function bindJita(ids){
  jitaWanted=[...new Set(ids.map(Number).filter(Number.isSafeInteger))].sort((a,b)=>a-b);
  $$('[data-jita-mode]').forEach(el=>el.onchange=()=>{jitaMode=el.value;try{localStorage.setItem('eve-muhely-jita-mode',jitaMode);}catch{}applyJita();});
  $$('[data-jita-refresh]').forEach(el=>el.onclick=()=>void loadJita(true));
  applyJita();void loadJita();
}
async function loadJita(refresh=false){
  if(jitaRequest)return;
  if(!document.querySelector('[data-cost-group]')){clearTimeout(jitaTimer);return;}
  const ids=[...jitaWanted],key=ids.join(',');
  if(!ids.length)return;
  let restart=false;
  const request=api('/api/prices?ids='+encodeURIComponent(key));jitaRequest=request;
  try{
    const data=await request;Object.assign(jitaData.quotes,data.quotes);jitaData={...data,quotes:jitaData.quotes};
    const now=Date.now()/1000;
    const needed=ids.filter(id=>{const q=data.quotes[id];return (!q||q.stale)&&(data.retry_after[id]||0)<=now&&(refresh||(jitaAttempted.get(id)||0)<=now);});
    if(needed.length){needed.forEach(id=>jitaAttempted.set(id,now+60));const started=await api('/api/prices/refresh',{ids:needed});Object.assign(jitaData.quotes,started.quotes);jitaData={...started,quotes:jitaData.quotes};}
    restart=jitaData.running;
  }catch(e){jitaData.fetch_error=true;}
  finally{jitaRequest=null;applyJita();clearTimeout(jitaTimer);if(key!==jitaWanted.join(','))void loadJita();else if(restart)jitaTimer=setTimeout(()=>void loadJita(),1200);}
}
function jitaCsv(id,quantity,unit='db'){
  const v=EveCosts.value([{id,quantity,unit}],jitaData.quotes,jitaMode).rows[0];
  return [jitaMode,EveCosts.formatUnit(v.price),EveCosts.format(v.cents)];
}
