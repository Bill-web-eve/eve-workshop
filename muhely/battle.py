"""Alliance-level inferred battle sides, editable per local activity session.

Positive edges mean shared targets; negative edges mean direct attacks.
No standings, current affiliations or alleged transitive friendship are invented.
"""
from collections import Counter,defaultdict
from itertools import combinations
import json,time
from .planner import PlanningError,integer


def schema(store):
    with store.db() as db:db.execute('CREATE TABLE IF NOT EXISTS fleet_sides(session_id TEXT PRIMARY KEY,data TEXT NOT NULL,updated REAL NOT NULL)')


def configuration(store,session_id,kill_ids=None):
    with store.db() as db:
        r=db.execute('SELECT data FROM fleet_sides WHERE session_id=?',(session_id,)).fetchone()
        if not r and kill_ids:
            # A late public killmail may prepend a session and change its first
            # kill ID. Keep the latest manual setup anchored to a kill still in
            # this same pilot's session; never inherit from an unrelated fight.
            ids=set(kill_ids);prefix=session_id.split(':')[0]+':'
            r=next((row for row in db.execute('SELECT data,session_id FROM fleet_sides WHERE session_id LIKE ? ORDER BY updated DESC',(prefix+'%',)) if int(row['session_id'].split(':')[1]) in ids),None)
    return {'side_count':None,'assignments':{},'names':{},**(json.loads(r[0]) if r else {})}


def positive(value):return type(value) is int and value>0


def group_key(entity):
    if positive(entity.get('alliance_id')):return 'alliance:'+str(entity['alliance_id'])
    cid=entity.get('corporation_id')
    # NPC corporations do not establish a common side for their player members.
    if positive(cid) and cid>=98000000:return 'corporation:'+str(cid)
    if positive(entity.get('character_id')):return 'character:'+str(entity['character_id'])
    return None


def name_ids(kills):
    ids=set()
    for k in kills:
        for p in [k['victim'],*k['attackers']]:
            key=group_key(p)
            if key:ids.add(int(key.split(':')[1]))
        if positive(k['victim'].get('character_id')):ids.add(k['victim']['character_id'])
    return sorted(ids)


def evidence(kills,character_id,names):
    groups={};hostile=Counter();coattack=Counter();events=[]
    def add(p):
        key=group_key(p)
        if not key:return None
        kind,eid=key.split(':');eid=int(eid)
        g=groups.setdefault(key,{'key':key,'kind':kind,'id':eid,'name':names.get(str(eid),{}).get('name') or kind.title()+' #'+str(eid),'pilots':set(),'own':False,'losses':[],'kills':set()})
        if positive(p.get('character_id')):g['pilots'].add(p['character_id'])
        if p.get('character_id')==character_id:g['own']=True
        return key
    for k in sorted({k['killmail_id']:k for k in kills}.values(),key=lambda k:k['killmail_id']):
        victim=add(k['victim']);attackers={key for p in k['attackers'] if (key:=add(p))}
        if victim:groups[victim]['losses'].append(k)
        for a in attackers:
            groups[a]['kills'].add(k['killmail_id'])
            hostile[a,victim]+=1 if victim else 0
        for a,b in combinations(sorted(attackers-{victim}),2):coattack[a,b]+=1
        events.append({'kill':k,'victim':victim,'attackers':attackers})
    return groups,hostile,coattack,events


def infer(groups,hostile,coattack,config):
    """Merge supported cooperation without crossing a direct-hostility edge,
    then color that conflict graph with 2--4 sides. Disconnected activity stays
    unassigned unless explicitly placed by the user. Manual pins survive refresh.
    """
    keys=sorted(groups);parent={key:key for key in keys};members={key:{key} for key in keys};pins=config['assignments']
    def root(key):
        while parent[key]!=key:parent[key]=parent[parent[key]];key=parent[key]
        return key
    def conflict(a,b):return hostile[a,b]+hostile[b,a]
    for (a,b),weight in sorted(coattack.items(),key=lambda p:(-p[1],p[0])):
        ra,rb=root(a),root(b)
        if ra==rb:continue
        combined=members[ra]|members[rb]
        if any(conflict(x,y) for x in members[ra] for y in members[rb]):continue
        keep,drop=sorted([ra,rb]);parent[drop]=keep;members[keep]=combined;members.pop(drop)
    roots=sorted(members);adj={r:set() for r in roots}
    for (a,b),weight in hostile.items():
        if not weight or b is None:continue
        ra,rb=root(a),root(b)
        if ra!=rb:adj[ra].add(rb);adj[rb].add(ra)
    owned=[r for r in roots if any(groups[k]['own'] for k in members[r])]
    anchor=min(owned or roots,key=lambda r:(-sum(len(groups[k]['kills'])+len(groups[k]['losses']) for k in members[r]),r)) if roots else None
    active=set();pending=[anchor] if anchor else []
    while pending:
        r=pending.pop()
        if r in active:continue
        active.add(r);pending.extend(adj[r]-active)
    # Manual changes move exactly the selected alliance, without recoloring
    # other groups or silently moving their cooperating partners as well.
    fixed={}
    minimum=max(2,max((v for k,v in pins.items() if k in groups and v>=0),default=0)+1)
    requested=config['side_count'];chosen={};inferred=2
    for limit in [requested] if requested else range(minimum,5):
        colors={r:c for r,c in fixed.items() if c<limit}
        if anchor and anchor not in colors:colors[anchor]=0
        remaining=active-set(colors)
        while remaining:
            r=min(remaining,key=lambda r:(-len({colors[n] for n in adj[r] if n in colors}),-len(adj[r]),-sum(len(groups[k]['pilots']) for k in members[r]),r))
            forbidden={colors[n] for n in adj[r] if n in colors and colors[n]>=0}
            available=[c for c in range(limit) if c not in forbidden]
            if available:
                # Fill connected opponents first; reuse the strongest supported color.
                colors[r]=min(available,key=lambda c:(-sum(coattack[tuple(sorted((a,b)))] for a in members[r] for q,side in colors.items() if side==c for b in members[q]),c))
            else:colors[r]=-1
            remaining.remove(r)
        chosen=colors;inferred=max(2,max((c+1 for c in colors.values() if c>=0),default=2))
        if all(c>=0 for c in colors.values()) or requested:break
    count=requested or max(inferred,minimum)
    assignments={key:pins.get(key,chosen.get(root(key),-1)) for key in keys}
    return assignments,count,anchor


def build(kills,character_id,config,names,summarize):
    groups,hostile,coattack,events=evidence(kills,character_id,names)
    assignments,count,_=infer(groups,hostile,coattack,config)
    buckets=[{'id':i,'name':config['names'].get(str(i)),'groups':[],'pilots':set(),'losses':[],'kills':set(),'friendly_fire':set()} for i in range(count)]
    unassigned={'id':-1,'name':None,'groups':[],'pilots':set(),'losses':[],'kills':set(),'friendly_fire':set()}
    index={b['id']:b for b in [*buckets,unassigned]}
    for key,g in groups.items():
        side=assignments[key];side=side if side in index else -1;b=index[side]
        conflicting=sum(v for (a,t),v in hostile.items() if a==key and t in assignments and assignments[t]==side and side>=0)
        b['groups'].append({'key':key,'kind':g['kind'],'id':g['id'],'name':g['name'],'side':side,'manual':key in config['assignments'],'own':g['own'],'pilot_count':len(g['pilots']),'kill_count':len(g['kills']),'loss_value':summarize(g['losses'],character_id)['total'],'conflicts':conflicting})
        b['pilots'].update(g['pilots'])
    relations=Counter()
    for e in events:
        victim=assignments.get(e['victim'],-1);index[victim]['losses'].append(e['kill'])
        for side in {assignments[a] for a in e['attackers']}:
            if side>=0 and side!=victim:index[side]['kills'].add(e['kill']['killmail_id'])
            if side>=0 and side==victim:index[side]['friendly_fire'].add(e['kill']['killmail_id'])
            relations[side,victim]+=1
    def finish(b):
        return {'id':b['id'],'name':b['name'],'groups':sorted(b['groups'],key=lambda g:(-int(g['loss_value']['cents']),g['name'],g['key'])),
                'pilot_count':len(b['pilots']),'loss_value':summarize(b['losses'],character_id)['total'],
                'loss_ids':[k['killmail_id'] for k in b['losses']],'kill_count':len(b['kills']),'friendly_fire':len(b['friendly_fire'])}
    return {'side_count':count,'configured_count':config['side_count'],'sides':[finish(b) for b in buckets],'unassigned':finish(unassigned),
            'relationships':[{'attacker':a,'victim':b,'killmails':n} for (a,b),n in sorted(relations.items())],
            'manual_groups':len(config['assignments']),'group_count':len(groups)}


def save(store,session_id,data,known_groups,seed=None):
    if not isinstance(data,dict) or set(data)-{'session_id','side_count','group','side','names','reset'}:raise PlanningError('Hibás battle report beállítás.')
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT data FROM fleet_sides WHERE session_id=?',(session_id,)).fetchone()
        current={'side_count':None,'assignments':{},'names':{},**(json.loads(row[0]) if row else seed or {})}
        if data.get('reset') is True:
            if set(data)-{'session_id','reset'}:raise PlanningError('Hibás battle report beállítás.')
            db.execute('INSERT OR REPLACE INTO fleet_sides VALUES(?,?,?)',(session_id,json.dumps({'side_count':None,'assignments':{},'names':{}}),time.time()));return
        if 'side_count' in data:
            n=data['side_count']
            if n is not None:n=integer(n,'Felek száma',4,2)
            current['side_count']=n
            if n:
                current['assignments']={k:(v if v<n else -1) for k,v in current['assignments'].items()}
        if 'group' in data:
            key=data['group']
            if not isinstance(key,str) or key not in known_groups:raise PlanningError('Ismeretlen harci csoport.')
            side=integer(data.get('side'),'Oldal',3,-1)
            if current['side_count'] and side>=current['side_count']:raise PlanningError('Nincs ilyen résztvevő oldal.')
            current['assignments'][key]=side
        elif 'side' in data:raise PlanningError('Ismeretlen harci csoport.')
        if 'names' in data:
            ns=data['names']
            if not isinstance(ns,dict) or any(k not in ['0','1','2','3'] or not isinstance(v,str) or len(v)>60 for k,v in ns.items()):raise PlanningError('Hibás oldalnév.')
            current['names'].update({k:v.strip() or None for k,v in ns.items()})
        db.execute('INSERT OR REPLACE INTO fleet_sides VALUES(?,?,?)',(session_id,json.dumps(current),time.time()))
