"""
Model & Idea Leaderboards Service (Band B #30)
───────────────────────────────────────────────
Delegates to politician_leaderboard_service for real trading data.
Also provides prediction/idea submission (in-memory for now).
"""

import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field

from app.services.politician_leaderboard_service import (
    get_leaderboard_by_trades,
    get_leaderboard_by_volume,
    get_leaderboard_by_returns,
    get_statistics,
    search_politician,
    get_notable_cases,
    get_executive_branch,
    get_all_politicians,
    get_top_performers_summary,
)

logger = logging.getLogger(__name__)


# ── Data models for prediction tracking ──────────────────────────────────────

@dataclass
class Prediction:
    id: str
    user_id: str
    ticker: str
    prediction_type: str
    predicted_value: float
    confidence: float
    target_date: str
    created_at: str = ""
    resolved: bool = False
    actual_value: Optional[float] = None
    brier_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "prediction_type": self.prediction_type,
            "predicted_value": self.predicted_value,
            "confidence": self.confidence,
            "target_date": self.target_date,
            "created_at": self.created_at,
            "resolved": self.resolved,
            "actual_value": self.actual_value,
            "brier_score": self.brier_score,
        }


@dataclass
class Idea:
    id: str
    user_id: str
    ticker: str
    direction: str
    thesis: str
    entry_price: float
    target_price: float
    stop_price: float
    time_horizon_days: int
    created_at: str = ""
    pnl_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "direction": self.direction,
            "thesis": self.thesis,
            "entry_price": self.entry_price,
            "target_price": self.target_price,
            "stop_price": self.stop_price,
            "time_horizon_days": self.time_horizon_days,
            "created_at": self.created_at,
            "pnl_pct": self.pnl_pct,
        }


@dataclass
class UserScore:
    user_id: str
    accuracy: float = 0.0
    brier_score: float = 1.0
    calibration: float = 0.0
    tier: str = "novice"
    total_predictions: int = 0
    badges: List[str] = field(default_factory=list)
    streak: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "accuracy": self.accuracy,
            "brier_score": self.brier_score,
            "calibration": self.calibration,
            "tier": self.tier,
            "total_predictions": self.total_predictions,
            "badges": self.badges,
            "streak": self.streak,
        }


@dataclass
class Calibration:
    user_id: str
    buckets: List[Dict] = field(default_factory=list)
    overall_calibration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "buckets": self.buckets,
            "overall_calibration": self.overall_calibration,
        }


@dataclass
class LeaderboardEntry:
    user_id: str
    rank: int = 0
    name: str = ""
    score: float = 0.0
    predictions: int = 0
    tier: str = "novice"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "rank": self.rank,
            "name": self.name,
            "score": self.score,
            "predictions": self.predictions,
            "tier": self.tier,
        }


# ── Service class ────────────────────────────────────────────────────────────

class LeaderboardService:
    """
    Leaderboard service combining:
    - Politician trading rankings (real data from politician_leaderboard_service)
    - User prediction tracking (in-memory)
    """

    def __init__(self):
        self._predictions: Dict[str, Prediction] = {}
        self._ideas: Dict[str, Idea] = {}
        self._user_scores: Dict[str, UserScore] = {}

    def submit_prediction(self, user_id: str, ticker: str, prediction_type: str,
                          predicted_value: float, confidence: float,
                          target_date: str) -> Prediction:
        pred = Prediction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            ticker=ticker.upper(),
            prediction_type=prediction_type,
            predicted_value=predicted_value,
            confidence=confidence,
            target_date=target_date,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self._predictions[pred.id] = pred

        if user_id not in self._user_scores:
            self._user_scores[user_id] = UserScore(user_id=user_id)
        self._user_scores[user_id].total_predictions += 1

        return pred

    def resolve_prediction(self, prediction_id: str, actual_value: float) -> Optional[Prediction]:
        pred = self._predictions.get(prediction_id)
        if not pred:
            return None

        pred.resolved = True
        pred.actual_value = actual_value
        pred.brier_score = (pred.confidence - (1.0 if actual_value == pred.predicted_value else 0.0)) ** 2

        score = self._user_scores.get(pred.user_id)
        if score:
            resolved = [p for p in self._predictions.values()
                        if p.user_id == pred.user_id and p.resolved]
            if resolved:
                score.brier_score = sum(p.brier_score for p in resolved) / len(resolved)
                score.accuracy = sum(1 for p in resolved if p.actual_value == p.predicted_value) / len(resolved)
                score.tier = self._compute_tier(score.brier_score)

        return pred

    def get_user_score(self, user_id: str) -> Optional[UserScore]:
        return self._user_scores.get(user_id)

    def get_leaderboard(self, metric: str = "brier", limit: int = 20,
                        category: Optional[str] = None) -> List[LeaderboardEntry]:
        """
        Get leaderboard entries. Merges politician trading data with user predictions.
        """
        entries = []

        # Pull from politician leaderboard as "real" trading leaders
        try:
            if category == "returns" or metric == "accuracy":
                politicians = get_leaderboard_by_returns(limit=limit)
            elif category == "volume":
                politicians = get_leaderboard_by_volume(limit=limit)
            else:
                politicians = get_leaderboard_by_trades(limit=limit)

            for i, p in enumerate(politicians):
                entries.append(LeaderboardEntry(
                    user_id=p.get("name", "").replace(" ", "_").lower(),
                    rank=i + 1,
                    name=p.get("name", ""),
                    score=p.get("return_pct", 0) or p.get("trade_count", 0),
                    predictions=p.get("trade_count", 0),
                    tier="politician",
                ))
        except Exception as e:
            logger.warning("Failed to load politician leaderboard: %s", e)

        return entries[:limit]

    def submit_idea(self, user_id: str, ticker: str, direction: str, thesis: str,
                    entry_price: float, target_price: float, stop_price: float,
                    time_horizon_days: int) -> Idea:
        idea = Idea(
            id=str(uuid.uuid4()),
            user_id=user_id,
            ticker=ticker.upper(),
            direction=direction,
            thesis=thesis,
            entry_price=entry_price,
            target_price=target_price,
            stop_price=stop_price,
            time_horizon_days=time_horizon_days,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self._ideas[idea.id] = idea
        return idea

    def get_idea_leaderboard(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return submitted ideas sorted by P&L."""
        ideas = sorted(self._ideas.values(), key=lambda i: i.pnl_pct, reverse=True)
        return [i.to_dict() for i in ideas[:limit]]

    def get_user_calibration(self, user_id: str) -> Calibration:
        """Calibration analysis for a user."""
        resolved = [p for p in self._predictions.values()
                    if p.user_id == user_id and p.resolved]

        buckets = []
        for low in range(0, 100, 10):
            high = low + 10
            in_bucket = [p for p in resolved if low / 100 <= p.confidence < high / 100]
            if in_bucket:
                actual_rate = sum(1 for p in in_bucket if p.actual_value == p.predicted_value) / len(in_bucket)
                buckets.append({
                    "confidence_range": f"{low}-{high}%",
                    "predicted_rate": (low + high) / 200,
                    "actual_rate": actual_rate,
                    "count": len(in_bucket),
                })

        overall = 0.0
        if buckets:
            overall = 1.0 - (sum(abs(b["predicted_rate"] - b["actual_rate"]) for b in buckets) / len(buckets))

        return Calibration(user_id=user_id, buckets=buckets, overall_calibration=overall)

    @staticmethod
    def _compute_tier(brier_score: float) -> str:
        if brier_score <= 0.1:
            return "elite"
        elif brier_score <= 0.25:
            return "expert"
        elif brier_score <= 0.5:
            return "proficient"
        return "novice"


# ── Singleton ────────────────────────────────────────────────────────────────

_service_instance = None


def get_leaderboard_service() -> LeaderboardService:
    global _service_instance
    if _service_instance is None:
        _service_instance = LeaderboardService()
    return _service_instance
