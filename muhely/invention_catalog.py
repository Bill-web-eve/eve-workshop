"""T2 ship invention data extracted from the same official SDE as recipes."""
import json


def import_invention(db,archive):
    db.executescript('''CREATE TABLE IF NOT EXISTS invention_recipes(product_id INTEGER PRIMARY KEY,data TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS invention_decryptors(id INTEGER PRIMARY KEY,data TEXT NOT NULL);''')
    db.execute('DELETE FROM invention_recipes');db.execute('DELETE FROM invention_decryptors')
    def rows(name):
        if name not in archive.namelist():return
        with archive.open(name) as stream:
            for line in stream:
                if line.strip():yield json.loads(line)
    groups={r['_key'] for r in rows('groups.jsonl') if r.get('categoryID')==6}
    ships={r['_key'] for r in rows('types.jsonl') if r.get('groupID') in groups and r.get('metaGroupID')==2}
    blueprints=list(rows('blueprints.jsonl'))
    manufactured={r['blueprintTypeID']:r.get('activities',{}).get('manufacturing',{}).get('products',[]) for r in blueprints}
    for row in blueprints:
        act=row.get('activities',{});inv=act.get('invention');base=manufactured[row['blueprintTypeID']]
        if not inv or len(base)!=1 or not act.get('copying'):continue
        outcomes=[p['typeID'] for bp in inv.get('products',[]) for p in manufactured.get(bp['typeID'],[])]
        for product in inv.get('products',[]):
            outputs=manufactured.get(product['typeID'],[])
            if len(outputs)!=1 or outputs[0]['typeID'] not in ships:continue
            tid=outputs[0]['typeID']
            data={'product_id':tid,'blueprint_id':product['typeID'],'base_blueprint_id':row['blueprintTypeID'],
                  'base_product_id':base[0]['typeID'],'base_probability':product['probability'],'runs':product['quantity'],
                  'materials':inv.get('materials',[]),'skills':inv.get('skills',[]),
                  'copy_seconds':act['copying']['time'],'invention_seconds':inv['time'],
                  'copy_limit':row.get('maxProductionLimit',1),'eiv_products':outcomes}
            db.execute('INSERT INTO invention_recipes VALUES(?,?)',(tid,json.dumps(data,separators=(',',':'))))
    for row in rows('typeDogma.jsonl'):
        attrs={a['attributeID']:a['value'] for a in row.get('dogmaAttributes',[])}
        if not all(i in attrs for i in [1112,1113,1114,1124]):continue
        if not db.execute('SELECT 1 FROM types WHERE id=? AND published=1 AND group_id=1304',(row['_key'],)).fetchone():continue
        data={'id':row['_key'],'probability_multiplier':attrs[1112],'me':int(attrs[1113]),'te':int(attrs[1114]),'runs':int(attrs[1124])}
        db.execute('INSERT INTO invention_decryptors VALUES(?,?)',(row['_key'],json.dumps(data,separators=(',',':'))))


def load(catalog):
    from contextlib import closing
    import sqlite3
    catalog.inventions={};catalog.decryptors={}
    for source in dict.fromkeys(p for p in [catalog.path,catalog.pi_fallback] if p):
        with closing(sqlite3.connect(source)) as db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'invention_recipes','invention_decryptors'}.issubset(tables):continue
            meta=dict(db.execute('SELECT key,value FROM meta'))
            if meta.get('buildNumber')!=catalog.meta.get('buildNumber'):continue
            catalog.inventions={int(tid):json.loads(data) for tid,data in db.execute('SELECT * FROM invention_recipes')}
            catalog.decryptors={int(tid):{**json.loads(data),'name':catalog.name(tid)} for tid,data in db.execute('SELECT * FROM invention_decryptors')}
            return
