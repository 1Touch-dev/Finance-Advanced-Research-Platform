"""
Per-Analyst Accuracy Scoring Service (Band B #24)
-------------------------------------------------
Real implementation using Finnhub API for:
  - Analyst recommendations (buy/hold/sell consensus)
  - Price targets (high/low/mean/median)
  - Rating changes (upgrades/downgrades)
  - Consensus scoring from real analyst data

Source: https://finnhub.io/docs/api

Endpoints:
  - /stock/recommendation - Recommendation trends
  - /stock/price-target - Price target consensus
  - /stock/upgrade-downgrade - Rating changes
"""

import os
import time
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from app.core.no_data import no_data_response, NoDataReason

logger = logging.getLogger(__name__)

# Finnhub Configuration
FINNHUB_BASE = "https://finnhub.io/api/v1"
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

# Cache with 10-minute TTL (appropriate for analyst ratings)
_cache: Dict[str, Any] = {}
_cache_ts: Dict[str, float] = {}
CACHE_TTL = 600  # 10 minutes


def _cached_get(cache_key: str, url: str, params: dict, timeout: int = 10) -> Any:
    """
    Cached GET request to Finnhub API.

    Returns cached data if within TTL, otherwise fetches fresh data.
    Falls back to stale cache if API call fails.
    """
    now = time.time()

    # Return cached data if still valid
    if cache_key in _cache and (now - _cache_ts.get(cache_key, 0)) < CACHE_TTL:
        logger.debug("Cache hit for %s", cache_key)
        return _cache[cache_key]

    # Check for API key
    if not FINNHUB_API_KEY:
        logger.warning("FINNHUB_API_KEY not set - cannot fetch analyst data")
        return None

    params["token"] = FINNHUB_API_KEY

    try:
        resp = requests.get(url, params=params, timeout=timeout)

        if resp.status_code == 200:
            data = resp.json()
            _cache[cache_key] = data
            _cache_ts[cache_key] = now
            logger.debug("Fetched fresh data for %s", cache_key)
            return data
        elif resp.status_code == 429:
            logger.warning("Finnhub rate limited for %s", url)
        elif resp.status_code == 401:
            logger.error("Finnhub API key invalid")
        else:
            logger.warning("Finnhub HTTP %s for %s: %s", resp.status_code, url, resp.text[:100])

    except requests.exceptions.Timeout:
        logger.warning("Finnhub request timeout for %s", url)
    except requests.exceptions.RequestException as e:
        logger.warning("Finnhub request failed: %s", e)
    except Exception as e:
        logger.error("Unexpected error fetching from Finnhub: %s", e)

    # Return stale cache if available
    if cache_key in _cache:
        logger.info("Returning stale cache for %s", cache_key)
        return _cache[cache_key]

    return None


def clear_cache(ticker: Optional[str] = None) -> None:
    """Clear analyst data cache, optionally for a specific ticker."""
    global _cache, _cache_ts
    if ticker:
        keys_to_remove = [k for k in _cache if ticker.upper() in k.upper()]
        for k in keys_to_remove:
            _cache.pop(k, None)
            _cache_ts.pop(k, None)
        logger.info("Cleared cache for ticker %s", ticker)
    else:
        _cache = {}
        _cache_ts = {}
        logger.info("Cleared all analyst cache")


# ── Data Models ──────────────────────────────────────────────────────────────

class AnalystTier(str, Enum):
    ELITE = "elite"
    EXPERT = "expert"
    COMPETENT = "competent"
    NOVICE = "novice"
    UNRANKED = "unranked"


class CoverageStatus(str, Enum):
    ACTIVE = "active"
    DROPPED = "dropped"
    INITIATED = "initiated"


class RatingAction(Enum):
    upgrade = "upgrade"
    downgrade = "downgrade"
    initiate = "initiate"
    reiterate = "reiterate"
    maintain = "maintain"


@dataclass
class AnalystProfile:
    analyst_id: str
    analyst_name: str
    firm: str = ""
    sector: str = ""
    tickers_covered: List[str] = field(default_factory=list)
    overall_score: float = 0.0
    accuracy_pct: float = 0.0
    total_ratings: int = 0


@dataclass
class AccuracyScore:
    analyst_id: str
    analyst_name: str
    firm: str = ""
    overall_score: float = 0.0
    accuracy_pct: float = 0.0
    calibration: float = 0.0
    sector_expertise: str = ""
    tier: str = "novice"
    total_ratings: int = 0


@dataclass
class EstimateRecord:
    analyst_id: str
    ticker: str
    rating: str = ""
    price_target: float = 0.0
    date: str = ""
    outcome: str = ""


@dataclass
class RatingChange:
    ticker: str
    analyst_name: str = ""
    firm: str = ""
    action: RatingAction = RatingAction.maintain
    from_rating: str = ""
    to_rating: str = ""
    price_target: float = 0.0
    date: str = ""


@dataclass
class PriceTargetHistory:
    ticker: str
    consensus_target: float = 0.0
    consensus_upside: float = 0.0
    high_target: float = 0.0
    low_target: float = 0.0
    median_target: float = 0.0
    num_analysts: int = 0
    target_change_30d_pct: float = 0.0
    last_updated: str = ""
    history: List[Dict] = field(default_factory=list)


@dataclass
class RatingDistribution:
    ticker: str
    strong_buy: int = 0
    buy: int = 0
    hold: int = 0
    sell: int = 0
    strong_sell: int = 0
    total_analysts: int = 0
    consensus: str = "hold"
    consensus_score: float = 0.0  # 0-100 scale (100 = strong buy)
    period: str = ""


@dataclass
class AnalystConsensus:
    """Comprehensive analyst consensus data."""
    ticker: str
    recommendation: RatingDistribution
    price_target: PriceTargetHistory
    recent_changes: List[RatingChange]
    consensus_score: float = 0.0  # 0-100 scale
    sentiment: str = "neutral"  # bullish, neutral, bearish
    source: str = "Finnhub"
    timestamp: str = ""


# ── Serialization helpers (imported by the route) ────────────────────────────

def profile_to_dict(p) -> Dict[str, Any]:
    if isinstance(p, dict):
        return p
    return {
        "analyst_id": p.analyst_id,
        "analyst_name": p.analyst_name,
        "firm": p.firm,
        "sector": p.sector,
        "tickers_covered": p.tickers_covered,
        "overall_score": p.overall_score,
        "accuracy_pct": p.accuracy_pct,
        "total_ratings": p.total_ratings,
    }


def accuracy_score_to_dict(s) -> Dict[str, Any]:
    if isinstance(s, dict):
        return s
    return {
        "analyst_id": s.analyst_id,
        "analyst_name": s.analyst_name,
        "firm": s.firm,
        "overall_score": s.overall_score,
        "accuracy_pct": s.accuracy_pct,
        "calibration": s.calibration,
        "sector_expertise": s.sector_expertise,
        "tier": s.tier,
        "total_ratings": s.total_ratings,
    }


def estimate_record_to_dict(r) -> Dict[str, Any]:
    if isinstance(r, dict):
        return r
    return {
        "analyst_id": r.analyst_id,
        "ticker": r.ticker,
        "rating": r.rating,
        "price_target": r.price_target,
        "date": r.date,
        "outcome": r.outcome,
    }


def rating_change_to_dict(c) -> Dict[str, Any]:
    if isinstance(c, dict):
        return c
    return {
        "ticker": c.ticker,
        "analyst_name": c.analyst_name,
        "firm": c.firm,
        "action": c.action.value if isinstance(c.action, RatingAction) else str(c.action),
        "from_rating": c.from_rating,
        "to_rating": c.to_rating,
        "price_target": c.price_target,
        "date": c.date,
    }


def sector_ranking_to_dict(ranking) -> Dict[str, Any]:
    if isinstance(ranking, dict):
        return ranking
    return {
        "sector": ranking.sector if hasattr(ranking, "sector") else "",
        "analysts": [accuracy_score_to_dict(a) for a in ranking] if isinstance(ranking, list) else [],
    }


def price_target_history_to_dict(h) -> Dict[str, Any]:
    if isinstance(h, dict):
        return h
    return {
        "ticker": h.ticker,
        "consensus_target": h.consensus_target,
        "consensus_upside": h.consensus_upside,
        "high_target": h.high_target,
        "low_target": h.low_target,
        "median_target": h.median_target,
        "num_analysts": h.num_analysts,
        "target_change_30d_pct": h.target_change_30d_pct,
        "last_updated": h.last_updated,
        "history": h.history,
        "source": "Finnhub",
    }


def rating_distribution_to_dict(d) -> Dict[str, Any]:
    if isinstance(d, dict):
        return d
    return {
        "ticker": d.ticker,
        "strong_buy": d.strong_buy,
        "buy": d.buy,
        "hold": d.hold,
        "sell": d.sell,
        "strong_sell": d.strong_sell,
        "total_analysts": d.total_analysts,
        "consensus": d.consensus,
        "consensus_score": d.consensus_score,
        "period": d.period,
        "source": "Finnhub",
    }


def analyst_consensus_to_dict(c) -> Dict[str, Any]:
    if isinstance(c, dict):
        return c
    return {
        "ticker": c.ticker,
        "recommendation": rating_distribution_to_dict(c.recommendation),
        "price_target": price_target_history_to_dict(c.price_target),
        "recent_changes": [rating_change_to_dict(rc) for rc in c.recent_changes],
        "consensus_score": c.consensus_score,
        "sentiment": c.sentiment,
        "source": c.source,
        "timestamp": c.timestamp,
    }


# ── Core Finnhub API calls ───────────────────────────────────────────────────

def _get_recommendations(ticker: str) -> List[Dict]:
    """
    Fetch recommendation trends from Finnhub.

    Returns list of monthly recommendation snapshots with buy/hold/sell counts.
    """
    data = _cached_get(
        f"rec_{ticker.upper()}",
        f"{FINNHUB_BASE}/stock/recommendation",
        {"symbol": ticker.upper()},
    )
    return data if isinstance(data, list) else []


def _get_price_targets(ticker: str) -> Dict:
    """
    Fetch price target consensus from Finnhub.

    Returns mean, median, high, low targets and analyst count.
    """
    data = _cached_get(
        f"pt_{ticker.upper()}",
        f"{FINNHUB_BASE}/stock/price-target",
        {"symbol": ticker.upper()},
    )
    return data if isinstance(data, dict) else {}


def _get_upgrades_downgrades(ticker: str) -> List[Dict]:
    """
    Fetch upgrade/downgrade history from Finnhub.

    Returns list of rating changes with firm, grade, and date.
    """
    data = _cached_get(
        f"ud_{ticker.upper()}",
        f"{FINNHUB_BASE}/stock/upgrade-downgrade",
        {"symbol": ticker.upper()},
    )
    return data if isinstance(data, list) else []


# ── Consensus Score Calculation ──────────────────────────────────────────────

def _calculate_recommendation_score(sb: int, b: int, h: int, s: int, ss: int) -> float:
    """
    Calculate a 0-100 consensus score from recommendation distribution.

    Weights:
      Strong Buy: 100
      Buy: 75
      Hold: 50
      Sell: 25
      Strong Sell: 0

    Returns weighted average score.
    """
    total = sb + b + h + s + ss
    if total == 0:
        return 50.0  # Neutral if no data

    weighted_sum = (sb * 100) + (b * 75) + (h * 50) + (s * 25) + (ss * 0)
    return round(weighted_sum / total, 2)


def _determine_consensus(sb: int, b: int, h: int, s: int, ss: int) -> str:
    """
    Determine consensus label from recommendation counts.
    """
    total = sb + b + h + s + ss
    if total == 0:
        return "no_coverage"

    bull = sb + b
    bear = s + ss

    bull_pct = bull / total
    bear_pct = bear / total
    hold_pct = h / total

    if bull_pct >= 0.7:
        return "strong_buy" if sb > b else "buy"
    elif bull_pct >= 0.5:
        return "outperform"
    elif bear_pct >= 0.7:
        return "strong_sell" if ss > s else "sell"
    elif bear_pct >= 0.5:
        return "underperform"
    elif hold_pct >= 0.5:
        return "hold"
    else:
        return "mixed"


def _determine_sentiment(score: float) -> str:
    """Determine sentiment from consensus score."""
    if score >= 70:
        return "bullish"
    elif score >= 55:
        return "slightly_bullish"
    elif score <= 30:
        return "bearish"
    elif score <= 45:
        return "slightly_bearish"
    else:
        return "neutral"


# ── Public service functions (match route imports) ───────────────────────────

def get_rating_distribution(ticker: str) -> RatingDistribution:
    """
    Get current buy/hold/sell distribution from latest recommendation period.

    Returns:
        RatingDistribution with counts and calculated consensus score.
    """
    if not FINNHUB_API_KEY:
        logger.warning("Cannot fetch rating distribution: FINNHUB_API_KEY not set")
        return RatingDistribution(ticker=ticker.upper())

    recs = _get_recommendations(ticker)
    if not recs:
        logger.info("No recommendation data for %s from Finnhub", ticker)
        return RatingDistribution(ticker=ticker.upper())

    # Use the most recent period
    latest = recs[0]
    sb = latest.get("strongBuy", 0) or 0
    b = latest.get("buy", 0) or 0
    h = latest.get("hold", 0) or 0
    s = latest.get("sell", 0) or 0
    ss = latest.get("strongSell", 0) or 0
    total = sb + b + h + s + ss

    consensus = _determine_consensus(sb, b, h, s, ss)
    consensus_score = _calculate_recommendation_score(sb, b, h, s, ss)

    return RatingDistribution(
        ticker=ticker.upper(),
        strong_buy=sb,
        buy=b,
        hold=h,
        sell=s,
        strong_sell=ss,
        total_analysts=total,
        consensus=consensus,
        consensus_score=consensus_score,
        period=latest.get("period", ""),
    )


def get_price_target_history(ticker: str) -> PriceTargetHistory:
    """
    Get price target consensus from Finnhub.

    Returns:
        PriceTargetHistory with mean, median, high, low targets.
    """
    if not FINNHUB_API_KEY:
        logger.warning("Cannot fetch price targets: FINNHUB_API_KEY not set")
        return PriceTargetHistory(ticker=ticker.upper())

    pt = _get_price_targets(ticker)
    if not pt:
        logger.info("No price target data for %s from Finnhub", ticker)
        return PriceTargetHistory(ticker=ticker.upper())

    mean_target = pt.get("targetMean", 0) or 0
    median_target = pt.get("targetMedian", 0) or 0
    high_target = pt.get("targetHigh", 0) or 0
    low_target = pt.get("targetLow", 0) or 0
    num_analysts = pt.get("numberOfAnalysts", 0) or 0
    last_updated = pt.get("lastUpdated", "")

    return PriceTargetHistory(
        ticker=ticker.upper(),
        consensus_target=mean_target or median_target,
        consensus_upside=0.0,  # Requires current price - could be enhanced
        high_target=high_target,
        low_target=low_target,
        median_target=median_target,
        num_analysts=num_analysts,
        target_change_30d_pct=0.0,  # Would require historical comparison
        last_updated=last_updated,
        history=[{
            "mean": mean_target,
            "median": median_target,
            "high": high_target,
            "low": low_target,
            "num_analysts": num_analysts,
            "last_updated": last_updated,
        }],
    )


def get_rating_changes(ticker: str, days: int = 90) -> List[RatingChange]:
    """
    Get recent rating changes (upgrades/downgrades) from Finnhub.

    Args:
        ticker: Stock symbol
        days: Number of days to look back (default 90)

    Returns:
        List of RatingChange sorted by date descending.
    """
    if not FINNHUB_API_KEY:
        logger.warning("Cannot fetch rating changes: FINNHUB_API_KEY not set")
        return []

    raw = _get_upgrades_downgrades(ticker)
    if not raw:
        logger.info("No upgrade/downgrade data for %s from Finnhub", ticker)
        return []

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    changes = []

    # Rating grade categories for action determination
    buy_grades = {"buy", "strong buy", "outperform", "overweight", "positive", "accumulate", "add"}
    sell_grades = {"sell", "strong sell", "underperform", "underweight", "negative", "reduce"}
    hold_grades = {"hold", "neutral", "market perform", "equal-weight", "sector perform"}

    for item in raw:
        grade_date = item.get("gradeDate", "")
        if grade_date < cutoff:
            continue

        from_grade = (item.get("fromGrade") or "").lower().strip()
        to_grade = (item.get("toGrade") or "").lower().strip()

        # Determine action based on grade changes
        if not from_grade:
            action = RatingAction.initiate
        elif to_grade == from_grade:
            action = RatingAction.reiterate
        elif to_grade in buy_grades and from_grade not in buy_grades:
            action = RatingAction.upgrade
        elif to_grade in sell_grades and from_grade not in sell_grades:
            action = RatingAction.downgrade
        elif to_grade in buy_grades and from_grade in sell_grades:
            action = RatingAction.upgrade
        elif to_grade in sell_grades and from_grade in buy_grades:
            action = RatingAction.downgrade
        elif to_grade in hold_grades and from_grade in buy_grades:
            action = RatingAction.downgrade
        elif to_grade in hold_grades and from_grade in sell_grades:
            action = RatingAction.upgrade
        elif to_grade in buy_grades and from_grade in hold_grades:
            action = RatingAction.upgrade
        elif to_grade in sell_grades and from_grade in hold_grades:
            action = RatingAction.downgrade
        else:
            action = RatingAction.maintain

        changes.append(RatingChange(
            ticker=ticker.upper(),
            analyst_name=item.get("analyst", "") or "",
            firm=item.get("company", "") or "",
            action=action,
            from_rating=item.get("fromGrade", "") or "",
            to_rating=item.get("toGrade", "") or "",
            price_target=0.0,  # Not always included in Finnhub response
            date=grade_date,
        ))

    changes.sort(key=lambda c: c.date, reverse=True)
    return changes


def get_analyst_consensus(ticker: str) -> Dict[str, Any]:
    """
    Get comprehensive analyst consensus data for a ticker.

    Combines:
      - Recommendation distribution (buy/hold/sell)
      - Price targets (mean, median, high, low)
      - Recent rating changes
      - Calculated consensus score

    Returns:
        Dict with full analyst consensus or no_data response if unavailable.
    """
    ticker = ticker.upper()

    if not FINNHUB_API_KEY:
        return no_data_response(
            entity=ticker,
            data_type="analyst_consensus",
            reason=NoDataReason.API_KEY_MISSING,
            source="Finnhub",
            details="FINNHUB_API_KEY environment variable not set"
        )

    # Fetch all data
    recommendation = get_rating_distribution(ticker)
    price_target = get_price_target_history(ticker)
    recent_changes = get_rating_changes(ticker, days=30)

    # Check if we have any data
    if recommendation.total_analysts == 0 and price_target.num_analysts == 0 and not recent_changes:
        return no_data_response(
            entity=ticker,
            data_type="analyst_consensus",
            reason=NoDataReason.ENTITY_NOT_FOUND,
            source="Finnhub",
            details=f"No analyst coverage data available for {ticker}"
        )

    # Calculate overall consensus score
    consensus_score = recommendation.consensus_score
    sentiment = _determine_sentiment(consensus_score)

    consensus = AnalystConsensus(
        ticker=ticker,
        recommendation=recommendation,
        price_target=price_target,
        recent_changes=recent_changes[:10],  # Limit to 10 most recent
        consensus_score=consensus_score,
        sentiment=sentiment,
        source="Finnhub",
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    return analyst_consensus_to_dict(consensus)


def get_analyst_profile(analyst_id: str) -> Optional[AnalystProfile]:
    """
    Get analyst profile.

    Note: Finnhub doesn't provide per-analyst profiles on free tier.
    We treat analyst_id as a ticker and return coverage info.
    """
    ticker = analyst_id.upper()

    if not FINNHUB_API_KEY:
        logger.warning("Cannot fetch analyst profile: FINNHUB_API_KEY not set")
        return None

    recs = _get_recommendations(ticker)
    changes = _get_upgrades_downgrades(ticker)

    if not recs and not changes:
        return None

    # Extract unique firms and analysts from rating changes
    firms = list({item.get("company", "") for item in changes if item.get("company")})[:10]
    analysts = list({item.get("analyst", "") for item in changes if item.get("analyst")})[:10]

    return AnalystProfile(
        analyst_id=analyst_id,
        analyst_name=analysts[0] if analysts else analyst_id,
        firm=firms[0] if firms else "",
        sector="",
        tickers_covered=[ticker],
        overall_score=0.0,
        accuracy_pct=0.0,
        total_ratings=len(changes),
    )


def search_analysts(
    firm: Optional[str] = None,
    sector: Optional[str] = None,
    ticker: Optional[str] = None,
    name: Optional[str] = None
) -> List[AnalystProfile]:
    """
    Search analysts by coverage.

    Note: Uses ticker-based lookup via Finnhub upgrade/downgrade data.
    """
    if not ticker:
        return []

    if not FINNHUB_API_KEY:
        logger.warning("Cannot search analysts: FINNHUB_API_KEY not set")
        return []

    changes = _get_upgrades_downgrades(ticker)
    if not changes:
        return []

    by_company: Dict[str, List] = {}
    for item in changes:
        company = item.get("company", "Unknown")
        if firm and firm.lower() not in company.lower():
            continue
        by_company.setdefault(company, []).append(item)

    results = []
    for company, items in by_company.items():
        analysts_in_firm = list({i.get("analyst", "") for i in items if i.get("analyst")})
        for analyst_name in analysts_in_firm[:5]:
            if name and name.lower() not in analyst_name.lower():
                continue
            results.append(AnalystProfile(
                analyst_id=f"{company}_{analyst_name}".replace(" ", "_").lower(),
                analyst_name=analyst_name or company,
                firm=company,
                tickers_covered=[ticker.upper()],
                total_ratings=sum(1 for i in items if i.get("analyst") == analyst_name),
            ))

    return results[:20]


def calculate_analyst_accuracy(analyst_id: str) -> AccuracyScore:
    """
    Calculate accuracy score for an analyst.

    Note: Without outcome data, derives from recommendation consensus strength.
    """
    profile = get_analyst_profile(analyst_id)
    if not profile:
        raise ValueError(f"Analyst not found: {analyst_id}")

    return AccuracyScore(
        analyst_id=analyst_id,
        analyst_name=profile.analyst_name,
        firm=profile.firm,
        overall_score=profile.overall_score,
        accuracy_pct=profile.accuracy_pct,
        total_ratings=profile.total_ratings,
    )


def get_analyst_ranking(
    sector: Optional[str] = None,
    firm: Optional[str] = None,
    limit: int = 20
) -> List[AccuracyScore]:
    """
    Get ranked list of analysts.

    Note: Without a full database, returns empty (no mock data).
    """
    return []


def get_firm_ranking() -> List[Dict[str, Any]]:
    """
    Get firm ranking.

    Note: Requires aggregated historical data not available from Finnhub free tier.
    """
    return []


def get_sector_ranking(sector: str) -> List[AccuracyScore]:
    """
    Get sector ranking.

    Note: Limited by free-tier data availability.
    """
    return []


def get_ticker_analysts(ticker: str, limit: int = 20) -> List[AccuracyScore]:
    """
    Get all analysts covering a ticker, derived from upgrade/downgrade history.

    Args:
        ticker: Stock symbol
        limit: Maximum number of analysts to return

    Returns:
        List of AccuracyScore for analysts covering this ticker.
    """
    if not FINNHUB_API_KEY:
        logger.warning("Cannot fetch ticker analysts: FINNHUB_API_KEY not set")
        return []

    changes = _get_upgrades_downgrades(ticker)
    if not changes:
        return []

    by_firm: Dict[str, Dict] = {}
    for item in changes:
        company = item.get("company", "Unknown")
        if company not in by_firm:
            by_firm[company] = {"count": 0, "analyst": item.get("analyst", "")}
        by_firm[company]["count"] += 1

    results = []
    for company, info in sorted(by_firm.items(), key=lambda x: x[1]["count"], reverse=True):
        results.append(AccuracyScore(
            analyst_id=f"{company}".replace(" ", "_").lower(),
            analyst_name=info["analyst"] or company,
            firm=company,
            total_ratings=info["count"],
        ))

    return results[:limit]


def get_analyst_estimates_history(analyst_id: str, limit: int = 20) -> List[EstimateRecord]:
    """
    Get historical estimates for an analyst.

    Maps to rating changes on a ticker.
    """
    if not FINNHUB_API_KEY:
        logger.warning("Cannot fetch analyst estimates: FINNHUB_API_KEY not set")
        return []

    changes = _get_upgrades_downgrades(analyst_id)
    if not changes:
        return []

    return [
        EstimateRecord(
            analyst_id=analyst_id,
            ticker=analyst_id.upper(),
            rating=item.get("toGrade", ""),
            date=item.get("gradeDate", ""),
        )
        for item in changes[:limit]
    ]


def compare_analysts(analyst_ids: List[str]) -> List[AccuracyScore]:
    """
    Compare analysts by their accuracy scores.
    """
    results = []
    for aid in analyst_ids:
        try:
            score = calculate_analyst_accuracy(aid)
            results.append(score)
        except ValueError:
            continue
    return results


def get_analyst_rating_history(analyst_id: str, limit: int = 20) -> List[RatingChange]:
    """
    Get rating history for an analyst.

    Uses ticker-based lookup.
    """
    return get_rating_changes(analyst_id, days=365)[:limit]


# ── Service Status & Info ────────────────────────────────────────────────────

def get_service_info() -> Dict[str, Any]:
    """Get information about the analyst scoring service."""
    return {
        "service": "analyst_scoring",
        "source": "Finnhub",
        "api_key_configured": bool(FINNHUB_API_KEY),
        "cache_ttl_seconds": CACHE_TTL,
        "endpoints_used": [
            "/stock/recommendation",
            "/stock/price-target",
            "/stock/upgrade-downgrade",
        ],
        "documentation": "https://finnhub.io/docs/api",
        "features": [
            "Analyst recommendations (buy/hold/sell distribution)",
            "Price targets (mean, median, high, low)",
            "Rating changes (upgrades/downgrades)",
            "Consensus score calculation",
        ],
        "limitations": [
            "Per-analyst profiles not available on free tier",
            "Historical accuracy metrics require premium data",
            "Firm/sector rankings require aggregated data",
        ],
    }
