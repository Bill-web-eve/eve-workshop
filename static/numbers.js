'use strict';
const EveNumbers=(()=>{
  const parse=value=>{const digits=String(value??'').replace(/\s/g,'');return /^\d+$/.test(digits)?Number(digits):NaN;};
  const format=value=>String(value).replace(/\B(?=(\d{3})+(?!\d))/g,' ');
  function validate(input){
    const value=parse(input.value),minimum=Number(input.dataset.numberMin||0),maximum=Number(input.dataset.numberMax||1000000000000);
    const message=input.value===''&&!input.required?'':!Number.isSafeInteger(value)||value<minimum||value>maximum?`Egész számot adj meg ${format(minimum)} és ${format(maximum)} között.`:'';
    input.setCustomValidity(typeof EveI18n==='undefined'?message:EveI18n.t(message));
  }
  function enhance(input){
    if(input.dataset.numberReady)return;input.dataset.numberReady='1';
    const update=()=>{
      const before=input.value,position=input.selectionStart??before.length;
      const leftDigits=before.slice(0,position).replace(/\s/g,'').length;
      if(/^\d[\d\s]*$/.test(before)){
        input.value=format(before.replace(/\s/g,''));
        let cursor=0,count=0;while(cursor<input.value.length&&count<leftDigits){if(/\d/.test(input.value[cursor]))count++;cursor++;}
        input.setSelectionRange(cursor,cursor);
      }
      validate(input);
    };
    input.addEventListener('input',update);input.addEventListener('blur',update);update();
  }
  function set(input,value){input.value=value==null?'':format(value);validate(input);}
  if(typeof document!=='undefined'){
    const scan=node=>{if(node.nodeType!==1)return;if(node.matches('[data-grouped-number]'))enhance(node);node.querySelectorAll('[data-grouped-number]').forEach(enhance);};
    new MutationObserver(records=>{for(const r of records)for(const node of r.addedNodes)scan(node);}).observe(document.body,{subtree:true,childList:true});scan(document.body);
  }
  if(typeof window!=='undefined')window.addEventListener('eve-language-change',()=>document.querySelectorAll('[data-grouped-number]').forEach(validate));
  return {parse,format,enhance,validate,set};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=EveNumbers;
