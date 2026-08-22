"""
Benchmark Attribution Service (Band C #44)
Compare portfolio vs S&P500, sector benchmarks using yfinance.
"""
import os
import time
import logging
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime

import yfinance as yf

log = logging.getLogger(__name__)

_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800  # 30 minutes

BENCHMARK_TICKERS = {
    "SPY": {"name": "S&P 500", "sector": "Large Cap"},
    "QQQ": {"name": "NASDAQ 100", "sector": "Tech/Growth"},
    "IWM": {"name": "Russell 2000", "sector": "Small Cap"},
    "DIA": {"name": "Dow Jones", "sector": "Blue Chip"},
    "VTI": {"name": "Total Market", "sector": "Broad Market"},
    "EFA": {"name": "International Developed", "sector": "International"},
    "EEM": {"name": "Emerging Markets", "sector": "International"},
    "TLT": {"name": "20+ Year Treasury", "sector": "Bonds"},
}

DEMO_PORTFOLIO = {
    "AAPL": 0.20,
    "MSFT": 0.15,
    "GOOGL": 0.15,
    "AMZN": 0.10,
    "NVDA": 0.10,
    "META": 0.10,
    "TSLA": 0.08,
    "JPM": 0.07,
    "JNJ": 0.05,
}


def _get_cached(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]
    return None


def _set_cache(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


def _compute_returns(prices):
    """Compute daily returns from price series."""
    if prices is None or len(prices) < 2:
        return np.array([])
    return np.diff(prices) / prices[:-1]


def get_benchmarks() -> List[Dict[str, Any]]:
    """Get all available benchmarks with current data."""
    cached = _get_cached("benchmarks_list")
    if cached is not None:
        return cached

    try:
        tickers_str = " ".join(BENCHMARK_TICKERS.keys())
        data = yf.download(tickers_str, period="5d", progress=False)
        if data.empty:
            return []

        results = []
        for ticker, info in BENCHMARK_TICKERS.items():
            try:
                if len(BENCHMARK_TICKERS) > 1 and "Close" in data.columns:
                    close_col = data["Close"][ticker] if ticker in data["Close"].columns else None
                else:
                    close_col = data["Close"]

                if close_col is None or close_col.dropna().empty:
                    continue

                last_price = float(close_col.dropna().iloc[-1])
                prev_price = float(close_col.dropna().iloc[-2]) if len(close_col.dropna()) > 1 else last_price
                change_pct = ((last_price - prev_price) / prev_price) * 100

                results.append({
                    "ticker": ticker,
                    "name": info["name"],
                    "sector": info["sector"],
                    "last_price": round(last_price, 2),
                    "daily_change_pct": round(change_pct, 2),
                })
            except Exception:
                continue

        _set_cache("benchmarks_list", results)
        return results
    except Exception as e:
        log.warning("Failed to fetch benchmarks: %s", e)
        return []


def get_benchmark(ticker: str) -> Optional[Dict[str, Any]]:
    """Get specific benchmark data."""
    cache_key = f"benchmark_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        data = yf.download(ticker, period="1y", progress=False)
        if data.empty:
            return {}

        close = data["Close"].dropna().values.flatten()
        if len(close) < 2:
            return {}

        returns = _compute_returns(close)
        total_return = (close[-1] / close[0] - 1) * 100
        annualized_vol = float(np.std(returns) * np.sqrt(252) * 100)
        sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252)) if np.std(returns) > 0 else 0

        result = {
            "ticker": ticker.upper(),
            "name": BENCHMARK_TICKERS.get(ticker.upper(), {}).get("name", ticker),
            "period": "1Y",
            "total_return_pct": round(total_return, 2),
            "annualized_volatility_pct": round(annualized_vol, 2),
            "sharpe_ratio": round(sharpe, 3),
            "max_drawdown_pct": round(_max_drawdown(close), 2),
            "last_price": round(float(close[-1]), 2),
            "source": "yfinance",
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.warning("Failed to fetch benchmark %s: %s", ticker, e)
        return {}


def _max_drawdown(prices) -> float:
    """Compute max drawdown percentage."""
    peak = prices[0]
    max_dd = 0
    for p in prices:
        if p > peak:
            peak = p
        dd = (peak - p) / peak * 100
        if dd > max_dd:
            max_dd = dd
    return max_dd


def get_portfolio_vs_benchmark(
    user_id: str,
    benchmark_ticker: str = "SPY",
) -> Dict[str, Any]:
    """Compare portfolio performance against a benchmark."""
    cache_key = f"pvb_{user_id}_{benchmark_ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    portfolio = DEMO_PORTFOLIO
    all_tickers = list(portfolio.keys()) + [benchmark_ticker]

    try:
        data = yf.download(all_tickers, period="1y", progress=False)
        if data.empty:
            return {"ticker": benchmark_ticker, "error": "No data available"}

        close = data["Close"].dropna()
        if close.empty:
            return {"ticker": benchmark_ticker, "error": "No price data"}

        # Portfolio weighted return
        port_returns_daily = None
        for ticker, weight in portfolio.items():
            if ticker not in close.columns:
                continue
            t_prices = close[ticker].dropna().values
            if len(t_prices) < 2:
                continue
            t_rets = _compute_returns(t_prices)
            if port_returns_daily is None:
                port_returns_daily = np.zeros(len(t_rets))
            min_len = min(len(port_returns_daily), len(t_rets))
            port_returns_daily[:min_len] += t_rets[:min_len] * weight

        if port_returns_daily is None or len(port_returns_daily) == 0:
            return {"ticker": benchmark_ticker, "error": "Insufficient portfolio data"}

        # Benchmark returns
        if benchmark_ticker in close.columns:
            bm_prices = close[benchmark_ticker].dropna().values
        else:
            bm_prices = np.array([])

        if len(bm_prices) < 2:
            return {"ticker": benchmark_ticker, "error": "No benchmark data"}

        bm_returns = _compute_returns(bm_prices)
        min_len = min(len(port_returns_daily), len(bm_returns))
        port_returns_daily = port_returns_daily[:min_len]
        bm_returns = bm_returns[:min_len]

        # Calculations
        port_total = float(np.prod(1 + port_returns_daily) - 1) * 100
        bm_total = float(np.prod(1 + bm_returns) - 1) * 100
        alpha = port_total - bm_total

        port_vol = float(np.std(port_returns_daily) * np.sqrt(252) * 100)
        bm_vol = float(np.std(bm_returns) * np.sqrt(252) * 100)

        # Tracking error
        tracking_diff = port_returns_daily - bm_returns
        tracking_error = float(np.std(tracking_diff) * np.sqrt(252) * 100)

        # Beta
        cov = np.cov(port_returns_daily, bm_returns)
        beta = float(cov[0, 1] / cov[1, 1]) if cov[1, 1] != 0 else 1.0

        # Sharpe
        port_sharpe = float(np.mean(port_returns_daily) / np.std(port_returns_daily) * np.sqrt(252)) if np.std(port_returns_daily) > 0 else 0
        bm_sharpe = float(np.mean(bm_returns) / np.std(bm_returns) * np.sqrt(252)) if np.std(bm_returns) > 0 else 0

        # Information ratio
        info_ratio = float(np.mean(tracking_diff) / np.std(tracking_diff) * np.sqrt(252)) if np.std(tracking_diff) > 0 else 0

        result = {
            "user_id": user_id,
            "benchmark": benchmark_ticker.upper(),
            "period": "1Y",
            "summary": {
                "portfolio_return_1y": round(port_total, 2),
                "benchmark_return_1y": round(bm_total, 2),
                "total_alpha_1y": round(alpha, 2),
                "outperforming": alpha > 0,
            },
            "risk_metrics": {
                "portfolio_volatility": round(port_vol, 2),
                "benchmark_volatility": round(bm_vol, 2),
                "beta": round(beta, 3),
                "tracking_error": round(tracking_error, 2),
                "information_ratio": round(info_ratio, 3),
                "portfolio_sharpe": round(port_sharpe, 3),
                "benchmark_sharpe": round(bm_sharpe, 3),
            },
            "portfolio_composition": {t: w for t, w in portfolio.items()},
            "source": "yfinance",
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.warning("Portfolio vs benchmark failed: %s", e)
        return {"ticker": benchmark_ticker, "error": str(e)}


def get_sector_attribution(user_id: str) -> Dict[str, Any]:
    """Get sector-level attribution analysis."""
    cache_key = f"sector_attr_{user_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    portfolio = DEMO_PORTFOLIO
    try:
        sectors = {}
        for ticker in portfolio:
            try:
                info = yf.Ticker(ticker).info
                sector = info.get("sector", "Unknown")
                if sector not in sectors:
                    sectors[sector] = {"weight": 0, "tickers": []}
                sectors[sector]["weight"] += portfolio[ticker]
                sectors[sector]["tickers"].append(ticker)
            except Exception:
                continue

        # Get returns for each sector group
        all_data = yf.download(list(portfolio.keys()), period="1y", progress=False)
        if all_data.empty:
            return {"user_id": user_id, "sectors": {}}

        close = all_data["Close"].dropna()
        sector_results = []
        for sector, sdata in sectors.items():
            sector_return = 0
            for ticker in sdata["tickers"]:
                if ticker in close.columns:
                    prices = close[ticker].dropna().values
                    if len(prices) >= 2:
                        ret = (prices[-1] / prices[0] - 1)
                        sector_return += ret * portfolio[ticker]

            sector_results.append({
                "sector": sector,
                "weight": round(sdata["weight"] * 100, 1),
                "tickers": sdata["tickers"],
                "contribution_pct": round(sector_return * 100, 2),
            })

        sector_results.sort(key=lambda x: x["contribution_pct"], reverse=True)
        result = {
            "user_id": user_id,
            "sectors": sector_results,
            "total_sectors": len(sector_results),
            "source": "yfinance",
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.warning("Sector attribution failed: %s", e)
        return {"user_id": user_id, "sectors": [], "error": str(e)}


def get_historical_comparison(
    user_id: str,
    benchmark_ticker: str = "SPY",
    periods: int = 12,
) -> Dict[str, Any]:
    """Get historical performance comparison."""
    cache_key = f"hist_comp_{user_id}_{benchmark_ticker}_{periods}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    portfolio = DEMO_PORTFOLIO
    all_tickers = list(portfolio.keys()) + [benchmark_ticker]

    try:
        data = yf.download(all_tickers, period="1y", progress=False)
        if data.empty:
            return {"user_id": user_id, "periods": []}

        close = data["Close"].dropna()
        n_rows = len(close)
        step = max(1, n_rows // periods)

        monthly_data = []
        for i in range(0, n_rows, step):
            end_idx = min(i + step, n_rows)
            if end_idx <= i:
                break

            # Portfolio return for this period
            port_ret = 0
            for ticker, weight in portfolio.items():
                if ticker in close.columns:
                    slice_prices = close[ticker].iloc[i:end_idx].dropna().values
                    if len(slice_prices) >= 2:
                        port_ret += (slice_prices[-1] / slice_prices[0] - 1) * weight

            # Benchmark return
            bm_ret = 0
            if benchmark_ticker in close.columns:
                bm_slice = close[benchmark_ticker].iloc[i:end_idx].dropna().values
                if len(bm_slice) >= 2:
                    bm_ret = bm_slice[-1] / bm_slice[0] - 1

            monthly_data.append({
                "period_start": str(close.index[i].date()),
                "period_end": str(close.index[min(end_idx - 1, n_rows - 1)].date()),
                "portfolio_return_pct": round(port_ret * 100, 2),
                "benchmark_return_pct": round(bm_ret * 100, 2),
                "alpha_pct": round((port_ret - bm_ret) * 100, 2),
            })

        result = {
            "user_id": user_id,
            "benchmark": benchmark_ticker.upper(),
            "periods": monthly_data,
            "total_periods": len(monthly_data),
            "source": "yfinance",
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.warning("Historical comparison failed: %s", e)
        return {"user_id": user_id, "periods": [], "error": str(e)}


def get_risk_contribution(user_id: str) -> Dict[str, Any]:
    """Get risk contribution by position."""
    cache_key = f"risk_contrib_{user_id}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    portfolio = DEMO_PORTFOLIO
    try:
        data = yf.download(list(portfolio.keys()), period="6mo", progress=False)
        if data.empty:
            return {"user_id": user_id, "positions": []}

        close = data["Close"].dropna()
        positions = []

        for ticker, weight in portfolio.items():
            if ticker not in close.columns:
                continue
            prices = close[ticker].dropna().values
            if len(prices) < 10:
                continue

            returns = _compute_returns(prices)
            vol = float(np.std(returns) * np.sqrt(252) * 100)
            var_95 = float(np.percentile(returns, 5) * 100)

            positions.append({
                "ticker": ticker,
                "weight_pct": round(weight * 100, 1),
                "annualized_vol_pct": round(vol, 2),
                "marginal_var_pct": round(vol * weight, 2),
                "var_95_daily_pct": round(var_95, 2),
                "risk_contribution_pct": round(vol * weight / sum(portfolio.values()) * 100, 1),
            })

        positions.sort(key=lambda x: x["marginal_var_pct"], reverse=True)
        total_risk = sum(p["marginal_var_pct"] for p in positions)

        result = {
            "user_id": user_id,
            "positions": positions,
            "portfolio_volatility_pct": round(total_risk, 2),
            "top_risk_contributor": positions[0]["ticker"] if positions else None,
            "source": "yfinance",
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.warning("Risk contribution failed: %s", e)
        return {"user_id": user_id, "positions": [], "error": str(e)}
