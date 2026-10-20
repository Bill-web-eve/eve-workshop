'use strict';
// Apply before styles load; dynamic Settings controls use the same preference.
globalThis.EveTheme=(()=>{
  const key='eve-muhely-theme';let theme='dark';
  try{const saved=localStorage.getItem(key);if(['dark','light'].includes(saved))theme=saved;}catch{}
  function apply(value){
    theme=value==='light'?'light':'dark';document.documentElement.dataset.theme=theme;
    for(const toggle of document.querySelectorAll('[data-theme-toggle],#theme-toggle')){
      toggle.setAttribute('aria-pressed',String(theme==='dark'));
      toggle.title=theme==='dark'?'Váltás világos módra':'Váltás sötét módra';
    }
    window.dispatchEvent(new CustomEvent('eve-theme-change',{detail:{theme}}));
  }
  function setTheme(value){apply(value);try{localStorage.setItem(key,theme);}catch{}}
  apply(theme);
  document.addEventListener('DOMContentLoaded',()=>apply(theme),{once:true});
  document.addEventListener('click',event=>{if(event.target.closest('[data-theme-toggle],#theme-toggle'))setTheme(theme==='dark'?'light':'dark');});
  window.addEventListener('storage',event=>{if(event.key===key)apply(event.newValue);});
  return {setTheme,get theme(){return theme;}};
})();
