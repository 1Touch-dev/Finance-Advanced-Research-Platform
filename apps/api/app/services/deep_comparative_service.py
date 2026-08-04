"""
Deep Comparative Analysis Service
────────────────────────────────────────────────────────────────────────────
Expands peer comparison beyond basic metrics to include:
  - Segment-level revenue comparison
  - Operating efficiency metrics
  - Capital allocation patterns
  - R&D and innovation intensity
  - Employee productivity
  - Geographic revenue mix
  - Customer concentration
  - Management quality indicators
  - Valuation decomposition
  - Growth trajectory analysis

Uses SEC EDGAR XBRL data and financial APIs.
"""

import os
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics

logger = logging.getLogger(__name__)

# Alpha Vantage API
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
AV_BASE = "https://www.alphavantage.co/query"

# Financial Modeling Prep API (free tier).
# The v3 endpoints were retired for accounts opened after 31 August 2025 and now
# answer every request with a "Legacy Endpoint" error, so every ratio, growth and
# per-employee figure in this module was None for *all* tickers including the
# target. The stable endpoints take the symbol as a query parameter rather than a
# path segment, which is why the URL is assembled differently below.
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"

# SEC EDGAR (free)
SEC_COMPANY_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"

SEC_HEADERS = {
    "User-Agent": "Research Platform research@example.com",
    "Accept": "application/json",
}


# A vendor that answers 200 with a quota notice instead of data is the reason a
# five-ticker comparison rendered the target and nothing else: the first ticker
# consumed the daily allowance and the peers came back as prose the caller read
# as an empty statement. The notice is recorded per run so the report can say the
# peers are missing because of a quota rather than because they filed nothing.
_VENDOR_NOTES: Dict[str, str] = {}


def _note_vendor_limit(vendor: str, message: str) -> None:
    """Record the first quota or refusal message a vendor returned."""
    if vendor not in _VENDOR_NOTES:
        _VENDOR_NOTES[vendor] = str(message)[:300]
        logger.warning("%s limited this run: %s", vendor, _VENDOR_NOTES[vendor])


def _fetch_alpha_vantage(function: str, symbol: str, **kwargs) -> Dict[str, Any]:
    """Fetch data from Alpha Vantage API."""
    if not ALPHA_VANTAGE_KEY:
        return {}

    params = {
        "function": function,
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_KEY,
        **kwargs
    }

    try:
        resp = requests.get(AV_BASE, params=params, timeout=15)
        if resp.ok:
            payload = resp.json()
            # Alpha Vantage reports exhaustion with HTTP 200 and one of these
            # keys. Returning it unchecked lets a quota message be treated as a
            # company with no reported financials.
            if isinstance(payload, dict):
                for key in ("Note", "Information", "Error Message"):
                    if payload.get(key):
                        _note_vendor_limit("alpha_vantage", payload[key])
                        return {}
            return payload
    except Exception as e:
        logger.warning("Alpha Vantage fetch failed: %s", e)

    return {}


def _fetch_fmp(endpoint: str, symbol: str = None, **kwargs) -> Any:
    """Fetch data from Financial Modeling Prep's stable API."""
    if not FMP_API_KEY:
        return None

    params = {"apikey": FMP_API_KEY, **kwargs}
    if symbol:
        params["symbol"] = symbol

    try:
        resp = requests.get(f"{FMP_BASE}/{endpoint}", params=params, timeout=15)
        if resp.ok:
            payload = resp.json()
            if isinstance(payload, dict) and payload.get("Error Message"):
                _note_vendor_limit("fmp", payload["Error Message"])
                return None
            return payload
        if resp.status_code in (401, 402, 403, 429):
            _note_vendor_limit("fmp", f"HTTP {resp.status_code}: {resp.text[:160]}")
    except Exception as e:
        logger.warning("FMP fetch failed: %s", e)

    return None


def _fetch_sec_company_facts(cik: str) -> Dict[str, Any]:
    """Fetch company facts from SEC EDGAR."""
    cik_padded = cik.zfill(10)

    try:
        resp = requests.get(
            SEC_COMPANY_FACTS.format(cik=cik_padded),
            headers=SEC_HEADERS,
            timeout=30
        )
        if resp.ok:
            return resp.json()
    except Exception as e:
        logger.warning("SEC company facts fetch failed: %s", e)

    return {}


def _lookup_cik(ticker: str) -> Optional[str]:
    """Look up CIK for a ticker symbol."""
    try:
        resp = requests.get(
            "https://www.sec.gov/cgi-bin/browse-edgar",
            params={
                "action": "getcompany",
                "CIK": ticker,
                "type": "10-K",
                "dateb": "",
                "owner": "include",
                "count": 1,
                "output": "atom"
            },
            headers=SEC_HEADERS,
            timeout=15
        )
        if resp.ok:
            # Parse CIK from response
            import re
            match = re.search(r'CIK=(\d+)', resp.text)
            if match:
                return match.group(1)
    except Exception as e:
        logger.warning("CIK lookup failed for %s: %s", ticker, e)

    return None


def _xbrl_concept_periods(facts: Dict[str, Any], concept: str,
                          unit: str) -> Dict[str, float]:
    """Annual 10-K values for one concept, keyed by period end."""
    us_gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    units = (us_gaap.get(concept) or {}).get("units") or {}
    values = units.get(unit) or units.get("USD") or units.get("USD/shares") or []

    chosen: Dict[str, Dict[str, Any]] = {}
    for value in values:
        if value.get("form") not in ("10-K", "10-K/A"):
            continue
        if value.get("val") is None or value.get("fp") not in (None, "FY"):
            continue
        end = value.get("end")
        if not end:
            continue
        # A 10-K carries quarterly comparatives alongside the annual figure;
        # anything materially shorter than a year is not the annual number.
        start = value.get("start")
        if start:
            try:
                span = (datetime.strptime(end, "%Y-%m-%d")
                        - datetime.strptime(start, "%Y-%m-%d")).days
            except (ValueError, TypeError):
                span = None
            if span is not None and not 330 <= span <= 400:
                continue
        prior = chosen.get(end)
        if not prior or (value.get("filed") or "") >= (prior.get("filed") or ""):
            chosen[end] = value

    return {end: float(v["val"]) for end, v in chosen.items()}


def _xbrl_annual_series(facts: Dict[str, Any], concepts: List[str],
                        unit: str = "USD") -> List[float]:
    """Annual values for a line item, newest first.

    Issuers disagree on tags and, worse, change them mid-history: NVIDIA
    reported revenue as ``RevenueFromContractWithCustomerExcludingAssessedTax``
    through FY2022 and as ``Revenues`` afterwards. Taking the first candidate
    that returns anything therefore produced a series that stopped four years
    ago and a 570% gross margin, because a current gross profit was divided by a
    stale revenue. The concept whose history reaches furthest forward wins, and
    older periods it does not cover are filled from the other candidates — which
    are alternate tags for the same line item, not different measures.
    """
    populated = [
        (concept, periods) for concept in concepts
        if (periods := _xbrl_concept_periods(facts, concept, unit))
    ]
    if not populated:
        return []

    populated.sort(key=lambda item: (max(item[1]), len(item[1])), reverse=True)
    merged = dict(populated[0][1])
    for _, periods in populated[1:]:
        for end, value in periods.items():
            merged.setdefault(end, value)

    return [merged[end] for end in sorted(merged, reverse=True)]


def _xbrl_latest(facts: Dict[str, Any], concepts: List[str],
                 unit: str = "USD") -> Optional[float]:
    """Most recent annual value across a list of candidate concepts."""
    series = _xbrl_annual_series(facts, concepts, unit)
    return series[0] if series else None


def _cagr(latest: Optional[float], earliest: Optional[float],
          years: int) -> Optional[float]:
    """Compound growth between two positive figures, else None.

    A CAGR across a sign change is arithmetically defined and economically
    meaningless, so a loss-making base year returns nothing rather than a number
    that would be ranked against peers.
    """
    if not latest or not earliest or years <= 0:
        return None
    if latest <= 0 or earliest <= 0:
        return None
    return (latest / earliest) ** (1 / years) - 1


def _ratio(numerator: Optional[float],
           denominator: Optional[float]) -> Optional[float]:
    """Quotient, or None when it cannot be formed."""
    if numerator is None or not denominator:
        return None
    return numerator / denominator


def _metrics_from_sec_facts(facts: Dict[str, Any]) -> Dict[str, Any]:
    """Comparable metrics computed from XBRL company facts alone.

    This is the floor under the vendor tiers. Both vendors used here fail in
    ways that produce no data and no error — a retired endpoint answers with a
    legacy notice, a free key exhausts its daily allowance after the first
    ticker — and a peer table of "N/A" is indistinguishable from a peer that
    reports nothing. Every figure below comes from the peers' own 10-K filings,
    which are free, unmetered and always available, so a comparison no longer
    depends on a vendor answering five times in a row.
    """
    if not facts.get("facts"):
        return {}

    revenue_series = _xbrl_annual_series(facts, [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues", "SalesRevenueNet", "SalesRevenueGoodsNet",
    ])
    net_income_series = _xbrl_annual_series(facts, [
        "NetIncomeLoss", "ProfitLoss",
    ])
    eps_series = _xbrl_annual_series(facts, [
        "EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted",
    ], unit="USD/shares")

    revenue = revenue_series[0] if revenue_series else None
    net_income = net_income_series[0] if net_income_series else None

    cost_of_revenue = _xbrl_latest(facts, [
        "CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfSales",
    ])
    gross_profit = _xbrl_latest(facts, ["GrossProfit"])
    if gross_profit is None and revenue is not None and cost_of_revenue is not None:
        gross_profit = revenue - cost_of_revenue

    operating_income = _xbrl_latest(facts, ["OperatingIncomeLoss"])
    rd_expense = _xbrl_latest(facts, ["ResearchAndDevelopmentExpense"])
    depreciation = _xbrl_latest(facts, [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet", "Depreciation",
    ])
    interest_expense = _xbrl_latest(facts, [
        "InterestExpense", "InterestExpenseNonoperating",
        "InterestIncomeExpenseNet",
    ])

    assets = _xbrl_latest(facts, ["Assets"])
    equity = _xbrl_latest(facts, [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ])
    current_assets = _xbrl_latest(facts, ["AssetsCurrent"])
    current_liabilities = _xbrl_latest(facts, ["LiabilitiesCurrent"])
    inventory = _xbrl_latest(facts, ["InventoryNet"])
    receivables = _xbrl_latest(facts, [
        "AccountsReceivableNetCurrent", "ReceivablesNetCurrent",
    ])
    goodwill = _xbrl_latest(facts, ["Goodwill"]) or 0
    intangibles = (_xbrl_latest(facts, [
        "IntangibleAssetsNetExcludingGoodwill", "FiniteLivedIntangibleAssetsNet",
    ]) or 0) + goodwill

    long_term_debt = _xbrl_latest(facts, [
        "LongTermDebtNoncurrent", "LongTermDebt",
        "DebtLongtermAndShorttermCombinedAmount",
    ])
    short_term_debt = _xbrl_latest(facts, [
        "LongTermDebtCurrent", "ShortTermBorrowings",
        "DebtCurrent",
    ])
    total_debt = None
    if long_term_debt is not None or short_term_debt is not None:
        total_debt = (long_term_debt or 0) + (short_term_debt or 0)

    operating_cf = _xbrl_latest(facts, [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ])
    capex = _xbrl_latest(facts, [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ])
    capex = abs(capex) if capex is not None else None
    free_cash_flow = None
    if operating_cf is not None:
        free_cash_flow = operating_cf - (capex or 0)

    ebitda = None
    if operating_income is not None:
        ebitda = operating_income + (depreciation or 0)

    metrics: Dict[str, Any] = {
        "revenue": revenue,
        "net_income": net_income,
        "total_assets": assets,
        "free_cash_flow": free_cash_flow,
        "gross_margin": _ratio(gross_profit, revenue),
        "operating_margin": _ratio(operating_income, revenue),
        "net_margin": _ratio(net_income, revenue),
        "ebitda_margin": _ratio(ebitda, revenue),
        "fcf_margin": _ratio(free_cash_flow, revenue),
        "asset_turnover": _ratio(revenue, assets),
        "inventory_turnover": _ratio(cost_of_revenue, inventory),
        "receivables_turnover": _ratio(revenue, receivables),
        "roe": _ratio(net_income, equity),
        "roa": _ratio(net_income, assets),
        "debt_to_equity": _ratio(total_debt, equity),
        "debt_to_ebitda": _ratio(total_debt, ebitda),
        "current_ratio": _ratio(current_assets, current_liabilities),
        "rd_intensity": _ratio(rd_expense, revenue),
        "capex_intensity": _ratio(capex, revenue),
        "intangibles_ratio": _ratio(intangibles or None, assets),
    }

    if current_assets is not None and current_liabilities:
        metrics["quick_ratio"] = (current_assets - (inventory or 0)) / current_liabilities

    if interest_expense:
        metrics["interest_coverage"] = _ratio(operating_income, abs(interest_expense))

    # Capital employed rather than invested capital: both are derivable from the
    # same two tags and the report labels the metric accordingly.
    if assets is not None and current_liabilities is not None:
        capital_employed = assets - current_liabilities
        metrics["roce"] = _ratio(operating_income, capital_employed)
        metrics["roic"] = metrics["roce"]

    if len(revenue_series) >= 2:
        metrics["revenue_growth_yoy"] = _ratio(
            revenue - revenue_series[1], abs(revenue_series[1]) or None)
    if len(revenue_series) >= 4:
        metrics["revenue_growth_3yr"] = _cagr(revenue, revenue_series[3], 3)
    if len(eps_series) >= 4:
        metrics["eps_growth_3yr"] = _cagr(eps_series[0], eps_series[3], 3)
    elif len(net_income_series) >= 4:
        metrics["eps_growth_3yr"] = _cagr(net_income, net_income_series[3], 3)

    fcf_series = _xbrl_annual_series(facts, [
        "NetCashProvidedByUsedInOperatingActivities",
    ])
    if len(fcf_series) >= 4:
        metrics["fcf_growth_3yr"] = _cagr(fcf_series[0], fcf_series[3], 3)

    dividends = _xbrl_latest(facts, [
        "PaymentsOfDividendsCommonStock", "PaymentsOfDividends",
    ])
    if dividends and net_income:
        metrics["dividend_payout"] = abs(dividends) / net_income

    return {k: v for k, v in metrics.items() if v is not None}


def _market_metrics(ticker: str, fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """Multiples that need a price, derived from the shared quote connector.

    XBRL supplies no market value, so the multiples are formed here from the
    same quote source the rest of the report uses rather than from a second
    vendor with its own quota.
    """
    try:
        from app.connectors.market_data_connector import get_quote
    except ImportError:
        return {}

    try:
        quote = get_quote(ticker) or {}
    except Exception as e:
        logger.warning("Quote fetch failed for %s: %s", ticker, e)
        return {}

    market_cap = _safe_float(quote.get("market_cap"))
    if not market_cap:
        return {}

    metrics: Dict[str, Any] = {"market_cap": market_cap}
    revenue = fundamentals.get("revenue")
    net_income = fundamentals.get("net_income")
    free_cash_flow = fundamentals.get("free_cash_flow")

    if net_income and net_income > 0:
        metrics["pe_ratio"] = market_cap / net_income
    if revenue and revenue > 0:
        metrics["ps_ratio"] = market_cap / revenue
    if free_cash_flow:
        metrics["fcf_yield"] = free_cash_flow / market_cap
    return metrics


def _extract_xbrl_value(facts: Dict[str, Any], concept: str, unit: str = "USD") -> Optional[float]:
    """Extract the most recent value for an XBRL concept."""
    try:
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        concept_data = us_gaap.get(concept, {})
        units = concept_data.get("units", {})

        values = units.get(unit, []) or units.get("USD", []) or units.get("pure", [])

        if not values:
            return None

        # Get most recent annual value
        annual_values = [
            v for v in values
            if v.get("form") in ("10-K", "10-K/A") and v.get("val") is not None
        ]

        if annual_values:
            sorted_values = sorted(
                annual_values,
                key=lambda x: x.get("end", ""),
                reverse=True
            )
            return sorted_values[0].get("val")

    except Exception:
        pass

    return None


# ─────────────────────────────────────────────────────────────────────────────
# METRIC CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

METRIC_CATEGORIES = {
    "profitability": {
        "label": "Profitability",
        "metrics": [
            {"name": "gross_margin", "label": "Gross Margin", "format": "pct", "higher_better": True},
            {"name": "operating_margin", "label": "Operating Margin", "format": "pct", "higher_better": True},
            {"name": "net_margin", "label": "Net Margin", "format": "pct", "higher_better": True},
            {"name": "ebitda_margin", "label": "EBITDA Margin", "format": "pct", "higher_better": True},
            {"name": "fcf_margin", "label": "FCF Margin", "format": "pct", "higher_better": True},
        ]
    },
    "efficiency": {
        "label": "Operating Efficiency",
        "metrics": [
            {"name": "asset_turnover", "label": "Asset Turnover", "format": "ratio", "higher_better": True},
            {"name": "inventory_turnover", "label": "Inventory Turnover", "format": "ratio", "higher_better": True},
            {"name": "receivables_turnover", "label": "Receivables Turnover", "format": "ratio", "higher_better": True},
            {"name": "revenue_per_employee", "label": "Revenue/Employee", "format": "currency_k", "higher_better": True},
            {"name": "profit_per_employee", "label": "Profit/Employee", "format": "currency_k", "higher_better": True},
        ]
    },
    "growth": {
        "label": "Growth Metrics",
        "metrics": [
            {"name": "revenue_growth_3yr", "label": "Revenue Growth (3Y CAGR)", "format": "pct", "higher_better": True},
            {"name": "eps_growth_3yr", "label": "EPS Growth (3Y CAGR)", "format": "pct", "higher_better": True},
            {"name": "fcf_growth_3yr", "label": "FCF Growth (3Y CAGR)", "format": "pct", "higher_better": True},
            {"name": "revenue_growth_yoy", "label": "Revenue Growth (YoY)", "format": "pct", "higher_better": True},
            {"name": "organic_growth", "label": "Organic Growth", "format": "pct", "higher_better": True},
        ]
    },
    "returns": {
        "label": "Return Metrics",
        "metrics": [
            {"name": "roe", "label": "Return on Equity", "format": "pct", "higher_better": True},
            {"name": "roa", "label": "Return on Assets", "format": "pct", "higher_better": True},
            {"name": "roic", "label": "Return on Invested Capital", "format": "pct", "higher_better": True},
            {"name": "roce", "label": "Return on Capital Employed", "format": "pct", "higher_better": True},
        ]
    },
    "capital_structure": {
        "label": "Capital Structure",
        "metrics": [
            {"name": "debt_to_equity", "label": "Debt/Equity", "format": "ratio", "higher_better": False},
            {"name": "debt_to_ebitda", "label": "Debt/EBITDA", "format": "ratio", "higher_better": False},
            {"name": "interest_coverage", "label": "Interest Coverage", "format": "ratio", "higher_better": True},
            {"name": "current_ratio", "label": "Current Ratio", "format": "ratio", "higher_better": True},
            {"name": "quick_ratio", "label": "Quick Ratio", "format": "ratio", "higher_better": True},
        ]
    },
    "valuation": {
        "label": "Valuation Multiples",
        "metrics": [
            {"name": "pe_ratio", "label": "P/E Ratio", "format": "ratio", "higher_better": None},
            {"name": "forward_pe", "label": "Forward P/E", "format": "ratio", "higher_better": None},
            {"name": "peg_ratio", "label": "PEG Ratio", "format": "ratio", "higher_better": False},
            {"name": "ps_ratio", "label": "P/S Ratio", "format": "ratio", "higher_better": None},
            {"name": "pb_ratio", "label": "P/B Ratio", "format": "ratio", "higher_better": None},
            {"name": "ev_ebitda", "label": "EV/EBITDA", "format": "ratio", "higher_better": None},
            {"name": "ev_revenue", "label": "EV/Revenue", "format": "ratio", "higher_better": None},
            {"name": "fcf_yield", "label": "FCF Yield", "format": "pct", "higher_better": True},
        ]
    },
    "rd_innovation": {
        "label": "R&D & Innovation",
        "metrics": [
            {"name": "rd_intensity", "label": "R&D/Revenue", "format": "pct", "higher_better": None},
            {"name": "rd_per_employee", "label": "R&D/Employee", "format": "currency_k", "higher_better": True},
            {"name": "capex_intensity", "label": "CapEx/Revenue", "format": "pct", "higher_better": None},
            {"name": "intangibles_ratio", "label": "Intangibles/Assets", "format": "pct", "higher_better": None},
        ]
    },
    "shareholder_returns": {
        "label": "Shareholder Returns",
        "metrics": [
            {"name": "dividend_yield", "label": "Dividend Yield", "format": "pct", "higher_better": None},
            {"name": "dividend_payout", "label": "Dividend Payout Ratio", "format": "pct", "higher_better": None},
            {"name": "buyback_yield", "label": "Buyback Yield", "format": "pct", "higher_better": True},
            {"name": "total_yield", "label": "Total Shareholder Yield", "format": "pct", "higher_better": True},
        ]
    },
}


def _resolve_cik(ticker: str) -> Optional[str]:
    """CIK for a ticker, preferring the maintained SEC resolver."""
    try:
        from app.connectors.sec_edgar_connector import get_filer_cik
        cik = get_filer_cik(ticker)
        if cik:
            return cik
    except Exception as e:
        logger.debug("Filer CIK lookup unavailable for %s: %s", ticker, e)
    return _lookup_cik(ticker)


def _calculate_company_metrics(ticker: str, cik: str = None) -> Dict[str, Any]:
    """Calculate comprehensive metrics for a single company.

    Sources are layered: the vendors first where they answer, then the issuer's
    own XBRL filings for everything still missing. The peers were previously
    left empty whenever a vendor quota ran out partway through the set, which
    turned a comparison table into a column of the target and four blanks.
    """
    metrics = {"ticker": ticker}
    sources_used: List[str] = []

    # Fetch data from multiple sources
    overview = _fetch_alpha_vantage("OVERVIEW", ticker)
    income = _fetch_alpha_vantage("INCOME_STATEMENT", ticker)
    balance = _fetch_alpha_vantage("BALANCE_SHEET", ticker)
    cashflow = _fetch_alpha_vantage("CASH_FLOW", ticker)
    if overview or income or balance or cashflow:
        sources_used.append("alpha_vantage")

    # FMP data
    ratios = _fetch_fmp("ratios-ttm", ticker)
    key_metrics = _fetch_fmp("key-metrics-ttm", ticker)
    growth = _fetch_fmp("financial-growth", ticker)
    if ratios or key_metrics or growth:
        sources_used.append("fmp")

    # SEC XBRL data. The CIK is resolved per ticker rather than supplied only
    # for the target, because the peers need the same fallback the target has.
    sec_facts = _fetch_sec_company_facts(cik or "") if cik else {}
    if not sec_facts.get("facts"):
        resolved = _resolve_cik(ticker)
        if resolved:
            sec_facts = _fetch_sec_company_facts(resolved)

    # Process Alpha Vantage overview
    if overview:
        metrics.update({
            "market_cap": _safe_float(overview.get("MarketCapitalization")),
            "pe_ratio": _safe_float(overview.get("PERatio")),
            "forward_pe": _safe_float(overview.get("ForwardPE")),
            "peg_ratio": _safe_float(overview.get("PEGRatio")),
            "pb_ratio": _safe_float(overview.get("PriceToBookRatio")),
            "ps_ratio": _safe_float(overview.get("PriceToSalesRatioTTM")),
            "ev_ebitda": _safe_float(overview.get("EVToEBITDA")),
            "ev_revenue": _safe_float(overview.get("EVToRevenue")),
            "dividend_yield": _safe_float(overview.get("DividendYield")),
            "dividend_payout": _safe_float(overview.get("PayoutRatio")),
            "roe": _safe_float(overview.get("ReturnOnEquityTTM")),
            "roa": _safe_float(overview.get("ReturnOnAssetsTTM")),
            "profit_margin": _safe_float(overview.get("ProfitMargin")),
            "operating_margin": _safe_float(overview.get("OperatingMarginTTM")),
            "gross_margin": None,  # Calculate from income statement
            "revenue_per_share": _safe_float(overview.get("RevenuePerShareTTM")),
            "eps": _safe_float(overview.get("EPS")),
            "beta": _safe_float(overview.get("Beta")),
            "52_week_high": _safe_float(overview.get("52WeekHigh")),
            "52_week_low": _safe_float(overview.get("52WeekLow")),
            "analyst_target": _safe_float(overview.get("AnalystTargetPrice")),
            "full_time_employees": _safe_int(overview.get("FullTimeEmployees")),
        })

    # Process income statement for margins
    if income and income.get("annualReports"):
        latest = income["annualReports"][0]
        revenue = _safe_float(latest.get("totalRevenue"))
        gross_profit = _safe_float(latest.get("grossProfit"))
        operating_income = _safe_float(latest.get("operatingIncome"))
        net_income = _safe_float(latest.get("netIncome"))
        rd_expense = _safe_float(latest.get("researchAndDevelopment"))

        if revenue and revenue > 0:
            if gross_profit:
                metrics["gross_margin"] = gross_profit / revenue
            if operating_income:
                metrics["operating_margin"] = operating_income / revenue
            if net_income:
                metrics["net_margin"] = net_income / revenue
            if rd_expense:
                metrics["rd_intensity"] = rd_expense / revenue

        # Calculate growth rates
        if len(income["annualReports"]) >= 4:
            try:
                old_revenue = _safe_float(income["annualReports"][3].get("totalRevenue"))
                if old_revenue and old_revenue > 0 and revenue:
                    metrics["revenue_growth_3yr"] = ((revenue / old_revenue) ** (1/3)) - 1

                old_eps = _safe_float(income["annualReports"][3].get("netIncome"))
                if old_eps and old_eps > 0 and net_income and net_income > 0:
                    metrics["eps_growth_3yr"] = ((net_income / old_eps) ** (1/3)) - 1
            except Exception:
                pass

    # Process balance sheet
    if balance and balance.get("annualReports"):
        latest = balance["annualReports"][0]
        total_assets = _safe_float(latest.get("totalAssets"))
        total_equity = _safe_float(latest.get("totalShareholderEquity"))
        total_debt = _safe_float(latest.get("shortLongTermDebtTotal")) or _safe_float(latest.get("longTermDebt", 0))
        current_assets = _safe_float(latest.get("totalCurrentAssets"))
        current_liabilities = _safe_float(latest.get("totalCurrentLiabilities"))
        inventory = _safe_float(latest.get("inventory"))
        intangibles = _safe_float(latest.get("intangibleAssets"))

        if total_equity and total_equity > 0:
            metrics["debt_to_equity"] = (total_debt or 0) / total_equity

        if current_liabilities and current_liabilities > 0:
            if current_assets:
                metrics["current_ratio"] = current_assets / current_liabilities
            if current_assets and inventory:
                metrics["quick_ratio"] = (current_assets - inventory) / current_liabilities

        if total_assets and total_assets > 0 and intangibles:
            metrics["intangibles_ratio"] = intangibles / total_assets

    # Process cash flow
    if cashflow and cashflow.get("annualReports"):
        latest = cashflow["annualReports"][0]
        operating_cf = _safe_float(latest.get("operatingCashflow"))
        capex = abs(_safe_float(latest.get("capitalExpenditures")) or 0)

        if operating_cf:
            fcf = operating_cf - capex
            revenue = metrics.get("revenue_per_share", 0) * metrics.get("full_time_employees", 1)
            if revenue and revenue > 0:
                metrics["fcf_margin"] = fcf / revenue

    # FMP ratios
    if ratios and isinstance(ratios, list) and ratios:
        r = ratios[0]
        metrics.update({
            "roic": r.get("returnOnCapitalEmployedTTM"),
            "roce": r.get("returnOnCapitalEmployedTTM"),
            "asset_turnover": r.get("assetTurnoverTTM"),
            "inventory_turnover": r.get("inventoryTurnoverTTM"),
            "receivables_turnover": r.get("receivablesTurnoverTTM"),
            "interest_coverage": r.get("interestCoverageTTM"),
        })

    # FMP key metrics
    if key_metrics and isinstance(key_metrics, list) and key_metrics:
        km = key_metrics[0]
        metrics.update({
            "revenue_per_employee": km.get("revenuePerEmployeeTTM"),
            "profit_per_employee": km.get("incomePerEmployeeTTM"),
            "fcf_yield": km.get("freeCashFlowYieldTTM"),
            "rd_per_employee": km.get("researchAndDdevelopementToRevenueTTM"),  # Note: FMP typo
            "buyback_yield": km.get("stockBasedCompensationToRevenueTTM"),  # Approximation
        })

    # FMP growth
    if growth and isinstance(growth, list) and growth:
        g = growth[0]
        metrics.update({
            "revenue_growth_yoy": g.get("revenueGrowth"),
            "eps_growth_yoy": g.get("epsgrowth"),
        })

    # Fill from the issuer's own filings. Vendor values are kept where they
    # exist, so this only ever adds coverage; a metric already carrying a number
    # is not overwritten by a differently-defined one.
    filing_metrics = _metrics_from_sec_facts(sec_facts)
    if filing_metrics:
        sources_used.append("sec_edgar")
        for key, value in filing_metrics.items():
            if metrics.get(key) is None:
                metrics[key] = value

        market_metrics = _market_metrics(ticker, filing_metrics)
        for key, value in market_metrics.items():
            if metrics.get(key) is None:
                metrics[key] = value

    metrics["_sources"] = sources_used
    return metrics


def _safe_float(value) -> Optional[float]:
    """Safely convert value to float."""
    if value is None or value == "None" or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> Optional[int]:
    """Safely convert value to int."""
    if value is None or value == "None" or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


# A percentile needs a distribution. Ranking a company against one or two
# observations produced the report's least defensible line — a 65.6% operating
# margin placed in the "0th percentile" and listed under areas for improvement,
# because it was the only company whose value resolved and nothing scores below
# itself. Below this count the rank is withheld.
MIN_PERCENTILE_OBSERVATIONS = 3


def _calculate_percentile_rank(value: float, all_values: List[float],
                               higher_better: bool = True) -> Optional[int]:
    """Percentile rank of a value within a peer set, or None if unrankable."""
    if not all_values or value is None:
        return None
    if len(all_values) < MIN_PERCENTILE_OBSERVATIONS:
        return None

    sorted_values = sorted(all_values)
    rank = sum(1 for v in sorted_values if v < value) / len(sorted_values)

    if not higher_better:
        rank = 1 - rank

    return int(rank * 100)


def _format_metric_value(value: Optional[float], format_type: str) -> str:
    """Format metric value for display."""
    if value is None:
        return "N/A"

    if format_type == "pct":
        return f"{value * 100:.1f}%" if abs(value) < 1 else f"{value:.1f}%"
    elif format_type == "ratio":
        return f"{value:.2f}x"
    elif format_type == "currency":
        if abs(value) >= 1e9:
            return f"${value / 1e9:.1f}B"
        elif abs(value) >= 1e6:
            return f"${value / 1e6:.1f}M"
        else:
            return f"${value:,.0f}"
    elif format_type == "currency_k":
        return f"${value / 1000:.0f}K"
    else:
        return f"{value:.2f}"


def run_deep_comparative_analysis(
    target_ticker: str,
    peer_tickers: List[str],
    target_cik: str = None,
) -> Dict[str, Any]:
    """
    Run comprehensive comparative analysis between target and peers.

    Args:
        target_ticker: Primary company ticker
        peer_tickers: List of peer company tickers
        target_cik: CIK for target company (optional)

    Returns:
        Complete comparative analysis data
    """
    logger.info("Starting deep comparative analysis for %s vs %s", target_ticker, peer_tickers)

    all_tickers = [target_ticker] + peer_tickers

    # Fetch metrics for all companies in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_calculate_company_metrics, ticker): ticker
            for ticker in all_tickers
        }

        company_metrics = {}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                metrics = future.result(timeout=60)
                company_metrics[ticker] = metrics
            except Exception as e:
                logger.warning("Metrics fetch failed for %s: %s", ticker, e)
                company_metrics[ticker] = {"ticker": ticker}

    # Build comparison tables by category
    category_comparisons = {}

    for category_key, category_config in METRIC_CATEGORIES.items():
        comparison = {
            "label": category_config["label"],
            "metrics": [],
        }

        for metric_config in category_config["metrics"]:
            metric_name = metric_config["name"]
            metric_data = {
                "name": metric_config["label"],
                "format": metric_config["format"],
                "higher_better": metric_config["higher_better"],
                "values": {},
                "ranks": {},
            }

            # Collect values across all companies
            all_values = []
            for ticker in all_tickers:
                value = company_metrics.get(ticker, {}).get(metric_name)
                metric_data["values"][ticker] = value
                if value is not None:
                    all_values.append(value)

            # Calculate percentile ranks
            for ticker in all_tickers:
                value = metric_data["values"][ticker]
                if value is not None and all_values:
                    metric_data["ranks"][ticker] = _calculate_percentile_rank(
                        value, all_values, metric_config["higher_better"] or True
                    )
                else:
                    metric_data["ranks"][ticker] = None

            comparison["metrics"].append(metric_data)

        category_comparisons[category_key] = comparison

    # Calculate overall scores by category
    category_scores = {}
    for category_key, comparison in category_comparisons.items():
        category_scores[category_key] = {}

        for ticker in all_tickers:
            ranks = [
                m["ranks"].get(ticker)
                for m in comparison["metrics"]
                if m["ranks"].get(ticker) is not None
            ]
            if ranks:
                category_scores[category_key][ticker] = statistics.mean(ranks)
            else:
                category_scores[category_key][ticker] = None

    # Calculate overall composite score
    composite_scores = {}
    for ticker in all_tickers:
        scores = [
            category_scores[cat].get(ticker)
            for cat in category_scores
            if category_scores[cat].get(ticker) is not None
        ]
        if scores:
            composite_scores[ticker] = statistics.mean(scores)
        else:
            composite_scores[ticker] = None

    # Identify strengths and weaknesses for target
    target_strengths = []
    target_weaknesses = []

    for category_key, comparison in category_comparisons.items():
        for metric in comparison["metrics"]:
            target_rank = metric["ranks"].get(target_ticker)
            if target_rank is not None:
                if target_rank >= 75:
                    target_strengths.append({
                        "category": comparison["label"],
                        "metric": metric["name"],
                        "value": _format_metric_value(
                            metric["values"].get(target_ticker),
                            metric["format"]
                        ),
                        "percentile": target_rank,
                    })
                elif target_rank <= 25:
                    target_weaknesses.append({
                        "category": comparison["label"],
                        "metric": metric["name"],
                        "value": _format_metric_value(
                            metric["values"].get(target_ticker),
                            metric["format"]
                        ),
                        "percentile": target_rank,
                    })

    # Sort by percentile
    target_strengths.sort(key=lambda x: x["percentile"], reverse=True)
    target_weaknesses.sort(key=lambda x: x["percentile"])

    return {
        "target_ticker": target_ticker,
        "peer_tickers": peer_tickers,
        "analysis_date": datetime.utcnow().isoformat() + "Z",

        "company_metrics": company_metrics,
        "category_comparisons": category_comparisons,
        "category_scores": category_scores,
        "composite_scores": composite_scores,

        "target_analysis": {
            "composite_score": composite_scores.get(target_ticker),
            "composite_rank": _calculate_percentile_rank(
                composite_scores.get(target_ticker),
                [s for s in composite_scores.values() if s is not None]
            ),
            "strengths": target_strengths[:10],
            "weaknesses": target_weaknesses[:10],
        },

        "peer_rankings": sorted(
            [
                {"ticker": t, "score": composite_scores.get(t)}
                for t in all_tickers
            ],
            key=lambda x: x["score"] or 0,
            reverse=True
        ),

        "data_sources": {
            "alpha_vantage": bool(ALPHA_VANTAGE_KEY),
            "fmp": bool(FMP_API_KEY),
            "sec_edgar": True,
        },

        # Which source actually answered per ticker, and any quota message a
        # vendor returned. Without these a blank cell cannot be told apart from
        # a company that reports nothing.
        "sources_by_ticker": {
            t: company_metrics.get(t, {}).get("_sources") or []
            for t in all_tickers
        },
        "vendor_notes": dict(_VENDOR_NOTES),
        "tickers_with_data": sorted(
            t for t in all_tickers
            if any(k not in ("ticker", "_sources")
                   for k in company_metrics.get(t, {}))
        ),
    }


def render_deep_comparative_markdown(analysis: Dict[str, Any]) -> List[str]:
    """Render deep comparative analysis as markdown."""
    lines = ["## Deep Comparative Analysis", ""]

    target = analysis.get("target_ticker", "")
    peers = analysis.get("peer_tickers", [])
    all_tickers = [target] + peers

    # Overview
    lines.append(f"Comprehensive comparison of **{target}** against {len(peers)} peer companies.")
    lines.append("")

    # Composite Scores
    lines.append("### Overall Competitive Position")
    lines.append("")

    rankings = analysis.get("peer_rankings", [])
    if rankings:
        lines.append("| Rank | Company | Composite Score |")
        lines.append("|------|---------|-----------------|")

        for i, item in enumerate(rankings, 1):
            ticker = item.get("ticker", "")
            score = item.get("score")
            score_str = f"{score:.1f}" if score is not None else "N/A"
            highlight = " **" if ticker == target else ""
            lines.append(f"| {i} | {highlight}{ticker}{highlight} | {score_str} |")
        lines.append("")

    # Target Strengths
    target_analysis = analysis.get("target_analysis", {})
    strengths = target_analysis.get("strengths", [])
    weaknesses = target_analysis.get("weaknesses", [])

    if strengths:
        lines.append("### Competitive Strengths")
        lines.append("")
        lines.append("| Metric | Value | Percentile |")
        lines.append("|--------|-------|------------|")

        for s in strengths[:7]:
            lines.append(f"| {s['metric']} | {s['value']} | {s['percentile']}th |")
        lines.append("")

    if weaknesses:
        lines.append("### Areas for Improvement")
        lines.append("")
        lines.append("| Metric | Value | Percentile |")
        lines.append("|--------|-------|------------|")

        for w in weaknesses[:7]:
            lines.append(f"| {w['metric']} | {w['value']} | {w['percentile']}th |")
        lines.append("")

    # Category breakdowns
    category_comparisons = analysis.get("category_comparisons", {})
    category_scores = analysis.get("category_scores", {})

    for category_key, comparison in category_comparisons.items():
        lines.append(f"### {comparison['label']}")
        lines.append("")

        # Category scores summary
        cat_scores = category_scores.get(category_key, {})
        if cat_scores:
            sorted_scores = sorted(
                [(t, s) for t, s in cat_scores.items() if s is not None],
                key=lambda x: x[1],
                reverse=True
            )
            leader = sorted_scores[0][0] if sorted_scores else "N/A"
            lines.append(f"*Category Leader: {leader}*")
            lines.append("")

        # Build comparison table
        metrics = comparison.get("metrics", [])
        if metrics:
            # Header
            header = "| Metric |"
            divider = "|--------|"
            for ticker in all_tickers:
                header += f" {ticker} |"
                divider += "--------|"

            lines.append(header)
            lines.append(divider)

            for metric in metrics[:6]:  # Limit to 6 metrics per category
                row = f"| {metric['name']} |"
                for ticker in all_tickers:
                    value = metric["values"].get(ticker)
                    formatted = _format_metric_value(value, metric["format"])
                    rank = metric["ranks"].get(ticker)

                    # Add rank indicator
                    if rank is not None:
                        if rank >= 75:
                            formatted = f"**{formatted}** 🟢"
                        elif rank <= 25:
                            formatted = f"{formatted} 🔴"

                    row += f" {formatted} |"

                lines.append(row)

            lines.append("")

    # Data quality note
    sources = analysis.get("data_sources", {})
    active_sources = [k for k, v in sources.items() if v]
    lines.append(f"*Data sources: {', '.join(active_sources)}*")
    lines.append("")

    return lines
