"""Local, read-only iCalendar subscription using cached extraction data."""
from datetime import datetime, timezone
import hashlib
import secrets
import time

from .extractions import report, stamp


def feed_token(store, action=None):
    # Separate from exported settings and OAuth credentials. Never bundled.
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS local_calendar (id INTEGER PRIMARY KEY, token TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT token FROM local_calendar WHERE id=1').fetchone()
        token = row['token'] if row else None
        if action == 'disable':
            db.execute('DELETE FROM local_calendar WHERE id=1')
            return None
        if action == 'reset' or action == 'enable' and not token:
            token = secrets.token_urlsafe(32)
            db.execute('INSERT OR REPLACE INTO local_calendar VALUES (1,?)', (token,))
        return token


def feed_status(store, origin):
    token = feed_token(store)
    url = origin + '/calendar/moons/' + token + '.ics' if token else None
    return {'enabled': bool(token), 'url': url,
            'webcal_url': url.replace('http://', 'webcal://', 1) if url else None}


def text(value):
    return str(value).replace('\\', '\\\\').replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')


def utc(value):
    return datetime.fromtimestamp(value, timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def fold(line):
    # The 75-octet limit includes the continuation space; never split UTF-8.
    parts, current = [], ''
    for char in line:
        if len((current + char).encode('utf-8')) > 75:
            parts.append(current)
            current = ' '
        current += char
    return '\r\n'.join(parts + [current])


def calendar(events, language='en', now=None):
    hu = language == 'hu'
    now = time.time() if now is None else now
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//EVE Workshop//Moon Calendar//EN',
             'CALSCALE:GREGORIAN', 'X-WR-CALNAME:EVE · ' + ('Holdkitermelések' if hu else 'Moon extractions'),
             'REFRESH-INTERVAL;VALUE=DURATION:PT1H', 'X-PUBLISHED-TTL:PT1H']
    seen = set()
    for event in events:
        arrival = stamp(event.get('date'))
        if arrival is None:
            continue
        # Timer, notification and calendar representations share one identity.
        identity = f"{event['moon_record_id']}:{int(arrival)}"
        uid = hashlib.sha256(identity.encode()).hexdigest() + '@eve-workshop.local'
        if uid in seen:
            continue
        seen.add(uid)
        description = [('A holdkőzet megérkezése; a naptár helyi időzónában mutatja.' if hu else
                        'Moon chunk arrival; displayed in your calendar’s local time zone.')]
        if event.get('timing_source')=='esi_calendar':
            description.append('Kitermelési időpont forrása: ESI naptáresemény.' if hu else 'Extraction time source: ESI calendar event.')
        if event.get('volume') is not None:
            description.append(('Érctérfogat' if hu else 'Ore volume') + f": {event['volume']:,.0f} m³")
        for ore in event.get('raw_ores') or event.get('ores', []):
            description.append(f"{ore['name']}: {ore['volume']:,.0f} m³")
        if event.get('natural_decay_time'):
            description.append(('Automatikus széttörés' if hu else 'Automatic fracture') + ': ' + event['natural_decay_time'])
        for key, label in [('belt_earliest_expiry', 'Becsült legkorábbi érceltűnés' if hu else 'Estimated earliest ore expiry'),
                           ('belt_latest_expiry', 'Becsült legkésőbbi érceltűnés' if hu else 'Estimated latest ore expiry')]:
            if event.get(key) is not None:
                description.append(label + ': ' + datetime.fromtimestamp(event[key], timezone.utc).isoformat())
        source = event.get('volume_source', 'unknown')
        description.append(('Ércadat forrása' if hu else 'Ore data source') + ': ' + {
            'esi_notification': 'ESI értesítés' if hu else 'ESI notification',
            'esi_calendar': 'ESI naptár' if hu else 'ESI calendar',
            'duration_estimate': 'Becslés időtartamból és kézi arányokból' if hu else 'Estimated from duration and manual proportions',
        }.get(source, 'Ismeretlen' if hu else 'Unknown'))
        if event.get('stale'):
            description.append('Régi adat · EVE-frissítés szükséges.' if hu else 'Stale data · refresh EVE data.')
        lines.extend(['BEGIN:VEVENT', 'UID:' + uid, 'DTSTAMP:' + utc(now),
                      'DTSTART:' + utc(arrival), 'DURATION:PT1M', 'TRANSP:TRANSPARENT',
                      'SUMMARY:' + text(event['moon_name'] + (' · Kitermelés' if hu else ' · Extraction')),
                      'DESCRIPTION:' + text('\n'.join(description)), 'END:VEVENT'])
    lines.append('END:VCALENDAR')
    return ('\r\n'.join(fold(line) for line in lines) + '\r\n').encode('utf-8')


def export(store, catalog, language='en'):
    included = {m['id'] for m in store.moon_records() if m['enabled'] and m['structure'] == 'Athanor'}
    events = [e for e in report(store, catalog)['events'] if e['moon_record_id'] in included]
    return calendar(events, language)
