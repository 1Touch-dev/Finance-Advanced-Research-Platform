"""
SEC-API.io Connector — Premium SEC Data Intelligence
────────────────────────────────────────────────────────────────────────────
Uses sec-api.io (paid API) for structured extraction of:
  - Form D (Private Placements) — investors, amounts, exemptions
  - Form N-PORT (Fund Holdings) — implied pricing from mutual fund marks
  - Directors & Board Members — structured board composition
  - Executive Compensation — pay packages
  - Company Subsidiaries — corporate structure
  - Form 3/4/5 (Insider Trading) — structured insider data
  - Form 13F (Portfolio Holdings) — institutional positions
  - Form 13D/13G (Beneficial Ownership) — activist positions
  - Outstanding Shares & Public Float
  - Audit Fees & Audit Reports

API Key: SEC_API_KEY env var (from sec-api.io dashboard)
"""
import os
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

SEC_API_KEY = os.getenv("SEC_API_KEY", "")
SEC_API_BASE = "https://api.sec-api.io"
EDGAR_MIRROR = "https://edgar-mirror.sec-api.io"

_HEADERS = {
    "Authorization": SEC_API_KEY,
    "Content-Type": "application/json",
    "User-Agent": "FinanceIntelPlatform/2.0",
}

_call_count = 0
_MAX_CALLS = 95  # stay under 100 trial limit


def _check_budget() -> bool:
    global _call_count
    if _call_count >= _MAX_CALLS:
        logger.warning("SEC-API call budget exhausted (%d/%d)", _call_count, _MAX_CALLS)
        return False
    return True


def _post(endpoint: str, payload: dict) -> Optional[dict]:
    """POST to sec-api.io with budget tracking."""
    global _call_count
    if not SEC_API_KEY:
        logger.info("SEC_API_KEY not set — skipping sec-api.io call")
        return None
    if not _check_budget():
        return None
    try:
        _call_count += 1
        url = f"{SEC_API_BASE}{endpoint}" if not endpoint.startswith("http") else endpoint
        if "?" in url:
            url += f"&token={SEC_API_KEY}"
        else:
            url += f"?token={SEC_API_KEY}"
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 403:
            logger.warning("SEC-API %s: 403 (subscription required)", endpoint)
            return None
        logger.warning("SEC-API %s returned %d: %s", endpoint, resp.status_code, resp.text[:200])
        return None
    except Exception as e:
        logger.warning("SEC-API %s error: %s", endpoint, e)
        return None


def _get(url: str) -> Optional[dict]:
    """GET from sec-api.io endpoints (used for simple lookups)."""
    global _call_count
    if not SEC_API_KEY:
        return None
    if not _check_budget():
        return None
    try:
        _call_count += 1
        sep = "&" if "?" in url else "?"
        resp = requests.get(f"{url}{sep}token={SEC_API_KEY}", timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 403:
            logger.debug("SEC-API GET %s: subscription required", url)
            return None
        logger.warning("SEC-API GET %s returned %d", url, resp.status_code)
        return None
    except Exception as e:
        logger.warning("SEC-API GET error: %s", e)
        return None


# ── Filing Query API ─────────────────────────────────────────────────────────

def query_filings(ticker: str, form_type: str, size: int = 10) -> List[dict]:
    """Query SEC filings by ticker and form type."""
    payload = {
        "query": f'ticker:{ticker} AND formType:"{form_type}"',
        "from": "0",
        "size": str(size),
        "sort": [{"filedAt": {"order": "desc"}}],
    }
    result = _post("", payload)
    if result and "filings" in result:
        return result["filings"]
    return []


def query_filings_by_name(company_name: str, form_type: str, size: int = 10) -> List[dict]:
    """Query filings by company name."""
    safe_name = company_name.replace('"', '\\"')
    payload = {
        "query": f'companyName:"{safe_name}" AND formType:"{form_type}"',
        "from": "0",
        "size": str(size),
        "sort": [{"filedAt": {"order": "desc"}}],
    }
    result = _post("", payload)
    if result and "filings" in result:
        return result["filings"]
    return []


# ── Form D (Private Placements) ──────────────────────────────────────────────

def get_form_d_filings(ticker: str = "", company_name: str = "",
                       limit: int = 20) -> Dict[str, Any]:
    """Get Form D private placement filings — investors, amounts, exemptions."""
    output = {
        "filings": [],
        "total_raised": 0.0,
        "investors_identified": [],
        "exemptions_used": [],
        "source": "sec-api.io/Form-D",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    # Query for Form D filings
    if ticker:
        filings = query_filings(ticker, "D", size=limit)
    elif company_name:
        filings = query_filings_by_name(company_name, "D", size=limit)
    else:
        return output

    for filing in filings:
        entry = {
            "filed_at": filing.get("filedAt"),
            "company": filing.get("companyName"),
            "cik": filing.get("cik"),
            "accession": filing.get("accessionNo"),
            "form_type": filing.get("formType"),
        }

        # Try to get structured Form D data
        detail = _get_form_d_detail(filing.get("accessionNo"))
        if detail:
            entry.update(detail)
            if detail.get("total_amount_sold"):
                output["total_raised"] += detail["total_amount_sold"]
            for inv in detail.get("investors", []):
                if inv not in output["investors_identified"]:
                    output["investors_identified"].append(inv)
            if detail.get("exemption") and detail["exemption"] not in output["exemptions_used"]:
                output["exemptions_used"].append(detail["exemption"])

        output["filings"].append(entry)

    return output


def _get_form_d_detail(accession_no: str) -> Optional[dict]:
    """Extract structured data from a Form D filing."""
    if not accession_no:
        return None
    url = f"{SEC_API_BASE}/form-d?accessionNo={accession_no}&token={SEC_API_KEY}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return None
        data = resp.json()
        result = {
            "issuer_name": data.get("issuerName"),
            "exemption": data.get("federalExemptionsExclusions"),
            "total_amount_sold": _safe_float(data.get("totalAmountSold")),
            "total_offering_amount": _safe_float(data.get("totalOfferingAmount")),
            "total_remaining": _safe_float(data.get("totalRemaining")),
            "investors": [],
            "sales_commissions": _safe_float(data.get("salesCommissions")),
            "is_amendment": data.get("isAmendment", False),
            "industry_group": data.get("industryGroupType"),
            "revenue_range": data.get("revenueRange"),
        }
        # Extract related persons (investors/promoters)
        for person in data.get("relatedPersons", []):
            result["investors"].append({
                "name": f"{person.get('firstName', '')} {person.get('lastName', '')}".strip(),
                "relationship": person.get("relationship"),
                "city": person.get("city"),
                "state": person.get("stateOrCountry"),
            })
        return result
    except Exception as e:
        logger.debug("Form D detail error: %s", e)
        return None


# ── Form N-PORT (Fund Holdings) ──────────────────────────────────────────────

def get_nport_holdings(ticker: str = "", company_name: str = "",
                       limit: int = 10) -> Dict[str, Any]:
    """Get N-PORT fund holdings — what funds hold this company at what value."""
    output = {
        "holdings": [],
        "funds_holding": 0,
        "total_value_held": 0.0,
        "implied_prices": [],
        "source": "sec-api.io/N-PORT",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    # N-PORT queries use holdings.issuerName or holdings.cusip
    search_term = company_name or ticker
    data = _post("/form-nport", {
        "query": f'holdings.issuerName:"{search_term}"',
        "from": "0",
        "size": str(min(limit, 5)),
        "sort": [{"periodOfReport": {"order": "desc"}}],
    })
    if not data or not data.get("data"):
        # Try ticker-based search
        if ticker and ticker != search_term:
            data = _post("/form-nport", {
                "query": f'holdings.ticker:"{ticker}"',
                "from": "0",
                "size": str(min(limit, 5)),
            })
    if not data or not data.get("data"):
        return output

    for fund_filing in data.get("data", []):
        fund_name = fund_filing.get("seriesName") or fund_filing.get("fundName", "")
        report_date = fund_filing.get("periodOfReport", "")
        # Each filing has a holdings array — filter to our target
        for h in fund_filing.get("holdings", []):
            issuer = h.get("issuerName", "")
            # Only include holdings matching our target
            if (search_term.upper() in issuer.upper() or
                    ticker.upper() in (h.get("ticker") or "").upper()):
                entry = {
                    "fund_name": fund_name,
                    "issuer_name": issuer,
                    "title": h.get("title"),
                    "cusip": h.get("cusip"),
                    "value_usd": _safe_float(h.get("valUSD") or h.get("value")),
                    "shares": _safe_float(h.get("balance") or h.get("shares")),
                    "pct_of_fund": _safe_float(h.get("pctVal")),
                    "asset_type": h.get("assetCat"),
                    "report_date": report_date,
                }
                output["holdings"].append(entry)
                output["total_value_held"] += entry["value_usd"]
                if entry["shares"] and entry["value_usd"]:
                    implied = entry["value_usd"] / entry["shares"]
                    output["implied_prices"].append({
                        "fund": fund_name,
                        "implied_price_per_share": round(implied, 4),
                        "date": report_date,
                    })

    output["funds_holding"] = len(set(h["fund_name"] for h in output["holdings"]))
    return output


# ── Directors & Board Members ────────────────────────────────────────────────

def get_directors(ticker: str) -> Dict[str, Any]:
    """Get structured directors and board members data via SDK-style POST."""
    output = {
        "directors": [],
        "total_directors": 0,
        "independent_count": 0,
        "committees": {},
        "source": "sec-api.io/directors",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    data = _post("/directors-and-board-members", {
        "query": f'ticker:"{ticker}"',
        "from": "0",
        "size": "5",
        "sort": [{"filedAt": {"order": "desc"}}],
    })
    if not data or not data.get("data"):
        return output

    # Take the most recent filing's directors
    latest = data["data"][0] if data["data"] else {}
    directors_raw = latest.get("directors", [])

    for d in directors_raw:
        entry = {
            "name": d.get("name", ""),
            "age": d.get("age"),
            "title": d.get("position") or d.get("title") or "Director",
            "since": d.get("dateFirstElected"),
            "is_independent": d.get("isIndependent", False),
            "director_class": d.get("directorClass"),
            "committees": d.get("committeeMemberships", []),
            "qualifications": d.get("qualificationsAndExperience", []),
            "other_boards": d.get("otherDirectorships", []),
        }
        output["directors"].append(entry)
        if entry["is_independent"]:
            output["independent_count"] += 1
        for comm in entry["committees"]:
            output["committees"].setdefault(comm, []).append(entry["name"])

    output["total_directors"] = len(output["directors"])
    output["filing_date"] = latest.get("filedAt", "")[:10]
    return output


# ── Executive Compensation ───────────────────────────────────────────────────

def get_executive_compensation(ticker: str) -> Dict[str, Any]:
    """Get structured executive compensation data (requires Pro subscription)."""
    output = {
        "executives": [],
        "total_ceo_comp": 0.0,
        "median_employee_pay": 0.0,
        "ceo_pay_ratio": None,
        "source": "sec-api.io/exec-comp",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    data = _post("/executive-compensation", {
        "query": f'ticker:"{ticker}"',
        "from": "0",
        "size": "3",
        "sort": [{"filedAt": {"order": "desc"}}],
    })
    if not data or not data.get("data"):
        # 403 = subscription required, not a real error
        output["note"] = "Executive compensation requires Pro subscription"
        return output

    latest = data["data"][0] if data["data"] else {}
    execs = latest.get("executives", [])
    for ex in execs:
        entry = {
            "name": ex.get("name", ""),
            "title": ex.get("title") or ex.get("position", ""),
            "salary": _safe_float(ex.get("salary")),
            "bonus": _safe_float(ex.get("bonus")),
            "stock_awards": _safe_float(ex.get("stockAwards")),
            "option_awards": _safe_float(ex.get("optionAwards")),
            "non_equity_incentive": _safe_float(ex.get("nonEquityIncentive")),
            "pension_change": _safe_float(ex.get("pensionChange")),
            "other_comp": _safe_float(ex.get("otherCompensation") or ex.get("allOther")),
            "total": _safe_float(ex.get("total") or ex.get("totalCompensation")),
            "year": ex.get("year") or ex.get("fiscalYear"),
        }
        output["executives"].append(entry)
        if entry["title"] and "ceo" in entry["title"].lower():
            output["total_ceo_comp"] = entry["total"]

    output["median_employee_pay"] = _safe_float(latest.get("medianEmployeePay"))
    output["ceo_pay_ratio"] = latest.get("ceoPayRatio")
    return output


# ── Company Subsidiaries ─────────────────────────────────────────────────────

def get_subsidiaries(ticker: str) -> Dict[str, Any]:
    """Get company subsidiaries list via SDK-style POST."""
    output = {
        "subsidiaries": [],
        "total_count": 0,
        "jurisdictions": {},
        "source": "sec-api.io/subsidiaries",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    data = _post("/subsidiaries", {
        "query": f'ticker:"{ticker}"',
        "from": "0",
        "size": "3",
        "sort": [{"filedAt": {"order": "desc"}}],
    })
    if not data or not data.get("data"):
        return output

    # Take the most recent filing's subsidiaries
    latest = data["data"][0] if data["data"] else {}
    subs_raw = latest.get("subsidiaries", [])

    for s in subs_raw:
        entry = {
            "name": s.get("name") or s.get("subsidiaryName", ""),
            "jurisdiction": s.get("jurisdiction") or s.get("stateOfIncorporation", ""),
            "ownership_pct": s.get("ownershipPercentage") or s.get("pctOwned"),
        }
        output["subsidiaries"].append(entry)
        j = entry["jurisdiction"] or "Unknown"
        output["jurisdictions"][j] = output["jurisdictions"].get(j, 0) + 1

    output["total_count"] = len(output["subsidiaries"])
    output["filing_date"] = latest.get("filedAt", "")[:10]
    return output


# ── Insider Trading (Form 3/4/5) ─────────────────────────────────────────────

def get_insider_trading_structured(ticker: str, limit: int = 50) -> Dict[str, Any]:
    """Get structured insider trading from Form 3/4/5 via sec-api.io."""
    output = {
        "transactions": [],
        "total_buys": 0,
        "total_sells": 0,
        "net_shares": 0,
        "net_value": 0.0,
        "top_sellers": [],
        "top_buyers": [],
        "source": "sec-api.io/insider",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    data = _post("/insider-trading", {
        "query": f'issuer.tradingSymbol:"{ticker}"',
        "from": "0",
        "size": str(limit),
        "sort": [{"periodOfReport": {"order": "desc"}}],
    })
    if not data:
        return output

    transactions = data.get("transactions", [])
    by_person: Dict[str, float] = {}

    for tx in transactions:
        owner = tx.get("reportingOwner", {})
        owner_name = owner.get("name", "Unknown")
        relationship = owner.get("relationship", {})
        is_director = relationship.get("isDirector", False)
        is_officer = relationship.get("isOfficer", False)
        officer_title = relationship.get("officerTitle", "")

        # Parse transactions from nonDerivativeTable
        nd_table = tx.get("nonDerivativeTable", {})
        for trade in nd_table.get("transactions", []):
            coding = trade.get("coding", {})
            amounts = trade.get("transactionAmounts", {})
            post = trade.get("postTransactionAmounts", {})

            shares = _safe_float(amounts.get("sharesTraded") or
                                 amounts.get("transactionShares"))
            price = _safe_float(amounts.get("pricePerShare") or
                                amounts.get("transactionPricePerShare"))
            code = coding.get("transactionCode", "")
            value = shares * price if shares and price else 0

            entry = {
                "name": owner_name,
                "title": officer_title or ("Director" if is_director else "Officer" if is_officer else ""),
                "transaction_date": tx.get("periodOfReport"),
                "transaction_type": code,
                "shares": shares,
                "price": price,
                "value": value,
                "shares_owned_after": _safe_float(post.get("sharesOwnedFollowingTransaction")),
                "is_10b5_1": tx.get("aff10b5One", False),
                "form_type": tx.get("documentType"),
                "is_direct": (trade.get("ownershipNature", {})
                              .get("directOrIndirectOwnership") == "D"),
            }
            output["transactions"].append(entry)

            is_buy = code in ("P", "A", "J", "G")
            if is_buy:
                output["total_buys"] += 1
                output["net_shares"] += shares
                output["net_value"] += value
            elif code in ("S", "F", "D"):
                output["total_sells"] += 1
                output["net_shares"] -= shares
                output["net_value"] -= value

            by_person[owner_name] = by_person.get(owner_name, 0) + (
                value if is_buy else -value)

        # Also handle holdings (Form 3 initial statements)
        for holding in nd_table.get("holdings", []):
            post = holding.get("postTransactionAmounts", {})
            entry = {
                "name": owner_name,
                "title": officer_title or ("Director" if is_director else ""),
                "transaction_date": tx.get("periodOfReport"),
                "transaction_type": "H",  # Holding
                "shares": _safe_float(post.get("sharesOwnedFollowingTransaction")),
                "price": 0,
                "value": 0,
                "shares_owned_after": _safe_float(post.get("sharesOwnedFollowingTransaction")),
                "is_10b5_1": False,
                "form_type": tx.get("documentType"),
                "is_direct": (holding.get("ownershipNature", {})
                              .get("directOrIndirectOwnership") == "D"),
            }
            output["transactions"].append(entry)

    # Top buyers/sellers
    sorted_people = sorted(by_person.items(), key=lambda x: x[1])
    output["top_sellers"] = [{"name": n, "net_value": abs(v)}
                             for n, v in sorted_people[:5] if v < 0]
    output["top_buyers"] = [{"name": n, "net_value": v}
                            for n, v in reversed(sorted_people) if v > 0][:5]

    return output


# ── 13F Portfolio Holdings ───────────────────────────────────────────────────

def get_13f_holders(ticker: str, limit: int = 20) -> Dict[str, Any]:
    """Get 13F institutional holders for a company."""
    output = {
        "holders": [],
        "total_institutional_value": 0.0,
        "total_holders": 0,
        "source": "sec-api.io/13F",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    url = (f"{SEC_API_BASE}/form-13f"
           f"?ticker={ticker}&token={SEC_API_KEY}&limit={limit}")
    data = _get(url)
    if not data:
        return output

    holders = data if isinstance(data, list) else data.get("holders", [])
    for h in holders:
        entry = {
            "manager_name": h.get("managerName") or h.get("filingManager"),
            "shares": _safe_float(h.get("sharesHeld") or h.get("shares")),
            "value": _safe_float(h.get("value") or h.get("marketValue")),
            "report_date": h.get("reportDate") or h.get("periodOfReport"),
            "investment_discretion": h.get("investmentDiscretion"),
            "voting_authority": h.get("votingAuthority"),
        }
        output["holders"].append(entry)
        output["total_institutional_value"] += entry["value"]

    output["total_holders"] = len(output["holders"])
    return output


# ── 13D/13G Beneficial Ownership ─────────────────────────────────────────────

def get_beneficial_ownership(ticker: str, limit: int = 10) -> Dict[str, Any]:
    """Get 13D/13G beneficial ownership filings (activist positions)."""
    output = {
        "filings": [],
        "activists_identified": [],
        "source": "sec-api.io/13D-13G",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    filings_13d = query_filings(ticker, "SC 13D", size=limit)
    filings_13g = query_filings(ticker, "SC 13G", size=limit)

    for f in filings_13d + filings_13g:
        entry = {
            "filer": f.get("companyName"),
            "form_type": f.get("formType"),
            "filed_at": f.get("filedAt"),
            "accession": f.get("accessionNo"),
            "is_activist": "13D" in (f.get("formType") or ""),
        }
        output["filings"].append(entry)
        if entry["is_activist"] and entry["filer"]:
            output["activists_identified"].append(entry["filer"])

    return output


# ── Outstanding Shares & Public Float ────────────────────────────────────────

def get_shares_outstanding(ticker: str) -> Dict[str, Any]:
    """Get outstanding shares and public float data."""
    output = {
        "shares_outstanding": None,
        "public_float": None,
        "float_pct": None,
        "source": "sec-api.io/shares",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    data = _post("/float", {
        "query": f'ticker:"{ticker}"',
        "from": "0",
        "size": "1",
        "sort": [{"filedAt": {"order": "desc"}}],
    })
    if data and data.get("data"):
        latest = data["data"][0]
        output["shares_outstanding"] = latest.get("sharesOutstanding")
        output["public_float"] = latest.get("publicFloat")
        if output["shares_outstanding"] and output["public_float"]:
            try:
                output["float_pct"] = round(
                    float(output["public_float"]) /
                    float(output["shares_outstanding"]) * 100, 2)
            except (ValueError, ZeroDivisionError):
                pass

    return output


# ── Enforcement Actions ──────────────────────────────────────────────────────

def get_enforcement_actions(company_name: str, limit: int = 10) -> Dict[str, Any]:
    """Get SEC enforcement actions related to entity."""
    output = {
        "actions": [],
        "total_found": 0,
        "source": "sec-api.io/enforcement",
    }
    if not SEC_API_KEY:
        output["error"] = "SEC_API_KEY not configured"
        return output

    data = _post("/sec-enforcement-actions", {
        "query": f'companyName:"{company_name}"',
        "from": "0",
        "size": str(limit),
        "sort": [{"releasedAt": {"order": "desc"}}],
    })
    if not data or not data.get("data"):
        return output

    for a in data.get("data", []):
        output["actions"].append({
            "date": (a.get("releasedAt") or a.get("date", ""))[:10],
            "title": a.get("headline") or a.get("title", ""),
            "type": a.get("category") or a.get("type", ""),
            "url": a.get("url") or a.get("link", ""),
            "description": (a.get("description") or "")[:500],
        })

    output["total_found"] = len(output["actions"])
    return output


# ── Comprehensive Fetch ──────────────────────────────────────────────────────

def fetch_all_sec_api_data(ticker: str, company_name: str = "") -> Dict[str, Any]:
    """Fetch all available SEC-API data for a company.

    This is the main entry point wired into the report generator.
    Returns a unified payload with all structured SEC data.
    """
    if not SEC_API_KEY:
        return {"error": "SEC_API_KEY not configured", "available": False}

    logger.info("SEC-API: fetching comprehensive data for %s (%s)", ticker, company_name)
    start = time.time()

    result = {
        "available": True,
        "ticker": ticker,
        "company_name": company_name,
        "fetch_timestamp": datetime.utcnow().isoformat(),
    }

    # Form D — Private Placements
    try:
        result["form_d"] = get_form_d_filings(ticker=ticker, company_name=company_name)
        logger.info("  Form D: %d filings", len(result["form_d"].get("filings", [])))
    except Exception as e:
        result["form_d"] = {"error": str(e)}
        logger.warning("  Form D failed: %s", e)

    # N-PORT — Fund Holdings
    try:
        result["nport"] = get_nport_holdings(ticker=ticker)
        logger.info("  N-PORT: %d holdings", len(result["nport"].get("holdings", [])))
    except Exception as e:
        result["nport"] = {"error": str(e)}
        logger.warning("  N-PORT failed: %s", e)

    # Directors
    try:
        result["directors"] = get_directors(ticker)
        logger.info("  Directors: %d found", result["directors"].get("total_directors", 0))
    except Exception as e:
        result["directors"] = {"error": str(e)}

    # Executive Compensation (Pro-only, may return empty)
    try:
        result["executive_compensation"] = get_executive_compensation(ticker)
        execs_found = len(result["executive_compensation"].get("executives", []))
        if execs_found:
            logger.info("  Exec comp: %d executives", execs_found)
        else:
            logger.info("  Exec comp: not available (Pro subscription required)")
    except Exception as e:
        result["executive_compensation"] = {"error": str(e)}

    # Subsidiaries
    try:
        result["subsidiaries"] = get_subsidiaries(ticker)
        logger.info("  Subsidiaries: %d found", result["subsidiaries"].get("total_count", 0))
    except Exception as e:
        result["subsidiaries"] = {"error": str(e)}

    # Insider Trading (structured)
    try:
        result["insider_trading_structured"] = get_insider_trading_structured(ticker)
        logger.info("  Insider trades: %d transactions",
                    len(result["insider_trading_structured"].get("transactions", [])))
    except Exception as e:
        result["insider_trading_structured"] = {"error": str(e)}

    # 13D/13G Beneficial Ownership
    try:
        result["beneficial_ownership"] = get_beneficial_ownership(ticker)
        logger.info("  13D/13G: %d filings",
                    len(result["beneficial_ownership"].get("filings", [])))
    except Exception as e:
        result["beneficial_ownership"] = {"error": str(e)}

    # Outstanding Shares (endpoint may not exist on trial)
    try:
        result["shares_data"] = get_shares_outstanding(ticker)
    except Exception as e:
        result["shares_data"] = {"error": str(e)}

    # Enforcement Actions
    if company_name:
        try:
            result["enforcement"] = get_enforcement_actions(company_name)
            logger.info("  Enforcement: %d actions",
                        result["enforcement"].get("total_found", 0))
        except Exception as e:
            result["enforcement"] = {"error": str(e)}

    elapsed = time.time() - start
    result["fetch_duration_seconds"] = round(elapsed, 1)
    result["api_calls_used"] = _call_count
    logger.info("SEC-API: completed in %.1fs using %d API calls", elapsed, _call_count)

    return result


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return 0.0


def get_api_usage() -> Dict[str, Any]:
    """Return current API call usage stats."""
    return {
        "calls_used": _call_count,
        "calls_remaining": max(0, _MAX_CALLS - _call_count),
        "budget_limit": _MAX_CALLS,
        "key_configured": bool(SEC_API_KEY),
    }
