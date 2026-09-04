#!/usr/bin/env python3
"""Exercise the generated DragonMax wizard's safety-critical runtime helpers."""
import ast
import hashlib
import json
import pathlib
import sys
import tempfile
import types
import warnings
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'


class Progress:
    def update(self, *_args):
        pass

    def iscanceled(self):
        return False


def expect_error(action, label):
    try:
        action()
    except Exception:
        return
    raise AssertionError(label + ' did not fail closed')


def load_wizard(source):
    tree = ast.parse(source, filename='generated-wizard-default.py')
    startup = [
        node for node in tree.body
        if isinstance(node, ast.Try)
        and any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == 'main'
            for child in ast.walk(node)
        )
    ]
    if len(startup) != 1:
        raise AssertionError('generated wizard must contain exactly one guarded startup call')
    tree.body.remove(startup[0])
    ast.fix_missing_locations(tree)

    state = {'enabled': {}, 'builtin_enables': False, 'builtins': []}
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGINFO = 1
    xbmc.LOGWARNING = 2
    xbmc.LOGERROR = 3
    xbmc.log = lambda *_args: None
    xbmc.sleep = lambda *_args: None

    def execute_json_rpc(raw):
        request = json.loads(raw)
        method = request.get('method')
        addon_id = request.get('params', {}).get('addonid', '')
        if method == 'Addons.SetAddonEnabled':
            return json.dumps({'jsonrpc': '2.0', 'id': request.get('id'), 'result': 'OK'})
        if method == 'Addons.GetAddonDetails':
            return json.dumps({'jsonrpc': '2.0', 'id': request.get('id'), 'result': {'addon': {'enabled': bool(state['enabled'].get(addon_id))}}})
        return json.dumps({'jsonrpc': '2.0', 'id': request.get('id'), 'result': {}})

    def execute_builtin(command):
        state['builtins'].append(command)
        if state['builtin_enables'] and command.startswith('EnableAddon(') and command.endswith(')'):
            state['enabled'][command[len('EnableAddon('):-1]] = True

    xbmc.executeJSONRPC = execute_json_rpc
    xbmc.executebuiltin = execute_builtin

    xbmcaddon = types.ModuleType('xbmcaddon')
    xbmcaddon.Addon = lambda *_args: object()
    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.Dialog = object
    xbmcgui.DialogProgress = object
    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda value: value

    names = {'xbmc': xbmc, 'xbmcaddon': xbmcaddon, 'xbmcgui': xbmcgui, 'xbmcvfs': xbmcvfs}
    previous = {name: sys.modules.get(name) for name in names}
    sys.modules.update(names)
    namespace = {'__name__': 'dragonmax_generated_wizard_test', '__file__': 'generated-wizard-default.py'}
    try:
        exec(compile(tree, 'generated-wizard-default.py', 'exec'), namespace)
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    return namespace, state


def test_repository(version):
    path = PUBLIC / f'repository.dragonmax-{version}.zip'
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        assert all(info.date_time == (2026, 1, 1, 0, 0, 0) for info in archive.infolist())
        root = ET.fromstring(archive.read('repository.dragonmax/addon.xml'))
    directories = root.findall('./extension[@point="xbmc.addon.repository"]/dir')
    assert len(directories) == 1, 'DragonMax must not aggregate unrelated third-party repositories'
    directory = directories[0]
    assert directory.attrib.get('minversion') == '21.0.0'
    assert directory.attrib.get('maxversion') == '21.89.0'
    endpoints = [directory.findtext(name, '') for name in ('info', 'checksum', 'datadir')]
    assert all(value.startswith('https://dragonmax.onrender.com/') for value in endpoints)


def test_metadata(build, payload):
    with zipfile.ZipFile(payload) as archive:
        infos = archive.infolist()
        assert archive.testzip() is None
    assert [info.filename for info in infos] == sorted(info.filename for info in infos)
    assert all(info.date_time == (2026, 1, 1, 0, 0, 0) for info in infos)
    assert int(build['compressed_size_bytes']) == payload.stat().st_size
    assert int(build['uncompressed_size_bytes']) == sum(info.file_size for info in infos)
    assert int(build['file_count']) == len(infos)


def test_wizard(namespace, state):
    progress = Progress()
    required = (
        'safe_rel', 'extract', 'verify', 'active_auramod', 'filter_device',
        'changed_files', 'expected_sizes', 'backup', 'apply', 'rollback',
        'addon_enabled', 'enable_runtime_addon', 'finalize_dragonmax',
    )
    for name in required:
        assert callable(namespace.get(name)), 'generated wizard helper missing: ' + name

    assert namespace['safe_rel']('addons/example/addon.xml')
    for unsafe in ('../escape', 'addons/../../escape', 'C:/escape', 'addons//escape'):
        assert not namespace['safe_rel'](unsafe), 'unsafe path accepted: ' + unsafe

    expect_error(lambda: namespace['expected_sizes']({}), 'missing exact payload metadata')
    expect_error(
        lambda: namespace['expected_sizes']({'compressed_size_bytes': -1, 'uncompressed_size_bytes': 1, 'file_count': 1}),
        'negative payload metadata',
    )
    assert namespace['expected_sizes']({'compressed_size_bytes': 10, 'uncompressed_size_bytes': 20, 'file_count': 2}) == (10, 20, 2)

    state['builtin_enables'] = False
    assert not namespace['enable_runtime_addon']('plugin.program.example'), 'unverified enable result was trusted'
    state['builtin_enables'] = True
    assert namespace['enable_runtime_addon']('plugin.program.example'), 'verified built-in activation failed'

    with tempfile.TemporaryDirectory(prefix='dragonmax-installer-runtime-') as temp:
        temp = pathlib.Path(temp)
        expect_error(lambda: namespace['ensure_space'](str(temp), 10**30, 'test storage'), 'insufficient free space')
        home = temp / 'home'
        source = temp / 'source'
        backup_root = temp / 'backup'
        home.mkdir()
        source.mkdir()

        skin_xml = home / 'addons/skin.auramod/addon.xml'
        skin_xml.parent.mkdir(parents=True)
        skin_xml.write_text('<addon id="skin.auramod" version="2.0.3"/>', encoding='utf-8')
        assert not namespace['active_auramod'](str(home))
        skin_xml.write_text('<addon id="skin.auramod" version="2.0.4"/>', encoding='utf-8')
        assert namespace['active_auramod'](str(home))

        candidates = [
            ('addons/skin.auramod/addon.xml', 'skin-addon'),
            ('addons/skin.auramod/1080i/Home.xml', 'skin-home'),
            ('addons/skin.auramod/shortcuts/mainmenu.DATA.xml', 'skin-menu'),
            ('addons/repository.auramod.aio/addon.xml', 'bootstrap-repo'),
        ]
        filtered = dict(namespace['filter_device'](str(home), candidates))
        assert 'addons/skin.auramod/addon.xml' not in filtered
        assert 'addons/skin.auramod/1080i/Home.xml' in filtered
        assert 'addons/skin.auramod/shortcuts/mainmenu.DATA.xml' in filtered
        assert 'addons/repository.auramod.aio/addon.xml' in filtered

        existing_rel = 'addons/service.dragonmax.voice/service.py'
        created_rel = 'addons/plugin.program.dragonmaxportal/default.py'
        marker_rel = 'userdata/addon_data/service.dragonmax.voice/pending_skin_activation.json'
        existing = home / existing_rel
        created = home / created_rel
        marker = home / marker_rel
        new_existing = source / 'service.py'
        new_created = source / 'default.py'
        existing.parent.mkdir(parents=True)
        marker.parent.mkdir(parents=True)
        existing.write_bytes(b'old-service')
        marker.write_bytes(b'old-marker')
        new_existing.write_bytes(b'new-service')
        new_created.write_bytes(b'new-portal')
        files = [(existing_rel, str(new_existing)), (created_rel, str(new_created))]
        assert namespace['changed_files'](str(home), [(existing_rel, str(existing))]) == []

        originals, created_paths = namespace['backup'](str(home), files, str(backup_root), progress, (marker_rel,))
        namespace['apply'](str(home), files, progress)
        marker.write_bytes(b'new-marker')
        assert existing.read_bytes() == b'new-service'
        assert created.read_bytes() == b'new-portal'
        namespace['rollback'](originals, created_paths)
        assert existing.read_bytes() == b'old-service'
        assert marker.read_bytes() == b'old-marker'
        assert not created.exists()

        payload_root = temp / 'payload'
        data = payload_root / 'addons/example/data.txt'
        manifest = payload_root / 'dragonmax/install_manifest.json'
        data.parent.mkdir(parents=True)
        manifest.parent.mkdir(parents=True)
        data.write_bytes(b'verified-data')
        row = {'path': 'addons/example/data.txt', 'size': len(data.read_bytes()), 'sha256': hashlib.sha256(data.read_bytes()).hexdigest()}
        manifest.write_text(json.dumps({'version': '4.9.0', 'install_protocol': 4, 'files': [row]}), encoding='utf-8')
        namespace['verify'](str(payload_root), progress)
        unlisted = payload_root / 'addons/example/unlisted.txt'
        unlisted.write_bytes(b'unlisted')
        expect_error(lambda: namespace['verify'](str(payload_root), progress), 'unlisted payload file')
        unlisted.unlink()
        manifest.write_text(json.dumps({'version': '4.9.0', 'install_protocol': 4, 'files': [row, row]}), encoding='utf-8')
        expect_error(lambda: namespace['verify'](str(payload_root), progress), 'duplicate manifest entry')

        malicious = temp / 'malicious.zip'
        with zipfile.ZipFile(malicious, 'w') as archive:
            archive.writestr('../escape.txt', b'escape')
        expect_error(lambda: namespace['extract'](str(malicious), str(temp / 'extract'), progress), 'ZIP traversal')
        assert not (temp / 'escape.txt').exists()

        duplicate = temp / 'duplicate.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(duplicate, 'w') as archive:
                archive.writestr('payload/repeated.txt', b'first')
                archive.writestr('payload/repeated.txt', b'second')
        expect_error(lambda: namespace['extract'](str(duplicate), str(temp / 'duplicate'), progress), 'duplicate ZIP member')

        oversized = temp / 'oversized.zip'
        with zipfile.ZipFile(oversized, 'w') as archive:
            archive.writestr('payload/data.txt', b'0123456789')
        expect_error(lambda: namespace['extract'](str(oversized), str(temp / 'oversized'), progress, max_bytes=5), 'expanded-size ceiling')

        symlink = temp / 'symlink.zip'
        link = zipfile.ZipInfo('payload/link')
        link.create_system = 3
        link.external_attr = 0o120777 << 16
        with zipfile.ZipFile(symlink, 'w') as archive:
            archive.writestr(link, b'target')
        expect_error(lambda: namespace['extract'](str(symlink), str(temp / 'symlink'), progress), 'symbolic-link member')


def main():
    build = json.loads((PUBLIC / 'build.json').read_text(encoding='utf-8'))['builds'][0]
    version = str(build['version'])
    payload = PUBLIC / str(build['zip'])
    wizard_zip = PUBLIC / f'plugin.program.dragonmaxwizard-{version}.zip'
    with zipfile.ZipFile(wizard_zip) as archive:
        assert archive.testzip() is None
        source = archive.read('plugin.program.dragonmaxwizard/default.py').decode('utf-8')
    compile(source, 'generated-wizard-default.py', 'exec')
    tree = ast.parse(source)
    bootstrap = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'bootstrap_dependencies')
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'atomic' for node in ast.walk(bootstrap))
    sequence = 'o,c=backup(home,fs,br,p,(marker,)); apply(home,fs,p); bootstrap_dependencies(root,home,p); finalize_addons(); finalize_dragonmax(home,root,p)'
    assert sequence in source, 'generated wizard transaction/finalization order changed'
    assert "'requires_restart':True" in source
    for forbidden in ('repository.redwizard', 'repo.redwizard.xyz', 'ResolveURL'):
        assert forbidden not in source, 'foreign repository behavior leaked into DragonMax: ' + forbidden

    namespace, state = load_wizard(source)
    test_repository(version)
    test_metadata(build, payload)
    test_wizard(namespace, state)
    print('DragonMax generated-installer runtime gate passed.')
    print('Verified exact size metadata, Kodi 21 scoping, actual add-on enable state, manifest/ZIP rejection,')
    print('compatible-skin preservation, transactional overwrite/marker rollback, and isolated repository trust.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
