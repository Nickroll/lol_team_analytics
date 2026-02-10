import unittest
import os
import shutil
import json
from src.api.match_cache import MatchCache

class TestMatchCache(unittest.TestCase):
    def setUp(self):
        self.test_dir = 'test_cache_data'
        self.cache = MatchCache(self.test_dir)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_save_and_get_match(self):
        match_id = 'NA1_12345'
        data = {'metadata': {}, 'info': {'gameId': 12345}}
        
        # Save
        self.cache.save_match(match_id, data)
        
        # Verify file exists
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, f"{match_id}.json")))
        
        # Get
        loaded_data = self.cache.get_match(match_id)
        self.assertEqual(loaded_data, data)

    def test_get_nonexistent_match(self):
        self.assertIsNone(self.cache.get_match('NONEXISTENT'))

    def test_save_and_get_timeline(self):
        match_id = 'NA1_12345'
        data = {'info': {'frames': []}}
        
        self.cache.save_timeline(match_id, data)
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, f"{match_id}_timeline.json")))
        
        loaded_data = self.cache.get_timeline(match_id)
        self.assertEqual(loaded_data, data)

if __name__ == '__main__':
    unittest.main()
