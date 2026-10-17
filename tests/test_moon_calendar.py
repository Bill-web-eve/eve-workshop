import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from muhely.moon_calendar import calendar, feed_token
from muhely.server import App, Server
from muhely.store import Store

ROOT = Path(__file__).resolve().parents[1]


class CalendarTests(unittest.TestCase):
    def event(self, **changes):
        return dict(moon_record_id='moon-one', moon_name='Árvíztűrő VI - Moon 7',
                    date='2026-10-18T12:30:00+02:00', volume=1000000,
                    ores=[{'name': 'Zeolites', 'volume': 750000}], stale=False,
                    volume_source='duration_estimate') | changes

    def test_calendar_utc_identity_and_updated_contents(self):
        event = self.event()
        first = calendar([event, event], now=100)
        self.assertEqual(first.count(b'BEGIN:VEVENT'), 1)
        self.assertIn(b'DTSTART:20261018T103000Z', first)
        self.assertIn(b'DURATION:PT1M', first)
        self.assertIn('Árvíztűrő VI - Moon 7 · Extraction'.encode(), first)
        updated = calendar([dict(event, volume=2000000, id='other-source')], now=200)
        uid = lambda raw: next(line for line in raw.split(b'\r\n') if line.startswith(b'UID:'))
        self.assertEqual(uid(first), uid(updated))
        self.assertNotEqual(first, updated)
        self.assertIn(b'Estimated from duration', updated)
        self.assertIn('Kitermelés'.encode(), calendar([event], 'hu'))

    def test_ical_escaping_line_folding_and_utf8(self):
        data = calendar([self.event(moon_name='ő' * 140 + ',x;y\\z\r\nBEGIN:VEVENT')])
        data.decode('utf-8')
        self.assertTrue(data.endswith(b'END:VCALENDAR\r\n'))
        self.assertTrue(all(len(line) <= 75 for line in data.split(b'\r\n')))
        unfolded = data.replace(b'\r\n ', b'').decode()
        self.assertIn(r'\,x\;y\\z\nBEGIN:VEVENT', unfolded)
        self.assertEqual(data.count(b'\r\nBEGIN:VEVENT\r\n'), 1)

    def test_empty_feed_is_valid_and_tokens_survive_restart_but_can_be_revoked(self):
        self.assertNotIn(b'BEGIN:VEVENT', calendar([]))
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            self.assertIsNone(feed_token(store))
            first = feed_token(store, 'enable')
            self.assertGreaterEqual(len(first), 40)
            self.assertEqual(feed_token(Store(folder), 'enable'), first)
            self.assertNotIn(first, json.dumps(store.settings()))
            self.assertNotEqual(feed_token(store, 'reset'), first)
            self.assertIsNone(feed_token(store, 'disable'))


class CalendarRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = App(self.tmp.name, ROOT/'data/catalog.sqlite3', port=0)
        self.server = Server(self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, body=None, authenticated=True, **headers):
        conn = http.client.HTTPConnection('127.0.0.1', self.app.port, timeout=10)
        defaults = {'Cookie': 'eve_session=' + self.app.cookie} if authenticated else {}
        if body is not None:
            defaults.update({'Content-Type': 'application/json', 'Origin': self.app.origin,
                             'X-CSRF-Token': self.app.csrf})
        conn.request('GET' if body is None else 'POST', path,
                     body=None if body is None else json.dumps(body), headers={**defaults, **headers})
        response = conn.getresponse()
        data, status, h = response.read(), response.status, dict(response.getheaders())
        conn.close()
        return status, json.loads(data) if 'application/json' in h.get('Content-Type', '') else data, h

    def test_subscription_is_opt_in_local_and_separate_from_session(self):
        self.assertFalse(self.request('/api/moons/calendar')[1]['enabled'])
        self.assertEqual(self.request('/api/moons/calendar', {'action': 'enable'}, Origin='http://evil.invalid')[0], 403)
        self.assertEqual(self.request('/api/moons/calendar', {'action': 'enable'}, authenticated=False)[0], 403)
        status, feed, _ = self.request('/api/moons/calendar', {'action': 'enable'})
        self.assertEqual(status, 200)
        path = feed['url'].removeprefix(self.app.origin)
        self.assertTrue(feed['webcal_url'].startswith('webcal://127.0.0.1:'))
        status, data, headers = self.request(path, authenticated=False)
        self.assertEqual(status, 200)
        self.assertIn(b'BEGIN:VCALENDAR', data)
        self.assertIn('text/calendar', headers['Content-Type'])
        self.assertEqual(self.request(path, authenticated=False, Host='evil.invalid')[0], 403)
        self.assertEqual(self.request('/api/state', authenticated=False)[0], 403)
        self.assertEqual(self.request('/api/moons/calendar.ics', authenticated=False)[0], 403)
        self.assertEqual(self.request('/calendar/moons/wrong.ics', authenticated=False)[0], 404)
        self.request('/api/moons/calendar', {'action': 'reset'})
        self.assertEqual(self.request(path, authenticated=False)[0], 404)
        new = self.request('/api/moons/calendar')[1]['url'].removeprefix(self.app.origin)
        self.request('/api/moons/calendar', {'action': 'disable'})
        self.assertEqual(self.request(new, authenticated=False)[0], 404)

    def test_export_filters_disabled_moons_and_metenox_and_reflects_new_snapshot(self):
        moons = [{'id': 'ath', 'enabled': True, 'structure': 'Athanor'},
                 {'id': 'off', 'enabled': False, 'structure': 'Athanor'},
                 {'id': 'met', 'enabled': True, 'structure': 'Metenox'}]
        event = {'moon_record_id': 'ath', 'moon_name': 'Test Moon', 'date': '2026-10-18T10:00:00Z', 'ores': []}
        with patch.object(self.app.store, 'moon_records', return_value=moons), patch('muhely.moon_calendar.report') as report:
            report.return_value = {'events': [dict(event, moon_record_id=m['id'], moon_name=m['id']) for m in moons]}
            status, data, headers = self.request('/api/moons/calendar.ics?lang=hu')
            self.assertEqual(status, 200)
            self.assertIn('attachment', headers['Content-Disposition'])
            self.assertEqual(data.count(b'BEGIN:VEVENT'), 1)
            self.assertIn('ath · Kitermelés'.encode(), data)
            report.return_value = {'events': []}
            self.assertNotIn(b'BEGIN:VEVENT', self.request('/api/moons/calendar.ics')[1])
