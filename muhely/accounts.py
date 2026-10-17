"""User-maintained account metadata. ESI exposes no subscription dates."""
import json
import math
import time
from .planner import PlanningError


def load(store):
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS account_tracking (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
        row=db.execute('SELECT data FROM account_tracking WHERE id=1').fetchone()
    data=json.loads(row['data']) if row else {'accounts':[], 'characters':{}}
    known={str(c['id']) for c in store.characters()}
    data['characters']={cid:pref for cid,pref in data['characters'].items() if cid in known}
    return data


def save(store, data):
    if not isinstance(data,dict) or not isinstance(data.get('accounts'),list) or not isinstance(data.get('characters'),dict):
        raise PlanningError('Hibás accountbeállítás.')
    if len(data['accounts'])>200:raise PlanningError('Túl sok account.')
    def expiry(value):
        if value is None:return None
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<4102444800:
            raise PlanningError('Hibás lejárati idő.')
        return float(value)
    accounts=[];ids=set()
    for raw in data['accounts']:
        if not isinstance(raw,dict):raise PlanningError('Hibás accountbeállítás.')
        aid=raw.get('id');name=raw.get('name');status=raw.get('omega_status','unknown')
        if not isinstance(aid,str) or not 1<=len(aid)<=80 or aid in ids or not isinstance(name,str) or not name.strip() or len(name)>100 or status not in ['unknown','omega','alpha']:
            raise PlanningError('Hibás vagy ismétlődő account.')
        ids.add(aid)
        accounts.append({'id':aid,'name':name.strip(),'omega_status':status,
                         **{k:expiry(raw.get(k)) for k in ['omega_expires','mct1_expires','mct2_expires']}})
    known={str(c['id']) for c in store.characters()};characters={};members={}
    for cid,raw in data['characters'].items():
        if cid not in known or not isinstance(raw,dict):raise PlanningError('Ismeretlen karakter az accountban.')
        aid=raw.get('account_id');mode=raw.get('training_mode','auto')
        if aid is not None and aid not in ids or mode not in ['auto','primary','mct1','mct2','disabled']:
            raise PlanningError('Hibás tanulási hely.')
        if aid:
            members.setdefault(aid,[]).append(cid)
            if len(members[aid])>3:raise PlanningError('Egy accounthoz legfeljebb három karakter rendelhető.')
        elif mode in ['primary','mct1','mct2']:raise PlanningError('A tanulási helyhez válassz accountot.')
        characters[cid]={'account_id':aid,'training_mode':mode}
    for aid in ids:
        assigned=[characters[c]['training_mode'] for c in members.get(aid,[]) if characters[c]['training_mode'] in ['primary','mct1','mct2']]
        if len(assigned)!=len(set(assigned)):raise PlanningError('Ugyanazt a tanulási helyet nem használhatja két karakter.')
    result={'accounts':accounts,'characters':characters}
    load(store)
    with store.db() as db:db.execute('INSERT OR REPLACE INTO account_tracking VALUES (1,?)',(json.dumps(result),))
    return result


def apply_tracking(rows, tracking, now):
    accounts={a['id']:a for a in tracking['accounts']}
    for row in rows:
        pref=tracking['characters'].get(str(row['id']),{})
        account=accounts.get(pref.get('account_id'));mode=pref.get('training_mode','auto')
        blocked=None;until=None
        row.update(account_id=pref.get('account_id'),account_name=(account or {}).get('name'),training_mode=mode,training_eligibility='unknown',training_reason='')
        if mode=='disabled':blocked='Kézzel kizárva a tanulásfigyelésből.'
        if account:
            alpha=account['omega_status']=='alpha' or account['omega_status']=='omega' and account['omega_expires'] is not None and account['omega_expires']<=now
            if alpha and row['total_sp'] is not None and row['total_sp']>=5000000:blocked='Alpha állapot · az 5 millió SP-s tanulási határ elérve.'
            elif account['omega_status']=='omega' and account['omega_expires'] and row['total_sp'] is not None and row['total_sp']>=5000000:
                until=account['omega_expires']
            if mode in ['mct1','mct2']:
                end=account[mode+'_expires']
                if end is not None and end<=now:blocked='A hozzárendelt MCT tanulási hely lejárt.'
                elif end is not None:until=min(until,end) if until else end
            if mode=='auto' and not row['current']:
                capacity=1+sum(bool(account[k] and account[k]>now) for k in ['mct1_expires','mct2_expires'])
                explicit={tracking['characters'][str(r['id'])]['training_mode'] for r in rows if tracking['characters'].get(str(r['id']),{}).get('account_id')==account['id'] and tracking['characters'][str(r['id'])]['training_mode'] in ['primary','mct1','mct2']}
                current=sum(bool(r['current']) and not r['stale'] for r in rows if tracking['characters'].get(str(r['id']),{}).get('account_id')==account['id'])
                assigned=sum(slot=='primary' or bool(account[slot+'_expires'] and account[slot+'_expires']>now) for slot in explicit)
                if max(current,assigned)>=capacity:blocked='Az account tanulási helyeit más karakterek használják.'
        row['training_until']=until
        if blocked:
            row.update(status='excluded',label='Nem tanítható / kizárva',training_eligibility='blocked',training_reason=blocked,stops_at=None,seconds_left=None)
        elif account and mode in ['primary','mct1','mct2']:
            row['training_eligibility']='eligible' if mode=='primary' or account[mode+'_expires'] else 'unknown'
        if not blocked and until and row['current'] and row['status'] in ['training','soon']:
            row['stops_at']=min(row['stops_at'],until);row['seconds_left']=max(0,row['stops_at']-now)
            if row['seconds_left']<=5*86400:
                row.update(status='soon',label='5 napon belül leáll',training_reason='A tanulási hozzáférés lejárata korlátozza a sort.')


def dashboard(store, now=None):
    data=load(store);now=time.time() if now is None else now
    return {**data,'manual':True,'calculated_at':now,'expiring':[
        {'account_id':a['id'],'account_name':a['name'],'kind':kind,'expires':a[key],'expired':a[key]<=now}
        for a in data['accounts'] for key,kind in [('omega_expires','Omega'),('mct1_expires','MCT 1'),('mct2_expires','MCT 2')]
        if a[key] and a[key]<=now+5*86400 and (key!='omega_expires' or a['omega_status']=='omega')]}
