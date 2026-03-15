import unittest
import os
from src.api.match_cache import MatchCache

class TestMatchCache(unittest.TestCase):
    def setUp(self):
        self.test_db = 'test_cache.db'
        self.cache = MatchCache(self.test_db)

    def tearDown(self):
        self.cache._conn.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_save_and_get_match(self):
        match_id = 'NA1_12345'
        data = {'metadata': {}, 'info': {'gameId': 12345}}

        self.cache.save_match(match_id, data)

        loaded_data = self.cache.get_match(match_id)
        self.assertEqual(loaded_data, data)

    def test_get_nonexistent_match(self):
        self.assertIsNone(self.cache.get_match('NONEXISTENT'))

    def test_save_and_get_timeline(self):
        match_id = 'NA1_12345'
        data = {'info': {'frames': []}}

        self.cache.save_timeline(match_id, data)

        loaded_data = self.cache.get_timeline(match_id)
        self.assertEqual(loaded_data, data)

    def test_clear(self):
        self.cache.save_match('NA1_1', {'a': 1})
        self.cache.save_timeline('NA1_1', {'b': 2})
        self.cache.clear()
        self.assertIsNone(self.cache.get_match('NA1_1'))
        self.assertIsNone(self.cache.get_timeline('NA1_1'))

    def test_get_stats(self):
        self.cache.save_match('NA1_1', {'a': 1})
        self.cache.save_match('NA1_2', {'a': 2})
        self.cache.save_timeline('NA1_1', {'b': 1})
        stats = self.cache.get_stats()
        self.assertEqual(stats['matches_cached'], 2)
        self.assertEqual(stats['timelines_cached'], 1)

if __name__ == '__main__':
    unittest.main()
