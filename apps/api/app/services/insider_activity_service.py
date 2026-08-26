"""
Insider Activity Screener Service (Band C #41)
Screens Form 4 filings, clusters buys/sells

Data Source: SEC EDGAR Form 4 (FREE, real data via sec_edgar_connector)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import time
import hashlib

log = logging.getLogger(__name__)

from app.connectors.sec_edgar_connector import (
    get_insider_transactions as sec_get_insider_transactions,
    get_cik_from_ticker,
    get_company_submissions,
)

# ── In-memory cache with TTL ─────────────────────────────────────────────────
_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes


def _cache_key(*parts) -> str:
    return hashlib.md5(":".join(str(p) for p in parts).encode()).hexdigest()


def _get_cached(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < CACHE_TTL_SECONDS:
        return entry["data"]
    if entry:
        del _cache[key]
    return None


def _set_cached(key: str, data: Any) -> None:
    _cache[key] = {"data": data, "ts": time.time()}


# ── Dataclasses (preserved for API compatibility) ─────────────────────────────

@dataclass
class InsiderTransaction:
    """Insider transaction from Form 4"""
    transaction_id: str
    ticker: str
    company_name: str
    insider_name: str
    insider_title: str
    relationship: str
    transaction_type: str  # P (Purchase), S (Sale), A (Award), M (Exercise), G (Gift)
    transaction_date: str
    filing_date: str
    shares: int
    price: float
    value: float
    shares_owned_after: int
    ownership_change_percent: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "insider_name": self.insider_name,
            "insider_title": self.insider_title,
            "relationship": self.relationship,
            "transaction_type": self.transaction_type,
            "transaction_date": self.transaction_date,
            "filing_date": self.filing_date,
            "shares": self.shares,
            "price": self.price,
            "value": self.value,
            "shares_owned_after": self.shares_owned_after,
            "ownership_change_percent": self.ownership_change_percent,
        }


@dataclass
class InsiderCluster:
    """Cluster of insider activity for a ticker"""
    ticker: str
    company_name: str
    total_buys: int
    total_sells: int
    net_shares: int
    net_value: float
    buy_value: float
    sell_value: float
    insider_count: int
    latest_transaction: str
    signal: str  # strong_buy, buy, neutral, sell, strong_sell
    transactions: List[InsiderTransaction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "total_buys": self.total_buys,
            "total_sells": self.total_sells,
            "net_shares": self.net_shares,
            "net_value": self.net_value,
            "buy_value": self.buy_value,
            "sell_value": self.sell_value,
            "insider_count": self.insider_count,
            "latest_transaction": self.latest_transaction,
            "signal": self.signal,
            "transactions": [t.to_dict() for t in self.transactions],
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fetch_insider_data_for_ticker(ticker: str, days: int = 90) -> List[Dict[str, Any]]:
    """
    Fetch Form 4 transactions for a single ticker via SEC EDGAR.
    Returns normalized transaction dicts or empty list on failure.
    """
    cache_k = _cache_key("ticker_txns", ticker, days)
    cached = _get_cached(cache_k)
    if cached is not None:
        return cached

    cik = get_cik_from_ticker(ticker)
    if not cik:
        log.debug("Could not resolve CIK for ticker %s", ticker)
        _set_cached(cache_k, [])
        return []

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        result = sec_get_insider_transactions(
            cik,
            start_date=start_date,
            max_filings=100,
            max_elapsed_seconds=30,
        )
    except Exception as e:
        log.warning("SEC EDGAR insider fetch for %s failed: %s", ticker, e)
        _set_cached(cache_k, [])
        return []

    if result.get("error"):
        log.debug("SEC EDGAR error for %s: %s", ticker, result["error"])
        _set_cached(cache_k, [])
        return []

    # Get company name from submissions
    company_name = ""
    try:
        subs = get_company_submissions(cik, limit=1)
        company_name = subs.get("name", "")
    except Exception as e:
        log.debug("Failed to get company name for %s: %s", ticker, e)

    transactions = []
    for txn in result.get("transactions", []):
        code = txn.get("code", "")
        # Map acquired/disposed to P/S style code for API compatibility
        if code in ("P", "S"):
            txn_type = code
        elif txn.get("acquired_disposed") == "D":
            txn_type = "S"
        else:
            txn_type = code or "P"

        shares_after = int(txn.get("shares_owned_after", 0))
        shares = int(txn.get("shares", 0))
        ownership_change = 0.0
        if shares_after > 0 and shares > 0:
            if txn.get("acquired_disposed") == "D":
                ownership_change = round(-shares / (shares_after + shares) * 100, 2)
            else:
                ownership_change = round(shares / shares_after * 100, 2)

        roles = txn.get("roles", [])
        relationship = roles[0] if roles else txn.get("title", "")

        transactions.append({
            "transaction_id": txn.get("source_url", ""),
            "ticker": ticker,
            "company_name": company_name,
            "insider_name": txn.get("insider", ""),
            "insider_title": txn.get("title", ""),
            "relationship": relationship,
            "transaction_type": txn_type,
            "transaction_date": txn.get("date", ""),
            "filing_date": txn.get("filing_date", ""),
            "shares": shares,
            "price": float(txn.get("price", 0)),
            "value": float(txn.get("value", 0)),
            "shares_owned_after": shares_after,
            "ownership_change_percent": ownership_change,
            "open_market": txn.get("open_market", False),
            "is_10b5_1": txn.get("is_10b5_1", False),
            "code": code,
            "code_meaning": txn.get("code_meaning", ""),
            "source": "SEC EDGAR Form 4",
        })

    _set_cached(cache_k, transactions)
    return transactions


def _determine_signal(buy_count: int, sell_count: int,
                      buy_value: float, sell_value: float) -> str:
    """Determine insider sentiment signal from buy/sell counts and values."""
    if buy_count >= 3 and buy_value > sell_value * 2:
        return "strong_buy"
    elif buy_count >= 2 and buy_value > sell_value:
        return "buy"
    elif sell_count >= 3 and sell_value > buy_value * 2:
        return "strong_sell"
    elif sell_count >= 2 and sell_value > buy_value:
        return "sell"
    return "neutral"


# ── Public API (signatures preserved) ────────────────────────────────────────

def get_recent_transactions(
    days: int = 7,
    transaction_type: Optional[str] = None,
    min_value: float = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get recent insider transactions across the market.

    NOTE: SEC EDGAR does not offer a cross-market "latest Form 4" feed.
    This function queries a curated set of high-activity tickers.
    For comprehensive cross-market screening, an additional data source
    (e.g., SEC full-text search RSS feed) would be needed.
    """
    cache_k = _cache_key("recent_txns", days, transaction_type, min_value, limit)
    cached = _get_cached(cache_k)
    if cached is not None:
        return cached

    # Query a set of high-volume tickers for recent activity
    # SEC EDGAR doesn't have a single "all recent Form 4" endpoint,
    # so we sample from well-known large-caps
    sample_tickers = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
        "AMD", "INTC", "CRM", "NFLX", "JPM", "BAC", "GS",
    ]

    all_transactions = []
    for ticker in sample_tickers:
        txns = _fetch_insider_data_for_ticker(ticker, days=days)
        all_transactions.extend(txns)

    # Filter
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    filtered = []
    for txn in all_transactions:
        if txn.get("transaction_date", "") < cutoff:
            continue
        if transaction_type and txn.get("transaction_type") != transaction_type:
            continue
        if txn.get("value", 0) < min_value:
            continue
        filtered.append(txn)

    filtered.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
    result = filtered[:limit]
    _set_cached(cache_k, result)
    return result


def get_transactions_by_ticker(ticker: str, days: int = 90) -> List[Dict[str, Any]]:
    """Get all insider transactions for a specific ticker."""
    ticker = ticker.upper()
    transactions = _fetch_insider_data_for_ticker(ticker, days=days)
    transactions.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
    return transactions


def _normalize_sec_transaction(txn: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize SEC EDGAR transaction to our standard format."""
    return {
        "transaction_id": txn.get("accession") or txn.get("id") or "",
        "ticker": txn.get("ticker") or txn.get("symbol") or "",
        "company_name": txn.get("company") or txn.get("issuer") or "",
        "insider_name": txn.get("insider") or txn.get("owner_name") or "",
        "insider_title": txn.get("title") or txn.get("relationship") or "",
        "relationship": txn.get("relationship") or txn.get("title") or "",
        "transaction_type": txn.get("transaction_code") or txn.get("type") or "",
        "transaction_date": txn.get("transaction_date") or txn.get("date") or "",
        "filing_date": txn.get("filing_date") or txn.get("filed") or "",
        "shares": int(txn.get("shares") or txn.get("quantity") or 0),
        "price": float(txn.get("price") or txn.get("price_per_share") or 0),
        "value": float(txn.get("value") or txn.get("total_value") or 0),
        "shares_owned_after": int(txn.get("shares_owned") or txn.get("post_shares") or 0),
        "ownership_change_percent": float(txn.get("ownership_change") or 0),
        "source": "SEC EDGAR Form 4",
    }


def get_cluster_buys(days: int = 14, min_insiders: int = 2) -> List[Dict[str, Any]]:
    """Get stocks with cluster buying (multiple insiders buying).

    NOTE: True cross-market cluster detection requires scanning all Form 4
    filings from the SEC EDGAR full-text search RSS feed, which would need
    an additional scheduled ingestion pipeline. This implementation checks
    a sample of actively-traded tickers for cluster activity.
    """
    cache_k = _cache_key("cluster_buys", days, min_insiders)
    cached = _get_cached(cache_k)
    if cached is not None:
        return cached

    sample_tickers = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
        "AMD", "INTC", "CRM", "NFLX", "JPM", "BAC", "GS",
        "IONQ", "PLTR", "SOFI", "RKLB", "SNOW", "NET",
    ]

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    ticker_buys: Dict[str, Dict[str, Any]] = {}

    for ticker in sample_tickers:
        txns = _fetch_insider_data_for_ticker(ticker, days=days)
        for txn in txns:
            if txn.get("transaction_type") != "P":
                continue
            if not txn.get("open_market", False):
                continue
            if txn.get("transaction_date", "") < cutoff:
                continue

            if ticker not in ticker_buys:
                ticker_buys[ticker] = {
                    "ticker": ticker,
                    "company_name": txn.get("company_name", ""),
                    "insiders": set(),
                    "total_value": 0,
                    "total_shares": 0,
                    "transactions": [],
                }
            ticker_buys[ticker]["insiders"].add(txn.get("insider_name", ""))
            ticker_buys[ticker]["total_value"] += txn.get("value", 0)
            ticker_buys[ticker]["total_shares"] += txn.get("shares", 0)
            ticker_buys[ticker]["transactions"].append(txn)

    clusters = []
    for ticker, data in ticker_buys.items():
        if len(data["insiders"]) >= min_insiders:
            clusters.append({
                "ticker": data["ticker"],
                "company_name": data["company_name"],
                "insider_count": len(data["insiders"]),
                "total_value": data["total_value"],
                "total_shares": data["total_shares"],
                "transactions": data["transactions"],
            })

    clusters.sort(key=lambda x: x["insider_count"], reverse=True)
    _set_cached(cache_k, clusters)
    return clusters


def get_cluster_sells(days: int = 14, min_insiders: int = 2) -> List[Dict[str, Any]]:
    """Get stocks with cluster selling (multiple insiders selling).

    Same limitation as get_cluster_buys — scans a sample set of tickers.
    """
    cache_k = _cache_key("cluster_sells", days, min_insiders)
    cached = _get_cached(cache_k)
    if cached is not None:
        return cached

    sample_tickers = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
        "AMD", "INTC", "CRM", "NFLX", "JPM", "BAC", "GS",
        "IONQ", "PLTR", "SOFI", "RKLB", "SNOW", "NET",
    ]

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    ticker_sells: Dict[str, Dict[str, Any]] = {}

    for ticker in sample_tickers:
        txns = _fetch_insider_data_for_ticker(ticker, days=days)
        for txn in txns:
            if txn.get("transaction_type") != "S":
                continue
            if not txn.get("open_market", False):
                continue
            if txn.get("transaction_date", "") < cutoff:
                continue

            if ticker not in ticker_sells:
                ticker_sells[ticker] = {
                    "ticker": ticker,
                    "company_name": txn.get("company_name", ""),
                    "insiders": set(),
                    "total_value": 0,
                    "total_shares": 0,
                    "transactions": [],
                }
            ticker_sells[ticker]["insiders"].add(txn.get("insider_name", ""))
            ticker_sells[ticker]["total_value"] += txn.get("value", 0)
            ticker_sells[ticker]["total_shares"] += txn.get("shares", 0)
            ticker_sells[ticker]["transactions"].append(txn)

    clusters = []
    for ticker, data in ticker_sells.items():
        if len(data["insiders"]) >= min_insiders:
            clusters.append({
                "ticker": data["ticker"],
                "company_name": data["company_name"],
                "insider_count": len(data["insiders"]),
                "total_value": data["total_value"],
                "total_shares": data["total_shares"],
                "transactions": data["transactions"],
            })

    clusters.sort(key=lambda x: x["insider_count"], reverse=True)
    _set_cached(cache_k, clusters)
    return clusters


def get_largest_transactions(
    days: int = 30,
    transaction_type: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get largest insider transactions by value from sampled tickers."""
    cache_k = _cache_key("largest_txns", days, transaction_type, limit)
    cached = _get_cached(cache_k)
    if cached is not None:
        return cached

    sample_tickers = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
        "AMD", "INTC", "CRM", "NFLX", "JPM", "BAC", "GS",
    ]

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    transactions = []

    for ticker in sample_tickers:
        txns = _fetch_insider_data_for_ticker(ticker, days=days)
        for txn in txns:
            if txn.get("transaction_date", "") < cutoff:
                continue
            if transaction_type and txn.get("transaction_type") != transaction_type:
                continue
            transactions.append(txn)

    transactions.sort(key=lambda x: x.get("value", 0), reverse=True)
    result = transactions[:limit]
    _set_cached(cache_k, result)
    return result


def get_ceo_transactions(days: int = 30) -> List[Dict[str, Any]]:
    """Get CEO/CFO transactions from sampled tickers."""
    cache_k = _cache_key("ceo_txns", days)
    cached = _get_cached(cache_k)
    if cached is not None:
        return cached

    sample_tickers = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
        "AMD", "INTC", "CRM", "NFLX", "JPM", "BAC", "GS",
    ]

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    transactions = []

    for ticker in sample_tickers:
        txns = _fetch_insider_data_for_ticker(ticker, days=days)
        for txn in txns:
            if txn.get("transaction_date", "") < cutoff:
                continue
            title = (txn.get("insider_title") or "").upper()
            rel = (txn.get("relationship") or "").upper()
            if "CEO" in title or "CFO" in title or "CEO" in rel or "CFO" in rel or "CHIEF" in title:
                transactions.append(txn)

    transactions.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
    _set_cached(cache_k, transactions)
    return transactions


def get_insider_stats() -> Dict[str, Any]:
    """Get insider trading statistics from sampled tickers."""
    cache_k = _cache_key("insider_stats")
    cached = _get_cached(cache_k)
    if cached is not None:
        return cached

    sample_tickers = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
        "AMD", "INTC", "CRM", "NFLX", "JPM", "BAC", "GS",
    ]

    all_txns = []
    for ticker in sample_tickers:
        txns = _fetch_insider_data_for_ticker(ticker, days=30)
        all_txns.extend(txns)

    total_buys = len([t for t in all_txns if t.get("transaction_type") == "P"])
    total_sells = len([t for t in all_txns if t.get("transaction_type") == "S"])
    buy_value = sum(t.get("value", 0) for t in all_txns if t.get("transaction_type") == "P")
    sell_value = sum(t.get("value", 0) for t in all_txns if t.get("transaction_type") == "S")
    buy_tickers = set(t.get("ticker") for t in all_txns if t.get("transaction_type") == "P")
    sell_tickers = set(t.get("ticker") for t in all_txns if t.get("transaction_type") == "S")

    by_relationship: Dict[str, int] = {}
    for txn in all_txns:
        rel = txn.get("relationship", "Other") or "Other"
        by_relationship[rel] = by_relationship.get(rel, 0) + 1

    result = {
        "total_transactions": len(all_txns),
        "total_buys": total_buys,
        "total_sells": total_sells,
        "buy_value": buy_value,
        "sell_value": sell_value,
        "net_value": buy_value - sell_value,
        "buy_sell_ratio": round(total_buys / max(1, total_sells), 2),
        "tickers_with_buying": len(buy_tickers),
        "tickers_with_selling": len(sell_tickers),
        "by_relationship": by_relationship,
        "source": "SEC EDGAR Form 4",
        "tickers_sampled": len(sample_tickers),
    }
    _set_cached(cache_k, result)
    return result


def get_insider_sentiment(ticker: str, days: int = 90) -> Dict[str, Any]:
    """Get insider sentiment for a specific ticker using real Form 4 data."""
    ticker = ticker.upper()
    cache_k = _cache_key("sentiment", ticker, days)
    cached = _get_cached(cache_k)
    if cached is not None:
        return cached

    transactions = _fetch_insider_data_for_ticker(ticker, days=days)

    buys = [t for t in transactions if t.get("transaction_type") == "P" and t.get("open_market")]
    sells = [t for t in transactions if t.get("transaction_type") == "S" and t.get("open_market")]

    buy_value = sum(t.get("value", 0) for t in buys)
    sell_value = sum(t.get("value", 0) for t in sells)
    net_value = buy_value - sell_value

    signal = _determine_signal(len(buys), len(sells), buy_value, sell_value)

    result = {
        "ticker": ticker,
        "total_buys": len(buys),
        "total_sells": len(sells),
        "buy_value": buy_value,
        "sell_value": sell_value,
        "net_value": net_value,
        "signal": signal,
        "recent_buys": buys[:5],
        "recent_sells": sells[:5],
        "source": "SEC EDGAR Form 4",
    }
    _set_cached(cache_k, result)
    return result


def screen_insiders(
    min_buy_value: float = 100000,
    min_insiders: int = 1,
    days: int = 14,
    signal_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Screen stocks by insider activity using real SEC EDGAR data."""
    cache_k = _cache_key("screen", min_buy_value, min_insiders, days, signal_filter)
    cached = _get_cached(cache_k)
    if cached is not None:
        return cached

    sample_tickers = [
        "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
        "AMD", "INTC", "CRM", "NFLX", "JPM", "BAC", "GS",
        "IONQ", "PLTR", "SOFI", "RKLB", "SNOW", "NET",
    ]

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    ticker_data: Dict[str, Dict[str, Any]] = {}

    for ticker in sample_tickers:
        txns = _fetch_insider_data_for_ticker(ticker, days=days)
        for txn in txns:
            if txn.get("transaction_date", "") < cutoff:
                continue
            if not txn.get("open_market", False):
                continue

            if ticker not in ticker_data:
                ticker_data[ticker] = {
                    "ticker": ticker,
                    "company_name": txn.get("company_name", ""),
                    "buy_value": 0,
                    "sell_value": 0,
                    "buy_count": 0,
                    "sell_count": 0,
                    "insiders": set(),
                    "latest_date": txn.get("transaction_date", ""),
                }
            data = ticker_data[ticker]
            data["insiders"].add(txn.get("insider_name", ""))
            if txn.get("transaction_date", "") > data["latest_date"]:
                data["latest_date"] = txn.get("transaction_date", "")

            if txn.get("transaction_type") == "P":
                data["buy_value"] += txn.get("value", 0)
                data["buy_count"] += 1
            elif txn.get("transaction_type") == "S":
                data["sell_value"] += txn.get("value", 0)
                data["sell_count"] += 1

    results = []
    for ticker, data in ticker_data.items():
        insider_count = len(data["insiders"])
        if insider_count < min_insiders:
            continue

        buy_value = data["buy_value"]
        sell_value = data["sell_value"]
        net_value = buy_value - sell_value

        signal = _determine_signal(data["buy_count"], data["sell_count"], buy_value, sell_value)

        if signal_filter and signal != signal_filter:
            continue
        if buy_value < min_buy_value and signal in ["buy", "strong_buy"]:
            continue

        results.append({
            "ticker": data["ticker"],
            "company_name": data["company_name"],
            "buy_value": buy_value,
            "sell_value": sell_value,
            "net_value": net_value,
            "buy_count": data["buy_count"],
            "sell_count": data["sell_count"],
            "insider_count": insider_count,
            "signal": signal,
            "latest_transaction": data["latest_date"],
            "source": "SEC EDGAR Form 4",
        })

    results.sort(key=lambda x: x["net_value"], reverse=True)
    _set_cached(cache_k, results)
    return results
