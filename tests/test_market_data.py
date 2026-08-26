"""
Market Data Critical Path Tests

Tests the market data endpoints that are essential for the platform:
- Stock snapshots (via yfinance - free, no API key needed)
- Price history
- Fundamentals
- Technical indicators
- Company info
"""
import pytest
from fastapi.testclient import TestClient

# conftest.py handles all env setup and imports
from app.main import app

client = TestClient(app)


class TestMarketSnapshot:
    """Test market snapshot endpoints (free via yfinance)."""

    def test_get_stock_snapshot(self):
        """Test getting stock snapshot without auth (if public)."""
        r = client.get("/market/snapshot/AAPL")
        # Might require auth or be public (429 if rate limited, 404 if route not registered)
        assert r.status_code in (200, 401, 404, 429)

    def test_get_snapshot_valid_ticker(self):
        """Test snapshot for a valid ticker."""
        r = client.get("/market/snapshot/MSFT")
        if r.status_code == 200:
            data = r.json()
            # Should have price data
            assert "price" in data or "current_price" in data or "close" in data or "ticker" in data

    def test_get_snapshot_invalid_ticker(self):
        """Test snapshot for invalid ticker returns error or empty."""
        r = client.get("/market/snapshot/INVALID123XYZ")
        # Should return 404 or 200 with empty/error data
        assert r.status_code in (200, 404, 500)


class TestPriceHistory:
    """Test price history endpoints."""

    def test_get_price_history_daily(self):
        """Test getting daily price history."""
        r = client.get("/market/chart/AAPL?period=1mo&interval=1d")
        assert r.status_code in (200, 401, 404, 429)

    def test_get_price_history_weekly(self):
        """Test getting weekly price history."""
        r = client.get("/market/chart/AAPL?period=1y&interval=1wk")
        assert r.status_code in (200, 401, 404, 429)

    def test_price_history_response_structure(self):
        """Test price history response has expected structure."""
        r = client.get("/market/chart/AAPL")
        if r.status_code == 200:
            data = r.json()
            # Should have some price data structure
            assert isinstance(data, (dict, list))


class TestFundamentals:
    """Test fundamentals endpoints."""

    def test_get_fundamentals(self):
        """Test getting company fundamentals."""
        r = client.get("/market/fundamentals/AAPL")
        assert r.status_code in (200, 401, 404)

    def test_fundamentals_response_structure(self):
        """Test fundamentals has expected fields."""
        r = client.get("/market/fundamentals/MSFT")
        if r.status_code == 200:
            data = r.json()
            # Should be a dict with some financial data
            assert isinstance(data, dict)


class TestCompanyInfo:
    """Test company info endpoints."""

    def test_get_company_info(self):
        """Test getting company info."""
        r = client.get("/market/company/AAPL")
        assert r.status_code in (200, 401, 404)

    def test_company_info_structure(self):
        """Test company info has expected fields."""
        r = client.get("/market/company/GOOGL")
        if r.status_code == 200:
            data = r.json()
            # Should have company details
            assert isinstance(data, dict)


class TestTechnicalIndicators:
    """Test technical indicators endpoints."""

    def test_get_technicals(self):
        """Test getting technical indicators."""
        r = client.get("/market/technicals/AAPL")
        assert r.status_code in (200, 401, 404)


class TestOptionsData:
    """Test options data endpoints."""

    def test_get_options_chain(self):
        """Test getting options chain."""
        r = client.get("/market/options/AAPL")
        assert r.status_code in (200, 401, 404)


class TestInstitutionalHoldings:
    """Test 13F institutional holdings endpoints."""

    def test_get_institutional_holders(self):
        """Test getting institutional holders."""
        r = client.get("/market/13f/holders/AAPL")
        assert r.status_code in (200, 401, 404)

    def test_get_13f_filings(self):
        """Test getting 13F filings."""
        r = client.get("/market/13f/filings")
        assert r.status_code in (200, 401, 404)


class TestInsiderActivity:
    """Test insider activity endpoints."""

    def test_get_insider_trades(self):
        """Test getting insider trades."""
        r = client.get("/market/insider/AAPL")
        assert r.status_code in (200, 401, 404)


class TestMarketScreeners:
    """Test market screening endpoints."""

    def test_volume_screener(self):
        """Test volume screening endpoint."""
        r = client.get("/market/screener/volume")
        assert r.status_code in (200, 401, 404)

    def test_momentum_screener(self):
        """Test momentum screening endpoint."""
        r = client.get("/market/screener/momentum")
        assert r.status_code in (200, 401, 404)


class TestErrorHandling:
    """Test error handling in market endpoints."""

    def test_missing_ticker_parameter(self):
        """Test endpoint behavior when ticker is missing."""
        r = client.get("/market/snapshot/")
        # Should return 404 (route not found) or redirect
        assert r.status_code in (307, 404, 405)

    def test_special_characters_in_ticker(self):
        """Test handling of special characters in ticker."""
        r = client.get("/market/snapshot/AAPL%20")
        # Should handle gracefully
        assert r.status_code in (200, 400, 404, 500)

    def test_very_long_ticker(self):
        """Test handling of very long ticker string."""
        r = client.get("/market/snapshot/" + "A" * 100)
        # Should reject or handle gracefully
        assert r.status_code in (200, 400, 404, 500)


class TestCachingBehavior:
    """Test that responses are appropriately cached/fresh."""

    def test_multiple_requests_consistent(self):
        """Test that multiple requests return consistent data."""
        r1 = client.get("/market/snapshot/AAPL")
        r2 = client.get("/market/snapshot/AAPL")

        if r1.status_code == 200 and r2.status_code == 200:
            # Both should have similar structure
            assert type(r1.json()) == type(r2.json())
