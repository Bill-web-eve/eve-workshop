'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
function setup(){
 const dom=new JSDOM('<div id="plan-status"></div><div id="actions"></div><main></main>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[],sent=[];
 w.$=s=>w.document.querySelector(s);w.$$=s=>[...w.document.querySelectorAll(s)];
 w.esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');w.verbatim=s=>'<span data-i18n-skip>'+w.esc(s)+'</span>';w.itemName=s=>'<button class="copy-item-name" data-copy-item="'+w.esc(s)+'">'+w.esc(s)+'</button>';
 w.table=(heads,rows,key)=>w.EveTables.markup(heads,rows,'',key);w.panel=(a,b,c)=>'<section><h2>'+(typeof a==='object'?w.verbatim(a.name)+a.suffix:a)+'</h2><p>'+b+'</p>'+c+'</section>';
 w.empty=(a,b='')=>'<h2>'+w.esc(a)+'</h2><p>'+w.esc(b)+'</p>';w.settingsShortcut=s=>'<p>'+s+'</p>';w.fmt=n=>Number(n).toLocaleString('en-US');w.actions=s=>w.$('#actions').innerHTML=s;w.setHead=()=>{};
 w.EveDesktop={active:true,notify:async data=>sent.push(data),notificationStatus:async()=>({status:'authorized'})};
 w.state={task:{running:false}};w.render=()=>w.renderContracts(w.$('main'));w.startTask=url=>calls.push({url});w.navigate=next=>{run('view='+JSON.stringify(next));w.render();};
 const row={contract_id:101,owner_id:11,title:'A <safe> contract',type:'item_exchange',status:'outstanding',issuer_id:77,issuer_name:'Issuer',assignee_id:11,assignee_name:'Pilot <safe>',acceptor_id:0,acceptor_name:'–',price:2000,reward:null,owners:[{id:11,name:'Pilot <safe>'}],date_issued:'2026-10-24T10:00:00Z',date_expired:'2026-11-01T10:00:00Z',start_location_id:6001,start_location_name:'Test Station'};
 w.api=async(url,body)=>{calls.push({url,body});if(url.includes('/details'))return {contract:row,history:[{at:1700000000,status:'outstanding',contract:row}],items:[{name:'Tritanium',type_id:34,quantity:100,is_included:true,is_singleton:false}],error:null};return {rows:[row],owners:[{id:11,name:'Pilot <safe>'},{id:22,name:'Other'}],sources:[],characters:[]};};
 for(const name of ['i18n-en.js','i18n.js','tables.js','costs.js','contracts.js','notifications.js'])run(fs.readFileSync(path.join(root,name),'utf8'));
 run("let view='contracts',corporationId=999;");
 return {w,run,calls,sent,row};
}
test('contract tabs are independent of production owner; shared table controls and escaping work',async t=>{
 const {w,run,calls}=setup();t.after(()=>w.close());await w.loadContracts();await tick();
 assert.equal(w.$('safe'),null);assert.match(w.$('main').textContent,/A <safe> contract/);assert(w.$('#plan-status').hidden);
 assert.equal(w.$('.table-filters').hidden,true);assert.deepEqual([...w.$('[data-table-page-size]').options].map(o=>o.value),['25','50','100']);
 assert.equal(w.$('#contract-owner').options.length,3);assert(w.$('select[data-table-filter="3"]'));
 w.$('[data-contract-scope="corporation"]').click();await tick();assert.match(calls.at(-1).url,/scope=corporation/);assert.equal(run('corporationId'),999);assert.equal(w.$('#contract-owner').value,'');
 w.$('#contract-owner').value='22';w.$('#contract-start').value='2026-10-01';w.$('#contract-end').value='2026-10-25';w.$('#contract-filter').onsubmit({preventDefault(){}});await tick();
 const query=new URL(calls.at(-1).url,'http://local').searchParams;assert.equal(query.get('owner'),'22');assert.equal(query.get('start'),'2026-10-01');assert.equal(query.get('end'),'2026-10-25');
 w.$('#contract-sync').click();assert.equal(calls.at(-1).url,'/api/contracts/sync');
});
test('English contract lists and details translate without changing names; local history and copyable items appear',async t=>{
 const {w}=setup();t.after(()=>w.close());w.EveI18n.setLanguage('en');await w.loadContracts();await tick();
 assert.match(w.$('main').textContent,/Contracts and history/);assert.match(w.$('main').textContent,/Awaiting acceptance/);assert.match(w.$('main').textContent,/Pilot <safe>/);assert.equal(w.$('safe'),null);
 w.$('[data-contract-id]').click();await tick();await tick();
 assert.equal(w.$('[data-copy-item]').dataset.copyItem,'Tritanium');assert.match(w.$('#contract-detail').textContent,/Offered/);assert.match(w.$('#contract-detail').textContent,/Observed locally/);
 w.EveI18n.setLanguage('hu');await tick();assert.match(w.$('#contract-detail').textContent,/Felajánlott/);assert.match(w.$('main').textContent,/Szerződések és előzmények/);
});
test('permission failures and network errors remain visible and cached reload retries',async t=>{
 const {w}=setup();t.after(()=>w.close());w.api=async()=>{throw Error('Server unavailable');};await w.loadContracts();assert.match(w.$('main').textContent,/Server unavailable/);
 w.api=async()=>({rows:[],owners:[],characters:[],sources:[{name:'Corp',authorized:false,enabled:true}]});await w.loadContracts(true);assert.match(w.$('main').textContent,/Szerződésengedély szükséges/);assert.match(w.$('main').textContent,/Nincs ilyen szerződés/);
});
test('state invalidation during a list request retries rather than leaving an endless loading view',async t=>{
 const {w,run}=setup();t.after(()=>w.close());let finish,count=0;w.api=async()=>{count++;if(count===1)return new Promise(r=>finish=r);return {rows:[],owners:[],sources:[]};};
 const pending=w.loadContracts();run('contractRevision++;');finish({rows:[],owners:[],sources:[]});await pending;await tick();assert.equal(count,2);assert.match(w.$('main').textContent,/Nincs ilyen szerződés/);
});
test('contract alerts use separate personal/corporation OS notifications with IDs and sound',async t=>{
 const {w,run,sent,calls}=setup();t.after(()=>w.close());const items=[{id:'a',notification_id:'a',receipt:'ra',category:'contracts',kind:'contract_new',subject:'Hull',contract_id:101,owner_id:11,owner_name:'Pilot',contract_scope:'personal',corporation_id:null,sound:true},{id:'b',notification_id:'b',receipt:'rb',category:'contracts',kind:'contract_accepted',subject:'Corp shipment',contract_id:102,owner_id:99,owner_name:'Corp',contract_scope:'corporation',corporation_id:99,scope_name:'Corp',sound:true}];
 w.api=async(url,body)=>{calls.push({url,body});return {items:url.endsWith('/claim')?items:[]};};run('notificationData={preferences:{os_enabled:true,categories:{contracts:true}}};');
 await w.deliverNotifications();assert.equal(sent.length,2);assert.equal(sent[0].scope,'personal');assert.equal(sent[1].scope,'99');assert.match(sent[0].body,/#101 · Pilot/);assert.match(sent[1].body,/#102 · Corp/);assert(sent.every(n=>n.category==='contracts'&&n.sound));assert.equal(calls.filter(c=>c.url==='/api/notifications/sent').length,2);
});
