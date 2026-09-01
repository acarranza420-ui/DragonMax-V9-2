#!/usr/bin/env python3
"""Compatibility entrypoint for Render; uses the canonical 4.9 release build."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).with_name('build_release.py')), run_name='__main__')
