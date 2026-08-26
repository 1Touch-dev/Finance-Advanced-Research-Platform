"""
Unusual Volume Screening Service (Band B #28)
Uses yfinance for REAL volume data and spike detection.
NO MOCK DATA - uses no_data_response when real data unavailable.

Features:
- Unusual volume detection (volume vs 20-day/50-day average)
- Volume breakouts with price correlation
- Volume trend analysis
- Relative volume screening across watchlists
- Sector-based volume flow analysis
"""
import time
import logging
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field

import yfinance as yf

from app.core.no_data import no_data_response, NoDataReason

log = logging.getLogger(__name__)

_cache: Dict[str, Any] = {}
# Cache TTL: 5-10 minutes for real-time volume data
_CACHE_TTL_REALTIME = 300   # 5 minutes for screening/alerts
_CACHE_TTL_PROFILE = 600    # 10 minutes for profiles
_CACHE_TTL_HISTORY = 900    # 15 minutes for historical data

DEFAULT_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD",
    "JPM", "BAC", "GS", "NFLX", "CRM", "COIN", "SHOP", "SQ",
    "DIS", "NKE", "BA", "UBER", "ABNB", "PLTR", "SOFI", "RIVN",
    "SPY", "QQQ", "IWM",
]

SECTOR_MAP = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMD", "CRM"],
    "Consumer": ["AMZN", "TSLA", "NFLX", "DIS", "NKE", "SHOP", "UBER", "ABNB"],
    "Finance": ["JPM", "BAC", "GS", "COIN", "SQ", "SOFI"],
    "Industrial": ["BA"],
    "Other": ["PLTR", "RIVN"],
}


class VolumeSignal(str, Enum):
    EXTREME_SPIKE = "extreme_spike"
    HIGH_VOLUME = "high_volume"
    ABOVE_AVERAGE = "above_average"
    NORMAL = "normal"
    BELOW_AVERAGE = "below_average"
    VERY_LOW = "very_low"


class PriceVolumePattern(str, Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    CLIMAX = "climax"
    NORMAL = "normal"


def _get_cached(key: str, ttl: int = _CACHE_TTL_REALTIME):
    """Get cached data if not expired."""
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < ttl:
            return entry["data"]
    return None


def _set_cache(key: str, data):
    """Cache data with timestamp."""
    _cache[key] = {"data": data, "ts": time.time()}


def _get_company_name(ticker: str) -> str:
    """Fetch company name from yfinance."""
    cache_key = f"company_name_{ticker}"
    cached = _get_cached(cache_key, ttl=3600)  # Cache names for 1 hour
    if cached is not None:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info
        name = info.get("shortName") or info.get("longName") or ticker.upper()
        _set_cache(cache_key, name)
        return name
    except Exception:
        return ticker.upper()


def _classify_volume(ratio: float) -> VolumeSignal:
    """Classify volume ratio into signal categories."""
    if ratio >= 3.0:
        return VolumeSignal.EXTREME_SPIKE
    elif ratio >= 2.0:
        return VolumeSignal.HIGH_VOLUME
    elif ratio >= 1.3:
        return VolumeSignal.ABOVE_AVERAGE
    elif ratio >= 0.7:
        return VolumeSignal.NORMAL
    elif ratio >= 0.4:
        return VolumeSignal.BELOW_AVERAGE
    else:
        return VolumeSignal.VERY_LOW


def _classify_price_volume_pattern(
    volume_ratio: float, price_change_pct: float, price_at_high: bool = False
) -> PriceVolumePattern:
    """
    Classify price-volume pattern based on volume spike and price movement.

    Patterns:
    - BREAKOUT: High volume (>2x) + strong up move (>2%)
    - BREAKDOWN: High volume (>2x) + strong down move (<-2%)
    - ACCUMULATION: Above avg volume + moderate up move
    - DISTRIBUTION: Above avg volume + moderate down move
    - CLIMAX: Extreme volume (>3x) + extreme price move
    - NORMAL: No significant pattern
    """
    if volume_ratio >= 3.0:
        # Climax patterns - extreme volume
        if abs(price_change_pct) >= 5.0:
            return PriceVolumePattern.CLIMAX
        elif price_change_pct >= 2.0:
            return PriceVolumePattern.BREAKOUT
        elif price_change_pct <= -2.0:
            return PriceVolumePattern.BREAKDOWN

    if volume_ratio >= 2.0:
        # High volume patterns
        if price_change_pct >= 2.0:
            return PriceVolumePattern.BREAKOUT
        elif price_change_pct <= -2.0:
            return PriceVolumePattern.BREAKDOWN
        elif price_change_pct >= 0.5:
            return PriceVolumePattern.ACCUMULATION
        elif price_change_pct <= -0.5:
            return PriceVolumePattern.DISTRIBUTION

    if volume_ratio >= 1.3:
        # Above average volume
        if price_change_pct >= 1.0:
            return PriceVolumePattern.ACCUMULATION
        elif price_change_pct <= -1.0:
            return PriceVolumePattern.DISTRIBUTION

    return PriceVolumePattern.NORMAL


def _is_breakout_confirmed(prices: np.ndarray, breakout_idx: int) -> bool:
    """
    Check if a breakout has price follow-through.
    Confirmed if price holds above breakout day's close for next 2 days.
    """
    if breakout_idx >= len(prices) - 1:
        return False  # Not enough data after breakout

    breakout_close = prices[breakout_idx]
    # Check if subsequent closes are above breakout close
    for i in range(breakout_idx + 1, min(breakout_idx + 3, len(prices))):
        if prices[i] < breakout_close * 0.98:  # Allow 2% pullback
            return False
    return True


@dataclass
class VolumeBar:
    ticker: str
    date: str
    volume: int
    avg_volume_20d: int
    ratio: float
    signal: VolumeSignal
    price: float = 0.0
    price_change_pct: float = 0.0


@dataclass
class VolumeAlert:
    ticker: str
    company_name: str
    date: str
    volume: int
    avg_volume_20d: int
    ratio: float
    signal: VolumeSignal
    price: float
    price_change_pct: float
    sector: str = ""
    pattern: PriceVolumePattern = PriceVolumePattern.NORMAL
    is_breakout: bool = False


@dataclass
class VolumeScreen:
    timestamp: str
    threshold: float
    alerts: List[VolumeAlert] = field(default_factory=list)
    total_screened: int = 0
    total_flagged: int = 0


@dataclass
class VolumeProfile:
    ticker: str
    company_name: str
    avg_volume_20d: int
    avg_volume_50d: int
    latest_volume: int
    latest_ratio: float
    latest_signal: VolumeSignal
    spikes_30d: int
    volume_trend: str
    price: float = 0.0
    sector: str = ""
    relative_volume: float = 0.0  # Volume relative to market average
    breakout_count_30d: int = 0   # Number of breakout days in 30d


@dataclass
class VolumeBreakout:
    """Volume breakout with price correlation."""
    ticker: str
    company_name: str
    date: str
    volume: int
    volume_ratio: float
    price: float
    price_change_pct: float
    pattern: PriceVolumePattern
    is_confirmed: bool  # Price follow-through
    sector: str = ""


@dataclass
class SectorVolumeFlow:
    sector: str
    tickers: List[str]
    total_volume: int
    avg_ratio: float
    direction: str
    top_mover: str = ""
    top_mover_ratio: float = 0.0


def _fetch_volume_data(tickers: List[str], period: str = "1mo") -> Dict[str, Any]:
    """
    Fetch volume + price data for multiple tickers from yfinance.

    Args:
        tickers: List of stock symbols
        period: yfinance period (1d, 5d, 1mo, 3mo, etc.)

    Returns:
        Dict with 'data' (DataFrame) and 'tickers' list, or empty dict on failure
    """
    cache_key = f"voldata_{'_'.join(sorted(tickers[:10]))}_{period}"
    cached = _get_cached(cache_key, ttl=_CACHE_TTL_REALTIME)
    if cached is not None:
        return cached

    try:
        log.info("Fetching volume data for %d tickers, period=%s", len(tickers), period)
        data = yf.download(tickers, period=period, progress=False, threads=True)
        if data.empty:
            log.warning("Empty data returned from yfinance for tickers: %s", tickers[:5])
            return {}
        result = {"data": data, "tickers": tickers}
        _set_cache(cache_key, result)
        log.debug("Volume data cached for %d tickers", len(tickers))
        return result
    except Exception as e:
        log.error("Volume data fetch failed for tickers %s: %s", tickers[:5], e)
        return {}


def get_volume_bar(ticker: str, bar_date=None) -> Dict[str, Any]:
    """
    Get latest volume bar for a ticker with real yfinance data.

    Args:
        ticker: Stock symbol
        bar_date: Optional specific date (not implemented, uses latest)

    Returns:
        VolumeBar dataclass or no_data response dict
    """
    cache_key = f"vol_bar_{ticker}"
    cached = _get_cached(cache_key, ttl=_CACHE_TTL_REALTIME)
    if cached is not None:
        return cached

    ticker = ticker.upper()
    try:
        log.info("Fetching volume bar for %s", ticker)
        data = yf.download(ticker, period="1mo", progress=False)
        if data.empty:
            log.warning("No data returned for ticker %s", ticker)
            return no_data_response(
                entity=ticker,
                data_type="volume_bar",
                reason=NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"No volume data available for {ticker}"
            )

        volumes = data["Volume"].dropna().values.flatten()
        closes = data["Close"].dropna().values.flatten()
        dates = [str(d.date()) for d in data.index]

        if len(volumes) < 2:
            log.warning("Insufficient volume data for %s (only %d bars)", ticker, len(volumes))
            return no_data_response(
                entity=ticker,
                data_type="volume_bar",
                reason=NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"Insufficient data for {ticker} - only {len(volumes)} bars"
            )

        latest_vol = int(volumes[-1])
        avg_20d = int(np.mean(volumes[-20:])) if len(volumes) >= 20 else int(np.mean(volumes))
        ratio = round(latest_vol / avg_20d, 2) if avg_20d > 0 else 0

        price = float(closes[-1]) if len(closes) > 0 else 0
        price_change = ((closes[-1] / closes[-2]) - 1) * 100 if len(closes) >= 2 else 0

        result = VolumeBar(
            ticker=ticker,
            date=dates[-1] if dates else str(date.today()),
            volume=latest_vol,
            avg_volume_20d=avg_20d,
            ratio=ratio,
            signal=_classify_volume(ratio),
            price=round(price, 2),
            price_change_pct=round(float(price_change), 2),
        )
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.error("Volume bar failed for %s: %s", ticker, e)
        return no_data_response(
            entity=ticker,
            data_type="volume_bar",
            reason=NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def get_volume_history(ticker: str, days: int = 30) -> Dict[str, Any]:
    """
    Get historical volume data for a ticker with real yfinance data.

    Args:
        ticker: Stock symbol
        days: Number of days of history (default 30)

    Returns:
        Dict with 'bars' list of VolumeBar or no_data response
    """
    cache_key = f"vol_hist_{ticker}_{days}"
    cached = _get_cached(cache_key, ttl=_CACHE_TTL_HISTORY)
    if cached is not None:
        return cached

    ticker = ticker.upper()
    try:
        period = "1mo" if days <= 30 else "3mo" if days <= 90 else "6mo"
        log.info("Fetching volume history for %s, period=%s", ticker, period)
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            return no_data_response(
                entity=ticker,
                data_type="volume_history",
                reason=NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"No historical data for {ticker}"
            )

        volumes = data["Volume"].dropna().values.flatten()
        closes = data["Close"].dropna().values.flatten()
        dates = [str(d.date()) for d in data.index]

        if len(volumes) < 5:
            return no_data_response(
                entity=ticker,
                data_type="volume_history",
                reason=NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"Insufficient history for {ticker}"
            )

        bars = []
        for i in range(min(days, len(volumes))):
            idx = len(volumes) - 1 - i
            if idx < 0:
                break

            avg_start = max(0, idx - 20)
            avg_20d = int(np.mean(volumes[avg_start:idx])) if idx > 0 else int(volumes[idx])
            vol = int(volumes[idx])
            ratio = round(vol / avg_20d, 2) if avg_20d > 0 else 0

            price_chg = 0
            if idx > 0 and closes[idx - 1] > 0:
                price_chg = ((closes[idx] / closes[idx - 1]) - 1) * 100

            bars.append(VolumeBar(
                ticker=ticker,
                date=dates[idx],
                volume=vol,
                avg_volume_20d=avg_20d,
                ratio=ratio,
                signal=_classify_volume(ratio),
                price=round(float(closes[idx]), 2),
                price_change_pct=round(float(price_chg), 2),
            ))

        bars.reverse()
        result = {"ticker": ticker, "days": days, "bars": bars, "source": "yfinance"}
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.error("Volume history failed for %s: %s", ticker, e)
        return no_data_response(
            entity=ticker,
            data_type="volume_history",
            reason=NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def screen_unusual_volume(
    min_ratio: float = 2.0,
    tickers: Optional[List[str]] = None,
    sector: Optional[str] = None,
    include_breakouts_only: bool = False
) -> Dict[str, Any]:
    """
    Screen for unusual volume across watchlist using real yfinance data.

    Args:
        min_ratio: Minimum volume ratio to flag (default 2.0 = 2x average)
        tickers: Custom ticker list (uses DEFAULT_WATCHLIST if None)
        sector: Filter by sector (Technology, Consumer, Finance, etc.)
        include_breakouts_only: Only include stocks with breakout patterns

    Returns:
        VolumeScreen dataclass or no_data response
    """
    cache_key = f"vol_screen_{min_ratio}_{sector}_{include_breakouts_only}"
    cached = _get_cached(cache_key, ttl=_CACHE_TTL_REALTIME)
    if cached is not None:
        return cached

    ticker_list = tickers or DEFAULT_WATCHLIST
    if sector and sector in SECTOR_MAP:
        ticker_list = SECTOR_MAP[sector]

    try:
        log.info("Screening %d tickers for unusual volume (min_ratio=%.1f)", len(ticker_list), min_ratio)
        data = yf.download(ticker_list, period="1mo", progress=False, threads=True)
        if data.empty:
            log.warning("No data returned for volume screening")
            return no_data_response(
                entity="watchlist",
                data_type="volume_screen",
                reason=NoDataReason.API_UNAVAILABLE,
                source="yfinance",
                details="Failed to fetch volume data for screening"
            )
    except Exception as e:
        log.error("Volume screen download failed: %s", e)
        return no_data_response(
            entity="watchlist",
            data_type="volume_screen",
            reason=NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )

    alerts = []
    for ticker in ticker_list:
        try:
            if len(ticker_list) > 1:
                vol_series = data["Volume"][ticker].dropna().values if ticker in data["Volume"].columns else np.array([])
                close_series = data["Close"][ticker].dropna().values if ticker in data["Close"].columns else np.array([])
            else:
                vol_series = data["Volume"].dropna().values.flatten()
                close_series = data["Close"].dropna().values.flatten()

            if len(vol_series) < 5:
                continue

            latest_vol = int(vol_series[-1])
            avg_20d = int(np.mean(vol_series[-20:])) if len(vol_series) >= 20 else int(np.mean(vol_series))
            ratio = latest_vol / avg_20d if avg_20d > 0 else 0

            if ratio < min_ratio:
                continue

            price = float(close_series[-1]) if len(close_series) > 0 else 0
            price_chg = ((close_series[-1] / close_series[-2]) - 1) * 100 if len(close_series) >= 2 else 0

            # Classify price-volume pattern
            pattern = _classify_price_volume_pattern(ratio, price_chg)
            is_breakout = pattern in (PriceVolumePattern.BREAKOUT, PriceVolumePattern.CLIMAX)

            if include_breakouts_only and not is_breakout:
                continue

            # Find sector
            t_sector = ""
            for s, s_tickers in SECTOR_MAP.items():
                if ticker in s_tickers:
                    t_sector = s
                    break

            # Get company name (cached)
            company_name = _get_company_name(ticker)

            alerts.append(VolumeAlert(
                ticker=ticker.upper(),
                company_name=company_name,
                date=str(date.today()),
                volume=latest_vol,
                avg_volume_20d=avg_20d,
                ratio=round(ratio, 2),
                signal=_classify_volume(ratio),
                price=round(price, 2),
                price_change_pct=round(float(price_chg), 2),
                sector=t_sector,
                pattern=pattern,
                is_breakout=is_breakout,
            ))
        except Exception as e:
            log.debug("Error processing ticker %s: %s", ticker, e)
            continue

    alerts.sort(key=lambda x: x.ratio, reverse=True)

    result = VolumeScreen(
        timestamp=str(datetime.now()),
        threshold=min_ratio,
        alerts=alerts,
        total_screened=len(ticker_list),
        total_flagged=len(alerts),
    )
    _set_cache(cache_key, result)
    log.info("Volume screen complete: %d flagged out of %d screened", len(alerts), len(ticker_list))
    return result


def get_ticker_volume_profile(ticker: str) -> Dict[str, Any]:
    """
    Get comprehensive volume profile for a ticker with real yfinance data.

    Args:
        ticker: Stock symbol

    Returns:
        VolumeProfile dataclass or no_data response
    """
    cache_key = f"vol_profile_{ticker}"
    cached = _get_cached(cache_key, ttl=_CACHE_TTL_PROFILE)
    if cached is not None:
        return cached

    ticker = ticker.upper()
    try:
        log.info("Fetching volume profile for %s", ticker)
        data = yf.download(ticker, period="3mo", progress=False)
        if data.empty:
            return no_data_response(
                entity=ticker,
                data_type="volume_profile",
                reason=NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"No data available for {ticker}"
            )

        volumes = data["Volume"].dropna().values.flatten()
        closes = data["Close"].dropna().values.flatten()

        if len(volumes) < 5:
            return no_data_response(
                entity=ticker,
                data_type="volume_profile",
                reason=NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"Insufficient data for {ticker} - only {len(volumes)} bars"
            )

        latest_vol = int(volumes[-1])
        avg_20d = int(np.mean(volumes[-20:])) if len(volumes) >= 20 else int(np.mean(volumes))
        avg_50d = int(np.mean(volumes[-50:])) if len(volumes) >= 50 else int(np.mean(volumes))
        ratio = latest_vol / avg_20d if avg_20d > 0 else 0

        # Count spikes (>2x) and breakouts in last 30 days
        spikes = 0
        breakouts = 0
        for i in range(-min(30, len(volumes)), 0):
            v = volumes[i]
            if v > avg_20d * 2:
                spikes += 1
                # Check if this was a breakout (price up too)
                if i < -1 and closes[i] > closes[i - 1] * 1.02:
                    breakouts += 1

        # Volume trend analysis
        if len(volumes) >= 20:
            recent_avg = np.mean(volumes[-10:])
            older_avg = np.mean(volumes[-20:-10])
            if recent_avg > older_avg * 1.2:
                trend = "increasing"
            elif recent_avg < older_avg * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        price = float(closes[-1]) if len(closes) > 0 else 0

        # Calculate relative volume (vs typical market volume)
        # This is simplified - ideally compare to sector average
        relative_volume = round(ratio, 2)

        # Get company name (cached) and sector
        company_name = _get_company_name(ticker)
        t_sector = ""
        for s, s_tickers in SECTOR_MAP.items():
            if ticker in s_tickers:
                t_sector = s
                break

        result = VolumeProfile(
            ticker=ticker,
            company_name=company_name,
            avg_volume_20d=avg_20d,
            avg_volume_50d=avg_50d,
            latest_volume=latest_vol,
            latest_ratio=round(ratio, 2),
            latest_signal=_classify_volume(ratio),
            spikes_30d=spikes,
            volume_trend=trend,
            price=round(price, 2),
            sector=t_sector,
            relative_volume=relative_volume,
            breakout_count_30d=breakouts,
        )
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.error("Volume profile failed for %s: %s", ticker, e)
        return no_data_response(
            entity=ticker,
            data_type="volume_profile",
            reason=NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def get_sector_volume_flow(sector: str) -> Dict[str, Any]:
    """
    Get sector-level volume flow analysis using real yfinance data.

    Args:
        sector: Sector name (Technology, Consumer, Finance, Industrial, Other)

    Returns:
        SectorVolumeFlow dataclass or no_data response
    """
    if sector not in SECTOR_MAP:
        return no_data_response(
            entity=sector,
            data_type="sector_volume_flow",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="internal",
            details=f"Unknown sector: {sector}. Available: {list(SECTOR_MAP.keys())}"
        )

    cache_key = f"sector_flow_{sector}"
    cached = _get_cached(cache_key, ttl=_CACHE_TTL_REALTIME)
    if cached is not None:
        return cached

    tickers = SECTOR_MAP[sector]
    try:
        log.info("Fetching sector volume flow for %s (%d tickers)", sector, len(tickers))
        data = yf.download(tickers, period="5d", progress=False, threads=True)
        if data.empty:
            return no_data_response(
                entity=sector,
                data_type="sector_volume_flow",
                reason=NoDataReason.API_UNAVAILABLE,
                source="yfinance",
                details=f"No data available for sector {sector}"
            )

        total_vol = 0
        ratios = []
        top_mover = ""
        top_ratio = 0.0

        for ticker in tickers:
            try:
                if len(tickers) > 1:
                    vol_series = data["Volume"][ticker].dropna().values if ticker in data["Volume"].columns else np.array([])
                else:
                    vol_series = data["Volume"].dropna().values.flatten()

                if len(vol_series) < 2:
                    continue

                latest = int(vol_series[-1])
                avg = int(np.mean(vol_series[:-1])) if len(vol_series) > 1 else latest
                ratio = latest / avg if avg > 0 else 1.0

                total_vol += latest
                ratios.append(ratio)

                if ratio > top_ratio:
                    top_ratio = ratio
                    top_mover = ticker
            except Exception as e:
                log.debug("Error processing %s in sector %s: %s", ticker, sector, e)
                continue

        avg_ratio = round(float(np.mean(ratios)), 2) if ratios else 1.0
        if avg_ratio > 1.3:
            direction = "inflow"
        elif avg_ratio < 0.7:
            direction = "outflow"
        else:
            direction = "neutral"

        result = SectorVolumeFlow(
            sector=sector,
            tickers=tickers,
            total_volume=total_vol,
            avg_ratio=avg_ratio,
            direction=direction,
            top_mover=top_mover,
            top_mover_ratio=round(top_ratio, 2),
        )
        _set_cache(cache_key, result)
        log.info("Sector flow for %s: direction=%s, avg_ratio=%.2f", sector, direction, avg_ratio)
        return result
    except Exception as e:
        log.error("Sector flow failed for %s: %s", sector, e)
        return no_data_response(
            entity=sector,
            data_type="sector_volume_flow",
            reason=NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


# ── Serializers ───────────────────────────────────────────────────────────────

def volume_bar_to_dict(bar) -> dict:
    if isinstance(bar, dict):
        return bar
    return {
        "ticker": bar.ticker,
        "date": bar.date,
        "volume": bar.volume,
        "avg_volume_20d": bar.avg_volume_20d,
        "ratio": bar.ratio,
        "signal": bar.signal.value if hasattr(bar.signal, "value") else bar.signal,
        "price": bar.price,
        "price_change_pct": bar.price_change_pct,
    }


def alert_to_dict(alert) -> dict:
    if isinstance(alert, dict):
        return alert
    return {
        "ticker": alert.ticker,
        "company_name": alert.company_name,
        "date": alert.date,
        "volume": alert.volume,
        "avg_volume_20d": alert.avg_volume_20d,
        "ratio": alert.ratio,
        "signal": alert.signal.value if hasattr(alert.signal, "value") else alert.signal,
        "price": alert.price,
        "price_change_pct": alert.price_change_pct,
        "sector": alert.sector,
        "pattern": alert.pattern.value if hasattr(alert.pattern, "value") else alert.pattern,
        "is_breakout": alert.is_breakout,
    }


def screen_to_dict(screen) -> dict:
    if isinstance(screen, dict):
        return screen
    return {
        "timestamp": screen.timestamp,
        "threshold": screen.threshold,
        "total_screened": screen.total_screened,
        "total_flagged": screen.total_flagged,
        "alerts": [alert_to_dict(a) for a in screen.alerts],
    }


def profile_to_dict(profile) -> dict:
    if isinstance(profile, dict):
        return profile
    return {
        "ticker": profile.ticker,
        "company_name": profile.company_name,
        "avg_volume_20d": profile.avg_volume_20d,
        "avg_volume_50d": profile.avg_volume_50d,
        "latest_volume": profile.latest_volume,
        "latest_ratio": profile.latest_ratio,
        "latest_signal": profile.latest_signal.value if hasattr(profile.latest_signal, "value") else profile.latest_signal,
        "spikes_30d": profile.spikes_30d,
        "volume_trend": profile.volume_trend,
        "price": profile.price,
        "sector": profile.sector,
        "relative_volume": profile.relative_volume,
        "breakout_count_30d": profile.breakout_count_30d,
    }


def sector_flow_to_dict(flow) -> dict:
    if isinstance(flow, dict):
        return flow
    return {
        "sector": flow.sector,
        "tickers": flow.tickers,
        "total_volume": flow.total_volume,
        "avg_ratio": flow.avg_ratio,
        "direction": flow.direction,
        "top_mover": flow.top_mover,
        "top_mover_ratio": flow.top_mover_ratio,
    }


def breakout_to_dict(breakout) -> dict:
    if isinstance(breakout, dict):
        return breakout
    return {
        "ticker": breakout.ticker,
        "company_name": breakout.company_name,
        "date": breakout.date,
        "volume": breakout.volume,
        "volume_ratio": breakout.volume_ratio,
        "price": breakout.price,
        "price_change_pct": breakout.price_change_pct,
        "pattern": breakout.pattern.value if hasattr(breakout.pattern, "value") else breakout.pattern,
        "is_confirmed": breakout.is_confirmed,
        "sector": breakout.sector,
    }


# ── Additional Screening Functions ────────────────────────────────────────────


def screen_volume_breakouts(
    tickers: Optional[List[str]] = None,
    min_volume_ratio: float = 2.0,
    min_price_change: float = 2.0,
    sector: Optional[str] = None
) -> Dict[str, Any]:
    """
    Screen for volume breakouts with price confirmation using real yfinance data.

    A breakout is defined as:
    - Volume > min_volume_ratio times average (default 2x)
    - Price change > min_price_change percent (default 2%)

    Args:
        tickers: Custom ticker list (uses DEFAULT_WATCHLIST if None)
        min_volume_ratio: Minimum volume ratio (default 2.0)
        min_price_change: Minimum price change % (default 2.0)
        sector: Filter by sector

    Returns:
        Dict with 'breakouts' list or no_data response
    """
    cache_key = f"vol_breakouts_{min_volume_ratio}_{min_price_change}_{sector}"
    cached = _get_cached(cache_key, ttl=_CACHE_TTL_REALTIME)
    if cached is not None:
        return cached

    ticker_list = tickers or DEFAULT_WATCHLIST
    if sector and sector in SECTOR_MAP:
        ticker_list = SECTOR_MAP[sector]

    try:
        log.info("Screening %d tickers for volume breakouts", len(ticker_list))
        data = yf.download(ticker_list, period="1mo", progress=False, threads=True)
        if data.empty:
            return no_data_response(
                entity="watchlist",
                data_type="volume_breakouts",
                reason=NoDataReason.API_UNAVAILABLE,
                source="yfinance",
                details="Failed to fetch data for breakout screening"
            )
    except Exception as e:
        log.error("Volume breakout screen failed: %s", e)
        return no_data_response(
            entity="watchlist",
            data_type="volume_breakouts",
            reason=NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )

    breakouts = []
    for ticker in ticker_list:
        try:
            if len(ticker_list) > 1:
                vol_series = data["Volume"][ticker].dropna().values if ticker in data["Volume"].columns else np.array([])
                close_series = data["Close"][ticker].dropna().values if ticker in data["Close"].columns else np.array([])
            else:
                vol_series = data["Volume"].dropna().values.flatten()
                close_series = data["Close"].dropna().values.flatten()

            if len(vol_series) < 5 or len(close_series) < 2:
                continue

            latest_vol = int(vol_series[-1])
            avg_20d = int(np.mean(vol_series[-20:])) if len(vol_series) >= 20 else int(np.mean(vol_series))
            vol_ratio = latest_vol / avg_20d if avg_20d > 0 else 0

            price = float(close_series[-1])
            price_chg = ((close_series[-1] / close_series[-2]) - 1) * 100

            # Check breakout criteria
            if vol_ratio < min_volume_ratio:
                continue
            if abs(price_chg) < min_price_change:
                continue

            # Determine pattern
            pattern = _classify_price_volume_pattern(vol_ratio, price_chg)

            # Check if confirmed (price held up)
            is_confirmed = _is_breakout_confirmed(close_series, len(close_series) - 1)

            # Get sector
            t_sector = ""
            for s, s_tickers in SECTOR_MAP.items():
                if ticker in s_tickers:
                    t_sector = s
                    break

            company_name = _get_company_name(ticker)

            breakouts.append(VolumeBreakout(
                ticker=ticker.upper(),
                company_name=company_name,
                date=str(date.today()),
                volume=latest_vol,
                volume_ratio=round(vol_ratio, 2),
                price=round(price, 2),
                price_change_pct=round(float(price_chg), 2),
                pattern=pattern,
                is_confirmed=is_confirmed,
                sector=t_sector,
            ))
        except Exception as e:
            log.debug("Error processing breakout for %s: %s", ticker, e)
            continue

    # Sort by volume ratio descending
    breakouts.sort(key=lambda x: x.volume_ratio, reverse=True)

    result = {
        "timestamp": str(datetime.now()),
        "min_volume_ratio": min_volume_ratio,
        "min_price_change": min_price_change,
        "total_screened": len(ticker_list),
        "total_breakouts": len(breakouts),
        "breakouts": [breakout_to_dict(b) for b in breakouts],
        "source": "yfinance",
    }
    _set_cache(cache_key, result)
    log.info("Breakout screen complete: %d breakouts found", len(breakouts))
    return result


def get_relative_volume_ranking(
    tickers: Optional[List[str]] = None,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Get relative volume ranking across watchlist using real yfinance data.

    Ranks stocks by their current volume relative to their 20-day average.

    Args:
        tickers: Custom ticker list (uses DEFAULT_WATCHLIST if None)
        top_n: Number of top movers to return (default 10)

    Returns:
        Dict with 'rankings' list or no_data response
    """
    cache_key = f"rel_vol_rank_{top_n}"
    cached = _get_cached(cache_key, ttl=_CACHE_TTL_REALTIME)
    if cached is not None:
        return cached

    ticker_list = tickers or DEFAULT_WATCHLIST

    try:
        log.info("Calculating relative volume ranking for %d tickers", len(ticker_list))
        data = yf.download(ticker_list, period="1mo", progress=False, threads=True)
        if data.empty:
            return no_data_response(
                entity="watchlist",
                data_type="relative_volume_ranking",
                reason=NoDataReason.API_UNAVAILABLE,
                source="yfinance",
                details="Failed to fetch data for volume ranking"
            )
    except Exception as e:
        log.error("Relative volume ranking failed: %s", e)
        return no_data_response(
            entity="watchlist",
            data_type="relative_volume_ranking",
            reason=NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )

    rankings = []
    for ticker in ticker_list:
        try:
            if len(ticker_list) > 1:
                vol_series = data["Volume"][ticker].dropna().values if ticker in data["Volume"].columns else np.array([])
                close_series = data["Close"][ticker].dropna().values if ticker in data["Close"].columns else np.array([])
            else:
                vol_series = data["Volume"].dropna().values.flatten()
                close_series = data["Close"].dropna().values.flatten()

            if len(vol_series) < 5:
                continue

            latest_vol = int(vol_series[-1])
            avg_20d = int(np.mean(vol_series[-20:])) if len(vol_series) >= 20 else int(np.mean(vol_series))
            ratio = latest_vol / avg_20d if avg_20d > 0 else 0

            price = float(close_series[-1]) if len(close_series) > 0 else 0
            price_chg = ((close_series[-1] / close_series[-2]) - 1) * 100 if len(close_series) >= 2 else 0

            # Get sector
            t_sector = ""
            for s, s_tickers in SECTOR_MAP.items():
                if ticker in s_tickers:
                    t_sector = s
                    break

            rankings.append({
                "ticker": ticker.upper(),
                "company_name": _get_company_name(ticker),
                "volume": latest_vol,
                "avg_volume_20d": avg_20d,
                "relative_volume": round(ratio, 2),
                "signal": _classify_volume(ratio).value,
                "price": round(price, 2),
                "price_change_pct": round(float(price_chg), 2),
                "sector": t_sector,
            })
        except Exception as e:
            log.debug("Error calculating relative volume for %s: %s", ticker, e)
            continue

    # Sort by relative volume descending
    rankings.sort(key=lambda x: x["relative_volume"], reverse=True)

    result = {
        "timestamp": str(datetime.now()),
        "total_tickers": len(ticker_list),
        "top_n": top_n,
        "rankings": rankings[:top_n],
        "all_rankings": rankings,
        "source": "yfinance",
    }
    _set_cache(cache_key, result)
    return result


def get_volume_trend_analysis(ticker: str, days: int = 30) -> Dict[str, Any]:
    """
    Analyze volume trend for a single ticker using real yfinance data.

    Args:
        ticker: Stock symbol
        days: Number of days for analysis (default 30)

    Returns:
        Dict with trend analysis or no_data response
    """
    cache_key = f"vol_trend_{ticker}_{days}"
    cached = _get_cached(cache_key, ttl=_CACHE_TTL_PROFILE)
    if cached is not None:
        return cached

    ticker = ticker.upper()
    try:
        log.info("Analyzing volume trend for %s over %d days", ticker, days)
        period = "1mo" if days <= 30 else "3mo" if days <= 90 else "6mo"
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            return no_data_response(
                entity=ticker,
                data_type="volume_trend",
                reason=NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"No data available for {ticker}"
            )

        volumes = data["Volume"].dropna().values.flatten()
        closes = data["Close"].dropna().values.flatten()
        dates = [str(d.date()) for d in data.index]

        if len(volumes) < 10:
            return no_data_response(
                entity=ticker,
                data_type="volume_trend",
                reason=NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"Insufficient data for trend analysis - only {len(volumes)} bars"
            )

        # Calculate various averages
        avg_5d = int(np.mean(volumes[-5:])) if len(volumes) >= 5 else int(np.mean(volumes))
        avg_10d = int(np.mean(volumes[-10:])) if len(volumes) >= 10 else int(np.mean(volumes))
        avg_20d = int(np.mean(volumes[-20:])) if len(volumes) >= 20 else int(np.mean(volumes))
        avg_50d = int(np.mean(volumes[-50:])) if len(volumes) >= 50 else avg_20d

        # Trend direction
        if avg_5d > avg_20d * 1.2:
            short_term_trend = "increasing"
        elif avg_5d < avg_20d * 0.8:
            short_term_trend = "decreasing"
        else:
            short_term_trend = "stable"

        if avg_10d > avg_50d * 1.15:
            medium_term_trend = "increasing"
        elif avg_10d < avg_50d * 0.85:
            medium_term_trend = "decreasing"
        else:
            medium_term_trend = "stable"

        # Count spike days (>2x average)
        spike_days = sum(1 for v in volumes[-days:] if v > avg_20d * 2)

        # Volume momentum (recent vs older)
        recent_avg = np.mean(volumes[-5:]) if len(volumes) >= 5 else volumes[-1]
        older_avg = np.mean(volumes[-20:-10]) if len(volumes) >= 20 else np.mean(volumes)
        momentum = round((recent_avg / older_avg - 1) * 100, 1) if older_avg > 0 else 0

        # Daily volume data for charting
        daily_data = []
        for i in range(-min(days, len(volumes)), 0):
            daily_data.append({
                "date": dates[i] if i + len(dates) >= 0 else "",
                "volume": int(volumes[i]),
                "price": round(float(closes[i]), 2) if i + len(closes) >= 0 else 0,
            })

        company_name = _get_company_name(ticker)

        result = {
            "ticker": ticker,
            "company_name": company_name,
            "analysis_period_days": days,
            "averages": {
                "avg_5d": avg_5d,
                "avg_10d": avg_10d,
                "avg_20d": avg_20d,
                "avg_50d": avg_50d,
            },
            "trends": {
                "short_term": short_term_trend,
                "medium_term": medium_term_trend,
            },
            "spike_days_in_period": spike_days,
            "volume_momentum_pct": momentum,
            "latest_volume": int(volumes[-1]),
            "latest_ratio": round(volumes[-1] / avg_20d, 2) if avg_20d > 0 else 0,
            "daily_data": daily_data[-30:],  # Last 30 days for charting
            "source": "yfinance",
            "timestamp": str(datetime.now()),
        }
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.error("Volume trend analysis failed for %s: %s", ticker, e)
        return no_data_response(
            entity=ticker,
            data_type="volume_trend",
            reason=NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def clear_cache():
    """Clear all cached data."""
    global _cache
    _cache = {}
    log.info("Volume screening cache cleared")
