import json
import os
from pathlib import Path
import sys
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

from app.models.base import Base
import app.models.market_13f_cache  # noqa: F401
from app.models.market_13f_schemas import (
    PositionDiffDataQuality,
    PositionDiffFilterStatus,
    PositionDiffStatus,
    PositionSnapshotEntry,
)
from app.services.sec_13f_service import (
    SEC13FFilingRecord,
    PositionAmbiguityError,
    build_13f_reporting_period_snapshot,
    build_position_key,
    compare_position_snapshots,
    compute_share_pct_change,
    fetch_13f_filing_records,
    filter_filing_records_for_period,
    get_or_fetch_13f_period_snapshot,
    group_compatible_positions,
    identify_13f_xml_documents,
    load_13f_filing,
    load_13f_period_snapshot_from_cache,
    normalize_cik,
    normalize_cusip,
    normalize_issuer_name,
    normalize_put_call,
    normalize_reporting_period,
    normalize_security_title,
    parse_13f_information_table,
    select_reporting_period_pair,
    upsert_13f_period_snapshot_cache,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "sec_13f"


def _entry(**overrides):
    payload = {
        "issuer_name": "Apple Inc.",
        "ticker": "AAPL",
        "cusip": "037833100",
        "security_title": "COM",
        "put_call": None,
        "shares": 10,
        "reported_value_usd": 1000,
        "accession_number": "0000000000-26-000001",
        "filing_date": date(2026, 5, 15),
    }
    payload.update(overrides)
    return PositionSnapshotEntry(**payload)


def _fixture_path_from_url(url: str) -> Path:
    normalized = url.replace("https://", "").replace("http://", "")
    return FIXTURE_ROOT.joinpath(*normalized.split("/"))


def _fixture_json_fetcher(url: str):
    return json.loads(_fixture_path_from_url(url).read_text())


def _fixture_text_fetcher(url: str):
    return _fixture_path_from_url(url).read_text()


def _mock_json_fetcher_factory(mapping):
    def _fetch(url: str):
        return mapping[url]
    return _fetch


def _mock_text_fetcher_factory(mapping):
    def _fetch(url: str):
        return mapping[url]
    return _fetch


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()


def test_normalize_cik_zero_pads():
    assert normalize_cik("1067983") == "0001067983"


def test_normalize_reporting_period_accepts_supported_formats():
    assert normalize_reporting_period("2026-03-31") == date(2026, 3, 31)
    assert normalize_reporting_period("03-31-2026") == date(2026, 3, 31)


def test_normalize_reporting_period_rejects_non_quarter_end():
    with pytest.raises(ValueError):
        normalize_reporting_period("2026-04-01")


def test_value_normalizers_clean_inputs():
    assert normalize_cusip(" 037833-100 ") == "037833100"
    assert normalize_issuer_name("Apple, Inc.") == "APPLE INC"
    assert normalize_security_title("com ") == "COM"
    assert normalize_put_call(" put ") == "PUT"
    assert normalize_put_call("") is None


def test_build_position_key_uses_cusip_then_issuer_fallback():
    assert build_position_key(_entry()).startswith("cusip:037833100|")
    fallback = _entry(cusip=None, issuer_name="Alphabet Inc.", security_title="Class A")
    assert build_position_key(fallback).startswith("issuer:ALPHABET INC|")


def test_group_compatible_positions_aggregates_safe_duplicates():
    left = _entry(shares=10, reported_value_usd=100)
    right = _entry(shares=5, reported_value_usd=40, ticker=None, ticker_resolution_method="sec_name")
    result = group_compatible_positions([left, right])
    assert len(result.positions) == 1
    assert result.positions[0].shares == 15
    assert result.positions[0].reported_value_usd == 140
    assert result.ambiguous_groups == {}
    assert result.warnings[0].code == "aggregated_duplicate_group"


def test_group_compatible_positions_marks_material_conflict():
    left = _entry()
    right = _entry(ticker="MSFT")
    result = group_compatible_positions([left, right])
    assert len(result.positions) == 0
    assert len(result.ambiguous_groups) == 1
    assert result.warnings[0].code == "ambiguous_duplicate_group"


def test_compute_share_pct_change_rules():
    assert compute_share_pct_change(10, 0) is None
    assert compute_share_pct_change(0, 10) == -100.0
    assert compute_share_pct_change(0, 0) == 0.0
    assert compute_share_pct_change(15, 10) == 50.0


def test_compare_position_snapshots_assigns_all_statuses():
    current = [
        _entry(issuer_name="New Co", cusip="111111111", shares=10, reported_value_usd=100, ticker=None),
        _entry(issuer_name="Increase Co", cusip="222222222", shares=15, reported_value_usd=150),
        _entry(issuer_name="Same Co", cusip="333333333", shares=5, reported_value_usd=50),
        _entry(issuer_name="Reduce Co", cusip="444444444", shares=3, reported_value_usd=30),
    ]
    previous = [
        _entry(issuer_name="Increase Co", cusip="222222222", shares=10, reported_value_usd=100),
        _entry(issuer_name="Same Co", cusip="333333333", shares=5, reported_value_usd=50),
        _entry(issuer_name="Reduce Co", cusip="444444444", shares=8, reported_value_usd=80),
        _entry(issuer_name="Exit Co", cusip="555555555", shares=4, reported_value_usd=40),
    ]

    response = compare_position_snapshots(
        institution_name="Test Manager",
        institution_cik="1067983",
        current_period=date(2026, 3, 31),
        previous_period=date(2025, 12, 31),
        current_positions=current,
        previous_positions=previous,
        filter_status=PositionDiffFilterStatus.ALL,
        data_quality=PositionDiffDataQuality(),
    )

    statuses = {p.issuer_name: p.status for p in response.positions}
    assert statuses["New Co"] == PositionDiffStatus.NEW
    assert statuses["Increase Co"] == PositionDiffStatus.INCREASED
    assert statuses["Same Co"] == PositionDiffStatus.UNCHANGED
    assert statuses["Reduce Co"] == PositionDiffStatus.REDUCED
    assert statuses["Exit Co"] == PositionDiffStatus.EXITED
    assert response.summary.new_count == 1
    assert response.summary.increased_count == 1
    assert response.summary.unchanged_count == 1
    assert response.summary.reduced_count == 1
    assert response.summary.exited_count == 1
    assert response.data_quality.ticker_enrichment_complete is False


def test_changed_filter_excludes_unchanged():
    current = [_entry(issuer_name="Same Co", cusip="333333333", shares=5, reported_value_usd=50)]
    previous = [_entry(issuer_name="Same Co", cusip="333333333", shares=5, reported_value_usd=50)]
    response = compare_position_snapshots(
        institution_name="Test Manager",
        institution_cik="1067983",
        current_period=date(2026, 3, 31),
        previous_period=date(2025, 12, 31),
        current_positions=current,
        previous_positions=previous,
    )
    assert response.positions == []
    assert response.pagination.total_matching == 0


def test_highlights_are_built_from_diff_results():
    current = [
        _entry(issuer_name="Buyer A", cusip="111111111", shares=20, reported_value_usd=200),
        _entry(issuer_name="Buyer B", cusip="222222222", shares=10, reported_value_usd=100),
    ]
    previous = [
        _entry(issuer_name="Buyer A", cusip="111111111", shares=10, reported_value_usd=100),
        _entry(issuer_name="Seller A", cusip="333333333", shares=12, reported_value_usd=120),
    ]
    response = compare_position_snapshots(
        institution_name="Test Manager",
        institution_cik="1067983",
        current_period=date(2026, 3, 31),
        previous_period=date(2025, 12, 31),
        current_positions=current,
        previous_positions=previous,
        filter_status=PositionDiffFilterStatus.ALL,
    )
    assert response.highlights.largest_buyers[0].issuer_name == "Buyer A"
    assert response.highlights.new_positions[0].issuer_name == "Buyer B"
    assert response.highlights.complete_exits[0].issuer_name == "Seller A"


def test_compare_raises_on_ambiguous_duplicate_group():
    current = [_entry(), _entry(ticker="MSFT")]
    previous = []
    with pytest.raises(PositionAmbiguityError):
        compare_position_snapshots(
            institution_name="Test Manager",
            institution_cik="1067983",
            current_period=date(2026, 3, 31),
            previous_period=date(2025, 12, 31),
            current_positions=current,
            previous_positions=previous,
        )


def test_fetch_13f_filing_records_merges_recent_and_historical_submissions():
    records = fetch_13f_filing_records("1067983", json_fetcher=_fixture_json_fetcher)
    assert len(records) == 6
    assert records[0].accession_number == "0001067983-26-000013"
    assert records[-1].accession_number == "0001067983-26-000001"
    assert {record.report_period for record in records} == {date(2026, 3, 31), date(2025, 12, 31)}


def test_select_reporting_period_pair_uses_report_period_not_filing_date():
    records = fetch_13f_filing_records("1067983", json_fetcher=_fixture_json_fetcher)
    current_period, previous_period = select_reporting_period_pair(records)
    assert current_period == date(2026, 3, 31)
    assert previous_period == date(2025, 12, 31)


def test_load_13f_filing_parses_metadata_and_normalizes_value_unit_to_usd():
    records = fetch_13f_filing_records("1067983", json_fetcher=_fixture_json_fetcher)
    filing_record = next(record for record in records if record.accession_number == "0001067983-26-000012")
    filing = load_13f_filing(
        filing_record,
        json_fetcher=_fixture_json_fetcher,
        text_fetcher=_fixture_text_fetcher,
    )
    assert filing.metadata.is_amendment is True
    assert filing.metadata.amendment_type == "NEW HOLDINGS"
    assert filing.metadata.amendment_no == 2
    assert filing.metadata.is_confidential_omitted is True
    assert filing.metadata.report_period == date(2026, 3, 31)
    assert filing.positions[0].issuer_name == "Delta Corp"
    assert filing.positions[0].reported_value_usd == 50.0
    assert filing.positions[0].accession_number == "0001067983-26-000012"


def test_identify_information_table_prefers_document_type_metadata_for_nonstandard_filename():
    filing_record = SEC13FFilingRecord(
        cik="0001067983",
        accession_number="0001067983-26-100001",
        form="13F-HR",
        filing_date=date(2026, 5, 15),
        report_period=date(2026, 3, 31),
        primary_document="primary_doc.xml",
    )
    index_json = {
        "directory": {
            "item": [
                {"name": "primary_doc.xml"},
                {"name": "brka20260331positions.xml"},
                {"name": "FilingSummary.xml"},
            ]
        }
    }
    base = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100001"
    text_fetcher = _mock_text_fetcher_factory(
        {
            f"{base}/0001067983-26-100001-index.html": """
            <table>
              <tr><td>1</td><td></td><td><a href="primary_doc.xml">primary_doc.xml</a></td><td>13F-HR</td></tr>
              <tr><td>2</td><td>Quarterly holdings</td><td><a href="brka20260331positions.xml">brka20260331positions.xml</a></td><td>INFORMATION TABLE</td></tr>
            </table>
            """,
            f"{base}/primary_doc.xml": """
            <edgarSubmission>
              <formData><coverPage><reportCalendarOrQuarter>2026-03-31</reportCalendarOrQuarter><filingManager><name>Example Capital</name></filingManager></coverPage></formData>
            </edgarSubmission>
            """,
            f"{base}/brka20260331positions.xml": """
            <informationTable>
              <infoTable>
                <nameOfIssuer>Alpha</nameOfIssuer>
                <titleOfClass>COM</titleOfClass>
                <cusip>123456789</cusip>
                <value>10</value>
                <shrsOrPrnAmt><sshPrnamt>1</sshPrnamt></shrsOrPrnAmt>
              </infoTable>
            </informationTable>
            """,
            f"{base}/FilingSummary.xml": "<FilingSummary />",
        }
    )

    documents = identify_13f_xml_documents(
        index_json,
        filing_record=filing_record,
        text_fetcher=text_fetcher,
    )
    assert documents.primary_xml_name == "primary_doc.xml"
    assert documents.information_table_xml_name == "brka20260331positions.xml"


def test_load_13f_filing_detects_namespace_aware_information_table_with_nonstandard_filename():
    filing_record = SEC13FFilingRecord(
        cik="0001067983",
        accession_number="0001067983-26-100002",
        form="13F-HR",
        filing_date=date(2026, 5, 15),
        report_period=date(2026, 3, 31),
        primary_document="coverpage.xml",
    )
    index_url = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100002/index.json"
    base = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100002"
    json_fetcher = _mock_json_fetcher_factory(
        {
            index_url: {
                "directory": {
                    "item": [
                        {"name": "coverpage.xml"},
                        {"name": "holdings-q1.xml"},
                    ]
                }
            }
        }
    )
    text_fetcher = _mock_text_fetcher_factory(
        {
            f"{base}/0001067983-26-100002-index.html": """
            <table>
              <tr><td>1</td><td></td><td><a href="coverpage.xml">coverpage.xml</a></td><td>13F-HR</td></tr>
              <tr><td>2</td><td>Q1 2026 Holdings</td><td><a href="holdings-q1.xml">holdings-q1.xml</a></td><td>INFORMATION TABLE</td></tr>
            </table>
            """,
            f"{base}/coverpage.xml": """
            <edgarSubmission xmlns="http://www.sec.gov/edgar/thirteenffiler">
              <formData><coverPage><reportCalendarOrQuarter>2026-03-31</reportCalendarOrQuarter><filingManager><name>Example Capital</name></filingManager></coverPage></formData>
            </edgarSubmission>
            """,
            f"{base}/holdings-q1.xml": """
            <ns:informationTable xmlns:ns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
              <ns:infoTable>
                <ns:nameOfIssuer>Namespaced Alpha</ns:nameOfIssuer>
                <ns:titleOfClass>COM</ns:titleOfClass>
                <ns:cusip>123456789</ns:cusip>
                <ns:value>250</ns:value>
                <ns:shrsOrPrnAmt><ns:sshPrnamt>5</ns:sshPrnamt></ns:shrsOrPrnAmt>
              </ns:infoTable>
            </ns:informationTable>
            """,
        }
    )

    filing = load_13f_filing(
        filing_record,
        json_fetcher=json_fetcher,
        text_fetcher=text_fetcher,
    )
    assert filing.positions[0].issuer_name == "Namespaced Alpha"
    assert filing.positions[0].reported_value_usd == 250.0


def test_primary_filing_xml_is_not_selected_as_information_table_when_multiple_xml_files_exist():
    filing_record = SEC13FFilingRecord(
        cik="0001067983",
        accession_number="0001067983-26-100003",
        form="13F-HR",
        filing_date=date(2026, 5, 15),
        report_period=date(2026, 3, 31),
        primary_document="primary_doc.xml",
    )
    index_json = {
        "directory": {
            "item": [
                {"name": "primary_doc.xml"},
                {"name": "d74313d8k_htm.xml"},
                {"name": "FilingSummary.xml"},
                {"name": "custom_holdings.xml"},
            ]
        }
    }
    base = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100003"
    text_fetcher = _mock_text_fetcher_factory(
        {
            f"{base}/0001067983-26-100003-index.html": """
            <table>
              <tr><td>1</td><td></td><td><a href="primary_doc.xml">primary_doc.xml</a></td><td>13F-HR</td></tr>
              <tr><td>2</td><td>XBRL instance</td><td><a href="d74313d8k_htm.xml">d74313d8k_htm.xml</a></td><td>EX-101.INS</td></tr>
              <tr><td>3</td><td>Holdings</td><td><a href="custom_holdings.xml">custom_holdings.xml</a></td><td>INFORMATION TABLE</td></tr>
            </table>
            """,
            f"{base}/primary_doc.xml": """
            <edgarSubmission><formData><coverPage><reportCalendarOrQuarter>2026-03-31</reportCalendarOrQuarter><filingManager><name>Example Capital</name></filingManager></coverPage></formData></edgarSubmission>
            """,
            f"{base}/d74313d8k_htm.xml": "<xbrl><context>not a 13f table</context></xbrl>",
            f"{base}/FilingSummary.xml": "<FilingSummary />",
            f"{base}/custom_holdings.xml": """
            <informationTable><infoTable><nameOfIssuer>Correct Pick</nameOfIssuer><titleOfClass>COM</titleOfClass><cusip>111111111</cusip><value>12</value><shrsOrPrnAmt><sshPrnamt>2</sshPrnamt></shrsOrPrnAmt></infoTable></informationTable>
            """,
        }
    )

    documents = identify_13f_xml_documents(
        index_json,
        filing_record=filing_record,
        text_fetcher=text_fetcher,
    )
    assert documents.primary_xml_name == "primary_doc.xml"
    assert documents.information_table_xml_name == "custom_holdings.xml"


def test_amendment_without_information_table_preserves_existing_snapshot_positions():
    original = SEC13FFilingRecord(
        cik="0001067983",
        accession_number="0001067983-26-100004",
        form="13F-HR",
        filing_date=date(2026, 5, 1),
        report_period=date(2026, 3, 31),
        primary_document="primary_doc.xml",
    )
    amendment = SEC13FFilingRecord(
        cik="0001067983",
        accession_number="0001067983-26-100005",
        form="13F-HR/A",
        filing_date=date(2026, 5, 10),
        report_period=date(2026, 3, 31),
        primary_document="amendment.xml",
    )

    archives = {
        "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100004/index.json": {
            "directory": {"item": [{"name": "primary_doc.xml"}, {"name": "holdings.xml"}]}
        },
        "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100005/index.json": {
            "directory": {"item": [{"name": "amendment.xml"}, {"name": "ck0000000000-ex99_a.pdf"}]}
        },
    }
    base_original = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100004"
    base_amendment = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100005"
    texts = {
        f"{base_original}/0001067983-26-100004-index.html": """
        <table>
          <tr><td>1</td><td></td><td><a href="primary_doc.xml">primary_doc.xml</a></td><td>13F-HR</td></tr>
          <tr><td>2</td><td></td><td><a href="holdings.xml">holdings.xml</a></td><td>INFORMATION TABLE</td></tr>
        </table>
        """,
        f"{base_original}/primary_doc.xml": """
        <edgarSubmission><formData><coverPage><reportCalendarOrQuarter>2026-03-31</reportCalendarOrQuarter><filingManager><name>Example Capital</name></filingManager></coverPage></formData></edgarSubmission>
        """,
        f"{base_original}/holdings.xml": """
        <informationTable><infoTable><nameOfIssuer>Original Alpha</nameOfIssuer><titleOfClass>COM</titleOfClass><cusip>123456789</cusip><value>15</value><shrsOrPrnAmt><sshPrnamt>3</sshPrnamt></shrsOrPrnAmt></infoTable></informationTable>
        """,
        f"{base_amendment}/0001067983-26-100005-index.html": """
        <table>
          <tr><td>1</td><td></td><td><a href="amendment.xml">amendment.xml</a></td><td>13F-HR/A</td></tr>
        </table>
        """,
        f"{base_amendment}/amendment.xml": """
        <edgarSubmission>
          <formData>
            <coverPage>
              <reportCalendarOrQuarter>2026-03-31</reportCalendarOrQuarter>
              <filingManager><name>Example Capital</name></filingManager>
              <isAmendment>true</isAmendment>
              <amendmentInfo><amendmentType>NEW HOLDINGS</amendmentType><amendmentNo>1</amendmentNo></amendmentInfo>
            </coverPage>
          </formData>
        </edgarSubmission>
        """,
    }
    snapshot = build_13f_reporting_period_snapshot(
        [original, amendment],
        json_fetcher=_mock_json_fetcher_factory(archives),
        text_fetcher=_mock_text_fetcher_factory(texts),
    )
    assert [position.issuer_name for position in snapshot.positions] == ["Original Alpha"]
    assert snapshot.warnings[0].code == "amendment_missing_information_table"


def test_no_valid_information_table_returns_controlled_error():
    filing_record = SEC13FFilingRecord(
        cik="0001067983",
        accession_number="0001067983-26-100006",
        form="13F-HR",
        filing_date=date(2026, 5, 15),
        report_period=date(2026, 3, 31),
        primary_document="primary_doc.xml",
    )
    index_url = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100006/index.json"
    base = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326100006"
    json_fetcher = _mock_json_fetcher_factory(
        {
            index_url: {
                "directory": {
                    "item": [
                        {"name": "primary_doc.xml"},
                        {"name": "FilingSummary.xml"},
                    ]
                }
            }
        }
    )
    text_fetcher = _mock_text_fetcher_factory(
        {
            f"{base}/0001067983-26-100006-index.html": """
            <table><tr><td>1</td><td></td><td><a href="primary_doc.xml">primary_doc.xml</a></td><td>13F-HR</td></tr></table>
            """,
            f"{base}/primary_doc.xml": """
            <edgarSubmission><formData><coverPage><reportCalendarOrQuarter>2026-03-31</reportCalendarOrQuarter><filingManager><name>Example Capital</name></filingManager></coverPage></formData></edgarSubmission>
            """,
            f"{base}/FilingSummary.xml": "<FilingSummary />",
        }
    )

    with pytest.raises(ValueError, match="information-table XML document"):
        load_13f_filing(
            filing_record,
            json_fetcher=json_fetcher,
            text_fetcher=text_fetcher,
        )


def test_regression_cik_1067983_nonstandard_information_table_filename_uses_metadata():
    filing_record = SEC13FFilingRecord(
        cik="0001067983",
        accession_number="0001067983-26-227107",
        form="13F-HR",
        filing_date=date(2026, 5, 15),
        report_period=date(2026, 3, 31),
        primary_document="primary_doc.xml",
    )
    index_url = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326227107/index.json"
    base = "https://www.sec.gov/Archives/edgar/data/1067983/000106798326227107"
    json_fetcher = _mock_json_fetcher_factory(
        {
            index_url: {
                "directory": {
                    "item": [
                        {"name": "primary_doc.xml"},
                        {"name": "ck0000000000-ex99_a.pdf"},
                        {"name": "ck0000000000-ex99_b.pdf"},
                        {"name": "brka20260331_positions.xml"},
                    ]
                }
            }
        }
    )
    text_fetcher = _mock_text_fetcher_factory(
        {
            f"{base}/0001067983-26-227107-index.html": """
            <table>
              <tr><td>1</td><td></td><td><a href="primary_doc.xml">primary_doc.xml</a></td><td>13F-HR</td></tr>
              <tr><td>2</td><td>Confidential appendix</td><td><a href="ck0000000000-ex99_a.pdf">ck0000000000-ex99_a.pdf</a></td><td>EX-99.A</td></tr>
              <tr><td>3</td><td>Confidential appendix</td><td><a href="ck0000000000-ex99_b.pdf">ck0000000000-ex99_b.pdf</a></td><td>EX-99.B</td></tr>
              <tr><td>4</td><td>Quarterly holdings</td><td><a href="brka20260331_positions.xml">brka20260331_positions.xml</a></td><td>INFORMATION TABLE</td></tr>
            </table>
            """,
            f"{base}/primary_doc.xml": """
            <edgarSubmission><formData><coverPage><reportCalendarOrQuarter>2026-03-31</reportCalendarOrQuarter><filingManager><name>Example Capital Management</name></filingManager></coverPage></formData></edgarSubmission>
            """,
            f"{base}/brka20260331_positions.xml": """
            <informationTable><infoTable><nameOfIssuer>Regression Holding</nameOfIssuer><titleOfClass>COM</titleOfClass><cusip>999999999</cusip><value>42</value><shrsOrPrnAmt><sshPrnamt>7</sshPrnamt></shrsOrPrnAmt></infoTable></informationTable>
            """,
        }
    )

    filing = load_13f_filing(
        filing_record,
        json_fetcher=json_fetcher,
        text_fetcher=text_fetcher,
    )
    assert filing.positions[0].issuer_name == "Regression Holding"
    assert filing.positions[0].reported_value_usd == 42.0


def test_build_13f_reporting_period_snapshot_applies_restatement_and_supplemental_amendments():
    records = fetch_13f_filing_records("1067983", json_fetcher=_fixture_json_fetcher)
    period_records = filter_filing_records_for_period(records, "2026-03-31")
    snapshot = build_13f_reporting_period_snapshot(
        period_records,
        json_fetcher=_fixture_json_fetcher,
        text_fetcher=_fixture_text_fetcher,
    )

    assert snapshot.institution_name == "Example Capital Management"
    assert snapshot.primary_filing.metadata.accession_number == "0001067983-26-000011"
    assert [item.metadata.accession_number for item in snapshot.supplemental_amendments] == [
        "0001067983-26-000012",
        "0001067983-26-000013",
    ]
    assert [position.issuer_name for position in snapshot.positions] == [
        "Alpha Corp",
        "Gamma Corp",
        "Delta Corp",
        "Epsilon Corp",
    ]
    assert [position.accession_number for position in snapshot.positions] == [
        "0001067983-26-000011",
        "0001067983-26-000011",
        "0001067983-26-000012",
        "0001067983-26-000013",
    ]
    assert snapshot.warnings[0].code == "confidential_omissions_possible"


def test_previous_period_restatement_replaces_original_snapshot_positions():
    records = fetch_13f_filing_records("1067983", json_fetcher=_fixture_json_fetcher)
    period_records = filter_filing_records_for_period(records, date(2025, 12, 31))
    snapshot = build_13f_reporting_period_snapshot(
        period_records,
        json_fetcher=_fixture_json_fetcher,
        text_fetcher=_fixture_text_fetcher,
    )
    assert snapshot.primary_filing.metadata.accession_number == "0001067983-26-000002"
    assert len(snapshot.positions) == 1
    assert snapshot.positions[0].issuer_name == "Legacy Holding"
    assert snapshot.positions[0].reported_value_usd == 95.0
    assert snapshot.positions[0].shares == 10


def test_parse_13f_information_table_keeps_post_2023_value_in_usd():
    filing_record = SEC13FFilingRecord(
        cik="0001067983",
        accession_number="0001067983-26-999999",
        form="13F-HR",
        filing_date=date(2026, 5, 15),
        report_period=date(2026, 3, 31),
        primary_document="primary_doc.xml",
    )
    xml_text = """
    <informationTable>
      <infoTable>
        <nameOfIssuer>Post 2023 Co</nameOfIssuer>
        <titleOfClass>COM</titleOfClass>
        <cusip>123456789</cusip>
        <value>150000000</value>
        <shrsOrPrnAmt>
          <sshPrnamt>10</sshPrnamt>
          <sshPrnamtType>SH</sshPrnamtType>
        </shrsOrPrnAmt>
      </infoTable>
    </informationTable>
    """
    positions = parse_13f_information_table(xml_text, filing_record=filing_record)
    assert positions[0].reported_value_usd == 150000000.0


def test_parse_13f_information_table_scales_pre_2023_thousands_to_usd():
    filing_record = SEC13FFilingRecord(
        cik="0001067983",
        accession_number="0001067983-22-999999",
        form="13F-HR",
        filing_date=date(2022, 12, 31),
        report_period=date(2022, 9, 30),
        primary_document="primary_doc.xml",
    )
    xml_text = """
    <informationTable>
      <infoTable>
        <nameOfIssuer>Pre 2023 Co</nameOfIssuer>
        <titleOfClass>COM</titleOfClass>
        <cusip>987654321</cusip>
        <value>150000</value>
        <shrsOrPrnAmt>
          <sshPrnamt>10</sshPrnamt>
          <sshPrnamtType>SH</sshPrnamtType>
        </shrsOrPrnAmt>
      </infoTable>
    </informationTable>
    """
    positions = parse_13f_information_table(xml_text, filing_record=filing_record)
    assert positions[0].reported_value_usd == 150000000.0


def test_13f_period_snapshot_cache_roundtrip_preserves_positions_and_warnings(db_session):
    records = fetch_13f_filing_records("1067983", json_fetcher=_fixture_json_fetcher)
    period_records = filter_filing_records_for_period(records, date(2026, 3, 31))
    snapshot = build_13f_reporting_period_snapshot(
        period_records,
        json_fetcher=_fixture_json_fetcher,
        text_fetcher=_fixture_text_fetcher,
    )

    cached = upsert_13f_period_snapshot_cache(db_session, snapshot)
    reloaded = load_13f_period_snapshot_from_cache(
        db_session,
        institution_cik="1067983",
        report_period=date(2026, 3, 31),
    )

    assert cached.primary_filing.metadata.accession_number == "0001067983-26-000011"
    assert reloaded is not None
    assert reloaded.primary_filing.metadata.accession_number == "0001067983-26-000011"
    assert reloaded.primary_filing.metadata.is_confidential_omitted is False
    assert [item.metadata.accession_number for item in reloaded.supplemental_amendments] == [
        "0001067983-26-000012",
        "0001067983-26-000013",
    ]
    assert [position.accession_number for position in reloaded.positions] == [
        "0001067983-26-000011",
        "0001067983-26-000011",
        "0001067983-26-000012",
        "0001067983-26-000013",
    ]
    assert reloaded.warnings[0].code == "confidential_omissions_possible"
    assert reloaded.data_quality.confidential_omissions_possible is True


def test_get_or_fetch_13f_period_snapshot_uses_cache_after_first_fetch(db_session):
    calls = {"json": 0, "text": 0}

    def counting_json_fetcher(url: str):
        calls["json"] += 1
        return _fixture_json_fetcher(url)

    def counting_text_fetcher(url: str):
        calls["text"] += 1
        return _fixture_text_fetcher(url)

    first = get_or_fetch_13f_period_snapshot(
        db_session,
        institution_cik="1067983",
        report_period=date(2026, 3, 31),
        json_fetcher=counting_json_fetcher,
        text_fetcher=counting_text_fetcher,
    )
    assert first.primary_filing.metadata.accession_number == "0001067983-26-000011"
    assert calls["json"] > 0
    assert calls["text"] > 0

    calls_before_second = calls.copy()
    second = get_or_fetch_13f_period_snapshot(
        db_session,
        institution_cik="1067983",
        report_period=date(2026, 3, 31),
        json_fetcher=counting_json_fetcher,
        text_fetcher=counting_text_fetcher,
    )
    assert second.primary_filing.metadata.accession_number == "0001067983-26-000011"
    assert calls == calls_before_second


def test_upsert_13f_period_snapshot_cache_does_not_create_duplicate_period_rows(db_session):
    records = fetch_13f_filing_records("1067983", json_fetcher=_fixture_json_fetcher)
    period_records = filter_filing_records_for_period(records, date(2026, 3, 31))
    snapshot = build_13f_reporting_period_snapshot(
        period_records,
        json_fetcher=_fixture_json_fetcher,
        text_fetcher=_fixture_text_fetcher,
    )

    first = upsert_13f_period_snapshot_cache(db_session, snapshot)
    second = upsert_13f_period_snapshot_cache(db_session, snapshot)

    assert first.primary_filing.metadata.accession_number == second.primary_filing.metadata.accession_number
    assert db_session.query(app.models.market_13f_cache.Institutional13FPeriodCache).count() == 1


def test_get_or_fetch_13f_period_snapshot_uses_cached_snapshot_when_fetchers_fail(db_session):
    initial = get_or_fetch_13f_period_snapshot(
        db_session,
        institution_cik="1067983",
        report_period=date(2026, 3, 31),
        json_fetcher=_fixture_json_fetcher,
        text_fetcher=_fixture_text_fetcher,
    )
    assert initial.primary_filing.metadata.accession_number == "0001067983-26-000011"

    def failing_json_fetcher(url: str):
        raise RuntimeError(f"unexpected SEC json fetch: {url}")

    def failing_text_fetcher(url: str):
        raise RuntimeError(f"unexpected SEC text fetch: {url}")

    cached = get_or_fetch_13f_period_snapshot(
        db_session,
        institution_cik="1067983",
        report_period=date(2026, 3, 31),
        json_fetcher=failing_json_fetcher,
        text_fetcher=failing_text_fetcher,
    )
    assert cached.primary_filing.metadata.accession_number == "0001067983-26-000011"
    assert [position.accession_number for position in cached.positions] == [
        "0001067983-26-000011",
        "0001067983-26-000011",
        "0001067983-26-000012",
        "0001067983-26-000013",
    ]
