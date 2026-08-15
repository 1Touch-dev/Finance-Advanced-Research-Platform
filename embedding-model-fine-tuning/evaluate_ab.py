#!/usr/bin/env python3
"""
A/B Evaluation: Compare fine-tuned finance-embed-v1 model vs base nomic-embed-text-v1.5.

Metrics:
  - Ranking Accuracy: % of triplets where positive ranks higher than negative
  - Average Margin: Mean difference (positive_score - negative_score)
  - MRR (Mean Reciprocal Rank): Average 1/rank of correct answer

Run: python evaluate_ab.py
"""

import json
import random
import time
from pathlib import Path

# Try to import sentence_transformers
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    print("Installing sentence-transformers...")
    import subprocess
    subprocess.check_call(["pip", "install", "sentence-transformers", "-q"])
    from sentence_transformers import SentenceTransformer, util

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FINE_TUNED_MODEL = SCRIPT_DIR / "finance-embed-v1"
TRIPLETS_FILE = PROJECT_ROOT / "apps" / "api" / "exports" / "embedding_triplets.jsonl"

# Evaluation sample size (larger = more accurate but slower)
EVAL_SAMPLE_SIZE = 200


def load_triplets(path: Path, max_samples: int = None) -> list:
    """Load triplets from JSONL file."""
    triplets = []
    with open(path) as f:
        for line in f:
            triplets.append(json.loads(line))

    if max_samples and len(triplets) > max_samples:
        random.seed(42)  # Reproducible sampling
        triplets = random.sample(triplets, max_samples)

    return triplets


def evaluate_model(model, triplets: list, model_name: str) -> dict:
    """
    Evaluate model on triplet ranking task.

    For each triplet (anchor, positive, negative):
    - Compute similarity(anchor, positive) and similarity(anchor, negative)
    - Check if positive ranks higher than negative
    """
    correct = 0
    total = 0
    score_diffs = []  # positive_score - negative_score
    mrr_sum = 0  # For Mean Reciprocal Rank

    print(f"\n  Evaluating {model_name}...")
    start_time = time.time()

    for i, t in enumerate(triplets):
        anchor = t.get('anchor', '')
        positive = t.get('positive', '')
        # Handle different negative field names
        negative = t.get('hard_negative') or t.get('negative', '')

        if not anchor or not positive or not negative:
            continue

        # Encode texts
        anchor_emb = model.encode([anchor], convert_to_tensor=True)
        pos_emb = model.encode([positive], convert_to_tensor=True)
        neg_emb = model.encode([negative], convert_to_tensor=True)

        # Compute cosine similarities
        pos_score = util.cos_sim(anchor_emb, pos_emb).item()
        neg_score = util.cos_sim(anchor_emb, neg_emb).item()

        # Ranking accuracy: does positive rank higher than negative?
        if pos_score > neg_score:
            correct += 1
            mrr_sum += 1.0  # Rank 1 → reciprocal = 1
        else:
            mrr_sum += 0.5  # Rank 2 → reciprocal = 0.5

        score_diffs.append(pos_score - neg_score)
        total += 1

        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"    Processed {i + 1}/{len(triplets)} triplets...")

    elapsed = time.time() - start_time

    accuracy = (correct / total * 100) if total > 0 else 0
    avg_margin = sum(score_diffs) / len(score_diffs) if score_diffs else 0
    mrr = mrr_sum / total if total > 0 else 0

    return {
        'model': model_name,
        'accuracy': round(accuracy, 2),
        'avg_margin': round(avg_margin, 4),
        'mrr': round(mrr, 4),
        'total_samples': total,
        'correct': correct,
        'time_sec': round(elapsed, 1),
        'score_diffs': score_diffs,
    }


def print_results(base_results: dict, fine_results: dict):
    """Print comparison table."""
    print("\n" + "=" * 70)
    print("A/B EVALUATION RESULTS")
    print("=" * 70)

    print(f"\n{'Metric':<30} {'Base Model':<20} {'Fine-tuned':<20}")
    print("-" * 70)
    print(f"{'Ranking Accuracy':<30} {base_results['accuracy']:.1f}%{'':<17} {fine_results['accuracy']:.1f}%")
    print(f"{'Avg Margin (pos - neg)':<30} {base_results['avg_margin']:.4f}{'':<14} {fine_results['avg_margin']:.4f}")
    print(f"{'MRR (Mean Reciprocal Rank)':<30} {base_results['mrr']:.4f}{'':<14} {fine_results['mrr']:.4f}")
    print(f"{'Correct / Total':<30} {base_results['correct']}/{base_results['total_samples']:<17} {fine_results['correct']}/{fine_results['total_samples']}")
    print(f"{'Evaluation Time':<30} {base_results['time_sec']}s{'':<17} {fine_results['time_sec']}s")

    # Improvements
    acc_diff = fine_results['accuracy'] - base_results['accuracy']
    margin_diff = fine_results['avg_margin'] - base_results['avg_margin']
    mrr_diff = fine_results['mrr'] - base_results['mrr']

    print("\n" + "=" * 70)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 70)
    print(f"{'Accuracy Change:':<30} {acc_diff:+.2f}%")
    print(f"{'Margin Change:':<30} {margin_diff:+.4f}")
    print(f"{'MRR Change:':<30} {mrr_diff:+.4f}")

    # Score distribution analysis
    base_positive = sum(1 for d in base_results['score_diffs'] if d > 0)
    fine_positive = sum(1 for d in fine_results['score_diffs'] if d > 0)
    base_strong = sum(1 for d in base_results['score_diffs'] if d > 0.1)
    fine_strong = sum(1 for d in fine_results['score_diffs'] if d > 0.1)

    print(f"\n{'Margin > 0 (correct ranking):':<30} {base_positive}/{base_results['total_samples']:<17} {fine_positive}/{fine_results['total_samples']}")
    print(f"{'Margin > 0.1 (strong signal):':<30} {base_strong}/{base_results['total_samples']:<17} {fine_strong}/{fine_results['total_samples']}")

    # Verdict
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    if acc_diff > 5:
        print("\n  SIGNIFICANT IMPROVEMENT!")
        print(f"  Fine-tuned model is {acc_diff:.1f}% more accurate at ranking financial documents.")
    elif acc_diff > 0:
        print("\n  MODEST IMPROVEMENT")
        print(f"  Fine-tuned model shows {acc_diff:.1f}% improvement in ranking accuracy.")
    elif acc_diff > -2:
        print("\n  SIMILAR PERFORMANCE")
        print("  Both models perform comparably on this dataset.")
    else:
        print("\n  REGRESSION DETECTED")
        print("  Fine-tuned model performs worse. Check training data quality.")

    if margin_diff > 0.01:
        print(f"  Margin improved by {margin_diff:.4f} - model is more confident in correct rankings.")

    print("\n" + "=" * 70)


def main():
    print("\n" + "=" * 70)
    print("EMBEDDINGS A/B EVALUATION")
    print("=" * 70)
    print(f"Fine-tuned model: {FINE_TUNED_MODEL}")
    print(f"Base model: nomic-ai/nomic-embed-text-v1.5")
    print(f"Triplets file: {TRIPLETS_FILE}")
    print(f"Sample size: {EVAL_SAMPLE_SIZE}")

    # Load triplets
    print("\nLoading triplets...")
    triplets = load_triplets(TRIPLETS_FILE, max_samples=EVAL_SAMPLE_SIZE)
    print(f"  Loaded {len(triplets)} triplets for evaluation")

    # Load models
    print("\nLoading models...")
    print("  Loading fine-tuned model (local)...")
    fine_model = SentenceTransformer(str(FINE_TUNED_MODEL), trust_remote_code=True)

    print("  Loading base model (downloading if needed)...")
    base_model = SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True)

    # Run evaluations
    base_results = evaluate_model(base_model, triplets, "Base (nomic-embed-text-v1.5)")
    fine_results = evaluate_model(fine_model, triplets, "Fine-tuned (finance-embed-v1)")

    # Print comparison
    print_results(base_results, fine_results)

    # Example queries
    print("\n" + "=" * 70)
    print("EXAMPLE QUERIES")
    print("=" * 70)

    test_queries = [
        {
            "query": "Apple Q3 revenue growth",
            "docs": [
                "AAPL reported $89B revenue in Q3 2024, up 12% YoY",
                "Microsoft reported $56B revenue in Q3 2024",
                "The weather forecast shows sunny skies",
            ],
            "expected": 0,  # First doc should rank highest
        },
        {
            "query": "Tesla insider trading",
            "docs": [
                "TSLA CEO sold 1M shares at $250 average price",
                "Ford executive compensation disclosed in proxy",
                "New car models announced at auto show",
            ],
            "expected": 0,
        },
    ]

    for test in test_queries:
        print(f"\nQuery: \"{test['query']}\"")
        print("-" * 50)

        query_emb_base = base_model.encode([test['query']])
        query_emb_fine = fine_model.encode([test['query']])

        docs_emb_base = base_model.encode(test['docs'])
        docs_emb_fine = fine_model.encode(test['docs'])

        scores_base = util.cos_sim(query_emb_base, docs_emb_base)[0].tolist()
        scores_fine = util.cos_sim(query_emb_fine, docs_emb_fine)[0].tolist()

        print(f"{'Document':<50} {'Base':<10} {'Fine-tuned':<10}")
        for i, doc in enumerate(test['docs']):
            doc_short = doc[:47] + "..." if len(doc) > 50 else doc
            marker = " <--" if i == test['expected'] else ""
            print(f"{doc_short:<50} {scores_base[i]:.4f}     {scores_fine[i]:.4f}{marker}")

        # Check which model got it right
        base_best = scores_base.index(max(scores_base))
        fine_best = scores_fine.index(max(scores_fine))

        base_correct = "correct" if base_best == test['expected'] else "WRONG"
        fine_correct = "correct" if fine_best == test['expected'] else "WRONG"
        print(f"\nBase model: {base_correct} | Fine-tuned: {fine_correct}")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
