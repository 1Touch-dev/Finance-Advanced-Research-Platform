"""
Integration tests for F-05 Congress.gov legislation API endpoints.

Complements tests/connectors/test_congress_gov.py (unit tests on the connector
functions) by verifying the FastAPI routes wire up correctly end-to-end.
Congress.gov HTTP calls are mocked at the connector's `requests.get` level so
these tests run offline and deterministically in CI.
"""
import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_integration.db")
os.environ.setdefault("ENV", "test")

from app.main import app  # noqa: E402
from app.connectors import gov_trading_connector as gtc  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_congress_cache():
    gtc._cache.clear()
    gtc._cache_ts.clear()
    yield
    gtc._cache.clear()
    gtc._cache_ts.clear()


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


class TestLegislationSearchEndpoint:
    def test_search_endpoint_returns_200(self):
        sample = {"bills": [{"congress": 118, "type": "hr", "number": "1", "title": "Banking bill"}]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            r = client.get("/market/gov-trading/legislation/search?query=banking")
        assert r.status_code == 200
        body = r.json()
        assert body["query"] == "banking"
        assert len(body["bills"]) == 1

    def test_search_endpoint_missing_query_returns_422(self):
        r = client.get("/market/gov-trading/legislation/search")
        assert r.status_code == 422  # query is required


class TestBillDetailEndpoint:
    def test_bill_detail_returns_200(self):
        sample = {"bill": {"congress": 118, "type": "hr", "number": "1", "title": "Test Bill"}}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            r = client.get("/market/gov-trading/legislation/bill/118/hr/1")
        assert r.status_code == 200
        assert r.json()["title"] == "Test Bill"

    def test_bill_detail_not_found_returns_error_payload(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({})
            r = client.get("/market/gov-trading/legislation/bill/118/hr/999999")
        assert r.status_code == 200  # graceful degrade, not 500
        assert "error" in r.json()


class TestRecentLawsEndpoint:
    def test_recent_laws_returns_200(self):
        sample = {"bills": [{"congress": 118, "type": "hr", "number": "1", "laws": [{"number": "118-1"}]}]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            r = client.get("/market/gov-trading/legislation/laws/118")
        assert r.status_code == 200
        assert r.json()["congress"] == 118
        assert len(r.json()["laws"]) == 1


class TestCommitteeBillsEndpoint:
    def test_committee_bills_returns_200(self):
        sample = {"committee-bills": {"bills": []}}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            r = client.get("/market/gov-trading/legislation/committee/senate/ssba")
        assert r.status_code == 200
        assert r.json()["committee"] == "ssba"


class TestCRSReportsEndpoint:
    def test_crs_reports_returns_200(self):
        sample = {"CRSReports": [{"id": "R1", "title": "Report 1"}]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            r = client.get("/market/gov-trading/legislation/crs-reports")
        assert r.status_code == 200
        assert len(r.json()["reports"]) == 1


class TestPoliticianVotesEndpoint:
    def test_votes_for_known_politician(self):
        members_sample = {"members": [{"directOrderName": "Nancy Pelosi", "bioguideId": "P000197", "state": "CA"}]}
        sponsored = {"sponsoredLegislation": [{"type": "hr", "number": "1", "title": "Bill A"}]}
        cosponsored = {"cosponsoredLegislation": []}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.side_effect = [_mock_response(members_sample), _mock_response(sponsored), _mock_response(cosponsored)]
            r = client.get("/market/gov-trading/politician/nancy_pelosi/votes")
        assert r.status_code == 200
        assert r.json()["politician"] == "Nancy Pelosi"

    def test_votes_for_unknown_politician_returns_error_payload(self):
        r = client.get("/market/gov-trading/politician/totally_unknown/votes")
        assert r.status_code == 200
        assert "error" in r.json()


class TestPoliticianProfileStillWorks:
    """Regression: existing endpoint must keep working after the DEMO_KEY -> real key fix."""

    def test_politician_profile_endpoint_200(self):
        members_sample = {"members": [{"directOrderName": "Nancy Pelosi", "bioguideId": "P000197", "state": "CA"}]}
        legislation_sample = {"sponsoredLegislation": []}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.side_effect = [_mock_response(members_sample), _mock_response(legislation_sample)]
            r = client.get("/market/gov-trading/politician/nancy_pelosi")
        assert r.status_code == 200
        assert "politician" in r.json()
