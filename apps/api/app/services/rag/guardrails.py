"""
RAG guardrails — input, retrieval, and output safety layers.

Financial-intelligence product rules (see Feature-Roadmap Band A #9): no
projections, no investment recommendations, disclaimers, and every answer must be
grounded in retrieved evidence.

All guardrails are pure functions returning verdicts; the pipeline decides what to
do with them (block, warn, or annotate).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List

from .types import ScoredDoc

# Retrieval floor: below this top-score, we treat context as "insufficient
# evidence" rather than forcing a weak/hallucinated answer.
_MIN_SCORE = float(os.getenv("RAG_MIN_RETRIEVAL_SCORE", "0.15"))

# Crude prompt-injection screen on the incoming query.
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|the\s+)?(previous|above|prior)?\s*instructions",
    r"disregard\s+(all\s+|the\s+)?(previous|your)?\s*(instructions|rules)",
    r"you are now",
    r"system prompt",
    r"reveal your (prompt|instructions)",
]

# Output content the product must not emit (no advice / projections).
# Note: answers are lowercased before matching, so patterns are lowercase.
_BANNED_OUTPUT = [
    r"\bi recommend (buying|selling|shorting)\b",
    r"\byou should (buy|sell|short)\b",
    r"\bguaranteed returns?\b",
    r"\bwill (definitely|certainly) (rise|fall|increase|drop)\b",
]


@dataclass
class Verdict:
    ok: bool = True
    flags: List[str] = field(default_factory=list)
    note: str = ""


def screen_query(query: str) -> Verdict:
    v = Verdict()
    low = query.lower()
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, low):
            v.ok = False
            v.flags.append("prompt_injection")
            v.note = "Query rejected: possible prompt-injection attempt."
            break
    return v


def check_retrieval(results: List[ScoredDoc]) -> Verdict:
    v = Verdict()
    if not results:
        v.ok = False
        v.flags.append("no_evidence")
        v.note = "No relevant evidence retrieved."
        return v
    top = max(r.score for r in results)
    if top < _MIN_SCORE:
        v.ok = False
        v.flags.append("weak_evidence")
        v.note = f"Top retrieval score {top:.3f} below floor {_MIN_SCORE}; insufficient evidence."
    return v


def check_output(answer: str, context_docs: List[ScoredDoc]) -> Verdict:
    """Grounding + banned-content check on the generated answer."""
    v = Verdict()
    low = answer.lower()
    for pat in _BANNED_OUTPUT:
        if re.search(pat, low):
            v.ok = False
            v.flags.append("investment_advice")
            v.note = "Answer contained prohibited investment advice/projection."
            return v
    # Grounding: at least one citation marker OR token overlap with context.
    if context_docs and not re.search(r"\[\d+\]", answer):
        ctx_tokens = set(re.findall(r"\b[a-z0-9]{4,}\b", " ".join(d.doc.text.lower() for d in context_docs)))
        ans_tokens = set(re.findall(r"\b[a-z0-9]{4,}\b", low))
        if ctx_tokens and len(ctx_tokens & ans_tokens) / max(len(ans_tokens), 1) < 0.05:
            v.flags.append("low_grounding")
            v.note = "Answer shows low overlap with retrieved evidence."
    return v
