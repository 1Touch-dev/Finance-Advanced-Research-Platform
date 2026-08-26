"""
Docket-to-Disclosure Reconciliation Service (Band B #31)
────────────────────────────────────────────────────────────────────────────
THE KEY L-SERIES FEATURE

Compares litigation on public court dockets to what companies disclose
in their SEC filings. Flags divergences where:
  - A lawsuit exists in CourtListener but isn't in the 10-K
  - Disclosure amounts differ from docket outcomes
  - Material litigation is mentioned differently across sources
  - Timing gaps between filing and disclosure

This is the core "L-series" feature that provides unique alpha.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import difflib

logger = logging.getLogger(__name__)


class DisclosureStatus(Enum):
    """Status of litigation disclosure reconciliation."""
    DISCLOSED = "disclosed"           # Found in both docket and 10-K
    UNDISCLOSED = "undisclosed"       # In docket, not in 10-K
    DISCLOSURE_ONLY = "disclosure_only"  # In 10-K, not found in docket
    PARTIAL = "partial"               # Mentioned but details differ
    RESOLVED = "resolved"             # Case closed, properly disclosed
    PENDING = "pending"               # Open case, not yet required to disclose


class MaterialityLevel(Enum):
    """Materiality classification for litigation."""
    CRITICAL = "critical"   # >10% of market cap or criminal
    HIGH = "high"          # >5% of market cap or significant regulatory
    MEDIUM = "medium"      # 1-5% of market cap
    LOW = "low"            # <1% of market cap
    UNKNOWN = "unknown"    # Amount not determinable


class DivergenceType(Enum):
    """Types of divergences found."""
    MISSING_DISCLOSURE = "missing_disclosure"       # Case not mentioned in 10-K
    AMOUNT_MISMATCH = "amount_mismatch"            # Different amounts claimed
    TIMING_GAP = "timing_gap"                       # Disclosure delayed vs filing date
    STATUS_MISMATCH = "status_mismatch"            # Different status (open vs closed)
    PARTY_MISMATCH = "party_mismatch"              # Different parties named
    MINIMIZATION = "minimization"                   # Disclosure downplays severity
    OUTCOME_NOT_UPDATED = "outcome_not_updated"     # Settlement not reflected


@dataclass
class DocketCase:
    """A case from the court docket."""
    case_id: str
    case_name: str
    court: str
    docket_number: str
    filed_date: str
    status: str  # open, closed, settled, dismissed
    parties: List[str]
    nature_of_suit: Optional[str] = None
    cause_of_action: Optional[str] = None
    amount_claimed: Optional[float] = None
    amount_awarded: Optional[float] = None
    judge: Optional[str] = None
    last_activity_date: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class DisclosedLitigation:
    """Litigation disclosed in SEC filings."""
    filing_type: str  # 10-K, 10-Q, 8-K
    filing_date: str
    accession_number: str
    description: str
    amount_disclosed: Optional[float] = None
    accrual_amount: Optional[float] = None
    outcome: Optional[str] = None
    parties_mentioned: List[str] = field(default_factory=list)
    section: str = "Legal Proceedings"  # Item 3 or Item 103
    management_assessment: Optional[str] = None  # "reasonably possible", "probable", "remote"
    source_text: Optional[str] = None


@dataclass
class ReconciliationFinding:
    """A finding from docket-to-disclosure reconciliation."""
    id: str
    divergence_type: DivergenceType
    disclosure_status: DisclosureStatus
    materiality: MaterialityLevel
    docket_case: Optional[DocketCase]
    disclosed_litigation: Optional[DisclosedLitigation]
    title: str
    description: str
    risk_score: float  # 0-100
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ReconciliationReport:
    """Complete reconciliation report for a company."""
    ticker: str
    company_name: str
    cik: str
    analysis_date: str
    docket_cases: List[DocketCase]
    disclosed_litigation: List[DisclosedLitigation]
    findings: List[ReconciliationFinding]
    summary: Dict[str, Any]
    risk_score: float
    generated_at: str


# ── Amount parsing patterns ────────────────────────────────────────────────────

AMOUNT_PATTERNS = [
    (r'\$([0-9,]+(?:\.[0-9]+)?)\s*(?:billion|bn)', 1e9),
    (r'\$([0-9,]+(?:\.[0-9]+)?)\s*(?:million|mm|m)', 1e6),
    (r'\$([0-9,]+(?:\.[0-9]+)?)\s*(?:thousand|k)', 1e3),
    (r'\$([0-9,]+(?:\.[0-9]+)?)', 1),
    (r'([0-9,]+(?:\.[0-9]+)?)\s*(?:billion|bn)\s*(?:dollars?)?', 1e9),
    (r'([0-9,]+(?:\.[0-9]+)?)\s*(?:million|mm|m)\s*(?:dollars?)?', 1e6),
]

MANAGEMENT_ASSESSMENT_PATTERNS = [
    (r'(reasonably possible|possible but not probable)', 'reasonably_possible'),
    (r'(probable|likely)', 'probable'),
    (r'(remote|unlikely)', 'remote'),
    (r'(material|significant)', 'material'),
    (r'(immaterial|not material|de minimis)', 'immaterial'),
]


def parse_amount(text: str) -> Optional[float]:
    """Extract dollar amount from text."""
    if not text:
        return None

    text = text.lower().replace(',', '')

    for pattern, multiplier in AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                value = float(match.group(1).replace(',', ''))
                return value * multiplier
            except ValueError:
                continue

    return None


def parse_management_assessment(text: str) -> Optional[str]:
    """Extract management's assessment of litigation outcome."""
    if not text:
        return None

    text_lower = text.lower()

    for pattern, assessment in MANAGEMENT_ASSESSMENT_PATTERNS:
        if re.search(pattern, text_lower):
            return assessment

    return None


def reconcile_litigation(
    ticker: str,
    lookback_years: int = 3,
) -> ReconciliationReport:
    """
    Reconcile court dockets against SEC disclosures.

    Args:
        ticker: Stock ticker symbol
        lookback_years: How many years of litigation to analyze

    Returns:
        ReconciliationReport with all findings
    """
    from app.connectors.sec_edgar_connector import (
        get_filer_cik,
        get_company_submissions,
    )
    from app.connectors.litigation_connector import search_federal_cases
    from app.connectors.filing_notes_connector import get_filing_notes

    logger.info(f"Reconciling litigation for {ticker}")

    # Get company info
    cik = get_filer_cik(ticker)
    if not cik:
        raise ValueError(f"Could not resolve CIK for ticker: {ticker}")

    submissions = get_company_submissions(cik)
    company_name = submissions.get("name", ticker) if submissions else ticker

    # Get docket cases
    docket_cases = _fetch_docket_cases(ticker, company_name, lookback_years)

    # Get disclosed litigation from filings
    disclosed = _fetch_disclosed_litigation(ticker, cik, lookback_years)

    # Reconcile
    findings = _reconcile_cases(docket_cases, disclosed, company_name)

    # Calculate overall risk score
    risk_score = _calculate_risk_score(findings)

    # Generate summary
    summary = _generate_summary(docket_cases, disclosed, findings)

    return ReconciliationReport(
        ticker=ticker,
        company_name=company_name,
        cik=cik,
        analysis_date=datetime.utcnow().strftime("%Y-%m-%d"),
        docket_cases=docket_cases,
        disclosed_litigation=disclosed,
        findings=findings,
        summary=summary,
        risk_score=risk_score,
        generated_at=datetime.utcnow().isoformat(),
    )


def _fetch_docket_cases(
    ticker: str,
    company_name: str,
    lookback_years: int,
) -> List[DocketCase]:
    """Fetch cases from court dockets."""
    cases = []

    try:
        from app.connectors.litigation_connector import search_federal_cases

        # Search CourtListener for cases
        result = search_federal_cases(company_name)

        if result and result.get("cases"):
            for case in result["cases"]:
                # Filter by date
                filed_date = case.get("date_filed", "")
                if filed_date:
                    try:
                        filed_dt = datetime.strptime(filed_date, "%Y-%m-%d")
                        cutoff = datetime.now() - timedelta(days=lookback_years * 365)
                        if filed_dt < cutoff:
                            continue
                    except ValueError as e:
                        logger.debug("Failed to parse filed date '%s': %s", filed_date, e)

                cases.append(DocketCase(
                    case_id=case.get("id", ""),
                    case_name=case.get("case_name", ""),
                    court=case.get("court", ""),
                    docket_number=case.get("docket_number", ""),
                    filed_date=filed_date,
                    status=case.get("status", "open"),
                    parties=[company_name],  # Simplified
                    nature_of_suit=case.get("nature_of_suit", ""),
                    cause_of_action=case.get("cause", ""),
                    amount_claimed=parse_amount(case.get("amount_claimed", "")),
                    source_url=case.get("url", ""),
                ))

    except Exception as e:
        logger.warning(f"Error fetching docket cases: {e}")

    return cases


def _fetch_disclosed_litigation(
    ticker: str,
    cik: str,
    lookback_years: int,
) -> List[DisclosedLitigation]:
    """Fetch disclosed litigation from SEC filings."""
    disclosed = []

    try:
        from app.connectors.filing_notes_connector import get_filing_notes

        # Get filing notes
        notes = get_filing_notes(ticker)

        if notes and notes.get("legal_matters"):
            for matter in notes.get("legal_matters", []):
                disclosed.append(DisclosedLitigation(
                    filing_type=matter.get("filing_type", "10-K"),
                    filing_date=matter.get("filing_date", ""),
                    accession_number=matter.get("accession", ""),
                    description=matter.get("text", matter.get("description", "")),
                    amount_disclosed=parse_amount(matter.get("text", "")),
                    management_assessment=parse_management_assessment(matter.get("text", "")),
                    section=matter.get("section", "Legal Proceedings"),
                    source_text=matter.get("text", "")[:500] if matter.get("text") else None,
                ))

        # Also check commitments/contingencies note
        if notes and notes.get("contingencies"):
            for contingency in notes.get("contingencies", []):
                if "litigation" in str(contingency).lower() or "legal" in str(contingency).lower():
                    text = contingency.get("text", "") if isinstance(contingency, dict) else str(contingency)
                    disclosed.append(DisclosedLitigation(
                        filing_type="10-K",
                        filing_date=notes.get("filing_date", ""),
                        accession_number=notes.get("accession", ""),
                        description=text[:200],
                        amount_disclosed=parse_amount(text),
                        management_assessment=parse_management_assessment(text),
                        section="Contingencies",
                        source_text=text[:500],
                    ))

    except Exception as e:
        logger.warning(f"Error fetching disclosed litigation: {e}")

    return disclosed


def _reconcile_cases(
    docket_cases: List[DocketCase],
    disclosed: List[DisclosedLitigation],
    company_name: str,
) -> List[ReconciliationFinding]:
    """Reconcile docket cases against disclosures."""
    findings = []
    finding_id = 0

    # Track which disclosures have been matched
    matched_disclosures: Set[int] = set()

    for case in docket_cases:
        # Try to find a matching disclosure
        match = _find_matching_disclosure(case, disclosed, matched_disclosures)

        if match:
            disclosure_idx, disclosure = match
            matched_disclosures.add(disclosure_idx)

            # Check for divergences
            divergences = _check_divergences(case, disclosure)

            for div_type, description in divergences:
                finding_id += 1
                findings.append(ReconciliationFinding(
                    id=f"F{finding_id:04d}",
                    divergence_type=div_type,
                    disclosure_status=DisclosureStatus.PARTIAL,
                    materiality=_assess_materiality(case),
                    docket_case=case,
                    disclosed_litigation=disclosure,
                    title=f"{div_type.value.replace('_', ' ').title()}: {case.case_name[:50]}",
                    description=description,
                    risk_score=_score_divergence(div_type, case),
                    evidence=[
                        {"type": "docket", "source": case.source_url},
                        {"type": "disclosure", "accession": disclosure.accession_number},
                    ],
                    recommendations=_generate_recommendations(div_type),
                ))
        else:
            # Case not disclosed - this is a key finding
            finding_id += 1
            materiality = _assess_materiality(case)

            # Only flag as undisclosed if material and case is recent
            if case.status.lower() not in ["dismissed", "closed"]:
                findings.append(ReconciliationFinding(
                    id=f"F{finding_id:04d}",
                    divergence_type=DivergenceType.MISSING_DISCLOSURE,
                    disclosure_status=DisclosureStatus.UNDISCLOSED,
                    materiality=materiality,
                    docket_case=case,
                    disclosed_litigation=None,
                    title=f"Undisclosed Litigation: {case.case_name[:50]}",
                    description=_format_missing_disclosure_desc(case),
                    risk_score=_score_missing_disclosure(case, materiality),
                    evidence=[
                        {"type": "docket", "source": case.source_url},
                    ],
                    recommendations=[
                        "Review disclosure requirements under Item 103",
                        "Assess materiality threshold for this matter",
                        "Consider whether disclosure should be in next filing",
                    ],
                ))

    # Check for disclosures without matching docket cases
    for idx, disclosure in enumerate(disclosed):
        if idx not in matched_disclosures:
            # This could be:
            # - State court case (not in federal docket)
            # - Arbitration
            # - Regulatory matter
            # - Settlement before docket filing
            # Not necessarily a problem, but worth noting
            logger.debug("Disclosure at index %d has no matching docket case", idx)

    return findings


def _find_matching_disclosure(
    case: DocketCase,
    disclosures: List[DisclosedLitigation],
    already_matched: Set[int],
) -> Optional[Tuple[int, DisclosedLitigation]]:
    """Find a disclosure that matches a docket case."""
    best_match = None
    best_score = 0

    for idx, disclosure in enumerate(disclosures):
        if idx in already_matched:
            continue

        score = _compute_match_score(case, disclosure)
        if score > best_score and score >= 0.3:  # Threshold
            best_score = score
            best_match = (idx, disclosure)

    return best_match


def _compute_match_score(case: DocketCase, disclosure: DisclosedLitigation) -> float:
    """Compute similarity score between docket case and disclosure."""
    score = 0.0

    # Case name similarity
    case_name_lower = case.case_name.lower()
    desc_lower = disclosure.description.lower()

    # Check if docket number mentioned
    if case.docket_number and case.docket_number in disclosure.description:
        score += 0.5

    # Check party names
    for party in case.parties:
        if party.lower() in desc_lower:
            score += 0.2

    # Check keywords from case name
    case_words = set(re.findall(r'\w+', case_name_lower))
    desc_words = set(re.findall(r'\w+', desc_lower))
    common_words = case_words & desc_words - {'the', 'a', 'an', 'inc', 'corp', 'llc', 'v', 'vs'}
    if len(case_words) > 0:
        score += len(common_words) / len(case_words) * 0.3

    # Check nature of suit
    if case.nature_of_suit:
        suit_lower = case.nature_of_suit.lower()
        if any(word in desc_lower for word in suit_lower.split()):
            score += 0.1

    # Check amounts (if both present and close)
    if case.amount_claimed and disclosure.amount_disclosed:
        ratio = min(case.amount_claimed, disclosure.amount_disclosed) / max(case.amount_claimed, disclosure.amount_disclosed)
        if ratio > 0.8:
            score += 0.2

    return min(score, 1.0)


def _check_divergences(
    case: DocketCase,
    disclosure: DisclosedLitigation,
) -> List[Tuple[DivergenceType, str]]:
    """Check for divergences between docket case and disclosure."""
    divergences = []

    # Amount mismatch
    if case.amount_claimed and disclosure.amount_disclosed:
        if case.amount_claimed != disclosure.amount_disclosed:
            ratio = disclosure.amount_disclosed / case.amount_claimed if case.amount_claimed else 0
            if ratio < 0.5 or ratio > 2.0:
                divergences.append((
                    DivergenceType.AMOUNT_MISMATCH,
                    f"Docket claims ${case.amount_claimed:,.0f}, disclosure shows ${disclosure.amount_disclosed:,.0f}"
                ))

    # Status mismatch
    if case.status.lower() in ["settled", "closed"] and disclosure.management_assessment in ["probable", "reasonably_possible"]:
        divergences.append((
            DivergenceType.OUTCOME_NOT_UPDATED,
            f"Case appears {case.status} but disclosure still shows contingent"
        ))

    # Timing gap
    if case.filed_date and disclosure.filing_date:
        try:
            filed_dt = datetime.strptime(case.filed_date, "%Y-%m-%d")
            disclosed_dt = datetime.strptime(disclosure.filing_date, "%Y-%m-%d")
            gap_days = (disclosed_dt - filed_dt).days
            if gap_days > 365:  # More than a year
                divergences.append((
                    DivergenceType.TIMING_GAP,
                    f"Case filed {case.filed_date}, first disclosed {disclosure.filing_date} ({gap_days} day gap)"
                ))
        except ValueError as e:
            logger.debug("Failed to parse dates for timing gap check: %s", e)

    # Minimization check
    if case.nature_of_suit and "class action" in case.nature_of_suit.lower():
        if "class" not in disclosure.description.lower():
            divergences.append((
                DivergenceType.MINIMIZATION,
                "Class action case not identified as such in disclosure"
            ))

    return divergences


def _assess_materiality(case: DocketCase) -> MaterialityLevel:
    """Assess materiality of a case."""
    if not case.amount_claimed:
        return MaterialityLevel.UNKNOWN

    amount = case.amount_claimed

    # Simple thresholds (should be relative to market cap in production)
    if amount >= 1e9:
        return MaterialityLevel.CRITICAL
    elif amount >= 100e6:
        return MaterialityLevel.HIGH
    elif amount >= 10e6:
        return MaterialityLevel.MEDIUM
    else:
        return MaterialityLevel.LOW


def _score_divergence(div_type: DivergenceType, case: DocketCase) -> float:
    """Score the risk of a divergence."""
    base_scores = {
        DivergenceType.MISSING_DISCLOSURE: 80,
        DivergenceType.AMOUNT_MISMATCH: 60,
        DivergenceType.MINIMIZATION: 70,
        DivergenceType.TIMING_GAP: 40,
        DivergenceType.STATUS_MISMATCH: 50,
        DivergenceType.OUTCOME_NOT_UPDATED: 30,
        DivergenceType.PARTY_MISMATCH: 20,
    }

    score = base_scores.get(div_type, 50)

    # Adjust for amount
    if case.amount_claimed:
        if case.amount_claimed >= 1e9:
            score = min(100, score + 15)
        elif case.amount_claimed >= 100e6:
            score = min(100, score + 10)

    return score


def _score_missing_disclosure(case: DocketCase, materiality: MaterialityLevel) -> float:
    """Score risk of missing disclosure."""
    base_score = 70

    # Adjust for materiality
    materiality_adjustments = {
        MaterialityLevel.CRITICAL: 30,
        MaterialityLevel.HIGH: 20,
        MaterialityLevel.MEDIUM: 10,
        MaterialityLevel.LOW: -20,
        MaterialityLevel.UNKNOWN: 0,
    }
    base_score += materiality_adjustments.get(materiality, 0)

    # Adjust for case status
    if case.status.lower() in ["open", "pending"]:
        base_score += 10

    # Adjust for nature of suit
    if case.nature_of_suit:
        nos_lower = case.nature_of_suit.lower()
        if "securities" in nos_lower:
            base_score += 15
        elif "class action" in nos_lower:
            base_score += 10
        elif "antitrust" in nos_lower:
            base_score += 10

    return min(100, max(0, base_score))


def _format_missing_disclosure_desc(case: DocketCase) -> str:
    """Format description for missing disclosure finding."""
    parts = [
        f"Court case '{case.case_name}' filed {case.filed_date} in {case.court}",
        f"was not found in SEC filings.",
    ]

    if case.nature_of_suit:
        parts.append(f"Nature of suit: {case.nature_of_suit}.")

    if case.amount_claimed:
        parts.append(f"Amount claimed: ${case.amount_claimed:,.0f}.")

    if case.status:
        parts.append(f"Current status: {case.status}.")

    return " ".join(parts)


def _generate_recommendations(div_type: DivergenceType) -> List[str]:
    """Generate recommendations based on divergence type."""
    recommendations = {
        DivergenceType.MISSING_DISCLOSURE: [
            "Review Item 103 disclosure requirements",
            "Assess if case is material under ASC 450",
            "Consider whether voluntary disclosure is appropriate",
        ],
        DivergenceType.AMOUNT_MISMATCH: [
            "Reconcile claimed vs disclosed amounts",
            "Review basis for disclosed figure",
            "Consider updating disclosure if material change",
        ],
        DivergenceType.TIMING_GAP: [
            "Review timing of disclosure relative to filing date",
            "Assess if case was material when filed",
            "Consider whether earlier disclosure was required",
        ],
        DivergenceType.MINIMIZATION: [
            "Review disclosure language for completeness",
            "Ensure class action status is clearly identified",
            "Consider investor perception of disclosure",
        ],
        DivergenceType.OUTCOME_NOT_UPDATED: [
            "Update disclosure to reflect resolved status",
            "Disclose settlement terms if material",
            "Remove or update contingency accrual",
        ],
    }

    return recommendations.get(div_type, ["Review disclosure requirements"])


def _calculate_risk_score(findings: List[ReconciliationFinding]) -> float:
    """Calculate overall reconciliation risk score."""
    if not findings:
        return 0.0

    # Weight by materiality
    weights = {
        MaterialityLevel.CRITICAL: 2.0,
        MaterialityLevel.HIGH: 1.5,
        MaterialityLevel.MEDIUM: 1.0,
        MaterialityLevel.LOW: 0.5,
        MaterialityLevel.UNKNOWN: 0.8,
    }

    weighted_scores = []
    for finding in findings:
        weight = weights.get(finding.materiality, 1.0)
        weighted_scores.append(finding.risk_score * weight)

    # Average of top 5 weighted scores
    weighted_scores.sort(reverse=True)
    top_scores = weighted_scores[:5]

    return sum(top_scores) / len(top_scores) if top_scores else 0.0


def _generate_summary(
    docket_cases: List[DocketCase],
    disclosed: List[DisclosedLitigation],
    findings: List[ReconciliationFinding],
) -> Dict[str, Any]:
    """Generate summary statistics for the reconciliation."""
    # Count by divergence type
    by_type = defaultdict(int)
    for f in findings:
        by_type[f.divergence_type.value] += 1

    # Count by materiality
    by_materiality = defaultdict(int)
    for f in findings:
        by_materiality[f.materiality.value] += 1

    # Count undisclosed
    undisclosed = [f for f in findings if f.disclosure_status == DisclosureStatus.UNDISCLOSED]

    return {
        "total_docket_cases": len(docket_cases),
        "total_disclosed": len(disclosed),
        "total_findings": len(findings),
        "undisclosed_count": len(undisclosed),
        "findings_by_type": dict(by_type),
        "findings_by_materiality": dict(by_materiality),
        "high_risk_findings": len([f for f in findings if f.risk_score >= 70]),
        "requires_attention": len([f for f in findings if f.risk_score >= 50]),
    }


# ── Serialization ────────────────────────────────────────────────────────────

def report_to_dict(report: ReconciliationReport) -> Dict[str, Any]:
    """Convert ReconciliationReport to JSON-serializable dict."""
    return {
        "ticker": report.ticker,
        "company_name": report.company_name,
        "cik": report.cik,
        "analysis_date": report.analysis_date,
        "docket_cases": [
            {
                "case_id": c.case_id,
                "case_name": c.case_name,
                "court": c.court,
                "docket_number": c.docket_number,
                "filed_date": c.filed_date,
                "status": c.status,
                "nature_of_suit": c.nature_of_suit,
                "amount_claimed": c.amount_claimed,
                "source_url": c.source_url,
            }
            for c in report.docket_cases
        ],
        "disclosed_litigation": [
            {
                "filing_type": d.filing_type,
                "filing_date": d.filing_date,
                "description": d.description[:200],
                "amount_disclosed": d.amount_disclosed,
                "management_assessment": d.management_assessment,
                "section": d.section,
            }
            for d in report.disclosed_litigation
        ],
        "findings": [
            {
                "id": f.id,
                "divergence_type": f.divergence_type.value,
                "disclosure_status": f.disclosure_status.value,
                "materiality": f.materiality.value,
                "title": f.title,
                "description": f.description,
                "risk_score": f.risk_score,
                "recommendations": f.recommendations,
                "docket_case_id": f.docket_case.case_id if f.docket_case else None,
            }
            for f in report.findings
        ],
        "summary": report.summary,
        "risk_score": report.risk_score,
        "generated_at": report.generated_at,
    }
