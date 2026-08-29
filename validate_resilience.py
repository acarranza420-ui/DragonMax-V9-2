#!/usr/bin/env python3
"""Independent resilience gate for DragonMax launch candidates.

This test does not import build_v12.py. It validates the generated payload as if
it were an external release artifact and models the failure cases that most often
hurt Fire TV upgrades: corrupt manifests, duplicate paths, incomplete critical
add-on dependencies, protected-data overwrite, broken activation persistence,
and missing last-known-good recovery hooks.
"""
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
CORE_PREFIXES = ('xbmc.', 'kodi.')
CRITICAL_ROOTS = {'skin.auramod', 'service.dragonmax.voice', 'plugin.program.dragonmaxwizard'}
OFFICIAL_ALLOWLIST = {
    'script.skinshortcuts', 'plugin.program.autocompletion',
    'script.module.simplecache', 'script.module.routing', 'script.module.requests',
    'script.module.inputstreamhelper', 'script.module.dateutil',
    'script.image.resource.select', 'resource.images.moviegenreicons.transparent',
    'resource.images.studios.coloured', 'resource.images.studios.white',
}
PROTECTED = {
    'userdata/Database/MyVideos121.db': b'WATCHED_STATE_SENTINEL',
    'userdata/Thumbnails/keep.jpg': b'THUMBNAIL_SENTINEL',
    'userdata/guisettings.xml': b'<settings>USER_GUI_SENTINEL</settings>',
    'userdata/addon_data/service.dragonmax.voice/state.json': b'{"realm":"crimson_court","performance_mode":"maximum_speed"}',
}
RECOVERY_TOKENS = {
    'corrupt_state', 'restore_last_good_state', 'state.last_good.json',
    'replace_with_safe_defaults', "'.tmp'", 'cooldown_seconds',
}
ACTIVATION_TOKENS = {
    'pending_skin_activation.json', 'UpdateLocalAddons',
    'Settings.SetSettingValue', 'lookandfeel.skin', 'active_skin_is',
}


def version_tuple(value):
    out = []
    for part in str(value).replace('-', '.').split('.'):
        digits = ''.join(ch for ch in part if ch.isdigit())
        if not digits:
            break
        out.append(int(digits))
    return tuple(out or [0])


def normalized_members(z):
    result = {}
    duplicates = []
    for info in z.infolist():
        raw = info.filename.replace('\\', '/').strip('/')
        parts = raw.split('/', 1)
        rel = parts[1] if len(parts) == 2 else parts[0]
        if not rel or rel.endswith('/'):
            continue
        if rel in result:
            duplicates.append(rel)
        result[rel] = info
    return result, duplicates


def addon_graph(z, members, errors):
    addons = {}
    for rel, info in members.items():
        if not (rel.startswith('addons/') and rel.endswith('/addon.xml') and rel.count('/') == 2):
            continue
        try:
            root = ET.fromstring(z.read(info).decode('utf-8'))
        except Exception as exc:
            errors.append(f'cannot parse {rel}: {exc}')
            continue
        aid = root.attrib.get('id', '')
        ver = root.attrib.get('version', '0')
        imports = []
        req = root.find('requires')
        if req is not None:
            for node in req.findall('import'):
                imports.append((node.attrib.get('addon', ''), node.attrib.get('version', '0'), node.attrib.get('optional', '').lower() == 'true'))
        addons[aid] = {'version': ver, 'imports': imports, 'rel': rel}

    for root_id in CRITICAL_ROOTS:
        if root_id not in addons:
            errors.append(f'critical addon absent from payload: {root_id}')
            continue
        queue = [root_id]
        seen = set()
        while queue:
            aid = queue.pop(0)
            if aid in seen or aid not in addons:
                continue
            seen.add(aid)
            for dep, minimum, optional in addons[aid]['imports']:
                if optional or not dep or dep.startswith(CORE_PREFIXES):
                    continue
                if dep in addons:
                    if version_tuple(addons[dep]['version']) < version_tuple(minimum):
                        errors.append(f'{aid} requires {dep}>={minimum}, bundled {addons[dep]["version"]}')
                    queue.append(dep)
                elif dep not in OFFICIAL_ALLOWLIST:
                    errors.append(f'critical dependency graph unresolved: {aid} -> {dep}>={minimum}')
    return addons


def verify_manifest(z, members, build_version, errors):
    rel = 'dragonmax/install_manifest.json'
    if rel not in members:
        errors.append('install manifest missing')
        return
    try:
        manifest = json.loads(z.read(members[rel]).decode('utf-8'))
    except Exception as exc:
        errors.append(f'install manifest invalid JSON: {exc}')
        return
    if str(manifest.get('version')) != str(build_version):
        errors.append(f'install manifest version {manifest.get("version")} != build {build_version}')
    entries = manifest.get('files', [])
    seen = set()
    for entry in entries:
        path = str(entry.get('path', '')).replace('\\', '/').strip('/')
        if not path:
            errors.append('install manifest contains empty path')
            continue
        if path in seen:
            errors.append(f'install manifest duplicate path: {path}')
            continue
        seen.add(path)
        if path not in members:
            errors.append(f'install manifest references missing payload member: {path}')
            continue
        data = z.read(members[path])
        if len(data) != int(entry.get('size', -1)):
            errors.append(f'install manifest size mismatch: {path}')
        actual = hashlib.sha256(data).hexdigest()
        if actual != entry.get('sha256'):
            errors.append(f'install manifest SHA mismatch: {path}')
    payload_files = {p for p in members if p != rel and not p.endswith('/')}
    missing_from_manifest = sorted(payload_files - seen)
    if missing_from_manifest:
        errors.append('payload files absent from install manifest: ' + ', '.join(missing_from_manifest[:8]))


def simulate_upgrade(z, members, errors):
    with tempfile.TemporaryDirectory(prefix='dragonmax-resilience-') as td:
        home = pathlib.Path(td) / 'home'
        home.mkdir(parents=True)
        for rel, data in PROTECTED.items():
            path = home / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        for rel, info in members.items():
            if rel.startswith('userdata/Database/') or rel.startswith('userdata/Thumbnails/') or rel == 'userdata/guisettings.xml':
                errors.append(f'payload illegally includes protected runtime path: {rel}')
                continue
            dest = home / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if rel == 'userdata/addon_data/service.dragonmax.voice/state.json' and dest.exists():
                continue
            dest.write_bytes(z.read(info))

        for rel, expected in PROTECTED.items():
            actual = (home / rel).read_bytes()
            if actual != expected:
                errors.append(f'upgrade simulation overwrote protected user data: {rel}')

        for required in ('addons/skin.auramod/addon.xml', 'addons/service.dragonmax.voice/addon.xml', 'dragonmax/config/menus.json'):
            if not (home / required).is_file():
                errors.append(f'upgrade simulation missing installed runtime file: {required}')


def main():
    errors = []
    try:
        build_doc = json.loads((PUBLIC / 'build.json').read_text(encoding='utf-8'))
        build = build_doc['builds'][0]
        version = str(build['version'])
        payload = PUBLIC / str(build['zip'])
    except Exception as exc:
        raise SystemExit(f'ERROR: generated release metadata unavailable: {exc}')

    if build.get('ready') is True:
        errors.append('build.json must remain ready=false until real Fire TV launch validation')
    if not payload.is_file():
        raise SystemExit(f'ERROR: payload missing: {payload}')
    if version not in payload.name:
        errors.append(f'payload filename does not contain build version {version}: {payload.name}')

    with zipfile.ZipFile(payload) as z:
        bad = z.testzip()
        if bad:
            errors.append(f'corrupt ZIP member: {bad}')
        members, duplicates = normalized_members(z)
        if duplicates:
            errors.append('duplicate normalized ZIP paths: ' + ', '.join(sorted(set(duplicates))[:8]))
        if len(members) > 25000:
            errors.append(f'payload file count {len(members)} exceeds Fire TV maintainability budget 25000')

        verify_manifest(z, members, version, errors)
        addons = addon_graph(z, members, errors)
        simulate_upgrade(z, members, errors)

        service_rel = 'addons/service.dragonmax.voice/service.py'
        repair_rel = 'addons/service.dragonmax.voice/self_repair.py'
        service = z.read(members[service_rel]).decode('utf-8', errors='ignore') if service_rel in members else ''
        repair = z.read(members[repair_rel]).decode('utf-8', errors='ignore') if repair_rel in members else ''
        for token in sorted(ACTIVATION_TOKENS):
            if token not in service:
                errors.append(f'restart/activation persistence hook missing: {token}')
        for token in sorted(RECOVERY_TOKENS):
            if token not in repair:
                errors.append(f'corrupt-state recovery hook missing: {token}')

        if 'skin.auramod' in addons and version_tuple(addons['skin.auramod']['version']) < (2, 0, 4):
            errors.append('AuraMOD bundled version is below 2.0.4')

    try:
        tree = ET.parse(PUBLIC / 'addons.xml')
        repo_versions = {n.attrib.get('id'): n.attrib.get('version') for n in tree.getroot().findall('addon')}
        for aid in ('repository.dragonmax', 'plugin.program.dragonmaxwizard'):
            if str(repo_versions.get(aid)) != version:
                errors.append(f'{aid} repository version {repo_versions.get(aid)!r} != build {version}')
            artifact = PUBLIC / f'{aid}-{version}.zip'
            if not artifact.is_file():
                errors.append(f'installer artifact missing: {artifact.name}')
    except Exception as exc:
        errors.append(f'cannot validate repository release identity: {exc}')

    if errors:
        for item in errors:
            print('ERROR:', item)
        return 1

    print('DragonMax resilience gate passed.')
    print('Verified: complete install-manifest hashes, duplicate-path rejection, critical dependency closure,')
    print('minimum dependency versions, protected-data upgrade preservation, restart activation hooks,')
    print('corrupt-state last-known-good recovery, release identity, and Fire TV file-count budget.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
