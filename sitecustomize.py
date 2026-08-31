"""Force Render's legacy build command onto the validated DragonMax 4.9 path."""
import json
import os
from pathlib import Path
import runpy
import sys

entry = os.path.basename(sys.argv[0] or '')
if entry == 'build_v12.py':
    root = Path(__file__).resolve().parent
    runpy.run_path(str(root / 'build_release.py'), run_name='__main__')

    public = root / 'public'
    try:
        build = json.loads((public / 'build.json').read_text(encoding='utf-8'))['builds'][0]
        version = str(build.get('version', ''))
        required = [
            public / 'repository.dragonmax-4.9.0.zip',
            public / 'plugin.program.dragonmaxwizard-4.9.0.zip',
            public / 'builds' / 'DragonMax_V12_Unified_Build_Content-4.9.0.zip',
        ]
        if version != '4.9.0':
            raise RuntimeError('Render generated wrong DragonMax version: ' + repr(version))
        missing = [str(p.relative_to(public)) for p in required if not p.is_file() or p.stat().st_size <= 0]
        if missing:
            raise RuntimeError('Render missing required 4.9 artifacts: ' + ', '.join(missing))
        print('RENDER RELEASE GATE PASSED: DragonMax 4.9.0 payload and installer artifacts verified.')
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
    except Exception as exc:
        print('RENDER RELEASE GATE FAILED: ' + str(exc), file=sys.stderr, flush=True)
        os._exit(97)
