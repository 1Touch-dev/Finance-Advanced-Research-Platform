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


def rule_features_dict(rule_result: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """Flatten the 10 gate scores into a {gate_name: score} feature dict.
    Public because decision.py's mode="ml" reuses this exact vectorization
    (must match app.services.quality.classifier.FEATURE_KEYS) - keeping it in
    one place avoids the two ever drifting apart."""
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


def text_features_dict(data: Dict[str, Any]) -> Dict[str, float]:
    """Extract text-based features from report data for classifier training.

    Features:
      - total_text_length: Total character count of all text fields
      - section_count: Number of major sections with content
      - citation_count: Number of source_url fields found
      - avg_sentence_length: Average sentence length (proxy for readability)
      - news_article_count: Number of news articles
      - executive_count: Number of named executives
    """
    features: Dict[str, float] = {}

    # Collect all text content
    all_text = []
    citation_count = 0
    section_count = 0

    def _extract_text(obj, depth=0):
        nonlocal citation_count, section_count
        if depth > 10:  # Prevent infinite recursion
            return
        if isinstance(obj, str):
            if len(obj) > 20:  # Meaningful text
                all_text.append(obj)
        elif isinstance(obj, dict):
            if "source_url" in obj and obj["source_url"]:
                citation_count += 1
            if depth == 1:  # Top-level keys are "sections"
                section_count += 1
            for v in obj.values():
                _extract_text(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                _extract_text(item, depth + 1)

    _extract_text(data)

    # Total text length
    total_text = " ".join(all_text)
    features["total_text_length"] = len(total_text)

    # Section count
    features["section_count"] = section_count

    # Citation count
    features["citation_count"] = citation_count

    # Average sentence length (proxy for readability)
    sentences = [s.strip() for s in total_text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    if sentences:
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        features["avg_sentence_length"] = round(avg_words, 2)
    else:
        features["avg_sentence_length"] = 0.0

    # News article count
    news = data.get("news_intelligence", {})
    articles = news.get("articles", []) if isinstance(news, dict) else []
    features["news_article_count"] = len(articles)

    # Executive count
    proxy = data.get("proxy_intelligence", {})
    execs = proxy.get("executives", []) if isinstance(proxy, dict) else []
    features["executive_count"] = len(execs)

    return features


# Backward-compatible alias (module-private name used before mode="ml" existed).
_rule_features = rule_features_dict


def build_label_row(
    data: Dict[str, Any],
    rule_result: Optional[Dict[str, Any]],
    judge_verdict: Optional[JudgeVerdict],
    *,
    report_id: Optional[str] = None,
    source: str = "live",
) -> Dict[str, Any]:
    """Pure function: assemble the JSONL row without writing it (testable).

    `source` is provenance, not a training signal: "live" (real request
    through decision.evaluate), "backfill" (replayed real historical report),
    or "synthetic" (LLM-generated report, see synthetic.py). Every consumer
    of quality_labels*.jsonl (train_quality_classifier.py, any future
    analysis) can filter/report on this - the honest-composition requirement
    is that synthetic volume is always visible, never silently blended away."""
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "report_id": report_id or data.get("ticker") or data.get("entity_name"),
        "source": source,
        "rule_features": _rule_features(rule_result),
        "text_features": text_features_dict(data),  # NEW: text-based features
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
    source: str = "live",
) -> None:
    """Append one label row to exports/quality_labels.jsonl. Never raises."""
    if os.getenv("QUALITY_LABEL_LOG", "on") == "off":
        return
    try:
        row = build_label_row(data, rule_result, judge_verdict, report_id=report_id, source=source)
        target = path or _LABELS_PATH
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a") as f:
            f.write(json.dumps(row) + "\n")
    except Exception as exc:
        logger.debug("quality label logging failed: %s", exc)
