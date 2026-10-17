const test=require('node:test'),assert=require('node:assert/strict');
const {text}=require('../static/multibuy.js');
test('Multibuy contains only canonical names and ungrouped quantities',()=>{
 assert.equal(text([{name:'Tritanium',buy:1234567,unit:'db'},{name:'Mexallon',buy:42}]),'Tritanium\t1234567\r\nMexallon\t42');
});
test('BPOs, BPCs and reaction formulas are excluded, remaining amounts are merged',()=>{
 assert.equal(text([{name:'Tritanium',buy:4},{name:'BPO',buy:1,is_blueprint:true},{name:'BPC',buy:3,unit:'run'},
  {name:'Reaction Formula',buy:1,category:'Reakcióformula'},{name:'Tritanium',buy:6},{name:'Zero',buy:0}]),'Tritanium\t10');
 assert.equal(text([{name:'Only Blueprint',buy:1,is_blueprint:true}]),'');
});
test('Invalid numbers and injected columns cannot corrupt import rows',()=>{
 assert.equal(text([{name:'Ore\tType\nName',buy:2},{name:'Invalid',buy:Infinity}]),'Ore Type Name\t2');
 assert.throws(()=>text([{name:'Ore',buy:Number.MAX_SAFE_INTEGER},{name:'Ore',buy:1}]));
});
