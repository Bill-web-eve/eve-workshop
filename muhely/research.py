"""Daily R&D snapshots and explicitly estimated datacore balances. Read-only ESI."""
from collections import defaultdict
from decimal import Decimal, ROUND_FLOOR
import math
import time

from . import progress
from .esi import ESI, RESEARCH_SCOPES, EsiError, AuthenticationError
from .extractions import stamp, cache_expiry
from .planner import PlanningError, integer

DAY = 86400
RP_PER_DATACORE = 100
REDEMPTION_ISK = 10000


def validate(data):
    if not isinstance(data, list):
        raise EsiError('Hibás research agent adat; a korábbi adatok megmaradtak.')
    seen = set()
    for row in data:
        if not isinstance(row, dict):
            raise EsiError('Hibás research agent adat; a korábbi adatok megmaradtak.')
        for key in ['agent_id', 'skill_type_id']:
            value = row.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or not 0 < value < 2**53:
                raise EsiError('Hibás research agent azonosító.')
        for key in ['points_per_day', 'remainder_points']:
            value = row.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 10**12:
                raise EsiError('Hibás research pontadat.')
        if stamp(row.get('started_at')) is None or row['agent_id'] in seen:
            raise EsiError('Hibás vagy ismétlődő research agent adat.')
        seen.add(row['agent_id'])


def resource(eve, cid, token, now=None):
    now = time.time() if now is None else now
    old = eve.store.snapshot(cid, 'research')
    progress.resource('Research agentek', bool(old and old['expires'] > now))
    if old and old['expires'] > now:
        return old
    body, headers = eve.http.request(f'{ESI}/characters/{cid}/agents_research', token=token,
                                    headers={'If-None-Match': old['etag']} if old and old.get('etag') else {})
    if body is None:
        if not old:
            raise EsiError('Hiányzó korábbi research adat.')
        body = old['data']
    validate(body)
    return {'data': body, 'fetched': now, 'expires': cache_expiry(headers, now),
            'etag': {k.lower(): v for k, v in headers.items()}.get('etag') or (old or {}).get('etag')}


def datacore(catalog, skill_id):
    # Published SDE names differ for the Amarr and Gallente datacores.
    field = catalog.name(skill_id)
    field = {'Amarr Starship Engineering': 'Amarrian Starship Engineering',
             'Gallente Starship Engineering': 'Gallentean Starship Engineering'}.get(field, field)
    name = 'Datacore - ' + field
    return next((r['id'] for r in catalog.types.values() if r['name'] == name and r.get('published')), None)


def agent_names(eve, ids, now):
    needed = []
    for aid in ids:
        old = eve.store.universe_cached('research-agent', aid)
        if not old or old['fetched'] + 90 * DAY <= now:
            needed.append(aid)
    for offset in range(0, len(needed), 1000):
        batch = needed[offset:offset + 1000]
        progress.resource('Research agentek nevei')
        rows, _ = eve.http.request(ESI + '/universe/names/', json_body=batch)
        if not isinstance(rows, list):
            raise EsiError('A research agentek nevei nem frissültek.')
        found = {r.get('id'): r.get('name') for r in rows if isinstance(r, dict)}
        for aid in batch:
            if isinstance(found.get(aid), str) and found[aid].strip():
                eve.store.save_universe_cache('research-agent', aid, {'name': found[aid]}, now)


def sync(eve, catalog, market=None, manual=False):
    if not eve.sync_lock.acquire(blocking=False):
        raise EsiError('Az EVE-frissítés már folyamatban van.')
    results = []
    try:
        scopes = eve.granted_scopes()
        for char in progress.items(eve.store.characters()):
            cid = char['id']
            if not set(RESEARCH_SCOPES).issubset(scopes.get(cid, [])):
                results.append({'id': cid, 'kind': 'research', 'ok': False, 'warning': False, 'needs_auth': True})
                continue
            try:
                token = eve.token(cid, required_scopes=RESEARCH_SCOPES)
                snap = resource(eve, cid, token)
                eve.store.save_snapshots(cid, {'research': snap}, domain='research')
                results.append({'id': cid, 'kind': 'research', 'ok': True})
            except EsiError as error:
                eve.store.resource_error(cid, 'research', str(error), isinstance(error, AuthenticationError))
                results.append({'id': cid, 'kind': 'research', 'ok': False, 'error': str(error)})
        ids = set()
        prices = set()
        for char in eve.store.characters():
            snap = eve.store.snapshot(char['id'], 'research')
            for row in (snap or {}).get('data', []):
                ids.add(row['agent_id'])
                tid = datacore(catalog, row['skill_type_id'])
                if tid:
                    prices.add(tid)
        try:
            agent_names(eve, sorted(ids), time.time())
        except EsiError as error:
            results.append({'kind': 'research_names', 'ok': False, 'error': str(error)})
        if market:
            for tid in progress.items(sorted(prices), name=lambda tid: catalog.name(tid)):
                progress.resource('Datacore-ok Jita-árai')
                try:
                    market.quote(tid, manual=manual)
                    results.append({'id': tid, 'kind': 'research_price', 'ok': True})
                except EsiError as error:
                    results.append({'id': tid, 'kind': 'research_price', 'ok': False, 'error': str(error)})
        return results
    finally:
        eve.sync_lock.release()


def dashboard(store, catalog, at=None, character_id=None, access_scopes=None, now=None):
    now = time.time() if now is None else now
    try:
        at = float(at) if at is not None else now
    except (ValueError, TypeError):
        raise PlanningError('Érvénytelen research előrejelzési időpont.') from None
    if not math.isfinite(at) or not now - 300 <= at <= now + 5 * 366 * DAY:
        raise PlanningError('A research előrejelzés időpontja mostantól legfeljebb öt év lehet.')
    cid = integer(character_id, 'Karakter', 2**31 - 1, 1) if character_id else None
    chars = store.characters()
    if cid and cid not in {c['id'] for c in chars}:
        raise PlanningError('Ismeretlen karakter.')
    access, rows = [], []
    grouped = defaultdict(lambda: {'quantity': 0, 'rp_per_day': Decimal(0)})
    for char in chars:
        snap = store.snapshot(char['id'], 'research')
        status = store.resource_status(char['id'], 'research') or {}
        authorized = set(RESEARCH_SCOPES).issubset((access_scopes or {}).get(char['id'], []))
        access.append({'id': char['id'], 'name': char['name'], 'authorized': authorized,
                       'needs_auth': not authorized, 'error': status.get('error'),
                       'checked_at': (snap or {}).get('fetched'),
                       'next_refresh': max((snap or {}).get('fetched', 0) + DAY, (snap or {}).get('expires', 0)) if snap else None})
        if cid and char['id'] != cid:
            continue
        for agent in (snap or {}).get('data', []):
            start = stamp(agent['started_at'])
            elapsed = Decimal(str(max(0, at - start))) / DAY
            rp = Decimal(str(agent['remainder_points'])) + Decimal(str(agent['points_per_day'])) * elapsed
            quantity = int((rp / RP_PER_DATACORE).to_integral_value(rounding=ROUND_FLOOR))
            if quantity > 2**53-1:
                raise PlanningError('A research előrejelzés mennyisége túl nagy.')
            tid = datacore(catalog, agent['skill_type_id'])
            name = store.universe_cached('research-agent', agent['agent_id'])
            rows.append({'character_id': char['id'], 'character_name': char['name'], 'agent_id': agent['agent_id'],
                         'agent_name': name['data']['name'] if name else str(agent['agent_id']),
                         'skill_id': agent['skill_type_id'], 'field': catalog.name(agent['skill_type_id']),
                         'datacore_id': tid, 'datacore_name': catalog.name(tid) if tid else None,
                         'rp': format(rp.quantize(Decimal('0.01'), rounding=ROUND_FLOOR), '.2f'), 'rp_per_day': agent['points_per_day'], 'quantity': quantity,
                         'redemption_cost': quantity * REDEMPTION_ISK, 'checked_at': snap['fetched']})
            group = grouped[tid, agent['skill_type_id']]
            group['quantity'] += quantity
            group['rp_per_day'] += Decimal(str(agent['points_per_day']))
    totals = [{'id': tid, 'name': catalog.name(tid) if tid else catalog.name(skill),
               'quantity': group['quantity'], 'rp_per_day': str(group['rp_per_day'])}
              for (tid, skill), group in sorted(grouped.items(), key=lambda kv: catalog.name(kv[0][1]))]
    if sum(r['quantity'] for r in rows) * REDEMPTION_ISK > 2**53-1:
        raise PlanningError('A research előrejelzés mennyisége túl nagy.')
    return {'characters': access, 'rows': rows, 'totals': totals, 'at': at,
            'quantity': sum(r['quantity'] for r in rows), 'rp_per_day': str(sum((Decimal(str(r['rp_per_day'])) for r in rows), Decimal(0))),
            'redemption_cost': sum(r['redemption_cost'] for r in rows), 'rp_per_datacore': RP_PER_DATACORE,
            'scopes': RESEARCH_SCOPES, 'calculated_at': now}
