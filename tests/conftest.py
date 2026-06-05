import os
import sys

import pytest

# Ensure connectors package is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PKG = os.path.join(ROOT, "packages", "connectors")
if PKG not in sys.path:
    sys.path.insert(0, PKG)

os.environ.setdefault("ENV", "test")
