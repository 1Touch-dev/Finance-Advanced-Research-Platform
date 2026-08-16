"""
Legal Proceedings Extraction & Litigation Reserve Tracking (Band C #50-51)
────────────────────────────────────────────────────────────────────────────────
#50: Legal proceedings extraction - Item 103 + contingency notes → structured
#51: Litigation reserve tracking - Feeds M11 Sloan accruals
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class CaseType(Enum):
    """Classification of legal matter type."""
    SECURITIES = "securities"
    ANTITRUST = "antitrust"
    PATENT = "patent"
    PRODUCT_LIABILITY = "product_liability"
    EMPLOYMENT = "employment"
    ENVIRONMENTAL = "environmental"
    REGULATORY = "regulatory"
    CONTRACT = "contract"
    GOVERNMENT_INVESTIGATION = "government_investigation"
    CLASS_ACTION = "class_action"
    DERIVATIVE = "derivative"
    OTHER = "other"


class CaseStatus(Enum):
    """Status of a legal matter."""
    PENDING = "pending"
    ACTIVE = "active"
    SETTLED = "settled"
    DISMISSED = "dismissed"
    JUDGMENT = "judgment"
    APPEAL = "appeal"
    UNKNOWN = "unknown"


class MaterialityAssessment(Enum):
    """Management's assessment of outcome probability."""
    PROBABLE = "probable"
    REASONABLY_POSSIBLE = "reasonably_possible"
    REMOTE = "remote"
    NOT_STATED = "not_stated"


@dataclass
class ExtractedProceeding:
    """A legal proceeding extracted from 10-K (#50)."""
    proceeding_id: str
    case_type: CaseType
    case_status: CaseStatus
    # Core information
    description: str
    venue: Optional[str] = None
    filing_date: Optional[str] = None
    parties: List[str] = field(default_factory=list)
    # Financial
    amount_claimed: Optional[float] = None
    amount_accrued: Optional[float] = None
    amount_settled: Optional[float] = None
    # Assessment
    materiality: MaterialityAssessment = MaterialityAssessment.NOT_STATED
    management_assessment: Optional[str] = None
    # Source
    source_filing: Optional[str] = None
    source_section: str = "Legal Proceedings"  # Item 103 or Contingencies
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proceeding_id": self.proceeding_id,
            "case_type": self.case_type.value,
            "case_status": self.case_status.value,
            "description": self.description,
            "venue": self.venue,
            "filing_date": self.filing_date,
            "parties": self.parties,
            "amount_claimed": self.amount_claimed,
            "amount_accrued": self.amount_accrued,
            "amount_settled": self.amount_settled,
            "materiality": self.materiality.value,
            "management_assessment": self.management_assessment,
            "source_filing": self.source_filing,
            "source_section": self.source_section,
            "extracted_at": self.extracted_at,
        }


@dataclass
class LitigationReserve:
    """A litigation reserve/accrual from financial statements (#51)."""
    reserve_id: str
    ticker: str
    as_of_date: str
    # Reserve amounts
    total_reserve: float
    reserve_for_probable: Optional[float] = None
    reserve_for_possible: Optional[float] = None
    # Changes
    prior_period_reserve: Optional[float] = None
    reserve_change: Optional[float] = None
    reserve_change_pct: Optional[float] = None
    # Context
    largest_matter_reserve: Optional[float] = None
    number_of_matters: Optional[int] = None
    # Analysis
    reserve_to_exposure_ratio: Optional[float] = None
    reserve_to_revenue_pct: Optional[float] = None
    reserve_to_equity_pct: Optional[float] = None
    reserve_adequacy: Optional[str] = None  # adequate, under-reserved, over-reserved
    # Source
    source_filing: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reserve_id": self.reserve_id,
            "ticker": self.ticker,
            "as_of_date": self.as_of_date,
            "total_reserve": self.total_reserve,
            "reserve_for_probable": self.reserve_for_probable,
            "reserve_for_possible": self.reserve_for_possible,
            "prior_period_reserve": self.prior_period_reserve,
            "reserve_change": self.reserve_change,
            "reserve_change_pct": self.reserve_change_pct,
            "largest_matter_reserve": self.largest_matter_reserve,
            "number_of_matters": self.number_of_matters,
            "reserve_to_exposure_ratio": self.reserve_to_exposure_ratio,
            "reserve_to_revenue_pct": self.reserve_to_revenue_pct,
            "reserve_to_equity_pct": self.reserve_to_equity_pct,
            "reserve_adequacy": self.reserve_adequacy,
            "source_filing": self.source_filing,
        }


@dataclass
class ReserveTimeSeries:
    """Historical litigation reserves for Sloan accrual analysis (#51)."""
    ticker: str
    company_name: str
    reserves: List[LitigationReserve] = field(default_factory=list)
    # Trend analysis
    trend_direction: Optional[str] = None  # increasing, decreasing, stable
    avg_reserve_change: Optional[float] = None
    reserve_volatility: Optional[float] = None
    # Flags
    significant_increase: bool = False
    significant_decrease: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "reserves": [r.to_dict() for r in self.reserves],
            "trend_direction": self.trend_direction,
            "avg_reserve_change": self.avg_reserve_change,
            "reserve_volatility": self.reserve_volatility,
            "significant_increase": self.significant_increase,
            "significant_decrease": self.significant_decrease,
        }


@dataclass
class LegalProceedingsReport:
    """Complete legal proceedings extraction report (#50)."""
    ticker: str
    company_name: str
    cik: str
    filing_date: str
    proceedings: List[ExtractedProceeding] = field(default_factory=list)
    reserves: Optional[LitigationReserve] = None
    # Summary
    total_proceedings: int = 0
    active_proceedings: int = 0
    total_exposure: float = 0.0
    total_accrued: float = 0.0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)
    # Risk flags
    has_securities_litigation: bool = False
    has_government_investigation: bool = False
    has_material_matters: bool = False
    management_overall_assessment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "cik": self.cik,
            "filing_date": self.filing_date,
            "proceedings": [p.to_dict() for p in self.proceedings],
            "reserves": self.reserves.to_dict() if self.reserves else None,
            "total_proceedings": self.total_proceedings,
            "active_proceedings": self.active_proceedings,
            "total_exposure": self.total_exposure,
            "total_accrued": self.total_accrued,
            "by_type": self.by_type,
            "by_status": self.by_status,
            "has_securities_litigation": self.has_securities_litigation,
            "has_government_investigation": self.has_government_investigation,
            "has_material_matters": self.has_material_matters,
            "management_overall_assessment": self.management_overall_assessment,
        }


# ── Extraction Patterns ───────────────────────────────────────────────────────

# Case type classification patterns
CASE_TYPE_PATTERNS = {
    CaseType.SECURITIES: re.compile(
        r"securities|10b-5|shareholder|stockholder derivative|"
        r"exchange act|securities act|sec violation|insider trading", re.I),
    CaseType.ANTITRUST: re.compile(
        r"antitrust|sherman act|monopol|price ?fix|market allocation|"
        r"unfair competition|competition law", re.I),
    CaseType.PATENT: re.compile(
        r"patent|infringement|intellectual property|trade secret|"
        r"misappropriation", re.I),
    CaseType.PRODUCT_LIABILITY: re.compile(
        r"product liability|defect|personal injury|wrongful death|"
        r"consumer protection", re.I),
    CaseType.EMPLOYMENT: re.compile(
        r"employment|discrimination|wrongful termination|wage|labor|"
        r"harassment|eeoc|nlrb|retaliation", re.I),
    CaseType.ENVIRONMENTAL: re.compile(
        r"environmental|epa|superfund|cercla|clean water|clean air|"
        r"pollution|contamination|hazardous", re.I),
    CaseType.REGULATORY: re.compile(
        r"regulatory|fda|ftc|cfpb|occ|fdic|sec enforcement|"
        r"consent decree|compliance", re.I),
    CaseType.CONTRACT: re.compile(
        r"breach of contract|contract dispute|vendor|supplier|"
        r"commercial dispute", re.I),
    CaseType.GOVERNMENT_INVESTIGATION: re.compile(
        r"investigation|inquiry|subpoena|grand jury|doj|"
        r"attorney general|prosecutor|criminal", re.I),
    CaseType.CLASS_ACTION: re.compile(r"class action|putative class", re.I),
    CaseType.DERIVATIVE: re.compile(r"derivative|shareholder demand", re.I),
}

# Status patterns
STATUS_PATTERNS = {
    CaseStatus.SETTLED: re.compile(
        r"settl|resolved|concluded|paid|compromised", re.I),
    CaseStatus.DISMISSED: re.compile(
        r"dismiss|thrown out|dropped|withdrawn", re.I),
    CaseStatus.JUDGMENT: re.compile(
        r"judgment|verdict|award|damages", re.I),
    CaseStatus.APPEAL: re.compile(r"appeal|appellate|circuit", re.I),
    CaseStatus.PENDING: re.compile(r"pending|ongoing|active|continue", re.I),
}

# Materiality assessment patterns
MATERIALITY_PATTERNS = {
    MaterialityAssessment.PROBABLE: re.compile(
        r"probable|likely|expected to|will result", re.I),
    MaterialityAssessment.REASONABLY_POSSIBLE: re.compile(
        r"reasonably possible|possible but|cannot be estimated|"
        r"uncertain|indeterminate", re.I),
    MaterialityAssessment.REMOTE: re.compile(
        r"remote|unlikely|not probable|meritless|without merit", re.I),
}

# Amount extraction pattern
AMOUNT_PATTERN = re.compile(
    r'\$\s*([\d,]+(?:\.\d+)?)\s*(billion|million|thousand)?', re.I)

AMOUNT_SCALE = {"billion": 1e9, "million": 1e6, "thousand": 1e3, None: 1}


def _parse_amount(text: str) -> Optional[float]:
    """Extract dollar amount from text."""
    match = AMOUNT_PATTERN.search(text)
    if match:
        value = float(match.group(1).replace(",", ""))
        scale = AMOUNT_SCALE.get((match.group(2) or "").lower() or None, 1)
        return value * scale
    return None


def _classify_case_type(text: str) -> CaseType:
    """Classify the type of legal matter."""
    for case_type, pattern in CASE_TYPE_PATTERNS.items():
        if pattern.search(text):
            return case_type
    return CaseType.OTHER


def _determine_status(text: str) -> CaseStatus:
    """Determine case status from description."""
    for status, pattern in STATUS_PATTERNS.items():
        if pattern.search(text):
            return status
    return CaseStatus.UNKNOWN


def _assess_materiality(text: str) -> MaterialityAssessment:
    """Determine management's materiality assessment."""
    for assessment, pattern in MATERIALITY_PATTERNS.items():
        if pattern.search(text):
            return assessment
    return MaterialityAssessment.NOT_STATED


def _extract_venue(text: str) -> Optional[str]:
    """Extract court/venue from text."""
    venue_pattern = re.compile(
        r"((?:U\.S\.\s+)?District Court[^.,;]{0,60}|"
        r"Court of Appeals[^.,;]{0,40}|"
        r"Delaware Court of Chancery|"
        r"State (?:Court|Supreme)[^.,;]{0,40}|"
        r"(?:Northern|Southern|Eastern|Western) District of [A-Z][a-z]+)",
        re.I)
    match = venue_pattern.search(text)
    return match.group(1).strip() if match else None


def _extract_filing_date(text: str) -> Optional[str]:
    """Extract filing/commencement date from text."""
    date_pattern = re.compile(
        r"\b(?:filed|commenced|initiated|began|started)\s+(?:in|on)?\s*"
        r"((?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{4})",
        re.I)
    match = date_pattern.search(text)
    return match.group(1).strip() if match else None


def _extract_parties(text: str) -> List[str]:
    """Extract party names from text."""
    parties = []
    # Look for "v." or "vs." patterns
    vs_pattern = re.compile(
        r"([A-Z][A-Za-z.,&\s]+?)\s+v\.?\s*(?:et al\.?)?\s+"
        r"([A-Z][A-Za-z.,&\s]+?)(?=[,.]|$)", re.I)
    matches = vs_pattern.findall(text)
    for m in matches:
        parties.extend([p.strip() for p in m if p.strip()])
    return parties[:10]  # Limit


# ── #50: Legal Proceedings Extraction ─────────────────────────────────────────


def extract_legal_proceedings(
    ticker: str,
    include_item_103: bool = True,
    include_contingencies: bool = True,
) -> LegalProceedingsReport:
    """
    Extract structured legal proceedings from 10-K (#50).

    Parses:
    - Item 103 (Legal Proceedings)
    - Note on Commitments and Contingencies
    - Footnotes mentioning litigation

    Args:
        ticker: Stock ticker
        include_item_103: Parse Item 103 section
        include_contingencies: Parse contingencies note

    Returns:
        LegalProceedingsReport with all extracted proceedings.
    """
    report = LegalProceedingsReport(
        ticker=ticker,
        company_name=ticker,
        cik="",
        filing_date="",
    )

    try:
        from app.connectors.sec_edgar_connector import get_filer_cik
        from app.connectors.filing_notes_connector import get_filing_notes

        cik = get_filer_cik(ticker)
        if not cik:
            logger.warning(f"Could not resolve CIK for {ticker}")
            return report

        report.cik = cik

        # Get filing notes (includes legal_matters from contingencies)
        notes = get_filing_notes(cik)
        if not notes:
            return report

        report.filing_date = notes.get("fiscal_period_end", "")

        # Process legal matters from contingencies note
        proceeding_id = 0
        for matter in notes.get("legal_matters", []):
            text = matter.get("text", "")
            if matter.get("is_assessment"):
                # This is management's overall assessment, not a specific matter
                report.management_overall_assessment = text[:500]
                continue

            proceeding_id += 1
            proceeding = ExtractedProceeding(
                proceeding_id=f"LP{proceeding_id:04d}",
                case_type=_classify_case_type(text),
                case_status=_determine_status(text),
                description=text[:1000],
                venue=matter.get("venue") or _extract_venue(text),
                filing_date=matter.get("first_date") or _extract_filing_date(text),
                parties=_extract_parties(text),
                amount_claimed=_parse_amount(text),
                materiality=_assess_materiality(text),
                source_section="Contingencies",
                source_filing=notes.get("accession"),
            )

            # Check for accrual/reserve mentions
            accrual_match = re.search(
                r"accru(?:ed|al)|reserve[ds]?\s+(?:of\s+)?\$\s*([\d,]+(?:\.\d+)?)\s*(billion|million)?",
                text, re.I)
            if accrual_match:
                proceeding.amount_accrued = _parse_amount(accrual_match.group(0))

            report.proceedings.append(proceeding)

        # Try to extract reserves from XBRL data
        report.reserves = _extract_litigation_reserves(ticker, cik)

        # Update summary
        report.total_proceedings = len(report.proceedings)
        report.active_proceedings = sum(
            1 for p in report.proceedings
            if p.case_status in [CaseStatus.PENDING, CaseStatus.ACTIVE, CaseStatus.APPEAL]
        )

        for p in report.proceedings:
            report.by_type[p.case_type.value] = report.by_type.get(p.case_type.value, 0) + 1
            report.by_status[p.case_status.value] = report.by_status.get(p.case_status.value, 0) + 1
            if p.amount_claimed:
                report.total_exposure += p.amount_claimed
            if p.amount_accrued:
                report.total_accrued += p.amount_accrued

        # Set flags
        report.has_securities_litigation = CaseType.SECURITIES.value in report.by_type
        report.has_government_investigation = CaseType.GOVERNMENT_INVESTIGATION.value in report.by_type
        report.has_material_matters = any(
            p.materiality == MaterialityAssessment.PROBABLE for p in report.proceedings
        )

    except Exception as e:
        logger.error(f"Error extracting legal proceedings for {ticker}: {e}")

    return report


# ── #51: Litigation Reserve Tracking ──────────────────────────────────────────


def _extract_litigation_reserves(
    ticker: str,
    cik: str,
) -> Optional[LitigationReserve]:
    """
    Extract litigation reserves from financial statements.

    Looks for:
    - Litigation accruals
    - Loss contingency reserves
    - Legal settlement accruals
    """
    try:
        from app.connectors.sec_edgar_connector import get_company_facts

        facts = get_company_facts(cik)
        if not facts:
            return None

        # Look for litigation-related XBRL tags
        litigation_tags = [
            "LossContingencyAccrualAtCarryingValue",
            "LitigationReserve",
            "LegalContingency",
            "AccruedLitigationCurrent",
            "AccruedLitigationNoncurrent",
            "LossContingencyEstimateOfPossibleLoss",
            "LossContingencyDamagesSoughtValue",
        ]

        us_gaap = facts.get("facts", {}).get("us-gaap", {})

        reserve_amount = 0.0
        as_of_date = None

        for tag in litigation_tags:
            tag_data = us_gaap.get(tag, {})
            units = tag_data.get("units", {})
            usd_values = units.get("USD", [])

            if usd_values:
                # Get most recent value
                most_recent = max(usd_values, key=lambda x: x.get("end", ""))
                val = most_recent.get("val", 0)
                if val > reserve_amount:
                    reserve_amount = val
                    as_of_date = most_recent.get("end")

        if reserve_amount > 0:
            return LitigationReserve(
                reserve_id=f"RES-{ticker}-{as_of_date or 'current'}",
                ticker=ticker,
                as_of_date=as_of_date or datetime.now().strftime("%Y-%m-%d"),
                total_reserve=reserve_amount,
            )

    except Exception as e:
        logger.debug(f"Could not extract reserves for {ticker}: {e}")

    return None


def get_litigation_reserve_history(
    ticker: str,
    periods: int = 8,
) -> ReserveTimeSeries:
    """
    Get historical litigation reserves for trend analysis (#51).

    Args:
        ticker: Stock ticker
        periods: Number of periods to retrieve

    Returns:
        ReserveTimeSeries with historical reserves.
    """
    series = ReserveTimeSeries(
        ticker=ticker,
        company_name=ticker,
    )

    try:
        from app.connectors.sec_edgar_connector import get_filer_cik, get_company_facts

        cik = get_filer_cik(ticker)
        if not cik:
            return series

        facts = get_company_facts(cik)
        if not facts:
            return series

        # Look for litigation reserve data over time
        us_gaap = facts.get("facts", {}).get("us-gaap", {})

        reserve_tags = [
            "LossContingencyAccrualAtCarryingValue",
            "LitigationReserve",
            "LegalContingency",
        ]

        reserves_by_date: Dict[str, float] = {}

        for tag in reserve_tags:
            tag_data = us_gaap.get(tag, {})
            units = tag_data.get("units", {})
            usd_values = units.get("USD", [])

            for entry in usd_values:
                end_date = entry.get("end")
                val = entry.get("val", 0)
                if end_date and val:
                    # Keep the largest reserve for each date
                    if end_date not in reserves_by_date or val > reserves_by_date[end_date]:
                        reserves_by_date[end_date] = val

        # Sort by date and take most recent N periods
        sorted_dates = sorted(reserves_by_date.keys(), reverse=True)[:periods]

        prior_reserve = None
        for date in sorted_dates:
            amount = reserves_by_date[date]
            reserve = LitigationReserve(
                reserve_id=f"RES-{ticker}-{date}",
                ticker=ticker,
                as_of_date=date,
                total_reserve=amount,
            )

            if prior_reserve is not None:
                reserve.prior_period_reserve = prior_reserve
                reserve.reserve_change = amount - prior_reserve
                if prior_reserve > 0:
                    reserve.reserve_change_pct = (amount - prior_reserve) / prior_reserve * 100

            prior_reserve = amount
            series.reserves.append(reserve)

        # Analyze trend
        if len(series.reserves) >= 2:
            changes = [r.reserve_change for r in series.reserves if r.reserve_change is not None]
            if changes:
                series.avg_reserve_change = sum(changes) / len(changes)

                # Determine trend direction
                if series.avg_reserve_change > 0.1 * series.reserves[0].total_reserve:
                    series.trend_direction = "increasing"
                    series.significant_increase = True
                elif series.avg_reserve_change < -0.1 * series.reserves[0].total_reserve:
                    series.trend_direction = "decreasing"
                    series.significant_decrease = True
                else:
                    series.trend_direction = "stable"

                # Calculate volatility (std dev of changes)
                if len(changes) > 1:
                    avg = sum(changes) / len(changes)
                    variance = sum((c - avg) ** 2 for c in changes) / len(changes)
                    series.reserve_volatility = variance ** 0.5

    except Exception as e:
        logger.error(f"Error getting reserve history for {ticker}: {e}")

    return series


def analyze_reserve_adequacy(
    ticker: str,
) -> Dict[str, Any]:
    """
    Analyze whether litigation reserves are adequate vs exposure (#51).

    Compares:
    - Total reserves vs total exposure
    - Reserve coverage ratio
    - Industry benchmarks

    Returns:
        Analysis of reserve adequacy.
    """
    result = {
        "ticker": ticker,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "total_exposure": 0.0,
        "total_reserves": 0.0,
        "coverage_ratio": None,
        "adequacy_assessment": "unknown",
        "flags": [],
        "recommendations": [],
    }

    try:
        # Get proceedings
        proceedings = extract_legal_proceedings(ticker)
        result["total_exposure"] = proceedings.total_exposure
        result["total_reserves"] = proceedings.total_accrued

        if proceedings.reserves:
            result["total_reserves"] = max(
                result["total_reserves"],
                proceedings.reserves.total_reserve
            )

        # Calculate coverage ratio
        if result["total_exposure"] > 0:
            result["coverage_ratio"] = result["total_reserves"] / result["total_exposure"]

            if result["coverage_ratio"] >= 0.5:
                result["adequacy_assessment"] = "adequate"
            elif result["coverage_ratio"] >= 0.2:
                result["adequacy_assessment"] = "possibly_under_reserved"
                result["flags"].append("Coverage ratio below 50%")
            else:
                result["adequacy_assessment"] = "under_reserved"
                result["flags"].append("Coverage ratio below 20% - significant reserve risk")

        # Check for specific risk factors
        if proceedings.has_securities_litigation:
            result["flags"].append("Securities litigation present - high settlement risk")
        if proceedings.has_government_investigation:
            result["flags"].append("Government investigation - potential for significant penalties")

        # Add recommendations
        if result["adequacy_assessment"] == "under_reserved":
            result["recommendations"].append(
                "Consider increasing reserves given exposure level"
            )
        if proceedings.active_proceedings > 5:
            result["recommendations"].append(
                "Multiple active proceedings warrant close monitoring"
            )

    except Exception as e:
        logger.error(f"Error analyzing reserve adequacy for {ticker}: {e}")

    return result


def get_reserve_to_financial_ratios(
    ticker: str,
) -> Dict[str, Any]:
    """
    Calculate litigation reserve ratios vs financial metrics (#51).

    Returns ratios useful for Sloan accrual analysis.
    """
    result = {
        "ticker": ticker,
        "as_of_date": datetime.now().strftime("%Y-%m-%d"),
        "total_reserve": 0.0,
        "reserve_to_revenue": None,
        "reserve_to_assets": None,
        "reserve_to_equity": None,
        "reserve_to_operating_income": None,
        "flags": [],
    }

    try:
        from app.connectors.sec_edgar_connector import get_filer_cik
        from app.connectors.market_data_connector import get_company_fundamentals

        cik = get_filer_cik(ticker)
        if cik:
            reserve = _extract_litigation_reserves(ticker, cik)
            if reserve:
                result["total_reserve"] = reserve.total_reserve
                result["as_of_date"] = reserve.as_of_date

        # Get fundamentals for ratio calculation
        fundamentals = get_company_fundamentals(ticker)
        if fundamentals and result["total_reserve"] > 0:
            revenue = fundamentals.get("revenue")
            assets = fundamentals.get("total_assets")
            equity = fundamentals.get("total_equity") or fundamentals.get("book_value")
            operating_income = fundamentals.get("operating_income")

            if revenue and revenue > 0:
                result["reserve_to_revenue"] = result["total_reserve"] / revenue * 100
                if result["reserve_to_revenue"] > 5:
                    result["flags"].append("Reserve exceeds 5% of revenue")

            if assets and assets > 0:
                result["reserve_to_assets"] = result["total_reserve"] / assets * 100

            if equity and equity > 0:
                result["reserve_to_equity"] = result["total_reserve"] / equity * 100
                if result["reserve_to_equity"] > 10:
                    result["flags"].append("Reserve exceeds 10% of equity")

            if operating_income and operating_income > 0:
                result["reserve_to_operating_income"] = result["total_reserve"] / operating_income * 100

    except Exception as e:
        logger.debug(f"Could not calculate reserve ratios for {ticker}: {e}")

    return result
