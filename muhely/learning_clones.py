"""Compare owned training clones only after every linked character is offline."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import re
import threading
import time

from .esi import ESI, EsiError, LEARNING_CLONE_SCOPES
from .refresh_policy import AUTO_SECONDS, RefreshPolicy
from .skills import instant, validate_resource

ONLINE_SCOPE = 'esi-location.read_online.v1'
ATTRIBUTES = {164:175, 165:176, 166:177, 167:178, 168:179}
FRESH_SECONDS = 120


def schema(store):
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS learning_clone_status(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL)')


def enabled(store):
    from .notifications import preferences
    return preferences(store)['categories'].get('learning_clones', True)


def saved_status(store):
    schema(store)
    with store.db() as db:
        row=db.execute('SELECT data FROM learning_clone_status WHERE id=1').fetchone()
    return json.loads(row[0]) if row else {}


def validate(kind, body):
    def ids(value):
        return isinstance(value,list) and len(value)<=10 and all(type(i) is int and 0<i<=2**31-1 for i in value) and len(set(value))==len(value)
    if kind=='learning_online':
        if not isinstance(body,dict) or type(body.get('online')) is not bool:raise EsiError('Hiányos tanulóklón-adat.')
        for key in ['last_login','last_logout']:
            if body.get(key) is not None:instant(body[key])
    elif kind=='active_implants':
        if not ids(body):raise EsiError('Hiányos tanulóklón-adat.')
    elif kind=='skillqueue':validate_resource(kind,body)
    else:
        if not isinstance(body,dict) or not isinstance(body.get('jump_clones'),list):raise EsiError('Hiányos tanulóklón-adat.')
        seen=set()
        for clone in body['jump_clones']:
            if (not isinstance(clone,dict) or type(clone.get('jump_clone_id')) is not int or not 0<clone['jump_clone_id']<=2**53-1
                or clone['jump_clone_id'] in seen or not ids(clone.get('implants'))
                or type(clone.get('location_id')) is not int or not 0<clone['location_id']<=2**53-1
                or not isinstance(clone.get('name',''),str) or len(clone.get('name',''))>300):raise EsiError('Hiányos tanulóklón-adat.')
            seen.add(clone['jump_clone_id'])


def online_gate(store, now):
    chars=store.characters();snapshots={c['id']:store.snapshot(c['id'],'learning_online') for c in chars}
    fresh=lambda s:bool(s and s['expires']>now and 0<=now-s['fetched']<=FRESH_SECONDS)
    online=[c['name'] for c in chars if fresh(snapshots[c['id']]) and snapshots[c['id']]['data']['online']]
    if online:return 'online',True,snapshots,online
    if not chars or any(not s or s['data'].get('online') is not False for s in snapshots.values()):return 'unknown',False,snapshots,[]
    return 'offline',all(fresh(s) for s in snapshots.values()),snapshots,[]


def current_skill(queue, now):
    for entry in sorted(queue['data'],key=lambda r:r['queue_position']):
        if entry.get('start_date') and entry.get('finish_date') and instant(entry['start_date'])<=now<instant(entry['finish_date']):return entry['skill_id']
    return None


def metadata(store, tid):
    row=store.universe_cached('learning-type',tid)
    if not row:raise EsiError('A skill vagy implant attribútumadata még hiányzik.')
    return row['data']


def compare(store, cid, now):
    from .accounts import load as tracking
    accounts=tracking(store);pref=accounts['characters'].get(str(cid),{});mode=pref.get('training_mode','auto')
    account=next((a for a in accounts['accounts'] if a['id']==pref.get('account_id')),None)
    skill_snapshot=store.snapshot(cid,'skills');total_sp=(skill_snapshot or {}).get('data',{}).get('total_sp')
    alpha=bool(account and (account['omega_status']=='alpha' or account['omega_status']=='omega' and account['omega_expires'] is not None and account['omega_expires']<=now))
    blocked_slot=bool(account and mode in ['mct1','mct2'] and account[mode+'_expires'] is not None and account[mode+'_expires']<=now)
    if mode=='disabled' or blocked_slot or alpha and total_sp is not None and total_sp>=5000000:
        return {'status':'not_training','checked_at':now}
    online=store.snapshot(cid,'learning_online')
    parts={kind:store.snapshot(cid,kind) for kind in ['active_implants','jump_clones','skillqueue']}
    if not online or any(not p for p in parts.values()):raise EsiError('A tanulóklón ellenőrzéséhez még hiányzik adat.')
    logout=instant(online['data']['last_logout']) if online['data'].get('last_logout') else None
    for kind in ['active_implants','jump_clones']:
        if logout is not None and parts[kind]['fetched']<logout:raise EsiError('Az implant- vagy klónadat még a kijelentkezés előtti; várunk a friss EVE-adatra.')
    queue=parts['skillqueue'];skill=current_skill(queue,now)
    if skill is None:return {'status':'not_training','checked_at':min(p['fetched'] for p in parts.values())}
    skill_data=metadata(store,skill);attrs=skill_data['attributes']
    primary=attrs.get('180');secondary=attrs.get('181')
    if primary not in ATTRIBUTES or secondary not in ATTRIBUTES:raise EsiError('A skill tanulási attribútumai nem ismertek.')
    def score(ids):
        bonuses={k:0.0 for k in ATTRIBUTES.values()}
        for tid in ids:
            for key,value in metadata(store,tid)['attributes'].items():
                if int(key) in bonuses:bonuses[int(key)]+=value
        p,s=bonuses[ATTRIBUTES[primary]],bonuses[ATTRIBUTES[secondary]]
        return {'score':p+s/2,'primary_bonus':p,'secondary_bonus':s}
    active=score(parts['active_implants']['data']);best=None
    for clone in sorted(parts['jump_clones']['data']['jump_clones'],key=lambda c:c['jump_clone_id']):
        candidate={**clone,**score(clone['implants'])}
        if candidate['score']>active['score']+1e-9 and (best is None or candidate['score']>best['score']+1e-9):best=candidate
    return {'status':'better' if best else 'optimal','skill_id':skill,'skill_name':skill_data['name'],
            'primary_attribute':int(primary),'secondary_attribute':int(secondary),'active':active,
            'best':best,'checked_at':min(p['fetched'] for p in parts.values()),
            'fresh':all(p['expires']>now for p in parts.values())}


def alerts(store, now=None):
    now=time.time() if now is None else now
    chars=store.characters();domains=['learning-clone:'+str(c['id']) for c in chars]
    if not enabled(store):return {'items':[],'observed_domains':domains}
    gate,reliable,online,_=online_gate(store,now)
    if gate=='online':return {'items':[],'observed_domains':domains}
    if gate!='offline':return {'items':[],'observed_domains':[]}
    result=[];observed=[];report=saved_status(store);errors=report.get('errors',{})
    episode=sorted((cid,s['data'].get('last_logout')) for cid,s in online.items())
    for char in chars:
        domain='learning-clone:'+str(char['id'])
        try:row=compare(store,char['id'],now)
        except EsiError:continue
        valid=reliable and report.get('online_verified',False) and not report.get('running') and not report.get('queued') and not errors.get(str(char['id'])) and row.get('fresh',True)
        if valid:observed.append(domain)
        if row['status']!='better':continue
        best=row['best'];fingerprint=hashlib.sha256(json.dumps([episode,row['skill_id'],best['jump_clone_id'],row['active']],sort_keys=True).encode()).hexdigest()
        result.append({'id':domain,'domain':domain,'category':'learning_clones','kind':'learning_clone_better',
            'subject':char['name'],'character_name':char['name'],'character_id':char['id'],'corporation_id':None,
            'scope_name':'Személyes','when':None,'checked_at':row['checked_at'],'reliable':valid,'sound':True,
            'episode_key':fingerprint,'skill_name':row['skill_name'],'best_clone_name':best.get('name') or '',
            'best_clone_id':best['jump_clone_id'],'best_location_id':best['location_id'],
            'active_bonus':row['active']['score'],'best_bonus':best['score']})
    return {'items':result,'observed_domains':observed}


class LearningCloneWatch:
    def __init__(self,store,eve,clock=None):
        self.store=store;self.eve=eve;self.clock=clock or time.time;self.policy=RefreshPolicy(store)
        self.lock=threading.RLock();self.work_lock=threading.Lock();self.stop_event=threading.Event();self.wake=threading.Event()
        self.thread=None;self.manual=False
        self.state={'running':False,'phase':'','done':0,'total':0,'current':None,**saved_status(store)}
        self.state.update(running=False,queued=False,current=None)

    def update(self,**values):
        with self.lock:
            self.state.update(values)
            with self.store.db() as db:db.execute('INSERT OR REPLACE INTO learning_clone_status VALUES(1,?)',(json.dumps(self.state),))

    def fetch(self,cid,kind,path,scope,fallback,manual):
        now=self.clock();old=self.store.snapshot(cid,kind)
        if old and old['expires']>now:return old
        token=self.eve.token(cid,required_scopes=[scope])
        body,headers=self.eve.http.request(f'{ESI}/characters/{cid}/{path}/',token=token,headers={'If-None-Match':old['etag']} if old and old.get('etag') else {})
        h={k.lower():v for k,v in headers.items()}
        age=max(0,int(h.get('age',0)));match=re.search(r'max-age="?(\d+)',h.get('cache-control',''))
        ttl=int(match[1]) if match else fallback
        if not match and h.get('expires'):
            try:ttl=max(0,parsedate_to_datetime(h['expires']).timestamp()-now)+age
            except (ValueError,TypeError,OverflowError):pass
        observed=now-age
        if h.get('date'):
            try:observed=min(observed,parsedate_to_datetime(h['date']).timestamp())
            except (ValueError,TypeError,OverflowError):pass
        body=old['data'] if body is None and old else body;validate(kind,body)
        row={'data':body,'fetched':min(now,observed),'expires':now+max(0,ttl-age),'etag':h.get('etag') or (old or {}).get('etag')}
        if not self.stop_event.is_set():self.store.save_snapshots(cid,{kind:row},domain='learning_clones')
        return row

    def type(self,tid,manual=False):
        now=self.clock();old=self.store.universe_cached('learning-type',tid)
        if old and old['fetched']+30*86400>now:return old['data']
        if not self.policy.claim(['learning-type:'+str(tid)],manual,now):raise EsiError('A skill vagy implant attribútumadata még hiányzik.')
        body,_=self.eve.http.request(f'{ESI}/universe/types/{tid}/')
        if not isinstance(body,dict) or not isinstance(body.get('name'),str) or not isinstance(body.get('dogma_attributes'),list):raise EsiError('Hiányos tanulóklón-adat.')
        attributes={}
        for a in body['dogma_attributes']:
            if not isinstance(a,dict) or type(a.get('attribute_id')) is not int or type(a.get('value')) not in [int,float] or not math.isfinite(a['value']):raise EsiError('Hiányos tanulóklón-adat.')
            if 175<=a['attribute_id']<=181:attributes[str(a['attribute_id'])]=a['value']
        value={'name':body['name'],'attributes':attributes}
        if not self.stop_event.is_set():self.store.save_universe_cache('learning-type',tid,value,now)
        return value

    def tick(self,manual=False):
        if self.stop_event.is_set() or not self.work_lock.acquire(blocking=False):return
        try:
            chars=self.store.characters()
            if not enabled(self.store) or not chars:return
            if not self.policy.claim(['learning-clones:cycle'],manual,self.clock()):return
            granted=self.eve.granted_scopes();errors={}
            self.update(running=True,queued=False,online_verified=False,phase='Online állapotok ellenőrzése',done=0,total=len(chars)*2,current=None,errors={})
            for index,char in enumerate(chars):
                if self.stop_event.is_set():return
                cid=char['id'];self.update(current=char['name'],done=index)
                try:
                    if ONLINE_SCOPE not in granted.get(cid,[]):raise EsiError('Onlineállapot-olvasási engedély szükséges.')
                    self.fetch(cid,'learning_online','online',ONLINE_SCOPE,60,manual)
                except (EsiError,OSError,ValueError,TypeError) as exc:errors[str(cid)]=str(exc)
            gate,fresh,_,_=online_gate(self.store,self.clock())
            if gate!='offline' or not fresh or errors:
                self.update(phase='Van online karakter; nincs tanulóklón-riasztás.' if gate=='online' else 'Nem igazolt, hogy minden karakter offline.',errors=errors)
                return
            self.update(online_verified=True,phase='Klónok és tanulási attribútumok ellenőrzése')
            resources=[('active_implants','implants','esi-clones.read_implants.v1'),('jump_clones','clones','esi-clones.read_clones.v1'),('skillqueue','skillqueue','esi-skills.read_skillqueue.v1')]
            for index,char in enumerate(chars):
                if self.stop_event.is_set():return
                cid=char['id'];self.update(current=char['name'],done=len(chars)+index)
                try:
                    if not set(LEARNING_CLONE_SCOPES)<=set(granted.get(cid,[])):raise EsiError('Tanulóklón-olvasási engedély szükséges.')
                    parts={}
                    for kind,path,scope in resources:
                        if self.stop_event.is_set():return
                        parts[kind]=self.fetch(cid,kind,path,scope,120,manual)
                    skill=current_skill(parts['skillqueue'],self.clock())
                    if skill is not None:
                        ids=set(parts['active_implants']['data'])|{i for c in parts['jump_clones']['data']['jump_clones'] for i in c['implants']}|{skill}
                        for tid in sorted(ids):
                            if self.stop_event.is_set():return
                            self.type(tid,manual)
                    compare(self.store,cid,self.clock())
                except (EsiError,OSError,ValueError,TypeError) as exc:errors[str(cid)]=str(exc)
            self.update(errors=errors,phase='Tanulóklónok ellenőrizve.')
        finally:
            if self.state.get('running'):self.update(running=False,done=self.state['total'],current=None,checked_at=self.clock())
            self.work_lock.release()

    def dashboard(self):
        granted=self.eve.granted_scopes();gate,fresh,_,online=online_gate(self.store,self.clock());rows=[]
        with self.lock:status=dict(self.state)
        status['running']=bool(status.get('running') or status.get('queued'))
        for char in self.store.characters():
            cid=char['id'];row={'id':cid,'name':char['name'],'authorized':set(LEARNING_CLONE_SCOPES)<=set(granted.get(cid,[])),
                'online_access':ONLINE_SCOPE in granted.get(cid,[]),'status':'waiting','error':status.get('errors',{}).get(str(cid))}
            if gate=='offline':
                try:row.update(compare(self.store,cid,self.clock()))
                except EsiError as exc:row.update(status='unknown',error=str(exc))
            rows.append(row)
        return {'scopes':LEARNING_CLONE_SCOPES,'enabled':enabled(self.store),'gate':gate,'online_fresh':fresh,'online_characters':online,
                'status':status,'characters':rows,'next_check':self.policy.next_at(['learning-clones:cycle'])}

    def request(self):
        if self.stop_event.is_set() or not enabled(self.store) or not self.store.characters():return self.dashboard()
        self.update(queued=True)
        with self.lock:self.manual=True
        self.start();self.wake.set()
        return self.dashboard()

    def start(self):
        if self.stop_event.is_set() or self.thread and self.thread.is_alive():return
        self.thread=threading.Thread(target=self._work,daemon=True,name='EVE-learning-clones');self.thread.start()

    def _work(self):
        while not self.stop_event.is_set():
            with self.lock:manual=self.manual;self.manual=False
            try:self.tick(manual)
            except Exception:self.update(running=False,online_verified=False,phase='A tanulóklónok ellenőrzése nem sikerült.')
            self.wake.wait(10);self.wake.clear()

    def stop(self):
        self.stop_event.set();self.wake.set()
        if self.thread and self.thread is not threading.current_thread():self.thread.join(timeout=3)
