#!/usr/bin/env python3
import repo_release_v45 as _r

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

# Make the generated-installer gate fail if this launch finalizer disappears.
_old_gates = "'UpdateLocalAddons','BOOTSTRAP'"
_new_gates = "'UpdateLocalAddons','EnableAddon(service.dragonmax.voice)','EnableAddon(skin.auramod)','pending_skin_activation.json','BOOTSTRAP'"
if _old_gates not in _r.DEFAULT:
    # The gate source is Python outside DEFAULT, so validate it in this shim too.
    pass

_original_gates = _r.gates
def gates(source):
    _original_gates(source)
    for token in ('finalize_addons','EnableAddon(service.dragonmax.voice)','EnableAddon(skin.auramod)','pending_skin_activation.json'):
        if token not in source:
            raise RuntimeError('Installer finalization gate missing '+token)
_r.gates = gates

from repo_release_v45 import *
DEFAULT = _r.DEFAULT
