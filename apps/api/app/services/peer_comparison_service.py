"""
Multi-company comparison (G-03).

*"Comparing it to companies with similar or related founders developers or
investors, or directors of company advisors etc... than comparing and
analyzing finding patterns."* — 16 July, repeated on 29 and 30.

The report already compares peers on one axis: who owns them. That is one
column of the table James described. This module fetches the other columns —
scale, profitability, research intensity, federal footprint, lobbying, insider
behaviour and board reach — for each peer, from the same free registers used
for the subject, and puts them side by side.

Two design decisions are worth stating because they are what stops a peer
table becoming a league table of noise.

**Comparability travels with the number.** Issuers keep different fiscal
calendars, so the peer figure is labelled with the period it came from rather
than being aligned to the subject's year-end and presented as though the two
were measured together.

**A rank is only shown where every peer has the figure.** Ranking four
companies out of five and printing "2nd of 5" describes our retrieval, not the
market. Where a peer is missing a metric the row says so and the rank is
withheld.

Fetches run in parallel because each peer is four independent network calls
and doing them serially would put a five-peer comparison past the point where
anyone waits for it.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_WORKERS = 6


def _pct(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if not numerator or not denominator:
        return None
    try:
        return round(numerator / denominator * 100, 1)
    except ZeroDivisionError:
        return None


# ---------------------------------------------------------------------------
# One peer
# ---------------------------------------------------------------------------

def _financial_slice(ticker: str) -> Dict[str, Any]:
    """Scale and margin from the peer's own SEC facts."""
    try:
        from app.connectors.sec_edgar_connector import get_full_financial_profile
        profile = get_full_financial_profile(ticker) or {}
    except Exception as error:
        logger.info("Peer financials %s failed: %s", ticker, error)
        return {"error": str(error)[:120]}

    statements = (profile.get("financial_statements") or {})
    income = statements.get("income_statement") or []
    if not income:
        return {"error": "no income statement"}

    latest = income[0]
    revenue = latest.get("Revenues")
    return {
        "cik": profile.get("cik"),
        "company": (profile.get("company_info") or {}).get("name"),
        "fiscal_year": latest.get("fiscal_year"),
        "period_end": latest.get("period_end_date"),
        "revenue": revenue,
        "gross_margin_pct": _pct(latest.get("GrossProfit"), revenue),
        "operating_margin_pct": _pct(latest.get("OperatingIncome"), revenue),
        "net_margin_pct": _pct(latest.get("NetIncome"), revenue),
        "rd_intensity_pct": _pct(latest.get("ResearchAndDevelopment"), revenue),
        "total_assets": latest.get("TotalAssets"),
        "periods_held": len(income),
    }


def _federal_slice(company: str) -> Dict[str, Any]:
    try:
        from app.connectors.fpds_connector import get_full_contract_portfolio
        portfolio = get_full_contract_portfolio(company) or {}
    except Exception as error:
        logger.info("Peer contracts %s failed: %s", company, error)
        return {"error": str(error)[:120]}
    summary = portfolio.get("summary") or {}
    return {
        "obligated": summary.get("total_obligated"),
        "awards": summary.get("contract_count") or len(portfolio.get("contracts") or []),
        "agencies": len(portfolio.get("agency_breakdown") or []),
    }


def _lobbying_slice(company: str) -> Dict[str, Any]:
    try:
        from app.connectors.opensecrets_connector import fetch_lobbying_summary
        lobbying = fetch_lobbying_summary(company) or {}
    except Exception as error:
        logger.info("Peer lobbying %s failed: %s", company, error)
        return {"error": str(error)[:120]}
    return {
        "spend": lobbying.get("total_spend"),
        "filings": lobbying.get("filing_count"),
        "registrants": len(lobbying.get("top_firms") or []),
        "in_house_pct": _pct(lobbying.get("in_house_spend"),
                             lobbying.get("total_spend")),
    }


def _insider_slice(cik: Optional[str]) -> Dict[str, Any]:
    if not cik:
        return {}
    try:
        from app.connectors.sec_edgar_connector import get_insider_transactions
        insider = get_insider_transactions(cik) or {}
    except Exception as error:
        logger.info("Peer insider %s failed: %s", cik, error)
        return {"error": str(error)[:120]}

    rows = insider.get("transactions") or []
    disposals = [r for r in rows if r.get("acquired_disposed") == "D"]
    acquisitions = [r for r in rows if r.get("acquired_disposed") == "A"]
    sold = sum(float(r.get("value") or 0) for r in disposals)
    bought = sum(float(r.get("value") or 0) for r in acquisitions)
    return {
        "transactions": len(rows),
        "disposal_value": sold,
        "acquisition_value": bought,
        # Open-market buying by insiders is rare enough that the ratio is
        # usually a statement about how compensation is structured, not about
        # conviction. It is reported without interpretation.
        "sell_share_pct": _pct(sold, sold + bought),
        "people": len({r.get("insider") for r in rows if r.get("insider")}),
    }


def profile_peer(ticker: str, company_hint: str = "") -> Dict[str, Any]:
    """Every comparable metric for one peer, fetched in parallel."""
    out: Dict[str, Any] = {"ticker": ticker, "errors": []}

    financials = _financial_slice(ticker)
    if financials.get("error"):
        out["errors"].append(f"financials: {financials['error']}")
    out.update({k: v for k, v in financials.items() if k != "error"})

    company = out.get("company") or company_hint or ticker

    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs = {
            executor.submit(_federal_slice, company): "federal",
            executor.submit(_lobbying_slice, company): "lobbying",
            executor.submit(_insider_slice, out.get("cik")): "insider",
        }
        for future in as_completed(jobs):
            label = jobs[future]
            try:
                payload = future.result() or {}
            except Exception as error:
                out["errors"].append(f"{label}: {str(error)[:100]}")
                continue
            if payload.get("error"):
                out["errors"].append(f"{label}: {payload['error']}")
            out[label] = {k: v for k, v in payload.items() if k != "error"}

    return out


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------

# metric key, label, where it lives, higher-is-first, and how to format.
_METRICS = [
    ("revenue", "Revenue", None, True, "money"),
    ("gross_margin_pct", "Gross margin", None, True, "pct"),
    ("operating_margin_pct", "Operating margin", None, True, "pct"),
    ("net_margin_pct", "Net margin", None, True, "pct"),
    ("rd_intensity_pct", "R&D as % of revenue", None, True, "pct"),
    ("obligated", "Federal obligations", "federal", True, "money"),
    ("awards", "Federal awards", "federal", True, "int"),
    ("spend", "Lobbying disclosed", "lobbying", True, "money"),
    ("filings", "LDA filings", "lobbying", True, "int"),
    ("disposal_value", "Insider disposals", "insider", True, "money"),
    ("sell_share_pct", "Disposals as % of insider value", "insider", True, "pct"),
]


def _read(peer: Dict[str, Any], key: str, section: Optional[str]):
    source = peer.get(section) if section else peer
    if not isinstance(source, dict):
        return None
    return source.get(key)


def compare_peers(subject_ticker: str, subject_data: Dict[str, Any],
                  peer_tickers: List[str]) -> Optional[Dict[str, Any]]:
    """The subject against its peers on every axis we can source for free."""
    peers = [t.strip().upper() for t in peer_tickers if t and t.strip()]
    if not peers:
        return None

    profiles: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        jobs = {executor.submit(profile_peer, t): t for t in peers}
        for future in as_completed(jobs):
            ticker = jobs[future]
            try:
                profiles[ticker] = future.result()
            except Exception as error:
                logger.warning("Peer %s failed entirely: %s", ticker, error)
                profiles[ticker] = {"ticker": ticker,
                                    "errors": [str(error)[:120]]}

    subject = _subject_profile(subject_ticker, subject_data)
    everyone = [subject] + [profiles[t] for t in peers if t in profiles]

    rows = []
    for key, label, section, higher_first, fmt in _METRICS:
        values = {p["ticker"]: _read(p, key, section) for p in everyone}
        present = {k: v for k, v in values.items()
                   if isinstance(v, (int, float))}

        row = {
            "metric": label,
            "format": fmt,
            "values": values,
            "coverage": f"{len(present)}/{len(everyone)}",
            "complete": len(present) == len(everyone),
        }
        # Rank only where every company has the figure.
        if row["complete"] and len(present) > 1:
            order = sorted(present, key=lambda k: present[k],
                           reverse=higher_first)
            row["ranks"] = {t: i + 1 for i, t in enumerate(order)}
            row["subject_rank"] = row["ranks"].get(subject_ticker)
            row["leader"] = order[0]
        rows.append(row)

    return {
        "subject": subject_ticker,
        "peers": peers,
        "companies": everyone,
        "rows": rows,
        "complete_metrics": sum(1 for r in rows if r["complete"]),
        "total_metrics": len(rows),
        "errors": {p["ticker"]: p.get("errors") or [] for p in everyone
                   if p.get("errors")},
        "fiscal_note": (
            "Issuers keep different fiscal calendars. Each figure is the most "
            "recent annual period that company filed, and the period end is "
            "given per company rather than the rows being forced onto one "
            "year-end they do not share."
        ),
    }


def _subject_profile(ticker: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """The subject read from data already in hand — no refetch."""
    statements = ((data.get("financial_intelligence") or {})
                  .get("financial_statements") or {})
    income = statements.get("income_statement") or []
    latest = income[0] if income else {}
    revenue = latest.get("Revenues")

    contracts = data.get("contract_intelligence") or {}
    summary = contracts.get("summary") or {}
    lobbying = ((data.get("political_intelligence") or {})
                .get("lobbying_summary") or {})

    rows = (data.get("insider_transactions") or {}).get("transactions") or []
    sold = sum(float(r.get("value") or 0) for r in rows
               if r.get("acquired_disposed") == "D")
    bought = sum(float(r.get("value") or 0) for r in rows
                 if r.get("acquired_disposed") == "A")

    return {
        "ticker": ticker,
        "company": data.get("entity_name"),
        "is_subject": True,
        "fiscal_year": latest.get("fiscal_year"),
        "period_end": latest.get("period_end_date"),
        "revenue": revenue,
        "gross_margin_pct": _pct(latest.get("GrossProfit"), revenue),
        "operating_margin_pct": _pct(latest.get("OperatingIncome"), revenue),
        "net_margin_pct": _pct(latest.get("NetIncome"), revenue),
        "rd_intensity_pct": _pct(latest.get("ResearchAndDevelopment"), revenue),
        "total_assets": latest.get("TotalAssets"),
        "federal": {
            "obligated": summary.get("total_obligated"),
            "awards": summary.get("contract_count")
                      or len(contracts.get("contracts") or []),
            "agencies": len(contracts.get("agency_breakdown") or []),
        },
        "lobbying": {
            "spend": lobbying.get("total_spend"),
            "filings": lobbying.get("filing_count"),
            "registrants": len(lobbying.get("top_firms") or []),
            "in_house_pct": _pct(lobbying.get("in_house_spend"),
                                 lobbying.get("total_spend")),
        },
        "insider": {
            "transactions": len(rows),
            "disposal_value": sold,
            "acquisition_value": bought,
            "sell_share_pct": _pct(sold, sold + bought),
            "people": len({r.get("insider") for r in rows if r.get("insider")}),
        },
        "errors": [],
    }
