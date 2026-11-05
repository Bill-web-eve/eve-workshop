'use strict';
let researchData=null,researchRequest=null,researchCharacter='',researchAt='',researchMode='sell',researchTab='agents',researchAutoAfter=0;
try{const saved=localStorage.getItem('eve-muhely-research-pricing');if(['buy','sell','split'].includes(saved))researchMode=saved;}catch{}
const researchNumber=value=>new Intl.NumberFormat('hu-HU',{maximumFractionDigits:2}).format(Number(value));
function researchLocal(value){const d=new Date(value*1000);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);}
async function refreshResearch(){
  if(researchRequest)return researchRequest;
  researchRequest=(async()=>{
    try{
      const params=new URLSearchParams();if(researchCharacter)params.set('character_id',researchCharacter);
      if(researchAt)params.set('at',String(new Date(researchAt).getTime()/1000));
      const data=await api('/api/research?'+params);
      researchData=data;if(view==='research')render();
      if(researchAutoAfter<=Date.now()/1000&&data.characters.some(c=>c.authorized)&&data.next_refresh<=Date.now()/1000){
        researchAutoAfter=Date.now()/1000+900;await startTask('/api/research/sync',false);
      }
    }catch(e){error(e.message);}
  })();
  try{await researchRequest;}finally{researchRequest=null;}
}
function researchValues(rows){
  const quotes=researchData.prices.quotes;
  return EveCosts.value(rows.map(r=>({id:r.datacore_id??r.id,quantity:r.quantity})),quotes,researchMode);
}
function researchPriceCells(row){
  const v=researchValues([row]).rows[0];
  return `<td class="num" data-sort-value="${v.price===null?'':Number(v.price)/10000}">${EveCosts.formatUnit(v.price)}</td><td class="num" data-sort-value="${v.cents===null?'':Number(v.cents)/100}">${EveCosts.format(v.cents)}</td>`;
}
function renderResearch(content){
  setHead('KUTATÁS','Research agentek','Az összes karakter RP-agentjei, beváltható datacore-jai és Jita-értékük.');
  actions(`<button class="button compact" id="research-sync" ${state.task.running?'disabled':''}>Research adatok és Jita-árak frissítése</button><button class="button compact" id="research-export">CSV mentése</button>`);
  $('#research-sync').onclick=()=>void startTask('/api/research/sync');
  const d=researchData;
  if(!d){content.innerHTML=empty('Research adatok betöltése…');$('#research-export').disabled=true;if(!researchRequest)void refreshResearch();return;}
  const current=d.characters.filter(c=>!researchCharacter||String(c.id)===researchCharacter),known=current.some(c=>c.checked_at);
  const values=researchValues(d.rows),redemption=BigInt(d.redemption_cost)*100n,net=values.cents-redemption;
  const checked=d.rows.length?Math.min(...d.rows.map(r=>r.checked_at)):null;
  const priceTimes=Object.values(d.prices.quotes).map(q=>q.checked),priceAt=priceTimes.length?Math.min(...priceTimes):null;
  content.innerHTML=`<section class="panel panel-body research-controls"><form id="research-filter"><label>Karakter<select name="character"><option value="">Összes karakter</option>${d.characters.map(c=>`<option value="${c.id}" ${researchCharacter===String(c.id)?'selected':''} data-i18n-skip>${esc(c.name)}</option>`).join('')}</select></label><label>Beváltás tervezett időpontja<input type="datetime-local" name="at" value="${esc(researchAt||researchLocal(d.at))}" min="${researchLocal(d.calculated_at-300)}" required></label><button class="button compact" type="submit">Előrejelzés számítása</button><button class="text-button" type="button" id="research-now">Most</button></form><label>Jita-árazás<select id="research-pricing">${['sell','buy','split'].map(mode=>`<option value="${mode}" ${mode===researchMode?'selected':''} data-i18n-skip>Jita ${mode}</option>`).join('')}</select></label><small><span>RP-adatok ellenőrizve:</span> ${checked?esc(date(checked)):'–'} · <span>Árak ellenőrizve:</span> ${priceAt?esc(date(priceAt)):'–'}<br><span>Következő automatikus frissítés:</span> ${d.next_refresh?esc(date(d.next_refresh)):'–'}</small></section>`;
  if(current.some(c=>!c.authorized||c.error||!c.checked_at))content.innerHTML+='<div class="banner warn">Az összesítés részleges: néhány karakter research hozzáférése vagy adata hiányzik. Az engedélyezési gombok az oldal alján találhatók.</div>';
  if(current.some(c=>c.checked_at&&c.next_refresh<=Date.now()/1000))content.innerHTML+='<div class="banner warn">A research pillanatkép több mint egy napos; az előrejelzés a legutóbbi sikeres adatokból számol.</div>';
  content.innerHTML+=`<div class="metrics research-metrics"><div class="metric"><div class="metric-label">Beváltható datacore</div><strong>${known?fmt(d.quantity):'–'}</strong><small>db</small></div><div class="metric"><div class="metric-label">Datacore-ok Jita-értéke</div><strong>${!known||values.missing?'–':EveCosts.format(values.cents)}</strong></div><div class="metric"><div class="metric-label">Beváltási díj</div><strong>${known?EveCosts.format(redemption):'–'}</strong></div><div class="metric"><div class="metric-label">Jita-érték beváltási díj után</div><strong>${!known||values.missing?'–':EveCosts.format(net)}</strong></div></div>`;
  content.innerHTML+=`<p class="footnote"><span>Becsült állapot:</span> ${esc(date(d.at))}. <span>A dátumok helyi idő szerint értendők. Automatikus RP- és árfrissítés 24 óránként; a külön frissítőgomb kézzel indít ellenőrzést.</span></p><p class="footnote">Az RP az ESI kezdési időpontjából, maradék pontjából és napi rátájából számolt becslés. Az ESI nem ad meg leállást vagy RP-plafont; a becslés folyamatos termelést feltételez. Beváltás után frissítsd az adatokat.</p>`;
  if(values.missing)content.innerHTML+='<p class="warning-text">Néhány datacore típusa vagy ára hiányzik; a teljes Jita-érték nem állapítható meg.</p>';
  if(priceAt&&priceAt+86400<Date.now()/1000)content.innerHTML+='<p class="warning-text">A Jita-árak több mint egy naposak.</p>';
  content.innerHTML+=`<div class="shopping-tabs"><button data-research-tab="agents" aria-pressed="${researchTab==='agents'}">Agentenként</button><button data-research-tab="characters" aria-pressed="${researchTab==='characters'}">Karakterenként</button><button data-research-tab="cores" aria-pressed="${researchTab==='cores'}">Datacore-onként</button></div>`;
  if(researchTab==='agents')content.innerHTML+=panel('RP-agentek','',table(['Karakter','Agent','Kutatási terület','RP / nap','Becsült RP','Datacore','Beváltható','Jita-egységár','Jita-érték'],d.rows.map(r=>`<tr><td>${verbatim(r.character_name)}</td><td>${verbatim(r.agent_name)}</td><td>${verbatim(r.field)}</td><td class="num">${researchNumber(r.rp_per_day)}</td><td class="num">${researchNumber(r.rp)}</td><td>${r.datacore_name?itemName(r.datacore_name):'–'}</td><td class="num">${fmt(r.quantity)}</td>${researchPriceCells(r)}</tr>`),'research-agents'));
  else if(researchTab==='cores')content.innerHTML+=panel('Datacore-onkénti összesítés','',table(['Datacore','RP / nap','Beváltható','Jita-egységár','Jita-érték'],d.totals.map(r=>`<tr><td>${itemName(r.name)}</td><td class="num">${researchNumber(r.rp_per_day)}</td><td class="num">${fmt(r.quantity)}</td>${researchPriceCells(r)}</tr>`),'research-cores'));
  else content.innerHTML+=panel('Karakterenkénti összesítés','',table(['Karakter','Agentek','RP / nap','Beváltható','Jita-érték','Beváltási díj'],current.map(c=>{
    const rows=d.rows.filter(r=>r.character_id===c.id),v=researchValues(rows),quantity=rows.reduce((n,r)=>n+r.quantity,0);
    return `<tr><td>${verbatim(c.name)}</td><td class="num">${fmt(rows.length)}</td><td class="num">${researchNumber(rows.reduce((n,r)=>n+Number(r.rp_per_day),0))}</td><td class="num">${fmt(quantity)}</td><td class="num">${v.missing?'–':EveCosts.format(v.cents)}</td><td class="num">${EveCosts.format(BigInt(quantity)*1000000n)}</td></tr>`;
  }),'research-characters'));
  content.innerHTML+='<p class="footnote">100 RP = 1 datacore; a beváltható mennyiséget minden karakter–agent párnál külön lefelé kerekítjük. Beváltási díj: 10 000 ISK/datacore. Az érték tájékoztató jellegű; eladási adó és broker fee nélkül.</p>';
  content.innerHTML+=panel('Research hozzáférések','',table(['Karakter','Utolsó sikeres lekérés','Állapot','Művelet'],d.characters.map(c=>`<tr><td>${verbatim(c.name)}</td><td>${c.checked_at?esc(date(c.checked_at)):'–'}</td><td>${esc(!c.authorized?'Engedélyezés szükséges':c.error|| (c.checked_at?'Olvasási engedély megadva':'Még nincs lekérdezés'))}</td><td><button class="button compact" data-research-auth="${c.id}">Research hozzáférés engedélyezése</button></td></tr>`),'research-access')+`<details class="panel-body"><summary>Szükséges jogosultságok</summary><code>${d.scopes.map(esc).join('\n')}</code><p>Az új scope-ot az EVE Developer alkalmazásban is engedélyezni kell, majd a karaktert újra jóváhagyni. A meglévő karakteradatok megmaradnak.</p></details>`);
  $('#research-filter').onsubmit=event=>{event.preventDefault();const f=new FormData(event.currentTarget);researchCharacter=String(f.get('character'));researchAt=String(f.get('at'));void refreshResearch();};
  $('#research-now').onclick=()=>{researchAt='';void refreshResearch();};
  $('#research-pricing').onchange=event=>{researchMode=event.target.value;try{localStorage.setItem('eve-muhely-research-pricing',researchMode);}catch{}render();};
  $$('[data-research-tab]').forEach(button=>button.onclick=()=>{researchTab=button.dataset.researchTab;render();});
  $$('[data-research-auth]').forEach(button=>button.onclick=async()=>{
    try{button.disabled=true;const auth=await api('/api/auth/start',{character_id:Number(button.dataset.researchAuth),feature:'research'});sessionStorage.setItem('eve-muhely-auth-return','research');await openEveAuthorization(auth);}
    catch(e){error(e.message);button.disabled=false;}
  });
  $('#research-export').onclick=()=>csv(d.rows.map(r=>[r.character_name,r.agent_name,r.field,r.rp_per_day,r.rp,r.datacore_name,r.quantity,researchMode,EveCosts.format(researchValues([r]).cents),new Date(d.at*1000).toISOString()]),['Karakter','Agent','Kutatási terület','RP / nap','Becsült RP','Datacore','Beváltható','Jita-árazás','Jita-érték','Időpont (UTC)'],'research-agents');
}
