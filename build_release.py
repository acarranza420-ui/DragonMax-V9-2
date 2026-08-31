#!/usr/bin/env python3
"""Deterministic DragonMax 4.9 release builder."""
import hashlib
import json
import shutil
import sys
import time
import xml.etree.ElementTree as ET

import repo_release_v49 as release

sys.modules['repo_release'] = release
import build_v12 as b

VERSION = '4.9.0'
base = release._base
ASSET_ROOT = b.ROOT / 'v49_assets'
REALMS = ('dragon_order','arcane_dominion','crimson_court','temple_guardians','champion_guild','office_consortium')

b.RELEASE_VERSION = VERSION
b.BUILD = b.OUT / 'builds' / f'DragonMax_V12_Unified_Build_Content-{VERSION}.zip'
b.BOOTSTRAP_PACKAGES.update(base._FLIGHT_PACK)
if 'media' not in b.RUNTIME_ROOTS:
    b.RUNTIME_ROOTS = tuple(b.RUNTIME_ROOTS) + ('media',)

# 4.9 owns JPG presentation assets. Do not allow the old generated PNG paths
# to remain wired into Home.xml.
base._DRAGONMAX_HOME_XML = (base._DRAGONMAX_HOME_XML
    .replace('dragon_order_hero_01.png', 'dragon_order_hero_01.jpg')
    .replace('dragon_order_portal.png', 'dragon_order_portal.jpg'))
release._DRAGONMAX_HOME_XML = base._DRAGONMAX_HOME_XML

def patch_wizard(default):
    default = default.replace(
        "ALLOWED=('addons/','userdata/','artwork/','audio/','startup/','dragonmax/');",
        "ALLOWED=('addons/','userdata/','artwork/','audio/','startup/','dragonmax/','media/');"
    )
    default = default.replace(
        "OWNED=('addons/service.dragonmax.voice/','userdata/addon_data/service.dragonmax.voice/','dragonmax/','artwork/','audio/','startup/')",
        "OWNED=('addons/service.dragonmax.voice/','userdata/addon_data/service.dragonmax.voice/','dragonmax/','artwork/','audio/','startup/','media/')"
    )
    marker = "def required_skin_dependencies(root):\n"
    helper = r'''def rpc(method,params=None):
 request={'jsonrpc':'2.0','method':method,'id':1}
 if params is not None: request['params']=params
 try:return json.loads(xbmc.executeJSONRPC(json.dumps(request)))
 except Exception:return {}
def enable_runtime_addon(aid):
 result=rpc('Addons.SetAddonEnabled',{'addonid':aid,'enabled':True})
 if result.get('result') in ('OK',True): return True
 xbmc.executebuiltin('EnableAddon('+aid+')'); xbmc.sleep(300)
 try:return xbmcaddon.Addon(aid) is not None
 except Exception:return False
def finalize_dragonmax(home,root,p):
 pu(p,98,'Activating DragonMax interface')
 pending=os.path.join(home,'userdata','addon_data','service.dragonmax.voice','pending_skin_activation.json')
 os.makedirs(os.path.dirname(pending),exist_ok=True)
 with open(pending,'w',encoding='utf-8') as f: json.dump({'skin':'skin.auramod','requested_by':'dragonmax-4.9-installer','show_startup_splash':True,'target_window':'home'},f)
 xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1800)
 for dep in required_skin_dependencies(root): enable_runtime_addon(dep)
 enable_runtime_addon('service.dragonmax.voice')
 enable_runtime_addon('plugin.program.dragonmaxportal')
 if not enable_runtime_addon('skin.auramod'): raise RuntimeError('AuraMOD could not be enabled after installation')
 result=rpc('Settings.SetSettingValue',{'setting':'lookandfeel.skin','value':'skin.auramod'})
 xbmc.sleep(2200)
 current=rpc('Settings.GetSettingValue',{'setting':'lookandfeel.skin'})
 value=((current.get('result') or {}).get('value') or '')
 if value!='skin.auramod':
  xbmc.log('[DragonMaxWizard] AuraMOD switch deferred to startup service: '+repr(result),xbmc.LOGWARNING)
 else:
  xbmc.executebuiltin('Skin.SetString(DragonMaxRealm,dragon_order)')
  xbmc.executebuiltin('Skin.SetString(DragonMaxRealmName,Dragon Order)')
  xbmc.executebuiltin('ActivateWindow(Home)')
'''
    if marker not in default:
        raise RuntimeError('Wizard dependency helper injection point not found')
    if 'def finalize_dragonmax(' not in default:
        default = default.replace(marker, helper + marker, 1)
    old = "apply(home,fs,p); finalize_addons(); pu(p,100,'Installation complete')"
    new = "apply(home,fs,p); finalize_addons(); finalize_dragonmax(home,root,p); pu(p,100,'Installation complete')"
    if old not in default:
        raise RuntimeError('Wizard activation sequence injection point not found')
    default = default.replace(old, new, 1)
    compile(default, 'dragonmaxwizard-default.py', 'exec')
    for token in ('def finalize_dragonmax(', "enable_runtime_addon('plugin.program.dragonmaxportal')", "Settings.SetSettingValue", "ActivateWindow(Home)"):
        if token not in default:
            raise RuntimeError('Wizard activation gate missing '+token)
    return default

base._r.DEFAULT = patch_wizard(base._r.DEFAULT)
release.DEFAULT = base._r.DEFAULT

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
    b.prune_development_debris()
    for p in sorted(list((b.STAGE / 'addons').rglob('*')), key=lambda x: len(x.parts), reverse=True):
        if any(part.lower() in b.DEV_DIR_NAMES for part in p.relative_to(b.STAGE).parts):
            try:
                if p.is_dir(): b.shutil.rmtree(p, ignore_errors=True)
                elif p.exists(): p.unlink()
            except OSError:
                pass
b.install_dragonmax_addons = install_dragonmax_with_closure


def _require_real_asset(path):
    if not path.is_file() or path.stat().st_size < 1000:
        raise RuntimeError('Required DragonMax 4.9 real asset missing: '+str(path))
    data = path.read_bytes()
    if path.suffix.lower() in ('.jpg','.jpeg') and not data.startswith(b'\xff\xd8\xff'):
        raise RuntimeError('DragonMax JPG asset corrupt: '+str(path))
    if path.suffix.lower() == '.png' and not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('DragonMax PNG asset corrupt: '+str(path))
    return data


def _copy_repeated(src, target_dir, names):
    data = _require_real_asset(src)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        (target_dir / name).write_bytes(data)

_original_media = b.generate_media
def generate_dragonmax_media():
    _original_media()

    # Replace every primary realm wallpaper/hero with recovered V12 artwork.
    # Synthetic gradients are physically removed from these directories.
    source_hashes = set()
    for realm in REALMS:
        src = ASSET_ROOT / 'wallpapers' / realm / f'{realm}_01.jpg'
        source_hashes.add(hashlib.sha256(_require_real_asset(src)).hexdigest())
        _copy_repeated(src, b.STAGE / 'artwork' / 'wallpapers' / realm,
                       [f'{realm}_{i:02d}.jpg' for i in range(1,9)])
        _copy_repeated(src, b.STAGE / 'artwork' / 'hero_banners' / realm,
                       [f'{realm}_hero_{i:02d}.jpg' for i in range(1,4)])
    if len(source_hashes) != len(REALMS):
        raise RuntimeError('DragonMax 4.9 realm artwork is not unique across all six realms')

    crest_src = ASSET_ROOT / 'crests' / 'dragon_order_crest.png'
    crest_dir = b.STAGE / 'artwork' / 'realm_crests'
    crest_dir.mkdir(parents=True, exist_ok=True)
    (crest_dir / 'dragon_order_crest.png').write_bytes(_require_real_asset(crest_src))

    portal_src = ASSET_ROOT / 'portal' / 'dragon_order_portal.jpg'
    portal_dir = b.STAGE / 'artwork' / 'portal_graphics'
    portal_dir.mkdir(parents=True, exist_ok=True)
    (portal_dir / 'dragon_order_portal.jpg').write_bytes(_require_real_asset(portal_src))
    old_portal = portal_dir / 'dragon_order_portal.png'
    if old_portal.exists(): old_portal.unlink()

    splash_src = ASSET_ROOT / 'startup' / 'dragonmax_static_splash.jpg'
    splash_data = _require_real_asset(splash_src)
    startup = b.STAGE / 'startup'
    startup.mkdir(parents=True, exist_ok=True)
    (startup / 'dragonmax_static_splash.jpg').write_bytes(splash_data)
    old_splash = startup / 'dragonmax_static_splash.png'
    if old_splash.exists(): old_splash.unlink()

    media = b.STAGE / 'media'
    media.mkdir(parents=True, exist_ok=True)
    (media / 'splash.jpg').write_bytes(splash_data)
    wrong_png = media / 'splash.png'
    if wrong_png.exists(): wrong_png.unlink()

    print('DragonMax 4.9 recovered realm artwork staged; synthetic primaries removed')
    print('DragonMax Kodi startup splash staged in media/splash.jpg')
b.generate_media = generate_dragonmax_media

_original_userdata = b.generate_userdata
def generate_dragonmax_userdata():
    _original_userdata()
    stage = b.STAGE

    # Harden the deferred skin switch. If the installer could not switch AuraMOD
    # immediately, the startup service must finish activation and return Home.
    voice = stage / 'addons' / 'service.dragonmax.voice' / 'service.py'
    voice_text = voice.read_text(encoding='utf-8')
    success_marker = "if active_skin == target_skin:\n"
    if success_marker not in voice_text:
        raise RuntimeError('Dragon Voice pending skin activation success marker missing')
    if "Skin.SetString(DragonMaxRealm,dragon_order)" not in voice_text:
        voice_text = voice_text.replace(
            success_marker,
            success_marker +
            "            xbmc.executebuiltin('Skin.SetString(DragonMaxRealm,dragon_order)')\n"
            "            xbmc.executebuiltin('Skin.SetString(DragonMaxRealmName,Dragon Order)')\n"
            "            xbmc.executebuiltin('ActivateWindow(Home)')\n"
            "            xbmc.sleep(300)\n",
            1)
    compile(voice_text, 'service.dragonmax.voice/service.py', 'exec')
    voice.write_text(voice_text, encoding='utf-8')

    keymap = stage / 'userdata' / 'keymaps' / 'dragonmax.xml'
    keymap.parent.mkdir(parents=True, exist_ok=True)
    keymap.write_text('<keymap><global><keyboard><menu>ActivateWindow(Programs,plugin://plugin.program.dragonmaxportal/,return)</menu></keyboard></global></keymap>',encoding='utf-8')
    pending = stage / 'userdata' / 'addon_data' / 'service.dragonmax.voice' / 'pending_skin_activation.json'
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_text(json.dumps({'skin':'skin.auramod','requested_by':'dragonmax-4.9-installer','show_startup_splash':True,'target_window':'home'},indent=2),encoding='utf-8')
    menu_path = stage / 'dragonmax' / 'config' / 'menus.json'
    try: menus = json.loads(menu_path.read_text(encoding='utf-8'))
    except Exception: menus = {}
    menus['home'] = ['Dragon Portal','Continue Watching','Movies','TV Shows','Sports','Anime','Music','Podcasts','Settings']
    menus['portal'] = ['Movies','TV Shows','Sports','Anime','Music','Podcasts','Switch Realm','Switch Skin','Performance','Weather','Wallpapers','All Add-ons','Martial Arts','Champion Guild','Office Consortium','Maintenance','Advanced Settings','System Info','Repair DragonMax']
    menu_path.write_text(json.dumps(menus, indent=2), encoding='utf-8')
    native_menu = stage / 'addons' / 'skin.auramod' / 'shortcuts' / 'mainmenu.DATA.xml'
    native_menu.parent.mkdir(parents=True, exist_ok=True)
    native_menu.write_text(base._DRAGONMAX_MAINMENU, encoding='utf-8')
    home = stage / 'addons' / 'skin.auramod' / '1080i' / 'Home.xml'
    home.write_text(base._DRAGONMAX_HOME_XML, encoding='utf-8')
    ET.parse(native_menu); ET.parse(home)
    labels = [str(x.findtext('label') or '') for x in ET.parse(native_menu).getroot().findall('shortcut')]
    required = ['Dragon Portal','Continue Watching','Movies','TV Shows','Sports','Anime','Music','Podcasts','Settings']
    if labels != required: raise RuntimeError('DragonMax 4.9 native menu validation failed: '+repr(labels))
    home_text = home.read_text(encoding='utf-8')
    for token in ('type="multiimage"','WindowOpen','effect="zoom"','target=sports','target=anime','target=music','target=podcasts','dragon_order_hero_01.jpg','dragon_order_portal.jpg'):
        if token not in home_text: raise RuntimeError('DragonMax 4.9 presentation missing '+token)
    for forbidden in ('dragon_order_hero_01.png','dragon_order_portal.png'):
        if forbidden in home_text: raise RuntimeError('Synthetic 4.9 presentation path survived: '+forbidden)
    for target in ('portal','continue','movies','tv','sports','anime','music','podcasts','settings'):
        if ('target='+target) not in home_text:
            raise RuntimeError('DragonMax 4.9 Home route missing '+target)

    portal = stage / 'addons' / 'plugin.program.dragonmaxportal' / 'default.py'
    portal_text = portal.read_text(encoding='utf-8')
    compile(portal_text, 'plugin.program.dragonmaxportal/default.py', 'exec')
    for token in ("return open_target(spec[1], play_sound=False)", "'browse_movies'", "'browse_tv'", "'browse_sports'", "'browse_anime'", "'browse_music'", "'browse_podcasts'"):
        if token not in portal_text: raise RuntimeError('Dragon Portal direct route gate missing '+token)
    if 'ActivateWindow(Home)' not in voice_text:
        raise RuntimeError('Dragon Voice fallback does not return to Home')

    print('DragonMax 4.9 animated media hub staged deterministically')
    print('DragonMax fresh-install and fallback skin activation staged')
b.generate_userdata = generate_dragonmax_userdata

sys.settrace(None)
b.main()
