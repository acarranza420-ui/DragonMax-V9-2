#!/usr/bin/env python3
"""Comprehensive independent DragonMax release audit."""
import json
import hashlib
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
CORE_PREFIXES = ('xbmc.', 'kodi.')
LAUNCH_ROOTS = ('skin.auramod', 'service.dragonmax.voice', 'plugin.program.dragonmaxportal')
TRANSITIVE_OFFICIAL = {
    'script.module.simplecache','script.module.routing','script.module.inputstreamhelper',
    'script.module.dateutil','script.module.simplejson','script.module.pil',
    'script.module.addon.signals','script.module.qrcode','script.module.beautifulsoup4',
    'script.module.arrow','script.module.certifi','script.module.chardet','script.module.idna',
    'script.module.urllib3','script.module.autocompletion',
}
REALMS = ('dragon_order','arcane_dominion','crimson_court','temple_guardians','champion_guild','office_consortium')
DRAGONMAX_HOME = ['Dragon Portal','Continue Watching','Movies','TV Shows','Sports','Anime','Music','Podcasts','Settings']


def version_tuple(value):
    parts=[]
    for piece in str(value).replace('-', '.').replace('+', '.').split('.'):
        digits=''.join(ch for ch in piece if ch.isdigit())
        if not digits: break
        parts.append(int(digits))
    return tuple(parts or [0])


def member_map(z):
    out={}
    for info in z.infolist():
        name=info.filename.replace('\\','/').strip('/')
        bits=name.split('/',1); rel=bits[1] if len(bits)==2 else bits[0]
        if rel and not rel.endswith('/'): out[rel]=info
    return out


def addon_graph(z,members,errors):
    addons={}
    for rel,info in members.items():
        if not (rel.startswith('addons/') and rel.endswith('/addon.xml') and rel.count('/')==2): continue
        try: root=ET.fromstring(z.read(info).decode('utf-8'))
        except Exception as exc: errors.append(f'cannot parse {rel}: {exc}'); continue
        imports=[]; req=root.find('requires')
        if req is not None:
            for node in req.findall('import'):
                imports.append((node.attrib.get('addon',''),node.attrib.get('version','0'),node.attrib.get('optional','').lower()=='true'))
        addons[root.attrib.get('id','')]={'version':root.attrib.get('version','0'),'imports':imports,'rel':rel}
    return addons


def audit_dependencies(addons,errors):
    skin=addons.get('skin.auramod')
    if not skin: errors.append('AuraMOD is absent from payload')
    else:
        for dep,minimum,optional in skin['imports']:
            if optional or not dep or dep.startswith(CORE_PREFIXES): continue
            if dep not in addons: errors.append(f'AuraMOD direct dependency is not bundled: {dep}>={minimum}')
            elif version_tuple(addons[dep]['version']) < version_tuple(minimum): errors.append(f'AuraMOD requires {dep}>={minimum}, bundled {addons[dep]["version"]}')
    queue=list(LAUNCH_ROOTS); seen=set()
    while queue:
        aid=queue.pop(0)
        if aid in seen: continue
        seen.add(aid); meta=addons.get(aid)
        if meta is None: errors.append(f'launch runtime addon missing: {aid}'); continue
        for dep,minimum,optional in meta['imports']:
            if optional or not dep or dep.startswith(CORE_PREFIXES): continue
            if dep in addons:
                if version_tuple(addons[dep]['version']) < version_tuple(minimum): errors.append(f'{aid} requires {dep}>={minimum}, bundled {addons[dep]["version"]}')
                queue.append(dep)
            elif dep not in TRANSITIVE_OFFICIAL: errors.append(f'unresolved recursive launch dependency: {aid} -> {dep}>={minimum}')


def audit_real_art(z,members,errors):
    expected=[]
    for realm in REALMS:
        expected.append((f'artwork/wallpapers/{realm}/{realm}_01.png',500_000,b'\x89PNG\r\n\x1a\n'))
    expected += [
        ('artwork/reference/dragonmax_v92_home_preview.png',1_000_000,b'\x89PNG\r\n\x1a\n'),
        ('startup/dragonmax_static_splash.jpg',5000,b'\xff\xd8\xff'),
        ('media/splash.jpg',5000,b'\xff\xd8\xff'),
    ]
    for rel,minimum,magic in expected:
        info=members.get(rel)
        if info is None: errors.append('real DragonMax asset missing: '+rel); continue
        data=z.read(info)
        if len(data)<minimum: errors.append(f'real DragonMax asset undersized: {rel} ({len(data)})')
        if not data.startswith(magic): errors.append('real DragonMax asset signature invalid: '+rel)
    try:
        manifest=json.loads(z.read(members['dragonmax/artwork_manifest.json']).decode('utf-8'))
        for rel,digest in manifest.get('sha256',{}).items():
            if rel not in members: errors.append('artwork manifest references missing file: '+rel)
            elif hashlib.sha256(z.read(members[rel])).hexdigest()!=digest: errors.append('artwork manifest hash mismatch: '+rel)
    except Exception as exc: errors.append('artwork manifest invalid: '+str(exc))
    for rel in members:
        if rel.startswith(('artwork/hero_banners/','artwork/realm_crests/','artwork/achievement_badges/','artwork/loading_screens/','artwork/portal_graphics/','artwork/wizard_graphics/')): errors.append('procedural/dead artwork survived: '+rel)
    if 'media/splash.png' in members: errors.append('fake-extension splash.png survived alongside JPG splash')


def audit_portal(z,members,addons,errors):
    if 'plugin.program.dragonmaxportal' not in addons: errors.append('Dragon Portal add-on is not bundled')
    rel='addons/plugin.program.dragonmaxportal/default.py'
    portal=z.read(members[rel]).decode('utf-8',errors='ignore') if rel in members else ''
    try: compile(portal,rel,'exec')
    except Exception as exc: errors.append('Dragon Portal Python invalid: '+str(exc))
    for token in ('Switch Realm','set_realm','MEDIA_SECTIONS','def build_section','Add-ons Source','video_addons','audio_addons',"'browse_movies'", "'browse_tv'", "'browse_sports'", "'browse_anime'", "'browse_music'", "'browse_podcasts'"):
        if token not in portal: errors.append('Dragon Portal routing/control missing: '+token)
    service_rel='addons/service.dragonmax.voice/service.py'
    service=z.read(members[service_rel]).decode('utf-8',errors='ignore') if service_rel in members else ''
    try: compile(service,service_rel,'exec')
    except Exception as exc: errors.append('Dragon Voice Python invalid: '+str(exc))
    for token in ('plugin.program.dragonmaxportal','required_skin_dependencies','ActivateWindow(Home)','Skin.SetString(DragonMaxRealm,dragon_order)'):
        if token not in service: errors.append('Dragon Voice activation wiring missing: '+token)


def audit_home(z,members,errors):
    menu_rel='addons/skin.auramod/shortcuts/mainmenu.DATA.xml'; home_rel='addons/skin.auramod/1080i/Home.xml'
    if menu_rel not in members: errors.append('DragonMax native AuraMOD main menu is missing'); return
    try:
        menu_text=z.read(members[menu_rel]).decode('utf-8'); root=ET.fromstring(menu_text)
        labels=[str(node.findtext('label') or '') for node in root.findall('shortcut')]
        if labels != DRAGONMAX_HOME: errors.append('AuraMOD would not boot to DragonMax 4.9 home; menu labels='+repr(labels))
    except Exception as exc: errors.append('DragonMax main menu XML invalid: '+str(exc)); return
    if 'RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open' in menu_text: errors.append('native menu still contains dead RunPlugin Portal directory route')
    if 'ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)' not in menu_text: errors.append('native Dragon Portal root does not open Programs window')
    for target in ('continue','movies','tv','sports','anime','music','podcasts','settings'):
        expected='ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/?action=open&amp;target='+target+'",return)'
        if expected not in menu_text: errors.append('native menu missing navigable route='+target)

    if home_rel not in members: errors.append('DragonMax custom AuraMOD Home.xml is missing'); return
    try:
        home_text=z.read(members[home_rel]).decode('utf-8'); home_root=ET.fromstring(home_text)
    except Exception as exc: errors.append('DragonMax custom Home.xml invalid: '+str(exc)); return
    for token in ('DRAGONMAX','DragonMaxRealm','DragonMaxRealmName','ENTER THE DRAGON REALMS','TRENDING MOVIES','type="multiimage"','WindowOpen','effect="zoom"','wallpapers/dragon_order/','dragonmax_v92_home_preview.png'):
        if token not in home_text: errors.append('DragonMax custom Home.xml missing: '+token)
    for forbidden in ('script.skinshortcuts-template-global-fanart','hero_banners/','realm_crests/','portal_graphics/','RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open'):
        if forbidden in home_text: errors.append('invalid/stock/synthetic Home.xml token survived: '+forbidden)
    for target in ('continue','movies','tv','sports','anime','music','podcasts','settings'):
        expected='ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/?action=open&amp;target='+target+'",return)'
        if expected not in home_text: errors.append('Home.xml missing navigable route='+target)
    controls={node.attrib.get('id') for node in home_root.findall('.//control') if node.attrib.get('id')}
    if str(home_root.findtext('defaultcontrol') or '') not in controls: errors.append('Home.xml default control does not exist')
    for node in home_root.findall('.//control[@id]'):
        source=node.attrib.get('id')
        for direction in ('onleft','onright','onup','ondown'):
            target=str(node.findtext(direction) or '')
            if target and target.isdigit() and target not in controls: errors.append(f'Home.xml {source} {direction} targets missing control {target}')
            if target and target==source: errors.append(f'Home.xml {source} has self-loop on {direction}')


def audit_policy(members,errors):
    for rel in members:
        if rel.startswith(('userdata/Database/','userdata/Thumbnails/','addons/packages/')): errors.append('protected/volatile runtime content leaked: '+rel)
    if 'userdata/guisettings.xml' in members: errors.append('live guisettings.xml must not be shipped')


def main():
    errors=[]
    try:
        build=json.loads((PUBLIC/'build.json').read_text(encoding='utf-8'))['builds'][0]
        payload=PUBLIC/str(build['zip'])
    except Exception as exc: raise SystemExit('ERROR: cannot load generated release metadata: '+str(exc))
    if not payload.is_file(): raise SystemExit('ERROR: generated payload missing: '+str(payload))
    with zipfile.ZipFile(payload) as z:
        bad=z.testzip()
        if bad: errors.append('corrupt ZIP member: '+bad)
        members=member_map(z); addons=addon_graph(z,members,errors)
        audit_dependencies(addons,errors); audit_real_art(z,members,errors); audit_portal(z,members,addons,errors); audit_home(z,members,errors); audit_policy(members,errors)
    if errors:
        for item in sorted(set(errors)): print('ERROR:',item)
        return 1
    print('DragonMax comprehensive release audit passed.')
    print('Verified dependency closure, recovered visual bytes, real splash, navigable 4.9 Home routes, Portal wiring, and skin fallback.')
    return 0

if __name__=='__main__': sys.exit(main())
