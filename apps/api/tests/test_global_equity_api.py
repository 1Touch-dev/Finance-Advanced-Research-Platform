"""
Tests for Global Equity Coverage API (#34)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestGlobalMarkets:
    """Tests for global markets endpoints."""

    def test_list_markets(self):
        """Test listing supported markets."""
        response = client.get("/global/markets")
        assert response.status_code == 200
        data = response.json()
        assert "markets" in data
        assert "total_markets" in data
        assert len(data["markets"]) > 0
        # Check market structure
        market = data["markets"][0]
        assert "code" in market
        assert "name" in market
        assert "currency" in market
        assert "timezone" in market

    def test_market_status(self):
        """Test getting market status."""
        response = client.get("/global/markets/status")
        assert response.status_code == 200
        data = response.json()
        assert "markets" in data
        assert "timestamp" in data
        # Check status structure
        market = data["markets"][0]
        assert "status" in market
        assert "local_time" in market


class TestGlobalSearch:
    """Tests for global stock search."""

    def test_search_stocks(self):
        """Test searching global stocks."""
        response = client.get("/global/search?query=toyota")
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
        assert "count" in data

    def test_search_with_market_filter(self):
        """Test searching with market filter."""
        response = client.get("/global/search?query=SAP&markets=DE,FR")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data


class TestGlobalQuotes:
    """Tests for global quote endpoints."""

    def test_get_quote(self):
        """Test getting international stock quote."""
        response = client.get("/global/quote/7203.T")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "price" in data
        assert "change" in data
        assert "currency" in data
        assert "exchange" in data

    def test_get_quote_european(self):
        """Test getting European stock quote."""
        response = client.get("/global/quote/SAP.DE")
        assert response.status_code == 200
        data = response.json()
        assert data["currency"] == "EUR"


class TestCurrencyConversion:
    """Tests for currency conversion."""

    def test_convert_usd_to_eur(self):
        """Test USD to EUR conversion."""
        response = client.get("/global/convert?amount=100&from_currency=USD&to_currency=EUR")
        assert response.status_code == 200
        data = response.json()
        assert data["from"]["amount"] == 100
        assert data["from"]["currency"] == "USD"
        assert data["to"]["currency"] == "EUR"
        assert "rate" in data

    def test_convert_jpy_to_usd(self):
        """Test JPY to USD conversion."""
        response = client.get("/global/convert?amount=10000&from_currency=JPY&to_currency=USD")
        assert response.status_code == 200
        data = response.json()
        assert data["to"]["amount"] < data["from"]["amount"]


class TestADRMappings:
    """Tests for ADR/GDR mappings."""

    def test_get_adr_mapping(self):
        """Test getting ADR mapping."""
        response = client.get("/global/adr/7203.T")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "adr" in data
        assert "local" in data
        assert "premium_discount" in data


class TestGlobalIndices:
    """Tests for global indices."""

    def test_list_indices(self):
        """Test listing global indices."""
        response = client.get("/global/indices")
        assert response.status_code == 200
        data = response.json()
        assert "indices" in data
        assert len(data["indices"]) > 0
        # Check index structure
        index = data["indices"][0]
        assert "symbol" in index
        assert "name" in index
        assert "country" in index
        assert "value" in index
