"""Read-only market locations, private structure quotes and seller fee profiles.

CCP rules: https://support.eveonline.com/hc/en-us/articles/203218962
No orders are created. Structure fees are a user-supplied total, including SCC.
"""
from decimal import Decimal
import json
import threading
import time
from urllib.parse import urlencode

from .esi import ESI,EsiError,MARKET_SCOPES,SKILL_SCOPES
from .market import Market,STATION,expiry
from .planner import PlanningError,integer,decimal_number
from .production import profiles
from .refresh_policy import RefreshPolicy,AUTO_SECONDS

ACCOUNTING=16622
BROKER_RELATIONS=3446
DEFAULTS={'system_id':None,'reader_id':None,'location_id':None,'location':None,'search':'' ,'structure_broker_fee':None,'hauling_isk_per_m3':'0'}
FINANCE={'materials':'jita:sell','sale':'jita:sell','seller_id':None,'sale_order':'auto','other_isk':'0','blueprints_isk':None}

def decimal(value,name,minimum=0,maximum=100):
    if isinstance(value,bool):raise PlanningError(name+': szám szükséges.')
    return format(decimal_number(value,name,minimum,maximum),'f')

def rate(accounting,broker,corp=0,faction=0):
    a=integer(accounting,'Accounting',5);b=integer(broker,'Broker Relations',5)
    c=Decimal(decimal(corp,'Corporation standing',-10,10));f=Decimal(decimal(faction,'Faction standing',-10,10))
    return {'sales_tax':format(Decimal('7.5')*(1-Decimal('.11')*a),'f'),
            'broker_fee':format(Decimal(3)-Decimal('.3')*b-Decimal('.02')*c-Decimal('.03')*f,'f')}

class StructureMarket(Market):
    """One atomic, paginated full order book per structure, reused by all items."""
    def __init__(self,store,eve,location,reader,clock=None):
        self.eve=eve;self.reader=reader
        super().__init__(store,eve.http,clock,location['region_id'],location['id'],f"structure:{location['id']}:{reader}")

    def _fetch_quote(self,tid,old,now):
        kind='structure-book:'+self.cache_key;cached=self.store.universe_cached(kind,0)
        book=cached['data'] if cached else None
        manual=tid in self.manual_pending or getattr(self,'direct_manual',False)
        if not book or (book['expires'] if manual else book['next_check'])<=now:
            key='structure-book:'+self.cache_key
            if not self.refresh_policy.claim([key],manual,now):
                if not book:raise EsiError('A market automatikus lekérési időköze még nem telt le.')
            else:
                try:
                    token=self.eve.token(self.reader,required_scopes=[MARKET_SCOPES[0]])
                    pages=[];page=1;count=1
                    while page<=count:
                        with self.lock:self.page=page;self.pages=count
                        prior=book['pages'][page-1] if book and len(book['pages'])>=page else None
                        headers={'If-None-Match':prior['etag']} if prior and prior.get('etag') else {}
                        data,h=self.http.request(f'{ESI}/markets/structures/{self.station}/?page={page}',token=token,headers=headers)
                        h={k.lower():v for k,v in h.items()}
                        try:reported=int(h.get('x-pages',(prior or {}).get('count',1)))
                        except (ValueError,TypeError):raise EsiError('Hibás market-oldalszám.') from None
                        if not 1<=reported<=500 or page>1 and reported!=count:raise EsiError('A market oldalszáma megváltozott; a korábbi árak megmaradnak.')
                        count=reported
                        if data is None:
                            if not prior:raise EsiError('Hiányzó korábbi marketoldal.')
                            values=prior['values']
                        else:
                            if not isinstance(data,list):raise EsiError('Hibás struktúrapiaci válasz.')
                            values={}
                            for order in data:
                                if not isinstance(order,dict):raise EsiError('Hibás piaci megbízás.')
                                if order.get('location_id')!=self.station or order.get('volume_remain',0)<=0:continue
                                item=integer(order.get('type_id'),'Piaci termék',2**31-1,1)
                                if not isinstance(order.get('is_buy_order'),bool):raise EsiError('Hibás piaci megbízás.')
                                price=Decimal(decimal(order.get('price'),'Piaci ár',0,10**18))
                                if price<=0:raise EsiError('Hibás piaci ár.')
                                side='buy' if order['is_buy_order'] else 'sell';q=values.setdefault(str(item),{'buy':None,'sell':None})
                                if q[side] is None or (price>Decimal(q[side]) if side=='buy' else price<Decimal(q[side])):q[side]=format(price,'f')
                        pages.append({'values':values,'etag':h.get('etag') or (prior or {}).get('etag'),'count':count,'expires':expiry(h,now)});page+=1
                    values={}
                    for part in pages:
                        for item,q in part['values'].items():
                            merged=values.setdefault(item,{'buy':None,'sell':None})
                            for side in ['buy','sell']:
                                if q[side] is not None and (merged[side] is None or (Decimal(q[side])>Decimal(merged[side]) if side=='buy' else Decimal(q[side])<Decimal(merged[side]))):merged[side]=q[side]
                    book={'values':values,'pages':pages,'checked':now,'expires':min(p['expires'] for p in pages),'next_check':now+AUTO_SECONDS}
                    self.store.save_universe_cache(kind,0,book,now)
                finally:self.refresh_policy.claim([key],True,self.clock())
        q=book['values'].get(str(tid),{'buy':None,'sell':None})
        result={'id':tid,**q,'checked':book['checked'],'expires':book['expires'],'next_check':book['next_check'],'pages':[]}
        self.save_quote(tid,result);return result

    def quote(self,tid,manual=False):
        self.direct_manual=manual
        try:return super().quote(tid,manual)
        finally:self.direct_manual=False

class Trade:
    def __init__(self,store,catalog,eve,clock=None):
        self.store=store;self.catalog=catalog;self.eve=eve;self.clock=clock or time.time
        self.policy=RefreshPolicy(store);self.lock=threading.RLock();self.local=None;self.local_key=None
        self.state={'running':False,'phase':'','done':0,'total':0,'error':None,'candidates':[],'system_id':None,'reader_id':None}
        with store.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS trade_settings(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS trade_plans(key TEXT PRIMARY KEY,data TEXT NOT NULL)')

    def settings(self):
        with self.store.db() as db:r=db.execute('SELECT data FROM trade_settings WHERE id=1').fetchone()
        p={**DEFAULTS,**(json.loads(r[0]) if r else {})}
        stored=p.get('hauling_rates',{})
        p['hauling_rates']={source:{direction:stored.get(source,{}).get(direction,p['hauling_isk_per_m3'] if direction=='import' else '0') for direction in ['import','export']} for source in ['jita','local']}
        return p

    def character(self,cid):
        cid=integer(cid,'Karakter',2**31-1,1)
        if cid not in {c['id'] for c in self.store.characters()}:raise PlanningError('Ismeretlen karakter.')
        return cid

    def system(self,sid):
        sid=integer(sid,'Rendszer',2**31-1,1)
        if sid not in self.catalog.moon_systems:raise PlanningError('Ismeretlen rendszer.')
        return sid

    def save(self,data):
        if not isinstance(data,dict):raise PlanningError('Hibás marketbeállítás.')
        sid=self.system(data.get('system_id'));cid=self.character(data.get('reader_id'))
        location_id=data.get('location_id') or None;location=None
        if location_id:
            location_id=integer(location_id,'Állomás',2**53-1,1)
            cached=self.store.universe_cached('trade-location:'+str(cid),location_id)
            if not cached or cached['data']['system_id']!=sid:raise PlanningError('Előbb keresd meg és válaszd ki az állomást ebben a rendszerben.')
            location=cached['data']
        fee=data.get('structure_broker_fee')
        fee=None if fee in [None,''] else decimal(fee,'Teljes struktúra broker fee',0,100)
        search=str(data.get('search','')).strip()
        if len(search)>120:raise PlanningError('Túl hosszú marketnév.')
        with self.lock:
            p=self.settings();p.update(system_id=sid,reader_id=cid,location_id=location_id,location=location,search=search,structure_broker_fee=fee)
            with self.store.db() as db:db.execute('INSERT OR REPLACE INTO trade_settings VALUES(1,?)',(json.dumps(p),))
        return self.dashboard()

    def save_hauling(self,data):
        if not isinstance(data,dict):raise PlanningError('Hibás szállítási beállítás.')
        def rate(value):
            value=decimal(value,'Szállítási díj',0,10**12)
            if Decimal(value)!=Decimal(value).quantize(Decimal('.0001')):raise PlanningError('A szállítási díj legfeljebb 4 tizedesjegy lehet.')
            return format(Decimal(value).quantize(Decimal('.0001')),'f')
        rates=None;legacy=None
        if 'hauling_rates' in data:
            raw=data['hauling_rates']
            if not isinstance(raw,dict) or any(not isinstance(raw.get(s),dict) for s in ['jita','local']):raise PlanningError('Hibás szállítási beállítás.')
            rates={s:{d:rate(raw[s].get(d)) for d in ['import','export']} for s in ['jita','local']}
        else:legacy=rate(data.get('hauling_isk_per_m3'))
        with self.lock:
            p=self.settings()
            if rates is not None:p['hauling_rates']=rates
            else:
                # Preserve the old single inbound rate for existing clients/profiles.
                p['hauling_isk_per_m3']=legacy
                for source in ['jita','local']:p['hauling_rates'][source]['import']=legacy
            with self.store.db() as db:db.execute('INSERT OR REPLACE INTO trade_settings VALUES(1,?)',(json.dumps(p),))
        return self.dashboard()

    def public(self,kind,item):
        old=self.store.universe_cached(kind,item);now=self.clock()
        if old and old['fetched']+30*86400>now:return old['data']
        data,h=self.eve.http.request(f'{ESI}/'+('corporations/' if kind=='corporations' else 'universe/'+kind+'/')+str(item)+'/')
        if not isinstance(data,dict):raise EsiError('Hiányos állomás- vagy rendszeradat.')
        self.store.save_universe_cache(kind,item,data,now);return data

    def location(self,lid,cid,token=None):
        kind='trade-location:'+str(cid);cached=self.store.universe_cached(kind,lid)
        if cached and cached['fetched']+(AUTO_SECONDS if lid>=10**12 else 30*86400)>self.clock():return cached['data']
        if lid>=10**12:
            token=token or self.eve.token(cid,required_scopes=[MARKET_SCOPES[1]])
            data,_=self.eve.http.request(f'{ESI}/universe/structures/{lid}/',token=token)
            if not isinstance(data,dict):raise EsiError('Hiányos struktúraadat.')
            sid=data.get('solar_system_id');owner=data.get('owner_id');faction=None
        else:
            data=self.public('stations',lid);sid=data.get('system_id');owner=data.get('owner')
            faction=self.public('corporations',owner).get('faction_id') if owner else None
        sid=self.system(sid);system=self.public('systems',sid);constellation=self.public('constellations',system['constellation_id'])
        name=data.get('name')
        if not isinstance(name,str) or not name or len(name)>300:raise EsiError('Hiányzó állomásnév.')
        value={'id':lid,'name':name,'system_id':sid,'system_name':self.catalog.moon_systems[sid]['name'],'region_id':constellation['region_id'],
               'kind':'structure' if lid>=10**12 else 'npc','owner_id':owner,'faction_id':faction}
        self.store.save_universe_cache(kind,lid,value,self.clock());return value

    def start(self,phase,work):
        with self.lock:
            if self.state['running']:raise PlanningError('A marketadatok lekérése már folyamatban van.')
            self.state.update(running=True,phase=phase,done=0,total=1,error=None)
        def run():
            try:work()
            except Exception as e:
                with self.lock:self.state['error']=str(e) if isinstance(e,(EsiError,PlanningError)) else 'A marketadatok nem frissültek; a korábbi adatok megmaradtak.'
            finally:
                with self.lock:self.state.update(running=False,phase='',done=self.state['total'])
        threading.Thread(target=run,daemon=True,name='EVE-market-access').start()

    def discover(self,data):
        sid=self.system(data.get('system_id'));cid=self.character(data.get('reader_id'));search=str(data.get('search','')).strip()
        direct=data.get('structure_id')
        if direct:direct=integer(direct,'Structure ID',2**53-1,10**12)
        if not direct and not 3<=len(search)<=120:raise PlanningError('Legalább három karakteres marketnevet adj meg.')
        def work():
            key=f'trade-discovery:{sid}:{cid}:{search}:{direct}'
            cached=self.store.universe_cached(key,0)
            if cached and cached['data']['expires']>self.clock():candidates=cached['data']['candidates']
            else:
                token=self.eve.token(cid,required_scopes=MARKET_SCOPES[1:3])
                system=self.public('systems',sid);ids=list(system.get('stations',[]))
                if direct:ids.append(direct)
                else:
                    result,_=self.eve.http.request(f'{ESI}/characters/{cid}/search/?'+urlencode({'categories':'structure','search':search,'strict':'false'}),token=token)
                    if not isinstance(result,dict) or not isinstance(result.get('structure',[]),list):raise EsiError('Hiányos marketkeresési válasz.')
                    ids+=result.get('structure',[])
                if len(ids)>200:raise PlanningError('Túl sok találat; pontosítsd a market nevét.')
                candidates=[]
                with self.lock:self.state.update(total=max(1,len(ids)),done=0,phase='Állomások ellenőrzése')
                for i,lid in enumerate(dict.fromkeys(ids)):
                    try:
                        value=self.location(integer(lid,'Állomás',2**53-1,1),cid,token)
                        if value['system_id']==sid:candidates.append(value)
                    except EsiError:
                        if direct:raise
                    with self.lock:self.state['done']=i+1
                self.store.save_universe_cache(key,0,{'candidates':candidates,'expires':self.clock()+AUTO_SECONDS},self.clock())
            with self.lock:self.state.update(candidates=sorted(candidates,key=lambda v:v['name']),system_id=sid,reader_id=cid)
        self.start('Helyi market keresése',work);return self.dashboard()

    def market(self):
        p=self.settings();loc=p['location'];cid=p['reader_id']
        if not loc or not cid:raise PlanningError('Előbb állítsd be a helyi marketet a Beállítások alatt.')
        self.character(cid)
        key=(loc['id'],loc['region_id'],cid)
        with self.lock:
            if key!=self.local_key:
                self.local=StructureMarket(self.store,self.eve,loc,cid,self.clock) if loc['kind']=='structure' else Market(self.store,self.eve.http,self.clock,loc['region_id'],loc['id'],f"station:{loc['id']}:{cid}")
                self.local_key=key
            return self.local

    def prices(self,ids,refresh=False,manual=False):
        try:
            m=self.market()
            if refresh:m.start(ids,manual=manual)
            result=m.snapshot(ids)
            result['market_name']=self.settings()['location']['name'];return result
        except PlanningError as e:return {'quotes':{},'running':False,'errors':{str(i):str(e) for i in ids},'retry_after':{},'source_key':'unconfigured','market_name':'Helyi market','done':0,'total':0}

    def key(self,pid):
        if pid in [None,'']:return 'draft'
        if not isinstance(pid,str) or pid not in {p['id'] for p in self.store.plans()}:raise PlanningError('Ismeretlen mentett terv.')
        return 'plan:'+pid

    def finance(self,pid=None):
        key=self.key(pid)
        with self.store.db() as db:r=db.execute('SELECT data FROM trade_plans WHERE key=?',(key,)).fetchone()
        return {**FINANCE,**(json.loads(r[0]) if r else {})}

    def save_finance(self,data):
        key=self.key(data.get('plan_id'));p=self.finance(data.get('plan_id'))
        for field in ['materials','sale']:
            value=data.get(field,p[field])
            if value not in [s+':'+m for s in ['jita','local'] for m in ['buy','sell','split']]:raise PlanningError('Ismeretlen árforrás.')
            p[field]=value
        seller=data.get('seller_id',p['seller_id']);p['seller_id']=self.character(seller) if seller else None
        if data.get('sale_order',p['sale_order']) not in ['auto','instant','order']:raise PlanningError('Ismeretlen eladási mód.')
        p['sale_order']=data.get('sale_order',p['sale_order']);p['other_isk']=decimal(data.get('other_isk',p['other_isk']),'Egyéb költség',0,10**18)
        blueprints=data.get('blueprints_isk',p['blueprints_isk'])
        p['blueprints_isk']=None if blueprints in [None,''] else decimal(blueprints,'Blueprintköltség',0,10**18)
        with self.store.db() as db:db.execute('INSERT OR REPLACE INTO trade_plans VALUES(?,?)',(key,json.dumps(p)))
        return p

    def refresh_profile(self,cid,source,manual=False):
        cid=self.character(cid)
        if source not in ['jita','local']:raise PlanningError('Ismeretlen árforrás.')
        def work():
            p=self.settings();loc=self.location(STATION,cid) if source=='jita' else p['location']
            if not loc:raise PlanningError('Előbb válaszd ki a helyi marketet.')
            if self.policy.claim(['trade-skills:'+str(cid)],manual,self.clock()):
                token=self.eve.token(cid,required_scopes=SKILL_SCOPES)
                parts={kind:self.eve.skill_resource(cid,kind,token) for kind in ['skills','skillqueue']}
                self.store.save_snapshots(cid,parts,domain='skills')
            if loc['kind']=='npc':
                old=self.store.universe_cached('trade-standings',cid);now=self.clock()
                if old and old['data']['expires']>now:return
                if not self.policy.claim(['trade-standings:'+str(cid)],manual,now):return
                token=self.eve.token(cid,required_scopes=[MARKET_SCOPES[3]])
                data,h=self.eve.http.request(f'{ESI}/characters/{cid}/standings/',token=token,headers={'If-None-Match':old['etag']} if old and old.get('etag') else {})
                if data is None:
                    if not old:raise EsiError('Hiányzó korábbi standingadat.')
                    data=old['data']['rows']
                if not isinstance(data,list):raise EsiError('Hibás standingadat.')
                seen=set()
                for row in data:
                    if not isinstance(row,dict) or row.get('from_type') not in ['agent','npc_corp','faction']:raise EsiError('Hibás standingadat.')
                    identity=(row['from_type'],integer(row.get('from_id'),'Standing',2**31-1,1))
                    if identity in seen:raise EsiError('Ismételt standingadat.')
                    seen.add(identity);decimal(row.get('standing'),'Standing',-10,10)
                self.store.save_universe_cache('trade-standings',cid,{'rows':data,'expires':expiry(h,now),'next_check':now+AUTO_SECONDS},now,h.get('ETag') or h.get('etag'))
        self.start('Eladó skillek és standingek frissítése',work);return self.dashboard()

    def profile(self,cid,source):
        cid=self.character(cid)
        if source not in ['jita','local']:raise PlanningError('Ismeretlen árforrás.')
        p=self.settings();loc=p['location'] if source=='local' else (self.store.universe_cached('trade-location:'+str(cid),STATION) or {}).get('data')
        profile=next((c for c in profiles(self.store,self.store.settings()) if c['id']==cid),None)
        result={'character_id':cid,'location':loc,'accounting':None,'broker_relations':None,'sales_tax':None,'broker_fee':None,'corp_standing':None,'faction_standing':None,'warnings':[],'skills_checked':profile['as_of'] if profile else None,'standings_checked':None}
        if not profile or not profile['available']:result['warnings'].append('Az eladó skilladata hiányzik; frissítsd az eladó adatait.')
        else:
            a=profile['levels'].get(ACCOUNTING,0);b=profile['levels'].get(BROKER_RELATIONS,0)
            result.update(accounting=a,broker_relations=b,sales_tax=rate(a,b)['sales_tax'])
            if profile['stale']:result['warnings'].append('Az eladó skilladata korábbi pillanatképből származik.')
        if not loc:result['warnings'].append('Az eladási állomás adatai még hiányoznak.')
        elif loc['kind']=='structure':
            result['broker_fee']=p['structure_broker_fee']
            if result['broker_fee'] is None:result['warnings'].append('Add meg a struktúra teljes broker fee-jét SCC-vel együtt.')
        else:
            standing=self.store.universe_cached('trade-standings',cid)
            if not standing:result['warnings'].append('Az eladó módosítatlan standingadata hiányzik.')
            else:
                values={(r['from_type'],r['from_id']):r['standing'] for r in standing['data']['rows']}
                c=values.get(('npc_corp',loc['owner_id']),0);f=values.get(('faction',loc['faction_id']),0)
                result.update(corp_standing=c,faction_standing=f,standings_checked=standing['fetched'])
                if result['accounting'] is not None:result['broker_fee']=rate(result['accounting'],result['broker_relations'],c,f)['broker_fee']
                if standing['data']['expires']<=self.clock():result['warnings'].append('Korábbi standingadatokkal számolunk.')
        return result

    def dashboard(self):
        p=self.settings();p['system_name']=self.catalog.moon_systems.get(p['system_id'],{}).get('name');grants=self.eve.granted_scopes()
        with self.lock:status=dict(self.state)
        return {'settings':p,'status':status,'scopes':MARKET_SCOPES,'characters':[{'id':c['id'],'name':c['name'],'market_access':set(MARKET_SCOPES[:3]).issubset(grants.get(c['id'],[])),'standings_access':MARKET_SCOPES[3] in grants.get(c['id'],[])} for c in self.store.characters()]}

    def status(self):
        with self.lock:return {k:v for k,v in self.state.items() if k!='candidates'}
