"""Dated PI cycle forecast, independent of HTTP cache freshness.

Factory products and optional modeled extraction follow validated routes.
Extraction formula: https://developers.eveonline.com/docs/guides/pi/
Dogma defaults 1683/1687 verified in CCP SDE build 3607705 (no ECU overrides).
All results are conditional estimates, never replacement ESI observations.
"""
from collections import defaultdict
from copy import deepcopy
import heapq
import math

MAX_SECONDS=90*86400
MAX_EVENTS=100000


def extraction_yield(base,cycle_seconds,index):
    """CCP documented decay/noise curve; index is the zero-based program cycle."""
    width=cycle_seconds/900
    position=(index+.5)*width
    phase=base**.7
    oscillation=max(0,(math.cos(phase+position/12)+math.cos(phase/2+position/5)+math.cos(position/2))/3)
    amount=width*base/(1+position*.012)*(1+.8*oscillation)
    # The game's integer boundary is exclusive, as documented by CCP.
    return max(0,math.ceil(amount)-1)


def forecast(pins,factories,routes,catalog,anchor,now,hours,valid=True,extractors=()):
    result={'anchor':anchor,'calculated_at':now,'available':False,'factories':[],
            'first_stop':None,'seconds_left':None,'materials_now':[],
            'assumptions':['modeled_extraction' if extractors else 'finite_stock'],'warnings':[],
            'extraction_since_snapshot':[],'extraction_next_period':[]}
    if not valid or anchor>now or any(f['last_cycle_start'] is not None and f['last_cycle_start']>anchor for f in factories):
        result['warnings'].append('inconsistent_time');return result
    if not factories and not extractors:result['available']=True;return result
    by_id={p['pin_id']:p for p in pins}
    fs={f['id']:f for f in factories}
    stock={pid:defaultdict(int) for pid in by_id}
    storage=set()
    for p in pins:
        if catalog.pi_types.get(p['type_id'],{}).get('group_id') in {1027,1029,1030}:storage.add(p['pin_id'])
        for item in p.get('contents',[]):stock[p['pin_id']][item['type_id']]+=item['amount']
    outgoing=defaultdict(list);incoming=defaultdict(list)
    for r in sorted(routes,key=lambda r:r['route_id']):
        outgoing[r['source_pin_id']].append(r);incoming[r['destination_pin_id']].append(r)
    # Exact phase only when the snapshot proves a currently running cycle.
    # Old/missing starts use the snapshot timestamp as the restart assumption.
    phase_unknown=False;events=[];running={};stops={};counts=defaultdict(int)
    completed=defaultdict(lambda:defaultdict(int));future=defaultdict(lambda:defaultdict(int))
    now_state=None;full=False;contention=False;steps=0;last_event=anchor;cutoff=min(now+30*86400,anchor+MAX_SECONDS)
    horizon=now+hours*3600
    mining={};mined=defaultdict(int);future_mined=defaultdict(int)
    for f in factories:
        start=f['last_cycle_start'];cycle=f['cycle_time']
        if cycle<=0:return result
        if start is not None and start<=anchor<start+cycle:
            end=start+cycle;running[f['id']]=end;heapq.heappush(events,(end,f['id']))
        else:phase_unknown=True

    for e in extractors:
        start,end,cycle=e['program_start'],e['program_end'],e['cycle_time']
        if not (start is not None and end is not None and end>start and cycle and e.get('qty_per_cycle',0)>0 and e['heads'] and e['output_routed']):continue
        if start>anchor:result['warnings'].append('inconsistent_time');return result
        count=math.floor((end-start)/cycle)
        index=max(0,math.floor((anchor-start)/cycle))
        if index<count:
            mining[e['id']]={'extractor':e,'index':index,'count':count}
            heapq.heappush(events,(start+(index+1)*cycle,e['id']))

    def totals():
        total=defaultdict(int)
        for s in stock.values():
            for tid,q in s.items():total[tid]+=q
        return total

    def capture():
        return {'stock':deepcopy(stock),'running':dict(running),'stops':dict(stops),'counts':dict(counts),
                'completed':{pid:dict(v) for pid,v in completed.items()},'totals':dict(totals()),'mined':dict(mined)}

    def capacity(pid,tid):
        if pid in fs:return max(0,fs[pid]['recipe']['inputs'].get(tid,0)-stock[pid][tid])
        if pid not in storage:return 0
        info=catalog.pi_types.get(by_id[pid]['type_id'],{});limit=info.get('capacity')
        volume=catalog.pi_types.get(tid,{}).get('volume')
        if limit is None or volume is None or volume<=0:return 0
        used=0
        for item,amount in stock[pid].items():
            v=catalog.pi_types.get(item,{}).get('volume')
            if amount and v is None:return 0
            used+=amount*(v or 0)
        return max(0,math.floor((limit-used+1e-8)/volume))

    def route_output(pid,tid,quantity):
        nonlocal full
        left=quantity
        for r in outgoing[pid]:
            if r['content_type_id']!=tid:continue
            dest=r['destination_pin_id'];wanted=min(left,int(r['quantity']))
            accepted=min(wanted,capacity(dest,tid));stock[dest][tid]+=accepted;left-=accepted
            if accepted<wanted:full=True
            if not left:break
        # Unrouted / overflow output cannot fund later factory cycles.
        if left:full=True

    def allocation(f):
        plan=[]
        for tid,need in f['recipe']['inputs'].items():
            own=min(need,stock[f['id']][tid]);remaining=need-own
            if own:plan.append((f['id'],tid,own))
            available={pid:stock[pid][tid] for pid in storage}
            for r in incoming[f['id']]:
                source=r['source_pin_id']
                if source not in storage or r['content_type_id']!=tid:continue
                amount=min(remaining,available[source],int(r['quantity']))
                if amount:plan.append((source,tid,amount));available[source]-=amount;remaining-=amount
            if remaining:return None
        return plan

    def simultaneous(ready):
        # Find a feasible shared-stock assignment before consuming anything.
        # A greedy first source can otherwise starve a factory with fewer routes.
        from .pi import maxflow
        plans={f['id']:[] for f in ready}
        for tid in {tid for f in ready for tid in f['recipe']['inputs']}:
            demand={};caps=defaultdict(int)
            for f in ready:
                need=f['recipe']['inputs'].get(tid,0);own=min(need,stock[f['id']][tid])
                if own:plans[f['id']].append((f['id'],tid,own))
                if need>own:demand[f['id']]=need-own
            supplies={pid:stock[pid][tid] for pid in storage}
            for f in ready:
                for r in incoming[f['id']]:
                    if r['source_pin_id'] in storage and r['content_type_id']==tid:
                        caps[r['source_pin_id'],f['id']]+=int(r['quantity'])
            assignments={};total,_=maxflow(supplies,demand,caps,assignments)
            if total!=sum(demand.values()):return None
            for (source,pid),q in assignments.items():
                if q:plans[pid].append((source,tid,q))
        return plans

    def start_ready(t):
        nonlocal contention
        waiting=[f for f in factories if f['id'] not in running and f['output_routed']]
        ready=[f for f in waiting if allocation(f) is not None]
        plans=simultaneous(ready)
        if plans is None:contention=True
        for f in sorted(ready,key=lambda f:f['id']):
            plan=plans[f['id']] if plans is not None else allocation(f)
            if plan is None:continue
            for source,tid,amount in plan:stock[source][tid]-=amount
            running[f['id']]=t+f['cycle_time'];heapq.heappush(events,(running[f['id']],f['id']))
            stops.pop(f['id'],None)
        for f in factories:
            if f['id'] not in running:stops.setdefault(f['id'],t)

    if mining:result['warnings'].append('modeled_yield')
    start_ready(anchor)
    while events:
        t=events[0][0]
        if t>cutoff:break
        if now_state is None and t>now:now_state=capture()
        last_event=t
        batch=[]
        while events and events[0][0]==t:batch.append(heapq.heappop(events)[1])
        for pid in batch:
            if pid in mining:
                program=mining[pid];e=program['extractor'];tid=e['product_id']
                q=extraction_yield(e['qty_per_cycle'],e['cycle_time'],program['index'])
                mined[tid]+=q
                if now<t<=horizon:future_mined[tid]+=q
                route_output(pid,tid,q);program['index']+=1
                if program['index']<program['count']:
                    heapq.heappush(events,(e['program_start']+(program['index']+1)*e['cycle_time'],pid))
                continue
            running.pop(pid,None);counts[pid]+=1
            for tid,amount in fs[pid]['recipe']['outputs'].items():
                completed[pid][tid]+=amount
                if now<t<=horizon:future[pid][tid]+=amount
                route_output(pid,tid,amount)
        start_ready(t);steps+=len(batch)
        if steps>=MAX_EVENTS:break
    exhausted=bool(events and (events[0][0]<=cutoff or cutoff<now+30*86400))
    if now_state is None:now_state=capture()
    result['available']=not exhausted
    if exhausted:result['warnings'].append('simulation_limit')
    if phase_unknown:result['warnings'].append('assumed_restart')
    if full:result['warnings'].append('output_capacity')
    if contention:result['warnings'].append('shared_priority')
    result['materials_now']=[{'id':tid,'name':catalog.name(tid),'quantity':q} for tid,q in sorted(now_state['totals'].items()) if q>0]
    stop_times=[]
    for f in factories:
        pid=f['id'];stop=stops.get(pid)
        if stop is not None:stop_times.append(stop)
        current=now_state['running'].get(pid)
        row={'id':pid,'running_now':current is not None,'current_cycle_end':current,
             'idle_since':now_state['stops'].get(pid),'expected_stop':stop,'stock_stop':stop if not extractors else None,
             'seconds_left':max(0,stop-now) if stop is not None else None,
             'completed_cycles':now_state['counts'].get(pid,0),
             'products_since_snapshot':[{'id':tid,'name':catalog.name(tid),'quantity':q} for tid,q in now_state['completed'].get(pid,{}).items()],
             'products_next_period':[{'id':tid,'name':catalog.name(tid),'quantity':q} for tid,q in future[pid].items()]}
        result['factories'].append(row)
    result['extraction_since_snapshot']=[{'id':tid,'name':catalog.name(tid),'quantity':q} for tid,q in now_state['mined'].items()]
    result['extraction_next_period']=[{'id':tid,'name':catalog.name(tid),'quantity':q} for tid,q in future_mined.items()]
    result['first_stop']=min(stop_times) if stop_times else None
    result['seconds_left']=max(0,result['first_stop']-now) if result['first_stop'] is not None else None
    result['simulated_until']=cutoff if events else last_event
    return result
