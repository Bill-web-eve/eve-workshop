from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import urllib.error
import urllib.parse
import urllib.request


from . import progress

ESI = 'https://esi.evetech.net'
SSO = 'https://login.eveonline.com'
INDUSTRY_SCOPES = ['esi-assets.read_assets.v1', 'esi-characters.read_blueprints.v1',
                   'esi-industry.read_character_jobs.v1']
SKILL_SCOPES = ['esi-skills.read_skills.v1', 'esi-skills.read_skillqueue.v1']
PI_SCOPES = ['esi-planets.manage_planets.v1']
SCOPES = INDUSTRY_SCOPES + SKILL_SCOPES + PI_SCOPES
CORPORATION_SCOPES = ['esi-assets.read_corporation_assets.v1', 'esi-corporations.read_blueprints.v1',
                      'esi-industry.read_corporation_jobs.v1']
MOON_SCOPES = ['esi-calendar.read_calendar_events.v1','esi-industry.read_corporation_mining.v1','esi-characters.read_notifications.v1']
MINING_SCOPES=['esi-industry.read_character_mining.v1']
INTEL_SCOPES=['esi-location.read_location.v1','esi-location.read_online.v1']
MARKET_SCOPES=['esi-markets.structure_markets.v1','esi-universe.read_structures.v1','esi-search.search_structures.v1','esi-characters.read_standings.v1']
IMPLANT_SCOPES=['esi-location.read_location.v1','esi-clones.read_implants.v1']
CONTRACT_SCOPES=['esi-contracts.read_character_contracts.v1','esi-contracts.read_corporation_contracts.v1']
ALL_SCOPES = list(dict.fromkeys(SCOPES + CORPORATION_SCOPES + MOON_SCOPES + INTEL_SCOPES + MINING_SCOPES + MARKET_SCOPES + IMPLANT_SCOPES + CONTRACT_SCOPES))
USER_AGENT = 'EveMuhely/0.1 (local personal industry planner)'
COMPATIBILITY = '2026-10-15'


def compatibility_date(now=None):
    # ESI's API day rolls over at 11:00 UTC, not local midnight. Cap our
    # reviewed schema date without automatically opting into future versions.
    current = datetime.now(timezone.utc) if now is None else now
    api_day = (current-timedelta(hours=11)).date().isoformat()
    return min(COMPATIBILITY, api_day)


class EsiError(RuntimeError):
    pass


class AuthenticationError(EsiError):
    pass


class SkillScopeError(AuthenticationError):
    pass


class PlanetScopeError(AuthenticationError):
    pass


class MoonScopeError(AuthenticationError):
    pass


class CorporationScopeError(AuthenticationError):
    pass


class LocationScopeError(AuthenticationError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an authenticated request to a redirect destination.
        raise EsiError('Az EVE szerver váratlan átirányítást küldött.')


class Transport:
    def __init__(self):
        self.opener = urllib.request.build_opener(NoRedirect())
        self.blocked_until = 0

    def request(self, url, token=None, form=None, headers=None, json_body=None):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in ['esi.evetech.net', 'login.eveonline.com'] or parsed.port not in [None, 443]:
            raise EsiError('Nem engedélyezett EVE-végpont.')
        if time.time() < self.blocked_until:
            raise EsiError('Az EVE lekérdezési korlátja miatt később próbáld újra.')
        h = {'User-Agent': USER_AGENT, 'Accept': 'application/json', **(headers or {})}
        if parsed.hostname == 'esi.evetech.net':
            h['X-Compatibility-Date'] = compatibility_date()
        if token:
            h['Authorization'] = 'Bearer '+token
        body = None
        if form is not None and json_body is not None:raise EsiError('Hibás EVE-kérés.')
        if json_body is not None:
            body=json.dumps(json_body,ensure_ascii=False,allow_nan=False).encode('utf-8')
            h['Content-Type']='application/json'
        if form is not None:
            body = urllib.parse.urlencode(form).encode()
            h['Content-Type'] = 'application/x-www-form-urlencoded'
        req = urllib.request.Request(url, data=body, headers=h)
        progress.report(mode='request')
        try:
            with self.opener.open(req, timeout=30) as response:
                payload = response.read(40*1024*1024)
                progress.report(mode='received')
                return json.loads(payload), dict(response.headers)
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                return None, dict(exc.headers)
            if exc.code in [420, 429]:
                retry = exc.headers.get('Retry-After') or exc.headers.get('X-ESI-Error-Limit-Reset') or '60'
                try:
                    self.blocked_until = time.time()+max(1, int(retry))
                except ValueError:
                    self.blocked_until = time.time()+60
            if exc.code in [401, 403]:
                error=AuthenticationError('Az EVE-hozzáférés lejárt vagy nincs jogosultság. Engedélyezd újra a karaktert.')
                error.status_code=exc.code
                raise error from None
            raise EsiError(f'Az EVE szerver HTTP {exc.code} hibát jelzett. A korábbi adatok megmaradtak.') from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            raise EsiError('Az EVE-adatok most nem érhetők el. A korábbi adatok megmaradtak.') from None


def b64decode(value):
    return base64.urlsafe_b64decode(value+'='*((-len(value)) % 4))


def verify_jwt(token, keys, client_id, now=None, required_scopes=None):
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import hashes
    try:
        head, payload, signature = token.split('.')
        header, claims = json.loads(b64decode(head)), json.loads(b64decode(payload))
        if header.get('alg') != 'RS256':
            raise ValueError('algorithm')
        key = next(k for k in keys['keys'] if k.get('kid') == header.get('kid') and k.get('kty') == 'RSA' and k.get('alg', 'RS256') == 'RS256')
        public_key = rsa.RSAPublicNumbers(int.from_bytes(b64decode(key['e']), 'big'),
                                         int.from_bytes(b64decode(key['n']), 'big')).public_key()
        public_key.verify(b64decode(signature), (head+'.'+payload).encode(), padding.PKCS1v15(), hashes.SHA256())
        current = time.time() if now is None else now
        if claims.get('iss') not in ['https://login.eveonline.com', 'https://login.eveonline.com/', 'login.eveonline.com']:
            raise ValueError('issuer')
        aud = claims.get('aud', [])
        if not isinstance(aud, list) or client_id not in aud or 'EVE Online' not in aud:
            raise ValueError('audience')
        if claims.get('exp', 0) <= current or claims.get('nbf', 0) > current+30:
            raise ValueError('expired')
        sub = str(claims.get('sub', '')).split(':')
        if len(sub) != 3 or sub[:2] != ['CHARACTER', 'EVE'] or not sub[2].isdigit():
            raise ValueError('subject')
        granted = claims.get('scp', [])
        if isinstance(granted, str):
            granted = granted.split()
        if not set(INDUSTRY_SCOPES if required_scopes is None else required_scopes).issubset(granted):
            raise ValueError('scopes')
        return claims
    except Exception:
        raise AuthenticationError('Az EVE-belépés aláírása, címzettje vagy jogosultsága nem ellenőrizhető.') from None


class Vault:
    """Encrypted tokens; macOS Keychain or Windows per-user DPAPI protects keys."""
    def __init__(self, folder, key_provider=None):
        self.folder = Path(folder)
        self.path = self.folder/'characters.enc'
        self.key_provider = key_provider
        self.lock = threading.RLock()
        self._cipher = None

    def cipher(self):
        from cryptography.fernet import Fernet
        if self._cipher is not None:
            return self._cipher
        if self.key_provider:
            key = self.key_provider()
        elif sys.platform == 'darwin':
            identity = hashlib.sha256(str(self.folder.resolve()).encode()).hexdigest()[:24]
            service = 'hu.eve.muhely.tokens'
            found = subprocess.run(['/usr/bin/security', 'find-generic-password', '-a', identity,
                                    '-s', service, '-w'], capture_output=True, text=True)
            if found.returncode == 0:
                key = found.stdout.strip().encode()
            else:
                if self.path.exists():
                    raise EsiError('A mentett belépés kulcsa nem érhető el a Kulcskarikában. Engedélyezd a hozzáférést.')
                key = Fernet.generate_key()
                command = 'add-generic-password -U -a '+shlex.quote(identity)+' -s '+shlex.quote(service)+' -w '+shlex.quote(key.decode())+'\n'
                created = subprocess.run(['/usr/bin/security', '-i'], input=command, capture_output=True, text=True)
                # Interactive security may return zero even if a subcommand failed.
                check = subprocess.run(['/usr/bin/security', 'find-generic-password', '-a', identity,
                                        '-s', service, '-w'], capture_output=True, text=True)
                if created.returncode or check.returncode or check.stdout.strip().encode() != key:
                    raise EsiError('A Kulcskarika nem engedte a belépés mentését.')
        elif sys.platform=='win32':
            from .windows_security import vault_key
            try:
                def validate(candidate):
                    cipher=Fernet(candidate)
                    if self.path.exists():cipher.decrypt(self.path.read_bytes())
                key=vault_key(self.folder,Fernet.generate_key,validate)
            except Exception:
                raise EsiError('A Windows nem tudta feloldani vagy biztonságosan menteni az EVE-belépés kulcsát. A korábbi adatok megmaradtak.') from None
        else:
            key_file = self.folder/'vault.key'
            if not key_file.exists():
                with key_file.open('xb') as f:
                    os.chmod(key_file, 0o600)
                    f.write(Fernet.generate_key())
            key = key_file.read_bytes()
        self._cipher = Fernet(key)
        return self._cipher

    def read(self):
        with self.lock:
            if not self.path.exists():
                return {}
            try:
                return json.loads(self.cipher().decrypt(self.path.read_bytes()))
            except EsiError:
                raise
            except Exception:
                raise EsiError('A mentett EVE-belépés nem olvasható; a fájl nem lett felülírva.') from None

    def set(self, char_id, tokens):
        with self.lock:
            records = self.read()
            if tokens is None:
                records.pop(str(char_id), None)
            else:
                records[str(char_id)] = tokens
            payload = self.cipher().encrypt(json.dumps(records).encode())
            temp = self.path.with_suffix('.tmp')
            with temp.open('wb') as stream:
                os.chmod(temp, 0o600)
                stream.write(payload)
            os.replace(temp, self.path)


class EveConnection:
    def __init__(self, store, vault=None, transport=None):
        self.store = store
        self.vault = vault or Vault(store.folder)
        self.http = transport or Transport()
        self.pending = {}
        self.lock = threading.RLock()
        self.keys = None
        self.keys_expires = 0
        self.sync_lock = threading.Lock()
        self.authorized_feature = None

    def jwks(self):
        if self.keys is None or time.time() >= self.keys_expires:
            meta, _ = self.http.request(SSO+'/.well-known/oauth-authorization-server')
            uri = meta['jwks_uri']
            if urllib.parse.urlsplit(uri).hostname != 'login.eveonline.com':
                raise EsiError('Váratlan EVE-aláírási végpont.')
            self.keys, _ = self.http.request(uri)
            self.keys_expires = time.time()+300
        return self.keys

    def start(self, session, redirect, character_id=None, feature=None):
        client = self.store.settings()['client_id'].strip()
        if not client:
            raise EsiError('Előbb add meg az EVE Developer Client ID-t a Kapcsolat oldalon.')
        if len(client) > 200 or not all(c.isalnum() or c in '-_' for c in client):
            raise EsiError('Hibás Client ID.')
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        state = secrets.token_urlsafe(32)
        requested=SCOPES
        if feature == 'all':
            requested=list(dict.fromkeys(ALL_SCOPES))
        elif feature in ['skills','pi','corporations','moons','intel','mining','markets','implants','contracts']:
            existing=self.vault.read().get(str(character_id),{}) if character_id else {}
            wanted=set(INDUSTRY_SCOPES+{'skills':SKILL_SCOPES,'pi':PI_SCOPES,'corporations':CORPORATION_SCOPES,'moons':MOON_SCOPES,'intel':INTEL_SCOPES,'mining':MINING_SCOPES,'markets':MARKET_SCOPES+SKILL_SCOPES,'implants':IMPLANT_SCOPES,'contracts':CONTRACT_SCOPES}[feature])
            wanted.update(set(existing.get('scopes',[])) & set(ALL_SCOPES))
            requested=[scope for scope in ALL_SCOPES if scope in wanted]
        with self.lock:
            self.pending = {k: v for k, v in self.pending.items() if v['expires'] > time.time()}
            self.pending[state] = dict(session=session, verifier=verifier, client=client,
                                       redirect=redirect, expires=time.time()+600, character_id=character_id,scopes=requested,feature=feature)
        return SSO+'/v2/oauth/authorize?'+urllib.parse.urlencode({
            'response_type': 'code', 'client_id': client, 'redirect_uri': redirect,
            'scope': ' '.join(requested), 'state': state, 'code_challenge': challenge,
            'code_challenge_method': 'S256'})

    def finish(self, state, code, session):
        with self.lock:
            pending = self.pending.pop(state, None)
        if not pending or pending['session'] != session or pending['expires'] < time.time():
            raise EsiError('A belépési kérés lejárt vagy nem ebből a böngészőből indult. Próbáld újra.')
        tokens, _ = self.http.request(SSO+'/v2/oauth/token', form={
            'grant_type': 'authorization_code', 'code': code, 'client_id': pending['client'],
            'code_verifier': pending['verifier'], 'redirect_uri': pending['redirect']})
        claims = verify_jwt(tokens['access_token'], self.jwks(), pending['client'], required_scopes=pending['scopes'])
        char_id = int(claims['sub'].split(':')[-1])
        if pending.get('character_id') is not None and char_id != pending['character_id']:
            raise EsiError('Másik karakterrel léptél be. A meglévő belépések megmaradtak; válaszd az engedélyezendő karaktert.')
        tokens.update(client_id=pending['client'], expires_at=claims['exp'], owner=claims.get('owner'),
                      scopes=claims['scp'].split() if isinstance(claims['scp'],str) else claims['scp'])
        if not tokens.get('refresh_token'):
            raise EsiError('Az EVE nem adott megújító tokent.')
        self.vault.set(char_id, tokens)
        self.store.add_character(char_id, claims.get('name', str(char_id)))
        if set(SKILL_SCOPES).issubset(tokens['scopes']):self.store.skill_access_granted(char_id)
        if set(PI_SCOPES).issubset(tokens['scopes']):self.store.resource_access_granted(char_id,'pi')
        if set(CORPORATION_SCOPES).issubset(tokens['scopes']):self.store.resource_access_granted(char_id,'corporations')
        if set(INTEL_SCOPES).issubset(tokens['scopes']):self.store.resource_access_granted(char_id,'intel_location')
        if set(MINING_SCOPES).issubset(tokens['scopes']):self.store.resource_access_granted(char_id,'mining')
        self.authorized_feature=pending.get('feature')
        for domain,scope in [('moon_calendar',MOON_SCOPES[0]),('moon_timers',MOON_SCOPES[1]),('moon_notifications',MOON_SCOPES[2])]:
            if scope in tokens['scopes']:self.store.resource_access_granted(char_id,domain)
        return char_id

    def granted_scopes(self):
        # Read only the verified scope metadata; never expose any token.
        try:
            with self.lock:return {int(cid):[s for s in token.get('scopes',[]) if s in ALL_SCOPES] for cid,token in self.vault.read().items()}
        except EsiError:return {}

    def token(self, char_id, required_scopes=None):
        with self.lock:
            tokens = self.vault.read().get(str(char_id))
            if not tokens:
                raise AuthenticationError('A karakter belépése hiányzik. Engedélyezd újra a karaktert.')
            if tokens['expires_at'] <= time.time()+90:
                fresh, _ = self.http.request(SSO+'/v2/oauth/token', form={
                    'grant_type': 'refresh_token', 'refresh_token': tokens['refresh_token'],
                    'client_id': tokens['client_id']})
                claims = verify_jwt(fresh['access_token'], self.jwks(), tokens['client_id'])
                if claims['sub'] != f'CHARACTER:EVE:{char_id}' or (tokens.get('owner') and claims.get('owner') != tokens['owner']):
                    raise AuthenticationError('A karakter tulajdonosa megváltozott. Add hozzá újra a karaktert.')
                tokens.update(fresh)
                tokens['expires_at'] = claims['exp']
                tokens['scopes'] = claims['scp'].split() if isinstance(claims['scp'],str) else claims['scp']
                self.vault.set(char_id, tokens)
            if required_scopes:
                if 'scopes' not in tokens:
                    claims = verify_jwt(tokens['access_token'], self.jwks(), tokens['client_id'])
                    if claims['sub'] != f'CHARACTER:EVE:{char_id}':
                        raise AuthenticationError('A karakter belépése nem ellenőrizhető.')
                    tokens['scopes'] = claims['scp'].split() if isinstance(claims['scp'],str) else claims['scp']
                    self.vault.set(char_id,tokens)
                if not set(required_scopes).issubset(tokens['scopes']):
                    if set(CONTRACT_SCOPES) & (set(required_scopes)-set(tokens['scopes'])):
                        raise AuthenticationError('Hiányzik a szerződések olvasási engedélye. Engedélyezd újra a szerződéshozzáférést.')
                    if set(MARKET_SCOPES) & (set(required_scopes)-set(tokens['scopes'])):
                        raise AuthenticationError('A market vagy standing olvasási engedélye hiányzik; engedélyezd a Market-hozzáférést.')
                    if set(MINING_SCOPES) & (set(required_scopes)-set(tokens['scopes'])):
                        raise AuthenticationError('A bányászati napló olvasási engedélye hiányzik. Engedélyezd a Mining ledger hozzáférését.')
                    if set(INTEL_SCOPES) & (set(required_scopes)-set(tokens['scopes'])):
                        raise LocationScopeError('Hiányzik a helyzet- és onlineadatok olvasási engedélye. Engedélyezd az intelhelyzet követését.')
                    if MOON_SCOPES[2] in set(required_scopes)-set(tokens['scopes']):
                        raise MoonScopeError('Hiányzik a karakterértesítések olvasási engedélye. Engedélyezd a holdadatok új értesítési hozzáférését.')
                    if set(MOON_SCOPES) & (set(required_scopes)-set(tokens['scopes'])):
                        raise MoonScopeError('Hiányzik a naptár vagy a corporation holdkitermelési engedélye. Engedélyezd a holdadatok olvasását.')
                    if set(CORPORATION_SCOPES) & (set(required_scopes)-set(tokens['scopes'])):
                        raise CorporationScopeError('Hiányzik a corporation készlet-, blueprint- és jobadatok olvasási engedélye. Engedélyezd a karakter corp-hozzáférését.')
                    if set(PI_SCOPES) & (set(required_scopes)-set(tokens['scopes'])):
                        raise PlanetScopeError('Hiányzik a bolygóadatok olvasási engedélye (esi-planets.manage_planets.v1). Engedélyezd újra a karakter PI-hozzáférését.')
                    raise SkillScopeError('Hiányzik a skillek és a tanulási sor olvasási engedélye. Engedélyezd újra ezt a karaktert a két új skilljogosultsággal.')
            return tokens['access_token']

    def skill_resource(self, char_id, kind, token):
        from .skills import validate_resource
        import re
        if kind not in ['skills','skillqueue']:
            raise EsiError('Ismeretlen skilladat.')
        old=self.store.snapshot(char_id,kind);now=time.time()
        progress.resource({'skills':'Skillek','skillqueue':'Tanulási sor'}.get(kind,kind),bool(old and old['expires']>now))
        if old and old['expires']>now:
            return old
        headers={'If-None-Match':old['etag']} if old and old.get('etag') else {}
        body,h=self.http.request(f'{ESI}/characters/{char_id}/{kind}',token=token,headers=headers)
        h={key.lower():value for key,value in h.items()}
        cache=h.get('cache-control','').lower();match=re.search(r'(?:^|,)\s*max-age\s*=\s*"?(\d+)',cache)
        try:age=max(0,int(h.get('age','0')))
        except (ValueError,TypeError):age=0
        ttl=max(0,min(60,int(match.group(1))-age)) if match else 60
        if 'no-cache' in cache or 'no-store' in cache:ttl=0
        if body is None:
            if not old:raise EsiError('Az EVE üres skillválaszt adott korábbi adat nélkül.')
            body=old['data']
        validate_resource(kind,body)
        return {'data':body,'fetched':now,'expires':now+ttl,'etag':h.get('etag') or (old or {}).get('etag')}

    def sync_skills(self):
        if not self.sync_lock.acquire(blocking=False):
            raise EsiError('Az EVE-frissítés már folyamatban van.')
        try:
            result=[]
            # Skill monitoring always includes every connected character,
            # independent of production/location filters.
            for char in progress.items(self.store.characters()):
                try:
                    token=self.token(char['id'],required_scopes=SKILL_SCOPES)
                    parts={kind:self.skill_resource(char['id'],kind,token) for kind in ['skills','skillqueue']}
                    self.store.save_snapshots(char['id'],parts,domain='skills')
                    result.append({'id':char['id'],'ok':True})
                except EsiError as error:
                    self.store.resource_error(char['id'],'skills',str(error),isinstance(error,AuthenticationError))
                    result.append({'id':char['id'],'ok':False,'error':str(error)})
            return result
        finally:
            self.sync_lock.release()

    def pi_resource(self,char_id,kind,url,token):
        from .pi import validate_planets,validate_layout
        old=self.store.snapshot(char_id,kind);now=time.time()
        progress.resource('PI-bolygók listája' if kind=='pi_planets' else 'PI-kolónia: '+kind.split(':')[-1],bool(old and old['expires']>now))
        if old and old['expires']>now:return old
        headers={'If-None-Match':old['etag']} if old and old.get('etag') else {}
        body,h=self.http.request(url,token=token,headers=headers)
        h={key.lower():value for key,value in h.items()}
        import re
        match=re.search(r'(?:^|,)\s*max-age\s*=\s*"?(\d+)',h.get('cache-control','').lower())
        try:age=max(0,int(h.get('age','0')))
        except (ValueError,TypeError):age=0
        ttl=max(0,min(600,int(match.group(1))-age)) if match else 600
        if any(v in h.get('cache-control','').lower() for v in ['no-cache','no-store']):ttl=0
        if body is None:
            if not old:raise EsiError('Az EVE PI-válasza üres, és nincs korábbi adat.')
            body=old['data']
        (validate_planets if kind=='pi_planets' else validate_layout)(body)
        return {'data':body,'fetched':now,'expires':now+ttl,'etag':h.get('etag') or (old or {}).get('etag')}

    def sync_pi(self):
        if not self.sync_lock.acquire(blocking=False):raise EsiError('Az EVE-frissítés már folyamatban van.')
        try:
            results=[]
            for char in progress.items(self.store.characters()):
                try:
                    token=self.token(char['id'],required_scopes=PI_SCOPES)
                    base=f"{ESI}/characters/{char['id']}/planets"
                    listing=self.pi_resource(char['id'],'pi_planets',base,token)
                    parts={'pi_planets':listing};colonies=[]
                    for planet in listing['data']:
                        if planet['owner_id']!=char['id']:raise EsiError('A bolygó tulajdonosa nem egyezik a lekért karakterrel.')
                        key='pi_planet:'+str(planet['planet_id'])
                        layout=self.pi_resource(char['id'],key,base+'/'+str(planet['planet_id']),token)
                        parts[key]=layout
                        colonies.append({'planet':planet,'layout':layout['data'],'layout_checked_at':layout['fetched']})
                    parts['pi']={'data':{'colonies':colonies},'fetched':time.time(),
                                 'expires':min(p['expires'] for p in parts.values()),'etag':None}
                    self.store.save_snapshots(char['id'],parts,domain='pi')
                    results.append({'id':char['id'],'ok':True})
                except EsiError as error:
                    self.store.resource_error(char['id'],'pi',str(error),isinstance(error,AuthenticationError))
                    results.append({'id':char['id'],'ok':False,'error':str(error)})
            return results
        finally:self.sync_lock.release()

    @staticmethod
    def expiry(headers):
        try:
            return parsedate_to_datetime(headers['Expires']).timestamp()
        except (KeyError, ValueError, TypeError):
            return time.time()+300

    def resource(self, char_id, kind, token):
        old = self.store.snapshot(char_id, kind)
        now = time.time()
        progress.resource({'assets':'Készlet','blueprints':'Blueprintok','jobs':'Ipari jobok'}[kind],bool(old and old['expires']>now))
        if old and old['expires'] > now:
            return old
        suffix = {'assets': 'assets/', 'blueprints': 'blueprints/', 'jobs': 'industry/jobs/?include_completed=true'}[kind]
        url = f'{ESI}/characters/{char_id}/{suffix}'
        result, dates, pages, expires = [], [], 1, []
        for page in range(1, 1001):
            progress.report(page=page,pages=pages if page>1 else None)
            page_url = url+('&' if '?' in url else '?')+'page='+str(page)
            # Validate every page's snapshot date. Never bypass ESI's cache.
            body, h = self.http.request(page_url, token=token)
            if not isinstance(body, list):
                raise EsiError('Az EVE váratlan adatot adott; az előző készlet megmaradt.')
            result.extend(body)
            dates.append(h.get('Last-Modified'))
            expires.append(self.expiry(h))
            pages = int(h.get('X-Pages', '1'))
            progress.report(page=page,pages=pages)
            if pages > 1000:
                raise EsiError('Az EVE több mint 1000 adatoldalt jelzett.')
            if page >= pages:
                break
        if len(set(dates)) > 1:
            raise EsiError('Az EVE-adatok lapozás közben megváltoztak. Próbáld újra később.')
        try:
            as_of = parsedate_to_datetime(dates[0]).timestamp() if dates[0] else now
        except (TypeError, ValueError):
            as_of = now
        return {'data': result, 'fetched': as_of, 'expires': min(expires), 'etag': None}

    def sync(self):
        if not self.sync_lock.acquire(blocking=False):
            raise EsiError('Az EVE-frissítés már folyamatban van.')
        try:
            result = []
            for char in progress.items(self.store.characters()):
                try:
                    token = self.token(char['id'])
                    parts = {}
                    for kind, label in [('assets', 'Készlet'), ('blueprints', 'Blueprintok'), ('jobs', 'Ipari jobok')]:
                        try:
                            parts[kind] = self.resource(char['id'], kind, token)
                        except EsiError as error:
                            raise EsiError(label+': '+str(error)) from None
                    self.store.save_snapshots(char['id'], parts)
                    result.append({'id': char['id'], 'ok': True})
                except EsiError as error:
                    self.store.character_error(char['id'], str(error))
                    result.append({'id': char['id'], 'ok': False, 'error': str(error)})
            return result
        finally:
            self.sync_lock.release()

    def corporation_resource(self, corporation_id, kind, token):
        if not self.store.corporation_monitored(corporation_id):raise EsiError('Ennek a corporationnek a figyelése ki van kapcsolva.')
        from .corporations import validate_resource
        old=self.store.corporation_snapshot(corporation_id,kind);now=time.time()
        progress.resource({'assets':'Corp-készlet','blueprints':'Corp-blueprintek','jobs':'Corp-jobok'}[kind],bool(old and old['expires']>now))
        if old and old['expires']>now:return old
        suffix={'assets':'assets','blueprints':'blueprints','jobs':'industry/jobs?include_completed=true'}[kind]
        url=f'{ESI}/corporations/{corporation_id}/{suffix}'
        result=[];dates=[];expiry=[]
        for page in range(1,1001):
            progress.report(page=page,pages=pages if page>1 else None)
            body,headers=self.http.request(url+('&' if '?' in url else '?')+'page='+str(page),token=token)
            h={k.lower():v for k,v in headers.items()}
            validate_resource(kind,body);result.extend(body);dates.append(h.get('last-modified'))
            import re
            match=re.search(r'(?:^|,)\s*max-age\s*=\s*"?(\d+)',h.get('cache-control','').lower())
            try:age=max(0,int(h.get('age','0')))
            except (ValueError,TypeError):age=0
            expires=min(self.expiry({'Expires':h['expires']}) if h.get('expires') else now+300,
                        now+max(0,int(match.group(1))-age) if match else now+3600)
            if any(v in h.get('cache-control','').lower() for v in ['no-store','no-cache']):expires=now
            expiry.append(expires)
            try:pages=int(h.get('x-pages','1'))
            except (TypeError,ValueError):raise EsiError('Hibás corp adatlapozás.') from None
            if not 1<=pages<=1000:raise EsiError('Túl sok corp adatoldal.')
            progress.report(page=page,pages=pages)
            if page>=pages:break
        if len(set(dates))>1:raise EsiError('A corporation adatai lapozás közben megváltoztak. Frissíts később.')
        try:as_of=parsedate_to_datetime(dates[0]).timestamp() if dates[0] else now
        except (ValueError,TypeError):as_of=now
        return {'data':result,'fetched':as_of,'expires':min(expiry),'etag':None}

    def sync_corporations(self):
        """Read once per corporation, trying other connected members on failure."""
        from .corporations import positive_id
        if not self.sync_lock.acquire(blocking=False):raise EsiError('Az EVE-frissítés már folyamatban van.')
        try:
            groups={};names={};results=[]
            for char in progress.items(self.store.characters()):
                if not self.store.corporation_monitored(char.get('corporation_id')):continue
                try:
                    profile,_=self.http.request(f"{ESI}/characters/{char['id']}")
                    cid=positive_id(profile.get('corporation_id')) if isinstance(profile,dict) else None
                    if cid is None:raise EsiError('A karakter corporation tagsága nem ellenőrizhető.')
                    if not self.store.corporation_monitored(cid):continue
                    if cid not in names:
                        details,_=self.http.request(f'{ESI}/corporations/{cid}')
                        if not isinstance(details,dict) or not isinstance(details.get('name'),str) or not details['name']:
                            raise EsiError('A corporation neve nem ellenőrizhető.')
                        names[cid]=details['name']
                    self.store.character_corporation(char['id'],cid,names[cid])
                    groups.setdefault(cid,[]).append(char)
                except EsiError as error:
                    self.store.resource_error(char['id'],'corporations',str(error),False)
                    if char.get('corporation_id'):self.store.corporation_error(char['corporation_id'],str(error))
                    results.append({'id':char['id'],'ok':False,'error':str(error)})
            for cid,chars in progress.items(groups.items(),name=lambda row:names[row[0]]):
                if not self.store.corporation_monitored(cid):continue
                success=False;failures=[]
                for char in chars:
                    try:
                        progress.report(subject=names[cid]+' · '+char['name'],resource='Hozzáférés ellenőrzése',mode='checking',page=None,pages=None)
                        token=self.token(char['id'],required_scopes=CORPORATION_SCOPES)
                        # Recheck membership before using a cached snapshot.
                        roles,_=self.http.request(f"{ESI}/characters/{char['id']}")
                        if not isinstance(roles,dict) or roles.get('corporation_id')!=cid:
                            raise EsiError('A karakter corporation tagsága megváltozott; frissítsd újra a corp adatokat.')
                        parts={}
                        for kind in ['assets','blueprints','jobs']:
                            try:parts[kind]=self.corporation_resource(cid,kind,token)
                            except AuthenticationError:
                                raise EsiError('A corp készlethez és blueprintekhez Director, a jobokhoz Factory Manager szerepkör szükséges. Ellenőrizd az EVE-jogosultságokat.') from None
                        self.store.save_corporation_snapshots(cid,char['id'],parts)
                        self.store.resource_access_granted(char['id'],'corporations')
                        results.append({'id':cid,'corporation_id':cid,'ok':True});success=True;break
                    except EsiError as error:
                        failures.append(str(error))
                        self.store.resource_error(char['id'],'corporations',str(error),isinstance(error,AuthenticationError))
                if not success:
                    message=failures[-1] if failures else 'Nincs megfelelő corp-hozzáférés.'
                    self.store.corporation_error(cid,message)
                    results.append({'id':cid,'corporation_id':cid,'ok':False,'error':message})
            return results
        finally:self.sync_lock.release()

    def forget(self, char_id):
        self.vault.set(char_id, None)
        self.store.forget_character(char_id)
