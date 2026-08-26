import os
import sys

import pyotp
import pytest

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_governance.db")
os.environ.setdefault("ENV", "test")

from app.auth.mfa import generate_totp_secret, verify_totp
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_mfa_totp_roundtrip():
    data = generate_totp_secret("test@example.com")
    code = pyotp.TOTP(data["secret"]).now()
    assert verify_totp(data["secret"], code) is True
    assert verify_totp(data["secret"], "000000") is False


def test_export_ready_endpoint():
    # Register + login to get a token (auth required on /reports/ endpoints)
    client.post("/auth/register", json={"email": "gov_test@example.com", "password": "govpassword123"})
    login = client.post("/auth/login", json={"email": "gov_test@example.com", "password": "govpassword123"})
    token = login.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    client.post("/reports/bootstrap", headers=headers)
    r = client.post("/reports/?title=T&kind=investor_intel", headers=headers)
    assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}: {r.text}"
    rid = r.json()["id"]
    ready = client.get(f"/reports/{rid}/export_ready", headers=headers)
    assert ready.status_code == 200
    assert "ready" in ready.json()
