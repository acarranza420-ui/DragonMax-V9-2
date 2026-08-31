#!/usr/bin/env python3
"""Deterministic DragonMax 4.9 release builder."""
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
ASSET_ROOT = b.ROOT / 'v12_assets'
REALMS = ('dragon_order','arcane_dominion','crimson_court','temple_guardians','champion_guild','office_consortium')

b.RELEASE_VERSION = VERSION
b.BUILD = b.OUT / 'builds' / f'DragonMax_V12_Unified_Build_Content-{VERSION}.zip'
b.BOOTSTRAP_PACKAGES.update(base._FLIGHT_PACK)
if 'media' not in b.RUNTIME_ROOTS:
    b.RUNTIME_ROOTS = tuple(b.RUNTIME_ROOTS) + ('media',)


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
    base._closure.bundle_official_dependency_closure(b.STAGE, b.fetch, b.extract_addon_zip, b.fetch_text)
    b.prune_development_debris()
    for p in sorted(list((b.STAGE / 'addons').rglob('*')), key=lambda x: len(x.parts), reverse=True):
        if any(part.lower() in b.DEV_DIR_NAMES for part in p.relative_to(b.STAGE).parts):
            try:
                if p.is_dir(): b.shutil.rmtree(p, ignore_errors=True)
                elif p.exists(): p.unlink()
            except OSError:
                pass
b.install_dragonmax_addons = install_dragonmax_with_closure


def require_asset(path, minimum):
    if not path.is_file() or path.stat().st_size < minimum:
        raise RuntimeError('Required DragonMax real asset missing/undersized: '+str(path))
    data = path.read_bytes()
    ext = path.suffix.lower()
    if ext in ('.jpg','.jpeg') and not data.startswith(b'\xff\xd8\xff'):
        raise RuntimeError('DragonMax JPG asset corrupt: '+str(path))
    if ext == '.png' and not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('DragonMax PNG asset corrupt: '+str(path))
    return data


def copy_asset(src, dst, minimum):
    data = require_asset(src, minimum)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    return data


_original_media = b.generate_media
def generate_dragonmax_media():
    _original_media()

    # Kill synthetic primary visual directories first. There is deliberately no
    # fallback: recovered source art must exist or the release fails.
    for rel in ('artwork/wallpapers','artwork/hero_banners','artwork/realm_crests','artwork/portal_graphics'):
        target = b.STAGE / rel
        if target.exists(): shutil.rmtree(target)

    for realm in REALMS:
        src = ASSET_ROOT / 'artwork' / 'wallpapers' / realm / f'{realm}_01.jpg'
        copy_asset(src, b.STAGE / 'artwork' / 'wallpapers' / realm / f'{realm}_01.jpg', 2500)
        crest = ASSET_ROOT / 'artwork' / 'realm_crests' / f'{realm}_crest.png'
        copy_asset(crest, b.STAGE / 'artwork' / 'realm_crests' / f'{realm}_crest.png', 500)

    portal = ASSET_ROOT / 'artwork' / 'portal_graphics' / 'dragon_order_portal.jpg'
    copy_asset(portal, b.STAGE / 'artwork' / 'portal_graphics' / 'dragon_order_portal.jpg', 2500)

    splash = ASSET_ROOT / 'startup' / 'dragonmax_static_splash.jpg'
    splash_data = require_asset(splash, 5000)
    startup = b.STAGE / 'startup'
    startup.mkdir(parents=True, exist_ok=True)
    (startup / 'dragonmax_static_splash.jpg').write_bytes(splash_data)
    for bad in (startup / 'dragonmax_static_splash.png', b.STAGE / 'media' / 'splash.png'):
        if bad.exists(): bad.unlink()
    media = b.STAGE / 'media'
    media.mkdir(parents=True, exist_ok=True)
    (media / 'splash.jpg').write_bytes(splash_data)

    # Byte-level release-source verification, not "a filename exists" theater.
    for realm in REALMS:
        require_asset(b.STAGE / 'artwork' / 'wallpapers' / realm / f'{realm}_01.jpg', 2500)
        require_asset(b.STAGE / 'artwork' / 'realm_crests' / f'{realm}_crest.png', 500)
    require_asset(b.STAGE / 'artwork' / 'portal_graphics' / 'dragon_order_portal.jpg', 2500)
    require_asset(b.STAGE / 'media' / 'splash.jpg', 5000)
    print('DragonMax recovered visual core staged and verified')
    print('DragonMax Kodi startup splash staged in media/splash.jpg')
b.generate_media = generate_dragonmax_media


_original_userdata = b.generate_userdata
def generate_dragonmax_userdata():
    _original_userdata()
    stage = b.STAGE

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
            "            xbmc.sleep(300)\n", 1)
    compile(voice_text, 'service.dragonmax.voice/service.py', 'exec')
    voice.write_text(voice_text, encoding='utf-8')

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
    for token in ('type="multiimage"','WindowOpen','effect="zoom"','target=sports','target=anime','target=music','target=podcasts','wallpapers/dragon_order/dragon_order_01.jpg','dragon_order_portal.jpg'):
        if token not in home_text: raise RuntimeError('DragonMax 4.9 presentation missing '+token)
    for forbidden in ('hero_banners/','dragon_order_portal.png','RunPlugin(plugin://plugin.program.dragonmaxportal'):
        if forbidden in home_text: raise RuntimeError('Invalid 4.9 presentation path/action survived: '+forbidden)
    for target in ('continue','movies','tv','sports','anime','music','podcasts','settings'):
        expected = 'ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/?action=open&amp;target='+target+'",return)'
        if expected not in home_text: raise RuntimeError('DragonMax 4.9 navigable Home route missing '+target)
    if 'ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)' not in home_text:
        raise RuntimeError('Dragon Portal root does not open a Kodi Programs window')
    if 'ActivateWindow(Home)' not in voice_text:
        raise RuntimeError('Dragon Voice fallback does not return to Home')

    portal = stage / 'addons' / 'plugin.program.dragonmaxportal' / 'default.py'
    portal_text = portal.read_text(encoding='utf-8')
    compile(portal_text, 'plugin.program.dragonmaxportal/default.py', 'exec')
    for token in ("'browse_movies'", "'browse_tv'", "'browse_sports'", "'browse_anime'", "'browse_music'", "'browse_podcasts'"):
        if token not in portal_text: raise RuntimeError('Dragon Portal route gate missing '+token)

    print('DragonMax 4.9 media hub staged with navigable Kodi windows')
    print('DragonMax fresh-install and fallback skin activation staged')
b.generate_userdata = generate_dragonmax_userdata

sys.settrace(None)
b.main()
