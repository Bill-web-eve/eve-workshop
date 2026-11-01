"""Read-only last coherent plan views; never a substitute for live reservations."""
import hashlib
import json
import time


def schema(store):
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS stable_plan_views(key TEXT PRIMARY KEY, snapshot TEXT NOT NULL, data TEXT NOT NULL, updated REAL NOT NULL)')


def key(context,plans,product,quantity,saved_id,manufacturer,catalog,characters):
    pool=[{k:p.get(k) for k in ['id','product_id','quantity','reserve_active','reserved_at','created','manufacturer_id']}
          for p in plans if p.get('corporation_id')==context.get('corporation_id')]
    pool.sort(key=lambda p:p['id'])
    value=[1,context.get('corporation_id'),product,quantity,saved_id,manufacturer,context['settings'],
           context['inventory'],context['parameters'],pool,catalog,sorted(c['id'] for c in characters)]
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def marker(context):
    value=[context[k] for k in ['stock','wip','blueprints','jobs','material_locations','skill_profiles']]
    return hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).hexdigest()


def needs_update(store,key,snapshot):
    schema(store)
    with store.db() as db:row=db.execute('SELECT snapshot FROM stable_plan_views WHERE key=?',(key,)).fetchone()
    return row is None or row['snapshot']!=snapshot


def remember(store,key,snapshot,plan):
    if plan.get('preview_only') or plan.get('inventory_wait'):return
    schema(store)
    with store.db() as db:
        db.execute('INSERT OR REPLACE INTO stable_plan_views VALUES(?,?,?,?)',(key,snapshot,json.dumps(plan),time.time()))
        db.execute('DELETE FROM stable_plan_views WHERE key NOT IN (SELECT key FROM stable_plan_views ORDER BY updated DESC LIMIT 128)')


def load(store,key):
    schema(store)
    with store.db() as db:row=db.execute('SELECT data FROM stable_plan_views WHERE key=?',(key,)).fetchone()
    return json.loads(row['data']) if row else None
