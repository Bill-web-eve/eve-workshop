from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import math
from .production import duration_skills


ACTIVE = {'active', 'paused', 'ready'}
ACTIVITIES = {1, 9}


class PlanningError(ValueError):
    pass


class AssetSnapshotPending(PlanningError):
    def __init__(self,items,retry_at,plan_name=None):
        self.info={'items':items,'retry_at':retry_at,'plan_name':plan_name}
        names=', '.join(sorted({item['name'] for item in items})[:5])
        prefix=f'A(z) {plan_name} terv készletfrissítésre vár. ' if plan_name else ''
        super().__init__(prefix+'Átvett jobok újabbak az EVE készletpillanatképénél: '+names+
            '. Az EVE gyorsítótárának lejártáig az ismételt frissítés ugyanazt az adatot adhatja. A foglalásaid megmaradnak.')



def integer(value, name, maximum=10**12, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value or not minimum <= value <= maximum:
        raise PlanningError(f'{name}: {minimum} és {maximum} közötti egész szám szükséges.')
    return int(value)


def decimal_number(value, name, minimum=0, maximum=100):
    try:
        n = Decimal(str(value))
    except Exception:
        raise PlanningError(f'{name}: szám szükséges.')
    if not n.is_finite() or not Decimal(str(minimum)) <= n <= Decimal(str(maximum)):
        raise PlanningError(f'{name}: {minimum} és {maximum} közötti szám szükséges.')
    return n


def material_for_batch(base, runs, factor):
    if not runs:
        return 0
    amount = (Decimal(base)*runs*factor).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    return max(runs, int(amount.to_integral_value(rounding=ROUND_CEILING)))


def batches(runs, batch_size, capacities=None, minimum=0, maximum=None):
    """Compressed job batches, split at each BPC's run boundary."""
    result = defaultdict(int)
    def add(n):
        if not n:return
        if minimum:
            cap=maximum or batch_size
            low=(n+cap-1)//cap;high=n//minimum
            if low<=high:
                count=max(low,min(high,(n+batch_size-1)//batch_size))
                size,extra=divmod(n,count)
                result[size+1]+=extra;result[size]+=count-extra
                return
        full,tail=divmod(n,batch_size);result[batch_size]+=full
        if tail:result[tail]+=1
    remaining = runs
    for capacity in capacities or []:
        n = min(remaining, max(0, capacity));add(n);remaining-=n
        if not remaining:break
    # Missing capacity remains a separately reported blueprint requirement.
    add(remaining)
    return [{'runs': n, 'count': count} for n, count in sorted(result.items(), reverse=True) if count]


def resolve_location(location_id, assets):
    seen = set()
    while location_id in assets:
        if location_id in seen:
            raise PlanningError('Körkörös konténerhivatkozás az assetadatokban.')
        seen.add(location_id)
        location_id = assets[location_id]['location_id']
    return location_id


def live_inventory(catalog, snapshots, locations=()):
    stock, wip = defaultdict(int), defaultdict(int)
    blueprints, jobs_out, location_set = [], [], set()
    seen_assets, seen_jobs, seen_bps = set(), set(), set()
    for snapshot in snapshots:
        assets = {int(a['item_id']): a for a in snapshot['assets']}
        for a in assets.values():
            location = resolve_location(a['location_id'], assets)
            location_set.add(location)
            if locations and location not in locations:
                continue
            if a['item_id'] not in seen_assets:
                seen_assets.add(a['item_id'])
                # Assembled ships/modules are in use, not production supplies.
                # Keep them in the location graph so packaged container contents
                # still resolve correctly. Blueprint ownership is read separately.
                if not a.get('is_singleton', False):
                    stock[int(a['type_id'])] += max(0, int(a.get('quantity', 0)))
        for bp in snapshot['blueprints']:
            location = resolve_location(bp['location_id'], assets)
            if locations and location not in locations:
                continue
            if bp['item_id'] not in seen_bps:
                blueprints.append({**bp, 'character_id': snapshot.get('character_id'), 'root_location_id': location})
                seen_bps.add(bp['item_id'])
        for job in snapshot['jobs']:
            if job['job_id'] in seen_jobs:
                continue
            seen_jobs.add(job['job_id'])
            type_id = job.get('product_type_id')
            recipe = catalog.recipes.get(type_id)
            expected_activity = 9 if recipe and recipe['activity'] == 'reaction' else 1
            eligible = job.get('activity_id') in ACTIVITIES and job.get('status') in ACTIVE
            if locations and job.get('output_location_id') not in locations:
                eligible = False
            # Also match blueprint/activity to the SDE recipe: invention's product
            # must never be mistaken for an actual ship or component.
            expected = 0
            if eligible and recipe and job.get('activity_id') == expected_activity and job.get('blueprint_type_id') == recipe['bp_id']:
                expected = int(job['runs'])*recipe['output']
                wip[type_id] += expected
            jobs_out.append({**job, 'name': catalog.name(type_id or 0), 'expected_output': expected,
                             'character_id': snapshot.get('character_id'),
                             'assets_as_of': snapshot.get('assets_as_of'),
                             'assets_expires': snapshot.get('assets_expires'),
                             'character_name': snapshot.get('character_name')})
    return stock, wip, blueprints, jobs_out, sorted(location_set)


class Planner:
    def __init__(self, catalog):
        self.catalog = catalog

    def calculate(self, product_id, quantity, settings, inventory=None, parameters=None,
                  stock=None, wip=None, blueprints=(), jobs=(), reservations=None, own_reservations=None,
                  skill_profiles=(), manufacturer_id=None):
        c = self.catalog
        product_id = integer(product_id, 'Termékazonosító', 10**9, 1)
        if product_id not in c.recipes:
            raise PlanningError('Ehhez a termékhez nincs gyártási vagy reakciórecept az adatbázisban.')
        quantity = integer(quantity, 'Célmennyiség', 10**8 if c.recipes[product_id]['activity']=='reaction' else 10**6, 1)
        inv, overrides = inventory or {}, parameters or {}
        stock, wip = stock or {}, wip or {}
        reservations, own_reservations = reservations or {}, own_reservations or {}
        graph, order, visiting = {}, [], set()
        def visit(tid):
            if tid in visiting:
                raise PlanningError('Körkörös receptlánc; ez a termék nem tervezhető.')
            if tid in graph:
                return
            if len(graph) > 4000:
                raise PlanningError('A receptlánc túl nagy.')
            visiting.add(tid)
            recipe = c.recipes.get(tid)
            # Fuel blocks are purchased inputs by default, as in the existing
            # spreadsheets. When selected as the target they are manufactured.
            default_mode = 'buy' if tid != product_id and c.types.get(tid, {}).get('group_id') == 1136 else 'build'
            building = recipe is not None and overrides.get(tid, {}).get('mode', default_mode) != 'buy'
            graph[tid] = recipe if building else None
            if building:
                for material in recipe['materials']:
                    visit(material['typeID'])
            visiting.remove(tid)
            order.append(tid)
        visit(product_id)
        # Reverse postorder processes every parent before any shared ingredient.
        # Thus shared demand is combined BEFORE stock and WIP are deducted once.
        demand, rows, stage = defaultdict(int), {}, {}
        blueprint_shortages,blueprint_usage=[],[]
        demand[product_id] = quantity
        bp_index = defaultdict(list)
        for bp in blueprints:
            bp_index[bp['type_id']].append(bp)
        busy = {j.get('blueprint_id') for j in jobs if j.get('status') in ACTIVE}
        for tid in reversed(order):
            recipe = graph[tid]
            required = demand[tid]
            if required > 2**53-1:
                raise PlanningError('A számított mennyiség túl nagy; csökkentsd a célmennyiséget.')
            local = inv.get(tid, {})
            on_hand = local.get('quantity')
            if on_hand is None:
                on_hand = int(stock.get(tid, 0))
            on_hand = integer(on_hand, 'Készlet')
            manual_reserved = integer(local.get('reserved', 0), 'Kézi foglalás')
            held = reservations.get(tid, {})
            plan_reserved = integer(held.get('stock', 0), 'Tervfoglalás')
            plan_wip_reserved = integer(held.get('wip', 0), 'Folyamatban kimenet foglalása')
            reserved = manual_reserved+plan_reserved
            available = max(0, on_hand-reserved)
            in_progress = local.get('wip')
            if in_progress is None:
                in_progress = int(wip.get(tid, 0))
            in_progress = integer(in_progress, 'Folyamatban')
            wip_total = in_progress
            in_progress = max(0, in_progress-plan_wip_reserved)
            used_stock = min(required, available)
            used_wip = min(max(0, required-used_stock), in_progress)
            missing = max(0, required-available-in_progress)
            warning = []
            if manual_reserved > on_hand:
                warning.append('A foglalás több a készletnél.')
            selected_recipe=recipe or c.recipes.get(tid)
            bp_holds=reservations.get(selected_recipe['bp_id'],{}).get('blueprint_runs',{}) if selected_recipe else {}
            params = self.parameters(selected_recipe, overrides.get(tid, {}), bp_index, busy,bp_holds)
            row = {'id': tid, 'name': c.name(tid), 'activity': recipe['activity'] if recipe else 'buy',
                   'required': required, 'on_hand': on_hand, 'available': available, 'reserved': reserved,
                   'manual_reserved': manual_reserved, 'plan_reserved': plan_reserved,
                   'plan_wip_reserved': plan_wip_reserved, 'wip_total': wip_total,
                   'own_reserved': own_reservations.get(tid, {}).get('stock', 0),
                   'own_wip_reserved': own_reservations.get(tid, {}).get('wip', 0),
                   'used_stock': used_stock, 'used_wip': used_wip,
                   'wip': in_progress, 'missing': missing, 'runs': 0, 'manufactured': 0, 'buy': 0,
                   'surplus': max(0, available+in_progress-required), 'seconds': 0,
                   'jobs': 0, 'batches': [], 'parameters': params,
                   'manual_stock': local.get('quantity') is not None, 'manual_wip': local.get('wip') is not None,
                   'warning': warning, 'materials': [],
                   'category': 'Vételre állított köztes' if c.recipes.get(tid) and not recipe else
                               'PI termék' if c.types.get(tid, {}).get('pi') else 'Alapanyag'}
            if recipe:
                runs = (missing+recipe['output']-1)//recipe['output']
                groups = batches(runs, params['job_runs'], params.get('capacities'),
                                 integer(overrides.get(tid,{}).get('_minimum_job_runs',0),'Minimum run/job'),
                                 integer(overrides.get(tid,{}).get('_maximum_job_runs',params['job_runs']),'Maximum run/job',minimum=1))
                facility = settings[recipe['activity']]
                factor = (1-Decimal(params['me'])/100)
                for key in ['material_role', 'material_rig']:
                    factor *= 1-decimal_number(facility[key], key, 0, 99)/100
                producer=duration_skills(recipe,c,skill_profiles,manufacturer_id)
                skill_factor=Decimal(str(producer['factor'])) if producer['factor'] is not None else decimal_number(facility['skill_time'], 'Skill időszorzó', .01, 1)
                row['producer']=producer
                time_factor = (1-Decimal(params['te'])/100)*skill_factor
                for key in ['time_role', 'time_rig']:
                    time_factor *= 1-decimal_number(facility[key], key, 0, 99)/100
                for material in recipe['materials']:
                    n = sum(material_for_batch(material['quantity'], g['runs'], factor)*g['count'] for g in groups)
                    mid = material['typeID']
                    demand[mid] += n
                    row['materials'].append({'id': mid, 'name': c.name(mid), 'quantity': n})
                row.update(runs=runs, manufactured=runs*recipe['output'],
                           surplus=max(0, available+in_progress+runs*recipe['output']-required),
                           seconds=float(runs*recipe['seconds']*time_factor),
                           jobs=sum(g['count'] for g in groups), batches=groups)
                if runs:
                    if producer['warning']:warning.append(producer['warning'])
                    remaining=runs
                    for source in params['run_sources']:
                        used=min(remaining,source['runs']);remaining-=used
                        if used:blueprint_usage.append({'id':params['bp_id'],'name':c.name(params['bp_id']),'item_id':source['item_id'],'runs':used})
                    if recipe['activity']=='reaction':
                        deficit=0 if params['bpo_count'] or params['bpc_count'] else 1
                        bp_required,bp_available,unit,category=1,1-deficit,'db','Reakcióformula'
                    else:
                        capacity=params['procurement_runs']
                        deficit=max(0,runs-capacity) if capacity is not None else 0
                        bp_required,bp_available,unit,category=runs,capacity or 0,'run','BPC-run'
                    if deficit:
                        blueprint_shortages.append({'id':params['bp_id'],'name':c.name(params['bp_id']),
                            'category':category,'unit':unit,'required':bp_required,'available':bp_available,
                            'on_hand':bp_available,'used_stock':min(bp_required,bp_available),'used_wip':0,
                            'wip':0,'buy':deficit,'missing':deficit,'product_id':tid,
                            'copy_runs':min(params['copy_limit'],max((b['runs'] or 0 for b in params['instances'] if b['kind']=='BPC'),default=0)) or params['copy_limit'],
                            'note':'Beszerzendő formula; nem másolható.' if unit=='db' else 'Hiányzó BPC-runkeret. Másolás, invention vagy beszerzés szükséges.'})
                    if params['source'] == 'manual':
                        warning.append('Kézi blueprintparaméterek; a blueprint megléte nincs igazolva.')
                    if params['available_runs'] is not None and runs > params['available_runs']:
                        warning.append(f"Kevés BPC-run: {params['available_runs']} elérhető, {runs} szükséges.")
                    if params['busy']:
                        warning.append('A kiválasztott blueprintcsoportban foglalt példány is van.')
                    if params['other_groups']:
                        warning.append('Más ME/TE-jű vagy eltérő fajtájú blueprint nincs beszámítva.')
            else:
                row['buy'] = missing
            rows[tid] = row
        for tid in order:
            recipe = graph[tid]
            stage[tid] = 1+max((stage[m['typeID']] for m in recipe['materials']), default=0) if recipe else 0
            rows[tid]['stage'] = stage[tid]
        queue = sorted((r for r in rows.values() if r['runs']), key=lambda r: (r['stage'], r['activity'] != 'reaction', normalize_name(r['name'])))
        blueprint_ids={recipe['bp_id'] for recipe in c.recipes.values()}
        for row in [*rows.values(),*blueprint_shortages]:row['is_blueprint']=row['id'] in blueprint_ids
        shopping = sorted([r for r in rows.values() if r['buy']]+blueprint_shortages, key=lambda r: (r['category'], normalize_name(r['name'])))
        return {'product_id': product_id, 'name': c.name(product_id), 'quantity': quantity,
                'activity':c.recipes[product_id]['activity'],'manufacturer_id':manufacturer_id,
                'blueprint_shortages':blueprint_shortages,'blueprint_usage':blueprint_usage,
                'queue': queue, 'shopping': shopping, 'rows': [rows[i] for i in reversed(order)],
                'summary': {'items': len(queue), 'runs': sum(r['runs'] for r in queue),
                            'jobs': sum(r['jobs'] for r in queue), 'seconds': sum(r['seconds'] for r in queue),
                            'shopping_items': len(shopping)},
                'sde': c.meta}

    def parameters(self, recipe, override, bp_index, busy,holds=None):
        if not recipe:
            return None
        owned = bp_index.get(recipe['bp_id'], [])
        holds=holds or {}
        def free_runs(bp):return max(0,int(bp.get('runs',0))-int(holds.get(bp['item_id'],holds.get(str(bp['item_id']),0))))
        def original(bp):
            return bp.get('quantity') == -1 or bp.get('runs') == -1
        def count(bp):
            # Negative ESI quantities identify single BPO/BPC items; positive
            # quantities represent a stack of packaged originals.
            return max(1, int(bp.get('quantity', 1)))
        copies = owned
        selected_id = override.get('item_id')
        if selected_id is not None:
            copies = [b for b in copies if b['item_id'] == selected_id]
            if not copies:
                raise PlanningError('A kiválasztott blueprintpéldány nincs a kiválasztott készletben.')
        usable = [b for b in copies if b.get('runs', -1) != 0]
        originals = [b for b in usable if original(b)]
        candidates = originals or [b for b in usable if free_runs(b)>0] or usable
        manual = override.get('source') == 'manual' or not candidates
        if manual:
            me = integer(override.get('me', 0), 'ME', 10)
            te = integer(override.get('te', 0), 'TE', 20)
            capacities, limit, kind, group = None, override.get('total_runs'), 'Kézi', []
            if limit is not None:
                limit = integer(limit, 'Összes run')
        else:
            best = max(candidates, key=lambda b: (b['material_efficiency'], b['time_efficiency']))
            me, te = int(best['material_efficiency']), int(best['time_efficiency'])
            group = [b for b in candidates if b['material_efficiency'] == me and b['time_efficiency'] == te]
            kind = 'BPO' if originals else 'BPC'
            capacities = sorted([free_runs(b) for b in group if free_runs(b)], reverse=True) if kind == 'BPC' else None
            limit = sum(capacities) if capacities is not None else None
        run_group=group if not manual else [b for b in copies if not original(b) and b['material_efficiency']==me and b['time_efficiency']==te]
        run_sources=[{'item_id':b['item_id'],'runs':free_runs(b)} for b in sorted(run_group,key=lambda b:(-free_runs(b),b['item_id'])) if not original(b)]
        if manual and limit is not None:
            limit=max(0,limit-int(holds.get(0,holds.get('0',0))))
            run_sources=[{'item_id':0,'runs':limit}]
        if originals:run_sources=[]
        procurement_runs=None if originals else sum(s['runs'] for s in run_sources)
        if recipe['activity'] == 'reaction':
            me = te = 0
        default_job_runs = min(100, max(capacities)) if capacities else min(100, recipe['copy_limit'])
        selected = {b['item_id'] for b in group}
        instances = [{'item_id': b['item_id'], 'kind': 'BPO' if original(b) else 'BPC',
                      'count': count(b), 'me': int(b['material_efficiency']), 'te': int(b['time_efficiency']),
                      'runs': None if original(b) else max(0, int(b['runs'])),
                      'selected': b['item_id'] in selected, 'busy': b['item_id'] in busy,
                      'character_id': b.get('character_id'),
                      'location_id': b.get('root_location_id', b.get('location_id'))} for b in owned]
        instances.sort(key=lambda b: (not b['selected'], b['kind'] != 'BPO', -b['me'], -b['te'], b['item_id']))
        return {'me': me, 'te': te, 'job_runs': integer(override.get('job_runs', default_job_runs), 'Run/job', 10**6, 1),
                'available_runs': limit, 'capacities': capacities, 'kind': kind,
                'procurement_runs':procurement_runs,'run_sources':run_sources,
                'source': 'manual' if manual else 'auto', 'group_count': sum(count(b) for b in group),
                'bpo_count': sum(count(b) for b in owned if original(b)),
                'bpc_count': sum(count(b) for b in owned if not original(b)),
                'bpc_runs': sum(max(0, int(b['runs']))*count(b) for b in owned if not original(b)),
                'instances': instances,
                'other_groups': len(copies) > len(group) if not manual else False,
                'busy': any(b['item_id'] in busy for b in group), 'bp_id': recipe['bp_id'],
                'output': recipe['output'], 'copy_limit': recipe['copy_limit']}


def normalize_name(s):
    return str(s).casefold()
