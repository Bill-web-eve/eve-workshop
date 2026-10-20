'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static');
function setup(){
 const dom=new JSDOM('<main></main>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[],opened=[],errors=[];
 w.state={characters:[{id:11,name:'Alice'},{id:22,name:'Bob'}],task:{running:false}};
 w.esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');w.verbatim=w.esc;
 w.panel=(title,subtitle,content)=>'<h2>'+title+'</h2><p>'+subtitle+'</p>'+content;
 w.table=(heads,rows)=>'<table><thead><tr>'+heads.map(s=>'<th>'+s+'</th>').join('')+'</tr></thead><tbody>'+rows.join('')+'</tbody></table>';
 w.$=s=>w.document.querySelector(s);w.$$=s=>Array.from(w.document.querySelectorAll(s));w.error=s=>errors.push(s);
 w.api=async(url,body)=>{calls.push({url,body});return {url:'https://login.eveonline.com/authorize'};};
 w.openEveAuthorization=async auth=>opened.push(auth);
 run(fs.readFileSync(path.join(root,'settings.js'),'utf8'));
 run('settingsAccessData={skills:{characters:[]},pi:{characters:[]},corporations:{characters:[]},mining:{characters:[]}};document.querySelector("main").innerHTML=generalAccessPanel();bindGeneralAccess();');
 return {w,run,calls,opened,errors};
}
test('each character has one all-access action, sends one character-bound request and returns to settings',async t=>{
 const {w,run,calls,opened}=setup();t.after(()=>w.close());
 const buttons=w.document.querySelectorAll('[data-access-feature=all]');assert.equal(buttons.length,2);
 for(const button of buttons)assert.equal(button.textContent,'Minden hozzáférés engedélyezése');
 assert.deepEqual(Array.from(w.document.querySelectorAll('tbody tr td:first-child')).map(c=>c.textContent),['Alice','Bob']);
 await buttons[1].onclick();assert.equal(calls.length,1);assert.equal(calls[0].url,'/api/auth/start');assert.equal(calls[0].body.character_id,22);assert.equal(calls[0].body.feature,'all');assert.equal(opened.length,1);
 assert.equal(w.sessionStorage.getItem('eve-muhely-auth-return'),'settings:access');
 assert(!buttons[0].disabled);assert(buttons[1].disabled);
 assert.equal(w.document.querySelectorAll('[data-access-feature=skills]').length,2);
 run(fs.readFileSync(path.join(root,'i18n-en.js'),'utf8'));
 assert.equal(w.EveEnglish[buttons[0].textContent],'Authorize all access');
});
test('authorization failure is visible and allows retry',async t=>{
 const {w,calls,opened,errors}=setup();t.after(()=>w.close());
 w.api=async()=>{throw Error('Authorization unavailable');};
 const button=w.document.querySelector('[data-access-feature=all]');await button.onclick();
 assert.equal(button.disabled,false);assert.equal(errors.at(-1),'Authorization unavailable');assert.equal(opened.length,0);
});
