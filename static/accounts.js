'use strict';
let accountData=null,accountRequest=null,accountDraft=null;
const accountDateInput=value=>value?new Date(value*1000-new Date(value*1000).getTimezoneOffset()*60000).toISOString().slice(0,16):'';
async function refreshAccounts(){
  if(accountRequest)return accountRequest;
  accountRequest=api('/api/accounts');
  try{accountData=await accountRequest;accountDraft=JSON.parse(JSON.stringify(accountData));if(view==='settings'&&settingsTab==='accounts'&&!dirty.accounts)render();}
  catch(e){error(e.message);}finally{accountRequest=null;}
}
function collectAccountForm(){
  const form=$('#account-form');if(!form)return accountDraft;
  const accounts=accountDraft.accounts.map(account=>{
    const value=key=>[...form.querySelectorAll('[data-account]')].find(input=>input.dataset.account===account.id&&input.dataset.accountKey===key).value;
    const date=key=>value(key)?new Date(value(key)).getTime()/1000:null;
    return {id:account.id,name:value('name'),omega_status:value('omega_status'),omega_expires:date('omega_expires'),mct1_expires:date('mct1_expires'),mct2_expires:date('mct2_expires')};
  });
  const characters=Object.fromEntries(state.characters.map(char=>[String(char.id),{account_id:form.querySelector(`[data-account-character="${char.id}"][data-character-key=account_id]`).value||null,training_mode:form.querySelector(`[data-account-character="${char.id}"][data-character-key=training_mode]`).value}]));
  return {accounts,characters};
}
function renderAccounts(target){
  if(!accountData){target.innerHTML=empty('Accountadatok betöltése');void refreshAccounts();return;}
  accountDraft=accountDraft||JSON.parse(JSON.stringify(accountData));
  const input=(a,key,type='text')=>`<input data-account="${esc(a.id)}" data-account-key="${key}" type="${type}" ${type==='text'?'maxlength="100" required':''} value="${esc(type==='datetime-local'?accountDateInput(a[key]):a[key])}">`;
  target.innerHTML=`<div class="banner">Az accountok és az Omega/MCT lejáratok kézi adatok. Az ESI nem ad accountazonosítót vagy előfizetési dátumot. Ne adj meg jelszót; egy saját accountnév elegendő. A dátumok helyi időben adhatók meg.</div><form id="account-form">`+
    panel('Accountok és lejáratok','Figyelmeztetés: lejárt vagy 5 napon belül lejár',accountDraft.accounts.length?table(['Account','Omega állapot','Omega lejárata','MCT 1 lejárata','MCT 2 lejárata','Művelet'],accountDraft.accounts.map(a=>`<tr><td>${input(a,'name')}</td><td><select data-account="${esc(a.id)}" data-account-key="omega_status">${Object.entries({unknown:'Ismeretlen',omega:'Omega',alpha:'Alpha'}).map(([key,label])=>`<option value="${key}" ${a.omega_status===key?'selected':''}>${esc(label)}</option>`).join('')}</select></td><td>${input(a,'omega_expires','datetime-local')}</td><td>${input(a,'mct1_expires','datetime-local')}</td><td>${input(a,'mct2_expires','datetime-local')}</td><td><button type="button" class="text-button" data-remove-account="${esc(a.id)}">Törlés</button></td></tr>`),'account-expiry'):empty('Még nincs felvitt account'))+
    `<div class="section-actions"><button type="button" class="button compact" id="add-account">Account hozzáadása</button></div>`+
    panel('Karakterek accountja és tanulási helye','Egy account: legfeljebb 3 karakter',table(['Karakter','Account','Tanulási hely'],state.characters.map(c=>{
      const pref=accountDraft.characters[String(c.id)]||{};
      return `<tr><td>${verbatim(c.name)}</td><td><select data-account-character="${c.id}" data-character-key="account_id"><option value="">Nincs hozzárendelve</option>${accountDraft.accounts.map(a=>`<option data-i18n-skip value="${esc(a.id)}" ${pref.account_id===a.id?'selected':''}>${esc(a.name)}</option>`).join('')}</select></td><td><select data-account-character="${c.id}" data-character-key="training_mode">${Object.entries({auto:'Automatikus',primary:'Alap tanulási hely',mct1:'MCT 1',mct2:'MCT 2',disabled:'Kizárva a tanulásfigyelésből'}).map(([key,label])=>`<option value="${key}" ${(pref.training_mode||'auto')===key?'selected':''}>${esc(label)}</option>`).join('')}</select></td></tr>`;
    }),'account-characters'))+
    `<p class="footnote">Üres dátum: ismeretlen lejárat. Automatikus módban a többi frissen tanuló karakter és a megadott MCT-helyek alapján figyelünk. Konkrét MCT-hely lejárata vagy kézi kizárás esetén nincs téves „nem tanul” riasztás. Alpha állapot önmagában nem tiltja a tanulást; az 5 millió SP-s határt is figyelembe vesszük.</p><button class="button primary" type="submit">Accountbeállítások mentése</button></form>`;
  const form=$('#account-form');form.oninput=()=>dirty.accounts=true;form.onchange=()=>dirty.accounts=true;
  $('#add-account').onclick=()=>{accountDraft=collectAccountForm();accountDraft.accounts.push({id:globalThis.crypto?.randomUUID?.()||'account-'+Date.now()+'-'+Math.random().toString(36).slice(2),name:EveI18n.t('Új account'),omega_status:'unknown',omega_expires:null,mct1_expires:null,mct2_expires:null});dirty.accounts=true;renderAccounts(target);};
  $$('[data-remove-account]').forEach(button=>button.onclick=()=>{accountDraft=collectAccountForm();accountDraft.accounts=accountDraft.accounts.filter(a=>a.id!==button.dataset.removeAccount);for(const pref of Object.values(accountDraft.characters))if(pref.account_id===button.dataset.removeAccount){pref.account_id=null;pref.training_mode='auto';}dirty.accounts=true;renderAccounts(target);});
  form.onsubmit=async event=>{
    event.preventDefault();try{await api('/api/accounts',collectAccountForm());delete dirty.accounts;accountDraft=null;accountData=null;skillData=null;await refreshAccounts();await refreshSkills();toast('Accountbeállítások mentve.');}catch(e){error(e.message);}
  };
}
function trainingAccountSummary(data){
  return `<div class="section-actions"><button class="button compact" data-open-settings="accounts">Omega és MCT beállításai</button><span>${fmt(data.summary.excluded||0)} <span>karakter tanulásfigyelése kizárva</span></span></div>`+
    (data.accounts?.accounts?.length?`<details class="panel"><summary>Accountok összes lejárata</summary>${table(['Account','Omega állapot','Omega lejárata','MCT 1 lejárata','MCT 2 lejárata'],data.accounts.accounts.map(a=>`<tr><td>${verbatim(a.name)}</td><td>${a.omega_status==='unknown'?'Ismeretlen':a.omega_status==='omega'?'Omega':'Alpha'}</td><td>${a.omega_expires?date(a.omega_expires):'–'}</td><td>${a.mct1_expires?date(a.mct1_expires):'–'}</td><td>${a.mct2_expires?date(a.mct2_expires):'–'}</td></tr>`),'all-training-expiries')}</details>`:'')+
    (data.accounts?.expiring?.length?panel('Omega és MCT lejáratok','Kézzel megadott adatok',table(['Account','Hozzáférés','Lejárat','Állapot'],data.accounts.expiring.map(a=>`<tr><td>${verbatim(a.account_name)}</td><td data-i18n-skip>${esc(a.kind)}</td><td>${date(a.expires)}</td><td><span class="badge warn">${a.expired?'Lejárt':'5 napon belül lejár'}</span></td></tr>`),'training-expiry')):'');
}
