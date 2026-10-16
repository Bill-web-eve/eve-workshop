"""Public moon metadata, rebuilt with the official CCP SDE (never user records)."""
from __future__ import annotations
import json

ORE_GROUPS = {1884: 4, 1920: 8, 1921: 16, 1922: 32, 1923: 64}


def roman(n):
    result = ''
    for value, symbol in [(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
        while n >= value:
            result += symbol
            n -= value
    return result


def import_moons(db, archive):
    def rows(name):
        if name not in archive.namelist(): return
        for line in archive.open(name):
            if line.strip(): yield json.loads(line)
    db.executescript('''
        CREATE TABLE moon_systems(id INTEGER PRIMARY KEY,name TEXT NOT NULL,search TEXT NOT NULL,
            constellation_id INTEGER,constellation TEXT,security REAL);
        CREATE TABLE moon_locations(id INTEGER PRIMARY KEY,system_id INTEGER NOT NULL,name TEXT NOT NULL);
        CREATE INDEX moon_location_system ON moon_locations(system_id);
        CREATE TABLE moon_ores(id INTEGER PRIMARY KEY,data TEXT NOT NULL);
        CREATE TABLE moon_crystals(id INTEGER PRIMARY KEY,data TEXT NOT NULL);
    ''')
    from .catalog import normalize
    constellations={r['_key']:r['name']['en'] for r in rows('mapConstellations.jsonl')}
    systems={r['_key']:r for r in rows('mapSolarSystems.jsonl')}
    db.executemany('INSERT INTO moon_systems VALUES (?,?,?,?,?,?)',
        ((i,r['name']['en'],normalize(r['name']['en']),r['constellationID'],
          constellations.get(r['constellationID'],''),r.get('securityStatus',0)) for i,r in systems.items()))
    planets={r['_key']:(r['solarSystemID'],r.get('celestialIndex',0)) for r in rows('mapPlanets.jsonl')}
    db.executemany('INSERT INTO moon_locations VALUES (?,?,?)',
        ((r['_key'],r['solarSystemID'],systems[r['solarSystemID']]['name']['en']+' '+
          roman(planets[r['orbitID']][1])+' - Moon '+str(r['orbitIndex']))
         for r in rows('mapMoons.jsonl') if r.get('orbitID') in planets and r['solarSystemID'] in systems))
    types={r['_key']:r for r in rows('types.jsonl')}
    dogma={r['_key']:{a['attributeID']:a['value'] for a in r.get('dogmaAttributes',[])} for r in rows('typeDogma.jsonl')}
    materials={r['_key']:r.get('materials',[]) for r in rows('typeMaterials.jsonl')}
    for i,t in types.items():
        a=dogma.get(i,{})
        if t.get('groupID') in ORE_GROUPS and a.get(2711)==i and t.get('published') and i in materials:
            data={'id':i,'name':t['name']['en'],'rarity':ORE_GROUPS[t['groupID']],
                  'skill_id':int(a[790]),'volume':t['volume'],'portion':t['portionSize'],
                  'materials':[{'id':v['materialTypeID'],'name':types[v['materialTypeID']]['name']['en'],
                                'quantity':v['quantity']} for v in materials[i]]}
            db.execute('INSERT INTO moon_ores VALUES (?,?)',(i,json.dumps(data)))
        name=t.get('name',{}).get('en','')
        if t.get('published') and 'Moon Mining Crystal Type ' in name and 'Blueprint' not in name and 783 in a:
            data={'id':i,'name':name,'skill_id':int(a[182]),'variant':name.split('Type ')[1],
                  'volatility':a[783],'damage':a[784],'hp':a.get(9,1)}
            db.execute('INSERT INTO moon_crystals VALUES (?,?)',(i,json.dumps(data)))
    def attr(name,attribute):
        i=next(i for i,t in types.items() if t.get('name',{}).get('en')==name)
        return dogma[i][attribute]
    metenox=next(rows('metenoxMoonDrill.jsonl'),None)
    if metenox:
        # Volume is 20,000 at introduction, doubled in New Dawn, then -25%
        # in Resources Realigned. It is not exported in metenoxMoonDrill.
        rules={'extraction_m3_hour':30000,'metenox':metenox,
               'athanor_fuel_hour':attr('Standup Moon Drill I',2109),
               'metenox_fuel_hour':attr('Standup Metenox Moon Drill',2109),
               'athanor_online_fuel':attr('Standup Moon Drill I',2110),
               'metenox_online_fuel':attr('Standup Metenox Moon Drill',2110),
               'tatara_bonus':attr('Tatara',2722),
               'rig_base':attr('Standup L-Set Reprocessing Monitor II',717),
               'rig_nullsec':attr('Standup L-Set Reprocessing Monitor II',2357)}
        db.execute('INSERT INTO meta VALUES (?,?)',('moonRules',json.dumps(rules)))
