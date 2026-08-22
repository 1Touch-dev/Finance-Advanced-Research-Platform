"""
Guidance vs Actual Tracking Service (Band B #22)
Uses Finnhub revenue-estimate and eps-estimate endpoints for forward guidance.
"""
import os
import time
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"

_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800


class GuidanceMetric(str, Enum):
    EPS = "eps"
    REVENUE = "revenue"
    GROSS_MARGIN = "gross_margin"


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


@dataclass
class GuidanceRecord:
    ticker: str
    metric: str
    fiscal_year: int
    fiscal_period: str
    guidance_low: float
    guidance_high: float
    guidance_mid: float
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
    metric: str
    old_low: float
    old_high: float
    new_low: float
    new_high: float
    direction: RevisionDirection
    change_pct: float


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
    credibility: ManagementCredibility


COMPANY_GUIDANCE_DATA: Dict[str, str] = {
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
}


def _get_cached(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]
    return None


def _set_cache(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


def _finnhub_get(endpoint: str, params: dict = None):
    if not FINNHUB_KEY:
        return None
    params = params or {}
    params["token"] = FINNHUB_KEY
    try:
        r = requests.get(f"{FINNHUB_BASE}{endpoint}", params=params, timeout=12)
        if r.status_code == 200:
            return r.json()
        log.warning("Finnhub %s → %s", endpoint, r.status_code)
    except Exception as e:
        log.warning("Finnhub %s failed: %s", endpoint, e)
    return None


def _fetch_eps_estimates(ticker: str) -> list:
    cache_key = f"guid_eps_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/eps-estimate", {"symbol": ticker.upper()})
    result = data.get("data", []) if isinstance(data, dict) else []
    _set_cache(cache_key, result)
    return result


def _fetch_revenue_estimates(ticker: str) -> list:
    cache_key = f"guid_rev_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/revenue-estimate", {"symbol": ticker.upper()})
    result = data.get("data", []) if isinstance(data, dict) else []
    _set_cache(cache_key, result)
    return result


def _fetch_earnings(ticker: str) -> list:
    cache_key = f"guid_earn_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/earnings", {"symbol": ticker.upper()})
    result = data if isinstance(data, list) else []
    _set_cache(cache_key, result)
    return result


def _classify_outcome(actual: float, low: float, high: float) -> GuidanceOutcome:
    if high == low:
        mid = high
        if actual > mid * 1.05:
            return GuidanceOutcome.SIGNIFICANTLY_BEAT
        elif actual > mid * 1.01:
            return GuidanceOutcome.BEAT
        elif actual >= mid * 0.99:
            return GuidanceOutcome.MET
        elif actual >= mid * 0.95:
            return GuidanceOutcome.MISSED
        else:
            return GuidanceOutcome.SIGNIFICANTLY_MISSED

    if actual > high * 1.03:
        return GuidanceOutcome.SIGNIFICANTLY_BEAT
    elif actual >= high:
        return GuidanceOutcome.BEAT
    elif actual >= low:
        return GuidanceOutcome.MET
    elif actual >= low * 0.97:
        return GuidanceOutcome.MISSED
    else:
        return GuidanceOutcome.SIGNIFICANTLY_MISSED


def get_current_guidance(ticker: str, metric=GuidanceMetric.EPS) -> List[GuidanceRecord]:
    """Get current fiscal year guidance (forward estimates as proxy)."""
    metric_val = metric.value if hasattr(metric, "value") else metric

    if metric_val == "eps":
        estimates = _fetch_eps_estimates(ticker)
    else:
        estimates = _fetch_revenue_estimates(ticker)

    if not estimates:
        return []

    records = []
    for entry in estimates[:4]:
        year = entry.get("year", date.today().year)
        period = entry.get("period", "annual")

        if metric_val == "eps":
            low = entry.get("epsLow", 0) or 0
            high = entry.get("epsHigh", 0) or 0
            avg = entry.get("epsAvg", 0) or 0
        else:
            low = entry.get("revenueLow", 0) or 0
            high = entry.get("revenueHigh", 0) or 0
            avg = entry.get("revenueAvg", 0) or 0

        mid = avg if avg else (low + high) / 2

        fiscal_period = "FY"
        if "Q1" in str(period) or "q1" in str(period):
            fiscal_period = "Q1"
        elif "Q2" in str(period) or "q2" in str(period):
            fiscal_period = "Q2"
        elif "Q3" in str(period) or "q3" in str(period):
            fiscal_period = "Q3"
        elif "Q4" in str(period) or "q4" in str(period):
            fiscal_period = "Q4"

        records.append(GuidanceRecord(
            ticker=ticker.upper(),
            metric=metric_val,
            fiscal_year=year,
            fiscal_period=fiscal_period,
            guidance_low=round(low, 4),
            guidance_high=round(high, 4),
            guidance_mid=round(mid, 4),
            date_issued=str(date.today()),
        ))

    return records


def get_guidance_vs_actual(ticker: str, fiscal_year: int, fiscal_period: str, metric=GuidanceMetric.EPS) -> GuidanceVsActual:
    """Compare guidance vs actual results for a specific period."""
    metric_val = metric.value if hasattr(metric, "value") else metric
    earnings = _fetch_earnings(ticker)

    # Find estimate for this period
    if metric_val == "eps":
        estimates = _fetch_eps_estimates(ticker)
    else:
        estimates = _fetch_revenue_estimates(ticker)

    # Find actual from earnings
    actual = 0.0
    for e in earnings:
        if e.get("year") == fiscal_year:
            q = e.get("quarter", 0)
            if fiscal_period == "FY" or fiscal_period == f"Q{q}":
                actual = e.get("actual", 0) or 0
                break

    # Find guidance (estimate range)
    low = high = mid = 0.0
    for entry in estimates:
        if entry.get("year") == fiscal_year:
            if metric_val == "eps":
                low = entry.get("epsLow", 0) or 0
                high = entry.get("epsHigh", 0) or 0
                mid = entry.get("epsAvg", 0) or 0
            else:
                low = entry.get("revenueLow", 0) or 0
                high = entry.get("revenueHigh", 0) or 0
                mid = entry.get("revenueAvg", 0) or 0
            break

    if not mid:
        mid = (low + high) / 2

    variance_pct = round(((actual - mid) / abs(mid)) * 100, 2) if mid != 0 else 0
    outcome = _classify_outcome(actual, low, high)

    return GuidanceVsActual(
        ticker=ticker.upper(),
        metric=metric_val,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        guidance_low=round(low, 4),
        guidance_high=round(high, 4),
        guidance_mid=round(mid, 4),
        actual=round(actual, 4),
        variance_pct=variance_pct,
        outcome=outcome,
    )


def get_guidance_history(ticker: str, metric=GuidanceMetric.EPS, quarters: int = 12) -> List[GuidanceVsActual]:
    """Get historical guidance vs actual record."""
    metric_val = metric.value if hasattr(metric, "value") else metric
    earnings = _fetch_earnings(ticker)

    if metric_val == "eps":
        estimates = _fetch_eps_estimates(ticker)
    else:
        estimates = _fetch_revenue_estimates(ticker)

    history = []
    for e in earnings[:quarters]:
        year = e.get("year", 0)
        quarter = e.get("quarter", 0)
        actual = e.get("actual", 0) or 0
        estimate = e.get("estimate", 0) or 0

        # Use estimate as guidance proxy
        low = estimate * 0.97
        high = estimate * 1.03
        mid = estimate

        # Check if we have proper estimate range
        for est in estimates:
            if est.get("year") == year:
                if metric_val == "eps":
                    est_low = est.get("epsLow", 0) or 0
                    est_high = est.get("epsHigh", 0) or 0
                    if est_low and est_high:
                        low = est_low
                        high = est_high
                        mid = est.get("epsAvg", 0) or (low + high) / 2

        variance_pct = round(((actual - mid) / abs(mid)) * 100, 2) if mid != 0 else 0
        outcome = _classify_outcome(actual, low, high)

        history.append(GuidanceVsActual(
            ticker=ticker.upper(),
            metric=metric_val,
            fiscal_year=year,
            fiscal_period=f"Q{quarter}",
            guidance_low=round(low, 4),
            guidance_high=round(high, 4),
            guidance_mid=round(mid, 4),
            actual=round(actual, 4),
            variance_pct=variance_pct,
            outcome=outcome,
        ))

    return history


def get_guidance_revisions(ticker: str, fiscal_year: Optional[int] = None) -> List[GuidanceRevision]:
    """Get guidance revision history (from estimate changes over time)."""
    # Finnhub doesn't provide revision history directly, derive from recommendation changes
    eps_estimates = _fetch_eps_estimates(ticker)
    fy = fiscal_year or date.today().year

    revisions = []
    # If we have multiple estimate periods, we can infer revisions
    prev_entry = None
    for entry in reversed(eps_estimates):
        if prev_entry is not None:
            old_avg = prev_entry.get("epsAvg", 0) or 0
            new_avg = entry.get("epsAvg", 0) or 0
            old_high = prev_entry.get("epsHigh", 0) or 0
            new_high = entry.get("epsHigh", 0) or 0
            old_low = prev_entry.get("epsLow", 0) or 0
            new_low = entry.get("epsLow", 0) or 0

            if old_avg != new_avg and old_avg != 0:
                change_pct = round(((new_avg - old_avg) / abs(old_avg)) * 100, 2)
                if change_pct > 1:
                    direction = RevisionDirection.RAISED
                elif change_pct < -1:
                    direction = RevisionDirection.LOWERED
                else:
                    direction = RevisionDirection.MAINTAINED

                revisions.append(GuidanceRevision(
                    ticker=ticker.upper(),
                    date=str(date.today()),
                    fiscal_year=entry.get("year", fy),
                    metric="eps",
                    old_low=round(old_low, 4),
                    old_high=round(old_high, 4),
                    new_low=round(new_low, 4),
                    new_high=round(new_high, 4),
                    direction=direction,
                    change_pct=change_pct,
                ))
        prev_entry = entry

    return revisions


def calculate_management_credibility(ticker: str) -> ManagementCredibility:
    """Calculate management credibility score from earnings history."""
    earnings = _fetch_earnings(ticker)
    company_name = COMPANY_GUIDANCE_DATA.get(ticker.upper(), ticker.upper())

    if not earnings:
        return ManagementCredibility(
            ticker=ticker.upper(),
            company_name=company_name,
            credibility_score=50.0,
            credibility_tier=CredibilityTier.AVERAGE,
            beat_rate=0,
            meet_or_beat_rate=0,
            avg_variance_pct=0,
            revision_tendency="unknown",
            quarters_analyzed=0,
        )

    beats = 0
    meets = 0
    misses = 0
    variances = []

    for e in earnings[:12]:
        actual = e.get("actual", 0) or 0
        estimate = e.get("estimate", 0) or 0
        if estimate == 0:
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
        total = 1

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

    if score >= 80:
        tier = CredibilityTier.EXCELLENT
    elif score >= 65:
        tier = CredibilityTier.GOOD
    elif score >= 45:
        tier = CredibilityTier.AVERAGE
    else:
        tier = CredibilityTier.POOR

    # Flags
    green_flags = []
    red_flags = []
    if beat_rate > 70:
        green_flags.append("Consistently beats estimates")
    if beat_rate > 80:
        green_flags.append("Exceptional beat record")
    if avg_variance > 3:
        green_flags.append("Conservative guidance pattern")
    if beat_rate < 40:
        red_flags.append("Frequently misses estimates")
    if avg_variance < -5:
        red_flags.append("Guidance appears overly optimistic")

    # Revision tendency
    if avg_variance > 2:
        revision_tendency = "conservative"
    elif avg_variance < -2:
        revision_tendency = "aggressive"
    else:
        revision_tendency = "balanced"

    return ManagementCredibility(
        ticker=ticker.upper(),
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


def get_full_guidance_track(ticker: str) -> FullGuidanceTrack:
    """Get complete guidance dashboard for a ticker."""
    company_name = COMPANY_GUIDANCE_DATA.get(ticker.upper(), ticker.upper())
    current = get_current_guidance(ticker, GuidanceMetric.EPS)
    history = get_guidance_history(ticker, GuidanceMetric.EPS, 8)
    revisions = get_guidance_revisions(ticker)
    credibility = calculate_management_credibility(ticker)

    return FullGuidanceTrack(
        ticker=ticker.upper(),
        company_name=company_name,
        current_guidance=current,
        history=history,
        revisions=revisions,
        credibility=credibility,
    )


# ── Serializers ───────────────────────────────────────────────────────────────

def guidance_record_to_dict(rec) -> dict:
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
        "date_issued": rec.date_issued,
        "source": rec.source,
    }


def vs_actual_to_dict(va) -> dict:
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


def revision_to_dict(rev) -> dict:
    if isinstance(rev, dict):
        return rev
    return {
        "ticker": rev.ticker,
        "date": rev.date,
        "fiscal_year": rev.fiscal_year,
        "metric": rev.metric,
        "old_range": {"low": rev.old_low, "high": rev.old_high},
        "new_range": {"low": rev.new_low, "high": rev.new_high},
        "direction": rev.direction.value if hasattr(rev.direction, "value") else rev.direction,
        "change_pct": rev.change_pct,
    }


def credibility_to_dict(cred) -> dict:
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


def guidance_track_to_dict(track) -> dict:
    if isinstance(track, dict):
        return track
    return {
        "ticker": track.ticker,
        "company_name": track.company_name,
        "current_guidance": [guidance_record_to_dict(r) for r in track.current_guidance],
        "history": [vs_actual_to_dict(h) for h in track.history],
        "revisions": [revision_to_dict(r) for r in track.revisions],
        "credibility": credibility_to_dict(track.credibility),
    }
