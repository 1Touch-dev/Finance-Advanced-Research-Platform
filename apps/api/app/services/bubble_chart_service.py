"""
Interactive Bubble Charts Service (James J5)
Multi-dimensional bubble chart data
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random
import math


@dataclass
class BubbleDataPoint:
    """Data point for bubble chart"""
    ticker: str
    name: str
    x: float  # X-axis metric
    y: float  # Y-axis metric
    size: float  # Bubble size
    color: str  # Color category
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "size": self.size,
            "color": self.color,
            "metadata": self.metadata,
        }


# Sector colors
SECTOR_COLORS = {
    "Technology": "#3B82F6",
    "Healthcare": "#10B981",
    "Financial": "#F59E0B",
    "Consumer": "#EF4444",
    "Energy": "#8B5CF6",
    "Industrial": "#EC4899",
    "Materials": "#06B6D4",
    "Utilities": "#F97316",
    "Real Estate": "#84CC16",
    "Communication": "#14B8A6",
}

# Mock company data
COMPANIES = [
    {"ticker": "NVDA", "name": "NVIDIA Corp", "sector": "Technology", "market_cap": 3100, "pe": 65, "growth": 125, "revenue": 60},
    {"ticker": "AAPL", "name": "Apple Inc", "sector": "Technology", "market_cap": 2900, "pe": 28, "growth": 8, "revenue": 385},
    {"ticker": "MSFT", "name": "Microsoft Corp", "sector": "Technology", "market_cap": 2800, "pe": 35, "growth": 18, "revenue": 211},
    {"ticker": "GOOGL", "name": "Alphabet Inc", "sector": "Communication", "market_cap": 2100, "pe": 25, "growth": 15, "revenue": 307},
    {"ticker": "AMZN", "name": "Amazon.com", "sector": "Consumer", "market_cap": 1900, "pe": 60, "growth": 12, "revenue": 575},
    {"ticker": "META", "name": "Meta Platforms", "sector": "Communication", "market_cap": 1200, "pe": 28, "growth": 22, "revenue": 135},
    {"ticker": "TSLA", "name": "Tesla Inc", "sector": "Consumer", "market_cap": 780, "pe": 75, "growth": 25, "revenue": 95},
    {"ticker": "UNH", "name": "UnitedHealth", "sector": "Healthcare", "market_cap": 480, "pe": 22, "growth": 10, "revenue": 371},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare", "market_cap": 420, "pe": 18, "growth": 5, "revenue": 85},
    {"ticker": "JPM", "name": "JPMorgan Chase", "sector": "Financial", "market_cap": 580, "pe": 12, "growth": 8, "revenue": 155},
    {"ticker": "V", "name": "Visa Inc", "sector": "Financial", "market_cap": 550, "pe": 30, "growth": 12, "revenue": 33},
    {"ticker": "XOM", "name": "Exxon Mobil", "sector": "Energy", "market_cap": 460, "pe": 11, "growth": -5, "revenue": 345},
    {"ticker": "PG", "name": "Procter & Gamble", "sector": "Consumer", "market_cap": 380, "pe": 25, "growth": 4, "revenue": 83},
    {"ticker": "HD", "name": "Home Depot", "sector": "Consumer", "market_cap": 350, "pe": 22, "growth": 6, "revenue": 152},
    {"ticker": "CVX", "name": "Chevron Corp", "sector": "Energy", "market_cap": 280, "pe": 10, "growth": -8, "revenue": 200},
]


def get_bubble_chart(
    x_metric: str = "market_cap",
    y_metric: str = "pe_ratio",
    size_metric: str = "revenue",
    color_by: str = "sector",
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get bubble chart data with configurable metrics"""
    companies = COMPANIES.copy()

    if tickers:
        tickers_upper = [t.upper() for t in tickers]
        companies = [c for c in companies if c["ticker"] in tickers_upper]

    bubbles = []
    for company in companies:
        # Map metrics
        x_value = _get_metric_value(company, x_metric)
        y_value = _get_metric_value(company, y_metric)
        size_value = _get_metric_value(company, size_metric)

        # Determine color
        if color_by == "sector":
            color = SECTOR_COLORS.get(company["sector"], "#6B7280")
            color_label = company["sector"]
        elif color_by == "performance":
            perf = company["growth"]
            color = "#10B981" if perf > 10 else "#EF4444" if perf < 0 else "#F59E0B"
            color_label = "positive" if perf > 0 else "negative"
        else:
            color = "#3B82F6"
            color_label = "default"

        bubbles.append({
            "ticker": company["ticker"],
            "name": company["name"],
            "x": x_value,
            "y": y_value,
            "size": size_value,
            "color": color,
            "color_label": color_label,
            "sector": company["sector"],
            "metadata": {
                "market_cap": company["market_cap"],
                "pe_ratio": company["pe"],
                "growth": company["growth"],
                "revenue": company["revenue"],
            },
        })

    return {
        "chart_type": "bubble",
        "x_axis": {
            "metric": x_metric,
            "label": _format_metric_label(x_metric),
            "min": min(b["x"] for b in bubbles) * 0.9 if bubbles else 0,
            "max": max(b["x"] for b in bubbles) * 1.1 if bubbles else 100,
        },
        "y_axis": {
            "metric": y_metric,
            "label": _format_metric_label(y_metric),
            "min": min(b["y"] for b in bubbles) * 0.9 if bubbles else 0,
            "max": max(b["y"] for b in bubbles) * 1.1 if bubbles else 100,
        },
        "size": {
            "metric": size_metric,
            "label": _format_metric_label(size_metric),
            "min": min(b["size"] for b in bubbles) if bubbles else 0,
            "max": max(b["size"] for b in bubbles) if bubbles else 100,
        },
        "color_by": color_by,
        "data": bubbles,
        "legend": _get_legend(color_by, bubbles),
    }


def _get_metric_value(company: Dict, metric: str) -> float:
    """Get metric value from company data"""
    metric_map = {
        "market_cap": company["market_cap"],
        "pe_ratio": company["pe"],
        "growth": company["growth"],
        "revenue": company["revenue"],
        "profit_margin": random.uniform(5, 35),
        "debt_to_equity": random.uniform(0.2, 2.5),
        "dividend_yield": random.uniform(0, 4),
        "beta": random.uniform(0.5, 2.0),
        "volatility": random.uniform(15, 60),
        "rsi": random.uniform(30, 70),
    }
    return round(metric_map.get(metric, 50), 2)


def _format_metric_label(metric: str) -> str:
    """Format metric name for display"""
    labels = {
        "market_cap": "Market Cap ($B)",
        "pe_ratio": "P/E Ratio",
        "growth": "Revenue Growth (%)",
        "revenue": "Revenue ($B)",
        "profit_margin": "Profit Margin (%)",
        "debt_to_equity": "Debt/Equity",
        "dividend_yield": "Dividend Yield (%)",
        "beta": "Beta",
        "volatility": "Volatility (%)",
        "rsi": "RSI",
    }
    return labels.get(metric, metric.replace("_", " ").title())


def _get_legend(color_by: str, bubbles: List[Dict]) -> List[Dict]:
    """Generate legend for bubble chart"""
    if color_by == "sector":
        sectors = set(b["color_label"] for b in bubbles)
        return [{"label": s, "color": SECTOR_COLORS.get(s, "#6B7280")} for s in sorted(sectors)]
    elif color_by == "performance":
        return [
            {"label": "Positive Growth", "color": "#10B981"},
            {"label": "Flat", "color": "#F59E0B"},
            {"label": "Negative Growth", "color": "#EF4444"},
        ]
    return []


def get_bubble_presets() -> List[Dict[str, Any]]:
    """Get preset bubble chart configurations"""
    return [
        {
            "name": "Value vs Growth",
            "x_metric": "pe_ratio",
            "y_metric": "growth",
            "size_metric": "market_cap",
            "color_by": "sector",
            "description": "Compare valuation to growth rate",
        },
        {
            "name": "Size vs Profitability",
            "x_metric": "market_cap",
            "y_metric": "profit_margin",
            "size_metric": "revenue",
            "color_by": "sector",
            "description": "Large caps vs profit margins",
        },
        {
            "name": "Risk vs Return",
            "x_metric": "volatility",
            "y_metric": "growth",
            "size_metric": "market_cap",
            "color_by": "performance",
            "description": "Volatility vs returns",
        },
        {
            "name": "Dividend Screener",
            "x_metric": "dividend_yield",
            "y_metric": "debt_to_equity",
            "size_metric": "market_cap",
            "color_by": "sector",
            "description": "Yield vs leverage",
        },
        {
            "name": "Momentum Analysis",
            "x_metric": "rsi",
            "y_metric": "beta",
            "size_metric": "market_cap",
            "color_by": "performance",
            "description": "Technical momentum indicators",
        },
    ]


def get_animated_bubble_data(
    ticker: str,
    periods: int = 12,
    interval: str = "quarterly",
) -> Dict[str, Any]:
    """Get animated bubble chart data over time"""
    frames = []
    base_date = datetime.now()

    if interval == "monthly":
        days_per_period = 30
    elif interval == "yearly":
        days_per_period = 365
    else:
        days_per_period = 90

    base_x = random.uniform(20, 80)
    base_y = random.uniform(15, 50)
    base_size = random.uniform(50, 200)

    for i in range(periods):
        date = base_date - timedelta(days=days_per_period * (periods - i - 1))

        # Evolve values over time
        base_x = max(10, min(100, base_x + random.uniform(-5, 7)))
        base_y = max(5, min(80, base_y + random.uniform(-3, 4)))
        base_size = max(20, min(300, base_size + random.uniform(-10, 15)))

        frames.append({
            "date": date.strftime("%Y-%m-%d"),
            "x": round(base_x, 2),
            "y": round(base_y, 2),
            "size": round(base_size, 2),
        })

    return {
        "ticker": ticker.upper(),
        "animation_type": "time_series",
        "interval": interval,
        "frames": frames,
        "x_metric": "pe_ratio",
        "y_metric": "growth",
        "size_metric": "market_cap",
    }


def get_sector_bubble_chart(sector: Optional[str] = None) -> Dict[str, Any]:
    """Get bubble chart grouped by sector"""
    companies = COMPANIES.copy()

    if sector:
        companies = [c for c in companies if c["sector"].lower() == sector.lower()]

    sectors = {}
    for company in companies:
        s = company["sector"]
        if s not in sectors:
            sectors[s] = {
                "sector": s,
                "companies": [],
                "total_market_cap": 0,
                "avg_pe": 0,
                "avg_growth": 0,
            }
        sectors[s]["companies"].append(company["ticker"])
        sectors[s]["total_market_cap"] += company["market_cap"]

    sector_bubbles = []
    for s, data in sectors.items():
        sector_companies = [c for c in companies if c["sector"] == s]
        avg_pe = sum(c["pe"] for c in sector_companies) / len(sector_companies)
        avg_growth = sum(c["growth"] for c in sector_companies) / len(sector_companies)

        sector_bubbles.append({
            "sector": s,
            "x": round(avg_pe, 1),
            "y": round(avg_growth, 1),
            "size": data["total_market_cap"],
            "color": SECTOR_COLORS.get(s, "#6B7280"),
            "company_count": len(sector_companies),
            "companies": data["companies"],
        })

    return {
        "chart_type": "sector_bubble",
        "x_axis": {"metric": "avg_pe", "label": "Average P/E Ratio"},
        "y_axis": {"metric": "avg_growth", "label": "Average Growth (%)"},
        "size": {"metric": "market_cap", "label": "Total Market Cap ($B)"},
        "data": sector_bubbles,
    }


def get_comparison_bubble_chart(
    ticker1: str,
    ticker2: str,
    periods: int = 8,
) -> Dict[str, Any]:
    """Get comparison bubble chart for two tickers"""
    def generate_history(base_x, base_y, base_size):
        history = []
        for i in range(periods):
            base_x = max(10, min(100, base_x + random.uniform(-5, 5)))
            base_y = max(0, min(80, base_y + random.uniform(-5, 5)))
            base_size = max(50, min(500, base_size + random.uniform(-20, 20)))
            history.append({"x": round(base_x, 1), "y": round(base_y, 1), "size": round(base_size, 1)})
        return history

    return {
        "chart_type": "comparison_bubble",
        "ticker1": {
            "ticker": ticker1.upper(),
            "color": "#3B82F6",
            "history": generate_history(40, 25, 200),
        },
        "ticker2": {
            "ticker": ticker2.upper(),
            "color": "#EF4444",
            "history": generate_history(35, 30, 150),
        },
        "x_axis": {"label": "P/E Ratio"},
        "y_axis": {"label": "Revenue Growth (%)"},
        "size": {"label": "Market Cap ($B)"},
        "periods": periods,
    }


def get_bubble_metrics() -> List[Dict[str, Any]]:
    """Get available metrics for bubble charts"""
    return [
        {"id": "market_cap", "label": "Market Cap", "unit": "$B", "type": "size"},
        {"id": "pe_ratio", "label": "P/E Ratio", "unit": "x", "type": "value"},
        {"id": "growth", "label": "Revenue Growth", "unit": "%", "type": "percent"},
        {"id": "revenue", "label": "Revenue", "unit": "$B", "type": "size"},
        {"id": "profit_margin", "label": "Profit Margin", "unit": "%", "type": "percent"},
        {"id": "debt_to_equity", "label": "Debt/Equity", "unit": "x", "type": "ratio"},
        {"id": "dividend_yield", "label": "Dividend Yield", "unit": "%", "type": "percent"},
        {"id": "beta", "label": "Beta", "unit": "", "type": "ratio"},
        {"id": "volatility", "label": "Volatility", "unit": "%", "type": "percent"},
        {"id": "rsi", "label": "RSI", "unit": "", "type": "indicator"},
    ]


def get_portfolio_bubble_chart(user_id: str) -> Dict[str, Any]:
    """Get bubble chart for user's portfolio"""
    # Mock portfolio holdings
    holdings = [
        {"ticker": "NVDA", "shares": 100, "weight": 25.5},
        {"ticker": "AAPL", "shares": 200, "weight": 22.3},
        {"ticker": "MSFT", "shares": 150, "weight": 18.7},
        {"ticker": "GOOGL", "shares": 50, "weight": 12.1},
        {"ticker": "AMZN", "shares": 80, "weight": 11.4},
        {"ticker": "META", "shares": 100, "weight": 10.0},
    ]

    bubbles = []
    for holding in holdings:
        company = next((c for c in COMPANIES if c["ticker"] == holding["ticker"]), None)
        if company:
            bubbles.append({
                "ticker": company["ticker"],
                "name": company["name"],
                "x": company["pe"],
                "y": company["growth"],
                "size": holding["weight"],
                "color": SECTOR_COLORS.get(company["sector"], "#6B7280"),
                "sector": company["sector"],
                "shares": holding["shares"],
                "weight": holding["weight"],
            })

    return {
        "chart_type": "portfolio_bubble",
        "user_id": user_id,
        "x_axis": {"metric": "pe_ratio", "label": "P/E Ratio"},
        "y_axis": {"metric": "growth", "label": "Revenue Growth (%)"},
        "size": {"metric": "weight", "label": "Portfolio Weight (%)"},
        "data": bubbles,
        "total_positions": len(bubbles),
    }
