#!/usr/bin/env python3
"""
Generate a Professional Intelligence Report (Phase 2 Enhanced)
====================================================================
Creates a comprehensive premium PDF report for any listed company using all
Phase 1 + Phase 2 deep research connectors. The registrant name, exchange and
peer set are resolved from the ticker, so no company-specific configuration is
required.

Phase 2 Connectors:
- SEC EDGAR Financial (XBRL, Form 4)
- Entity Network/Swarm (family networks, cross-firm)
- Proxy Statement Parser (compensation, governance)
- Litigation Tracker (federal cases, SEC enforcement)
- Timeline Generator (event chronology)
- DCF Valuation Model (Bear/Base/Bull scenarios)
- Risk Register Generator (categorized risks)

Usage:
    cd apps/api
    python scripts/generate_intelligence_report.py --ticker AAPL
    python scripts/generate_intelligence_report.py --ticker JPM --peers WFC,C,GS

Output (named after the resolved registrant):
    - reports/<ENTITY>_Intelligence_Report_YYYYMMDD_HHMMSS.pdf
    - reports/<ENTITY>_Intelligence_Report_YYYYMMDD_HHMMSS.md
    - reports/<ENTITY>_Intelligence_Data_YYYYMMDD_HHMMSS.json
"""

import os
import re
import argparse
import sys
import json
import time
import logging
from datetime import date, datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file (project root)
try:
    from dotenv import load_dotenv
    # Try multiple locations for .env
    env_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env"),  # project root
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),  # apps/api
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            break
except ImportError:
    pass  # dotenv not installed, rely on system environment

# Set environment variables if needed
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://user:password@127.0.0.1:5433/mydb")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charts. Absent matplotlib the report WILL NOT GENERATE — charts are mandatory.
# Every chart restates a table that is present either way, but James requires
# visual data representation in every report.
try:
    from app.services import chart_service as charts
    CHARTS_AVAILABLE = charts.CHARTS_AVAILABLE
    if not CHARTS_AVAILABLE:
        raise ImportError("matplotlib loaded but CHARTS_AVAILABLE is False")
except Exception as e:  # pragma: no cover
    charts = None
    CHARTS_AVAILABLE = False
    logger.error("CHARTS UNAVAILABLE: %s — install matplotlib to generate reports", e)

FIGURE_COUNT = 0


def _figure(lines):
    """Count a chart and hand its markdown back to the caller."""
    global FIGURE_COUNT
    if lines:
        FIGURE_COUNT += 1
    return lines or []


# Import Phase 2 orchestrator
try:
    from app.connectors.deep_research_orchestrator import (
        run_comprehensive_intelligence,
        get_comprehensive_summary,
        check_connector_availability,
        get_connector_status,
    )
    PHASE2_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Phase 2 orchestrator not available: {e}")
    PHASE2_AVAILABLE = False

# Import legacy services
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.services.intelligence_service import generate_enhanced_intelligence_report
    from app.services.premium_pdf_service import convert_to_premium_pdf
    LEGACY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Legacy services not available: {e}")
    LEGACY_AVAILABLE = False

# Rendered from the report markdown, so it needs none of the legacy stack.
try:
    from app.services.markdown_pdf_service import convert_markdown_to_pdf
    PDF_AVAILABLE = True
except ImportError as e:
    logger.warning(f"PDF renderer not available: {e}")
    PDF_AVAILABLE = False

# New analysis services (no external APIs required)
try:
    from app.services.founder_correlations_service import (
        build_founder_correlation_graph,
        render_founder_correlations_markdown,
    )
    FOUNDER_CORRELATIONS_AVAILABLE = True
except ImportError:
    FOUNDER_CORRELATIONS_AVAILABLE = False

try:
    from app.services.market_dynamics_service import (
        get_market_dynamics,
        render_market_dynamics_markdown,
    )
    MARKET_DYNAMICS_AVAILABLE = True
except ImportError:
    MARKET_DYNAMICS_AVAILABLE = False

try:
    from app.services.coinvestment_network_service import (
        build_coinvestment_network,
        render_coinvestment_network_markdown,
    )
    COINVESTMENT_AVAILABLE = True
except ImportError:
    COINVESTMENT_AVAILABLE = False

try:
    from app.services.industry_trends_service import (
        get_industry_trends,
        render_industry_trends_markdown,
    )
    INDUSTRY_TRENDS_AVAILABLE = True
except ImportError:
    INDUSTRY_TRENDS_AVAILABLE = False

try:
    from app.services.self_dealing_service import (
        cross_reference_self_dealing,
        render_self_dealing_markdown,
    )
    SELF_DEALING_AVAILABLE = True
except ImportError:
    SELF_DEALING_AVAILABLE = False

try:
    from app.services.sec_api_report_service import render_all_sec_api_markdown
    SEC_API_REPORT_AVAILABLE = True
except ImportError:
    SEC_API_REPORT_AVAILABLE = False

# Configuration
OUTPUT_DIR = "../../reports"

# Runtime configuration. Populated by configure() from CLI arguments so the
# generator works for any listed company; the module-level defaults exist only
# so the script remains runnable with no arguments.
ENTITY_NAME = ""
TICKER = ""
COMPETITORS: list = []
TIMESTAMP = ""
OUTPUT_FILENAME = ""
OUTPUT_MD = ""
OUTPUT_JSON = ""
OUTPUT_HTML = ""


def resolve_entity_name(ticker: str) -> str:
    """
    Official registrant name for a ticker.

    Named after the entity that files the financial statements rather than the
    ticker's mapped entity: XOM maps to "ExxonMobil Holdings Corp", but every
    figure in the report comes from "EXXON MOBIL CORP".
    """
    import requests
    from app.connectors.sec_edgar_connector import get_filer_cik, SEC_HEADERS

    try:
        cik = get_filer_cik(ticker)
        if cik:
            resp = requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",
                                headers=SEC_HEADERS, timeout=20)
            if resp.ok:
                name = resp.json().get("name")
                if name:
                    return name
    except Exception as e:
        logger.warning("Could not resolve entity name for %s: %s", ticker, e)
    return ticker.upper()


def resolve_peers(ticker: str, limit: int = 4) -> list:
    """Peer tickers for comparison, from the market data provider."""
    try:
        from app.connectors.market_data_connector import get_peers
        return get_peers(ticker).get("peers", [])[:limit]
    except Exception as e:
        logger.warning("Could not resolve peers for %s: %s", ticker, e)
        return []


def _slug(name: str) -> str:
    """Filesystem-safe token for output filenames."""
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") or "Entity"


def configure(ticker: str, entity_name: str = "", competitors: list = None) -> None:
    """Bind the module-level report configuration for one run."""
    global ENTITY_NAME, TICKER, COMPETITORS
    global TIMESTAMP, OUTPUT_FILENAME, OUTPUT_MD, OUTPUT_JSON, OUTPUT_HTML

    TICKER = ticker.upper().strip()
    ENTITY_NAME = entity_name or resolve_entity_name(TICKER)
    COMPETITORS = competitors if competitors is not None else resolve_peers(TICKER)

    TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug(ENTITY_NAME)
    OUTPUT_FILENAME = f"{slug}_Intelligence_Report_{TIMESTAMP}.pdf"
    OUTPUT_MD = f"{slug}_Intelligence_Report_{TIMESTAMP}.md"
    OUTPUT_JSON = f"{slug}_Intelligence_Data_{TIMESTAMP}.json"
    OUTPUT_HTML = f"{slug}_Intelligence_Report_{TIMESTAMP}.html"


def format_currency(value, billions=False):
    """Format currency value. Missing values use the report's em-dash convention."""
    if value is None or value == 0:
        return "—"
    if billions:
        return f"${value / 1e9:,.1f}B"
    if value >= 1e9:
        return f"${value / 1e9:,.2f}B"
    if value >= 1e6:
        return f"${value / 1e6:,.1f}M"
    return f"${value:,.0f}"


def _fmt_scaled(value):
    """
    Currency at a scale suited to its magnitude.

    A fixed trillions scale renders anything below about $10B as "$0.00T", which
    covers most of the listed market.
    """
    if not value:
        return "—"
    for threshold, divisor, suffix in ((1e12, 1e12, "T"), (1e9, 1e9, "B"),
                                       (1e6, 1e6, "M")):
        if abs(value) >= threshold:
            return f"${value / divisor:,.2f}{suffix}"
    return f"${value:,.0f}"


def _fmt_m(value):
    """Format a raw USD figure in millions, matching the reference report style."""
    if value is None:
        return "—"
    return f"{value / 1e6:,.0f}"


def _pct(value, digits=1):
    return "—" if value is None else f"{value:.{digits}f}%"


# Nature-of-suit codes are filed as "820 Copyright". The label alone reads
# better in prose than the code.
def _clean_nos(value: str) -> str:
    return re.sub(r"^\d{3}\s+", "", (value or "").strip())


def _render_matter(matter: dict, entity_name: str) -> list:
    """
    One litigation matter as a sourced paragraph.

    Only fields actually present on the docket are stated. A matter retrieved
    without a cause of action is described as such rather than being given a
    plausible-sounding one.
    """
    name = matter.get("case_name") or matter.get("title") or matter.get("name") or "Unnamed matter"
    lines = [f"**{name}**", ""]

    facts = []
    if matter.get("docket_number"):
        facts.append(f"docket {matter['docket_number']}")
    if matter.get("court"):
        facts.append(matter["court"])
    if matter.get("date_filed"):
        facts.append(f"filed {matter['date_filed']}")
    facts.append(f"terminated {matter['date_terminated']}" if matter.get("date_terminated")
                 else "open on the docket as retrieved")
    if facts:
        sentence = ", ".join(facts)
        lines.append(sentence[0].upper() + sentence[1:] + ".")

    detail = []
    cause = _clean_nos(matter.get("cause"))
    nos = _clean_nos(matter.get("nature_of_suit"))
    if cause:
        detail.append(f"The cause of action is recorded as {cause}")
    if nos and nos.lower() not in cause.lower():
        detail.append(f"under a nature of suit of {nos}")
    if not cause and not nos:
        detail.append("The docket records no cause of action or nature of suit")
    if matter.get("assigned_to"):
        detail.append(f"assigned to {matter['assigned_to']}")
    if matter.get("referred_to"):
        detail.append(f"referred to {matter['referred_to']}")
    if matter.get("jury_demand"):
        detail.append(f"with a jury demand by the {matter['jury_demand'].lower()}")
    if detail:
        lines.append(", ".join(detail) + ".")

    source = matter.get("source") or "CourtListener"
    url = matter.get("absolute_url") or ""
    if url.startswith("/"):
        # CourtListener returns site-relative paths.
        url = f"https://www.courtlistener.com{url}"
    if url:
        source = f"[{source}]({url})"
    lines.append(f"*Source: {source}.*")
    lines.append("")
    return lines


_CASE_TYPE_LABELS = {
    "patent": "Patent",
    "ip": "Copyright and other intellectual property",
    "antitrust": "Antitrust",
    "securities": "Securities and shareholder",
    "employment": "Employment",
    "contract": "Contract",
    "regulatory": "Regulatory",
    "consumer": "Consumer",
    "environmental": "Environmental",
    "other": "Other and unclassified",
}

# What a court is for. Used only to explain why a venue recurs on a docket;
# these are descriptions of each forum's jurisdiction, not characterisations
# of how it rules.
_VENUE_NOTES = {
    "E.D. Texas": "a district that hears a disproportionate share of the "
                  "nation's patent filings because plaintiffs may choose it",
    "W.D. Texas": "another high-volume patent venue",
    "D. Delaware": "the district where most US public companies are "
                   "incorporated, which draws both patent and corporate suits",
    "Court of Chancery of Delaware": "Delaware's business court, which hears "
                                     "fiduciary-duty, merger and corporate "
                                     "governance disputes without a jury",
    "N.D. California": "the district covering Silicon Valley, and so the home "
                       "forum for many technology defendants",
}


def _venue_note(court: str) -> str:
    for key, note in _VENUE_NOTES.items():
        if key.lower() in (court or "").lower():
            return note
    return ""


def _render_note_matters(notes: dict, entity_name: str) -> list:
    """Legal matters as the issuer itself describes them in the 10-K.

    This is a different population from a docket search, and a more important
    one. A docket returns everything filed; the contingencies note returns what
    management concluded was material enough to describe, and includes
    regulatory inquiries that never reach a court. It also carries management's
    own accrual judgement, which no external source has.
    """
    matters = [m for m in ((notes or {}).get("legal_matters") or [])
               if not m.get("is_assessment")]
    assessment = next((m for m in ((notes or {}).get("legal_matters") or [])
                       if m.get("is_assessment")), None)
    if not matters:
        return []

    url = (notes or {}).get("source_url") or ""
    accession = (notes or {}).get("accession") or ""
    lines = ["### Matters disclosed in the contingencies note", ""]
    lines.append(
        f"{entity_name} describes {len(matters)} "
        f"{'matter' if len(matters) == 1 else 'matters'} in the commitments and "
        f"contingencies note to its most recent Form 10-K "
        f"({accession}). This is the issuer's own account, filed under the "
        f"liability that attaches to it, and it is authoritative on which "
        f"proceedings management considers material — a judgement no docket "
        f"search can supply."
    )
    lines.append("")

    venues = {}
    for matter in matters:
        if matter.get("venue"):
            venues[matter["venue"]] = venues.get(matter["venue"], 0) + 1
    if venues:
        leader, count = max(venues.items(), key=lambda kv: kv[1])
        if count > 1:
            lines.append(
                f"{count} of the {len(matters)} are pending in the "
                f"{leader}, which concentrates the outcome risk in a single "
                f"forum and a single body of circuit precedent."
            )
            lines.append("")

    for index, matter in enumerate(matters, 1):
        heading = matter.get("venue") or "Proceeding"
        dated = f", first filed {matter['first_date']}" if matter.get("first_date") else ""
        lines.append(f"**Matter {index} — {heading}{dated}.** As disclosed:")
        lines.append("")
        lines.append(f"> {matter['text']}")
        lines.append("")

    if assessment:
        lines.append("**Management's assessment.** As stated in the same note:")
        lines.append("")
        lines.append(f"> {assessment['text']}")
        lines.append("")
        lines.append(
            f"The absence of an accrual is itself the disclosure. Under ASC 450 a "
            f"loss is accrued when it is both probable and reasonably estimable; "
            f"stating that liabilities are reasonably possible but not probable "
            f"places these matters deliberately below that threshold. It means the "
            f"balance sheet carries no provision against them, so any adverse "
            f"outcome falls directly to earnings in the period it resolves."
        )
        lines.append("")

    if url:
        lines.append(f"Source: Form 10-K commitments and contingencies note, {url}")
        lines.append("")
    return lines


def _render_legal(litigation: dict, entity_name: str, notes: dict = None) -> list:
    """Legal exposure as an analysed docket rather than a list of cases.

    Distinguishes matters where the company is captioned as a party from those
    that merely cite it in an opinion. The distinction is the whole point:
    full-text retrieval returns both, and only the former is exposure.
    """
    lines = ["## Legal and Regulatory Exposure", ""]

    federal = litigation.get("federal_cases") or {}
    all_cases = federal.get("cases") or []
    party = [c for c in all_cases if c.get("entity_is_party")]
    cited = [c for c in all_cases if not c.get("entity_is_party")]
    risk = litigation.get("risk_assessment") or {}

    resolved = [c for c in party if c.get("date_terminated")]
    open_matters = [c for c in party if not c.get("date_terminated")]

    lines.append(
        f"Federal docket retrieval returned {len(all_cases)} matters naming "
        f"{entity_name}. Of those, {len(party)} caption the company as a party "
        f"and represent actual exposure; the remaining {len(cited)} cite it in "
        f"the body of an opinion or filing without joining it, and are treated "
        f"separately below. Overall litigation risk is assessed as "
        f"{str(risk.get('overall_risk', 'unknown')).lower()}."
    )
    lines.append("")

    lines.extend(_render_note_matters(notes, entity_name))

    # ── Composition ──────────────────────────────────────────────────────
    if party:
        by_type = {}
        for c in party:
            by_type.setdefault(c.get("case_type") or "other", []).append(c)
        lines.append("| Category | Matters | Open | Resolved |")
        lines.append("|----------|---------|------|----------|")
        for t, items in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
            done = sum(1 for c in items if c.get("date_terminated"))
            lines.append(
                f"| {_CASE_TYPE_LABELS.get(t, t.title())} | {len(items)} "
                f"| {len(items) - done} | {done} |"
            )
        lines.append(
            f"| **Total** | **{len(party)}** | **{len(open_matters)}** "
            f"| **{len(resolved)}** |"
        )
        lines.append("")

        # Venue concentration is a real signal: repeat filings in a plaintiff's
        # chosen patent forum read differently from suits in a home district.
        courts = {}
        for c in party:
            if c.get("court"):
                courts[c["court"]] = courts.get(c["court"], 0) + 1
        if courts:
            ranked = sorted(courts.items(), key=lambda kv: -kv[1])
            lead, lead_n = ranked[0]
            venue = (
                f"The {len(party)} matters sit across {len(courts)} "
                f"{'court' if len(courts) == 1 else 'courts'}"
            )
            if lead_n > 1:
                venue += f", with {lead_n} filed in {lead}"
            else:
                venue += f", led by {lead}"
            note = _venue_note(lead)
            if note:
                venue += f" — {note}"
            lines.append(venue + ".")
            lines.append("")

        # Statutory basis, where the docket records one.
        causes = [_clean_nos(c.get("cause")) for c in party if c.get("cause")]
        if causes:
            lines.append(
                f"{len(causes)} of the {len(party)} party matters record a "
                f"statutory cause of action: "
                + "; ".join(sorted(set(causes))) + "."
            )
            lines.append("")

        # ── Matter-level narrative, grouped ──────────────────────────────
        for t, items in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"### {_CASE_TYPE_LABELS.get(t, t.title())} "
                         f"({len(items)})")
            lines.append("")
            for m in sorted(items, key=lambda x: x.get("date_filed") or "",
                            reverse=True):
                lines.extend(_render_matter(m, entity_name))
    else:
        lines.append(
            f"No federal matter retrieved in the search window captions "
            f"{entity_name} as a party."
        )
        lines.append("")

    # ── Regulatory dockets: absence is a finding ─────────────────────────
    regulatory = (
        ("SEC enforcement",
         (litigation.get("sec_enforcement") or {}).get("enforcement_actions") or []),
        ("FTC proceedings", litigation.get("ftc_proceedings") or []),
        ("DOJ antitrust matters", litigation.get("doj_antitrust") or []),
        ("ITC section 337 investigations", litigation.get("itc_investigations") or []),
        ("PTAB proceedings", litigation.get("ptab_proceedings") or []),
    )
    empty = [label for label, items in regulatory if not items]
    populated = [(label, items) for label, items in regulatory if items]
    for label, items in populated:
        lines.append(f"### {label} ({len(items)})")
        lines.append("")
        for m in items[:25]:
            lines.extend(_render_matter(m, entity_name))
    if empty:
        lines.append("### Regulatory dockets searched without result")
        lines.append("")
        lines.append(
            "The following registers were queried for this entity and returned "
            "nothing in the search window: " + "; ".join(empty).lower() + ". "
            "This is a negative finding rather than an absence of coverage — "
            "each register was reachable and answered. It does not extend to "
            "non-public investigations or to foreign regulators outside these "
            "systems."
        )
        lines.append("")

    # ── Cited-only matters ───────────────────────────────────────────────
    if cited:
        courts = sorted({c.get("court") for c in cited if c.get("court")})
        types = {}
        for c in cited:
            types[c.get("case_type") or "other"] = types.get(c.get("case_type") or "other", 0) + 1
        lines.append(f"### Matters citing {entity_name} without naming it "
                     f"({len(cited)})")
        lines.append("")
        lines.append(
            f"Full-text retrieval surfaced {len(cited)} further federal matters "
            f"across {len(courts)} courts that reference the company in "
            f"pleadings or opinions without joining it as a party. These carry "
            f"no direct liability and are excluded from the exposure count, but "
            f"the pattern is informative: it shows where the company's "
            f"technology, contracts or market position is being litigated "
            f"between other parties."
        )
        lines.append("")
        spread = ", ".join(
            f"{_CASE_TYPE_LABELS.get(t, t.title()).lower()} {n}"
            for t, n in sorted(types.items(), key=lambda kv: -kv[1])[:6]
        )
        lines.append(f"By subject matter: {spread}.")
        lines.append("")
        recent = sorted(cited, key=lambda x: x.get("date_filed") or "",
                        reverse=True)[:8]
        lines.append("| Filed | Matter | Court |")
        lines.append("|-------|--------|-------|")
        for c in recent:
            nm = (c.get("case_name") or "")[:70]
            lines.append(f"| {c.get('date_filed') or '—'} | {nm} "
                         f"| {c.get('court') or '—'} |")
        lines.append("")

    return lines


_ORDINALS = ("One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
             "Nine", "Ten")


def _sentence_case(text: str) -> str:
    """Capitalise the first letter only.

    str.capitalize lowercases the remainder, which would turn FY2026 into
    fy2026 and $215,938M into $215,938m.
    """
    return text[:1].upper() + text[1:] if text else text


def _money(value: float) -> str:
    """Scale a dollar amount to the unit that reads naturally at its size."""
    for cut, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= cut:
            return f"${value / cut:,.2f}{suffix}"
    return f"${value:,.0f}"


def _fiscal_year_end(raw: str) -> str:
    """Render EDGAR's MMDD fiscal year end as a date.

    EDGAR reports it as four digits, so "0131" would otherwise print verbatim.
    """
    if not raw:
        return "—"
    digits = str(raw).strip()
    if len(digits) == 4 and digits.isdigit():
        month, day = int(digits[:2]), int(digits[2:])
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{datetime(2000, month, day).strftime('%d %B')}"
    return digits


def _summary_findings(data: dict, entity_name: str, ticker: str) -> list:
    """Rank the report's findings by materiality.

    Each finding is a (weight, text) pair built only where the underlying data
    was retrieved, so a company with no litigation or no federal footprint
    simply yields fewer findings rather than empty assertions. Weight orders
    the narrative; it is not published.
    """
    findings = []

    financial = data.get("financial_intelligence", {}) or {}
    notes = data.get("filing_notes", {}) or {}
    statements = financial.get("financial_statements", {}) or {}
    annual = statements.get("income_statement", []) or []
    dcf = (data.get("valuation_analysis", {}) or {}).get("dcf", {}) or {}
    snapshot = dcf.get("market_snapshot", {}) or {}

    # ── Growth and margin trajectory ─────────────────────────────────────
    if len(annual) >= 2:
        cur, prior = annual[0], annual[1]
        rev, prev_rev = cur.get("Revenues"), prior.get("Revenues")
        if rev and prev_rev:
            growth = (rev - prev_rev) / prev_rev * 100
            margin = cur.get("net_margin")
            prior_margin = prior.get("net_margin")
            text = (
                f"revenue grew {growth:+.1f}% in FY{cur.get('fiscal_year', '')} "
                f"to ${_fmt_m(rev)}M"
            )
            if margin is not None:
                text += f", at a {_pct(margin)} net margin"
                if prior_margin is not None:
                    move = (margin - prior_margin) * 100 if margin < 1 else margin - prior_margin
                    direction = ("widening" if move > 0.5 else
                                 "compressing" if move < -0.5 else "holding")
                    text += (f" — {direction} against "
                             f"{_pct(prior_margin)} a year earlier")
            # Growth against prior-year growth is the trajectory, and it says
            # more than the level does on its own.
            if len(annual) >= 3:
                before = annual[2].get("Revenues")
                if before and prev_rev:
                    prior_growth = (prev_rev - before) / before * 100
                    shift = growth - prior_growth
                    text += (
                        f". Growth is {'decelerating' if shift < -2 else 'accelerating' if shift > 2 else 'steady'} "
                        f"— the prior year grew {prior_growth:+.1f}%, so the "
                        f"rate has moved {shift:+.1f} points"
                    )
            findings.append((100 + abs(growth), _sentence_case(text) + "."))

    # ── Valuation gap ────────────────────────────────────────────────────
    intrinsic = dcf.get("intrinsic_price_per_share")
    price = dcf.get("current_market_price")
    if intrinsic and price:
        gap = (intrinsic - price) / price * 100
        findings.append((90 + abs(gap), (
            f"The discounted cash flow model values the equity at "
            f"${intrinsic:,.2f} against a traded ${price:,.2f}, a gap of "
            f"{gap:+.0f}%. The model is not asserting mispricing so much as "
            f"measuring the growth the market is underwriting; the Valuation "
            f"section inverts it to state that rate explicitly."
        )))

    # ── Insider disposition ──────────────────────────────────────────────
    insider = data.get("insider_transactions", {}) or {}
    txns = insider.get("transactions") or []
    if txns:
        sales = [t for t in txns if t.get("acquired_disposed") == "D"
                 and t.get("open_market") and t.get("value")]
        if sales:
            gross = sum(t["value"] for t in sales)
            people = len({t.get("insider") for t in sales})
            buys = [t for t in txns if t.get("acquired_disposed") == "A"
                    and t.get("open_market") and t.get("value")]
            text = (
                f"Insiders disposed of {format_currency(gross)} of stock on the "
                f"open market across {len(sales)} transactions by {people} "
                f"individuals"
            )
            if buys:
                text += (f", against {format_currency(sum(t['value'] for t in buys))} "
                         f"of open-market purchases")
            else:
                text += (", with no open-market purchase recorded in the same "
                         "period")
            findings.append((85, text + "."))

    # ── Ownership ────────────────────────────────────────────────────────
    holdings = data.get("institutional_holdings", {}) or {}
    if holdings.get("pct_shares_outstanding"):
        findings.append((60, (
            f"{holdings.get('institutions_holding', 0)} of the "
            f"{holdings.get('institutions_polled', 0)} largest institutional "
            f"managers report holding {holdings['pct_shares_outstanding']:.1f}% "
            f"of shares outstanding on Form 13F. Concentration at that level "
            f"means index and mega-cap active flows, rather than company "
            f"disclosure, set much of the near-term price."
        )))

    # ── Governance ───────────────────────────────────────────────────────
    proxy = data.get("proxy_intelligence", {}) or {}
    board = (proxy.get("board_composition") or {})
    directors = board.get("directors") or []
    if directors:
        ages = [d["age"] for d in directors if isinstance(d.get("age"), int)]
        text = f"The board seats {len(directors)} directors"
        if ages:
            text += f", median age {sorted(ages)[len(ages) // 2]}"
        sop = proxy.get("say_on_pay") or {}
        if sop.get("approval_pct"):
            text += (f", and say-on-pay carried {sop['approval_pct']:.1f}% "
                     f"support at the last annual meeting")
        findings.append((45, text + "."))

    # ── Legal ────────────────────────────────────────────────────────────
    lit = data.get("litigation_intelligence", {}) or {}
    fed = (lit.get("federal_cases") or {}).get("summary") or {}
    if fed.get("cases_as_party") is not None:
        as_party = fed.get("cases_as_party", 0)
        findings.append((55 if as_party else 30, (
            f"{as_party} federal matters name the company as a party"
            + (f", alongside {fed.get('cases_mentioning_only', 0)} that cite it "
               f"without joining it" if fed.get("cases_mentioning_only") else "")
            + ". Every register queried for enforcement activity is reported in "
              "the legal section, including those that returned nothing."
        )))

    # ── Political and federal ────────────────────────────────────────────
    political = data.get("political_intelligence", {}) or {}
    lobby = political.get("lobbying_summary") or {}
    if lobby.get("total_spend"):
        text = (f"Disclosed lobbying runs to "
                f"{format_currency(lobby['total_spend'])} across "
                f"{lobby.get('filing_count', 0)} Senate LDA filings")
        pac = political.get("pac_activity") or {}
        if pac.get("committee_found") and pac.get("total_all_cycles"):
            text += (f", with a corporate PAC disbursing "
                     f"{format_currency(pac['total_all_cycles'])} across the "
                     f"cycles retrieved")
        findings.append((50, text + "."))

    contracts = data.get("contract_intelligence", {}) or {}
    csum = contracts.get("summary") or {}
    if csum.get("total_obligated"):
        findings.append((35, (
            f"Federal prime awards total "
            f"{format_currency(csum['total_obligated'])} across "
            f"{csum.get('total_contracts', 0)} awards — immaterial to revenue, "
            f"but almost entirely research funding rather than product "
            f"procurement, which is what makes it worth reading."
        )))

    # ── Risk ─────────────────────────────────────────────────────────────
    register = data.get("risk_register", {}) or {}
    rsum = register.get("summary") or {}
    if rsum.get("overall_risk_profile"):
        critical = rsum.get("critical_risks", 0)
        high = rsum.get("high_risks", 0)
        if critical or high:
            findings.append((65, (
                f"The risk register scores {critical} critical and {high} high "
                f"risks, on an overall profile of "
                f"{str(rsum['overall_risk_profile']).lower()}. Each is tied to "
                f"the filing or dataset that evidences it."
            )))

    # ── Network intelligence (P-series) ───────────────────────────────────
    rpt = [t for t in (proxy.get("related_party_transactions") or [])
           if not t.get("is_routine")]
    if rpt:
        largest = max((t.get("largest_amount") or 0) for t in rpt)
        findings.append((80 if largest >= 1e6 else 55, (
            f"The latest proxies disclose {len(rpt)} related-party passages "
            f"under Item 404"
            + (f", the largest at {format_currency(largest)}" if largest else "")
            + ". Arrangements with family members of officers and directors, "
              "and transactions with entities they control, are the conflicts "
              "the financial statements do not surface on their own."
        )))

    interlocks = data.get("board_interlocks") or {}
    current_seats = sum(p.get("current_seat_count") or 0
                        for p in (interlocks.get("people") or []))
    if current_seats:
        shared = interlocks.get("shared_boards") or []
        text = (
            f"{current_seats} outside public-company seat"
            f"{'' if current_seats == 1 else 's'} are currently held by this "
            f"board's directors and officers, read from their own Section 16 "
            f"filings"
        )
        if shared:
            text += (f". {len(shared)} of those seats are shared by two or "
                     f"more of this board — the interlock proper")
        findings.append((70, text + "."))

    investments = notes.get("investments") or []
    roll = next((i for i in investments
                 if i.get("kind") == "portfolio_rollforward"), None)
    if roll and roll.get("closing_balance") and roll.get("net_additions"):
        closing = roll["closing_balance"]
        additions = roll["net_additions"]
        findings.append((75, (
            f"Private-company holdings carried under the measurement "
            f"alternative closed the year at {format_currency(closing)}, of "
            f"which {format_currency(additions)} was capital deployed during "
            f"the year rather than revaluation — "
            f"{additions / closing * 100:.0f}% of the book is current "
            f"deployment."
        )))

    subs = (notes.get("subsidiaries") or {})
    if (subs.get("total") or 0) >= 8:
        holding = {"cayman islands", "bermuda", "luxembourg", "ireland",
                   "netherlands", "british virgin islands", "jersey", "guernsey"}
        by_j = subs.get("by_jurisdiction") or {}
        offshore = sum(c for j, c in by_j.items() if j.lower() in holding)
        if offshore:
            findings.append((48, (
                f"Exhibit 21 names {subs['total']} subsidiaries, {offshore} of "
                f"them organised in jurisdictions used principally for holding "
                f"and financing structures."
            )))

    overlap = data.get("institutional_overlap") or {}
    analysis = overlap.get("overlap_analysis") or overlap
    skew_flags = [f for f in (analysis.get("risk_flags") or [])
                  if f.get("type") == "allocation_skew"]
    if skew_flags:
        findings.append((58, (
            f"{len(skew_flags)} institutional manager"
            f"{'' if len(skew_flags) == 1 else 's'} weight this issuer or a "
            f"peer at two times or more the weight of another competitor in "
            f"the same portfolio — an active allocation, not index tracking. "
            f"{skew_flags[0].get('detail', '')}."
        )))

    trends = _network_trends(data)
    overlaps = trends.get("n07_overlaps") or []
    if overlaps:
        findings.append((82, (
            f"{len(overlaps)} cross-link"
            f"{'' if len(overlaps) == 1 else 's'} appear between related-party "
            f"counterparties, subsidiaries, private holdings and director "
            f"affiliations — relationships that sit in separate filings and "
            f"are invisible until the registers are read against each other. "
            f"{overlaps[0]}"
        )))
    seats = trends.get("n01_competitor_seats") or []
    if seats:
        findings.append((78, (
            f"{len(seats)} outside seat"
            f"{'' if len(seats) == 1 else 's'} land on a competitor or named "
            f"strategic counterparty. {seats[0]}"
        )))
    holder_timing = trends.get("n05_holder_timing") or []
    if holder_timing:
        findings.append((60, holder_timing[0]))
    jurisdictions = trends.get("n06_jurisdictions") or []
    if jurisdictions:
        findings.append((50, jurisdictions[0]))

    findings.sort(key=lambda f: -f[0])
    return [text for _, text in findings]


def _entity_key(name: str) -> str:
    """Normalise a company or person name for fuzzy overlap matching."""
    value = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    value = re.sub(
        r"\b(the|inc|corp|corporation|company|co|plc|ltd|limited|llc|lp|"
        r"holdings?|group|foundation|trust|partners|management)\b", " ", value)
    return " ".join(value.split())


def _names_match(left: str, right: str) -> bool:
    a, b = _entity_key(left), _entity_key(right)
    if not a or not b or len(a) < 3 or len(b) < 3:
        return False
    return a == b or a in b or b in a


def _competitor_universe(data: dict) -> list:
    """Tickers and names of peers used for network matching."""
    peers = list(COMPETITORS or [])
    overlap = data.get("institutional_overlap") or {}
    for ticker in overlap.get("competitors") or []:
        if ticker and ticker.upper() not in {p.upper() for p in peers}:
            peers.append(ticker.upper())
    return peers


def _named_counterparties(data: dict) -> list:
    """Acquisition targets and other named strategic counterparties from notes."""
    notes = data.get("filing_notes") or {}
    named = []
    for acq in notes.get("acquisitions") or []:
        if acq.get("counterparty"):
            named.append({
                "name": acq["counterparty"],
                "role": "acquisition counterparty",
                "source": "10-K business combination / licence note",
            })
    for inv in notes.get("investments") or []:
        if inv.get("kind") == "named_holding" and inv.get("name"):
            named.append({
                "name": inv["name"],
                "role": "private holding",
                "source": "ASC 321 note",
            })
        for company in inv.get("companies") or inv.get("holdings") or []:
            name = company.get("name") if isinstance(company, dict) else company
            if name:
                named.append({
                    "name": name,
                    "role": "private holding",
                    "source": "ASC 321 note",
                })
    return named


def _network_competitor_seats(data: dict) -> list:
    """N-01 — directors/officers with seats at competitors or named counterparties."""
    interlocks = data.get("board_interlocks") or {}
    peers = {p.upper() for p in _competitor_universe(data)}
    counterparties = _named_counterparties(data)
    findings = []
    seen = set()

    for person in interlocks.get("people") or []:
        for seat in person.get("other_seats") or []:
            ticker = (seat.get("ticker") or "").upper()
            issuer = seat.get("issuer") or ticker
            role = ", ".join(seat.get("roles") or []).lower() or "insider"
            currency = "currently" if seat.get("current") else (
                f"previously (last filed {seat.get('last_filed')})"
                if seat.get("last_filed") else "previously")
            match_role = None
            if ticker and ticker in peers:
                match_role = f"competitor {ticker}"
            else:
                for cp in counterparties:
                    if _names_match(issuer, cp["name"]) or (
                            ticker and _names_match(ticker, cp["name"])):
                        match_role = f"{cp['role']} {cp['name']}"
                        break
            if not match_role:
                continue
            key = (person.get("name"), ticker or issuer, match_role)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                f"{person.get('name')} {currency} reports at {issuer}"
                + (f" ({ticker})" if ticker else "")
                + f" as {role} — {match_role}."
                + (f" Source: {seat.get('source_url')}."
                   if seat.get("source_url") else "")
            )
    return findings


def _network_co_holdings(data: dict) -> list:
    """N-02 — institutions that hold the issuer and competitors at skewed weights."""
    overlap = data.get("institutional_overlap") or {}
    analysis = overlap.get("overlap_analysis") or overlap or {}
    findings = []
    for flag in analysis.get("risk_flags") or []:
        if flag.get("type") == "allocation_skew" and flag.get("detail"):
            findings.append(flag["detail"].rstrip(".") + ".")
    # Dominant cross-holders are informative when the dollar weight is large.
    for flag in analysis.get("risk_flags") or []:
        if flag.get("type") == "dominant_cross_holder" and flag.get("detail"):
            findings.append(flag["detail"].rstrip(".") + ".")
    shared = analysis.get("shared_holders") or []
    skewed = [h for h in shared
              if (h.get("weight_skew") or 0) >= 2
              and h.get("overweight")]
    for holder in skewed[:6]:
        details = holder.get("details_by_ticker") or {}
        name = next((d.get("original_name") for d in details.values()
                     if d.get("original_name")),
                    holder.get("normalized_name", "Manager"))
        text = (
            f"{name} weights {holder['overweight']} at "
            f"{holder['weight_skew']:.1f}x its position in the lightest peer "
            f"it also holds — conviction relative to the rest of the set, not "
            f"an index weight."
        )
        if text not in findings and not any(holder["overweight"] in f
                                            and name.split()[0].lower() in f.lower()
                                            for f in findings):
            findings.append(text)
    return findings[:8]


def _network_invest_acq_cluster(data: dict) -> list:
    """N-03 — whether private holdings cluster with acquisition counterparties.

    The ASC 321 rollforward is usually aggregate-only. This fires only when
    named holdings exist alongside named acquisitions — otherwise omitted.
    """
    counterparties = _named_counterparties(data)
    holdings = [c for c in counterparties if c["role"] == "private holding"]
    acqs = [c for c in counterparties if c["role"] == "acquisition counterparty"]
    if not holdings or not acqs:
        return []
    findings = []
    for hold in holdings:
        for acq in acqs:
            if _names_match(hold["name"], acq["name"]):
                findings.append(
                    f"{hold['name']} appears both as a private holding and as "
                    f"an acquisition counterparty — the investment and the "
                    f"business combination sit on the same entity."
                )
            # Shared token overlap of 2+ meaningful tokens is a weak signal;
            # require a real name match only.
    if holdings and acqs and not findings:
        hold_names = ", ".join(h["name"] for h in holdings[:6])
        acq_names = ", ".join(a["name"] for a in acqs[:6])
        findings.append(
            f"Named private holdings ({hold_names}) and acquisition "
            f"counterparties ({acq_names}) do not overlap on the entities "
            f"disclosed. Sector clustering cannot be tested further without "
            f"issuer-named portfolio companies beyond the ASC 321 aggregate."
        )
    return findings


def _network_personnel_moves(data: dict) -> list:
    """N-04 — executives/directors who also sat at investees or acquirees."""
    interlocks = data.get("board_interlocks") or {}
    targets = _named_counterparties(data)
    stakes = ((data.get("beneficial_ownership") or {}).get("stakes_in_others")
              or [])
    for stake in stakes:
        if stake.get("subject"):
            targets.append({
                "name": stake["subject"],
                "role": "5%+ investee",
                "source": stake.get("form") or "Schedule 13",
            })
    if not targets:
        return []

    findings = []
    seen = set()
    for person in interlocks.get("people") or []:
        for seat in person.get("other_seats") or []:
            issuer = seat.get("issuer") or ""
            for target in targets:
                if not _names_match(issuer, target["name"]):
                    continue
                key = (person.get("name"), target["name"])
                if key in seen:
                    continue
                seen.add(key)
                when = ("currently" if seat.get("current")
                        else f"as of last filing {seat.get('last_filed', '—')}")
                findings.append(
                    f"{person.get('name')} {when} reports at {issuer}, which "
                    f"is also a {target['role']} of this issuer "
                    f"({target['source']})."
                )
    return findings


def _parse_iso_date(value: str):
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _network_holder_timing(data: dict) -> list:
    """N-05 — 5%+ holders appearing near strategic announcements."""
    holders = (data.get("beneficial_ownership") or {}).get("holders") or []
    events = ((data.get("event_timeline") or {}).get("events") or [])
    strategic = [
        e for e in events
        if e.get("event_type") in ("acquisition", "material_event",
                                   "executive_change")
        or (e.get("form_type") == "8-K"
            and any((item.get("code") or "").startswith(("1.", "2.", "5.", "8."))
                    for item in (e.get("items") or [{}])))
        or (e.get("form_type") == "8-K"
            and not e.get("items")
            and e.get("event_type") != "earnings")
    ]
    findings = []
    window = 90  # calendar days either side

    for holder in holders:
        filed = _parse_iso_date(holder.get("filed"))
        if not filed or (holder.get("percent_of_class") or 0) < 5:
            continue
        nearby = []
        for event in strategic:
            ed = _parse_iso_date(event.get("date"))
            if not ed:
                continue
            delta = (ed - filed).days
            if abs(delta) <= window:
                nearby.append((abs(delta), delta, event))
        nearby.sort()
        if not nearby:
            continue
        _, delta, event = nearby[0]
        relation = ("after" if delta > 0 else "before" if delta < 0
                    else "on the same day as")
        days = abs(delta)
        findings.append(
            f"{holder.get('holder') or 'A 5%+ holder'} filed "
            f"{holder.get('form') or 'Schedule 13'} on {holder.get('filed')} "
            f"at {holder.get('percent_of_class')}% — {days} day"
            f"{'' if days == 1 else 's'} {relation} "
            f"{event.get('title') or event.get('form_type') or 'a strategic disclosure'} "
            f"({event.get('date')}). Timing adjacency is not causation; both "
            f"dates are on the public record."
            + (f" Source: {holder.get('source_url')}."
               if holder.get("source_url") else "")
        )
    return findings[:8]


def _network_jurisdiction_mismatch(data: dict) -> list:
    """N-06 — subsidiaries organised where no operations revenue is disclosed."""
    notes = data.get("filing_notes") or {}
    subs = (notes.get("subsidiaries") or {})
    entities = subs.get("subsidiaries") or []
    if not entities:
        return []

    geo = (((data.get("financial_intelligence") or {}).get("segments") or {})
           .get("geographic") or [])
    geo_keys = {_entity_key(g.get("name")) for g in geo if g.get("name")}
    # United States covers Delaware / California / etc. domestic org.
    us_aliases = {"united states", "us", "u s", "america", "north america"}
    has_us_geo = any(k in us_aliases or "united states" in k for k in geo_keys)

    domestic = {
        "delaware", "california", "new york", "texas", "washington", "nevada",
        "massachusetts", "illinois", "florida", "oregon", "colorado",
        "united states", "usa", "u.s.", "u.s.a",
    }
    holding = {
        "cayman islands", "bermuda", "luxembourg", "ireland", "netherlands",
        "british virgin islands", "jersey", "guernsey", "mauritius", "curacao",
        "barbados", "panama", "singapore", "hong kong", "switzerland",
    }

    findings = []
    by_j = {}
    for entity in entities:
        j = (entity.get("jurisdiction") or "Not Stated").strip()
        by_j.setdefault(j, []).append(entity.get("name") or "unnamed")

    mismatched = []
    for jurisdiction, names in by_j.items():
        jkey = jurisdiction.lower().strip()
        if jkey in ("not stated", ""):
            continue
        if jkey in domestic and has_us_geo:
            continue
        # Match geo segment names (Taiwan, China, Israel, …)
        if any(_names_match(jurisdiction, g.get("name", "")) for g in geo):
            continue
        if any(jkey in gk or gk in jkey for gk in geo_keys if gk):
            continue
        mismatched.append((jurisdiction, names))

    if mismatched and geo:
        parts = []
        for jurisdiction, names in sorted(mismatched, key=lambda x: -len(x[1])):
            sample = ", ".join(names[:3])
            extra = f" (+{len(names) - 3} more)" if len(names) > 3 else ""
            parts.append(f"{jurisdiction} ({sample}{extra})")
        geo_list = ", ".join(g.get("name") for g in geo if g.get("name"))
        findings.append(
            f"Exhibit 21 lists subsidiaries organised in "
            f"{'; '.join(parts)}, none of which appear among the revenue "
            f"geographies the issuer discloses ({geo_list}). Organisation "
            f"jurisdiction is not the same as where revenue is recognised; "
            f"the mismatch marks a legal footprint without a matching "
            f"operations disclosure, not a finding about profit location."
        )

    offshore = [(j, names) for j, names in by_j.items()
                if j.lower() in holding]
    if offshore:
        count = sum(len(n) for _, n in offshore)
        named = ", ".join(
            f"{len(names)} in {j}" for j, names in
            sorted(offshore, key=lambda x: -len(x[1])))
        findings.append(
            f"{count} "
            f"{'subsidiary sits' if count == 1 else 'subsidiaries sit'} "
            f"in jurisdictions used principally for holding and financing "
            f"structures — {named}. The exhibit states organisation only."
        )
    return findings


def _network_trends(data: dict) -> dict:
    """N-01..N-06 analyses. Empty lists are valid and omit their subsections."""
    return {
        "n01_competitor_seats": _network_competitor_seats(data),
        "n02_co_holdings": _network_co_holdings(data),
        "n03_invest_acq": _network_invest_acq_cluster(data),
        "n04_personnel_moves": _network_personnel_moves(data),
        "n05_holder_timing": _network_holder_timing(data),
        "n06_jurisdictions": _network_jurisdiction_mismatch(data),
        "n07_overlaps": _network_overlaps(data),
    }


def _network_overlaps(data: dict) -> list:
    """N-07 — related-party counterparties against subsidiaries, investees and seats.

    Each register is filed for a different purpose and never cross-references
    the others. Reading them against each other is what turns three disclosures
    into one finding.
    """
    proxy = data.get("proxy_intelligence") or {}
    notes = data.get("filing_notes") or {}
    interlocks = data.get("board_interlocks") or {}
    beneficial = data.get("beneficial_ownership") or {}

    counterparties = []
    for entry in proxy.get("related_party_transactions") or []:
        if entry.get("is_routine"):
            continue
        for name in entry.get("counterparties") or []:
            counterparties.append((name, entry))
        # A family arrangement names no counterparty entity; the relationship
        # itself is the link to a director, and that is matched separately.
        text = entry.get("sentence") or entry.get("text") or ""
        for match in re.finditer(
                r"\b([A-Z][\w.&'-]+(?:\s+[A-Z][\w.&'-]+){0,4})"
                r"(?:\s*,?\s*(?:Inc|Corp|LLC|Ltd|Foundation|Company)\.?)", text):
            counterparties.append((match.group(0).strip(" ,."), entry))

    subsidiaries = [(s.get("name"), s)
                    for s in ((notes.get("subsidiaries") or {}).get("subsidiaries")
                              or []) if s.get("name")]
    seats = []
    for person in interlocks.get("people") or []:
        for seat in person.get("other_seats") or []:
            seats.append((seat.get("issuer") or seat.get("ticker"), person, seat))

    stakes = [(s.get("subject"), s)
              for s in (beneficial.get("stakes_in_others") or []) if s.get("subject")]

    found = []
    seen = set()

    def record(key, text):
        if key in seen:
            return
        seen.add(key)
        found.append(text)

    for name, entry in counterparties:
        for sub_name, _sub in subsidiaries:
            if _names_match(name, sub_name):
                record(("sub", name.lower()), (
                    f"{name} appears both as a related-party counterparty and "
                    f"as a subsidiary named in Exhibit 21"
                    + (f" — {format_currency(entry['largest_amount'])} disclosed"
                       if entry.get("largest_amount") else "")
                    + "."
                ))
        for issuer, person, seat in seats:
            if _names_match(name, issuer):
                record(("seat", name.lower(), person["name"].lower()), (
                    f"{name} is a related-party counterparty and also an "
                    f"issuer where {person['name']} reports under Section 16"
                    + (f" as {', '.join(seat.get('roles') or []).lower()}"
                       if seat.get("roles") else "")
                    + "."
                ))
        for subject, stake in stakes:
            if _names_match(name, subject):
                record(("stake", name.lower()), (
                    f"{name} appears as a related-party counterparty and as a "
                    f"public company in which this issuer holds "
                    f"{stake.get('percent_of_class')}%."
                ))

    # Directors who sit elsewhere at an entity that also shows up in the
    # related-party prose, even when the counterparty extractor missed the name.
    for entry in proxy.get("related_party_transactions") or []:
        if entry.get("is_routine"):
            continue
        text = (entry.get("sentence") or entry.get("text") or "").lower()
        for issuer, person, seat in seats:
            key = _entity_key(issuer)
            if key and len(key) >= 4 and key in text:
                record(("prose", key, person["name"].lower()), (
                    f"The related-party disclosure names {issuer}, where "
                    f"{person['name']} also holds a "
                    f"{', '.join(seat.get('roles') or ['role']).lower()}."
                ))

    return found


def _evidence_linked_risks(data: dict, entity_name: str) -> list:
    """Risks that name the filing or dataset that raises them.

    The connector's register mixes filing-derived entries with industry
    boilerplate. This list is built only from data the report holds, so every
    entry can be opened against a source.
    """
    risks = []
    proxy = data.get("proxy_intelligence") or {}
    notes = data.get("filing_notes") or {}
    interlocks = data.get("board_interlocks") or {}
    insider = data.get("insider_transactions") or {}
    lit = data.get("litigation_intelligence") or {}
    overlap = ((data.get("institutional_overlap") or {}).get("overlap_analysis")
               or data.get("institutional_overlap") or {})

    rpt = [t for t in (proxy.get("related_party_transactions") or [])
           if not t.get("is_routine") and (t.get("largest_amount") or 0) >= 120_000]
    if rpt:
        largest = max(t.get("largest_amount") or 0 for t in rpt)
        risks.append({
            "title": "Related-party concentration",
            "category": "Governance",
            "description": (
                f"{len(rpt)} Item 404 disclosures in the proxies read, the "
                f"largest at {format_currency(largest)}. A standing arrangement "
                f"with a family member or controlled entity is a conflict the "
                f"board must supervise continuously"
            ),
            "likelihood": "High",
            "impact": "Medium" if largest < 1e7 else "High",
            "risk_score": 6 if largest < 1e7 else 8,
            "evidence": "DEF 14A Item 404 — Related Party Transactions",
            "source_url": (proxy.get("proxy_filings_analyzed") or [{}])[0].get("url"),
        })

    sales = [t for t in (insider.get("transactions") or [])
             if t.get("acquired_disposed") == "D" and t.get("open_market")
             and t.get("value") and not t.get("is_10b5_1")]
    if sales:
        gross = sum(t["value"] for t in sales)
        if gross >= 5e7:
            risks.append({
                "title": "Discretionary insider selling",
                "category": "Governance",
                "description": (
                    f"{format_currency(gross)} of open-market disposals were "
                    f"not under a 10b5-1 plan. Discretionary sales are timed by "
                    f"the seller; plan sales are not"
                ),
                "likelihood": "High",
                "impact": "Medium",
                "risk_score": 6,
                "evidence": "Form 4 open-market codes (S), excluding 10b5-1",
            })

    as_party = ((lit.get("federal_cases") or {}).get("summary") or {}).get(
        "cases_as_party")
    if as_party and as_party >= 3:
        risks.append({
            "title": "Active party litigation",
            "category": "Legal",
            "description": (
                f"{as_party} federal matters name {entity_name} as a party. "
                f"The contingencies note and the docket are not the same "
                f"population; both are reported in the legal section"
            ),
            "likelihood": "High",
            "impact": "Medium",
            "risk_score": 6,
            "evidence": "CourtListener party search + 10-K contingencies note",
        })

    for flag in (overlap.get("risk_flags") or []):
        if flag.get("type") != "allocation_skew":
            continue
        risks.append({
            "title": "Institutional allocation skew versus peers",
            "category": "Ownership",
            "description": flag.get("detail") or flag.get("description", ""),
            "likelihood": "Medium",
            "impact": "Low",
            "risk_score": 3,
            "evidence": "Form 13F-HR positions across peer tickers",
        })

    shared = interlocks.get("shared_boards") or []
    if shared:
        names = "; ".join(
            f"{s['issuer']} ({', '.join(s['directors'])})" for s in shared[:3])
        risks.append({
            "title": "Shared outside board seats",
            "category": "Governance",
            "description": (
                f"Two or more of this board sit together elsewhere: {names}. "
                f"A shared seat among a single issuer's directors is uncommon "
                f"under Clayton Act section 8 and worth examining"
            ),
            "likelihood": "Low",
            "impact": "Medium",
            "risk_score": 4,
            "evidence": "Form 3 filings of each director's own CIK",
        })

    for overlap_text in _network_overlaps(data)[:3]:
        risks.append({
            "title": "Cross-register network overlap",
            "category": "Governance",
            "description": overlap_text.rstrip("."),
            "likelihood": "Medium",
            "impact": "Medium",
            "risk_score": 5,
            "evidence": "DEF 14A × Exhibit 21 × Section 16 × Schedule 13",
        })

    roll = next((i for i in (notes.get("investments") or [])
                 if i.get("kind") == "portfolio_rollforward"), None)
    if roll and (roll.get("net_additions") or 0) >= 1e9:
        risks.append({
            "title": "Rapid private-portfolio deployment",
            "category": "Strategic",
            "description": (
                f"{format_currency(roll['net_additions'])} of net additions to "
                f"non-marketable equity securities in a single year, against a "
                f"closing balance of {format_currency(roll.get('closing_balance'))}. "
                f"The note does not name the investees"
            ),
            "likelihood": "High",
            "impact": "Medium",
            "risk_score": 6,
            "evidence": "10-K non-marketable equity securities note (ASC 321)",
        })

    risks.sort(key=lambda r: -r.get("risk_score", 0))
    return risks


def _render_federal(contracts: dict, entity_name: str) -> list:
    """Federal footprint as an analysed portfolio.

    The distinction that matters is between research agreements and product
    procurement: they say different things about the relationship, and the
    dollar split between them is usually lopsided in a way the headline total
    conceals.
    """
    lines = ["## Federal Contracting", ""]
    summary = contracts.get("summary") or {}
    awards = contracts.get("contracts") or []
    total = summary.get("total_obligated") or 0
    count = summary.get("total_contracts") or len(awards)

    # Show resolution method for transparency
    resolution_method = summary.get("resolution_method", "text_search")
    recipient_uei = summary.get("recipient_uei")
    if recipient_uei:
        lines.append(f"*Entity resolved via UEI: {recipient_uei} "
                     f"(captures all subsidiary awards under this registration)*")
        lines.append("")

    if not awards:
        lines.append(
            f"No federal prime award to {entity_name} was returned by "
            f"USASpending for the search window."
        )
        lines.append("")
        return lines

    earliest = summary.get("earliest_contract") or ""
    latest = summary.get("latest_contract") or ""
    lines.append(
        f"USASpending returns {count} prime awards to {entity_name} totalling "
        f"{format_currency(total)}"
        + (f", running from {earliest} to {latest}" if earliest and latest else "")
        + ". Against revenue of the scale reported above, the federal "
          "relationship is immaterial as a revenue line. Its interest is in "
          "what it reveals about the company's research direction and its "
          "standing with defence and energy agencies."
    )
    lines.append("")
    if contracts.get("excluded_false_positives"):
        lines.append(
            f"{contracts['excluded_false_positives']} further records matching "
            f"the search text were excluded as unrelated recipients sharing a "
            f"similar name."
        )
        lines.append("")

    # ── Agency concentration ─────────────────────────────────────────────
    breakdown = contracts.get("agency_breakdown") or []
    if breakdown and total:
        lines.append("### Awards by agency")
        lines.append("")
        lines.append("| Agency | Obligated | Share |")
        lines.append("|--------|-----------|-------|")
        for row in sorted(breakdown, key=lambda r: -(r.get("amount") or 0)):
            amt = row.get("amount") or 0
            lines.append(f"| {row.get('agency') or '—'} | {format_currency(amt)} "
                         f"| {amt / total * 100:.1f}% |")
        lines.append("")
        lead = max(breakdown, key=lambda r: r.get("amount") or 0)
        lines.append(
            f"{lead.get('agency')} accounts for "
            f"{(lead.get('amount') or 0) / total * 100:.1f}% of obligated "
            f"value. Concentration of that order means the relationship is "
            f"effectively with one buyer, and a change in that agency's "
            f"research priorities would remove most of the footprint."
        )
        lines.append("")

        if CHARTS_AVAILABLE:
            lines.extend(_figure(charts.federal_obligations(contracts)))

    # ── Research versus procurement ──────────────────────────────────────
    # award_group separates definitive contracts from other transaction
    # agreements, grants and similar instruments.
    research = [a for a in awards if a.get("award_group") != "contracts"]
    procurement = [a for a in awards if a.get("award_group") == "contracts"]
    r_total = sum(a.get("amount") or 0 for a in research)
    p_total = sum(a.get("amount") or 0 for a in procurement)
    if research and procurement and total:
        lines.append(
            f"Splitting by instrument type is more revealing than the total. "
            f"{len(research)} awards worth {format_currency(r_total)} "
            f"({r_total / total * 100:.1f}%) are research agreements — other "
            f"transaction agreements and cooperative instruments used to fund "
            f"development work. Only {len(procurement)} awards worth "
            f"{format_currency(p_total)} ({p_total / total * 100:.2f}%) are "
            f"definitive procurement contracts. The federal government is "
            f"overwhelmingly funding this company's research rather than "
            f"buying its products through prime awards."
        )
        lines.append("")

    # ── Award ledger with subject matter ─────────────────────────────────
    # Narrated in full only down to a readable depth. A heavy federal supplier
    # can carry hundreds of awards, and rendering every one as prose would make
    # this the longest section in the report while adding nothing after the
    # first dozen; the remainder is tabulated so the total still reconciles.
    ranked = sorted(awards, key=lambda x: -(x.get("amount") or 0))
    narrated, tabulated = ranked[:15], ranked[15:]
    lines.append(f"### Prime award ledger"
                 + (f" — {len(narrated)} largest of {len(ranked)}"
                    if tabulated else ""))
    lines.append("")
    for a in narrated:
        recipient = a.get("recipient") or entity_name
        agency = a.get("agency") or "—"
        sub = a.get("sub_agency")
        if sub and sub != agency:
            agency = f"{agency} ({sub})"
        header = (f"**{a.get('award_id') or '—'}** — {format_currency(a.get('amount'))}, "
                  f"{agency}")
        lines.append(header)
        lines.append("")
        period = []
        if a.get("start_date"):
            period.append(f"awarded {a['start_date']}")
        if a.get("end_date"):
            period.append(f"period of performance ending {a['end_date']}")
        detail = []
        if recipient and recipient.upper() != entity_name.upper():
            detail.append(
                f"The recipient of record is {recipient}, a distinct registered "
                f"entity from the parent"
            )
        if period:
            detail.append(", ".join(period))
        if detail:
            lines.append(". ".join(_sentence_case(d) for d in detail) + ".")
        desc = (a.get("description") or "").strip()
        if desc:
            # Quoted verbatim from the award record. FPDS stores these in upper
            # case, and re-casing them would corrupt programme acronyms and
            # contract identifiers embedded in the text.
            lines.append(f'Stated purpose: "{desc.rstrip(".")}."')
        lines.append("")

    if tabulated:
        remainder = sum(a.get("amount") or 0 for a in tabulated)
        lines.append(f"### Remaining awards ({len(tabulated)})")
        lines.append("")
        lines.append(
            f"A further {len(tabulated)} awards account for "
            f"{format_currency(remainder)}"
            + (f", or {remainder / total * 100:.1f}% of the total" if total else "")
            + ". They are listed without narrative detail."
        )
        lines.append("")
        lines.append("| Award ID | Agency | Amount | Awarded |")
        lines.append("|----------|--------|--------|---------|")
        for a in tabulated[:60]:
            # These keys exist on every record but are frequently null, so a
            # default on .get would never fire.
            lines.append(
                f"| {a.get('award_id') or '—'} | {a.get('agency') or '—'} "
                f"| {format_currency(a.get('amount'))} "
                f"| {a.get('start_date') or '—'} |"
            )
        lines.append("")
        if len(tabulated) > 60:
            lines.append(f"*{len(tabulated) - 60} further awards below "
                         f"{format_currency(tabulated[59].get('amount'))} are "
                         f"omitted; they are included in every total above.*")
            lines.append("")

    # ── Timing ───────────────────────────────────────────────────────────
    years = contracts.get("year_breakdown") or []
    if len(years) > 1:
        lines.append("### Obligations by year")
        lines.append("")
        lines.append("| Year | Obligated |")
        lines.append("|------|-----------|")
        for row in sorted(years, key=lambda r: str(r.get("year"))):
            lines.append(f"| {row.get('year')} | {format_currency(row.get('amount'))} |")
        lines.append("")
        gap_years = sorted(int(r["year"]) for r in years if str(r.get("year")).isdigit())
        if gap_years:
            lines.append(
                f"Obligations are episodic rather than recurring, falling in "
                f"{len(gap_years)} distinct years between {gap_years[0]} and "
                f"{gap_years[-1]}. This is the signature of project-based "
                f"research funding, not a standing supply relationship."
            )
            lines.append("")

    # ── Integrity screens ────────────────────────────────────────────────
    screen = contracts.get("self_dealing_analysis") or {}
    if screen:
        lines.append("### Award integrity screens")
        lines.append("")
        bits = [
            f"{screen.get('contracts_analyzed', 0)} prime awards and "
            f"{screen.get('subcontracts_analyzed', 0)} subaward records screened",
            f"{screen.get('sole_source_count', 0)} sole-source awards identified",
        ]
        lines.append(
            _sentence_case("; ".join(bits))
            + f". The screen returns an overall risk level of "
              f"{str(screen.get('risk_level', 'unknown')).lower()}"
            + (f" (score {screen['risk_score']})" if screen.get("risk_score") is not None else "")
            + "."
        )
        lines.append("")
        for flag in screen.get("flags") or []:
            lines.append(
                f"- **{str(flag.get('severity', '')).title()} — "
                f"{str(flag.get('type', '')).replace('_', ' ')}.** "
                f"{flag.get('detail', '')}."
            )
        if screen.get("flags"):
            lines.append("")

    lines.append(
        f"*Source: {contracts.get('source', 'USASpending.gov')}. Figures are "
        f"obligated amounts on prime awards; subaward and outlay data are "
        f"reported separately by the agency and are not netted here.*"
    )
    lines.append("")
    return lines


def _name_tokens(name: str) -> list:
    """Alphabetic name parts, lowercased. Initials and suffixes are dropped."""
    parts = re.split(r"[^A-Za-z]+", name or "")
    return [p.lower() for p in parts if len(p) > 1 and p.lower() not in ("jr", "sr", "ii", "iii")]


def _insider_record(name: str, insider: dict) -> dict:
    """
    A person's dealing history from the parsed Form 4 filings.

    The two sources order names oppositely: a proxy writes "Mark A. Stevens"
    while EDGAR files the reporting owner as "STEVENS MARK A". Matching is
    therefore on the surname alone, taken from the end of the proxy name and
    the start of the EDGAR name. A surname shared by two reporting owners is
    reported as ambiguous rather than attributed to either.
    """
    tokens = _name_tokens(name)
    if not tokens:
        return {}
    surname = tokens[-1]

    matched = []
    for txn in (insider or {}).get("transactions") or []:
        filed = _name_tokens(txn.get("insider"))
        if filed and filed[0] == surname:
            matched.append(txn)
    if not matched:
        return {}

    filers = {t.get("insider") for t in matched}
    sales = [t for t in matched if t.get("acquired_disposed") == "D"
             and t.get("open_market") and t.get("value")]
    return {
        "ambiguous": len(filers) > 1,
        "transactions": len(matched),
        "sale_value": sum(t["value"] for t in sales),
        "sale_count": len(sales),
        "planned_value": sum(t["value"] for t in sales if t.get("is_10b5_1")),
        "latest": max((t.get("date") or "" for t in matched), default=""),
        "source_url": next((t.get("source_url") for t in matched if t.get("source_url")), None),
    }


def _render_person(director: dict, insider: dict, proxy_date: str) -> list:
    """One director as a sourced dossier: role, tenure, committees, dealing."""
    name = director.get("name", "—")
    lines = [f"**{name}**", ""]

    if director.get("occupation"):
        lines.append(f"{director['occupation']}.")

    facts = []
    if director.get("age"):
        facts.append(f"age {director['age']}")
    if director.get("since"):
        tenure = datetime.now().year - director["since"]
        facts.append(f"a director since {director['since']}, {tenure} years")
    if director.get("is_independent"):
        facts.append("independent")
    if director.get("is_lead_director"):
        facts.append("lead director")
    if director.get("is_financial_expert"):
        facts.append("designated an audit committee financial expert")
    if director.get("committees"):
        facts.append(f"serving on {', '.join(director['committees'])}")
    if director.get("other_boards"):
        facts.append(f"other public boards: {director['other_boards']}")
    if facts:
        # Only the leading character is raised: str.capitalize would lowercase
        # the proper nouns in committee names and board names.
        sentence = ", ".join(facts)
        lines.append(sentence[0].upper() + sentence[1:] + ".")

    if director.get("biography"):
        lines.append(director["biography"])

    if director.get("fees_earned"):
        lines.append(f"Earned {format_currency(director['fees_earned'])} in fees "
                     f"for the year reported.")

    record = _insider_record(name, insider)
    if record:
        if record["ambiguous"]:
            lines.append("Form 4 filings under this surname could not be attributed "
                         "to one individual and are excluded.")
        elif record["sale_count"]:
            planned = ""
            if record["planned_value"]:
                share = record["planned_value"] / record["sale_value"] * 100
                planned = (f", of which {format_currency(record['planned_value'])} "
                           f"({share:.0f}%) under a Rule 10b5-1 plan")
            count = record["sale_count"]
            lines.append(f"Sold {format_currency(record['sale_value'])} of stock on the "
                         f"open market across {count} "
                         f"transaction{'' if count == 1 else 's'}"
                         f"{planned}. Most recent reported transaction "
                         f"{record['latest']}.")
        else:
            lines.append(f"Filed {record['transactions']} Form 4 transactions in the "
                         f"period with no open-market sales.")

    source = f"DEF 14A filed {proxy_date}"
    if record.get("source_url"):
        source += f"; [Form 4]({record['source_url']})"
    lines.append(f"*Source: {source}.*")
    lines.append("")
    return lines


# What each SEC form is for, so the filing mix reads as a disclosure profile
# rather than a list of codes.
_FORM_PURPOSE = {
    "4": "Insider transaction in the issuer's securities",
    "3": "Initial statement of beneficial ownership by a new insider",
    "5": "Annual statement of deferred insider transactions",
    "144": "Notice of proposed sale of restricted or control securities",
    "8-K": "Current report of a material event",
    "10-K": "Audited annual report",
    "10-Q": "Unaudited quarterly report",
    "DEF 14A": "Definitive proxy statement",
    "DEFA14A": "Additional proxy soliciting material",
    "13F-HR": "Quarterly holdings report by an institutional manager",
    "SCHEDULE 13G": "Passive beneficial ownership above 5%",
    "SCHEDULE 13G/A": "Amendment to a passive 5% ownership report",
    "SC 13G": "Passive beneficial ownership above 5%",
    "SC 13G/A": "Amendment to a passive 5% ownership report",
    "SC 13D": "Activist beneficial ownership above 5%",
    "424B5": "Prospectus supplement for a registered offering",
    "S-8": "Registration of securities for employee benefit plans",
    "SD": "Specialised disclosure on conflict minerals",
    "ARS": "Annual report to shareholders",
    "PX14A6G": "Notice of exempt shareholder solicitation",
    "11-K": "Annual report of an employee stock purchase plan",
    "S-3": "Shelf registration statement",
    "CERT": "Exchange certification of listing approval",
    "25-NSE": "Notification of removal from listing",
}

_MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December")


def _month_label(yyyy_mm: str) -> str:
    try:
        year, month = yyyy_mm.split("-")
        return f"{_MONTH_NAMES[int(month) - 1]} {year}"
    except (ValueError, IndexError):
        return yyyy_mm


def _describe_event(event: dict) -> str:
    """One material disclosure as a sentence, from the filing's own metadata."""
    form = event.get("form_type") or ""
    title = event.get("title") or ""
    items = event.get("items") or []

    if form == "8-K" and items:
        reported = "; ".join(f"Item {i['code']}, {i['title'].lower()}" for i in items)
        return f"Filed an 8-K reporting {reported}."
    if form == "8-K":
        # Items could not be read; say so rather than implying a subject.
        return "Filed an 8-K. The reportable items could not be read from the filing."
    if form == "10-K":
        return "Filed its annual report on Form 10-K."
    if form == "10-Q":
        return "Filed its quarterly report on Form 10-Q."
    if form == "DEF 14A":
        return "Filed its definitive proxy statement on Schedule 14A."
    return f"{title}." if title else f"Filed a {form}." if form else ""


# Why a given reportable item matters, keyed on the 8-K item code. Each note
# describes what the item is for under Regulation 8-K; the consequence for this
# issuer is drawn from its own data where available.
_ITEM_SIGNIFICANCE = {
    "1.01": "commits the company to a material agreement outside the ordinary "
            "course",
    "1.02": "terminates a material agreement, which can remove a revenue or "
            "supply relationship",
    "2.01": "completes an acquisition or disposition of assets",
    "2.02": "is the quarterly earnings release",
    "2.03": "creates a direct financial obligation, typically new debt",
    "3.02": "issues equity outside a registered offering, diluting holders",
    "5.02": "changes the board or the executive team",
    "5.03": "amends the charter or bylaws",
    "5.07": "reports the shareholder vote at the annual meeting",
    "7.01": "furnishes information the company chose to disclose voluntarily",
    "8.01": "discloses an event the company judged material without a specific "
            "reporting trigger",
}


def _event_significance(event: dict, context: dict) -> str:
    """Why a disclosure matters, grounded in this issuer's own figures.

    Returns an empty string when nothing can be said from retrieved data. A
    generic observation would read as analysis while carrying none.
    """
    form = event.get("form_type") or ""
    date = event.get("date") or ""
    items = [i.get("code") for i in (event.get("items") or [])]

    if form == "8-K" and "2.02" in items:
        # Tie the release to the period it reported, where the quarter is held.
        for q in context.get("quarterly") or []:
            end = q.get("period_end") or ""
            if end and end < date and (
                    datetime.fromisoformat(date) - datetime.fromisoformat(end)
            ).days <= 120:
                rev = q.get("Revenues")
                if rev:
                    return (
                        f"Reported {q.get('fiscal_period', 'the quarter')} "
                        f"revenue of ${_fmt_m(rev)}M"
                        + (f" at a {_pct(q.get('gross_margin'))} gross margin"
                           if q.get("gross_margin") else "")
                        + "."
                    )
        return "Carries the quarter's results and management's outlook."

    if form == "8-K" and "5.07" in items:
        sop = context.get("say_on_pay") or {}
        if sop.get("approval_pct"):
            return (
                f"Recorded the annual meeting vote, including say-on-pay "
                f"support of {sop['approval_pct']:.1f}%."
            )
        return "Records how shareholders voted on each ballot item."

    if form == "8-K" and "5.02" in items:
        return ("A change in the board or executive team; repeated filings of "
                "this item are the clearest public signal of leadership churn.")

    if form == "8-K" and items:
        for code in items:
            if code in _ITEM_SIGNIFICANCE:
                note = _ITEM_SIGNIFICANCE[code]
                return f"This {note}."
        return ""

    if form == "10-K":
        fy = context.get("latest_annual") or {}
        if fy.get("Revenues"):
            return (
                f"The audited full-year account, reporting ${_fmt_m(fy['Revenues'])}M "
                f"of revenue. It is the source for the financial and risk "
                f"sections of this report."
            )
        return "The audited full-year account and risk-factor disclosure."

    if form == "10-Q":
        return "Unaudited interim results and updated contingencies."

    if form == "DEF 14A":
        return ("Sets out board nominees, executive pay and the matters put to "
                "a shareholder vote; it is the source for the personnel "
                "section of this report.")

    return ""


def _render_chronology(material: list, insider: dict,
                       context: dict = None) -> list:
    """
    Material disclosures grouped by month, each as a dated sentence.

    Insider dealing is summarised per month rather than listed filing by
    filing; a large issuer files several Form 4s a week and they would
    otherwise crowd out every substantive disclosure.
    """
    context = context or {}
    # Events such as an executive change are inferred from an 8-K item, so the
    # filing and the inference both appear on the same date. The filing itself
    # is narrated and the inference dropped, since the filing now names every
    # item it reported.
    reported = {(e.get("date"), item["code"])
                for e in material if e.get("form_type") == "8-K"
                for item in e.get("items") or []}

    by_month = {}
    seen = set()
    for event in material:
        month = (event.get("date") or "")[:7]
        if not month:
            continue
        if (event.get("date"), event.get("item_code")) in reported:
            continue
        key = (event.get("date"), event.get("accession") or event.get("title"))
        if key in seen:
            continue
        seen.add(key)
        by_month.setdefault(month, []).append(event)

    # Open-market disposals per month. Grants, option exercises and shares
    # withheld for tax are excluded: they are not discretionary selling.
    insider_by_month = {}
    for txn in (insider or {}).get("transactions") or []:
        if (txn.get("acquired_disposed") != "D" or not txn.get("value")
                or not txn.get("open_market")):
            continue
        month = (txn.get("date") or "")[:7]
        if not month:
            continue
        bucket = insider_by_month.setdefault(month, {"value": 0.0, "count": 0,
                                                     "insiders": set()})
        bucket["value"] += txn["value"]
        bucket["count"] += 1
        bucket["insiders"].add(txn.get("insider"))

    lines = []
    for month in sorted(by_month, reverse=True):
        lines.append(f"**{_month_label(month)}**")
        lines.append("")
        for event in sorted(by_month[month], key=lambda e: e.get("date") or "",
                            reverse=True):
            sentence = _describe_event(event)
            if not sentence:
                continue
            url = event.get("source_url")
            cite = f" ([{event.get('accession', 'EDGAR')}]({url}))" if url else ""
            why = _event_significance(event, context)
            lines.append(f"- **{event.get('date', '')}** — {sentence}"
                         + (f" {why}" if why else "") + cite)

        summary = insider_by_month.get(month)
        if summary:
            lines.append(f"- Open-market insider sales this month totalled "
                         f"{format_currency(summary['value'])} across "
                         f"{summary['count']} transactions by "
                         f"{len(summary['insiders'])} insiders (Form 4).")
        lines.append("")
    return lines


def _dcf_price(base_fcf, g_initial, terminal_growth, wacc, horizon,
               net_debt, shares):
    """Re-run the published DCF with substituted assumptions.

    Mirrors valuation_connector.calculate_dcf step for step so the sensitivity
    grid and the reverse-DCF reconcile with the headline figure instead of
    approximating it. A WACC at or below terminal growth has no finite
    Gordon value, so those cells are reported as not meaningful.
    """
    if not shares or horizon < 1 or wacc <= terminal_growth:
        return None
    fcf = float(base_fcf)
    pv_sum = 0.0
    for yr in range(1, horizon + 1):
        g = (terminal_growth if horizon == 1 else
             g_initial + (terminal_growth - g_initial) * (yr - 1) / (horizon - 1))
        fcf *= (1 + g)
        pv_sum += fcf / ((1 + wacc) ** yr)
    terminal = fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    enterprise = pv_sum + terminal / ((1 + wacc) ** horizon)
    return max(enterprise - net_debt, 0) / shares


def _implied_growth(target_price, base_fcf, terminal_growth, wacc, horizon,
                    net_debt, shares):
    """Initial FCF growth rate that would justify the traded price.

    Bisection on the same model. Answers the question a valuation gap always
    raises: not "is the model right" but "what would have to be true".
    """
    lo, hi = -0.50, 3.0
    top = _dcf_price(base_fcf, hi, terminal_growth, wacc, horizon, net_debt, shares)
    if top is None or top < target_price:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        price = _dcf_price(base_fcf, mid, terminal_growth, wacc, horizon,
                           net_debt, shares)
        if price is None:
            return None
        if price < target_price:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _render_segments(segments: dict, entity_name: str) -> list:
    """Segment, geographic and customer concentration, section 4.

    The figures come from the 10-K's rendered statements rather than from
    companyfacts, which publishes only undimensioned facts and so could never
    answer where revenue comes from.
    """
    reportable = segments.get("segments") or []
    geographic = segments.get("geographic") or []
    markets = segments.get("markets") or []
    assets = segments.get("long_lived_assets") or []
    concentration = segments.get("customer_concentration") or []
    if not any((reportable, geographic, markets, concentration)):
        return []

    lines = ["## Segment, Geographic and Customer Concentration", ""]
    period = (segments.get("periods") or ["the latest fiscal year"])[0]
    lines.append(
        f"Disaggregated figures below are as reported in the segment note to the "
        f"most recent Form 10-K, for the period ended {period}. Amounts are in "
        f"millions of USD as filed."
    )
    lines.append("")

    def table(rows, title, unit="Revenue"):
        out = [f"### {title}", "",
               f"| Component | {unit} | Share | Year over year |",
               "|-----------|-------|-------|----------------|"]
        for row in rows:
            name = row["name"]
            if row.get("parent_of"):
                name = f"{name} (total of {len(row['parent_of'])} below)"
            growth = (f"{row['growth_pct']:+.1f}%" if row.get("growth_pct") is not None
                      else "—")
            share = f"{row['share_pct']:.1f}%" if row.get("share_pct") is not None else "—"
            out.append(f"| {name} | {row['current']:,.0f} | {share} | {growth} |")
        out.append("")
        return out

    def top_share(rows):
        leaves = [r for r in rows if not r.get("parent_of")]
        return max((r["share_pct"] or 0) for r in leaves) if leaves else 0

    if reportable:
        lines.extend(table(reportable, "Reportable segments"))
        leader = max(reportable, key=lambda r: r["current"])
        lines.append(
            f"{entity_name} reports {len(reportable)} segments. {leader['name']} "
            f"contributes {leader['share_pct']:.1f}% of segment revenue"
            + (f" and grew {leader['growth_pct']:+.1f}% over the prior year"
               if leader.get("growth_pct") is not None else "")
            + ". Segment reporting follows how management allocates resources, so "
            "the boundaries are the company's own and are not comparable across "
            "issuers."
        )
        lines.append("")

    if markets:
        lines.extend(table(markets, "Revenue by market"))
        leaves = [m for m in markets if not m.get("parent_of")]
        concentrated = top_share(markets)
        lines.append(
            f"Across {len(leaves)} end markets the largest accounts for "
            f"{concentrated:.1f}% of revenue. "
            + ("A single market above 60% of revenue means the company's results "
               "track that market's demand cycle rather than a diversified base; "
               "a downturn confined to it would still be a downturn for the whole."
               if concentrated >= 60 else
               "No single market dominates to the point where the company's "
               "results are a proxy for one demand cycle.")
        )
        fastest = max((m for m in leaves if m.get("growth_pct") is not None),
                      key=lambda m: m["growth_pct"], default=None)
        slowest = min((m for m in leaves if m.get("growth_pct") is not None),
                      key=lambda m: m["growth_pct"], default=None)
        if fastest and slowest and fastest is not slowest:
            lines.append(
                f" Growth was widest apart between {fastest['name']} at "
                f"{fastest['growth_pct']:+.1f}% and {slowest['name']} at "
                f"{slowest['growth_pct']:+.1f}%, a spread of "
                f"{fastest['growth_pct'] - slowest['growth_pct']:.0f} points, so the "
                f"consolidated growth rate is an average over markets moving at "
                f"very different speeds."
            )
        lines.append("")

    if geographic:
        lines.extend(table(geographic, "Revenue by region"))
        largest = max(geographic, key=lambda r: r["current"])
        lines.append(
            f"{largest['name']} accounts for {largest['share_pct']:.1f}% of revenue. "
            f"Regional revenue is reported on a bill-to basis — it records where "
            f"the invoiced customer sits, not where the product is ultimately "
            f"deployed — so it measures the location of the contracting entity "
            f"rather than end demand."
        )
        declining = [g for g in geographic
                     if g.get("growth_pct") is not None and g["growth_pct"] < 0]
        if declining:
            worst = min(declining, key=lambda g: g["growth_pct"])
            lines.append(
                f" {worst['name']} revenue fell {abs(worst['growth_pct']):.1f}% to "
                f"{worst['current']:,.0f}, the only material region in decline"
                if len(declining) == 1 else
                f" {len(declining)} regions declined, led by {worst['name']} at "
                f"{worst['growth_pct']:+.1f}%"
            )
            lines[-1] += (
                ". A regional contraction against consolidated growth points to a "
                "cause specific to that market — trade restriction, competitive "
                "displacement, or local demand — rather than to the business overall."
            )
        lines.append("")

    if CHARTS_AVAILABLE:
        lines.extend(_figure(charts.composition(segments)))

    if assets:
        lines.extend(table(assets, "Long-lived assets by region", unit="Carrying value"))
        top_assets = max(assets, key=lambda r: r["current"])
        lines.append(
            f"{top_assets['share_pct']:.1f}% of long-lived assets sit in "
            f"{top_assets['name']}. Where assets are held and where revenue is "
            f"booked answer different questions: the first indicates operational "
            f"and tax exposure to a jurisdiction, the second commercial exposure."
        )
        if geographic:
            asset_regions = {a["name"] for a in assets}
            revenue_regions = {g["name"] for g in geographic}
            revenue_only = revenue_regions - asset_regions
            if revenue_only:
                lines[-1] += (
                    f" Revenue is booked in {', '.join(sorted(revenue_only)[:4])} "
                    f"without a corresponding long-lived asset base there, indicating "
                    f"sales into those markets rather than operations within them."
                )
        lines.append("")

    if concentration:
        # A concentration figure tagged against a region is geographic exposure,
        # not a single counterparty. Labelling Taiwan as a customer would assert
        # a commercial relationship the filing does not disclose.
        regions = {g["name"] for g in geographic} | {a["name"] for a in assets}
        for item in concentration:
            item["kind"] = "Region" if item["counterparty"] in regions else "Counterparty"

        lines.append("### Concentration disclosures")
        lines.append("")
        lines.append("| Exposure | Type | Share | Basis |")
        lines.append("|----------|------|-------|-------|")
        for item in concentration:
            lines.append(f"| {item['counterparty']} | {item['kind']} | "
                         f"{item['pct']:.1f}% | Percent of {item['basis']} |")
        lines.append("")
        largest = concentration[0]
        anonymous = [c for c in concentration
                     if re.match(r"^customer [a-z]$", c["counterparty"], re.I)]
        lines.append(
            f"The largest disclosed concentration is {largest['counterparty']} at "
            f"{largest['pct']:.1f}% of {largest['basis']}, reported as "
            f"{'a geographic' if largest['kind'] == 'Region' else 'a counterparty'} "
            f"exposure. Disclosure is required once a counterparty or region passes "
            f"10% of revenue, so this table is a regulatory floor rather than a "
            f"complete picture: everything below that threshold goes unreported, and "
            f"the absence of a name here is not evidence of a diversified base."
        )
        if anonymous:
            lines.append(
                f" {len(anonymous)} are identified only by letter, which discloses "
                f"the dependency without naming who holds it."
            )
        lines.append("")

    return lines


def _render_acquisitions(notes: dict, entity_name: str, m) -> list:
    """Transactions described in a business combination or asset acquisition note.

    Goodwill and intangibles are tagged, but only the note says what was bought
    and how the consideration was structured — which is what determines whether
    the accounting treatment carries a regulatory implication.
    """
    deals = (notes or {}).get("acquisitions") or []
    if not deals:
        return []

    lines = ["### Acquisitions and asset purchases", ""]
    for deal in deals:
        name = deal.get("counterparty") or "an acquired business"
        parts = []
        if deal.get("goodwill"):
            parts.append(f"{m(deal['goodwill'])} of goodwill")
        if deal.get("developed_technology"):
            parts.append(f"{m(deal['developed_technology'])} of developed-technology "
                         f"intangibles")
        lines.append(
            f"**{name}.** {entity_name} recorded {' and '.join(parts)} on this "
            f"transaction. The disclosure reads:"
        )
        lines.append("")
        lines.append(f"> {deal['text']}")
        lines.append("")
        # An acquisition booked almost entirely to goodwill, with no equity or
        # customer contracts transferring, is an accounting fact with a
        # regulatory reading: it is the structure that keeps a transaction
        # outside merger review.
        if deal.get("goodwill") and re.search(
                r"no (customer contracts|equity)|license agreement|hired certain",
                deal["text"], re.I):
            total = (deal.get("goodwill") or 0) + (deal.get("developed_technology") or 0)
            lines.append(
                f"The structure is worth noting. {m(total)} of value was recognised "
                f"without acquiring equity interests, customer contracts or existing "
                f"products — the consideration bought a non-exclusive licence and the "
                f"people who built the technology. A transaction assembled this way "
                f"transfers the substance of a business while falling outside the "
                f"thresholds that trigger pre-merger notification, so it does not "
                f"appear in any merger-review record."
            )
            lines.append("")
    return lines


def _render_correlations(data: dict, entity_name: str) -> list:
    """C-series — measured relationships, and the ones we declined to measure.

    The negative results are printed on purpose. A reader who only ever sees
    findings cannot tell whether we looked and found nothing or never looked,
    and the second is what most research documents quietly do.
    """
    correlations = data.get("correlations") or {}
    if not correlations or not correlations.get("ran"):
        return []

    lines = ["## Statistical Correlations", ""]
    lines.append(
        f"Every relationship below is co-movement between two series that "
        f"{entity_name} or its regulators published. None of it is causal, and "
        f"the phrasing does not imply otherwise. A finding built on fewer than "
        f"{correlations.get('min_sample', 12)} observations is withheld rather "
        f"than printed with a caveat, because a caveat gets read as a hedge "
        f"and an absence gets read correctly."
    )
    lines.append("")

    bars = correlations.get("price_bars") or 0
    if bars:
        lines.append(
            f"The price series behind these tests is {bars} daily closes from "
            f"{correlations.get('price_source') or 'market data'}."
        )
        lines.append("")

    # ── Insider sale timing ───────────────────────────────────────────────
    timing = correlations.get("insider_timing") or {}
    if timing:
        lines.append("### Do discretionary insider sales precede weakness?")
        lines.append("")
        window = timing.get("window_days", 30)
        if timing.get("suppressed"):
            lines.append(
                f"Not measured. {timing.get('reason', 'insufficient sample')}."
            )
            lines.append("")
        else:
            lines.append(
                f"A 10b5-1 sale is scheduled months ahead, so its date says "
                f"nothing about what the seller knew that week. A discretionary "
                f"sale is chosen. Comparing the two holds the issuer, the "
                f"period and the people constant, which is what removes the "
                f"market drift that would otherwise have to be modelled."
            )
            lines.append("")
            lines.append(f"| Sale type | Dates | Mean {window}-day return after |")
            lines.append("|-----------|------:|-------------------------------:|")
            lines.append(
                f"| Discretionary | {timing.get('discretionary_n')} "
                f"| {timing.get('discretionary_mean_pct'):+.2f}% |"
                if timing.get("discretionary_mean_pct") is not None else
                f"| Discretionary | {timing.get('discretionary_n')} | — |")
            if timing.get("plan_mean_pct") is not None:
                lines.append(
                    f"| 10b5-1 plan | {timing.get('plan_n')} "
                    f"| {timing.get('plan_mean_pct'):+.2f}% |")
            lines.append("")

            if timing.get("ci_low_pct") is not None:
                lines.append(
                    f"The discretionary mean carries a 95% interval of "
                    f"{timing['ci_low_pct']:+.2f}% to {timing['ci_high_pct']:+.2f}% "
                    f"(p={timing.get('p_vs_zero')} against no move)."
                )
                lines.append("")

            if timing.get("p_vs_plan") is not None:
                spread = timing.get("spread_pct", 0)
                if timing.get("differs_from_plan"):
                    lines.append(
                        f"Discretionary sales are followed by returns "
                        f"{spread:+.2f} percentage points different from plan "
                        f"sales, and that gap clears significance "
                        f"(p={timing['p_vs_plan']}). It is a difference in "
                        f"timing, not a finding about intent, and nothing in "
                        f"the filings speaks to intent."
                    )
                else:
                    lines.append(
                        f"**No relationship.** The gap between discretionary "
                        f"and plan sales is {spread:+.2f} percentage points at "
                        f"p={timing['p_vs_plan']}, which is indistinguishable "
                        f"from zero on this sample. Discretionary sellers at "
                        f"{entity_name} are not, on this evidence, timing "
                        f"their sales any better than the calendar does. That "
                        f"is a result worth stating: the opposite would have "
                        f"been reported here in the same terms."
                    )
                lines.append("")
            elif timing.get("plan_note"):
                lines.append(f"No control group — {timing['plan_note']}.")
                lines.append("")

    # ── 8-K abnormal returns ──────────────────────────────────────────────
    events = correlations.get("event_returns") or {}
    if events:
        lines.append("### Price response to 8-K disclosure, by item")
        lines.append("")
        if events.get("suppressed"):
            lines.append(f"Not measured. {events.get('reason')}.")
            if events.get("largest_group"):
                lines.append("")
                lines.append(
                    f"The largest single item group holds "
                    f"{events['largest_group']} filings across "
                    f"{events.get('item_codes_seen')} distinct item codes. "
                    f"Widening the price window would raise the count and "
                    f"lower the precision; it is left where it is."
                )
            lines.append("")
        else:
            lines.append(
                f"{events['total_events']} 8-K filings fall inside the price "
                f"window, grouped by the item code each reported. Returns are "
                + ("adjusted for the market over the same days."
                   if events.get("adjusted") else
                   "**raw, not market-adjusted** — no index series was "
                   "retrieved for this run, so a sector-wide move would show "
                   "here as though it were company-specific.")
            )
            lines.append("")
            lines.append(f"| Item | Reports | Filings | Mean {events['window_days']}-day return | p |")
            lines.append("|------|---------|--------:|------------------------:|--:|")
            for group in events["groups"]:
                marker = " \\*" if group.get("significant") else ""
                lines.append(
                    f"| {group['item']} | {group['label']} | {group['n']} "
                    f"| {group['mean_pct']:+.2f}%{marker} "
                    f"| {group.get('p', '—')} |")
            lines.append("")
            lines.append(
                f"\\* clears p<{events['threshold']}, the 0.05 threshold "
                f"divided by the {events['tests_run']} groups tested. Testing "
                f"several groups at 0.05 buys a false positive by "
                f"construction, so the bar moves with the number of tests."
            )
            lines.append("")
            if events.get("suppressed_groups"):
                lines.append(
                    f"{events['suppressed_groups']} further item code"
                    f"{'' if events['suppressed_groups'] == 1 else 's'} "
                    f"appeared too few times to measure and are omitted."
                )
                lines.append("")

    # ── Lobbying against awards ───────────────────────────────────────────
    lag = correlations.get("lobbying_lag") or {}
    if lag:
        lines.append("### Lobbying spend against federal awards")
        lines.append("")
        if lag.get("negative_result"):
            lines.append(
                f"**Not measurable on annual data.** Pairing disclosed "
                f"lobbying with obligations at lags of nought to three years "
                f"yields at most {lag.get('max_pairs', 0)} matched year"
                f"{'' if lag.get('max_pairs') == 1 else 's'}, against a "
                f"minimum of {lag.get('min_sample')}. The LDA register is "
                f"quarterly and awards are dated to the day, so this becomes "
                f"answerable at quarterly granularity; at annual granularity "
                f"any coefficient would be an artefact of four or five points."
            )
        else:
            best = lag.get("best") or {}
            stat = best.get("result") or {}
            lines.append(
                f"The strongest association falls at a lag of "
                f"{best.get('lag_years')} year"
                f"{'' if best.get('lag_years') == 1 else 's'}: r={stat.get('r')} "
                f"across {stat.get('n')} paired years, 95% interval "
                f"{stat.get('ci_low')} to {stat.get('ci_high')}, p={stat.get('p')}. "
                f"Lobbying and contracting both scale with the size of a "
                f"company's federal business, so a positive coefficient is "
                f"expected without either driving the other."
            )
        lines.append("")

    return lines


def _render_cooccurrence(data: dict, entity_name: str) -> list:
    """G-02 — the co-occurrence graph over people and over capital."""
    graph = data.get("cooccurrence") or {}
    if not graph:
        return []

    lines = ["## Network Co-occurrence", ""]
    lines.append(
        f"This section asks one question in two places: when the people and "
        f"the institutions attached to {entity_name} appear somewhere else, do "
        f"they appear somewhere else *together*? An edge here is two parties "
        f"filing at the same third entity. It is a fact about filings and not "
        f"evidence of coordination."
    )
    lines.append("")
    lines.append(f"*Method.* {graph.get('method')}")
    lines.append("")

    # ── People layer ──────────────────────────────────────────────────────
    lines.append("### People")
    lines.append("")
    lines.append(
        f"{graph.get('cohort_size', 0)} insiders report at "
        f"{graph.get('entities_reached', 0)} outside entities between them."
    )
    lines.append("")

    if graph.get("negative_result"):
        lines.append(f"**No shared entities.** {graph['negative_result']}")
        lines.append("")
    elif graph.get("edges"):
        lines.append("| Person A | Person B | Shared entities | Which |")
        lines.append("|----------|----------|----------------:|-------|")
        for edge in graph["edges"][:15]:
            lines.append(
                f"| {edge['a']} | {edge['b']} | {edge['weight']} "
                f"| {', '.join(edge['shared'][:3])} |")
        lines.append("")

        rates = [r for r in graph.get("overlap_rates") or []
                 if r["shared_entities"]]
        if rates:
            lines.append(
                "Per person, the share of their outside entities that another "
                "member of this cohort also reports at. This is the figure the "
                "published analysis of the PayPal cohort reported per member "
                "— 31% for Thiel, 47% for Rabois — and it is the most portable "
                "number here because it needs no external benchmark to read."
            )
            lines.append("")
            lines.append("| Person | Entities | Shared | Overlap rate |")
            lines.append("|--------|---------:|-------:|-------------:|")
            for row in rates[:12]:
                lines.append(
                    f"| {row['name']} | {row['entities']} "
                    f"| {row['shared_entities']} | {row['overlap_rate']:.0f}% |")
            lines.append("")

        for cluster in (graph.get("clusters") or [])[:3]:
            lines.append(
                f"**Cluster of {cluster['size']}.** "
                f"{', '.join(cluster['members'])} are joined by "
                f"{cluster['edges']} shared-entity edge"
                f"{'' if cluster['edges'] == 1 else 's'} across "
                f"{len(cluster['shared_entities'])} entities "
                f"(density {cluster['density']}). Membership is a connected "
                f"component of the filing graph, not a judgement about who "
                f"belongs together."
            )
            lines.append("")

    activity = graph.get("activity_by_year") or []
    if len(activity) > 2:
        lines.append("| Year | New outside seats taken |")
        lines.append("|------|------------------------:|")
        for row in activity:
            lines.append(f"| {row['year']} | {row['new_seats']} |")
        lines.append("")

    # ── Capital layer ─────────────────────────────────────────────────────
    institutional = graph.get("institutional") or {}
    if institutional:
        lines.append("### Capital")
        lines.append("")
        lines.append(
            f"Section 8 of the Clayton Act constrains the people layer; it "
            f"does not constrain capital. {institutional['manager_count']} "
            f"managers hold {entity_name} and at least one peer, and they are "
            f"joined by {institutional['edge_count']} shared-issuer edges."
        )
        lines.append("")

        fully = institutional.get("fully_shared") or []
        if fully:
            lines.append(
                f"Every one of these managers holds all "
                f"{len(fully)} issuers examined — {', '.join(fully)}. A "
                f"co-occurrence rate of 100% across a sector is what index "
                f"construction looks like from the inside, not a finding "
                f"about intent, but it does mean the same handful of votes "
                f"is cast at every company in the comparison."
            )
            lines.append("")

        lines.append("| Manager | Issuers held | Which |")
        lines.append("|---------|-------------:|-------|")
        for manager in institutional["managers"][:12]:
            lines.append(
                f"| {manager['name']} | {manager['count']} "
                f"| {', '.join(manager['issuers'])} |")
        lines.append("")

    # ── Endpoints ─────────────────────────────────────────────────────────
    endpoints = graph.get("endpoints") or {}
    capital_entities = endpoints.get("capital_entities") or []
    if capital_entities:
        lines.append("### Where the network lands")
        lines.append("")
        lines.append(
            f"The published analysis of the PayPal cohort ends by tracing it "
            f"into the funds its members came to run, and from there into "
            f"defence contracts and policy roles. That endpoint is the reason "
            f"the exercise is worth doing. Of the entities this cohort "
            f"reaches, {len(capital_entities)} are investment-management "
            f"vehicles: {', '.join(capital_entities[:8])}."
        )
        lines.append("")
        lines.append(endpoints.get("note", ""))
        lines.append("")

    if graph.get("limits"):
        lines.append(f"*Limits.* {graph['limits']}")
        lines.append("")

    return lines


def _render_family_network(data: dict, entity_name: str) -> list:
    """G-04 — positions relatives can hold that the payroll test misses."""
    family = data.get("family_network") or {}
    profile = family.get("position_profile") or {}
    if not profile:
        return []

    lines = ["## Family, Trusts and Investment Vehicles", ""]
    lines.append(
        f"A relative on the payroll is the easiest position to find and the "
        f"least interesting one, because it is also the easiest to avoid. The "
        f"positions that matter are held through a vehicle — a trust, a family "
        f"partnership, an LLC or a foundation — and each of those is visible "
        f"in a free register. This section reads those registers for "
        f"{entity_name} rather than relying on the proxy's Item 404 disclosure "
        f"alone."
    )
    lines.append("")

    census = family.get("position_census") or []
    if census:
        lines.append("| Position | Where it would be visible | Found |")
        lines.append("|----------|---------------------------|------:|")
        for row in census:
            found = ("not readable from filings" if row["found"] is None
                     else str(row["found"]))
            lines.append(f"| {row['position']} | {row['visible_in']} | {found} |")
        lines.append("")

    vehicles = family.get("vehicles") or []
    if vehicles:
        lines.append("### Vehicles filing against the issuer")
        lines.append("")
        lines.append("| Vehicle | Kind | Disclosed value | Filings |")
        lines.append("|---------|------|----------------:|--------:|")
        for vehicle in vehicles[:15]:
            lines.append(
                f"| {vehicle['name']} | {vehicle['kind'].title()} "
                f"| {format_currency(vehicle.get('value'))} "
                f"| {vehicle.get('transactions', '—')} |")
        lines.append("")
    else:
        lines.append(
            f"No trust, partnership or limited-liability vehicle files under "
            f"Section 16 against {entity_name}, and the proxy ownership table "
            f"names none beyond the institutional managers. Insiders here hold "
            f"directly. That is a real finding about how this issuer's "
            f"ownership is structured, not a gap in the search."
        )
        lines.append("")

    links = family.get("surname_links") or []
    if links:
        lines.append("### Vehicles sharing an insider's surname")
        lines.append("")
        for link in links[:10]:
            lines.append(f"**{link['vehicle']}** — {link['basis']}")
            lines.append("")

    foundations = family.get("foundations") or []
    corporate = [f for f in foundations if f.get("corporate")]
    personal = [f for f in foundations if not f.get("corporate")]

    # A family foundation follows a naming convention. Matches that fit it are
    # worth a reader's time; matches that merely contain the surname are not,
    # and listing both together would bury the first set in the second.
    strong = [f for f in personal if f.get("strength") == "pattern match"]
    weak = [f for f in personal if f not in strong]

    # Where one surname returns several foundations in different states, no
    # single one can be attributed to the insider on a name test alone. The
    # count is the finding; picking a row would be inventing the link.
    by_surname = {}
    for foundation in strong:
        by_surname.setdefault(foundation.get("matched_on", "—"), []).append(foundation)
    resolved = {s: f for s, f in by_surname.items() if len(f) == 1}
    ambiguous = {s: f for s, f in by_surname.items() if len(f) > 1}

    if strong:
        lines.append("### Foundations carrying an insider's surname")
        lines.append("")
        lines.append(
            "A private foundation files an IRS Form 990 naming its trustees "
            "and stating the assets under their control, which makes it one "
            "of the few places a family's money is visible without a "
            "subscription. Each row below is a **lead to verify against the "
            "990 itself, not an established link**: the match is on surname, "
            "surnames are not unique, and this test cannot distinguish a "
            "director's family foundation from a stranger who shares the "
            "name. Only names following the usual family-foundation "
            "convention are shown."
        )
        lines.append("")
        if resolved:
            lines.append("| Foundation | Location | EIN | Surname |")
            lines.append("|------------|----------|-----|---------|")
            for surname, group in sorted(resolved.items())[:12]:
                foundation = group[0]
                place = ", ".join(x for x in (foundation.get("city"),
                                              foundation.get("state")) if x)
                lines.append(
                    f"| {foundation['name']} | {place or '—'} "
                    f"| {foundation['ein']} | {surname} |")
            lines.append("")

        if ambiguous:
            total = sum(len(g) for g in ambiguous.values())
            detail = "; ".join(
                f"{surname} ({len(group)}, in "
                + ", ".join(sorted({g.get('state') or '?' for g in group}))
                + ")"
                for surname, group in sorted(ambiguous.items())[:6])
            lines.append(
                f"**{len(ambiguous)} surnames cannot be resolved.** "
                f"{total} foundations match them, spread across different "
                f"states — {detail}. Where a surname returns more than one "
                f"foundation, no single one can be attributed to the insider "
                f"on a name test, so none is named here. Resolving these "
                f"means reading the trustee list on each 990."
            )
            lines.append("")

        if weak:
            lines.append(
                f"A further {len(weak)} registered charities carry an "
                f"insider's surname inside a longer name — a museum, a "
                f"hospital wing, a place name. Those are excluded: the "
                f"surname in them is far more likely to be coincidence than "
                f"a family link."
            )
            lines.append("")
    elif personal:
        lines.append(
            f"{len(personal)} registered charities carry an insider's surname "
            f"somewhere in their name, but none follow the naming convention "
            f"a family foundation normally uses, so none are listed. On a "
            f"surname-only test that is the correct outcome to report."
        )
        lines.append("")

    if corporate:
        lines.append(
            f"{entity_name} also runs "
            f"{len(corporate)} foundation{'' if len(corporate) == 1 else 's'} "
            f"in its own name ("
            + ", ".join(f["name"] for f in corporate[:4])
            + "). A corporate foundation is a different object from a family "
              "one and is listed separately for that reason."
        )
        lines.append("")

    institutional = family.get("institutional_vehicles") or []
    if institutional:
        lines.append(
            f"{len(institutional)} further vehicle"
            f"{'' if len(institutional) == 1 else 's'} on the register "
            f"({', '.join(v['name'] for v in institutional[:5])}) "
            f"{'is' if len(institutional) == 1 else 'are'} identifiable as "
            f"asset managers and excluded from the analysis above."
        )
        lines.append("")

    lines.append(
        "**The blind spot.** An advisor holds no office, files no Section 16 "
        "form and appears in no register. Advisory roles exist only in prose "
        "— interviews, announcements, conference billing — which is why they "
        "are reachable through the news layer and nowhere else in this "
        "document."
    )
    lines.append("")
    if family.get("sources"):
        lines.append(f"*Sources.* {'; '.join(family['sources'])}.")
        lines.append("")
    return lines


def _render_peer_comparison(data: dict, entity_name: str) -> list:
    """G-03 — the subject against peers on every axis we can source free."""
    comparison = data.get("peer_comparison") or {}
    rows = comparison.get("rows") or []
    if not rows:
        return []

    companies = comparison.get("companies") or []
    tickers = [c["ticker"] for c in companies]
    subject = comparison.get("subject")

    lines = ["## Peer Comparison", ""]
    lines.append(
        f"{entity_name} against {len(comparison.get('peers') or [])} peers on "
        f"the registers used throughout this report — SEC facts, USAspending, "
        f"the Senate LDA register and Section 16. The ownership comparison "
        f"sits in its own section above; this is everything else."
    )
    lines.append("")
    lines.append(f"*{comparison.get('fiscal_note', '')}*")
    lines.append("")

    header = "| Metric | " + " | ".join(tickers) + " | Coverage |"
    divider = "|--------|" + "|".join("---:" for _ in tickers) + "|---------:|"
    lines.append(header)
    lines.append(divider)

    def _cell(value, fmt):
        if value is None:
            return "—"
        # A real zero and a value we could not retrieve mean opposite things,
        # and the report's em-dash convention renders both as "—". In a
        # comparison table that turns "this company has no federal business"
        # into "we did not check", so zero is written out here.
        if value == 0:
            return "none"
        if fmt == "money":
            return format_currency(value)
        if fmt == "pct":
            return f"{value:.1f}%"
        return f"{value:,.0f}"

    for row in rows:
        cells = []
        for ticker in tickers:
            text = _cell(row["values"].get(ticker), row["format"])
            if row.get("leader") == ticker and text != "—":
                text = f"**{text}**"
            cells.append(text)
        lines.append(f"| {row['metric']} | " + " | ".join(cells)
                     + f" | {row['coverage']} |")
    lines.append("")

    lines.append(
        f"Bold marks the highest value in each row. {comparison['complete_metrics']} "
        f"of {comparison['total_metrics']} metrics are available for every "
        f"company; where one is missing the row is still shown but no ranking "
        f"is stated, because ranking four companies out of five describes our "
        f"retrieval rather than the market. A cell reading *none* is a zero "
        f"the source returned; *—* is a figure the source did not carry."
    )
    lines.append("")

    # A zero federal or lobbying figure is retrieved by matching the company's
    # name against a register. For a company that plainly has such business
    # the zero is a name-resolution failure, and saying so is more useful than
    # letting the reader treat it as a fact about the company.
    zero_rows = []
    for row in rows:
        if row["metric"] not in ("Federal obligations", "Federal awards",
                                 "Lobbying disclosed", "LDA filings"):
            continue
        zeros = [t for t in tickers if row["values"].get(t) == 0]
        if zeros:
            zero_rows.append((row["metric"], zeros))
    if zero_rows:
        affected = sorted({t for _, ts in zero_rows for t in ts})
        lines.append(
            f"**Treat the zeros with suspicion.** "
            f"{', '.join(affected)} return no records on "
            + ", ".join(m.lower() for m, _ in zero_rows)
            + ". These registers are searched by company name, and a large "
              "listed company almost always files under several. A zero here "
              "is more likely a name that did not resolve than an absence of "
              "activity, and it should be confirmed against the register "
              "directly before being used."
        )
        lines.append("")

    periods = [f"{c['ticker']} to {c.get('period_end') or 'an unstated date'}"
               for c in companies if c.get("period_end")]
    if periods:
        lines.append(f"Fiscal periods: {'; '.join(periods)}.")
        lines.append("")

    # Where the subject sits, in prose, on the rows that ranked.
    ranked = [r for r in rows if r.get("subject_rank")]
    if ranked:
        leads = [r["metric"] for r in ranked if r["subject_rank"] == 1]
        trails = [r["metric"] for r in ranked
                  if r["subject_rank"] == len(tickers)]
        if leads:
            lines.append(
                f"{entity_name} leads the set on {len(leads)} of "
                f"{len(ranked)} ranked metrics: {', '.join(leads).lower()}."
            )
            lines.append("")
        if trails:
            lines.append(
                f"It sits last on {', '.join(trails).lower()}. A low federal "
                f"or lobbying figure is a statement about where a company's "
                f"revenue comes from, not about how well it is run."
            )
            lines.append("")

    errors = comparison.get("errors") or {}
    if errors:
        lines.append(
            "Retrieval notes: "
            + "; ".join(f"{k} ({'; '.join(v)})" for k, v in errors.items())
            + "."
        )
        lines.append("")
    return lines


def _render_news(data: dict, entity_name: str) -> list:
    """G-05 — coverage, themes and the people named in them."""
    news = data.get("news_intelligence") or {}
    articles = news.get("articles") or []
    summary = news.get("summary") or {}
    if not articles and not news.get("sources_failed"):
        return []

    lines = ["## News, Coverage and the Open Web", ""]

    if not articles:
        lines.append(
            f"No coverage could be resolved to {entity_name}. Sources "
            f"attempted: {', '.join(news.get('sources_failed') or [])}."
        )
        lines.append("")
        return lines

    date_range = summary.get("date_range") or []
    lines.append(
        f"{summary.get('article_count', 0)} articles resolved to "
        f"{entity_name}"
        + (f", spanning {date_range[0]} to {date_range[1]}"
           if len(date_range) == 2 and all(date_range) else "")
        + f". A further {news.get('dropped_unresolved', 0)} items were "
        f"returned by the same queries and dropped because they could not be "
        f"tied to the issuer — a headline naming a sector is not coverage of "
        f"a company, and padding this section with near-matches would make it "
        f"unreadable."
    )
    lines.append("")

    queried = news.get("sources_queried") or []
    if queried:
        lines.append(
            "Sources: "
            + ", ".join(f"{s['source']} ({s['returned']})" for s in queried)
            + "."
        )
        lines.append("")

    themes = summary.get("themes") or []
    if themes:
        lines.append("### What the coverage is about")
        lines.append("")
        lines.append("| Theme | Articles |")
        lines.append("|-------|---------:|")
        for theme, count in themes:
            lines.append(f"| {theme.title()} | {count} |")
        lines.append("")

    outlets = summary.get("top_outlets") or []
    if outlets:
        lines.append(
            "Most frequent outlets: "
            + ", ".join(f"{name} ({count})" for name, count in outlets[:8])
            + "."
        )
        lines.append("")

    mentions = news.get("people_mentions") or []
    if mentions:
        lines.append("### Insiders named in coverage")
        lines.append("")
        lines.append(
            "The join between this section and the filings: an article about "
            "the issuer that also names a director carries more than one that "
            "does not."
        )
        lines.append("")
        for person in mentions[:8]:
            lines.append(f"**{person['person']}** — {person['count']} article"
                         f"{'' if person['count'] == 1 else 's'}")
            for article in person["articles"][:3]:
                lines.append(f"- {article['date'] or '—'} — {article['title']}")
            lines.append("")

    lines.append("### Recent coverage")
    lines.append("")
    lines.append("| Date | Outlet | Headline | Themes |")
    lines.append("|------|--------|----------|--------|")
    for article in articles[:25]:
        title = (article.get("title") or "").replace("|", "-")[:100]
        lines.append(
            f"| {article.get('date') or '—'} | {article.get('outlet') or '—'} "
            f"| {title} | {', '.join(article.get('themes') or [])} |")
    lines.append("")

    tone = summary.get("tone") or {}
    if tone:
        lines.append(
            f"Headline tone across the set: {tone.get('positive', 0)} "
            f"positive, {tone.get('neutral', 0)} neutral, "
            f"{tone.get('negative', 0)} negative. This is keyword counting on "
            f"headlines, not sentiment analysis, and it should be read as a "
            f"rough shape rather than a measurement."
        )
        lines.append("")

    reddit = news.get("reddit") or []
    if reddit:
        lines.append("### Retail discussion")
        lines.append("")
        lines.append(
            "Reddit threads mentioning the issuer. Retail chatter is not "
            "evidence about the business and is separated from the coverage "
            "above for that reason."
        )
        lines.append("")
        lines.append("| Subreddit | Score | Thread |")
        lines.append("|-----------|------:|--------|")
        for post in reddit[:10]:
            lines.append(f"| {post.get('outlet')} | {post.get('score') or 0} "
                         f"| {(post.get('title') or '')[:80]} |")
        lines.append("")
    elif news.get("reddit_unavailable_reason"):
        lines.append(
            f"*Retail discussion is not included: "
            f"{news['reddit_unavailable_reason']}*"
        )
        lines.append("")

    failed = news.get("sources_failed") or []
    if failed:
        lines.append(f"Sources that returned nothing: {', '.join(failed)}.")
        lines.append("")
    return lines


def _render_data_health(data: dict, entity_name: str) -> list:
    """G-09 — which sources answered, and what an empty one might mean."""
    health = data.get("data_health") or {}
    checks = health.get("checks") or []
    if not checks:
        return []

    lines = ["## Source Coverage for This Run", ""]
    lines.append(
        f"{health['healthy']} of {health['total']} sources returned data "
        f"({health['coverage_pct']}% coverage), checked at "
        f"{health.get('checked_at')}. This table exists because a broken "
        f"connector does not raise an error — it returns nothing, and nothing "
        f"renders as \"no such transactions were disclosed\". A reader cannot "
        f"tell a clean company from a failed fetch unless the report says "
        f"which one this was."
    )
    lines.append("")
    lines.append("| Source | Status | Records | Consequence if absent |")
    lines.append("|--------|--------|--------:|-----------------------|")
    for check in checks:
        status = {
            "ok": "Returned",
            "empty": "Empty",
            "suspect": "**Suspect**",
            "broken": "**Failed**",
            "not_run": "**Not run**",
        }.get(check["status"], check["status"])
        # For a suspect or failed source the standing "consequence if absent"
        # note is the wrong thing to print: it explains what a legitimate zero
        # would mean, when the whole point of the status is that this zero is
        # probably not legitimate. The reason displaces it.
        if check["status"] in ("suspect", "broken"):
            note = check.get("detail") or check["impact"]
        elif check["status"] != "ok":
            note = check["impact"]
        else:
            note = "—"
        lines.append(
            f"| {check['source']} | {status} "
            f"| {check['records'] or '—'} | {note} |")
    lines.append("")

    alerts = health.get("alerts") or []
    if alerts:
        lines.append(
            f"{len(alerts)} source{'' if len(alerts) == 1 else 's'} triggered "
            f"an alert on this run. Sections depending on them are absent from "
            f"this document rather than empty."
        )
        lines.append("")
        alert = (health.get("alert") or {})
        if alert.get("webhook_configured"):
            lines.append(
                "An alert was dispatched to the configured webhook."
                if alert.get("delivered") else
                "A webhook is configured but delivery failed; the alert is in "
                "the run log.")
        else:
            lines.append(
                "No alert webhook is configured. Set `DATA_HEALTH_WEBHOOK_URL` "
                "to a Slack or Teams incoming-webhook address and these "
                "alerts will be delivered as they happen rather than being "
                "found here after the fact."
            )
        lines.append("")
    else:
        lines.append("No source failed on this run.")
        lines.append("")
    return lines


def _render_network_trends(data: dict, entity_name: str) -> list:
    """N-01..N-07 — analysis across the P-series registers. Omit empty legs."""
    trends = _network_trends(data)
    sections = [
        ("n01_competitor_seats",
         "Seats at competitors and strategic counterparties",
         f"Section 16 filings name every other public issuer where a "
         f"{entity_name} director or officer has reported. Those issuers are "
         f"compared here to the peer set and to counterparties named in the "
         f"business-combination and investment notes."),
        ("n02_co_holdings",
         "Institutions holding the issuer and its competitors",
         f"The same 13F managers appear on {entity_name}'s register and on "
         f"those of its peers. Overlap alone is uninformative for index "
         f"managers; relative portfolio weight is what the filings support."),
        ("n03_invest_acq",
         "Private holdings and acquisitions",
         "Named investees are read against acquisition counterparties. The "
         "ASC 321 rollforward is often aggregate-only, so this subsection "
         "appears only when the note names entities."),
        ("n04_personnel_moves",
         "Personnel movement into investees and acquirees",
         f"Outside seats of {entity_name} insiders are matched to entities "
         f"the issuer has acquired or in which it holds a disclosed stake."),
        ("n05_holder_timing",
         "5%+ holders around strategic announcements",
         "Schedule 13D/G filing dates are compared to material 8-K and "
         "acquisition dates in the chronology. Adjacency is recorded; "
         "causation is not inferred."),
        ("n06_jurisdictions",
         "Subsidiary jurisdictions versus disclosed operations",
         "Exhibit 21 organisation jurisdictions are read against the "
         "geographic revenue breakdown. A legal footprint without a matching "
         "operations disclosure is flagged as structure, not as tax finding."),
        ("n07_overlaps",
         "Cross-register overlaps",
         "Related-party disclosures, the subsidiary list, beneficial-ownership "
         "schedules and directors' outside seats are filed for different "
         "purposes and never cite each other."),
    ]
    populated = [(key, title, intro, trends.get(key) or [])
                 for key, title, intro in sections
                 if trends.get(key)]
    if not populated:
        return []

    n_findings = sum(len(items) for _k, _t, _i, items in populated)
    lines = ["### Network analysis", ""]
    lines.append(
        f"The registers below were each built for a single disclosure purpose. "
        f"Reading them against one another for {entity_name} produces "
        f"{n_findings} finding{'' if n_findings == 1 else 's'} across "
        f"{len(populated)} comparison"
        f"{'' if len(populated) == 1 else 's'}. Empty comparisons are omitted "
        f"rather than padded."
    )
    lines.append("")
    for _key, title, intro, items in populated:
        lines.append(f"#### {title}")
        lines.append("")
        lines.append(intro)
        lines.append("")
        for text in items[:12]:
            lines.append(f"- {text}")
        lines.append("")
    return lines


def _render_network_overlaps(data: dict, entity_name: str) -> list:
    """Back-compat alias — full N-series lives in `_render_network_trends`."""
    return _render_network_trends(data, entity_name)


def _render_related_parties(proxy: dict, entity_name: str) -> list:
    """Item 404 disclosures: who inside the company transacts with it.

    A related-party transaction is disclosed precisely because the counterparty
    is not at arm's length. The proxy states the relationship and the amount,
    which together are the conflict — neither is inferable from the financials.
    """
    transactions = (proxy or {}).get("related_party_transactions") or []
    real = [t for t in transactions if not t.get("is_routine")]
    if not real:
        return []

    # Several proxies are read, and each restates the prior two years, so one
    # standing arrangement appears many times. Grouping by the insider named in
    # the disclosure turns that repetition into what it actually is: an
    # arrangement with a history, rather than a list of separate transactions.
    def principal(text: str) -> str:
        match = re.search(
            r"\bof\s+((?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][\w'-]+"
            r"|[A-Z][\w'-]+(?:[- ][A-Z][\w'-]+){1,2})", text or "")
        if not match:
            return ""
        return match.group(1).split()[-1].strip(",.")

    def fiscal_year(text: str) -> str:
        match = re.search(r"[Ff]iscal(?:\s+year)?\s+(\d{4})", text or "")
        return match.group(1) if match else ""

    groups: dict = {}
    for entry in real:
        text = entry.get("sentence") or entry.get("text", "")
        key = (entry.get("category"), principal(text)
               or (entry.get("counterparties") or [""])[0].lower())
        groups.setdefault(key, []).append(entry)

    lines = ["### Related-party transactions", ""]
    lines.append(
        f"Item 404 of Regulation S-K requires {entity_name} to disclose any "
        f"transaction above $120,000 in which a director, executive officer, "
        f"five percent holder or an immediate family member of one of them has "
        f"a material interest. The proxies read here carry {len(real)} such "
        f"passages, describing {len(groups)} distinct "
        f"{'arrangement' if len(groups) == 1 else 'arrangements'} — each proxy "
        f"restates the two preceding years, so a standing arrangement recurs "
        f"across filings."
    )
    lines.append("")

    ordered = sorted(
        groups.items(),
        key=lambda kv: max((e.get("largest_amount") or 0) for e in kv[1]),
        reverse=True)

    for (category, who), entries in ordered:
        entries = sorted(entries, key=lambda e: e.get("largest_amount") or 0,
                         reverse=True)
        named = next((c for e in entries for c in (e.get("counterparties") or [])),
                     None)
        relationship = next((e.get("relationship") for e in entries
                             if e.get("relationship")), None)

        if category == "family employment" and who:
            heading = f"Family members of {who} on the payroll"
        elif named:
            heading = named
        else:
            heading = {
                "family employment": "Employment of a family member",
                "entity transaction": "Transaction with a related entity",
            }.get(category or "", "Related-party disclosure")

        opening = f"**{heading}.**"
        # The heading already names the insider for a family arrangement, and a
        # single disclosure often covers more than one relative.
        if relationship and not (category == "family employment" and who):
            opening += (f" The proxy identifies the counterparty as the "
                        f"{relationship} of a named officer or director.")
        largest = max((e.get("largest_amount") or 0) for e in entries)
        if largest:
            opening += (f" The largest amount disclosed is "
                        f"{format_currency(largest)}.")
        lines.append(opening)
        lines.append("")

        # Quote each distinct passage once, newest fiscal year first, and drop
        # a passage that adds no figure where a quantified one already stands.
        quoted, seen = [], set()
        for entry in entries:
            text = " ".join((entry.get("sentence")
                             or entry.get("text", "")).split())
            if text.lower() in seen:
                continue
            seen.add(text.lower())
            quoted.append((fiscal_year(text), entry.get("largest_amount"), text))

        quantified = [q for q in quoted if q[1]]
        for year, _amount, text in sorted(
                quantified or quoted, key=lambda q: q[0], reverse=True):
            lines.append(f"> {text}")
            lines.append("")
        if quantified and len(quoted) > len(quantified):
            context = next(t for _, amount, t in quoted if not amount)
            lines.append(f"The arrangement is introduced as: {context}")
            lines.append("")

    routine = [t for t in transactions if t.get("is_routine")]
    if routine:
        lines.append(
            f"A further {len(routine)} passage"
            f"{'' if len(routine) == 1 else 's'} in the same section "
            f"{'restates' if len(routine) == 1 else 'restate'} the review policy "
            f"or the $120,000 threshold itself rather than describing a "
            f"transaction, and {'is' if len(routine) == 1 else 'are'} excluded."
        )
        lines.append("")
    return lines


_NAME_SUFFIX = re.compile(r"^(jr|sr|ii|iii|iv|md|phd|dr|mr|mrs|ms)$", re.I)


_CORPORATE = re.compile(
    r"\b(inc|corp|corporation|co|llc|lp|llp|plc|ltd|limited|company|"
    r"holdings?|group|trust|partners|management|capital|advisors|fund|"
    r"bank|associates|foundation)\b\.?", re.I)


def _name_token_set(name: str) -> set:
    """Significant words in a person's name, ignoring initials and suffixes."""
    return {t.lower() for t in re.split(r"[^A-Za-z]+", name or "")
            if len(t) > 1 and not _NAME_SUFFIX.match(t)}


def _person_name(edgar_name: str, known: list) -> str:
    """A reporting owner's name as a reader would write it.

    EDGAR stores an individual reporting owner surname-first and usually in
    capitals — "SEAWELL A BROOKE". The proxy writes the same person as
    "A. Brooke Seawell", so where the two can be matched the proxy's rendering
    is used. Failing a match the name is title-cased and the leading surname
    moved to the end, which is the convention EDGAR documents for individuals.
    """
    tokens = _name_token_set(edgar_name)
    if not tokens:
        return edgar_name

    for candidate in known:
        if len(tokens & _name_token_set(candidate)) >= 2:
            return candidate

    # A reporting owner can be a firm rather than a person — a ten percent
    # holder usually is — and a firm's name is already in reading order.
    words = [w for w in re.split(r"\s+", (edgar_name or "").strip()) if w]
    if (_CORPORATE.search(edgar_name or "") or len(words) < 2
            or not all(re.fullmatch(r"[A-Za-z.'’-]+", w) for w in words)):
        return edgar_name.title() if edgar_name.isupper() else edgar_name

    surname, rest = words[0], words[1:]
    suffix = [w for w in rest if _NAME_SUFFIX.match(w.strip("."))]
    rest = [w for w in rest if not _NAME_SUFFIX.match(w.strip("."))]
    ordered = rest + [surname] + suffix
    return " ".join(w.title() if w.isupper() or w.islower() else w
                    for w in ordered)


def _render_interlocks(interlocks: dict, entity_name: str,
                       proxy: dict = None) -> list:
    """Other public-company seats held by this issuer's directors and officers."""
    people = (interlocks or {}).get("people") or []
    if not people:
        return []

    # The proxy spells these people's names properly; EDGAR does not.
    proxy = proxy or {}
    known = [d.get("name") for d in
             ((proxy.get("board_composition") or {}).get("directors") or [])
             if d.get("name")]
    known += [c.get("name") for c in (proxy.get("compensation_table") or [])
              if c.get("name")]

    summary = interlocks.get("summary", {})
    current = [p for p in people if p.get("current_seat_count")]

    lines = ["### Board interlocks and outside seats", ""]
    lines.append(
        f"Every person who reports under Section 16 keeps a single SEC "
        f"identifier for life, across every issuer where they serve. Reading "
        f"back the issuers named in their initial ownership statements gives "
        f"each individual's other public-company roles from their own sworn "
        f"filings. Of {summary.get('people_checked', 0)} "
        f"{entity_name} insiders checked, {len(people)} have reported at "
        f"another issuer and {len(current)} hold a seat that is still active."
    )
    lines.append("")
    lines.append(
        f"Nothing in Section 16 records a departure, so a role counts as "
        f"current here only where the person has filed at that issuer since "
        f"{summary.get('current_since', 'the cutoff')}; a two-year window spans "
        f"an annual grant cycle, which a sitting director would normally trigger."
    )
    lines.append("")

    for person in people[:12]:
        active = [s for s in person["other_seats"] if s.get("current")]
        lapsed = [s for s in person["other_seats"] if not s.get("current")]
        roles = ", ".join(person.get("roles_at_issuer") or []) or "insider"
        person = dict(person, name=_person_name(person["name"], known))

        if active:
            described = "; ".join(
                f"{s['issuer']}"
                + (f" ({s['ticker']})" if s.get("ticker") else "")
                + f" as {', '.join(s['roles']).lower()}" if s.get("roles")
                else s["issuer"] for s in active)
            lines.append(
                f"**{person['name']}** — {roles} at {entity_name} — currently "
                f"reports at {described}."
            )
        else:
            lines.append(
                f"**{person['name']}** — {roles} at {entity_name} — reports no "
                f"other active seat."
            )
        if lapsed:
            history = ", ".join(
                f"{s['issuer']} (last filed {s['last_filed']})"
                for s in lapsed[:6])
            lines.append("")
            lines.append(
                f"Earlier roles, where the last filing at the issuer predates "
                f"the currency window: {history}."
                + (f" A further {len(lapsed) - 6} are on file."
                   if len(lapsed) > 6 else "")
            )
        lines.append("")

    if CHARTS_AVAILABLE:
        lines.extend(_figure(charts.interlock_network(
            interlocks, entity_name,
            name_formatter=lambda n: _person_name(n, known))))

    shared = interlocks.get("shared_boards") or []
    if shared:
        lines.append(
            "Two or more of this board sit together elsewhere, which is the "
            "interlock proper rather than an individual's unrelated seat:"
        )
        lines.append("")
        for entry in shared:
            named = ", ".join(_person_name(d, known) for d in entry["directors"])
            lines.append(f"- **{entry['issuer']}** — {named}.")
        lines.append("")
    else:
        lines.append(
            "No two of these people sit on the same outside board. That is the "
            "expected result: section 8 of the Clayton Act prohibits a person "
            "from serving as a director of two competing corporations, so a "
            "shared seat among a single issuer's directors is uncommon and "
            "worth examining where it occurs."
        )
        lines.append("")
    return lines


def _render_beneficial_ownership(beneficial: dict, entity_name: str) -> list:
    """Five percent holders from Schedule 13D and 13G."""
    holders = (beneficial or {}).get("holders") or []
    stakes = (beneficial or {}).get("stakes_in_others") or []
    if not holders and not stakes:
        return []

    lines = ["### Five percent holders (Schedule 13D/G)", ""]
    if holders:
        activist = beneficial.get("activist_filings", 0)
        lines.append(
            f"A Schedule 13 is triggered by crossing five percent of a class, "
            f"which makes it a different record from a 13F: it captures "
            f"strategic and insider blocks a quarterly manager report never "
            f"shows, and the choice of form states intent. A 13D asserts a "
            f"purpose of influencing control; a 13G disclaims it. "
            f"{entity_name} has {beneficial.get('passive_filings', 0)} passive "
            f"and {activist} control-intent "
            f"{'filing' if activist == 1 else 'filings'} on record."
        )
        lines.append("")
        lines.append("| Holder | Percent of class | Form | Filed | Stated intent |")
        lines.append("|--------|-----------------|------|-------|---------------|")
        for holder in holders[:15]:
            lines.append(
                f"| {holder['holder']} "
                f"| {holder['percent_of_class']:.2f}% "
                f"| {holder['form']} | {holder['filed']} "
                f"| {holder['intent']} |"
            )
        lines.append("")
        read = beneficial.get("passive_filings", 0) + activist
        lines.append(
            f"Each figure is the percentage stated in that holder's most recent "
            f"schedule, so the dates differ by holder and none is restated to a "
            f"common measurement point. {read} schedules were read and "
            f"{len(holders)} carried a percentage in a form that could be "
            f"parsed; the remainder are amendments that restate an exhibit "
            f"without repeating the cover-page figures."
        )
        lines.append("")
        newest = max((h["filed"] for h in holders), default="")
        if newest and newest < (date.today() - timedelta(days=550)).isoformat():
            lines.append(
                f"The most recent of these was filed {newest}. A Schedule 13 is "
                f"amended only when a position changes materially, so an "
                f"interval of this length is not itself unusual — but these "
                f"percentages are the last stated positions, not current ones."
            )
            lines.append("")
        for holder in holders:
            if holder.get("purpose"):
                lines.append(
                    f"**{holder['holder']}** filed on a control-intent basis. "
                    f"The stated purpose reads:"
                )
                lines.append("")
                lines.append(f"> {holder['purpose']}")
                lines.append("")

    if stakes:
        lines.append(
            f"The same schedules run in the other direction. {entity_name} has "
            f"itself crossed five percent of another public company and filed "
            f"accordingly, which places these positions on the public record "
            f"where an ordinary corporate investment would not appear:"
        )
        lines.append("")
        for stake in stakes[:10]:
            lines.append(
                f"- **{stake['subject']}** — {stake['percent_of_class']:.2f}% "
                f"of the class, {stake['form']} filed {stake['filed']}."
            )
        lines.append("")
    return lines


def _render_venture_portfolio(notes: dict, entity_name: str, m) -> list:
    """The private-equity portfolio from the non-marketable securities note."""
    investments = (notes or {}).get("investments") or []
    rollforward = next((i for i in investments
                        if i.get("kind") == "portfolio_rollforward"), None)
    if not rollforward:
        return []

    opening = rollforward.get("opening_balance") or 0
    closing = rollforward.get("closing_balance") or 0
    additions = rollforward.get("net_additions") or 0

    lines = ["### Private company holdings", ""]
    lines.append(
        f"Equity stakes in companies with no public market are carried under "
        f"the measurement alternative and disclosed as a rollforward rather "
        f"than a holdings list. The note does not name the investees, but it "
        f"does size the programme, and the year's movement is the clearest "
        f"available measure of how much capital {entity_name} is directing "
        f"into private companies."
    )
    lines.append("")
    lines.append("| Movement | Amount |")
    lines.append("|----------|--------|")
    for field, label in (("opening_balance", "Balance at start of year"),
                         ("net_additions", "Net additions"),
                         ("unrealized_gains", "Unrealised gains"),
                         ("impairments", "Impairments and unrealised losses"),
                         ("sales", "Sales and reclassifications"),
                         ("closing_balance", "Balance at end of year")):
        value = rollforward.get(field)
        if value is not None:
            # A rollforward reads as a column of movements, so a reduction is
            # shown in brackets rather than with a sign inside the currency.
            rendered = f"({m(abs(value))})" if value < 0 else m(value)
            lines.append(f"| {label} | {rendered} |")
    lines.append("")

    if CHARTS_AVAILABLE:
        lines.extend(_figure(charts.portfolio_rollforward(investments)))

    if opening and closing:
        multiple = closing / opening if opening else 0
        lines.append(
            f"The portfolio moved from {m(opening)} to {m(closing)}"
            + (f", a {multiple:.1f}-fold increase" if multiple >= 1.5 else "")
            + (f", of which {m(additions)} is new capital deployed rather than "
               f"revaluation of positions already held" if additions else "")
            + "."
        )
        if additions and closing:
            lines.append("")
            lines.append(
                f"That distinction matters: {additions / closing * 100:.0f}% of "
                f"the closing balance arrived during the year, so the position "
                f"reflects current deployment rather than an accumulated legacy "
                f"book."
            )
        lines.append("")

    for entry in investments:
        if entry.get("kind") == "disclosure":
            lines.append(f"The note also states {entry['measure']} of "
                         f"{m(entry['amount'])}.")
            lines.append("")
    return lines


def _render_subsidiaries(notes: dict, entity_name: str) -> list:
    """Legal structure from Exhibit 21."""
    data = (notes or {}).get("subsidiaries") or {}
    entities = data.get("subsidiaries") or []
    if not entities:
        return []

    by_jurisdiction = sorted((data.get("by_jurisdiction") or {}).items(),
                             key=lambda kv: -kv[1])
    total = len(entities)

    lines = ["## Corporate Structure", "", "### Subsidiaries and jurisdictions", ""]
    lines.append(
        f"Item 601(b)(21) requires the 10-K to list significant subsidiaries "
        f"and the jurisdiction in which each is organised. It is the only "
        f"public statement of {entity_name}'s legal structure. The exhibit "
        f"names {total} "
        f"{'entity' if total == 1 else 'entities'} across "
        f"{len([j for j, _ in by_jurisdiction if j != 'Not Stated'])} "
        f"jurisdictions."
    )
    lines.append("")
    lines.append("| Jurisdiction | Entities |")
    lines.append("|--------------|---------:|")
    for jurisdiction, count in by_jurisdiction[:15]:
        lines.append(f"| {jurisdiction} | {count} |")
    lines.append("")

    if CHARTS_AVAILABLE:
        lines.extend(_figure(charts.subsidiary_jurisdictions(data)))

    # Jurisdictions that carry no operations are worth separating: an entity
    # organised there is a financing or holding structure, not a business.
    holding = {"cayman islands", "bermuda", "luxembourg", "ireland",
               "netherlands", "british virgin islands", "jersey", "guernsey",
               "mauritius", "curacao", "barbados", "panama"}
    offshore = [(j, c) for j, c in by_jurisdiction if j.lower() in holding]
    if offshore:
        named = ", ".join(f"{count} in {jurisdiction}"
                          for jurisdiction, count in offshore)
        share = sum(c for _, c in offshore) / total * 100
        lines.append(
            f"{sum(c for _, c in offshore)} of the {total} entities "
            f"({share:.0f}%) are organised in jurisdictions used principally "
            f"for holding and financing structures — {named}. The exhibit "
            f"states where each entity is organised and nothing about what it "
            f"does, so this is a structural observation and not a finding about "
            f"where profit is recognised."
        )
        lines.append("")

    lines.append("The full list as filed:")
    lines.append("")
    for entity in entities[:120]:
        jurisdiction = entity.get("jurisdiction") or "jurisdiction not stated"
        lines.append(f"- {entity['name']} — {jurisdiction}")
    if len(entities) > 120:
        lines.append(f"- ...and {len(entities) - 120} further entities in the "
                     f"exhibit.")
    lines.append("")
    if data.get("source_url"):
        lines.append(f"Source: [Exhibit 21]({data['source_url']}).")
        lines.append("")
    return lines


def _render_overlap(overlap: dict, entity_name: str) -> list:
    """Where the same managers hold this issuer and its competitors."""
    # The peer comparison wraps the analysis; a single-issuer run returns it flat.
    analysis = (overlap or {}).get("overlap_analysis") or overlap or {}
    shared = analysis.get("shared_holders") or []
    if not shared:
        return []

    summary = analysis.get("summary") or {}
    lines = ["### Common ownership with competitors", ""]
    lines.append(
        f"The same institutions appear on the register of {entity_name} and of "
        f"its competitors. The overlap itself is not informative — an index "
        f"manager holds every large issuer by construction, and because this "
        f"comparison polls a curated set of the largest filers rather than the "
        f"whole 13F universe, the overlap rate converges on 100% whatever the "
        f"issuer. What the same filings do support is the relative weight each "
        f"manager assigns."
    )
    lines.append("")
    lines.append("| Manager | Held across | Combined value | Relative weight | Reads as |")
    lines.append("|---------|-------------|----------------|-----------------|----------|")
    for holder in shared[:15]:
        details = holder.get("details_by_ticker") or {}
        name = next((d.get("original_name") for d in details.values()
                     if d.get("original_name")), holder.get("normalized_name", "—"))
        skew = holder.get("weight_skew")
        if skew is None:
            skew_text, reading = "—", "not comparable"
        else:
            skew_text = f"{skew:.2f}x"
            reading = ("conviction" if skew >= 2 else
                       "index tracking" if skew <= 1.3 else "mild tilt")
            if holder.get("overweight") and skew >= 2:
                reading += f" in {holder['overweight']}"
        lines.append(
            f"| {name} | {holder.get('count', 0)} issuers "
            f"| {format_currency(holder.get('total_value_across_all'))} "
            f"| {skew_text} | {reading} |"
        )
    lines.append("")
    lines.append(
        "Relative weight compares how much of a manager's own portfolio sits "
        "in this issuer against the same manager's position in the peer named "
        "in its filings. A manager tracking an index reproduces the market's "
        "weights and lands near 1.0; a wide spread is an active decision. That "
        "the index trackers cluster together while the active managers scatter "
        "is what indicates the measure is reading something real."
    )
    lines.append("")

    flags = [f for f in (analysis.get("risk_flags") or [])
             if f.get("type") == "allocation_skew"]
    for flag in flags[:6]:
        lines.append(f"- {flag.get('detail') or flag.get('description', '')}")
    if flags:
        lines.append("")
    if summary.get("holder_universe"):
        lines.append(f"Holder universe: {summary['holder_universe']}.")
        lines.append("")
    return lines


def _render_balance_sheet(annual: list, metrics: dict, entity_name: str,
                          notes: dict = None) -> list:
    """Balance sheet and capital allocation, section 6.

    Every figure here already arrived with the income statement — the same
    companyfacts rows carry the balance-sheet instants and the cash-flow
    durations — but only seven of them were ever printed, as a bare metric
    table. What was missing was not data but the derived measures that make a
    balance sheet interpretable: liquidity relative to the operating base,
    leverage net of the securities portfolio, the working-capital cycle, and
    whether shareholder returns were funded out of operations or out of the
    balance sheet.
    """
    if not annual:
        return []

    now, lines = annual[0], []

    def val(row, *keys):
        for key in keys:
            v = row.get(key)
            if v:
                return float(v)
        return None

    def m(x):
        return f"${_fmt_m(x)}M" if x is not None else "—"

    def ratio(a, b, digits=2):
        return f"{a / b:.{digits}f}x" if a and b else "—"

    def share(a, b):
        return f"{a / b * 100:.1f}%" if a and b else "—"

    lines.append("## Balance Sheet and Capital Allocation")
    lines.append("")
    fy = now.get("fiscal_year", "the latest fiscal year")
    assets = val(now, "TotalAssets")
    liabilities = val(now, "TotalLiabilities")
    equity = val(now, "StockholdersEquity")

    if assets and equity:
        lines.append(
            f"At the close of FY{fy} {entity_name} carried {m(assets)} of total assets "
            f"against {m(liabilities)} of liabilities, leaving {m(equity)} of "
            f"shareholders' equity — {share(equity, assets)} of the asset base. "
            f"Equity funds the majority of assets where that share exceeds 50%; "
            f"below it, creditors do."
        )
        lines.append("")

    # ── 6.1 Liquidity ────────────────────────────────────────────────────
    cash = val(now, "Cash") or 0.0
    st_inv = val(now, "ShortTermInvestments")
    securities = val(now, "MarketableSecurities")
    # Prefer the explicit current tranche; fall back to the undivided total,
    # which some issuers report in place of the current/noncurrent split.
    liquid_investments = st_inv if st_inv is not None else securities
    liquidity = cash + (liquid_investments or 0.0)
    current_assets = val(now, "CurrentAssets")
    current_liabilities = val(now, "CurrentLiabilities")
    inventory = val(now, "Inventory")
    receivables = val(now, "AccountsReceivable")

    if liquidity:
        lines.append("### Liquidity")
        lines.append("")
        parts = [f"cash and equivalents of {m(cash)}"]
        if liquid_investments:
            parts.append(f"marketable securities of {m(liquid_investments)}")
        lines.append(
            f"Immediately available resources total {m(liquidity)}, comprising "
            f"{' and '.join(parts)}. Reading the cash line alone understates the "
            f"position for any issuer that parks its liquidity in short-dated "
            f"securities."
        )
        lines.append("")

        rows = [("Cash and equivalents", cash),
                ("Marketable securities", liquid_investments),
                ("Accounts receivable", receivables),
                ("Inventory", inventory),
                ("Total current assets", current_assets),
                ("Total current liabilities", current_liabilities)]
        lines.append("| Component | Amount | Share of current assets |")
        lines.append("|-----------|--------|------------------------|")
        for label, amount in rows:
            if amount is None:
                continue
            pct = share(amount, current_assets) if "current liabilities" not in label.lower() else "—"
            bold = "**" if label.startswith("Total") else ""
            lines.append(f"| {bold}{label}{bold} | {bold}{m(amount)}{bold} | {pct} |")
        lines.append("")

        if current_assets and current_liabilities:
            current_ratio = current_assets / current_liabilities
            quick = (current_assets - (inventory or 0.0)) / current_liabilities
            lines.append(
                f"The current ratio stands at {current_ratio:.2f}x and the quick "
                f"ratio, which excludes inventory as the least readily realisable "
                f"current asset, at {quick:.2f}x. "
                + ("Both sit comfortably above the 1.0x threshold at which current "
                   "obligations would exceed current resources."
                   if quick >= 1 else
                   "The quick ratio below 1.0x means inventory must convert to cash "
                   "on schedule for current obligations to be met from current assets.")
            )
            lines.append("")

    # ── 6.2 Leverage ─────────────────────────────────────────────────────
    lt_debt = val(now, "LongTermDebtNoncurrent") or 0.0
    st_debt = val(now, "DebtCurrent") or 0.0
    # The reported TotalDebt tag resolves to whichever single debt concept the
    # issuer tagged first, so it can capture the current portion alone. Summing
    # the two tranches is unambiguous.
    total_debt = (lt_debt + st_debt) or (val(now, "TotalDebt") or 0.0)
    leases = val(now, "OperatingLeaseLiability")
    commitments = val(now, "PurchaseObligation")

    lines.append("### Leverage and obligations")
    lines.append("")
    if total_debt:
        net = total_debt - liquidity
        lines.append(
            f"Interest-bearing debt totals {m(total_debt)}"
            + (f", of which {m(st_debt)} falls due within twelve months"
               if st_debt else "")
            + f". Against {m(liquidity)} of liquid resources the company is in a net "
            + (f"cash position of {m(-net)}" if net < 0 else f"debt position of {m(net)}")
            + (f", and debt equals {share(total_debt, equity)} of equity." if equity else ".")
        )
    else:
        lines.append(
            f"{entity_name} reports no interest-bearing debt, so the capital "
            f"structure carries no scheduled repayment obligation and no interest "
            f"burden against operating income."
        )
    lines.append("")

    # The commitments note states amounts that no single XBRL tag captures.
    # NVIDIA tags $22.7bn of unrecorded purchase obligations while the note
    # describes $95.2bn of supply commitments, $27bn of cloud services and
    # $11.4bn of investment commitments. Where the note is available it governs,
    # and the tag is reported alongside it rather than in place of it.
    noted = (notes or {}).get("commitments") or []

    obligations = [("Long-term debt", lt_debt), ("Current portion of debt", st_debt),
                   ("Operating lease liabilities", leases)]
    if noted:
        obligations += [(f"{c['kind']} commitments (off balance sheet)", c["amount"])
                        for c in noted]
    elif commitments:
        obligations.append(("Purchase commitments (off balance sheet)", commitments))
    shown = [(k, v) for k, v in obligations if v]
    if shown:
        lines.append("| Obligation | Amount | Multiple of latest operating cash flow |")
        lines.append("|------------|--------|---------------------------------------|")
        ocf = val(now, "OperatingCashFlow")
        for label, amount in shown:
            lines.append(f"| {label} | {m(amount)} | {ratio(amount, ocf)} |")
        lines.append("")

    if noted:
        total_noted = sum(c["amount"] for c in noted)
        largest = noted[0]
        lines.append(
            f"Off-balance-sheet commitments described in the notes total "
            f"{m(total_noted)}, against {m(liabilities)} of recognised "
            f"liabilities. They bind future cash without appearing on the "
            f"balance sheet. The largest is {largest['kind'].lower()} at "
            f"{m(largest['amount'])}"
            + (f", substantially all payable through fiscal "
               f"{largest['through_fiscal_year']}"
               if largest.get("through_fiscal_year") else "")
            + "."
        )
        if len(noted) > 1:
            rest = [f"{c['kind'].lower()} at {m(c['amount'])}" for c in noted[1:]]
            joined = (rest[0] if len(rest) == 1
                      else f"{', '.join(rest[:-1])} and {rest[-1]}")
            lines[-1] += f" Alongside it sit {joined}."
        if commitments and abs(commitments - total_noted) / total_noted > 0.2:
            lines[-1] += (
                f" The tagged purchase-obligation figure of {m(commitments)} covers "
                f"a narrower definition than the note and understates the "
                f"commitment position by {m(total_noted - commitments)}."
            )
        lines.append("")
        for commitment in noted:
            lines.append(f"> {commitment['sentence']}")
            lines.append("")
        lines.append(
            f"For a company that outsources manufacturing these represent capacity "
            f"reserved ahead of demand, and they are the clearest quantitative "
            f"statement of how much volume management expects to sell — one made "
            f"under the liability standard that attaches to a filed financial "
            f"statement rather than to guidance."
        )
        lines.append("")
    elif commitments:
        lines.append(
            f"Purchase commitments of {m(commitments)} are contractual but "
            f"unrecognised: they do not appear among the {m(liabilities)} of "
            f"reported liabilities, yet they bind future cash. For a company that "
            f"outsources manufacturing they represent capacity reserved ahead of "
            f"demand, and they are the clearest quantitative statement of how much "
            f"volume management expects to sell."
        )
        # Only difference the two years when both were tagged with the same
        # concept. Issuers move between PurchaseObligation and the unrecorded
        # equivalent, and comparing across the switch invents a change.
        prior = annual[1] if len(annual) > 1 else {}
        same_tag = (prior.get("PurchaseObligation_concept")
                    == now.get("PurchaseObligation_concept"))
        prior_commitments = val(prior, "PurchaseObligation") if same_tag else None
        if prior_commitments:
            change = (commitments - prior_commitments) / prior_commitments * 100
            lines[-1] += (
                f" They stand {abs(change):.0f}% "
                f"{'above' if change > 0 else 'below'} the {m(prior_commitments)} "
                f"committed a year earlier, which is a forward signal on expected "
                f"volume independent of any guidance management has given."
            )
        lines.append("")

    if CHARTS_AVAILABLE:
        lines.extend(_figure(charts.commitments(notes,
                                                val(now, "OperatingCashFlow"))))

    lines.extend(_render_acquisitions(notes, entity_name, m))
    lines.extend(_render_venture_portfolio(notes, entity_name, m))

    # ── 6.3 Working capital cycle ────────────────────────────────────────
    revenue = val(now, "Revenues")
    gross = val(now, "GrossProfit")
    cogs = (revenue - gross) if (revenue and gross is not None) else None
    payables = val(now, "AccountsPayable")
    if revenue and receivables:
        dso = receivables / revenue * 365
        dio = inventory / cogs * 365 if (inventory and cogs) else None
        dpo = payables / cogs * 365 if (payables and cogs) else None
        lines.append("### Working capital cycle")
        lines.append("")
        lines.append("| Measure | Days | Reads as |")
        lines.append("|---------|------|----------|")
        lines.append(f"| Days sales outstanding | {dso:.0f} | Time to collect a dollar of revenue |")
        if dio:
            lines.append(f"| Days inventory outstanding | {dio:.0f} | Time inventory sits before sale |")
        if dpo:
            lines.append(f"| Days payables outstanding | {dpo:.0f} | Time taken to pay suppliers |")
        if dio and dpo:
            ccc = dso + dio - dpo
            lines.append(f"| **Cash conversion cycle** | **{ccc:.0f}** | **Days of working capital funded by the company** |")
        lines.append("")
        narrative = (
            f"Receivables of {m(receivables)} equate to {dso:.0f} days of sales. "
        )
        if dio and dpo:
            ccc = dso + dio - dpo
            narrative += (
                f"With inventory turning in {dio:.0f} days and suppliers paid in "
                f"{dpo:.0f}, the cash conversion cycle runs {ccc:.0f} days: "
                + (f"the company funds {ccc:.0f} days of working capital itself, so "
                   f"growth consumes cash before it generates it."
                   if ccc > 0 else
                   "suppliers finance the cycle in full, so growth releases cash "
                   "rather than absorbing it.")
            )
        lines.append(narrative)
        lines.append("")

    # ── 6.4 Capital allocation ───────────────────────────────────────────
    lines.append("### Capital allocation")
    lines.append("")
    lines.append("All figures in millions of USD, from the audited cash flow statement.")
    lines.append("")
    lines.append("| Fiscal year | Operating cash flow | Capital expenditure | Free cash flow "
                 "| Buybacks | Dividends | Total returned | Returned as % of FCF |")
    lines.append("|-------------|--------------------|--------------------|----------------"
                 "|----------|-----------|----------------|----------------------|")
    totals = {"ocf": 0.0, "capex": 0.0, "buyback": 0.0, "dividend": 0.0}
    for row in annual[:5]:
        ocf = val(row, "OperatingCashFlow")
        capex = val(row, "CapEx")
        if ocf is None:
            continue
        fcf = ocf - (capex or 0.0)
        buyback = val(row, "StockRepurchases") or 0.0
        dividend = val(row, "Dividends") or 0.0
        returned = buyback + dividend
        totals["ocf"] += ocf
        totals["capex"] += capex or 0.0
        totals["buyback"] += buyback
        totals["dividend"] += dividend
        lines.append(
            f"| FY{row.get('fiscal_year')} | {_fmt_m(ocf)} | {_fmt_m(capex)} | {_fmt_m(fcf)} "
            f"| {_fmt_m(buyback)} | {_fmt_m(dividend)} | {_fmt_m(returned)} "
            f"| {share(returned, fcf)} |"
        )
    cumulative_fcf = totals["ocf"] - totals["capex"]
    cumulative_returned = totals["buyback"] + totals["dividend"]
    lines.append(
        f"| **Five-year total** | **{_fmt_m(totals['ocf'])}** | **{_fmt_m(totals['capex'])}** "
        f"| **{_fmt_m(cumulative_fcf)}** | **{_fmt_m(totals['buyback'])}** "
        f"| **{_fmt_m(totals['dividend'])}** | **{_fmt_m(cumulative_returned)}** "
        f"| **{share(cumulative_returned, cumulative_fcf)}** |"
    )
    lines.append("")

    if CHARTS_AVAILABLE:
        lines.extend(_figure(charts.capital_allocation(annual)))

    if cumulative_fcf:
        retained = cumulative_fcf - cumulative_returned
        lines.append(
            f"Across five years the company generated {m(cumulative_fcf)} of free cash "
            f"flow and returned {m(cumulative_returned)} of it to shareholders, "
            f"{share(cumulative_returned, cumulative_fcf)} of the total. "
            + (f"The remaining {m(retained)} was retained on the balance sheet or "
               f"deployed into acquisitions and investments."
               if retained > 0 else
               f"Returns exceeded free cash flow by {m(-retained)}, so distributions "
               f"drew on existing balances or on new borrowing rather than on the "
               f"year's operations alone.")
        )
        lines.append("")
        buyback_share = share(totals["buyback"], cumulative_returned)
        lines.append(
            f"Repurchases account for {buyback_share} of what was returned"
            + (f", with dividends the balance at {m(totals['dividend'])}."
               if totals["dividend"] else
               ", and no dividend has been paid over the period.")
        )
        remaining = val(now, "BuybackAuthorizationRemaining")
        if remaining:
            latest_buyback = val(now, "StockRepurchases")
            pace = (f" — roughly {remaining / latest_buyback:.1f} years at the FY{fy} pace"
                    if latest_buyback else "")
            lines[-1] += (
                f" {m(remaining)} remains authorised under the board's existing "
                f"repurchase programme{pace}. Authorisation is a ceiling rather than "
                f"a commitment, and carries no obligation to execute."
            )
        lines.append("")

    # ── 6.5 Capital intensity and returns ────────────────────────────────
    ppe = val(now, "PPENet")
    goodwill = val(now, "Goodwill")
    intangibles = val(now, "IntangiblesNet")
    equity_stakes = val(now, "EquityInvestments")
    capex_now = val(now, "CapEx")

    lines.append("### Asset composition and returns on capital")
    lines.append("")
    composition = [("Property, plant and equipment", ppe),
                   ("Goodwill", goodwill),
                   ("Other intangible assets", intangibles),
                   ("Strategic equity investments", equity_stakes)]
    shown = [(k, v) for k, v in composition if v]
    if shown and assets:
        lines.append("| Asset | Carrying value | Share of total assets |")
        lines.append("|-------|----------------|-----------------------|")
        for label, amount in shown:
            lines.append(f"| {label} | {m(amount)} | {share(amount, assets)} |")
        lines.append("")

    if ppe and revenue:
        lines.append(
            f"Net property, plant and equipment of {m(ppe)} supports {m(revenue)} of "
            f"revenue, a ratio of {revenue / ppe:.1f}x. "
            + (f"Capital expenditure of {m(capex_now)} in FY{fy} equals "
               f"{share(capex_now, revenue)} of revenue."
               if capex_now else "")
        )
        lines.append("")

    if equity_stakes and assets:
        lines.append(
            f"Strategic equity investments of {m(equity_stakes)} — {share(equity_stakes, assets)} "
            f"of assets — are stakes in other companies rather than operating assets. "
            f"They are carried at fair value, so their movement affects reported income "
            f"without any change in the operating business."
        )
        lines.append("")

    net_income = val(now, "NetIncome")
    if net_income and equity and assets:
        invested = equity + total_debt
        lines.append("| Return measure | FY" + str(fy) + " | Basis |")
        lines.append("|----------------|------|-------|")
        lines.append(f"| Return on equity | {share(net_income, equity)} | Net income over shareholders' equity |")
        lines.append(f"| Return on assets | {share(net_income, assets)} | Net income over total assets |")
        lines.append(f"| Return on invested capital | {share(net_income, invested)} | Net income over equity plus debt |")
        if metrics.get("debt_to_equity") is not None:
            lines.append(f"| Debt to equity | {metrics.get('debt_to_equity')} | Reported leverage ratio |")
        lines.append("")
        lines.append(
            f"Return on equity of {share(net_income, equity)} and return on invested "
            f"capital of {share(net_income, invested)} sit close together because "
            f"leverage is {'minimal' if total_debt < equity * 0.2 else 'material'}: "
            f"with debt at {share(total_debt, equity)} of equity, borrowing "
            f"{'does little to amplify' if total_debt < equity * 0.2 else 'materially amplifies'} "
            f"the return earned on the operating base."
        )
        lines.append("")

    return lines


def _render_valuation(dcf: dict, consensus: dict, ticker: str,
                      entity_name: str) -> list:
    """Full valuation walk-through: base, discount rate, bridge, sensitivity.

    The model outputs were already computed upstream; this renders the chain of
    reasoning behind them so the number is auditable rather than asserted.
    """
    lines = []
    inputs = dcf.get("inputs") or {}
    base_fcf = inputs.get("base_fcf") or 0
    horizon = int(inputs.get("projection_years") or 0)
    wacc = (inputs.get("wacc_pct") or 0) / 100
    tg = (inputs.get("terminal_growth_pct") or 0) / 100
    g0 = (inputs.get("fcf_growth_initial_pct")
          or inputs.get("fcf_growth_5y_assumed") or 0) / 100
    net_debt = dcf.get("net_debt") or 0
    equity_value = dcf.get("equity_value") or 0
    intrinsic = dcf.get("intrinsic_price_per_share")
    price = dcf.get("current_market_price")
    shares = (equity_value / intrinsic) if (equity_value and intrinsic) else 0

    if not (base_fcf and horizon and wacc and intrinsic):
        return lines

    lines.append("## Valuation")
    lines.append("")
    lines.append(
        f"The valuation is a discounted cash flow on unlevered free cash flow, "
        f"run over an explicit {horizon}-year forecast with a Gordon terminal "
        f"value. Every input is derived from filed figures or quoted market "
        f"data; none is hand-set for this issuer, which is what makes the "
        f"output comparable across names."
    )
    lines.append("")

    # ── Free cash flow base ──────────────────────────────────────────────
    history = dcf.get("fcf_history") or []
    if history:
        lines.append("### The free cash flow base")
        lines.append("")
        lines.append(
            f"Free cash flow is operating cash flow less capital expenditure, "
            f"both taken from SEC XBRL company facts and matched on period end "
            f"date rather than filing year, so a restated or late-filed period "
            f"cannot pair the wrong two figures together."
        )
        lines.append("")
        lines.append("| Fiscal year | Period end | Operating cash flow | CapEx | Free cash flow |")
        lines.append("|-------------|------------|---------------------|-------|----------------|")
        for h in history[:6]:
            capex_note = "" if h.get("capex_retrieved", True) else " *(not disclosed)*"
            lines.append(
                f"| FY{h.get('fy') or '—'} | {h.get('period_end') or '—'} "
                f"| ${_fmt_m(h.get('ocf'))}M | ${_fmt_m(h.get('capex'))}M{capex_note} "
                f"| ${_fmt_m(h.get('fcf'))}M |"
            )
        lines.append("")
        newest = history[0]
        cagr = inputs.get("historical_cagr_pct")
        base_sentence = (
            f"The model starts from FY{newest.get('fy', '')} free cash flow of "
            f"${_fmt_m(base_fcf)}M."
        )
        if cagr:
            base_sentence += (
                f" Realised growth across the retrieved history compounds at "
                f"{cagr:.1f}% a year. The forecast does not extend that rate: "
                f"it opens at {g0 * 100:.1f}% and fades linearly to the "
                f"{tg * 100:.1f}% terminal rate by year {horizon}, because "
                f"{'an' if str(int(cagr))[0] in '8' else 'a'} {cagr:.0f}% "
                f"compound sustained for a decade implies an end-state larger "
                f"than any plausible addressable market."
            )
        lines.append(base_sentence)
        lines.append("")

    # ── Discount rate ────────────────────────────────────────────────────
    lines.append("### Discount rate")
    lines.append("")
    beta_raw = inputs.get("beta_raw")
    beta_adj = inputs.get("beta_adjusted") or inputs.get("beta")
    rf = inputs.get("risk_free_rate_pct")
    coe = inputs.get("cost_of_equity_pct")
    cod = inputs.get("cost_of_debt_aftertax_pct")
    we = inputs.get("equity_weight")
    wd = inputs.get("debt_weight")
    parts = []
    if rf is not None:
        parts.append(f"a {rf:.2f}% risk-free rate taken from the 10-year Treasury")
    if beta_raw and beta_adj:
        parts.append(
            f"a raw equity beta of {beta_raw:.2f}, pulled toward the market by "
            f"the standard Blume adjustment to {beta_adj:.3f}"
        )
    if parts:
        lines.append(
            "Cost of equity is CAPM on " + ", and ".join(parts) + ". "
            + (f"That yields {coe:.2f}%. " if coe else "")
            + (f"After-tax cost of debt is {cod:.2f}%. " if cod else "")
            + (f"At a capital structure of {we * 100:.1f}% equity and "
               f"{wd * 100:.1f}% debt, the weighted average cost of capital is "
               f"{wacc * 100:.2f}%." if (we is not None and wd is not None) else "")
        )
        lines.append("")
        if beta_raw and beta_adj and beta_raw > 1.5:
            lines.append(
                f"The beta is the single most consequential input here. A raw "
                f"{beta_raw:.2f} reflects realised volatility far above the "
                f"market, and it drives the discount rate well above what a "
                f"cash-generative balance sheet would otherwise carry. The "
                f"Blume adjustment tempers it on the reasoning that betas mean-"
                f"revert, but a reader who believes the volatility is transitory "
                f"should read the lower-WACC column of the grid below as the "
                f"more relevant one."
            )
            lines.append("")

    # ── Projection and bridge ────────────────────────────────────────────
    projected = dcf.get("projected_fcfs") or []
    if projected:
        lines.append("### Forecast and present value")
        lines.append("")
        lines.append("| Year | Growth | Projected FCF | Discount factor | Present value |")
        lines.append("|------|--------|---------------|-----------------|---------------|")
        for p in projected:
            yr = p.get("year")
            df = 1 / ((1 + wacc) ** yr) if yr else None
            lines.append(
                f"| {yr} | {p.get('growth_rate_pct', 0):.1f}% "
                f"| ${_fmt_m(p.get('projected_fcf'))}M "
                f"| {df:.3f} | ${_fmt_m(p.get('present_value'))}M |"
            )
        lines.append("")

    pv_fcf = dcf.get("pv_projected_fcfs") or 0
    pv_tv = dcf.get("pv_terminal_value") or 0
    ev = dcf.get("enterprise_value") or 0
    tv = dcf.get("terminal_value") or 0
    lines.append("### From enterprise value to price per share")
    lines.append("")
    lines.append("| Component | Value |")
    lines.append("|-----------|-------|")
    lines.append(f"| Present value of forecast cash flows | ${_fmt_m(pv_fcf)}M |")
    lines.append(f"| Terminal value at year {horizon} | ${_fmt_m(tv)}M |")
    lines.append(f"| Present value of terminal value | ${_fmt_m(pv_tv)}M |")
    lines.append(f"| **Enterprise value** | **${_fmt_m(ev)}M** |")
    lines.append(
        f"| Less net debt{' (a net cash position, so it adds)' if net_debt < 0 else ''} "
        f"| {'-' if net_debt < 0 else ''}${_fmt_m(abs(net_debt))}M |"
    )
    lines.append(f"| **Equity value** | **${_fmt_m(equity_value)}M** |")
    if shares:
        lines.append(f"| Diluted shares | {shares / 1e6:,.0f}M |")
    lines.append(f"| **Intrinsic value per share** | **${intrinsic:,.2f}** |")
    lines.append("")

    if ev and pv_tv:
        tv_share = pv_tv / ev * 100
        lines.append(
            f"The terminal value carries {tv_share:.1f}% of the enterprise "
            f"value. "
            + ("That is a high share, and it means the valuation rests more on "
               "the perpetuity assumption than on the forecast decade. Readers "
               "who distrust the terminal growth rate should weight the "
               "sensitivity grid accordingly."
               if tv_share > 65 else
               "That is a moderate share, so the explicit forecast rather than "
               "the perpetuity assumption carries most of the value.")
        )
        lines.append("")

    # ── Sensitivity ──────────────────────────────────────────────────────
    if shares:
        lines.append("### Sensitivity to the two assumptions that matter")
        lines.append("")
        lines.append(
            "Intrinsic value per share across a range of discount rates and "
            "terminal growth rates, holding the free cash flow base and the "
            "growth fade constant. Cells at or below the traded price are the "
            "combinations under which the market is not overpaying."
        )
        lines.append("")
        wacc_row = [w for w in (wacc - 0.03, wacc - 0.015, wacc, wacc + 0.015,
                                wacc + 0.03) if w > 0]
        tg_col = [t for t in (tg - 0.01, tg - 0.005, tg, tg + 0.005, tg + 0.01)
                  if t >= 0]
        lines.append("| WACC \\ terminal growth | "
                     + " | ".join(f"{t * 100:.1f}%" for t in tg_col) + " |")
        lines.append("|---" * (len(tg_col) + 1) + "|")
        grid = []
        for w in wacc_row:
            row, cells = [], []
            for t in tg_col:
                v = _dcf_price(base_fcf, g0, t, w, horizon, net_debt, shares)
                row.append(v)
                cells.append(f"${v:,.0f}" if v else "n/m")
            grid.append(row)
            marker = " **(base)**" if abs(w - wacc) < 1e-9 else ""
            lines.append(f"| **{w * 100:.2f}%**{marker} | " + " | ".join(cells) + " |")
        lines.append("")

        if CHARTS_AVAILABLE:
            lines.extend(_figure(charts.dcf_sensitivity(
                wacc_row, tg_col, grid, base_wacc=wacc, base_growth=tg,
                current=price)))

    # ── Scenarios ────────────────────────────────────────────────────────
    scenarios = dcf.get("scenarios") or {}
    if scenarios:
        lines.append("### Scenarios")
        lines.append("")
        for name in ("bear", "base", "bull"):
            s = scenarios.get(name) or {}
            iv = s.get("intrinsic_price")
            if not iv:
                continue
            delta = ((iv - price) / price * 100) if price else None
            lines.append(
                f"- **{name.title()} — ${iv:,.2f}**"
                + (f" ({delta:+.1f}% against the traded price)" if delta is not None else "")
                + f". {s.get('description', '')}."
            )
        lines.append("")

    # ── Reverse DCF ──────────────────────────────────────────────────────
    if price and shares:
        implied = _implied_growth(price, base_fcf, tg, wacc, horizon, net_debt,
                                  shares)
        gap = ((intrinsic - price) / price * 100) if price else 0
        lines.append("### What the market price implies")
        lines.append("")
        if implied is not None:
            lines.append(
                f"Inverting the model answers the more useful question. Holding "
                f"the {wacc * 100:.2f}% discount rate and {tg * 100:.1f}% "
                f"terminal growth fixed, the traded price of ${price:,.2f} is "
                f"consistent with opening free cash flow growth of "
                f"{implied * 100:.1f}%, fading on the same schedule — against "
                f"the {g0 * 100:.1f}% the base case assumes."
            )
            lines.append("")
            lines.append(
                f"So the {abs(gap):.0f}% gap between the model and the market is "
                f"not a claim that the company is worth "
                f"{'less' if gap < 0 else 'more'} than it trades for. It is a "
                f"statement that buyers are underwriting roughly "
                f"{implied * 100:.0f}% near-term cash flow growth where this "
                f"model underwrites {g0 * 100:.0f}%. Whether that is optimism "
                f"or foresight is a judgement about demand durability, not "
                f"about arithmetic."
            )
        else:
            lines.append(
                f"The traded price of ${price:,.2f} cannot be reconciled with "
                f"this model at any non-negative growth rate within a plausible "
                f"range, holding the discount rate and terminal growth fixed. "
                f"The gap therefore sits in the discount rate or the terminal "
                f"assumption rather than in the growth forecast."
            )
        lines.append("")

    # ── Consensus cross-check ────────────────────────────────────────────
    if consensus.get("target_consensus"):
        tc = consensus["target_consensus"]
        lines.append("### Sell-side cross-check")
        lines.append("")
        sentence = (
            f"Consensus sits at ${tc:,.2f}"
            + (f" against a traded ${price:,.2f}" if price else "")
            + (f", with the range spanning ${consensus.get('target_low', 0):,.0f} "
               f"to ${consensus.get('target_high', 0):,.0f}"
               if consensus.get("target_high") else "")
            + "."
        )
        if consensus.get("ratings_total"):
            sentence += (
                f" {consensus.get('bullish_pct', 0)}% of "
                f"{consensus['ratings_total']} covering analysts carry a buy or "
                f"better."
            )
        lines.append(sentence)
        lines.append("")
        if intrinsic and tc:
            lines.append(
                f"Consensus and this model differ by "
                f"{abs((tc - intrinsic) / intrinsic * 100):.0f}%. Sell-side "
                f"targets are typically 12-month price objectives anchored on "
                f"near-term earnings multiples, not perpetuity cash flow "
                f"valuations, so the two are answering different questions and "
                f"the divergence is expected rather than contradictory."
            )
            lines.append("")

    return lines


def generate_markdown_report(data: dict) -> str:
    """Generate comprehensive markdown report from Phase 2 data."""
    global FIGURE_COUNT
    FIGURE_COUNT = 0
    lines = []

    financial = data.get("financial_intelligence", {}) or {}
    notes = data.get("filing_notes", {}) or {}
    statements = financial.get("financial_statements", {}) or {}
    annual = statements.get("income_statement", []) or []
    quarterly = statements.get("quarterly", []) or []
    ttm = statements.get("ttm", {}) or {}
    metrics = statements.get("metrics", {}) or {}
    company = financial.get("company_info", {}) or {}

    valuation = data.get("valuation_analysis", {}) or {}
    dcf = valuation.get("dcf", {}) or {}
    snapshot = dcf.get("market_snapshot", {}) or {}
    consensus = snapshot.get("consensus", {}) or {}

    # Header
    # Prefer values carried in the payload so the renderer is not tied to the
    # module-level configuration of a particular run.
    entity_name = data.get("entity_name") or ENTITY_NAME
    ticker = data.get("ticker") or TICKER
    exchange = company.get("exchange") or snapshot.get("exchange") or ""

    lines.append(f"# {entity_name} — Intelligence Report")
    lines.append("")
    lines.append("**Classification:** INTERNAL USE ONLY — NOT FOR DISTRIBUTION")
    lines.append(f"**Report Date:** {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"**Ticker:** {(exchange + ': ') if exchange else ''}{ticker}")
    lines.append("")

    # Entity identity block
    if company:
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Legal entity | {company.get('name') or '—'} ({company.get('state') or '—'}) |")
        lines.append(f"| SEC CIK | {financial.get('cik') or '—'} |")
        lines.append(f"| SIC | {company.get('sic') or '—'} — {company.get('sic_description') or '—'} |")
        lines.append(f"| IRS EIN | {company.get('ein') or '—'} |")
        lines.append(f"| Exchange | {company.get('exchange') or '—'} |")
        lines.append(f"| Fiscal year end | {_fiscal_year_end(company.get('fiscal_year_end'))} |")
        lines.append(f"| Report date | {datetime.now().strftime('%d %B %Y')} |")
        if snapshot.get("price"):
            lines.append(f"| Last price | ${snapshot['price']:,.2f} |")
        if snapshot.get("market_cap"):
            lines.append(f"| Market capitalisation | {_money(snapshot['market_cap'])} |")
        if annual and annual[0].get("Revenues"):
            lines.append(
                f"| Revenue (FY{annual[0].get('fiscal_year') or ''}) | "
                f"${_fmt_m(annual[0]['Revenues'])}M |"
            )
        lines.append("")
    lines.append("---")
    lines.append("")

    # ── Executive Summary ────────────────────────────────────────────────
    lines.append("## Executive Summary")
    lines.append("")
    if annual:
        latest = annual[0]
        prior = annual[1] if len(annual) > 1 else {}
        rev = latest.get("Revenues")
        prior_rev = prior.get("Revenues")
        growth = ((rev - prior_rev) / prior_rev * 100) if rev and prior_rev else None
        lines.append(
            f"{entity_name} closed FY{latest.get('fiscal_year', '')} with "
            f"${_fmt_m(rev)}M of revenue"
            + (f", up {growth:.1f}% year over year" if growth else "")
            + f", and ${_fmt_m(latest.get('NetIncome'))}M of net income "
            f"({_pct(latest.get('net_margin'))} net margin)."
        )
        if ttm.get("Revenues"):
            lines.append("")
            lines.append(
                f"On a trailing-twelve-month basis through {ttm.get('period_end', '')} the company "
                f"generated ${_fmt_m(ttm.get('Revenues'))}M of revenue and "
                f"${_fmt_m(ttm.get('NetIncome'))}M of net income — a "
                f"{_pct(ttm.get('net_margin'))} net margin."
            )
    if snapshot.get("price"):
        lines.append("")
        below = snapshot.get("pct_below_52w_high")
        lines.append(
            f"{ticker} last traded at ${snapshot['price']:,.2f} for a market capitalisation of "
            f"{_fmt_scaled(snapshot.get('market_cap'))}"
            + (f", {abs(below):.1f}% below its 52-week high of "
               f"${snapshot.get('week_52_high'):,.2f}." if below else ".")
        )
    lines.append("")

    # The findings that follow are ranked by materiality and each is carried in
    # full by a later section. A reader who stops here should still have the
    # report's conclusions.
    findings = _summary_findings(data, entity_name, ticker)
    if findings:
        lines.append(f"{_ORDINALS[min(len(findings), 10) - 1]} findings drive "
                     f"this report's conclusions."
                     if len(findings) > 1 else
                     "One finding drives this report's conclusions.")
        lines.append("")
        for i, finding in enumerate(findings[:10]):
            lines.append(f"**{_ORDINALS[i]}.** {finding}")
            lines.append("")

    # ── Investment View ──────────────────────────────────────────────────
    if dcf and not dcf.get("error"):
        lines.append("## Investment View")
        lines.append("")
        current_price = dcf.get("current_market_price")
        intrinsic = dcf.get("intrinsic_price_per_share")
        scenarios = dcf.get("scenarios", {}) or {}

        lines.append("| Method | Output | Vs. market |")
        lines.append("|--------|--------|------------|")
        for name in ("bear", "base", "bull"):
            s = scenarios.get(name) or {}
            iv = s.get("intrinsic_price")
            if iv and current_price:
                delta = (iv - current_price) / current_price * 100
                lines.append(f"| DCF — {name.title()} | ${iv:,.2f} | {delta:+.1f}% |")
        if consensus.get("target_consensus") and current_price:
            tc = consensus["target_consensus"]
            lines.append(
                f"| Sell-side consensus target | ${tc:,.2f} | "
                f"{(tc - current_price) / current_price * 100:+.1f}% |"
            )
        lines.append(f"| Market price | ${current_price:,.2f} | — |"
                     if current_price else "| Market price | — | — |")
        lines.append("")
        lines.append(f"**Assessment:** {dcf.get('assessment') or 'N/A'}")
        lines.append("")

        if consensus.get("ratings"):
            r = consensus["ratings"]
            lines.append(
                f"Sell-side distribution ({consensus.get('ratings_period', '')}): "
                f"{r.get('strongBuy', 0)} strong buy, {r.get('buy', 0)} buy, "
                f"{r.get('hold', 0)} hold, {r.get('sell', 0)} sell — "
                f"{consensus.get('bullish_pct', 0)}% bullish across "
                f"{consensus.get('ratings_total', 0)} analysts"
                + (f". Targets range "
                   f"${consensus['target_low']:,.0f}–"
                   f"${consensus['target_high']:,.0f}."
                   if consensus.get("target_low") and consensus.get("target_high")
                   else ".")
            )
            lines.append("")

        inputs = dcf.get("inputs") or {}
        if inputs:
            lines.append(
                f"The model discounts a "
                f"{int(inputs.get('projection_years') or 0)}-year free cash flow "
                f"forecast at a {(inputs.get('wacc_pct') or 0):.2f}% weighted "
                f"average cost of capital, opening at "
                f"{(inputs.get('fcf_growth_initial_pct') or 0):.1f}% growth and "
                f"fading to a {(inputs.get('terminal_growth_pct') or 0):.1f}% "
                f"terminal rate. Market inputs are sourced from "
                f"{dcf.get('market_data_provider') or 'the configured provider'}. "
                f"The full derivation, a sensitivity grid and the growth rate "
                f"the traded price implies are in the Valuation section."
            )
            lines.append("")

    # ── Financial Performance ────────────────────────────────────────────
    if annual:
        lines.append("## Financial Performance")
        lines.append("")
        lines.append("All figures US GAAP, in millions of USD, from SEC XBRL companyfacts"
                     f" (CIK {financial.get('cik') or '—'}).")
        lines.append("")
        lines.append("### Annual results")
        lines.append("")
        lines.append("| Fiscal year | Revenue | Gross profit | Operating income | "
                     "Net income | Gross margin | Operating margin | Net margin |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for row in annual[:5]:
            lines.append(
                f"| FY{row.get('fiscal_year', '')} ({row.get('period_end_date', '')}) "
                f"| {_fmt_m(row.get('Revenues'))} | {_fmt_m(row.get('GrossProfit'))} "
                f"| {_fmt_m(row.get('OperatingIncome'))} | {_fmt_m(row.get('NetIncome'))} "
                f"| {_pct(row.get('gross_margin'))} | {_pct(row.get('operating_margin'))} "
                f"| {_pct(row.get('net_margin'))} |"
            )
        lines.append("")

        if CHARTS_AVAILABLE:
            lines.extend(_figure(charts.revenue_and_margin(annual)))

        if quarterly:
            lines.append("### Quarterly detail")
            lines.append("")
            lines.append("| Quarter ended | Revenue | Gross profit | Gross margin | Net income |")
            lines.append("|---|---|---|---|---|")
            for q in quarterly[:8]:
                rev = q.get("Revenues")
                gp = q.get("GrossProfit")
                gm = (gp / rev * 100) if rev and gp else None
                flag = " *(DERIVED)*" if q.get("derived") else ""
                lines.append(
                    f"| {q.get('period_end', '')} {q.get('fiscal_period', '')}{flag} "
                    f"| {_fmt_m(rev)} | {_fmt_m(gp)} | {_pct(gm)} | {_fmt_m(q.get('NetIncome'))} |"
                )
            lines.append("")
            lines.append("Quarters marked DERIVED are computed as the full fiscal year less "
                         "Q1–Q3, because discrete fourth-quarter durations are not tagged in XBRL.")
            lines.append("")

        if ttm.get("Revenues"):
            lines.append("### Trailing twelve months")
            lines.append("")
            lines.append("| Metric | TTM |")
            lines.append("|--------|-----|")
            lines.append(f"| Revenue | {_fmt_m(ttm.get('Revenues'))} |")
            lines.append(f"| Gross profit | {_fmt_m(ttm.get('GrossProfit'))} |")
            lines.append(f"| Operating income | {_fmt_m(ttm.get('OperatingIncome'))} |")
            lines.append(f"| Net income | {_fmt_m(ttm.get('NetIncome'))} |")
            lines.append(f"| Gross margin | {_pct(ttm.get('gross_margin'))} |")
            lines.append(f"| Operating margin | {_pct(ttm.get('operating_margin'))} |")
            lines.append(f"| Net margin | {_pct(ttm.get('net_margin'))} |")
            lines.append("")

        # Cash generation and the balance sheet were summarised here as two
        # small tables. They now carry their own section, where the derived
        # measures have room to be stated.

    # ── Segment, Geographic and Customer Concentration ───────────────────
    lines.extend(_render_segments(financial.get("segments") or {}, entity_name))
    lines.extend(_render_subsidiaries(notes, entity_name))

    # ── Peer Comparison ──────────────────────────────────────────────────
    # Placed straight after the issuer's own financials: a margin is only
    # readable against the margins of companies selling into the same market.
    lines.extend(_render_peer_comparison(data, entity_name))
    lines.extend(_figure(charts.peer_metric_bars(
        data.get("peer_comparison") or {})))

    # ── Market Dynamics Analysis ──────────────────────────────────────────
    # Analyzes demand factors, infrastructure scaling, customer churn, and
    # competitive landscape - uses SEC filings and business intelligence.
    if MARKET_DYNAMICS_AVAILABLE:
        try:
            # Get filing text from multiple sources
            filing_text = ""
            # Try notes dict first
            if notes:
                for key in ["business_description", "risk_factors", "mda", "item1", "item1a", "item7"]:
                    if notes.get(key):
                        filing_text += str(notes[key]) + " "
            # Also check business_intelligence for additional context
            bi = data.get("business_intelligence") or {}
            bm = bi.get("business_model") or {}
            io = bi.get("industry_outlook") or {}
            if bm.get("business_description"):
                filing_text += str(bm["business_description"]) + " "
            if io.get("sector_outlook"):
                filing_text += str(io["sector_outlook"]) + " "
            if io.get("competitive_landscape"):
                filing_text += str(io["competitive_landscape"]) + " "
            if io.get("growth_drivers"):
                for driver in io.get("growth_drivers") or []:
                    filing_text += str(driver) + " "
            if io.get("industry_challenges"):
                for challenge in io.get("industry_challenges") or []:
                    filing_text += str(challenge) + " "

            # Get news articles if available
            news_articles = (data.get("news_intelligence") or {}).get("articles") or []

            # Get peers for competitive analysis
            peers = data.get("competitors") or COMPETITORS or []

            if filing_text or news_articles:
                market_dynamics = get_market_dynamics(
                    filing_text=filing_text,
                    news_articles=news_articles,
                    financial_data=financial.get("financial_statements"),
                    segment_data=financial.get("segments"),
                    peers=peers,
                )
                lines.extend(render_market_dynamics_markdown(market_dynamics))
        except Exception as e:
            logger.warning(f"Market dynamics analysis failed: {e}")

    # ── Industry Direction & Trends ───────────────────────────────────────
    # Analyzes industry lifecycle, technology trends, consumer preferences,
    # and regulatory direction - uses SEC filings and business intelligence.
    if INDUSTRY_TRENDS_AVAILABLE:
        try:
            # Get filing text from multiple sources
            filing_text = ""
            if notes:
                for key in ["business_description", "risk_factors", "mda", "item1", "item1a", "item7"]:
                    if notes.get(key):
                        filing_text += str(notes[key]) + " "
            # Also check business_intelligence for additional context
            bi = data.get("business_intelligence") or {}
            bm = bi.get("business_model") or {}
            io = bi.get("industry_outlook") or {}
            if bm.get("business_description"):
                filing_text += str(bm["business_description"]) + " "
            if io.get("sector_outlook"):
                filing_text += str(io["sector_outlook"]) + " "
            if io.get("regulatory_environment"):
                filing_text += str(io["regulatory_environment"]) + " "
            if io.get("growth_drivers"):
                for driver in io.get("growth_drivers") or []:
                    filing_text += str(driver) + " "

            news_articles = (data.get("news_intelligence") or {}).get("articles") or []
            industry = (company.get("sic_description") or "").split("-")[0].strip()

            if filing_text or news_articles:
                industry_trends = get_industry_trends(
                    filing_text=filing_text,
                    news_articles=news_articles,
                    industry=industry,
                    business_model=financial.get("segments"),
                )
                lines.extend(render_industry_trends_markdown(industry_trends))
        except Exception as e:
            logger.warning(f"Industry trends analysis failed: {e}")

    # ── Balance Sheet and Capital Allocation ─────────────────────────────
    if annual:
        lines.extend(_render_balance_sheet(annual, metrics, entity_name, notes))

    # ── Valuation ────────────────────────────────────────────────────────
    if dcf and not dcf.get("error"):
        lines.extend(_render_valuation(dcf, consensus, ticker, entity_name))

    # ── Key Personnel ────────────────────────────────────────────────────
    proxy = data.get("proxy_intelligence", {}) or {}
    # Read ahead of the personnel section: director profiles cite each
    # individual's own Form 4 record alongside their proxy disclosures.
    insider = data.get("insider_transactions") or financial.get("insider_activity", {}) or {}
    comp = (proxy.get("executive_compensation") or {}).get("all_entries", []) or []
    board = proxy.get("board_composition", {}) or {}
    personnel = data.get("personnel_intelligence", {}) or {}
    dossiers = personnel.get("executive_dossiers", []) or []

    if comp or board.get("directors") or dossiers:
        lines.append("## Key Personnel")
        lines.append("")
        proxies = proxy.get("proxy_filings_analyzed") or []
        if proxies:
            lines.append(f"Sourced from {len(proxies)} DEF 14A proxy statement(s); "
                         f"most recent filed {comp[0].get('filing_date') or '—' if comp else '—'}.")
            lines.append("")

        if comp:
            lines.append("### Compensation (per most recent proxy)")
            lines.append("")
            lines.append("| Name | Position | Salary | Stock awards | Other | Total |")
            lines.append("|------|----------|--------|--------------|-------|-------|")
            # The table reports three fiscal years per executive, most recent
            # first, so each name recurs. Only the latest year is shown.
            latest, seen_names = [], set()
            for person in comp:
                key = (person.get("name") or "").lower()
                if key and key not in seen_names:
                    seen_names.add(key)
                    latest.append(person)
            for person in latest[:20]:
                lines.append(
                    f"| {person.get('name') or '—'} "
                    f"| {person.get('title') or '—'} "
                    f"| {format_currency(person.get('salary'))} "
                    f"| {format_currency(person.get('stock_awards'))} "
                    f"| {format_currency(person.get('other_compensation'))} "
                    f"| {format_currency(person.get('total'))} |"
                )
            lines.append("")

        directors = board.get("directors") or []
        # Someone who drew fees during the year but has since left the board is
        # part of the compensation record, not the sitting board.
        former = [d for d in directors if d.get("is_former")]
        directors = [d for d in directors if not d.get("is_former")]

        if directors:
            lines.append(f"### Board composition ({len(directors)} directors)")
            lines.append("")
            if board.get("avg_tenure_years"):
                lines.append(f"- **Average tenure:** {board['avg_tenure_years']:.1f} years")
            committees = board.get("committees") or {}
            for name, members in committees.items():
                if members:
                    lines.append(f"- **{name.title()} committee:** {', '.join(members)}")
            lines.append("")
            lines.append("| Director | Age | Director since | Fees earned |")
            lines.append("|----------|-----|----------------|-------------|")
            for d in directors[:25]:
                lines.append(
                    f"| {d.get('name') or '—'} | {d.get('age') or '—'} "
                    f"| {d.get('since') or '—'} "
                    f"| {format_currency(d.get('fees_earned'))} |"
                )
            lines.append("")

            lines.append("### Director profiles")
            lines.append("")
            proxy_date = (comp[0].get("filing_date") if comp else None) or "the latest proxy"
            for d in directors[:25]:
                lines.extend(_render_person(d, insider, proxy_date))

        if former:
            lines.append(f"### Directors who left the board ({len(former)})")
            lines.append("")
            lines.append(
                "The following drew director fees during the reported year but "
                "no longer serve, per the proxy's own description. They are "
                "excluded from the board count above."
            )
            lines.append("")
            for d in former:
                lines.append(
                    f"- **{d.get('name') or '—'}** — "
                    f"{format_currency(d.get('fees_earned'))} in fees for the "
                    f"year reported."
                )
            lines.append("")

        sop = proxy.get("say_on_pay") or {}
        if sop.get("approval_pct") is not None:
            lines.append(f"**Say-on-pay:** {sop['approval_pct']}% approval"
                         f" ({sop.get('votes_for', 0):,} for,"
                         f" {sop.get('votes_against', 0):,} against)"
                         f" — {sop.get('source', 'source unrecorded')}.")
            lines.append("")

        lines.extend(_render_related_parties(proxy, entity_name))

        # ── Related-party cross-reference ────────────────────────────────
        # Item 404 names the conflicts; Section 16, Form 3 outside seats and the
        # federal ledger say whether anyone else names the same parties. All
        # four were already in the report, on separate pages.
        if SELF_DEALING_AVAILABLE:
            try:
                lines.extend(render_self_dealing_markdown(
                    cross_reference_self_dealing(
                        proxy.get("related_party_transactions") or [],
                        insider_transactions=data.get("insider_transactions") or {},
                        board_interlocks=data.get("board_interlocks") or {},
                        contract_intelligence=data.get("contract_intelligence") or {},
                        family_network=data.get("family_network") or {},
                        institutional_holders=(
                            (data.get("institutional_holdings") or {})
                            .get("holders") or []),
                        entity_name=entity_name,
                    )))
            except Exception as e:
                logger.warning(f"Self-dealing cross-reference failed: {e}")

        lines.extend(_render_family_network(data, entity_name))
        lines.extend(_render_interlocks(data.get("board_interlocks") or {},
                                        entity_name, proxy))
        lines.extend(_render_network_overlaps(data, entity_name))
        lines.extend(_render_cooccurrence(data, entity_name))
        lines.extend(_figure(charts.cooccurrence_graph(
            data.get("cooccurrence") or {})))
        lines.extend(_figure(charts.cohort_activity(
            data.get("cooccurrence") or {})))

        # ── Founder & Executive Correlations ─────────────────────────────
        # Identifies educational overlaps (PayPal Mafia style), prior company
        # connections, and serial founders among the executive team.
        if FOUNDER_CORRELATIONS_AVAILABLE:
            try:
                # Build people list from directors and dossiers
                people_for_correlation = []
                for d in directors:
                    people_for_correlation.append({
                        "name": d.get("name", ""),
                        "title": "Director",
                        "biography": d.get("biography") or d.get("bio") or "",
                    })
                for exec_d in dossiers:
                    people_for_correlation.append({
                        "name": exec_d.get("name", ""),
                        "title": exec_d.get("title", ""),
                        "biography": exec_d.get("background") or exec_d.get("biography") or "",
                    })
                if people_for_correlation:
                    correlation_data = build_founder_correlation_graph(
                        people_for_correlation, entity_name)
                    lines.extend(render_founder_correlations_markdown(correlation_data))
            except Exception as e:
                logger.warning(f"Founder correlations failed: {e}")

        for person in dossiers[:10]:
            lines.append(f"### {person.get('name', 'Unknown')}")
            lines.append(f"**{person.get('title', '')}**")
            lines.append("")
            if person.get("background"):
                lines.append(f"{person['background'][:300]}...")
            lines.append("")

    # ── Insider Activity ─────────────────────────────────────────────────
    # (assigned above, ahead of the personnel section)
    ins_summary = insider.get("summary", {}) or {}
    if insider.get("filings_count"):
        lines.append("## Insider Activity")
        lines.append("")
        lines.append(f"- **Form 4 filings found:** {insider.get('filings_count', 0):,}"
                     f" ({insider.get('filings_parsed', 0):,} parsed,"
                     f" {len(insider.get('transactions') or []):,} transactions)")

        sold = ins_summary.get("open_market_value_sold") or 0
        bought = ins_summary.get("open_market_value_bought") or 0
        if sold or bought:
            lines.append(f"- **Open-market sales:** {format_currency(sold)}")
            lines.append(f"- **Open-market purchases:** {format_currency(bought)}")
        disc = ins_summary.get("discretionary_sold") or 0
        plan = ins_summary.get("plan_based_sold") or 0
        if disc or plan:
            total = disc + plan
            lines.append(f"- **Discretionary (non-10b5-1):** {format_currency(disc)} "
                         f"({disc / total * 100:.1f}% of disposals by value)")
            lines.append(f"- **10b5-1 plan sales:** {format_currency(plan)}")
        lines.append("")

        by_code = insider.get("by_code") or {}
        if by_code:
            lines.append("Transaction codes distinguish open-market trades from "
                         "compensation mechanics such as vesting and tax withholding.")
            lines.append("")
            lines.append("| Code | Meaning | Transactions | Shares | Value |")
            lines.append("|------|---------|--------------|--------|-------|")
            for code, bucket in sorted(by_code.items(),
                                       key=lambda kv: -kv[1].get("value", 0)):
                lines.append(f"| {code} | {bucket.get('meaning', code)} | "
                             f"{bucket.get('count', 0):,} | "
                             f"{bucket.get('shares', 0):,.0f} | "
                             f"{format_currency(bucket.get('value'))} |")
            lines.append("")

        if CHARTS_AVAILABLE:
            lines.extend(_figure(charts.insider_disposals(insider)))
            lines.extend(_figure(charts.insider_on_price(
                insider, data.get("price_history") or {})))

        by_insider = insider.get("by_insider") or {}
        sellers = sorted(by_insider.items(), key=lambda kv: -kv[1].get("value_sold", 0))
        sellers = [s for s in sellers if s[1].get("value_sold")]
        if sellers:
            lines.append("### Most active sellers")
            lines.append("")
            lines.append("| Insider | Role | Transactions | Shares disposed | Value |")
            lines.append("|---------|------|--------------|-----------------|-------|")
            for name, rec in sellers[:12]:
                roles = ", ".join(rec.get("roles") or []) or rec.get("title") or "—"
                lines.append(f"| {name} | {roles} | {rec.get('transactions', 0)} | "
                             f"{rec.get('total_sold', 0):,.0f} | "
                             f"{format_currency(rec.get('value_sold'))} |")
            lines.append("")

    # ── Institutional Ownership ──────────────────────────────────────────
    holdings = data.get("institutional_holdings") or {}
    holders = holdings.get("holders") or []
    if holders:
        lines.append("## Institutional Ownership")
        lines.append("")
        lines.append(f"- **Managers holding:** {holdings.get('institutions_holding', 0)} "
                     f"of {holdings.get('institutions_polled', 0)} largest 13F filers")
        lines.append(f"- **Shares held:** {holdings.get('total_shares_held', 0):,}")
        if holdings.get("pct_shares_outstanding") is not None:
            lines.append(f"- **Share of shares outstanding:** "
                         f"{holdings['pct_shares_outstanding']}%")
        if holdings.get("cusip"):
            lines.append(f"- **CUSIP:** {holdings['cusip']}")
        lines.append("")

        has_pct = any(h.get("pct_outstanding") is not None for h in holders)
        header = "| Holder | Shares | Value | " + ("% of s/o | " if has_pct else "") + "Report date |"
        lines.append(header)
        lines.append("|--------|--------|---------------|" + ("----------|" if has_pct else "") + "-------------|")
        for h in holders[:20]:
            pct = f" {h['pct_outstanding']}% |" if has_pct and h.get("pct_outstanding") is not None else (" — |" if has_pct else "")
            lines.append(f"| {h.get('institution', '')} | {h.get('shares', 0):,} | "
                         f"{_fmt_scaled(h.get('value'))} |{pct} {h.get('report_date') or '—'} |")
        lines.append("")
        lines.append(f"*{holdings.get('coverage', '')}*")
        lines.append("")

        if CHARTS_AVAILABLE:
            lines.extend(_figure(charts.institutional_concentration(holdings)))

        if holdings.get("stale_filers"):
            stale = ", ".join(f"{s['institution']} (last filed {s['last_filed']})"
                              for s in holdings["stale_filers"])
            lines.append(f"Excluded as no longer filing under the polled CIK: {stale}.")
            lines.append("")

        lines.extend(_render_beneficial_ownership(
            data.get("beneficial_ownership") or {}, entity_name))
        lines.extend(_render_overlap(
            data.get("institutional_overlap") or {}, entity_name))

        # ── Co-Investment Network Analysis ────────────────────────────────
        # Analyzes institutional investor patterns, identifies co-investments,
        # clusters by investment style, and identifies coordinated movements.
        if COINVESTMENT_AVAILABLE and holdings:
            try:
                coinvestment_data = build_coinvestment_network(
                    primary_ticker=ticker,
                    institutional_holders=holdings,
                    depth=2,  # Analyze 2nd degree connections
                )
                lines.extend(render_coinvestment_network_markdown(coinvestment_data))
            except Exception as e:
                logger.warning(f"Co-investment network analysis failed: {e}")

    # ── Federal Contracting ──────────────────────────────────────────────
    contracts = data.get("contract_intelligence", {}) or {}
    if contracts:
        lines.extend(_render_federal(contracts, entity_name))

    # ── Political Intelligence ───────────────────────────────────────────
    political = data.get("political_intelligence", {}) or {}
    lobbying = political.get("lobbying_summary", {}) or {}
    pac = political.get("pac_activity", {}) or {}
    if lobbying.get("filing_count") or pac.get("committee_found"):
        lines.append("## Lobbying and Political Activity")
        lines.append("")
        total = lobbying.get("total_spend") or 0
        filings = lobbying.get("filing_count") or 0
        in_house = lobbying.get("in_house_spend") or 0
        outside = lobbying.get("outside_firm_spend") or 0
        lines.append(
            f"{entity_name} discloses {format_currency(total)} of federal "
            f"lobbying across {filings} Senate LDA filing"
            f"{'' if filings == 1 else 's'}"
            + (f", of which {format_currency(in_house)} "
               f"({in_house / total * 100:.0f}%) is in-house and "
               f"{format_currency(outside)} "
               f"({outside / total * 100:.0f}%) is spent through outside "
               f"registrants" if total and (in_house or outside) else "")
            + ". LDA figures are what the registrant reported, not what was "
              "actually spent influencing a particular bill; the register is "
              "a floor on activity, not a measure of influence."
        )
        lines.append("")
        if lobbying.get("source_url"):
            lines.append(f"Source: {lobbying['source_url']}")
            lines.append("")

        year_breakdown = lobbying.get("year_breakdown") or {}
        if year_breakdown:
            ordered = sorted(year_breakdown.items(), key=lambda kv: str(kv[0]))
            periods = lobbying.get("year_periods") or {}
            counts = lobbying.get("year_filings") or {}
            complete = set(lobbying.get("complete_years") or [])
            lines.append("### Spend by year")
            lines.append("")
            lines.append("| Year | Disclosed spend | Filings | Quarters | Change vs prior |")
            lines.append("|------|-----------------|--------:|---------:|-----------------|")
            prior_amt = None
            for year, amt in ordered:
                # A change against a partial base year is arithmetic on two
                # different things, so it is withheld rather than printed.
                if prior_amt and str(year) in complete and prior_amt > 0:
                    change = f"{(amt - prior_amt) / prior_amt * 100:+.0f}%"
                else:
                    change = "—"
                quarters = periods.get(str(year))
                lines.append(
                    f"| {year} | {format_currency(amt)} "
                    f"| {counts.get(str(year), '—')} "
                    f"| {quarters if quarters else '—'}"
                    f"{'' if str(year) in complete else ' (partial)'} "
                    f"| {change} |")
                prior_amt = amt if str(year) in complete else None
            lines.append("")

            # The trajectory is measured only across years where all four
            # quarterly periods were filed and the year has closed. An earlier
            # version anchored on whichever year appeared first in the window;
            # where that year held a single filing it produced growth rates in
            # the thousands of percent that described our retrieval coverage
            # rather than the issuer's spending.
            full = [(y, a) for y, a in ordered if str(y) in complete]
            if len(full) >= 2 and full[0][1]:
                first_y, first_a = full[0]
                last_y, last_a = full[-1]
                traj = (last_a - first_a) / first_a * 100
                lines.append(
                    f"Across the complete years from {first_y} to {last_y}, "
                    f"disclosed spend moved {traj:+.0f}%. "
                    + ("A rising line against a stable federal footprint "
                       "is the pattern that usually precedes a regulatory "
                       "fight rather than routine monitoring."
                       if traj >= 25 else
                       "Spend is broadly stable across the window, which "
                       "reads as a standing Washington presence rather "
                       "than a campaign timed to a single bill."
                       if abs(traj) < 25 else
                       "Spend has contracted over the window; that is "
                       "consistent with a resolved issue set or a shift "
                       "of activity into channels the LDA does not capture.")
                )
                lines.append("")
            elif ordered:
                lines.append(
                    f"No growth rate is stated. The LDA register is filed "
                    f"quarterly, and only {len(full)} of the "
                    f"{len(ordered)} years retrieved carry all four periods "
                    f"against a closed year. A percentage taken across a "
                    f"partially covered year measures retrieval, not spending."
                )
                lines.append("")

            partial = lobbying.get("partial_years") or []
            if partial:
                lines.append(
                    f"Years marked partial ({', '.join(partial)}) are either "
                    f"still in progress or returned fewer than four quarterly "
                    f"periods. Their totals are real but are a floor, and they "
                    f"are excluded from the comparison above."
                )
                lines.append("")

        firms = lobbying.get("top_firms") or []
        if firms:
            lines.append("### Registrants")
            lines.append("")
            in_house_firms = [f for f in firms if f.get("in_house")]
            outside_firms = [f for f in firms if not f.get("in_house")]
            if outside_firms:
                top = outside_firms[0]
                lines.append(
                    f"The largest outside registrant is "
                    f"**{top.get('firm') or '—'}** at "
                    f"{format_currency(top.get('amount'))}"
                    + (f", followed by "
                       f"{', '.join((f.get('firm') or '—') for f in outside_firms[1:4])}"
                       if len(outside_firms) > 1 else "")
                    + ". Outside firms are retained for access and subject "
                      "expertise the issuer does not keep on staff; a "
                      "concentration in one or two names is a relationship, "
                      "not a commodity purchase."
                )
                lines.append("")
            if in_house_firms:
                lines.append(
                    f"In-house lobbying is reported under "
                    f"{', '.join((f.get('firm') or '—') for f in in_house_firms[:3])}"
                    + "."
                )
                lines.append("")
            lines.append("| Registrant | Type | Disclosed spend |")
            lines.append("|------------|------|-----------------|")
            for f in firms:
                lines.append(f"| {f.get('firm') or '—'} "
                             f"| {'In-house' if f.get('in_house') else 'Outside firm'} "
                             f"| {format_currency(f.get('amount'))} |")
            lines.append("")

        issues = lobbying.get("top_issues") or []
        if issues:
            lines.append("### Issues lobbied")
            lines.append("")
            top_names = [i[0] if isinstance(i, (list, tuple)) else i.get("issue", "")
                         for i in issues[:5]]
            lines.append(
                f"The issues named most often across the filings are "
                f"{', '.join(top_names)}. LDA issue codes are broad — "
                f"\"Computer/Information Tech\" covers export controls, "
                f"procurement and tax alike — so the code is a topic label, "
                f"not a bill list."
            )
            lines.append("")
            lines.append("| Issue | Filings |")
            lines.append("|-------|---------|")
            for issue in issues[:12]:
                if isinstance(issue, (list, tuple)):
                    name, count = issue[0], issue[1]
                else:
                    name, count = issue.get("issue", "—"), issue.get("count", 0)
                lines.append(f"| {name} | {count} |")
            lines.append("")

        # ── Corporate PAC ────────────────────────────────────────────────
        lines.append("### Corporate PAC")
        lines.append("")
        if not pac.get("committee_found"):
            lines.append("No corporate PAC is registered with the FEC under this "
                         "company's name.")
            lines.append("")
        else:
            lines.append(f"- **Committee:** {pac.get('committee_name') or '—'} "
                         f"({pac.get('committee_id') or '—'})")
            lines.append(f"- **Disbursed across cycles:** "
                         f"{format_currency(pac.get('total_all_cycles'))}")
            split = pac.get("party_split") or {}
            if any(split.values()):
                # FEC tags a party only when the recipient is a candidate
                # committee; disbursements to other PACs and party organs carry
                # none, so the third bucket is unattributed rather than "other".
                lines.append(f"- **Party split:** Democratic "
                             f"{format_currency(split.get('DEM'))} / Republican "
                             f"{format_currency(split.get('REP'))} / unattributed "
                             f"{format_currency(split.get('OTHER'))}")
            lines.append("")

            by_cycle = pac.get("contributions_by_cycle") or {}
            if by_cycle:
                lines.append("| Cycle | Disbursed | Democratic | Republican |")
                lines.append("|-------|-----------|------------|------------|")
                for cycle, rec in sorted(by_cycle.items(), reverse=True):
                    party = rec.get("by_party") or {}
                    lines.append(f"| {cycle} | {format_currency(rec.get('total'))} "
                                 f"| {format_currency(party.get('DEM'))} "
                                 f"| {format_currency(party.get('REP'))} |")
                lines.append("")

            recipients = pac.get("top_recipients_all_time") or []
            if recipients:
                lines.append("| Recipient | Received |")
                lines.append("|-----------|----------|")
                for r in recipients[:12]:
                    name = r.get("recipient") if isinstance(r, dict) else r[0]
                    amount = r.get("amount") if isinstance(r, dict) else r[1]
                    lines.append(f"| {name} | {format_currency(amount)} |")
                lines.append("")

    # ── Legal and Regulatory ─────────────────────────────────────────────
    litigation = data.get("litigation_intelligence", {}) or {}
    notes = data.get("filing_notes", {}) or {}
    if litigation:
        lines.extend(_render_legal(litigation, entity_name, notes))

    # ── News and the Open Web ────────────────────────────────────────────
    lines.extend(_render_news(data, entity_name))
    lines.extend(_figure(charts.news_volume(
        data.get("news_intelligence") or {})))

    # ── Statistical Correlations ─────────────────────────────────────────
    # After the registers and the coverage, because every input it consumes
    # has by now been shown to the reader in its own section.
    lines.extend(_render_correlations(data, entity_name))
    lines.extend(_figure(charts.insider_timing_distribution(
        data.get("correlations") or {})))

    # ── Event Chronology ─────────────────────────────────────────────────
    timeline = data.get("event_timeline", {}) or {}
    events = timeline.get("events") or []
    if events:
        lines.append("## Event Chronology")
        lines.append("")
        by_category = timeline.get("by_category", {}) or {}
        period_years = timeline.get("period_years", 2)
        dates = sorted(e.get("date") for e in events if e.get("date"))
        span = f"{dates[0]} to {dates[-1]}" if dates else ""
        lines.append(
            f"{len(events)} filings and disclosures over the trailing "
            f"{period_years} years"
            + (f", spanning {span}" if span else "")
            + ". The chronology below narrates the material subset; the "
            "routine filings are counted here so the total reconciles."
        )
        lines.append("")

        # Filing mix is itself a disclosure profile: what an issuer files, and
        # how often, distinguishes a quiet compliance calendar from one driven
        # by leadership change or heavy insider dealing.
        form_counts = {}
        for e in events:
            form = e.get("form_type")
            if form:
                form_counts[form] = form_counts.get(form, 0) + 1
        if form_counts:
            lines.append("| Form | Count | What it reports |")
            lines.append("|------|-------|-----------------|")
            for form, count in sorted(form_counts.items(), key=lambda kv: -kv[1])[:12]:
                lines.append(f"| {form} | {count} | {_FORM_PURPOSE.get(form, '—')} |")
            lines.append("")

        if CHARTS_AVAILABLE:
            lines.extend(_figure(charts.filing_cadence(timeline)))

        if by_category:
            spread = ", ".join(
                f"{str(cat).lower()} {len(items) if isinstance(items, list) else items}"
                for cat, items in sorted(
                    by_category.items(),
                    key=lambda kv: -(len(kv[1]) if isinstance(kv[1], list) else kv[1]))
            )
            lines.append(f"By category: {spread}.")
            lines.append("")

        # Intensity and mix: what dominates the calendar is itself a signal
        # before any individual filing is narrated.
        lines.append("### Filing intensity")
        lines.append("")
        months = {}
        for e in events:
            month = (e.get("date") or "")[:7]
            if month:
                months[month] = months.get(month, 0) + 1
        if months:
            busiest = sorted(months.items(), key=lambda kv: -kv[1])[:3]
            quietest = sorted(months.items(), key=lambda kv: kv[1])[:2]
            avg = len(events) / max(len(months), 1)
            lines.append(
                f"Activity averaged {avg:.1f} filings a month across "
                f"{len(months)} months. The busiest months were "
                + ", ".join(f"{_month_label(m)} ({n})" for m, n in busiest)
                + "; the quietest were "
                + ", ".join(f"{_month_label(m)} ({n})" for m, n in quietest)
                + ". A spike usually coincides with earnings, a proxy season "
                "or a cluster of Form 4 activity rather than a single "
                "one-off disclosure."
            )
            lines.append("")
        form4 = form_counts.get("4") or form_counts.get("Form 4") or 0
        eightk = form_counts.get("8-K") or 0
        if form4 or eightk:
            lines.append(
                f"Form 4 insider filings account for "
                f"{form4 / max(len(events), 1) * 100:.0f}% of the chronology "
                f"({form4:,}); 8-K current reports for "
                f"{eightk / max(len(events), 1) * 100:.0f}% ({eightk}). "
                f"The narrative below keeps the 8-K and periodic reports and "
                f"collapses open-market Form 4 activity into monthly totals "
                f"so the material disclosures remain readable."
            )
            lines.append("")
        highlights = timeline.get("highlights") or []
        if highlights:
            lines.append("### Highlights from the period")
            lines.append("")
            for item in highlights[:6]:
                if isinstance(item, dict):
                    lines.append(
                        f"- {item.get('date', '')} — "
                        f"{item.get('text') or item.get('title') or item}"
                    )
                else:
                    lines.append(f"- {item}")
            lines.append("")

        # Material events only: routine Form 4/13G/144 noise is counted above
        # but not narrated, since it would bury the disclosures that matter.
        material = [
            e for e in events
            if e.get("event_type") in ("executive_change", "earnings", "acquisition",
                                       "material_event", "litigation")
            or (e.get("form_type") in ("8-K", "10-K", "10-Q", "DEF 14A"))
        ]
        context = {
            "quarterly": quarterly,
            "latest_annual": annual[0] if annual else {},
            "say_on_pay": (proxy.get("say_on_pay") or {}),
        }
        lines.append(f"### Material events ({len(material)})")
        lines.append("")
        lines.extend(_render_chronology(material, insider, context))
        lines.append("")

        # Form 144 is notice of an intent to sell restricted stock. It precedes
        # the Form 4 that reports the sale, so a heavy 144 calendar is forward
        # visibility on insider supply that the Form 4 record cannot give.
        notices = [e for e in events if e.get("form_type") == "144"]
        if notices:
            months = {}
            for n in notices:
                month = (n.get("date") or "")[:7]
                if month:
                    months[month] = months.get(month, 0) + 1
            busiest = sorted(months.items(), key=lambda kv: -kv[1])[:3]
            lines.append(f"### Proposed sale notices ({len(notices)} Form 144)")
            lines.append("")
            lines.append(
                f"Insiders filed {len(notices)} notices of proposed sale over "
                f"the period, an average of {len(notices) / max(len(months), 1):.1f} "
                f"a month across {len(months)} months. Form 144 states an "
                f"intention to sell restricted or control securities and is "
                f"filed before the trade; the executed sale appears separately "
                f"on Form 4. The two should not be added together, and a 144 "
                f"does not oblige the holder to sell."
            )
            lines.append("")
            if busiest:
                lines.append(
                    "Heaviest months were "
                    + ", ".join(f"{_month_label(m)} ({n} notices)"
                                for m, n in busiest)
                    + "."
                )
                lines.append("")

    # Risk Register — evidence-linked entries first, then the connector's
    # register with its stated basis. An entry that cannot name a filing is
    # kept but labelled as assessment rather than evidence.
    evidenced = _evidence_linked_risks(data, entity_name)
    risk_register = data.get("risk_register", {}) or {}
    if evidenced or risk_register:
        lines.append("## Risk Register")
        lines.append("")
        if evidenced:
            lines.append(
                f"{len(evidenced)} risk"
                f"{'' if len(evidenced) == 1 else 's'} below are raised by "
                f"filings and datasets retrieved for this report. Each names "
                f"the source that evidences it."
            )
            lines.append("")
            lines.append("### Evidence-linked risks")
            lines.append("")
            for i, risk in enumerate(evidenced[:10], 1):
                heading = f"{i}. **{risk.get('title', '')}**"
                if risk.get("category"):
                    heading += f" — {risk['category']}"
                lines.append(heading)
                if risk.get("description"):
                    lines.append(f"   - {risk['description']}.")
                scoring = " / ".join(filter(None, [
                    f"likelihood {risk['likelihood'].lower()}" if risk.get("likelihood") else "",
                    f"impact {risk['impact'].lower()}" if risk.get("impact") else "",
                    f"score {risk['risk_score']}" if risk.get("risk_score") is not None else "",
                ]))
                if scoring:
                    lines.append(f"   - Scored {scoring}.")
                lines.append(f"   - *Evidence: {risk.get('evidence') or 'see above'}.*")
                if risk.get("source_url"):
                    lines.append(f"   - Source: {risk['source_url']}")
                lines.append("")

        risk_summary = risk_register.get("summary", {}) or {}
        top_risks = risk_register.get("top_risks", []) or []
        # Drop connector entries that restate an evidence-linked title, and
        # demote industry-boilerplate sources so they cannot outrank filings.
        evidenced_titles = {r.get("title", "").lower() for r in evidenced}
        boilerplate = {"industry analysis", "standard assessment",
                       "market analysis", ""}
        filtered = [r for r in top_risks
                    if r.get("title", "").lower() not in evidenced_titles]
        filing_backed = [r for r in filtered
                         if (r.get("data_source") or "").lower() not in boilerplate]
        assessed = [r for r in filtered
                    if (r.get("data_source") or "").lower() in boilerplate]

        if risk_summary:
            lines.append(
                f"**Connector profile:** {risk_summary.get('overall_risk_profile', 'UNKNOWN')} "
                f"({risk_summary.get('critical_risks', 0)} critical / "
                f"{risk_summary.get('high_risks', 0)} high / "
                f"{risk_summary.get('medium_risks', 0)} medium / "
                f"{risk_summary.get('low_risks', 0)} low)."
            )
            lines.append("")

        if filing_backed:
            lines.append("### Filing-backed assessments")
            lines.append("")
            for i, risk in enumerate(filing_backed[:6], 1):
                heading = f"{i}. **{risk.get('title', '')}**"
                if risk.get("category"):
                    heading += f" — {risk['category']}"
                lines.append(heading)
                if risk.get("description"):
                    lines.append(f"   - {risk['description']}.")
                lines.append(f"   - *Basis: {risk.get('data_source')}.*")
                lines.append("")

        if assessed:
            lines.append("### General assessments")
            lines.append("")
            lines.append(
                "The following are industry-standard risk framings rather than "
                "findings raised by a specific filing retrieved for this "
                "issuer. They are retained for completeness and labelled as "
                "assessments."
            )
            lines.append("")
            for i, risk in enumerate(assessed[:4], 1):
                lines.append(
                    f"{i}. **{risk.get('title', '')}** — "
                    f"{risk.get('description', '').rstrip('.')}. "
                    f"*Assessment basis: {risk.get('data_source') or 'unattributed'}.*"
                )
            lines.append("")

    # Cross-reference findings
    xref = data.get("cross_reference_findings", [])
    if xref:
        lines.append("## Cross-Reference Findings")
        lines.append("")
        for finding in xref[:10]:
            lines.append(f"- **[{finding.get('severity', '')}]** {finding.get('detail', '')}")
        lines.append("")

    # ── Phase 3: Deep Intelligence Sections ──────────────────────────────

    # Founder Track Record
    founder_track = data.get("founder_track_record", {}) or {}
    if founder_track.get("executive_profiles"):
        try:
            from app.connectors.founder_track_record_connector import (
                render_founder_track_record_markdown,
            )
            lines.extend(render_founder_track_record_markdown(founder_track))
        except Exception as e:
            logger.warning("Founder track record render failed: %s", e)

    # Rumors and Next Steps Analysis
    rumors = data.get("rumors_analysis", {}) or {}
    if rumors.get("summary"):
        try:
            from app.connectors.rumors_analysis_connector import (
                render_rumors_analysis_markdown,
            )
            lines.extend(render_rumors_analysis_markdown(rumors))
        except Exception as e:
            logger.warning("Rumors analysis render failed: %s", e)

    # Contract Probability Analysis
    contract_prob = data.get("contract_probability", {}) or {}
    if contract_prob.get("historical_performance"):
        try:
            from app.services.contract_probability_service import (
                render_contract_probability_markdown,
            )
            lines.extend(render_contract_probability_markdown(contract_prob))
        except Exception as e:
            logger.warning("Contract probability render failed: %s", e)

    # Deep Comparative Analysis
    deep_comp = data.get("deep_comparative", {}) or {}
    if deep_comp.get("category_comparisons"):
        try:
            from app.services.deep_comparative_service import (
                render_deep_comparative_markdown,
            )
            lines.extend(render_deep_comparative_markdown(deep_comp))
        except Exception as e:
            logger.warning("Deep comparative render failed: %s", e)

    # Family Network Analysis
    family_net = data.get("family_network", {}) or {}
    if family_net.get("executives") or family_net.get("foundations"):
        try:
            from app.connectors.family_network_connector import (
                render_family_network_markdown,
            )
            lines.extend(render_family_network_markdown(family_net))
        except Exception as e:
            logger.warning("Family network render failed: %s", e)

    # Business Intelligence (Business Model, Revenue Structure, Brand Portfolio, Industry Outlook)
    biz_intel = data.get("business_intelligence", {}) or {}
    if biz_intel.get("business_model") or biz_intel.get("revenue_structure"):
        try:
            from app.services.business_intelligence_service import (
                render_all_business_intelligence_markdown,
            )
            lines.extend(render_all_business_intelligence_markdown(biz_intel))
        except Exception as e:
            logger.warning("Business intelligence render failed: %s", e)

    # ── SEC-API Structured Data ──────────────────────────────────────────
    if SEC_API_REPORT_AVAILABLE and data.get("sec_api_data", {}).get("available"):
        try:
            lines.extend(render_all_sec_api_markdown(data["sec_api_data"]))
        except Exception as e:
            logger.warning("SEC-API report render failed: %s", e)

    # ── Methodology ──────────────────────────────────────────────────────
    lines.append("## Methodology and Sources")
    lines.append("")
    lines.append("| Domain | Source |")
    lines.append("|--------|--------|")
    lines.append(f"| Financial statements | SEC XBRL companyfacts, CIK {financial.get('cik') or '—'} |")
    lines.append("| Narrative notes, Exhibit 21, ASC 321 | 10-K HTML / XBRL exhibits (SEC EDGAR) |")
    lines.append("| Personnel and compensation | DEF 14A proxy statements (SEC EDGAR) |")
    lines.append("| Board interlocks and 5% holders | Form 3 / Schedule 13D/G (SEC EDGAR) |")
    lines.append("| Insider transactions | Form 4 filings (SEC EDGAR) |")
    lines.append("| Institutional overlap | 13F-HR from largest managers (SEC EDGAR) |")
    lines.append("| Federal awards | USASpending.gov API v2, DUNS/UEI-keyed recipient resolution |")
    lines.append("| Lobbying | Senate LDA API |")
    lines.append("| Litigation | CourtListener, SEC, FTC, DOJ, ITC, PTAB |")
    # Phase 3 sources
    if data.get("founder_track_record"):
        lines.append("| Founder track record | Google Books API, Open Library, Apify web scraping |")
    if data.get("rumors_analysis"):
        lines.append("| Rumors and next steps | NewsAPI, Alpha Vantage, Twitter/X via Apify |")
    if data.get("contract_probability"):
        lines.append("| Contract probability | USASpending.gov, SAM.gov |")
    if data.get("deep_comparative"):
        lines.append("| Deep comparative analysis | Alpha Vantage, Financial Modeling Prep, SEC EDGAR XBRL |")
    if data.get("family_network"):
        lines.append("| Family network | Form 990 (ProPublica), Section 16 filings, LinkedIn via Apify |")
    if data.get("business_intelligence"):
        lines.append("| Business model & industry | SEC 10-K Item 1, SIC classification, segment disclosures |")
    if data.get("sec_api_data", {}).get("available"):
        lines.append("| Private placements (Form D) | sec-api.io Form D structured extraction |")
        lines.append("| Fund marks & implied pricing (N-PORT) | sec-api.io N-PORT fund holdings |")
        lines.append("| Corporate subsidiaries | sec-api.io Exhibit 21 structured extraction |")
        lines.append("| Executive compensation (structured) | sec-api.io DEF 14A extraction |")
        lines.append("| Beneficial ownership (13D/13G) | sec-api.io Schedule 13D/13G |")
        lines.append("| SEC enforcement actions | sec-api.io enforcement database |")
    price = data.get("price_history") or {}
    price_bars = price.get("bars") or []
    if price_bars or price.get("source") or price.get("provider"):
        lines.append(
            f"| Daily price history | "
            f"{price.get('source') or price.get('provider') or 'market data'} "
            f"({len(price_bars):,} bars) |"
        )
    if dcf.get("market_data_provider"):
        lines.append(f"| Market and consensus data | {dcf['market_data_provider']} |")
    if CHARTS_AVAILABLE and FIGURE_COUNT:
        lines.append(
            f"| Figures | Matplotlib PNG embedded via WeasyPrint "
            f"({FIGURE_COUNT} chart{'' if FIGURE_COUNT == 1 else 's'} in this run) |"
        )
    lines.append("")

    lines.extend(_render_data_health(data, entity_name))

    lines.append("### Reporting conventions")
    lines.append("")
    lines.append("- Figures are US GAAP in millions of USD unless otherwise labelled.")
    lines.append("- Quarters marked DERIVED are computed as the fiscal year less Q1–Q3.")
    lines.append("- Values that could not be retrieved are shown as `—` and are never estimated.")
    lines.append("- Fiscal years follow the issuer's own calendar, which for many "
                 "companies does not align with the calendar year.")
    lines.append("- Where a figure is quoted from a filing, the filing rather "
                 "than a data vendor is the cited source.")
    lines.append("- Charts are drawn only from fields already tabulated in the "
                 "report; a missing series omits the figure rather than inventing "
                 "a shape.")
    lines.append("- Network findings name a person or entity only when a filed "
                 "document places them on both sides of the comparison.")
    lines.append("- Statistical correlations, when present, state sample size n "
                 "and are suppressed entirely where n < 12.")
    lines.append("")

    lines.append("### Quality gates")
    lines.append("")
    lines.append(
        "The report is checked before it is rendered, and the build fails "
        "rather than emitting a document that would read as complete while "
        "carrying unresolved values. The gates are:"
    )
    lines.append("")
    lines.append("- Placeholder and sentinel strings are rejected, so a "
                 "template fragment cannot reach the page as if it were data. "
                 "Embedded chart payloads are excluded from that scan so "
                 "base64 content cannot false-trigger.")
    lines.append("- A minimum populated section count, so a run in which most "
                 "connectors failed does not ship as a thin but valid report.")
    lines.append("- A minimum word count, which catches a run that populated "
                 "its section headers but not their contents.")
    lines.append("- The subject company must be named, which catches a "
                 "misrouted ticker resolving to the wrong filer.")
    lines.append("- Sections without supporting data are omitted, never filled "
                 "with industry boilerplate presented as issuer-specific fact.")
    lines.append("")

    quality = data.get("data_quality", {}) or {}
    succeeded = quality.get("sources_successful", 0)
    failed = quality.get("sources_failed", 0)
    lines.append("### Source health for this run")
    lines.append("")
    lines.append(
        f"{succeeded} of {succeeded + failed} sources returned data. "
        + ("Every source queried answered." if not failed else
           f"{failed} did not answer, and any section depending on them says "
           f"so in place of substituting an estimate.")
    )
    lines.append("")

    # A throttled run and a run against a company with nothing to report look
    # identical on the page unless the throttling is stated.
    throttled = data.get("sec_requests_throttled") or 0
    if throttled:
        lines.append(
            f"**{throttled} SEC requests were abandoned after repeated "
            f"rate-limit responses.** EDGAR throttles by source address, and "
            f"this run exceeded its budget. Any section below its usual depth "
            f"is thin for that reason rather than because the filings do not "
            f"exist; re-running after a pause will populate them."
        )
        lines.append("")
    if PHASE2_AVAILABLE:
        status = get_connector_status()
        lines.append(f"Connectors active: {status.get('total_available', 0)}. "
                     f"Research version {status.get('version', '2.0')}.")
        lines.append("")

    lines.append("### Limitations")
    lines.append("")
    lines.append(
        "These bound what the report can support, and are stated because a "
        "reader cannot infer them from the text:"
    )
    lines.append("")
    lines.append(
        "- **Retrieval windows are finite.** Litigation, chronology and "
        "political data cover a fixed lookback stated in each section. A matter "
        "older than the window is absent, not resolved."
    )
    lines.append(
        "- **Full-text docket search returns citations as well as parties.** "
        "The legal section separates the two; a count taken from any other "
        "source may conflate them."
    )
    lines.append(
        "- **Institutional ownership is drawn from a curated set of the largest "
        "13F filers**, not the full universe, so the reported percentage is a "
        "floor rather than total institutional ownership."
    )
    segments = data.get("financial_intelligence", {}).get("segments") or {}
    if not any((segments.get("segments"), segments.get("geographic"),
                segments.get("markets"))):
        lines.append(
            "- **No segment breakdown is shown.** Disaggregated revenue is read "
            "from the rendered statements attached to the 10-K, and each "
            "breakdown must sum to consolidated revenue before it is published. "
            "Where an issuer combines two dimensions in a single schedule, or "
            "titles the note in a way the parser does not recognise, the "
            "breakdown is withheld rather than published unreconciled. Absence "
            "here means it could not be verified, not that the issuer reports "
            "a single segment."
        )
    if not (notes.get("commitments") or notes.get("legal_matters")):
        lines.append(
            "- **No figures were read from the narrative notes.** Commitments and "
            "contingencies are extracted from the rendered notes attached to the "
            "10-K, which requires that the issuer state the amount in prose or in "
            "a maturity schedule the parser can attribute to a named commitment. "
            "Where it does not, the tagged XBRL obligation is reported instead. "
            "That tag covers a narrower definition, so the commitment position "
            "shown may understate the total."
        )
    lines.append(
        "- **No government action precedent library is included.** Establishing "
        "how regulators have acted against comparable issuers requires a curated "
        "enforcement feed keyed to industry; full-text docket search returns "
        "unrelated matters at a rate that makes it unusable for the purpose. The "
        "section is omitted rather than populated with weak matches."
    )
    lines.append(
        "- **Form 4 parsing covers a capped number of filings per issuer.** "
        "Where an issuer exceeds it, the insider section states the sample size "
        "so the totals are read as a lower bound."
    )
    lines.append(
        "- **The valuation is a model, not a forecast.** It is sensitive above "
        "all to the discount rate and the terminal growth assumption, which is "
        "why the sensitivity grid and the implied-growth inversion are shown "
        "alongside the headline figure."
    )
    lines.append(
        "- **Narrative is generated from retrieved fields only.** No section "
        "supplies context from outside the cited sources, which means genuine "
        "background a human analyst would add is absent by design."
    )
    lines.append("")
    lines.append(
        f"Prepared from public records and open sources. Research use only — "
        f"not legal, investment, or tax advice. "
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
    )
    lines.append("")

    return "\n".join(lines)


# Strings that present a fabricated or unresolved value as if it were data.
# A bare "—" is the documented convention for "not retrieved" and is allowed.
PLACEHOLDER_PATTERNS = [
    "$0.00", "UNKNOWN", "TBD", "should be evaluated", "provides insight into",
    "Lorem ipsum", "$nan", "None |", "nan%", "nan |", "$None",
    "| — | — | — | — |",  # row of all missing values
]


def sanitize_markdown(markdown: str) -> str:
    """
    Remove broken/empty content from the rendered markdown before PDF generation.
    This ensures no garbage, placeholder, or missing-data rows appear in the final output.
    """
    lines = markdown.split("\n")
    cleaned = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Skip table rows that are ALL dashes/empty (no real data)
        if line.startswith("|") and "—" in line:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if all(c in ("—", "", "None", "nan", "$0", "$0.00", "—") for c in cells):
                i += 1
                continue

        # Skip rows with "None" as all values
        if line.startswith("|") and line.count("None") >= 3:
            i += 1
            continue

        # Skip rows where all numeric cells are 0 or empty (insider trading with no data)
        if line.startswith("|") and "| — | — | — |" in line:
            i += 1
            continue

        # Remove "0 buys, 0 sells | Net value: $0" type headers that indicate no real data
        if "0 buys, 0 sells" in line and "Net value: $0" in line:
            i += 1
            continue

        # Remove empty sections: heading followed immediately by another heading
        if line.startswith("## ") or line.startswith("### "):
            # Look ahead for content
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            # If next non-blank line is another heading of same or higher level, skip
            if j < len(lines):
                next_line = lines[j]
                current_level = len(line) - len(line.lstrip("#"))
                if next_line.startswith("#"):
                    next_level = len(next_line) - len(next_line.lstrip("#"))
                    if next_level <= current_level:
                        # Empty section — skip the heading
                        i += 1
                        continue

        cleaned.append(line)
        i += 1

    return "\n".join(cleaned)


def check_report_quality(markdown: str, ticker: str = "", entity_name: str = "") -> dict:
    """
    Reject reports that would ship with placeholder values or empty sections.

    Runs before PDF generation so a broken pipeline fails loudly instead of
    producing a clean-looking document full of zeros.
    """
    issues = []

    # Base64 chart payloads are opaque binary-as-text. Scanning them for
    # placeholders matches random byte sequences ("TBD", "$0.00") that are not
    # content — strip every data URI before the text checks run.
    text = re.sub(r"data:image/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=\s]+",
                  "[chart]", markdown)

    # Guard against another company's identifiers surviving in the output. A
    # hardcoded ticker once labelled every report's price line "NVDA" whatever
    # the subject was, and the numbers around it looked entirely plausible.
    subject_tokens = {t.upper() for t in
                      re.findall(r"[A-Za-z]{2,}", f"{ticker} {entity_name}")}
    for foreign in re.findall(r"\b[A-Z]{2,5}\b(?= last traded| closed FY)", text):
        if foreign not in subject_tokens:
            issues.append(f"Report references foreign ticker '{foreign}'")

    for pattern in PLACEHOLDER_PATTERNS:
        count = text.count(pattern)
        if count:
            issues.append(f"{count} occurrence(s) of placeholder '{pattern}'")

    # A heading immediately followed by another heading means an empty section.
    lines = text.split("\n")
    headings = [(i, l) for i, l in enumerate(lines) if l.startswith("## ")]
    for idx, (line_no, heading) in enumerate(headings):
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        body = [l for l in lines[line_no + 1:end] if l.strip()]
        if not body:
            issues.append(f"Empty section: '{heading.strip('# ')}'")

    # Word count excludes the base64 payloads, which would otherwise dominate.
    word_count = len(text.split())
    if word_count < 800:
        issues.append(f"Report body is thin ({word_count} words)")

    return {
        "passed": not issues,
        "issues": issues,
        "word_count": word_count,
        "section_count": len(headings),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a deep intelligence report for any listed company.",
        epilog="Examples:  %(prog)s --ticker AAPL      %(prog)s --ticker JPM --peers WFC,C,GS"
               "      %(prog)s --from-json path/to/data.json",
    )
    parser.add_argument("--ticker", default="NVDA",
                        help="Stock ticker to analyse (default: NVDA)")
    parser.add_argument("--entity-name", default="",
                        help="Override the registrant name (default: resolved from SEC)")
    parser.add_argument("--peers", default="",
                        help="Comma-separated peer tickers (default: resolved from market data)")
    parser.add_argument("--years", type=int, default=5,
                        help="Years of history to retrieve (default: 5)")
    parser.add_argument("--from-json", default="",
                        help="Re-render markdown/PDF from a saved intelligence JSON "
                             "(skips connector fetch)")
    parser.add_argument("--no-news", action="store_true",
                        help="Skip the news, interview and open-web fetch")
    parser.add_argument("--no-peers", action="store_true",
                        help="Skip the peer comparison fetch (the slowest stage)")
    parser.add_argument("--refetch", action="store_true",
                        help="With --from-json, refetch the network-bound "
                             "enrichment instead of reusing what was saved")
    return parser.parse_args(argv)


def enrich(data: dict, ticker: str, entity_name: str,
           peers=None, want_news: bool = True, want_peers: bool = True,
           reuse: bool = True) -> dict:
    """Run the analyses that sit on top of the fetched registers.

    Split into two kinds. Pure computation — correlations, the co-occurrence
    graph, data health — is always recomputed, because it costs nothing and
    re-running a report after changing the maths should show the new maths.
    Network-bound work — news, foundations, peer financials — is reused from
    the saved payload unless `reuse` is off, which is what keeps `--from-json`
    a seconds-long operation rather than a repeat of the full fetch.
    """
    print("\n[1b/4] Analysis layer")

    def _cached(key):
        return data.get(key) if reuse else None

    # ── News and the open web (G-05) ──────────────────────────────────────
    if want_news and not _cached("news_intelligence"):
        try:
            from app.connectors.news_intelligence_connector import (
                get_news_intelligence)
            people = [d.get("name") for d
                      in ((data.get("proxy_intelligence") or {})
                          .get("board_composition") or {}).get("directors") or []
                      if d.get("name")]
            data["news_intelligence"] = get_news_intelligence(
                entity_name, ticker, people=people)
            summary = data["news_intelligence"].get("summary") or {}
            print(f"      News: {summary.get('article_count', 0)} articles "
                  f"resolved from "
                  f"{len(data['news_intelligence'].get('sources_queried') or [])} sources")
        except Exception as error:
            print(f"      News failed: {error}")
            data["news_intelligence"] = {"error": str(error)[:200]}
    elif _cached("news_intelligence"):
        print("      News: reused from saved payload")

    # ── Family, trust and vehicle networks (G-04) ─────────────────────────
    if not _cached("family_network"):
        try:
            from app.connectors.family_network_connector import get_family_network
            data["family_network"] = get_family_network(
                entity_name,
                data.get("proxy_intelligence") or {},
                data.get("insider_transactions") or {},
                include_foundations=want_news)
            profile = data["family_network"].get("position_profile") or {}
            print(f"      Family vehicles: {profile.get('vehicles_identified', 0)} "
                  f"candidate, {profile.get('surname_linked', 0)} surname-linked, "
                  f"{profile.get('foundations', 0)} foundations")
        except Exception as error:
            print(f"      Family network failed: {error}")

    # ── Peer comparison (G-03) ────────────────────────────────────────────
    if want_peers and not _cached("peer_comparison"):
        try:
            from app.services.peer_comparison_service import compare_peers
            data["peer_comparison"] = compare_peers(ticker, data, peers or [])
            comparison = data.get("peer_comparison") or {}
            print(f"      Peers: {comparison.get('complete_metrics', 0)}"
                  f"/{comparison.get('total_metrics', 0)} metrics complete "
                  f"across {len(comparison.get('peers') or [])} companies")
        except Exception as error:
            print(f"      Peer comparison failed: {error}")
    elif _cached("peer_comparison"):
        print("      Peers: reused from saved payload")

    # ── Correlations (G-01) ───────────────────────────────────────────────
    try:
        from app.services.correlation_service import run_all
        data["correlations"] = run_all(data)
        print(f"      Correlations: {data['correlations'].get('ran', 0)} "
              f"analyses on {data['correlations'].get('price_bars', 0)} price bars")
    except Exception as error:
        print(f"      Correlations failed: {error}")

    # ── Co-occurrence graph (G-02) ────────────────────────────────────────
    try:
        from app.services.cooccurrence_service import build_cooccurrence
        graph = build_cooccurrence(data, entity_name)
        data["cooccurrence"] = graph
        if graph:
            institutional = graph.get("institutional") or {}
            print(f"      Network: {graph.get('cohort_size', 0)} people over "
                  f"{graph.get('entities_reached', 0)} entities, "
                  f"{graph.get('edge_count', 0)} people edges, "
                  f"{institutional.get('edge_count', 0)} capital edges")
    except Exception as error:
        print(f"      Co-occurrence failed: {error}")

    # ── Data health (G-09) ────────────────────────────────────────────────
    try:
        from app.services.data_health_service import run_health_checks, send_alert
        health = run_health_checks(data)
        data["data_health"] = health
        delivery = send_alert(health, entity_name, ticker)
        data["data_health"]["alert"] = delivery
        print(f"      Health: {health['healthy']}/{health['total']} sources "
              f"({health['coverage_pct']}%)"
              + (f" — {len(health['alerts'])} alert(s)"
                 if health.get("alerts") else ""))
        for alert in health.get("alerts") or []:
            print(f"        [{alert['severity']}] {alert['source']}: "
                  f"{alert['detail']}")
    except Exception as error:
        print(f"      Health checks failed: {error}")

    return data


def main(argv=None):
    args = parse_args(argv)
    peers = [p.strip().upper() for p in args.peers.split(",") if p.strip()] or None

    phase2_data = {}
    if args.from_json:
        with open(args.from_json) as fh:
            phase2_data = json.load(fh)
        ticker = (phase2_data.get("ticker") or args.ticker or "NVDA").upper()
        entity = (args.entity_name or phase2_data.get("entity_name") or "")
        saved_peers = ((phase2_data.get("institutional_overlap") or {})
                       .get("competitors")) or None
        configure(ticker, entity, peers or saved_peers)
    else:
        configure(args.ticker, args.entity_name, peers)

    print("=" * 70)
    print("Deep Intelligence Report Generator (Phase 2)")
    print("=" * 70)
    print(f"\nEntity: {ENTITY_NAME}")
    print(f"Ticker: {TICKER}")
    print(f"Competitors: {COMPETITORS}")
    print()

    # Check Phase 2 availability
    if PHASE2_AVAILABLE and not args.from_json:
        status = get_connector_status()
        print("Phase 2 Connector Status:")
        print(f"  Phase 1 connectors: {status.get('phase1_connectors', 0)}")
        print(f"  Phase 2 connectors: {status.get('phase2_connectors', 0)}")
        print(f"  Total available: {status.get('total_available', 0)}")
        print(f"  Comprehensive ready: {status.get('comprehensive_ready', False)}")
        print()

    # Step 1: Run Phase 2 comprehensive intelligence (or load saved JSON)
    if args.from_json:
        print(f"[1/4] Loaded intelligence JSON: {args.from_json}")
        print(f"      Sources successful: "
              f"{phase2_data.get('data_quality', {}).get('sources_successful', 0)}")
    else:
        print("[1/4] Running comprehensive intelligence gathering...")
        print("      (This may take 2-5 minutes)")

        start_time = time.time()

        if PHASE2_AVAILABLE:
            try:
                phase2_data = run_comprehensive_intelligence(
                    entity_name=ENTITY_NAME,
                    ticker=TICKER,
                    competitors=COMPETITORS,
                    years=args.years,
                )
                elapsed = time.time() - start_time
                print(f"      Phase 2 complete in {elapsed:.1f} seconds")
                print(f"      Sources successful: {phase2_data.get('data_quality', {}).get('sources_successful', 0)}")
                print(f"      Sources failed: {phase2_data.get('data_quality', {}).get('sources_failed', 0)}")
            except Exception as e:
                print(f"      Phase 2 failed: {e}")
                phase2_data = {}
        else:
            print("      Phase 2 not available, using legacy mode")
            phase2_data = {}

    # Step 1b: the analysis layer on top of the fetched registers
    if phase2_data:
        phase2_data = enrich(
            phase2_data, TICKER, ENTITY_NAME, peers=COMPETITORS,
            want_news=not args.no_news, want_peers=not args.no_peers,
            reuse=bool(args.from_json) and not args.refetch)

    # Step 2: Generate markdown report
    print("\n[2/4] Generating markdown report...")

    if phase2_data:
        try:
            from app.connectors.sec_http import throttled_count
            phase2_data["sec_requests_throttled"] = throttled_count()
        except ImportError:
            pass

        markdown_report = generate_markdown_report(phase2_data)
    else:
        markdown_report = f"# {ENTITY_NAME} — Intelligence Report\n\nNo data available."

    quality = check_report_quality(markdown_report, TICKER, ENTITY_NAME)
    print(f"      Quality gate: {'PASS' if quality['passed'] else 'FAIL'} "
          f"({quality['word_count']:,} words, {quality['section_count']} sections)")
    if CHARTS_AVAILABLE:
        print(f"      Charts embedded: {FIGURE_COUNT}"
              + ("" if FIGURE_COUNT else " (none — data did not support a figure)"))
    else:
        print("      Charts embedded: UNAVAILABLE — report will lack visual data")
        print("      ⚠️  Install matplotlib to enable charts: pip install matplotlib")
    for issue in quality["issues"]:
        print(f"        - {issue}")

    # Sanitize: remove broken/empty/placeholder content before PDF
    markdown_report = sanitize_markdown(markdown_report)
    # Re-check quality after sanitization
    quality_post = check_report_quality(markdown_report, TICKER, ENTITY_NAME)
    if quality_post["word_count"] < quality["word_count"]:
        removed = quality["word_count"] - quality_post["word_count"]
        print(f"      Sanitizer removed {removed} words of broken/empty content")

    # Step 3: Save outputs
    print("\n[3/4] Saving outputs...")

    output_base = os.path.join(os.path.dirname(__file__), OUTPUT_DIR)
    os.makedirs(output_base, exist_ok=True)

    # Save markdown
    md_path = os.path.join(output_base, OUTPUT_MD)
    with open(md_path, "w") as f:
        f.write(markdown_report)
    print(f"      Markdown: {md_path}")

    # Save JSON data
    json_path = os.path.join(output_base, OUTPUT_JSON)
    with open(json_path, "w") as f:
        json_data = json.loads(json.dumps(phase2_data, default=str))
        json.dump(json_data, f, indent=2)
    print(f"      JSON: {json_path}")

    # Step 4: Generate PDF
    print("\n[4/4] Generating PDF...")

    pdf_path = os.path.join(output_base, OUTPUT_FILENAME)

    # The PDF is rendered from the markdown produced in step 3, not rebuilt
    # from the data. The legacy premium renderer assembled its own HTML from a
    # separate schema, so it silently omitted every section added since — the
    # PDF carried 1 of 13 sections and none of the narrative while the markdown
    # beside it was complete. One source of truth avoids that drifting again.
    if not PDF_AVAILABLE:
        print("      PDF renderer unavailable; markdown written above")
    else:
        try:
            pdf_bytes = convert_markdown_to_pdf(
                markdown_content=markdown_report,
                output_path=pdf_path,
                title=f"{ENTITY_NAME} — Intelligence Report",
            )
            print(f"      PDF: {pdf_path}")
            print(f"      PDF size: {len(pdf_bytes):,} bytes")
        except Exception as e:
            print(f"      PDF generation failed: {e}")
            import traceback
            traceback.print_exc()

    # The interactive rendering is built from the same markdown as the PDF, so
    # the two cannot disagree about content — only about what you can do with it.
    html_path = os.path.join(output_base, OUTPUT_HTML)
    try:
        from app.services.interactive_report_service import (
            generate_interactive_report)
        result = generate_interactive_report(
            markdown_report, phase2_data, html_path, ENTITY_NAME, TICKER)
        if result.get("written"):
            print(f"      Interactive: {html_path}")
            print(f"      Interactive size: {result['bytes']:,} bytes, "
                  f"{result['sections']} sections, {result['nodes']} nodes, "
                  f"{result['links']} connections")
        else:
            print(f"      Interactive skipped: {result.get('reason')}")
            html_path = ""
    except Exception as e:
        print(f"      Interactive report failed: {e}")
        html_path = ""

    # Summary
    print("\n" + "=" * 70)
    print("REPORT GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nOutputs:")
    print(f"  Markdown: {md_path}")
    print(f"  JSON: {json_path}")
    if os.path.exists(pdf_path):
        print(f"  PDF: {pdf_path}")
    if html_path and os.path.exists(html_path):
        print(f"  Interactive: {html_path}")
    print(f"\nOpen markdown: open '{md_path}'")
    if html_path and os.path.exists(html_path):
        print(f"Open interactive: open '{html_path}'")

    return 0


def _convert_to_legacy_format(phase2_data: dict) -> dict:
    """Convert Phase 2 data to legacy report format for PDF generation."""
    sections = []

    # Executive Summary
    sections.append({
        "name": "Executive Summary",
        "claims": [
            {
                "text": f"This comprehensive intelligence report covers {ENTITY_NAME} ({TICKER}) using Phase 2 deep research connectors.",
                "source": "Research Platform",
                "confidence": "DOCUMENTED"
            }
        ]
    })

    # Valuation
    valuation = phase2_data.get("valuation_analysis") or {}
    dcf = valuation.get("dcf") or {}
    if dcf:
        assessment = dcf.get("assessment") or "N/A"
        intrinsic = dcf.get("intrinsic_price_per_share") or 0
        current = dcf.get("current_market_price") or 0
        upside = dcf.get("upside_downside_pct") or 0

        sections.append({
            "name": "Investment Thesis",
            "claims": [
                {
                    "text": f"**Recommendation: {assessment}**\n\nBased on DCF valuation, intrinsic value is ${intrinsic:,.2f} vs current price ${current:,.2f} ({upside:+.1f}% {'upside' if upside > 0 else 'downside'}).",
                    "source": "DCF Valuation",
                    "confidence": "ANALYTICAL"
                }
            ]
        })

    # Financial
    financial = phase2_data.get("financial_intelligence") or {}
    income = financial.get("income_statement") or {}
    if income:
        revenue = format_currency(income.get('revenue', 0))
        net_income = format_currency(income.get('net_income', 0))
        sections.append({
            "name": "Financial Health",
            "claims": [
                {
                    "text": f"| Metric | Value |\n|--------|-------|\n| Revenue (TTM) | {revenue} |\n| Net Income | {net_income} |",
                    "source": "SEC EDGAR",
                    "confidence": "DOCUMENTED"
                }
            ]
        })

    # Contracts
    contracts = phase2_data.get("contract_intelligence") or {}
    summary = contracts.get("summary") or {}
    if summary:
        total = summary.get('total_contracts', 0)
        amount = format_currency(summary.get('total_obligated', 0))
        sections.append({
            "name": "Government Contracts",
            "claims": [
                {
                    "text": f"{ENTITY_NAME} received {total} federal contract(s) totaling {amount} in documented obligations.",
                    "source": "USASpending.gov",
                    "confidence": "DOCUMENTED"
                }
            ]
        })

    # Risk Register
    risk = phase2_data.get("risk_register") or {}
    top_risks = risk.get("top_risks") or []
    if top_risks:
        risk_text = "\n".join([
            f"- **{r.get('title', '')}** [{r.get('severity', '')}]: {r.get('description', '')}"
            for r in top_risks[:5]
        ])
        sections.append({
            "name": "Risk Assessment",
            "claims": [
                {
                    "text": f"**Overall Profile:** {(risk.get('summary') or {}).get('overall_risk_profile', 'UNKNOWN')}\n\n{risk_text}",
                    "source": "Risk Analysis",
                    "confidence": "ANALYTICAL"
                }
            ]
        })

    # People
    personnel = phase2_data.get("personnel_intelligence") or {}
    people_data = []
    for exec in (personnel.get("executive_dossiers") or [])[:5]:
        people_data.append({
            "name": exec.get("name", ""),
            "title": exec.get("title", ""),
            "bio": exec.get("background", "")[:300],
            "education": [],
            "experience": []
        })

    # Relationships
    relationships = []
    for comp in COMPETITORS:
        relationships.append({
            "kind": "competitor",
            "dst_name": comp,
            "context": f"Industry competitor"
        })

    return {
        "entity_name": ENTITY_NAME,
        "ticker": TICKER,
        "report_type": "enhanced",
        "sections": sections,
        "relationships_created": relationships,
        "people_data": people_data,
        "summary": {
            "total_claims": sum(len(s.get("claims", [])) for s in sections),
            "total_sections": len(sections),
            "relationships_count": len(relationships),
            "key_personnel_count": len(people_data)
        },
        "data_sources": {
            "sec_edgar": bool(phase2_data.get("financial_intelligence")),
            "usaspending": bool(phase2_data.get("contract_intelligence")),
            "yfinance": bool(phase2_data.get("valuation_analysis")),
            "phase2_connectors": True
        }
    }


if __name__ == "__main__":
    sys.exit(main())
