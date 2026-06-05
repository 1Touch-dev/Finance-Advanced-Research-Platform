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
    client.post("/reports/bootstrap")
    r = client.post("/reports/?title=T&kind=investor_intel")
    rid = r.json()["id"]
    ready = client.get(f"/reports/{rid}/export_ready")
    assert ready.status_code == 200
    assert "ready" in ready.json()
