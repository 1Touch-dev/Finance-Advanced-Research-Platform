"""
RAG embeddings — provider-agnostic, batched, disk-cached, resilient.

Design:
  - PRIMARY: Fine-tuned finance-embed-v1 model (if available locally).
    This model was trained on 7,198 financial triplets and achieves +8.5%
    ranking accuracy over the base model.
  - FALLBACK 1: OpenAI text-embedding-3-small (cheap, 1536-d).
  - FALLBACK 2: Local model tier (sentence-transformers, e.g. bge/nomic).
  - FALLBACK 3: If ALL are unavailable → raise EmbeddingUnavailable, and callers
    fall back to keyword/TF-IDF retrieval.

  Disk cache keyed by (model, sha1(text)) so we never pay to re-embed the same
  chunk twice across ingest + eval runs.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

_MODEL = os.getenv("RAG_EMBED_MODEL", "text-embedding-3-small")
_CACHE_DIR = Path(os.getenv("EXPORT_DIR", "exports")) / "rag_index" / "embed_cache"
_BATCH = int(os.getenv("RAG_EMBED_BATCH", "128"))
# Optional local fallback model (CPU-ok). Empty = disabled.
_LOCAL_MODEL = os.getenv("RAG_LOCAL_EMBED_MODEL", "")
_RETRY_ATTEMPTS = int(os.getenv("RAG_EMBED_RETRIES", "3"))

# Fine-tuned model path — auto-detect common locations if not set
_FINETUNE_MODEL_PATH = os.getenv("RAG_FINETUNE_MODEL_PATH", "")
_USE_FINETUNED = os.getenv("RAG_USE_FINETUNED", "true").lower() in ("true", "1", "yes")

# Known embedding dimensions, used to size fallback zero-vectors coherently.
_MODEL_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "finance-embed-v1": 768,  # nomic-embed-text-v1.5 base
}


class EmbeddingUnavailable(RuntimeError):
    """Raised when embeddings cannot be produced (no key / provider error)."""


def model_name() -> str:
    return _MODEL


def provider_name() -> str:
    """Which embedding tier is configured (for /health/rag)."""
    # Check if fine-tuned model is available
    if _USE_FINETUNED:
        path = _find_finetuned_model_path()
        if path:
            return "finetuned:finance-embed-v1"
    if _MODEL.startswith("text-embedding-"):
        return f"openai:{_MODEL}"
    if _LOCAL_MODEL:
        return f"local:{_LOCAL_MODEL}"
    return _MODEL


def model_dim() -> int:
    """Return embedding dimension based on active model."""
    # Check if fine-tuned model will be used
    if _USE_FINETUNED and _find_finetuned_model_path():
        return 768  # nomic-embed-text-v1.5 dimension
    return _MODEL_DIMS.get(_MODEL, 1536)


def _cache_path(text: str) -> Path:
    h = hashlib.sha1(f"{_MODEL}::{text}".encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{h}.json"


def _read_cache(text: str) -> Optional[List[float]]:
    p = _cache_path(text)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def _write_cache(text: str, vec: List[float]) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(text).write_text(json.dumps(vec))
    except Exception as exc:  # cache is best-effort
        logger.debug("embed cache write failed: %s", exc)


def _client():
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise EmbeddingUnavailable("OPENAI_API_KEY not configured")
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise EmbeddingUnavailable(f"openai package missing: {exc}")
    return OpenAI(api_key=key)


def _embed_openai_batch(batch_texts: List[str]) -> List[List[float]]:
    """One OpenAI batch call, retried with exponential backoff on transient errors."""
    client = _client()  # raises EmbeddingUnavailable if no key/pkg

    def _call():
        resp = client.embeddings.create(model=_MODEL, input=batch_texts)
        return [item.embedding for item in resp.data]

    try:
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    except ImportError:
        return _call()  # tenacity missing → single attempt

    # Retry only transient network/rate errors; a hard 401 fails fast.
    retryer = retry(
        reraise=True,
        stop=stop_after_attempt(_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    )
    return retryer(_call)()


_local_model_cache = None
_finetuned_model_cache = None
_finetuned_model_path_resolved = None


def _find_finetuned_model_path() -> Optional[str]:
    """Auto-detect fine-tuned model path from common locations."""
    global _finetuned_model_path_resolved
    if _finetuned_model_path_resolved is not None:
        return _finetuned_model_path_resolved if _finetuned_model_path_resolved else None

    # Check explicit env var first
    if _FINETUNE_MODEL_PATH and Path(_FINETUNE_MODEL_PATH).exists():
        _finetuned_model_path_resolved = _FINETUNE_MODEL_PATH
        return _finetuned_model_path_resolved

    # Common locations to check
    candidates = [
        # EC2 server
        Path("/home/ubuntu/Finance-Advanced-Research-Platform/models/finance-embed-v1"),
        # Mac local dev
        Path.home() / "Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/embedding-model-fine-tuning/finance-embed-v1",
        # Relative to project root
        Path(__file__).parent.parent.parent.parent.parent.parent / "models" / "finance-embed-v1",
        Path(__file__).parent.parent.parent.parent.parent.parent / "embedding-model-fine-tuning" / "finance-embed-v1",
    ]

    for p in candidates:
        if p.exists() and (p / "model.safetensors").exists():
            _finetuned_model_path_resolved = str(p)
            logger.info("Fine-tuned model auto-detected at: %s", _finetuned_model_path_resolved)
            return _finetuned_model_path_resolved

    _finetuned_model_path_resolved = ""  # Mark as "not found"
    return None


def _embed_finetuned(texts: List[str]) -> Optional[np.ndarray]:
    """
    Embed using fine-tuned finance-embed-v1 model.
    Returns normalized (n, dim) array or None if unavailable.
    """
    global _finetuned_model_cache

    if not _USE_FINETUNED:
        return None

    model_path = _find_finetuned_model_path()
    if not model_path:
        return None

    try:
        from sentence_transformers import SentenceTransformer

        if _finetuned_model_cache is None:
            logger.info("Loading fine-tuned model from: %s", model_path)
            _finetuned_model_cache = SentenceTransformer(model_path, trust_remote_code=True)
            logger.info("Fine-tuned model loaded successfully (dim=%d)", _finetuned_model_cache.get_embedding_dimension())

        arr = np.asarray(
            _finetuned_model_cache.encode(texts, normalize_embeddings=True, show_progress_bar=False),
            dtype=np.float32,
        )
        return arr
    except Exception as exc:
        logger.warning("Fine-tuned model embedding failed: %s", exc)
        return None


def _embed_local(texts: List[str]) -> Optional[np.ndarray]:
    """Local sentence-transformers tier. Returns normalized (n, dim) or None."""
    global _local_model_cache
    if not _LOCAL_MODEL:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        if _local_model_cache is None:
            _local_model_cache = SentenceTransformer(_LOCAL_MODEL)
        arr = np.asarray(
            _local_model_cache.encode(texts, normalize_embeddings=True),
            dtype=np.float32,
        )
        return arr
    except Exception as exc:
        logger.warning("local embed tier failed (%s)", exc)
        return None


def embed_texts(texts: List[str], *, use_cache: bool = True) -> np.ndarray:
    """
    Embed a list of texts → (n, dim) float32 array (L2-normalized rows).

    Tier order:
      1. Fine-tuned finance-embed-v1 (if available) — best for financial queries
      2. OpenAI text-embedding-3-small (retried) — general fallback
      3. Local sentence-transformers model — offline fallback
      4. Raise EmbeddingUnavailable → caller falls back to keyword search

    Cached texts are served from disk.
    """
    if not texts:
        return np.zeros((0, model_dim()), dtype=np.float32)

    # Tier 0: Try fine-tuned model first (no caching needed, it's local)
    finetuned = _embed_finetuned(texts)
    if finetuned is not None:
        return finetuned

    # Log fallback (only on first occurrence to avoid spam)
    if _USE_FINETUNED and not hasattr(embed_texts, '_fallback_logged'):
        logger.warning("Fine-tuned model unavailable; falling back to OpenAI embeddings")
        embed_texts._fallback_logged = True

    # Fall through to OpenAI + local tiers with caching
    vectors: List[Optional[List[float]]] = [None] * len(texts)
    misses: List[int] = []

    if use_cache:
        for i, t in enumerate(texts):
            cached = _read_cache(t)
            if cached is not None:
                vectors[i] = cached
            else:
                misses.append(i)
    else:
        misses = list(range(len(texts)))

    if misses:
        miss_texts = [texts[i] for i in misses]
        try:
            # Tier 1: OpenAI with retry/backoff, batched.
            filled: List[List[float]] = []
            for start in range(0, len(miss_texts), _BATCH):
                batch = miss_texts[start:start + _BATCH]
                filled.extend(_embed_openai_batch(batch))
            for pos, idx in enumerate(misses):
                vectors[idx] = filled[pos]
                if use_cache:
                    _write_cache(texts[idx], filled[pos])
        except Exception as openai_exc:
            # Tier 2: local model (offline). Only if BOTH miss do we give up.
            local = _embed_local(miss_texts)
            if local is None:
                raise EmbeddingUnavailable(
                    f"embedding unavailable (openai: {openai_exc}; no local tier)"
                ) from openai_exc
            logger.info("OpenAI embeddings failed; served %d texts from local tier", len(misses))
            for pos, idx in enumerate(misses):
                vectors[idx] = local[pos].tolist()
                if use_cache:
                    _write_cache(texts[idx], vectors[idx])

    arr = np.array(vectors, dtype=np.float32)
    # L2-normalize so dot product == cosine similarity.
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def embed_query(text: str) -> np.ndarray:
    """Embed a single query → (dim,) normalized vector."""
    return embed_texts([text])[0]


async def embed_texts_async(texts: List[str], *, use_cache: bool = True) -> np.ndarray:
    """
    Async wrapper around embed_texts(). The embedding call itself is sync
    (OpenAI SDK + tenacity retry are sync), so this offloads to a thread via
    asyncio.to_thread — lets FastAPI request handlers `await` embedding without
    blocking the event loop for other requests. Same fail-soft contract as the
    sync path (raises EmbeddingUnavailable on total failure).
    """
    import asyncio
    return await asyncio.to_thread(embed_texts, texts, use_cache=use_cache)


async def embed_query_async(text: str) -> np.ndarray:
    """Async single-query embed — see embed_texts_async."""
    result = await embed_texts_async([text])
    return result[0]
