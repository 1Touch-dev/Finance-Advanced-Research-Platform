#!/usr/bin/env python
"""
Backfill quality labels — replay existing reports through decision.evaluate
(mode="blend") to seed exports/quality_labels.jsonl before any judge has run
live. This is what makes a real ML classifier trainable *next*: the judge is
the label source the terminal audit said we lacked.

Sources replayed:
  1. DB reports (kind=entity_network_intel) via intelligence_service.get_intelligence_report.
  2. On-disk deep-research JSON files under reports/*.json (matching the shape
     quality_gate_service.run_quality_gates expects).

Usage:
  python -m app.scripts.backfill_quality_labels
  python -m app.scripts.backfill_quality_labels --limit 5 --dry-run
  python -m app.scripts.backfill_quality_labels --mode judge
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterator, Tuple

from dotenv import find_dotenv, load_dotenv

# Load .env explicitly and up front. Without this, disk-sourced reports (which
# are processed before the DB generator's lazy `intelligence_service` import
# has a chance to trigger dotenv loading as a side effect) silently see no
# OPENAI_API_KEY and every judge call fails - a real bug found by running this
# against the actual on-disk NVIDIA report.
load_dotenv(find_dotenv(), override=False)


def _iter_db_reports(limit: int) -> Iterator[Tuple[str, Dict[str, Any]]]:
    try:
        from app.db.session import SessionLocal
        from app.services.intelligence_service import list_intelligence_reports, get_intelligence_report
    except Exception as exc:
        print(f"[backfill] DB reports unavailable ({exc}); skipping DB source")
        return
    db = SessionLocal()
    try:
        rows = list_intelligence_reports(db, limit=limit)
        for row in rows:
            report_id = row["report_id"]
            data = get_intelligence_report(db, report_id)
            if data:
                yield f"db:{report_id}", data
    finally:
        db.close()


def _iter_disk_reports(limit: int) -> Iterator[Tuple[str, Dict[str, Any]]]:
    repo_root = Path(__file__).resolve().parents[4]  # apps/api/app/scripts -> repo root
    pattern = str(repo_root / "reports" / "*.json")
    paths = sorted(glob.glob(pattern))[:limit]
    for p in paths:
        try:
            with open(p) as f:
                data = json.load(f)
            yield f"disk:{Path(p).name}", data
        except Exception as exc:
            print(f"[backfill] failed to read {p}: {exc}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20, help="max reports per source")
    ap.add_argument("--mode", choices=["rules", "judge", "blend"], default="blend")
    ap.add_argument("--dry-run", action="store_true", help="evaluate but don't write labels")
    args = ap.parse_args()

    from app.services.quality.decision import evaluate

    total, judged = 0, 0
    for source_kind, iterator in (("disk", _iter_disk_reports(args.limit)), ("db", _iter_db_reports(args.limit))):
        for report_id, data in iterator:
            total += 1
            try:
                result = evaluate(data, mode=args.mode, report_id=report_id, log_labels=not args.dry_run)
            except Exception as exc:
                print(f"[backfill] {report_id}: evaluate failed ({exc})")
                continue
            jr = result.get("judge_result") or {}
            if jr.get("ok"):
                judged += 1
            print(f"[backfill] {report_id:40s} decision={result['decision']:18s} "
                  f"score={result.get('combined_score')} judge_ok={jr.get('ok')}")

    label_path = Path(os.getenv("EXPORT_DIR", "exports")) / "quality_labels.jsonl"
    print(f"\n[backfill] processed {total} reports, {judged} judged successfully.")
    if not args.dry_run:
        print(f"[backfill] labels written to {label_path}")


if __name__ == "__main__":
    main()
