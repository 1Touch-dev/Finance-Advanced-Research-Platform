"""
Tests for PWA Advanced Features API (E2, E3, E5)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestOfflineCaching:
    """E2: Offline caching tests."""

    def test_get_offline_config(self):
        response = client.get("/pwa-advanced/offline/config")
        assert response.status_code == 200
        data = response.json()
        assert "cache_version" in data
        assert "strategies" in data
        assert "cacheable_routes" in data

    def test_get_sw_config(self):
        response = client.get("/pwa-advanced/offline/sw-config")
        assert response.status_code == 200
        data = response.json()
        assert "sw_version" in data
        assert "precache_urls" in data
        assert "runtime_caching" in data

    def test_cache_route(self):
        response = client.post("/pwa-advanced/offline/cache?user_id=test_user&route=/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cached"
        assert data["route"] == "/portfolio"

    def test_get_cached_routes(self):
        response = client.get("/pwa-advanced/offline/cached?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "cached_routes" in data
        assert "count" in data

    def test_clear_cache(self):
        response = client.delete("/pwa-advanced/offline/cache?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"


class TestWebAuthn:
    """E3: WebAuthn / Biometric tests."""

    def test_start_registration(self):
        response = client.post("/pwa-advanced/biometric/register/start?user_id=test_user&username=testuser")
        assert response.status_code == 200
        data = response.json()
        assert "challenge" in data
        assert "rp" in data
        assert "user" in data
        assert "pubKeyCredParams" in data

    def test_complete_registration(self):
        # First start registration
        client.post("/pwa-advanced/biometric/register/start?user_id=webauthn_user&username=testuser")

        response = client.post(
            "/pwa-advanced/biometric/register/complete?user_id=webauthn_user",
            json={"credential_id": "test_cred_123", "public_key": "test_public_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"
        assert data["biometric_enabled"] == True

    def test_get_biometric_status(self):
        response = client.get("/pwa-advanced/biometric/status?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "biometric_enabled" in data

    def test_start_login(self):
        # First register
        client.post("/pwa-advanced/biometric/register/start?user_id=login_user&username=logintest")
        client.post(
            "/pwa-advanced/biometric/register/complete?user_id=login_user",
            json={"credential_id": "login_cred", "public_key": "login_key"}
        )

        response = client.post("/pwa-advanced/biometric/login/start?user_id=login_user")
        assert response.status_code == 200
        data = response.json()
        assert "challenge" in data

    def test_verify_login(self):
        # Register first
        client.post("/pwa-advanced/biometric/register/start?user_id=verify_user&username=verifytest")
        client.post(
            "/pwa-advanced/biometric/register/complete?user_id=verify_user",
            json={"credential_id": "verify_cred", "public_key": "verify_key"}
        )
        # Start login
        client.post("/pwa-advanced/biometric/login/start?user_id=verify_user")

        response = client.post(
            "/pwa-advanced/biometric/login/verify?user_id=verify_user",
            json={"credential_id": "verify_cred", "signature": "test_sig"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] == True


class TestScreenSharing:
    """E5: Screen sharing tests."""

    def test_create_session(self):
        response = client.post("/pwa-advanced/screen/create?user_id=host_user&session_name=Test%20Session")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["host_user_id"] == "host_user"
        assert data["status"] == "waiting"
        assert "ice_servers" in data

    def test_join_session(self):
        # Create session first
        create_res = client.post("/pwa-advanced/screen/create?user_id=host_user2")
        session_id = create_res.json()["session_id"]

        response = client.post(f"/pwa-advanced/screen/{session_id}/join?user_id=guest_user")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "joined"
        assert "guest_user" in data["participants"]

    def test_get_session_info(self):
        # Create session first
        create_res = client.post("/pwa-advanced/screen/create?user_id=info_host")
        session_id = create_res.json()["session_id"]

        response = client.get(f"/pwa-advanced/screen/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

    def test_leave_session(self):
        # Create and join
        create_res = client.post("/pwa-advanced/screen/create?user_id=leave_host")
        session_id = create_res.json()["session_id"]
        client.post(f"/pwa-advanced/screen/{session_id}/join?user_id=leave_guest")

        response = client.post(f"/pwa-advanced/screen/{session_id}/leave?user_id=leave_guest")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "left"

    def test_end_session(self):
        # Create session
        create_res = client.post("/pwa-advanced/screen/create?user_id=end_host")
        session_id = create_res.json()["session_id"]

        response = client.post(f"/pwa-advanced/screen/{session_id}/end?user_id=end_host")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ended"

    def test_get_active_sessions(self):
        response = client.get("/pwa-advanced/screen/active?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "count" in data
