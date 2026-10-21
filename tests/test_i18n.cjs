const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {JSDOM}=require('jsdom');
const root=path.join(__dirname,'../static');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('moon refresh distinguishes optional access from real errors in English',async t=>{
 const dom=await page(),i=dom.window.EveI18n;t.after(()=>dom.window.close());i.setLanguage('en');
 const message='Holdadatok: naptár 5, értesítések 5, corporation-időzítők 0 sikeres olvasó. Kihagyott holdadatforrások: 5 karakter még nem engedélyezte. Nem elérhető corporation-időzítők: 5 karakter (403 / Station Manager). A naptár és az értesítések ettől függetlenül használhatók.';
 const en=i.t(message);assert.match(en,/Moon data: calendar 5, notifications 5, corporation timers 0 successful readers/);
 assert.match(en,/Skipped moon sources: 5 characters/);assert.match(en,/Unavailable corporation timers: 5 characters/);
 assert(!/[áéőű]/i.test(en));
 const error=i.t('Sikertelen holdadat-lekérések: 1; a korábbi adatok megmaradtak. Részletek: Beállítások → Adathozzáférések.\nHoldadat-hiba · Reader · Naptár: A karakter belépése hiányzik. Engedélyezd újra a karaktert.');
 assert.match(error,/Failed moon data requests: 1/);assert.match(error,/Settings → Data access/);assert.match(error,/Moon data error · Reader · Calendar:/);
 assert(!/[áéőű]/i.test(error));
});
async function page(html='',saved=null){
  const dom=new JSDOM(`<html lang="hu"><body><div class="language-control" data-i18n-skip><button data-ui-language="hu">Magyar</button><button data-ui-language="en">English</button></div>${html}</body></html>`,{url:'http://127.0.0.1:8765',runScripts:'outside-only'});
  if(saved)dom.window.localStorage.setItem('eve-muhely-language',saved);
  for(const name of ['i18n-en.js','i18n.js'])vm.runInContext(fs.readFileSync(path.join(root,name),'utf8'),dom.getInternalVMContext());
  await tick();return dom;
}
test('English translates messages and parameters while preserving names and escaping',async()=>{
  const dom=await page();const i=dom.window.EveI18n;i.setLanguage('en');
  assert.equal(i.t('Gyártási terv'),'Production plan');
  assert.equal(i.t('Salvation – Név másolása'),'Salvation – Copy name');
  assert.equal(i.t('Az EVE szerver HTTP 400 hibát jelzett. A korábbi adatok megmaradtak.'),'The EVE server returned HTTP 400. Previous data has been preserved.');
  const p=dom.window.document.createElement('p');p.textContent='Másolva: <script>arbitrary name</script>';dom.window.document.body.append(p);await tick();
  assert.equal(p.textContent,'Copied: <script>arbitrary name</script>');assert.equal(p.querySelector('script'),null);
  dom.window.close();
});
test('language buttons persist selection and do not change unsaved fields, item names or theme',async()=>{
  const dom=await page('<h1>Gyártási terv</h1><input value="15 000 000"><span data-i18n-skip>Gyártási terv</span><button class="copy-item-name" data-copy-item="Reakció">Reakció</button>');
  const w=dom.window,d=w.document;w.localStorage.setItem('eve-muhely-theme','light');
  const input=d.querySelector('input');input.value='73 123';input.focus();input.setSelectionRange(2,5);
  d.querySelector('[data-ui-language=en]').click();await tick();
  assert.equal(d.documentElement.lang,'en');assert.equal(d.querySelector('h1').textContent,'Production plan');
  assert.equal(input.value,'73 123');assert.equal(input.selectionStart,2);assert.equal(d.activeElement,input);
  assert.equal(d.querySelector('.copy-item-name').textContent,'Reakció');assert.equal(d.querySelector('.copy-item-name').dataset.copyItem,'Reakció');
  assert.equal(d.querySelector('span').textContent,'Gyártási terv');assert.equal(w.localStorage.getItem('eve-muhely-language'),'en');assert.equal(w.localStorage.getItem('eve-muhely-theme'),'light');
  d.querySelector('[data-ui-language=hu]').click();await tick();assert.equal(d.querySelector('h1').textContent,'Gyártási terv');assert.equal(input.value,'73 123');
  w.close();
});
test('saved language, malformed preferences and blocked storage are safe',async()=>{
  for(const [saved,expected] of [['en','Production plan'],['unexpected','Gyártási terv']]){
    const dom=await page('<p>Gyártási terv</p>',saved);assert.equal(dom.window.document.querySelector('p').textContent,expected);dom.window.close();
  }
  const dom=await page('<p>Gyártási terv</p>');Object.defineProperty(dom.window,'localStorage',{get(){throw new Error('blocked');}});
  dom.window.EveI18n.setLanguage('en');assert.equal(dom.window.document.querySelector('p').textContent,'Production plan');dom.window.close();
});
test('new content, attributes and dates translate and restore without replacing controls',async()=>{
  const dom=await page(),w=dom.window,d=w.document;w.EveI18n.setLanguage('en');
  const div=d.createElement('div'),stamp=w.EveI18n.date(1760000000000,{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
  div.innerHTML=`<label title="Rendezés: Termék">Gyártási terv</label><input placeholder="Szűrés…"><small>${stamp}</small>`;d.body.append(div);await tick();
  assert.equal(div.querySelector('label').textContent,'Production plan');assert.equal(div.querySelector('label').title,'Sort: Product');assert.equal(div.querySelector('input').placeholder,'Filter…');
  assert.notEqual(div.querySelector('small').textContent,stamp);
  const input=div.querySelector('input');w.EveI18n.setLanguage('hu');await tick();assert.equal(input,div.querySelector('input'));assert.equal(input.placeholder,'Szűrés…');assert.equal(div.querySelector('small').textContent,stamp);
  div.querySelector('label').textContent='Készlet';await tick();w.EveI18n.setLanguage('en');await tick();assert.equal(div.querySelector('label').textContent,'Inventory');w.close();
});
test('table filters, character dropdowns and row controls survive language changes',async()=>{
  const dom=await page(),w=dom.window,d=w.document;vm.runInContext(fs.readFileSync(path.join(root,'tables.js'),'utf8'),dom.getInternalVMContext());
  d.body.insertAdjacentHTML('beforeend',w.EveTables.markup(['Karakter','Tevékenység'],['<tr><td data-filter-value="Reakció">Reakció</td><td>Gyártás<input value="22"></td></tr>','<tr><td data-filter-value="Other">Other</td><td>Reakció<input value="33"></td></tr>'],'','stable-key'));
  await tick();w.EveI18n.setLanguage('en');await tick();
  assert.equal(d.querySelector('[data-table-filter="0"] option[value="Reakció"]').textContent,'Reakció');
  const filter=d.querySelector('[data-table-filter="1"]'),row=d.querySelector('tbody tr'),input=row.querySelector('input');
  filter.value='Manufacturing';filter.dispatchEvent(new w.Event('input'));await tick();assert.equal(row.hidden,false);assert.equal(row.nextElementSibling.hidden,true);
  input.value='777';w.EveI18n.setLanguage('hu');await tick();assert.equal(row.querySelector('input'),input);assert.equal(input.value,'777');assert.equal(filter.value,'Manufacturing');assert.equal(d.querySelector('.table-filters').hidden,true);assert.equal(d.querySelector('.table-empty-row td').textContent,'Nincs a szűrésnek megfelelő sor.');w.close();
});
test('number validation switches language and preserves 100-million-unit quantities',async()=>{
  const dom=await page('<input data-grouped-number data-number-min="1" data-number-max="100000000" value="100000001">'),w=dom.window,d=w.document;
  vm.runInContext(fs.readFileSync(path.join(root,'numbers.js'),'utf8'),dom.getInternalVMContext());await tick();const input=d.querySelector('input');
  assert.match(input.validationMessage,/Egész számot/);w.EveI18n.setLanguage('en');await tick();assert.equal(input.value,'100 000 001');assert.equal(input.validationMessage,'Enter a whole number between 1 and 100 000 000.');
  input.value='100 000 000';input.dispatchEvent(new w.Event('input'));assert.equal(input.validationMessage,'');w.close();
});
test('blueprint wire values and canonical metadata are not translated',async()=>{
  const dom=await page('<select data-id="92822" data-key="source"><option value="auto">Automatikus</option><option value="manual" selected>Kézi</option></select><input data-id="92822" data-key="me" value="3"><span data-i18n-skip>Készlet</span>');
  const w=dom.window,d=w.document,select=d.querySelector('select');w.EveI18n.setLanguage('en');await tick();
  assert.equal(select.value,'manual');assert.equal(select.selectedOptions[0].textContent,'Manual');assert.equal(select.dataset.key,'source');assert.equal(d.querySelector('input').value,'3');assert.equal(d.querySelector('span').textContent,'Készlet');
  w.EveI18n.setLanguage('hu');await tick();assert.equal(select.value,'manual');assert.equal(select.selectedOptions[0].textContent,'Kézi');w.close();
});
test('stale-stock and edited-plan banners translate with names preserved',async()=>{
 const dom=await page(),i=dom.window.EveI18n;i.setLanguage('en');
 assert.equal(i.t('Korábbi EVE-adatokból számolunk: Alpha Test, Készlet. Frissítsd az EVE-adatokat; a legutóbbi sikeres pillanatkép addig megmarad.'),'Using an earlier EVE snapshot: Alpha Test, Készlet. Refresh the EVE data; the last successful snapshot remains available until then.');
 assert.equal(i.t('Módosított mennyiség vagy gyártó karakter előnézete. A Terv és foglalás frissítése gombbal érvényesítheted. A későbbi tervek kiosztása is változhat.'),'Preview of a changed quantity or manufacturing character. Apply it using Update plan and reservations. Allocations for later plans may also change.');
 dom.window.close();
});
test('moon dropdown filters select exact column values and preserve names across languages',async()=>{
 const dom=await page(),w=dom.window,d=w.document;vm.runInContext(fs.readFileSync(path.join(root,'tables.js'),'utf8'),dom.getInternalVMContext());
 d.body.insertAdjacentHTML('beforeend',w.EveTables.markup(['Hold','Anyag'],['<tr><td><span data-i18n-skip>Moon 1</span></td><td>One</td></tr>','<tr><td><span data-i18n-skip>Moon 10</span></td><td>Two</td></tr>','<tr><td><span data-i18n-skip>Moon 1</span></td><td>Three</td></tr>'],'','moon-select',{selectColumns:[0]}));await tick();
 const select=d.querySelector('[data-table-filter="0"]');assert.equal(select.tagName,'SELECT');assert.equal(select.options.length,3);assert.equal(d.querySelector('.table-filters').hidden,true);
 select.value='Moon 1';select.dispatchEvent(new w.Event('change'));await tick();
 assert.deepEqual([...d.querySelectorAll('tbody tr:not(.table-empty-row)')].map(r=>r.hidden),[false,true,false]);
 w.EveI18n.setLanguage('en');await tick();assert.equal(select.value,'Moon 1');assert.equal(select.options[0].textContent,'All moons');dom.window.close();
});

test('moon filter removes selections that disappeared from refreshed rows',async()=>{
 const dom=await page(),w=dom.window,d=w.document;vm.runInContext(fs.readFileSync(path.join(root,'tables.js'),'utf8'),dom.getInternalVMContext());
 const host=d.createElement('div');d.body.append(host);
 const markup=name=>w.EveTables.markup(['Hold'],['<tr><td><span data-i18n-skip>'+name+'</span></td></tr>'],'','refreshed-moons',{selectColumns:[0]});
 host.innerHTML=markup('Moon 1');await tick();let select=host.querySelector('select');select.value='Moon 1';select.dispatchEvent(new w.Event('change'));
 host.innerHTML=markup('Moon 2');await tick();select=host.querySelector('select');assert.equal(select.value,'');assert.deepEqual([...select.options].map(o=>o.value),['','Moon 2']);dom.window.close();
});
test('PI forecast and manual fuel controls translate while keeping entered prices intact',async()=>{
 const dom=await page('<label>Fuel Block típusa<select><option data-i18n-skip>Hydrogen Fuel Block</option></select></label><label>Kézi Fuel Block egységár (ISK)<input value="12 345,6789" placeholder="Üresen: Jita-ár"></label><h3>Időalapú termelési becslés</h3><p>Készletből még: 2 óra</p><p>Becsült termék a következő 24 órában</p>');
 const w=dom.window,d=w.document;w.EveI18n.setLanguage('en');await tick();
 assert.equal(d.querySelector('h3').textContent,'Time-based production forecast');
 assert.equal(d.querySelector('input').value,'12 345,6789');
 assert.equal(d.querySelector('input').placeholder,'Empty: use Jita price');
 assert.equal(d.querySelector('option').textContent,'Hydrogen Fuel Block');
 assert.equal([...d.querySelectorAll('p')][1].textContent,'Estimated products in the next 24 hours');
 w.EveI18n.setLanguage('hu');await tick();assert.equal(d.querySelector('h3').textContent,'Időalapú termelési becslés');w.close();
});

test('complete delivered-job cache errors translate while preserving plan and item names',async()=>{
 const dom=await page(),i=dom.window.EveI18n;i.setLanguage('en');
 const materials='Caesarium Cadmide, Carbon Polymers, Fluxed Condensates, Prometium';
 const body='Átvett jobok újabbak az EVE készletpillanatképénél: '+materials+'. Az EVE gyorsítótárának lejártáig az ismételt frissítés ugyanazt az adatot adhatja. A foglalásaid megmaradnak.';
 const english='Delivered jobs are newer than the EVE inventory snapshot: '+materials+'. Refreshing again may return the same data until the EVE cache expires. Your reservations are preserved.';
 assert.equal(i.t(body),english);
 assert.equal(i.t('A(z) Redeemer terv készletfrissítésre vár. '+body),'Plan Redeemer is waiting for an inventory update. '+english);
 assert.equal(i.t('A(z) Project. Készlet terv készletfrissítésre vár. '+body),'Plan Project. Készlet is waiting for an inventory update. '+english);
 dom.window.close();
});
