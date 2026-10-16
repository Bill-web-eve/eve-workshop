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
