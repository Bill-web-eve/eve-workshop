"""Rebuild plan allocations against one stock snapshot, in reservation order."""
from collections import defaultdict

from .planner import PlanningError,AssetSnapshotPending


def allocate_plans(plans, calculate, calculate_saved=None):
    totals = defaultdict(lambda: {'stock': 0, 'wip': 0})
    by_plan = {}
    active = sorted((p for p in plans if p['reserve_active']),
                    key=lambda p: (p['reserved_at'] or p['created'], p['created'], p['id']))
    for priority, saved in enumerate(active, 1):
        try:
            plan = calculate_saved(saved,totals) if calculate_saved else calculate(saved['product_id'], saved['quantity'], totals)
        except AssetSnapshotPending as error:
            raise AssetSnapshotPending(error.info['items'],error.info['retry_at'],saved['name']) from None
        except PlanningError as error:
            raise PlanningError(f"A(z) {saved['name']} mentett terv foglalása nem számolható: {error} "
                                'A Mentett tervek oldalon feloldhatod a foglalását.') from None
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
    return {'totals': dict(totals), 'by_plan': by_plan, 'active_count': len(active)}


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
