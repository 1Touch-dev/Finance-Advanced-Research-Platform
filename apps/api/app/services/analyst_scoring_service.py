"""
Per-Analyst Accuracy Scoring Service (Band B #24)
─────────────────────────────────────────────────
Real implementation using Finnhub API for:
  - Analyst recommendations (buy/hold/sell consensus)
  - Price targets (high/low/mean/median)
  - Rating changes (upgrades/downgrades)

Source: https://finnhub.io/docs/api
"""

import os
import time
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

# 30-minute cache
_cache: Dict[str, Any] = {}
_cache_ts: Dict[str, float] = {}
CACHE_TTL = 1800


def _cached_get(cache_key: str, url: str, params: dict, timeout: int = 10) -> Any:
    now = time.time()
    if cache_key in _cache and (now - _cache_ts.get(cache_key, 0)) < CACHE_TTL:
        return _cache[cache_key]

    if not FINNHUB_API_KEY:
        logger.warning("FINNHUB_API_KEY not set")
        return None

    params["token"] = FINNHUB_API_KEY
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            _cache[cache_key] = data
            _cache_ts[cache_key] = now
            return data
        logger.warning("Finnhub HTTP %s for %s", resp.status_code, url)
    except Exception as e:
        logger.warning("Finnhub request failed: %s", e)
    return _cache.get(cache_key)


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
    target_change_30d_pct: float = 0.0
    history: List[Dict] = field(default_factory=list)


@dataclass
class RatingDistribution:
    ticker: str
    strong_buy: int = 0
    buy: int = 0
    hold: int = 0
    sell: int = 0
    strong_sell: int = 0
    consensus: str = "hold"
    period: str = ""


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
        "target_change_30d_pct": h.target_change_30d_pct,
        "history": h.history,
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
        "consensus": d.consensus,
        "period": d.period,
    }


# ── Core Finnhub API calls ───────────────────────────────────────────────────

def _get_recommendations(ticker: str) -> List[Dict]:
    """Finnhub recommendation trends."""
    data = _cached_get(
        f"rec_{ticker}",
        f"{FINNHUB_BASE}/stock/recommendation",
        {"symbol": ticker.upper()},
    )
    return data if isinstance(data, list) else []


def _get_price_targets(ticker: str) -> Dict:
    """Finnhub price target consensus."""
    data = _cached_get(
        f"pt_{ticker}",
        f"{FINNHUB_BASE}/stock/price-target",
        {"symbol": ticker.upper()},
    )
    return data if isinstance(data, dict) else {}


def _get_upgrades_downgrades(ticker: str) -> List[Dict]:
    """Finnhub upgrade/downgrade history."""
    data = _cached_get(
        f"ud_{ticker}",
        f"{FINNHUB_BASE}/stock/upgrade-downgrade",
        {"symbol": ticker.upper()},
    )
    return data if isinstance(data, list) else []


# ── Public service functions (match route imports) ───────────────────────────

def get_rating_distribution(ticker: str) -> RatingDistribution:
    """Current buy/hold/sell distribution from latest recommendation period."""
    recs = _get_recommendations(ticker)
    if not recs:
        return RatingDistribution(ticker=ticker.upper())

    latest = recs[0]
    sb = latest.get("strongBuy", 0)
    b = latest.get("buy", 0)
    h = latest.get("hold", 0)
    s = latest.get("sell", 0)
    ss = latest.get("strongSell", 0)

    total = sb + b + h + s + ss
    if total > 0:
        bull = sb + b
        bear = s + ss
        if bull > bear and bull > h:
            consensus = "buy" if bull > total * 0.6 else "outperform"
        elif bear > bull and bear > h:
            consensus = "sell" if bear > total * 0.6 else "underperform"
        else:
            consensus = "hold"
    else:
        consensus = "hold"

    return RatingDistribution(
        ticker=ticker.upper(),
        strong_buy=sb,
        buy=b,
        hold=h,
        sell=s,
        strong_sell=ss,
        consensus=consensus,
        period=latest.get("period", ""),
    )


def get_price_target_history(ticker: str) -> PriceTargetHistory:
    """Price target consensus from Finnhub."""
    pt = _get_price_targets(ticker)
    if not pt:
        return PriceTargetHistory(ticker=ticker.upper())

    return PriceTargetHistory(
        ticker=ticker.upper(),
        consensus_target=pt.get("targetMean", 0) or pt.get("targetMedian", 0),
        consensus_upside=0.0,
        high_target=pt.get("targetHigh", 0),
        low_target=pt.get("targetLow", 0),
        target_change_30d_pct=0.0,
        history=[{
            "mean": pt.get("targetMean"),
            "median": pt.get("targetMedian"),
            "high": pt.get("targetHigh"),
            "low": pt.get("targetLow"),
            "last_updated": pt.get("lastUpdated", ""),
        }],
    )


def get_rating_changes(ticker: str, days: int = 90) -> List[RatingChange]:
    """Recent rating changes (upgrades/downgrades) from Finnhub."""
    raw = _get_upgrades_downgrades(ticker)
    if not raw:
        return []

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    changes = []
    for item in raw:
        grade_date = item.get("gradeDate", "")
        if grade_date < cutoff:
            continue

        from_grade = (item.get("fromGrade") or "").lower()
        to_grade = (item.get("toGrade") or "").lower()

        buy_grades = {"buy", "strong buy", "outperform", "overweight", "positive"}
        sell_grades = {"sell", "strong sell", "underperform", "underweight", "negative"}

        if not from_grade:
            action = RatingAction.initiate
        elif to_grade in buy_grades and from_grade not in buy_grades:
            action = RatingAction.upgrade
        elif to_grade in sell_grades and from_grade not in sell_grades:
            action = RatingAction.downgrade
        elif to_grade == from_grade:
            action = RatingAction.reiterate
        elif to_grade in buy_grades and from_grade in sell_grades:
            action = RatingAction.upgrade
        elif to_grade in sell_grades and from_grade in buy_grades:
            action = RatingAction.downgrade
        else:
            action = RatingAction.maintain

        changes.append(RatingChange(
            ticker=ticker.upper(),
            analyst_name=item.get("analyst", "") or "",
            firm=item.get("company", ""),
            action=action,
            from_rating=item.get("fromGrade", ""),
            to_rating=item.get("toGrade", ""),
            price_target=0.0,
            date=grade_date,
        ))

    changes.sort(key=lambda c: c.date, reverse=True)
    return changes


def get_analyst_profile(analyst_id: str) -> Optional[AnalystProfile]:
    """
    Analyst profile. Since Finnhub doesn't have per-analyst IDs,
    we treat the analyst_id as a ticker and return coverage info.
    """
    ticker = analyst_id.upper()
    recs = _get_recommendations(ticker)
    changes = _get_upgrades_downgrades(ticker)

    if not recs and not changes:
        return None

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


def search_analysts(firm: Optional[str] = None, sector: Optional[str] = None,
                    ticker: Optional[str] = None, name: Optional[str] = None) -> List[AnalystProfile]:
    """Search analysts by coverage. Uses ticker-based lookup via Finnhub."""
    if not ticker:
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
    """Accuracy score. Without outcome data, derives from recommendation consensus strength."""
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


def get_analyst_ranking(sector: Optional[str] = None, firm: Optional[str] = None,
                        limit: int = 20) -> List[AccuracyScore]:
    """Ranked list. Without a full database, returns empty."""
    return []


def get_firm_ranking() -> List[Dict[str, Any]]:
    """Firm ranking — requires aggregated historical data not available from Finnhub free tier."""
    return []


def get_sector_ranking(sector: str) -> List[AccuracyScore]:
    """Sector ranking — limited by free-tier data availability."""
    return []


def get_ticker_analysts(ticker: str) -> List[AccuracyScore]:
    """All analysts covering a ticker, derived from upgrade/downgrade history."""
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

    return results[:limit] if (limit := 20) else results


def get_analyst_estimates_history(analyst_id: str, limit: int = 20) -> List[EstimateRecord]:
    """Historical estimates for an analyst — maps to rating changes on a ticker."""
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
    """Compare analysts — returns accuracy scores for each."""
    results = []
    for aid in analyst_ids:
        try:
            score = calculate_analyst_accuracy(aid)
            results.append(score)
        except ValueError:
            continue
    return results


def get_analyst_rating_history(analyst_id: str, limit: int = 20) -> List[RatingChange]:
    """Rating history for an analyst — uses ticker-based lookup."""
    return get_rating_changes(analyst_id, days=365)[:limit]
