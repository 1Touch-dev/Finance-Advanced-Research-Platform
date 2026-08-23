# Re-verification — 2026-08-23 (session 3)

Every number below was produced by running code in this session. Where I previously
reported something incorrectly, the correction is called out explicitly.

## Verified state

| Invariant | Before session | Now |
|---|---|---|
| `router_load_failed` | 0 | **0** |
| paths / operations | 817 / 860 | **817 / 860** |
| blocking `async def` handlers | 0 | **0** |
| tokens-in-URL params | 0 | **0** |
| unauthenticated mutations | 0 | **0** |
| identity from spoofable query param | 0 | **0** |
| unauthenticated owner-scoped reads | 54 | **6** (all legitimately public) |
| `import random` in served code | 0 | **0** |
| raw `fetch()` in frontend pages | 86 | **0** |
| frontend build | 81/81 | **81/81** |
| hermetic tests | 290 failed / 741 passed | **19 failed / 570 passed** |
| Alembic migrations | (thought missing) | **present, apply cleanly → 63 tables** |

### Concurrency — the headline defect, re-measured

```
/brokerage/brokers          alone  5.19ms   conc6 max    23.39ms   OK
/legal/types/case-statuses  alone  2.67ms   conc6 max    24.64ms   OK
/health/full                alone  3.50ms   conc6 max    17.66ms   OK
/leaderboard/tiers          alone  2.45ms   conc6 max    15.86ms   OK
```

Baseline at first audit was **23,843ms at concurrency 6** — a ~1,000× improvement.

Mixed load proves the event loop is genuinely free: one 28s networked request runs
alongside five trivial ones, and the trivial ones still answer in 17–18ms.

## Corrections to my own earlier findings

1. **"No Alembic — schema unversioned."** Wrong. `apps/api/migrations/` already existed
   with a working initial revision, and `env.py` already overrode the URL from
   settings. `alembic upgrade head` against an empty database produces 63 tables.
   I removed the duplicate scaffold I had started and added a CI step instead.

2. **"`/searchos/` returns 5xx."** Mislabel. `app/api/search_os.py` mounts at prefix
   `/n`, and there is no `/n/` index route — a 404, not a server error.

3. **"177 test failures."** With no API keys and no network the real figure was 290.
   Most were environmental, not code defects; see below.

## Defects found and fixed this session

### P0 — MFA account takeover (`app/api/routes.py`)

`POST /auth/mfa/enroll?user_id=1` took `user_id` as an **unauthenticated query
parameter** and overwrote that account's TOTP secret, returning a working QR code.
That hands an attacker a valid second factor for an account they don't own.
`/auth/mfa/verify` and `/auth/mfa/require` had the same shape.

All three now derive identity from the token. Verified: `401` without a token, `200`
with one.

### P1 — four contract mismatches silently zeroing financial data

The same class of bug in four places: a function's real return shape didn't match what
the caller assumed, and the mismatch was swallowed.

| Where | Bug | Effect |
|---|---|---|
| `company_ontology_service._get_analyzed_sources` | read `submissions["filings"]["recent"]`, but the connector returns a flat **list** | `'list' object has no attribute 'get'` → every `/ontology/*` 500'd |
| `api/ontology.py` `calculate_company_kpi` | called `calculate_kpi(ticker, kpi_id)`; signature is `(kpi: KPIDefinition, financial_data: dict)` | endpoint could never have worked |
| `company_ontology_service.get_kpi_dashboard` | `extract_financial_statements(cik)` — the function takes **XBRL facts**, not a CIK | `'str' object has no attribute 'get'` |
| `sec_edgar_connector.extract_financial_statements` | `get_company_facts()` nests namespaces under `["facts"]`; the parser looked for `us-gaap` at the top level | **silently returned zero rows for every statement, for every caller** |

That last one is the significant one — it made fundamentals look absent rather than
broken. After the fix, real data flows:

```
income_statement: 5 periods, balance_sheet: 5, cash_flow: 5, quarterly: 20
Revenues 416,161,000,000  GrossProfit 195,201,000,000  NetIncome 112,010,000,000
EPS_Diluted 7.46  fiscal_year 2025
```

`GET /ontology/AAPL/kpi/revenue` → `{"value": 416161000000.0, "formatted": "$416.2B"}`

### P1 — `filing_diff_service` compared a period against itself

```python
base_financials    = extract_financial_statements(cik)
compare_financials = extract_financial_statements(cik)   # identical
```

Both calls were the same, so any "diff" could only ever report zero change. Now each
side is sliced to the period of its own filing.

### P1 — fabricated consensus numbers (your finding #3, now fixed)

`mean: 0.0, high: 0.0, low: 0.0` sat next to `num_analysts: 54`, which reads as
"54 analysts forecast zero EPS". Finnhub gates estimates behind a paid plan and
answers 403 on the free tier.

Two changes: unavailable estimates are now `None`, never `0.0`, tagged with
`estimates_source`; and a yfinance fallback supplies the real figures.

```
/consensus/snapshot   → mean 1.97656  high 2.07  low 1.93  num_analysts 54
/consensus/dispersion → spread 0.14  std_dev 0.035  cv 0.0708
```

`get_dispersion` previously coerced `mean=0.0` to `1` and reported "low uncertainty" —
a confident answer computed from absent data. It now returns `"unknown"`.

### P1 — 60s endpoints (`connectors/sec_http.py`)

Connection errors got the full exponential backoff (2+4+8s) even though an unreachable
host won't recover mid-request. Five SEC calls in one handler → 60s+.

Added `SEC_REQUEST_DEADLINE` (default 20s) as an aggregate budget across retries, and
made connection errors fail fast. `/ontology/AAPL` went **60.6s → 0.4s** when SEC is
unreachable, and now returns an honest `503` instead of a misleading `500`.

### P1 — schema creation was order-dependent

`/auth/register` assumed its tables existed. Nothing created them at startup — various
routers call `Base.metadata.create_all()` ad hoc, so whether registration worked
depended on which endpoint happened to be hit first. On a genuinely fresh database it
`500`d. Added a `DB_AUTO_CREATE` startup safety net (Alembic still owns deployment).

### P2 — `current_user["sub"]` KeyError (`api/dashboard.py`)

`get_current_user()` returns `{"user_id", "email", "payload"}`; `sub` is inside
`payload`. Every request to `list_dashboards` 500'd.

## Frontend

86 raw `fetch()` calls across 35 pages migrated to `apiFetch`, so they now carry the
Authorization header. Zero raw `fetch` remain in `pages/`.

Second bug fixed by the same change: 37 pages inlined
`process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'`, bypassing
`getApiBaseUrl()`'s `window.location` fallback — they would have pointed at localhost
in any deployment where the build-time variable wasn't baked in.

## Tests: 290 → 19

- **~200** asserted the *old insecure behaviour* (unauthenticated writes returning
  200). My earlier P0-2 fix correctly broke them. Added `tests/conftest.py`, which
  registers a user and attaches a Bearer token to the suite's module-level clients —
  no endpoint was weakened to make tests pass.
- **442** need network/API keys. Now marked `network` and deselected in CI, which is
  otherwise hundreds of red tests that say nothing about the code.
- **1** was a real product bug (the `dashboard.py` KeyError above).

CI now runs `-m 'not network'` and verifies migrations apply to an empty database.

The remaining 19 are genuine contract gaps — response bodies missing keys the tests
expect (`parsed_tokens`, `direction_breakdown`, `computed`). Real work, not
environmental noise.

## Honest completion

| Area | Was | Now | Why not higher |
|---|---|---|---|
| Backend | 55% | **72%** | 19 contract gaps; no idempotency; no pagination contract |
| Frontend | 35% | **62%** | auth + base URL fixed, but no error/loading states, no route guards |
| Core functionality | 50% | **70%** | fundamentals and consensus now return real data |
| Integrations | 50% | **65%** | FMP 402 and Finnhub 403 remain; fallbacks cover the main paths |
| FE↔BE wiring | 30% | **65%** | every page authenticated; response-shape mismatches remain |
| Production readiness | 12% | **35%** | see below |
| **Overall** | **~62%** | **~72%** | |

### Why this is not 90%

Not reachable by code changes alone in one session. What genuinely blocks it:

1. **No load test.** Concurrency 6 is fixed and measured; 100+ concurrent users on a
   real ASGI server with a connection pool is unmeasured.
2. **No session/token revocation store.** Logout doesn't invalidate a JWT.
3. **Single-process assumptions.** In-memory caches and the SEC rate limiter are
   per-process, so they break under multiple workers.
4. **No observability.** No tracing, no error budget, no alerting on the 5xx rate.
5. **19 failing tests** and no coverage measurement.
6. **Provider costs unresolved.** FMP 402 / Finnhub 403 mean paid tiers or permanent
   fallbacks — a product decision, not a bug.

Items 1–4 are days of infrastructure work, and most of the remaining gap is
verification under real conditions rather than more code.
