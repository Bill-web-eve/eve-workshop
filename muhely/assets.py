"""Read-only asset browsing, independent of production filters and reservations."""
import time
from collections import defaultdict

from .planner import PlanningError


def root_locations(assets):
    parents={a['item_id']:a['location_id'] for a in assets}
    resolved={}
    for start in parents:
        trail=[];seen=set();location=start
        while location in parents and location not in resolved and location not in seen:
            seen.add(location);trail.append(location);location=parents[location]
        if location in resolved:location=resolved[location]
        if location in seen:location=None
        for item in trail:resolved[item]=location
    return resolved


def dashboard(store,catalog,corporation_id=None,now=None):
    now=time.time() if now is None else now
    if corporation_id is None:
        owners=[{'id':c['id'],'name':c['name'],'error':c.get('error'),
                 'snapshot':store.snapshot(c['id'],'assets')} for c in store.characters()]
    else:
        corp=store.corporation(corporation_id)
        if not corp:raise PlanningError('Ismeretlen corporation. Előbb frissítsd a corp-adatokat.')
        owners=[{'id':corp['id'],'name':corp['name'],'error':corp.get('error'),
                 'snapshot':store.corporation_snapshot(corporation_id,'assets')}]
    rows=[];sources=[]
    for owner in owners:
        snapshot=owner['snapshot']
        sources.append({'id':owner['id'],'name':owner['name'],'available':snapshot is not None,
                        'fetched':snapshot['fetched'] if snapshot else None,
                        'stale':bool(snapshot and (snapshot['expires']<=now or owner['error'])),
                        'error':owner['error']})
        if not snapshot:continue
        assets=snapshot['data'];locations=root_locations(assets);grouped=defaultdict(int);seen=set()
        for asset in assets:
            # Every asset is visible, including assembled items and blueprints.
            # Never apply production overrides or add future job output here.
            if asset['item_id'] in seen:continue
            seen.add(asset['item_id'])
            quantity=max(0,asset['quantity'])
            if not quantity:continue
            state='blueprint_copy' if asset.get('is_blueprint_copy') else 'singleton' if asset.get('is_singleton') else 'packaged'
            key=(asset['type_id'],locations[asset['item_id']],asset.get('location_flag',''),state)
            grouped[key]+=quantity
        for (tid,location,flag,state),quantity in grouped.items():
            rows.append({'type_id':tid,'name':catalog.name(tid),'owner_id':owner['id'],'owner_name':owner['name'],
                         'location_id':location,'location_flag':flag,'state':state,'quantity':quantity})
    rows.sort(key=lambda r:(r['name'].casefold(),r['owner_name'].casefold(),r['location_id'] or 0,r['location_flag'],r['state']))
    return {'corporation_id':corporation_id,'sources':sources,'rows':rows,
            'type_count':len({r['type_id'] for r in rows}),'quantity':sum(r['quantity'] for r in rows),
            'calculated_at':now}
