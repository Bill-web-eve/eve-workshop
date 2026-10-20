from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import sys
import time


BUNDLED_DEFAULTS = Path(__file__).resolve().parent.parent/'data/defaults.json'


def bundled_defaults():
    if not BUNDLED_DEFAULTS.exists():return {}
    value=json.loads(BUNDLED_DEFAULTS.read_text(encoding='utf-8')).get('client_id','')
    if not isinstance(value,str) or len(value)>200 or (value and not all(c.isalnum() or c in '-_' for c in value)):
        raise ValueError('Hibás előre beállított EVE Client ID.')
    # A distributable may only seed the public application identifier.
    return {'client_id':value}


DEFAULT_SETTINGS = {
    'source': 'manual', 'source_explicit': False,
    'character_ids': [], 'location_ids': [], 'client_id': '',
    'corporation_locations': {},
    'manufacturing': {'material_role': 1, 'material_rig': 4.2,
                      'time_role': 30, 'time_rig': 42, 'skill_time': 1, 'system_id':None,
                      'facility_tax':2.5,'job_cost_role':5,'scc_surcharge':4,'alpha_surcharge':0},
    'reaction': {'material_role': 0, 'material_rig': 2.6,
                 'time_role': 25, 'time_rig': 26.4, 'skill_time': 1,'system_id':None,
                 'facility_tax':2.5,'job_cost_role':0,'scc_surcharge':4,'alpha_surcharge':0},
}


def default_data_dir():
    if os.environ.get('EVE_MUHELY_DATA'):
        return Path(os.environ['EVE_MUHELY_DATA']).expanduser()
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/EVE Muhely'
    if sys.platform == 'win32':
        return Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData/Local')/'EVE Muhely'
    return Path.home() / '.local/share/eve-muhely'


class Store:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.folder / 'muhely.sqlite3'
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS mining_ledger(character_id INTEGER NOT NULL,date TEXT NOT NULL,
                    solar_system_id INTEGER NOT NULL,type_id INTEGER NOT NULL,quantity INTEGER NOT NULL,
                    fetched REAL NOT NULL,PRIMARY KEY(character_id,date,solar_system_id,type_id));
                CREATE TABLE IF NOT EXISTS market_quotes(type_id INTEGER PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS moons(id TEXT PRIMARY KEY,moon_id INTEGER UNIQUE NOT NULL,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS moon_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS universe_cache(kind TEXT,id INTEGER,data TEXT NOT NULL,
                    fetched REAL NOT NULL,etag TEXT,PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS inventory(type_id INTEGER PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS parameters(type_id INTEGER PRIMARY KEY,data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS characters(id INTEGER PRIMARY KEY,name TEXT NOT NULL,
                    synced_at REAL,error TEXT);
                CREATE TABLE IF NOT EXISTS snapshots(character_id INTEGER,kind TEXT,data TEXT,
                    fetched REAL,expires REAL,etag TEXT,PRIMARY KEY(character_id,kind));
                CREATE TABLE IF NOT EXISTS resource_status(character_id INTEGER,kind TEXT,
                    checked_at REAL,error TEXT,needs_auth INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(character_id,kind));
                CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY,name TEXT NOT NULL,
                    product_id INTEGER NOT NULL,quantity INTEGER NOT NULL,created REAL NOT NULL,
                    saved_inputs TEXT);
                CREATE TABLE IF NOT EXISTS corporations(id INTEGER PRIMARY KEY,name TEXT NOT NULL,
                    provider_id INTEGER,synced_at REAL,error TEXT);
                CREATE TABLE IF NOT EXISTS corporation_snapshots(corporation_id INTEGER,kind TEXT,data TEXT,
                    fetched REAL,expires REAL,etag TEXT,PRIMARY KEY(corporation_id,kind));
                CREATE TABLE IF NOT EXISTS corporation_mapping(corporation_id INTEGER,kind TEXT,type_id INTEGER,
                    data TEXT,PRIMARY KEY(corporation_id,kind,type_id));
            ''')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(plans)')}
            if 'reserve_active' not in columns:
                db.execute('ALTER TABLE plans ADD COLUMN reserve_active INTEGER NOT NULL DEFAULT 0')
            if 'reserved_at' not in columns:
                db.execute('ALTER TABLE plans ADD COLUMN reserved_at REAL')
            if 'corporation_id' not in columns:
                db.execute('ALTER TABLE plans ADD COLUMN corporation_id INTEGER')
            if 'manufacturer_id' not in columns:
                db.execute('ALTER TABLE plans ADD COLUMN manufacturer_id INTEGER')
            if 'corporation_id' not in {r['name'] for r in db.execute('PRAGMA table_info(characters)')}:
                db.execute('ALTER TABLE characters ADD COLUMN corporation_id INTEGER')
        self.path.chmod(0o600)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def settings(self):
        result = json.loads(json.dumps(DEFAULT_SETTINGS))
        result.update(bundled_defaults())
        with self.db() as db:
            for r in db.execute('SELECT * FROM settings'):
                value=json.loads(r['value'])
                result[r['key']] = {**result[r['key']],**value} if r['key'] in ['manufacturing','reaction'] and isinstance(value,dict) else value
        return result

    def save_settings(self, settings):
        with self.db() as db:
            db.executemany('INSERT OR REPLACE INTO settings VALUES (?,?)',
                           ((k, json.dumps(v)) for k, v in settings.items()))

    def enable_eve_after_sync(self):
        # Activate imported stock after the first successful connection, while
        # preserving any source deliberately chosen by the user.
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = dict(db.execute("SELECT key,value FROM settings WHERE key IN ('source','source_explicit')"))
            if json.loads(rows.get('source_explicit', 'false')) or json.loads(rows.get('source', '"manual"')) == 'eve':
                return False
            db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', ('source', '"eve"'))
            return True

    def mapping(self, table, corporation_id=None):
        assert table in ['inventory', 'parameters']
        with self.db() as db:
            if corporation_id is not None:
                return {r['type_id']:json.loads(r['data']) for r in db.execute(
                    'SELECT type_id,data FROM corporation_mapping WHERE corporation_id=? AND kind=?',(corporation_id,table))}
            return {r['type_id']: json.loads(r['data']) for r in db.execute('SELECT * FROM '+table)}

    def plans(self):
        with self.db() as db:
            return [{**dict(row), 'reserve_active': bool(row['reserve_active'])} for row in db.execute(
                'SELECT id,name,product_id,quantity,created,reserve_active,reserved_at,corporation_id,manufacturer_id FROM plans ORDER BY created DESC,id')]

    def save_plan(self, plan):
        with self.db() as db:
            db.execute('''INSERT INTO plans(id,name,product_id,quantity,created,reserve_active,reserved_at,corporation_id,manufacturer_id)
                       VALUES (:id,:name,:product_id,:quantity,:created,:reserve_active,:reserved_at,:corporation_id,:manufacturer_id)
                       ON CONFLICT(id) DO UPDATE SET name=excluded.name,product_id=excluded.product_id,
                       quantity=excluded.quantity,reserve_active=excluded.reserve_active,reserved_at=excluded.reserved_at,
                       manufacturer_id=excluded.manufacturer_id''', {'corporation_id':None,'manufacturer_id':None,**plan})

    def remove_plan(self, plan_id):
        with self.db() as db:
            db.execute('DELETE FROM plans WHERE id=?', (plan_id,))

    def save_mapping(self, table, rows, corporation_id=None):
        assert table in ['inventory', 'parameters']
        with self.db() as db:
            for type_id, data in rows.items():
                if corporation_id is not None:
                    if data:db.execute('INSERT OR REPLACE INTO corporation_mapping VALUES (?,?,?,?)',
                                       (corporation_id,table,int(type_id),json.dumps(data)))
                    else:db.execute('DELETE FROM corporation_mapping WHERE corporation_id=? AND kind=? AND type_id=?',
                                    (corporation_id,table,int(type_id)))
                    continue
                if data:
                    db.execute(f'INSERT OR REPLACE INTO {table} VALUES (?,?)', (int(type_id), json.dumps(data)))
                else:
                    db.execute(f'DELETE FROM {table} WHERE type_id=?', (int(type_id),))

    def characters(self):
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT * FROM characters ORDER BY name')]

    def add_character(self, char_id, name):
        with self.db() as db:
            db.execute('''INSERT INTO characters(id,name) VALUES (?,?)
                       ON CONFLICT(id) DO UPDATE SET name=excluded.name,error=NULL''', (char_id, name))

    def forget_character(self, char_id):
        with self.db() as db:
            db.execute('DELETE FROM snapshots WHERE character_id=?', (char_id,))
            db.execute('DELETE FROM resource_status WHERE character_id=?', (char_id,))
            db.execute('DELETE FROM mining_ledger WHERE character_id=?', (char_id,))
            db.execute('DELETE FROM characters WHERE id=?', (char_id,))

    def snapshot(self, char_id, kind):
        with self.db() as db:
            row = db.execute('SELECT * FROM snapshots WHERE character_id=? AND kind=?', (char_id, kind)).fetchone()
            return None if row is None else {**dict(row), 'data': json.loads(row['data'])}

    def save_snapshots(self, char_id, snapshots, domain='industry'):
        # A failed page/resource never leaves a half-updated character snapshot.
        with self.db() as db:
            for kind, item in snapshots.items():
                db.execute('INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?)',
                           (char_id, kind, json.dumps(item['data']), item['fetched'], item['expires'], item.get('etag')))
            if domain == 'industry':
                db.execute('UPDATE characters SET synced_at=?,error=NULL WHERE id=?', (time.time(), char_id))
            else:
                db.execute('INSERT OR REPLACE INTO resource_status VALUES (?,?,?,?,?)',
                           (char_id, domain, time.time(), None, 0))

    def save_mining(self, char_id, snapshot):
        with self.db() as db:
            db.executemany('INSERT INTO mining_ledger VALUES (?,?,?,?,?,?) ON CONFLICT(character_id,date,solar_system_id,type_id) DO UPDATE SET quantity=excluded.quantity,fetched=excluded.fetched',
                ((char_id,r['date'],r['solar_system_id'],r['type_id'],r['quantity'],snapshot['fetched']) for r in snapshot['data']))
            db.execute('INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?)',
                (char_id,'mining',json.dumps(snapshot['data']),snapshot['fetched'],snapshot['expires'],None))
            db.execute('INSERT OR REPLACE INTO resource_status VALUES (?,?,?,?,?)',(char_id,'mining',time.time(),None,0))

    def resource_status(self, char_id, kind):
        with self.db() as db:
            row=db.execute('SELECT * FROM resource_status WHERE character_id=? AND kind=?',(char_id,kind)).fetchone()
            return dict(row) if row else None

    def skill_records(self):
        # Read skills, queue and status from the same database revision while a
        # background sync may be committing a new pair of resources.
        with self.db() as db:
            db.execute('BEGIN')
            characters=[dict(r) for r in db.execute('SELECT * FROM characters ORDER BY name')]
            snapshots={(r['character_id'],r['kind']):{**dict(r),'data':json.loads(r['data'])}
                       for r in db.execute("SELECT * FROM snapshots WHERE kind IN ('skills','skillqueue')")}
            statuses={r['character_id']:dict(r) for r in db.execute("SELECT * FROM resource_status WHERE kind='skills'")}
            return [(c,snapshots.get((c['id'],'skills')),snapshots.get((c['id'],'skillqueue')),statuses.get(c['id']))
                    for c in characters]

    def resource_error(self, char_id, kind, message, needs_auth=False):
        with self.db() as db:
            db.execute('INSERT OR REPLACE INTO resource_status VALUES (?,?,?,?,?)',
                       (char_id,kind,time.time(),message,int(needs_auth)))

    def skill_access_granted(self, char_id):
        self.resource_access_granted(char_id,'skills')

    def resource_access_granted(self,char_id,domain):
        with self.db() as db:
            db.execute('INSERT OR REPLACE INTO resource_status VALUES (?,?,NULL,NULL,0)',(char_id,domain))

    def pi_records(self):
        with self.db() as db:
            db.execute('BEGIN')
            characters=[dict(r) for r in db.execute('SELECT * FROM characters ORDER BY name')]
            snapshots={r['character_id']:{**dict(r),'data':json.loads(r['data'])}
                       for r in db.execute("SELECT * FROM snapshots WHERE kind='pi'")}
            statuses={r['character_id']:dict(r) for r in db.execute("SELECT * FROM resource_status WHERE kind='pi'")}
            return [(c,snapshots.get(c['id']),statuses.get(c['id'])) for c in characters]

    def character_error(self, char_id, message):
        with self.db() as db:
            db.execute('UPDATE characters SET error=? WHERE id=?', (message, char_id))

    def corporation(self, corporation_id):
        with self.db() as db:
            row=db.execute('SELECT * FROM corporations WHERE id=?',(corporation_id,)).fetchone()
            return dict(row) if row else None

    def corporations(self):
        with self.db() as db:
            return [dict(r) for r in db.execute('SELECT * FROM corporations ORDER BY name,id')]

    def character_corporation(self, char_id, corporation_id, name):
        with self.db() as db:
            db.execute('INSERT INTO corporations(id,name) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name',
                       (corporation_id,name))
            db.execute('UPDATE characters SET corporation_id=? WHERE id=?',(corporation_id,char_id))

    def corporation_snapshot(self, corporation_id, kind):
        with self.db() as db:
            row=db.execute('SELECT * FROM corporation_snapshots WHERE corporation_id=? AND kind=?',(corporation_id,kind)).fetchone()
            return {**dict(row),'data':json.loads(row['data'])} if row else None

    def corporation_record(self, corporation_id):
        # A concurrent refresh cannot pair old assets with new job outputs.
        with self.db() as db:
            db.execute('BEGIN')
            row=db.execute('SELECT * FROM corporations WHERE id=?',(corporation_id,)).fetchone()
            members=[dict(r) for r in db.execute('SELECT * FROM characters WHERE corporation_id=?',(corporation_id,))]
            parts={r['kind']:{**dict(r),'data':json.loads(r['data'])} for r in db.execute(
                "SELECT * FROM corporation_snapshots WHERE corporation_id=? AND kind IN ('assets','blueprints','jobs')",(corporation_id,))}
            return (dict(row) if row else None),members,{k:parts.get(k) for k in ['assets','blueprints','jobs']}

    def save_corporation_snapshots(self, corporation_id, provider_id, parts):
        with self.db() as db:
            for kind,item in parts.items():
                db.execute('INSERT OR REPLACE INTO corporation_snapshots VALUES (?,?,?,?,?,?)',
                           (corporation_id,kind,json.dumps(item['data']),item['fetched'],item['expires'],item.get('etag')))
            db.execute('UPDATE corporations SET provider_id=?,synced_at=?,error=NULL WHERE id=?',
                       (provider_id,time.time(),corporation_id))

    def corporation_error(self, corporation_id, message):
        with self.db() as db:
            db.execute('UPDATE corporations SET error=? WHERE id=?',(message,corporation_id))

    def moon_records(self):
        with self.db() as db:
            return [json.loads(r['data']) for r in db.execute('SELECT data FROM moons ORDER BY moon_id')]

    def save_moon(self, value):
        with self.db() as db:
            other=db.execute('SELECT id FROM moons WHERE moon_id=?',(value['moon_id'],)).fetchone()
            if other and other['id']!=value['id']:
                from .planner import PlanningError
                raise PlanningError('Ez a hold már szerepel a nyilvántartásban.')
            db.execute('INSERT INTO moons VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET moon_id=excluded.moon_id,data=excluded.data',
                       (value['id'],value['moon_id'],json.dumps(value)))

    def remove_moon(self, value):
        with self.db() as db:db.execute('DELETE FROM moons WHERE id=?',(value,))

    def moon_preferences(self):
        with self.db() as db:return {r['key']:json.loads(r['value']) for r in db.execute('SELECT * FROM moon_settings')}

    def save_moon_preferences(self, value):
        with self.db() as db:db.executemany('INSERT OR REPLACE INTO moon_settings VALUES (?,?)',
            ((k,json.dumps(v)) for k,v in value.items()))

    def universe_cached(self, kind, item_id):
        with self.db() as db:
            row=db.execute('SELECT * FROM universe_cache WHERE kind=? AND id=?',(kind,item_id)).fetchone()
            return {**dict(row),'data':json.loads(row['data'])} if row else None

    def save_universe_cache(self, kind, item_id, data, fetched, etag=None):
        with self.db() as db:db.execute('INSERT OR REPLACE INTO universe_cache VALUES (?,?,?,?,?)',
                                       (kind,item_id,json.dumps(data),fetched,etag))

    def market_quote(self, tid):
        with self.db() as db:
            row=db.execute('SELECT data FROM market_quotes WHERE type_id=?',(tid,)).fetchone()
            return json.loads(row['data']) if row else None

    def save_market_quote(self, tid, data):
        with self.db() as db:db.execute('INSERT OR REPLACE INTO market_quotes VALUES (?,?)',(tid,json.dumps(data)))
