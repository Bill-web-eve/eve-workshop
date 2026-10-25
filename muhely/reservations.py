"""Rebuild plan allocations against one stock snapshot, in reservation order."""
from collections import defaultdict
import hashlib,json,math,time

from .planner import PlanningError,AssetSnapshotPending


def allocate_plans(plans, calculate, calculate_saved=None):
    totals = defaultdict(lambda: {'stock': 0, 'wip': 0})
    by_plan = {}
    pending = []
    active = ordered_active(plans)
    for priority, saved in enumerate(active, 1):
        try:
            plan = calculate_saved(saved,totals) if calculate_saved else calculate(saved['product_id'], saved['quantity'], totals)
        except AssetSnapshotPending as error:
            raise AssetSnapshotPending(error.info['items'],error.info['retry_at'],saved['name']) from None
        except PlanningError as error:
            raise PlanningError(f"A(z) {saved['name']} mentett terv foglalása nem számolható: {error} "
                                'A Foglalások oldalon kikapcsolhatod a foglalását.') from None
        if plan.get('inventory_wait'):
            pending.append({**plan['inventory_wait'],'plan_name':saved['name']})
        items = []
        for row in plan['rows']:
            stock = row['used_stock']
            wip = row['used_wip']
            if stock or wip:
                items.append({'id': row['id'], 'name': row['name'], 'stock': stock, 'wip': wip})
                totals[row['id']]['stock'] += stock
                totals[row['id']]['wip'] += wip
        items.sort(key=lambda r: r['name'].casefold())
        blueprint_usage=plan.get('blueprint_usage',[])
        for usage in blueprint_usage:
            held=totals[usage['id']].setdefault('blueprint_runs',{})
            held[usage['item_id']]=held.get(usage['item_id'],0)+usage['runs']
        by_plan[saved['id']] = {'priority': priority, 'items': items,
                               'blueprint_usage':blueprint_usage,
                               'reserved_types': len(items)+len({u['id'] for u in blueprint_usage}), 'summary': plan['summary'],
                               'shopping': [{key: row[key] for key in ['id','name','category','required','used_stock','used_wip','buy','unit','copy_runs','note'] if key in row} for row in plan['shopping']]}
    return {'totals': dict(totals), 'by_plan': by_plan, 'active_count': len(active), 'pending':pending}


def except_owner(allocation, plan_id):
    own = allocation['by_plan'].get(plan_id, {})
    own_items = {r['id']: r for r in own.get('items', [])}
    own_blueprints={}
    for usage in own.get('blueprint_usage',[]):
        held=own_blueprints.setdefault(usage['id'],{})
        held[usage['item_id']]=held.get(usage['item_id'],0)+usage['runs']
    other = {}
    for tid, total in allocation['totals'].items():
        mine = own_items.get(tid, {})
        amounts = {key: total[key]-mine.get(key, 0) for key in ['stock', 'wip']}
        if total.get('blueprint_runs'):
            amounts['blueprint_runs']={item:used-own_blueprints.get(tid,{}).get(item,0) for item,used in total['blueprint_runs'].items()}
        if amounts['stock'] or amounts['wip'] or any(amounts.get('blueprint_runs',{}).values()):
            other[tid] = amounts
    return other, own_items


def pending_info(waits):
    items={}
    for wait in waits:
        for item in wait['items']:
            key=(item.get('character_id'),item['id'])
            if key not in items or item['completed_at']>items[key]['completed_at']:items[key]=item
    return {'items':list(items.values()),'retry_at':min(w['retry_at'] for w in waits),'plan_name':None}


def ordered_active(plans):
    return sorted((p for p in plans if p['reserve_active']),
                  key=lambda p:(p['reserved_at'] or p['created'],p['created'],p['id']))


def revision(plans,corporation_id=None):
    fields=('id','product_id','quantity','created','reserve_active','reserved_at','corporation_id','manufacturer_id')
    rows=[{k:p.get(k) for k in fields} for p in plans if p.get('corporation_id')==corporation_id]
    rows.sort(key=lambda p:p['id'])
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def reorder(plans,ids,corporation_id,expected):
    if expected!=revision(plans,corporation_id):raise PlanningError('A foglalások megváltoztak. Frissítsd a listát, majd próbáld újra.')
    pool=[p for p in plans if p.get('corporation_id')==corporation_id];active=ordered_active(pool)
    if not isinstance(ids,list) or len(ids)>10000 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids) or set(ids)!={p['id'] for p in active}:
        raise PlanningError('Az aktív foglalások teljes, ismétlés nélküli sorrendjét add meg a kiválasztott gyártási körből.')
    # Reuse the existing priority time slots. Make ties strictly ordered while
    # keeping every slot at or before now, so newly activated plans append.
    slots=sorted(float(p['reserved_at'] or p['created']) for p in active)
    if any(not math.isfinite(value) for value in slots):raise PlanningError('Hibás foglalási elsőbbség.')
    limit=time.time()
    for i in range(len(slots)-1,-1,-1):
        slots[i]=min(slots[i],limit);limit=math.nextafter(slots[i],-math.inf)
    values=dict(zip(ids,slots))
    return [{**p,'reserved_at':values[p['id']]} if p['id'] in values else p for p in plans]
