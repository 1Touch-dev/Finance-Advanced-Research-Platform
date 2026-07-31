"""
Deep Company Intelligence Connector
──────────────────────────────────────────────────────────────────────────────
Quarterly financial reports (10-K/10-Q), cap table, analyst ratings,
insider/big trades, and earnings history for publicly traded companies.
Free sources:
  - SEC EDGAR API (free, no key)
  - yfinance (already used elsewhere)
  - EDGAR XBRL for structured financial data
"""
import os
import re
import time
import logging
import requests
from typing import Optional
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

EDGAR_BASE = "https://data.sec.gov"
EDGAR_FULLTEXT = "https://efts.sec.gov/LATEST/search-index"
EDGAR_COMPANY_SEARCH = "https://efts.sec.gov/LATEST/search-index"
SEC_HEADERS = {"User-Agent": "Finance-Platform/1.0 abhishekk@kyma.world"}

# CIK lookup cache
_cik_cache = {}


def _get(url, params=None, timeout=15) -> dict:
    try:
        r = requests.get(url, params=params, headers=SEC_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Company deep fetch error %s: %s", url, e)
        return {}


def _get_text(url, timeout=15) -> str:
    try:
        r = requests.get(url, headers=SEC_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.warning("Text fetch error %s: %s", url, e)
        return ""


# ─── CIK Resolution ──────────────────────────────────────────────────────────

def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """
    Resolve company CIK from ticker symbol via SEC EDGAR.

    Delegates to the resolver in sec_edgar_connector, which caches the ticker
    map on disk. This module previously kept its own in-process cache and
    refetched the map every run; under SEC rate limiting that lookup failed and
    took valuation, institutional ownership and proxy data down with it, since
    all three resolve their CIK through here. One resolver and one cache means
    a throttled response cannot empty half the report.
    """
    ticker = ticker.upper().strip()
    if ticker in _cik_cache:
        return _cik_cache[ticker]

    from app.connectors.sec_edgar_connector import get_cik_from_ticker

    cik = get_cik_from_ticker(ticker)
    if cik:
        _cik_cache[ticker] = cik
    else:
        log.warning("Ticker %s could not be resolved to a CIK", ticker)
    return cik


def get_company_info(ticker: str) -> dict:
    """Get basic company info from SEC EDGAR."""
    cik = get_cik_for_ticker(ticker)
    if not cik:
        return {"ticker": ticker, "error": "CIK not found"}
    data = _get(f"{EDGAR_BASE}/submissions/CIK{cik}.json")
    if not data:
        return {"ticker": ticker, "cik": cik, "error": "EDGAR data unavailable"}
    return {
        "ticker": ticker,
        "cik": cik,
        "name": data.get("name"),
        "sic": data.get("sic"),
        "sic_description": data.get("sicDescription"),
        "state_of_incorporation": data.get("stateOfIncorporation"),
        "fiscal_year_end": data.get("fiscalYearEnd"),
        "business_phone": data.get("phone"),
        "website": data.get("website"),
        "city": data.get("addresses", {}).get("business", {}).get("city"),
        "state": data.get("addresses", {}).get("business", {}).get("stateOrCountry"),
    }


# ─── Filings: 10-K / 10-Q ────────────────────────────────────────────────────

def get_recent_filings(ticker: str, form_types: list = None, limit: int = 10) -> list:
    """Get recent SEC filings for a company."""
    cik = get_cik_for_ticker(ticker)
    if not cik:
        return []
    form_types = form_types or ["10-K", "10-Q", "8-K", "DEF 14A", "4"]
    data = _get(f"{EDGAR_BASE}/submissions/CIK{cik}.json")
    if not data:
        return []

    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    acc_nums = filings.get("accessionNumber", [])
    descriptions = filings.get("primaryDocument", [])
    doc_descriptions = filings.get("primaryDocDescription", [])

    results = []
    for form, date, acc, doc, desc in zip(forms, dates, acc_nums, descriptions, doc_descriptions):
        if form in form_types:
            acc_clean = acc.replace("-", "")
            results.append({
                "form_type": form,
                "filing_date": date,
                "accession_number": acc,
                "primary_doc": doc,
                "description": desc,
                "viewer_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}&dateb=&owner=include&count=5",
                "document_url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc}",
            })
            if len(results) >= limit:
                break

    return results


def get_quarterly_financials(ticker: str) -> dict:
    """
    Extract key financial metrics from SEC EDGAR XBRL data.
    Returns revenue, net income, EPS, etc. for recent quarters.
    """
    cik = get_cik_for_ticker(ticker)
    if not cik:
        return {"ticker": ticker, "error": "CIK not found"}

    # XBRL company facts
    facts = _get(f"{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json")
    if not facts:
        return {"ticker": ticker, "cik": cik, "error": "XBRL data unavailable"}

    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    def _extract_metric(concept: str, unit: str = "USD", label: str = None) -> list:
        data = us_gaap.get(concept, {}).get("units", {}).get(unit, [])
        # Filter for annual/quarterly filed data
        quarterly = [d for d in data if d.get("form") in ("10-K", "10-Q") and d.get("val") is not None]
        quarterly.sort(key=lambda x: x.get("end", ""), reverse=True)
        return [
            {
                "period_end": d.get("end"),
                "value": d.get("val"),
                "form": d.get("form"),
                "filed": d.get("filed"),
                "label": label or concept,
            }
            for d in quarterly[:8]
        ]

    revenue = (
        _extract_metric("RevenueFromContractWithCustomerExcludingAssessedTax", label="Revenue") or
        _extract_metric("Revenues", label="Revenue") or
        _extract_metric("SalesRevenueNet", label="Revenue")
    )
    net_income = _extract_metric("NetIncomeLoss", label="Net Income")
    eps_basic = _extract_metric("EarningsPerShareBasic", unit="USD/shares", label="EPS Basic")
    eps_diluted = _extract_metric("EarningsPerShareDiluted", unit="USD/shares", label="EPS Diluted")
    operating_income = _extract_metric("OperatingIncomeLoss", label="Operating Income")
    gross_profit = _extract_metric("GrossProfit", label="Gross Profit")
    research_dev = _extract_metric("ResearchAndDevelopmentExpense", label="R&D Expense")
    total_assets = _extract_metric("Assets", label="Total Assets")
    total_debt = _extract_metric("LongTermDebt", label="Long-term Debt")
    cash = (
        _extract_metric("CashAndCashEquivalentsAtCarryingValue", label="Cash") or
        _extract_metric("CashCashEquivalentsAndShortTermInvestments", label="Cash")
    )
    shares_outstanding = _extract_metric("CommonStockSharesOutstanding", unit="shares", label="Shares Outstanding")

    return {
        "ticker": ticker,
        "cik": cik,
        "revenue": revenue[:8],
        "net_income": net_income[:8],
        "eps_basic": eps_basic[:8],
        "eps_diluted": eps_diluted[:8],
        "operating_income": operating_income[:8],
        "gross_profit": gross_profit[:8],
        "research_development": research_dev[:8],
        "total_assets": total_assets[:8],
        "total_debt": total_debt[:8],
        "cash": cash[:8],
        "shares_outstanding": shares_outstanding[:4],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


# ─── Cap Table & Shareholders ─────────────────────────────────────────────────

def get_cap_table(ticker: str) -> dict:
    """
    Major shareholders (institutional, mutual fund, insider) via yfinance.
    Plus insider transactions from SEC EDGAR Form 4.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)

        # Institutional holders
        inst_df = stock.institutional_holders
        inst_list = []
        if inst_df is not None and not inst_df.empty:
            for _, row in inst_df.head(20).iterrows():
                import math
                def _sf(v):
                    try:
                        f = float(v or 0)
                        return 0.0 if math.isnan(f) or math.isinf(f) else f
                    except Exception:
                        return 0.0
                inst_list.append({
                    "holder": str(row.get("Holder", row.get("Name", ""))),
                    "shares": int(_sf(row.get("Shares", 0))),
                    "date_reported": str(row.get("Date Reported", "")),
                    "pct_held": round(_sf(row.get("% Out", row.get("pctHeld", 0))), 6),
                    "value_usd": int(_sf(row.get("Value", 0))),
                })

        # Mutual fund holders
        mf_df = stock.mutualfund_holders
        mf_list = []
        if mf_df is not None and not mf_df.empty:
            for _, row in mf_df.head(15).iterrows():
                import math
                def _sf2(v):
                    try:
                        f = float(v or 0)
                        return 0.0 if math.isnan(f) or math.isinf(f) else f
                    except Exception:
                        return 0.0
                mf_list.append({
                    "holder": str(row.get("Holder", row.get("Name", ""))),
                    "shares": int(_sf2(row.get("Shares", 0))),
                    "date_reported": str(row.get("Date Reported", "")),
                    "pct_held": round(_sf2(row.get("% Out", row.get("pctHeld", 0))), 6),
                    "value_usd": int(_sf2(row.get("Value", 0))),
                })

        # Major holders summary
        major_df = stock.major_holders
        major_list = []
        if major_df is not None and not major_df.empty:
            for _, row in major_df.iterrows():
                if len(row) >= 2:
                    major_list.append({"value": str(row.iloc[0]), "description": str(row.iloc[1])})
                elif len(row) == 1:
                    major_list.append({"value": str(row.iloc[0]), "description": ""})

        info = stock.info or {}
        shares_out = info.get("sharesOutstanding")
        float_shares = info.get("floatShares")
        insider_pct = info.get("heldPercentInsiders")
        inst_pct = info.get("heldPercentInstitutions")

        return {
            "ticker": ticker,
            "shares_outstanding": shares_out,
            "float_shares": float_shares,
            "insider_ownership_pct": insider_pct,
            "institutional_ownership_pct": inst_pct,
            "major_holders": major_list,
            "top_institutional_holders": inst_list,
            "top_mutual_fund_holders": mf_list,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    except Exception as e:
        log.error("Cap table error for %s: %s", ticker, e)
        return {"ticker": ticker, "error": str(e)}


# ─── Insider Trades / Big Trades ──────────────────────────────────────────────

def get_insider_trades(ticker: str, limit: int = 30) -> list:
    """Recent insider trades from SEC Form 4 via yfinance."""
    try:
        import yfinance as yf
        import math

        def _safe_num(v, default=0):
            try:
                f = float(v if v is not None else default)
                return default if math.isnan(f) or math.isinf(f) else f
            except Exception:
                return default

        stock = yf.Ticker(ticker)
        df = stock.insider_transactions
        if df is None or df.empty:
            return []
        trades = []
        for _, row in df.head(limit).iterrows():
            shares = _safe_num(row.get("Shares", row.get("shares", 0)))
            value = _safe_num(row.get("Value", row.get("value", 0)))
            trades.append({
                "insider": str(row.get("Insider", row.get("Name", ""))),
                "title": str(row.get("Title", row.get("title", ""))),
                "transaction": str(row.get("Transaction", row.get("transaction", ""))),
                "shares": int(shares),
                "value_usd": round(value, 2),
                "date": str(row.get("Start Date", row.get("Date", ""))),
                "ownership_type": str(row.get("Ownership", "Direct")),
            })
        return trades
    except Exception as e:
        log.error("Insider trades error for %s: %s", ticker, e)
        return []


def get_institutional_big_trades(ticker: str) -> dict:
    """
    Recent large institutional buy/sell activity inferred from
    13F quarterly position changes via yfinance institutional holders.
    """
    try:
        cap = get_cap_table(ticker)
        inst = cap.get("top_institutional_holders", [])
        mf = cap.get("top_mutual_fund_holders", [])

        # Flag significant positions
        big_positions = []
        for h in inst + mf:
            shares = h.get("shares", 0)
            value = h.get("value_usd", 0)
            if value >= 100_000_000:  # $100M+
                big_positions.append({
                    **h,
                    "significance": "MEGA" if value >= 1e9 else "LARGE",
                })

        total_inst_value = sum(h.get("value_usd", 0) for h in inst)
        return {
            "ticker": ticker,
            "significant_positions": sorted(big_positions, key=lambda x: x.get("value_usd", 0), reverse=True),
            "total_institutional_value_usd": total_inst_value,
            "institution_count": len(inst),
            "mutual_fund_count": len(mf),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ─── Analyst Ratings & Price Targets ─────────────────────────────────────────

def get_analyst_ratings(ticker: str) -> dict:
    """
    Current analyst consensus, price targets, and upgrade/downgrade history.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info or {}

        # Recommendation summary
        rec_mean = info.get("recommendationMean")
        rec_key = info.get("recommendationKey", "")
        target_mean = info.get("targetMeanPrice")
        target_high = info.get("targetHighPrice")
        target_low = info.get("targetLowPrice")
        target_median = info.get("targetMedianPrice")
        analyst_count = info.get("numberOfAnalystOpinions")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")

        upside = None
        if target_mean and current_price:
            upside = round((target_mean - current_price) / current_price * 100, 2)

        # Upgrade/downgrade history
        upgrades_df = stock.upgrades_downgrades
        recent_ratings = []
        if upgrades_df is not None and not upgrades_df.empty:
            upgrades_df = upgrades_df.reset_index()
            for _, row in upgrades_df.head(20).iterrows():
                recent_ratings.append({
                    "firm": str(row.get("Firm", "")),
                    "to_grade": str(row.get("ToGrade", "")),
                    "from_grade": str(row.get("FromGrade", "")),
                    "action": str(row.get("Action", "")),
                    "date": str(row.get("GradeDate", row.get("Date", ""))),
                })

        # Earnings estimates
        earnings_est = {}
        try:
            estimates = stock.earnings_estimate
            if estimates is not None and not estimates.empty:
                e = estimates.reset_index().to_dict(orient="records")
                earnings_est["earnings_estimate"] = e[:4]
        except Exception:
            pass

        return {
            "ticker": ticker,
            "recommendation": rec_key.upper() if rec_key else None,
            "recommendation_score": rec_mean,  # 1=Strong Buy, 5=Strong Sell
            "analyst_count": analyst_count,
            "price_target_mean": target_mean,
            "price_target_high": target_high,
            "price_target_low": target_low,
            "price_target_median": target_median,
            "current_price": current_price,
            "upside_potential_pct": upside,
            "recent_ratings": recent_ratings,
            "earnings_estimates": earnings_est,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    except Exception as e:
        log.error("Analyst ratings error for %s: %s", ticker, e)
        return {"ticker": ticker, "error": str(e)}


# ─── Earnings History ─────────────────────────────────────────────────────────

def get_earnings_history(ticker: str) -> dict:
    """Earnings history: actual vs estimate, EPS surprise, calendar."""
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)

        # Historical earnings
        earnings = {}
        try:
            df = stock.earnings_history
            if df is not None and not df.empty:
                df = df.reset_index()
                earnings["history"] = df.head(12).to_dict(orient="records")
        except Exception:
            pass

        # Calendar (next earnings)
        calendar = {}
        try:
            cal = stock.calendar
            if isinstance(cal, dict):
                calendar = {k: str(v) for k, v in cal.items()}
        except Exception:
            pass

        return {
            "ticker": ticker,
            "earnings_history": earnings.get("history", []),
            "calendar": calendar,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


# ─── Company News via RSS + News APIs ────────────────────────────────────────

def get_company_news(ticker: str, company_name: str = "", limit: int = 20) -> dict:
    """Aggregate company news from multiple sources."""
    try:
        from app.connectors.financial_news_connector import aggregate_news
        query = company_name or ticker
        result = aggregate_news(query, limit)
        return result if isinstance(result, dict) else {"articles": result or []}
    except Exception as e:
        log.error("Company news error: %s", e)
        return {"articles": [], "error": str(e)}


# ─── Full Deep Company Report ─────────────────────────────────────────────────

def deep_company_report(ticker: str, company_name: str = "") -> dict:
    """
    Comprehensive deep-dive report combining:
    - Company info (SEC EDGAR)
    - Recent filings list
    - Quarterly financials (XBRL)
    - Cap table / shareholders
    - Insider trades
    - Analyst ratings
    - Earnings history
    - Recent news
    """
    import json, math

    def _sanitize(obj):
        """Recursively replace NaN/Inf with None so JSON serialization won't fail."""
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_sanitize(i) for i in obj]
        return obj
    log.info("Building deep report for %s", ticker)
    from concurrent.futures import ThreadPoolExecutor, as_completed

    tasks = {
        "company_info": lambda: get_company_info(ticker),
        "recent_filings": lambda: get_recent_filings(ticker, ["10-K", "10-Q", "8-K"], limit=8),
        "quarterly_financials": lambda: get_quarterly_financials(ticker),
        "cap_table": lambda: get_cap_table(ticker),
        "insider_trades": lambda: get_insider_trades(ticker, limit=20),
        "analyst_ratings": lambda: get_analyst_ratings(ticker),
        "earnings_history": lambda: get_earnings_history(ticker),
        "news": lambda: get_company_news(ticker, company_name, limit=10),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        fut_map = {ex.submit(fn): name for name, fn in tasks.items()}
        for fut in as_completed(fut_map):
            name = fut_map[fut]
            try:
                results[name] = fut.result(timeout=30)
            except Exception as e:
                results[name] = {"error": str(e)}
                log.warning("Deep report task %s failed: %s", name, e)

    results["ticker"] = ticker
    results["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return _sanitize(results)
