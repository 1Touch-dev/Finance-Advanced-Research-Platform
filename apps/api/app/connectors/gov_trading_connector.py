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
import re
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

# Congress.gov legislation cache — shorter TTL than PTR/Form4 cache above.
# Gap 1 fix (lead review, F-05): 20 min balances data freshness against the
# 1,000 req/hr rate limit of our registered CONGRESS_API_KEY. At ~16 req/min
# max allowed, a 20-min window means even a burst of concurrent users mostly
# hits cache instead of the live API.
CONGRESS_CACHE_TTL = 1200  # 20 minutes
CONGRESS_BASE = "https://api.congress.gov/v3"

# Known committee system codes (verified against Congress.gov /v3/committee).
# Wrong codes return 404 — use these exact strings with get_committee_bills().
COMMITTEE_CODES = {
    # Senate
    "senate_banking":       "ssbk00",   # Banking, Housing, and Urban Affairs
    "senate_finance":       "ssfi00",   # Finance
    "senate_armed_services":"ssas00",   # Armed Services
    "senate_judiciary":     "ssju00",   # Judiciary
    "senate_budget":        "ssbu00",   # Budget
    "senate_commerce":      "sscm00",   # Commerce, Science, and Transportation
    "senate_health":        "sshr00",   # Health, Education, Labor, and Pensions
    "senate_energy":        "sseg00",   # Energy and Natural Resources
    "senate_small_biz":     "sssb00",   # Small Business and Entrepreneurship
    # House
    "house_financial_svcs": "hsba00",   # Financial Services
    "house_judiciary":      "hsju00",   # Judiciary
}


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
        import math
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
            raw_shares = row.get("Shares", 0)
            raw_value = row.get("Value", 0)
            shares_val = raw_shares if raw_shares is not None else 0
            value_val = raw_value if raw_value is not None else 0
            try:
                shares = int(shares_val) if not (isinstance(shares_val, float) and math.isnan(shares_val)) else 0
            except Exception:
                shares = 0
            try:
                value = float(value_val) if not (isinstance(value_val, float) and math.isnan(value_val)) else 0.0
            except Exception:
                value = 0.0
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
    - Senate PTR filers (via senate-stock-watcher / Senate eFD)
    - Recent SEC Form 4 insider transactions
    """
    year = datetime.now().year

    try:
        ptr_filers = get_house_ptr_filers(year=year, days=days)
    except Exception:
        ptr_filers = []

    try:
        senate_filers = get_senate_ptr_filers(days=days)
    except Exception:
        senate_filers = []

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
    total_senate_filers = len(senate_filers)

    # State breakdown (House only — Senate data doesn't carry state_dst)
    by_state = defaultdict(int)
    for m in ptr_filers:
        st = (m.get("state_dst") or "")[:2]
        by_state[st] += 1
    top_states = sorted(by_state.items(), key=lambda x: x[1], reverse=True)[:10]

    # Combined recent filers (both chambers, sorted by filing_date desc)
    combined_recent = sorted(
        ptr_filers + senate_filers,
        key=lambda x: x.get("filing_date", ""),
        reverse=True,
    )[:25]

    return {
        "period_days": days,
        "total_ptr_disclosures": total_ptr + total_senate_filers,
        "house_ptr_filers": total_ptr,
        "senate_ptr_filers": total_senate_filers,
        "recent_ptr_filers": combined_recent,
        "most_active_members": active_members,
        "top_states_by_ptr": [{"state": s, "count": c} for s, c in top_states],
        "recent_sec_form4_insiders": form4_trades[:20],
        "data_sources": [
            "House Clerk Annual FD ZIP (PTR type P = stock trades)",
            "Senate eFD via senate-stock-watcher (github.com/timothycarambat)",
            "SEC EDGAR EFTS Full-Text Search (Form 4)",
        ],
        "note": "PTR = Periodic Transaction Report under the STOCK Act. Individual trade details require fetching per-filing PDFs.",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ─── Senate STOCK Act Disclosures (senate-stock-watcher) ─────────────────────
#
# The House Clerk ZIP only covers House members. Senate PTRs are filed on a
# separate system (efdsearch.senate.gov). We pull pre-normalised JSON from the
# community-maintained senate-stock-watcher GitHub repo (MIT licence, public
# domain US government data). Two URL fallbacks are used in case GitHub CDN is
# slow; the data is then cached for 4 hours to avoid hammering the source.

SENATE_WATCHER_URL = (
    "https://raw.githubusercontent.com/timothycarambat/"
    "senate-stock-watcher-data/master/aggregate/all_transactions_for_senators.json"
)
SENATE_WATCHER_FALLBACK = (
    "https://raw.githubusercontent.com/timothycarambat/"
    "senate-stock-watcher-data/master/aggregate/all_transactions.json"
)
SENATE_CACHE_TTL = 14400  # 4 hours — data updates once/day at most

# ─── CongressInvests (primary live source, 2021-present) ─────────────────────
# Free API, no API key, 100 req/day limit.  Covers both House + Senate PTRs
# from the official eFD / House Clerk portals, updated within hours of filing.
# senate-stock-watcher data only reaches 2021-03 (repo abandoned); we use
# CongressInvests as primary and fall back to the watcher for pre-2021 history.

CONGRESS_INVESTS_BASE = "https://congressinvests.com"
CONGRESS_INVESTS_TTL = 3600  # 1-hour cache — API updates hourly


def _load_senate_watcher() -> list:
    """
    Load all Senate PTR filings from senate-stock-watcher GitHub repo.
    Returns a list of senator filing dicts, each containing a 'transactions' list.
    Result is module-level cached for 4 hours.
    """
    cache_key = "senate_watcher_all"
    if cache_key in _cache and (time.time() - _cache_ts.get(cache_key, 0)) < SENATE_CACHE_TTL:
        return _cache[cache_key]

    for url in [SENATE_WATCHER_URL, SENATE_WATCHER_FALLBACK]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list) and data:
                _cache[cache_key] = data
                _cache_ts[cache_key] = time.time()
                log.info("Senate watcher loaded: %d senator records from %s", len(data), url)
                return data
        except Exception as e:
            log.warning("Senate watcher fetch failed (%s): %s", url, e)

    log.error("All Senate watcher sources failed — returning empty list")
    return _cache.get(cache_key, [])


def _clean_ticker(raw: str) -> str:
    """Strip HTML anchor tags from tickers that come wrapped in <a href=...>TICK</a>."""
    if not raw or raw == "--":
        return ""
    clean = re.sub(r"<[^>]+>", "", raw).strip()
    return clean if clean != "--" else ""


def _ci_get_all_trades(chamber: str = "", limit: int = 700) -> list:
    """
    Fetch all recent congressional trades from CongressInvests.
    Result is module-level cached for 1 hour.
    chamber: '' = both, 'Senate', 'House'
    """
    cache_key = f"ci_trades_{chamber.lower()}"
    if cache_key in _cache and (time.time() - _cache_ts.get(cache_key, 0)) < CONGRESS_INVESTS_TTL:
        return _cache[cache_key]

    all_trades = []
    offset = 0
    params = {"limit": 50}
    if chamber:
        params["chamber"] = chamber

    try:
        while True:
            params["offset"] = offset
            r = requests.get(f"{CONGRESS_INVESTS_BASE}/trades", params=params, headers=HEADERS, timeout=15)
            r.raise_for_status()
            data = r.json()
            batch = data.get("trades", [])
            if not batch:
                break
            all_trades.extend(batch)
            if not data.get("has_more", False) or len(all_trades) >= limit:
                break
            offset += 50
    except Exception as e:
        log.warning("CongressInvests fetch failed (chamber=%s): %s", chamber, e)

    if all_trades:
        _cache[cache_key] = all_trades
        _cache_ts[cache_key] = time.time()
        log.info("CongressInvests loaded: %d trades (chamber=%s)", len(all_trades), chamber or "all")

    return all_trades or _cache.get(cache_key, [])


def _ci_normalize(trade: dict, source_label: str = "CongressInvests / Senate eFD") -> dict:
    """Normalize a CongressInvests trade record to our internal format."""
    return {
        "name": trade.get("member", ""),
        "chamber": (trade.get("chamber") or "").lower(),
        "ticker": (trade.get("ticker") or "").upper(),
        "asset_description": (trade.get("asset") or "")[:120],
        "transaction": trade.get("trade_type", ""),
        "amount": trade.get("amount", ""),
        "date": trade.get("tx_date", ""),
        "filing_date": trade.get("disclosed", ""),
        "ptr_link": trade.get("link", ""),
        "source": source_label,
    }


def get_senate_ptr_filers(days: int = 90) -> list:
    """
    Senate members who filed PTRs.
    Primary: CongressInvests (2021-present). Fallback: senate-stock-watcher (2012-2021).
    Normalised to same shape as get_house_ptr_filers().
    """
    results = []
    seen_names = set()

    # ── Primary: CongressInvests ──────────────────────────────────────────────
    try:
        ci_trades = _ci_get_all_trades(chamber="Senate")
        cutoff = datetime.now() - timedelta(days=days)
        per_member: dict = {}
        for trade in ci_trades:
            member = trade.get("member", "")
            disc_date = trade.get("disclosed", "")
            try:
                dt = datetime.strptime(disc_date[:10], "%Y-%m-%d")
                if dt < cutoff:
                    continue
            except Exception:
                pass
            if member not in per_member:
                per_member[member] = {"latest": disc_date, "count": 0}
            per_member[member]["count"] += 1
            if disc_date > per_member[member]["latest"]:
                per_member[member]["latest"] = disc_date
        for member, info in per_member.items():
            parts = member.split()
            first = parts[0] if parts else ""
            last = parts[-1] if parts else ""
            results.append({
                "first": first,
                "last": last,
                "name": member,
                "chamber": "senate",
                "filing_date": info["latest"],
                "filing_type": "P",
                "transaction_count": info["count"],
                "source": "CongressInvests / Senate eFD (live)",
            })
            seen_names.add(member.lower())
    except Exception as e:
        log.warning("CongressInvests senate filers failed: %s", e)

    # ── Fallback: senate-stock-watcher ────────────────────────────────────────
    try:
        all_filings = _load_senate_watcher()
        cutoff_sw = datetime.now() - timedelta(days=max(days, 3650))
        for filing in all_filings:
            raw_date = filing.get("date_recieved", "")
            dt = None
            for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(raw_date, fmt)
                    break
                except Exception:
                    pass
            if dt and dt < cutoff_sw:
                continue
            first = (filing.get("first_name") or "").strip()
            last = (filing.get("last_name") or "").strip()
            full_name = f"{first} {last}".strip().lower()
            if full_name in seen_names:
                continue
            results.append({
                "first": first,
                "last": last,
                "name": f"{first} {last}".strip(),
                "chamber": "senate",
                "filing_date": raw_date,
                "filing_type": "P",
                "ptr_link": filing.get("ptr_link", ""),
                "transaction_count": len(filing.get("transactions") or []),
                "source": "senate-stock-watcher (archived 2012-2021)",
            })
    except Exception as e:
        log.warning("senate-stock-watcher filers fallback failed: %s", e)

    return results


def get_senate_trades_by_member(name: str, days: int = 3650) -> list:
    """
    All Senate PTR transactions for a named senator.
    Primary source: CongressInvests API (2021-present, live data).
    Fallback: senate-stock-watcher GitHub dataset (2012-2021, archived).
    Merges both to give the widest possible history window.
    """
    name_lower = name.lower().strip()
    name_parts = name_lower.split()
    if not name_parts:
        return []
    target_last = name_parts[-1]
    target_first = name_parts[0]

    cutoff = datetime.now() - timedelta(days=days)
    results = []
    seen = set()

    # ── Primary: CongressInvests (live, 2021-present) ─────────────────────────
    try:
        ci_trades = _ci_get_all_trades(chamber="Senate")
        for trade in ci_trades:
            member = (trade.get("member") or "").lower()
            member_parts = member.split()
            if not member_parts:
                continue
            # Match on last name (last word of stored name)
            if target_last not in member:
                continue
            # Do NOT require first-name match — CongressInvests stores legal names
            # (e.g. "Thomas H Tuberville") which often differ from tracking names
            # ("Tommy Tuberville"). Last-name uniqueness is sufficient for senators.
            tx_date = trade.get("tx_date", "")
            dt = None
            for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
                try:
                    dt = datetime.strptime(tx_date[:10], fmt)
                    break
                except Exception:
                    pass
            if dt and dt < cutoff:
                continue
            ticker = (trade.get("ticker") or "").upper()
            txn_type = trade.get("trade_type", "")
            amount = trade.get("amount", "")
            key = (member, ticker, tx_date, txn_type, amount)
            if key in seen:
                continue
            seen.add(key)
            results.append(_ci_normalize(trade, "CongressInvests / Senate eFD (live)"))
    except Exception as e:
        log.warning("CongressInvests senator lookup failed for %s: %s", name, e)

    # ── Fallback: senate-stock-watcher (archived, 2012-2021) ──────────────────
    try:
        all_filings = _load_senate_watcher()
        for filing in all_filings:
            first = (filing.get("first_name") or "").lower().strip()
            last = (filing.get("last_name") or "").lower().strip()
            last_clean = re.sub(r",\s*(jr\.?|sr\.?|ii+|iv+|v+)\s*$", "", last).strip()
            if last_clean != target_last and not last_clean.startswith(target_last):
                continue
            first_parts = [p.strip("().") for p in re.split(r"[\s]+", first) if p.strip("().")]
            first_matches = any(p.startswith(target_first[:3]) for p in first_parts if p)
            if not first_matches:
                continue
            senator_name = f"{filing.get('first_name', '').strip()} {filing.get('last_name', '').strip()}".strip()
            filing_date = filing.get("date_recieved", "")
            for txn in (filing.get("transactions") or []):
                ticker = _clean_ticker(txn.get("ticker", ""))
                txn_date = txn.get("transaction_date", "")
                txn_type = txn.get("type", "")
                amount = txn.get("amount", "")
                asset = txn.get("asset_description", "")
                dt = None
                for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(txn_date, fmt)
                        break
                    except Exception:
                        pass
                if dt and dt < cutoff:
                    continue
                key = (senator_name.lower(), ticker, txn_date, txn_type, amount)
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "name": senator_name,
                    "chamber": "senate",
                    "ticker": ticker,
                    "asset_description": (asset[:100] if asset else ""),
                    "transaction": txn_type,
                    "amount": amount,
                    "filing_date": filing_date,
                    "date": txn_date,
                    "owner": txn.get("owner", "Self"),
                    "ptr_link": txn.get("ptr_link", filing.get("ptr_link", "")),
                    "source": "Senate eFD / senate-stock-watcher (archived 2012-2021)",
                })
    except Exception as e:
        log.warning("senate-stock-watcher fallback failed for %s: %s", name, e)

    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    return results


def get_recent_congress_trades(days: int = 30, limit: int = 50) -> list:
    """Get recent congressional PTR filers — House + Senate combined."""
    house = get_house_ptr_filers(days=days)
    senate = get_senate_ptr_filers(days=days)
    combined = house + senate
    combined.sort(key=lambda x: x.get("filing_date", ""), reverse=True)
    return combined[:limit]


def get_trades_by_ticker(ticker: str, days: int = 365) -> list:
    """
    All congressional + insider trades for a specific stock.
    Combines: CongressInvests (House+Senate live), SEC Form 4, senate-stock-watcher fallback.
    """
    import math

    def _sanitize(obj):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(v) for v in obj]
        return obj

    ticker_upper = ticker.upper().strip()
    cutoff = datetime.now() - timedelta(days=days)
    seen = set()
    results = []

    # ── CongressInvests live feed (House + Senate, 2021-present) ─────────────
    try:
        r = requests.get(
            f"{CONGRESS_INVESTS_BASE}/trades/{ticker_upper}",
            headers=HEADERS, timeout=15,
        )
        if r.status_code == 200:
            for trade in r.json().get("trades", []):
                tx_date = trade.get("tx_date", "")
                dt = None
                for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
                    try:
                        dt = datetime.strptime(tx_date[:10], fmt)
                        break
                    except Exception:
                        pass
                if dt and dt < cutoff:
                    continue
                key = (trade.get("member", "").lower(), tx_date, trade.get("trade_type", ""))
                if key in seen:
                    continue
                seen.add(key)
                results.append(_ci_normalize(trade, f"CongressInvests / {(trade.get('chamber') or 'Congress')} eFD (live)"))
    except Exception as e:
        log.warning("CongressInvests ticker search failed for %s: %s", ticker_upper, e)

    # ── SEC Form 4 insider trades (corporate officers/directors) ─────────────
    insider_trades = _sanitize(get_insider_trades_for_ticker(ticker_upper, days=days))
    results.extend(insider_trades)

    # ── Senate-stock-watcher fallback (2012-2021 historical) ─────────────────
    try:
        for filing in _load_senate_watcher():
            for txn in (filing.get("transactions") or []):
                raw_ticker = _clean_ticker(txn.get("ticker", ""))
                if raw_ticker.upper() != ticker_upper:
                    continue
                txn_date = txn.get("transaction_date", "")
                dt = None
                for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(txn_date, fmt)
                        break
                    except Exception:
                        pass
                if dt and dt < cutoff:
                    continue
                first = (filing.get("first_name") or "").strip()
                last = (filing.get("last_name") or "").strip()
                key = (f"{first} {last}".strip().lower(), txn_date, txn.get("type","").lower())
                if key in seen:
                    continue
                seen.add(key)
                results.append({
                    "name": f"{first} {last}".strip(),
                    "chamber": "senate",
                    "ticker": ticker_upper,
                    "asset_description": (txn.get("asset_description") or "")[:100],
                    "transaction": txn.get("type", ""),
                    "amount": txn.get("amount", ""),
                    "date": txn_date,
                    "filing_date": filing.get("date_recieved", ""),
                    "source": "Senate eFD / senate-stock-watcher (archived 2012-2021)",
                })
    except Exception as e:
        log.warning("Senate watcher ticker search failed for %s: %s", ticker_upper, e)

    results.sort(key=lambda x: x.get("date", ""), reverse=True)
    return results


def _politician_name_matches(target_name: str, m_first: str, m_last: str) -> bool:
    """
    Robust name matcher for House Financial Disclosure records.

    The naive "target_name in (first + ' ' + last)" substring check breaks
    the moment a filer's record includes a middle name/initial — e.g.
    "michael mccaul" is NOT a substring of "michael t. mccaul", even though
    it's the same person. That silently zeroed-out several tracked members
    (Michael McCaul confirmed live). Instead we match first/last tokens
    independently.
    """
    parts = target_name.lower().split()
    if not parts:
        return False
    target_first, target_last = parts[0], parts[-1]
    m_first_l = (m_first or "").lower().strip()
    m_last_l = (m_last or "").lower().strip()
    if not m_first_l or not m_last_l:
        return False
    first_ok = m_first_l.split()[0] == target_first
    last_ok = m_last_l == target_last
    return first_ok and last_ok


def get_trades_by_member(name: str, years: int = 3) -> list:
    """
    Find PTR filings by a specific congressional member, searching the
    current year plus the `years - 1` prior years.

    A single year's House FD ZIP often has very few (or zero) PTR filings
    for a given member simply because they haven't traded yet that year —
    that made most profiles look "blank" even for active traders. Searching
    a rolling multi-year window gives a realistic view of trading activity.
    """
    current_year = datetime.now().year
    seen = set()
    results = []
    for yr in range(current_year, current_year - years, -1):
        for m in _load_house_fd(yr):
            if m.get("filing_type") != "P":
                continue
            if not _politician_name_matches(name, m.get("first", ""), m.get("last", "")):
                continue
            key = (m.get("doc_id"), m.get("filing_date"), m.get("year"))
            if key in seen:
                continue
            seen.add(key)
            results.append({**m, "name": f"{m['first']} {m['last']}"})
    results.sort(key=lambda x: x.get("filing_date", ""), reverse=True)
    return results


def get_most_traded_tickers(days: int = 90, top_n: int = 20) -> list:
    """
    Since individual PTR trade data requires PDF parsing,
    returns a summary of congressional trading activity by state/member.
    """
    return get_most_traded_tickers_congress(top_n=top_n)


def get_most_active_members(days: int = 90, top_n: int = 20) -> list:
    """Most active congressional traders based on PTR filings."""
    return get_most_active_members_congress(top_n=top_n)


# ─── Named Politician / Figure Tracker ───────────────────────────────────────

# Known politicians with their House/Senate names for searching
TRACKED_POLITICIANS = {
    "nancy_pelosi": {"name": "Nancy Pelosi", "chamber": "house", "state": "CA", "party": "D"},
    "mitch_mcconnell": {"name": "Mitch McConnell", "chamber": "senate", "state": "KY", "party": "R"},
    "josh_gottheimer": {"name": "Josh Gottheimer", "chamber": "house", "state": "NJ", "party": "D"},
    "ro_khanna": {"name": "Ro Khanna", "chamber": "house", "state": "CA", "party": "D"},
    "suzan_delbene": {"name": "Suzan DelBene", "chamber": "house", "state": "WA", "party": "D"},
    "chuck_schumer": {"name": "Chuck Schumer", "chamber": "senate", "state": "NY", "party": "D"},
    "elizabeth_warren": {"name": "Elizabeth Warren", "chamber": "senate", "state": "MA", "party": "D"},
    "bernie_sanders": {"name": "Bernie Sanders", "chamber": "senate", "state": "VT", "party": "I"},
    "marco_rubio": {"name": "Marco Rubio", "chamber": "senate", "state": "FL", "party": "R"},
    "ted_cruz": {"name": "Ted Cruz", "chamber": "senate", "state": "TX", "party": "R"},
    "mark_kelly": {"name": "Mark Kelly", "chamber": "senate", "state": "AZ", "party": "D"},
    "tommy_tuberville": {"name": "Tommy Tuberville", "chamber": "senate", "state": "AL", "party": "R"},
    "dan_crenshaw": {"name": "Dan Crenshaw", "chamber": "house", "state": "TX", "party": "R"},
    "michael_mccaul": {"name": "Michael McCaul", "chamber": "house", "state": "TX", "party": "R"},
    "marjorie_taylor_greene": {"name": "Marjorie Taylor Greene", "chamber": "house", "state": "GA", "party": "R"},
}


# ─── Congress.gov Legislation API (F-05) ─────────────────────────────────────
#
# Gap fixes applied per lead review (docs/api/CONGRESS_GOV_IMPLEMENTATION_PLAN_WITH_GAP_FIXES.md):
#   Gap 1 — 20-min TTL cache (CONGRESS_CACHE_TTL above) on every call below.
#   Gap 3 — Congress.gov is a FREE government API. There is no paid tier.
#           CONGRESS_API_KEY (1,000 req/hr) already exists in .env — just wasn't read.
#   Gap 4 — `import os` verified present at top of this file (line 11).

def _get_congress_api_key() -> str:
    """
    Read CONGRESS_API_KEY from environment. Falls back to the public
    DEMO_KEY (30 req/hr, shared across all callers) only if the env var
    is unset — e.g. local dev without a .env file configured yet.
    """
    return os.environ.get("CONGRESS_API_KEY", "DEMO_KEY")


def _congress_get(cache_key: str, url: str, params: Optional[dict] = None, timeout: int = 10) -> dict:
    """
    Cached GET wrapper for Congress.gov API v3.

    - Injects api_key from CONGRESS_API_KEY (Phase 1 fix — replaces hardcoded DEMO_KEY).
    - 20-min TTL cache (Gap 1 fix) — protects the 1,000 req/hr limit under concurrent use.
    - On network/HTTP error, returns last-known cached value if present, else {} —
      never raises, so callers degrade gracefully (Risk Assessment §8 of the proposal).
    """
    now = time.time()
    if cache_key in _cache and (now - _cache_ts.get(cache_key, 0)) < CONGRESS_CACHE_TTL:
        return _cache[cache_key]

    full_params = {**(params or {}), "api_key": _get_congress_api_key(), "format": "json"}
    try:
        r = requests.get(url, params=full_params, headers={"User-Agent": "Finance-Platform/1.0"}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("Congress.gov fetch %s: %s", url, e)
        return _cache.get(cache_key, {})

    _cache[cache_key] = data
    _cache_ts[cache_key] = now
    return data


def search_bills(query: str, from_date: str = None, to_date: str = None, limit: int = 20) -> list:
    """Free-text bill search. GET /v3/bill?query=... (e.g. 'AI regulation', 'banking', 'crypto')."""
    if not query or not query.strip():
        return []
    limit = max(1, min(limit, 100))
    cache_key = f"bill_search_{query.lower().strip()}_{from_date}_{to_date}_{limit}"
    params = {"query": query.strip(), "limit": limit}
    if from_date:
        params["fromDateTime"] = f"{from_date}T00:00:00Z"
    if to_date:
        params["toDateTime"] = f"{to_date}T00:00:00Z"

    data = _congress_get(cache_key, f"{CONGRESS_BASE}/bill", params)
    bills = data.get("bills", []) or []
    return [
        {
            "congress": b.get("congress"),
            "type": b.get("type", ""),
            "number": b.get("number", ""),
            "title": (b.get("title") or "")[:200],
            "updated": b.get("updateDate", ""),
            "latest_action": (b.get("latestAction") or {}).get("text") or "",
            "latest_action_date": (b.get("latestAction") or {}).get("actionDate") or "",
            "url": b.get("url", ""),
        }
        for b in bills[:limit]
    ]


def get_bill_details(congress: int, bill_type: str, bill_number: int) -> Optional[dict]:
    """Full bill info. GET /v3/bill/{congress}/{type}/{number}"""
    cache_key = f"bill_{congress}_{bill_type}_{bill_number}"
    data = _congress_get(cache_key, f"{CONGRESS_BASE}/bill/{congress}/{bill_type}/{bill_number}")
    bill = data.get("bill")
    if not bill:
        return None
    return {
        "congress": bill.get("congress"),
        "type": bill.get("type", ""),
        "number": bill.get("number", ""),
        "title": bill.get("title", ""),
        "introduced_date": bill.get("introducedDate", ""),
        "policy_area": (bill.get("policyArea") or {}).get("name") or "",
        "latest_action": (bill.get("latestAction") or {}).get("text") or "",
        "latest_action_date": (bill.get("latestAction") or {}).get("actionDate") or "",
        "sponsors": [
            {"name": s.get("fullName", ""), "party": s.get("party", ""), "state": s.get("state", "")}
            for s in (bill.get("sponsors") or [])
        ],
        "cosponsors_count": (bill.get("cosponsors") or {}).get("count", 0),
        "summaries_count": (bill.get("summaries") or {}).get("count", 0),
        "text_versions_url": (bill.get("textVersions") or {}).get("url", ""),
    }


def get_bill_text(congress: int, bill_type: str, bill_number: int) -> list:
    """
    Bill text version links (XML/PDF/HTML — not inline full text; see §12
    'What Congress.gov API Can NOT Do' in the feature proposal).
    GET /v3/bill/{congress}/{type}/{number}/text
    """
    cache_key = f"bill_text_{congress}_{bill_type}_{bill_number}"
    data = _congress_get(cache_key, f"{CONGRESS_BASE}/bill/{congress}/{bill_type}/{bill_number}/text")
    versions = data.get("textVersions", []) or []
    return [
        {
            "type": v.get("type", ""),
            "date": v.get("date", ""),
            "formats": [{"type": f.get("type"), "url": f.get("url")} for f in (v.get("formats") or [])],
        }
        for v in versions
    ]


def get_bill_cosponsors(congress: int, bill_type: str, bill_number: int, limit: int = 20) -> list:
    """Members who co-signed a bill. GET /v3/bill/{congress}/{type}/{number}/cosponsors"""
    limit = max(1, min(limit, 100))
    cache_key = f"bill_cosponsors_{congress}_{bill_type}_{bill_number}_{limit}"
    data = _congress_get(cache_key, f"{CONGRESS_BASE}/bill/{congress}/{bill_type}/{bill_number}/cosponsors", {"limit": limit})
    cosponsors = data.get("cosponsors", []) or []
    return [
        {
            "name": c.get("fullName", ""),
            "party": c.get("party", ""),
            "state": c.get("state", ""),
            "sponsorship_date": c.get("sponsorshipDate", ""),
        }
        for c in cosponsors[:limit]
    ]


def get_recent_laws(congress: int = None, limit: int = 20) -> list:
    """Bills that became actual laws. GET /v3/law/{congress}"""
    congress = congress or 118
    limit = max(1, min(limit, 100))
    cache_key = f"laws_{congress}_{limit}"
    data = _congress_get(cache_key, f"{CONGRESS_BASE}/law/{congress}", {"limit": limit})
    laws = data.get("bills", []) or []
    return [
        {
            "congress": l.get("congress"),
            "type": l.get("type", ""),
            "number": l.get("number", ""),
            "title": (l.get("title") or "")[:200],
            "law_number": (l.get("laws") or [{}])[0].get("number", "") if l.get("laws") else "",
            "law_type": (l.get("laws") or [{}])[0].get("type", "") if l.get("laws") else "",
        }
        for l in laws[:limit]
    ]


def get_committee_bills(chamber: str, committee_code: str, limit: int = 20) -> list:
    """
    All bills assigned to a specific committee.

    Use the system code from Congress.gov, e.g.:
      Senate Banking, Housing & Urban Affairs → 'ssbk00'
      Senate Finance                          → 'ssfi00'
      Senate Armed Services                   → 'ssas00'
      Senate Judiciary                        → 'ssju00'
      Senate Budget                           → 'ssbu00'
      House Financial Services                → 'hsba00'
      House Ways and Means                    → pass 'hswm00'
      House Judiciary                         → 'hsju00'

    To discover any committee's systemCode call:
      GET https://api.congress.gov/v3/committee/{chamber}?api_key=...
    """
    limit = max(1, min(limit, 100))
    chamber = (chamber or "").lower().strip()
    cache_key = f"committee_bills_{chamber}_{committee_code}_{limit}"
    data = _congress_get(cache_key, f"{CONGRESS_BASE}/committee/{chamber}/{committee_code}/bills", {"limit": limit})
    container = data.get("committee-bills", data)
    bills = container.get("bills", []) if isinstance(container, dict) else []
    return [
        {
            "congress": b.get("congress"),
            "type": b.get("type", ""),
            "number": b.get("number", ""),
            "action_date": b.get("actionDate", ""),
            "relationship_type": b.get("relationshipType", ""),
        }
        for b in bills[:limit]
    ]


def get_crs_reports(limit: int = 20) -> list:
    """Congressional Research Service non-partisan policy analysis reports. GET /v3/crsreport"""
    limit = max(1, min(limit, 100))
    cache_key = f"crs_reports_{limit}"
    data = _congress_get(cache_key, f"{CONGRESS_BASE}/crsreport", {"limit": limit})
    reports = data.get("CRSReports", []) or []
    return [
        {
            "id": r.get("id", ""),
            "title": r.get("title", ""),
            "type": r.get("type", ""),
            "status": r.get("status", ""),
            "publish_date": r.get("publishDate", ""),
            "url": r.get("url", ""),
        }
        for r in reports[:limit]
    ]


def get_bioguide_id(politician_name: str) -> Optional[str]:
    """Look up a member's bioguideId by name — links a tracked politician to Congress.gov."""
    cache_key = "member_list_all"
    data = _congress_get(cache_key, f"{CONGRESS_BASE}/member", {"limit": 250})
    members = data.get("members", []) or []
    name_lower = politician_name.lower()
    parts = name_lower.split()
    if not parts:
        return None
    first, last = parts[0], parts[-1]
    for m in members:
        m_name = (m.get("directOrderName") or m.get("name") or "").lower()
        if last in m_name and first in m_name:
            return m.get("bioguideId")
    return None


def get_member_votes(bioguide_id: str, limit: int = 20) -> list:
    """
    Legislative activity for a member (sponsor + cosponsor roles).

    Note: Congress.gov API v3 does not expose per-member roll-call vote
    positions directly (see §12 of the feature proposal) — that data lives
    on individual bill/roll-call records, not the member endpoint. This
    returns sponsored + cosponsored bills as the best available proxy for
    "how active/aligned" a member is on legislation, tagged by role.
    """
    limit = max(1, min(limit, 100))
    sponsored = _congress_get(
        f"member_sponsored_{bioguide_id}_{limit}",
        f"{CONGRESS_BASE}/member/{bioguide_id}/sponsored-legislation",
        {"limit": limit},
    )
    cosponsored = _congress_get(
        f"member_cosponsored_{bioguide_id}_{limit}",
        f"{CONGRESS_BASE}/member/{bioguide_id}/cosponsored-legislation",
        {"limit": limit},
    )

    result = []
    for bill in (sponsored.get("sponsoredLegislation") or [])[:limit]:
        result.append({
            "type": bill.get("type", ""), "number": bill.get("number", ""),
            "title": (bill.get("title") or "")[:150], "role": "sponsor",
            "introduced": bill.get("introducedDate", ""),
            "latest_action": (bill.get("latestAction") or {}).get("text") or "",
        })
    for bill in (cosponsored.get("cosponsoredLegislation") or [])[:limit]:
        result.append({
            "type": bill.get("type", ""), "number": bill.get("number", ""),
            "title": (bill.get("title") or "")[:150], "role": "cosponsor",
            "introduced": bill.get("introducedDate", ""),
            "latest_action": (bill.get("latestAction") or {}).get("text") or "",
        })
    return result[:limit]


def get_politician_profile(politician_id: str) -> dict:
    """
    Get complete financial trading profile for a named politician.
    Combines PTR filings (House) + SEC Form 4 + Congress.gov legislation.
    """
    info = TRACKED_POLITICIANS.get(politician_id.lower().replace(" ", "_"))
    if not info:
        # Try by name
        for pid, pinfo in TRACKED_POLITICIANS.items():
            if politician_id.lower() in pinfo["name"].lower():
                info = pinfo
                break
    if not info:
        return {"error": f"Politician '{politician_id}' not found", "available": list(TRACKED_POLITICIANS.keys())}

    name = info["name"]
    last_name = name.split()[-1]
    first_name = name.split()[0]
    chamber = info.get("chamber", "house")

    # Get their PTR filings — Senate via senate-stock-watcher, House via Clerk ZIP
    if chamber == "senate":
        ptr_filings = get_senate_trades_by_member(name, days=3650)
    else:
        ptr_filings = get_trades_by_member(name)

    # Get Congress.gov recent bills sponsored.
    # Phase 1 fix: real CONGRESS_API_KEY (1,000 req/hr) via _congress_get(),
    # replacing the two hardcoded "DEMO_KEY" (30 req/hr, shared) calls that
    # silently returned empty legislation once the shared quota was exhausted.
    legislation = []
    try:
        members = _congress_get("member_list_all", f"{CONGRESS_BASE}/member", {"limit": 250}).get("members", []) or []
        for m in members:
            m_name = m.get("directOrderName") or m.get("name") or ""
            if last_name.lower() in m_name.lower() and (
                first_name.lower() in m_name.lower() or info.get("state", "") in (m.get("state") or "")
            ):
                bioguide_id = m.get("bioguideId", "")
                if bioguide_id:
                    leg_data = _congress_get(
                        f"member_sponsored_{bioguide_id}_10",
                        f"{CONGRESS_BASE}/member/{bioguide_id}/sponsored-legislation",
                        {"limit": 10},
                    ).get("sponsoredLegislation", []) or []
                    for bill in leg_data[:10]:
                        legislation.append({
                            "title": (bill.get("title") or "")[:150],
                            "type": bill.get("type", ""),
                            "number": bill.get("number", ""),
                            "introduced": bill.get("introducedDate", ""),
                            "policy_area": ((bill.get("policyArea") or {}).get("name") or "") if isinstance(bill.get("policyArea"), dict) else "",
                            "latest_action": ((bill.get("latestAction") or {}).get("text") or "") if isinstance(bill.get("latestAction"), dict) else "",
                        })
                break
    except Exception as e:
        log.debug("Congress.gov legislation fetch error: %s", e)

    # Cross-reference: find legislation topics matching their traded tickers
    # (basic keyword overlap)
    traded_sectors = []
    for filing in ptr_filings[:20]:
        doc_id = filing.get("doc_id", "")
        # Map doc_ids to known company types through filing dates
        traded_sectors.append(filing.get("state_dst", ""))

    # Analyze legislation themes vs trading sectors
    # (title/policy_area defensively defaulted — Congress.gov can return a
    # present-but-null "policyArea"/"title" key rather than omitting it,
    # which crashed the str concatenation below with a live-data bug found
    # during Phase 1 smoke testing.)
    financial_legislation = [l for l in legislation if any(
        kw in ((l.get("title") or "") + (l.get("policy_area") or "")).lower()
        for kw in ["finance", "banking", "investment", "securities", "trade", "tax",
                   "defense", "technology", "health", "energy", "pharmaceut"]
    )]

    base_note = "PTR = Periodic Transaction Report (STOCK Act). Individual trade details require PDF parsing of specific disclosure documents."
    if chamber == "senate" and not ptr_filings:
        note = (f"No Senate PTR filings found for {name} in the last 3 years. "
                f"This can mean they haven't reported a disclosable stock trade recently, "
                f"or the Senate eFD record isn't yet in the senate-stock-watcher dataset. {base_note}")
    elif chamber == "senate":
        note = (f"Senate PTR data sourced from efdsearch.senate.gov via senate-stock-watcher. {base_note}")
    elif not ptr_filings:
        note = (f"No House PTR filings found for {name} in the last 3 years. This can mean they haven't "
                f"reported a disclosable stock trade recently, or aren't currently serving in the House. "
                f"{base_note}")
    else:
        note = base_note

    return {
        "politician": {
            "name": name,
            "chamber": info.get("chamber", ""),
            "state": info.get("state", ""),
            "party": info.get("party", ""),
        },
        "ptr_filings_count": len(ptr_filings),
        "recent_ptr_filings": ptr_filings[:20],
        "recent_legislation_sponsored": legislation[:10],
        "financially_relevant_legislation": financial_legislation[:5],
        "disclosure_activity": {
            "total_ptrs": len(ptr_filings),
            "recent_filings_30d": sum(1 for f in ptr_filings
                if f.get("filing_date", "") > (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y")),
        },
        "note": note,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ─── F-03: Big Trade Scanner ─────────────────────────────────────────────────

def scan_big_trades(tickers: list, threshold: float = 500_000, days: int = 30) -> list:
    """
    Scan a list of tickers for insider trades above `threshold` USD.
    Uses get_insider_trades_for_ticker() (yfinance Form 4).
    Returns qualifying trade dicts sorted by value_usd desc.
    """
    qualifying = []
    for ticker in tickers:
        if not ticker:
            continue
        try:
            trades = get_insider_trades_for_ticker(ticker, days=days)
            for t in trades:
                if float(t.get("value_usd") or 0) >= threshold:
                    qualifying.append(t)
            time.sleep(0.5)  # avoid yfinance/SEC rate limits between tickers
        except Exception as e:
            log.warning("scan_big_trades error for %s: %s", ticker, e)
    qualifying.sort(key=lambda x: float(x.get("value_usd") or 0), reverse=True)
    return qualifying


def get_all_politicians_summary() -> list:
    """
    Trading activity summary for all tracked politicians.
    House members use the House Clerk disclosure ZIP.
    Senate members use the senate-stock-watcher GitHub dataset (Senate eFD).
    """
    results = []

    for pid, info in TRACKED_POLITICIANS.items():
        name = info["name"]
        chamber = info.get("chamber", "house")

        if chamber == "senate":
            ptrs = get_senate_trades_by_member(name, days=3650)
            data_note = "Senate PTR data sourced from efdsearch.senate.gov via senate-stock-watcher (2012–2021 dataset)."
        else:
            ptrs = get_trades_by_member(name, years=3)
            data_note = None

        results.append({
            "id": pid,
            "name": name,
            "chamber": chamber,
            "party": info.get("party"),
            "state": info.get("state"),
            "ptr_count": len(ptrs),
            "latest_filing": sorted([p.get("filing_date", p.get("date", "")) for p in ptrs if p.get("filing_date") or p.get("date")])[-1] if ptrs else None,
            "data_note": data_note,
        })

    return sorted(results, key=lambda x: x["ptr_count"], reverse=True)
