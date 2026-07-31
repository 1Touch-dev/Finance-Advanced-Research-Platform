"""
Institutional Holdings Connector
─────────────────────────────────────────────────────────────────────────────
Institutional ownership assembled from SEC Form 13F-HR information tables.

Every commercial ownership feed available on the project's current API tiers is
paywalled (Finnhub fund-ownership returns 403, FMP's ownership endpoints 404),
and the previous implementation depended on yfinance, which is unavailable here.
13F-HR filings are the underlying public source those vendors resell.

SEC publishes no reverse index from security to holder, so a complete ownership
picture would mean parsing all ~10,000 13F filings that mention a given CUSIP.
Instead the largest institutional managers are polled directly. They are the
dominant holders of essentially every listed US equity, which makes the result a
well-identified floor on institutional ownership rather than a complete census —
``coverage`` in the response records exactly that.

Positions are matched by CUSIP once discovered, and only by issuer name until
then, so a manager holding several share classes is aggregated correctly.
"""
import re
import logging
from html import unescape
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.connectors.entity_naming import matches_entity
from app.connectors.sec_edgar_connector import (
    SEC_WWW_BASE,
    get_company_submissions,
)
from app.connectors.sec_http import sec_get

log = logging.getLogger(__name__)

# The largest 13F filers, each verified to file 13F-HR under this CIK. Ordered
# by typical assets under management so the most significant holders resolve
# first when a caller limits the number of managers polled.
MAJOR_INSTITUTIONS: List[Dict[str, str]] = [
    {"name": "Vanguard Group Inc", "cik": "0000102909"},
    # CIK 1364742 ("BlackRock Finance, Inc.") stopped filing in Aug 2024; the
    # group now files under 2012383. Reading the retired CIK returned a
    # two-year-old position alongside current ones from other managers.
    {"name": "BlackRock Inc", "cik": "0002012383"},
    {"name": "State Street Corp", "cik": "0000093751"},
    {"name": "FMR LLC (Fidelity)", "cik": "0000315066"},
    {"name": "Geode Capital Management", "cik": "0001214717"},
    {"name": "T. Rowe Price Associates", "cik": "0000080255"},
    {"name": "Morgan Stanley", "cik": "0000895421"},
    {"name": "Goldman Sachs Group", "cik": "0000886982"},
    {"name": "Wellington Management Group", "cik": "0000902219"},
    {"name": "Norges Bank", "cik": "0001374170"},
    {"name": "Northern Trust Corp", "cik": "0000073124"},
    {"name": "Invesco Ltd", "cik": "0000914208"},
    {"name": "UBS Group AG", "cik": "0001610520"},
    {"name": "Bank of New York Mellon", "cik": "0001390777"},
]

_INFO_TABLE_CACHE: Dict[str, Optional[str]] = {}

# One <infoTable> holding. Parsed with a regex rather than an XML tree because
# these documents reach tens of megabytes and hold tens of thousands of rows.
_HOLDING_RE = re.compile(
    r"<nameOfIssuer>(?P<issuer>[^<]+)</nameOfIssuer>.*?"
    r"<cusip>(?P<cusip>[^<]+)</cusip>.*?"
    r"<value>(?P<value>\d+)</value>.*?"
    r"<sshPrnamt>(?P<shares>\d+)</sshPrnamt>",
    re.DOTALL | re.IGNORECASE,
)


def _latest_13f_table(cik: str) -> Optional[Dict[str, str]]:
    """Locate and fetch a manager's most recent 13F-HR information table."""
    if cik in _INFO_TABLE_CACHE:
        return _INFO_TABLE_CACHE[cik]

    result = None
    try:
        subs = get_company_submissions(cik, forms=["13F-HR"], limit=1)
        filings = subs.get("filings") or []
        if filings:
            filing = filings[0]
            accession = filing["accession"].replace("-", "")
            base = f"{SEC_WWW_BASE}/Archives/edgar/data/{cik.lstrip('0')}/{accession}/"

            index = sec_get(base, timeout=30)
            if index is not None:
                names = re.findall(r'href="[^"]*/([^/"]+\.xml)"', index.text)
                # The information table is the XML that is not the cover page.
                table = next((n for n in names
                              if "primary_doc" not in n.lower()), None)
                if table:
                    resp = sec_get(base + table, timeout=120)
                    if resp is not None and resp.ok:
                        result = {
                            "xml": resp.text,
                            "url": base + table,
                            "period": filing.get("filing_date", ""),
                        }
    except Exception as e:
        log.warning("13F fetch failed for CIK %s: %s", cik, e)

    _INFO_TABLE_CACHE[cik] = result
    return result


def _positions_in(xml: str, entity_name: str, cusip: Optional[str]) -> Dict[str, Any]:
    """
    A manager's aggregate position in one issuer.

    A 13F lists a holding once per internal sub-manager, so Vanguard reports
    NVIDIA across seven rows. Summing them gives the firm-level position.
    """
    shares = 0
    value_thousands = 0
    found_cusip = cusip
    rows = 0

    for match in _HOLDING_RE.finditer(xml):
        row_cusip = match.group("cusip").strip().upper()
        if cusip:
            if row_cusip != cusip:
                continue
        # Issuer names arrive XML-escaped: "JPMORGAN CHASE &amp; CO.". Matched
        # raw, no issuer with an ampersand in its name is ever found.
        elif not matches_entity(unescape(match.group("issuer")), entity_name):
            continue

        rows += 1
        shares += int(match.group("shares"))
        value_thousands += int(match.group("value"))
        found_cusip = found_cusip or row_cusip

    return {"shares": shares, "value": value_thousands,
            "rows": rows, "cusip": found_cusip}


def _normalise_value(value: int, shares: int, price: Optional[float]) -> int:
    """
    Position value in whole dollars.

    Managers disagree on units. The SEC dropped the "report in thousands"
    convention for periods from 2023, but adoption is uneven, so a single table
    can mix Vanguard reporting dollars with T. Rowe Price reporting thousands —
    a thousand-fold error between adjacent rows. Comparing the filed value to
    shares times the market price identifies the scale actually used.
    """
    if not (value and shares and price):
        return value
    expected = shares * price
    # Only rescale on an unambiguous order-of-magnitude mismatch.
    if expected / 100 > value > 0:
        return value * 1000
    return value


def get_institutional_holders(entity_name: str, ticker: str = "",
                              shares_outstanding: Optional[float] = None,
                              price: Optional[float] = None,
                              max_institutions: int = 14) -> Dict[str, Any]:
    """
    Institutional holders of an issuer, from 13F-HR filings.

    Args:
        entity_name: Registrant name as it appears in 13F issuer fields.
        shares_outstanding: Used to express each position as a percentage of
            shares outstanding. Percentages are omitted when unavailable rather
            than estimated.
        price: Reference share price, used to resolve the units a manager
            reported position values in.
    """
    result: Dict[str, Any] = {
        "entity_name": entity_name,
        "ticker": ticker,
        "cusip": None,
        "holders": [],
        "stale_filers": [],
        "institutions_polled": 0,
        "institutions_holding": 0,
        "total_shares_held": 0,
        "total_value_held": 0,
        "pct_shares_outstanding": None,
        "coverage": ("Aggregated from the largest 13F filers only; a floor on "
                     "institutional ownership, not a complete census."),
        "source": "SEC Form 13F-HR information tables",
    }

    # 13F is quarterly; anything older than a year means the manager has moved
    # to a different CIK or ceased filing.
    stale_before = (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d")

    cusip = None
    for institution in MAJOR_INSTITUTIONS[:max_institutions]:
        table = _latest_13f_table(institution["cik"])
        result["institutions_polled"] += 1
        if not table:
            continue

        # A manager that has stopped filing under this CIK would otherwise
        # contribute a years-old position to a table of current ones.
        if table["period"] < stale_before:
            result["stale_filers"].append({
                "institution": institution["name"],
                "last_filed": table["period"],
            })
            continue

        position = _positions_in(table["xml"], entity_name, cusip)
        if not position["shares"]:
            continue

        cusip = cusip or position["cusip"]
        holding = {
            "institution": institution["name"],
            "cik": institution["cik"],
            "shares": position["shares"],
            "value": _normalise_value(position["value"], position["shares"], price),
            "value_as_filed": position["value"],
            "positions_reported": position["rows"],
            "report_date": table["period"],
            "source_url": table["url"],
        }
        if shares_outstanding:
            holding["pct_outstanding"] = round(
                position["shares"] / shares_outstanding * 100, 2)
        result["holders"].append(holding)

    result["cusip"] = cusip
    result["holders"].sort(key=lambda h: h["shares"], reverse=True)
    result["institutions_holding"] = len(result["holders"])
    result["total_shares_held"] = sum(h["shares"] for h in result["holders"])
    result["total_value_held"] = sum(h["value"] for h in result["holders"])

    if shares_outstanding and result["total_shares_held"]:
        result["pct_shares_outstanding"] = round(
            result["total_shares_held"] / shares_outstanding * 100, 2)

    return result
