"""Read-only input coverage and physical location annotations; never alter plans."""
from collections import defaultdict
from .assets import root_locations


def locations(store,settings,corporation_id=None,jobs=()):
    if settings['source']!='eve':return {}
    if corporation_id is not None:
        snap=store.corporation_snapshot(corporation_id,'assets');snapshots=[snap] if snap else []
    else:
        chars=[c for c in store.characters() if not settings['character_ids'] or c['id'] in settings['character_ids']]
        snapshots=[store.snapshot(c['id'],'assets') for c in chars if all(store.snapshot(c['id'],k) for k in ['assets','blueprints','jobs'])]
    assets=[a for s in snapshots if s for a in s['data']];roots=root_locations(assets)
    stock=defaultdict(lambda:defaultdict(int));wip=defaultdict(lambda:defaultdict(int));seen=set()
    for asset in assets:
        if asset['item_id'] in seen:continue
        seen.add(asset['item_id']);loc=roots.get(asset['item_id'])
        if settings['location_ids'] and loc not in settings['location_ids']:continue
        if not asset.get('is_singleton',False) and asset.get('quantity',0)>0:stock[asset['type_id']][loc]+=asset['quantity']
    for job in jobs:
        if job.get('expected_output',0)<=0:continue
        loc=job.get('output_location_id');loc=roots.get(loc,loc)
        wip[job['product_type_id']][loc]+=job['expected_output']
    return {'stock':dict(stock),'wip':dict(wip)}


class Pools:
    def __init__(self,plan,physical):
        self.budget={};self.places={}
        for row in plan['rows']:
            for source,used,held,manual in [('stock','used_stock','reserved','manual_stock'),('wip','used_wip','plan_wip_reserved','manual_wip')]:
                key=(source,row['id']);self.budget[key]=row.get(used,0)
                # Existing holds are quantities, not station allocations. Only
                # the guaranteed free lower bound at each station is known.
                self.places[key]={loc:max(0,n-row.get(held,0)) for loc,n in physical.get(source,{}).get(row['id'],{}).items()}
                if row.get(manual):self.places[key]={}

    def consume(self,source,tid,quantity,target):
        key=(source,tid);remaining=min(quantity,self.budget.get(key,0));taken=[]
        for loc in sorted(self.places.get(key,{}),key=lambda loc:(loc!=target,loc is None,loc or 0)):
            n=min(remaining,self.places[key][loc])
            if n:taken.append({'source':source,'quantity':n,'location_id':loc});self.places[key][loc]-=n;remaining-=n
            if not remaining:break
        if remaining:taken.append({'source':source,'quantity':remaining,'location_id':None})
        self.budget[key]=self.budget.get(key,0)-sum(a['quantity'] for a in taken)
        return taken


def describe(materials,target,targets=()):
    has_wip=any(a['source']=='wip' and a['quantity'] for m in materials for a in m['allocations'])
    missing=any(a['source'] not in ['stock','wip'] and a['quantity'] for m in materials for a in m['allocations'])
    wrong=any(a['location_id'] is not None and a['location_id']!=target for m in materials for a in m['allocations']) if target is not None else False
    unknown=target is None or any(a['location_id'] is None for m in materials for a in m['allocations'])
    state='missing' if missing else 'wip' if has_wip else 'stock'
    for m in materials:
        m.update(stock=sum(a['quantity'] for a in m['allocations'] if a['source']=='stock'),
                 wip=sum(a['quantity'] for a in m['allocations'] if a['source']=='wip'),
                 missing=sum(a['quantity'] for a in m['allocations'] if a['source'] not in ['stock','wip']))
    return {'status':state,'location_status':'transfer' if wrong else 'unknown' if unknown else 'local',
            'target_location_id':target,'blueprint_locations':list(targets),'has_wip':has_wip,
            'can_start_here':state=='stock' and not wrong and not unknown,'materials':materials}


def plan_targets(row,plan):
    params=row['parameters'];instances=params.get('instances',[])
    if params.get('source')=='manual':return []
    if params['kind']=='BPC':
        used={r['item_id'] for r in plan.get('blueprint_usage',[]) if r['id']==params['bp_id']}
        if params.get('available_runs') is not None and row['runs']>params['available_runs']:return []
        chosen=[b for b in instances if b['item_id'] in used]
    else:chosen=[b for b in instances if b['selected']]
    if not chosen or any(b.get('location_id') is None for b in chosen):return []
    return sorted({b['location_id'] for b in chosen})


def annotate_plan(plan,physical=None):
    pools=Pools(plan,physical or {})
    for row in plan['queue']:
        targets=plan_targets(row,plan);target=targets[0] if len(targets)==1 else None;inputs=[]
        for material in row['materials']:
            n=material['quantity'];alloc=[]
            for source in ['stock','wip']:
                part=pools.consume(source,material['id'],n-sum(a['quantity'] for a in alloc),target);alloc.extend(part)
            missing=n-sum(a['quantity'] for a in alloc)
            if missing:alloc.append({'source':'missing','quantity':missing,'location_id':None})
            inputs.append({**material,'allocations':alloc})
        row['input_readiness']=describe(inputs,target,targets)


def annotate_schedule(result,plan,context):
    pools=Pools(plan,context.get('material_locations',{}));blueprints={b['item_id']:b for b in context['blueprints']}
    def target(job):
        bp=blueprints.get(job.get('blueprint_item_id'),{})
        return bp.get('root_location_id',bp.get('location_id'))
    targets={j['id']:target(j) for j in result['jobs']}
    for job in result['jobs']:
        place=targets[job['id']];inputs=[]
        for material in job['materials']:
            alloc=[]
            for a in material['allocations']:
                source=a['source']
                if source in ['stock','wip']:
                    part=pools.consume(source,material['id'],a['quantity'],place);alloc.extend(part)
                    left=a['quantity']-sum(p['quantity'] for p in part)
                    if left:alloc.append({'source':source,'quantity':left,'location_id':None})
                else:alloc.append({'source':source,'quantity':a['quantity'],'location_id':targets.get(a.get('job_id')) if source=='job' else None})
            inputs.append({k:material[k] for k in ['id','name','quantity']}|{'allocations':alloc})
        job['input_readiness']=describe(inputs,place,[place] if place is not None else [])
