import json
import os
import hashlib

CACHE_DIR = 'data/cache'

class MatchCache:
    def __init__(self, cache_dir=CACHE_DIR):
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _get_path(self, filename):
        return os.path.join(self.cache_dir, filename)

    def get_match(self, match_id):
        filepath = self._get_path(f"{match_id}.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def save_match(self, match_id, data):
        filepath = self._get_path(f"{match_id}.json")
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f)
            return True
        except IOError:
            return False

    def get_timeline(self, match_id):
        filepath = self._get_path(f"{match_id}_timeline.json")
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def save_timeline(self, match_id, data):
        filepath = self._get_path(f"{match_id}_timeline.json")
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f)
            return True
        except IOError:
            return False
