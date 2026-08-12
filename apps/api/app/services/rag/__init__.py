"""
services.rag — production-grade retrieval package.

Unifies both retrieval paths (report-claims and uploaded-doc-chunks) behind one
Retriever interface, with vector / keyword / hybrid modes, reranking, guardrails,
per-stage tracing, and an evaluation harness.

Everything fails soft: if embeddings are unavailable the pipeline degrades to
BM25/TF-IDF keyword retrieval so /chat/ask never hard-fails.
"""
from .types import Document, ScoredDoc, RetrievalMode

__all__ = ["Document", "ScoredDoc", "RetrievalMode"]
