'use strict';
const EveTables=(()=>{
  const t=value=>typeof EveI18n==='undefined'?value:EveI18n.t(value);
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normalize=value=>String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('hu-HU').replace(/\s+/g,' ').trim();
  const collator=new Intl.Collator('hu',{numeric:true,sensitivity:'base'});
  const number=value=>{
    const text=String(value??'').trim().replace(/−/g,'-');
    if(!/^[+-]?\d[\d\s]*(?:[.,]\d+)?(?:\s*(?:%|db|units|run|m³))?$/.test(text))return null;
    const result=Number(text.replace(/\s/g,'').replace(/(?:%|db|units|run|m³)$/,'').replace(',','.'));
    return Number.isFinite(result)?result:null;
  };
  function compare(a,b,direction=1){
    // Unknown values remain at the bottom in both directions.
    if(a===null||b===null)return a===b?0:a===null?1:-1;
    return direction*(typeof a==='number'&&typeof b==='number'?a-b:collator.compare(String(a),String(b)));
  }
  function matches(text,query){
    const value=normalize(text),needle=normalize(query);
    return value.includes(needle)||(/^[\d\s,.+-]+$/.test(needle)&&value.replace(/\s/g,'').includes(needle.replace(/\s/g,'')));
  }
  const states=new Map(),instances=new WeakMap();
  let size=100;
  try{const saved=Number(localStorage.getItem('eve-muhely-table-page-size'));if([25,50,100].includes(saved))size=saved;}catch{}
  const pageSize=()=>size;
  const sizeControl=()=>`<label class="table-page-size"><span>Sor oldalanként</span><select data-table-page-size aria-label="Sor oldalanként">${[25,50,100].map(n=>`<option value="${n}" ${n===size?'selected':''}>${n}</option>`).join('')}</select></label>`;
  function setPageSize(value){
    if(![25,50,100].includes(Number(value)))return;
    size=Number(value);try{localStorage.setItem('eve-muhely-table-page-size',String(size));}catch{}
    for(const setting of states.values())setting.page=0;
    refreshAll();if(typeof window!=='undefined')window.dispatchEvent(new Event('eve-table-page-size-change'));
  }
  let filterRowId=0;
  function markup(headers,rows,cls,key,options={}){
    const heading=headers.map((h,i)=>`<th scope="col" aria-sort="none" data-column="${i}" data-label="${escape(h)}"><button type="button" class="table-sort" data-table-sort="${i}" aria-label="Rendezés: ${escape(h)}" title="Növekvő, csökkenő, majd eredeti sorrend">${escape(h)}<span class="table-sort-icon" aria-hidden="true">↕</span></button></th>`).join('');
    const filters=headers.map((h,i)=>`<td>${/^karakter(?: neve|név)?$/i.test(h)||options.selectColumns?.includes(i)?`<select data-table-filter="${i}" aria-label="${escape(h)} – oszlopszűrő"><option value="">${/^karakter(?: neve|név)?$/i.test(h)?'Minden karakter':'Minden hold'}</option></select>`:`<input type="search" data-table-filter="${i}" aria-label="${escape(h)} – oszlopszűrő" placeholder="Szűrés…" autocomplete="off">`}</td>`).join('');
    return `<div class="table-block"><div class="table-tools"><span data-table-count role="status"></span><div class="table-tool-actions">${sizeControl()}<button type="button" class="text-button" data-table-toggle-filters aria-expanded="false">Szűrők megnyitása</button><button type="button" class="text-button" data-table-reset>Rendezés és oszlopszűrők törlése</button></div></div><div class="table-scroll"><table class="data-table ${escape(cls)}" data-table-key="${escape(key)}"><thead><tr>${heading}</tr><tr class="table-filters" hidden>${filters}</tr></thead><tbody>${rows.join('')}</tbody></table></div><div class="table-pagination"><button type="button" class="button compact" data-table-prev aria-label="Előző oldal">←</button><span data-table-page role="status"></span><button type="button" class="button compact" data-table-next aria-label="Következő oldal">→</button></div></div>`;
  }
  function cellValue(cell){
    if(!cell)return {text:'',sort:null};
    const clone=cell.cloneNode(true);
    clone.querySelectorAll('input,select,textarea').forEach(el=>el.remove());
    const controls=[...cell.querySelectorAll('input,select,textarea')].map(el=>el.tagName==='SELECT'?[...el.selectedOptions].map(o=>o.textContent).join(' '):el.value||el.placeholder||'');
    const text=cell.hasAttribute('data-filter-value')?cell.dataset.filterValue:[clone.textContent,...controls].join(' ').replace(/\s+/g,' ').trim();
    if(cell.hasAttribute('data-sort-value')){
      const raw=cell.dataset.sortValue;
      return {text,sort:raw===''?null:Number.isFinite(Number(raw))?Number(raw):raw};
    }
    const input=cell.querySelector('input,select,textarea');
    if(input){
      const value=input.tagName==='SELECT'?[...input.selectedOptions].map(o=>o.textContent).join(' '):input.value;
      return {text,sort:input.type==='number'||input.hasAttribute('data-grouped-number')?(input.value===''?null:number(input.value)):value||null};
    }
    clone.querySelectorAll('small,.batch-note,.pi-row-note,.skill-error,.row-warning').forEach(el=>el.remove());
    const primary=clone.textContent.replace(/\s+/g,' ').trim();
    return {text,sort:!primary||['–','—'].includes(primary)?null:number(primary)??primary};
  }
  function apply(table){
    const info=instances.get(table);if(!info)return;
    const setting=states.get(info.key),cache=new Map();
    const value=(row,index)=>{
      if(!cache.has(row))cache.set(row,new Map());
      const cells=cache.get(row);if(!cells.has(index))cells.set(index,cellValue(row.cells[index]));return cells.get(index);
    };
    let visible=0;
    for(const row of info.rows){
      const external=!info.search||matches(row.dataset[info.searchAttribute]||'',info.search);
      const accepted=external&&setting.filters.every((query,i)=>!query||(info.characterColumns.has(i)?value(row,i).text===query:matches(value(row,i).text,query)));
      row.hidden=!accepted;if(accepted)visible++;
    }
    const sorted=[...info.rows];
    if(setting.sort)sorted.sort((a,b)=>compare(value(a,setting.sort.column).sort,value(b,setting.sort.column).sort,setting.sort.direction)||info.order.get(a)-info.order.get(b));
    const pages=Math.max(1,Math.ceil(visible/size));setting.page=Math.max(0,Math.min(setting.page||0,pages-1));
    let acceptedIndex=0;
    for(const row of sorted)if(!row.hidden){const index=acceptedIndex++;row.hidden=index<setting.page*size||index>=(setting.page+1)*size;}
    for(const row of sorted)table.tBodies[0].append(row);
    table.tBodies[0].append(info.empty);info.empty.hidden=visible!==0;
    info.block.querySelector('[data-table-count]').textContent=t(`${visible.toLocaleString('hu-HU')} / ${info.rows.length.toLocaleString('hu-HU')} sor · ${setting.sort?'Egyéni rendezés':'Eredeti sorrend'}`);
    info.block.querySelector('[data-table-reset]').disabled=!setting.sort&&!setting.filters.some(Boolean);
    info.block.querySelector('[data-table-page-size]').value=String(size);
    info.block.querySelector('[data-table-page]').textContent=`${setting.page+1} / ${pages}`;
    info.block.querySelector('[data-table-prev]').disabled=setting.page===0;
    info.block.querySelector('[data-table-next]').disabled=setting.page===pages-1;
    const toggle=info.block.querySelector('[data-table-toggle-filters]'),activeFilters=setting.filters.filter(Boolean).length;
    table.querySelector('.table-filters').hidden=!setting.filtersOpen;
    toggle.setAttribute('aria-expanded',String(setting.filtersOpen));
    toggle.textContent=t((setting.filtersOpen?'Szűrők bezárása':'Szűrők megnyitása')+(activeFilters?` · ${activeFilters} aktív`:''));
    toggle.title=t('A szűrősor becsukása nem törli a beállított szűrést.');
    for(const th of table.tHead.rows[0].cells){
      const active=setting.sort?.column===th.cellIndex;
      th.setAttribute('aria-sort',active?(setting.sort.direction===1?'ascending':'descending'):'none');
      th.querySelector('.table-sort-icon').textContent=active?(setting.sort.direction===1?'↑':'↓'):'↕';
    }
  }
  function enhance(table){
    if(instances.has(table))return;
    const key=table.dataset.tableKey,headers=[...table.tHead.rows[0].cells],rows=[...table.tBodies[0].rows];
    if(!states.has(key))states.set(key,{sort:null,filters:headers.map(()=> ''),filtersOpen:false,page:0});
    const setting=states.get(key),block=table.closest('.table-block'),characterColumns=new Set();
    const empty=document.createElement('tr');empty.className='table-empty-row';
    const message=document.createElement('td');message.colSpan=headers.length;message.textContent='Nincs a szűrésnek megfelelő sor.';empty.append(message);
    instances.set(table,{key,block,rows,order:new Map(rows.map((row,i)=>[row,i])),empty,characterColumns,search:'',searchAttribute:'search'});
    const heading=table.closest('.panel')?.querySelector('h2');
    table.setAttribute('aria-label',(typeof EveI18n==='undefined'?heading?.textContent:EveI18n.sourceText(heading))||'Táblázat');
    const filterRow=table.querySelector('.table-filters');filterRow.id='table-filters-'+(++filterRowId);
    const toggle=block.querySelector('[data-table-toggle-filters]');toggle.setAttribute('aria-controls',filterRow.id);
    toggle.addEventListener('click',()=>{setting.filtersOpen=!setting.filtersOpen;apply(table);});
    block.querySelector('[data-table-page-size]').addEventListener('change',event=>setPageSize(event.target.value));
    block.querySelector('[data-table-prev]').addEventListener('click',()=>{setting.page--;apply(table);});
    block.querySelector('[data-table-next]').addEventListener('click',()=>{setting.page++;apply(table);});
    for(const control of table.querySelectorAll('[data-table-filter]')){
      const index=Number(control.dataset.tableFilter);
      if(control.tagName==='SELECT'){
        characterColumns.add(index);
        const names=new Set(rows.map(r=>cellValue(r.cells[index]).text).filter(Boolean));
        if(setting.filters[index]&&!names.has(setting.filters[index]))setting.filters[index]='';
        for(const name of [...names].sort(collator.compare)){const option=document.createElement('option');option.value=name;option.textContent=name;control.append(option);}
      }
      control.value=setting.filters[index]||'';
      const filter=()=>{setting.filters[index]=control.value;setting.page=0;apply(table);};
      control.addEventListener(control.tagName==='SELECT'?'change':'input',filter);
    }
    for(const button of table.querySelectorAll('[data-table-sort]'))button.addEventListener('click',()=>{
      const column=Number(button.dataset.tableSort),previous=setting.sort;
      setting.sort=previous?.column===column?(previous.direction===1?{column,direction:-1}:null):{column,direction:1};
      setting.page=0;
      apply(table);
    });
    block.querySelector('[data-table-reset]').addEventListener('click',()=>{
      setting.sort=null;setting.page=0;setting.filters.fill('');table.querySelectorAll('[data-table-filter]').forEach(control=>control.value='');apply(table);
    });
    apply(table);
  }
  function setSearch(table,search,attribute='search'){
    if(!table)return;enhance(table);const info=instances.get(table);if(info.search!==search)states.get(info.key).page=0;info.search=search;info.searchAttribute=attribute;apply(table);
  }
  if(typeof document!=='undefined'){
    const scan=node=>{if(node.nodeType!==1)return;if(node.matches('table[data-table-key]'))enhance(node);else node.querySelectorAll('table[data-table-key]').forEach(enhance);};
    new MutationObserver(records=>{for(const record of records)for(const node of record.addedNodes)scan(node);}).observe(document.body,{childList:true,subtree:true});
    scan(document.body);
  }
  function refreshAll(){if(typeof document!=='undefined')document.querySelectorAll('table[data-table-key]').forEach(table=>{if(instances.has(table))apply(table);});}
  if(typeof window!=='undefined')window.addEventListener('eve-language-change',refreshAll);
  return {markup,enhance,setSearch,normalize,number,compare,matches,refreshAll,pageSize,setPageSize,sizeControl};
})();
globalThis.EveTables=EveTables;
if(typeof module!=='undefined'&&module.exports)module.exports=EveTables;
