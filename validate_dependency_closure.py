#!/usr/bin/env python3
import json
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
CORE_PREFIXES = ('xbmc.', 'kodi.')
ROOTS = ('skin.auramod', 'service.dragonmax.voice', 'plugin.program.dragonmaxportal')


def version_tuple(value):
    out=[]; token=''
    for ch in str(value):
        if ch.isdigit(): token += ch
        elif token: out.append(int(token)); token=''
    if token: out.append(int(token))
    return tuple(out or [0])


def main():
    errors=[]
    build=json.loads((PUBLIC/'build.json').read_text(encoding='utf-8'))['builds'][0]
    payload=PUBLIC/build['zip']
    with zipfile.ZipFile(payload) as z:
        addons={}
        for name in z.namelist():
            rel=name.replace('\\','/').strip('/')
            parts=rel.split('/',1)
            rel=parts[1] if len(parts)==2 else parts[0]
            if not (rel.startswith('addons/') and rel.endswith('/addon.xml') and rel.count('/')==2):
                continue
            root=ET.fromstring(z.read(name).decode('utf-8'))
            req=[]
            requires=root.find('requires')
            if requires is not None:
                for node in requires.findall('import'):
                    req.append((node.attrib.get('addon',''),node.attrib.get('version','0'),node.attrib.get('optional','').lower()=='true'))
            addons[root.attrib.get('id','')]={'version':root.attrib.get('version','0'),'imports':req}

        queue=list(ROOTS); seen=set()
        for root in ROOTS:
            if root not in addons: errors.append('launch root missing: '+root)
        while queue:
            aid=queue.pop(0)
            if aid in seen or aid not in addons: continue
            seen.add(aid)
            for dep,minimum,optional in addons[aid]['imports']:
                if optional or not dep or dep.startswith(CORE_PREFIXES): continue
                if dep not in addons:
                    errors.append(f'{aid} -> {dep}>={minimum} is not bundled')
                    continue
                if version_tuple(addons[dep]['version']) < version_tuple(minimum):
                    errors.append(f'{aid} requires {dep}>={minimum}, bundled {addons[dep]["version"]}')
                queue.append(dep)

        portal='addons/plugin.program.dragonmaxportal/addon.xml'
        if portal not in {n.replace('\\','/').split('/',1)[-1] for n in z.namelist()}:
            errors.append('Dragon Portal missing from payload')

        service_names=[n for n in z.namelist() if n.replace('\\','/').endswith('/addons/service.dragonmax.voice/service.py')]
        if service_names:
            service=z.read(service_names[0]).decode('utf-8',errors='ignore')
            for token in ('required_skin_dependencies','plugin.program.dragonmaxportal','ElementTree'):
                if token not in service: errors.append('activation service missing '+token)
        else:
            errors.append('Dragon Voice service source missing')

        keymaps=[n for n in z.namelist() if n.replace('\\','/').endswith('/userdata/keymaps/dragonmax.xml')]
        if not keymaps:
            errors.append('DragonMax keymap missing')
        else:
            text=z.read(keymaps[0]).decode('utf-8',errors='ignore')
            if 'plugin.program.dragonmaxportal' not in text: errors.append('DragonMax keymap does not open native Dragon Portal')

    if errors:
        for e in sorted(set(errors)): print('ERROR:',e)
        return 1
    print('DragonMax strict dependency closure gate passed.')
    print('All mandatory launch dependencies are physically bundled and version-satisfied.')
    return 0


if __name__=='__main__':
    sys.exit(main())
