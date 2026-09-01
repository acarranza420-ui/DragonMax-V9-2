#!/usr/bin/env python3
import json
import os
import re
import secrets
import threading
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from dragon_memory import DragonMemory
from self_repair import SelfRepairManager

ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
STATE_FILE = os.path.join(PROFILE, 'state.json')
TOKEN_FILE = os.path.join(PROFILE, 'bridge_token.txt')
PENDING_SKIN_FILE = os.path.join(PROFILE, 'pending_skin_activation.json')
HOST = '0.0.0.0'
PORT = 8765
CORE_PREFIXES = ('xbmc.', 'kodi.')
PORTAL = 'plugin://plugin.program.dragonmaxportal/'
STARTUP_THEME = 'special://home/audio/startup_theme.wav'
STARTUP_AUDIO_PROPERTY = 'DragonMax.StartupAudioSession'

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


ensure_profile()
MEMORY = DragonMemory(PROFILE)
REPAIR = SelfRepairManager(PROFILE, STATE_FILE)


def load_state():
    try:
        return json.loads(read_text(STATE_FILE, '{}') or '{}')
    except Exception:
        return {}


def save_state(state):
    write_text(STATE_FILE, json.dumps(state, indent=2))
    REPAIR.mark_last_good_state(state)


def notify(msg):
    xbmcgui.Dialog().notification('Dragon AI', msg, xbmcgui.NOTIFICATION_INFO, 2500)


def builtin(command):
    xbmc.executebuiltin(command)


def jsonrpc(method, params=None):
    request = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params is not None:
        request['params'] = params
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except Exception as exc:
        xbmc.log('[DragonVoice] JSON-RPC '+method+' failed: '+repr(exc), xbmc.LOGERROR)
        return {'error': repr(exc)}


def addon_enabled(addon_id):
    result = jsonrpc('Addons.GetAddonDetails', {'addonid': addon_id, 'properties': ['enabled']})
    try:
        return bool(result['result']['addon']['enabled'])
    except Exception:
        return False


def enable_addon(addon_id):
    result = jsonrpc('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': True})
    if result.get('result') in ('OK', True):
        return True
    xbmc.executebuiltin('EnableAddon('+addon_id+')')
    xbmc.sleep(250)
    return addon_enabled(addon_id)


def required_skin_dependencies(skin):
    """Use the installed skin addon.xml as the single source of activation truth."""
    xml_path = xbmcvfs.translatePath('special://home/addons/'+skin+'/addon.xml')
    try:
        root = ET.fromstring(read_text(xml_path, ''))
    except Exception as exc:
        xbmc.log('[DragonVoice] cannot parse '+skin+' addon.xml: '+repr(exc), xbmc.LOGERROR)
        return None
    required = []
    req = root.find('requires')
    if req is None:
        return required
    for node in req.findall('import'):
        dep = node.attrib.get('addon', '')
        optional = node.attrib.get('optional', '').lower() == 'true'
        if dep and not optional and not dep.startswith(CORE_PREFIXES):
            required.append(dep)
    return required


def enable_skin_stack(skin):
    xbmc.executebuiltin('UpdateLocalAddons')
    xbmc.sleep(1500)
    dependencies = required_skin_dependencies(skin)
    if dependencies is None:
        return False
    unresolved = []
    for addon_id in dependencies:
        if not enable_addon(addon_id) and not addon_enabled(addon_id):
            unresolved.append(addon_id)
    if not enable_addon(skin) and not addon_enabled(skin):
        unresolved.append(skin)
    if unresolved:
        xbmc.log('[DragonVoice] required skin stack still disabled: '+', '.join(unresolved), xbmc.LOGWARNING)
        return False
    return True


def active_skin_is(skin):
    result = jsonrpc('Settings.GetSettingValue', {'setting': 'lookandfeel.skin'})
    try:
        return result['result']['value'] == skin
    except Exception:
        return False


def play_startup_theme_once():
    """Play the packaged splash theme once for this Kodi process.

    The build owns the WAV under special://home/audio.  A global window property
    resets with Kodi, so this runs on every real Kodi launch but never repeats
    from the service's health loop or a Home-window refresh.
    """
    session = str(os.getpid())
    window = xbmcgui.Window(10000)
    if window.getProperty(STARTUP_AUDIO_PROPERTY) == session:
        return False
    if not active_skin_is('skin.auramod'):
        return False
    if not xbmcvfs.exists(STARTUP_THEME):
        xbmc.log('[DragonVoice] startup theme is missing: '+STARTUP_THEME, xbmc.LOGERROR)
        return False
    xbmc.executebuiltin('PlayMedia('+STARTUP_THEME+')')
    window.setProperty(STARTUP_AUDIO_PROPERTY, session)
    xbmc.log('[DragonVoice] played DragonMax startup theme for Kodi process '+session, xbmc.LOGINFO)
    return True


def activate_pending_skin():
    if not xbmcvfs.exists(PENDING_SKIN_FILE):
        return False
    try:
        payload = json.loads(read_text(PENDING_SKIN_FILE, '{}') or '{}')
        if payload.get('requires_restart') and int(payload.get('installer_pid', -1)) == os.getpid():
            xbmc.log('[DragonVoice] waiting for Kodi restart before skin activation', xbmc.LOGINFO)
            return False
        skin = payload.get('skin', 'skin.auramod')
        if not enable_skin_stack(skin):
            return False
        result = jsonrpc('Settings.SetSettingValue', {'setting': 'lookandfeel.skin', 'value': skin})
        if result.get('result') in (True, 'OK'):
            xbmc.sleep(1500)
            if active_skin_is(skin):
                xbmc.executebuiltin('Skin.SetString(DragonMaxRealm,dragon_order)')
                xbmc.executebuiltin('Skin.SetString(DragonMaxRealmName,Dragon Order)')
                xbmc.executebuiltin('ActivateWindow(Home)')
                xbmc.sleep(300)
                play_startup_theme_once()
                try:
                    xbmcvfs.delete(PENDING_SKIN_FILE)
                except Exception:
                    pass
                xbmc.log('[DragonVoice] activated pending skin '+skin, xbmc.LOGINFO)
                return True
        xbmc.log('[DragonVoice] pending skin activation returned '+repr(result), xbmc.LOGWARNING)
    except Exception as exc:
        xbmc.log('[DragonVoice] pending skin activation failed: '+repr(exc), xbmc.LOGERROR)
    return False


def switch_realm(realm_name):
    key = REALMS.get(realm_name.lower())
    if not key:
        return False, 'I could not match that realm.'
    state = load_state()
    state['realm'] = key
    save_state(state)
    MEMORY.remember('preferred realm', realm_name.title(), source='observed_action')
    notify('Realm: '+realm_name.title())
    return True, 'Switched to '+realm_name.title()+'.'


def set_performance(mode):
    aliases = {'maximum speed': 'maximum_speed', 'max speed': 'maximum_speed', 'balanced': 'balanced', 'visual quality': 'visual_quality'}
    key = aliases.get(mode.lower())
    if not key:
        return False, 'Unknown performance mode.'
    state = load_state()
    state['performance_mode'] = key
    save_state(state)
    MEMORY.remember('preferred performance mode', mode.title(), source='observed_action')
    notify('Performance: '+mode.title())
    return True, 'Performance mode set to '+mode.title()+'.'


def health_summary():
    state = load_state()
    realm = state.get('realm', 'dragon_order').replace('_', ' ').title()
    perf = state.get('performance_mode', 'balanced').replace('_', ' ').title()
    free = 0
    try:
        free = xbmcvfs.getDiskSpace(xbmcvfs.translatePath('special://home/')) // (1024*1024)
    except Exception:
        pass
    msg = f'Realm {realm}. Performance {perf}.'
    if free:
        msg += f' About {free} MB free.'
    faults = REPAIR.diagnose()
    msg += (' I also detected '+', '.join(faults)+'.') if faults else ' DragonMax core state looks healthy.'
    return True, msg


def resolve_intent(text):
    t = re.sub(r'\s+', ' ', text.strip().lower())
    t = re.sub(r'^(hey\s+)?dragon[,:]?\s*', '', t)
    if t.startswith('remember that '):
        body = t[len('remember that '):].strip()
        if ' is ' in body:
            key, value = body.split(' is ', 1)
            return {'name': 'remember', 'arg': {'key': key.strip(), 'value': value.strip()}}
        return {'name': 'remember_note', 'arg': body}
    if t.startswith('remember '): return {'name': 'remember_note', 'arg': t[len('remember '):].strip()}
    if t.startswith('forget '): return {'name': 'forget', 'arg': t[len('forget '):].strip()}
    if 'what do you remember' in t or t == 'memory': return {'name': 'recall_all'}
    if 'repair yourself' in t or 'self repair' in t or 'fix yourself' in t: return {'name': 'self_repair'}
    if 'recent repairs' in t or 'repair history' in t: return {'name': 'repair_history'}
    for realm in REALMS:
        if ('switch' in t or 'change' in t or 'realm' in t) and realm in t: return {'name': 'switch_realm', 'arg': realm}
    if any(p in t for p in ['maximum speed', 'max speed']): return {'name': 'set_performance', 'arg': 'maximum speed'}
    if 'balanced mode' in t or t == 'balanced': return {'name': 'set_performance', 'arg': 'balanced'}
    if 'visual quality' in t: return {'name': 'set_performance', 'arg': 'visual quality'}
    if t in {'go home', 'home', 'open home'}: return {'name': 'builtin', 'arg': 'ActivateWindow(Home)'}
    if 'open movies' in t: return {'name': 'builtin', 'arg': 'ActivateWindow(Videos,MovieTitles,return)'}
    if 'open tv' in t or 'open tv shows' in t: return {'name': 'builtin', 'arg': 'ActivateWindow(Videos,TVShowTitles,return)'}
    if 'continue watching' in t: return {'name': 'builtin', 'arg': 'ActivateWindow(Home)'}
    if 'dragon portal' in t or 'open portal' in t: return {'name': 'builtin', 'arg': 'ActivateWindow(Programs,'+PORTAL+',return)'}
    if 'system health' in t or 'why is kodi slow' in t or 'kodi running slow' in t: return {'name': 'health'}
    if 'clean cache' in t: return {'name': 'maintenance_cache'}
    if any(p in t for p in ['factory reset', 'wipe data', 'clear all data']): return {'name': 'factory_reset'}
    if 'restore backup' in t: return {'name': 'restore_backup'}
    if t.startswith('search for '): return {'name': 'search', 'arg': t[11:].strip()}
    return {'name': 'unknown', 'arg': t}


def execute_intent(intent, confirmed=False):
    name = intent.get('name')
    arg = intent.get('arg', '')
    if name in DANGEROUS and not confirmed:
        return {'ok': False, 'needs_confirmation': True, 'intent': intent, 'message': 'That action changes or removes data. Say confirm to continue.'}
    if name == 'switch_realm': ok, msg = switch_realm(arg)
    elif name == 'set_performance': ok, msg = set_performance(arg)
    elif name == 'builtin': builtin(arg); ok, msg = True, 'Done.'
    elif name == 'health': ok, msg = health_summary()
    elif name == 'remember': ok = MEMORY.remember(arg.get('key', ''), arg.get('value', ''), source='explicit'); msg = 'Remembered.' if ok else 'I could not store that memory.'
    elif name == 'remember_note':
        note = str(arg).strip(); ok = MEMORY.remember('note '+str(len(MEMORY.recall())+1), note, source='explicit') if note else False; msg = 'Remembered that note.' if ok else 'There was nothing useful to remember.'
    elif name == 'forget': ok = MEMORY.forget(arg); msg = 'Forgot '+arg+'.' if ok else 'I did not have a memory stored under '+arg+'.'
    elif name == 'recall_all':
        memories = MEMORY.recall(); ok = True; msg = 'I remember '+'; '.join(f'{k}: {v}' for k, v in list(memories.items())[:8]) if memories else 'I do not have any saved preferences yet.'
    elif name == 'self_repair':
        results = REPAIR.auto_repair_known_faults(); ok = all(r.get('ok') for r in results) if results else True; msg = 'No repair was needed.' if not results else ' '.join(r.get('message', '') for r in results)
    elif name == 'repair_history':
        repairs = REPAIR.recent_repairs(5); ok = True; msg = 'No repairs recorded.' if not repairs else 'Recent repairs: '+'; '.join(f"{r.get('fault')}: {r.get('action')}" for r in repairs)
    elif name == 'maintenance_cache': builtin('ActivateWindow(Programs,'+PORTAL+',return)'); ok, msg = True, 'Opened Dragon Portal maintenance.'
    elif name == 'search': builtin('ActivateWindow(Videos)'); ok, msg = True, 'Search request received for '+arg+'.'
    elif name in DANGEROUS: ok, msg = False, 'Destructive action is intentionally not executed directly by Dragon Voice.'
    else: ok, msg = False, 'I understood the speech, but I do not have a safe local action for that yet.'
    return {'ok': ok, 'message': msg, 'intent': intent}


def handle_command(text, confirmed=False):
    intent = resolve_intent(text)
    result = execute_intent(intent, confirmed=confirmed)
    MEMORY.record_turn(text, intent.get('name', 'unknown'), result.get('message', ''), result.get('ok', False))
    if result.get('message'):
        notify(result['message'])
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = 'DragonVoice/1.3'
    def _json(self, code, payload):
        body = json.dumps(payload).encode('utf-8'); self.send_response(code); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def _authorized(self): return secrets.compare_digest(self.headers.get('X-Dragon-Token', ''), get_token())
    def do_GET(self):
        if self.path == '/health': ok, msg = health_summary(); return self._json(200, {'ok': ok, 'message': msg, 'faults': REPAIR.diagnose()})
        if self.path == '/memory':
            if not self._authorized(): return self._json(401, {'ok': False, 'message': 'Invalid Dragon token.'})
            return self._json(200, {'ok': True, 'preferences': MEMORY.recall(), 'recent_context': MEMORY.recent_context(8)})
        if self.path == '/repairs':
            if not self._authorized(): return self._json(401, {'ok': False, 'message': 'Invalid Dragon token.'})
            return self._json(200, {'ok': True, 'repairs': REPAIR.recent_repairs(20)})
        if self.path == '/pair':
            if self.client_address[0] in {'127.0.0.1', '::1'}: return self._json(200, {'ok': True, 'token': get_token(), 'port': PORT})
            return self._json(403, {'ok': False, 'message': 'Pairing token is only exposed locally.'})
        return self._json(404, {'ok': False})
    def do_POST(self):
        if not self._authorized(): return self._json(401, {'ok': False, 'message': 'Invalid Dragon token.'})
        length = int(self.headers.get('Content-Length', '0') or 0)
        try: data = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception: return self._json(400, {'ok': False, 'message': 'Invalid JSON.'})
        if self.path == '/command': return self._json(200, handle_command(str(data.get('text', '')), bool(data.get('confirmed', False))))
        if self.path == '/repair':
            results = REPAIR.auto_repair_known_faults(); return self._json(200, {'ok': all(r.get('ok') for r in results) if results else True, 'results': results})
        return self._json(404, {'ok': False})
    def log_message(self, fmt, *args): xbmc.log('[DragonVoice] '+(fmt % args), xbmc.LOGDEBUG)


def run_server():
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        xbmc.log(f'[DragonVoice] bridge listening on {PORT}', xbmc.LOGINFO)
        return server
    except Exception as exc:
        xbmc.log('[DragonVoice] bridge unavailable; local functions remain active: '+repr(exc), xbmc.LOGERROR)
        return None


def main():
    ensure_profile(); get_token(); REPAIR.auto_repair_known_faults(); server = run_server(); monitor = xbmc.Monitor()
    activated = False
    if xbmcvfs.exists(PENDING_SKIN_FILE):
        for attempt in range(12):
            if monitor.abortRequested(): break
            xbmc.sleep(2500 if attempt == 0 else 5000)
            if activate_pending_skin(): activated = True; break
            xbmc.executebuiltin('UpdateLocalAddons')
    play_startup_theme_once()
    notify('DragonMax activated' if activated else 'Dragon Voice memory and self-repair ready')
    while not monitor.abortRequested():
        if xbmcvfs.exists(PENDING_SKIN_FILE): activate_pending_skin()
        play_startup_theme_once()
        if monitor.waitForAbort(5): break
    if server:
        server.shutdown(); server.server_close()


if __name__ == '__main__':
    main()
