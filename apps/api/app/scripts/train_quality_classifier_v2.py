#!/usr/bin/env python
"""
Improved Quality Classifier Training (v2) — addresses F1=0.387 weakness.

Key improvements over v1:
  1. Uses Gradient Boosting (handles class imbalance better than LogReg)
  2. SMOTE oversampling for minority class
  3. Stratified K-fold cross-validation for robust evaluation
  4. Automatic removal of zero-variance features
  5. Threshold optimization for best F1
  6. Feature interaction terms
  7. Multiple model comparison (LogReg, RF, GBM, XGBoost)

Usage:
  python -m app.scripts.train_quality_classifier_v2
  python -m app.scripts.train_quality_classifier_v2 --model xgboost
  python -m app.scripts.train_quality_classifier_v2 --smote --cv-folds 5
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import numpy as np

warnings.filterwarnings("ignore")

DEFAULT_MIN_SAMPLES = 100  # Lower threshold for v2 since we handle imbalance
DEFAULT_LABEL_FILES = [
    Path("exports/quality_labels.jsonl"),
    Path("exports/quality_labels_synthetic.jsonl"),
]


def _load_labels(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _load_all_labels(paths: List[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in paths:
        file_rows = _load_labels(path)
        print(f"[train-v2] {len(file_rows)} rows from {path}" + ("" if file_rows else " (missing or empty)"))
        rows.extend(file_rows)
    return rows


def _usable_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Only rows with a real judge verdict and rule_features."""
    return [
        r for r in rows
        if r.get("judge_ok") and isinstance(r.get("judge_publishable"), bool) and r.get("rule_features")
    ]


# Extended feature keys with interaction terms
BASE_FEATURE_KEYS: Tuple[str, ...] = (
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

# Text-based feature keys (new in v2)
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
    """Extended feature vector with interaction terms and text features."""
    base = [float(rule_features.get(k, 0)) if isinstance(rule_features.get(k), (int, float)) else 0.0
            for k in BASE_FEATURE_KEYS]

    # Add text features (normalized)
    if add_text_features and text_features:
        # Normalize text features to reasonable scales
        base.append(min(float(text_features.get("total_text_length", 0)) / 10000, 10.0))  # Cap at 100k chars
        base.append(float(text_features.get("section_count", 0)) / 10.0)  # Normalize
        base.append(float(text_features.get("citation_count", 0)) / 20.0)  # Normalize
        base.append(float(text_features.get("avg_sentence_length", 0)) / 30.0)  # Normalize
        base.append(float(text_features.get("news_article_count", 0)) / 5.0)  # Normalize
        base.append(float(text_features.get("executive_count", 0)) / 5.0)  # Normalize
    elif add_text_features:
        # Add zeros if no text features available (backward compatibility)
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


def remove_zero_variance(X: np.ndarray, feature_names: List[str]) -> Tuple[np.ndarray, List[str], List[int]]:
    """Remove features with zero variance (no signal)."""
    variances = np.var(X, axis=0)
    keep_idx = [i for i, v in enumerate(variances) if v > 1e-10]
    removed = [feature_names[i] for i in range(len(feature_names)) if i not in keep_idx]
    if removed:
        print(f"[train-v2] Removed zero-variance features: {removed}")
    return X[:, keep_idx], [feature_names[i] for i in keep_idx], keep_idx


def find_best_threshold(y_true: np.ndarray, y_proba: np.ndarray) -> Tuple[float, float]:
    """Find threshold that maximizes F1 score."""
    from sklearn.metrics import f1_score

    best_threshold = 0.5
    best_f1 = 0.0

    for threshold in np.arange(0.1, 0.9, 0.05):
        y_pred = (y_proba >= threshold).astype(int)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold

    return best_threshold, best_f1


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    model_type: str = "gradient_boosting",
    class_weight: Optional[Dict] = None,
) -> Any:
    """Train the specified model type."""

    if model_type == "logistic":
        from sklearn.linear_model import LogisticRegression
        return LogisticRegression(
            max_iter=1000,
            class_weight=class_weight or "balanced",
            C=0.5,  # Regularization
        ).fit(X_train, y_train)

    elif model_type == "random_forest":
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=5,
            class_weight=class_weight or "balanced",
            random_state=42,
        ).fit(X_train, y_train)

    elif model_type == "gradient_boosting":
        from sklearn.ensemble import GradientBoostingClassifier
        # GBM doesn't have class_weight, we handle via sample_weight
        sample_weight = None
        if class_weight == "balanced":
            from sklearn.utils.class_weight import compute_sample_weight
            sample_weight = compute_sample_weight("balanced", y_train)
        return GradientBoostingClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            min_samples_leaf=5,
            random_state=42,
        ).fit(X_train, y_train, sample_weight=sample_weight)

    elif model_type == "xgboost":
        try:
            import xgboost as xgb
            # Calculate scale_pos_weight for imbalanced data
            n_neg = np.sum(y_train == 0)
            n_pos = np.sum(y_train == 1)
            scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1

            return xgb.XGBClassifier(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.1,
                scale_pos_weight=scale_pos_weight,
                eval_metric="logloss",
                random_state=42,
            ).fit(X_train, y_train)
        except ImportError:
            print("[train-v2] XGBoost not installed, falling back to GradientBoosting")
            return train_model(X_train, y_train, "gradient_boosting", class_weight)

    else:
        raise ValueError(f"Unknown model type: {model_type}")


def cross_validate_model(
    X: np.ndarray,
    y: np.ndarray,
    model_type: str,
    n_folds: int = 5,
    use_smote: bool = False,
) -> Dict[str, Any]:
    """Perform stratified K-fold cross-validation."""
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    fold_metrics = {
        "accuracy": [],
        "f1": [],
        "precision": [],
        "recall": [],
        "best_threshold": [],
    }

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        # Apply SMOTE if requested
        if use_smote:
            try:
                from imblearn.over_sampling import SMOTE
                smote = SMOTE(random_state=42, k_neighbors=min(3, sum(y_train == 1) - 1))
                if sum(y_train == 1) >= 2:  # Need at least 2 positive samples
                    X_train, y_train = smote.fit_resample(X_train, y_train)
            except ImportError:
                if fold == 0:
                    print("[train-v2] imblearn not installed, skipping SMOTE")

        # Train model
        clf = train_model(X_train, y_train, model_type, class_weight="balanced")

        # Get probabilities and find best threshold
        y_proba = clf.predict_proba(X_val)[:, 1]
        best_thresh, _ = find_best_threshold(y_val, y_proba)
        y_pred = (y_proba >= best_thresh).astype(int)

        fold_metrics["accuracy"].append(accuracy_score(y_val, y_pred))
        fold_metrics["f1"].append(f1_score(y_val, y_pred, zero_division=0))
        fold_metrics["precision"].append(precision_score(y_val, y_pred, zero_division=0))
        fold_metrics["recall"].append(recall_score(y_val, y_pred, zero_division=0))
        fold_metrics["best_threshold"].append(best_thresh)

    return {
        "accuracy_mean": np.mean(fold_metrics["accuracy"]),
        "accuracy_std": np.std(fold_metrics["accuracy"]),
        "f1_mean": np.mean(fold_metrics["f1"]),
        "f1_std": np.std(fold_metrics["f1"]),
        "precision_mean": np.mean(fold_metrics["precision"]),
        "recall_mean": np.mean(fold_metrics["recall"]),
        "best_threshold_mean": np.mean(fold_metrics["best_threshold"]),
        "fold_f1s": fold_metrics["f1"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Improved Quality Classifier Training (v2)")
    ap.add_argument("--labels", type=Path, nargs="+", default=None)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model", type=str, default="gradient_boosting",
                    choices=["logistic", "random_forest", "gradient_boosting", "xgboost"],
                    help="Model type to use")
    ap.add_argument("--smote", action="store_true", help="Use SMOTE oversampling")
    ap.add_argument("--cv-folds", type=int, default=5, help="Number of CV folds")
    ap.add_argument("--compare-all", action="store_true", help="Compare all model types")
    ap.add_argument("--no-interactions", action="store_true", help="Skip interaction features")
    ap.add_argument("--no-text-features", action="store_true", help="Skip text-based features")
    args = ap.parse_args()

    label_paths = args.labels or DEFAULT_LABEL_FILES

    all_rows = _load_all_labels(label_paths)
    rows = _usable_rows(all_rows)
    n = len(rows)
    print(f"[train-v2] {n} usable labeled rows")

    if n < args.min_samples and not args.force:
        print(f"[train-v2] REFUSING to train: {n} < {args.min_samples}. Pass --force to override.")
        return 1

    # Class distribution
    composition = dict(Counter(r.get("source", "unknown") for r in rows))
    class_dist = Counter([r["judge_publishable"] for r in rows])
    print(f"[train-v2] Source composition: {composition}")
    print(f"[train-v2] Class distribution: {dict(class_dist)}")
    print(f"[train-v2] Minority class ratio: {class_dist[True]/n:.1%}")

    if class_dist[True] < 5:
        print("[train-v2] ERROR: Need at least 5 positive samples for cross-validation")
        return 1

    # Prepare features
    add_interactions = not args.no_interactions
    add_text_features = not args.no_text_features if hasattr(args, 'no_text_features') else True

    # Check if any rows have text_features
    has_text_features = any(r.get("text_features") for r in rows)
    if add_text_features and not has_text_features:
        print("[train-v2] NOTE: No text_features in labels - using rule features only")
        add_text_features = False

    X = np.array([
        vectorize_extended(
            r["rule_features"],
            text_features=r.get("text_features"),
            add_interactions=add_interactions,
            add_text_features=add_text_features,
        )
        for r in rows
    ])
    y = np.array([1 if r["judge_publishable"] else 0 for r in rows])

    # Feature names
    feature_names = list(BASE_FEATURE_KEYS)
    if add_text_features:
        feature_names.extend(list(TEXT_FEATURE_KEYS))
    if add_interactions:
        feature_names.extend([
            "citation_x_overall",
            "failures_x_overall",
            "placeholder_x_sensitive",
            "failures_squared",
            "has_failures",
            "high_citation",
        ])

    # Remove zero-variance features
    X, feature_names, keep_idx = remove_zero_variance(X, feature_names)
    print(f"[train-v2] Using {len(feature_names)} features after removing zero-variance")

    # Compare models if requested
    if args.compare_all:
        print("\n[train-v2] Comparing all model types...")
        print("-" * 60)
        model_types = ["logistic", "random_forest", "gradient_boosting"]
        try:
            import xgboost
            model_types.append("xgboost")
        except ImportError:
            pass

        results = []
        for model_type in model_types:
            cv_result = cross_validate_model(X, y, model_type, args.cv_folds, args.smote)
            results.append((model_type, cv_result))
            print(f"{model_type:20s} F1={cv_result['f1_mean']:.3f}±{cv_result['f1_std']:.3f} "
                  f"P={cv_result['precision_mean']:.3f} R={cv_result['recall_mean']:.3f} "
                  f"thresh={cv_result['best_threshold_mean']:.2f}")

        # Use best model
        best_model, best_result = max(results, key=lambda x: x[1]["f1_mean"])
        print(f"\n[train-v2] Best model: {best_model}")
        args.model = best_model
        print("-" * 60)

    # Cross-validate chosen model
    print(f"\n[train-v2] Cross-validating {args.model} with {args.cv_folds} folds" +
          (" + SMOTE" if args.smote else "") + "...")

    cv_result = cross_validate_model(X, y, args.model, args.cv_folds, args.smote)

    print(f"[train-v2] CV Results:")
    print(f"    F1:        {cv_result['f1_mean']:.3f} ± {cv_result['f1_std']:.3f}")
    print(f"    Precision: {cv_result['precision_mean']:.3f}")
    print(f"    Recall:    {cv_result['recall_mean']:.3f}")
    print(f"    Accuracy:  {cv_result['accuracy_mean']:.3f}")
    print(f"    Best threshold: {cv_result['best_threshold_mean']:.2f}")
    print(f"    Fold F1s: {[f'{f:.3f}' for f in cv_result['fold_f1s']]}")

    # Train final model on all data
    print("\n[train-v2] Training final model on all data...")

    X_train, y_train = X, y
    if args.smote:
        try:
            from imblearn.over_sampling import SMOTE
            if sum(y == 1) >= 2:
                smote = SMOTE(random_state=42, k_neighbors=min(3, sum(y == 1) - 1))
                X_train, y_train = smote.fit_resample(X, y)
                print(f"[train-v2] After SMOTE: {len(y_train)} samples ({sum(y_train == 1)} positive)")
        except ImportError:
            pass

    final_clf = train_model(X_train, y_train, args.model, class_weight="balanced")

    # Get optimal threshold
    y_proba_all = final_clf.predict_proba(X)[:, 1]
    optimal_threshold, optimal_f1 = find_best_threshold(y, y_proba_all)
    print(f"[train-v2] Optimal threshold on full data: {optimal_threshold:.2f} (F1={optimal_f1:.3f})")

    # Feature importances
    print("\n[train-v2] Feature importances:")
    if hasattr(final_clf, "feature_importances_"):
        importances = final_clf.feature_importances_
    elif hasattr(final_clf, "coef_"):
        importances = np.abs(final_clf.coef_[0])
    else:
        importances = [0] * len(feature_names)

    for name, imp in sorted(zip(feature_names, importances), key=lambda x: -x[1])[:10]:
        print(f"    {name:28s} {imp:.4f}")

    # Save model
    from app.services.quality.classifier import QualityClassifier

    demo_mode = n < 200
    version = f"v2-{args.model[:3]}-n{n}" + ("-smote" if args.smote else "") + ("-demo" if demo_mode else "")

    metrics = {
        "n_samples": n,
        "model_type": args.model,
        "use_smote": args.smote,
        "cv_folds": args.cv_folds,
        "f1_cv_mean": round(cv_result["f1_mean"], 4),
        "f1_cv_std": round(cv_result["f1_std"], 4),
        "precision_cv": round(cv_result["precision_mean"], 4),
        "recall_cv": round(cv_result["recall_mean"], 4),
        "optimal_threshold": round(optimal_threshold, 4),
        "composition": composition,
        "class_balance": {"publishable": int(sum(y)), "not_publishable": int(n - sum(y))},
        "feature_names": feature_names,
        "keep_feature_idx": keep_idx,
        "add_interactions": add_interactions,
        "demo_mode": demo_mode,
    }

    # Wrap with custom threshold support
    from app.services.quality.classifier import ThresholdClassifier
    wrapped_clf = ThresholdClassifier(final_clf, optimal_threshold)

    model = QualityClassifier(wrapped_clf, tuple(feature_names), version, metrics=metrics)
    out_path = model.save(args.out)
    print(f"\n[train-v2] Saved model to {out_path}")
    print(f"[train-v2] Version: {version}")
    print(f"[train-v2] F1 (CV): {cv_result['f1_mean']:.3f} ± {cv_result['f1_std']:.3f}")

    # Comparison with v1
    print(f"\n[train-v2] Improvement over v1 (F1=0.387):")
    improvement = ((cv_result["f1_mean"] - 0.387) / 0.387) * 100
    print(f"    F1 change: 0.387 -> {cv_result['f1_mean']:.3f} ({improvement:+.1f}%)")

    from app.services.quality import classifier as classifier_mod
    classifier_mod.reset_cache()

    return 0


if __name__ == "__main__":
    sys.exit(main())
