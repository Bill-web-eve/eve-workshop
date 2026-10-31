"""Public regional traded volume. ESI does not expose order-side/station history."""
from datetime import date, datetime, time as daytime, timedelta, timezone
from email.utils import parsedate_to_datetime
import re
import threading
import time

from .esi import ESI, EsiError, Transport
from .refresh_policy import AUTO_SECONDS, RefreshPolicy


def history_expiry(headers, now):
    h = {k.lower(): v for k, v in headers.items()}
    match = re.search(r'(?:^|,)\s*max-age\s*=\s*"?(\d+)', h.get('cache-control', '').lower())
    if match:
        try:
            return now + max(0, int(match[1]) - max(0, int(h.get('age', '0'))))
        except ValueError:
            pass
    if h.get('expires'):
        try:
            return max(now, parsedate_to_datetime(h['expires']).timestamp())
        except (ValueError, TypeError, OverflowError):
            pass
    # The endpoint updates daily at 11:05 UTC, not with the order-book cache.
    current = datetime.fromtimestamp(now, timezone.utc)
    expiry = datetime.combine(current.date(), daytime(11, 5), timezone.utc)
    if expiry <= current:
        expiry += timedelta(days=1)
    return expiry.timestamp()


def normalize_history(data):
    if not isinstance(data, list):
        raise EsiError('Hibás piaci forgalmi adatok.')
    rows = {}
    for row in data:
        if not isinstance(row, dict):
            raise EsiError('Hibás piaci forgalmi adatok.')
        day, volume = row.get('date'), row.get('volume')
        try:
            valid_date = isinstance(day, str) and date.fromisoformat(day).isoformat() == day
        except ValueError:
            valid_date = False
        if not valid_date or type(volume) is not int or not 0 <= volume <= 2**53-1 or day in rows:
            raise EsiError('Hibás piaci forgalmi adatok.')
        rows[day] = volume
    return [{'date': day, 'volume': rows[day]} for day in sorted(rows)]


def summarize_history(rows, now):
    today = datetime.fromtimestamp(now, timezone.utc).date()
    end = today - timedelta(days=1)
    values = {r['date']: r['volume'] for r in rows if r['date'] < today.isoformat()}
    latest = max(values, default=None)
    month_end = date.fromisoformat(latest) if latest else end
    start = month_end - timedelta(days=29)
    def volume(day):
        # An omitted trading day inside the published period has no trades;
        # an unpublished day is unknown, never a manufactured zero.
        return values.get(day.isoformat(), 0) if latest and day.isoformat() <= latest else None
    daily = [{'date': (month_end-timedelta(days=i)).isoformat(), 'volume': volume(month_end-timedelta(days=i))}
             for i in range(6, -1, -1)]
    complete = latest is not None and latest >= end.isoformat()
    total = sum(volume(start+timedelta(days=i)) or 0 for i in range(30)) if latest else None
    return {'daily': daily, 'month_start': start.isoformat(), 'month_end': month_end.isoformat(),
            'month_volume': total, 'weekly_average': total*7/30 if total is not None else None,
            'complete': complete, 'latest_date': latest, 'timezone': 'UTC'}


class MarketHistory:
    def __init__(self, store, http=None, clock=None):
        self.store = store
        self.http = http or Transport()
        self.clock = clock or time.time
        self.policy = RefreshPolicy(store)
        self.lock = threading.RLock()
        self.pending = set()
        self.errors = {}

    def cached(self, region, tid):
        row = self.store.universe_cached('market-history:'+str(region), tid)
        return row['data'] if row else None

    def fetch(self, region, tid, manual=False):
        now = self.clock()
        old = self.cached(region, tid)
        if old and old['expires'] > now:
            return old
        key = f'market-history:{region}:{tid}'
        if not self.policy.claim([key], manual, now):
            return old
        headers = {'If-None-Match': old['etag']} if old and old.get('etag') else {}
        data, headers = self.http.request(f'{ESI}/markets/{region}/history/?type_id={tid}', headers=headers)
        h = {k.lower(): v for k, v in headers.items()}
        if data is None:
            if not old:
                raise EsiError('Üres piaci forgalmi válasz korábbi adat nélkül.')
            rows = old['rows']
        else:
            rows = normalize_history(data)
        result = {'rows': rows, 'checked': now, 'expires': history_expiry(headers, now),
                  'etag': h.get('etag') or (old or {}).get('etag')}
        self.store.save_universe_cache('market-history:'+str(region), tid, result, now)
        return result

    def start(self, region, tid, manual=False):
        key = (region, tid)
        with self.lock:
            old = self.cached(region, tid)
            now = self.clock()
            if key in self.pending or old and old['expires'] > now:
                return
            if not manual and self.policy.next_at([f'market-history:{region}:{tid}']) > now:
                return
            self.pending.add(key)
            self.errors.pop(key, None)
        threading.Thread(target=self._work, args=(region, tid, manual), daemon=True).start()

    def _work(self, region, tid, manual):
        try:
            self.fetch(region, tid, manual)
        except Exception as exc:
            with self.lock:
                self.errors[(region, tid)] = str(exc) if isinstance(exc, EsiError) else 'A piaci forgalom nem frissült.'
        finally:
            with self.lock:
                self.pending.discard((region, tid))

    def snapshot(self, region, tid):
        now = self.clock()
        with self.lock:
            old = self.cached(region, tid)
            result = {'region_id': region, 'type_id': tid, 'scope': 'region', 'order_side': 'all',
                      'running': (region, tid) in self.pending, 'error': self.errors.get((region, tid)),
                      'checked': old['checked'] if old else None, 'stale': bool(old and old['expires'] <= now),
                      'next_refresh': max((old or {}).get('expires', 0), self.policy.next_at([f'market-history:{region}:{tid}']))}
        return {**result, **summarize_history(old['rows'] if old else [], now)}
