"""Read-only, cached moon timers and calendar. Never invent an ESI ore scan."""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
import math
import re
import time

from .esi import ESI, EsiError, AuthenticationError
from . import moon_notifications as notices

CALENDAR_SCOPE='esi-calendar.read_calendar_events.v1'
MINING_SCOPE='esi-industry.read_corporation_mining.v1'
MOON_SCOPES=[CALENDAR_SCOPE,MINING_SCOPE,notices.SCOPE]


def stamp(value):
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        return d.timestamp() if d.tzinfo is not None else None
    except (ValueError,TypeError,AttributeError,OverflowError):return None


def positive(value):return isinstance(value,int) and not isinstance(value,bool) and 0<value<2**53


def validate_timers(data):
    if not isinstance(data,list):raise EsiError('Hibás ESI kitermelési időzítő.')
    seen=set()
    for row in data:
        if not isinstance(row,dict) or not all(positive(row.get(k)) for k in ['moon_id','structure_id']):raise EsiError('Hibás ESI kitermelési időzítő.')
        dates=[stamp(row.get(k)) for k in ['extraction_start_time','chunk_arrival_time','natural_decay_time']]
        if None in dates or not dates[0]<dates[1]<=dates[2] or dates[1]-dates[0]>60*86400:raise EsiError('Hibás ESI kitermelési időzítő.')
        key=(row['moon_id'],row['structure_id'])
        if key in seen:raise EsiError('Ismételt ESI kitermelési időzítő.')
        seen.add(key)
    return data


def cached(eve,char_id,kind,url,token,validator):
    old=eve.store.snapshot(char_id,kind);now=time.time()
    if old and old['expires']>now:return old
    data,h=eve.http.request(url,token=token,headers={'If-None-Match':old['etag']} if old and old.get('etag') else {})
    if data is None:
        if not old:raise EsiError('Hiányzó korábbi holdadat.')
        data=old['data']
    validator(data)
    return {'data':data,'fetched':now,'expires':cache_expiry(h,now),'etag':{k.lower():v for k,v in h.items()}.get('etag') or (old or {}).get('etag')}


def cache_expiry(headers,now):
    h={k.lower():v for k,v in headers.items()}
    match=re.search(r'max-age\s*=\s*"?(\d+)',h.get('cache-control',''))
    if match:
        try:return now+max(60,int(match[1])-max(0,int(h.get('age',0))))
        except ValueError:pass
    if 'expires' in h:
        from email.utils import parsedate_to_datetime
        try:return max(now+60,parsedate_to_datetime(h['expires']).timestamp())
        except (ValueError,TypeError):pass
    return now+300


def validate_notifications(data):
    if not isinstance(data,list) or len(data)>10000 or any(not isinstance(r,dict) for r in data):raise EsiError('Hibás ESI értesítéslista.')
    for row in data:
        if row.get('type') in notices.TYPES and (not positive(row.get('notification_id')) or stamp(row.get('timestamp')) is None or not isinstance(row.get('text'),str) or len(row['text'])>200000):raise EsiError('Hibás holdkitermelési értesítés.')


def validate_calendar(data):
    if not isinstance(data,list) or any(not isinstance(r,dict) or not positive(r.get('event_id')) or stamp(r.get('event_date')) is None for r in data):raise EsiError('Hibás ESI naptáradat.')


def validate_event(data):
    if not isinstance(data,dict) or not positive(data.get('event_id')) or stamp(data.get('date')) is None or not isinstance(data.get('title'),str) or len(data['title'])>2000 or not isinstance(data.get('text'),str) or len(data['text'])>200000:raise EsiError('Hibás ESI naptáresemény.')


def sync(eve):
    if not eve.sync_lock.acquire(blocking=False):raise EsiError('Az EVE-frissítés már folyamatban van.')
    results=[];done={}
    try:
        for char in eve.store.characters():
            cid=char['id']
            try:
                token=eve.token(cid,required_scopes=[notices.SCOPE])
                raw=cached(eve,cid,'moon_notification_response',f'{ESI}/characters/{cid}/notifications',token,validate_notifications)
                filtered=[r for r in raw['data'] if r.get('type') in notices.TYPES]
                previous=eve.store.snapshot(cid,'moon_notifications')
                combined={r['notification_id']:r for r in (previous or {}).get('data',{}).get('notifications',[]) if stamp(r.get('timestamp')) and stamp(r['timestamp'])>time.time()-90*86400}
                combined.update({r['notification_id']:r for r in filtered})
                eve.store.save_snapshots(cid,{'moon_notification_response':{**raw,'data':filtered},'moon_notifications':{**raw,'data':{'notifications':list(combined.values())}}},domain='moon_notifications')
                results.append({'id':cid,'kind':'notifications','ok':True})
            except EsiError as error:
                eve.store.resource_error(cid,'moon_notifications',str(error),isinstance(error,AuthenticationError));results.append({'id':cid,'kind':'notifications','ok':False,'error':str(error)})
            # Calendar access remains useful even without corporation mining roles.
            try:
                token=eve.token(cid,required_scopes=[CALENDAR_SCOPE]);parts={};events=[];cursor=None;seen=set()
                for page in range(20):
                    url=f'{ESI}/characters/{cid}/calendar'+(f'?from_event={cursor}' if cursor else '')
                    key='moon_calendar_page:'+str(cursor or 0)
                    listing=cached(eve,cid,key,url,token,validate_calendar);parts[key]=listing
                    rows=listing['data']
                    for row in rows:
                        if row['event_id'] in seen:raise EsiError('Ismétlődő ESI naptároldal.')
                        seen.add(row['event_id'])
                        detail=cached(eve,cid,'moon_event:'+str(row['event_id']),f"{ESI}/characters/{cid}/calendar/{row['event_id']}",token,validate_event)
                        if detail['data']['event_id']!=row['event_id']:raise EsiError('Hibás ESI naptáresemény.')
                        parts['moon_event:'+str(row['event_id'])]=detail
                        events.append(detail['data'])
                    if len(rows)<50:break
                    cursor=rows[-1]['event_id']
                else:raise EsiError('A naptár túl nagy; a korábbi teljes adat megmaradt.')
                previous=eve.store.snapshot(cid,'moon_calendar')
                live_ids={e['event_id'] for e in events}
                events.extend(dict(e,historical=True) for e in (previous or {}).get('data',[]) if e['event_id'] not in live_ids and stamp(e['date']) is not None and time.time()-90*86400<stamp(e['date'])<=time.time())
                parts['moon_calendar']={'data':events,'fetched':time.time(),'expires':min(p['expires'] for p in parts.values()),'etag':None}
                eve.store.save_snapshots(cid,parts,domain='moon_calendar');results.append({'id':cid,'kind':'calendar','ok':True})
            except EsiError as error:
                eve.store.resource_error(cid,'moon_calendar',str(error),isinstance(error,AuthenticationError));results.append({'id':cid,'kind':'calendar','ok':False,'error':str(error)})
            try:
                token=eve.token(cid,required_scopes=[MINING_SCOPE])
                profile,_=eve.http.request(f'{ESI}/characters/{cid}')
                corp=profile.get('corporation_id') if isinstance(profile,dict) else None
                if not positive(corp):raise EsiError('A karakter corporation tagsága nem ellenőrizhető.')
                if corp in done:
                    snap=done[corp]
                else:
                    parts={};rows=[];pages=1;modified=[]
                    for page in range(1,1001):
                        key=f'moon_timer_page:{corp}:{page}'
                        # X-Pages is not present on a cached body; keep it in its payload.
                        old=eve.store.snapshot(cid,key);now=time.time()
                        if old and old['expires']>now:
                            chunk=old['data']['rows'];pages=old['data']['pages'];part=old
                        else:
                            chunk,h=eve.http.request(f'{ESI}/corporation/{corp}/mining/extractions?page={page}',token=token,headers={'If-None-Match':old['etag']} if old and old.get('etag') else {})
                            if chunk is None:
                                if not old:raise EsiError('Hiányzó korábbi holdadat.')
                                chunk=old['data']['rows']
                            validate_timers(chunk)
                            low={k.lower():v for k,v in h.items()};pages=int(low.get('x-pages',(old or {}).get('data',{}).get('pages',1)))
                            if not 1<=pages<=1000:raise EsiError('Túl sok ESI kitermelési oldal.')
                            part={'data':{'rows':chunk,'pages':pages,'modified':low.get('last-modified') or (old or {}).get('data',{}).get('modified')},'fetched':now,'expires':cache_expiry(h,now),'etag':low.get('etag') or (old or {}).get('etag')}
                        parts[key]=part;rows.extend(chunk);modified.append(part['data'].get('modified'))
                        if page>=pages:break
                    validate_timers(rows)
                    if len({d for d in modified if d is not None})>1:raise EsiError('A kitermelési adatok lapozás közben megváltoztak.')
                    old_history=eve.store.snapshot(cid,'moon_history:'+str(corp))
                    history={(r['moon_id'],r['structure_id'],r['chunk_arrival_time']):r for r in (old_history or {}).get('data',[]) if stamp(r['chunk_arrival_time'])>time.time()-90*86400}
                    for row in rows:history[(row['moon_id'],row['structure_id'],row['chunk_arrival_time'])]=row
                    parts['moon_history:'+str(corp)]={'data':list(history.values()),'fetched':time.time(),'expires':time.time()+90*86400,'etag':None}
                    snap={'data':{'corporation_id':corp,'rows':rows,'history':list(history.values())},'fetched':time.time(),'expires':min(p['expires'] for p in parts.values()),'etag':None}
                    parts['moon_timers']=snap;eve.store.save_snapshots(cid,parts,domain='moon_timers');done[corp]=snap
                eve.store.save_snapshots(cid,{'moon_timers':snap},domain='moon_timers');results.append({'id':cid,'kind':'timers','ok':True})
            except (EsiError,ValueError) as error:
                role_denied=getattr(error,'status_code',None)==403
                message='Az ESI elutasította a corporation időzítőinek olvasását (403). A fúró tulajdonos corporationjében Station Manager szerepkör szükséges; a naptár olvasási engedélye önmagában nem elég.' if role_denied else str(error) if isinstance(error,EsiError) else 'Hibás ESI kitermelési lapozás.'
                eve.store.resource_error(cid,'moon_timers',message,isinstance(error,AuthenticationError) and not role_denied);results.append({'id':cid,'kind':'timers','ok':False,'error':message})
        return results
    finally:eve.sync_lock.release()


class Plain(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ['br','tr','p','div']:self.parts.append('\n')
        elif tag in ['td','th']:self.parts.append(' ')
    def handle_endtag(self,tag):
        if tag in ['tr','p','div']:self.parts.append('\n')
        elif tag in ['td','th']:self.parts.append(' ')
    def handle_data(self,text):self.parts.append(text)


def event_ores(event,catalog):
    """Only explicit, complete per-ore m3 lines; never infer a scan from a title."""
    parser=Plain();parser.feed(event['text']);text=''.join(parser.parts)
    rows=[];unknown=False
    for line in text.splitlines():
        if not re.search(r'm(?:³|3)\b|m³',line,re.I):
            if any(re.search(r'(?<!\w)'+re.escape(o['name'])+r'(?!\w)',line,re.I) for o in catalog.moon_ores.values()):unknown=True
            continue
        if re.search(r'[-−]\s*\d',line):unknown=True;continue
        found=[o for o in catalog.moon_ores.values() if re.search(r'(?<!\w)'+re.escape(o['name'])+r'(?!\w)',line,re.I)]
        amount=re.search(r'(?<![\w.,+−-])(\d[\d\s\u00a0.,]*?)\s*m(?:³|3)',line,re.I)
        if len(found)!=1 or not amount:unknown=True;continue
        value=re.sub(r'\s','',amount[1])
        # English client grouping and a decimal point. Ambiguous comma decimals
        # are rejected rather than silently multiplied by a thousand.
        if ',' in value:
            if not re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?',value):unknown=True;continue
            value=value.replace(',','')
        try:volume=float(Decimal(value))
        except Exception:unknown=True;continue
        if not math.isfinite(volume) or not 0<volume<10**12:unknown=True;continue
        rows.append({'id':found[0]['id'],'volume':volume})
    if unknown or not 1<=len(rows)<=4 or len({r['id'] for r in rows})!=len(rows):return []
    return rows


def report(store,catalog,now=None,access_scopes=None):
    now=time.time() if now is None else now
    timers={};events={};access=[];corp_snapshots={}
    notice_cycles,notice_issues=notices.cycles(store,catalog,now)
    for char in store.characters():
        entry={'id':char['id'],'name':char['name']}
        for kind in ['moon_calendar','moon_timers','moon_notifications']:
            snap=store.snapshot(char['id'],kind);status=store.resource_status(char['id'],kind) or {}
            entry[kind]={'fetched':(snap or {}).get('fetched'),'expires':(snap or {}).get('expires'),'error':status.get('error'),'needs_auth':bool(status.get('needs_auth')),'stale':not snap or snap['expires']<=now or bool(status.get('error'))}
            scope={'moon_calendar':CALENDAR_SCOPE,'moon_timers':MINING_SCOPE,'moon_notifications':notices.SCOPE}[kind]
            entry[kind]['scope_granted']=scope in access_scopes.get(char['id'],[]) if access_scopes is not None else None
            entry[kind]['count']=len(snap['data'].get('notifications',[])) if snap and kind=='moon_notifications' else len(snap['data'].get('rows',[])) if snap and kind=='moon_timers' else len(snap['data']) if snap else 0
            if not snap or kind=='moon_notifications':continue
            if kind=='moon_timers':
                corp=snap['data']['corporation_id']
                if corp not in corp_snapshots or snap['fetched']>corp_snapshots[corp][0]['fetched'] or snap['fetched']==corp_snapshots[corp][0]['fetched'] and not entry[kind]['stale']:
                    corp_snapshots[corp]=(snap,entry[kind]['stale'])
            else:
                for row in snap['data']:
                    if row['event_id'] not in events or snap['fetched']>events[row['event_id']]['checked'] or snap['fetched']==events[row['event_id']]['checked'] and not entry[kind]['stale']:
                        events[row['event_id']]={**row,'checked':snap['fetched'],'stale':entry[kind]['stale']}
        access.append(entry)
    for corp,(snap,stale) in corp_snapshots.items():
        current={(r['structure_id'],r['chunk_arrival_time']) for r in snap['data']['rows']}
        combined=list(snap['data']['rows'])+[dict(r,historical=True) for r in snap['data'].get('history',[]) if (r['structure_id'],r['chunk_arrival_time']) not in current and stamp(r['chunk_arrival_time'])<=now]
        for row in combined:
            key=(row['moon_id'],row['structure_id'],row['chunk_arrival_time'])
            timers[key]={**row,'corporation_id':corp,'checked':snap['fetched'],'stale':stale}
    output=[];moon_states={}
    for moon in store.moon_records():
        name=next((r['name'] for r in catalog.moon_locations(moon['system_id']) if r['id']==moon['moon_id']),str(moon['moon_id']))
        matches=[r for r in timers.values() if r['moon_id']==moon['moon_id'] and stamp(r['natural_decay_time'])+moon.get('belt_lifetime_hours',48)*3600>now]
        matched_events=[]
        for event in events.values():
            body=event['title']+' '+event['text']
            structure_ids={r['structure_id'] for r in timers.values() if r['moon_id']==moon['moon_id']}
            linked_structure=any(re.search(r'showinfo:\d+//'+str(sid)+r'(?!\d)',body) for sid in structure_ids)
            if linked_structure or re.search(r'(?<!\w)'+re.escape(name)+r'(?!\d)',body,re.I) or re.search(r'showinfo:(?:14|0)//'+str(moon['moon_id'])+r'(?!\d)',body):matched_events.append(event)
        used_notices=set()
        for timer in matches:
            arrival=stamp(timer['chunk_arrival_time'])
            matching=[n for n in notice_cycles if n['moon_id']==moon['moon_id'] and n['structure_id']==timer['structure_id'] and n['ready_time'] is not None and abs(n['ready_time']-arrival)<=60]
            notice=max(matching,key=lambda n:n['observed_at']) if matching else None
            if notice and notice['cancelled'] or any(n['moon_id']==moon['moon_id'] and n['structure_id']==timer['structure_id'] and n['cancelled'] and n['ready_time'] is None and stamp(timer['extraction_start_time'])<=n['observed_at']<=arrival for n in notice_cycles):continue
            if notice:used_notices.add((notice['structure_id'],notice['ready_time']))
            same=[e for e in matched_events if abs(stamp(e['date'])-arrival)<=3600]
            sources=[(event_ores(e,catalog),e) for e in same if not e['stale']]
            sources=[(ores,e) for ores,e in sources if ores]
            unique={tuple((o['id'],o['volume']) for o in sorted(ores,key=lambda r:r['id'])) for ores,e in sources}
            automatic=sources[0] if len(unique)==1 else None
            ores,event=automatic if automatic else ([],None)
            hours=(arrival-stamp(timer['extraction_start_time']))/3600
            total=sum(o['volume'] for o in ores) if ores else hours*catalog.moon_rules['extraction_m3_hour']
            composition=[{'id':o['id'],'volume':o['volume'],'percent':o['volume']/total*100,'name':catalog.name(o['id'])} for o in ores] if ores else [dict(o,name=catalog.name(o['id']),volume=total*o['percent']/100) for o in moon['ores']]
            # ESI natural_decay_time is automatic FRACTURE, not belt expiry.
            # Actual fracture/rig data is not supplied by these routes.
            decay_hours=moon.get('belt_lifetime_hours',48)
            output.append({**timer,'id':f"timer:{timer['structure_id']}:{timer['chunk_arrival_time']}",'moon_record_id':moon['id'],'moon_name':name,'date':timer['chunk_arrival_time'],'hours':hours,'volume':total,'ores':composition,'composition_source':'esi_calendar' if ores else 'manual','event_id':event['event_id'] if event else None,'volume_source':'esi_calendar' if ores else 'duration_estimate','belt_earliest_expiry':arrival+decay_hours*3600,'belt_latest_expiry':stamp(timer['natural_decay_time'])+decay_hours*3600,'belt_lifetime_hours':decay_hours,'expiry_source':'estimated','kind':'history' if timer.get('historical') or stamp(timer['natural_decay_time'])<=now else 'extraction'})
            if notice:
                apply_notice(output[-1],notice,catalog,decay_hours)
        for notice in notice_cycles:
            if notice['moon_id']!=moon['moon_id'] or notice['cancelled'] or (notice['structure_id'],notice['ready_time']) in used_notices:continue
            end=(notice['fractured_at'] or notice['auto_time'] or notice['ready_time'])+moon.get('belt_lifetime_hours',48)*3600
            if end<now:continue
            row={'id':f"notification:{notice['structure_id']}:{notice['ready_time']}",'moon_record_id':moon['id'],'moon_name':name,'structure_id':notice['structure_id'],'date':datetime.fromtimestamp(notice['ready_time'],timezone.utc).isoformat(),'checked':notice['checked'],'stale':notice['stale'],'natural_decay_time':datetime.fromtimestamp(notice['auto_time'],timezone.utc).isoformat() if notice['auto_time'] else None,'kind':'notification_history' if notice['fractured_at'] or (notice['auto_time'] or notice['ready_time'])<=now else 'notification','expiry_source':'estimated'}
            apply_notice(row,notice,catalog,moon.get('belt_lifetime_hours',48));output.append(row)
        for event in matched_events:
            if any(abs(stamp(event['date'])-stamp(t['chunk_arrival_time']))<=3600 for t in matches) or any(r['moon_record_id']==moon['id'] and abs(stamp(r['date'])-stamp(event['date']))<=3600 for r in output):continue
            if stamp(event['date'])<now-90*86400:continue
            ores=event_ores(event,catalog)
            output.append({'id':'calendar:'+str(event['event_id']),'event_id':event['event_id'],'moon_record_id':moon['id'],'moon_name':name,'date':event['date'],'volume':sum(o['volume'] for o in ores) if ores else None,'ores':[dict(o,name=catalog.name(o['id']),percent=o['volume']/sum(x['volume'] for x in ores)*100) for o in ores] if ores else [],'composition_source':'esi_calendar' if ores else 'unknown','volume_source':'esi_calendar' if ores else 'unknown','kind':'calendar_history' if event.get('historical') or stamp(event['date'])<=now else 'calendar','stale':event['stale'],'checked':event['checked'],'belt_earliest_expiry':None,'belt_latest_expiry':None,'expiry_source':'unknown'})
        current=[r for r in output if r['moon_record_id']==moon['id']]
        fresh=any(not r['stale'] and r['kind'] in ['extraction','notification'] and (r.get('fractured_at') is None) for r in current)
        calendar_only=any(not r['stale'] and r['kind']=='calendar' for r in current)
        # Empty timer data is only authoritative when a freshly authorised corp
        # resource was read. Calendar silence never proves that no drill runs.
        covered=any(not a['moon_timers']['stale'] for a in access)
        status='not_applicable' if moon['structure']=='Metenox' or not moon['enabled'] else 'scheduled' if fresh else 'calendar_only' if calendar_only else 'stale' if any(r['stale'] for r in current) else 'missing' if covered else 'unknown'
        auto=[r for r in current if r['composition_source'] in ['esi_calendar','esi_notification'] and not r['stale'] and r['kind'] in ['extraction','calendar','notification','notification_history']] if moon['structure']=='Athanor' else []
        auto.sort(key=lambda r:r['date'])
        if any(r['composition_source']=='esi_notification' for r in auto):auto=[r for r in auto if r['composition_source']=='esi_notification']
        identities={tuple((o['id'],o['percent']) for o in sorted(e['ores'],key=lambda o:o['id'])) for e in auto}
        if len(identities)>1:auto=[]
        moon_states[moon['id']]={'status':status,'composition':auto[0]['ores'] if auto else None,'composition_event_id':auto[0].get('event_id') if auto else None,'composition_source':auto[0]['composition_source'] if auto else 'manual'}
    return {'events':sorted(output,key=lambda r:(r['date'],r['moon_name'])),'moons':moon_states,'access':access,'now':now,'notification_issues':notice_issues}


def apply_notice(row,notice,catalog,lifetime):
    total=float(sum((Decimal(o.get('volume_exact',str(o['volume']))) for o in notice['ores']),Decimal(0)))
    row.update(volume=total,ores=notices.composition(notice['ores'],catalog),raw_ores=notice['ores'],composition_source='esi_notification',volume_source='esi_notification',notification_id=notice['notification_id'],notification_type=notice['type'],notification_observed_at=notice['observed_at'],notification_checked=notice['checked'],notification_stale=notice['stale'],fractured_at=notice['fractured_at'])
    row['belt_earliest_expiry']=(notice['fractured_at'] or notice['ready_time'])+lifetime*3600
    row['belt_latest_expiry']=(notice['fractured_at']+lifetime*3600) if notice['fractured_at'] else (notice['auto_time']+lifetime*3600 if notice['auto_time'] else None)
    if notice['fractured_at']:row['kind']='notification_history'


def crystal_plan(store,catalog,moon_record_id,event_id=None):
    from .moons import dashboard, preferences
    from .planner import PlanningError
    data=dashboard(store,catalog);moon=next((m for m in data['moons'] if m['id']==moon_record_id),None)
    if not moon:raise PlanningError('Ismeretlen hold.')
    if moon['structure']=='Metenox':return {'rows':[],'automatic':True,'source':'metenox'}
    prefs=preferences(store);source='30_days';event=None
    ores=[{'id':o['id'],'volume':o['volume'],'percent':o['percent']} for o in moon['ores']]
    if event_id:
        event=next((e for e in data['extractions']['events'] if e['id']==event_id and e['moon_record_id']==moon['id']),None)
        if not event:raise PlanningError('Ismeretlen kitermelés.')
        ores=event['ores'];source=event['volume_source']
    from fractions import Fraction
    from functools import reduce
    grouped={}
    if not moon['included'] or event and event['stale']:return {'rows':[],'source':source,'unavailable':True}
    for o in ores:
        if o.get('volume') is None or o['volume']<=0:continue
        ore=catalog.moon_ores[o['id']]
        crystal=next((c for c in catalog.moon_crystals.values() if c['skill_id']==ore['skill_id'] and c['variant']==prefs['crystal_variant']),None)
        if not crystal:continue
        entry=grouped.setdefault(crystal['id'],{**crystal,'volume':0,'ores':[],'weight':Fraction(0)})
        entry['volume']+=o['volume'];entry['ores'].append(ore['name'])
        # Manual percentages are exact decimal user inputs. Calendar m3 are
        # exact source quantities; do not round repeating derived percentages.
        weight=o.get('volume_exact',o['volume']) if source in ['esi_calendar','esi_notification'] else o['percent']
        entry['weight']+=Fraction(Decimal(str(weight)))
    rows=list(grouped.values())
    denominator=math.lcm(*(c['weight'].denominator for c in rows)) if rows else 1
    integers=[int(c['weight']*denominator) for c in rows]
    divisor=reduce(math.gcd,integers) if integers else 1
    total=sum((c['weight'] for c in rows),Fraction(0))
    for c,n in zip(rows,integers):
        c['count']=n//divisor;c['share']=float(c.pop('weight')/total*100)
    return {'rows':rows,'source':source,'event_id':event_id,'automatic':False,'unavailable':not rows,'total_count':sum(c['count'] for c in rows)}
