"""
Global Equity Coverage Service (#34)
International markets (EU, Asia, etc.) - powered by yfinance

REAL DATA ONLY - No mock/simulated data.
Uses no_data_response when data is unavailable.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, time
import time as time_module
import logging

import yfinance as yf
import pytz

from app.core.no_data import no_data_response, NoDataReason

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TTL Cache Implementation
# ---------------------------------------------------------------------------

class TTLCache:
    """Simple in-memory cache with TTL expiration."""

    def __init__(self, ttl_seconds: int):
        self._ttl = ttl_seconds
        self._store: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            if time_module.time() - self._timestamps[key] < self._ttl:
                return self._store[key]
            # Expired - clean up
            del self._store[key]
            del self._timestamps[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value
        self._timestamps[key] = time_module.time()

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()
        self._timestamps.clear()

    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry."""
        self._store.pop(key, None)
        self._timestamps.pop(key, None)


# Cache instances with appropriate TTLs
_quote_cache = TTLCache(ttl_seconds=300)        # 5 minutes for quotes
_fx_cache = TTLCache(ttl_seconds=600)           # 10 minutes for FX rates
_static_cache = TTLCache(ttl_seconds=3600)      # 1 hour for static data
_indices_cache = TTLCache(ttl_seconds=300)      # 5 minutes for indices


# ---------------------------------------------------------------------------
# Market Definitions (Static Reference Data)
# ---------------------------------------------------------------------------

MARKETS = {
    "NYSE": {
        "name": "New York Stock Exchange",
        "country": "United States",
        "currency": "USD",
        "timezone": "America/New_York",
        "open": time(9, 30),
        "close": time(16, 0),
        "suffix": "",
        "example_tickers": ["AAPL", "MSFT", "JPM"],
    },
    "NASDAQ": {
        "name": "NASDAQ",
        "country": "United States",
        "currency": "USD",
        "timezone": "America/New_York",
        "open": time(9, 30),
        "close": time(16, 0),
        "suffix": "",
        "example_tickers": ["GOOGL", "AMZN", "TSLA"],
    },
    "LSE": {
        "name": "London Stock Exchange",
        "country": "United Kingdom",
        "currency": "GBP",
        "timezone": "Europe/London",
        "open": time(8, 0),
        "close": time(16, 30),
        "suffix": ".L",
        "example_tickers": ["SHEL.L", "HSBA.L", "BP.L"],
    },
    "XETRA": {
        "name": "XETRA (Frankfurt)",
        "country": "Germany",
        "currency": "EUR",
        "timezone": "Europe/Berlin",
        "open": time(9, 0),
        "close": time(17, 30),
        "suffix": ".DE",
        "example_tickers": ["SAP.DE", "SIE.DE", "BAS.DE"],
    },
    "EURONEXT_AMS": {
        "name": "Euronext Amsterdam",
        "country": "Netherlands",
        "currency": "EUR",
        "timezone": "Europe/Amsterdam",
        "open": time(9, 0),
        "close": time(17, 30),
        "suffix": ".AS",
        "example_tickers": ["ASML.AS", "PHIA.AS", "INGA.AS"],
    },
    "TSE": {
        "name": "Tokyo Stock Exchange",
        "country": "Japan",
        "currency": "JPY",
        "timezone": "Asia/Tokyo",
        "open": time(9, 0),
        "close": time(15, 0),
        "suffix": ".T",
        "example_tickers": ["7203.T", "6758.T", "9984.T"],
    },
    "HKEX": {
        "name": "Hong Kong Stock Exchange",
        "country": "Hong Kong",
        "currency": "HKD",
        "timezone": "Asia/Hong_Kong",
        "open": time(9, 30),
        "close": time(16, 0),
        "suffix": ".HK",
        "example_tickers": ["9988.HK", "0700.HK", "1299.HK"],
    },
    "NSE": {
        "name": "National Stock Exchange of India",
        "country": "India",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "open": time(9, 15),
        "close": time(15, 30),
        "suffix": ".NS",
        "example_tickers": ["RELIANCE.NS", "TCS.NS", "INFY.NS"],
    },
    "ASX": {
        "name": "Australian Securities Exchange",
        "country": "Australia",
        "currency": "AUD",
        "timezone": "Australia/Sydney",
        "open": time(10, 0),
        "close": time(16, 0),
        "suffix": ".AX",
        "example_tickers": ["BHP.AX", "CBA.AX", "CSL.AX"],
    },
    "TSX": {
        "name": "Toronto Stock Exchange",
        "country": "Canada",
        "currency": "CAD",
        "timezone": "America/Toronto",
        "open": time(9, 30),
        "close": time(16, 0),
        "suffix": ".TO",
        "example_tickers": ["RY.TO", "TD.TO", "SHOP.TO"],
    },
    "SSE": {
        "name": "Shanghai Stock Exchange",
        "country": "China",
        "currency": "CNY",
        "timezone": "Asia/Shanghai",
        "open": time(9, 30),
        "close": time(15, 0),
        "suffix": ".SS",
        "example_tickers": ["600519.SS", "601318.SS"],
    },
    "EURONEXT_PAR": {
        "name": "Euronext Paris",
        "country": "France",
        "currency": "EUR",
        "timezone": "Europe/Paris",
        "open": time(9, 0),
        "close": time(17, 30),
        "suffix": ".PA",
        "example_tickers": ["MC.PA", "OR.PA", "SAN.PA"],
    },
}

# Major Global Indices
GLOBAL_INDICES = {
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones Industrial Average",
    "^IXIC": "NASDAQ Composite",
    "^FTSE": "FTSE 100",
    "^GDAXI": "DAX",
    "^FCHI": "CAC 40",
    "^N225": "Nikkei 225",
    "^HSI": "Hang Seng Index",
    "000001.SS": "Shanghai Composite",
    "^NSEI": "Nifty 50",
    "^AXJO": "ASX 200",
    "^GSPTSE": "S&P/TSX Composite",
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _is_market_open(market_info: Dict) -> bool:
    """
    Determine if a market is currently open based on timezone and trading hours.
    Uses real timezone calculations - no simulation.
    """
    try:
        tz = pytz.timezone(market_info["timezone"])
        now = datetime.now(tz)
        # Weekend check
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        current_time = now.time()
        return market_info["open"] <= current_time <= market_info["close"]
    except Exception as e:
        log.warning(f"Error checking market hours: {e}")
        return False


def _fetch_yfinance_info(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch ticker info from yfinance with error handling.
    Returns None if data is unavailable.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        # Validate that we got real data
        if not info or not isinstance(info, dict):
            log.debug(f"No info dict returned for {ticker}")
            return None
        # Check for valid price data
        if info.get("regularMarketPrice") is None and info.get("previousClose") is None:
            log.debug(f"No price data available for {ticker}")
            return None
        return info
    except Exception as e:
        log.warning(f"yfinance fetch failed for {ticker}: {e}")
        return None


def _fetch_yfinance_history(ticker: str, period: str = "1d") -> Optional[Any]:
    """
    Fetch historical data from yfinance with error handling.
    Returns None if data is unavailable.
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period)
        if hist is None or hist.empty:
            return None
        return hist
    except Exception as e:
        log.warning(f"yfinance history fetch failed for {ticker}: {e}")
        return None


# ---------------------------------------------------------------------------
# Public API - Supported Markets
# ---------------------------------------------------------------------------

def get_supported_markets() -> Dict[str, Any]:
    """
    Get list of supported global markets.
    Returns static reference data about supported exchanges.
    """
    cached = _static_cache.get("supported_markets")
    if cached:
        return cached

    markets_list = []
    for code, info in MARKETS.items():
        markets_list.append({
            "code": code,
            "name": info["name"],
            "country": info["country"],
            "currency": info["currency"],
            "timezone": info["timezone"],
            "trading_hours": f"{info['open'].strftime('%H:%M')}-{info['close'].strftime('%H:%M')}",
            "suffix": info["suffix"],
            "example_tickers": info["example_tickers"],
        })

    result = {
        "status": "ok",
        "total_markets": len(markets_list),
        "markets": markets_list,
    }
    _static_cache.set("supported_markets", result)
    log.debug(f"Returned {len(markets_list)} supported markets")
    return result


# ---------------------------------------------------------------------------
# Public API - Market Status
# ---------------------------------------------------------------------------

def get_market_status() -> Dict[str, Any]:
    """
    Get real-time market status for all markets.
    Uses actual timezone calculations - no simulation or random values.
    """
    statuses = []
    for code, info in MARKETS.items():
        try:
            is_open = _is_market_open(info)
            tz = pytz.timezone(info["timezone"])
            local_now = datetime.now(tz)
            statuses.append({
                "code": code,
                "name": info["name"],
                "status": "open" if is_open else "closed",
                "local_time": local_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "trading_hours": f"{info['open'].strftime('%H:%M')}-{info['close'].strftime('%H:%M')}",
            })
        except Exception as e:
            log.warning(f"Error getting status for market {code}: {e}")
            statuses.append({
                "code": code,
                "name": info["name"],
                "status": "unknown",
                "error": str(e),
            })

    open_count = sum(1 for s in statuses if s.get("status") == "open")
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "markets_open": open_count,
        "markets_closed": len(statuses) - open_count,
        "markets": statuses,
    }


# ---------------------------------------------------------------------------
# Public API - Stock Search
# ---------------------------------------------------------------------------

def search_global_stocks(query: str, markets: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Search for stocks across global markets using yfinance.
    Supports any ticker - not limited to hardcoded list.

    Args:
        query: Ticker symbol or search term
        markets: Optional list of market codes to search in

    Returns:
        Search results with real price data from yfinance
    """
    results = []
    tickers_to_try = [query.upper()]

    # Build list of tickers to try with market suffixes
    if markets:
        for m in markets:
            market_info = MARKETS.get(m.upper())
            if market_info and market_info["suffix"]:
                suffixed = query.upper()
                if not suffixed.endswith(market_info["suffix"]):
                    suffixed = query.upper() + market_info["suffix"]
                tickers_to_try.append(suffixed)
    else:
        # Try all market suffixes
        for info in MARKETS.values():
            if info["suffix"]:
                suffixed = query.upper() + info["suffix"]
                tickers_to_try.append(suffixed)

    seen = set()
    for ticker_str in tickers_to_try:
        if ticker_str in seen:
            continue
        seen.add(ticker_str)

        info = _fetch_yfinance_info(ticker_str)
        if not info:
            continue

        price = info.get("regularMarketPrice")
        if price is None:
            continue

        results.append({
            "ticker": ticker_str,
            "name": info.get("shortName") or info.get("longName", ""),
            "exchange": info.get("exchange", ""),
            "market": info.get("market", ""),
            "currency": info.get("currency", ""),
            "type": info.get("quoteType", ""),
            "price": price,
        })
        log.debug(f"Found match: {ticker_str} @ {price}")

    if not results:
        log.info(f"No results found for query: {query}")

    return {
        "status": "ok",
        "query": query,
        "result_count": len(results),
        "results": results,
    }


# ---------------------------------------------------------------------------
# Public API - Get Quote (REAL DATA)
# ---------------------------------------------------------------------------

def get_global_quote(ticker: str) -> Dict[str, Any]:
    """
    Get real-time quote for any ticker via yfinance.

    REAL DATA ONLY:
    - Fetches live price data from yfinance
    - No random values, no hardcoded prices
    - Uses no_data_response when data is unavailable

    Args:
        ticker: Any valid ticker symbol (e.g., AAPL, SHEL.L, 7203.T)

    Returns:
        Quote data with real prices or no_data response
    """
    ticker = ticker.upper().strip()
    cache_key = f"quote:{ticker}"

    # Check cache first
    cached = _quote_cache.get(cache_key)
    if cached:
        log.debug(f"Cache hit for quote: {ticker}")
        return cached

    log.info(f"Fetching real quote for: {ticker}")

    # Fetch real data from yfinance
    info = _fetch_yfinance_info(ticker)

    if not info:
        log.warning(f"No data available for ticker: {ticker}")
        return no_data_response(
            entity=ticker,
            data_type="global_quote",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="yfinance",
            details=f"No market data found for ticker '{ticker}'"
        )

    # Extract price - try multiple fields
    price = info.get("regularMarketPrice")
    if price is None:
        price = info.get("currentPrice")
    if price is None:
        # Try to get from history as fallback
        hist = _fetch_yfinance_history(ticker, period="1d")
        if hist is not None and not hist.empty:
            price = float(hist["Close"].iloc[-1])

    if price is None:
        log.warning(f"Price data unavailable for: {ticker}")
        return no_data_response(
            entity=ticker,
            data_type="global_quote",
            reason=NoDataReason.API_UNAVAILABLE,
            source="yfinance",
            details="Price data not available"
        )

    # Calculate change from previous close
    prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
    change = None
    change_pct = None
    if price is not None and prev_close is not None and prev_close != 0:
        change = round(price - prev_close, 4)
        change_pct = round((change / prev_close) * 100, 4)

    # Build result with all available data
    result = {
        "status": "ok",
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName", ""),
        "exchange": info.get("exchange", ""),
        "currency": info.get("currency", ""),
        "price": price,
        "previous_close": prev_close,
        "change": change,
        "change_percent": change_pct,
        "open": info.get("regularMarketOpen") or info.get("open"),
        "day_high": info.get("regularMarketDayHigh") or info.get("dayHigh"),
        "day_low": info.get("regularMarketDayLow") or info.get("dayLow"),
        "volume": info.get("regularMarketVolume") or info.get("volume"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "dividend_yield": info.get("dividendYield"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data_source": "yfinance",
    }

    # Cache the result
    _quote_cache.set(cache_key, result)
    log.info(f"Quote fetched for {ticker}: ${price}")

    return result


# ---------------------------------------------------------------------------
# Public API - Currency Conversion (REAL FX RATES)
# ---------------------------------------------------------------------------

def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    """
    Convert between currencies using real-time FX rates from yfinance.

    REAL DATA ONLY:
    - Fetches live FX rates (e.g., EURUSD=X)
    - No hardcoded rates
    - Uses no_data_response when rates unavailable

    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., EUR, GBP)
        to_currency: Target currency code (e.g., USD, JPY)

    Returns:
        Conversion result with real rate or no_data response
    """
    from_cur = from_currency.upper().strip()
    to_cur = to_currency.upper().strip()

    # Same currency - no conversion needed
    if from_cur == to_cur:
        return {
            "status": "ok",
            "from_currency": from_cur,
            "to_currency": to_cur,
            "amount": amount,
            "converted": amount,
            "rate": 1.0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    cache_key = f"fx:{from_cur}{to_cur}"
    cached_rate = _fx_cache.get(cache_key)

    if cached_rate is not None:
        log.debug(f"Cache hit for FX rate: {from_cur}/{to_cur}")
        rate = cached_rate
    else:
        log.info(f"Fetching real FX rate: {from_cur}/{to_cur}")

        # yfinance FX pair format: EURUSD=X
        pair = f"{from_cur}{to_cur}=X"

        try:
            t = yf.Ticker(pair)
            info = t.info
            rate = info.get("regularMarketPrice")

            # Fallback to history if info doesn't have price
            if rate is None:
                hist = _fetch_yfinance_history(pair, period="1d")
                if hist is not None and not hist.empty:
                    rate = float(hist["Close"].iloc[-1])

            if rate is None:
                # Try inverse pair
                inverse_pair = f"{to_cur}{from_cur}=X"
                t_inv = yf.Ticker(inverse_pair)
                info_inv = t_inv.info
                inv_rate = info_inv.get("regularMarketPrice")
                if inv_rate is not None and inv_rate != 0:
                    rate = 1.0 / inv_rate
                    log.debug(f"Used inverse pair {inverse_pair}")

            if rate is None:
                log.warning(f"FX rate unavailable: {from_cur}/{to_cur}")
                return no_data_response(
                    entity=f"{from_cur}/{to_cur}",
                    data_type="fx_rate",
                    reason=NoDataReason.API_UNAVAILABLE,
                    source="yfinance",
                    details=f"Unable to fetch FX rate for {from_cur}/{to_cur}"
                )

            _fx_cache.set(cache_key, rate)
            log.info(f"FX rate fetched: {from_cur}/{to_cur} = {rate}")

        except Exception as e:
            log.error(f"FX rate lookup failed for {from_cur}/{to_cur}: {e}")
            return no_data_response(
                entity=f"{from_cur}/{to_cur}",
                data_type="fx_rate",
                reason=NoDataReason.API_ERROR,
                source="yfinance",
                details=str(e)
            )

    converted = round(amount * rate, 4)
    return {
        "status": "ok",
        "from_currency": from_cur,
        "to_currency": to_cur,
        "amount": amount,
        "converted": converted,
        "rate": rate,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data_source": "yfinance",
    }


# ---------------------------------------------------------------------------
# Public API - ADR Mappings
# ---------------------------------------------------------------------------

def get_adr_mappings(ticker: str) -> Dict[str, Any]:
    """
    Get ADR/GDR mappings and information for international stocks.

    Args:
        ticker: ADR or underlying stock ticker

    Returns:
        ADR information or no_data response
    """
    ticker = ticker.upper().strip()

    info = _fetch_yfinance_info(ticker)

    if not info:
        log.warning(f"No ADR info for: {ticker}")
        return no_data_response(
            entity=ticker,
            data_type="adr_mapping",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="yfinance",
            details=f"No data found for ticker '{ticker}'"
        )

    # Detect ADR status from name
    short_name = info.get("shortName") or ""
    long_name = info.get("longName") or ""
    is_adr = "ADR" in short_name.upper() or "ADR" in long_name.upper()

    return {
        "status": "ok",
        "ticker": ticker,
        "name": short_name or long_name,
        "exchange": info.get("exchange", ""),
        "currency": info.get("currency", ""),
        "quote_type": info.get("quoteType", ""),
        "is_adr": is_adr,
        "country": info.get("country", ""),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Public API - Global Indices (REAL DATA)
# ---------------------------------------------------------------------------

def get_global_indices() -> Dict[str, Any]:
    """
    Get real-time data for major global indices via yfinance.

    REAL DATA ONLY:
    - Fetches live index prices
    - No simulated data
    - Gracefully handles unavailable indices

    Returns:
        Index data with real prices
    """
    cache_key = "global_indices"
    cached = _indices_cache.get(cache_key)
    if cached:
        log.debug("Cache hit for global indices")
        return cached

    log.info("Fetching real global indices data")

    indices = []
    for symbol, name in GLOBAL_INDICES.items():
        try:
            t = yf.Ticker(symbol)
            info = t.info

            price = info.get("regularMarketPrice")
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")

            # Try history fallback if info doesn't have price
            if price is None:
                hist = _fetch_yfinance_history(symbol, period="1d")
                if hist is not None and not hist.empty:
                    price = float(hist["Close"].iloc[-1])

            change = None
            change_pct = None
            if price is not None and prev_close is not None and prev_close != 0:
                change = round(price - prev_close, 2)
                change_pct = round((change / prev_close) * 100, 2)

            indices.append({
                "symbol": symbol,
                "name": name,
                "price": price,
                "change": change,
                "change_percent": change_pct,
                "currency": info.get("currency", ""),
                "data_available": price is not None,
            })

            if price is not None:
                log.debug(f"Index {symbol}: {price}")

        except Exception as e:
            log.warning(f"Failed to fetch index {symbol}: {e}")
            indices.append({
                "symbol": symbol,
                "name": name,
                "price": None,
                "change": None,
                "change_percent": None,
                "data_available": False,
                "error": "Data unavailable",
            })

    available_count = sum(1 for i in indices if i.get("data_available"))
    log.info(f"Fetched {available_count}/{len(indices)} global indices")

    result = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "count": len(indices),
        "available": available_count,
        "indices": indices,
        "data_source": "yfinance",
    }

    _indices_cache.set(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Public API - Batch Quotes
# ---------------------------------------------------------------------------

def get_batch_quotes(tickers: List[str]) -> Dict[str, Any]:
    """
    Get quotes for multiple tickers efficiently.

    Args:
        tickers: List of ticker symbols

    Returns:
        Batch results with individual quote data
    """
    results = []
    successful = 0

    for ticker in tickers[:50]:  # Limit to 50 to avoid timeout
        quote = get_global_quote(ticker)
        results.append(quote)
        if quote.get("status") == "ok":
            successful += 1

    return {
        "status": "ok",
        "requested": len(tickers),
        "processed": len(results),
        "successful": successful,
        "quotes": results,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ---------------------------------------------------------------------------
# Cache Management
# ---------------------------------------------------------------------------

def clear_caches() -> Dict[str, str]:
    """Clear all caches - useful for testing or forcing fresh data."""
    _quote_cache.clear()
    _fx_cache.clear()
    _static_cache.clear()
    _indices_cache.clear()
    log.info("All caches cleared")
    return {"status": "ok", "message": "All caches cleared"}
