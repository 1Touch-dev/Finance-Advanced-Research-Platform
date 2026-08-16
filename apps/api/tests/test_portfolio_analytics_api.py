"""
Tests for Portfolio Analytics API (D1-D11)
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestFactorDecomposition:
    """D1: Factor decomposition tests."""

    def test_get_factor_decomposition(self):
        response = client.get("/portfolio-analytics/factor-decomposition?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "factors" in data
        assert "r_squared" in data
        assert len(data["factors"]) > 0


class TestRebalancing:
    """D2: Rebalancing tests."""

    def test_get_rebalancing_suggestions(self):
        response = client.post("/portfolio-analytics/rebalancing?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "current_allocation" in data
        assert "target_allocation" in data
        assert "suggested_trades" in data


class TestModelPortfolios:
    """D3: Model portfolios tests."""

    def test_get_model_portfolios(self):
        response = client.get("/portfolio-analytics/model-portfolios")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0
        assert "risk_level" in data["models"][0]


class TestRiskParity:
    """D4: Risk parity tests."""

    def test_get_risk_parity(self):
        response = client.get("/portfolio-analytics/risk-parity?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "allocations" in data
        assert "portfolio_volatility" in data
        assert "sharpe_ratio" in data


class TestScenarioAnalysis:
    """D5: Scenario analysis tests."""

    def test_run_scenario_analysis(self):
        response = client.post("/portfolio-analytics/scenario-analysis?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert "var_95" in data
        assert len(data["scenarios"]) > 0


class TestDrawdownAnalytics:
    """D6: Drawdown analytics tests."""

    def test_get_drawdown(self):
        response = client.get("/portfolio-analytics/drawdown?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "max_drawdown" in data
        assert "current_drawdown" in data
        assert "drawdown_periods" in data


class TestCorrelationMatrix:
    """D7: Correlation matrix tests."""

    def test_get_correlation_matrix(self):
        response = client.get("/portfolio-analytics/correlation-matrix?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "tickers" in data
        assert "matrix" in data
        assert "avg_correlation" in data


class TestSectorRotation:
    """D8: Sector rotation tests."""

    def test_get_sector_rotation(self):
        response = client.get("/portfolio-analytics/sector-rotation?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "recommended_rotation" in data
        assert len(data["signals"]) > 0


class TestFactorTiming:
    """D9: Factor timing tests."""

    def test_get_factor_timing(self):
        response = client.get("/portfolio-analytics/factor-timing")
        assert response.status_code == 200
        data = response.json()
        assert "factors" in data
        assert "market_regime" in data


class TestCustomBenchmark:
    """D10: Custom benchmark tests."""

    def test_create_custom_benchmark(self):
        components = [
            {"ticker": "SPY", "weight": 60},
            {"ticker": "AGG", "weight": 40}
        ]
        response = client.post(
            "/portfolio-analytics/custom-benchmark?user_id=test_user",
            json=components
        )
        assert response.status_code == 200
        data = response.json()
        assert "benchmark_id" in data
        assert "components" in data


class TestPerformanceAttribution:
    """D11: Performance attribution tests."""

    def test_get_performance_attribution(self):
        response = client.get("/portfolio-analytics/performance-attribution?user_id=test_user")
        assert response.status_code == 200
        data = response.json()
        assert "total_return" in data
        assert "benchmark_return" in data
        assert "attribution" in data
        assert "allocation_effect" in data["attribution"]
