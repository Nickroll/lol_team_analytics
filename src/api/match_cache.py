import json
import os
import sqlite3
import time

DB_PATH = 'data/cache.db'

class MatchCache:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()
        self._hits = 0
        self._misses = 0

    def _init_db(self):
        self._conn.execute('''CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            fetched_at REAL NOT NULL
        )''')
        self._conn.execute('''CREATE TABLE IF NOT EXISTS timelines (
            match_id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            fetched_at REAL NOT NULL
        )''')
        self._conn.commit()

    def get_match(self, match_id):
        try:
            row = self._conn.execute('SELECT data FROM matches WHERE match_id = ?', (match_id,)).fetchone()
            if row:
                self._hits += 1
                return json.loads(row[0])
            self._misses += 1
            return None
        except Exception:
            self._misses += 1
            return None

    def save_match(self, match_id, data):
        try:
            self._conn.execute(
                'INSERT OR REPLACE INTO matches (match_id, data, fetched_at) VALUES (?, ?, ?)',
                (match_id, json.dumps(data), time.time())
            )
            self._conn.commit()
            return True
        except Exception:
            return False

    def get_timeline(self, match_id):
        try:
            row = self._conn.execute('SELECT data FROM timelines WHERE match_id = ?', (match_id,)).fetchone()
            if row:
                self._hits += 1
                return json.loads(row[0])
            self._misses += 1
            return None
        except Exception:
            self._misses += 1
            return None

    def save_timeline(self, match_id, data):
        try:
            self._conn.execute(
                'INSERT OR REPLACE INTO timelines (match_id, data, fetched_at) VALUES (?, ?, ?)',
                (match_id, json.dumps(data), time.time())
            )
            self._conn.commit()
            return True
        except Exception:
            return False

    def get_stats(self):
        """Returns cache statistics."""
        try:
            match_count = self._conn.execute('SELECT COUNT(*) FROM matches').fetchone()[0]
            timeline_count = self._conn.execute('SELECT COUNT(*) FROM timelines').fetchone()[0]
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024) if os.path.exists(self.db_path) else 0
            return {
                'matches_cached': match_count,
                'timelines_cached': timeline_count,
                'db_size_mb': round(db_size_mb, 2),
                'session_hits': self._hits,
                'session_misses': self._misses,
            }
        except Exception:
            return {'matches_cached': 0, 'timelines_cached': 0, 'db_size_mb': 0, 'session_hits': 0, 'session_misses': 0}

    def clear(self):
        """Clears all cached data."""
        try:
            self._conn.execute('DELETE FROM matches')
            self._conn.execute('DELETE FROM timelines')
            self._conn.execute('VACUUM')
            self._conn.commit()
            self._hits = 0
            self._misses = 0
            return True
        except Exception:
            return False
