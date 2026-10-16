"""Manual moon register and transparent 30-day production projections."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
import time
import uuid

from .catalog import normalize
from .esi import ESI, EsiError
from .planner import PlanningError, integer, decimal_number

CACHE_SECONDS=90*86400
FUEL_BLOCKS=(4246,4247,4051,4312)
MAGMATIC_GAS=81143
DEFAULTS={'implant':4,'mining_recovery':100,'crystal_variant':'A II','fuel_block_id':4246,'fuel_block_price':None,'sales_tax':0,'broker_fee':0}
SOURCES=[
    {'name':'CCP Static Data Export','url':'https://developers.eveonline.com/docs/services/static-data/'},
    {'name':'Moon mining','url':'https://support.eveonline.com/hc/en-us/articles/115005404229-Moon-Mining'},
    {'name':'Metenox · Equinox','url':'https://www.eveonline.com/news/view/equinox-expansion-notes'},
    {'name':'Magmatic Gas · 2025','url':'https://www.eveonline.com/news/view/patch-notes-version-23-01'},
    {'name':'Tatara · 5.5%','url':'https://www.eveonline.com/news/view/patch-notes-version-20-03'},
    {'name':'Resources Realigned','url':'https://www.eveonline.com/news/view/resources-realigned'},
]
D=lambda v:Decimal(str(v))


def preferences(store):return {**DEFAULTS,**store.moon_preferences()}


def validate_preferences(data):
    if not isinstance(data,dict) or set(data)-set(DEFAULTS):raise PlanningError('Ismeretlen holdbeállítás.')
    result={}
    for key,value in data.items():
        if key=='implant':
            if isinstance(value,bool) or value not in [0,1,2,4]:raise PlanningError('Hibás finomítási implant.')
        elif key=='mining_recovery':value=float(decimal_number(value,'Begyűjtött arány',0,100))
        elif key in ['sales_tax','broker_fee']:
            amount=decimal_number(value,key,0,100)
            if amount.as_tuple().exponent < -4:raise PlanningError('Az adó legfeljebb négy tizedesjegyet tartalmazhat.')
            value=float(amount)
        elif key=='fuel_block_id':
            if isinstance(value,bool) or value not in FUEL_BLOCKS:raise PlanningError('Ismeretlen Fuel Block típus.')
        elif key=='fuel_block_price':
            if value is not None:
                price=decimal_number(value,'Fuel Block egységár',0,10**12)
                if price.as_tuple().exponent < -4:raise PlanningError('Az egységár legfeljebb négy tizedesjegyet tartalmazhat.')
                value=format(price,'f')
        elif value not in ['A I','A II','B I','B II','C I','C II']:raise PlanningError('Ismeretlen kristályváltozat.')
        result[key]=value
    return result


def validate_moon(data,catalog,existing):
    if not isinstance(data,dict) or set(data)-{'id','system_id','moon_id','structure','ores','notes','enabled','online_starts','rent_isk','other_cost_isk'}:
        raise PlanningError('Ismeretlen holdmező.')
    mid=integer(data.get('moon_id'),'Hold',2**53-1,1)
    sid=integer(data.get('system_id'),'Rendszer',2**53-1,1)
    if sid not in catalog.moon_systems:raise PlanningError('Válassz rendszert a találati listából.')
    if not any(m['id']==mid for m in catalog.moon_locations(sid)):raise PlanningError('A hold nem a kiválasztott rendszerben van.')
    structure=data.get('structure')
    if structure not in ['Athanor','Metenox']:raise PlanningError('Válassz Athanort vagy Metenoxot.')
    if structure=='Athanor' and catalog.moon_systems[sid]['security']>=.55:
        raise PlanningError('Athanor holdfúró csak 0.5 vagy alacsonyabb biztonsági besorolásnál működhet.')
    if structure=='Metenox' and catalog.moon_systems[sid]['security']>=.45:
        raise PlanningError('Metenox nem helyezhető el highsec rendszerben.')
    ores=data.get('ores')
    if not isinstance(ores,list) or not 1<=len(ores)<=4:raise PlanningError('Egy holdhoz 1–4 érc adható meg.')
    items=[];seen=set()
    for row in ores:
        if not isinstance(row,dict) or set(row)-{'id','percent'}:raise PlanningError('Hibás ércbeállítás.')
        tid=integer(row.get('id'),'Érc',2**31-1,1)
        if tid not in catalog.moon_ores or tid in seen:raise PlanningError('Ismeretlen vagy ismételt holdérc.')
        seen.add(tid)
        items.append({'id':tid,'percent':float(decimal_number(row.get('percent'),'Ércarány',.0001,100))})
    notes=data.get('notes','')
    if not isinstance(notes,str) or len(notes)>2000:raise PlanningError('A megjegyzés legfeljebb 2000 karakter lehet.')
    enabled=data.get('enabled',True)
    if not isinstance(enabled,bool):raise PlanningError('Hibás üzemállapot.')
    identifier=data.get('id')
    if identifier is not None and identifier not in {r['id'] for r in existing}:raise PlanningError('A szerkesztett hold már nem található.')
    previous=next((r for r in existing if r['id']==identifier),{})
    costs={key:format(decimal_number(data.get(key,previous.get(key,'0')),'Bérlet' if key=='rent_isk' else 'Egyéb holdköltség',0,10**15).quantize(Decimal('.01'),rounding=ROUND_HALF_UP),'f') for key in ['rent_isk','other_cost_isk']}
    return {**costs,'id':identifier or str(uuid.uuid4()),'system_id':sid,'moon_id':mid,'structure':structure,
            'ores':items,'notes':notes.strip(),'enabled':enabled,
            'online_starts':integer(data.get('online_starts',0),'Bekapcsolások',1000,0)}


def system_search(catalog,query):
    q=normalize(query.strip())[:100]
    if not q:return []
    rows=[s for s in catalog.moon_systems.values() if q in s['search']]
    rows.sort(key=lambda s:(s['search']!=q,not s['search'].startswith(q),s['search']))
    return [{k:s[k] for k in ['id','name','constellation','security']} for s in rows[:40]]


def public_resource(store,http,kind,item_id,force=False,now=None):
    now=time.time() if now is None else now
    old=store.universe_cached(kind,item_id)
    if old and not force and old['fetched']+CACHE_SECONDS>now:return old
    headers={'If-None-Match':old['etag']} if old and old.get('etag') else {}
    data,h=http.request(f'{ESI}/universe/{kind}/{item_id}/',headers=headers)
    if data is None:
        if not old:raise EsiError('Az EVE rendszeradata hiányos.')
        data=old['data']
    if not isinstance(data,dict):raise EsiError('Az EVE rendszeradata hiányos.')
    store.save_universe_cache(kind,item_id,data,now,h.get('ETag') or h.get('Etag') or (old or {}).get('etag'))
    return store.universe_cached(kind,item_id)


def system_info(store,catalog,http,sid,force=False):
    sid=integer(sid,'Rendszer',2**53-1,1)
    with catalog.lock:
        if sid not in catalog.moon_systems:raise PlanningError('Ismeretlen rendszer.')
        system=dict(catalog.moon_systems[sid]);locations=catalog.moon_locations(sid)
    status='sde';error=None;checked=None
    try:
        s=public_resource(store,http,'systems',sid,force)
        cid=s['data'].get('constellation_id')
        if not isinstance(cid,int):raise EsiError('Az EVE rendszeradata hiányos.')
        c=public_resource(store,http,'constellations',cid,force)
        if not isinstance(c['data'].get('name'),str):raise EsiError('Az EVE csillagképadata hiányos.')
        system.update(name=s['data'].get('name',system['name']),constellation_id=cid,
                      constellation=c['data']['name'],security=s['data'].get('security_status',system['security']))
        status='esi';checked=min(s['fetched'],c['fetched'])
    except EsiError as exc:
        error=str(exc)
        s=store.universe_cached('systems',sid)
        c=store.universe_cached('constellations',(s or {}).get('data',{}).get('constellation_id')) if s else None
        if s and c:
            system.update(name=s['data']['name'],constellation_id=c['id'],constellation=c['data']['name'],
                          security=s['data'].get('security_status',system['security']))
            checked=min(s['fetched'],c['fetched']);status='stale'
    return {'system':system,'source':status,'checked':checked,'error':error,'moons':locations}


def refresh_universe(store,catalog,http):
    results=[]
    for sid in sorted({r['system_id'] for r in store.moon_records()}):
        data=system_info(store,catalog,http,sid,True)
        results.append({'ok':not data['error'],'id':sid,'error':data['error']})
    return results


def reprocessing_yield(rules,settings):
    return D(rules['rig_base'])*(1+D(rules['tatara_bonus'])/100)*D(rules['rig_nullsec'])*D('1.15')*D('1.10')*D('1.10')*(1+D(settings['implant'])/100)


def composition_state(ores):
    total=sum((D(o['percent']) for o in ores),D(0))
    return total,('invalid' if total>D('100.02') else 'partial' if total<D('99.98') else 'ok')


def dashboard(store,catalog):
    prefs=preferences(store);rules=catalog.moon_rules
    if not rules:raise PlanningError('A holdadatokhoz frissítsd az EVE-receptadatbázist.')
    refining=reprocessing_yield(rules,prefs)
    records=store.moon_records();moons=[];totals=defaultdict(lambda:defaultdict(int));crystal_totals={}
    fuel_totals={k:{'fuel':0,'gas':0,'online_fuel':0,'count':0} for k in ['Athanor','Metenox','all']}
    for record in records:
        s=dict(catalog.moon_systems[record['system_id']])
        cache=store.universe_cached('systems',s['id']);const=None
        if cache:const=store.universe_cached('constellations',cache['data'].get('constellation_id'))
        if cache and const:s.update(constellation=const['data']['name'],constellation_id=const['id'])
        name=next((m['name'] for m in catalog.moon_locations(s['id']) if m['id']==record['moon_id']),str(record['moon_id']))
        total,status=composition_state(record['ores']);valid=status!='invalid';active=record['enabled'];structure=record['structure']
        factor=refining*D(prefs['mining_recovery'])/100 if structure=='Athanor' else D(rules['metenox']['miningEfficiency'])
        ores=[];outputs=defaultdict(int);crystals={}
        for o in record['ores']:
            ore=catalog.moon_ores[o['id']];volume=D(rules['extraction_m3_hour'])*720*D(o['percent'])/100
            # Athanor projection: collect all listed ore (or the configured recovery),
            # then reprocess each full portion, floor each material, carry no leftovers
            # between separate moons. Metenox refines on its exported hourly tick.
            period_hours=D(rules['metenox']['miningCycleTime'])/3600
            units=volume/D(ore['volume'])
            portions=(units*(D(prefs['mining_recovery'])/100)/D(ore['portion'])).to_integral_value(rounding=ROUND_FLOOR)
            produced=[]
            for material in ore['materials']:
                # Metenox yields moon materials only, not the standard minerals
                # present in R4 reprocessing (e.g. Pyerite and Mexallon).
                if structure=='Metenox' and catalog.types.get(material['id'],{}).get('group_id')!=427:continue
                if structure=='Metenox':
                    per_tick=volume/720*period_hours/D(ore['volume'])/D(ore['portion'])*D(material['quantity'])*factor
                    quantity=int(per_tick.to_integral_value(rounding=ROUND_FLOOR))*int(D(720)/period_hours)
                else:
                    quantity=int((portions*D(material['quantity'])*refining).to_integral_value(rounding=ROUND_FLOOR))
                if not active or not valid:quantity=0
                outputs[material['id']]+=quantity
                produced.append({**material,'quantity':quantity})
            ores.append({**ore,'percent':o['percent'],'volume':float(volume) if active and valid else None,
                         'units':int(units) if active and valid else None,'outputs':produced})
            if structure=='Athanor':
                crystal=next((c for c in catalog.moon_crystals.values() if c['skill_id']==ore['skill_id'] and c['variant']==prefs['crystal_variant']),None)
                if crystal:
                    item=crystals.setdefault(crystal['id'],{'id':crystal['id'],'name':crystal['name'],'rarity':ore['rarity'],'percent':0,'volume':0,'ores':[]})
                    item['percent']+=o['percent'];item['volume']+=float(volume) if active and valid else 0;item['ores'].append(ore['name'])
        crystal_rows=[]
        for c in crystals.values():
            c['share']=float(D(c['percent'])/total*100) if valid and total and active else None
            c['volume']=c['volume'] if valid and active else None
            crystal_rows.append(c)
            if valid and active:
                a=crystal_totals.setdefault(c['id'],{'id':c['id'],'name':c['name'],'rarity':c['rarity'],'volume':0})
                a['volume']+=c['volume']
        out=[{'id':tid,'name':catalog.name(tid),'quantity':amount} for tid,amount in outputs.items()]
        for row in out:
            if valid and active:
                totals[structure][row['id']]+=row['quantity'];totals['all'][row['id']]+=row['quantity']
        # Onlining is explicit; do not charge it every month by default. Other
        # service modules and Tatara fuel are outside this moon-drill budget.
        fuel=int(D(rules['athanor_fuel_hour' if structure=='Athanor' else 'metenox_fuel_hour'])*720) if active else 0
        gas=int(D(rules['metenox']['reagentsConsumedPerCycle'])*D(720)*3600/D(rules['metenox']['miningCycleTime'])) if active and structure=='Metenox' else 0
        online=int(rules['athanor_online_fuel' if structure=='Athanor' else 'metenox_online_fuel'])*record.get('online_starts',0)
        for group in [structure,'all']:
            fuel_totals[group]['fuel']+=fuel;fuel_totals[group]['gas']+=gas;fuel_totals[group]['online_fuel']+=online;fuel_totals[group]['count']+=int(active)
        moons.append({**record,'name':name,'system':s,'esi_checked':min(cache['fetched'],const['fetched']) if cache and const else None,
                      'percent_total':float(total),'status':status,'included':valid and active,'ores':ores,'outputs':out,'crystals':crystal_rows,
                      'fuel':fuel,'gas':gas,'online_fuel':online,'refining_yield':float(factor)})
    total_volume=sum(c['volume'] for c in crystal_totals.values())
    for c in crystal_totals.values():c['share']=c['volume']/total_volume*100 if total_volume else 0
    return {'moons':moons,'settings':prefs,'rules':rules,'refining_yield':float(refining),
            'ores':sorted(catalog.moon_ores.values(),key=lambda o:(o['rarity'],o['name'])),
            'fuel_blocks':[{'id':tid,'name':catalog.name(tid)} for tid in FUEL_BLOCKS],
            'magmatic_gas':{'id':MAGMATIC_GAS,'name':catalog.name(MAGMATIC_GAS)},
            'crystal_variants':['A I','A II','B I','B II','C I','C II'],
            'totals':{k:[{'id':tid,'name':catalog.name(tid),'quantity':v} for tid,v in sorted(totals[k].items(),key=lambda r:catalog.name(r[0]))] for k in ['Athanor','Metenox','all']},
            'consumption':fuel_totals,'crystals':sorted(crystal_totals.values(),key=lambda c:c['rarity']),
            'summary':{'count':len(moons),'invalid':sum(m['status']=='invalid' for m in moons),'partial':sum(m['status']=='partial' for m in moons),
                       'included':sum(m['included'] for m in moons)},'sources':SOURCES,'sde':catalog.moon_meta}
