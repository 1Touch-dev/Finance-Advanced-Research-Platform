"""
Shared HTTP client for SEC EDGAR.

Every SEC-backed connector previously carried its own rate limiter, or none at
all. Each stayed within the published ten-requests-per-second ceiling on its
own, but a single report run drives six of them, so the combined rate exceeded
the budget and EDGAR answered 429. None of the callers retried, so a throttled
response was indistinguishable from missing data: the board roster, the
institutional holdings and the valuation would simply come back empty, and the
report rendered around the gap without saying why.

One limiter shared across the process fixes the rate, and honouring Retry-After
fixes the recovery.
"""

import logging
import os
import threading
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SEC_HEADERS = {
    "User-Agent": os.getenv("SEC_USER_AGENT")
    or "FinanceIntelPlatform/1.0 research@example.com",
    "Accept-Encoding": "gzip, deflate",
}

# SEC publishes a ten-per-second ceiling. Sustained bursts at exactly that rate
# still draw throttling, so the shared budget is set slightly below it.
_MIN_INTERVAL = float(os.getenv("SEC_MIN_REQUEST_INTERVAL", "0.15"))
_MAX_ATTEMPTS = int(os.getenv("SEC_MAX_ATTEMPTS", "4"))

# Ceiling on total time one logical SEC call may spend, retries and backoff
# included. Without it, a fan-out endpoint that makes five SEC calls while the
# network is unreachable spends 5 x (timeout + 2 + 4 + 8) and blows past a
# minute, which is how /ontology/* and /filings/* reached 60s.
_DEADLINE = float(os.getenv("SEC_REQUEST_DEADLINE", "20"))

_lock = threading.Lock()
_last_request = 0.0

# Requests abandoned after exhausting retries. A report whose sections are thin
# because EDGAR was throttling should say so rather than presenting the gap as
# an absence of filings.
_throttled = 0


def throttled_count() -> int:
    """Requests this process gave up on after repeated 429 or 5xx responses."""
    return _throttled


def reset_throttled_count() -> None:
    global _throttled
    _throttled = 0


def _throttle() -> None:
    """Space requests across every caller in this process."""
    global _last_request
    with _lock:
        elapsed = time.time() - _last_request
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        _last_request = time.time()


def sec_get(url: str, *, headers: Optional[dict] = None, timeout: int = 30,
            attempts: int = _MAX_ATTEMPTS, deadline: Optional[float] = None,
            **kwargs) -> Optional[requests.Response]:
    """GET an SEC URL, respecting the shared rate budget.

    Retries on 429 and on 5xx, backing off exponentially and honouring
    Retry-After when EDGAR supplies it. Returns None once the attempts are
    exhausted so callers can distinguish "throttled" from "empty", rather than
    receiving a 429 error page and parsing it as though it were a filing.

    ``deadline`` caps total wall-clock time across all attempts. Connection
    errors are not retried: an unreachable host or a blocked proxy will not
    recover within a request, so backing off only burns the caller's budget.
    """
    request_headers = dict(SEC_HEADERS)
    if headers:
        request_headers.update(headers)

    budget = _DEADLINE if deadline is None else deadline
    started = time.monotonic()
    timeout = min(timeout, budget)

    def remaining() -> float:
        return budget - (time.monotonic() - started)

    for attempt in range(1, attempts + 1):
        if remaining() <= 0:
            logger.warning("SEC deadline of %.0fs exhausted for %s", budget, url)
            return None
        _throttle()
        try:
            response = requests.get(url, headers=request_headers,
                                    timeout=max(1.0, min(timeout, remaining())), **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            # Unreachable host / blocked proxy / timeout: retrying in-request
            # cannot help, so fail fast instead of sleeping 2+4+8s.
            logger.warning("SEC unreachable for %s: %s", url, exc)
            return None
        except requests.RequestException as exc:
            logger.warning("SEC request error (attempt %d/%d) for %s: %s",
                           attempt, attempts, url, exc)
            if attempt == attempts:
                return None
            time.sleep(min(2 ** attempt, 16, max(0.0, remaining())))
            continue

        if response.status_code == 429 or response.status_code >= 500:
            if attempt == attempts:
                global _throttled
                _throttled += 1
                logger.error("SEC returned %d after %d attempts for %s",
                             response.status_code, attempts, url)
                return None
            retry_after = response.headers.get("Retry-After")
            try:
                delay = float(retry_after) if retry_after else min(2 ** attempt, 16)
            except ValueError:
                delay = min(2 ** attempt, 16)
            delay = min(delay, max(0.0, remaining()))
            if delay <= 0:
                logger.warning("SEC deadline of %.0fs exhausted for %s", budget, url)
                return None
            logger.warning("SEC %d for %s; retrying in %.1fs (attempt %d/%d)",
                           response.status_code, url, delay, attempt, attempts)
            time.sleep(delay)
            continue

        return response

    return None


def sec_get_text(url: str, **kwargs) -> str:
    """Document body, or an empty string if it could not be retrieved."""
    response = sec_get(url, **kwargs)
    if response is None or not response.ok:
        return ""
    return response.text


def sec_get_json(url: str, **kwargs):
    """Parsed JSON, or None if the request or the parse failed."""
    response = sec_get(url, headers={"Accept": "application/json"}, **kwargs)
    if response is None or not response.ok:
        return None
    try:
        return response.json()
    except ValueError:
        logger.warning("SEC response for %s was not valid JSON", url)
        return None
