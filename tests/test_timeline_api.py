import os
import sys
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

from app.api import intelligence as intelligence_api
from app.connectors import timeline_connector
from app.db.session import get_db
from app.main import app
from app.models.base import Base


def _timeline_fixture():
    return {
        "ticker": "NVDA",
        "events": [
            {
                "date": "2026-08-01",
                "event_type": "earnings_release",
                "form_type": "8-K",
                "title": "Earnings Release (8-K 2.02)",
                "description": "Quarterly results announced",
                "entity": "NVIDIA Corporation",
                "source": "SEC 8-K",
                "source_url": "https://sec.example/8k",
                "priority": 8,
                "category": "financial",
                "price": 140.25,
                "change_pct": 5.2,
                "accession": "0001",
                "document": "earnings.htm",
            },
            {
                "date": "2026-07-15",
                "event_type": "insider_cluster",
                "title": "Multiple Insider Transactions (3 filings)",
                "description": "Insiders filing: Jane Doe, John Roe, Sam Poe",
                "entity": "NVIDIA Corporation",
                "source": "SEC Form 4",
                "priority": 6,
                "category": "insider",
            },
            {
                "date": "2026-06-01",
                "event_type": "price_movement",
                "title": "Stock Up 11.0%",
                "description": "Closed at $130.00",
                "entity": "NVIDIA Corporation",
                "source": "Market Data",
                "priority": 5,
                "category": "market",
                "price": 130.0,
                "change_pct": 11.0,
            },
        ],
    }


def _price_fixture():
    return {
        "ticker": "NVDA",
        "bars": [
            {"date": "2026-07-31", "close": 133.5, "volume": 1000, "open": 130},
            {"date": "2026-08-01", "close": 140.25, "volume": 2000, "open": 134},
        ],
    }


def _compare_timeline_fixture():
    return {
        "tickers": ["NVDA", "AMD", "INTC"],
        "timelines": {
            "NVDA": {
                "ticker": "NVDA",
                "events": [
                    {
                        "date": "2026-08-03",
                        "event_type": "earnings_release",
                        "title": "NVIDIA earnings",
                        "description": "NVIDIA reported quarterly earnings",
                        "source": "SEC 8-K",
                        "source_url": "https://sec.example/nvda-8k",
                        "priority": 8,
                        "category": "financial",
                        "price": 150.0,
                        "change_pct": 3.5,
                        "accession": "nvda-1",
                        "document": "earnings.htm",
                    },
                    {
                        "date": "2026-07-15",
                        "event_type": "insider_cluster",
                        "title": "NVIDIA insider activity",
                        "description": "Multiple insider transactions",
                        "source": "SEC Form 4",
                        "priority": 6,
                        "category": "insider",
                    },
                ],
            },
            "AMD": {
                "ticker": "AMD",
                "events": [
                    {
                        "date": "2026-08-03",
                        "event_type": "price_movement",
                        "title": "AMD stock up",
                        "description": "AMD stock moved higher",
                        "source": "Market Data",
                        "priority": 7,
                        "category": "market",
                        "price": 175.0,
                        "change_pct": 4.0,
                        "accession": "amd-1",
                    }
                ],
            },
            "INTC": {
                "ticker": "INTC",
                "events": [
                    {
                        "date": "2026-08-01",
                        "event_type": "proxy_filing",
                        "title": "Intel proxy filed",
                        "description": "DEF 14A filing",
                        "source": "SEC DEF 14A",
                        "priority": 5,
                        "category": "governance",
                    }
                ],
            },
        },
        "summary": {"events_by_ticker": {"NVDA": 2, "AMD": 1, "INTC": 1}, "total_events": 4},
    }


def _compare_price_fixture(ticker):
    return {
        "ticker": ticker,
        "bars": [
            {"date": "2026-08-01", "close": 100 + len(ticker), "volume": 1000 + len(ticker)},
            {"date": "2026-08-02", "close": 101 + len(ticker), "volume": 1100 + len(ticker)},
        ],
    }


def client():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
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


def test_timeline_route_happy_path_and_response_contract(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", lambda *args, **kwargs: _timeline_fixture())
    monkeypatch.setattr(intelligence_api, "get_price_history", lambda *args, **kwargs: _price_fixture())

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA?years=2&include_price=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "NVDA"
    assert payload["entity_name"] == "NVIDIA Corporation"
    assert set(payload["period"].keys()) == {"start", "end"}
    assert payload["partial"] is False
    assert payload["warnings"] == []
    assert len(payload["events"]) == 3
    event = payload["events"][0]
    assert set(event.keys()) >= {"id", "date", "category", "title", "description", "significance", "source", "source_url"}
    assert event["category"] == "financial"
    assert event["significance"] == 8
    assert event["related_price"]["close"] == 140.25
    assert len(payload["price_series"]) == 2
    assert payload["price_series"][0] == {"date": "2026-07-31", "close": 133.5, "volume": 1000}
    assert payload["summary"]["total_events"] == 3
    assert payload["summary"]["by_category"]["financial"] == 1
    assert len(payload["summary"]["most_significant"]) == 3


def test_timeline_route_category_filtering(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", False)
    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", lambda *args, **kwargs: _timeline_fixture())

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA?categories= financial , insider ")

    assert response.status_code == 200
    payload = response.json()
    assert [event["category"] for event in payload["events"]] == ["financial", "insider"]
    assert payload["summary"]["total_events"] == 2
    assert "market" not in payload["summary"]["by_category"]


def test_timeline_route_significance_filtering(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", False)
    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", lambda *args, **kwargs: _timeline_fixture())

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA?significance_min=7")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["events"]) == 1
    assert payload["events"][0]["significance"] == 8
    assert payload["summary"]["total_events"] == 1


def test_timeline_route_years_validation(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    test_client = next(client())

    assert test_client.get("/intelligence/timeline/NVDA?years=0").status_code == 422
    assert test_client.get("/intelligence/timeline/NVDA?years=6").status_code == 422
    assert test_client.get("/intelligence/timeline/NVDA?significance_min=10").status_code == 422


def test_timeline_route_include_price_false_skips_price_fetch(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", lambda *args, **kwargs: _timeline_fixture())
    calls = {"count": 0}

    def fake_price_history(*args, **kwargs):
        calls["count"] += 1
        return _price_fixture()

    monkeypatch.setattr(intelligence_api, "get_price_history", fake_price_history)

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA?include_price=false")

    assert response.status_code == 200
    payload = response.json()
    assert payload["price_series"] == []
    assert calls["count"] == 0


def test_timeline_route_include_price_true_with_missing_price_is_partial(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", lambda *args, **kwargs: _timeline_fixture())
    monkeypatch.setattr(intelligence_api, "get_price_history", lambda *args, **kwargs: {"bars": []})

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA?include_price=true")

    assert response.status_code == 200
    payload = response.json()
    assert payload["partial"] is True
    assert payload["price_series"] == []
    assert payload["warnings"][0]["source"] == "price_series"


def test_timeline_route_invalid_ticker_or_unusable_response(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", lambda *args, **kwargs: {"error": "Could not resolve CIK for BAD"})

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/BAD")
    assert response.status_code == 422

    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", lambda *args, **kwargs: {"ticker": "NVDA"})
    response = test_client.get("/intelligence/timeline/NVDA")
    assert response.status_code == 502


def test_timeline_route_bounded_timeout(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_TIMELINE_ROUTE_TIMEOUT_SECONDS", 0.05)

    def slow_timeline(*args, **kwargs):
        time.sleep(0.2)
        return _timeline_fixture()

    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", slow_timeline)

    test_client = next(client())
    started = time.perf_counter()
    response = test_client.get("/intelligence/timeline/NVDA")
    elapsed = time.perf_counter() - started

    assert response.status_code == 504
    assert elapsed < 0.16


def test_timeline_route_slow_optional_source_returns_partial_not_504(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", True)
    monkeypatch.setattr(
        intelligence_api,
        "_TIMELINE_INTERACTIVE_SOURCE_TIMEOUTS",
        {
            "sec_filings": 0.1,
            "8k_events": 0.1,
            "stock_events": 0.1,
            "insider_events": 0.1,
            "8k_enrichment": 0.05,
        },
    )
    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", timeline_connector.generate_entity_timeline)
    monkeypatch.setattr(intelligence_api, "get_price_history", lambda *args, **kwargs: _price_fixture())
    monkeypatch.setattr(timeline_connector, "_get_cik_from_ticker", lambda ticker: "0001045810")
    monkeypatch.setattr(
        timeline_connector,
        "_fetch_sec_filings",
        lambda *args, **kwargs: [
            {
                "date": "2026-08-01",
                "event_type": "sec_filing",
                "form_type": "8-K",
                "title": "Material Event (8-K)",
                "description": "Material event filing",
                "entity": "NVIDIA Corporation",
                "source": "SEC EDGAR",
                "priority": 8,
                "category": "financial",
                "accession": "0001",
                "document": "filing.htm",
            }
        ],
    )
    monkeypatch.setattr(timeline_connector, "_fetch_8k_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(timeline_connector, "_fetch_stock_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(timeline_connector, "_fetch_insider_transactions", lambda *args, **kwargs: [])

    def slow_enrichment(cik, events, max_filings=40):
        time.sleep(0.2)
        events[0]["title"] = "Enriched 8-K Event"
        return events

    monkeypatch.setattr(timeline_connector, "enrich_8k_items", slow_enrichment)

    test_client = next(client())
    started = time.perf_counter()
    response = test_client.get("/intelligence/timeline/NVDA?years=2&include_price=true")
    elapsed = time.perf_counter() - started

    assert response.status_code == 200
    assert elapsed < 0.18
    payload = response.json()
    assert payload["partial"] is True
    assert payload["events"][0]["title"] == "Material Event (8-K)"
    assert any(item["source"] == "8k_enrichment" and item["code"] == "timeout" for item in payload["warnings"])


def test_existing_intelligence_routes_remain_registered(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    paths = app.openapi().get("paths", {})
    assert "/intelligence/timeline/{ticker}" in paths
    assert "/intelligence/timeline/{ticker}/compare" in paths
    assert "/intelligence/" in paths
    assert "/intelligence/{report_id}" in paths


def test_compare_timeline_happy_path_and_contract(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "compare_entity_timelines", lambda *args, **kwargs: _compare_timeline_fixture())
    monkeypatch.setattr(intelligence_api, "get_price_history", lambda ticker, **kwargs: _compare_price_fixture(ticker))

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA/compare?against=AMD,INTC&years=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["primary_ticker"] == "NVDA"
    assert payload["tickers"] == ["NVDA", "AMD", "INTC"]
    assert set(payload["period"].keys()) == {"start", "end"}
    assert payload["partial"] is False
    assert len(payload["events"]) == 4
    assert payload["events"][0]["ticker"] == "NVDA"
    assert payload["events"][1]["ticker"] == "AMD"
    assert all("ticker" in event for event in payload["events"])
    assert len(payload["price_series"]) == 3
    assert payload["price_series"][0]["ticker"] == "NVDA"
    assert payload["summary"]["total_events"] == 4
    assert payload["summary"]["by_ticker"] == {"NVDA": 2, "AMD": 1, "INTC": 1}
    assert payload["summary"]["by_category"]["financial"] == 1
    assert len(payload["summary"]["most_significant"]) == 4


def test_compare_timeline_normalizes_comparators(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", True)
    seen = {}

    def fake_compare(tickers, years):
        seen["tickers"] = tickers
        return {
            "tickers": tickers,
            "timelines": {ticker: {"ticker": ticker, "events": []} for ticker in tickers},
            "summary": {"events_by_ticker": {ticker: 0 for ticker in tickers}, "total_events": 0},
        }

    monkeypatch.setattr(intelligence_api, "compare_entity_timelines", fake_compare)
    monkeypatch.setattr(intelligence_api, "get_price_history", lambda ticker, **kwargs: _compare_price_fixture(ticker))

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA/compare?against= amd , nvda, INTC , amd ")

    assert response.status_code == 200
    assert seen["tickers"] == ["NVDA", "AMD", "INTC"]
    assert response.json()["warnings"] == []


def test_compare_timeline_caps_to_five_and_warns_on_malformed(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", True)
    seen = {}

    def fake_compare(tickers, years):
        seen["tickers"] = tickers
        return {
            "tickers": tickers,
            "timelines": {ticker: {"ticker": ticker, "events": []} for ticker in tickers},
            "summary": {"events_by_ticker": {ticker: 0 for ticker in tickers}, "total_events": 0},
        }

    monkeypatch.setattr(intelligence_api, "compare_entity_timelines", fake_compare)
    monkeypatch.setattr(intelligence_api, "get_price_history", lambda ticker, **kwargs: _compare_price_fixture(ticker))

    test_client = next(client())
    response = test_client.get(
        "/intelligence/timeline/NVDA/compare?against=amd,bad!,intc,msft,googl,orcl,meta,tsla"
    )

    assert response.status_code == 200
    assert seen["tickers"] == ["NVDA", "AMD", "INTC", "MSFT", "GOOGL", "ORCL"]
    warnings = response.json()["warnings"]
    assert any(item["code"] == "malformed_ticker" for item in warnings)
    assert any(item["code"] == "limit_applied" for item in warnings)


def test_compare_timeline_partial_when_one_ticker_is_unusable(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", True)
    payload = _compare_timeline_fixture()
    payload["timelines"]["AMD"] = {"error": "provider exploded internally with traceback"}
    monkeypatch.setattr(intelligence_api, "compare_entity_timelines", lambda *args, **kwargs: payload)
    monkeypatch.setattr(intelligence_api, "get_price_history", lambda ticker, **kwargs: _compare_price_fixture(ticker))

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA/compare?against=AMD,INTC")

    assert response.status_code == 200
    body = response.json()
    assert body["partial"] is True
    assert body["tickers"] == ["NVDA", "INTC"]
    assert body["summary"]["by_ticker"]["NVDA"] == 2
    assert body["summary"]["by_ticker"]["INTC"] == 1
    assert any(item["code"] == "ticker_unavailable" for item in body["warnings"])
    assert all("traceback" not in item["detail"].lower() for item in body["warnings"])


def test_compare_timeline_no_valid_comparators_is_422(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA/compare?against=bad!,###,nvda")

    assert response.status_code == 422


def test_compare_timeline_price_failure_is_partial(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "compare_entity_timelines", lambda *args, **kwargs: _compare_timeline_fixture())

    def flaky_price_history(ticker, **kwargs):
        if ticker == "AMD":
            raise RuntimeError("price down")
        return _compare_price_fixture(ticker)

    monkeypatch.setattr(intelligence_api, "get_price_history", flaky_price_history)

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA/compare?against=AMD,INTC")

    assert response.status_code == 200
    body = response.json()
    assert body["partial"] is True
    amd_series = next(item for item in body["price_series"] if item["ticker"] == "AMD")
    assert amd_series["points"] == []
    assert any(item["source"] == "price_series" for item in body["warnings"])


def test_compare_timeline_bounded_timeout(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_TIMELINE_ROUTE_TIMEOUT_SECONDS", 0.05)

    def slow_compare(*args, **kwargs):
        time.sleep(0.2)
        return _compare_timeline_fixture()

    monkeypatch.setattr(intelligence_api, "compare_entity_timelines", slow_compare)

    test_client = next(client())
    started = time.perf_counter()
    response = test_client.get("/intelligence/timeline/NVDA/compare?against=AMD")
    elapsed = time.perf_counter() - started

    assert response.status_code == 504
    assert elapsed < 0.16


def test_single_ticker_route_still_works_after_compare_addition(monkeypatch):
    monkeypatch.setattr(intelligence_api, "_TIMELINE_AVAILABLE", True)
    monkeypatch.setattr(intelligence_api, "_PRICE_HISTORY_AVAILABLE", False)
    monkeypatch.setattr(intelligence_api, "generate_entity_timeline", lambda *args, **kwargs: _timeline_fixture())

    test_client = next(client())
    response = test_client.get("/intelligence/timeline/NVDA")

    assert response.status_code == 200
    assert response.json()["ticker"] == "NVDA"
