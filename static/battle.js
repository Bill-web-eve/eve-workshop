'use strict';
let fleetSidesSaving=false;
function battleSideName(side){return side.name?esc(side.name):esc(EveI18n.t('Oldal'))+' '+(side.id+1);}
function battleMoney(value,field='cents',missing='missing'){
  return value[missing]===value.count&&value.count?'–':(value[missing]?'≥ ':'')+EveCosts.format(BigInt(value[field]));
}
function renderBattleReport(session,incomplete){
  const b=session.battle;if(!b)return '';
  const option=(id,label,chosen)=>`<option value="${id}" ${chosen?'selected':''}>${label}</option>`;
  function group(g){
    const kind={alliance:'Alliance',corporation:'Corporation',character:'Karakter'}[g.kind]||g.kind;
    const image=['alliance','corporation'].includes(g.kind)?`<img src="https://images.evetech.net/${g.kind==='alliance'?'alliances':'corporations'}/${g.id}/logo?size=64" width="24" height="24" alt="" loading="lazy">`:'';
    return `<div class="battle-group" draggable="true" data-battle-group="${esc(g.key)}"><div class="battle-group-title">${image}<strong data-i18n-skip>${esc(g.name)}</strong>${g.own?'<span class="badge good">Saját karakter</span>':''}</div><div class="battle-group-detail"><span>${EveI18n.t(kind)}</span> · ${fmt(g.pilot_count)} <span>pilóta</span> · ${fmt(g.loss_value.count)} <span>veszteség</span> · ${battleMoney(g.loss_value)}</div><label><span>Oldal</span><select data-battle-move="${esc(g.key)}" aria-label="${esc(EveI18n.t('Csoport áthelyezése')+': '+g.name)}">${option(-1,EveI18n.t('Besorolatlan'),g.side===-1)}${b.sides.map(s=>option(s.id,battleSideName(s),g.side===s.id)).join('')}</select><small>${EveI18n.t(g.manual?'Kézi besorolás':'Becsült besorolás')}${g.conflicts?' · '+EveI18n.t('Ellentmondó lövési kapcsolat'):''}</small></label></div>`;
  }
  function losses(side){
    const ids=new Set(side.loss_ids),rows=session.rows.filter(k=>ids.has(k.id));
    return rows.length?`<details class="battle-losses" data-fleet-detail="battle-losses-${side.id}"><summary>${EveI18n.t('Veszteségek')} (${rows.length})</summary>${table(['Killmail','Megsemmisült hajó','Érték (ISK)'],rows.map(k=>`<tr><td data-sort-value="${k.id}" data-filter-value="${esc(k.ship)} #${k.id}">${fleetLink(k)}</td><td>${itemName(k.ship)}</td><td class="num">${k.value==null?'–':fmt(Math.round(k.value))}</td></tr>`),'battle-losses-'+side.id)}</details>`:'';
  }
  function card(side,unassigned=false){
    return `<section class="battle-side" data-battle-side="${side.id}"><h3>${unassigned?EveI18n.t('Besorolatlan'):battleSideName(side)}</h3><div class="battle-side-value">${battleMoney(side.loss_value)}</div><div class="footnote"><span>Ténylegesen megsemmisült:</span> ${battleMoney(side.loss_value,'destroyed_cents','destroyed_missing')}</div><div class="battle-counts"><span>${fmt(side.pilot_count)} <span>pilóta</span></span><span>${fmt(side.loss_value.count)} <span>veszteség</span></span><span>${fmt(side.kill_count)} kill</span></div>${side.friendly_fire?'<div class="battle-conflict">'+EveI18n.t('Azonos oldalra sorolt csoportok egymásra is lőttek.')+' '+fmt(side.friendly_fire)+' killmail</div>':''}<div class="battle-groups">${side.groups.length?side.groups.map(group).join(''):'<p class="footnote">Nincs ide sorolt alliance vagy corporation.</p>'}</div>${losses(side)}</section>`;
  }
  const totalMissing=[...b.sides,b.unassigned].some(side=>side.loss_value.missing||side.loss_value.destroyed_missing);
  const relations=table(['Támadó oldal','Veszteséget szenvedő oldal','Killmailek'],b.relationships.map(r=>`<tr><td>${r.attacker<0?EveI18n.t('Besorolatlan'):battleSideName(b.sides[r.attacker])}</td><td>${r.victim<0?EveI18n.t('Besorolatlan'):battleSideName(b.sides[r.victim])}</td><td class="num">${fmt(r.killmails)}</td></tr>`),'battle-relationships');
  return `<section id="fleet-battle" class="battle-report"><div class="battle-heading"><h2>Szemben álló felek</h2><div class="battle-controls"><label><span>Felek száma</span><select id="battle-side-count">${option('auto',EveI18n.t('Automatikus')+' ('+b.side_count+')',b.configured_count==null)}${[2,3,4].map(n=>option(n,String(n),b.configured_count===n)).join('')}</select></label><button id="battle-reset" class="button compact">Automatikus besorolás visszaállítása</button></div></div><p class="footnote">A közös célpontokra lövés együttműködésre, az egymásra lövés szembenállásra utal. A besorolás becslés. Egy alliance teljes csoportja a választóval vagy áthúzással mozgatható; a kézi döntés ehhez a sessionhöz mentődik.</p>${incomplete||totalMissing?'<div class="banner warn">Az oldalak veszteségértéke részösszeg: a riport vagy az értékadatok még hiányosak.</div>':''}<div class="battle-sides" data-count="${b.side_count}">${b.sides.map(s=>card(s)).join('')}</div>${b.unassigned.groups.length||b.unassigned.loss_value.count?`<details data-fleet-detail="battle-unassigned" class="battle-unassigned" ${b.unassigned.loss_value.count?'open':''}><summary>${EveI18n.t('Besorolatlan')} · ${fmt(b.unassigned.pilot_count)} ${EveI18n.t('pilóta')} · ${battleMoney(b.unassigned.loss_value)}</summary><p class="footnote">Az elkülönülő, nem azonosítható vagy ellentmondásos szereplőket nem soroljuk biztosan egyik félhez sem. Kézzel elhelyezheted a csoportjaikat.</p>${card(b.unassigned,true)}</details>`:''}<details data-fleet-detail="battle-evidence" class="battle-evidence"><summary>Harci kapcsolatok és a számítás értelmezése</summary><p>A veszteség mindig az áldozat oldalán, killmailenként egyszer számít. A killdarabszám minden részt vevő támadó oldalnál megjelenhet, ezért ezeket nem szabad összeadni. A pilótaszám egyedi karaktereket jelent; a struktúrák nem pilóták. A logisztikások vagy a kil­lmaileken nem szereplő flottatagok hiányozhatnak.</p>${relations}</details></section>`;
}
async function setBattleSides(sessionId,changes){
  if(fleetSidesSaving)return;
  if(!fleetLeaveEdits())return;
  fleetSidesSaving=true;
  document.querySelectorAll('#fleet-battle select,#fleet-battle button').forEach(el=>el.disabled=true);
  try{error('');await api('/api/fleet/sides',{session_id:sessionId,...changes});if(fleetRequest)await fleetRequest.catch(()=>{});await loadFleet();}
  catch(e){error(e.message);}
  finally{fleetSidesSaving=false;if(view==='fleet')render();}
}
function bindBattleReport(){
  const report=document.querySelector('#fleet-battle');if(!report)return;
  const sessionId=fleetSession;
  if(fleetSidesSaving)report.querySelectorAll('select,button').forEach(el=>el.disabled=true);
  report.querySelector('#battle-side-count').onchange=e=>void setBattleSides(sessionId,{side_count:e.target.value==='auto'?null:Number(e.target.value)});
  report.querySelector('#battle-reset').onclick=()=>void setBattleSides(sessionId,{reset:true});
  report.querySelectorAll('[data-battle-move]').forEach(el=>el.onchange=e=>void setBattleSides(sessionId,{group:el.dataset.battleMove,side:Number(e.target.value)}));
  report.querySelectorAll('[data-battle-group]').forEach(el=>el.ondragstart=e=>{if(fleetSidesSaving){e.preventDefault();return;}e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('application/x-eve-battle-group',el.dataset.battleGroup);});
  report.querySelectorAll('[data-battle-side]').forEach(el=>{
    el.ondragover=e=>{if([...e.dataTransfer.types].includes('application/x-eve-battle-group')){e.preventDefault();e.dataTransfer.dropEffect='move';}};
    el.ondrop=e=>{const group=e.dataTransfer.getData('application/x-eve-battle-group');if(!report.querySelector(`[data-battle-move="${CSS.escape(group)}"]`))return;e.preventDefault();void setBattleSides(sessionId,{group,side:Number(el.dataset.battleSide)});};
  });
}
