const {test}=require('node:test');
const assert=require('node:assert/strict');
const {number,compare,matches}=require('../static/tables.js');

test('Hungarian quantities and percentages sort by value across digit and decimal boundaries',()=>{
  const values=['10 000','900','2','12,5%','0','–'].map(number);
  assert.deepEqual(values.sort((a,b)=>compare(a,b)),[0,2,12.5,900,10000,null]);
  assert.deepEqual(values.sort((a,b)=>compare(a,b,-1)),[10000,900,12.5,2,0,null]);
});
test('text sorting is natural, case insensitive and leaves equal values stable',()=>{
  const values=['Item 100','item 2','Item 10'];
  assert.deepEqual(values.sort(compare),['item 2','Item 10','Item 100']);
  assert.equal(compare('Ferrofluid','ferrofluid'),0);
});
test('timestamp sorting crosses month and year boundaries; missing dates stay last',()=>{
  const dates=[Date.UTC(2027,0,1),null,Date.UTC(2026,11,31),Date.UTC(2026,9,15)];
  assert.deepEqual(dates.sort((a,b)=>compare(a,b,-1)),[Date.UTC(2027,0,1),Date.UTC(2026,11,31),Date.UTC(2026,9,15),null]);
});
test('free text filters ignore accents and accept ungrouped quantities',()=>{
  assert.equal(matches('Gyártás – Befejezés','gyartas'),true);
  assert.equal(matches('37\u00a0400 db','37400'),true);
  assert.equal(matches('37\u00a0400 db','37 400'),true);
  assert.equal(matches('Ferrofluid 16669','fluid'),true);
  assert.equal(matches('Ferrofluid','Ferrogel'),false);
});
