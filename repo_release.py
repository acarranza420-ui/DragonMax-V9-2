#!/usr/bin/env python3
import hashlib
import io
import json
import zipfile
from pathlib import Path

VERSION = '4.0.0'
HOST = 'https://dragonmax-v12-release.onrender.com/'
PAYLOAD = HOST + 'builds/DragonMax_V12_Unified_Build_Content-4.0.0.zip'

REPO_ADDON = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
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

WIZARD_ADDON = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="plugin.program.dragonmaxwizard" name="DragonMax Wizard" version="{VERSION}" provider-name="DragonMax RD">
  <requires><import addon="xbmc.python" version="3.0.0"/></requires>
  <extension point="xbmc.python.script" library="default.py"><provides>executable</provides></extension>
  <extension point="xbmc.addon.metadata">
    <summary>DragonMax V12 staging installer</summary>
    <description>Downloads, validates, backs up, stages, and applies DragonMax V12 Unified for device testing.</description>
    <platform>all</platform>
  </extension>
</addon>
'''

WIZARD_DEFAULT = r'''#!/usr/bin/env python3
import json, os, shutil, tempfile, urllib.request, zipfile, time
import xbmc, xbmcaddon, xbmcgui, xbmcvfs

ADDON = xbmcaddon.Addon()
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
BUILD_JSON = 'https://dragonmax-v12-release.onrender.com/build.json'
PAYLOAD = 'https://dragonmax-v12-release.onrender.com/builds/DragonMax_V12_Unified_Build_Content-4.0.0.zip'


def note(msg, ms=3500):
    xbmcgui.Dialog().notification('DragonMax Wizard', msg, xbmcgui.NOTIFICATION_INFO, ms)


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'DragonMaxWizard/4.0'})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode('utf-8'))


def download(url, dst):
    req = urllib.request.Request(url, headers={'User-Agent': 'DragonMaxWizard/4.0'})
    with urllib.request.urlopen(req, timeout=180) as r, open(dst, 'wb') as f:
        shutil.copyfileobj(r, f)


def backup(home, userdata):
    stamp = time.strftime('%Y%m%d-%H%M%S')
    root = os.path.join(PROFILE, 'backups', stamp)
    os.makedirs(root, exist_ok=True)
    if os.path.isdir(userdata):
        shutil.copytree(userdata, os.path.join(root, 'userdata'), dirs_exist_ok=True)
    for addon in ('skin.auramod', 'service.dragonmax.voice'):
        src = os.path.join(home, 'addons', addon)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(root, 'addons', addon), dirs_exist_ok=True)
    return root


def rollback(home, backup_root):
    bu = os.path.join(backup_root, 'userdata')
    if os.path.isdir(bu):
        shutil.copytree(bu, os.path.join(home, 'userdata'), dirs_exist_ok=True)
    ba = os.path.join(backup_root, 'addons')
    if os.path.isdir(ba):
        shutil.copytree(ba, os.path.join(home, 'addons'), dirs_exist_ok=True)


def apply_tree(src_root, home):
    for name in ('addons', 'userdata'):
        src = os.path.join(src_root, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(home, name), dirs_exist_ok=True)
    for name in ('artwork', 'audio', 'startup', 'dragonmax'):
        src = os.path.join(src_root, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(home, name), dirs_exist_ok=True)
    manifest = os.path.join(src_root, 'dragonmax_manifest.json')
    if os.path.isfile(manifest):
        shutil.copy2(manifest, os.path.join(home, 'dragonmax_manifest.json'))


def main():
    dlg = xbmcgui.Dialog()
    backup_root = None
    try:
        meta = get_json(BUILD_JSON)
        build = meta['builds'][0]
    except Exception as e:
        dlg.ok('DragonMax Wizard', 'Could not load staging metadata.\n\n' + str(e))
        return

    if not build.get('ready', False):
        if not dlg.yesno('DragonMax V12 STAGING TEST',
                         'This build is intentionally not marked release-ready yet.\n\n'
                         'A rollback backup will be created before installation.\n\n'
                         'Install this staging build now?'):
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

    work = tempfile.mkdtemp(prefix='dragonmax-v12-')
    zpath = os.path.join(work, 'dragonmax.zip')
    extract = os.path.join(work, 'extract')
    try:
        note('Downloading DragonMax V12...')
        download(PAYLOAD, zpath)
        minimum = float(build.get('minimum_size_mb', 60)) * 1024 * 1024
        if os.path.getsize(zpath) < minimum:
            raise RuntimeError('Downloaded payload is smaller than the declared minimum.')
        with zipfile.ZipFile(zpath) as z:
            bad = z.testzip()
            if bad:
                raise RuntimeError('Corrupt ZIP member: ' + bad)
            z.extractall(extract)
        roots = [os.path.join(extract, n) for n in os.listdir(extract) if os.path.isdir(os.path.join(extract, n))]
        if len(roots) != 1:
            raise RuntimeError('Unexpected payload layout.')
        root = roots[0]
        required = [
            os.path.join(root, 'addons', 'skin.auramod'),
            os.path.join(root, 'addons', 'service.dragonmax.voice'),
            os.path.join(root, 'userdata'),
            os.path.join(root, 'dragonmax', 'config'),
        ]
        if any(not os.path.exists(p) for p in required):
            raise RuntimeError('Payload is missing required DragonMax components.')

        note('Creating rollback backup...')
        backup_root = backup(home, userdata)
        note('Applying DragonMax V12...')
        apply_tree(root, home)
        dlg.ok('DragonMax V12 Installed',
               'Staging installation completed.\n\n'
               'Fully exit Kodi, reopen it, then begin device testing.\n\n'
               'Rollback backup: ' + backup_root)
    except Exception as e:
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


if __name__ == '__main__':
    main()
'''


def zip_bytes(folder, files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, text in files.items():
            z.writestr(folder + '/' + name, text)
    return out.getvalue()


def publish(root: Path, out: Path):
    addons = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n' + REPO_ADDON + '\n' + WIZARD_ADDON + '\n</addons>\n'
    (out / 'addons.xml').write_text(addons, encoding='utf-8')
    (out / 'addons.xml.md5').write_text(hashlib.md5(addons.encode('utf-8')).hexdigest(), encoding='utf-8')
    (out / 'repository.dragonmax-4.0.0.zip').write_bytes(zip_bytes('repository.dragonmax', {'addon.xml': REPO_ADDON}))
    (out / 'plugin.program.dragonmaxwizard-4.0.0.zip').write_bytes(zip_bytes('plugin.program.dragonmaxwizard', {'addon.xml': WIZARD_ADDON, 'default.py': WIZARD_DEFAULT}))
    for name in ('repository.dragonmax-4.0.0.zip', 'plugin.program.dragonmaxwizard-4.0.0.zip'):
        with zipfile.ZipFile(out / name) as z:
            bad = z.testzip()
            if bad:
                raise RuntimeError('Corrupt generated installer ZIP member: ' + bad)
    print('DragonMax repository and wizard 4.0.0 artifacts generated.')
