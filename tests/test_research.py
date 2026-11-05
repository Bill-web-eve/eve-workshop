from datetime import datetime, timezone
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from muhely import research
from muhely.catalog import Catalog
from muhely.esi import ALL_SCOPES, INDUSTRY_SCOPES, RESEARCH_SCOPES, EveConnection, EsiError
from muhely.planner import PlanningError
from muhely.refresh_policy import RefreshPolicy
from muhely.server import App
from muhely.store import Store
import test_server as server_tests

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 5, 15, 0, tzinfo=timezone.utc).timestamp()


def agent(aid=3001, remainder=99, rate=100, skill=11442, days=0):
    return {'agent_id': aid, 'skill_type_id': skill, 'points_per_day': rate,
            'remainder_points': remainder,
            'started_at': datetime.fromtimestamp(NOW-days*86400, timezone.utc).isoformat()}


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.catalog = Catalog(ROOT/'data/catalog.sqlite3')
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        for cid in [1, 2]: self.store.add_character(cid, f'Pilot {cid}')
    def seed(self, cid, rows):
        self.store.save_snapshots(cid, {'research': {'data': rows, 'fetched': NOW, 'expires': NOW+3600, 'etag': 'one'}}, domain='research')
    def view(self, **kwargs):
        return research.dashboard(self.store, self.catalog, access_scopes={1: RESEARCH_SCOPES, 2: RESEARCH_SCOPES}, now=NOW, **kwargs)
    def test_rounds_each_owner_and_agent_separately_then_sums_datacores(self):
        self.seed(1, [agent(3001), agent(3002)])
        self.seed(2, [agent(3001, remainder=101)])
        d = self.view()
        self.assertEqual([r['quantity'] for r in d['rows']], [0, 0, 1])
        self.assertEqual(d['quantity'], 1); self.assertEqual(d['redemption_cost'], 10000)
        self.assertEqual(d['totals'][0]['quantity'], 1)
        self.assertEqual(self.view(at=NOW+86400)['quantity'], 4)
        self.assertEqual(self.view(character_id=1)['quantity'], 0)
    def test_exact_decimal_threshold_and_hundreds_not_old_field_multipliers(self):
        self.seed(1, [agent(remainder=63.89, rate=114.73, skill=11454)])
        d = self.view(at=NOW+86400)
        self.assertEqual(d['rows'][0]['rp'], '178.62')
        self.assertEqual(d['quantity'], 1)
        self.assertEqual(d['rows'][0]['datacore_id'], 25887)
        for skill, tid in [(11444, 20421), (11450, 20410)]:
            self.assertEqual(research.datacore(self.catalog, skill), tid)
        self.seed(1, [agent(remainder=99.999, rate=0)])
        self.assertEqual(self.view()['quantity'], 0)
    def test_unknown_mapping_is_explicit_and_no_unproven_27600_cap_is_applied(self):
        self.seed(1, [agent(remainder=27800, rate=100, skill=99999999)])
        d = self.view(at=NOW+86400)
        self.assertIsNone(d['rows'][0]['datacore_id'])
        self.assertEqual(d['rows'][0]['rp'], '27900.00'); self.assertEqual(d['quantity'], 279)
    def test_invalid_payload_never_replaces_complete_character_snapshot(self):
        self.seed(1, [agent()])
        eve = EveConnection(self.store, vault=Mock(), transport=Mock())
        eve.token = Mock(return_value='test'); eve.granted_scopes = Mock(return_value={1: RESEARCH_SCOPES})
        invalid = [agent(), agent()]
        eve.http.request.return_value = invalid, {}
        with patch('muhely.research.time.time', return_value=NOW+86400): result = research.sync(eve, self.catalog)
        self.assertFalse(result[0]['ok']); self.assertEqual(self.store.snapshot(1, 'research')['data'], [agent()])
        self.assertFalse(result[1]['warning']); self.assertTrue(result[1]['needs_auth'])
        self.assertIsNone(self.store.characters()[0]['error'])
    def test_cache_and_304_reuse_previous_balance_and_missing_access_never_requests_token(self):
        self.seed(1, [agent()]); eve = EveConnection(self.store, vault=Mock(), transport=Mock())
        self.assertEqual(research.resource(eve, 1, 'test', NOW)['data'], [agent()]); eve.http.request.assert_not_called()
        eve.http.request.return_value = None, {'Cache-Control': 'max-age=3600', 'ETag': 'new'}
        value = research.resource(eve, 1, 'test', NOW+86400)
        self.assertEqual(value['data'], [agent()]); self.assertEqual(value['etag'], 'new')
        self.assertEqual(value['expires'], NOW+86400+3600)
        eve.granted_scopes = Mock(return_value={}); eve.token = Mock()
        self.store.save_universe_cache('research-agent', 3001, {'name': 'Agent'}, NOW)
        with patch('muhely.research.time.time', return_value=NOW): research.sync(eve, self.catalog)
        eve.token.assert_not_called()
    def test_names_and_prices_are_unique_across_all_owners(self):
        self.seed(1, [agent()]); self.seed(2, [agent()])
        eve = EveConnection(self.store, vault=Mock(), transport=Mock())
        eve.granted_scopes = Mock(return_value={1: RESEARCH_SCOPES, 2: RESEARCH_SCOPES}); eve.token = Mock(return_value='test')
        eve.http.request.return_value = [{'id': 3001, 'name': 'Researcher <name>'}], {}
        market = Mock()
        with patch('muhely.research.time.time', return_value=NOW): research.sync(eve, self.catalog, market)
        self.assertEqual(eve.http.request.call_count, 1); self.assertEqual(market.quote.call_count, 1)
        self.assertEqual(self.view()['rows'][0]['agent_name'], 'Researcher <name>')
    def test_forecast_filters_and_invalid_fields_are_rejected(self):
        for updates in [{'remainder_points': True}, {'points_per_day': float('nan')}, {'started_at': 'invalid'}, {'agent_id': 0}]:
            with self.assertRaises(EsiError): research.validate([{**agent(), **updates}])
        for kwargs in [{'at': float('nan')}, {'at': NOW-86400}, {'at': NOW+86400*2000}, {'character_id': 999}]:
            with self.assertRaises(PlanningError): self.view(**kwargs)
    def test_research_authorization_adds_scope_and_preserves_prior_permissions(self):
        import urllib.parse
        eve = EveConnection(self.store, vault=Mock(), transport=Mock()); eve.vault.read.return_value = {'1': {'scopes': ['esi-calendar.read_calendar_events.v1']}}
        self.store.save_settings({'client_id': 'public-client'})
        url = eve.start('session', 'http://127.0.0.1:8765/callback', 1, 'research')
        scopes = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['scope'][0].split()
        self.assertTrue(set(RESEARCH_SCOPES+INDUSTRY_SCOPES+['esi-calendar.read_calendar_events.v1']).issubset(scopes))
        self.assertTrue(set(RESEARCH_SCOPES).issubset(ALL_SCOPES))


class DailyPolicyTests(unittest.TestCase):
    def test_daily_limits_survive_restart_but_other_sources_keep_fifteen_minutes(self):
        with tempfile.TemporaryDirectory() as folder:
            p = RefreshPolicy(Store(folder)); p.claim(['research', 'extractions', 'pi'], now=NOW)
            p = RefreshPolicy(Store(folder))
            self.assertEqual(p.claim(['research', 'extractions', 'pi'], now=NOW+900), {'pi'})
            self.assertEqual(p.next_at(['extractions']), NOW+86400)
            self.assertEqual(p.claim(['research', 'extractions'], now=NOW+86399), set())
            self.assertEqual(p.claim(['research', 'extractions'], now=NOW+86400), {'research', 'extractions'})
    def test_general_manual_refresh_cannot_repeat_daily_moons_or_research(self):
        with tempfile.TemporaryDirectory() as folder:
            app = App(folder, ROOT/'data/catalog.sqlite3', 0); self.addCleanup(app.intel.stop)
            app.store.add_character(1, 'Pilot')
            app.store.save_snapshots(1, {'moon_calendar': {'data': [], 'fetched': NOW, 'expires': NOW+300, 'etag': None}}, domain='moon_calendar')
            app.eve.granted_scopes = Mock(return_value={1: RESEARCH_SCOPES})
            app.eve.sync = Mock(return_value=[]); app.eve.sync_skills = Mock(return_value=[]); app.eve.sync_pi = Mock(return_value=[])
            def finish():
                end = time.monotonic()+5
                while app.task['running'] and time.monotonic()<end: time.sleep(.01)
                self.assertFalse(app.task['running'])
            with patch('muhely.server.extractions.sync', return_value=[]) as moons, patch('muhely.server.research.sync', return_value=[]) as rp:
                app.start_task('sync', manual=True); finish()
                app.start_task('sync', manual=True); finish()
                self.assertEqual(moons.call_count, 1); self.assertEqual(rp.call_count, 1)
                self.assertEqual(app.eve.sync.call_count, 2)
                app.start_task('extractions', manual=True); finish(); self.assertEqual(moons.call_count, 2)
                app.start_task('research', manual=True); finish(); self.assertEqual(rp.call_count, 2)


class ResearchApiTests(unittest.TestCase):
    setUp=server_tests.ServerTests.setUp; close=server_tests.ServerTests.close; request=server_tests.ServerTests.request
    def test_research_does_not_calculate_plans_and_refresh_requires_session_csrf(self):
        self.assertEqual(self.request('/api/research', Cookie='')[0], 403)
        self.assertEqual(self.request('/research.js')[0], 200)
        with patch.object(self.app, 'plan', side_effect=AssertionError('Research must not calculate a production plan')):
            status, data, _ = self.request('/api/research')
        self.assertEqual(status, 200); self.assertEqual(data['rows'], [])
        for path in ['/api/research?at=nan', '/api/research?character_id=999']:
            self.assertEqual(self.request(path)[0], 400)
        self.app.start_task = Mock()
        self.assertEqual(self.request('/api/research/sync', {}, Origin='https://other.invalid')[0], 403)
        self.app.start_task.assert_not_called()
        self.assertEqual(self.request('/api/research/sync', {'manual': True})[0], 200)
        self.app.start_task.assert_called_once_with('research', manual=True)
        self.app.store.add_character(1,'Pilot')
        self.app.eve.start=Mock(return_value='https://login.eveonline.com/v2/oauth/authorize?state=test')
        self.assertEqual(self.request('/api/auth/start',{'character_id':1,'feature':'research'})[0],200)
        self.app.eve.start.assert_called_once_with(self.app.cookie,self.app.origin+'/callback',1,'research')
