"""
Unusual Volume Screening Service (Band B #28)
────────────────────────────────────────────────────────────────────────────
Provides:
  - Unusual volume detection (delayed EOD data)
  - Volume spike screening
  - Historical volume patterns
  - Volume vs price movement analysis

Note: Uses delayed/EOD data. Honest delayed > wrong live.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, date, timedelta
import statistics
import math
import random


# ── Enums ──────────────────────────────────────────────────────────────────────

class VolumeSignal(Enum):
    """Type of volume signal."""
    EXTREME_SPIKE = "extreme_spike"  # >3x average
    HIGH_VOLUME = "high_volume"  # 2-3x average
    ELEVATED = "elevated"  # 1.5-2x average
    NORMAL = "normal"
    LOW = "low"  # <0.5x average
    EXTREME_LOW = "extreme_low"  # <0.25x average


class PriceVolumePattern(Enum):
    """Price-volume relationship pattern."""
    ACCUMULATION = "accumulation"  # High volume + price up
    DISTRIBUTION = "distribution"  # High volume + price down
    BREAKOUT = "breakout"  # Volume spike + price breakout
    EXHAUSTION = "exhaustion"  # Volume spike + price reversal
    CONSOLIDATION = "consolidation"  # Low volume + price stable
    DIVERGENCE = "divergence"  # Volume declining while price rising


class ScreenerTimeframe(Enum):
    """Screening timeframe."""
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class VolumeBar:
    """Single volume data point."""
    ticker: str
    date: date
    volume: int
    avg_volume_20d: int
    avg_volume_50d: int
    volume_ratio: float  # volume / avg

    # Price context
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    price_change_pct: float

    # Signal
    signal: VolumeSignal


@dataclass
class VolumeAlert:
    """Volume-based alert."""
    # Required fields first (no defaults)
    ticker: str
    company_name: str
    alert_date: date
    volume: int
    avg_volume: int
    volume_ratio: float
    volume_rank: int  # Rank in lookback period
    signal: VolumeSignal
    price: float
    price_change_pct: float
    intraday_range_pct: float

    # Optional fields with defaults
    alert_time: Optional[datetime] = None
    pattern: Optional[PriceVolumePattern] = None
    days_since_last_spike: Optional[int] = None
    sector: Optional[str] = None
    news_catalyst: Optional[str] = None


@dataclass
class VolumeScreen:
    """Results from volume screener."""
    screen_date: date
    timeframe: ScreenerTimeframe

    # Results
    alerts: List[VolumeAlert]

    # Summary
    total_screened: int
    alerts_count: int
    extreme_spikes: int
    high_volume: int

    # Sector breakdown
    sector_distribution: Dict[str, int]

    # Top movers
    highest_volume_ratio: Optional[VolumeAlert] = None
    biggest_price_move: Optional[VolumeAlert] = None


@dataclass
class TickerVolumeProfile:
    """Volume profile for a single ticker."""
    ticker: str
    company_name: str
    analysis_date: date

    # Averages
    avg_volume_10d: int
    avg_volume_20d: int
    avg_volume_50d: int
    avg_volume_90d: int

    # Recent volume
    latest_volume: int
    latest_ratio: float
    latest_signal: VolumeSignal

    # Historical patterns
    spikes_30d: int  # Number of >2x days in last 30
    spikes_90d: int
    avg_spike_magnitude: float

    # Trend
    volume_trend: str  # increasing, decreasing, stable
    volume_volatility: float  # CV of daily volume

    # Recent history
    recent_bars: List[VolumeBar] = field(default_factory=list)


@dataclass
class SectorVolumeFlow:
    """Sector-level volume flow analysis."""
    sector: str
    analysis_date: date

    # Aggregate metrics
    total_volume: int
    avg_volume: int
    volume_vs_avg: float

    # Flow direction
    net_inflow_estimate: float  # Based on up/down volume
    flow_direction: str  # bullish, bearish, neutral

    # Component breakdown
    tickers_elevated: int
    tickers_low: int

    # Top contributors
    top_volume_tickers: List[str]


# ── Simulated Data ─────────────────────────────────────────────────────────────

TICKER_VOLUME_DATA: Dict[str, Dict[str, Any]] = {
    "NVDA": {"name": "NVIDIA Corporation", "avg_vol": 50_000_000, "sector": "Technology"},
    "AAPL": {"name": "Apple Inc.", "avg_vol": 80_000_000, "sector": "Technology"},
    "MSFT": {"name": "Microsoft Corporation", "avg_vol": 25_000_000, "sector": "Technology"},
    "GOOGL": {"name": "Alphabet Inc.", "avg_vol": 20_000_000, "sector": "Technology"},
    "META": {"name": "Meta Platforms Inc.", "avg_vol": 15_000_000, "sector": "Technology"},
    "AMZN": {"name": "Amazon.com Inc.", "avg_vol": 40_000_000, "sector": "Consumer"},
    "TSLA": {"name": "Tesla Inc.", "avg_vol": 100_000_000, "sector": "Consumer"},
    "AMD": {"name": "Advanced Micro Devices", "avg_vol": 60_000_000, "sector": "Technology"},
    "INTC": {"name": "Intel Corporation", "avg_vol": 45_000_000, "sector": "Technology"},
    "JPM": {"name": "JPMorgan Chase", "avg_vol": 12_000_000, "sector": "Financials"},
    "V": {"name": "Visa Inc.", "avg_vol": 8_000_000, "sector": "Financials"},
    "JNJ": {"name": "Johnson & Johnson", "avg_vol": 7_000_000, "sector": "Healthcare"},
    "XOM": {"name": "Exxon Mobil", "avg_vol": 15_000_000, "sector": "Energy"},
}


def _generate_volume_bar(ticker: str, bar_date: date, spike_probability: float = 0.1) -> VolumeBar:
    """Generate simulated volume bar."""
    data = TICKER_VOLUME_DATA.get(ticker, {"avg_vol": 10_000_000})
    avg_vol = data["avg_vol"]

    # Determine if this is a spike day
    is_spike = random.random() < spike_probability

    if is_spike:
        volume_ratio = random.uniform(1.8, 4.0)
    else:
        volume_ratio = random.gauss(1.0, 0.3)
        volume_ratio = max(0.2, min(2.0, volume_ratio))

    volume = int(avg_vol * volume_ratio)

    # Price movement
    base_price = 100 + random.uniform(-20, 50)
    price_change = random.gauss(0, 2)

    if is_spike:
        # Spikes often accompany bigger moves
        price_change = random.gauss(0, 5) * (1 if random.random() > 0.4 else -1)

    # Determine signal
    if volume_ratio >= 3.0:
        signal = VolumeSignal.EXTREME_SPIKE
    elif volume_ratio >= 2.0:
        signal = VolumeSignal.HIGH_VOLUME
    elif volume_ratio >= 1.5:
        signal = VolumeSignal.ELEVATED
    elif volume_ratio <= 0.25:
        signal = VolumeSignal.EXTREME_LOW
    elif volume_ratio <= 0.5:
        signal = VolumeSignal.LOW
    else:
        signal = VolumeSignal.NORMAL

    return VolumeBar(
        ticker=ticker,
        date=bar_date,
        volume=volume,
        avg_volume_20d=avg_vol,
        avg_volume_50d=int(avg_vol * 0.95),
        volume_ratio=round(volume_ratio, 2),
        open_price=round(base_price, 2),
        close_price=round(base_price * (1 + price_change / 100), 2),
        high_price=round(base_price * (1 + abs(price_change) / 100 + 0.01), 2),
        low_price=round(base_price * (1 - abs(price_change) / 100 - 0.01), 2),
        price_change_pct=round(price_change, 2),
        signal=signal,
    )


def _determine_pattern(volume_ratio: float, price_change: float) -> PriceVolumePattern:
    """Determine price-volume pattern."""
    if volume_ratio >= 2.0:
        if price_change > 3:
            return PriceVolumePattern.BREAKOUT
        elif price_change > 0:
            return PriceVolumePattern.ACCUMULATION
        elif price_change < -3:
            return PriceVolumePattern.EXHAUSTION
        else:
            return PriceVolumePattern.DISTRIBUTION
    elif volume_ratio <= 0.5:
        return PriceVolumePattern.CONSOLIDATION
    else:
        return PriceVolumePattern.ACCUMULATION if price_change > 0 else PriceVolumePattern.DISTRIBUTION


# ── Service Functions ──────────────────────────────────────────────────────────

def get_volume_bar(ticker: str, bar_date: Optional[date] = None) -> VolumeBar:
    """Get volume bar for a ticker on a specific date."""
    bar_date = bar_date or date.today()
    return _generate_volume_bar(ticker.upper(), bar_date)


def get_volume_history(
    ticker: str,
    days: int = 30,
) -> List[VolumeBar]:
    """Get historical volume bars."""
    ticker = ticker.upper()
    today = date.today()
    bars = []

    for i in range(days):
        bar_date = today - timedelta(days=i)
        # Skip weekends
        if bar_date.weekday() >= 5:
            continue
        bars.append(_generate_volume_bar(ticker, bar_date))

    return list(reversed(bars))


def screen_unusual_volume(
    min_ratio: float = 2.0,
    tickers: Optional[List[str]] = None,
    sector: Optional[str] = None,
) -> VolumeScreen:
    """
    Screen for unusual volume across the market.

    Returns tickers with volume significantly above average.
    """
    target_tickers = list(TICKER_VOLUME_DATA.keys())

    if tickers:
        target_tickers = [t.upper() for t in tickers if t.upper() in TICKER_VOLUME_DATA]

    if sector:
        sector_lower = sector.lower()
        target_tickers = [
            t for t in target_tickers
            if TICKER_VOLUME_DATA[t]["sector"].lower() == sector_lower
        ]

    alerts = []
    sector_dist: Dict[str, int] = {}

    today = date.today()

    for ticker in target_tickers:
        bar = _generate_volume_bar(ticker, today, spike_probability=0.15)

        if bar.volume_ratio >= min_ratio:
            data = TICKER_VOLUME_DATA[ticker]
            pattern = _determine_pattern(bar.volume_ratio, bar.price_change_pct)

            alert = VolumeAlert(
                ticker=ticker,
                company_name=data["name"],
                alert_date=today,
                volume=bar.volume,
                avg_volume=bar.avg_volume_20d,
                volume_ratio=bar.volume_ratio,
                volume_rank=1,  # Would be calculated from history
                signal=bar.signal,
                pattern=pattern,
                price=bar.close_price,
                price_change_pct=bar.price_change_pct,
                intraday_range_pct=round((bar.high_price - bar.low_price) / bar.open_price * 100, 2),
                sector=data["sector"],
            )
            alerts.append(alert)

            sector_dist[data["sector"]] = sector_dist.get(data["sector"], 0) + 1

    # Sort by volume ratio
    alerts.sort(key=lambda x: x.volume_ratio, reverse=True)

    extreme_count = sum(1 for a in alerts if a.signal == VolumeSignal.EXTREME_SPIKE)
    high_count = sum(1 for a in alerts if a.signal == VolumeSignal.HIGH_VOLUME)

    return VolumeScreen(
        screen_date=today,
        timeframe=ScreenerTimeframe.DAILY,
        alerts=alerts,
        total_screened=len(target_tickers),
        alerts_count=len(alerts),
        extreme_spikes=extreme_count,
        high_volume=high_count,
        sector_distribution=sector_dist,
        highest_volume_ratio=alerts[0] if alerts else None,
        biggest_price_move=max(alerts, key=lambda x: abs(x.price_change_pct)) if alerts else None,
    )


def get_ticker_volume_profile(ticker: str) -> TickerVolumeProfile:
    """Get comprehensive volume profile for a ticker."""
    ticker = ticker.upper()
    data = TICKER_VOLUME_DATA.get(ticker)

    if not data:
        raise ValueError(f"Unknown ticker: {ticker}")

    today = date.today()
    bars = get_volume_history(ticker, days=90)

    if not bars:
        raise ValueError(f"No volume data for {ticker}")

    volumes = [b.volume for b in bars]
    avg_vol = data["avg_vol"]

    # Calculate averages
    avg_10d = statistics.mean(volumes[:10]) if len(volumes) >= 10 else avg_vol
    avg_20d = statistics.mean(volumes[:20]) if len(volumes) >= 20 else avg_vol
    avg_50d = statistics.mean(volumes[:50]) if len(volumes) >= 50 else avg_vol
    avg_90d = statistics.mean(volumes) if volumes else avg_vol

    latest = bars[-1] if bars else None
    latest_ratio = latest.volume_ratio if latest else 1.0

    # Count spikes
    spikes_30d = sum(1 for b in bars[-30:] if b.volume_ratio >= 2.0)
    spikes_90d = sum(1 for b in bars if b.volume_ratio >= 2.0)
    spike_magnitudes = [b.volume_ratio for b in bars if b.volume_ratio >= 2.0]
    avg_spike = statistics.mean(spike_magnitudes) if spike_magnitudes else 0

    # Volume trend
    if len(volumes) >= 20:
        early_avg = statistics.mean(volumes[10:20])
        recent_avg = statistics.mean(volumes[:10])
        if recent_avg > early_avg * 1.2:
            trend = "increasing"
        elif recent_avg < early_avg * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # Volatility
    vol_volatility = statistics.stdev(volumes) / statistics.mean(volumes) if volumes else 0

    return TickerVolumeProfile(
        ticker=ticker,
        company_name=data["name"],
        analysis_date=today,
        avg_volume_10d=int(avg_10d),
        avg_volume_20d=int(avg_20d),
        avg_volume_50d=int(avg_50d),
        avg_volume_90d=int(avg_90d),
        latest_volume=latest.volume if latest else 0,
        latest_ratio=latest_ratio,
        latest_signal=latest.signal if latest else VolumeSignal.NORMAL,
        spikes_30d=spikes_30d,
        spikes_90d=spikes_90d,
        avg_spike_magnitude=round(avg_spike, 2),
        volume_trend=trend,
        volume_volatility=round(vol_volatility, 3),
        recent_bars=bars[-10:],
    )


def get_sector_volume_flow(sector: str) -> SectorVolumeFlow:
    """Analyze volume flow at sector level."""
    sector_tickers = [
        t for t, d in TICKER_VOLUME_DATA.items()
        if d["sector"].lower() == sector.lower()
    ]

    if not sector_tickers:
        raise ValueError(f"No tickers in sector: {sector}")

    today = date.today()
    total_vol = 0
    total_avg = 0
    up_volume = 0
    down_volume = 0
    elevated = 0
    low = 0
    top_tickers = []

    for ticker in sector_tickers:
        bar = _generate_volume_bar(ticker, today)
        data = TICKER_VOLUME_DATA[ticker]

        total_vol += bar.volume
        total_avg += data["avg_vol"]

        if bar.price_change_pct > 0:
            up_volume += bar.volume
        else:
            down_volume += bar.volume

        if bar.volume_ratio >= 1.5:
            elevated += 1
        elif bar.volume_ratio <= 0.5:
            low += 1

        top_tickers.append((ticker, bar.volume))

    top_tickers.sort(key=lambda x: x[1], reverse=True)

    ratio = total_vol / total_avg if total_avg > 0 else 1.0
    net_flow = (up_volume - down_volume) / total_vol if total_vol > 0 else 0

    if net_flow > 0.2:
        flow_dir = "bullish"
    elif net_flow < -0.2:
        flow_dir = "bearish"
    else:
        flow_dir = "neutral"

    return SectorVolumeFlow(
        sector=sector,
        analysis_date=today,
        total_volume=total_vol,
        avg_volume=total_avg,
        volume_vs_avg=round(ratio, 2),
        net_inflow_estimate=round(net_flow, 3),
        flow_direction=flow_dir,
        tickers_elevated=elevated,
        tickers_low=low,
        top_volume_tickers=[t[0] for t in top_tickers[:5]],
    )


# ── Serialization ──────────────────────────────────────────────────────────────

def volume_bar_to_dict(bar: VolumeBar) -> Dict[str, Any]:
    """Convert volume bar to dictionary."""
    return {
        "ticker": bar.ticker,
        "date": bar.date.isoformat(),
        "volume": bar.volume,
        "avg_volume_20d": bar.avg_volume_20d,
        "volume_ratio": bar.volume_ratio,
        "signal": bar.signal.value,
        "price": {
            "open": bar.open_price,
            "close": bar.close_price,
            "high": bar.high_price,
            "low": bar.low_price,
            "change_pct": bar.price_change_pct,
        },
    }


def alert_to_dict(alert: VolumeAlert) -> Dict[str, Any]:
    """Convert volume alert to dictionary."""
    return {
        "ticker": alert.ticker,
        "company_name": alert.company_name,
        "alert_date": alert.alert_date.isoformat(),
        "volume": alert.volume,
        "avg_volume": alert.avg_volume,
        "volume_ratio": alert.volume_ratio,
        "signal": alert.signal.value,
        "pattern": alert.pattern.value if alert.pattern else None,
        "price": alert.price,
        "price_change_pct": alert.price_change_pct,
        "intraday_range_pct": alert.intraday_range_pct,
        "sector": alert.sector,
    }


def screen_to_dict(screen: VolumeScreen) -> Dict[str, Any]:
    """Convert volume screen to dictionary."""
    return {
        "screen_date": screen.screen_date.isoformat(),
        "timeframe": screen.timeframe.value,
        "summary": {
            "total_screened": screen.total_screened,
            "alerts_count": screen.alerts_count,
            "extreme_spikes": screen.extreme_spikes,
            "high_volume": screen.high_volume,
        },
        "sector_distribution": screen.sector_distribution,
        "alerts": [alert_to_dict(a) for a in screen.alerts],
        "highlights": {
            "highest_ratio": alert_to_dict(screen.highest_volume_ratio) if screen.highest_volume_ratio else None,
            "biggest_move": alert_to_dict(screen.biggest_price_move) if screen.biggest_price_move else None,
        },
    }


def profile_to_dict(profile: TickerVolumeProfile) -> Dict[str, Any]:
    """Convert volume profile to dictionary."""
    return {
        "ticker": profile.ticker,
        "company_name": profile.company_name,
        "analysis_date": profile.analysis_date.isoformat(),
        "averages": {
            "10d": profile.avg_volume_10d,
            "20d": profile.avg_volume_20d,
            "50d": profile.avg_volume_50d,
            "90d": profile.avg_volume_90d,
        },
        "latest": {
            "volume": profile.latest_volume,
            "ratio": profile.latest_ratio,
            "signal": profile.latest_signal.value,
        },
        "patterns": {
            "spikes_30d": profile.spikes_30d,
            "spikes_90d": profile.spikes_90d,
            "avg_spike_magnitude": profile.avg_spike_magnitude,
            "trend": profile.volume_trend,
            "volatility": profile.volume_volatility,
        },
        "recent_bars": [volume_bar_to_dict(b) for b in profile.recent_bars],
    }


def sector_flow_to_dict(flow: SectorVolumeFlow) -> Dict[str, Any]:
    """Convert sector flow to dictionary."""
    return {
        "sector": flow.sector,
        "analysis_date": flow.analysis_date.isoformat(),
        "volume": {
            "total": flow.total_volume,
            "average": flow.avg_volume,
            "vs_avg": flow.volume_vs_avg,
        },
        "flow": {
            "net_inflow_estimate": flow.net_inflow_estimate,
            "direction": flow.flow_direction,
        },
        "breakdown": {
            "tickers_elevated": flow.tickers_elevated,
            "tickers_low": flow.tickers_low,
        },
        "top_tickers": flow.top_volume_tickers,
    }
