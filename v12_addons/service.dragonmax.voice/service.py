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

from dragon_memory import DragonMemory
from self_repair import SelfRepairManager

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
STATE_FILE = os.path.join(PROFILE, 'state.json')
TOKEN_FILE = os.path.join(PROFILE, 'bridge_token.txt')
PENDING_SKIN_FILE = os.path.join(PROFILE, 'pending_skin_activation.json')
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
    if not xbmcvfs.exists(PROFILE): xbmcvfs.mkdirs(PROFILE)

def read_text(path, default=''):
    try:
        with xbmcvfs.File(path, 'r') as f: return f.read()
    except Exception: return default

def write_text(path, text):
    ensure_profile()
    with xbmcvfs.File(path, 'w') as f: f.write(text)

def get_token():
    token = read_text(TOKEN_FILE).strip()
    if not token:
        token = secrets.token_urlsafe(24); write_text(TOKEN_FILE, token)
    return token

ensure_profile()
MEMORY = DragonMemory(PROFILE)
REPAIR = SelfRepairManager(PROFILE, STATE_FILE)

def load_state():
    try: return json.loads(read_text(STATE_FILE, '{}') or '{}')
    except Exception: return {}
def save_state(state):
    write_text(STATE_FILE, json.dumps(state, indent=2)); REPAIR.mark_last_good_state(state)
def notify(msg): xbmcgui.Dialog().notification('Dragon AI', msg, xbmcgui.NOTIFICATION_INFO, 2500)
def builtin(command): xbmc.executebuiltin(command)

def activate_pending_skin():
    if not xbmcvfs.exists(PENDING_SKIN_FILE): return False
    try:
        payload=json.loads(read_text(PENDING_SKIN_FILE,'{}') or '{}')
        skin=payload.get('skin','skin.auramod')
        request={'jsonrpc':'2.0','method':'Settings.SetSettingValue','id':1,'params':{'setting':'lookandfeel.skin','value':skin}}
        result=json.loads(xbmc.executeJSONRPC(json.dumps(request)))
        if result.get('result') is True:
            try: xbmcvfs.delete(PENDING_SKIN_FILE)
            except Exception: pass
            xbmc.log('[DragonVoice] activated pending skin '+skin, xbmc.LOGINFO)
            return True
        xbmc.log('[DragonVoice] pending skin activation returned '+repr(result), xbmc.LOGWARNING)
    except Exception as e:
        xbmc.log('[DragonVoice] pending skin activation failed: '+repr(e), xbmc.LOGERROR)
    return False

def switch_realm(realm_name):
    key=REALMS.get(realm_name.lower())
    if not key: return False,'I could not match that realm.'
    state=load_state(); state['realm']=key; save_state(state); MEMORY.remember('preferred realm',realm_name.title(),source='observed_action'); notify('Realm: '+realm_name.title()); return True,'Switched to '+realm_name.title()+'.'
def set_performance(mode):
    aliases={'maximum speed':'maximum_speed','max speed':'maximum_speed','balanced':'balanced','visual quality':'visual_quality'}; key=aliases.get(mode.lower())
    if not key: return False,'Unknown performance mode.'
    state=load_state(); state['performance_mode']=key; save_state(state); MEMORY.remember('preferred performance mode',mode.title(),source='observed_action'); notify('Performance: '+mode.title()); return True,'Performance mode set to '+mode.title()+'.'
def health_summary():
    state=load_state(); realm=state.get('realm','dragon_order').replace('_',' ').title(); perf=state.get('performance_mode','balanced').replace('_',' ').title(); free=0
    try: free=xbmcvfs.getDiskSpace(xbmcvfs.translatePath('special://home/'))//(1024*1024)
    except Exception: pass
    msg=f'Realm {realm}. Performance {perf}.'
    if free: msg+=f' About {free} MB free.'
    faults=REPAIR.diagnose(); msg += (' I also detected '+', '.join(faults)+'.') if faults else ' DragonMax core state looks healthy.'
    return True,msg

def resolve_intent(text):
    t=re.sub(r'\s+',' ',text.strip().lower()); t=re.sub(r'^(hey\s+)?dragon[,:]?\s*','',t)
    if t.startswith('remember that '):
        body=t[len('remember that '):].strip()
        if ' is ' in body:
            key,value=body.split(' is ',1); return {'name':'remember','arg':{'key':key.strip(),'value':value.strip()}}
        return {'name':'remember_note','arg':body}
    if t.startswith('remember '): return {'name':'remember_note','arg':t[len('remember '):].strip()}
    if t.startswith('forget '): return {'name':'forget','arg':t[len('forget '):].strip()}
    if 'what do you remember' in t or t=='memory': return {'name':'recall_all'}
    if 'repair yourself' in t or 'self repair' in t or 'fix yourself' in t: return {'name':'self_repair'}
    if 'recent repairs' in t or 'repair history' in t: return {'name':'repair_history'}
    for realm in REALMS:
        if ('switch' in t or 'change' in t or 'realm' in t) and realm in t: return {'name':'switch_realm','arg':realm}
    if any(p in t for p in ['maximum speed','max speed']): return {'name':'set_performance','arg':'maximum speed'}
    if 'balanced mode' in t or t=='balanced': return {'name':'set_performance','arg':'balanced'}
    if 'visual quality' in t: return {'name':'set_performance','arg':'visual quality'}
    if t in {'go home','home','open home'}: return {'name':'builtin','arg':'ActivateWindow(Home)'}
    if 'open movies' in t: return {'name':'builtin','arg':'ActivateWindow(Videos,MovieTitles,return)'}
    if 'open tv' in t or 'open tv shows' in t: return {'name':'builtin','arg':'ActivateWindow(Videos,TVShowTitles,return)'}
    if 'continue watching' in t: return {'name':'builtin','arg':'ActivateWindow(Home)'}
    if 'dragon portal' in t or 'open portal' in t: return {'name':'builtin','arg':'ActivateWindow(Programs,plugin.program.dragonmaxwizard,return)'}
    if 'system health' in t or 'why is kodi slow' in t or 'kodi running slow' in t: return {'name':'health'}
    if 'clean cache' in t: return {'name':'maintenance_cache'}
    if any(p in t for p in ['factory reset','wipe data','clear all data']): return {'name':'factory_reset'}
    if 'restore backup' in t: return {'name':'restore_backup'}
    if t.startswith('search for '): return {'name':'search','arg':t[11:].strip()}
    return {'name':'unknown','arg':t}

def execute_intent(intent,confirmed=False):
    name=intent.get('name'); arg=intent.get('arg','')
    if name in DANGEROUS and not confirmed: return {'ok':False,'needs_confirmation':True,'intent':intent,'message':'That action changes or removes data. Say confirm to continue.'}
    if name=='switch_realm': ok,msg=switch_realm(arg)
    elif name=='set_performance': ok,msg=set_performance(arg)
    elif name=='builtin': builtin(arg); ok,msg=True,'Done.'
    elif name=='health': ok,msg=health_summary()
    elif name=='remember': ok=MEMORY.remember(arg.get('key',''),arg.get('value',''),source='explicit'); msg='Remembered.' if ok else 'I could not store that memory.'
    elif name=='remember_note':
        note=str(arg).strip(); ok=MEMORY.remember('note '+str(len(MEMORY.recall())+1),note,source='explicit') if note else False; msg='Remembered that note.' if ok else 'There was nothing useful to remember.'
    elif name=='forget': ok=MEMORY.forget(arg); msg='Forgot '+arg+'.' if ok else 'I did not have a memory stored under '+arg+'.'
    elif name=='recall_all': memories=MEMORY.recall(); ok=True; msg='I remember '+'; '.join(f'{k}: {v}' for k,v in list(memories.items())[:8]) if memories else 'I do not have any saved preferences yet.'
    elif name=='self_repair': results=REPAIR.auto_repair_known_faults(); ok=all(r.get('ok') for r in results) if results else True; msg='No repair was needed.' if not results else ' '.join(r.get('message','') for r in results)
    elif name=='repair_history': repairs=REPAIR.recent_repairs(5); ok=True; msg='No repairs recorded.' if not repairs else 'Recent repairs: '+'; '.join(f"{r.get('fault')}: {r.get('action')}" for r in repairs)
    elif name=='maintenance_cache': builtin('ActivateWindow(Programs,plugin.program.dragonmaxwizard,return)'); ok,msg=True,'Opened Dragon Portal maintenance. Cache cleaning remains confirmation-based.'
    elif name=='search': builtin('ActivateWindow(Videos)'); ok,msg=True,'Search request received for '+arg+'.'
    elif name in DANGEROUS: ok,msg=False,'Destructive action is intentionally not executed directly by Dragon Voice.'
    else: ok,msg=False,'I understood the speech, but I do not have a safe local action for that yet.'
    return {'ok':ok,'message':msg,'intent':intent}
def handle_command(text,confirmed=False):
    intent=resolve_intent(text); result=execute_intent(intent,confirmed=confirmed); MEMORY.record_turn(text,intent.get('name','unknown'),result.get('message',''),result.get('ok',False));
    if result.get('message'): notify(result['message'])
    return result

class Handler(BaseHTTPRequestHandler):
    server_version='DragonVoice/1.2'
    def _json(self,code,payload):
        body=json.dumps(payload).encode('utf-8'); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def _authorized(self): return secrets.compare_digest(self.headers.get('X-Dragon-Token',''),get_token())
    def do_GET(self):
        if self.path=='/health': ok,msg=health_summary(); return self._json(200,{'ok':ok,'message':msg,'faults':REPAIR.diagnose()})
        if self.path=='/memory':
            if not self._authorized(): return self._json(401,{'ok':False,'message':'Invalid Dragon token.'})
            return self._json(200,{'ok':True,'preferences':MEMORY.recall(),'recent_context':MEMORY.recent_context(8)})
        if self.path=='/repairs':
            if not self._authorized(): return self._json(401,{'ok':False,'message':'Invalid Dragon token.'})
            return self._json(200,{'ok':True,'repairs':REPAIR.recent_repairs(20)})
        if self.path=='/pair':
            if self.client_address[0] in {'127.0.0.1','::1'}: return self._json(200,{'ok':True,'token':get_token(),'port':PORT})
            return self._json(403,{'ok':False,'message':'Pairing token is only exposed locally.'})
        return self._json(404,{'ok':False})
    def do_POST(self):
        if not self._authorized(): return self._json(401,{'ok':False,'message':'Invalid Dragon token.'})
        length=int(self.headers.get('Content-Length','0') or 0)
        try:data=json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception:return self._json(400,{'ok':False,'message':'Invalid JSON.'})
        if self.path=='/command': return self._json(200,handle_command(str(data.get('text','')),bool(data.get('confirmed',False))))
        if self.path=='/repair':
            results=REPAIR.auto_repair_known_faults(); return self._json(200,{'ok':all(r.get('ok') for r in results) if results else True,'results':results})
        return self._json(404,{'ok':False})
    def log_message(self,fmt,*args): xbmc.log('[DragonVoice] '+(fmt%args),xbmc.LOGDEBUG)

def run_server():
    try:
        server=ThreadingHTTPServer((HOST,PORT),Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); xbmc.log(f'[DragonVoice] bridge listening on {PORT}',xbmc.LOGINFO); return server
    except Exception as e:
        xbmc.log('[DragonVoice] bridge unavailable; local functions remain active: '+repr(e),xbmc.LOGERROR); return None

def main():
    ensure_profile(); get_token(); REPAIR.auto_repair_known_faults(); xbmc.sleep(1000); activated=activate_pending_skin(); server=run_server()
    notify('DragonMax activated' if activated else 'Dragon Voice memory and self-repair ready')
    monitor=xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1): break
    if server:
        server.shutdown(); server.server_close()

if __name__=='__main__': main()
