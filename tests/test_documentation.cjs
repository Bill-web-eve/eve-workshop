'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const manual=require('../static/documentation.js');
test('bundled guides expose complete searchable chapters in both languages',()=>{
  for(const [lang,name,topics] of [
    ['hu','Hasznalat.md',['Gyártásütemező','Bányászkristályok','Accountok, Omega és MCT','Kitermelési naptár','Jita-árak','Gyakori helyzetek']],
    ['en','UserGuide.en.md',['Production scheduler','Mining crystals','Accounts, Omega and MCT','Extraction calendar','Jita prices','Troubleshooting']]
  ]){
    const parsed=manual.parse(fs.readFileSync(path.join(__dirname,'..',name),'utf8'));
    assert(parsed.sections.length>=25);assert.equal(new Set(parsed.sections.map(s=>s.id)).size,parsed.sections.length);
    for(const topic of topics)assert(parsed.sections.some(s=>s.title.includes(topic)),lang+' '+topic);
    assert(parsed.sections.some(s=>manual.matches(s,'minimum 12')));
    assert(parsed.sections.every(s=>manual.matches(s,'')));
    assert(!parsed.sections.some(s=>manual.matches(s,'qwerty-no-such-feature')));
    assert(!parsed.sections.map(s=>s.html).join('').includes('<script'));
  }
});
test('Markdown renders nested instructions, formatting and bonus tables',()=>{
  const parsed=manual.parse('# Guide\n\n## Setup\n\n1. **Enable** scopes.\n   - `scope.one`\n   - scope.two\n\n2. Save.\n\n| Activity | Value |\n|---|---:|\n| Reaction | 12 |');
  const html=parsed.sections[0].html;
  assert.match(html,/<ol start="1"><li><strong>Enable<\/strong>/);assert.match(html,/<ul><li><code>scope.one<\/code>/);
  assert.match(html,/<\/ul><\/li><li>Save\.<\/li><\/ol>/);assert.match(html,/<th scope="col">Activity<\/th>/);assert.match(html,/<td>Reaction<\/td>/);
});
test('raw HTML and executable Markdown URLs cannot become active content',()=>{
  const html=manual.parse('# Guide\n## Safety\n<script>alert(1)</script>\n\n[x](javascript:alert(1)) [safe](https://example.com/?q=\"x\")\n\n`<img onerror=x>`').sections[0].html;
  assert(!/<script|<img|href="javascript:|onerror="/.test(html));assert.match(html,/&lt;script&gt;/);assert.match(html,/href="https:\/\/example.com\/\?q=&quot;x&quot;"/);assert.match(html,/rel="noopener noreferrer"/);
});
test('search ignores case, accents and extra whitespace and checks every word',()=>{
  const section=manual.parse('# Guide\n## Ütemező\nBányászkristály és gyártás.').sections[0];
  assert(manual.matches(section,'  UTEMEZO  gyartas '));assert(manual.matches(section,'banyaszkristaly'));assert(!manual.matches(section,'gyartas nincs'));
});
