"""
Tests for app.services.quality.classifier (Phase 3b) — no network dependency,
trains tiny in-memory models via joblib round-trips to temp paths.

Covers:
  - vectorize() is order-stable and defensive against missing/non-numeric keys
  - save/load round-trip preserves estimator + metadata
  - predict() fail-soft: no model on disk -> ok=False, never raises
  - get_classifier() caches and reset_cache() forces a reload
  - decision.evaluate(mode="ml") wiring: rules veto first, degrades to rules
    when no model is trained, uses the classifier score otherwise
"""
from __future__ import annotations

import pytest

from app.services.quality import decision
from app.services.quality.classifier import (
    FEATURE_KEYS,
    ClassifierVerdict,
    QualityClassifier,
    classify,
    get_classifier,
    reset_cache,
    vectorize,
)


@pytest.fixture(autouse=True)
def _clear_classifier_cache():
    reset_cache()
    yield
    reset_cache()


def test_vectorize_is_order_stable_and_defensive():
    features = {"citation_coverage": 0.9, "overall_score": 0.8, "hard_failure_count": 2, "unrelated": "ignored"}
    vec = vectorize(features)
    assert len(vec) == len(FEATURE_KEYS)
    assert vec[FEATURE_KEYS.index("citation_coverage")] == 0.9
    assert vec[FEATURE_KEYS.index("overall_score")] == 0.8
    assert vec[FEATURE_KEYS.index("hard_failure_count")] == 2.0
    # missing / non-numeric keys become 0.0, never raise
    assert vec[FEATURE_KEYS.index("duplicate_detection")] == 0.0


def test_vectorize_handles_empty_and_none_like_inputs():
    assert vectorize({}) == [0.0] * len(FEATURE_KEYS)
    assert vectorize({"overall_score": "not-a-number"}) == [0.0] * len(FEATURE_KEYS)


class _StubEstimator:
    """Minimal sklearn-shaped stub so tests don't depend on actually fitting
    a real LogisticRegression (keeps this suite fast and dependency-light)."""

    def __init__(self, positive_score: float = 0.75):
        self.positive_score = positive_score

    def predict_proba(self, X):
        return [[1 - self.positive_score, self.positive_score] for _ in X]


def test_classifier_save_and_load_round_trip(tmp_path):
    model_path = tmp_path / "quality_classifier.joblib"
    model = QualityClassifier(_StubEstimator(0.9), FEATURE_KEYS, "test-v1", metrics={"n_samples": 5})
    saved_path = model.save(model_path)
    assert saved_path == model_path
    assert model_path.exists()

    loaded = QualityClassifier.load(model_path)
    assert loaded is not None
    assert loaded.version == "test-v1"
    assert loaded.feature_keys == FEATURE_KEYS
    assert loaded.metrics["n_samples"] == 5

    verdict = loaded.predict({"overall_score": 0.8})
    assert verdict.ok is True
    assert verdict.score == pytest.approx(0.9)
    assert verdict.publishable is True


def test_classifier_load_missing_path_returns_none(tmp_path):
    assert QualityClassifier.load(tmp_path / "does_not_exist.joblib") is None


def test_classifier_predict_fail_soft_on_broken_estimator():
    class _Boom:
        def predict_proba(self, X):
            raise RuntimeError("model corrupted")

    model = QualityClassifier(_Boom(), FEATURE_KEYS, "broken-v1")
    verdict = model.predict({"overall_score": 0.5})
    assert verdict.ok is False
    assert "model corrupted" in verdict.error


def test_classify_fail_soft_when_no_model_trained(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.quality.classifier._DEFAULT_MODEL_PATH", tmp_path / "missing.joblib")
    reset_cache()
    verdict = classify({"overall_score": 0.5})
    assert verdict.ok is False
    assert verdict.score is None


def test_get_classifier_caches_and_reset_forces_reload(tmp_path, monkeypatch):
    model_path = tmp_path / "quality_classifier.joblib"
    monkeypatch.setattr("app.services.quality.classifier._DEFAULT_MODEL_PATH", model_path)
    reset_cache()

    assert get_classifier() is None  # nothing trained yet

    model = QualityClassifier(_StubEstimator(0.6), FEATURE_KEYS, "cache-v1")
    model.save(model_path)

    # Still None: cache was populated (as None) on the first call above.
    assert get_classifier() is None
    reset_cache()
    loaded = get_classifier()
    assert loaded is not None
    assert loaded.version == "cache-v1"


# ── decision layer: mode="ml" ─────────────────────────────────────────────────
DEEP_RESEARCH_REPORT = {
    "entity_name": "Acme Corp",
    "ticker": "ACME",
    "financial_intelligence": {
        "total_revenue": 1000000000,
        "source_url": "https://sec.gov/acme/10k",
        "segments": [{"name": "Core", "revenue": 1000000000, "source_url": "https://sec.gov/acme/10k#seg"}],
    },
    "insider_transactions": {
        "transactions": [{"owner_name": "Jane Doe", "transaction_code": "S", "shares": 1000,
                           "source_url": "https://sec.gov/form4/acme"}],
    },
    "proxy_intelligence": {"executives": [{"name": "Jane Doe"}]},
    "board_interlocks": {"people": [{"name": "Jane Doe"}]},
}
HARD_FAIL_REPORT = {
    "entity_name": "Uncited Co",
    "ticker": "UNCT",
    "financial_intelligence": {"total_revenue": 500000000, "segments": [{"name": "Core", "revenue": 500000000}]},
}


def test_decision_ml_mode_degrades_to_rules_when_no_model_trained(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.quality.classifier._DEFAULT_MODEL_PATH", tmp_path / "missing.joblib")
    reset_cache()
    result = decision.evaluate(DEEP_RESEARCH_REPORT, mode="ml", log_labels=False)
    assert result["ml_result"]["ok"] is False
    assert result["decision"] == "publication_ready"
    assert result["combined_score"] == result["rule_result"]["overall_score"]


def test_decision_ml_mode_uses_classifier_score_when_available(tmp_path, monkeypatch):
    model_path = tmp_path / "quality_classifier.joblib"
    QualityClassifier(_StubEstimator(0.9), FEATURE_KEYS, "test-v1").save(model_path)
    monkeypatch.setattr("app.services.quality.classifier._DEFAULT_MODEL_PATH", model_path)
    reset_cache()

    result = decision.evaluate(DEEP_RESEARCH_REPORT, mode="ml", log_labels=False)
    assert result["ml_result"]["ok"] is True
    assert result["combined_score"] == pytest.approx(0.9)
    assert result["decision"] == "publication_ready"


def test_decision_ml_mode_respects_rules_veto_regardless_of_classifier_score(tmp_path, monkeypatch):
    model_path = tmp_path / "quality_classifier.joblib"
    QualityClassifier(_StubEstimator(0.99), FEATURE_KEYS, "test-v1").save(model_path)
    monkeypatch.setattr("app.services.quality.classifier._DEFAULT_MODEL_PATH", model_path)
    reset_cache()

    result = decision.evaluate(HARD_FAIL_REPORT, mode="ml", log_labels=False)
    assert result["decision"] == "blocked"  # rules veto wins even though classifier score is near-perfect
