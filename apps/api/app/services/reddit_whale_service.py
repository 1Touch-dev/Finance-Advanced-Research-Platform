"""
Reddit & Whale Improvements Service (James J4)
Enhanced social sentiment and whale tracking

Uses yfinance for institutional/insider data.
Reddit sentiment requires Reddit API credentials (optional).
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

log = logging.getLogger(__name__)

# Cache for yfinance data
_cache: Dict[str, tuple] = {}
_CACHE_TTL = 1800  # 30 minutes


def _get_cached(key: str) -> Optional[Any]:
    """Get cached value if not expired."""
    if key in _cache:
        value, ts = _cache[key]
        if datetime.now().timestamp() - ts < _CACHE_TTL:
            return value
    return None


def _set_cached(key: str, value: Any):
    """Set cached value."""
    _cache[key] = (value, datetime.now().timestamp())


def get_reddit_sentiment(
    ticker: Optional[str] = None,
    subreddit: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get Reddit sentiment for ticker or subreddit.

    Note: Requires Reddit API credentials for real data.
    Returns stub data indicating the feature is available but needs config.
    """
    return {
        "ticker": ticker,
        "subreddit": subreddit or "wallstreetbets",
        "status": "api_key_required",
        "message": "Reddit API credentials not configured. Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET.",
        "sample_response": {
            "sentiment_score": 0.65,
            "mentions_24h": 150,
            "top_posts": [],
        },
    }


def get_reddit_trending(limit: int = 10) -> Dict[str, Any]:
    """Get trending tickers on Reddit."""
    return {
        "status": "api_key_required",
        "message": "Reddit API credentials not configured.",
        "trending": [],
    }


def get_subreddit_activity(subreddit: str) -> Dict[str, Any]:
    """Get activity metrics for a subreddit."""
    return {
        "subreddit": subreddit,
        "status": "api_key_required",
        "message": "Reddit API credentials not configured.",
    }


def get_sentiment_history(
    ticker: str,
    days: int = 30,
) -> Dict[str, Any]:
    """Get sentiment history over time."""
    return {
        "ticker": ticker,
        "days": days,
        "status": "api_key_required",
        "message": "Reddit API credentials not configured.",
        "history": [],
    }


def get_whale_transactions(
    ticker: Optional[str] = None,
    whale_type: Optional[str] = None,
    transaction_type: Optional[str] = None,
    min_value: float = 0,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get whale transactions with filters using yfinance insider data."""
    if not ticker:
        return {"transactions": [], "message": "Specify a ticker to see whale transactions"}

    cache_key = f"whale_tx:{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)

        # Get insider transactions
        insider_tx = stock.insider_transactions
        if insider_tx is None or insider_tx.empty:
            result = {"ticker": ticker, "transactions": [], "source": "yfinance"}
            _set_cached(cache_key, result)
            return result

        transactions = []
        for _, row in insider_tx.head(limit).iterrows():
            tx = {
                "insider": row.get("Insider") or row.get("insider", "Unknown"),
                "relation": row.get("Relationship") or row.get("relationship", ""),
                "transaction_type": row.get("Transaction") or row.get("transaction", ""),
                "shares": int(row.get("Shares") or row.get("shares", 0)),
                "value": float(row.get("Value") or row.get("value", 0)) if row.get("Value") or row.get("value") else None,
                "date": str(row.get("Start Date") or row.get("startDate", "")),
            }
            if min_value == 0 or (tx["value"] and tx["value"] >= min_value):
                transactions.append(tx)

        result = {
            "ticker": ticker,
            "transactions": transactions,
            "count": len(transactions),
            "source": "yfinance",
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        log.warning(f"Failed to fetch whale transactions for {ticker}: {e}")
        return {"ticker": ticker, "transactions": [], "error": str(e)}


def get_whale_flow(ticker: str, days: int = 30) -> Dict[str, Any]:
    """Get whale money flow over time using insider transaction data."""
    cache_key = f"whale_flow:{ticker}:{days}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)

        insider_tx = stock.insider_transactions
        if insider_tx is None or insider_tx.empty:
            return {"ticker": ticker, "days": days, "net_flow": 0, "transactions": 0}

        cutoff = datetime.now() - timedelta(days=days)

        buy_value = 0
        sell_value = 0
        buy_count = 0
        sell_count = 0

        for _, row in insider_tx.iterrows():
            tx_type = str(row.get("Transaction") or row.get("transaction", "")).lower()
            value = float(row.get("Value") or row.get("value", 0)) if row.get("Value") or row.get("value") else 0

            if "purchase" in tx_type or "buy" in tx_type:
                buy_value += value
                buy_count += 1
            elif "sale" in tx_type or "sell" in tx_type:
                sell_value += value
                sell_count += 1

        result = {
            "ticker": ticker,
            "days": days,
            "net_flow": buy_value - sell_value,
            "buy_volume": buy_value,
            "sell_volume": sell_value,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "sentiment": "bullish" if buy_value > sell_value else "bearish" if sell_value > buy_value else "neutral",
            "source": "yfinance",
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        log.warning(f"Failed to fetch whale flow for {ticker}: {e}")
        return {"ticker": ticker, "days": days, "error": str(e)}


def get_top_whales(
    ticker: Optional[str] = None,
    whale_type: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Get top whales by transaction volume using institutional holders data."""
    if not ticker:
        return {"whales": [], "message": "Specify a ticker to see top whales"}

    cache_key = f"top_whales:{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)

        holders = stock.institutional_holders
        if holders is None or holders.empty:
            return {"ticker": ticker, "whales": [], "source": "yfinance"}

        whales = []
        for _, row in holders.head(limit).iterrows():
            whale = {
                "name": row.get("Holder") or row.get("holder", "Unknown"),
                "shares": int(row.get("Shares") or row.get("shares", 0)),
                "value": float(row.get("Value") or row.get("value", 0)),
                "pct_held": float(row.get("% Out") or row.get("pctHeld", 0)),
                "date_reported": str(row.get("Date Reported") or row.get("dateReported", "")),
            }
            whales.append(whale)

        result = {
            "ticker": ticker,
            "whales": whales,
            "count": len(whales),
            "source": "yfinance",
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        log.warning(f"Failed to fetch top whales for {ticker}: {e}")
        return {"ticker": ticker, "whales": [], "error": str(e)}


def get_institutional_ownership(ticker: str) -> Dict[str, Any]:
    """Get institutional ownership breakdown using yfinance."""
    cache_key = f"inst_ownership:{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get institutional holders
        inst_holders = stock.institutional_holders
        mutual_holders = stock.mutualfund_holders

        inst_count = len(inst_holders) if inst_holders is not None and not inst_holders.empty else 0
        mutual_count = len(mutual_holders) if mutual_holders is not None and not mutual_holders.empty else 0

        result = {
            "ticker": ticker,
            "institutional_ownership_pct": info.get("heldPercentInstitutions", 0) * 100 if info.get("heldPercentInstitutions") else 0,
            "insider_ownership_pct": info.get("heldPercentInsiders", 0) * 100 if info.get("heldPercentInsiders") else 0,
            "institutional_holder_count": inst_count,
            "mutual_fund_holder_count": mutual_count,
            "float_shares": info.get("floatShares", 0),
            "shares_outstanding": info.get("sharesOutstanding", 0),
            "source": "yfinance",
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        log.warning(f"Failed to fetch institutional ownership for {ticker}: {e}")
        return {"ticker": ticker, "error": str(e)}


def get_insider_sentiment(ticker: str, days: int = 90) -> Dict[str, Any]:
    """Get insider buying/selling sentiment using yfinance."""
    cache_key = f"insider_sentiment:{ticker}:{days}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)

        insider_tx = stock.insider_transactions
        if insider_tx is None or insider_tx.empty:
            return {
                "ticker": ticker,
                "days": days,
                "sentiment": "neutral",
                "buy_count": 0,
                "sell_count": 0,
                "net_shares": 0,
            }

        buy_shares = 0
        sell_shares = 0
        buy_count = 0
        sell_count = 0

        for _, row in insider_tx.iterrows():
            tx_type = str(row.get("Transaction") or row.get("transaction", "")).lower()
            shares = int(row.get("Shares") or row.get("shares", 0))

            if "purchase" in tx_type or "buy" in tx_type:
                buy_shares += shares
                buy_count += 1
            elif "sale" in tx_type or "sell" in tx_type:
                sell_shares += shares
                sell_count += 1

        net_shares = buy_shares - sell_shares
        if net_shares > 0:
            sentiment = "bullish"
        elif net_shares < 0:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        result = {
            "ticker": ticker,
            "days": days,
            "sentiment": sentiment,
            "buy_count": buy_count,
            "sell_count": sell_count,
            "buy_shares": buy_shares,
            "sell_shares": sell_shares,
            "net_shares": net_shares,
            "source": "yfinance",
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        log.warning(f"Failed to fetch insider sentiment for {ticker}: {e}")
        return {"ticker": ticker, "days": days, "error": str(e)}


def get_social_momentum(ticker: str) -> Dict[str, Any]:
    """Get combined social momentum score.

    Combines insider sentiment with institutional ownership changes.
    Reddit sentiment requires API credentials.
    """
    cache_key = f"social_momentum:{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    try:
        # Get insider sentiment
        insider = get_insider_sentiment(ticker, days=30)

        # Get institutional ownership
        ownership = get_institutional_ownership(ticker)

        # Calculate momentum score (0-100)
        score = 50  # neutral baseline

        # Insider sentiment contribution (+/- 25 points)
        if insider.get("sentiment") == "bullish":
            score += 25
        elif insider.get("sentiment") == "bearish":
            score -= 25

        # Institutional ownership contribution (+/- 25 points)
        inst_pct = ownership.get("institutional_ownership_pct", 0)
        if inst_pct > 70:
            score += 25  # High institutional confidence
        elif inst_pct > 50:
            score += 15
        elif inst_pct < 20:
            score -= 15  # Low institutional interest

        result = {
            "ticker": ticker,
            "momentum_score": min(100, max(0, score)),
            "insider_sentiment": insider.get("sentiment", "neutral"),
            "institutional_ownership_pct": ownership.get("institutional_ownership_pct", 0),
            "reddit_sentiment": "api_key_required",
            "components": {
                "insider": insider,
                "institutional": ownership,
            },
            "source": "yfinance",
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        log.warning(f"Failed to calculate social momentum for {ticker}: {e}")
        return {"ticker": ticker, "error": str(e)}
