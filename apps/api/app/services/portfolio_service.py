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

    def _is_cache_valid(self) -> bool:
        """Check if price cache is still within 5-minute TTL."""
        if not self._cache_time or not self._price_cache:
            return False
        return (datetime.now() - self._cache_time).total_seconds() < 300

    def _get_market_data(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current market data for tickers using yfinance with 5-min cache."""
        import yfinance as yf

        if self._is_cache_valid():
            missing = [t for t in tickers if t not in self._price_cache]
            if not missing:
                return {t: self._price_cache[t] for t in tickers}
        else:
            missing = tickers

        try:
            data = yf.download(
                missing,
                period="2d",
                progress=False,
                group_by="ticker" if len(missing) > 1 else "column",
                threads=True,
            )

            for ticker in missing:
                try:
                    if len(missing) == 1:
                        ticker_data = data
                    else:
                        ticker_data = data[ticker]

                    closes = ticker_data["Close"].dropna()
                    if len(closes) < 1:
                        continue

                    current_price = float(closes.iloc[-1])
                    prev_close = float(closes.iloc[-2]) if len(closes) >= 2 else current_price
                    day_change = current_price - prev_close
                    day_change_pct = (day_change / prev_close * 100) if prev_close else 0

                    self._price_cache[ticker] = {
                        "price": current_price,
                        "prev_close": prev_close,
                        "day_change": day_change,
                        "day_change_pct": day_change_pct,
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse market data for {ticker}: {e}")
                    continue

            self._cache_time = datetime.now()

        except Exception as e:
            logger.error(f"yfinance download failed: {e}")

        return {t: self._price_cache[t] for t in tickers if t in self._price_cache}

    def _get_sector_info(self, ticker: str) -> tuple:
        """Get sector and industry for a ticker using yfinance, falling back to static map."""
        if ticker in _SECTOR_MAP:
            return _SECTOR_MAP[ticker]

        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            sector = info.get("sector")
            industry = info.get("industry")
            if sector:
                _SECTOR_MAP[ticker] = (sector, industry or "Other")
                return (sector, industry or "Other")
        except Exception as e:
            logger.warning(f"Failed to fetch sector info for {ticker}: {e}")

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

    # Risk-adjusted returns
    # TODO: compute from real historical data via yfinance
    risk_free_rate = 0.05  # 5% risk-free rate
    expected_return = None  # Needs real historical return series
    downside_deviation = None  # Needs real downside return series
    sharpe_ratio = 0.0
    sortino_ratio = 0.0

    # Drawdown metrics
    # TODO: compute from real historical price series
    max_drawdown = None
    current_drawdown = None
    avg_drawdown = None
    drawdown_duration = 0

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

    # Correlation and diversification
    # TODO: compute from real return correlation matrix
    n = len(holdings)
    avg_correlation = None
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
        downside_deviation=downside_deviation or 0.0,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown or 0.0,
        current_drawdown=current_drawdown or 0.0,
        avg_drawdown=avg_drawdown or 0.0,
        drawdown_duration_days=drawdown_duration,
        top_5_concentration=top_5_weight,
        herfindahl_index=hhi,
        sector_concentration=max_sector_weight,
        avg_pairwise_correlation=avg_correlation or 0.0,
        diversification_ratio=diversification_ratio,
    )


# ── Position-level P&L (#41) ──────────────────────────────────────────────────

@dataclass
class PositionPnL:
    """Detailed P&L metrics for a single position."""
    position_id: int
    ticker: str
    company_name: Optional[str]
    sector: Optional[str]

    # Current position
    quantity: float
    cost_basis: float
    current_price: float
    market_value: float

    # Unrealized P&L
    unrealized_pnl: float
    unrealized_pnl_pct: float

    # Period returns
    day_pnl: float
    day_pnl_pct: float
    week_pnl: float
    week_pnl_pct: float
    month_pnl: float
    month_pnl_pct: float
    ytd_pnl: float
    ytd_pnl_pct: float

    # Cost tracking
    total_cost: float
    avg_cost_per_share: float

    # Realized P&L (from closed positions)
    realized_pnl: float
    total_pnl: float  # realized + unrealized

    # Timestamps
    first_purchase_date: Optional[str]
    last_activity_date: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "position": {
                "quantity": self.quantity,
                "cost_basis": round(self.cost_basis, 2),
                "current_price": round(self.current_price, 2),
                "market_value": round(self.market_value, 2),
            },
            "pnl": {
                "unrealized": round(self.unrealized_pnl, 2),
                "unrealized_pct": round(self.unrealized_pnl_pct, 2),
                "realized": round(self.realized_pnl, 2),
                "total": round(self.total_pnl, 2),
            },
            "period_returns": {
                "day": {"pnl": round(self.day_pnl, 2), "pct": round(self.day_pnl_pct, 2)},
                "week": {"pnl": round(self.week_pnl, 2), "pct": round(self.week_pnl_pct, 2)},
                "month": {"pnl": round(self.month_pnl, 2), "pct": round(self.month_pnl_pct, 2)},
                "ytd": {"pnl": round(self.ytd_pnl, 2), "pct": round(self.ytd_pnl_pct, 2)},
            },
            "cost_tracking": {
                "total_cost": round(self.total_cost, 2),
                "avg_cost_per_share": round(self.avg_cost_per_share, 2),
            },
            "dates": {
                "first_purchase": self.first_purchase_date,
                "last_activity": self.last_activity_date,
            },
        }


@dataclass
class PortfolioPnLSummary:
    """Summary of P&L for all positions in a portfolio."""
    portfolio_id: int
    portfolio_name: str
    as_of_date: str

    # Totals
    total_market_value: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    total_pnl: float

    # Period totals
    day_pnl: float
    week_pnl: float
    month_pnl: float
    ytd_pnl: float

    # Position details
    positions: List[PositionPnL]

    # Statistics
    winners_count: int
    losers_count: int
    best_performer: Optional[str]
    best_performer_pct: float
    worst_performer: Optional[str]
    worst_performer_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "portfolio_name": self.portfolio_name,
            "as_of_date": self.as_of_date,
            "summary": {
                "total_market_value": round(self.total_market_value, 2),
                "total_cost_basis": round(self.total_cost_basis, 2),
                "total_unrealized_pnl": round(self.total_unrealized_pnl, 2),
                "total_realized_pnl": round(self.total_realized_pnl, 2),
                "total_pnl": round(self.total_pnl, 2),
            },
            "period_totals": {
                "day": round(self.day_pnl, 2),
                "week": round(self.week_pnl, 2),
                "month": round(self.month_pnl, 2),
                "ytd": round(self.ytd_pnl, 2),
            },
            "statistics": {
                "winners": self.winners_count,
                "losers": self.losers_count,
                "best_performer": self.best_performer,
                "best_performer_pct": round(self.best_performer_pct, 2),
                "worst_performer": self.worst_performer,
                "worst_performer_pct": round(self.worst_performer_pct, 2),
            },
            "positions": [p.to_dict() for p in self.positions],
        }


# Simulated price history for period returns
_PRICE_HISTORY = {
    # ticker: {day_ago, week_ago, month_ago, ytd_start}
    "AAPL": {"day": 0.98, "week": 0.95, "month": 0.92, "ytd": 0.85},
    "MSFT": {"day": 0.99, "week": 0.97, "month": 0.94, "ytd": 0.88},
    "GOOGL": {"day": 1.01, "week": 0.98, "month": 0.96, "ytd": 0.90},
    "NVDA": {"day": 0.97, "week": 0.92, "month": 0.85, "ytd": 0.65},
    "TSLA": {"day": 1.02, "week": 1.05, "month": 0.90, "ytd": 0.75},
    "AMD": {"day": 0.98, "week": 0.94, "month": 0.88, "ytd": 0.70},
    "META": {"day": 0.99, "week": 0.96, "month": 0.93, "ytd": 0.82},
    "AMZN": {"day": 1.00, "week": 0.98, "month": 0.95, "ytd": 0.87},
    "JPM": {"day": 1.01, "week": 1.00, "month": 0.98, "ytd": 0.92},
    "BAC": {"day": 1.00, "week": 0.99, "month": 0.97, "ytd": 0.90},
}


def _get_price_history_factors(ticker: str) -> Dict[str, float]:
    """Get historical price factors for a ticker (current price / historical price)."""
    if ticker in _PRICE_HISTORY:
        return _PRICE_HISTORY[ticker]
    # TODO: needs real historical data from yfinance
    # For now return neutral factors (no change) for unknown tickers
    return {
        "day": 1.0,
        "week": 1.0,
        "month": 1.0,
        "ytd": 1.0,
    }


def calculate_position_pnl(
    position_id: int,
    ticker: str,
    quantity: float,
    cost_basis: float,
    notes: Optional[str] = None,
) -> PositionPnL:
    """
    Calculate detailed P&L for a single position.

    Returns comprehensive P&L metrics including period returns.
    """
    service = get_portfolio_service()

    # Get current market data
    market_data = service._get_market_data([ticker])
    data = market_data.get(ticker, {"price": cost_basis, "day_change": 0, "day_change_pct": 0})
    current_price = data["price"]

    # Get sector info
    sector, industry = service._get_sector_info(ticker)

    # Calculate basic P&L
    market_value = quantity * current_price
    total_cost = quantity * cost_basis
    unrealized_pnl = market_value - total_cost
    unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost else 0

    # Get historical price factors
    factors = _get_price_history_factors(ticker)

    # Calculate period P&L
    # Day P&L
    prev_day_price = current_price * factors["day"]
    day_pnl = quantity * (current_price - prev_day_price)
    day_pnl_pct = ((current_price - prev_day_price) / prev_day_price * 100) if prev_day_price else 0

    # Week P&L
    prev_week_price = current_price * factors["week"]
    week_pnl = quantity * (current_price - prev_week_price)
    week_pnl_pct = ((current_price - prev_week_price) / prev_week_price * 100) if prev_week_price else 0

    # Month P&L
    prev_month_price = current_price * factors["month"]
    month_pnl = quantity * (current_price - prev_month_price)
    month_pnl_pct = ((current_price - prev_month_price) / prev_month_price * 100) if prev_month_price else 0

    # YTD P&L
    ytd_start_price = current_price * factors["ytd"]
    ytd_pnl = quantity * (current_price - ytd_start_price)
    ytd_pnl_pct = ((current_price - ytd_start_price) / ytd_start_price * 100) if ytd_start_price else 0

    # Company name (simulated)
    company_names = {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "GOOGL": "Alphabet Inc.",
        "NVDA": "NVIDIA Corporation",
        "TSLA": "Tesla, Inc.",
        "AMD": "Advanced Micro Devices",
        "META": "Meta Platforms, Inc.",
        "AMZN": "Amazon.com, Inc.",
        "JPM": "JPMorgan Chase & Co.",
        "BAC": "Bank of America Corporation",
    }

    return PositionPnL(
        position_id=position_id,
        ticker=ticker,
        company_name=company_names.get(ticker, f"{ticker} Corp"),
        sector=sector,
        quantity=quantity,
        cost_basis=cost_basis,
        current_price=current_price,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_pct=unrealized_pnl_pct,
        day_pnl=day_pnl,
        day_pnl_pct=day_pnl_pct,
        week_pnl=week_pnl,
        week_pnl_pct=week_pnl_pct,
        month_pnl=month_pnl,
        month_pnl_pct=month_pnl_pct,
        ytd_pnl=ytd_pnl,
        ytd_pnl_pct=ytd_pnl_pct,
        total_cost=total_cost,
        avg_cost_per_share=cost_basis,
        realized_pnl=0,  # Would track from closed trades
        total_pnl=unrealized_pnl,  # unrealized + realized
        first_purchase_date=None,  # Would come from transaction history
        last_activity_date=datetime.now().strftime("%Y-%m-%d"),
    )


def calculate_portfolio_pnl_summary(
    portfolio_id: int,
    portfolio_name: str,
    positions: List[Dict[str, Any]],
) -> PortfolioPnLSummary:
    """
    Calculate P&L summary for all positions in a portfolio.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    if not positions:
        return PortfolioPnLSummary(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio_name,
            as_of_date=today,
            total_market_value=0,
            total_cost_basis=0,
            total_unrealized_pnl=0,
            total_realized_pnl=0,
            total_pnl=0,
            day_pnl=0,
            week_pnl=0,
            month_pnl=0,
            ytd_pnl=0,
            positions=[],
            winners_count=0,
            losers_count=0,
            best_performer=None,
            best_performer_pct=0,
            worst_performer=None,
            worst_performer_pct=0,
        )

    # Calculate P&L for each position
    position_pnls = []
    for pos in positions:
        pnl = calculate_position_pnl(
            position_id=pos.get("id", 0),
            ticker=pos.get("ticker", "UNKNOWN"),
            quantity=pos.get("qty", 0),
            cost_basis=pos.get("cost_basis", 0),
            notes=pos.get("notes"),
        )
        position_pnls.append(pnl)

    # Calculate totals
    total_market_value = sum(p.market_value for p in position_pnls)
    total_cost_basis = sum(p.total_cost for p in position_pnls)
    total_unrealized_pnl = sum(p.unrealized_pnl for p in position_pnls)
    total_realized_pnl = sum(p.realized_pnl for p in position_pnls)

    day_pnl = sum(p.day_pnl for p in position_pnls)
    week_pnl = sum(p.week_pnl for p in position_pnls)
    month_pnl = sum(p.month_pnl for p in position_pnls)
    ytd_pnl = sum(p.ytd_pnl for p in position_pnls)

    # Statistics
    winners = [p for p in position_pnls if p.unrealized_pnl >= 0]
    losers = [p for p in position_pnls if p.unrealized_pnl < 0]

    sorted_by_pct = sorted(position_pnls, key=lambda x: x.unrealized_pnl_pct, reverse=True)
    best = sorted_by_pct[0] if sorted_by_pct else None
    worst = sorted_by_pct[-1] if sorted_by_pct else None

    return PortfolioPnLSummary(
        portfolio_id=portfolio_id,
        portfolio_name=portfolio_name,
        as_of_date=today,
        total_market_value=total_market_value,
        total_cost_basis=total_cost_basis,
        total_unrealized_pnl=total_unrealized_pnl,
        total_realized_pnl=total_realized_pnl,
        total_pnl=total_unrealized_pnl + total_realized_pnl,
        day_pnl=day_pnl,
        week_pnl=week_pnl,
        month_pnl=month_pnl,
        ytd_pnl=ytd_pnl,
        positions=position_pnls,
        winners_count=len(winners),
        losers_count=len(losers),
        best_performer=best.ticker if best else None,
        best_performer_pct=best.unrealized_pnl_pct if best else 0,
        worst_performer=worst.ticker if worst else None,
        worst_performer_pct=worst.unrealized_pnl_pct if worst else 0,
    )


# Singleton instance
_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get or create portfolio service singleton."""
    global _service
    if _service is None:
        _service = PortfolioService()
    return _service
