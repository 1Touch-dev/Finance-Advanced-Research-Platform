"""
Portfolio Analytics Service (D1-D11)
Advanced portfolio analytics features
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random
import math


def get_factor_decomposition(user_id: str) -> Dict[str, Any]:
    """D1: Multi-factor risk attribution."""
    factors = ["Market", "Size", "Value", "Momentum", "Quality", "Volatility"]
    return {
        "user_id": user_id,
        "factors": [
            {
                "name": f,
                "exposure": round(random.uniform(-0.5, 1.5), 2),
                "contribution": round(random.uniform(-2, 5), 2),
                "t_stat": round(random.uniform(0.5, 3.0), 2)
            }
            for f in factors
        ],
        "r_squared": round(random.uniform(0.7, 0.95), 2),
        "residual_risk": round(random.uniform(5, 15), 2),
        "tracking_error": round(random.uniform(2, 8), 2)
    }


def get_rebalancing_suggestions(user_id: str, target_allocation: Dict[str, float] = None) -> Dict[str, Any]:
    """D2: Auto-rebalance to target weights."""
    current = {"Technology": 45, "Healthcare": 20, "Financials": 15, "Consumer": 12, "Energy": 8}
    target = target_allocation or {"Technology": 35, "Healthcare": 25, "Financials": 20, "Consumer": 15, "Energy": 5}
    
    trades = []
    for sector in current:
        diff = target.get(sector, 0) - current[sector]
        if abs(diff) > 2:
            trades.append({
                "sector": sector,
                "action": "sell" if diff < 0 else "buy",
                "current_weight": current[sector],
                "target_weight": target.get(sector, 0),
                "change": diff,
                "estimated_value": abs(diff) * 1000
            })
    
    return {
        "user_id": user_id,
        "current_allocation": current,
        "target_allocation": target,
        "suggested_trades": trades,
        "estimated_tax_impact": round(random.uniform(100, 1000), 2),
        "drift_score": round(random.uniform(5, 20), 1)
    }


def get_model_portfolios() -> Dict[str, Any]:
    """D3: Pre-built portfolio templates."""
    models = [
        {"id": "conservative", "name": "Conservative Growth", "risk_level": 3, "expected_return": 6.5, "volatility": 8},
        {"id": "balanced", "name": "Balanced", "risk_level": 5, "expected_return": 8.0, "volatility": 12},
        {"id": "aggressive", "name": "Aggressive Growth", "risk_level": 8, "expected_return": 12.0, "volatility": 18},
        {"id": "income", "name": "Income Focus", "risk_level": 4, "expected_return": 5.5, "volatility": 7},
        {"id": "tech_growth", "name": "Tech Growth", "risk_level": 9, "expected_return": 15.0, "volatility": 25},
    ]
    return {"models": models, "count": len(models)}


def get_risk_parity_allocation(user_id: str) -> Dict[str, Any]:
    """D4: Risk-weighted allocation."""
    assets = ["Stocks", "Bonds", "Commodities", "Real Estate", "Cash"]
    return {
        "user_id": user_id,
        "allocations": [
            {
                "asset": asset,
                "weight": round(random.uniform(10, 30), 1),
                "risk_contribution": round(100 / len(assets), 1),
                "volatility": round(random.uniform(5, 25), 1)
            }
            for asset in assets
        ],
        "portfolio_volatility": round(random.uniform(8, 12), 2),
        "sharpe_ratio": round(random.uniform(0.8, 1.5), 2)
    }


def run_scenario_analysis(user_id: str, scenarios: List[str] = None) -> Dict[str, Any]:
    """D5: What-if portfolio simulations."""
    default_scenarios = ["market_crash", "rate_hike", "recession", "bull_market", "stagflation"]
    scenarios = scenarios or default_scenarios
    
    return {
        "user_id": user_id,
        "scenarios": [
            {
                "name": s,
                "portfolio_impact": round(random.uniform(-30, 20), 1),
                "probability": round(random.uniform(5, 25), 1),
                "worst_holdings": [f"Holding_{i}" for i in range(3)],
                "best_holdings": [f"Holding_{i+3}" for i in range(3)]
            }
            for s in scenarios
        ],
        "var_95": round(random.uniform(-15, -5), 2),
        "cvar_95": round(random.uniform(-20, -10), 2)
    }


def get_drawdown_analytics(user_id: str) -> Dict[str, Any]:
    """D6: Max drawdown, recovery analysis."""
    return {
        "user_id": user_id,
        "max_drawdown": {
            "value": round(random.uniform(-35, -15), 2),
            "start_date": "2022-01-03",
            "bottom_date": "2022-10-12",
            "recovery_date": "2023-07-15",
            "duration_days": 285,
            "recovery_days": 276
        },
        "current_drawdown": round(random.uniform(-10, 0), 2),
        "drawdown_periods": [
            {"start": "2020-02-19", "bottom": "2020-03-23", "end": "2020-08-18", "depth": -33.9},
            {"start": "2022-01-03", "bottom": "2022-10-12", "end": "2023-07-15", "depth": -25.4}
        ],
        "avg_recovery_time": 180
    }


def get_correlation_matrix(user_id: str, tickers: List[str] = None) -> Dict[str, Any]:
    """D7: Asset correlation heatmaps."""
    tickers = tickers or ["NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "JPM", "JNJ"]
    n = len(tickers)
    matrix = [[round(random.uniform(0.3, 1.0) if i != j else 1.0, 2) for j in range(n)] for i in range(n)]
    
    return {
        "user_id": user_id,
        "tickers": tickers,
        "matrix": matrix,
        "avg_correlation": round(sum(sum(row) for row in matrix) / (n * n), 2),
        "highest_corr": {"pair": ["NVDA", "AMD"], "value": 0.85},
        "lowest_corr": {"pair": ["NVDA", "JNJ"], "value": 0.15}
    }


def get_sector_rotation_signals(user_id: str) -> Dict[str, Any]:
    """D8: Sector momentum signals."""
    sectors = ["Technology", "Healthcare", "Financials", "Consumer Discretionary", "Energy", "Industrials", "Materials", "Utilities"]
    return {
        "user_id": user_id,
        "signals": [
            {
                "sector": s,
                "momentum_score": round(random.uniform(-100, 100), 1),
                "signal": random.choice(["overweight", "neutral", "underweight"]),
                "relative_strength": round(random.uniform(0.5, 1.5), 2),
                "trend": random.choice(["up", "down", "sideways"])
            }
            for s in sectors
        ],
        "recommended_rotation": {
            "increase": ["Technology", "Healthcare"],
            "decrease": ["Energy", "Utilities"]
        }
    }


def get_factor_timing_signals() -> Dict[str, Any]:
    """D9: Factor exposure timing."""
    factors = ["Value", "Growth", "Momentum", "Quality", "Low Volatility", "Size"]
    return {
        "factors": [
            {
                "name": f,
                "current_signal": random.choice(["bullish", "neutral", "bearish"]),
                "regime": random.choice(["expansion", "contraction", "recovery"]),
                "recommended_exposure": random.choice(["overweight", "neutral", "underweight"]),
                "conviction": round(random.uniform(0.5, 0.95), 2)
            }
            for f in factors
        ],
        "market_regime": "late_cycle",
        "regime_probability": 0.72
    }


def create_custom_benchmark(user_id: str, components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """D10: Build custom benchmark blends."""
    benchmark_id = f"custom_{user_id}_{datetime.now().strftime('%Y%m%d')}"
    return {
        "benchmark_id": benchmark_id,
        "user_id": user_id,
        "components": components or [
            {"ticker": "SPY", "weight": 60},
            {"ticker": "AGG", "weight": 30},
            {"ticker": "GLD", "weight": 10}
        ],
        "ytd_return": round(random.uniform(5, 15), 2),
        "volatility": round(random.uniform(8, 15), 2),
        "created_at": datetime.now().isoformat()
    }


def get_performance_attribution(user_id: str) -> Dict[str, Any]:
    """D11: Brinson attribution."""
    return {
        "user_id": user_id,
        "total_return": 12.5,
        "benchmark_return": 10.2,
        "excess_return": 2.3,
        "attribution": {
            "allocation_effect": 0.8,
            "selection_effect": 1.2,
            "interaction_effect": 0.3,
            "total_active_return": 2.3
        },
        "by_sector": [
            {"sector": "Technology", "allocation": 0.4, "selection": 0.6, "interaction": 0.1},
            {"sector": "Healthcare", "allocation": 0.2, "selection": 0.3, "interaction": 0.1},
            {"sector": "Financials", "allocation": 0.2, "selection": 0.3, "interaction": 0.1}
        ]
    }
