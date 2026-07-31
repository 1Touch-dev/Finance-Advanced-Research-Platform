"""
Unit tests for Congress.gov legislation connector functions (F-05).

Gap 2 fix (lead review): this file did not exist in the original feature
proposal. Addresses:
  - DEMO_KEY -> CONGRESS_API_KEY replacement (Phase 1)
  - New Phase 2 functions: search_bills, get_bill_details, get_bill_text,
    get_bill_cosponsors, get_recent_laws, get_committee_bills,
    get_crs_reports, get_bioguide_id, get_member_votes
  - 20-min TTL cache behavior (Gap 1)
  - Graceful error handling (network errors, malformed responses, 429s)

All Congress.gov HTTP calls are mocked — no live network access required,
so these tests are fast and deterministic in CI.
"""
import os
import sys
import time
from unittest.mock import patch, MagicMock

import pytest

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_integration.db")
os.environ.setdefault("ENV", "test")

from app.connectors import gov_trading_connector as gtc  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_congress_cache():
    """Ensure each test starts with a clean module-level cache."""
    gtc._cache.clear()
    gtc._cache_ts.clear()
    yield
    gtc._cache.clear()
    gtc._cache_ts.clear()


def _mock_response(json_data, status_code=200, raise_exc=None):
    """Build a mock requests.Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    if raise_exc:
        resp.raise_for_status.side_effect = raise_exc
    else:
        resp.raise_for_status.return_value = None
    return resp


# ─── Gap 3/Phase 1: API key usage ────────────────────────────────────────────

class TestCongressAPIKeyUsage:
    def test_uses_real_api_key_from_env(self, monkeypatch):
        """CONGRESS_API_KEY from env must be used, not the hardcoded DEMO_KEY."""
        monkeypatch.setenv("CONGRESS_API_KEY", "real_test_key_12345")
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"bills": []})
            gtc.search_bills("banking")
            called_params = mock_get.call_args.kwargs["params"]
            assert called_params["api_key"] == "real_test_key_12345"
            assert called_params["api_key"] != "DEMO_KEY"

    def test_falls_back_to_demo_key_if_env_missing(self, monkeypatch):
        """If CONGRESS_API_KEY is unset, fall back to public DEMO_KEY (not crash)."""
        monkeypatch.delenv("CONGRESS_API_KEY", raising=False)
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"bills": []})
            gtc.search_bills("banking")
            called_params = mock_get.call_args.kwargs["params"]
            assert called_params["api_key"] == "DEMO_KEY"

    def test_politician_profile_uses_real_key_not_demo(self, monkeypatch):
        """get_politician_profile must not hardcode DEMO_KEY (Phase 1 regression test)."""
        monkeypatch.setenv("CONGRESS_API_KEY", "real_test_key_12345")
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"members": []})
            with patch("app.connectors.gov_trading_connector.get_trades_by_member", return_value=[]):
                gtc.get_politician_profile("nancy_pelosi")
            called_params = mock_get.call_args.kwargs["params"]
            assert called_params["api_key"] == "real_test_key_12345"


# ─── Gap 4: os import check ───────────────────────────────────────────────────

class TestOSImportPrerequisite:
    def test_os_module_available_in_connector(self):
        """Gap 4: verify `os` is importable/used in the connector module (no NameError)."""
        assert hasattr(gtc, "os")
        assert gtc.os.environ.get("__DOES_NOT_EXIST__", "fallback_ok") == "fallback_ok"

    def test_get_congress_api_key_does_not_raise(self, monkeypatch):
        """_get_congress_api_key() must not raise NameError for missing `os` import."""
        monkeypatch.delenv("CONGRESS_API_KEY", raising=False)
        key = gtc._get_congress_api_key()
        assert key == "DEMO_KEY"


# ─── search_bills() ───────────────────────────────────────────────────────────

class TestSearchBills:
    def test_returns_valid_data(self):
        sample = {"bills": [
            {"congress": 118, "type": "hr", "number": "1234", "title": "A bill on banking reform",
             "updateDate": "2026-01-01", "latestAction": {"text": "Referred to committee", "actionDate": "2026-01-02"}}
        ]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            results = gtc.search_bills("banking reform")
        assert len(results) == 1
        assert results[0]["title"] == "A bill on banking reform"
        assert results[0]["type"] == "hr"

    def test_empty_query_returns_empty_list_no_api_call(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            results = gtc.search_bills("")
            assert results == []
            mock_get.assert_not_called()

    def test_whitespace_query_returns_empty_list(self):
        results = gtc.search_bills("   ")
        assert results == []

    def test_no_results_returns_empty_list(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"bills": []})
            results = gtc.search_bills("xyznonexistentbill12345")
        assert results == []

    def test_limit_is_clamped_between_1_and_100(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"bills": []})
            gtc.search_bills("banking", limit=500)
            assert mock_get.call_args.kwargs["params"]["limit"] == 100

            gtc._cache.clear()
            gtc._cache_ts.clear()
            gtc.search_bills("crypto", limit=0)
            assert mock_get.call_args.kwargs["params"]["limit"] == 1

    def test_network_error_returns_empty_list_not_crash(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.side_effect = ConnectionError("network down")
            results = gtc.search_bills("banking")
        assert results == []

    def test_rate_limit_429_handled_gracefully(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            import requests as real_requests
            mock_get.return_value = _mock_response(
                {}, status_code=429, raise_exc=real_requests.HTTPError("429 Too Many Requests")
            )
            results = gtc.search_bills("banking")
        assert results == []


# ─── Cache behavior (Gap 1) ───────────────────────────────────────────────────

class TestCongressCache:
    def test_second_call_within_ttl_uses_cache_not_api(self):
        sample = {"bills": [{"congress": 118, "type": "hr", "number": "1", "title": "Cached bill"}]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            first = gtc.search_bills("banking")
            second = gtc.search_bills("banking")
        assert first == second
        assert mock_get.call_count == 1  # Second call hit cache, no new HTTP request

    def test_cache_expires_after_ttl(self, monkeypatch):
        sample = {"bills": [{"congress": 118, "type": "hr", "number": "1", "title": "Bill"}]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            gtc.search_bills("banking")
            assert mock_get.call_count == 1

            # Simulate 20+ minutes passing by rewinding the cached timestamp
            for key in list(gtc._cache_ts.keys()):
                gtc._cache_ts[key] = time.time() - (gtc.CONGRESS_CACHE_TTL + 1)

            gtc.search_bills("banking")
        assert mock_get.call_count == 2  # Cache expired -> fresh fetch

    def test_cache_ttl_is_20_minutes(self):
        """Gap 1: verify the documented 20-minute (1200s) TTL constant."""
        assert gtc.CONGRESS_CACHE_TTL == 1200

    def test_fetch_error_falls_back_to_stale_cache(self):
        """If a later request errors, return the last-known-good cached value instead of []."""
        sample = {"bills": [{"congress": 118, "type": "hr", "number": "1", "title": "Bill"}]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            gtc.search_bills("banking")

            # Expire cache, then simulate a network failure on refetch
            for key in list(gtc._cache_ts.keys()):
                gtc._cache_ts[key] = time.time() - (gtc.CONGRESS_CACHE_TTL + 1)
            mock_get.side_effect = ConnectionError("down")

            results = gtc.search_bills("banking")
        assert len(results) == 1  # stale cache returned instead of crashing/empty


# ─── get_bill_details() ───────────────────────────────────────────────────────

class TestBillDetails:
    def test_valid_bill_returns_details(self):
        sample = {"bill": {
            "congress": 118, "type": "hr", "number": "1", "title": "Test Bill",
            "introducedDate": "2026-01-01", "policyArea": {"name": "Finance"},
            "latestAction": {"text": "Passed House", "actionDate": "2026-02-01"},
            "sponsors": [{"fullName": "Rep. Example", "party": "D", "state": "CA"}],
            "cosponsors": {"count": 5}, "summaries": {"count": 1},
        }}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            bill = gtc.get_bill_details(118, "hr", 1)
        assert bill is not None
        assert bill["title"] == "Test Bill"
        assert bill["cosponsors_count"] == 5
        assert bill["sponsors"][0]["name"] == "Rep. Example"

    def test_invalid_bill_returns_none(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({})
            bill = gtc.get_bill_details(118, "hr", 999999)
        assert bill is None

    def test_network_error_returns_none(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.side_effect = ConnectionError("down")
            bill = gtc.get_bill_details(118, "hr", 1)
        assert bill is None


# ─── get_recent_laws() ─────────────────────────────────────────────────────────

class TestRecentLaws:
    def test_returns_law_list(self):
        sample = {"bills": [
            {"congress": 118, "type": "hr", "number": "1", "title": "Enacted Law",
             "laws": [{"number": "118-1", "type": "Public Law"}]}
        ]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            laws = gtc.get_recent_laws(118)
        assert len(laws) == 1
        assert laws[0]["law_number"] == "118-1"

    def test_empty_response_returns_empty_list(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"bills": []})
            laws = gtc.get_recent_laws(999)
        assert laws == []


# ─── get_committee_bills() ─────────────────────────────────────────────────────

class TestCommitteeBills:
    def test_valid_committee_returns_bills(self):
        sample = {"committee-bills": {"bills": [
            {"congress": 118, "type": "s", "number": "100", "actionDate": "2026-01-01", "relationshipType": "Primary"}
        ]}}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            bills = gtc.get_committee_bills("senate", "ssba")
        assert len(bills) == 1
        assert bills[0]["relationship_type"] == "Primary"

    def test_invalid_committee_returns_empty_list(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({})
            bills = gtc.get_committee_bills("senate", "invalid_code")
        assert bills == []


# ─── get_crs_reports() ─────────────────────────────────────────────────────────

class TestCRSReports:
    def test_returns_reports(self):
        sample = {"CRSReports": [
            {"id": "R12345", "title": "Policy Analysis", "type": "Report",
             "status": "Active", "publishDate": "2026-01-01", "url": "https://example.com"}
        ]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            reports = gtc.get_crs_reports(limit=5)
        assert len(reports) == 1
        assert reports[0]["id"] == "R12345"

    def test_respects_limit(self):
        sample = {"CRSReports": [{"id": f"R{i}", "title": f"Report {i}"} for i in range(10)]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            reports = gtc.get_crs_reports(limit=3)
        assert len(reports) == 3


# ─── get_bioguide_id() + get_member_votes() ───────────────────────────────────

class TestMemberLookupAndVotes:
    def test_get_bioguide_id_finds_match(self):
        sample = {"members": [
            {"directOrderName": "Nancy Pelosi", "bioguideId": "P000197", "state": "CA"}
        ]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response(sample)
            bioguide_id = gtc.get_bioguide_id("Nancy Pelosi")
        assert bioguide_id == "P000197"

    def test_get_bioguide_id_no_match_returns_none(self):
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.return_value = _mock_response({"members": []})
            bioguide_id = gtc.get_bioguide_id("Nonexistent Person")
        assert bioguide_id is None

    def test_get_member_votes_combines_sponsor_and_cosponsor(self):
        sponsored = {"sponsoredLegislation": [
            {"type": "hr", "number": "1", "title": "Sponsored Bill", "introducedDate": "2026-01-01",
             "latestAction": {"text": "Introduced"}}
        ]}
        cosponsored = {"cosponsoredLegislation": [
            {"type": "s", "number": "2", "title": "Cosponsored Bill", "introducedDate": "2026-01-02",
             "latestAction": {"text": "Referred"}}
        ]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.side_effect = [_mock_response(sponsored), _mock_response(cosponsored)]
            votes = gtc.get_member_votes("P000197")
        assert len(votes) == 2
        assert votes[0]["role"] == "sponsor"
        assert votes[1]["role"] == "cosponsor"


# ─── get_politician_profile() — integration of the Phase 1 fix ───────────────

class TestPoliticianProfileLegislation:
    def test_unknown_politician_returns_error(self):
        result = gtc.get_politician_profile("totally_unknown_person_xyz")
        assert "error" in result

    def test_known_politician_returns_legislation_not_empty(self, monkeypatch):
        monkeypatch.setenv("CONGRESS_API_KEY", "test_key")
        members_sample = {"members": [
            {"directOrderName": "Nancy Pelosi", "bioguideId": "P000197", "state": "CA"}
        ]}
        legislation_sample = {"sponsoredLegislation": [
            {"title": "Banking Oversight Act", "type": "hr", "number": "10",
             "introducedDate": "2026-01-01", "policyArea": {"name": "Finance and Financial Sector"},
             "latestAction": {"text": "Referred to committee"}}
        ]}
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.side_effect = [_mock_response(members_sample), _mock_response(legislation_sample)]
            with patch("app.connectors.gov_trading_connector.get_trades_by_member", return_value=[]):
                profile = gtc.get_politician_profile("nancy_pelosi")

        assert profile["recent_legislation_sponsored"] != []
        assert profile["recent_legislation_sponsored"][0]["title"] == "Banking Oversight Act"
        assert len(profile["financially_relevant_legislation"]) >= 1

    def test_congress_api_failure_does_not_crash_profile(self, monkeypatch):
        """If Congress.gov is fully down, profile should still return (empty legislation), not raise."""
        with patch("app.connectors.gov_trading_connector.requests.get") as mock_get:
            mock_get.side_effect = ConnectionError("Congress.gov down")
            with patch("app.connectors.gov_trading_connector.get_trades_by_member", return_value=[]):
                profile = gtc.get_politician_profile("nancy_pelosi")
        assert "error" not in profile
        assert profile["recent_legislation_sponsored"] == []
