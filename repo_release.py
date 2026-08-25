#!/usr/bin/env python3
import hashlib
import io
import zipfile
from pathlib import Path

VERSION = '4.1.0'
HOST = 'https://dragonmax-v12-release.onrender.com/'
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
    <summary>DragonMax V12 transactional staging installer</summary>
    <description>Preflights, downloads, verifies, backs up only touched files, safely applies DragonMax, and rolls back failed installs.</description>
    <platform>all</platform>
  </extension>
</addon>
'''

WIZARD_DEFAULT = r'''#!/usr/bin/env python3
import hashlib
import json
import os
import shutil
import time
import traceback
import urllib.request
import zipfile

import xbmc
import xbmcgui
import xbmcvfs

HOST = 'https://dragonmax-v12-release.onrender.com/'
BUILD_JSON = HOST + 'build.json'
ADDON_ID = 'plugin.program.dragonmaxwizard'
VERSION = '4.1.0'
PROTECTED = (
    'userdata/Database/',
    'userdata/Thumbnails/',
    'userdata/temp/',
    'addons/packages/',
    'temp/',
    'cache/',
    'dragonmax_backups/',
)
PROTECTED_FILES = {'userdata/guisettings.xml'}


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[DragonMaxWizard] ' + str(msg), level)


def profile_path():
    path = xbmcvfs.translatePath('special://profile/addon_data/' + ADDON_ID + '/')
    os.makedirs(path, exist_ok=True)
    return path


def work_path():
    candidates = [
        xbmcvfs.translatePath('special://temp/dragonmax-v12/'),
        os.path.join(profile_path(), 'work'),
    ]
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
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Kodi/21 DragonMaxWizard/' + VERSION,
        'Accept': '*/*',
        'Connection': 'close',
    })
    return urllib.request.urlopen(req, timeout=timeout)


def get_json(url):
    with request(url, 45) as r:
        return json.loads(r.read().decode('utf-8'))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(url, dst):
    with request(url, 300) as r, open(dst, 'wb') as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)


def normalized(rel):
    return rel.replace('\\', '/').lstrip('/')


def protected(rel):
    rel = normalized(rel)
    if rel in PROTECTED_FILES:
        return True
    return any(rel.startswith(prefix) for prefix in PROTECTED)


def payload_files(root):
    rows = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not protected(normalized(os.path.relpath(os.path.join(base, d), root)) + '/')]
        for name in files:
            src = os.path.join(base, name)
            rel = normalized(os.path.relpath(src, root))
            if not protected(rel):
                rows.append((rel, src))
    return rows


def verify_install_manifest(root):
    manifest_path = os.path.join(root, 'dragonmax', 'install_manifest.json')
    if not os.path.isfile(manifest_path):
        raise RuntimeError('Payload install manifest is missing.')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    expected = {normalized(row['path']): row for row in manifest.get('files', [])}
    if not expected:
        raise RuntimeError('Payload install manifest is empty.')
    for rel, row in expected.items():
        if protected(rel):
            raise RuntimeError('Payload manifest contains protected Kodi runtime state: ' + rel)
        path = os.path.join(root, rel.replace('/', os.sep))
        if not os.path.isfile(path):
            raise RuntimeError('Payload manifest references a missing file: ' + rel)
        if os.path.getsize(path) != int(row['size']):
            raise RuntimeError('Payload file size mismatch: ' + rel)
        if sha256_file(path).lower() != str(row['sha256']).lower():
            raise RuntimeError('Payload file checksum mismatch: ' + rel)


def backup_targets(home, files, backup_root):
    originals = []
    created = []
    for rel, _src in files:
        dst = os.path.join(home, rel.replace('/', os.sep))
        if os.path.isfile(dst):
            backup = os.path.join(backup_root, 'originals', rel.replace('/', os.sep))
            try:
                os.makedirs(os.path.dirname(backup), exist_ok=True)
                shutil.copy2(dst, backup)
                originals.append((dst, backup))
            except (PermissionError, OSError) as e:
                raise RuntimeError('Cannot safely back up target before overwrite: %s (%s)' % (rel, e))
        elif not os.path.exists(dst):
            created.append(dst)
    with open(os.path.join(backup_root, 'transaction.json'), 'w', encoding='utf-8') as f:
        json.dump({'created': created, 'originals': originals}, f, indent=2)
    return originals, created


def rollback_transaction(originals, created):
    for dst in reversed(created):
        try:
            if os.path.isfile(dst) or os.path.islink(dst):
                os.remove(dst)
        except OSError:
            pass
    for dst, backup in originals:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(backup, dst)
        except OSError as e:
            log('Rollback restore failed for %s: %s' % (dst, e), xbmc.LOGERROR)


def apply_files(home, files, progress):
    total = max(1, len(files))
    for i, (rel, src) in enumerate(files, 1):
        if progress.iscanceled():
            raise RuntimeError('Installation cancelled before completion.')
        dst = os.path.join(home, rel.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        if i == 1 or i == total or i % 25 == 0:
            progress.update(int(i * 100 / total), 'Applying DragonMax V12', rel, '')


def main():
    dlg = xbmcgui.Dialog()
    progress = xbmcgui.DialogProgress()
    log('Wizard launch started, version ' + VERSION)

    try:
        build = get_json(BUILD_JSON)['builds'][0]
    except Exception as e:
        dlg.ok('DragonMax Wizard', 'Could not load staging metadata.\n\n' + str(e))
        return

    if int(build.get('install_protocol', 0)) < 2:
        dlg.ok('DragonMax Wizard', 'The server payload is not using the current safe install protocol yet. Please wait for the current deployment to finish.')
        return

    if not build.get('ready', False) and not dlg.yesno(
        'DragonMax V12 STAGING TEST',
        'This is a staging build.\n\nThe installer will verify the payload, protect Kodi runtime databases, back up only files it will change, and automatically roll back a failed apply.\n\nInstall now?'
    ):
        return

    home = xbmcvfs.translatePath('special://home/')
    try:
        free = xbmcvfs.getDiskSpace(home)
    except Exception:
        free = 0
    if free and free < 650 * 1024 * 1024:
        dlg.ok('DragonMax Wizard', 'At least 650 MB free space is required for download, extraction, and rollback staging.')
        return

    work = work_path()
    zpath = os.path.join(work, 'dragonmax.zip')
    extract = os.path.join(work, 'extract')
    stamp = time.strftime('%Y%m%d-%H%M%S')
    backup_root = os.path.join(home, 'dragonmax_backups', stamp)
    originals = []
    created = []

    try:
        progress.create('DragonMax Wizard', 'Downloading DragonMax V12', '', 'Please wait')
        payload_url = HOST + str(build['zip']).lstrip('/')
        download(payload_url, zpath)
        progress.update(20, 'Validating download', '', '')

        minimum = float(build.get('minimum_size_mb', 60)) * 1024 * 1024
        if os.path.getsize(zpath) < minimum:
            raise RuntimeError('Downloaded payload is smaller than the declared minimum.')
        expected_sha = str(build.get('sha256', '')).strip().lower()
        if not expected_sha:
            raise RuntimeError('Server did not publish a payload SHA-256 checksum.')
        actual_sha = sha256_file(zpath).lower()
        if actual_sha != expected_sha:
            raise RuntimeError('Downloaded payload checksum does not match the server manifest.')

        os.makedirs(extract, exist_ok=True)
        progress.update(30, 'Testing and extracting package', '', '')
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
            os.path.join(root, 'dragonmax', 'install_manifest.json'),
        ]
        if any(not os.path.exists(p) for p in required):
            raise RuntimeError('Payload is missing required DragonMax components.')

        progress.update(45, 'Verifying every payload file', '', '')
        verify_install_manifest(root)
        files = payload_files(root)
        if not files:
            raise RuntimeError('No installable files were found in the payload.')

        os.makedirs(backup_root, exist_ok=True)
        progress.update(55, 'Creating transactional rollback set', '', '')
        originals, created = backup_targets(home, files, backup_root)

        progress.update(60, 'Applying DragonMax V12', '', '')
        apply_files(home, files, progress)
        progress.update(100, 'Installation complete', '', '')
        progress.close()
        dlg.ok(
            'DragonMax V12 Installed',
            'Transactional staging installation completed successfully.\n\nFully exit Kodi and reopen it before testing.\n\nRollback data: ' + backup_root
        )
    except Exception as e:
        log(traceback.format_exc(), xbmc.LOGERROR)
        try:
            progress.close()
        except Exception:
            pass
        if originals or created:
            rollback_transaction(originals, created)
            dlg.ok('DragonMax Install Failed', str(e) + '\n\nAll changes made by this attempt were rolled back.')
        else:
            dlg.ok('DragonMax Install Failed', str(e) + '\n\nNo DragonMax files were applied.')
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
    print('DragonMax repository and wizard 4.1.0 generated with transactional install protocol 2.')
