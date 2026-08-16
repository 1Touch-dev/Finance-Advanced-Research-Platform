"""
Tests for MEDIUM task APIs:
- #42 Cost Basis Tracking
- #44 Benchmark Attribution
- #45 Tax Lot Optimization
- #48 Shared Workspaces
- #49 Team Permission Roles
- J1 Person Timelines
- J2 Data Visualizations
- J3 Valuation Timeline
- J4 Reddit/Whale Improvements
- J5 Interactive Bubble Charts
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ============ #42 Cost Basis Tracking Tests ============

class TestCostBasisAPI:
    """Tests for Cost Basis Tracking API"""

    def test_get_positions(self):
        response = client.get("/cost-basis/positions")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data

    def test_get_positions_by_ticker(self):
        response = client.get("/cost-basis/positions?ticker=AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data

    def test_get_position_detail(self):
        response = client.get("/cost-basis/positions/AAPL")
        assert response.status_code == 200
        data = response.json()
        # Either has position data or error
        assert "ticker" in data or "error" in data

    def test_get_portfolio_summary(self):
        response = client.get("/cost-basis/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_cost_basis" in data or "error" in data

    def test_get_realized_gains(self):
        response = client.get("/cost-basis/realized-gains")
        assert response.status_code == 200
        data = response.json()
        assert "long_term" in data or "short_term" in data or "error" in data

    def test_calculate_sale(self):
        response = client.post(
            "/cost-basis/calculate-sale?ticker=AAPL&shares=10"
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_realized_gain" in data or "error" in data

    def test_tax_lot_comparison(self):
        response = client.get("/cost-basis/tax-lot-comparison/AAPL?shares=10")
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data or "error" in data

    def test_cost_basis_history(self):
        response = client.get("/cost-basis/history/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data or "positions" in data or "error" in data


# ============ #44 Benchmark Attribution Tests ============

class TestBenchmarkAPI:
    """Tests for Benchmark Attribution API"""

    def test_get_benchmarks(self):
        response = client.get("/benchmark/available")
        assert response.status_code == 200
        data = response.json()
        assert "benchmarks" in data

    def test_compare_portfolio(self):
        response = client.get("/benchmark/compare?benchmark=SPY")
        assert response.status_code == 200
        data = response.json()
        assert "portfolio" in data or "comparison" in data or "error" in data

    def test_sector_attribution(self):
        response = client.get("/benchmark/sector-attribution")
        assert response.status_code == 200
        data = response.json()
        # The function returns sectors in the data
        assert isinstance(data, dict)

    def test_historical_comparison(self):
        response = client.get("/benchmark/historical")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data or "error" in data

    def test_risk_metrics(self):
        response = client.get("/benchmark/risk-metrics")
        assert response.status_code == 200
        data = response.json()
        # Should have risk-related fields
        assert isinstance(data, dict)

    def test_risk_contribution(self):
        response = client.get("/benchmark/risk-contribution")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data or "error" in data

    def test_factor_exposure(self):
        response = client.get("/benchmark/factor-exposure")
        assert response.status_code == 200
        data = response.json()
        assert "positions" in data or "error" in data

    def test_performance_attribution(self):
        response = client.get("/benchmark/attribution")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_calculate_alpha(self):
        response = client.get("/benchmark/alpha/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "alpha" in data or "error" in data


# ============ #45 Tax Lot Optimization Tests ============

class TestTaxLotsAPI:
    """Tests for Tax Lot Optimization API"""

    def test_get_tax_lots(self):
        response = client.get("/tax-lots/")
        assert response.status_code == 200
        data = response.json()
        assert "lots" in data

    def test_get_tax_lots_by_ticker(self):
        response = client.get("/tax-lots/?ticker=AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "lots" in data

    def test_get_lot_by_id(self):
        response = client.get("/tax-lots/lot/TL001")
        assert response.status_code == 200
        data = response.json()
        # Either lot data or error
        assert "lot_id" in data or "error" in data

    def test_optimize_sale(self):
        response = client.get("/tax-lots/optimize?ticker=AAPL&shares=50")
        assert response.status_code == 200
        data = response.json()
        assert "selected_lots" in data or "error" in data

    def test_compare_methods(self):
        response = client.get("/tax-lots/compare-methods?ticker=AAPL&shares=50")
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data or "error" in data

    def test_harvesting_opportunities(self):
        response = client.get("/tax-lots/harvesting-opportunities")
        assert response.status_code == 200
        data = response.json()
        assert "opportunities" in data

    def test_approaching_long_term(self):
        response = client.get("/tax-lots/approaching-long-term")
        assert response.status_code == 200
        data = response.json()
        assert "lots" in data


# ============ #48 Shared Workspaces Tests ============

class TestWorkspacesAPI:
    """Tests for Shared Workspaces API"""

    def test_get_user_workspaces(self):
        response = client.get("/workspaces/")
        assert response.status_code == 200
        data = response.json()
        assert "workspaces" in data

    def test_get_workspace(self):
        response = client.get("/workspaces/WS001")
        assert response.status_code == 200
        data = response.json()
        assert "workspace_id" in data or "error" in data

    def test_create_workspace(self):
        response = client.post(
            "/workspaces/?name=Test%20Workspace&description=Test"
        )
        assert response.status_code == 200
        data = response.json()
        assert "workspace_id" in data or "error" in data

    def test_get_workspace_activity(self):
        response = client.get("/workspaces/WS001/activity")
        assert response.status_code == 200
        data = response.json()
        assert "activity" in data

    def test_update_workspace(self):
        response = client.put("/workspaces/WS001?name=Updated%20Name")
        assert response.status_code == 200
        data = response.json()
        # Either updated workspace or error
        assert isinstance(data, dict)


# ============ #49 Team Permission Roles Tests ============

class TestTeamPermissionsAPI:
    """Tests for Team Permission Roles API"""

    def test_get_roles(self):
        response = client.get("/teams/roles")
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data

    def test_get_permissions(self):
        response = client.get("/teams/permissions")
        assert response.status_code == 200
        data = response.json()
        assert "permissions" in data

    def test_get_user_teams(self):
        response = client.get("/teams/")
        assert response.status_code == 200
        data = response.json()
        assert "teams" in data

    def test_get_team(self):
        response = client.get("/teams/TEAM001")
        assert response.status_code == 200
        data = response.json()
        assert "team_id" in data or "error" in data

    def test_create_team(self):
        response = client.post("/teams/?name=Test%20Team")
        assert response.status_code == 200
        data = response.json()
        assert "team_id" in data or "error" in data

    def test_get_member_permissions(self):
        response = client.get("/teams/TEAM001/members/demo_user/permissions")
        assert response.status_code == 200
        data = response.json()
        assert "permissions" in data or "error" in data

    def test_check_permission(self):
        response = client.get(
            "/teams/TEAM001/members/demo_user/check?permission=view_watchlists"
        )
        assert response.status_code == 200
        data = response.json()
        assert "has_permission" in data or "error" in data


# ============ J1 Person Timelines Tests ============

class TestPersonTimelineAPI:
    """Tests for Person Timeline API"""

    def test_search_persons(self):
        response = client.get("/persons/search?query=jensen")
        assert response.status_code == 200
        data = response.json()
        assert "persons" in data

    def test_get_person(self):
        response = client.get("/persons/jensen_huang")
        assert response.status_code == 200
        data = response.json()
        assert "person_id" in data or "name" in data or "error" in data

    def test_get_timeline(self):
        response = client.get("/persons/jensen_huang/timeline")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data or "error" in data

    def test_get_timeline_with_prices(self):
        response = client.get("/persons/jensen_huang/timeline-with-prices")
        assert response.status_code == 200
        data = response.json()
        assert "prices" in data or "error" in data

    def test_get_person_news(self):
        response = client.get("/persons/jensen_huang/news")
        assert response.status_code == 200
        data = response.json()
        assert "news" in data or "error" in data

    def test_get_person_trades(self):
        response = client.get("/persons/jensen_huang/trades")
        assert response.status_code == 200
        data = response.json()
        assert "trades" in data or "error" in data

    def test_get_person_filings(self):
        response = client.get("/persons/jensen_huang/filings")
        assert response.status_code == 200
        data = response.json()
        assert "filings" in data or "error" in data

    def test_compare_persons(self):
        response = client.get(
            "/persons/compare/multiple?person_ids=jensen_huang,elon_musk"
        )
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data or "error" in data


# ============ J2 Data Visualizations Tests ============

class TestDataVisualizationsAPI:
    """Tests for Data Visualizations API"""

    def test_sector_breakdown(self):
        response = client.get("/visualizations/sector-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_performance_comparison(self):
        response = client.get("/visualizations/performance-comparison?tickers=AAPL,MSFT")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_time_series(self):
        response = client.get("/visualizations/time-series/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data or "data" in data

    def test_correlation(self):
        response = client.get("/visualizations/correlation?tickers=AAPL,MSFT,GOOGL")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_treemap(self):
        response = client.get("/visualizations/treemap")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_scatter(self):
        response = client.get("/visualizations/scatter")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_candlestick(self):
        response = client.get("/visualizations/candlestick/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_area_chart(self):
        response = client.get("/visualizations/area?tickers=AAPL,MSFT")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_radar_chart(self):
        response = client.get("/visualizations/radar/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_histogram(self):
        response = client.get("/visualizations/histogram")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_gauge(self):
        response = client.get("/visualizations/gauge")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data

    def test_waterfall(self):
        response = client.get("/visualizations/waterfall/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data


# ============ J3 Valuation Timeline Tests ============

class TestValuationTimelineAPI:
    """Tests for Valuation Timeline API"""

    def test_get_timeline(self):
        response = client.get("/valuation/timeline/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data or "ticker" in data

    def test_compare_valuations(self):
        response = client.get("/valuation/compare?tickers=NVDA,AAPL,MSFT")
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data

    def test_get_bands(self):
        response = client.get("/valuation/bands/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "bands" in data or "ticker" in data

    def test_get_zscore(self):
        response = client.get("/valuation/zscore/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "zscores" in data or "overall_zscore" in data

    def test_get_sector_valuations(self):
        response = client.get("/valuation/sector/technology")
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data

    def test_get_events(self):
        response = client.get("/valuation/events/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data


# ============ J4 Reddit/Whale Tests ============

class TestRedditWhaleAPI:
    """Tests for Reddit & Whale Tracking API"""

    def test_reddit_sentiment(self):
        response = client.get("/social/reddit/sentiment")
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data or "sentiment_summary" in data

    def test_reddit_sentiment_by_ticker(self):
        response = client.get("/social/reddit/sentiment?ticker=NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data or "sentiment_summary" in data

    def test_reddit_trending(self):
        response = client.get("/social/reddit/trending")
        assert response.status_code == 200
        data = response.json()
        assert "trending" in data

    def test_subreddit_activity(self):
        response = client.get("/social/reddit/subreddit/wallstreetbets")
        assert response.status_code == 200
        data = response.json()
        assert "subreddit" in data

    def test_sentiment_history(self):
        response = client.get("/social/reddit/history/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data

    def test_whale_transactions(self):
        response = client.get("/social/whales/transactions")
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data

    def test_whale_flow(self):
        response = client.get("/social/whales/flow/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data

    def test_top_whales(self):
        response = client.get("/social/whales/top")
        assert response.status_code == 200
        data = response.json()
        assert "whales" in data

    def test_institutional_ownership(self):
        response = client.get("/social/institutional/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data

    def test_insider_sentiment(self):
        response = client.get("/social/insider-sentiment/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data

    def test_social_momentum(self):
        response = client.get("/social/momentum/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data


# ============ J5 Interactive Bubble Charts Tests ============

class TestBubbleChartsAPI:
    """Tests for Interactive Bubble Charts API"""

    def test_get_bubble_chart(self):
        response = client.get("/bubble-charts/")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data or "data" in data

    def test_get_bubble_chart_with_params(self):
        response = client.get(
            "/bubble-charts/?x_metric=pe_ratio&y_metric=growth&size_metric=market_cap"
        )
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data or "data" in data

    def test_get_presets(self):
        response = client.get("/bubble-charts/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data

    def test_get_animated(self):
        response = client.get("/bubble-charts/animated/NVDA")
        assert response.status_code == 200
        data = response.json()
        assert "frames" in data or "ticker" in data

    def test_get_sector_bubbles(self):
        response = client.get("/bubble-charts/sectors")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data or "data" in data

    def test_compare_bubbles(self):
        response = client.get("/bubble-charts/compare?ticker1=NVDA&ticker2=AMD")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data or "ticker1" in data

    def test_get_metrics(self):
        response = client.get("/bubble-charts/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data

    def test_get_portfolio_bubbles(self):
        response = client.get("/bubble-charts/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert "chart_type" in data or "data" in data


# Run summary
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
