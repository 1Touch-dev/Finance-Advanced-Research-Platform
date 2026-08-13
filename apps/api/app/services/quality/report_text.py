"""
Report flattener — turns the nested intelligence `data` dict (the same shape
`quality_gate_service.run_quality_gates` consumes) into a compact, human/LLM
-readable digest. The raw dict can be megabytes (see reports/*.json); an LLM
judge needs a bounded, information-dense summary, not the raw tree.

Pure function: same input -> same output, no I/O, no side effects, no network.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Default character budget for the flattened digest. Roughly ~1 char/0.3
# tokens for English text, so 12000 chars is comfortably under an 8k-token
# judge prompt budget alongside instructions.
_DEFAULT_CHAR_BUDGET = 12000

_SENSITIVE_PATTERNS = [
    r"fraud", r"insider trading", r"manipulation", r"embezzlement",
    r"brib(e|ery)", r"kickback", r"self-dealing", r"money laundering",
    r"tax evasion", r"shell company", r"siphon", r"misappropriat",
]
_SENSITIVE_RE = re.compile("|".join(_SENSITIVE_PATTERNS), re.IGNORECASE)


def _fmt_num(v: Any) -> str:
    if isinstance(v, (int, float)):
        if abs(v) >= 1000:
            return f"{v:,.0f}"
        return f"{v:.2f}" if isinstance(v, float) else str(v)
    return str(v)


def _as_list(value: Any) -> List[Any]:
    """Best-effort normalization to a list. Production report shapes vary by
    connector: some fields are plain lists, others are a dict wrapping the
    real list under a nested key (e.g. litigation sub-sections wrap `cases`/
    `enforcement_actions`). Never raises; unknown shapes just yield []."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        flattened: List[Any] = []
        for v in value.values():
            if isinstance(v, list):
                flattened.extend(v)
        return flattened
    return []


def _financial_summary(data: Dict[str, Any], max_items: int = 8) -> List[str]:
    fin = data.get("financial_intelligence") or {}
    if not isinstance(fin, dict):
        return []
    lines = []
    total_rev = fin.get("total_revenue")
    if isinstance(total_rev, (int, float)):
        lines.append(f"Total revenue: {_fmt_num(total_rev)}")

    # `segments` is a plain list in the simple/test shape, but in real
    # generated reports it's a dict of {category: [row, ...]} (e.g.
    # "segments"/"geographic"), and rows use current/prior, not "revenue".
    for seg in _as_list(fin.get("segments"))[:max_items]:
        if not isinstance(seg, dict):
            continue
        name = seg.get("name")
        if not name:
            continue
        value = seg.get("revenue")
        if not isinstance(value, (int, float)):
            value = seg.get("current")
        if isinstance(value, (int, float)):
            lines.append(f"Segment {name}: {_fmt_num(value)}")

    # Free-text narrative, when present, is what actually lets the judge
    # assess clarity/accuracy/neutrality (the pure numeric lines above can't).
    # No production connector populates this key today, so this is additive
    # and never changes existing digests - but see synthetic.py, which does.
    summary = fin.get("summary")
    if isinstance(summary, str) and summary.strip():
        lines.append(f"Analysis: {summary.strip()[:800]}")
    return lines[:max_items]


def _insider_summary(data: Dict[str, Any], max_items: int = 5) -> List[str]:
    ins = data.get("insider_transactions") or {}
    if not isinstance(ins, dict):
        return []
    lines = []
    for t in _as_list(ins.get("transactions"))[:max_items]:
        if not isinstance(t, dict):
            continue
        owner = t.get("owner_name", "unknown")
        code = t.get("transaction_code", "?")
        shares = t.get("shares", 0)
        line = f"Insider {owner}: code={code} shares={_fmt_num(shares)}"
        context = t.get("context")
        if isinstance(context, str) and context.strip():
            line += f" — {context.strip()[:300]}"
        lines.append(line)
    return lines


def _news_summary(data: Dict[str, Any], max_items: int = 5) -> List[str]:
    news = data.get("news_intelligence") or {}
    if not isinstance(news, dict):
        return []
    lines = []
    for a in _as_list(news.get("articles"))[:max_items]:
        if not isinstance(a, dict):
            continue
        title = (a.get("title") or a.get("headline") or "").strip()
        date = a.get("date") or a.get("published") or ""
        if title:
            line = f"News ({date}): {title[:140]}"
            desc = a.get("summary") or a.get("description")
            if isinstance(desc, str) and desc.strip():
                line += f" — {desc.strip()[:300]}"
            lines.append(line)
    return lines


def _contract_summary(data: Dict[str, Any], max_items: int = 5) -> List[str]:
    c = data.get("contract_intelligence") or {}
    if not isinstance(c, dict):
        return []
    lines = []
    for con in _as_list(c.get("contracts"))[:max_items]:
        if not isinstance(con, dict):
            continue
        agency = con.get("agency", "unknown agency")
        amount = con.get("obligated_amount", 0)
        lines.append(f"Contract with {agency}: obligated {_fmt_num(amount)}")
    return lines


def _litigation_summary(data: Dict[str, Any], max_items: int = 5) -> List[str]:
    """
    Real reports spread litigation across several typed sub-sections
    (federal_cases, sec_enforcement, ftc_proceedings, ...), each of which may
    itself be a dict wrapping the actual case list (e.g.
    federal_cases -> {"cases": [...]}, sec_enforcement -> {"enforcement_actions": [...]}).
    Gathers across all of them defensively.
    """
    lit = data.get("litigation_intelligence") or {}
    if not isinstance(lit, dict):
        return []
    cases: List[Any] = []
    for key in ("federal_cases", "sec_enforcement", "ftc_proceedings", "doj_antitrust",
                "itc_investigations", "ptab_proceedings", "cases", "filings"):
        val = lit.get(key)
        cases.extend(_as_list(val))

    lines = []
    for case in cases[:max_items]:
        if not isinstance(case, dict):
            continue
        desc = case.get("case_name") or case.get("summary") or case.get("description") or case.get("title") or ""
        if desc:
            court = f" ({case['court']})" if case.get("court") else ""
            lines.append(f"Litigation: {str(desc)[:140]}{court}")
    return lines[:max_items]


def _named_people_summary(data: Dict[str, Any], max_items: int = 10) -> List[str]:
    """People + how many independent sources mention them (mirrors Gate 9's logic
    but for the digest, not a verdict)."""
    person_sources: Dict[str, set] = {}

    proxy = data.get("proxy_intelligence") or {}
    if isinstance(proxy, dict):
        for p in _as_list(proxy.get("executives")) + _as_list(proxy.get("directors")):
            if isinstance(p, dict) and p.get("name"):
                person_sources.setdefault(p["name"], set()).add("proxy")

    ins = data.get("insider_transactions") or {}
    if isinstance(ins, dict):
        for t in _as_list(ins.get("transactions")):
            if isinstance(t, dict) and t.get("owner_name"):
                person_sources.setdefault(t["owner_name"], set()).add("form4")

    interlocks = data.get("board_interlocks") or {}
    if isinstance(interlocks, dict):
        for p in _as_list(interlocks.get("people")):
            if isinstance(p, dict) and p.get("name"):
                person_sources.setdefault(p["name"], set()).add("interlocks")

    news = data.get("news_intelligence") or {}
    if isinstance(news, dict):
        for m in _as_list(news.get("people_mentions")):
            if isinstance(m, dict) and m.get("name"):
                person_sources.setdefault(m["name"], set()).add("news")

    lines = []
    for name, sources in list(person_sources.items())[:max_items]:
        lines.append(f"{name}: {len(sources)} source(s) ({', '.join(sorted(sources))})")
    return lines


def _sensitive_claims(data: Dict[str, Any], max_items: int = 5) -> List[str]:
    hits: List[str] = []

    def _walk(obj: Any, depth: int = 0) -> None:
        if depth > 12 or len(hits) >= max_items:
            return
        if isinstance(obj, str) and len(obj) > 20 and _SENSITIVE_RE.search(obj):
            hits.append(obj[:200])
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item, depth + 1)

    _walk(data)
    return hits


def flatten_report(data: Dict[str, Any], *, char_budget: int = _DEFAULT_CHAR_BUDGET) -> str:
    """
    Build a compact, judge-readable digest of a report's `data` dict.

    Handles two shapes seen in this codebase:
      1. Deep-research shape (financial_intelligence/insider_transactions/...)
         -- the one quality_gate_service's rule gates are written against.
      2. DB report shape (sections/claims/summary, from
         intelligence_service.get_intelligence_report) -- lighter, no numeric
         structure the rule gates can check, but still real report content the
         judge can read.

    Sections: identity, financials, insider activity, contracts, litigation,
    news, named people + source diversity, sensitive claims (shape 1); or
    identity, summary, section narratives, sample claims (shape 2). Truncated to
    `char_budget` characters (whole-line truncation, never mid-sentence) so
    callers always get a bounded, deterministic prompt size.
    """
    if not isinstance(data, dict):
        return ""

    is_deep_research = any(k in data for k in (
        "financial_intelligence", "insider_transactions", "news_intelligence",
        "proxy_intelligence", "board_interlocks", "contract_intelligence",
    ))

    sections: List[str] = []

    entity = data.get("entity_name") or data.get("ticker") or data.get("title") or "Unknown entity"
    ticker = data.get("ticker", "")
    header = f"ENTITY: {entity}" + (f" ({ticker})" if ticker and ticker != entity else "")
    sections.append(header)

    if is_deep_research:
        fin = _financial_summary(data)
        if fin:
            sections.append("FINANCIALS:\n" + "\n".join(f"- {l}" for l in fin))

        insiders = _insider_summary(data)
        if insiders:
            sections.append("INSIDER ACTIVITY:\n" + "\n".join(f"- {l}" for l in insiders))

        contracts = _contract_summary(data)
        if contracts:
            sections.append("GOVERNMENT CONTRACTS:\n" + "\n".join(f"- {l}" for l in contracts))

        litigation = _litigation_summary(data)
        if litigation:
            sections.append("LITIGATION:\n" + "\n".join(f"- {l}" for l in litigation))

        news = _news_summary(data)
        if news:
            sections.append("RECENT NEWS:\n" + "\n".join(f"- {l}" for l in news))

        people = _named_people_summary(data)
        if people:
            sections.append("NAMED PEOPLE (source diversity):\n" + "\n".join(f"- {l}" for l in people))
    else:
        summary = data.get("summary")
        if summary:
            sections.append(f"SUMMARY:\n{str(summary)[:1500]}")

        for sec in (data.get("sections") or [])[:12]:
            if not isinstance(sec, dict):
                continue
            name = sec.get("name", "Section")
            content = (sec.get("content") or "").strip()
            if content:
                sections.append(f"SECTION - {name}:\n{content[:1200]}")

        claims = data.get("claims") or []
        claim_lines = [
            f"- {(c.get('text') or '').strip()[:200]}"
            for c in claims[:15] if isinstance(c, dict) and c.get("text")
        ]
        if claim_lines:
            sections.append("CLAIMS SAMPLE:\n" + "\n".join(claim_lines))

    sensitive = _sensitive_claims(data)
    if sensitive:
        sections.append("SENSITIVE CLAIMS (verify citations):\n" + "\n".join(f"- {l}" for l in sensitive))

    digest = "\n\n".join(sections)
    if len(digest) <= char_budget:
        return digest

    # Truncate on a line boundary when reasonably close to the budget so we
    # don't cut mid-sentence; otherwise a hard cut is unavoidable (e.g. one
    # giant unbroken line) but we still always mark it as truncated.
    truncated = digest[:char_budget]
    last_newline = truncated.rfind("\n")
    if last_newline > char_budget * 0.5:
        truncated = truncated[:last_newline]
    return truncated + "\n\n[...truncated for length...]"
