import json
import os
from pathlib import Path
import sys
from datetime import date

import pytest

API_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
if API_ROOT not in sys.path:
    sys.path.insert(0, API_ROOT)

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
    group_compatible_positions,
    load_13f_filing,
    normalize_cik,
    normalize_cusip,
    normalize_issuer_name,
    normalize_put_call,
    normalize_reporting_period,
    normalize_security_title,
    parse_13f_information_table,
    select_reporting_period_pair,
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
