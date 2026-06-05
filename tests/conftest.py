import os
import sys

import pytest

# Ensure connectors package is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PKG = os.path.join(ROOT, "packages", "connectors")
if PKG not in sys.path:
    sys.path.insert(0, PKG)

os.environ.setdefault("ENV", "test")

# Remove stale sqlite test DBs so schema migrations apply cleanly
for _db in ("test_integration.db", "test_governance.db"):
    for base in (ROOT, os.path.join(ROOT, "apps", "api")):
        path = os.path.join(base, _db)
        if os.path.exists(path):
            os.remove(path)
