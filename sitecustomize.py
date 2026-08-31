"""Keep legacy Render build commands on the deterministic DragonMax 4.9 path."""
import os
import runpy
import sys

entry = os.path.basename(sys.argv[0] or '')
if entry == 'build_v12.py':
    # Render still invokes build_v12.py directly. Execute the validated release
    # entrypoint instead, then terminate before the legacy script body runs.
    runpy.run_path('build_release.py', run_name='__main__')
    try:
        sys.stdout.flush()
        sys