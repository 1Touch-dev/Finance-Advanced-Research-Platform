import json
import os
from pathlib import Path
import sys
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)
FINANCE_PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "finance"))
if FINANCE_PKG not in sys.path:
    sys.path.insert(0, FINANCE_PKG)

from app.db.session import get_db
from app.main import app
from app.models.base import Base
import app.models.market_13f_cache as market_13f_cache
from app.models.market_13f_schemas import PositionDiffDataQuality, PositionSnapshotEntry
from app.services import sec_13f_service
from app.services.sec_13f_service import (
    ParsedSEC13FFiling,
    ParsedSEC13FMetadata,
    SEC13FFilingRecord,
    SEC13FPeriodSnapshot,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "sec_13f"


def _fixture_path_from_url(url: str) -> Path:
    normalized = url.replace("https://", "").replace("http://", "")
    return FIXTURE_ROOT.joinpath(*normalized.split("/"))


def _fixture_json_fetcher(url: str):
    return json.loads(_fixture_path_from_url(url).read_text())


def _fixture_text_fetcher(url: str):
    return _fixture_path_from_url(url).read_text()


def _snapshot(period: date, accession: str, positions: list[PositionSnapshotEntry]) -> SEC13FPeriodSnapshot:
    filing = ParsedSEC13FFiling(
        metadata=ParsedSEC13FMetadata(
            cik="0001067983",
            accession_number=accession,
            form="13F-HR",
            filing_date=date(2026, 5, 15),
            report_period=period,
            filing_manager_name="Example Capital Management",
            is_amendment=False,
            amendment_type=None,
            amendment_no=None,
            is_confidential_omitted=False,
        ),
        positions=positions,
    )
    return SEC13FPeriodSnapshot(
        institution_name="Example Capital Management",
        cik="0001067983",
        report_period=period,
        primary_filing=filing,
        positions=positions,
    )


@pytest.fixture
def client_and_session():
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
        with TestClient(app) as client:
            yield client, TestingSessionLocal
    finally:
        app.dependency_overrides.clear()


def test_position_diff_success_response_includes_filings_warnings_and_quality(client_and_session, monkeypatch):
    client, _ = client_and_session
    monkeypatch.setattr(sec_13f_service, "_requests_json_fetcher", _fixture_json_fetcher)
    monkeypatch.setattr(sec_13f_service, "_requests_text_fetcher", _fixture_text_fetcher)

    response = client.get(
        "/market/institutional/position-diff",
        params={
            "institution_cik": "1067983",
            "current_period": "2026-03-31",
            "previous_period": "2025-12-31",
            "status": "all",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["institution"]["cik"] == "0001067983"
    assert payload["filings"]["current"]["accession_number"] == "0001067983-26-000011"
    assert len(payload["filings"]["current_supplemental_amendments"]) == 2
    assert payload["summary"]["new_count"] == 4
    assert payload["summary"]["exited_count"] == 1
    assert payload["warnings"][0]["code"] == "confidential_omissions_possible"
    assert payload["data_quality"]["confidential_omissions_possible"] is True


def test_position_diff_cache_miss_then_cache_hit_without_duplicate_sec_calls(client_and_session, monkeypatch):
    client, _ = client_and_session
    calls = {"json": 0, "text": 0}

    def counting_json_fetcher(url: str):
        calls["json"] += 1
        return _fixture_json_fetcher(url)

    def counting_text_fetcher(url: str):
        calls["text"] += 1
        return _fixture_text_fetcher(url)

    monkeypatch.setattr(sec_13f_service, "_requests_json_fetcher", counting_json_fetcher)
    monkeypatch.setattr(sec_13f_service, "_requests_text_fetcher", counting_text_fetcher)

    params = {
        "institution_cik": "1067983",
        "current_period": "2026-03-31",
        "previous_period": "2025-12-31",
        "status": "all",
    }
    first = client.get("/market/institutional/position-diff", params=params)
    assert first.status_code == 200
    first_counts = calls.copy()
    assert first_counts["json"] == 8
    assert first_counts["text"] == 12

    second = client.get("/market/institutional/position-diff", params=params)
    assert second.status_code == 200
    assert calls == first_counts


def test_position_diff_offline_cache_fallback_returns_cached_response(client_and_session, monkeypatch):
    client, _ = client_and_session
    monkeypatch.setattr(sec_13f_service, "_requests_json_fetcher", _fixture_json_fetcher)
    monkeypatch.setattr(sec_13f_service, "_requests_text_fetcher", _fixture_text_fetcher)

    params = {
        "institution_cik": "1067983",
        "current_period": "2026-03-31",
        "previous_period": "2025-12-31",
        "status": "all",
    }
    prime = client.get("/market/institutional/position-diff", params=params)
    assert prime.status_code == 200

    def failing_json_fetcher(url: str):
        raise requests.RequestException(url)

    def failing_text_fetcher(url: str):
        raise requests.RequestException(url)

    import requests

    monkeypatch.setattr(sec_13f_service, "_requests_json_fetcher", failing_json_fetcher)
    monkeypatch.setattr(sec_13f_service, "_requests_text_fetcher", failing_text_fetcher)

    cached = client.get("/market/institutional/position-diff", params=params)
    assert cached.status_code == 200
    assert cached.json()["filings"]["current"]["accession_number"] == "0001067983-26-000011"


def test_position_diff_empty_result_is_returned_cleanly(client_and_session, monkeypatch):
    client, _ = client_and_session

    current = [
        PositionSnapshotEntry(
            issuer_name="Same Co",
            cusip="333333333",
            security_title="COM",
            shares=5,
            reported_value_usd=50,
            accession_number="0001067983-26-000100",
            filing_date=date(2026, 5, 15),
        )
    ]

    filing_records = [
        SEC13FFilingRecord(
            cik="0001067983",
            accession_number="0001067983-26-000100",
            form="13F-HR",
            filing_date=date(2026, 5, 15),
            report_period=date(2026, 3, 31),
        ),
        SEC13FFilingRecord(
            cik="0001067983",
            accession_number="0001067983-25-000099",
            form="13F-HR",
            filing_date=date(2026, 2, 14),
            report_period=date(2025, 12, 31),
        ),
    ]

    monkeypatch.setattr(sec_13f_service, "fetch_13f_filing_records", lambda *args, **kwargs: filing_records)
    monkeypatch.setattr(
        sec_13f_service,
        "build_13f_reporting_period_snapshot",
        lambda records, **kwargs: _snapshot(records[0].report_period, records[0].accession_number, current),
    )

    response = client.get(
        "/market/institutional/position-diff",
        params={
            "institution_cik": "1067983",
            "current_period": "2026-03-31",
            "previous_period": "2025-12-31",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["positions"] == []
    assert payload["pagination"]["total_matching"] == 0
    assert payload["summary"]["unchanged_count"] == 1


def test_position_diff_invalid_cik_returns_422(client_and_session):
    client, _ = client_and_session
    response = client.get("/market/institutional/position-diff", params={"institution_cik": "abc"})
    assert response.status_code == 422


def test_position_diff_invalid_report_period_returns_422(client_and_session):
    client, _ = client_and_session
    response = client.get(
        "/market/institutional/position-diff",
        params={
            "institution_cik": "1067983",
            "current_period": "2026-04-01",
            "previous_period": "2025-12-31",
        },
    )
    assert response.status_code == 422


def test_position_diff_missing_required_parameter_returns_422(client_and_session):
    client, _ = client_and_session
    response = client.get("/market/institutional/position-diff")
    assert response.status_code == 422


def test_position_diff_invalid_sort_option_returns_422(client_and_session):
    client, _ = client_and_session
    response = client.get(
        "/market/institutional/position-diff",
        params={"institution_cik": "1067983", "sort_by": "not_a_sort"},
    )
    assert response.status_code == 422


def test_position_diff_invalid_pagination_returns_422(client_and_session):
    client, _ = client_and_session
    response = client.get(
        "/market/institutional/position-diff",
        params={"institution_cik": "1067983", "limit": 999},
    )
    assert response.status_code == 422


def test_position_diff_filing_not_found_returns_404(client_and_session, monkeypatch):
    client, _ = client_and_session
    monkeypatch.setattr(sec_13f_service, "_requests_json_fetcher", _fixture_json_fetcher)
    monkeypatch.setattr(sec_13f_service, "_requests_text_fetcher", _fixture_text_fetcher)

    response = client.get(
        "/market/institutional/position-diff",
        params={
            "institution_cik": "1067983",
            "current_period": "2024-03-31",
            "previous_period": "2023-12-31",
        },
    )
    assert response.status_code == 404


def test_position_diff_sec_failure_with_no_cache_returns_503(client_and_session, monkeypatch):
    client, _ = client_and_session

    import requests

    def failing_json_fetcher(url: str):
        raise requests.RequestException(url)

    monkeypatch.setattr(sec_13f_service, "_requests_json_fetcher", failing_json_fetcher)

    response = client.get(
        "/market/institutional/position-diff",
        params={
            "institution_cik": "1067983",
            "current_period": "2026-03-31",
            "previous_period": "2025-12-31",
        },
    )
    assert response.status_code == 503


def test_position_diff_default_order_is_stable_for_equal_diffs(client_and_session, monkeypatch):
    client, _ = client_and_session
    current_positions = [
        PositionSnapshotEntry(
            issuer_name="Buyer A",
            cusip="111111111",
            security_title="COM",
            shares=10,
            reported_value_usd=100,
            accession_number="0001067983-26-000101",
            filing_date=date(2026, 5, 15),
        ),
        PositionSnapshotEntry(
            issuer_name="Buyer B",
            cusip="222222222",
            security_title="COM",
            shares=10,
            reported_value_usd=100,
            accession_number="0001067983-26-000101",
            filing_date=date(2026, 5, 15),
        ),
    ]
    previous_positions: list[PositionSnapshotEntry] = []

    filing_records = [
        SEC13FFilingRecord(
            cik="0001067983",
            accession_number="0001067983-26-000101",
            form="13F-HR",
            filing_date=date(2026, 5, 15),
            report_period=date(2026, 3, 31),
        ),
        SEC13FFilingRecord(
            cik="0001067983",
            accession_number="0001067983-25-000099",
            form="13F-HR",
            filing_date=date(2026, 2, 14),
            report_period=date(2025, 12, 31),
        ),
    ]

    monkeypatch.setattr(sec_13f_service, "fetch_13f_filing_records", lambda *args, **kwargs: filing_records)

    def fake_build_snapshot(records, **kwargs):
        record = records[0]
        if record.report_period == date(2026, 3, 31):
            return _snapshot(record.report_period, record.accession_number, current_positions)
        return _snapshot(record.report_period, record.accession_number, previous_positions)

    monkeypatch.setattr(sec_13f_service, "build_13f_reporting_period_snapshot", fake_build_snapshot)

    params = {
        "institution_cik": "1067983",
        "current_period": "2026-03-31",
        "previous_period": "2025-12-31",
        "status": "all",
    }
    first = client.get("/market/institutional/position-diff", params=params)
    second = client.get("/market/institutional/position-diff", params=params)
    assert first.status_code == 200
    assert second.status_code == 200
    assert [item["issuer_name"] for item in first.json()["positions"]] == ["Buyer A", "Buyer B"]
    assert [item["issuer_name"] for item in second.json()["positions"]] == ["Buyer A", "Buyer B"]


def test_position_diff_preserves_current_and_previous_data_quality_flags(client_and_session, monkeypatch):
    client, _ = client_and_session
    filing_records = [
        SEC13FFilingRecord(
            cik="0001067983",
            accession_number="0001067983-26-000201",
            form="13F-HR",
            filing_date=date(2026, 5, 15),
            report_period=date(2026, 3, 31),
        ),
        SEC13FFilingRecord(
            cik="0001067983",
            accession_number="0001067983-25-000199",
            form="13F-HR",
            filing_date=date(2026, 2, 14),
            report_period=date(2025, 12, 31),
        ),
    ]

    monkeypatch.setattr(sec_13f_service, "fetch_13f_filing_records", lambda *args, **kwargs: filing_records)

    def fake_build_snapshot(records, **kwargs):
        record = records[0]
        snapshot = _snapshot(record.report_period, record.accession_number, [])
        if record.report_period == date(2026, 3, 31):
            return SEC13FPeriodSnapshot(
                institution_name=snapshot.institution_name,
                cik=snapshot.cik,
                report_period=snapshot.report_period,
                primary_filing=snapshot.primary_filing,
                positions=snapshot.positions,
                data_quality=PositionDiffDataQuality(
                    comparison_complete=True,
                    current_filing_complete=True,
                    previous_filing_complete=True,
                    ticker_enrichment_complete=True,
                    confidential_omissions_possible=False,
                ),
            )
        return SEC13FPeriodSnapshot(
            institution_name=snapshot.institution_name,
            cik=snapshot.cik,
            report_period=snapshot.report_period,
            primary_filing=snapshot.primary_filing,
            positions=snapshot.positions,
            data_quality=PositionDiffDataQuality(
                comparison_complete=True,
                current_filing_complete=False,
                previous_filing_complete=False,
                ticker_enrichment_complete=True,
                confidential_omissions_possible=False,
            ),
        )

    monkeypatch.setattr(sec_13f_service, "build_13f_reporting_period_snapshot", fake_build_snapshot)

    response = client.get(
        "/market/institutional/position-diff",
        params={
            "institution_cik": "1067983",
            "current_period": "2026-03-31",
            "previous_period": "2025-12-31",
            "status": "all",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_quality"]["current_filing_complete"] is True
    assert payload["data_quality"]["previous_filing_complete"] is False
