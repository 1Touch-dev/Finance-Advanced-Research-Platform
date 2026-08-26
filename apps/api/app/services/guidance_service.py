"""
Guidance vs Actual Tracking Service (Band B #22)

Provides company guidance and revenue/earnings estimates using real Finnhub data:
- /stock/revenue-estimate - Revenue estimates
- /stock/eps-estimate - EPS estimates
- /stock/earnings - Actual vs estimate data

Features:
- Real revenue estimates (quarterly and annual)
- Real EPS estimates
- Guidance trends from historical estimates
- Estimate revisions tracking (up/down over time)
- Caching with 20-minute TTL
- Proper no_data pattern when data unavailable
"""
import os
import time
import logging
import requests
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date, timedelta
from enum import Enum
from dataclasses import dataclass, field

from app.core.no_data import no_data_response, NoDataReason

log = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"

# Cache storage
_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 1200  # 20 minutes (within 15-30 min range)
_REQUEST_TIMEOUT = 12


class GuidanceMetric(str, Enum):
    EPS = "eps"
    REVENUE = "revenue"


class GuidanceOutcome(str, Enum):
    SIGNIFICANTLY_BEAT = "significantly_beat"
    BEAT = "beat"
    MET = "met"
    MISSED = "missed"
    SIGNIFICANTLY_MISSED = "significantly_missed"


class RevisionDirection(str, Enum):
    RAISED = "raised"
    LOWERED = "lowered"
    MAINTAINED = "maintained"


class CredibilityTier(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


@dataclass
class GuidanceRecord:
    ticker: str
    metric: str
    fiscal_year: int
    fiscal_period: str
    guidance_low: float
    guidance_high: float
    guidance_mid: float
    num_analysts: int
    date_issued: str
    source: str = "Finnhub"


@dataclass
class GuidanceVsActual:
    ticker: str
    metric: str
    fiscal_year: int
    fiscal_period: str
    guidance_low: float
    guidance_high: float
    guidance_mid: float
    actual: float
    variance_pct: float
    outcome: GuidanceOutcome


@dataclass
class GuidanceRevision:
    ticker: str
    date: str
    fiscal_year: int
    fiscal_period: str
    metric: str
    old_low: float
    old_high: float
    old_mid: float
    new_low: float
    new_high: float
    new_mid: float
    direction: RevisionDirection
    change_pct: float


@dataclass
class GuidanceTrend:
    ticker: str
    metric: str
    periods_analyzed: int
    direction: TrendDirection
    avg_revision_pct: float
    revisions_up: int
    revisions_down: int
    revisions_unchanged: int
    trend_strength: float  # 0-100


@dataclass
class ManagementCredibility:
    ticker: str
    company_name: str
    credibility_score: float
    credibility_tier: CredibilityTier
    beat_rate: float
    meet_or_beat_rate: float
    avg_variance_pct: float
    revision_tendency: str
    quarters_analyzed: int
    green_flags: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)


@dataclass
class FullGuidanceTrack:
    ticker: str
    company_name: str
    current_guidance: List[GuidanceRecord]
    history: List[GuidanceVsActual]
    revisions: List[GuidanceRevision]
    trends: Dict[str, GuidanceTrend]
    credibility: ManagementCredibility


# Company name lookup
COMPANY_NAMES: Dict[str, str] = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "NVDA": "NVIDIA Corporation",
    "META": "Meta Platforms Inc.",
    "TSLA": "Tesla Inc.",
    "AMD": "Advanced Micro Devices",
    "CRM": "Salesforce Inc.",
    "NFLX": "Netflix Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "BAC": "Bank of America Corp.",
    "WMT": "Walmart Inc.",
    "DIS": "The Walt Disney Company",
    "INTC": "Intel Corporation",
}


# ── Caching Functions ─────────────────────────────────────────────────────────


def _get_cached(key: str) -> Optional[Any]:
    """Get data from cache if still valid."""
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            log.debug("Cache hit for %s", key)
            return entry["data"]
        else:
            log.debug("Cache expired for %s", key)
    return None


def _set_cache(key: str, data: Any) -> None:
    """Store data in cache with timestamp."""
    _cache[key] = {"data": data, "ts": time.time()}
    log.debug("Cache set for %s", key)


def clear_cache(ticker: Optional[str] = None) -> None:
    """Clear cache for a ticker or all cache."""
    global _cache
    if ticker:
        keys_to_remove = [k for k in _cache if ticker.upper() in k]
        for k in keys_to_remove:
            del _cache[k]
        log.info("Cleared cache for %s (%d entries)", ticker, len(keys_to_remove))
    else:
        count = len(_cache)
        _cache = {}
        log.info("Cleared all cache (%d entries)", count)


# ── Finnhub API Functions ─────────────────────────────────────────────────────


def _finnhub_get(endpoint: str, params: Optional[dict] = None) -> Optional[Any]:
    """Make GET request to Finnhub API with error handling."""
    if not FINNHUB_KEY:
        log.warning("FINNHUB_API_KEY not set in environment")
        return None

    params = params or {}
    params["token"] = FINNHUB_KEY

    try:
        url = f"{FINNHUB_BASE}{endpoint}"
        log.debug("Finnhub request: %s params=%s", endpoint, {k: v for k, v in params.items() if k != "token"})

        r = requests.get(url, params=params, timeout=_REQUEST_TIMEOUT)

        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            log.warning("Finnhub rate limited for %s", endpoint)
        elif r.status_code == 401:
            log.warning("Finnhub API key invalid")
        elif r.status_code == 403:
            log.warning("Finnhub access denied for %s", endpoint)
        else:
            log.warning("Finnhub %s returned %s: %s", endpoint, r.status_code, r.text[:200])
    except requests.exceptions.Timeout:
        log.warning("Finnhub %s request timed out", endpoint)
    except requests.exceptions.ConnectionError:
        log.warning("Finnhub connection error for %s", endpoint)
    except Exception as e:
        log.warning("Finnhub %s request failed: %s", endpoint, e)

    return None


def _fetch_eps_estimates(ticker: str) -> List[Dict[str, Any]]:
    """Fetch EPS estimates from Finnhub."""
    cache_key = f"guid_eps_{ticker.upper()}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = _finnhub_get("/stock/eps-estimate", {"symbol": ticker.upper()})
    result = data.get("data", []) if isinstance(data, dict) else []

    _set_cache(cache_key, result)
    log.info("Fetched %d EPS estimates for %s", len(result), ticker)
    return result


def _fetch_revenue_estimates(ticker: str) -> List[Dict[str, Any]]:
    """Fetch revenue estimates from Finnhub."""
    cache_key = f"guid_rev_{ticker.upper()}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = _finnhub_get("/stock/revenue-estimate", {"symbol": ticker.upper()})
    result = data.get("data", []) if isinstance(data, dict) else []

    _set_cache(cache_key, result)
    log.info("Fetched %d revenue estimates for %s", len(result), ticker)
    return result


def _fetch_earnings(ticker: str) -> List[Dict[str, Any]]:
    """Fetch actual earnings data from Finnhub."""
    cache_key = f"guid_earn_{ticker.upper()}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = _finnhub_get("/stock/earnings", {"symbol": ticker.upper()})
    result = data if isinstance(data, list) else []

    _set_cache(cache_key, result)
    log.info("Fetched %d earnings records for %s", len(result), ticker)
    return result


def _fetch_recommendation_trends(ticker: str) -> List[Dict[str, Any]]:
    """Fetch analyst recommendation trends (helps track estimate changes)."""
    cache_key = f"guid_rec_{ticker.upper()}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    data = _finnhub_get("/stock/recommendation", {"symbol": ticker.upper()})
    result = data if isinstance(data, list) else []

    _set_cache(cache_key, result)
    return result


# ── Helper Functions ──────────────────────────────────────────────────────────


def _parse_fiscal_period(period: Any) -> str:
    """Parse fiscal period string from estimate data."""
    if not period:
        return "FY"

    period_str = str(period).upper()
    if "Q1" in period_str or period_str.endswith("-03"):
        return "Q1"
    elif "Q2" in period_str or period_str.endswith("-06"):
        return "Q2"
    elif "Q3" in period_str or period_str.endswith("-09"):
        return "Q3"
    elif "Q4" in period_str or period_str.endswith("-12"):
        return "Q4"
    return "FY"


def _classify_outcome(actual: float, low: float, high: float, mid: float) -> GuidanceOutcome:
    """Classify outcome based on actual vs guidance range."""
    if mid == 0:
        return GuidanceOutcome.MET

    variance_pct = ((actual - mid) / abs(mid)) * 100

    if actual > high * 1.05:
        return GuidanceOutcome.SIGNIFICANTLY_BEAT
    elif actual > high:
        return GuidanceOutcome.BEAT
    elif actual >= low:
        return GuidanceOutcome.MET
    elif actual >= low * 0.95:
        return GuidanceOutcome.MISSED
    else:
        return GuidanceOutcome.SIGNIFICANTLY_MISSED


def _classify_revision_direction(old_mid: float, new_mid: float) -> Tuple[RevisionDirection, float]:
    """Classify revision direction and calculate change percentage."""
    if old_mid == 0:
        return RevisionDirection.MAINTAINED, 0.0

    change_pct = ((new_mid - old_mid) / abs(old_mid)) * 100

    if change_pct > 1.0:
        return RevisionDirection.RAISED, round(change_pct, 2)
    elif change_pct < -1.0:
        return RevisionDirection.LOWERED, round(change_pct, 2)
    else:
        return RevisionDirection.MAINTAINED, round(change_pct, 2)


def _get_company_name(ticker: str) -> str:
    """Get company name from lookup or return ticker."""
    return COMPANY_NAMES.get(ticker.upper(), ticker.upper())


# ── Service Functions ─────────────────────────────────────────────────────────


def get_current_guidance(
    ticker: str,
    metric: GuidanceMetric = GuidanceMetric.EPS
) -> Dict[str, Any]:
    """
    Get current fiscal year guidance (forward estimates).

    Args:
        ticker: Stock ticker symbol
        metric: EPS or REVENUE

    Returns:
        Dict with guidance records or no_data response
    """
    ticker = ticker.upper()
    metric_val = metric.value if hasattr(metric, "value") else metric

    if not FINNHUB_KEY:
        return no_data_response(
            entity=ticker,
            data_type="guidance",
            reason=NoDataReason.API_KEY_MISSING,
            source="Finnhub"
        )

    if metric_val == "eps":
        estimates = _fetch_eps_estimates(ticker)
    else:
        estimates = _fetch_revenue_estimates(ticker)

    if not estimates:
        return no_data_response(
            entity=ticker,
            data_type=f"{metric_val}_guidance",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="Finnhub",
            details=f"No {metric_val.upper()} estimates found for {ticker}"
        )

    records = []
    for entry in estimates[:8]:  # Get up to 8 periods
        year = entry.get("year") or date.today().year
        period = entry.get("period", "annual")

        if metric_val == "eps":
            low = entry.get("epsLow") or 0
            high = entry.get("epsHigh") or 0
            avg = entry.get("epsAvg") or 0
            num_analysts = entry.get("numberAnalysts") or 0
        else:
            low = entry.get("revenueLow") or 0
            high = entry.get("revenueHigh") or 0
            avg = entry.get("revenueAvg") or 0
            num_analysts = entry.get("numberAnalysts") or 0

        mid = avg if avg else (low + high) / 2 if (low or high) else 0
        fiscal_period = _parse_fiscal_period(period)

        records.append(GuidanceRecord(
            ticker=ticker,
            metric=metric_val,
            fiscal_year=year,
            fiscal_period=fiscal_period,
            guidance_low=round(low, 4),
            guidance_high=round(high, 4),
            guidance_mid=round(mid, 4),
            num_analysts=num_analysts,
            date_issued=str(date.today()),
        ))

    return {
        "ticker": ticker,
        "metric": metric_val,
        "guidance": [guidance_record_to_dict(r) for r in records],
        "count": len(records),
        "source": "Finnhub",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_guidance_vs_actual(
    ticker: str,
    fiscal_year: Optional[int] = None,
    fiscal_period: Optional[str] = None,
    metric: GuidanceMetric = GuidanceMetric.EPS
) -> Dict[str, Any]:
    """
    Compare guidance vs actual results for a specific period.

    Args:
        ticker: Stock ticker symbol
        fiscal_year: Year to analyze (defaults to current year)
        fiscal_period: Period (Q1-Q4 or FY)
        metric: EPS or REVENUE

    Returns:
        Dict with comparison data or no_data response
    """
    ticker = ticker.upper()
    metric_val = metric.value if hasattr(metric, "value") else metric
    fy = fiscal_year or date.today().year

    if not FINNHUB_KEY:
        return no_data_response(
            entity=ticker,
            data_type="guidance_vs_actual",
            reason=NoDataReason.API_KEY_MISSING,
            source="Finnhub"
        )

    earnings = _fetch_earnings(ticker)

    if metric_val == "eps":
        estimates = _fetch_eps_estimates(ticker)
    else:
        estimates = _fetch_revenue_estimates(ticker)

    if not earnings:
        return no_data_response(
            entity=ticker,
            data_type="guidance_vs_actual",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="Finnhub",
            details=f"No earnings data found for {ticker}"
        )

    # Find actual from earnings for specified period
    actual = None
    actual_period = None
    for e in earnings:
        e_year = e.get("year", 0)
        e_quarter = e.get("quarter", 0)

        if e_year == fy:
            if fiscal_period is None or fiscal_period == f"Q{e_quarter}" or fiscal_period == "FY":
                actual = e.get("actual")
                actual_period = f"Q{e_quarter}" if e_quarter else "FY"
                break

    if actual is None:
        return no_data_response(
            entity=ticker,
            data_type="guidance_vs_actual",
            reason=NoDataReason.NO_FILINGS,
            source="Finnhub",
            details=f"No actual results found for {ticker} FY{fy}"
        )

    # Find guidance (estimate range) for this period
    low = high = mid = 0.0
    num_analysts = 0
    for entry in estimates:
        if entry.get("year") == fy:
            if metric_val == "eps":
                low = entry.get("epsLow") or 0
                high = entry.get("epsHigh") or 0
                mid = entry.get("epsAvg") or 0
                num_analysts = entry.get("numberAnalysts") or 0
            else:
                low = entry.get("revenueLow") or 0
                high = entry.get("revenueHigh") or 0
                mid = entry.get("revenueAvg") or 0
                num_analysts = entry.get("numberAnalysts") or 0
            break

    if not mid:
        mid = (low + high) / 2 if (low or high) else 0

    variance_pct = round(((actual - mid) / abs(mid)) * 100, 2) if mid != 0 else 0
    outcome = _classify_outcome(actual, low, high, mid)

    result = GuidanceVsActual(
        ticker=ticker,
        metric=metric_val,
        fiscal_year=fy,
        fiscal_period=actual_period or fiscal_period or "FY",
        guidance_low=round(low, 4),
        guidance_high=round(high, 4),
        guidance_mid=round(mid, 4),
        actual=round(actual, 4),
        variance_pct=variance_pct,
        outcome=outcome,
    )

    return {
        "comparison": vs_actual_to_dict(result),
        "num_analysts": num_analysts,
        "source": "Finnhub",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_guidance_history(
    ticker: str,
    metric: GuidanceMetric = GuidanceMetric.EPS,
    quarters: int = 12
) -> Dict[str, Any]:
    """
    Get historical guidance vs actual record.

    Args:
        ticker: Stock ticker symbol
        metric: EPS or REVENUE
        quarters: Number of quarters to analyze

    Returns:
        Dict with history or no_data response
    """
    ticker = ticker.upper()
    metric_val = metric.value if hasattr(metric, "value") else metric

    if not FINNHUB_KEY:
        return no_data_response(
            entity=ticker,
            data_type="guidance_history",
            reason=NoDataReason.API_KEY_MISSING,
            source="Finnhub"
        )

    earnings = _fetch_earnings(ticker)

    if not earnings:
        return no_data_response(
            entity=ticker,
            data_type="guidance_history",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="Finnhub",
            details=f"No earnings history found for {ticker}"
        )

    if metric_val == "eps":
        estimates = _fetch_eps_estimates(ticker)
    else:
        estimates = _fetch_revenue_estimates(ticker)

    # Build year -> estimate mapping
    estimate_map = {}
    for est in estimates:
        year = est.get("year")
        if year:
            estimate_map[year] = est

    history = []
    beats = 0
    misses = 0

    for e in earnings[:quarters]:
        year = e.get("year", 0)
        quarter = e.get("quarter", 0)
        actual = e.get("actual")
        estimate = e.get("estimate")

        if actual is None:
            continue

        # Use estimate from earnings as default, fallback to estimate data
        low = (estimate or 0) * 0.97 if estimate else 0
        high = (estimate or 0) * 1.03 if estimate else 0
        mid = estimate or 0

        # Check if we have proper estimate range from /eps-estimate
        if year in estimate_map:
            est = estimate_map[year]
            if metric_val == "eps":
                est_low = est.get("epsLow")
                est_high = est.get("epsHigh")
                est_avg = est.get("epsAvg")
                if est_low and est_high:
                    low = est_low
                    high = est_high
                    mid = est_avg or (low + high) / 2

        variance_pct = round(((actual - mid) / abs(mid)) * 100, 2) if mid != 0 else 0
        outcome = _classify_outcome(actual, low, high, mid)

        if outcome in [GuidanceOutcome.BEAT, GuidanceOutcome.SIGNIFICANTLY_BEAT]:
            beats += 1
        elif outcome in [GuidanceOutcome.MISSED, GuidanceOutcome.SIGNIFICANTLY_MISSED]:
            misses += 1

        history.append(GuidanceVsActual(
            ticker=ticker,
            metric=metric_val,
            fiscal_year=year,
            fiscal_period=f"Q{quarter}" if quarter else "FY",
            guidance_low=round(low, 4),
            guidance_high=round(high, 4),
            guidance_mid=round(mid, 4),
            actual=round(actual, 4),
            variance_pct=variance_pct,
            outcome=outcome,
        ))

    return {
        "ticker": ticker,
        "metric": metric_val,
        "history": [vs_actual_to_dict(h) for h in history],
        "count": len(history),
        "summary": {
            "beats": beats,
            "misses": misses,
            "met": len(history) - beats - misses,
            "beat_rate": round(beats / len(history) * 100, 1) if history else 0,
        },
        "source": "Finnhub",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_guidance_revisions(
    ticker: str,
    metric: GuidanceMetric = GuidanceMetric.EPS,
    fiscal_year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get guidance revision history tracking estimate changes over time.

    Since Finnhub doesn't provide historical revision data directly,
    we analyze the spread between periods to infer revision patterns.

    Args:
        ticker: Stock ticker symbol
        metric: EPS or REVENUE
        fiscal_year: Filter by fiscal year

    Returns:
        Dict with revisions or no_data response
    """
    ticker = ticker.upper()
    metric_val = metric.value if hasattr(metric, "value") else metric
    fy = fiscal_year or date.today().year

    if not FINNHUB_KEY:
        return no_data_response(
            entity=ticker,
            data_type="guidance_revisions",
            reason=NoDataReason.API_KEY_MISSING,
            source="Finnhub"
        )

    if metric_val == "eps":
        estimates = _fetch_eps_estimates(ticker)
    else:
        estimates = _fetch_revenue_estimates(ticker)

    if not estimates:
        return no_data_response(
            entity=ticker,
            data_type="guidance_revisions",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="Finnhub",
            details=f"No estimates found for {ticker}"
        )

    # Also fetch recommendation trends to help infer estimate changes
    rec_trends = _fetch_recommendation_trends(ticker)

    revisions = []

    # Analyze consecutive periods to detect revisions
    sorted_estimates = sorted(estimates, key=lambda x: (x.get("year", 0), x.get("period", "")))

    for i in range(1, len(sorted_estimates)):
        prev = sorted_estimates[i - 1]
        curr = sorted_estimates[i]

        # Only compare same fiscal year
        if prev.get("year") != curr.get("year"):
            continue

        if fiscal_year and prev.get("year") != fiscal_year:
            continue

        if metric_val == "eps":
            old_low = prev.get("epsLow") or 0
            old_high = prev.get("epsHigh") or 0
            old_avg = prev.get("epsAvg") or 0
            new_low = curr.get("epsLow") or 0
            new_high = curr.get("epsHigh") or 0
            new_avg = curr.get("epsAvg") or 0
        else:
            old_low = prev.get("revenueLow") or 0
            old_high = prev.get("revenueHigh") or 0
            old_avg = prev.get("revenueAvg") or 0
            new_low = curr.get("revenueLow") or 0
            new_high = curr.get("revenueHigh") or 0
            new_avg = curr.get("revenueAvg") or 0

        old_mid = old_avg or (old_low + old_high) / 2 if (old_low or old_high) else 0
        new_mid = new_avg or (new_low + new_high) / 2 if (new_low or new_high) else 0

        if old_mid == 0 or new_mid == old_mid:
            continue

        direction, change_pct = _classify_revision_direction(old_mid, new_mid)

        if direction != RevisionDirection.MAINTAINED:
            revisions.append(GuidanceRevision(
                ticker=ticker,
                date=str(date.today()),  # Revision date approximated
                fiscal_year=curr.get("year", fy),
                fiscal_period=_parse_fiscal_period(curr.get("period")),
                metric=metric_val,
                old_low=round(old_low, 4),
                old_high=round(old_high, 4),
                old_mid=round(old_mid, 4),
                new_low=round(new_low, 4),
                new_high=round(new_high, 4),
                new_mid=round(new_mid, 4),
                direction=direction,
                change_pct=change_pct,
            ))

    # Calculate revision stats
    raised_count = sum(1 for r in revisions if r.direction == RevisionDirection.RAISED)
    lowered_count = sum(1 for r in revisions if r.direction == RevisionDirection.LOWERED)

    return {
        "ticker": ticker,
        "metric": metric_val,
        "revisions": [revision_to_dict(r) for r in revisions],
        "count": len(revisions),
        "summary": {
            "raised": raised_count,
            "lowered": lowered_count,
            "net_direction": "raised" if raised_count > lowered_count else "lowered" if lowered_count > raised_count else "unchanged",
            "avg_change_pct": round(sum(r.change_pct for r in revisions) / len(revisions), 2) if revisions else 0,
        },
        "source": "Finnhub",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def calculate_guidance_trends(
    ticker: str,
    metric: GuidanceMetric = GuidanceMetric.EPS
) -> Dict[str, Any]:
    """
    Calculate guidance trends from historical estimates.

    Args:
        ticker: Stock ticker symbol
        metric: EPS or REVENUE

    Returns:
        Dict with trend analysis or no_data response
    """
    ticker = ticker.upper()
    metric_val = metric.value if hasattr(metric, "value") else metric

    if not FINNHUB_KEY:
        return no_data_response(
            entity=ticker,
            data_type="guidance_trends",
            reason=NoDataReason.API_KEY_MISSING,
            source="Finnhub"
        )

    # Get revisions to analyze trend
    revisions_data = get_guidance_revisions(ticker, metric)

    if "no_data" in revisions_data:
        return revisions_data

    revisions = revisions_data.get("revisions", [])

    # Also analyze historical beat/miss pattern
    history_data = get_guidance_history(ticker, metric, quarters=8)

    if "no_data" in history_data:
        return history_data

    history = history_data.get("history", [])

    # Calculate trend metrics
    raised = sum(1 for r in revisions if r.get("direction") == "raised")
    lowered = sum(1 for r in revisions if r.get("direction") == "lowered")
    total_revisions = raised + lowered

    avg_revision_pct = sum(r.get("change_pct", 0) for r in revisions) / len(revisions) if revisions else 0

    # Determine trend direction
    if raised > lowered * 1.5:
        direction = TrendDirection.IMPROVING
        trend_strength = min(100, (raised / max(total_revisions, 1)) * 100)
    elif lowered > raised * 1.5:
        direction = TrendDirection.DECLINING
        trend_strength = min(100, (lowered / max(total_revisions, 1)) * 100)
    else:
        direction = TrendDirection.STABLE
        trend_strength = 50

    # Enhance with beat/miss pattern
    beat_rate = history_data.get("summary", {}).get("beat_rate", 50)
    if beat_rate > 70:
        direction = TrendDirection.IMPROVING
        trend_strength = max(trend_strength, beat_rate)
    elif beat_rate < 30:
        direction = TrendDirection.DECLINING
        trend_strength = max(trend_strength, 100 - beat_rate)

    trend = GuidanceTrend(
        ticker=ticker,
        metric=metric_val,
        periods_analyzed=len(history),
        direction=direction,
        avg_revision_pct=round(avg_revision_pct, 2),
        revisions_up=raised,
        revisions_down=lowered,
        revisions_unchanged=len(revisions) - raised - lowered,
        trend_strength=round(trend_strength, 1),
    )

    return {
        "ticker": ticker,
        "metric": metric_val,
        "trend": {
            "direction": trend.direction.value,
            "strength": trend.trend_strength,
            "avg_revision_pct": trend.avg_revision_pct,
            "periods_analyzed": trend.periods_analyzed,
            "revisions_up": trend.revisions_up,
            "revisions_down": trend.revisions_down,
        },
        "beat_rate": beat_rate,
        "source": "Finnhub",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def calculate_management_credibility(ticker: str) -> Dict[str, Any]:
    """
    Calculate management credibility score from earnings history.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with credibility assessment or no_data response
    """
    ticker = ticker.upper()
    company_name = _get_company_name(ticker)

    if not FINNHUB_KEY:
        return no_data_response(
            entity=ticker,
            data_type="management_credibility",
            reason=NoDataReason.API_KEY_MISSING,
            source="Finnhub"
        )

    earnings = _fetch_earnings(ticker)

    if not earnings:
        return no_data_response(
            entity=ticker,
            data_type="management_credibility",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="Finnhub",
            details=f"No earnings data found for {ticker}"
        )

    beats = 0
    meets = 0
    misses = 0
    variances = []

    for e in earnings[:12]:  # Analyze up to 12 quarters
        actual = e.get("actual")
        estimate = e.get("estimate")

        if actual is None or estimate is None or estimate == 0:
            continue

        variance = ((actual - estimate) / abs(estimate)) * 100
        variances.append(variance)

        if actual > estimate * 1.01:
            beats += 1
        elif actual >= estimate * 0.99:
            meets += 1
        else:
            misses += 1

    total = beats + meets + misses
    if total == 0:
        return no_data_response(
            entity=ticker,
            data_type="management_credibility",
            reason=NoDataReason.NO_FILINGS,
            source="Finnhub",
            details=f"Insufficient earnings data for {ticker}"
        )

    beat_rate = round(beats / total * 100, 1)
    meet_or_beat_rate = round((beats + meets) / total * 100, 1)
    avg_variance = round(sum(variances) / len(variances), 2) if variances else 0

    # Score calculation
    score = 50.0
    score += beat_rate * 0.3  # Up to +30 for high beat rate
    score += (meet_or_beat_rate - 50) * 0.2  # Bonus for consistency
    if avg_variance > 0:
        score += min(10, avg_variance * 2)  # Bonus for positive variance
    else:
        score -= min(10, abs(avg_variance) * 2)

    score = max(0, min(100, score))

    # Determine tier
    if score >= 80:
        tier = CredibilityTier.EXCELLENT
    elif score >= 65:
        tier = CredibilityTier.GOOD
    elif score >= 45:
        tier = CredibilityTier.AVERAGE
    else:
        tier = CredibilityTier.POOR

    # Generate flags
    green_flags = []
    red_flags = []

    if beat_rate > 70:
        green_flags.append("Consistently beats estimates")
    if beat_rate > 80:
        green_flags.append("Exceptional beat record")
    if avg_variance > 3:
        green_flags.append("Conservative guidance pattern")
    if meet_or_beat_rate > 90:
        green_flags.append("Highly reliable guidance")

    if beat_rate < 40:
        red_flags.append("Frequently misses estimates")
    if avg_variance < -5:
        red_flags.append("Guidance appears overly optimistic")
    if misses > beats:
        red_flags.append("More misses than beats historically")

    # Revision tendency
    if avg_variance > 2:
        revision_tendency = "conservative"
    elif avg_variance < -2:
        revision_tendency = "aggressive"
    else:
        revision_tendency = "balanced"

    credibility = ManagementCredibility(
        ticker=ticker,
        company_name=company_name,
        credibility_score=round(score, 1),
        credibility_tier=tier,
        beat_rate=beat_rate,
        meet_or_beat_rate=meet_or_beat_rate,
        avg_variance_pct=avg_variance,
        revision_tendency=revision_tendency,
        quarters_analyzed=total,
        green_flags=green_flags,
        red_flags=red_flags,
    )

    return {
        "credibility": credibility_to_dict(credibility),
        "source": "Finnhub",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_full_guidance_track(ticker: str) -> Dict[str, Any]:
    """
    Get complete guidance dashboard for a ticker.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Comprehensive guidance analysis or no_data response
    """
    ticker = ticker.upper()
    company_name = _get_company_name(ticker)

    if not FINNHUB_KEY:
        return no_data_response(
            entity=ticker,
            data_type="guidance_track",
            reason=NoDataReason.API_KEY_MISSING,
            source="Finnhub"
        )

    # Fetch all components
    current_eps = get_current_guidance(ticker, GuidanceMetric.EPS)
    current_rev = get_current_guidance(ticker, GuidanceMetric.REVENUE)
    history = get_guidance_history(ticker, GuidanceMetric.EPS, quarters=8)
    revisions = get_guidance_revisions(ticker, GuidanceMetric.EPS)
    eps_trends = calculate_guidance_trends(ticker, GuidanceMetric.EPS)
    rev_trends = calculate_guidance_trends(ticker, GuidanceMetric.REVENUE)
    credibility = calculate_management_credibility(ticker)

    # Check if we have any real data
    has_data = False
    if "guidance" in current_eps and current_eps["guidance"]:
        has_data = True
    if "history" in history and history["history"]:
        has_data = True

    if not has_data:
        return no_data_response(
            entity=ticker,
            data_type="guidance_track",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="Finnhub",
            details=f"No guidance data available for {ticker}"
        )

    return {
        "ticker": ticker,
        "company_name": company_name,
        "current_guidance": {
            "eps": current_eps.get("guidance", []) if "guidance" in current_eps else [],
            "revenue": current_rev.get("guidance", []) if "guidance" in current_rev else [],
        },
        "history": history.get("history", []) if "history" in history else [],
        "history_summary": history.get("summary", {}) if "summary" in history else {},
        "revisions": revisions.get("revisions", []) if "revisions" in revisions else [],
        "revision_summary": revisions.get("summary", {}) if "summary" in revisions else {},
        "trends": {
            "eps": eps_trends.get("trend", {}) if "trend" in eps_trends else {},
            "revenue": rev_trends.get("trend", {}) if "trend" in rev_trends else {},
        },
        "credibility": credibility.get("credibility", {}) if "credibility" in credibility else {},
        "source": "Finnhub",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_estimate_consensus(
    ticker: str,
    metric: GuidanceMetric = GuidanceMetric.EPS
) -> Dict[str, Any]:
    """
    Get current analyst consensus estimates.

    Args:
        ticker: Stock ticker symbol
        metric: EPS or REVENUE

    Returns:
        Consensus data or no_data response
    """
    ticker = ticker.upper()
    metric_val = metric.value if hasattr(metric, "value") else metric

    if not FINNHUB_KEY:
        return no_data_response(
            entity=ticker,
            data_type="estimate_consensus",
            reason=NoDataReason.API_KEY_MISSING,
            source="Finnhub"
        )

    if metric_val == "eps":
        estimates = _fetch_eps_estimates(ticker)
    else:
        estimates = _fetch_revenue_estimates(ticker)

    if not estimates:
        return no_data_response(
            entity=ticker,
            data_type="estimate_consensus",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="Finnhub",
            details=f"No {metric_val.upper()} estimates found for {ticker}"
        )

    # Get the most recent estimate (typically current quarter)
    latest = estimates[0] if estimates else {}

    if metric_val == "eps":
        consensus = {
            "period": latest.get("period"),
            "year": latest.get("year"),
            "consensus": latest.get("epsAvg"),
            "high": latest.get("epsHigh"),
            "low": latest.get("epsLow"),
            "num_analysts": latest.get("numberAnalysts"),
        }
    else:
        consensus = {
            "period": latest.get("period"),
            "year": latest.get("year"),
            "consensus": latest.get("revenueAvg"),
            "high": latest.get("revenueHigh"),
            "low": latest.get("revenueLow"),
            "num_analysts": latest.get("numberAnalysts"),
        }

    # Calculate spread
    if consensus.get("high") and consensus.get("low"):
        spread = consensus["high"] - consensus["low"]
        consensus["spread"] = round(spread, 4)
        if consensus.get("consensus"):
            consensus["spread_pct"] = round((spread / abs(consensus["consensus"])) * 100, 2)

    return {
        "ticker": ticker,
        "metric": metric_val,
        "consensus": consensus,
        "all_periods": [{
            "period": e.get("period"),
            "year": e.get("year"),
            "estimate": e.get("epsAvg") if metric_val == "eps" else e.get("revenueAvg"),
            "num_analysts": e.get("numberAnalysts"),
        } for e in estimates[:4]],
        "source": "Finnhub",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ── Serializers ───────────────────────────────────────────────────────────────


def guidance_record_to_dict(rec: GuidanceRecord) -> Dict[str, Any]:
    """Convert GuidanceRecord to dictionary."""
    if isinstance(rec, dict):
        return rec
    return {
        "ticker": rec.ticker,
        "metric": rec.metric,
        "fiscal_year": rec.fiscal_year,
        "fiscal_period": rec.fiscal_period,
        "guidance_low": rec.guidance_low,
        "guidance_high": rec.guidance_high,
        "guidance_mid": rec.guidance_mid,
        "num_analysts": rec.num_analysts,
        "date_issued": rec.date_issued,
        "source": rec.source,
    }


def vs_actual_to_dict(va: GuidanceVsActual) -> Dict[str, Any]:
    """Convert GuidanceVsActual to dictionary."""
    if isinstance(va, dict):
        return va
    return {
        "ticker": va.ticker,
        "metric": va.metric,
        "fiscal_year": va.fiscal_year,
        "fiscal_period": va.fiscal_period,
        "guidance_low": va.guidance_low,
        "guidance_high": va.guidance_high,
        "guidance_mid": va.guidance_mid,
        "actual": va.actual,
        "variance_pct": va.variance_pct,
        "outcome": va.outcome.value if hasattr(va.outcome, "value") else va.outcome,
    }


def revision_to_dict(rev: GuidanceRevision) -> Dict[str, Any]:
    """Convert GuidanceRevision to dictionary."""
    if isinstance(rev, dict):
        return rev
    return {
        "ticker": rev.ticker,
        "date": rev.date,
        "fiscal_year": rev.fiscal_year,
        "fiscal_period": rev.fiscal_period,
        "metric": rev.metric,
        "old_range": {"low": rev.old_low, "high": rev.old_high, "mid": rev.old_mid},
        "new_range": {"low": rev.new_low, "high": rev.new_high, "mid": rev.new_mid},
        "direction": rev.direction.value if hasattr(rev.direction, "value") else rev.direction,
        "change_pct": rev.change_pct,
    }


def credibility_to_dict(cred: ManagementCredibility) -> Dict[str, Any]:
    """Convert ManagementCredibility to dictionary."""
    if isinstance(cred, dict):
        return cred
    return {
        "ticker": cred.ticker,
        "company_name": cred.company_name,
        "credibility_score": cred.credibility_score,
        "credibility_tier": cred.credibility_tier.value if hasattr(cred.credibility_tier, "value") else cred.credibility_tier,
        "beat_rate": cred.beat_rate,
        "meet_or_beat_rate": cred.meet_or_beat_rate,
        "avg_variance_pct": cred.avg_variance_pct,
        "revision_tendency": cred.revision_tendency,
        "quarters_analyzed": cred.quarters_analyzed,
        "green_flags": cred.green_flags,
        "red_flags": cred.red_flags,
    }


def guidance_track_to_dict(track: FullGuidanceTrack) -> Dict[str, Any]:
    """Convert FullGuidanceTrack to dictionary."""
    if isinstance(track, dict):
        return track
    return {
        "ticker": track.ticker,
        "company_name": track.company_name,
        "current_guidance": [guidance_record_to_dict(r) for r in track.current_guidance],
        "history": [vs_actual_to_dict(h) for h in track.history],
        "revisions": [revision_to_dict(r) for r in track.revisions],
        "trends": {k: {"direction": v.direction.value, "strength": v.trend_strength} for k, v in track.trends.items()},
        "credibility": credibility_to_dict(track.credibility),
    }


# ── Data Info ─────────────────────────────────────────────────────────────────


def get_finnhub_guidance_info() -> Dict[str, Any]:
    """Get information about Finnhub guidance data availability."""
    return {
        "source": "Finnhub",
        "api_endpoints": [
            "/stock/eps-estimate",
            "/stock/revenue-estimate",
            "/stock/earnings",
            "/stock/recommendation",
        ],
        "api_key_set": bool(FINNHUB_KEY),
        "cache_ttl_seconds": _CACHE_TTL,
        "update_frequency": "Real-time",
        "cost": "FREE (with rate limits)",
        "documentation": "https://finnhub.io/docs/api",
        "features": [
            "EPS estimates (quarterly and annual)",
            "Revenue estimates",
            "Actual vs estimate comparisons",
            "Guidance trend analysis",
            "Estimate revision tracking",
            "Management credibility scoring",
        ],
    }
