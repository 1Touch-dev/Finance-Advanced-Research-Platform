"""
SEC EDGAR Connector — Financial Statement Intelligence
────────────────────────────────────────────────────────────────────────────
Retrieves financial data from SEC EDGAR for deep intelligence reports:
  - XBRL companyfacts API for financial statements
  - 10-K/10-Q filing parsing
  - Segment, geographic, customer concentration
  - Balance sheet analysis
  - Investment portfolio tracking

Primary sources:
  - SEC EDGAR XBRL: https://data.sec.gov/api/xbrl/companyfacts/
  - SEC Submissions: https://data.sec.gov/submissions/
  - SEC Full-Text Search: https://efts.sec.gov/LATEST/

No API key required - public SEC data.
"""
import html
import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from xml.etree import ElementTree as ET
import math

from app.connectors.sec_http import sec_get_json, sec_get_text

logger = logging.getLogger(__name__)

SEC_BASE = "https://data.sec.gov"
# The XBRL/submissions APIs live on data.sec.gov, but the ticker→CIK map is only
# served from www.sec.gov; requesting it from data.sec.gov returns 404.
SEC_WWW_BASE = "https://www.sec.gov"
# `or` rather than a getenv default: the variable is present but may be empty,
# and SEC rejects requests with a blank User-Agent with HTTP 403.
SEC_HEADERS = {
    "User-Agent": os.getenv("SEC_USER_AGENT") or "FinanceIntelPlatform/1.0 research@example.com",
    "Accept": "application/json",
}

# Rate limiting for SEC (10 requests per second max)
_last_request_time = 0
def _rate_limit():
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 0.1:
        time.sleep(0.1 - elapsed)
    _last_request_time = time.time()


def _safe_float(v) -> float:
    """Safely convert to float."""
    try:
        if v is None:
            return 0.0
        f = float(v)
        return 0.0 if math.isnan(f) or math.isinf(f) else f
    except:
        return 0.0


def _safe_int(v) -> int:
    """Safely convert to int."""
    try:
        if v is None:
            return 0
        return int(float(v))
    except:
        return 0


_TICKER_CIK_CACHE: Dict[str, str] = {}


def _duration_days(fact: Dict[str, Any]) -> Optional[int]:
    """Length in days of an XBRL fact's reporting period, if it has one."""
    start, end = fact.get("start"), fact.get("end")
    if not start or not end:
        return None  # instant fact (balance-sheet item), not a duration
    try:
        d0 = datetime.strptime(start, "%Y-%m-%d")
        d1 = datetime.strptime(end, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
    return (d1 - d0).days


def _is_annual_duration(fact: Dict[str, Any]) -> bool:
    """
    True for full-year durations and for instant (balance-sheet) facts.

    A 10-K contains both annual durations and quarterly comparatives; without
    this check a Q4 income figure can be mistaken for the full year.
    """
    days = _duration_days(fact)
    return days is None or 330 <= days <= 400


def _is_quarterly_duration(fact: Dict[str, Any]) -> bool:
    """True for roughly-one-quarter durations, or instant facts."""
    days = _duration_days(fact)
    return days is None or 80 <= days <= 100


_FILER_CIK_CACHE: Dict[str, Optional[str]] = {}


def _cik_has_financials(cik: str) -> bool:
    """Whether a CIK actually reports XBRL financial facts."""
    facts = get_company_facts(cik)
    return bool((facts.get("facts") or {}).get("us-gaap"))


def _find_filer_cik_via_fulltext(ticker: str) -> Optional[str]:
    """
    Locate the CIK that files financial statements for a ticker.

    After a holding-company reorganisation the ticker map points at the new
    parent, which has no XBRL history: SEC maps XOM to "ExxonMobil Holdings
    Corp" (zero concepts) while the statements remain under "EXXON MOBIL CORP".
    EDGAR full-text search returns the CIK that actually filed the 10-Ks.
    """
    try:
        resp = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params={"q": f'"{ticker}"', "forms": "10-K"},
            headers=SEC_HEADERS,
            timeout=25,
        )
        if not resp.ok:
            return None
        seen = []
        for hit in resp.json().get("hits", {}).get("hits", []):
            source = hit.get("_source") or {}
            # display_names look like "EXXON MOBIL CORP  (XOM)  (CIK 0000034088)"
            names = " ".join(source.get("display_names") or []).upper()
            if f"({ticker.upper()})" not in names:
                continue
            for cik in source.get("ciks") or []:
                padded = str(cik).zfill(10)
                if padded not in seen:
                    seen.append(padded)
        for padded in seen[:3]:
            if _cik_has_financials(padded):
                return padded
    except Exception as e:
        logger.warning("Full-text CIK fallback failed for %s: %s", ticker, e)
    return None


# Registrants are added to the map continuously but existing tickers do not
# move, so a stale map costs at most a newly listed issuer.
_TICKER_MAP_PATH = Path(tempfile.gettempdir()) / "sec_company_tickers.json"
_TICKER_MAP_TTL = timedelta(days=7)


def _load_ticker_map_cache() -> bool:
    """Populate the in-process map from disk. True when usable data was read."""
    try:
        if not _TICKER_MAP_PATH.exists():
            return False
        age = datetime.now() - datetime.fromtimestamp(_TICKER_MAP_PATH.stat().st_mtime)
        if age > _TICKER_MAP_TTL:
            return False
        _TICKER_CIK_CACHE.update(json.loads(_TICKER_MAP_PATH.read_text()))
        return True
    except Exception as e:
        logger.debug("Ticker map cache unreadable: %s", e)
        return False


def _store_ticker_map_cache() -> None:
    try:
        _TICKER_MAP_PATH.write_text(json.dumps(_TICKER_CIK_CACHE))
    except Exception as e:
        logger.debug("Could not write ticker map cache: %s", e)


def get_filer_cik(ticker: str) -> Optional[str]:
    """
    CIK of the entity that files this ticker's financial statements.

    Prefer this over get_cik_from_ticker wherever financial facts are needed: it
    verifies the mapped CIK reports XBRL data and falls back to full-text search
    when the ticker resolves to a non-reporting holding company.
    """
    key = ticker.upper().strip()
    if key in _FILER_CIK_CACHE:
        return _FILER_CIK_CACHE[key]

    cik = get_cik_from_ticker(key)
    if cik and not _cik_has_financials(cik):
        logger.info("CIK %s for %s reports no XBRL facts; searching for the filer",
                    cik, key)
        cik = _find_filer_cik_via_fulltext(key) or cik

    _FILER_CIK_CACHE[key] = cik
    return cik


def get_cik_from_ticker(ticker: str) -> Optional[str]:
    """
    Resolve stock ticker to SEC CIK (Central Index Key).
    Returns padded 10-digit CIK string.

    The whole map is cached on first call; every SEC-backed connector depends on
    this resolution, so a miss here silently empties the entire report.

    The map is also cached on disk. It is the first SEC request any run makes
    and the same file every time, so refetching it per process is what
    eventually draws a 429 — and that failure takes every downstream section
    with it.
    """
    ticker_upper = ticker.upper().strip()
    if ticker_upper in _TICKER_CIK_CACHE:
        return _TICKER_CIK_CACHE[ticker_upper]

    if _load_ticker_map_cache() and ticker_upper in _TICKER_CIK_CACHE:
        return _TICKER_CIK_CACHE[ticker_upper]

    for attempt in range(3):
        _rate_limit()
        try:
            resp = requests.get(
                f"{SEC_WWW_BASE}/files/company_tickers.json",
                headers=SEC_HEADERS,
                timeout=20,
            )
            if resp.ok:
                for entry in resp.json().values():
                    sym = str(entry.get("ticker", "")).upper()
                    if sym:
                        _TICKER_CIK_CACHE[sym] = str(entry.get("cik_str", "")).zfill(10)
                _store_ticker_map_cache()
                if ticker_upper in _TICKER_CIK_CACHE:
                    return _TICKER_CIK_CACHE[ticker_upper]
                logger.warning("Ticker %s not present in SEC ticker map", ticker)
                return None
            logger.warning("SEC ticker map HTTP %s (attempt %d)", resp.status_code, attempt + 1)
        except Exception as e:
            logger.warning("Error resolving ticker %s to CIK (attempt %d): %s",
                           ticker, attempt + 1, e)
        time.sleep(1.5 * (attempt + 1))

    return None


def get_company_facts(cik: str) -> Dict[str, Any]:
    """
    Retrieve XBRL company facts from SEC EDGAR.

    This is the primary source for all financial statement data.
    Returns the full companyfacts JSON including all reported facts.
    """
    _rate_limit()
    result = {
        "cik": cik,
        "entity_name": "",
        "facts": {},
        "fiscal_year_end": "",
        "sic": "",
        "error": None,
    }

    try:
        url = f"{SEC_BASE}/api/xbrl/companyfacts/CIK{cik}.json"
        resp = requests.get(url, headers=SEC_HEADERS, timeout=30)

        if resp.ok:
            data = resp.json()
            result["entity_name"] = data.get("entityName", "")
            result["facts"] = data.get("facts", {})

            # Try to extract fiscal year end from facts
            us_gaap = data.get("facts", {}).get("us-gaap", {})
            if us_gaap:
                # Look for any fact to get the fiscal year end pattern
                for concept_name, concept_data in us_gaap.items():
                    units = concept_data.get("units", {})
                    for unit_type, values in units.items():
                        if values and len(values) > 0:
                            last_val = values[-1]
                            if "end" in last_val:
                                result["fiscal_year_end"] = last_val.get("end", "")[:10]
                                break
                    if result["fiscal_year_end"]:
                        break
        else:
            result["error"] = f"HTTP {resp.status_code}"

    except Exception as e:
        logger.warning("Error fetching company facts for CIK %s: %s", cik, e)
        result["error"] = str(e)

    return result


def get_company_submissions(cik: str, forms: Optional[List[str]] = None,
                            limit: int = 100) -> Dict[str, Any]:
    """
    Company submission history from SEC EDGAR.

    Args:
        forms: Restrict to these form types. Filtering happens across the whole
            submission index rather than after truncation — without it a
            high-volume filer returns nothing useful. JPMorgan files around a
            hundred 424B2 structured-note prospectuses in a single day, so the
            first hundred filings contain no Form 4, 8-K or 10-K at all.
        limit: Maximum filings to return after filtering.
    """
    _rate_limit()
    result = {
        "cik": cik,
        "name": "",
        "sic": "",
        "sic_description": "",
        "ticker": "",
        "exchange": "",
        "ein": "",
        "state": "",
        "fiscal_year_end": "",
        "filings": [],
        "error": None,
    }

    try:
        url = f"{SEC_BASE}/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=SEC_HEADERS, timeout=30)

        if resp.ok:
            data = resp.json()
            result["name"] = data.get("name", "")
            result["sic"] = data.get("sic", "")
            result["sic_description"] = data.get("sicDescription", "")
            result["ein"] = data.get("ein", "")
            result["state"] = data.get("stateOfIncorporation", "")
            result["fiscal_year_end"] = data.get("fiscalYearEnd", "")

            # Get ticker and exchange
            tickers = data.get("tickers", [])
            exchanges = data.get("exchanges", [])
            if tickers:
                result["ticker"] = tickers[0]
            if exchanges:
                result["exchange"] = exchanges[0]

            # Parse recent filings
            recent = data.get("filings", {}).get("recent", {})
            if recent:
                form_types = recent.get("form", [])
                filing_dates = recent.get("filingDate", [])
                accessions = recent.get("accessionNumber", [])
                primary_docs = recent.get("primaryDocument", [])

                wanted = {f.upper() for f in forms} if forms else None
                for i in range(len(form_types)):
                    form = form_types[i]
                    if wanted and form.upper() not in wanted:
                        continue
                    result["filings"].append({
                        "form": form,
                        "filing_date": filing_dates[i] if i < len(filing_dates) else "",
                        "accession": accessions[i] if i < len(accessions) else "",
                        "document": primary_docs[i] if i < len(primary_docs) else "",
                    })
                    if len(result["filings"]) >= limit:
                        break
        else:
            result["error"] = f"HTTP {resp.status_code}"

    except Exception as e:
        logger.warning("Error fetching submissions for CIK %s: %s", cik, e)
        result["error"] = str(e)

    return result


_MARGIN_SOURCES = (
    ("gross_margin", "GrossProfit"),
    ("operating_margin", "OperatingIncome"),
    ("net_margin", "NetIncome"),
)


def _set_margins(row: Dict[str, Any], revenue: float) -> None:
    """Attach margins, but only where the numerator was actually reported.

    Defaulting a missing numerator to zero turns "this issuer does not report
    gross profit" into "this issuer earns a 0.0% gross margin", which is a
    claim rather than a gap. Banks and REITs never report gross profit and
    most banks never report operating income, so on those filers every margin
    line read 0.0%. It went unnoticed because the two companies the pipeline
    was built against both report all three.
    """
    for field, source in _MARGIN_SOURCES:
        value = row.get(source)
        row[field] = round(value / revenue * 100, 2) if value is not None else None


def extract_financial_statements(facts: Dict[str, Any], years: int = 5) -> Dict[str, Any]:
    """
    Extract key financial statement data from XBRL company facts.

    Returns structured income statement, balance sheet, and cash flow data
    for the specified number of years.
    """
    result = {
        "income_statement": [],
        "balance_sheet": [],
        "cash_flow": [],
        "quarterly": [],
        "ttm": {},
        "metrics": {},
    }

    us_gaap = facts.get("us-gaap", {})
    if not us_gaap:
        return result

    # Key concepts to extract
    income_concepts = {
        # Ordered by preference. Banks and insurers report total revenue as
        # RevenuesNetOfInterestExpense and stop tagging `Revenues` entirely, so
        # omitting it leaves every financial-sector issuer without a revenue line.
        "Revenues": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax",
            "RevenuesNetOfInterestExpense",
            "SalesRevenueGoodsNet",
            "SalesRevenueServicesNet",
        ],
        "GrossProfit": ["GrossProfit"],
        "OperatingIncome": ["OperatingIncomeLoss", "OperatingIncome"],
        "NetIncome": ["NetIncomeLoss", "NetIncome", "ProfitLoss"],
        "EPS_Diluted": ["EarningsPerShareDiluted"],
        "EPS_Basic": ["EarningsPerShareBasic"],
        # Research intensity is the one operating-expense line that separates
        # otherwise similar issuers, and it is what a peer comparison of two
        # semiconductor companies actually turns on.
        "ResearchAndDevelopment": [
            "ResearchAndDevelopmentExpense",
            "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost",
            "ResearchAndDevelopmentExpenseSoftwareExcludingAcquiredInProcessCost",
        ],
        "SellingGeneralAdministrative": [
            "SellingGeneralAndAdministrativeExpense",
            "GeneralAndAdministrativeExpense",
        ],
    }

    balance_concepts = {
        "TotalAssets": ["Assets"],
        "TotalLiabilities": ["Liabilities"],
        "StockholdersEquity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
        "Cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsAndShortTermInvestments"],
        "TotalDebt": ["LongTermDebt", "DebtCurrent", "LongTermDebtAndCapitalLeaseObligations"],
        "Inventory": ["InventoryNet", "Inventory"],
        "AccountsReceivable": ["AccountsReceivableNetCurrent", "AccountsReceivableNet"],
        "Goodwill": ["Goodwill"],
        # Liquidity, leverage and working-capital detail. These carry the
        # balance-sheet section: without current assets and liabilities there is
        # no current ratio, and without the investment tiers a company holding
        # most of its liquidity in marketable securities reads as cash-poor.
        "CurrentAssets": ["AssetsCurrent"],
        "CurrentLiabilities": ["LiabilitiesCurrent"],
        "ShortTermInvestments": [
            "ShortTermInvestments",
            "MarketableSecuritiesCurrent",
            "AvailableForSaleSecuritiesCurrent",
            "AvailableForSaleSecuritiesDebtSecuritiesCurrent",
        ],
        "LongTermInvestments": [
            "LongTermInvestments",
            "MarketableSecuritiesNoncurrent",
            "AvailableForSaleSecuritiesNoncurrent",
            "AvailableForSaleSecuritiesDebtSecuritiesNoncurrent",
        ],
        # Issuers migrate between the current/noncurrent split and a single
        # total; carry the total so liquidity is measurable either way.
        "MarketableSecurities": [
            "AvailableForSaleSecuritiesDebtSecurities",
            "AvailableForSaleSecurities",
            "MarketableSecurities",
        ],
        # Strategic stakes in other companies, which sit outside the
        # marketable-securities line and are often the largest single
        # discretionary use of the balance sheet.
        "EquityInvestments": [
            "EquitySecuritiesFVNINoncurrent",
            "EquitySecuritiesWithoutReadilyDeterminableFairValueAmount",
            "EquityMethodInvestments",
        ],
        "AccruedLiabilities": ["AccruedLiabilitiesCurrent"],
        "BuybackAuthorizationRemaining": [
            "StockRepurchaseProgramRemainingAuthorizedRepurchaseAmount1",
            "StockRepurchaseProgramRemainingAuthorizedRepurchaseAmount",
        ],
        "LongTermDebtNoncurrent": ["LongTermDebtNoncurrent"],
        "DebtCurrent": ["DebtCurrent", "LongTermDebtCurrent"],
        "PPENet": ["PropertyPlantAndEquipmentNet"],
        "AccountsPayable": ["AccountsPayableCurrent", "AccountsPayable"],
        "DeferredRevenue": [
            "ContractWithCustomerLiabilityCurrent",
            "DeferredRevenueCurrent",
        ],
        "RetainedEarnings": ["RetainedEarningsAccumulatedDeficit"],
        "OperatingLeaseLiability": [
            "OperatingLeaseLiabilityNoncurrent",
            "OperatingLeaseLiability",
        ],
        "IntangiblesNet": ["IntangibleAssetsNetExcludingGoodwill"],
        # Off-balance-sheet supply commitments, disclosed in the commitments
        # note. For a fabless manufacturer these can exceed reported liabilities.
        "PurchaseObligation": [
            "PurchaseObligation",
            "UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount",
            "PurchaseCommitmentRemainingMinimumAmountCommitted",
        ],
    }

    cashflow_concepts = {
        "OperatingCashFlow": [
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        ],
        "CapEx": [
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
            "PaymentsToAcquirePropertyPlantAndEquipmentAndIntangibleAssets",
        ],
        "StockRepurchases": ["PaymentsForRepurchaseOfCommonStock"],
        "Dividends": ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"],
        "StockBasedComp": ["ShareBasedCompensation", "StockBasedCompensationExpense"],
        # Capital allocation cannot be characterised from buybacks alone: the
        # investing and financing totals show whether returns were funded from
        # operations or from the balance sheet.
        "InvestingCashFlow": ["NetCashProvidedByUsedInInvestingActivities"],
        "FinancingCashFlow": ["NetCashProvidedByUsedInFinancingActivities"],
        "DebtIssued": ["ProceedsFromIssuanceOfLongTermDebt", "ProceedsFromIssuanceOfDebt"],
        "DebtRepaid": ["RepaymentsOfLongTermDebt", "RepaymentsOfDebt"],
        "Depreciation": [
            "DepreciationDepletionAndAmortization",
            "DepreciationAmortizationAndAccretionNet",
        ],
        "TaxExpense": ["IncomeTaxExpenseBenefit"],
        "PretaxIncome": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"],
    }

    def get_concept_values(concept_names: List[str], period_type: str = "FY") -> List[Dict]:
        """
        Values for a metric, merged across every candidate concept name.

        Companies migrate between XBRL tags over time: NVIDIA reported revenue
        under RevenueFromContractWithCustomerExcludingAssessedTax through FY2022
        and under Revenues afterwards. Returning the first *existing* concept
        therefore yielded four-year-stale figures whose periods did not align
        with the other metrics, leaving revenue absent and all margins at zero.

        Candidates are merged by period end, with earlier names in the list
        winning ties, so both historical and current tags contribute.
        """
        by_period: Dict[str, Dict] = {}

        for name in reversed(concept_names):  # reversed: higher priority overwrites
            if name not in us_gaap:
                continue
            units = us_gaap[name].get("units", {})
            for unit_type in ["USD", "USD/shares", "shares", "pure"]:
                if unit_type not in units:
                    continue
                values = units[unit_type]
                if period_type == "FY":
                    filtered = [
                        v for v in values
                        if v.get("form") == "10-K"
                        and v.get("fp") == "FY"
                        and _is_annual_duration(v)
                    ]
                else:
                    filtered = [
                        v for v in values
                        if v.get("form") in ("10-Q", "10-K")
                        and v.get("fp") in ("Q1", "Q2", "Q3", "Q4")
                        and _is_quarterly_duration(v)
                    ]
                for v in filtered:
                    end = v.get("end", "")
                    if not end:
                        continue
                    existing = by_period.get(end)
                    # Prefer the earliest filing that reported this period. Later
                    # filings repeat it as a comparative and stamp it with their
                    # own fiscal year, which mislabels companies whose fiscal
                    # year is named for its start (52/53-week retail calendars).
                    #
                    # That preference holds only within a single concept. Applied
                    # across concepts it let a low-priority tag that happened to
                    # be filed earlier outrank the issuer's primary tag, so one
                    # year of a series could be drawn from a different concept
                    # than the next and a year-over-year change became a
                    # comparison between two different things.
                    if existing is not None:
                        same_concept = existing.get("_concept") == name
                        if same_concept and existing.get("filed", "") <= v.get("filed", ""):
                            continue
                    v = dict(v, _concept=name)
                    by_period[end] = v
                break  # first available unit type only

        merged = sorted(by_period.values(), key=lambda x: x.get("end", ""), reverse=True)
        limit = years if period_type == "FY" else years * 4
        return merged[:limit]

    # Build annual data
    annual_data = defaultdict(dict)

    for metric_name, concept_names in income_concepts.items():
        values = get_concept_values(concept_names, "FY")
        for v in values:
            period_end = v.get("end", "")[:7]  # YYYY-MM
            annual_data[period_end][metric_name] = _safe_float(v.get("val", 0))
            annual_data[period_end]["period_end_date"] = v.get("end")
            if v.get("start"):
                annual_data[period_end]["period_start_date"] = v.get("start")
            # Adopt the fiscal-year label from the earliest filing seen for this
            # period, which is the issuer's own label for it.
            filed = v.get("filed", "")
            prior_filed = annual_data[period_end].get("_fy_filed")
            if v.get("fy") and (prior_filed is None or filed < prior_filed):
                annual_data[period_end]["fiscal_year"] = v.get("fy")
                annual_data[period_end]["_fy_filed"] = filed

    for metric_name, concept_names in balance_concepts.items():
        values = get_concept_values(concept_names, "FY")
        for v in values:
            period_end = v.get("end", "")[:7]
            annual_data[period_end][metric_name] = _safe_float(v.get("val", 0))
            # Which XBRL tag supplied the figure. Where an issuer switches tags
            # part way through a series, a year-over-year change would otherwise
            # compare two different concepts and report a move that never
            # happened; callers can check this before differencing.
            annual_data[period_end][f"{metric_name}_concept"] = v.get("_concept")

    for metric_name, concept_names in cashflow_concepts.items():
        values = get_concept_values(concept_names, "FY")
        for v in values:
            period_end = v.get("end", "")[:7]
            annual_data[period_end][metric_name] = _safe_float(v.get("val", 0))

    # Convert to list and sort
    for period, data in sorted(annual_data.items(), reverse=True)[:years]:
        data["period_end"] = period
        data.pop("_fy_filed", None)
        # Fall back to the calendar year of the period end only when the issuer's
        # own label is unavailable.
        if not data.get("fiscal_year"):
            end_date = data.get("period_end_date") or period
            if end_date[:4].isdigit():
                data["fiscal_year"] = int(end_date[:4])
        result["income_statement"].append(data)

        # The three statements were collected into one row but only the income
        # statement was ever published, so balance_sheet and cash_flow returned
        # empty and the report had no section to build from. Project the same
        # row onto the other two statements rather than re-querying.
        stamp = {"fiscal_year": data.get("fiscal_year"),
                 "period_end": period,
                 "period_end_date": data.get("period_end_date")}
        balance_row = {k: data[k] for k in balance_concepts if k in data}
        if balance_row:
            result["balance_sheet"].append({**stamp, **balance_row})
        cashflow_row = {k: data[k] for k in cashflow_concepts if k in data}
        if cashflow_row:
            result["cash_flow"].append({**stamp, **cashflow_row})

    # ── Quarterly series, with a derived Q4 ───────────────────────────────
    quarterly_data = defaultdict(dict)
    for metric_name, concept_names in income_concepts.items():
        for v in get_concept_values(concept_names, "Q"):
            end = v.get("end", "")
            if not end:
                continue
            q = quarterly_data[end]
            q[metric_name] = _safe_float(v.get("val", 0))
            q["fiscal_year"] = v.get("fy")
            q["fiscal_period"] = v.get("fp")

    # A quarter is only real if it carries at least one income-statement value.
    # Facts for other metrics can create an entry at the fiscal year end that
    # holds no results; counting those made the Q1-Q3 tally four and suppressed
    # the derived Q4 for issuers on a 52/53-week calendar.
    income_metrics = set(income_concepts)
    quarters = []
    for end, data in sorted(quarterly_data.items(), reverse=True):
        if not any(data.get(m) is not None for m in income_metrics):
            continue
        data["period_end"] = end
        data["derived"] = False
        quarters.append(data)

    # Many issuers, NVIDIA included, never tag a discrete Q4 duration. Q4 is
    # computed as the full year less Q1-Q3 and flagged as DERIVED so the report
    # can label it rather than presenting it as a reported figure.
    #
    # Quarters are matched to a fiscal year by date range, not by the XBRL `fy`
    # field: `fy` is the fiscal year of the filing that reported the fact, so a
    # quarter restated in a later filing carries the wrong year and produced a
    # negative Q4 when used for this.
    for annual in result["income_statement"]:
        fy_start = annual.get("period_start_date")
        fy_end_date = annual.get("period_end_date")
        if not fy_start or not fy_end_date:
            continue

        # The three interim quarters are those ending strictly inside the year.
        # A row ending exactly on the fiscal year end is the fourth quarter, even
        # when the issuer labels it otherwise, and must not be counted as interim.
        in_year = sorted(
            (q for q in quarters
             if not q.get("derived")
             and fy_start <= q.get("period_end", "") < fy_end_date),
            key=lambda x: x["period_end"],
        )
        if len(in_year) != 3:
            continue

        existing_q4 = next((q for q in quarters
                            if q.get("period_end") == fy_end_date and not q.get("derived")),
                           None)
        target = existing_q4 if existing_q4 is not None else {
            "period_end": fy_end_date, "fiscal_period": "Q4",
            "fiscal_year": annual.get("fiscal_year"),
        }

        filled = False
        for metric in ("Revenues", "GrossProfit", "OperatingIncome", "NetIncome"):
            full_year = annual.get(metric)
            if full_year is None or target.get(metric) is not None:
                continue
            partial = sum(q.get(metric, 0) or 0 for q in in_year)
            if partial:
                target[metric] = full_year - partial
                filled = True

        if filled:
            target["fiscal_period"] = "Q4"
            target["derived"] = True
            if existing_q4 is None:
                quarters.append(target)

    quarters.sort(key=lambda q: q.get("period_end", ""), reverse=True)
    result["quarterly"] = quarters[:years * 4]

    # ── Trailing twelve months from the four most recent quarters ─────────
    recent_four = [q for q in result["quarterly"] if q.get("Revenues")][:4]
    if len(recent_four) == 4:
        ttm = {"period_end": recent_four[0].get("period_end"),
               "quarters_used": [q.get("period_end") for q in recent_four],
               "includes_derived": any(q.get("derived") for q in recent_four)}
        for metric in ("Revenues", "GrossProfit", "OperatingIncome", "NetIncome"):
            vals = [q.get(metric) for q in recent_four if q.get(metric) is not None]
            if len(vals) == 4:
                ttm[metric] = sum(vals)
        rev = ttm.get("Revenues")
        if rev:
            _set_margins(ttm, rev)
        result["ttm"] = ttm

    # Calculate key metrics from latest period
    if result["income_statement"]:
        latest = result["income_statement"][0]
        revenue = latest.get("Revenues", 0)
        # Per-year margins, so the report can show a trend rather than a point.
        for row in result["income_statement"]:
            rev = row.get("Revenues") or 0
            if rev:
                _set_margins(row, rev)
            ocf = row.get("OperatingCashFlow") or 0
            capex = row.get("CapEx") or 0
            if ocf:
                row["FreeCashFlow"] = ocf - abs(capex)
        gross_profit = latest.get("GrossProfit", 0)
        operating_income = latest.get("OperatingIncome", 0)
        net_income = latest.get("NetIncome", 0)
        total_assets = latest.get("TotalAssets", 0)
        equity = latest.get("StockholdersEquity", 0)
        debt = latest.get("TotalDebt", 0)

        result["metrics"] = {
            "gross_margin": round(gross_profit / revenue * 100, 2) if revenue else 0,
            "operating_margin": round(operating_income / revenue * 100, 2) if revenue else 0,
            "net_margin": round(net_income / revenue * 100, 2) if revenue else 0,
            "debt_to_equity": round(debt / equity, 3) if equity else 0,
            "roa": round(net_income / total_assets * 100, 2) if total_assets else 0,
            "roe": round(net_income / equity * 100, 2) if equity else 0,
        }

    return result


def _parse_rendered_table(html: str) -> Dict[str, Any]:
    """Read one of EDGAR's rendered statement tables.

    The R-files are the exhibits the SEC's own viewer displays, and they carry
    the dimensional breakdowns — revenue by segment, by region, by market —
    that companyfacts omits. Companyfacts publishes only undimensioned facts,
    which is why the segment section had no data source at all.

    Their layout is consistent across filers: a period header, then rows that
    are either a dimension member on its own (a full-width label such as "Data
    Center") or a fact under the member in force.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"periods": [], "rows": []}

    table = BeautifulSoup(html, "html.parser").find("table")
    if table is None:
        return {"periods": [], "rows": []}

    raw_rows = []
    periods: List[str] = []
    for tr in table.find_all("tr"):
        texts = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        filled = [t for t in texts if t]
        if not filled:
            continue
        if not periods and len(filled) > 1 and all(_looks_like_date(t) for t in filled):
            periods = filled
            continue
        raw_rows.append(filled)

    # A single-cell row is either a dimension member or the note's line-items
    # header, which EDGAR repeats before every member. Distinguishing them by
    # repetition is what separates "United States" from "Revenues and
    # Long-Lived Assets"; treating the header as a member collapsed an entire
    # geographic breakdown into one meaningless row.
    single = [r[0] for r in raw_rows if len(r) == 1]
    repeated = {label for label in single if single.count(label) > 1}

    rows: List[Dict[str, Any]] = []
    member = ""
    for filled in raw_rows:
        if len(filled) == 1:
            label = filled[0]
            if "[" in label or label in repeated or _looks_like_date(label):
                continue
            member = label
            continue
        values = [_parse_rendered_number(v) for v in filled[1:]]
        if all(v is None for v in values):
            continue
        rows.append({"member": member, "label": filled[0], "values": values})

    return {"periods": periods, "rows": rows}


def _looks_like_date(text: str) -> bool:
    return bool(re.match(r"^[A-Z][a-z]{2}\.?\s+\d{1,2},\s+\d{4}$", text.strip()))


def _parse_rendered_number(text: str) -> Optional[float]:
    """Read a figure out of a rendered cell, honouring accounting negatives."""
    cleaned = text.replace("$", "").replace(",", "").replace("%", "").strip()
    if not cleaned or cleaned in ("—", "-", "–"):
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


# Which rendered statement answers which question. Matched against the report's
# ShortName in FilingSummary.xml, most specific first.
# Rendered reports are named "<note title> - <what this table shows> (Details)".
# Classifying on the note title alone fails wherever the title is broad: Apple
# files everything under "Segment Information and Geographic Data", so revenue
# by segment, sales by country and assets by country all matched "geographic"
# and the first one seen won. The sub-name is what actually describes the table.
_SEGMENT_REPORTS = (
    ("markets", re.compile(
        r"(by market|disaggregat|by product|revenue.*categor|"
        r"net sales.*(product|categor))", re.I)),
    ("segments", re.compile(
        r"(reportable segments?|by segment|operating segments?|"
        r"^segment reporting|segments?.*(result|information|revenue|earnings|data))",
        re.I)),
    ("geographic", re.compile(
        r"((revenue|net sales|sales).*(region|countr|geograph)|"
        r"(geograph|region|countr).*(revenue|sales))", re.I)),
    ("long_lived", re.compile(
        r"(long-?lived|property.*(region|countr|geograph))", re.I)),
)

# Some issuers name the table only "Summary". That is too generic to trust on
# its own — it also names equity-award and preferred-stock schedules — so it is
# accepted only when the enclosing note is a segment note.
_SEGMENT_REPORTS_LOOSE = (
    ("segments", re.compile(r"\bsummary\b", re.I)),
)

_SEGMENT_NOTE_TITLE = re.compile(
    r"\bsegments?\b|\bgeographic\b|disaggregat|^(net )?(revenues?|sales)\b", re.I)

_CONCENTRATION_NOTE = re.compile(
    r"concentration|major customer|significant customer", re.I)

# Notes that use the same vocabulary for something else entirely. A bank's
# "Loans - By Portfolio Segment" is a credit disclosure, not a segment note.
_NOT_A_SEGMENT_NOTE = re.compile(
    r"loan|delinquen|credit quality|allowance|charge-?off|goodwill by|"
    r"impair|hedg|derivativ|fair value|deposit|securitiz", re.I)


def find_latest_filing(cik: str, form: str) -> Optional[Dict[str, Any]]:
    """Locate an issuer's most recent filing of a given form type.

    The submissions endpoint holds only the last thousand filings inline and
    pages the remainder into separate files. For an issuer that files heavily —
    Exxon's recent block is entirely Forms 4 and 8-K — the annual report is not
    in the inline block at all, and reading only that block reports the company
    as having never filed a 10-K.
    """
    submissions = sec_get_json(f"{SEC_BASE}/submissions/CIK{cik.zfill(10)}.json")
    if not submissions:
        return None

    def locate(block: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        forms = block.get("form", [])
        try:
            index = forms.index(form)
        except ValueError:
            return None
        accession = block["accessionNumber"][index]
        primary_docs = block.get("primaryDocument", [])
        primary_doc = primary_docs[index] if index < len(primary_docs) else None
        return {
            "accession": accession,
            "report_date": (block.get("reportDate") or [None] * (index + 1))[index],
            "filing_date": (block.get("filingDate") or [None] * (index + 1))[index],
            "primary_document": primary_doc,
            "base_url": (f"{SEC_WWW_BASE}/Archives/edgar/data/{int(cik)}/"
                         f"{accession.replace('-', '')}"),
        }

    filings = submissions.get("filings", {})
    found = locate(filings.get("recent", {}))
    if found:
        return found

    # Overflow files are ordered newest first, so the first hit is the latest.
    for page in filings.get("files", []):
        name = page.get("name")
        if not name:
            continue
        older = sec_get_json(f"{SEC_BASE}/submissions/{name}")
        if not older:
            continue
        found = locate(older)
        if found:
            return found
    return None


def get_segment_data(cik: str,
                     total_revenue: Optional[float] = None) -> Dict[str, Any]:
    """Revenue by segment, region and market, and customer concentration.

    Sourced from the latest 10-K's rendered statements rather than from
    companyfacts, which carries no dimensional data.

    Where consolidated revenue is supplied, each revenue breakdown must
    reconcile to it before being published. Report titles vary enough between
    issuers that name matching alone will occasionally select a table combining
    two dimensions — Exxon reports segment and geography in one schedule — and
    the members then sum to roughly twice revenue. Reconciliation catches that
    generically, where no amount of pattern tuning does.
    """
    result: Dict[str, Any] = {
        "segments": [],
        "geographic": [],
        "markets": [],
        "long_lived_assets": [],
        "customer_concentration": {},
        "periods": [],
        "source_url": None,
    }

    filing = find_latest_filing(cik, "10-K")
    if not filing:
        return result

    base = filing["base_url"]
    result["source_url"] = f"{base}/"
    result["fiscal_period_end"] = filing["report_date"]

    summary = sec_get_text(f"{base}/FilingSummary.xml")
    if not summary:
        return result

    # Only the "(Details)" reports carry figures; the note and table variants
    # repeat the same content as narrative or as an empty shell. Candidates are
    # collected per subject rather than taking the first match, because the
    # first report under a heading is often the narrative and yields no rows.
    wanted: Dict[str, List[str]] = defaultdict(list)
    for block in re.findall(r"<Report[^>]*>(.*?)</Report>", summary, re.S):
        name = re.search(r"<ShortName>(.*?)</ShortName>", block)
        filename = re.search(r"<HtmlFileName>(.*?)</HtmlFileName>", block)
        if not name or not filename:
            continue
        short = html.unescape(name.group(1))
        if "Detail" not in short or _NOT_A_SEGMENT_NOTE.search(short):
            continue
        note, _, detail = short.partition(" - ")
        detail = detail or short

        matched = next((key for key, pattern in _SEGMENT_REPORTS
                        if pattern.search(detail)), None)
        if not matched and _SEGMENT_NOTE_TITLE.search(note):
            matched = next((key for key, pattern in _SEGMENT_REPORTS_LOOSE
                            if pattern.search(detail)), None)
        if not matched and _CONCENTRATION_NOTE.search(short):
            matched = "concentration"
        if matched:
            wanted[matched].append(filename.group(1))

    concentration: List[Dict[str, Any]] = []
    for key, filenames in wanted.items():
        for filename in filenames:
            parsed = _parse_rendered_table(sec_get_text(f"{base}/{filename}"))
            if not parsed["rows"]:
                continue
            if not result["periods"]:
                result["periods"] = parsed["periods"]

            # Concentration percentages are disclosed inside whichever note the
            # issuer chose, most often the geographic or revenue note rather
            # than one of their own, so every table is scanned for them.
            concentration.extend(_shape_concentration(parsed))
            if key == "concentration":
                continue

            measure = _ASSET_LINE if key == "long_lived" else _REVENUE_LINE
            target = "long_lived_assets" if key == "long_lived" else key
            shaped = _shape_breakdown(parsed, measure)
            if key != "long_lived" and not _reconciles(shaped, total_revenue):
                continue
            if shaped and not result[target]:
                result[target] = shaped
            if key == "geographic" and not result["long_lived_assets"]:
                # The same note usually carries assets by region beside revenue.
                result["long_lived_assets"] = _shape_breakdown(parsed, _ASSET_LINE)
            if result[target]:
                break

    # Deduplicate: the same counterparty can appear in more than one note.
    unique: Dict[tuple, Dict[str, Any]] = {}
    for item in concentration:
        unique.setdefault((item["counterparty"], item["basis"]), item)
    result["customer_concentration"] = sorted(
        unique.values(), key=lambda c: c["pct"], reverse=True)

    return result


_REVENUE_LINE = re.compile(r"revenue|net sales|^sales", re.I)
_ASSET_LINE = re.compile(r"long-?lived|property.*equipment", re.I)
# Members that restate the consolidated figure or reverse it out. Counting them
# alongside the real members doubles the denominator and halves every share.
_AGGREGATE_MEMBER = re.compile(
    r"^(operating segments?|reportable segments?|total|consolidat|"
    r"segment reconciling items?|segment reporting|intersegment|corporate|"
    r"all other|elimination)", re.I)


def _clean_member(name: str) -> str:
    """Drop the axis qualifiers EDGAR appends to a member label.

    Rendered members read "Compute & Networking | Operating Segments"; only the
    part before the first bar names the segment.
    """
    return name.split("|")[0].strip()


def _shape_breakdown(parsed: Dict[str, Any],
                     measure: re.Pattern = _REVENUE_LINE) -> List[Dict[str, Any]]:
    """One entry per dimension member for a single measure.

    Members are kept in document order first so that parent/child rows can be
    identified: a segment note frequently lists a total ("Data Center") ahead of
    its components ("Compute", "Networking"), and summing all of them counts the
    revenue twice.
    """
    entries: List[Dict[str, Any]] = []
    seen = set()
    for row in parsed["rows"]:
        member = _clean_member(row["member"])
        if not member or member in seen:
            continue
        if _AGGREGATE_MEMBER.match(member) or not measure.search(row["label"]):
            continue
        # A "member" that names a measure is a line item the layout left
        # ungrouped, not a dimension: "Sales and other operating revenue" is
        # what is being counted, not something it is counted across.
        if _REVENUE_LINE.search(member) or _ASSET_LINE.search(member):
            continue
        values = [v for v in row["values"]]
        if not values or values[0] is None:
            continue
        seen.add(member)
        entries.append({
            "name": member,
            "line_item": row["label"],
            "current": values[0],
            "prior": values[1] if len(values) > 1 else None,
            "history": values,
            "parent_of": [],
        })

    _mark_parents(entries)

    # A member that is the sum of every other member is the consolidated total
    # wearing a member's label — Coca-Cola tags one "Segment Reporting" — and
    # listing it beside the parts restates the whole as though it were one.
    entries = [e for e in entries if len(e["parent_of"]) < len(entries) - 1]
    _mark_parents(entries)

    # Shares are taken against the members that stand on their own, so a
    # breakdown that lists sub-components still sums to 100%.
    leaves = [e for e in entries if not e["parent_of"]]
    total = sum(e["current"] for e in leaves if e["current"] > 0) or None
    for entry in entries:
        entry["share_pct"] = (round(entry["current"] / total * 100, 1)
                              if total else None)
        entry["growth_pct"] = (
            round((entry["current"] - entry["prior"]) / abs(entry["prior"]) * 100, 1)
            if entry["prior"] else None)
    # One member is not a breakdown. A lone entry means the table was matched in
    # error or the measure was not the one the table reports, and publishing it
    # as "100% of revenue" would state something the filing does not.
    if len(entries) < 2:
        return []
    return sorted(entries, key=lambda e: e["current"], reverse=True)


def _reconciles(entries: List[Dict[str, Any]],
                total_revenue: Optional[float], tolerance: float = 0.05) -> bool:
    """True when the breakdown's independent members sum to consolidated revenue.

    Rendered figures are in the units the statement uses, usually millions,
    while companyfacts reports whole dollars, so the comparison is made after
    scaling to whichever order of magnitude matches.
    """
    if not entries:
        return False
    if not total_revenue:
        return True          # nothing to check against; accept as filed
    total = sum(e["current"] for e in entries
                if not e["parent_of"] and e["current"] > 0)
    if total <= 0:
        return False
    for scale in (1, 1e3, 1e6):
        if abs(total * scale - total_revenue) / total_revenue <= tolerance:
            return True
    return False


def _mark_parents(entries: List[Dict[str, Any]]) -> None:
    """Flag members whose value is the sum of the members listed beneath them."""
    for i, parent in enumerate(entries):
        running = 0.0
        for j in range(i + 1, len(entries)):
            child = entries[j]
            if child["current"] is None:
                break
            running += child["current"]
            if j > i and abs(running - parent["current"]) <= max(1.0, abs(parent["current"]) * 0.005):
                parent["parent_of"] = [e["name"] for e in entries[i + 1:j + 1]]
                break
            if running > parent["current"]:
                break


_CONCENTRATION_PCT = re.compile(r"concentration risk|percent|%", re.I)


def _shape_concentration(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Concentration percentages disclosed against a named counterparty.

    Issuers frequently identify these only as "Customer A", which is itself the
    disclosure: the dependency is reported without the counterparty's name.
    """
    found = []
    for row in parsed["rows"]:
        member = _clean_member(row["member"])
        if not member or not _CONCENTRATION_PCT.search(row["label"]):
            continue
        # "All other" carrying 95% of revenue is a residual bucket, not a
        # concentration; naming it as an exposure would be actively misleading.
        if _AGGREGATE_MEMBER.match(member):
            continue
        value = next((v for v in row["values"] if v is not None), None)
        if value is None or not 0 < value <= 100:
            continue
        basis = "revenue" if "Revenue" in row["member"] else (
            "receivables" if "Receivable" in row["member"] else "revenue")
        found.append({"counterparty": member, "pct": value, "basis": basis,
                      "dimension": row["member"]})
    return found


def _form4_raw_xml_url(cik: str, accession: str, document: str) -> str:
    """
    URL of a Form 4's machine-readable XML.

    The submissions index gives the *rendered* document path,
    "xslF345X06/wk-form4_123.xml", which serves an HTML page built from the XML
    by an XSL transform. Stripping the transform directory yields the raw XML.
    Only www.sec.gov serves the Archives tree; data.sec.gov returns 404.
    """
    raw = document.split("/")[-1]
    return f"{SEC_WWW_BASE}/Archives/edgar/data/{cik.lstrip('0')}/{accession}/{raw}"


def _strip_ns(root):
    """Remove XML namespaces so tags can be addressed by local name."""
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _val(node, path: str) -> str:
    """
    Text of a node, unwrapping SEC's <value> indirection.

    Ownership XML wraps most fields as <transactionShares><value>500</value>,
    but the same field can appear unwrapped in older filings.
    """
    el = node.find(path)
    if el is None:
        return ""
    inner = el.find("value")
    text = (inner if inner is not None else el).text
    return (text or "").strip()


# Form 4 transaction codes. Only open-market trades signal conviction; grants,
# tax withholding and gifts are compensation mechanics and are counted apart so
# a vesting event is not reported as an insider purchase.
OPEN_MARKET_CODES = {"P", "S"}
TRANSACTION_CODE_MEANINGS = {
    "P": "Open-market purchase",
    "S": "Open-market sale",
    "A": "Grant or award",
    "D": "Disposition to issuer",
    "F": "Shares withheld for tax",
    "G": "Gift",
    "I": "Discretionary transaction",
    "M": "Option/RSU exercise",
    "C": "Conversion of derivative",
    "X": "In-the-money option exercise",
    "O": "Out-of-money option exercise",
    "E": "Expiration of short position",
    "H": "Expiration of long position",
    "J": "Other acquisition or disposition",
    "K": "Equity swap",
    "L": "Small acquisition",
    "U": "Disposition in a tender offer",
    "V": "Voluntary early report",
    "W": "Acquisition by will or descent",
    "Z": "Voting trust deposit or withdrawal",
}


def _parse_form4_document(xml_text: str, filing_date: str, source_url: str) -> List[Dict[str, Any]]:
    """
    Every transaction row in one Form 4.

    A single filing routinely reports several rows — an option exercise, the
    sale that funds it and the shares withheld for tax — so each row is emitted
    separately rather than taking only the first.
    """
    try:
        root = _strip_ns(ET.fromstring(xml_text))
    except ET.ParseError:
        return []

    owners = []
    for owner in root.findall(".//reportingOwner"):
        rel = owner.find("reportingOwnerRelationship")
        title = _val(rel, "officerTitle") if rel is not None else ""
        roles = []
        if rel is not None:
            for tag, label in (("isDirector", "Director"), ("isOfficer", "Officer"),
                               ("isTenPercentOwner", "10% owner"), ("isOther", "Other")):
                if _val(rel, tag) in ("1", "true"):
                    roles.append(label)
        owners.append({
            "name": _val(owner, "reportingOwnerId/rptOwnerName") or "Unknown",
            # The owner's own CIK. A person keeps one CIK across every issuer
            # they report at, which is what makes their other board seats
            # discoverable without a commercial directory.
            "cik": (_val(owner, "reportingOwnerId/rptOwnerCik") or "").lstrip("0"),
            "roles": roles,
            "title": title,
        })
    if not owners:
        owners = [{"name": "Unknown", "cik": "", "roles": [], "title": ""}]

    # The 10b5-1 checkbox lives at document level. Many filers leave it unset and
    # disclose the plan in a footnote instead, so both are consulted — but a
    # footnote is attributed only to the transactions that reference it. A filing
    # commonly pairs a plan sale with an unrelated gift, and treating the whole
    # filing as plan-based would misreport discretionary activity.
    plan_checkbox = _val(root, "aff10b5One") in ("1", "true")
    plan_footnotes = {
        f.get("id") for f in root.findall(".//footnote")
        if "10b5-1" in (f.text or "").lower().replace(" ", "")
        or "10b5-1" in (f.text or "").lower()
    }

    rows = []
    for kind, path in (("non_derivative", ".//nonDerivativeTransaction"),
                       ("derivative", ".//derivativeTransaction")):
        for txn in root.findall(path):
            coding = txn.find("transactionCoding")
            code = _val(coding, "transactionCode") if coding is not None else ""
            amounts = txn.find("transactionAmounts")
            if amounts is None:
                continue

            shares = _safe_float(_val(amounts, "transactionShares"))
            price = _safe_float(_val(amounts, "transactionPricePerShare"))
            disposed = _val(amounts, "transactionAcquiredDisposedCode") == "D"

            referenced = {fn.get("id") for fn in txn.iter("footnoteId")}
            under_plan = plan_checkbox or bool(referenced & plan_footnotes)

            for owner in owners:
                rows.append({
                    "date": _val(txn, "transactionDate") or filing_date,
                    "filing_date": filing_date,
                    "insider": owner["name"],
                    "insider_cik": owner.get("cik", ""),
                    "roles": owner["roles"],
                    "title": owner["title"],
                    "security": _val(txn, "securityTitle"),
                    "table": kind,
                    "code": code,
                    "code_meaning": TRANSACTION_CODE_MEANINGS.get(code, code),
                    "shares": shares,
                    "price": price,
                    "value": shares * price,
                    "acquired_disposed": "D" if disposed else "A",
                    "open_market": code in OPEN_MARKET_CODES,
                    "is_10b5_1": under_plan,
                    "shares_owned_after": _safe_float(
                        _val(txn, "postTransactionAmounts/sharesOwnedFollowingTransaction")),
                    "source_url": source_url,
                })
    return rows


def get_insider_transactions(cik: str, start_date: str = None,
                             max_filings: int = 250) -> Dict[str, Any]:
    """
    Form 4 insider transactions with share counts, prices and 10b5-1 status.

    Values are reported for open-market trades separately from total activity:
    grants, option exercises and tax withholding dominate the row count for most
    issuers and would otherwise swamp the signal.

    ``max_filings`` covers the whole two-year window for a typical large-cap;
    a lower cap silently truncates the sample and understates disposals, since
    filings are processed newest first.
    """
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")

    result = {
        "cik": cik,
        "filings_count": 0,
        "filings_parsed": 0,
        "transactions": [],
        "summary": {
            "total_sold": 0.0,
            "total_bought": 0.0,
            "total_value_sold": 0.0,
            "total_value_bought": 0.0,
            "discretionary_sold": 0.0,
            "plan_based_sold": 0.0,
            "open_market_value_sold": 0.0,
            "open_market_value_bought": 0.0,
        },
        "by_insider": {},
        "by_code": {},
        "error": None,
    }

    submissions = get_company_submissions(cik, forms=["4", "4/A"], limit=400)
    form4 = [f for f in submissions.get("filings", [])
             if f.get("filing_date", "") >= start_date]
    result["filings_count"] = len(form4)

    for filing in form4[:max_filings]:
        accession = (filing.get("accession") or "").replace("-", "")
        document = filing.get("document") or ""
        if not accession or not document:
            continue

        url = _form4_raw_xml_url(cik, accession, document)
        try:
            _rate_limit()
            resp = requests.get(url, headers=SEC_HEADERS, timeout=15)
            if not resp.ok:
                continue
            rows = _parse_form4_document(resp.text, filing.get("filing_date", ""), url)
        except Exception as e:
            logger.debug("Form 4 parse failed for %s: %s", url, e)
            continue

        if rows:
            result["filings_parsed"] += 1
        result["transactions"].extend(rows)

    for txn in result["transactions"]:
        shares, value = txn["shares"], txn["value"]
        summary = result["summary"]
        code_bucket = result["by_code"].setdefault(
            txn["code"], {"meaning": txn["code_meaning"], "count": 0,
                          "shares": 0.0, "value": 0.0})
        code_bucket["count"] += 1
        code_bucket["shares"] += shares
        code_bucket["value"] += value

        insider = result["by_insider"].setdefault(txn["insider"], {
            "title": txn["title"], "roles": txn["roles"], "transactions": 0,
            "total_sold": 0.0, "total_bought": 0.0,
            "value_sold": 0.0, "value_bought": 0.0,
        })
        insider["transactions"] += 1

        if txn["acquired_disposed"] == "D":
            summary["total_sold"] += shares
            summary["total_value_sold"] += value
            insider["total_sold"] += shares
            insider["value_sold"] += value
            if txn["is_10b5_1"]:
                summary["plan_based_sold"] += value
            else:
                summary["discretionary_sold"] += value
            if txn["open_market"]:
                summary["open_market_value_sold"] += value
        else:
            summary["total_bought"] += shares
            summary["total_value_bought"] += value
            insider["total_bought"] += shares
            insider["value_bought"] += value
            if txn["open_market"]:
                summary["open_market_value_bought"] += value

    result["transactions"].sort(key=lambda t: t.get("date", ""), reverse=True)
    return result



def get_institutional_holders(cik: str) -> Dict[str, Any]:
    """
    Get institutional ownership from 13F filings.
    """
    result = {
        "cik": cik,
        "total_institutional_pct": 0,
        "holders": [],
        "top_10": [],
    }

    # This would require parsing 13F filings which are complex XML
    # For now, we use yfinance as primary source for institutional data

    return result


def get_investment_portfolio(facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract investment portfolio data from XBRL facts.

    Tracks:
    - Marketable securities
    - Non-marketable equity securities
    - Strategic investments
    """
    result = {
        "marketable_securities": 0,
        "non_marketable_equity": 0,
        "total_investment_portfolio": 0,
        "gains_losses": 0,
        "history": [],
    }

    us_gaap = facts.get("us-gaap", {})

    # Investment concepts
    investment_concepts = {
        "MarketableSecurities": ["MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
        "NonMarketableEquity": ["EquitySecuritiesFvNiNoncurrent", "InvestmentsInAffiliatesSubsidiariesAssociatesAndJointVentures"],
        "InvestmentGains": ["GainLossOnInvestments", "UnrealizedGainLossOnInvestments"],
    }

    for metric_name, concept_names in investment_concepts.items():
        for name in concept_names:
            if name in us_gaap:
                units = us_gaap[name].get("units", {})
                if "USD" in units:
                    values = units["USD"]
                    if values:
                        latest = max(values, key=lambda x: x.get("end", ""))
                        result[metric_name.lower().replace(" ", "_")] = _safe_float(latest.get("val", 0))
                        break

    result["total_investment_portfolio"] = (
        result.get("marketable_securities", 0) +
        result.get("non_marketable_equity", 0)
    )

    return result


def get_full_financial_profile(ticker: str) -> Dict[str, Any]:
    """
    Comprehensive financial profile for deep intelligence.

    Combines all SEC EDGAR data sources into a unified profile.
    """
    result = {
        "ticker": ticker,
        "cik": None,
        "company_info": {},
        "financial_statements": {},
        "segments": {},
        "insider_activity": {},
        "investment_portfolio": {},
        "filings": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "errors": [],
    }

    # Resolve to the CIK that actually files financial statements, which can
    # differ from the ticker's mapped CIK after a holding-company reorganisation.
    cik = get_filer_cik(ticker)
    if not cik:
        result["errors"].append(f"Could not resolve ticker {ticker} to CIK")
        return result

    result["cik"] = cik

    # Get company info
    submissions = get_company_submissions(cik)
    if not submissions.get("error"):
        result["company_info"] = {
            "name": submissions.get("name", ""),
            "sic": submissions.get("sic", ""),
            "sic_description": submissions.get("sic_description", ""),
            "ticker": submissions.get("ticker", ""),
            "exchange": submissions.get("exchange", ""),
            "ein": submissions.get("ein", ""),
            "state": submissions.get("state", ""),
            "fiscal_year_end": submissions.get("fiscal_year_end", ""),
        }
        result["filings"] = submissions.get("filings", [])[:20]  # Recent 20
    else:
        result["errors"].append(f"Submissions error: {submissions.get('error')}")

    # Get company facts and financials
    facts_data = get_company_facts(cik)
    if not facts_data.get("error"):
        facts = facts_data.get("facts", {})
        result["financial_statements"] = extract_financial_statements(facts)
        result["investment_portfolio"] = get_investment_portfolio(facts)
    else:
        result["errors"].append(f"Company facts error: {facts_data.get('error')}")

    # Get insider activity
    insider_data = get_insider_transactions(cik)
    if not insider_data.get("error"):
        result["insider_activity"] = {
            "filings_count": insider_data.get("filings_count", 0),
            "summary": insider_data.get("summary", {}),
            "by_insider": insider_data.get("by_insider", {}),
            "recent_transactions": insider_data.get("transactions", [])[:20],
        }

    # Get segment data
    # Consolidated revenue lets the segment breakdowns be reconciled rather than
    # taken on trust from a report title.
    annual_rows = result["financial_statements"]["income_statement"]
    latest_revenue = annual_rows[0].get("Revenues") if annual_rows else None
    result["segments"] = get_segment_data(cik, total_revenue=latest_revenue)

    return result


# ── Convenience Exports ──────────────────────────────────────────────────────

def get_financials(ticker: str) -> Dict[str, Any]:
    """Get financial statements for a ticker."""
    return get_full_financial_profile(ticker)


def get_insiders(ticker: str) -> Dict[str, Any]:
    """Get insider transaction summary for a ticker."""
    cik = get_cik_from_ticker(ticker)
    if cik:
        return get_insider_transactions(cik)
    return {"error": f"Could not resolve ticker {ticker}"}


def resolve_ticker(ticker: str) -> Optional[str]:
    """Resolve ticker to CIK."""
    return get_cik_from_ticker(ticker)
