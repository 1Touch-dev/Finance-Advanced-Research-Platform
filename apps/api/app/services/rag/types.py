"""Shared types for the RAG package."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RetrievalMode(str, Enum):
    VECTOR = "vector"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass
class Document:
    """A retrievable unit — a report claim OR a document chunk."""
    id: str
    text: str
    source: str = ""
    confidence: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_source(self) -> Dict[str, Any]:
        """Shape expected by existing rag_chat / documents API responses."""
        out = {"text": self.text, "source": self.source, "confidence": self.confidence}
        out.update(self.metadata)
        return out


@dataclass
class ScoredDoc:
    doc: Document
    score: float
    # component scores for debugging/eval (bm25, dense, rerank, fused ranks...)
    components: Dict[str, float] = field(default_factory=dict)
