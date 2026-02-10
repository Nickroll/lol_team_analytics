import json
import os

CONFIG_FILE = 'config.json'

class ConfigManager:
    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file

    def load_config(self):
        if not os.path.exists(self.config_file):
            return {}
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save_config(self, config_data):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=4)
            return True
        except IOError:
            return False
