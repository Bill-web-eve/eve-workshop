'use strict';
// Shared, scoped place labels. Names update in place without resetting forms,
// table filters, page size or the selected character/production scope.
globalThis.EveLocations=(()=>{
 const cache=new Map(),busy=new Map();let timer=null,generation=0;
 const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
 const t=s=>globalThis.EveI18n?.t(s)||s;
 const key=(id,scope)=>String(scope||'personal')+':'+id;
 const statusText=status=>t(({access:'A hely neve nem érhető el · hozzáférés szükséges',disabled:'Corporation figyelése kikapcsolva',unknown:'Ismeretlen hely',unavailable:'A hely neve átmenetileg nem érhető el'})[status]||'Helynév betöltése…');
 const validName=(name,id)=>typeof name==='string'&&name.trim()&&name!==String(id);
 function markup(id,name=null,scope=undefined){
  if(!Number.isSafeInteger(Number(id))||Number(id)<=0)return '–';
  id=Number(id);if(scope===undefined)scope=typeof corporationId==='undefined'?null:corporationId;
  scope=Number.isSafeInteger(Number(scope))&&Number(scope)>0?Number(scope):null;
  const info=cache.get(key(id,scope));
  if(validName(name,id))cache.set(key(id,scope),{name,status:'resolved',until:Date.now()+900000});
  else name=info?.name;
  return `<span data-location-id="${id}" data-location-scope="${scope||'personal'}" ${name?'data-i18n-skip':''} title="${esc(t('Helyazonosító'))}: ${id}">${esc(name||statusText(info?.status))}</span>`;
 }
 function paint(node,value){
  const id=Number(node.dataset.locationId),name=value?.name,text=name||statusText(value?.status);
  let changed=false;
  if(node.textContent!==text){node.textContent=text;changed=true;}
  if(node.hasAttribute('data-i18n-skip')!==!!name)node.toggleAttribute('data-i18n-skip',!!name);
  const title=t('Helyazonosító')+': '+id;if(node.title!==title)node.title=title;
  const cell=node.closest('td');
  if(cell&&!node.closest('[data-location-sort-skip]')){
   const sort=name||text,filter=sort+' '+id;
   if(cell.dataset.sortValue!==sort||cell.dataset.filterValue!==filter){cell.dataset.sortValue=sort;cell.dataset.filterValue=filter;changed=true;}
  }
  return changed;
 }
 function nodes(){return [...document.querySelectorAll('[data-location-id]')];}
 function apply(){
  let changed=false;
  for(const node of nodes()){
   const value=cache.get(key(node.dataset.locationId,node.dataset.locationScope));
   if(value)changed=paint(node,value)||changed;
  }
  if(changed)globalThis.EveTables?.refreshAll();
 }
 function schedule(delay=0){if(timer===null)timer=setTimeout(()=>{timer=null;void load();},delay);}
 async function load(){
  if(typeof api!=='function')return;
  const groups=new Map(),now=Date.now(),revision=generation;apply();
  for(const node of nodes()){
   const id=Number(node.dataset.locationId),scope=node.dataset.locationScope||'personal',k=key(id,scope);
   if(!Number.isSafeInteger(id)||id<=0||busy.has(k)||(cache.get(k)?.until||0)>now)continue;
   if(!groups.has(scope))groups.set(scope,new Set());groups.get(scope).add(id);
  }
  await Promise.all([...groups].map(async([scope,values])=>{
   const ids=[...values];
   for(let offset=0;offset<ids.length;offset+=200){
    if(revision!==generation)return;
    const batch=ids.slice(offset,offset+200),ticket={};batch.forEach(id=>busy.set(key(id,scope),ticket));
    try{
     const data=await api('/api/locations?ids='+batch.join(',')+(scope==='personal'?'':'&corporation_id='+scope));
     if(revision!==generation)continue;
     for(const id of batch){
      const value=data.locations?.[id]||{status:'unknown'},old=cache.get(key(id,scope));
      cache.set(key(id,scope),{...value,name:validName(value.name,id)?value.name:old?.name,until:Date.now()+(value.status==='pending'?1500:900000)});
     }
    }catch{
     if(revision===generation)for(const id of batch){const old=cache.get(key(id,scope));cache.set(key(id,scope),{...old,status:'unavailable',until:Date.now()+900000});}
    }finally{batch.forEach(id=>{if(busy.get(key(id,scope))===ticket)busy.delete(key(id,scope));});if(revision===generation)apply();}
   }
  }));
  const pending=nodes().some(node=>cache.get(key(node.dataset.locationId,node.dataset.locationScope))?.status==='pending');
  if(pending&&revision===generation)schedule(2000);
 }
 new MutationObserver(records=>{
  if(records.some(r=>[...r.addedNodes].some(n=>n.nodeType===1&&(n.matches('[data-location-id]')||n.querySelector('[data-location-id]')))))schedule();
 }).observe(document.body,{childList:true,subtree:true});
 window.addEventListener('eve-language-change',apply);
 return {markup,refresh:()=>{generation++;cache.clear();busy.clear();schedule();},load};
})();
