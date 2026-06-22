"""
Per-entity RAG (Retrieval-Augmented Generation) chat service.

Allows users to ask natural-language questions about an entity, answered with
cited evidence drawn from that entity's intelligence report sections.

Architecture:
  1. Retrieve   — gather all claims for the entity from its latest report
  2. Rank        — simple TF-IDF keyword ranking (no pgvector needed; pure Python)
  3. Answer      — call OpenAI gpt-4o-mini with the top-k retrieved claims as context
  4. Cite        — return answer with source citations embedded

pgvector / embeddings upgrade path:
  - When pgvector is available, swap _rank_claims() for an embedding-similarity search.
  - The rest of the interface stays identical.
"""
import os
import re
import json
import logging
import requests as _req
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

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
    Rank claims by keyword overlap with the query.
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
) -> Dict[str, Any]:
    """
    Answer a natural-language question about an entity using its report as context.

    Args:
        question:     User's question string.
        report:       Full intelligence report dict (with sections and claims). Can be None.
        chat_history: Optional list of { role, content } for multi-turn conversation.
        entity_name:  Fallback entity name if no report provided.

    Returns:
        {
          "answer":  str,
          "sources": [{ "text": ..., "source": ..., "confidence": ... }],
          "context_used": int,  # number of claims in context
        }
    """
    resolved_entity = entity_name or (report.get('entity_name') if report else None) or 'this entity'

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

    # Retrieve relevant claims
    top_claims = _rank_claims(question, all_claims)
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

    return {
        "answer":       answer,
        "sources":      top_claims,
        "context_used": len(top_claims),
        "entity_name":  resolved_entity,
    }


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
