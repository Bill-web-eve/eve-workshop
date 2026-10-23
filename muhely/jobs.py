"""Read downloaded industry jobs independently of plan and inventory filters."""
import time
from .planner import ACTIVE,ACTIVITIES,PlanningError


def dashboard(store,catalog,corporation_id=None,now=None):
    now=time.time() if now is None else now
    chars=store.characters();names={c['id']:c['name'] for c in chars}
    corporate_ids=set()
    for corp in store.corporations():
        snapshot=store.corporation_snapshot(corp['id'],'jobs')
        if snapshot:corporate_ids.update(j['job_id'] for j in snapshot['data'])
    if corporation_id is None:
        owners=[(c,store.snapshot(c['id'],'jobs')) for c in chars]
    else:
        corp=store.corporation(corporation_id)
        if not corp:raise PlanningError('Ismeretlen corporation. Előbb frissítsd a corp-adatokat.')
        owners=[(corp,store.corporation_snapshot(corporation_id,'jobs'))]
    sources=[];rows={};seen={}
    for owner,snapshot in owners:
        sources.append({'id':owner['id'],'name':owner['name'],'available':snapshot is not None,
                        'fetched':snapshot['fetched'] if snapshot else None,
                        'stale':bool(snapshot and (snapshot['expires']<=now or owner.get('error'))),'error':owner.get('error')})
        if not snapshot:continue
        for job in snapshot['data']:
            jid=job['job_id']
            if corporation_id is None and (jid in corporate_ids or job.get('corporation_id')):continue
            if snapshot['fetched']<seen.get(jid,0):continue
            seen[jid]=snapshot['fetched']
            if job.get('status') not in ACTIVE:rows.pop(jid,None);continue
            char_id=job.get('installer_id') or (owner['id'] if corporation_id is None else None)
            tid=job.get('product_type_id');recipe=catalog.recipes.get(tid)
            activity=9 if recipe and recipe['activity']=='reaction' else 1
            expected=0
            if recipe and job.get('activity_id') in ACTIVITIES and job['activity_id']==activity and job.get('blueprint_type_id')==recipe['bp_id']:
                expected=int(job['runs'])*recipe['output']
            rows[jid]={**job,'name':catalog.name(tid or job.get('blueprint_type_id') or 0),
                       'expected_output':expected,'character_id':char_id,'character_name':names.get(char_id,str(char_id or '–')),
                       'corporation_id':corporation_id}
    return {'corporation_id':corporation_id,'sources':sources,'rows':sorted(rows.values(),key=lambda j:(j.get('end_date') or '',j['job_id'])),'calculated_at':now}
