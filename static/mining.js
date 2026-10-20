'use strict';
let miningData=null,miningRequest=null,miningGeneration=0,miningTab='characters',miningBasis='raw';
let miningFilters={period:'30',character:'',ore:'',start:'',end:''};
const miningTabs={characters:'Karakterenként',ores:'Ércenként',days:'Napi bontás',records:'Naplósorok'};
function miningQuery(){
  const p=new URLSearchParams();
  const utc=new Date().toISOString().slice(0,10);
  if(miningFilters.period==='custom'){
    if(miningFilters.start)p.set('start',miningFilters.start);
    if(miningFilters.end)p.set('end',miningFilters.end);
  }else{
    const d=new Date(utc+'T00:00:00Z');d.setUTCDate(d.getUTCDate()-(Number(miningFilters.period)||30)+1);
    p.set('start',miningFilters.period==='all'?'2003-01-01':d.toISOString().slice(0,10));p.set('end',utc);
  }
  if(miningFilters.character)p.set('character_id',miningFilters.character);
  if(miningFilters.ore)p.set('ore_id',miningFilters.ore);
  return p.toString();
}
async function refreshMining(){
  const generation=++miningGeneration,query=miningQuery();
  const request=api('/api/mining?'+query);miningRequest=request;
  try{const d=await request;if(generation!==miningGeneration)return;miningData=d;if(view==='mining')render();}
  catch(e){if(generation===miningGeneration&&view==='mining'){error(e.message);}}
  finally{if(generation===miningGeneration)miningRequest=null;}
}
function miningMoney(rows){return EveCosts.value(rows||[],jitaData.quotes,jitaMode);}
function miningAmount(v){return v.missing&&!v.rows.some(r=>r.quantity>0&&r.cents!==null)?'–':(v.missing?'≥ ':'')+EveCosts.format(v.cents);}
function miningValue(key,bucket){
  return `<td class="num" data-mining-value="${esc(key)}" data-mining-basis="raw">–</td><td class="num" data-mining-value="${esc(key)}" data-mining-basis="refined">–</td>`;
}
function miningNumber(n,places=3){return new Intl.NumberFormat('hu-HU',{maximumFractionDigits:places}).format(n);}
function miningVolume(b){return b.unknown_volume?'–':miningNumber(b.volume);}
let miningBuckets=new Map();
function applyMiningValues(){
  if(view!=='mining'||!miningData)return;
  $$('[data-mining-value]').forEach(el=>{
    const b=miningBuckets.get(el.dataset.miningValue);if(!b)return;
    const refined=el.dataset.miningBasis==='refined';
    const value=miningMoney(refined?b.materials:b.raw);
    const absent=refined&&b.unrefinable>0;
    el.textContent=absent&&!b.materials.length?'–':miningAmount(value)+(absent?' *':'');
    el.dataset.sortValue=value.missing||absent?'':String(Number(value.cents)/100);
  });
}
function renderMining(content){
  setHead('MINING LEDGER','Bányászati napló','Az összes hozzáadott karakter bányászata, Jita-értéke és becsült finomított kihozatala.');
  actions(`<button class="button compact" id="mining-sync" ${state.task.running?'disabled':''}>Bányászati naplók frissítése</button><button class="button compact" id="mining-export">CSV mentése</button>`);
  $('#mining-sync').onclick=()=>void startTask('/api/mining/sync');
  const d=miningData;
  if(!d){content.innerHTML=empty('Bányászati naplók betöltése…');$('#mining-export').disabled=true;if(!miningRequest)void refreshMining();return;}
  miningBuckets=new Map([['summary',d.summary],...d.by_character.map(r=>['c'+r.id,r]),...d.by_ore.map(r=>['o'+r.id,r]),...d.by_day.map(r=>['d'+r.date,r])]);
  const current=d.characters.filter(c=>!miningFilters.character||String(c.id)===miningFilters.character);
  const missing=current.filter(c=>c.needs_auth||c.error||!c.checked_at);
  content.innerHTML=`<section class="panel panel-body"><form id="mining-filters" class="mining-filters"><label>Időszak<select name="period">${Object.entries({'7':'Utolsó 7 nap','30':'Utolsó 30 nap','90':'Utolsó 90 nap',all:'Teljes helyi előzmény',custom:'Egyéni időszak'}).map(([id,name])=>`<option value="${id}" ${miningFilters.period===id?'selected':''}>${name}</option>`).join('')}</select></label><label>Karakter<select name="character"><option value="">Összes karakter</option>${d.characters.map(c=>`<option value="${c.id}" ${miningFilters.character===String(c.id)?'selected':''} data-i18n-skip>${esc(c.name)}</option>`).join('')}</select></label><label>Érc<select name="ore"><option value="">Összes érc</option>${d.ores.map(o=>`<option value="${o.id}" ${miningFilters.ore===String(o.id)?'selected':''} data-i18n-skip>${esc(o.name)}</option>`).join('')}</select></label><label>Értékelés<select name="basis"><option value="raw" ${miningBasis==='raw'?'selected':''}>Nyers érc</option><option value="refined" ${miningBasis==='refined'?'selected':''}>Finomított anyagok</option></select></label>${miningFilters.period==='custom'?`<label>Kezdő dátum (UTC)<input type="date" name="start" value="${esc(miningFilters.start||d.start)}" required></label><label>Záró dátum (UTC)<input type="date" name="end" value="${esc(miningFilters.end||d.end)}" required></label>`:''}<button class="button compact" type="submit">Szűrés alkalmazása</button></form><p class="footnote">${esc(d.start)} – ${esc(d.end)} · <span>A napló napjai UTC szerint értendők.</span></p></section>`;
  if(missing.length)content.innerHTML+=`<div class="banner warn"><span>Néhány karakter naplója hiányzik vagy nem frissült; az összesítés részleges lehet.</span> ${missing.map(c=>verbatim(c.name)).join(', ')} <button class="text-button" data-open-settings="access">Adathozzáférések megnyitása</button></div>`;
  else if(current.some(c=>c.stale))content.innerHTML+='<div class="banner warn">Korábbi bányászati naplóadatokból számolunk. A frissítésig a legutóbbi sikeres adatok láthatók.</div>';
  content.innerHTML+=`<div class="metrics mining-metrics"><div class="metric"><div class="metric-label">Kibányászott mennyiség</div><strong>${fmt(d.summary.quantity)}</strong><small>db</small></div><div class="metric"><div class="metric-label">Kibányászott térfogat</div><strong>${miningVolume(d.summary)}</strong><small>m³</small></div><div class="metric"><div class="metric-label">Bányászó karakterek</div><strong>${fmt(d.by_character.length)}</strong></div></div>`;
  content.innerHTML+=costSummary('mining-total',miningBasis==='raw'?d.summary.raw:d.summary.materials,miningBasis==='raw'?'Kibányászott ércek Jita-értéke':'Finomított anyagok Jita-értéke','A jelenlegi Jita-árakkal számolt bruttó becslés; nem korabeli eladási bevétel. A bányászati napló nem a jelenlegi készlet.',true);
  if(d.summary.unrefinable)content.innerHTML+='<div class="banner warn">Néhány tételhez nincs finomítási recept vagy kihozatal; a finomított érték részösszeg. A gázokat nem tekintjük finomítható ércnek.</div>';
  content.innerHTML+=`<p class="footnote"><span>Finomítás: nullsec Tatara, T2 rig, maximális skillek.</span> <span>Implant:</span> ${fmt(d.implant)}% · <span>Kihozatal:</span> ${d.refining_yield===null?'–':miningNumber(d.refining_yield*100,4)}%. <span>A teljes finomítási adagokat karakterenként és érctípusonként vonjuk össze a kiválasztott időszakban; a maradék ércet nem finomítjuk. Adók és díjak nélkül.</span></p>`;
  content.innerHTML+=`<div class="shopping-tabs" role="group" aria-label="Bányászati statisztikák">${Object.entries(miningTabs).map(([key,label])=>`<button data-mining-tab="${key}" aria-pressed="${miningTab===key}">${esc(label)}</button>`).join('')}</div>`;
  const heads=['Mennyiség (db)','Térfogat (m³)','Nyers érc értéke','Finomított érték'];
  const stats=(b,key)=>`<td class="num">${fmt(b.quantity)}</td><td class="num">${miningVolume(b)}</td>${miningValue(key,b)}`;
  if(['characters','ores'].includes(miningTab)){
    const chars=miningTab==='characters',rows=(chars?d.by_character:d.by_ore).map(b=>`<tr><td>${chars?verbatim(b.name):itemName(b.name)}</td>${stats(b,(chars?'c':'o')+b.id)}</tr>`);
    const total=`<tfoot><tr class="total-row"><td>Összesen</td>${stats(d.summary,'summary')}</tr></tfoot>`;
    const markup=table([chars?'Karakter':'Érc',...heads],rows,'mining-'+miningTab).replace('</tbody></table>','</tbody>'+total+'</table>');
    content.innerHTML+=panel(miningTabs[miningTab],'',markup);
  }else if(miningTab==='days'){
    const rows=d.by_day.map(b=>`<tr><td>${esc(b.date)}</td>${stats(b,'d'+b.date)}</tr>`);
    const total=`<tfoot><tr class="total-row"><td>Összesen</td>${stats(d.summary,'summary')}</tr></tfoot>`;
    const markup=table(['Dátum',...heads],rows,'mining-days').replace('</tbody></table>','</tbody>'+total+'</table>');
    content.innerHTML+=panel('Napi bontás','UTC',markup);
    content.innerHTML+='<p class="footnote">A napi táblázat külön mutatja a nyers és a finomított értéket, ugyanazzal a Jita-árazással, mint a felső összesítés. A finomítási adagok maradékát a következő napra visszük tovább a kiválasztott időszakon belül, karakterenként és érctípusonként. Az ISK-sorok kerekítése néhány fillér eltérést okozhat.</p>';
  }else{
    const rows=d.records.map(r=>`<tr><td>${esc(r.date)}</td><td>${verbatim(r.character_name)}</td><td data-i18n-skip>${esc(r.system_name)}</td><td>${itemName(r.name)}</td><td class="num">${fmt(r.quantity)}</td><td class="num">${r.volume===null?'–':miningNumber(r.volume)}</td>${costCell(r.type_id,r.quantity)}</tr>`);
    content.innerHTML+=panel(miningTabs[miningTab],'',rows.length?table(['Dátum','Karakter','Rendszer','Érc','Mennyiség (db)','Térfogat (m³)','Egységár','Nyers érc értéke'],rows,'mining-records'):empty('Nincs bányászati naplósor a kiválasztott időszakban'));
  }
  content.innerHTML+=`<details class="panel panel-body"><summary>Adatforrás és lefedettség</summary><p>Az ESI az elmúlt 30 nap bányászatát adja vissza, legfeljebb 10 perces gyorsítótárral. A letöltött napokat helyben megőrizzük. A frissítés nem duplázza meg a korábbi mennyiségeket; a régebbi, le nem töltött múlt nem állítható vissza.</p>${table(['Karakter','Utolsó sikeres lekérés','Következő frissítés','Hozzáférés'],d.characters.map(c=>`<tr><td>${verbatim(c.name)}</td><td>${c.checked_at?esc(date(c.checked_at)):'–'}</td><td>${c.expires?esc(date(c.expires)):'–'}</td><td>${esc(c.needs_auth?'Engedélyezés szükséges':c.error||'Olvasási engedély megadva')}</td></tr>`),'mining-access')}<button class="button compact" data-open-settings="access">Adathozzáférések megnyitása</button></details>`;
  $('#mining-filters').onsubmit=event=>{event.preventDefault();if(Object.keys(dirty).length&&!confirmUI('Vannak még nem alkalmazott módosítások. Elhagyod ezt az oldalt?'))return;dirty={};const f=new FormData(event.currentTarget);miningBasis=String(f.get('basis'));for(const k of ['period','character','ore','start','end'])if(f.has(k))miningFilters[k]=String(f.get(k));void refreshMining();};
  $('#mining-filters').elements.period.onchange=event=>{const value=event.target.value;if(value==='custom'||miningFilters.period==='custom'){miningFilters.period=value;render();}};
  $$('[data-mining-tab]').forEach(el=>el.onclick=()=>{if(Object.keys(dirty).length&&!confirmUI('Vannak még nem alkalmazott módosítások. Elhagyod ezt az oldalt?'))return;dirty={};miningTab=el.dataset.miningTab;render();});
  $('#mining-export').onclick=()=>csv(d.records.map(r=>[r.date,r.character_name,r.system_name,r.name,r.quantity,r.volume,...jitaCsv(r.type_id,r.quantity)]),['Dátum','Karakter','Rendszer','Érc','Mennyiség (db)','Térfogat (m³)','Árazás','Egységár','Nyers érc értéke'],'mining-ledger');
  const ids=[...new Set([...d.summary.raw,...d.summary.materials].map(r=>r.id))];
  bindJita(d.price_ids||ids);applyMiningValues();
}
