"""
Tests for Insider Activity Screener API (Band C #41)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestRecentTransactions:
    def test_get_recent_default(self):
        response = client.get("/insider/transactions")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "count" in data
        assert data["filters"]["days"] == 7

    def test_get_recent_purchases(self):
        response = client.get("/insider/transactions?transaction_type=P")
        assert response.status_code == 200
        data = response.json()
        for txn in data["transactions"]:
            assert txn["transaction_type"] == "P"

    def test_get_recent_sales(self):
        response = client.get("/insider/transactions?transaction_type=S")
        assert response.status_code == 200
        data = response.json()
        for txn in data["transactions"]:
            assert txn["transaction_type"] == "S"

    def test_get_recent_min_value(self):
        response = client.get("/insider/transactions?min_value=1000000")
        assert response.status_code == 200
        data = response.json()
        for txn in data["transactions"]:
            assert txn["value"] >= 1000000

    def test_invalid_transaction_type(self):
        response = client.get("/insider/transactions?transaction_type=X")
        assert response.status_code == 400


class TestTransactionsByTicker:
    def test_get_by_ticker(self):
        response = client.get("/insider/ticker/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "NVDA"
        assert len(data["transactions"]) > 0
        for txn in data["transactions"]:
            assert txn["ticker"] == "NVDA"

    def test_get_by_ticker_custom_days(self):
        response = client.get("/insider/ticker/AMD?days=30")
        assert response.status_code == 200
        data = response.json()
        assert data["days_back"] == 30


class TestClusterBuys:
    def test_get_cluster_buys_default(self):
        response = client.get("/insider/cluster-buys")
        assert response.status_code == 200
        data = response.json()
        assert "clusters" in data
        assert data["min_insiders"] == 2
        for cluster in data["clusters"]:
            assert cluster["insider_count"] >= 2

    def test_get_cluster_buys_custom(self):
        response = client.get("/insider/cluster-buys?days=30&min_insiders=3")
        assert response.status_code == 200
        data = response.json()
        assert data["min_insiders"] == 3


class TestClusterSells:
    def test_get_cluster_sells_default(self):
        response = client.get("/insider/cluster-sells")
        assert response.status_code == 200
        data = response.json()
        assert "clusters" in data
        assert data["min_insiders"] == 2

    def test_get_cluster_sells_custom(self):
        response = client.get("/insider/cluster-sells?days=30&min_insiders=2")
        assert response.status_code == 200
        data = response.json()
        assert data["days_back"] == 30


class TestLargestTransactions:
    def test_get_largest_default(self):
        response = client.get("/insider/largest")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert len(data["transactions"]) <= 10
        # Check sorted by value
        if len(data["transactions"]) > 1:
            assert data["transactions"][0]["value"] >= data["transactions"][1]["value"]

    def test_get_largest_purchases(self):
        response = client.get("/insider/largest?transaction_type=P")
        assert response.status_code == 200
        data = response.json()
        for txn in data["transactions"]:
            assert txn["transaction_type"] == "P"

    def test_get_largest_sales(self):
        response = client.get("/insider/largest?transaction_type=S")
        assert response.status_code == 200


class TestCEOCFOTransactions:
    def test_get_ceo_cfo(self):
        response = client.get("/insider/ceo-cfo")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        for txn in data["transactions"]:
            assert txn["relationship"] in ["CEO", "CFO"]


class TestInsiderStats:
    def test_get_stats(self):
        response = client.get("/insider/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_transactions" in data
        assert "total_buys" in data
        assert "total_sells" in data
        assert "buy_value" in data
        assert "sell_value" in data
        assert "buy_sell_ratio" in data
        assert "by_relationship" in data


class TestInsiderSentiment:
    def test_get_sentiment(self):
        response = client.get("/insider/sentiment/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "NVDA"
        assert "total_buys" in data
        assert "total_sells" in data
        assert "signal" in data
        assert data["signal"] in ["strong_buy", "buy", "neutral", "sell", "strong_sell"]

    def test_get_sentiment_custom_days(self):
        response = client.get("/insider/sentiment/AMD?days=60")
        assert response.status_code == 200


class TestInsiderScreen:
    def test_screen_default(self):
        response = client.get("/insider/screen")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "filters" in data
        for result in data["results"]:
            assert "ticker" in result
            assert "signal" in result
            assert "net_value" in result

    def test_screen_buy_signals(self):
        response = client.get("/insider/screen?signal=buy")
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            assert result["signal"] == "buy"

    def test_screen_strong_buy(self):
        response = client.get("/insider/screen?signal=strong_buy")
        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            assert result["signal"] == "strong_buy"

    def test_screen_custom_filters(self):
        response = client.get("/insider/screen?min_buy_value=500000&min_insiders=2&days=30")
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["min_buy_value"] == 500000
        assert data["filters"]["min_insiders"] == 2

    def test_screen_invalid_signal(self):
        response = client.get("/insider/screen?signal=invalid")
        assert response.status_code == 400
