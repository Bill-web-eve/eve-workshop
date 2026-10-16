const {test}=require('node:test');
const assert=require('node:assert/strict');
const graph=require('../static/graph.js');
const row=(id,stage,extra={})=>({id,name:'Item '+id,stage,activity:stage===1?'reaction':'manufacturing',
  required:10,runs:1,buy:0,materials:[],...extra});
function fixture(){return {rows:[
  row(100,4,{materials:[{id:110,quantity:2},{id:120,quantity:3}]}),
  row(110,3,{materials:[{id:130,quantity:5}]}),
  row(120,3,{materials:[{id:130,quantity:7}]}),
  row(130,1,{materials:[{id:200,quantity:24}]}),
  row(200,0,{activity:'buy',runs:0,buy:24})]};}

test('shared reaction is one node with two outgoing production dependencies',()=>{
  const g=graph.build(fixture());
  assert.deepEqual(g.nodes.map(n=>n.id),[100,110,120,130]);
  assert.deepEqual(g.edges.filter(e=>e.from===130),[{from:130,to:110,quantity:5},{from:130,to:120,quantity:7}]);
});
test('purchase toggle shows only actual net shortages',()=>{
  const p=fixture();p.rows.push(row(201,0,{activity:'buy',runs:0,buy:0,required:0}));
  const g=graph.build(p,{purchases:true});
  assert.deepEqual(g.nodes.filter(n=>n.kind==='buy').map(n=>n.id),[200]);
  assert.ok(g.edges.some(e=>e.from===200&&e.to===130&&e.quantity===24));
});
test('finished or in-progress components hide their unused input branch',()=>{
  const p=fixture();p.rows[1].runs=0;p.rows[1].materials=[{id:130,quantity:0}];
  let g=graph.build(p);assert.ok(!g.nodes.some(n=>n.id===110));
  g=graph.build(p,{covered:true});assert.equal(g.nodes.find(n=>n.id===110).kind,'covered');
  assert.ok(g.edges.some(e=>e.from===110&&e.to===100));
  assert.ok(!g.edges.some(e=>e.from===130&&e.to===110));
});
test('fully covered target does not recreate reactions or raw demand',()=>{
  const p=fixture();p.rows.forEach(n=>{n.runs=0;n.buy=0;n.required=0;n.materials=[];});
  p.rows[0].required=1;
  assert.equal(graph.build(p).nodes.length,0);
  const g=graph.build(p,{covered:true,purchases:true});
  assert.deepEqual(g.nodes.map(n=>n.id),[100]);assert.equal(g.edges.length,0);
});
test('selection does not highlight a sibling simply because it shares an input',()=>{
  const g=graph.build(fixture(),{purchases:true});
  assert.deepEqual([...graph.branch(g,110)].sort((a,b)=>a-b),[100,110,130,200]);
  assert.deepEqual([...graph.branch(g,100)].sort((a,b)=>a-b),[100,110,120,130,200]);
});
test('layout keeps nodes separate and arrows forward without modifying plan quantities',()=>{
  const p=fixture(),before=JSON.stringify(p),g=graph.build(p,{purchases:true});
  assert.equal(JSON.stringify(p),before);
  for(const a of g.nodes)for(const b of g.nodes){
    if(a.id===b.id)continue;
    assert.ok(a.x+a.width<=b.x||b.x+b.width<=a.x||a.y+a.height<=b.y||b.y+b.height<=a.y);
  }
  for(const edge of g.edges){
    assert.ok(g.nodes.find(n=>n.id===edge.from).x<g.nodes.find(n=>n.id===edge.to).x);
    assert.ok(!/NaN|undefined|Infinity/.test(graph.path(g,edge)));
  }
});
test('empty and single-node plans have usable dimensions and bounded labels',()=>{
  for(const rows of [[],[row(1,1)]]){
    const g=graph.build({rows});assert.ok(g.width>0&&g.height>0);
  }
  const name='Capital Super Long Shared Component With Many Different Names';
  const lines=graph.wrap(name);assert.equal(lines.length,2);assert.ok(lines.every(l=>l.length<=29));
});
