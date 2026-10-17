"""Dependency, material, character-slot and physical-blueprint list scheduling.

This is a deterministic heuristic, not a proof of a globally minimal makespan.
The returned material plan is recalculated for the actual batch sizes.
"""
import copy
import math
import time
from collections import defaultdict
from decimal import Decimal

from .accounts import load as account_tracking
from .extractions import stamp
from .planner import PlanningError, material_for_batch
from .production import duration_skills

MAX_JOBS=10000


def all_jobs(store):
    result={};checked={};seen_at={}
    for char in store.characters():
        snapshot=store.snapshot(char['id'],'jobs')
        checked[char['id']]=snapshot['fetched'] if snapshot else None
        for job in snapshot['data'] if snapshot else []:
            if snapshot['fetched']>=seen_at.get(job['job_id'],0):
                result[job['job_id']]={**job,'character_id':job.get('installer_id',char['id'])};seen_at[job['job_id']]=snapshot['fetched']
    for corp in store.corporations():
        snapshot=store.corporation_snapshot(corp['id'],'jobs')
        for job in snapshot['data'] if snapshot else []:
            if snapshot['fetched']>=seen_at.get(job['job_id'],0):
                result[job['job_id']]={**job,'character_id':job.get('installer_id')};seen_at[job['job_id']]=snapshot['fetched']
    return list(result.values()),checked


def release(job,now):
    if job['status']=='ready':return now
    if job['status']=='paused':return math.inf
    end=stamp(job.get('end_date'))
    return max(now,end) if end is not None else math.inf


def worker_profiles(context,store,jobs,checked,selected,now,reference_now=None):
    reference_now=now if reference_now is None else reference_now
    tracking=account_tracking(store);accounts={a['id']:a for a in tracking['accounts']}
    result=[]
    for profile in context['skill_profiles']:
        if selected is not None and profile['id'] not in selected:continue
        p={**profile,'slots':{},'capacity':{},'excluded':None,'until':None,'jobs_as_of':checked.get(profile['id'])}
        pref=tracking['characters'].get(str(p['id']),{});account=accounts.get(pref.get('account_id'))
        if not p['available']:p['excluded']='Nincs használható aktív skilladat.'
        elif p['stale']:p['excluded']='A skilladat elavult vagy hibás; frissítsd a skilleket.'
        elif not checked.get(p['id']):p['excluded']='A karakter saját ipari jobadata hiányzik; frissítsd az EVE-adatokat.'
        elif reference_now-checked[p['id']]>86400:p['excluded']='A karakter jobadata több mint egy napos; frissítsd az EVE-adatokat.'
        if account and account['omega_status']=='omega' and account['omega_expires']:
            p['until']=account['omega_expires']
            if p['until']<=now and (p['as_of'] or 0)<p['until']:p['excluded']='Az Omega lejárt; az aktív skilleket újra le kell kérni.'
            elif p['until']<=now:p['until']=None
        for activity,skills in [('manufacturing',(3387,24625)),('reaction',(45748,45749))]:
            count=1+sum(p['levels'].get(s,0) for s in skills)
            busy=sorted(release(j,now) for j in jobs if j.get('character_id')==p['id'] and j.get('activity_id')==(9 if activity=='reaction' else 1) and j.get('status') in ['active','paused','ready'])
            p['capacity'][activity]=count
            p['slots'][activity]=([now]*(count-len(busy))+busy) if len(busy)<count else busy[-count:]
        result.append(p)
    return result


def qualified(row,catalog,workers):
    result=[]
    for worker in workers:
        if worker['excluded']:continue
        producer=duration_skills(catalog.recipes[row['id']],catalog,workers,worker['id'])
        prerequisite=45746 if row['activity']=='reaction' else 3380
        if producer['status']!='verified' or worker['levels'].get(prerequisite,0)<1:continue
        result.append((worker,producer))
    return result


def blueprints(row,context,held,jobs,now,workers,transfer=False):
    params=row['parameters'];by_id=defaultdict(list)
    for job in jobs:
        if job.get('status') in ['active','paused','ready']:by_id[job.get('blueprint_id')].append(job)
    result=[]
    for bp in context['blueprints']:
        if bp['type_id']!=params['bp_id']:continue
        if row['activity']!='reaction' and (bp['material_efficiency']!=params['me'] or bp['time_efficiency']!=params['te']):continue
        original=bp.get('quantity')==-1 or bp.get('runs')==-1
        free=None if original else max(0,bp['runs']-int(held.get(bp['item_id'],held.get(str(bp['item_id']),0))))
        if free==0:continue
        for unit in range(min(max(1,bp.get('quantity',1)),sum(w['capacity'][row['activity']] for w in workers) or 1)):
            result.append({'key':f"{bp['item_id']}:{unit}",'item_id':bp['item_id'],'kind':'BPO' if original else 'BPC',
                           'remaining':free,'available':max([now]+[release(j,now) for j in by_id[bp['item_id']]]),
                           'owner':None if context['corporation_id'] or transfer else bp.get('character_id'),
                           'actual_owner':bp.get('character_id'),'virtual':False,'used':0})
    return result


class Materials:
    def __init__(self):self.items=defaultdict(list)
    def add(self,tid,quantity,when):
        if quantity>0 and math.isfinite(when):self.items[tid].append([when,quantity]);self.items[tid].sort()
    def ready(self,tid,quantity):
        if quantity<=0:return 0
        have=0
        for when,amount in self.items[tid]:
            have+=amount
            if have>=quantity:return when
        return math.inf
    def consume(self,tid,quantity,when):
        remaining=quantity
        for item in self.items[tid]:
            if item[0]>when:break
            take=min(item[1],remaining);item[1]-=take;remaining-=take
            if not remaining:break
        if remaining:raise PlanningError('Az ütemezés anyagegyenlege nem zárható.')
        self.items[tid]=[i for i in self.items[tid] if i[1]]


def duration(row,recipe,producer,settings,runs):
    f=settings[row['activity']]
    return max(.001,runs*recipe['seconds']*(1-row['parameters']['te']/100)*producer['factor']*(1-f['time_role']/100)*(1-f['time_rig']/100))


def _strategy(context,store,catalog,calculate,options,now=None,granularity=1):
    now=time.time() if now is None else now
    start=options.get('start',now);supply=options.get('supply_at',start)
    if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not 0<v<now+10*365*86400 for v in [start,supply]):
        raise PlanningError('Hibás ütemezési kezdés vagy anyagérkezés.')
    start=max(now,start);supply=max(start,supply)
    selected=options.get('characters')
    known={p['id'] for p in context['skill_profiles']}
    if selected is not None and (not isinstance(selected,list) or any(isinstance(i,bool) or not isinstance(i,int) or i not in known for i in selected)):
        raise PlanningError('Ismeretlen gyártó karakter az ütemezésben.')
    owned=options.get('owned_only',True);transfer=options.get('transfer_blueprints',False)
    if not isinstance(owned,bool) or not isinstance(transfer,bool):raise PlanningError('Hibás blueprintmód.')
    jobs,checked=all_jobs(store)
    workers=worker_profiles(context,store,jobs,checked,selected,start,now)
    context=copy.deepcopy(context)
    for bp in context['blueprints']:
        if bp.get('runs',-1)>=0 and bp.get('quantity')!=-1:
            bp['runs']=max(0,bp['runs']-sum(j.get('runs',0) for j in jobs if j.get('blueprint_id')==bp['item_id'] and j.get('activity_id') in [1,9] and j.get('status') in ['active','paused','ready']))
    base=calculate(context)
    # Short jobs expose parallel capacity without changing ME/TE. Recalculate
    # the complete BOM so per-job rounding and BPC boundaries remain exact.
    for row in base['queue']:
        capable=qualified(row,catalog,workers)
        parallel=sum(w['capacity'][row['activity']] for w,_ in capable) or 1
        if owned:
            pool=blueprints(row,context,context.get('reservations',{}).get(row['parameters']['bp_id'],{}).get('blueprint_runs',{}),jobs,start,workers,transfer)
            parallel=min(parallel,len(pool) or 1)
        recipe=catalog.recipes[row['id']]
        per_run=max([duration(row,recipe,p,context['settings'],1) for _,p in capable] or [recipe['seconds']])
        limit=max(1,int(30*86400/per_run))
        batch=min(row['parameters']['job_runs'],max(1,math.ceil(row['runs']/(parallel*granularity)) if granularity else 1),limit,recipe['copy_limit'])
        context['parameters'].setdefault(row['id'],{})['job_runs']=batch
    plan=calculate(context)
    if sum(r['jobs'] for r in plan['queue'])>MAX_JOBS:raise PlanningError('Az ütemezés több mint 10 000 jobot igényel. Növeld a Run/job értéket vagy csökkentsd a célmennyiséget.')
    ledger=Materials();pending={};pools={};critical={};eligibility={};warnings=[]
    relevant_jobs=context['jobs']
    for row in plan['rows']:
        ledger.add(row['id'],row['used_stock'],start)
        if row['used_wip']:
            matching=[j for j in relevant_jobs if j.get('product_type_id')==row['id'] and j.get('expected_output',0)>0 and j.get('status') in ['active','ready','paused']]
            when=max([release(j,start) for j in matching]) if matching and not row['manual_wip'] else math.inf
            ledger.add(row['id'],row['used_wip'],when)
            if not math.isfinite(when):warnings.append({'id':row['id'],'name':row['name'],'reason':'A folyamatban lévő anyag érkezése nem ellenőrizhető.'})
        if row['buy']:ledger.add(row['id'],row['buy'],supply)
    for row in plan['queue']:
        eligible=qualified(row,catalog,workers);eligibility[row['id']]=eligible
        held=context.get('reservations',{}).get(row['parameters']['bp_id'],{}).get('blueprint_runs',{})
        pool=blueprints(row,context,held,jobs,start,workers,transfer)
        if not owned and eligible:
            parallel=sum(w['capacity'][row['activity']] for w,_ in eligible)
            originals=any(p['remaining'] is None for p in pool)
            capacity=sum(p['remaining'] or 0 for p in pool)
            needed=max(0,math.ceil((row['runs']-capacity)/row['parameters']['copy_limit'])) if not originals and row['activity']!='reaction' else 0
            needed=max(needed,max(0,min(row['jobs'],parallel)-len(pool)))
            for n in range(min(MAX_JOBS,needed)):
                pool.append({'key':f"new:{row['id']}:{n}",'item_id':None,'kind':'BPO' if row['activity']=='reaction' else 'BPC',
                             'remaining':None if row['activity']=='reaction' else row['parameters']['copy_limit'],
                             'available':supply,'owner':None,'actual_owner':None,'virtual':True,'used':0})
        pools[row['id']]=pool
        pending[row['id']]=[g['runs'] for g in row['batches'] for _ in range(g['count'])]
    # Downstream work is prioritised when multiple jobs can start together.
    for row in reversed(plan['queue']):
        critical[row['id']]=row['seconds']+max([critical.get(p['id'],0) for p in plan['queue'] if any(m['id']==row['id'] for m in p['materials'])] or [0])
    rows={r['id']:r for r in plan['queue']};scheduled=[]
    while any(pending.values()):
        best=None
        for tid,runs_list in pending.items():
            if not runs_list:continue
            row=rows[tid];runs=runs_list[0];recipe=catalog.recipes[tid];f=context['settings'][row['activity']]
            factor=Decimal(1)-Decimal(str(row['parameters']['me']))/100
            factor*=1-Decimal(str(f['material_role']))/100;factor*=1-Decimal(str(f['material_rig']))/100
            materials=[(m['typeID'],material_for_batch(m['quantity'],runs,factor)) for m in recipe['materials']]
            ready=max([start]+[ledger.ready(mid,n) for mid,n in materials])
            if not math.isfinite(ready):continue
            for worker,producer in eligibility[tid]:
                slots=worker['slots'][row['activity']];slot=min(range(len(slots)),key=slots.__getitem__)
                candidates=[bp for bp in pools[tid] if (bp['remaining'] is None or bp['remaining']>=runs) and (bp['owner'] is None or bp['owner']==worker['id'])]
                if not candidates:continue
                bp=min(candidates,key=lambda b:(max(b['available'],ready,slots[slot]),b['virtual'],b['key']))
                begin=max(ready,slots[slot],bp['available']);seconds=duration(row,recipe,producer,context['settings'],runs)
                if not math.isfinite(begin) or worker['until'] and begin>=worker['until']:continue
                score=(begin,-critical[tid],begin+seconds,worker['id'],tid)
                if best is None or score<best[0]:best=(score,row,runs,worker,slot,bp,materials,begin,seconds)
        if best is None:break
        _,row,runs,worker,slot,bp,materials,begin,seconds=best;end=begin+seconds
        for mid,n in materials:ledger.consume(mid,n,begin)
        ledger.add(row['id'],runs*row['parameters']['output'],end)
        worker['slots'][row['activity']][slot]=end;bp['available']=end;bp['used']+=runs
        if bp['remaining'] is not None:bp['remaining']-=runs
        pending[row['id']].pop(0)
        scheduled.append({'id':len(scheduled)+1,'product_id':row['id'],'name':row['name'],'activity':row['activity'],
                          'character_id':worker['id'],'character_name':worker['name'],'slot':slot+1,'runs':runs,
                          'output':runs*row['parameters']['output'],'start':begin,'end':end,'seconds':seconds,
                          'blueprint_id':row['parameters']['bp_id'],'blueprint_item_id':bp['item_id'],'blueprint_key':bp['key'],
                          'blueprint_kind':bp['kind'],'procure_blueprint':bp['virtual'],'transfer_required':bool(not context['corporation_id'] and bp['actual_owner'] and bp['actual_owner']!=worker['id']),
                          'me':row['parameters']['me'],'te':row['parameters']['te']})
    blocked=[];shortages=[]
    for row in plan['queue']:
        tid=row['id'];pool=pools[tid];remaining=sum(pending[tid])
        virtual=[p for p in pool if p['virtual'] and p['used']]
        real=[p for p in pool if not p['virtual']]
        # Capacity is measured before this schedule, after other plans' holds.
        available_runs=None if any(p['remaining'] is None for p in real) else sum((p['remaining'] or 0)+p['used'] for p in real)
        deficit=max(0,row['runs']-available_runs) if available_runs is not None else 0
        if virtual or deficit:
            shortages.append({'id':row['parameters']['bp_id'],'name':catalog.name(row['parameters']['bp_id']),'product_id':tid,
                              'copies':len(virtual) or (1 if row['activity']=='reaction' else math.ceil(deficit/row['parameters']['copy_limit'])),
                              'runs':sum(p['used'] for p in virtual) or deficit,'copy_runs':row['parameters']['copy_limit'],
                              'category':'Reakcióformula' if row['activity']=='reaction' else 'BPC-run','is_blueprint':True})
        if remaining:
            reason='Nincs megfelelő skillű, ellenőrzött karakter.' if not eligibility[tid] else 'Blueprint, szabad slot, tanulástól független Omega-korlát vagy gyártási bemenet hiányzik.'
            blocked.append({'id':tid,'name':row['name'],'runs':remaining,'reason':reason})
    target_ready=ledger.ready(plan['product_id'],plan['quantity'])
    finish=max([start]+[j['end'] for j in scheduled]+([target_ready] if math.isfinite(target_ready) else []))
    return {'jobs':sorted(scheduled,key=lambda j:(j['start'],j['end'],j['id'])),'blocked':blocked,'blueprint_shortages':shortages,
            'workers':[{k:w[k] for k in ['id','name','capacity','as_of','jobs_as_of','stale','excluded','until']} for w in workers],
            'material_shortfall':plan['shopping'],'material_warnings':warnings,'start':start,'finish':finish if not blocked and not warnings else None,
            'partial_finish':finish,'seconds':finish-start,'complete':not blocked and not warnings,'owned_only':owned,
            'runs':sum(j['runs'] for j in scheduled),'source':plan['source'],'corporation_id':context['corporation_id'],
            'scope_label':plan['scope_label'],'supply_at':supply,'heuristic':True,'calculated_at':now,
            'assumptions':['Az alapanyagok és az új blueprintek a megadott anyagérkezéskor rendelkezésre állnak.',
                           'A kész jobok átvétele és a szükséges árumozgatás késedelem nélkül történik.',
                           'Csak a kiválasztott ME/TE-vel egyező blueprinteket használjuk. A corp indítási jogosultságokat biztosítottnak tekintjük.']}


def build(context,store,catalog,calculate,options,now=None):
    now=time.time() if now is None else now
    first=_strategy(context,store,catalog,calculate,options,now)
    candidates=[first]
    # Compare coarse/finer batches, including unit jobs for small plans. This
    # avoids claiming that equal chunks always balance unequal character speeds.
    if first['jobs'] and any(j['runs']>1 for j in first['jobs']):
        for granularity in ([4,0] if first['runs']<=200 else [4]):
            try:candidates.append(_strategy(context,store,catalog,calculate,options,now,granularity))
            except PlanningError as error:
                if '10 000' not in str(error):raise
    best=min(candidates,key=lambda p:(not p['complete'],sum(r['runs'] for r in p['blocked']),p['seconds'],len(p['jobs']),sum(b['copies'] for b in p['blueprint_shortages'])))
    best['strategies_compared']=len(candidates)
    return best
