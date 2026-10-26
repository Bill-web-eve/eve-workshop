'use strict';
let boostData=null,boostLoading=false,boostTimer=null,boostChannels=[],boostDraft=null,boostAction=false,boostRevision=0;
async function loadBoosts(){
 if(boostLoading)return;boostLoading=true;const revision=boostRevision;
 try{
  const data=await api('/api/boosts');if(revision!==boostRevision)return;boostData=data;
  if(!boostDraft)boostDraft={folder:boostData.folder,channel:boostData.channel};
  if(view==='boosts')renderBoosts($('#view-content'));
 }catch(e){if(view==='boosts')error(e.message);}
 finally{boostLoading=false;clearTimeout(boostTimer);if(view==='boosts')boostTimer=setTimeout(()=>void loadBoosts(),1500);}
}
function renderBoosts(content){
 setHead('FLOTTATÁMOGATÁS','Boost számláló','A kiválasztott csatornán bejelentett shield, skirmish és information boostok.');
 if(!boostData){content.innerHTML=empty('Boost-adatok betöltése…');void loadBoosts();return;}
 if(!boostLoading){clearTimeout(boostTimer);boostTimer=setTimeout(()=>void loadBoosts(),1500);}
 if(!$('#boost-view')){
  content.innerHTML=`<section id="boost-view"><form id="boost-form" class="panel boost-toolbar"><label>Chatlogmappa<div class="boost-folder"><input name="folder" type="text" required value="${esc(boostDraft.folder)}" placeholder="Documents/EVE/logs/Chatlogs"><button type="button" id="boost-folder" class="button compact" ${EveDesktop.active?'':'disabled'}>Mappa kiválasztása</button></div></label><label>Boost csatorna<select name="channel" required><option value="">Válassz Boost csatornát</option></select></label><div class="boost-actions"><button type="button" id="boost-discover" class="button compact">Csatornák keresése</button><button type="submit" class="button primary compact">Új számlálás indítása</button><button type="button" id="boost-stop" class="button compact">Számlálás leállítása</button><button type="button" id="boost-copy" class="button compact">Lista másolása</button></div></form><div id="boost-status" class="banner" role="status"></div><div id="boost-cards" class="boost-groups"></div><p class="footnote">Indításkor nulláról indulunk; a korábban naplózott üzenetek kimaradnak. Karakterenként az utolsó bejelentett boostkészlet számít, az ismétlések nem adódnak össze. A „missing” összesítéseket nem számoljuk. A számláló a bejelentéseket követi, a játékban ténylegesen futó boostot nem ellenőrzi.</p><details id="boost-provider-details" class="panel"><summary>Bejelentett karakterek</summary><div id="boost-providers" class="panel-body"></div></details></section>`;
  const form=$('#boost-form');
  form.oninput=()=>{boostDraft.folder=form.elements.folder.value;boostDraft.channel=form.elements.channel.value;};
  form.onchange=form.oninput;
  form.elements.folder.onchange=()=>{boostChannels=[];boostDraft.channel='';boostChannelOptions();};
  form.onsubmit=e=>{e.preventDefault();if(form.reportValidity())void boostCommand('start',{folder:form.elements.folder.value,channel:form.elements.channel.value});};
  $('#boost-stop').onclick=()=>void boostCommand('stop',{});
  $('#boost-copy').onclick=async()=>{try{await navigator.clipboard.writeText(boostData.copy_text);toast('Boostlista vágólapra másolva.');}catch(e){error('A Boostlista másolása nem sikerült.');}};
  $('#boost-discover').onclick=()=>void discoverBoostChannels();
  $('#boost-folder').onclick=async()=>{try{const selected=await EveDesktop.chooseIntelFolder();if(selected.path){form.elements.folder.value=selected.path;boostDraft.folder=selected.path;boostDraft.channel='';boostChannels=[];await discoverBoostChannels();}}catch(e){error(e.message);}};
  boostChannelOptions();
  if(boostDraft.folder&&!boostChannels.length)void discoverBoostChannels();
 }
 updateBoosts();
}
function boostChannelOptions(){
 const select=$('#boost-form')?.elements.channel;if(!select)return;
 const names=[...new Set([...boostChannels,...(boostDraft.channel?[boostDraft.channel]:[])])];
 select.innerHTML='<option value="">Válassz Boost csatornát</option>'+names.map(name=>`<option data-i18n-skip value="${esc(name)}">${esc(name)}</option>`).join('');
 select.value=boostDraft.channel||'';
}
async function discoverBoostChannels(){
 const form=$('#boost-form');if(!form||boostAction)return;
 const folder=form.elements.folder.value;$('#boost-discover').disabled=true;
 try{const data=await api('/api/boosts/channels?folder='+encodeURIComponent(folder));if(!$('#boost-form')||folder!==boostDraft.folder)return;boostChannels=data.channels;boostChannelOptions();if(!data.channels.length)error('Ebben a mappában nincs Boost nevű chatcsatorna. Nyisd meg a csatornát az EVE-ben, és kapcsold be a chatnaplózást.');}
 catch(e){error(e.message);}finally{if($('#boost-discover'))$('#boost-discover').disabled=boostData.running||boostAction;}
}
async function boostCommand(action,body){
 if(boostAction)return;boostAction=true;boostRevision++;updateBoosts();
 try{boostData=await api('/api/boosts/'+action,body);boostDraft={folder:boostData.folder,channel:boostData.channel};error('');}
 catch(e){error(e.message);}finally{boostAction=false;if(view==='boosts')updateBoosts();void loadBoosts();}
}
function updateBoosts(){
 if(!$('#boost-view')||!boostData)return;const data=boostData,form=$('#boost-form');
 form.elements.folder.disabled=data.running||boostAction;form.elements.channel.disabled=data.running||boostAction;
 form.querySelector('[type=submit]').disabled=data.running||boostAction;
 $('#boost-folder').disabled=data.running||boostAction||!EveDesktop.active;$('#boost-discover').disabled=data.running||boostAction;
 $('#boost-stop').disabled=!data.running||boostAction;
 const status=$('#boost-status');status.className='banner'+(data.error||data.file_errors?' warn':'');
 status.innerHTML=`<strong>${esc(data.running?'Boostfigyelés fut':'Boostfigyelés leállítva')}</strong>${data.channel?' · '+verbatim(data.channel):''} · <span>Bejelentett karakterek</span>: ${fmt(data.providers.length)}${data.started?' · <span>Indítás</span>: '+date(data.started):''}${data.checked?' · <span>Utolsó ellenőrzés:</span> '+date(data.checked):''}${data.error?'<div>'+esc(data.error)+'</div>':''}${data.file_errors?'<div>Legalább egy Boost-napló nem olvasható; ellenőrizd a fájlok hozzáférését.</div>':''}`;
 $('#boost-cards').innerHTML=['Shield','Skirmish','Information'].map(group=>`<section class="panel boost-group"><h2 data-i18n-skip>${group}</h2><div class="boost-items">${data.rows.filter(r=>r.group===group).map(r=>`<article class="boost-card ${r.count?'has-boost':''}"><div class="boost-icon"><img src="https://images.evetech.net/types/${r.id}/icon?size=64" width="64" height="64" alt="${esc(r.name)}" data-i18n-skip>${r.count?`<span class="boost-badge" aria-label="${esc(r.name+': '+r.count)}">${fmt(r.count)}</span>`:''}</div><div class="boost-name">${itemName(r.name)}<small>${r.count?verbatim(r.providers.join(' · ')):'0'}</small></div></article>`).join('')}</div></section>`).join('');
 $('#boost-providers').innerHTML=data.providers.length?table(['Karakter','Bejelentett boostok','Utolsó bejelentés'],data.providers.map(p=>`<tr><td>${verbatim(p.name)}</td><td>${p.charges.map(id=>itemName(data.rows.find(r=>r.id===id)?.name||String(id))).join(' · ')}</td><td>${date(p.at)}</td></tr>`),'boost-providers-table'):empty('Még nincs boostbejelentés','Indítsd el a számlálást, majd a kiválasztott csatornán jelentsétek a boostokat a játékbeli charge-nevekkel.');
}
