"""Personal mining ledger history and refining estimates."""
from __future__ import annotations
from collections import defaultdict
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal,ROUND_FLOOR
import re,time
from . import progress
from .esi import ESI,MINING_SCOPES,EsiError,AuthenticationError
from .planner import PlanningError,integer
from .moons import preferences,reprocessing_yield


def day(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise PlanningError('Érvénytelen dátum.')
    try:date.fromisoformat(value)
    except ValueError:raise PlanningError('Érvénytelen dátum.') from None
    return value


def validate(rows):
    if not isinstance(rows,list):raise EsiError('Hibás bányászati napló; a korábbi adatok megmaradtak.')
    keys=set()
    for r in rows:
        if not isinstance(r,dict):raise EsiError('Hibás bányászati naplósor.')
        try:
            day(r.get('date'))
            for k in ['type_id','solar_system_id']:integer(r.get(k),k,2**31-1,1)
            integer(r.get('quantity'),'Mennyiség',10**12)
        except PlanningError as e:raise EsiError(str(e)) from None
        key=(r['date'],r['solar_system_id'],r['type_id'])
        if key in keys:raise EsiError('Ismétlődő bányászati naplósor; próbáld újra később.')
        keys.add(key)


def resource(eve,cid,token):
    old=eve.store.snapshot(cid,'mining');now=time.time()
    progress.resource('Bányászati napló',bool(old and old['expires']>now))
    if old and old['expires']>now:return old
    rows=[];expires=[];dates=[];pages=None
    for page in range(1,1001):
        progress.report(page=page,pages=pages)
        body,h=eve.http.request(f'{ESI}/characters/{cid}/mining/?page={page}',token=token)
        h={k.lower():v for k,v in h.items()}
        validate(body)
        try:reported=int(h.get('x-pages','1'))
        except (ValueError,TypeError):raise EsiError('Hibás bányászati lapozás.') from None
        if not 1<=reported<=1000 or (pages is not None and pages!=reported):raise EsiError('A bányászati lapozás megváltozott; próbáld újra később.')
        pages=reported;rows.extend(body);dates.append(h.get('last-modified'))
        cache=h.get('cache-control','').lower();m=re.search(r'(?:^|,)\s*max-age\s*=\s*"?(\d+)',cache)
        try:age=max(0,int(h.get('age','0')))
        except (TypeError,ValueError):age=0
        ttl=max(0,min(600,int(m[1])-age)) if m else 600
        if 'no-cache' in cache or 'no-store' in cache:ttl=0
        expires.append(now+ttl);progress.report(page=page,pages=pages)
        if page>=pages:break
    if len(set(dates))>1:raise EsiError('A bányászati napló lapozás közben megváltozott; próbáld újra később.')
    validate(rows)
    return {'data':rows,'fetched':now,'expires':min(expires),'etag':None}


def sync(eve):
    if not eve.sync_lock.acquire(blocking=False):raise EsiError('Az EVE-frissítés már folyamatban van.')
    try:
        results=[]
        for char in progress.items(eve.store.characters()):
            try:
                token=eve.token(char['id'],required_scopes=MINING_SCOPES)
                eve.store.save_mining(char['id'],resource(eve,char['id'],token))
                results.append({'id':char['id'],'ok':True})
            except EsiError as e:
                eve.store.resource_error(char['id'],'mining',str(e),isinstance(e,AuthenticationError))
                results.append({'id':char['id'],'ok':False,'error':str(e)})
        return results
    finally:eve.sync_lock.release()


def dashboard(store,catalog,start=None,end=None,character_id=None,ore_id=None,access_scopes=None,now=None):
    now=time.time() if now is None else now;today=datetime.fromtimestamp(now,timezone.utc).date()
    start=day(start) if start else (today-timedelta(days=29)).isoformat()
    end=day(end) if end else today.isoformat()
    if start>end:raise PlanningError('A kezdő dátum nem lehet későbbi a záró dátumnál.')
    cid=integer(character_id,'Karakter',2**31-1,1) if character_id else None
    tid=integer(ore_id,'Érc',2**31-1,1) if ore_id else None
    chars=store.characters();names={c['id']:c['name'] for c in chars}
    if cid and cid not in names:raise PlanningError('Ismeretlen karakter.')
    access=[]
    for c in chars:
        status=store.resource_status(c['id'],'mining') or {};snap=store.snapshot(c['id'],'mining')
        auth=not set(MINING_SCOPES).issubset((access_scopes or {}).get(c['id'],[])) if access_scopes is not None else bool(status.get('needs_auth') or not snap)
        access.append({'id':c['id'],'name':c['name'],'needs_auth':auth,'error':status.get('error'),
                       'checked_at':(snap or {}).get('fetched'),'expires':(snap or {}).get('expires'),
                       'stale':bool(snap and snap['expires']<=now)})
    with store.db() as db:
        records=[dict(r) for r in db.execute('''SELECT l.* FROM mining_ledger l
            JOIN characters c ON c.id=l.character_id
            WHERE l.date>=? AND l.date<=? AND (? IS NULL OR l.character_id=?) AND (? IS NULL OR l.type_id=?)
            ORDER BY l.date DESC,c.name,l.type_id,l.solar_system_id''',(start,end,cid,cid,tid,tid))]
        ores=[{'id':r[0],'name':catalog.name(r[0])} for r in db.execute('SELECT DISTINCT type_id FROM mining_ledger l JOIN characters c ON c.id=l.character_id ORDER BY type_id')]
        earliest=db.execute('SELECT MIN(date) FROM mining_ledger l JOIN characters c ON c.id=l.character_id').fetchone()[0]
    prefs=preferences(store);yield_=reprocessing_yield(catalog.moon_rules,prefs) if catalog.moon_rules else None
    def bucket():return {'quantity':0,'volume':0.,'unknown_volume':0,'records':0,'raw':defaultdict(int),'materials':defaultdict(int),'unrefinable':0}
    all_=bucket();by_char=defaultdict(bucket);by_ore=defaultdict(bucket);by_day=defaultdict(bucket);batches=defaultdict(lambda:defaultdict(int))
    def add(b,r):
        b['quantity']+=r['quantity'];b['records']+=1;b['raw'][r['type_id']]+=r['quantity']
        if r['volume'] is None:b['unknown_volume']+=1
        else:b['volume']+=r['volume']
    for r in records:
        info=catalog.mining_types.get(r['type_id'],{})
        r.update(name=catalog.name(r['type_id']),character_name=names[r['character_id']],system_name=catalog.moon_systems.get(r['solar_system_id'],{}).get('name',str(r['solar_system_id'])),
                 volume=float(Decimal(str(info['volume']))*r['quantity']) if info else None)
        for b in [all_,by_char[r['character_id']],by_ore[r['type_id']],by_day[r['date']]]:add(b,r)
        batches[r['character_id'],r['type_id']][r['date']]+=r['quantity']
    for (c,t),days in batches.items():
        info=catalog.mining_types.get(t,{})
        if not info.get('materials') or yield_ is None:
            for b in [all_,by_char[c],by_ore[t],*(by_day[d] for d in days)]:b['unrefinable']+=1
            continue
        # Attribute pooled refining output to the day its cumulative complete
        # portions become available. Carry ore remainders forward, never between
        # characters or types, so daily material quantities sum to the period.
        for m in info['materials']:
            cumulative=0;previous=0
            for d,quantity in sorted(days.items()):
                cumulative+=quantity
                output=int((Decimal(cumulative//info['portion'])*m['quantity']*yield_).to_integral_value(rounding=ROUND_FLOOR))
                by_day[d]['materials'][m['id']]+=output-previous
                previous=output
            for b in [all_,by_char[c],by_ore[t]]:b['materials'][m['id']]+=previous
    def finish(b):
        return {**b,'raw':[{'id':i,'name':catalog.name(i),'quantity':n} for i,n in sorted(b['raw'].items())],
                'materials':[{'id':i,'name':catalog.name(i),'quantity':n} for i,n in sorted(b['materials'].items())]}
    return {'characters':access,'ores':sorted(ores,key=lambda o:o['name']),'start':start,'end':end,'earliest':earliest,
            'summary':finish(all_),'by_character':[{'id':c,'name':names[c],**finish(b)} for c,b in sorted(by_char.items())],
            'by_ore':[{'id':t,'name':catalog.name(t),**finish(b)} for t,b in sorted(by_ore.items())],
            'by_day':[{'date':d,**finish(b)} for d,b in sorted(by_day.items())],
            'records':records,'price_ids':sorted(i for i in set(all_['materials']) if i in catalog.types),'refining_yield':float(yield_) if yield_ is not None else None,'implant':prefs['implant'],
            'scopes':MINING_SCOPES,'calculated_at':now}
