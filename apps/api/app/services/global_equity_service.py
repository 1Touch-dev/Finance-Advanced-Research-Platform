"""
Global Equity Coverage Service (#34)
International markets (EU, Asia, etc.) — powered by yfinance
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, time
from functools import lru_cache
import time as time_module

import yfinance as yf
import pytz


# ---------------------------------------------------------------------------
# Simple TTL cache
# ---------------------------------------------------------------------------

class TTLCache:
    def __init__(self, ttl_seconds: int):
        self._ttl = ttl_seconds
        self._store: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            if time_module.time() - self._timestamps[key] < self._ttl:
                return self._store[key]
            del self._store[key]
            del self._timestamps[key]
        return None

    def set(self, key: str, value: Any):
        self._store[key] = value
        self._timestamps[key] = time_module.time()


_quote_cache = TTLCache(ttl_seconds=300)       # 5 minutes
_static_cache = TTLCache(ttl_seconds=3600)     # 1 hour


# ---------------------------------------------------------------------------
# Market definitions
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


def _is_market_open(market_info: Dict) -> bool:
    """Determine if a market is currently open based on timezone and trading hours."""
    tz = pytz.timezone(market_info["timezone"])
    now = datetime.now(tz)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    current_time = now.time()
    return market_info["open"] <= current_time <= market_info["close"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_supported_markets() -> Dict[str, Any]:
    """Get list of supported global markets."""
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
    return result


def get_market_status() -> Dict[str, Any]:
    """Get real-time market status for all markets (timezone-derived)."""
    statuses = []
    for code, info in MARKETS.items():
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

    open_count = sum(1 for s in statuses if s["status"] == "open")
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "markets_open": open_count,
        "markets_closed": len(statuses) - open_count,
        "markets": statuses,
    }


def search_global_stocks(query: str, markets: List[str] = None) -> Dict[str, Any]:
    """Search for stocks across global markets using yfinance ticker lookup."""
    results = []

    tickers_to_try = [query]
    if markets:
        for m in markets:
            market_info = MARKETS.get(m.upper())
            if market_info and market_info["suffix"]:
                suffixed = query if query.endswith(market_info["suffix"]) else query + market_info["suffix"]
                tickers_to_try.append(suffixed)
    else:
        for info in MARKETS.values():
            if info["suffix"]:
                suffixed = query + info["suffix"]
                tickers_to_try.append(suffixed)

    seen = set()
    for ticker_str in tickers_to_try:
        if ticker_str in seen:
            continue
        seen.add(ticker_str)
        try:
            t = yf.Ticker(ticker_str)
            info = t.info
            if not info or info.get("regularMarketPrice") is None:
                continue
            results.append({
                "ticker": ticker_str,
                "name": info.get("shortName") or info.get("longName", ""),
                "exchange": info.get("exchange", ""),
                "market": info.get("market", ""),
                "currency": info.get("currency", ""),
                "type": info.get("quoteType", ""),
                "price": info.get("regularMarketPrice"),
            })
        except Exception:
            continue

    return {
        "status": "ok",
        "query": query,
        "result_count": len(results),
        "results": results,
    }


def get_global_quote(ticker: str) -> Dict[str, Any]:
    """Get quote for international stock via yfinance."""
    cached = _quote_cache.get(f"quote:{ticker}")
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or info.get("regularMarketPrice") is None:
            return {
                "status": "error",
                "ticker": ticker,
                "message": f"No data found for ticker '{ticker}'",
            }

        price = info.get("regularMarketPrice")
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        change = None
        change_pct = None
        if price is not None and prev_close:
            change = round(price - prev_close, 4)
            change_pct = round((change / prev_close) * 100, 4)

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
            "open": info.get("regularMarketOpen"),
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
        }
        _quote_cache.set(f"quote:{ticker}", result)
        return result

    except Exception as e:
        return {
            "status": "error",
            "ticker": ticker,
            "message": str(e),
        }


def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    """Convert between currencies using yfinance FX rates."""
    from_cur = from_currency.upper()
    to_cur = to_currency.upper()

    if from_cur == to_cur:
        return {
            "status": "ok",
            "from_currency": from_cur,
            "to_currency": to_cur,
            "amount": amount,
            "converted": amount,
            "rate": 1.0,
        }

    cache_key = f"fx:{from_cur}{to_cur}"
    cached_rate = _quote_cache.get(cache_key)

    if cached_rate is not None:
        rate = cached_rate
    else:
        try:
            pair = f"{from_cur}{to_cur}=X"
            t = yf.Ticker(pair)
            info = t.info
            rate = info.get("regularMarketPrice")
            if rate is None:
                hist = t.history(period="1d")
                if not hist.empty:
                    rate = float(hist["Close"].iloc[-1])
            if rate is None:
                return {
                    "status": "error",
                    "message": f"Unable to fetch FX rate for {from_cur}/{to_cur}",
                }
            _quote_cache.set(cache_key, rate)
        except Exception as e:
            return {
                "status": "error",
                "message": f"FX rate lookup failed: {e}",
            }

    converted = round(amount * rate, 4)
    return {
        "status": "ok",
        "from_currency": from_cur,
        "to_currency": to_cur,
        "amount": amount,
        "converted": converted,
        "rate": rate,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_adr_mappings(ticker: str) -> Dict[str, Any]:
    """Get ADR/GDR mappings for international stocks."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if not info or info.get("regularMarketPrice") is None:
            return {
                "status": "error",
                "ticker": ticker,
                "message": f"No data found for ticker '{ticker}'",
            }

        exchange = info.get("exchange", "")
        currency = info.get("currency", "")
        name = info.get("shortName") or info.get("longName", "")

        # Attempt to identify if this is an ADR or find its foreign counterpart
        quote_type = info.get("quoteType", "")
        is_adr = "ADR" in (info.get("shortName") or "") or "ADR" in (info.get("longName") or "")

        result = {
            "status": "ok",
            "ticker": ticker,
            "name": name,
            "exchange": exchange,
            "currency": currency,
            "quote_type": quote_type,
            "is_adr": is_adr,
            "country": info.get("country", ""),
            "sector": info.get("sector", ""),
        }
        return result

    except Exception as e:
        return {
            "status": "error",
            "ticker": ticker,
            "message": str(e),
        }


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


def get_global_indices() -> Dict[str, Any]:
    """Get major global indices via yfinance."""
    cached = _quote_cache.get("global_indices")
    if cached:
        return cached

    indices = []
    for symbol, name in GLOBAL_INDICES.items():
        try:
            t = yf.Ticker(symbol)
            info = t.info
            price = info.get("regularMarketPrice")
            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")

            change = None
            change_pct = None
            if price is not None and prev_close:
                change = round(price - prev_close, 2)
                change_pct = round((change / prev_close) * 100, 2)

            indices.append({
                "symbol": symbol,
                "name": name,
                "price": price,
                "change": change,
                "change_percent": change_pct,
                "currency": info.get("currency", ""),
            })
        except Exception:
            indices.append({
                "symbol": symbol,
                "name": name,
                "price": None,
                "change": None,
                "change_percent": None,
                "error": "Data unavailable",
            })

    result = {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "count": len(indices),
        "indices": indices,
    }
    _quote_cache.set("global_indices", result)
    return result
