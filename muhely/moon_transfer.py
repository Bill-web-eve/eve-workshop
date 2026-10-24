"""Portable moon-register backups and EVE survey clipboard imports."""
from __future__ import annotations
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import re

from .moons import validate_moon, composition_state
from .planner import PlanningError
from .store import moon_revision

FORMAT='eve-workshop-moons'
MAX_MOONS=1000
MAX_TEXT=1024*1024
FIELDS={'system_id','moon_id','structure','ores','notes','enabled','online_starts','rent_isk','other_cost_isk','belt_lifetime_hours'}
COLUMNS=['moon','moonproduct','quantity','oretypeid','solarsystemid','planetid','moonid']

def location(catalog,sid,mid):
    if sid not in catalog.moon_systems:raise PlanningError('Ismeretlen rendszer az importban.')
    row=next((m for m in catalog.moon_locations(sid) if m['id']==mid),None)
    if not row:raise PlanningError('A MoonID nem a megadott rendszerhez tartozik.')
    return row

def export_register(store,catalog):
    rows=[]
    for record in store.moon_records():
        row={k:v for k,v in record.items() if k in FIELDS}
        row['name']=location(catalog,record['system_id'],record['moon_id'])['name']
        row['ores']=[{**o,'name':catalog.moon_ores[o['id']]['name']} for o in record['ores']]
        rows.append(row)
    return {'format':FORMAT,'version':1,'exported_at':datetime.now(timezone.utc).isoformat(),
            'sde_build':catalog.meta.get('buildNumber'),'moons':rows}

def parse_json(text):
    try:data=json.loads(text)
    except (ValueError,RecursionError):raise PlanningError('Nem olvasható JSON holdexport.') from None
    if not isinstance(data,dict) or data.get('format')!=FORMAT or type(data.get('version')) is not int or data['version']!=1:
        raise PlanningError('Nem támogatott holdexport-formátum vagy verzió.')
    rows=data.get('moons')
    if not isinstance(rows,list):raise PlanningError('A holdexport nem tartalmaz holdlistát.')
    result=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)-FIELDS-{'name'}:raise PlanningError('Ismeretlen mező a holdexportban.')
        if not isinstance(row.get('ores'),list):raise PlanningError('Hibás érclista a holdexportban.')
        ores=[]
        for ore in row['ores']:
            if not isinstance(ore,dict) or set(ore)-{'id','name','percent'}:raise PlanningError('Hibás érclista a holdexportban.')
            ores.append({k:v for k,v in ore.items() if k in {'id','percent'}})
        result.append(({**{k:v for k,v in row.items() if k in FIELDS},'ores':ores},[]))
    return result

def scan_error(number,message):
    raise PlanningError(f'Hibás scansor: {number} · {message}')

def parse_scan(text,catalog):
    grouped={};header=COLUMNS;title=''
    for number,line in enumerate(text.splitlines(),1):
        if not line.strip():continue
        if line.lstrip().startswith('|'):
            cells=[c.strip() for c in line.strip().strip('|').split('|')]
            if cells and all(re.fullmatch(r':?-+:?',c.replace(' ','')) for c in cells):continue
        else:
            try:cells=[c.strip() for c in next(csv.reader([line],delimiter='\t',strict=True))]
            except csv.Error:scan_error(number,'Hibás tabulátoros sor.')
        keys=[re.sub(r'\s+','',c).lower() for c in cells]
        if set(keys)==set(COLUMNS):header=keys;continue
        if len(cells)==1 or (cells[0] and not any(cells[1:])):
            title=cells[0];continue
        if len(cells)==6 and header==COLUMNS:cells.insert(0,'')
        if len(cells)!=7:scan_error(number,'Hét oszlop szükséges; a játékból tabulátorokkal másold ki a táblázatot.')
        r=dict(zip(header,cells));name=r['moon'] or title
        try:
            if not all(re.fullmatch(r'\d+',r[k]) for k in ['oretypeid','solarsystemid','planetid','moonid']):raise ValueError()
            tid,sid,pid,mid=(int(r[k]) for k in ['oretypeid','solarsystemid','planetid','moonid'])
            quantity=Decimal(r['quantity'].replace(',','.'))
            if not quantity.is_finite() or not 0<quantity<=1:raise ValueError()
        except (ValueError,InvalidOperation):scan_error(number,'Érvényes azonosítók és 0–1 közötti Quantity szükséges.')
        try:moon=location(catalog,sid,mid)
        except PlanningError as e:scan_error(number,str(e))
        planet=catalog.pi_planets.get(pid)
        if not planet or planet['system_id']!=sid or moon['name'].split(' - Moon ')[0]!=planet['name']:
            scan_error(number,'A PlanetID nem a megadott hold bolygója.')
        if tid not in catalog.moon_ores:scan_error(number,'Az Ore TypeID nem ismert holdérc.')
        ore=catalog.moon_ores[tid]
        entry=grouped.setdefault(mid,({'system_id':sid,'moon_id':mid,'ores':[]},[]));row,warnings=entry
        if row['system_id']!=sid:scan_error(number,'Egy holdhoz több rendszerazonosító szerepel.')
        if any(o['id']==tid for o in row['ores']):scan_error(number,'Ismételt érc ugyanannál a holdnál.')
        if len(row['ores'])==4:scan_error(number,'Egy holdhoz legfeljebb négy érc adható meg.')
        row['ores'].append({'id':tid,'percent':float(quantity*100)})
        if name and name!=moon['name']:warnings.append('Az eltérő holdnév helyett a MoonID szerinti hivatalos nevet használjuk.')
        if r['moonproduct']!=ore['name']:warnings.append('Az eltérő ércnév helyett az Ore TypeID szerinti nevet használjuk.')
        if len(grouped)>MAX_MOONS:raise PlanningError('Egyszerre legfeljebb 1000 hold importálható.')
    return list(grouped.values())

def prepare(store,catalog,data):
    if not isinstance(data,dict):raise PlanningError('Hibás holdimport.')
    text=data.get('text');kind=data.get('format');mode=data.get('existing','skip')
    if not isinstance(text,str) or not text.strip() or len(text.encode('utf-8'))>MAX_TEXT:raise PlanningError('Az import szövege üres vagy nagyobb 1 MB-nál.')
    if mode not in ['skip','update']:raise PlanningError('Ismeretlen frissítési mód.')
    if kind not in ['json','scan']:raise PlanningError('Ismeretlen importformátum.')
    parsed=parse_json(text.lstrip('\ufeff')) if kind=='json' else parse_scan(text.lstrip('\ufeff'),catalog)
    if not 1<=len(parsed)<=MAX_MOONS:raise PlanningError('Az importnak 1–1000 holdat kell tartalmaznia.')
    current=store.moon_records();by_moon={r['moon_id']:r for r in current};seen=set();rows=[];values=[]
    counts={'new':0,'update':0,'skip':0}
    for raw,warnings in parsed:
        mid=raw.get('moon_id')
        if type(mid) is not int or mid in seen:raise PlanningError('Hiányzó vagy ismételt MoonID az importban.')
        seen.add(mid);old=by_moon.get(mid)
        if kind=='scan':
            # A rescan updates composition, never the saved rent or drill settings.
            value={**(old or {}),**raw}
            if not old:value.update(structure=data.get('structure','Athanor'),rent_isk=data.get('rent_isk','0'))
        else:value={**(old or {}),**raw}
        if old:value['id']=old['id']
        value=validate_moon(value,catalog,current)
        name=location(catalog,value['system_id'],mid)['name']
        action='skip' if old and mode=='skip' else 'update' if old else 'new';counts[action]+=1
        total,status=composition_state(value['ores'])
        if status=='invalid':warnings.append('Az ércarányok összege 100% felett van; a hold termelése javításig nem számít.')
        elif status=='partial':warnings.append('Részleges összetétel; az arányokat nem növeljük 100%-ra.')
        if old and kind=='scan':warnings.append('A meglévő struktúra, bérlet és egyéb holdbeállítások megmaradnak.')
        rows.append({'moon_id':mid,'name':name,'structure':value['structure'],'action':action,'percent_total':float(total),
                     'ores':[{**o,'name':catalog.moon_ores[o['id']]['name']} for o in value['ores']],
                     'rent_isk':value['rent_isk'],'other_cost_isk':value['other_cost_isk'],'warnings':list(dict.fromkeys(warnings))})
        if action!='skip':values.append(value)
    return {'revision':moon_revision(current),'counts':counts,'rows':rows},values

def preview(store,catalog,data):return prepare(store,catalog,data)[0]

def apply_import(store,catalog,data):
    report,values=prepare(store,catalog,data)
    if data.get('revision')!=report['revision']:raise PlanningError('A holdlista megváltozott; kérj új importelőnézetet.')
    store.import_moons(values,report['revision'])
    return {'ok':True,'counts':report['counts']}
