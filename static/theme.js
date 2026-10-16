'use strict';
// Apply before styles load so a saved dark theme never flashes white.
(()=>{
  const key='eve-muhely-theme';
  let theme='dark';
  try{const saved=localStorage.getItem(key);if(['dark','light'].includes(saved))theme=saved;}catch{}
  function apply(value){
    theme=value;
    document.documentElement.dataset.theme=theme;
    const toggle=document.getElementById('theme-toggle');
    if(toggle){
      toggle.setAttribute('aria-pressed',String(theme==='dark'));
      toggle.title=theme==='dark'?'Váltás világos módra':'Váltás sötét módra';
    }
  }
  apply(theme);
  document.addEventListener('DOMContentLoaded',()=>{
    apply(theme);
    document.getElementById('theme-toggle').addEventListener('click',()=>{
      apply(theme==='dark'?'light':'dark');
      try{localStorage.setItem(key,theme);}catch{}
    });
  },{once:true});
  window.addEventListener('storage',event=>{
    if(event.key===key)apply(event.newValue==='light'?'light':'dark');
  });
})();
