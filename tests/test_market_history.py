import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from muhely.esi import EsiError
from muhely.market_history import MarketHistory, history_expiry, normalize_history, summarize_history
from muhely.store import Store

NOW = datetime(2026, 10, 31, 10, tzinfo=timezone.utc).timestamp()


class MarketHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        self.now = NOW
        self.http = Mock(blocked_until=0)
        self.history = MarketHistory(self.store, self.http, lambda: self.now)

    def rows(self):
        return [{'date': f'2026-10-{i:02}', 'volume': i*10} for i in range(1, 31)]

    def wait(self):
        end = time.monotonic()+2
        while self.history.pending and time.monotonic() < end:
            time.sleep(.005)
        self.assertFalse(self.history.pending)

    def test_last_seven_complete_utc_days_and_normalized_weekly_average(self):
        rows = self.rows()+[{'date': '2026-10-31', 'volume': 999999}]
        result = summarize_history(rows, NOW)
        self.assertEqual([d['date'] for d in result['daily']], [f'2026-10-{i}' for i in range(24, 31)])
        self.assertEqual([d['volume'] for d in result['daily']], list(range(240, 301, 10)))
        self.assertEqual(result['month_volume'], 4650)
        self.assertEqual(result['weekly_average'], 1085)
        self.assertEqual((result['month_start'], result['month_end']), ('2026-10-01', '2026-10-30'))

    def test_utc_rollover_crosses_month_and_year_and_sparse_published_days_are_zero(self):
        now = datetime(2027, 1, 1, 0, tzinfo=timezone.utc).timestamp()
        result = summarize_history([{'date': '2026-12-31', 'volume': 30}], now)
        self.assertEqual((result['month_start'], result['month_end']), ('2026-12-02', '2026-12-31'))
        self.assertEqual(result['daily'][0]['volume'], 0)
        self.assertEqual(result['weekly_average'], 7)

    def test_unpublished_days_and_empty_history_are_unknown_not_zero(self):
        result = summarize_history(self.rows()[:-1], NOW)
        self.assertIsNone(result['daily'][-1]['volume'])
        self.assertEqual(result['weekly_average'], 1015)
        self.assertEqual((result['month_start'],result['month_end']), ('2026-09-30','2026-10-29'))
        self.assertFalse(result['complete'])
        result = summarize_history([], NOW)
        self.assertTrue(all(d['volume'] is None for d in result['daily']))
        self.assertIsNone(result['month_volume'])

    def test_daily_cache_age_expires_and_fallback_not_order_book_five_minutes(self):
        self.assertEqual(history_expiry({'Cache-Control': 'public, max-age=86400', 'Age': '100'}, NOW), NOW+86300)
        self.assertEqual(history_expiry({'Expires': 'Sat, 31 Oct 2026 11:05:00 GMT'}, NOW), NOW+3900)
        self.assertEqual(history_expiry({}, NOW), NOW+3900)
        self.assertEqual(history_expiry({}, NOW+4000), NOW+3900+86400)

    def test_public_history_cache_survives_restart_and_isolated_by_region_and_type(self):
        self.http.request.return_value = (self.rows(), {'ETag': 'history', 'Cache-Control': 'max-age=86400'})
        self.history.fetch(10000002, 35)
        self.history.fetch(10000002, 35, manual=True)
        self.assertEqual(self.http.request.call_count, 1)
        self.assertEqual(self.http.request.call_args.kwargs, {'headers': {}})
        self.assertIn('/markets/10000002/history/?type_id=35', self.http.request.call_args.args[0])
        other = MarketHistory(Store(self.tmp.name), self.http, lambda: self.now)
        self.assertEqual(other.snapshot(10000002, 35)['weekly_average'], 1085)
        self.assertIsNone(other.snapshot(10000002, 36)['checked'])
        self.assertIsNone(other.snapshot(10000058, 35)['checked'])

    def test_etag_304_and_failures_preserve_complete_snapshot(self):
        self.http.request.return_value = (self.rows(), {'ETag': 'old', 'Cache-Control': 'max-age=300'})
        self.history.fetch(10000002, 35)
        self.now += 901
        self.http.request.return_value = (None, {'Cache-Control': 'max-age=300'})
        self.history.fetch(10000002, 35)
        self.assertEqual(self.http.request.call_args.kwargs['headers'], {'If-None-Match': 'old'})
        old = self.history.cached(10000002, 35)
        self.now += 901
        self.http.request.side_effect = EsiError('offline')
        self.history.start(10000002, 35)
        self.wait()
        self.assertEqual(self.history.cached(10000002, 35), old)
        result = self.history.snapshot(10000002, 35)
        self.assertTrue(result['stale'])
        self.assertEqual(result['error'], 'offline')
        calls = self.http.request.call_count
        self.history.start(10000002, 35)
        self.assertEqual(self.http.request.call_count, calls)

    def test_manual_bypasses_app_spacing_but_never_valid_esi_cache(self):
        self.http.request.return_value = (self.rows(), {'Cache-Control': 'max-age=300'})
        self.history.fetch(10000002, 35)
        self.now += 301
        self.history.start(10000002, 35)
        self.assertFalse(self.history.pending)
        self.history.start(10000002, 35, manual=True)
        self.wait()
        self.assertEqual(self.http.request.call_count, 2)
        self.history.start(10000002, 35, manual=True)
        self.assertEqual(self.http.request.call_count, 2)

    def test_invalid_payload_never_saved_as_zero_volume(self):
        bad = [None, {}, [None], [{'date': 'invalid', 'volume': 5}],
               [{'date': '2026-10-30', 'volume': True}], [{'date': '2026-10-30', 'volume': -1}],
               [{'date': '2026-10-30', 'volume': 1.5}], self.rows()*2]
        for rows in bad:
            with self.subTest(rows=rows), self.assertRaises(EsiError):
                normalize_history(rows)


if __name__ == '__main__':
    unittest.main()
