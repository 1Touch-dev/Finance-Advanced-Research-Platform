#!/usr/bin/env python
"""
Generate synthetic quality-classifier training labels.

Two-stage pipeline (see app/services/quality/synthetic.py for the "why"):
  1. Ask Claude for a bank of narrative paragraph variants, one batch call per
     (quality-profile x section) combo (~30 calls total, not one per report).
  2. Deterministically assemble N report_data dicts from that bank + random
     structural mutations, then run each through the REAL rule gates + REAL
     LLM judge (decision.evaluate(mode="blend")) - Claude never assigns the
     label, only supplies prose variety. Judge calls are parallelized with a
     thread pool since they're one HTTP round-trip each.

Labels are written to exports/quality_labels_synthetic.jsonl (source="synthetic"),
physically separate from exports/quality_labels.jsonl (real live/backfill data) -
train_quality_classifier.py must explicitly opt in to blending them.

Usage:
  python -m app.scripts.generate_synthetic_labels --n 280
  python -m app.scripts.generate_synthetic_labels --n 20 --dry-run
  python -m app.scripts.generate_synthetic_labels --n 280 --workers 8
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=False)

_DEFAULT_OUT = Path(os.getenv("EXPORT_DIR", "exports")) / "quality_labels_synthetic.jsonl"
_DEFAULT_BANK_CACHE = Path(os.getenv("EXPORT_DIR", "exports")) / "synthetic_fragment_bank.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=280, help="number of synthetic reports to generate")
    ap.add_argument("--fragments-per-bucket", type=int, default=6,
                     help="distinct paragraph variants Claude generates per quality profile x section")
    ap.add_argument("--mode", choices=["judge", "blend"], default="blend")
    ap.add_argument("--workers", type=int, default=6, help="parallel judge calls (I/O-bound HTTP)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dry-run", action="store_true", help="evaluate but don't write labels")
    ap.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    ap.add_argument("--bank-cache", type=Path, default=_DEFAULT_BANK_CACHE,
                     help="cache the Claude-generated fragment bank here so repeated runs "
                          "(e.g. tuning --n) don't re-pay ~5min of sequential LLM calls")
    ap.add_argument("--refresh-bank", action="store_true", help="ignore any cached bank and regenerate")
    args = ap.parse_args()

    from app.services.quality.decision import evaluate
    from app.services.quality.synthetic import generate_fragment_bank, generate_synthetic_reports

    fragment_bank = None
    if args.bank_cache.exists() and not args.refresh_bank:
        try:
            fragment_bank = json.loads(args.bank_cache.read_text())
            print(f"[synthetic] loaded cached fragment bank from {args.bank_cache}: "
                  f"{ {k: len(v) for k, v in fragment_bank.items()} }")
        except Exception as exc:
            print(f"[synthetic] failed to load cached bank ({exc}); regenerating")
            fragment_bank = None

    if fragment_bank is None:
        print(f"[synthetic] generating fragment bank ({args.fragments_per_bucket} variants x "
              f"6 profiles x 6 sections = up to {args.fragments_per_bucket * 36} Claude-authored paragraphs)...")
        t0 = time.time()
        fragment_bank = generate_fragment_bank(n_per_bucket=args.fragments_per_bucket)
        bank_counts = {k: len(v) for k, v in fragment_bank.items()}
        print(f"[synthetic] fragment bank ready in {time.time() - t0:.1f}s: {bank_counts}")
        if sum(bank_counts.values()) == 0:
            print("[synthetic] WARNING: fragment bank is empty (no ANTHROPIC_API_KEY?) - "
                  "reports will fall back to a single generic sentence per profile. Continuing anyway.")
        else:
            args.bank_cache.parent.mkdir(parents=True, exist_ok=True)
            args.bank_cache.write_text(json.dumps(fragment_bank, indent=2))
            print(f"[synthetic] cached fragment bank to {args.bank_cache}")

    print(f"[synthetic] assembling {args.n} synthetic report_data dicts (deterministic, seed={args.seed})...")
    reports = generate_synthetic_reports(args.n, fragment_bank, seed=args.seed)

    print(f"[synthetic] running mode={args.mode} evaluation on {len(reports)} reports "
          f"with {args.workers} parallel workers (this calls OPENAI_API_KEY for the judge)...")

    def _run_one(idx_report):
        idx, report = idx_report
        report_id = f"synthetic:{report.get('ticker', idx)}"
        try:
            result = evaluate(
                report, mode=args.mode, report_id=report_id, log_labels=not args.dry_run,
                label_source="synthetic", label_path=args.out,
            )
            return report_id, result, None
        except Exception as exc:
            return report_id, None, exc

    decisions: Counter = Counter()
    judged_ok = 0
    scores = []
    failed = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(_run_one, item) for item in enumerate(reports)]
        for i, fut in enumerate(as_completed(futures), 1):
            report_id, result, exc = fut.result()
            if exc is not None:
                failed += 1
                print(f"[synthetic] {report_id}: FAILED ({exc})")
                continue
            decisions[result["decision"]] += 1
            jr = result.get("judge_result") or {}
            if jr.get("ok"):
                judged_ok += 1
            if result.get("combined_score") is not None:
                scores.append(result["combined_score"])
            if i % 20 == 0 or i == len(reports):
                print(f"[synthetic] {i}/{len(reports)} done "
                      f"({time.time() - t0:.0f}s elapsed, {judged_ok} judged ok, {failed} failed)")

    print(f"\n[synthetic] done in {time.time() - t0:.0f}s.")
    print(f"[synthetic] decisions: {dict(decisions)}")
    print(f"[synthetic] judged_ok={judged_ok}/{len(reports)}  failed={failed}")
    if scores:
        print(f"[synthetic] combined_score mean={sum(scores)/len(scores):.3f} "
              f"min={min(scores):.3f} max={max(scores):.3f}")
    if not args.dry_run:
        print(f"[synthetic] labels written to {args.out}")


if __name__ == "__main__":
    main()
