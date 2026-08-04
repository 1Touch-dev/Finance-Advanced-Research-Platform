"""
Data-health checks and alerting (G-09).

*"Nobody gets notified when a data source breaks."* — the cheapest item on the
backlog and the one with the worst failure mode, because a broken connector
does not raise. It returns an empty list, the section renders as "no related
party transactions were disclosed", and the report reads as a clean bill of
health for a company we simply failed to fetch.

That is the distinction this module exists to draw:

    absent   — the source answered and the issuer has nothing to disclose
    broken   — the source did not answer, and we cannot tell either way

Everything else follows from it. A check knows what a healthy response looks
like for its own source, so "zero federal contracts" is fine for a software
company and suspicious for a defence prime; the checks encode which is which
by looking at whether the *fetch* succeeded, not at whether the result is
large.

Severity is deliberately coarse. Three levels, each tied to an action:

    critical — the report should not ship; a spine source is missing
    degraded — the report ships with a stated gap
    notice   — worth knowing, no action

Alerting writes to the log and, where configured, to a webhook. It does not
depend on the platform's Postgres or its queue, because a health check that
needs the platform to be healthy is not a health check.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

CRITICAL = "critical"
DEGRADED = "degraded"
NOTICE = "notice"

_ORDER = {CRITICAL: 0, DEGRADED: 1, NOTICE: 2}


def _count(value: Any) -> int:
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, (list, tuple, set)):
        return len(value)
    return 1 if value else 0


# ---------------------------------------------------------------------------
# The check table
# ---------------------------------------------------------------------------
#
# Each row: key in the payload, human label, severity if empty, and a probe
# that returns the number of records the source produced. Severity is about
# what the absence costs the report, not about how much data arrived.

_CHECKS: List[Dict[str, Any]] = [
    {"key": "financial_intelligence", "label": "SEC company facts",
     "severity": CRITICAL,
     "probe": lambda d: _count(((d.get("financial_intelligence") or {})
                                .get("financial_statements") or {}).get("income_statement")),
     "means": "no financial statements — the report has no spine"},

    {"key": "price_history", "label": "Daily price bars", "severity": DEGRADED,
     "probe": lambda d: _count((d.get("price_history") or {}).get("bars")),
     "means": "no correlations and no price chart"},

    {"key": "insider_transactions", "label": "Form 4 insider activity",
     "severity": DEGRADED,
     "probe": lambda d: _count((d.get("insider_transactions") or {}).get("transactions")),
     "means": "no insider timing analysis and no Section 16 cohort"},

    {"key": "institutional_holdings", "label": "13F institutional holders",
     "severity": DEGRADED,
     "probe": lambda d: _count((d.get("institutional_holdings") or {}).get("holders")),
     "means": "no ownership concentration and no overlap graph"},

    {"key": "proxy_intelligence", "label": "DEF 14A proxy",
     "severity": DEGRADED,
     "probe": lambda d: _count((d.get("proxy_intelligence") or {}).get("related_party_transactions")),
     "means": "no related-party register and no board composition"},

    {"key": "board_interlocks", "label": "Board interlocks",
     "severity": NOTICE,
     "probe": lambda d: _count((d.get("board_interlocks") or {}).get("people")),
     "means": "no co-occurrence graph over people"},

    {"key": "contract_intelligence", "label": "Federal awards (USAspending)",
     "severity": NOTICE,
     "probe": lambda d: _count((d.get("contract_intelligence") or {}).get("contracts")),
     "means": "no federal footprint; legitimately zero for most issuers"},

    {"key": "political_intelligence", "label": "Senate LDA lobbying",
     "severity": NOTICE,
     "probe": lambda d: ((d.get("political_intelligence") or {})
                         .get("lobbying_summary") or {}).get("filing_count") or 0,
     "means": "no lobbying analysis; legitimately zero for most issuers"},

    {"key": "event_timeline", "label": "Filing chronology", "severity": DEGRADED,
     "probe": lambda d: _count((d.get("event_timeline") or {}).get("events")),
     "means": "no chronology and no event study"},

    {"key": "news_intelligence", "label": "News and open web",
     "severity": DEGRADED,
     "probe": lambda d: _count((d.get("news_intelligence") or {}).get("articles")),
     "means": "no coverage, interviews or rumour surface"},

    {"key": "litigation_intelligence", "label": "Litigation and enforcement",
     "severity": NOTICE,
     "probe": lambda d: sum(
         _count((d.get("litigation_intelligence") or {}).get(bucket))
         for bucket in ("federal_cases", "sec_enforcement", "ftc_proceedings",
                        "doj_antitrust", "itc_investigations",
                        "ptab_proceedings")),
     "means": "no docket history"},

    {"key": "valuation_analysis", "label": "DCF valuation", "severity": NOTICE,
     "probe": lambda d: _count((d.get("valuation_analysis") or {}).get("dcf")),
     "means": "no intrinsic value estimate"},
]


def _flag_implausible_zeros(checks: List[Dict[str, Any]],
                            data: Dict[str, Any]) -> None:
    """Raise the severity of an empty result another source contradicts.

    An empty register is normally unremarkable — most issuers do no lobbying
    and hold no federal contracts. But a company with 234 federal awards that
    discloses no lobbying at all is not a quiet company; it is a fetch that
    failed. Nothing in the register itself can tell the two apart, so the
    contradiction has to come from a second source.
    """
    by_key = {c["key"]: c for c in checks}

    def _records(key: str) -> int:
        check = by_key.get(key)
        return int(check.get("records") or 0) if check else 0

    contradictions = [
        # (empty source, corroborating source, threshold, why it is implausible)
        ("political_intelligence", "contract_intelligence", 25,
         "the issuer holds {n} federal awards; a federal contractor of that "
         "size disclosing no lobbying is far more likely to be a failed or "
         "throttled fetch than a true zero"),
        ("contract_intelligence", "political_intelligence", 25,
         "the issuer filed {n} lobbying disclosures; that level of federal "
         "engagement alongside no federal awards points at a name that did "
         "not resolve rather than an absence of contracts"),
    ]

    for key, corroborator, threshold, reason in contradictions:
        check = by_key.get(key)
        if not check or check["status"] != "empty":
            continue
        count = _records(corroborator)
        if count < threshold:
            continue
        check["status"] = "suspect"
        check["severity"] = "degraded"
        check["detail"] = ("source answered with no records, but "
                           + reason.format(n=f"{count:,}"))


def _payload_error(payload: Any, depth: int = 2) -> Optional[str]:
    """The refusal reason a connector recorded, wherever it recorded it.

    Several connectors return a wrapper whose failure is set on the nested
    section that failed rather than on the payload the check reads — the
    lobbying summary sits inside the political-intelligence payload, and an
    unreachable register was consequently reported as an issuer with nothing to
    disclose. One level of nesting is inspected so that a connector cannot fail
    silently by putting its reason one key deeper than expected.
    """
    if not isinstance(payload, dict):
        return None
    direct = payload.get("error") or payload.get("failure")
    if direct:
        return str(direct)
    if depth <= 0:
        return None
    for value in payload.values():
        nested = _payload_error(value, depth - 1)
        if nested:
            return nested
    return None


def run_health_checks(data: Dict[str, Any]) -> Dict[str, Any]:
    """Per-source status for one report run."""
    checks: List[Dict[str, Any]] = []

    for spec in _CHECKS:
        payload = data.get(spec["key"])
        try:
            records = int(spec["probe"](data) or 0)
        except Exception as error:
            logger.debug("Health probe %s raised: %s", spec["key"], error)
            records = 0

        # An error field on the payload is the one unambiguous signal that the
        # source was reached and refused. Anything else is inference.
        error_text = _payload_error(payload)

        if error_text:
            status, detail = "broken", str(error_text)[:200]
        elif payload is None:
            status, detail = "not_run", "the connector was never called"
        elif records > 0:
            status, detail = "ok", f"{records} record{'' if records == 1 else 's'}"
        else:
            # Reached, returned, empty. Might be honest, might be a silent
            # break; the report is told it cannot distinguish the two.
            status, detail = "empty", "source answered with no records"

        checks.append({
            "source": spec["label"],
            "key": spec["key"],
            "status": status,
            "records": records,
            "detail": detail,
            "severity": spec["severity"] if status != "ok" else None,
            "impact": spec["means"],
        })

    _flag_implausible_zeros(checks, data)

    # "suspect" sits with the failures rather than the empties: another source
    # contradicts it, so it is a probable break and should be treated as one.
    failing = [c for c in checks if c["status"] in ("broken", "not_run", "suspect")]
    empty = [c for c in checks if c["status"] == "empty"]
    healthy = [c for c in checks if c["status"] == "ok"]

    worst = None
    for check in failing + empty:
        if check["severity"] and (worst is None
                                  or _ORDER[check["severity"]] < _ORDER[worst]):
            worst = check["severity"]

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checks": sorted(checks, key=lambda c: (
            _ORDER.get(c["severity"], 3),
            c["status"] not in ("broken", "suspect"), c["source"])),
        "suspect": len([c for c in checks if c["status"] == "suspect"]),
        "healthy": len(healthy),
        "empty": len(empty),
        "failing": len(failing),
        "total": len(checks),
        "coverage_pct": round(len(healthy) / max(1, len(checks)) * 100),
        "worst_severity": worst,
        "should_alert": worst in (CRITICAL, DEGRADED),
        "alerts": [
            {"source": c["source"], "severity": c["severity"],
             "status": c["status"], "impact": c["impact"], "detail": c["detail"]}
            for c in failing + empty if c["severity"] in (CRITICAL, DEGRADED)
        ],
    }


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

def format_alert(health: Dict[str, Any], entity_name: str = "",
                 ticker: str = "") -> str:
    """A plain-text alert. Readable in a terminal, a log or a Slack message."""
    header = (f"Data health — {entity_name or 'run'}"
              f"{f' ({ticker})' if ticker else ''}: "
              f"{health['healthy']}/{health['total']} sources returned data "
              f"({health['coverage_pct']}% coverage)")
    if not health.get("alerts"):
        return header + "\nNo source failed."

    lines = [header, ""]
    for alert in health["alerts"]:
        lines.append(
            f"  [{alert['severity'].upper()}] {alert['source']}: "
            f"{alert['status']} — {alert['detail']}")
        lines.append(f"      impact: {alert['impact']}")
    return "\n".join(lines)


def send_alert(health: Dict[str, Any], entity_name: str = "",
               ticker: str = "") -> Dict[str, Any]:
    """Log the alert, and post it to a webhook where one is configured.

    Slack and Teams both accept a bare `{"text": ...}` payload, so one
    environment variable covers either. Failure to deliver an alert is itself
    logged and never raised — an unreachable webhook must not take down the
    report it was warning about.
    """
    message = format_alert(health, entity_name, ticker)
    delivered = []

    if health.get("should_alert"):
        logger.warning("%s", message)
    else:
        logger.info("%s", message)

    webhook = os.getenv("DATA_HEALTH_WEBHOOK_URL", "")
    if webhook and health.get("should_alert"):
        try:
            request = urllib.request.Request(
                webhook,
                data=json.dumps({"text": message}).encode("utf-8"),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=10) as response:
                if 200 <= response.status < 300:
                    delivered.append("webhook")
        except Exception as error:
            logger.warning("Health webhook delivery failed: %s", error)

    return {
        "message": message,
        "delivered": delivered,
        "webhook_configured": bool(webhook),
        "alerted": bool(health.get("should_alert")),
    }
