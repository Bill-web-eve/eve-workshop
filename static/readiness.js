'use strict';
globalThis.EveReadiness=(()=>{
 const sources={stock:'Alapanyag készleten',wip:'Alapanyag folyamatban',missing:'Alapanyag hiányzik'};
 const places={local:'A blueprint helyén',transfer:'Áthelyezés szükséges',unknown:'Az állomás nem igazolható'};
 const t=s=>globalThis.EveI18n?.t(s)||s;
 function tone(r){return !r?'unknown':r.location_status==='transfer'?'transfer':r.status==='missing'?'missing':r.location_status==='unknown'?'unknown':r.status;}
 function label(r){return t(sources[r?.status]||'Alapanyagállapot nem ismert');}
 function locationLabel(r){return t(places[r?.location_status]||'Az állomás nem igazolható');}
 function title(r){return label(r)+' · '+locationLabel(r);}
 function markup(r){
  if(!r)return '<span class="badge">Alapanyagállapot nem ismert</span>';
  const detail=r.materials.map(m=>`<li><strong>${itemName(m.name)}</strong><div><span>Készletből:</span> ${fmt(m.stock)} · <span>Folyamatban:</span> ${fmt(m.wip)} · <span>Még szükséges:</span> ${fmt(m.missing)}</div>${m.allocations.filter(a=>a.location_id!=null).map(a=>`<div class="batch-note">${EveLocations.markup(a.location_id)} · ${fmt(a.quantity)} <span>${a.source==='stock'?'Készlet':a.source==='wip'?'Folyamatban lévő job':'Ütemezett job'}</span></div>`).join('')}</li>`).join('');
  const target=r.target_location_id!=null?EveLocations.markup(r.target_location_id):r.blueprint_locations?.length>1?'<span>Több blueprintállomás; a pontos helyet az ütemező rendeli hozzá.</span> '+r.blueprint_locations.map(id=>EveLocations.markup(id)).join(' · '):t('A blueprint helye nem ismert.');
  return `<div class="input-readiness" data-location-sort-skip><span class="badge input-${r.status}">${sources[r.status]}</span>${r.status==='missing'&&r.has_wip?'<span class="batch-note">Részben folyamatban</span>':''}<span class="badge input-place-${r.location_status}">${places[r.location_status]}</span><details><summary>Alapanyag-részletek</summary><div class="readiness-target"><span>Blueprint helye:</span> ${target}</div><ul>${detail}</ul></details></div>`;
 }
 function legend(){return '<div class="input-legend">'+['stock','wip','missing','transfer','unknown'].map(k=>`<span><i class="input-dot input-${k}" aria-hidden="true"></i>${k==='transfer'?places.transfer:k==='unknown'?places.unknown:sources[k]}</span>`).join('')+'</div>';}
 return {markup,label,locationLabel,title,tone,legend};
})();
