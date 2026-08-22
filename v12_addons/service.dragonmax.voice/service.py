#!/usr/bin/env python3
import json
import os
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
STATE_FILE = os.path.join(PROFILE, 'state.json')
TOKEN_FILE = os.path.join(PROFILE, 'bridge_token.txt')
HOST = '0.0.0.0'
PORT = 8765

REALMS = {
    'dragon order': 'dragon_order',
    'arcane dominion': 'arcane_dominion',
    'crimson court': 'crimson_court',
    'temple guardians': 'temple_guardians',
    'champion guild': 'champion_guild',
    'office consortium': 'office_consortium',
}

DANGEROUS = {'factory_reset', 'restore_backup', 'clear_all_data'}


def ensure_profile():
    if not xbmcvfs.exists(PROFILE):
        xbmcvfs.mkdirs(PROFILE)


def read_text(path, default=''):
    try:
        with xbmcvfs.File(path, 'r') as f:
            return f.read()
    except Exception:
        return default


def write_text(path, text):
    ensure_profile()
    with xbmcvfs.File(path, 'w') as f:
        f.write(text)


def get_token():
    token = read_text(TOKEN_FILE).strip()
    if not token:
        token = secrets.token_urlsafe(24)
        write_text(TOKEN_FILE, token)
    return token


def load_state():
    try:
        return json.loads(read_text(STATE_FILE, '{}') or '{}')
    except Exception:
        return {}


def save_state(state):
    write_text(STATE_FILE, json.dumps(state, indent=2))


def notify(msg):
    xbmcgui.Dialog().notification('Dragon AI', msg, xbmcgui.NOTIFICATION_INFO, 2500)


def builtin(command):
    xbmc.executebuiltin(command)


def switch_realm(realm_name):
    key = REALMS.get(realm_name.lower())
    if not key:
        return False, 'I could not match that realm.'
    state = load_state()
    state['realm'] = key
    save_state(state)
    notify('Realm: ' + realm_name.title())
    return True, 'Switched to ' + realm_name.title() + '.'


def set_performance(mode):
    aliases = {
        'maximum speed': 'maximum_speed',
        'max speed': 'maximum_speed',
        'balanced': 'balanced',
        'visual quality': 'visual_quality',
    }
    key = aliases.get(mode.lower())
    if not key:
        return False, 'Unknown performance mode.'
    state = load_state()
    state['performance_mode'] = key
    save_state(state)
    notify('Performance: ' + mode.title())
    return True, 'Performance mode set to ' + mode.title() + '.'


def health_summary():
    state = load_state()
    realm = state.get('realm', 'dragon_order').replace('_', ' ').title()
    perf = state.get('performance_mode', 'balanced').replace('_', ' ').title()
    free = 0
    try:
        free = xbmcvfs.getDiskSpace(xbmcvfs.translatePath('special://home/')) // (1024 * 1024)
    except Exception:
        pass
    msg = f'Realm {realm}. Performance {perf}.'
    if free:
        msg += f' About {free} MB free.'
    return True, msg


def resolve_intent(text):
    t = re.sub(r'\s+', ' ', text.strip().lower())
    t = re.sub(r'^(hey\s+)?dragon[,:]?\s*', '', t)

    for realm in REALMS:
        if ('switch' in t or 'change' in t or 'realm' in t) and realm in t:
            return {'name': 'switch_realm', 'arg': realm}

    if any(p in t for p in ['maximum speed', 'max speed']):
        return {'name': 'set_performance', 'arg': 'maximum speed'}
    if 'balanced mode' in t or t == 'balanced':
        return {'name': 'set_performance', 'arg': 'balanced'}
    if 'visual quality' in t:
        return {'name': 'set_performance', 'arg': 'visual quality'}

    if t in {'go home', 'home', 'open home'}:
        return {'name': 'builtin', 'arg': 'ActivateWindow(Home)'}
    if 'open movies' in t:
        return {'name': 'builtin', 'arg': 'ActivateWindow(Videos,MovieTitles,return)'}
    if 'open tv' in t or 'open tv shows' in t:
        return {'name': 'builtin', 'arg': 'ActivateWindow(Videos,TVShowTitles,return)'}
    if 'continue watching' in t:
        return {'name': 'builtin', 'arg': 'ActivateWindow(Home)'}
    if 'dragon portal' in t or 'open portal' in t:
        return {'name': 'builtin', 'arg': 'ActivateWindow(Programs,plugin.program.dragonmaxwizard,return)'}
    if 'system health' in t or 'why is kodi slow' in t or 'kodi running slow' in t:
        return {'name': 'health'}
    if 'clean cache' in t:
        return {'name': 'maintenance_cache'}
    if any(p in t for p in ['factory reset', 'wipe data', 'clear all data']):
        return {'name': 'factory_reset'}
    if 'restore backup' in t:
        return {'name': 'restore_backup'}
    if t.startswith('search for '):
        return {'name': 'search', 'arg': t[11:].strip()}
    return {'name': 'unknown', 'arg': t}


def execute_intent(intent, confirmed=False):
    name = intent.get('name')
    arg = intent.get('arg', '')

    if name in DANGEROUS and not confirmed:
        return {'ok': False, 'needs_confirmation': True, 'intent': intent,
                'message': 'That action changes or removes data. Say confirm to continue.'}

    if name == 'switch_realm':
        ok, msg = switch_realm(arg)
    elif name == 'set_performance':
        ok, msg = set_performance(arg)
    elif name == 'builtin':
        builtin(arg); ok, msg = True, 'Done.'
    elif name == 'health':
        ok, msg = health_summary()
    elif name == 'maintenance_cache':
        builtin('ActivateWindow(Programs,plugin.program.dragonmaxwizard,return)')
        ok, msg = True, 'Opened Dragon Portal maintenance. Cache cleaning remains confirmation-based.'
    elif name == 'search':
        builtin('ActivateWindow(Videos)')
        ok, msg = True, 'Search request received for ' + arg + '.'
    elif name in DANGEROUS:
        ok, msg = False, 'Destructive action is intentionally not executed directly by Dragon Voice.'
    else:
        ok, msg = False, 'I understood the speech, but I do not have a safe local action for that yet.'
    return {'ok': ok, 'message': msg, 'intent': intent}


def handle_command(text, confirmed=False):
    intent = resolve_intent(text)
    result = execute_intent(intent, confirmed=confirmed)
    if result.get('message'):
        notify(result['message'])
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = 'DragonVoice/1.0'

    def _json(self, code, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        supplied = self.headers.get('X-Dragon-Token', '')
        return secrets.compare_digest(supplied, get_token())

    def do_GET(self):
        if self.path == '/health':
            ok, msg = health_summary()
            return self._json(200, {'ok': ok, 'message': msg})
        if self.path == '/pair':
            ip = self.client_address[0]
            if ip in {'127.0.0.1', '::1'}:
                return self._json(200, {'ok': True, 'token': get_token(), 'port': PORT})
            return self._json(403, {'ok': False, 'message': 'Pairing token is only exposed locally.'})
        return self._json(404, {'ok': False})

    def do_POST(self):
        if not self._authorized():
            return self._json(401, {'ok': False, 'message': 'Invalid Dragon token.'})
        length = int(self.headers.get('Content-Length', '0') or 0)
        try:
            data = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception:
            return self._json(400, {'ok': False, 'message': 'Invalid JSON.'})
        if self.path == '/command':
            text = str(data.get('text', ''))
            confirmed = bool(data.get('confirmed', False))
            return self._json(200, handle_command(text, confirmed))
        return self._json(404, {'ok': False})

    def log_message(self, fmt, *args):
        xbmc.log('[DragonVoice] ' + (fmt % args), xbmc.LOGDEBUG)


def run_server():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    xbmc.log(f'[DragonVoice] bridge listening on {PORT}', xbmc.LOGINFO)
    return server


def main():
    ensure_profile()
    get_token()
    server = run_server()
    notify('Dragon Voice bridge ready')
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
    server.shutdown()
    server.server_close()


if __name__ == '__main__':
    main()
