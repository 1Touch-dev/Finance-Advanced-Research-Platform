"""
Government Trading Intelligence Connector
──────────────────────────────────────────
Tracks financial trades & disclosures by US government officials and insiders:
  - Congressional STOCK Act PTR (Periodic Transaction Reports) via House Clerk ZIP
  - SEC EDGAR Form 4 insider transactions
  - Company insider trades via yfinance
Free sources only.
"""
import io
import os
import time
import logging
import requests
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Finance-Platform/1.0 abhishekk@kyma.world"}
EDGAR_BASE = "https://data.sec.gov"
EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"
HOUSE_FD_URL = "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{}FD.ZIP"

# Module-level cache
_cache: dict = {}
_cache_ts: dict = {}
CACHE_TTL = 7200  # 2 hours


def _get(url, timeout=20) -> dict:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Gov fetch %s: %s", url, e)
        return {}


def _get_bytes(url, timeout=30) -> bytes:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.content
    except Exception as e:
        log.warning("Gov bytes fetch %s: %s", url, e)
        return b""


# ─── House Congressional Financial Disclosures ───────────────────────────────

def _load_house_fd(year: int = None, force: bool = False) -> list:
    """
    Load House Financial Disclosure data (annual ZIP from clerk.house.gov).
    Returns list of members who filed PTR (Periodic Transaction Reports).
    """
    year = year or datetime.now().year
    cache_key = f"house_fd_{year}"
    if not force and cache_key in _cache and (time.time() - _cache_ts.get(cache_key, 0)) < CACHE_TTL:
        return _cache[cache_key]

    url = HOUSE_FD_URL.format(year)
    data = _get_bytes(url, timeout=30)
    if not data:
        log.warning("Could not fetch House FD ZIP for %d", year)
        return _cache.get(cache_key, [])

    members = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml_files = [f for f in zf.namelist() if f.endswith(".xml")]
            if not xml_files:
                return []
            with zf.open(xml_files[0]) as xf:
                tree = ET.parse(xf)
                root = tree.getroot()
                for member in root.findall("Member"):
                    filing_type = (member.findtext("FilingType") or "").strip()
                    members.append({
                        "last": member.findtext("Last") or "",
                        "first": member.findtext("First") or "",
                        "prefix": member.findtext("Prefix") or "",
                        "state_dst": member.findtext("StateDst") or "",
                        "filing_type": filing_type,
                        "filing_date": member.findtext("FilingDate") or "",
                        "year": int(member.findtext("Year") or year),
                        "doc_id": member.findtext("DocID") or "",
                        "chamber": "house",
                    })
    except Exception as e:
        log.error("House FD parse error: %s", e)
        return _cache.get(cache_key, [])

    _cache[cache_key] = members
    _cache_ts[cache_key] = time.time()
    return members


def get_house_ptr_filers(year: int = None, days: int = 90) -> list:
    """
    Get House members who filed Periodic Transaction Reports (stock trades).
    Filing type 'P' = PTR (actual stock trades).
    """
    year = year or datetime.now().year
    members = _load_house_fd(year)

    # Filter PTR filers only
    ptr_filers = [m for m in members if m["filing_type"] == "P"]

    # Filter by date if days specified
    if days:
        cutoff = datetime.now() - timedelta(days=days)
        filtered = []
        for m in ptr_filers:
            dt = None
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(m["filing_date"], fmt)
                    break
                except Exception:
                    pass
            if dt and dt >= cutoff:
                filtered.append({**m, "name": f"{m['first']} {m['last']}"})
        return filtered

    return [{**m, "name": f"{m['first']} {m['last']}"} for m in ptr_filers]


# ─── SEC EDGAR Form 4 Insider Trades ─────────────────────────────────────────

def get_recent_sec_form4(days: int = 30, limit: int = 50) -> list:
    """
    Recent SEC Form 4 insider transactions from EDGAR full-text search.
    Covers corporate insiders (officers/directors) buying/selling stock.
    """
    start_dt = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_dt = datetime.now().strftime("%Y-%m-%d")

    try:
        params = {
            "q": "",
            "forms": "4",
            "dateRange": "custom",
            "startdt": start_dt,
            "enddt": end_dt,
            "hits.hits._source": "period_of_report,display_names,file_date,form_type",
            "hits.hits.total": "true",
        }
        r = requests.get(EFTS_BASE, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        hits = data.get("hits", {}).get("hits", [])[:limit]
        result = []
        for h in hits:
            src = h.get("_source", {})
            display_names = src.get("display_names", []) or []
            insider = display_names[0] if display_names else "Unknown"
            company = display_names[1] if len(display_names) > 1 else ""
            result.append({
                "insider": insider.split("(CIK")[0].strip(),
                "company": company.split("(CIK")[0].strip(),
                "filing_date": src.get("file_date", ""),
                "period": src.get("period_of_report", ""),
                "form_type": src.get("form_type", "4"),
                "source": "SEC EDGAR",
            })
        return result
    except Exception as e:
        log.error("SEC Form 4 search error: %s", e)
        return []


def get_insider_trades_for_ticker(ticker: str, days: int = 90) -> list:
    """
    Insider trades for a specific company via yfinance.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        df = stock.insider_transactions
        if df is None or df.empty:
            return []

        cutoff = datetime.now() - timedelta(days=days)
        trades = []
        for _, row in df.head(50).iterrows():
            date_str = str(row.get("Start Date", row.get("Date", "")))
            try:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                if dt < cutoff:
                    continue
            except Exception:
                pass
            shares = int(row.get("Shares", 0) or 0)
            value = float(row.get("Value", 0) or 0)
            trades.append({
                "ticker": ticker,
                "insider": str(row.get("Insider", row.get("Name", ""))),
                "title": str(row.get("Title", "")),
                "transaction": str(row.get("Transaction", "")),
                "shares": shares,
                "value_usd": value,
                "date": date_str[:10],
                "ownership_type": str(row.get("Ownership", "Direct")),
                "source": "yfinance/SEC Form 4",
            })
        return trades
    except Exception as e:
        log.error("Insider trade error for %s: %s", ticker, e)
        return []


# ─── Most-Traded Tickers by Congress ─────────────────────────────────────────

def get_most_traded_tickers_congress(year: int = None, top_n: int = 20) -> list:
    """
    Based on House PTR filers - not individual trades yet.
    Returns the list of congressional members who filed PTRs recently.
    """
    year = year or datetime.now().year
    ptr_filers = get_house_ptr_filers(year=year, days=180)

    # Group by state/district
    by_state = defaultdict(list)
    for m in ptr_filers:
        by_state[m.get("state_dst", "")].append(m["name"])

    return [
        {"state_district": k, "members": v, "ptr_count": len(v)}
        for k, v in sorted(by_state.items(), key=lambda x: len(x[1]), reverse=True)
    ][:top_n]


def get_most_active_members_congress(year: int = None, top_n: int = 20) -> list:
    """
    Congressional members who filed PTRs most recently.
    """
    year = year or datetime.now().year
    ptr_filers = get_house_ptr_filers(year=year, days=90)

    # Count by member
    member_counts = defaultdict(lambda: {"count": 0, "state_dst": "", "dates": []})
    for m in ptr_filers:
        name = m["name"]
        member_counts[name]["count"] += 1
        member_counts[name]["state_dst"] = m.get("state_dst", "")
        member_counts[name]["dates"].append(m.get("filing_date", ""))

    ranked = sorted(member_counts.items(), key=lambda x: x[1]["count"], reverse=True)
    return [
        {
            "name": k,
            "chamber": "house",
            "state_dst": v["state_dst"],
            "ptr_filings": v["count"],
            "latest_filing": sorted(v["dates"])[-1] if v["dates"] else "",
        }
        for k, v in ranked[:top_n]
    ]


# ─── Government Trading Dashboard ────────────────────────────────────────────

def gov_trading_summary(days: int = 90) -> dict:
    """
    Government trading intelligence dashboard combining:
    - House PTR filers (congressional stock trade disclosures)
    - Recent SEC Form 4 insider transactions
    """
    year = datetime.now().year

    try:
        ptr_filers = get_house_ptr_filers(year=year, days=days)
    except Exception:
        ptr_filers = []

    try:
        form4_trades = get_recent_sec_form4(days=min(days, 30), limit=30)
    except Exception:
        form4_trades = []

    try:
        active_members = get_most_active_members_congress(year=year, top_n=15)
    except Exception:
        active_members = []

    # Filing type breakdown
    total_ptr = len(ptr_filers)

    # State breakdown
    by_state = defaultdict(int)
    for m in ptr_filers:
        st = (m.get("state_dst") or "")[:2]
        by_state[st] += 1
    top_states = sorted(by_state.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "period_days": days,
        "total_ptr_disclosures": total_ptr,
        "house_ptr_filers": total_ptr,
        "recent_ptr_filers": ptr_filers[:20],
        "most_active_members": active_members,
        "top_states_by_ptr": [{"state": s, "count": c} for s, c in top_states],
        "recent_sec_form4_insiders": form4_trades[:20],
        "data_sources": [
            "House Clerk Annual FD ZIP (PTR type P = stock trades)",
            "SEC EDGAR EFTS Full-Text Search (Form 4)",
        ],
        "note": "PTR = Periodic Transaction Report under the STOCK Act. Individual trade details require fetching per-filing PDFs.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def get_recent_congress_trades(days: int = 30, limit: int = 50) -> list:
    """Get recent congressional PTR filers + their filing dates."""
    return get_house_ptr_filers(days=days)[:limit]


def get_trades_by_ticker(ticker: str, days: int = 365) -> list:
    """Get insider trades for a specific stock + congressional context."""
    insider_trades = get_insider_trades_for_ticker(ticker, days=days)
    return insider_trades


def get_trades_by_member(name: str) -> list:
    """Find PTR filings by a specific congressional member."""
    all_members = _load_house_fd()
    name_lower = name.lower()
    return [
        {**m, "name": f"{m['first']} {m['last']}"}
        for m in all_members
        if name_lower in (m.get("first", "") + " " + m.get("last", "")).lower()
        and m.get("filing_type") == "P"
    ]


def get_most_traded_tickers(days: int = 90, top_n: int = 20) -> list:
    """
    Since individual PTR trade data requires PDF parsing,
    returns a summary of congressional trading activity by state/member.
    """
    return get_most_traded_tickers_congress(top_n=top_n)


def get_most_active_members(days: int = 90, top_n: int = 20) -> list:
    """Most active congressional traders based on PTR filings."""
    return get_most_active_members_congress(top_n=top_n)
