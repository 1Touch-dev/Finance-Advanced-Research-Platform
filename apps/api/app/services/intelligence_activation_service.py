from __future__ import annotations

import os
import re
import tempfile
import threading
import time
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

import logging

logger = logging.getLogger(__name__)

from app.services.coinvestment_network_service import (
    analyze_position_concentration,
    build_coinvestment_network,
    find_coordinated_movements,
    render_coinvestment_network_markdown,
)
from app.services.contract_probability_service import analyze_contract_probability
from app.services.correlation_service import run_all as run_correlation_suite
from app.services.deep_comparative_service import render_deep_comparative_markdown
from app.services.founder_correlations_service import (
    build_founder_correlation_graph,
    render_founder_correlations_markdown,
)
from app.services.interactive_report_service import generate_interactive_report
from app.services.self_dealing_service import cross_reference_self_dealing
from app.services.intelligence_service import generate_enhanced_intelligence_report

try:
    from app.connectors.board_interlock_connector import get_board_interlocks
    BOARD_INTERLOCK_AVAILABLE = True
except ImportError:
    BOARD_INTERLOCK_AVAILABLE = False

    def get_board_interlocks(*args, **kwargs):
        return {}

try:
    from app.connectors.family_network_connector import research_family_network
    FAMILY_NETWORK_AVAILABLE = True
except ImportError:
    FAMILY_NETWORK_AVAILABLE = False

    def research_family_network(*args, **kwargs):
        return {}

try:
    from app.connectors.fpds_connector import get_full_contract_portfolio
    CONTRACTS_AVAILABLE = True
except ImportError:
    CONTRACTS_AVAILABLE = False

    def get_full_contract_portfolio(*args, **kwargs):
        return {}

try:
    from app.connectors.institutional_holdings_connector import get_institutional_holders
    INSTITUTIONAL_HOLDINGS_AVAILABLE = True
except ImportError:
    INSTITUTIONAL_HOLDINGS_AVAILABLE = False

    def get_institutional_holders(*args, **kwargs):
        return {}

try:
    from app.connectors.institutional_overlap_connector import compare_competitor_ownership
    INSTITUTIONAL_OVERLAP_AVAILABLE = True
except ImportError:
    INSTITUTIONAL_OVERLAP_AVAILABLE = False

    def compare_competitor_ownership(*args, **kwargs):
        return {}

try:
    from app.connectors.market_data_connector import get_price_history, get_quote
    MARKET_DATA_AVAILABLE = True
except ImportError:
    MARKET_DATA_AVAILABLE = False

    def get_price_history(*args, **kwargs):
        return {}

    def get_quote(*args, **kwargs):
        return {}

try:
    from app.connectors.opensecrets_connector import get_political_intelligence
    POLITICAL_AVAILABLE = True
except ImportError:
    POLITICAL_AVAILABLE = False

    def get_political_intelligence(*args, **kwargs):
        return {}

try:
    from app.connectors.proxy_statement_connector import get_proxy_intelligence
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False

    def get_proxy_intelligence(*args, **kwargs):
        return {}

try:
    from app.connectors.sec_edgar_connector import get_cik_from_ticker, get_filer_cik, get_insider_transactions
    SEC_EDGAR_AVAILABLE = True
except ImportError:
    SEC_EDGAR_AVAILABLE = False

    def get_cik_from_ticker(*args, **kwargs):
        return None

    def get_filer_cik(*args, **kwargs):
        return None

    def get_insider_transactions(*args, **kwargs):
        return {}

try:
    from app.connectors.timeline_connector import generate_entity_timeline
    TIMELINE_AVAILABLE = True
except ImportError:
    TIMELINE_AVAILABLE = False

    def generate_entity_timeline(*args, **kwargs):
        return {}

try:
    from app.services.deep_comparative_service import run_deep_comparative_analysis
    DEEP_COMPARATIVE_AVAILABLE = True
except ImportError:
    DEEP_COMPARATIVE_AVAILABLE = False

    def run_deep_comparative_analysis(*args, **kwargs):
        return {}


def _source_state(available: bool, status: str, detail: str = "", used: bool = False) -> Dict[str, Any]:
    return {
        "available": available,
        "used": used,
        "status": status,
        "detail": detail,
    }


def _warning(source: str, code: str, detail: str) -> Dict[str, str]:
    return {"source": source, "code": code, "detail": detail}


def _clean_markdown_line(line: str) -> str:
    text = (line or "").strip()
    if not text or text.startswith("|---"):
        return ""
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"^[-*]\s+", "", text)
    text = re.sub(r"^>\s*", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return text.strip()


def _markdown_lines_to_report_section(
    name: str,
    order: int,
    lines: List[str],
    data: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    claims = []
    for raw_line in lines:
        cleaned = _clean_markdown_line(raw_line)
        if cleaned:
            claims.append({"text": cleaned, "confidence": "ANALYTICAL"})
    if not claims:
        return None
    return {
        "name": name,
        "order": order,
        "claims": claims,
        "data": data or {},
    }


def _render_source_status_markdown(
    title: str,
    source_status: Dict[str, Dict[str, Any]],
    warnings: List[Dict[str, str]],
) -> List[str]:
    lines: List[str] = []
    if warnings:
        lines.extend([f"### {title}", ""])
        for warning in warnings:
            detail = warning.get("detail") or warning.get("code") or "Unavailable."
            lines.append(
                f"- {warning.get('source', 'source').replace('_', ' ').title()}: {detail}"
            )
        lines.append("")
    elif source_status:
        degraded = [
            f"- {name.replace('_', ' ').title()}: {state.get('detail') or state.get('status')}"
            for name, state in source_status.items()
            if state.get("status") in {"error", "unavailable", "missing_input"}
        ]
        if degraded:
            lines.extend([f"### {title}", ""])
            lines.extend(degraded)
            lines.append("")
    return lines


def _render_correlation_markdown(data: Dict[str, Any]) -> List[str]:
    correlations = _ensure_dict(data.get("correlations") or {})
    if not correlations:
        return []

    lines = ["## Correlation & Event Studies", ""]
    lines.append(
        f"Grounded event-study and co-movement analysis over "
        f"{correlations.get('price_bars', 0)} price bars."
    )
    lines.append("")

    insider = correlations.get("insider_timing")
    if insider:
        lines.append("### Insider Sale Timing")
        lines.append("")
        lines.append(
            f"- Correlation: {insider.get('r')} over n={insider.get('n')} "
            f"(95% CI {insider.get('ci_low')} to {insider.get('ci_high')})."
        )
        lines.append(
            f"- Statistical significance after point-estimate test: "
            f"{'yes' if insider.get('significant') else 'no'}."
        )
        lines.append("")

    event_returns = correlations.get("event_returns")
    if event_returns:
        lines.append("### Event Return Study")
        lines.append("")
        lines.append(
            f"- Events analyzed: {event_returns.get('n_events', event_returns.get('n', 'N/A'))}."
        )
        if event_returns.get("mean_abnormal_return") is not None:
            lines.append(
                f"- Mean abnormal return: {event_returns.get('mean_abnormal_return')}."
            )
        lines.append("")

    lobbying_lag = correlations.get("lobbying_lag")
    if lobbying_lag:
        lines.append("### Lobbying / Award Lag")
        lines.append("")
        if lobbying_lag.get("median_lag_days") is not None:
            lines.append(f"- Median lag: {lobbying_lag.get('median_lag_days')} days.")
        if lobbying_lag.get("matches") is not None:
            lines.append(f"- Matches observed: {lobbying_lag.get('matches')}.")
        lines.append("")

    if correlations.get("ran", 0) == 0:
        lines.append(
            "No grounded correlations met the service thresholds for publication."
        )
        lines.append("")

    return lines


def _public_error_detail(error: Exception, default: str = "Upstream request failed.") -> str:
    message = str(error or "").strip()
    if not message:
        return default
    message = re.sub(r"https?://\S+", "[url]", message)
    message = re.sub(r"(?i)(token|apikey|api_key|key)=([^&\s]+)", r"\1=[redacted]", message)
    message = re.sub(r"\s+", " ", message)
    return message[:240]


def _source_error_detail(source: str, error: Exception, default: str = "Upstream request failed.") -> str:
    if isinstance(error, TimeoutError):
        labels = {
            "proxy_intelligence": "Proxy intelligence source timed out.",
            "insider_transactions": "Insider transactions source timed out.",
            "board_interlocks": "Board interlocks source timed out.",
            "contract_intelligence": "Contract intelligence source timed out.",
            "family_network": "Family network source timed out.",
            "institutional_holders": "Institutional holders source timed out.",
            "price_history": "Price history source timed out.",
            "event_timeline": "Event timeline source timed out.",
            "political_intelligence": "Political intelligence source timed out.",
            "deep_comparative": "Deep comparative source timed out.",
        }
        return labels.get(source, f"{source.replace('_', ' ').title()} source timed out.")
    if isinstance(error, ModuleNotFoundError):
        labels = {
            "family_network": "Family network source unavailable.",
        }
        return labels.get(source, f"{source.replace('_', ' ').title()} source unavailable.")
    return _public_error_detail(error, default=default)


_SELF_DEALING_SOURCE_TIMEOUTS = {
    "proxy_intelligence": 12.0,
    "insider_transactions": 12.0,
    "board_interlocks": 10.0,
    "contract_intelligence": 15.0,
    "family_network": 12.0,
    "institutional_holders": 15.0,
}
_SELF_DEALING_WALL_CLOCK_BUDGET = 25.0

_CORRELATION_SOURCE_TIMEOUTS = {
    "insider_transactions": 12.0,
    "price_history": 12.0,
    "event_timeline": 12.0,
    "political_intelligence": 8.0,
    "contract_intelligence": 15.0,
    "deep_comparative": 20.0,
}
_CORRELATION_WALL_CLOCK_BUDGET = 25.0
_COMPANY_TICKER_TITLE_CACHE: Dict[str, str] = {}
_INTERACTIVE_INSIDER_MAX_FILINGS = 20
_INTERACTIVE_INSIDER_REQUEST_TIMEOUT = 3.0
_INTERACTIVE_INSIDER_MAX_ELAPSED = 8.0


def _call_with_timeout(func, *args, timeout: float = 12.0, **kwargs):
    result: "Queue[tuple[bool, Any]]" = Queue(maxsize=1)

    def runner():
        try:
            result.put((True, func(*args, **kwargs)))
        except Exception as error:  # pragma: no cover - exercised via caller
            result.put((False, error))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"{getattr(func, '__name__', 'source')} timed out after {timeout}s")
    try:
        ok, payload = result.get_nowait()
    except Empty:
        raise TimeoutError(f"{getattr(func, '__name__', 'source')} returned no result before timeout")
    if ok:
        return payload
    raise payload


def _run_correlation_source_jobs(
    source_jobs: Dict[str, Any],
    source_timeouts: Dict[str, float],
) -> Dict[str, Any]:
    """Run optional correlation sources without waiting on unfinished workers."""
    return _run_bounded_source_jobs(
        source_jobs,
        source_timeouts,
        wall_clock_budget=_CORRELATION_WALL_CLOCK_BUDGET,
        log_prefix="correlation",
    )


def _run_bounded_source_jobs(
    source_jobs: Dict[str, Any],
    source_timeouts: Dict[str, float],
    *,
    wall_clock_budget: float,
    log_prefix: str,
) -> Dict[str, Any]:
    """Run source jobs with per-source deadlines and a shared wall-clock budget."""
    started = time.monotonic()
    wall_deadline = started + wall_clock_budget
    active: Dict[str, Dict[str, Any]] = {}
    results: Dict[str, Any] = {}

    for source, job in source_jobs.items():
        result_queue: "Queue[tuple[bool, Any]]" = Queue(maxsize=1)
        func, args, kwargs = job

        def runner(source_name=source, source_func=func, source_args=args, source_kwargs=kwargs, queue=result_queue):
            logger.warning("%s:%s:start elapsed=%.3fs", log_prefix, source_name, time.monotonic() - started)
            try:
                queue.put((True, source_func(*source_args, **source_kwargs)))
            except Exception as error:
                queue.put((False, error))

        thread = threading.Thread(target=runner, daemon=True, name=f"{log_prefix}-{source}")
        active[source] = {
            "queue": result_queue,
            "deadline": min(started + source_timeouts[source], wall_deadline),
            "thread": thread,
        }
        thread.start()

    while active:
        now = time.monotonic()
        if now >= wall_deadline:
            logger.warning("%s:budget_exhausted elapsed=%.3fs", log_prefix, now - started)

        for source, state in list(active.items()):
            queue = state["queue"]
            try:
                ok, payload = queue.get_nowait()
            except Empty:
                if now >= state["deadline"] or now >= wall_deadline:
                    error = TimeoutError(f"{source} exceeded {log_prefix} wall-clock budget")
                    results[source] = (False, error)
                    active.pop(source, None)
                    logger.warning("%s:%s:timeout elapsed=%.3fs", log_prefix, source, now - started)
                continue

            results[source] = (ok, payload)
            active.pop(source, None)
            logger.warning("%s:%s:end elapsed=%.3fs", log_prefix, source, time.monotonic() - started)

        if active:
            next_deadline = min(state["deadline"] for state in active.values())
            sleep_for = max(0.01, min(0.05, next_deadline - time.monotonic()))
            time.sleep(sleep_for)

    return results


def _ensure_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _timeline_has_events(payload: Dict[str, Any]) -> bool:
    events = payload.get("events")
    return isinstance(events, list) and bool(events)


def _contract_payload_has_data(payload: Dict[str, Any]) -> bool:
    contracts = payload.get("contracts")
    subcontracts = payload.get("subcontracts")
    if isinstance(contracts, list) and contracts:
        return True
    if isinstance(subcontracts, list) and subcontracts:
        return True
    summary = payload.get("summary")
    return bool(isinstance(summary, dict) and summary.get("total_contracts", 0))


def _deep_comparative_has_data(payload: Dict[str, Any]) -> bool:
    if not isinstance(payload, dict) or not payload:
        return False
    tickers_with_data = payload.get("tickers_with_data")
    if isinstance(tickers_with_data, list) and len(tickers_with_data) > 1:
        return True
    peer_rankings = payload.get("peer_rankings")
    if isinstance(peer_rankings, list):
        return any(
            item.get("ticker") != payload.get("target_ticker") and item.get("score") is not None
            for item in peer_rankings
            if isinstance(item, dict)
        )
    return False


def _build_correlation_event_timeline(ticker: str, years: int, cik: Optional[str]) -> Dict[str, Any]:
    try:
        return _ensure_dict(
            generate_entity_timeline(
                ticker,
                years=min(years, 2),
                resolved_cik=cik,
                max_8k_item_enrichment=10,
                eight_k_request_timeout=6,
            ) or {}
        )
    except TypeError:
        return _ensure_dict(generate_entity_timeline(ticker, years=min(years, 2)) or {})


def _build_correlation_contract_portfolio(entity_name: str) -> Dict[str, Any]:
    try:
        return _ensure_dict(
            get_full_contract_portfolio(
                entity_name,
                request_timeout=12,
                max_elapsed_seconds=12.0,
                subaward_timeout=8,
            ) or {}
        )
    except TypeError:
        return _ensure_dict(get_full_contract_portfolio(entity_name) or {})


def _build_correlation_political_intelligence(entity_name: str) -> Dict[str, Any]:
    try:
        return _ensure_dict(
            get_political_intelligence(
                entity_name,
                lda_attempts=1,
                lda_request_timeout=5,
            ) or {}
        )
    except TypeError:
        return _ensure_dict(get_political_intelligence(entity_name) or {})


def _company_lookup_key(value: str) -> str:
    text = re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper())
    words = [
        word
        for word in text.split()
        if word not in {"THE", "INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "PLC", "LLC"}
    ]
    return " ".join(words)


def _resolve_self_dealing_ticker(entity_name: str, ticker: str) -> str:
    """Use a real symbol when the ticker field accidentally contains a company name."""
    candidate = _normalize_ticker(ticker)
    if _TICKER_PATTERN.fullmatch(candidate):
        return candidate

    lookup_key = _company_lookup_key(candidate or entity_name)
    if not lookup_key:
        return candidate
    if lookup_key in _COMPANY_TICKER_TITLE_CACHE:
        return _COMPANY_TICKER_TITLE_CACHE[lookup_key]

    try:
        from app.connectors import sec_edgar_connector as sec_edgar
        from app.connectors.sec_http import sec_get_json

        payload = sec_get_json(
            f"{sec_edgar.SEC_WWW_BASE}/files/company_tickers.json",
            timeout=5,
            attempts=1,
        )
        if isinstance(payload, dict):
            for entry in payload.values():
                symbol = str(entry.get("ticker") or "").upper().strip()
                title = str(entry.get("title") or "")
                title_key = _company_lookup_key(title)
                if symbol and title_key:
                    _COMPANY_TICKER_TITLE_CACHE.setdefault(title_key, symbol)
                    if lookup_key == title_key or lookup_key in title_key or title_key in lookup_key:
                        _COMPANY_TICKER_TITLE_CACHE[lookup_key] = symbol
                        return symbol
    except Exception as error:
        logger.warning("Ticker title resolution failed for %s: %s", lookup_key, error)

    return candidate


def _build_self_dealing_insider_transactions(ticker: str) -> Dict[str, Any]:
    cik = _resolve_interactive_cik(ticker)
    if not cik:
        return {"cik": None, "insider_transactions": {}}
    return _build_interactive_insider_transactions_for_cik(cik)


def _build_self_dealing_insider_transactions_for_cik(cik: str) -> Dict[str, Any]:
    return _build_interactive_insider_transactions_for_cik(cik)


def _build_interactive_insider_transactions_for_cik(cik: str) -> Dict[str, Any]:
    try:
        insider = get_insider_transactions(
            cik,
            max_filings=_INTERACTIVE_INSIDER_MAX_FILINGS,
            request_timeout=_INTERACTIVE_INSIDER_REQUEST_TIMEOUT,
            max_elapsed_seconds=_INTERACTIVE_INSIDER_MAX_ELAPSED,
        )
    except TypeError:
        try:
            insider = get_insider_transactions(cik, max_filings=_INTERACTIVE_INSIDER_MAX_FILINGS)
        except TypeError:
            insider = get_insider_transactions(cik)
    return {"cik": cik, "insider_transactions": _ensure_dict(insider or {})}


def _resolve_self_dealing_cik(ticker: str) -> Optional[str]:
    return _resolve_interactive_cik(ticker)


def _resolve_interactive_cik(ticker: str) -> Optional[str]:
    """Resolve a ticker to its registrant CIK using the fast ticker map path."""
    normalized = _normalize_ticker(ticker)
    if not normalized:
        return None
    if getattr(get_filer_cik, "__name__", "") == "<lambda>":
        return get_filer_cik(normalized)
    try:
        from app.connectors import sec_edgar_connector as sec_edgar
        cache = getattr(sec_edgar, "_TICKER_CIK_CACHE", {})
        if normalized in cache:
            return cache[normalized]
        load_cache = getattr(sec_edgar, "_load_ticker_map_cache", None)
        if callable(load_cache) and load_cache() and normalized in cache:
            return cache[normalized]
        from app.connectors.sec_http import sec_get_json

        payload = sec_get_json(
            f"{sec_edgar.SEC_WWW_BASE}/files/company_tickers.json",
            timeout=5,
            attempts=1,
        )
        if isinstance(payload, dict):
            for entry in payload.values():
                sym = str(entry.get("ticker", "")).upper()
                if sym:
                    cache[sym] = str(entry.get("cik_str", "")).zfill(10)
            store_cache = getattr(sec_edgar, "_store_ticker_map_cache", None)
            if callable(store_cache):
                store_cache()
            if normalized in cache:
                return cache[normalized]
    except Exception as error:
        logger.warning("Fast CIK resolution failed for %s: %s", normalized, error)
    return get_cik_from_ticker(normalized) or get_filer_cik(normalized)


def _classify_interactive_insider_payload(insider_transactions: Dict[str, Any]) -> tuple[str, bool, Optional[str], Optional[str]]:
    payload = _ensure_dict(insider_transactions)
    transactions = payload.get("transactions") or []
    if transactions:
        if payload.get("timeout"):
            return (
                "ok",
                True,
                "Insider transactions returned a partial sample within the interactive budget.",
                "partial_timeout",
            )
        return "ok", True, None, None
    if payload.get("timeout"):
        return "timeout", False, "Insider transactions source timed out.", "timeout"
    if payload.get("error"):
        return "unavailable", False, "Insider transactions source unavailable.", "source_unavailable"
    return "no_data", False, None, None


def _has_insider_transaction_rows(insider_transactions: Dict[str, Any]) -> bool:
    return bool(_ensure_dict(insider_transactions).get("transactions") or [])


def _build_self_dealing_family_network(
    entity_name: str,
    ticker: str,
    proxy_data: Dict[str, Any],
    insider_transactions: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        from app.connectors.family_network_connector import get_family_network

        return _ensure_dict(
            get_family_network(
                entity_name=entity_name,
                proxy=proxy_data,
                insider=insider_transactions,
                include_foundations=True,
            ) or {}
        )
    except ImportError:
        raise
    except Exception:
        return _ensure_dict(research_family_network(entity_name, ticker) or {})


def _build_self_dealing_contract_portfolio(
    entity_name: str,
    exec_names: List[str],
    related_entities: List[str],
) -> Dict[str, Any]:
    try:
        return _ensure_dict(
            get_full_contract_portfolio(
                entity_name,
                executives=exec_names or None,
                related_entities=related_entities or None,
                request_timeout=5,
                max_elapsed_seconds=8.0,
                subaward_timeout=3,
            ) or {}
        )
    except TypeError:
        return _ensure_dict(
            get_full_contract_portfolio(
                entity_name,
                executives=exec_names or None,
                related_entities=related_entities or None,
            ) or {}
        )


def _build_self_dealing_institutional_holders(entity_name: str, ticker: str) -> Dict[str, Any]:
    quote = _build_quote_context(ticker)
    return _ensure_dict(
        get_institutional_holders(
            entity_name,
            ticker,
            quote.get("shares_outstanding"),
            quote.get("price"),
            max_institutions=4,
        ) or {}
    )


def _political_status(payload: Dict[str, Any]) -> str:
    error = str(payload.get("error") or "").lower()
    if error:
        if "429" in error or "rate" in error:
            return "rate_limited"
        if "401" in error or "403" in error or "api_key" in error or "did not answer" in error:
            return "unavailable"
        return "error"
    return "ok" if payload else "no_data"


def _build_quote_context(ticker: str) -> Dict[str, Any]:
    if not (MARKET_DATA_AVAILABLE and ticker):
        return {}
    try:
        return _ensure_dict(get_quote(ticker) or {})
    except Exception as error:
        return {"_error": _public_error_detail(error)}


_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def _normalize_ticker(value: str) -> str:
    return str(value or "").strip().upper()


def _normalize_competitors(
    primary_ticker: str,
    competitors: Optional[List[str]],
    warnings: List[Dict[str, str]],
    max_competitors: int = 5,
) -> List[str]:
    primary = _normalize_ticker(primary_ticker)
    seen = set()
    normalized: List[str] = []
    invalid: List[str] = []
    removed_primary = False
    duplicates_removed = 0

    for raw in competitors or []:
        candidate = _normalize_ticker(raw)
        if not candidate:
            continue
        if candidate == primary:
            removed_primary = True
            continue
        if not _TICKER_PATTERN.fullmatch(candidate):
            invalid.append(str(raw))
            continue
        if candidate in seen:
            duplicates_removed += 1
            continue
        seen.add(candidate)
        normalized.append(candidate)

    if invalid:
        warnings.append(
            _warning(
                "deep_comparative",
                "invalid_competitor",
                "Some competitor inputs were not valid ticker symbols and were ignored.",
            )
        )
    if removed_primary:
        warnings.append(
            _warning(
                "deep_comparative",
                "primary_competitor_removed",
                "The primary ticker was removed from the competitor list.",
            )
        )
    if duplicates_removed:
        warnings.append(
            _warning(
                "deep_comparative",
                "duplicate_competitor_removed",
                "Duplicate competitor tickers were removed.",
            )
        )
    if len(normalized) > max_competitors:
        warnings.append(
            _warning(
                "deep_comparative",
                "competitor_limit",
                f"Only the first {max_competitors} normalized competitors were analyzed.",
            )
        )
        normalized = normalized[:max_competitors]

    return normalized


def _extract_proxy_people(proxy_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    people: List[Dict[str, Any]] = []
    seen = set()
    proxy_data = _ensure_dict(proxy_data)
    board = _ensure_dict(proxy_data.get("board_composition", {}) or proxy_data.get("board", {}))

    for director in board.get("directors", []) or []:
        name = director.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        people.append(
            {
                "name": name,
                "title": director.get("principal_position") or director.get("title") or "Director",
                "biography": director.get("biography") or director.get("bio") or "",
                "education": director.get("education") or [],
            }
        )

    for officer in proxy_data.get("named_executive_officers", []) or []:
        if not isinstance(officer, dict):
            continue
        name = officer.get("name") or officer.get("executive")
        if not name or name in seen:
            continue
        seen.add(name)
        people.append(
            {
                "name": name,
                "title": officer.get("title") or officer.get("position") or "Executive Officer",
                "biography": officer.get("biography") or officer.get("bio") or "",
                "education": officer.get("education") or [],
            }
        )

    return people


def _extract_exec_names(people: List[Dict[str, Any]], insider_transactions: Dict[str, Any]) -> List[str]:
    names = [person.get("name") for person in people if person.get("name")]
    if names:
        return names
    extracted = []
    for row in _ensure_dict(insider_transactions).get("transactions", []) or []:
        if not isinstance(row, dict):
            continue
        name = row.get("insider") or row.get("owner_name") or row.get("reporting_owner_name")
        if name and name not in extracted:
            extracted.append(name)
    return extracted


def _build_markdown_from_sections(entity_name: str, sections: List[Dict[str, Any]]) -> str:
    lines = [f"# {entity_name} Intelligence Report", ""]
    for section in sections or []:
        lines.append(f"## {section.get('name', 'Section')}")
        claims = section.get("claims") or []
        if claims:
            for claim in claims:
                text = claim.get("text", "") if isinstance(claim, dict) else str(claim)
                if text:
                    lines.append(f"- {text}")
        else:
            content = section.get("content")
            if content:
                lines.append(str(content))
        lines.append("")
    return "\n".join(lines)


def _build_graph_ready_data(analysis: Dict[str, Any]) -> Dict[str, Any]:
    analysis = _ensure_dict(analysis)
    institutional_holders = _ensure_dict(analysis.get("institutional_holders") or {})
    managers = []
    for holder in institutional_holders.get("holders", []) or []:
        managers.append(
            {
                "name": holder.get("institution"),
                "count": 1,
                "issuers": [analysis.get("entity_name")],
            }
        )

    return {
        "board_interlocks": analysis.get("board_interlocks") or {},
        "family_network": analysis.get("family_network") or {},
        "cooccurrence": {"institutional": {"managers": managers}},
        "data_health": {
            "healthy": sum(
                1
                for key in ("board_interlocks", "family_network", "institutional_holders")
                if analysis.get(key)
            ),
            "total": 3,
        },
    }


def build_report_intelligence_additions(
    entity_name: str,
    ticker: str = "",
    competitors: Optional[List[str]] = None,
    network_depth: int = 1,
    family_network: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    competitors = competitors or []
    sections: List[Dict[str, Any]] = []
    next_order = 0

    network_analysis = build_network_analysis(
        entity_name=entity_name,
        ticker=ticker,
        competitors=competitors,
        depth=network_depth,
    ) if ticker else {}

    if network_analysis:
        founder_lines = render_founder_correlations_markdown(
            _ensure_dict(network_analysis.get("founder_correlations") or {})
        )
        founder_lines.extend(
            _render_source_status_markdown(
                "Availability Notes",
                _ensure_dict(network_analysis.get("source_status") or {}),
                network_analysis.get("warnings") or [],
            )
        )
        founder_section = _markdown_lines_to_report_section(
            "Grounded Founder & Executive Network",
            next_order,
            founder_lines,
            data={
                "founder_correlations": network_analysis.get("founder_correlations") or {},
                "board_interlocks": network_analysis.get("board_interlocks") or {},
                "warnings": network_analysis.get("warnings") or [],
                "source_status": network_analysis.get("source_status") or {},
            },
        )
        if founder_section:
            sections.append(founder_section)
            next_order += 10

        coinvest_lines = render_coinvestment_network_markdown(
            _ensure_dict(network_analysis.get("co_investment_network") or {})
        )
        if network_analysis.get("position_concentration"):
            concentration = network_analysis["position_concentration"]
            coinvest_lines.extend(
                [
                    "### Holder Concentration",
                    "",
                    f"- Herfindahl index: {concentration.get('herfindahl_index', 0)}.",
                    f"- Top holder share: {concentration.get('largest_holder_pct', 0)}%.",
                    "",
                ]
            )
        coinvest_section = _markdown_lines_to_report_section(
            "Grounded Co-Investment Network",
            next_order,
            coinvest_lines,
            data={
                "co_investment_network": network_analysis.get("co_investment_network") or {},
                "position_concentration": network_analysis.get("position_concentration") or {},
                "institutional_overlap": network_analysis.get("institutional_overlap") or {},
            },
        )
        if coinvest_section:
            sections.append(coinvest_section)
            next_order += 10

    correlation_analysis = build_correlation_analysis(
        entity_name=entity_name,
        ticker=ticker,
        competitors=competitors,
    ) if ticker else {}

    if correlation_analysis:
        correlation_lines = _render_correlation_markdown(correlation_analysis)
        correlation_lines.extend(
            _render_source_status_markdown(
                "Availability Notes",
                _ensure_dict(correlation_analysis.get("source_status") or {}),
                correlation_analysis.get("warnings") or [],
            )
        )
        correlation_section = _markdown_lines_to_report_section(
            "Correlation & Event Studies",
            next_order,
            correlation_lines,
            data={
                "correlations": correlation_analysis.get("correlations") or {},
                "source_status": correlation_analysis.get("source_status") or {},
                "warnings": correlation_analysis.get("warnings") or [],
            },
        )
        if correlation_section:
            sections.append(correlation_section)
            next_order += 10

        deep_comparative = _ensure_dict(correlation_analysis.get("deep_comparative") or {})
        if deep_comparative.get("target_ticker") or deep_comparative.get("peer_tickers"):
            comparative_lines = render_deep_comparative_markdown(deep_comparative)
            comparative_section = _markdown_lines_to_report_section(
                "Deep Comparative Analysis",
                next_order,
                comparative_lines,
                data={"deep_comparative": deep_comparative},
            )
            if comparative_section:
                sections.append(comparative_section)
                next_order += 10

    graph_data = _build_graph_ready_data(
        {
            "entity_name": entity_name,
            "board_interlocks": (network_analysis or {}).get("board_interlocks") or {},
            "family_network": family_network or {},
            "institutional_holders": (network_analysis or {}).get("institutional_holders") or {},
        }
    )

    return {
        "sections": sections,
        "network_analysis": network_analysis,
        "correlation_analysis": correlation_analysis,
        "interactive_report": {
            "supported": True,
            "graph_data": graph_data,
        },
    }


def build_paypal_mafia_report_addendum() -> Dict[str, Any]:
    network_analysis = build_network_analysis(
        entity_name="PayPal Holdings Inc",
        ticker="PYPL",
        competitors=[],
        depth=1,
    )
    lines = render_founder_correlations_markdown(
        _ensure_dict(network_analysis.get("founder_correlations") or {})
    )
    lines.extend(
        render_coinvestment_network_markdown(
            _ensure_dict(network_analysis.get("co_investment_network") or {})
        )
    )
    lines.extend(
        _render_source_status_markdown(
            "Availability Notes",
            _ensure_dict(network_analysis.get("source_status") or {}),
            network_analysis.get("warnings") or [],
        )
    )
    if not lines:
        lines = [
            "## Grounded PayPal Network Addendum",
            "",
            "Grounded founder and co-investment data was unavailable for this run, so no additional network links are asserted here.",
            "",
        ]
    return {
        "markdown": "\n".join(lines).strip() + "\n",
        "analysis": network_analysis,
    }


def build_self_dealing_analysis(
    entity_name: str,
    ticker: str = "",
    related_entities: Optional[List[str]] = None,
    include_family_network: bool = True,
    include_institutional_holders: bool = True,
) -> Dict[str, Any]:
    overall_started = time.monotonic()
    ticker = _resolve_self_dealing_ticker(entity_name, ticker)
    logger.warning("self_dealing:start entity=%s ticker=%s", entity_name, ticker)
    related_entities = related_entities or []
    source_status: Dict[str, Dict[str, Any]] = {}
    warnings: List[Dict[str, str]] = []

    proxy_data: Dict[str, Any] = {}
    insider_transactions: Dict[str, Any] = {}
    board_interlocks: Dict[str, Any] = {}
    contract_intelligence: Dict[str, Any] = {}
    family_network: Dict[str, Any] = {}
    holders_report: Dict[str, Any] = {}
    cik = None

    def remaining_budget() -> float:
        elapsed = time.monotonic() - overall_started
        return max(0.5, _SELF_DEALING_WALL_CLOCK_BUDGET - elapsed)

    initial_jobs: Dict[str, Any] = {}
    initial_timeouts: Dict[str, float] = {}

    if PROXY_AVAILABLE and ticker:
        initial_jobs["proxy_intelligence"] = (get_proxy_intelligence, (ticker,), {"years": 1})
        initial_timeouts["proxy_intelligence"] = _SELF_DEALING_SOURCE_TIMEOUTS["proxy_intelligence"]
    else:
        detail = "Ticker is required for proxy analysis." if not ticker else "Proxy connector unavailable."
        source_status["proxy_intelligence"] = _source_state(PROXY_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)

    if SEC_EDGAR_AVAILABLE and ticker:
        cik = _resolve_self_dealing_cik(ticker)
        if cik:
            initial_jobs["insider_transactions"] = (_build_self_dealing_insider_transactions_for_cik, (cik,), {})
            initial_timeouts["insider_transactions"] = _SELF_DEALING_SOURCE_TIMEOUTS["insider_transactions"]
        else:
            source_status["insider_transactions"] = _source_state(True, "no_data", "No filer CIK resolved for ticker.")
    else:
        detail = "Ticker is required for insider analysis." if not ticker else "SEC EDGAR connector unavailable."
        source_status["insider_transactions"] = _source_state(SEC_EDGAR_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)

    if initial_jobs:
        for source, outcome in _run_bounded_source_jobs(
            initial_jobs,
            initial_timeouts,
            wall_clock_budget=remaining_budget(),
            log_prefix="self_dealing",
        ).items():
            ok, value = outcome
            try:
                if not ok:
                    raise value
                if source == "proxy_intelligence":
                    proxy_data = _ensure_dict(value or {})
                    status = "ok" if proxy_data else "no_data"
                    source_status[source] = _source_state(True, status, used=bool(proxy_data))
                else:
                    payload = _ensure_dict(value or {})
                    cik = payload.get("cik") or cik
                    insider_transactions = _ensure_dict(payload.get("insider_transactions") or {})
                    if cik:
                        status, used, detail, code = _classify_interactive_insider_payload(insider_transactions)
                        source_status[source] = _source_state(True, status, detail, used=used)
                        if detail and code:
                            warnings.append(_warning(source, code, detail))
                    else:
                        source_status[source] = _source_state(True, "no_data", "No filer CIK resolved for ticker.")
            except Exception as error:
                detail = _source_error_detail(source, error)
                status = "timeout" if isinstance(error, TimeoutError) else "error"
                source_status[source] = _source_state(True, status, detail)
                code = "timeout" if isinstance(error, TimeoutError) else "upstream_error"
                warnings.append(_warning(source, code, detail))

    followup_jobs: Dict[str, Any] = {}
    followup_timeouts: Dict[str, float] = {}

    if BOARD_INTERLOCK_AVAILABLE and _has_insider_transaction_rows(insider_transactions) and cik:
        followup_jobs["board_interlocks"] = (
            get_board_interlocks,
            (insider_transactions.get("transactions", []), cik, entity_name),
            {},
        )
        followup_timeouts["board_interlocks"] = _SELF_DEALING_SOURCE_TIMEOUTS["board_interlocks"]
    else:
        detail = "Requires ticker-resolved insider transactions." if ticker else "Ticker is required."
        source_status["board_interlocks"] = _source_state(
            BOARD_INTERLOCK_AVAILABLE,
            "missing_input" if not _has_insider_transaction_rows(insider_transactions) else "unavailable",
            detail,
        )

    exec_names = _extract_exec_names(_extract_proxy_people(proxy_data), insider_transactions)
    if CONTRACTS_AVAILABLE:
        followup_jobs["contract_intelligence"] = (
            _build_self_dealing_contract_portfolio,
            (entity_name, exec_names, related_entities),
            {},
        )
        followup_timeouts["contract_intelligence"] = _SELF_DEALING_SOURCE_TIMEOUTS["contract_intelligence"]
    else:
        source_status["contract_intelligence"] = _source_state(False, "unavailable", "FPDS/USASpending connector unavailable.")

    if include_family_network:
        if FAMILY_NETWORK_AVAILABLE and ticker:
            followup_jobs["family_network"] = (
                _build_self_dealing_family_network,
                (entity_name, ticker, proxy_data, insider_transactions),
                {},
            )
            followup_timeouts["family_network"] = _SELF_DEALING_SOURCE_TIMEOUTS["family_network"]
        else:
            detail = "Ticker is required for family network analysis." if not ticker else "Family network connector unavailable."
            source_status["family_network"] = _source_state(FAMILY_NETWORK_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)
    else:
        source_status["family_network"] = _source_state(FAMILY_NETWORK_AVAILABLE, "skipped", "Family network analysis disabled.")

    if include_institutional_holders:
        if INSTITUTIONAL_HOLDINGS_AVAILABLE and ticker:
            followup_jobs["institutional_holders"] = (
                _build_self_dealing_institutional_holders,
                (entity_name, ticker),
                {},
            )
            followup_timeouts["institutional_holders"] = _SELF_DEALING_SOURCE_TIMEOUTS["institutional_holders"]
        else:
            detail = "Ticker is required for 13F holder analysis." if not ticker else "Institutional holdings connector unavailable."
            source_status["institutional_holders"] = _source_state(INSTITUTIONAL_HOLDINGS_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)
    else:
        source_status["institutional_holders"] = _source_state(INSTITUTIONAL_HOLDINGS_AVAILABLE, "skipped", "Institutional holder analysis disabled.")

    if followup_jobs:
        for source, outcome in _run_bounded_source_jobs(
            followup_jobs,
            followup_timeouts,
            wall_clock_budget=remaining_budget(),
            log_prefix="self_dealing",
        ).items():
            ok, value = outcome
            try:
                if not ok:
                    raise value
                payload = _ensure_dict(value or {})
                if source == "board_interlocks":
                    board_interlocks = payload
                elif source == "contract_intelligence":
                    contract_intelligence = payload
                elif source == "family_network":
                    family_network = payload
                elif source == "institutional_holders":
                    holders_report = payload
                status = "ok" if payload else "no_data"
                source_status[source] = _source_state(True, status, used=bool(payload))
            except Exception as error:
                detail = _source_error_detail(source, error)
                if source == "family_network" and isinstance(error, ModuleNotFoundError):
                    status = "unavailable"
                    code = "source_unavailable"
                else:
                    status = "timeout" if isinstance(error, TimeoutError) else "error"
                    code = "timeout" if isinstance(error, TimeoutError) else "upstream_error"
                source_status[source] = _source_state(True, status, detail)
                warnings.append(_warning(source, code, detail))

    analysis = cross_reference_self_dealing(
        (proxy_data or {}).get("related_party_transactions") or [],
        insider_transactions=insider_transactions,
        board_interlocks=board_interlocks,
        contract_intelligence=contract_intelligence,
        family_network=family_network,
        institutional_holders=(holders_report or {}).get("holders") or [],
        entity_name=entity_name,
    )

    logger.warning("build_self_dealing_analysis:return ticker=%s elapsed=%.3fs", ticker, time.monotonic() - overall_started)

    return {
        "entity_name": entity_name,
        "ticker": ticker,
        "cik": cik,
        "analysis": analysis,
        "source_status": source_status,
        "warnings": warnings,
        "partial": any(value["status"] in {"error", "timeout", "unavailable", "missing_input"} for value in source_status.values()),
    }


def build_network_analysis(
    entity_name: str,
    ticker: str = "",
    competitors: Optional[List[str]] = None,
    depth: int = 1,
) -> Dict[str, Any]:
    competitors = competitors or []
    source_status: Dict[str, Dict[str, Any]] = {}
    warnings: List[Dict[str, str]] = []

    proxy_data: Dict[str, Any] = {}
    insider_transactions: Dict[str, Any] = {}
    board_interlocks: Dict[str, Any] = {}
    holders_report: Dict[str, Any] = {}
    overlap_report: Dict[str, Any] = {}
    cik = None

    if PROXY_AVAILABLE and ticker:
        try:
            proxy_data = _ensure_dict(get_proxy_intelligence(ticker, years=3) or {})
            source_status["proxy_intelligence"] = _source_state(True, "ok" if proxy_data else "no_data", used=bool(proxy_data))
        except Exception as error:
            detail = _public_error_detail(error)
            source_status["proxy_intelligence"] = _source_state(True, "error", detail)
            warnings.append(_warning("proxy_intelligence", "upstream_error", detail))
    else:
        detail = "Ticker is required for proxy biographies." if not ticker else "Proxy connector unavailable."
        source_status["proxy_intelligence"] = _source_state(PROXY_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)

    if SEC_EDGAR_AVAILABLE and ticker:
        try:
            cik = _resolve_interactive_cik(ticker)
            if cik:
                insider_payload = _call_with_timeout(
                    _build_interactive_insider_transactions_for_cik,
                    cik,
                    timeout=_CORRELATION_SOURCE_TIMEOUTS["insider_transactions"],
                )
                insider_transactions = _ensure_dict(
                    _ensure_dict(insider_payload or {}).get("insider_transactions") or {}
                )
                status, used, detail, code = _classify_interactive_insider_payload(insider_transactions)
                source_status["insider_transactions"] = _source_state(True, status, detail, used=used)
                if detail and code:
                    warnings.append(_warning("insider_transactions", code, detail))
            else:
                source_status["insider_transactions"] = _source_state(True, "no_data", "No filer CIK resolved for ticker.")
        except Exception as error:
            detail = _source_error_detail("insider_transactions", error)
            status = "timeout" if isinstance(error, TimeoutError) else "error"
            source_status["insider_transactions"] = _source_state(True, status, detail)
            warnings.append(_warning("insider_transactions", "timeout" if isinstance(error, TimeoutError) else "upstream_error", detail))
    else:
        detail = "Ticker is required for insider and board analysis." if not ticker else "SEC EDGAR connector unavailable."
        source_status["insider_transactions"] = _source_state(SEC_EDGAR_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)

    if BOARD_INTERLOCK_AVAILABLE and _has_insider_transaction_rows(insider_transactions) and cik:
        try:
            board_interlocks = _ensure_dict(get_board_interlocks(
                insider_transactions.get("transactions", []), cik, entity_name
            ) or {})
            source_status["board_interlocks"] = _source_state(True, "ok" if board_interlocks else "no_data", used=bool(board_interlocks))
        except Exception as error:
            detail = _public_error_detail(error)
            source_status["board_interlocks"] = _source_state(True, "error", detail)
            warnings.append(_warning("board_interlocks", "upstream_error", detail))
    else:
        source_status["board_interlocks"] = _source_state(
            BOARD_INTERLOCK_AVAILABLE,
            "missing_input" if not _has_insider_transaction_rows(insider_transactions) else "unavailable",
            "Requires ticker-resolved insider transactions.",
        )

    quote = _build_quote_context(ticker) if ticker else {}
    if INSTITUTIONAL_HOLDINGS_AVAILABLE and ticker:
        try:
            holders_report = _ensure_dict(get_institutional_holders(
                entity_name,
                ticker,
                quote.get("shares_outstanding"),
                quote.get("price"),
            ) or {})
            source_status["institutional_holders"] = _source_state(True, "ok" if holders_report else "no_data", used=bool(holders_report))
        except Exception as error:
            detail = _public_error_detail(error)
            source_status["institutional_holders"] = _source_state(True, "error", detail)
            warnings.append(_warning("institutional_holders", "upstream_error", detail))
    else:
        detail = "Ticker is required for 13F network analysis." if not ticker else "Institutional holdings connector unavailable."
        source_status["institutional_holders"] = _source_state(INSTITUTIONAL_HOLDINGS_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)

    if competitors and ticker and INSTITUTIONAL_OVERLAP_AVAILABLE:
        try:
            overlap_report = _ensure_dict(compare_competitor_ownership(ticker, competitors) or {})
            source_status["institutional_overlap"] = _source_state(True, "ok" if overlap_report else "no_data", used=bool(overlap_report))
        except Exception as error:
            detail = _public_error_detail(error)
            source_status["institutional_overlap"] = _source_state(True, "error", detail)
            warnings.append(_warning("institutional_overlap", "upstream_error", detail))
    else:
        detail = "Provide both ticker and competitors for overlap analysis." if not competitors else "Institutional overlap connector unavailable."
        source_status["institutional_overlap"] = _source_state(INSTITUTIONAL_OVERLAP_AVAILABLE, "missing_input" if not competitors else "unavailable", detail)

    founder_people = _extract_proxy_people(proxy_data)
    founder_graph = build_founder_correlation_graph(founder_people, company_name=entity_name)

    safe_depth = 1
    if depth > 1:
        warnings.append(
            _warning(
                "co_investment_network",
                "depth_limited",
                "Depth > 1 would rely on inferred second-degree holdings in the current service, so output is limited to grounded first-degree data.",
            )
        )

    coinvestment = {}
    concentration = {}
    coordinated = {}
    if holders_report:
        coinvestment = build_coinvestment_network(ticker or entity_name, holders_report, depth=safe_depth)
        concentration = analyze_position_concentration(holders_report, quote.get("shares_outstanding"))
        coordinated = find_coordinated_movements(ticker, historical_holdings=None)
        if not coordinated.get("position_changes"):
            warnings.append(
                _warning(
                    "coordinated_movements",
                    "no_historical_holdings",
                    "Historical multi-quarter holder series is not available through the current grounded pipeline.",
                )
            )

    return {
        "entity_name": entity_name,
        "ticker": ticker,
        "cik": cik,
        "founder_correlations": founder_graph,
        "board_interlocks": board_interlocks,
        "institutional_holders": holders_report,
        "co_investment_network": coinvestment,
        "position_concentration": concentration,
        "coordinated_movements": coordinated,
        "institutional_overlap": overlap_report,
        "source_status": source_status,
        "warnings": warnings,
        "partial": any(value["status"] in {"error", "timeout", "unavailable", "missing_input"} for value in source_status.values()),
    }


def build_correlation_analysis(
    entity_name: str,
    ticker: str = "",
    competitors: Optional[List[str]] = None,
    years: int = 2,
) -> Dict[str, Any]:
    overall_started = time.monotonic()
    logger.warning("correlation:start entity=%s ticker=%s", entity_name, ticker)
    ticker = _normalize_ticker(ticker)
    source_status: Dict[str, Dict[str, Any]] = {}
    warnings: List[Dict[str, str]] = []
    normalized_competitors = _normalize_competitors(ticker, competitors or [], warnings)

    insider_transactions: Dict[str, Any] = {}
    price_history: Dict[str, Any] = {}
    event_timeline: Dict[str, Any] = {}
    political_intelligence: Dict[str, Any] = {}
    contract_intelligence: Dict[str, Any] = {}
    deep_comparative: Dict[str, Any] = {}
    cik = None

    if SEC_EDGAR_AVAILABLE and ticker:
        try:
            cik_started = time.monotonic()
            logger.warning("resolve_cik:start ticker=%s", ticker)
            cik = get_filer_cik(ticker)
            logger.warning("resolve_cik:end elapsed=%.3fs", time.monotonic() - cik_started)
            if cik:
                insider_started = time.monotonic()
                logger.warning("insider:start cik=%s", cik)
                insider_transactions = _ensure_dict(get_insider_transactions(cik) or {})
                logger.warning("insider:end elapsed=%.3fs", time.monotonic() - insider_started)
                source_status["insider_transactions"] = _source_state(True, "ok" if insider_transactions else "no_data", used=bool(insider_transactions))
            else:
                source_status["insider_transactions"] = _source_state(True, "no_data", "No filer CIK resolved for ticker.")
        except Exception as error:
            detail = _public_error_detail(error)
            source_status["insider_transactions"] = _source_state(True, "error", detail)
            warnings.append(_warning("insider_transactions", "upstream_error", detail))
    else:
        detail = "Ticker is required for insider timing analysis." if not ticker else "SEC EDGAR connector unavailable."
        source_status["insider_transactions"] = _source_state(SEC_EDGAR_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)

    source_jobs: Dict[str, Any] = {}
    source_readers: Dict[str, Any] = {}
    source_timeouts: Dict[str, float] = {}

    if MARKET_DATA_AVAILABLE and ticker:
        source_jobs["price_history"] = (get_price_history, (ticker, 400), {})
        source_readers["price_history"] = lambda payload: _ensure_dict(payload or {})
        source_timeouts["price_history"] = _CORRELATION_SOURCE_TIMEOUTS["price_history"]
    else:
        detail = "Ticker is required for price history." if not ticker else "Market data connector unavailable."
        source_status["price_history"] = _source_state(MARKET_DATA_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)

    if TIMELINE_AVAILABLE and ticker:
        source_jobs["event_timeline"] = (_build_correlation_event_timeline, (ticker, years, cik), {})
        source_readers["event_timeline"] = lambda payload: _ensure_dict(payload or {})
        source_timeouts["event_timeline"] = _CORRELATION_SOURCE_TIMEOUTS["event_timeline"]
    else:
        detail = "Ticker is required for event timeline analysis." if not ticker else "Timeline connector unavailable."
        source_status["event_timeline"] = _source_state(TIMELINE_AVAILABLE, "missing_input" if not ticker else "unavailable", detail)

    if POLITICAL_AVAILABLE:
        source_jobs["political_intelligence"] = (_build_correlation_political_intelligence, (entity_name,), {})
        source_readers["political_intelligence"] = lambda payload: _ensure_dict(payload or {})
        source_timeouts["political_intelligence"] = _CORRELATION_SOURCE_TIMEOUTS["political_intelligence"]
    else:
        source_status["political_intelligence"] = _source_state(False, "unavailable", "OpenSecrets connector unavailable.")

    if CONTRACTS_AVAILABLE:
        source_jobs["contract_intelligence"] = (_build_correlation_contract_portfolio, (entity_name,), {})
        source_readers["contract_intelligence"] = lambda payload: _ensure_dict(payload or {})
        source_timeouts["contract_intelligence"] = _CORRELATION_SOURCE_TIMEOUTS["contract_intelligence"]
    else:
        source_status["contract_intelligence"] = _source_state(False, "unavailable", "FPDS/USASpending connector unavailable.")

    if normalized_competitors and ticker and DEEP_COMPARATIVE_AVAILABLE:
        source_jobs["deep_comparative"] = (run_deep_comparative_analysis, (ticker, normalized_competitors, cik), {})
        source_readers["deep_comparative"] = lambda payload: _ensure_dict(payload or {})
        source_timeouts["deep_comparative"] = _CORRELATION_SOURCE_TIMEOUTS["deep_comparative"]
    else:
        detail = "Provide both ticker and competitors for comparative analysis." if not normalized_competitors else "Deep comparative service unavailable."
        source_status["deep_comparative"] = _source_state(DEEP_COMPARATIVE_AVAILABLE, "missing_input" if not normalized_competitors else "unavailable", detail)

    if source_jobs:
        source_started = time.monotonic()
        for source, outcome in _run_correlation_source_jobs(source_jobs, source_timeouts).items():
            ok, value = outcome
            try:
                if not ok:
                    raise value
                payload = source_readers[source](value)
                if source == "price_history":
                    price_history = payload
                    has_data = bool(price_history)
                    status = "ok" if has_data else "no_data"
                elif source == "event_timeline":
                    event_timeline = payload
                    has_data = _timeline_has_events(event_timeline)
                    status = "ok" if has_data else "no_data"
                elif source == "political_intelligence":
                    political_intelligence = payload
                    status = _political_status(political_intelligence)
                    has_data = status == "ok"
                    if status in {"unavailable", "rate_limited", "error"}:
                        detail = str(political_intelligence.get("error") or "Political intelligence source unavailable.")
                        warnings.append(_warning("political_intelligence", status, detail))
                elif source == "contract_intelligence":
                    contract_intelligence = payload
                    has_data = _contract_payload_has_data(contract_intelligence)
                    status = "ok" if has_data else "no_data"
                else:
                    deep_comparative = payload
                    has_data = _deep_comparative_has_data(deep_comparative)
                    status = "ok" if has_data else "no_data"
                source_status[source] = _source_state(True, status, used=has_data)
                if source == "political_intelligence" and status in {"unavailable", "rate_limited", "error"}:
                    source_status[source]["detail"] = str(political_intelligence.get("error") or "Political intelligence source unavailable.")
            except Exception as error:
                detail = _source_error_detail(source, error)
                status = "timeout" if isinstance(error, TimeoutError) else "error"
                source_status[source] = _source_state(True, status, detail)
                warnings.append(_warning(source, "timeout" if isinstance(error, TimeoutError) else "upstream_error", detail))
        logger.warning("correlation:sources:end elapsed=%.3fs", time.monotonic() - source_started)

    correlation_input = {
        "insider_transactions": insider_transactions,
        "price_history": price_history,
        "event_timeline": event_timeline,
        "political_intelligence": political_intelligence,
        "contract_intelligence": contract_intelligence,
    }
    correlation_suite_started = time.monotonic()
    correlations = run_correlation_suite(correlation_input)
    logger.warning("correlation:suite:end elapsed=%.3fs", time.monotonic() - correlation_suite_started)
    logger.warning("build_correlation_analysis:return ticker=%s elapsed=%.3fs", ticker, time.monotonic() - overall_started)

    return {
        "entity_name": entity_name,
        "ticker": ticker,
        "cik": cik,
        "correlations": correlations,
        "deep_comparative": deep_comparative,
        "source_status": source_status,
        "warnings": warnings,
        "partial": any(value["status"] in {"error", "timeout", "unavailable", "missing_input"} for value in source_status.values()),
    }


def build_contract_probability_analysis(
    entity_name: str,
    ticker: str = "",
    naics_codes: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    total_revenue: Optional[float] = None,
) -> Dict[str, Any]:
    warnings: List[Dict[str, str]] = []
    analysis = analyze_contract_probability(
        entity_name,
        ticker=ticker,
        naics_codes=naics_codes or None,
        keywords=keywords or None,
        total_revenue=total_revenue,
    )

    if analysis.get("historical_performance", {}).get("total_awards_5yr", 0) == 0:
        warnings.append(
            _warning(
                "contract_probability",
                "limited_contract_history",
                "No significant historical awards were identified in the current USASpending-backed lookup.",
            )
        )
        if isinstance(analysis.get("opportunity_pipeline"), dict):
            analysis["opportunity_pipeline"]["weighted_avg_win_probability"] = None

    if analysis.get("opportunity_pipeline", {}).get("opportunities_identified", 0) == 0:
        warnings.append(
            _warning(
                "contract_probability",
                "no_open_opportunities",
                "No open SAM.gov opportunities were returned or the SAM API key is unavailable.",
            )
        )

    return {
        "entity_name": entity_name,
        "ticker": ticker,
        "analysis": analysis,
        "warnings": warnings,
        "partial": bool(warnings),
    }


def build_interactive_report_html(
    db: Session,
    entity_name: str,
    entity_type: str = "org",
    ticker: str = "",
) -> Dict[str, Any]:
    report = generate_enhanced_intelligence_report(
        db,
        entity_name=entity_name,
        entity_type=entity_type,
        ticker=ticker or None,
    )
    if report.get("error"):
        raise RuntimeError(report["error"])
    return render_interactive_report_from_report(report)


def render_interactive_report_from_report(report: Dict[str, Any]) -> Dict[str, Any]:
    sections = report.get("sections") or []
    entity_name = report.get("entity_name") or report.get("ticker") or "Entity"
    ticker = report.get("ticker") or ""
    interactive_meta = _ensure_dict(report.get("interactive_report") or {})
    graph_data = _ensure_dict(interactive_meta.get("graph_data") or {})
    if not graph_data:
        raise RuntimeError(
            "Interactive rendering is only available for newly generated compatible reports."
        )
    markdown_content = _build_markdown_from_sections(entity_name, sections)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as handle:
        temp_path = Path(handle.name)

    try:
        result = generate_interactive_report(
            markdown_content,
            graph_data,
            str(temp_path),
            entity_name=entity_name,
            ticker=ticker,
        )
        if not result.get("written"):
            raise RuntimeError(result.get("reason", "Interactive report generation failed."))
        html_text = temp_path.read_text(encoding="utf-8")
        return {
            "html": html_text,
            "meta": result,
            "report_id": report.get("report_id"),
            "base_report_id": report.get("base_report_id"),
        }
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
