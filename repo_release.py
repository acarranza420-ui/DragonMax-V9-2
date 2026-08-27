#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
import repo_release_v45 as _r

# repo_release_v45.publish validates generated addons.xml with ET. Keep the
# parser available in the base module namespace so CI and Render execute the
# exact same publisher successfully.
_r.ET = ET

# Build-time flight pack. build_v12.py imports this module before it creates its
# BOOTSTRAP_PACKAGES dict, so a short-lived trace is the earliest reliable place
# to extend the real builder. Unlike sitecustomize, this is guaranteed to run
# because build_v12 imports repo_release explicitly.
_FLIGHT_PACK = {
    'script.skin.helper.service': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.skin.helper.service/script.skin.helper.service-1.1.43.zip',
    'script.skin.helper.widgets': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.skin.helper.widgets/script.skin.helper.widgets-1.0.45.zip',
    'plugin.video.themoviedb.helper': 'https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/plugin.video.themoviedb.helper/plugin.video.themoviedb.helper-6.16.5.zip',
    'script.module.metadatautils': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.module.metadatautils/script.module.metadatautils-1.0.50.zip',
    'script.module.thetvdb': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.module.thetvdb/script.module.thetvdb-1.0.34.zip',
    'script.module.musicbrainz': 'https://raw.githubusercontent.com/kodi-community-addons/repository.marcelveldt/master/matrix/script.module.musicbrainz/script.module.musicbrainz-0.7.0.zip',
    'script.module.jurialmunkey': 'https://raw.githubusercontent.com/jurialmunkey/repository.jurialmunkey/master/omega/zips/script.module.jurialmunkey/script.module.jurialmunkey-0.2.35.zip',
    # Direct AuraMOD resources observed failing on Fire TV. These are copied
    # into the payload so device-time repository timing cannot block launch.
    'script.image.resource.select': 'https://mirrors.kodi.tv/addons/omega/script.image.resource.select/script.image.resource.select-0.0.5.zip',
    'resource.images.moviegenreicons.transparent': 'https://mirrors.kodi.tv/addons/omega/resource.images.moviegenreicons.transparent/resource.images.moviegenreicons.transparent-0.0.6.zip',
    'resource.images.studios.coloured': 'https://mirrors.kodi.tv/addons/omega/resource.images.studios.coloured/resource.images.studios.coloured-0.0.24.zip',
    'resource.images.studios.white': 'https://mirrors.kodi.tv/addons/omega/resource.images.studios.white/resource.images.studios.white-0.0.34.zip',
}

def _patch_builder(frame, event, arg):
    if event == 'line' and frame.f_globals.get('__name__') == '__main__':
        filename = frame.f_code.co_filename.replace('\\', '/')
        packages = frame.f_globals.get('BOOTSTRAP_PACKAGES')
        if filename.endswith('/build_v12.py') and isinstance(packages, dict):
            packages.update(_FLIGHT_PACK)
            sys.settrace(None)
            return None
    return _patch_builder

sys.settrace(_patch_builder)

# Harden the generated wizard without duplicating its full source in the build
# entrypoint. The base wizard remains versioned in repo_release_v45.py; this shim
# injects launch-only finalization and bootstrap behavior, then re-exports publish.

_boot_old = "xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1500); xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(3500)"
_boot_new = "xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1500); [xbmc.executebuiltin('EnableAddon('+aid+')') for aid in BOOTSTRAP]; xbmc.sleep(1000); xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(5000)"
if _boot_old not in _r.DEFAULT:
    raise RuntimeError('DragonMax dependency-repository bootstrap injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_boot_old, _boot_new, 1)

# Device gate hardening: retry repository resolution once after a forced repo
# refresh instead of failing the entire install on the first Fire TV timing miss.
_wait_old = "deadline=time.time()+120\n  while time.time()<deadline:\n   unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n   if not unresolved: break\n   if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency setup')\n   xbmc.sleep(2000)\n  unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n  if unresolved: raise RuntimeError('AuraMOD dependency installation did not complete: '+', '.join(unresolved))"
_wait_new = "deadline=time.time()+120\n  while time.time()<deadline:\n   unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n   if not unresolved: break\n   if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency setup')\n   xbmc.sleep(2000)\n  unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n  if unresolved:\n   xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(5000)\n   for dep in unresolved: xbmc.executebuiltin('InstallAddon('+dep+')')\n   deadline=time.time()+90\n   while time.time()<deadline:\n    unresolved=[d for d in unresolved if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n    if not unresolved: break\n    if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency retry')\n    xbmc.sleep(2000)\n  if unresolved: raise RuntimeError('AuraMOD dependency installation did not complete after retry: '+', '.join(unresolved))"
if _wait_old not in _r.DEFAULT:
    raise RuntimeError('DragonMax dependency wait injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_wait_old, _wait_new, 1)

_FINALIZER = r'''
def finalize_addons():
    # Register the files we just applied without shipping or editing Kodi's live
    # addon database. Enable the DragonMax service and AuraMOD explicitly so a
    # clean profile behaves the same as an upgrade profile.
    xbmc.executebuiltin('UpdateLocalAddons')
    xbmc.sleep(1500)
    xbmc.executebuiltin('EnableAddon(service.dragonmax.voice)')
    xbmc.executebuiltin('EnableAddon(skin.auramod)')
    profile = xbmcvfs.translatePath('special://profile/addon_data/service.dragonmax.voice/')
    os.makedirs(profile, exist_ok=True)
    marker = os.path.join(profile, 'pending_skin_activation.json')
    with open(marker, 'w', encoding='utf-8') as f:
        json.dump({'skin': 'skin.auramod', 'wizard_version': VERSION}, f)
'''

if '\ndef finalize_addons():' not in _r.DEFAULT:
    _r.DEFAULT = _r.DEFAULT.replace('\ndef main():', _FINALIZER + '\ndef main():', 1)

_old = "preflight(home,fs); o,c=backup(home,fs,br,p); c.extend(bootstrap_created); apply(home,fs,p); pu(p,100,'Installation complete'); p.close();"
_new = "preflight(home,fs); o,c=backup(home,fs,br,p); c.extend(bootstrap_created); apply(home,fs,p); finalize_addons(); pu(p,100,'Installation complete'); p.close();"
if _old not in _r.DEFAULT:
    raise RuntimeError('DragonMax finalizer injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_old, _new, 1)

_original_gates = _r.gates
def gates(source):
    _original_gates(source)
    required = (
        'finalize_addons',
        'EnableAddon(service.dragonmax.voice)',
        'EnableAddon(skin.auramod)',
        'EnableAddon('+"'"+'+aid+'+"'"+')',
        'pending_skin_activation.json',
        'dependency retry',
    )
    for token in required:
        if token not in source:
            raise RuntimeError('Installer finalization/bootstrap gate missing '+token)
_r.gates = gates

from repo_release_v45 import *
DEFAULT = _r.DEFAULT
