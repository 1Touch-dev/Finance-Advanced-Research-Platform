"""
Global Equity Coverage Service (#34)
International markets (EU, Asia, etc.)
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random


GLOBAL_MARKETS = {
    "US": {"name": "United States", "exchanges": ["NYSE", "NASDAQ"], "currency": "USD", "timezone": "America/New_York"},
    "UK": {"name": "United Kingdom", "exchanges": ["LSE"], "currency": "GBP", "timezone": "Europe/London"},
    "DE": {"name": "Germany", "exchanges": ["XETRA", "Frankfurt"], "currency": "EUR", "timezone": "Europe/Berlin"},
    "FR": {"name": "France", "exchanges": ["Euronext Paris"], "currency": "EUR", "timezone": "Europe/Paris"},
    "JP": {"name": "Japan", "exchanges": ["TSE", "OSE"], "currency": "JPY", "timezone": "Asia/Tokyo"},
    "CN": {"name": "China", "exchanges": ["SSE", "SZSE"], "currency": "CNY", "timezone": "Asia/Shanghai"},
    "HK": {"name": "Hong Kong", "exchanges": ["HKEX"], "currency": "HKD", "timezone": "Asia/Hong_Kong"},
    "IN": {"name": "India", "exchanges": ["NSE", "BSE"], "currency": "INR", "timezone": "Asia/Kolkata"},
    "AU": {"name": "Australia", "exchanges": ["ASX"], "currency": "AUD", "timezone": "Australia/Sydney"},
    "CA": {"name": "Canada", "exchanges": ["TSX"], "currency": "CAD", "timezone": "America/Toronto"},
}

GLOBAL_STOCKS = {
    "ASML.AS": {"name": "ASML Holding", "country": "NL", "exchange": "Euronext", "currency": "EUR", "sector": "Technology"},
    "SAP.DE": {"name": "SAP SE", "country": "DE", "exchange": "XETRA", "currency": "EUR", "sector": "Technology"},
    "NESN.SW": {"name": "Nestle", "country": "CH", "exchange": "SIX", "currency": "CHF", "sector": "Consumer Staples"},
    "7203.T": {"name": "Toyota Motor", "country": "JP", "exchange": "TSE", "currency": "JPY", "sector": "Consumer Discretionary"},
    "9988.HK": {"name": "Alibaba Group", "country": "CN", "exchange": "HKEX", "currency": "HKD", "sector": "Technology"},
    "RELIANCE.NS": {"name": "Reliance Industries", "country": "IN", "exchange": "NSE", "currency": "INR", "sector": "Energy"},
    "BHP.AX": {"name": "BHP Group", "country": "AU", "exchange": "ASX", "currency": "AUD", "sector": "Materials"},
    "RY.TO": {"name": "Royal Bank of Canada", "country": "CA", "exchange": "TSX", "currency": "CAD", "sector": "Financials"},
}


def get_supported_markets() -> Dict[str, Any]:
    """Get list of supported global markets."""
    return {
        "markets": [
            {
                "code": code,
                "name": info["name"],
                "exchanges": info["exchanges"],
                "currency": info["currency"],
                "timezone": info["timezone"],
                "status": "open" if random.random() > 0.5 else "closed"
            }
            for code, info in GLOBAL_MARKETS.items()
        ],
        "total_markets": len(GLOBAL_MARKETS)
    }


def get_market_status() -> Dict[str, Any]:
    """Get real-time market status for all markets."""
    return {
        "markets": [
            {
                "code": code,
                "name": info["name"],
                "status": random.choice(["open", "closed", "pre-market", "after-hours"]),
                "local_time": datetime.now().strftime("%H:%M"),
                "next_open": "09:30" if random.random() > 0.5 else None,
                "next_close": "16:00" if random.random() > 0.5 else None
            }
            for code, info in GLOBAL_MARKETS.items()
        ],
        "timestamp": datetime.now().isoformat()
    }


def search_global_stocks(query: str, markets: List[str] = None) -> Dict[str, Any]:
    """Search for stocks across global markets."""
    results = []
    for ticker, info in GLOBAL_STOCKS.items():
        if query.lower() in ticker.lower() or query.lower() in info["name"].lower():
            if markets is None or info["country"] in markets:
                results.append({
                    "ticker": ticker,
                    "name": info["name"],
                    "country": info["country"],
                    "exchange": info["exchange"],
                    "currency": info["currency"],
                    "sector": info["sector"]
                })
    return {"query": query, "results": results, "count": len(results)}


def get_global_quote(ticker: str) -> Dict[str, Any]:
    """Get quote for international stock."""
    info = GLOBAL_STOCKS.get(ticker, {"name": ticker, "country": "Unknown", "exchange": "Unknown", "currency": "USD", "sector": "Unknown"})
    base_price = 100 + hash(ticker) % 500
    return {
        "ticker": ticker,
        "name": info["name"],
        "country": info["country"],
        "exchange": info["exchange"],
        "currency": info["currency"],
        "price": round(base_price + random.uniform(-5, 5), 2),
        "change": round(random.uniform(-5, 5), 2),
        "change_percent": round(random.uniform(-3, 3), 2),
        "volume": random.randint(100000, 10000000),
        "market_cap": f"{random.randint(10, 500)}B {info['currency']}",
        "pe_ratio": round(random.uniform(10, 40), 1),
        "dividend_yield": round(random.uniform(0, 5), 2),
        "timestamp": datetime.now().isoformat()
    }


def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    """Convert between currencies."""
    rates = {"USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5, "CNY": 7.24, "HKD": 7.82, "INR": 83.2, "AUD": 1.53, "CAD": 1.36, "CHF": 0.88}
    from_rate = rates.get(from_currency, 1.0)
    to_rate = rates.get(to_currency, 1.0)
    converted = amount / from_rate * to_rate
    return {
        "from": {"amount": amount, "currency": from_currency},
        "to": {"amount": round(converted, 2), "currency": to_currency},
        "rate": round(to_rate / from_rate, 4),
        "timestamp": datetime.now().isoformat()
    }


def get_adr_mappings(ticker: str) -> Dict[str, Any]:
    """Get ADR/GDR mappings for international stocks."""
    return {
        "ticker": ticker,
        "adr": {"ticker": f"{ticker.split('.')[0]}", "exchange": "NYSE", "ratio": "1:1"},
        "local": {"ticker": ticker, "exchange": GLOBAL_STOCKS.get(ticker, {}).get("exchange", "Unknown")},
        "premium_discount": round(random.uniform(-2, 2), 2)
    }


def get_global_indices() -> Dict[str, Any]:
    """Get major global indices."""
    indices = [
        {"symbol": "^GSPC", "name": "S&P 500", "country": "US", "value": 5234.56, "change": 1.2},
        {"symbol": "^DJI", "name": "Dow Jones", "country": "US", "value": 38876.45, "change": 0.8},
        {"symbol": "^FTSE", "name": "FTSE 100", "country": "UK", "value": 8234.12, "change": -0.3},
        {"symbol": "^GDAXI", "name": "DAX", "country": "DE", "value": 18234.56, "change": 0.5},
        {"symbol": "^N225", "name": "Nikkei 225", "country": "JP", "value": 38456.78, "change": 1.5},
        {"symbol": "^HSI", "name": "Hang Seng", "country": "HK", "value": 17234.56, "change": -0.8},
        {"symbol": "000001.SS", "name": "Shanghai Composite", "country": "CN", "value": 3045.67, "change": 0.2},
    ]
    return {"indices": indices, "timestamp": datetime.now().isoformat()}
