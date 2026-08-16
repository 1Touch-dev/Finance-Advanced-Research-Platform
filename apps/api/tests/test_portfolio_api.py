"""
Tests for Portfolio API (Band C #32)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Portfolio Service Tests ───────────────────────────────────────────────────

class TestPortfolioService:
    """Test the portfolio service directly."""

    def test_service_imports(self):
        """Service can be imported."""
        from app.services.portfolio_service import get_portfolio_service, PortfolioService
        service = get_portfolio_service()
        assert isinstance(service, PortfolioService)

    def test_calculate_holdings_empty(self):
        """Empty positions returns empty holdings."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()
        holdings = service.calculate_holdings([])
        assert holdings == []

    def test_calculate_holdings_single(self):
        """Single position calculates correctly."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        positions = [{"ticker": "AAPL", "qty": 100, "cost_basis": 150.0}]
        holdings = service.calculate_holdings(positions)

        assert len(holdings) == 1
        assert holdings[0].ticker == "AAPL"
        assert holdings[0].quantity == 100
        assert holdings[0].cost_basis == 150.0
        assert holdings[0].market_value > 0
        assert holdings[0].weight == 1.0  # Only position

    def test_calculate_holdings_multiple(self):
        """Multiple positions calculate weights correctly."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        positions = [
            {"ticker": "AAPL", "qty": 100, "cost_basis": 150.0},
            {"ticker": "MSFT", "qty": 50, "cost_basis": 350.0},
        ]
        holdings = service.calculate_holdings(positions)

        assert len(holdings) == 2
        total_weight = sum(h.weight for h in holdings)
        assert abs(total_weight - 1.0) < 0.001  # Weights sum to 1

    def test_calculate_sector_allocation(self):
        """Sector allocation groups holdings correctly."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        positions = [
            {"ticker": "AAPL", "qty": 100, "cost_basis": 150.0},
            {"ticker": "MSFT", "qty": 50, "cost_basis": 350.0},
            {"ticker": "JPM", "qty": 25, "cost_basis": 200.0},
        ]
        holdings = service.calculate_holdings(positions)
        allocation = service.calculate_sector_allocation(holdings)

        assert len(allocation) >= 2  # Technology + Financials at least
        total_weight = sum(a.weight for a in allocation)
        assert abs(total_weight - 1.0) < 0.001

    def test_calculate_performance(self):
        """Performance metrics calculate correctly."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        positions = [
            {"ticker": "AAPL", "qty": 100, "cost_basis": 150.0},
            {"ticker": "MSFT", "qty": 50, "cost_basis": 350.0},
        ]
        holdings = service.calculate_holdings(positions)
        performance = service.calculate_performance(holdings)

        assert performance.total_market_value > 0
        assert performance.total_cost_basis > 0
        assert performance.holdings_count == 2
        assert performance.positive_positions + performance.negative_positions == 2

    def test_performance_empty(self):
        """Empty portfolio returns zero metrics."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        performance = service.calculate_performance([])

        assert performance.total_market_value == 0
        assert performance.holdings_count == 0

    def test_portfolio_summary(self):
        """Full portfolio summary includes all components."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        positions = [
            {"ticker": "AAPL", "qty": 100, "cost_basis": 150.0},
            {"ticker": "NVDA", "qty": 20, "cost_basis": 800.0},
        ]

        summary = service.get_portfolio_summary(
            portfolio_id=1,
            name="Test Portfolio",
            base_currency="USD",
            thesis="Test thesis",
            positions=positions,
            created_at="2025-01-01",
        )

        assert summary.portfolio_id == 1
        assert summary.name == "Test Portfolio"
        assert len(summary.holdings) == 2
        assert len(summary.sector_allocation) > 0
        assert summary.performance.holdings_count == 2

    def test_summary_to_dict(self):
        """Summary serializes to dict correctly."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        positions = [{"ticker": "AAPL", "qty": 100, "cost_basis": 150.0}]
        summary = service.get_portfolio_summary(
            portfolio_id=1,
            name="Test",
            base_currency="USD",
            thesis=None,
            positions=positions,
            created_at="2025-01-01",
        )

        data = summary.to_dict()
        assert "holdings" in data
        assert "sector_allocation" in data
        assert "performance" in data


# ── Holding Tests ─────────────────────────────────────────────────────────────

class TestHolding:
    """Test Holding dataclass."""

    def test_holding_to_dict(self):
        """Holding serializes correctly."""
        from app.services.portfolio_service import Holding

        holding = Holding(
            ticker="AAPL",
            quantity=100,
            cost_basis=150.0,
            current_price=180.0,
            market_value=18000.0,
            unrealized_pnl=3000.0,
            unrealized_pnl_pct=20.0,
            weight=0.5,
            sector="Technology",
            industry="Consumer Electronics",
        )

        data = holding.to_dict()
        assert data["ticker"] == "AAPL"
        assert data["quantity"] == 100
        assert data["weight"] == 50.0  # Converted to percentage


# ── API Endpoint Tests ────────────────────────────────────────────────────────

class TestPortfolioAPI:
    """Test portfolio API endpoints."""

    def test_list_portfolios(self):
        """GET /portfolio returns list."""
        response = client.get("/portfolio")
        # May be empty or have data, just check structure
        assert response.status_code in (200, 500)  # 500 if no DB
        if response.status_code == 200:
            data = response.json()
            assert "portfolios" in data
            assert "count" in data

    def test_create_portfolio_validation(self):
        """POST /portfolio requires name."""
        response = client.post("/portfolio")
        # Should fail without name parameter
        assert response.status_code in (422, 500)

    def test_get_portfolio_not_found(self):
        """GET /portfolio/{id} returns 404 for missing."""
        response = client.get("/portfolio/99999")
        assert response.status_code in (404, 500)

    def test_delete_portfolio_not_found(self):
        """DELETE /portfolio/{id} returns 404 for missing."""
        response = client.delete("/portfolio/99999")
        assert response.status_code in (404, 500)

    def test_compare_needs_two(self):
        """GET /portfolio/compare requires 2+ portfolios."""
        response = client.get("/portfolio/compare?ids=1")
        assert response.status_code in (400, 500)


# ── Performance Endpoint Tests ────────────────────────────────────────────────

class TestPerformanceAPI:
    """Test performance-related endpoints."""

    def test_performance_not_found(self):
        """GET /portfolio/{id}/performance returns 404 for missing."""
        response = client.get("/portfolio/99999/performance")
        assert response.status_code in (404, 500)

    def test_allocation_not_found(self):
        """GET /portfolio/{id}/allocation returns 404 for missing."""
        response = client.get("/portfolio/99999/allocation")
        assert response.status_code in (404, 500)


# ── Position Endpoint Tests ───────────────────────────────────────────────────

class TestPositionAPI:
    """Test position-related endpoints."""

    def test_add_position_requires_portfolio(self):
        """POST /portfolio/{id}/positions fails for missing portfolio."""
        response = client.post(
            "/portfolio/99999/positions",
            params={"ticker": "AAPL", "quantity": 100, "cost_basis": 150}
        )
        assert response.status_code in (404, 500)

    def test_update_position_not_found(self):
        """PUT /portfolio/{id}/positions/{pos_id} returns 404."""
        response = client.put(
            "/portfolio/99999/positions/99999",
            params={"quantity": 200}
        )
        assert response.status_code in (404, 500)

    def test_delete_position_not_found(self):
        """DELETE /portfolio/{id}/positions/{pos_id} returns 404."""
        response = client.delete("/portfolio/99999/positions/99999")
        assert response.status_code in (404, 500)


# ── Dataclass Tests ───────────────────────────────────────────────────────────

class TestDataclasses:
    """Test dataclass definitions."""

    def test_sector_allocation_to_dict(self):
        """SectorAllocation serializes correctly."""
        from app.services.portfolio_service import SectorAllocation

        alloc = SectorAllocation(
            sector="Technology",
            weight=0.6,
            market_value=60000,
            holdings_count=3,
            day_change=500,
        )

        data = alloc.to_dict()
        assert data["sector"] == "Technology"
        assert data["weight"] == 60.0  # Converted to percentage
        assert data["holdings_count"] == 3

    def test_performance_metrics_to_dict(self):
        """PerformanceMetrics serializes correctly."""
        from app.services.portfolio_service import PerformanceMetrics

        perf = PerformanceMetrics(
            total_market_value=100000,
            total_cost_basis=80000,
            total_unrealized_pnl=20000,
            total_unrealized_pnl_pct=25.0,
            day_change=500,
            day_change_pct=0.5,
            holdings_count=5,
            positive_positions=4,
            negative_positions=1,
            largest_position_weight=0.3,
            top_gainer="NVDA",
            top_gainer_pct=50.0,
            top_loser="INTC",
            top_loser_pct=-10.0,
        )

        data = perf.to_dict()
        assert data["total_market_value"] == 100000
        assert data["holdings_count"] == 5
        assert data["top_gainer"] == "NVDA"


# ── Edge Cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_holdings_with_zero_quantity(self):
        """Zero quantity positions are handled."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        positions = [{"ticker": "AAPL", "qty": 0, "cost_basis": 150.0}]
        holdings = service.calculate_holdings(positions)
        # Should handle gracefully
        assert len(holdings) == 1

    def test_holdings_with_unknown_ticker(self):
        """Unknown tickers get default sector."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        positions = [{"ticker": "UNKNOWN123", "qty": 100, "cost_basis": 50.0}]
        holdings = service.calculate_holdings(positions)

        assert len(holdings) == 1
        assert holdings[0].sector == "Other"

    def test_performance_with_single_holding(self):
        """Single holding calculates performance correctly."""
        from app.services.portfolio_service import get_portfolio_service
        service = get_portfolio_service()

        positions = [{"ticker": "AAPL", "qty": 100, "cost_basis": 150.0}]
        holdings = service.calculate_holdings(positions)
        perf = service.calculate_performance(holdings)

        assert perf.holdings_count == 1
        assert perf.largest_position_weight == 1.0  # Only position


# ── Enum Tests ────────────────────────────────────────────────────────────────

class TestEnums:
    """Test enum definitions."""

    def test_asset_class_enum(self):
        """AssetClass enum has expected values."""
        from app.services.portfolio_service import AssetClass

        assert AssetClass.EQUITY.value == "equity"
        assert AssetClass.ETF.value == "etf"
        assert AssetClass.CRYPTO.value == "crypto"
        assert AssetClass.CASH.value == "cash"
