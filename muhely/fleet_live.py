"""Resumable R2Z2 consumer. Public data only; never send an EVE token.

One serial connection, at most five requests/second, and at least six seconds
after an empty queue. A committed cursor may replay a batch after a crash;
ingestion is idempotent, so a crash cannot skip unsaved killmails.
"""
import copy,gzip,io,json,math,re,threading,time,urllib.error,urllib.request
from email.utils import parsedate_to_datetime
from .esi import EsiError,NoRedirect
from .fleet import PROJECT,cache,remember,preferences,validate_kills

BASE='https://r2z2.zkillboard.com/ephemeral/'
CURSOR='live:cursor'


class LiveFeed:
    def __init__(self,fleet):
        self.fleet=fleet;self.store=fleet.store;self.stop_event=fleet.stop_event
        self.opener=urllib.request.build_opener(NoRedirect());self.thread=None
        self.lock=threading.RLock();self.last_request=0;self.failures=0
        old=cache(self.store,CURSOR);self.cursor=(old or {}).get('data',{}).copy()
        self.next_check=(old or {}).get('expires',0)
        self.state={'phase':'connecting','checked':(old or {}).get('checked') or None,'last_received':self.cursor.get('last_received'),
                    'received':0,'saved':0,'error':(old or {}).get('error'),'retry_at':self.next_check or None,'gap_at':self.cursor.get('gap_at')}
    def enabled(self):return preferences(self.store)['live']
    def status(self):
        with self.lock:state=copy.deepcopy(self.state)
        return {**state,'enabled':self.enabled()}
    def start(self):
        if self.thread and self.thread.is_alive():return
        self.thread=threading.Thread(target=self._work,daemon=True,name='EVE-zkill-live');self.thread.start()
    def _work(self):
        while not self.stop_event.is_set():
            try:delay=self.step()
            except Exception:
                delay=60
                with self.lock:self.state.update(phase='retrying',error='Az élő zKillboard-adatfolyam átmenetileg nem érhető el.',retry_at=time.time()+delay)
            self.stop_event.wait(delay)
    def _read(self,name):
        if not re.fullmatch(r'(?:sequence|[1-9]\d*)\.json',name):raise EsiError('Hibás zKillboard-adat.')
        if self.stop_event.wait(max(0,.2-(time.monotonic()-self.last_request))):raise InterruptedError()
        self.last_request=time.monotonic()
        request=urllib.request.Request(BASE+name,headers={'User-Agent':PROJECT,'Accept-Encoding':'gzip','Accept':'application/json'})
        try:
            with self.opener.open(request,timeout=15) as response:
                payload=response.read(16*1024*1024+1)
                if len(payload)>16*1024*1024:raise EsiError('Túl nagy zKillboard-válasz.')
                if response.headers.get('Content-Encoding','').lower()=='gzip':
                    with gzip.GzipFile(fileobj=io.BytesIO(payload)) as compressed:payload=compressed.read(32*1024*1024+1)
                if len(payload)>32*1024*1024:raise EsiError('Túl nagy zKillboard-válasz.')
                return json.loads(payload)
        except urllib.error.HTTPError as e:
            if e.code==404:return None
            raise
    def _pointer(self):
        data=self._read('sequence.json');sequence=data.get('sequence') if isinstance(data,dict) else None
        if type(sequence) is not int or sequence<=0:raise EsiError('Hibás zKillboard-adat.')
        return sequence
    def _kill(self,package,sequence):
        if not isinstance(package,dict) or package.get('sequence_id')!=sequence or not isinstance(package.get('esi'),dict) or not isinstance(package.get('zkb'),dict):raise EsiError('Hibás zKillboard-adat.')
        row={**package['esi'],'zkb':package['zkb']}
        if package.get('killmail_id')!=row.get('killmail_id'):raise EsiError('Hibás zKillboard-adat.')
        uploaded=package.get('uploaded_at')
        if type(uploaded) not in [int,float] or not math.isfinite(uploaded) or uploaded<=0:raise EsiError('Hibás zKillboard-adat.')
        validate_kills([row]);return row
    def _persist(self,error=None,delay=0):
        now=time.time();self.next_check=now+delay
        remember(self.store,CURSOR,self.cursor,now,self.next_check,error)
    def step(self):
        if not self.enabled() or not self.fleet.actors():
            with self.lock:self.state.update(phase='paused',retry_at=None)
            return 5
        if self.next_check>time.time():return max(.2,min(6,self.next_check-time.time()))
        rows=[];sequence=None;empty=False;failure=None
        try:
            # After a long absence the sequence files may have expired. Keep a
            # visible gap marker; the hourly historical queries still run.
            if not self.cursor.get('sequence') or time.time()-(self.cursor.get('polled_at') or 0)>23*3600:
                if self.cursor.get('sequence'):self.cursor['gap_at']=time.time()
                self.cursor['sequence']=self._pointer()
            sequence=self.cursor['sequence']
            for _ in range(25):
                if self.stop_event.is_set() or not self.enabled():break
                package=self._read(str(sequence)+'.json')
                if package is None:empty=True;break
                rows.append(self._kill(package,sequence));sequence+=1
        except (OSError,ValueError,EsiError) as e:failure=e
        if self.stop_event.is_set():return 0
        # Save first, checkpoint second. Replays after a crash are harmless.
        saved=self.fleet.ingest_live(list({k['killmail_id']:k for k in rows}.values()))
        now=time.time()
        if sequence is not None:self.cursor['sequence']=sequence
        if rows or failure is None:self.cursor['polled_at']=now
        if rows:self.cursor['last_received']=now
        delay=6 if empty else .2
        error=None
        if failure is not None:
            self.failures+=1;delay=min(900,30*2**min(self.failures-1,5))
            error='Az élő zKillboard-adatfolyam átmenetileg nem érhető el.'
            if isinstance(failure,urllib.error.HTTPError) and failure.code in [403,420,429,503]:
                delay=max(delay,3600 if failure.code==403 else 900)
                retry=failure.headers.get('Retry-After')
                if retry:
                    try:delay=max(delay,min(86400,float(retry)))
                    except ValueError:
                        try:delay=max(delay,min(86400,parsedate_to_datetime(retry).timestamp()-now))
                        except (ValueError,TypeError):pass
        else:self.failures=0
        self._persist(error,delay)
        with self.lock:
            self.state.update(phase='retrying' if error else 'live' if empty else 'catching_up',checked=now,
                              last_received=self.cursor.get('last_received'),received=self.state['received']+len(rows),saved=self.state['saved']+saved,
                              error=error,retry_at=now+delay if error else None,gap_at=self.cursor.get('gap_at'))
        return delay
