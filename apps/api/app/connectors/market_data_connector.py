"""
Market Data Connector
─────────────────────────────────────────────────────────────────────────────
Provider-independent market data with an explicit fallback chain, replacing the
hard dependency on yfinance (unavailable in this environment).

Chain:  Finnhub  →  FMP (stable API)  →  Alpha Vantage

Every returned value carries its source URL in the parallel ``sources`` map so
downstream report assembly can cite each figure. A field that could not be
retrieved is absent rather than zero — callers must not substitute estimates.
"""
import os
import time
import logging
import requests
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
FMP_KEY = os.getenv("FMP_API_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")

FINNHUB_BASE = "https://finnhub.io/api/v1"
FMP_BASE = "https://financialmodelingprep.com/stable"
ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"

_TIMEOUT = 12


def _get_json(url: str, params: Dict[str, Any], timeout: int = _TIMEOUT) -> Any:
    try:
        r = requests.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.warning("Market data fetch %s: %s", url, e)
        return None


def _num(val) -> Optional[float]:
    """Coerce to float, returning None for missing/unparseable/zero-as-missing."""
    if val is None or val == "":
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f if f != 0 else None


# ─── Provider: Finnhub ────────────────────────────────────────────────────────

def _finnhub_quote(ticker: str) -> Dict[str, Any]:
    """Finnhub /quote + /stock/profile2. Note: profile2 reports market cap and
    share count in MILLIONS; both are normalised to absolute units here."""
    if not FINNHUB_KEY:
        return {}

    out: Dict[str, Any] = {"sources": {}}
    q = _get_json(f"{FINNHUB_BASE}/quote", {"symbol": ticker, "token": FINNHUB_KEY})
    if isinstance(q, dict):
        quote_url = f"{FINNHUB_BASE}/quote?symbol={ticker}"
        for field, key in (("price", "c"), ("previous_close", "pc"),
                           ("day_high", "h"), ("day_low", "l"), ("open", "o")):
            v = _num(q.get(key))
            if v is not None:
                out[field] = v
                out["sources"][field] = quote_url

    p = _get_json(f"{FINNHUB_BASE}/stock/profile2", {"symbol": ticker, "token": FINNHUB_KEY})
    if isinstance(p, dict):
        profile_url = f"{FINNHUB_BASE}/stock/profile2?symbol={ticker}"
        mcap_millions = _num(p.get("marketCapitalization"))
        if mcap_millions is not None:
            out["market_cap"] = mcap_millions * 1_000_000
            out["sources"]["market_cap"] = profile_url
        shares_millions = _num(p.get("shareOutstanding"))
        if shares_millions is not None:
            out["shares_outstanding"] = shares_millions * 1_000_000
            out["sources"]["shares_outstanding"] = profile_url
        if p.get("name"):
            out["company_name"] = p["name"]
        if p.get("exchange"):
            out["exchange"] = p["exchange"]

    return out


def _finnhub_metrics(ticker: str) -> Dict[str, Any]:
    """Finnhub /stock/metric — beta, 52-week range, leverage, trailing multiples."""
    if not FINNHUB_KEY:
        return {}

    data = _get_json(f"{FINNHUB_BASE}/stock/metric",
                     {"symbol": ticker, "metric": "all", "token": FINNHUB_KEY})
    if not isinstance(data, dict):
        return {}
    m = data.get("metric") or {}
    url = f"{FINNHUB_BASE}/stock/metric?symbol={ticker}&metric=all"

    out: Dict[str, Any] = {"sources": {}}
    for field, key in (("beta", "beta"),
                       ("week_52_high", "52WeekHigh"),
                       ("week_52_low", "52WeekLow"),
                       ("pe_ttm", "peTTM"),
                       ("ps_ttm", "psTTM"),
                       ("debt_to_equity", "totalDebt/totalEquityQuarterly")):
        v = _num(m.get(key))
        if v is not None:
            out[field] = v
            out["sources"][field] = url
    return out


# ─── Provider: FMP (stable API) ───────────────────────────────────────────────

def _fmp_quote(ticker: str) -> Dict[str, Any]:
    """FMP /stable/quote. The legacy /api/v3 endpoints were retired Aug 2025."""
    if not FMP_KEY:
        return {}

    data = _get_json(f"{FMP_BASE}/quote", {"symbol": ticker, "apikey": FMP_KEY})
    if not isinstance(data, list) or not data:
        return {}
    q = data[0]
    url = f"{FMP_BASE}/quote?symbol={ticker}"

    out: Dict[str, Any] = {"sources": {}}
    for field, key in (("price", "price"), ("previous_close", "previousClose"),
                       ("day_high", "dayHigh"), ("day_low", "dayLow"),
                       ("open", "open"), ("market_cap", "marketCap"),
                       ("week_52_high", "yearHigh"), ("week_52_low", "yearLow"),
                       ("price_avg_50", "priceAvg50"), ("price_avg_200", "priceAvg200")):
        v = _num(q.get(key))
        if v is not None:
            out[field] = v
            out["sources"][field] = url
    if q.get("name"):
        out["company_name"] = q["name"]
    if q.get("exchange"):
        out["exchange"] = q["exchange"]
    return out


# ─── Provider: Alpha Vantage ──────────────────────────────────────────────────

def _alpha_vantage_quote(ticker: str) -> Dict[str, Any]:
    """Alpha Vantage GLOBAL_QUOTE — last resort; free tier is rate limited."""
    if not ALPHA_VANTAGE_KEY:
        return {}

    data = _get_json(ALPHA_VANTAGE_BASE,
                     {"function": "GLOBAL_QUOTE", "symbol": ticker,
                      "apikey": ALPHA_VANTAGE_KEY})
    if not isinstance(data, dict):
        return {}
    q = data.get("Global Quote") or {}
    if not q:
        return {}
    url = f"{ALPHA_VANTAGE_BASE}?function=GLOBAL_QUOTE&symbol={ticker}"

    out: Dict[str, Any] = {"sources": {}}
    for field, key in (("price", "05. price"), ("previous_close", "08. previous close"),
                       ("day_high", "03. high"), ("day_low", "04. low"),
                       ("open", "02. open")):
        v = _num(q.get(key))
        if v is not None:
            out[field] = v
            out["sources"][field] = url
    if q.get("07. latest trading day"):
        out["as_of_date"] = q["07. latest trading day"]
    return out


# ─── Public: quote with fallback ──────────────────────────────────────────────

def get_quote(ticker: str) -> Dict[str, Any]:
    """
    Price and market-cap snapshot, merged across providers in priority order.

    Later providers only fill fields the earlier ones failed to supply, so a
    single provider outage degrades coverage rather than the whole call.
    """
    merged: Dict[str, Any] = {"ticker": ticker, "sources": {}, "providers_used": []}

    for name, fetch in (("finnhub", _finnhub_quote),
                        ("fmp", _fmp_quote),
                        ("alpha_vantage", _alpha_vantage_quote)):
        try:
            data = fetch(ticker)
        except Exception as e:
            log.warning("Provider %s failed for %s: %s", name, ticker, e)
            continue
        if not data:
            continue

        sources = data.pop("sources", {})
        added = False
        for field, value in data.items():
            if field not in merged:
                merged[field] = value
                if field in sources:
                    merged["sources"][field] = sources[field]
                added = True
        if added:
            merged["providers_used"].append(name)

    # Metrics are additive rather than a fallback tier — only Finnhub supplies beta.
    try:
        metrics = _finnhub_metrics(ticker)
    except Exception as e:
        log.warning("Finnhub metrics failed for %s: %s", ticker, e)
        metrics = {}
    if metrics:
        sources = metrics.pop("sources", {})
        for field, value in metrics.items():
            if field not in merged:
                merged[field] = value
                if field in sources:
                    merged["sources"][field] = sources[field]
        if "finnhub" not in merged["providers_used"]:
            merged["providers_used"].append("finnhub")

    merged["retrieved_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return merged


# ─── Public: analyst consensus ────────────────────────────────────────────────

def get_analyst_consensus(ticker: str) -> Dict[str, Any]:
    """
    Sell-side price targets (FMP) and recommendation distribution (Finnhub).

    Supports the reference report's §2/§11 consensus-vs-model comparison.
    """
    out: Dict[str, Any] = {"ticker": ticker, "sources": {}}

    if FMP_KEY:
        data = _get_json(f"{FMP_BASE}/price-target-consensus",
                         {"symbol": ticker, "apikey": FMP_KEY})
        if isinstance(data, list) and data:
            c = data[0]
            url = f"{FMP_BASE}/price-target-consensus?symbol={ticker}"
            for field, key in (("target_high", "targetHigh"), ("target_low", "targetLow"),
                               ("target_consensus", "targetConsensus"),
                               ("target_median", "targetMedian")):
                v = _num(c.get(key))
                if v is not None:
                    out[field] = v
                    out["sources"][field] = url

    if FINNHUB_KEY:
        data = _get_json(f"{FINNHUB_BASE}/stock/recommendation",
                         {"symbol": ticker, "token": FINNHUB_KEY})
        if isinstance(data, list) and data:
            latest = data[0]
            url = f"{FINNHUB_BASE}/stock/recommendation?symbol={ticker}"
            buckets = {k: int(latest.get(k) or 0)
                       for k in ("strongBuy", "buy", "hold", "sell", "strongSell")}
            total = sum(buckets.values())
            if total:
                out["ratings"] = buckets
                out["ratings_total"] = total
                out["ratings_period"] = latest.get("period")
                out["bullish_pct"] = round(
                    (buckets["strongBuy"] + buckets["buy"]) / total * 100, 1)
                out["sources"]["ratings"] = url

    return out


def get_peers(ticker: str) -> Dict[str, Any]:
    """Peer set for the comparables table (§11 of the reference report)."""
    if not FINNHUB_KEY:
        return {"ticker": ticker, "peers": []}

    data = _get_json(f"{FINNHUB_BASE}/stock/peers", {"symbol": ticker, "token": FINNHUB_KEY})
    peers: List[str] = [p for p in data if p != ticker] if isinstance(data, list) else []
    return {
        "ticker": ticker,
        "peers": peers,
        "sources": {"peers": f"{FINNHUB_BASE}/stock/peers?symbol={ticker}"} if peers else {},
    }


def get_peer_comparables(ticker: str, limit: int = 8) -> Dict[str, Any]:
    """Peer market caps and trailing multiples — appendix sheet A5."""
    peer_list = get_peers(ticker).get("peers", [])[:limit]
    rows = []
    for peer in peer_list:
        quote = get_quote(peer)
        if quote.get("price") is None:
            continue
        rows.append({
            "ticker": peer,
            "company_name": quote.get("company_name"),
            "price": quote.get("price"),
            "market_cap": quote.get("market_cap"),
            "pe_ttm": quote.get("pe_ttm"),
            "ps_ttm": quote.get("ps_ttm"),
        })
    return {"ticker": ticker, "peers_analyzed": len(rows), "comparables": rows}


# ─── Public: combined snapshot ────────────────────────────────────────────────

def get_market_snapshot(ticker: str, include_peers: bool = False) -> Dict[str, Any]:
    """Everything the valuation and report layers need in one call."""
    snapshot = get_quote(ticker)
    snapshot["consensus"] = get_analyst_consensus(ticker)
    if include_peers:
        snapshot["comparables"] = get_peer_comparables(ticker)

    price = snapshot.get("price")
    high = snapshot.get("week_52_high")
    if price and high:
        snapshot["pct_below_52w_high"] = round((price - high) / high * 100, 2)

    snapshot["data_available"] = price is not None
    return snapshot


def provider_status() -> Dict[str, bool]:
    """Which providers are configured — surfaced in the report methodology section."""
    return {
        "finnhub": bool(FINNHUB_KEY),
        "fmp": bool(FMP_KEY),
        "alpha_vantage": bool(ALPHA_VANTAGE_KEY),
    }
