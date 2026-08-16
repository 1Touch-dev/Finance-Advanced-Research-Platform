"""
Tests for app.api.ontology API endpoints (Band B #16)
────────────────────────────────────────────────────────────────────────────
Tests the FastAPI endpoints for:
  - /ontology/{ticker} - Get company ontology
  - /ontology/{ticker}/kpis - Get company KPIs
  - /ontology/{ticker}/entities - Get extracted entities
  - /ontology/reference/industries - Get industry templates
  - /ontology/reference/industries/{industry}/kpis - Get industry KPIs
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Reference Endpoints Tests (no SEC API calls) ─────────────────────────────

class TestIndustryTemplates:
    """Tests for industry reference endpoints."""

    def test_list_industries(self):
        response = client.get("/ontology/reference/industries")
        assert response.status_code == 200

        data = response.json()
        assert "industries" in data
        assert "total" in data
        assert "sic_mappings" in data
        assert data["total"] > 0

    def test_industries_have_kpi_counts(self):
        response = client.get("/ontology/reference/industries")
        data = response.json()

        for industry in data["industries"]:
            assert "industry" in industry
            assert "kpi_count" in industry
            assert "kpi_names" in industry
            assert industry["kpi_count"] >= 0

    def test_get_technology_kpis(self):
        response = client.get("/ontology/reference/industries/technology/kpis")
        assert response.status_code == 200

        data = response.json()
        assert data["industry"] == "technology"
        assert "kpis" in data
        assert len(data["kpis"]) > 0

    def test_get_semiconductor_kpis(self):
        response = client.get("/ontology/reference/industries/semiconductor/kpis")
        assert response.status_code == 200

        data = response.json()
        assert data["industry"] == "semiconductor"
        assert "kpis" in data

    def test_get_banking_kpis(self):
        response = client.get("/ontology/reference/industries/banking/kpis")
        assert response.status_code == 200

        data = response.json()
        assert data["industry"] == "banking"

    def test_get_retail_kpis(self):
        response = client.get("/ontology/reference/industries/retail/kpis")
        assert response.status_code == 200

        data = response.json()
        assert data["industry"] == "retail"

    def test_industry_kpis_have_required_fields(self):
        response = client.get("/ontology/reference/industries/technology/kpis")
        data = response.json()

        for kpi in data["kpis"]:
            assert "id" in kpi
            assert "name" in kpi
            assert "description" in kpi
            assert "metric_type" in kpi
            assert "unit" in kpi
            assert "higher_is_better" in kpi

    def test_invalid_industry_returns_404(self):
        response = client.get("/ontology/reference/industries/nonexistent_industry/kpis")
        assert response.status_code == 404

    def test_industry_case_insensitive(self):
        response = client.get("/ontology/reference/industries/TECHNOLOGY/kpis")
        assert response.status_code == 200

        data = response.json()
        assert data["industry"] == "technology"


# ── KPI Template Structure Tests ─────────────────────────────────────────────

class TestKPITemplateStructure:
    """Tests for KPI template content."""

    def test_technology_includes_arr(self):
        response = client.get("/ontology/reference/industries/technology/kpis")
        data = response.json()

        kpi_ids = [k["id"] for k in data["kpis"]]
        assert "arr" in kpi_ids

    def test_technology_includes_nrr(self):
        response = client.get("/ontology/reference/industries/technology/kpis")
        data = response.json()

        kpi_ids = [k["id"] for k in data["kpis"]]
        assert "nrr" in kpi_ids

    def test_semiconductor_includes_data_center(self):
        response = client.get("/ontology/reference/industries/semiconductor/kpis")
        data = response.json()

        kpi_ids = [k["id"] for k in data["kpis"]]
        assert "data_center_revenue" in kpi_ids

    def test_banking_includes_nim(self):
        response = client.get("/ontology/reference/industries/banking/kpis")
        data = response.json()

        kpi_ids = [k["id"] for k in data["kpis"]]
        assert "nim" in kpi_ids

    def test_retail_includes_same_store_sales(self):
        response = client.get("/ontology/reference/industries/retail/kpis")
        data = response.json()

        kpi_ids = [k["id"] for k in data["kpis"]]
        assert "same_store_sales" in kpi_ids


# ── SIC Mappings Tests ───────────────────────────────────────────────────────

class TestSICMappings:
    """Tests for SIC code to industry mappings."""

    def test_sic_mappings_present(self):
        response = client.get("/ontology/reference/industries")
        data = response.json()

        assert "sic_mappings" in data
        assert isinstance(data["sic_mappings"], dict)

    def test_sic_3674_is_semiconductor(self):
        response = client.get("/ontology/reference/industries")
        data = response.json()

        assert data["sic_mappings"].get("3674") == "semiconductor"

    def test_sic_7370_is_technology(self):
        response = client.get("/ontology/reference/industries")
        data = response.json()

        assert data["sic_mappings"].get("7370") == "technology"

    def test_sic_6021_is_banking(self):
        response = client.get("/ontology/reference/industries")
        data = response.json()

        assert data["sic_mappings"].get("6021") == "banking"
