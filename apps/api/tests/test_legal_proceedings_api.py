"""
Tests for Legal Proceedings & Litigation Reserves API (Band C #50-51)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Service Unit Tests ────────────────────────────────────────────────────────


class TestEnums:
    """Test enum definitions."""

    def test_case_type_values(self):
        """CaseType has expected values."""
        from app.services.legal_proceedings_service import CaseType

        assert CaseType.SECURITIES.value == "securities"
        assert CaseType.ANTITRUST.value == "antitrust"
        assert CaseType.PATENT.value == "patent"
        assert CaseType.GOVERNMENT_INVESTIGATION.value == "government_investigation"

    def test_case_status_values(self):
        """CaseStatus has expected values."""
        from app.services.legal_proceedings_service import CaseStatus

        assert CaseStatus.PENDING.value == "pending"
        assert CaseStatus.SETTLED.value == "settled"
        assert CaseStatus.DISMISSED.value == "dismissed"

    def test_materiality_assessment_values(self):
        """MaterialityAssessment has expected values."""
        from app.services.legal_proceedings_service import MaterialityAssessment

        assert MaterialityAssessment.PROBABLE.value == "probable"
        assert MaterialityAssessment.REASONABLY_POSSIBLE.value == "reasonably_possible"
        assert MaterialityAssessment.REMOTE.value == "remote"


class TestExtractedProceeding:
    """Test ExtractedProceeding dataclass (#50)."""

    def test_to_dict(self):
        """ExtractedProceeding serializes correctly."""
        from app.services.legal_proceedings_service import (
            ExtractedProceeding,
            CaseType,
            CaseStatus,
            MaterialityAssessment,
        )

        proceeding = ExtractedProceeding(
            proceeding_id="LP0001",
            case_type=CaseType.SECURITIES,
            case_status=CaseStatus.PENDING,
            description="Securities class action lawsuit",
            venue="U.S. District Court",
            amount_claimed=100000000,
            materiality=MaterialityAssessment.PROBABLE,
        )

        data = proceeding.to_dict()
        assert data["proceeding_id"] == "LP0001"
        assert data["case_type"] == "securities"
        assert data["case_status"] == "pending"
        assert data["amount_claimed"] == 100000000


class TestLitigationReserve:
    """Test LitigationReserve dataclass (#51)."""

    def test_to_dict(self):
        """LitigationReserve serializes correctly."""
        from app.services.legal_proceedings_service import LitigationReserve

        reserve = LitigationReserve(
            reserve_id="RES-TEST-2025-01-01",
            ticker="TEST",
            as_of_date="2025-01-01",
            total_reserve=50000000,
            reserve_for_probable=40000000,
            prior_period_reserve=45000000,
            reserve_change=5000000,
            reserve_change_pct=11.11,
            reserve_adequacy="adequate",
        )

        data = reserve.to_dict()
        assert data["reserve_id"] == "RES-TEST-2025-01-01"
        assert data["total_reserve"] == 50000000
        assert data["reserve_change"] == 5000000


class TestReserveTimeSeries:
    """Test ReserveTimeSeries dataclass (#51)."""

    def test_to_dict(self):
        """ReserveTimeSeries serializes correctly."""
        from app.services.legal_proceedings_service import (
            ReserveTimeSeries,
            LitigationReserve,
        )

        reserve = LitigationReserve(
            reserve_id="RES-TEST-2025-01-01",
            ticker="TEST",
            as_of_date="2025-01-01",
            total_reserve=50000000,
        )

        series = ReserveTimeSeries(
            ticker="TEST",
            company_name="Test Corp",
            reserves=[reserve],
            trend_direction="increasing",
            significant_increase=True,
        )

        data = series.to_dict()
        assert data["ticker"] == "TEST"
        assert data["trend_direction"] == "increasing"
        assert len(data["reserves"]) == 1


class TestLegalProceedingsReport:
    """Test LegalProceedingsReport dataclass (#50)."""

    def test_to_dict(self):
        """LegalProceedingsReport serializes correctly."""
        from app.services.legal_proceedings_service import (
            LegalProceedingsReport,
            ExtractedProceeding,
            CaseType,
            CaseStatus,
        )

        proceeding = ExtractedProceeding(
            proceeding_id="LP0001",
            case_type=CaseType.SECURITIES,
            case_status=CaseStatus.PENDING,
            description="Test case",
        )

        report = LegalProceedingsReport(
            ticker="TEST",
            company_name="Test Corp",
            cik="0000012345",
            filing_date="2025-01-01",
            proceedings=[proceeding],
            total_proceedings=1,
            has_securities_litigation=True,
        )

        data = report.to_dict()
        assert data["ticker"] == "TEST"
        assert data["total_proceedings"] == 1
        assert data["has_securities_litigation"] is True


class TestHelperFunctions:
    """Test helper functions."""

    def test_parse_amount_millions(self):
        """_parse_amount parses millions correctly."""
        from app.services.legal_proceedings_service import _parse_amount

        assert _parse_amount("$50 million") == 50000000
        assert _parse_amount("$100.5 million") == 100500000

    def test_parse_amount_billions(self):
        """_parse_amount parses billions correctly."""
        from app.services.legal_proceedings_service import _parse_amount

        assert _parse_amount("$1.2 billion") == 1200000000

    def test_parse_amount_no_match(self):
        """_parse_amount returns None for no match."""
        from app.services.legal_proceedings_service import _parse_amount

        assert _parse_amount("no amount here") is None

    def test_classify_case_type_securities(self):
        """_classify_case_type identifies securities cases."""
        from app.services.legal_proceedings_service import _classify_case_type, CaseType

        assert _classify_case_type("10b-5 securities fraud") == CaseType.SECURITIES
        assert _classify_case_type("shareholder derivative action") == CaseType.SECURITIES

    def test_classify_case_type_antitrust(self):
        """_classify_case_type identifies antitrust cases."""
        from app.services.legal_proceedings_service import _classify_case_type, CaseType

        assert _classify_case_type("antitrust price fixing") == CaseType.ANTITRUST
        assert _classify_case_type("Sherman Act violation") == CaseType.ANTITRUST

    def test_classify_case_type_patent(self):
        """_classify_case_type identifies patent cases."""
        from app.services.legal_proceedings_service import _classify_case_type, CaseType

        assert _classify_case_type("patent infringement") == CaseType.PATENT

    def test_determine_status(self):
        """_determine_status identifies case status."""
        from app.services.legal_proceedings_service import _determine_status, CaseStatus

        assert _determine_status("case was settled") == CaseStatus.SETTLED
        assert _determine_status("case was dismissed") == CaseStatus.DISMISSED
        assert _determine_status("matter is pending") == CaseStatus.PENDING

    def test_assess_materiality(self):
        """_assess_materiality identifies materiality assessments."""
        from app.services.legal_proceedings_service import (
            _assess_materiality,
            MaterialityAssessment,
        )

        assert _assess_materiality("probable loss") == MaterialityAssessment.PROBABLE
        assert _assess_materiality("reasonably possible") == MaterialityAssessment.REASONABLY_POSSIBLE
        assert _assess_materiality("remote likelihood") == MaterialityAssessment.REMOTE

    def test_extract_venue(self):
        """_extract_venue extracts court information."""
        from app.services.legal_proceedings_service import _extract_venue

        assert "District Court" in (_extract_venue("U.S. District Court for Delaware") or "")
        assert _extract_venue("no court mentioned") is None


# ── API Tests ─────────────────────────────────────────────────────────────────


class TestProceedingsAPI:
    """Test legal proceedings API (#50)."""

    def test_get_proceedings(self):
        """GET /legal/{ticker}/proceedings returns proceedings."""
        response = client.get("/legal/AAPL/proceedings")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "proceedings" in data
        assert "total_proceedings" in data

    def test_get_proceedings_with_filter(self):
        """GET /legal/{ticker}/proceedings accepts filters."""
        response = client.get("/legal/AAPL/proceedings?case_type=securities")
        assert response.status_code == 200

    def test_get_proceedings_invalid_type(self):
        """GET /legal/{ticker}/proceedings rejects invalid case_type."""
        response = client.get("/legal/AAPL/proceedings?case_type=invalid")
        assert response.status_code == 400

    def test_get_proceedings_summary(self):
        """GET /legal/{ticker}/proceedings/summary returns summary."""
        response = client.get("/legal/AAPL/proceedings/summary")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "total_proceedings" in data
        assert "by_type" in data


class TestReservesAPI:
    """Test litigation reserves API (#51)."""

    def test_get_reserves(self):
        """GET /legal/{ticker}/reserves returns reserves."""
        response = client.get("/legal/AAPL/reserves")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data

    def test_get_reserve_history(self):
        """GET /legal/{ticker}/reserve-history returns history."""
        response = client.get("/legal/AAPL/reserve-history?periods=4")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "reserves" in data

    def test_get_reserve_adequacy(self):
        """GET /legal/{ticker}/reserve-adequacy returns analysis."""
        response = client.get("/legal/AAPL/reserve-adequacy")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "adequacy_assessment" in data

    def test_get_reserve_ratios(self):
        """GET /legal/{ticker}/reserve-ratios returns ratios."""
        response = client.get("/legal/AAPL/reserve-ratios")
        assert response.status_code == 200
        data = response.json()
        assert "ticker" in data
        assert "total_reserve" in data


class TestReferenceEndpoints:
    """Test reference data endpoints."""

    def test_list_case_types(self):
        """GET /legal/types/case-types returns types."""
        response = client.get("/legal/types/case-types")
        assert response.status_code == 200
        data = response.json()
        assert "case_types" in data
        assert len(data["case_types"]) > 0

    def test_list_case_statuses(self):
        """GET /legal/types/case-statuses returns statuses."""
        response = client.get("/legal/types/case-statuses")
        assert response.status_code == 200
        data = response.json()
        assert "case_statuses" in data

    def test_list_materiality_assessments(self):
        """GET /legal/types/materiality-assessments returns assessments."""
        response = client.get("/legal/types/materiality-assessments")
        assert response.status_code == 200
        data = response.json()
        assert "materiality_assessments" in data
