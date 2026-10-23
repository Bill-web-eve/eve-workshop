"""Read-only skill monitoring, including completed entries not yet in /skills."""
from datetime import datetime, timezone
import time

from .esi import EsiError
from .refresh_policy import AUTO_SECONDS

FIVE_DAYS=5*24*60*60


def instant(value):
    if value is None:
        return None
    try:
        result=datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result.timestamp()
    except (TypeError,ValueError,AttributeError,OverflowError):
        raise EsiError('Érvénytelen időpont az EVE skilladataiban; a korábbi adatok megmaradtak.') from None


def validate_resource(kind,data):
    def integer(record,key,minimum=0,maximum=2**53-1):
        value=record.get(key)
        if isinstance(value,bool) or not isinstance(value,int) or not minimum<=value<=maximum:
            raise EsiError('Az EVE hibás skilladatot adott; a korábbi adatok megmaradtak.')
    if kind=='skills':
        if not isinstance(data,dict) or not isinstance(data.get('skills'),list):
            raise EsiError('Az EVE skilllistája nem olvasható; a korábbi adatok megmaradtak.')
        integer(data,'total_sp')
        if 'unallocated_sp' in data:integer(data,'unallocated_sp')
        records=data['skills'];seen=set()
        for row in records:
            if not isinstance(row,dict):raise EsiError('Érvénytelen skillrekord.')
            integer(row,'skill_id',1);integer(row,'trained_skill_level',0,5)
            integer(row,'active_skill_level',0,5);integer(row,'skillpoints_in_skill')
            if row['skill_id'] in seen:raise EsiError('Ismétlődő skill az EVE válaszában.')
            seen.add(row['skill_id'])
    elif kind=='skillqueue':
        if not isinstance(data,list):raise EsiError('Az EVE tanulási sora nem olvasható.')
        seen=set()
        for row in data:
            if not isinstance(row,dict):raise EsiError('Érvénytelen tanulásisor-rekord.')
            integer(row,'skill_id',1);integer(row,'finished_level',1,5);integer(row,'queue_position',0,10000)
            if row['queue_position'] in seen:raise EsiError('Ismétlődő pozíció az EVE tanulási sorában.')
            seen.add(row['queue_position'])
            start,end=instant(row.get('start_date')),instant(row.get('finish_date'))
            if start is not None and end is not None and start>end:raise EsiError('Fordított időrend az EVE tanulási sorában.')
            for key in ['level_end_sp','level_start_sp','training_start_sp']:
                if key in row:integer(row,key)
    else:
        raise EsiError('Ismeretlen skilladat.')


def character_view(character,skills,queue,status,name,now):
    base={'id':character['id'],'name':character['name'],'skills':[],'queue':[],
          'current':None,'queue_end':None,'stops_at':None,'seconds_left':None,
          'queue_count':0,'completed_count':0,'total_sp':None,'unallocated_sp':None,
          'skills_as_of':skills['fetched'] if skills else None,
          'queue_as_of':queue['fetched'] if queue else None,
          'checked_at':(status or {}).get('checked_at'),'error':(status or {}).get('error'),
          'needs_auth':bool((status or {}).get('needs_auth',status is None)),
          'stale':False,'status':'unknown','training_status':'unknown','label':'Még nincs adat',
          'gap':False}
    if base['needs_auth']:base['label']='Engedélyezés szükséges'
    if not skills or not queue:
        if base['error'] and not base['needs_auth']:base['label']='Frissítési hiba'
        return base
    try:
        validate_resource('skills',skills['data']);validate_resource('skillqueue',queue['data'])
    except EsiError as error:
        base.update(error=str(error),label='Nem ellenőrizhető adat')
        return base
    trained={r['skill_id']:{'id':r['skill_id'],'name':name(r['skill_id']),
             'trained_level':r['trained_skill_level'],'active_level':r['active_skill_level'],
             'sp':r['skillpoints_in_skill'],'queue_adjusted':False} for r in skills['data']['skills']}
    delta_sp=0;entries=[]
    for raw in sorted(queue['data'],key=lambda r:r['queue_position']):
        start,end=instant(raw.get('start_date')),instant(raw.get('finish_date'))
        phase='completed' if end is not None and end<=now else (
              'training' if start is not None and end is not None and start<=now<end else (
              'scheduled' if start is not None and start>now else
              'uncertain' if end is not None else 'paused'))
        entry={'id':raw['skill_id'],'name':name(raw['skill_id']),'position':raw['queue_position'],
               'level':raw['finished_level'],'start':start,'finish':end,'phase':phase,
               'seconds_left':max(0,end-now) if end is not None else None}
        entries.append(entry)
        if phase=='completed':
            skill=trained.setdefault(raw['skill_id'],{'id':raw['skill_id'],'name':name(raw['skill_id']),
                    'trained_level':0,'active_level':None,'sp':0,'queue_adjusted':False})
            if raw['finished_level']>skill['trained_level']:
                skill['trained_level']=raw['finished_level'];skill['queue_adjusted']=True
            if 'level_end_sp' in raw and raw['level_end_sp']>skill['sp']:
                delta_sp+=raw['level_end_sp']-skill['sp'];skill['sp']=raw['level_end_sp'];skill['queue_adjusted']=True
    pending=[e for e in entries if e['phase']!='completed']
    active=[e for e in pending if e['phase']=='training']
    current=active[0] if len(active)==1 else None
    training_status='idle';label='Nem tanul';stops_at=None;gap=False
    if current:
        stops_at=current['finish']
        for entry in pending:
            if entry['position']<=current['position']:continue
            if entry['start'] is None or entry['finish'] is None or entry['start']>stops_at+1:
                gap=True;break
            stops_at=max(stops_at,entry['finish'])
        training_status='soon' if stops_at<=now+FIVE_DAYS else 'training'
        label='5 napon belül leáll' if training_status=='soon' else 'Tanul · több mint 5 napra elég'
    elif len(active)>1 or any(e['phase']=='uncertain' for e in pending):
        training_status='unknown';label='Az időzítés nem ellenőrizhető'
    elif pending:
        label='Nem tanul / szünetel'
    else:
        label='Nem tanul · üres sor'
    # Cache lifetime decides when to revalidate, not whether a just-checked
    # no-cache response is already obsolete. Allow the 15-minute polling interval plus a five-minute refresh grace period.
    stale=now-min(skills['fetched'],queue['fetched'])>=AUTO_SECONDS+5*60
    display_status=training_status
    if base['needs_auth']:display_status='unknown';label='Engedélyezés szükséges'
    elif base['error']:display_status='unknown';label='Frissítési hiba · korábbi adatok'
    elif stale:display_status='unknown';label='Elavult adatok · frissítés szükséges'
    base.update(skills=sorted(trained.values(),key=lambda s:s['name'].casefold()),queue=entries,current=current,
                queue_end=max((e['finish'] for e in pending if e['finish'] is not None),default=None),
                stops_at=stops_at,seconds_left=max(0,stops_at-now) if stops_at is not None else None,
                queue_count=len(pending),completed_count=len(entries)-len(pending),gap=gap,
                total_sp=skills['data']['total_sp']+delta_sp,unallocated_sp=skills['data'].get('unallocated_sp'),
                stale=stale,status=display_status,training_status=training_status,label=label)
    return base


def dashboard(store,catalog,now=None):
    now=time.time() if now is None else now
    rows=[character_view(c,skills,queue,status,catalog.name,now)
          for c,skills,queue,status in store.skill_records()]
    from .accounts import load,apply_tracking,dashboard as account_dashboard
    apply_tracking(rows,load(store),now)
    order={'idle':0,'soon':1,'unknown':2,'training':3,'excluded':4}
    rows.sort(key=lambda r:(order[r['status']],r['name'].casefold()))
    return {'characters':rows,'summary':{key:sum(r['status']==key for r in rows)
            for key in ['idle','soon','unknown','training','excluded']},'accounts':account_dashboard(store,now),'calculated_at':now,'threshold_seconds':FIVE_DAYS}
