from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import threading
import unicodedata
import zipfile
from contextlib import closing


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text)).casefold()
                   if not unicodedata.combining(c))


def import_sde(archive_path, target):
    """Build a small, replaceable catalogue from the official JSONL export."""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix('.building.sqlite3')
    temp.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(archive_path) as archive, closing(sqlite3.connect(temp)) as db:
            db.executescript('''
                CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE types(id INTEGER PRIMARY KEY,name TEXT NOT NULL,search TEXT NOT NULL,
                    group_id INTEGER,published INTEGER NOT NULL,pi INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE recipes(product_id INTEGER PRIMARY KEY,bp_id INTEGER NOT NULL,
                    activity TEXT NOT NULL,output INTEGER NOT NULL,seconds INTEGER NOT NULL,
                    copy_limit INTEGER NOT NULL,materials TEXT NOT NULL,skills TEXT NOT NULL DEFAULT '[]');
                CREATE INDEX recipe_bp ON recipes(bp_id);
                CREATE INDEX type_search ON types(search);
                CREATE TABLE pi_schematics(id INTEGER PRIMARY KEY,name TEXT NOT NULL,cycle_time INTEGER NOT NULL,
                    inputs TEXT NOT NULL,outputs TEXT NOT NULL,pins TEXT NOT NULL);
                CREATE TABLE pi_types(id INTEGER PRIMARY KEY,group_id INTEGER,capacity REAL,volume REAL);
                CREATE TABLE pi_planets(id INTEGER PRIMARY KEY,name TEXT,system_id INTEGER,type_id INTEGER);
                CREATE TABLE pi_systems(id INTEGER PRIMARY KEY,name TEXT NOT NULL);
            ''')
            def rows(file):
                with archive.open(file) as stream:
                    for line in stream:
                        if line.strip():
                            yield json.loads(line)
            meta = next(r for r in rows('_sde.jsonl') if r['_key'] == 'sde')
            db.executemany('INSERT INTO meta VALUES (?,?)',
                           [(key, str(meta[key])) for key in ['buildNumber', 'releaseDate']])
            db.executemany('INSERT INTO types(id,name,search,group_id,published) VALUES (?,?,?,?,?)',
                           ((r['_key'], r.get('name', {}).get('en', str(r['_key'])),
                             normalize(r.get('name', {}).get('en', str(r['_key']))),
                             r.get('groupID'), int(r.get('published', False))) for r in rows('types.jsonl')))
            if 'planetSchematics.jsonl' in archive.namelist():
                schematics=list(rows('planetSchematics.jsonl'))
                pi = {int(v['_key']) for r in schematics
                      for v in r.get('types', []) if not v.get('isInput', True)}
                db.executemany('UPDATE types SET pi=1 WHERE id=?', ((v,) for v in pi))
                db.executemany('INSERT INTO pi_schematics VALUES (?,?,?,?,?,?)',
                    ((r['_key'],r['name']['en'],r['cycleTime'],
                      json.dumps({v['_key']:v['quantity'] for v in r['types'] if v.get('isInput',True)}),
                      json.dumps({v['_key']:v['quantity'] for v in r['types'] if not v.get('isInput',True)}),
                      json.dumps(r['pins'])) for r in schematics))
                pi_ids={v['_key'] for r in schematics for v in r['types']}
                db.executemany('INSERT INTO pi_types VALUES (?,?,?,?)',
                    ((r['_key'],r.get('groupID'),r.get('capacity'),r.get('volume')) for r in rows('types.jsonl')
                     if r['_key'] in pi_ids or r.get('groupID') in [1027,1028,1029,1030,1063]))
                systems={r['_key']:r['name']['en'] for r in rows('mapSolarSystems.jsonl')}
                db.executemany('INSERT INTO pi_systems VALUES (?,?)',systems.items())
                def roman(number):
                    value=''
                    for n,symbol in [(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
                        while number>=n:value+=symbol;number-=n
                    return value
                def planet_name(r):
                    given=r.get('name')
                    return (given.get('en') if isinstance(given,dict) else given) or \
                           (systems.get(r['solarSystemID'],str(r['solarSystemID']))+' '+roman(r.get('celestialIndex',0)))
                db.executemany('INSERT INTO pi_planets VALUES (?,?,?,?)',
                    ((r['_key'],planet_name(r),r['solarSystemID'],r['typeID']) for r in rows('mapPlanets.jsonl')))
            duplicate_count = 0
            for r in rows('blueprints.jsonl'):
                blueprint = db.execute('SELECT published FROM types WHERE id=?', (r['blueprintTypeID'],)).fetchone()
                if not blueprint or not blueprint[0]:
                    continue
                for activity in ['manufacturing', 'reaction']:
                    a = r.get('activities', {}).get(activity, {})
                    if not a.get('materials') or len(a.get('products', [])) != 1:
                        continue
                    for product in a.get('products', []):
                        existing = db.execute('SELECT 1 FROM recipes WHERE product_id=?',
                                              (product['typeID'],)).fetchone()
                        if existing:
                            duplicate_count += 1
                            continue
                        db.execute('INSERT INTO recipes VALUES (?,?,?,?,?,?,?,?)',
                                   (product['typeID'], r['blueprintTypeID'], activity,
                                    product['quantity'], a.get('time', 0), r.get('maxProductionLimit', 1),
                                    json.dumps(a.get('materials', []), separators=(',', ':')),
                                    json.dumps(a.get('skills', []), separators=(',', ':'))))
            bonuses={}
            if 'typeDogma.jsonl' in archive.namelist():
                for r in rows('typeDogma.jsonl'):
                    attributes={a['attributeID']:a['value'] for a in r.get('dogmaAttributes',[])}
                    if 1982 in attributes:bonuses[r['_key']]=attributes[1982]
            db.execute('INSERT INTO meta VALUES (?,?)',('requiredSkillTimeBonuses',json.dumps(bonuses)))
            db.execute('INSERT INTO meta VALUES (?,?)', ('duplicateRecipes', str(duplicate_count)))
            db.commit()
            assert db.execute('SELECT count(*) FROM recipes').fetchone()[0] > 1000
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        os.replace(temp, target)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


class Catalog:
    def __init__(self, path, pi_fallback=None):
        self.path = Path(path)
        self.pi_fallback = Path(pi_fallback) if pi_fallback else None
        self.lock = threading.RLock()
        self.reload()

    def reload(self):
        with self.lock, closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            self.types = {r['id']: dict(r) for r in db.execute('SELECT * FROM types')}
            self.recipes = {r['product_id']: dict(r) for r in db.execute('SELECT * FROM recipes')}
            self.meta = dict(db.execute('SELECT key,value FROM meta'))
            for r in self.recipes.values():
                r['materials'] = json.loads(r['materials'])
                if 'skills' in r:r['skills']=json.loads(r['skills'])
            self.skill_time_bonuses={int(k):v for k,v in json.loads(self.meta.get('requiredSkillTimeBonuses','{}')).items()}
            # A previously downloaded catalogue can predate skill metadata.
            # Only augment from the bundled catalogue when its SDE build matches.
            if self.pi_fallback and self.pi_fallback.resolve()!=self.path.resolve():
                with closing(sqlite3.connect(self.pi_fallback)) as fallback:
                    meta=dict(fallback.execute('SELECT key,value FROM meta'))
                    columns={r[1] for r in fallback.execute('PRAGMA table_info(recipes)')}
                    if meta.get('buildNumber')==self.meta.get('buildNumber') and 'skills' in columns:
                        for tid,skills in fallback.execute('SELECT product_id,skills FROM recipes'):
                            if tid in self.recipes:self.recipes[tid].setdefault('skills',json.loads(skills))
                        if not self.skill_time_bonuses:
                            self.skill_time_bonuses={int(k):v for k,v in json.loads(meta.get('requiredSkillTimeBonuses','{}')).items()}
            self.by_blueprint = {r['bp_id']: r for r in self.recipes.values()}
            self.pi_schematics,self.pi_types,self.pi_planets,self.pi_systems={},{},{},{}
            self.pi_meta={}
            for source in dict.fromkeys(p for p in [self.path,self.pi_fallback] if p):
                with closing(sqlite3.connect(source)) as pi_db:
                    pi_db.row_factory=sqlite3.Row
                    tables={r[0] for r in pi_db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    if not {'pi_schematics','pi_types','pi_planets','pi_systems'}.issubset(tables):continue
                    self.pi_schematics={r['id']:{**dict(r),
                        'inputs':{int(k):v for k,v in json.loads(r['inputs']).items()},
                        'outputs':{int(k):v for k,v in json.loads(r['outputs']).items()},
                        'pins':json.loads(r['pins'])} for r in pi_db.execute('SELECT * FROM pi_schematics')}
                    self.pi_types={r['id']:dict(r) for r in pi_db.execute('SELECT * FROM pi_types')}
                    self.pi_planets={r['id']:dict(r) for r in pi_db.execute('SELECT * FROM pi_planets')}
                    self.pi_systems=dict(pi_db.execute('SELECT id,name FROM pi_systems'))
                    self.pi_meta=dict(pi_db.execute('SELECT key,value FROM meta'))
                    break

    def name(self, type_id):
        return self.types.get(int(type_id), {}).get('name', f'Type {type_id}')

    def search(self, query, all_types=False):
        q = normalize(query.strip())
        if not q:
            return []
        candidates = self.types.values() if all_types else (
            self.types[i] for i in self.recipes if i in self.types)
        rows = [t for t in candidates if t['published'] and
                (all(word in t['search'] for word in q.split()) or str(t['id']) == q)]
        rows.sort(key=lambda t: (t['search'] != q, not t['search'].startswith(q), t['search']))
        return [{'id': t['id'], 'name': t['name'],
                 'activity': self.recipes.get(t['id'], {}).get('activity'),
                 'output': self.recipes.get(t['id'], {}).get('output')} for t in rows[:40]]
