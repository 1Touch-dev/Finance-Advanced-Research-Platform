#!/usr/bin/env python
"""
Quality judge demo — before/after: rules-only vs judge vs blend.

Runs three sample reports through all three modes and prints a side-by-side
table (rule verdict, judge score + top issues, blended decision). The money
shot: a report engineered to pass every rule gate while reading vague/biased
— rules say "publication_ready", the judge (when an API key is configured)
should flag it. Without a key, the judge degrades to ok=False and blend
transparently falls back to rules (shown in the table too, honestly).

Usage:
  python -m app.scripts.quality_judge_demo
"""
from __future__ import annotations

import json

from app.services.quality.decision import evaluate

# 1) A clean, well-cited report — should sail through rules.
GOOD_REPORT = {
    "entity_name": "Acme Semiconductor Corp",
    "ticker": "ACME",
    "financial_intelligence": {
        "total_revenue": 12500000000,
        "source_url": "https://sec.gov/acme/10k-fy2025",
        "segments": [
            {"name": "Data Center", "revenue": 8000000000, "source_url": "https://sec.gov/acme/10k-fy2025#segments"},
            {"name": "Gaming", "revenue": 4500000000, "source_url": "https://sec.gov/acme/10k-fy2025#segments"},
        ],
    },
    "insider_transactions": {
        "transactions": [
            {"owner_name": "Jane Smith", "transaction_code": "S", "shares": 20000,
             "source_url": "https://sec.gov/edgar/form4/acme-jsmith"},
        ],
    },
    "proxy_intelligence": {
        "executives": [{"name": "Jane Smith"}],
        "directors": [{"name": "Tom Lee"}],
    },
    "board_interlocks": {"people": [{"name": "Tom Lee"}]},
    "news_intelligence": {"articles": [{"title": "Acme beats Q4 estimates", "date": "2026-08-01"}]},
}

# 2) A report engineered to pass mechanical rule checks (citations exist,
# numbers reconcile, no placeholders) but reads misleadingly / vague — the
# gap the judge exists to close.
SUBTLE_BAD_REPORT = {
    "entity_name": "Vague Holdings Inc",
    "ticker": "VAGU",
    "financial_intelligence": {
        "total_revenue": 5000000000,
        "source_url": "https://sec.gov/vagu/10k",
        "segments": [{"name": "Core", "revenue": 5000000000, "source_url": "https://sec.gov/vagu/10k#seg"}],
    },
    "insider_transactions": {"transactions": []},
    "news_intelligence": {
        "articles": [{"title": "Vague Holdings may possibly see some growth eventually, sources suggest", "date": "2026-08-01"}],
    },
}

# 3) A report with a real compliance problem (no citations at all on numeric
# claims) — this trips Citation Coverage's hard_fail threshold, so the rules
# veto must win regardless of how well the judge might score it.
NON_PUBLISHABLE_REPORT = {
    "entity_name": "Uncited Capital Corp",
    "ticker": "UNCT",
    "financial_intelligence": {
        "total_revenue": 900000000,
        "segments": [{"name": "Core", "revenue": 900000000}],
    },
}

SAMPLES = [
    ("Clean, well-cited report", GOOD_REPORT),
    ("Subtly vague/misleading (passes mechanics)", SUBTLE_BAD_REPORT),
    ("No citations on numeric claims (hard rule veto)", NON_PUBLISHABLE_REPORT),
]


def _fmt_issues(judge: dict) -> str:
    if not judge or not judge.get("ok"):
        return f"(unavailable: {judge.get('error') if judge else 'n/a'})"
    issues = judge.get("issues") or []
    return "; ".join(issues[:3]) if issues else "(none)"


def main() -> None:
    print("=" * 100)
    print("QUALITY JUDGE DEMO — rules vs judge vs blend")
    print("=" * 100)

    for label, data in SAMPLES:
        print(f"\n### {label} ###")
        row = {}
        for mode in ("rules", "judge", "blend"):
            result = evaluate(data, mode=mode, report_id=f"demo:{label}", log_labels=False)
            row[mode] = result

        rules_res = row["rules"]
        judge_res = row["judge"]["judge_result"]
        blend_res = row["blend"]

        print(f"  rules : decision={rules_res['decision']:18s} score={rules_res['combined_score']}")
        print(f"  judge : decision={row['judge']['decision']:18s} score={row['judge']['combined_score']}  "
              f"issues={_fmt_issues(judge_res)}")
        print(f"  blend : decision={blend_res['decision']:18s} score={blend_res['combined_score']}")

    print("\n" + "=" * 100)
    print("Note: without OPENAI_API_KEY, the judge shows ok=False and blend degrades to")
    print("pure rules (fail-soft, by design) — set the key to see the judge's real signal.")
    print("=" * 100)


if __name__ == "__main__":
    main()
