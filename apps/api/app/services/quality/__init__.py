"""
Quality decision layer for generated intelligence reports.

Three complementary judges, one final decision:
  - rules  (quality_gate_service.run_quality_gates): mechanical, explicit failure
    shapes (missing citations, stale news, placeholders, ...). Fast, free,
    deterministic. Cannot judge tone, relevance, or subtle misleading framing.
  - judge  (services/quality/judge.judge_report): LLM-as-judge holistic read
    (accuracy/citations/clarity/relevance/neutrality). Catches what rules can't;
    costs one token call; only as good as the prompt until calibrated by review.
  - classifier (services/quality/classifier.classify, mode="ml"): supervised
    model trained on rule_features -> judge_publishable (see
    app/scripts/train_quality_classifier.py). No LLM call, near-zero cost;
    intentionally refuses to train below a label-volume floor rather than
    ship a model that's just memorizing noise on a handful of examples.

Rules always retain hard-veto power — an LLM (or the classifier) can never
override a compliance block. Every judge run is logged
(services/quality/labels) so today's judgments become tomorrow's training set
for the classifier above.

See docs/Quality-Judge.md for the full architecture writeup.
"""
from .classifier import ClassifierVerdict, classify
from .judge import JudgeVerdict, judge_report
from .decision import evaluate

__all__ = ["JudgeVerdict", "judge_report", "ClassifierVerdict", "classify", "evaluate"]
