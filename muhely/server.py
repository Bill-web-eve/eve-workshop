from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
import uuid
import webbrowser

from . import __version__
from . import moons, extractions, moon_calendar, accounts, scheduler, notifications, progress, intel, intel_universe, mining, assets, jobs as job_browser, fleet, contracts, invention
from .market import Market,validate_ids as market_ids
from . import moon_transfer
from .trade import Trade
from .industry_costs import IndustryCosts
from .catalog import Catalog, import_sde
from .esi import EveConnection, EsiError, AuthenticationError, SCOPES, SKILL_SCOPES, PI_SCOPES, CORPORATION_SCOPES, INTEL_SCOPES, IMPLANT_SCOPES, CONTRACT_SCOPES
from .corporations import dashboard as corporation_dashboard
from .skills import dashboard as skill_dashboard
from .production import profiles as production_profiles
from .pi import dashboard as pi_dashboard
from .planner import Planner, PlanningError, AssetSnapshotPending, integer, decimal_number, live_inventory
from .reservations import allocate_plans, except_owner, pending_info, ordered_active, revision as reservation_revision, reorder as reorder_reservations
from .store import Store, default_data_dir, DEFAULT_SETTINGS

from .refresh_policy import RefreshPolicy
from .asset_locations import AssetLocations
from .boosts import BoostCounter,discover as boost_channels

ROOT = Path(__file__).resolve().parent.parent


class App:
    def __init__(self, folder, catalog_path, port=8765):
        self.store = Store(folder)
        self.catalog = Catalog(catalog_path,pi_fallback=ROOT/'data/catalog.sqlite3')
        self.planner = Planner(self.catalog)
        self.eve = EveConnection(self.store)
        self.market = Market(self.store)
        self.trade = Trade(self.store,self.catalog,self.eve)
        self.industry = IndustryCosts(self.store)
        self.port = port
        self.origin = f'http://127.0.0.1:{port}'
        self.cookie = secrets.token_urlsafe(32)
        self.csrf = secrets.token_urlsafe(32)
        self.instance = secrets.token_urlsafe(24)
        self.stopping=False
        self.refresh_policy = RefreshPolicy(self.store)
        self.desktop_auth = {}
        self.desktop_auth_lock = threading.RLock()
        self.task_lock = threading.RLock()
        self.planning_lock = threading.RLock()
        self.invention_skill_lock = threading.RLock()
        self.invention_skill_checks = {}
        self.task = {'running': False, 'kind': None, 'message': '', 'finished': None, 'results': []}
        self.intel=intel.IntelMonitor(self.store,self.catalog,self.eve)
        self.fleet=fleet.Fleet(self.store,self.catalog,self.eve,self.market)
        self.asset_locations=AssetLocations(self.store,self.eve)
        self.boosts=BoostCounter(self.store)

    def desktop_auth_start(self, url):
        """One-use browser handoff; OAuth codes and tokens never enter the UI."""
        ticket = secrets.token_urlsafe(32)
        oauth_state = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['state'][0]
        with self.desktop_auth_lock:
            self.desktop_auth = {k:v for k,v in self.desktop_auth.items() if v['expires'] > time.time()}
            self.desktop_auth[ticket] = {'url':url,'oauth_state':oauth_state,'status':'pending',
                                         'opened':False,'expires':time.time()+600}
        return {'url':self.origin+'/desktop/auth/'+ticket,'ticket':ticket}

    def desktop_auth_finish(self, oauth_state, error=None):
        with self.desktop_auth_lock:
            for item in self.desktop_auth.values():
                if item['oauth_state'] == oauth_state and item['expires'] > time.time() and item['status'] == 'pending':
                    item.update(status='error' if error else 'complete',error=error)
                    return True
        return False

    def refresh_domains(self,kind):
        if kind in ['sync','notifications']:
            domains=['industry','skills','pi']
            if any(c['monitoring_enabled'] for c in self.store.corporations()):domains.append('corporations')
            if any(self.store.snapshot(c['id'],k) for c in self.store.characters() for k in ['moon_calendar','moon_timers','moon_notifications']):domains.append('extractions')
            if any('esi-industry.read_character_mining.v1' in scopes for scopes in self.eve.granted_scopes().values()):domains.append('mining')
            if any(set(CONTRACT_SCOPES)&set(scopes) for scopes in self.eve.granted_scopes().values()):domains.append('contracts')
            return domains
        return ['industry' if kind=='sync' else 'moon-universe' if kind=='moons' else kind]

    def start_task(self, kind, manual=True):
        with self.task_lock:
            if self.stopping:raise PlanningError('Az alkalmazás leállítása folyamatban van.')
            if self.task['running']:
                raise PlanningError('Egy frissítés már folyamatban van.')
            domains=self.refresh_domains(kind)
            allowed=self.refresh_policy.claim(domains,manual=manual)
            if not allowed:return False
            self.task = {'id':uuid.uuid4().hex,'running':True,'kind':kind,'message':'Frissítés folyamatban…','results':[],'finished':None,'started':time.time(),'updated':time.time(),'outcome':'running','progress':{}}
        def work():
            outcomes=[]
            phases=1
            phase_index=0
            def phase(label,operation,domain=None):
                nonlocal phase_index
                if domain and domain not in allowed:return []
                self.task_progress({'stage':label,'stage_index':phase_index,'stages':phases,'subject':'','completed':0,'total':None,'resource':'Előkészítés','mode':'checking','page':None,'pages':None})
                try:
                    with progress.listen(self.task_progress):value=operation()
                finally:
                    # Space batches from their last request, including slow or failed refreshes.
                    if domain:self.refresh_policy.claim([domain],manual=True)
                if isinstance(value,list):outcomes.extend(value)
                phase_index+=1
                return value
            try:
                include_corps='corporations' in allowed
                include_moons='extractions' in allowed
                include_mining='mining' in allowed
                include_contracts='contracts' in allowed
                phases=sum(d in allowed for d in ['industry','skills','pi'])+int(include_corps)+int(include_moons)+int(include_mining)+int(include_contracts) if kind in ['sync','notifications'] else 1
                if kind in ['sync','notifications']:
                    if not self.store.characters():
                        raise PlanningError('Előbb adj hozzá egy karaktert az EVE-kapcsolat oldalon.')
                    result = phase('Személyes ipari adatok',self.eve.sync,'industry')
                    ok = all(r['ok'] for r in result)
                    message = 'Az EVE-adatok frissítve.' if ok else 'Néhány karakter frissítése sikertelen. A részletek az EVE-kapcsolat oldalon láthatók.'
                    if kind=='sync' and ok and result and self.store.enable_eve_after_sync():
                        message += ' A terv most a személyes EVE-készlettel és jobkimenetekkel számol.'
                    skill_results=phase('Skillek és tanulási sorok',self.eve.sync_skills,'skills')
                    missing=sum(not r['ok'] for r in skill_results)
                    if missing:
                        message+=f' {missing} karakter skilladata engedélyezést vagy frissítést igényel; részletek a Skillek és tanulás menüben.'
                    pi_results=phase('Bolygók és PI',self.eve.sync_pi,'pi')
                    pi_missing=sum(not r['ok'] for r in pi_results)
                    if pi_missing:message+=f' {pi_missing} karakter PI-adata engedélyezést vagy frissítést igényel; részletek a Bolygók és PI menüben.'
                    if include_corps:
                        corp_results=phase('Corporationok',self.eve.sync_corporations,'corporations')
                        message+=f" Corp-adatok: {sum(r['ok'] for r in corp_results)} sikeres lekérés; részletek a Corporationok oldalon."
                    if include_moons:
                        moon_results=phase('Holdak és naptár',lambda:extractions.sync(self.eve),'extractions')
                        message+=' '+extractions.refresh_summary(moon_results,self.store.characters())
                    if include_mining:
                        mining_results=phase('Bányászati naplók',lambda:mining.sync(self.eve),'mining')
                        message+=f" Bányászati naplók frissítve: {sum(r['ok'] for r in mining_results)}/{len(mining_results)} karakter."
                    if include_contracts:
                        contract_results=phase('Szerződések',lambda:contracts.sync(self.eve),'contracts')
                        message+=f" Szerződésadatok frissítve: {sum(r['ok'] for r in contract_results)}/{len(contract_results)} forrás."
                elif kind == 'contracts':
                    result=phase('Szerződések',lambda:contracts.sync(self.eve),'contracts')
                    message=f"Szerződésadatok frissítve: {sum(r['ok'] for r in result)}/{len(result)} forrás."
                elif kind == 'mining':
                    result=phase('Bányászati naplók',lambda:mining.sync(self.eve),'mining')
                    message=f"Bányászati naplók frissítve: {sum(r['ok'] for r in result)}/{len(result)} karakter."
                elif kind == 'skills':
                    if not self.store.characters():
                        raise PlanningError('Előbb adj hozzá karaktert az EVE-kapcsolat oldalon.')
                    result=phase('Skillek és tanulási sorok',self.eve.sync_skills,'skills')
                    ok_count=sum(r['ok'] for r in result)
                    message=f'Skilladatok ellenőrizve: {ok_count}/{len(result)} karakter. A részleteket a Skillek és tanulás oldalon találod.'
                elif kind == 'pi':
                    if not self.store.characters():raise PlanningError('Előbb adj hozzá karaktert az EVE-kapcsolat oldalon.')
                    result=phase('Bolygók és PI',self.eve.sync_pi,'pi');ok_count=sum(r['ok'] for r in result)
                    message=f'PI-adatok ellenőrizve: {ok_count}/{len(result)} karakter. Részletek a Bolygók és PI menüben.'
                elif kind == 'moons':
                    result=phase('Holdak rendszeradatai',lambda:moons.refresh_universe(self.store,self.catalog,self.eve.http))
                    message='A holdak rendszeradatai frissítve.' if all(r['ok'] for r in result) else 'Néhány rendszer ESI-adata nem frissült. A korábbi adatok megmaradtak.'
                elif kind == 'extractions':
                    result=phase('Holdak és naptár',lambda:extractions.sync(self.eve),'extractions')
                    message=extractions.refresh_summary(result,self.store.characters())
                elif kind == 'corporations':
                    if not self.store.characters():raise PlanningError('Előbb adj hozzá egy corp-hozzáférésre jogosult karaktert.')
                    result=phase('Corporationok',self.eve.sync_corporations,'corporations');ok_count=sum(r['ok'] for r in result)
                    message=f'Corp-adatok ellenőrizve: {ok_count} sikeres lekérés. A részleteket a Corporationok oldalon találod.'
                else:
                    phase('Receptadatbázis',self.update_catalog)
                    result, message = [], 'Az EVE-receptadatbázis naprakész.'
                if set(domains)-allowed:message+=' Egyes forrásoknál a 15 perces automatikus frissítési időköz még nem telt le; a mentett adatok láthatók.'
                with self.task_lock:
                    self.task.update(running=False,message=message,results=result,finished=time.time(),updated=time.time(),outcome='warning' if any(not row.get('ok',True) and row.get('warning',True) for row in outcomes) else 'success')
            except Exception as error:
                message = str(error) if isinstance(error, (PlanningError, EsiError)) else 'A frissítés nem sikerült. Az előző adatok megmaradtak.'
                with self.task_lock:
                    self.task.update(running=False,message=message,finished=time.time(),updated=time.time(),outcome='error',results=[{'ok':False,'error':message}])
        threading.Thread(target=work, daemon=True).start()
        return True

    def task_progress(self,values):
        allowed={'stage','stage_index','stages','subject','completed','total','resource','mode','page','pages','bytes_done','bytes_total'}
        with self.task_lock:
            self.task['progress'].update({key:value for key,value in values.items() if key in allowed})
            self.task['updated']=time.time()

    def task_snapshot(self):
        with self.task_lock:return copy.deepcopy(self.task)

    def activity(self):
        task=self.task_snapshot()
        with self.market.lock:
            market={'running':self.market.running,'done':self.market.done,'total':self.market.total,'errors':len(self.market.errors),'current':getattr(self.market,'current',None),'current_name':self.catalog.name(self.market.current) if getattr(self.market,'current',None) else None,'page':getattr(self.market,'page',None),'pages':getattr(self.market,'pages',None)}
        with self.intel.lock:intel_status=dict(self.intel.status)
        return {'task':task,'market':market,'industry':self.industry.status(),'trade':self.trade.status(),'local_market':self.trade.local.snapshot([]) if self.trade.local else {},'intel':intel_status,'fleet':self.fleet.status()}

    def invention_options(self,product_id,plan_id=None):
        product_id=integer(product_id,'Termék',10**9,1)
        if product_id not in self.catalog.inventions:raise PlanningError('Ehhez a termékhez nincs T2 hajó invention-recept.')
        finance=self.trade.finance(plan_id)
        if plan_id and self._saved(self.store.plans(),plan_id)['product_id']!=product_id:raise PlanningError('Az invention-beállítás más termékhez tartozik.')
        config=finance.get('invention');configured=bool(config and config['product_id']==product_id)
        if not configured:
            config=invention.defaults(self.store,self.catalog,product_id)
            if plan_id:config['inventor_id']=self._saved(self.store.plans(),plan_id).get('manufacturer_id') or None
        recipe=self.catalog.inventions[product_id]
        return {'config':config,'configured':configured,'manufacturing_prices':finance['materials'],'recipe':recipe,
                'product_name':self.catalog.name(product_id),'base_name':self.catalog.name(recipe['base_product_id']),
                'decryptors':list(self.catalog.decryptors.values()),'characters':[{k:p[k] for k in ['id','name','available','stale','as_of']} for p in production_profiles(self.store,self.store.settings())],
                'systems':{str(config[a]['system_id']):self.catalog.moon_systems.get(config[a]['system_id'],{}).get('name','') for a in ['copying','invention']}}

    def start_invention_skills(self,cid):
        if not cid:return
        with self.invention_skill_lock:
            if self.invention_skill_checks.get(cid,{}).get('running'):return
            self.invention_skill_checks[cid]={'running':True,'error':None}
        def work():
            error=None
            try:
                with self.eve.sync_lock:
                    if self.stopping:return
                    token=self.eve.token(cid,required_scopes=SKILL_SCOPES)
                    parts={'skills':self.eve.skill_resource(cid,'skills',token)}
                    self.store.save_snapshots(cid,parts,domain='skills')
            except Exception as exc:
                error=str(exc) if isinstance(exc,EsiError) else 'Az inventáló karakter skilladata nem frissült.'
                self.store.resource_error(cid,'skills',error,isinstance(exc,AuthenticationError))
            finally:
                with self.invention_skill_lock:self.invention_skill_checks[cid]={'running':False,'error':error}
        threading.Thread(target=work,daemon=True).start()

    def invention_estimate(self,data):
        for flag in ['check_data','refresh_all']:
            if flag in data and type(data[flag]) is not bool:raise PlanningError('Hibás invention-adatellenőrzési kapcsoló.')
        with self.invention_skill_lock:skills_running=any(v['running'] for v in self.invention_skill_checks.values())
        was_running=self.market.running or self.industry.running or bool(self.trade.local and self.trade.local.running) or skills_running
        with self.catalog.lock:
            config=invention.validate(data.get('config'),self.store,self.catalog)
            if not config:raise PlanningError('Hibás invention-beállítás.')
            source=data.get('manufacturing_prices','jita:sell')
            if source not in [s+':'+m for s in ['jita','local'] for m in ['buy','sell','split']]:raise PlanningError('Ismeretlen árforrás.')
            cid=self.scope_id(data.get('corporation_id'))
            def quotes(market,ids):return self.market.snapshot(ids) if market=='jita' else self.trade.prices(ids)
            settings=self.scope_settings(cid)
            live=self.live_data(settings) if cid is None else self.corporation_data(cid,settings)
            result=invention.compare(self.store,self.catalog,self.industry,config,data.get('quantity'),quotes,source,
                self.store.mapping('parameters',cid),live[2])
        if data.get('check_data') or data.get('refresh_all'):
            # Explicit Compare checks every dependency. Each provider still honors ESI expiry.
            for market,ids in result['price_ids_by_source'].items():
                if market=='jita':self.market.start(ids,manual=True)
                else:self.trade.prices(ids,True,True)
            self.industry.start(manual=True)
            self.start_invention_skills(config['inventor_id'])
            return self.invention_estimate({**data,'check_data':False,'refresh_all':False})
        with self.invention_skill_lock:
            result['skill_refresh']=dict(self.invention_skill_checks.get(config['inventor_id'],{'running':False,'error':None}))
        result['refresh_pending']=was_running
        return result

    def notification_data(self):
        with self.catalog.lock:
            data=notifications.collect(self.store,self.catalog)
        data['implants']=self.fleet.implants.dashboard()
        data.update(task=self.task_snapshot(),next_sync_at=self.refresh_policy.next_at(self.refresh_domains('notifications')))
        return data

    def update_catalog(self):
        progress.resource('Adatbázis-verzió ellenőrzése')
        url = 'https://developers.eveonline.com/static-data/tranquility/latest.jsonl'
        req = urllib.request.Request(url, headers={'User-Agent': 'EveMuhely/'+__version__})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                records = [json.loads(line) for line in response if line.strip()]
            latest = next(r for r in records if r['_key'] == 'sde')
            if str(latest['buildNumber']) == self.catalog.meta.get('buildNumber') and self.catalog.mining_types:
                return
            build = integer(latest['buildNumber'], 'SDE build', 10**12, 1)
            archive = self.store.folder/'sde.download'
            req = urllib.request.Request(f'https://developers.eveonline.com/static-data/tranquility/eve-online-static-data-{build}-jsonl.zip',
                                         headers={'User-Agent': 'EveMuhely/'+__version__})
            with urllib.request.urlopen(req, timeout=60) as response, archive.open('wb') as output:
                total = 0
                size=response.headers.get('Content-Length','')
                size=int(size) if size.isdigit() else None
                progress.report(resource='Receptadatbázis letöltése',mode='request',bytes_done=0,bytes_total=size)
                while block := response.read(1024*1024):
                    total += len(block)
                    if total > 400*1024*1024:
                        raise PlanningError('A letöltött adatcsomag váratlanul nagy.')
                    output.write(block)
                    progress.report(bytes_done=total)
            target = self.store.folder/'catalog.sqlite3'
            progress.report(resource='Receptadatbázis feldolgozása',mode='checking',bytes_done=None,bytes_total=None)
            import_sde(archive, target)
            with self.catalog.lock:
                self.catalog.path = target
                self.catalog.reload()
            if intel_universe.build(archive,self.store.folder/'intel_universe.json',build):self.intel.universe=intel_universe.load(self.store)
            archive.unlink(missing_ok=True)
        except PlanningError:
            raise
        except Exception:
            raise PlanningError('Az EVE-adatcsomag frissítése sikertelen. Az előző adatbázis használható.') from None

    def live_data(self, settings, strict=False):
        chars = self.store.characters()
        if settings['character_ids']:
            chars = [c for c in chars if c['id'] in settings['character_ids']]
            missing = set(settings['character_ids'])-{c['id'] for c in chars}
            if missing and strict:
                raise PlanningError('A kiválasztott karakterek egyike már nincs hozzáadva.')
        snapshots, stale = [], []
        if not chars and strict:
            raise PlanningError('EVE-készlethez előbb adj hozzá karaktert, majd frissítsd az adatokat. Kézi készlettel addig is tervezhetsz.')
        for char in chars:
            parts = {kind: self.store.snapshot(char['id'], kind) for kind in ['assets', 'blueprints', 'jobs']}
            if any(value is None for value in parts.values()):
                if strict:
                    raise PlanningError(f"{char['name']}: nincs teljes készlet-, blueprint- és jobadat. Nyomd meg az EVE-frissítést.")
                continue
            # Explicit refresh errors remain visible and block new live plans.
            if char['error'] and strict:
                raise PlanningError(f"{char['name']}: {char['error']} Kézi módban folytathatod a tervezést.")
            if min(p['expires'] for p in parts.values()) <= time.time():
                stale.append(char['name'])
            snapshots.append({'character_id': char['id'], 'assets_as_of': parts['assets']['fetched'],
                              'assets_expires':parts['assets']['expires'],'character_name':char['name'],
                              **{k: v['data'] for k, v in parts.items()}})
        result = live_inventory(self.catalog, snapshots, settings['location_ids'])
        return (*result, stale)

    def scope_label(self, corporation_id=None):
        return (self.store.corporation(corporation_id) or {}).get('name',str(corporation_id)) if corporation_id is not None else 'Személyes gyártás'

    def scope_id(self, value):
        if value is None or value=='':return None
        if isinstance(value,str):
            if not re.fullmatch(r'[1-9][0-9]*',value):raise PlanningError('Hibás corporation azonosító.')
            value=int(value)
        cid=integer(value,'Corporation',2**53-1,1)
        if not self.store.corporation(cid):raise PlanningError('Ismeretlen corporation. Előbb frissítsd a corp-adatokat.')
        return cid

    def scope_settings(self, corporation_id=None):
        settings = self.store.settings()
        if corporation_id is not None:
            settings.update(source='eve',location_ids=settings.get('corporation_locations',{}).get(str(corporation_id),[]))
        return settings

    def corporation_data(self, corporation_id, settings, strict=False):
        corp,members,parts=self.store.corporation_record(corporation_id)
        reason=('Nincs hozzáadott, ehhez a corporationhöz tartozó karakter.' if not members else
                (corp or {}).get('error') or ('Még nincs teljes corp készlet-, blueprint- és jobadat.' if not all(parts.values()) else None))
        if reason:
            if strict:raise PlanningError(self.scope_label(corporation_id)+': '+reason+' A Corporationok oldalon engedélyezd és frissítsd a hozzáférést.')
            return {},{},[],[],[],[]
        provider=next((c for c in members if c['id']==corp['provider_id']),None)
        if provider is None:
            if strict:raise PlanningError('A corp-adatot lekérő karakter már nem tag. Frissítsd a corporation adatait.')
            return {},{},[],[],[],[]
        snapshot={'character_id':provider['id'],'character_name':corp['name'],'corporation_id':corporation_id,
                  'assets_as_of':parts['assets']['fetched'],'assets_expires':parts['assets']['expires'],
                  **{k:p['data'] for k,p in parts.items()}}
        stock,wip,bps,jobs,locations=live_inventory(self.catalog,[snapshot],settings['location_ids'])
        names={c['id']:c['name'] for c in self.store.characters()}
        for job in jobs:
            job['corporation_id']=corporation_id
            job['character_id']=job.get('installer_id')
            job['character_name']=names.get(job.get('installer_id'),str(job.get('installer_id') or '–'))
        stale=[corp['name']] if min(p['expires'] for p in parts.values())<=time.time() else []
        return stock,wip,bps,jobs,locations,stale

    def _context(self, corporation_id=None):
        corporation_id=self.scope_id(corporation_id)
        settings = self.scope_settings(corporation_id)
        if corporation_id is not None:
            stock,wip,bps,jobs,_,stale=self.corporation_data(corporation_id,settings,strict=True)
        else:
            stock, wip, bps, jobs, _, stale = self.live_data(settings, strict=settings['source'] == 'eve')
        if settings['source'] != 'eve':
            stock, wip = {}, {}
        return dict(settings=settings, stock=stock, wip=wip, blueprints=bps, jobs=jobs, stale=stale,
                    skill_profiles=production_profiles(self.store,settings,corporation_id),
                    corporation_id=corporation_id,inventory=self.store.mapping('inventory',corporation_id),
                    parameters=self.store.mapping('parameters',corporation_id))

    def _calculate(self, product_id, quantity, context, reservations=None, own=None, manufacturer_id=None,allow_pending=False):
        settings = context['settings']
        plan = self.planner.calculate(product_id, quantity, settings, context['inventory'], context['parameters'],
                                      context['stock'], context['wip'], context['blueprints'], context['jobs'],
                                      reservations=reservations, own_reservations=own,
                                      skill_profiles=context['skill_profiles'],manufacturer_id=manufacturer_id)
        # Asset and job caches can disagree just after delivery. Do not allocate
        # those materials or create duplicate production until the assets catch up.
        planned = {r['id']: r for r in plan['rows']}
        waiting = {}
        for job in context['jobs'] if settings['source'] == 'eve' else []:
            if settings['location_ids'] and job.get('output_location_id') not in settings['location_ids']:
                continue
            row = planned.get(job.get('product_type_id'))
            if not row or not row['missing'] or row['manual_stock'] or job.get('status') != 'delivered' or job.get('activity_id') not in [1, 9]:
                continue
            recipe=self.catalog.recipes.get(job.get('product_type_id'))
            if not recipe or job.get('blueprint_type_id')!=recipe['bp_id'] or job['activity_id']!=(9 if recipe['activity']=='reaction' else 1):
                continue
            if job.get('completed_date') and job.get('assets_as_of'):
                completed = datetime.fromisoformat(job['completed_date'].replace('Z', '+00:00')).timestamp()
                if completed > job['assets_as_of']:
                    waiting[(job.get('character_id'),row['id'])]={'id':row['id'],'name':row['name'],
                        'character_id':job.get('character_id'),'character_name':job.get('character_name'),
                        'assets_as_of':job['assets_as_of'],'assets_expires':job.get('assets_expires'),
                        'completed_at':completed}
        if waiting:
            items=list(waiting.values())
            retry_at=min((item['assets_expires'] for item in items if item['assets_expires']),default=time.time()+60)
            if not allow_pending:raise AssetSnapshotPending(items,retry_at)
            plan['inventory_wait']={'items':items,'retry_at':retry_at,'plan_name':None}
        plan.update(source=settings['source'], stale_characters=context['stale'], calculated_at=time.time(),
                    corporation_id=context.get('corporation_id'),scope_label=self.scope_label(context.get('corporation_id')))
        return plan

    def _allocate(self, plans, context, allow_pending=False):
        same_pool=[p for p in plans if p.get('corporation_id')==context.get('corporation_id')]
        return allocate_plans(same_pool, lambda product, quantity, held: self._calculate(product, quantity, context, held,allow_pending=allow_pending),
            calculate_saved=lambda saved,held:self._calculate(saved['product_id'],saved['quantity'],context,held,
                                                            manufacturer_id=saved.get('manufacturer_id'),allow_pending=allow_pending))

    def manufacturer(self,value,corporation_id=None,allow_missing=None):
        if value is None or value in ['', 'auto']:return None
        if value=='manual':return 0
        if isinstance(value,str) and re.fullmatch(r'[0-9]+',value):value=int(value)
        value=integer(value,'Gyártó karakter',2**53-1,0)
        if value==0:return 0
        if value==allow_missing:return value
        character=next((c for c in self.store.characters() if c['id']==value),None)
        if not character or corporation_id is not None and character.get('corporation_id')!=corporation_id:
            raise PlanningError('A gyártó karakter nincs hozzáadva vagy nem ehhez a corporationhöz tartozik.')
        return value

    @staticmethod
    def _saved(plans, plan_id):
        found = next((p for p in plans if p['id'] == plan_id), None)
        if not found:
            raise PlanningError('Ez a mentett terv már nem található. Nyiss meg másik tervet vagy kezdj újat.')
        return found

    def plan(self, product_id, quantity, saved_plan_id=None, corporation_id=None, manufacturer_id='saved',allow_preview=False):
        with self.planning_lock, self.catalog.lock:
            context = self._context(corporation_id)
            plans = self.store.plans()
            saved = self._saved(plans, saved_plan_id) if saved_plan_id else None
            manufacturer_id=saved.get('manufacturer_id') if manufacturer_id=='saved' and saved else None if manufacturer_id=='saved' else self.manufacturer(manufacturer_id,context['corporation_id'],saved.get('manufacturer_id') if saved else None)
            if saved and saved.get('corporation_id')!=context.get('corporation_id'):
                raise PlanningError('A mentett terv másik készlethez tartozik. Nyisd meg a saját gyártási körében.')
            if saved and saved['product_id'] != product_id:
                raise PlanningError('Másik termékhez kezdj új tervet; a mentett terv saját foglalása csak a saját céljához használható.')
            # Editing a saved quantity previews the same priority allocation that
            # saving it will commit. No persistent reservation changes on GET.
            preview = [{**p, 'quantity': quantity} if p['id'] == saved_plan_id else p for p in plans]
            try:
                allocation = self._allocate(preview, context)
                other, own = except_owner(allocation, saved_plan_id)
                plan = self._calculate(product_id, quantity, context, other, own,manufacturer_id)
            except AssetSnapshotPending:
                if not allow_preview:raise
                # Read-only preview: keep the exact same cached assets/WIP and
                # reservation priority. Never invent delivered output or write
                # provisional holds. All saving/scheduling paths remain strict.
                allocation = self._allocate(preview, context,allow_pending=True)
                other, own = except_owner(allocation, saved_plan_id)
                plan = self._calculate(product_id, quantity, context, other, own,manufacturer_id,allow_pending=True)
                waits=allocation['pending']+([plan['inventory_wait']] if plan.get('inventory_wait') else [])
                plan.update(preview_only=True,inventory_wait=pending_info(waits))
            plan['saved_plan'] = ({**saved, 'preview_changed': quantity != saved['quantity'] or (manufacturer_id or 0)!=(saved.get('manufacturer_id') or 0)} if saved else None)
            plan['reservation_summary'] = {'active_count': allocation['active_count'],
                'other_plan_count': allocation['active_count']-int(bool(saved and saved['reserve_active'])),
                'own': allocation['by_plan'].get(saved_plan_id),'provisional':bool(plan.get('preview_only'))}
            return plan

    def schedule(self,data):
        with self.planning_lock,self.catalog.lock:
            cid=self.scope_id(data.get('corporation_id'))
            context=self._context(cid)
            product=integer(data.get('product_id'),'Termék',10**9,1)
            quantity=data.get('quantity');sid=data.get('saved_plan_id')
            plans=self.store.plans();saved=self._saved(plans,sid) if sid else None
            if saved and (saved.get('corporation_id')!=cid or saved['product_id']!=product):
                raise PlanningError('A mentett terv más termékhez vagy gyártási körhöz tartozik.')
            preview=[{**p,'quantity':quantity} if p['id']==sid else p for p in plans]
            allocation=self._allocate(preview,context);other,own=except_owner(allocation,sid)
            context['reservations']=other
            def calculate(current):return self._calculate(product,quantity,current,other,own,None)
            return scheduler.build(context,self.store,self.catalog,calculate,data)

    def shopping_summary(self,allow_preview=False):
        """Preview every saved goal against one pool; no persistent holds change."""
        with self.planning_lock, self.catalog.lock:
            plans=self.store.plans()
            if not plans:
                return {'rows':[], 'plans':[], 'source':self.store.settings()['source'],
                        'stale_characters':[], 'calculated_at':time.time()}
            contexts={cid:self._context(cid) for cid in dict.fromkeys(p.get('corporation_id') for p in plans)}
            # Active reservations retain their priority. Unreserved saved plans
            # use only what remains, in creation order, without activating them.
            last=max([time.time()]+[p['reserved_at'] or p['created'] for p in plans])
            inactive=sorted((p for p in plans if not p['reserve_active']),key=lambda p:(p['created'],p['id']))
            priority={p['id']:last+i+1 for i,p in enumerate(inactive)}
            virtual=[{**p,'reserve_active':True,'reserved_at':priority[p['id']]} if not p['reserve_active'] else p for p in plans]
            allocation={'by_plan':{}};waits=[]
            for context in contexts.values():
                try:part=self._allocate(virtual,context)
                except AssetSnapshotPending:
                    if not allow_preview:raise
                    part=self._allocate(virtual,context,allow_pending=True);waits.extend(part['pending'])
                allocation['by_plan'].update(part['by_plan'])
            rows={};included=[];formulas=set()
            for saved in sorted(plans,key=lambda p:(self.scope_label(p.get('corporation_id')),allocation['by_plan'][p['id']]['priority'])):
                result=allocation['by_plan'][saved['id']]
                included.append({key:saved[key] for key in ['id','name','product_id','quantity','reserve_active','corporation_id']})
                included[-1]['scope_label']=self.scope_label(saved.get('corporation_id'))
                included[-1].update(priority=result['priority'],shopping_items=len(result['shopping']))
                for material in result['shopping']:
                    tid=material['id']
                    reusable=material['category']=='Reakcióformula'
                    pool=(saved.get('corporation_id'),tid)
                    if reusable and pool in formulas:continue
                    if reusable:formulas.add(pool)
                    if tid not in rows:
                        rows[tid]={key:material[key] for key in ['id','name','category','unit','copy_runs','note'] if key in material}
                        rows[tid].update(required=0,used_stock=0,used_wip=0,buy=0,plans=[])
                    row=rows[tid]
                    for key in ['required','used_stock','used_wip','buy']:row[key]+=material[key]
                    row['plans'].append({'id':saved['id'],'name':saved['name'],'quantity':saved['quantity'],'buy':material['buy'],
                                         'corporation_id':saved.get('corporation_id'),'scope_label':self.scope_label(saved.get('corporation_id'))})
            blueprint_ids={r['bp_id'] for r in self.catalog.recipes.values()}
            for row in rows.values():row['is_blueprint']=row['id'] in blueprint_ids
            return {'rows':sorted(rows.values(),key=lambda r:(r['category'],r['name'].casefold())),
                    'plans':included,'source':self.store.settings()['source'],'separate_pools':len(contexts)>1 or any(contexts),
                    'stale_characters':list(dict.fromkeys(n for c in contexts.values() for n in c['stale'])),'calculated_at':time.time(),
                    **({'preview_only':True,'inventory_wait':pending_info(waits)} if waits else {})}

    def save_plan(self, data):
        with self.planning_lock, self.catalog.lock:
            product = integer(data.get('product_id'), 'Termék', 10**9, 1)
            if product not in self.catalog.recipes:
                raise PlanningError('Ismeretlen gyártható termék.')
            quantity = integer(data.get('quantity'), 'Mennyiség', 10**8 if self.catalog.recipes[product]['activity']=='reaction' else 10**6, 1)
            plans = self.store.plans()
            old = self._saved(plans, data['id']) if data.get('id') else None
            corporation_id=self.scope_id(data.get('corporation_id'))
            manufacturer_id=self.manufacturer(data.get('manufacturer_id',old.get('manufacturer_id') if old else None),corporation_id,old.get('manufacturer_id') if old else None)
            if old and old.get('corporation_id')!=corporation_id:
                raise PlanningError('A terv készlettulajdonosa nem módosítható. Másik corporationhöz kezdj új tervet.')
            if old and old['product_id'] != product:
                raise PlanningError('Másik terméket új tervként ments el.')
            now = time.time()
            saved = {'id': old['id'] if old else str(uuid.uuid4()),
                     'name': str(data.get('name') or self.catalog.name(product))[:120].strip(),
                     'product_id': product, 'quantity': quantity,'manufacturer_id':manufacturer_id,
                     'created': old['created'] if old else now, 'reserve_active': old['reserve_active'] if old else True,'corporation_id':corporation_id,
                     'reserved_at': (old['reserved_at'] if old and old['reserve_active'] else now) if not old or old['reserve_active'] else None}
            proposed = [p for p in plans if p['id'] != saved['id']]+[saved]
            allocation = self._allocate(proposed, self._context(corporation_id)) if saved['reserve_active'] else None
            self.store.save_plan(saved)
            return {'ok': True, 'id': saved['id'], 'allocation': allocation['by_plan'][saved['id']] if allocation else None}

    def set_reservation(self, plan_id, active, expected=None):
        if not isinstance(active, bool):
            raise PlanningError('A foglalás állapota igaz vagy hamis lehet.')
        with self.planning_lock, self.catalog.lock:
            plans = self.store.plans()
            old = self._saved(plans, plan_id)
            if expected is not None and expected!=reservation_revision(plans,old.get('corporation_id')):raise PlanningError('A foglalások megváltoztak. Frissítsd a listát, majd próbáld újra.')
            saved = {**old, 'reserve_active': active,
                     'reserved_at': (old['reserved_at'] if old['reserve_active'] else time.time()) if active else None}
            if active:
                self._allocate([p for p in plans if p['id'] != plan_id]+[saved], self._context(old.get('corporation_id')))
            self.store.save_plan(saved)

    def reorder_reservations(self,data):
        if not isinstance(data,dict) or set(data)!={'corporation_id','ids','revision'}:raise PlanningError('Hibás foglalási sorrend.')
        with self.planning_lock,self.catalog.lock:
            cid=self.scope_id(data['corporation_id']);plans=self.store.plans()
            proposed=reorder_reservations(plans,data['ids'],cid,data['revision'])
            if [p['id'] for p in ordered_active([p for p in plans if p.get('corporation_id')==cid])]!=data['ids']:
                self._allocate(proposed,self._context(cid))
                self.store.save_reservation_order(cid,data['revision'],proposed)
            return {'ok':True,'revision':reservation_revision(self.store.plans(),cid)}

    def remove_plan(self, plan_id):
        with self.planning_lock:
            self.store.remove_plan(plan_id)

    def state(self, corporation_id=None):
        with self.planning_lock, self.catalog.lock:
            return self._state(self.scope_id(corporation_id))

    def _state(self, corporation_id=None):
        settings = self.scope_settings(corporation_id)
        _, _, bps, jobs, locations, stale = (self.live_data(settings) if corporation_id is None else self.corporation_data(corporation_id,settings))
        plans = self.store.plans()
        reservation_error = None
        delivery_wait = None
        allocation = {'by_plan': {}}
        for cid in dict.fromkeys(p.get('corporation_id') for p in plans if p['reserve_active']):
            try:
                allocation['by_plan'].update(self._allocate(plans, self._context(cid))['by_plan'])
            except (PlanningError, EsiError) as error:
                for p in plans:
                    if p.get('corporation_id')==cid:p['allocation_error']=str(error)
                if cid==corporation_id:
                    reservation_error = str(error)
                    if isinstance(error,AssetSnapshotPending):delivery_wait=error.info
        for saved in plans:
            saved['activity']=self.catalog.recipes.get(saved['product_id'],{}).get('activity')
            saved['product_name'] = self.catalog.name(saved['product_id'])
            saved['scope_label']=self.scope_label(saved.get('corporation_id'))
            saved['allocation'] = allocation['by_plan'].get(saved['id'])
        for cid in dict.fromkeys(p.get('corporation_id') for p in plans):
            for rank,p in enumerate(ordered_active([p for p in plans if p.get('corporation_id')==cid]),1):p['reservation_priority']=rank
        chars = self.store.characters()
        for char in chars:
            char['data_times'] = {kind: (self.store.snapshot(char['id'], kind) or {}).get('fetched') for kind in ['assets', 'blueprints', 'jobs']}
        return {'version': __version__, 'csrf': self.csrf, 'settings': settings,
                'corporation_id':corporation_id,'scope_label':self.scope_label(corporation_id),
                'corporations':corporation_dashboard(self.store)['corporations'],'corporation_scopes':CORPORATION_SCOPES,
                'industry_facilities':{a:{'system_id':settings[a].get('system_id'),'system_name':self.catalog.moon_systems.get(settings[a].get('system_id'),{}).get('name')} for a in ['manufacturing','reaction']},
                'production_characters':[{k:p[k] for k in ['id','name','available','as_of']} for p in production_profiles(self.store,settings,corporation_id)],
                'characters': chars, 'plans': plans, 'invention_products':sorted(self.catalog.inventions), 'reservation_revision':reservation_revision(plans,corporation_id), 'reservation_error': reservation_error,'delivery_wait':delivery_wait,
                'inventory': self.store.mapping('inventory',corporation_id), 'parameters': self.store.mapping('parameters',corporation_id),
                'locations': locations, 'jobs': [j for j in jobs if j.get('status') in ['active', 'paused', 'ready']],
                'blueprint_count': len(bps), 'stale_characters': stale, 'sde': self.catalog.meta,
                'recipe_count': sum(self.catalog.types.get(i, {}).get('published', 0) for i in self.catalog.recipes),
                'fleet_running':self.fleet.status()['task']['running'],'task': self.task_snapshot(), 'callback': self.origin+'/callback', 'scopes': SCOPES, 'skill_scopes': SKILL_SCOPES, 'pi_scopes': PI_SCOPES, 'intel_scopes':INTEL_SCOPES,'implant_scopes':IMPLANT_SCOPES,'contract_scopes':CONTRACT_SCOPES,'market_scopes':self.trade.dashboard()['scopes'],'mining_scopes':mining.MINING_SCOPES,
                'crypto_available': crypto_available()}


def crypto_available():
    try:
        import cryptography
        return bool(cryptography)
    except ImportError:
        return False


def validated_settings(data, current):
    result = copy.deepcopy(current)
    for key, value in data.items():
        if key == 'source':
            if value not in ['manual', 'eve']:
                raise PlanningError('Ismeretlen készletforrás.')
            result['source_explicit'] = True
        elif key == 'client_id':
            if not isinstance(value, str) or len(value) > 200 or (value and not re.fullmatch(r'[A-Za-z0-9_-]+', value)):
                raise PlanningError('Hibás Client ID; ide a nyilvános azonosító szükséges.')
            if current['client_id'] and value != current['client_id']:
                # Existing tokens retain the client ID used to issue them.
                pass
        elif key in ['character_ids', 'location_ids']:
            if not isinstance(value, list) or len(value) > 1000:
                raise PlanningError('Hibás karakter- vagy helylista.')
            value = list(dict.fromkeys(integer(v, 'Azonosító', 2**53-1, 1) for v in value))
        elif key in ['manufacturing', 'reaction']:
            if not isinstance(value, dict) or set(value)-set(DEFAULT_SETTINGS[key]):
                raise PlanningError('Ismeretlen struktúrabeállítás.')
            group = result[key].copy()
            for field, n in value.items():
                if field=='system_id':
                    group[field]=None if n is None else integer(n,'Rendszer',2**31-1,1)
                    continue
                group[field] = float(decimal_number(n, field, .01 if field == 'skill_time' else 0,
                                                    1 if field == 'skill_time' else 10 if field=='facility_tax' else 99))
            value = group
        else:
            raise PlanningError('Ismeretlen beállítás.')
        result[key] = value
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = 'EveMuhely/'+__version__

    @property
    def app(self):
        return self.server.app

    def log_message(self, *_args):
        # OAuth callback query strings and character data must not enter logs.
        pass

    def send(self, status, data, content_type='application/json; charset=utf-8', cookie=False, headers=None):
        if isinstance(data, (dict, list)):
            data = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        elif isinstance(data, str):
            data = data.encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https://images.evetech.net; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if cookie:
            self.send_header('Set-Cookie', f'eve_session={self.app.cookie}; HttpOnly; SameSite=Lax; Path=/')
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def host_ok(self):
        return self.headers.get('Host', '') in [f'127.0.0.1:{self.app.port}', f'localhost:{self.app.port}']

    def authorized(self):
        try:
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            return secrets.compare_digest(cookie['eve_session'].value, self.app.cookie)
        except (KeyError, ValueError):
            return False

    def do_GET(self):
        try:
            if not self.host_ok():
                return self.send(403, {'error': 'Csak a helyi cím használható.'})
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path
            query = urllib.parse.parse_qs(parsed.query)
            if path == '/health':
                return self.send(200, {'app': 'eve-muhely', 'version': __version__})
            if path == '/':
                return self.send(200, (ROOT/'static/index.html').read_bytes(), 'text/html; charset=utf-8', cookie=True)
            if path in ['/invention.js', '/boosts.js', '/reservations.js', '/contracts.js', '/trade.js', '/battle.js', '/fleet.js', '/assets.js', '/jobs.js', '/app.js', '/i18n.js', '/i18n-en.js', '/theme.js', '/tables.js', '/numbers.js', '/corporations.js', '/style.css', '/graph.js', '/graph.css', '/skills.js', '/pi.js', '/mining.js', '/moons.js', '/moon-transfer.js', '/costs.js', '/prices.js', '/economics.js', '/extractions.js', '/settings.js', '/multibuy.js', '/accounts.js', '/schedule.js', '/schedule-graph.js', '/documentation.js', '/desktop.js', '/notifications.js', '/activity.js', '/intel.js', '/intel-map.js', '/app-window-icon.png', '/icon.svg']:
                return self.send(200, (ROOT/'static'/path[1:]).read_bytes(),
                                 mimetypes.guess_type(path)[0] or 'application/octet-stream')
            if path.startswith('/desktop/auth/'):
                ticket = path.removeprefix('/desktop/auth/')
                with self.app.desktop_auth_lock:
                    handoff = self.app.desktop_auth.get(ticket)
                    if not handoff or handoff['expires'] <= time.time() or handoff['opened']:
                        return self.send(404, {'error':'Az EVE-belépés lejárt. Próbáld újra.'})
                    handoff['opened'] = True
                    return self.send(303,b'',cookie=True,headers={'Location':handoff['url']})
            if path.startswith('/calendar/moons/'):
                token = moon_calendar.feed_token(self.app.store)
                supplied = path.removeprefix('/calendar/moons/').removesuffix('.ics')
                if not token or not path.endswith('.ics') or not secrets.compare_digest(supplied, token):
                    return self.send(404, {'error': 'Nincs ilyen naptár.'})
                with self.app.catalog.lock:
                    return self.send(200, moon_calendar.export(self.app.store, self.app.catalog, query.get('lang', ['en'])[0]), 'text/calendar; charset=utf-8')
            if not self.authorized():
                return self.send(403, {'error': 'Nyisd meg az alkalmazás kezdőlapját.'})
            if path == '/api/fleet':return self.send(200,self.app.fleet.dashboard())
            if path == '/api/jobs':
                cid=self.app.scope_id(query.get('corporation_id',[None])[0])
                with self.app.catalog.lock:return self.send(200,job_browser.dashboard(self.app.store,self.app.catalog,cid))
            if path == '/api/assets':
                cid=self.app.scope_id(query.get('corporation_id',[None])[0])
                with self.app.catalog.lock:data=assets.dashboard(self.app.store,self.app.catalog,cid)
                return self.send(200,self.app.asset_locations.decorate(data,cid))
            if path == '/api/intel':
                center=integer(int(query.get('center',['0'])[0]),'Rendszer',2**31-1,0) or None
                radius=integer(int(query.get('radius',['5'])[0]),'Jump',12,1)
                return self.send(200,self.app.intel.dashboard(center,radius,query.get('history',['0'])[0]=='1',region=integer(int(query.get('region',['0'])[0]),'Régió',2**31-1,0) or None,character_id=integer(int(query.get('character_id',['0'])[0]),'Karakter',2**31-1,0) or None))
            if path == '/api/intel/channels':return self.send(200,{'channels':self.app.intel.channels(query.get('folder',[''])[0])})
            if path == '/api/boosts':return self.send(200,self.app.boosts.snapshot())
            if path == '/api/boosts/channels':return self.send(200,{'channels':boost_channels(query.get('folder',[''])[0])})
            if path == '/api/intel/systems':
                q=query.get('q',[''])[0].strip().casefold()
                rows=[s for s in self.app.intel.universe.systems.values() if q and q in s['name'].casefold()]
                return self.send(200,sorted(rows,key=lambda s:(not s['name'].casefold().startswith(q),s['name']))[:40])
            if path == '/api/intel/alerts':return self.send(200,intel.collect_alerts(self.app.store,self.app.intel.universe))
            if path == '/api/activity':return self.send(200,self.app.activity())
            if path == '/api/notifications':
                return self.send(200,self.app.notification_data())
            if path == '/api/contracts':return self.send(200,contracts.dashboard(self.app.store,query.get('scope',['personal'])[0],query.get('owner',[None])[0],query.get('start',[None])[0],query.get('end',[None])[0],self.app.eve.granted_scopes(),self.app.asset_locations))
            if path == '/api/contracts/details':return self.send(200,contracts.details(self.app.eve,self.app.catalog,query.get('scope',['personal'])[0],int(query.get('owner',['0'])[0]),int(query.get('id',['0'])[0])))
            if path == '/api/implants':return self.send(200,self.app.fleet.implants.dashboard())
            if path == '/api/desktop/auth':
                with self.app.desktop_auth_lock:
                    item = self.app.desktop_auth.get(query.get('ticket',[''])[0])
                    if not item or item['expires'] <= time.time():
                        return self.send(200,{'status':'error','error':'Az EVE-belépés lejárt. Próbáld újra.'})
                    return self.send(200,{'status':item['status'],'error':item.get('error')})
            if path == '/callback':
                error = query.get('error')
                if error==['invalid_scope']:
                    raise PlanningError('Az EVE Developer alkalmazás nem engedélyezi az egyik kért scope-ot. Add hozzá a Beállításokban felsorolt kért olvasási engedélyeket a Client ID alkalmazásához, majd lépj be újra.')
                if error:
                    raise PlanningError('Az EVE-belépés megszakadt. Az EVE-kapcsolat oldalon újraindítható.')
                self.app.eve.finish(query.get('state', [''])[0], query.get('code', [''])[0], self.app.cookie)
                if self.app.eve.authorized_feature=='intel':self.app.intel.request_locations()
                if self.app.eve.authorized_feature=='contracts':
                    try:self.app.start_task('contracts')
                    except PlanningError:pass
                if self.app.eve.authorized_feature=='mining':
                    try:self.app.start_task('mining')
                    except PlanningError:pass
                if self.app.eve.authorized_feature=='moons':
                    try:self.app.start_task('extractions')
                    except PlanningError:pass
                if self.app.desktop_auth_finish(query.get('state',[''])[0]):
                    return self.send(200,'<!doctype html><html><head><meta charset="utf-8"><title>EVE Workshop</title></head><body><h1>EVE authorization complete</h1><p>Return to the EVE Workshop application. You can close this browser tab.</p><p>A belépés sikerült. Térj vissza az EVE Műhely alkalmazásablakába. Ezt a böngészőlapot bezárhatod.</p></body></html>','text/html; charset=utf-8')
                return self.send(303, b'', headers={'Location': '/?connected=1'})
            if path == '/api/documentation':
                language = query.get('lang', ['hu'])[0]
                if language not in ['hu', 'en']:
                    raise PlanningError('Ismeretlen kézikönyvnyelv.')
                name = 'UserGuide.en.md' if language == 'en' else 'Hasznalat.md'
                return self.send(200, {'language': language, 'markdown': (ROOT/name).read_text(encoding='utf-8')})
            if path == '/api/state':
                return self.send(200, self.app.state(query.get('corporation_id',[None])[0]))
            if path == '/api/corporations':
                return self.send(200,corporation_dashboard(self.app.store))
            if path == '/api/accounts':return self.send(200,accounts.dashboard(self.app.store))
            if path == '/api/mining':
                with self.app.catalog.lock:
                    return self.send(200,mining.dashboard(self.app.store,self.app.catalog,query.get('start',[None])[0],query.get('end',[None])[0],int(query.get('character_id',['0'])[0]),int(query.get('ore_id',['0'])[0]),self.app.eve.granted_scopes()))
            if path == '/api/skills':
                with self.app.catalog.lock:
                    return self.send(200, skill_dashboard(self.app.store,self.app.catalog))
            if path == '/api/industry':return self.send(200,self.app.industry.status())
            if path == '/api/trade':return self.send(200,self.app.trade.dashboard())
            if path == '/api/invention/options':return self.send(200,self.app.invention_options(int(query.get('product_id',['0'])[0]),query.get('plan_id',[None])[0]))
            if path == '/api/trade/plan':return self.send(200,self.app.trade.finance(query.get('plan_id',[None])[0]))
            if path == '/api/trade/seller':return self.send(200,self.app.trade.profile(int(query.get('character_id',['0'])[0]),query.get('source',['jita'])[0]))
            if path == '/api/industry/system':return self.send(200,self.app.industry.system(int(query.get('id',['0'])[0]),self.app.catalog))
            if path == '/api/prices':
                ids=market_ids([int(v) for v in query.get('ids',[''])[0].split(',') if v],self.app.catalog)
                source=query.get('source',['jita'])[0]
                if source not in ['jita','local']:raise PlanningError('Ismeretlen árforrás.')
                if source=='local':return self.send(200,self.app.trade.prices(ids))
                return self.send(200,self.app.market.snapshot(ids))
            if path == '/api/moons/calendar':
                return self.send(200, moon_calendar.feed_status(self.app.store, self.app.origin))
            if path == '/api/moons/calendar.ics':
                with self.app.catalog.lock:
                    return self.send(200, moon_calendar.export(self.app.store, self.app.catalog, query.get('lang', ['en'])[0]), 'text/calendar; charset=utf-8', headers={'Content-Disposition': 'attachment; filename="eve-moon-extractions.ics"'})
            if path == '/api/moons/export':
                with self.app.catalog.lock:return self.send(200,moon_transfer.export_register(self.app.store,self.app.catalog))
            if path == '/api/moons':
                with self.app.catalog.lock:return self.send(200,moons.dashboard(self.app.store,self.app.catalog,self.app.eve.granted_scopes()))
            if path == '/api/moons/crystals':
                with self.app.catalog.lock:return self.send(200,extractions.crystal_plan(self.app.store,self.app.catalog,query.get('moon_id',[''])[0],query.get('event_id',[None])[0]))
            if path == '/api/moons/systems':
                with self.app.catalog.lock:return self.send(200,moons.system_search(self.app.catalog,query.get('q',[''])[0]))
            if path == '/api/moons/system':
                return self.send(200,moons.system_info(self.app.store,self.app.catalog,self.app.eve.http,int(query.get('id',['0'])[0])))
            if path == '/api/pi':
                with self.app.catalog.lock:
                    return self.send(200,pi_dashboard(self.app.store,self.app.catalog,int(query.get('hours',['24'])[0])))
            if path == '/api/search':
                return self.send(200, self.app.catalog.search(query.get('q', [''])[0][:200], query.get('all', ['0'])[0] == '1'))
            if path == '/api/plans/shopping':
                return self.send(200,self.app.shopping_summary(allow_preview=query.get('preview',['0'])[0]=='1'))
            if path == '/api/plan':
                return self.send(200, self.app.plan(int(query.get('product_id', ['0'])[0]), int(query.get('quantity', ['1'])[0]),
                                                   query.get('saved_plan_id', [None])[0],query.get('corporation_id',[None])[0],query.get('manufacturer_id',['saved'])[0],allow_preview=query.get('preview',['0'])[0]=='1'))
            return self.send(404, {'error': 'Nincs ilyen oldal.'})
        except (PlanningError, EsiError, ValueError) as error:
            message = str(error) if isinstance(error, (PlanningError, EsiError)) else 'Hibás kérés.'
            if urllib.parse.urlsplit(self.path).path == '/callback':
                self.app.desktop_auth_finish(urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get('state',[''])[0],message)
                import html
                return self.send(400, '<!doctype html><html lang="hu"><head><meta charset="utf-8"><title>EVE-belépés</title><script src="/i18n-en.js"></script><script src="/i18n.js"></script></head><body><h1>A belépés nem fejeződött be</h1><p>'+html.escape(message)+'</p><a href="/">Vissza az alkalmazáshoz</a></body></html>', 'text/html; charset=utf-8')
            return self.send(400, {'error': message,**({'delivery_wait':error.info} if isinstance(error,AssetSnapshotPending) else {})})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.send(500, {'error': 'A kérés nem sikerült. A korábbi adatok megmaradtak.'})

    def do_POST(self):
        try:
            origin = self.headers.get('Origin', '')
            if (not self.host_ok() or not self.authorized() or
                origin not in [self.app.origin, f'http://localhost:{self.app.port}'] or
                not secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), self.app.csrf)):
                return self.send(403, {'error': 'A kérés csak az alkalmazás saját oldaláról indítható.'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.send(415, {'error': 'JSON kérés szükséges.'})
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 2*1024*1024:
                return self.send(413, {'error': 'A kérés túl nagy vagy üres.'})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise PlanningError('Hibás kérés.')
            path = urllib.parse.urlsplit(self.path).path
            query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            corporation_id=self.app.scope_id(query.get('corporation_id',[None])[0])
            if path == '/api/fleet/preferences':return self.send(200,fleet.save_preferences(self.app.store,data))
            elif path == '/api/boosts/start':return self.send(200,self.app.boosts.start(data.get('folder'),data.get('channel')))
            elif path == '/api/boosts/stop':return self.send(200,self.app.boosts.stop())
            elif path == '/api/fleet/sides':return self.send(200,self.app.fleet.configure_sides(data))
            elif path == '/api/fleet/refresh':return self.send(200,self.app.fleet.start_refresh(data.get('character_id'),data.get('session_id')))
            elif path == '/api/intel/preferences':return self.send(200,self.app.intel.configure(data))
            elif path == '/api/intel/characters':
                self.app.intel.request_characters(manual=True);return self.send(200,{'intel':dict(self.app.intel.status)})
            elif path == '/api/intel/locations':
                self.app.intel.request_locations();return self.send(200,{'intel':dict(self.app.intel.status)})
            elif path == '/api/intel/claim':return self.send(200,{'items':notifications.claim(self.app.store,intel.collect_alerts(self.app.store,self.app.intel.universe))})
            elif path == '/api/industry/refresh':
                self.app.industry.start(manual=data.get('manual') is True);return self.send(200,self.app.industry.status())
            elif path == '/api/invention/estimate':return self.send(200,self.app.invention_estimate(data))
            elif path == '/api/industry/estimate':
                with self.app.catalog.lock:return self.send(200,self.app.industry.estimate(data.get('rows'),self.app.store.settings(),self.app.catalog))
            elif path == '/api/trade/hauling':return self.send(200,self.app.trade.save_hauling(data))
            elif path == '/api/trade/settings':return self.send(200,self.app.trade.save(data))
            elif path == '/api/trade/discover':return self.send(200,self.app.trade.discover(data))
            elif path == '/api/trade/plan':return self.send(200,self.app.trade.save_finance(data))
            elif path == '/api/trade/seller/refresh':return self.send(200,self.app.trade.refresh_profile(data.get('character_id'),data.get('source','jita'),data.get('manual') is True))
            elif path == '/api/prices/refresh':
                ids=market_ids(data.get('ids'),self.app.catalog)
                source=data.get('source','jita')
                if source not in ['jita','local']:raise PlanningError('Ismeretlen árforrás.')
                if source=='local':return self.send(200,self.app.trade.prices(ids,True,data.get('manual') is True))
                self.app.market.start(ids,manual=data.get('manual') is True)
                return self.send(200,self.app.market.snapshot(ids))
            elif path == '/api/schedule':
                return self.send(200,self.app.schedule(data))
            elif path == '/api/accounts':
                return self.send(200,accounts.save(self.app.store,data))
            elif path == '/api/moons/calendar':
                action = data.get('action')
                if action not in ['enable', 'reset', 'disable']:
                    raise PlanningError('Hibás kérés.')
                moon_calendar.feed_token(self.app.store, action)
                return self.send(200, moon_calendar.feed_status(self.app.store, self.app.origin))
            elif path == '/api/moons/import/preview':
                with self.app.catalog.lock:return self.send(200,moon_transfer.preview(self.app.store,self.app.catalog,data))
            elif path == '/api/moons/import':
                with self.app.catalog.lock:return self.send(200,moon_transfer.apply_import(self.app.store,self.app.catalog,data))
            elif path == '/api/moons/save':
                with self.app.catalog.lock:
                    value=moons.validate_moon(data,self.app.catalog,self.app.store.moon_records())
                    self.app.store.save_moon(value)
                return self.send(200,{'ok':True,'id':value['id']})
            elif path == '/api/moons/remove':
                if not isinstance(data.get('id'),str):raise PlanningError('Ismeretlen hold.')
                self.app.store.remove_moon(data['id'])
            elif path == '/api/moons/extractions/sync':
                self.app.start_task('extractions',manual=data.get('manual') is True)
            elif path == '/api/moons/settings':
                self.app.store.save_moon_preferences(moons.validate_preferences(data))
            elif path == '/api/moons/sync':
                self.app.start_task('moons',manual=data.get('manual') is True)
            elif path == '/api/settings':
                if corporation_id is not None:
                    if set(data)-{'location_ids','source'} or data.get('source','eve')!='eve':
                        raise PlanningError('Corp gyártás kizárólag a saját corporation EVE-készletével számolhat.')
                    updated=validated_settings(data,self.app.scope_settings(corporation_id))
                    current=self.app.store.settings();current.setdefault('corporation_locations',{})[str(corporation_id)]=updated['location_ids']
                    self.app.store.save_settings(current)
                else:
                    updated=validated_settings(data, self.app.store.settings())
                    for activity in ['manufacturing','reaction']:
                        sid=updated[activity].get('system_id')
                        if sid is not None and sid not in self.app.catalog.moon_systems:raise PlanningError('Ismeretlen rendszer.')
                    self.app.store.save_settings(updated)
            elif path in ['/api/inventory', '/api/parameters']:
                table = 'inventory' if path.endswith('inventory') else 'parameters'
                existing = self.app.store.mapping(table,corporation_id)
                if len(data) > 4000:
                    raise PlanningError('Túl sok módosítás egy kérésben.')
                updates = {}
                for tid, patch in data.items():
                    type_id = integer(int(tid), 'Termékazonosító', 10**9, 1)
                    if type_id not in self.app.catalog.types or not isinstance(patch, dict):
                        raise PlanningError('Ismeretlen termék vagy hibás módosítás.')
                    allowed = ['quantity', 'reserved', 'wip'] if table == 'inventory' else ['source', 'me', 'te', 'job_runs', 'total_runs', 'mode', 'item_id']
                    if set(patch)-set(allowed):
                        raise PlanningError('Ismeretlen mező.')
                    value = existing.get(type_id, {}).copy()
                    for key, n in patch.items():
                        if n is None:
                            value.pop(key, None)
                        elif key in ['source', 'mode']:
                            if n not in (['auto', 'manual'] if key == 'source' else ['build', 'buy']):
                                raise PlanningError('Ismeretlen blueprintbeállítás.')
                            value[key] = n
                        else:
                            value[key] = integer(n, key, 10 if key == 'me' else 20 if key == 'te' else 2**53-1 if key == 'item_id' else 10**6 if key == 'job_runs' else 10**12,
                                                 1 if key in ['job_runs', 'item_id'] else 0)
                    updates[type_id] = value
                self.app.store.save_mapping(table, updates,corporation_id)
            elif path == '/api/auth/start':
                if not crypto_available():
                    raise PlanningError('A belépéshez hiányzik a cryptography csomag. Futtasd az egyszeri telepítőt.')
                char_id=data.get('character_id')
                if char_id is not None:
                    char_id=integer(char_id,'Karakter',2**53-1,1)
                    if char_id not in {c['id'] for c in self.app.store.characters()}:
                        raise PlanningError('A karakter már nincs hozzáadva.')
                feature=data.get('feature')
                if feature not in [None,'skills','pi','corporations','moons','intel','mining','markets','implants','contracts','all']:raise PlanningError('Ismeretlen engedélyezési cél.')
                url = self.app.eve.start(self.app.cookie, self.app.origin+'/callback',char_id,feature)
                return self.send(200,self.app.desktop_auth_start(url) if data.get('desktop') is True else {'url':url})
            elif path == '/api/characters/remove':
                self.app.eve.forget(integer(data.get('id'), 'Karakter', 2**53-1, 1))
            elif path == '/api/notifications/dismiss':
                with self.app.catalog.lock:
                    notifications.dismiss(self.app.store,self.app.notification_data(),data)
                return self.send(200,{'ok':True})
            elif path == '/api/notifications/preferences':
                return self.send(200,notifications.save_preferences(self.app.store,data))
            elif path == '/api/implants/preferences':
                from .implants import save_preferences
                save_preferences(self.app.store,data)
                return self.send(200,self.app.fleet.implants.dashboard())
            elif path == '/api/implants/claim':
                from .implants import events
                return self.send(200,{'items':notifications.claim(self.app.store,{'items':events(self.app.store),'observed_domains':['implants:'+str(c['id']) for c in self.app.store.characters()]})})
            elif path == '/api/notifications/claim':
                snapshot=self.app.notification_data()
                with self.app.task_lock:
                    items=[] if self.app.task['running'] else notifications.claim(self.app.store,snapshot)
                return self.send(200,{'items':items})
            elif path == '/api/notifications/sent':
                notifications.acknowledge(self.app.store,data.get('receipts'))
                return self.send(200,{'ok':True})
            elif path == '/api/corporations/monitoring':
                with self.app.task_lock:
                    if self.app.task['running']:raise PlanningError('Várd meg a folyamatban lévő frissítést a figyelés módosítása előtt.')
                    with self.app.eve.sync_lock:
                        self.app.store.set_corporation_monitoring(data.get('id'),data.get('enabled'))
                return self.send(200,corporation_dashboard(self.app.store))
            elif path == '/api/notifications/sync':
                with self.app.task_lock:
                    started=False if self.app.task['running'] else self.app.start_task('notifications',manual=data.get('manual') is True)
                return self.send(200,{'ok':True,'started':started,'next_sync_at':self.app.refresh_policy.next_at(self.app.refresh_domains('notifications'))})
            elif path in ['/api/sync','/api/contracts/sync','/api/skills/sync','/api/mining/sync','/api/pi/sync','/api/corporations/sync']:
                kind={'/api/contracts/sync':'contracts','/api/sync':'sync','/api/skills/sync':'skills','/api/mining/sync':'mining','/api/pi/sync':'pi','/api/corporations/sync':'corporations'}[path]
                self.app.start_task(kind,manual=data.get('manual') is True)
            elif path == '/api/sde/update':
                self.app.start_task('sde')
            elif path == '/api/plans/save':
                return self.send(200, self.app.save_plan(data))
            elif path == '/api/plans/reservation':
                self.app.set_reservation(str(data.get('id', '')), data.get('active'),data.get('revision'))
            elif path == '/api/plans/reservations/order':
                return self.send(200,self.app.reorder_reservations(data))
            elif path == '/api/plans/remove':
                self.app.remove_plan(str(data.get('id', '')))
            elif path == '/api/shutdown':
                self.send(200, {'ok': True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            else:
                return self.send(404, {'error': 'Nincs ilyen művelet.'})
            return self.send(200, {'ok': True})
        except (PlanningError, EsiError, ValueError, TypeError) as error:
            message = str(error) if isinstance(error, (PlanningError, EsiError)) else 'Hibás kérés.'
            self.send(400, {'error': message})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.send(500, {'error': 'A módosítás nem sikerült. Az előző adatok megmaradtak.'})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def server_close(self):
        if getattr(self,'_workers_stopped',False):return super().server_close()
        self._workers_stopped=True
        self.app.boosts.close()
        self.app.asset_locations.stop()
        self.app.fleet.stop()
        self.app.intel.stop()
        super().server_close()

    def shutdown(self):
        # The shutdown button and native window close share the same complete
        # teardown, including the listening socket, rather than only the loop.
        self.app.stopping=True;self.app.fleet.closed=True;self.app.intel.closed=True
        self.app.boosts.stop_event.set()
        with self.app.asset_locations.lock:self.app.asset_locations.closed=True;self.app.asset_locations.pending.clear()
        self.app.fleet.stop_event.set();self.app.intel.stop_event.set()
        super().shutdown()
        self.server_close()

    def __init__(self, app):
        self.app = app
        super().__init__(('127.0.0.1', app.port), Handler)
        app.port = self.server_address[1]
        app.origin = f'http://127.0.0.1:{app.port}'
        app.boosts.resume()


def main():
    parser = argparse.ArgumentParser(description='EVE Műhely — helyi gyártástervező')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--data-dir', type=Path, default=default_data_dir())
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('A port 1024 és 65535 közé essen.')
    os.umask(0o077)
    writable_catalog = args.data_dir/'catalog.sqlite3'
    catalog = writable_catalog if writable_catalog.exists() else ROOT/'data/catalog.sqlite3'
    if not catalog.exists():
        parser.error('Hiányzik a receptadatbázis; futtasd az egyszeri telepítőt.')
    app = App(args.data_dir, catalog, args.port)
    try:
        server = Server(app)
    except OSError:
        raise SystemExit(f'A {args.port} port foglalt. Ha az alkalmazás már fut, nyisd meg: {app.origin}')
    app.fleet.start()
    if not args.no_browser:
        threading.Timer(.4, lambda: webbrowser.open(app.origin)).start()
    print(f'EVE Műhely: {app.origin}\nAdatok: {args.data_dir}\nLeállítás: a felületen vagy Ctrl+C.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
