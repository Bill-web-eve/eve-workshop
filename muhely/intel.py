"""Local EVE chat-log intel. Chat contents never leave this computer."""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from collections import defaultdict
import hashlib,html,json,os,re,stat,threading,time
from .planner import PlanningError
from .esi import ESI,EsiError,AuthenticationError,INTEL_SCOPES
from . import intel_universe

DEFAULTS={'enabled':False,'folder':'','channels':[],'character_ids':None,'manual_locations':{},'jumps':5,'ttl_minutes':20,'cooldown_seconds':20,'region_ids':[],'allow_local_alerts':False,'sound':False}
FILE=re.compile(r'^(?P<channel>.+)_(?P<date>\d{8})_(?P<time>\d{6})_(?P<character>\d+)\.txt$',re.I)
LINE=re.compile(r'^\ufeff*\[\s*(\d{4}\.\d\d\.\d\d \d\d:\d\d:\d\d)\s*\]\s*([^>]{1,100})>\s*(.*)$')
LINK=re.compile(r'<url=["\']?showinfo:(137[3-9]|138[0-6])//(\d+)["\']?>(.*?)</url>',re.I)
STOP=re.compile(r'\b(?:on|at|in|to|from|towards|gate|gates|out|of|with|and|plus|jumped|jumping|jump|left|leaving|reported|seen|was|is|are|no|visual|nv|ni|onlined|docked|undocked|likely|maybe|possibly|spike|spiked|spiking|clear|clr|cleared|loc|pls|please|status|check|checkin|check-in|help|scan|scanned|reported|still|just|now|local|heading|destination|need|needle|red|reds|new|ago|minutes?|minute|min|camp|camping|for|the|a|an|cloaked|cloak|suspect|scout|unknown|neut|neuts|neutral|hostile|hostiles|fleets?|tackled)\b',re.I)


def schema(store):
    with store.db() as db:db.executescript('''
        CREATE TABLE IF NOT EXISTS intel_config(id INTEGER PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS intel_files(id TEXT PRIMARY KEY,device INTEGER,inode INTEGER,offset INTEGER,encoding TEXT,channel TEXT,seen REAL);
        CREATE TABLE IF NOT EXISTS intel_reports(id TEXT PRIMARY KEY,ts REAL,channel TEXT,reporter TEXT,body TEXT,data TEXT,received REAL);
        CREATE INDEX IF NOT EXISTS intel_report_time ON intel_reports(ts);
        CREATE TABLE IF NOT EXISTS intel_local_positions(character_id INTEGER PRIMARY KEY,data TEXT);
        CREATE TABLE IF NOT EXISTS intel_status(id INTEGER PRIMARY KEY,data TEXT);
    ''')


def preferences(store):
    schema(store)
    with store.db() as db:row=db.execute('SELECT data FROM intel_config WHERE id=1').fetchone()
    return {**DEFAULTS,**(json.loads(row['data']) if row else {})}


def save_preferences(store,data,universe):
    if not isinstance(data,dict) or set(data)-set(DEFAULTS):raise PlanningError('Hibás intelbeállítás.')
    p=preferences(store);known={c['id'] for c in store.characters()}
    for key,value in data.items():
        if key in ['enabled','allow_local_alerts','sound']:
            if type(value) is not bool:raise PlanningError('Hibás intelkapcsoló.')
        elif key=='folder':
            if not isinstance(value,str) or len(value)>2000:raise PlanningError('Hibás chatlogmappa.')
            value=str(Path(value).expanduser().resolve()) if value.strip() else ''
            if value and not Path(value).is_dir():raise PlanningError('A chatlogmappa nem érhető el. Válassz létező mappát.')
        elif key=='channels':
            if not isinstance(value,list) or len(value)>100 or any(not isinstance(c,str) or not c.strip() or len(c)>160 for c in value):raise PlanningError('Hibás intelcsatorna-lista.')
            value=list(dict.fromkeys(c.strip() for c in value))
        elif key=='character_ids':
            if value is not None and (not isinstance(value,list) or any(type(v) is not int or v not in known for v in value)):raise PlanningError('Ismeretlen intelkarakter.')
            if value is not None:value=list(dict.fromkeys(value))
        elif key=='manual_locations':
            if not isinstance(value,dict) or any(not isinstance(k,str) or not k.isdigit() or int(k) not in known or type(v) is not int or v not in universe.systems for k,v in value.items()):raise PlanningError('Hibás kézi intelhelyszín.')
        elif key=='region_ids':
            valid={r['region_id'] for r in universe.systems.values()}
            if not isinstance(value,list) or any(type(v) is not int or v not in valid for v in value):raise PlanningError('Ismeretlen intelrégió.')
        else:
            low,high={'jumps':(0,30),'ttl_minutes':(1,120),'cooldown_seconds':(0,600)}[key]
            if type(value) is not int or not low<=value<=high:raise PlanningError('Az intelérték kívül esik a megengedett tartományon.')
        p[key]=value
    if p['enabled'] and (not p['folder'] or not p['channels']):raise PlanningError('A figyeléshez válassz chatlogmappát és legalább egy csatornát.')
    with store.db() as db:db.execute('INSERT OR REPLACE INTO intel_config VALUES(1,?)',(json.dumps(p),))
    return p


def parse_message(line,universe,channel,channel_id,now=None,regions=()):
    match=LINE.match(line.strip());now=time.time() if now is None else now
    if not match:return None
    date,reporter,body=match.groups();reporter=reporter.strip();body=body[:4000]
    if reporter.casefold() in ['eve system','eve-system']:return None
    try:at=datetime.strptime(date,'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
    except ValueError:return None
    if at>now+60:return None
    linked=[{'name':html.unescape(re.sub('<[^>]+>','',m[3])).strip(),'id':int(m[2]),'verified':True} for m in LINK.finditer(body)]
    plain=html.unescape(re.sub('<[^>]+>','',body))
    # A linked character can be named after a system. Do not parse their name as a location.
    searching=LINK.sub(lambda m:' '*len(m.group()),body)
    mentions=universe.mentions(searching,regions)
    ids=list(dict.fromkeys(sid for sid,_,_ in mentions))
    arrow=bool(re.search(r'(?:->|→|=>)',plain))
    if arrow and len(ids)>1:ids=ids[-1:]
    question='?' in plain
    is_clear=bool(re.search(r'(?<!\w)(?:clr|clear|cleared|tiszta)(?!\w)',plain,re.I)) and not re.search(r'\b(?:not|no|nem)\s+(?:clr|clear|cleared|tiszta)\b',plain,re.I)
    state='query' if question else 'clear' if is_clear else 'contact' if ids else 'unparsed'
    text=plain
    for _,(start,end),_ in reversed(mentions):
        # Linked markup can change offsets; full-name removal below also handles that case.
        if '<' not in body:text=text[:start]+' '*max(1,end-start)+text[end:]
    text=universe.pattern.sub(' ',text);text=universe.ship_pattern.sub(' ',text)
    text=LINK.sub(' ',text)
    for pilot in linked:text=text.replace(pilot['name'],' ')
    candidates=[]
    for chunk in re.split(r'[|,;:()\[\]<>/]|(?:\s+[+\-]\s*)|(?:->|→|=>)',text):
        parts=STOP.split(chunk)
        for part in parts:
            name=re.sub(r'\s+',' ',part).strip(' .!*+"\t-')
            if 2<=len(name)<=64 and len(name.split())<=4 and re.search('[A-Za-zÀ-ž]',name) and re.fullmatch(r"[\w .’'\-]+",name) and not name.isdigit():
                if name.casefold() not in {p['name'].casefold() for p in linked}:candidates.append({'name':name,'id':None,'verified':False})
    pilots=list({p['name'].casefold():p for p in linked+candidates}.values())[:12] if state=='contact' else []
    count=re.search(r'(?:\+|\bspike\s+)(\d{1,5})\b',plain,re.I)
    key='\0'.join([channel_id or channel.casefold(),date,reporter,body]);identity=hashlib.sha256(key.encode()).hexdigest()
    return {'id':identity,'timestamp':at,'channel':channel,'reporter':reporter,'message':body,'systems':ids,'pilots':pilots,'state':state,'count':min(10000,int(count[1])) if count else len(pilots) or None,'ambiguous':len(ids)>1,'abbreviated':any(short for _,_,short in mentions)}


def selected_characters(store,p):return [c for c in store.characters() if p['character_ids'] is None or c['id'] in p['character_ids']]


def positions(store,universe,p,now):
    result=[]
    with store.db() as db:locals={r['character_id']:json.loads(r['data']) for r in db.execute('SELECT * FROM intel_local_positions')}
    for char in selected_characters(store,p):
        cid=char['id'];manual=p['manual_locations'].get(str(cid));snap=store.snapshot(cid,'intel_position');status=store.resource_status(cid,'intel_location') or {}
        row={'id':cid,'name':char['name'],'system_id':None,'source':'unknown','as_of':None,'alertable':False,'needs_auth':bool(status.get('needs_auth',True)),'error':status.get('error'),'online':None}
        if manual in universe.systems:row.update(system_id=manual,source='manual',alertable=True)
        elif snap and snap['expires']>now and not status.get('error'):
            data=snap['data'];fresh=snap['expires']>now and not status.get('error')
            row.update(system_id=data.get('solar_system_id'),source='esi',as_of=snap['fetched'],online=data.get('online'),alertable=fresh and data.get('online') is True,needs_auth=bool(status.get('needs_auth')))
        elif cid in locals and (not snap or locals[cid]['checked']>=snap['fetched']):
            data=locals[cid];row.update(system_id=data['system_id'],source='local',as_of=data['checked'],alertable=p['allow_local_alerts'] and 0<=now-data['checked']<=300)
        elif snap:
            data=snap['data'];row.update(system_id=data.get('solar_system_id'),source='esi',as_of=snap['fetched'],online=data.get('online'))
        row['system_name']=universe.systems.get(row['system_id'],{}).get('name');result.append(row)
    return result


def read_reports(store,p,now):
    channels={s.casefold() for s in p['channels']}
    with store.db() as db:rows=db.execute('SELECT data FROM intel_reports WHERE ts>=? AND ts<=? ORDER BY ts DESC LIMIT 3000',(now-86400,now+60)).fetchall()
    return [r for raw in rows if (r:=json.loads(raw['data']))['channel'].casefold() in channels]


def active_state(reports,now,ttl,owned=()):
    ordered=sorted(reports,key=lambda r:(r['timestamp'],r['state']=='clear',r['id']))
    cleared={};latest_pilot={};active=[]
    for row in ordered:
        if row['timestamp']>now:continue
        if row['state']=='clear':
            for sid in row['systems']:cleared[sid]=row['timestamp']
        elif row['state']=='contact' and not row['ambiguous']:
            for pilot in row['pilots']:latest_pilot[pilot['name'].casefold()]=row['id']
    for row in ordered:
        if row['state']!='contact' or not 0<=now-row['timestamp']<=ttl:continue
        remaining=[p for p in row['pilots'] if p['name'].casefold() not in owned and (row['ambiguous'] or latest_pilot.get(p['name'].casefold())==row['id'])]
        if row['pilots'] and not remaining:continue
        for sid in row['systems']:
            if row['timestamp']>cleared.get(sid,0):active.append({**row,'system_id':sid,'pilots':remaining})
    return active,cleared


def collect_alerts(store,universe=None,now=None):
    now=time.time() if now is None else now;p=preferences(store);universe=universe or intel_universe.load(store)
    with store.db() as db:row=db.execute('SELECT data FROM intel_status WHERE id=1').fetchone()
    status=json.loads(row['data']) if row else {}
    if not p['enabled'] or status.get('error') or now-(status.get('checked') or 0)>10:return {'items':[],'observed_domains':[],'enabled':p['enabled']}
    pos=positions(store,universe,p,now);reports=read_reports(store,p,now);owned={c['name'].casefold() for c in store.characters()}
    active,cleared=active_state(reports,now,p['ttl_minutes']*60,owned);items=[];domains=[]
    by_system=defaultdict(list)
    for r in active:
        if not r.get('historical') and not r['ambiguous']:by_system[r['system_id']].append(r)
    for char in pos:
        if not char['alertable']:continue
        domain='intel:'+str(char['id']);domains.append(domain);distances=universe.distances(char['system_id'])
        for sid,rows in by_system.items():
            distance=distances.get(sid)
            if distance is None or distance>p['jumps']:continue
            pilots=sorted({p['name'] for r in rows for p in r['pilots']});identity=hashlib.sha256('\0'.join(pilots or ['unnamed']).encode()).hexdigest()[:20]
            key=f"intel:{char['id']}:{sid}:{identity}";newest=max(rows,key=lambda r:r['timestamp']);name=universe.systems[sid]['name']
            items.append({'id':key,'domain':domain,'category':'intel','kind':'intel_near','subject':name+(' · '+', '.join(pilots[:6]) if pilots else ''),'corporation_id':None,'scope_name':'Személyes','when':newest['timestamp'],'checked_at':status['checked'],'reliable':True,'character_id':char['id'],'character_name':char['name'],'system_id':sid,'jumps':distance,'pilots':pilots,'report_id':newest['id'],'sound':p['sound'],'cooldown':p['cooldown_seconds']})
            items[-1]['episode_key']=str(int(cleared.get(sid,0)))
    return {'items':items,'observed_domains':domains,'enabled':p['enabled']}


class IntelMonitor:
    def __init__(self,store,catalog,eve,universe=None):
        self.store=store;self.catalog=catalog;self.eve=eve;self.universe=universe or intel_universe.load(store)
        self.lock=threading.RLock();self.stop_event=threading.Event();self.refresh_event=threading.Event();self.thread=None;self.headers={};self.started=time.time();self.last_locations=0;self.location_thread=None;self.closed=False
        self.status={'running':False,'scanning':False,'checked':None,'files':0,'done':0,'new_messages':0,'error':None,'file_errors':0}
        schema(store)
        if preferences(store)['enabled']:self.start()
    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():return
            self.stop_event.clear();self.started=time.time();self.thread=threading.Thread(target=self._work,daemon=True,name='EVE-intel');self.thread.start()
    def stop(self,permanent=True):
        if permanent:self.closed=True
        self.stop_event.set()
        if self.thread and self.thread is not threading.current_thread():self.thread.join(timeout=3)
        with self.lock:self.status['running']=False
    def configure(self,data):
        p=save_preferences(self.store,data,self.universe)
        self.started=time.time()
        if p['enabled']:self.start();self.refresh_event.set()
        else:self.stop(permanent=False)
        return p
    def request_locations(self):
        self.refresh_event.set();self._start_locations(preferences(self.store))
    def _start_locations(self,p):
        with self.lock:
            if self.location_thread and self.location_thread.is_alive():return
            self.status['location_refreshing']=True
        def work():
            try:self.refresh_locations(p)
            finally:
                with self.lock:self.status['location_refreshing']=False;self.status['location_character']=None
        self.location_thread=threading.Thread(target=work,daemon=True,name='EVE-intel-location');self.location_thread.start()

    def _write_status(self):
        with self.lock:value=dict(self.status)
        with self.store.db() as db:db.execute('INSERT OR REPLACE INTO intel_status VALUES(1,?)',(json.dumps(value),))
    def _work(self):
        while not self.stop_event.is_set():
            try:
                p=preferences(self.store)
                if not p['enabled']:break
                self.scan(p)
                if time.time()-self.last_locations>=15 or self.refresh_event.is_set():
                    self.refresh_event.clear();self.last_locations=time.time();self._start_locations(p)
            except Exception as error:
                with self.lock:self.status.update(error=str(error) if isinstance(error,(PlanningError,EsiError)) else 'Az intelolvasás nem sikerült. Ellenőrizd a mappa hozzáférését.',checked=time.time(),scanning=False)
                self._write_status()
            self.stop_event.wait(1)
        with self.lock:self.status['running']=False;self.status['scanning']=False
        self._write_status()
    def channels(self,folder):
        root=Path(folder).expanduser()
        try:
            names={match['channel'] for f in root.iterdir() if f.is_file() and not f.is_symlink() and (match:=FILE.match(f.name))}
        except OSError:raise PlanningError('A chatlogmappa nem olvasható. Ellenőrizd a hozzáférési engedélyt.') from None
        return sorted(names,key=str.casefold)
    def scan(self,p=None,now=None):
        now=time.time() if now is None else now;p=p or preferences(self.store);root=Path(p['folder'])
        if not root.is_dir():raise PlanningError('A chatlogmappa nem érhető el.')
        allowed={s.casefold() for s in p['channels']};characters={c['id']:c for c in self.store.characters()}
        files=[]
        try:
            for f in root.iterdir():
                m=FILE.match(f.name)
                if m and not f.is_symlink() and f.is_file() and (m['channel'].casefold() in allowed or m['channel']=='Local' and int(m['character']) in characters):
                    if now-f.stat().st_mtime<=86400*2:files.append((f,m))
        except OSError:raise PlanningError('A chatlogmappa nem olvasható. Ellenőrizd a hozzáférési engedélyt.') from None
        files.sort(key=lambda row:row[0].stat().st_mtime,reverse=True)
        with self.lock:self.status.update(running=True,scanning=True,files=len(files),done=0,error=None,file_errors=0,new_messages=0)
        self._write_status()
        for index,(f,m) in enumerate(files):
            if self.stop_event.is_set():break
            try:count=self._file(f,m,p,characters,now)
            except (OSError,UnicodeError,ValueError):
                count=0
                with self.lock:self.status['file_errors']+=1
            with self.lock:self.status['done']=index+1;self.status['new_messages']+=count
        with self.lock:self.status.update(checked=now,scanning=False)
        self._write_status()
        with self.store.db() as db:
            db.execute('DELETE FROM intel_reports WHERE ts<?',(now-86400,));db.execute('DELETE FROM intel_files WHERE seen<?',(now-86400*30,))
    def _file(self,path,match,p,characters,now):
        flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0);fd=os.open(path,flags)
        with os.fdopen(fd,'rb') as f:
            info=os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode):return 0
            key=hashlib.sha256(str(path.resolve()).encode()).hexdigest()
            with self.store.db() as db:old=db.execute('SELECT * FROM intel_files WHERE id=?',(key,)).fetchone()
            offset=old['offset'] if old and old['device']==info.st_dev and old['inode']==info.st_ino and old['offset']<=info.st_size else 0
            # Do not reopen or decode the complete file on each poll.
            if old and offset==info.st_size:return 0
            header_key=(key,info.st_dev,info.st_ino)
            if old and old['offset']>info.st_size:self.headers.pop(header_key,None)
            if header_key not in self.headers:
                head=f.read(8192);encoding='utf-16-le' if head.startswith(b'\xff\xfe') else 'utf-16-be' if head.startswith(b'\xfe\xff') else 'utf-8-sig'
                text=head[:len(head)//2*2].decode(encoding,errors='replace') if encoding.startswith('utf-16') else head.decode(encoding,errors='replace')
                fields={k:v.strip() for k,v in re.findall(r'^\s*(Channel ID|Channel Name|Listener):\s*(.*?)\s*$',text,re.M)}
                if not fields.get('Channel Name') or not fields.get('Listener'):return 0
                self.headers[header_key]=(encoding,fields)
            encoding,fields=self.headers[header_key];channel=fields['Channel Name'];cid=int(match['character'])
            local=channel=='Local' and cid in characters and fields['Listener']==characters[cid]['name']
            if not local and channel.casefold() not in {c.casefold() for c in p['channels']}:return 0
            f.seek(offset);chunk=f.read(4*1024*1024);separator=b'\n\x00' if encoding=='utf-16-le' else b'\x00\n' if encoding=='utf-16-be' else b'\n'
            end=chunk.rfind(separator)
            if encoding.startswith('utf-16'):
                while end>=0 and end%2:end=chunk.rfind(separator,0,end)
            if end<0:
                if len(chunk)>=4*1024*1024:raise ValueError('Oversized log line')
                return 0
            used=end+len(separator);text=chunk[:used].decode(encoding);count=0
            with self.store.db() as db:
                for line in text.splitlines():
                    raw=LINE.match(line.strip())
                    if local:
                        if not raw:continue
                        try:at=datetime.strptime(raw[1],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
                        except ValueError:continue
                        if at>now+60:continue
                        moved=re.search(r'Channel changed to Local\s*:\s*(.+)',raw[3]) if raw[2].strip()=='EVE System' else None
                        row=db.execute('SELECT data FROM intel_local_positions WHERE character_id=?',(cid,)).fetchone();position=json.loads(row['data']) if row else None
                        if moved and (sid:=self.universe.resolve(moved[1])) and (not position or at>=position['checked']):position={'system_id':sid,'changed':at,'checked':at}
                        elif position and at>=position['checked']:position['checked']=at
                        if position:db.execute('INSERT OR REPLACE INTO intel_local_positions VALUES(?,?)',(cid,json.dumps(position)))
                    else:
                        report=parse_message(line,self.universe,channel,fields.get('Channel ID',''),now,p['region_ids'])
                        if not report or report['timestamp']<now-86400:continue
                        report.update(historical=report['timestamp']<self.started-5,received=now)
                        cur=db.execute('INSERT OR IGNORE INTO intel_reports VALUES(?,?,?,?,?,?,?)',(report['id'],report['timestamp'],channel,report['reporter'],report['message'],json.dumps(report),now));count+=cur.rowcount
                db.execute('INSERT OR REPLACE INTO intel_files VALUES(?,?,?,?,?,?,?)',(key,info.st_dev,info.st_ino,offset+used,encoding,channel,now))
            return count
    def refresh_locations(self,p=None,now=None):
        p=p or preferences(self.store);now=time.time() if now is None else now
        for char in selected_characters(self.store,p):
            if self.closed:break
            if str(char['id']) in p['manual_locations']:continue
            status=self.store.resource_status(char['id'],'intel_location')
            if status and status['needs_auth']:continue
            with self.lock:self.status['location_character']=char['name']
            try:
                token=self.eve.token(char['id'],required_scopes=INTEL_SCOPES);parts={}
                for resource in ['location','online']:
                    key='intel_'+resource;old=self.store.snapshot(char['id'],key)
                    if old and old['expires']>now:parts[key]=old;continue
                    body,headers=self.eve.http.request(f"{ESI}/characters/{char['id']}/{resource}/",token=token,headers={'If-None-Match':old['etag']} if old and old.get('etag') else {})
                    h={k.lower():v for k,v in headers.items()};data=old['data'] if body is None and old else body
                    if not isinstance(data,dict) or (resource=='location' and (type(data.get('solar_system_id')) is not int or data['solar_system_id'] not in self.universe.systems)) or (resource=='online' and type(data.get('online')) is not bool):raise EsiError('Hiányos EVE-helyzetadat.')
                    max_age=re.search(r'max-age="?(\d+)',h.get('cache-control',''));ttl=max(1,int(max_age[1])-int(h.get('age','0'))) if max_age else 5
                    parts[key]={'data':data,'fetched':now,'expires':now+ttl,'etag':h.get('etag') or (old or {}).get('etag')}
                parts['intel_position']={'data':{**parts['intel_location']['data'],'online':parts['intel_online']['data']['online']},'fetched':min(r['fetched'] for r in parts.values()),'expires':min(r['expires'] for r in parts.values()),'etag':None}
                if not self.closed:self.store.save_snapshots(char['id'],parts,domain='intel_location')
            except (EsiError,ValueError) as error:self.store.resource_error(char['id'],'intel_location',str(error) if isinstance(error,EsiError) else 'Hiányos EVE-helyzetadat.',isinstance(error,AuthenticationError))
    def dashboard(self,center=None,radius=5,history=False,now=None,region=None):
        now=time.time() if now is None else now;p=preferences(self.store);universe=self.universe;pos=positions(self.store,universe,p,now);reports=read_reports(self.store,p,now)
        active,cleared=active_state(reports,now,p['ttl_minutes']*60,{c['name'].casefold() for c in self.store.characters()})
        if center not in universe.systems:center=next((c['system_id'] for c in pos if c['system_id'] in universe.systems),next((r['systems'][0] for r in reports if r['systems']),None))
        distance=universe.distances(center);ids={sid for sid,s in universe.systems.items() if s['region_id']==region} if region else {sid for sid,d in distance.items() if d<=radius};clipped=len(ids)>400
        if clipped:ids=set(sorted(ids,key=lambda sid:(distance.get(sid,float('inf')),universe.systems[sid]['name']))[:400])
        by_sid=defaultdict(list)
        for row in active:by_sid[row['system_id']].append(row)
        last={}
        for row in reports:
            for sid in row['systems']:last.setdefault(sid,row)
        nodes=[]
        for sid in ids:
            rows=by_sid[sid];recent=last.get(sid);clear=cleared.get(sid)
            pilots=sorted({p['name'] for row in rows for p in row['pilots']});state='contact' if rows else 'clear' if clear and now-clear<=min(600,p['ttl_minutes']*60) else 'old' if history and recent else 'quiet'
            nodes.append({**universe.systems[sid],'distance':distance.get(sid),'state':state,'pilots':pilots,'reported_at':max(r['timestamp'] for r in rows) if rows else clear if state=='clear' else recent['timestamp'] if recent and state=='old' else None,'characters':[c['name'] for c in pos if c['system_id']==sid],'reports':[r['id'] for r in rows]})
        for report in reports:report['system_names']=[universe.systems[sid]['name'] for sid in report['systems']]
        manual_names={cid:universe.systems[sid]['name'] for cid,sid in p['manual_locations'].items() if sid in universe.systems}
        with self.lock:status=dict(self.status)
        alerts=collect_alerts(self.store,universe,now)['items']
        return {'preferences':p,'manual_system_names':manual_names,'status':status,'characters':pos,'center':center,'nodes':nodes,'edges':[[a,b] for a,b in universe.edges if a in ids and b in ids],'reports':reports[:500],'alerts':alerts,'clipped':clipped,'universe_build':universe.build,'regions':sorted({(s['region_id'],s['region']) for s in universe.systems.values()},key=lambda r:r[1]),'calculated_at':now}
