"""
RAG evaluation harness.

Retrieval metrics (need a labeled set of relevant doc-ids per query):
  - hit@k, MRR, nDCG@k
Generation metrics (reference-light, so they run without gold answers):
  - grounding: fraction of answer tokens supported by retrieved context
  - citation_rate: answer contains [n] markers
  - guardrail_pass: output guardrail verdict

Also exposes a before/after comparator (keyword vs vector vs hybrid) used by the
CLI at scripts/rag_eval.py — the demo money-shot.
"""
from __future__ import annotations

import logging
import math
import os
import re
from typing import Callable, Dict, List, Optional

from .types import Document, RetrievalMode, ScoredDoc
from . import retriever

logger = logging.getLogger(__name__)


# ── retrieval metrics ─────────────────────────────────────────────────────────
def hit_at_k(ranked_ids: List[str], relevant: set, k: int) -> float:
    return 1.0 if any(i in relevant for i in ranked_ids[:k]) else 0.0


def mrr(ranked_ids: List[str], relevant: set) -> float:
    for rank, did in enumerate(ranked_ids, 1):
        if did in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked_ids: List[str], relevant: set, k: int) -> float:
    dcg = 0.0
    for i, did in enumerate(ranked_ids[:k]):
        if did in relevant:
            dcg += 1.0 / math.log2(i + 2)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return dcg / ideal if ideal > 0 else 0.0


def evaluate_retrieval(
    queries: List[Dict],
    docs: List[Document],
    mode: RetrievalMode,
    k: int = 5,
    use_rerank: bool = True,
) -> Dict[str, float]:
    """queries: [{ "query": str, "relevant_ids": [str, ...] }, ...]"""
    hits, mrrs, ndcgs = [], [], []
    for q in queries:
        relevant = set(q["relevant_ids"])
        scored = retriever.retrieve(q["query"], docs, mode=mode, top_k=k, use_rerank=use_rerank)
        ranked = [s.doc.id for s in scored]
        hits.append(hit_at_k(ranked, relevant, k))
        mrrs.append(mrr(ranked, relevant))
        ndcgs.append(ndcg_at_k(ranked, relevant, k))
    n = max(len(queries), 1)
    return {
        f"hit@{k}": round(sum(hits) / n, 4),
        "mrr": round(sum(mrrs) / n, 4),
        f"ndcg@{k}": round(sum(ndcgs) / n, 4),
        "n": len(queries),
    }


# ── generation metrics (reference-light) ────────────────────────────────────
def grounding_score(answer: str, context: List[ScoredDoc]) -> float:
    ctx = set(re.findall(r"\b[a-z0-9]{4,}\b", " ".join(d.doc.text.lower() for d in context)))
    ans = set(re.findall(r"\b[a-z0-9]{4,}\b", answer.lower()))
    if not ans:
        return 0.0
    return round(len(ctx & ans) / len(ans), 4)


def citation_rate(answer: str) -> float:
    return 1.0 if re.search(r"\[\d+\]", answer) else 0.0


# ── faithfulness (real entailment, not token-overlap) ─────────────────────────
_NLI_MODEL = os.getenv("RAG_NLI_MODEL", "cross-encoder/nli-deberta-v3-small")
_nli_cache = None


def _load_nli():
    global _nli_cache
    if _nli_cache is not None:
        return _nli_cache
    try:
        from sentence_transformers import CrossEncoder
        _nli_cache = CrossEncoder(_NLI_MODEL)
    except Exception as exc:  # lib/model unavailable
        logger.info("NLI model unavailable (%s); faithfulness via token-overlap", exc)
        _nli_cache = False
    return _nli_cache


def faithfulness_score(answer: str, context: List[ScoredDoc]) -> Dict[str, float]:
    """
    Does the retrieved context ENTAIL the answer? Splits the answer into sentence
    claims and, for each, takes the max entailment probability over context docs.
    Uses an NLI cross-encoder when available; degrades to grounding token-overlap.

    Returns {"faithfulness": 0..1, "method": "nli"|"overlap", "unsupported": n}.
    """
    if not answer.strip() or not context:
        return {"faithfulness": 0.0, "method": "none", "unsupported": 0}

    claims = [c.strip() for c in re.split(r"(?<=[.!?])\s+", answer) if len(c.strip()) > 8]
    if not claims:
        claims = [answer.strip()]
    ctx_texts = [d.doc.text for d in context]

    model = _load_nli()
    if not model:  # overlap fallback
        return {"faithfulness": grounding_score(answer, context), "method": "overlap", "unsupported": 0}

    try:
        import numpy as np
        # NLI label order for these models: [contradiction, entailment, neutral].
        supported = 0
        per_claim = []
        for claim in claims:
            pairs = [(ctx, claim) for ctx in ctx_texts]
            logits = np.asarray(model.predict(pairs))
            if logits.ndim == 1:  # some heads return a single score
                probs = 1.0 / (1.0 + np.exp(-logits))
                best = float(probs.max())
            else:
                ent = logits[:, 1]  # entailment column
                best = float(ent.max())
                # normalize to 0..1 via softmax on the winning row
                row = logits[int(np.argmax(ent))]
                e = np.exp(row - row.max())
                best = float((e / e.sum())[1])
            per_claim.append(best)
            if best >= 0.5:
                supported += 1
        return {
            "faithfulness": round(sum(per_claim) / len(per_claim), 4),
            "method": "nli",
            "unsupported": len(claims) - supported,
        }
    except Exception as exc:
        logger.warning("NLI faithfulness failed (%s); overlap fallback", exc)
        return {"faithfulness": grounding_score(answer, context), "method": "overlap", "unsupported": 0}


def llm_judge_faithfulness(answer: str, context: List[ScoredDoc]) -> Optional[Dict]:
    """
    Optional LLM-as-judge faithfulness (0..1) + rationale. Returns None if no
    OPENAI_API_KEY (so callers can skip). Kept separate from the NLI path because
    it costs a token call per eval item.
    """
    import os as _os
    if not _os.getenv("OPENAI_API_KEY"):
        return None
    try:
        import json as _json
        import requests as _req
        ctx = "\n".join(f"- {d.doc.text}" for d in context[:8])
        prompt = (
            "You are a strict fact-checker. Given CONTEXT and an ANSWER, rate how "
            "fully the ANSWER is supported by the CONTEXT on a 0.0-1.0 scale. "
            "Reply as compact JSON: {\"faithfulness\": float, \"reason\": str}.\n\n"
            f"CONTEXT:\n{ctx}\n\nANSWER:\n{answer}"
        )
        resp = _req.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {_os.getenv('OPENAI_API_KEY')}", "Content-Type": "application/json"},
            json={"model": _os.getenv("RAG_JUDGE_MODEL", "gpt-4o-mini"),
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.0, "max_tokens": 200},
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", content, re.DOTALL)
        return _json.loads(m.group(0)) if m else {"faithfulness": None, "reason": content}
    except Exception as exc:
        logger.warning("LLM judge failed: %s", exc)
        return None


# ── before/after comparator ──────────────────────────────────────────────────
def compare_modes(
    query: str,
    docs: List[Document],
    k: int = 5,
    modes: Optional[List[RetrievalMode]] = None,
) -> Dict[str, List[Dict]]:
    modes = modes or [RetrievalMode.KEYWORD, RetrievalMode.VECTOR, RetrievalMode.HYBRID]
    out: Dict[str, List[Dict]] = {}
    for m in modes:
        scored = retriever.retrieve(query, docs, mode=m, top_k=k, use_rerank=(m != RetrievalMode.KEYWORD))
        out[m.value] = [
            {"id": s.doc.id, "score": round(s.score, 4), "text": s.doc.text[:120]}
            for s in scored
        ]
    return out
