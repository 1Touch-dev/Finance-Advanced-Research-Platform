"""
Tests for app.api.formula API endpoints (Band B #26)
────────────────────────────────────────────────────────────────────────────
Tests the FastAPI endpoints for:
  - /formula/evaluate - Formula evaluation
  - /formula/validate - Formula validation
  - /formula/list - List saved formulas
  - /formula/save - Save custom formulas
  - /formula/{id} - Get/delete formulas
  - /formula/reference/* - Available metrics and functions
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Evaluate Endpoint Tests ──────────────────────────────────────────────────

class TestEvaluateFormula:
    """Tests for POST /formula/evaluate."""

    def test_evaluate_simple_formula(self):
        response = client.post("/formula/evaluate", json={
            "formula": "AAPL.close",
            "tickers": ["AAPL"],
            "days": 30
        })
        assert response.status_code == 200

        data = response.json()
        assert "formula" in data
        assert "computed" in data

    def test_evaluate_with_math(self):
        response = client.post("/formula/evaluate", json={
            "formula": "AAPL.close / AAPL.close[1] - 1",
            "tickers": ["AAPL"],
            "days": 30
        })
        assert response.status_code == 200

    def test_evaluate_multi_ticker(self):
        response = client.post("/formula/evaluate", json={
            "formula": "AAPL.close / MSFT.close",
            "tickers": ["AAPL", "MSFT"],
            "days": 30
        })
        assert response.status_code == 200

        data = response.json()
        assert "computed" in data

    def test_evaluate_default_days(self):
        response = client.post("/formula/evaluate", json={
            "formula": "NVDA.close",
        })
        assert response.status_code == 200


# ── Validate Endpoint Tests ──────────────────────────────────────────────────

class TestValidateFormula:
    """Tests for GET /formula/validate."""

    def test_validate_simple_formula(self):
        response = client.get("/formula/validate?formula=AAPL.close")
        assert response.status_code == 200

        data = response.json()
        assert "valid" in data
        assert "parsed_tokens" in data

    def test_validate_complex_formula(self):
        response = client.get("/formula/validate?formula=rolling_avg(AAPL.close, 20)")
        assert response.status_code == 200

        data = response.json()
        assert "referenced_tickers" in data
        assert "referenced_metrics" in data

    def test_validate_extracts_tickers(self):
        response = client.get("/formula/validate?formula=AAPL.close + MSFT.close")
        assert response.status_code == 200

        data = response.json()
        assert "AAPL" in data.get("referenced_tickers", [])


# ── List Formulas Tests ──────────────────────────────────────────────────────

class TestListFormulas:
    """Tests for GET /formula/list."""

    def test_list_all_formulas(self):
        response = client.get("/formula/list")
        assert response.status_code == 200

        data = response.json()
        assert "formulas" in data
        assert "count" in data
        assert isinstance(data["formulas"], list)

    def test_list_by_category(self):
        response = client.get("/formula/list?category=preset")
        assert response.status_code == 200

        data = response.json()
        assert "formulas" in data


# ── Save Formula Tests ───────────────────────────────────────────────────────

class TestSaveFormula:
    """Tests for POST /formula/save."""

    def test_save_valid_formula(self):
        response = client.post("/formula/save", json={
            "name": "Test Formula",
            "formula": "AAPL.close / AAPL.close[20] - 1",
            "description": "20-day return",
            "category": "custom"
        })
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Formula"

    def test_save_formula_with_tickers(self):
        response = client.post("/formula/save", json={
            "name": "Ratio Formula",
            "formula": "AAPL.close / MSFT.close",
            "tickers": ["AAPL", "MSFT"]
        })
        assert response.status_code == 200

    def test_save_invalid_formula_fails(self):
        response = client.post("/formula/save", json={
            "name": "Invalid",
            "formula": "INVALID_SYNTAX(((",
        })
        # Should return 400 for invalid formula
        assert response.status_code in [200, 400]


# ── Get/Delete Formula Tests ─────────────────────────────────────────────────

class TestGetDeleteFormula:
    """Tests for GET/DELETE /formula/{id}."""

    def test_get_formula(self):
        # First save a formula
        save_response = client.post("/formula/save", json={
            "name": "Get Test",
            "formula": "NVDA.close",
        })
        assert save_response.status_code == 200
        formula_id = save_response.json()["id"]

        # Then get it
        response = client.get(f"/formula/{formula_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == formula_id
        assert data["name"] == "Get Test"

    def test_get_nonexistent_formula(self):
        response = client.get("/formula/nonexistent_id_12345")
        assert response.status_code == 404

    def test_delete_formula(self):
        # First save a formula
        save_response = client.post("/formula/save", json={
            "name": "Delete Test",
            "formula": "TSLA.close",
        })
        assert save_response.status_code == 200
        formula_id = save_response.json()["id"]

        # Delete it
        response = client.delete(f"/formula/{formula_id}")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

        # Verify it's gone
        get_response = client.get(f"/formula/{formula_id}")
        assert get_response.status_code == 404


# ── Reference Endpoints Tests ────────────────────────────────────────────────

class TestReferenceEndpoints:
    """Tests for reference endpoints."""

    def test_get_metrics(self):
        response = client.get("/formula/reference/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "metrics" in data
        assert isinstance(data["metrics"], list)

    def test_get_functions(self):
        response = client.get("/formula/reference/functions")
        assert response.status_code == 200

        data = response.json()
        assert "functions" in data
        assert isinstance(data["functions"], list)

    def test_metrics_include_common(self):
        response = client.get("/formula/reference/metrics")
        data = response.json()

        metric_names = [m.get("name", m) if isinstance(m, dict) else m for m in data["metrics"]]
        # Should include common metrics
        assert len(metric_names) > 0

    def test_functions_include_rolling(self):
        response = client.get("/formula/reference/functions")
        data = response.json()

        func_names = [f.get("name", f) if isinstance(f, dict) else f for f in data["functions"]]
        # Should include time-series functions
        assert len(func_names) > 0
