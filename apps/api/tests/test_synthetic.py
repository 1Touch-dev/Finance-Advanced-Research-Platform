"""
Tests for app.services.quality.synthetic (Phase 3b synthetic training data
generator) — no network dependency. generate_fragment_bank() is the only
function that calls Claude; every other function here is pure/deterministic
given a pre-supplied fragment bank, which is what these tests exercise.
"""
from __future__ import annotations

from app.services.quality_gate_service import run_quality_gates
from app.services.quality.synthetic import (
    MutationProfile,
    build_synthetic_report,
    generate_synthetic_reports,
    random_mutation_profile,
)
import random

_FAKE_BANK = {
    "excellent": ["Revenue grew 12% year over year on strong segment performance."],
    "thin_citation": ["The company reported steady results across its business lines."],
    "vague_hedging": ["It could perhaps be argued that results were somewhat mixed."],
    "overconfident": ["This company will definitely dominate its market beyond question."],
    "biased": ["Management's motives here are clearly self-serving and suspicious."],
    "misleading": ["One small segment grew nicely, ignoring much larger losses elsewhere."],
}


def test_generate_synthetic_reports_is_deterministic_given_same_seed():
    a = generate_synthetic_reports(10, _FAKE_BANK, seed=7)
    b = generate_synthetic_reports(10, _FAKE_BANK, seed=7)
    assert a == b


def test_generate_synthetic_reports_varies_with_different_seed():
    a = generate_synthetic_reports(10, _FAKE_BANK, seed=1)
    b = generate_synthetic_reports(10, _FAKE_BANK, seed=2)
    assert a != b


def test_generated_reports_have_unique_entity_names_and_tickers():
    reports = generate_synthetic_reports(20, _FAKE_BANK, seed=3)
    names = [r["entity_name"] for r in reports]
    tickers = [r["ticker"] for r in reports]
    assert len(set(names)) == len(names)
    assert len(set(tickers)) == len(tickers)


def test_generated_reports_are_shaped_like_real_deep_research_reports():
    reports = generate_synthetic_reports(5, _FAKE_BANK, seed=5)
    for r in reports:
        assert "entity_name" in r and "ticker" in r
        assert "financial_intelligence" in r
        fin = r["financial_intelligence"]
        assert "total_revenue" in fin and "segments" in fin
        # every report must be consumable by the real rule gates without raising
        result = run_quality_gates(r)
        assert "overall_score" in result and "hard_failures" in result


def test_high_tier_mutation_profile_is_structurally_cleaner_than_low_tier():
    rng_high = random.Random(1)
    rng_low = random.Random(1)
    high_profiles = [random_mutation_profile(rng_high, tier="high") for _ in range(30)]
    low_profiles = [random_mutation_profile(rng_low, tier="low") for _ in range(30)]

    avg_citation_high = sum(p.citation_rate for p in high_profiles) / len(high_profiles)
    avg_citation_low = sum(p.citation_rate for p in low_profiles) / len(low_profiles)
    assert avg_citation_high > avg_citation_low

    avg_placeholders_high = sum(p.placeholder_count for p in high_profiles) / len(high_profiles)
    avg_placeholders_low = sum(p.placeholder_count for p in low_profiles) / len(low_profiles)
    assert avg_placeholders_high < avg_placeholders_low


def test_tier_correlated_reports_produce_a_healthier_class_split_than_pure_random():
    """Regression guard for the class-imbalance bug found during manual
    verification: fully-random (uncorrelated) mutations produced ~13% clean
    (0 hard-failure) reports out of 60; tier correlation should produce a much
    larger clean fraction so judge_publishable has a learnable signal."""
    reports = generate_synthetic_reports(120, _FAKE_BANK, seed=11)
    hard_failure_counts = [len(run_quality_gates(r)["hard_failures"]) for r in reports]
    clean_fraction = sum(1 for c in hard_failure_counts if c == 0) / len(hard_failure_counts)
    assert clean_fraction > 0.25  # tier weights are 40% high / 40% low / 20% mixed


def test_build_synthetic_report_respects_explicit_mutation_profile():
    rng = random.Random(42)
    mutation = MutationProfile(
        citation_rate=1.0, duplicate_paragraphs=0, news_staleness_days=None,
        placeholder_count=0, arithmetic_mismatch=False, fiscal_labeled=True,
        landing_page_urls=False, named_person_sources=0, sensitive_claim_cited=None,
    )
    report = build_synthetic_report(_FAKE_BANK, mutation, rng, idx=0, tier="high")
    result = run_quality_gates(report)
    assert result["hard_failures"] == []


def test_generate_synthetic_reports_handles_empty_fragment_bank_without_raising():
    empty_bank = {k: [] for k in _FAKE_BANK}
    reports = generate_synthetic_reports(5, empty_bank, seed=9)
    assert len(reports) == 5
    for r in reports:
        result = run_quality_gates(r)  # must not raise even with generic fallback text
        assert "overall_score" in result
