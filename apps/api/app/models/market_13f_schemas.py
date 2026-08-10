from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PositionDiffStatus(str, Enum):
    NEW = "new"
    INCREASED = "increased"
    REDUCED = "reduced"
    UNCHANGED = "unchanged"
    EXITED = "exited"


class PositionDiffFilterStatus(str, Enum):
    CHANGED = "changed"
    NEW = "new"
    INCREASED = "increased"
    REDUCED = "reduced"
    UNCHANGED = "unchanged"
    EXITED = "exited"
    ALL = "all"


class PositionDiffSortField(str, Enum):
    REPORTED_VALUE_DIFF_USD = "reported_value_diff_usd"
    SHARE_DIFF = "share_diff"
    CURRENT_REPORTED_VALUE_USD = "current_reported_value_usd"
    PREVIOUS_REPORTED_VALUE_USD = "previous_reported_value_usd"
    ISSUER_NAME = "issuer_name"
    STATUS = "status"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class PutCallValue(str, Enum):
    PUT = "PUT"
    CALL = "CALL"


class PositionDiffRequest(BaseModel):
    institution_cik: str
    current_period: Optional[date] = None
    previous_period: Optional[date] = None
    status: PositionDiffFilterStatus = PositionDiffFilterStatus.CHANGED
    ticker: Optional[str] = None
    cusip: Optional[str] = None
    sort_by: PositionDiffSortField = PositionDiffSortField.REPORTED_VALUE_DIFF_USD
    sort_dir: SortDirection = SortDirection.DESC
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class PositionDiffWarning(BaseModel):
    code: str
    message: str
    key: Optional[str] = None


class PositionDiffDataQuality(BaseModel):
    comparison_complete: bool = True
    current_filing_complete: bool = True
    previous_filing_complete: bool = True
    ticker_enrichment_complete: bool = True
    confidential_omissions_possible: bool = False


class PositionDiffFreshness(BaseModel):
    status: str
    threshold_days: int
    as_of_date: date
    filing_date: Optional[date] = None
    age_days: Optional[int] = None
    message: str


class PositionSnapshotEntry(BaseModel):
    issuer_name: str
    ticker: Optional[str] = None
    ticker_resolution_method: Optional[str] = None
    cusip: Optional[str] = None
    security_title: Optional[str] = None
    put_call: Optional[str] = None
    shares: float = 0
    reported_value_usd: float = 0
    accession_number: Optional[str] = None
    filing_date: Optional[date] = None
    raw_row_index: Optional[int] = None


class PositionDiffPosition(BaseModel):
    institution_name: str
    institution_cik: str
    issuer_name: str
    ticker: Optional[str] = None
    ticker_resolution_method: Optional[str] = None
    cusip: Optional[str] = None
    security_title: Optional[str] = None
    put_call: Optional[str] = None
    current_period: date
    previous_period: date
    current_shares: float = 0
    previous_shares: float = 0
    share_diff: float = 0
    share_pct_change: Optional[float] = None
    current_reported_value_usd: float = 0
    previous_reported_value_usd: float = 0
    reported_value_diff_usd: float = 0
    status: PositionDiffStatus
    current_accession_number: Optional[str] = None
    previous_accession_number: Optional[str] = None
    current_filing_date: Optional[date] = None
    previous_filing_date: Optional[date] = None


class PositionDiffHighlights(BaseModel):
    largest_buyers: list[PositionDiffPosition] = Field(default_factory=list)
    largest_sellers: list[PositionDiffPosition] = Field(default_factory=list)
    new_positions: list[PositionDiffPosition] = Field(default_factory=list)
    complete_exits: list[PositionDiffPosition] = Field(default_factory=list)


class PositionDiffSummary(BaseModel):
    current_position_count: int = 0
    previous_position_count: int = 0
    new_count: int = 0
    increased_count: int = 0
    reduced_count: int = 0
    unchanged_count: int = 0
    exited_count: int = 0
    current_total_reported_value_usd: float = 0
    previous_total_reported_value_usd: float = 0
    total_reported_value_diff_usd: float = 0
    total_share_diff: float = 0


class PositionDiffPagination(BaseModel):
    limit: int
    offset: int
    returned: int
    total_matching: int


class PositionDiffInstitution(BaseModel):
    name: str
    cik: str


class PositionDiffPeriods(BaseModel):
    current: date
    previous: date


class PositionDiffFilingRef(BaseModel):
    accession_number: Optional[str] = None
    filing_date: Optional[date] = None
    form: Optional[str] = None
    amendment_type: Optional[str] = None


class PositionDiffFilings(BaseModel):
    current: Optional[PositionDiffFilingRef] = None
    previous: Optional[PositionDiffFilingRef] = None
    current_supplemental_amendments: list[PositionDiffFilingRef] = Field(default_factory=list)
    previous_supplemental_amendments: list[PositionDiffFilingRef] = Field(default_factory=list)


class PositionDiffResponse(BaseModel):
    institution: PositionDiffInstitution
    periods: PositionDiffPeriods
    filings: PositionDiffFilings = Field(default_factory=PositionDiffFilings)
    freshness: Optional[PositionDiffFreshness] = None
    summary: PositionDiffSummary
    highlights: PositionDiffHighlights
    positions: list[PositionDiffPosition]
    pagination: PositionDiffPagination
    data_quality: PositionDiffDataQuality
    warnings: list[PositionDiffWarning] = Field(default_factory=list)
