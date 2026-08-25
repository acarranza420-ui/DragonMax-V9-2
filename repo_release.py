#!/usr/bin/env python3
import hashlib
import io
import zipfile
from pathlib import Path

VERSION = '4.0.4'
HOST = 'https://dragonmax-v12-release.onrender.com/'
PAYLOAD = HOST + 'builds/DragonMax_V12_Unified_Build_Content-4.0.0.zip'
XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'

REPO_ADDON = f'''{XML_DECL}
<addon id="repository.dragonmax" name="DragonMax Repository" version="{VERSION}" provider-name="DragonMax RD">
  <extension point="xbmc.addon.repository" name="DragonMax Repository">
    <dir minversion="21.0.0">
      <info compressed="false">{HOST}addons.xml</info>
      <checksum>{HOST}addons.xml.md5</checksum>
      <datadir zip="true">{HOST}</datadir>
    </dir>
  </extension>
  <extension point="xbmc.addon.metadata">
    <summary>DragonMax V12 Unified repository</summary>
    <description>DragonMax V12 Unified repository for Kodi 21+.</description>
    <platform>all</platform>
  </extension>
</addon>
'''

WIZARD_ADDON = f'''{XML_DECL}
<addon id="plugin.program.dragonmaxwizard" name="DragonMax Wizard" version="{VERSION}" provider-name="DragonMax RD">
  <requires><import addon="xbmc.python" version="3.0.0"/></requires>
  <extension point="xbmc.python.pluginsource" library="default.py"><provides>executable</provides></extension>
  <extension point="xbmc.addon.metadata">
    <summary>DragonMax V12 staging installer</summary>
    <description>Downloads, validates, safely backs up, stages, and applies DragonMax V12 Unified for device testing.</description>
    <platform>all</platform>
  </extension>
</addon>
'''

WIZARD_DEFAULT = r'''#!/usr/bin/env python3
import json, os, shutil, time, traceback, urllib.request, zipfile
import xbmc, xbmcgui, xbmcvfs

BUILD_JSON = 'https://dragonmax-v12-release.onrender.com/build.json'
PAYLOAD = 'https://dragonmax-v12-release.onrender.com/builds/DragonMax_V12_Unified_Build_Content-4.0.0.zip'
ADDON_ID = 'plugin.program.dragonmaxwizard'
VERSION = '4.0.4'


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[DragonMaxWizard] ' + str(msg), level)


def note(msg, ms=3500):
    xbmcgui.Dialog().notification('DragonMax Wizard', msg, xbmcgui.NOTIFICATION_INFO, ms)


def profile_path():
    path = xbmcvfs.translatePath('special://profile/addon_data/' + ADDON_ID + '/')
    os.makedirs(path, exist_ok=True)
    return path


def work_path():
    candidates = [xbmcvfs.translatePath('special://temp/dragonmax-v12/'), os.path.join(profile_path(), 'work')]
    last_error = None
    for path in candidates:
        try:
            shutil.rmtree(path, ignore_errors=True)
            os.makedirs(path, exist_ok=True)
            probe = os.path.join(path, '.write-test')
            with open(probe, 'wb') as f:
                f.write(b'ok')
            os.remove(probe)
            return path
        except Exception as e:
            last_error = e
    raise RuntimeError('No writable DragonMax work directory: ' + str(last_error))


def request(url, timeout=60):
    req = urllib.request.Request(url, headers={'User-Agent': 'Kodi/21 DragonMaxWizard/' + VERSION, 'Accept': '*/*', 'Connection': 'close'})
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(url):
    with request(url, 45) as r:
        return json.loads(r.read().decode('utf-8'))


def download(url, dst):
    with request(url, 300) as r, open(dst, 'wb') as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)


def copy_if_readable(src, dst):
    try:
        if os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            return True
    except (PermissionError, OSError) as e:
        log('Backup skipped unreadable file: %s (%s)' % (src, e), xbmc.LOGWARNING)
    return False


def backup(home, userdata):
    stamp = time.strftime('%Y%m%d-%H%M%S')
    root = os.path.join(home, 'dragonmax_backups', stamp)
    os.makedirs(root, exist_ok=True)

    # Kodi keeps several SQLite databases open while it is running. Android can
    # refuse direct reads of those files, so do not copy Database at all during a
    # live install. Back up only user configuration that is safe to read.
    safe_files = (
        'advancedsettings.xml', 'guisettings.xml', 'profiles.xml',
        'sources.xml', 'favourites.xml', 'RssFeeds.xml', 'mediasources.xml'
    )
    for name in safe_files:
        copy_if_readable(os.path.join(userdata, name), os.path.join(root, 'userdata', name))

    keymaps = os.path.join(userdata, 'keymaps')
    if os.path.isdir(keymaps):
        try:
            shutil.copytree(keymaps, os.path.join(root, 'userdata', 'keymaps'), dirs_exist_ok=True)
        except (PermissionError, OSError) as e:
            log('Backup skipped keymaps: ' + str(e), xbmc.LOGWARNING)

    for addon in ('skin.auramod', 'service.dragonmax.voice'):
        src = os.path.join(home, 'addons', addon)
        if os.path.isdir(src):
            try:
                dst = os.path.join(root, 'addons', addon)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copytree(src, dst, dirs_exist_ok=True)
            except (PermissionError, OSError) as e:
                log('Backup skipped addon %s: %s' % (addon, e), xbmc.LOGWARNING)
    return root


def rollback(home, backup_root):
    bu = os.path.join(backup_root, 'userdata')
    if os.path.isdir(bu):
        shutil.copytree(bu, os.path.join(home, 'userdata'), dirs_exist_ok=True)
    ba = os.path.join(backup_root, 'addons')
    if os.path.isdir(ba):
        shutil.copytree(ba, os.path.join(home, 'addons'), dirs_exist_ok=True)


def apply_tree(src_root, home):
    for name in ('addons', 'userdata', 'artwork', 'audio', 'startup', 'dragonmax'):
        src = os.path.join(src_root, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(home, name), dirs_exist_ok=True)
    manifest = os.path.join(src_root, 'dragonmax_manifest.json')
    if os.path.isfile(manifest):
        shutil.copy2(manifest, os.path.join(home, 'dragonmax_manifest.json'))


def main():
    dlg = xbmcgui.Dialog()
    log('Wizard launch started, version ' + VERSION)
    try:
        build = get_json(BUILD_JSON)['builds'][0]
    except Exception as e:
        dlg.ok('DragonMax Wizard', 'Could not load staging metadata.\n\n' + str(e))
        return

    if not build.get('ready', False) and not dlg.yesno('DragonMax V12 STAGING TEST',
        'This build is not marked release-ready yet.\n\nA safe rollback backup will be created before installation.\n\nInstall this staging build now?'):
        return

    home = xbmcvfs.translatePath('special://home/')
    userdata = xbmcvfs.translatePath('special://userdata/')
    try:
        free = xbmcvfs.getDiskSpace(home)
    except Exception:
        free = 0
    if free and free < 600 * 1024 * 1024:
        dlg.ok('DragonMax Wizard', 'At least 600 MB free space is required for safe staging and rollback.')
        return

    work = work_path()
    zpath, extract = os.path.join(work, 'dragonmax.zip'), os.path.join(work, 'extract')
    backup_root = None
    try:
        note('Downloading DragonMax V12...')
        download(PAYLOAD, zpath)
        if os.path.getsize(zpath) < float(build.get('minimum_size_mb', 60)) * 1024 * 1024:
            raise RuntimeError('Downloaded payload is smaller than the declared minimum.')
        os.makedirs(extract, exist_ok=True)
        with zipfile.ZipFile(zpath) as z:
            bad = z.testzip()
            if bad:
                raise RuntimeError('Corrupt ZIP member: ' + bad)
            z.extractall(extract)
        roots = [os.path.join(extract, n) for n in os.listdir(extract) if os.path.isdir(os.path.join(extract, n))]
        if len(roots) != 1:
            raise RuntimeError('Unexpected payload layout.')
        root = roots[0]
        required = [os.path.join(root, 'addons', 'skin.auramod'), os.path.join(root, 'addons', 'service.dragonmax.voice'), os.path.join(root, 'userdata'), os.path.join(root, 'dragonmax', 'config')]
        if any(not os.path.exists(p) for p in required):
            raise RuntimeError('Payload is missing required DragonMax components.')

        note('Creating safe rollback backup...')
        backup_root = backup(home, userdata)
        note('Applying DragonMax V12...')
        apply_tree(root, home)
        dlg.ok('DragonMax V12 Installed', 'Staging installation completed.\n\nFully exit Kodi, reopen it, then begin device testing.\n\nRollback backup: ' + backup_root)
    except Exception as e:
        log(traceback.format_exc(), xbmc.LOGERROR)
        if backup_root:
            try:
                rollback(home, backup_root)
                dlg.ok('DragonMax Install Failed', str(e) + '\n\nRollback was applied.')
            except Exception as re:
                dlg.ok('DragonMax Install Failed', str(e) + '\n\nRollback also failed: ' + str(re))
        else:
            dlg.ok('DragonMax Install Failed', str(e))
    finally:
        shutil.rmtree(work, ignore_errors=True)


try:
    main()
except BaseException as e:
    log(traceback.format_exc(), xbmc.LOGERROR)
    try:
        xbmcgui.Dialog().ok('DragonMax Wizard Startup Error', str(e))
    except Exception:
        pass
'''


def zip_bytes(folder, files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(folder + '/' + name, text)
    return out.getvalue()


def addon_fragment(xml_text):
    return xml_text.replace(XML_DECL, '', 1).strip()


def publish(root: Path, out: Path):
    addons = XML_DECL + '\n<addons>\n' + addon_fragment(REPO_ADDON) + '\n' + addon_fragment(WIZARD_ADDON) + '\n</addons>\n'
    compile(WIZARD_DEFAULT, 'default.py', 'exec')
    import xml.etree.ElementTree as ET
    ET.fromstring(addons)
    (out / 'addons.xml').write_text(addons, encoding='utf-8')
    (out / 'addons.xml.md5').write_text(hashlib.md5(addons.encode('utf-8')).hexdigest(), encoding='utf-8')
    repo_zip = zip_bytes('repository.dragonmax', {'addon.xml': REPO_ADDON})
    wizard_zip = zip_bytes('plugin.program.dragonmaxwizard', {'addon.xml': WIZARD_ADDON, 'default.py': WIZARD_DEFAULT})
    for addon_id, data in (('repository.dragonmax', repo_zip), ('plugin.program.dragonmaxwizard', wizard_zip)):
        root_zip = out / f'{addon_id}-{VERSION}.zip'
        addon_dir = out / addon_id
        addon_dir.mkdir(parents=True, exist_ok=True)
        root_zip.write_bytes(data)
        (addon_dir / f'{addon_id}-{VERSION}.zip').write_bytes(data)
        with zipfile.ZipFile(root_zip) as z:
            bad = z.testzip()
            if bad:
                raise RuntimeError('Corrupt generated installer ZIP member: ' + bad)
    print('DragonMax repository and wizard 4.0.4 generated; live Kodi database backup is safely skipped.')
