'use strict';
// Exact four-decimal unit prices and cent totals, without floating point sums.
const EveCosts=(()=>{
  function scaled(value,allowZero=false){
    const match=String(value??'').match(/^(\d+)(?:\.(\d{1,4}))?$/);
    if(!match)return null;
    const amount=BigInt(match[1])*10000n+BigInt((match[2]||'').padEnd(4,'0'));
    return amount>0n||allowZero?amount:null;
  }
  function unit(quote,mode){
    if(!quote)return null;
    const buy=scaled(quote.buy),sell=scaled(quote.sell);
    return mode==='buy'?buy:mode==='sell'?sell:buy!==null&&sell!==null?(buy+sell)/2n:null;
  }
  function value(rows,quotes,mode){
    let cents=0n,missing=0,stale=0;
    const values=rows.map(row=>{
      const quantity=row.quantity,quote=quotes[String(row.id)];
      const manual=row.manual_price!==undefined&&row.manual_price!==null;
      const price=row.unit==='run'?null:manual?scaled(row.manual_price,true):unit(quote,mode);
      const valid=Number.isSafeInteger(quantity)&&quantity>=0;
      const line=quantity===0?0n:price===null||!valid?null:(price*BigInt(quantity)+50n)/100n;
      if(line===null)missing++;else cents+=line;
      if(!manual&&quote?.stale&&quantity>0)stale++;
      return {...row,price,cents:line,stale:!manual&&!!quote?.stale};
    });
    return {rows:values,cents,missing,stale};
  }
  function materials(plan){
    // Each raw input or consumed existing intermediate is valued once. Do not
    // add manufactured intermediates again on top of their production inputs.
    return (plan?.rows||[]).filter(r=>r.id!==plan.product_id).map(r=>({id:r.id,name:r.name,
      quantity:r.runs?(r.used_stock||0)+(r.used_wip||0):r.required,unit:'db'})).filter(r=>r.quantity>0);
  }
  function format(cents){
    if(cents===null||cents===undefined)return '–';
    const s=cents.toString().padStart(3,'0'),whole=s.slice(0,-2).replace(/\B(?=(\d{3})+(?!\d))/g,' ');
    return whole+','+s.slice(-2)+' ISK';
  }
  function formatUnit(price){
    if(price===null||price===undefined)return '–';
    const s=price.toString().padStart(5,'0');
    return s.slice(0,-4).replace(/\B(?=(\d{3})+(?!\d))/g,' ')+','+s.slice(-4).replace(/0{1,2}$/,'')+' ISK';
  }
  return {scaled,unit,value,materials,format,formatUnit};
})();
globalThis.EveCosts=EveCosts;
if(typeof module!=='undefined'&&module.exports)module.exports=EveCosts;
