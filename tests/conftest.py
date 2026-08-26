import os
import sys

import pytest

# Ensure connectors package is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PKG = os.path.join(ROOT, "packages", "connectors")
API_ROOT = os.path.join(ROOT, "apps", "api")

if PKG not in sys.path:
    sys.path.insert(0, PKG)
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

# Set test environment variables BEFORE importing app modules
os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("REDIS_URL", "")  # Disable Redis in tests

# Remove stale sqlite test DBs so schema migrations apply cleanly
for _db in ("test_integration.db", "test_governance.db", "test.db", "test_auth.db",
            "test_portfolios.db", "test_intelligence.db", "test_market.db"):
    for base in (ROOT, API_ROOT, os.getcwd()):
        path = os.path.join(base, _db)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all database tables before running tests."""
    from app.models.base import Base
    from app.db.session import engine

    # Import all models to register them with Base
    from app.models import entities, reports, evidence, sources, skills, review
    from app.models import compliance, monitor, registry, models

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield

    # Cleanup after all tests (optional)
    # Base.metadata.drop_all(bind=engine)
