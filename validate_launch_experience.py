#!/usr/bin/env python3
"""Independent DragonMax release experience gate.

Runs after build_release.py and validates the generated distribution as a product,
not just as a ZIP. It intentionally does not import the builder so it can catch
builder assumptions and stale generated output independently.
"""
import json
import pathlib
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
MAX_COMPRESSED_MIB = 320
MAX_EXTRACTED_MIB = 900
EXPECTED_REALMS = {
    'dragon_order', 'arcane_dominion', 'crimson_court',
    'temple_guardians', 'champion_guild', 'office_consortium',
}
REQUIRED_HOME = {'Dragon Portal', 'Continue Watching', 'Movies', 'TV Shows', 'Settings'}
REQUIRED_WIDGETS = {'Continue Watching', 'Trending Movies', 'Trending TV', 'Favorites'}
REQUIRED_AUDIO = {
    'startup_theme.wav', 'portal_open.wav', 'achievement.wav',
    'ui_click.wav', 'ui_back.wav', 'ui_select.wav', 'error.wav',
}
REQUIRED_ACTIVATION_TOKENS = {
    'pending_skin_activation.json', 'Addons.SetAddonEnabled',
    'enable_skin_stack', 'active_skin_is',
    'Settings.SetSettingValue', 'lookandfeel.skin',
}


def fail(errors, message):
    errors.append(message)


def member_map(z):
    out = {}
    for info in z.infolist():
        name = info.filename.replace('\\', '/').strip('/')
        parts = name.split('/', 1)
        rel = parts[1] if len(parts) == 2 else parts[0]
        out[rel] = info
    return out


def read_json_member(z, members, rel, errors):
    if rel not in members:
        fail(errors, f'missing generated config: {rel}')
        return {}
    try:
        return json.loads(z.read(members[rel]).decode('utf-8'))
    except Exception as exc:
        fail(errors, f'invalid JSON {rel}: {exc}')
        return {}


def main():
    errors = []
    try:
        build_doc = json.loads((PUBLIC / 'build.json').read_text(encoding='utf-8'))
        build = build_doc['builds'][0]
        version = str(build.get('version', ''))
    except Exception as exc:
        raise SystemExit(f'ERROR: cannot load generated build.json: {exc}')

    payload = PUBLIC / str(build.get('zip', ''))
    if not payload.is_file():
        raise SystemExit(f'ERROR: payload missing: {payload}')

    compressed_mib = payload.stat().st_size / 1024 / 1024
    if compressed_mib > MAX_COMPRESSED_MIB:
        fail(errors, f'compressed payload {compressed_mib:.1f} MiB exceeds {MAX_COMPRESSED_MIB} MiB Fire TV budget')

    with zipfile.ZipFile(payload) as z:
        if z.testzip():
            fail(errors, 'payload contains a corrupt ZIP member')
        members = member_map(z)
        extracted_mib = sum(i.file_size for i in z.infolist()) / 1024 / 1024
        if extracted_mib > MAX_EXTRACTED_MIB:
            fail(errors, f'extracted payload {extracted_mib:.1f} MiB exceeds {MAX_EXTRACTED_MIB} MiB Fire TV budget')

        menus = read_json_member(z, members, 'dragonmax/config/menus.json', errors)
        widgets = read_json_member(z, members, 'dragonmax/config/widgets.json', errors)
        realms = read_json_member(z, members, 'dragonmax/config/realms.json', errors)
        perf = read_json_member(z, members, 'dragonmax/config/performance.json', errors)
        voice = read_json_member(z, members, 'dragonmax/config/voice.json', errors)

        home = menus.get('home', []) if isinstance(menus, dict) else []
        if not isinstance(home, list) or not home:
            fail(errors, 'home menu is empty or malformed')
        else:
            if len(home) > 9:
                fail(errors, f'home menu has {len(home)} top-level entries; maximum polished Fire TV target is 9')
            if len(home) != len(set(home)):
                fail(errors, 'home menu contains duplicate entries')
            missing = sorted(REQUIRED_HOME - set(home))
            if missing:
                fail(errors, 'home menu missing core destinations: ' + ', '.join(missing))

        rows = widgets.get('rows', []) if isinstance(widgets, dict) else []
        if not isinstance(rows, list) or not rows:
            fail(errors, 'widget row configuration is empty or malformed')
        else:
            if not (4 <= len(rows) <= 8):
                fail(errors, f'widget row count {len(rows)} is outside 4-8 launch budget')
            if len(rows) != len(set(rows)):
                fail(errors, 'widget rows contain duplicates')
            if rows[0] != 'Continue Watching':
                fail(errors, 'Continue Watching must be the first home widget')
            missing = sorted(REQUIRED_WIDGETS - set(rows))
            if missing:
                fail(errors, 'widget configuration missing core rows: ' + ', '.join(missing))

        realm_rows = realms.get('realms', []) if isinstance(realms, dict) else []
        ids = {r.get('id') for r in realm_rows if isinstance(r, dict)}
        if ids != EXPECTED_REALMS:
            fail(errors, f'realm contract mismatch: expected {sorted(EXPECTED_REALMS)}, got {sorted(x for x in ids if x)}')
        for realm in EXPECTED_REALMS:
            wallpapers = [n for n in members if n.startswith(f'artwork/wallpapers/{realm}/') and n.endswith('.png')]
            if len(wallpapers) != 1: fail(errors, f'{realm} must have exactly one curated realm wallpaper, found {len(wallpapers)}')
            elif members[wallpapers[0]].file_size < 500_000: fail(errors, f'{realm} realm wallpaper is undersized')
        reference = 'artwork/reference/dragonmax_v92_home_preview.png'
        if reference not in members or members[reference].file_size < 1_000_000:
            fail(errors, 'recovered DragonMax V9.2 reference artwork missing or undersized')
        for fake_root in ('artwork/hero_banners/', 'artwork/realm_crests/', 'artwork/achievement_badges/', 'artwork/loading_screens/', 'artwork/portal_graphics/', 'artwork/wizard_graphics/'):
            if any(n.startswith(fake_root) for n in members): fail(errors, 'procedural/dead artwork survived: '+fake_root)

        profiles = perf.get('profiles', {}) if isinstance(perf, dict) else {}
        expected_profiles = {'maximum_speed', 'balanced', 'visual_quality'}
        if set(profiles) != expected_profiles:
            fail(errors, 'performance profiles must be exactly maximum_speed, balanced, visual_quality')
        for name, cfg in profiles.items():
            if not isinstance(cfg, dict):
                fail(errors, f'performance profile {name} is malformed')
                continue
            limit = cfg.get('widget_limit')
            if not isinstance(limit, int) or not (1 <= limit <= 6):
                fail(errors, f'performance profile {name} has unsafe widget_limit {limit!r}')
        if profiles.get('maximum_speed', {}).get('animated_backgrounds') is not False:
            fail(errors, 'maximum_speed must disable animated backgrounds')
        if profiles.get('visual_quality', {}).get('animated_backgrounds') is not True:
            fail(errors, 'visual_quality must enable animated backgrounds')

        if voice.get('destructive_confirmation_required') is not True:
            fail(errors, 'Dragon Voice destructive actions must require confirmation')
        if voice.get('self_repair_enabled') is not True:
            fail(errors, 'Dragon self-repair must be enabled')
        if voice.get('self_repair_policy') != 'allowlisted_reversible_only':
            fail(errors, 'Dragon self-repair policy must remain allowlisted_reversible_only')

        if 'startup/dragonmax_static_splash.jpg' not in members:
            fail(errors, 'DragonMax startup splash missing')
        audio_names = {pathlib.PurePosixPath(n).name for n in members if n.startswith('audio/')}
        missing_audio = sorted(REQUIRED_AUDIO - audio_names)
        if missing_audio:
            fail(errors, 'missing core sound assets: ' + ', '.join(missing_audio))
        for realm in EXPECTED_REALMS:
            if f'realm_change_{realm}.wav' not in audio_names:
                fail(errors, f'missing realm transition audio for {realm}')

        service_rel = 'addons/service.dragonmax.voice/service.py'
        source_text = ''
        if service_rel in members:
            try: source_text = z.read(members[service_rel]).decode('utf-8', errors='ignore')
            except Exception: pass
        else:
            fail(errors, 'Dragon Voice startup service missing from runtime payload')
        for token in REQUIRED_ACTIVATION_TOKENS:
            if token not in source_text:
                fail(errors, f'post-install activation/recovery hook missing token: {token}')

        addon_ids = {}
        for rel, info in members.items():
            if rel.startswith('addons/') and rel.endswith('/addon.xml') and rel.count('/') == 2:
                try:
                    node = ET.fromstring(z.read(info).decode('utf-8'))
                    addon_ids[node.attrib.get('id', '')] = node.attrib.get('version', '')
                except Exception as exc:
                    fail(errors, f'cannot parse {rel}: {exc}')
        for required in ('skin.auramod', 'service.dragonmax.voice'):
            if required not in addon_ids:
                fail(errors, f'launch-critical runtime addon missing: {required}')

    for installer_id in ('repository.dragonmax', 'plugin.program.dragonmaxwizard'):
        artifact = PUBLIC / f'{installer_id}-{version}.zip'
        if not artifact.is_file():
            fail(errors, f'launch installer artifact missing: {artifact.name}')
        else:
            try:
                with zipfile.ZipFile(artifact) as installer_zip:
                    bad = installer_zip.testzip()
                    if bad:
                        fail(errors, f'{artifact.name} corrupt member: {bad}')
                    roots = {n.replace('\\','/').split('/',1)[0] for n in installer_zip.namelist() if n and not n.endswith('/')}
                    if roots != {installer_id}: fail(errors, f'{artifact.name} malformed root layout: {sorted(roots)}')
                    if f'{installer_id}/addon.xml' not in {n.replace('\\','/') for n in installer_zip.namelist()}:
                        fail(errors, f'{artifact.name} missing root addon.xml')
            except Exception as exc:
                fail(errors, f'{artifact.name} is not a valid installer ZIP: {exc}')

    if errors:
        for e in errors:
            print('ERROR:', e)
        return 1

    print('DragonMax launch-experience gate passed.')
    print(f'Compressed payload: {compressed_mib:.1f} MiB')
    print(f'Extracted payload: {extracted_mib:.1f} MiB')
    print('Verified: home contract, widget contract, six realm media packs, performance profiles,')
    print('voice safety/self-repair, startup/audio assets, JSON-RPC activation hooks, runtime addons,')
    print('and separate repository/wizard installer artifacts.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
