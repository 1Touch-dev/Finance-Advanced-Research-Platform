"""
Model & Idea Leaderboards Service (Band B #30)

Features:
- Brier scoring for predictions
- Model accuracy leaderboards
- Idea tracking and performance
- User ranking system
- Historical calibration
"""

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random
import hashlib


# ── Data Models ──────────────────────────────────────────────────────────────

@dataclass
class Prediction:
    """A scored prediction."""
    id: str
    user_id: str
    ticker: str
    prediction_type: str  # 'earnings_beat', 'price_target', 'direction'
    prediction_date: str
    target_date: str
    predicted_value: float
    confidence: float  # 0-1 probability
    actual_value: Optional[float] = None
    outcome: Optional[str] = None  # 'correct', 'incorrect', 'pending'
    brier_score: Optional[float] = None
    resolved_date: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class UserScore:
    """Aggregated score for a user."""
    user_id: str
    display_name: str
    total_predictions: int
    resolved_predictions: int
    correct_predictions: int
    accuracy_rate: float
    avg_brier_score: float
    calibration_score: float
    tier: str  # 'elite', 'expert', 'proficient', 'novice'
    rank: int
    badges: List[str]
    streak_current: int
    streak_best: int

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LeaderboardEntry:
    """Entry in a leaderboard."""
    rank: int
    user_id: str
    display_name: str
    score: float
    metric_name: str
    total_predictions: int
    accuracy_rate: float
    tier: str
    trend: str  # 'up', 'down', 'stable'
    trend_change: int

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class IdeaSubmission:
    """A trading idea submission."""
    id: str
    user_id: str
    ticker: str
    direction: str  # 'long', 'short'
    thesis: str
    entry_price: float
    target_price: float
    stop_price: float
    time_horizon_days: int
    submitted_date: str
    status: str  # 'active', 'hit_target', 'stopped_out', 'expired'
    current_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    score: Optional[float] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CalibrationData:
    """Calibration analysis for a user."""
    user_id: str
    display_name: str
    calibration_buckets: List[Dict[str, Any]]  # [{confidence_range, predicted_rate, actual_rate, count}]
    overall_calibration: float  # 0-1, 1 is perfect
    overconfidence_bias: float  # Positive = overconfident
    underconfidence_bias: float
    calibration_chart: List[Dict[str, float]]  # For plotting

    def to_dict(self) -> Dict:
        return asdict(self)


# ── Service Implementation ───────────────────────────────────────────────────

class LeaderboardService:
    """Model and idea leaderboard service with Brier scoring."""

    TIERS = {
        (0.90, 1.00): 'elite',
        (0.75, 0.90): 'expert',
        (0.50, 0.75): 'proficient',
        (0.00, 0.50): 'novice',
    }

    BADGES = [
        ('streak_5', 'Hot Streak', 'correct_streak', 5),
        ('streak_10', 'On Fire', 'correct_streak', 10),
        ('accuracy_80', 'Sharp Shooter', 'accuracy_rate', 0.8),
        ('predictions_100', 'Century', 'total_predictions', 100),
        ('calibrated', 'Well Calibrated', 'calibration_score', 0.85),
        ('contrarian', 'Contrarian', 'contrarian_rate', 0.3),
    ]

    def __init__(self):
        self._predictions: Dict[str, Prediction] = {}
        self._ideas: Dict[str, IdeaSubmission] = {}
        self._user_scores: Dict[str, Dict] = {}
        self._init_mock_data()

    def _init_mock_data(self):
        """Initialize mock predictions and users."""
        users = [
            ('user_001', 'QuantMaster'),
            ('user_002', 'ValueHunter'),
            ('user_003', 'TechTrader'),
            ('user_004', 'MacroMaven'),
            ('user_005', 'AlphaSeeker'),
            ('user_006', 'RiskManager'),
            ('user_007', 'CatalystPro'),
            ('user_008', 'EarningsEdge'),
            ('user_009', 'SectorRotator'),
            ('user_010', 'DeepValue'),
        ]

        tickers = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'META', 'AMD', 'AMZN', 'GOOGL']
        prediction_types = ['earnings_beat', 'price_target', 'direction']

        for user_id, display_name in users:
            # Initialize user score tracking
            self._user_scores[user_id] = {
                'display_name': display_name,
                'predictions': [],
                'correct': 0,
                'total': 0,
                'brier_sum': 0,
                'streak': 0,
                'best_streak': 0,
            }

            # Generate mock predictions
            num_predictions = random.randint(20, 100)
            for i in range(num_predictions):
                pred_id = f"{user_id}_pred_{i}"
                days_ago = random.randint(1, 365)
                pred_date = datetime.now() - timedelta(days=days_ago)
                target_date = pred_date + timedelta(days=random.randint(1, 90))

                confidence = random.uniform(0.3, 0.95)

                # Simulate outcome based on confidence and skill
                skill = random.uniform(0.4, 0.7)  # User skill factor
                is_correct = random.random() < (confidence * skill + (1 - confidence) * (1 - skill))

                actual = 1 if is_correct else 0
                brier = (confidence - actual) ** 2

                pred = Prediction(
                    id=pred_id,
                    user_id=user_id,
                    ticker=random.choice(tickers),
                    prediction_type=random.choice(prediction_types),
                    prediction_date=pred_date.strftime('%Y-%m-%d'),
                    target_date=target_date.strftime('%Y-%m-%d'),
                    predicted_value=1,
                    confidence=round(confidence, 3),
                    actual_value=actual,
                    outcome='correct' if is_correct else 'incorrect',
                    brier_score=round(brier, 4),
                    resolved_date=target_date.strftime('%Y-%m-%d'),
                )

                self._predictions[pred_id] = pred
                self._user_scores[user_id]['predictions'].append(pred_id)
                self._user_scores[user_id]['total'] += 1
                self._user_scores[user_id]['brier_sum'] += brier
                if is_correct:
                    self._user_scores[user_id]['correct'] += 1

    def _calculate_brier_score(self, confidence: float, actual: int) -> float:
        """Calculate Brier score (0 = perfect, 1 = worst)."""
        return (confidence - actual) ** 2

    def _get_tier(self, score: float) -> str:
        """Get tier based on normalized score."""
        for (low, high), tier in self.TIERS.items():
            if low <= score < high:
                return tier
        return 'novice'

    def _calculate_calibration(self, user_id: str) -> CalibrationData:
        """Calculate calibration metrics for a user."""
        user_preds = [
            self._predictions[pid]
            for pid in self._user_scores.get(user_id, {}).get('predictions', [])
            if pid in self._predictions and self._predictions[pid].outcome
        ]

        if not user_preds:
            return CalibrationData(
                user_id=user_id,
                display_name=self._user_scores.get(user_id, {}).get('display_name', 'Unknown'),
                calibration_buckets=[],
                overall_calibration=0.5,
                overconfidence_bias=0,
                underconfidence_bias=0,
                calibration_chart=[],
            )

        # Group by confidence bucket
        buckets = [(0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
        bucket_data = []

        for low, high in buckets:
            in_bucket = [p for p in user_preds if low <= p.confidence < high]
            if in_bucket:
                predicted_rate = sum(p.confidence for p in in_bucket) / len(in_bucket)
                actual_rate = sum(1 for p in in_bucket if p.outcome == 'correct') / len(in_bucket)
                bucket_data.append({
                    'confidence_range': f"{int(low*100)}-{int(high*100)}%",
                    'predicted_rate': round(predicted_rate, 3),
                    'actual_rate': round(actual_rate, 3),
                    'count': len(in_bucket),
                    'deviation': round(predicted_rate - actual_rate, 3),
                })

        # Overall calibration (1 - mean absolute deviation)
        if bucket_data:
            mad = sum(abs(b['deviation']) for b in bucket_data) / len(bucket_data)
            overall_cal = max(0, 1 - mad * 2)
        else:
            overall_cal = 0.5

        # Bias calculation
        over_conf = sum(b['deviation'] for b in bucket_data if b['deviation'] > 0)
        under_conf = sum(abs(b['deviation']) for b in bucket_data if b['deviation'] < 0)

        return CalibrationData(
            user_id=user_id,
            display_name=self._user_scores.get(user_id, {}).get('display_name', 'Unknown'),
            calibration_buckets=bucket_data,
            overall_calibration=round(overall_cal, 3),
            overconfidence_bias=round(over_conf, 3),
            underconfidence_bias=round(under_conf, 3),
            calibration_chart=[
                {'predicted': b['predicted_rate'], 'actual': b['actual_rate']}
                for b in bucket_data
            ],
        )

    def submit_prediction(
        self,
        user_id: str,
        ticker: str,
        prediction_type: str,
        predicted_value: float,
        confidence: float,
        target_date: str
    ) -> Prediction:
        """Submit a new prediction."""
        pred_id = hashlib.md5(f"{user_id}_{ticker}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        pred = Prediction(
            id=pred_id,
            user_id=user_id,
            ticker=ticker.upper(),
            prediction_type=prediction_type,
            prediction_date=datetime.now().strftime('%Y-%m-%d'),
            target_date=target_date,
            predicted_value=predicted_value,
            confidence=min(0.99, max(0.01, confidence)),
            actual_value=None,
            outcome='pending',
            brier_score=None,
            resolved_date=None,
        )

        self._predictions[pred_id] = pred

        if user_id not in self._user_scores:
            self._user_scores[user_id] = {
                'display_name': f'User_{user_id[:6]}',
                'predictions': [],
                'correct': 0,
                'total': 0,
                'brier_sum': 0,
                'streak': 0,
                'best_streak': 0,
            }
        self._user_scores[user_id]['predictions'].append(pred_id)

        return pred

    def resolve_prediction(
        self,
        prediction_id: str,
        actual_value: float
    ) -> Optional[Prediction]:
        """Resolve a prediction with actual outcome."""
        if prediction_id not in self._predictions:
            return None

        pred = self._predictions[prediction_id]
        if pred.outcome != 'pending':
            return pred  # Already resolved

        pred.actual_value = actual_value
        actual_binary = 1 if actual_value >= pred.predicted_value else 0
        pred.brier_score = self._calculate_brier_score(pred.confidence, actual_binary)
        pred.outcome = 'correct' if actual_binary == round(pred.confidence) else 'incorrect'
        pred.resolved_date = datetime.now().strftime('%Y-%m-%d')

        # Update user stats
        user = self._user_scores.get(pred.user_id)
        if user:
            user['total'] += 1
            user['brier_sum'] += pred.brier_score
            if pred.outcome == 'correct':
                user['correct'] += 1
                user['streak'] += 1
                user['best_streak'] = max(user['best_streak'], user['streak'])
            else:
                user['streak'] = 0

        return pred

    def get_user_score(self, user_id: str) -> Optional[UserScore]:
        """Get aggregated score for a user."""
        if user_id not in self._user_scores:
            return None

        user = self._user_scores[user_id]
        total = user['total']
        correct = user['correct']

        if total == 0:
            return UserScore(
                user_id=user_id,
                display_name=user['display_name'],
                total_predictions=0,
                resolved_predictions=0,
                correct_predictions=0,
                accuracy_rate=0,
                avg_brier_score=0.25,
                calibration_score=0.5,
                tier='novice',
                rank=0,
                badges=[],
                streak_current=0,
                streak_best=0,
            )

        accuracy = correct / total if total > 0 else 0
        avg_brier = user['brier_sum'] / total if total > 0 else 0.25
        calibration = self._calculate_calibration(user_id)

        # Score combines accuracy, Brier, and calibration
        combined_score = (accuracy * 0.4 + (1 - avg_brier) * 0.4 + calibration.overall_calibration * 0.2)
        tier = self._get_tier(combined_score)

        # Calculate badges
        badges = []
        if user['streak'] >= 5:
            badges.append('Hot Streak')
        if user['best_streak'] >= 10:
            badges.append('On Fire')
        if accuracy >= 0.8:
            badges.append('Sharp Shooter')
        if total >= 100:
            badges.append('Century')
        if calibration.overall_calibration >= 0.85:
            badges.append('Well Calibrated')

        return UserScore(
            user_id=user_id,
            display_name=user['display_name'],
            total_predictions=total,
            resolved_predictions=total,
            correct_predictions=correct,
            accuracy_rate=round(accuracy, 3),
            avg_brier_score=round(avg_brier, 4),
            calibration_score=round(calibration.overall_calibration, 3),
            tier=tier,
            rank=0,  # Will be set by leaderboard
            badges=badges,
            streak_current=user['streak'],
            streak_best=user['best_streak'],
        )

    def get_leaderboard(
        self,
        metric: str = 'brier',
        limit: int = 20,
        category: Optional[str] = None
    ) -> List[LeaderboardEntry]:
        """Get leaderboard by specified metric."""
        entries = []

        for user_id in self._user_scores:
            score = self.get_user_score(user_id)
            if not score or score.total_predictions < 10:  # Minimum threshold
                continue

            if metric == 'brier':
                metric_value = 1 - score.avg_brier_score  # Invert so higher is better
                metric_name = 'Brier Score'
            elif metric == 'accuracy':
                metric_value = score.accuracy_rate
                metric_name = 'Accuracy'
            elif metric == 'calibration':
                metric_value = score.calibration_score
                metric_name = 'Calibration'
            else:
                metric_value = score.accuracy_rate
                metric_name = 'Accuracy'

            entries.append({
                'user_id': user_id,
                'display_name': score.display_name,
                'score': round(metric_value, 4),
                'metric_name': metric_name,
                'total_predictions': score.total_predictions,
                'accuracy_rate': score.accuracy_rate,
                'tier': score.tier,
            })

        # Sort by score descending
        entries.sort(key=lambda x: x['score'], reverse=True)

        # Add rank and trend
        leaderboard = []
        for i, entry in enumerate(entries[:limit]):
            trend = random.choice(['up', 'down', 'stable'])
            trend_change = random.randint(-3, 3) if trend != 'stable' else 0

            leaderboard.append(LeaderboardEntry(
                rank=i + 1,
                user_id=entry['user_id'],
                display_name=entry['display_name'],
                score=entry['score'],
                metric_name=entry['metric_name'],
                total_predictions=entry['total_predictions'],
                accuracy_rate=entry['accuracy_rate'],
                tier=entry['tier'],
                trend=trend,
                trend_change=trend_change,
            ))

        return leaderboard

    def submit_idea(
        self,
        user_id: str,
        ticker: str,
        direction: str,
        thesis: str,
        entry_price: float,
        target_price: float,
        stop_price: float,
        time_horizon_days: int
    ) -> IdeaSubmission:
        """Submit a trading idea."""
        idea_id = hashlib.md5(f"{user_id}_{ticker}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]

        idea = IdeaSubmission(
            id=idea_id,
            user_id=user_id,
            ticker=ticker.upper(),
            direction=direction.lower(),
            thesis=thesis,
            entry_price=entry_price,
            target_price=target_price,
            stop_price=stop_price,
            time_horizon_days=time_horizon_days,
            submitted_date=datetime.now().strftime('%Y-%m-%d'),
            status='active',
            current_price=entry_price,
            pnl_pct=0,
            score=None,
        )

        self._ideas[idea_id] = idea
        return idea

    def get_idea_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Get ideas ranked by performance."""
        scored_ideas = []

        for idea in self._ideas.values():
            # Mock current price movement
            pnl_mult = 1 if idea.direction == 'long' else -1
            price_change = random.uniform(-0.15, 0.25)
            current_price = idea.entry_price * (1 + price_change)
            pnl_pct = (current_price - idea.entry_price) / idea.entry_price * 100 * pnl_mult

            # Check if hit target or stopped out
            if idea.direction == 'long':
                if current_price >= idea.target_price:
                    status = 'hit_target'
                elif current_price <= idea.stop_price:
                    status = 'stopped_out'
                else:
                    status = 'active'
            else:
                if current_price <= idea.target_price:
                    status = 'hit_target'
                elif current_price >= idea.stop_price:
                    status = 'stopped_out'
                else:
                    status = 'active'

            scored_ideas.append({
                'id': idea.id,
                'user_id': idea.user_id,
                'ticker': idea.ticker,
                'direction': idea.direction,
                'thesis': idea.thesis[:100] + '...' if len(idea.thesis) > 100 else idea.thesis,
                'entry_price': idea.entry_price,
                'target_price': idea.target_price,
                'current_price': round(current_price, 2),
                'pnl_pct': round(pnl_pct, 2),
                'status': status,
                'submitted_date': idea.submitted_date,
            })

        # Sort by P&L descending
        scored_ideas.sort(key=lambda x: x['pnl_pct'], reverse=True)
        return scored_ideas[:limit]

    def get_user_calibration(self, user_id: str) -> CalibrationData:
        """Get calibration data for a user."""
        return self._calculate_calibration(user_id)


# ── Module-level instance ────────────────────────────────────────────────────

_service_instance = None

def get_leaderboard_service() -> LeaderboardService:
    """Get singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = LeaderboardService()
    return _service_instance
