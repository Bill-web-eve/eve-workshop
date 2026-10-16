const {test}=require('node:test');
const assert=require('node:assert/strict');
const {parse,format}=require('../static/numbers.js');
test('grouped quantities remain exact at the 100 million boundary',()=>{
  for(const n of [1,999,1000,1000000,100000000,1000000000000])assert.equal(parse(format(n)),n);
  assert.equal(format(100000000),'100 000 000');
  assert.equal(parse('100\u00a0000\u202f000'),100000000);
});
test('decimal, exponent, negative and invalid quantity input is rejected',()=>{
  for(const s of ['1e8','1.5','1,5','-1','abc',''])assert.ok(Number.isNaN(parse(s)));
});
test('grouped monetary input preserves four decimal places without numeric rounding',()=>{
 const N=require('../static/numbers.js');
 for(const [source,shown,parsed] of [['12345.6789','12 345,6789','12345.6789'],['1000000000000.0001','1 000 000 000 000,0001','1000000000000.0001'],['0','0','0'],['12,','12,','12']]){
  assert.equal(N.moneyFormat(source),shown);assert.equal(N.moneyParse(shown),parsed);
 }
 for(const bad of ['1e5','-1','12.12345','abc'])assert.equal(N.moneyParse(bad),null);
});
