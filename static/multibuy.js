'use strict';
const EveMultibuy=(()=>{
  function text(rows){
    const totals=new Map();
    for(const row of rows){
      if(row.is_blueprint||row.unit==='run'||['BPC-run','BPO','BPC','Reakcióformula'].includes(row.category))continue;
      if(!Number.isSafeInteger(row.buy)||row.buy<=0)continue;
      const name=String(row.name).replace(/[\r\n\t]+/g,' ').trim();
      const quantity=(totals.get(name)||0)+row.buy;
      if(!Number.isSafeInteger(quantity))throw Error('A másolandó mennyiség túl nagy.');
      totals.set(name,quantity);
    }
    return [...totals].map(([name,quantity])=>`${name}\t${quantity}`).join('\r\n');
  }
  return {text};
})();
if(typeof module!=='undefined')module.exports=EveMultibuy;
