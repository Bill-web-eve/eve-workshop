"""Cached public ESI industry indices and adjusted-price job fee estimates.

Post-Viridian: EIV * (SCI * job-cost bonus + facility tax + SCC + alpha).
EIV uses unmodified recipe inputs per run, independently of ME/Jita prices.
https://www.eveonline.com/news/view/viridian-expansion-notes
https://www.eveonline.com/news/view/patch-notes-version-21-06
"""
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from email.utils import parsedate_to_datetime
import math
import threading
import time

from .esi import ESI,EsiError,Transport
from .planner import PlanningError,integer

from .refresh_policy import RefreshPolicy,AUTO_SECONDS

D=lambda v:Decimal(str(v))
PATHS={'systems':'/industry/systems/','prices':'/markets/prices/'}
CACHE_SECONDS=3600


def decimal_value(value):
    if isinstance(value,bool):raise EsiError('Hibás ipari ár- vagy indexadat.')
    try:v=D(value)
    except (InvalidOperation,ValueError,TypeError):raise EsiError('Hibás ipari ár- vagy indexadat.') from None
    if not v.is_finite() or v<0 or v>10**18:raise EsiError('Hibás ipari ár- vagy indexadat.')
    return v


def normalize(kind,data):
    if not isinstance(data,list) or len(data)>100000:raise EsiError('Hiányos EVE ipari költségadat.')
    result={};seen=set()
    for row in data:
        if not isinstance(row,dict):raise EsiError('Hiányos EVE ipari költségadat.')
        key=row.get('solar_system_id' if kind=='systems' else 'type_id')
        if isinstance(key,bool) or not isinstance(key,int) or key<=0 or key in seen:raise EsiError('Hibás vagy ismételt ipari azonosító.')
        seen.add(key)
        if kind=='prices':
            if row.get('adjusted_price') is not None:result[str(key)]=format(decimal_value(row['adjusted_price']),'f')
        else:
            indices=row.get('cost_indices')
            if not isinstance(indices,list):raise EsiError('Hiányzó system cost index.')
            values={}
            for item in indices:
                if not isinstance(item,dict):raise EsiError('Hibás system cost index.')
                activity=item.get('activity')
                if activity not in ['manufacturing','reaction','copying','invention']:continue
                if activity in values:raise EsiError('Ismételt system cost index.')
                value=decimal_value(item.get('cost_index'))
                if value>1:raise EsiError('Hibás system cost index.')
                values[activity]=format(value,'f')
            result[str(key)]=values
    if not result:raise EsiError('Üres EVE ipari költségadat; a korábbi adatok megmaradtak.')
    return result


def cache_expiry(headers,now):
    h={k.lower():v for k,v in headers.items()}
    try:
        if h.get('expires'):return max(now,parsedate_to_datetime(h['expires']).timestamp())
        import re
        m=re.search(r'max-age="?(\d+)',h.get('cache-control',''))
        return now+max(0,int(m[1])-int(h.get('age','0'))) if m else now+CACHE_SECONDS
    except (ValueError,TypeError,OverflowError):return now+CACHE_SECONDS


class IndustryCosts:
    def __init__(self,store,http=None,clock=None):
        self.store=store;self.http=http or Transport();self.clock=clock or time.time
        self.refresh_policy=RefreshPolicy(store)
        self.lock=threading.RLock();self.running=False;self.errors={};self.retry_after=0;self.current=None;self.done=0

    def cached(self,kind):return self.store.universe_cached('industry-'+kind,0)

    def refresh(self,manual=False):
        for index,(kind,path) in enumerate(PATHS.items()):
            with self.lock:self.current=kind;self.done=index
            old=self.cached(kind);now=self.clock()
            if old and (kind!='systems' or old['data'].get('activities_version')==2) and (old['data']['expires'] if manual else old['data'].get('next_check',old['data']['expires']))>now:continue
            if not self.refresh_policy.claim(['industry-cost:'+kind],manual,now):continue
            try:
                headers={'If-None-Match':old['etag']} if old and old.get('etag') and (kind!='systems' or old['data'].get('activities_version')==2) else {}
                data,h=self.http.request(ESI+path,headers=headers)
                h={k.lower():v for k,v in h.items()}
                if data is None and not old:raise EsiError('Hiányzó korábbi ipari költségadat.')
                values=old['data']['values'] if data is None else normalize(kind,data)
                # Each endpoint replaces its old snapshot only after validation.
                self.store.save_universe_cache('industry-'+kind,0,{'activities_version':2,'values':values,'expires':cache_expiry(h,now),'next_check':max(now+AUTO_SECONDS,cache_expiry(h,now))},now,h.get('etag') or (old or {}).get('etag'))
                with self.lock:self.errors.pop(kind,None)
            except Exception as e:
                with self.lock:
                    self.errors[kind]=str(e) if isinstance(e,EsiError) else 'Az ipari költségadat nem frissült; a korábbi adat megmaradt.'
                    self.retry_after=max(self.retry_after,now+AUTO_SECONDS,getattr(self.http,'blocked_until',0))
            finally:
                self.refresh_policy.claim(['industry-cost:'+kind],manual=True,now=self.clock())

    def start(self,manual=False):
        with self.lock:
            if self.running or not manual and self.clock()<self.retry_after:return
            records=[self.cached(k) for k in PATHS]
            if all(r and (kind!='systems' or r['data'].get('activities_version')==2) and (r['data']['expires'] if manual else r['data'].get('next_check',r['data']['expires']))>self.clock() for kind,r in zip(PATHS,records)):return
            self.running=True
        def work():
            try:self.refresh(manual=manual)
            finally:
                with self.lock:self.running=False;self.current=None;self.done=2
        threading.Thread(target=work,daemon=True).start()

    def status(self):
        resources={}
        for kind in PATHS:
            r=self.cached(kind)
            resources[kind]={'checked':r['fetched'] if r else None,'expires':r['data']['expires'] if r else None,'stale':not r or r['data']['expires']<=self.clock()}
        with self.lock:return {'resources':resources,'running':self.running,'errors':dict(self.errors),'retry_after':self.retry_after,'current':self.current,'done':self.done}

    def system(self,sid,catalog):
        sid=integer(sid,'Rendszer',2**31-1,1)
        if sid not in catalog.moon_systems:raise PlanningError('Ismeretlen rendszer.')
        r=self.cached('systems');indices=(r or {}).get('data',{}).get('values',{}).get(str(sid),{})
        return {'id':sid,'name':catalog.moon_systems[sid]['name'],'indices':indices,
                'checked':r['fetched'] if r else None,'expires':r['data']['expires'] if r else None,'stale':not r or r['data']['expires']<=self.clock()}

    def estimate(self,rows,settings,catalog):
        if not isinstance(rows,list) or len(rows)>4000:raise PlanningError('Túl sok gyártási költségsor.')
        data={kind:self.cached(kind) for kind in PATHS}
        prices=(data['prices'] or {}).get('data',{}).get('values',{})
        systems=(data['systems'] or {}).get('data',{}).get('values',{})
        fees=[];total=0;missing=0;seen=set()
        for row in rows:
            if not isinstance(row,dict):raise PlanningError('Hibás gyártási költségsor.')
            tid=integer(row.get('id'),'Termék',2**31-1,1)
            if tid in seen or tid not in catalog.recipes:raise PlanningError('Ismeretlen vagy ismételt gyártási költségsor.')
            seen.add(tid);recipe=catalog.recipes[tid];activity=recipe['activity'];facility=settings[activity]
            groups=row.get('batches')
            if not isinstance(groups,list) or len(groups)>4000:raise PlanningError('Hibás jobfelosztás.')
            groups=[{'runs':integer(g.get('runs'),'Run',100000000,1),'count':integer(g.get('count'),'Job',100000000,1)} for g in groups if isinstance(g,dict)]
            if len(groups)!=len(row['batches']):raise PlanningError('Hibás jobfelosztás.')
            if sum(g['runs']*g['count'] for g in groups)>100000000:raise PlanningError('Túl sok run az ipari költségsorban.')
            sid=facility.get('system_id');index=systems.get(str(sid),{}).get(activity)
            base=Decimal(0);unpriced=[]
            for m in recipe['materials']:
                value=prices.get(str(m['typeID']))
                if value is None:unpriced.append(m['typeID'])
                else:base+=D(value)*m['quantity']
            complete=not unpriced and index is not None
            components={key:0 for key in ['system','facility','scc','alpha']};line=0
            if complete:
                rates={'system':D(index)*(1-D(facility.get('job_cost_role',0))/100),
                       'facility':D(facility.get('facility_tax',0))/100,
                       'scc':D(facility.get('scc_surcharge',4))/100,
                       'alpha':D(facility.get('alpha_surcharge',0))/100}
                for group in groups:
                    amount=base*group['runs']
                    # Per-job component cents; counts multiply already-rounded fees.
                    parts={k:int((amount*rate*100).quantize(Decimal('1'),rounding=ROUND_HALF_UP))*group['count'] for k,rate in rates.items()}
                    for k,v in parts.items():components[k]+=v
                    line+=sum(parts.values())
                total+=line
            else:missing+=1
            fees.append({'id':tid,'name':catalog.name(tid),'activity':activity,'system_id':sid,
                         'system_name':catalog.moon_systems.get(sid,{}).get('name'),'system_index':index,
                         'eiv_per_run':format(base,'f') if not unpriced else None,'missing_prices':unpriced,
                         'missing_system':index is None,'cents':str(line) if complete else None,
                         'components':{k:str(v) for k,v in components.items()} if complete else None})
        return {'rows':fees,'cents':str(total),'missing':missing,'complete':not missing,
                'stale':any(r and r['data']['expires']<=self.clock() for r in data.values()),'status':self.status()}
