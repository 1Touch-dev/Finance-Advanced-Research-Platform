"""
Tests for Litigation Intelligence API (Band C #52-56)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Service Unit Tests ────────────────────────────────────────────────────────


class TestEnforcementTypes:
    """Test enforcement type enums."""

    def test_enforcement_type_values(self):
        """EnforcementType has expected values."""
        from app.services.litigation_service import EnforcementType

        assert EnforcementType.SEC.value == "sec"
        assert EnforcementType.DOJ.value == "doj"
        assert EnforcementType.FTC.value == "ftc"
        assert EnforcementType.OFAC.value == "ofac"

    def test_risk_level_values(self):
        """RiskLevel has expected values."""
        from app.services.litigation_service import RiskLevel

        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MINIMAL.value == "minimal"


class TestEnforcementEvent:
    """Test EnforcementEvent dataclass."""

    def test_to_dict(self):
        """EnforcementEvent serializes correctly."""
        from app.services.litigation_service import EnforcementEvent, EnforcementType

        event = EnforcementEvent(
            event_id="ENF0001",
            event_type=EnforcementType.SEC,
            event_date="2025-01-15",
            entity_name="Test Corp",
            ticker="TEST",
            description="SEC enforcement action",
            amount=1000000,
            agency="SEC",
        )

        data = event.to_dict()
        assert data["event_id"] == "ENF0001"
        assert data["event_type"] == "sec"
        assert data["ticker"] == "TEST"
        assert data["amount"] == 1000000


class TestEventStudyResult:
    """Test EventStudyResult dataclass."""

    def test_to_dict(self):
        """EventStudyResult serializes correctly."""
        from app.services.litigation_service import (
            EventStudyResult,
            EnforcementEvent,
            EnforcementType,
        )

        event = EnforcementEvent(
            event_id="ENF0001",
            event_type=EnforcementType.SEC,
            event_date="2025-01-15",
            entity_name="Test Corp",
            ticker="TEST",
            description="Test event",
        )

        result = EventStudyResult(
            event=event,
            pre_event_return=-0.02,
            event_day_return=-0.05,
            post_event_return=-0.03,
            cumulative_abnormal_return=-0.10,
            market_reaction="strongly_negative",
        )

        data = result.to_dict()
        assert data["event"]["event_id"] == "ENF0001"
        assert data["event_day_return"] == -0.05
        assert data["market_reaction"] == "strongly_negative"


class TestDocketVelocity:
    """Test DocketVelocity dataclass (#53)."""

    def test_to_dict(self):
        """DocketVelocity serializes correctly."""
        from app.services.litigation_service import DocketVelocity, RiskLevel

        velocity = DocketVelocity(
            ticker="TEST",
            company_name="Test Corp",
            period_days=90,
            new_filings=5,
            avg_filings_per_period=2.0,
            velocity_ratio=2.5,
            undisclosed_count=2,
            days_to_disclosure_avg=45.0,
            alert_level=RiskLevel.HIGH,
            recent_cases=[{"case_name": "Test v. Test"}],
        )

        data = velocity.to_dict()
        assert data["ticker"] == "TEST"
        assert data["new_filings"] == 5
        assert data["velocity_ratio"] == 2.5
        assert data["alert_level"] == "high"


class TestNormalizedExposure:
    """Test NormalizedExposure dataclass (#54)."""

    def test_to_dict(self):
        """NormalizedExposure serializes correctly."""
        from app.services.litigation_service import NormalizedExposure, RiskLevel

        exposure = NormalizedExposure(
            ticker="TEST",
            company_name="Test Corp",
            total_litigation_exposure=100000000,
            exposure_to_revenue=5.5,
            exposure_to_market_cap=2.3,
            risk_level=RiskLevel.MEDIUM,
            case_count=10,
            active_cases=5,
        )

        data = exposure.to_dict()
        assert data["ticker"] == "TEST"
        assert data["total_litigation_exposure"] == 100000000
        assert data["exposure_to_revenue"] == 5.5
        assert data["risk_level"] == "medium"


class TestLitigationSnapshot:
    """Test LitigationSnapshot dataclass (#55)."""

    def test_to_dict(self):
        """LitigationSnapshot serializes correctly."""
        from app.services.litigation_service import LitigationSnapshot

        snapshot = LitigationSnapshot(
            ticker="TEST",
            as_of_date="2025-01-15",
            total_cases=20,
            active_cases=8,
            total_exposure=50000000,
            disclosed_exposure=40000000,
            undisclosed_exposure=10000000,
            by_type={"securities": 5, "patent": 3},
            risk_score=65.0,
        )

        data = snapshot.to_dict()
        assert data["ticker"] == "TEST"
        assert data["total_cases"] == 20
        assert data["undisclosed_exposure"] == 10000000
        assert data["by_type"]["securities"] == 5


class TestLitigationTimeSeries:
    """Test LitigationTimeSeries dataclass (#55)."""

    def test_to_dict(self):
        """LitigationTimeSeries serializes correctly."""
        from app.services.litigation_service import LitigationTimeSeries, LitigationSnapshot

        snapshot = LitigationSnapshot(
            ticker="TEST",
            as_of_date="2025-01-01",
            total_cases=15,
            active_cases=5,
            total_exposure=30000000,
            disclosed_exposure=25000000,
            undisclosed_exposure=5000000,
        )

        series = LitigationTimeSeries(
            ticker="TEST",
            company_name="Test Corp",
            start_date="2024-01-01",
            end_date="2025-01-01",
            frequency="quarterly",
            snapshots=[snapshot],
        )

        data = series.to_dict()
        assert data["ticker"] == "TEST"
        assert data["frequency"] == "quarterly"
        assert len(data["snapshots"]) == 1


class TestScreenerFields:
    """Test LitigationScreenerFields dataclass (#56)."""

    def test_to_dict(self):
        """LitigationScreenerFields serializes correctly."""
        from app.services.litigation_service import LitigationScreenerFields, RiskLevel

        fields = LitigationScreenerFields(
            ticker="TEST",
            company_name="Test Corp",
            total_cases=25,
            active_cases=10,
            total_exposure_usd=75000000,
            exposure_pct_revenue=3.5,
            exposure_pct_market_cap=1.2,
            new_cases_30d=2,
            new_cases_90d=6,
            risk_score=55.0,
            risk_level=RiskLevel.MEDIUM,
            securities_cases=5,
            has_sec_enforcement=True,
            has_class_action=True,
            velocity_alert=False,
        )

        data = fields.to_dict()
        assert data["ticker"] == "TEST"
        assert data["total_cases"] == 25
        assert data["has_sec_enforcement"] is True
        assert data["risk_level"] == "medium"


class TestHelperFunctions:
    """Test helper functions."""

    def test_within_days_true(self):
        """_within_days returns True for recent date."""
        from datetime import datetime
        from app.services.litigation_service import _within_days

        today = datetime.now().strftime("%Y-%m-%d")
        assert _within_days(today, 30) is True

    def test_within_days_false_empty(self):
        """_within_days returns False for empty date."""
        from app.services.litigation_service import _within_days

        assert _within_days("", 30) is False

    def test_calculate_screener_risk_score(self):
        """Risk score calculation works correctly."""
        from app.services.litigation_service import (
            LitigationScreenerFields,
            RiskLevel,
            _calculate_screener_risk_score,
        )

        # Low risk case
        low_risk = LitigationScreenerFields(
            ticker="LOW",
            company_name="Low Risk Corp",
            total_cases=2,
            active_cases=1,
        )
        low_score = _calculate_screener_risk_score(low_risk)
        assert low_score < 30

        # High risk case
        high_risk = LitigationScreenerFields(
            ticker="HIGH",
            company_name="High Risk Corp",
            total_cases=25,
            active_cases=15,
            exposure_pct_market_cap=12.0,
            has_sec_enforcement=True,
            has_class_action=True,
            has_undisclosed=True,
            new_cases_30d=5,
        )
        high_score = _calculate_screener_risk_score(high_risk)
        assert high_score > 70


# ── API Tests ─────────────────────────────────────────────────────────────────


class TestEnforcementAPI:
    """Test enforcement events API (#52)."""

    def test_get_enforcement_events(self):
        """GET /litigation/{ticker}/enforcement returns events."""
        response = client.get("/litigation/AAPL/enforcement?years=1")
        # Should return even if empty (no errors)
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "events" in data
        assert "event_count" in data

    def test_get_enforcement_events_with_filter(self):
        """GET /litigation/{ticker}/enforcement accepts event_type filter."""
        response = client.get("/litigation/AAPL/enforcement?event_type=sec")
        assert response.status_code == 200

    def test_get_enforcement_events_invalid_type(self):
        """GET /litigation/{ticker}/enforcement rejects invalid event_type."""
        response = client.get("/litigation/AAPL/enforcement?event_type=invalid")
        assert response.status_code == 400


class TestEventStudyAPI:
    """Test event study API (#52)."""

    def test_run_event_study(self):
        """GET /litigation/{ticker}/event-study returns results."""
        response = client.get("/litigation/AAPL/event-study?event_window=5")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "event_window" in data
        assert "results" in data


class TestVelocityAPI:
    """Test docket velocity API (#53)."""

    def test_get_velocity(self):
        """GET /litigation/{ticker}/velocity returns velocity data."""
        response = client.get("/litigation/AAPL/velocity?period_days=90")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "new_filings" in data
        assert "velocity_ratio" in data
        assert "alert_level" in data


class TestExposureAPI:
    """Test normalized exposure API (#54)."""

    def test_get_exposure(self):
        """GET /litigation/{ticker}/exposure returns exposure data."""
        response = client.get("/litigation/AAPL/exposure")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "total_litigation_exposure" in data
        assert "risk_level" in data


class TestSnapshotAPI:
    """Test point-in-time snapshot API (#55)."""

    def test_get_snapshot(self):
        """GET /litigation/{ticker}/snapshot returns snapshot."""
        response = client.get("/litigation/AAPL/snapshot")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "as_of_date" in data
        assert "total_cases" in data

    def test_get_snapshot_with_date(self):
        """GET /litigation/{ticker}/snapshot accepts as_of_date."""
        response = client.get("/litigation/AAPL/snapshot?as_of_date=2024-06-01")
        assert response.status_code == 200


class TestHistoryAPI:
    """Test litigation history API (#55)."""

    def test_get_history(self):
        """GET /litigation/{ticker}/history returns time series."""
        response = client.get("/litigation/AAPL/history?start_date=2024-01-01")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "snapshots" in data
        assert "frequency" in data

    def test_get_history_invalid_frequency(self):
        """GET /litigation/{ticker}/history rejects invalid frequency."""
        response = client.get("/litigation/AAPL/history?start_date=2024-01-01&frequency=hourly")
        assert response.status_code == 400


class TestScreenerAPI:
    """Test screener API (#56)."""

    def test_get_screener_fields(self):
        """GET /litigation/{ticker}/screener-fields returns fields."""
        response = client.get("/litigation/AAPL/screener-fields")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "total_cases" in data
        assert "risk_score" in data
        assert "has_sec_enforcement" in data

    def test_screen_companies(self):
        """POST /litigation/screen filters companies."""
        response = client.post("/litigation/screen?tickers=AAPL&tickers=MSFT")
        assert response.status_code == 200
        data = response.json()
        assert "screened_count" in data
        assert "results" in data

    def test_screen_with_filters(self):
        """POST /litigation/screen accepts filter parameters."""
        response = client.post(
            "/litigation/screen?tickers=AAPL&min_risk_score=0&max_risk_score=100"
        )
        assert response.status_code == 200


class TestReferenceEndpoints:
    """Test reference data endpoints."""

    def test_list_enforcement_types(self):
        """GET /litigation/types/enforcement returns types."""
        response = client.get("/litigation/types/enforcement")
        assert response.status_code == 200
        data = response.json()
        assert "enforcement_types" in data
        assert len(data["enforcement_types"]) > 0

    def test_list_risk_levels(self):
        """GET /litigation/types/risk-levels returns levels."""
        response = client.get("/litigation/types/risk-levels")
        assert response.status_code == 200
        data = response.json()
        assert "risk_levels" in data
        assert len(data["risk_levels"]) == 5
