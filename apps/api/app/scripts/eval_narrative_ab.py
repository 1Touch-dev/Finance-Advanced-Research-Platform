"""
A/B evaluation: GPT-4o-mini vs fine-tuned model for narrative generation.
Uses LLM-as-judge for quality comparison.

Metrics evaluated:
  - accuracy: Factual correctness
  - clarity: Easy to understand
  - professional_style: Reads like an analyst report
  - evidence_use: Cites sources appropriately
  - overall_winner: Which output is better overall

Usage:
  python -m app.scripts.eval_narrative_ab
  python -m app.scripts.eval_narrative_ab --model-b models/finance-narrative-v1 --max-samples 50
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"
DEFAULT_TRAINING_LOG = EXPORTS_DIR / "narrative_training_log.jsonl"

# Judge model - use a stronger model for evaluation
JUDGE_MODEL = os.getenv("NARRATIVE_JUDGE_MODEL", "gpt-4o")
JUDGE_TIMEOUT = int(os.getenv("NARRATIVE_JUDGE_TIMEOUT", "60"))


@dataclass
class JudgeVerdict:
    """Result from LLM judge comparison."""
    winner: str  # "A", "B", or "tie"
    scores_a: Dict[str, float]
    scores_b: Dict[str, float]
    reasoning: str
    dimensions: List[str] = field(default_factory=list)


@dataclass
class EvalResult:
    """Aggregated evaluation results for a model."""
    model_name: str
    mean_accuracy: float
    mean_clarity: float
    mean_style: float
    mean_evidence: float
    overall_score: float
    win_rate: float
    num_samples: int
    details: List[Dict[str, Any]] = field(default_factory=list)


def load_prompts_from_log(path: Path, max_samples: int = 100) -> List[Dict[str, Any]]:
    """
    Load prompts from narrative training log.
    Each entry has: entity, section, prompt, output, model
    """
    prompts = []
    seen_prompts = set()

    with open(path) as f:
        for line in f:
            entry = json.loads(line)
            # Dedupe by prompt hash
            prompt_hash = hash(entry.get("prompt", "")[:500])
            if prompt_hash in seen_prompts:
                continue
            seen_prompts.add(prompt_hash)

            prompts.append({
                "entity": entry.get("entity", "Unknown"),
                "section": entry.get("section", "unknown"),
                "prompt": entry.get("prompt", ""),
                "reference_output": entry.get("output", ""),  # GPT-4o-mini output
            })

            if len(prompts) >= max_samples:
                break

    return prompts


def _call_openai(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0.3,
                 max_tokens: int = 2000, timeout: int = 60) -> str:
    """Call OpenAI API."""
    import requests

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _generate_local(prompt: str, model_path: str, max_tokens: int = 2000) -> str:
    """Generate using local fine-tuned model."""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        # Cache the model
        if not hasattr(_generate_local, "_model") or _generate_local._model_path != model_path:
            logger.info("Loading local model: %s", model_path)
            _generate_local._tokenizer = AutoTokenizer.from_pretrained(model_path)
            _generate_local._model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
            )
            _generate_local._model_path = model_path

        inputs = _generate_local._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096)
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        outputs = _generate_local._model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7,
            pad_token_id=_generate_local._tokenizer.eos_token_id,
        )

        return _generate_local._tokenizer.decode(outputs[0], skip_special_tokens=True)
    except ImportError:
        raise RuntimeError("transformers not installed. Install with: pip install transformers torch")


def judge_outputs(prompt: str, output_a: str, output_b: str,
                  entity: str = "", section: str = "") -> JudgeVerdict:
    """
    Use GPT-4 as judge to compare two narrative outputs.

    Returns scores for each dimension and an overall winner.
    """
    judge_prompt = f"""You are an expert editor evaluating financial intelligence reports.

Compare these two narratives generated for {entity or 'an entity'} ({section or 'report section'}).

ORIGINAL PROMPT:
{prompt[:2000]}

OUTPUT A:
{output_a[:3000]}

OUTPUT B:
{output_b[:3000]}

Rate each output on a scale of 1-5 for:
1. accuracy: Are claims factually correct and internally consistent?
2. clarity: Is the writing clear, precise, and easy to understand?
3. professional_style: Does it read like a professional analyst report?
4. evidence_use: Are sources cited appropriately?

Then determine the overall winner.

Reply with ONLY compact JSON in exactly this shape:
{{"scores_a": {{"accuracy": <1-5>, "clarity": <1-5>, "professional_style": <1-5>, "evidence_use": <1-5>}}, "scores_b": {{"accuracy": <1-5>, "clarity": <1-5>, "professional_style": <1-5>, "evidence_use": <1-5>}}, "winner": "A" or "B" or "tie", "reasoning": "<brief explanation>"}}"""

    try:
        response = _call_openai(judge_prompt, model=JUDGE_MODEL, temperature=0.0,
                                max_tokens=500, timeout=JUDGE_TIMEOUT)

        # Extract JSON from response
        import re
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if not match:
            raise ValueError("No JSON in response")

        data = json.loads(match.group(0))

        return JudgeVerdict(
            winner=data.get("winner", "tie"),
            scores_a=data.get("scores_a", {}),
            scores_b=data.get("scores_b", {}),
            reasoning=data.get("reasoning", ""),
            dimensions=["accuracy", "clarity", "professional_style", "evidence_use"],
        )

    except Exception as exc:
        logger.warning("Judge failed: %s", exc)
        return JudgeVerdict(
            winner="tie",
            scores_a={},
            scores_b={},
            reasoning=f"Judge error: {exc}",
        )


def run_ab_evaluation(
    prompts: List[Dict[str, Any]],
    model_a: str = "gpt-4o-mini",
    model_b: Optional[str] = None,
    use_cached_a: bool = True,
) -> Tuple[EvalResult, Optional[EvalResult]]:
    """
    Run A/B evaluation comparing two models.

    Args:
        prompts: List of prompt dicts with 'prompt', 'entity', 'section', 'reference_output'
        model_a: OpenAI model name for model A
        model_b: Local model path for model B (optional)
        use_cached_a: If True, use reference_output as model A output (faster)
    """
    results_a = []
    results_b = []
    verdicts = []

    for i, p in enumerate(prompts):
        prompt = p["prompt"]
        entity = p["entity"]
        section = p["section"]

        logger.info("Evaluating %d/%d: %s - %s", i + 1, len(prompts), entity, section)

        # Get output A (OpenAI)
        if use_cached_a and p.get("reference_output"):
            output_a = p["reference_output"]
        else:
            try:
                t0 = time.perf_counter()
                output_a = _call_openai(prompt, model=model_a)
                latency_a = (time.perf_counter() - t0) * 1000
            except Exception as exc:
                logger.warning("Model A failed: %s", exc)
                continue

        # Get output B (local model, if specified)
        if model_b:
            try:
                t0 = time.perf_counter()
                output_b = _generate_local(prompt, model_b)
                latency_b = (time.perf_counter() - t0) * 1000
            except Exception as exc:
                logger.warning("Model B failed: %s", exc)
                output_b = output_a  # Fallback for comparison
                latency_b = 0
        else:
            # If no model B, compare A against itself (baseline)
            output_b = output_a
            latency_b = 0

        # Judge the outputs
        verdict = judge_outputs(prompt, output_a, output_b, entity, section)
        verdicts.append(verdict)

        results_a.append({
            "entity": entity,
            "section": section,
            "scores": verdict.scores_a,
            "won": verdict.winner == "A",
        })

        if model_b:
            results_b.append({
                "entity": entity,
                "section": section,
                "scores": verdict.scores_b,
                "won": verdict.winner == "B",
            })

    # Aggregate results for model A
    def avg_score(results, key):
        vals = [r["scores"].get(key, 0) for r in results if r["scores"]]
        return round(statistics.mean(vals), 2) if vals else 0.0

    n_a = max(len(results_a), 1)
    eval_a = EvalResult(
        model_name=f"openai:{model_a}",
        mean_accuracy=avg_score(results_a, "accuracy"),
        mean_clarity=avg_score(results_a, "clarity"),
        mean_style=avg_score(results_a, "professional_style"),
        mean_evidence=avg_score(results_a, "evidence_use"),
        overall_score=round(sum(
            avg_score(results_a, k) for k in ["accuracy", "clarity", "professional_style", "evidence_use"]
        ) / 4, 2),
        win_rate=round(sum(1 for v in verdicts if v.winner == "A") / len(verdicts), 4) if verdicts else 0,
        num_samples=len(results_a),
        details=results_a,
    )

    eval_b = None
    if model_b and results_b:
        n_b = max(len(results_b), 1)
        eval_b = EvalResult(
            model_name=f"local:{model_b}",
            mean_accuracy=avg_score(results_b, "accuracy"),
            mean_clarity=avg_score(results_b, "clarity"),
            mean_style=avg_score(results_b, "professional_style"),
            mean_evidence=avg_score(results_b, "evidence_use"),
            overall_score=round(sum(
                avg_score(results_b, k) for k in ["accuracy", "clarity", "professional_style", "evidence_use"]
            ) / 4, 2),
            win_rate=round(sum(1 for v in verdicts if v.winner == "B") / len(verdicts), 4) if verdicts else 0,
            num_samples=len(results_b),
            details=results_b,
        )

    return eval_a, eval_b


def print_comparison(result_a: EvalResult, result_b: Optional[EvalResult]):
    """Print formatted comparison table."""
    print("\n" + "=" * 70)
    print("NARRATIVE A/B EVALUATION (LLM Judge)")
    print("=" * 70)

    print(f"\n{'Metric':<25} {result_a.model_name[:20]:<20}", end="")
    if result_b:
        print(f" {result_b.model_name[:20]:<20} {'Delta':<10}")
    else:
        print()

    print("-" * 70)

    metrics = [
        ("Accuracy (1-5)", result_a.mean_accuracy, result_b.mean_accuracy if result_b else None),
        ("Clarity (1-5)", result_a.mean_clarity, result_b.mean_clarity if result_b else None),
        ("Professional Style", result_a.mean_style, result_b.mean_style if result_b else None),
        ("Evidence Use", result_a.mean_evidence, result_b.mean_evidence if result_b else None),
        ("Overall Score", result_a.overall_score, result_b.overall_score if result_b else None),
        ("Win Rate", f"{result_a.win_rate:.1%}", f"{result_b.win_rate:.1%}" if result_b else None),
        ("Samples", result_a.num_samples, result_b.num_samples if result_b else None),
    ]

    for name, val_a, val_b in metrics:
        print(f"{name:<25} {str(val_a):<20}", end="")
        if val_b is not None:
            if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                delta = val_b - val_a
                delta_str = f"{delta:+.2f}"
            else:
                delta_str = ""
            print(f" {str(val_b):<20} {delta_str:<10}")
        else:
            print()

    print("=" * 70)

    if result_b:
        tie_rate = 1 - result_a.win_rate - result_b.win_rate
        print(f"\nResults: A wins {result_a.win_rate:.1%}, B wins {result_b.win_rate:.1%}, ties {tie_rate:.1%}")

        if result_b.overall_score >= result_a.overall_score - 0.2:
            print("✓ Model B quality is within acceptable range (≤0.2 difference)")
        else:
            print("✗ Model B quality needs improvement")


def main():
    parser = argparse.ArgumentParser(description="A/B narrative model evaluation with LLM judge")
    parser.add_argument("--training-log", type=Path, default=DEFAULT_TRAINING_LOG,
                        help="Path to narrative training log JSONL")
    parser.add_argument("--model-a", type=str, default="gpt-4o-mini",
                        help="Model A (OpenAI model name)")
    parser.add_argument("--model-b", type=str, default=None,
                        help="Model B (local model path, e.g., models/finance-narrative-v1)")
    parser.add_argument("--max-samples", type=int, default=20,
                        help="Maximum prompts to evaluate")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output JSON file for detailed results")
    parser.add_argument("--regenerate-a", action="store_true",
                        help="Regenerate model A outputs instead of using cached")
    args = parser.parse_args()

    if not args.training_log.exists():
        logger.error("Training log not found: %s", args.training_log)
        logger.info("Generate some reports first to populate the training log")
        return

    logger.info("Loading prompts from %s", args.training_log)
    prompts = load_prompts_from_log(args.training_log, max_samples=args.max_samples)
    logger.info("Loaded %d unique prompts for evaluation", len(prompts))

    if not prompts:
        logger.error("No prompts found in training log")
        return

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not set")
        return

    logger.info("Running A/B evaluation with LLM judge (%s)...", JUDGE_MODEL)
    result_a, result_b = run_ab_evaluation(
        prompts,
        model_a=args.model_a,
        model_b=args.model_b,
        use_cached_a=not args.regenerate_a,
    )

    print_comparison(result_a, result_b)

    # Save detailed results
    if args.output:
        output_data = {
            "judge_model": JUDGE_MODEL,
            "model_a": {
                "name": result_a.model_name,
                "metrics": {
                    "accuracy": result_a.mean_accuracy,
                    "clarity": result_a.mean_clarity,
                    "professional_style": result_a.mean_style,
                    "evidence_use": result_a.mean_evidence,
                    "overall_score": result_a.overall_score,
                    "win_rate": result_a.win_rate,
                    "num_samples": result_a.num_samples,
                },
            },
        }
        if result_b:
            output_data["model_b"] = {
                "name": result_b.model_name,
                "metrics": {
                    "accuracy": result_b.mean_accuracy,
                    "clarity": result_b.mean_clarity,
                    "professional_style": result_b.mean_style,
                    "evidence_use": result_b.mean_evidence,
                    "overall_score": result_b.overall_score,
                    "win_rate": result_b.win_rate,
                    "num_samples": result_b.num_samples,
                },
            }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        logger.info("Detailed results saved to %s", args.output)


if __name__ == "__main__":
    main()
