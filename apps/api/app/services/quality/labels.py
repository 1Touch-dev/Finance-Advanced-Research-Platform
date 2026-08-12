"""
Label logging — the classifier bootstrap.

Every judge run (mode=judge or mode=blend) appends one line to
exports/quality_labels.jsonl: {ts, report_id, rule_features, rule_pass,
judge_score, judge_publishable, judge_dimensions, judge_issues}. This is the
concrete artifact that makes a real supervised classifier trainable in the
future — today there are zero real quality labels anywhere in this system; from
the moment this hook runs, every report accumulates one.

Fail-soft: logging failures never raise (env-gated by QUALITY_LABEL_LOG=on,
default on; wrapped in try/except by the caller in decision.py too, as a
second layer of protection).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .judge import JudgeVerdict

logger = logging.getLogger(__name__)

_EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))
_LABELS_PATH = _EXPORT_DIR / "quality_labels.jsonl"


def _rule_features(rule_result: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Flatten the 10 gate scores into a {gate_name: score} feature dict."""
    if not rule_result:
        return {}
    features: Dict[str, float] = {}
    for r in rule_result.get("results", []):
        name = r.get("gate", "").lower().replace(" ", "_").replace("-", "_")
        if name:
            features[name] = round(float(r.get("score", 0.0)), 4)
    features["overall_score"] = round(float(rule_result.get("overall_score", 0.0)), 4)
    features["hard_failure_count"] = len(rule_result.get("hard_failures", []) or [])
    return features


def build_label_row(
    data: Dict[str, Any],
    rule_result: Optional[Dict[str, Any]],
    judge_verdict: Optional[JudgeVerdict],
    *,
    report_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Pure function: assemble the JSONL row without writing it (testable)."""
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "report_id": report_id or data.get("ticker") or data.get("entity_name"),
        "rule_features": _rule_features(rule_result),
        "rule_pass": bool(rule_result.get("passed")) if rule_result else None,
        "judge_score": judge_verdict.score if judge_verdict and judge_verdict.ok else None,
        "judge_publishable": judge_verdict.publishable if judge_verdict and judge_verdict.ok else None,
        "judge_dimensions": judge_verdict.dimensions if judge_verdict and judge_verdict.ok else {},
        "judge_issues": judge_verdict.issues if judge_verdict and judge_verdict.ok else [],
        "judge_ok": bool(judge_verdict.ok) if judge_verdict else False,
    }


def log_judgment(
    data: Dict[str, Any],
    rule_result: Optional[Dict[str, Any]],
    judge_verdict: Optional[JudgeVerdict],
    *,
    report_id: Optional[str] = None,
    path: Optional[Path] = None,
) -> None:
    """Append one label row to exports/quality_labels.jsonl. Never raises."""
    if os.getenv("QUALITY_LABEL_LOG", "on") == "off":
        return
    try:
        row = build_label_row(data, rule_result, judge_verdict, report_id=report_id)
        target = path or _LABELS_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception as exc:
        logger.debug("quality label logging failed: %s", exc)
