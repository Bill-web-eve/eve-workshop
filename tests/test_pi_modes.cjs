'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom'),root=path.join(__dirname,'../static'),tick=()=>new Promise(r=>setImmediate(r));
async function fixture(){
 const dom=new JSDOM('<html><body><span id="plan-status"></span><div id="actions"></div><div id="view-content"></div></body></html>',{url:'http://127.0.0.1:8765',runScripts:'outside-only'}),w=dom.window,d=w.document,run=s=>vm.runInContext(s,dom.getInternalVMContext());
 w.$=s=>d.querySelector(s);w.$$=s=>[...d.querySelectorAll(s)];w.state={task:{running:false}};w.view='pi';
 w.esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 w.fmt=n=>String(n);w.skillDate=n=>n==null?'–':new Date(n*1000).toISOString();w.skillDuration=n=>n==null?'–':`${n}s`;
 w.itemName=n=>`<span data-i18n-skip>${w.esc(n)}</span>`;
 w.panel=(name,note,body)=>`<section class="panel"><h2>${w.esc(name?.name||name)}</h2>${body}</section>`;
 w.table=(heads,rows)=>`<table><thead><tr>${heads.map(h=>`<th>${w.esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table>`;
 w.empty=s=>s;w.setHead=()=>{};w.actions=s=>d.querySelector('#actions').innerHTML=s;
 for(const script of ['i18n-en.js','i18n.js','pi.js'])run(fs.readFileSync(path.join(root,script),'utf8'));
 const now=1800000000,end=now+86400*7;
 w.sample={id:1,character_id:2,character_name:'Pilot',name:'Test I',type:'barren',checked_at:now,last_update:now-86400,status:'ok',alerts:[],monitor_mode:'extraction',cached:false,
  extraction:{next_end:end,seconds_left:86400*7,expired_count:0},factories:[],unassigned:[],unknown_recipes:[],storages:[],
  // Bogus old factory projection must never leak into the extraction UI.
  projection:{available:true,first_stop:now-86400,seconds_left:0},
  extractors:[{id:3,name:'Extractor',product:'Water',program_active:true,active:false,label:'Kimeneti útvonal hiányzik',heads:10,cycle_time:7200,program_start:now,program_duration:86400*7,cycles_remaining:84,program_end:end,seconds_left:86400*7}]};
 run('piData={characters:[{id:2,name:"Pilot",status:"loaded",expires:9999999999}],colonies:[sample],summary:{alert:0,warning:0,unknown:0}};renderPI($("#view-content"))');
 await tick();return {w,d,run,end,now};
}
test('extraction view shows exact program dates without factory predictions and translates to English',async t=>{
 const {w,d,end,now}=await fixture();t.after(()=>w.close());
 const detail=d.querySelector('#pi-detail');assert.equal(detail.querySelectorAll('table').length,1);
 assert(detail.textContent.includes(new Date(end*1000).toISOString()));assert(detail.textContent.includes(new Date(now*1000).toISOString()));
 assert(detail.textContent.includes('Program aktív'));assert(!detail.textContent.includes('Időalapú termelési becslés'));
 assert(!d.querySelector('.pi-forecast'));assert(!d.querySelector('#pi-export'));
 w.EveI18n.setLanguage('en');await tick();
 assert.match(d.querySelector('#view-content').textContent,/Extraction planet/);
 assert.match(d.querySelector('#view-content').textContent,/ESI program end · local time/);
 assert.match(detail.textContent,/Program start/);assert.match(detail.textContent,/Program active/);
 assert(!/[áéőű]/i.test(d.querySelector('#view-content').textContent),d.querySelector('#view-content').textContent);
});
test('factory coverage remains finite, local and independent of extraction view',async t=>{
 const {w,d,run,now}=await fixture();t.after(()=>w.close());
 run(`sample={...sample,monitor_mode:'factory',extractors:[],period_materials:[],factories:[],pin_count:2,upgrade_level:4,
 projection:{available:true,anchor:${now},calculated_at:${now},first_stop:${now+3600},seconds_left:3600,factories:[],warnings:[]}};
 piData.colonies=[sample];renderPI($('#view-content'));`);
 const detail=d.querySelector('#pi-detail');assert(detail.querySelector('.pi-forecast'));
 assert(detail.textContent.includes('kizárólag a bolygó letöltött készletéből'));
 assert(detail.textContent.includes('Kitermelésből vagy más bolygóról érkező utánpótlást nem adunk hozzá'));
 w.EveI18n.setLanguage('en');await tick();
 assert.match(detail.textContent,/No extraction or supplies from other planets are added/);
 assert(!detail.textContent.includes('CCP'));
});
