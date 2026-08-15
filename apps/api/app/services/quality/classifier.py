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


class ThresholdClassifier:
    """Wrapper that applies a custom threshold for classification.

    Used by v2 models to optimize F1 score with a threshold != 0.5.
    Must be defined here (not in training script) for joblib pickle/unpickle.
    """

    def __init__(self, clf, threshold: float = 0.5):
        self.clf = clf
        self.threshold = threshold

    def predict_proba(self, X):
        return self.clf.predict_proba(X)

    def predict(self, X):
        import numpy as np
        proba = self.clf.predict_proba(X)[:, 1]
        return (proba >= self.threshold).astype(int)


def vectorize(rule_features: Dict[str, Any]) -> List[float]:
    """Pure, order-stable feature vector. Missing or non-numeric keys become
    0.0 so this never raises regardless of upstream shape drift."""
    return [float(rule_features.get(k)) if isinstance(rule_features.get(k), (int, float)) else 0.0
            for k in FEATURE_KEYS]


# Text-based feature keys (for v2 models with text features)
TEXT_FEATURE_KEYS: Tuple[str, ...] = (
    "total_text_length",
    "section_count",
    "citation_count",
    "avg_sentence_length",
    "news_article_count",
    "executive_count",
)


def vectorize_extended(
    rule_features: Dict[str, Any],
    text_features: Optional[Dict[str, Any]] = None,
    add_interactions: bool = True,
    add_text_features: bool = True,
) -> List[float]:
    """Extended feature vector with interaction terms and text features for v2 models."""
    base = [float(rule_features.get(k, 0)) if isinstance(rule_features.get(k), (int, float)) else 0.0
            for k in FEATURE_KEYS]

    # Add text features (normalized)
    if add_text_features:
        if text_features:
            # Normalize text features to reasonable scales
            base.append(min(float(text_features.get("total_text_length", 0)) / 10000, 10.0))
            base.append(float(text_features.get("section_count", 0)) / 10.0)
            base.append(float(text_features.get("citation_count", 0)) / 20.0)
            base.append(float(text_features.get("avg_sentence_length", 0)) / 30.0)
            base.append(float(text_features.get("news_article_count", 0)) / 5.0)
            base.append(float(text_features.get("executive_count", 0)) / 5.0)
        else:
            # Add zeros if no text features (backward compatibility)
            base.extend([0.0] * len(TEXT_FEATURE_KEYS))

    if add_interactions:
        # Add key interaction features
        citation = rule_features.get("citation_coverage", 0)
        overall = rule_features.get("overall_score", 0)
        hard_failures = rule_features.get("hard_failure_count", 0)
        placeholder = rule_features.get("placeholder_scan", 0)
        sensitive = rule_features.get("sensitive_claim_review", 0)

        # Interaction: citation * overall (strong signal when both high)
        base.append(float(citation) * float(overall))
        # Interaction: hard_failures * overall (penalize high score with failures)
        base.append(float(hard_failures) * float(overall))
        # Interaction: placeholder * sensitive (both quality signals)
        base.append(float(placeholder) * float(sensitive))
        # Squared hard_failure_count (non-linear penalty)
        base.append(float(hard_failures) ** 2)
        # Binary: any hard failures
        base.append(1.0 if hard_failures > 0 else 0.0)
        # Binary: high citation coverage
        base.append(1.0 if citation >= 0.5 else 0.0)

    return base


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

    def predict(
        self,
        rule_features: Dict[str, Any],
        text_features: Optional[Dict[str, Any]] = None,
    ) -> ClassifierVerdict:
        try:
            # Check if this is a v2 model with extended features
            is_v2 = self.version.startswith("v2") or self.metrics.get("add_interactions", False)

            if is_v2:
                # v2 model: use extended features and filter by keep_feature_idx
                add_text_features = bool(self.metrics.get("feature_names") and
                                         any("text" in f or "citation_count" in f or "news_article" in f
                                             for f in self.metrics.get("feature_names", [])))

                full_vec = vectorize_extended(
                    rule_features,
                    text_features=text_features,
                    add_interactions=True,
                    add_text_features=add_text_features,
                )
                keep_idx = self.metrics.get("keep_feature_idx")
                if keep_idx:
                    x = [[full_vec[i] for i in keep_idx]]
                else:
                    x = [full_vec]
            else:
                # v1 model: use basic features
                x = [vectorize(rule_features)]

            proba = self.estimator.predict_proba(x)[0]
            score = float(proba[1])  # class 1 == publishable

            # v2 models may have custom thresholds embedded in estimator
            # v1 models use 0.5 threshold
            threshold = getattr(self.estimator, "threshold", 0.5)
            publishable = score >= threshold

            return ClassifierVerdict(
                ok=True, score=round(score, 4), publishable=publishable,
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
