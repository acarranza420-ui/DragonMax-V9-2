#!/usr/bin/env python3
import repo_release_v45 as _r

# Harden the generated wizard without duplicating its full source in the build
# entrypoint. The base wizard remains versioned in repo_release_v45.py; this shim
# injects launch-only finalization and bootstrap behavior, then re-exports publish.

_boot_old = "xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1500); xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(3500)"
_boot_new = "xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1500); [xbmc.executebuiltin('EnableAddon('+aid+')') for aid in BOOTSTRAP]; xbmc.sleep(1000); xbmc.executebuiltin('UpdateAddonRepos'); xbmc.sleep(3500)"
if _boot_old not in _r.DEFAULT:
    raise RuntimeError('DragonMax dependency-repository bootstrap injection point not found')
_r.DEFAULT = _r.DEFAULT.replace(_boot_old, _boot_new, 1)

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
    )
    for token in required:
        if token not in source:
            raise RuntimeError('Installer finalization/bootstrap gate missing '+token)
_r.gates = gates

from repo_release_v45 import *
DEFAULT = _r.DEFAULT
