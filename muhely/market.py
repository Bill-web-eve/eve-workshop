"""Public Jita 4-4 best quotes. Persistent cache, no SSO and no trade actions."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
import re
import threading
import time

from .esi import ESI, EsiError, Transport
from .planner import PlanningError, integer

REGION=10000002
STATION=60003760
CACHE_SECONDS=300


def validate_ids(values,catalog):
    if not isinstance(values,list) or len(values)>1000:raise PlanningError('Legfeljebb 1000 termék árazható egyszerre.')
    result=[]
    for value in values:
        tid=integer(value,'Termékazonosító',2**31-1,1)
        if tid not in catalog.types:raise PlanningError('Ismeretlen árazandó termék.')
        if tid not in result:result.append(tid)
    return result


def expiry(headers,now):
    h={k.lower():v for k,v in headers.items()}
    ttl=CACHE_SECONDS
    match=re.search(r'(?:^|,)\s*max-age\s*=\s*"?(\d+)',h.get('cache-control','').lower())
    if match:
        try:ttl=max(0,min(CACHE_SECONDS,int(match.group(1))-max(0,int(h.get('age','0')))))
        except ValueError:pass
    elif h.get('expires'):
        try:ttl=max(0,min(CACHE_SECONDS,parsedate_to_datetime(h['expires']).timestamp()-now))
        except (ValueError,TypeError,OverflowError):pass
    return now+ttl


def best_quotes(orders):
    if not isinstance(orders,list):raise EsiError('Hibás Jita-piaci válasz.')
    buy=[];sell=[]
    for o in orders:
        if not isinstance(o,dict):raise EsiError('Hibás Jita-piaci válasz.')
        if o.get('location_id')!=STATION or o.get('volume_remain',0)<=0:continue
        if not isinstance(o.get('is_buy_order'),bool):raise EsiError('Hibás Jita-piaci válasz.')
        try:price=Decimal(str(o['price']))
        except (KeyError,InvalidOperation):raise EsiError('Hibás Jita-piaci ár.') from None
        if not price.is_finite() or price<=0:raise EsiError('Hibás Jita-piaci ár.')
        (buy if o['is_buy_order'] else sell).append(price)
    return {'buy':format(max(buy),'f') if buy else None,'sell':format(min(sell),'f') if sell else None}


class Market:
    def __init__(self,store,http=None,clock=None):
        self.store=store;self.http=http or Transport();self.clock=clock or time.time
        self.lock=threading.RLock();self.pending=set();self.running=False
        self.total=0;self.done=0;self.errors={};self.retry_after={};self.current=None;self.page=None;self.pages=None

    def quote(self,tid):
        old=self.store.market_quote(tid);now=self.clock()
        if old and old.get('next_check',old['expires'])>now:return old
        pages=[];count=1;page=1
        while page<=count:
            with self.lock:self.page=page;self.pages=count if page>1 else None
            prior=(old or {}).get('pages',[])
            prior=prior[page-1] if len(prior)>=page else None
            headers={'If-None-Match':prior['etag']} if prior and prior.get('etag') else {}
            orders,h=self.http.request(f'{ESI}/markets/{REGION}/orders/?order_type=all&type_id={tid}&page={page}',headers=headers)
            h={k.lower():v for k,v in h.items()}
            try:count=int(h.get('x-pages',prior.get('count',1) if prior else 1))
            except (TypeError,ValueError):raise EsiError('Hibás Jita-piaci oldalszám.') from None
            with self.lock:self.pages=count
            if not 1<=count<=100:raise EsiError('Túl sok Jita-piaci oldal érkezett.')
            if orders is None:
                if not prior:raise EsiError('Üres Jita-válasz korábbi ár nélkül.')
                quotes=prior['quotes']
            else:quotes=best_quotes(orders)
            pages.append({'quotes':quotes,'etag':h.get('etag') or (prior or {}).get('etag'),
                          'count':count,'expires':expiry(h,now)})
            page+=1
        buys=[Decimal(p['quotes']['buy']) for p in pages if p['quotes']['buy'] is not None]
        sells=[Decimal(p['quotes']['sell']) for p in pages if p['quotes']['sell'] is not None]
        result={'id':tid,'buy':format(max(buys),'f') if buys else None,'sell':format(min(sells),'f') if sells else None,
                'checked':now,'expires':min(p['expires'] for p in pages),'next_check':now+CACHE_SECONDS,'pages':pages}
        # Failed pages never replace a previously complete quote.
        self.store.save_market_quote(tid,result)
        return result

    def snapshot(self,ids):
        now=self.clock();quotes={}
        for tid in ids:
            row=self.store.market_quote(tid)
            if row:
                quotes[str(tid)]={k:row[k] for k in ['id','buy','sell','checked','expires']}
                quotes[str(tid)]['stale']=row['expires']<=now
        with self.lock:
            return {'quotes':quotes,'running':self.running,'done':self.done,'total':self.total,
                    'errors':{str(k):v for k,v in self.errors.items() if k in ids},
                    'retry_after':{str(k):v for k,v in self.retry_after.items() if k in ids},
                    'station_id':STATION,'region_id':REGION}

    def start(self,ids):
        with self.lock:
            now=self.clock();needed=[]
            for tid in ids:
                old=self.store.market_quote(tid)
                if (not old or old.get('next_check',old['expires'])<=now) and self.retry_after.get(tid,0)<=now and tid not in self.pending:needed.append(tid)
            if not needed:return
            if not self.running:self.total=0;self.done=0;self.errors={}
            self.pending.update(needed);self.total+=len(needed)
            if self.running:return
            self.running=True
        threading.Thread(target=self._work,daemon=True).start()

    def _work(self):
        while True:
            with self.lock:
                if not self.pending:self.running=False;self.current=None;self.page=None;self.pages=None;return
                tid=min(self.pending);self.current=tid;self.page=None;self.pages=None
            try:
                self.quote(tid)
                with self.lock:self.errors.pop(tid,None);self.retry_after.pop(tid,None)
            except Exception as exc:
                with self.lock:
                    self.errors[tid]=str(exc) if isinstance(exc,EsiError) else 'A Jita-ár nem frissült.'
                    self.retry_after[tid]=max(self.clock()+60,getattr(self.http,'blocked_until',0))
            finally:
                with self.lock:self.pending.discard(tid);self.done+=1
