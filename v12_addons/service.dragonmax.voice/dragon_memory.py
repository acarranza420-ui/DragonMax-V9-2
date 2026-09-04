#!/usr/bin/env python3
import json
import os
import time

import xbmcvfs


class DragonMemory:
    """Small, inspectable local memory store for Dragon AI.

    Stores explicit user preferences and recent interaction context separately.
    It never stores raw audio and caps history to keep Fire TV storage predictable.
    """

    def __init__(self, profile_dir, history_limit=50):
        self.profile_dir = profile_dir
        self.memory_file = os.path.join(profile_dir, 'memory.json')
        self.history_file = os.path.join(profile_dir, 'conversation_history.json')
        self.history_limit = history_limit
        if not xbmcvfs.exists(profile_dir):
            xbmcvfs.mkdirs(profile_dir)

    def _read_json(self, path, default):
        try:
            with xbmcvfs.File(path, 'r') as f:
                raw = f.read()
            data = json.loads(raw) if raw else default
            return data
        except Exception:
            return default

    def _write_json(self, path, data):
        tmp = path + '.tmp'
        with xbmcvfs.File(tmp, 'w') as f:
            f.write(json.dumps(data, indent=2, sort_keys=True))
        if xbmcvfs.exists(path):
            xbmcvfs.delete(path)
        xbmcvfs.rename(tmp, path)

    def remember(self, key, value, source='voice'):
        key = str(key).strip().lower()[:80]
        value = str(value).strip()[:500]
        if not key or not value:
            return False
        data = self._read_json(self.memory_file, {'preferences': {}, 'updated_at': 0})
        prefs = data.setdefault('preferences', {})
        prefs[key] = {'value': value, 'source': source, 'updated_at': int(time.time())}
        data['updated_at'] = int(time.time())
        self._write_json(self.memory_file, data)
        return True

    def forget(self, key):
        key = str(key).strip().lower()
        data = self._read_json(self.memory_file, {'preferences': {}, 'updated_at': 0})
        prefs = data.setdefault('preferences', {})
        if key in prefs:
            del prefs[key]
            data['updated_at'] = int(time.time())
            self._write_json(self.memory_file, data)
            return True
        return False

    def recall(self, key=None):
        data = self._read_json(self.memory_file, {'preferences': {}})
        prefs = data.get('preferences', {})
        if key is None:
            return {k: v.get('value', '') for k, v in prefs.items()}
        item = prefs.get(str(key).strip().lower())
        return item.get('value') if item else None

    def record_turn(self, user_text, intent_name, result_message, ok):
        history = self._read_json(self.history_file, [])
        history.append({
            'ts': int(time.time()),
            'user': str(user_text)[:500],
            'intent': str(intent_name)[:80],
            'result': str(result_message)[:500],
            'ok': bool(ok),
        })
        history = history[-self.history_limit:]
        self._write_json(self.history_file, history)

    def recent_context(self, limit=8):
        history = self._read_json(self.history_file, [])
        return history[-max(1, min(int(limit), self.history_limit)):]

    def clear_session_history(self):
        self._write_json(self.history_file, [])
