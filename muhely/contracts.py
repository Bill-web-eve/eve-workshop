"""Scoped contract snapshots, durable history and baseline-safe change alerts."""
from __future__ import annotations
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from email.utils import parsedate_to_datetime
import json,re,time
from . import progress
from .esi import ESI,EsiError,AuthenticationError,CONTRACT_SCOPES
from .planner import PlanningError,integer

STATES={'outstanding','in_progress','finished_issuer','finished_contractor','finished','cancelled','rejected','failed','deleted','reversed'}
TYPES={'unknown','item_exchange','auction','courier','loan'}
ACCEPTED={'in_progress','finished_issuer','finished_contractor','finished'}


def stamp(value):
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        return result.timestamp() if result.tzinfo else None
    except (ValueError,TypeError,AttributeError):return None


def schema(store):
    with store.db() as db:db.executescript('''
      CREATE TABLE IF NOT EXISTS contract_sources(scope TEXT NOT NULL,owner_id INTEGER NOT NULL,provider_id INTEGER,
        initialized REAL,fetched REAL,expires REAL,error TEXT,PRIMARY KEY(scope,owner_id));
      CREATE TABLE IF NOT EXISTS contract_archive(scope TEXT NOT NULL,owner_id INTEGER NOT NULL,contract_id INTEGER NOT NULL,
        issued REAL NOT NULL,first_seen REAL NOT NULL,last_seen REAL NOT NULL,data TEXT NOT NULL,PRIMARY KEY(scope,owner_id,contract_id));
      CREATE INDEX IF NOT EXISTS contract_archive_issued ON contract_archive(scope,issued);
      CREATE TABLE IF NOT EXISTS contract_history(scope TEXT NOT NULL,owner_id INTEGER NOT NULL,contract_id INTEGER NOT NULL,
        at REAL NOT NULL,status TEXT NOT NULL,data TEXT NOT NULL,PRIMARY KEY(scope,owner_id,contract_id,at));
      CREATE TABLE IF NOT EXISTS contract_alerts(id TEXT PRIMARY KEY,scope TEXT NOT NULL,owner_id INTEGER NOT NULL,detected REAL NOT NULL,data TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS contract_details(scope TEXT NOT NULL,owner_id INTEGER NOT NULL,contract_id INTEGER NOT NULL,
        fetched REAL NOT NULL,expires REAL NOT NULL,data TEXT NOT NULL,PRIMARY KEY(scope,owner_id,contract_id));
    ''')


def source(store,scope,oid):
    schema(store)
    with store.db() as db:
        row=db.execute('SELECT * FROM contract_sources WHERE scope=? AND owner_id=?',(scope,oid)).fetchone()
    return dict(row) if row else None


def validate(rows):
    if not isinstance(rows,list):raise EsiError('Hibás szerződéslista; a korábbi adatok megmaradtak.')
    ids=set()
    for r in rows:
        if not isinstance(r,dict):raise EsiError('Hibás szerződésadat.')
        for field in ['contract_id','issuer_id','issuer_corporation_id','assignee_id','acceptor_id']:
            value=r.get(field)
            if type(value) is not int or not (0 if field in ['assignee_id','acceptor_id'] else 1)<=value<2**53:raise EsiError('Hibás szerződésazonosító.')
        if r['contract_id'] in ids:raise EsiError('Ismétlődő szerződésadat; frissíts később.')
        ids.add(r['contract_id'])
        if r.get('status') not in STATES or r.get('type') not in TYPES or type(r.get('for_corporation')) is not bool or r.get('availability') not in {'public','personal','corporation','alliance'}:raise EsiError('Hibás szerződésállapot.')
        for field in ['date_issued','date_expired']:
            if stamp(r.get(field)) is None:raise EsiError('Hiányos szerződésidőpont.')
        for field in ['date_accepted','date_completed']:
            if r.get(field) is not None and stamp(r[field]) is None:raise EsiError('Hiányos szerződésidőpont.')
        if not isinstance(r.get('title',''),str) or len(r.get('title',''))>10000:raise EsiError('Hibás szerződéscím.')
        for field in ['price','buyout','reward','collateral','volume']:
            if field in r:
                try:value=Decimal(str(r[field]))
                except InvalidOperation:raise EsiError('Hibás szerződésösszeg.') from None
                if not value.is_finite() or value<0 or value>10**20:raise EsiError('Hibás szerződésösszeg.')
        for field in ['start_location_id','end_location_id','days_to_complete']:
            if field in r and (type(r[field]) is not int or not 0<=r[field]<2**53):raise EsiError('Hibás szerződéshely vagy határidő.')


def owned(r,scope,oid):
    return issued_by(r,scope,oid) or r['assignee_id']==oid or r['acceptor_id']==oid


def issued_by(r,scope,oid):
    return r['for_corporation'] and r['issuer_corporation_id']==oid if scope=='corporation' else not r['for_corporation'] and r['issuer_id']==oid


def accepted(r):return r['status'] in ACCEPTED and r['acceptor_id']>0


def resource(eve,scope,oid,token):
    old=source(eve.store,scope,oid);now=time.time()
    progress.resource('Szerződéslista',bool(old and old['expires'] and old['expires']>now))
    if old and old['expires'] and old['expires']>now:return None
    rows=[];pages=None;dates=[];expires=[];observed=[]
    for page in range(1,1001):
        body,h=eve.http.request(f'{ESI}/{"corporations" if scope=="corporation" else "characters"}/{oid}/contracts/?page={page}',token=token)
        h={k.lower():v for k,v in h.items()};validate(body)
        try:count=int(h.get('x-pages','1'));age=max(0,int(h.get('age','0')))
        except (ValueError,TypeError):raise EsiError('Hibás szerződéslapozás.') from None
        if not 1<=count<=1000 or pages is not None and pages!=count:raise EsiError('A szerződéslista lapozás közben megváltozott; a korábbi adatok megmaradtak.')
        pages=count;dates.append(h.get('last-modified'));rows.extend(body)
        if len(rows)>100000:raise EsiError('Túl nagy szerződéslista.')
        match=re.search(r'max-age="?(\d+)',h.get('cache-control',''));ttl=max(0,int(match[1])-age) if match else 300
        expires.append(now+ttl)
        try:observed.append(min(now,parsedate_to_datetime(h.get('last-modified') or h['date']).timestamp()- (0 if h.get('last-modified') else age)))
        except (KeyError,ValueError,TypeError):observed.append(now-age)
        progress.report(page=page,pages=pages)
        if page>=pages:break
    if len(set(dates))>1:raise EsiError('A szerződéslista lapozás közben megváltozott; a korábbi adatok megmaradtak.')
    validate(rows)
    return {'rows':rows,'fetched':min(observed),'expires':min(expires)}


def ingest(store,scope,oid,provider,part,now=None):
    """One complete source only; failed/missing pages never mutate the archive."""
    schema(store);now=time.time() if now is None else now;validate(part['rows'])
    rows=[r for r in part['rows'] if owned(r,scope,oid)]
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE');old_source=db.execute('SELECT * FROM contract_sources WHERE scope=? AND owner_id=?',(scope,oid)).fetchone()
        if old_source and old_source['fetched'] is not None and old_source['fetched']>part['fetched']:return
        initialized=old_source['initialized'] if old_source and old_source['initialized'] is not None else part['fetched']
        baseline=old_source is not None and old_source['initialized'] is not None
        for r in rows:
            rid=r['contract_id'];raw=json.dumps(r);previous=db.execute('SELECT * FROM contract_archive WHERE scope=? AND owner_id=? AND contract_id=?',(scope,oid,rid)).fetchone()
            prior=json.loads(previous['data']) if previous else None
            db.execute('INSERT OR REPLACE INTO contract_archive VALUES(?,?,?,?,?,?,?)',(scope,oid,rid,stamp(r['date_issued']),previous['first_seen'] if previous else now,part['fetched'],raw))
            if prior is None or any(prior.get(k)!=r.get(k) for k in ['status','acceptor_id','date_accepted','date_completed']):
                db.execute('INSERT OR REPLACE INTO contract_history VALUES(?,?,?,?,?,?)',(scope,oid,rid,now,r['status'],raw))
            kinds=[]
            if baseline and prior is None and stamp(r['date_issued'])>=initialized and r['assignee_id']==oid and r['status']=='outstanding' and stamp(r['date_expired'])>now:kinds.append('contract_new')
            if baseline and issued_by(r,scope,oid) and accepted(r) and (prior is not None and not accepted(prior) or prior is None and stamp(r['date_issued'])>=initialized):kinds.append('contract_accepted')
            for kind in kinds:
                key=f'contract:{scope}:{oid}:{rid}:{kind}'
                event={'id':key,'domain':f'contracts:{scope}:{oid}','category':'contracts','kind':kind,'subject':r.get('title') or '#'+str(rid),
                       'contract_id':rid,'owner_id':oid,'contract_scope':scope,'corporation_id':oid if scope=='corporation' else None,
                       'character_id':oid if scope=='personal' else None,'when':stamp(r.get('date_accepted')) if kind=='contract_accepted' else stamp(r['date_issued']),
                       'checked_at':part['fetched'],'reliable':True,'sound':True}
                db.execute('INSERT OR IGNORE INTO contract_alerts VALUES(?,?,?,?,?)',(key,scope,oid,now,json.dumps(event)))
        db.execute('INSERT OR REPLACE INTO contract_sources VALUES(?,?,?,?,?,?,NULL)',(scope,oid,provider,initialized,part['fetched'],part['expires']))


def failure(store,scope,oid,error,provider=None):
    schema(store)
    with store.db() as db:
        db.execute('INSERT OR IGNORE INTO contract_sources(scope,owner_id,provider_id) VALUES(?,?,?)',(scope,oid,provider))
        db.execute('UPDATE contract_sources SET error=? WHERE scope=? AND owner_id=?',(str(error),scope,oid))


def resolve_names(eve,rows):
    now=time.time();known={c['id'] for c in [*eve.store.characters(),*eve.store.corporations()]}
    ids={r[k] for r in rows for k in ['issuer_id','issuer_corporation_id','assignee_id','acceptor_id'] if r[k]>0}-known
    missing=[i for i in sorted(ids) if not (old:=eve.store.universe_cached('contract-name',i)) or old['data'].get('expires',0)<=now]
    for start in range(0,len(missing),1000):
        batch=missing[start:start+1000]
        try:
            progress.resource('Szerződéses felek nevei')
            result,_=eve.http.request(ESI+'/universe/names/',json_body=batch)
            if not isinstance(result,list) or any(not isinstance(r,dict) or r.get('id') not in batch or not isinstance(r.get('name'),str) for r in result):raise EsiError('Hiányos szerződéses névadat.')
            found={r['id']:r['name'] for r in result}
            for i in batch:eve.store.save_universe_cache('contract-name',i,{'name':found.get(i),'expires':now+(30*86400 if i in found else 900)},now)
        except EsiError:
            for i in batch:
                old=eve.store.universe_cached('contract-name',i)
                eve.store.save_universe_cache('contract-name',i,{**((old or {}).get('data',{})),'expires':now+900},now)


def sync(eve):
    if not eve.sync_lock.acquire(blocking=False):raise EsiError('Az EVE-frissítés már folyamatban van.')
    try:
        schema(eve.store);results=[];chars=eve.store.characters();granted=eve.granted_scopes()
        for c in progress.items(chars):
            cid=c['id']
            if CONTRACT_SCOPES[0] not in granted.get(cid,[]):continue
            try:
                token=eve.token(cid,required_scopes=[CONTRACT_SCOPES[0]]);part=resource(eve,'personal',cid,token)
                if part:ingest(eve.store,'personal',cid,cid,part);resolve_names(eve,part['rows'])
                results.append({'id':cid,'ok':True,'scope':'personal'})
            except EsiError as e:failure(eve.store,'personal',cid,e,cid);results.append({'id':cid,'ok':False,'scope':'personal','error':str(e)})
        for corp in progress.items(eve.store.corporations()):
            oid=corp['id']
            if not eve.store.corporation_monitored(oid):continue
            members=[c for c in chars if c.get('corporation_id')==oid and CONTRACT_SCOPES[1] in granted.get(c['id'],[])]
            if not members:continue
            errors=[]
            for c in members:
                try:
                    if not eve.store.corporation_monitored(oid):break
                    profile,_=eve.http.request(f'{ESI}/characters/{c["id"]}/')
                    if not isinstance(profile,dict) or profile.get('corporation_id')!=oid:raise EsiError('A szerződéseket olvasó karakter corporation-tagsága megváltozott.')
                    token=eve.token(c['id'],required_scopes=[CONTRACT_SCOPES[1]]);part=resource(eve,'corporation',oid,token)
                    if part:ingest(eve.store,'corporation',oid,c['id'],part);resolve_names(eve,part['rows'])
                    results.append({'id':oid,'ok':True,'scope':'corporation'});break
                except EsiError as e:errors.append(str(e))
            else:
                text=errors[-1] if errors else 'Nincs jogosult szerződésolvasó.';failure(eve.store,'corporation',oid,text)
                results.append({'id':oid,'ok':False,'scope':'corporation','error':text})
        return results
    finally:eve.sync_lock.release()


def alerts(store,now=None):
    schema(store);now=time.time() if now is None else now
    chars={c['id']:c['name'] for c in store.characters()};corps={c['id']:c for c in store.corporations()};rows=[]
    with store.db() as db:
        for row in db.execute('SELECT * FROM contract_alerts WHERE detected>=?',(now-86400,)):
            scope,oid=row['scope'],row['owner_id']
            if scope=='personal' and oid not in chars or scope=='corporation' and (oid not in corps or not corps[oid]['monitoring_enabled']):continue
            item=json.loads(row['data']);item['scope_name']=corps[oid]['name'] if scope=='corporation' else 'Személyes';item['character_name']=chars.get(oid) if scope=='personal' else None
            item['owner_name']=corps[oid]['name'] if scope=='corporation' else chars[oid];rows.append(item)
    return rows


def dashboard(store,scope='personal',owner=None,start=None,end=None,granted=None,locations=None):
    if scope not in {'personal','corporation'}:raise PlanningError('Ismeretlen szerződésnézet.')
    schema(store);now=time.time();chars=store.characters();corps=store.corporations();owners=chars if scope=='personal' else corps
    names={c['id']:c['name'] for c in [*chars,*corps]};known={c['id'] for c in owners}
    if owner is not None:
        try:owner=int(owner)
        except (ValueError,TypeError):raise PlanningError('Ismeretlen szerződéstulajdonos.') from None
        owner=integer(owner,'Tulajdonos',2**53-1,1)
    if owner is not None and owner not in known:raise PlanningError('Ismeretlen szerződéstulajdonos.')
    conditions=['scope=?'];args=[scope]
    ids=[owner] if owner else sorted(known)
    dates={}
    for key,value in [('start',start),('end',end)]:
        if value:
            try:dates[key]=datetime.strptime(value,'%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()
            except (ValueError,TypeError):raise PlanningError('Érvénytelen szerződésdátum.') from None
    if 'start' in dates and 'end' in dates and dates['start']>dates['end']:raise PlanningError('A kezdő dátum nem lehet a záró dátum után.')
    if not ids:return {'rows':[],'sources':[],'owners':owners,'characters':[{'id':c['id'],'name':c['name'],'authorized':set(CONTRACT_SCOPES)<=set((granted or {}).get(c['id'],[])),'personal_access':CONTRACT_SCOPES[0] in (granted or {}).get(c['id'],[]),'corporation_access':CONTRACT_SCOPES[1] in (granted or {}).get(c['id'],[])} for c in chars],'scopes':CONTRACT_SCOPES,'truncated':False,'scope':scope}
    conditions.append('owner_id IN ('+','.join('?' for _ in ids)+')');args.extend(ids)
    for key,operator in [('start','>='),('end','<')]:
        if key in dates:
            conditions.append('issued'+operator+'?');args.append(dates[key]+(86400 if key=='end' else 0))
    grouped={}
    with store.db() as db:
        records=db.execute('SELECT * FROM contract_archive WHERE '+' AND '.join(conditions)+' ORDER BY issued DESC,last_seen DESC LIMIT 10001',args).fetchall()
        for raw in records[:10000]:
            row=json.loads(raw['data']);rid=row['contract_id'];old=grouped.get(rid)
            if old:
                old['owners'].append({'id':raw['owner_id'],'name':names[raw['owner_id']]});continue
            row.update(scope=scope,owner_id=raw['owner_id'],owners=[{'id':raw['owner_id'],'name':names[raw['owner_id']]}],checked_at=raw['last_seen'],first_seen=raw['first_seen'])
            row['outgoing']=issued_by(row,scope,raw['owner_id']);row['incoming']=row['assignee_id']==raw['owner_id']
            for field in ['issuer_id','assignee_id','acceptor_id']:
                cached=store.universe_cached('contract-name',row[field]) if row[field] else None
                row[field.replace('_id','_name')]=names.get(row[field]) or (cached or {}).get('data',{}).get('name') or str(row[field] or '–')
            grouped[rid]=row
    rows=list(grouped.values());sources=[];granted=granted or {}
    for c in owners:
        if c['id'] not in ids:continue
        old=source(store,scope,c['id']);authorized=CONTRACT_SCOPES[0] in granted.get(c['id'],[]) if scope=='personal' else any(m.get('corporation_id')==c['id'] and CONTRACT_SCOPES[1] in granted.get(m['id'],[]) for m in chars)
        sources.append({'id':c['id'],'name':c['name'],'authorized':authorized,'enabled':scope=='personal' or c['monitoring_enabled'],
                        'fetched':(old or {}).get('fetched'),'expires':(old or {}).get('expires'),'error':(old or {}).get('error'),'stale':not old or not old['expires'] or old['expires']<=now})
    if locations:
        for oid in ids:
            selected=[r for r in rows if r['owner_id']==oid];parts=[{'location_id':r.get(k),'row':r,'field':k.replace('_id','_name')} for r in selected for k in ['start_location_id','end_location_id'] if r.get(k)]
            if scope=='corporation' and not store.corporation_monitored(oid):continue
            locations.decorate({'rows':parts},oid if scope=='corporation' else None)
            for p in parts:p['row'][p['field']]=p['location_name']
    return {'rows':rows,'sources':sources,'owners':owners,'characters':[{'id':c['id'],'name':c['name'],'authorized':set(CONTRACT_SCOPES)<=set((granted or {}).get(c['id'],[])),'personal_access':CONTRACT_SCOPES[0] in (granted or {}).get(c['id'],[]),'corporation_access':CONTRACT_SCOPES[1] in (granted or {}).get(c['id'],[])} for c in chars],'scopes':CONTRACT_SCOPES,'truncated':len(records)>10000,'scope':scope}


def details(eve,catalog,scope,oid,rid):
    if scope not in {'personal','corporation'}:raise PlanningError('Ismeretlen szerződésnézet.')
    oid=integer(oid,'Tulajdonos',2**53-1,1);rid=integer(rid,'Szerződés',2**53-1,1);schema(eve.store)
    with eve.store.db() as db:
        raw=db.execute('SELECT * FROM contract_archive WHERE scope=? AND owner_id=? AND contract_id=?',(scope,oid,rid)).fetchone()
        old=db.execute('SELECT * FROM contract_details WHERE scope=? AND owner_id=? AND contract_id=?',(scope,oid,rid)).fetchone()
        history=[{'at':r['at'],'status':r['status'],'contract':json.loads(r['data'])} for r in db.execute('SELECT * FROM contract_history WHERE scope=? AND owner_id=? AND contract_id=? ORDER BY at',(scope,oid,rid))]
    if not raw:raise PlanningError('A szerződés nincs a helyi előzményekben.')
    chars=eve.store.characters();members=[c for c in chars if c['id']==oid] if scope=='personal' else [c for c in chars if c.get('corporation_id')==oid]
    if not members:raise PlanningError('Nincs hozzáadott, jogosult tagkarakter.')
    result={'contract':json.loads(raw['data']),'history':history,'items':json.loads(old['data']) if old else None,'items_at':old['fetched'] if old else None,'error':None}
    if result['items'] is not None:result['items']=[{**r,'name':catalog.name(r['type_id'])} for r in result['items']]
    if scope=='corporation' and not eve.store.corporation_monitored(oid):result['error']='Ennek a corporationnek a figyelése ki van kapcsolva.';return result
    if old and old['expires']>time.time():return result
    scope_name=CONTRACT_SCOPES[scope=='corporation'];errors=[]
    for c in members:
        try:
            token=eve.token(c['id'],required_scopes=[scope_name])
            if scope=='corporation':
                profile,_=eve.http.request(f'{ESI}/characters/{c["id"]}/')
                if profile.get('corporation_id')!=oid:raise EsiError('A szerződéseket olvasó karakter corporation-tagsága megváltozott.')
            rows,h=eve.http.request(f'{ESI}/{"corporations" if scope=="corporation" else "characters"}/{oid}/contracts/{rid}/items/',token=token)
            if not isinstance(rows,list):raise EsiError('Hibás szerződéstétel-lista.')
            for r in rows:
                if not isinstance(r,dict) or any(type(r.get(k)) is not int or r[k]<1 for k in ['record_id','type_id']) or type(r.get('quantity')) is not int or r['quantity']<0 or type(r.get('is_included')) is not bool or type(r.get('is_singleton')) is not bool:raise EsiError('Hibás szerződéstétel.')
            now=time.time();h={k.lower():v for k,v in h.items()};m=re.search(r'max-age="?(\d+)',h.get('cache-control',''));expiry=now+max(0,(int(m[1]) if m else 3600)-int(h.get('age',0)))
            with eve.store.db() as db:db.execute('INSERT OR REPLACE INTO contract_details VALUES(?,?,?,?,?,?)',(scope,oid,rid,now,expiry,json.dumps(rows)))
            result.update(items=rows,items_at=now);break
        except (EsiError,ValueError) as e:errors.append(str(e))
    else:result['error']=errors[-1] if errors else 'Nincs jogosult szerződésolvasó.'
    if result['items'] is not None:result['items']=[{**r,'name':catalog.name(r['type_id'])} for r in result['items']]
    return result
