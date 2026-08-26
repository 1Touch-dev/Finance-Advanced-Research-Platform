"""Shared pytest configuration.

Two jobs:

1. Authenticate the module-level ``TestClient`` instances the suite already uses.
   Endpoints that mutate user-owned data now require a Bearer token (previously any
   caller could write as any ``user_id``). The existing tests were written against
   that insecure behaviour and assert ``200``, so they broke when the hole was
   closed. Rather than weaken the endpoints or rewrite hundreds of call sites, the
   default headers on each client are populated once with a real registered user's
   token.

2. Isolate the database, so a test run never touches the developer's ``local.db``.
"""

import os
import tempfile
import uuid
from pathlib import Path

# Pin the test database BEFORE load_dotenv (which would stamp in the Postgres
# URL from .env and make setdefault a no-op).  pydantic-settings prefers
# environment variables over env_file, so as long as DATABASE_URL is in
# os.environ before Settings() is instantiated the engine points at SQLite.
_TEST_DB = os.path.join(tempfile.gettempdir(), f"pytest_{uuid.uuid4().hex[:8]}.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ.setdefault("RATE_LIMIT", "off")
os.environ.setdefault("RAG_PRELOAD", "off")

# Load remaining .env values (non-DB keys like API keys, JWT secret, etc.)
# override=False so our DATABASE_URL above is not clobbered.
from dotenv import load_dotenv
_env_path = Path(__file__).resolve().parents[1] / ".env"
if not _env_path.exists():
    _env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path, override=False)

import pytest


def _issue_token() -> str | None:
    """Register a throwaway user and return its access token."""
    import importlib

    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import engine
    from app.models.base import Base

    # importlib, not `import app.models.models`: the latter rebinds the local name
    # `app` to the package, so the FastAPI instance is shadowed and TestClient is
    # handed a module ("TypeError: 'module' object is not callable").
    importlib.import_module("app.models.models")

    # /auth/register assumes its tables exist; nothing created them before startup,
    # so a fresh test database 500s on the first request.
    Base.metadata.create_all(bind=engine)

    # Deliberately not using ``with TestClient(...)``: the context manager runs the
    # app's startup/shutdown lifespan, which clashes with the module-level clients the
    # suite already creates. A plain client issues requests without touching lifespan.
    client = TestClient(app, raise_server_exceptions=False)
    creds = {"email": f"pytest_{uuid.uuid4().hex[:10]}@example.com",
             "password": "PytestPass123!"}
    for path in ("/auth/register", "/auth/login"):
        try:
            response = client.post(path, json=creds)
        except Exception:
            continue
        if response.status_code < 300:
            token = response.json().get("access_token")
            if token:
                return token
    return None


@pytest.fixture(scope="session")
def auth_token() -> str | None:
    try:
        return _issue_token()
    except Exception:
        return None


@pytest.fixture(scope="session")
def auth_headers(auth_token) -> dict:
    return {"Authorization": f"Bearer {auth_token}"} if auth_token else {}


@pytest.fixture(autouse=True, scope="session")
def _authenticate_module_clients():
    """Attach a Bearer token to every module-level TestClient in the suite.

    The clients are created at import time as module globals, so they cannot take a
    fixture argument. Mutating their ``headers`` after collection reaches all of
    them without touching the individual test files.
    """
    token = None
    try:
        token = _issue_token()
    except Exception:
        # Never let auth setup fail collection; tests that need a token will
        # report their own 401 instead of every test erroring at setup.
        token = None
    if not token:
        yield
        return

    import sys
    from starlette.testclient import TestClient as _TC

    patched = []
    for module in list(sys.modules.values()):
        if not getattr(module, "__name__", "").startswith("tests"):
            continue
        for name in dir(module):
            obj = getattr(module, name, None)
            if isinstance(obj, _TC) and "Authorization" not in obj.headers:
                obj.headers.update({"Authorization": f"Bearer {token}"})
                patched.append(f"{module.__name__}.{name}")
    yield


def pytest_collection_modifyitems(config, items):
    """Tag tests that need outbound network so they can be deselected offline.

    Run only the hermetic subset with ``-m 'not network'``. Without the marker a CI
    box with no API keys reports hundreds of failures that say nothing about the
    code.
    """
    network_hint = (
        "consensus", "analyst", "whisper", "volatility", "volume", "guidance",
        "short_interest", "ipo_calendar", "earnings_calendar", "ma_rumors",
        "benchmark", "valuation", "global_equity", "macro", "gov_trading",
        "sec_", "edgar", "finnhub", "yfinance", "rag_vector",
    )
    for item in items:
        path = str(getattr(item, "fspath", "")).lower()
        if any(hint in path for hint in network_hint):
            item.add_marker(pytest.mark.network)


@pytest.fixture(autouse=True)
def _rate_limit_pause(request):
    """Pause 0.5s between network tests to avoid Finnhub 60 req/min rate limit."""
    yield
    if request.node.get_closest_marker("network"):
        import time
        time.sleep(0.5)
