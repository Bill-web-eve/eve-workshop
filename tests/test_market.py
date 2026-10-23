import tempfile,time,unittest
from pathlib import Path
from unittest.mock import Mock
from muhely.market import Market,STATION,best_quotes,validate_ids,expiry
from muhely.esi import EsiError
from muhely.store import Store
from muhely.planner import PlanningError

def order(price,buy=False,station=STATION,volume=100):return dict(price=price,is_buy_order=buy,location_id=station,volume_remain=volume)

class MarketTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(self.tmp.name)
        self.now=1000;self.http=Mock(blocked_until=0);self.market=Market(self.store,self.http,lambda:self.now)
    def test_only_jita_station_best_bid_and_ask(self):
        q=best_quotes([order(10,True),order(11,True),order(13),order(12),order(100,True,123),order(1,False,123),order(1,volume=0)])
        self.assertEqual(q,{'buy':'11','sell':'12'})
    def test_no_side_is_unknown_and_invalid_prices_do_not_turn_into_zero(self):
        self.assertEqual(best_quotes([]),{'buy':None,'sell':None})
        for bad in [float('nan'),float('inf'),-1,0]:
            with self.subTest(price=bad),self.assertRaises(EsiError):best_quotes([order(bad)])
    def test_every_page_is_used_and_cache_prevents_forced_refetch(self):
        self.http.request.side_effect=[([order(11,True),order(14)],{'X-Pages':'2','ETag':'one'}),([order(12,True),order(13)],{'X-Pages':'2','ETag':'two'})]
        q=self.market.quote(35);self.assertEqual((q['buy'],q['sell']),('12','13'));self.assertEqual(q['expires'],1300)
        self.market.quote(35);self.assertEqual(self.http.request.call_count,2)
        self.assertNotIn('token',self.http.request.call_args.kwargs)
    def test_304_refresh_reuses_page_quotes_and_etag(self):
        self.http.request.return_value=([order(11,True),order(12)],{'ETag':'abc'})
        self.market.quote(35);self.now=1901;self.http.request.return_value=(None,{'ETag':'abc'})
        q=self.market.quote(35);self.assertEqual(q['buy'],'11');self.assertEqual(q['checked'],1901)
        self.assertEqual(self.http.request.call_args.kwargs['headers'],{'If-None-Match':'abc'})
    def test_partial_failure_does_not_replace_last_complete_snapshot(self):
        self.http.request.return_value=([order(11,True),order(12)],{})
        old=self.market.quote(35);self.now=1901
        self.http.request.side_effect=[([order(15,True)],{'X-Pages':'2'}),EsiError('offline')]
        with self.assertRaises(EsiError):self.market.quote(35)
        self.assertEqual(self.store.market_quote(35),old);self.assertTrue(self.market.snapshot([35])['quotes']['35']['stale'])
    def test_manual_quote_bypasses_only_application_interval_and_resets_automatic_timer(self):
        self.http.request.return_value=([order(11,True),order(12)],{})
        self.market.quote(35);self.now=1100
        self.market.quote(35,manual=True);self.assertEqual(self.http.request.call_count,1)
        self.now=1301;self.market.quote(35);self.assertEqual(self.http.request.call_count,1)
        self.market.quote(35,manual=True);self.assertEqual(self.http.request.call_count,2)
        self.now=2100
        other=Market(self.store,self.http,lambda:self.now);other.quote(35)
        self.assertEqual(self.http.request.call_count,2)
        self.now=2201;other.quote(35);self.assertEqual(self.http.request.call_count,3)

    def test_cached_reads_cannot_extend_the_next_automatic_quote_deadline(self):
        self.http.request.return_value=([order(11,True),order(12)],{})
        self.market.quote(35)
        for now in [1301,1400,1500,1800]:
            self.now=now;self.market.quote(35)
        self.assertEqual(self.market.refresh_policy.next_at(['market:35']),1900)
        self.now=1900;self.market.quote(35);self.assertEqual(self.http.request.call_count,2)

    def test_snapshot_missing_is_not_a_fake_zero_price(self):
        data=self.market.snapshot([35]);self.assertEqual(data['quotes'],{})
    def test_background_failures_retain_quotes_and_limit_retry(self):
        self.http.request.side_effect=EsiError('offline');self.market.start([35,35])
        deadline=time.monotonic()+2
        while self.market.running and time.monotonic()<deadline:time.sleep(.005)
        self.assertFalse(self.market.running);s=self.market.snapshot([35]);self.assertIn('35',s['errors'])
        self.assertEqual(self.http.request.call_count,1);self.market.start([35]);self.assertEqual(self.http.request.call_count,1)
    def test_old_short_ttl_not_mislabeled_fresh_but_requests_still_rate_limited(self):
        self.http.request.return_value=([order(11)],{'Cache-Control':'max-age=300','Age':'200'})
        self.market.quote(35);self.now=1101;self.assertTrue(self.market.snapshot([35])['quotes']['35']['stale'])
        self.market.quote(35);self.assertEqual(self.http.request.call_count,1)
    def test_id_validation(self):
        from types import SimpleNamespace
        c=SimpleNamespace(types={35:{}});self.assertEqual(validate_ids([35,35],c),[35])
        for value in [None,[True],[36],[35]*1001]:
            with self.assertRaises(PlanningError):validate_ids(value,c)
    def test_background_quote_persists_across_restart(self):
        self.http.request.return_value=([order(11,True),order(12)],{})
        self.market.start([35]);deadline=time.monotonic()+2
        while self.market.running and time.monotonic()<deadline:time.sleep(.005)
        other=Market(Store(self.tmp.name),Mock(),lambda:self.now)
        self.assertEqual(other.snapshot([35])['quotes']['35']['buy'],'11')

import test_server as base
class MarketApiTests(unittest.TestCase):
    setUp=base.ServerTests.setUp
    close=base.ServerTests.close
    request=base.ServerTests.request
    def test_api_validates_ids_and_requires_csrf_for_quote_refresh(self):
        self.app.market.http=Mock(blocked_until=0)
        self.app.market.http.request.return_value=([order(11,True),order(12)],{})
        self.assertEqual(self.request('/api/prices?ids=35')[0],200)
        self.assertEqual(self.request('/api/prices?ids=0')[0],400)
        self.assertEqual(self.request('/api/prices/refresh',{'ids':[35]},**{'X-CSRF-Token':'wrong'})[0],403)
        self.assertEqual(self.request('/api/prices/refresh',{'ids':[35]})[0],200)
        deadline=time.monotonic()+2
        while self.app.market.running and time.monotonic()<deadline:time.sleep(.005)
        self.assertEqual(self.request('/api/prices?ids=35')[1]['quotes']['35']['sell'],'12')
        self.assertEqual(self.request('/costs.js')[0],200);self.assertEqual(self.request('/prices.js')[0],200)
