"""Local alert aggregation. Never infer a healthy/failed state from missing data."""
from __future__ import annotations
import hashlib
import json
import secrets
import time
from . import skills, pi, extractions
from .planner import PlanningError

CATEGORIES=('skills','jobs','pi','moons','intel')
DEFAULTS={'os_enabled':False,'auto_refresh':True,'moon_days':3,'personal':True,'corporations':True,
          'categories':{k:True for k in CATEGORIES},'moon_owners':{}}


def schema(store):
    with store.db() as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS notification_preferences(id INTEGER PRIMARY KEY,data TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS notification_events(id TEXT PRIMARY KEY,domain TEXT NOT NULL,fingerprint TEXT NOT NULL,
            episode INTEGER NOT NULL,active INTEGER NOT NULL,sent INTEGER NOT NULL DEFAULT 0,
            lease TEXT,lease_until REAL NOT NULL DEFAULT 0,updated REAL NOT NULL);
          CREATE TABLE IF NOT EXISTS intel_alarm_sent(owner TEXT PRIMARY KEY,at REAL NOT NULL);''')


def preferences(store):
    schema(store)
    with store.db() as db:row=db.execute('SELECT data FROM notification_preferences WHERE id=1').fetchone()
    data=json.loads(row['data']) if row else {}
    return {**DEFAULTS,**data,'categories':{**DEFAULTS['categories'],**data.get('categories',{})}}


def save_preferences(store,data):
    if not isinstance(data,dict) or set(data)-set(DEFAULTS):raise PlanningError('Hibás értesítési beállítás.')
    result=preferences(store)
    for key,value in data.items():
        if key in ['os_enabled','auto_refresh','personal','corporations']:
            if type(value) is not bool:raise PlanningError('Hibás értesítési kapcsoló.')
        elif key=='moon_days':
            if type(value) is not int or not 1<=value<=30:raise PlanningError('A holdelőrejelzés 1–30 nap lehet.')
        elif key=='categories':
            if not isinstance(value,dict) or set(value)-set(CATEGORIES) or any(type(v) is not bool for v in value.values()):raise PlanningError('Hibás értesítéstípus.')
            value={**result[key],**value}
        elif key=='moon_owners':
            moons={m['id'] for m in store.moon_records()};corps={c['id'] for c in store.corporations()}
            if not isinstance(value,dict) or any(k not in moons or (v is not None and (type(v) is not int or v not in corps)) for k,v in value.items()):raise PlanningError('Ismeretlen hold vagy corporation az értesítésekben.')
        result[key]=value
    with store.db() as db:db.execute('INSERT OR REPLACE INTO notification_preferences VALUES(1,?)',(json.dumps(result),))
    return result


def stamp(value):
    try:return skills.instant(value)
    except Exception:return None


def fresh(snapshot,now,error=False):
    return bool(snapshot and not error and snapshot['fetched']<=now+60 and now<=max(snapshot['expires'],snapshot['fetched']+1200))


def collect(store,catalog,now=None):
    now=time.time() if now is None else now;prefs=preferences(store)
    chars=store.characters();names={c['id']:c['name'] for c in chars};corps={c['id']:c['name'] for c in store.corporations()}
    alerts={};observed=set();moon_rows=[]
    def add(key,domain,category,kind,subject,scope=None,when=None,checked=None,reliable=True,**details):
        alerts[key]={'id':key,'domain':domain,'category':category,'kind':kind,'subject':subject,'corporation_id':scope,
                     'scope_name':corps.get(scope,str(scope)) if scope else 'Személyes',
                     'when':when,'checked_at':checked,'reliable':reliable,**details}
    def unknown(key,domain,subject,scope=None,checked=None,**details):
        add('data:'+key,domain,'data','unknown',subject,scope,checked=checked,reliable=False,**details)
    sd=skills.dashboard(store,catalog,now)
    for c in sd['characters']:
        domain='skills:'+str(c['id'])
        if c['status']=='unknown':unknown(domain,domain,c['name'],checked=c['queue_as_of'],source_category='skills',character_id=c['id'],character_name=c['name']);continue
        observed.add(domain)
        if c['status'] in ['idle','soon']:
            add(domain+':'+c['status'],domain,'skills','training_'+c['status'],c['name'],when=c['stops_at'],checked=c['queue_as_of'],character_id=c['id'])
    # A corporation job may also occur in its installer's character response.
    # Confirmed ownership wins, even when one of the copies is stale.
    corporate_ids=set();corp_parts=[]
    for corp in store.corporations():
        snap=store.corporation_snapshot(corp['id'],'jobs');corp_parts.append((corp,snap))
        if snap:corporate_ids.update(j['job_id'] for j in snap['data'])
    def jobs(rows,snapshot,domain,scope=None,char=None,error=False):
        valid=fresh(snapshot,now,error)
        if valid:observed.add(domain)
        else:unknown(domain,domain,corps[scope] if scope else char['name'],scope,(snapshot or {}).get('fetched'),source_category='jobs',character_id=(char or {}).get('id'),character_name=(char or {}).get('name'))
        for j in rows:
            if scope is None and j['job_id'] in corporate_ids:continue
            end=stamp(j.get('end_date'));status=j.get('status')
            if status!='ready' and not(status=='active' and end is not None and end<=now):continue
            tid=j.get('product_type_id') or j.get('blueprint_type_id') or 0
            add('job:'+str(j['job_id']),domain,'jobs','job_ready' if status=='ready' else 'job_expected',catalog.name(tid),scope,
                when=end,checked=(snapshot or {}).get('fetched'),reliable=valid,job_id=j['job_id'],runs=j.get('runs',0),
                character_id=(char or {}).get('id') if scope is None else j.get('installer_id'),
                character_name=(char or {}).get('name') if scope is None else names.get(j.get('installer_id'),str(j.get('installer_id') or '–')))
    for c in chars:
        snap=store.snapshot(c['id'],'jobs');jobs(snap['data'] if snap else [],snap,'jobs:personal:'+str(c['id']),char=c,error=bool(c['error']))
    for corp,snap in corp_parts:
        authorized=any(c.get('corporation_id')==corp['id'] and c['id']==corp['provider_id'] for c in chars)
        jobs(snap['data'] if snap else [],snap,'jobs:corp:'+str(corp['id']),corp['id'],error=bool(corp['error']) or not authorized)
    pd=pi.dashboard(store,catalog,now=now)
    for c in pd['characters']:
        if c['status']=='unknown':unknown('pi:'+str(c['id']),'pi:'+str(c['id']),c['name'],checked=c['checked_at'],source_category='pi',character_id=c['id'],character_name=c['name'])
    for c in pd['colonies']:
        domain=f"pi:{c['character_id']}:{c['id']}";projection=c.get('projection') or {}
        computed=projection.get('available') and not c['cached']
        known=not c['cached'] and (c['status']!='unknown' or computed)
        if known:observed.add(domain)
        else:unknown(domain,domain,c['name'],checked=c['checked_at'],source_category='pi',character_id=c['character_id'],character_name=c['character_name'],planet_id=c['id'])
        stopped=[f for f in projection.get('factories',[]) if not f['running_now'] and not f['products_next_period']] if computed else []
        expired=[e for e in c['extractors'] if e.get('program_end') is not None and e['program_end']<=now]
        kind='pi_estimated' if stopped else 'pi_extractor' if expired and not c['cached'] else 'pi_idle' if c['status']=='alert' and not c['cached'] else None
        if kind:
            add(domain+':stop',domain,'pi',kind,c['name'],when=projection.get('first_stop') if stopped else min(e['program_end'] for e in expired) if expired else c['last_update'],
                checked=c['checked_at'],reliable=known or (kind=='pi_extractor' and not c['cached']),character_id=c['character_id'],character_name=c['character_name'],planet_id=c['id'],factories=len(stopped),estimated=bool(stopped))
    moon_data=extractions.report(store,catalog,now)
    records={m['id']:m for m in store.moon_records()};structure_corps={}
    for c in chars:
        snap=store.snapshot(c['id'],'moon_timers')
        if snap:
            for r in snap['data'].get('rows',[]):structure_corps.setdefault(r['structure_id'],set()).add(snap['data']['corporation_id'])
    for mid,m in records.items():
        name=next((x['name'] for x in catalog.moon_locations(m['system_id']) if x['id']==m['moon_id']),str(m['moon_id']))
        moon_rows.append({'id':mid,'name':name})
        if m['structure']!='Athanor' or not m['enabled']:continue
        domain='moon:'+mid
        current=[e for e in moon_data['events'] if e['moon_record_id']==mid]
        if any(not e['stale'] for e in current):observed.add(domain)
        for e in current:
            at=stamp(e['date'])
            if at is None or e.get('fractured_at') is not None or e['kind'].endswith('history'):continue
            if at>now+prefs['moon_days']*86400 or at<now-86400:continue
            inferred=structure_corps.get(e.get('structure_id'),set())
            scope=prefs['moon_owners'].get(mid,e.get('corporation_id') or (next(iter(inferred)) if len(inferred)==1 else None))
            if scope and scope not in corps:corps[scope]='Corporation '+str(scope)
            valid=not e['stale'] and e['kind'] in ['extraction','notification']
            key=f"moon:{m['moon_id']}:{e.get('structure_id',0)}:{int(at)}"
            add(key,domain,'moons','moon_ready' if at<=now else 'moon_soon',name,when=at,scope=scope,checked=e.get('checked'),reliable=valid,
                moon_record_id=mid,volume=e.get('volume'),estimated=e.get('volume_source')=='duration_estimate',ownership_unknown=scope is None and mid not in prefs['moon_owners'])
    from .intel import collect_alerts
    intel_data=collect_alerts(store,now=now)
    observed.update(intel_data['observed_domains'])
    for item in intel_data['items']:alerts[item['id']]=item
    rows=sorted(alerts.values(),key=lambda a:(not a['reliable'],a['when'] is None,a['when'] or 0,a['subject'].casefold(),a['id']))
    return {'items':rows,'observed_domains':sorted(observed),'corporations':[{'id':cid,'name':name} for cid,name in sorted(corps.items(),key=lambda x:x[1])],
            'moons':moon_rows,'preferences':prefs,'calculated_at':now,
            'counts':{category:sum(a['category']==category for a in rows) for category in (*CATEGORIES,'data')}}


def claim(store,data,now=None):
    """Lease only unsent active episodes. Unknown data never resolves an episode."""
    now=time.time() if now is None else now;prefs=preferences(store);schema(store)
    if not prefs['os_enabled']:return []
    eligible=[a for a in data['items'] if a['category'] in CATEGORIES and a['reliable']]
    current={a['id'] for a in eligible};observed=set(data['observed_domains']);result=[]
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        for old in db.execute('SELECT id,domain FROM notification_events WHERE active=1').fetchall():
            if old['id'] not in current and old['domain'] in observed:db.execute('UPDATE notification_events SET active=0,lease=NULL,lease_until=0 WHERE id=?',(old['id'],))
        for a in eligible:
            if len(result)>=2000:break
            if not prefs['categories'][a['category']] or not prefs['corporations' if a['corporation_id'] else 'personal']:continue
            if a['category']=='intel':
                owner=':'.join(a['id'].split(':')[:3]);sent=db.execute('SELECT at FROM intel_alarm_sent WHERE owner=?',(owner,)).fetchone()
                if sent and now-sent['at']<a.get('cooldown',20):continue
            # Stable job/moon identity suppresses repeated snapshots and the
            # expected-to-confirmed transition for the same completed job.
            fingerprint=a.get('episode_key','') if a['category']=='intel' else str(int(a['when'])) if a['category']=='skills' and a['when'] is not None else ''
            old=db.execute('SELECT * FROM notification_events WHERE id=?',(a['id'],)).fetchone()
            episode=old['episode'] if old else 1
            if old and (not old['active'] or old['fingerprint']!=fingerprint):episode+=1;old=None
            if old and (old['sent'] or old['lease_until']>now):continue
            lease=secrets.token_urlsafe(24)
            db.execute('INSERT OR REPLACE INTO notification_events VALUES(?,?,?,?,1,0,?,?,?)',
                       (a['id'],a['domain'],fingerprint,episode,lease,now+120,now))
            result.append({**a,'receipt':lease,'notification_id':hashlib.sha256(f"{a['id']}:{episode}".encode()).hexdigest()})
        db.execute('DELETE FROM notification_events WHERE active=0 AND updated<?',(now-90*86400,))
    return result


def acknowledge(store,receipts):
    if not isinstance(receipts,list) or len(receipts)>2000 or any(not isinstance(v,str) or len(v)>100 for v in receipts):raise PlanningError('Hibás értesítési visszaigazolás.')
    schema(store)
    with store.db() as db:
        for receipt in receipts:
            row=db.execute('SELECT id FROM notification_events WHERE lease=?',(receipt,)).fetchone()
            if row and row['id'].startswith('intel:'):db.execute('INSERT OR REPLACE INTO intel_alarm_sent VALUES(?,?)',(':'.join(row['id'].split(':')[:3]),time.time()))
            db.execute('UPDATE notification_events SET sent=1,lease=NULL,lease_until=0 WHERE lease=?',(receipt,))
