#!/usr/bin/env python3
"""Deterministic DragonMax 4.9 release builder."""
import hashlib
import json
import shutil
import sys
import time
import xml.etree.ElementTree as ET

import repo_release as release
import release_builder as b

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
 with open(pending,'w',encoding='utf-8') as f: json.dump({'skin':'skin.auramod','requested_by':'dragonmax-4.9-installer','installer_pid':os.getpid(),'requires_restart':True,'show_startup_splash':True,'target_window':'home'},f)
 xbmc.executebuiltin('UpdateLocalAddons'); xbmc.sleep(1800)
 for dep in required_skin_dependencies(root): enable_runtime_addon(dep)
 enable_runtime_addon('service.dragonmax.voice')
 enable_runtime_addon('plugin.program.dragonmaxportal')
 if not enable_runtime_addon('skin.auramod'): raise RuntimeError('AuraMOD could not be enabled after installation')
 xbmc.log('[DragonMaxWizard] DragonMax skin activation deferred until Kodi restarts',xbmc.LOGINFO)
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
    for token in ('def finalize_dragonmax(', "enable_runtime_addon('plugin.program.dragonmaxportal')", "installer_pid", "requires_restart"):
        if token not in default:
            raise RuntimeError('Wizard activation gate missing '+token)
    return default

base._r.DEFAULT = patch_wizard(base._r.DEFAULT)
release.DEFAULT = base._r.DEFAULT

_raw_fetch = b.fetch
_raw_fetch_text = b.fetch_text
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

def resilient_fetch_text(url):
    last = None
    for attempt in range(1, 4):
        try:
            return _raw_fetch_text(url)
        except Exception as exc:
            last = exc
            if attempt < 3:
                delay = attempt * 4
                print(f'WARN index fetch attempt {attempt}/3 failed for {url}: {exc}; retrying in {delay}s')
                time.sleep(delay)
    raise last
b.fetch_text = resilient_fetch_text

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


def generate_dragonmax_media():
    # Build audio only. Visuals are immutable project assets; the procedural
    # placeholder generator is deliberately bypassed.
    audio = b.STAGE / 'audio'
    b.write_wav(audio/'startup_theme.wav',8.0,(55,110,165,220),.26)
    b.write_wav(audio/'portal_open.wav',2.0,(140,280,560),.22)
    b.write_wav(audio/'achievement.wav',1.4,(523,659,784,1046),.20)
    b.write_wav(audio/'ui_click.wav',.16,(900,1300),.17)
    b.write_wav(audio/'ui_back.wav',.22,(420,260),.17)
    b.write_wav(audio/'ui_select.wav',.30,(660,880,1320),.17)
    b.write_wav(audio/'error.wav',.45,(180,120),.18)
    for i, realm in enumerate(REALMS):
        b.write_wav(audio/f'realm_change_{realm}.wav',1.0,(140+i*20,280+i*25,560+i*30),.18)

    artwork = b.STAGE / 'artwork'
    if artwork.exists(): shutil.rmtree(artwork)

    for realm in REALMS:
        src = ASSET_ROOT / 'artwork' / 'wallpapers' / realm / f'{realm}_01.png'
        copy_asset(src, b.STAGE / 'artwork' / 'wallpapers' / realm / f'{realm}_01.png', 500_000)

    recovered = ASSET_ROOT / 'artwork' / 'reference' / 'dragonmax_v92_home_preview.png'
    recovered_data = copy_asset(recovered, b.STAGE / 'artwork' / 'reference' / recovered.name, 1_000_000)
    legacy_recovered = b.STAGE / 'dragonmax' / 'artwork' / recovered.name
    if not legacy_recovered.is_file() or legacy_recovered.read_bytes() != recovered_data:
        raise RuntimeError('Recovered DragonMax V9.2 artwork does not match the legacy payload source')

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

    source_hashes = {}
    for realm in REALMS:
        path = b.STAGE / 'artwork' / 'wallpapers' / realm / f'{realm}_01.png'
        source_hashes[str(path.relative_to(b.STAGE)).replace('\\','/')] = hashlib.sha256(require_asset(path, 500_000)).hexdigest()
    ref_path = b.STAGE / 'artwork' / 'reference' / recovered.name
    source_hashes[str(ref_path.relative_to(b.STAGE)).replace('\\','/')] = hashlib.sha256(require_asset(ref_path, 1_000_000)).hexdigest()
    (b.STAGE / 'dragonmax' / 'artwork_manifest.json').write_text(json.dumps({'schema':1,'source':'project assets plus byte-identical recovered V9.2 reference','sha256':source_hashes},indent=2),encoding='utf-8')
    require_asset(b.STAGE / 'media' / 'splash.jpg', 5000)
    print('DragonMax realm artwork and recovered V9.2 reference staged and byte-verified')
    print('DragonMax Kodi startup splash staged in media/splash.jpg')
b.generate_audio = generate_dragonmax_media


_original_userdata = b.generate_userdata
def generate_dragonmax_userdata():
    _original_userdata()
    stage = b.STAGE

    voice = stage / 'addons' / 'service.dragonmax.voice' / 'service.py'
    voice_text = voice.read_text(encoding='utf-8')
    compile(voice_text, 'service.dragonmax.voice/service.py', 'exec')
    for token in ("payload.get('requires_restart')", "os.getpid()", "Skin.SetString(DragonMaxRealm,dragon_order)", "ActivateWindow(Home)", "play_startup_theme_once", "startup_theme.wav", "DragonMax.StartupAudioSession", "PlayMedia("):
        if token not in voice_text: raise RuntimeError('Dragon Voice restart activation gate missing '+token)

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

    # XML text legitimately escapes the double quotes inside Kodi built-ins.
    # Normalize that representation before validating the command graph.
    home_text = home.read_text(encoding='utf-8').replace('&quot;', '"')
    for token in ('DragonMaxPrimaryArtwork','WindowOpen','effect="zoom"','target=sports','target=anime','target=music','target=podcasts','wallpapers/arcane_dominion/','dragonmax_v92_home_preview.png','realm=dragon_order','realm=office_consortium'):
        if token not in home_text: raise RuntimeError('DragonMax 4.9 presentation missing '+token)
    for forbidden in ('hero_banners/','realm_crests/','portal_graphics/','RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open'):
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
    print('DragonMax restart-gated skin activation staged')
b.generate_userdata = generate_dragonmax_userdata

sys.settrace(None)
b.main()
