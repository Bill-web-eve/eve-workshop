"""Local, session-based command-burst declarations. No chat is sent to ESI."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,html,json,os,re,stat,threading,time

from .intel import FILE,LINE,preferences as intel_preferences
from .planner import PlanningError

CHARGES=[
 (42694,'Active Shielding Charge','Shield'),(42695,'Shield Harmonizing Charge','Shield'),(42696,'Shield Extension Charge','Shield'),
 (42838,'Evasive Maneuvers Charge','Skirmish'),(42839,'Interdiction Maneuvers Charge','Skirmish'),(42840,'Rapid Deployment Charge','Skirmish'),
 (42835,'Sensor Optimization Charge','Information'),(42836,'Electronic Superiority Charge','Information'),(42837,'Electronic Hardening Charge','Information')]
IDS={i for i,_,_ in CHARGES}
NAMES=[(i,re.compile(r'(?<!\w)'+re.escape(name)+r'(?!\w)',re.I)) for i,name,_ in CHARGES]
MISSING=re.compile(r'\b(?:missing|needed|need|summary|hiány|hiányzik|hiányzó|összesítés)\b',re.I)
NUMBERED=re.compile(r'(?:'+ '|'.join(re.escape(name) for _,name,_ in CHARGES)+r')\s+(?:[:=]\s*)?\d+(?!\w)',re.I)
SEPARATORS={'utf-16-le':b'\n\x00','utf-16-be':b'\x00\n','utf-8-sig':b'\n'}

def declaration(line,now):
    match=LINE.match(line.strip())
    if not match:return None
    stamp,reporter,body=match.groups();reporter=reporter.strip()
    if not reporter or reporter.casefold() in ['eve system','eve-system']:return None
    try:at=datetime.strptime(stamp,'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
    except ValueError:return None
    if at>now+60 or len(body)>8000:return None
    plain=html.unescape(re.sub(r'<[^>]*>','',body))
    if MISSING.search(plain):return None
    if NUMBERED.search(plain) and not re.sub(r'[\s,;|/]+','',NUMBERED.sub('',plain)):return None
    charges={i for i,pattern in NAMES if pattern.search(plain)}
    charges.update(int(i) for i in re.findall(r'showinfo:(\d+)(?!\d)',body,re.I) if int(i) in IDS)
    if not charges:return None
    event=hashlib.sha256((stamp+'\0'+reporter.casefold()+'\0'+plain).encode()).hexdigest()
    return {'name':reporter,'at':at,'charges':sorted(charges),'event':event}

def folder_path(value):
    if not isinstance(value,str) or not value.strip() or len(value)>2000:raise PlanningError('Válassz elérhető chatlogmappát.')
    root=Path(value).expanduser().resolve()
    if not root.is_dir():raise PlanningError('A chatlogmappa nem érhető el.')
    return root

def discover(folder):
    root=folder_path(folder)
    try:
        names={m['channel'] for p in root.iterdir() if (m:=FILE.match(p.name)) and 'boost' in m['channel'].casefold() and not p.is_symlink() and p.is_file()}
    except OSError:raise PlanningError('A Boost-chatnaplók mappája nem olvasható.') from None
    return sorted(names,key=str.casefold)

class BoostCounter:
    def __init__(self,store,clock=None):
        self.store=store;self.clock=clock or time.time;self.lock=threading.RLock();self.stop_event=threading.Event();self.thread=None
        with store.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS boost_counter_state(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL)')
            row=db.execute('SELECT data FROM boost_counter_state WHERE id=1').fetchone()
        self.state=json.loads(row['data']) if row else {'running':False,'folder':'','channel':'','started':None,'stopped':None,'checked':None,'providers':{},'files':{},'events':[],'error':None,'file_errors':0}

    def persist(self):
        with self.store.db() as db:db.execute('INSERT OR REPLACE INTO boost_counter_state VALUES(1,?)',(json.dumps(self.state),))

    def paths(self,root,channel):
        try:return sorted((p for p in root.iterdir() if (m:=FILE.match(p.name)) and m['channel'].casefold()==channel.casefold() and not p.is_symlink() and p.is_file()),key=lambda p:p.name)
        except OSError:raise PlanningError('A Boost-chatnaplók mappája nem olvasható.') from None

    def open_log(self,path):
        fd=os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
        stream=os.fdopen(fd,'rb')
        try:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):raise ValueError('Not a regular log')
            head=stream.read(8192);enc='utf-16-le' if head.startswith(b'\xff\xfe') else 'utf-16-be' if head.startswith(b'\xfe\xff') else 'utf-8-sig'
            text=(head[:len(head)//2*2] if enc.startswith('utf-16') else head).decode(enc,errors='replace')
            header={k:v.strip() for k,v in re.findall(r'^\s*(Channel ID|Channel Name|Listener):\s*(.*?)\s*$',text,re.M)}
            if not header.get('Listener') or header.get('Channel Name','').casefold()!=self.state['channel'].casefold():raise ValueError('Wrong channel header')
            return stream,info,enc
        except Exception:stream.close();raise

    def start(self,folder,channel):
        root=folder_path(folder)
        if not isinstance(channel,str) or channel not in discover(str(root)):raise PlanningError('Válassz a listából egy Boost nevű csatornát.')
        with self.lock:
            now=self.clock();old=self.state
            self.state={'running':True,'folder':str(root),'channel':channel,'started':now,'stopped':None,'checked':now,'providers':{},'files':{},'events':[],'error':None,'file_errors':0}
            try:
                # Baseline at EOF: messages already present never enter a new count.
                for path in self.paths(root,channel):
                    try:
                        stream,info,enc=self.open_log(path)
                        with stream:
                            sep=SEPARATORS[enc];stream.seek(max(0,info.st_size-len(sep)));tail=stream.read()
                        offset=info.st_size-(info.st_size%2 if enc.startswith('utf-16') else 0)
                        self.state['files'][path.name]={'device':info.st_dev,'inode':info.st_ino,'offset':offset,'skip_partial':bool(info.st_size and not tail.endswith(sep))}
                    except (OSError,ValueError,UnicodeError):self.state['file_errors']+=1
                self.persist()
            except Exception:self.state=old;raise
        self.resume()
        return self.snapshot()

    def stop(self):
        with self.lock:
            self.state.update(running=False,stopped=self.clock());self.persist()
        return self.snapshot()

    def resume(self):
        with self.lock:
            if self.stop_event.is_set() or not self.state['running'] or self.thread and self.thread.is_alive():return
            self.thread=threading.Thread(target=self.work,daemon=True,name='EVE-boost-counter');self.thread.start()

    def close(self):
        self.stop_event.set()
        if self.thread and self.thread is not threading.current_thread():self.thread.join(timeout=2)

    def work(self):
        while not self.stop_event.is_set():
            self.scan()
            self.stop_event.wait(1)

    def scan(self):
        with self.lock:
            if not self.state['running']:return
            now=self.clock();changed=False
            try:
                root=folder_path(self.state['folder']);batch=[];errors=0
                for path in self.paths(root,self.state['channel']):
                    try:
                        old=self.state['files'].get(path.name)
                        info=path.stat()
                        if old and old['device']==info.st_dev and old['inode']==info.st_ino and old['offset']==info.st_size:continue
                        stream,info,enc=self.open_log(path)
                        with stream:
                            same=old and old['device']==info.st_dev and old['inode']==info.st_ino and old['offset']<=info.st_size
                            offset=old['offset'] if same else 0;skip=old.get('skip_partial',False) if same else False
                            stream.seek(offset);chunk=stream.read(1024*1024);sep=SEPARATORS[enc];end=chunk.rfind(sep)
                            if enc.startswith('utf-16'):
                                while end>=0 and end%2:end=chunk.rfind(sep,0,end)
                            if end<0:
                                if len(chunk)>=1024*1024:raise ValueError('Oversized log line')
                                continue
                            used=end+len(sep);complete=chunk[:used]
                            if skip:
                                first=complete.find(sep)
                                if enc.startswith('utf-16'):
                                    while first>=0 and first%2:first=complete.find(sep,first+1)
                                complete=complete[first+len(sep):] if first>=0 else b''
                            text=complete.decode(enc)
                            for line in text.splitlines():
                                item=declaration(line,now)
                                if item and item['at']>=int(self.state['started']):batch.append(item)
                            self.state['files'][path.name]={'device':info.st_dev,'inode':info.st_ino,'offset':offset+used,'skip_partial':False};changed=True
                    except (OSError,ValueError,UnicodeError):errors+=1
                seen=set(self.state['events'])
                for item in sorted(batch,key=lambda i:i['at']):
                    if item['event'] in seen:continue
                    seen.add(item['event']);self.state['events'].append(item['event'])
                    key=item['name'].casefold();prior=self.state['providers'].get(key)
                    if not prior or item['at']>=prior['at']:self.state['providers'][key]=item
                self.state['events']=self.state['events'][-20000:]
                self.state.update(error=None,file_errors=errors,checked=now)
            except Exception as exc:
                self.state.update(error=str(exc) if isinstance(exc,PlanningError) else 'A Boost-chatnaplók olvasása nem sikerült.',checked=now)
            self.persist()

    def snapshot(self):
        with self.lock:
            providers=sorted(self.state['providers'].values(),key=lambda p:p['name'].casefold())
            rows=[{'id':i,'name':name,'group':group,'count':sum(i in p['charges'] for p in providers),'providers':[p['name'] for p in providers if i in p['charges']]} for i,name,group in CHARGES]
            folder=self.state['folder'] or intel_preferences(self.store)['folder']
            return {**{k:self.state[k] for k in ['running','channel','started','stopped','checked','error','file_errors']},'folder':folder,'rows':rows,'providers':[{k:p[k] for k in ['name','at','charges']} for p in providers],'copy_text':'\n'.join(r['name']+'\t'+str(r['count']) for r in rows)}
