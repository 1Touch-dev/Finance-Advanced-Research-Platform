import os
import sys
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

from app.db.session import get_db
from app.main import app
from app.models.base import Base
from app.api import intelligence as intelligence_api
from app.connectors import opensecrets_connector
from app.connectors import sec_edgar_connector
from app.connectors import sec_http
from app.services import intelligence_activation_service
from app.services import intelligence_service


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_self_dealing_route_returns_grounded_cross_reference(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "FAMILY_NETWORK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_HOLDINGS_AVAILABLE", True)
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_proxy_intelligence",
        lambda ticker, years=3: {
            "related_party_transactions": [
                {"counterparties": ["Acme Ventures LLC"], "largest_amount": 15000000}
            ]
        },
    )
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0000000001")
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_insider_transactions",
        lambda cik: {"transactions": [{"insider": "Jane Doe", "roles": ["Director"]}]},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_board_interlocks",
        lambda transactions, cik, entity_name: {
            "people": [
                {
                    "name": "Jane Doe",
                    "roles_at_issuer": ["Director"],
                    "other_seats": [{"issuer": "Acme Ventures LLC", "current": True}],
                }
            ]
        },
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_full_contract_portfolio",
        lambda entity_name, executives=None, related_entities=None: {"contracts": [], "subcontracts": []},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "research_family_network",
        lambda entity_name, ticker: {"family_members": []},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_institutional_holders",
        lambda *args, **kwargs: {"holders": []},
    )
    monkeypatch.setattr(intelligence_activation_service, "get_quote", lambda ticker: {})

    response = client.post(
        "/intelligence/self-dealing",
        json={"entity_name": "Example Corp", "ticker": "EXM"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["summary"]["transactions_examined"] == 1
    assert payload["source_status"]["proxy_intelligence"]["status"] == "ok"
    assert payload["analysis"]["findings"]


def test_self_dealing_route_distinguishes_partial_sources_from_no_findings(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", True)
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_proxy_intelligence",
        lambda ticker, years=3: {"related_party_transactions": []},
    )
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0000000001")
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_insider_transactions",
        lambda cik: {"transactions": []},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_full_contract_portfolio",
        lambda entity_name, executives=None, related_entities=None: (_ for _ in ()).throw(
            RuntimeError("https://provider.example/request?apikey=secret failed")
        ),
    )

    response = client.post(
        "/intelligence/self-dealing",
        json={"entity_name": "Example Corp", "ticker": "EXM", "include_family_network": False, "include_institutional_holders": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["findings"] == []
    assert payload["analysis"]["summary"]["transactions_examined"] == 0
    assert payload["partial"] is True
    assert payload["source_status"]["contract_intelligence"]["status"] == "error"
    assert "secret" not in payload["source_status"]["contract_intelligence"]["detail"]


def test_self_dealing_route_sanitizes_family_network_missing_dependency(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "FAMILY_NETWORK_AVAILABLE", True)
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_proxy_intelligence",
        lambda ticker, years=3: {"related_party_transactions": []},
    )
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0000000001")
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_insider_transactions",
        lambda cik: {"transactions": []},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_full_contract_portfolio",
        lambda entity_name, executives=None, related_entities=None: {"contracts": [], "subcontracts": []},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "_build_self_dealing_family_network",
        lambda entity_name, ticker, proxy_data, insider_transactions: (_ for _ in ()).throw(ModuleNotFoundError("No module named 'bs4'")),
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_institutional_holders",
        lambda *args, **kwargs: {"holders": []},
    )
    monkeypatch.setattr(intelligence_activation_service, "get_quote", lambda ticker: {})

    response = client.post(
        "/intelligence/self-dealing",
        json={"entity_name": "Example Corp", "ticker": "EXM"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["partial"] is True
    assert payload["source_status"]["family_network"]["status"] == "unavailable"
    assert payload["source_status"]["family_network"]["detail"] == "Family network source unavailable."
    assert "bs4" not in payload["source_status"]["family_network"]["detail"]
    family_warnings = [warning for warning in payload["warnings"] if warning.get("source") == "family_network"]
    assert family_warnings
    assert family_warnings[0]["code"] == "source_unavailable"
    assert family_warnings[0]["detail"] == "Family network source unavailable."


def test_self_dealing_route_times_out_slow_source_and_returns_partial(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_activation_service,
        "_SELF_DEALING_SOURCE_TIMEOUTS",
        {
            "proxy_intelligence": 0.05,
            "insider_transactions": 0.05,
            "board_interlocks": 0.05,
            "contract_intelligence": 0.05,
            "family_network": 0.05,
            "institutional_holders": 0.05,
        },
    )
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "FAMILY_NETWORK_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_HOLDINGS_AVAILABLE", False)
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_proxy_intelligence",
        lambda ticker, years=3: {"related_party_transactions": []},
    )
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0000000001")
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_insider_transactions",
        lambda cik: {"transactions": []},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_full_contract_portfolio",
        lambda entity_name, executives=None, related_entities=None: (time.sleep(0.2) or {"contracts": []}),
    )

    response = client.post(
        "/intelligence/self-dealing",
        json={"entity_name": "Example Corp", "ticker": "EXM", "include_family_network": False, "include_institutional_holders": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["partial"] is True
    assert payload["source_status"]["contract_intelligence"]["status"] == "timeout"
    assert payload["source_status"]["contract_intelligence"]["detail"] == "Contract intelligence source timed out."
    contract_warnings = [warning for warning in payload["warnings"] if warning.get("source") == "contract_intelligence"]
    assert contract_warnings
    assert contract_warnings[0]["code"] == "timeout"


def test_self_dealing_resolves_company_name_entered_as_ticker(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "FAMILY_NETWORK_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_HOLDINGS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "_COMPANY_TICKER_TITLE_CACHE", {})
    monkeypatch.setattr(
        sec_http,
        "sec_get_json",
        lambda url, **kwargs: {
            "0": {"ticker": "NVDA", "title": "NVIDIA CORP", "cik_str": 1045810}
        },
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_proxy_intelligence",
        lambda ticker, years=1: {"related_party_transactions": []},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_cik_from_ticker",
        lambda ticker: "0001045810" if ticker == "NVDA" else None,
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_insider_transactions",
        lambda cik, max_filings=40: {"transactions": [{"insider": "Jane Doe", "roles": ["Director"]}]},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_board_interlocks",
        lambda transactions, cik, entity_name: {"people": []},
    )

    response = client.post(
        "/intelligence/self-dealing",
        json={"entity_name": "NVIDIA Corporation", "ticker": "NVIDIA CORPORATION"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "NVDA"
    assert payload["cik"] == "0001045810"
    assert payload["source_status"]["insider_transactions"]["status"] == "ok"


def test_self_dealing_preserves_cik_when_insider_parsing_times_out(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_activation_service,
        "_SELF_DEALING_SOURCE_TIMEOUTS",
        {
            "proxy_intelligence": 0.05,
            "insider_transactions": 0.05,
            "board_interlocks": 0.05,
            "contract_intelligence": 0.05,
            "family_network": 0.05,
            "institutional_holders": 0.05,
        },
    )
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "FAMILY_NETWORK_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_HOLDINGS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "_resolve_self_dealing_cik", lambda ticker: "0000789019")
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_insider_transactions",
        lambda cik, max_filings=40: (time.sleep(0.2) or {"transactions": []}),
    )

    response = client.post(
        "/intelligence/self-dealing",
        json={"entity_name": "Microsoft Corporation", "ticker": "MSFT", "include_family_network": False, "include_institutional_holders": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cik"] == "0000789019"
    assert payload["source_status"]["insider_transactions"]["status"] == "timeout"


def test_network_route_limits_depth_to_grounded_first_degree(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_HOLDINGS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_OVERLAP_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", True)
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_proxy_intelligence",
        lambda ticker, years=3: {
            "board_composition": {
                "directors": [
                    {
                        "name": "Alice Smith",
                        "principal_position": "Founder",
                        "biography": "Alice Smith received an MBA from Stanford University and worked at PayPal.",
                    },
                    {
                        "name": "Bob Jones",
                        "principal_position": "Director",
                        "biography": "Bob Jones studied at Stanford University and previously served at PayPal.",
                    },
                ]
            }
        },
    )
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0000000002")
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_insider_transactions",
        lambda cik: {"transactions": [{"insider": "Alice Smith"}]},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_board_interlocks",
        lambda transactions, cik, entity_name: {"people": [{"name": "Alice Smith", "other_seats": []}]},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_quote",
        lambda ticker: {"shares_outstanding": 1000, "price": 10},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_institutional_holders",
        lambda *args, **kwargs: {
            "holders": [
                {"institution": "Vanguard Group Inc", "shares": 300, "value": 3000},
                {"institution": "BlackRock Inc", "shares": 200, "value": 2000},
            ]
        },
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "compare_competitor_ownership",
        lambda ticker, competitors: {"summary": {"avg_overlap_pct": 12.5}},
    )

    response = client.post(
        "/intelligence/network",
        json={
            "entity_name": "Example Corp",
            "ticker": "EXM",
            "competitors": ["CMP1", "CMP2"],
            "depth": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["founder_correlations"]["network_stats"]["node_count"] == 2
    assert payload["position_concentration"]["herfindahl_index"] > 0
    assert any(item["code"] == "depth_limited" for item in payload["warnings"])


def test_network_route_handles_empty_inputs_cleanly(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_HOLDINGS_AVAILABLE", True)
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_proxy_intelligence",
        lambda ticker, years=3: {},
    )
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: None)
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_institutional_holders",
        lambda *args, **kwargs: {},
    )

    response = client.post(
        "/intelligence/network",
        json={"entity_name": "Example Corp", "ticker": "EXM"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["founder_correlations"]["nodes"] == []
    assert payload["co_investment_network"] == {}
    assert payload["position_concentration"] == {}


def test_get_filer_cik_does_not_cache_transient_none(monkeypatch):
    sec_edgar_connector._FILER_CIK_CACHE.clear()

    calls = {"count": 0}

    def fake_get_cik_from_ticker(ticker):
        calls["count"] += 1
        return None if calls["count"] == 1 else "0000320193"

    monkeypatch.setattr(sec_edgar_connector, "get_cik_from_ticker", fake_get_cik_from_ticker)
    monkeypatch.setattr(sec_edgar_connector, "_cik_has_financials", lambda cik: True)

    first = sec_edgar_connector.get_filer_cik("AAPL")
    second = sec_edgar_connector.get_filer_cik("AAPL")

    assert first is None
    assert second == "0000320193"
    assert sec_edgar_connector._FILER_CIK_CACHE["AAPL"] == "0000320193"


def test_get_insider_transactions_respects_interactive_elapsed_budget(monkeypatch):
    monkeypatch.setattr(sec_edgar_connector, "_rate_limit", lambda: None)
    monkeypatch.setattr(
        sec_edgar_connector,
        "get_company_submissions",
        lambda cik, forms=None, limit=100, request_timeout=30: {
            "filings": [
                {"filing_date": "2026-01-01", "accession": "0001", "document": "form4.xml"},
                {"filing_date": "2026-01-02", "accession": "0002", "document": "form4.xml"},
                {"filing_date": "2026-01-03", "accession": "0003", "document": "form4.xml"},
            ]
        },
    )
    calls = {"count": 0}

    class Response:
        ok = False
        text = ""

    def slow_get(*args, **kwargs):
        calls["count"] += 1
        time.sleep(0.08)
        return Response()

    monkeypatch.setattr(sec_edgar_connector.requests, "get", slow_get)

    started = time.perf_counter()
    payload = sec_edgar_connector.get_insider_transactions(
        "0000789019",
        max_filings=3,
        request_timeout=0.05,
        max_elapsed_seconds=0.1,
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 0.2
    assert calls["count"] == 1
    assert payload["timeout"] is True
    assert payload["partial"] is True


def test_interactive_insider_helper_passes_budgeted_connector_options(monkeypatch):
    captured = {}

    def fake_get_insider_transactions(cik, **kwargs):
        captured.update(kwargs)
        return {"transactions": [{"insider": "Jane Doe"}]}

    monkeypatch.setattr(
        intelligence_activation_service,
        "get_insider_transactions",
        fake_get_insider_transactions,
    )

    payload = intelligence_activation_service._build_interactive_insider_transactions_for_cik("0000789019")

    assert payload["cik"] == "0000789019"
    assert payload["insider_transactions"]["transactions"]
    assert captured["max_filings"] == intelligence_activation_service._INTERACTIVE_INSIDER_MAX_FILINGS
    assert captured["request_timeout"] == intelligence_activation_service._INTERACTIVE_INSIDER_REQUEST_TIMEOUT
    assert captured["max_elapsed_seconds"] == intelligence_activation_service._INTERACTIVE_INSIDER_MAX_ELAPSED


def test_network_route_uses_interactive_insider_data_for_board_interlocks(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_HOLDINGS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_OVERLAP_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "get_proxy_intelligence", lambda ticker, years=3: {})
    monkeypatch.setattr(intelligence_activation_service, "_resolve_interactive_cik", lambda ticker: "0000789019")
    monkeypatch.setattr(
        intelligence_activation_service,
        "_build_interactive_insider_transactions_for_cik",
        lambda cik: {"cik": cik, "insider_transactions": {"transactions": [{"insider": "Jane Doe"}]}},
    )
    captured = {}

    def fake_board_interlocks(transactions, cik, entity_name):
        captured["transactions"] = transactions
        captured["cik"] = cik
        return {"people": [{"name": "Jane Doe"}]}

    monkeypatch.setattr(intelligence_activation_service, "get_board_interlocks", fake_board_interlocks)
    monkeypatch.setattr(intelligence_activation_service, "get_quote", lambda ticker: {"shares_outstanding": 1000, "price": 10})
    monkeypatch.setattr(intelligence_activation_service, "get_institutional_holders", lambda *args, **kwargs: {"holders": []})
    monkeypatch.setattr(intelligence_activation_service, "compare_competitor_ownership", lambda ticker, competitors: {})

    response = client.post(
        "/intelligence/network",
        json={"entity_name": "Microsoft Corporation", "ticker": "MSFT", "competitors": ["GOOGL"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cik"] == "0000789019"
    assert payload["source_status"]["insider_transactions"]["status"] == "ok"
    assert payload["source_status"]["board_interlocks"]["status"] == "ok"
    assert captured["transactions"] == [{"insider": "Jane Doe"}]
    assert captured["cik"] == "0000789019"


def test_network_route_bounds_slow_interactive_insider_provider(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_activation_service,
        "_CORRELATION_SOURCE_TIMEOUTS",
        {
            "insider_transactions": 0.05,
            "price_history": 0.05,
            "event_timeline": 0.05,
            "political_intelligence": 0.05,
            "contract_intelligence": 0.05,
            "deep_comparative": 0.05,
        },
    )
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_HOLDINGS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_OVERLAP_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "_resolve_interactive_cik", lambda ticker: "0000789019")
    monkeypatch.setattr(
        intelligence_activation_service,
        "_build_interactive_insider_transactions_for_cik",
        lambda cik: (time.sleep(0.2) or {"cik": cik, "insider_transactions": {"transactions": []}}),
    )

    started = time.perf_counter()
    response = client.post(
        "/intelligence/network",
        json={"entity_name": "Microsoft Corporation", "ticker": "MSFT"},
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed < 0.16
    payload = response.json()
    assert payload["cik"] == "0000789019"
    assert payload["source_status"]["insider_transactions"]["status"] == "timeout"
    assert payload["source_status"]["board_interlocks"]["status"] == "missing_input"
    assert payload["partial"] is True


def test_self_dealing_maps_budgeted_insider_timeout_without_board_interlocks(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "PROXY_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "BOARD_INTERLOCK_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "FAMILY_NETWORK_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "INSTITUTIONAL_HOLDINGS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "_resolve_self_dealing_cik", lambda ticker: "0000789019")
    monkeypatch.setattr(
        intelligence_activation_service,
        "_build_interactive_insider_transactions_for_cik",
        lambda cik: {
            "cik": cik,
            "insider_transactions": {
                "transactions": [],
                "timeout": True,
                "partial": True,
            },
        },
    )

    response = client.post(
        "/intelligence/self-dealing",
        json={"entity_name": "Microsoft Corporation", "ticker": "MSFT", "include_family_network": False, "include_institutional_holders": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["cik"] == "0000789019"
    assert payload["source_status"]["insider_transactions"]["status"] == "timeout"
    assert payload["source_status"]["board_interlocks"]["status"] == "missing_input"


def test_interactive_insider_payload_unavailable_and_no_data_classification():
    assert intelligence_activation_service._classify_interactive_insider_payload(
        {"transactions": [], "error": "HTTP 503"}
    )[:2] == ("unavailable", False)
    assert intelligence_activation_service._classify_interactive_insider_payload(
        {"transactions": []}
    )[:2] == ("no_data", False)


class _FakeResponse:
    def __init__(self, status_code, payload=None, text="", headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text
        self.headers = headers or {}
        self.ok = 200 <= status_code < 300
        self.is_redirect = status_code in (301, 302, 307, 308)

    def json(self):
        return self._payload


def test_lda_403_fails_fast_without_exponential_sleep(monkeypatch):
    opensecrets_connector.reset_lda_circuit()
    calls = {"sleep": [], "get": 0}

    monkeypatch.delenv("LDA_API_KEY", raising=False)
    monkeypatch.delenv("SENATE_LDA_API_KEY", raising=False)
    monkeypatch.setattr(opensecrets_connector.time, "sleep", lambda seconds: calls["sleep"].append(seconds))

    def fake_get(*args, **kwargs):
        calls["get"] += 1
        return _FakeResponse(403, text="forbidden")

    monkeypatch.setattr(opensecrets_connector.requests, "get", fake_get)

    payload = opensecrets_connector._fetch_lda_page({"client_name": "NVIDIA"}, attempts=4, request_timeout=1)

    assert payload == {}
    assert calls["get"] == 1
    assert calls["sleep"] == []
    assert opensecrets_connector._LDA_STATE["blocked"] is True
    assert "403" in opensecrets_connector._LDA_STATE["reason"]


def test_lda_401_fails_fast(monkeypatch):
    opensecrets_connector.reset_lda_circuit()
    calls = {"sleep": []}

    monkeypatch.setattr(opensecrets_connector.time, "sleep", lambda seconds: calls["sleep"].append(seconds))
    monkeypatch.setattr(opensecrets_connector.requests, "get", lambda *args, **kwargs: _FakeResponse(401))

    payload = opensecrets_connector._fetch_lda_page({"client_name": "NVIDIA"}, attempts=4, request_timeout=1)

    assert payload == {}
    assert calls["sleep"] == []
    assert opensecrets_connector._LDA_STATE["blocked"] is True
    assert "401" in opensecrets_connector._LDA_STATE["reason"]


def test_lda_429_fails_fast_without_long_retry(monkeypatch):
    opensecrets_connector.reset_lda_circuit()
    calls = {"sleep": []}

    monkeypatch.setattr(opensecrets_connector.time, "sleep", lambda seconds: calls["sleep"].append(seconds))
    monkeypatch.setattr(
        opensecrets_connector.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(429, headers={"Retry-After": "120"}),
    )

    payload = opensecrets_connector._fetch_lda_page({"client_name": "NVIDIA"}, attempts=4, request_timeout=1)

    assert payload == {}
    assert calls["sleep"] == []
    assert opensecrets_connector._LDA_STATE["blocked"] is True
    assert "429" in opensecrets_connector._LDA_STATE["reason"]


def test_lda_transient_retry_is_bounded(monkeypatch):
    opensecrets_connector.reset_lda_circuit()
    sleeps = []
    statuses = iter([500, 200])

    monkeypatch.setattr(opensecrets_connector.time, "sleep", lambda seconds: sleeps.append(seconds))

    def fake_get(*args, **kwargs):
        status = next(statuses)
        if status == 200:
            return _FakeResponse(200, payload={"results": [{"id": 1}]})
        return _FakeResponse(status, text="temporary")

    monkeypatch.setattr(opensecrets_connector.requests, "get", fake_get)

    payload = opensecrets_connector._fetch_lda_page({"client_name": "NVIDIA"}, attempts=2, request_timeout=1)

    assert payload == {"results": [{"id": 1}]}
    assert sleeps == [2]
    assert opensecrets_connector._LDA_STATE["blocked"] is False


def test_correlation_route_returns_correlation_and_comparative_results(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0000000003")
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_insider_transactions",
        lambda cik: {"transactions": [{"insider": "Alice Smith"}]},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_price_history",
        lambda ticker, days=400: {"bars": [{"date": "2026-01-01", "close": 10.0}], "source": "mock"},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "generate_entity_timeline",
        lambda ticker, years=2: {"events": [{"date": "2026-01-01", "type": "filing"}]},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_political_intelligence",
        lambda entity_name, executives=None, cycles=None: {"lobbying_summary": {"top_issues": []}},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_full_contract_portfolio",
        lambda entity_name: {"contracts": [], "subcontracts": []},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "run_correlation_suite",
        lambda data: {"ran": 2, "insider_timing": {"n": 12}, "event_returns": {"n": 15}},
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "run_deep_comparative_analysis",
        lambda ticker, competitors, target_cik=None: {"peer_count": len(competitors)},
    )

    response = client.post(
        "/intelligence/correlation",
        json={
            "entity_name": "Example Corp",
            "ticker": "EXM",
            "competitors": ["CMP1", "CMP2"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["correlations"]["ran"] == 2
    assert payload["deep_comparative"]["peer_count"] == 2


@pytest.mark.parametrize("ticker", ["AAPL", "MSFT", "NVDA", "GOOGL", "LMT"])
def test_correlation_route_invokes_political_intelligence_with_company_identifier(client, monkeypatch, ticker):
    calls = {}

    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", False)
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_political_intelligence",
        lambda company_name, executives=None, cycles=None: calls.setdefault(
            "payload",
            {
                "company_name": company_name,
                "executives": executives,
                "cycles": cycles,
            },
        ) or {"lobbying_summary": {"top_issues": []}},
    )
    monkeypatch.setattr(intelligence_activation_service, "run_correlation_suite", lambda data: {"ran": 0})

    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": f"{ticker} Corp", "ticker": ticker},
    )

    assert response.status_code == 200
    assert calls["payload"]["company_name"] == f"{ticker} Corp"
    assert calls["payload"]["executives"] is None
    assert calls["payload"]["cycles"] is None
    assert response.json()["source_status"]["political_intelligence"]["status"] == "ok"


def test_correlation_route_normalizes_competitors_and_passes_target_cik(client, monkeypatch):
    comparative_calls = {}

    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0000320193")
    monkeypatch.setattr(intelligence_activation_service, "get_insider_transactions", lambda cik: {})
    monkeypatch.setattr(intelligence_activation_service, "run_correlation_suite", lambda data: {"ran": 0})
    monkeypatch.setattr(
        intelligence_activation_service,
        "run_deep_comparative_analysis",
        lambda ticker, competitors, target_cik=None: comparative_calls.setdefault(
            "payload",
            {"ticker": ticker, "competitors": competitors, "target_cik": target_cik},
        ) or {"peer_count": len(competitors)},
    )

    response = client.post(
        "/intelligence/correlation",
        json={
            "entity_name": "Apple Inc",
            "ticker": "aapl",
            "competitors": [" msft ", "AAPL", "MSFT", "123 bad", "nvda", "googl", "lmt", "orcl", "amd"],
        },
    )

    assert response.status_code == 200
    assert comparative_calls["payload"]["ticker"] == "AAPL"
    assert comparative_calls["payload"]["competitors"] == ["MSFT", "NVDA", "GOOGL", "LMT", "ORCL"]
    assert comparative_calls["payload"]["target_cik"] == "0000320193"
    codes = {warning["code"] for warning in response.json()["warnings"]}
    assert "invalid_competitor" in codes
    assert "primary_competitor_removed" in codes
    assert "duplicate_competitor_removed" in codes
    assert "competitor_limit" in codes


def test_correlation_route_handles_invalid_competitor_list_without_crashing(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "run_correlation_suite", lambda data: {"ran": 0})

    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": "Example Corp", "ticker": "EXM", "competitors": ["??", " ", "EXM"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_status"]["deep_comparative"]["status"] == "missing_input"
    codes = {warning["code"] for warning in payload["warnings"]}
    assert "invalid_competitor" in codes
    assert "primary_competitor_removed" in codes


def test_correlation_route_supports_single_competitor(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0000051143")
    monkeypatch.setattr(intelligence_activation_service, "get_insider_transactions", lambda cik: {})
    monkeypatch.setattr(intelligence_activation_service, "run_correlation_suite", lambda data: {"ran": 0})
    monkeypatch.setattr(
        intelligence_activation_service,
        "run_deep_comparative_analysis",
        lambda ticker, competitors, target_cik=None: {"peer_count": len(competitors), "peer_tickers": competitors},
    )

    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": "Microsoft Corp", "ticker": "MSFT", "competitors": ["NVDA"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["deep_comparative"]["peer_count"] == 1
    assert payload["deep_comparative"]["peer_tickers"] == ["NVDA"]


def test_correlation_route_political_provider_unavailable_is_honest(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "run_correlation_suite", lambda data: {"ran": 0})

    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": "Example Corp", "ticker": "EXM"},
    )

    assert response.status_code == 200
    assert response.json()["source_status"]["political_intelligence"]["status"] == "unavailable"


def test_correlation_route_handles_malformed_upstream_data_without_crashing(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0001045810")
    monkeypatch.setattr(intelligence_activation_service, "get_insider_transactions", lambda cik: ["bad-shape"])
    monkeypatch.setattr(intelligence_activation_service, "get_price_history", lambda ticker, days=400: "bad-shape")
    monkeypatch.setattr(intelligence_activation_service, "generate_entity_timeline", lambda ticker, years=2: ["bad-shape"])
    monkeypatch.setattr(intelligence_activation_service, "get_political_intelligence", lambda company_name, executives=None, cycles=None: ["bad-shape"])
    monkeypatch.setattr(intelligence_activation_service, "get_full_contract_portfolio", lambda entity_name: ["bad-shape"])
    monkeypatch.setattr(intelligence_activation_service, "run_deep_comparative_analysis", lambda ticker, competitors, target_cik=None: ["bad-shape"])

    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": "NVIDIA Corp", "ticker": "NVDA", "competitors": ["MSFT"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_status"]["insider_transactions"]["status"] == "no_data"
    assert payload["source_status"]["price_history"]["status"] == "no_data"
    assert payload["source_status"]["event_timeline"]["status"] == "no_data"
    assert payload["source_status"]["political_intelligence"]["status"] == "no_data"
    assert payload["source_status"]["contract_intelligence"]["status"] == "no_data"
    assert payload["source_status"]["deep_comparative"]["status"] == "no_data"
    assert payload["correlations"]["ran"] == 0


def test_correlation_route_reports_insufficient_observations_honestly(client, monkeypatch):
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0000000003")
    monkeypatch.setattr(intelligence_activation_service, "get_insider_transactions", lambda cik: {"transactions": []})
    monkeypatch.setattr(intelligence_activation_service, "get_price_history", lambda ticker, days=400: {"bars": [{"date": "2026-01-01", "close": 10.0}], "source": "mock"})
    monkeypatch.setattr(intelligence_activation_service, "generate_entity_timeline", lambda ticker, years=2: {"events": []})
    monkeypatch.setattr(intelligence_activation_service, "get_political_intelligence", lambda company_name, executives=None, cycles=None: {})
    monkeypatch.setattr(intelligence_activation_service, "get_full_contract_portfolio", lambda entity_name: {})

    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": "Example Corp", "ticker": "EXM"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["correlations"]["ran"] == 0
    assert payload["correlations"]["insider_timing"] is None
    assert payload["correlations"]["event_returns"] is None
    assert payload["correlations"]["lobbying_lag"] is None


def test_correlation_route_times_out_slow_source_and_returns_partial(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_activation_service,
        "_CORRELATION_SOURCE_TIMEOUTS",
        {
            "insider_transactions": 0.05,
            "price_history": 0.05,
            "event_timeline": 0.05,
            "political_intelligence": 0.05,
            "contract_intelligence": 0.05,
            "deep_comparative": 0.05,
        },
    )
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "run_correlation_suite", lambda data: {"ran": 0})
    monkeypatch.setattr(
        intelligence_activation_service,
        "get_full_contract_portfolio",
        lambda entity_name: (time.sleep(0.2) or {"contracts": []}),
    )

    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": "Example Corp", "ticker": "EXM"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["partial"] is True
    assert payload["source_status"]["contract_intelligence"]["status"] == "timeout"
    assert payload["source_status"]["contract_intelligence"]["detail"] == "Contract intelligence source timed out."
    warnings = [warning for warning in payload["warnings"] if warning.get("source") == "contract_intelligence"]
    assert warnings
    assert warnings[0]["code"] == "timeout"


def test_correlation_route_bounds_multiple_slow_sources_concurrently(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_activation_service,
        "_CORRELATION_SOURCE_TIMEOUTS",
        {
            "insider_transactions": 0.05,
            "price_history": 0.05,
            "event_timeline": 0.05,
            "political_intelligence": 0.05,
            "contract_intelligence": 0.05,
            "deep_comparative": 0.05,
        },
    )
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0001045810")
    monkeypatch.setattr(intelligence_activation_service, "get_insider_transactions", lambda cik: {"transactions": []})
    monkeypatch.setattr(intelligence_activation_service, "run_correlation_suite", lambda data: {"ran": 0})
    monkeypatch.setattr(intelligence_activation_service, "get_price_history", lambda ticker, days=400: (time.sleep(0.2) or {"bars": []}))
    monkeypatch.setattr(intelligence_activation_service, "generate_entity_timeline", lambda ticker, years=2: (time.sleep(0.2) or {"events": []}))
    monkeypatch.setattr(intelligence_activation_service, "get_political_intelligence", lambda company_name, executives=None, cycles=None: (time.sleep(0.2) or {}))
    monkeypatch.setattr(intelligence_activation_service, "get_full_contract_portfolio", lambda entity_name: (time.sleep(0.2) or {"contracts": []}))
    monkeypatch.setattr(intelligence_activation_service, "run_deep_comparative_analysis", lambda ticker, competitors, target_cik=None: (time.sleep(0.2) or {}))

    started = time.perf_counter()
    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": "NVIDIA Corp", "ticker": "NVDA", "competitors": ["AMD", "INTC"]},
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    payload = response.json()
    assert elapsed < 0.35
    assert payload["source_status"]["price_history"]["status"] == "timeout"
    assert payload["source_status"]["event_timeline"]["status"] == "timeout"
    assert payload["source_status"]["political_intelligence"]["status"] == "timeout"
    assert payload["source_status"]["contract_intelligence"]["status"] == "timeout"
    assert payload["source_status"]["deep_comparative"]["status"] == "timeout"


def test_correlation_route_does_not_wait_for_hung_political_worker(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_activation_service,
        "_CORRELATION_SOURCE_TIMEOUTS",
        {
            "insider_transactions": 0.05,
            "price_history": 0.05,
            "event_timeline": 0.05,
            "political_intelligence": 0.05,
            "contract_intelligence": 0.05,
            "deep_comparative": 0.05,
        },
    )
    monkeypatch.setattr(intelligence_activation_service, "_CORRELATION_WALL_CLOCK_BUDGET", 0.05)
    monkeypatch.setattr(intelligence_activation_service, "SEC_EDGAR_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "MARKET_DATA_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "POLITICAL_AVAILABLE", True)
    monkeypatch.setattr(intelligence_activation_service, "CONTRACTS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "DEEP_COMPARATIVE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_activation_service, "get_filer_cik", lambda ticker: "0001045810")
    monkeypatch.setattr(intelligence_activation_service, "get_insider_transactions", lambda cik: {"transactions": []})
    monkeypatch.setattr(intelligence_activation_service, "get_price_history", lambda ticker, days=400: {"bars": [{"date": "2026-01-01", "close": 10}]})
    monkeypatch.setattr(intelligence_activation_service, "generate_entity_timeline", lambda ticker, years=2: {"events": [{"date": "2026-01-01"}]})
    monkeypatch.setattr(intelligence_activation_service, "run_correlation_suite", lambda data: {"ran": 2})

    monkeypatch.setattr(
        intelligence_activation_service,
        "_build_correlation_political_intelligence",
        lambda entity_name: (time.sleep(0.2) or {}),
    )

    started = time.perf_counter()
    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": "NVIDIA Corp", "ticker": "NVDA"},
    )
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed < 0.16
    payload = response.json()
    assert payload["partial"] is True
    assert payload["source_status"]["price_history"]["status"] == "ok"
    assert payload["source_status"]["event_timeline"]["status"] == "ok"
    assert payload["source_status"]["political_intelligence"]["status"] == "timeout"
    warnings = [warning for warning in payload["warnings"] if warning.get("source") == "political_intelligence"]
    assert warnings
    assert warnings[0]["code"] == "timeout"


def test_correlation_route_reports_missing_inputs_without_crashing(client):
    response = client.post(
        "/intelligence/correlation",
        json={"entity_name": "Example Corp"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_status"]["insider_transactions"]["status"] == "missing_input"
    assert payload["source_status"]["price_history"]["status"] == "missing_input"
    assert "correlations" in payload


def test_contract_probability_route_reports_empty_pipeline_honestly(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_activation_service,
        "analyze_contract_probability",
        lambda *args, **kwargs: {
            "historical_performance": {"total_awards_5yr": 0},
            "opportunity_pipeline": {"opportunities_identified": 0},
        },
    )

    response = client.post(
        "/intelligence/contract-probability",
        json={"entity_name": "Example Corp", "ticker": "EXM"},
    )

    assert response.status_code == 200
    payload = response.json()
    codes = {item["code"] for item in payload["warnings"]}
    assert "limited_contract_history" in codes
    assert "no_open_opportunities" in codes
    assert payload["analysis"]["opportunity_pipeline"]["weighted_avg_win_probability"] is None


def test_interactive_report_route_returns_html(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_api,
        "build_interactive_report_html",
        lambda db, entity_name, entity_type="org", ticker="": {
            "html": "<html><body>interactive report</body></html>"
        },
    )

    response = client.post(
        "/intelligence/interactive-report",
        json={"entity_name": "Example Corp", "ticker": "EXM"},
    )

    assert response.status_code == 200
    assert "interactive report" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_interactive_report_route_returns_controlled_error_when_generation_fails(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_api,
        "build_interactive_report_html",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Interactive report generation failed.")),
    )

    response = client.post(
        "/intelligence/interactive-report",
        json={"entity_name": "Example Corp", "ticker": "EXM"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Interactive report generation failed."


def test_generate_enhanced_report_persists_grounded_sections_and_interactive_payload(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_service,
        "generate_intelligence_report",
        lambda db, entity_name, entity_type="org", ticker=None: {
            "report_id": 11,
            "entity_id": 99,
            "entity_name": entity_name,
            "entity_type": entity_type,
            "ticker": ticker,
            "sections": [{"name": "Base Section", "order": 1, "claims": [{"text": "Base claim"}]}],
            "summary": {"base": True},
            "data_sources": {"sec": True},
            "relationships_created": [],
        },
    )
    monkeypatch.setattr(intelligence_service, "ENHANCED_NARRATIVE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "YFINANCE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "VALUATION_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "TECHNICALS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "APOLLO_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "MULTI_AGENT_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "DEEP_RESEARCH_AVAILABLE", False)
    monkeypatch.setattr(
        intelligence_activation_service,
        "build_report_intelligence_additions",
        lambda **kwargs: {
            "sections": [
                {
                    "name": "Grounded Founder & Executive Network",
                    "order": 0,
                    "claims": [{"text": "Two executives attended Stanford University.", "confidence": "ANALYTICAL"}],
                    "data": {"founder_correlations": {"nodes": [{"id": "Alice"}]}},
                },
                {
                    "name": "Deep Comparative Analysis",
                    "order": 10,
                    "claims": [{"text": "EXM ranks first against two peers.", "confidence": "ANALYTICAL"}],
                    "data": {"deep_comparative": {"peer_count": 2}},
                },
            ],
            "network_analysis": {"founder_correlations": {"nodes": [{"id": "Alice"}]}},
            "correlation_analysis": {"correlations": {"ran": 1}, "deep_comparative": {"peer_count": 2}},
            "interactive_report": {"supported": True, "graph_data": {"nodes": [], "links": []}},
        },
    )

    db = next(app.dependency_overrides[get_db]())
    try:
        report = intelligence_service.generate_enhanced_intelligence_report(
            db,
            entity_name="Example Corp",
            entity_type="org",
            ticker="EXM",
            competitors=["CMP1", "CMP2"],
            network_depth=1,
        )
        reloaded = intelligence_service.get_enhanced_intelligence_report(db, report["report_id"])
    finally:
        db.close()

    assert report["network_analysis"]["founder_correlations"]["nodes"]
    assert report["correlation_analysis"]["deep_comparative"]["peer_count"] == 2
    assert report["interactive_report"]["supported"] is True
    assert any(section["name"] == "Grounded Founder & Executive Network" for section in report["sections"])
    assert reloaded["interactive_report"]["supported"] is True
    assert reloaded["network_analysis"]["founder_correlations"]["nodes"]


def test_interactive_report_by_report_id_renders_for_newly_generated_compatible_report(client, monkeypatch):
    monkeypatch.setattr(
        intelligence_service,
        "generate_intelligence_report",
        lambda db, entity_name, entity_type="org", ticker=None: {
            "report_id": 12,
            "entity_id": 100,
            "entity_name": entity_name,
            "entity_type": entity_type,
            "ticker": ticker,
            "sections": [{"name": "Base Section", "order": 1, "claims": [{"text": "Base claim"}]}],
            "summary": {},
            "data_sources": {},
            "relationships_created": [],
        },
    )
    monkeypatch.setattr(intelligence_service, "ENHANCED_NARRATIVE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "YFINANCE_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "VALUATION_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "TECHNICALS_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "APOLLO_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "MULTI_AGENT_AVAILABLE", False)
    monkeypatch.setattr(intelligence_service, "DEEP_RESEARCH_AVAILABLE", False)
    monkeypatch.setattr(
        intelligence_activation_service,
        "build_report_intelligence_additions",
        lambda **kwargs: {
            "sections": [],
            "network_analysis": {},
            "correlation_analysis": {},
            "interactive_report": {"supported": True, "graph_data": {"nodes": [], "links": []}},
        },
    )
    monkeypatch.setattr(
        intelligence_activation_service,
        "generate_interactive_report",
        lambda markdown_content, data, output_path, entity_name="", ticker="": (
            open(output_path, "w", encoding="utf-8").write("<html><body>stored interactive</body></html>") or True
        ) and {"written": True, "path": output_path},
    )

    db = next(app.dependency_overrides[get_db]())
    try:
        report = intelligence_service.generate_enhanced_intelligence_report(
            db,
            entity_name="Example Corp",
            entity_type="org",
            ticker="EXM",
        )
    finally:
        db.close()

    response = client.get(f"/intelligence/{report['report_id']}/interactive")

    assert response.status_code == 200
    assert "stored interactive" in response.text


def test_interactive_report_by_report_id_rejects_historical_incomplete_report(client):
    db = next(app.dependency_overrides[get_db]())
    try:
        db.execute(
            intelligence_service.text("INSERT INTO reports (title, kind, status) VALUES (:t, :k, 'published')"),
            {"t": "Enhanced Intelligence Report: Legacy Corp", "k": intelligence_service.ENHANCED_INTELLIGENCE_KIND},
        )
        db.commit()
        report_id = db.execute(
            intelligence_service.text("SELECT id FROM reports ORDER BY id DESC LIMIT 1")
        ).scalar_one()
        intelligence_service._save_report_meta(
            db,
            report_id,
            {"entity_name": "Legacy Corp", "entity_type": "org", "ticker": "LEG", "summary": {}},
        )
    finally:
        db.close()

    response = client.get(f"/intelligence/{report_id}/interactive")

    assert response.status_code == 409
    assert "newly generated compatible reports" in response.json()["detail"]


def test_paypal_mafia_addendum_builds_grounded_markdown(monkeypatch):
    monkeypatch.setattr(
        intelligence_activation_service,
        "build_network_analysis",
        lambda **kwargs: {
            "founder_correlations": {
                "nodes": [{"id": "Peter Thiel"}],
                "network_stats": {"node_count": 1, "edge_count": 0, "education_connections": 0, "company_connections": 0, "elite_university_pct": 0},
                "key_findings": ["Peter Thiel appears in the grounded cohort."],
                "education_overlaps": {},
                "company_overlaps": {},
            },
            "co_investment_network": {},
            "source_status": {},
            "warnings": [],
        },
    )

    addendum = intelligence_activation_service.build_paypal_mafia_report_addendum()

    assert "Peter Thiel appears in the grounded cohort." in addendum["markdown"]
    assert addendum["analysis"]["founder_correlations"]["nodes"]


def test_openapi_contains_new_intelligence_routes():
    schema = app.openapi()
    for path in (
        "/intelligence/self-dealing",
        "/intelligence/network",
        "/intelligence/correlation",
        "/intelligence/contract-probability",
        "/intelligence/interactive-report",
        "/intelligence/{report_id}/interactive",
    ):
        assert path in schema["paths"]
