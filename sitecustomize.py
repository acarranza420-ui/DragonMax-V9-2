"""Load DragonMax 4.9 presentation overrides only for the release builder."""
import os
import sys

entry = os.path.basename(sys.argv[0] or '')
if entry == 'build_v12.py':
    import repo_release_v49 as _dragonmax_v49
    sys.modules['repo_release'] = _dragonmax_v49
