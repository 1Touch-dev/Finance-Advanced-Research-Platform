#!/usr/bin/env python
"""
Train the quality classifier (Phase 3b) from exports/quality_labels.jsonl.

This is the *only* place the label source and minimum-N gate are decided —
see docs/Quality-Judge.md for why: the documented sequencing is judge now ->
labels accumulate -> classifier once N is sufficient. Running this script on
too few labels will refuse to train by default (loudly, not silently) rather
than ship a model that's just memorizing noise.

Usage:
  python -m app.scripts.train_quality_classifier
  python -m app.scripts.train_quality_classifier --labels exports/quality_labels.jsonl
  python -m app.scripts.train_quality_classifier --min-samples 200
  python -m app.scripts.train_quality_classifier --force --min-samples 10   # dev/demo only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_MIN_SAMPLES = 200  # industry rule of thumb for a binary classifier, per docs/Quality-Judge.md


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


def _usable_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Only rows with a real judge verdict (ok=True, publishable is a bool)
    and at least one non-empty rule_features dict are trainable."""
    return [
        r for r in rows
        if r.get("judge_ok") and isinstance(r.get("judge_publishable"), bool) and r.get("rule_features")
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", type=Path, default=Path("exports/quality_labels.jsonl"))
    ap.add_argument("--out", type=Path, default=None, help="defaults to QUALITY_MODEL_PATH or app/models/quality_classifier.joblib")
    ap.add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES)
    ap.add_argument("--force", action="store_true", help="train anyway below --min-samples (dev/demo only, never for production use)")
    ap.add_argument("--test-size", type=float, default=0.2)
    args = ap.parse_args()

    from app.services.quality.classifier import FEATURE_KEYS, QualityClassifier, vectorize

    rows = _usable_rows(_load_labels(args.labels))
    n = len(rows)
    print(f"[train] {n} usable labeled rows in {args.labels}")

    if n < args.min_samples and not args.force:
        print(
            f"[train] REFUSING to train: {n} < --min-samples {args.min_samples}. "
            f"This is intentional (see docs/Quality-Judge.md) — a classifier trained on "
            f"too few labels just memorizes noise. Keep running the judge/blend modes "
            f"(or backfill_quality_labels.py) to accumulate more labels, or pass "
            f"--force --min-samples N for an explicit dev/demo model (NOT for production)."
        )
        return 1

    if n < 2 or len({r["judge_publishable"] for r in rows}) < 2:
        print("[train] need at least 2 samples and both classes present (publishable True and False). Aborting.")
        return 1

    demo_mode = n < DEFAULT_MIN_SAMPLES
    if demo_mode:
        print(
            f"[train] WARNING: training with --force on only {n} samples (recommended floor: "
            f"{DEFAULT_MIN_SAMPLES}). This model is a DEV/DEMO artifact to validate the pipeline "
            f"end-to-end - do not treat its scores as production-grade."
        )

    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score

    X = np.array([vectorize(r["rule_features"]) for r in rows])
    y = np.array([1 if r["judge_publishable"] else 0 for r in rows])

    metrics: Dict[str, Any] = {"n_samples": n, "demo_mode": demo_mode, "class_balance": {
        "publishable": int(y.sum()), "not_publishable": int(n - y.sum()),
    }}

    can_split = n >= 10 and min(np.bincount(y)) >= 2
    if can_split:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=args.test_size, random_state=42, stratify=y,
        )
    else:
        print("[train] sample too small for a held-out split; evaluating on training data only (optimistic, expected with a demo-sized set).")
        X_train, X_test, y_train, y_test = X, X, y, y

    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    metrics.update({"accuracy": round(float(acc), 4), "f1": round(float(f1), 4), "held_out_split": can_split})

    print(f"[train] accuracy={acc:.3f} f1={f1:.3f} (held_out_split={can_split})")
    print("[train] feature coefficients (higher magnitude = more influential):")
    for key, coef in sorted(zip(FEATURE_KEYS, clf.coef_[0]), key=lambda kv: -abs(kv[1])):
        print(f"    {key:28s} {coef:+.3f}")

    version = f"v1-n{n}" + ("-demo" if demo_mode else "")
    model = QualityClassifier(clf, FEATURE_KEYS, version, metrics=metrics)
    out_path = model.save(args.out)
    print(f"[train] saved model to {out_path} (version={version})")

    from app.services.quality import classifier as classifier_mod
    classifier_mod.reset_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
