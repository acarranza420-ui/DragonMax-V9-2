#!/usr/bin/env python3
import json
import sys
import xml.etree.ElementTree as ET
import dependency_closure as _closure
import repo_release_v45 as _r

_r.ET = ET

# Fire TV flight pack for third-party launch dependencies. Official Kodi Omega
# modules are resolved recursively by dependency_closure.py.
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

# Kodi profile data that defines the actual DragonMax AuraMOD experience. This
# is configuration, not volatile device state, so it survives the V9.2 -> V12
# migration while databases, thumbnails, cache, logs, and guisettings do not.
_LEGACY_SKIN_PROFILE = (
    ('addon_data', 'skin.auramod'),
    ('addon_data', 'script.skinshortcuts'),
    ('addon_data', 'script.skin.helper.service'),
    ('addon_data', 'script.skin.helper.widgets'),
    ('addon_data', 'script.colorbox'),
)

_builder_state = {
    'packages': False,
    'legacy_skin': False,
    'pruner': False,
    'closure': False,
    'userdata': False,
}


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

    reset_userdata = g.get('reset_userdata')
    if callable(reset_userdata) and not _builder_state['legacy_skin']:
        original_reset = reset_userdata

        def reset_preserving_dragonmax_skin():
            stage = g['STAGE']
            shutil_mod = g['shutil']
            stash = stage.parent / 'legacy_dragonmax_skin_profile'
            shutil_mod.rmtree(stash, ignore_errors=True)
            preserved = []

            for parts in _LEGACY_SKIN_PROFILE:
                rel = g['Path'](*parts)
                src = stage / 'userdata' / rel
                if not src.exists():
                    continue
                dst = stash / rel
                if src.is_dir():
                    shutil_mod.copytree(src, dst, dirs_exist_ok=True, copy_function=shutil_mod.copyfile)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil_mod.copyfile(src, dst)
                preserved.append(str(rel).replace('\\', '/'))

            original_reset()

            for parts in _LEGACY_SKIN_PROFILE:
                rel = g['Path'](*parts)
                src = stash / rel
                if not src.exists():
                    continue
                dst = stage / 'userdata' / rel
                if src.is_dir():
                    shutil_mod.copytree(src, dst, dirs_exist_ok=True, copy_function=shutil_mod.copyfile)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil_mod.copyfile(src, dst)

            if preserved:
                print('DragonMax legacy skin profile preserved:', ', '.join(preserved))
                files = []
                for p in sorted(stash.rglob('*')):
                    if p.is_file():
                        files.append(str(p.relative_to(stash)).replace('\\', '/'))
                print('DragonMax legacy skin profile files:', ', '.join(files[:80]))
            else:
                print('WARN no legacy AuraMOD/Skin Shortcuts profile was found to preserve')

        g['reset_userdata'] = reset_preserving_dragonmax_skin
        _builder_state['legacy_skin'] = True

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

    install_dragonmax = g.get('install_dragonmax_addons')
    if callable(install_dragonmax) and not _builder_state['closure']:
        original_install = install_dragonmax

        def install_with_dependency_closure():
            original_install()
            _closure.bundle_official_dependency_closure(
                g['STAGE'], g['fetch'], g['extract_addon_zip'], g['fetch_text']
            )

        g['install_dragonmax_addons'] = install_with_dependency_closure
        _builder_state['closure'] = True

    generate_userdata = g.get('generate_userdata')
    if callable(generate_userdata) and not _builder_state['userdata']:
        original_userdata = generate_userdata

        def generate_unified_userdata():
            original_userdata()
            stage = g['STAGE']
            keymap = stage / 'userdata' / 'keymaps' / 'dragonmax.xml'
            keymap.write_text(
                '<keymap><global><keyboard><menu>ActivateWindow(Programs,plugin://plugin.program.dragonmaxportal/,return)</menu></keyboard></global></keymap>',
                encoding='utf-8',
            )
            menu_path = stage / 'dragonmax' / 'config' / 'menus.json'
            try:
                menus = json.loads(menu_path.read_text(encoding='utf-8'))
            except Exception:
                menus = {}
            menus['portal'] = [
                'Switch Skin', 'Performance', 'Weather', 'Wallpapers', 'Add-ons',
                'Maintenance', 'Advanced Settings', 'System Info', 'Repair DragonMax'
            ]
            menu_path.write_text(json.dumps(menus, indent=2), encoding='utf-8')

            # Sidecar JSON is useful to DragonMax services, but AuraMOD itself
            # needs real skin/profile files. Require at least one real migrated
            # configuration file so CI cannot call a stock AuraMOD home valid.
            skin_profile = stage / 'userdata' / 'addon_data' / 'skin.auramod'
            shortcuts_profile = stage / 'userdata' / 'addon_data' / 'script.skinshortcuts'
            real_skin_files = []
            for root in (skin_profile, shortcuts_profile):
                if root.is_dir():
                    real_skin_files.extend(
                        p for p in root.rglob('*')
                        if p.is_file() and p.name != 'dragonmax_skin_base.json'
                    )
            if not real_skin_files:
                raise RuntimeError(
                    'DragonMax home configuration missing: legacy AuraMOD/Skin Shortcuts profile was stripped or absent'
                )
            print('DragonMax real AuraMOD profile validated:', len(real_skin_files), 'configuration files')

        g['generate_userdata'] = generate_unified_userdata
        _builder_state['userdata'] = True

    if all(_builder_state.values()):
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
    xbmc.executebuiltin('EnableAddon(plugin.program.dragonmaxportal)')
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
        'EnableAddon(plugin.program.dragonmaxportal)',
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
