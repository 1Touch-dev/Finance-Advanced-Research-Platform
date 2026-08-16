"""
Tests for Price Alerts API (Band C #35)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestCreateAlert:
    def test_create_basic_alert(self):
        response = client.post(
            "/alerts?user_id=test_user&ticker=AAPL&alert_type=price_above&target_value=200"
        )
        assert response.status_code == 200
        data = response.json()
        assert "alert" in data
        assert data["alert"]["ticker"] == "AAPL"
        assert data["alert"]["target_value"] == 200
        assert data["alert"]["status"] == "active"

    def test_create_alert_with_options(self):
        response = client.post(
            "/alerts?user_id=test_user&ticker=MSFT&alert_type=price_below"
            "&target_value=350&channels=email,push&note=Test&expires_in_days=30"
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data["alert"]["notification_channels"]
        assert data["alert"]["note"] == "Test"

    def test_create_recurring_alert(self):
        response = client.post(
            "/alerts?user_id=test_user&ticker=NVDA&alert_type=percent_change"
            "&target_value=5&recurring=true"
        )
        assert response.status_code == 200
        assert response.json()["alert"]["recurring"] is True


class TestListAlerts:
    def test_list_user_alerts(self):
        # Create an alert first
        client.post("/alerts?user_id=list_user&ticker=GOOGL&alert_type=price_above&target_value=150")
        
        response = client.get("/alerts?user_id=list_user")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert data["count"] >= 1

    def test_list_with_status_filter(self):
        response = client.get("/alerts?user_id=list_user&status=active")
        assert response.status_code == 200

    def test_list_with_ticker_filter(self):
        response = client.get("/alerts?user_id=list_user&ticker=GOOGL")
        assert response.status_code == 200


class TestAlertTypes:
    def test_get_alert_types(self):
        response = client.get("/alerts/types")
        assert response.status_code == 200
        data = response.json()
        assert "alert_types" in data
        types = [t["type"] for t in data["alert_types"]]
        assert "price_above" in types
        assert "price_below" in types
        assert "percent_change" in types


class TestAlertStats:
    def test_get_stats(self):
        response = client.get("/alerts/stats?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "total_alerts" in data
        assert "active" in data
        assert "triggered_today" in data


class TestNotifications:
    def test_list_notifications(self):
        response = client.get("/alerts/notifications?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "count" in data

    def test_list_unread_only(self):
        response = client.get("/alerts/notifications?user_id=test_user&unread_only=true")
        assert response.status_code == 200


class TestSingleAlert:
    def test_get_alert(self):
        # Create first
        create_resp = client.post(
            "/alerts?user_id=single_user&ticker=META&alert_type=price_above&target_value=500"
        )
        alert_id = create_resp.json()["alert"]["alert_id"]
        
        response = client.get(f"/alerts/{alert_id}?user_id=single_user")
        assert response.status_code == 200
        assert response.json()["alert"]["ticker"] == "META"

    def test_get_nonexistent_alert(self):
        response = client.get("/alerts/nonexistent?user_id=test_user")
        assert response.status_code == 404


class TestUpdateAlert:
    def test_update_target(self):
        create_resp = client.post(
            "/alerts?user_id=update_user&ticker=TSLA&alert_type=price_above&target_value=250"
        )
        alert_id = create_resp.json()["alert"]["alert_id"]
        
        response = client.put(f"/alerts/{alert_id}?user_id=update_user&target_value=300")
        assert response.status_code == 200
        assert response.json()["alert"]["target_value"] == 300

    def test_update_nonexistent(self):
        response = client.put("/alerts/nonexistent?user_id=test_user&target_value=100")
        assert response.status_code == 404


class TestDeleteAlert:
    def test_delete_alert(self):
        create_resp = client.post(
            "/alerts?user_id=delete_user&ticker=AMD&alert_type=price_below&target_value=100"
        )
        alert_id = create_resp.json()["alert"]["alert_id"]
        
        response = client.delete(f"/alerts/{alert_id}?user_id=delete_user")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    def test_delete_nonexistent(self):
        response = client.delete("/alerts/nonexistent?user_id=test_user")
        assert response.status_code == 404


class TestCheckAlerts:
    def test_check_triggers(self):
        # Create an alert that should trigger
        client.post(
            "/alerts?user_id=check_user&ticker=AAPL&alert_type=price_above&target_value=100"
        )
        
        response = client.post("/alerts/check/AAPL?current_price=200")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "triggered_count" in data
