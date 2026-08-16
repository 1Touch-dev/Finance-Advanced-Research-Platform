"""
Benchmark Attribution Service (Band C #44)
Compare portfolio vs S&P500, sector benchmarks
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random


@dataclass
class BenchmarkData:
    """Benchmark performance data"""
    name: str
    ticker: str
    return_1d: float
    return_1w: float
    return_1m: float
    return_3m: float
    return_ytd: float
    return_1y: float
    volatility: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "ticker": self.ticker,
            "return_1d": self.return_1d,
            "return_1w": self.return_1w,
            "return_1m": self.return_1m,
            "return_3m": self.return_3m,
            "return_ytd": self.return_ytd,
            "return_1y": self.return_1y,
            "volatility": self.volatility,
        }


# Mock benchmark data
BENCHMARKS = {
    "SPY": BenchmarkData("S&P 500", "SPY", 0.45, 1.23, 3.45, 8.12, 18.5, 24.3, 14.2),
    "QQQ": BenchmarkData("NASDAQ 100", "QQQ", 0.62, 1.85, 4.12, 10.5, 22.8, 32.1, 18.5),
    "DIA": BenchmarkData("Dow Jones", "DIA", 0.32, 0.95, 2.85, 6.8, 14.2, 18.7, 12.8),
    "IWM": BenchmarkData("Russell 2000", "IWM", 0.55, 1.45, 2.95, 5.2, 8.5, 12.3, 22.5),
    "XLK": BenchmarkData("Technology", "XLK", 0.72, 2.15, 5.25, 12.8, 28.5, 38.2, 20.1),
    "XLF": BenchmarkData("Financials", "XLF", 0.38, 1.05, 3.15, 7.5, 15.2, 22.5, 16.8),
    "XLE": BenchmarkData("Energy", "XLE", -0.25, -0.85, 1.25, 3.2, 5.8, 8.2, 28.5),
    "XLV": BenchmarkData("Healthcare", "XLV", 0.28, 0.75, 2.15, 4.8, 8.2, 12.5, 13.2),
    "XLY": BenchmarkData("Consumer Disc.", "XLY", 0.52, 1.35, 3.85, 9.2, 18.5, 25.8, 17.5),
    "XLP": BenchmarkData("Consumer Staples", "XLP", 0.18, 0.55, 1.85, 3.5, 6.2, 9.8, 10.5),
}

# Mock portfolio returns for demo user
MOCK_PORTFOLIO_RETURNS = {
    "demo_user": {
        "return_1d": 0.58,
        "return_1w": 1.65,
        "return_1m": 4.85,
        "return_3m": 11.2,
        "return_ytd": 25.8,
        "return_1y": 35.2,
        "volatility": 16.8,
    }
}


def get_benchmarks() -> List[Dict[str, Any]]:
    """Get all available benchmarks"""
    return [b.to_dict() for b in BENCHMARKS.values()]


def get_benchmark(ticker: str) -> Optional[Dict[str, Any]]:
    """Get specific benchmark data"""
    benchmark = BENCHMARKS.get(ticker.upper())
    return benchmark.to_dict() if benchmark else None


def get_portfolio_vs_benchmark(
    user_id: str,
    benchmark_ticker: str = "SPY",
) -> Dict[str, Any]:
    """Compare portfolio performance against a benchmark"""
    portfolio = MOCK_PORTFOLIO_RETURNS.get(user_id, MOCK_PORTFOLIO_RETURNS["demo_user"])
    benchmark = BENCHMARKS.get(benchmark_ticker.upper())

    if not benchmark:
        return {"error": f"Benchmark {benchmark_ticker} not found"}

    periods = ["1d", "1w", "1m", "3m", "ytd", "1y"]
    comparison = []

    for period in periods:
        port_return = portfolio.get(f"return_{period}", 0)
        bench_return = getattr(benchmark, f"return_{period}", 0)
        alpha = port_return - bench_return

        comparison.append({
            "period": period,
            "portfolio_return": port_return,
            "benchmark_return": bench_return,
            "alpha": round(alpha, 2),
            "outperformed": alpha > 0,
        })

    # Calculate risk-adjusted metrics
    portfolio_vol = portfolio.get("volatility", 15)
    benchmark_vol = benchmark.volatility
    risk_free_rate = 4.5  # Approximate current rate

    portfolio_sharpe = (portfolio["return_1y"] - risk_free_rate) / portfolio_vol
    benchmark_sharpe = (benchmark.return_1y - risk_free_rate) / benchmark_vol

    # Information ratio (simplified)
    tracking_error = abs(portfolio_vol - benchmark_vol) + 2  # Simplified
    information_ratio = (portfolio["return_1y"] - benchmark.return_1y) / tracking_error

    return {
        "portfolio": portfolio,
        "benchmark": benchmark.to_dict(),
        "comparison": comparison,
        "risk_metrics": {
            "portfolio_volatility": portfolio_vol,
            "benchmark_volatility": benchmark_vol,
            "portfolio_sharpe": round(portfolio_sharpe, 2),
            "benchmark_sharpe": round(benchmark_sharpe, 2),
            "information_ratio": round(information_ratio, 2),
            "tracking_error": round(tracking_error, 2),
            "beta": round(portfolio_vol / benchmark_vol, 2),
        },
        "summary": {
            "total_alpha_ytd": round(portfolio["return_ytd"] - benchmark.return_ytd, 2),
            "total_alpha_1y": round(portfolio["return_1y"] - benchmark.return_1y, 2),
            "outperforming": portfolio["return_ytd"] > benchmark.return_ytd,
        },
    }


def get_sector_attribution(user_id: str) -> Dict[str, Any]:
    """Get sector-level attribution analysis"""
    # Mock sector weights and returns
    sectors = [
        {"sector": "Technology", "benchmark": "XLK", "portfolio_weight": 35.5, "benchmark_weight": 28.5, "portfolio_return": 32.5, "benchmark_return": 28.5},
        {"sector": "Financials", "benchmark": "XLF", "portfolio_weight": 15.2, "benchmark_weight": 13.5, "portfolio_return": 18.5, "benchmark_return": 15.2},
        {"sector": "Healthcare", "benchmark": "XLV", "portfolio_weight": 12.8, "benchmark_weight": 13.2, "portfolio_return": 10.2, "benchmark_return": 8.2},
        {"sector": "Consumer Disc.", "benchmark": "XLY", "portfolio_weight": 10.5, "benchmark_weight": 10.8, "portfolio_return": 22.5, "benchmark_return": 18.5},
        {"sector": "Energy", "benchmark": "XLE", "portfolio_weight": 5.2, "benchmark_weight": 4.5, "portfolio_return": 6.5, "benchmark_return": 5.8},
        {"sector": "Consumer Staples", "benchmark": "XLP", "portfolio_weight": 8.5, "benchmark_weight": 7.2, "portfolio_return": 8.2, "benchmark_return": 6.2},
        {"sector": "Other", "benchmark": "SPY", "portfolio_weight": 12.3, "benchmark_weight": 22.3, "portfolio_return": 15.5, "benchmark_return": 18.5},
    ]

    total_allocation_effect = 0
    total_selection_effect = 0

    for sector in sectors:
        # Allocation effect: (Portfolio weight - Benchmark weight) * Benchmark return
        allocation_effect = (sector["portfolio_weight"] - sector["benchmark_weight"]) / 100 * sector["benchmark_return"]
        sector["allocation_effect"] = round(allocation_effect, 3)
        total_allocation_effect += allocation_effect

        # Selection effect: Portfolio weight * (Portfolio return - Benchmark return)
        selection_effect = sector["portfolio_weight"] / 100 * (sector["portfolio_return"] - sector["benchmark_return"])
        sector["selection_effect"] = round(selection_effect, 3)
        total_selection_effect += selection_effect

        sector["total_effect"] = round(allocation_effect + selection_effect, 3)

    return {
        "sectors": sectors,
        "summary": {
            "allocation_effect": round(total_allocation_effect, 2),
            "selection_effect": round(total_selection_effect, 2),
            "total_active_return": round(total_allocation_effect + total_selection_effect, 2),
        },
    }


def get_historical_comparison(
    user_id: str,
    benchmark_ticker: str = "SPY",
    periods: int = 12,
) -> Dict[str, Any]:
    """Get historical performance comparison"""
    # Generate mock historical data
    history = []
    base_date = datetime.now()

    for i in range(periods, 0, -1):
        date = base_date - timedelta(days=30 * i)
        port_return = random.uniform(-5, 8) + (12 - i) * 0.5  # Trending up
        bench_return = random.uniform(-4, 6) + (12 - i) * 0.4

        history.append({
            "date": date.strftime("%Y-%m"),
            "portfolio_return": round(port_return, 2),
            "benchmark_return": round(bench_return, 2),
            "alpha": round(port_return - bench_return, 2),
        })

    # Calculate cumulative returns
    port_cumulative = 100
    bench_cumulative = 100

    for h in history:
        port_cumulative *= (1 + h["portfolio_return"] / 100)
        bench_cumulative *= (1 + h["benchmark_return"] / 100)
        h["portfolio_cumulative"] = round(port_cumulative, 2)
        h["benchmark_cumulative"] = round(bench_cumulative, 2)

    return {
        "benchmark": benchmark_ticker.upper(),
        "history": history,
        "final_portfolio_value": round(port_cumulative, 2),
        "final_benchmark_value": round(bench_cumulative, 2),
        "total_outperformance": round(port_cumulative - bench_cumulative, 2),
    }


def get_risk_contribution(user_id: str) -> Dict[str, Any]:
    """Get risk contribution by position"""
    # Mock risk contribution data
    positions = [
        {"ticker": "NVDA", "weight": 25.5, "volatility": 45.2, "beta": 1.85, "risk_contribution": 32.5},
        {"ticker": "AAPL", "weight": 18.2, "volatility": 28.5, "beta": 1.25, "risk_contribution": 18.8},
        {"ticker": "MSFT", "weight": 15.5, "volatility": 25.8, "beta": 1.15, "risk_contribution": 14.2},
        {"ticker": "GOOGL", "weight": 12.8, "volatility": 32.5, "beta": 1.35, "risk_contribution": 12.5},
        {"ticker": "TSLA", "weight": 10.2, "volatility": 55.8, "beta": 2.15, "risk_contribution": 15.8},
        {"ticker": "AMD", "weight": 8.5, "volatility": 48.5, "beta": 1.95, "risk_contribution": 10.2},
        {"ticker": "META", "weight": 9.3, "volatility": 38.2, "beta": 1.45, "risk_contribution": 8.5},
    ]

    # Find overweight risk contributors
    for p in positions:
        p["risk_weight_ratio"] = round(p["risk_contribution"] / p["weight"], 2)
        p["is_risk_heavy"] = p["risk_contribution"] > p["weight"] * 1.2

    return {
        "positions": positions,
        "portfolio_beta": round(sum(p["beta"] * p["weight"] / 100 for p in positions), 2),
        "portfolio_volatility": 16.8,
        "diversification_ratio": 0.72,  # 1 = perfect diversification
    }
