"""California SOS connector.

Priority waterfall:
  1. Official CA SOS CBC API (calico.sos.ca.gov) — free, requires subscription key
  2. BizFile Online public search scrape (bizfileonline.sos.ca.gov) — free, no key needed
  3. Cobalt Intelligence API — paid third-party, kept as tertiary backup
  4. Embedded sample records — always available for tests / offline runs
"""
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from us._common.http_helpers import ensure_playwright_platform, http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.cobalt_fallback import cobalt_search
from us.state_registry.schema import normalize

CA_API_BASE = "https://calico.sos.ca.gov/cbc/v1/api"
BIZFILE_SEARCH_URL = "https://bizfileonline.sos.ca.gov/search/business"
BIZFILE_API_URL = "https://bizfileonline.sos.ca.gov/api/Records/businesssearch"

SEED_QUERIES = ["Apple", "Google", "Services", "Technologies", "Inc"]

# Headers that pass BizFile's Imperva WAF when used with a real browser session
_BIZFILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "https://bizfileonline.sos.ca.gov",
    "Referer": "https://bizfileonline.sos.ca.gov/search/business",
}


class CaliforniaSOSConnector(StateRegistryConnector):
    name = "state_us_ca"
    jurisdiction_code = "us_ca"
    source_tier = "api"
    source_url = BIZFILE_SEARCH_URL

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return

        # Tier 1: official CA SOS CBC API (requires subscription key)
        api_key = os.getenv("CA_SOS_API_KEY", "").strip()
        if api_key:
            records = list(_api_fetch(api_key))
            if records:
                yield from records
                return

        # Tier 2: BizFile public search scrape (free, official source)
        bizfile_records = list(_bizfile_fetch())
        if bizfile_records:
            yield from bizfile_records
            return

        # Tier 3: Cobalt Intelligence (paid, tertiary backup)
        cobalt_records = list(_cobalt_fetch())
        if cobalt_records:
            yield from cobalt_records
            return

        yield from _sample_records()

    def normalize(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return normalize(
            jurisdiction_code=self.jurisdiction_code,
            entity_id=external_id,
            legal_name=payload.get("legal_name", ""),
            raw_status=payload.get("status"),
            raw_entity_type=payload.get("entity_type"),
            formation_date=payload.get("formation_date"),
            source_tier=self.source_tier,
            source_url=self.source_url,
        )


def _api_headers(api_key: str) -> Dict[str, str]:
    return {
        "Ocp-Apim-Subscription-Key": api_key,
        "Accept": "application/json",
    }


def _map_entity(item: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    eid = str(item.get("EntityID") or item.get("entityID") or "")
    name = item.get("EntityName") or item.get("entityName") or ""
    if not eid and not name:
        return None
    return eid or name, {
        "legal_name": name,
        "status": item.get("StatusDescription") or item.get("statusDescription") or "",
        "entity_type": item.get("EntityType") or item.get("entityType") or "",
        "formation_date": item.get("FilingDate") or item.get("filingDate"),
        "registered_agent_name": item.get("AgentName") or item.get("agentName"),
        "jurisdiction": item.get("Jurisdiction") or item.get("jurisdiction"),
    }


def _parse_keyword_response(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("EntityData") or data.get("entityData") or []
    return []


def _api_fetch(api_key: str) -> Iterable[Tuple[str, Dict[str, Any]]]:
    seen: set = set()
    for query in SEED_QUERIES[:3]:
        try:
            url = f"{CA_API_BASE}/BusinessEntityKeywordSearch"
            resp = http_get(
                url,
                params={"search-term": query},
                headers=_api_headers(api_key),
                timeout=30,
            )
            for item in _parse_keyword_response(resp.json()):
                mapped = _map_entity(item)
                if not mapped:
                    continue
                eid, payload = mapped
                if eid in seen:
                    continue
                seen.add(eid)
                yield eid, payload
        except Exception as exc:
            print(f"[us_ca] keyword search error ({query!r}): {exc}")

    if seen:
        return

    # Fallback: known public entity number (Apple Inc in CA)
    try:
        url = f"{CA_API_BASE}/BusinessEntityDetails"
        resp = http_get(
            url,
            params={"entity-number": "0806597"},
            headers=_api_headers(api_key),
            timeout=30,
        )
        data = resp.json()
        if isinstance(data, dict) and data.get("EntityID"):
            mapped = _map_entity(data)
            if mapped:
                eid, payload = mapped
                seen.add(eid)
                yield eid, payload
    except Exception as exc:
        print(f"[us_ca] entity details error: {exc}")

    if not seen:
        return


def _bizfile_fetch(
    queries: Optional[List[str]] = None,
    max_per_query: int = 50,
) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """
    Scrape BizFile Online (bizfileonline.sos.ca.gov) — free, official, no key required.

    Strategy:
      1. POST to /api/Records/businesssearch with browser-mimicking headers.
         BizFile's Imperva WAF accepts requests that carry a valid `reese84`
         anti-bot cookie. We bootstrap one session by doing a plain GET to the
         search page first, which lets Imperva set the cookie, then reuse that
         session for the JSON POST.
      2. If the API POST is blocked (403/empty), fall back to Playwright DOM
         extraction — launch a real browser, type the query, wait for the table
         to render, then extract rows from the DOM.
      3. If Playwright is unavailable, return nothing (caller will try Cobalt).
    """
    import requests  # stdlib-style import; present in all supported envs

    queries = queries or SEED_QUERIES[:3]
    seen: set = set()
    total = 0

    session = requests.Session()
    session.headers.update(_BIZFILE_HEADERS)

    # Bootstrap session — Imperva issues anti-bot cookies on the first GET
    try:
        session.get(BIZFILE_SEARCH_URL, timeout=20)
        time.sleep(1)
    except Exception as exc:
        print(f"[us_ca/bizfile] session bootstrap failed: {exc}")

    for query in queries:
        api_records = list(_bizfile_api_query(session, query, max_per_query, seen))
        if api_records:
            for item in api_records:
                total += 1
                yield item
            continue

        # API blocked — try Playwright DOM scrape
        playwright_records = list(_bizfile_playwright_query(query, max_per_query, seen))
        for item in playwright_records:
            total += 1
            yield item

    print(f"[us_ca/bizfile] yielded {total} records across {len(queries)} queries")


def _bizfile_api_query(
    session: Any,
    query: str,
    limit: int,
    seen: set,
) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """POST to BizFile JSON API and parse results."""
    payload = {
        "SEARCH_VALUE": query,
        "SEARCH_FILTER_TYPE_ID": "0",
        "SEARCH_TYPE_ID": "1",
        "FILING_TYPE_ID": "0",
        "STATUS_ID": "0",
        "FILING_DATE": "",
    }
    try:
        resp = session.post(BIZFILE_API_URL, json=payload, timeout=30)
        if resp.status_code != 200 or not resp.content:
            print(f"[us_ca/bizfile] API returned {resp.status_code} for {query!r}")
            return
        data = resp.json()
        rows = data if isinstance(data, list) else (data.get("rows") or data.get("data") or [])
        count = 0
        for row in rows:
            if count >= limit:
                break
            mapped = _map_bizfile_row(row)
            if not mapped:
                continue
            eid, payload_out = mapped
            if eid in seen:
                continue
            seen.add(eid)
            count += 1
            yield eid, payload_out
    except Exception as exc:
        print(f"[us_ca/bizfile] API query error ({query!r}): {exc}")


def _bizfile_playwright_query(
    query: str,
    limit: int,
    seen: set,
) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """
    Launch a headless Chromium via Playwright, perform a BizFile search,
    and extract rows from the rendered table.

    BizFile is an Angular SPA — after clicking "Execute search" we wait for
    the results table (<table> with class containing 'results') to appear.

    Column order confirmed from live DOM inspection 2026-06-15:
      0: entity name (with entity number in parentheses)
      1: formation date  MM/DD/YYYY
      2: status
      3: entity type
      4: jurisdiction (state)
      5: registered agent name
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[us_ca/bizfile] Playwright not installed — skipping browser scrape")
        return

    ensure_playwright_platform()

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
            except Exception as browser_err:
                msg = str(browser_err)
                if "Executable doesn't exist" in msg or "not supported" in msg.lower():
                    print(
                        "[us_ca/bizfile] Chromium not installed — run: "
                        "PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 playwright install chromium && "
                        "playwright install-deps chromium"
                    )
                elif "shared libraries" in msg or "libatk" in msg:
                    print("[us_ca/bizfile] Missing browser deps — run: playwright install-deps chromium")
                else:
                    print(f"[us_ca/bizfile] Chromium launch failed: {browser_err}")
                return
            ctx = browser.new_context(
                user_agent=_BIZFILE_HEADERS["User-Agent"],
                locale="en-US",
            )
            page = ctx.new_page()
            page.goto(BIZFILE_SEARCH_URL, wait_until="networkidle", timeout=30000)

            # Type query and submit
            page.fill("input[placeholder*='name or file number']", query)
            page.click("button[aria-label*='Execute search'], button[title*='search']")

            # Wait for results table to load (Angular renders it asynchronously)
            try:
                page.wait_for_selector("table tbody tr", timeout=15000)
            except Exception:
                print(f"[us_ca/bizfile] Playwright: no table rows for {query!r}")
                browser.close()
                return

            # Extract rows via JS evaluation for speed
            rows_data = page.evaluate(
                """() => {
                    const rows = document.querySelectorAll('table tbody tr');
                    const result = [];
                    for (const r of rows) {
                        const cells = r.querySelectorAll('td');
                        if (cells.length >= 3) {
                            result.push([...cells].map(c => c.textContent.trim()));
                        }
                    }
                    return result;
                }"""
            )
            browser.close()

        count = 0
        for cells in (rows_data or []):
            if count >= limit:
                break
            mapped = _parse_bizfile_dom_row(cells)
            if not mapped:
                continue
            eid, payload_out = mapped
            if eid in seen:
                continue
            seen.add(eid)
            count += 1
            yield eid, payload_out

    except Exception as exc:
        print(f"[us_ca/bizfile] Playwright scrape error ({query!r}): {exc}")


# ── BizFile row parsers ────────────────────────────────────────────────────────

_ENTITY_NUM_RE = re.compile(r"\(([A-Z0-9]+)\)\s*(?:Click to expand)?$", re.IGNORECASE)


def _parse_bizfile_dom_row(
    cells: List[str],
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Parse a list of cell text strings extracted from a BizFile DOM table row.

    Expected column order (confirmed 2026-06-15):
      0: "ENTITY NAME (EntityNumber)Click to expand"
      1: formation date MM/DD/YYYY
      2: status
      3: entity type
      4: jurisdiction
      5: registered agent name
    """
    if not cells:
        return None

    name_cell = cells[0]
    m = _ENTITY_NUM_RE.search(name_cell)
    eid = m.group(1) if m else ""
    name = _ENTITY_NUM_RE.sub("", name_cell).strip()
    if not name:
        return None
    key = eid or name[:64]

    return key, {
        "legal_name": name,
        "formation_date": _parse_date(cells[1]) if len(cells) > 1 else None,
        "status": cells[2].strip() if len(cells) > 2 else "",
        "entity_type": cells[3].strip() if len(cells) > 3 else "",
        "jurisdiction": cells[4].strip() if len(cells) > 4 else "",
        "registered_agent_name": cells[5].strip() if len(cells) > 5 else "",
        "source_tier": "scrape_bizfile",
    }


def _map_bizfile_row(row: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Map a JSON row returned by the BizFile /api/Records/businesssearch endpoint.
    Field names determined from API response inspection; we handle camelCase and
    UPPER_SNAKE variants defensively.
    """
    eid = str(
        row.get("ENTITY_NUM")
        or row.get("entityNum")
        or row.get("FILE_NUM")
        or row.get("fileNum")
        or ""
    )
    name = (
        row.get("ENTITY_NAME")
        or row.get("entityName")
        or row.get("NAME")
        or row.get("name")
        or ""
    )
    if not name:
        return None
    key = eid or name[:64]
    return key, {
        "legal_name": name,
        "formation_date": _parse_date(
            row.get("INITIAL_FILING_DATE") or row.get("initialFilingDate") or row.get("FILING_DATE") or ""
        ),
        "status": row.get("ENTITY_STATUS") or row.get("entityStatus") or row.get("STATUS") or "",
        "entity_type": row.get("ENTITY_TYPE") or row.get("entityType") or row.get("TYPE") or "",
        "registered_agent_name": row.get("AGENT_NAME") or row.get("agentName") or "",
        "source_tier": "scrape_bizfile",
    }


def _parse_date(raw: str) -> Optional[str]:
    """Normalise MM/DD/YYYY or YYYY-MM-DD to YYYY-MM-DD; return None on failure."""
    if not raw:
        return None
    raw = raw.strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", raw)
    if m:
        return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        return raw[:10]
    return None


def _cobalt_fetch() -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Interim live CA data while CA SOS subscription is pending approval."""
    seen: set = set()
    for query in SEED_QUERIES[:2]:
        for row in cobalt_search("ca", query):
            eid = str(row.get("sos_id") or row.get("legal_name") or "")
            if not eid or eid in seen:
                continue
            seen.add(eid)
            yield eid, {
                "legal_name": row.get("legal_name", ""),
                "status": row.get("status", ""),
                "entity_type": row.get("entity_type", ""),
                "formation_date": row.get("formation_date"),
                "registered_agent_name": row.get("registered_agent_name"),
            }


def _sample_records() -> Iterable[Tuple[str, Dict[str, Any]]]:
    samples = [
        {"id": "CA001", "legal_name": "APPLE INC", "status": "Active", "entity_type": "Domestic Stock Corporation"},
        {"id": "CA002", "legal_name": "GOOGLE LLC", "status": "Active", "entity_type": "Foreign Limited Liability Company"},
        {"id": "CA003", "legal_name": "NETFLIX INC", "status": "Active", "entity_type": "Domestic Stock Corporation"},
        {"id": "CA004", "legal_name": "SILICON VALLEY SERVICES LLC", "status": "Active", "entity_type": "Domestic Limited Liability Company"},
    ]
    for s in samples:
        eid = s["id"]
        yield eid, {
            "legal_name": s["legal_name"],
            "status": s["status"],
            "entity_type": s["entity_type"],
            "formation_date": None,
        }
