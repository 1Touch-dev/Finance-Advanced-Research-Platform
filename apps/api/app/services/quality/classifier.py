"""
Supervised quality classifier (Phase 3b) — a cheap, LLM-free approximation of
the judge's publishable verdict, trained on the free `rule_features` that
run_quality_gates() already computes for every report.

Why distill the judge instead of training on "ground truth": there are no
human-reviewed labels yet (see docs/Quality-Judge.md — the documented
sequencing is judge now -> labels accumulate -> classifier once N is
sufficient -> human-in-the-loop for high-stakes calls). Training against the
judge's own `judge_publishable` is a legitimate first step (it lets a cheap
model triage most reports instantly and reserve the paid LLM call for
uncertain cases), but it is a proxy for the judge, not for human quality
judgment. The training script is intentionally the only place the label
source is chosen, so swapping to human-reviewed labels later is a one-line
change, not a rewrite of this module.

Fail-soft contract, matching judge.py: no trained model on disk -> ok=False,
never raises. decision.py treats ok=False as "ml unavailable, fall back to
rules" exactly like it already does when the judge has no API key.
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Order matters and must match the fixed key set labels.py writes into
# `rule_features` (gate name, lowercased/underscored, plus overall_score and
# hard_failure_count). A model trained against one order can't be safely
# scored with another, so this tuple is the single source of truth for both
# training (train_quality_classifier.py) and inference (this module).
FEATURE_KEYS: Tuple[str, ...] = (
    "citation_coverage",
    "arithmetic_reconciliation",
    "duplicate_detection",
    "news_staleness",
    "directionality_lint",
    "placeholder_scan",
    "fiscal_basis_lint",
    "landing_page_ban",
    "named_person_accuracy",
    "sensitive_claim_review",
    "overall_score",
    "hard_failure_count",
)

_DEFAULT_MODEL_PATH = Path(os.getenv("QUALITY_MODEL_PATH", "app/models/quality_classifier.joblib"))


def vectorize(rule_features: Dict[str, Any]) -> List[float]:
    """Pure, order-stable feature vector. Missing or non-numeric keys become
    0.0 so this never raises regardless of upstream shape drift."""
    return [float(rule_features.get(k)) if isinstance(rule_features.get(k), (int, float)) else 0.0
            for k in FEATURE_KEYS]


@dataclass
class ClassifierVerdict:
    ok: bool = False
    score: Optional[float] = None       # P(publishable) in [0, 1], per the judge proxy
    publishable: Optional[bool] = None
    error: Optional[str] = None
    model_version: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok, "score": self.score, "publishable": self.publishable,
            "error": self.error, "model_version": self.model_version,
        }


class QualityClassifier:
    """Thin wrapper around a fitted scikit-learn estimator + training
    metadata. Training lives in app/scripts/train_quality_classifier.py; this
    class only serializes, loads, and serves predictions."""

    def __init__(self, estimator: Any, feature_keys: Tuple[str, ...], version: str,
                 metrics: Optional[Dict[str, Any]] = None):
        self.estimator = estimator
        self.feature_keys = feature_keys
        self.version = version
        self.metrics = metrics or {}

    def predict(self, rule_features: Dict[str, Any]) -> ClassifierVerdict:
        try:
            x = [vectorize(rule_features)]
            proba = self.estimator.predict_proba(x)[0]
            score = float(proba[1])  # class 1 == publishable
            return ClassifierVerdict(
                ok=True, score=round(score, 4), publishable=score >= 0.5,
                model_version=self.version,
            )
        except Exception as exc:  # never raise into decision.py
            logger.warning("quality classifier predict failed: %s", exc)
            return ClassifierVerdict(ok=False, error=str(exc), model_version=self.version)

    def save(self, path: Optional[Path] = None) -> Path:
        import joblib
        path = path or _DEFAULT_MODEL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"estimator": self.estimator, "feature_keys": self.feature_keys,
             "version": self.version, "metrics": self.metrics},
            path,
        )
        return path

    @classmethod
    def load(cls, path: Optional[Path] = None) -> Optional["QualityClassifier"]:
        import joblib
        path = path or _DEFAULT_MODEL_PATH
        if not path.exists():
            return None
        try:
            blob = joblib.load(path)
            return cls(blob["estimator"], tuple(blob["feature_keys"]), blob["version"], blob.get("metrics"))
        except Exception as exc:
            logger.warning("failed to load quality classifier from %s: %s", path, exc)
            return None


_lock = threading.Lock()
_cached: Optional[QualityClassifier] = None
_cache_checked = False


def get_classifier(path: Optional[Path] = None) -> Optional[QualityClassifier]:
    """Lazily load and cache the classifier singleton (thread-safe). Returns
    None — not an exception — if no model has been trained yet."""
    global _cached, _cache_checked
    if path is not None:
        return QualityClassifier.load(path)
    with _lock:
        if not _cache_checked:
            _cached = QualityClassifier.load()
            _cache_checked = True
        return _cached


def reset_cache() -> None:
    """Test/ops hook to force a reload after retraining without a process restart."""
    global _cached, _cache_checked
    with _lock:
        _cached = None
        _cache_checked = False


def classify(rule_features: Dict[str, Any]) -> ClassifierVerdict:
    """Fail-soft entry point used by decision.py's mode="ml"."""
    clf = get_classifier()
    if clf is None:
        return ClassifierVerdict(ok=False, error=f"no trained model at {_DEFAULT_MODEL_PATH}")
    return clf.predict(rule_features)
