#!/usr/bin/env python3
import json
import os
import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE = sys.argv[0]
PROFILE = xbmcvfs.translatePath('special://profile/addon_data/service.dragonmax.voice/')
STATE_FILE = os.path.join(PROFILE, 'state.json')


def url(action, **kwargs):
    data = {'action': action}
    data.update(kwargs)
    return BASE + '?' + urllib.parse.urlencode(data)


def item(label, action=None, folder=False, **kwargs):
    li = xbmcgui.ListItem(label=label)
    li.setArt({'icon': 'DefaultAddonProgram.png', 'thumb': 'DefaultAddonProgram.png'})
    target = url(action, **kwargs) if action else ''
    xbmcplugin.addDirectoryItem(HANDLE, target, li, isFolder=folder)


def notify(msg):
    xbmcgui.Dialog().notification('Dragon Portal', msg, xbmcgui.NOTIFICATION_INFO, 2600)


def read_state():
    try:
        with xbmcvfs.File(STATE_FILE, 'r') as f:
            return json.loads(f.read() or '{}')
    except Exception:
        return {}


def write_state(data):
    if not xbmcvfs.exists(PROFILE):
        xbmcvfs.mkdirs(PROFILE)
    with xbmcvfs.File(STATE_FILE, 'w') as f:
        f.write(json.dumps(data, indent=2))


def jsonrpc(method, params=None):
    req = {'jsonrpc': '2.0', 'method': method, 'id': 1}
    if params is not None:
        req['params'] = params
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(req)))
    except Exception:
        return {}


def set_skin(skin):
    jsonrpc('Addons.SetAddonEnabled', {'addonid': skin, 'enabled': True})
    result = jsonrpc('Settings.SetSettingValue', {'setting': 'lookandfeel.skin', 'value': skin})
    if result.get('result') in (True, 'OK'):
        notify('Skin switched to ' + skin.replace('skin.', '').title())
    else:
        notify('Skin switch could not be completed.')


def performance(mode):
    state = read_state()
    state['performance_mode'] = mode
    write_state(state)
    labels = {'maximum_speed': 'Maximum Speed', 'balanced': 'Balanced', 'visual_quality': 'Visual Quality'}
    notify('Performance: ' + labels.get(mode, mode))


def maintenance():
    choice = xbmcgui.Dialog().select('DragonMax Maintenance', [
        'Refresh local add-ons',
        'Refresh repositories',
        'Clear thumbnail cache',
        'Open Kodi File Manager',
    ])
    if choice == 0:
        xbmc.executebuiltin('UpdateLocalAddons')
        notify('Local add-ons refreshed.')
    elif choice == 1:
        xbmc.executebuiltin('UpdateAddonRepos')
        notify('Repositories refreshed.')
    elif choice == 2:
        if not xbmcgui.Dialog().yesno('DragonMax Maintenance', 'Clear cached thumbnails? Kodi will rebuild them as needed.'):
            return
        thumbs = xbmcvfs.translatePath('special://thumbnails/')
        try:
            dirs, files = xbmcvfs.listdir(thumbs)
            for name in files:
                xbmcvfs.delete(os.path.join(thumbs, name))
            for name in dirs:
                path = os.path.join(thumbs, name)
                subdirs, subfiles = xbmcvfs.listdir(path)
                for f in subfiles:
                    xbmcvfs.delete(os.path.join(path, f))
            notify('Thumbnail cache cleanup completed.')
        except Exception:
            notify('Thumbnail cleanup could not complete.')
    elif choice == 3:
        xbmc.executebuiltin('ActivateWindow(FileManager)')


def system_info():
    free = 0
    try:
        free = xbmcvfs.getDiskSpace(xbmcvfs.translatePath('special://home/')) // (1024 * 1024)
    except Exception:
        pass
    skin = jsonrpc('Settings.GetSettingValue', {'setting': 'lookandfeel.skin'}).get('result', {}).get('value', 'unknown')
    state = read_state()
    perf = state.get('performance_mode', 'balanced').replace('_', ' ').title()
    msg = 'Kodi: ' + xbmc.getInfoLabel('System.BuildVersion')
    msg += '\nSkin: ' + str(skin)
    msg += '\nPerformance: ' + perf
    if free:
        msg += '\nFree storage: ' + str(free) + ' MB'
    xbmcgui.Dialog().textviewer('DragonMax System Information', msg)


def repair():
    xbmc.executebuiltin('RunScript(service.dragonmax.voice)')
    xbmc.executebuiltin('UpdateLocalAddons')
    xbmc.sleep(1000)
    xbmc.executebuiltin('UpdateAddonRepos')
    notify('DragonMax repair cycle requested.')


def weather():
    xbmc.executebuiltin('ActivateWindow(Weather)')


def weather_settings():
    xbmc.executebuiltin('ActivateWindow(Settings,weather,return)')


def wallpapers():
    xbmc.executebuiltin('ActivateWindow(Pictures,special://home/artwork/wallpapers/,return)')


def addon_manager():
    xbmc.executebuiltin('ActivateWindow(AddonBrowser)')


def advanced_settings():
    xbmc.executebuiltin('ActivateWindow(SettingsSystem)')


def build_root():
    item('Switch Skin', 'skins', folder=True)
    item('Performance', 'performance_menu', folder=True)
    item('Weather', 'weather_menu', folder=True)
    item('Wallpapers', 'wallpapers')
    item('Add-ons', 'addons')
    item('Maintenance', 'maintenance')
    item('Advanced Settings', 'advanced')
    item('System Info', 'system_info')
    item('Repair DragonMax', 'repair')
    xbmcplugin.endOfDirectory(HANDLE)


def build_skins():
    item('AuraMOD', 'set_skin', skin='skin.auramod')
    item('Estuary Safe Mode', 'set_skin', skin='skin.estuary')
    xbmcplugin.endOfDirectory(HANDLE)


def build_perf():
    item('Maximum Speed', 'performance', mode='maximum_speed')
    item('Balanced', 'performance', mode='balanced')
    item('Visual Quality', 'performance', mode='visual_quality')
    xbmcplugin.endOfDirectory(HANDLE)


def build_weather():
    item('View Weather', 'weather')
    item('Weather Settings', 'weather_settings')
    xbmcplugin.endOfDirectory(HANDLE)


def main():
    q = urllib.parse.parse_qs(sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2].startswith('?') else '')
    action = q.get('action', [''])[0]
    if not action:
        return build_root()
    if action == 'skins': return build_skins()
    if action == 'performance_menu': return build_perf()
    if action == 'weather_menu': return build_weather()
    if action == 'set_skin': set_skin(q.get('skin', ['skin.auramod'])[0])
    elif action == 'performance': performance(q.get('mode', ['balanced'])[0])
    elif action == 'weather': weather()
    elif action == 'weather_settings': weather_settings()
    elif action == 'wallpapers': wallpapers()
    elif action == 'addons': addon_manager()
    elif action == 'maintenance': maintenance()
    elif action == 'advanced': advanced_settings()
    elif action == 'system_info': system_info()
    elif action == 'repair': repair()


if __name__ == '__main__':
    main()
