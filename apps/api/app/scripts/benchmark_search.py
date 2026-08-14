#!/usr/bin/env python
"""
Search Speed Benchmark — measures baseline search speeds across all retrieval modes.

Benchmarks:
  1. Keyword search (BM25)
  2. Vector search (embeddings + cosine similarity)
  3. Hybrid search (BM25 + vector + RRF fusion)
  4. With reranking vs without

Usage:
  python -m app.scripts.benchmark_search
  python -m app.scripts.benchmark_search --iterations 10
  python -m app.scripts.benchmark_search --corpus-size 1000
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=False)


@dataclass
class BenchmarkResult:
    mode: str
    rerank: bool
    iterations: int
    corpus_size: int
    latencies_ms: List[float] = field(default_factory=list)

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.latencies_ms) if self.latencies_ms else 0

    @property
    def median_ms(self) -> float:
        return statistics.median(self.latencies_ms) if self.latencies_ms else 0

    @property
    def p95_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def p99_ms(self) -> float:
        if not self.latencies_ms:
            return 0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[min(idx, len(sorted_lat) - 1)]

    @property
    def min_ms(self) -> float:
        return min(self.latencies_ms) if self.latencies_ms else 0

    @property
    def max_ms(self) -> float:
        return max(self.latencies_ms) if self.latencies_ms else 0

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "rerank": self.rerank,
            "iterations": self.iterations,
            "corpus_size": self.corpus_size,
            "mean_ms": round(self.mean_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
        }


# Sample queries for benchmarking
SAMPLE_QUERIES = [
    "What are the company's main risk factors?",
    "Who are the key executives and board members?",
    "What is the revenue breakdown by segment?",
    "Are there any pending lawsuits or litigation?",
    "What government contracts does the company have?",
    "What is the company's competitive position?",
    "Are there any insider trading activities?",
    "What are the analyst recommendations?",
    "What is the company's debt structure?",
    "How does the company compare to its peers?",
]


def generate_test_corpus(n: int) -> List["Document"]:
    """Generate a synthetic test corpus of documents."""
    from app.services.rag.types import Document

    # Financial text templates
    templates = [
        "According to the company's 10-K filing, revenue increased by {pct}% year-over-year, driven by strong performance in the {segment} segment. Management expects continued growth in {year}.",
        "The board of directors approved a dividend increase of {pct}%, reflecting confidence in the company's financial position. This represents the {n}th consecutive year of dividend growth.",
        "Risk factors disclosed in SEC filings include: market volatility, regulatory changes, and competitive pressures. The company maintains adequate insurance coverage.",
        "Insider trading activity shows {name}, the {title}, purchased {shares} shares at an average price of ${price}. This signals confidence in the company's prospects.",
        "Government contracts worth ${amount} million were awarded in Q{quarter}. These contracts span {duration} years and include both development and production phases.",
        "The company's competitive moat includes proprietary technology, strong brand recognition, and a diversified customer base across {n} countries.",
        "Litigation disclosed in the 10-Q includes a patent dispute with {company}. Management believes the claims are without merit.",
        "Analyst consensus rating is {rating} with a price target of ${target}. The stock currently trades at {multiple}x forward earnings.",
        "Debt structure includes ${amount} billion in senior notes due {year} and a ${credit} million revolving credit facility.",
        "Compared to peers, the company ranks in the top quartile for operating margin and return on equity.",
    ]

    docs = []
    for i in range(n):
        template = templates[i % len(templates)]
        text = template.format(
            pct=random.randint(5, 25),
            segment=random.choice(["cloud", "enterprise", "consumer", "hardware"]),
            year=random.choice(["FY2025", "FY2026"]),
            n=random.randint(5, 15),
            name=random.choice(["John Smith", "Jane Doe", "Robert Johnson"]),
            title=random.choice(["CEO", "CFO", "COO", "CTO"]),
            shares=random.randint(10000, 100000),
            price=random.randint(50, 200),
            amount=random.randint(100, 500),
            quarter=random.randint(1, 4),
            duration=random.randint(3, 10),
            company=random.choice(["TechCorp", "InnovateTech", "DataSystems"]),
            rating=random.choice(["Buy", "Strong Buy", "Hold"]),
            target=random.randint(100, 300),
            multiple=random.randint(15, 30),
            credit=random.randint(500, 2000),
        )
        docs.append(Document(id=f"doc_{i}", text=text))

    return docs


def run_benchmark(
    docs: List["Document"],
    mode: str,
    use_rerank: bool,
    iterations: int,
    warmup: int = 2,
) -> BenchmarkResult:
    """Run a benchmark for a specific mode."""
    from app.services.rag.retriever import retrieve
    from app.services.rag.types import RetrievalMode

    mode_enum = {
        "keyword": RetrievalMode.KEYWORD,
        "vector": RetrievalMode.VECTOR,
        "hybrid": RetrievalMode.HYBRID,
    }[mode]

    result = BenchmarkResult(
        mode=mode,
        rerank=use_rerank,
        iterations=iterations,
        corpus_size=len(docs),
    )

    # Warmup runs (not counted)
    for _ in range(warmup):
        query = random.choice(SAMPLE_QUERIES)
        retrieve(query, docs, mode=mode_enum, top_k=10, use_rerank=use_rerank)

    # Actual benchmark runs
    for i in range(iterations):
        query = SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)]
        t0 = time.perf_counter()
        retrieve(query, docs, mode=mode_enum, top_k=10, use_rerank=use_rerank)
        latency = (time.perf_counter() - t0) * 1000
        result.latencies_ms.append(latency)

    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Search speed benchmark")
    ap.add_argument("--iterations", type=int, default=20, help="Number of benchmark iterations per mode")
    ap.add_argument("--corpus-size", type=int, default=500, help="Number of documents in test corpus")
    ap.add_argument("--warmup", type=int, default=2, help="Warmup iterations (not counted)")
    ap.add_argument("--output", type=Path, default=None, help="Save results to JSON file")
    ap.add_argument("--modes", type=str, default="keyword,vector,hybrid", help="Comma-separated modes to test")
    args = ap.parse_args()

    print(f"\n{'='*70}")
    print("SEARCH SPEED BENCHMARK")
    print(f"{'='*70}")
    print(f"Corpus Size: {args.corpus_size} documents")
    print(f"Iterations: {args.iterations} per mode")
    print(f"Warmup: {args.warmup} iterations")
    print(f"Modes: {args.modes}")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"{'='*70}\n")

    # Generate test corpus
    print("Generating test corpus...")
    docs = generate_test_corpus(args.corpus_size)
    print(f"  Created {len(docs)} documents")

    # Run benchmarks
    modes = [m.strip() for m in args.modes.split(",")]
    results: List[BenchmarkResult] = []

    for mode in modes:
        if mode not in ("keyword", "vector", "hybrid"):
            print(f"  Skipping unknown mode: {mode}")
            continue

        # Without reranking
        print(f"\nBenchmarking {mode} (no rerank)...")
        result = run_benchmark(docs, mode, use_rerank=False, iterations=args.iterations, warmup=args.warmup)
        results.append(result)
        print(f"  Mean: {result.mean_ms:.1f}ms, P95: {result.p95_ms:.1f}ms, P99: {result.p99_ms:.1f}ms")

        # With reranking (only for vector and hybrid)
        if mode in ("vector", "hybrid"):
            print(f"Benchmarking {mode} (with rerank)...")
            result = run_benchmark(docs, mode, use_rerank=True, iterations=args.iterations, warmup=args.warmup)
            results.append(result)
            print(f"  Mean: {result.mean_ms:.1f}ms, P95: {result.p95_ms:.1f}ms, P99: {result.p99_ms:.1f}ms")

    # Summary table
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"{'Mode':<15} {'Rerank':<8} {'Mean':<10} {'Median':<10} {'P95':<10} {'P99':<10}")
    print("-" * 70)
    for r in results:
        rerank_str = "Yes" if r.rerank else "No"
        print(f"{r.mode:<15} {rerank_str:<8} {r.mean_ms:<10.1f} {r.median_ms:<10.1f} {r.p95_ms:<10.1f} {r.p99_ms:<10.1f}")

    # Performance recommendations
    print(f"\n{'='*70}")
    print("RECOMMENDATIONS")
    print(f"{'='*70}")

    # Find fastest mode
    fastest = min(results, key=lambda r: r.mean_ms)
    print(f"  Fastest mode: {fastest.mode} ({'with' if fastest.rerank else 'no'} rerank) at {fastest.mean_ms:.1f}ms mean")

    # Check if any mode is too slow
    slow_modes = [r for r in results if r.p95_ms > 1000]
    if slow_modes:
        print(f"  Slow modes (P95 > 1s): {', '.join(r.mode for r in slow_modes)}")
        print(f"  Consider reducing corpus size or disabling reranking for these modes")

    # Hybrid vs others comparison
    hybrid_results = [r for r in results if r.mode == "hybrid" and not r.rerank]
    keyword_results = [r for r in results if r.mode == "keyword"]
    if hybrid_results and keyword_results:
        hybrid_latency = hybrid_results[0].mean_ms
        keyword_latency = keyword_results[0].mean_ms
        overhead = ((hybrid_latency / keyword_latency) - 1) * 100
        print(f"  Hybrid overhead vs keyword: +{overhead:.0f}%")

    # Save results
    if args.output:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "corpus_size": args.corpus_size,
                "iterations": args.iterations,
                "warmup": args.warmup,
            },
            "results": [r.to_dict() for r in results],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {args.output}")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
