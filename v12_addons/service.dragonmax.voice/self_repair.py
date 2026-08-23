#!/usr/bin/env python3
import json
import os
import time

import xbmc
import xbmcvfs


class SelfRepairManager:
    """Conservative self-healing for known, reversible DragonMax faults.

    Repairs are allow-listed, logged, rate-limited, and never perform destructive
    resets automatically. Unknown problems are reported for later diagnosis.
    """

    def __init__(self, profile_dir, state_file):
        self.profile_dir = profile_dir
        self.state_file = state_file
        self.log_file = os.path.join(profile_dir, 'repair_log.json')
        self.backup_state = os.path.join(profile_dir, 'state.last_good.json')
        self.cooldown_seconds = 300
        if not xbmcvfs.exists(profile_dir):
            xbmcvfs.mkdirs(profile_dir)

    def _read_json(self, path, default):
        try:
            with xbmcvfs.File(path, 'r') as f:
                raw = f.read()
            return json.loads(raw) if raw else default
        except Exception:
            return default

    def _write_json(self, path, data):
        tmp = path + '.tmp'
        with xbmcvfs.File(tmp, 'w') as f:
            f.write(json.dumps(data, indent=2, sort_keys=True))
        if xbmcvfs.exists(path):
            xbmcvfs.delete(path)
        xbmcvfs.rename(tmp, path)

    def mark_last_good_state(self, state):
        self._write_json(self.backup_state, state)

    def _record(self, fault, action, ok, detail=''):
        entries = self._read_json(self.log_file, [])
        entries.append({
            'ts': int(time.time()),
            'fault': fault,
            'action': action,
            'ok': bool(ok),
            'detail': str(detail)[:500],
        })
        self._write_json(self.log_file, entries[-100:])

    def recent_repairs(self, limit=20):
        entries = self._read_json(self.log_file, [])
        return entries[-max(1, min(int(limit), 100)):]

    def _recently_attempted(self, fault):
        now = int(time.time())
        for item in reversed(self._read_json(self.log_file, [])):
            if item.get('fault') == fault:
                return now - int(item.get('ts', 0)) < self.cooldown_seconds
        return False

    def diagnose(self):
        faults = []
        if not xbmcvfs.exists(self.state_file):
            faults.append('missing_state')
        else:
            try:
                with xbmcvfs.File(self.state_file, 'r') as f:
                    json.loads(f.read() or '{}')
            except Exception:
                faults.append('corrupt_state')
        return faults

    def repair(self, fault):
        if self._recently_attempted(fault):
            return False, 'Repair cooldown active.'

        if fault == 'missing_state':
            state = {'realm': 'dragon_order', 'performance_mode': 'balanced'}
            self._write_json(self.state_file, state)
            self.mark_last_good_state(state)
            self._record(fault, 'recreate_default_state', True)
            return True, 'Recreated DragonMax state with safe defaults.'

        if fault == 'corrupt_state':
            backup = self._read_json(self.backup_state, None)
            if isinstance(backup, dict):
                self._write_json(self.state_file, backup)
                self._record(fault, 'restore_last_good_state', True)
                return True, 'Restored the last known-good DragonMax state.'
            state = {'realm': 'dragon_order', 'performance_mode': 'balanced'}
            self._write_json(self.state_file, state)
            self.mark_last_good_state(state)
            self._record(fault, 'replace_with_safe_defaults', True)
            return True, 'Replaced corrupt state with safe defaults.'

        self._record(fault, 'report_only', False, 'Unknown fault; automatic changes withheld.')
        xbmc.log('[DragonRepair] Unknown fault left untouched: ' + str(fault), xbmc.LOGWARNING)
        return False, 'Unknown problem detected. I did not make an unsafe automatic change.'

    def auto_repair_known_faults(self):
        results = []
        for fault in self.diagnose():
            ok, msg = self.repair(fault)
            results.append({'fault': fault, 'ok': ok, 'message': msg})
        return results
