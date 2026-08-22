"""
Model & Idea Leaderboards Service (Band B #30)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.no_data import no_data_response, NoDataReason


class LeaderboardService:
    """Model and idea leaderboard service with Brier scoring."""

    def submit_prediction(self, user_id: str, ticker: str, prediction_type: str, predicted_value: float, confidence: float, target_date: str) -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(user_id, "prediction_submission", NoDataReason.API_UNAVAILABLE, details="Leaderboard rankings require aggregated data pipeline")}

    def resolve_prediction(self, prediction_id: str, actual_value: float) -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(prediction_id, "prediction_resolution", NoDataReason.API_UNAVAILABLE, details="Leaderboard rankings require aggregated data pipeline")}

    def get_user_score(self, user_id: str) -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(user_id, "user_score", NoDataReason.API_UNAVAILABLE, details="Leaderboard rankings require aggregated data pipeline")}

    def get_leaderboard(self, metric: str = "brier", limit: int = 20, category: Optional[str] = None) -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response("leaderboard", "leaderboard_rankings", NoDataReason.API_UNAVAILABLE, details="Leaderboard rankings require aggregated data pipeline")}

    def submit_idea(self, user_id: str, ticker: str, direction: str, thesis: str, entry_price: float, target_price: float, stop_price: float, time_horizon_days: int) -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(user_id, "idea_submission", NoDataReason.API_UNAVAILABLE, details="Leaderboard rankings require aggregated data pipeline")}

    def get_idea_leaderboard(self, limit: int = 20) -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response("leaderboard", "idea_leaderboard", NoDataReason.API_UNAVAILABLE, details="Leaderboard rankings require aggregated data pipeline")}

    def get_user_calibration(self, user_id: str) -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(user_id, "calibration_data", NoDataReason.API_UNAVAILABLE, details="Leaderboard rankings require aggregated data pipeline")}


_service_instance = None


def get_leaderboard_service() -> LeaderboardService:
    global _service_instance
    if _service_instance is None:
        _service_instance = LeaderboardService()
    return _service_instance
