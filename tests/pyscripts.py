"""Load the repo's root-level utility scripts as importable modules.

Both scripts live at the repo root with hyphenated filenames
(check-classes.py, generate_sitemap.py) so they can't be `import`ed by
name — they're meant to be run as `python3 check-classes.py`, not
imported. This loads them from their file path instead.
"""
from __future__ import annotations

import importlib.util
import os

from htmlkit import ROOT


def load(script_name: str):
    path = os.path.join(ROOT, script_name)
    module_name = script_name.replace("-", "_").removesuffix(".py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
