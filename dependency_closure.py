#!/usr/bin/env python3
"""Resolve the complete launch-critical dependency graph into the DragonMax payload.

Third-party launch dependencies must already be explicitly bundled by DragonMax.
Missing dependencies that exist in Kodi's official Omega catalog are downloaded
and staged recursively until every non-optional launch dependency is closed.
Kodi-bundled system modules are accepted from the Kodi 21 runtime itself.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

KODI_OMEGA_INDEX = 'https://download.kodi.tv/addons/omega/addons.xml'
KODI_OMEGA_BASE = 'https://download.kodi.tv/addons/omega'
CORE_PREFIXES = ('xbmc.', 'kodi.')
KODI_SYSTEM_ADDONS = {
    'script.module.pil',
    'script.module.pycryptodome',
    'repository.xbmc.org',
    'resource.language.en_gb',
    'resource.uisounds.kodi',
    'skin.estuary',
}
LAUNCH_ROOTS = ('skin.auramod', 'service.dragonmax.voice', 'plugin.program.dragonmaxportal')


def version_tuple(value):
    out = []
    token = ''
    for ch in str(value):
        if ch.isdigit():
            token += ch
        elif token:
            out.append(int(token)); token = ''
    if token:
        out.append(int(token))
    return tuple(out or [0])


def addon_metadata(addon_dir):
    xml = addon_dir / 'addon.xml'
    if not xml.is_file():
        return None
    root = ET.parse(xml).getroot()
    imports = []
    req = root.find('requires')
    if req is not None:
        for node in req.findall('import'):
            imports.append((
                node.attrib.get('addon', ''),
                node.attrib.get('version', '0'),
                node.attrib.get('optional', '').lower() == 'true',
            ))
    return {'id': root.attrib.get('id', ''), 'version': root.attrib.get('version', '0'), 'imports': imports}


def staged_metadata(stage):
    addons = Path(stage) / 'addons'
    result = {}
    if not addons.is_dir():
        return result
    for child in addons.iterdir():
        if not child.is_dir():
            continue
        try:
            meta = addon_metadata(child)
        except Exception:
            continue
        if meta and meta['id']:
            result[meta['id']] = meta
    return result


def official_catalog(fetch_text):
    root = ET.fromstring(fetch_text(KODI_OMEGA_INDEX))
    catalog = {}
    for node in root.findall('addon'):
        addon_id = node.attrib.get('id', '')
        version = node.attrib.get('version', '')
        if addon_id and version:
            catalog[addon_id] = version
    return catalog


def reachable_requirements(metas):
    queue = [root for root in LAUNCH_ROOTS if root in metas]
    seen = set()
    requirements = []
    while queue:
        addon_id = queue.pop(0)
        if addon_id in seen or addon_id not in metas:
            continue
        seen.add(addon_id)
        for dep, minimum, optional in metas[addon_id]['imports']:
            if optional or not dep or dep.startswith(CORE_PREFIXES) or dep in KODI_SYSTEM_ADDONS:
                continue
            requirements.append((addon_id, dep, minimum or '0'))
            if dep in metas:
                queue.append(dep)
    return requirements


def bundle_official_dependency_closure(stage, fetch, extract_addon_zip, fetch_text):
    stage = Path(stage)
    catalog = official_catalog(fetch_text)
    installed_now = []

    for _round in range(12):
        metas = staged_metadata(stage)
        missing = []
        undersized = []
        for parent, dep, minimum in reachable_requirements(metas):
            if dep in metas:
                if version_tuple(metas[dep]['version']) < version_tuple(minimum):
                    undersized.append((parent, dep, minimum, metas[dep]['version']))
                continue
            missing.append((parent, dep, minimum))

        if undersized:
            problems = []
            for parent, dep, minimum, actual in undersized:
                official = catalog.get(dep)
                if official and version_tuple(official) >= version_tuple(minimum):
                    url = f'{KODI_OMEGA_BASE}/{dep}/{dep}-{official}.zip'
                    archive = stage.parent / ('omega_'+dep+'.zip')
                    fetch(url, archive)
                    extract_addon_zip(archive, dep)
                    installed_now.append(dep+'@'+official)
                else:
                    problems.append(f'{parent} requires {dep}>={minimum}, staged {actual}')
            if problems:
                raise RuntimeError('Launch dependency versions cannot be satisfied: ' + '; '.join(sorted(set(problems))))
            continue

        if not missing:
            print('Full launch dependency closure passed. Official Omega modules added:', ', '.join(installed_now) if installed_now else 'none')
            return

        unresolved = []
        progress = False
        for parent, dep, minimum in missing:
            official = catalog.get(dep)
            if official and version_tuple(official) >= version_tuple(minimum):
                url = f'{KODI_OMEGA_BASE}/{dep}/{dep}-{official}.zip'
                archive = stage.parent / ('omega_'+dep+'.zip')
                fetch(url, archive)
                extract_addon_zip(archive, dep)
                installed_now.append(dep+'@'+official)
                progress = True
            else:
                unresolved.append(f'{parent} -> {dep}>={minimum}')

        if unresolved:
            raise RuntimeError('Complete launch dependency graph unresolved: ' + '; '.join(sorted(set(unresolved))))
        if not progress:
            break

    raise RuntimeError('Launch dependency closure exceeded recursion limit')
