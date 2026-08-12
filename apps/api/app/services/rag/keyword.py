"""
Keyword retrieval — BM25 (rank_bm25) with a pure-Python TF-IDF fallback.

This is both the `keyword` mode AND the always-available fallback when embeddings
are unavailable, so it must never require external services.
"""
from __future__ import annotations

import logging
import re
from typing import List

from .types import Document, ScoredDoc

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"\b[a-z0-9]{2,}\b")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _tfidf_fallback(query: str, docs: List[Document], top_k: int) -> List[ScoredDoc]:
    """Pure-Python overlap ranking — mirrors the legacy rag_chat _tfidf_score."""
    q = set(_tokenize(query))
    scored: List[ScoredDoc] = []
    for d in docs:
        toks = _tokenize(d.text)
        if not toks:
            continue
        overlap = len(q & set(toks))
        if overlap:
            score = overlap / (len(set(toks)) ** 0.5 + len(q) ** 0.5)
            scored.append(ScoredDoc(d, float(score), {"tfidf": float(score)}))
    scored.sort(key=lambda s: -s.score)
    return scored[:top_k]


def keyword_search(query: str, docs: List[Document], top_k: int = 12) -> List[ScoredDoc]:
    if not docs:
        return []
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.info("rank_bm25 unavailable; using TF-IDF fallback")
        return _tfidf_fallback(query, docs, top_k)

    corpus = [_tokenize(d.text) for d in docs]
    if not any(corpus):
        return _tfidf_fallback(query, docs, top_k)
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query))
    ranked = sorted(range(len(docs)), key=lambda i: -scores[i])[:top_k]
    out = []
    for i in ranked:
        if scores[i] <= 0:
            continue
        out.append(ScoredDoc(docs[i], float(scores[i]), {"bm25": float(scores[i])}))
    return out
