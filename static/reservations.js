'use strict';
let reservationOrderDraft=null,reservationOrderBase=null,reservationOrderScope=null,reservationSaving=false;
function resetReservationDraft(){reservationOrderDraft=null;reservationOrderBase=null;reservationOrderScope=null;delete dirty.reservation_order;}
function activeReservationPlans(){return scopedPlans().filter(p=>p.reserve_active).sort((a,b)=>(a.reserved_at||a.created)-(b.reserved_at||b.created)||a.created-b.created||a.id.localeCompare(b.id));}
function moveReservation(id,direction){
 if(reservationSaving)return;
 if(!reservationOrderDraft){reservationOrderDraft=activeReservationPlans().map(p=>p.id);reservationOrderBase=state.reservation_revision;reservationOrderScope=corporationId;}
 const i=reservationOrderDraft.indexOf(id),j=i+direction;if(i<0||j<0||j>=reservationOrderDraft.length)return;
 [reservationOrderDraft[i],reservationOrderDraft[j]]=[reservationOrderDraft[j],reservationOrderDraft[i]];dirty.reservation_order=true;render();
}
async function refreshAfterReservationChange(){
 await reloadState();if(productId)await calculate(false);else render();
}
function renderReservations(content){
 setHead('KÉSZLETFELHASZNÁLÁS','Foglalások','A mentett tervek megmaradnak, ha kikapcsolod a foglalásukat. Felülről lefelé kapnak készletet és jobkimenetet.');$('#plan-status').hidden=true;
 const pool=scopedPlans(),active=activeReservationPlans(),inactive=pool.filter(p=>!p.reserve_active),draft=!!reservationOrderDraft;
 const stale=draft&&(reservationOrderScope!==corporationId||reservationOrderBase!==state.reservation_revision),waiting=!!state.delivery_wait||!!state.reservation_error;
 const ordered=draft?[...reservationOrderDraft.map(id=>active.find(p=>p.id===id)).filter(Boolean),...active.filter(p=>!reservationOrderDraft.includes(p.id))]:active;
 const scopes=[{id:null,name:'Személyes'},...state.corporations.map(c=>({id:c.id,name:'Corp · '+c.name}))];
 actions('<button class="button compact" id="reservation-refresh">Lista frissítése</button>');$('#reservation-refresh').disabled=reservationSaving||draft;$('#reservation-refresh').onclick=async()=>{try{await reloadState();render();}catch(e){error(e.message);}};
 content.innerHTML=`<div class="saved-categories" role="group" aria-label="Foglalások gyártási körei">${scopes.map(s=>`<button class="button compact" data-reservation-scope="${s.id??''}" aria-pressed="${s.id===corporationId}" ${reservationSaving||draft?'disabled':''}>${s.id===null?esc(s.name):verbatim(s.name)}</button>`).join('')}</div>`;
 if(waiting)content.innerHTML+=`<div class="banner warn"><strong>A foglalások újraszámítása friss készletadatra vár.</strong><div>A foglalás kikapcsolható. Bekapcsolás és sorrendmentés a friss készlet megérkezése után lehetséges.</div>${state.delivery_wait?`<div>Legkorábbi frissítési próbálkozás: ${esc(deliveryRetryTimestamp(state.delivery_wait.retry_at))}.</div>`:`<div>${esc(state.reservation_error)}</div>`}</div>`;
 if(stale)content.innerHTML+='<div class="banner warn">A foglalások megváltoztak. Vond vissza a sorrend tervezetét, és rendezd újra a friss listát.</div>';
 const card=(p,index,isActive)=>`<div class="reservation-row ${p.id===reservationDetailId?'selected':''}"><span class="reservation-position">${isActive?index+1:'–'}</span><div class="reservation-info"><strong>${verbatim(p.name)}</strong><small>${itemName(p.product_name)} · ${fmt(p.quantity)} db</small><small>${p.allocation?`${fmt(p.allocation.reserved_types)} terméktípus foglalva`:isActive?'A kiosztás még nem ellenőrizhető.':'A terv nincs törölve; nem foglal készletet.'}</small></div><label class="reservation-switch"><input type="checkbox" role="switch" data-reservation-active="${esc(p.id)}" aria-label="${esc(p.name)} – Foglalás" ${isActive?'checked':''} ${reservationSaving||draft||waiting&&!isActive?'disabled':''}><span>${isActive?'Foglalás aktív':'Foglalás kikapcsolva'}</span></label><div class="reservation-row-actions">${isActive?`<button class="button compact" data-reservation-move="${esc(p.id)}" data-direction="-1" aria-label="${esc(p.name)} – Előrébb" ${reservationSaving||index===0?'disabled':''}>↑</button><button class="button compact" data-reservation-move="${esc(p.id)}" data-direction="1" aria-label="${esc(p.name)} – Hátrébb" ${reservationSaving||index===ordered.length-1?'disabled':''}>↓</button><button class="text-button" data-reservation-detail="${esc(p.id)}" ${reservationSaving?'disabled':''}>Lefoglalt tételek</button>`:''}</div></div>`;
 content.innerHTML+=panel('Aktív foglalások',draft?'Sorrend tervezete':'Mentett elsőbbségi sorrend',`<div class="reservation-order">${ordered.length?ordered.map((p,i)=>card(p,i,true)).join(''):empty('Nincs aktív foglalás','A kikapcsolt terveknél a kapcsolóval indítható új foglalás.')}</div><div class="panel-body section-actions"><button class="button primary compact" id="reservation-order-save" ${!draft||reservationSaving||stale||waiting?'disabled':''}>Sorrend mentése</button><button class="button compact" id="reservation-order-cancel" ${!draft||reservationSaving?'disabled':''}>Módosítások visszavonása</button></div>`);
 if(inactive.length)content.innerHTML+=panel('Kikapcsolt foglalások',`${fmt(inactive.length)} megmaradó terv`,`<div class="reservation-order">${inactive.map((p,i)=>card(p,i,false)).join('')}</div>`);
 content.innerHTML+='<p class="footnote">Az első terv kap először készletet, folyamatban lévő kimenetet és BPC-runokat. Kikapcsoláskor a terv megmarad, a foglalása felszabadul. Visszakapcsoláskor a sorrend végére kerül. A személyes és az egyes corporationök sorrendje külön állítható. A tételrészletek a mentett sorrend szerinti kiosztást mutatják.</p><div id="reservation-detail"></div>';
 $$('[data-reservation-scope]').forEach(b=>b.onclick=()=>setProductionScope(Number(b.dataset.reservationScope)||null));
 $$('[data-reservation-move]').forEach(b=>b.onclick=()=>moveReservation(b.dataset.reservationMove,Number(b.dataset.direction)));
 $('#reservation-order-cancel').onclick=()=>{resetReservationDraft();render();};
 $('#reservation-order-save').onclick=async()=>{
  if(!reservationOrderDraft||reservationSaving||stale||waiting)return;
  reservationSaving=true;render();try{await api('/api/plans/reservations/order',{corporation_id:corporationId,ids:reservationOrderDraft,revision:reservationOrderBase});resetReservationDraft();await refreshAfterReservationChange();toast('Foglalási sorrend mentve.');}catch(e){error(e.message);}finally{reservationSaving=false;render();}
 };
 $$('[data-reservation-active]').forEach(input=>input.onchange=async()=>{
  if(reservationSaving||draft)return;const id=input.dataset.reservationActive,active=input.checked,revision=state.reservation_revision;
  reservationSaving=true;render();try{await api('/api/plans/reservation',{id,active,revision});await refreshAfterReservationChange();toast(active?'A foglalás bekapcsolva.':'A foglalás kikapcsolva; a terv megmaradt.');}catch(e){error(e.message);}finally{reservationSaving=false;render();}
 });
 $$('[data-reservation-detail]').forEach(b=>b.onclick=()=>{reservationDetailId=b.dataset.reservationDetail;render();$('#reservation-detail').scrollIntoView?.({block:'nearest',behavior:'smooth'});});
 renderReservationDetails();
}
