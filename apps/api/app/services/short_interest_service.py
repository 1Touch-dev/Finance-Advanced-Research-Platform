"""
Short Interest Data Service (Band C #40)

Provides short interest data:
- Current short interest by ticker
- Short interest history
- Days to cover calculation
- Short squeeze indicators
- Comparison across sectors
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import random


@dataclass
class ShortInterestData:
    ticker: str
    company_name: str
    short_interest: int  # Number of shares short
    short_percent_float: float  # % of float shorted
    short_percent_outstanding: float  # % of outstanding shares
    days_to_cover: float
    short_change_percent: float  # Change from prior period
    avg_daily_volume: int
    settlement_date: str
    prior_short_interest: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "short_interest": self.short_interest,
            "short_percent_float": self.short_percent_float,
            "short_percent_outstanding": self.short_percent_outstanding,
            "days_to_cover": self.days_to_cover,
            "short_change_percent": self.short_change_percent,
            "avg_daily_volume": self.avg_daily_volume,
            "settlement_date": self.settlement_date,
            "prior_short_interest": self.prior_short_interest,
        }


@dataclass
class ShortSqueezeIndicator:
    ticker: str
    squeeze_score: float  # 0-100
    short_percent_float: float
    days_to_cover: float
    borrow_rate: float
    price_momentum_5d: float
    volume_vs_avg: float
    risk_level: str  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "squeeze_score": self.squeeze_score,
            "short_percent_float": self.short_percent_float,
            "days_to_cover": self.days_to_cover,
            "borrow_rate": self.borrow_rate,
            "price_momentum_5d": self.price_momentum_5d,
            "volume_vs_avg": self.volume_vs_avg,
            "risk_level": self.risk_level,
        }


# ── Mock Data ─────────────────────────────────────────────────────────────────

COMPANIES = {
    "GME": ("GameStop Corp.", 25.0, 8.5),
    "AMC": ("AMC Entertainment", 22.0, 5.2),
    "TSLA": ("Tesla Inc.", 3.2, 1.8),
    "AAPL": ("Apple Inc.", 0.8, 0.5),
    "MSFT": ("Microsoft Corp.", 0.6, 0.4),
    "NVDA": ("NVIDIA Corp.", 1.5, 1.2),
    "BBBY": ("Bed Bath & Beyond", 35.0, 12.0),
    "KOSS": ("Koss Corporation", 40.0, 15.0),
    "BB": ("BlackBerry Limited", 8.5, 4.2),
    "NOK": ("Nokia Corporation", 2.1, 1.5),
    "PLTR": ("Palantir Technologies", 4.5, 2.8),
    "RIVN": ("Rivian Automotive", 12.0, 5.5),
    "LCID": ("Lucid Group Inc.", 15.0, 6.2),
    "SOFI": ("SoFi Technologies", 9.0, 4.0),
    "HOOD": ("Robinhood Markets", 7.5, 3.8),
}


def _generate_short_data(ticker: str) -> ShortInterestData:
    """Generate mock short interest data."""
    name, base_short_pct, base_dtc = COMPANIES.get(ticker, (f"{ticker} Inc.", 5.0, 2.0))
    
    short_pct = base_short_pct * random.uniform(0.8, 1.2)
    dtc = base_dtc * random.uniform(0.8, 1.2)
    
    avg_volume = random.randint(5_000_000, 50_000_000)
    short_interest = int(avg_volume * dtc * random.uniform(0.8, 1.2))
    prior_short = int(short_interest * random.uniform(0.85, 1.15))
    change_pct = (short_interest - prior_short) / prior_short * 100 if prior_short else 0
    
    return ShortInterestData(
        ticker=ticker,
        company_name=name,
        short_interest=short_interest,
        short_percent_float=round(short_pct, 2),
        short_percent_outstanding=round(short_pct * 0.7, 2),
        days_to_cover=round(dtc, 1),
        short_change_percent=round(change_pct, 1),
        avg_daily_volume=avg_volume,
        settlement_date=(datetime.utcnow() - timedelta(days=random.randint(1, 15))).strftime("%Y-%m-%d"),
        prior_short_interest=prior_short,
    )


# ── Service Functions ─────────────────────────────────────────────────────────


def get_short_interest(ticker: str) -> Optional[ShortInterestData]:
    """Get current short interest for a ticker."""
    if ticker.upper() not in COMPANIES:
        # Generate generic data for unknown tickers
        return ShortInterestData(
            ticker=ticker.upper(),
            company_name=f"{ticker.upper()} Corp.",
            short_interest=random.randint(1_000_000, 10_000_000),
            short_percent_float=round(random.uniform(1, 10), 2),
            short_percent_outstanding=round(random.uniform(0.5, 7), 2),
            days_to_cover=round(random.uniform(1, 5), 1),
            short_change_percent=round(random.uniform(-20, 30), 1),
            avg_daily_volume=random.randint(1_000_000, 20_000_000),
            settlement_date=(datetime.utcnow() - timedelta(days=random.randint(1, 15))).strftime("%Y-%m-%d"),
            prior_short_interest=random.randint(1_000_000, 10_000_000),
        )
    
    return _generate_short_data(ticker.upper())


def get_short_interest_history(
    ticker: str,
    periods: int = 12,
) -> List[Dict[str, Any]]:
    """Get historical short interest data."""
    history = []
    base_data = get_short_interest(ticker)
    if not base_data:
        return []
    
    current_short = base_data.short_interest
    
    for i in range(periods):
        # Go back i bi-weekly periods (short interest is reported bi-weekly)
        period_date = datetime.utcnow() - timedelta(days=14 * i)
        
        # Simulate historical values with some variance
        historical_short = int(current_short * random.uniform(0.7, 1.3))
        
        history.append({
            "settlement_date": period_date.strftime("%Y-%m-%d"),
            "short_interest": historical_short,
            "short_percent_float": round(base_data.short_percent_float * random.uniform(0.8, 1.2), 2),
            "days_to_cover": round(base_data.days_to_cover * random.uniform(0.8, 1.2), 1),
        })
    
    history.reverse()
    return history


def get_most_shorted(
    min_short_percent: float = 10.0,
    limit: int = 20,
) -> List[ShortInterestData]:
    """Get most heavily shorted stocks."""
    results = []
    
    for ticker in COMPANIES.keys():
        data = _generate_short_data(ticker)
        if data.short_percent_float >= min_short_percent:
            results.append(data)
    
    results.sort(key=lambda x: x.short_percent_float, reverse=True)
    return results[:limit]


def get_short_squeeze_candidates(
    min_squeeze_score: float = 50.0,
    limit: int = 20,
) -> List[ShortSqueezeIndicator]:
    """Get potential short squeeze candidates."""
    candidates = []
    
    for ticker in COMPANIES.keys():
        data = _generate_short_data(ticker)
        
        # Calculate squeeze score based on multiple factors
        score = 0.0
        score += min(data.short_percent_float * 2, 40)  # Max 40 from short %
        score += min(data.days_to_cover * 5, 30)  # Max 30 from days to cover
        
        borrow_rate = random.uniform(1, 50)  # Mock borrow rate
        score += min(borrow_rate, 20)  # Max 20 from borrow rate
        
        momentum = random.uniform(-10, 15)
        if momentum > 0:
            score += min(momentum, 10)  # Max 10 from momentum
        
        if score >= min_squeeze_score:
            risk_level = "low" if score < 60 else ("medium" if score < 75 else "high")
            
            candidates.append(ShortSqueezeIndicator(
                ticker=ticker,
                squeeze_score=round(score, 1),
                short_percent_float=data.short_percent_float,
                days_to_cover=data.days_to_cover,
                borrow_rate=round(borrow_rate, 2),
                price_momentum_5d=round(momentum, 2),
                volume_vs_avg=round(random.uniform(0.5, 3.0), 2),
                risk_level=risk_level,
            ))
    
    candidates.sort(key=lambda x: x.squeeze_score, reverse=True)
    return candidates[:limit]


def get_short_changes(
    min_change_percent: float = 10.0,
    direction: str = "both",  # "up", "down", or "both"
    limit: int = 20,
) -> List[ShortInterestData]:
    """Get stocks with significant short interest changes."""
    results = []
    
    for ticker in COMPANIES.keys():
        data = _generate_short_data(ticker)
        
        if abs(data.short_change_percent) >= min_change_percent:
            if direction == "up" and data.short_change_percent < 0:
                continue
            if direction == "down" and data.short_change_percent > 0:
                continue
            results.append(data)
    
    results.sort(key=lambda x: abs(x.short_change_percent), reverse=True)
    return results[:limit]


def get_sector_short_summary() -> List[Dict[str, Any]]:
    """Get short interest summary by sector."""
    sectors = {
        "Technology": ["AAPL", "MSFT", "NVDA", "PLTR"],
        "Consumer Discretionary": ["TSLA", "GME", "AMC", "BBBY"],
        "Financials": ["HOOD", "SOFI"],
        "Automotive": ["RIVN", "LCID"],
        "Communications": ["BB", "NOK"],
    }
    
    summary = []
    for sector, tickers in sectors.items():
        sector_data = [_generate_short_data(t) for t in tickers if t in COMPANIES]
        if not sector_data:
            continue
        
        avg_short_pct = sum(d.short_percent_float for d in sector_data) / len(sector_data)
        avg_dtc = sum(d.days_to_cover for d in sector_data) / len(sector_data)
        
        summary.append({
            "sector": sector,
            "stock_count": len(sector_data),
            "avg_short_percent_float": round(avg_short_pct, 2),
            "avg_days_to_cover": round(avg_dtc, 1),
            "most_shorted": max(sector_data, key=lambda x: x.short_percent_float).ticker,
        })
    
    summary.sort(key=lambda x: x["avg_short_percent_float"], reverse=True)
    return summary


def get_short_stats() -> Dict[str, Any]:
    """Get overall short interest statistics."""
    all_data = [_generate_short_data(t) for t in COMPANIES.keys()]
    
    return {
        "total_tracked": len(all_data),
        "highly_shorted_count": len([d for d in all_data if d.short_percent_float >= 20]),
        "avg_short_percent": round(sum(d.short_percent_float for d in all_data) / len(all_data), 2),
        "avg_days_to_cover": round(sum(d.days_to_cover for d in all_data) / len(all_data), 1),
        "net_short_change": round(sum(d.short_change_percent for d in all_data) / len(all_data), 2),
        "most_shorted": max(all_data, key=lambda x: x.short_percent_float).ticker,
        "biggest_increase": max(all_data, key=lambda x: x.short_change_percent).ticker,
        "biggest_decrease": min(all_data, key=lambda x: x.short_change_percent).ticker,
        "last_updated": datetime.utcnow().isoformat(),
    }
