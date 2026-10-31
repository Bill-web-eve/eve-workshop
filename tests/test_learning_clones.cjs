'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
function setup(){
 const dom=new JSDOM('<main></main>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[],sent=[],opened=[];
 w.$=s=>d.querySelector(s);w.$$=s=>[...d.querySelectorAll(s)];w.esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');w.verbatim=s=>'<span data-i18n-skip>'+w.esc(s)+'</span>';w.fmt=String;
 w.table=(heads,rows)=>'<table><thead><tr>'+heads.map(h=>'<th>'+h+'</th>').join('')+'</tr></thead><tbody>'+rows.join('')+'</tbody></table>';
 w.panel=(a,b,c)=>'<section><h2>'+a+'</h2>'+c+'</section>';w.EveLocations={markup:id=>'<span data-place="'+id+'">Station</span>'};
 w.EveDesktop={active:true,notificationStatus:async()=>({status:'authorized'}),notify:async data=>sent.push(data)};
 w.openEveAuthorization=async data=>opened.push(data);w.error=()=>{};w.render=()=>{};
 w.api=async(url,body)=>{calls.push({url,body});return url==='/api/auth/start'?{url:'https://login.eveonline.com/authorize'}:{items:[]};};
 for(const file of ['i18n-en.js','i18n.js','notifications.js','learning-clones.js'])run(fs.readFileSync(__dirname+'/../static/'+file,'utf8'));
 run(`let view='settings',settingsTab='notifications',dirty={};`);w.EveI18n.setLanguage('en');
 const data={enabled:true,gate:'offline',online_fresh:true,online_characters:[],status:{running:false},scopes:['esi-clones.read_clones.v1'],characters:[{id:11,name:'Pilot <safe>',authorized:true,status:'better',skill_name:'Gunnery',active:{score:4.5},best:{score:7.5,name:'Training clone',jump_clone_id:101,location_id:60003760}}]};
 d.querySelector('main').innerHTML=w.learningCloneSettingsPanel(data);run('notificationData={preferences:{os_enabled:true,categories:{learning_clones:true}}};');w.bindLearningClones();w.EveI18n.translate(d.body);
 return {dom,w,d,run,data,calls,sent,opened};
}
test('settings describe the all-offline gate and show the weighted owned clone and its location in English',t=>{
 const {dom,d}=setup();t.after(()=>dom.window.close());assert(d.body.textContent.includes('All connected characters are offline.'));
 assert(d.body.textContent.includes('Gunnery'));assert(d.body.textContent.includes('4.5 → 7.5'));assert(d.body.textContent.includes('Training clone'));
 assert(d.querySelector('[data-place="60003760"]'));assert.equal(d.querySelector('safe'),null);assert(!/[áéőű]/i.test(d.body.textContent));
});
test('authorization preserves character identity and returns to notification settings',async t=>{
 const {dom,w,calls,opened}=setup();t.after(()=>dom.window.close());await w.$('[data-learning-authorize]').onclick();
 assert.equal(calls[0].url,'/api/auth/start');assert.equal(calls[0].body.character_id,11);assert.equal(calls[0].body.feature,'learning_clones');assert.equal(opened.length,1);
 assert.equal(w.sessionStorage.getItem('eve-muhely-auth-return'),'settings:notifications');
});
test('OS notifications are separate for every affected character, audible, and category-specific',async t=>{
 const {dom,w,calls,sent}=setup();t.after(()=>dom.window.close());
 const item={id:'learning-clone:11',category:'learning_clones',kind:'learning_clone_better',subject:'Pilot',character_id:11,corporation_id:null,skill_name:'Gunnery',best_clone_name:'Training clone',best_clone_id:101,active_bonus:4.5,best_bonus:7.5,notification_id:'a',receipt:'r',sound:true,when:null};
 w.api=async(url,body)=>{calls.push({url,body});return {items:url.endsWith('/claim')?[item,{...item,id:'learning-clone:22',character_id:22,subject:'Other',notification_id:'b',receipt:'s'}]:[]};};
 await w.pollLearningCloneAlerts();assert.equal(sent.length,2);assert(sent.every(n=>n.sound&&n.category==='learning_clones'));
 assert(sent[0].body.includes('Gunnery · Training clone · 4.5 → 7.5'));assert(sent[1].body.includes('Other'));
 assert.equal(calls.filter(c=>c.url==='/api/notifications/sent').length,2);
});
test('disabling the category suppresses OS claims without changing other notification preferences',async t=>{
 const {dom,w,run,calls}=setup();t.after(()=>dom.window.close());run('notificationData.preferences.categories.learning_clones=false;');
 await w.pollLearningCloneAlerts();assert.equal(calls.length,0);
});
test('manual checks preserve unsaved settings while displaying real progress',async t=>{
 const {dom,w,run,data,d}=setup();t.after(()=>dom.window.close());run('dirty.other=true;');
 const old=d.querySelector('[data-learning-authorize]');w.api=async()=>({...data,status:{running:true,phase:'Online állapotok ellenőrzése',done:1,total:4}});
 await w.refreshLearningClones(true);assert.equal(d.querySelector('[data-learning-authorize]'),old);
 assert(d.querySelector('[data-learning-status]').textContent.includes('Checking online status · 1 / 4'));assert(w.$('#learning-clone-refresh').disabled);
});
