'use strict';
let tradeData=null,tradeRequest=null,tradeTimer=null,financeContext=null,financePrefs=null,financeKey='',financeGeneration=0,financeTimer=null,financeBusy=false,financeSaveTimer=null,financeProfile=null,financeProfileKey='',financeError='';
let financeBooks={jita:{quotes:{},errors:{}},local:{quotes:{},errors:{}}};
const financeDefaults={materials:'jita:sell',sale:'jita:sell',seller_id:null,sale_order:'auto',other_isk:'0',blueprints_isk:null};
function localMarketName(){return tradeData?.settings.location?.name||'Helyi market';}
function pricingOptions(value){return ['jita','local'].map(source=>`<optgroup label="${esc(source==='jita'?'Jita 4-4':localMarketName())}">${['sell','buy','split'].map(mode=>`<option value="${source}:${mode}" ${value===source+':'+mode?'selected':''}>${esc(source==='jita'?'Jita':'Helyi')} ${mode}</option>`).join('')}</optgroup>`).join('');}
async function loadTrade(background=false){
 if(tradeRequest)return tradeRequest;
 tradeRequest=(async()=>{
  try{const previous=JSON.stringify([tradeData?.settings.location_id,tradeData?.settings.reader_id,tradeData?.settings.structure_broker_fee]);tradeData=await api('/api/trade');const current=JSON.stringify([tradeData.settings.location_id,tradeData.settings.reader_id,tradeData.settings.structure_broker_fee]);if(previous!==current){financeGeneration++;financeBooks.local={quotes:{},errors:{}};if(typeof resetLocalPrices==='function')resetLocalPrices();}updateTradeStatus();
   if(view==='settings'&&settingsTab==='market'&&!$('#market-settings'))renderTradeSettings($('#settings-content'));
   if(view==='settings'&&settingsTab==='market')updateMarketCandidates();
   if(view==='queue'&&financePrefs){$$('[data-finance-field] optgroup').forEach(g=>{if(g.querySelector('option')?.value.startsWith('local:'))g.label=localMarketName();});await loadFinanceProfile();}
  }catch(e){if(!background)error(e.message);}finally{tradeRequest=null;clearTimeout(tradeTimer);if(tradeData?.status.running)tradeTimer=setTimeout(()=>void loadTrade(true),1000);}
 })();return tradeRequest;
}
function updateTradeStatus(){
 const status=tradeData?.status;
 $$('[data-trade-status]').forEach(el=>{el.textContent=status?.running?`${status.phase} · ${status.done}/${status.total}`:status?.error||'';el.classList.toggle('warning-text',!!status?.error);});
 $$('[data-trade-work]').forEach(el=>el.disabled=!!status?.running);
}
function renderTradeSettings(target){
 if(!tradeData){target.innerHTML=empty('Marketadatok betöltése…');void loadTrade();return;}
 const p=tradeData.settings;
 target.innerHTML=panel('Marketek és értékesítés','',`<form id="market-settings" class="panel-body"><div class="trade-settings-grid"><label>Helyi market rendszere<div class="search-wrap"><input id="market-system" type="search" data-system-id="${p.system_id||''}" value="${esc(p.location?.system_name||p.system_name||'')}" placeholder="Gépelj rendszernevet…" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="market-system-results"><div id="market-system-results" class="search-results" role="listbox" hidden></div></div></label><label>Marketadatokat olvasó karakter<select name="reader_id"><option value="">Válassz karaktert</option>${tradeData.characters.map(c=>`<option value="${c.id}" ${p.reader_id===c.id?'selected':''} data-i18n-skip>${esc(c.name)}</option>`).join('')}</select></label><label>Állomás vagy struktúra neve<input name="search" type="text" maxlength="120" value="${esc(p.search)}" placeholder="C-N4OD - Fountain of Life"></label><label>Structure ID · opcionális<input name="structure_id" type="text" inputmode="numeric" placeholder="Ha név alapján nem található"></label></div><div class="section-actions"><button type="button" class="button compact" id="market-discover" data-trade-work>Market keresése</button><small data-trade-status role="status"></small></div><div class="trade-settings-grid"><label>Helyi piaci állomás<select name="location_id" id="market-location"><option value="">Előbb keresd meg a marketet</option>${p.location?`<option value="${p.location.id}" selected data-i18n-skip>${esc(p.location.name)}</option>`:''}</select></label><label>Teljes struktúra broker fee (%)<input name="structure_broker_fee" type="number" min="0" max="100" step="0.0001" value="${p.structure_broker_fee??''}" placeholder="SCC-vel együtt"></label><div class="footnote">A struktúra tényleges, rád érvényes teljes broker fee-jét az EVE piacablakából add meg. Az ESI ezt nem közli. NPC-állomásnál az eladó skilljeiből és módosítatlan standingjeiből számolunk.</div></div><div class="section-actions"><button class="button primary compact" type="submit">Marketbeállítások mentése</button><button type="button" class="text-button" id="market-example">C-N4OD · Fountain of Life</button></div></form>`)+panel('Market-hozzáférések','',`<div class="panel-body"><p>A struktúra piacához dokkolási hozzáférés és olvasási ESI-engedély szükséges. Az eladói NPC-díjakhoz a standingek olvasása is kell.</p>${tradeData.characters.map(c=>`<div class="trade-access"><strong data-i18n-skip>${esc(c.name)}</strong><span>${c.market_access?'Piaci hozzáférés megadva':'Piaci engedély hiányzik'}</span><span>${c.standings_access?'Standinghozzáférés megadva':'Standingengedély hiányzik'}</span><button class="button compact" data-market-authorize="${c.id}">Market-hozzáférés engedélyezése</button></div>`).join('')}<details><summary>Szükséges jogosultságok</summary><code>${tradeData.scopes.map(esc).join('\n')}</code><p>Az új scope-okat az EVE Developer alkalmazásban is engedélyezni kell.</p></details></div>`);
 const form=$('#market-settings'),input=$('#market-system'),results=$('#market-system-results');let timer,generation=0;
 input.oninput=()=>{dirty.market=true;input.dataset.systemId='';results.hidden=true;clearTimeout(timer);const current=++generation;
  timer=setTimeout(async()=>{try{const rows=await api('/api/moons/systems?q='+encodeURIComponent(input.value));if(current!==generation||!input.isConnected)return;results.innerHTML=rows.map(s=>`<button type="button" role="option" data-market-system="${s.id}">${verbatim(s.name)} · ${verbatim(s.constellation)}</button>`).join('');results.hidden=false;input.setAttribute('aria-expanded','true');results.querySelectorAll('button').forEach(b=>b.onclick=()=>{input.value=rows.find(s=>s.id===Number(b.dataset.marketSystem)).name;input.dataset.systemId=b.dataset.marketSystem;results.hidden=true;input.setAttribute('aria-expanded','false');form.elements.location_id.innerHTML='<option value="">Előbb keresd meg a marketet</option>';});}catch(e){error(e.message);}},180);
 };
 input.onkeydown=e=>{if(e.key==='Escape'){results.hidden=true;input.setAttribute('aria-expanded','false');}if(e.key==='ArrowDown'){e.preventDefault();results.querySelector('button')?.focus();}if(e.key==='Enter'&&!results.hidden){e.preventDefault();results.querySelector('button')?.click();}};
 results.onkeydown=e=>{const buttons=[...results.querySelectorAll('button')],i=buttons.indexOf(document.activeElement);if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();buttons[(i+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}if(e.key==='Escape'){results.hidden=true;input.focus();}};
 form.oninput=()=>{dirty.market=true;};
 $('#market-example').onclick=()=>{input.value='C-N4OD';input.dataset.systemId='30004600';form.elements.search.value='C-N4OD - Fountain of Life';dirty.market=true;};
 const body=()=>({system_id:Number(input.dataset.systemId),reader_id:Number(form.elements.reader_id.value),search:form.elements.search.value,structure_id:form.elements.structure_id.value?Number(form.elements.structure_id.value):null});
 $('#market-discover').onclick=async()=>{try{tradeData=await api('/api/trade/discover',body());updateTradeStatus();void loadTrade(true);}catch(e){error(e.message);}};
 form.onsubmit=async e=>{e.preventDefault();try{tradeData=await api('/api/trade/settings',{...body(),location_id:Number(form.elements.location_id.value)||null,structure_broker_fee:form.elements.structure_broker_fee.value});dirty={};financeGeneration++;financeBooks={jita:{quotes:{},errors:{}},local:{quotes:{},errors:{}}};if(typeof resetLocalPrices==='function')resetLocalPrices();toast('Marketbeállítások mentve.');renderTradeSettings(target);}catch(e){error(e.message);}};
 $$('[data-market-authorize]').forEach(b=>b.onclick=async()=>{try{const auth=await api('/api/auth/start',{character_id:Number(b.dataset.marketAuthorize),feature:'markets'});sessionStorage.setItem('eve-muhely-auth-return','settings:market');tradeData=null;await openEveAuthorization(auth);}catch(e){error(e.message);}});
 updateTradeStatus();updateMarketCandidates();

}
function updateMarketCandidates(){
 const form=$('#market-settings'),status=tradeData?.status;if(!form||!status||status.running)return;
 if(status.system_id!==Number($('#market-system').dataset.systemId)||status.reader_id!==Number(form.elements.reader_id.value))return;
 const select=form.elements.location_id,previous=select.value||String(tradeData.settings.location_id||'');
 const rows=status.candidates||[];const stamp=JSON.stringify(rows);if(select.dataset.stamp===stamp)return;select.dataset.stamp=stamp;
 select.innerHTML='<option value="">Válassz állomást</option>'+rows.map(r=>`<option value="${r.id}" data-i18n-skip>${esc(r.name)}</option>`).join('');
 if(rows.some(r=>String(r.id)===previous))select.value=previous;else if(rows.length===1)select.value=String(rows[0].id);
 if(!rows.length)error('Ebben a rendszerben nem találtunk elérhető marketet. Ellenőrizd a nevet és a karakter hozzáférését.');
}
function productionFinance(p,materials){
 planEconomics(p);
 const key=JSON.stringify([activePlanId,p.product_id,p.quantity,p.queue.map(r=>[r.id,r.runs,r.manufactured]),corporationId]);
 if(key!==financeKey){financeKey=key;financeGeneration++;financePrefs=null;financeProfile=null;financeProfileKey='';financeError='';clearTimeout(financeSaveTimer);}
 financeContext={plan:p,materials,plan_id:activePlanId,key,quantity:p.queue.find(r=>r.id===p.product_id)?.manufactured||0};
 const f=financePrefs||financeDefaults;
 return `<section class="panel production-finance"><div class="panel-head"><h2>Gyártási költség és várható bevétel</h2><button type="button" class="text-button" data-finance-settings>Marketbeállítások</button></div><div class="panel-body"><div class="finance-grid"><section><label>Anyagok és blueprintek árazása<select data-finance-field="materials">${pricingOptions(f.materials)}</select></label><div class="finance-line"><span>Felhasznált anyagok</span><strong data-finance-value="materials">–</strong></div><div class="finance-line"><span>Blueprint beszerzés</span><strong data-finance-value="blueprints">–</strong></div><div class="finance-line"><span>Job cost</span><strong data-finance-value="jobs">–</strong></div><div class="finance-line"><span>Szállítás és egyéb</span><strong data-finance-value="other">–</strong></div></section><section><label>Eladási árforrás<select data-finance-field="sale">${pricingOptions(f.sale)}</select></label><div class="finance-control-row"><label>Eladó karakter<select data-finance-field="seller_id"><option value="">Válassz karaktert</option>${state.characters.map(c=>`<option value="${c.id}" ${c.id===f.seller_id?'selected':''} data-i18n-skip>${esc(c.name)}</option>`).join('')}</select></label><label>Eladási mód<select data-finance-field="sale_order"><option value="auto" ${f.sale_order==='auto'?'selected':''}>Árforrás szerint</option><option value="instant" ${f.sale_order==='instant'?'selected':''}>Azonnali eladás · nincs broker fee</option><option value="order" ${f.sale_order==='order'?'selected':''}>Eladási megbízás</option></select></label></div><div class="finance-line"><span>Eladási egységár</span><strong data-finance-value="unit">–</strong></div><div class="finance-line"><span>Bruttó eladási érték</span><strong data-finance-value="gross">–</strong></div></section><section><div class="finance-line"><span>Eladási adó</span><strong data-finance-value="sales_tax">–</strong></div><div class="finance-line"><span>Broker fee</span><strong data-finance-value="broker_fee">–</strong></div><div class="finance-line"><span>Nettó eladási bevétel</span><strong data-finance-value="net">–</strong></div><div class="finance-line finance-total"><span>Összes bekerülési költség</span><strong data-finance-value="total">–</strong></div><div class="finance-line finance-total"><span>Várható profit</span><strong data-finance-value="profit">–</strong></div><small data-finance-profile></small></section></div><div class="section-actions"><button type="button" class="button compact" data-finance-refresh>↻ Piaci árak frissítése</button><button type="button" class="button compact" data-finance-seller data-trade-work>Eladó adatainak frissítése</button><button type="button" class="text-button" data-industry-refresh>↻ Ipari költségadatok frissítése</button><small data-finance-status role="status"></small><small data-trade-status role="status"></small></div><p class="warning-text" data-finance-warning></p><details class="finance-details"><summary>További költségek és részletek</summary><div class="trade-settings-grid"><label>Blueprintköltség felülírása (ISK)<input data-finance-field="blueprints_isk" type="number" min="0" step="0.01" value="${f.blueprints_isk??''}" placeholder="Automatikus · BPC esetén add meg"></label><label>Szállítás és egyéb költség (ISK)<input data-finance-field="other_isk" type="number" min="0" step="0.01" value="${esc(f.other_isk)}"></label></div><p>A hátralévő gyártás új céltermékkimenete: ${fmt(financeContext.quantity)} db. A meglévő készterméket és az elindított céltermékjobokat nem értékesítjük újra a profitban. A felhasznált készlet és folyamatban lévő köztes anyag piaci értéke is költség; az általunk gyártott köztes termék alapanyagait egyszer számoljuk. A job cost az ESI adjusted price és a beállított ipari díjak alapján számít.</p><p>Buy: legmagasabb vételi ajánlat. Sell: legalacsonyabb eladási ajánlat. Split: a kettő átlaga. Nincs automatikus Jita-helyettesítés hiányzó helyi árnál. A piaci mélységet, a megbízások újraárazását és a későbbi árváltozást nem becsüljük.</p><div data-finance-materials></div><div data-job-cost-details></div></details></div></section>`;
}
function financeFee(cents,rate){
 if(cents===null||rate===null||rate===undefined)return null;
 const m=String(rate).match(/^(\d+)(?:\.(\d{1,8}))?$/);if(!m)return null;
 const scaled=BigInt(m[1])*100000000n+BigInt((m[2]||'').padEnd(8,'0'));return (cents*scaled+5000000000n)/10000000000n;
}
function financeValues(c,f,books,profile,jobs){
 const [ms,mm]=f.materials.split(':'),[ss,sm]=f.sale.split(':'),material=EveCosts.value(c.materials,books[ms]?.quotes||{},mm);
 const bp=EveCosts.value((c.plan.blueprint_shortages||[]).map(r=>({...r,quantity:r.buy})),books[ms]?.quotes||{},mm);
 const blueprints=f.blueprints_isk===null||f.blueprints_isk===''?(bp.missing?null:bp.cents):EveCosts.money(f.blueprints_isk);
 const sale=EveCosts.value([{id:c.plan.product_id,quantity:c.quantity}],books[ss]?.quotes||{},sm);
 const gross=sale.missing?null:sale.cents,job=jobs?.complete?BigInt(jobs.cents):c.plan.queue.length?null:0n;
 const order=f.sale_order==='order'||f.sale_order==='auto'&&sm!=='buy';
 const tax=gross===0n?0n:financeFee(gross,profile?.sales_tax);let broker=order&&gross!==0n?financeFee(gross,profile?.broker_fee):0n;
 if(order&&broker!==null&&Number(profile?.broker_fee)>0&&gross>0n&&broker<10000n)broker=10000n;
 const other=EveCosts.money(f.other_isk),total=material.missing||blueprints===null||job===null||other===null?null:material.cents+blueprints+job+other;
 const net=gross===null||tax===null||broker===null?null:gross-tax-broker;
 return {values:{materials:material.missing?null:material.cents,blueprints,jobs:job,other,gross,unit:sale.rows[0]?.price,sales_tax:tax,broker_fee:broker,net,total,profit:total===null||net===null?null:net-total},material,bp,sale,order};
}
function applyProductionFinance(){
 const target=$('#production-finance');if(!target||target.hidden||!financeContext||!financePrefs)return;
 const c=financeContext,f=financePrefs,job=jobCostKey===economicPanels.get('plan-materials')?.key?jobCostData:null;
 const out=financeValues(c,f,financeBooks,financeProfile,job),warnings=[];
 if(out.material.missing)warnings.push('Néhány anyag ára hiányzik; a teljes költség és profit nem számolható.');
 if(out.values.blueprints===null)warnings.push('A hiányzó BPC-k vagy blueprintek beszerzési árát add meg a Blueprintköltség mezőben.');
 if(out.values.jobs===null)warnings.push('A job cost hiányos; állítsd be a gyártási rendszert és az ipari díjakat.');
 if(out.sale.missing)warnings.push('A céltermék kiválasztott piaci ára hiányzik.');
 if(c.quantity&&out.values.sales_tax===null)warnings.push('Válassz eladó karaktert, majd frissítsd az adatait.');
 if(c.quantity&&out.order&&out.values.broker_fee===null)warnings.push('A broker fee nem ismert; frissítsd az eladó standingjét vagy add meg a struktúra díját.');
 if(out.material.stale||out.sale.stale||out.bp.stale)warnings.push('Korábbi piaci árakat is használunk.');
 if(job?.stale)warnings.push('Korábbi ipari indexet vagy adjusted price adatot használunk.');
 if(f.sale.endsWith(':split'))warnings.push('A split elméleti középár, nem közvetlenül teljesíthető ajánlat.');
 if(financeProfile)warnings.push(...financeProfile.warnings.filter(w=>out.order||/skill/i.test(w)));
 const sources=new Set([f.materials.split(':')[0],f.sale.split(':')[0]]);for(const s of sources)if(financeBooks[s]?.fetch_error||Object.keys(financeBooks[s]?.errors||{}).length)warnings.push('Néhány piaci ár nem frissült; ellenőrizd a market hozzáférését.');
 if(financeError)warnings.push(financeError);
 target.querySelectorAll('[data-finance-value]').forEach(el=>{const key=el.dataset.financeValue,value=out.values[key];el.textContent=key==='unit'?EveCosts.formatUnit(value):EveCosts.format(value);el.classList.toggle('danger',value!==null&&value<0n);});
 target.querySelector('[data-finance-warning]').textContent=[...new Set(warnings)].join(' ');
 target.querySelector('[data-finance-profile]').textContent=financeProfile?`Accounting ${financeProfile.accounting??'–'} · Broker Relations ${financeProfile.broker_relations??'–'} · ${financeProfile.location?.name||''} · ${financeProfile.sales_tax??'–'}% / ${financeProfile.broker_fee??'–'}%`:'';
 const busy=[...sources].some(s=>financeBooks[s]?.running);target.querySelector('[data-finance-status]').textContent=financeBusy?'Piaci árak ellenőrzése…':busy?'Piaci árak betöltése…':'';
 target.querySelector('[data-finance-refresh]').disabled=financeBusy||busy;
 const detail=target.querySelector('[data-finance-materials]');if(!detail.closest('details').open)return;
 detail.innerHTML=table(['Anyag','Mennyiség','Egységár','Anyagérték'],out.material.rows.map(r=>`<tr><td>${itemName(r.name)}</td><td class="num">${fmt(r.quantity)}</td><td class="num">${EveCosts.formatUnit(r.price)}</td><td class="num">${EveCosts.format(r.cents)}</td></tr>`),'finance-material-table');
 const jd=target.querySelector('[data-job-cost-details]');if(job)jd.innerHTML=table(['Termék','Job cost'],job.rows.map(r=>`<tr><td>${itemName(r.name)}</td><td class="num">${r.cents===null?'–':EveCosts.format(BigInt(r.cents))}</td></tr>`),'finance-job-table');
}
function bindProductionFinance(){
 const target=$('#production-finance'),key=financeKey,generation=financeGeneration;if(!target||target.hidden)return;
 target.querySelector('[data-finance-settings]').onclick=()=>openSettingsTab('market');
 target.querySelector('details').ontoggle=()=>applyProductionFinance();
 target.querySelector('[data-finance-refresh]').onclick=()=>void loadFinancePrices(true);
 target.querySelector('[data-finance-seller]').onclick=async()=>{try{if(!financePrefs?.seller_id)throw Error(EveI18n.t('Válassz eladó karaktert.'));tradeData=await api('/api/trade/seller/refresh',{character_id:financePrefs.seller_id,source:financePrefs.sale.split(':')[0],manual:true});void loadTrade(true);}catch(e){error(e.message);}};
 target.querySelectorAll('[data-finance-field]').forEach(input=>input.onchange=()=>{
  if(!financePrefs)return;const field=input.dataset.financeField,value=field==='seller_id'?Number(input.value)||null:field==='blueprints_isk'&&input.value===''?null:input.value;
  financePrefs={...financePrefs,[field]:value};financeError='';applyProductionFinance();clearTimeout(financeSaveTimer);
  const body={...financePrefs,plan_id:financeContext.plan_id};financeSaveTimer=setTimeout(async()=>{try{await api('/api/trade/plan',body);}catch(e){if(key===financeKey){financeError=e.message;applyProductionFinance();}}},300);
  if(['sale','seller_id'].includes(field))void loadFinanceProfile();if(['materials','sale'].includes(field))void loadFinancePrices();
 });
 if(financePrefs){applyProductionFinance();void loadFinancePrices();void loadFinanceProfile();return;}
 void (async()=>{try{const prefs=await api('/api/trade/plan'+(financeContext.plan_id?'?plan_id='+encodeURIComponent(financeContext.plan_id):''));if(key!==financeKey||generation!==financeGeneration)return;financePrefs=prefs;target.querySelectorAll('[data-finance-field]').forEach(input=>input.value=prefs[input.dataset.financeField]??'');applyProductionFinance();void loadFinancePrices();await loadTrade(true);void loadFinanceProfile();}catch(e){financeError=e.message;error(e.message);}})();
}
async function loadFinanceProfile(){
 if(!financePrefs||!financeContext||view!=='queue')return;const cid=financePrefs.seller_id,source=financePrefs.sale.split(':')[0],key=JSON.stringify([cid,source,tradeData?.settings.location_id,tradeData?.settings.structure_broker_fee]);
 if(!cid){financeProfile=null;financeProfileKey='';applyProductionFinance();return;}
 if(financeProfileKey!==key){financeProfile=null;applyProductionFinance();}financeProfileKey=key;
 try{const p=await api('/api/trade/seller?character_id='+cid+'&source='+source);if(key!==financeProfileKey)return;financeProfile=p;applyProductionFinance();}catch(e){if(key===financeProfileKey){financeProfile=null;financeError=e.message;applyProductionFinance();}}
}
async function loadFinancePrices(manual=false){
 if(!financePrefs||!financeContext||view!=='queue'||financeBusy)return;financeBusy=true;applyProductionFinance();clearTimeout(financeTimer);const key=financeKey,f={...financePrefs},c=financeContext,generation=financeGeneration;
 const ids=[...new Set([...c.materials.map(r=>r.id),...(c.plan.blueprint_shortages||[]).filter(r=>r.unit!=='run').map(r=>r.id),c.plan.product_id])];
 const sources=[...new Set([f.materials.split(':')[0],f.sale.split(':')[0]])];let again=false;
 try{await Promise.all(sources.map(async source=>{
  try{let data=await api('/api/prices?source='+source+'&ids='+ids.join(','));
   const needed=ids.filter(id=>{const q=data.quotes[id];return (!q||q.stale||manual)&&(manual||(data.retry_after?.[id]||0)<=Date.now()/1000);});
   if(needed.length){const next=await api('/api/prices/refresh',{source,ids:needed,manual});data={...data,...next,quotes:{...data.quotes,...next.quotes},errors:{...Object.fromEntries(Object.entries(data.errors||{}).filter(([id])=>!needed.includes(Number(id)))),...next.errors}};}
   if(key!==financeKey||generation!==financeGeneration)return;financeBooks[source]=data;again||=data.running;
  }catch(e){if(key===financeKey&&generation===financeGeneration)financeBooks[source]={...financeBooks[source],fetch_error:true};}
 }));}finally{financeBusy=false;applyProductionFinance();if(key!==financeKey||generation!==financeGeneration||JSON.stringify([f.materials,f.sale])!==JSON.stringify([financePrefs?.materials,financePrefs?.sale]))void loadFinancePrices();else if(again&&view==='queue')financeTimer=setTimeout(()=>void loadFinancePrices(),1200);}
}
