"""Production duration from active ESI skill levels and SDE requirements."""
from decimal import Decimal
import time

from .skills import validate_resource
from .esi import EsiError


def profiles(store, settings, corporation_id=None):
    result=[]
    for character,skills,queue,status in store.skill_records():
        if corporation_id is not None:
            if character.get('corporation_id')!=corporation_id:continue
        available=skills is not None and not (status or {}).get('needs_auth',False)
        if available:
            try:validate_resource('skills',skills['data'])
            except EsiError:available=False
        result.append({'id':character['id'],'name':character['name'],'available':available,
            'levels':{r['skill_id']:r['active_skill_level'] for r in skills['data']['skills']} if available else {},
            'as_of':skills['fetched'] if skills else None,
            'stale':bool(available and (time.time()-skills['fetched']>86400 or (status or {}).get('error')))})
    return result


def duration_skills(recipe, catalog, characters, selected=None):
    manual={'character_id':None,'name':None,'factor':None,'bonuses':[],'missing_skills':[],
            'status':'manual','as_of':None,'warning':''}
    if selected in [None,0]:return {**manual,'warning':'Nincs kiválasztva gyártó karakter; kézi időbecslés.'}
    if 'skills' not in recipe:return {**manual,'warning':'A recept skilladata hiányzik; frissítsd a receptadatbázist. Kézi időbecslés.'}
    candidates=[]
    for character in characters:
        if character['id']!=selected:continue
        if not character['available']:continue
        levels=character['levels'];factor=Decimal(1);bonuses=[]
        required=recipe['skills']
        missing=[{'id':s['typeID'],'name':catalog.name(s['typeID']),'required':s['level'],
                  'active':levels.get(s['typeID'],0)} for s in required if levels.get(s['typeID'],0)<s['level']]
        effects=[(45746,-4)] if recipe['activity']=='reaction' else [(3380,-4),(3388,-3)]+[
            (s['typeID'],catalog.skill_time_bonuses[s['typeID']]) for s in required
            if s['typeID'] not in [3380,3388] and s['typeID'] in catalog.skill_time_bonuses]
        for sid,percent in effects:
            level=levels.get(sid,0)
            factor*=1+Decimal(str(percent))*level/100
            bonuses.append({'id':sid,'name':catalog.name(sid),'level':level,'percent_per_level':percent})
        candidates.append({'character_id':character['id'],'name':character['name'],'factor':float(factor),
            'bonuses':bonuses,'missing_skills':missing,'status':'missing' if missing else 'verified',
            'as_of':character['as_of'],'warning':('Hiányzó gyártási skill; ezzel a karakterrel a job nem indítható.' if missing else
                'Korábbi skilladatokból számolt idő; frissítsd a skilleket.' if character['stale'] else '')})
    if candidates:return candidates[0]
    return {**manual,'warning':'Nincs használható skilladat; engedélyezd és frissítsd a skilleket. Kézi időbecslés.'}
