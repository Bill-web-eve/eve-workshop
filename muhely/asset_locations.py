"""Resolve inventory places asynchronously, with scoped caches and bounded retries."""
import json
import threading
import time

from .esi import ESI,EsiError
from . import intel_universe

SCOPE='esi-universe.read_structures.v1'


class AssetLocations:
    def __init__(self,store,eve,clock=time.time):
        self.store=store;self.eve=eve;self.clock=clock;self.lock=threading.RLock()
        self.pending={};self.active=None;self.thread=None;self.closed=False
        self.universe=intel_universe.load(store)

    def readers(self,corporation_id):
        if corporation_id is not None and not self.store.corporation_monitored(corporation_id):return []
        return [c['id'] for c in self.store.characters() if corporation_id is None or c.get('corporation_id')==corporation_id]

    def cached(self,ids,readers,scope=None):
        result={};allowed={f'asset-structure:{cid}' for cid in readers}|{f'trade-location:{cid}' for cid in readers}|{f'asset-unresolved:{scope or 0}'}
        with self.store.db() as db:
            for row in db.execute("SELECT kind,id,data,fetched FROM universe_cache WHERE kind='asset-location' OR kind='stations' OR kind LIKE 'asset-structure:%' OR kind LIKE 'trade-location:%' OR kind LIKE 'asset-unresolved:%' ORDER BY fetched"):
                lid=row['id']
                if lid not in ids or (row['kind'] not in {'asset-location','stations'} and row['kind'] not in allowed):continue
                data=json.loads(row['data']);private=lid>=10**12
                value={'name':data.get('name'),'expires':data.get('expires',row['fetched']+(900 if private else 30*86400)),'error':data.get('error')}
                old=result.get(lid)
                if old is None:result[lid]=value
                else:result[lid]={'name':value['name'] or old['name'],'expires':max(value['expires'],old['expires']),'error':value['error'] or old.get('error')}
        for lid in ids:
            if lid in self.universe.systems:result[lid]={'name':self.universe.systems[lid]['name'],'expires':float('inf')}
        return result

    def decorate(self,data,corporation_id=None):
        readers=self.readers(corporation_id);ids={r['location_id'] for r in data['rows'] if r['location_id'] is not None}
        cached=self.cached(ids,readers,corporation_id);now=self.clock()
        missing=ids-{lid for lid,value in cached.items() if value['expires']>now}
        with self.lock:
            if not self.closed:
                for lid in missing:
                    key=(corporation_id,lid)
                    if self.active!=key:self.pending[key]=readers
                if self.pending and (self.thread is None or not self.thread.is_alive()):
                    self.thread=threading.Thread(target=self._work,daemon=True,name='EVE-asset-locations');self.thread.start()
            pending={lid for scope,lid in self.pending if scope==corporation_id}
            if self.active and self.active[0]==corporation_id:pending.add(self.active[1])
        for row in data['rows']:
            value=cached.get(row['location_id'],{})
            row['location_name']=value.get('name')
            row['location_status']='resolved' if value.get('name') else 'pending' if row['location_id'] in pending else value.get('error','unknown')
        data['locations_pending']=bool(ids&pending)
        data['locations_resolved']=sum(bool(v.get('name')) for v in cached.values())
        data['locations_total']=len(ids)
        return data

    def _resolve(self,lid,readers,scope=None):
        if 30_000_000<=lid<40_000_000 or 60_000_000<=lid<64_000_000:
            kind='systems' if lid<40_000_000 else 'stations'
            value,_=self.eve.http.request(f'{ESI}/universe/{kind}/{lid}/')
            if not isinstance(value,dict) or not isinstance(value.get('name'),str) or not value['name']:raise EsiError('Missing station name')
            self.store.save_universe_cache('asset-location',lid,{'name':value['name'],'expires':self.clock()+30*86400},self.clock());return
        if lid>=10**12:
            scopes=self.eve.granted_scopes()
            for cid in readers:
                if self.closed:return
                if SCOPE not in scopes.get(cid,[]):continue
                try:
                    token=self.eve.token(cid,required_scopes=[SCOPE])
                    value,_=self.eve.http.request(f'{ESI}/universe/structures/{lid}/',token=token)
                    if not isinstance(value,dict) or not isinstance(value.get('name'),str) or not value['name']:continue
                    self.store.save_universe_cache(f'asset-structure:{cid}',lid,{'name':value['name'],'expires':self.clock()+86400},self.clock());return
                except EsiError:continue
            # Negative entries are scoped: an inaccessible corp place must not
            # suppress a personal reader with docking access (or another corp).
            for cid in readers:self.store.save_universe_cache(f'asset-structure:{cid}',lid,{'error':'access','expires':self.clock()+900},self.clock())
            self.store.save_universe_cache(f'asset-unresolved:{scope or 0}',lid,{'error':'access','expires':self.clock()+900},self.clock())
            return
        self.store.save_universe_cache('asset-location',lid,{'error':'unknown','expires':self.clock()+900},self.clock())

    def _work(self):
        while True:
            with self.lock:
                if self.closed or not self.pending:self.active=None;self.thread=None;return
                key=next(iter(self.pending));readers=self.pending.pop(key);self.active=key
            try:
                self._resolve(key[1],readers,key[0])
            except Exception:
                # Preserve any last known name and throttle failed lookups.
                kind='asset-location' if key[1]<10**12 else f'asset-unresolved:{key[0] or 0}'
                old=self.store.universe_cached(kind,key[1]);value=dict(old['data']) if old else {}
                value.update(error='unavailable',expires=self.clock()+900)
                self.store.save_universe_cache(kind,key[1],value,self.clock())
            finally:
                with self.lock:self.active=None

    def stop(self):
        with self.lock:self.closed=True;self.pending.clear()
        thread=self.thread
        if thread and thread is not threading.current_thread():thread.join(timeout=3)
