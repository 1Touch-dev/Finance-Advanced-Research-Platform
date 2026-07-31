"""
Institutional Ownership Overlap Analyzer (13F Intelligence)
────────────────────────────────────────────────────────────────────────────
Cross-company institutional ownership analysis for deep intelligence:
  - Compare institutional holders across competitors
  - Identify shared major investors
  - Detect ownership concentration patterns
  - Track mega-position overlaps
  - Analyze potential coordinated selling/buying risk

Uses SEC EDGAR 13F filings + yfinance for current holdings.
No API key required - public SEC data.
"""
import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

EDGAR_BASE = "https://data.sec.gov"
SEC_HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "FinanceIntelPlatform/1.0 research@example.com")}

# Top institutions to always track
TOP_INSTITUTIONS = {
    "Berkshire Hathaway": "0001067983",
    "BlackRock": "0001364742",
    "Vanguard": "0000102909",
    "State Street": "0000093751",
    "Fidelity": "0000315066",
    "T. Rowe Price": "0000860546",
    "JP Morgan": "0000070858",
    "Goldman Sachs": "0000886982",
    "Morgan Stanley": "0000895421",
    "Capital Group": "0000036405",
    "Wellington": "0001448067",
    "Invesco": "0001040280",
    "Northern Trust": "0000073124",
    "Bank of America": "0000070858",
    "Geode Capital": "0001214717",
}


def _safe_float(v) -> float:
    """Safely convert to float."""
    try:
        if v is None:
            return 0.0
        import pandas as pd
        if hasattr(pd, 'isna') and pd.isna(v):
            return 0.0
        f = float(v)
        return 0.0 if math.isnan(f) or math.isinf(f) else f
    except:
        return 0.0


def _get_institutional_holders_yf(ticker: str) -> Dict[str, Dict[str, Any]]:
    """
    Institutional holders for a ticker, keyed by manager name.

    Reads SEC Form 13F-HR information tables. This previously called yfinance,
    which is not installed and never has been, so every overlap calculation in
    this module returned zeros against a fully working comparison engine. The
    13F path is the same public filing the commercial feeds resell.
    """
    holders: Dict[str, Dict[str, Any]] = {}
    try:
        from app.connectors.institutional_holdings_connector import (
            get_institutional_holders,
        )
        from app.connectors.market_data_connector import get_quote
        from app.connectors.sec_edgar_connector import get_filer_cik
        from app.connectors.sec_http import sec_get_json

        quote = get_quote(ticker) or {}
        shares_outstanding = quote.get("shares_outstanding")

        # 13F information tables carry the issuer's registrant name, so the
        # name must come from EDGAR rather than from a market vendor. Finnhub
        # returns "Advanced Micro Devices, Inc." where the filing says
        # "ADVANCED MICRO DEVICES INC", and the vendor name is absent for some
        # tickers entirely.
        entity_name = quote.get("company_name") or ticker
        cik = get_filer_cik(ticker)
        if cik:
            submissions = sec_get_json(
                f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json") or {}
            entity_name = submissions.get("name") or entity_name

        report = get_institutional_holders(
            entity_name, ticker, shares_outstanding, quote.get("price")) or {}

        for holding in report.get("holders", []):
            name = holding.get("institution")
            if not name:
                continue
            shares = int(_safe_float(holding.get("shares")))
            holders[name] = {
                "shares": shares,
                # Percentages are computed only where the share count is known,
                # never estimated, matching the holdings connector's rule.
                "pct_held": (shares / shares_outstanding * 100.0
                             if shares_outstanding else 0.0),
                "value_usd": int(_safe_float(holding.get("value"))),
                "date_reported": (holding.get("report_date") or "")[:10],
                "source_url": holding.get("source_url"),
            }

    except Exception as e:
        logger.warning("Error fetching institutional holders for %s: %s", ticker, e)

    return holders


def _normalize_holder_name(name: str) -> str:
    """Normalize holder name for matching across companies."""
    normalized = name.lower().strip()
    # Remove common suffixes
    for suffix in [" inc", " inc.", " llc", " lp", " l.p.", " corp", " corp.",
                   " co", " co.", " group", " holdings", " management",
                   " advisors", " advisers", " capital", " partners", " fund"]:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
    return normalized


def get_institutional_overlap(tickers: List[str]) -> Dict[str, Any]:
    """
    Analyze institutional ownership overlap across multiple tickers.

    Args:
        tickers: List of stock tickers to compare (e.g., ["NVDA", "AMD", "INTC"])

    Returns:
        Overlap analysis with shared investors, concentration metrics, and risk flags.
    """
    result = {
        "tickers_analyzed": tickers,
        "holders_by_ticker": {},
        "shared_holders": [],
        "overlap_matrix": {},
        "concentration_metrics": {},
        "top_cross_holders": [],
        "risk_flags": [],
        "summary": {
            "total_unique_holders": 0,
            "holders_in_all": 0,
            "holders_in_majority": 0,
            "avg_overlap_pct": 0,
        },
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if len(tickers) < 2:
        result["error"] = "Need at least 2 tickers for overlap analysis"
        return result

    # Fetch holders for each ticker
    all_holders: Dict[str, Set[str]] = {}  # normalized_name -> set of tickers
    holder_details: Dict[str, Dict[str, Dict]] = {}  # ticker -> holder_name -> details

    for ticker in tickers:
        logger.info("Fetching institutional holders for %s", ticker)
        holders = _get_institutional_holders_yf(ticker)
        holder_details[ticker] = holders
        result["holders_by_ticker"][ticker] = {
            "count": len(holders),
            "top_5": sorted(
                [{"holder": k, **v} for k, v in holders.items()],
                key=lambda x: x.get("value_usd", 0),
                reverse=True,
            )[:5],
        }

        # Track which tickers each holder owns
        for holder_name in holders.keys():
            normalized = _normalize_holder_name(holder_name)
            if normalized not in all_holders:
                all_holders[normalized] = set()
            all_holders[normalized].add(ticker)

    # Identify shared holders
    shared = []
    for normalized_name, ticker_set in all_holders.items():
        if len(ticker_set) >= 2:
            # Get full details for this holder across tickers
            holder_data = {
                "normalized_name": normalized_name,
                "tickers_held": list(ticker_set),
                "count": len(ticker_set),
                "details_by_ticker": {},
                "total_value_across_all": 0,
            }

            # Find original name and details from each ticker
            for ticker in ticker_set:
                for holder_name, details in holder_details.get(ticker, {}).items():
                    if _normalize_holder_name(holder_name) == normalized_name:
                        holder_data["details_by_ticker"][ticker] = {
                            "original_name": holder_name,
                            **details,
                        }
                        holder_data["total_value_across_all"] += details.get("value_usd", 0)
                        break

            shared.append(holder_data)

    # Sort by number of tickers held, then by total value
    shared.sort(key=lambda x: (-x["count"], -x["total_value_across_all"]))
    result["shared_holders"] = shared[:50]

    # Build overlap matrix
    overlap_matrix = {}
    for i, ticker1 in enumerate(tickers):
        overlap_matrix[ticker1] = {}
        holders1 = set(_normalize_holder_name(h) for h in holder_details.get(ticker1, {}).keys())

        for j, ticker2 in enumerate(tickers):
            if i == j:
                overlap_matrix[ticker1][ticker2] = 100.0
                continue

            holders2 = set(_normalize_holder_name(h) for h in holder_details.get(ticker2, {}).keys())

            if holders1 and holders2:
                intersection = len(holders1 & holders2)
                union = len(holders1 | holders2)
                overlap_pct = (intersection / union * 100) if union > 0 else 0
            else:
                overlap_pct = 0

            overlap_matrix[ticker1][ticker2] = round(overlap_pct, 1)

    result["overlap_matrix"] = overlap_matrix

    # Concentration metrics
    for ticker in tickers:
        holders = holder_details.get(ticker, {})
        total_pct = sum(h.get("pct_held", 0) for h in holders.values())
        top5_pct = sum(
            h.get("pct_held", 0) for h in sorted(
                holders.values(),
                key=lambda x: x.get("value_usd", 0),
                reverse=True,
            )[:5]
        )

        result["concentration_metrics"][ticker] = {
            "total_institutional_pct": round(total_pct, 2),
            "top_5_holder_pct": round(top5_pct, 2),
            "holder_count": len(holders),
        }

    # Top cross-holders (holders with most value across all tickers)
    cross_holder_values = defaultdict(float)
    for holder_data in shared:
        cross_holder_values[holder_data["normalized_name"]] = holder_data["total_value_across_all"]

    result["top_cross_holders"] = sorted(
        [{"holder": k, "total_value": v, "tickers": list(all_holders.get(k, set()))}
         for k, v in cross_holder_values.items()],
        key=lambda x: x["total_value"],
        reverse=True,
    )[:20]

    # Summary metrics
    result["summary"]["total_unique_holders"] = len(all_holders)
    result["summary"]["holders_in_all"] = len([h for h, t in all_holders.items() if len(t) == len(tickers)])
    result["summary"]["holders_in_majority"] = len([h for h, t in all_holders.items() if len(t) > len(tickers) / 2])

    # Average overlap
    overlap_values = []
    for ticker1 in tickers:
        for ticker2 in tickers:
            if ticker1 != ticker2:
                overlap_values.append(overlap_matrix.get(ticker1, {}).get(ticker2, 0))
    result["summary"]["avg_overlap_pct"] = round(sum(overlap_values) / len(overlap_values), 1) if overlap_values else 0

    # The holder universe is a curated poll of the largest 13F filers, not the
    # complete share register. Every one of them holds every large-cap issuer,
    # so the overlap percentage converges on 100% by construction and says
    # nothing about the market. Flagging that as "selling pressure may cascade"
    # reports the sampling method as though it were a finding, which is the
    # failure this pipeline exists to prevent. The percentage is retained as a
    # coverage statistic and labelled as one.
    result["summary"]["overlap_is_sampling_artifact"] = True
    result["summary"]["holder_universe"] = "curated poll of major 13F filers"

    # What the same data does support: whether a manager weights one competitor
    # differently from another. That is a real allocation decision, visible
    # because the same filer reports all of them on one form.
    for shared in result["shared_holders"]:
        weights = {t: d.get("pct_held") or 0.0
                   for t, d in (shared.get("details_by_ticker") or {}).items()}
        held = {t: w for t, w in weights.items() if w > 0}
        if len(held) < 2:
            continue
        top_ticker = max(held, key=held.get)
        low_ticker = min(held, key=held.get)
        if held[low_ticker] <= 0:
            continue
        skew = held[top_ticker] / held[low_ticker]
        shared["weight_skew"] = round(skew, 2)
        shared["overweight"] = top_ticker
        shared["underweight"] = low_ticker
        # A manager holding one peer at several times the weight of another is
        # expressing a view. Below 2x it is closer to index tracking.
        if skew >= 2.0:
            result["risk_flags"].append({
                "type": "allocation_skew",
                "severity": "LOW",
                "detail": (f"{shared['details_by_ticker'][top_ticker]['original_name']} "
                           f"holds {held[top_ticker]:.2f}% of {top_ticker} against "
                           f"{held[low_ticker]:.2f}% of {low_ticker}, a {skew:.1f}x "
                           f"weighting difference between competitors"),
            })

    # Check for dominant cross-holder
    if result["top_cross_holders"]:
        top = result["top_cross_holders"][0]
        if top.get("total_value", 0) > 50_000_000_000:  # $50B+
            result["risk_flags"].append({
                "type": "dominant_cross_holder",
                "severity": "MEDIUM",
                "detail": f"{top['holder']} holds ${top['total_value']/1e9:.1f}B across {len(top['tickers'])} competitors",
            })

    return result


def compare_competitor_ownership(primary_ticker: str, competitors: List[str]) -> Dict[str, Any]:
    """
    Compare ownership structure of primary company vs competitors.

    Args:
        primary_ticker: Main company ticker
        competitors: List of competitor tickers

    Returns:
        Detailed comparison with shared investor analysis.
    """
    all_tickers = [primary_ticker] + competitors
    overlap = get_institutional_overlap(all_tickers)

    result = {
        "primary_ticker": primary_ticker,
        "competitors": competitors,
        "overlap_analysis": overlap,
        "primary_specific_analysis": {
            "holders_only_in_primary": [],
            "holders_shared_with_competitors": [],
            "competitor_specific_holders": {},
        },
        "investment_thesis_implications": [],
    }

    # Identify holders unique to primary
    primary_holders = set(_normalize_holder_name(h) for h in
                          overlap.get("holders_by_ticker", {}).get(primary_ticker, {}).get("top_5", []))

    all_competitor_holders = set()
    for comp in competitors:
        comp_holders = overlap.get("holders_by_ticker", {}).get(comp, {}).get("top_5", [])
        for h in comp_holders:
            all_competitor_holders.add(_normalize_holder_name(h.get("holder", "")))

    # Shared vs unique analysis
    shared_with_competitors = []
    for holder_data in overlap.get("shared_holders", []):
        if primary_ticker in holder_data.get("tickers_held", []):
            comp_overlap = [t for t in holder_data.get("tickers_held", []) if t != primary_ticker]
            if comp_overlap:
                shared_with_competitors.append({
                    "holder": holder_data["normalized_name"],
                    "also_holds": comp_overlap,
                    "value_in_primary": holder_data.get("details_by_ticker", {}).get(primary_ticker, {}).get("value_usd", 0),
                })

    result["primary_specific_analysis"]["holders_shared_with_competitors"] = shared_with_competitors[:15]

    # Investment implications
    avg_overlap = overlap.get("summary", {}).get("avg_overlap_pct", 0)

    if avg_overlap > 70:
        result["investment_thesis_implications"].append(
            "High institutional overlap suggests sector-level trading dynamics dominate stock-specific factors"
        )
    if overlap.get("risk_flags"):
        result["investment_thesis_implications"].append(
            "Correlated ownership increases risk of cascading sell-offs during sector stress"
        )

    return result


def get_mega_holder_positions(ticker: str) -> Dict[str, Any]:
    """
    Identify mega positions (>$1B) in a specific ticker.
    """
    result = {
        "ticker": ticker,
        "mega_positions": [],  # >$1B
        "large_positions": [],  # $100M-$1B
        "notable_holders": {},
        "total_mega_value": 0,
        "total_large_value": 0,
    }

    holders = _get_institutional_holders_yf(ticker)

    for holder_name, details in holders.items():
        value = details.get("value_usd", 0)

        position = {
            "holder": holder_name,
            "value_usd": value,
            "shares": details.get("shares", 0),
            "pct_held": details.get("pct_held", 0),
        }

        if value >= 1_000_000_000:
            result["mega_positions"].append(position)
            result["total_mega_value"] += value
        elif value >= 100_000_000:
            result["large_positions"].append(position)
            result["total_large_value"] += value

        # Check if notable institution
        normalized = _normalize_holder_name(holder_name)
        for inst_name in TOP_INSTITUTIONS:
            if inst_name.lower().split()[0] in normalized or normalized in inst_name.lower():
                result["notable_holders"][inst_name] = position
                break

    # Sort by value
    result["mega_positions"].sort(key=lambda x: x["value_usd"], reverse=True)
    result["large_positions"].sort(key=lambda x: x["value_usd"], reverse=True)

    return result


def track_position_changes(ticker: str, days: int = 90) -> Dict[str, Any]:
    """
    Track recent position changes by major institutions.
    Uses SEC EDGAR EFTS to find recent 13F filings.
    """
    result = {
        "ticker": ticker,
        "recent_filings": [],
        "position_changes": {
            "new_positions": [],
            "increased": [],
            "decreased": [],
            "exited": [],
        },
    }

    try:
        # Search EDGAR for recent 13F filings mentioning this ticker
        start_dt = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        params = {
            "q": f'"{ticker}"',
            "forms": "13F-HR",
            "dateRange": "custom",
            "startdt": start_dt,
            "enddt": datetime.now().strftime("%Y-%m-%d"),
        }

        resp = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params=params,
            headers=SEC_HEADERS,
            timeout=15,
        )

        if resp.ok:
            hits = resp.json().get("hits", {}).get("hits", [])[:30]
            for h in hits:
                src = h.get("_source", {})
                names = src.get("display_names", [])
                filer_name = names[0].split("(CIK")[0].strip() if names else "Unknown"

                result["recent_filings"].append({
                    "filer": filer_name,
                    "filing_date": src.get("file_date", ""),
                    "period": src.get("period_of_report", ""),
                    "accession": h.get("_id", ""),
                })

    except Exception as e:
        logger.warning("Error tracking position changes for %s: %s", ticker, e)

    return result


# ── Convenience Exports ──────────────────────────────────────────────────────

def analyze_overlap(tickers: List[str]) -> Dict[str, Any]:
    """Analyze institutional overlap across tickers."""
    return get_institutional_overlap(tickers)


def compare_competitors(primary: str, competitors: List[str]) -> Dict[str, Any]:
    """Compare primary company ownership vs competitors."""
    return compare_competitor_ownership(primary, competitors)


def get_mega_holders(ticker: str) -> Dict[str, Any]:
    """Get mega position holders for a ticker."""
    return get_mega_holder_positions(ticker)
