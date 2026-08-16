"""
Tests for Brokerage Sync API (#43)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestBrokerList:
    """Tests for broker listing."""

    def test_list_brokers(self):
        """Test listing supported brokers."""
        response = client.get("/brokerage/brokers")
        assert response.status_code == 200
        data = response.json()
        assert "brokers" in data
        assert "count" in data
        assert len(data["brokers"]) > 0
        # Check broker structure
        broker = data["brokers"][0]
        assert "id" in broker
        assert "name" in broker
        assert "oauth" in broker


class TestBrokerLinking:
    """Tests for broker linking endpoints."""

    def test_initiate_link(self):
        """Test initiating broker link."""
        response = client.post("/brokerage/link/initiate?user_id=test_user&broker_id=fidelity")
        assert response.status_code == 200
        data = response.json()
        assert "link_token" in data
        assert "broker" in data
        assert data["broker"]["id"] == "fidelity"

    def test_initiate_link_invalid_broker(self):
        """Test initiating link with invalid broker."""
        response = client.post("/brokerage/link/initiate?user_id=test_user&broker_id=invalid")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_complete_link(self):
        """Test completing broker link."""
        response = client.post(
            "/brokerage/link/complete?user_id=test_user&link_token=test_token&access_token=test_access"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "linked"
        assert "account" in data


class TestLinkedAccounts:
    """Tests for linked account operations."""

    def test_list_accounts(self):
        """Test listing linked accounts."""
        response = client.get("/brokerage/accounts?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
        assert "count" in data

    def test_sync_account(self):
        """Test syncing account."""
        response = client.post("/brokerage/accounts/test_account/sync?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "sync_status" in data
        assert "positions_synced" in data

    def test_get_positions(self):
        """Test getting account positions."""
        response = client.get("/brokerage/accounts/test_account/positions?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data
        assert "total_value" in data

    def test_get_transactions(self):
        """Test getting account transactions."""
        response = client.get("/brokerage/accounts/test_account/transactions?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data

    def test_unlink_account(self):
        """Test unlinking account."""
        response = client.delete("/brokerage/accounts/test_account?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unlinked"

    def test_sync_status(self):
        """Test getting sync status."""
        response = client.get("/brokerage/sync-status?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "accounts" in data
