'use strict';
// Local presentation only: never translate stored values, EVE names or user input.
const EveI18n=(()=>{
  const key='eve-muhely-language',catalog=globalThis.EveEnglish||{};
  const normalize=s=>String(s).replace(/\s+/g,' ').trim();
  const escaped=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
  const patterns=[];
  for(const [source,target] of Object.entries(catalog)){
    const slots=[];let last=0,regex='';
    for(const match of source.matchAll(/\{(\d+)\}/g)){
      regex+=escaped(source.slice(last,match.index))+'(.*?)';slots.push(match[1]);last=match.index+match[0].length;
    }
    if(slots.length)patterns.push({regex:new RegExp('^'+regex+escaped(source.slice(last))+'$'),slots,target,weight:source.replace(/\{\d+\}/g,'').length});
  }
  patterns.sort((a,b)=>b.weight-a.weight);
  let language='hu',observer=null,ready=false;
  try{if(localStorage.getItem(key)==='en')language='en';}catch{}
  const sources=new WeakMap(),attributes=new WeakMap(),cache=new Map(),dates=new Map();
  const skip='[data-i18n-skip],script,style,code,pre,textarea,.copy-item-name,[data-filter-value],.character-name,.skill-character-name,.pi-planet-name,select[data-table-filter] option:not([value=""])';
  function formatCapture(value){
    if(dates.has(value))return dates.get(value);
    let result=value;
    for(const [hu,en] of dates)if(result.includes(hu))result=result.split(hu).join(en);
    return result;
  }
  function english(source,depth=0){
    if(cache.has(source))return cache.get(source);
    if(dates.has(source))return dates.get(source);
    let result=catalog[source];
    if(result===undefined){
      for(const pattern of patterns){
        const found=source.match(pattern.regex);if(!found)continue;
        const values=Object.fromEntries(pattern.slots.map((slot,i)=>[slot,found[i+1]]));
        result=pattern.target.replace(/\{(\d+)(:t)?\}/g,(_,id,recursive)=>recursive&&depth<4?english(normalize(values[id]??''),depth+1):formatCapture(values[id]??''));
        break;
      }
    }
    if(result===undefined&&depth<4){
      // Compound server messages: translate sentences and the error after a
      // character-name prefix, preserving the name and all unknown text.
      const parts=source.split(/(?<=[.!?])\s+(?=[A-ZÁÉÍÓÖŐÚÜŰ0-9])/);
      if(parts.length>1)result=parts.map(part=>english(part,depth+1)).join(' ');
      else{
        const colon=source.indexOf(': ');
        if(colon>0){const tail=source.slice(colon+2),translated=english(tail,depth+1);if(tail!==translated)result=source.slice(0,colon+2)+translated;}
      }
    }
    result=formatCapture(result??source);
    if(depth===0){if(cache.size>8192)cache.clear();cache.set(source,result);}
    return result;
  }
  function t(value){
    const text=String(value??'');if(language==='hu'||!text.trim())return text;
    if(text.includes('\n'))return text.split('\n').map(t).join('\n');
    const body=normalize(text),leading=text.match(/^\s*/)[0],trailing=text.match(/\s*$/)[0];
    return leading+english(body)+trailing;
  }
  // Return the canonical Hungarian date. The presentation layer can switch
  // existing dates in place without rebuilding forms or changing their values.
  function date(value,options){
    const d=value instanceof Date?value:new Date(value);
    const hu=d.toLocaleString('hu-HU',options),en=d.toLocaleString('en-GB',options);
    dates.set(normalize(hu),en);cache.clear();return hu;
  }
  function project(node,map,read,write){
    const current=read();let info=map.get(node);
    if(!info||current!==info.last)info={source:current,last:current};
    const translated=t(info.source);info.last=translated;map.set(node,info);
    if(current===translated)return false;write(translated);return true;
  }
  function translate(root=document.documentElement){
    if(!root)return;
    let tableChanged=false;
    const visit=node=>{
      if(node.nodeType===3){
        if(node.parentElement?.closest(skip))return;
        if(node.parentElement?.dataset.i18nName===node.data)return;
        if(project(node,sources,()=>node.data,value=>node.data=value)&&node.parentElement?.closest('tbody'))tableChanged=true;
        return;
      }
      if(node.nodeType!==1||node.matches('script,style,code,pre,textarea,[data-i18n-skip]'))return;
      for(const name of ['title','aria-label','placeholder','alt'])if(node.hasAttribute(name)){
        let maps=attributes.get(node);if(!maps){maps=new Map();attributes.set(node,maps);}
        let source=maps.get(name),current=node.getAttribute(name);
        if(!source||source.last!==current)source={source:current,last:current};
        const translated=t(source.source);source.last=translated;maps.set(name,source);
        if(translated!==current)node.setAttribute(name,translated);
      }
      for(const child of node.childNodes)visit(child);
    };
    visit(root);
    if(tableChanged)globalThis.EveTables?.refreshAll?.();
  }
  function controls(){
    document.documentElement.lang=language;
    document.documentElement.dataset.language=language;
    for(const button of document.querySelectorAll('[data-ui-language]'))button.setAttribute('aria-pressed',String(button.dataset.uiLanguage===language));
  }
  function sourceText(node){
    if(!node)return '';
    if(node.nodeType===3){const info=sources.get(node);return info&&info.last===node.data?info.source:node.data;}
    return [...node.childNodes].map(sourceText).join('');
  }
  function setLanguage(value,persist=true){
    value=value==='en'?'en':'hu';language=value;cache.clear();
    if(typeof document==='undefined')return;
    if(persist)try{localStorage.setItem(key,language);}catch{}
    controls();if(ready)translate();
    window.dispatchEvent(new CustomEvent('eve-language-change',{detail:{language}}));
  }
  function init(){
    ready=true;controls();translate();
    document.addEventListener('click',event=>{const button=event.target.closest('[data-ui-language]');if(button)setLanguage(button.dataset.uiLanguage);});
    observer=new MutationObserver(records=>{
      const roots=new Set();
      for(const record of records){
        if(record.type==='characterData')roots.add(record.target);
        else if(record.type==='attributes')roots.add(record.target);
        else for(const node of record.addedNodes)roots.add(node);
      }
      for(const node of roots)if(node.isConnected)translate(node);
    });
    observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['title','aria-label','placeholder','alt']});
    window.addEventListener('storage',event=>{if(event.key===key)setLanguage(event.newValue,false);});
  }
  if(typeof document!=='undefined'){
    document.documentElement.lang=language;
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  }
  return {t,date,translate,sourceText,setLanguage,get language(){return language;},get locale(){return language==='en'?'en-GB':'hu-HU';}};
})();
globalThis.EveI18n=EveI18n;
if(typeof module!=='undefined'&&module.exports)module.exports=EveI18n;
