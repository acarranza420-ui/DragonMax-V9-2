#!/usr/bin/env python3
"""Deterministic DragonMax 4.9 release entrypoint.

Load the current release wrapper explicitly, alias it as repo_release for the
legacy builder, then execute build_v12.py unchanged. This avoids relying on
sitecustomize/import startup behavior in GitHub Actions and Render.
"""
import runpy
import sys

import repo_release_v49 as release

sys.modules['repo_release'] = release
runpy.run_path('build_v12.py', run_name='__main__')
