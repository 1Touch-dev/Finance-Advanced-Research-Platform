"""
Tests for Recursive Entity Discovery API (J7)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestRecursiveDiscovery:
    """Tests for recursive discovery endpoints."""

    def test_discover_recursively(self):
        """Test recursive entity discovery."""
        response = client.post("/recursive/discover/NVDA?max_depth=3")
        assert response.status_code == 200
        data = response.json()
        assert data["root"] == "NVDA"
        assert "discovered_entities" in data
        assert "total_discovered" in data

    def test_build_entity_graph(self):
        """Test building entity graph."""
        response = client.get("/recursive/graph/AAPL?max_depth=2")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "graph" in data
        assert "nodes" in data["graph"]
        assert "edges" in data["graph"]
        assert "statistics" in data


class TestPathFinding:
    """Tests for path finding endpoints."""

    def test_find_shortest_path(self):
        """Test finding shortest path between entities."""
        response = client.get("/recursive/path?source=NVDA&target=AMD")
        assert response.status_code == 200
        data = response.json()
        assert data["source"] == "NVDA"
        assert data["target"] == "AMD"
        assert "path" in data
        assert "path_length" in data
        assert "relationship_chain" in data


class TestEntityAnalysis:
    """Tests for entity analysis endpoints."""

    def test_get_clusters(self):
        """Test getting entity clusters."""
        response = client.get("/recursive/clusters/MSFT")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "MSFT"
        assert "clusters" in data
        assert "total_clusters" in data

    def test_detect_circular_ownership(self):
        """Test circular ownership detection."""
        response = client.get("/recursive/circular/GOOGL")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "GOOGL"
        assert "circular_ownership_detected" in data
        assert "risk_level" in data

    def test_get_ownership_chain(self):
        """Test getting ownership chain."""
        response = client.get("/recursive/chain/TSLA")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TSLA"
        assert "chain" in data
        assert "ultimate_parent" in data
        assert "chain_length" in data


class TestNetworkComparison:
    """Tests for network comparison endpoints."""

    def test_compare_networks(self):
        """Test comparing entity networks."""
        response = client.get("/recursive/compare?ticker1=NVDA&ticker2=AMD")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker1"] == "NVDA"
        assert data["ticker2"] == "AMD"
        assert "common_entities" in data
        assert "network_overlap_score" in data
        assert "relationship_strength" in data
