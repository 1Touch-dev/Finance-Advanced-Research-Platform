import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_integration.db")
os.environ.setdefault("ENV", "test")

from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_token():
    """Get an auth token for integration tests."""
    email = f"integration_test_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={
        "email": email,
        "password": "TestPassword123!"
    })
    if r.status_code == 200:
        return r.json()["access_token"]
    # If registration fails, try login
    r = client.post("/auth/login", json={
        "email": email,
        "password": "TestPassword123!"
    })
    return r.json().get("access_token", "")


@pytest.fixture
def auth_headers(auth_token):
    """Get auth headers for requests."""
    return {"Authorization": f"Bearer {auth_token}"}


def test_health():
    """Health endpoint does not require auth."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_bootstrap_and_sources(auth_headers):
    """Bootstrap endpoints require auth post-hardening."""
    r = client.post("/sources/bootstrap", headers=auth_headers)
    assert r.status_code == 200
    r = client.get("/sources/health", headers=auth_headers)
    assert r.status_code == 200
    assert "sources" in r.json()


def test_evidence_bootstrap(auth_headers):
    """Evidence bootstrap requires auth."""
    r = client.post("/evidence/bootstrap", headers=auth_headers)
    assert r.status_code == 200


def test_skills_bootstrap(auth_headers):
    """Skills bootstrap requires auth."""
    r = client.post("/skills/bootstrap", headers=auth_headers)
    assert r.status_code == 200


def test_monitor_bootstrap_and_scan(auth_headers):
    """Monitor endpoints require auth."""
    r = client.post("/monitor/bootstrap", headers=auth_headers)
    assert r.status_code == 200
    r = client.post("/monitor/scan", headers=auth_headers)
    assert r.status_code == 200


def test_search_hybrid(auth_headers):
    """Search requires auth and bootstrapped data."""
    client.post("/entities/bootstrap", headers=auth_headers)
    client.post("/evidence/bootstrap", headers=auth_headers)
    r = client.get("/search/?q=test", headers=auth_headers)
    assert r.status_code == 200
