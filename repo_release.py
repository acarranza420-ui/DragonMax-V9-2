#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
import repo_release_v45 as _r

_r.ET = ET

# Fire TV launch flight pack. Keep launch-critical AuraMOD direct dependencies
# and the non-core Python modules that are otherwise exposed to repository timing.
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
}

_builder_state = {'packages': False, 'pruner': False}

def _patch_builder(frame, event, arg):
    if event != 'line' or frame.f_globals.get('__name__') != '__main__':
        return _patch_builder
    filename = frame.f_code.co_filename.replace('\\', '/')
    if not filename.endswith('/build_v12.py'):
        return _patch_builder

    g = frame.f_globals
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
            if not stage.exists():
                return
            for p in sorted(list(stage.rglob('*')), key=lambda x: len(x.parts), reverse=True):
                if p.name.lower() not in dev_names:
                    continue
                try:
                    if p.is_dir():
                        shutil_mod.rmtree(p, ignore_errors=True)
                    else:
                        p.unlink()
                except OSError:
                    pass
        g['prune_development_debris'] = hardened_prune
        _builder_state['pruner'] = True

    if _builder_state['packages'] and _builder_state['pruner']:
        sys.settrace(None)
        return None
    return _patch_builder

sys.settrace(_patch_builder)

_boot_old = "xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1500); xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(3500)"
_boot_new = "xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1500); [xbmc.executebuiltin('EnableAddon('+aid+')') for aid in BOOTSTRAP]; xbmc.sleep(1000); xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(5000)"
if _boot_old not in _r.DEFAULT:
    raise RuntimeError('DragonMax dependency-repository bootstrap injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_boot_old, _boot_new, 1)

_wait_old = "deadline=time.time()+120\n  while time.time()<deadline:\n   unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n   if not unresolved: break\n   if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency setup')\n   xbmc.sleep(2000)\n  unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n  if unresolved: raise RuntimeError('AuraMOD dependency installation did not complete: '+', '.join(unresolved))"
_wait_new = "deadline=time.time()+120\n  while time.time()<deadline:\n   unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n   if not unresolved: break\n   if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency setup')\n   xbmc.sleep(2000)\n  unresolved=[d for d in missing if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n  if unresolved:\n   xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(5000)\n   for dep in unresolved: xbmc.executebuiltin('InstallAddon('+dep+')')\n   deadline=time.time()+90\n   while time.time()<deadline:\n    unresolved=[d for d in unresolved if not addon_installed(d) and not os.path.isdir(os.path.join(home,'addons',d))]\n    if not unresolved: break\n    if p.iscanceled(): raise RuntimeError('Installation cancelled during dependency retry')\n    xbmc.sleep(2000)\n  if unresolved: raise RuntimeError('AuraMOD dependency installation did not complete after retry: '+', '.join(unresolved))"
if _wait_old not in _r.DEFAULT:
    raise RuntimeError('DragonMax dependency wait injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_wait_old, _wait_new, 1)

_FINALIZER = r'''
def finalize_addons():
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
