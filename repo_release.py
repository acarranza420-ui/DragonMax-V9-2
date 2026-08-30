#!/usr/bin/env python3
import json
import sys
import xml.etree.ElementTree as ET
import dependency_closure as _closure
import repo_release_v45 as _r

_r.ET = ET
_RELEASE_VERSION = '4.6.0'
_r.VERSION = _RELEASE_VERSION
_r.REPO = _r.REPO.replace('4.5.0', _RELEASE_VERSION)
_r.ADDON = _r.ADDON.replace('4.5.0', _RELEASE_VERSION)
_r.DEFAULT = _r.DEFAULT.replace('4.5.0', _RELEASE_VERSION)

_FLIGHT_PACK = {
    'script.skin.helper.service': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.skin.helper.service/script.skin.helper.service-1.1.43.zip',
    'script.skin.helper.widgets': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.skin.helper.widgets/script.skin.helper.widgets-1.0.45.zip',
    'plugin.video.themoviedb.helper': 'https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/plugin.video.themoviedb.helper/plugin.video.themoviedb.helper-6.16.5.zip',
    'script.module.metadatautils': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.module.metadatautils/script.module.metadatautils-1.0.50.zip',
    'script.module.thetvdb': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.module.thetvdb/script.module.thetvdb-1.0.34.zip',
    'script.module.musicbrainz': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.module.musicbrainz/script.module.musicbrainz-0.7.0.zip',
    'script.module.jurialmunkey': 'https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/script.module.jurialmunkey/script.module.jurialmunkey-0.2.35.zip',
    'script.module.infotagger': 'https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/script.module.infotagger/script.module.infotagger-0.0.8.zip',
    'script.module.requests': 'https://mirrors.kodi.tv/addons/omega/script.module.requests/script.module.requests-2.31.0.zip',
    'script.image.resource.select': 'https://codeload.github.com/phil65/script.image.resource.select/zip/refs/heads/master',
    'resource.images.moviegenreicons.transparent': 'https://mirrors.kodi.tv/addons/matrix/resource.images.moviegenreicons.transparent/resource.images.moviegenreicons.transparent-0.0.6.zip',
    'resource.images.studios.coloured': 'https://mirrors.kodi.tv/addons/omega/resource.images.studios.coloured/resource.images.studios.coloured-0.0.24.zip',
    'resource.images.studios.white': 'https://mirrors.kodi.tv/addons/omega/resource.images.studios.white/resource.images.studios.white-0.0.34.zip',
    'script.skinshortcuts': 'https://github.com/MikeSiLVO/script.skinshortcuts/releases/download/v2.0.3/script.skinshortcuts-2.0.3.zip',
    'plugin.program.autocompletion': 'https://codeload.github.com/henryjfry/repository.thenewdiamond/zip/refs/heads/main',
}

_DRAGONMAX_MAINMENU = '''<?xml version="1.0" encoding="UTF-8"?>
<shortcuts>
  <shortcut>
    <label>Dragon Portal</label><label2>DragonMax</label2><defaultID>dragonportal</defaultID>
    <icon>special://home/artwork/realm_crests/dragon_order_crest.png</icon>
    <thumb>special://home/artwork/portal_graphics/dragon_order_portal.png</thumb>
    <action>ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)</action>
  </shortcut>
  <shortcut>
    <label>Continue Watching</label><label2>DragonMax</label2><defaultID>continuewatching</defaultID>
    <icon>special://skin/extras/icons/playlist.png</icon>
    <thumb>special://home/artwork/hero_banners/dragon_order/dragon_order_hero_01.png</thumb>
    <action>ActivateWindow(Videos,"videodb://inprogresstvshows/",return)</action>
  </shortcut>
  <shortcut>
    <label>Movies</label><label2>DragonMax</label2><defaultID>movies</defaultID>
    <icon>special://skin/extras/icons/film.png</icon>
    <thumb>special://home/artwork/hero_banners/crimson_court/crimson_court_hero_01.png</thumb>
    <action>ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_movie&amp;widget=True",return)</action>
  </shortcut>
  <shortcut>
    <label>TV Shows</label><label2>DragonMax</label2><defaultID>tvshows</defaultID>
    <icon>special://skin/extras/icons/tv.png</icon>
    <thumb>special://home/artwork/hero_banners/arcane_dominion/arcane_dominion_hero_01.png</thumb>
    <action>ActivateWindow(Videos,"plugin://plugin.video.themoviedb.helper/?info=dir_tv&amp;widget=True",return)</action>
  </shortcut>
  <shortcut>
    <label>Anime Universe</label><label2>DragonMax Realm</label2><defaultID>animeuniverse</defaultID>
    <icon>special://home/artwork/realm_crests/arcane_dominion_crest.png</icon>
    <thumb>special://home/artwork/portal_graphics/arcane_dominion_portal.png</thumb>
    <action>ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)</action>
  </shortcut>
  <shortcut>
    <label>Martial Arts</label><label2>DragonMax Realm</label2><defaultID>martialarts</defaultID>
    <icon>special://home/artwork/realm_crests/temple_guardians_crest.png</icon>
    <thumb>special://home/artwork/portal_graphics/temple_guardians_portal.png</thumb>
    <action>ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)</action>
  </shortcut>
  <shortcut>
    <label>Champion Guild</label><label2>DragonMax Realm</label2><defaultID>championguild</defaultID>
    <icon>special://home/artwork/realm_crests/champion_guild_crest.png</icon>
    <thumb>special://home/artwork/portal_graphics/champion_guild_portal.png</thumb>
    <action>ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)</action>
  </shortcut>
  <shortcut>
    <label>Office Consortium</label><label2>DragonMax Realm</label2><defaultID>officeconsortium</defaultID>
    <icon>special://home/artwork/realm_crests/office_consortium_crest.png</icon>
    <thumb>special://home/artwork/portal_graphics/office_consortium_portal.png</thumb>
    <action>ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)</action>
  </shortcut>
  <shortcut>
    <label>Settings</label><label2>DragonMax</label2><defaultID>settings</defaultID>
    <icon>special://skin/extras/icons/settings.png</icon>
    <action>ActivateWindow(Settings)</action>
  </shortcut>
</shortcuts>
'''

_builder_state = {'version': False, 'packages': False, 'pruner': False, 'closure': False, 'userdata': False}


def _patch_builder(frame, event, arg):
    if event != 'line' or frame.f_globals.get('__name__') != '__main__':
        return _patch_builder
    filename = frame.f_code.co_filename.replace('\\', '/')
    if not filename.endswith('/build_v12.py'):
        return _patch_builder
    g = frame.f_globals

    if 'RELEASE_VERSION' in g and 'BUILD' in g and not _builder_state['version']:
        g['RELEASE_VERSION'] = _RELEASE_VERSION
        g['BUILD'] = g['OUT'] / 'builds' / ('DragonMax_V12_Unified_Build_Content-'+_RELEASE_VERSION+'.zip')
        _builder_state['version'] = True

    packages = g.get('BOOTSTRAP_PACKAGES')
    if isinstance(packages, dict) and not _builder_state['packages']:
        packages.update(_FLIGHT_PACK)
        _builder_state['packages'] = True

    prune = g.get('prune_development_debris')
    if callable(prune) and not _builder_state['pruner']:
        original = prune
        def hardened_prune():
            original()
            stage = g['STAGE'] / 'addons'
            dev_names = g['DEV_DIR_NAMES']
            shutil_mod = g['shutil']
            if not stage.exists(): return
            for p in sorted(list(stage.rglob('*')), key=lambda x: len(x.parts), reverse=True):
                if p.name.lower() not in dev_names: continue
                try:
                    if p.is_dir(): shutil_mod.rmtree(p, ignore_errors=True)
                    else: p.unlink()
                except OSError: pass
        g['prune_development_debris'] = hardened_prune
        _builder_state['pruner'] = True

    install_dragonmax = g.get('install_dragonmax_addons')
    if callable(install_dragonmax) and not _builder_state['closure']:
        original_install = install_dragonmax
        def install_with_dependency_closure():
            original_install()
            _closure.bundle_official_dependency_closure(g['STAGE'], g['fetch'], g['extract_addon_zip'], g['fetch_text'])
        g['install_dragonmax_addons'] = install_with_dependency_closure
        _builder_state['closure'] = True

    generate_userdata = g.get('generate_userdata')
    if callable(generate_userdata) and not _builder_state['userdata']:
        original_userdata = generate_userdata
        def generate_unified_userdata():
            original_userdata()
            stage = g['STAGE']
            keymap = stage / 'userdata' / 'keymaps' / 'dragonmax.xml'
            keymap.write_text('<keymap><global><keyboard><menu>ActivateWindow(Programs,plugin://plugin.program.dragonmaxportal/,return)</menu></keyboard></global></keymap>', encoding='utf-8')
            menu_path = stage / 'dragonmax' / 'config' / 'menus.json'
            try: menus = json.loads(menu_path.read_text(encoding='utf-8'))
            except Exception: menus = {}
            menus['portal'] = ['Switch Skin','Performance','Weather','Wallpapers','Add-ons','Maintenance','Advanced Settings','System Info','Repair DragonMax']
            menu_path.write_text(json.dumps(menus, indent=2), encoding='utf-8')

            native_menu = stage / 'addons' / 'skin.auramod' / 'shortcuts' / 'mainmenu.DATA.xml'
            native_menu.parent.mkdir(parents=True, exist_ok=True)
            native_menu.write_text(_DRAGONMAX_MAINMENU, encoding='utf-8')
            parsed = ET.parse(native_menu).getroot()
            labels = [str(x.findtext('label') or '') for x in parsed.findall('shortcut')]
            required = {'Dragon Portal','Continue Watching','Movies','TV Shows','Anime Universe','Martial Arts','Champion Guild','Office Consortium','Settings'}
            if set(labels) != required:
                raise RuntimeError('DragonMax native AuraMOD main menu validation failed: '+repr(labels))
            print('DragonMax native AuraMOD home staged:', ', '.join(labels))
        g['generate_userdata'] = generate_unified_userdata
        _builder_state['userdata'] = True

    if all(_builder_state.values()):
        sys.settrace(None)
        return None
    return _patch_builder


sys.settrace(_patch_builder)

_boot_old = "xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1500); xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(3500)"
_boot_new = "xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1500); [xbmc.executebuiltin('EnableAddon('+aid+')') for aid in BOOTSTRAP]; xbmc.sleep(1000); xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(5000)"
if _boot_old not in _r.DEFAULT: raise RuntimeError('DragonMax dependency-repository bootstrap injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_boot_old, _boot_new, 1)

_filter_old = "if active_auramod(home) and r.startswith('addons/skin.auramod/'): continue"
_filter_new = "if active_auramod(home) and r.startswith('addons/skin.auramod/') and r!='addons/skin.auramod/shortcuts/mainmenu.DATA.xml': continue"
if _filter_old not in _r.DEFAULT: raise RuntimeError('AuraMOD preservation filter injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_filter_old, _filter_new, 1)

_wait_old = "deadline=time.time()+120\n  while time.time()<deadline:\n   unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n   if not unresolved: break\n   if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency setup')\n   xbmc.sleep(2000)\n  unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n  if unresolved: raise RuntimeError('AuraMOD dependency installation did not complete: '+', '.join(unresolved))"
_wait_new = "deadline=time.time()+120\n  while time.time()<deadline:\n   unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n   if not unresolved: break\n   if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency setup')\n   xbmc.sleep(2000)\n  unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n  if unresolved:\n   xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(5000)\n   for dep in unresolved: xbmc.executebuiltin('InstallAddon('+dep+')')\n   deadline=time.time()+90\n   while time.time()<deadline:\n    unresolved=[d for d in unresolved if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n    if not unresolved: break\n    if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency retry')\n    xbmc.sleep(2000)\n  if unresolved: raise RuntimeError('AuraMOD dependency installation did not complete after retry: '+', '.join(unresolved))"
if _wait_old not in _r.DEFAULT: raise RuntimeError('DragonMax dependency wait injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_wait_old, _wait_new, 1)

_FINALIZER = r'''
def finalize_addons():
    xbmc.executebuiltin('UpdateLocalAddons')
    xbmc.sleep(1500)
    xbmc.executebuiltin('EnableAddon(service.dragonmax.voice)')
    xbmc.executebuiltin('EnableAddon(plugin.program.dragonmaxportal)')
    xbmc.executebuiltin('EnableAddon(skin.auramod)')

    # Remove only AuraMOD's generated Skin Shortcuts user/cache files so this
    # install cannot retain the stock menu from an earlier failed candidate.
    shortcuts = xbmcvfs.translatePath('special://profile/addon_data/script.skinshortcuts/')
    try:
        if os.path.isdir(shortcuts):
            for name in os.listdir(shortcuts):
                if name.startswith('skin.auramod'):
                    path = os.path.join(shortcuts, name)
                    if os.path.isfile(path) or os.path.islink(path): os.remove(path)
                    elif os.path.isdir(path): shutil.rmtree(path, ignore_errors=True)
    except Exception as exc:
        log('AuraMOD Skin Shortcuts cache reset warning: '+str(exc), xbmc.LOGWARNING)

    profile = xbmcvfs.translatePath('special://profile/addon_data/service.dragonmax.voice/')
    os.makedirs(profile, exist_ok=True)
    marker = os.path.join(profile, 'pending_skin_activation.json')
    with open(marker, 'w', encoding='utf-8') as f:
        json.dump({'skin': 'skin.auramod', 'wizard_version': VERSION, 'rebuild_menu': True}, f)
'''
if '\ndef finalize_addons():' not in _r.DEFAULT:
    _r.DEFAULT = _r.DEFAULT.replace('\ndef main():', _FINALIZER + '\ndef main():', 1)

_old = "preflight(home,fs); o,c=backup(home,fs,br,p); c.extend(bootstrap_created); apply(home,fs,p); pu(p,100,'Installation complete'); p.close();"
_new = "preflight(home,fs); o,c=backup(home,fs,br,p); c.extend(bootstrap_created); apply(home,fs,p); finalize_addons(); pu(p,100,'Installation complete'); p.close();"
if _old not in _r.DEFAULT: raise RuntimeError('DragonMax finalizer injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_old, _new, 1)

_original_gates = _r.gates
def gates(source):
    _original_gates(source)
    required = ('finalize_addons','EnableAddon(service.dragonmax.voice)','EnableAddon(plugin.program.dragonmaxportal)','EnableAddon(skin.auramod)','pending_skin_activation.json','dependency retry','mainmenu.DATA.xml','name.startswith(\'skin.auramod\')')
    for token in required:
        if token not in source: raise RuntimeError('Installer finalization/bootstrap gate missing '+token)
_r.gates = gates

from repo_release_v45 import *
DEFAULT = _r.DEFAULT
