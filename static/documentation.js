'use strict';
// Small, escaped Markdown renderer for the bundled manuals. No raw HTML,
// executable URLs, remote scripts or external Markdown dependency.
const EveManual=(()=>{
  const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normalize=s=>String(s).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase().replace(/\s+/g,' ').trim();
  function inline(source,depth=0){
    if(depth>5)return escape(source);
    const tokens=/(`[^`\n]+`|\*\*[^*\n]+\*\*|\[[^\]\n]+\]\([^\s)]+\)|https?:\/\/[^\s<>]+)/g;
    let html='',last=0;
    for(const match of source.matchAll(tokens)){
      html+=escape(source.slice(last,match.index));const text=match[0];
      if(text.startsWith('`'))html+='<code>'+escape(text.slice(1,-1))+'</code>';
      else if(text.startsWith('**'))html+='<strong>'+inline(text.slice(2,-2),depth+1)+'</strong>';
      else{
        const link=text.match(/^\[([^\]]+)\]\(([^)]+)\)$/),url=link?link[2]:text;
        html+=/^https?:\/\//i.test(url)?`<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">${inline(link?link[1]:url,6)}</a>`:escape(text);
      }
      last=match.index+text.length;
    }
    return html+escape(source.slice(last));
  }
  function blocks(lines){
    let html='',i=0;
    const cells=line=>line.trim().replace(/^\||\|$/g,'').split('|').map(c=>c.trim());
    const list=line=>line.match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
    while(i<lines.length){
      const line=lines[i];if(!line.trim()){i++;continue;}
      const heading=line.match(/^(#{1,6})\s+(.+)$/);
      if(heading){const n=Math.max(2,heading[1].length);html+=`<h${n}>${inline(heading[2])}</h${n}>`;i++;continue;}
      if(line.startsWith('```')){
        const code=[];i++;while(i<lines.length&&!lines[i].startsWith('```'))code.push(lines[i++]);i++;
        html+='<pre><code>'+escape(code.join('\n'))+'</code></pre>';continue;
      }
      if(line.includes('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){
        const headers=cells(line);i+=2;let rows='';
        while(i<lines.length&&lines[i].includes('|')){rows+='<tr>'+cells(lines[i++]).map(c=>'<td>'+inline(c)+'</td>').join('')+'</tr>';}
        html+='<div class="manual-table"><table><thead><tr>'+headers.map(c=>'<th scope="col">'+inline(c)+'</th>').join('')+'</tr></thead><tbody>'+rows+'</tbody></table></div>';continue;
      }
      const match=list(line);
      if(match){
        const ordered=/\d/.test(match[2]),tag=ordered?'ol':'ul',indent=match[1].length;
        html+=`<${tag}${ordered?` start="${parseInt(match[2],10)}"`:''}>`;
        while(i<lines.length){
          const current=list(lines[i]);if(!current||current[1].length!==indent||/\d/.test(current[2])!==ordered)break;
          html+='<li>'+inline(current[3]);i++;const nested=[];
          while(i<lines.length){
            if(!lines[i].trim()){
              let next=i+1;while(next<lines.length&&!lines[next].trim())next++;
              if(next<lines.length&&/^\s/.test(lines[next])&&lines[next].search(/\S/)>indent){nested.push('');i++;continue;}
              break;
            }
            if(lines[i].search(/\S/)>indent){nested.push(lines[i].slice(indent+2));i++;}else break;
          }
          if(nested.length)html+=blocks(nested);html+='</li>';
          // Blank lines may separate items in a Markdown list.
          let next=i;while(next<lines.length&&!lines[next].trim())next++;
          const following=list(lines[next]||'');if(following&&following[1].length===indent&&/\d/.test(following[2])===ordered)i=next;
        }
        html+=`</${tag}>`;continue;
      }
      const paragraph=[line];i++;
      while(i<lines.length&&lines[i].trim()&&!/^#{1,6}\s|^```/.test(lines[i])&&!list(lines[i]))paragraph.push(lines[i++]);
      html+='<p>'+inline(paragraph.join(' ').trim())+'</p>';
    }
    return html;
  }
  function parse(markdown){
    let title='',section=null;const sections=[];
    for(const line of markdown.replace(/\r\n?/g,'\n').split('\n')){
      if(/^# /.test(line)&&!title){title=line.slice(2);continue;}
      if(/^## /.test(line)){section={id:'manual-section-'+sections.length,title:line.slice(3),lines:[]};sections.push(section);}
      else{if(!section){section={id:'manual-section-0',title:title||'EVE Workshop',lines:[]};sections.push(section);}section.lines.push(line);}
    }
    return {title,sections:sections.filter(s=>s.lines.some(l=>l.trim())).map(s=>({...s,html:blocks(s.lines),search:normalize(s.title+' '+s.lines.join(' '))}))};
  }
  function matches(section,query){return normalize(query).split(' ').filter(Boolean).every(word=>section.search.includes(word));}
  return {parse,matches,normalize};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=EveManual;

if(typeof document!=='undefined'){
  const manualCache=new Map();let manualGeneration=0,manualQuery='',manualData=null;
  async function renderDocumentation(content){
    const generation=++manualGeneration,language=EveI18n.language;
    setHead('SEGÍTSÉG','Dokumentáció','Teljes felhasználói kézikönyv · keresés és tartalomjegyzék.');
    $('#plan-status').hidden=true;
    actions('<button class="button compact" id="manual-download" disabled>Kézikönyv letöltése</button><button class="button compact" id="manual-print" disabled>Nyomtatás / PDF</button>');
    content.innerHTML=empty('Kézikönyv betöltése…');
    try{
      if(!manualCache.has(language))manualCache.set(language,api('/api/documentation?lang='+language).catch(e=>{manualCache.delete(language);throw e;}));
      const data=await manualCache.get(language);
      if(generation!==manualGeneration||view!=='documentation'||language!==EveI18n.language)return;
      manualData={...data,...EveManual.parse(data.markdown)};
      content.innerHTML=`<div class="manual-toolbar panel panel-body"><label for="manual-search">Keresés a kézikönyvben</label><div class="manual-search-row"><input id="manual-search" type="search" placeholder="Funkció, beállítás vagy hibaüzenet…" value="${esc(manualQuery)}"><button class="button compact" id="manual-clear">Keresés törlése</button></div><p id="manual-count" class="footnote" role="status"></p></div><details class="manual-toc panel" open><summary>Tartalomjegyzék</summary><nav id="manual-toc" aria-label="Kézikönyv fejezetei" data-i18n-skip lang="${language}">${manualData.sections.map(s=>`<a href="#${s.id}" data-manual-link="${s.id}">${esc(s.title)}</a>`).join('')}</nav></details><div id="manual-empty" class="banner" hidden>Nincs találat. Próbálj másik keresőkifejezést.</div><article class="manual-content" data-i18n-skip lang="${language}" aria-label="${esc(manualData.title)}"><div class="manual-title">${esc(manualData.title)}</div>${manualData.sections.map(s=>`<section class="manual-section panel panel-body" id="${s.id}" tabindex="-1"><h2>${esc(s.title)}</h2>${s.html}</section>`).join('')}</article>`;
      const filter=()=>{
        let count=0;
        for(const section of manualData.sections){const visible=EveManual.matches(section,manualQuery);$('#'+section.id).hidden=!visible;content.querySelector(`[data-manual-link="${section.id}"]`).hidden=!visible;if(visible)count++;}
        $('#manual-empty').hidden=count>0;
        $('#manual-count').textContent=EveI18n.t('{0} / {1} fejezet').replace('{0}',count).replace('{1}',manualData.sections.length);
        $('#manual-clear').disabled=!manualQuery;
      };
      $('#manual-search').oninput=event=>{manualQuery=event.target.value;filter();};
      $('#manual-clear').onclick=()=>{manualQuery='';$('#manual-search').value='';filter();$('#manual-search').focus();};
      content.querySelectorAll('[data-manual-link]').forEach(link=>link.onclick=event=>{event.preventDefault();const section=$('#'+link.dataset.manualLink);section.scrollIntoView({block:'start'});section.focus({preventScroll:true});});
      $('#manual-download').disabled=false;$('#manual-download').onclick=()=>{
        const url=URL.createObjectURL(new Blob([data.markdown],{type:'text/markdown;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='EVE-Workshop-User-Guide-'+language+'.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      };
      $('#manual-print').disabled=false;$('#manual-print').onclick=()=>window.print();
      document.body.classList.add('manual-view');filter();
    }catch(e){if(generation===manualGeneration&&view==='documentation'){content.innerHTML=empty('A kézikönyv nem tölthető be.',e.message);}}
  }
  globalThis.renderDocumentation=renderDocumentation;
  window.addEventListener('eve-language-change',()=>{if(view==='documentation'&&state)void renderDocumentation($('#view-content'));});
}
