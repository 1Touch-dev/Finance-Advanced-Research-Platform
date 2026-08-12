"""
RAG embeddings — provider-agnostic, batched, disk-cached, resilient.

Design:
  - Default model: text-embedding-3-small (cheap, 1536-d, strong general-purpose).
    Swappable via RAG_EMBED_MODEL. The eval harness (services/rag/eval) is what
    decides the production model on OUR data, not vendor claims.
  - Disk cache keyed by (model, sha1(text)) so we never pay to re-embed the same
    chunk twice across ingest + eval runs.
  - Resilience tiers (a transient OpenAI blip should NOT drop us to keyword):
      1. OpenAI, retried with exponential backoff (tenacity).
      2. Local model tier (sentence-transformers, e.g. bge/nomic) if configured
         via RAG_LOCAL_EMBED_MODEL — runs offline on CPU.
      3. Only if BOTH are unavailable → raise EmbeddingUnavailable, and callers
         fall back to keyword/TF-IDF retrieval.
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

# Known embedding dimensions, used to size fallback zero-vectors coherently.
_MODEL_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class EmbeddingUnavailable(RuntimeError):
    """Raised when embeddings cannot be produced (no key / provider error)."""


def model_name() -> str:
    return _MODEL


def provider_name() -> str:
    """Which embedding tier is configured (for /health/rag)."""
    if _MODEL.startswith("text-embedding-"):
        return f"openai:{_MODEL}"
    if _LOCAL_MODEL:
        return f"local:{_LOCAL_MODEL}"
    return _MODEL


def model_dim() -> int:
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
    Tries OpenAI (retried), then a local model tier, then raises
    EmbeddingUnavailable. Cached texts are served from disk.
    """
    if not texts:
        return np.zeros((0, model_dim()), dtype=np.float32)

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
