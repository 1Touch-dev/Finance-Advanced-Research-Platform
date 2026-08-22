#!/usr/bin/env python3
"""
Smoke Test Script — S0-A Demo Path Lock
========================================
Tests all critical API routes to ensure they respond without errors.
Run: python -m app.scripts.smoke_test

Exit codes:
  0 = All tests passed
  1 = Some tests failed
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dotenv
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'))


def test_service(name: str, test_fn, allow_empty: bool = False) -> Dict[str, Any]:
    """Run a single service test."""
    start = time.time()
    try:
        result = test_fn()
        elapsed = time.time() - start

        if result is None and not allow_empty:
            return {"name": name, "status": "NO_DATA", "elapsed_ms": int(elapsed * 1000)}

        return {
            "name": name,
            "status": "PASS",
            "elapsed_ms": int(elapsed * 1000),
            "sample": str(result)[:100] if result else None
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "name": name,
            "status": "FAIL",
            "elapsed_ms": int(elapsed * 1000),
            "error": str(e)[:200]
        }


def run_smoke_tests() -> List[Dict[str, Any]]:
    """Run all smoke tests."""
    results = []

    print("=" * 60)
    print("SMOKE TEST — S0-A Demo Path Lock")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # === CORE SERVICES ===
    print("\n[CORE SERVICES]")

    # 1. Politician Leaderboard
    def test_politician_leaderboard():
        from app.services.politician_leaderboard_service import get_statistics
        stats = get_statistics()
        assert stats.get("total_politicians", 0) > 0, "No politicians found"
        return stats
    results.append(test_service("politician_leaderboard", test_politician_leaderboard))
    print(f"  {results[-1]['status']}: politician_leaderboard ({results[-1]['elapsed_ms']}ms)")

    # 2. Earnings Calendar
    def test_earnings():
        from app.services.earnings_calendar_service import get_upcoming_earnings
        events = get_upcoming_earnings(days_ahead=7)
        return {"count": len(events)}
    results.append(test_service("earnings_calendar", test_earnings, allow_empty=True))
    print(f"  {results[-1]['status']}: earnings_calendar ({results[-1]['elapsed_ms']}ms)")

    # 3. Short Interest
    def test_short_interest():
        from app.services.short_interest_service import get_short_interest
        data = get_short_interest("AAPL")
        return {"ticker": data.ticker if data else None, "short_pct": data.short_percent_float if data else None}
    results.append(test_service("short_interest", test_short_interest, allow_empty=True))
    print(f"  {results[-1]['status']}: short_interest ({results[-1]['elapsed_ms']}ms)")

    # 4. IPO Calendar
    def test_ipo():
        from app.services.ipo_calendar_service import get_upcoming_ipos
        ipos = get_upcoming_ipos(days=30)
        return {"count": len(ipos)}
    results.append(test_service("ipo_calendar", test_ipo, allow_empty=True))
    print(f"  {results[-1]['status']}: ipo_calendar ({results[-1]['elapsed_ms']}ms)")

    # === GOV TRADING ===
    print("\n[GOV TRADING]")

    # 5. Gov Trading Connector
    def test_gov_trading():
        from app.connectors.gov_trading_connector import get_recent_congress_trades
        trades = get_recent_congress_trades(days=90, limit=5)
        return {"count": len(trades) if trades else 0}
    results.append(test_service("gov_trading_connector", test_gov_trading, allow_empty=True))
    print(f"  {results[-1]['status']}: gov_trading_connector ({results[-1]['elapsed_ms']}ms)")

    # 6. Leaderboard by Trades
    def test_leaderboard_trades():
        from app.services.politician_leaderboard_service import get_leaderboard_by_trades
        data = get_leaderboard_by_trades(limit=5)
        assert len(data) > 0, "No leaderboard data"
        return {"count": len(data), "first": data[0]["name"] if data else None}
    results.append(test_service("leaderboard_by_trades", test_leaderboard_trades))
    print(f"  {results[-1]['status']}: leaderboard_by_trades ({results[-1]['elapsed_ms']}ms)")

    # 7. Leaderboard by Volume
    def test_leaderboard_volume():
        from app.services.politician_leaderboard_service import get_leaderboard_by_volume
        data = get_leaderboard_by_volume(limit=5)
        return {"count": len(data)}
    results.append(test_service("leaderboard_by_volume", test_leaderboard_volume))
    print(f"  {results[-1]['status']}: leaderboard_by_volume ({results[-1]['elapsed_ms']}ms)")

    # 8. Notable Cases
    def test_notable_cases():
        from app.services.politician_leaderboard_service import get_notable_cases
        cases = get_notable_cases(limit=5)
        return {"count": len(cases)}
    results.append(test_service("notable_cases", test_notable_cases))
    print(f"  {results[-1]['status']}: notable_cases ({results[-1]['elapsed_ms']}ms)")

    # === DATA CONNECTORS ===
    print("\n[DATA CONNECTORS]")

    # 9. SEC EDGAR (check connector exists)
    def test_sec_edgar():
        from app.connectors.sec_edgar_connector import get_filer_cik, get_company_facts
        # Test with a known ticker
        cik = get_filer_cik("AAPL")
        return {"cik": cik, "has_cik_function": True}
    results.append(test_service("sec_edgar_connector", test_sec_edgar))
    print(f"  {results[-1]['status']}: sec_edgar_connector ({results[-1]['elapsed_ms']}ms)")

    # 10. Financial News
    def test_financial_news():
        from app.connectors.financial_news_connector import finnhub_quote
        quote = finnhub_quote("AAPL")
        return quote
    results.append(test_service("finnhub_quote", test_financial_news, allow_empty=True))
    print(f"  {results[-1]['status']}: finnhub_quote ({results[-1]['elapsed_ms']}ms)")

    # === QUALITY SERVICES ===
    print("\n[QUALITY SERVICES]")

    # 11. Quality Classifier
    def test_quality_classifier():
        from app.services.quality.classifier import get_classifier
        clf = get_classifier()
        return {"loaded": clf is not None}
    results.append(test_service("quality_classifier", test_quality_classifier, allow_empty=True))
    print(f"  {results[-1]['status']}: quality_classifier ({results[-1]['elapsed_ms']}ms)")

    # 12. RAG Retriever
    def test_rag():
        from app.services.rag.retriever import retrieve
        # Just verify the function exists and is importable
        return {"retrieve_function": retrieve is not None}
    results.append(test_service("rag_retriever", test_rag, allow_empty=True))
    print(f"  {results[-1]['status']}: rag_retriever ({results[-1]['elapsed_ms']}ms)")

    return results


def print_summary(results: List[Dict[str, Any]]) -> int:
    """Print test summary and return exit code."""
    print("\n" + "=" * 60)
    print("SMOKE TEST SUMMARY")
    print("=" * 60)

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    no_data = [r for r in results if r["status"] == "NO_DATA"]

    print(f"\n✅ PASSED: {len(passed)}/{len(results)}")
    print(f"❌ FAILED: {len(failed)}/{len(results)}")
    print(f"📭 NO_DATA: {len(no_data)}/{len(results)}")

    if failed:
        print("\n❌ FAILED TESTS:")
        for r in failed:
            print(f"  - {r['name']}: {r.get('error', 'Unknown error')}")

    if no_data:
        print("\n📭 NO DATA TESTS:")
        for r in no_data:
            print(f"  - {r['name']}")

    total_time = sum(r["elapsed_ms"] for r in results)
    print(f"\nTotal time: {total_time}ms")
    print(f"Average: {total_time // len(results)}ms per test")

    # Write results to JSON
    output_path = os.path.join(os.path.dirname(__file__), "smoke_test_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(results),
                "passed": len(passed),
                "failed": len(failed),
                "no_data": len(no_data)
            },
            "results": results
        }, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    results = run_smoke_tests()
    exit_code = print_summary(results)
    sys.exit(exit_code)
