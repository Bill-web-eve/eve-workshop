'use strict';
let financeHistoryKey='',financeHistoryData=null,financeHistoryError='',financeHistoryTimer=null,financeHistoryRequest=0,financeHistoryBusy=false;
function financeHistoryMarkup(){
 return '<section class="finance-history" data-finance-history aria-label="Piaci forgalom"><div class="finance-history-head"><strong>Piaci forgalom</strong><button type="button" class="text-button" data-history-refresh>↻ Frissítés</button></div><div data-history-content role="status">Piaci forgalom betöltése…</div><small>A teljes régió forgalma, buy és sell együtt. Az ESI nem közöl külön sell orderes vagy állomásonkénti előzményt. A napok EVE-idő (UTC) szerint értendők.</small></section>';
}
function renderFinanceHistory(){
 const target=$('[data-finance-history]');if(!target)return;
 const data=financeHistoryData,content=target.querySelector('[data-history-content]');
 target.setAttribute('aria-busy',String(financeHistoryBusy||!!data?.running));
 const button=target.querySelector('[data-history-refresh]');button.disabled=financeHistoryBusy||!!data?.running;button.onclick=()=>syncFinanceHistory(true);
 const date=s=>EveI18n.date(s+'T00:00:00Z',{month:'short',day:'numeric',timeZone:'UTC'});
 let html='';
 if(data?.checked){
  const region=financePrefs?.sale?.startsWith('local:')?esc(EveI18n.t('{0} régiója').replace('{0}',tradeData?.settings.location?.system_name||localMarketName())):'Jita régiója · The Forge';
  const max=Math.max(1,...data.daily.map(r=>r.volume||0));
  html=`<small class="history-region"><span>${region}</span> · <span>Utolsó 7 elérhető nap</span></small><div class="history-days">${data.daily.map(r=>`<div class="history-day"><span>${esc(date(r.date))}</span><svg class="history-bar" viewBox="0 0 28 25" width="28" height="25" aria-hidden="true"><rect x="0" y="${25-(r.volume||0)/max*25}" width="28" height="${(r.volume||0)/max*25}"></rect></svg><strong title="${esc(r.date)} · UTC">${r.volume===null?'–':fmt(r.volume)}</strong></div>`).join('')}</div><div class="finance-line history-average"><span>Heti átlag · előző 30 nap</span><strong>${data.weekly_average===null?'–':Number(data.weekly_average).toLocaleString(EveI18n.locale,{maximumFractionDigits:1})} <span>db / hét</span></strong></div><small>${esc(date(data.month_start))} – ${esc(date(data.month_end))} · <span>30 nap összforgalma ÷ 30 × 7</span></small>`;
  if(!data.latest_date)html+='<p>Nincs közzétett piaci forgalmi adat.</p>';
  if(data.stale)html+='<p class="warning-text">Korábbi piaci forgalmi adatot mutatunk.</p>';
 }
 if(financeHistoryBusy||data?.running)html+='<p class="history-progress">Piaci forgalom betöltése…</p>';
 const error=financeHistoryError||data?.error;if(error)html+=`<p class="warning-text">${esc(EveI18n.t(error))}</p>`;
 if(!html)html='<p>Nincs közzétett piaci forgalmi adat.</p>';
 content.innerHTML=html;
 EveI18n.translate(target);
}
function syncFinanceHistory(manual=false){
 if(typeof view==='undefined'||view!=='queue'||!financeContext||!financePrefs||!$('[data-finance-history]'))return;
 const source=financePrefs.sale.split(':')[0],location=tradeData?.settings.location;
 const key=JSON.stringify([financeContext.plan.product_id,source,source==='local'?location?.id:null,source==='local'?location?.region_id:null]);
 if(key===financeHistoryKey&&!manual){renderFinanceHistory();if(!financeHistoryBusy&&!financeHistoryTimer)void requestFinanceHistory(key,source,financeContext.plan.product_id);return;}
 if(key!==financeHistoryKey)financeHistoryData=null;
 financeHistoryKey=key;financeHistoryError='';clearTimeout(financeHistoryTimer);
 void requestFinanceHistory(key,source,financeContext.plan.product_id,manual);
}
async function requestFinanceHistory(key,source,tid,manual=false){
 if(view!=='queue'||key!==financeHistoryKey||!$('[data-finance-history]'))return;
 const request=++financeHistoryRequest;financeHistoryBusy=true;renderFinanceHistory();
 try{
  const data=manual?await api('/api/market/history/refresh',{type_id:tid,source}):await api('/api/market/history?type_id='+tid+'&source='+source);
  if(key!==financeHistoryKey||request!==financeHistoryRequest)return;
  financeHistoryData=data;financeHistoryError='';
 }catch(e){if(key===financeHistoryKey&&request===financeHistoryRequest)financeHistoryError=e.message;}
 finally{
  if(key===financeHistoryKey&&request===financeHistoryRequest){
   financeHistoryBusy=false;renderFinanceHistory();clearTimeout(financeHistoryTimer);
   financeHistoryTimer=setTimeout(()=>{financeHistoryTimer=null;void requestFinanceHistory(key,source,tid);},financeHistoryData?.running?1000:15*60*1000);
  }
 }
}
