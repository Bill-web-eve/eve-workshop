'use strict';
// Shared request tracker and lightweight background-work monitor. No fake ETA.
globalThis.EveActivity=(()=>{
  const active=new Map(),completed=new Map(),seen=new Set();let serial=0,pollTimer=null,polling=false,expanded=true,showTimer=null,hideTimer=null,visible=false,monitorFailures=0;
  const t=(source,...values)=>{let value=globalThis.EveI18n?.t(source)||source;values.forEach((v,i)=>value=value.replaceAll('{'+i+'}',String(v)));return value;};
  const part=(text,...args)=>({text,args});
  const detailText=value=>Array.isArray(value)?value.map(p=>p.raw?p.text:t(p.text,...(p.args||[]))).join(' · '):t(value);
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels={
    '/api/contracts':'Szerződések betöltése','/api/contracts/details':'Szerződés részleteinek betöltése','/api/contracts/sync':'Szerződések frissítése','/api/trade':'Marketadatok lekérése','/api/trade/discover':'Helyi market keresése','/api/trade/settings':'Marketbeállítások mentése','/api/trade/plan':'Terv költségbeállításainak mentése','/api/trade/seller':'Eladó díjainak ellenőrzése','/api/trade/seller/refresh':'Eladó skillek és standingek frissítése',
    '/api/fleet/sides':'Harci oldalak mentése','/api/fleet':'Flottaadatok betöltése…','/api/fleet/refresh':'Killmailek frissítése','/api/assets':'Teljes EVE-készlet betöltése',
    '/api/mining':'Bányászati naplók összesítése','/api/mining/sync':'Bányászati naplók frissítése',
    '/api/intel/characters':'Pilótaazonosítók ellenőrzése…','/api/intel':'Inteladatok betöltése','/api/intel/channels':'Intelcsatornák keresése','/api/intel/locations':'ESI-helyzetek frissítése',
    '/api/state':'Műhelyadatok betöltése','/api/plan':'Gyártási terv számítása','/api/schedule':'Gyártás ütemezése','/api/search':'Termékkeresés',
    '/api/skills':'Skilladatok összesítése','/api/pi':'PI-adatok összesítése','/api/moons':'Holdadatok összesítése','/api/moons/systems':'Rendszerkeresés',
    '/api/prices':'Jita-árak ellenőrzése','/api/prices/refresh':'Jita-árak frissítése','/api/industry':'Ipari költségadatok ellenőrzése','/api/industry/refresh':'Ipari költségadatok frissítése','/api/industry/estimate':'Gyártási költség számítása','/api/industry/system':'Rendszerindex ellenőrzése',
    '/api/implants':'Implantadatok ellenőrzése…','/api/implants/preferences':'Implantfigyelés mentése','/api/notifications':'Értesítések összesítése','/api/notifications/claim':'Értesítések előkészítése','/api/notifications/sent':'Értesítések visszaigazolása',
    '/api/corporations':'Corp-adatok összesítése','/api/accounts':'Accountadatok kezelése','/api/plans/shopping':'Összes terv anyaghiányának számítása','/api/documentation':'Kézikönyv betöltése','/api/export':'Fájl előkészítése',
    '/api/auth/start':'EVE-belépés előkészítése','/api/desktop/auth':'EVE-belépés ellenőrzése','/api/shutdown':'Alkalmazás leállítása'
  };
  const taskLabels={contracts:'Szerződések frissítése',mining:'Bányászati naplók frissítése',sync:'EVE-adatok frissítése',notifications:'EVE-adatok ellenőrzése',skills:'Skilladatok frissítése',pi:'PI-adatok frissítése',corporations:'Corp-adatok frissítése',moons:'Holdrendszerek ellenőrzése',extractions:'Holdadatok frissítése',sde:'Receptadatbázis frissítése'};
  const starts=new Set(['/api/contracts/sync','/api/mining/sync','/api/sync','/api/notifications/sync','/api/skills/sync','/api/pi/sync','/api/corporations/sync','/api/moons/sync','/api/moons/extractions/sync','/api/sde/update','/api/prices/refresh','/api/industry/refresh']);
  const base=path=>String(path).split('?')[0];
  function label(path){const key=base(path);if(labels[key])return labels[key];if(starts.has(key))return 'Adatfrissítés indítása';if(/\/(save|settings|preferences|parameters|inventory|reservation|remove)$/.test(key))return 'Módosítások mentése';return 'Adatok lekérése';}
  function elements(){
    let panel=document.getElementById('activity-panel');if(panel)return panel;
    panel=document.createElement('aside');panel.id='activity-panel';panel.className='activity-panel';panel.hidden=true;panel.setAttribute('aria-label',t('Folyamatok állapota'));
    panel.innerHTML='<div class="activity-heading"><strong id="activity-heading" role="status" aria-live="polite"></strong><button id="activity-collapse" type="button" class="text-button"></button></div><div id="activity-body"></div>';
    document.body.append(panel);
    const toggle=document.createElement('button');toggle.id='activity-toggle';toggle.type='button';toggle.className='button compact activity-toggle';toggle.hidden=true;toggle.setAttribute('aria-controls','activity-panel');
    (document.querySelector('.topbar>div')||document.body).prepend(toggle);toggle.onclick=()=>{expanded=!expanded;visible=true;render();};
    panel.querySelector('#activity-collapse').onclick=()=>{expanded=false;render();};return panel;
  }
  function reveal(){clearTimeout(hideTimer);if(!visible&&!showTimer)showTimer=setTimeout(()=>{showTimer=null;visible=true;render();},120);render();}
  function start(key,title,detail='Válaszra várunk'){
    if(!visible&&!active.size)completed.clear();
    const previous=active.get(key);const value={key,title,detail,state:'running',started:previous?.started||Date.now(),...previous};
    active.set(key,value);completed.delete(key);reveal();return value;
  }
  function finish(key,state='success',detail='A művelet elkészült.'){
    const value=active.get(key);if(!value)return;
    if(state!=='success')visible=true;
    active.delete(key);completed.set(key,{...value,state,detail,finished:Date.now(),progress:null});
    while(completed.size>6){const expendable=[...completed.keys()].find(key=>completed.get(key).state==='success');completed.delete(expendable||completed.keys().next().value);}
    render();
    if(!active.size){clearTimeout(showTimer);showTimer=null;if(visible){clearTimeout(hideTimer);hideTimer=setTimeout(()=>{visible=false;render();},[...completed.values()].some(r=>r.state!=='success')?15000:5000);}}
  }
  function background(key,title,running,detail,progress=null,outcome='success'){
    if(running){const row=start(key,title);Object.assign(row,{title,detail,progress});render();}
    else if(active.has(key))finish(key,outcome,detail);
  }
  function task(data){
    if(!data||!data.kind)return;
    const key='task:'+String(data.id||data.started||data.kind),p=data.progress||{};
    if(seen.has(key)){if(active.has('pending:task'))finish('pending:task','success','Nincs folyamatban adatfrissítés.');return;}
    if(!data.running&&!active.has(key)&&!active.has('pending:task'))return;
    const pending=active.has('pending:task');active.delete('pending:task');
    for(const old of [...active.keys()])if(old.startsWith('task:')&&old!==key)active.delete(old);
    const bits=[];
    if(p.stage)bits.push(part(p.stage));
    if(p.stages)bits.push(part('{0} / {1} szakasz',Math.min((p.stage_index||0)+1,p.stages),p.stages));
    if(p.subject)bits.push({text:p.subject,raw:true});
    if(p.total!=null)bits.push(part('Ellenőrizve: {0} / {1}',p.completed||0,p.total));
    if(p.resource)bits.push(part(p.resource));
    if(p.page)bits.push(p.pages?part('{0} / {1} oldal',p.page,p.pages):part('{0}. oldal',p.page));
    if(p.mode==='cache')bits.push(part('Érvényes EVE-gyorsítótár'));
    else if(p.mode==='request')bits.push(part('Várakozás az EVE válaszára'));
    else if(p.mode==='received')bits.push(part('Válasz feldolgozása'));
    let bar=p.total>0?{done:p.completed||0,total:p.total}:null;
    if(p.bytes_total>0){bar={done:p.bytes_done||0,total:p.bytes_total};bits.push(part('{0} / {1} MB',((p.bytes_done||0)/1048576).toFixed(1),(p.bytes_total/1048576).toFixed(1)));}
    const outcome=data.outcome||(data.results?.some(r=>!r.ok)?'warning':'success');
    if(!data.running&&pending&&!active.has(key))start(key,taskLabels[data.kind]||'Adatfrissítés');
    background(key,taskLabels[data.kind]||'Adatfrissítés',data.running,data.running?bits:data.message||'A művelet elkészült.',bar,outcome);
    if(data.running){const row=active.get(key);if(data.started)row.started=data.started*1000;pollSoon();}
    else{seen.add(key);}
  }
  function observe(path,data){
    if(!data||typeof data!=='object')return;
    if(base(path)==='/api/fleet')fleet(data.status,data.location_status);
    if(data.task)task(data.task);
    if(data.intel)intel(data.intel);
    if(base(path).startsWith('/api/trade')&&data.status)trade(data.status);
    const key=base(path);
    if(key.startsWith('/api/prices'))market(data);
    if(key==='/api/industry'||key==='/api/industry/refresh')industry(data);
    if(starts.has(key)&&!key.startsWith('/api/prices')&&!key.startsWith('/api/industry')){if(![...active.keys()].some(k=>k.startsWith('task:')))start('pending:task','Adatfrissítés','A folyamat állapotának lekérése');pollSoon(0);}
  }
  function market(data){
    const key=data.source_key&&data.source_key!=='jita'?'market-local':'market';
    const detail=[part('Árak ellenőrizve: {0} / {1}',data.done||0,data.total||0)];
    if(data.current_name)detail.push({text:data.current_name,raw:true});
    if(data.page)detail.push(data.pages?part('{0} / {1} oldal',data.page,data.pages):part('{0}. oldal',data.page));
    const errors=typeof data.errors==='number'?data.errors:Object.keys(data.errors||{}).length;
    background(key,key==='market'?'Jita-árak frissítése':'Piaci árak frissítése',data.running,errors&&!data.running?[part('{0} ár nem frissült; a korábbi adatok megmaradtak.',errors)]:detail,data.total?{done:data.done||0,total:data.total}:null,errors?'warning':'success');
    if(data.running)pollSoon();
  }
  function trade(data){background('trade','Marketadatok lekérése',!!data.running,[part(data.phase||'Marketadatok lekérése'),...(data.error?[part(data.error)]:[])],{done:data.done||0,total:data.total||1},data.error?'warning':'success');if(data.running)pollSoon();}
  function industry(data){
    const names={systems:'Rendszerindexek',prices:'ESI alapárak'};
    const detail=data.running?[part(names[data.current]||'Ipari költségadatok'),part('Ellenőrizve: {0} / {1}',data.done||0,2)]:Object.keys(data.errors||{}).length?'Néhány ipari költségadat nem frissült.':'Az ipari költségadatok ellenőrizve.';
    background('industry','Ipari költségadatok frissítése',data.running,detail,{done:data.done||0,total:2},Object.keys(data.errors||{}).length?'warning':'success');if(data.running)pollSoon();
  }
  function intel(data){
    background('intel-names','Pilótaazonosítók ellenőrzése…',!!data.resolving_characters,[part('Ellenőrizve: {0} / {1}',data.names_done||0,data.names_total||0)],data.names_total?{done:data.names_done||0,total:data.names_total}:null,data.names_error?'warning':'success');if(data.resolving_characters)pollSoon();
    background('intel','ESI-helyzetek frissítése',!!data.location_refreshing,data.location_character?[{text:data.location_character,raw:true}]:[part('Helyzetadatok ellenőrzése')]);if(data.location_refreshing)pollSoon();
  }
  function fleet(data={},location={}){
    const bits=[part('Ellenőrizve: {0} / {1}',data.completed||0,data.total||0)];
    if(data.subject)bits.push({text:data.subject,raw:true});
    if(data.page)bits.push(part('{0}. oldal',data.page));
    if(data.resource)bits.push(part(data.resource));
    const issue=data.error||data.results?.some(r=>!r.ok||r.partial);
    background('fleet','Killmailek frissítése',!!data.running,data.error||bits,data.total?{done:data.completed||0,total:data.total}:null,issue?'warning':'success');
    background('fleet-location','ESI-helyzetek frissítése',!!location.running,location.character?[{text:location.character,raw:true}]:[part('Helyzetadatok ellenőrzése')]);
    if(data.running||location.running)pollSoon();
  }
  function monitoring(){return [...active.keys()].some(key=>key==='fleet'||key==='fleet-location'||key==='intel-names'||key==='intel'||key==='market'||key==='market-local'||key==='trade'||key==='industry'||key==='pending:task'||key.startsWith('task:'));}
  function pollSoon(delay=700){if(!pollTimer&&!polling)pollTimer=setTimeout(()=>{pollTimer=null;void poll();},delay);}
  async function poll(){
    if(polling)return;polling=true;
    try{
      const response=await fetch('/api/activity');if(!response.ok)throw Error('status');const data=await response.json();monitorFailures=0;
      if(data.task?.kind)task(data.task);else if(active.has('pending:task'))finish('pending:task','success','Nincs folyamatban adatfrissítés.');
      fleet(data.fleet?.task,data.fleet?.location);market(data.market||{});if(data.local_market?.source_key)market(data.local_market);trade(data.trade||{});industry(data.industry||{});intel(data.intel||{});finish('monitor','success','Az állapotjelzés helyreállt.');
    }catch{
      monitorFailures++;
      const row=start('monitor','Az állapot most nem ellenőrizhető.','Újrapróbáljuk az állapot lekérését; a folyamat befejezése még nem igazolt.');row.state='warning';render();
    }finally{polling=false;if(monitoring()||monitorFailures)pollSoon(monitorFailures?5000:700);}
  }
  async function run(path,operation){
    const key='request:'+(++serial),route=base(path);
    const quiet=(route==='/api/fleet'&&String(path).includes('background=1'))||route==='/api/implants/claim'||route==='/api/intel/alerts'||route==='/api/intel/claim'||(route==='/api/intel'&&String(path).includes('background=1'))||route==='/api/activity'||(route==='/api/state'&&monitoring())||(route==='/api/prices'&&active.has('market'));
    if(!quiet)start(key,label(path));
    try{const result=await operation();observe(path,result);if(!quiet)finish(key);return result;}
    catch(error){if(!quiet)finish(key,'error',error.message||'A kérés nem sikerült.');throw error;}
  }
  function render(){
    const panel=elements(),toggle=document.getElementById('activity-toggle');
    const rows=[...active.values()],history=[...completed.values()].reverse().sort((a,b)=>(a.state==='success')-(b.state==='success'));
    const issue=rows.some(r=>r.state!=='running')||history.some(r=>r.state!=='success');
    const title=rows.length?t('{0} folyamatban lévő művelet',rows.length):issue?t('Befejezve · ellenőrzést igényel'):t('Minden művelet elkészült');
    toggle.hidden=!visible;toggle.textContent=title;toggle.dataset.state=issue?'warning':rows.length?'running':'success';toggle.setAttribute('aria-expanded',String(visible&&expanded));
    panel.hidden=!visible||!expanded;panel.dataset.state=toggle.dataset.state;panel.setAttribute('aria-busy',String(rows.length>0));
    document.getElementById('activity-heading').textContent=title;document.getElementById('activity-collapse').textContent=t('Kis méret');
    const body=document.getElementById('activity-body');
    const html=[...rows,...history.slice(0,rows.length?2:4)].map(row=>{
      const bar=row.state==='running',p=row.progress,known=p&&Number.isFinite(p.total)&&p.total>0;
      return `<section class="activity-row" data-state="${row.state}"><div class="activity-row-title"><span class="activity-state" aria-hidden="true">${row.state==='running'?'◌':row.state==='success'?'✓':'!'}</span><strong>${escape(t(row.title))}</strong><small class="activity-result">${escape(t({running:'Folyamatban',success:'Elkészült',warning:'Figyelmeztetés',error:'Sikertelen'}[row.state]))}</small></div><p data-i18n-skip>${escape(detailText(row.detail))}</p>${bar?`<progress aria-label="${escape(t(row.title))}" ${known?`max="${p.total}" value="${Math.max(0,Math.min(p.done,p.total))}"`:''}></progress><small class="activity-elapsed" data-started="${row.started}" aria-live="off"></small>`:''}</section>`;
    }).join('');
    if(body.dataset.rendered!==html){body.innerHTML=html;body.dataset.rendered=html;}
    elapsed();
  }
  function elapsed(){for(const el of document.querySelectorAll('.activity-elapsed'))el.textContent=t('Eltelt idő: {0} mp',Math.max(0,Math.floor((Date.now()-Number(el.dataset.started))/1000)));}
  window.addEventListener('eve-language-change',render);setInterval(elapsed,1000);
  return {run,observe,task,poll,render};
})();
