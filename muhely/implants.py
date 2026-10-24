"""Observe dock-to-space transitions; price only the active clone's implants."""
from decimal import Decimal,InvalidOperation
from email.utils import parsedate_to_datetime
import json,re,secrets,threading,time
from .esi import ESI,EsiError,IMPLANT_SCOPES
from .planner import PlanningError

DEFAULT_THRESHOLD='1000000000'


def schema(store):
    with store.db() as db:db.executescript('''
        CREATE TABLE IF NOT EXISTS implant_watch_preferences(character_id INTEGER PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS implant_watch_status(character_id INTEGER PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS implant_undock_events(id TEXT PRIMARY KEY,character_id INTEGER NOT NULL,at REAL NOT NULL,data TEXT NOT NULL);
    ''')


def preferences(store):
    schema(store)
    with store.db() as db:rows={r[0]:json.loads(r[1]) for r in db.execute('SELECT * FROM implant_watch_preferences')}
    return {c['id']:{'enabled':False,'threshold':DEFAULT_THRESHOLD,**rows.get(c['id'],{})} for c in store.characters()}


def save_preferences(store,data):
    if not isinstance(data,dict) or set(data)!={'characters'} or not isinstance(data['characters'],list):raise PlanningError('Hibás implantfigyelési beállítás.')
    known=preferences(store);updates={}
    for row in data['characters']:
        if not isinstance(row,dict) or set(row)!={'id','enabled','threshold'} or type(row['id']) is not int or row['id'] not in known or row['id'] in updates or type(row['enabled']) is not bool:raise PlanningError('Hibás implantfigyelési karakter.')
        try:value=Decimal(str(row['threshold']))
        except InvalidOperation:raise PlanningError('Érvénytelen implantérték-határ.') from None
        if not value.is_finite() or value<0 or value>10**15 or value.as_tuple().exponent < -4:raise PlanningError('Érvénytelen implantérték-határ.')
        updates[row['id']]={'enabled':row['enabled'],'threshold':format(value,'f')}
    with store.db() as db:
        for cid,row in updates.items():db.execute('INSERT OR REPLACE INTO implant_watch_preferences VALUES(?,?)',(cid,json.dumps(row)))
    return preferences(store)


def events(store,now=None):
    schema(store);now=time.time() if now is None else now
    enabled={cid for cid,p in preferences(store).items() if p['enabled']}
    with store.db() as db:
        db.execute('DELETE FROM implant_undock_events WHERE at<?',(now-86400,))
        return [json.loads(r['data']) for r in db.execute('SELECT * FROM implant_undock_events WHERE at>=?',(now-300,)) if r['character_id'] in enabled]


class ImplantWatch:
    def __init__(self,store,catalog,eve,market,clock=None):
        self.store=store;self.catalog=catalog;self.eve=eve;self.market=market;self.clock=clock or time.time
        self.previous={};self.pending={};self.next_location={};self.active={};self.lock=threading.Lock()
        schema(store)

    def status(self,cid,**changes):
        with self.store.db() as db:
            old=db.execute('SELECT data FROM implant_watch_status WHERE character_id=?',(cid,)).fetchone()
            value={**(json.loads(old[0]) if old else {}),**changes}
            db.execute('INSERT OR REPLACE INTO implant_watch_status VALUES(?,?)',(cid,json.dumps(value)))

    def dashboard(self):
        prefs=preferences(self.store);granted=self.eve.granted_scopes()
        with self.store.db() as db:status={r[0]:json.loads(r[1]) for r in db.execute('SELECT * FROM implant_watch_status')}
        return {'scopes':IMPLANT_SCOPES,'characters':[{'id':c['id'],'name':c['name'],**prefs[c['id']],
                'authorized':set(IMPLANT_SCOPES)<=set(granted.get(c['id'],[])),**status.get(c['id'],{})} for c in self.store.characters()]}

    def fetch(self,cid,kind,path,minimum,token,now):
        old=self.store.snapshot(cid,kind)
        if old and old['expires']>now:return old
        body,h=self.eve.http.request(f'{ESI}/characters/{cid}/{path}/',token=token,headers={'If-None-Match':old['etag']} if old and old.get('etag') else {})
        h={k.lower():v for k,v in h.items()};age=max(0,int(h.get('age',0)))
        match=re.search(r'max-age="?(\d+)',h.get('cache-control',''));ttl=max(minimum,int(match[1]) if match else minimum)
        try:observed=min(now,parsedate_to_datetime(h['date']).timestamp()-age)
        except (KeyError,ValueError,TypeError):observed=now-age
        if body is None:
            if not old:raise EsiError('Hiányos implantfigyelési EVE-adat.')
            body=old['data']
        if kind=='active_implants':
            if not isinstance(body,list) or len(body)>10 or any(type(i) is not int or i<=0 for i in body) or len(set(body))!=len(body):raise EsiError('Hiányos implantfigyelési EVE-adat.')
        elif not isinstance(body,dict) or type(body.get('solar_system_id')) is not int or any(k in body and (type(body[k]) is not int or body[k]<=0) for k in ['station_id','structure_id']):raise EsiError('Hiányos implantfigyelési EVE-adat.')
        row={'data':body,'fetched':observed,'expires':now+max(5,ttl-age),'etag':h.get('etag') or (old or {}).get('etag')}
        self.store.save_snapshots(cid,{kind:row},domain='implants');return row

    def tick(self,stop_event):
        if not self.lock.acquire(blocking=False):return
        try:
            prefs=preferences(self.store);enabled={cid:p for cid,p in prefs.items() if p['enabled']}
            for cid in set(self.active)|set(enabled):
                if self.active.get(cid)!=enabled.get(cid):
                    self.previous.pop(cid,None);self.pending.pop(cid,None);self.next_location.pop(cid,None)
            self.active=enabled
            if not enabled:return
            granted=self.eve.granted_scopes();chars={c['id']:c for c in self.store.characters()}
            for cid,p in enabled.items():
                if stop_event.is_set():break
                now=self.clock()
                if self.next_location.get(cid,0)>now:continue
                if not set(IMPLANT_SCOPES)<=set(granted.get(cid,[])):
                    self.status(cid,error='Implantfigyelési engedély szükséges.',checking=False);continue
                self.next_location[cid]=now+5
                self.status(cid,checking=True,error=None)
                try:
                    token=self.eve.token(cid,required_scopes=IMPLANT_SCOPES)
                    loc=self.fetch(cid,'implant_location','location',5,token,now)
                    if now-loc['fetched']>15:raise EsiError('Korábbi helyzetadat; a kidokkolás nem ellenőrizhető.')
                    docked=bool(loc['data'].get('station_id') or loc['data'].get('structure_id'));previous=self.previous.get(cid)
                    if previous and previous['docked'] and not docked and 0<loc['fetched']-previous['at']<=30:
                        self.pending[cid]={'key':secrets.token_hex(16),'at':now,'system_id':loc['data']['solar_system_id']}
                    if not previous or loc['fetched']>previous['at']:self.previous[cid]={'docked':docked,'at':loc['fetched']}
                    if docked:self.pending.pop(cid,None)
                    if stop_event.is_set():break
                    implants=self.fetch(cid,'active_implants','implants',120,token,now)
                    if now-implants['fetched']>180:raise EsiError('Az aktív klón implantadata még nem frissült.')
                    ids=implants['data'];self.market.start(ids)
                    quotes=self.market.snapshot(ids)['quotes'];total=Decimal(0);missing=[]
                    for tid in ids:
                        q=quotes.get(str(tid));price=(q or {}).get('sell')
                        if price is None or now-q['checked']>1800:missing.append(tid)
                        else:total+=Decimal(price)
                    self.status(cid,checking=False,docked=docked,checked_at=loc['fetched'],implants_at=implants['fetched'],
                                value=format(total,'f'),missing=missing,implant_count=len(ids),error=None)
                    pending=self.pending.get(cid)
                    if pending and now-pending['at']>120:self.pending.pop(cid,None);pending=None
                    if pending and total>Decimal(p['threshold']):
                        if stop_event.is_set() or preferences(self.store).get(cid)!=p:continue
                        item={'id':'implants:'+pending['key'],'domain':'implants:'+str(cid),'category':'implants','kind':'implant_undock',
                              'subject':chars[cid]['name'],'character_name':chars[cid]['name'],'character_id':cid,
                              'corporation_id':None,'scope_name':'Személyes','when':pending['at'],'checked_at':loc['fetched'],
                              'reliable':True,'sound':True,'value':format(total,'f'),'threshold':p['threshold'],
                              'partial':bool(missing),'implants_at':implants['fetched'],'system_id':pending['system_id']}
                        with self.store.db() as db:db.execute('INSERT OR IGNORE INTO implant_undock_events VALUES(?,?,?,?)',(item['id'],cid,pending['at'],json.dumps(item)))
                        self.pending.pop(cid,None)
                    elif pending and not missing:self.pending.pop(cid,None)
                except (EsiError,OSError,ValueError,InvalidOperation) as error:
                    self.next_location[cid]=self.clock()+30
                    self.status(cid,checking=False,error=str(error) if isinstance(error,EsiError) else 'Az implantfigyelés adatai nem frissültek.')
        finally:self.lock.release()
