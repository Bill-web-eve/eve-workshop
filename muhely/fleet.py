"""Private local combat history, observed positions and conservative activity windows.

Only public zKillboard queries leave this module; SSO tokens go exclusively to ESI.
A killmail does not expose fleet membership or a historical route.
"""
from __future__ import annotations
from datetime import datetime, timezone
from bisect import bisect_left,bisect_right
from collections import defaultdict
from decimal import Decimal,ROUND_HALF_UP
from email.utils import parsedate_to_datetime
import copy,gzip,json,math,re,threading,time,urllib.error,urllib.request
from . import intel_universe,progress,battle
from .esi import ESI,EsiError,AuthenticationError,NoRedirect
from .planner import PlanningError,integer

LOCATION_SCOPE='esi-location.read_location.v1'
PROJECT='EVEWorkshop/1.2 (https://github.com/Bill-web-eve/eve-workshop)'
DEFAULTS={'tracking':True,'live':True,'interval_seconds':60,'gap_minutes':45,'padding_minutes':15,'character_ids':None}


def schema(store):
    with store.db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS fleet_settings(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fleet_kills(id INTEGER PRIMARY KEY,ts REAL NOT NULL,system_id INTEGER NOT NULL,data TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS fleet_kills_time ON fleet_kills(ts);
        CREATE TABLE IF NOT EXISTS fleet_positions(character_id INTEGER NOT NULL,ts REAL NOT NULL,system_id INTEGER NOT NULL,PRIMARY KEY(character_id,ts));
        CREATE INDEX IF NOT EXISTS fleet_positions_time ON fleet_positions(ts);
        CREATE TABLE IF NOT EXISTS fleet_sources(key TEXT PRIMARY KEY,data TEXT NOT NULL,checked REAL NOT NULL,expires REAL NOT NULL,error TEXT);
        CREATE TABLE IF NOT EXISTS fleet_live_buffer(id INTEGER PRIMARY KEY,ts REAL NOT NULL,system_id INTEGER NOT NULL,seen REAL NOT NULL,characters TEXT NOT NULL,data TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS fleet_live_buffer_window ON fleet_live_buffer(system_id,ts);
        CREATE INDEX IF NOT EXISTS fleet_live_buffer_seen ON fleet_live_buffer(seen);
        ''')


def preferences(store):
    with store.db() as db:row=db.execute('SELECT data FROM fleet_settings WHERE id=1').fetchone()
    return {**DEFAULTS,**(json.loads(row[0]) if row else {})}


def save_preferences(store,data):
    if not isinstance(data,dict) or set(data)-set(DEFAULTS):raise PlanningError('Hibás flottakövetési beállítás.')
    p=preferences(store)
    for key,value in data.items():
        if key in ['tracking','live']:
            if type(value) is not bool:raise PlanningError('Hibás flottakövetési beállítás.')
        elif key=='character_ids':
            ids={c['id'] for c in store.characters()}
            if value is not None and (not isinstance(value,list) or any(type(i) is not int or i not in ids for i in value)):raise PlanningError('Ismeretlen karakter.')
            if value is not None:value=list(dict.fromkeys(value))
        else:
            lo,hi={'interval_seconds':(30,900),'gap_minutes':(15,180),'padding_minutes':(15,60)}[key]
            value=integer(value,key,hi,lo)
        p[key]=value
    with store.db() as db:db.execute('INSERT OR REPLACE INTO fleet_settings VALUES(1,?)',(json.dumps(p),))
    return p


def timestamp(value):
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        if dt.tzinfo is None:raise ValueError()
        return dt.timestamp()
    except (ValueError,TypeError,AttributeError):raise EsiError('Hibás zKillboard-adat.') from None


def validate_kills(rows):
    if not isinstance(rows,list) or len(rows)>1000:raise EsiError('Hibás zKillboard-adat.')
    seen=set()
    for row in rows:
        if not isinstance(row,dict):raise EsiError('Hibás zKillboard-adat.')
        for key in ['killmail_id','solar_system_id']:
            if type(row.get(key)) is not int or row[key]<=0:raise EsiError('Hibás zKillboard-adat.')
        if row['killmail_id'] in seen:raise EsiError('Hibás zKillboard-adat.')
        seen.add(row['killmail_id']);timestamp(row.get('killmail_time'))
        if not isinstance(row.get('victim'),dict) or not isinstance(row.get('attackers'),list) or any(not isinstance(a,dict) for a in row['attackers']):raise EsiError('Hiányos zKillboard-adat; a korábbi adatok megmaradtak.')
        for field in ['totalValue','destroyedValue']:
            value=row.get('zkb',{}).get(field) if isinstance(row.get('zkb',{}),dict) else None
            if value is not None and (type(value) not in [int,float] or not math.isfinite(value) or value<0):raise EsiError('Hibás zKillboard-adat.')


def cache(store,key):
    with store.db() as db:r=db.execute('SELECT * FROM fleet_sources WHERE key=?',(key,)).fetchone()
    return {**dict(r),'data':json.loads(r['data'])} if r else None


def remember(store,key,data,checked,expires,error=None):
    with store.db() as db:db.execute('INSERT OR REPLACE INTO fleet_sources VALUES(?,?,?,?,?)',(key,json.dumps(data),checked,expires,error))


def save_kills(store,rows):
    validate_kills(rows)
    with store.db() as db:db.executemany('INSERT OR REPLACE INTO fleet_kills VALUES(?,?,?,?)',[(r['killmail_id'],timestamp(r['killmail_time']),r['solar_system_id'],json.dumps(r)) for r in rows])


def record_position(store,cid,sid,at):
    if type(cid) is not int or type(sid) is not int or not math.isfinite(at):return
    with store.db() as db:db.execute('INSERT OR IGNORE INTO fleet_positions VALUES(?,?,?)',(cid,at,sid))


def role(kill,cid):
    if kill['victim'].get('character_id')==cid:return 'loss'
    if any(a.get('character_id')==cid for a in kill['attackers']):return 'kill'
    return None


def participants(kill):
    return {a['character_id'] for a in kill['attackers'] if type(a.get('character_id')) is int}


def sessions(kills,positions,cid,p,universe):
    """Per-pilot temporal clusters. Never infer transit systems or actual fleet IDs.

    Distinct visits retain separate windows; merge only overlapping windows for a
    system. ESI samples supplement a kill-seeded session, never create a battle.
    Every system with kills retains the requested minimum +/-15 minute envelope.
    """
    own=sorted((k for k in kills if role(k,cid)),key=lambda k:(timestamp(k['killmail_time']),k['killmail_id']))
    groups=[]
    for k in own:
        if not groups or timestamp(k['killmail_time'])-timestamp(groups[-1][-1]['killmail_time'])>p['gap_minutes']*60:groups.append([])
        groups[-1].append(k)
    own_positions=sorted((r for r in positions if r['character_id']==cid),key=lambda r:r['ts'])
    sample_times=[r['ts'] for r in own_positions]
    result=[];pad=p['padding_minutes']*60
    for group in groups:
        first=timestamp(group[0]['killmail_time']);last=timestamp(group[-1]['killmail_time']);start=first-pad;end=last+pad
        points=[{'at':timestamp(k['killmail_time']),'system_id':k['solar_system_id'],'source':'kill','kill_id':k['killmail_id']} for k in group]
        points.extend({'at':r['ts'],'system_id':r['system_id'],'source':'esi','kill_id':None} for r in own_positions[bisect_left(sample_times,start):bisect_right(sample_times,end)])
        points.sort(key=lambda r:(r['at'],r['source']))
        visits=[]
        for pt in points:
            # A sampling gap is unknown travel, even when both endpoints agree.
            if not visits or pt['system_id']!=visits[-1]['system_id'] or pt['at']-visits[-1]['last']>max(p['interval_seconds']*2,pad*2):
                visits.append({'system_id':pt['system_id'],'first':pt['at'],'last':pt['at'],'kill_ids':[],'esi_samples':0,'kill_times':[]})
            v=visits[-1];v['last']=pt['at']
            if pt['source']=='kill':v['kill_ids'].append(pt['kill_id']);v['kill_times'].append(pt['at'])
            else:v['esi_samples']+=1
        windows=[]
        for index,v in enumerate(visits):
            sid=v['system_id'];info=universe.systems.get(sid,{})
            previous=visits[index-1] if index else None;following=visits[index+1] if index+1<len(visits) else None
            # With adjacent samples, arrival/departure is bounded by the two
            # observations. Do not claim an exact gate jump or interpolate a gap.
            lower=previous['last'] if previous and v['first']-previous['last']<=p['interval_seconds']*2 else v['first']-pad
            upper=following['first'] if following and following['first']-v['last']<=p['interval_seconds']*2 else v['last']+pad
            kill_start=min(v['kill_times'])-pad if v['kill_times'] else v['first']
            kill_end=max(v['kill_times'])+pad if v['kill_times'] else v['last']
            v.update(name=info.get('name',str(sid)),region=info.get('region',''),start=max(start,min(lower,kill_start)),end=min(end,max(upper,kill_end)))
            windows.append({'system_id':sid,'name':v['name'],'start':v['start'],'end':v['end'],'kill_ids':v['kill_ids'][:],'esi_samples':v['esi_samples']})
            del v['kill_times']
        merged=[]
        for w in sorted(windows,key=lambda r:(r['system_id'],r['start'])):
            if merged and merged[-1]['system_id']==w['system_id'] and w['start']<=merged[-1]['end']:
                merged[-1]['end']=max(w['end'],merged[-1]['end']);merged[-1]['kill_ids']+=w['kill_ids'];merged[-1]['esi_samples']+=w['esi_samples']
            else:merged.append(w.copy())
        allies=set().union(*(participants(k)-{cid} for k in group))
        result.append({'id':str(cid)+':'+str(group[0]['killmail_id']),'character_id':cid,'first':first,'last':last,'start':start,'end':end,
                       'kills':sum(role(k,cid)=='kill' for k in group),'losses':sum(role(k,cid)=='loss' for k in group),
                       'kill_ids':[k['killmail_id'] for k in group],'fleet_candidate':bool(allies),'other_attackers':len(allies),
                       'visits':visits,'windows':sorted(merged,key=lambda r:r['start']),'esi_samples':sum(v['esi_samples'] for v in visits)})
    return result


def session_value(kills,cid):
    """Whole killmail values, counted once. Participation is not damage credit.

    Keep destroyedValue distinct from totalValue (which also includes loot).
    Missing valuations remain explicit instead of silently becoming zero.
    """
    def bucket():return {'count':0,'cents':0,'missing':0,'destroyed_cents':0,'destroyed_missing':0}
    totals={key:bucket() for key in ['total','participation','losses']}
    unique={k['killmail_id']:k for k in kills}
    for k in unique.values():
        side=role(k,cid);keys=['total']+(['participation'] if side=='kill' else ['losses'] if side=='loss' else [])
        for key in keys:
            b=totals[key];b['count']+=1
            for field,out,missing in [('totalValue','cents','missing'),('destroyedValue','destroyed_cents','destroyed_missing')]:
                value=k.get('zkb',{}).get(field)
                if type(value) not in [int,float] or not math.isfinite(value) or value<0:b[missing]+=1
                else:b[out]+=int((Decimal(str(value))*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    total=totals['total'];part=totals['participation']
    percent=str((Decimal(part['cents'])*100/total['cents']).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) if total['cents'] and not total['missing'] else None
    for b in totals.values():
        b['cents']=str(b['cents']);b['destroyed_cents']=str(b['destroyed_cents'])
    return {**totals,'participation_percent':percent}


class ZKill:
    """One-hour persistent source cache, serial polite requests and cooldowns."""
    def __init__(self,store):self.store=store;self.lock=threading.RLock();self.last=0;self.opener=urllib.request.build_opener(NoRedirect())
    def query(self,path):
        if not re.fullmatch(r'(?:characterID|solarSystemID)/\d+/(?:year/\d{4}/month/\d{1,2}/)?page/\d+/',path):raise EsiError('Hibás zKillboard-lekérdezés.')
        with self.lock:
            now=time.time();old=cache(self.store,'zkill:'+path)
            if old and old['expires']>now:
                if old['error']:raise EsiError(old['error'])
                progress.resource('zKillboard',True);return old['data']
            cooldown=cache(self.store,'zkill:cooldown')
            if cooldown and cooldown['expires']>now:raise EsiError('A zKillboard lekérdezési korlátja miatt később próbáld újra.')
            time.sleep(max(0,1.1-(time.monotonic()-self.last)));self.last=time.monotonic()
            progress.resource('zKillboard');progress.report(mode='request')
            request=urllib.request.Request('https://zkillboard.com/api/'+path,headers={'User-Agent':PROJECT,'Accept-Encoding':'gzip','Accept':'application/json'})
            try:
                with self.opener.open(request,timeout=25) as response:
                    payload=response.read(16*1024*1024+1)
                    if len(payload)>16*1024*1024:raise EsiError('Túl nagy zKillboard-válasz.')
                    if response.headers.get('Content-Encoding')=='gzip':
                        import io
                        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as compressed:payload=compressed.read(32*1024*1024+1)
                    if len(payload)>32*1024*1024:raise EsiError('Túl nagy zKillboard-válasz.')
                    rows=json.loads(payload);validate_kills(rows)
                remember(self.store,'zkill:'+path,rows,time.time(),time.time()+3600);return rows
            except (OSError,ValueError,EsiError) as e:
                message='A zKillboard nem érhető el; a korábbi adatok megmaradtak.'
                delay=900
                if isinstance(e,urllib.error.HTTPError) and e.code in [420,429,503]:
                    message='A zKillboard lekérdezési korlátja miatt később próbáld újra.'
                    try:delay=max(900,min(86400,int(e.headers.get('Retry-After','900'))))
                    except ValueError:pass
                    remember(self.store,'zkill:cooldown',{},time.time(),time.time()+delay,message)
                remember(self.store,'zkill:'+path,(old or {}).get('data',[]),(old or {}).get('checked',0),time.time()+delay,message)
                raise EsiError(message) from None


class Fleet:
    def __init__(self,store,catalog,eve):
        self.store=store;self.catalog=catalog;self.eve=eve;schema(store);battle.schema(store)
        self.universe=intel_universe.load(store);self.zkill=ZKill(store)
        self.lock=threading.RLock();self.location_lock=threading.Lock();self.stop_event=threading.Event();self.thread=None
        self.state={'running':False,'kind':None,'completed':0,'total':0,'subject':'','resource':'','error':None,'finished':None,'results':[],'revision':0}
        self.location_status={'running':False,'character':'','checked':None}
        from .fleet_live import LiveFeed
        self.live=LiveFeed(self)
    def actors(self):
        p=preferences(self.store);return [c for c in self.store.characters() if p['character_ids'] is None or c['id'] in p['character_ids']]
    def start(self):
        if getattr(self,'closed',False):return
        if self.thread and self.thread.is_alive():return
        self.stop_event.clear();self.thread=threading.Thread(target=self._work,daemon=True,name='EVE-fleet-tracking');self.thread.start();self.live.start()
    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=3)
        if self.live.thread:self.live.thread.join(timeout=3)
    def _work(self):
        while not self.stop_event.is_set():
            try:
                if preferences(self.store)['tracking']:self.locations()
                # Public kill history refreshes independently of location sampling.
                actors=self.actors()
                if actors and not self.stop_event.is_set():
                    due=[c for c in actors if not (old:=cache(self.store,'character:'+str(c['id']))) or old['expires']<=time.time()]
                    if due:
                        with self.lock:busy=self.state['running']
                        if not busy:self.start_refresh()
                    name_check=cache(self.store,'live:names')
                    if preferences(self.store)['live'] and (not name_check or name_check['expires']<=time.time()):
                        with self.lock:busy=self.state['running']
                        if not busy:
                            remember(self.store,'live:names',{},time.time(),time.time()+900)
                            with self.store.db() as db:recent=[json.loads(r[0]) for r in db.execute('SELECT data FROM fleet_kills WHERE ts>=?',(time.time()-6*3600,))]
                            self.resolve_battle_names(recent)
            except Exception:
                with self.lock:self.location_status.update(running=False,checked=time.time())
            self.stop_event.wait(5)
    def locations(self):
        if not self.location_lock.acquire(blocking=False):return
        try:
            p=preferences(self.store)
            granted=self.eve.granted_scopes()
            for c in self.actors():
                if self.stop_event.is_set() or not preferences(self.store)['tracking']:break
                cid=c['id'];key='location:'+str(cid);old=cache(self.store,key);now=time.time()
                if old and old['expires']>now:continue
                if LOCATION_SCOPE not in granted.get(cid,[]):continue
                status=self.store.resource_status(cid,'intel_location')
                if status and status.get('needs_auth'):continue
                with self.lock:self.location_status.update(running=True,character=c['name'])
                try:
                    token=self.eve.token(cid,required_scopes=[LOCATION_SCOPE])
                    body,h=self.eve.http.request(f'{ESI}/characters/{cid}/location/',token=token,headers={'If-None-Match':old['data']['etag']} if old and old['data'].get('etag') else {})
                    h={k.lower():v for k,v in h.items()};data=old['data'].get('location') if body is None and old else body
                    if not isinstance(data,dict) or type(data.get('solar_system_id')) is not int or data['solar_system_id'] not in self.universe.systems:raise EsiError('Hiányos EVE-helyzetadat.')
                    age=max(0,int(h.get('age',0)));m=re.search(r'max-age="?(\d+)',h.get('cache-control',''));ttl=max(0,int(m[1])-age) if m else 5
                    at=time.time()
                    try:observed=min(at,parsedate_to_datetime(h['date']).timestamp()-age)
                    except (KeyError,ValueError,TypeError):observed=at-age
                    # Do not turn a cached repeated response into a new observation.
                    record_position(self.store,cid,data['solar_system_id'],observed)
                    remember(self.store,key,{'location':data,'etag':h.get('etag'),'observed':observed},at,at+max(p['interval_seconds'],ttl))
                except (EsiError,ValueError) as e:
                    remember(self.store,key,(old or {}).get('data',{}),(old or {}).get('checked',0),time.time()+max(900,p['interval_seconds']),str(e) if isinstance(e,EsiError) else 'Hiányos EVE-helyzetadat.')
            with self.lock:self.location_status.update(running=False,character='',checked=time.time())
        finally:self.location_lock.release()
    def status(self):
        with self.lock:state={'task':copy.deepcopy(self.state),'location':dict(self.location_status)}
        return {**state,'live':self.live.status()}
    def ingest_live(self,rows):
        """Keep own kills and matching session windows, not a global kill archive.

        A bounded six-hour staging buffer lets a newly received own kill discover
        surrounding losses that arrived earlier in the feed. Position samples
        can expand windows on subsequent polls without needing another kill.
        """
        validate_kills(rows);now=time.time();p=preferences(self.store);actors=self.actors();ids={c['id'] for c in actors}
        if not ids:return 0
        with self.store.db() as db:
            db.executemany('INSERT OR REPLACE INTO fleet_live_buffer VALUES(?,?,?,?,?,?)',[(k['killmail_id'],timestamp(k['killmail_time']),k['solar_system_id'],now,','+','.join(str(cid) for cid in participants(k)|{k['victim'].get('character_id')} if type(cid) is int)+',',json.dumps(k)) for k in rows])
            db.execute('DELETE FROM fleet_live_buffer WHERE seen<?',(now-6*3600,))
            db.execute('DELETE FROM fleet_live_buffer WHERE id IN (SELECT id FROM fleet_live_buffer ORDER BY seen DESC,id DESC LIMIT -1 OFFSET 10000)')
            own={}
            for r in db.execute('SELECT data FROM fleet_kills WHERE ts>=?',(now-90*86400,)):
                k=json.loads(r[0])
                if any(role(k,cid) for cid in ids):own[k['killmail_id']]=k
            for r in db.execute('SELECT data FROM fleet_live_buffer WHERE '+' OR '.join('characters LIKE ?' for _ in ids),tuple('%,'+str(cid)+',%' for cid in ids)):
                k=json.loads(r[0])
                if any(role(k,cid) for cid in ids):own[k['killmail_id']]=k
            selected=own.copy()
            for cid in ids:
                positions={}
                for seed in sessions(list(own.values()),[],cid,p,self.universe):
                    for r in db.execute('SELECT * FROM fleet_positions WHERE character_id=? AND ts>=? AND ts<=?',(cid,seed['start'],seed['end'])):positions[r['ts']]=dict(r)
                for session in sessions(list(own.values()),list(positions.values()),cid,p,self.universe):
                    for w in session['windows']:
                        for r in db.execute('SELECT data FROM fleet_live_buffer WHERE system_id=? AND ts>=? AND ts<=?',(w['system_id'],w['start'],w['end'])):
                            k=json.loads(r[0]);selected[k['killmail_id']]=k
            changed=0
            for k in selected.values():
                body=json.dumps(k);old=db.execute('SELECT data FROM fleet_kills WHERE id=?',(k['killmail_id'],)).fetchone()
                if old and old[0]==body:continue
                db.execute('INSERT OR REPLACE INTO fleet_kills VALUES(?,?,?,?)',(k['killmail_id'],timestamp(k['killmail_time']),k['solar_system_id'],body));changed+=1
        return changed
    def _progress(self,values):
        with self.lock:self.state.update({k:v for k,v in values.items() if k in ['completed','total','subject','resource','page','pages','mode']})
    def start_refresh(self,cid=None,session_id=None):
        if cid is not None:
            cid=integer(cid,'Karakter',2**31-1,1)
            if cid not in {c['id'] for c in self.store.characters()}:raise PlanningError('Ismeretlen karakter.')
        session=None
        if session_id is not None:
            if not isinstance(session_id,str) or len(session_id)>80:raise PlanningError('Ismeretlen flottamenet.')
            session=next((s for s in self.dashboard()['sessions'] if s['id']==session_id),None)
            if not session:raise PlanningError('Ismeretlen flottamenet.')
        with self.lock:
            if self.state['running']:raise PlanningError('Egy flottalekérdezés már folyamatban van.')
            self.state.update(running=True,kind='report' if session else 'kills',completed=0,total=0,subject='',resource='',error=None,finished=None,results=[],page=None,pages=None)
        def work():
            try:
                with progress.listen(self._progress):results=self.context(session) if session else self.sync_kills(cid)
                with self.lock:self.state['results']=results
            except Exception as e:
                with self.lock:self.state['error']=str(e) if isinstance(e,(PlanningError,EsiError)) else 'A flottalekérdezés nem sikerült; a korábbi adatok megmaradtak.'
            finally:
                with self.lock:self.state.update(running=False,finished=time.time(),revision=self.state['revision']+1)
        threading.Thread(target=work,daemon=True,name='EVE-fleet-kills').start();return {'started':True}
    def sync_kills(self,cid=None):
        actors=[c for c in (self.store.characters() if cid is not None else self.actors()) if cid is None or c['id']==cid];results=[];cutoff=time.time()-30*86400
        for c in progress.items(actors):
            rows=[];complete=False;key='character:'+str(c['id'])
            try:
                for page in range(1,6):
                    if self.stop_event.is_set():break
                    progress.report(page=page,pages=5)
                    batch=self.zkill.query(f"characterID/{c['id']}/page/{page}/");rows.extend(batch)
                    if len(batch)<200 or (batch and min(timestamp(k['killmail_time']) for k in batch)<=cutoff):complete=True;break
                save_kills(self.store,list({k['killmail_id']:k for k in rows}.values()))
                remember(self.store,key,{'complete':complete,'oldest':min((timestamp(k['killmail_time']) for k in rows),default=None)},time.time(),time.time()+3600)
                results.append({'id':c['id'],'name':c['name'],'ok':True,'partial':not complete})
            except EsiError as e:
                old=cache(self.store,key);remember(self.store,key,(old or {}).get('data',{}),(old or {}).get('checked',0),time.time()+900,str(e));results.append({'id':c['id'],'name':c['name'],'ok':False,'error':str(e)})
        return results
    def context(self,s):
        queries={}
        for w in s['windows']:
            current=datetime.fromtimestamp(w['start'],timezone.utc);finish=datetime.fromtimestamp(w['end'],timezone.utc)
            while (current.year,current.month)<=(finish.year,finish.month):
                key=(w['system_id'],current.year,current.month);queries[key]=min(queries.get(key,w['start']),w['start'])
                current=current.replace(year=current.year+(current.month==12),month=current.month%12+1,day=1)
        results=[];budget=20
        for index,((sid,year,month),start) in enumerate(sorted(queries.items())):
            progress.report(completed=index,total=len(queries),subject=self.universe.systems.get(sid,{}).get('name',str(sid)))
            full=False;error=None;rows=[]
            try:
                for page in range(1,6):
                    if budget<=0 or self.stop_event.is_set():break
                    budget-=1;progress.report(page=page,pages=5)
                    batch=self.zkill.query(f'solarSystemID/{sid}/year/{year}/month/{month}/page/{page}/')
                    rows.extend(k for k in batch if any(w['system_id']==k['solar_system_id'] and w['start']<=timestamp(k['killmail_time'])<=w['end'] for w in s['windows']))
                    if len(batch)<200 or min(timestamp(k['killmail_time']) for k in batch)<=start:full=True;break
                save_kills(self.store,list({k['killmail_id']:k for k in rows}.values()))
            except EsiError as e:error=str(e)
            results.append({'system_id':sid,'year':year,'month':month,'ok':not error,'partial':not full,'error':error})
        self.resolve_battle_names([json.loads(r[0]) for r in self._battle_kill_rows(s['windows'])])
        progress.report(completed=len(queries),total=len(queries))
        remember(self.store,'report:'+s['id'],{'results':results,'windows':s['windows']},time.time(),time.time()+3600)
        return results
    def _battle_kill_rows(self,windows):
        found={}
        with self.store.db() as db:
            for w in windows:
                for r in db.execute('SELECT data,id FROM fleet_kills WHERE system_id=? AND ts>=? AND ts<=?',(w['system_id'],w['start'],w['end'])):found[r['id']]=r
        return list(found.values())
    def resolve_battle_names(self,kills):
        old=cache(self.store,'battle-names');names=(old or {}).get('data',{}).copy();now=time.time()
        ids=battle.name_ids(kills)
        missing=[i for i in ids if str(i) not in names or (old or {}).get('expires',0)<=now]
        blocked=cache(self.store,'battle-name-errors')
        if not missing or blocked and blocked['expires']>now:return
        try:
            for start in range(0,len(missing),1000):
                batch=missing[start:start+1000];progress.resource('Harci résztvevők nevei');progress.report(mode='request')
                rows,_=self.eve.http.request(ESI+'/universe/names/',json_body=batch)
                if not isinstance(rows,list) or any(not isinstance(r,dict) or r.get('id') not in batch or not isinstance(r.get('name'),str) or r.get('category') not in ['alliance','corporation','character'] for r in rows):raise EsiError('Hiányos résztvevőnév-adat.')
                names.update({str(r['id']):{'name':r['name'],'category':r['category']} for r in rows})
            remember(self.store,'battle-names',names,time.time(),time.time()+30*86400)
        except EsiError:
            remember(self.store,'battle-name-errors',{},time.time(),time.time()+900,'A résztvevőnevek egy része nem frissült; az azonosítók láthatók.')
    def configure_sides(self,data):
        sid=data.get('session_id')
        if not isinstance(sid,str) or not re.fullmatch(r'\d+:\d+',sid):raise PlanningError('Ismeretlen flottamenet.')
        session=next((s for s in self.dashboard()['sessions'] if s['id']==sid),None)
        if not session:raise PlanningError('Ismeretlen flottamenet.')
        known={g['key'] for side in [*session['battle']['sides'],session['battle']['unassigned']] for g in side['groups']}
        battle.save(self.store,sid,data,known,battle.configuration(self.store,sid,session['kill_ids']));return {'ok':True}
    def dashboard(self):
        p=preferences(self.store);chars=self.store.characters();names={c['id']:c['name'] for c in chars};now=time.time();granted=self.eve.granted_scopes()
        with self.store.db() as db:
            kills=[json.loads(r[0]) for r in db.execute('SELECT data FROM fleet_kills WHERE ts>=? ORDER BY ts',(now-90*86400,))]
        by_system=defaultdict(list)
        for k in kills:by_system[k['solar_system_id']].append(k)
        system_times={sid:[timestamp(k['killmail_time']) for k in rows] for sid,rows in by_system.items()}
        names_cache=(cache(self.store,'battle-names') or {}).get('data',{})
        activity=[];access=[]
        for c in chars:
            # Read only kill-seeded intervals, not months of minute-by-minute
            # tracking with no combat. The (pilot,time) primary key bounds reads.
            positions={}
            with self.store.db() as db:
                for seed in sessions(kills,[],c['id'],p,self.universe):
                    for r in db.execute('SELECT * FROM fleet_positions WHERE character_id=? AND ts>=? AND ts<=? ORDER BY ts',(c['id'],seed['start'],seed['end'])):positions[r['ts']]=dict(r)
            for s in sessions(kills,list(positions.values()),c['id'],p,self.universe):
                s['character_name']=c['name'];status=cache(self.store,'report:'+s['id'])
                s['report']=status
                context={}
                for w in s['windows']:
                    sid=w['system_id'];ts=system_times.get(sid,[]);rows=by_system.get(sid,[])
                    for k in rows[bisect_left(ts,w['start']):bisect_right(ts,w['end'])]:context[k['killmail_id']]=k
                context=list(context.values())
                s['rows']=[self.row(k,c['id']) for k in sorted(context,key=lambda r:timestamp(r['killmail_time']))]
                s['context_count']=len(context);s['value_summary']=session_value(context,c['id'])
                s['battle']=battle.build(context,c['id'],battle.configuration(self.store,s['id'],s['kill_ids']),names_cache,session_value)
                activity.append(s)
            source=cache(self.store,'character:'+str(c['id']));loc=cache(self.store,'location:'+str(c['id']));sid=(loc or {}).get('data',{}).get('location',{}).get('solar_system_id')
            access.append({'id':c['id'],'name':c['name'],'checked':(source or {}).get('checked'),'next_check':(source or {}).get('expires'),'error':(source or {}).get('error'),'complete':(source or {}).get('data',{}).get('complete',False),
                           'location_access':LOCATION_SCOPE in granted.get(c['id'],[]),'location_checked':(loc or {}).get('data',{}).get('observed'),'location_error':(loc or {}).get('error'),'system':self.universe.systems.get(sid,{}).get('name'),'selected':p['character_ids'] is None or c['id'] in p['character_ids']})
        own=[k for k in kills if any(role(k,cid) for cid in names)]
        with self.lock:status=copy.deepcopy(self.state);location_status=copy.deepcopy(self.location_status)
        return {'preferences':p,'characters':access,'sessions':sorted(activity,key=lambda s:-s['last']),
                'kills':[self.row(k,None,names) for k in sorted(own,key=lambda k:-timestamp(k['killmail_time']))],
                'status':status,'location_status':location_status,'live_status':self.live.status(),'calculated_at':now}
    def row(self,k,cid=None,names=None):
        value=k.get('zkb',{}).get('totalValue');victim=k['victim'];at=timestamp(k['killmail_time']);sid=k['solar_system_id']
        return {'id':k['killmail_id'],'at':at,'system_id':sid,'system':self.universe.systems.get(sid,{}).get('name',str(sid)),
                'ship_id':victim.get('ship_type_id'),'ship':self.catalog.name(victim.get('ship_type_id',0)),
                'victim_id':victim.get('character_id'),'value':value,'attackers':len(participants(k)),
                'role':role(k,cid) if cid else None,'characters':[{'id':i,'name':n,'role':role(k,i)} for i,n in (names or {}).items() if role(k,i)]}
