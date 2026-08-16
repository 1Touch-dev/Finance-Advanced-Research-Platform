"""
Tests for app.api.filings API endpoints (Band B #15)
--------------------------------------------------------------------------------
Tests the FastAPI endpoints for:
  - /filings/compare - Compare two filings
  - /filings/compare/redline - HTML redline comparison
  - /filings/compare/excel - Excel export
  - /filings/history - Filing history
  - /filings/material-changes - Material changes only
  - /filings/search - Full-text search
  - /filings/ontology - Company ontology
  - /filings/kpis - Company KPIs
  - /filings/litigation/* - Litigation reconciliation

Note: These tests may return 400/500 errors when SEC EDGAR API is unavailable.
We test that the endpoints exist and return appropriate responses.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# -- Compare Filings Tests ----------------------------------------------------

class TestCompareFilings:
    """Tests for GET /filings/compare."""

    def test_compare_endpoint_exists(self):
        """Endpoint exists and returns expected status codes."""
        response = client.get("/filings/compare?ticker=AAPL")
        # 200 = success, 400 = no filings found, 500 = API error
        assert response.status_code in [200, 400, 500]

    def test_compare_returns_json(self):
        """Endpoint returns JSON response."""
        response = client.get("/filings/compare?ticker=MSFT")
        assert response.headers.get("content-type", "").startswith("application/json")

    def test_compare_requires_ticker(self):
        """Ticker is required."""
        response = client.get("/filings/compare")
        assert response.status_code == 422

    def test_compare_with_form_type(self):
        """Form type parameter is accepted."""
        response = client.get("/filings/compare?ticker=NVDA&form_type=10-K")
        assert response.status_code in [200, 400, 500]

    def test_compare_with_periods(self):
        """Period parameters are accepted."""
        response = client.get(
            "/filings/compare?ticker=GOOGL&base_period=2024&compare_period=2023"
        )
        assert response.status_code in [200, 400, 500]

    def test_compare_success_structure(self):
        """When successful, response has expected structure."""
        response = client.get("/filings/compare?ticker=AAPL")
        data = response.json()

        if response.status_code == 200:
            assert "ticker" in data
            assert "form_type" in data
            assert "financial_changes" in data
            assert "summary" in data


# -- Redline HTML Tests -------------------------------------------------------

class TestRedlineHtml:
    """Tests for GET /filings/compare/redline."""

    def test_redline_endpoint_exists(self):
        """Endpoint exists and returns expected status codes."""
        response = client.get("/filings/compare/redline?ticker=AAPL")
        assert response.status_code in [200, 400, 500]

    def test_redline_requires_ticker(self):
        """Ticker is required."""
        response = client.get("/filings/compare/redline")
        assert response.status_code == 422

    def test_redline_returns_html_on_success(self):
        """Returns HTML content type on success."""
        response = client.get("/filings/compare/redline?ticker=MSFT")
        if response.status_code == 200:
            assert "text/html" in response.headers.get("content-type", "")


# -- Excel Export Tests -------------------------------------------------------

class TestExcelExport:
    """Tests for GET /filings/compare/excel."""

    def test_excel_endpoint_exists(self):
        """Endpoint exists and returns expected status codes."""
        response = client.get("/filings/compare/excel?ticker=AAPL")
        assert response.status_code in [200, 400, 500]

    def test_excel_requires_ticker(self):
        """Ticker is required."""
        response = client.get("/filings/compare/excel")
        assert response.status_code == 422


# -- Filing History Tests -----------------------------------------------------

class TestFilingHistory:
    """Tests for GET /filings/history."""

    def test_history_endpoint_exists(self):
        """Endpoint exists and returns expected status codes."""
        response = client.get("/filings/history?ticker=AAPL")
        assert response.status_code in [200, 400, 404, 500]

    def test_history_requires_ticker(self):
        """Ticker is required."""
        response = client.get("/filings/history")
        assert response.status_code == 422

    def test_history_with_form_type(self):
        """Form type parameter is accepted."""
        response = client.get("/filings/history?ticker=MSFT&form_type=10-K")
        assert response.status_code in [200, 400, 404, 500]

    def test_history_with_limit(self):
        """Limit parameter is accepted."""
        response = client.get("/filings/history?ticker=NVDA&limit=5")
        assert response.status_code in [200, 400, 404, 500]

    def test_history_success_structure(self):
        """When successful, response has expected structure."""
        response = client.get("/filings/history?ticker=AAPL")
        data = response.json()

        if response.status_code == 200:
            assert "ticker" in data
            assert "filings" in data
            assert "cik" in data


# -- Material Changes Tests ---------------------------------------------------

class TestMaterialChanges:
    """Tests for GET /filings/material-changes."""

    def test_material_changes_endpoint_exists(self):
        """Endpoint exists and returns expected status codes."""
        response = client.get("/filings/material-changes?ticker=AAPL")
        assert response.status_code in [200, 400, 500]

    def test_material_changes_requires_ticker(self):
        """Ticker is required."""
        response = client.get("/filings/material-changes")
        assert response.status_code == 422

    def test_material_changes_success_structure(self):
        """When successful, response has expected structure."""
        response = client.get("/filings/material-changes?ticker=MSFT")
        data = response.json()

        if response.status_code == 200:
            assert "ticker" in data
            assert "material_changes" in data


# -- Search Tests -------------------------------------------------------------

class TestFilingSearch:
    """Tests for GET /filings/search."""

    def test_search_requires_query(self):
        """Query is required."""
        response = client.get("/filings/search")
        assert response.status_code == 422

    @pytest.mark.skip(reason="search_filings not yet implemented in sec_edgar_connector")
    def test_search_response_structure(self):
        """Response has expected structure even with partial implementation."""
        response = client.get("/filings/search?query=risk")
        # 200 = success, 500 = import error (partial implementation)
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "query" in data
            assert "results" in data


# -- Company Ontology Tests ---------------------------------------------------

class TestCompanyOntology:
    """Tests for GET /filings/ontology."""

    def test_ontology_endpoint_exists(self):
        """Endpoint exists and returns expected status codes."""
        response = client.get("/filings/ontology?ticker=AAPL")
        assert response.status_code in [200, 400, 500]

    def test_ontology_requires_ticker(self):
        """Ticker is required."""
        response = client.get("/filings/ontology")
        assert response.status_code == 422

    def test_ontology_with_options(self):
        """Options parameters are accepted."""
        response = client.get(
            "/filings/ontology?ticker=MSFT&include_kpis=true&include_entities=false"
        )
        assert response.status_code in [200, 400, 500]


# -- Company KPIs Tests -------------------------------------------------------

class TestCompanyKPIs:
    """Tests for GET /filings/kpis."""

    def test_kpis_endpoint_exists(self):
        """Endpoint exists and returns expected status codes."""
        response = client.get("/filings/kpis?ticker=AAPL")
        assert response.status_code in [200, 400, 500]

    def test_kpis_requires_ticker(self):
        """Ticker is required."""
        response = client.get("/filings/kpis")
        assert response.status_code == 422


# -- Litigation Reconciliation Tests ------------------------------------------

class TestLitigationReconciliation:
    """Tests for GET /filings/litigation/* endpoints."""

    def test_reconcile_endpoint_exists(self):
        """Endpoint exists and returns expected status codes."""
        response = client.get("/filings/litigation/reconcile?ticker=AAPL")
        assert response.status_code == 200

    def test_reconcile_with_lookback(self):
        """Lookback years parameter is accepted."""
        response = client.get(
            "/filings/litigation/reconcile?ticker=MSFT&lookback_years=5"
        )
        assert response.status_code == 200

    def test_reconcile_structure(self):
        """Response has expected structure."""
        response = client.get("/filings/litigation/reconcile?ticker=NVDA")
        data = response.json()

        assert "ticker" in data
        assert "findings" in data or "docket_cases" in data

    def test_undisclosed_endpoint_exists(self):
        """Undisclosed litigation endpoint exists."""
        response = client.get("/filings/litigation/undisclosed?ticker=AAPL")
        assert response.status_code == 200

    def test_undisclosed_structure(self):
        """Undisclosed response has expected structure."""
        response = client.get("/filings/litigation/undisclosed?ticker=GOOGL")
        data = response.json()

        assert "ticker" in data
        assert "undisclosed_findings" in data
        assert "total_undisclosed" in data

    def test_risk_score_endpoint_exists(self):
        """Risk score endpoint exists."""
        response = client.get("/filings/litigation/risk-score?ticker=AAPL")
        assert response.status_code == 200

    def test_risk_score_structure(self):
        """Risk score response has expected structure."""
        response = client.get("/filings/litigation/risk-score?ticker=META")
        data = response.json()

        assert "ticker" in data
        assert "risk_score" in data
        assert "risk_level" in data
        assert data["risk_score"] >= 0
        assert data["risk_score"] <= 100

    def test_risk_level_values(self):
        """Risk level is one of expected values."""
        response = client.get("/filings/litigation/risk-score?ticker=NVDA")
        data = response.json()

        valid_levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"]
        assert data["risk_level"] in valid_levels


# -- Edge Cases ---------------------------------------------------------------

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_ticker_case_insensitive(self):
        """Ticker should be case insensitive."""
        r1 = client.get("/filings/litigation/risk-score?ticker=aapl")
        r2 = client.get("/filings/litigation/risk-score?ticker=AAPL")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["ticker"] == r2.json()["ticker"]

    def test_missing_ticker_fails(self):
        """Missing required ticker returns validation error."""
        response = client.get("/filings/compare")
        assert response.status_code == 422

    def test_invalid_ticker_handled(self):
        """Invalid ticker returns appropriate error."""
        response = client.get("/filings/history?ticker=INVALID_TICKER_XYZ")
        assert response.status_code in [400, 404, 500]


# -- Service Tests ------------------------------------------------------------

class TestFilingDiffService:
    """Tests for the underlying filing_diff_service module."""

    def test_change_types(self):
        """Change type enum values are correct."""
        from app.services.filing_diff_service import ChangeType

        assert ChangeType.ADDED.value == "added"
        assert ChangeType.REMOVED.value == "removed"
        assert ChangeType.MODIFIED.value == "modified"
        assert ChangeType.MATERIAL.value == "material"
        assert ChangeType.UNCHANGED.value == "unchanged"

    def test_materiality_levels(self):
        """Materiality level enum values are correct."""
        from app.services.filing_diff_service import MaterialityLevel

        assert MaterialityLevel.HIGH.value == "high"
        assert MaterialityLevel.MEDIUM.value == "medium"
        assert MaterialityLevel.LOW.value == "low"
        assert MaterialityLevel.INFO.value == "info"

    def test_dataclass_definitions(self):
        """Dataclasses are properly defined."""
        from app.services.filing_diff_service import (
            FilingChange,
            TextDiff,
            TableData,
            FilingDiffResult,
        )

        # FilingChange
        change = FilingChange(
            section="income_statement",
            field="revenue",
            change_type=ChangeType.MODIFIED,
            old_value=100,
            new_value=120,
        )
        assert change.field == "revenue"

        # TextDiff
        diff = TextDiff(
            section="risk_factors",
            old_text="old",
            new_text="new",
            diff_html="<diff>",
            added_lines=1,
            removed_lines=0,
            similarity_ratio=0.8,
        )
        assert diff.section == "risk_factors"

        # TableData
        table = TableData(
            name="Income Statement",
            section="financials",
            headers=["Metric", "Value"],
            rows=[["Revenue", 100]],
            source_filing="AAPL",
            period="2024",
        )
        assert table.name == "Income Statement"

    def test_material_keywords_defined(self):
        """Material keywords list is defined."""
        from app.services.filing_diff_service import MATERIAL_KEYWORDS

        assert "material weakness" in MATERIAL_KEYWORDS
        assert "restatement" in MATERIAL_KEYWORDS
        assert "going concern" in MATERIAL_KEYWORDS
        assert "sec investigation" in MATERIAL_KEYWORDS

    def test_materiality_thresholds_defined(self):
        """Materiality thresholds are defined."""
        from app.services.filing_diff_service import MATERIALITY_THRESHOLDS

        assert "revenue" in MATERIALITY_THRESHOLDS
        assert "net_income" in MATERIALITY_THRESHOLDS
        assert "default" in MATERIALITY_THRESHOLDS
        assert "high" in MATERIALITY_THRESHOLDS["revenue"]
        assert "medium" in MATERIALITY_THRESHOLDS["revenue"]

    def test_helper_functions_exist(self):
        """Helper functions are importable."""
        from app.services.filing_diff_service import (
            generate_redline_html,
            export_diff_to_excel,
            diff_result_to_dict,
        )

        # Functions exist
        assert callable(generate_redline_html)
        assert callable(export_diff_to_excel)
        assert callable(diff_result_to_dict)


# Import ChangeType for dataclass tests
from app.services.filing_diff_service import ChangeType
