const test=require('node:test'),assert=require('node:assert/strict');
const C=require('../static/costs.js');
test('highest buy / lowest sell quotes produce exact split values and cent totals',()=>{
 const quotes={1:{buy:'12.01',sell:'12.02'}};
 assert.equal(C.unit(quotes[1],'buy'),120100n);assert.equal(C.unit(quotes[1],'sell'),120200n);assert.equal(C.unit(quotes[1],'split'),120150n);
 assert.equal(C.value([{id:1,quantity:100_000_000}],quotes,'split').cents,120150000000n);
 assert.equal(C.value([{id:1,quantity:1}],quotes,'split').cents,1202n);
});
test('unknown quote side and BPC runs remain unpriced, never valued as BPOs',()=>{
 const q={1:{buy:'10',sell:null},2:{buy:'1000000',sell:'2000000'}};
 const value=C.value([{id:1,quantity:5},{id:2,quantity:30,unit:'run'}],q,'split');
 assert.equal(value.missing,2);assert.equal(value.cents,0n);assert.equal(value.rows[0].cents,null);
 assert.equal(C.value([{id:1,quantity:5}],q,'buy').cents,5000n);
});
test('large grouped ISK amounts preserve cents beyond Number safe precision',()=>{
 assert.equal(C.format(123456789012345678901n),'1 234 567 890 123 456 789,01 ISK');
 assert.equal(C.formatUnit(120150n),'12,015 ISK');assert.equal(C.formatUnit(10000n),'1,00 ISK');
});
test('material cost values raw inputs plus consumed existing intermediates once',()=>{
 const p={product_id:1,rows:[{id:1,required:1,runs:1,used_stock:0},
  {id:2,name:'Component',required:10,runs:6,used_stock:3,used_wip:1},
  {id:3,name:'Raw',required:60,runs:0,used_stock:30,used_wip:10,buy:20}]};
 assert.deepEqual(C.materials(p).map(r=>[r.id,r.quantity]),[[2,4],[3,60]]);
 assert.equal(C.value(C.materials(p),{2:{buy:'20',sell:'20'},3:{buy:'1',sell:'1'}},'sell').cents,14000n);
});
test('existing completed component cuts off its raw branch and fully covered target costs zero',()=>{
 const p={product_id:1,rows:[{id:1,required:1,runs:1},{id:2,name:'Built component',required:1,runs:0,used_stock:1},{id:3,required:0,runs:0}]};
 assert.deepEqual(C.materials(p).map(r=>[r.id,r.quantity]),[[2,1]]);
 assert.deepEqual(C.materials({product_id:1,rows:[{id:1,required:1,runs:0,used_stock:1},{id:2,required:0,runs:0}]}),[]);
});
test('missing and stale price counts remain visible while known subtotal sums correctly',()=>{
 const v=C.value([{id:1,quantity:2},{id:2,quantity:3}],{1:{sell:'4.5',stale:true}},'sell');
 assert.equal(v.cents,900n);assert.equal(v.stale,1);assert.equal(v.missing,1);
});

test('an entirely unpriced summary shows a dash, not a zero-cost production',()=>{
 const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),{JSDOM}=require('jsdom');
 const dom=new JSDOM('<body></body>',{url:'http://127.0.0.1',runScripts:'outside-only'}),ctx=dom.getInternalVMContext();
 vm.runInContext("const $$=s=>[...document.querySelectorAll(s)];const esc=s=>String(s);const date=s=>String(s);",ctx);
 for(const name of ['costs.js','prices.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../static',name),'utf8'),ctx);
 vm.runInContext("document.body.innerHTML=costSummary('unknown',[{id:1,quantity:10}],'Cost','Description');jitaWanted=[1];applyJita();",ctx);
 assert.equal(dom.window.document.querySelector('[data-cost-grand]').textContent,'–');
 vm.runInContext("jitaData.quotes={1:{sell:'2.01',checked:1}};applyJita();",ctx);
 assert.equal(dom.window.document.querySelector('[data-cost-grand]').textContent,'20,10 ISK');dom.window.close();
});
test('manual fuel prices override all Jita modes, preserve zero and ignore quote staleness',()=>{
  const rows=[{id:4246,quantity:3600,manual_price:'10.1234'},{id:81143,quantity:144000}],quotes={4246:{buy:'99',sell:'101',stale:true},81143:{buy:'1',sell:'3'}};
  assert.equal(C.value(rows,quotes,'sell').cents,46844424n);
  assert.equal(C.value(rows,quotes,'buy').cents,18044424n);
  assert.equal(C.value(rows,quotes,'split').cents,32444424n);
  assert.equal(C.value(rows,quotes,'sell').stale,0);
  assert.equal(C.value([{id:4246,quantity:3600,manual_price:'0'}],{},'sell').cents,0n);
  assert.equal(C.value([{id:4246,quantity:3600,manual_price:'bad'}],quotes,'sell').missing,1);
});
test('fuel aggregates sum rounded per-moon costs without losing cents',()=>{
 const rows=[{id:4246,quantity:3960,manual_price:'0.0001'},{id:4246,quantity:3960,manual_price:'0.0001'}];
 const result=C.value(rows,{},'split');
 assert.equal(result.cents,80n);assert.equal(result.rows[0].cents,40n);
});
test('profit formatting preserves losses and exact percentage fees',()=>{
 assert.equal(C.format(-5n),'-0,05 ISK');assert.equal(C.format(-123456789n),'-1 234 567,89 ISK');
 assert.equal(C.money('123456789012345.6789012345'),12345678901234568n);
 assert.equal(C.percent(123456789n,'2.5'),3086420n);
 assert.equal(C.percent(0n,0),0n);
});
