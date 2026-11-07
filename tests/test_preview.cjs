'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function fixture(platform='mac'){
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext()),calls=[],native=[];
 const state={csrf:'test',version:'1.7.0',characters:[],corporations:[],production_characters:[],plans:[],jobs:[],settings:{source:'manual'},task:{running:false},sde:{buildNumber:1},recipe_count:1};
 const data={supported:true,enabled:false,editing:false,only_eve:true,fps:5,screen_permission:false,accessibility_permission:false,error:'',next_key:{code:124,modifiers:6144},previous_key:{code:123,modifiers:6144},hotkeys_active:false,windows:[{key:'a',title:'EVE - Pilot <A>',label:'',enabled:true,width:260,online:true,active:false,capturing:false},{key:'b',title:'EVE - Pilot B',label:'B',enabled:true,width:260,online:true,active:false,capturing:false}]};
 w.localStorage.setItem('eve-muhely-language','en');w.confirm=()=>true;
 if(platform==='mac')w.webkit={messageHandlers:{eveDesktop:{postMessage:async body=>{native.push(body);if(body.action==='previewConfigure'){const options=body.options;Object.assign(data,options);if(options.slots){data.windows=options.slots.map(slot=>({...data.windows.find(r=>r.key===slot.key),...slot}));delete data.slots;}}return structuredClone(data);}}}};
 w.fetch=async url=>{calls.push(url);const value=url==='/api/state'?state:url==='/api/notifications'?{items:[],counts:{},task:{running:false},corporations:[],preferences:{os_enabled:false,categories:{intel:false}}}:url==='/api/intel/alerts'?{enabled:false,items:[]}:null;if(value===null)throw Error('Unexpected '+url);return {ok:true,json:async()=>value};};
 for(const tag of d.querySelectorAll('script[src]'))run(fs.readFileSync(path.join(root,tag.getAttribute('src')),'utf8'));
 await tick();await tick();if(platform==='windows'){w.EveDesktop.active=true;w.EveDesktop.platform='windows';}
 run('navigate("preview")');await tick();await tick();return {w,d,run,native,calls,data};
}
for(const platform of ['browser','windows'])test('eve-preview explains unavailable '+platform+' support without native or ESI calls',async t=>{
 const f=await fixture(platform);t.after(()=>f.w.close());assert(f.d.querySelector('#view-content').textContent.includes('Mac desktop app'));assert.equal(f.d.querySelector('#preview-settings'),null);assert.equal(f.native.length,0);assert(!f.calls.some(url=>url.includes('preview')));
});
test('Mac preview has compact translated controls, safe window names and a separate menu',async t=>{
 const {w,d,native,calls,run}=await fixture();t.after(()=>w.close());assert.equal(d.querySelector('#page-title').textContent,'eve-preview');assert(d.querySelector('[data-view=preview]'));assert(d.querySelector('.plan-selector').hidden);assert.equal(d.querySelectorAll('[data-preview-row]').length,2);assert(d.querySelector('#view-content').textContent.includes('EVE - Pilot <A>'));assert.equal(d.querySelector('#view-content A'),null);assert(!/[áéíóöőúüű]/i.test(d.querySelector('#view-content').textContent.replaceAll('EVE Műhely','')),d.querySelector('#view-content').textContent);assert(!native.some(r=>r.action==='previewPermission'));assert(!calls.some(url=>url.includes('preview')));
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
