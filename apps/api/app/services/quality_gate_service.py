"""
Quality Gate Battery Service (P0-14)
────────────────────────────────────────────────────────────────────────────────
Ten validation gates that determine whether a report meets publication standards.
This is what separates a template from a reference-quality intelligence report.

Gates:
  1. Citation coverage — ≥95% of numeric blocks have source URLs
  2. Arithmetic reconciliation — segment sums, totals tie within ±0.5%
  3. Duplicate detection — Jaccard >0.85 between paragraphs fails
  4. News staleness — newest item ≤90 days; window ≤24 months
  5. Directionality lint — lower-is-better metrics never marked "below average"
  6. Placeholder scan — reject "TBD", "N/A", "$0.00", "UNKNOWN", etc.
  7. Fiscal-basis lint — every figure carries FY/Q label
  8. Landing-page ban — deep document URLs only
  9. Named-person accuracy — ≥2 independent sources per named person
  10. Sensitive-claim review — documented facts only, no asserted motive

Usage:
    from app.services.quality_gate_service import run_quality_gates
    result = run_quality_gates(report_data)
    if not result["passed"]:
        print(f"Report failed {len(result['failures'])} gates")
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Set, Tuple, Optional
from collections import Counter

logger = logging.getLogger(__name__)

# ── Gate Configuration ────────────────────────────────────────────────────────

PLACEHOLDER_PATTERNS = [
    r"\bTBD\b", r"\bN/A\b", r"\bUNKNOWN\b", r"\bPENDING\b",
    r"\$0\.00(?!\d)", r"\$0(?!\d)", r"should be evaluated",
    r"to be determined", r"data unavailable", r"not available",
    r"placeholder", r"XXX", r"\[insert\]", r"\[TODO\]",
]

LANDING_PAGE_PATTERNS = [
    r"sec\.gov/?$", r"sec\.gov/cgi-bin/browse-edgar\?action=getcompany",
    r"usaspending\.gov/?$", r"opensecrets\.org/?$", r"lda\.senate\.gov/?$",
    r"courtlistener\.com/?$", r"ftc\.gov/enforcement/?$",
]

# Metrics where lower is better — should never be flagged as "below average"
LOWER_IS_BETTER = {
    "debt_to_equity", "d/e", "debt/equity", "leverage",
    "dso", "days_sales_outstanding", "days sales outstanding",
    "dsi", "days_inventory", "days inventory",
    "dpo", "days_payable", "accounts_payable_days",
    "employee_turnover", "churn", "attrition",
    "short_interest", "cost_of_capital", "wacc",
}

# Sensitive claim patterns that need verification
SENSITIVE_PATTERNS = [
    r"fraud", r"insider trading", r"manipulation", r"embezzlement",
    r"brib(e|ery)", r"kickback", r"self-dealing", r"money laundering",
    r"tax evasion", r"shell company", r"siphon", r"misappropriat",
]


class QualityGate:
    """Base class for quality gates."""

    def __init__(self, name: str, threshold: float = 0.0, hard_fail: float = 0.0):
        self.name = name
        self.threshold = threshold
        self.hard_fail = hard_fail

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the gate check. Returns result dict."""
        raise NotImplementedError


class CitationCoverageGate(QualityGate):
    """Gate 1: ≥95% of numeric blocks have source URLs."""

    def __init__(self):
        super().__init__("Citation Coverage", threshold=0.95, hard_fail=0.90)

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        total_numeric = 0
        cited_numeric = 0

        def scan_for_citations(obj, depth=0):
            nonlocal total_numeric, cited_numeric
            if depth > 10:
                return

            if isinstance(obj, dict):
                # Check if this is a numeric claim with potential citation
                has_numeric = False
                has_citation = False

                for key, value in obj.items():
                    if isinstance(value, (int, float)) and key not in ("depth", "level", "id"):
                        has_numeric = True
                    if key in ("source_url", "url", "source", "citation", "filing_url"):
                        if value and str(value).startswith("http"):
                            has_citation = True
                    scan_for_citations(value, depth + 1)

                if has_numeric:
                    total_numeric += 1
                    if has_citation:
                        cited_numeric += 1

            elif isinstance(obj, list):
                for item in obj:
                    scan_for_citations(item, depth + 1)

        scan_for_citations(data)

        coverage = cited_numeric / total_numeric if total_numeric > 0 else 1.0

        return {
            "gate": self.name,
            "passed": coverage >= self.threshold,
            "hard_fail": coverage < self.hard_fail,
            "score": coverage,
            "threshold": self.threshold,
            "detail": f"{cited_numeric}/{total_numeric} numeric blocks have citations ({coverage:.1%})",
        }


class ArithmeticReconciliationGate(QualityGate):
    """Gate 2: Segment sums, totals tie within ±0.5%."""

    def __init__(self):
        super().__init__("Arithmetic Reconciliation", threshold=0.995)

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        errors = []

        # Check financial segment sums
        fin_data = data.get("financial_intelligence", {})
        segments = fin_data.get("segments", [])
        if segments:
            segment_total = sum(s.get("revenue", 0) or 0 for s in segments)
            reported_total = fin_data.get("total_revenue", 0) or 0
            if reported_total > 0:
                diff = abs(segment_total - reported_total) / reported_total
                if diff > 0.005:
                    errors.append(f"Segment revenue ({segment_total:,.0f}) differs from total ({reported_total:,.0f}) by {diff:.1%}")

        # Check insider transaction totals
        insider_data = data.get("insider_transactions", {})
        transactions = insider_data.get("transactions", [])
        if transactions:
            computed_acquired = sum(t.get("shares", 0) or 0 for t in transactions if t.get("transaction_code") in ("P", "A"))
            computed_disposed = sum(t.get("shares", 0) or 0 for t in transactions if t.get("transaction_code") in ("S", "D"))
            summary = insider_data.get("summary", {})
            reported_acquired = summary.get("total_acquired", 0) or 0
            reported_disposed = summary.get("total_disposed", 0) or 0

            if reported_acquired > 0:
                diff = abs(computed_acquired - reported_acquired) / reported_acquired if reported_acquired else 0
                if diff > 0.005:
                    errors.append(f"Insider acquisitions don't reconcile: computed {computed_acquired:,} vs reported {reported_acquired:,}")

        # Check contract totals
        contract_data = data.get("contract_intelligence", {})
        contracts = contract_data.get("contracts", [])
        if contracts:
            computed_total = sum(c.get("obligated_amount", 0) or 0 for c in contracts)
            reported_total = contract_data.get("total_obligated", 0) or 0
            if reported_total > 0:
                diff = abs(computed_total - reported_total) / reported_total
                if diff > 0.005:
                    errors.append(f"Contract totals don't reconcile: computed {computed_total:,.0f} vs reported {reported_total:,.0f}")

        passed = len(errors) == 0
        return {
            "gate": self.name,
            "passed": passed,
            "hard_fail": len(errors) > 3,
            "score": 1.0 if passed else 0.0,
            "threshold": self.threshold,
            "detail": "; ".join(errors) if errors else "All totals reconcile within ±0.5%",
            "errors": errors,
        }


class DuplicateDetectionGate(QualityGate):
    """Gate 3: Jaccard similarity >0.85 between paragraphs fails."""

    def __init__(self):
        super().__init__("Duplicate Detection", threshold=0.85)

    def _jaccard(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        paragraphs = []

        def extract_text(obj, depth=0):
            if depth > 10:
                return
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("text", "summary", "description", "narrative") and isinstance(value, str):
                        if len(value) > 50:  # Only check substantial text
                            paragraphs.append(value)
                    extract_text(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    extract_text(item, depth + 1)

        extract_text(data)

        duplicates = []
        for i, p1 in enumerate(paragraphs):
            for j, p2 in enumerate(paragraphs[i+1:], i+1):
                similarity = self._jaccard(p1, p2)
                if similarity > self.threshold:
                    duplicates.append((i, j, similarity, p1[:50], p2[:50]))

        passed = len(duplicates) == 0
        return {
            "gate": self.name,
            "passed": passed,
            "hard_fail": len(duplicates) > 5,
            "score": 1.0 if passed else 1.0 - (len(duplicates) / max(len(paragraphs), 1)),
            "threshold": self.threshold,
            "detail": f"Found {len(duplicates)} duplicate paragraphs" if duplicates else "No duplicate paragraphs detected",
            "duplicates": [(d[3], d[4], f"{d[2]:.1%}") for d in duplicates[:5]],
        }


class NewsStalenessGate(QualityGate):
    """Gate 4: Newest item ≤90 days; window ≤24 months."""

    def __init__(self):
        super().__init__("News Staleness", threshold=90)

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        news_data = data.get("news_intelligence", {})
        articles = news_data.get("articles", [])

        if not articles:
            return {
                "gate": self.name,
                "passed": True,
                "hard_fail": False,
                "score": 1.0,
                "threshold": self.threshold,
                "detail": "No news articles to check",
            }

        now = datetime.utcnow()
        dates = []

        for article in articles:
            date_str = article.get("date") or article.get("published") or ""
            if date_str:
                try:
                    if "T" in date_str:
                        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    dates.append(date.replace(tzinfo=None))
                except:
                    pass

        if not dates:
            return {
                "gate": self.name,
                "passed": True,
                "hard_fail": False,
                "score": 0.5,
                "threshold": self.threshold,
                "detail": "Could not parse news dates",
            }

        newest = max(dates)
        oldest = min(dates)
        days_since_newest = (now - newest).days
        window_months = (newest - oldest).days / 30

        passed = days_since_newest <= 90 and window_months <= 24
        return {
            "gate": self.name,
            "passed": passed,
            "hard_fail": days_since_newest > 180,
            "score": 1.0 if passed else 0.5,
            "threshold": self.threshold,
            "detail": f"Newest article: {days_since_newest} days ago; window: {window_months:.1f} months",
            "newest_date": newest.isoformat() if newest else None,
            "oldest_date": oldest.isoformat() if oldest else None,
        }


class DirectionalityLintGate(QualityGate):
    """Gate 5: Lower-is-better metrics never marked 'below average'."""

    def __init__(self):
        super().__init__("Directionality Lint")

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        violations = []

        def scan_for_violations(obj, path="", depth=0):
            if depth > 10:
                return
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = key.lower().replace("_", " ")
                    current_path = f"{path}.{key}" if path else key

                    # Check if this is a lower-is-better metric
                    is_lower_better = any(lib in key_lower for lib in LOWER_IS_BETTER)

                    if is_lower_better and isinstance(value, str):
                        if "below average" in value.lower():
                            violations.append((current_path, value))

                    scan_for_violations(value, current_path, depth + 1)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    scan_for_violations(item, f"{path}[{i}]", depth + 1)

        scan_for_violations(data)

        passed = len(violations) == 0
        return {
            "gate": self.name,
            "passed": passed,
            "hard_fail": False,
            "score": 1.0 if passed else 0.0,
            "threshold": 0,
            "detail": f"Found {len(violations)} directionality errors" if violations else "All metric directions correct",
            "violations": violations[:10],
        }


class PlaceholderScanGate(QualityGate):
    """Gate 6: Reject TBD, N/A, $0.00, UNKNOWN, etc."""

    def __init__(self):
        super().__init__("Placeholder Scan")

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        placeholders = []
        pattern = re.compile("|".join(PLACEHOLDER_PATTERNS), re.IGNORECASE)

        def scan_for_placeholders(obj, path="", depth=0):
            if depth > 15:
                return
            if isinstance(obj, str):
                matches = pattern.findall(obj)
                for match in matches:
                    placeholders.append((path, match, obj[:100]))
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    scan_for_placeholders(value, f"{path}.{key}" if path else key, depth + 1)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    scan_for_placeholders(item, f"{path}[{i}]", depth + 1)

        scan_for_placeholders(data)

        passed = len(placeholders) == 0
        return {
            "gate": self.name,
            "passed": passed,
            "hard_fail": len(placeholders) > 10,
            "score": 1.0 if passed else max(0, 1.0 - len(placeholders) / 20),
            "threshold": 0,
            "detail": f"Found {len(placeholders)} placeholder values" if placeholders else "No placeholder values found",
            "placeholders": [(p[0], p[1]) for p in placeholders[:15]],
        }


class FiscalBasisLintGate(QualityGate):
    """Gate 7: Every financial figure carries FY/Q label."""

    def __init__(self):
        super().__init__("Fiscal-Basis Lint", threshold=0.90)

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        total_figures = 0
        labeled_figures = 0

        fin_data = data.get("financial_intelligence", {})
        statements = fin_data.get("financial_statements", {})

        for statement_type in ["income_statement", "balance_sheet", "cash_flow"]:
            rows = statements.get(statement_type, [])
            for row in rows:
                if isinstance(row, dict):
                    total_figures += 1
                    if row.get("fiscal_year") or row.get("fy") or row.get("period"):
                        labeled_figures += 1

        # Also check other financial data
        facts = fin_data.get("facts", {})
        for concept, concept_data in facts.items():
            if isinstance(concept_data, dict):
                units = concept_data.get("units", {})
                for unit, values in units.items():
                    if isinstance(values, list):
                        for v in values:
                            if isinstance(v, dict) and v.get("val"):
                                total_figures += 1
                                if v.get("fy") or v.get("fp"):
                                    labeled_figures += 1

        coverage = labeled_figures / total_figures if total_figures > 0 else 1.0

        return {
            "gate": self.name,
            "passed": coverage >= self.threshold,
            "hard_fail": coverage < 0.7,
            "score": coverage,
            "threshold": self.threshold,
            "detail": f"{labeled_figures}/{total_figures} financial figures have fiscal labels ({coverage:.1%})",
        }


class LandingPageBanGate(QualityGate):
    """Gate 8: Deep document URLs only, no landing pages."""

    def __init__(self):
        super().__init__("Landing-Page Ban")

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        landing_pages = []
        pattern = re.compile("|".join(LANDING_PAGE_PATTERNS), re.IGNORECASE)

        def scan_for_urls(obj, path="", depth=0):
            if depth > 15:
                return
            if isinstance(obj, str) and obj.startswith("http"):
                if pattern.search(obj):
                    landing_pages.append((path, obj))
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ("url", "source_url", "filing_url", "citation"):
                        scan_for_urls(value, f"{path}.{key}" if path else key, depth + 1)
                    else:
                        scan_for_urls(value, f"{path}.{key}" if path else key, depth + 1)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    scan_for_urls(item, f"{path}[{i}]", depth + 1)

        scan_for_urls(data)

        passed = len(landing_pages) == 0
        return {
            "gate": self.name,
            "passed": passed,
            "hard_fail": False,
            "score": 1.0 if passed else max(0, 1.0 - len(landing_pages) / 10),
            "threshold": 0,
            "detail": f"Found {len(landing_pages)} landing page URLs" if landing_pages else "All URLs are deep links",
            "landing_pages": landing_pages[:10],
        }


class NamedPersonAccuracyGate(QualityGate):
    """Gate 9: ≥2 independent sources per named person."""

    def __init__(self):
        super().__init__("Named-Person Accuracy", threshold=0.80)

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        person_sources: Dict[str, Set[str]] = {}

        # Check proxy data for executives/directors
        proxy_data = data.get("proxy_intelligence", {})
        for person in proxy_data.get("executives", []) + proxy_data.get("directors", []):
            name = person.get("name", "")
            if name:
                person_sources.setdefault(name, set()).add("proxy")

        # Check insider transactions for Form 4 filers
        insider_data = data.get("insider_transactions", {})
        for txn in insider_data.get("transactions", []):
            name = txn.get("owner_name", "")
            if name:
                person_sources.setdefault(name, set()).add("form4")

        # Check board interlocks
        interlock_data = data.get("board_interlocks", {})
        for person in interlock_data.get("people", []):
            name = person.get("name", "")
            if name:
                person_sources.setdefault(name, set()).add("interlocks")

        # Check news mentions
        news_data = data.get("news_intelligence", {})
        for mention in news_data.get("people_mentions", []):
            name = mention.get("name", "")
            if name:
                person_sources.setdefault(name, set()).add("news")

        # Calculate coverage
        total_people = len(person_sources)
        multi_source = sum(1 for sources in person_sources.values() if len(sources) >= 2)

        coverage = multi_source / total_people if total_people > 0 else 1.0

        return {
            "gate": self.name,
            "passed": coverage >= self.threshold,
            "hard_fail": coverage < 0.5,
            "score": coverage,
            "threshold": self.threshold,
            "detail": f"{multi_source}/{total_people} named people have ≥2 sources ({coverage:.1%})",
            "single_source_people": [name for name, sources in person_sources.items() if len(sources) < 2][:10],
        }


class SensitiveClaimReviewGate(QualityGate):
    """Gate 10: Documented facts only, no asserted motive."""

    def __init__(self):
        super().__init__("Sensitive-Claim Review")

    def check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sensitive_claims = []
        pattern = re.compile("|".join(SENSITIVE_PATTERNS), re.IGNORECASE)

        def scan_for_sensitive(obj, path="", depth=0):
            if depth > 15:
                return
            if isinstance(obj, str) and len(obj) > 20:
                matches = pattern.findall(obj)
                if matches:
                    # Check if claim has a citation
                    has_citation = "according to" in obj.lower() or "source:" in obj.lower()
                    if not has_citation:
                        sensitive_claims.append((path, matches[0], obj[:150]))
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    scan_for_sensitive(value, f"{path}.{key}" if path else key, depth + 1)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    scan_for_sensitive(item, f"{path}[{i}]", depth + 1)

        scan_for_sensitive(data)

        passed = len(sensitive_claims) == 0
        return {
            "gate": self.name,
            "passed": passed,
            "hard_fail": len(sensitive_claims) > 3,
            "score": 1.0 if passed else max(0, 1.0 - len(sensitive_claims) / 5),
            "threshold": 0,
            "detail": f"Found {len(sensitive_claims)} sensitive claims without citations" if sensitive_claims else "All sensitive claims are cited",
            "flagged_claims": [(c[1], c[2]) for c in sensitive_claims[:5]],
        }


# ── Main Entry Point ──────────────────────────────────────────────────────────

ALL_GATES = [
    CitationCoverageGate(),
    ArithmeticReconciliationGate(),
    DuplicateDetectionGate(),
    NewsStalenessGate(),
    DirectionalityLintGate(),
    PlaceholderScanGate(),
    FiscalBasisLintGate(),
    LandingPageBanGate(),
    NamedPersonAccuracyGate(),
    SensitiveClaimReviewGate(),
]


def run_quality_gates(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all 10 quality gates against the report data.

    Args:
        data: Deep research data dictionary

    Returns:
        Quality gate results with pass/fail status for each gate.
    """
    results = []
    passed_count = 0
    hard_failures = []

    for gate in ALL_GATES:
        try:
            result = gate.check(data)
            results.append(result)
            if result["passed"]:
                passed_count += 1
            if result.get("hard_fail"):
                hard_failures.append(result["gate"])
        except Exception as e:
            logger.warning("Quality gate %s failed with error: %s", gate.name, e)
            results.append({
                "gate": gate.name,
                "passed": False,
                "hard_fail": False,
                "score": 0.0,
                "threshold": 0,
                "detail": f"Gate check error: {e}",
            })

    overall_score = sum(r.get("score", 0) for r in results) / len(results) if results else 0
    all_passed = passed_count == len(ALL_GATES)

    return {
        "passed": all_passed and len(hard_failures) == 0,
        "gates_passed": passed_count,
        "gates_total": len(ALL_GATES),
        "overall_score": overall_score,
        "hard_failures": hard_failures,
        "results": results,
        "summary": {
            "publication_ready": all_passed and len(hard_failures) == 0,
            "needs_review": not all_passed and len(hard_failures) == 0,
            "blocked": len(hard_failures) > 0,
        },
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }


def format_quality_report(gate_results: Dict[str, Any]) -> str:
    """Format quality gate results as markdown."""
    lines = ["## Quality Gate Report\n"]

    status = "PASSED" if gate_results["passed"] else "FAILED"
    lines.append(f"**Status:** {status}")
    lines.append(f"**Score:** {gate_results['overall_score']:.1%}")
    lines.append(f"**Gates Passed:** {gate_results['gates_passed']}/{gate_results['gates_total']}")
    lines.append("")

    if gate_results["hard_failures"]:
        lines.append("### Hard Failures (blocking)")
        for gate in gate_results["hard_failures"]:
            lines.append(f"- {gate}")
        lines.append("")

    lines.append("### Gate Results\n")
    lines.append("| Gate | Status | Score | Detail |")
    lines.append("|------|--------|-------|--------|")

    for result in gate_results["results"]:
        status_icon = "✅" if result["passed"] else "❌"
        lines.append(
            f"| {result['gate']} | {status_icon} | {result.get('score', 0):.1%} | {result['detail'][:60]}... |"
        )

    return "\n".join(lines)
