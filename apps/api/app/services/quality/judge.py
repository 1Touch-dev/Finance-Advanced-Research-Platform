"""
LLM-as-judge for report quality — the holistic layer the 10 regex gates in
quality_gate_service can't provide. Mirrors the pattern already proven in
services/rag/eval.py::llm_judge_faithfulness: JSON-only prompt, RAG_JUDGE_MODEL,
temperature 0, regex-extract JSON from the response, fail-soft to `ok=False`
(never raises) so callers can always fall back to rules.

Why an LLM here and not another rule: the gates can only catch failure shapes
someone already wrote a pattern for (missing citation, stale date, placeholder
text). They cannot tell "citations exist but are weak", "news is fresh but
irrelevant", "math is right but the framing is misleading", or "language is
vague/subtly biased". A holistic read is what catches those - see
docs/Quality-Judge.md.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.rag import guardrails

from .report_text import flatten_report

logger = logging.getLogger(__name__)

_JUDGE_MODEL = os.getenv("RAG_JUDGE_MODEL", "gpt-4o-mini")
_JUDGE_SAMPLES = max(1, int(os.getenv("RAG_JUDGE_SAMPLES", "1")))
_TIMEOUT_S = int(os.getenv("RAG_JUDGE_TIMEOUT", "30"))

_DIMENSIONS = ("accuracy", "citations", "clarity", "relevance", "neutrality")

_PROMPT_TEMPLATE = """You are a strict, senior financial-intelligence editor reviewing a \
research report before publication. Rate it honestly - do not be lenient.

Score five dimensions from 1 (very poor) to 5 (excellent):
- accuracy: are claims plausible, internally consistent, not misleading despite being technically correct
- citations: are sources present AND actually relevant/strong (not just present)
- clarity: is the writing precise, not vague or hedge-everything language
- relevance: is the content on-topic and timely, not stale or tangential
- neutrality: is the tone neutral and non-biased, no unsupported asserted motive

Then give an overall quality_score 1-5, a publishable boolean, and up to 5 \
concrete issues (short phrases, not full sentences).

REPORT DIGEST:
{digest}

Reply with ONLY compact JSON, no prose, in exactly this shape:
{{"quality_score": <1-5 float>, "publishable": <true|false>, \
"dimensions": {{"accuracy": <1-5>, "citations": <1-5>, "clarity": <1-5>, \
"relevance": <1-5>, "neutrality": <1-5>}}, "issues": [<string>, ...], \
"reasoning": <short string>}}"""


@dataclass
class JudgeVerdict:
    ok: bool = False
    score: Optional[float] = None          # normalized 0..1
    publishable: Optional[bool] = None
    dimensions: Dict[str, float] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    reasoning: str = ""
    model: str = _JUDGE_MODEL
    error: Optional[str] = None
    pre_screen_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok, "score": self.score, "publishable": self.publishable,
            "dimensions": self.dimensions, "issues": self.issues,
            "reasoning": self.reasoning, "model": self.model, "error": self.error,
            "pre_screen_flags": self.pre_screen_flags,
        }


def _extract_json(content: str) -> Optional[Dict[str, Any]]:
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _call_llm_once(digest: str, model: str) -> Dict[str, Any]:
    """One raw LLM call. Raises on any failure (caller handles fail-soft)."""
    import requests

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    prompt = _PROMPT_TEMPLATE.format(digest=digest)
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 500,
        },
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    parsed = _extract_json(content)
    if parsed is None:
        raise ValueError(f"judge response was not valid JSON: {content[:200]!r}")
    return parsed


def _normalize(parsed: Dict[str, Any], model: str) -> JudgeVerdict:
    raw_score = parsed.get("quality_score")
    score01: Optional[float] = None
    if isinstance(raw_score, (int, float)):
        score01 = round(max(0.0, min(1.0, (float(raw_score) - 1.0) / 4.0)), 4)

    dims_raw = parsed.get("dimensions") or {}
    dims: Dict[str, float] = {}
    for d in _DIMENSIONS:
        v = dims_raw.get(d)
        if isinstance(v, (int, float)):
            dims[d] = round(max(0.0, min(1.0, (float(v) - 1.0) / 4.0)), 4)

    issues = parsed.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]

    return JudgeVerdict(
        ok=True,
        score=score01,
        publishable=bool(parsed.get("publishable")) if "publishable" in parsed else None,
        dimensions=dims,
        issues=[str(i) for i in issues][:10],
        reasoning=str(parsed.get("reasoning", ""))[:1000],
        model=model,
    )


def judge_report(data: Dict[str, Any], *, model: Optional[str] = None) -> JudgeVerdict:
    """
    Score a report's `data` dict holistically via LLM-as-judge.

    Fail-soft contract: returns JudgeVerdict(ok=False, ...) on ANY failure (no
    API key, network error, malformed JSON) - never raises. Callers (decision.py)
    treat ok=False as "judge unavailable, fall back to rules".
    """
    model = model or _JUDGE_MODEL

    digest = flatten_report(data)
    if not digest.strip():
        return JudgeVerdict(ok=False, error="empty report digest", model=model)

    # Cheap pre-screen before spending a token call: banned-content check reuses
    # the same guardrail the RAG answer path uses. context_docs=[] skips the
    # grounding-overlap check (not meaningful for a report digest), keeping only
    # the banned-phrase screen.
    screen = guardrails.check_output(digest, [])
    pre_flags = list(screen.flags)

    if not os.getenv("OPENAI_API_KEY"):
        return JudgeVerdict(ok=False, error="OPENAI_API_KEY not configured", pre_screen_flags=pre_flags, model=model)

    samples: List[JudgeVerdict] = []
    last_error: Optional[str] = None
    for _ in range(_JUDGE_SAMPLES):
        try:
            parsed = _call_llm_once(digest, model)
            samples.append(_normalize(parsed, model))
        except Exception as exc:
            last_error = str(exc)
            logger.warning("quality judge call failed: %s", exc)

    if not samples:
        return JudgeVerdict(ok=False, error=last_error or "judge unavailable", pre_screen_flags=pre_flags, model=model)

    if len(samples) == 1:
        verdict = samples[0]
    else:
        # Self-consistency: average numeric fields, union issues, keep first reasoning.
        avg_score = round(sum(s.score for s in samples if s.score is not None) / len(samples), 4)
        avg_dims: Dict[str, float] = {}
        for d in _DIMENSIONS:
            vals = [s.dimensions.get(d) for s in samples if d in s.dimensions]
            if vals:
                avg_dims[d] = round(sum(vals) / len(vals), 4)
        all_issues = list({i for s in samples for i in s.issues})[:10]
        verdict = JudgeVerdict(
            ok=True, score=avg_score,
            publishable=sum(1 for s in samples if s.publishable) > len(samples) / 2,
            dimensions=avg_dims, issues=all_issues,
            reasoning=samples[0].reasoning, model=model,
        )

    verdict.pre_screen_flags = pre_flags
    if pre_flags:
        # Banned content always wins regardless of the LLM's own score.
        verdict.publishable = False
    return verdict
