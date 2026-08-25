#!/usr/bin/env python3
import ast
import hashlib
import io
import zipfile
from pathlib import Path

VERSION = '4.2.1'
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
    <summary>DragonMax V12 guarded transactional installer</summary>
    <description>Verifies the full payload, installs only allowlisted Kodi roots, safely ignores legacy wrapper debris, preflights destinations, and rolls back failed applies.</description>
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
VERSION = '4.2.1'

ALLOWED_ROOTS = ('addons/', 'userdata/', 'artwork/', 'audio/', 'startup/', 'dragonmax/')
METADATA_ONLY = {'dragonmax_manifest.json', 'dragonmax/install_manifest.json'}
PROTECTED_PREFIXES = (
    'userdata/Database/', 'userdata/Thumbnails/', 'userdata/temp/',
    'addons/packages/', 'temp/', 'cache/', 'dragonmax_backups/',
)
PROTECTED_FILES = {'userdata/guisettings.xml'}


def log(msg, level=xbmc.LOGINFO):
    xbmc.log('[DragonMaxWizard] ' + str(msg), level)


def progress_create(progress, title, message=''):
    progress.create(title, message)


def progress_update(progress, percent, message=''):
    progress.update(int(max(0, min(100, percent))), message)


def normalized(rel):
    return rel.replace('\\', '/').lstrip('/')


def protected(rel):
    rel = normalized(rel)
    return rel in PROTECTED_FILES or any(rel.startswith(p) for p in PROTECTED_PREFIXES)


def installable(rel):
    rel = normalized(rel)
    if rel in METADATA_ONLY or protected(rel):
        return False
    return any(rel.startswith(root) for root in ALLOWED_ROOTS)


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
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Kodi/21 DragonMaxWizard/' + VERSION,
        'Accept': '*/*', 'Connection': 'close',
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


def download(url, dst, progress=None):
    with request(url, 300) as r, open(dst, 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0)
        done = 0
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress and total:
                progress_update(progress, min(20, done * 20 / total), 'Downloading DragonMax V12')


def safe_extract(zpath, extract, progress):
    with zipfile.ZipFile(zpath) as z:
        members = z.infolist()
        total = max(1, len(members))
        root_abs = os.path.abspath(extract)
        for i, member in enumerate(members, 1):
            name = member.filename.replace('\\', '/')
            target = os.path.abspath(os.path.join(extract, name))
            if target != root_abs and not target.startswith(root_abs + os.sep):
                raise RuntimeError('Unsafe ZIP path rejected: ' + name)
            z.extract(member, extract)
            if i == 1 or i == total or i % 25 == 0:
                progress_update(progress, 25 + (20 * i / total), 'Testing and extracting package\n' + name[-70:])


def verify_install_manifest(root, progress):
    manifest_path = os.path.join(root, 'dragonmax', 'install_manifest.json')
    if not os.path.isfile(manifest_path):
        raise RuntimeError('Payload install manifest is missing.')
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    expected = [row for row in manifest.get('files', []) if isinstance(row, dict) and row.get('path')]
    if not expected:
        raise RuntimeError('Payload install manifest is empty.')
    skipped = []
    total = max(1, len(expected))
    for i, row in enumerate(expected, 1):
        rel = normalized(row['path'])
        if protected(rel):
            raise RuntimeError('Payload manifest contains protected Kodi runtime state: ' + rel)
        path = os.path.join(root, rel.replace('/', os.sep))
        if not os.path.isfile(path):
            raise RuntimeError('Payload manifest references a missing file: ' + rel)
        if os.path.getsize(path) != int(row['size']):
            raise RuntimeError('Payload file size mismatch: ' + rel)
        if sha256_file(path).lower() != str(row['sha256']).lower():
            raise RuntimeError('Payload file checksum mismatch: ' + rel)
        if rel not in METADATA_ONLY and not any(rel.startswith(r) for r in ALLOWED_ROOTS):
            skipped.append(rel)
        if i == 1 or i == total or i % 50 == 0:
            progress_update(progress, 45 + (10 * i / total), 'Verifying payload files\n' + rel[-70:])
    return skipped


def payload_files(root):
    rows = []
    for base, _dirs, files in os.walk(root):
        for name in files:
            src = os.path.join(base, name)
            rel = normalized(os.path.relpath(src, root))
            if installable(rel):
                rows.append((rel, src))
    rows.sort(key=lambda x: x[0])
    return rows


def preflight_destinations(home, files):
    roots = set()
    for rel, _src in files:
        top = rel.split('/', 1)[0]
        roots.add(os.path.join(home, top))
    for target_root in sorted(roots):
        parent = target_root if os.path.isdir(target_root) else home
        probe = os.path.join(parent, '.dragonmax-write-probe')
        try:
            with open(probe, 'wb') as f:
                f.write(b'ok')
            os.remove(probe)
        except Exception as e:
            raise RuntimeError('DragonMax cannot write to required Kodi location: %s (%s)' % (parent, e))


def backup_targets(home, files, backup_root, progress):
    originals, created = [], []
    total = max(1, len(files))
    for i, (rel, _src) in enumerate(files, 1):
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
        if i == 1 or i == total or i % 50 == 0:
            progress_update(progress, 55 + (5 * i / total), 'Preparing rollback set\n' + rel[-70:])
    with open(os.path.join(backup_root, 'transaction.json'), 'w', encoding='utf-8') as f:
        json.dump({'version': VERSION, 'created': created, 'originals': originals}, f, indent=2)
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
            progress_update(progress, 60 + (40 * i / total), 'Applying DragonMax V12\n' + rel[-70:])


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
        dlg.ok('DragonMax Wizard', 'The server payload is not using the current safe install protocol yet.')
        return

    if not build.get('ready', False) and not dlg.yesno(
        'DragonMax V12 STAGING TEST',
        'This installer verifies the entire payload, installs only approved Kodi roots, safely skips legacy wrapper debris, preflights writes, backs up touched files, and rolls back failed applies.\n\nInstall now?'
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
    originals, created = [], []

    try:
        progress_create(progress, 'DragonMax Wizard', 'Downloading DragonMax V12')
        payload_url = HOST + str(build['zip']).lstrip('/')
        download(payload_url, zpath, progress)
        progress_update(progress, 20, 'Validating download')

        minimum = float(build.get('minimum_size_mb', 60)) * 1024 * 1024
        if os.path.getsize(zpath) < minimum:
            raise RuntimeError('Downloaded payload is smaller than the declared minimum.')
        expected_sha = str(build.get('sha256', '')).strip().lower()
        if not expected_sha:
            raise RuntimeError('Server did not publish a payload SHA-256 checksum.')
        if sha256_file(zpath).lower() != expected_sha:
            raise RuntimeError('Downloaded payload checksum does not match the server manifest.')

        os.makedirs(extract, exist_ok=True)
        progress_update(progress, 25, 'Testing and extracting package')
        safe_extract(zpath, extract, progress)

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

        progress_update(progress, 45, 'Verifying every payload file')
        skipped = verify_install_manifest(root, progress)
        if skipped:
            log('Verified and skipped %d non-installable legacy/metadata paths. First: %s' % (len(skipped), skipped[0]), xbmc.LOGWARNING)
            progress_update(progress, 55, 'Ignoring verified legacy wrapper debris\n%d non-installable files' % len(skipped))

        files = payload_files(root)
        if not files:
            raise RuntimeError('No installable files were found in the payload.')

        progress_update(progress, 56, 'Preflighting destination permissions')
        preflight_destinations(home, files)
        os.makedirs(backup_root, exist_ok=True)
        originals, created = backup_targets(home, files, backup_root, progress)

        progress_update(progress, 60, 'Applying DragonMax V12')
        apply_files(home, files, progress)
        progress_update(progress, 100, 'Installation complete')
        progress.close()
        dlg.ok('DragonMax V12 Installed', 'DragonMax V12 installed successfully.\n\nFully exit Kodi and reopen it before testing.\n\nRollback data: ' + backup_root)
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


def validate_wizard_static_gates(source):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ('create', 'update') and isinstance(node.func.value, ast.Name) and node.func.value.id == 'progress' and len(node.args) > 2:
                raise RuntimeError('Kodi DialogProgress API gate failed: %s called with %d positional args' % (node.func.attr, len(node.args)))
    required = ['ALLOWED_ROOTS', 'METADATA_ONLY', 'preflight_destinations', 'safe_extract', 'rollback_transaction', 'skipped = verify_install_manifest']
    for token in required:
        if token not in source:
            raise RuntimeError('Installer safety gate missing: ' + token)
    if 'Payload contains unexpected non-installable paths' in source:
        raise RuntimeError('Legacy-wrapper false-positive gate regression detected')


def publish(root: Path, out: Path):
    addons = XML_DECL + '\n<addons>\n' + addon_fragment(REPO_ADDON) + '\n' + addon_fragment(WIZARD_ADDON) + '\n</addons>\n'
    compile(WIZARD_DEFAULT, 'default.py', 'exec')
    validate_wizard_static_gates(WIZARD_DEFAULT)
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
    print('DragonMax repository and wizard 4.2.1 generated; legacy wrapper skip and Superman gates passed.')
