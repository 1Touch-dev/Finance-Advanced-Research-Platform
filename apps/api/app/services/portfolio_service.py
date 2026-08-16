"""
Portfolio Service (Band C #32)
--------------------------------------------------------------------------------
Provides comprehensive portfolio tracking with:
- Holdings with market values
- P&L calculations (unrealized, realized)
- Performance metrics (daily, total return)
- Sector/industry breakdown
- Risk metrics integration
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AssetClass(Enum):
    EQUITY = "equity"
    ETF = "etf"
    FIXED_INCOME = "fixed_income"
    CRYPTO = "crypto"
    CASH = "cash"
    OTHER = "other"


@dataclass
class Holding:
    """Individual position in a portfolio."""
    ticker: str
    quantity: float
    cost_basis: float  # Per share
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    weight: float  # Portfolio weight
    sector: Optional[str] = None
    industry: Optional[str] = None
    asset_class: str = "equity"
    company_name: Optional[str] = None
    day_change: float = 0.0
    day_change_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "quantity": self.quantity,
            "cost_basis": round(self.cost_basis, 2),
            "current_price": round(self.current_price, 2),
            "market_value": round(self.market_value, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 2),
            "weight": round(self.weight * 100, 2),
            "sector": self.sector,
            "industry": self.industry,
            "asset_class": self.asset_class,
            "company_name": self.company_name,
            "day_change": round(self.day_change, 2),
            "day_change_pct": round(self.day_change_pct, 2),
        }


@dataclass
class SectorAllocation:
    """Sector weight in portfolio."""
    sector: str
    weight: float
    market_value: float
    holdings_count: int
    day_change: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector": self.sector,
            "weight": round(self.weight * 100, 2),
            "market_value": round(self.market_value, 2),
            "holdings_count": self.holdings_count,
            "day_change": round(self.day_change, 2),
        }


@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics."""
    total_market_value: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    day_change: float
    day_change_pct: float
    holdings_count: int
    positive_positions: int
    negative_positions: int
    largest_position_weight: float
    top_gainer: Optional[str] = None
    top_gainer_pct: float = 0.0
    top_loser: Optional[str] = None
    top_loser_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_market_value": round(self.total_market_value, 2),
            "total_cost_basis": round(self.total_cost_basis, 2),
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 2),
            "total_unrealized_pnl_pct": round(self.total_unrealized_pnl_pct, 2),
            "day_change": round(self.day_change, 2),
            "day_change_pct": round(self.day_change_pct, 2),
            "holdings_count": self.holdings_count,
            "positive_positions": self.positive_positions,
            "negative_positions": self.negative_positions,
            "largest_position_weight": round(self.largest_position_weight * 100, 2),
            "top_gainer": self.top_gainer,
            "top_gainer_pct": round(self.top_gainer_pct, 2),
            "top_loser": self.top_loser,
            "top_loser_pct": round(self.top_loser_pct, 2),
        }


@dataclass
class PortfolioSummary:
    """Full portfolio summary."""
    portfolio_id: int
    name: str
    base_currency: str
    thesis: Optional[str]
    holdings: List[Holding]
    sector_allocation: List[SectorAllocation]
    performance: PerformanceMetrics
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "base_currency": self.base_currency,
            "thesis": self.thesis,
            "holdings": [h.to_dict() for h in self.holdings],
            "sector_allocation": [s.to_dict() for s in self.sector_allocation],
            "performance": self.performance.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Sector mapping for common tickers (simulated - in production would use API)
_SECTOR_MAP = {
    "AAPL": ("Technology", "Consumer Electronics"),
    "MSFT": ("Technology", "Software"),
    "GOOGL": ("Technology", "Internet Services"),
    "AMZN": ("Consumer Discretionary", "E-Commerce"),
    "META": ("Technology", "Social Media"),
    "NVDA": ("Technology", "Semiconductors"),
    "TSLA": ("Consumer Discretionary", "Electric Vehicles"),
    "AMD": ("Technology", "Semiconductors"),
    "JPM": ("Financials", "Banks"),
    "BAC": ("Financials", "Banks"),
    "WFC": ("Financials", "Banks"),
    "GS": ("Financials", "Investment Banking"),
    "MS": ("Financials", "Investment Banking"),
    "JNJ": ("Healthcare", "Pharmaceuticals"),
    "PFE": ("Healthcare", "Pharmaceuticals"),
    "UNH": ("Healthcare", "Insurance"),
    "XOM": ("Energy", "Oil & Gas"),
    "CVX": ("Energy", "Oil & Gas"),
    "PG": ("Consumer Staples", "Household Products"),
    "KO": ("Consumer Staples", "Beverages"),
    "PEP": ("Consumer Staples", "Beverages"),
    "WMT": ("Consumer Staples", "Retail"),
    "HD": ("Consumer Discretionary", "Home Improvement"),
    "DIS": ("Communication Services", "Entertainment"),
    "NFLX": ("Communication Services", "Streaming"),
    "V": ("Financials", "Payment Processing"),
    "MA": ("Financials", "Payment Processing"),
    "INTC": ("Technology", "Semiconductors"),
    "CRM": ("Technology", "Software"),
    "ORCL": ("Technology", "Software"),
    "IBM": ("Technology", "IT Services"),
    "SPY": ("ETF", "S&P 500 Index"),
    "QQQ": ("ETF", "Nasdaq 100 Index"),
    "IWM": ("ETF", "Russell 2000 Index"),
    "VTI": ("ETF", "Total Stock Market"),
    "BTC": ("Crypto", "Cryptocurrency"),
    "ETH": ("Crypto", "Cryptocurrency"),
}


class PortfolioService:
    """Service for portfolio tracking and analytics."""

    def __init__(self):
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_time: Optional[datetime] = None

    def _get_market_data(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current market data for tickers (simulated for demo)."""
        # In production, would call yfinance or market data API
        # For now, simulate with deterministic prices based on ticker
        import hashlib

        result = {}
        for ticker in tickers:
            # Generate deterministic but realistic prices
            seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
            base_price = 50 + (seed % 500)
            day_change_pct = ((seed % 100) - 50) / 100  # -0.5% to +0.5%

            result[ticker] = {
                "price": base_price,
                "prev_close": base_price / (1 + day_change_pct),
                "day_change": base_price * day_change_pct,
                "day_change_pct": day_change_pct * 100,
            }

        return result

    def _get_sector_info(self, ticker: str) -> tuple:
        """Get sector and industry for a ticker."""
        if ticker in _SECTOR_MAP:
            return _SECTOR_MAP[ticker]
        return ("Other", "Other")

    def calculate_holdings(
        self,
        positions: List[Dict[str, Any]],
    ) -> List[Holding]:
        """Calculate holdings with market values and P&L."""
        if not positions:
            return []

        # Get unique tickers
        tickers = list(set(p["ticker"] for p in positions if p.get("ticker")))
        market_data = self._get_market_data(tickers)

        # Calculate total market value for weights
        holdings_raw = []
        for pos in positions:
            ticker = pos.get("ticker", "UNKNOWN")
            qty = pos.get("qty", 0)
            cost_basis = pos.get("cost_basis", 0)

            data = market_data.get(ticker, {"price": cost_basis, "day_change": 0, "day_change_pct": 0})
            current_price = data["price"]
            market_value = qty * current_price
            cost_total = qty * cost_basis
            unrealized_pnl = market_value - cost_total
            unrealized_pnl_pct = (unrealized_pnl / cost_total * 100) if cost_total else 0

            sector, industry = self._get_sector_info(ticker)

            holdings_raw.append({
                "ticker": ticker,
                "quantity": qty,
                "cost_basis": cost_basis,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "sector": sector,
                "industry": industry,
                "day_change": data.get("day_change", 0) * qty,
                "day_change_pct": data.get("day_change_pct", 0),
            })

        # Calculate weights
        total_value = sum(h["market_value"] for h in holdings_raw)

        holdings = []
        for h in holdings_raw:
            weight = h["market_value"] / total_value if total_value else 0
            holdings.append(Holding(
                ticker=h["ticker"],
                quantity=h["quantity"],
                cost_basis=h["cost_basis"],
                current_price=h["current_price"],
                market_value=h["market_value"],
                unrealized_pnl=h["unrealized_pnl"],
                unrealized_pnl_pct=h["unrealized_pnl_pct"],
                weight=weight,
                sector=h["sector"],
                industry=h["industry"],
                day_change=h["day_change"],
                day_change_pct=h["day_change_pct"],
            ))

        # Sort by market value descending
        holdings.sort(key=lambda x: x.market_value, reverse=True)
        return holdings

    def calculate_sector_allocation(
        self,
        holdings: List[Holding],
    ) -> List[SectorAllocation]:
        """Calculate sector allocation from holdings."""
        sector_data: Dict[str, Dict[str, Any]] = {}

        for h in holdings:
            sector = h.sector or "Other"
            if sector not in sector_data:
                sector_data[sector] = {
                    "market_value": 0,
                    "day_change": 0,
                    "holdings_count": 0,
                }
            sector_data[sector]["market_value"] += h.market_value
            sector_data[sector]["day_change"] += h.day_change
            sector_data[sector]["holdings_count"] += 1

        total_value = sum(s["market_value"] for s in sector_data.values())

        allocations = []
        for sector, data in sector_data.items():
            weight = data["market_value"] / total_value if total_value else 0
            allocations.append(SectorAllocation(
                sector=sector,
                weight=weight,
                market_value=data["market_value"],
                holdings_count=data["holdings_count"],
                day_change=data["day_change"],
            ))

        allocations.sort(key=lambda x: x.weight, reverse=True)
        return allocations

    def calculate_performance(
        self,
        holdings: List[Holding],
    ) -> PerformanceMetrics:
        """Calculate portfolio performance metrics."""
        if not holdings:
            return PerformanceMetrics(
                total_market_value=0,
                total_cost_basis=0,
                total_unrealized_pnl=0,
                total_unrealized_pnl_pct=0,
                day_change=0,
                day_change_pct=0,
                holdings_count=0,
                positive_positions=0,
                negative_positions=0,
                largest_position_weight=0,
            )

        total_market_value = sum(h.market_value for h in holdings)
        total_cost_basis = sum(h.quantity * h.cost_basis for h in holdings)
        total_unrealized_pnl = total_market_value - total_cost_basis
        total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis else 0

        day_change = sum(h.day_change for h in holdings)
        prev_value = total_market_value - day_change
        day_change_pct = (day_change / prev_value * 100) if prev_value else 0

        positive_positions = sum(1 for h in holdings if h.unrealized_pnl >= 0)
        negative_positions = sum(1 for h in holdings if h.unrealized_pnl < 0)
        largest_position_weight = max(h.weight for h in holdings) if holdings else 0

        # Find top gainer and loser
        sorted_by_pnl_pct = sorted(holdings, key=lambda x: x.unrealized_pnl_pct, reverse=True)
        top_gainer = sorted_by_pnl_pct[0].ticker if sorted_by_pnl_pct else None
        top_gainer_pct = sorted_by_pnl_pct[0].unrealized_pnl_pct if sorted_by_pnl_pct else 0
        top_loser = sorted_by_pnl_pct[-1].ticker if sorted_by_pnl_pct else None
        top_loser_pct = sorted_by_pnl_pct[-1].unrealized_pnl_pct if sorted_by_pnl_pct else 0

        return PerformanceMetrics(
            total_market_value=total_market_value,
            total_cost_basis=total_cost_basis,
            total_unrealized_pnl=total_unrealized_pnl,
            total_unrealized_pnl_pct=total_unrealized_pnl_pct,
            day_change=day_change,
            day_change_pct=day_change_pct,
            holdings_count=len(holdings),
            positive_positions=positive_positions,
            negative_positions=negative_positions,
            largest_position_weight=largest_position_weight,
            top_gainer=top_gainer,
            top_gainer_pct=top_gainer_pct,
            top_loser=top_loser,
            top_loser_pct=top_loser_pct,
        )

    def get_portfolio_summary(
        self,
        portfolio_id: int,
        name: str,
        base_currency: str,
        thesis: Optional[str],
        positions: List[Dict[str, Any]],
        created_at: str,
    ) -> PortfolioSummary:
        """Get full portfolio summary with holdings and metrics."""
        holdings = self.calculate_holdings(positions)
        sector_allocation = self.calculate_sector_allocation(holdings)
        performance = self.calculate_performance(holdings)

        return PortfolioSummary(
            portfolio_id=portfolio_id,
            name=name,
            base_currency=base_currency,
            thesis=thesis,
            holdings=holdings,
            sector_allocation=sector_allocation,
            performance=performance,
            created_at=created_at,
            updated_at=datetime.now().isoformat(),
        )


# ── Risk Metrics (#45) ─────────────────────────────────────────────────────────

@dataclass
class RiskMetrics:
    """Portfolio risk metrics."""
    portfolio_id: int
    as_of_date: str

    # Value at Risk (VaR)
    var_95_daily: float  # 95% VaR (daily)
    var_99_daily: float  # 99% VaR (daily)
    var_95_monthly: float  # 95% VaR (monthly)
    var_99_monthly: float  # 99% VaR (monthly)
    var_method: str  # historical, parametric, monte_carlo

    # Beta (market correlation)
    portfolio_beta: float  # vs S&P 500
    weighted_avg_beta: float

    # Volatility metrics
    portfolio_volatility: float  # Annualized std dev
    downside_deviation: float
    sharpe_ratio: float
    sortino_ratio: float

    # Drawdown metrics
    max_drawdown: float  # Maximum peak-to-trough decline
    current_drawdown: float  # Current drawdown from peak
    avg_drawdown: float
    drawdown_duration_days: int  # Days in current drawdown

    # Concentration risk
    top_5_concentration: float  # % in top 5 holdings
    herfindahl_index: float  # Concentration index
    sector_concentration: float  # % in largest sector

    # Correlation
    avg_pairwise_correlation: float
    diversification_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "as_of_date": self.as_of_date,
            "value_at_risk": {
                "var_95_daily": round(self.var_95_daily, 2),
                "var_99_daily": round(self.var_99_daily, 2),
                "var_95_monthly": round(self.var_95_monthly, 2),
                "var_99_monthly": round(self.var_99_monthly, 2),
                "method": self.var_method,
            },
            "beta": {
                "portfolio_beta": round(self.portfolio_beta, 3),
                "weighted_avg_beta": round(self.weighted_avg_beta, 3),
            },
            "volatility": {
                "annualized": round(self.portfolio_volatility * 100, 2),
                "downside_deviation": round(self.downside_deviation * 100, 2),
                "sharpe_ratio": round(self.sharpe_ratio, 3),
                "sortino_ratio": round(self.sortino_ratio, 3),
            },
            "drawdown": {
                "max_drawdown_pct": round(self.max_drawdown * 100, 2),
                "current_drawdown_pct": round(self.current_drawdown * 100, 2),
                "avg_drawdown_pct": round(self.avg_drawdown * 100, 2),
                "duration_days": self.drawdown_duration_days,
            },
            "concentration": {
                "top_5_pct": round(self.top_5_concentration * 100, 2),
                "herfindahl_index": round(self.herfindahl_index, 4),
                "largest_sector_pct": round(self.sector_concentration * 100, 2),
            },
            "diversification": {
                "avg_correlation": round(self.avg_pairwise_correlation, 3),
                "diversification_ratio": round(self.diversification_ratio, 3),
            },
        }


# Simulated beta values for common stocks
_BETA_MAP = {
    "AAPL": 1.28, "MSFT": 1.05, "GOOGL": 1.15, "AMZN": 1.22,
    "META": 1.35, "NVDA": 1.68, "TSLA": 2.05, "AMD": 1.75,
    "JPM": 1.12, "BAC": 1.35, "GS": 1.28, "V": 0.98,
    "MA": 1.05, "JNJ": 0.62, "PFE": 0.68, "UNH": 0.78,
    "XOM": 1.02, "CVX": 1.08, "PG": 0.45, "KO": 0.58,
    "PEP": 0.52, "WMT": 0.48, "HD": 1.12, "DIS": 1.22,
    "NFLX": 1.45, "INTC": 0.95, "CRM": 1.18, "ORCL": 0.92,
    "IBM": 0.78, "SPY": 1.00, "QQQ": 1.10, "IWM": 1.25,
}


def calculate_risk_metrics(
    portfolio_id: int,
    holdings: List[Holding],
    total_value: float,
) -> RiskMetrics:
    """
    Calculate comprehensive risk metrics for a portfolio.

    Includes VaR, beta, volatility, drawdown, and concentration metrics.
    """
    import math
    import random

    today = datetime.now().strftime("%Y-%m-%d")

    if not holdings or total_value == 0:
        return RiskMetrics(
            portfolio_id=portfolio_id,
            as_of_date=today,
            var_95_daily=0, var_99_daily=0, var_95_monthly=0, var_99_monthly=0,
            var_method="parametric",
            portfolio_beta=0, weighted_avg_beta=0,
            portfolio_volatility=0, downside_deviation=0,
            sharpe_ratio=0, sortino_ratio=0,
            max_drawdown=0, current_drawdown=0, avg_drawdown=0, drawdown_duration_days=0,
            top_5_concentration=0, herfindahl_index=0, sector_concentration=0,
            avg_pairwise_correlation=0, diversification_ratio=0,
        )

    # Calculate weighted average beta
    total_weight = sum(h.weight for h in holdings)
    weighted_beta = sum(
        h.weight * _BETA_MAP.get(h.ticker, 1.0) for h in holdings
    ) / total_weight if total_weight > 0 else 1.0

    # Simulate portfolio volatility based on holdings
    # More holdings = lower volatility due to diversification
    base_vol = 0.18  # 18% base volatility
    diversification_benefit = max(0.5, 1 - len(holdings) * 0.03)  # 3% reduction per holding
    portfolio_volatility = base_vol * diversification_benefit * weighted_beta

    # Calculate VaR (parametric method)
    # VaR = Portfolio Value * Z-score * Volatility * sqrt(time)
    z_95 = 1.645
    z_99 = 2.326
    daily_vol = portfolio_volatility / math.sqrt(252)  # Daily vol

    var_95_daily = total_value * z_95 * daily_vol
    var_99_daily = total_value * z_99 * daily_vol
    var_95_monthly = total_value * z_95 * portfolio_volatility * math.sqrt(21/252)
    var_99_monthly = total_value * z_99 * portfolio_volatility * math.sqrt(21/252)

    # Risk-adjusted returns (simulated)
    risk_free_rate = 0.05  # 5% risk-free rate
    expected_return = 0.10 + random.uniform(-0.05, 0.05)  # ~10% expected return
    downside_deviation = portfolio_volatility * 0.7  # Lower than total vol

    sharpe_ratio = (expected_return - risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
    sortino_ratio = (expected_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0

    # Drawdown metrics (simulated)
    max_drawdown = random.uniform(0.10, 0.25)  # 10-25% max drawdown
    current_drawdown = random.uniform(0, max_drawdown * 0.5)  # Currently up to half of max
    avg_drawdown = max_drawdown * 0.4
    drawdown_duration = random.randint(0, 60) if current_drawdown > 0 else 0

    # Concentration metrics
    sorted_holdings = sorted(holdings, key=lambda x: x.weight, reverse=True)
    top_5_weight = sum(h.weight for h in sorted_holdings[:5])
    hhi = sum(h.weight ** 2 for h in holdings)  # Herfindahl index

    # Sector concentration
    sector_weights: Dict[str, float] = {}
    for h in holdings:
        sector = h.sector or "Other"
        sector_weights[sector] = sector_weights.get(sector, 0) + h.weight
    max_sector_weight = max(sector_weights.values()) if sector_weights else 0

    # Correlation and diversification (simulated)
    n = len(holdings)
    avg_correlation = 0.35 + random.uniform(-0.1, 0.1)  # Typical equity correlation
    diversification_ratio = 1 / math.sqrt(n) if n > 0 else 1

    return RiskMetrics(
        portfolio_id=portfolio_id,
        as_of_date=today,
        var_95_daily=var_95_daily,
        var_99_daily=var_99_daily,
        var_95_monthly=var_95_monthly,
        var_99_monthly=var_99_monthly,
        var_method="parametric",
        portfolio_beta=weighted_beta,
        weighted_avg_beta=weighted_beta,
        portfolio_volatility=portfolio_volatility,
        downside_deviation=downside_deviation,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown,
        current_drawdown=current_drawdown,
        avg_drawdown=avg_drawdown,
        drawdown_duration_days=drawdown_duration,
        top_5_concentration=top_5_weight,
        herfindahl_index=hhi,
        sector_concentration=max_sector_weight,
        avg_pairwise_correlation=avg_correlation,
        diversification_ratio=diversification_ratio,
    )


# Singleton instance
_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get or create portfolio service singleton."""
    global _service
    if _service is None:
        _service = PortfolioService()
    return _service
