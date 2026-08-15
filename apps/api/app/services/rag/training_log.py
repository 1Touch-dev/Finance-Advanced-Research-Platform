"""
RAG training data logger — captures query-retrieval pairs for embedding fine-tuning.

Logs to exports/rag_training_log.jsonl with:
  - query: the user's question
  - positive_chunks: docs retrieved and used in answer (high scores)
  - hard_negative_chunks: docs retrieved but lower scored (in pool, not top)
  - answer_length: response length (for filtering low-quality examples)
  - timestamp, entity, collection for provenance

Enable/disable via RAG_TRAINING_LOG_ENABLED env var (default: on).

Usage:
  from app.services.rag.training_log import log_retrieval_for_training
  log_retrieval_for_training(query, retrieved_docs, used_in_answer, answer)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import ScoredDoc

logger = logging.getLogger(__name__)

# Configuration
_LOG_ENABLED = os.getenv("RAG_TRAINING_LOG_ENABLED", "true").lower() in ("true", "1", "on")
_LOG_PATH = Path(os.getenv(
    "RAG_TRAINING_LOG_PATH",
    Path(__file__).parent.parent.parent.parent / "exports" / "rag_training_log.jsonl"
))
# Score threshold to separate "positive" from "hard negative"
_POSITIVE_THRESHOLD = float(os.getenv("RAG_TRAINING_POSITIVE_THRESHOLD", "0.6"))
# Maximum chunks to log per query to control file size
_MAX_CHUNKS_PER_QUERY = int(os.getenv("RAG_TRAINING_MAX_CHUNKS", "20"))


def log_retrieval_for_training(
    query: str,
    retrieved_docs: List[ScoredDoc],
    *,
    used_doc_ids: Optional[List[str]] = None,
    answer: Optional[str] = None,
    entity: str = "",
    collection: str = "",
    correlation_id: Optional[str] = None,
) -> bool:
    """
    Log a retrieval event for future embedding fine-tuning.

    Args:
        query: The user's natural language query
        retrieved_docs: All documents returned by the retriever (with scores)
        used_doc_ids: IDs of docs actually cited in the answer (if known)
        answer: The generated answer (for quality filtering)
        entity: Entity name for grouping
        collection: Collection identifier
        correlation_id: Request correlation ID

    Returns:
        True if logged successfully, False otherwise
    """
    if not _LOG_ENABLED:
        return False

    if not query or not query.strip():
        return False

    if not retrieved_docs:
        return False

    try:
        # Separate docs into positives and hard negatives based on score
        # If used_doc_ids provided, use that; otherwise use score threshold
        positive_chunks: List[Dict[str, Any]] = []
        hard_negative_chunks: List[Dict[str, Any]] = []

        for sd in retrieved_docs[:_MAX_CHUNKS_PER_QUERY]:
            chunk_data = {
                "id": sd.doc.id,
                "text": sd.doc.text[:1000],  # Truncate long texts
                "source": sd.doc.source,
                "score": round(sd.score, 4),
            }

            if used_doc_ids is not None:
                # Use explicit "used in answer" signal
                if sd.doc.id in used_doc_ids:
                    positive_chunks.append(chunk_data)
                else:
                    hard_negative_chunks.append(chunk_data)
            else:
                # Use score threshold
                if sd.score >= _POSITIVE_THRESHOLD:
                    positive_chunks.append(chunk_data)
                else:
                    hard_negative_chunks.append(chunk_data)

        # Skip if no positive examples (nothing useful for training)
        if not positive_chunks:
            return False

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query.strip()[:500],  # Truncate very long queries
            "positive_chunks": positive_chunks[:10],  # Max 10 positives
            "hard_negative_chunks": hard_negative_chunks[:10],  # Max 10 hard negatives
            "answer_length": len(answer) if answer else 0,
            "entity": entity,
            "collection": collection,
            "correlation_id": correlation_id,
            "num_retrieved": len(retrieved_docs),
        }

        # Ensure directory exists
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(_LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        return True

    except Exception as exc:
        logger.debug("RAG training log failed: %s", exc)
        return False


def get_log_stats() -> Dict[str, Any]:
    """
    Return statistics about the training log.
    """
    if not _LOG_PATH.exists():
        return {"exists": False, "entries": 0, "size_kb": 0}

    try:
        with open(_LOG_PATH) as f:
            entries = sum(1 for _ in f)

        size_kb = _LOG_PATH.stat().st_size / 1024

        return {
            "exists": True,
            "path": str(_LOG_PATH),
            "entries": entries,
            "size_kb": round(size_kb, 2),
        }
    except Exception as exc:
        return {"exists": True, "error": str(exc)}


def export_triplets_from_log(
    log_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> int:
    """
    Convert RAG training log entries to embedding triplets.

    For each entry:
      - anchor = query
      - positive = high-scoring chunk text
      - hard_negative = low-scoring chunk text

    Returns count of triplets generated.
    """
    log_path = log_path or _LOG_PATH
    output_path = output_path or (log_path.parent / "embedding_triplets_from_rag.jsonl")

    if not log_path.exists():
        return 0

    triplet_count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path) as f_in, open(output_path, "a") as f_out:
        for line in f_in:
            try:
                entry = json.loads(line)
                query = entry.get("query", "")
                positives = entry.get("positive_chunks", [])
                negatives = entry.get("hard_negative_chunks", [])

                if not query or not positives:
                    continue

                # Generate triplets
                for pos in positives:
                    for neg in negatives:
                        triplet = {
                            "anchor": query,
                            "positive": pos.get("text", ""),
                            "hard_negative": neg.get("text", ""),
                            "source": f"rag_log:{entry.get('entity', '')}:{entry.get('collection', '')}",
                            "entity": entry.get("entity", ""),
                            "triplet_type": "rag_query",
                        }
                        f_out.write(json.dumps(triplet) + "\n")
                        triplet_count += 1

            except Exception:
                continue

    return triplet_count
