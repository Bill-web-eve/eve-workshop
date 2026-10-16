"""PI snapshot monitoring and route-constrained, finite-stock supply checks.

ESI does not advance a colony until it is opened in the game. These checks
therefore describe dated evidence, never an unconditional live simulation.
"""
from collections import defaultdict,deque
from datetime import datetime
import math
import time

from .esi import EsiError
from .pi_forecast import forecast

STORAGE_GROUPS={1027,1029,1030}


def stamp(value):
    if value is None:return None
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.tzinfo is None:raise ValueError()
        return result.timestamp()
    except (ValueError,TypeError,AttributeError,OverflowError):
        raise EsiError('Érvénytelen időpont az EVE PI-adataiban.') from None


def number(row,key,minimum=0,integer=True,optional=False):
    value=row.get(key)
    if value is None and optional:return
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<minimum or value>2**53-1 or (integer and int(value)!=value):
        raise EsiError('Hibás számadat az EVE PI-válaszában; a korábbi adatok megmaradtak.')


def validate_planets(data):
    if not isinstance(data,list) or len(data)>100:raise EsiError('Az EVE bolygólistája nem olvasható.')
    seen=set()
    for planet in data:
        if not isinstance(planet,dict):raise EsiError('Hibás bolygórekord.')
        for key in ['planet_id','solar_system_id','owner_id']:number(planet,key,1)
        for key in ['num_pins','upgrade_level']:number(planet,key)
        if planet['planet_id'] in seen:raise EsiError('Ismétlődő bolygó az EVE válaszában.')
        seen.add(planet['planet_id'])
        if not isinstance(planet.get('planet_type'),str) or stamp(planet.get('last_update')) is None:
            raise EsiError('Hiányos PI bolygóadat.')


def validate_layout(data):
    if not isinstance(data,dict) or any(not isinstance(data.get(k),list) for k in ['pins','links','routes']):
        raise EsiError('Az EVE kolóniaelrendezése nem olvasható.')
    if len(data['pins'])>1000 or len(data['routes'])>10000 or len(data['links'])>10000:
        raise EsiError('Váratlanul nagy PI-kolónia.')
    seen=set()
    for pin in data['pins']:
        if not isinstance(pin,dict):raise EsiError('Hibás PI-épület.')
        number(pin,'pin_id',1);number(pin,'type_id',1)
        if pin['pin_id'] in seen:raise EsiError('Ismétlődő PI-épület.')
        seen.add(pin['pin_id'])
        if not isinstance(pin.get('contents',[]),list):raise EsiError('Hibás PI-készlet.')
        for content in pin.get('contents',[]):
            if not isinstance(content,dict):raise EsiError('Hibás PI-készletrekord.')
            number(content,'type_id',1);number(content,'amount')
        for key in ['install_time','expiry_time','last_cycle_start']:stamp(pin.get(key))
        number(pin,'schematic_id',optional=True)
        factory=pin.get('factory_details')
        if factory is not None:
            if not isinstance(factory,dict):raise EsiError('Hibás gyáradat.')
            number(factory,'schematic_id')
        extractor=pin.get('extractor_details')
        if extractor is not None:
            if not isinstance(extractor,dict) or not isinstance(extractor.get('heads'),list):raise EsiError('Hibás kitermelőadat.')
            for key in ['cycle_time','product_type_id','qty_per_cycle']:number(extractor,key,optional=True)
    seen=set()
    for route in data['routes']:
        if not isinstance(route,dict):raise EsiError('Hibás PI-útvonal.')
        for key in ['route_id','source_pin_id','destination_pin_id','content_type_id']:number(route,key,1)
        number(route,'quantity',integer=False)
        if route['route_id'] in seen:raise EsiError('Ismétlődő PI-útvonal.')
        seen.add(route['route_id'])
        if not isinstance(route.get('waypoints',[]),list):raise EsiError('Hibás útvonalpontok.')
        for value in route.get('waypoints',[]):number({'id':value},'id',1)
    for link in data['links']:
        if not isinstance(link,dict):raise EsiError('Hibás PI-kapcsolat.')
        for key in ['source_pin_id','destination_pin_id']:number(link,key,1)
        number(link,'link_level')


def valid_routes(layout):
    ids={p['pin_id'] for p in layout['pins']}
    links={frozenset((l['source_pin_id'],l['destination_pin_id'])) for l in layout['links']}
    good=[];bad=[]
    for route in layout['routes']:
        path=[]
        for pin in [route['source_pin_id'],*route.get('waypoints',[]),route['destination_pin_id']]:
            if not path or path[-1]!=pin:path.append(pin)
        okay=len(path)>=2 and all(i in ids for i in path) and all(frozenset((a,b)) in links for a,b in zip(path,path[1:]))
        (good if okay and route['quantity']>=1 else bad).append(route)
    return good,bad


def maxflow(supply,demand,capacities,allocations=None):
    """Integer bipartite flow. Reassignment avoids greedy shared-stock errors."""
    source=('root',);sink=('sink',);edges=defaultdict(dict)
    def add(a,b,capacity):
        if capacity<=0:return
        edges[a][b]=edges[a].get(b,0)+int(capacity);edges[b].setdefault(a,0)
    for pin,quantity in supply.items():add(source,('stock',pin),quantity)
    for pin,quantity in demand.items():add(('factory',pin),sink,quantity)
    for (stock,factory),quantity in capacities.items():add(('stock',stock),('factory',factory),quantity)
    total=0
    while True:
        previous={source:None};queue=deque([source])
        while queue and sink not in previous:
            node=queue.popleft()
            for nxt,quantity in edges[node].items():
                if quantity>0 and nxt not in previous:previous[nxt]=node;queue.append(nxt)
        if sink not in previous:break
        amount=2**53-1;node=sink
        while previous[node] is not None:amount=min(amount,edges[previous[node]][node]);node=previous[node]
        node=sink
        while previous[node] is not None:
            parent=previous[node];edges[parent][node]-=amount;edges[node][parent]+=amount;node=parent
        total+=amount
    missing={pin:edges.get(('factory',pin),{}).get(sink,0) for pin in demand}
    # Flag all competing factories in an underfunded connected stock pool,
    # instead of pretending the arbitrary flow order is the game's priority.
    neighbors=defaultdict(set)
    for (a,b),quantity in capacities.items():
        if quantity>0 and supply.get(a,0)>0:
            x=('stock',a);y=('factory',b);neighbors[x].add(y);neighbors[y].add(x)
    affected=set()
    for pin,quantity in missing.items():
        if not quantity:continue
        seen={('factory',pin)};pending=list(seen)
        while pending:
            node=pending.pop()
            for nxt in neighbors[node]-seen:seen.add(nxt);pending.append(nxt)
        affected.update(node[1] for node in seen if node[0]=='factory')
    if allocations is not None:
        allocations.update({(a,b):edges.get(('factory',b),{}).get(('stock',a),0) for a,b in capacities})
    return total,affected


class Supply:
    def __init__(self,pins,factories,routes,catalog):
        self.pins=pins;self.factories=factories;self.routes=routes;self.catalog=catalog;self.cache={}
        self.contents={p['pin_id']:defaultdict(int) for p in pins}
        self.storage=set()
        for pin in pins:
            if catalog.pi_types.get(pin['type_id'],{}).get('group_id') in STORAGE_GROUPS:self.storage.add(pin['pin_id'])
            for row in pin.get('contents',[]):self.contents[pin['pin_id']][row['type_id']]+=int(row['amount'])

    def check(self,seconds):
        cycles={f['id']:max(1,math.ceil(seconds/f['recipe']['cycle_time'])) for f in self.factories}
        key=tuple(cycles.values())
        if key in self.cache:return self.cache[key]
        materials=sorted({tid for f in self.factories for tid in f['recipe']['inputs']})
        rows=[];affected=defaultdict(list)
        for tid in materials:
            total_need=0;own=0;demand={}
            for f in self.factories:
                need=f['recipe']['inputs'].get(tid,0)*cycles[f['id']]
                if not need:continue
                total_need+=need;buffer=min(need,self.contents[f['id']].get(tid,0));own+=buffer
                if need>buffer:demand[f['id']]=need-buffer
            supply={pid:stock[tid] for pid,stock in self.contents.items() if pid in self.storage and stock.get(tid,0)>0}
            capacities=defaultdict(int)
            for route in self.routes:
                if route['content_type_id']==tid and route['source_pin_id'] in supply and route['destination_pin_id'] in demand:
                    capacities[route['source_pin_id'],route['destination_pin_id']]+=int(route['quantity'])*cycles[route['destination_pin_id']]
            routed,blocked=maxflow(supply,demand,capacities)
            for pid in blocked:affected[pid].append(tid)
            total_stock=sum(stock.get(tid,0) for stock in self.contents.values())
            rows.append({'id':tid,'name':self.catalog.name(tid),'required':total_need,'on_planet':total_stock,
                         'buffer_used':own,'routed_used':routed,'usable':own+routed,
                         'missing':total_need-own-routed})
        result={'materials':rows,'affected':dict(affected),'enough':not any(r['missing'] for r in rows)}
        self.cache[key]=result;return result

    def coverage(self):
        if not self.factories:return None
        if not self.check(1)['enough']:return 0
        rates=defaultdict(float)
        for f in self.factories:
            for tid,quantity in f['recipe']['inputs'].items():rates[tid]+=quantity/f['recipe']['cycle_time']
        upper=min((sum(s.get(tid,0) for s in self.contents.values())/rate for tid,rate in rates.items()),default=0)
        maximum=30*86400;lo=0;hi=min(maximum,math.ceil(upper)+max(f['recipe']['cycle_time'] for f in self.factories))
        while lo<hi:
            middle=(lo+hi+1)//2
            if self.check(middle)['enough']:lo=middle
            else:hi=middle-1
        return lo


def colony_view(record,catalog,now,hours):
    planet,layout=record['planet'],record['layout']
    validate_planets([planet]);validate_layout(layout)
    pid=planet['planet_id'];metadata=catalog.pi_planets.get(pid,{})
    pins=layout['pins'];by_id={p['pin_id']:p for p in pins}
    routes,bad_routes=valid_routes(layout)
    updated=stamp(planet['last_update']);state_age=max(0,now-updated)
    messages=[];factories=[];extractors=[];unassigned=[];unknown_recipes=[];storages=[]
    for pin in pins:
        info=catalog.pi_types.get(pin['type_id'],{})
        group=info.get('group_id',catalog.types.get(pin['type_id'],{}).get('group_id'))
        base={'id':pin['pin_id'],'type_id':pin['type_id'],'name':catalog.name(pin['type_id'])}
        if group==1028 or pin.get('factory_details') or pin.get('schematic_id'):
            sid=(pin.get('factory_details') or {}).get('schematic_id') or pin.get('schematic_id',0)
            conflict=pin.get('schematic_id') and (pin.get('factory_details') or {}).get('schematic_id') and pin['schematic_id']!=pin['factory_details']['schematic_id']
            recipe=None if conflict else catalog.pi_schematics.get(sid)
            if not sid:
                unassigned.append({**base,'label':'Nincs beállított recept'});continue
            if not recipe or pin['type_id'] not in recipe['pins']:
                unknown_recipes.append({**base,'schematic_id':sid,'label':'A recept nem ellenőrizhető'});continue
            last=stamp(pin.get('last_cycle_start'))
            running=last is not None and last<=now<last+recipe['cycle_time']
            output_routes=[r for r in routes if r['source_pin_id']==pin['pin_id'] and r['content_type_id'] in recipe['outputs']]
            factories.append({**base,'schematic_id':sid,'product':recipe['name'],'recipe':recipe,
                'cycle_time':recipe['cycle_time'],'last_cycle_start':last,
                'cycle_end':last+recipe['cycle_time'] if last is not None else None,
                'running_evidence':running,'output_routed':bool(output_routes)})
        elif group==1063 or pin.get('extractor_details') is not None:
            detail=pin.get('extractor_details') or {};start=stamp(pin.get('install_time'));end=stamp(pin.get('expiry_time'))
            product=detail.get('product_type_id');heads=len(detail.get('heads',[]));cycle=detail.get('cycle_time')
            program=bool(end is not None and end>now and start is not None and start<=now and product and heads and cycle and detail.get('qty_per_cycle',0)>0)
            routed=any(r['source_pin_id']==pin['pin_id'] and r['content_type_id']==product for r in routes)
            label='Program aktív' if program and routed else 'Kimeneti útvonal hiányzik' if program else \
                  'A program lejárt' if end is not None and end<=now else 'Nincs aktív kitermelőprogram'
            extractors.append({**base,'product_id':product,'product':catalog.name(product) if product else '–',
                'heads':heads,'cycle_time':cycle,'qty_per_cycle':detail.get('qty_per_cycle'),'program_start':start,'program_end':end,
                'program_duration':end-start if start is not None and end is not None and end>=start else None,
                'cycles_remaining':max(0,math.floor((end-start)/cycle)-math.floor(max(0,now-start)/cycle)) if start is not None and end is not None and cycle and end>=start else None,
                'seconds_left':max(0,end-now) if end is not None else None,
                'active':program and routed,'program_active':program,'output_routed':routed,'label':label})
        if group in STORAGE_GROUPS:
            capacity=info.get('capacity');used=0;known=True
            for item in pin.get('contents',[]):
                volume=catalog.pi_types.get(item['type_id'],{}).get('volume')
                if volume is None:known=False
                else:used+=item['amount']*volume
            full=bool(known and capacity and used>=capacity-1e-6)
            storages.append({**base,'capacity':capacity,'used':used if known else None,'full':full,
                'contents':[{'id':r['type_id'],'name':catalog.name(r['type_id']),'amount':r['amount']} for r in pin.get('contents',[])]})
    supply=Supply(pins,factories,routes,catalog);next_cycle=supply.check(1);period=supply.check(hours*3600)
    coverage=supply.coverage()
    valid=not unknown_recipes and planet['num_pins']==len(pins) and not bad_routes
    stored_projection=forecast(pins,factories,routes,catalog,updated,now,hours,valid=valid)
    projection=forecast(pins,factories,routes,catalog,updated,now,hours,valid=valid,extractors=extractors) if extractors else stored_projection
    projection['stock_only_first_stop']=stored_projection['first_stop']
    projection['stock_only_seconds_left']=stored_projection['seconds_left']
    for f in projection['factories']:
        f['stock_stop']=next((r['expected_stop'] for r in stored_projection['factories'] if r['id']==f['id']),None)
    factory_by_id={f['id']:f for f in factories};factory_outputs={f['id']:set(f['recipe']['outputs']) for f in factories}
    factory_inputs={f['id']:set(f['recipe']['inputs']) for f in factories}
    extractor_by_id={e['id']:e for e in extractors}
    def providers(tid,target):
        result=[];seen={target};pending=[target]
        while pending:
            dest=pending.pop()
            for route in routes:
                if route['destination_pin_id']!=dest or route['content_type_id']!=tid:continue
                source=route['source_pin_id']
                if source in seen:continue
                seen.add(source)
                if source in extractor_by_id:
                    if extractor_by_id[source]['active'] and extractor_by_id[source]['product_id']==tid:result.append(source)
                elif source in factory_by_id:
                    if tid in factory_outputs[source]:result.append(source)
                elif source in supply.storage:pending.append(source)
        return result
    for factory in factories:
        missing=next_cycle['affected'].get(factory['id'],[])
        replenishment=bool(missing and all(providers(tid,factory['id']) for tid in missing))
        factory['supply_status']='incoming' if replenishment else 'shortage' if missing else 'ready'
        factory['supply_label']='Termeléstől / kitermeléstől függ' if replenishment else 'Készlethiány vagy útvonalhiány' if missing else 'Következő ciklus fedezett'
        factory['missing_materials']=[{'id':tid,'name':catalog.name(tid)} for tid in missing]
        factory['inputs']=[{'id':tid,'name':catalog.name(tid),'per_cycle':quantity,
                           'buffer':supply.contents[factory['id']].get(tid,0),
                           'suppliers':providers(tid,factory['id'])} for tid,quantity in factory['recipe']['inputs'].items()]
        factory['outputs']=[{'id':tid,'name':catalog.name(tid),'per_cycle':quantity} for tid,quantity in factory['recipe']['outputs'].items()]
        # Trace extractor dependencies through storage and intermediate factories.
        seen=set();pending=[(factory['id'],tid) for tid in factory_inputs[factory['id']]];extractor_sources=set()
        while pending:
            dest,tid=pending.pop()
            if (dest,tid) in seen:continue
            seen.add((dest,tid))
            for r in routes:
                if r['destination_pin_id']!=dest or r['content_type_id']!=tid:continue
                source=r['source_pin_id']
                if source in extractor_by_id and extractor_by_id[source]['product_id']==tid:extractor_sources.add(source)
                elif source in supply.storage:pending.append((source,tid))
                elif source in factory_by_id and tid in factory_outputs[source]:pending.extend((source,material) for material in factory_inputs[source])
        factory['extractor_sources']=sorted(extractor_sources)
        factory['projection']=next((f for f in projection['factories'] if f['id']==factory['id']),None)
        factory.pop('recipe')
    active=sum(e['active'] for e in extractors)+sum(f['running_evidence'] and f['output_routed'] for f in factories)
    stopped_extractors=sum(not e['active'] for e in extractors)
    unfed=sum(f['supply_status']=='shortage' and not f['running_evidence'] for f in factories)
    missing_outputs=sum(not f['output_routed'] for f in factories)
    if stopped_extractors:messages.append(f'{stopped_extractors} kitermelőnek nincs működő programja vagy kimeneti útvonala a betöltött adatok szerint.')
    if missing_outputs:messages.append(f'{missing_outputs} gyárhoz nincs érvényes termékkimeneti útvonal.')
    if unassigned:messages.append(f'{len(unassigned)} gyárban nincs beállított recept.')
    if unknown_recipes:messages.append(f'{len(unknown_recipes)} gyár receptje nem ellenőrizhető az adatcsomagból.')
    if not next_cycle['enough']:messages.append('A tárolt és útvonalon elérhető készlet nem fedezi az összes gyár következő ciklusát. Egyes gyárak további termelésre várhatnak.')
    elif not period['enough']:messages.append(f'A tárolt készlet nem fedez {hours} óra folyamatos gyártást.')
    if any(s['full'] for s in storages):messages.append('Van tele tároló; a kimenetek elhelyezését ellenőrizni kell.')
    if bad_routes:messages.append(f'{len(bad_routes)} útvonal hiányos kapcsolatra, hibás célra vagy nulla mennyiségre mutat.')
    if any(e['active'] and e['seconds_left']<=hours*3600 for e in extractors):messages.append(f'Kitermelőprogram jár le a következő {hours} órában.')
    if not factories and not extractors and not unassigned and not unknown_recipes:messages.append('A betöltött kolónián nincs termelőépület.')
    if factories and not any(f['running_evidence'] for f in factories):messages.append('Az időbélyegekből jelenleg futó gyári ciklus nem igazolható.')
    status='alert' if not active and (stopped_extractors or unfed or missing_outputs or unassigned or not (factories or extractors)) else 'warning' if messages else 'ok'
    state_old=bool(factories or unassigned or unknown_recipes) and state_age>1800
    inconsistent=planet['num_pins']!=len(pins)
    if state_old:messages.insert(0,'A gyárak kolóniaállapota 30 percnél régebbi. Nyisd meg a bolygót a játékban, majd frissíts: a készletjelzések korábbi pillanatképre vonatkoznak.')
    if inconsistent:messages.insert(0,'A bolygólista és az elrendezés épületszáma eltér; újabb, egyező adat szükséges.')
    if state_old or inconsistent or unknown_recipes:status='unknown'
    return {'id':pid,'name':metadata.get('name',f'Bolygó {pid}'),'system':catalog.pi_systems.get(planet['solar_system_id'],str(planet['solar_system_id'])),
            'system_id':planet['solar_system_id'],'type':planet['planet_type'],'upgrade_level':planet['upgrade_level'],'pin_count':len(pins),
            'last_update':updated,'layout_checked_at':record.get('layout_checked_at'),
            'state_old':state_old,'status':status,'alerts':messages,'extractors':extractors,'factories':factories,
            'unassigned':unassigned,'unknown_recipes':unknown_recipes,'storages':storages,
            'active_signals':active,'next_enough':next_cycle['enough'] if not unknown_recipes else None,
            'next_materials':next_cycle['materials'],'horizon_hours':hours,'period_enough':period['enough'] if not unknown_recipes else None,
            'period_materials':period['materials'],'stock_coverage_seconds':coverage,'bad_routes':len(bad_routes),'projection':projection}


def dashboard(store,catalog,hours=24,now=None):
    if hours not in [1,6,24,72]:raise EsiError('A PI-ellátás időtávja 1, 6, 24 vagy 72 óra lehet.')
    now=time.time() if now is None else now
    characters=[];colonies=[]
    for char,snapshot,status in store.pi_records():
        needs_auth=bool((status or {}).get('needs_auth',status is None));error=(status or {}).get('error')
        stale=bool(snapshot and now-snapshot['fetched']>1200)
        item={'id':char['id'],'name':char['name'],'needs_auth':needs_auth,'error':error,
              'checked_at':snapshot['fetched'] if snapshot else None,'expires':snapshot['expires'] if snapshot else None,'stale':stale,'planet_count':None}
        character_colonies=[]
        if snapshot:
            raw=snapshot['data'].get('colonies') if isinstance(snapshot['data'],dict) else None
            if not isinstance(raw,list):item['error']='A korábbi PI-adat nem olvasható.'
            else:
                item['planet_count']=len(raw)
                for record in raw:
                    try:colony=colony_view(record,catalog,now,hours)
                    except (EsiError,KeyError,TypeError,ValueError):
                        item['error']='Az egyik korábbi kolónia adata nem ellenőrizhető.';continue
                    colony.update(character_id=char['id'],character_name=char['name'],checked_at=snapshot['fetched'])
                    character_colonies.append(colony)
        for colony in character_colonies:
            colony['cached']=bool(needs_auth or item['error'] or stale)
            if colony['cached']:
                colony['status']='unknown';colony['alerts'].insert(0,'A PI-lekérés nem friss vagy engedélyezést igényel; korábbi adatok láthatók.')
            colonies.append(colony)
        item['status']='unknown' if needs_auth or item['error'] or stale or not snapshot else 'loaded'
        characters.append(item)
    order={'alert':0,'warning':1,'unknown':2,'ok':3}
    colonies.sort(key=lambda c:(order[c['status']],c['character_name'].casefold(),c['name']))
    return {'characters':characters,'colonies':colonies,'horizon_hours':hours,'calculated_at':now,
            'summary':{key:sum(c['status']==key for c in colonies) for key in order},
            'pi_sde':catalog.pi_meta}
