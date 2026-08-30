#!/usr/bin/env python3
"""Comprehensive independent DragonMax release audit."""
import json
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
CORE_PREFIXES = ('xbmc.', 'kodi.')
LAUNCH_ROOTS = ('skin.auramod', 'service.dragonmax.voice', 'plugin.program.dragonmaxportal')
TRANSITIVE_OFFICIAL = {
    'script.module.simplecache', 'script.module.routing',
    'script.module.inputstreamhelper', 'script.module.dateutil',
    'script.module.simplejson', 'script.module.pil',
    'script.module.addon.signals', 'script.module.qrcode',
    'script.module.beautifulsoup4', 'script.module.arrow',
    'script.module.certifi', 'script.module.chardet',
    'script.module.idna', 'script.module.urllib3',
    'script.module.autocompletion',
}
DRAGONMAX_HOME = [
    'Dragon Portal', 'Continue Watching', 'Movies', 'TV Shows',
    'Anime Universe', 'Martial Arts', 'Champion Guild',
    'Office Consortium', 'Settings',
]


def version_tuple(value):
    parts = []
    for piece in str(value).replace('-', '.').replace('+', '.').split('.'):
        digits = ''.join(ch for ch in piece if ch.isdigit())
        if not digits: break
        parts.append(int(digits))
    return tuple(parts or [0])


def member_map(z):
    out = {}
    for info in z.infolist():
        name = info.filename.replace('\\', '/').strip('/')
        bits = name.split('/', 1)
        rel = bits[1] if len(bits) == 2 else bits[0]
        if rel and not rel.endswith('/'): out[rel] = info
    return out


def addon_graph(z, members, errors):
    addons = {}
    for rel, info in members.items():
        if not (rel.startswith('addons/') and rel.endswith('/addon.xml') and rel.count('/') == 2): continue
        try: root = ET.fromstring(z.read(info).decode('utf-8'))
        except Exception as exc:
            errors.append(f'cannot parse {rel}: {exc}'); continue
        imports = []
        req = root.find('requires')
        if req is not None:
            for node in req.findall('import'):
                imports.append((node.attrib.get('addon',''), node.attrib.get('version','0'), node.attrib.get('optional','').lower() == 'true'))
        addons[root.attrib.get('id','')] = {'version':root.attrib.get('version','0'),'imports':imports,'rel':rel}
    return addons


def audit_direct_auramod(addons, errors):
    skin = addons.get('skin.auramod')
    if not skin:
        errors.append('AuraMOD is absent from payload'); return
    for dep, minimum, optional in skin['imports']:
        if optional or not dep or dep.startswith(CORE_PREFIXES): continue
        if dep not in addons:
            errors.append(f'AuraMOD direct dependency is not bundled: {dep}>={minimum}'); continue
        if version_tuple(addons[dep]['version']) < version_tuple(minimum):
            errors.append(f'AuraMOD requires {dep}>={minimum}, bundled {addons[dep]["version"]}')


def audit_recursive(addons, errors):
    queue = list(LAUNCH_ROOTS); seen = set()
    while queue:
        aid = queue.pop(0)
        if aid in seen: continue
        seen.add(aid); meta = addons.get(aid)
        if meta is None:
            errors.append(f'launch runtime addon missing: {aid}'); continue
        for dep, minimum, optional in meta['imports']:
            if optional or not dep or dep.startswith(CORE_PREFIXES): continue
            if dep in addons:
                if version_tuple(addons[dep]['version']) < version_tuple(minimum):
                    errors.append(f'{aid} requires {dep}>={minimum}, bundled {addons[dep]["version"]}')
                queue.append(dep)
            elif dep not in TRANSITIVE_OFFICIAL:
                errors.append(f'unresolved recursive launch dependency: {aid} -> {dep}>={minimum}')


def audit_portal(z, members, addons, errors):
    if 'plugin.program.dragonmaxportal' not in addons: errors.append('Dragon Portal add-on is not bundled')
    portal_default = 'addons/plugin.program.dragonmaxportal/default.py'
    if portal_default not in members: errors.append('Dragon Portal runtime entrypoint is missing')
    service_rel = 'addons/service.dragonmax.voice/service.py'
    service = z.read(members[service_rel]).decode('utf-8', errors='ignore') if service_rel in members else ''
    if 'plugin.program.dragonmaxportal' not in service: errors.append('Dragon Voice is not wired to the native Dragon Portal')
    if 'plugin.program.dragonmaxwizard,return' in service: errors.append('Dragon Voice still contains stale Wizard-as-Portal routing')
    if 'required_skin_dependencies' not in service or 'addon.xml' not in service: errors.append('activation service is not deriving skin blockers from packaged addon metadata')


def audit_dragonmax_home(z, members, errors):
    rel = 'addons/skin.auramod/shortcuts/mainmenu.DATA.xml'
    if rel not in members:
        errors.append('DragonMax native AuraMOD main menu is missing'); return
    try:
        root = ET.fromstring(z.read(members[rel]).decode('utf-8'))
    except Exception as exc:
        errors.append('DragonMax AuraMOD main menu XML invalid: '+str(exc)); return
    labels = [str(node.findtext('label') or '') for node in root.findall('shortcut')]
    if labels != DRAGONMAX_HOME:
        errors.append('AuraMOD would not boot to the DragonMax home; menu labels='+repr(labels))
    text = z.read(members[rel]).decode('utf-8', errors='ignore')
    if 'plugin://plugin.program.dragonmaxportal/' not in text:
        errors.append('DragonMax home does not route to native Dragon Portal')
    for token in ('animeuniverse','martialarts','championguild','officeconsortium'):
        if token not in text: errors.append('DragonMax themed home item missing: '+token)


def audit_payload_policy(members, errors):
    forbidden = ('userdata/Database/', 'userdata/Thumbnails/', 'addons/packages/')
    for rel in members:
        if any(rel.startswith(prefix) for prefix in forbidden): errors.append('protected/volatile runtime content leaked into payload: '+rel)
    if 'userdata/guisettings.xml' in members: errors.append('live guisettings.xml must not be shipped')


def main():
    errors = []
    try:
        build_doc = json.loads((PUBLIC/'build.json').read_text(encoding='utf-8'))
        build = build_doc['builds'][0]
        payload = PUBLIC/str(build['zip'])
    except Exception as exc:
        raise SystemExit('ERROR: cannot load generated release metadata: '+str(exc))
    if not payload.is_file(): raise SystemExit('ERROR: generated payload missing: '+str(payload))

    with zipfile.ZipFile(payload) as z:
        bad = z.testzip()
        if bad: errors.append('corrupt ZIP member: '+bad)
        members = member_map(z)
        addons = addon_graph(z, members, errors)
        audit_direct_auramod(addons, errors)
        audit_recursive(addons, errors)
        audit_portal(z, members, addons, errors)
        audit_dragonmax_home(z, members, errors)
        audit_payload_policy(members, errors)

    if errors:
        for item in sorted(set(errors)): print('ERROR:', item)
        return 1
    print('DragonMax comprehensive release audit passed.')
    print('Verified dependency closure, native Dragon Portal, DragonMax-owned AuraMOD home,')
    print('metadata-driven activation, and protected Fire TV runtime paths.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
