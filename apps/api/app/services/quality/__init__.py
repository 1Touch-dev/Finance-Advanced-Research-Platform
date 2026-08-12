"""
Quality decision layer for generated intelligence reports.

Two complementary judges, one final decision:
  - rules  (quality_gate_service.run_quality_gates): mechanical, explicit failure
    shapes (missing citations, stale news, placeholders, ...). Fast, free,
    deterministic. Cannot judge tone, relevance, or subtle misleading framing.
  - judge  (services/quality/judge.judge_report): LLM-as-judge holistic read
    (accuracy/citations/clarity/relevance/neutrality). Catches what rules can't;
    costs one token call; only as good as the prompt until calibrated by review.

Rules always retain hard-veto power — an LLM can never override a compliance
block. Every judge run is logged (services/quality/labels) so today's judgments
become tomorrow's training set for a future supervised classifier once enough
real labels accumulate.

See docs/Quality-Judge.md for the full architecture writeup.
"""
from .judge import JudgeVerdict, judge_report
from .decision import evaluate

__all__ = ["JudgeVerdict", "judge_report", "evaluate"]
