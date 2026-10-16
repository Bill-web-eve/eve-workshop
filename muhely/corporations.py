"""Corporation resource validation and safe, token-free UI status."""
import time

from .esi import EsiError


def positive_id(value):
    return value if type(value) is int and 0<value<2**53 else None


def validate_resource(kind, data):
    if not isinstance(data,list):raise EsiError('Hibás corporation adatlista. A korábbi adatok megmaradtak.')
    required={'assets':['item_id','type_id','location_id'],
              'blueprints':['item_id','type_id','location_id'],
              'jobs':['job_id','blueprint_type_id','output_location_id']}[kind]
    for row in data:
        if not isinstance(row,dict) or any(positive_id(row.get(k)) is None for k in required):
            raise EsiError('Hibás corporation tételazonosító. A korábbi adatok megmaradtak.')
        fields={'assets':['quantity'],'blueprints':['quantity','runs','material_efficiency','time_efficiency'],
                'jobs':['runs','activity_id']}[kind]
        if any(type(row.get(k)) is not int for k in fields):raise EsiError('Hibás corporation mennyiségadat.')
        if kind=='assets' and row['quantity']<0:raise EsiError('Negatív corp készletmennyiség.')
        if kind=='blueprints' and not (0<=row['material_efficiency']<=10 and 0<=row['time_efficiency']<=20 and row['runs']>=-1):
            raise EsiError('Hibás corp blueprintparaméter.')
        if kind=='jobs' and (row['runs']<0 or not isinstance(row.get('status'),str)):
            raise EsiError('Hibás corp jobadat.')


def dashboard(store):
    chars=store.characters();rows=[]
    for corp in store.corporations():
        members=[{**c,'access':store.resource_status(c['id'],'corporations')} for c in chars if c.get('corporation_id')==corp['id']]
        parts={k:store.corporation_snapshot(corp['id'],k) for k in ['assets','blueprints','jobs']}
        ready=bool(any(c['id']==corp['provider_id'] for c in members) and all(parts.values()) and not corp['error'])
        rows.append({**corp,'members':members,'ready':ready,
                     'stale':bool(ready and min(p['expires'] for p in parts.values())<=time.time()),
                     'data_times':{k:(p or {}).get('fetched') for k,p in parts.items()},
                     'asset_count':len(parts['assets']['data']) if parts['assets'] else None,
                     'blueprint_count':len(parts['blueprints']['data']) if parts['blueprints'] else None,
                     'job_count':sum(j.get('status') in ['active','paused','ready'] for j in parts['jobs']['data']) if parts['jobs'] else None})
    return {'corporations':rows,'characters':[{**c,'access':store.resource_status(c['id'],'corporations')} for c in chars]}
