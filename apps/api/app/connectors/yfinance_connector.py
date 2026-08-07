"""
yfinance Connector — Phase 5th-July
=====================================
Wraps the yfinance library to expose:
  • OHLCV price history (daily / weekly / monthly)
  • Dividends & stock splits history
  • Options chain (nearest expiry)
  • Fast fundamentals (P/E, P/B, EV/EBITDA, revenue, margins, etc.)
  • Company info (sector, industry, employees, website, description)
  • Institutional holders & insider ownership summary

All functions return plain dicts / lists and degrade gracefully on error.
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)

def _import_yf():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        log.warning("yfinance not installed — run: pip install yfinance")
        return None


# ─── OHLCV Price History ─────────────────────────────────────────────────────

def yf_price_history(ticker: str, period: str = "1y", interval: str = "1d") -> list:
    """
    OHLCV bars for the given period/interval.
    period: 1d 5d 1mo 3mo 6mo 1y 2y 5y 10y ytd max
    interval: 1m 2m 5m 15m 30m 60m 90m 1h 1d 5d 1wk 1mo 3mo
    """
    yf = _import_yf()
    if not yf:
        return []
    try:
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        if hist.empty:
            return []
        rows = []
        for dt, row in hist.iterrows():
            rows.append({
                "date":   str(dt.date()) if hasattr(dt, "date") else str(dt)[:10],
                "open":   round(float(row.get("Open", 0)), 4),
                "high":   round(float(row.get("High", 0)), 4),
                "low":    round(float(row.get("Low", 0)), 4),
                "close":  round(float(row.get("Close", 0)), 4),
                "volume": int(row.get("Volume", 0)),
            })
        return rows
    except Exception as e:
        log.warning("yf_price_history error for %s: %s", ticker, e)
        return []


# ─── Dividends & Splits ──────────────────────────────────────────────────────

def yf_dividends(ticker: str) -> list:
    """Historical dividend payments."""
    yf = _import_yf()
    if not yf:
        return []
    try:
        divs = yf.Ticker(ticker).dividends
        if divs.empty:
            return []
        return [{"date": str(d.date()), "dividend": round(float(v), 6)}
                for d, v in divs.items()][-40:]
    except Exception as e:
        log.warning("yf_dividends error for %s: %s", ticker, e)
        return []


def yf_splits(ticker: str) -> list:
    """Historical stock splits."""
    yf = _import_yf()
    if not yf:
        return []
    try:
        splits = yf.Ticker(ticker).splits
        if splits.empty:
            return []
        return [{"date": str(d.date()), "ratio": float(v)}
                for d, v in splits.items()]
    except Exception as e:
        log.warning("yf_splits error for %s: %s", ticker, e)
        return []


# ─── Options Chain ───────────────────────────────────────────────────────────

def yf_options(ticker: str) -> dict:
    """Nearest-expiry options chain (calls + puts), top 10 strikes each."""
    yf = _import_yf()
    if not yf:
        return {"calls": [], "puts": [], "expiry": None}
    try:
        t = yf.Ticker(ticker)
        exps = t.options
        if not exps:
            return {"calls": [], "puts": [], "expiry": None}
        expiry = exps[0]
        chain = t.option_chain(expiry)

        def _fmt(df, n=10):
            rows = []
            for _, row in df.head(n).iterrows():
                rows.append({
                    "strike":            float(row.get("strike", 0)),
                    "lastPrice":         float(row.get("lastPrice", 0)),
                    "bid":               float(row.get("bid", 0)),
                    "ask":               float(row.get("ask", 0)),
                    "volume":            int(row.get("volume", 0) or 0),
                    "openInterest":      int(row.get("openInterest", 0) or 0),
                    "impliedVolatility": round(float(row.get("impliedVolatility", 0)), 4),
                    "inTheMoney":        bool(row.get("inTheMoney", False)),
                })
            return rows

        return {"calls": _fmt(chain.calls), "puts": _fmt(chain.puts), "expiry": expiry}
    except Exception as e:
        log.warning("yf_options error for %s: %s", ticker, e)
        return {"calls": [], "puts": [], "expiry": None}


# ─── Fundamentals ────────────────────────────────────────────────────────────

def yf_fundamentals(ticker: str) -> dict:
    """
    Fast fundamentals via yfinance info dict.
    Includes valuation ratios, margins, revenue, EPS, etc.
    """
    yf = _import_yf()
    if not yf:
        return {}
    try:
        info = yf.Ticker(ticker).info
        fields = [
            "currentPrice", "previousClose", "marketCap", "enterpriseValue",
            "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months",
            "enterpriseToRevenue", "enterpriseToEbitda",
            "trailingEps", "forwardEps",
            "totalRevenue", "grossProfits", "ebitda", "netIncomeToCommon",
            "profitMargins", "operatingMargins", "grossMargins",
            "returnOnEquity", "returnOnAssets",
            "totalDebt", "totalCash", "debtToEquity",
            "currentRatio", "quickRatio",
            "dividendYield", "dividendRate", "payoutRatio",
            "beta", "52WeekChange", "sharesOutstanding", "floatShares",
            "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
            "shortRatio", "shortPercentOfFloat",
            "heldPercentInsiders", "heldPercentInstitutions",
            "recommendationMean", "numberOfAnalystOpinions",
        ]
        result = {}
        for f in fields:
            v = info.get(f)
            if v is not None:
                try:
                    result[f] = round(float(v), 6) if isinstance(v, float) else v
                except (TypeError, ValueError):
                    result[f] = v
        result["source"] = "yfinance"
        return result
    except Exception as e:
        log.warning("yf_fundamentals error for %s: %s", ticker, e)
        return {}


# ─── Company Info ────────────────────────────────────────────────────────────

def yf_company_info(ticker: str) -> dict:
    """Company profile: name, sector, industry, employees, website, description."""
    yf = _import_yf()
    if not yf:
        return {}
    try:
        info = yf.Ticker(ticker).info
        return {
            "name":        info.get("longName") or info.get("shortName"),
            "sector":      info.get("sector"),
            "industry":    info.get("industry"),
            "country":     info.get("country"),
            "city":        info.get("city"),
            "employees":   info.get("fullTimeEmployees"),
            "website":     info.get("website"),
            "description": (info.get("longBusinessSummary") or "")[:1000],
            "exchange":    info.get("exchange"),
            "currency":    info.get("currency"),
            "source":      "yfinance",
        }
    except Exception as e:
        log.warning("yf_company_info error for %s: %s", ticker, e)
        return {}


# ─── Holders ────────────────────────────────────────────────────────────────

def yf_institutional_holders(ticker: str) -> list:
    """Top institutional holders."""
    yf = _import_yf()
    if not yf:
        return []
    try:
        df = yf.Ticker(ticker).institutional_holders
        if df is None or df.empty:
            return []
        rows = []
        for _, row in df.head(15).iterrows():
            rows.append({
                "holder":     str(row.get("Holder") or row.get("Name", "")),
                "shares":     int(row.get("Shares", 0) or 0),
                "value":      float(row.get("Value", 0) or 0),
                "pct_held":   round(float(row.get("% Out", 0) or 0), 4),
                "date_reported": str(row.get("Date Reported", "")),
            })
        return rows
    except Exception as e:
        log.warning("yf_institutional_holders error for %s: %s", ticker, e)
        return []


# ─── Comprehensive snapshot ──────────────────────────────────────────────────

def yf_snapshot(ticker: str) -> dict:
    """All yfinance data in one call: company, fundamentals, history, dividends."""
    return {
        "ticker":       ticker,
        "company":      yf_company_info(ticker),
        "fundamentals": yf_fundamentals(ticker),
        "price_history": yf_price_history(ticker, period="1y", interval="1d"),
        "dividends":    yf_dividends(ticker),
        "splits":       yf_splits(ticker),
        "source":       "yfinance",
    }
