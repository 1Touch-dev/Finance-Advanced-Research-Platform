"""
Portfolio Analytics Service (D1-D11)
Real analytics using yfinance + numpy
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import time
import logging

import yfinance as yf
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_PORTFOLIO = {
    "AAPL": 0.2, "MSFT": 0.15, "NVDA": 0.15, "GOOGL": 0.1,
    "JPM": 0.1, "XOM": 0.1, "JNJ": 0.1, "SPY": 0.1
}


def _get_user_portfolio(user_id: str) -> Dict[str, float]:
    """Get user's portfolio weights from DB, or DEFAULT_PORTFOLIO if none."""
    try:
        from app.db.session import get_db_context
        from app.models.monitor import Portfolio, Position
        from sqlalchemy import text
        with get_db_context() as db:
            portfolio = db.query(Portfolio).first()  # TODO: filter by user_id when auth is wired
            if not portfolio:
                return DEFAULT_PORTFOLIO
            positions = db.execute(
                text("SELECT ticker, qty, cost_basis FROM positions WHERE portfolio_id = :pid"),
                {"pid": portfolio.id}
            ).fetchall()
            if not positions:
                return DEFAULT_PORTFOLIO
            total = sum(r[1] * r[2] for r in positions)
            if total <= 0:
                return DEFAULT_PORTFOLIO
            return {r[0]: (r[1] * r[2]) / total for r in positions if r[0]}
    except Exception as exc:
        logger.debug("Failed to load user portfolio, using default: %s", exc)
        return DEFAULT_PORTFOLIO

SECTOR_ETFS = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy",
    "XLV": "Healthcare", "XLI": "Industrials", "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples", "XLU": "Utilities", "XLB": "Materials",
    "XLRE": "Real Estate", "XLC": "Communication Services"
}

TICKER_SECTORS = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology",
    "GOOGL": "Communication Services", "JPM": "Financials",
    "XOM": "Energy", "JNJ": "Healthcare", "SPY": "Broad Market"
}

_cache: Dict[str, Any] = {}
CACHE_TTL = 1800  # 30 minutes


def _get_cached(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < CACHE_TTL:
            return entry["data"]
    return None


def _set_cache(key: str, data: Any):
    _cache[key] = {"data": data, "ts": time.time()}


def _download_prices(tickers: List[str], period: str = "1y") -> Dict[str, np.ndarray]:
    """Download adjusted close prices for tickers."""
    cache_key = f"prices_{'_'.join(sorted(tickers))}_{period}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
        if data.empty:
            return {}

        result = {}
        if len(tickers) == 1:
            prices = data["Close"].dropna().values
            if len(prices) > 0:
                result[tickers[0]] = prices
        else:
            close = data["Close"]
            for t in tickers:
                if t in close.columns:
                    prices = close[t].dropna().values
                    if len(prices) > 0:
                        result[t] = prices

        _set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Failed to download prices: {e}")
        return {}


def _compute_returns(prices: np.ndarray) -> np.ndarray:
    """Simple daily returns."""
    return np.diff(prices) / prices[:-1]


def _ols_regression(y: np.ndarray, X: np.ndarray):
    """Simple OLS: y = X @ beta + e. Returns betas and r_squared."""
    X_with_const = np.column_stack([np.ones(len(X)), X])
    try:
        beta = np.linalg.lstsq(X_with_const, y, rcond=None)[0]
        y_hat = X_with_const @ beta
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        return beta, r_squared
    except Exception:
        return np.zeros(X_with_const.shape[1]), 0.0


def get_factor_decomposition(user_id: str) -> Dict[str, Any]:
    """D1: Multi-factor risk attribution using SPY, IWM-SPY, IWD-IWG."""
    cache_key = f"factor_decomp_{user_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    portfolio = _get_user_portfolio(user_id)
    factor_tickers = ["SPY", "IWM", "IWD", "IWG"]
    all_tickers = list(set(list(portfolio.keys()) + factor_tickers))

    prices = _download_prices(all_tickers, period="1y")
    if not prices or "SPY" not in prices:
        return {"status": "error", "message": "Could not fetch market data"}

    spy_ret = _compute_returns(prices["SPY"])
    n = len(spy_ret)

    # Build factor returns
    market_factor = spy_ret
    size_factor = np.zeros(n)
    value_factor = np.zeros(n)

    if "IWM" in prices:
        iwm_ret = _compute_returns(prices["IWM"])
        min_len = min(len(iwm_ret), n)
        size_factor[:min_len] = iwm_ret[:min_len] - spy_ret[:min_len]

    if "IWD" in prices and "IWG" in prices:
        iwd_ret = _compute_returns(prices["IWD"])
        iwg_ret = _compute_returns(prices["IWG"])
        min_len = min(len(iwd_ret), len(iwg_ret), n)
        value_factor[:min_len] = iwd_ret[:min_len] - iwg_ret[:min_len]

    X_factors = np.column_stack([market_factor, size_factor, value_factor])

    # Portfolio weighted return
    port_ret = np.zeros(n)
    for ticker, weight in portfolio.items():
        if ticker in prices:
            t_ret = _compute_returns(prices[ticker])
            min_len = min(len(t_ret), n)
            port_ret[:min_len] += weight * t_ret[:min_len]

    beta, r_squared = _ols_regression(port_ret, X_factors)

    # Per-stock decomposition
    stock_factors = {}
    for ticker in portfolio:
        if ticker in prices:
            t_ret = _compute_returns(prices[ticker])
            min_len = min(len(t_ret), n)
            padded = np.zeros(n)
            padded[:min_len] = t_ret[:min_len]
            b, r2 = _ols_regression(padded, X_factors)
            stock_factors[ticker] = {
                "alpha": round(float(b[0]) * 252, 4),
                "market_beta": round(float(b[1]), 3),
                "size_beta": round(float(b[2]), 3),
                "value_beta": round(float(b[3]), 3),
                "r_squared": round(float(r2), 3)
            }

    result = {
        "status": "success",
        "portfolio_factors": {
            "alpha_annualized": round(float(beta[0]) * 252, 4),
            "market_beta": round(float(beta[1]), 3),
            "size_beta": round(float(beta[2]), 3),
            "value_beta": round(float(beta[3]), 3),
            "r_squared": round(float(r_squared), 3),
        },
        "stock_decomposition": stock_factors,
        "factors_used": ["Market (SPY)", "Size (IWM-SPY)", "Value (IWD-IWG)"],
        "period": "1Y",
        "computed_at": datetime.utcnow().isoformat()
    }
    _set_cache(cache_key, result)
    return result


def get_correlation_matrix(user_id: str, tickers: List[str] = None) -> Dict[str, Any]:
    """D7: Pairwise correlation matrix from historical prices."""
    portfolio = _get_user_portfolio(user_id)
    ticker_list = tickers if tickers else list(portfolio.keys())

    cache_key = f"corr_{'_'.join(sorted(ticker_list))}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    prices = _download_prices(ticker_list, period="1y")
    if len(prices) < 2:
        return {"status": "error", "message": "Need at least 2 tickers with data"}

    available = [t for t in ticker_list if t in prices]
    min_len = min(len(prices[t]) for t in available)
    returns_matrix = np.column_stack([
        _compute_returns(prices[t][:min_len]) for t in available
    ])

    corr = np.corrcoef(returns_matrix.T)

    matrix = {}
    for i, t1 in enumerate(available):
        matrix[t1] = {}
        for j, t2 in enumerate(available):
            matrix[t1][t2] = round(float(corr[i, j]), 4)

    # Eigenvalue decomposition for risk contribution
    eigenvalues = np.linalg.eigvalsh(corr)
    eigenvalues = np.sort(eigenvalues)[::-1]

    result = {
        "status": "success",
        "tickers": available,
        "correlation_matrix": matrix,
        "avg_correlation": round(float(
            (np.sum(corr) - len(available)) / (len(available) * (len(available) - 1))
        ), 4),
        "max_correlation": {
            "pair": None,
            "value": 0.0
        },
        "min_correlation": {
            "pair": None,
            "value": 1.0
        },
        "eigenvalues": [round(float(e), 4) for e in eigenvalues[:5]],
        "computed_at": datetime.utcnow().isoformat()
    }

    # Find max/min off-diagonal
    max_val, min_val = -2.0, 2.0
    max_pair, min_pair = ("", ""), ("", "")
    for i, t1 in enumerate(available):
        for j, t2 in enumerate(available):
            if i < j:
                v = corr[i, j]
                if v > max_val:
                    max_val = v
                    max_pair = (t1, t2)
                if v < min_val:
                    min_val = v
                    min_pair = (t1, t2)

    result["max_correlation"] = {"pair": list(max_pair), "value": round(float(max_val), 4)}
    result["min_correlation"] = {"pair": list(min_pair), "value": round(float(min_val), 4)}

    _set_cache(cache_key, result)
    return result


def get_drawdown_analytics(user_id: str) -> Dict[str, Any]:
    """D6: Max drawdown and recovery analysis."""
    cache_key = f"drawdown_{user_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    portfolio = _get_user_portfolio(user_id)
    tickers = list(portfolio.keys())
    prices = _download_prices(tickers, period="2y")

    if not prices:
        return {"status": "error", "message": "Could not fetch price data"}

    # Compute portfolio value series
    available = [t for t in tickers if t in prices]
    min_len = min(len(prices[t]) for t in available)

    # Normalize to $10000 portfolio
    port_values = np.zeros(min_len)
    for t in available:
        weight = portfolio[t]
        p = prices[t][:min_len]
        normalized = p / p[0] * 10000 * weight
        port_values += normalized

    # Drawdown calculation
    running_max = np.maximum.accumulate(port_values)
    drawdowns = (port_values - running_max) / running_max

    max_dd = float(np.min(drawdowns))
    max_dd_idx = int(np.argmin(drawdowns))

    # Find peak before max drawdown
    peak_idx = int(np.argmax(port_values[:max_dd_idx + 1])) if max_dd_idx > 0 else 0

    # Find recovery (if any)
    recovery_idx = None
    peak_val = port_values[peak_idx]
    for i in range(max_dd_idx, min_len):
        if port_values[i] >= peak_val:
            recovery_idx = i
            break

    # Per-stock drawdowns
    stock_drawdowns = {}
    for t in available:
        p = prices[t][:min_len]
        rm = np.maximum.accumulate(p)
        dd = (p - rm) / rm
        stock_drawdowns[t] = {
            "max_drawdown": round(float(np.min(dd)), 4),
            "current_drawdown": round(float(dd[-1]), 4),
        }

    # Drawdown periods (top 5)
    dd_periods = []
    in_dd = False
    start = 0
    for i in range(1, min_len):
        if drawdowns[i] < -0.02 and not in_dd:
            in_dd = True
            start = i
        elif drawdowns[i] >= -0.005 and in_dd:
            in_dd = False
            dd_val = float(np.min(drawdowns[start:i]))
            dd_periods.append({"start_idx": start, "end_idx": i, "depth": round(dd_val, 4)})

    dd_periods.sort(key=lambda x: x["depth"])
    top_periods = dd_periods[:5]

    result = {
        "status": "success",
        "portfolio_drawdown": {
            "max_drawdown": round(max_dd, 4),
            "current_drawdown": round(float(drawdowns[-1]), 4),
            "peak_to_trough_days": max_dd_idx - peak_idx,
            "recovery_days": (recovery_idx - max_dd_idx) if recovery_idx else None,
            "recovered": recovery_idx is not None,
        },
        "stock_drawdowns": stock_drawdowns,
        "worst_periods": top_periods,
        "portfolio_value_start": round(float(port_values[0]), 2),
        "portfolio_value_end": round(float(port_values[-1]), 2),
        "computed_at": datetime.utcnow().isoformat()
    }
    _set_cache(cache_key, result)
    return result


def get_performance_attribution(user_id: str) -> Dict[str, Any]:
    """D11: Brinson-style performance attribution by stock/sector."""
    cache_key = f"perf_attr_{user_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    portfolio = _get_user_portfolio(user_id)
    tickers = list(portfolio.keys())
    prices = _download_prices(tickers + ["SPY"], period="6mo")

    if not prices or "SPY" not in prices:
        return {"status": "error", "message": "Could not fetch price data"}

    benchmark_ret = (prices["SPY"][-1] / prices["SPY"][0]) - 1

    # Stock-level attribution
    stock_attribution = {}
    total_port_return = 0.0
    for t in tickers:
        if t in prices:
            stock_ret = (prices[t][-1] / prices[t][0]) - 1
            contribution = portfolio[t] * stock_ret
            total_port_return += contribution
            stock_attribution[t] = {
                "weight": portfolio[t],
                "return": round(float(stock_ret), 4),
                "contribution": round(float(contribution), 4),
                "sector": TICKER_SECTORS.get(t, "Other"),
            }

    # Sector-level attribution
    sector_data = {}
    for t, info in stock_attribution.items():
        sector = info["sector"]
        if sector not in sector_data:
            sector_data[sector] = {"weight": 0.0, "contribution": 0.0, "stocks": []}
        sector_data[sector]["weight"] += info["weight"]
        sector_data[sector]["contribution"] += info["contribution"]
        sector_data[sector]["stocks"].append(t)

    for s in sector_data:
        w = sector_data[s]["weight"]
        sector_data[s]["weighted_return"] = round(
            sector_data[s]["contribution"] / w if w > 0 else 0, 4
        )
        sector_data[s]["weight"] = round(sector_data[s]["weight"], 4)
        sector_data[s]["contribution"] = round(sector_data[s]["contribution"], 4)

    active_return = total_port_return - benchmark_ret

    result = {
        "status": "success",
        "summary": {
            "portfolio_return": round(float(total_port_return), 4),
            "benchmark_return": round(float(benchmark_ret), 4),
            "active_return": round(float(active_return), 4),
            "period": "6M",
        },
        "stock_attribution": stock_attribution,
        "sector_attribution": sector_data,
        "computed_at": datetime.utcnow().isoformat()
    }
    _set_cache(cache_key, result)
    return result


def run_scenario_analysis(user_id: str, scenarios: List[str] = None) -> Dict[str, Any]:
    """D5: Historical scenario replay on current portfolio."""
    cache_key = f"scenario_{user_id}_{'_'.join(scenarios or [])}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    SCENARIOS = {
        "2008_financial_crisis": {"start": "2008-09-01", "end": "2009-03-09", "label": "2008 Financial Crisis"},
        "covid_crash": {"start": "2020-02-19", "end": "2020-03-23", "label": "COVID-19 Crash"},
        "2022_rate_hike": {"start": "2022-01-03", "end": "2022-10-12", "label": "2022 Rate Hike Bear Market"},
        "dot_com_burst": {"start": "2000-03-10", "end": "2002-10-09", "label": "Dot-Com Bubble Burst"},
        "2020_recovery": {"start": "2020-03-23", "end": "2020-08-18", "label": "COVID Recovery Rally"},
    }

    selected = scenarios or ["2008_financial_crisis", "covid_crash", "2022_rate_hike"]
    portfolio = _get_user_portfolio(user_id)
    tickers = list(portfolio.keys())

    results = {}
    for scenario_key in selected:
        if scenario_key not in SCENARIOS:
            results[scenario_key] = {"error": "Unknown scenario"}
            continue

        sc = SCENARIOS[scenario_key]
        try:
            data = yf.download(
                tickers, start=sc["start"], end=sc["end"],
                auto_adjust=True, progress=False
            )
            if data.empty:
                results[scenario_key] = {"error": "No data for period"}
                continue

            close = data["Close"] if len(tickers) > 1 else data[["Close"]]
            scenario_result = {"label": sc["label"], "period": f"{sc['start']} to {sc['end']}", "stocks": {}}
            port_return = 0.0

            for t in tickers:
                try:
                    if len(tickers) > 1:
                        col = close[t].dropna()
                    else:
                        col = close["Close"].dropna()
                    if len(col) >= 2:
                        ret = float((col.iloc[-1] / col.iloc[0]) - 1)
                        scenario_result["stocks"][t] = {
                            "return": round(ret, 4),
                            "contribution": round(ret * portfolio[t], 4)
                        }
                        port_return += ret * portfolio[t]
                except Exception:
                    pass

            scenario_result["portfolio_return"] = round(port_return, 4)
            scenario_result["portfolio_dollar_impact"] = round(port_return * 10000, 2)
            results[scenario_key] = scenario_result
        except Exception as e:
            results[scenario_key] = {"error": str(e)}

    result = {
        "status": "success",
        "scenarios": results,
        "portfolio_value_assumed": 10000,
        "computed_at": datetime.utcnow().isoformat()
    }
    _set_cache(cache_key, result)
    return result


def get_risk_parity_allocation(user_id: str) -> Dict[str, Any]:
    """D4: Equal risk contribution weights using inverse volatility."""
    cache_key = f"risk_parity_{user_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    portfolio = _get_user_portfolio(user_id)
    tickers = list(portfolio.keys())
    prices = _download_prices(tickers, period="1y")

    if not prices:
        return {"status": "error", "message": "Could not fetch price data"}

    available = [t for t in tickers if t in prices]
    vols = {}
    for t in available:
        ret = _compute_returns(prices[t])
        vols[t] = float(np.std(ret) * np.sqrt(252))  # annualized vol

    # Inverse volatility weighting
    inv_vols = {t: 1.0 / v for t, v in vols.items() if v > 0}
    total_inv = sum(inv_vols.values())
    risk_parity_weights = {t: round(iv / total_inv, 4) for t, iv in inv_vols.items()}

    # Compare to current
    comparisons = {}
    for t in available:
        current_w = portfolio.get(t, 0)
        rp_w = risk_parity_weights.get(t, 0)
        comparisons[t] = {
            "current_weight": current_w,
            "risk_parity_weight": rp_w,
            "difference": round(rp_w - current_w, 4),
            "annualized_vol": round(vols[t], 4),
        }

    # Portfolio vol under both allocations
    min_len = min(len(prices[t]) for t in available)
    returns_matrix = np.column_stack([_compute_returns(prices[t][:min_len]) for t in available])
    cov = np.cov(returns_matrix.T) * 252

    current_weights = np.array([portfolio.get(t, 0) for t in available])
    rp_weights = np.array([risk_parity_weights.get(t, 0) for t in available])

    current_port_vol = float(np.sqrt(current_weights @ cov @ current_weights))
    rp_port_vol = float(np.sqrt(rp_weights @ cov @ rp_weights))

    result = {
        "status": "success",
        "risk_parity_weights": risk_parity_weights,
        "comparisons": comparisons,
        "portfolio_volatility": {
            "current": round(current_port_vol, 4),
            "risk_parity": round(rp_port_vol, 4),
            "reduction": round((current_port_vol - rp_port_vol) / current_port_vol, 4) if current_port_vol > 0 else 0,
        },
        "method": "Inverse Volatility Weighting",
        "computed_at": datetime.utcnow().isoformat()
    }
    _set_cache(cache_key, result)
    return result


def get_rebalancing_suggestions(user_id: str, target_allocation: Dict[str, float] = None) -> Dict[str, Any]:
    """D2: Compare current to target, suggest trades."""
    cache_key = f"rebal_{user_id}"
    cached = _get_cached(cache_key)
    if cached and target_allocation is None:
        return cached

    portfolio = _get_user_portfolio(user_id)
    target = target_allocation or portfolio  # if no target, use equal weight
    if target_allocation is None:
        n = len(portfolio)
        target = {t: round(1.0 / n, 4) for t in portfolio}

    tickers = list(set(list(portfolio.keys()) + list(target.keys())))
    prices = _download_prices(tickers, period="3mo")

    # Simulate drift: use 3-month returns to drift current weights
    drifted_weights = {}
    total_value = 0.0
    for t, w in portfolio.items():
        if t in prices and len(prices[t]) >= 2:
            growth = prices[t][-1] / prices[t][0]
            drifted_weights[t] = w * growth
            total_value += w * growth
        else:
            drifted_weights[t] = w
            total_value += w

    # Normalize drifted weights
    for t in drifted_weights:
        drifted_weights[t] = drifted_weights[t] / total_value

    # Calculate trades needed
    trades = []
    portfolio_value = 10000  # assumed
    for t in set(list(drifted_weights.keys()) + list(target.keys())):
        current = drifted_weights.get(t, 0)
        tgt = target.get(t, 0)
        diff = tgt - current
        if abs(diff) > 0.005:  # only suggest if >0.5% difference
            trades.append({
                "ticker": t,
                "current_weight": round(float(current), 4),
                "target_weight": round(float(tgt), 4),
                "difference": round(float(diff), 4),
                "action": "BUY" if diff > 0 else "SELL",
                "dollar_amount": round(abs(diff) * portfolio_value, 2),
            })

    trades.sort(key=lambda x: abs(x["difference"]), reverse=True)

    # Tracking error
    drift_amount = sum(abs(drifted_weights.get(t, 0) - target.get(t, 0)) for t in set(list(drifted_weights.keys()) + list(target.keys())))

    result = {
        "status": "success",
        "current_weights_drifted": {t: round(float(v), 4) for t, v in drifted_weights.items()},
        "target_weights": target,
        "suggested_trades": trades,
        "total_drift": round(float(drift_amount), 4),
        "num_trades_needed": len(trades),
        "portfolio_value_assumed": portfolio_value,
        "computed_at": datetime.utcnow().isoformat()
    }
    _set_cache(cache_key, result)
    return result


def get_sector_rotation_signals(user_id: str) -> Dict[str, Any]:
    """D8: Sector momentum from ETFs."""
    cache_key = "sector_rotation"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    etf_list = list(SECTOR_ETFS.keys())
    prices = _download_prices(etf_list, period="6mo")

    if not prices:
        return {"status": "error", "message": "Could not fetch sector ETF data"}

    sectors = {}
    for etf, sector_name in SECTOR_ETFS.items():
        if etf not in prices or len(prices[etf]) < 20:
            continue
        p = prices[etf]

        # Momentum signals
        ret_1m = float((p[-1] / p[-21]) - 1) if len(p) >= 22 else 0
        ret_3m = float((p[-1] / p[-63]) - 1) if len(p) >= 64 else 0
        ret_6m = float((p[-1] / p[0]) - 1)

        # Relative strength vs SPY
        vol = float(np.std(_compute_returns(p)) * np.sqrt(252))

        # Simple moving average trend
        sma_50 = float(np.mean(p[-50:])) if len(p) >= 50 else float(np.mean(p))
        above_sma = float(p[-1]) > sma_50

        # Momentum score (composite)
        score = (ret_1m * 0.3 + ret_3m * 0.4 + ret_6m * 0.3) * 100

        sectors[sector_name] = {
            "etf": etf,
            "return_1m": round(ret_1m, 4),
            "return_3m": round(ret_3m, 4),
            "return_6m": round(ret_6m, 4),
            "volatility": round(vol, 4),
            "above_sma50": above_sma,
            "momentum_score": round(score, 2),
            "signal": "OVERWEIGHT" if score > 5 else ("UNDERWEIGHT" if score < -5 else "NEUTRAL"),
        }

    # Rank sectors
    ranked = sorted(sectors.items(), key=lambda x: x[1]["momentum_score"], reverse=True)

    result = {
        "status": "success",
        "sectors": sectors,
        "ranking": [{"rank": i + 1, "sector": s[0], "score": s[1]["momentum_score"]} for i, s in enumerate(ranked)],
        "top_sectors": [s[0] for s in ranked[:3]],
        "bottom_sectors": [s[0] for s in ranked[-3:]],
        "computed_at": datetime.utcnow().isoformat()
    }
    _set_cache(cache_key, result)
    return result


def get_factor_timing_signals() -> Dict[str, Any]:
    """D9: Factor momentum/mean-reversion signals."""
    cache_key = "factor_timing"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    factor_etfs = {
        "MTUM": "Momentum", "VLUE": "Value", "QUAL": "Quality",
        "SIZE": "Size", "USMV": "Low Volatility"
    }

    prices = _download_prices(list(factor_etfs.keys()) + ["SPY"], period="1y")
    if not prices or "SPY" not in prices:
        return {"status": "error", "message": "Could not fetch factor ETF data"}

    spy_p = prices["SPY"]
    factors = {}

    for etf, factor_name in factor_etfs.items():
        if etf not in prices or len(prices[etf]) < 50:
            continue
        p = prices[etf]
        min_len = min(len(p), len(spy_p))

        # Relative performance vs SPY
        etf_ret = (p[-1] / p[0]) - 1
        spy_ret = (spy_p[-1] / spy_p[0]) - 1
        relative_perf = float(etf_ret - spy_ret)

        # Recent momentum (1m)
        ret_1m = float((p[-1] / p[-21]) - 1) if len(p) >= 22 else 0

        # Vol of relative returns
        etf_rets = _compute_returns(p[:min_len])
        spy_rets = _compute_returns(spy_p[:min_len])
        min_r = min(len(etf_rets), len(spy_rets))
        rel_rets = etf_rets[:min_r] - spy_rets[:min_r]
        rel_vol = float(np.std(rel_rets) * np.sqrt(252))

        # Z-score of recent performance
        rolling_rets = []
        for i in range(max(0, len(p) - 252), len(p) - 21):
            rolling_rets.append((p[i + 21] / p[i]) - 1)
        z_score = 0.0
        if rolling_rets:
            mean_r = np.mean(rolling_rets)
            std_r = np.std(rolling_rets)
            if std_r > 0:
                z_score = float((ret_1m - mean_r) / std_r)

        signal = "OVERWEIGHT" if z_score > 1 else ("UNDERWEIGHT" if z_score < -1 else "NEUTRAL")

        factors[factor_name] = {
            "etf": etf,
            "ytd_return": round(float(etf_ret), 4),
            "relative_to_spy": round(relative_perf, 4),
            "return_1m": round(ret_1m, 4),
            "relative_volatility": round(rel_vol, 4),
            "z_score": round(z_score, 2),
            "signal": signal,
        }

    result = {
        "status": "success",
        "factors": factors,
        "recommendation": "Favor factors with positive z-scores and rising momentum",
        "computed_at": datetime.utcnow().isoformat()
    }
    _set_cache(cache_key, result)
    return result


def get_model_portfolios() -> Dict[str, Any]:
    """D3: Pre-built portfolio templates with real performance data."""
    cache_key = "model_portfolios"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    models = {
        "aggressive_growth": {
            "name": "Aggressive Growth",
            "description": "High-growth tech-heavy portfolio",
            "holdings": {"QQQ": 0.4, "ARKK": 0.15, "SOXX": 0.15, "VGT": 0.15, "MTUM": 0.15},
        },
        "balanced": {
            "name": "Balanced 60/40",
            "description": "Classic balanced allocation",
            "holdings": {"VTI": 0.40, "VXUS": 0.20, "BND": 0.30, "GLD": 0.10},
        },
        "dividend_income": {
            "name": "Dividend Income",
            "description": "High-yield dividend focus",
            "holdings": {"VYM": 0.30, "SCHD": 0.30, "DVY": 0.20, "JEPI": 0.20},
        },
        "all_weather": {
            "name": "All Weather (Ray Dalio inspired)",
            "description": "Diversified across asset classes",
            "holdings": {"VTI": 0.30, "TLT": 0.40, "GLD": 0.15, "DBC": 0.075, "IEF": 0.075},
        },
    }

    # Fetch real performance for each model
    all_tickers = set()
    for m in models.values():
        all_tickers.update(m["holdings"].keys())

    prices = _download_prices(list(all_tickers), period="1y")

    for key, model in models.items():
        port_ret = 0.0
        port_vol_data = []
        for t, w in model["holdings"].items():
            if t in prices and len(prices[t]) >= 2:
                ret = (prices[t][-1] / prices[t][0]) - 1
                port_ret += w * ret
                daily_ret = _compute_returns(prices[t])
                port_vol_data.append((w, daily_ret))

        # Simple portfolio vol estimate
        if port_vol_data:
            weighted_var = sum(
                w ** 2 * np.var(r) for w, r in port_vol_data
            ) * 252
            model["performance"] = {
                "return_1y": round(float(port_ret), 4),
                "est_volatility": round(float(np.sqrt(weighted_var)), 4),
                "sharpe_est": round(float(port_ret / np.sqrt(weighted_var)) if weighted_var > 0 else 0, 2),
            }
        else:
            model["performance"] = {"return_1y": None, "est_volatility": None, "sharpe_est": None}

    result = {
        "status": "success",
        "models": models,
        "computed_at": datetime.utcnow().isoformat()
    }
    _set_cache(cache_key, result)
    return result


def create_custom_benchmark(user_id: str, components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """D10: Build custom benchmark from ETF blend."""
    # components: [{"ticker": "SPY", "weight": 0.6}, {"ticker": "AGG", "weight": 0.4}]
    tickers = [c["ticker"] for c in components if "ticker" in c]
    weights = {c["ticker"]: c.get("weight", 1.0 / len(components)) for c in components}

    # Normalize weights
    total_w = sum(weights.values())
    weights = {t: w / total_w for t, w in weights.items()}

    prices = _download_prices(tickers, period="1y")
    if not prices:
        return {"status": "error", "message": "Could not fetch benchmark data"}

    available = [t for t in tickers if t in prices]
    min_len = min(len(prices[t]) for t in available)

    # Build benchmark series
    bench_values = np.zeros(min_len)
    for t in available:
        p = prices[t][:min_len]
        bench_values += weights[t] * (p / p[0])

    bench_returns = _compute_returns(bench_values)
    total_return = float(bench_values[-1] / bench_values[0] - 1)
    vol = float(np.std(bench_returns) * np.sqrt(252))
    sharpe = total_return / vol if vol > 0 else 0

    # Max drawdown
    running_max = np.maximum.accumulate(bench_values)
    drawdowns = (bench_values - running_max) / running_max
    max_dd = float(np.min(drawdowns))

    result = {
        "status": "success",
        "benchmark": {
            "components": [{"ticker": t, "weight": round(weights[t], 4)} for t in available],
            "total_return": round(total_return, 4),
            "annualized_vol": round(vol, 4),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd, 4),
            "data_points": min_len,
        },
        "computed_at": datetime.utcnow().isoformat()
    }
    return result
