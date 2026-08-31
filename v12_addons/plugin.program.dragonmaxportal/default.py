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
PENDING_SKIN_FILE = os.path.join(PROFILE, 'pending_skin_activation.json')

REALMS = (
    ('dragon_order', 'Dragon Order'),
    ('arcane_dominion', 'Arcane Dominion'),
    ('crimson_court', 'Crimson Court'),
    ('temple_guardians', 'Temple Guardians'),
    ('champion_guild', 'Champion Guild'),
    ('office_consortium', 'Office Consortium'),
)

MEDIA_SECTIONS = {
    'movies': ('Movies', 'browse_movies', 'video_addons'),
    'tv': ('TV Shows', 'browse_tv', 'video_addons'),
    'sports': ('Sports', 'browse_sports', 'video_addons'),
    'anime': ('Anime', 'browse_anime', 'video_addons'),
    'music': ('Music', 'browse_music', 'audio_addons'),
    'podcasts': ('Podcasts', 'browse_podcasts', 'audio_addons'),
}


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
    xbmcgui.Dialog().notification('Dragon Portal', msg, xbmcgui.NOTIFICATION_INFO, 2200)


def click_sound(name='ui_select.wav'):
    xbmc.executebuiltin('PlayMedia(special://home/audio/' + name + ')')


def ensure_profile():
    if not xbmcvfs.exists(PROFILE):
        xbmcvfs.mkdirs(PROFILE)


def read_state():
    try:
        with xbmcvfs.File(STATE_FILE, 'r') as f:
            return json.loads(f.read() or '{}')
    except Exception:
        return {}


def write_json(path, data):
    ensure_profile()
    with xbmcvfs.File(path, 'w') as f:
        f.write(json.dumps(data, indent=2))


def write_state(data):
    write_json(STATE_FILE, data)


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
    xbmc.sleep(800)
    current = jsonrpc('Settings.GetSettingValue', {'setting': 'lookandfeel.skin'}).get('result', {}).get('value', '')
    if current == skin:
        if skin == 'skin.auramod':
            xbmc.executebuiltin('Skin.SetString(DragonMaxRealm,dragon_order)')
            xbmc.executebuiltin('Skin.SetString(DragonMaxRealmName,Dragon Order)')
            xbmc.executebuiltin('ActivateWindow(Home)')
        notify('Skin switched to ' + skin.replace('skin.', '').title())
    else:
        notify('Skin switch queued. Restart Kodi if the interface does not change immediately.')


def set_realm(slug):
    realm_name = dict(REALMS).get(slug)
    if not realm_name:
        notify('Unknown DragonMax realm.')
        return
    state = read_state()
    state['realm'] = slug
    write_state(state)
    xbmc.executebuiltin('Skin.SetString(DragonMaxRealm,' + slug + ')')
    xbmc.executebuiltin('Skin.SetString(DragonMaxRealmName,' + realm_name + ')')
    xbmc.executebuiltin('PlayMedia(special://home/audio/realm_change_' + slug + '.wav)')
    xbmc.sleep(180)
    xbmc.executebuiltin('ActivateWindow(Home)')


def activate_builtin(command, label):
    try:
        xbmc.executebuiltin(command)
        return True
    except Exception as exc:
        xbmc.log('[DragonPortal] ' + label + ' failed: ' + repr(exc), xbmc.LOGERROR)
        notify(label + ' could not be opened.')
        return False


def open_section(section):
    """Home tabs go directly to their primary destination. No nested Programs-window hop."""
    spec = MEDIA_SECTIONS.get(section)
    if not spec:
        notify('Unknown DragonMax media section: ' + section)
        return
    return open_target(spec[1], play_sound=False)


def build_section(section):
    spec = MEDIA_SECTIONS.get(section)
    if not spec:
        notify('Unknown DragonMax media section: ' + section)
        xbmcplugin.endOfDirectory(HANDLE)
        return
    label, browse_target, addons_target = spec
    item('Browse ' + label, 'open', target=browse_target)
    item(label + ' Add-ons Source', 'open', target=addons_target)
    xbmcplugin.setPluginCategory(HANDLE, 'DragonMax - ' + label)
    xbmcplugin.endOfDirectory(HANDLE)


def open_target(target, play_sound=True):
    """Single command router used by every DragonMax Home control."""
    if play_sound:
        click_sound()

    if target in MEDIA_SECTIONS:
        return open_section(target)

    if target == 'browse_anime':
        state = read_state()
        state['realm'] = 'arcane_dominion'
        write_state(state)
        xbmc.executebuiltin('Skin.SetString(DragonMaxRealm,arcane_dominion)')
        xbmc.executebuiltin('Skin.SetString(DragonMaxRealmName,Arcane Dominion)')
        xbmc.executebuiltin('PlayMedia(special://home/audio/realm_change_arcane_dominion.wav)')

    routes = {
        'portal': ('ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)', 'Dragon Portal'),
        'continue': ('ActivateWindow(Videos,"videodb://inprogresstvshows/",return)', 'Continue Watching'),
        'browse_movies': ('ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_movie",return)', 'Movies'),
        'browse_tv': ('ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_tv",return)', 'TV Shows'),
        'browse_sports': ('ActivateWindow(Videos,"addons://sources/video/",return)', 'Sports'),
        'browse_anime': ('ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=search&query=anime",return)', 'Anime'),
        'browse_music': ('ActivateWindow(MusicFiles)', 'Music'),
        'browse_podcasts': ('ActivateWindow(MusicFiles,"addons://sources/audio/",return)', 'Podcasts'),
        'video_addons': ('ActivateWindow(Videos,"addons://sources/video/",return)', 'Video Add-ons'),
        'audio_addons': ('ActivateWindow(MusicFiles,"addons://sources/audio/",return)', 'Audio Add-ons'),
        'settings': ('ActivateWindow(Settings)', 'Settings'),
        'addons': ('ActivateWindow(AddonBrowser)', 'Add-ons'),
        'weather': ('ActivateWindow(Weather)', 'Weather'),
    }
    route = routes.get(target)
    if not route:
        notify('Unknown DragonMax destination: ' + target)
        return
    return activate_builtin(route[0], route[1])


def performance(mode):
    state = read_state()
    state['performance_mode'] = mode
    write_state(state)
    labels = {'maximum_speed': 'Maximum Speed', 'balanced': 'Balanced', 'visual_quality': 'Visual Quality'}
    notify('Performance: ' + labels.get(mode, mode))


def maintenance():
    choice = xbmcgui.Dialog().select('DragonMax Maintenance', [
        'Refresh local add-ons', 'Refresh repositories', 'Clear thumbnail cache', 'Open Kodi File Manager'])
    if choice == 0:
        xbmc.executebuiltin('UpdateLocalAddons'); notify('Local add-ons refreshed.')
    elif choice == 1:
        xbmc.executebuiltin('UpdateAddonRepos'); notify('Repositories refreshed.')
    elif choice == 2:
        if not xbmcgui.Dialog().yesno('DragonMax Maintenance', 'Clear cached thumbnails? Kodi will rebuild them as needed.'):
            return
        thumbs = xbmcvfs.translatePath('special://thumbnails/')
        try:
            dirs, files = xbmcvfs.listdir(thumbs)
            for name in files: xbmcvfs.delete(os.path.join(thumbs, name))
            for name in dirs:
                path = os.path.join(thumbs, name)
                _, subfiles = xbmcvfs.listdir(path)
                for f in subfiles: xbmcvfs.delete(os.path.join(path, f))
            notify('Thumbnail cache cleanup completed.')
        except Exception:
            notify('Thumbnail cleanup could not complete.')
    elif choice == 3:
        xbmc.executebuiltin('ActivateWindow(FileManager)')


def system_info():
    free = 0
    try: free = xbmcvfs.getDiskSpace(xbmcvfs.translatePath('special://home/')) // (1024 * 1024)
    except Exception: pass
    skin = jsonrpc('Settings.GetSettingValue', {'setting': 'lookandfeel.skin'}).get('result', {}).get('value', 'unknown')
    state = read_state(); perf = state.get('performance_mode', 'balanced').replace('_', ' ').title()
    realm = dict(REALMS).get(state.get('realm', 'dragon_order'), 'Dragon Order')
    msg = 'Kodi: ' + xbmc.getInfoLabel('System.BuildVersion') + '\nSkin: ' + str(skin) + '\nRealm: ' + realm + '\nPerformance: ' + perf
    if free: msg += '\nFree storage: ' + str(free) + ' MB'
    xbmcgui.Dialog().textviewer('DragonMax System Information', msg)


def repair():
    if not xbmcgui.Dialog().yesno('Repair DragonMax', 'Refresh add-ons and repositories, re-enable DragonMax services, and queue AuraMOD recovery for the next startup?'):
        return
    xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(750)
    for addon_id in ('service.dragonmax.voice', 'plugin.program.dragonmaxportal', 'skin.auramod'):
        jsonrpc('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': True})
    xbmc.executebuiltin('UpdateAddonRepos')
    write_json(PENDING_SKIN_FILE, {'skin': 'skin.auramod', 'source': 'dragon_portal_repair', 'target_window': 'home'})
    notify('Repair queued. Fully exit Kodi and reopen it.')


def wallpapers(): xbmc.executebuiltin('ActivateWindow(Pictures,special://home/artwork/wallpapers/,return)')
def advanced_settings(): xbmc.executebuiltin('ActivateWindow(SettingsSystem)')


def build_root():
    for section in ('movies', 'tv', 'sports', 'anime', 'music', 'podcasts'):
        item(MEDIA_SECTIONS[section][0], 'section', folder=True, section=section)
    item('Switch Realm', 'realms', folder=True); item('Switch Skin', 'skins', folder=True)
    item('Performance', 'performance_menu', folder=True); item('Weather', 'open', target='weather')
    item('Wallpapers', 'wallpapers'); item('All Add-ons', 'open', target='addons'); item('Maintenance', 'maintenance')
    item('Advanced Settings', 'advanced'); item('System Info', 'system_info'); item('Repair DragonMax', 'repair')
    xbmcplugin.setPluginCategory(HANDLE, 'Dragon Portal')
    xbmcplugin.endOfDirectory(HANDLE)


def build_realms():
    current = read_state().get('realm', 'dragon_order')
    for slug, name in REALMS: item(('✓ ' if slug == current else '') + name, 'set_realm', realm=slug)
    xbmcplugin.endOfDirectory(HANDLE)


def build_skins():
    item('AuraMOD', 'set_skin', skin='skin.auramod'); item('Estuary Safe Mode', 'set_skin', skin='skin.estuary')
    xbmcplugin.endOfDirectory(HANDLE)


def build_perf():
    item('Maximum Speed', 'performance', mode='maximum_speed'); item('Balanced', 'performance', mode='balanced'); item('Visual Quality', 'performance', mode='visual_quality')
    xbmcplugin.endOfDirectory(HANDLE)


def main():
    q = urllib.parse.parse_qs(sys.argv[2][1:] if len(sys.argv) > 2 and sys.argv[2].startswith('?') else '')
    action = q.get('action', [''])[0]
    if not action: return build_root()
    if action == 'section': return build_section(q.get('section', ['movies'])[0])
    if action == 'realms': return build_realms()
    if action == 'skins': return build_skins()
    if action == 'performance_menu': return build_perf()
    if action == 'open': return open_target(q.get('target', ['portal'])[0])
    if action == 'set_realm': return set_realm(q.get('realm', ['dragon_order'])[0])
    if action == 'set_skin': return set_skin(q.get('skin', ['skin.auramod'])[0])
    if action == 'performance': return performance(q.get('mode', ['balanced'])[0])
    if action == 'wallpapers': return wallpapers()
    if action == 'maintenance': return maintenance()
    if action == 'advanced': return advanced_settings()
    if action == 'system_info': return system_info()
    if action == 'repair': return repair()

if __name__ == '__main__': main()
