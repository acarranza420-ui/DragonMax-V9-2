#!/usr/bin/env python3
"""Deterministic DragonMax 4.9 release builder."""
import json
import sys
import time
import xml.etree.ElementTree as ET

import repo_release_v49 as release

sys.modules['repo_release'] = release
import build_v12 as b

VERSION = '4.9.0'
base = release._base

b.RELEASE_VERSION = VERSION
b.BUILD = b.OUT / 'builds' / f'DragonMax_V12_Unified_Build_Content-{VERSION}.zip'
b.BOOTSTRAP_PACKAGES.update(base._FLIGHT_PACK)

# Network hardening for GitHub Actions/Render. Dependency hosts occasionally
# time out; retry the exact same immutable URL before failing the release.
_raw_fetch = b.fetch
def resilient_fetch(url, dest):
    last = None
    for attempt in range(1, 4):
        try:
            return _raw_fetch(url, dest)
        except Exception as exc:
            last = exc
            try:
                if dest.exists(): dest.unlink()
            except OSError:
                pass
            if attempt < 3:
                delay = attempt * 4
                print(f'WARN dependency fetch attempt {attempt}/3 failed for {url}: {exc}; retrying in {delay}s')
                time.sleep(delay)
    raise last
b.fetch = resilient_fetch

_original_install = b.install_dragonmax_addons
def install_dragonmax_with_closure():
    _original_install()
    base._closure.bundle_official_dependency_closure(
        b.STAGE, b.fetch, b.extract_addon_zip, b.fetch_text
    )
b.install_dragonmax_addons = install_dragonmax_with_closure

_original_userdata = b.generate_userdata
def generate_dragonmax_userdata():
    _original_userdata()
    stage = b.STAGE

    keymap = stage / 'userdata' / 'keymaps' / 'dragonmax.xml'
    keymap.parent.mkdir(parents=True, exist_ok=True)
    keymap.write_text(
        '<keymap><global><keyboard><menu>ActivateWindow(Programs,plugin://plugin.program.dragonmaxportal/,return)</menu></keyboard></global></keymap>',
        encoding='utf-8'
    )

    menu_path = stage / 'dragonmax' / 'config' / 'menus.json'
    try:
        menus = json.loads(menu_path.read_text(encoding='utf-8'))
    except Exception:
        menus = {}
    menus['home'] = ['Dragon Portal','Continue Watching','Movies','TV Shows','Sports','Anime','Music','Podcasts','Martial Arts','Champion Guild','Office Consortium','Settings']
    menus['portal'] = ['Movies','TV Shows','Sports','Anime','Music','Podcasts','Switch Realm','Switch Skin','Performance','Weather','Wallpapers','All Add-ons','Maintenance','Advanced Settings','System Info','Repair DragonMax']
    menu_path.write_text(json.dumps(menus, indent=2), encoding='utf-8')

    native_menu = stage / 'addons' / 'skin.auramod' / 'shortcuts' / 'mainmenu.DATA.xml'
    native_menu.parent.mkdir(parents=True, exist_ok=True)
    native_menu.write_text(base._DRAGONMAX_MAINMENU, encoding='utf-8')

    home = stage / 'addons' / 'skin.auramod' / '1080i' / 'Home.xml'
    home.write_text(base._DRAGONMAX_HOME_XML, encoding='utf-8')

    ET.parse(native_menu)
    ET.parse(home)

    labels = [str(x.findtext('label') or '') for x in ET.parse(native_menu).getroot().findall('shortcut')]
    required = ['Dragon Portal','Continue Watching','Movies','TV Shows','Sports','Anime','Music','Podcasts','Martial Arts','Champion Guild','Office Consortium','Settings']
    if labels != required:
        raise RuntimeError('DragonMax 4.9 native menu validation failed: ' + repr(labels))

    home_text = home.read_text(encoding='utf-8')
    for token in ('type="multiimage"','WindowOpen','effect="zoom"','target=sports','target=anime','target=music','target=podcasts'):
        if token not in home_text:
            raise RuntimeError('DragonMax 4.9 presentation missing ' + token)

    print('DragonMax 4.9 animated media hub staged deterministically')

b.generate_userdata = generate_dragonmax_userdata

sys.settrace(None)
b.main()
