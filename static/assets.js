'use strict';
let inventoryMode='plan',assetCorporationId=null,assetData=null,assetRevision=0,assetRequest=null,assetError='',assetErrorKey='';
let assetQuery='',assetOwner='',assetPage=0,assetFiltersOpen=false,assetSort={key:'name',direction:1};
let assetFilters={name:'',owner:'',quantity:'',location:'',state:''};
const assetPageSize=100;
const assetState=row=>({packaged:'Becsomagolt / halmozott',singleton:'Egyedi / kibontott',blueprint_copy:'Blueprintmásolat'}[row.state]||row.state);
function inventoryTabs(){return `<div class="segmented asset-tabs" role="group" aria-label="Készletnézet"><button class="button compact ${inventoryMode==='plan'?'primary':''}" data-inventory-mode="plan" aria-pressed="${inventoryMode==='plan'}">A terv készlete</button><button class="button compact ${inventoryMode==='personal'?'primary':''}" data-inventory-mode="personal" aria-pressed="${inventoryMode==='personal'}">Összes személyes item</button><button class="button compact ${inventoryMode==='corporation'?'primary':''}" data-inventory-mode="corporation" aria-pressed="${inventoryMode==='corporation'}">Corporation teljes készlete</button></div>`;}
function bindInventoryTabs(){
 $$('[data-inventory-mode]').forEach(button=>button.onclick=()=>{
  if(inventoryMode===button.dataset.inventoryMode)return;
  if(Object.keys(dirty).length){error('Előbb alkalmazd a még nem mentett készlet- vagy blueprintmódosításokat.');return;}
  inventoryMode=button.dataset.inventoryMode;assetOwner='';assetPage=0;assetError='';assetErrorKey='';
  if(inventoryMode==='corporation'&&!state.corporations.some(c=>c.id===assetCorporationId))assetCorporationId=corporationId||state.corporations[0]?.id||null;
  render();
 });
}
function renderInventoryEmpty(content){
 if(deliveryWait)renderDeliveryWait(content);
 else{setHead('KÉSZLET','A terv készlete','A teljes EVE-készlet terv nélkül is böngészhető.');content.innerHTML=empty('Válassz tervet, vagy nyisd meg a teljes készletet');}
 content.insertAdjacentHTML('afterbegin',inventoryTabs());bindInventoryTabs();
}
function assetRows(){
 const collator=new Intl.Collator(EveI18n.locale,{numeric:true,sensitivity:'base'});
 const values=r=>({name:r.name,owner:r.owner_name,quantity:r.quantity,location:[r.location_id??'–',r.location_flag].join(' · '),state:EveI18n.t(assetState(r))});
 return (assetData?.rows||[]).filter(r=>{
  if(assetOwner&&String(r.owner_id)!==assetOwner)return false;
  const v=values(r);
  if(assetQuery&&!EveTables.matches([r.name,r.type_id,r.owner_name,v.location,v.state].join(' '),assetQuery))return false;
  return Object.entries(assetFilters).every(([key,q])=>!q||EveTables.matches(key==='name'?r.name+' '+r.type_id:v[key],q));
 }).sort((a,b)=>{const x=values(a)[assetSort.key],y=values(b)[assetSort.key];return assetSort.direction*(typeof x==='number'?x-y:collator.compare(String(x),String(y)));});
}
function renderAssetInventory(content){
 setHead('KÉSZLET','Teljes EVE-készlet','A tervtől független keresés; a kibontott tárgyak és blueprintek is láthatók.');
 $('#plan-status').hidden=true;
 actions('<button id="asset-reload" class="button compact">Betöltött készlet újraolvasása</button>'+exportButton());
 const cid=inventoryMode==='corporation'?assetCorporationId:null,key=inventoryMode+':'+(cid||'');
 if(assetData&&assetData.key!==key)assetData=null;
 if(assetErrorKey!==key)assetError='';
 content.innerHTML=inventoryTabs()+`<div class="asset-toolbar">${inventoryMode==='corporation'?`<label>Corporation<select id="asset-corporation"><option value="">Válassz corporationt</option>${state.corporations.map(c=>`<option data-i18n-skip value="${c.id}" ${cid===c.id?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label>`:''}<label class="asset-search">Keresés az összes itemben<input type="search" id="asset-query" value="${esc(assetQuery)}" placeholder="Item neve, típusazonosító vagy hely…"></label>${inventoryMode==='personal'?'<label>Karakter<select id="asset-owner"><option value="">Minden karakter</option></select></label>':''}</div><p class="footnote">Ez a nézet a letöltött EVE-készletet mutatja, tervfoglalások és kézi felülírások levonása nélkül. A személyes és a corp-készlet külön marad. Friss EVE-adatokhoz használd az EVE-frissítés gombot.</p><div id="asset-results" aria-live="polite"></div>`;
 bindInventoryTabs();
 $('#asset-reload').onclick=()=>{assetData=null;assetError='';assetRevision++;render();};
 $('#asset-query').oninput=e=>{assetQuery=e.target.value;assetPage=0;drawAssetRows();};
 const corp=$('#asset-corporation');if(corp)corp.onchange=e=>{assetCorporationId=Number(e.target.value)||null;assetPage=0;assetOwner='';render();};
 $('#export-csv').onclick=()=>csv(assetRows().map(r=>[r.name,r.type_id,r.owner_name,r.quantity,r.location_id??'',r.location_flag,EveI18n.t(assetState(r))]),['Termék','Típusazonosító',inventoryMode==='personal'?'Karakter':'Corporation','Mennyiség','Helyazonosító','Tárolási hely','Állapot'],'teljes-keszlet');
 if(inventoryMode==='corporation'&&!cid){$('#asset-results').innerHTML=empty('Válassz corporationt a készlet böngészéséhez');$('#export-csv').disabled=true;return;}
 if(assetData?.key===key){populateAssetOwners();drawAssetRows();return;}
 $('#export-csv').disabled=true;
 $('#asset-results').innerHTML=assetError?empty('A teljes készlet nem tölthető be',assetError):empty('Teljes készlet betöltése…');
 if(assetError)return;
 if(assetRequest?.key===key&&assetRequest.revision===assetRevision)return;
 const request={key,revision:assetRevision};assetRequest=request;
 api('/api/assets'+(cid?'?corporation_id='+encodeURIComponent(cid):'')).then(data=>{
  if(request.revision!==assetRevision||assetRequest!==request)return;
  assetData={...data,key};assetError='';
  if(view==='inventory'&&inventoryMode+':'+(inventoryMode==='corporation'?assetCorporationId||'':'')===key)render();
 }).catch(e=>{if(assetRequest===request&&request.revision===assetRevision){assetError=e.message;assetErrorKey=key;if(view==='inventory'&&inventoryMode+':'+(inventoryMode==='corporation'?assetCorporationId||'':'')===key)render();}}).finally(()=>{if(assetRequest===request)assetRequest=null;});
}
function populateAssetOwners(){
 const select=$('#asset-owner');if(!select)return;
 if(assetOwner&&!assetData.sources.some(o=>String(o.id)===assetOwner))assetOwner='';
 select.innerHTML='<option value="">Minden karakter</option>'+assetData.sources.map(o=>`<option data-i18n-skip value="${o.id}">${esc(o.name)}</option>`).join('');select.value=assetOwner;
 select.onchange=e=>{assetOwner=e.target.value;assetPage=0;drawAssetRows();};
}
function drawAssetRows(){
 if(!assetData||!$('#asset-results'))return;
 const rows=assetRows(),pages=Math.max(1,Math.ceil(rows.length/assetPageSize));assetPage=Math.max(0,Math.min(assetPage,pages-1));
 const visible=rows.slice(assetPage*assetPageSize,(assetPage+1)*assetPageSize),sources=assetData.sources;
 const missing=sources.filter(s=>!s.available),stale=sources.filter(s=>s.stale);
 const owner=inventoryMode==='personal'?'Karakter':'Corporation';
 const heads=[['name','Termék'],['owner',owner],['quantity','Mennyiség'],['location','Helyazonosító / tárolási hely'],['state','Állapot']];
 const sortHeaders=heads.map(([key,label])=>`<th scope="col" aria-sort="${assetSort.key===key?(assetSort.direction===1?'ascending':'descending'):'none'}"><button class="table-sort" data-asset-sort="${key}">${label}<span class="table-sort-icon" aria-hidden="true">↕</span></button></th>`).join('');
 const ownerFilter=inventoryMode==='personal'?`<select data-asset-owner-filter aria-label="Karakter – oszlopszűrő"><option value="">Minden karakter</option>${sources.map(o=>`<option data-i18n-skip value="${o.id}" ${assetOwner===String(o.id)?'selected':''}>${esc(o.name)}</option>`).join('')}</select>`:`<input type="search" data-asset-filter="owner" aria-label="Corporation – oszlopszűrő" placeholder="Szűrés…" value="${esc(assetFilters.owner)}">`;
 const filters=heads.map(([key,label])=>`<td>${key==='owner'?ownerFilter:`<input type="search" data-asset-filter="${key}" aria-label="${label} – oszlopszűrő" placeholder="Szűrés…" value="${esc(assetFilters[key])}">`}</td>`).join('');
 const tools=`<div class="table-tools"><span>${fmt(rows.length)} / ${fmt(assetData.rows.length)} <span>készletsor</span> · ${fmt(new Set(rows.map(r=>r.type_id)).size)} <span>itemtípus</span> · ${fmt(rows.reduce((n,r)=>n+r.quantity,0))} <span>db</span></span><div class="table-tool-actions"><button class="text-button" id="asset-filters" aria-controls="asset-column-filters" aria-expanded="${assetFiltersOpen}">${assetFiltersOpen?'Szűrők bezárása':'Szűrők megnyitása'}</button><button class="text-button" id="asset-reset">Rendezés és oszlopszűrők törlése</button></div></div>`;
 $('#asset-results').innerHTML=(missing.length?`<div class="banner warn"><span>Még nincs betöltött EVE-készlet:</span> ${missing.map(s=>verbatim(s.name)).join(', ')}</div>`:'')+(stale.length?`<div class="banner"><span>Korábbi készletadatot mutatunk:</span> ${stale.map(s=>verbatim(s.name)).join(', ')}</div>`:'')+`<div class="table-block">${tools}<div class="table-scroll"><table class="data-table all-assets-table"><thead><tr>${sortHeaders}</tr><tr class="table-filters" id="asset-column-filters" ${assetFiltersOpen?'':'hidden'}>${filters}</tr></thead><tbody>${visible.map(r=>`<tr><td><div class="item-name">${itemName(r.name)}<small>${r.type_id}</small></div></td><td>${verbatim(r.owner_name)}</td><td class="num">${fmt(r.quantity)}</td><td>${esc(r.location_id??'–')}<div class="batch-note" data-i18n-skip>${esc(r.location_flag)}</div></td><td>${assetState(r)}</td></tr>`).join('')||'<tr><td colspan="5">Nincs találat a teljes készletben.</td></tr>'}</tbody></table></div><div class="asset-pagination"><button class="button compact" id="asset-prev" ${assetPage===0?'disabled':''}>←</button><span>${assetPage+1} / ${pages} · <span>100 sor oldalanként</span></span><button class="button compact" id="asset-next" ${assetPage===pages-1?'disabled':''}>→</button></div></div><details><summary>Készletadatok ellenőrzési ideje</summary>${sources.map(s=>`<p>${verbatim(s.name)} · ${date(s.fetched)}</p>`).join('')}</details>`;
 $('#export-csv').disabled=!rows.length;
 $('#asset-filters').onclick=()=>{assetFiltersOpen=!assetFiltersOpen;drawAssetRows();};
 $('#asset-reset').onclick=()=>{assetFilters={name:'',owner:'',quantity:'',location:'',state:''};assetOwner='';assetSort={key:'name',direction:1};assetPage=0;populateAssetOwners();drawAssetRows();};
 $$('[data-asset-sort]').forEach(b=>b.onclick=()=>{const key=b.dataset.assetSort;assetSort={key,direction:assetSort.key===key?-assetSort.direction:1};assetPage=0;drawAssetRows();});
 $$('[data-asset-filter]').forEach(input=>input.oninput=e=>{const key=input.dataset.assetFilter,pos=input.selectionStart;assetFilters[key]=input.value;assetPage=0;drawAssetRows();const next=$(`[data-asset-filter="${key}"]`);next.focus();if(pos!=null)next.setSelectionRange?.(pos,pos);});
 const select=$('[data-asset-owner-filter]');if(select)select.onchange=e=>{assetOwner=e.target.value;assetPage=0;populateAssetOwners();drawAssetRows();};
 $('#asset-prev').onclick=()=>{assetPage--;drawAssetRows();};$('#asset-next').onclick=()=>{assetPage++;drawAssetRows();};
}
window.addEventListener('eve-language-change',()=>{if(typeof view!=='undefined'&&view==='inventory'&&inventoryMode!=='plan'&&assetData)drawAssetRows();});
