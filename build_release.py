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
 with open(pending,'w',encoding='utf-8') as f: json.dump({'skin':'skin.auramod','requested_by':'dragonmax-4.9-installer','show_startup_splash':True},f)
 xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1800)
 for dep in required_skin_dependencies(root): enable_runtime_addon(dep)
 enable_runtime_addon('service.dragonmax.voice')
 if not enable_runtime_addon('skin.auramod'): raise RuntimeError('AuraMOD could not be enabled after installation')
 result=rpc('Settings.SetSettingValue',{'setting':'lookandfeel.skin','value':'skin.auramod'})
 xbmc.sleep(2200)
 current=rpc('Settings.GetSettingValue',{'setting':'lookandfeel.skin'})
 value=((current.get('result') or {}).get('value') or '')
 if value!='skin.auramod':
  xbmc.log('[DragonMaxWizard] AuraMOD switch deferred to startup service: '+repr(result),xbmc.LOGWARNING)
 else:
  try: os.remove(pending)
  except OSError: pass
  xbmc.executebuiltin('ActivateWindow(Home)')
'''
    if marker not in default:
        raise RuntimeError('Wizard dependency helper injection point not found')
    if 'def finalize_dragonmax(' not in default:
        default = default.replace(marker, helper + marker, 1)
    old = 'apply(home,fs,p)'
    if old not in default:
        raise RuntimeError('Wizard apply injection point not found')
    default = default.replace(old, old+'; finalize_dragonmax(home,root,p)', 1)
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

_original_media = b.generate_media
def generate_dragonmax_media():
    _original_media()
    source = b.STAGE / 'startup' / 'dragonmax_static_splash.png'
    media = b.STAGE / 'media'
    media.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    (media / 'splash.jpg').write_bytes(data)
    (media / 'splash.png').write_bytes(data)
    print('DragonMax Kodi startup splash staged in media/')
b.generate_media = generate_dragonmax_media

_original_userdata = b.generate_userdata
def generate_dragonmax_userdata():
    _original_userdata()
    stage = b.STAGE
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
    for token in ('type="multiimage"','WindowOpen','effect="zoom"','target=sports','target=anime','target=music','target=podcasts'):
        if token not in home_text: raise RuntimeError('DragonMax 4.9 presentation missing '+token)
    print('DragonMax 4.9 animated media hub staged deterministically')
    print('DragonMax fresh-install skin activation trigger staged')
b.generate_userdata = generate_dragonmax_userdata

sys.settrace(None)
b.main()
