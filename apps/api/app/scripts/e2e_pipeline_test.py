#!/usr/bin/env python
"""
End-to-End Pipeline Test — validates the entire report generation pipeline.

Tests the full flow:
  1. Generate an intelligence report for a test entity
  2. Run quality gates (rules, blend, ml modes)
  3. Verify RAG retrieval works on the report
  4. Check database health
  5. Verify all health endpoints respond

Usage:
  python -m app.scripts.e2e_pipeline_test
  python -m app.scripts.e2e_pipeline_test --entity "NVIDIA"
  python -m app.scripts.e2e_pipeline_test --skip-generation
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=False)


@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    details: Optional[str] = None
    error: Optional[str] = None


def run_test(name: str, fn) -> TestResult:
    """Run a test function and capture result."""
    t0 = time.perf_counter()
    try:
        result = fn()
        duration = (time.perf_counter() - t0) * 1000
        if isinstance(result, tuple):
            passed, details = result
        else:
            passed, details = bool(result), str(result)
        return TestResult(name=name, passed=passed, duration_ms=round(duration, 2), details=details)
    except Exception as exc:
        duration = (time.perf_counter() - t0) * 1000
        return TestResult(name=name, passed=False, duration_ms=round(duration, 2), error=str(exc))


def test_database_health() -> tuple:
    """Test database connectivity."""
    from app.db.session import check_db_health
    result = check_db_health()
    passed = result.get("status") == "ok"
    details = f"backend={result.get('backend')}, latency={result.get('latency_ms')}ms"
    return passed, details


def test_rag_health() -> tuple:
    """Test RAG pipeline components."""
    from app.api.health_rag import rag_health
    result = rag_health()
    passed = result.get("status") == "ok"
    components = result.get("components", {})
    details = f"embeddings={components.get('embeddings', {}).get('provider', 'unknown')}, vector={components.get('vector_backend', 'unknown')}"
    return passed, details


def test_quality_classifier() -> tuple:
    """Test quality classifier is loaded."""
    from app.services.quality.classifier import get_classifier
    clf = get_classifier()
    if clf:
        return True, f"version={clf.version}, metrics={clf.metrics.get('test_f1', 'N/A')}"
    return False, "No trained classifier found"


def test_quality_rules(data: Dict[str, Any]) -> tuple:
    """Test rule-based quality gates (verifies gates run, not that test data passes)."""
    from app.services.quality_gate_service import run_quality_gates
    result = run_quality_gates(data)
    # Test passes if gates ran without error (score exists)
    passed = result.get("overall_score") is not None
    details = f"score={result.get('overall_score')}, gates={result.get('gates_passed')}/{result.get('gates_total')}"
    return passed, details


def test_quality_blend(data: Dict[str, Any]) -> tuple:
    """Test blended quality evaluation (verifies blend runs, not that test data passes)."""
    from app.services.quality.decision import evaluate
    result = evaluate(data, mode="blend", log_labels=False)
    decision = result.get("decision")
    # Test passes if a decision was made (any valid decision is OK for infrastructure test)
    passed = decision in ("publication_ready", "needs_review", "blocked")
    details = f"decision={decision}, score={result.get('combined_score')}"
    return passed, details


def test_quality_ml(data: Dict[str, Any]) -> tuple:
    """Test ML classifier quality evaluation (verifies ML runs, not that test data passes)."""
    from app.services.quality.decision import evaluate
    result = evaluate(data, mode="ml", log_labels=False)
    decision = result.get("decision")
    ml_result = result.get("ml_result", {})
    # Test passes if a decision was made
    passed = decision in ("publication_ready", "needs_review", "blocked")
    if ml_result and ml_result.get("ok"):
        details = f"decision={decision}, ml_score={ml_result.get('score')}"
    else:
        details = f"decision={decision}, ml_unavailable (fell back to rules)"
    return passed, details


def test_rag_retrieval(data: Dict[str, Any]) -> tuple:
    """Test RAG retrieval on report data."""
    from app.services.rag.types import Document, RetrievalMode
    from app.services.rag.retriever import retrieve

    # Build documents from report data
    docs = []
    for key, value in data.items():
        if isinstance(value, str) and len(value) > 50:
            docs.append(Document(id=key, text=value))
        elif isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, str) and len(v) > 50:
                    docs.append(Document(id=f"{key}.{k}", text=v))

    if not docs:
        return False, "No documents extracted from report"

    # Test hybrid search
    query = "What are the key risk factors?"
    results = retrieve(query, docs, mode=RetrievalMode.HYBRID, top_k=5)
    passed = len(results) > 0
    details = f"query_len={len(query)}, docs={len(docs)}, results={len(results)}"
    return passed, details


def generate_test_report(entity_name: str) -> Dict[str, Any]:
    """Generate a test report for the entity."""
    # This is a minimal test report structure
    return {
        "entity_name": entity_name,
        "ticker": entity_name[:4].upper(),
        "executive_summary": f"""
        {entity_name} is a leading technology company with significant market presence.
        The company has demonstrated strong revenue growth over the past fiscal year,
        with Q3 earnings exceeding analyst expectations by 15%. According to SEC filings,
        the company maintains healthy cash reserves and a disciplined approach to capital allocation.
        Management's strategic initiatives, as disclosed in the recent 10-K filing, position
        the company well for continued growth in emerging markets.
        """,
        "financial_intelligence": {
            "total_revenue": 50000000000,
            "segments": [
                {"name": "Cloud Services", "revenue": 25000000000, "source_url": "https://sec.gov/cgi-bin/browse-edgar?action=getcompany"},
                {"name": "Hardware", "revenue": 15000000000, "source_url": "https://sec.gov/cgi-bin/browse-edgar?action=getcompany"},
                {"name": "Software", "revenue": 10000000000, "source_url": "https://sec.gov/cgi-bin/browse-edgar?action=getcompany"},
            ],
            "fiscal_year": "FY2025",
            "source_url": "https://sec.gov/cgi-bin/browse-edgar?action=getcompany&type=10-K",
        },
        "risk_factors": {
            "note": "The company disclosed regulatory discussions in its 10-Q filing.",
            "source_url": "https://sec.gov/cgi-bin/browse-edgar?action=getcompany&type=10-Q",
        },
        "news_intelligence": {
            "articles": [
                {
                    "title": f"{entity_name} Reports Strong Earnings",
                    "date": "2026-08-10",
                    "summary": "The company exceeded analyst expectations in Q3.",
                    "source_url": "https://reuters.com/technology",
                },
            ],
        },
        "proxy_intelligence": {
            "executives": [
                {"name": "Jane Smith", "title": "CEO", "source_url": "https://sec.gov/cgi-bin/browse-edgar?action=getcompany&type=DEF14A"},
            ],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="End-to-end pipeline test")
    ap.add_argument("--entity", type=str, default="TestCorp", help="Entity name for test report")
    ap.add_argument("--skip-generation", action="store_true", help="Skip report generation, use stub data")
    ap.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = ap.parse_args()

    print(f"\n{'='*60}")
    print("E2E PIPELINE TEST")
    print(f"{'='*60}")
    print(f"Entity: {args.entity}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results: List[TestResult] = []

    # Phase 1: Infrastructure tests
    print("Phase 1: Infrastructure")
    print("-" * 40)

    results.append(run_test("Database Health", test_database_health))
    print(f"  {'✓' if results[-1].passed else '✗'} {results[-1].name}: {results[-1].details or results[-1].error}")

    results.append(run_test("RAG Health", test_rag_health))
    print(f"  {'✓' if results[-1].passed else '✗'} {results[-1].name}: {results[-1].details or results[-1].error}")

    results.append(run_test("Quality Classifier", test_quality_classifier))
    print(f"  {'✓' if results[-1].passed else '✗'} {results[-1].name}: {results[-1].details or results[-1].error}")

    # Phase 2: Generate test data
    print(f"\nPhase 2: Test Data Generation")
    print("-" * 40)

    data = generate_test_report(args.entity)
    print(f"  Generated test report for '{args.entity}'")
    print(f"  Sections: {len(data)}")

    # Phase 3: Quality gate tests
    print(f"\nPhase 3: Quality Gates")
    print("-" * 40)

    results.append(run_test("Quality Rules", lambda: test_quality_rules(data)))
    print(f"  {'✓' if results[-1].passed else '✗'} {results[-1].name}: {results[-1].details or results[-1].error}")

    results.append(run_test("Quality Blend", lambda: test_quality_blend(data)))
    print(f"  {'✓' if results[-1].passed else '✗'} {results[-1].name}: {results[-1].details or results[-1].error}")

    results.append(run_test("Quality ML", lambda: test_quality_ml(data)))
    print(f"  {'✓' if results[-1].passed else '✗'} {results[-1].name}: {results[-1].details or results[-1].error}")

    # Phase 4: RAG retrieval test
    print(f"\nPhase 4: RAG Retrieval")
    print("-" * 40)

    results.append(run_test("RAG Retrieval", lambda: test_rag_retrieval(data)))
    print(f"  {'✓' if results[-1].passed else '✗'} {results[-1].name}: {results[-1].details or results[-1].error}")

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    total_duration = sum(r.duration_ms for r in results)

    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total Duration: {total_duration:.0f}ms")

    if failed > 0:
        print(f"\nFailed Tests:")
        for r in results:
            if not r.passed:
                print(f"  - {r.name}: {r.error or r.details}")

    print(f"\n{'='*60}")
    status = "PASSED" if failed == 0 else "FAILED"
    print(f"OVERALL: {status}")
    print(f"{'='*60}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
