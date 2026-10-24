'use strict';
const moonImportPlaceholder='Másold ide a játék teljes scantáblázatát, akár több holdét egyszerre, vagy tölts be egy exportfájlt.';
window.addEventListener('eve-language-change',()=>{const input=$('#moon-import-form [name=text]');if(input)input.placeholder=EveI18n.t(moonImportPlaceholder);});
let moonTransferDraft=null,moonTransferBusy=false,moonTransferGeneration=0;
function openMoonTransfer(){
 if(moonEditing)return error('Előbb mentsd vagy zárd be a hold szerkesztőjét.');
 if(!moonTransferDraft)moonTransferDraft={format:'scan',text:'',existing:'skip',structure:'Metenox',rent_isk:'0',preview:null,message:''};
 renderMoonTransfer();
}
function renderMoonTransfer(){
 const target=$('#moon-transfer');if(!target||!moonTransferDraft)return;
 const d=moonTransferDraft,p=d.preview;
 target.innerHTML=panel('Holdak tömeges importja','JSON holdexport vagy a játékból másolt scaneredmény',`<form id="moon-import-form" class="panel-body"><div class="trade-settings-grid"><label>Importformátum<select name="format"><option value="scan" ${d.format==='scan'?'selected':''}>Játékbeli moon scan</option><option value="json" ${d.format==='json'?'selected':''}>EVE Műhely holdexport (JSON)</option></select></label><label>Meglévő holdak<select name="existing"><option value="skip" ${d.existing==='skip'?'selected':''}>Kihagyás</option><option value="update" ${d.existing==='update'?'selected':''}>Frissítés</option></select></label><label>Fájl betöltése<input id="moon-import-file" type="file" accept=".json,.txt,.tsv,text/plain,application/json,text/tab-separated-values">${d.fileName?`<small><span>Betöltött fájl:</span> <span data-i18n-skip>${esc(d.fileName)}</span></small>`:''}</label></div><div class="trade-settings-grid" ${d.format==='scan'?'':'hidden'}><label>Új scanholdak struktúrája<select name="structure"><option value="Metenox" ${d.structure==='Metenox'?'selected':''}>Metenox</option><option value="Athanor" ${d.structure==='Athanor'?'selected':''}>Athanor</option></select></label><label>Új scanholdak bérlete / 30 nap (ISK)<input name="rent_isk" type="number" min="0" max="1000000000000000" step="0.01" value="${esc(d.rent_isk)}"></label></div><label>Importálandó szöveg<textarea name="text" rows="7" maxlength="1048576" spellcheck="false" placeholder="${esc(EveI18n.t(moonImportPlaceholder))}">${esc(d.text)}</textarea></label><p>A scan Quantity értékét 100-zal szorozzuk százalékká. A holdat és az ércet azonosító alapján ellenőrizzük. Scanfrissítésnél csak az összetétel változik; a meglévő bérlet és struktúra megmarad. JSON-frissítésnél a fájlban szereplő holdbeállításokat vesszük át. A listából kimaradó holdakat nem töröljük.</p><div class="section-actions"><button class="button primary compact" id="moon-import-preview" type="submit" ${moonTransferBusy?'disabled':''}>Import előnézete</button><button class="button compact" type="button" id="moon-import-apply" ${moonTransferBusy||!p||!p.counts.new&&!p.counts.update?'disabled':''}>Előnézetben látható holdak importálása</button><button class="text-button" type="button" id="moon-import-cancel" ${moonTransferBusy?'disabled':''}>Mégse</button><small id="moon-import-status" role="status">${esc(d.message)}</small>${moonTransferBusy?'<progress aria-label="Holdimport feldolgozása"></progress>':''}</div><div id="moon-import-result">${p?moonImportPreview(p):''}</div></form>`);
 const form=$('#moon-import-form');form.querySelectorAll('input,select,textarea').forEach(el=>el.disabled=moonTransferBusy);
 form.oninput=form.onchange=e=>{
  if(e.target.id==='moon-import-file')return;
  moonTransferGeneration++;d.format=form.elements.format.value;d.existing=form.elements.existing.value;d.structure=form.elements.structure.value;d.rent_isk=form.elements.rent_isk.value;d.text=form.elements.text.value;d.preview=null;d.message='';dirty.moon_import=!!d.text;
  $('#moon-import-apply').disabled=true;$('#moon-import-result').innerHTML='';$('#moon-import-status').textContent='';
  if(e.target.name==='format')renderMoonTransfer();
 };
 $('#moon-import-file').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;const generation=++moonTransferGeneration;
  if(file.size>1048576){d.message='Az import szövege üres vagy nagyobb 1 MB-nál.';renderMoonTransfer();return;}
  try{const text=await file.text();if(generation!==moonTransferGeneration||moonTransferDraft!==d)return;d.text=text;d.fileName=file.name;d.format=file.name.toLowerCase().endsWith('.json')?'json':'scan';d.preview=null;d.message='';dirty.moon_import=true;renderMoonTransfer();}catch(e){d.message='A fájl nem olvasható.';renderMoonTransfer();}
 };
 $('#moon-import-cancel').onclick=()=>{moonTransferGeneration++;moonTransferDraft=null;delete dirty.moon_import;target.innerHTML='';};
 form.onsubmit=async e=>{e.preventDefault();if(moonTransferBusy)return;const generation=++moonTransferGeneration;moonTransferBusy=true;d.preview=null;d.message='Holdimport előnézetének ellenőrzése…';renderMoonTransfer();
  try{const result=await api('/api/moons/import/preview',moonImportBody(d));if(generation===moonTransferGeneration&&moonTransferDraft===d){d.preview=result;d.message='Az előnézet még nem mentette el a holdakat.';}}
  catch(e){if(generation===moonTransferGeneration&&moonTransferDraft===d)d.message=e.message;}
  finally{moonTransferBusy=false;if(moonTransferDraft===d)renderMoonTransfer();}
 };
 $('#moon-import-apply').onclick=async()=>{
  if(moonTransferBusy||!d.preview)return;moonTransferBusy=true;d.message='Holdak importálása…';renderMoonTransfer();
  try{const result=await api('/api/moons/import',{...moonImportBody(d),revision:d.preview.revision});moonTransferGeneration++;moonTransferDraft=null;delete dirty.moon_import;await refreshMoons(true);toast(`Holdimport kész: ${result.counts.new} új, ${result.counts.update} frissített, ${result.counts.skip} kihagyott.`);}
  catch(e){d.preview=null;d.message=e.message;}
  finally{moonTransferBusy=false;if(moonTransferDraft===d)renderMoonTransfer();}
 };
}
function moonImportBody(d){return {format:d.format,text:d.text,existing:d.existing,structure:d.structure,rent_isk:d.rent_isk};}
function moonImportPreview(p){
 const labels={new:'Új hold',update:'Frissítés',skip:'Kihagyás'};
 return `<p><strong>Új: ${fmt(p.counts.new)} · Frissítés: ${fmt(p.counts.update)} · Kihagyás: ${fmt(p.counts.skip)}</strong></p>`+moonTable(['Hold','Struktúra','Ércek és arányok','Arányösszeg','Bérlet / 30 nap','Egyéb / 30 nap','Importművelet','Ellenőrzés'],p.rows.map(r=>`<tr><td>${verbatim(r.name)}</td><td>${verbatim(r.structure)}</td><td>${r.ores.map(o=>`${itemName(o.name)} ${moonPercent(o.percent)}`).join('<br>')}</td><td class="num">${moonPercent(r.percent_total)}</td><td class="num">${EveCosts.format(EveCosts.money(r.rent_isk))}</td><td class="num">${EveCosts.format(EveCosts.money(r.other_cost_isk))}</td><td>${labels[r.action]}</td><td>${r.warnings.map(w=>`<span class="warning-text">${esc(w)}</span>`).join('<br>')}</td></tr>`),'import-preview');
}
async function exportMoons(button){
 button.disabled=true;
 try{const data=await api('/api/moons/export'),blob=new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json;charset=utf-8'}),filename='eve-moons-'+new Date().toLocaleDateString('sv-SE')+'.json';
  if(EveDesktop.active)await EveDesktop.saveBlob(blob,filename);
  else{const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 }catch(e){error(e.message);}finally{button.disabled=false;}
}
