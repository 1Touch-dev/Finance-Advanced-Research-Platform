"""
Decision layer — combines the rule gates and the LLM judge into one publish
decision. Rules always retain hard-veto power: a hard_fail from
quality_gate_service blocks publication regardless of what the judge says, so
an LLM can never override a compliance rule. This is the non-negotiable design
constraint from docs/Quality-Judge.md.

Modes:
  rules  - existing run_quality_gates() only (unchanged default behavior).
  judge  - LLM-as-judge only (0..1 score + issues + reasoning).
  blend  - rules veto first; otherwise weighted combination of rule score and
           judge score. Degrades to pure rules if the judge is unavailable.
  ml     - rules veto first; otherwise the supervised classifier (Phase 3b,
           trained on rule_features -> judge_publishable) substitutes for the
           judge - no LLM call, near-zero latency/cost. Degrades to pure rules
           if no model has been trained yet (see train_quality_classifier.py).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.quality_gate_service import run_quality_gates

from .classifier import ClassifierVerdict, classify
from .judge import JudgeVerdict, judge_report
from .labels import rule_features_dict

logger = logging.getLogger(__name__)

VALID_MODES = ("rules", "judge", "blend", "ml")

# blend weighting: judge gets more weight because it catches what rules can't,
# but rules still gate hard failures unconditionally before this ever applies.
_BLEND_RULE_WEIGHT = float(os.getenv("QUALITY_BLEND_RULE_WEIGHT", "0.4"))
_BLEND_JUDGE_WEIGHT = 1.0 - _BLEND_RULE_WEIGHT
_PUBLISH_FLOOR = float(os.getenv("QUALITY_PUBLISH_FLOOR", "0.7"))
_REVIEW_FLOOR = float(os.getenv("QUALITY_REVIEW_FLOOR", "0.5"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decision_from_score(score: Optional[float], hard_blocked: bool) -> str:
    if hard_blocked:
        return "blocked"
    if score is None:
        return "needs_review"
    if score >= _PUBLISH_FLOOR:
        return "publication_ready"
    if score >= _REVIEW_FLOOR:
        return "needs_review"
    return "blocked"


def evaluate(data: Dict[str, Any], mode: str = "rules", *, report_id: Optional[str] = None,
             log_labels: bool = True, label_source: str = "live",
             label_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Evaluate a report's `data` dict and return a normalized decision:
    {mode, decision, rule_result, judge_result, combined_score, checked_at}

    `label_source` is provenance passed through to labels.log_judgment (see
    labels.py) - "live" for real request traffic (default), "backfill" for
    replayed historical reports, "synthetic" for generated reports.

    `label_path` overrides the default exports/quality_labels.jsonl target -
    used by generate_synthetic_labels.py to keep synthetic labels physically
    separate from real ones (exports/quality_labels_synthetic.jsonl), so
    train_quality_classifier.py has to explicitly opt in to blending them.
    """
    if mode not in VALID_MODES:
        logger.warning("unknown quality mode %r; defaulting to 'rules'", mode)
        mode = "rules"

    rule_result: Optional[Dict[str, Any]] = None
    judge_result: Optional[JudgeVerdict] = None
    ml_result: Optional[ClassifierVerdict] = None

    if mode in ("rules", "blend", "ml"):
        rule_result = run_quality_gates(data)

    if mode in ("judge", "blend"):
        judge_result = judge_report(data)

    if mode == "ml":
        ml_result = classify(rule_features_dict(rule_result))

    hard_blocked = bool(rule_result and rule_result.get("hard_failures"))

    if mode == "rules":
        decision = "blocked" if hard_blocked else (
            "publication_ready" if rule_result["passed"] else "needs_review"
        )
        combined_score = rule_result["overall_score"] if rule_result else None

    elif mode == "judge":
        if judge_result.ok:
            decision = _decision_from_score(judge_result.score, hard_blocked=False)
            if judge_result.pre_screen_flags:
                decision = "blocked"
        else:
            decision = "needs_review"  # judge unavailable; no rules ran, can't block
        combined_score = judge_result.score if judge_result.ok else None

    elif mode == "ml":
        if hard_blocked:
            decision = "blocked"
            combined_score = rule_result["overall_score"]
        elif ml_result and ml_result.ok:
            combined_score = ml_result.score
            decision = _decision_from_score(combined_score, hard_blocked=False)
        else:
            # No trained model yet -> degrade to pure rules (fail-soft, same
            # pattern as blend's judge-unavailable branch).
            combined_score = rule_result["overall_score"]
            decision = "publication_ready" if rule_result["passed"] else "needs_review"

    else:  # blend
        if hard_blocked:
            decision = "blocked"
            combined_score = rule_result["overall_score"]
        elif judge_result and judge_result.ok:
            if judge_result.pre_screen_flags:
                decision = "blocked"
                combined_score = 0.0
            else:
                combined_score = round(
                    _BLEND_RULE_WEIGHT * rule_result["overall_score"]
                    + _BLEND_JUDGE_WEIGHT * judge_result.score,
                    4,
                )
                decision = _decision_from_score(combined_score, hard_blocked=False)
        else:
            # Judge unavailable -> degrade to pure rules (fail-soft).
            combined_score = rule_result["overall_score"]
            decision = "publication_ready" if rule_result["passed"] else "needs_review"

    result = {
        "mode": mode,
        "decision": decision,
        "combined_score": combined_score,
        "rule_result": rule_result,
        "judge_result": judge_result.to_dict() if judge_result is not None else None,
        "checked_at": _now(),
    }
    if mode == "ml":
        result["ml_result"] = ml_result.to_dict() if ml_result is not None else None

    if log_labels and judge_result is not None and os.getenv("QUALITY_LABEL_LOG", "on") != "off":
        try:
            from .labels import log_judgment
            log_judgment(data, rule_result, judge_result, report_id=report_id, source=label_source,
                         path=label_path)
        except Exception as exc:  # label logging must never break a request
            logger.debug("label logging skipped: %s", exc)

    return result
