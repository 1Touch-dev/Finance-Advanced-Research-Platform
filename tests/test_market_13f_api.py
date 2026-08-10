import os
import sys
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

from app.db.session import get_db
from app.main import app as fastapi_app
from app.models.base import Base
import app.models.entities  # noqa: F401
import app.models.market_13f_cache as market_13f_cache
import app.models.monitor  # noqa: F401
import app.models.reports  # noqa: F401
import app.models.sources  # noqa: F401
from app.models.market_13f_schemas import PositionSnapshotEntry
from app.services import sec_13f_service
from app.services.sec_13f_service import (
    ParsedSEC13FFiling,
    ParsedSEC13FMetadata,
    SEC13FFilingRecord,
    SEC13FPeriodSnapshot,
    _build_13f_freshness,
    extract_13f_filing_records,
    load_13f_filing,
    select_reporting_period_pair,
)


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


def _snapshot_with_filing_date(filing_date: date | None) -> SEC13FPeriodSnapshot:
    filing = ParsedSEC13FFiling(
        metadata=ParsedSEC13FMetadata(
            cik="0001067983",
            accession_number="0001067983-26-000101",
            form="13F-HR",
            filing_date=filing_date,
            report_period=date(2026, 3, 31),
            filing_manager_name="Example Capital Management",
            is_amendment=False,
            amendment_type=None,
            amendment_no=None,
            is_confidential_omitted=False,
        ),
        positions=[],
    )
    return SEC13FPeriodSnapshot(
        institution_name="Example Capital Management",
        cik="0001067983",
        report_period=date(2026, 3, 31),
        primary_filing=filing,
        positions=[],
    )


def _filing_record(
    *,
    accession_number: str = "0001067983-26-000101",
    form: str = "13F-HR",
    primary_document: str | None = "primary.xml",
) -> SEC13FFilingRecord:
    return SEC13FFilingRecord(
        cik="0001067983",
        accession_number=accession_number,
        form=form,
        filing_date=date(2026, 5, 15),
        report_period=date(2026, 3, 31),
        primary_document=primary_document,
    )


def _archive_index(*items: dict) -> dict:
    return {"directory": {"item": list(items)}}


def _primary_xml(*, amendment: bool = False, amendment_type: str | None = None) -> str:
    amendment_xml = ""
    if amendment:
        amendment_xml = f"""
          <isAmendment>true</isAmendment>
          <amendmentInfo>
            <amendmentType>{amendment_type or "NEW HOLDINGS"}</amendmentType>
            <amendmentNo>1</amendmentNo>
          </amendmentInfo>
        """
    return f"""
    <edgarSubmission>
      <formData>
        <coverPage>
          <reportCalendarOrQuarter>2026-03-31</reportCalendarOrQuarter>
          <filingManager><name>Example Capital Management</name></filingManager>
          {amendment_xml}
        </coverPage>
        <summaryPage><isConfidentialOmitted>false</isConfidentialOmitted></summaryPage>
      </formData>
    </edgarSubmission>
    """


def _information_table_xml(*, namespace: bool = False, issuer: str = "Apple Inc") -> str:
    xmlns = ' xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable"' if namespace else ""
    return f"""
    <informationTable{xmlns}>
      <infoTable>
        <nameOfIssuer>{issuer}</nameOfIssuer>
        <titleOfClass>COM</titleOfClass>
        <cusip>037833100</cusip>
        <value>150000000</value>
        <shrsOrPrnAmt>
          <sshPrnamt>25</sshPrnamt>
          <sshPrnamtType>SH</sshPrnamtType>
        </shrsOrPrnAmt>
      </infoTable>
    </informationTable>
    """


def _load_with_archive(index_json: dict, files: dict[str, str], *, record: SEC13FFilingRecord | None = None):
    filing_record = record or _filing_record()

    def json_fetcher(_url):
        return index_json

    def text_fetcher(url):
        name = url.rsplit("/", 1)[-1]
        return files[name]

    return load_13f_filing(filing_record, json_fetcher=json_fetcher, text_fetcher=text_fetcher)


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

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(fastapi_app) as client:
            yield client, TestingSessionLocal
    finally:
        fastapi_app.dependency_overrides.clear()


def test_position_diff_response_includes_13f_freshness(client_and_session, monkeypatch):
    client, _ = client_and_session
    current_positions = [
        PositionSnapshotEntry(
            issuer_name="Fresh Co",
            cusip="111111111",
            security_title="COM",
            shares=10,
            reported_value_usd=100,
            accession_number="0001067983-26-000101",
            filing_date=date(2026, 5, 15),
        )
    ]
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
        positions = current_positions if record.report_period == date(2026, 3, 31) else []
        return _snapshot(record.report_period, record.accession_number, positions)

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
    assert payload["freshness"]["as_of_date"] == "2026-03-31"
    assert payload["freshness"]["filing_date"] == "2026-05-15"
    assert payload["freshness"]["threshold_days"] == 45
    assert payload["freshness"]["status"] in {"fresh", "stale"}


def test_13f_freshness_rules_cover_fresh_stale_unknown_and_future(monkeypatch):
    monkeypatch.delenv("SOURCE_MAX_AGE_DAYS", raising=False)

    fresh = _build_13f_freshness(_snapshot_with_filing_date(date.today() - timedelta(days=45)))
    stale = _build_13f_freshness(_snapshot_with_filing_date(date.today() - timedelta(days=46)))
    missing = _build_13f_freshness(_snapshot_with_filing_date(None))
    future = _build_13f_freshness(_snapshot_with_filing_date(date.today() + timedelta(days=1)))

    assert fresh.status == "fresh"
    assert fresh.age_days == 45
    assert stale.status == "stale"
    assert missing.status == "stale"
    assert missing.filing_date is None
    assert future.status == "unknown"


def test_13f_freshness_invalid_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("SOURCE_MAX_AGE_DAYS", "not-a-number")
    result = _build_13f_freshness(_snapshot_with_filing_date(date.today()))

    assert result.threshold_days == 45
    assert result.status == "fresh"


def test_13f_archive_information_table_detected_by_document_metadata():
    filing = _load_with_archive(
        _archive_index(
            {"name": "primary.xml"},
            {"name": "holdings-document.xml", "type": "INFORMATION TABLE"},
        ),
        {
            "primary.xml": _primary_xml(),
            "holdings-document.xml": _information_table_xml(),
        },
    )

    assert filing.metadata.filing_manager_name == "Example Capital Management"
    assert filing.positions[0].issuer_name == "Apple Inc"
    assert filing.positions[0].reported_value_usd == 150000000


def test_13f_archive_information_table_detected_by_content_with_nonstandard_filename():
    filing = _load_with_archive(
        _archive_index(
            {"name": "primary.xml"},
            {"name": "manager-holdings.xml"},
        ),
        {
            "primary.xml": _primary_xml(),
            "manager-holdings.xml": _information_table_xml(issuer="Microsoft Corp"),
        },
    )

    assert filing.positions[0].issuer_name == "Microsoft Corp"


def test_13f_archive_information_table_supports_namespace_and_mixed_case_filename():
    filing = _load_with_archive(
        _archive_index(
            {"name": "PRIMARY.XML"},
            {"name": "INFO-TABLE.XML"},
        ),
        {
            "PRIMARY.XML": _primary_xml(),
            "INFO-TABLE.XML": _information_table_xml(namespace=True),
        },
        record=_filing_record(primary_document="PRIMARY.XML"),
    )

    assert filing.positions[0].cusip == "037833100"


def test_13f_archive_primary_xml_is_not_selected_as_information_table():
    filing = _load_with_archive(
        _archive_index(
            {"name": "primary.xml", "description": "PRIMARY DOCUMENT"},
            {"name": "filing-detail.xml"},
            {"name": "supporting.xml", "description": "INFORMATION TABLE"},
        ),
        {
            "primary.xml": _primary_xml(),
            "filing-detail.xml": "<edgarSubmission><formData /></edgarSubmission>",
            "supporting.xml": _information_table_xml(issuer="Nvidia Corp"),
        },
    )

    assert filing.positions[0].issuer_name == "Nvidia Corp"
    assert filing.metadata.accession_number == "0001067983-26-000101"


def test_13f_archive_rejects_invalid_xml_candidates_and_uses_valid_table():
    filing = _load_with_archive(
        _archive_index(
            {"name": "primary.xml"},
            {"name": "informationtable.xml"},
            {"name": "zz-alt.xml"},
        ),
        {
            "primary.xml": _primary_xml(),
            "informationtable.xml": "<notInformationTable />",
            "zz-alt.xml": _information_table_xml(issuer="Alphabet Inc"),
        },
    )

    assert filing.positions[0].issuer_name == "Alphabet Inc"


def test_13f_archive_amendment_with_valid_information_table_is_loaded():
    filing = _load_with_archive(
        _archive_index(
            {"name": "amendment-primary.xml"},
            {"name": "supplemental.xml", "description": "Information Table"},
        ),
        {
            "amendment-primary.xml": _primary_xml(amendment=True, amendment_type="NEW HOLDINGS"),
            "supplemental.xml": _information_table_xml(issuer="Tesla Inc"),
        },
        record=_filing_record(
            accession_number="0001067983-26-000102",
            form="13F-HR/A",
            primary_document="amendment-primary.xml",
        ),
    )

    assert filing.metadata.is_amendment is True
    assert filing.metadata.amendment_type == "NEW HOLDINGS"
    assert filing.positions[0].issuer_name == "Tesla Inc"


def test_13f_archive_without_valid_information_table_returns_controlled_error():
    with pytest.raises(ValueError, match="valid information-table XML document"):
        _load_with_archive(
            _archive_index(
                {"name": "primary.xml"},
                {"name": "schema.xml"},
                {"name": "supporting.xml"},
            ),
            {
                "primary.xml": _primary_xml(),
                "schema.xml": "<schema />",
                "supporting.xml": "<supportingDocument />",
            },
        )


def test_13f_submission_discovery_skips_malformed_report_dates_without_weakening_user_validation():
    submissions = {
        "cik": "1067983",
        "filings": {
            "recent": {
                "form": ["13F-HR", "13F-HR", "13F-HR"],
                "filingDate": ["2026-07-15", "2026-05-15", "2026-02-14"],
                "accessionNumber": [
                    "0001067983-26-000200",
                    "0001067983-26-000101",
                    "0001067983-25-000099",
                ],
                "reportDate": ["2026-07-08", "2026-03-31", "2025-12-31"],
                "primaryDocument": ["bad.xml", "primary.xml", "primary.xml"],
            }
        },
    }

    records = extract_13f_filing_records(submissions, cik="1067983")

    assert [record.report_period for record in records] == [date(2026, 3, 31), date(2025, 12, 31)]
    assert select_reporting_period_pair(records) == (date(2026, 3, 31), date(2025, 12, 31))
    with pytest.raises(ValueError, match="calendar quarter end"):
        select_reporting_period_pair(records, current_period="2026-07-08")


def test_institutional_exposure_search_is_cache_backed(client_and_session):
    client, TestingSessionLocal = client_and_session
    with TestingSessionLocal() as db:
        period = market_13f_cache.Institutional13FPeriodCache(
            institution_cik="0001067983",
            report_period=date(2026, 3, 31),
            institution_name="Example Capital Management",
            primary_accession_number="0001067983-26-000101",
            primary_form="13F-HR",
            primary_filing_date=date(2026, 5, 15),
        )
        period.positions = [
            market_13f_cache.Institutional13FPositionCache(
                sort_order=0,
                issuer_name="Apple Inc",
                ticker="AAPL",
                cusip="037833100",
                security_title="COM",
                shares=25,
                reported_value_usd=500,
                accession_number="0001067983-26-000101",
                filing_date=date(2026, 5, 15),
            )
        ]
        db.add(period)
        db.commit()

    response = client.get("/market/institutional/exposure", params={"ticker": "AAPL"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_source"] == "institutional_13f_cache"
    assert payload["pagination"]["total_matching"] == 1
    assert payload["results"][0]["institution_cik"] == "0001067983"
    assert payload["results"][0]["issuer_name"] == "Apple Inc"


def test_institutional_exposure_empty_cache_and_invalid_cik_are_controlled(client_and_session):
    client, _ = client_and_session

    empty = client.get("/market/institutional/exposure", params={"ticker": "AAPL"})
    invalid = client.get("/market/institutional/exposure", params={"institution_cik": "bad-cik"})

    assert empty.status_code == 200
    assert empty.json()["pagination"]["total_matching"] == 0
    assert empty.json()["results"] == []
    assert invalid.status_code == 422


def test_honesty_entity_returns_unknown_without_fabricated_sources(client_and_session):
    client, _ = client_and_session
    response = client.get("/honesty/entity/missing-entity")

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_staleness"] == "unknown"
    assert payload["data_sources"] == []
    assert "No verified source freshness metadata" in payload["disclaimers"][0]


def test_export_available_data_uses_database_counts(client_and_session):
    client, _ = client_and_session
    response = client.get("/export/available-data")

    assert response.status_code == 200
    payload = response.json()
    counts = {item["id"]: item["record_count"] for item in payload["data_types"]}
    assert counts["watchlists"] == 0
    assert counts["alerts"] == 0
    assert counts["reports"] == 0
    assert counts["entities"] == 0
    assert counts["tracking"] == 0


def test_openapi_keeps_13f_and_existing_market_routes_registered(client_and_session):
    client, _ = client_and_session
    paths = client.get("/openapi.json").json()["paths"]

    assert "/market/institutional/position-diff" in paths
    assert "/market/institutional/exposure" in paths
    assert "/market/quote" in paths
    assert "/market/yf/snapshot" in paths
