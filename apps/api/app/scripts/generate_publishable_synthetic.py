#!/usr/bin/env python
"""
Generate HIGH-QUALITY PUBLISHABLE synthetic reports using Claude Opus 4.5.

This script focuses on generating reports that WILL pass the quality gates,
to balance the training data which is currently 90% non-publishable.

Key differences from generate_synthetic_labels.py:
  1. Uses Claude Opus 4.5 (claude-opus-4-5-20251101) for best quality
  2. 90% "excellent" tier (vs 40% in original)
  3. Stricter mutation profiles that avoid hard failures
  4. Generates well-cited, clear, professional reports

Usage:
  python -m app.scripts.generate_publishable_synthetic --n 100
  python -m app.scripts.generate_publishable_synthetic --n 50 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=False)

_DEFAULT_OUT = Path(os.getenv("EXPORT_DIR", "exports")) / "quality_labels_synthetic.jsonl"
_DEFAULT_BANK_CACHE = Path(os.getenv("EXPORT_DIR", "exports")) / "opus_fragment_bank.json"

# Use Claude Opus 4.5 for best quality
OPUS_MODEL = "claude-opus-4-5-20251101"

# Fictional entities
_SYNTH_ENTITIES = [
    ("Quantum Dynamics Corp", "QDYN"), ("Sterling Biotech Holdings", "STBH"),
    ("Aurora Semiconductor Inc", "AURS"), ("Nexus Cloud Systems", "NCLS"),
    ("Pinnacle Energy Solutions", "PNES"), ("Citadel Defense Tech", "CDFT"),
    ("Horizon Materials Group", "HMGP"), ("Vertex Aerospace Industries", "VTXI"),
    ("Summit Analytics Corp", "SMAC"), ("Frontier Robotics Inc", "FRNT"),
    ("Catalyst Financial Tech", "CAFT"), ("Apex Renewable Power", "APXR"),
    ("Titan Logistics Holdings", "TLGH"), ("Nova Cybersecurity Systems", "NVCS"),
    ("Evergreen Health Sciences", "EVHS"),
]

# High-quality prompt templates designed to pass quality gates
_PUBLISHABLE_PROMPTS = {
    "analyst_grade": """Write a 4-5 sentence analytical paragraph for a financial intelligence report's {section} section.

REQUIREMENTS:
- Write like a senior equity research analyst at Goldman Sachs or Morgan Stanley
- Use precise, neutral, analytical language - no hedging phrases like "may" or "could"
- Make concrete, well-sourced claims (reference SEC filings, earnings calls, industry reports)
- Include specific citations like "according to the company's 10-K filing" or "per recent earnings call"
- State facts confidently without speculation
- Keep it purely qualitative - NO dollar figures or percentages
- Refer to the subject as "the company" - never use a specific name

Example tone: "The company's strategic pivot toward cloud infrastructure, disclosed in its Q3 earnings call, positions it favorably against commoditized competitors. Management's disciplined approach to capital allocation, as evidenced by SEC filings, demonstrates commitment to long-term shareholder value."
""",
    "institutional_quality": """Write a 4-5 sentence paragraph for an institutional-grade financial intelligence report's {section} section.

REQUIREMENTS:
- Professional, objective tone suitable for institutional investors
- Reference specific public documents (10-K, 10-Q, proxy statements, earnings transcripts)
- Make assertive claims backed by documented evidence
- No vague language, no hedging, no speculation
- Clear logical structure with evidence-based conclusions
- Keep it qualitative - NO specific numbers
- Refer to the subject as "the company" only

Example: "According to SEC filings, the company has established significant barriers to entry through proprietary technology and exclusive supplier agreements. Recent proxy disclosures indicate strong alignment between executive compensation and shareholder returns."
""",
    "research_report": """Write a 4-5 sentence paragraph for a professional research report's {section} section.

REQUIREMENTS:
- Write with the authority of a published research report
- Cite sources explicitly: "disclosed in quarterly filings", "per industry analysis", "according to management commentary"
- Make definitive statements about the company's position and trajectory
- Avoid ALL hedging language (no "potentially", "might", "could", "appears to")
- Focus on documented facts and clear analytical conclusions
- Keep it qualitative with NO dollar amounts
- Use "the company" as the only reference

The goal is a paragraph that reads like it came from a published Wall Street research note.
""",
}

_SECTIONS = [
    "financial performance", "competitive position", "management quality",
    "strategic initiatives", "market opportunity", "operational efficiency"
]


@dataclass
class PublishableMutation:
    """Mutation profile designed to PASS quality gates."""
    citation_rate: float = 1.0          # Full citations
    duplicate_paragraphs: int = 0        # No duplicates
    news_staleness_days: int = 5         # Recent news
    placeholder_count: int = 0           # No placeholders
    arithmetic_mismatch: bool = False    # Correct math
    fiscal_labeled: bool = True          # Proper FY labels
    landing_page_urls: bool = False      # Deep links, not bare domains
    named_person_sources: int = 3        # Well-sourced people
    sensitive_claim_cited: bool = True   # Cited sensitive claims


def generate_opus_fragments(n_per_section: int = 8) -> Dict[str, List[str]]:
    """Generate high-quality fragments using Claude Opus 4.5."""
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[opus-synth] WARNING: ANTHROPIC_API_KEY not set, using fallback text")
        return {}

    client = anthropic.Anthropic(api_key=api_key)
    bank: Dict[str, List[str]] = {name: [] for name in _PUBLISHABLE_PROMPTS}

    print(f"[opus-synth] Generating fragments with Opus 4.5 ({len(_PUBLISHABLE_PROMPTS)} profiles x {len(_SECTIONS)} sections)...")

    for profile_name, prompt_template in _PUBLISHABLE_PROMPTS.items():
        for section in _SECTIONS:
            prompt = prompt_template.format(section=section)
            batch_prompt = (
                prompt +
                f"\n\nGenerate exactly {n_per_section} DIFFERENT high-quality variants. "
                "Each should be independently excellent, with different specific details/angles. "
                "Reply with ONLY a JSON array of strings."
            )

            try:
                response = client.messages.create(
                    model=OPUS_MODEL,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": batch_prompt}],
                    system="You are a senior financial analyst generating training data for a report quality classifier. Every paragraph must be publication-ready."
                )

                text = response.content[0].text
                match = re.search(r"\[.*\]", text, re.DOTALL)
                if match:
                    variants = json.loads(match.group(0))
                    bank[profile_name].extend(str(v) for v in variants if isinstance(v, str))
                    print(f"  [opus-synth] {profile_name}/{section}: {len(variants)} variants")

            except Exception as exc:
                print(f"  [opus-synth] {profile_name}/{section}: FAILED ({exc})")

    total = sum(len(v) for v in bank.values())
    print(f"[opus-synth] Generated {total} high-quality fragments")
    return bank


def build_publishable_report(
    fragment_bank: Dict[str, List[str]],
    rng: random.Random,
    idx: int,
) -> Dict[str, Any]:
    """Build a report designed to pass quality gates."""
    entity_name, ticker = rng.choice(_SYNTH_ENTITIES)
    entity_name = f"{entity_name} #{idx}"
    base_url = f"https://sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker.lower()}{idx}"

    # Pick a random profile and get fragment
    profile = rng.choice(list(_PUBLISHABLE_PROMPTS.keys()))
    fragments = fragment_bank.get(profile, [])

    if fragments:
        narrative = rng.choice(fragments)
        context_fragment = rng.choice(fragments)
    else:
        narrative = (
            f"The company has demonstrated consistent execution of its strategic initiatives, "
            f"as documented in recent SEC filings. Management's capital allocation decisions, "
            f"per the latest proxy statement, reflect a disciplined approach to value creation. "
            f"Industry analysis confirms the company's strong competitive positioning within "
            f"its core markets."
        )
        context_fragment = narrative

    # Build properly cited financial segments
    n_segments = rng.choice([2, 3, 4])
    segments = []
    segment_total = 0
    for i in range(n_segments):
        revenue = rng.randint(50, 500) * 1_000_000
        segment_total += revenue
        segments.append({
            "name": f"Business Unit {chr(65 + i)}",  # A, B, C, D
            "revenue": revenue,
            "source_url": f"{base_url}&type=10-K#segment{i}",
            "fiscal_period": "FY2025",
        })

    financial_intelligence = {
        "total_revenue": segment_total,  # Correct arithmetic
        "segments": segments,
        "summary": narrative,
        "source_url": f"{base_url}&type=10-K",
        "fiscal_year": "FY2025",
    }

    data = {
        "entity_name": entity_name,
        "ticker": f"{ticker}{idx}",
        "financial_intelligence": financial_intelligence,
    }

    # Recent news (within 7 days)
    article_date = (datetime.utcnow() - timedelta(days=rng.randint(1, 7))).strftime("%Y-%m-%d")
    data["news_intelligence"] = {
        "articles": [
            {
                "title": f"{entity_name} Announces Strategic Update",
                "date": article_date,
                "summary": context_fragment,
                "source_url": f"https://reuters.com/companies/{ticker.lower()}{idx}",
            },
            {
                "title": f"Analyst Coverage: {entity_name}",
                "date": article_date,
                "summary": rng.choice(fragments) if fragments else context_fragment,
                "source_url": f"https://bloomberg.com/quote/{ticker.lower()}{idx}",
            },
        ]
    }

    # Well-sourced executives (multiple independent sources)
    exec_name = f"John Smith (CEO #{idx})"
    data["proxy_intelligence"] = {
        "executives": [
            {"name": exec_name, "title": "Chief Executive Officer", "source_url": f"{base_url}&type=DEF14A"}
        ]
    }
    data["board_interlocks"] = {
        "people": [{"name": exec_name, "source_url": f"https://linkedin.com/in/{ticker.lower()}-ceo"}]
    }
    data["insider_transactions"] = {
        "transactions": [
            {
                "owner_name": exec_name,
                "transaction_code": "P",  # Purchase (positive signal)
                "shares": rng.randint(10000, 100000),
                "source_url": f"{base_url}&type=4",
                "context": "Regular purchase per disclosed trading plan",
            }
        ]
    }

    # Cited sensitive claims (if any)
    if rng.random() < 0.3:  # Only 30% have sensitive claims
        data["risk_flags"] = {
            "note": "The company disclosed ongoing regulatory discussions, as detailed in its 10-Q filing.",
            "source_url": f"{base_url}&type=10-Q#risk",
        }

    return data


def generate_publishable_reports(
    n: int,
    fragment_bank: Dict[str, List[str]],
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Generate N publishable-quality reports."""
    rng = random.Random(seed)
    return [build_publishable_report(fragment_bank, rng, i) for i in range(n)]


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate high-quality publishable synthetic reports")
    ap.add_argument("--n", type=int, default=100, help="Number of reports to generate")
    ap.add_argument("--fragments-per-section", type=int, default=8)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1337)  # Different seed from original
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    ap.add_argument("--bank-cache", type=Path, default=_DEFAULT_BANK_CACHE)
    ap.add_argument("--refresh-bank", action="store_true")
    args = ap.parse_args()

    # Load or generate fragment bank
    fragment_bank = None
    if args.bank_cache.exists() and not args.refresh_bank:
        try:
            fragment_bank = json.loads(args.bank_cache.read_text())
            total = sum(len(v) for v in fragment_bank.values())
            print(f"[opus-synth] Loaded cached Opus fragment bank: {total} fragments")
        except Exception as exc:
            print(f"[opus-synth] Failed to load cache: {exc}")

    if fragment_bank is None:
        fragment_bank = generate_opus_fragments(n_per_section=args.fragments_per_section)
        if sum(len(v) for v in fragment_bank.values()) > 0:
            args.bank_cache.parent.mkdir(parents=True, exist_ok=True)
            args.bank_cache.write_text(json.dumps(fragment_bank, indent=2))
            print(f"[opus-synth] Cached to {args.bank_cache}")

    # Generate reports
    print(f"[opus-synth] Generating {args.n} publishable-quality reports...")
    reports = generate_publishable_reports(args.n, fragment_bank, seed=args.seed)

    # Run through quality evaluation
    from app.services.quality.decision import evaluate

    print(f"[opus-synth] Evaluating {len(reports)} reports with {args.workers} workers...")

    def _run_one(idx_report):
        idx, report = idx_report
        report_id = f"synthetic:{report.get('ticker', idx)}"
        try:
            result = evaluate(
                report, mode="blend", report_id=report_id,
                log_labels=not args.dry_run,
                label_source="synthetic", label_path=args.out,
            )
            return report_id, result, None
        except Exception as exc:
            return report_id, None, exc

    decisions: Counter = Counter()
    publishable_count = 0
    scores = []
    failed = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(_run_one, item) for item in enumerate(reports)]
        for i, fut in enumerate(as_completed(futures), 1):
            report_id, result, exc = fut.result()
            if exc:
                failed += 1
                print(f"  {report_id}: FAILED ({exc})")
                continue

            decisions[result["decision"]] += 1
            jr = result.get("judge_result") or {}
            if jr.get("publishable"):
                publishable_count += 1
            if result.get("combined_score") is not None:
                scores.append(result["combined_score"])

            if i % 20 == 0 or i == len(reports):
                print(f"  {i}/{len(reports)} done ({publishable_count} publishable so far)")

    print(f"\n[opus-synth] Done in {time.time() - t0:.0f}s")
    print(f"[opus-synth] Decisions: {dict(decisions)}")
    print(f"[opus-synth] Publishable: {publishable_count}/{len(reports)} ({100*publishable_count/max(1,len(reports)):.1f}%)")
    if scores:
        print(f"[opus-synth] Scores: mean={sum(scores)/len(scores):.3f}, min={min(scores):.3f}, max={max(scores):.3f}")
    if not args.dry_run:
        print(f"[opus-synth] Labels appended to {args.out}")


if __name__ == "__main__":
    main()
