"""
Filing Diff Service (Band B #15)
────────────────────────────────────────────────────────────────────────────
Provides filing-level comparison capabilities:
  - Year-over-year 10-K/10-Q comparison
  - Narrative text diff with redline markup
  - Material change detection and flagging
  - Table extraction for Excel export
  - Section-by-section delta analysis

Uses SEC EDGAR data via sec_edgar_connector and filing_notes_connector.
"""

import os
import re
import logging
import difflib
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes detected in filings."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"
    MATERIAL = "material"  # Significant change flagged


class MaterialityLevel(Enum):
    """Materiality classification for changes."""
    HIGH = "high"      # >10% change or new risk factor
    MEDIUM = "medium"  # 5-10% change
    LOW = "low"        # <5% change
    INFO = "info"      # Informational only


@dataclass
class FilingChange:
    """Represents a single change between two filing versions."""
    section: str
    field: str
    change_type: ChangeType
    old_value: Any
    new_value: Any
    delta: Optional[float] = None
    delta_pct: Optional[float] = None
    materiality: MaterialityLevel = MaterialityLevel.INFO
    context: Optional[str] = None
    source_url: Optional[str] = None


@dataclass
class TextDiff:
    """Represents a text diff with redline markup."""
    section: str
    old_text: str
    new_text: str
    diff_html: str
    added_lines: int
    removed_lines: int
    similarity_ratio: float


@dataclass
class TableData:
    """Represents an extracted table for Excel export."""
    name: str
    section: str
    headers: List[str]
    rows: List[List[Any]]
    source_filing: str
    period: str


@dataclass
class FilingDiffResult:
    """Complete diff result between two filings."""
    ticker: str
    company_name: str
    form_type: str
    base_filing: Dict[str, Any]
    compare_filing: Dict[str, Any]
    financial_changes: List[FilingChange]
    narrative_changes: List[TextDiff]
    material_changes: List[FilingChange]
    tables: List[TableData]
    summary: Dict[str, Any]
    generated_at: str


# Material change thresholds
MATERIALITY_THRESHOLDS = {
    "revenue": {"high": 0.10, "medium": 0.05},
    "net_income": {"high": 0.15, "medium": 0.08},
    "total_assets": {"high": 0.10, "medium": 0.05},
    "total_debt": {"high": 0.15, "medium": 0.10},
    "cash": {"high": 0.20, "medium": 0.10},
    "operating_income": {"high": 0.15, "medium": 0.08},
    "gross_margin": {"high": 0.03, "medium": 0.02},  # Percentage points
    "operating_margin": {"high": 0.03, "medium": 0.02},
    "default": {"high": 0.10, "medium": 0.05},
}

# Keywords that indicate material narrative changes
MATERIAL_KEYWORDS = [
    "material weakness", "restatement", "going concern",
    "sec investigation", "securities litigation", "class action",
    "regulatory inquiry", "subpoena", "enforcement action",
    "impairment", "write-down", "write-off", "restructuring",
    "goodwill impairment", "asset impairment", "discontinued operation",
    "change in control", "merger", "acquisition", "divestiture",
    "bankruptcy", "default", "covenant violation", "credit downgrade",
    "cfo departure", "ceo departure", "auditor change", "auditor resignation",
    "data breach", "cybersecurity incident", "privacy violation",
    "environmental liability", "product recall", "safety issue",
]


def get_filing_diff(
    ticker: str,
    form_type: str = "10-K",
    base_period: Optional[str] = None,
    compare_period: Optional[str] = None,
) -> FilingDiffResult:
    """
    Generate a comprehensive diff between two filing periods.

    Args:
        ticker: Stock ticker symbol
        form_type: SEC form type (10-K, 10-Q, 8-K)
        base_period: Base period for comparison (e.g., "2024" or "2024-Q1")
        compare_period: Period to compare against (e.g., "2023" or "2023-Q1")

    Returns:
        FilingDiffResult with all changes categorized
    """
    from app.connectors.sec_edgar_connector import (
        get_filer_cik,
        get_company_submissions,
        extract_financial_statements,
        get_segment_data,
    )
    from app.connectors.filing_notes_connector import get_filing_notes

    logger.info(f"Generating filing diff for {ticker} ({form_type})")

    # Resolve CIK
    cik = get_filer_cik(ticker)
    if not cik:
        raise ValueError(f"Could not resolve CIK for ticker: {ticker}")

    # Get company submissions
    submissions = get_company_submissions(cik)
    if not submissions:
        raise ValueError(f"Could not fetch submissions for CIK: {cik}")

    company_name = submissions.get("name", ticker)

    # Find the two filings to compare
    filings = _find_comparison_filings(submissions, form_type, base_period, compare_period)
    if not filings or len(filings) < 2:
        raise ValueError(f"Could not find two {form_type} filings to compare")

    base_filing_info, compare_filing_info = filings[0], filings[1]

    # Extract financial data for both periods
    base_financials = extract_financial_statements(cik)
    compare_financials = extract_financial_statements(cik)

    # Get segment data
    base_segments = get_segment_data(ticker)
    compare_segments = get_segment_data(ticker)

    # Get narrative notes
    base_notes = get_filing_notes(ticker)
    compare_notes = get_filing_notes(ticker)

    # Compute financial changes
    financial_changes = _compute_financial_changes(
        base_financials, compare_financials,
        base_filing_info, compare_filing_info
    )

    # Compute segment changes
    segment_changes = _compute_segment_changes(base_segments, compare_segments)
    financial_changes.extend(segment_changes)

    # Compute narrative diffs
    narrative_changes = _compute_narrative_diffs(base_notes, compare_notes)

    # Identify material changes
    material_changes = [c for c in financial_changes if c.materiality == MaterialityLevel.HIGH]
    material_changes.extend(_detect_material_narrative_changes(narrative_changes))

    # Extract tables for Excel export
    tables = _extract_tables(base_financials, compare_financials, base_segments, ticker)

    # Generate summary
    summary = _generate_diff_summary(
        financial_changes, narrative_changes, material_changes,
        base_filing_info, compare_filing_info
    )

    return FilingDiffResult(
        ticker=ticker,
        company_name=company_name,
        form_type=form_type,
        base_filing=base_filing_info,
        compare_filing=compare_filing_info,
        financial_changes=financial_changes,
        narrative_changes=narrative_changes,
        material_changes=material_changes,
        tables=tables,
        summary=summary,
        generated_at=datetime.utcnow().isoformat(),
    )


def _find_comparison_filings(
    submissions: Dict[str, Any],
    form_type: str,
    base_period: Optional[str],
    compare_period: Optional[str],
) -> List[Dict[str, Any]]:
    """Find the two filings to compare based on form type and periods."""
    filings_list = submissions.get("filings", {}).get("recent", {})

    forms = filings_list.get("form", [])
    dates = filings_list.get("filingDate", [])
    accessions = filings_list.get("accessionNumber", [])
    documents = filings_list.get("primaryDocument", [])

    # Filter to requested form type (exact match, excluding amendments for now)
    matching_filings = []
    for i, form in enumerate(forms):
        if form == form_type:
            matching_filings.append({
                "form": form,
                "filing_date": dates[i] if i < len(dates) else None,
                "accession": accessions[i] if i < len(accessions) else None,
                "document": documents[i] if i < len(documents) else None,
                "period": _extract_period_from_date(dates[i]) if i < len(dates) else None,
            })

    # Sort by filing date descending (most recent first)
    matching_filings.sort(key=lambda x: x.get("filing_date", ""), reverse=True)

    # If specific periods requested, filter to those
    if base_period and compare_period:
        base_filing = next((f for f in matching_filings if base_period in str(f.get("period", ""))), None)
        compare_filing = next((f for f in matching_filings if compare_period in str(f.get("period", ""))), None)
        if base_filing and compare_filing:
            return [base_filing, compare_filing]

    # Default: return most recent two filings
    return matching_filings[:2] if len(matching_filings) >= 2 else matching_filings


def _extract_period_from_date(filing_date: str) -> str:
    """Extract fiscal period from filing date."""
    if not filing_date:
        return ""
    try:
        dt = datetime.strptime(filing_date, "%Y-%m-%d")
        # 10-K filings are typically filed 60-90 days after fiscal year end
        # Approximate the fiscal year
        return str(dt.year - 1) if dt.month <= 3 else str(dt.year)
    except ValueError:
        return filing_date[:4] if len(filing_date) >= 4 else ""


def _compute_financial_changes(
    base_data: Dict[str, Any],
    compare_data: Dict[str, Any],
    base_info: Dict[str, Any],
    compare_info: Dict[str, Any],
) -> List[FilingChange]:
    """Compute changes in financial metrics between two periods."""
    changes = []

    # Key financial metrics to compare
    metrics = {
        "income_statement": [
            ("Revenues", "revenue"),
            ("GrossProfit", "gross_profit"),
            ("OperatingIncome", "operating_income"),
            ("NetIncome", "net_income"),
            ("ResearchAndDevelopment", "r_and_d"),
        ],
        "balance_sheet": [
            ("Assets", "total_assets"),
            ("Liabilities", "total_liabilities"),
            ("CashAndCashEquivalents", "cash"),
            ("LongTermDebt", "long_term_debt"),
            ("StockholdersEquity", "stockholders_equity"),
        ],
        "cash_flow": [
            ("OperatingCashFlow", "operating_cash_flow"),
            ("CapitalExpenditures", "capital_expenditures"),
            ("FreeCashFlow", "free_cash_flow"),
        ],
        "metrics": [
            ("gross_margin", "gross_margin"),
            ("operating_margin", "operating_margin"),
            ("net_margin", "net_margin"),
            ("return_on_equity", "roe"),
            ("return_on_assets", "roa"),
        ],
    }

    for section, metric_list in metrics.items():
        base_section = base_data.get(section, [])
        compare_section = compare_data.get(section, [])

        # Handle list vs dict sections
        if isinstance(base_section, list) and base_section:
            base_section = base_section[0]  # Most recent period
        if isinstance(compare_section, list) and compare_section:
            compare_section = compare_section[0]

        if not isinstance(base_section, dict):
            base_section = {}
        if not isinstance(compare_section, dict):
            compare_section = {}

        for xbrl_tag, field_name in metric_list:
            base_val = base_section.get(xbrl_tag) or base_section.get(field_name)
            compare_val = compare_section.get(xbrl_tag) or compare_section.get(field_name)

            change = _create_change(
                section=section,
                field=field_name,
                old_value=compare_val,
                new_value=base_val,
                base_info=base_info,
            )
            if change:
                changes.append(change)

    return changes


def _create_change(
    section: str,
    field: str,
    old_value: Any,
    new_value: Any,
    base_info: Dict[str, Any],
) -> Optional[FilingChange]:
    """Create a FilingChange object with computed delta and materiality."""
    if old_value is None and new_value is None:
        return None

    # Determine change type
    if old_value is None and new_value is not None:
        change_type = ChangeType.ADDED
    elif old_value is not None and new_value is None:
        change_type = ChangeType.REMOVED
    elif old_value != new_value:
        change_type = ChangeType.MODIFIED
    else:
        change_type = ChangeType.UNCHANGED
        return None  # Skip unchanged values

    # Calculate delta for numeric values
    delta = None
    delta_pct = None
    materiality = MaterialityLevel.INFO

    if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
        delta = new_value - old_value
        if old_value != 0:
            delta_pct = (delta / abs(old_value)) * 100

            # Determine materiality
            thresholds = MATERIALITY_THRESHOLDS.get(field, MATERIALITY_THRESHOLDS["default"])
            abs_pct = abs(delta_pct) / 100

            if abs_pct >= thresholds["high"]:
                materiality = MaterialityLevel.HIGH
                change_type = ChangeType.MATERIAL
            elif abs_pct >= thresholds["medium"]:
                materiality = MaterialityLevel.MEDIUM

    return FilingChange(
        section=section,
        field=field,
        change_type=change_type,
        old_value=old_value,
        new_value=new_value,
        delta=delta,
        delta_pct=round(delta_pct, 2) if delta_pct else None,
        materiality=materiality,
        source_url=_build_filing_url(base_info) if base_info else None,
    )


def _compute_segment_changes(
    base_segments: Dict[str, Any],
    compare_segments: Dict[str, Any],
) -> List[FilingChange]:
    """Compute changes in segment data."""
    changes = []

    # Revenue by segment
    base_rev = base_segments.get("revenue_by_segment", {})
    compare_rev = compare_segments.get("revenue_by_segment", {})

    all_segments = set(base_rev.keys()) | set(compare_rev.keys())
    for segment in all_segments:
        change = _create_change(
            section="segments",
            field=f"segment_{segment}",
            old_value=compare_rev.get(segment),
            new_value=base_rev.get(segment),
            base_info={},
        )
        if change:
            changes.append(change)

    # Geographic revenue
    base_geo = base_segments.get("geographic_revenue", {})
    compare_geo = compare_segments.get("geographic_revenue", {})

    all_regions = set(base_geo.keys()) | set(compare_geo.keys())
    for region in all_regions:
        change = _create_change(
            section="geographic",
            field=f"geo_{region}",
            old_value=compare_geo.get(region),
            new_value=base_geo.get(region),
            base_info={},
        )
        if change:
            changes.append(change)

    return changes


def _compute_narrative_diffs(
    base_notes: Dict[str, Any],
    compare_notes: Dict[str, Any],
) -> List[TextDiff]:
    """Compute text diffs for narrative sections."""
    diffs = []

    # Sections to compare
    sections = [
        "risk_factors",
        "legal_proceedings",
        "management_discussion",
        "commitments",
        "related_party",
    ]

    for section in sections:
        base_text = _extract_section_text(base_notes, section)
        compare_text = _extract_section_text(compare_notes, section)

        if not base_text and not compare_text:
            continue

        diff = _create_text_diff(section, compare_text or "", base_text or "")
        if diff.added_lines > 0 or diff.removed_lines > 0:
            diffs.append(diff)

    return diffs


def _extract_section_text(notes: Dict[str, Any], section: str) -> Optional[str]:
    """Extract text content for a narrative section."""
    if not notes:
        return None

    # Try different possible keys
    possible_keys = [
        section,
        section.replace("_", " "),
        section.title().replace("_", " "),
    ]

    for key in possible_keys:
        if key in notes:
            content = notes[key]
            if isinstance(content, str):
                return content
            elif isinstance(content, dict):
                return content.get("text", content.get("content", str(content)))
            elif isinstance(content, list):
                return "\n".join(str(item) for item in content)

    return None


def _create_text_diff(section: str, old_text: str, new_text: str) -> TextDiff:
    """Create a text diff with HTML redline markup."""
    # Split into lines for comparison
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    # Compute diff
    differ = difflib.HtmlDiff()
    diff_html = differ.make_table(old_lines, new_lines, context=True, numlines=3)

    # Count changes
    matcher = difflib.SequenceMatcher(None, old_text, new_text)
    similarity = matcher.ratio()

    # Count added/removed lines
    diff_ops = list(difflib.unified_diff(old_lines, new_lines))
    added = sum(1 for line in diff_ops if line.startswith('+') and not line.startswith('+++'))
    removed = sum(1 for line in diff_ops if line.startswith('-') and not line.startswith('---'))

    return TextDiff(
        section=section,
        old_text=old_text,
        new_text=new_text,
        diff_html=diff_html,
        added_lines=added,
        removed_lines=removed,
        similarity_ratio=round(similarity, 3),
    )


def _detect_material_narrative_changes(diffs: List[TextDiff]) -> List[FilingChange]:
    """Detect material changes in narrative text based on keywords."""
    material_changes = []

    for diff in diffs:
        # Check for material keywords in new text that weren't in old text
        new_text_lower = diff.new_text.lower()
        old_text_lower = diff.old_text.lower()

        for keyword in MATERIAL_KEYWORDS:
            if keyword in new_text_lower and keyword not in old_text_lower:
                material_changes.append(FilingChange(
                    section=diff.section,
                    field=f"keyword_{keyword.replace(' ', '_')}",
                    change_type=ChangeType.MATERIAL,
                    old_value=None,
                    new_value=keyword,
                    materiality=MaterialityLevel.HIGH,
                    context=f"New mention of '{keyword}' in {diff.section}",
                ))

    return material_changes


def _extract_tables(
    base_financials: Dict[str, Any],
    compare_financials: Dict[str, Any],
    segments: Dict[str, Any],
    ticker: str,
) -> List[TableData]:
    """Extract tables suitable for Excel export."""
    tables = []

    # Income Statement comparison table
    income_table = _build_comparison_table(
        base_financials.get("income_statement", []),
        compare_financials.get("income_statement", []),
        "Income Statement",
    )
    if income_table:
        tables.append(income_table)

    # Balance Sheet comparison table
    balance_table = _build_comparison_table(
        base_financials.get("balance_sheet", []),
        compare_financials.get("balance_sheet", []),
        "Balance Sheet",
    )
    if balance_table:
        tables.append(balance_table)

    # Cash Flow comparison table
    cashflow_table = _build_comparison_table(
        base_financials.get("cash_flow", []),
        compare_financials.get("cash_flow", []),
        "Cash Flow",
    )
    if cashflow_table:
        tables.append(cashflow_table)

    # Segment revenue table
    if segments.get("revenue_by_segment"):
        segment_headers = ["Segment", "Revenue", "% of Total"]
        segment_rows = []
        total = sum(v for v in segments["revenue_by_segment"].values() if isinstance(v, (int, float)))

        for seg, rev in segments["revenue_by_segment"].items():
            pct = (rev / total * 100) if total > 0 and isinstance(rev, (int, float)) else 0
            segment_rows.append([seg, rev, round(pct, 1)])

        tables.append(TableData(
            name="Segment Revenue",
            section="segments",
            headers=segment_headers,
            rows=segment_rows,
            source_filing=ticker,
            period="Latest",
        ))

    return tables


def _build_comparison_table(
    base_data: List[Dict],
    compare_data: List[Dict],
    name: str,
) -> Optional[TableData]:
    """Build a comparison table from two periods of data."""
    if not base_data or not compare_data:
        return None

    base_period = base_data[0] if base_data else {}
    compare_period = compare_data[0] if compare_data else {}

    # Get all unique keys
    all_keys = set(base_period.keys()) | set(compare_period.keys())
    # Filter to numeric values only
    all_keys = {k for k in all_keys if isinstance(base_period.get(k), (int, float)) or isinstance(compare_period.get(k), (int, float))}

    if not all_keys:
        return None

    headers = ["Metric", "Current Period", "Prior Period", "Change", "Change %"]
    rows = []

    for key in sorted(all_keys):
        base_val = base_period.get(key)
        compare_val = compare_period.get(key)

        if base_val is None or compare_val is None:
            continue
        if not isinstance(base_val, (int, float)) or not isinstance(compare_val, (int, float)):
            continue

        change = base_val - compare_val
        change_pct = (change / abs(compare_val) * 100) if compare_val != 0 else 0

        rows.append([
            key,
            base_val,
            compare_val,
            change,
            round(change_pct, 1),
        ])

    return TableData(
        name=name,
        section="financials",
        headers=headers,
        rows=rows,
        source_filing="SEC EDGAR",
        period=base_period.get("period_end", ""),
    )


def _generate_diff_summary(
    financial_changes: List[FilingChange],
    narrative_changes: List[TextDiff],
    material_changes: List[FilingChange],
    base_info: Dict[str, Any],
    compare_info: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate a summary of the diff analysis."""
    # Count changes by materiality
    high_count = sum(1 for c in financial_changes if c.materiality == MaterialityLevel.HIGH)
    medium_count = sum(1 for c in financial_changes if c.materiality == MaterialityLevel.MEDIUM)
    low_count = sum(1 for c in financial_changes if c.materiality == MaterialityLevel.LOW)

    # Largest changes
    largest_changes = sorted(
        [c for c in financial_changes if c.delta_pct is not None],
        key=lambda x: abs(x.delta_pct or 0),
        reverse=True,
    )[:5]

    return {
        "base_period": base_info.get("period", "Current"),
        "compare_period": compare_info.get("period", "Prior"),
        "base_filing_date": base_info.get("filing_date"),
        "compare_filing_date": compare_info.get("filing_date"),
        "total_financial_changes": len(financial_changes),
        "high_materiality_changes": high_count,
        "medium_materiality_changes": medium_count,
        "low_materiality_changes": low_count,
        "narrative_sections_changed": len(narrative_changes),
        "total_lines_added": sum(d.added_lines for d in narrative_changes),
        "total_lines_removed": sum(d.removed_lines for d in narrative_changes),
        "material_keyword_flags": len(material_changes),
        "largest_changes": [
            {
                "field": c.field,
                "delta_pct": c.delta_pct,
                "old_value": c.old_value,
                "new_value": c.new_value,
            }
            for c in largest_changes
        ],
    }


def _build_filing_url(info: Dict[str, Any]) -> Optional[str]:
    """Build SEC EDGAR URL for a filing."""
    accession = info.get("accession")
    if not accession:
        return None

    # Format: https://www.sec.gov/Archives/edgar/data/CIK/ACCESSION/DOCUMENT
    return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&accessionNumber={accession}"


def generate_redline_html(diff_result: FilingDiffResult) -> str:
    """Generate a standalone HTML document with redline comparison."""
    html_parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"<title>Filing Comparison: {diff_result.ticker}</title>",
        "<style>",
        _get_redline_css(),
        "</style>",
        "</head>",
        "<body>",
        f"<h1>Filing Comparison: {diff_result.company_name} ({diff_result.ticker})</h1>",
        f"<h2>{diff_result.form_type} Comparison</h2>",
        f"<p>Base Period: {diff_result.summary.get('base_period')} | Compare Period: {diff_result.summary.get('compare_period')}</p>",
        "<hr>",
    ]

    # Material changes section
    if diff_result.material_changes:
        html_parts.append("<h3>Material Changes</h3>")
        html_parts.append("<ul class='material-changes'>")
        for change in diff_result.material_changes:
            html_parts.append(f"<li class='material'>{change.field}: {change.context or f'{change.old_value} → {change.new_value}'}</li>")
        html_parts.append("</ul>")

    # Financial changes table
    html_parts.append("<h3>Financial Changes</h3>")
    html_parts.append("<table class='changes-table'>")
    html_parts.append("<tr><th>Metric</th><th>Prior</th><th>Current</th><th>Change</th><th>Change %</th></tr>")

    for change in diff_result.financial_changes:
        css_class = "high" if change.materiality == MaterialityLevel.HIGH else "medium" if change.materiality == MaterialityLevel.MEDIUM else ""
        html_parts.append(f"<tr class='{css_class}'>")
        html_parts.append(f"<td>{change.field}</td>")
        html_parts.append(f"<td>{_format_value(change.old_value)}</td>")
        html_parts.append(f"<td>{_format_value(change.new_value)}</td>")
        html_parts.append(f"<td>{_format_value(change.delta)}</td>")
        html_parts.append(f"<td>{change.delta_pct or '—'}%</td>")
        html_parts.append("</tr>")

    html_parts.append("</table>")

    # Narrative diffs
    if diff_result.narrative_changes:
        html_parts.append("<h3>Narrative Changes</h3>")
        for diff in diff_result.narrative_changes:
            html_parts.append(f"<h4>{diff.section.replace('_', ' ').title()}</h4>")
            html_parts.append(f"<p>Similarity: {diff.similarity_ratio*100:.1f}% | +{diff.added_lines} / -{diff.removed_lines} lines</p>")
            html_parts.append(diff.diff_html)

    html_parts.extend([
        f"<footer>Generated: {diff_result.generated_at}</footer>",
        "</body>",
        "</html>",
    ])

    return "\n".join(html_parts)


def _format_value(value: Any) -> str:
    """Format a value for display."""
    if value is None:
        return "—"
    if isinstance(value, float):
        if abs(value) >= 1_000_000_000:
            return f"${value/1_000_000_000:.1f}B"
        elif abs(value) >= 1_000_000:
            return f"${value/1_000_000:.1f}M"
        elif abs(value) >= 1_000:
            return f"${value/1_000:.1f}K"
        else:
            return f"{value:.2f}"
    return str(value)


def _get_redline_css() -> str:
    """CSS styles for redline HTML output."""
    return """
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               margin: 40px; line-height: 1.6; }
        h1, h2, h3, h4 { color: #1a1a1a; }
        .changes-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .changes-table th, .changes-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .changes-table th { background: #f5f5f5; font-weight: 600; }
        .changes-table tr.high { background: #fff3cd; }
        .changes-table tr.medium { background: #e8f4fd; }
        .material-changes { list-style: none; padding: 0; }
        .material-changes li.material { padding: 10px; background: #f8d7da; border-left: 4px solid #dc3545; margin: 5px 0; }
        ins { background: #d4edda; text-decoration: none; }
        del { background: #f8d7da; text-decoration: line-through; }
        .diff table { width: 100%; font-size: 12px; }
        .diff td { padding: 2px 8px; font-family: 'SF Mono', Monaco, monospace; }
        footer { margin-top: 40px; color: #666; font-size: 12px; }
    """


def export_diff_to_excel(diff_result: FilingDiffResult, filepath: str) -> str:
    """Export diff tables to Excel workbook."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        raise ImportError("openpyxl is required for Excel export. Install with: pip install openpyxl")

    wb = openpyxl.Workbook()

    # Remove default sheet
    default_sheet = wb.active

    # Style definitions
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2c3e50", end_color="2c3e50", fill_type="solid")
    high_fill = PatternFill(start_color="fff3cd", end_color="fff3cd", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Summary sheet
    summary_ws = wb.create_sheet("Summary")
    summary_data = [
        ["Filing Comparison Summary"],
        [""],
        ["Company", diff_result.company_name],
        ["Ticker", diff_result.ticker],
        ["Form Type", diff_result.form_type],
        ["Base Period", diff_result.summary.get("base_period", "")],
        ["Compare Period", diff_result.summary.get("compare_period", "")],
        ["Generated", diff_result.generated_at],
        [""],
        ["Change Statistics"],
        ["High Materiality Changes", diff_result.summary.get("high_materiality_changes", 0)],
        ["Medium Materiality Changes", diff_result.summary.get("medium_materiality_changes", 0)],
        ["Narrative Sections Changed", diff_result.summary.get("narrative_sections_changed", 0)],
        ["Lines Added", diff_result.summary.get("total_lines_added", 0)],
        ["Lines Removed", diff_result.summary.get("total_lines_removed", 0)],
    ]

    for row_data in summary_data:
        summary_ws.append(row_data if isinstance(row_data, list) else [row_data])

    # Financial Changes sheet
    changes_ws = wb.create_sheet("Financial Changes")
    headers = ["Section", "Field", "Prior Value", "Current Value", "Delta", "Delta %", "Materiality"]
    changes_ws.append(headers)

    for cell in changes_ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border

    for change in diff_result.financial_changes:
        row = [
            change.section,
            change.field,
            change.old_value,
            change.new_value,
            change.delta,
            change.delta_pct,
            change.materiality.value if change.materiality else "",
        ]
        changes_ws.append(row)

        # Highlight high materiality rows
        if change.materiality == MaterialityLevel.HIGH:
            for cell in changes_ws[changes_ws.max_row]:
                cell.fill = high_fill

    # Export each table
    for table in diff_result.tables:
        ws = wb.create_sheet(table.name[:31])  # Excel sheet name limit
        ws.append(table.headers)

        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.border = thin_border

        for row in table.rows:
            ws.append(row)

    # Remove the default empty sheet
    if default_sheet.title == "Sheet":
        wb.remove(default_sheet)

    # Save
    wb.save(filepath)
    return filepath


# Serialization helper for API responses
def diff_result_to_dict(result: FilingDiffResult) -> Dict[str, Any]:
    """Convert FilingDiffResult to JSON-serializable dict."""
    return {
        "ticker": result.ticker,
        "company_name": result.company_name,
        "form_type": result.form_type,
        "base_filing": result.base_filing,
        "compare_filing": result.compare_filing,
        "financial_changes": [
            {
                "section": c.section,
                "field": c.field,
                "change_type": c.change_type.value,
                "old_value": c.old_value,
                "new_value": c.new_value,
                "delta": c.delta,
                "delta_pct": c.delta_pct,
                "materiality": c.materiality.value,
                "context": c.context,
                "source_url": c.source_url,
            }
            for c in result.financial_changes
        ],
        "narrative_changes": [
            {
                "section": d.section,
                "added_lines": d.added_lines,
                "removed_lines": d.removed_lines,
                "similarity_ratio": d.similarity_ratio,
                # Omit full text for API response size
            }
            for d in result.narrative_changes
        ],
        "material_changes": [
            {
                "section": c.section,
                "field": c.field,
                "context": c.context,
                "materiality": c.materiality.value,
            }
            for c in result.material_changes
        ],
        "tables": [
            {
                "name": t.name,
                "section": t.section,
                "headers": t.headers,
                "row_count": len(t.rows),
            }
            for t in result.tables
        ],
        "summary": result.summary,
        "generated_at": result.generated_at,
    }
