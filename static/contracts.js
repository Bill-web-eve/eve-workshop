'use strict';
let contractData=null,contractRequest=null,contractScope='personal',contractOwner='',contractStart='',contractEnd='',contractSelected=null,contractDetail=null,contractDetailRequest=null,contractRevision=0,contractError='';
const contractStatuses={outstanding:'Elfogadásra vár',in_progress:'Folyamatban',finished:'Teljesítve',finished_issuer:'Kiadó által lezárva',finished_contractor:'Elfogadó által lezárva',cancelled:'Visszavonva',rejected:'Elutasítva',failed:'Sikertelen',deleted:'Törölve',reversed:'Visszafordítva'};
const contractTypes={unknown:'Ismeretlen',item_exchange:'Tételcsere',auction:'Aukció',courier:'Futár',loan:'Kölcsön'};
const contractDate=s=>s?EveI18n.date(new Date(s),{year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'–';
const contractMoney=v=>v==null?'–':EveCosts.format(EveCosts.money(String(v)));
const contractKey=()=>JSON.stringify([contractScope,contractOwner,contractStart,contractEnd]);
async function loadContracts(force=false){
 const key=contractKey(),revision=contractRevision;
 if(contractRequest?.key===key&&!force)return contractRequest.promise;
 const params=new URLSearchParams({scope:contractScope});if(contractOwner)params.set('owner',contractOwner);if(contractStart)params.set('start',contractStart);if(contractEnd)params.set('end',contractEnd);
 const request={key};contractRequest=request;
 request.promise=(async()=>{try{
  const data=await api('/api/contracts?'+params);if(key!==contractKey()||revision!==contractRevision)return;
  contractData={...data,key};contractError='';if(view==='contracts')render();
 }catch(e){if(key===contractKey()&&revision===contractRevision){contractError=e.message;if(view==='contracts')render();}}finally{if(contractRequest===request){contractRequest=null;if(view==='contracts'&&key===contractKey()&&revision!==contractRevision&&!contractData)void loadContracts();}}})();return request.promise;
}
function changeContractScope(scope){contractScope=scope;contractOwner='';contractSelected=null;contractDetail=null;contractDetailRequest=null;contractData=null;contractError='';contractRevision++;render();}
function renderContracts(content){
 setHead('EVE-SZERZŐDÉSEK','Szerződések','Személyes és corporation-szerződések, helyi előzményekkel és állapotváltozásokkal.');$('#plan-status').hidden=true;
 actions('<button class="button compact" id="contract-reload">Mentett lista újraolvasása</button><button class="button primary compact" id="contract-sync">ESI-szerződések frissítése</button>');
 $('#contract-reload').onclick=()=>void loadContracts(true);$('#contract-sync').disabled=!!state.task.running;$('#contract-sync').onclick=()=>startTask('/api/contracts/sync');
 content.innerHTML=`<div class="shopping-tabs"><button data-contract-scope="personal" aria-pressed="${contractScope==='personal'}">Személyes</button><button data-contract-scope="corporation" aria-pressed="${contractScope==='corporation'}">Corporationok</button></div>`;
 if(contractData?.key!==contractKey()){
  content.innerHTML+=contractError?empty('A szerződések nem tölthetők be',contractError):empty('Szerződések betöltése…');$$('[data-contract-scope]').forEach(b=>b.onclick=()=>changeContractScope(b.dataset.contractScope));if(!contractError)void loadContracts();return;
 }
 const data=contractData;
 content.innerHTML+=`<form class="contract-controls panel panel-body" id="contract-filter"><label>${contractScope==='personal'?'Karakter':'Corporation'}<select id="contract-owner"><option value="">${contractScope==='personal'?'Minden karakter':'Összes corporation'}</option>${data.owners.map(c=>`<option data-i18n-skip value="${c.id}" ${String(c.id)===contractOwner?'selected':''}>${esc(c.name)}</option>`).join('')}</select></label><label>Kiadva ettől (EVE/UTC)<input type="date" id="contract-start" value="${esc(contractStart)}"></label><label>Kiadva eddig (EVE/UTC)<input type="date" id="contract-end" value="${esc(contractEnd)}"></label><button class="button compact" type="submit">Előzmények szűrése</button></form>`;
 content.innerHTML+=settingsShortcut('A szerződések új ESI-engedélyeit a Beállítások → Adathozzáférések oldalon adhatod meg.');
 const notices=data.sources.filter(s=>!s.authorized||s.error||!s.enabled||!s.fetched);
 if(notices.length)content.innerHTML+=`<div class="banner">${notices.map(s=>`<p>${verbatim(s.name)} · <span>${!s.enabled?'Figyelés kikapcsolva':!s.authorized?'Szerződésengedély szükséges':s.error?esc(s.error):'Még nincs betöltött szerződésadat'}</span></p>`).join('')}</div>`;
 if(data.truncated)content.innerHTML+='<div class="banner warn">Az első 10 000 szerződés látható. Szűkítsd a dátumot vagy a tulajdonost.</div>';
 content.innerHTML+=panel('Szerződések és előzmények',`${fmt(data.rows.length)} szerződés`,data.rows.length?table(['Szerződés','Típus','Állapot',contractScope==='personal'?'Karakter':'Corporation','Kiadó','Címzett','Elfogadó','Ár (ISK)','Jutalom (ISK)','Kiadva','Elfogadva','Lejárat','Indulási hely','Érkezési hely'],data.rows.map(r=>`<tr><td><button class="text-button" data-contract-id="${r.contract_id}"><span data-i18n-skip>${esc(r.title||'#'+r.contract_id)}</span></button><div class="batch-note">#${r.contract_id}</div></td><td>${esc(contractTypes[r.type]||r.type)}</td><td>${esc(contractStatuses[r.status]||r.status)}</td><td>${r.owners.map(c=>verbatim(c.name)).join(', ')}</td><td>${verbatim(r.issuer_name)}</td><td>${r.assignee_id?verbatim(r.assignee_name):'Nyilvános / nincs címzett'}</td><td>${verbatim(r.acceptor_name)}</td><td class="num" data-sort-value="${r.price??''}">${contractMoney(r.price)}</td><td class="num" data-sort-value="${r.reward??''}">${contractMoney(r.reward)}</td><td data-sort-value="${Date.parse(r.date_issued)}">${esc(contractDate(r.date_issued))}</td><td data-sort-value="${r.date_accepted?Date.parse(r.date_accepted):''}">${esc(contractDate(r.date_accepted))}</td><td data-sort-value="${Date.parse(r.date_expired)}">${esc(contractDate(r.date_expired))}</td><td>${r.start_location_name?verbatim(r.start_location_name):r.start_location_id||'–'}</td><td>${r.end_location_name?verbatim(r.end_location_name):r.end_location_id||'–'}</td></tr>`),'contracts-'+contractScope):empty('Nincs ilyen szerződés','Engedélyezd az olvasást, frissítsd az EVE-adatokat, vagy módosítsd a dátumszűrést.'));
 content.innerHTML+='<p class="footnote">Az ESI az elmúlt 30 nap szerződéseit és a folyamatban lévőket adja vissza. A már beolvasott helyi előzményeket megőrizzük. Az első betöltés nem indít régi értesítéseket. Automatikus ellenőrzés legfeljebb 15 percenként; a kézi frissítés is tiszteletben tartja az EVE 5 perces gyorsítótárát. A dátumszűrés EVE-időben, a megjelenített időpontok helyi időben értendők.</p><div id="contract-detail"></div>';
 $$('[data-contract-scope]').forEach(b=>b.onclick=()=>changeContractScope(b.dataset.contractScope));
 $('#contract-filter').onsubmit=e=>{e.preventDefault();contractOwner=$('#contract-owner').value;contractStart=$('#contract-start').value;contractEnd=$('#contract-end').value;contractData=null;contractSelected=null;contractDetail=null;contractRevision++;render();};
 $$('[data-contract-id]').forEach(b=>b.onclick=()=>{contractSelected=Number(b.dataset.contractId);contractDetail=null;renderContractDetail();});
 renderContractDetail();
}
async function renderContractDetail(){
 const target=$('#contract-detail');if(!target||!contractSelected)return;
 const row=contractData.rows.find(r=>r.contract_id===contractSelected);if(!row)return;
 const key=JSON.stringify([contractScope,row.owner_id,row.contract_id]);
 if(contractDetail?.key!==key){
  target.innerHTML=empty('Szerződés részleteinek betöltése…');if(contractDetailRequest===key)return;contractDetailRequest=key;
  try{const data=await api('/api/contracts/details?'+new URLSearchParams({scope:contractScope,owner:row.owner_id,id:row.contract_id}));if(contractDetailRequest!==key)return;contractDetail={...data,key};renderContractDetail();}
  catch(e){if(contractDetailRequest===key)target.innerHTML=empty('A szerződés részletei nem érhetők el',e.message);}finally{if(contractDetailRequest===key)contractDetailRequest=null;}return;
 }
 const d=contractDetail,r=d.contract;
 target.innerHTML=panel({name:r.title||'#'+r.contract_id,suffix:' · #'+r.contract_id},'',`<div class="panel-body contract-summary"><div><span>Típus</span><strong>${esc(contractTypes[r.type]||r.type)}</strong></div><div><span>Állapot</span><strong>${esc(contractStatuses[r.status]||r.status)}</strong></div><div><span>Ár (ISK)</span><strong>${contractMoney(r.price)}</strong></div><div><span>Jutalom (ISK)</span><strong>${contractMoney(r.reward)}</strong></div><div><span>Fedezet (ISK)</span><strong>${contractMoney(r.collateral)}</strong></div><div><span>Kivásárlás (ISK)</span><strong>${contractMoney(r.buyout)}</strong></div><div><span>Térfogat (m³)</span><strong>${r.volume==null?'–':fmt(r.volume)}</strong></div><div><span>Teljesítési idő (nap)</span><strong>${r.days_to_complete??'–'}</strong></div></div>`+(d.error?`<p class="panel-body warning-text">${esc(d.error)}</p>`:'')+(d.items?.length?table(['Termék','Mennyiség','Szerződésbeli szerep','Példánytípus'],d.items.map(i=>`<tr><td>${itemName(i.name)}</td><td class="num">${fmt(i.quantity)}</td><td>${i.is_included?'Felajánlott':'Kért'}</td><td>${i.raw_quantity===-2?'BPC':i.raw_quantity===-1?'Egyedi / BPO':'Kötegelt'}</td></tr>`),'contract-items'):'<p class="panel-body">Az ESI nem adott elérhető tétellistát ehhez a szerződéshez.</p>')+table(['Helyben észlelve','Állapot','Elfogadva','Teljesítve'],d.history.map(h=>`<tr><td data-sort-value="${h.at}">${esc(EveI18n.date(h.at*1000))}</td><td>${esc(contractStatuses[h.status]||h.status)}</td><td>${esc(contractDate(h.contract.date_accepted))}</td><td>${esc(contractDate(h.contract.date_completed))}</td></tr>`),'contract-history'));
}
