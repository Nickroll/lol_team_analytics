import unittest
import os
import json
from src.config import ConfigManager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.test_file = 'test_config.json'
        self.manager = ConfigManager(self.test_file)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_load_nonexistent_config(self):
        config = self.manager.load_config()
        self.assertEqual(config, {})

    def test_save_and_load_config(self):
        data = {
            'api_key': 'test_key',
            'region': 'na1',
            'players': ['p1', 'p2', 'p3', 'p4', 'p5']
        }
        self.manager.save_config(data)
        
        loaded_data = self.manager.load_config()
        self.assertEqual(loaded_data, data)

if __name__ == '__main__':
    unittest.main()
