"""
A/B comparison: generic vs fine-tuned embeddings on domain evaluation set.

Uses triplets from embedding_triplets.jsonl as eval queries:
  - anchor = query
  - positive = expected relevant doc
  - hard_negative = confusing but wrong doc

Metrics:
  - hit@k: Does the positive doc appear in top k?
  - MRR: Mean Reciprocal Rank of the positive doc
  - nDCG@k: Normalized Discounted Cumulative Gain
  - Latency: Time per query (ms)
  - Separation: Score difference between positive and hard_negative

Usage:
  python -m app.scripts.eval_embeddings_ab
  python -m app.scripts.eval_embeddings_ab --model-b models/finance-embed-v1 --k 10
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"
DEFAULT_TRIPLETS = EXPORTS_DIR / "embedding_triplets.jsonl"


@dataclass
class EvalResult:
    """Results from evaluating one embedding model."""
    model_name: str
    hit_at_k: float
    mrr: float
    ndcg_at_k: float
    mean_latency_ms: float
    p95_latency_ms: float
    mean_separation: float  # Score(positive) - Score(hard_negative)
    num_queries: int
    details: List[Dict[str, Any]] = field(default_factory=list)


def load_triplets(path: Path, max_samples: int = 500) -> List[Dict[str, Any]]:
    """Load triplets from JSONL file."""
    triplets = []
    with open(path) as f:
        for line in f:
            triplets.append(json.loads(line))
            if len(triplets) >= max_samples:
                break
    return triplets


def _embed_openai(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """Embed texts using OpenAI API."""
    import requests

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": texts},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return [item["embedding"] for item in data["data"]]


def _embed_local(texts: List[str], model_path: str) -> List[List[float]]:
    """Embed texts using a local sentence-transformers model."""
    from sentence_transformers import SentenceTransformer

    # Cache the model
    if not hasattr(_embed_local, "_model") or _embed_local._model_path != model_path:
        logger.info("Loading local model: %s", model_path)
        _embed_local._model = SentenceTransformer(model_path)
        _embed_local._model_path = model_path

    embeddings = _embed_local._model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-9))


def evaluate_model(
    triplets: List[Dict[str, Any]],
    embed_fn,
    model_name: str,
    k: int = 5,
) -> EvalResult:
    """
    Evaluate an embedding model on triplet queries.

    For each triplet:
      1. Embed anchor, positive, hard_negative
      2. Compute similarity scores
      3. Check if positive ranks higher than hard_negative
    """
    hits = []
    mrrs = []
    ndcgs = []
    separations = []
    latencies = []
    details = []

    for i, triplet in enumerate(triplets):
        anchor = triplet["anchor"]
        positive = triplet["positive"]
        hard_negative = triplet["hard_negative"]

        t0 = time.perf_counter()
        try:
            embeddings = embed_fn([anchor, positive, hard_negative])
        except Exception as exc:
            logger.warning("Embedding failed for triplet %d: %s", i, exc)
            continue
        latency_ms = (time.perf_counter() - t0) * 1000

        emb_anchor, emb_positive, emb_negative = embeddings

        score_positive = cosine_similarity(emb_anchor, emb_positive)
        score_negative = cosine_similarity(emb_anchor, emb_negative)

        # Separation: how much better is positive than hard_negative
        separation = score_positive - score_negative
        separations.append(separation)

        # For hit@k and MRR, we treat this as a 2-doc corpus
        # Positive should rank higher than hard_negative
        if score_positive > score_negative:
            rank = 1  # Positive is rank 1
        else:
            rank = 2  # Positive is rank 2

        # hit@k: Did positive appear in top k? (with 2 docs, k >= 1 always hits)
        hit = 1.0 if rank <= k else 0.0
        hits.append(hit)

        # MRR: 1/rank of first relevant
        mrrs.append(1.0 / rank)

        # nDCG@k: Normalized DCG (simplified for 2-doc case)
        # DCG = 1/log2(rank+1) if positive is in top k
        import math
        dcg = 1.0 / math.log2(rank + 1) if rank <= k else 0.0
        ideal_dcg = 1.0  # Ideal is positive at rank 1: 1/log2(2) = 1
        ndcg = dcg / ideal_dcg
        ndcgs.append(ndcg)

        latencies.append(latency_ms)

        details.append({
            "triplet_idx": i,
            "score_positive": round(score_positive, 4),
            "score_negative": round(score_negative, 4),
            "separation": round(separation, 4),
            "rank": rank,
            "latency_ms": round(latency_ms, 2),
        })

    n = max(len(hits), 1)
    return EvalResult(
        model_name=model_name,
        hit_at_k=round(sum(hits) / n, 4),
        mrr=round(sum(mrrs) / n, 4),
        ndcg_at_k=round(sum(ndcgs) / n, 4),
        mean_latency_ms=round(statistics.mean(latencies) if latencies else 0, 2),
        p95_latency_ms=round(sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0, 2),
        mean_separation=round(statistics.mean(separations) if separations else 0, 4),
        num_queries=len(hits),
        details=details,
    )


def run_ab_comparison(
    triplets: List[Dict[str, Any]],
    model_a: str = "text-embedding-3-small",
    model_b: Optional[str] = None,
    k: int = 5,
) -> Tuple[EvalResult, Optional[EvalResult]]:
    """
    Run A/B comparison between two embedding models.

    Model A: OpenAI or specified model
    Model B: Local fine-tuned model (optional)
    """
    # Define embedding functions
    def embed_a(texts):
        return _embed_openai(texts, model=model_a)

    result_a = evaluate_model(triplets, embed_a, f"openai:{model_a}", k=k)

    result_b = None
    if model_b:
        def embed_b(texts):
            return _embed_local(texts, model_b)
        result_b = evaluate_model(triplets, embed_b, f"local:{model_b}", k=k)

    return result_a, result_b


def print_comparison(result_a: EvalResult, result_b: Optional[EvalResult], k: int):
    """Print formatted comparison table."""
    print("\n" + "=" * 70)
    print("A/B EMBEDDING COMPARISON")
    print("=" * 70)

    headers = ["Metric", result_a.model_name[:25]]
    if result_b:
        headers.append(result_b.model_name[:25])
        headers.append("Delta")

    print(f"\n{'Metric':<20} {result_a.model_name[:25]:<25}", end="")
    if result_b:
        print(f" {result_b.model_name[:25]:<25} {'Delta':<10}")
    else:
        print()

    print("-" * 70)

    metrics = [
        (f"hit@{k}", result_a.hit_at_k, result_b.hit_at_k if result_b else None),
        ("MRR", result_a.mrr, result_b.mrr if result_b else None),
        (f"nDCG@{k}", result_a.ndcg_at_k, result_b.ndcg_at_k if result_b else None),
        ("Separation", result_a.mean_separation, result_b.mean_separation if result_b else None),
        ("Latency (ms)", result_a.mean_latency_ms, result_b.mean_latency_ms if result_b else None),
        ("P95 Latency", result_a.p95_latency_ms, result_b.p95_latency_ms if result_b else None),
        ("Queries", result_a.num_queries, result_b.num_queries if result_b else None),
    ]

    for name, val_a, val_b in metrics:
        print(f"{name:<20} {val_a:<25}", end="")
        if val_b is not None:
            if name in ("Latency (ms)", "P95 Latency"):
                # Lower is better for latency
                delta = val_a - val_b
                delta_str = f"{delta:+.1f}ms"
            elif name == "Queries":
                delta_str = ""
            else:
                # Higher is better for other metrics
                if val_a > 0:
                    delta_pct = ((val_b - val_a) / val_a) * 100
                    delta_str = f"{delta_pct:+.1f}%"
                else:
                    delta_str = "N/A"
            print(f" {val_b:<25} {delta_str:<10}")
        else:
            print()

    print("=" * 70)

    # Summary
    if result_b:
        wins = sum([
            result_b.hit_at_k > result_a.hit_at_k,
            result_b.mrr > result_a.mrr,
            result_b.ndcg_at_k > result_a.ndcg_at_k,
            result_b.mean_separation > result_a.mean_separation,
        ])
        print(f"\nModel B wins on {wins}/4 retrieval metrics")
        if result_b.mean_latency_ms < result_a.mean_latency_ms:
            print("Model B is faster")
        else:
            print(f"Model B is {result_b.mean_latency_ms - result_a.mean_latency_ms:.1f}ms slower (acceptable if quality improved)")


def main():
    parser = argparse.ArgumentParser(description="A/B embedding model comparison")
    parser.add_argument("--triplets", type=Path, default=DEFAULT_TRIPLETS,
                        help="Path to triplets JSONL file")
    parser.add_argument("--model-a", type=str, default="text-embedding-3-small",
                        help="Model A (OpenAI model name)")
    parser.add_argument("--model-b", type=str, default=None,
                        help="Model B (local model path, e.g., models/finance-embed-v1)")
    parser.add_argument("--k", type=int, default=5, help="k for hit@k and nDCG@k")
    parser.add_argument("--max-samples", type=int, default=200,
                        help="Maximum triplets to evaluate (for speed)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output JSON file for detailed results")
    args = parser.parse_args()

    if not args.triplets.exists():
        logger.error("Triplets file not found: %s", args.triplets)
        logger.info("Run extract_embedding_pairs.py first to generate triplets")
        return

    logger.info("Loading triplets from %s", args.triplets)
    triplets = load_triplets(args.triplets, max_samples=args.max_samples)
    logger.info("Loaded %d triplets for evaluation", len(triplets))

    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY not set - Model A evaluation will fail")

    logger.info("Running A/B comparison...")
    result_a, result_b = run_ab_comparison(
        triplets,
        model_a=args.model_a,
        model_b=args.model_b,
        k=args.k,
    )

    print_comparison(result_a, result_b, args.k)

    # Save detailed results
    if args.output:
        output_data = {
            "model_a": {
                "name": result_a.model_name,
                "metrics": {
                    f"hit@{args.k}": result_a.hit_at_k,
                    "mrr": result_a.mrr,
                    f"ndcg@{args.k}": result_a.ndcg_at_k,
                    "mean_separation": result_a.mean_separation,
                    "mean_latency_ms": result_a.mean_latency_ms,
                    "p95_latency_ms": result_a.p95_latency_ms,
                    "num_queries": result_a.num_queries,
                },
                "details": result_a.details,
            },
        }
        if result_b:
            output_data["model_b"] = {
                "name": result_b.model_name,
                "metrics": {
                    f"hit@{args.k}": result_b.hit_at_k,
                    "mrr": result_b.mrr,
                    f"ndcg@{args.k}": result_b.ndcg_at_k,
                    "mean_separation": result_b.mean_separation,
                    "mean_latency_ms": result_b.mean_latency_ms,
                    "p95_latency_ms": result_b.p95_latency_ms,
                    "num_queries": result_b.num_queries,
                },
                "details": result_b.details,
            }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        logger.info("Detailed results saved to %s", args.output)


if __name__ == "__main__":
    main()
