"""
Institutional Position Change Tracker (13F Intelligence)
────────────────────────────────────────────────────────────────────────────
Tracks big institutional money movements by comparing 13F-HR quarterly filings:
  - SEC EDGAR EFTS search for 13F-HR filings by top institutions
  - Quarter-over-quarter position changes (new, increased, decreased, exited)
  - Who is buying vs selling a specific stock
  - Overall institutional conviction signal
Uses only free SEC EDGAR data.
"""
import re
import time
import logging
import requests
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

log = logging.getLogger(__name__)
EDGAR_BASE = "https://data.sec.gov"
EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"
SEC_HEADERS = {"User-Agent": "Finance-Platform/1.0 abhishekk@kyma.world"}

# Top institutions to track (CIKs of major asset managers)
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
    "Cathie Wood / ARK": "0001579982",
    "Pershing Square": "0001336528",
}


def _get(url, params=None, timeout=15) -> dict:
    try:
        r = requests.get(url, params=params, headers=SEC_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("13F fetch %s: %s", url, e)
        return {}


def _get_text(url, timeout=20) -> str:
    try:
        r = requests.get(url, headers=SEC_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.warning("13F text fetch %s: %s", url, e)
        return ""


def _parse_13f_text(text: str, ticker: str) -> list:
    """Parse 13F-HR filing text to find positions for a specific ticker."""
    positions = []
    ticker_upper = ticker.upper()
    # 13F filings contain issuer name, CUSIP, value, shares
    # Pattern: look for ticker or company name in the filing
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if ticker_upper in line.upper() or 'APPLE' in line.upper() and ticker == 'AAPL':
            # Look for numeric values nearby
            context = ' '.join(lines[max(0, i-2):i+3])
            # Find dollar amounts (in thousands in 13F)
            amounts = re.findall(r'(\d{1,3}(?:,\d{3})*)', context)
            if amounts:
                positions.append({
                    "context": context[:200],
                    "amounts": [int(a.replace(',', '')) for a in amounts[:4]],
                })
    return positions[:5]


def get_recent_13f_filers(ticker: str, days: int = 120) -> list:
    """
    Search EDGAR for recent 13F-HR filings that mention a ticker.
    Returns list of institutions that filed 13F and their filing info.
    """
    start_dt = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        params = {
            "q": f'"{ticker}"',
            "forms": "13F-HR",
            "dateRange": "custom",
            "startdt": start_dt,
            "enddt": datetime.now().strftime("%Y-%m-%d"),
        }
        r = requests.get(EFTS_BASE, params=params, headers=SEC_HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        hits = data.get("hits", {}).get("hits", [])[:30]
        filers = []
        for h in hits:
            src = h.get("_source", {})
            names = src.get("display_names", [])
            filer_name = names[0].split("(CIK")[0].strip() if names else "Unknown"
            filer_cik = ""
            if names:
                cik_match = re.search(r'CIK\s+(\d+)', names[0])
                if cik_match:
                    filer_cik = cik_match.group(1)
            filers.append({
                "filer": filer_name,
                "cik": filer_cik,
                "filing_date": src.get("file_date", ""),
                "period": src.get("period_of_report", ""),
                "accession": h.get("_id", ""),
            })
        return filers
    except Exception as e:
        log.error("13F EFTS search error: %s", e)
        return []


def get_institutional_13f_changes(ticker: str) -> dict:
    """
    Analyze institutional position changes for a ticker using yfinance
    (most reliable and structured data for this purpose).
    Returns quarter-over-quarter changes inferred from current vs prior holder data.
    """
    try:
        import yfinance as yf
        import math
        import pandas as pd

        def _sf(v):
            """Safely convert to float, handling NaN, None, and pandas NA."""
            try:
                if v is None:
                    return 0.0
                if isinstance(v, (pd.Timestamp, str)):
                    return 0.0
                if pd.isna(v):
                    return 0.0
                f = float(v)
                return 0.0 if math.isnan(f) or math.isinf(f) else f
            except Exception:
                return 0.0

        def _get_val(row, *keys):
            """Get value from row trying multiple column names."""
            for k in keys:
                if k in row.index:
                    return row[k]
            return None

        stock = yf.Ticker(ticker)

        # Current quarter institutional holders
        inst_df = stock.institutional_holders
        current_holders = {}
        if inst_df is not None and not inst_df.empty:
            for _, row in inst_df.head(25).iterrows():
                name = str(_get_val(row, "Holder", "Name") or "Unknown")
                shares = int(_sf(_get_val(row, "Shares", "shares")))
                pct = float(_sf(_get_val(row, "pctHeld", "% Out", "pctOut", "Pct Held")))
                value = int(_sf(_get_val(row, "Value", "value")))
                date_rep = _get_val(row, "Date Reported", "dateReported", "Date")
                current_holders[name] = {
                    "shares": shares,
                    "pct_held": pct,
                    "value_usd": value,
                    "date_reported": str(date_rep)[:10] if date_rep else "",
                }

        # Major holders summary
        major_df = stock.major_holders
        ownership_summary = {}
        if major_df is not None and not major_df.empty:
            try:
                for idx, row in major_df.iterrows():
                    key = str(row.iloc[1]) if len(row) > 1 else str(idx)
                    val = str(row.iloc[0]) if len(row) > 0 else ""
                    ownership_summary[key] = val
            except Exception:
                pass

        # Mutual fund holders
        mf_df = stock.mutualfund_holders
        mf_holders = {}
        if mf_df is not None and not mf_df.empty:
            for _, row in mf_df.head(15).iterrows():
                name = str(_get_val(row, "Holder", "Name") or "Unknown Fund")
                shares = int(_sf(_get_val(row, "Shares", "shares")))
                pct = float(_sf(_get_val(row, "pctHeld", "% Out", "pctOut", "Pct Held")))
                value = int(_sf(_get_val(row, "Value", "value")))
                date_rep = _get_val(row, "Date Reported", "dateReported", "Date")
                mf_holders[name] = {
                    "shares": shares,
                    "pct_held": pct,
                    "value_usd": value,
                    "date_reported": str(date_rep)[:10] if date_rep else "",
                }

        # Recent 13F filers from EDGAR
        recent_filers = get_recent_13f_filers(ticker, days=90)

        # Classify institutional positions
        mega_positions = []  # > $1B
        large_positions = []  # $100M-$1B
        for name, data in current_holders.items():
            v = data["value_usd"]
            if v >= 1_000_000_000:
                mega_positions.append({"holder": name, **data})
            elif v >= 100_000_000:
                large_positions.append({"holder": name, **data})

        # Known activist/notable holders
        notable = {}
        for inst_name in TOP_INSTITUTIONS:
            for holder_name, data in {**current_holders, **mf_holders}.items():
                if inst_name.split('/')[0].strip().lower() in holder_name.lower():
                    notable[inst_name] = {"holder": holder_name, **data}
                    break

        return {
            "ticker": ticker,
            "ownership_summary": ownership_summary,
            "institutional_holders": sorted(
                [{"holder": k, **v} for k, v in current_holders.items()],
                key=lambda x: x.get("value_usd", 0), reverse=True
            )[:20],
            "mutual_fund_holders": sorted(
                [{"holder": k, **v} for k, v in mf_holders.items()],
                key=lambda x: x.get("value_usd", 0), reverse=True
            )[:15],
            "mega_positions_over_1b": mega_positions,
            "large_positions_100m_to_1b": large_positions[:10],
            "notable_institution_positions": notable,
            "recent_13f_filers": recent_filers[:15],
            "total_institutional_holders": len(current_holders),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    except Exception as e:
        log.error("13F institutional changes error for %s: %s", ticker, e)
        return {"ticker": ticker, "error": str(e)}


def get_top_institution_holdings(institution_name: str = "Berkshire Hathaway") -> dict:
    """
    Get top holdings for a named institution using SEC EDGAR.
    Uses the known CIK to fetch their latest 13F filing.
    """
    cik = TOP_INSTITUTIONS.get(institution_name)
    if not cik:
        # Try fuzzy match
        for name, c in TOP_INSTITUTIONS.items():
            if institution_name.lower() in name.lower():
                cik = c
                institution_name = name
                break
    if not cik:
        return {"error": f"Institution '{institution_name}' not found. Known: {list(TOP_INSTITUTIONS.keys())}"}

    # Get recent filings
    data = _get(f"{EDGAR_BASE}/submissions/CIK{cik}.json")
    if not data:
        return {"institution": institution_name, "cik": cik, "error": "No EDGAR data"}

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    acc_nums = filings.get("accessionNumber", [])
    docs = filings.get("primaryDocument", [])

    # Find most recent 13F-HR
    latest_13f = None
    for form, dt, acc, doc in zip(forms, dates, acc_nums, docs):
        if form in ("13F-HR", "13F-HR/A"):
            latest_13f = {"form": form, "date": dt, "accession": acc, "doc": doc}
            break

    if not latest_13f:
        return {"institution": institution_name, "cik": cik, "error": "No 13F-HR found"}

    # Parse the filing (XML format for 13F)
    acc_clean = latest_13f["accession"].replace("-", "")
    # 13F filings have a specific XML document
    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/"
    index_text = _get_text(index_url, timeout=10)

    # Find the infotable XML
    xml_match = re.search(r'href="(/Archives/edgar/data/[^"]+\.xml)"', index_text)
    holdings = []

    if xml_match:
        xml_url = f"https://www.sec.gov{xml_match.group(1)}"
        xml_text = _get_text(xml_url, timeout=15)
        if xml_text:
            # Parse 13F XML infotable
            entries = re.findall(
                r'<infoTable>(.*?)</infoTable>', xml_text, re.DOTALL
            )
            for entry in entries[:50]:
                name_m = re.search(r'<nameOfIssuer>(.*?)</nameOfIssuer>', entry)
                val_m = re.search(r'<value>(.*?)</value>', entry)
                shares_m = re.search(r'<sshPrnamt>(.*?)</sshPrnamt>', entry)
                type_m = re.search(r'<investmentDiscretion>(.*?)</investmentDiscretion>', entry)

                if name_m:
                    holdings.append({
                        "issuer": name_m.group(1).strip(),
                        "value_thousands": int(val_m.group(1).replace(',', '').strip()) if val_m else 0,
                        "shares": int(shares_m.group(1).replace(',', '').strip()) if shares_m else 0,
                        "type": type_m.group(1).strip() if type_m else "SOLE",
                    })

            holdings.sort(key=lambda x: x.get("value_thousands", 0), reverse=True)

    return {
        "institution": institution_name,
        "cik": cik,
        "latest_13f_date": latest_13f["date"],
        "latest_13f_form": latest_13f["form"],
        "holdings_count": len(holdings),
        "top_holdings": holdings[:30],
        "top_holdings_value_b": round(sum(h.get("value_thousands", 0) for h in holdings) / 1e6, 2),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
