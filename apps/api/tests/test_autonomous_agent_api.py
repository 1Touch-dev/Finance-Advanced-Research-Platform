"""
Tests for Autonomous Agent API (J6)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestDiscoveryJobs:
    """Tests for discovery job endpoints."""

    def test_start_discovery(self):
        """Test starting a discovery job."""
        response = client.post("/agent/discover?ticker=NVDA&depth=2")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["ticker"] == "NVDA"
        assert data["status"] == "running"
        assert data["depth"] == 2

    def test_start_discovery_with_types(self):
        """Test starting discovery with specific entity types."""
        response = client.post("/agent/discover?ticker=AAPL&entity_types=subsidiary&entity_types=investment")
        assert response.status_code == 200
        data = response.json()
        assert "subsidiary" in data["entity_types"]

    def test_get_job_status(self):
        """Test getting job status."""
        response = client.get("/agent/jobs/disc_NVDA_20240101120000")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "status" in data
        assert "progress" in data


class TestEntityDiscovery:
    """Tests for entity discovery endpoints."""

    def test_get_entities(self):
        """Test getting discovered entities."""
        response = client.get("/agent/entities/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "NVDA"
        assert "entities" in data
        assert "count" in data

    def test_get_entity_graph(self):
        """Test getting entity relationship graph."""
        response = client.get("/agent/graph/NVDA?depth=2")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert data["ticker"] == "NVDA"
        assert "node_count" in data


class TestSpecificDiscoveries:
    """Tests for specific discovery types."""

    def test_discover_subsidiaries(self):
        """Test discovering subsidiaries."""
        response = client.get("/agent/subsidiaries/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "subsidiaries" in data
        assert "source" in data

    def test_discover_investments(self):
        """Test discovering investments."""
        response = client.get("/agent/investments/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "NVDA"
        assert "investments" in data
        assert "total_value" in data

    def test_discover_board_connections(self):
        """Test discovering board connections."""
        response = client.get("/agent/board-connections/MSFT")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "MSFT"
        assert "board_connections" in data

    def test_get_family_tree(self):
        """Test getting corporate family tree."""
        response = client.get("/agent/family-tree/GOOGL")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "GOOGL"
        assert "tree" in data
        assert "ultimate_parent" in data
