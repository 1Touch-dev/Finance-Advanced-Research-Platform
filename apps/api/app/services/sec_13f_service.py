from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
import os
import re
from typing import Any, Callable, Iterable, Sequence
import xml.etree.ElementTree as ET

import requests
from sqlalchemy.orm import Session

from app.models.market_13f_cache import (
    Institutional13FPeriodCache,
    Institutional13FPositionCache,
    Institutional13FSupplementalAmendmentCache,
)
from app.models.market_13f_schemas import (
    PositionDiffDataQuality,
    PositionDiffFilterStatus,
    PositionDiffFilingRef,
    PositionDiffFilings,
    PositionDiffHighlights,
    PositionDiffInstitution,
    PositionDiffPagination,
    PositionDiffPeriods,
    PositionDiffPosition,
    PositionDiffResponse,
    PositionDiffRequest,
    PositionDiffSortField,
    PositionDiffStatus,
    PositionDiffSummary,
    PositionDiffWarning,
    PositionSnapshotEntry,
    PutCallValue,
    SortDirection,
)


QUARTER_ENDS = {(3, 31), (6, 30), (9, 30), (12, 31)}
FORM_13F_VALUE_NEAREST_DOLLAR_DATE = date(2023, 1, 3)
_SPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]")
_NAME_PUNCT_RE = re.compile(r"[^A-Z0-9 ]")
_INFO_TABLE_NAME_RE = re.compile(r"(information[-_ ]?table|infotable)", re.IGNORECASE)
_PRIMARY_XML_NAME_RE = re.compile(r"(primary|13fhr|form13f)", re.IGNORECASE)
_AMENDMENT_RESTATEMENT = "RESTATEMENT"
_AMENDMENT_NEW_HOLDINGS = "NEW HOLDINGS"


class PositionAmbiguityError(ValueError):
    """Raised when positions cannot be safely aggregated or compared."""


@dataclass
class GroupedPositionsResult:
    positions: list[PositionSnapshotEntry]
    warnings: list[PositionDiffWarning]
    ambiguous_groups: dict[str, list[PositionSnapshotEntry]]


@dataclass(frozen=True)
class SEC13FFilingRecord:
    cik: str
    accession_number: str
    form: str
    filing_date: date
    report_period: date
    primary_document: str | None = None

    @property
    def accession_number_compact(self) -> str:
        return self.accession_number.replace("-", "")

    @property
    def archives_path_cik(self) -> str:
        return str(int(self.cik))


@dataclass(frozen=True)
class SEC13FXmlDocuments:
    primary_xml_name: str
    information_table_xml_name: str


@dataclass(frozen=True)
class ParsedSEC13FMetadata:
    cik: str
    accession_number: str
    form: str
    filing_date: date
    report_period: date
    filing_manager_name: str
    is_amendment: bool
    amendment_type: str | None
    amendment_no: int | None
    is_confidential_omitted: bool


@dataclass(frozen=True)
class ParsedSEC13FFiling:
    metadata: ParsedSEC13FMetadata
    positions: list[PositionSnapshotEntry]


@dataclass(frozen=True)
class SEC13FPeriodSnapshot:
    institution_name: str
    cik: str
    report_period: date
    primary_filing: ParsedSEC13FFiling
    supplemental_amendments: list[ParsedSEC13FFiling] = field(default_factory=list)
    positions: list[PositionSnapshotEntry] = field(default_factory=list)
    warnings: list[PositionDiffWarning] = field(default_factory=list)
    data_quality: PositionDiffDataQuality = field(default_factory=PositionDiffDataQuality)


JsonFetcher = Callable[[str], dict[str, Any]]
TextFetcher = Callable[[str], str]


def normalize_cik(value: str) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if not digits:
        raise ValueError("institution_cik must contain digits")
    if len(digits) > 10:
        raise ValueError("institution_cik cannot exceed 10 digits")
    return digits.zfill(10)


def _sec_headers() -> dict[str, str]:
    return {
        "User-Agent": os.getenv("SEC_USER_AGENT", "IntelPlatform research@example.com"),
        "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
    }


def _requests_json_fetcher(url: str) -> dict[str, Any]:
    response = requests.get(url, headers=_sec_headers(), timeout=20)
    response.raise_for_status()
    return response.json()


def _requests_text_fetcher(url: str) -> str:
    response = requests.get(url, headers=_sec_headers(), timeout=20)
    response.raise_for_status()
    return response.text


def normalize_reporting_period(value: date | str) -> date:
    if isinstance(value, date):
        period = value
    else:
        raw = str(value or "").strip()
        if not raw:
            raise ValueError("reporting period is required")
        period = None
        for fmt in ("%Y-%m-%d", "%m-%d-%Y"):
            try:
                period = datetime.strptime(raw, fmt).date()
                break
            except ValueError:
                continue
        if period is None:
            raise ValueError("reporting period must be YYYY-MM-DD or MM-DD-YYYY")

    if (period.month, period.day) not in QUARTER_ENDS:
        raise ValueError("reporting period must be a calendar quarter end")
    return period


def normalize_cusip(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _NON_ALNUM_RE.sub("", str(value).upper())
    return normalized or None


def normalize_issuer_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _NAME_PUNCT_RE.sub(" ", str(value).upper())
    collapsed = _SPACE_RE.sub(" ", cleaned).strip()
    return collapsed or None


def normalize_security_title(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _NAME_PUNCT_RE.sub(" ", str(value).upper())
    collapsed = _SPACE_RE.sub(" ", cleaned).strip()
    return collapsed or None


def normalize_put_call(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _SPACE_RE.sub(" ", str(value).upper()).strip()
    if not cleaned:
        return None
    if cleaned == PutCallValue.PUT.value:
        return PutCallValue.PUT.value
    if cleaned == PutCallValue.CALL.value:
        return PutCallValue.CALL.value
    raise ValueError("put/call must be PUT, CALL, or blank")


def _normalize_bool(value: str | None) -> bool:
    cleaned = _SPACE_RE.sub("", str(value or "").upper())
    return cleaned in {"Y", "YES", "TRUE", "1"}


def _parse_optional_int(value: str | None) -> int | None:
    raw = str(value or "").strip()
    return int(raw) if raw else None


def _parse_optional_float(value: str | None) -> float | None:
    raw = str(value or "").strip()
    return float(raw.replace(",", "")) if raw else None


def _normalize_13f_value_to_usd(raw_value: float, *, filing_date: date) -> float:
    if filing_date >= FORM_13F_VALUE_NEAREST_DOLLAR_DATE:
        return raw_value
    return raw_value * 1000.0


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_find_first_text(element: ET.Element, path: Sequence[str]) -> str | None:
    current = element
    for expected in path:
        next_element = None
        for child in current:
            if _xml_local_name(child.tag) == expected:
                next_element = child
                break
        if next_element is None:
            return None
        current = next_element
    text = current.text.strip() if current.text else ""
    return text or None


def _xml_findall_by_local_name(element: ET.Element, local_name: str) -> list[ET.Element]:
    return [node for node in element.iter() if _xml_local_name(node.tag) == local_name]


def _normalize_amendment_type(value: str | None) -> str | None:
    normalized = normalize_issuer_name(value)
    if normalized is None:
        return None
    if normalized == _AMENDMENT_RESTATEMENT:
        return _AMENDMENT_RESTATEMENT
    if normalized == _AMENDMENT_NEW_HOLDINGS:
        return _AMENDMENT_NEW_HOLDINGS
    return normalized


def canonical_ticker(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _NON_ALNUM_RE.sub("", str(value).upper())
    return cleaned or None


def extract_13f_filing_records(
    submissions_json: dict[str, Any], *, cik: str | None = None
) -> list[SEC13FFilingRecord]:
    normalized_cik = normalize_cik(cik or submissions_json.get("cik", ""))
    records: list[SEC13FFilingRecord] = []
    filing_sections = [submissions_json.get("filings", {}).get("recent", {})]
    for section in filing_sections:
        forms = section.get("form", [])
        filing_dates = section.get("filingDate", [])
        accession_numbers = section.get("accessionNumber", [])
        report_dates = section.get("reportDate", [])
        primary_documents = section.get("primaryDocument", [])

        for idx, form in enumerate(forms):
            if not str(form or "").upper().startswith("13F-HR"):
                continue
            report_date = report_dates[idx] if idx < len(report_dates) else None
            if not report_date:
                continue
            accession_number = accession_numbers[idx] if idx < len(accession_numbers) else None
            filing_date = filing_dates[idx] if idx < len(filing_dates) else None
            if not accession_number or not filing_date:
                continue
            primary_document = primary_documents[idx] if idx < len(primary_documents) else None
            records.append(
                SEC13FFilingRecord(
                    cik=normalized_cik,
                    accession_number=accession_number,
                    form=str(form),
                    filing_date=datetime.strptime(filing_date, "%Y-%m-%d").date(),
                    report_period=normalize_reporting_period(report_date),
                    primary_document=primary_document or None,
                )
            )

    deduped: dict[tuple[str, date], SEC13FFilingRecord] = {}
    for record in records:
        deduped[(record.accession_number, record.report_period)] = record

    ordered_records = list(deduped.values())
    ordered_records.sort(
        key=lambda item: (
            item.report_period,
            item.filing_date,
            item.accession_number,
        ),
        reverse=True,
    )
    return ordered_records


def _merge_submission_file_records(
    root_submissions_json: dict[str, Any],
    *,
    cik: str,
    json_fetcher: JsonFetcher,
    submissions_base_url: str,
) -> dict[str, Any]:
    merged = {
        **root_submissions_json,
        "filings": {
            **root_submissions_json.get("filings", {}),
            "recent": {
                **root_submissions_json.get("filings", {}).get("recent", {}),
            },
        },
    }
    historical_files = root_submissions_json.get("filings", {}).get("files", [])
    recent = merged["filings"]["recent"]
    for historical_file in historical_files:
        name = historical_file.get("name")
        if not name:
            continue
        historical_url = f"{submissions_base_url}/{name}"
        historical_json = json_fetcher(historical_url)
        for key, values in historical_json.items():
            if not isinstance(values, list):
                continue
            recent.setdefault(key, [])
            recent[key].extend(values)
    return merged


def fetch_13f_filing_records(
    cik: str,
    *,
    json_fetcher: JsonFetcher | None = None,
    submissions_base_url: str = "https://data.sec.gov/submissions",
) -> list[SEC13FFilingRecord]:
    normalized_cik = normalize_cik(cik)
    fetch_json = json_fetcher or _requests_json_fetcher
    submissions_url = f"{submissions_base_url}/CIK{normalized_cik}.json"
    root_submissions = fetch_json(submissions_url)
    merged_submissions = _merge_submission_file_records(
        root_submissions,
        cik=normalized_cik,
        json_fetcher=fetch_json,
        submissions_base_url=submissions_base_url,
    )
    return extract_13f_filing_records(merged_submissions, cik=normalized_cik)


def select_reporting_period_pair(
    filing_records: Sequence[SEC13FFilingRecord],
    *,
    current_period: date | str | None = None,
    previous_period: date | str | None = None,
) -> tuple[date, date]:
    periods = sorted({record.report_period for record in filing_records}, reverse=True)
    if not periods:
        raise ValueError("No 13F reporting periods were found for this institution")

    if current_period is None:
        selected_current = periods[0]
    else:
        selected_current = normalize_reporting_period(current_period)
        if selected_current not in periods:
            raise ValueError("Requested current_period is not available in SEC submissions")

    available_previous = [period for period in periods if period < selected_current]
    if previous_period is None:
        if not available_previous:
            raise ValueError("No previous reporting period is available for comparison")
        selected_previous = available_previous[0]
    else:
        selected_previous = normalize_reporting_period(previous_period)
        if selected_previous not in periods:
            raise ValueError("Requested previous_period is not available in SEC submissions")
        if selected_previous >= selected_current:
            raise ValueError("previous_period must be earlier than current_period")

    return selected_current, selected_previous


def filter_filing_records_for_period(
    filing_records: Sequence[SEC13FFilingRecord], report_period: date | str
) -> list[SEC13FFilingRecord]:
    normalized_period = normalize_reporting_period(report_period)
    return [record for record in filing_records if record.report_period == normalized_period]


def build_filing_archive_index_url(
    filing_record: SEC13FFilingRecord,
    *,
    archives_base_url: str = "https://www.sec.gov/Archives/edgar/data",
) -> str:
    return (
        f"{archives_base_url}/{filing_record.archives_path_cik}/"
        f"{filing_record.accession_number_compact}/index.json"
    )


def _build_filing_archive_file_url(
    filing_record: SEC13FFilingRecord,
    file_name: str,
    *,
    archives_base_url: str = "https://www.sec.gov/Archives/edgar/data",
) -> str:
    return (
        f"{archives_base_url}/{filing_record.archives_path_cik}/"
        f"{filing_record.accession_number_compact}/{file_name}"
    )


def identify_13f_xml_documents(
    index_json: dict[str, Any], *, primary_document: str | None = None
) -> SEC13FXmlDocuments:
    items = index_json.get("directory", {}).get("item", [])
    xml_names = [item.get("name") for item in items if str(item.get("name", "")).lower().endswith(".xml")]
    xml_names = [name for name in xml_names if name]
    if not xml_names:
        raise ValueError("SEC filing archive did not contain any XML documents")

    info_candidates = [name for name in xml_names if _INFO_TABLE_NAME_RE.search(name)]
    if not info_candidates:
        raise ValueError("SEC filing archive did not contain an information-table XML document")
    information_table_xml_name = sorted(info_candidates)[0]

    primary_candidates = [name for name in xml_names if name != information_table_xml_name]
    if primary_document and primary_document.lower().endswith(".xml"):
        for candidate in primary_candidates:
            if candidate.lower() == primary_document.lower():
                return SEC13FXmlDocuments(
                    primary_xml_name=candidate,
                    information_table_xml_name=information_table_xml_name,
                )
    ranked_primary = sorted(
        primary_candidates,
        key=lambda name: (
            0 if _PRIMARY_XML_NAME_RE.search(name) else 1,
            name.lower(),
        ),
    )
    if not ranked_primary:
        raise ValueError("SEC filing archive did not contain a primary 13F XML document")
    return SEC13FXmlDocuments(
        primary_xml_name=ranked_primary[0],
        information_table_xml_name=information_table_xml_name,
    )


def parse_13f_primary_document(
    xml_text: str,
    *,
    filing_record: SEC13FFilingRecord,
) -> ParsedSEC13FMetadata:
    root = ET.fromstring(xml_text)
    report_period = _xml_find_first_text(root, ("formData", "coverPage", "reportCalendarOrQuarter"))
    if report_period is None:
        report_period = _xml_find_first_text(root, ("headerData", "filerInfo", "periodOfReport"))

    manager_name = _xml_find_first_text(root, ("formData", "coverPage", "filingManager", "name"))
    if manager_name is None:
        manager_name = _xml_find_first_text(root, ("headerData", "filerInfo", "filer", "name"))
    if manager_name is None:
        raise ValueError("Primary 13F XML is missing the filing manager name")

    amendment_type = _normalize_amendment_type(
        _xml_find_first_text(root, ("formData", "coverPage", "amendmentInfo", "amendmentType"))
    )

    return ParsedSEC13FMetadata(
        cik=filing_record.cik,
        accession_number=filing_record.accession_number,
        form=filing_record.form,
        filing_date=filing_record.filing_date,
        report_period=normalize_reporting_period(report_period or filing_record.report_period),
        filing_manager_name=manager_name.strip(),
        is_amendment=_normalize_bool(
            _xml_find_first_text(root, ("formData", "coverPage", "isAmendment"))
        ),
        amendment_type=amendment_type,
        amendment_no=_parse_optional_int(
            _xml_find_first_text(root, ("formData", "coverPage", "amendmentNo"))
        ),
        is_confidential_omitted=_normalize_bool(
            _xml_find_first_text(root, ("formData", "summaryPage", "isConfidentialOmitted"))
        ),
    )


def parse_13f_information_table(
    xml_text: str,
    *,
    filing_record: SEC13FFilingRecord,
) -> list[PositionSnapshotEntry]:
    root = ET.fromstring(xml_text)
    positions: list[PositionSnapshotEntry] = []
    for row_index, info_table in enumerate(_xml_findall_by_local_name(root, "infoTable")):
        issuer_name = _xml_find_first_text(info_table, ("nameOfIssuer",))
        if not issuer_name:
            raise ValueError("13F information table row is missing nameOfIssuer")
        raw_value = _parse_optional_float(_xml_find_first_text(info_table, ("value",))) or 0.0
        shares = _parse_optional_float(
            _xml_find_first_text(info_table, ("shrsOrPrnAmt", "sshPrnamt"))
        ) or 0.0
        positions.append(
            PositionSnapshotEntry(
                issuer_name=issuer_name.strip(),
                cusip=_xml_find_first_text(info_table, ("cusip",)),
                security_title=_xml_find_first_text(info_table, ("titleOfClass",)),
                put_call=_xml_find_first_text(info_table, ("putCall",)),
                shares=shares,
                reported_value_usd=_normalize_13f_value_to_usd(
                    raw_value,
                    filing_date=filing_record.filing_date,
                ),
                accession_number=filing_record.accession_number,
                filing_date=filing_record.filing_date,
                raw_row_index=row_index,
            )
        )
    if not positions:
        raise ValueError("13F information table XML did not contain any infoTable rows")
    return positions


def load_13f_filing(
    filing_record: SEC13FFilingRecord,
    *,
    json_fetcher: JsonFetcher | None = None,
    text_fetcher: TextFetcher | None = None,
    archives_base_url: str = "https://www.sec.gov/Archives/edgar/data",
) -> ParsedSEC13FFiling:
    fetch_json = json_fetcher or _requests_json_fetcher
    fetch_text = text_fetcher or _requests_text_fetcher
    index_json = fetch_json(build_filing_archive_index_url(filing_record, archives_base_url=archives_base_url))
    xml_documents = identify_13f_xml_documents(index_json, primary_document=filing_record.primary_document)

    primary_xml = fetch_text(
        _build_filing_archive_file_url(
            filing_record, xml_documents.primary_xml_name, archives_base_url=archives_base_url
        )
    )
    info_table_xml = fetch_text(
        _build_filing_archive_file_url(
            filing_record, xml_documents.information_table_xml_name, archives_base_url=archives_base_url
        )
    )

    metadata = parse_13f_primary_document(primary_xml, filing_record=filing_record)
    positions = parse_13f_information_table(info_table_xml, filing_record=filing_record)
    return ParsedSEC13FFiling(metadata=metadata, positions=positions)


def _filing_sort_key(filing: ParsedSEC13FFiling) -> tuple[int, date, str]:
    amendment_no = filing.metadata.amendment_no if filing.metadata.amendment_no is not None else -1
    return (
        amendment_no,
        filing.metadata.filing_date,
        filing.metadata.accession_number,
    )


def build_13f_reporting_period_snapshot(
    filing_records: Sequence[SEC13FFilingRecord],
    *,
    json_fetcher: JsonFetcher | None = None,
    text_fetcher: TextFetcher | None = None,
    archives_base_url: str = "https://www.sec.gov/Archives/edgar/data",
) -> SEC13FPeriodSnapshot:
    if not filing_records:
        raise ValueError("At least one filing record is required to build a 13F snapshot")

    loaded_filings = [
        load_13f_filing(
            filing_record,
            json_fetcher=json_fetcher,
            text_fetcher=text_fetcher,
            archives_base_url=archives_base_url,
        )
        for filing_record in filing_records
    ]
    loaded_filings.sort(key=_filing_sort_key)

    report_periods = {filing.metadata.report_period for filing in loaded_filings}
    if len(report_periods) != 1:
        raise ValueError("Snapshot filings must all belong to the same reporting period")

    original_filings = [filing for filing in loaded_filings if not filing.metadata.is_amendment]
    amendments = [filing for filing in loaded_filings if filing.metadata.is_amendment]
    if original_filings:
        active_primary = sorted(original_filings, key=_filing_sort_key)[0]
    else:
        active_primary = loaded_filings[0]

    active_positions = [position.model_copy(deep=True) for position in active_primary.positions]
    supplemental_amendments: list[ParsedSEC13FFiling] = []
    warnings: list[PositionDiffWarning] = []

    for amendment in amendments:
        amendment_type = amendment.metadata.amendment_type
        if amendment_type == _AMENDMENT_RESTATEMENT:
            active_primary = amendment
            active_positions = [position.model_copy(deep=True) for position in amendment.positions]
            supplemental_amendments = []
        elif amendment_type == _AMENDMENT_NEW_HOLDINGS:
            active_positions.extend(position.model_copy(deep=True) for position in amendment.positions)
            supplemental_amendments.append(amendment)
        else:
            raise PositionAmbiguityError(
                "Unsupported or missing 13F amendmentType for accession "
                f"{amendment.metadata.accession_number}: {amendment_type!r}"
            )

    if any(filing.metadata.is_confidential_omitted for filing in loaded_filings):
        warnings.append(
            PositionDiffWarning(
                code="confidential_omissions_possible",
                message="One or more 13F filings reported confidential omissions for this period.",
            )
        )

    return SEC13FPeriodSnapshot(
        institution_name=active_primary.metadata.filing_manager_name,
        cik=active_primary.metadata.cik,
        report_period=active_primary.metadata.report_period,
        primary_filing=active_primary,
        supplemental_amendments=supplemental_amendments,
        positions=active_positions,
        warnings=warnings,
        data_quality=PositionDiffDataQuality(
            confidential_omissions_possible=any(
                filing.metadata.is_confidential_omitted for filing in loaded_filings
            )
        ),
    )


def _warning_to_json(warning: PositionDiffWarning) -> dict[str, Any]:
    return warning.model_dump()


def _warning_from_json(payload: dict[str, Any]) -> PositionDiffWarning:
    return PositionDiffWarning(**payload)


def _data_quality_to_json(data_quality: PositionDiffDataQuality) -> dict[str, Any]:
    return data_quality.model_dump()


def _data_quality_from_json(payload: dict[str, Any] | None) -> PositionDiffDataQuality:
    return PositionDiffDataQuality(**(payload or {}))


def _cached_report_periods(db: Session, institution_cik: str) -> list[date]:
    normalized_cik = normalize_cik(institution_cik)
    rows = (
        db.query(Institutional13FPeriodCache.report_period)
        .filter(Institutional13FPeriodCache.institution_cik == normalized_cik)
        .order_by(Institutional13FPeriodCache.report_period.desc())
        .all()
    )
    return [row[0] for row in rows]


def _resolve_position_diff_periods(
    db: Session,
    *,
    institution_cik: str,
    current_period: date | str | None,
    previous_period: date | str | None,
    json_fetcher: JsonFetcher | None = None,
    submissions_base_url: str = "https://data.sec.gov/submissions",
) -> tuple[date, date]:
    normalized_cik = normalize_cik(institution_cik)
    normalized_current = normalize_reporting_period(current_period) if current_period else None
    normalized_previous = normalize_reporting_period(previous_period) if previous_period else None

    if normalized_current and normalized_previous:
        if normalized_previous >= normalized_current:
            raise ValueError("previous_period must be earlier than current_period")
        return normalized_current, normalized_previous

    cached_periods = _cached_report_periods(db, normalized_cik)
    if normalized_current is None and normalized_previous is None and len(cached_periods) >= 2:
        return cached_periods[0], cached_periods[1]
    if normalized_current is not None and normalized_previous is None:
        previous_candidates = [period for period in cached_periods if period < normalized_current]
        if previous_candidates:
            return normalized_current, previous_candidates[0]
    if normalized_current is None and normalized_previous is not None:
        current_candidates = [period for period in cached_periods if period > normalized_previous]
        if current_candidates:
            return current_candidates[0], normalized_previous

    filing_records = fetch_13f_filing_records(
        normalized_cik,
        json_fetcher=json_fetcher,
        submissions_base_url=submissions_base_url,
    )
    return select_reporting_period_pair(
        filing_records,
        current_period=normalized_current,
        previous_period=normalized_previous,
    )


def _build_filings_metadata(
    current_snapshot: SEC13FPeriodSnapshot,
    previous_snapshot: SEC13FPeriodSnapshot,
) -> PositionDiffFilings:
    def _ref(filing: ParsedSEC13FFiling) -> PositionDiffFilingRef:
        return PositionDiffFilingRef(
            accession_number=filing.metadata.accession_number,
            filing_date=filing.metadata.filing_date,
            form=filing.metadata.form,
            amendment_type=filing.metadata.amendment_type,
        )

    return PositionDiffFilings(
        current=_ref(current_snapshot.primary_filing),
        previous=_ref(previous_snapshot.primary_filing),
        current_supplemental_amendments=[_ref(item) for item in current_snapshot.supplemental_amendments],
        previous_supplemental_amendments=[_ref(item) for item in previous_snapshot.supplemental_amendments],
    )


def load_13f_period_snapshot_from_cache(
    db: Session,
    *,
    institution_cik: str,
    report_period: date | str,
) -> SEC13FPeriodSnapshot | None:
    normalized_cik = normalize_cik(institution_cik)
    normalized_period = normalize_reporting_period(report_period)
    cache_row = (
        db.query(Institutional13FPeriodCache)
        .filter(
            Institutional13FPeriodCache.institution_cik == normalized_cik,
            Institutional13FPeriodCache.report_period == normalized_period,
        )
        .one_or_none()
    )
    if cache_row is None:
        return None

    primary_metadata = ParsedSEC13FMetadata(
        cik=cache_row.institution_cik,
        accession_number=cache_row.primary_accession_number,
        form=cache_row.primary_form,
        filing_date=cache_row.primary_filing_date,
        report_period=cache_row.report_period,
        filing_manager_name=cache_row.institution_name,
        is_amendment=bool(cache_row.primary_is_amendment),
        amendment_type=cache_row.primary_amendment_type,
        amendment_no=cache_row.primary_amendment_no,
        is_confidential_omitted=bool(cache_row.primary_is_confidential_omitted),
    )
    positions = [
        PositionSnapshotEntry(
            issuer_name=position.issuer_name,
            ticker=position.ticker,
            ticker_resolution_method=position.ticker_resolution_method,
            cusip=position.cusip,
            security_title=position.security_title,
            put_call=position.put_call,
            shares=float(position.shares),
            reported_value_usd=float(position.reported_value_usd),
            accession_number=position.accession_number,
            filing_date=position.filing_date,
            raw_row_index=position.raw_row_index,
        )
        for position in cache_row.positions
    ]
    primary_filing = ParsedSEC13FFiling(
        metadata=primary_metadata,
        positions=[
            entry.model_copy(deep=True)
            for entry in positions
            if entry.accession_number == cache_row.primary_accession_number
        ],
    )
    supplemental_amendments = [
        ParsedSEC13FFiling(
            metadata=ParsedSEC13FMetadata(
                cik=cache_row.institution_cik,
                accession_number=amendment.accession_number,
                form=amendment.form,
                filing_date=amendment.filing_date,
                report_period=cache_row.report_period,
                filing_manager_name=cache_row.institution_name,
                is_amendment=True,
                amendment_type=amendment.amendment_type,
                amendment_no=amendment.amendment_no,
                is_confidential_omitted=bool(amendment.is_confidential_omitted),
            ),
            positions=[
                entry.model_copy(deep=True)
                for entry in positions
                if entry.accession_number == amendment.accession_number
            ],
        )
        for amendment in cache_row.supplemental_amendments
    ]
    return SEC13FPeriodSnapshot(
        institution_name=cache_row.institution_name,
        cik=cache_row.institution_cik,
        report_period=cache_row.report_period,
        primary_filing=primary_filing,
        supplemental_amendments=supplemental_amendments,
        positions=positions,
        warnings=[_warning_from_json(item) for item in (cache_row.warnings_json or [])],
        data_quality=_data_quality_from_json(cache_row.data_quality_json),
    )


def upsert_13f_period_snapshot_cache(
    db: Session,
    snapshot: SEC13FPeriodSnapshot,
    *,
    commit: bool = True,
) -> SEC13FPeriodSnapshot:
    normalized_cik = normalize_cik(snapshot.cik)
    normalized_period = normalize_reporting_period(snapshot.report_period)
    cache_row = (
        db.query(Institutional13FPeriodCache)
        .filter(
            Institutional13FPeriodCache.institution_cik == normalized_cik,
            Institutional13FPeriodCache.report_period == normalized_period,
        )
        .one_or_none()
    )
    if cache_row is None:
        cache_row = Institutional13FPeriodCache(
            institution_cik=normalized_cik,
            report_period=normalized_period,
        )
        db.add(cache_row)

    cache_row.institution_name = snapshot.institution_name
    cache_row.primary_accession_number = snapshot.primary_filing.metadata.accession_number
    cache_row.primary_form = snapshot.primary_filing.metadata.form
    cache_row.primary_filing_date = snapshot.primary_filing.metadata.filing_date
    cache_row.primary_is_amendment = snapshot.primary_filing.metadata.is_amendment
    cache_row.primary_is_confidential_omitted = (
        snapshot.primary_filing.metadata.is_confidential_omitted
    )
    cache_row.primary_amendment_type = snapshot.primary_filing.metadata.amendment_type
    cache_row.primary_amendment_no = snapshot.primary_filing.metadata.amendment_no
    cache_row.warnings_json = [_warning_to_json(item) for item in snapshot.warnings]
    cache_row.data_quality_json = _data_quality_to_json(snapshot.data_quality)

    if cache_row.id is not None:
        cache_row.supplemental_amendments.clear()
        cache_row.positions.clear()
        db.flush()

    cache_row.supplemental_amendments = [
        Institutional13FSupplementalAmendmentCache(
            sort_order=index,
            accession_number=filing.metadata.accession_number,
            form=filing.metadata.form,
            filing_date=filing.metadata.filing_date,
            amendment_type=filing.metadata.amendment_type,
            amendment_no=filing.metadata.amendment_no,
            is_confidential_omitted=filing.metadata.is_confidential_omitted,
        )
        for index, filing in enumerate(snapshot.supplemental_amendments)
    ]
    cache_row.positions = [
        Institutional13FPositionCache(
            sort_order=index,
            accession_number=position.accession_number,
            filing_date=position.filing_date,
            issuer_name=position.issuer_name,
            ticker=position.ticker,
            ticker_resolution_method=position.ticker_resolution_method,
            cusip=position.cusip,
            security_title=position.security_title,
            put_call=position.put_call,
            shares=float(position.shares),
            reported_value_usd=float(position.reported_value_usd),
            raw_row_index=position.raw_row_index,
        )
        for index, position in enumerate(snapshot.positions)
    ]

    db.flush()
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(cache_row)
    return load_13f_period_snapshot_from_cache(
        db,
        institution_cik=normalized_cik,
        report_period=normalized_period,
    ) or snapshot


def get_or_fetch_13f_period_snapshot(
    db: Session,
    *,
    institution_cik: str,
    report_period: date | str,
    json_fetcher: JsonFetcher | None = None,
    text_fetcher: TextFetcher | None = None,
    submissions_base_url: str = "https://data.sec.gov/submissions",
    archives_base_url: str = "https://www.sec.gov/Archives/edgar/data",
    commit: bool = True,
) -> SEC13FPeriodSnapshot:
    cached = load_13f_period_snapshot_from_cache(
        db,
        institution_cik=institution_cik,
        report_period=report_period,
    )
    if cached is not None:
        return cached

    filing_records = fetch_13f_filing_records(
        institution_cik,
        json_fetcher=json_fetcher,
        submissions_base_url=submissions_base_url,
    )
    period_records = filter_filing_records_for_period(filing_records, report_period)
    if not period_records:
        raise ValueError("No 13F filings were found for the requested reporting period")
    snapshot = build_13f_reporting_period_snapshot(
        period_records,
        json_fetcher=json_fetcher,
        text_fetcher=text_fetcher,
        archives_base_url=archives_base_url,
    )
    return upsert_13f_period_snapshot_cache(db, snapshot, commit=commit)


def get_institutional_position_diff(
    db: Session,
    request: PositionDiffRequest,
    *,
    json_fetcher: JsonFetcher | None = None,
    text_fetcher: TextFetcher | None = None,
    submissions_base_url: str = "https://data.sec.gov/submissions",
    archives_base_url: str = "https://www.sec.gov/Archives/edgar/data",
    commit: bool = True,
) -> PositionDiffResponse:
    current_period, previous_period = _resolve_position_diff_periods(
        db,
        institution_cik=request.institution_cik,
        current_period=request.current_period,
        previous_period=request.previous_period,
        json_fetcher=json_fetcher,
        submissions_base_url=submissions_base_url,
    )
    current_snapshot = load_13f_period_snapshot_from_cache(
        db,
        institution_cik=request.institution_cik,
        report_period=current_period,
    )
    previous_snapshot = load_13f_period_snapshot_from_cache(
        db,
        institution_cik=request.institution_cik,
        report_period=previous_period,
    )

    if current_snapshot is None or previous_snapshot is None:
        filing_records = fetch_13f_filing_records(
            request.institution_cik,
            json_fetcher=json_fetcher,
            submissions_base_url=submissions_base_url,
        )
        if current_snapshot is None:
            current_records = filter_filing_records_for_period(filing_records, current_period)
            if not current_records:
                raise ValueError("No 13F filings were found for requested reporting period")
            current_snapshot = upsert_13f_period_snapshot_cache(
                db,
                build_13f_reporting_period_snapshot(
                    current_records,
                    json_fetcher=json_fetcher,
                    text_fetcher=text_fetcher,
                    archives_base_url=archives_base_url,
                ),
                commit=commit,
            )
        if previous_snapshot is None:
            previous_records = filter_filing_records_for_period(filing_records, previous_period)
            if not previous_records:
                raise ValueError("No 13F filings were found for requested reporting period")
            previous_snapshot = upsert_13f_period_snapshot_cache(
                db,
                build_13f_reporting_period_snapshot(
                    previous_records,
                    json_fetcher=json_fetcher,
                    text_fetcher=text_fetcher,
                    archives_base_url=archives_base_url,
                ),
                commit=commit,
            )

    combined_data_quality = PositionDiffDataQuality(
        comparison_complete=(
            current_snapshot.data_quality.comparison_complete
            and previous_snapshot.data_quality.comparison_complete
        ),
        current_filing_complete=current_snapshot.data_quality.current_filing_complete,
        previous_filing_complete=previous_snapshot.data_quality.previous_filing_complete,
        ticker_enrichment_complete=(
            current_snapshot.data_quality.ticker_enrichment_complete
            and previous_snapshot.data_quality.ticker_enrichment_complete
        ),
        confidential_omissions_possible=(
            current_snapshot.data_quality.confidential_omissions_possible
            or previous_snapshot.data_quality.confidential_omissions_possible
        ),
    )

    response = compare_position_snapshots(
        institution_name=current_snapshot.institution_name,
        institution_cik=request.institution_cik,
        current_period=current_period,
        previous_period=previous_period,
        current_positions=current_snapshot.positions,
        previous_positions=previous_snapshot.positions,
        filter_status=request.status,
        sort_by=request.sort_by.value,
        sort_dir=request.sort_dir.value,
        limit=request.limit,
        offset=request.offset,
        warnings=[*current_snapshot.warnings, *previous_snapshot.warnings],
        data_quality=combined_data_quality,
        ticker=request.ticker,
        cusip=request.cusip,
    )
    response.filings = _build_filings_metadata(current_snapshot, previous_snapshot)
    return response


def build_position_key(entry: PositionSnapshotEntry) -> str:
    normalized_cusip = normalize_cusip(entry.cusip)
    normalized_title = normalize_security_title(entry.security_title) or ""
    normalized_put_call = normalize_put_call(entry.put_call) or ""
    if normalized_cusip:
        return f"cusip:{normalized_cusip}|title:{normalized_title}|pc:{normalized_put_call}"

    normalized_issuer = normalize_issuer_name(entry.issuer_name)
    if not normalized_issuer:
        raise ValueError("issuer_name is required when cusip is missing")
    return f"issuer:{normalized_issuer}|title:{normalized_title}|pc:{normalized_put_call}"


def _compatible_nullable_text(left: str | None, right: str | None) -> bool:
    return left is None or right is None or left == right


def _entries_compatible(left: PositionSnapshotEntry, right: PositionSnapshotEntry) -> bool:
    if build_position_key(left) != build_position_key(right):
        return False
    if normalize_issuer_name(left.issuer_name) != normalize_issuer_name(right.issuer_name):
        return False
    if normalize_security_title(left.security_title) != normalize_security_title(right.security_title):
        return False
    if normalize_put_call(left.put_call) != normalize_put_call(right.put_call):
        return False
    if normalize_cusip(left.cusip) != normalize_cusip(right.cusip):
        return False
    if not _compatible_nullable_text(canonical_ticker(left.ticker), canonical_ticker(right.ticker)):
        return False
    if not _compatible_nullable_text(left.ticker_resolution_method, right.ticker_resolution_method):
        return False
    if not _compatible_nullable_text(left.accession_number, right.accession_number):
        return False
    if left.filing_date and right.filing_date and left.filing_date != right.filing_date:
        return False
    return True


def _merge_entries(entries: Sequence[PositionSnapshotEntry]) -> PositionSnapshotEntry:
    merged = entries[0].model_copy(deep=True)
    merged.shares = float(sum(item.shares for item in entries))
    merged.reported_value_usd = float(sum(item.reported_value_usd for item in entries))
    merged.raw_row_index = None

    for item in entries[1:]:
        if merged.ticker is None and item.ticker is not None:
            merged.ticker = item.ticker
        if merged.ticker_resolution_method is None and item.ticker_resolution_method is not None:
            merged.ticker_resolution_method = item.ticker_resolution_method
        if merged.accession_number is None and item.accession_number is not None:
            merged.accession_number = item.accession_number
        if merged.filing_date is None and item.filing_date is not None:
            merged.filing_date = item.filing_date
    return merged


def group_compatible_positions(entries: Iterable[PositionSnapshotEntry]) -> GroupedPositionsResult:
    warnings: list[PositionDiffWarning] = []
    grouped: dict[str, list[PositionSnapshotEntry]] = defaultdict(list)
    for entry in entries:
        grouped[build_position_key(entry)].append(entry)

    aggregated: list[PositionSnapshotEntry] = []
    ambiguous_groups: dict[str, list[PositionSnapshotEntry]] = {}

    for key, members in grouped.items():
        if len(members) == 1:
            aggregated.append(members[0])
            continue

        compatible = [members[0]]
        conflicting: list[PositionSnapshotEntry] = []
        for member in members[1:]:
            if all(_entries_compatible(member, seen) for seen in compatible):
                compatible.append(member)
            else:
                conflicting.append(member)

        if conflicting:
            ambiguous_groups[key] = members
            warnings.append(
                PositionDiffWarning(
                    code="ambiguous_duplicate_group",
                    message="Positions with the same normalized key had materially conflicting fields.",
                    key=key,
                )
            )
            continue

        aggregated.append(_merge_entries(compatible))
        warnings.append(
            PositionDiffWarning(
                code="aggregated_duplicate_group",
                message="Compatible duplicate rows were aggregated.",
                key=key,
            )
        )

    return GroupedPositionsResult(
        positions=aggregated,
        warnings=warnings,
        ambiguous_groups=ambiguous_groups,
    )


def compute_share_pct_change(current_shares: float, previous_shares: float) -> float | None:
    if previous_shares == 0 and current_shares > 0:
        return None
    if previous_shares > 0 and current_shares == 0:
        return -100.0
    if previous_shares == 0 and current_shares == 0:
        return 0.0
    return ((current_shares - previous_shares) / previous_shares) * 100.0


def build_highlights(
    positions: Sequence[PositionDiffPosition], top_n: int = 10
) -> PositionDiffHighlights:
    buyer_status_rank = {
        PositionDiffStatus.INCREASED: 0,
        PositionDiffStatus.NEW: 1,
    }
    largest_buyers = sorted(
        [p for p in positions if p.status in (PositionDiffStatus.NEW, PositionDiffStatus.INCREASED)],
        key=lambda p: (
            buyer_status_rank[p.status],
            -p.reported_value_diff_usd,
            p.issuer_name,
        ),
    )[:top_n]
    largest_sellers = sorted(
        [p for p in positions if p.status in (PositionDiffStatus.REDUCED, PositionDiffStatus.EXITED)],
        key=lambda p: (
            p.reported_value_diff_usd,
            p.issuer_name,
        ),
    )[:top_n]
    new_positions = [p for p in positions if p.status == PositionDiffStatus.NEW][:top_n]
    complete_exits = [p for p in positions if p.status == PositionDiffStatus.EXITED][:top_n]
    return PositionDiffHighlights(
        largest_buyers=largest_buyers,
        largest_sellers=largest_sellers,
        new_positions=new_positions,
        complete_exits=complete_exits,
    )


def _sort_positions(
    positions: list[PositionDiffPosition], sort_by: str, sort_dir: str
) -> list[PositionDiffPosition]:
    reverse = sort_dir == "desc"
    if sort_by == "reported_value_diff_usd":
        key = lambda item: item.reported_value_diff_usd
    elif sort_by == "share_diff":
        key = lambda item: item.share_diff
    elif sort_by == "current_reported_value_usd":
        key = lambda item: item.current_reported_value_usd
    elif sort_by == "previous_reported_value_usd":
        key = lambda item: item.previous_reported_value_usd
    elif sort_by == "issuer_name":
        key = lambda item: item.issuer_name
    elif sort_by == "status":
        key = lambda item: item.status.value
    else:
        raise ValueError(f"unsupported sort field: {sort_by}")
    return sorted(positions, key=key, reverse=reverse)


def _filter_positions(
    positions: list[PositionDiffPosition], filter_status: PositionDiffFilterStatus
) -> list[PositionDiffPosition]:
    if filter_status == PositionDiffFilterStatus.ALL:
        return positions
    if filter_status == PositionDiffFilterStatus.CHANGED:
        return [
            item for item in positions
            if item.status in (
                PositionDiffStatus.NEW,
                PositionDiffStatus.INCREASED,
                PositionDiffStatus.REDUCED,
                PositionDiffStatus.EXITED,
            )
        ]
    return [item for item in positions if item.status.value == filter_status.value]


def _filter_position_identity(
    positions: list[PositionDiffPosition],
    *,
    ticker: str | None = None,
    cusip: str | None = None,
) -> list[PositionDiffPosition]:
    normalized_ticker = canonical_ticker(ticker)
    normalized_cusip = normalize_cusip(cusip)
    filtered = positions
    if normalized_ticker is not None:
        filtered = [item for item in filtered if canonical_ticker(item.ticker) == normalized_ticker]
    if normalized_cusip is not None:
        filtered = [item for item in filtered if normalize_cusip(item.cusip) == normalized_cusip]
    return filtered


def compare_position_snapshots(
    *,
    institution_name: str,
    institution_cik: str,
    current_period: date,
    previous_period: date,
    current_positions: Sequence[PositionSnapshotEntry],
    previous_positions: Sequence[PositionSnapshotEntry],
    filter_status: PositionDiffFilterStatus = PositionDiffFilterStatus.CHANGED,
    sort_by: str = "reported_value_diff_usd",
    sort_dir: str = "desc",
    limit: int = 100,
    offset: int = 0,
    warnings: Sequence[PositionDiffWarning] | None = None,
    data_quality: PositionDiffDataQuality | None = None,
    ticker: str | None = None,
    cusip: str | None = None,
) -> PositionDiffResponse:
    current_grouped = group_compatible_positions(current_positions)
    previous_grouped = group_compatible_positions(previous_positions)

    ambiguity_keys = set(current_grouped.ambiguous_groups) | set(previous_grouped.ambiguous_groups)
    if ambiguity_keys:
        raise PositionAmbiguityError(
            "Ambiguous duplicate positions prevent deterministic comparison: "
            + ", ".join(sorted(ambiguity_keys))
        )

    combined_warnings = list(warnings or [])
    combined_warnings.extend(current_grouped.warnings)
    combined_warnings.extend(previous_grouped.warnings)

    current_by_key = {build_position_key(item): item for item in current_grouped.positions}
    previous_by_key = {build_position_key(item): item for item in previous_grouped.positions}
    all_keys = set(current_by_key) | set(previous_by_key)

    positions: list[PositionDiffPosition] = []
    ticker_enrichment_complete = True

    for key in sorted(all_keys):
        current_item = current_by_key.get(key)
        previous_item = previous_by_key.get(key)

        current_shares = float(current_item.shares) if current_item else 0.0
        previous_shares = float(previous_item.shares) if previous_item else 0.0
        current_value = float(current_item.reported_value_usd) if current_item else 0.0
        previous_value = float(previous_item.reported_value_usd) if previous_item else 0.0

        if current_item is not None and previous_item is None:
            status = PositionDiffStatus.NEW
            base_item = current_item
        elif current_item is None and previous_item is not None:
            status = PositionDiffStatus.EXITED
            base_item = previous_item
        elif current_shares > previous_shares:
            status = PositionDiffStatus.INCREASED
            base_item = current_item or previous_item
        elif current_shares < previous_shares:
            status = PositionDiffStatus.REDUCED
            base_item = current_item or previous_item
        else:
            status = PositionDiffStatus.UNCHANGED
            base_item = current_item or previous_item

        if base_item.ticker is None:
            ticker_enrichment_complete = False

        positions.append(
            PositionDiffPosition(
                institution_name=institution_name,
                institution_cik=normalize_cik(institution_cik),
                issuer_name=base_item.issuer_name,
                ticker=canonical_ticker(base_item.ticker),
                ticker_resolution_method=base_item.ticker_resolution_method,
                cusip=normalize_cusip(base_item.cusip),
                security_title=normalize_security_title(base_item.security_title),
                put_call=normalize_put_call(base_item.put_call),
                current_period=current_period,
                previous_period=previous_period,
                current_shares=current_shares,
                previous_shares=previous_shares,
                share_diff=current_shares - previous_shares,
                share_pct_change=compute_share_pct_change(current_shares, previous_shares),
                current_reported_value_usd=current_value,
                previous_reported_value_usd=previous_value,
                reported_value_diff_usd=current_value - previous_value,
                status=status,
                current_accession_number=current_item.accession_number if current_item else None,
                previous_accession_number=previous_item.accession_number if previous_item else None,
                current_filing_date=current_item.filing_date if current_item else None,
                previous_filing_date=previous_item.filing_date if previous_item else None,
            )
        )

    summary = PositionDiffSummary(
        current_position_count=len(current_grouped.positions),
        previous_position_count=len(previous_grouped.positions),
        new_count=sum(1 for p in positions if p.status == PositionDiffStatus.NEW),
        increased_count=sum(1 for p in positions if p.status == PositionDiffStatus.INCREASED),
        reduced_count=sum(1 for p in positions if p.status == PositionDiffStatus.REDUCED),
        unchanged_count=sum(1 for p in positions if p.status == PositionDiffStatus.UNCHANGED),
        exited_count=sum(1 for p in positions if p.status == PositionDiffStatus.EXITED),
        current_total_reported_value_usd=float(sum(p.current_reported_value_usd for p in positions)),
        previous_total_reported_value_usd=float(sum(p.previous_reported_value_usd for p in positions)),
        total_reported_value_diff_usd=float(sum(p.reported_value_diff_usd for p in positions)),
        total_share_diff=float(sum(p.share_diff for p in positions)),
    )

    filtered = _filter_positions(positions, filter_status)
    filtered = _filter_position_identity(filtered, ticker=ticker, cusip=cusip)
    sorted_positions = _sort_positions(filtered, sort_by, sort_dir)
    paginated = sorted_positions[offset : offset + limit]

    final_quality = data_quality.model_copy(deep=True) if data_quality else PositionDiffDataQuality()
    final_quality.ticker_enrichment_complete = (
        final_quality.ticker_enrichment_complete and ticker_enrichment_complete
    )

    return PositionDiffResponse(
        institution=PositionDiffInstitution(name=institution_name, cik=normalize_cik(institution_cik)),
        periods=PositionDiffPeriods(current=current_period, previous=previous_period),
        summary=summary,
        highlights=build_highlights(positions),
        positions=paginated,
        pagination=PositionDiffPagination(
            limit=limit,
            offset=offset,
            returned=len(paginated),
            total_matching=len(filtered),
        ),
        data_quality=final_quality,
        warnings=combined_warnings,
    )
