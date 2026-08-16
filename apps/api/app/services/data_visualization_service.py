"""
Data Visualization Service (James J2)
Visualization data generators for charts
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random
import math


@dataclass
class ChartDataPoint:
    """Generic chart data point"""
    label: str
    value: float
    color: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "value": self.value,
            "color": self.color,
            "metadata": self.metadata or {},
        }


# Color palettes
CHART_COLORS = [
    "#3B82F6",  # Blue
    "#10B981",  # Green
    "#F59E0B",  # Yellow
    "#EF4444",  # Red
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#F97316",  # Orange
]

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


def get_sector_breakdown(tickers: Optional[List[str]] = None) -> Dict[str, Any]:
    """Get sector breakdown for pie/donut chart"""
    sectors = [
        {"name": "Technology", "value": 35.5, "count": 8},
        {"name": "Healthcare", "value": 18.2, "count": 5},
        {"name": "Financial", "value": 15.8, "count": 6},
        {"name": "Consumer", "value": 12.3, "count": 4},
        {"name": "Energy", "value": 8.5, "count": 3},
        {"name": "Industrial", "value": 5.2, "count": 2},
        {"name": "Other", "value": 4.5, "count": 3},
    ]

    for sector in sectors:
        sector["color"] = SECTOR_COLORS.get(sector["name"], "#6B7280")

    return {
        "chart_type": "pie",
        "title": "Portfolio Sector Breakdown",
        "data": sectors,
        "total_value": sum(s["value"] for s in sectors),
    }


def get_performance_comparison(
    tickers: List[str],
    period: str = "1Y",
) -> Dict[str, Any]:
    """Get performance comparison bar chart data"""
    period_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "YTD": 200}
    days = period_days.get(period, 365)

    data = []
    for i, ticker in enumerate(tickers[:10]):
        # Generate mock performance
        base_return = random.uniform(-20, 50)
        data.append({
            "ticker": ticker.upper(),
            "return": round(base_return, 2),
            "color": CHART_COLORS[i % len(CHART_COLORS)],
            "positive": base_return > 0,
        })

    # Sort by return
    data.sort(key=lambda x: x["return"], reverse=True)

    return {
        "chart_type": "bar",
        "title": f"Performance Comparison ({period})",
        "period": period,
        "data": data,
        "benchmark": {"ticker": "SPY", "return": round(random.uniform(5, 15), 2)},
    }


def get_time_series(
    ticker: str,
    period: str = "1Y",
    interval: str = "daily",
) -> Dict[str, Any]:
    """Get time series data for line chart"""
    period_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "5Y": 1825}
    days = period_days.get(period, 365)

    if interval == "weekly":
        num_points = days // 7
    elif interval == "monthly":
        num_points = days // 30
    else:
        num_points = min(days, 252)  # Trading days

    base_price = 100.0
    data = []
    base_date = datetime.now() - timedelta(days=days)

    for i in range(num_points):
        date = base_date + timedelta(days=(days * i // num_points))
        # Random walk with slight upward bias
        change = random.gauss(0.1, 2)
        base_price = max(50, base_price + change)

        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "price": round(base_price, 2),
            "volume": random.randint(1000000, 50000000),
        })

    return {
        "chart_type": "line",
        "title": f"{ticker.upper()} Price History",
        "ticker": ticker.upper(),
        "period": period,
        "interval": interval,
        "data": data,
        "summary": {
            "start_price": data[0]["price"],
            "end_price": data[-1]["price"],
            "high": max(d["price"] for d in data),
            "low": min(d["price"] for d in data),
            "change_percent": round(((data[-1]["price"] / data[0]["price"]) - 1) * 100, 2),
        },
    }


def get_correlation_matrix(tickers: List[str]) -> Dict[str, Any]:
    """Get correlation matrix heatmap data"""
    tickers = [t.upper() for t in tickers[:10]]
    n = len(tickers)

    matrix = []
    for i, ticker1 in enumerate(tickers):
        row = []
        for j, ticker2 in enumerate(tickers):
            if i == j:
                corr = 1.0
            elif i > j:
                # Mirror the correlation
                corr = matrix[j][i]
            else:
                # Generate random correlation
                corr = round(random.uniform(0.2, 0.95), 2)
            row.append(corr)
        matrix.append(row)

    return {
        "chart_type": "heatmap",
        "title": "Correlation Matrix",
        "tickers": tickers,
        "matrix": matrix,
        "color_scale": {
            "min": -1,
            "max": 1,
            "colors": ["#EF4444", "#FFFFFF", "#10B981"],
        },
    }


def get_treemap_data(
    group_by: str = "sector",
) -> Dict[str, Any]:
    """Get treemap data for hierarchical visualization"""
    if group_by == "sector":
        data = [
            {
                "name": "Technology",
                "value": 450000,
                "color": SECTOR_COLORS["Technology"],
                "children": [
                    {"name": "NVDA", "value": 150000, "change": 125.5},
                    {"name": "AAPL", "value": 120000, "change": 15.2},
                    {"name": "MSFT", "value": 100000, "change": 22.3},
                    {"name": "GOOGL", "value": 80000, "change": 18.7},
                ],
            },
            {
                "name": "Healthcare",
                "value": 200000,
                "color": SECTOR_COLORS["Healthcare"],
                "children": [
                    {"name": "UNH", "value": 80000, "change": 8.5},
                    {"name": "JNJ", "value": 70000, "change": 3.2},
                    {"name": "PFE", "value": 50000, "change": -5.1},
                ],
            },
            {
                "name": "Financial",
                "value": 180000,
                "color": SECTOR_COLORS["Financial"],
                "children": [
                    {"name": "JPM", "value": 90000, "change": 12.3},
                    {"name": "BAC", "value": 50000, "change": 8.7},
                    {"name": "GS", "value": 40000, "change": 15.2},
                ],
            },
        ]
    else:
        data = [
            {
                "name": "Large Cap",
                "value": 600000,
                "color": "#3B82F6",
                "children": [
                    {"name": "AAPL", "value": 200000, "change": 15.2},
                    {"name": "MSFT", "value": 180000, "change": 22.3},
                    {"name": "GOOGL", "value": 120000, "change": 18.7},
                    {"name": "AMZN", "value": 100000, "change": 25.5},
                ],
            },
            {
                "name": "Mid Cap",
                "value": 200000,
                "color": "#10B981",
                "children": [
                    {"name": "CRM", "value": 80000, "change": 28.3},
                    {"name": "SNOW", "value": 70000, "change": -12.5},
                    {"name": "NET", "value": 50000, "change": 45.2},
                ],
            },
        ]

    return {
        "chart_type": "treemap",
        "title": f"Portfolio by {group_by.title()}",
        "group_by": group_by,
        "data": data,
        "total_value": sum(d["value"] for d in data),
    }


def get_scatter_plot(
    x_metric: str = "market_cap",
    y_metric: str = "pe_ratio",
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get scatter plot data"""
    default_tickers = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "JPM", "UNH", "V"]
    tickers = tickers or default_tickers

    data = []
    for ticker in tickers:
        data.append({
            "ticker": ticker.upper(),
            "x": round(random.uniform(50, 3000), 1),  # Market cap in B
            "y": round(random.uniform(10, 80), 1),  # PE ratio
            "size": round(random.uniform(10, 100), 1),  # Volume or weight
            "color": random.choice(CHART_COLORS),
            "sector": random.choice(list(SECTOR_COLORS.keys())),
        })

    return {
        "chart_type": "scatter",
        "title": f"{x_metric.replace('_', ' ').title()} vs {y_metric.replace('_', ' ').title()}",
        "x_axis": {"label": x_metric.replace("_", " ").title(), "unit": "B"},
        "y_axis": {"label": y_metric.replace("_", " ").title(), "unit": "x"},
        "data": data,
    }


def get_candlestick_data(
    ticker: str,
    period: str = "3M",
) -> Dict[str, Any]:
    """Get candlestick chart data"""
    period_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 252}
    days = period_days.get(period, 90)

    base_price = 100.0
    data = []
    base_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        date = base_date + timedelta(days=i)
        # Skip weekends
        if date.weekday() >= 5:
            continue

        # Generate OHLC
        open_price = base_price + random.uniform(-1, 1)
        change = random.gauss(0.1, 2)
        close_price = open_price + change
        high_price = max(open_price, close_price) + random.uniform(0, 2)
        low_price = min(open_price, close_price) - random.uniform(0, 2)

        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": random.randint(1000000, 50000000),
        })

        base_price = close_price

    return {
        "chart_type": "candlestick",
        "title": f"{ticker.upper()} Price Chart",
        "ticker": ticker.upper(),
        "period": period,
        "data": data,
    }


def get_area_chart(
    tickers: List[str],
    stacked: bool = True,
    period: str = "1Y",
) -> Dict[str, Any]:
    """Get stacked area chart data"""
    period_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}
    days = period_days.get(period, 365)
    num_points = min(days, 52)  # Weekly points

    series = []
    for i, ticker in enumerate(tickers[:5]):
        base_value = random.uniform(10000, 50000)
        data = []
        base_date = datetime.now() - timedelta(days=days)

        for j in range(num_points):
            date = base_date + timedelta(days=(days * j // num_points))
            change = random.uniform(-500, 800)
            base_value = max(5000, base_value + change)
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "value": round(base_value, 2),
            })

        series.append({
            "ticker": ticker.upper(),
            "color": CHART_COLORS[i % len(CHART_COLORS)],
            "data": data,
        })

    return {
        "chart_type": "area",
        "title": "Portfolio Value Over Time",
        "stacked": stacked,
        "period": period,
        "series": series,
    }


def get_radar_chart(ticker: str) -> Dict[str, Any]:
    """Get radar chart data for multi-dimensional analysis"""
    metrics = [
        {"name": "Value", "score": random.randint(40, 95)},
        {"name": "Growth", "score": random.randint(40, 95)},
        {"name": "Profitability", "score": random.randint(40, 95)},
        {"name": "Momentum", "score": random.randint(40, 95)},
        {"name": "Quality", "score": random.randint(40, 95)},
        {"name": "Safety", "score": random.randint(40, 95)},
    ]

    return {
        "chart_type": "radar",
        "title": f"{ticker.upper()} Factor Analysis",
        "ticker": ticker.upper(),
        "metrics": metrics,
        "max_score": 100,
        "overall_score": round(sum(m["score"] for m in metrics) / len(metrics), 1),
    }


def get_histogram(
    metric: str = "returns",
    period: str = "1Y",
) -> Dict[str, Any]:
    """Get histogram data for distribution analysis"""
    # Generate return distribution
    num_samples = 252 if period == "1Y" else 126

    returns = [random.gauss(0.05, 2) for _ in range(num_samples)]

    # Create bins
    min_val = min(returns)
    max_val = max(returns)
    num_bins = 20
    bin_width = (max_val - min_val) / num_bins

    bins = []
    for i in range(num_bins):
        bin_start = min_val + i * bin_width
        bin_end = bin_start + bin_width
        count = sum(1 for r in returns if bin_start <= r < bin_end)
        bins.append({
            "range": f"{round(bin_start, 1)} to {round(bin_end, 1)}",
            "start": round(bin_start, 2),
            "end": round(bin_end, 2),
            "count": count,
            "frequency": round(count / num_samples * 100, 1),
        })

    return {
        "chart_type": "histogram",
        "title": f"Daily {metric.title()} Distribution",
        "metric": metric,
        "period": period,
        "bins": bins,
        "statistics": {
            "mean": round(sum(returns) / len(returns), 3),
            "std": round((sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns))**0.5, 3),
            "min": round(min(returns), 3),
            "max": round(max(returns), 3),
            "skewness": round(random.uniform(-0.5, 0.5), 3),
        },
    }


def get_gauge_chart(
    metric: str = "portfolio_health",
    value: Optional[float] = None,
) -> Dict[str, Any]:
    """Get gauge chart data"""
    if value is None:
        value = random.uniform(40, 95)

    zones = [
        {"min": 0, "max": 30, "color": "#EF4444", "label": "Poor"},
        {"min": 30, "max": 50, "color": "#F59E0B", "label": "Fair"},
        {"min": 50, "max": 70, "color": "#FBBF24", "label": "Good"},
        {"min": 70, "max": 85, "color": "#10B981", "label": "Very Good"},
        {"min": 85, "max": 100, "color": "#059669", "label": "Excellent"},
    ]

    current_zone = next((z for z in zones if z["min"] <= value < z["max"]), zones[-1])

    return {
        "chart_type": "gauge",
        "title": metric.replace("_", " ").title(),
        "value": round(value, 1),
        "max_value": 100,
        "zones": zones,
        "current_zone": current_zone["label"],
        "color": current_zone["color"],
    }


def get_waterfall_chart(ticker: str) -> Dict[str, Any]:
    """Get waterfall chart data for performance attribution"""
    components = [
        {"name": "Starting Value", "value": 100000, "type": "start"},
        {"name": "Price Change", "value": 15000, "type": "positive"},
        {"name": "Dividends", "value": 2500, "type": "positive"},
        {"name": "Fees", "value": -500, "type": "negative"},
        {"name": "Currency", "value": -1200, "type": "negative"},
        {"name": "Rebalancing", "value": 800, "type": "positive"},
        {"name": "Ending Value", "value": 116600, "type": "end"},
    ]

    running_total = 0
    for comp in components:
        if comp["type"] == "start":
            comp["start"] = 0
            comp["end"] = comp["value"]
            running_total = comp["value"]
        elif comp["type"] == "end":
            comp["start"] = 0
            comp["end"] = comp["value"]
        else:
            comp["start"] = running_total
            running_total += comp["value"]
            comp["end"] = running_total

    return {
        "chart_type": "waterfall",
        "title": f"{ticker.upper()} Performance Attribution",
        "ticker": ticker.upper(),
        "data": components,
        "total_change": components[-1]["value"] - components[0]["value"],
        "total_change_percent": round(((components[-1]["value"] / components[0]["value"]) - 1) * 100, 2),
    }
