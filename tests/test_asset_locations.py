import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from muhely.asset_locations import AssetLocations,SCOPE
from muhely.esi import EsiError
from muhely.store import Store


class AssetLocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name);self.store.add_character(1,'First');self.store.add_character(2,'Second')
        self.eve=SimpleNamespace(http=Mock(),token=Mock(return_value='synthetic'),granted_scopes=Mock(return_value={1:[SCOPE],2:[SCOPE]}))
        self.resolver=AssetLocations(self.store,self.eve,lambda:1000);self.addCleanup(self.resolver.stop)

    def data(self,lid):return {'rows':[{'location_id':lid}]}

    def test_system_name_is_resolved_locally_without_esi(self):
        data=self.resolver.decorate(self.data(30000142))
        self.assertEqual(data['rows'][0]['location_name'],'Jita');self.assertFalse(data['locations_pending'])
        self.eve.http.request.assert_not_called()

    def test_station_cache_is_reused_and_old_trade_cache_is_understood(self):
        self.eve.http.request.return_value=({'name':'Jita IV - Moon 4'}, {})
        self.resolver._resolve(60003760,[1])
        self.assertEqual(self.resolver.decorate(self.data(60003760))['rows'][0]['location_name'],'Jita IV - Moon 4')
        self.eve.http.request.assert_called_once()
        self.eve.http.request.return_value=({'name':'Uncached solar system'}, {})
        self.resolver._resolve(39999999,[1])
        self.assertEqual(self.resolver.decorate(self.data(39999999))['rows'][0]['location_name'],'Uncached solar system')
        self.store.save_universe_cache('trade-location:1',10**12,{'name':'Known structure'},999)
        self.assertEqual(self.resolver.decorate(self.data(10**12))['rows'][0]['location_name'],'Known structure')

    def test_inaccessible_reader_does_not_hide_a_name_from_another_authorized_reader(self):
        self.eve.http.request.side_effect=[EsiError('HTTP 403'),({'name':'Fountain of Life'}, {})]
        self.resolver._resolve(10**12,[1,2])
        data=self.resolver.decorate(self.data(10**12))
        self.assertEqual(data['rows'][0]['location_name'],'Fountain of Life');self.assertFalse(data['locations_pending'])
        self.assertEqual(self.eve.http.request.call_count,2)

    def test_missing_scope_is_explained_and_throttled(self):
        self.eve.granted_scopes.return_value={}
        self.resolver._resolve(10**12,[1,2])
        for _ in range(3):
            data=self.resolver.decorate(self.data(10**12))
            self.assertEqual(data['rows'][0]['location_status'],'access');self.assertFalse(data['locations_pending'])
        self.eve.http.request.assert_not_called()

    def test_stale_known_name_survives_a_failed_refresh_without_a_request_loop(self):
        self.store.save_universe_cache('asset-structure:1',10**12,{'name':'Last known name','expires':500},400)
        self.store.save_universe_cache('asset-unresolved:0',10**12,{'error':'access','expires':1900},1000)
        data=self.resolver.decorate(self.data(10**12))
        self.assertEqual(data['rows'][0]['location_name'],'Last known name');self.assertFalse(data['locations_pending'])
        self.eve.http.request.assert_not_called()

    def test_corporation_names_are_scoped_and_disabled_corporations_have_no_readers(self):
        self.store.character_corporation(1,99,'A');self.store.character_corporation(2,98,'B')
        self.assertEqual(self.resolver.readers(99),[1])
        self.store.save_universe_cache('asset-structure:2',10**12,{'name':'Other corp private place','expires':2000},999)
        self.assertNotIn(10**12,self.resolver.cached({10**12},[1],99))
        self.store.set_corporation_monitoring(99,False);self.assertEqual(self.resolver.readers(99),[])


if __name__=='__main__':unittest.main()
