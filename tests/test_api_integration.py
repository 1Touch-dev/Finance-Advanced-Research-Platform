import os
import sys

import pytest
from fastapi.testclient import TestClient

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_integration.db")
os.environ.setdefault("ENV", "test")

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_bootstrap_and_sources():
    r = client.post("/sources/bootstrap")
    assert r.status_code == 200
    r = client.get("/sources/health")
    assert r.status_code == 200
    assert "sources" in r.json()


def test_evidence_bootstrap():
    r = client.post("/evidence/bootstrap")
    assert r.status_code == 200


def test_skills_bootstrap():
    r = client.post("/skills/bootstrap")
    assert r.status_code == 200


def test_monitor_bootstrap_and_scan():
    r = client.post("/monitor/bootstrap")
    assert r.status_code == 200
    r = client.post("/monitor/scan")
    assert r.status_code == 200


def test_search_hybrid():
    client.post("/entities/bootstrap")
    client.post("/evidence/bootstrap")
    r = client.get("/search/?q=test")
    assert r.status_code == 200
