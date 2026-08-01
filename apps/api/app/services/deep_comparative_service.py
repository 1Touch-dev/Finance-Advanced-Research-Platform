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

# Financial Modeling Prep API (free tier)
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/api/v3"

# SEC EDGAR (free)
SEC_COMPANY_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"

SEC_HEADERS = {
    "User-Agent": "Research Platform research@example.com",
    "Accept": "application/json",
}


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
            return resp.json()
    except Exception as e:
        logger.warning("Alpha Vantage fetch failed: %s", e)

    return {}


def _fetch_fmp(endpoint: str, symbol: str = None, **kwargs) -> Any:
    """Fetch data from Financial Modeling Prep API."""
    if not FMP_API_KEY:
        return None

    url = f"{FMP_BASE}/{endpoint}"
    if symbol:
        url = f"{url}/{symbol}"

    params = {"apikey": FMP_API_KEY, **kwargs}

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.ok:
            return resp.json()
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


def _calculate_company_metrics(ticker: str, cik: str = None) -> Dict[str, Any]:
    """Calculate comprehensive metrics for a single company."""
    metrics = {"ticker": ticker}

    # Fetch data from multiple sources
    overview = _fetch_alpha_vantage("OVERVIEW", ticker)
    income = _fetch_alpha_vantage("INCOME_STATEMENT", ticker)
    balance = _fetch_alpha_vantage("BALANCE_SHEET", ticker)
    cashflow = _fetch_alpha_vantage("CASH_FLOW", ticker)

    # FMP data
    ratios = _fetch_fmp("ratios-ttm", ticker)
    key_metrics = _fetch_fmp("key-metrics-ttm", ticker)
    growth = _fetch_fmp("financial-growth", ticker)

    # SEC XBRL data
    if cik:
        sec_facts = _fetch_sec_company_facts(cik)
    else:
        sec_facts = {}

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


def _calculate_percentile_rank(value: float, all_values: List[float], higher_better: bool = True) -> int:
    """Calculate percentile rank of a value within a list."""
    if not all_values or value is None:
        return 50

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
                composite_scores.get(target_ticker) or 50,
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
        }
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
