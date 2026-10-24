'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),layout=require('../static/intel-map.js').layout;
const root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function fixture(mode=null){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765'+(mode?'/?intel_window='+mode:''),runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[];
 const prefs={enabled:true,killfeed_enabled:true,kill_region_ids:[],folder:'/test/logs',channels:['Test Intel'],character_ids:null,manual_locations:{'1':300001},jumps:5,ttl_minutes:20,cooldown_seconds:20,region_ids:[],allow_local_alerts:false,sound:false};
 const position={id:1,name:'Own Pilot',system_id:300001,system_name:'J5A-IX',source:'manual',alertable:true};
 const intel={preferences:prefs,manual_system_names:{'1':'J5A-IX'},status:{checked:1800000000,files:1,done:1},characters:[position],center:300001,universe_build:1,regions:[[10,'Test Region']],nodes:[{id:300001,name:'J5A-IX',x:0,y:0,state:'contact',characters:['Own Pilot'],pilots:['Reported Pilot'],distance:0,in_range:true,contacts:[{timestamp:1800000000,pilots:[{id:359618261,name:'Reported Pilot'}],ships:[{name:'Buzzard',type_id:11192}]}]}],edges:[],alerts:[],reports:[{id:'report',timestamp:1800000000,channel:'Test Intel',systems:[300001],system_names:['J5A-IX'],pilots:[{name:'Reported Pilot',verified:false}],state:'contact',reporter:'Reporter',message:'J5A-IX Reported Pilot <script>fake</script>',historical:true}]};
 const state={csrf:'test',version:'1.0.0',characters:[{id:1,name:'Own Pilot'}],corporations:[],production_characters:[],plans:[],jobs:[],settings:{source:'manual'},task:{running:false},sde:{buildNumber:1},recipe_count:1};
 const notifications={items:[],counts:{data:0},task:{running:false},corporations:[],moons:[],preferences:{os_enabled:false,categories:{intel:true,jobs:true,skills:true,pi:true,moons:true}}};
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;w.Date.now=()=>1800000000000;
 w.fetch=async (url,opts)=>{calls.push(url);const value=url.startsWith('/api/jobs')?{rows:[],sources:[]}:url==='/api/state'?state:url==='/api/notifications'?notifications:url==='/api/notifications/preferences'?(intel.notifications_enabled=JSON.parse(opts.body).categories.intel,Object.assign(notifications.preferences.categories,JSON.parse(opts.body).categories),notifications.preferences):url==='/api/intel/alerts'?{enabled:true,items:intel.alerts}:url==='/api/intel/preferences'?Object.assign(prefs,JSON.parse(opts.body)):url.startsWith('/api/intel?')?intel:url.startsWith('/api/intel/channels?')?{channels:['Test Intel','Other Intel']}:url.startsWith('/api/intel/systems?')?[{id:300002,name:'L-A5XP',region:'Test Region'}]:url==='/api/intel/claim'?{items:intel.alerts}:null;if(value===null)throw Error('Unexpected '+url);return {ok:true,json:async()=>value};};
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
 const sent=[];w.EveDesktop.active=true;w.EveDesktop.syncIntelOverlay=async()=>({});w.EveDesktop.notificationStatus=async()=>({status:'authorized'});w.EveDesktop.notify=async body=>sent.push(body);
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
test('detached chat window buttons open only their requested window without bubbling into the root',async t=>{
 const {w,d}=await fixture('chat');t.after(()=>w.close());const opened=[];
 w.EveDesktop.openIntelWindow=async(kind,options)=>opened.push({kind,options});
 d.querySelector('button[data-intel-window=map]').click();await tick();
 assert.deepEqual(opened.map(call=>call.kind),['map']);
 assert.equal(d.documentElement.onclick,null);
 d.querySelector('#intel-chat-auto').click();await tick();
 assert.equal(opened.length,1);
});

test('detached map contains only the live system map and its navigation controls',async t=>{
 const {w,d,run,intel}=await fixture('map');t.after(()=>w.close());
 const content=d.querySelector('#view-content');assert.equal(content.children.length,1);assert(content.firstElementChild.classList.contains('panel'));assert.equal(content.querySelector('.banner'),null);
 for(const selector of ['#intel-character','#intel-region','#intel-history','#intel-refresh','#intel-resolve','button[data-intel-window]','.intel-toolbar'])assert.equal(d.querySelector(selector),null,selector);
 assert(d.querySelector('#intel-map svg'));assert(d.querySelector('.intel-legend'));assert.equal(d.querySelector('#view-actions').textContent,'');
 d.querySelector('#intel-zoom-in').click();assert.equal(run('intelZoom'),1.25);
 d.querySelector('#intel-fit').click();assert.equal(run('intelZoom'),1);
 intel.characters[0].alertable=false;intel.reference=intel.characters[0];await run('refreshIntel(true)');
 assert(content.querySelector('.intel-map-provenance'));assert(content.querySelector('.intel-range-stale'));
 intel.nodes[0].state='clear';await run('refreshIntel(true)');assert(d.querySelector('.intel-node.clear'));
});

test('report cards expire at three minutes without a refresh, preserve reports and accept new intel',async t=>{
 const {w,d,run,intel}=await fixture('map');t.after(()=>w.close());
 const origin=1800000000000,timers=[];let now=origin;w.Date.now=()=>now;
 w.setTimeout=(fn,delay)=>{timers.push({fn,delay});return timers.length;};w.clearTimeout=()=>{};
 intel.nodes[0].contacts.push({...intel.nodes[0].contacts[0],timestamp:1800000010,pilots:[{name:'Next report'}]});
 run('drawIntelMap()');assert.equal(timers.at(-1).delay,180000);assert(!d.querySelector('.intel-card-body').textContent.includes('Next report'));
 now=origin+179999;run('drawIntelMap()');assert(d.querySelector('.intel-activity-card'));assert.equal(timers.at(-1).delay,1);
 now=origin+180000;timers.at(-1).fn();assert(d.querySelector('.intel-activity-card'));assert(!d.querySelector('.intel-card-body').textContent.includes('Reported Pilot'));assert(d.querySelector('.intel-card-body').textContent.includes('Next report'));assert.equal(timers.at(-1).delay,10000);
 now=origin+190000;timers.at(-1).fn();assert.equal(d.querySelector('.intel-activity-card'),null);assert.equal(intel.reports.length,1);assert(d.querySelector('.intel-node.contact'));
 intel.nodes[0].contacts.push({...intel.nodes[0].contacts[0],timestamp:now/1000});run('drawIntelMap()');assert(d.querySelector('.intel-activity-card'));
});

test('intel overlay receives fresh report details independently of OS notification permission',async t=>{
 const {w,run,intel,notifications,calls}=await fixture();t.after(()=>w.close());const sent=[];
 w.EveDesktop.active=true;w.EveDesktop.syncIntelOverlay=async data=>sent.push(data);notifications.preferences.os_enabled=false;
 intel.alerts=[{system_id:300001,system_name:'J5A-IX',character_name:'Own Pilot',jumps:2,overlay_reports:[{id:'new-report',when:1800000000,pilots:['Reported Pilot'],ships:['Buzzard']}]}];
 const original=w.fetch;w.fetch=async(url,options)=>url==='/api/notifications/preferences'?(intel.notifications_enabled=JSON.parse(opts.body).categories.intel,Object.assign(notifications.preferences.categories,JSON.parse(opts.body).categories),notifications.preferences):url==='/api/intel/alerts'?{ok:true,json:async()=>({enabled:true,overlay:{enabled:true,seconds:75},items:intel.alerts})}:original(url,options);
 await run('pollIntelAlerts()');assert.equal(sent.length,1);assert.equal(sent[0].seconds,75);assert.equal(sent[0].items[0].system,'J5A-IX');assert.equal(sent[0].items[0].pilots,'Reported Pilot');assert.equal(sent[0].items[0].ships,'Buzzard');assert(!calls.includes('/api/intel/claim'));
});
for(const platform of ['mac','windows'])test(platform+' overlay settings expose monitor selection, exact seconds and explicit move/lock controls',async t=>{
 const {w,d,run}=await fixture();t.after(()=>w.close());w.EveDesktop.active=true;w.EveDesktop.platform=platform;
 w.EveDesktop.intelOverlayStatus=async()=>({screens:[{id:'1',name:'Test monitor',width:1920,height:1080,placement:{x:20,y:40,width:330}}],screen_id:'1',placement:{x:20,y:40,width:330},editing:false});
 run('openSettingsTab("intel")');await tick();await tick();const form=d.querySelector('#intel-overlay-form');assert(form);assert.equal(form.elements.overlay_seconds.value,'60');assert.equal(form.elements.screen_id.value,'1');assert(d.querySelector('#intel-overlay-move'));assert(d.querySelector('#intel-overlay-lock'));assert(!/[áéíóöőúüű]/i.test(d.querySelector('#intel-overlay-settings').textContent));
});

test('intel notification toggle changes only intel and keeps the map and chat enabled',async t=>{
 const {w,d,calls,intel,notifications}=await fixture();t.after(()=>w.close());
 const button=d.querySelector('#intel-notifications');assert.equal(button.getAttribute('aria-pressed'),'true');
 button.click();await tick();await tick();await tick();
 assert.equal(d.querySelector('#intel-notifications').getAttribute('aria-pressed'),'false');
 assert.equal(d.querySelector('#intel-notifications').textContent,'Intel notifications: off');
 assert.equal(intel.preferences.enabled,true);assert.equal(intel.preferences.channels[0],'Test Intel');
 assert.equal(notifications.preferences.categories.intel,false);
 for(const key of ['jobs','skills','pi','moons'])assert.equal(notifications.preferences.categories[key],true);
 assert(d.querySelector('#intel-map'));assert(calls.includes('/api/notifications/preferences'));
 d.querySelector('#intel-notifications').click();await tick();await tick();await tick();
 assert.equal(notifications.preferences.categories.intel,true);
});

for(const platform of ['mac','windows'])test(platform+' intel notification switch clears a visible overlay and blocks stale enabled payloads',async t=>{
 const {w,d,run,intel}=await fixture();t.after(()=>w.close());const sent=[];
 w.EveDesktop.active=true;w.EveDesktop.platform=platform;w.EveDesktop.syncIntelOverlay=async data=>sent.push(data);
 intel.alerts=[{system_id:300001,system_name:'J5A-IX',character_name:'Own Pilot',jumps:2,overlay_reports:[{id:'visible',when:1800000000,pilots:['Reported Pilot'],ships:['Buzzard']}]}];
 w.overlayPayload={enabled:true,notifications_enabled:true,overlay:{enabled:true,seconds:75},items:intel.alerts};
 await run('syncIntelOverlay(overlayPayload)');assert.equal(sent.at(-1).enabled,true);assert.equal(sent.at(-1).items.length,1);
 d.querySelector('#intel-notifications').click();await tick();await tick();await tick();
 assert.equal(d.querySelector('#intel-notifications').getAttribute('aria-pressed'),'false');
 assert.equal(sent.at(-1).enabled,false);assert.equal(sent.at(-1).items.length,0);
 await run('syncIntelOverlay(overlayPayload)');assert.equal(sent.at(-1).enabled,false);assert.equal(sent.at(-1).items.length,0);
 assert.equal(intel.preferences.enabled,true);assert(d.querySelector('#intel-map'));
});
test('late intel polling cannot reopen the overlay after notification disable',async t=>{
 const {w,run,intel,notifications}=await fixture();t.after(()=>w.close());const sent=[];
 w.EveDesktop.active=true;w.EveDesktop.syncIntelOverlay=async data=>sent.push(data);
 let release;const gate=new Promise(resolve=>{release=resolve;}),original=w.fetch;
 w.fetch=async(url,options)=>{if(url==='/api/intel/alerts'){await gate;return {ok:true,json:async()=>({enabled:true,notifications_enabled:true,overlay:{enabled:true,seconds:60},items:[]})};}return original(url,options);};
 const pending=run('pollIntelAlerts()');await tick();
 await run('applyIntelNotificationPreferences({...notificationData.preferences,categories:{...notificationData.preferences.categories,intel:false}})');
 assert.equal(sent.at(-1).enabled,false);const cleared=sent.length;
 release();await pending;assert.equal(sent.length,cleared);assert.equal(notifications.preferences.categories.intel,false);
 assert.equal(intel.preferences.enabled,true);
});
test('server notification disable blocks overlays even before preferences reload',async t=>{
 const {w,run}=await fixture();t.after(()=>w.close());const sent=[];
 w.EveDesktop.syncIntelOverlay=async data=>sent.push(data);
 await run('syncIntelOverlay({enabled:true,notifications_enabled:false,overlay:{enabled:true,seconds:60},items:[]})');
 assert.equal(sent.at(-1).enabled,false);assert.equal(sent.at(-1).items.length,0);
});

function killGroup(id='kill:300001:1'){
 return {id,system_id:300001,system_name:'J5A-IX',region_id:10,region_name:'Test Region',received:1800000000,ready_at:1800000010,last_at:1799999990,count:2,cents:'300000',missing:0,
  ships:[{type_id:590,name:'Rifter',count:2}],kills:[{id:1,at:1799999980,ship_id:590,ship:'Rifter',cents:'100000'},{id:2,at:1799999990,ship_id:590,ship:'Rifter',cents:'200000'}]};
}
test('regional kills have one grouped callout and an independent map marker on clear systems',async t=>{
 const {w,d,run,intel}=await fixture();t.after(()=>w.close());const g=killGroup();
 intel.nodes[0].state='clear';intel.nodes[0].contacts=[];intel.nodes[0].pilots=[];intel.nodes[0].kill_groups=[g];intel.kill_groups=[g];intel.kill_regions=[10];intel.kill_feed={enabled:true,checked:1800000000};
 await run('refreshIntel(true)');await tick();
 assert(d.querySelector('.intel-node.clear.kill-activity'));assert(d.querySelector('.intel-kill-ring'));assert.equal(d.querySelectorAll('.intel-kill-summary').length,1);
 assert.match(d.querySelector('.intel-kill-summary').textContent,/2 kill/);assert(!d.querySelector('.intel-kill-summary').textContent.includes('ISK'));assert.match(d.querySelector('.intel-kill-summary').textContent,/2 × Rifter/);
 assert.equal(d.querySelectorAll('.intel-kills tbody tr:not(.table-empty-row)').length,1);
 assert(d.querySelector('.intel-kill-links a[href="https://zkillboard.com/kill/1/"] img'));assert(d.querySelector('.intel-kill-links a[href="https://zkillboard.com/kill/2/"] img'));
 assert(!/[áéíóöőúüű]/i.test(d.querySelector('#view-content').textContent),d.querySelector('#view-content').textContent);
 w.Date.now=()=>1800000180000;run('drawIntelMap()');assert.equal(d.querySelector('.intel-kill-summary'),null);assert(d.querySelector('.intel-node.kill-activity'));
});
test('detached kill map stays map-only and combines several bursts in the same system',async t=>{
 const {w,d,run,intel}=await fixture('map');t.after(()=>w.close());const a=killGroup(),b=killGroup('kill:300001:3');b.kills=[{...a.kills[0],id:3}];b.count=1;b.cents='100000';
 intel.nodes[0].contacts=[];intel.nodes[0].kill_groups=[a,b];await run('refreshIntel(true)');await tick();
 assert.equal(d.querySelector('#view-content').children.length,1);assert.equal(d.querySelectorAll('.intel-kill-summary').length,1);assert.match(d.querySelector('.intel-kill-summary').textContent,/3 kill/);assert(!d.querySelector('.intel-kill-summary').textContent.includes('ISK'));
 assert.equal(d.querySelector('.intel-kills'),null);
});
test('kill notifications are grouped, omit ISK and do not invent live pilots',async t=>{
 const {w,run,intel,notifications:n}=await fixture();t.after(()=>w.close());const sent=[],overlays=[];
 w.EveDesktop.active=true;w.EveDesktop.platform='mac';w.EveDesktop.syncIntelOverlay=async data=>overlays.push(data);w.EveDesktop.notificationStatus=async()=>({status:'authorized'});w.EveDesktop.notify=async data=>sent.push(data);n.preferences.os_enabled=true;
 intel.alerts=[{id:'intel:kill:300001:1',category:'intel',kind:'intel_kill',subject:'J5A-IX',system_id:300001,system_name:'J5A-IX',character_name:'Test Region',region_name:'Test Region',jumps:null,corporation_id:null,kill_count:2,cents:'300000',missing:0,when:1800000000,receipt:'receipt',notification_id:'id',overlay_reports:[{id:'kill:300001:1',kind:'kill',when:1800000000,kill_count:2,cents:'300000',missing:0,pilots:[],ships:['2 × Rifter']}]}];
 const old=w.fetch;w.fetch=async(url,opts)=>url==='/api/notifications/sent'?{ok:true,json:async()=>({ok:true})}:url==='/api/intel/alerts'?{ok:true,json:async()=>({enabled:true,notifications_enabled:true,overlay:{enabled:true,seconds:60},items:intel.alerts})}:old(url,opts);
 await run('pollIntelAlerts()');assert.equal(sent.length,1);assert.match(sent[0].body,/Kill in the region: J5A-IX · 2 kill · Test Region/);assert(!sent[0].body.includes('null jump'));assert(!sent[0].body.includes('ISK'));
 assert.equal(overlays.at(-1).items.length,1);assert.equal(overlays.at(-1).items[0].pilots,'2 kill');assert(!overlays.at(-1).items[0].pilots.includes('Unnamed'));assert.equal(overlays.at(-1).items[0].jumps,null);
 await run('applyIntelNotificationPreferences({...notificationData.preferences,categories:{...notificationData.preferences.categories,intel:false}})');await run('pollIntelAlerts()');assert.equal(sent.length,1);assert.equal(overlays.at(-1).enabled,false);
});
test('kill region and source settings save independently from chat parsing region',async t=>{
 const {w,d,run,intel}=await fixture();t.after(()=>w.close());run('openSettingsTab("intel")');await tick();
 const form=d.querySelector('#intel-settings');form.elements.kill_region.value='10';form.elements.killfeed_enabled.checked=false;form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();
 assert.equal(intel.preferences.killfeed_enabled,false);assert.equal(intel.preferences.kill_region_ids[0],10);assert.equal(intel.preferences.region_ids.length,0);assert.equal(intel.preferences.enabled,true);
});
test('live kills do not dismiss an open region selector and paint after focus leaves it',async t=>{
 const {w,d,run,intel}=await fixture();t.after(()=>w.close());const select=d.querySelector('#intel-region'),svg=d.querySelector('#intel-map svg');select.focus();
 intel.nodes[0].kill_groups=[killGroup()];await run('refreshIntel(true)');assert.equal(d.querySelector('#intel-region'),select);assert.equal(d.querySelector('#intel-map svg'),svg);
 select.blur();await run('refreshIntel(true)');assert.notEqual(d.querySelector('#intel-map svg'),svg);assert(d.querySelector('.intel-kill-summary'));
});
