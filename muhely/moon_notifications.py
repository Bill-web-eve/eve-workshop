"""Read the restricted scalar/map subset of CCP moon notifications, never YAML code."""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
import json
import math
import re

SCOPE='esi-characters.read_notifications.v1'
TYPES={'MoonminingExtractionStarted','MoonminingExtractionFinished','MoonminingAutomaticFracture','MoonminingLaserFired','MoonminingExtractionCancelled'}


def text_fields(text):
    if not isinstance(text,str) or len(text)>200000:raise ValueError('invalid_text')
    fields={};ore_lines=[];in_ores=False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        top=re.fullmatch(r'([A-Za-z][A-Za-z0-9_]*):\s*(.*?)\s*',line)
        if top:
            key,value=top.groups()
            if key in fields:raise ValueError('duplicate_field')
            fields[key]=value;in_ores=key=='oreVolumeByType'
            if in_ores and value:
                if not value.startswith('{') or not value.endswith('}'):raise ValueError('invalid_ore_map')
                ore_lines.extend(value[1:-1].split(','))
        elif in_ores and line[:1].isspace():ore_lines.append(line.strip())
    ores={}
    for line in ore_lines:
        match=re.fullmatch(r"\s*['\"]?(\d+)['\"]?\s*:\s*([+]?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)\s*",line)
        if not match:raise ValueError('invalid_ore_map')
        key=int(match[1]);amount=Decimal(match[2])
        if key in ores or not amount.is_finite() or not 0<=amount<=10**12:raise ValueError('invalid_ore_volume')
        if amount:ores[key]=format(amount,'f')
    return fields,ores


def field_id(fields,key):
    value=fields.get(key,'').strip("'\"")
    if not re.fullmatch(r'\d+',value) or not 0<int(value)<2**53:raise ValueError('invalid_'+key)
    return int(value)


def eve_time(value):
    if value is None:return None
    value=str(value).strip("'\"")
    try:
        if re.fullmatch(r'\d+',value):
            n=int(value)
            seconds=float(Decimal(n)/10_000_000-11644473600) if n>10**15 else float(n) if 10**8<n<10**11 else None
            if seconds is None:return None
            date=datetime.fromtimestamp(seconds,timezone.utc)
        else:
            date=datetime.fromisoformat(value.replace('Z','+00:00'))
            if date.tzinfo is None:return None
        return date.timestamp() if 2000<=date.year<=2200 else None
    except (ValueError,OverflowError,OSError):return None


def parse(row,catalog):
    from .extractions import positive,stamp
    if not isinstance(row,dict) or row.get('type') not in TYPES:return None
    if not positive(row.get('notification_id')) or stamp(row.get('timestamp')) is None:raise ValueError('invalid_notification')
    fields,amounts=text_fields(row.get('text'))
    result={'notification_id':row['notification_id'],'type':row['type'],'timestamp':stamp(row['timestamp']),
            'moon_id':field_id(fields,'moonID'),'structure_id':field_id(fields,'structureID'),
            'ready_time':eve_time(fields.get('readyTime')),'auto_time':eve_time(fields.get('autoTime')),'ores':[]}
    if row['type']=='MoonminingExtractionStarted' and (result['ready_time'] is None or result['ready_time']<=result['timestamp'] or result['ready_time']-result['timestamp']>60*86400):raise ValueError('invalid_ready_time')
    if 'autoTime' in fields and result['auto_time'] is None:raise ValueError('invalid_auto_time')
    if result['ready_time'] and result['auto_time'] and result['auto_time']<result['ready_time']:raise ValueError('invalid_auto_time')
    for tid,volume in amounts.items():
        variant=getattr(catalog,'moon_variants',{}).get(tid)
        if not variant and tid in catalog.moon_ores:variant=dict(catalog.moon_ores[tid],base_id=tid)
        if not variant or variant['base_id'] not in catalog.moon_ores or variant['volume']<1:raise ValueError('unknown_or_compressed_ore')
        result['ores'].append({'id':variant['base_id'],'type_id':tid,'name':variant['name'],'volume':float(volume),'volume_exact':volume})
    if row['type']!='MoonminingExtractionCancelled' and not result['ores']:raise ValueError('missing_ore_volumes')
    return result


def composition(ores,catalog):
    grouped={};total=sum((Decimal(o.get('volume_exact',str(o['volume']))) for o in ores),Decimal(0))
    for ore in ores:
        group=grouped.setdefault(ore['id'],{'id':ore['id'],'name':catalog.name(ore['id']),'volume':0,'volume_exact':Decimal(0),'variants':[]})
        group['volume_exact']+=Decimal(ore.get('volume_exact',str(ore['volume'])));group['variants'].append(ore)
    for group in grouped.values():
        group['percent']=float(group['volume_exact']/total*100);group['volume']=float(group['volume_exact']);group['volume_exact']=format(group['volume_exact'],'f')
    return list(grouped.values())


def cycles(store,catalog,now):
    """Dedupe notifications across readers, then replay each structure's lifecycle."""
    observed={};issues=[]
    for char in store.characters():
        snap=store.snapshot(char['id'],'moon_notifications')
        if not snap:continue
        status=store.resource_status(char['id'],'moon_notifications') or {}
        stale=snap['expires']<=now or bool(status.get('error'))
        for row in snap['data']['notifications']:
            if row['notification_id'] in observed and (observed[row['notification_id']]['checked']>snap['fetched'] or observed[row['notification_id']]['checked']==snap['fetched'] and (not observed[row['notification_id']]['stale'] or stale)):continue
            try:
                event=parse(row,catalog)
                if event:observed[row['notification_id']]={**event,'checked':snap['fetched'],'stale':stale}
            except (ValueError,InvalidOperation):issues.append({'character_id':char['id'],'notification_id':row.get('notification_id'),'reason':'unreadable_notification'})
    structures=defaultdict(list);seen=set()
    for row in sorted(observed.values(),key=lambda r:(r['checked'],not r['stale']),reverse=True):
        signature=(row['type'],row['moon_id'],row['structure_id'],row['timestamp'],row['ready_time'],tuple(sorted((o['type_id'],o['volume_exact']) for o in row['ores'])))
        if signature in seen:continue
        seen.add(signature)
        structures[(row['moon_id'],row['structure_id'])].append(row)
    output=[]
    for key,events in structures.items():
        items=[]
        for event in sorted(events,key=lambda e:(e['timestamp'],e['notification_id'])):
            kind=event['type'];t=event['timestamp']
            if kind=='MoonminingExtractionStarted':
                existing=next((c for c in items if c['ready_time']==event['ready_time']),None)
                if existing:
                    if event['checked']>existing['checked']:existing.update(checked=event['checked'],stale=event['stale'])
                    continue
                cycle={**event,'start_time':t,'observed_at':t,'cancelled':False,'fractured_at':None};items.append(cycle)
            else:
                candidates=[c for c in items if not c['cancelled'] and c['ready_time'] is not None and (c['start_time'] or c['ready_time'])<=t and not c['fractured_at']]
                if kind=='MoonminingExtractionFinished':candidates=[c for c in candidates if abs(c['ready_time']-t)<=3600 or c['auto_time'] and c['auto_time']==event['auto_time']]
                if kind in ['MoonminingLaserFired','MoonminingAutomaticFracture']:candidates=[c for c in candidates if c['ready_time']<=t+60]
                cycle=max(candidates,key=lambda c:c['start_time'] or c['ready_time']) if candidates else None
                if not cycle:
                    if kind=='MoonminingExtractionCancelled':
                        items.append({**event,'start_time':None,'ready_time':None,'observed_at':t,'cancelled':True,'fractured_at':None});continue
                    cycle={**event,'start_time':None,'ready_time':t,'observed_at':t,'cancelled':False,'fractured_at':None};items.append(cycle)
                if kind=='MoonminingExtractionCancelled':cycle['cancelled']=True
                else:
                    cycle.update(ores=event['ores'],type=kind,observed_at=t,notification_id=event['notification_id'])
                    if kind=='MoonminingExtractionFinished' and event['auto_time']:cycle['auto_time']=event['auto_time']
                    if kind in ['MoonminingLaserFired','MoonminingAutomaticFracture']:cycle['fractured_at']=t
                cycle.update(checked=event['checked'],stale=event['stale'])
        output.extend(items)
    return output,issues
