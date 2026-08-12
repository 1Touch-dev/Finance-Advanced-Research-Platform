"""
Per-entity RAG (Retrieval-Augmented Generation) chat service.

Allows users to ask natural-language questions about an entity, answered with
cited evidence drawn from that entity's intelligence report sections.

Architecture:
  1. Retrieve   — gather all claims for the entity from its latest report
  2. Rank        — services.rag unified retriever (vector / keyword / hybrid + rerank);
                    degrades to pure-Python TF-IDF when embeddings are unavailable
  3. Answer      — call OpenAI gpt-4o-mini with the top-k retrieved claims as context
  4. Cite        — return answer with source citations embedded

The ranking is delegated to app.services.rag so both the report-Q&A path and the
uploaded-document path share one retrieval engine. The legacy _rank_claims below is
kept as an in-module fallback and for tests.
"""
import os
import re
import json
import logging
import requests as _req
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Unified retrieval engine (vector/keyword/hybrid + rerank + guardrails + trace).
try:
    from app.services.rag import retriever as _rag_retriever, guardrails as _rag_guardrails
    from app.services.rag.trace import Trace as _RagTrace
    from app.services.rag.types import Document as _RagDoc, RetrievalMode as _RagMode
    _RAG_ENGINE_OK = True
except Exception as _exc:  # pragma: no cover - never break chat on import error
    logger.warning("rag engine import failed, using legacy TF-IDF: %s", _exc)
    _RAG_ENGINE_OK = False

_OPENAI_KEY  = os.getenv("OPENAI_API_KEY", "")
_OPENAI_BASE = "https://api.openai.com/v1/chat/completions"
_MODEL       = "gpt-4o-mini"
_TOP_K       = 12  # Number of claims to include in context


# ── Simple keyword retrieval (no external dependencies) ───────────────────────

def _tokenize(text: str) -> set:
    return set(re.findall(r'\b[a-z]{3,}\b', text.lower()))


def _tfidf_score(query_tokens: set, claim_text: str) -> float:
    claim_tokens = _tokenize(claim_text)
    overlap = query_tokens & claim_tokens
    if not claim_tokens:
        return 0.0
    return len(overlap) / (len(claim_tokens) ** 0.5 + len(query_tokens) ** 0.5)


def _rank_claims(query: str, all_claims: List[Dict]) -> List[Dict]:
    """
    Legacy pure-Python keyword ranking (fallback / tests).
    Returns up to _TOP_K most relevant claims.
    """
    q_tokens = _tokenize(query)
    scored = []
    for claim in all_claims:
        text = claim.get('text') or str(claim) or ''
        score = _tfidf_score(q_tokens, text)
        if score > 0:
            scored.append((score, claim))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:_TOP_K]]


def _claims_to_docs(all_claims: List[Dict]) -> List["_RagDoc"]:
    docs = []
    for i, claim in enumerate(all_claims):
        text = (claim.get('text') or str(claim) or '').strip()
        if not text:
            continue
        docs.append(_RagDoc(
            id=str(i),
            text=text,
            source=claim.get('source', ''),
            confidence=claim.get('confidence', ''),
            metadata={k: v for k, v in claim.items() if k not in ("text", "source", "confidence")},
        ))
    return docs


def _retrieve_claims(
    query: str,
    all_claims: List[Dict],
    mode: str = "hybrid",
    trace=None,
    collection: str = "report:default",
) -> List[Dict]:
    """
    Engine-backed retrieval → list of claim dicts (same shape the rest of the
    module expects). Falls back to legacy TF-IDF if the engine is unavailable or
    errors, so /chat/ask never hard-fails.
    """
    if not _RAG_ENGINE_OK:
        return _rank_claims(query, all_claims)
    try:
        docs = _claims_to_docs(all_claims)
        try:
            rmode = _RagMode(mode)
        except ValueError:
            rmode = _RagMode.HYBRID
        scored = _rag_retriever.retrieve(query, docs, mode=rmode, top_k=_TOP_K,
                                         trace=trace, collection=collection)
        out = []
        for sd in scored:
            claim = dict(sd.doc.metadata)
            claim.update({"text": sd.doc.text, "source": sd.doc.source,
                          "confidence": sd.doc.confidence, "_score": round(sd.score, 4)})
            out.append(claim)
        return out
    except Exception as exc:
        logger.warning("rag engine retrieval failed (%s); legacy TF-IDF fallback", exc)
        return _rank_claims(query, all_claims)


# ── Context builder ───────────────────────────────────────────────────────────

def _build_context(claims: List[Dict]) -> str:
    lines = []
    for i, claim in enumerate(claims, 1):
        text = (claim.get('text') or str(claim)).strip()
        src  = claim.get('source', '')
        conf = claim.get('confidence', '')
        lines.append(f"[{i}] {text}")
        if src or conf:
            lines.append(f"    Source: {src}  Confidence: {conf}")
    return "\n".join(lines)


# ── OpenAI call ───────────────────────────────────────────────────────────────

def _call_openai(messages: List[Dict]) -> str:
    if not _OPENAI_KEY:
        return "[RAG unavailable — OPENAI_API_KEY not configured]"
    try:
        resp = _req.post(
            _OPENAI_BASE,
            headers={
                "Authorization": f"Bearer {_OPENAI_KEY}",
                "Content-Type":  "application/json",
            },
            json={"model": _MODEL, "messages": messages, "temperature": 0.2, "max_tokens": 800},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("RAG OpenAI call failed: %s", exc)
        return f"[AI answer unavailable: {exc}]"


# ── Public API ────────────────────────────────────────────────────────────────

def answer_question(
    question: str,
    report: Optional[Dict[str, Any]],
    chat_history: Optional[List[Dict]] = None,
    entity_name: Optional[str] = None,
    mode: str = "hybrid",
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Answer a natural-language question about an entity using its report as context.

    Args:
        question:     User's question string.
        report:       Full intelligence report dict (with sections and claims). Can be None.
        chat_history: Optional list of { role, content } for multi-turn conversation.
        entity_name:  Fallback entity name if no report provided.
        mode:         Retrieval mode — "vector" | "keyword" | "hybrid" (default).
        debug:        If True, attach a per-stage retrieval trace + guardrail flags.

    Returns:
        {
          "answer":  str,
          "sources": [{ "text": ..., "source": ..., "confidence": ... }],
          "context_used": int,  # number of claims in context
          "trace": {...}        # only when debug=True
        }
    """
    resolved_entity = entity_name or (report.get('entity_name') if report else None) or 'this entity'

    trace = _RagTrace(enabled=debug) if _RAG_ENGINE_OK else None

    # ── Input guardrail: reject prompt-injection before doing any work ──────────
    if _RAG_ENGINE_OK:
        gv = _rag_guardrails.screen_query(question)
        if trace:
            trace.stage("guardrail_input", ok=gv.ok, flags=gv.flags)
        if not gv.ok:
            return {
                "answer": "This question could not be processed for safety reasons.",
                "sources": [], "context_used": 0, "entity_name": resolved_entity,
                "guardrail": gv.note,
                **({"trace": trace.as_dict()} if trace else {}),
            }

    # Flatten all claims from all sections
    all_claims = []
    if report:
        for sec in (report.get('sections') or []):
            for claim in (sec.get('claims') or []):
                if isinstance(claim, dict):
                    all_claims.append(claim)
                elif isinstance(claim, str):
                    all_claims.append({"text": claim, "source": sec.get("name",""), "confidence": ""})

    if not all_claims:
        # No report — answer from general knowledge with a disclaimer
        if not _OPENAI_KEY:
            return {
                "answer":       f"No intelligence report generated yet for {resolved_entity}. Generate a report first to enable cited Q&A.",
                "sources":      [],
                "context_used": 0,
            }
        # Use OpenAI general knowledge as fallback
        fallback_messages = [
            {"role": "system", "content": f"You are an expert intelligence analyst. The user is asking about {resolved_entity}. No specific database report is available — answer from general knowledge and be transparent about that."},
        ]
        for turn in (chat_history or [])[-4:]:
            fallback_messages.append({"role": turn["role"], "content": turn["content"]})
        fallback_messages.append({"role": "user", "content": question})
        answer_text = _call_openai(fallback_messages)
        return {
            "answer":       answer_text,
            "sources":      [],
            "context_used": 0,
            "note":         "No report data — answered from general knowledge. Generate a report for cited evidence.",
        }

    # Retrieve relevant claims (engine: vector/keyword/hybrid + rerank; TF-IDF fallback)
    top_claims = _retrieve_claims(
        question, all_claims, mode=mode, trace=trace,
        collection=f"report:{report.get('id') or report.get('report_id') or resolved_entity}",
    )
    if not top_claims:
        top_claims = all_claims[:_TOP_K]

    context = _build_context(top_claims)

    system_prompt = (
        f"You are an expert intelligence analyst answering questions about {resolved_entity}. "
        "You have access to cited evidence from government databases, public filings, news, and commercial data. "
        "Answer the user's question based ONLY on the evidence provided. "
        "Cite your sources by referencing the claim number [1], [2], etc. "
        "If the evidence does not contain a clear answer, say so honestly. "
        "Keep your answer concise (3-6 sentences) and factual."
    )

    messages = [{"role": "system", "content": system_prompt}]

    # Add chat history (last 4 turns)
    for turn in (chat_history or [])[-4:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    user_message = (
        f"Evidence about {resolved_entity}:\n\n{context}\n\n"
        f"Question: {question}"
    )
    messages.append({"role": "user", "content": user_message})

    answer = _call_openai(messages)

    result = {
        "answer":       answer,
        "sources":      top_claims,
        "context_used": len(top_claims),
        "entity_name":  resolved_entity,
        "mode":         mode,
    }

    # ── Output guardrail: no investment advice / grounding check ────────────────
    if _RAG_ENGINE_OK:
        try:
            ctx_docs = _rag_retriever.retrieve  # noqa: F841 (keep import warm)
            from app.services.rag.types import Document as _D, ScoredDoc as _S
            ctx = [_S(_D(id=str(i), text=c.get("text", "")), 1.0) for i, c in enumerate(top_claims)]
            ov = _rag_guardrails.check_output(answer, ctx)
            if not ov.ok:
                result["answer"] = (
                    "The generated answer was withheld because it violated content "
                    "policy (no investment advice or projections)."
                )
            if ov.flags:
                result["guardrail_flags"] = ov.flags
        except Exception as exc:  # never break the response on guardrail error
            logger.debug("output guardrail error: %s", exc)

    if trace and trace.enabled:
        result["trace"] = trace.as_dict()

    return result


def build_entity_summary(report: Dict[str, Any]) -> str:
    """
    Generate a short 3-sentence executive summary for an entity using its report.
    """
    entity_name = report.get('entity_name') or 'this entity'
    all_claims = []
    for sec in (report.get('sections') or [])[:5]:
        for claim in (sec.get('claims') or [])[:3]:
            text = (claim.get('text') if isinstance(claim, dict) else str(claim)) or ''
            if text:
                all_claims.append(text[:300])

    context = "\n".join(all_claims[:15])
    if not context:
        return f"No data available for {entity_name}."

    messages = [
        {"role": "system", "content": "You are a senior intelligence analyst. Write a 3-sentence executive summary."},
        {"role": "user", "content": f"Summarize {entity_name} based on this evidence:\n\n{context}"},
    ]
    return _call_openai(messages)
