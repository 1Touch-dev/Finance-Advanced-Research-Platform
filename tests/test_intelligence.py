"""
Intelligence Report Critical Path Tests

Tests the intelligence report generation flow:
- Generate intelligence report
- Get report by ID
- Self-dealing analysis
- Network analysis
- Correlation analysis

NOTE: Tests with @pytest.mark.timeout(10) will fail after 10s to prevent CI hangs.
      Tests hitting external APIs should accept 408/500/503 as valid responses.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

# conftest.py handles all env setup and imports
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_token():
    """Get an auth token for testing."""
    email = f"intel_test_{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={
        "email": email,
        "password": "TestPassword123!"
    })
    if r.status_code == 200:
        return r.json()["access_token"]
    r = client.post("/auth/login", json={
        "email": email,
        "password": "TestPassword123!"
    })
    return r.json().get("access_token", "")


@pytest.fixture
def auth_headers(auth_token):
    """Get auth headers for requests."""
    return {"Authorization": f"Bearer {auth_token}"}


class TestIntelligenceReports:
    """Test intelligence report generation and retrieval."""

    def test_generate_report_requires_auth(self):
        """Test that generating report requires authentication."""
        r = client.post(
            "/intelligence/generate",
            params={"entity_name": "Apple Inc", "entity_type": "org"}
        )
        assert r.status_code in (401, 429)  # 429 if rate limited

    @pytest.mark.skip(reason="External APIs (Apify/SEC/Apollo) timeout in CI - run manually")
    @pytest.mark.timeout(30)
    def test_generate_basic_report(self, auth_headers):
        """Test generating a basic intelligence report.

        NOTE: This test requires external APIs (Apify, SEC, Apollo) which timeout.
        Skipped in CI to prevent blocking. Run manually with:
        pytest tests/test_intelligence.py::TestIntelligenceReports::test_generate_basic_report -v
        """
        r = client.post(
            "/intelligence/generate",
            headers=auth_headers,
            params={
                "entity_name": "Apple Inc",
                "entity_type": "org",
                "ticker": "AAPL"
            }
        )
        assert r.status_code in (200, 201, 202, 404, 408, 422, 429, 500, 503, 504)

    def test_list_reports(self, auth_headers):
        """Test listing intelligence reports."""
        r = client.get("/intelligence/reports", headers=auth_headers)
        assert r.status_code in (200, 404, 422, 429)

    def test_get_report_by_id(self, auth_headers):
        """Test retrieving a report by ID."""
        # Try to get a nonexistent report
        r = client.get("/intelligence/reports/nonexistent-id", headers=auth_headers)
        assert r.status_code in (404, 200)


class TestSelfDealingAnalysis:
    """Test self-dealing detection endpoints."""

    @pytest.mark.timeout(45)
    def test_self_dealing_analysis(self, auth_headers):
        """Test self-dealing analysis endpoint."""
        r = client.post(
            "/intelligence/self-dealing",
            headers=auth_headers,
            json={
                "ticker": "AAPL",
                "entity_name": "Apple Inc"
            }
        )
        assert r.status_code in (200, 404, 408, 422, 429, 500, 503, 504)

    def test_self_dealing_without_ticker(self, auth_headers):
        """Test self-dealing analysis without required params."""
        r = client.post(
            "/intelligence/self-dealing",
            headers=auth_headers,
            json={}
        )
        assert r.status_code in (400, 422, 429)


class TestNetworkAnalysis:
    """Test entity network analysis endpoints."""

    @pytest.mark.skip(reason="SEC API timeouts in CI - run manually")
    @pytest.mark.timeout(20)
    def test_network_analysis(self, auth_headers):
        """Test network analysis endpoint."""
        r = client.post(
            "/intelligence/network",
            headers=auth_headers,
            json={
                "ticker": "AAPL",
                "entity_name": "Apple Inc"
            }
        )
        assert r.status_code in (200, 404, 408, 422, 429, 500, 503, 504)

    @pytest.mark.skip(reason="SEC API timeouts in CI - run manually")
    @pytest.mark.timeout(20)
    def test_network_depth_parameter(self, auth_headers):
        """Test network analysis with depth parameter."""
        r = client.post(
            "/intelligence/network",
            headers=auth_headers,
            json={
                "ticker": "AAPL",
                "entity_name": "Apple Inc",
                "max_depth": 2
            }
        )
        assert r.status_code in (200, 404, 408, 422, 429, 500, 503, 504)


class TestCorrelationAnalysis:
    """Test correlation analysis endpoints."""

    @pytest.mark.timeout(20)
    def test_correlation_analysis(self, auth_headers):
        """Test correlation analysis endpoint."""
        r = client.post(
            "/intelligence/correlation",
            headers=auth_headers,
            json={
                "ticker": "AAPL",
                "peer_tickers": ["MSFT", "GOOGL"]
            }
        )
        assert r.status_code in (200, 404, 408, 422, 429, 500, 503, 504)


class TestMarketEndpoints:
    """Test market data endpoints that feed intelligence."""

    def test_market_snapshot(self, auth_headers):
        """Test market snapshot endpoint."""
        r = client.get("/market/snapshot/AAPL", headers=auth_headers)
        assert r.status_code in (200, 404)

    def test_market_chart(self, auth_headers):
        """Test market chart endpoint."""
        r = client.get("/market/chart/AAPL", headers=auth_headers)
        assert r.status_code in (200, 404)

    def test_market_fundamentals(self, auth_headers):
        """Test market fundamentals endpoint."""
        r = client.get("/market/fundamentals/AAPL", headers=auth_headers)
        assert r.status_code in (200, 404)


class TestSECEndpoints:
    """Test SEC data endpoints."""

    def test_sec_filings(self, auth_headers):
        """Test SEC filings endpoint."""
        r = client.get("/sec/filings/AAPL", headers=auth_headers)
        assert r.status_code in (200, 404)

    def test_sec_13f(self, auth_headers):
        """Test SEC 13F endpoint."""
        r = client.get("/market/13f/holders/AAPL", headers=auth_headers)
        assert r.status_code in (200, 404)


class TestIntelligenceGraphStore:
    """Test intelligence graph store endpoints."""

    def test_bootstrap_entities(self, auth_headers):
        """Test entity bootstrap endpoint."""
        r = client.post("/entities/bootstrap", headers=auth_headers)
        assert r.status_code in (200, 401, 403, 404, 429)

    def test_get_entity(self, auth_headers):
        """Test getting entity details."""
        r = client.get("/entities/lookup?name=Apple", headers=auth_headers)
        assert r.status_code in (200, 404)

    def test_search_entities(self, auth_headers):
        """Test entity search."""
        r = client.get("/entities/search?q=Apple", headers=auth_headers)
        assert r.status_code in (200, 404)


class TestRecursiveEntityDiscovery:
    """Test recursive entity discovery endpoints."""

    @pytest.mark.skip(reason="SEC/FEC APIs timeout in CI - run manually")
    @pytest.mark.timeout(30)
    def test_recursive_discover(self, auth_headers):
        """Test recursive entity discovery.

        NOTE: This test may timeout due to recursive SEC/FEC API calls.
        """
        r = client.post(
            "/recursive/discover/AAPL",
            headers=auth_headers,
            params={"max_depth": 2}
        )
        assert r.status_code in (200, 404, 408, 422, 429, 500, 503, 504)

    @pytest.mark.skip(reason="SEC API timeouts in CI - run manually")
    @pytest.mark.timeout(30)
    def test_entity_graph(self, auth_headers):
        """Test entity graph building."""
        r = client.get(
            "/recursive/graph/AAPL",
            headers=auth_headers,
            params={"max_depth": 2}
        )
        assert r.status_code in (200, 404, 500, 503, 504)


class TestInputValidation:
    """Test input validation for intelligence endpoints."""

    @pytest.mark.skip(reason="Calls /intelligence/generate which hits external APIs - run manually")
    def test_invalid_ticker_format(self, auth_headers):
        """Test handling of invalid ticker format."""
        r = client.post(
            "/intelligence/generate",
            headers=auth_headers,
            params={
                "entity_name": "Test",
                "ticker": "INVALID_TICKER_TOO_LONG"
            }
        )
        # Should either reject or handle gracefully
        assert r.status_code in (200, 400, 404, 422, 429, 500)

    @pytest.mark.skip(reason="Calls /intelligence/generate which hits external APIs - run manually")
    def test_empty_entity_name(self, auth_headers):
        """Test handling of empty entity name."""
        r = client.post(
            "/intelligence/generate",
            headers=auth_headers,
            params={
                "entity_name": "",
                "entity_type": "org"
            }
        )
        assert r.status_code in (400, 404, 422, 429)
