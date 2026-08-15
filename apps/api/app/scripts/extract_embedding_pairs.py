"""
Extract (anchor, positive, hard_negative) triplets from existing reports
for contrastive fine-tuning of embedding model.

Sources:
  1. On-disk reports (apps/reports/*.json) - deep research format
  2. DB reports - if accessible via intelligence service
  3. Quality labels - for report_id to file mapping

Output: exports/embedding_triplets.jsonl

Usage:
  python -m app.scripts.extract_embedding_pairs
  python -m app.scripts.extract_embedding_pairs --min-pairs 1000 --output exports/custom_pairs.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Paths relative to apps/api/
REPORTS_DIR = Path(__file__).parent.parent.parent.parent / "reports"  # apps/reports/
REPORTS_DIR_ALT = Path(__file__).parent.parent.parent.parent.parent / "reports"  # /reports/ at root
EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"

DEFAULT_OUTPUT = EXPORTS_DIR / "embedding_triplets.jsonl"


@dataclass
class EmbeddingTriplet:
    """A training triplet for contrastive embedding learning."""
    anchor: str           # The claim or query text
    positive: str         # Semantically similar content (from same source/context)
    hard_negative: str    # Same topic/entity, different meaning (confusing but wrong)
    source: str           # Provenance: "report:{filename}:{section}"
    entity: str           # Entity name for grouping
    triplet_type: str     # Type: "financial", "contract", "news", "insider", etc.

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        """Unique ID for deduplication."""
        h = hashlib.md5((self.anchor + self.positive).encode()).hexdigest()[:12]
        return h


def _as_list(value: Any) -> List[Any]:
    """Best-effort normalization to a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        flattened: List[Any] = []
        for v in value.values():
            if isinstance(v, list):
                flattened.extend(v)
        return flattened
    return []


def _fmt_num(v: Any) -> str:
    """Format a number for readable claims."""
    if isinstance(v, (int, float)):
        if abs(v) >= 1_000_000_000:
            return f"${v/1_000_000_000:.2f}B"
        if abs(v) >= 1_000_000:
            return f"${v/1_000_000:.2f}M"
        if abs(v) >= 1000:
            return f"${v:,.0f}"
        return f"{v:.2f}" if isinstance(v, float) else str(v)
    return str(v)


def _extract_financial_triplets(
    data: Dict[str, Any],
    entity: str,
    source_base: str
) -> List[EmbeddingTriplet]:
    """
    Extract triplets from financial_intelligence section.

    Anchor: Human-readable claim about a segment/metric
    Positive: The raw data context (e.g., same segment, different phrasing)
    Hard negative: Similar metric from different segment/period
    """
    triplets = []
    fin = data.get("financial_intelligence") or {}
    if not isinstance(fin, dict):
        return triplets

    segments_data = fin.get("segments") or {}

    # Handle both dict and list formats
    segments_list = []
    if isinstance(segments_data, dict):
        # Gather all segment types
        for key in ("segments", "geographic", "markets"):
            segments_list.extend(_as_list(segments_data.get(key)))
    else:
        segments_list = _as_list(segments_data)

    # Build claims from segments
    claims = []
    for seg in segments_list:
        if not isinstance(seg, dict):
            continue
        name = seg.get("name")
        if not name:
            continue

        current = seg.get("current")
        growth = seg.get("growth_pct")
        share = seg.get("share_pct")
        line_item = seg.get("line_item", "revenue")

        # Create human-readable claim
        claim_parts = [f"{entity}'s {name} {line_item.lower()}"]
        if isinstance(current, (int, float)):
            claim_parts.append(f"was {_fmt_num(current)}")
        if isinstance(growth, (int, float)):
            claim_parts.append(f"({growth:+.1f}% YoY growth)")
        if isinstance(share, (int, float)):
            claim_parts.append(f"representing {share:.1f}% of total")

        claim = " ".join(claim_parts)

        # Raw context as positive
        raw_context = json.dumps(seg, indent=2)[:500]

        claims.append({
            "claim": claim,
            "context": raw_context,
            "category": "segment",
            "name": name,
        })

    # Generate triplets by pairing claims with hard negatives from other segments
    for i, c in enumerate(claims):
        # Find a hard negative (different segment, same entity)
        hard_neg_candidates = [
            other for j, other in enumerate(claims)
            if j != i and other["category"] == c["category"]
        ]

        if not hard_neg_candidates:
            continue

        hard_neg = random.choice(hard_neg_candidates)

        triplets.append(EmbeddingTriplet(
            anchor=c["claim"],
            positive=c["context"],
            hard_negative=hard_neg["claim"],
            source=f"{source_base}:financial:{c['name']}",
            entity=entity,
            triplet_type="financial",
        ))

    return triplets


def _extract_contract_triplets(
    data: Dict[str, Any],
    entity: str,
    source_base: str
) -> List[EmbeddingTriplet]:
    """
    Extract triplets from contract_intelligence section.

    Anchor: Contract description/summary
    Positive: Agency + amount + date context
    Hard negative: Different contract from same or similar entity
    """
    triplets = []
    contracts = data.get("contract_intelligence") or {}
    if not isinstance(contracts, dict):
        return triplets

    contract_list = _as_list(contracts.get("contracts"))

    claims = []
    for con in contract_list:
        if not isinstance(con, dict):
            continue

        desc = con.get("description", "").strip()
        if not desc or len(desc) < 20:
            continue

        agency = con.get("agency", "unknown agency")
        amount = con.get("amount")
        start = con.get("start_date", "")

        # Claim is the description
        anchor = desc[:400]

        # Positive is structured context
        context_parts = [f"Contract with {agency}"]
        if isinstance(amount, (int, float)):
            context_parts.append(f"valued at {_fmt_num(amount)}")
        if start:
            context_parts.append(f"starting {start}")
        positive = ". ".join(context_parts)

        claims.append({
            "anchor": anchor,
            "positive": positive,
            "agency": agency,
            "award_id": con.get("award_id", ""),
        })

    # Generate triplets
    for i, c in enumerate(claims):
        hard_neg_candidates = [
            other for j, other in enumerate(claims)
            if j != i
        ]

        if not hard_neg_candidates:
            continue

        hard_neg = random.choice(hard_neg_candidates)

        triplets.append(EmbeddingTriplet(
            anchor=c["anchor"],
            positive=c["positive"],
            hard_negative=hard_neg["anchor"],
            source=f"{source_base}:contract:{c['award_id']}",
            entity=entity,
            triplet_type="contract",
        ))

    return triplets


def _extract_news_triplets(
    data: Dict[str, Any],
    entity: str,
    source_base: str
) -> List[EmbeddingTriplet]:
    """
    Extract triplets from news_intelligence section.

    Anchor: Article headline/title
    Positive: Article summary/description
    Hard negative: Different article about same entity
    """
    triplets = []
    news = data.get("news_intelligence") or {}
    if not isinstance(news, dict):
        return triplets

    articles = _as_list(news.get("articles"))

    claims = []
    for art in articles:
        if not isinstance(art, dict):
            continue

        title = (art.get("title") or art.get("headline") or "").strip()
        summary = (art.get("summary") or art.get("description") or "").strip()

        if not title or not summary or len(summary) < 30:
            continue

        # Clean up HTML entities
        title = title.replace("&nbsp;", " ").replace("&amp;", "&")
        summary = summary.replace("&nbsp;", " ").replace("&amp;", "&")

        claims.append({
            "title": title[:200],
            "summary": summary[:500],
            "date": art.get("date", ""),
        })

    # Generate triplets
    for i, c in enumerate(claims):
        hard_neg_candidates = [
            other for j, other in enumerate(claims)
            if j != i
        ]

        if not hard_neg_candidates:
            continue

        hard_neg = random.choice(hard_neg_candidates)

        triplets.append(EmbeddingTriplet(
            anchor=c["title"],
            positive=c["summary"],
            hard_negative=hard_neg["title"],
            source=f"{source_base}:news:{c['date']}",
            entity=entity,
            triplet_type="news",
        ))

    return triplets


def _extract_insider_triplets(
    data: Dict[str, Any],
    entity: str,
    source_base: str
) -> List[EmbeddingTriplet]:
    """
    Extract triplets from insider_transactions section.

    Anchor: Transaction description
    Positive: Transaction details (owner, code, shares)
    Hard negative: Different transaction from same entity
    """
    triplets = []
    ins = data.get("insider_transactions") or {}
    if not isinstance(ins, dict):
        return triplets

    transactions = _as_list(ins.get("transactions"))

    claims = []
    for t in transactions:
        if not isinstance(t, dict):
            continue

        owner = t.get("owner_name", "Unknown")
        code = t.get("transaction_code", "?")
        shares = t.get("shares", 0)
        date = t.get("date", "")

        if not owner or owner == "Unknown":
            continue

        # Create anchor (human-readable description)
        code_desc = {
            "P": "purchased",
            "S": "sold",
            "A": "acquired",
            "D": "disposed of",
            "M": "exercised options for",
        }.get(code, f"transacted ({code})")

        anchor = f"{owner} {code_desc} {_fmt_num(shares)} shares of {entity}"

        # Positive: structured details
        positive = f"Insider transaction: {owner}, code {code}, {shares:,} shares"
        if date:
            positive += f", dated {date}"

        claims.append({
            "anchor": anchor,
            "positive": positive,
            "owner": owner,
        })

    # Generate triplets
    for i, c in enumerate(claims):
        hard_neg_candidates = [
            other for j, other in enumerate(claims)
            if j != i
        ]

        if not hard_neg_candidates:
            continue

        hard_neg = random.choice(hard_neg_candidates)

        triplets.append(EmbeddingTriplet(
            anchor=c["anchor"],
            positive=c["positive"],
            hard_negative=hard_neg["anchor"],
            source=f"{source_base}:insider:{c['owner']}",
            entity=entity,
            triplet_type="insider",
        ))

    return triplets


def _extract_litigation_triplets(
    data: Dict[str, Any],
    entity: str,
    source_base: str
) -> List[EmbeddingTriplet]:
    """
    Extract triplets from litigation_intelligence section.
    """
    triplets = []
    lit = data.get("litigation_intelligence") or {}
    if not isinstance(lit, dict):
        return triplets

    # Gather cases from various sub-sections
    cases: List[Dict] = []
    for key in ("federal_cases", "sec_enforcement", "ftc_proceedings",
                "doj_antitrust", "cases", "filings"):
        cases.extend(_as_list(lit.get(key)))

    claims = []
    for case in cases:
        if not isinstance(case, dict):
            continue

        name = case.get("case_name") or case.get("title") or ""
        summary = case.get("summary") or case.get("description") or ""
        court = case.get("court", "")

        if not name and not summary:
            continue

        anchor = (name or summary)[:300]
        positive = f"Legal matter"
        if court:
            positive += f" in {court}"
        if summary and summary != anchor:
            positive += f": {summary[:200]}"

        claims.append({
            "anchor": anchor,
            "positive": positive,
            "court": court,
        })

    # Generate triplets
    for i, c in enumerate(claims):
        hard_neg_candidates = [
            other for j, other in enumerate(claims)
            if j != i
        ]

        if not hard_neg_candidates:
            continue

        hard_neg = random.choice(hard_neg_candidates)

        triplets.append(EmbeddingTriplet(
            anchor=c["anchor"],
            positive=c["positive"],
            hard_negative=hard_neg["anchor"],
            source=f"{source_base}:litigation",
            entity=entity,
            triplet_type="litigation",
        ))

    return triplets


def _extract_sections_triplets(
    data: Dict[str, Any],
    entity: str,
    source_base: str
) -> List[EmbeddingTriplet]:
    """
    Extract triplets from the new 'sections' format reports.
    Each section has 'name' and 'claims' list.
    """
    triplets = []
    sections = data.get("sections") or []

    if not isinstance(sections, list):
        return triplets

    # Collect all claims across sections for cross-section negatives
    all_claims = []
    for section in sections:
        if not isinstance(section, dict):
            continue
        section_name = section.get("name", "unknown")
        claims = section.get("claims") or []

        for claim in claims:
            if not isinstance(claim, dict):
                continue
            text = claim.get("text", "").strip()
            source = claim.get("source", "")
            if text and len(text) > 30:
                all_claims.append({
                    "text": text[:500],
                    "source": source,
                    "section": section_name,
                })

    # Generate triplets from claims
    for i, claim in enumerate(all_claims):
        # Find a hard negative from a different section or different claim
        hard_neg_candidates = [
            c for j, c in enumerate(all_claims)
            if j != i and (c["section"] != claim["section"] or j > i + 2)
        ]

        if not hard_neg_candidates:
            continue

        hard_neg = random.choice(hard_neg_candidates)

        # Use claim text as anchor, source as positive context
        if claim["source"]:
            positive = f"Source: {claim['source']}. {claim['text'][:200]}"
        else:
            positive = claim["text"][:300]

        # Determine triplet type based on section name
        section_lower = claim["section"].lower()
        if "contract" in section_lower or "procurement" in section_lower:
            triplet_type = "contract"
        elif "litigation" in section_lower or "legal" in section_lower:
            triplet_type = "litigation"
        elif "lobby" in section_lower or "political" in section_lower:
            triplet_type = "lobbying"
        elif "investor" in section_lower or "capital" in section_lower:
            triplet_type = "financial"
        elif "sanction" in section_lower or "compliance" in section_lower:
            triplet_type = "compliance"
        else:
            triplet_type = "general"

        triplets.append(EmbeddingTriplet(
            anchor=claim["text"][:400],
            positive=positive[:400],
            hard_negative=hard_neg["text"][:400],
            source=f"{source_base}:sections:{claim['section']}",
            entity=entity,
            triplet_type=triplet_type,
        ))

    return triplets[:200]  # Limit per report


def extract_from_report(report_path: Path) -> List[EmbeddingTriplet]:
    """
    Extract all triplets from a single report file.
    Supports both old format (financial_intelligence, etc.) and new format (sections).
    """
    try:
        with open(report_path) as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s", report_path, e)
        return []

    entity = data.get("entity_name") or data.get("ticker") or "Unknown"
    source_base = f"report:{report_path.name}"

    triplets = []

    # Try old format first (financial_intelligence, contract_intelligence, etc.)
    triplets.extend(_extract_financial_triplets(data, entity, source_base))
    triplets.extend(_extract_contract_triplets(data, entity, source_base))
    triplets.extend(_extract_news_triplets(data, entity, source_base))
    triplets.extend(_extract_insider_triplets(data, entity, source_base))
    triplets.extend(_extract_litigation_triplets(data, entity, source_base))

    # Also try new format (sections with claims)
    triplets.extend(_extract_sections_triplets(data, entity, source_base))

    return triplets


def generate_cross_entity_negatives(
    triplets: List[EmbeddingTriplet],
    max_cross: int = 1000
) -> List[EmbeddingTriplet]:
    """
    Generate additional triplets using cross-entity hard negatives.

    These are harder negatives: same topic type, different entity.
    E.g., NVIDIA revenue claim vs MSFT revenue claim.
    """
    # Group by type
    by_type: Dict[str, List[EmbeddingTriplet]] = {}
    for t in triplets:
        by_type.setdefault(t.triplet_type, []).append(t)

    cross_triplets = []
    for ttype, group in by_type.items():
        if len(group) < 2:
            continue

        # Create cross-entity pairs
        entities = list(set(t.entity for t in group))
        if len(entities) < 2:
            continue

        for t in group[:max_cross // len(by_type)]:
            # Find a triplet from a different entity
            candidates = [
                other for other in group
                if other.entity != t.entity
            ]
            if not candidates:
                continue

            hard_neg = random.choice(candidates)

            cross_triplets.append(EmbeddingTriplet(
                anchor=t.anchor,
                positive=t.positive,
                hard_negative=hard_neg.anchor,
                source=f"{t.source}:cross",
                entity=t.entity,
                triplet_type=f"{ttype}_cross",
            ))

    return cross_triplets


def find_report_files() -> List[Path]:
    """Find all report JSON files."""
    report_files = []

    for reports_dir in [REPORTS_DIR, REPORTS_DIR_ALT]:
        if reports_dir.exists():
            for f in reports_dir.glob("*.json"):
                if "Intelligence" in f.name:
                    report_files.append(f)

    return report_files


def main():
    parser = argparse.ArgumentParser(description="Extract embedding triplets from reports")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Output JSONL file path")
    parser.add_argument("--min-pairs", type=int, default=100,
                        help="Minimum triplets to generate (will skip if fewer available)")
    parser.add_argument("--add-cross-entity", action="store_true", default=True,
                        help="Add cross-entity hard negatives")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    random.seed(args.seed)

    # Find all reports
    report_files = find_report_files()
    logger.info("Found %d report files", len(report_files))

    if not report_files:
        logger.error("No report files found. Check REPORTS_DIR paths.")
        return

    # Extract triplets from all reports
    all_triplets: List[EmbeddingTriplet] = []
    for report_path in report_files:
        triplets = extract_from_report(report_path)
        all_triplets.extend(triplets)
        logger.info("  %s: %d triplets", report_path.name, len(triplets))

    logger.info("Extracted %d base triplets", len(all_triplets))

    # Add cross-entity negatives
    if args.add_cross_entity:
        cross_triplets = generate_cross_entity_negatives(all_triplets)
        all_triplets.extend(cross_triplets)
        logger.info("Added %d cross-entity triplets, total: %d",
                    len(cross_triplets), len(all_triplets))

    # Deduplicate
    seen = set()
    unique_triplets = []
    for t in all_triplets:
        fp = t.fingerprint()
        if fp not in seen:
            seen.add(fp)
            unique_triplets.append(t)

    logger.info("After dedup: %d unique triplets", len(unique_triplets))

    if len(unique_triplets) < args.min_pairs:
        logger.warning("Only %d triplets available, below min-pairs=%d. "
                       "Need more reports to reach target.",
                       len(unique_triplets), args.min_pairs)

    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        for t in unique_triplets:
            f.write(json.dumps(t.to_dict()) + "\n")

    logger.info("Wrote %d triplets to %s", len(unique_triplets), args.output)

    # Summary by type
    by_type: Dict[str, int] = {}
    for t in unique_triplets:
        by_type[t.triplet_type] = by_type.get(t.triplet_type, 0) + 1

    logger.info("Triplets by type:")
    for ttype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        logger.info("  %s: %d", ttype, count)


if __name__ == "__main__":
    main()
