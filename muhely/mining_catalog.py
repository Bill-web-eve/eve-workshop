"""Mining ore volumes and refining recipes from the same official SDE build."""
from __future__ import annotations
import json


def import_mining(db, archive):
    def rows(name):
        for line in archive.open(name):
            if line.strip():yield json.loads(line)
    groups={r['_key'] for r in rows('groups.jsonl') if r.get('categoryID')==25 or r['_key']==711}
    types={r['_key']:r for r in rows('types.jsonl')}
    materials={r['_key']:r.get('materials',[]) for r in rows('typeMaterials.jsonl')}
    db.execute('CREATE TABLE IF NOT EXISTS mining_types(id INTEGER PRIMARY KEY,data TEXT NOT NULL)')
    db.execute('DELETE FROM mining_types')
    for tid,t in types.items():
        if t.get('groupID') not in groups or not t.get('published') or t.get('volume',0)<=0:continue
        data={'id':tid,'name':t['name']['en'],'volume':t['volume'],'portion':t.get('portionSize',1),
              'materials':[{'id':v['materialTypeID'],'name':types[v['materialTypeID']]['name']['en'],
                            'quantity':v['quantity']} for v in materials.get(tid,[])]}
        db.execute('INSERT INTO mining_types VALUES (?,?)',(tid,json.dumps(data)))
