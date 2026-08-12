"""
Tests for app.services.quality — no network dependency (LLM calls mocked).

Covers:
  - flattener is pure/deterministic and handles both report shapes
  - judge parses well-formed JSON and normalizes scores correctly
  - judge fail-soft: no API key -> ok=False, no key -> never raises
  - judge pre-screen: banned content forces publishable=False
  - blend respects rules-veto: a hard-fail input is blocked regardless of judge score
  - blend degrades to rules when judge is unavailable
  - rules mode is unchanged / independent of judge availability
  - label logging writes a valid JSONL line with expected fields
"""
import json

import pytest

from app.services.quality import decision, judge as judge_mod, labels
from app.services.quality.judge import JudgeVerdict, judge_report
from app.services.quality.report_text import flatten_report

DEEP_RESEARCH_REPORT = {
    "entity_name": "Acme Corp",
    "ticker": "ACME",
    "financial_intelligence": {
        "total_revenue": 1000000000,
        "source_url": "https://sec.gov/acme/10k",
        "segments": [{"name": "Core", "revenue": 1000000000, "source_url": "https://sec.gov/acme/10k#seg"}],
    },
    "insider_transactions": {
        "transactions": [{"owner_name": "Jane Doe", "transaction_code": "S", "shares": 1000,
                           "source_url": "https://sec.gov/form4/acme"}],
    },
    "proxy_intelligence": {"executives": [{"name": "Jane Doe"}]},
    "board_interlocks": {"people": [{"name": "Jane Doe"}]},
}

DB_SHAPE_REPORT = {
    "entity_name": "DB Corp",
    "title": "Intelligence Report: DB Corp",
    "summary": "DB Corp reported strong quarterly growth.",
    "sections": [{"name": "Overview", "content": "Revenue grew 10% year over year.", "order": 0}],
    "claims": [{"text": "Revenue grew 10%", "status": "verified"}],
}

HARD_FAIL_REPORT = {
    "entity_name": "Uncited Co",
    "ticker": "UNCT",
    "financial_intelligence": {"total_revenue": 500000000, "segments": [{"name": "Core", "revenue": 500000000}]},
}

BANNED_CONTENT_REPORT = {
    "entity_name": "Advice Co",
    "ticker": "ADVC",
    "financial_intelligence": {
        "total_revenue": 100000000,
        "source_url": "https://sec.gov/advc/10k",
        "segments": [{"name": "Core", "revenue": 100000000, "source_url": "https://sec.gov/advc/10k#seg"}],
    },
    "news_intelligence": {"articles": [{"title": "Analysts say you should buy this stock now, guaranteed returns", "date": "2026-08-01"}]},
}


# ── flattener ────────────────────────────────────────────────────────────────
def test_flatten_report_is_pure_and_deterministic():
    a = flatten_report(DEEP_RESEARCH_REPORT)
    b = flatten_report(DEEP_RESEARCH_REPORT)
    assert a == b
    assert "Acme Corp" in a
    assert "ACME" in a


def test_flatten_report_handles_deep_research_shape():
    digest = flatten_report(DEEP_RESEARCH_REPORT)
    assert "FINANCIALS" in digest
    assert "INSIDER ACTIVITY" in digest
    assert "1,000,000,000" in digest


def test_flatten_report_handles_db_shape():
    digest = flatten_report(DB_SHAPE_REPORT)
    assert "DB Corp" in digest
    assert "SUMMARY" in digest
    assert "SECTION - Overview" in digest
    assert "CLAIMS SAMPLE" in digest


def test_flatten_report_truncates_to_char_budget():
    big = {
        "entity_name": "Big Corp",
        "sections": [{"name": f"Section{i}", "content": "y" * 1100, "order": i} for i in range(12)],
    }
    digest = flatten_report(big, char_budget=2000)
    assert len(digest) <= 2050  # small allowance for the truncation marker
    assert "truncated" in digest


def test_flatten_report_empty_or_invalid_input():
    assert flatten_report({}) != ""  # still gets an ENTITY header
    assert flatten_report(None) == ""
    assert flatten_report("not a dict") == ""


def test_flatten_report_detects_sensitive_claims():
    data = {"entity_name": "X", "risk_flags": {"note": "Alleged insider trading scheme uncovered by regulators."}}
    digest = flatten_report(data)
    assert "SENSITIVE CLAIMS" in digest


# ── judge: fail-soft ─────────────────────────────────────────────────────────
def test_judge_fail_soft_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    verdict = judge_report(DEEP_RESEARCH_REPORT)
    assert verdict.ok is False
    assert verdict.score is None
    assert "OPENAI_API_KEY" in verdict.error


def test_judge_never_raises_on_llm_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    def boom(digest, model):
        raise RuntimeError("network blip")
    monkeypatch.setattr(judge_mod, "_call_llm_once", boom)
    verdict = judge_report(DEEP_RESEARCH_REPORT)
    assert verdict.ok is False
    assert "network blip" in verdict.error


def test_judge_empty_digest_is_fail_soft():
    verdict = judge_report({})
    # entity header always present, so digest is non-empty; use a payload
    # that truly flattens to nothing.
    verdict2 = judge_report(None)
    assert verdict2.ok is False


# ── judge: parses well-formed JSON ────────────────────────────────────────────
def test_judge_parses_well_formed_json(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    fake_response = {
        "quality_score": 4,
        "publishable": True,
        "dimensions": {"accuracy": 4, "citations": 5, "clarity": 3, "relevance": 4, "neutrality": 5},
        "issues": ["minor: could cite more sources"],
        "reasoning": "Well-structured and mostly well-cited.",
    }
    monkeypatch.setattr(judge_mod, "_call_llm_once", lambda digest, model: fake_response)
    verdict = judge_report(DEEP_RESEARCH_REPORT)
    assert verdict.ok is True
    assert verdict.score == pytest.approx((4 - 1) / 4, abs=1e-4)
    assert verdict.publishable is True
    assert verdict.dimensions["citations"] == pytest.approx(1.0)
    assert verdict.dimensions["clarity"] == pytest.approx(0.5)
    assert verdict.issues == ["minor: could cite more sources"]


def test_judge_self_consistency_averages_samples(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setattr(judge_mod, "_JUDGE_SAMPLES", 2)
    responses = iter([
        {"quality_score": 3, "publishable": True, "dimensions": {}, "issues": ["a"], "reasoning": "r1"},
        {"quality_score": 5, "publishable": True, "dimensions": {}, "issues": ["b"], "reasoning": "r2"},
    ])
    monkeypatch.setattr(judge_mod, "_call_llm_once", lambda digest, model: next(responses))
    verdict = judge_report(DEEP_RESEARCH_REPORT)
    assert verdict.ok is True
    # average of (3-1)/4=0.5 and (5-1)/4=1.0 -> 0.75
    assert verdict.score == pytest.approx(0.75, abs=1e-4)
    assert set(verdict.issues) == {"a", "b"}


def test_judge_pre_screen_forces_not_publishable(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    fake_response = {
        "quality_score": 5, "publishable": True, "dimensions": {}, "issues": [], "reasoning": "looks fine",
    }
    monkeypatch.setattr(judge_mod, "_call_llm_once", lambda digest, model: fake_response)
    verdict = judge_report(BANNED_CONTENT_REPORT)
    assert verdict.pre_screen_flags  # banned output pattern caught
    assert verdict.publishable is False  # overridden despite judge saying True


# ── decision layer ────────────────────────────────────────────────────────────
def test_decision_rules_mode_unaffected_by_judge_availability(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = decision.evaluate(DEEP_RESEARCH_REPORT, mode="rules", log_labels=False)
    assert result["decision"] == "publication_ready"
    assert result["judge_result"] is None


def test_decision_blend_respects_rules_veto_regardless_of_judge_score(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    fake_response = {
        "quality_score": 5, "publishable": True,
        "dimensions": {"accuracy": 5, "citations": 5, "clarity": 5, "relevance": 5, "neutrality": 5},
        "issues": [], "reasoning": "excellent",
    }
    monkeypatch.setattr(judge_mod, "_call_llm_once", lambda digest, model: fake_response)
    result = decision.evaluate(HARD_FAIL_REPORT, mode="blend", log_labels=False)
    assert result["decision"] == "blocked"  # rules veto wins even though judge gave a perfect score


def test_decision_blend_degrades_to_rules_when_judge_unavailable(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = decision.evaluate(DEEP_RESEARCH_REPORT, mode="blend", log_labels=False)
    assert result["judge_result"]["ok"] is False
    assert result["decision"] == "publication_ready"
    assert result["combined_score"] == result["rule_result"]["overall_score"]


def test_decision_blend_combines_scores_when_judge_available(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    fake_response = {
        "quality_score": 3, "publishable": True, "dimensions": {}, "issues": [], "reasoning": "ok",
    }
    monkeypatch.setattr(judge_mod, "_call_llm_once", lambda digest, model: fake_response)
    result = decision.evaluate(DEEP_RESEARCH_REPORT, mode="blend", log_labels=False)
    rule_score = result["rule_result"]["overall_score"]
    judge_score = (3 - 1) / 4
    expected = round(decision._BLEND_RULE_WEIGHT * rule_score + decision._BLEND_JUDGE_WEIGHT * judge_score, 4)
    assert result["combined_score"] == expected


def test_decision_unknown_mode_defaults_to_rules(monkeypatch):
    result = decision.evaluate(DEEP_RESEARCH_REPORT, mode="bogus", log_labels=False)
    assert result["mode"] == "rules"


# ── label logging ─────────────────────────────────────────────────────────────
def test_log_judgment_writes_valid_jsonl_line(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    fake_response = {
        "quality_score": 4, "publishable": True,
        "dimensions": {"accuracy": 4}, "issues": ["x"], "reasoning": "fine",
    }
    monkeypatch.setattr(judge_mod, "_call_llm_once", lambda digest, model: fake_response)
    verdict = judge_report(DEEP_RESEARCH_REPORT)
    from app.services.quality_gate_service import run_quality_gates
    rule_result = run_quality_gates(DEEP_RESEARCH_REPORT)

    label_path = tmp_path / "quality_labels.jsonl"
    labels.log_judgment(DEEP_RESEARCH_REPORT, rule_result, verdict, report_id="test-1", path=label_path)

    lines = label_path.read_text().strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["report_id"] == "test-1"
    assert row["judge_score"] == verdict.score
    assert row["judge_publishable"] is True
    assert "overall_score" in row["rule_features"]
    assert row["rule_pass"] is True


def test_log_judgment_never_raises_on_bad_path(monkeypatch):
    from app.services.quality_gate_service import run_quality_gates
    rule_result = run_quality_gates(DEEP_RESEARCH_REPORT)
    # An impossible path (root-owned, nonexistent drive-ish) should be
    # swallowed, not raised.
    import pathlib
    bad_path = pathlib.Path("/this/path/does/not/exist/labels.jsonl")
    labels.log_judgment(DEEP_RESEARCH_REPORT, rule_result, None, report_id="x", path=bad_path)  # must not raise


def test_log_judgment_respects_env_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("QUALITY_LABEL_LOG", "off")
    from app.services.quality_gate_service import run_quality_gates
    rule_result = run_quality_gates(DEEP_RESEARCH_REPORT)
    label_path = tmp_path / "quality_labels.jsonl"
    labels.log_judgment(DEEP_RESEARCH_REPORT, rule_result, None, report_id="x", path=label_path)
    assert not label_path.exists()


def test_decision_evaluate_logs_labels_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path))
    monkeypatch.setattr(labels, "_LABELS_PATH", tmp_path / "quality_labels.jsonl")
    fake_response = {"quality_score": 4, "publishable": True, "dimensions": {}, "issues": [], "reasoning": "ok"}
    monkeypatch.setattr(judge_mod, "_call_llm_once", lambda digest, model: fake_response)
    decision.evaluate(DEEP_RESEARCH_REPORT, mode="judge", report_id="auto-1")
    label_file = tmp_path / "quality_labels.jsonl"
    assert label_file.exists()
    row = json.loads(label_file.read_text().strip().splitlines()[-1])
    assert row["report_id"] == "auto-1"
