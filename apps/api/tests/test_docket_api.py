"""
Tests for app.api.docket API endpoints (Band B #31)
--------------------------------------------------------------------------------
Tests the FastAPI endpoints for:
  - /docket/{ticker}/reconcile - Run reconciliation
  - /docket/{ticker}/findings - Get findings
  - /docket/{ticker}/cases - Get docket cases
  - /docket/{ticker}/disclosures - Get disclosures
  - /docket/{ticker}/summary - Get summary
  - /docket/finding/{id} - Get finding detail
  - /docket/types/* - Reference data
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# -- Reconciliation Tests -----------------------------------------------------

class TestReconciliation:
    """Tests for GET /docket/{ticker}/reconcile."""

    def test_reconcile_basic(self):
        response = client.get("/docket/AAPL/reconcile")
        assert response.status_code == 200

        data = response.json()
        assert "report" in data
        assert "cached" in data

    def test_reconcile_with_lookback(self):
        response = client.get("/docket/MSFT/reconcile?lookback_years=5")
        assert response.status_code == 200

        data = response.json()
        assert data["report"]["ticker"] == "MSFT"

    def test_reconcile_cached(self):
        # First call
        r1 = client.get("/docket/GOOGL/reconcile")
        assert r1.status_code == 200

        # Second call should be cached
        r2 = client.get("/docket/GOOGL/reconcile")
        assert r2.status_code == 200
        assert r2.json()["cached"] is True

    def test_reconcile_force_refresh(self):
        # Prime cache
        client.get("/docket/META/reconcile")

        # Force refresh
        response = client.get("/docket/META/reconcile?refresh=true")
        assert response.status_code == 200
        assert response.json()["cached"] is False

    def test_reconcile_report_structure(self):
        response = client.get("/docket/NVDA/reconcile")
        data = response.json()

        report = data["report"]
        assert "ticker" in report
        assert "company_name" in report
        assert "cik" in report
        assert "analysis_date" in report
        assert "docket_cases" in report
        assert "disclosed_litigation" in report
        assert "findings" in report
        assert "summary" in report
        assert "risk_score" in report


# -- Findings Tests -----------------------------------------------------------

class TestFindings:
    """Tests for GET /docket/{ticker}/findings."""

    def test_get_findings(self):
        response = client.get("/docket/AAPL/findings")
        assert response.status_code == 200

        data = response.json()
        assert "ticker" in data
        assert "findings" in data
        assert "total_findings" in data

    def test_findings_with_min_risk(self):
        response = client.get("/docket/AAPL/findings?min_risk=50")
        assert response.status_code == 200

        data = response.json()
        for finding in data["findings"]:
            assert finding["risk_score"] >= 50

    def test_findings_with_divergence_filter(self):
        response = client.get("/docket/AAPL/findings?divergence_type=missing_disclosure")
        assert response.status_code == 200

        data = response.json()
        for finding in data["findings"]:
            assert finding["divergence_type"] == "missing_disclosure"

    def test_findings_with_materiality_filter(self):
        response = client.get("/docket/AAPL/findings?materiality=high")
        assert response.status_code == 200

        data = response.json()
        for finding in data["findings"]:
            assert finding["materiality"] == "high"

    def test_findings_with_limit(self):
        response = client.get("/docket/AAPL/findings?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data["findings"]) <= 5

    def test_findings_structure(self):
        response = client.get("/docket/TSLA/findings")
        data = response.json()

        if data["findings"]:
            finding = data["findings"][0]
            assert "id" in finding
            assert "divergence_type" in finding
            assert "disclosure_status" in finding
            assert "materiality" in finding
            assert "title" in finding
            assert "description" in finding
            assert "risk_score" in finding
            assert "recommendations" in finding


# -- Cases Tests --------------------------------------------------------------

class TestCases:
    """Tests for GET /docket/{ticker}/cases."""

    def test_get_cases(self):
        response = client.get("/docket/AAPL/cases")
        assert response.status_code == 200

        data = response.json()
        assert "ticker" in data
        assert "cases" in data
        assert "total_cases" in data

    def test_cases_with_status_filter(self):
        response = client.get("/docket/AAPL/cases?status=open")
        assert response.status_code == 200

        data = response.json()
        for case in data["cases"]:
            assert case["status"].lower() == "open"

    def test_cases_with_limit(self):
        response = client.get("/docket/AAPL/cases?limit=10")
        assert response.status_code == 200

        data = response.json()
        assert len(data["cases"]) <= 10

    def test_cases_structure(self):
        response = client.get("/docket/AMZN/cases")
        data = response.json()

        if data["cases"]:
            case = data["cases"][0]
            assert "case_id" in case
            assert "case_name" in case
            assert "court" in case
            assert "docket_number" in case
            assert "filed_date" in case
            assert "status" in case


# -- Disclosures Tests --------------------------------------------------------

class TestDisclosures:
    """Tests for GET /docket/{ticker}/disclosures."""

    def test_get_disclosures(self):
        response = client.get("/docket/AAPL/disclosures")
        assert response.status_code == 200

        data = response.json()
        assert "ticker" in data
        assert "disclosures" in data
        assert "total_disclosures" in data

    def test_disclosures_with_filing_type(self):
        response = client.get("/docket/AAPL/disclosures?filing_type=10-K")
        assert response.status_code == 200

        data = response.json()
        for disclosure in data["disclosures"]:
            assert disclosure["filing_type"].upper() == "10-K"

    def test_disclosures_with_limit(self):
        response = client.get("/docket/AAPL/disclosures?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data["disclosures"]) <= 5

    def test_disclosures_structure(self):
        response = client.get("/docket/JPM/disclosures")
        data = response.json()

        if data["disclosures"]:
            disclosure = data["disclosures"][0]
            assert "filing_type" in disclosure
            assert "filing_date" in disclosure
            assert "accession_number" in disclosure
            assert "section" in disclosure


# -- Summary Tests ------------------------------------------------------------

class TestSummary:
    """Tests for GET /docket/{ticker}/summary."""

    def test_get_summary(self):
        response = client.get("/docket/AAPL/summary")
        assert response.status_code == 200

        data = response.json()
        assert "ticker" in data
        assert "company_name" in data
        assert "risk_score" in data
        assert "summary" in data

    def test_summary_structure(self):
        response = client.get("/docket/MSFT/summary")
        data = response.json()

        assert "cik" in data
        assert "analysis_date" in data
        assert "generated_at" in data
        assert data["risk_score"] >= 0
        assert data["risk_score"] <= 100


# -- Finding Detail Tests -----------------------------------------------------

class TestFindingDetail:
    """Tests for GET /docket/finding/{finding_id}."""

    def test_get_finding_detail(self):
        # First get findings to get an ID
        findings_resp = client.get("/docket/AAPL/findings")
        findings = findings_resp.json().get("findings", [])

        if findings:
            finding_id = findings[0]["id"]
            response = client.get(f"/docket/finding/{finding_id}")
            assert response.status_code == 200

            data = response.json()
            assert "ticker" in data
            assert "finding" in data
            assert data["finding"]["id"] == finding_id

    def test_get_nonexistent_finding(self):
        response = client.get("/docket/finding/NONEXISTENT_FINDING_999")
        assert response.status_code == 404


# -- Reference Data Tests -----------------------------------------------------

class TestReferenceData:
    """Tests for GET /docket/types/*."""

    def test_list_divergence_types(self):
        response = client.get("/docket/types/divergence")
        assert response.status_code == 200

        data = response.json()
        assert "divergence_types" in data
        assert len(data["divergence_types"]) > 0

        for dt in data["divergence_types"]:
            assert "value" in dt
            assert "description" in dt

    def test_list_materiality_levels(self):
        response = client.get("/docket/types/materiality")
        assert response.status_code == 200

        data = response.json()
        assert "materiality_levels" in data
        assert len(data["materiality_levels"]) > 0

        for ml in data["materiality_levels"]:
            assert "value" in ml
            assert "description" in ml

    def test_divergence_types_include_expected(self):
        response = client.get("/docket/types/divergence")
        data = response.json()

        values = [d["value"] for d in data["divergence_types"]]
        assert "missing_disclosure" in values
        assert "amount_mismatch" in values
        assert "timing_gap" in values

    def test_materiality_levels_include_expected(self):
        response = client.get("/docket/types/materiality")
        data = response.json()

        values = [m["value"] for m in data["materiality_levels"]]
        assert "critical" in values
        assert "high" in values
        assert "medium" in values
        assert "low" in values
        assert "unknown" in values


# -- Edge Cases ---------------------------------------------------------------

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_ticker_case_insensitive(self):
        r1 = client.get("/docket/aapl/reconcile")
        r2 = client.get("/docket/AAPL/reconcile")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["report"]["ticker"] == r2.json()["report"]["ticker"]

    def test_invalid_lookback_too_small(self):
        response = client.get("/docket/AAPL/reconcile?lookback_years=0")
        assert response.status_code == 422  # Validation error

    def test_invalid_lookback_too_large(self):
        response = client.get("/docket/AAPL/reconcile?lookback_years=20")
        assert response.status_code == 422  # Validation error

    def test_invalid_min_risk(self):
        response = client.get("/docket/AAPL/findings?min_risk=150")
        assert response.status_code == 422  # Validation error

    def test_invalid_divergence_type_ignored(self):
        # Invalid divergence type should be ignored, not error
        response = client.get("/docket/AAPL/findings?divergence_type=invalid_type")
        assert response.status_code == 200

    def test_invalid_materiality_ignored(self):
        # Invalid materiality should be ignored, not error
        response = client.get("/docket/AAPL/findings?materiality=invalid_level")
        assert response.status_code == 200
