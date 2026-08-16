"""
Per-Analyst Accuracy Scoring Service (Band B #24)
────────────────────────────────────────────────────────────────────────────
Provides:
  - Individual analyst accuracy scoring
  - Calibration metrics (Brier score, reliability)
  - Sector/industry expertise identification
  - Historical track record analysis
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, date, timedelta
import statistics
import math


# ── Enums ──────────────────────────────────────────────────────────────────────

class AnalystTier(Enum):
    """Analyst ranking tier."""
    STAR = "star"  # Top 10%
    TOP = "top"  # Top 25%
    ABOVE_AVERAGE = "above_average"  # 25-50%
    AVERAGE = "average"  # 50-75%
    BELOW_AVERAGE = "below_average"  # Bottom 25%


class RatingAction(Enum):
    """Analyst rating action."""
    INITIATE = "initiate"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    REITERATE = "reiterate"
    SUSPEND = "suspend"


class CoverageStatus(Enum):
    """Analyst coverage status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DROPPED = "dropped"


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class AnalystEstimateRecord:
    """Single analyst estimate with outcome."""
    analyst_id: str
    ticker: str
    metric: str  # eps, revenue, etc.
    fiscal_year: int
    fiscal_period: str
    estimate_date: date
    estimate_value: float
    actual_value: Optional[float] = None
    error: Optional[float] = None
    error_pct: Optional[float] = None
    direction_correct: Optional[bool] = None


@dataclass
class AnalystProfile:
    """Analyst profile with career information."""
    analyst_id: str
    name: str
    firm: str
    title: str = "Senior Analyst"
    years_experience: int = 5

    # Coverage
    sectors_covered: List[str] = field(default_factory=list)
    tickers_covered: List[str] = field(default_factory=list)
    coverage_status: CoverageStatus = CoverageStatus.ACTIVE

    # Contact (simulated)
    email: Optional[str] = None

    # Career history
    previous_firms: List[str] = field(default_factory=list)


@dataclass
class AnalystAccuracyScore:
    """Comprehensive analyst accuracy scoring."""
    analyst_id: str
    analyst_name: str
    firm: str
    as_of_date: date

    # Overall score (0-100)
    overall_score: float
    tier: AnalystTier
    percentile_rank: int  # 1-100

    # Accuracy metrics
    mean_absolute_error: float  # Average % error
    mean_signed_error: float  # Bias indicator
    direction_accuracy: float  # % correct direction
    hit_rate: float  # % within 5% of actual

    # Calibration metrics
    brier_score: float  # Lower is better
    calibration_score: float  # How well-calibrated

    # Coverage stats
    estimates_count: int
    tickers_covered: int
    sectors_covered: List[str]

    # Timeliness
    avg_days_before_report: float  # How early estimates are made
    revision_frequency: float  # Avg revisions per estimate

    # Expertise
    best_sectors: List[str] = field(default_factory=list)
    best_tickers: List[str] = field(default_factory=list)
    worst_tickers: List[str] = field(default_factory=list)


@dataclass
class AnalystRatingRecord:
    """Analyst rating action record."""
    analyst_id: str
    ticker: str
    action: RatingAction
    rating: str  # buy, hold, sell
    target_price: float
    rating_date: date

    # Outcome
    price_at_rating: Optional[float] = None
    price_3m_later: Optional[float] = None
    price_6m_later: Optional[float] = None
    price_12m_later: Optional[float] = None
    target_achieved: Optional[bool] = None


@dataclass
class AnalystRatingAccuracy:
    """Analyst rating/target accuracy."""
    analyst_id: str
    analyst_name: str
    firm: str

    # Target price accuracy
    avg_target_error: float
    target_hit_rate: float  # % where price reached target

    # Rating profitability
    buy_avg_return: float  # Avg return on buy ratings
    sell_avg_return: float  # Avg return on sell ratings
    rating_edge: float  # Buy return - sell return

    # Timeliness
    avg_days_to_target: float

    # Consistency
    upgrade_success_rate: float
    downgrade_success_rate: float

    total_ratings: int


@dataclass
class FirmAnalystRanking:
    """Ranking of analysts within a firm."""
    firm: str
    ranking_date: date
    analysts: List[AnalystAccuracyScore]

    # Firm aggregates
    firm_avg_score: float
    firm_rank_overall: int  # Rank among all firms
    top_analyst: str


@dataclass
class SectorAnalystRanking:
    """Ranking of analysts covering a sector."""
    sector: str
    ranking_date: date
    analysts: List[AnalystAccuracyScore]

    # Sector stats
    avg_sector_score: float
    best_analyst: str
    coverage_count: int


# ── Simulated Analyst Database ─────────────────────────────────────────────────

ANALYST_PROFILES: Dict[str, AnalystProfile] = {
    "analyst_001": AnalystProfile(
        analyst_id="analyst_001",
        name="John Smith",
        firm="Goldman Sachs",
        title="Managing Director",
        years_experience=15,
        sectors_covered=["Technology", "Semiconductors"],
        tickers_covered=["NVDA", "AMD", "INTC", "AVGO"],
    ),
    "analyst_002": AnalystProfile(
        analyst_id="analyst_002",
        name="Sarah Johnson",
        firm="Morgan Stanley",
        title="Executive Director",
        years_experience=12,
        sectors_covered=["Technology", "Software"],
        tickers_covered=["MSFT", "ORCL", "CRM", "ADBE"],
    ),
    "analyst_003": AnalystProfile(
        analyst_id="analyst_003",
        name="Michael Chen",
        firm="JPMorgan",
        title="Managing Director",
        years_experience=18,
        sectors_covered=["Technology", "Internet"],
        tickers_covered=["AAPL", "GOOGL", "META", "AMZN"],
    ),
    "analyst_004": AnalystProfile(
        analyst_id="analyst_004",
        name="Emily Davis",
        firm="Bank of America",
        title="Director",
        years_experience=8,
        sectors_covered=["Semiconductors"],
        tickers_covered=["NVDA", "AMD", "TSM", "ASML"],
    ),
    "analyst_005": AnalystProfile(
        analyst_id="analyst_005",
        name="Robert Wilson",
        firm="Citi",
        title="Managing Director",
        years_experience=20,
        sectors_covered=["Financials", "Banks"],
        tickers_covered=["JPM", "GS", "MS", "BAC"],
    ),
    "analyst_006": AnalystProfile(
        analyst_id="analyst_006",
        name="Jennifer Lee",
        firm="UBS",
        title="Executive Director",
        years_experience=10,
        sectors_covered=["Healthcare", "Pharma"],
        tickers_covered=["JNJ", "PFE", "MRK", "ABBV"],
    ),
    "analyst_007": AnalystProfile(
        analyst_id="analyst_007",
        name="David Brown",
        firm="Barclays",
        title="Director",
        years_experience=6,
        sectors_covered=["Consumer", "Retail"],
        tickers_covered=["AMZN", "WMT", "TGT", "COST"],
    ),
    "analyst_008": AnalystProfile(
        analyst_id="analyst_008",
        name="Lisa Anderson",
        firm="Deutsche Bank",
        title="Vice President",
        years_experience=4,
        sectors_covered=["Energy"],
        tickers_covered=["XOM", "CVX", "COP", "SLB"],
    ),
    "analyst_009": AnalystProfile(
        analyst_id="analyst_009",
        name="James Taylor",
        firm="Wells Fargo",
        title="Senior Analyst",
        years_experience=7,
        sectors_covered=["Industrials"],
        tickers_covered=["BA", "CAT", "DE", "UPS"],
    ),
    "analyst_010": AnalystProfile(
        analyst_id="analyst_010",
        name="Amanda White",
        firm="RBC Capital",
        title="Managing Director",
        years_experience=14,
        sectors_covered=["Technology", "Software"],
        tickers_covered=["MSFT", "GOOGL", "AAPL", "META"],
    ),
}

# Simulated accuracy data
ANALYST_ACCURACY_DATA: Dict[str, Dict[str, float]] = {
    "analyst_001": {"mae": 3.2, "direction": 0.82, "hit_rate": 0.68, "brier": 0.15},
    "analyst_002": {"mae": 4.1, "direction": 0.78, "hit_rate": 0.62, "brier": 0.18},
    "analyst_003": {"mae": 2.8, "direction": 0.85, "hit_rate": 0.72, "brier": 0.12},
    "analyst_004": {"mae": 5.5, "direction": 0.72, "hit_rate": 0.55, "brier": 0.22},
    "analyst_005": {"mae": 3.5, "direction": 0.80, "hit_rate": 0.65, "brier": 0.16},
    "analyst_006": {"mae": 4.8, "direction": 0.75, "hit_rate": 0.58, "brier": 0.20},
    "analyst_007": {"mae": 6.2, "direction": 0.68, "hit_rate": 0.48, "brier": 0.25},
    "analyst_008": {"mae": 7.5, "direction": 0.62, "hit_rate": 0.42, "brier": 0.30},
    "analyst_009": {"mae": 5.0, "direction": 0.73, "hit_rate": 0.56, "brier": 0.21},
    "analyst_010": {"mae": 3.0, "direction": 0.83, "hit_rate": 0.70, "brier": 0.14},
}


# ── Service Functions ──────────────────────────────────────────────────────────

def get_analyst_profile(analyst_id: str) -> Optional[AnalystProfile]:
    """Get analyst profile by ID."""
    return ANALYST_PROFILES.get(analyst_id)


def search_analysts(
    firm: Optional[str] = None,
    sector: Optional[str] = None,
    ticker: Optional[str] = None,
    name: Optional[str] = None,
) -> List[AnalystProfile]:
    """Search analysts by various criteria."""
    results = list(ANALYST_PROFILES.values())

    if firm:
        firm_lower = firm.lower()
        results = [a for a in results if firm_lower in a.firm.lower()]

    if sector:
        sector_lower = sector.lower()
        results = [a for a in results if any(sector_lower in s.lower() for s in a.sectors_covered)]

    if ticker:
        ticker_upper = ticker.upper()
        results = [a for a in results if ticker_upper in a.tickers_covered]

    if name:
        name_lower = name.lower()
        results = [a for a in results if name_lower in a.name.lower()]

    return results


def calculate_analyst_accuracy(analyst_id: str) -> AnalystAccuracyScore:
    """Calculate comprehensive accuracy score for an analyst."""
    profile = ANALYST_PROFILES.get(analyst_id)
    if not profile:
        raise ValueError(f"Analyst not found: {analyst_id}")

    data = ANALYST_ACCURACY_DATA.get(analyst_id, {"mae": 5.0, "direction": 0.70, "hit_rate": 0.50, "brier": 0.20})

    mae = data["mae"]
    direction = data["direction"]
    hit_rate = data["hit_rate"]
    brier = data["brier"]

    # Calculate overall score (0-100)
    # Lower MAE is better, higher direction/hit_rate is better, lower brier is better
    mae_score = max(0, 100 - mae * 10)  # 10% error = 0 score
    direction_score = direction * 100
    hit_score = hit_rate * 100
    brier_score = max(0, 100 - brier * 200)

    overall = (mae_score * 0.30 + direction_score * 0.25 + hit_score * 0.25 + brier_score * 0.20)

    # Determine tier
    if overall >= 85:
        tier = AnalystTier.STAR
        percentile = 95
    elif overall >= 75:
        tier = AnalystTier.TOP
        percentile = 85
    elif overall >= 65:
        tier = AnalystTier.ABOVE_AVERAGE
        percentile = 65
    elif overall >= 50:
        tier = AnalystTier.AVERAGE
        percentile = 45
    else:
        tier = AnalystTier.BELOW_AVERAGE
        percentile = 25

    # Calibration score
    calibration = 100 - abs(50 - direction * 100)  # How close to perfect calibration

    return AnalystAccuracyScore(
        analyst_id=analyst_id,
        analyst_name=profile.name,
        firm=profile.firm,
        as_of_date=date.today(),
        overall_score=round(overall, 1),
        tier=tier,
        percentile_rank=percentile,
        mean_absolute_error=mae,
        mean_signed_error=round((mae * 0.3) - 1.0, 2),  # Simulated bias
        direction_accuracy=round(direction * 100, 1),
        hit_rate=round(hit_rate * 100, 1),
        brier_score=brier,
        calibration_score=round(calibration, 1),
        estimates_count=48 + profile.years_experience * 4,
        tickers_covered=len(profile.tickers_covered),
        sectors_covered=profile.sectors_covered,
        avg_days_before_report=45,
        revision_frequency=2.3,
        best_sectors=profile.sectors_covered[:1],
        best_tickers=profile.tickers_covered[:2],
        worst_tickers=[],
    )


def get_analyst_ranking(
    sector: Optional[str] = None,
    firm: Optional[str] = None,
    limit: int = 20,
) -> List[AnalystAccuracyScore]:
    """Get ranked list of analysts."""
    # Filter analysts
    analysts = search_analysts(firm=firm, sector=sector)

    # Calculate scores
    scores = []
    for analyst in analysts:
        try:
            score = calculate_analyst_accuracy(analyst.analyst_id)
            scores.append(score)
        except Exception:
            continue

    # Sort by overall score
    scores.sort(key=lambda x: x.overall_score, reverse=True)

    return scores[:limit]


def get_firm_ranking() -> List[Dict[str, Any]]:
    """Get ranking of firms by average analyst quality."""
    firms: Dict[str, List[float]] = {}

    for analyst_id in ANALYST_PROFILES:
        try:
            score = calculate_analyst_accuracy(analyst_id)
            firm = score.firm
            if firm not in firms:
                firms[firm] = []
            firms[firm].append(score.overall_score)
        except Exception:
            continue

    # Calculate averages
    firm_scores = [
        {
            "firm": firm,
            "avg_score": round(statistics.mean(scores), 1),
            "analyst_count": len(scores),
            "top_score": max(scores),
        }
        for firm, scores in firms.items()
    ]

    firm_scores.sort(key=lambda x: x["avg_score"], reverse=True)

    # Add ranks
    for i, f in enumerate(firm_scores):
        f["rank"] = i + 1

    return firm_scores


def get_sector_ranking(sector: str) -> SectorAnalystRanking:
    """Get ranking of analysts covering a sector."""
    analysts = search_analysts(sector=sector)
    scores = []

    for analyst in analysts:
        try:
            score = calculate_analyst_accuracy(analyst.analyst_id)
            scores.append(score)
        except Exception:
            continue

    scores.sort(key=lambda x: x.overall_score, reverse=True)

    avg_score = statistics.mean([s.overall_score for s in scores]) if scores else 0

    return SectorAnalystRanking(
        sector=sector,
        ranking_date=date.today(),
        analysts=scores,
        avg_sector_score=round(avg_score, 1),
        best_analyst=scores[0].analyst_name if scores else "",
        coverage_count=len(scores),
    )


def get_ticker_analysts(ticker: str) -> List[AnalystAccuracyScore]:
    """Get all analysts covering a ticker with their scores."""
    analysts = search_analysts(ticker=ticker)
    scores = []

    for analyst in analysts:
        try:
            score = calculate_analyst_accuracy(analyst.analyst_id)
            scores.append(score)
        except Exception:
            continue

    scores.sort(key=lambda x: x.overall_score, reverse=True)
    return scores


def get_analyst_estimates_history(
    analyst_id: str,
    limit: int = 20,
) -> List[AnalystEstimateRecord]:
    """Get analyst's historical estimates with outcomes."""
    profile = ANALYST_PROFILES.get(analyst_id)
    if not profile:
        raise ValueError(f"Analyst not found: {analyst_id}")

    import random

    records = []
    accuracy = ANALYST_ACCURACY_DATA.get(analyst_id, {"mae": 5.0, "direction": 0.70})

    for i in range(limit):
        ticker = random.choice(profile.tickers_covered) if profile.tickers_covered else "AAPL"
        estimate_val = 5.0 + random.uniform(-1, 2)
        error_pct = random.gauss(0, accuracy["mae"])
        actual_val = estimate_val * (1 + error_pct / 100)
        direction_correct = random.random() < accuracy["direction"]

        records.append(AnalystEstimateRecord(
            analyst_id=analyst_id,
            ticker=ticker,
            metric="eps",
            fiscal_year=2024 - (i // 4),
            fiscal_period=f"Q{(i % 4) + 1}",
            estimate_date=date.today() - timedelta(days=i * 30),
            estimate_value=round(estimate_val, 2),
            actual_value=round(actual_val, 2),
            error=round(actual_val - estimate_val, 2),
            error_pct=round(error_pct, 2),
            direction_correct=direction_correct,
        ))

    return records


def compare_analysts(analyst_ids: List[str]) -> List[AnalystAccuracyScore]:
    """Compare multiple analysts side by side."""
    scores = []
    for analyst_id in analyst_ids:
        try:
            score = calculate_analyst_accuracy(analyst_id)
            scores.append(score)
        except Exception:
            continue

    scores.sort(key=lambda x: x.overall_score, reverse=True)
    return scores


# ── Rating Changes & Price Target History (#36) ───────────────────────────────

@dataclass
class RatingChange:
    """Single rating change event."""
    ticker: str
    analyst_id: str
    analyst_name: str
    firm: str
    change_date: date
    action: RatingAction
    old_rating: Optional[str]
    new_rating: str
    old_target: Optional[float]
    new_target: float
    price_at_change: float
    target_upside: float  # % upside to target


@dataclass
class PriceTargetHistory:
    """Price target history for a ticker."""
    ticker: str
    company_name: str
    current_price: float
    as_of_date: date

    # Current consensus
    consensus_target: float
    consensus_upside: float
    num_analysts: int
    high_target: float
    low_target: float

    # Recent changes
    recent_changes: List[RatingChange]

    # Target evolution
    target_30d_ago: float
    target_90d_ago: float
    target_change_30d_pct: float
    target_change_90d_pct: float


@dataclass
class RatingDistribution:
    """Rating distribution for a ticker."""
    ticker: str
    buy_count: int
    hold_count: int
    sell_count: int
    total_analysts: int
    buy_pct: float
    hold_pct: float
    sell_pct: float
    consensus_rating: str  # strong buy, buy, hold, sell, strong sell


def get_rating_changes(
    ticker: str,
    days: int = 90,
) -> List[RatingChange]:
    """
    Get recent analyst rating changes for a ticker.

    Returns upgrades, downgrades, and initiations.
    """
    import random
    ticker = ticker.upper()

    # Simulated current price
    prices = {
        "NVDA": 875.0, "AAPL": 178.0, "MSFT": 415.0, "GOOGL": 175.0,
        "META": 495.0, "AMZN": 178.0, "TSLA": 245.0, "AMD": 165.0,
    }
    current_price = prices.get(ticker, 100.0)

    changes = []
    today = date.today()

    # Generate simulated rating changes
    for i in range(random.randint(3, 8)):
        analyst_id = f"analyst_{(i % 10) + 1:03d}"
        profile = ANALYST_PROFILES.get(analyst_id)
        if not profile:
            continue

        # Random action
        actions = [RatingAction.UPGRADE, RatingAction.DOWNGRADE, RatingAction.INITIATE, RatingAction.REITERATE]
        action = random.choice(actions)

        # Ratings
        ratings = ["buy", "overweight", "hold", "underweight", "sell"]
        if action == RatingAction.UPGRADE:
            old_idx = random.randint(2, 4)
            new_idx = random.randint(0, old_idx - 1)
            old_rating = ratings[old_idx]
            new_rating = ratings[new_idx]
        elif action == RatingAction.DOWNGRADE:
            old_idx = random.randint(0, 2)
            new_idx = random.randint(old_idx + 1, 4)
            old_rating = ratings[old_idx]
            new_rating = ratings[new_idx]
        elif action == RatingAction.INITIATE:
            old_rating = None
            new_rating = random.choice(["buy", "overweight", "hold"])
        else:
            old_rating = random.choice(ratings)
            new_rating = old_rating

        # Price targets
        old_target = current_price * (1 + random.uniform(-0.1, 0.3)) if old_rating else None
        new_target = current_price * (1 + random.uniform(0.05, 0.4))
        target_upside = ((new_target - current_price) / current_price) * 100

        changes.append(RatingChange(
            ticker=ticker,
            analyst_id=analyst_id,
            analyst_name=profile.name,
            firm=profile.firm,
            change_date=today - timedelta(days=random.randint(1, days)),
            action=action,
            old_rating=old_rating,
            new_rating=new_rating,
            old_target=round(old_target, 2) if old_target else None,
            new_target=round(new_target, 2),
            price_at_change=round(current_price * (1 + random.uniform(-0.05, 0.05)), 2),
            target_upside=round(target_upside, 2),
        ))

    # Sort by date (most recent first)
    changes.sort(key=lambda x: x.change_date, reverse=True)
    return changes


def get_price_target_history(ticker: str) -> PriceTargetHistory:
    """
    Get price target history and consensus for a ticker.

    Includes current consensus, target evolution, and recent changes.
    """
    ticker = ticker.upper()

    # Simulated data
    prices = {
        "NVDA": 875.0, "AAPL": 178.0, "MSFT": 415.0, "GOOGL": 175.0,
        "META": 495.0, "AMZN": 178.0, "TSLA": 245.0, "AMD": 165.0,
    }
    company_names = {
        "NVDA": "NVIDIA Corporation", "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation", "GOOGL": "Alphabet Inc.",
        "META": "Meta Platforms Inc.", "AMZN": "Amazon.com Inc.",
        "TSLA": "Tesla Inc.", "AMD": "Advanced Micro Devices",
    }

    import random

    current_price = prices.get(ticker, 100.0)
    company_name = company_names.get(ticker, ticker)

    # Generate target range
    consensus_target = current_price * (1 + random.uniform(0.1, 0.25))
    high_target = consensus_target * 1.3
    low_target = consensus_target * 0.7
    num_analysts = random.randint(20, 40)

    # Historical targets (targets were lower in the past)
    target_30d_ago = consensus_target * (1 - random.uniform(-0.05, 0.15))
    target_90d_ago = consensus_target * (1 - random.uniform(0.05, 0.25))

    target_change_30d_pct = ((consensus_target - target_30d_ago) / target_30d_ago) * 100
    target_change_90d_pct = ((consensus_target - target_90d_ago) / target_90d_ago) * 100

    # Get recent rating changes
    recent_changes = get_rating_changes(ticker, days=30)

    return PriceTargetHistory(
        ticker=ticker,
        company_name=company_name,
        current_price=current_price,
        as_of_date=date.today(),
        consensus_target=round(consensus_target, 2),
        consensus_upside=round(((consensus_target - current_price) / current_price) * 100, 2),
        num_analysts=num_analysts,
        high_target=round(high_target, 2),
        low_target=round(low_target, 2),
        recent_changes=recent_changes,
        target_30d_ago=round(target_30d_ago, 2),
        target_90d_ago=round(target_90d_ago, 2),
        target_change_30d_pct=round(target_change_30d_pct, 2),
        target_change_90d_pct=round(target_change_90d_pct, 2),
    )


def get_rating_distribution(ticker: str) -> RatingDistribution:
    """
    Get current rating distribution for a ticker.

    Shows breakdown of buy/hold/sell ratings.
    """
    import random
    ticker = ticker.upper()

    # Simulate realistic distribution (skewed toward buy for most stocks)
    total = random.randint(20, 40)
    buy_pct = random.uniform(0.4, 0.7)
    sell_pct = random.uniform(0.05, 0.15)
    hold_pct = 1 - buy_pct - sell_pct

    buy_count = int(total * buy_pct)
    sell_count = int(total * sell_pct)
    hold_count = total - buy_count - sell_count

    # Determine consensus
    if buy_pct > 0.6:
        consensus = "strong buy"
    elif buy_pct > 0.45:
        consensus = "buy"
    elif sell_pct > 0.3:
        consensus = "sell"
    else:
        consensus = "hold"

    return RatingDistribution(
        ticker=ticker,
        buy_count=buy_count,
        hold_count=hold_count,
        sell_count=sell_count,
        total_analysts=total,
        buy_pct=round(buy_pct * 100, 1),
        hold_pct=round(hold_pct * 100, 1),
        sell_pct=round(sell_pct * 100, 1),
        consensus_rating=consensus,
    )


def get_analyst_rating_history(
    analyst_id: str,
    limit: int = 20,
) -> List[RatingChange]:
    """
    Get an analyst's rating history across all covered tickers.
    """
    profile = ANALYST_PROFILES.get(analyst_id)
    if not profile:
        raise ValueError(f"Analyst not found: {analyst_id}")

    import random

    changes = []
    today = date.today()

    for i, ticker in enumerate(profile.tickers_covered[:limit]):
        # Generate rating change for each covered ticker
        prices = {
            "NVDA": 875.0, "AAPL": 178.0, "MSFT": 415.0, "GOOGL": 175.0,
            "META": 495.0, "AMZN": 178.0, "TSLA": 245.0, "AMD": 165.0,
        }
        current_price = prices.get(ticker, 100.0)

        action = random.choice([RatingAction.UPGRADE, RatingAction.REITERATE, RatingAction.INITIATE])
        ratings = ["buy", "overweight", "hold"]
        new_rating = random.choice(ratings)
        old_rating = random.choice(ratings) if action != RatingAction.INITIATE else None

        new_target = current_price * (1 + random.uniform(0.1, 0.35))

        changes.append(RatingChange(
            ticker=ticker,
            analyst_id=analyst_id,
            analyst_name=profile.name,
            firm=profile.firm,
            change_date=today - timedelta(days=random.randint(1, 180)),
            action=action,
            old_rating=old_rating,
            new_rating=new_rating,
            old_target=None,
            new_target=round(new_target, 2),
            price_at_change=round(current_price, 2),
            target_upside=round(((new_target - current_price) / current_price) * 100, 2),
        ))

    changes.sort(key=lambda x: x.change_date, reverse=True)
    return changes


# ── Serialization ──────────────────────────────────────────────────────────────

def profile_to_dict(profile: AnalystProfile) -> Dict[str, Any]:
    """Convert analyst profile to dictionary."""
    return {
        "analyst_id": profile.analyst_id,
        "name": profile.name,
        "firm": profile.firm,
        "title": profile.title,
        "years_experience": profile.years_experience,
        "sectors_covered": profile.sectors_covered,
        "tickers_covered": profile.tickers_covered,
        "coverage_status": profile.coverage_status.value,
    }


def accuracy_score_to_dict(score: AnalystAccuracyScore) -> Dict[str, Any]:
    """Convert accuracy score to dictionary."""
    return {
        "analyst_id": score.analyst_id,
        "analyst_name": score.analyst_name,
        "firm": score.firm,
        "as_of_date": score.as_of_date.isoformat(),
        "overall_score": score.overall_score,
        "tier": score.tier.value,
        "percentile_rank": score.percentile_rank,
        "accuracy_metrics": {
            "mean_absolute_error": score.mean_absolute_error,
            "mean_signed_error": score.mean_signed_error,
            "direction_accuracy": score.direction_accuracy,
            "hit_rate": score.hit_rate,
        },
        "calibration": {
            "brier_score": score.brier_score,
            "calibration_score": score.calibration_score,
        },
        "coverage": {
            "estimates_count": score.estimates_count,
            "tickers_covered": score.tickers_covered,
            "sectors_covered": score.sectors_covered,
        },
        "expertise": {
            "best_sectors": score.best_sectors,
            "best_tickers": score.best_tickers,
            "worst_tickers": score.worst_tickers,
        },
    }


def estimate_record_to_dict(record: AnalystEstimateRecord) -> Dict[str, Any]:
    """Convert estimate record to dictionary."""
    return {
        "analyst_id": record.analyst_id,
        "ticker": record.ticker,
        "metric": record.metric,
        "fiscal_year": record.fiscal_year,
        "fiscal_period": record.fiscal_period,
        "estimate_date": record.estimate_date.isoformat(),
        "estimate_value": record.estimate_value,
        "actual_value": record.actual_value,
        "error": record.error,
        "error_pct": record.error_pct,
        "direction_correct": record.direction_correct,
    }


def sector_ranking_to_dict(ranking: SectorAnalystRanking) -> Dict[str, Any]:
    """Convert sector ranking to dictionary."""
    return {
        "sector": ranking.sector,
        "ranking_date": ranking.ranking_date.isoformat(),
        "avg_sector_score": ranking.avg_sector_score,
        "best_analyst": ranking.best_analyst,
        "coverage_count": ranking.coverage_count,
        "analysts": [accuracy_score_to_dict(a) for a in ranking.analysts],
    }


def rating_change_to_dict(change: RatingChange) -> Dict[str, Any]:
    """Convert rating change to dictionary."""
    return {
        "ticker": change.ticker,
        "analyst_id": change.analyst_id,
        "analyst_name": change.analyst_name,
        "firm": change.firm,
        "change_date": change.change_date.isoformat(),
        "action": change.action.value,
        "old_rating": change.old_rating,
        "new_rating": change.new_rating,
        "old_target": change.old_target,
        "new_target": change.new_target,
        "price_at_change": change.price_at_change,
        "target_upside": change.target_upside,
    }


def price_target_history_to_dict(history: PriceTargetHistory) -> Dict[str, Any]:
    """Convert price target history to dictionary."""
    return {
        "ticker": history.ticker,
        "company_name": history.company_name,
        "current_price": history.current_price,
        "as_of_date": history.as_of_date.isoformat(),
        "consensus": {
            "target": history.consensus_target,
            "upside_pct": history.consensus_upside,
            "high_target": history.high_target,
            "low_target": history.low_target,
            "num_analysts": history.num_analysts,
        },
        "target_evolution": {
            "target_30d_ago": history.target_30d_ago,
            "target_90d_ago": history.target_90d_ago,
            "change_30d_pct": history.target_change_30d_pct,
            "change_90d_pct": history.target_change_90d_pct,
        },
        "recent_changes": [rating_change_to_dict(c) for c in history.recent_changes],
    }


def rating_distribution_to_dict(dist: RatingDistribution) -> Dict[str, Any]:
    """Convert rating distribution to dictionary."""
    return {
        "ticker": dist.ticker,
        "total_analysts": dist.total_analysts,
        "consensus_rating": dist.consensus_rating,
        "distribution": {
            "buy": {"count": dist.buy_count, "pct": dist.buy_pct},
            "hold": {"count": dist.hold_count, "pct": dist.hold_pct},
            "sell": {"count": dist.sell_count, "pct": dist.sell_pct},
        },
    }
