"""
Tests for Mobile PWA API (#33)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestPWAManifest:
    """Tests for PWA manifest endpoints."""

    def test_get_manifest(self):
        """Test getting PWA manifest."""
        response = client.get("/pwa/manifest")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "short_name" in data
        assert "icons" in data
        assert "start_url" in data
        assert "display" in data

    def test_get_sw_config(self):
        """Test getting service worker config."""
        response = client.get("/pwa/sw-config")
        assert response.status_code == 200
        data = response.json()
        assert "cache_name" in data
        assert "cache_urls" in data
        assert "api_cache_strategy" in data

    def test_get_install_prompt(self):
        """Test getting install prompt config."""
        response = client.get("/pwa/install-prompt")
        assert response.status_code == 200
        data = response.json()
        assert "show_after_visits" in data
        assert "prompt_text" in data

    def test_get_compatibility(self):
        """Test getting PWA compatibility check."""
        response = client.get("/pwa/compatibility")
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert "install_criteria" in data
        assert "service_worker" in data["features"]


class TestPushNotifications:
    """Tests for push notification endpoints."""

    def test_subscribe_push(self):
        """Test subscribing to push notifications."""
        subscription = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
            "keys": {
                "auth": "test_auth_key",
                "p256dh": "test_p256dh_key"
            }
        }
        response = client.post(
            "/pwa/push/subscribe?user_id=test_user",
            json=subscription
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"
        assert data["user_id"] == "test_user"
        assert "subscription_id" in data

    def test_unsubscribe_push(self):
        """Test unsubscribing from push notifications."""
        response = client.delete("/pwa/push/subscribe?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unregistered"

    def test_get_notification_preferences(self):
        """Test getting notification preferences."""
        response = client.get("/pwa/notifications/preferences?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test_user"
        assert "preferences" in data
        assert "price_alerts" in data["preferences"]

    def test_update_notification_preferences(self):
        """Test updating notification preferences."""
        preferences = {
            "price_alerts": False,
            "earnings_reminders": True
        }
        response = client.put(
            "/pwa/notifications/preferences?user_id=test_user",
            json=preferences
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == True

    def test_send_notification(self):
        """Test sending push notification."""
        response = client.post(
            "/pwa/notifications/send?user_id=test_user&title=Test&body=Test notification"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"
        assert data["notification"]["title"] == "Test"
