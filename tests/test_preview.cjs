'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function fixture(platform='mac'){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[],native=[];
 const state={csrf:'test',version:'1.7.0',characters:[],corporations:[],production_characters:[],plans:[],jobs:[],settings:{source:'manual'},task:{running:false},sde:{buildNumber:1},recipe_count:1};
 const mining={enabled:true,folder:'/test/Gamelogs',characters:[],error:null,file_errors:0};
 const data={supported:true,enabled:false,editing:false,only_eve:true,fps:5,screen_permission:false,accessibility_permission:false,error:'',next_key:{code:124,modifiers:6144},previous_key:{code:123,modifiers:6144},hotkeys_active:false,windows:[{key:'a',title:'EVE - Pilot <A>',label:'',enabled:true,width:260,online:true,active:false,capturing:false,has_frame:false},{key:'b',title:'EVE - Pilot B',label:'B',enabled:true,width:260,online:true,active:false,capturing:false,has_frame:false}]};
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 if(platform==='mac')w.webkit={messageHandlers:{eveDesktop:{postMessage:async body=>{native.push(body);if(body.action==='previewConfigure'){const options=body.options;Object.assign(data,options);if(options.slots){data.windows=options.slots.map(slot=>({...data.windows.find(r=>r.key===slot.key),...slot}));delete data.slots;}}return structuredClone(data);}}}};
 w.fetch=async (url,options={})=>{calls.push(url);if(url==='/api/preview/mining/replace-crystal'){const body=JSON.parse(options.body);assert.equal(body.name,mining.characters[0].name);assert.equal(body.id,mining.characters[0].alerts[0].id);mining.characters[0].alerts=[{id:'a'.repeat(24),kind:'module_stopped',at:2}];}if(url==='/api/preview/mining/acknowledge'){const body=JSON.parse(options.body);mining.characters[0].alerts=mining.characters[0].alerts.filter(a=>!body.ids.includes(a.id));}const value=url==='/api/state'?state:url.startsWith('/api/preview/mining')?mining:url==='/api/notifications'?{items:[],counts:{},task:{running:false},corporations:[],preferences:{os_enabled:false,categories:{intel:false}}}:url==='/api/intel/alerts'?{enabled:false,items:[]}:null;if(value===null)throw Error('Unexpected '+url);return {ok:true,json:async()=>value};};
 for(const tag of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,tag.getAttribute('src')),'utf8'));
 await tick();await tick();if(platform==='windows'){w.EveDesktop.active=true;w.EveDesktop.platform='windows';}
 run('navigate("preview")');await tick();await tick();return {w,d,run,native,calls,data,mining};
}
for(const platform of ['browser','windows'])test('eve-preview explains unavailable '+platform+' support without native or ESI calls',async t=>{
 const f=await fixture(platform);t.after(()=>f.w.close());assert(f.d.querySelector('#view-content').textContent.includes('Mac desktop app'));assert.equal(f.d.querySelector('#preview-settings'),null);assert.equal(f.native.length,0);assert(!f.calls.some(url=>url.includes('preview')));
});
test('Mac preview has compact translated controls, safe window names and a separate menu',async t=>{
 const {w,d,native,calls,run}=await fixture();t.after(()=>w.close());assert.equal(d.querySelector('#page-title').textContent,'eve-preview');assert(d.querySelector('[data-view=preview]'));assert(d.querySelector('.plan-selector').hidden);assert.equal(d.querySelectorAll('[data-preview-row]').length,2);assert(d.querySelector('#view-content').textContent.includes('EVE - Pilot <A>'));assert.equal(d.querySelector('#view-content A'),null);assert(!/[áéíóöőúüű]/i.test(d.querySelector('#view-content').textContent.replaceAll('EVE Műhely','')),d.querySelector('#view-content').textContent);assert(!native.some(r=>r.action==='previewPermission'));assert(!calls.some(url=>url.includes('preview')&&url!=='/api/preview/mining'));
 w.EveI18n.setLanguage('hu');await tick();assert(d.querySelector('#view-content').textContent.includes('Előnézet és ablakváltás'));run('render()');assert(d.querySelector('#preview-settings'));
});
test('polling preserves unsaved labels, size, order and newly discovered windows',async t=>{
 const {w,d,run,data,native}=await fixture();t.after(()=>w.close());const form=d.querySelector('#preview-settings'),label=form.querySelector('[data-label]');label.value='My custom pilot';form.dispatchEvent(new w.Event('input',{bubbles:true}));form.querySelector('[data-down]').click();data.windows.push({key:'c',title:'EVE - Pilot C',label:'',enabled:true,width:300,online:true});await run('loadPreview()');assert.equal(d.querySelector('#preview-settings'),form);assert.equal(form.querySelector('[data-preview-row="a"] [data-label]').value,'My custom pilot');assert.deepEqual([...form.querySelectorAll('[data-preview-row]')].map(r=>r.dataset.previewRow),['b','a','c']);
 form.elements.enabled.checked=true;form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();const call=native.findLast(r=>r.action==='previewConfigure');assert(call.options.enabled);assert.deepEqual([...call.options.slots].map(r=>r.key),['b','a','c']);assert.equal(run('Object.keys(dirty).length'),0);assert(d.querySelector('#preview-settings').elements.enabled.checked);
});
test('permission, layout and activation require explicit clicks; invalid hotkeys do not save',async t=>{
 const {w,d,run,data,native}=await fixture();t.after(()=>w.close());d.querySelector('[data-preview-permission=screen]').click();await tick();assert.equal(native.findLast(r=>r.action==='previewPermission').kind,'screen');
 let form=d.querySelector('#preview-settings');form.elements.next_code.value='123';form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();assert(!native.some(r=>r.action==='previewConfigure'));assert(d.querySelector('#global-error').textContent.includes('must be different'));
 form.elements.next_code.value='124';form.elements.enabled.checked=true;form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();d.querySelector('#preview-layout').click();await tick();assert(native.findLast(r=>r.action==='previewConfigure').options.editing);assert(d.querySelector('#preview-status').textContent.includes('Editing layout'));
 data.accessibility_permission=true;data.screen_permission=true;await run('loadPreview()');d.querySelector('[data-activate]').click();await tick();assert.equal(native.findLast(r=>r.action==='previewActivate').key,'a');
 data.windows[0].width=345;await run('loadPreview()');assert.equal(d.querySelector('[data-width]').value,'345');
});
test('Mac bridge exposes only the intended preview messages',async t=>{
 const {w,native}=await fixture();t.after(()=>w.close());await w.EveDesktop.cyclePreview(-1);assert.equal(native.at(-1).action,'previewCycle');assert.equal(native.at(-1).direction,-1);
});

test('capture status waits for the first actual frame before calling a preview live',async t=>{
 const {w,d,run,data}=await fixture();t.after(()=>w.close());data.windows[0].capturing=true;await run('loadPreview()');assert.equal(d.querySelector('[data-preview-state]').textContent,'Starting preview…');data.windows[0].has_frame=true;await run('loadPreview()');assert.equal(d.querySelector('[data-preview-state]').textContent,'Live preview');
});

test('shortcut delivery count updates without replacing edited fields',async t=>{
 const {w,d,run,data}=await fixture();t.after(()=>w.close());const form=d.querySelector('#preview-settings');form.querySelector('[data-label]').value='Keep label';form.dispatchEvent(new w.Event('input',{bubbles:true}));data.shortcut_count=4;await run('loadPreview()');assert.equal(d.querySelector('#preview-key-count').textContent,'4');assert.equal(d.querySelector('#preview-settings'),form);assert.equal(form.querySelector('[data-label]').value,'Keep label');data.error='hotkey_unavailable';await run('loadPreview()');assert(d.querySelector('#preview-status').textContent.includes('Shortcut listening could not start'));
});


test('shortcut fields record a single key or full combination without dropdowns',async t=>{
 const {w,d,run,native,data}=await fixture();t.after(()=>w.close());let form=d.querySelector('#preview-settings');
 assert.equal(form.querySelector('select'),null);const input=form.elements.next_shortcut;input.focus();await tick();assert.equal(native.findLast(r=>r.action==='previewKeyCapture').capturing,true);
 const press=(field,code,key,modifiers={})=>field.dispatchEvent(new w.KeyboardEvent('keydown',{code,key,...modifiers,bubbles:true,cancelable:true}));
 w.dispatchEvent(new w.Event('blur'));await tick();assert.equal(native.findLast(r=>r.action==='previewKeyCapture').capturing,false);w.dispatchEvent(new w.Event('focus'));await tick();assert.equal(native.findLast(r=>r.action==='previewKeyCapture').capturing,true);
 press(input,'KeyK','k');assert.equal(input.value,'K');assert.equal(form.elements.next_modifiers.value,'0');await run('loadPreview()');assert.equal(form.elements.next_shortcut,input);assert.equal(input.value,'K');
 input.blur();await tick();assert.equal(native.findLast(r=>r.action==='previewKeyCapture').capturing,false);
 form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();await tick();const saved=native.findLast(r=>r.action==='previewConfigure');assert.equal(saved.options.next_key.code,40);assert.equal(saved.options.next_key.modifiers,0);assert.equal(run('Object.keys(dirty).length'),0);
 form=d.querySelector('#preview-settings');assert.equal(form.elements.next_shortcut.value,'K');assert(d.querySelector('#view-content').textContent.includes('Click a shortcut field'));assert(d.querySelector('#view-content').textContent.includes('only while EVE is in front'));
 press(form.elements.previous_shortcut,'KeyK','k');const count=native.filter(r=>r.action==='previewConfigure').length;form.dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await tick();assert.equal(native.filter(r=>r.action==='previewConfigure').length,count);assert(d.querySelector('#global-error').textContent.includes('must be different'));
 press(form.elements.previous_shortcut,'KeyJ','J',{ctrlKey:true,altKey:true,shiftKey:true});assert.equal(form.elements.previous_shortcut.value,'Control + Option + Shift + J');assert.equal(form.elements.previous_modifiers.value,String(4096|2048|512));
 for(const code of ['F12','PageUp','NumpadEnter','Semicolon','Space'])press(form.elements.next_shortcut,code,code);assert.equal(form.elements.next_shortcut.value,'Space');
 const before=form.elements.next_code.value;press(form.elements.next_shortcut,'ControlLeft','Control',{ctrlKey:true});press(form.elements.next_shortcut,'KeyL','l',{repeat:true});assert.equal(form.elements.next_code.value,before);
 const tab=new w.KeyboardEvent('keydown',{key:'Tab',code:'Tab',bubbles:true,cancelable:true});assert(form.elements.next_shortcut.dispatchEvent(tab));
});

test('mining badges are forwarded from authenticated local logs without changing dirty fields',async t=>{
 const {w,d,run,native}=await fixture();t.after(()=>w.close());assert(d.querySelector('#preview-mining'));assert(d.querySelector('#preview-mining').textContent.includes('Mining alerts'));
 assert(native.some(r=>r.action==='previewMining'));const form=d.querySelector('#preview-mining-settings');form.elements.folder.value='/half-entered';
 run(`previewMiningData={enabled:true,folder:'/original',characters:[{name:'Pilot <A>',last_module:'Strip Miner',alerts:[{id:'123456789012345678901234',kind:'crystal_broken',at:1,crystal:'Crystal <A>'}]}]};renderPreviewMining();`);
 assert.equal(d.querySelector('#preview-mining-settings'),form);assert.equal(form.elements.folder.value,'/half-entered');assert(d.querySelector('#preview-mining').textContent.includes('Crystal destroyed'));assert(d.querySelector('#preview-mining').textContent.includes('Pilot <A>'));assert.equal(d.querySelector('#preview-mining A'),null);assert(d.querySelector('[data-mining-ack]'));
});


test('native crystal and pause clicks call the protected event-specific endpoints',async t=>{
 const {w,d,run,calls,mining,native}=await fixture();t.after(()=>w.close());mining.characters=[{name:'Pilot A',last_module:'Miner',alerts:[{id:'b'.repeat(24),kind:'crystal_broken',at:1}]}];
 await run(`previewMiningAction({name:'Pilot A',kind:'crystal_broken',id:'${'b'.repeat(24)}'})`);
 assert(calls.includes('/api/preview/mining/replace-crystal'));assert(d.querySelector('#preview-mining-rows').textContent.includes('Module not running'));assert(native.findLast(r=>r.action==='previewMining').data.characters[0].alerts[0].kind==='module_stopped');
 await run(`previewMiningAction({name:'Pilot A',kind:'module_stopped',id:'${'a'.repeat(24)}'})`);
 assert(calls.includes('/api/preview/mining/acknowledge'));assert(d.querySelector('#preview-mining-rows').textContent.includes('No new alerts'));
});
