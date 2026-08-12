"""
Hybrid search — fuse BM25 (sparse) and dense vector rankings via Reciprocal
Rank Fusion (RRF).

RRF is used instead of score-normalization because BM25 and cosine live on
different scales; RRF only needs the *rank* of each doc in each list, so it is
robust and parameter-light. score = sum over lists of 1/(k + rank).
"""
from __future__ import annotations

import os
from typing import Dict, List

from .types import Document, ScoredDoc

_RRF_K = int(os.getenv("RAG_RRF_K", "60"))


def reciprocal_rank_fusion(
    dense: List[ScoredDoc],
    sparse: List[ScoredDoc],
    top_k: int = 12,
    k: int = _RRF_K,
) -> List[ScoredDoc]:
    fused: Dict[str, ScoredDoc] = {}

    def _add(results: List[ScoredDoc], label: str) -> None:
        for rank, sd in enumerate(results):
            did = sd.doc.id
            contrib = 1.0 / (k + rank + 1)
            if did not in fused:
                fused[did] = ScoredDoc(sd.doc, 0.0, {})
            fused[did].score += contrib
            fused[did].components[f"{label}_rank"] = rank + 1
            fused[did].components.update(sd.components)

    _add(dense, "dense")
    _add(sparse, "sparse")

    out = sorted(fused.values(), key=lambda s: -s.score)
    return out[:top_k]
