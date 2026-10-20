'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),layout=require('../static/intel-map.js').layout;
const root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function fixture(mode=null){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765'+(mode?'/?intel_window='+mode:''),runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[];
 const prefs={enabled:true,folder:'/test/logs',channels:['Test Intel'],character_ids:null,manual_locations:{'1':300001},jumps:5,ttl_minutes:20,cooldown_seconds:20,region_ids:[],allow_local_alerts:false,sound:false};
 const position={id:1,name:'Own Pilot',system_id:300001,system_name:'J5A-IX',source:'manual',alertable:true};
 const intel={preferences:prefs,manual_system_names:{'1':'J5A-IX'},status:{checked:1800000000,files:1,done:1},characters:[position],center:300001,universe_build:1,regions:[[10,'Test Region']],nodes:[{id:300001,name:'J5A-IX',x:0,y:0,state:'contact',characters:['Own Pilot'],pilots:['Reported Pilot'],distance:0,in_range:true,contacts:[{timestamp:1800000000,pilots:[{id:359618261,name:'Reported Pilot'}],ships:[{name:'Buzzard',type_id:11192}]}]}],edges:[],alerts:[],reports:[{id:'report',timestamp:1800000000,channel:'Test Intel',systems:[300001],system_names:['J5A-IX'],pilots:[{name:'Reported Pilot',verified:false}],state:'contact',reporter:'Reporter',message:'J5A-IX Reported Pilot <script>fake</script>',historical:true}]};
 const state={csrf:'test',version:'1.0.0',characters:[{id:1,name:'Own Pilot'}],corporations:[],production_characters:[],plans:[],jobs:[],settings:{source:'manual'},task:{running:false},sde:{buildNumber:1},recipe_count:1};
 const notifications={items:[],counts:{data:0},task:{running:false},corporations:[],moons:[],preferences:{os_enabled:false,categories:{intel:true}}};
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 w.fetch=async (url,opts)=>{calls.push(url);const value=url==='/api/state'?state:url==='/api/notifications'?notifications:url==='/api/intel/alerts'?{enabled:true,items:intel.alerts}:url==='/api/intel/preferences'?Object.assign(prefs,JSON.parse(opts.body)):url.startsWith('/api/intel?')?intel:url.startsWith('/api/intel/channels?')?{channels:['Test Intel','Other Intel']}:url.startsWith('/api/intel/systems?')?[{id:300002,name:'L-A5XP',region:'Test Region'}]:url==='/api/intel/claim'?{items:intel.alerts}:null;if(value===null)throw Error('Unexpected '+url);return {ok:true,json:async()=>value};};
 for(const tag of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,tag.getAttribute('src')),'utf8'));
 await tick();await tick();run('error("Old production error");navigate("intel")');await tick();await tick();return {w,d,run,calls,intel,notifications};
}
test('map layout is deterministic, finite, bounded and retains input data',()=>{
 const nodes=Array.from({length:150},(_,id)=>({id,x:id%15,y:Math.floor(id/15),name:'System '+id})),original=JSON.stringify(nodes),rows=layout(nodes);
 assert.deepEqual(layout(nodes),rows);assert.equal(JSON.stringify(nodes),original);assert.equal(new Set(rows.map(n=>n.id)).size,150);assert(rows.every(n=>Number.isFinite(n.lx)&&n.lx>=0&&n.lx<=1200&&n.ly>=0&&n.ly<=720));
});
test('intel has a separate view, map, original source and safe English labels',async t=>{
 const {w,d,run}=await fixture();t.after(()=>w.close());assert.equal(d.querySelector('#global-error').hidden,true);assert.equal(d.querySelector('.plan-selector').hidden,true);assert.equal(d.querySelector('#page-title').textContent,'Intel map');assert.equal(d.querySelectorAll('.intel-node').length,1);assert.equal(d.querySelector('#view-content script'),null);
 assert(d.querySelector('#view-content').textContent.includes('Reported Pilot'));assert(d.querySelector('#view-content').textContent.includes('Reporter'));assert(d.querySelector('#view-content').textContent.includes('Inferred from text'));
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#view-content').textContent),d.querySelector('#view-content').textContent);
 d.querySelector('[data-intel-system]').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',bubbles:true}));assert.equal(run('intelSelected'),300001);
 d.querySelector('#intel-zoom-in').click();assert.equal(run('intelZoom'),1.25);assert(d.querySelector('#intel-map-transform').getAttribute('transform').includes('1.25'));
 w.EveI18n.setLanguage('hu');await tick();assert.equal(d.querySelector('#page-title').textContent,'Inteltérkép');
});
test('intel settings preserve dirty inputs and support selectable systems and channels',async t=>{
 const {w,d,run,calls}=await fixture();t.after(()=>w.close());run('openSettingsTab("intel")');await tick();
 assert.equal(d.querySelector('#page-title').textContent,'Intel settings');assert(!/[áéíóöőúüű]/i.test(d.querySelector('#settings-content').textContent));
 const form=d.querySelector('#intel-settings');assert.equal(form.querySelector('[data-intel-manual]').value,'J5A-IX');form.elements.jumps.value='3';form.dispatchEvent(new w.Event('input',{bubbles:true}));await run('refreshIntel()');assert.equal(d.querySelector('#intel-settings'),form);assert.equal(form.elements.jumps.value,'3');
 d.querySelector('#intel-discover').click();await tick();d.querySelector('[data-intel-add="Other Intel"]').click();assert(form.elements.channels.value.includes('Other Intel'));
 form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();assert(calls.includes('/api/intel/preferences'));assert.equal(run('intelData.preferences.jumps'),3);assert.equal(run('Object.keys(dirty).length'),0);
});
test('nearby intel delivery uses durable claim, character and distance; notification opens intel',async t=>{
 const {w,d,run,intel,notifications:n,calls}=await fixture();t.after(()=>w.close());
 intel.alerts=[{id:'intel:1:300001:x',category:'intel',kind:'intel_near',subject:'J5A-IX · Reported Pilot',character_name:'Own Pilot',jumps:2,corporation_id:null,when:1800000000,receipt:'receipt',notification_id:'id',sound:true}];n.preferences.os_enabled=true;
 const sent=[];w.EveDesktop.active=true;w.EveDesktop.notificationStatus=async()=>({status:'authorized'});w.EveDesktop.notify=async body=>sent.push(body);
 const old=w.fetch;w.fetch=async(url,opts)=>url==='/api/notifications/sent'?{ok:true,json:async()=>({ok:true})}:old(url,opts);
 await run('pollIntelAlerts()');assert.equal(sent.length,1);assert(sent[0].body.includes('Own Pilot · 2 jump'));assert(sent[0].sound);assert(calls.includes('/api/intel/claim'));assert.equal(d.querySelector('#intel-count').textContent,'1');
 run('navigate("jobs");openNotificationCenter("personal","intel")');await tick();assert.equal(run('view'),'intel');
});

test('background status checks keep the map DOM stable when no intel changed',async t=>{
 const {w,d,run,intel}=await fixture();t.after(()=>w.close());const svg=d.querySelector('#intel-map svg'),table=d.querySelector('.intel-feed');
 intel.status.checked+=1;await run('refreshIntel(true)');await tick();assert.equal(d.querySelector('#intel-map svg'),svg);assert.equal(d.querySelector('.intel-feed'),table);
 intel.reports[0].state='clear';await run('refreshIntel(true)');await tick();assert.notEqual(d.querySelector('#intel-map svg'),svg);
});

test('activity cards display exact zKillboard links, ship icons and range highlighting',async t=>{
 const {w,d}=await fixture();t.after(()=>w.close());
 const card=d.querySelector('.intel-activity-card');assert(card);assert.equal(card.querySelector('a').href,'https://zkillboard.com/character/359618261/');assert.equal(card.querySelector('img').src,'https://images.evetech.net/types/11192/icon?size=32');
 assert(d.querySelector('.intel-range-halo'));assert.equal(d.querySelector('#intel-radius'),null);assert(d.querySelector('[data-intel-window=map]'));assert(d.querySelector('[data-intel-window=chat]'));
});
test('detached chat aggregates selected channels, keeps source text safe and does not send OS alerts',async t=>{
 const {w,d,run,intel,calls}=await fixture('chat');t.after(()=>w.close());
 assert.equal(d.documentElement.dataset.intelWindow,'chat');assert.equal(d.querySelector('#page-title').textContent,'Combined intel chat');assert(!d.querySelector('#intel-chat-feed script'));assert.equal(d.querySelectorAll('.intel-chat-line').length,1);
 const feed=d.querySelector('#intel-chat-feed'),first=feed.firstElementChild;await run('refreshIntel(true)');assert.equal(feed.firstElementChild,first);
 intel.reports.push({...intel.reports[0],id:'second',channel:'Second Intel',timestamp:1800000001,pilots:[{id:359618261,name:'Steve Hluskan'}],message:'J5A-IX Steve Hluskan',ships:[{type_id:11192,name:'Buzzard'}]});await run('refreshIntel(true)');await tick();
 assert.equal(d.querySelectorAll('.intel-chat-line').length,2);assert(feed.textContent.includes('Second Intel'));assert(feed.querySelector('a[href="https://zkillboard.com/character/359618261/"]'));assert.equal(d.querySelectorAll('#intel-chat-feed input, #intel-chat-feed textarea').length,0);assert(!calls.includes('/api/notifications/claim'));
 d.querySelector('#intel-chat-auto').checked=false;d.querySelector('#intel-chat-auto').dispatchEvent(new w.Event('change'));await run('refreshIntel(true)');assert.equal(run('intelChatAuto'),false);
});
test('contact callouts stay within the viewport and avoid identical placement',()=>{
 const nodes=[{id:1,lx:5,ly:5,contacts:[{pilots:[{name:'One'}],ships:[]}]},{id:2,lx:1195,ly:710,contacts:[{pilots:[{name:'Two'}],ships:[]}]}];
 const cards=require('../static/intel-map.js').callouts(nodes);assert.equal(cards.length,2);assert(cards.every(c=>c.x>=0&&c.y>=0&&c.x+c.width<=1200&&c.y+c.height<=720));
});
test('detached map window buttons open only their requested window without bubbling into the root',async t=>{
 const {w,d,run}=await fixture('map');t.after(()=>w.close());const opened=[];
 w.EveDesktop.openIntelWindow=async(kind,options)=>opened.push({kind,options});
 d.querySelector('button[data-intel-window=chat]').click();await tick();
 assert.deepEqual(opened.map(call=>call.kind),['chat']);
 assert.equal(d.documentElement.onclick,null);
 d.querySelector('#intel-zoom-in').click();await tick();
 assert.equal(opened.length,1);assert.equal(run('intelZoom'),1.25);
});
