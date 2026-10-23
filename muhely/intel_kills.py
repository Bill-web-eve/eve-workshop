"""Compact regional intel from the public live feed; never infer current pilots.

Ten-second arrival batches are per system and span at most two minutes of event
time. Once closed, batch membership is immutable; reprocessed killmails update
values without creating another notification. Records are bounded to one day.
"""
from collections import Counter
from decimal import Decimal,ROUND_HALF_UP
import json,time

GROUP_SECONDS=10


def schema(store):
    with store.db() as db:db.executescript('''
        CREATE TABLE IF NOT EXISTS intel_kill_groups(id TEXT PRIMARY KEY,system_id INTEGER NOT NULL,first_at REAL NOT NULL,last_at REAL NOT NULL,received REAL NOT NULL,ready_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS intel_kill_events(id INTEGER PRIMARY KEY,group_id TEXT NOT NULL,ts REAL NOT NULL,received REAL NOT NULL,data TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS intel_kill_group_system ON intel_kill_groups(system_id,ready_at);
        CREATE INDEX IF NOT EXISTS intel_kill_event_group ON intel_kill_events(group_id);
        CREATE INDEX IF NOT EXISTS intel_kill_event_time ON intel_kill_events(ts);
    ''')


def wants_feed(store):
    from .intel import preferences,selected_characters
    p=preferences(store)
    return p['killfeed_enabled'] and bool(p['kill_region_ids'] or selected_characters(store,p))


def source(store):
    """Read persistent feed health without starting a worker or making requests."""
    with store.db() as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('fleet_settings','fleet_sources')")}
        settings=db.execute('SELECT data FROM fleet_settings WHERE id=1').fetchone() if 'fleet_settings' in tables else None
        cursor=db.execute("SELECT checked,error FROM fleet_sources WHERE key='live:cursor'").fetchone() if 'fleet_sources' in tables else None
    return {'enabled':not settings or json.loads(settings['data']).get('live',True),
            'checked':cursor['checked'] if cursor else None,'error':cursor['error'] if cursor else None}


def regions(p,positions,universe):
    return set(p['kill_region_ids']) or {universe.systems[c['system_id']]['region_id'] for c in positions if c['system_id'] in universe.systems}


def ingest(store,rows,catalog,now=None):
    from .intel import preferences
    from .fleet import timestamp
    now=time.time() if now is None else now
    if not preferences(store)['killfeed_enabled']:return
    with store.db() as db:
        for k in rows:
            at=timestamp(k['killmail_time'])
            if not now-86400<=at<=now+60:continue
            kid=k['killmail_id'];sid=k['solar_system_id'];victim=k['victim'];tid=victim.get('ship_type_id');value=k['zkb'].get('totalValue')
            data={'id':kid,'at':at,'ship_id':tid,'ship':catalog.name(tid or 0),'victim_id':victim.get('character_id'),
                  'cents':None if value is None else str(int((Decimal(str(value))*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP)))}
            old=db.execute('SELECT group_id FROM intel_kill_events WHERE id=?',(kid,)).fetchone()
            if old:
                db.execute('UPDATE intel_kill_events SET ts=?,data=? WHERE id=?',(at,json.dumps(data),kid));continue
            group=db.execute('SELECT * FROM intel_kill_groups WHERE system_id=? AND ready_at>? AND first_at>=? AND last_at<=? ORDER BY received DESC LIMIT 1',
                             (sid,now,at-120,at+120)).fetchone()
            gid=group['id'] if group else f'kill:{sid}:{kid}'
            if group:db.execute('UPDATE intel_kill_groups SET first_at=MIN(first_at,?),last_at=MAX(last_at,?) WHERE id=?',(at,at,gid))
            else:db.execute('INSERT INTO intel_kill_groups VALUES(?,?,?,?,?,?)',(gid,sid,at,at,now,now+GROUP_SECONDS))
            db.execute('INSERT INTO intel_kill_events VALUES(?,?,?,?,?)',(kid,gid,at,now,json.dumps(data)))
        db.execute('DELETE FROM intel_kill_events WHERE received<?',(now-86400,))
        db.execute('DELETE FROM intel_kill_events WHERE id IN (SELECT id FROM intel_kill_events ORDER BY received DESC,id DESC LIMIT -1 OFFSET 20000)')
        db.execute('DELETE FROM intel_kill_groups WHERE id NOT IN (SELECT DISTINCT group_id FROM intel_kill_events)')


def groups(store,universe,p,now,region_ids):
    if not p['killfeed_enabled'] or not region_ids:return []
    schema(store);systems={sid for sid,s in universe.systems.items() if s['region_id'] in region_ids}
    with store.db() as db:
        raw=db.execute('SELECT g.*,e.data,e.received event_received FROM intel_kill_groups g JOIN intel_kill_events e ON e.group_id=g.id WHERE e.ts>=? AND e.ts<=? ORDER BY g.received,g.id,e.ts,e.id',
                       (now-p['ttl_minutes']*60,now)).fetchall()
    found={}
    for r in raw:
        if r['system_id'] not in systems:continue
        if r['id'] not in found:
            info=universe.systems[r['system_id']]
            found[r['id']]={'id':r['id'],'system_id':r['system_id'],'system_name':info['name'],'region_id':info['region_id'],'region_name':info['region'],
                            'received':r['received'],'ready_at':r['ready_at'],'kills':[]}
        found[r['id']]['kills'].append(json.loads(r['data']))
    for g in found.values():
        g['count']=len(g['kills']);g['first_at']=min(k['at'] for k in g['kills']);g['last_at']=max(k['at'] for k in g['kills'])
        g['missing']=sum(k['cents'] is None for k in g['kills']);g['cents']=str(sum(int(k['cents'] or 0) for k in g['kills']))
        counts=Counter((k['ship_id'],k['ship']) for k in g['kills']);g['ships']=[{'type_id':tid,'name':name,'count':count} for (tid,name),count in sorted(counts.items(),key=lambda x:(-x[1],x[0][1]))]
    return list(found.values())


def alerts(store,universe,p,pos,now):
    feed=source(store);regions_=regions(p,pos,universe);items=[]
    domain='intel:kill';domains=[domain]
    if not feed['enabled'] or not p['killfeed_enabled']:return items,domains
    for g in groups(store,universe,p,now,regions_):
        if now<g['ready_at']:continue
        distances=[universe.distances(c['system_id']).get(g['system_id']) for c in pos]
        distance=min((d for d in distances if d is not None),default=None)
        items.append({'id':'intel:'+g['id'],'domain':domain,'category':'intel','kind':'intel_kill','subject':g['system_name'],
                      'corporation_id':None,'scope_name':'Személyes','when':g['last_at'],'checked_at':feed['checked'] or g['received'],'reliable':True,
                      'system_id':g['system_id'],'system_name':g['system_name'],'character_name':'','region_name':g['region_name'],'jumps':distance,
                      'kill_count':g['count'],'cents':g['cents'],'missing':g['missing'],'ships':g['ships'],'sound':p['sound'],'cooldown':p['cooldown_seconds'],
                      'overlay_reports':[{'id':g['id'],'kind':'kill','when':g['ready_at'],'kill_count':g['count'],'cents':g['cents'],'missing':g['missing'],
                                          'pilots':[],'ships':[str(s['count'])+' × '+s['name'] for s in g['ships']]}]})
    return items,domains
