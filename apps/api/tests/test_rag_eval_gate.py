"""
CI gate on retrieval quality — fails the build if hit@k/MRR drops below a floor
on a fixed, offline labeled eval set (apps/api/tests/data/rag_eval_set.jsonl).

The set is intentionally larger (20 docs / 19 queries) than the smoke-test corpus
in test_rag_vector.py, covering the heterogeneous topics a real report spans
(13F, insider trades, contracts, litigation, proxy, news, financials). Runs fully
offline: keyword mode needs no embeddings; vector/hybrid use a deterministic
mocked embedder so the gate never depends on network or OpenAI credits.
"""
import json
from pathlib import Path

import numpy as np
import pytest

from app.services.rag import embeddings, eval as rag_eval
from app.services.rag.types import Document, RetrievalMode

_DATA_PATH = Path(__file__).parent / "data" / "rag_eval_set.jsonl"

# Floors: chosen below the measured baseline so the gate only trips on a real
# regression, not on noise. Tune upward once the eval set grows.
_KEYWORD_HIT_AT_5_FLOOR = 0.60
_KEYWORD_MRR_FLOOR = 0.55
_HYBRID_HIT_AT_5_FLOOR = 0.60
_HYBRID_MRR_FLOOR = 0.55


def _load_eval_set():
    docs, queries = [], []
    with open(_DATA_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row["kind"] == "doc":
                docs.append(Document(id=row["id"], text=row["text"]))
            elif row["kind"] == "query":
                queries.append({"query": row["query"], "relevant_ids": row["relevant_ids"]})
    return docs, queries


@pytest.fixture
def mock_embeddings(monkeypatch):
    """Same deterministic bag-of-chars embedder used in test_rag_vector.py, so
    the vector/hybrid gate is offline and reproducible."""
    dim = 32

    def _vec(text: str) -> list:
        v = np.zeros(dim, dtype=np.float32)
        for ch in text.lower():
            v[ord(ch) % dim] += 1.0
        n = np.linalg.norm(v) or 1.0
        return (v / n).tolist()

    def fake_embed_texts(texts, use_cache=True):
        if not texts:
            return np.zeros((0, dim), dtype=np.float32)
        return np.array([_vec(t) for t in texts], dtype=np.float32)

    def fake_embed_query(text):
        return np.array(_vec(text), dtype=np.float32)

    monkeypatch.setattr(embeddings, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(embeddings, "embed_query", fake_embed_query)
    monkeypatch.setattr(embeddings, "model_dim", lambda: dim)
    import app.services.rag.vector_store as vs
    monkeypatch.setattr(vs.embeddings, "embed_texts", fake_embed_texts)
    monkeypatch.setattr(vs.embeddings, "embed_query", fake_embed_query)


def test_eval_set_is_well_formed():
    docs, queries = _load_eval_set()
    assert 15 <= len(docs) <= 25, "eval corpus should stay in the intended N~15-25 range"
    assert 15 <= len(queries) <= 25
    doc_ids = {d.id for d in docs}
    for q in queries:
        assert q["relevant_ids"], f"query has no relevant_ids: {q['query']!r}"
        assert set(q["relevant_ids"]) <= doc_ids, f"dangling relevant_id in query: {q['query']!r}"


def test_keyword_retrieval_meets_floor():
    """Pure BM25/TF-IDF gate — no embeddings involved, always runs in CI."""
    docs, queries = _load_eval_set()
    metrics = rag_eval.evaluate_retrieval(queries, docs, mode=RetrievalMode.KEYWORD, k=5, use_rerank=False)
    assert metrics["hit@5"] >= _KEYWORD_HIT_AT_5_FLOOR, metrics
    assert metrics["mrr"] >= _KEYWORD_MRR_FLOOR, metrics


def test_hybrid_retrieval_meets_floor(mock_embeddings):
    """Dense+sparse fusion gate with a deterministic mocked embedder."""
    docs, queries = _load_eval_set()
    metrics = rag_eval.evaluate_retrieval(queries, docs, mode=RetrievalMode.HYBRID, k=5, use_rerank=False)
    assert metrics["hit@5"] >= _HYBRID_HIT_AT_5_FLOOR, metrics
    assert metrics["mrr"] >= _HYBRID_MRR_FLOOR, metrics


def test_hybrid_does_not_regress_below_keyword_by_much(mock_embeddings):
    """Sanity check: fusing in a (mocked, noisy) dense signal shouldn't tank
    quality relative to keyword-only on this labeled set."""
    docs, queries = _load_eval_set()
    kw = rag_eval.evaluate_retrieval(queries, docs, mode=RetrievalMode.KEYWORD, k=5, use_rerank=False)
    hy = rag_eval.evaluate_retrieval(queries, docs, mode=RetrievalMode.HYBRID, k=5, use_rerank=False)
    assert hy["hit@5"] >= kw["hit@5"] - 0.15
