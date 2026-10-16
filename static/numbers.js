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
  const moneyParse=value=>{const raw=String(value??'').replace(/\s/g,'').replace(',','.');return /^\d+(?:\.\d{0,4})?$/.test(raw)?raw.replace(/\.$/,''):null;};
  const moneyFormat=value=>{const raw=String(value??'').replace(/\s/g,'').replace('.',',');const [whole,...fraction]=raw.split(',');return format(whole)+(fraction.length?','+fraction.join(','):'');};
  function enhanceMoney(input){
    if(input.dataset.moneyReady)return;input.dataset.moneyReady='1';
    const update=()=>{
      const before=input.value,pos=input.selectionStart??before.length,left=before.slice(0,pos).replace(/\s/g,'').length;
      if(/^\d[\d\s]*(?:[,.]\d{0,4})?$/.test(before)){
        input.value=moneyFormat(before);let cursor=0,count=0;while(cursor<input.value.length&&count<left){if(!/\s/.test(input.value[cursor]))count++;cursor++;}input.setSelectionRange(cursor,cursor);
      }
      const raw=moneyParse(input.value),invalid=input.value!==''&&(raw===null||Number(raw)>Number(input.dataset.moneyMax||'1000000000000000'));
      input.setCustomValidity(invalid?(typeof EveI18n==='undefined'?'Érvényes, legfeljebb négy tizedesjegyes árat adj meg.':EveI18n.t('Érvényes, legfeljebb négy tizedesjegyes árat adj meg.')):'');
    };
    input.addEventListener('input',update);input.addEventListener('blur',update);input.addEventListener('eve-language-change',update);update();
  }
  function set(input,value){input.value=value==null?'':format(value);validate(input);}
  if(typeof document!=='undefined'){
    const scan=node=>{if(node.nodeType!==1)return;if(node.matches('[data-grouped-number]'))enhance(node);node.querySelectorAll('[data-grouped-number]').forEach(enhance);if(node.matches('[data-grouped-money]'))enhanceMoney(node);node.querySelectorAll('[data-grouped-money]').forEach(enhanceMoney);};
    new MutationObserver(records=>{for(const r of records)for(const node of r.addedNodes)scan(node);}).observe(document.body,{subtree:true,childList:true});scan(document.body);
  }
  if(typeof window!=='undefined')window.addEventListener('eve-language-change',()=>{document.querySelectorAll('[data-grouped-number]').forEach(validate);document.querySelectorAll('[data-grouped-money]').forEach(i=>i.dispatchEvent(new Event('eve-language-change')));});
  return {parse,format,enhance,validate,set,moneyParse,moneyFormat,enhanceMoney};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=EveNumbers;
