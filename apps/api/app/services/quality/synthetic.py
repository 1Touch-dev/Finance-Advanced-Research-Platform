"""
Synthetic report generator for Phase 3b classifier training data.

Why synthetic reports at all: the whole system only has ~23 real reports
(22 DB + 1 disk), and all 22 DB reports are variations on one product line
(entity_network_intel), so their rule_features barely vary - not enough
signal diversity for a classifier to learn from. This module generates
report_data dicts that DO span the rule-gate feature space, using Claude
(anthropic_client, already configured in this codebase) to author the
narrative content and deterministic mutation knobs to control the
structural properties each rule gate actually checks.

Design: text quality (Claude's job) and structural properties (citations
present/absent, duplicate paragraphs, stale dates, placeholders, arithmetic
mismatches, ...) are generated independently, then combined. This keeps the
label honest: the judge_publishable target still comes from a REAL judge
call (judge.py) against the assembled report - Claude only supplies
plausible variety in wording, never a label.
"""
from __future__ import annotations

import json
import logging
import random
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Distinct fictional entities so synthetic reports can never be confused with
# real companies in exports/quality_labels_synthetic.jsonl.
_SYNTH_ENTITIES = [
    ("Vantage Semiconductor Corp", "VNTG"), ("Northgate Biopharma Inc", "NGBP"),
    ("Cascade Robotics Holdings", "CSRB"), ("Ironclad Logistics Group", "IRNC"),
    ("Solace Renewable Power", "SLRP"), ("Ashwood Financial Holdings", "AWFH"),
    ("Redline Aerospace Systems", "RDLN"), ("Brightfield Agritech Ltd", "BRFA"),
    ("Meridian Cybersecurity Inc", "MRDN"), ("Halcyon Materials Corp", "HLCY"),
    ("Copperline Mining Co", "CPRL"), ("Fathom Subsea Networks", "FTHM"),
    ("Greywolf Defense Industries", "GRWF"), ("Lumen Optics Holdings", "LMNO"),
    ("Peregrine Data Systems", "PRGR"),
]

_QUALITY_PROMPTS: Dict[str, str] = {
    "excellent": (
        "Write a short (3-4 sentence) paragraph for a financial intelligence report's "
        "{section} section. Precise, neutral, analytical tone, like a senior equity "
        "research analyst. State concrete, well-sourced claims (e.g. 'as disclosed in "
        "the company's public SEC filings') with no hedging and no hype. Do NOT invent "
        "any specific revenue/growth numbers or dollar figures - the numeric data is "
        "supplied separately elsewhere in the report, so keep this paragraph purely "
        "qualitative/analytical. Refer to the subject only as \"the company\" - do not "
        "invent or use any specific company name."
    ),
    "thin_citation": (
        "Write a short (3-4 sentence) paragraph for a financial intelligence report's "
        "{section} section. Plausible and professional in tone. Do NOT invent any "
        "specific revenue/growth numbers or dollar figures - the numeric data is "
        "supplied separately elsewhere in the report, so keep this paragraph purely "
        "qualitative. This is for a citation-coverage test, so just write naturally, "
        "don't mention citations. Refer to the subject only as \"the company\" - do "
        "not invent or use any specific company name."
    ),
    "vague_hedging": (
        "Write a short (3-4 sentence) paragraph for a financial intelligence report's "
        "{section} section. Use vague, hedge-everything language throughout - 'may "
        "possibly', 'it could be argued', 'to some extent', 'it seems plausible that' - "
        "avoid ever committing to a concrete claim. Do NOT invent any specific revenue "
        "numbers. Refer to the subject only as \"the company\" - do not invent or use "
        "any specific company name."
    ),
    "overconfident": (
        "Write a short (3-4 sentence) paragraph for a financial intelligence report's "
        "{section} section. Use bold, unsupported, overconfident assertions with no "
        "hedging and no evidence cited - state opinions as if they were settled facts. "
        "Do NOT invent any specific revenue numbers. Refer to the subject only as \"the "
        "company\" - do not invent or use any specific company name."
    ),
    "biased": (
        "Write a short (3-4 sentence) paragraph for a financial intelligence report's "
        "{section} section. Write with an obvious negative editorial bias, implying "
        "bad motives without stating any documented fact - insinuate, don't assert. "
        "Do NOT invent any specific revenue numbers. Refer to the subject only as \"the "
        "company\" - do not invent or use any specific company name."
    ),
    "misleading": (
        "Write a short (3-4 sentence) paragraph for a financial intelligence report's "
        "{section} section. Frame the company's situation in a way that's subtly "
        "misleading about the overall trend (e.g. touting one strength while ignoring "
        "a much larger, worse issue) without stating any single fact that's outright "
        "false. Do NOT invent any specific revenue numbers - keep this qualitative. "
        "Refer to the subject only as \"the company\" - do not invent or use any "
        "specific company name."
    ),
}

_SECTIONS = ["financial performance", "insider trading activity", "recent litigation",
             "government contracts", "recent news coverage", "executive leadership"]

_STALE_HEADLINES = [
    "{entity} reports quarterly results", "{entity} announces leadership change",
    "Analysts weigh in on {entity}", "{entity} faces regulatory scrutiny",
    "{entity} expands into new market",
]


@dataclass
class MutationProfile:
    """Structural knobs, independent of narrative quality, that map directly
    onto the 10 rule gates in quality_gate_service.py."""
    citation_rate: float          # fraction of numeric claims that get a source_url
    duplicate_paragraphs: int     # count of injected exact-duplicate paragraphs
    news_staleness_days: Optional[int]  # None = no news; else days since newest article
    placeholder_count: int        # count of TBD/N/A/UNKNOWN tokens injected
    arithmetic_mismatch: bool     # segment sum vs total_revenue off by >0.5%
    fiscal_labeled: bool          # whether financial figures carry FY/Q labels
    landing_page_urls: bool       # True = bare domain URLs (fails gate), False = deep links
    named_person_sources: int     # independent source count per named person (0, 1, or 2+)
    sensitive_claim_cited: Optional[bool]  # None = no sensitive claim at all


def random_mutation_profile(rng: random.Random, tier: str = "mixed") -> MutationProfile:
    """
    `tier` correlates structural cleanliness with the tier so rule_features and
    judge_publishable actually co-vary (the whole point of distillation) while
    keeping some independent noise so the classifier can't just be a rules
    lookup table:
      "high" -> mostly clean (few/no hard failures)
      "low"  -> mostly messy (multiple hard failures)
      "mixed" -> uniform random across the full range (legacy/default behavior)
    """
    if tier == "high":
        return MutationProfile(
            citation_rate=rng.choice([0.8, 1.0, 1.0, 1.0]),
            duplicate_paragraphs=rng.choice([0, 0, 0, 2]),
            news_staleness_days=rng.choice([None, 5, 5, 45]),
            placeholder_count=rng.choice([0, 0, 0, 1]),
            arithmetic_mismatch=rng.random() < 0.08,
            fiscal_labeled=rng.random() < 0.85,
            landing_page_urls=rng.random() < 0.05,
            named_person_sources=rng.choice([0, 2, 2, 3]),
            sensitive_claim_cited=rng.choice([None, None, True]),
        )
    if tier == "low":
        return MutationProfile(
            citation_rate=rng.choice([0.0, 0.0, 0.2, 0.5]),
            duplicate_paragraphs=rng.choice([0, 2, 6, 6]),
            news_staleness_days=rng.choice([45, 120, 400, 400]),
            placeholder_count=rng.choice([1, 5, 15, 15]),
            arithmetic_mismatch=rng.random() < 0.55,
            fiscal_labeled=rng.random() < 0.3,
            landing_page_urls=rng.random() < 0.5,
            named_person_sources=rng.choice([0, 0, 1, 1]),
            sensitive_claim_cited=rng.choice([None, False, False]),
        )
    return MutationProfile(
        citation_rate=rng.choice([0.0, 0.2, 0.5, 0.8, 1.0]),
        duplicate_paragraphs=rng.choice([0, 0, 0, 2, 6]),
        news_staleness_days=rng.choice([None, 5, 45, 120, 400]),
        placeholder_count=rng.choice([0, 0, 1, 5, 15]),
        arithmetic_mismatch=rng.random() < 0.25,
        fiscal_labeled=rng.random() < 0.6,
        landing_page_urls=rng.random() < 0.2,
        named_person_sources=rng.choice([0, 0, 1, 2, 3]),
        sensitive_claim_cited=rng.choice([None, None, True, False]),
    )


# Tier -> text profile weighted choices, so "high" tier mostly (not always)
# gets excellent prose, etc. Keeping some cross-tier leakage (e.g. an
# overconfident paragraph on an otherwise-clean report) is intentional noise -
# real reports aren't perfectly bimodal either.
_TIER_TEXT_PROFILES: Dict[str, List[str]] = {
    "high": ["excellent", "excellent", "excellent", "thin_citation"],
    "low": ["overconfident", "biased", "misleading", "vague_hedging"],
    "mixed": list(_QUALITY_PROMPTS),
}


# ── fragment generation (Claude) ──────────────────────────────────────────────
def generate_fragment_bank(
    n_per_bucket: int = 6,
) -> Dict[str, List[str]]:
    """
    Calls Claude (anthropic_client) once per (quality_profile, section) combo,
    asking for `n_per_bucket` distinct paragraph variants in one shot (batched,
    not one-call-per-sample - ~30 calls total covers 6 profiles x 6 sections
    instead of hundreds of individual round-trips).

    Fragments are entity-agnostic by design ("the company", never a specific
    name) - build_synthetic_report mixes each fragment into a report for a
    DIFFERENT randomly-chosen fictional entity, so if a fragment named a
    company, the assembled report would read as incoherent ("Vantage Corp's
    filing" pasted into a Northgate Biopharma report) and the judge would
    flag that instead of the actual quality signal we want it grading.

    Returns {profile_name: [paragraph, paragraph, ...]} - flattened across
    sections since the assembler only needs prose variety per quality level,
    not section-perfect matching.
    """
    from app.services.anthropic_client import anthropic_client

    bank: Dict[str, List[str]] = {name: [] for name in _QUALITY_PROMPTS}

    if not anthropic_client.is_configured():
        logger.warning("ANTHROPIC_API_KEY not configured; fragment bank will be empty")
        return bank

    for profile_name, prompt_template in _QUALITY_PROMPTS.items():
        for section in _SECTIONS:
            batch_prompt = (
                prompt_template.format(section=section)
                + f"\n\nGenerate exactly {n_per_bucket} DIFFERENT variants of this "
                "paragraph (different wording/details each time, same style/quality "
                "level). Reply with ONLY a JSON array of strings, no other text."
            )
            try:
                res = anthropic_client.analyze_text(
                    batch_prompt,
                    system="You generate synthetic training text for a report-quality "
                           "classifier. Follow the style instruction exactly.",
                    max_tokens=1500,
                )
                text = res.get("text", "")
                match = re.search(r"\[.*\]", text, re.DOTALL)
                if match:
                    variants = json.loads(match.group(0))
                    bank[profile_name].extend(str(v) for v in variants if isinstance(v, str))
            except Exception as exc:
                logger.warning("fragment generation failed for %s/%s: %s", profile_name, section, exc)

    return bank


# ── report assembly (deterministic, no network) ──────────────────────────────
def _maybe_cite(base_url: str, idx: int, citation_rate: float, rng: random.Random) -> Dict[str, Any]:
    """Returns a dict with a numeric field + optionally a source_url, at the
    given citation rate. This is literally what CitationCoverageGate scans for.

    Uses realistic company-scale dollar figures (tens to hundreds of millions)
    - "$1,000" segment revenue reads as absurd/toy-like to the judge
    regardless of prose quality, which was silently capping every synthetic
    report's plausibility score no matter how good the narrative was."""
    row: Dict[str, Any] = {"value": rng.randint(20, 400) * 1_000_000}
    if rng.random() < citation_rate:
        row["source_url"] = f"{base_url}#item{idx}"
    return row


def build_synthetic_report(
    fragment_bank: Dict[str, List[str]],
    mutation: MutationProfile,
    rng: random.Random,
    *,
    idx: int,
    tier: str = "mixed",
) -> Dict[str, Any]:
    """
    Assemble one report_data dict (deep-research shape) from a random
    narrative fragment + the given structural mutation profile. Deterministic
    given the same rng state - no network calls here, fragment_bank is
    pre-generated once per run (see generate_fragment_bank).
    """
    entity_name, ticker = rng.choice(_SYNTH_ENTITIES)
    entity_name = f"{entity_name} #{idx}"  # keep report_ids unique across a run
    base_url = f"https://sec.gov/synthetic/{ticker.lower()}{idx}"

    profile_name = rng.choice(_TIER_TEXT_PROFILES.get(tier, list(_QUALITY_PROMPTS)))
    paragraphs = fragment_bank.get(profile_name) or []
    if paragraphs:
        narrative = rng.choice(paragraphs)
    else:
        narrative = (
            f"{entity_name} reported quarterly activity across multiple business segments, "
            "with continued investment in its core product lines and no material changes "
            "to its competitive position during the period."
        )
    # A second, independently-drawn fragment gives insider/news context extra
    # substance without contradicting the main financial narrative's numbers
    # (prompts explicitly forbid inventing figures - see _QUALITY_PROMPTS).
    context_fragment = rng.choice(paragraphs) if paragraphs else narrative

    # Financial segments: 2-3 segments, optionally citation, optionally an
    # arithmetic mismatch against total_revenue (ArithmeticReconciliationGate).
    n_segments = rng.choice([2, 3])
    segment_total = 0
    segments = []
    for i in range(n_segments):
        row = _maybe_cite(base_url, i, mutation.citation_rate, rng)
        row["name"] = f"Segment {i+1}"
        row["revenue"] = row.pop("value")
        segment_total += row["revenue"]
        segments.append(row)
    total_revenue = segment_total if not mutation.arithmetic_mismatch else int(segment_total * 1.15)

    fin_lines = [narrative]
    if mutation.placeholder_count:
        fin_lines.append(" ".join(rng.choice(["TBD", "N/A", "UNKNOWN", "$0.00"])
                                   for _ in range(mutation.placeholder_count)))

    financial_intelligence: Dict[str, Any] = {
        "total_revenue": total_revenue,
        "segments": segments,
        # Kept as ONE clean paragraph (never diluted with placeholders/dupes)
        # so report_text._financial_summary's "Analysis:" line - the only
        # thing that lets the judge see prose quality at all - reflects the
        # actual quality tier, not noise mixed in for other gates.
        "summary": "\n\n".join(fin_lines),
    }
    if mutation.duplicate_paragraphs:
        # DuplicateDetectionGate only compares SEPARATE dict entries keyed
        # text/summary/description/narrative (each >50 chars) - a single
        # bloated string can never trigger it. `notes` gives it real
        # candidates: the same paragraph repeated across distinct entries.
        financial_intelligence["notes"] = [{"text": narrative} for _ in range(mutation.duplicate_paragraphs)]
    if mutation.citation_rate > 0:
        financial_intelligence["source_url"] = base_url if not mutation.landing_page_urls else "https://sec.gov"

    data: Dict[str, Any] = {
        "entity_name": entity_name,
        "ticker": f"{ticker}{idx}",
        "financial_intelligence": financial_intelligence,
    }

    # News staleness: 0-3 articles at the configured recency.
    if mutation.news_staleness_days is not None:
        from datetime import datetime, timedelta
        article_date = (datetime.utcnow() - timedelta(days=mutation.news_staleness_days)).strftime("%Y-%m-%d")
        headline = rng.choice(_STALE_HEADLINES).format(entity=entity_name)
        data["news_intelligence"] = {"articles": [
            {"title": headline, "date": article_date, "summary": context_fragment},
        ]}

    # Named people + source diversity (NamedPersonAccuracyGate).
    if mutation.named_person_sources > 0:
        person_name = f"Executive {idx}"
        data["proxy_intelligence"] = {"executives": [{"name": person_name}]}
        if mutation.named_person_sources >= 2:
            data["board_interlocks"] = {"people": [{"name": person_name}]}
        if mutation.named_person_sources >= 3:
            txn = {"owner_name": person_name, "transaction_code": "S", "shares": rng.randint(5000, 250000),
                   "context": context_fragment}
            if rng.random() < mutation.citation_rate:
                txn["source_url"] = f"{base_url}#form4"  # keep CitationCoverageGate consistent with the tier
            data["insider_transactions"] = {"transactions": [txn]}

    # Sensitive claim, cited or not (SensitiveClaimReviewGate).
    if mutation.sensitive_claim_cited is not None:
        claim_text = f"An internal review raised concerns about possible self-dealing at {entity_name}."
        risk_flags: Dict[str, Any] = {"note": claim_text}
        if mutation.sensitive_claim_cited:
            risk_flags["source_url"] = f"{base_url}#risk"
        data["risk_flags"] = risk_flags

    return data


def generate_synthetic_reports(
    n: int,
    fragment_bank: Dict[str, List[str]],
    *,
    seed: int = 42,
    tier_weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Pure/deterministic given the same fragment_bank and seed - no network.

    `tier_weights` controls the mix of "high"/"low"/"mixed" tiers (default
    40/40/20) - correlating structural cleanliness with text-quality tier is
    what gives judge_publishable a learnable relationship with rule_features
    instead of pure noise, while "mixed" preserves cross-tier examples so the
    classifier isn't just memorizing "tier == label".
    """
    weights = tier_weights or {"high": 0.4, "low": 0.4, "mixed": 0.2}
    tiers = list(weights.keys())
    probs = list(weights.values())
    rng = random.Random(seed)
    reports = []
    for i in range(n):
        tier = rng.choices(tiers, weights=probs, k=1)[0]
        mutation = random_mutation_profile(rng, tier=tier)
        reports.append(build_synthetic_report(fragment_bank, mutation, rng, idx=i, tier=tier))
    return reports
