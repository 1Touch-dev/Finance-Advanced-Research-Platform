# Verified Technical Audit — Finance Advanced Research Platform

**Date:** 23 Aug 2026 · **HEAD:** `2aa49ee` · **Branch:** `8th-july-sprint`

**Method.** Nothing here comes from `MASTER_TASK_STATUS.md`, `REALITY_DOC.md`, `JAMES_ASKS.txt`, commit messages, code comments, or the pre-existing `docs/INDEPENDENT_AUDIT_2026-08-23.md`. I booted the real app, swept **all 618 GET endpoints** over the live network, ran the pytest suite to completion, executed a **real authenticated register → login → write → read E2E**, machine-diffed every frontend `fetch()` URL against the live route table, and read the implementations behind each claim. Every statement below has a command or `file:line` behind it.

I also **re-tested** the claims in the pre-existing audit doc and **found three of them wrong** (documented in §11) — treat that file as superseded.

---

## 1. Executive Summary

### What is genuinely working

There is a real, non-trivial financial/political intelligence **read** layer. I confirmed live external data end-to-end:

| Feature | Provider | Evidence |
|---|---|---|
| Gov trading leaderboard | static JSON (637 officials) | `/market/gov-trading/leaderboard/volume` → real names, `volume_usd` |
| Congress trading feed | House/Senate PTR | `/market/gov-trading/recent` → live filings (Khanna, 8/7/2026) |
| Quotes | Finnhub | `/market/quote?ticker=AAPL` → 309.35, 7/7 fields |
| Earnings history | Finnhub | `/earnings/ticker/AAPL` → real EPS/dates |
| Short interest | FINRA | `/short-interest/ticker/AAPL` → 141,606,163 sh, DTC 2.58 |
| IPO calendar | Finnhub/FMP | `/ipo/upcoming` → SIYATA PTT, 2026-09-08 |
| Options IV surface | yfinance | `/volatility/surface/AAPL` → ATM IV 25.07 |
| Valuation timeline | yfinance | `/valuation/timeline/AAPL` → P/E 35.48, P/B 42.03 |
| Macro dashboard | FRED | `/market/macro/dashboard` → GDP 32475.21 |
| Volume screening | yfinance | `/volume/screen` → 27 screened, COIN flagged |
| Insider Form 4 feed | SEC EDGAR | `/insider/transactions` → real Form 4 XML URLs |
| Litigation | CourtListener | `/litigation/AAPL/snapshot` → 37 real dockets, typed |
| RAG stack | fine-tuned embeddings | `/health/rag` → `finetuned:finance-embed-v1`, reranker active |

**Backend persistence genuinely works.** In my authenticated E2E, `POST /portfolio` → 200, `POST /workspaces/` → 200, `POST /tracking/watchlist` → 200, and rows actually landed in `portfolios`, `workspaces`, `memberships`, `organizations`, `tracked_entities`. This is real SQLAlchemy CRUD, not a stub. HEAD's claim that ~21 services were converted from fake to real is **substantially true at the service layer**.

### What is broken or misleadingly complete

1. **The API cannot serve more than ~1 concurrent user.** Proven, not theorised: `/brokerage/brokers` returns a constant dict in **7.7 ms** alone, but took **23,843 ms** during a sweep with a concurrency of only **6**. `/legal/types/case-statuses` (a static enum list): **2.1 ms → 21,867 ms**. `/health/full`: **3.6 ms → 23,507 ms**. Cause: **266 of 268** `async def` handlers in `app/api/` contain **zero `await`** while performing synchronous network I/O directly on the event loop. 44 of 618 endpoints exceeded 25 s at concurrency 6.
2. **The frontend has no authentication at all** — 0 `Authorization`/`Bearer` occurrences, 0 `localStorage`, no login/signup page. Every write the UI offers returns **401**.
3. **The served auth API is not the documented auth API.** `routes.py:37` wins route matching over `auth.py`, so `POST /auth/register` with a JSON body → **422**, and the winning handler returns **no token at all**.
4. **`.env` silently overrides real deployment config.** `main.py:2` uses `load_dotenv(..., override=True)`. I set `DATABASE_URL` in the environment and the app **ignored it** and wrote to `local.db`. This means `docker-compose.yml`'s Postgres URL and `JWT_SECRET` are both silently discarded at runtime.
5. **`pytest tests/` runs zero tests** — it aborts at collection with 3 `ImportError`s. Forced past them: **177 failed, 732 passed, 3 errors, 855 s**. CI executes **no tests**.
6. **Fundamental financial statements are dead** — FMP returns **402 Payment Required**; income statement / balance sheet / cash flow all return `{"statements": []}` with HTTP 200.
7. **Analyst consensus is half-fabricated** — Finnhub returns **403** on `price-target` and `eps-estimate`, so `/consensus/snapshot` reports `mean: 0.0, high: 0.0, low: 0.0` **next to** `num_analysts: 54`.
8. **Portfolio risk metrics are invented.** `portfolio_service.py:588` — `base_vol = 0.18  # 18% base volatility` and `diversification_benefit = max(0.5, 1 - len(holdings) * 0.03)`. Every VaR figure is derived from that constant and labelled `var_method: "parametric"`.

### One-line verdict

A **credible financial data API** with a **large, mostly-unwired demo frontend** bolted on, that **falls over at 6 concurrent requests** and whose **deployment config is silently ignored**.

---

## 2. Real Completion Percentages

```text
REAL APPLICATION COMPLETION: ~38%

Frontend:                   ~35%   (72 pages render; no auth; 22 pages unreachable from nav; 2 components orphaned)
Backend:                    ~55%   (849 ops; data layer real; persistence real; concurrency model broken)
Core product functionality: ~50%   (reads work single-user; fundamentals/analyst data dead; risk math invented)
External integrations:      ~50%   (9 working, 3 degraded, 4 unusable, 5 stubs)
Integration (FE↔BE wiring): ~30%   (526/806 routes never called; 0 auth headers; all writes 401)
Production readiness:       ~12%   (fails at 6 concurrent req; 0 tests in CI; env override kills deploy config)
```

**Weighting.** I weighted core data retrieval + the ability to save work at ~70% of product value, and secondary screens at ~30%. An endpoint no UI calls, or one that returns HTTP 200 in 7 ms alone and 24 s under trivial load, is worth close to zero.

**Why not 90–95%:** that figure counted files and endpoints. **Why not the in-repo "70%+ verified" either:** that claim is unsupported — the suite it left behind cannot even be collected. My **~38%** is slightly *above* the repo's own self-corrected 25–30% because the recent data-layer work is real and I verified it live.

---

## 3. Biggest Findings

**F1 — The API collapses at concurrency 6. (P0, most severe finding.)**
This is the headline defect and it is measured, not inferred. Identical endpoints, alone vs. during a 6-way concurrent sweep:

| Endpoint | Isolated | At concurrency 6 | Nature |
|---|---|---|---|
| `/brokerage/brokers` | **7.7 ms** | **23,843 ms** | returns a constant stub dict |
| `/legal/types/case-statuses` | **2.1 ms** | **21,867 ms** | returns a static enum list |
| `/health/full` | **3.6 ms** | **23,507 ms** | health check |
| `/legal/AAPL/proceedings` | — | **23,895 ms** | 5 sibling routes all ~23.9 s |

Endpoints that touch **no network and no DB** take 20+ seconds. That is textbook event-loop starvation. **44 of 618 GETs exceeded 25 s.** Root cause is F2.

**F2 — 266 of 268 `async def` handlers contain zero `await`.**
AST scan of `app/api/*.py`. Each does synchronous `requests` I/O on the event loop, so any slow outbound call freezes every other request in the process. Worst: `comments.py` (19), `intelligence_graph.py` (19), `pwa_advanced.py` (16), `corporate_ownership.py` (15), `portfolio.py` (14), `dashboard.py` (13). Note `ipo_calendar.py` and `government.py` use plain `def` — those are correct and FastAPI threadpools them. The fix is mechanical: `async def` → `def`.

**F3 — `load_dotenv(override=True)` silently discards deployment configuration. (P0, not in prior audit.)**
`main.py:2`: `load_dotenv(find_dotenv(), override=True)`. I launched the app with `DATABASE_URL=sqlite:////tmp/audit_e2e.db` in the environment; it **ignored it** and wrote every row to `local.db` (confirmed: `portfolios` went 0→1 in `local.db`, and 0 in the copy). Consequences:
- `docker-compose.yml` sets `DATABASE_URL: postgresql+psycopg://...` and `JWT_SECRET: dev-secret-change` — **both are overridden by the committed `.env`**, which contains `DATABASE_URL=sqlite:///./local.db`.
- The container will run on **SQLite**, not Postgres, while appearing correctly configured.
- Any orchestrator (ECS/K8s/Amplify) injecting secrets is silently defeated.

**F4 — The served `/auth` API is not the documented one, and it returns no token.**
`app/api/routes.py:37` defines `POST /auth/register(email: str, password: str)` as **query params**; `app/api/auth.py:50` defines the same path with a Pydantic **JSON body**. `main.py:74` includes `core_router` before `auth_router` (line 75) and first match wins. Verified:
- `POST /auth/register` + JSON body → **422** `missing query param email`
- `POST /auth/register?email=...&password=...` → **200** `{"id":4,"email":"..."}` — **no token issued**
- `POST /auth/login` returns `{"token", "refresh_token"}`, while `auth.py` promises `{"access_token"}`

So `auth.py`, its `TokenResponse`, its 201, and its 409 conflict handling are **dead code**, and a client written against `/docs` fails.

**F5 — The frontend has no authentication whatsoever.**
`rg "Authorization|Bearer" apps/web` → **0 matches** across 94 JS files. `rg localStorage` → **0**. No `login`/`signup`/`register` page exists. Pages hardcode `const USER_ID = 'demo_user'` and pass it as a **query parameter**. Meanwhile 9 API modules enforce `get_current_user`. The halves are architecturally incompatible.

**F6 — Every write flow in the UI returns 401 or 404.**
Simulated exactly as the frontend calls them (no auth header):

| UI action | Frontend call | Result |
|---|---|---|
| Create portfolio | `POST /portfolio?user_id=demo_user&...` | **401** |
| Create alert | `POST /alerts?user_id=demo_user&...` | **401** |
| Create workspace | `POST /workspaces/?name=...` | **401** |
| Post comment | `POST /comments?...` | **401** |
| Add annotation | `POST /annotations?...` | **422** (missing `document_type`, `start_offset`) |
| Link brokerage | `POST /brokerage/link/initiate` | **401** |
| Screen revisions | `POST /revisions/screen` | **404** (router dead — F8) |
| Create dashboard | `POST /dashboards?...` | **404** (real path is `/dashboard`) |

Two genuinely work unauthenticated, which is its own problem: `POST /agent/discover` → 200 and `POST /intelligence/graph/paypal-mafia/load` → 200 (loads 47 entities, 57 edges — **unauthenticated state mutation**).

**F7 — The backend write path *does* work; only the wiring is missing. (Correction to prior audit.)**
The prior doc concluded persistence was broken because tables were empty. That was the wrong inference. With a valid token I got:

```
register(query params) 200 → login 200 → /auth/me 200
POST /portfolio        200  {"id":1,"name":"E2E","base_currency":"USD"}
GET  /portfolio        200  portfolio present in list
GET  /portfolio/1      200  full aggregate (holdings, sector_allocation, performance)
POST /workspaces/      200  {"status":"created","id":1,"org_id":1}
POST /tracking/watchlist 200 {"ok":true,"action":"added"}
→ rows confirmed in portfolios, workspaces, memberships, organizations, tracked_entities
```

The tables are empty **because no client can log in**, not because persistence is stubbed. This makes F5 the single highest-leverage fix in the repo — it is wiring, not construction.

**F8 — `/revisions/*` is dead, and a 543-line page calls it.**
`main.py:139` `_safe_include("app.api.revision_screener")` fails at boot: `cannot import name 'ConsensusMomentum' from app.services.consensus_service` — HEAD's rewrite deleted the symbol. `pages/revisions.js` calls 5 `/revisions/*` endpoints → all **404**. `_safe_include` logs only `logger.warning`, so **the app boots green and CI passes**. This is the mechanism that lets structural breakage ship silently.

**F9 — `pytest tests/` runs zero tests; CI runs none either.**
Plain `pytest tests/` → `Interrupted: 3 errors during collection` in 2.31 s: `AnalystTier`, `SurpriseType`, `PriceVolumePattern` were deleted by HEAD but tests still import them. Forced with `--continue-on-collection-errors`: **177 failed, 732 passed, 1 skipped, 3 errors in 855 s**. Failures cluster in exactly the rewritten modules: `test_revision_screener_api.py` (30), `test_whisper_api.py` (17), `test_volatility_api.py` (16), `test_short_interest_api.py` (3). `ci.yml` runs only `python -c "from app.main import app"` plus a `grep` for `import random` — **pytest is never invoked**. 980 test functions exist and none gate anything.

**F10 — Tests were deleted rather than fixed.**
HEAD's own message: *"Deleted 8 impossible test files"* — including `test_medium_tasks_api.py` (585 lines), `test_portfolio_analytics_api.py`, `test_brokerage_sync_api.py`. These covered precisely the features that were gutted.

**F11 — Fundamental financial statements are entirely dead (FMP 402).**
Server log: `GET https://financialmodelingprep.com/stable/income-statement → 402`, same for `balance-sheet-statement` and `cash-flow-statement`. The key is present (32 chars) but the account lacks entitlement. `financial_news_connector.py:201` does `if not data or isinstance(data, dict): return []`, so `/market/income-statement?ticker=AAPL` → **HTTP 200** `{"ticker":"AAPL","statements":[]}`. For a financial research platform, missing income statements is a core-feature failure presented as success.

**F12 — Analyst consensus mixes real and zeroed data in one response.**
Log: `Finnhub /stock/price-target → 403` (×2), `Finnhub /stock/eps-estimate → 403` (×4). Result: `/consensus/snapshot?ticker=AAPL` → `mean: 0.0, high: 0.0, low: 0.0` **alongside** `num_analysts: 54, strong_buy: 13`. `/analysts/price-targets/AAPL` → every target `0.0`. A user sees "54 analysts" and a $0.00 target and cannot tell which half is real.

**F13 — Portfolio risk metrics are fabricated from a hardcoded constant.**
`portfolio_service.py:586-591`:
```python
base_vol = 0.18  # 18% base volatility
diversification_benefit = max(0.5, 1 - len(holdings) * 0.03)
portfolio_volatility = base_vol * diversification_benefit * weighted_beta
```
All four VaR figures derive from this and are labelled `var_method: "parametric"`. Then at lines 605-635, behind `# TODO: compute from real historical data via yfinance`: `sharpe_ratio = 0.0`, `sortino_ratio = 0.0`, `max_drawdown = None → 0.0`, `avg_correlation = None`. Only `beta` is real. HEAD claimed portfolio was made real — the *prices* were; the *risk math* was not.

**F14 — `import random` fabricates the public uptime figure; the CI guard cannot see it.**
`app/api/status.py:106-113`:
```python
def _calculate_uptime(service_id: str, days: int = 90) -> float:
    import random
    base_uptime = 99.90
    variation = random.uniform(0, 0.09)
    return round(base_uptime + variation, 4)
```
Used by 5 endpoints including `/status/uptime` and `overall_uptime`. CI greps only `apps/api/app/services/*.py`, so `app/api/` is unchecked. `experiments.py:13` also imports random. Publishing invented uptime is a trust and compliance problem.

**F15 — `GET /dashboard` fabricates a dashboard for any unauthenticated string, and hides DB errors.**
`app/api/dashboard.py:47-71`: `list_dashboards` has **no** `get_current_user`, and on `except Exception` returns `get_default_dashboard_config(user_id)`. I passed `user_id=demo_user`, `1`, `2`, `admin` with no token — all returned a populated "My Dashboard" with 3 widgets. So (a) it is an unauthenticated read reflecting arbitrary IDs, and (b) a genuine DB failure is indistinguishable from an empty account.

**F16 — `/insider/transactions` silently ignores the `ticker` filter.**
`GET /insider/transactions?ticker=AAPL` → 49 rows: `{AMD: 25, META: 15, BAC: 4, AMZN: 3, AAPL: 1, MSFT: 1}`. `insider_activity.py:14` declares only `days`, `transaction_type`, `min_value`, `limit` — **there is no `ticker` parameter**, so FastAPI drops it and returns an unfiltered feed. The user sees plausible data for the wrong company.

**F17 — NaN crash: `/market/gov-trading/leaderboard/search` and `/rank/{name}` return 500.**
Reproduced directly: `search_politician("Pelosi")` → `AttributeError: 'float' object has no attribute 'lower'` at `politician_leaderboard_service.py:244`, where `(r.get("official") or r.get("name") or "").lower()` meets a NaN float from the Excel import. Commit `61ec993` "fix: handle NaN values" added `_safe_str`/`_safe_float` but **never applied them on this path**. Search on the single most reliable feature is broken.

**F18 — 5 subsystems are pure stubs (31 endpoints, ~2,240 lines of dead UI).**
Every function returns `{"status":"not_available"}`: `pwa_advanced_service.py` (16 stubs/87 lines), `mobile_native_service.py` (13/72), `reddit_whale_service.py` (10/74), `narrative_model_service.py` (9/52), `mobile_pwa_service.py` (9/52), `brokerage_sync_service.py` (9/52), `browser_extension_service.py` (6/37). Commits `1cd0f2b`, `416ee87`, `adc5043`, `8e1896e`, `2bf5d55` all claimed these "implemented"/"complete". Their fully-built pages remain: `pwa-advanced.js` (637 lines), `revisions.js` (543), `narrative-model.js` (318), `brokerage.js` (290), `social.js` (257), `pwa-settings.js` (197).

**F19 — Evidence of unreviewed bulk gutting.**
`reddit_whale_service.py:45,59,64,69` return `"Reddit API credentials not configured"` for `get_whale_transactions`, `get_top_whales`, `get_institutional_ownership`, `get_insider_sentiment` — **none of which involve Reddit** (they are 13F/Form 4 data). Worse: `institutional_13f_position_cache` already holds **200 rows**, so `get_institutional_ownership` could return real data today. Also `brokerage.js:59` posts `access_token=simulated_token` to fake a Plaid link against a service with no implementation.

**F20 — `no_data_response()` has a key-collision bug at every call site.**
Pattern used ~70 times: `{"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response(...)}`. The spread runs last, so the literal human-readable `reason` is **overwritten** by the enum value (`dependency_missing`). Confirmed live: `/brokerage/brokers` → `"reason":"dependency_missing"`. The specific reason is silently lost everywhere.

**F21 — Three tables referenced in SQL do not exist; failures surface as 500s.**
Migration `3dd8a2786cc5` creates 62 tables with only 11 indexes. Raw SQL references **`rss_articles`, `rss_sources`, `entity_alerts`** — none exist. Result: `/market/rss/articles`, `/market/rss/digest`, `/market/rss/entity-feed` → 500 `no such table: rss_articles`. Also `no such table: saved_searches` / `recent_searches` (created lazily via `create table if not exists` with **Postgres `serial` syntax**, which fails on the SQLite that is actually in use), and `near "'1 hour'": syntax error` — **Postgres interval syntax executed against SQLite**. `search.py:140` is written for a database the app is not running.

**F22 — ~23 endpoints return 500 identically with and without network** (code bugs, not connectivity): `/filings/kpis` + `/filings/ontology` (`'list' object has no attribute 'get'`), `/filings/search` (`ImportError: cannot import name 'search_filings'` — `filings.py:246` imports a function that does not exist in `sec_edgar_connector.py`), `/persons/{id}` + 6 sub-routes, `/registry/health`, `/registry/jurisdictions`, `/search/recent`, `/search/saved`, `/searchos/`, `/portfolio/compare`, `/visualizations/histogram`, `/market/crypto/wallet/eth/*` (Etherscan V1 deprecated → `ValueError`), `/ontology/{t}` + 3 sub-routes.

**F23 — 146 silent exception handlers convert failure into "no data".**
AST scan of `app/**/*.py`: `except: pass` ×89, `except: continue` ×33, `except: return None` ×17, `except: return []` ×6, `except: return {}` ×1. Concentrated in `gov_trading_connector.py` (8), `osint_connector.py` (5), `deep_comparative_service.py` (5), `market.py` (4), `sec_edgar_connector.py` (4). Combined with 20 empty and 4 absent credentials, the sweep produced **52 all-empty + 13 empty-list + 7 empty-object** HTTP 200s. For a data product this is the most dangerous pattern present.

**F24 — 526 of 806 routes (65%) are never called by the frontend.**
Machine diff of every frontend `fetch()` URL against the live route table: 293 distinct frontend paths, 284 matched, 9 unmatched (5 are the dead `/revisions/*`). Entire subsystems are unreachable: all of `/ai-visibility/*`, `/editorial/*`, `/experiments/*`, `/export/*`, `/fact-scoring/*`, `/freshness/*`, `/seo/*`, `/compliance/*`, `/registry/*`, `/corporate-ownership/*`, most of `/consensus/*` and `/analysts/*`.

**F25 — 22 of 72 pages are unreachable from navigation.**
`Layout.js` exposes 50 links. Orphaned: `alerts`, `benchmark`, `brokerage`, `bubble-charts`, `calendar`, `cost-basis`, `entities/merge`, `entity-discovery`, `global-markets`, `intelligence/interactive-report`, `macro-dashboard`, `narrative-model`, `network-graph`, `persons`, `pwa-advanced`, `pwa-settings`, `revisions`, `social`, `tax-lots`, `teams`, `visualizations`, `workspaces`. Note `network-graph.js` was added by `d27b69e` (the last feature commit) and **was never linked into the nav**. `Comments.js` and `Annotations.js` have **0 importers** — ~900 lines of components no page renders.

**F26 — Errors are invisible to users.** `portfolios.js` has 5 × `catch (err) { console.error(err) }` with no error state. A 401 produces a silently empty list. Only 16 of 66 pages use `NoDataCard`.

**F27 — Entity graph and scheduler are in-process and lose data on restart.**
`entity_graph_service.py:204-211` holds `_entities`/`_edges`/`_adjacency` in plain dicts (it does hydrate from `entities`/`relationships` at startup, which the prior audit missed, but writes are not durable). `scheduler.py` runs **6 daemon threads inside the API process**; its own docstring says *"the fetched data lands in the connector's module-level cache."* With N uvicorn workers you get N schedulers hammering Finnhub/FINRA/SEC and N divergent caches. `_refresh_global_indices` wraps each index in a bare `except`.

**F28 — Deployment artifacts are broken.**
`apps/web/Dockerfile:11` sets `ENV NEXT_PUBLIC_API_URL` **after** `RUN npm run build` (line 9) — Next.js inlines `NEXT_PUBLIC_*` at build time, so the value never reaches the bundle; and `http://api:8000` is a Docker-internal hostname no browser can resolve. It only appears to work via `lib/api.js:7`'s `${window.location.hostname}:8000` fallback, which breaks under HTTPS. `apps/worker/` is a phantom (Dockerfile + package.json; `src/index.js` deleted in HEAD) yet `ecosystem.config.js` still launches `finance-worker`. `bloomberg-terminal-free` is a **gitlink with no `.gitmodules`** — fresh clones break. `packages/*` (6 workspaces, 58 files) is imported by nothing.

---

## 4. Critical Broken Workflows — exact break points

**W1. Sign up / log in — breaks at step 1 (frontend), and step 2 is wrong (backend).**
```
[ ] Reach a login page          FAIL  no login/signup/register page exists in apps/web/pages
[ ] Submit credentials          FAIL  no frontend code calls /auth/* at all
[ ] Receive a token             FAIL  the SERVED register handler (routes.py:37) returns no token
[ ] Store token                 FAIL  zero localStorage usage in 94 files
[ ] Send Authorization header   FAIL  zero Bearer headers in 94 files
```
The backend can authenticate (I did it), so this is missing wiring plus F4. Highest leverage fix in the repo.

**W2. Create a portfolio — breaks only at the auth header.**
```
UI control       OK    pages/portfolios.js modal + button
API call         OK    fetch(`${API_BASE}/portfolio?...`, {method:'POST'})
payload shape    OK    query params correctly match the backend signature
auth header      FAIL  none sent → 401 "Missing authentication token"
error surfaced   FAIL  portfolios.js:394 catch { console.error } — user sees an empty list
[with a token]   PASS  200, row persisted, GET /portfolio returns it
```
The last line is the important one: **this feature is complete except for the token.**

**W3. Estimate revision screener — breaks at import time.**
```
pages/revisions.js (543 lines) → POST /revisions/screen → 404
cause: main.py:139 _safe_include fails — ImportError ConsensusMomentum
       (symbol deleted from consensus_service.py by HEAD 2aa49ee)
logged as WARNING only → app boots green → CI passes → 30 tests fail unseen
```

**W4. Any concurrent usage — breaks the entire process.**
```
1 user   → /brokerage/brokers 7.7 ms
6 users  → /brokerage/brokers 23,843 ms   (a function that returns a constant dict)
         → 44 of 618 endpoints exceed 25 s
```
This is what a second customer experiences.

**W5. Read a company's fundamentals — breaks at the provider, reported as success.**
```
/market/income-statement?ticker=AAPL → HTTP 200 {"statements":[]}
cause: FMP → 402 Payment Required; connector returns [] on non-list
UI: renders an empty table with no explanation
```

**W6. Read analyst consensus — returns a self-contradictory response.**
```
/consensus/snapshot?ticker=AAPL → 200 {mean:0.0, high:0.0, low:0.0, num_analysts:54, strong_buy:13}
cause: Finnhub 403 on eps-estimate + price-target; recommendations endpoint still works
```

**W7. Portfolio risk analysis — returns invented numbers.**
```
VaR ← base_vol = 0.18 hardcoded (portfolio_service.py:588), labelled var_method:"parametric"
Sharpe/Sortino/max_drawdown ← 0.0 behind TODOs, indistinguishable from real zeros
```

**W8. Search a government official — 500.**
```
/market/gov-trading/leaderboard/search?name=Pelosi → 500
/market/gov-trading/leaderboard/rank/Pelosi        → 500
cause: AttributeError NaN.lower() at politician_leaderboard_service.py:244
```

**W9. RSS / news feed — 500 (table never created).**
```
/market/rss/articles|digest|entity-feed → 500 "no such table: rss_articles"
cause: table only created by app/connectors/rss_worker.py, which nothing runs;
       and its DDL is Postgres-specific (GIN index) against a SQLite database
```

**W10. Brokerage linking — fake token against a stub.**
```
brokerage.js:59 posts access_token=simulated_token → service returns not_available
```

---

## 5. Last 50 Commits — claimed vs. actual

Range: **16 Jul → 22 Aug 2026**, 234 files, +98,481/−6,678. Three distinct phases.

### Phase A — "Feature factory" (16–17 Aug, ~25 commits)

Repeating pattern: one API file + one service + one test + one 200–600 line Next.js page, then a `docs:` commit ticking boxes. **8 of 50 commits (16%) change only `MASTER_TASK_STATUS.md`.**

| Commit | Claimed | Verified actual |
|---|---|---|
| `2bf5d55` | "10 MEDIUM tasks, full stack" (33 files) | Mixed. `workspace`/`team_permission`/`cost_basis`/`tax_lot` later became real. `reddit_whale` became a pure stub. Its 585-line test was **deleted** in HEAD. |
| `1cd0f2b` | "brokerage sync with Plaid/OAuth integration" | **No Plaid ever existed.** Original used `hashlib.md5` + `random.choice` and a fake `https://api.plaid.com/link?token=...` URL. Now 52 lines of stubs. Test deleted. |
| `416ee87` | "narrative model training and deployment" | **No training code.** 52 lines of stubs. Test deleted. |
| `adc5043` | "Mobile PWA with push notifications" | **No push service.** 52 lines of stubs. Test deleted. |
| `8e1896e` | "PWA Advanced — offline caching, WebAuthn, screen sharing" | **None implemented.** 87 lines of stubs + 637-line dead page. Test deleted. |
| `94943eb` | "complete portfolio analytics suite (D1–D11)" | Was fake; genuinely rewritten in HEAD (860 lines, real yfinance). Test deleted anyway. |
| `7148c03` | "Global Equity Coverage" | Test deleted; service later rewritten to ~570 lines. |
| `224fdf1`/`15d91db` | "autonomous agent loop" / "recursive entity discovery" | Real code exists; `POST /agent/discover` returns a job ID **unauthenticated**. |
| `0e5c238` | "revision screener page + comments/annotations components" | Page is now 100% 404 (F8); both components have **0 importers** (F25). |

**Assessment:** ~25,000 lines and a wall of green checkboxes for approximately zero usable features. The tests written alongside were the ones later deleted as "impossible" — they asserted on mock shapes.

### Phase B — "Real data push" (21 Aug, 8 commits) — the most honest work in the window

- `226344f` — 38,277 lines of real gov-trading data (637 officials from Excel). **Still the single most valuable feature.**
- `6b98cda` — *"fix: resolve mock data exposure in investor-facing endpoints"* — an explicit admission that shipped features had been serving mock data to investors. Added 4 real connectors.
- `ab07733` — real FRED/gov connectors. **Verified working.**
- `227846f`/`7d63a5d`/`82a7c0b` — graph store + ingestion; hydrates from DB at boot but writes are not durable (F27).
- `61ec993` — NaN fix that **missed** `search_politician` (F17, still 500s).
- `9c8e494` — genuine one-line param fix.
- `d27b69e` — 496-line `network-graph.js` added with **no backend commit and no nav link** (F25).

### Phase C — "The great gutting and re-building" (22 Aug, 2 commits, same day)

- **`7568581`** *"complete platform overhaul — real APIs, no fake data, production infra"*, 97 files, net **−3,623 lines**. Deleted ~12,000 lines of mock generators across 30+ services; removed 27 `import random`; added Alembic, JWT `auth.py`, the `no_data` contract, `scheduler.py`, CI, `NoDataCard.js`; rewrote `MASTER_TASK_STATUS.md` down to **"~25-30%"** — a self-audit contradicting all 48 prior commits. **Directionally the most important commit in the window.** But it introduced F4 (shadowed auth router), F20 (key-collision bug at ~70 sites), and left ~40 services as stubs. It also committed 7 macOS AppleDouble binaries (`._*.py`) into `app/services/` and then deleted them in the same commit.
- **`2aa49ee`** *"convert all remaining stubs to real services — 70%+ verified"*, +8,726/−3,401. **Genuinely converted ~21 services to real yfinance/Finnhub calls — I verified 13 of them returning live data.** However it **broke 4 modules' public APIs** (`ConsensusMomentum` → dead router F8; `AnalystTier`/`SurpriseType`/`PriceVolumePattern` → 3 uncollectible test modules F9), **deleted 8 test files** instead of fixing them, and its **"70%+ verified" claim is unverifiable** — the suite it left cannot be collected and CI runs none of it.

### Cross-cutting patterns

1. **Documentation-driven development** — progress was tracked by editing a markdown file, not by verifying behaviour.
2. **Tests as decoration** — written against mocks, deleted when mocks were removed, never run in CI.
3. **Two safety nets both fail by design** — `_safe_include` downgrades a dead router to a `warning`; CI asserts only that the app imports.
4. **The last two commits contradict the previous 48 — and are right to.**

---

## 6. External Integrations — classified

| Integration | Status | Evidence |
|---|---|---|
| **Finnhub** (quote, earnings, IPO, recommendations) | **WORKING** | quote 7/7 fields; real EPS; 54 analysts |
| **Finnhub** (price-target, eps-estimate) | **WIRED BUT BROKEN** | HTTP **403** → `mean/high/low = 0.0` beside `num_analysts: 54` |
| **FINRA** short interest | **WORKING** | 141,606,163 sh, DTC 2.58 |
| **yfinance** (options IV, valuation, volume, beta) | **WORKING** | ATM IV 25.07; P/E 35.48; 27-ticker screen |
| **FRED** macro | **PARTIALLY WORKING** | dashboard 9/9 fields, but `/fred/series` → **400** on sub-routes |
| **SEC EDGAR** (CIK, Form 4, submissions) | **WORKING** | real Form 4 XML URLs |
| **Congress.gov / House PTR** | **WORKING** | live filings, 2026 dates |
| **Static gov dataset** (637 officials) | **WORKING** (search path 500s — F17) | real names/volumes |
| **CourtListener** litigation | **WORKING** | 37 real typed dockets for AAPL |
| **Stripe** billing | **PARTIALLY WORKING** | plans return; honest "not configured" for charges |
| **OpenSearch / RAG** | **PARTIALLY WORKING** | `/health/rag` ok with fine-tuned model, but OpenSearch on :9200 **connection refused** → falls back to `memory-cached` |
| **FMP** financials | **WIRED BUT BROKEN** | **402 Payment Required** → `{"statements":[]}` at HTTP 200 |
| **GDELT** news | **WIRED BUT BROKEN** | **429** rate-limited ×5 → `{"articles":[]}` |
| **OpenCorporates** | **UNKNOWN — NEEDS CREDENTIALS** | **401**; `OPENCORPORATES_API_TOKEN` empty |
| **ALEPH / OCCRP** | **UNKNOWN — NEEDS CREDENTIALS** | **401**; `ALEPH_API_KEY` empty |
| **FinCEN** | **WIRED BUT BROKEN** | DNS `efts.fincen.gov` does not resolve — wrong hostname |
| **Etherscan** crypto | **WIRED BUT BROKEN** | V1 deprecated → `ValueError` → 500 |
| **UK Companies House** | **PARTIALLY WORKING** | reachable; 404 on my synthetic ID; **38 s** slowest call in sweep |
| **OIDC / SSO** | **NOT IMPLEMENTED** | `501 "OIDC not configured"`; both vars empty |
| **Reddit** | **PLACEHOLDER** | 74-line stub; creds empty; **supplying keys would change nothing** |
| **Plaid** | **PLACEHOLDER** | 52-line stub; `PLAID_*` absent from `.env` |
| **Push notifications / WebAuthn / mobile native / browser extension** | **PLACEHOLDER** | 4 stub services, 0 lines of implementation |
| **GPU / narrative model** | **NOT IMPLEMENTED** | 52-line stub |
| **OpenSecrets, Senate LDA, HIBP, CA SOS** | **UNKNOWN — NEEDS CREDENTIALS** | keys present-but-empty |

**Credentials:** 121 vars in `.env`; **20 present-but-empty**; **`SEC_API_KEY` read by code but absent**; `PLAID_*`, `CONGRESS_GOV_API_KEY`, `ALPHA_VANTAGE_API_KEY`, `SECRET_KEY` absent. Note `financial_news_connector.py:16` reads `ALPHA_VANTAGE_KEY` while docs reference `ALPHA_VANTAGE_API_KEY` — a name mismatch. `JWT_SECRET` is only 17 chars.

**Timeouts:** of 147 `requests.get/post` calls in connectors and services, only **62 pass an inline `timeout`**. `financial_news_connector.py` sets a shared `_TIMEOUT = 12`, but many other modules have no bound at all.

---

## 7. Gap Analysis

| Area | Claimed | Actual (verified) | Evidence | Sev | Remaining work |
|---|---|---|---|---|---|
| Concurrency | "production infra" | **Collapses at 6 concurrent req** | 7.7 ms → 23,843 ms on a constant-dict endpoint | **P0** | `async`→`def`; timeouts |
| Async correctness | — | **266/268 handlers block the loop** | AST scan | **P0** | Mechanical conversion |
| Deployment config | Postgres via compose | **`.env` overrides everything → SQLite** | `main.py:2`; DB write went to `local.db` | **P0** | `override=False` |
| Auth API contract | "JWT auth complete" | **Duplicate router wins; no token returned** | JSON → 422; query → 200 no token | **P0** | Delete `routes.py` auth block |
| Frontend auth | "complete" | **Nonexistent** | 0 Bearer, 0 localStorage, no page | **P0** | Login + token + fetch wrapper |
| Write flows | "complete" | **All 401/404 from UI; work with a token** | 8 simulated calls; E2E passes with token | **P0** | Depends on frontend auth |
| Revision screener | "#37 complete" | **Router dead; 5 endpoints 404** | ImportError `ConsensusMomentum` | **P0** | Restore symbol |
| Test/CI | "tests added" per commit | **0 tests run; 177 fail when forced** | collection aborts; `ci.yml` | **P0** | Fix imports; run pytest |
| Fundamentals | "real APIs, no fake data" | **FMP 402 → empty at HTTP 200** | server log | **P0** | Fix plan or surface `no_data` |
| Analyst/consensus | "Finnhub integration" | **403 → zeros beside 54 analysts** | server log | **P1** | Partial-response flag |
| Portfolio risk | "risk metrics endpoint" | **`base_vol=0.18` hardcoded; Sharpe 0.0** | `portfolio_service.py:588,605-635` | **P1** | Real history or null |
| Status uptime | "status page" | **`random.uniform` fabricated** | `status.py:110` | **P1** | Real data or remove |
| Gov search | "leaderboard complete" | **500 on NaN** | reproduced | **P1** | `str()` coercion at :244 |
| Insider filter | "insider activity" | **`ticker` param silently ignored** | 49 rows, 6 tickers | **P1** | Add param or reject |
| Dashboard auth | — | **Unauth read; fabricates default; hides DB errors** | `dashboard.py:47-71` | **P1** | Add auth; stop masking |
| Missing tables | "Alembic migrations" | **`rss_articles`/`rss_sources`/`entity_alerts` absent** | 500s | **P1** | Migrate or remove |
| Postgres-only SQL | — | **`serial`, `'1 hour'`, GIN on SQLite** | `search.py:140`; log | **P1** | Pick one dialect |
| 5xx endpoints | — | **~23 endpoints 500 (code bugs)** | sweep, both modes | **P1** | Fix or remove |
| Silent failures | "no fake data" | **146 silent excepts; 72 empty 200s** | AST + sweep | **P1** | Distinguish empty vs failed |
| Stub features | "implemented" | **7 services, 31 endpoints, ~2,240 lines dead UI** | 37–87 line files | **P1** | Implement or delete |
| Graph/scheduler | "Graph Store + cron wiring" | **In-process; N× per worker; non-durable writes** | `scheduler.py` docstring | **P1** | Extract to worker |
| FE↔BE coverage | "frontend wired" | **526/806 routes (65%) unused** | machine diff | **P2** | Delete or expose |
| Page reachability | — | **22/72 pages orphaned; 2 components unused** | nav diff | **P2** | Link or delete |
| Docker web | "production infra" | **env set after build; internal hostname** | `Dockerfile:9,11` | **P1** | Build ARG |
| Repo hygiene | — | **gitlink w/o `.gitmodules`; phantom worker; unused packages** | `git ls-files -s` | **P2** | Remove |
| Secrets | ".env.example all 55+ vars" | **`SEC_API_KEY` absent; 20 empty; 17-char JWT secret** | env diff | **P2** | Fail fast on required |

---

## 8. Remaining Work — fresh task list

### P0 — MUST FIX

**P0-1. Convert the 266 no-`await` `async def` handlers to `def`, and bound every outbound call.**
- *Why:* the product cannot serve a second user. `/brokerage/brokers` (a constant dict) goes **7.7 ms → 23,843 ms** at concurrency 6; `/legal/types/case-statuses` (a static enum) **2.1 ms → 21,867 ms**; 44 of 618 endpoints exceed 25 s. Every one of these handlers does synchronous `requests` I/O on the event loop.
- *Files:* all `app/api/*.py` — worst `comments.py` (19), `intelligence_graph.py` (19), `pwa_advanced.py` (16), `corporate_ownership.py` (15), `portfolio.py` (14), `dashboard.py` (13); plus 85 un-bounded `requests` calls in `app/connectors/`.
- *Fix:* (a) change `async def` → `def` for any handler with no `await` (FastAPI threadpools them); (b) add a module-level `_TIMEOUT` and pass `timeout=` to every `requests`/`httpx` call; (c) in `corporate_ownership.py:240` cap the depth-2 fan-out and return `partial: true`.
- *Verify:* re-run the 618-endpoint sweep at concurrency 6 — no endpoint above ~30 s; `/brokerage/brokers` and `/legal/types/case-statuses` stay in single-digit ms under load.
- *Complexity:* M (1–2 d, mostly mechanical). **Do this first — it is the difference between a demo and a service.**

**P0-2. Change `load_dotenv(find_dotenv(), override=True)` to `override=False`.**
- *Why:* `main.py:2` makes the committed `.env` win over the real environment. I proved it: an env-provided `DATABASE_URL` was ignored and writes went to `local.db`. In Docker this silently discards the compose Postgres URL and `JWT_SECRET`, so production runs on SQLite with a dev secret while looking correctly configured.
- *Files:* `apps/api/app/main.py:2`; audit other `load_dotenv` call sites; `apps/api/app/core/settings.py`.
- *Fix:* `load_dotenv(find_dotenv(), override=False)`. Add a startup assertion that fails when `ENV=production` and `DATABASE_URL` starts with `sqlite`.
- *Verify:* `DATABASE_URL=postgresql+psycopg://... uvicorn app.main:app` connects to Postgres; `docker compose up` shows `backend: postgres` at `/health/full`.
- *Complexity:* S (1 h). **Highest value-per-line change in the repo.**

**P0-3. Delete the duplicate auth router in `routes.py`.**
- *Why:* `routes.py:37,47,95` register `/auth/register|login|refresh` with **query params** and are included at `main.py:74`, before `auth_router` at line 75. First match wins, so the documented JSON API returns **422** and the winning register handler **issues no token**. `auth.py`'s `TokenResponse`, 201 and 409 handling are dead. Response keys also disagree (`token` vs `access_token`).
- *Files:* `app/api/routes.py` (remove ~lines 37–100), `app/api/auth.py`, `app/main.py`.
- *Fix:* delete the `routes.py` auth endpoints; keep `auth.py`; port the unique bits across (refresh token, MFA check, `AuditLog` write). Standardise on `access_token`.
- *Verify:* `curl -X POST /auth/register -H 'Content-Type: application/json' -d '{"email":"a@b.com","password":"x"}'` → **201 with `access_token`**; exactly one `/auth/register` in `openapi.json`.
- *Complexity:* S (2–4 h).

**P0-4. Build frontend authentication: login page, token storage, authenticated fetch wrapper.**
- *Why:* 0 `Authorization` headers and 0 `localStorage` across 94 files; no login page; `USER_ID = 'demo_user'` hardcoded. This alone is why every write 401s and every business table is empty. **The backend write path already works** — I created a portfolio, a workspace and a watchlist entry with a token and all persisted. This is wiring, not construction.
- *Files:* new `apps/web/pages/login.js`, `apps/web/lib/auth.js`; extend `apps/web/lib/api.js` with `apiFetch()`; `pages/_app.js` (route guard); `src/components/Layout.js` (user menu/logout); then remove hardcoded `user_id` from `pages/alerts.js:9`, `pages/pwa-advanced.js:12`, `benchmark.js`.
- *Fix:* `apiFetch()` injects `Authorization: Bearer`, redirects to `/login` on 401. Migrate all raw `fetch` call sites. **Derive `user_id` from the JWT server-side and stop accepting it as a query param** — today `GET /dashboard?user_id=<anything>` returns data with no token (F15).
- *Verify:* log in via UI → create a portfolio → `select count(*) from portfolios` = 1 → reload shows it.
- *Complexity:* M (2–3 d).

**P0-5. Make `_safe_include` fail loudly, and restore `ConsensusMomentum`.**
- *Why:* `main.py:115-116` logs a dead router as a `warning`, so `/revisions/*` has been 404 while `pages/revisions.js` (543 lines) and 30 tests fail — and CI passed the whole time.
- *Files:* `app/main.py:107-166`; `app/services/consensus_service.py`; `app/services/revision_screener_service.py:22,197`; `app/api/revision_screener.py:27`; `.github/workflows/ci.yml`.
- *Fix:* re-add the `ConsensusMomentum` dataclass (recover via `git show 7568581^:apps/api/app/services/consensus_service.py`) or refactor `_classify_trend` onto the new shape. Make `_safe_include` raise when `ENV in (local, ci)`; in prod, collect failures and expose them as degraded in `/health`.
- *Verify:* all 10 `/revisions/*` non-404; `test_revision_screener_api.py` 30 failures → 0; breaking an import deliberately turns CI red.
- *Complexity:* S (3–5 h).

**P0-6. Make the test suite collectable and run it in CI.**
- *Why:* `pytest tests/` aborts in 2.31 s with 3 `ImportError`s — **zero tests execute**. Forced past them: **177 failed, 732 passed** in 855 s. `ci.yml` only runs `python -c "from app.main import app"`.
- *Files:* `app/services/analyst_scoring_service.py` (`AnalystTier`), `consensus_service.py` (`SurpriseType`), `volume_screening_service.py` (`PriceVolumePattern`); `tests/test_analyst_service.py:15`, `test_consensus_service.py:17`, `test_volume_service.py:15`; `.github/workflows/ci.yml`.
- *Fix:* re-export the three symbols or update the tests. Add `pytest` + `pytest-timeout --timeout=60` to CI; mark network tests so CI runs a fast offline subset. Extend the `import random` guard from `app/services/` to **all** of `app/` (it currently misses `status.py:110` and `experiments.py:13`).
- *Verify:* `pytest --co` collects cleanly; CI fails on regression; the random guard catches `status.py`.
- *Complexity:* M (1–2 d).

**P0-7. Fix or honestly surface the dead fundamentals feed.**
- *Why:* FMP returns **402 Payment Required**, and `financial_news_connector.py:201` (`if not data or isinstance(data, dict): return []`) turns that into **HTTP 200 + `{"statements":[]}`**. Income statement, balance sheet and cash flow — core features of a financial research product — are all silently dead.
- *Files:* `app/connectors/financial_news_connector.py:195-260`; `app/api/market.py:64-81`.
- *Fix:* upgrade the FMP plan **or** re-source fundamentals from SEC EDGAR `companyfacts` (already implemented in `sec_edgar_connector.extract_financial_statements`). Either way, propagate the upstream status: return `no_data(reason=API_KEY_INVALID, http_status=402)` rather than `[]`.
- *Verify:* `/market/income-statement?ticker=AAPL` returns real revenue, or an explicit `no_data` naming the 402. Never a bare empty array.
- *Complexity:* M (1 d via EDGAR; S if the plan is upgraded).

### P1 — IMPORTANT

**P1-1. Replace the fabricated portfolio risk model.** `portfolio_service.py:588` hardcodes `base_vol = 0.18` and a `1 - n*0.03` "diversification benefit", then publishes four VaR figures labelled `var_method: "parametric"`; lines 605-635 emit `sharpe_ratio=0.0`, `sortino_ratio=0.0`, `max_drawdown=0.0` behind TODOs. Compute from real yfinance history (already a dependency) or return `null` with `metrics_unavailable`. Publishing invented risk numbers to investors is the highest-liability item here. **M**

**P1-2. Flag partial provider responses instead of zero-filling.** Finnhub 403s on `eps-estimate`/`price-target` produce `mean/high/low = 0.0` beside `num_analysts: 54`. Add a `partial: true` + `missing_fields: [...]` contract and render it. Applies to `/consensus/*` and `/analysts/price-targets/*`. **M**

**P1-3. Remove the fabricated uptime.** `status.py:106-113` returns `99.90 + random.uniform(0, 0.09)` from 5 endpoints including `overall_uptime`. Compute from real samples or return `no_data`. **S**

**P1-4. Fix the NaN 500 in `search_politician`.** `politician_leaderboard_service.py:244` — `(r.get("official") or r.get("name") or "").lower()` raises `AttributeError` on a NaN float. Use the `_safe_str` helper that `61ec993` already added but never applied here. Also fixes `/leaderboard/rank/{name}`. **S**

**P1-5. Add the missing `ticker` filter to `/insider/transactions`.** `insider_activity.py:14` has no `ticker` param, so `?ticker=AAPL` is silently dropped and returns AMD/META/BAC rows. Add the parameter and filter, or reject unknown query params. Wrong-company data presented as correct is worse than an error. **S**

**P1-6. Create the missing tables and settle on one SQL dialect.** `rss_articles`, `rss_sources`, `entity_alerts` are referenced but never created → 500s on 3 `/market/rss/*` routes. `search.py:140` issues Postgres `serial` DDL and `'1 hour'` intervals against SQLite. Move all DDL into Alembic; delete the lazy `create table if not exists` paths. **M**

**P1-7. Triage the ~23 persistent 500s.** Same with and without network, so these are code bugs: `/filings/search` (`ImportError: search_filings` — `filings.py:246` imports a nonexistent function), `/filings/kpis` + `/filings/ontology` (`'list' object has no attribute 'get'`), `/persons/{id}` + 6 sub-routes, `/ontology/{t}` + 3, `/registry/health`, `/registry/jurisdictions`, `/search/recent`, `/search/saved`, `/searchos/`, `/portfolio/compare`, `/visualizations/histogram`, `/market/crypto/wallet/eth/*` (Etherscan V1 deprecated). Fix or delete — a 500 is worse than a 404. **M**

**P1-8. Distinguish "no data" from "call failed", and fix the `no_data_response` collision.** 146 silent handlers (`except: pass` ×89, `continue` ×33, `return None` ×17, `return []` ×6) produced 72 empty-but-200 responses in the sweep. Separately, the `{"reason": "...", **no_data_response(...)}` pattern at ~70 sites has the spread **overwrite** the human-readable `reason` with the enum value — reorder the spread or drop the literal key. Log the exception, return the real reason, render it in `NoDataCard`. **M**

**P1-9. Secure `GET /dashboard`.** `dashboard.py:47-71` has no `get_current_user`, reflects any `user_id` string, and on `except Exception` returns a fabricated default dashboard — masking real DB failures. Add auth, derive the user from the JWT, and let errors surface. **S**

**P1-10. Fix the web Dockerfile.** `apps/web/Dockerfile:11` sets `ENV NEXT_PUBLIC_API_URL` **after** `RUN npm run build` (line 9), so Next.js never inlines it; and `http://api:8000` is unresolvable from a browser. Use `ARG NEXT_PUBLIC_API_URL` before the build with a public URL. Note `lib/api.js:7`'s `hostname:8000` fallback hides this locally and breaks under HTTPS. **S**

**P1-11. Move the scheduler out of the API process.** `scheduler.py` runs 6 daemon threads whose results land in module-level caches (its own docstring), so data is lost on restart and N uvicorn workers means N schedulers hammering Finnhub/FINRA/SEC with N divergent caches. Run as a separate process (restore `apps/worker`) writing to Postgres/Redis. Remove the bare `except` in `_refresh_global_indices`. **M**

**P1-12. Make entity-graph writes durable.** `entity_graph_service.py:204-211` keeps `_entities`/`_edges`/`_adjacency` in dicts; it hydrates from `entities`/`relationships` (45/50 rows) at boot but new edges are not persisted, so 19 `/intelligence-graph/*` endpoints and the PayPal-Mafia seed are per-process. `_entity_db_pk`/`_edge_db_pk` already exist — complete the write-through. Also require auth on `POST /intelligence/graph/paypal-mafia/load`, which currently mutates state unauthenticated. **L**

**P1-13. Decide the fate of the 7 stub services.** 31 endpoints and ~2,240 lines of dead UI return `{"status":"not_available"}`: `brokerage_sync`, `narrative_model`, `mobile_pwa`, `pwa_advanced`, `reddit_whale`, `mobile_native`, `browser_extension`. Implement or delete both halves. **Quick win:** `reddit_whale_service.get_institutional_ownership` is blocked on a bogus "Reddit credentials" reason while `institutional_13f_position_cache` already holds **200 rows** — wire it. Also delete `brokerage.js:59`'s `access_token=simulated_token`. **M**

### P2 — CLEANUP / QUALITY

**P2-1.** Surface errors in the UI: replace `catch (err) { console.error(err) }` (5× in `portfolios.js` alone) with visible error states; extend `NoDataCard` from 16 to all 66 pages. **M**
**P2-2.** Resolve the 526 unused endpoints (65%): delete dead subsystems (`/ai-visibility`, `/editorial`, `/experiments`, `/fact-scoring`, `/freshness`, `/seo`, `/compliance/content`) or expose them. **L**
**P2-3.** Link or delete the 22 orphaned pages, and either use or remove `Comments.js` + `Annotations.js` (~900 lines, 0 importers). **S**
**P2-4.** Consolidate 4 frontend API clients (`api.js`, `institutional.js`, `intelligence.js`, `institutional-models.js`) plus raw `fetch` into one client (pairs with P0-4). **M**
**P2-5.** Repo hygiene: remove the `bloomberg-terminal-free` gitlink with no `.gitmodules` (breaks fresh clones), the phantom `apps/worker/`, tracked `apps/api/local.db`, `apps/api/src/index.js`, `reports/` (42 dirs of PDFs), `docs/*.xlsx`, `.DS_Store`; add `._*` and `.DS_Store` to `.gitignore`; delete or wire the 6 unused `packages/*` workspaces (58 files imported by nothing). **S**
**P2-6.** Move `DATABASE_URL` to Postgres and review indexes — the single migration creates 62 tables with only 11 indexes, and `claims` already has 3,551 rows. **M**
**P2-7.** Document required vs optional env vars and fail fast on required ones: `SEC_API_KEY` is read but absent; 20 vars are empty; `ALPHA_VANTAGE_KEY` vs `ALPHA_VANTAGE_API_KEY` mismatch at `financial_news_connector.py:16`; `JWT_SECRET` is 17 chars. **S**
**P2-8.** Replace deprecated `@app.on_event("startup")` (`main.py:175`) with a lifespan handler; fix Pydantic v2 `class Config` warnings (`settings.py:8`, `auth.py:36`). **S**
**P2-9.** Collapse 92 services / 79 API modules into ~15 domain services (see §9). **L**

---

## 9. Dead / Duplicate / Unnecessary Code — and architecture critique

### Delete outright
- **`app/api/routes.py` auth block (~37–100)** — duplicate router that shadows `auth.py` and returns no token (F4).
- **`apps/worker/`** — `Dockerfile` + `package.json` with no source; `src/index.js` deleted in HEAD, yet `ecosystem.config.js` still launches `finance-worker`.
- **`bloomberg-terminal-free`** — gitlink (`160000 6f2b3fa...`) with **no `.gitmodules`**; breaks fresh clones.
- **`packages/*`** — 6 workspaces, 58 files, **imported by nothing**.
- **`apps/api/src/index.js`** — a JS file inside the Python service.
- **`Comments.js` + `Annotations.js`** — ~900 lines, **0 importers**.
- **Tracked artifacts** — `apps/api/local.db`, `reports/` (42 dirs of generated PDFs/JSON), `docs/*.xlsx`, `.DS_Store`, `.pytest_cache/`.

### Simplify — unnecessary complexity for the actual requirements
- **92 services / 79 API modules / 849 endpoints for ~15 real features.** One-service-per-ticket produced ~40 modules that wrap a single connector call. `portfolio_service.py` (1,014 lines) and `portfolio_analytics_service.py` (860) overlap heavily. Target ~15 domain services.
- **266 pointless `async def`** — this is not elegance, it is the direct cause of the P0 concurrency failure. Converting to `def` both simplifies and fixes.
- **`_safe_include` × 48** — an abstraction whose only effect is to convert startup failures into silent warnings. Replace with a hard failure plus a health-check entry.
- **`no_data_response()`** — an 11-value enum + message map whose calling convention is broken at ~70 sites (F20). Reduce to `{"no_data": True, "reason": str, "source": str, "upstream_status": int}`.
- **4 frontend API clients** plus raw `fetch` everywhere. One client.
- **6 daemon threads inside the API process** masquerading as a scheduler.

### Keep — genuinely required
Alembic migrations; the connector layer (real, well-isolated, the most valuable code here); `NoDataCard.js`; `auth/security.py` JWT; the static gov-trading dataset; the fine-tuned embeddings/RAG stack; `ErrorBoundary.js`.

### Is the complexity justified?
**No, in one direction; yes, in another.** The *breadth* (849 endpoints, 92 services, 72 pages) is unjustified — it exists because tickets were closed by creating files. The *depth* in `app/connectors/` **is** justified: 43 connectors doing real rate-limited HTTP against SEC/FINRA/Finnhub/FRED/CourtListener is inherently messy work, and that layer is the product's actual moat. **Cut breadth, keep depth.**

---

## 10. Production Blockers

A paying customer cannot reliably use this today because:

1. **A second concurrent user breaks it.** A constant-dict endpoint goes 7.7 ms → 23.8 s at concurrency 6; 44 endpoints exceed 25 s (F1, F2).
2. **Deployment config is silently ignored** — `.env` overrides the environment, so the container runs SQLite with a dev JWT secret regardless of what the orchestrator injects (F3).
3. **Nobody can log in** — no login page, no token handling, and the served register endpoint issues no token (F4, F5).
4. **Nothing can be saved from the UI** — every write 401s, even though the backend write path works (F6, F7).
5. **Core financial data is dead but reports success** — fundamentals empty at HTTP 200 (FMP 402); analyst targets $0.00 beside "54 analysts" (F11, F12).
6. **Published numbers are fabricated** — random uptime; VaR from a hardcoded 0.18; Sharpe/Sortino 0.0 (F13, F14).
7. **Authorization is bypassable** — `user_id` as a query param; `GET /dashboard` and `POST /intelligence/graph/.../load` need no token; `roles`/`role_permissions` empty so RBAC grants nothing (F15).
8. **Broken pages ship** — `/revisions` 404s; 5 pages front pure stubs; ~23 endpoints 500 (F8, F18, F22).
9. **No safety net** — 0 tests run in CI; 177 fail when forced; `_safe_include` hides structural breakage (F9, F10).
10. **State is lost on restart** — scheduler and graph caches are in-process; 3 referenced tables do not exist; SQL mixes Postgres and SQLite dialects (F21, F27).

---

## 11. Corrections to the Prior Audit Document

I re-tested the claims in `docs/INDEPENDENT_AUDIT_2026-08-23.md`. Three are **wrong**, and its single most important finding was **missed**. That file should be superseded by this one.

| Prior claim | Verified reality |
|---|---|
| "One endpoint ran for **5.5 hours** (19,617 s) and returned 200" (its F6) | **False.** `/corporate-ownership/uk-companies-house/company/1` alone: **0.67 s**. The 19,617 s figure was an artifact of running the whole sweep on a starved event loop. The real defect is worse and more general — see F1 — but no endpoint takes 5.5 h. |
| "**Zero** business data has ever been persisted; persistence is broken" (its F4) | **Wrong inference.** With a valid token I created a portfolio, a workspace + membership + org, and a watchlist entry — all persisted (F7). Tables are empty because no client can log in. Persistence is **complete**; wiring is missing. This changes the fix from "build persistence" to "add a login page". |
| "Malformed template literal leaks a JS expression into the URL in `gov-trading-leaderboard.js`" (its P2-5) | **False positive.** `gov-trading-leaderboard.js:25` is a valid nested ternary producing `/leaderboard/notable-cases` or `/leaderboard/<tab>`. My URL extractor produced the same artifact; reading the source disproves it. |
| "266 blocking async handlers" listed as one P0 among many | **Understated.** This is *the* defect. The prior doc never measured isolated-vs-concurrent latency, so it misattributed the symptom to a single slow endpoint. |
| `load_dotenv(override=True)` discarding deployment config | **Not mentioned at all.** This is a P0 (F3). |
| FMP **402** killing all fundamentals; Finnhub **403** on estimates | **Not mentioned.** Both are core-feature failures (F11, F12). |
| `/insider/transactions` ignoring `ticker`; `rss_articles` missing; Postgres SQL on SQLite; `GET /dashboard` unauthenticated | **Not mentioned** (F16, F21, F15). |
| "177 of 910 tests fail (19.5%)" | Directionally right, but it missed that **`pytest tests/` runs zero tests** — it aborts at collection unless `--continue-on-collection-errors` is passed. |
| "578/806 routes unused", "13 business tables", "849 endpoints" | Close; I measure **526/806** unused and 849 ops / 806 paths. |

---

## 12. Recommended Fix Order

```
1 → P0-2  load_dotenv override=False           (1 hour; unblocks Postgres + real secrets)
2 → P0-1  async→def + timeouts                 (makes the API able to serve >1 user)
3 → P0-3  delete duplicate auth router         (2-4h; makes /auth honest and token-issuing)
4 → P0-4  frontend auth: login + token + fetch (2-3d; turns the demo into an application)
5 → P0-5  _safe_include fails loudly + restore ConsensusMomentum
6 → P0-6  fix test imports + run pytest in CI  (locks in everything above)
7 → P0-7  fundamentals via SEC EDGAR or FMP plan
8 → P1-4 NaN 500 · P1-3 fake uptime · P1-5 insider filter · P1-10 Dockerfile  (fast, high-trust)
9 → P1-1 real risk metrics · P1-2 partial-response flags   (liability)
10→ P1-8 real error semantics · P1-6 missing tables · P1-7 the 23 5xx
11→ P1-9 dashboard auth · P1-11 extract scheduler · P1-12 durable graph
12→ P1-13 implement-or-delete the 7 stub features
13→ P2-*  dead code, consolidation, repo hygiene
```

**Rationale.** Steps 1–2 are cheap and change the product's category: today it is a single-user demo whose deploy config is ignored. Steps 3–4 are the difference between "data API" and "application", and step 4 is unusually cheap because the backend already persists correctly. Steps 5–6 stop the bleeding — without CI running tests, every later fix can regress silently, which is exactly how `/revisions` died. Refactoring is deliberately last.

---

## 13. Final Verdict

```
Historical claimed completion:   90-95%   (commit messages, checklists)
In-repo self-corrected claim:    25-30%   (MASTER_TASK_STATUS.md)
HEAD commit's claim:             70%+ "verified"
Prior audit doc's estimate:      ~42%
Independently verified:          ~38%

Why the difference:
  The 90-95% figure counted artifacts — 849 endpoints, 92 services, 72 pages. Weighted by
  product value, an endpoint no UI calls (526 of 806), a write path that 401s, and a
  handler that takes 24 seconds under a load of six are all worth ~0.

  HEAD's "70%+ verified" is unverifiable in the strict sense: the test suite it left behind
  cannot even be collected, and CI never runs it. Its underlying data work, though, is real
  — I confirmed live data from Finnhub, FINRA, yfinance, FRED, SEC EDGAR, Congress and
  CourtListener across 13 endpoints. That deserves credit.

  I land slightly BELOW the prior audit's 42% despite finding persistence in better shape
  than it did, because I found three defects it missed that are each more severe than
  anything on its list: the API cannot survive six concurrent requests; .env silently
  overrides all deployment configuration; and fundamentals plus analyst estimates are dead
  at the provider while returning HTTP 200.

The application should NOT be considered production-ready because:
  A user cannot sign up, cannot log in, and cannot save a record — and if six of them tried
  at once, a function that returns a constant dictionary would take 24 seconds. Deploying
  it to Postgres is currently impossible without a code change, because the committed .env
  overrides the environment. On top of that: fabricated uptime, VaR derived from a
  hardcoded 0.18, empty income statements returned as success, ~23 endpoints returning 500,
  a router that is silently dead beneath a 543-line page, and a test suite that runs zero
  tests.

Most important structural insight:
  The bottleneck is NOT the data layer — that is now largely real and is the product's moat.
  It is that ~48 of the last 50 commits optimised for closing tickets, and the three
  mechanisms that should have caught it all fail by design:
    · _safe_include downgrades a dead router to a warning
    · CI asserts only that the app imports
    · 146 silent except handlers turn provider failures into empty 200s
  Fix those three, flip two lines (override=False, async→def), and wire a login page, and
  this becomes a credible single-tenant product in roughly 3-4 focused weeks. Leave them,
  and the next regression ships exactly as quietly as the last one did.
```

---

### Appendix — Reproducing this audit

```bash
cd apps/api && source ../../venv/bin/activate

# 849 operations / 806 paths; 1 router dead at boot
python -c "from app.main import app; s=app.openapi(); \
print(len(s['paths']), sum(1 for p in s['paths'] for m in s['paths'][p] \
if m in ('get','post','put','patch','delete')))"

# THE headline defect: same endpoint, alone vs. concurrency 6
uvicorn app.main:app --port 8123 &
curl -s -o /dev/null -w "%{time_total}\n" localhost:8123/brokerage/brokers     # ~0.008s
for i in $(seq 6); do curl -s -o /dev/null localhost:8123/global/quote/AAPL & done
curl -s -o /dev/null -w "%{time_total}\n" localhost:8123/brokerage/brokers     # ~24s

# 266 of 268 async handlers never await
python - <<'PY'
import ast,glob
n=[f"{f}:{x.lineno}" for f in glob.glob("app/api/*.py")
   for x in ast.walk(ast.parse(open(f).read()))
   if isinstance(x,ast.AsyncFunctionDef) and not any(isinstance(y,ast.Await) for y in ast.walk(x))]
print(len(n))
PY

# .env silently overrides the environment  →  writes still land in local.db
DATABASE_URL=sqlite:////tmp/other.db python -c \
"from app.main import app; from app.core.settings import settings; print(settings.database_url)"

# the served auth API is not the documented one
curl -s -X POST localhost:8123/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"x"}'          # 422 (expects query params)

# zero tests run
python -m pytest tests/ -q                          # Interrupted: 3 collection errors
python -m pytest tests/ -q --continue-on-collection-errors   # 177 failed, 732 passed

# dead router, silent in a normal boot
python -c "import app.api.revision_screener"        # ImportError: ConsensusMomentum

# NaN 500 on the flagship dataset
python -c "from app.services.politician_leaderboard_service import search_politician as s; s('Pelosi')"

# core data dead at the provider, reported as HTTP 200
curl -s "localhost:8123/market/income-statement?ticker=AAPL"   # {"statements":[]}  (FMP 402)
curl -s "localhost:8123/analysts/price-targets/AAPL"           # all 0.0  (Finnhub 403)

# insider ticker filter silently ignored
curl -s "localhost:8123/insider/transactions?ticker=AAPL" | python3 -c \
"import json,sys,collections;print(collections.Counter(x['ticker'] for x in json.load(sys.stdin)['transactions']))"

# frontend has no auth, and 22 pages are unreachable
rg -c "Authorization|Bearer|localStorage" ../web --glob '*.js'   # no matches
ls ../web/pages | grep -iE "login|signup"                        # nothing
```

> **Workspace left unmodified.** The temporary sweep script was deleted; all rows written by the E2E test (`users`, `portfolios`, `workspaces`, `memberships`, `organizations`, `tracked_entities`) were removed and counts verified back at their original values. The only new file is this report.

---

### Note on repository hygiene (per project convention)

Documentation is correctly consolidated under `docs/`, but the root still carries `MASTER_TASK_STATUS.md`, `REALITY_DOC.md` (36 KB), `JAMES_ASKS.txt` (64 KB), `README.md` (32 KB) and `CHANGELOG.md`. Suggested cleanup:

- **Move** `MASTER_TASK_STATUS.md`, `REALITY_DOC.md`, `JAMES_ASKS.txt` into `docs/program/`; keep only `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md` at root.
- **Supersede** `docs/INDEPENDENT_AUDIT_2026-08-23.md` with this file (see §11 — three of its findings are incorrect).
- **Delete from VCS:** `reports/` (42 dirs of generated PDFs/JSON), `docs/US Government Officials — Stock Trading Rankings.xlsx` (118 KB binary), `apps/api/local.db`, `apps/api/app/scripts/smoke_test_results.json`, `.DS_Store` (root + `docs/`), `.pytest_cache/`, `apps/api/src/index.js`, `apps/worker/`, and the `bloomberg-terminal-free` gitlink.
- **Add to `.gitignore`:** `._*`, `.DS_Store`, `*.db`, `.pytest_cache/`.





