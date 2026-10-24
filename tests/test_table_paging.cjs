'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
function fixture(){
 const dom=new JSDOM('<body></body>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document;
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/tables.js'),'utf8'),dom.getInternalVMContext());
 d.body.innerHTML=w.EveTables.markup(['Item','Quantity'],Array.from({length:123},(_,i)=>`<tr data-search="Item ${i}"><td>Item ${i}</td><td>${i}</td></tr>`),'','paging');
 const table=d.querySelector('table');w.EveTables.enhance(table);
 return {w,d,table,close:()=>w.close(),visible:()=>[...table.tBodies[0].rows].filter(r=>!r.hidden&&!r.classList.contains('table-empty-row'))};
}
test('25/50/100 paging preserves every row and sorts and filters the entire dataset',t=>{
 const f=fixture();t.after(f.close);const {w,d,table}=f;
 assert.equal(f.visible().length,100);
 const size=d.querySelector('[data-table-page-size]');size.value='25';size.dispatchEvent(new w.Event('change'));
 assert.equal(f.visible().length,25);assert.equal(w.localStorage.getItem('eve-muhely-table-page-size'),'25');
 d.querySelector('[data-table-next]').click();assert.equal(f.visible()[0].cells[1].textContent,'25');
 d.querySelector('[data-table-sort="1"]').click();d.querySelector('[data-table-sort="1"]').click();assert.equal(f.visible()[0].cells[1].textContent,'122');
 const query=table.querySelector('[data-table-filter="0"]');query.value='Item 122';query.dispatchEvent(new w.Event('input'));assert.equal(f.visible().length,1);assert.equal(f.visible()[0].cells[1].textContent,'122');
 d.querySelector('[data-table-reset]').click();w.EveTables.setPageSize(50);assert.equal(f.visible().length,50);
 assert.equal(table.querySelectorAll('tbody tr:not(.table-empty-row)').length,123);
});
test('external search resets an invalid page and all rendered tables share the saved size',t=>{
 const f=fixture();t.after(f.close);const {w,d,table}=f;w.EveTables.setPageSize(25);
 d.querySelector('[data-table-next]').click();w.EveTables.setSearch(table,'Item 122');assert.equal(f.visible().length,1);
 const panel=d.createElement('section');panel.innerHTML=w.EveTables.markup(['Other'],['<tr><td>Only one</td></tr>'],'','other');d.body.append(panel);w.EveTables.enhance(panel.querySelector('table'));
 assert.equal(panel.querySelector('[data-table-page-size]').value,'25');assert.equal(panel.querySelector('[data-table-next]').disabled,true);
 w.EveTables.setPageSize(17);assert.equal(w.EveTables.pageSize(),25);
});
