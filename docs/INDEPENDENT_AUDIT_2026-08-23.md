# Independent Verification Audit — Finance Advanced Research Platform

**Auditor:** Independent technical audit (evidence-driven, claims-ignored)
**Date:** 22–23 Aug 2026
**HEAD at audit:** `2aa49ee` (a second commit, `7568581`, landed mid-audit; both are covered)
**Method:** Booted the real FastAPI app, enumerated the live route table from the generated OpenAPI schema, executed 618 GET endpoints (sandboxed + real-network), ran targeted core-feature verification against real external APIs, ran the full pytest suite, executed a real register→login→create E2E against an isolated DB copy, and machine-diffed every frontend `fetch()` URL against the live route table.

> Nothing in this report is taken from `MASTER_TASK_STATUS.md`, `REALITY_DOC.md`, commit messages, or code comments. Every claim below has a reproducible command or file:line behind it.

---

## 1. Executive Summary

### What is really working

A genuine, non-trivial read-only financial data layer exists and returns **real, live, external data**. This is not fake — I verified it end-to-end over the network:

| Verified working | Evidence (live response) |
|---|---|
| Gov trading leaderboard | 633 politicians from static JSON, `/market/gov-trading/leaderboard/volume` → real names/volumes |
| Congress trading feed | `/market/gov-trading/recent` → live House filings (Khanna, Menefee), 12.8s |
| Earnings (Finnhub) | `/earnings/ticker/AAPL` → real EPS est. 1.9271 vs actual |
| IPO calendar (Finnhub) | `/ipo/upcoming` → real SIYATA PTT, 6,112,327 shares |
| Short interest (FINRA) | `/short-interest/ticker/AAPL` → 141,606,163 shares, DTC 2.58 |
| Options IV (yfinance) | `/volatility/surface/AAPL` → underlying 309.35, ATM IV 24.62 |
| Consensus (Finnhub) | `/consensus/snapshot?ticker=AAPL` → 54 analysts, 13 strong buy |
| Guidance credibility | `/guidance/credibility` → score 85.9, beat rate 75% |
| Valuation timeline | `/valuation/timeline/AAPL` → real P/E 35.48, historical series |
| FRED macro | `/market/macro/dashboard` → real GDP 32475.21 (27s) |
| Volume screening | `/volume/screen` → 27 screened, COIN flagged at 2.4x |
| Auth (JWT) | register→login→`/auth/me` all 200, bcrypt+JWT, users/audit_logs persisted |
| Workspace/RBAC persistence | 40 and 39 real SQLAlchemy calls; not stubs |

The HEAD commit's claim that ~21 services were converted from fake to real is **substantially true at the service layer**. Fake price generators (`hashlib.md5`, `_BETA_MAP`, `_PRICE_HISTORY`) are genuinely gone.

### What is broken or misleadingly complete

The product is **read-only in practice**. Every write workflow the UI advertises is impossible to perform from the UI:

- **6 of 8 write flows return 401** when called exactly as the frontend calls them, because the frontend sends **zero `Authorization` headers anywhere in 74 files** and has **no login page at all**.
- **`portfolios`, `positions`, `workspaces`, `dashboards`, `comments`, `watchlists`, `annotations`, `users` tables are all empty (0 rows)** — no user has ever successfully written data.
- A **duplicate auth router** (`routes.py`) shadows the new JWT router (`auth.py`), so `POST /auth/register` with a JSON body returns **422**. The documented API is not the served API.
- **`/revisions/*` is entirely dead** — router fails to import, yet `revisions.js` calls 5 of its endpoints.
- **177 of 910 tests fail (19.5%)**, 3 test modules cannot even import, and **CI runs no tests at all**.
- **578 of 806 endpoints (72%) are never called by the frontend.**

### Verdict in one line

The **data-retrieval half is real and respectable**; the **application half (accounts, persistence, writes, UI wiring) is not connected**. This is a working financial data API with a large, mostly-unwired demo frontend bolted to it.

---

## 2. Real Completion Percentages

```text
REAL APPLICATION COMPLETION: ~42%

Frontend:                  ~35%   (73 pages render; no auth, no login, 72% of API unused, 5 dead endpoints)
Backend:                   ~60%   (849 endpoints; core data real; writes gated by unreachable auth)
Core product functionality: ~55%   (read paths genuinely work; write/persist paths do not)
External integrations:     ~55%   (Finnhub/FINRA/yfinance/FRED/SEC/Congress real; Reddit/Plaid/GPU/push absent)
Integration (FE↔BE wiring): ~30%   (machine-verified: 228/806 routes reachable, 6/8 writes 401)
Production readiness:      ~20%   (no tests in CI, 177 failing, 266 blocking async handlers, sqlite, 5.5h endpoint)
```

**Why not the claimed 90–95%:** that figure counted *endpoint existence*. Weighted by product value, an endpoint a user cannot reach through the UI, or that writes to a table that stays empty, is worth close to zero. Note the in-repo docs have already self-corrected to ~25–40%; my independent figure of **~42%** is slightly *above* their latest estimate, because the most recent service rewrites are real and I verified them with live data.

---

## 3. Biggest Findings (ranked by severity)

**F1 — Duplicate auth router: the new JWT auth is dead code (P0).**
`app/api/routes.py:37` defines `POST /auth/register(email: str, password: str)` — query params. `app/api/auth.py:50` defines the same path with a Pydantic **JSON body**. `main.py:74` includes `core_router` *before* `auth_router` (line 75), so FastAPI's first-match wins and `routes.py` serves it. Proof: `POST /auth/register` with JSON body → **422 "missing query param email"**. Also the response schemas differ — `routes.py` login returns `{"token", "refresh_token"}`, `auth.py` returns `{"access_token"}`. Any client written against `/docs` breaks.

**F2 — The frontend has no authentication whatsoever (P0).**
`rg "Authorization|Bearer|localStorage.*token"` across all 74 frontend JS files → **zero matches**. `ls apps/web/pages | grep -iE "login|signup|auth"` → **NONE**. Instead pages hardcode `const USER_ID = 'demo_user'` (`pages/alerts.js:9`, `pages/pwa-advanced.js:12`) and pass it as a query param. Meanwhile 9 backend API modules now enforce `get_current_user`. The two halves are architecturally incompatible.

**F3 — Every advertised write flow is impossible from the UI (P0).**
Simulating the frontend exactly (no auth header): create portfolio **401**, create alert **401**, create workspace **401**, create dashboard **401**, post comment **401**, create team **401**. `POST /watchlist` and `POST /tracking/entities` → **404** (frontend calls paths that don't exist). **6/8 auth-blocked, 2/8 missing.**

**F4 — Zero business data has ever been persisted (P0).**
Live counts from `local.db`: `users 0, portfolios 0, positions 0, workspaces 0, memberships 0, organizations 0, dashboards 0, dashboard_widgets 0, watchlists 0, comments 0, annotations 0, roles 0, role_permissions 0`. `permissions` has 10 rows but `roles`/`role_permissions` are empty, so **RBAC can never grant anything**. The only populated tables are read-side caches: `claims 3551`, `report_sections 649`, `institutional_13f_position_cache 200`, `relationships 50`, `entities 45`.

**F5 — `/revisions/*` router is dead and the frontend calls it (P0).**
`main.py:139 _safe_include("app.api.revision_screener")` fails with `cannot import name 'ConsensusMomentum' from app.services.consensus_service`. The HEAD rewrite of `consensus_service.py` deleted that symbol. `pages/revisions.js:221,240,241,256,268` calls `/revisions/screen`, `/top-upward`, `/top-downward`, `/alerts`, `/summary` → all **404**. The page is 543 lines of permanently-broken UI. `_safe_include` logs only a `warning`, so the app boots "successfully" and CI passes.

**F6 — One endpoint ran for 5.5 hours and returned HTTP 200 (P0).**
`GET /corporate-ownership/full-analysis/{entity_name}` took **19,617.65 seconds**. `corporate_ownership.py:240` is `async def` but calls four synchronous, network-fanning functions with no `await`, no timeout, and no cap — `fetch_private_company_intel_full`, `detect_ultimate_beneficial_owners`, `cross_reference_ownership`, then a depth-2 graph walk. There is no `timeout` anywhere in `corporate_ownership.py`. In production this pins a worker forever.

**F7 — 266 `async def` endpoints contain zero `await` (P0).**
AST scan of `app/api/*.py`. Each performs synchronous network/DB I/O directly on the event loop, so **one slow request blocks all concurrent requests**. Worst offenders: `comments.py` (19), `intelligence_graph.py` (19), `pwa_advanced.py` (16), `corporate_ownership.py` (15), `portfolio.py` (14).

**F8 — 177 of 910 tests fail; CI runs none of them (P0).**
`pytest` → `177 failed, 732 passed, 1 skipped in 904s`. Failures: `test_whisper_api.py` (17), `test_volatility_api.py` (16), `test_revision_screener_api.py` (13), `test_short_interest_api.py` (3), plus **3 modules that cannot import at all** (`AnalystTier`, `SurpriseType`, `PriceVolumePattern` were deleted by the HEAD rewrite). `.github/workflows/ci.yml` runs only `python -c "from app.main import app"` — it never invokes pytest. The suite also takes 15 minutes with no timeout plugin.

**F9 — Tests were deleted rather than fixed.**
HEAD commit message: *"Deleted 8 impossible test files"* — `test_autonomous_agent_api.py`, `test_brokerage_sync_api.py`, `test_global_equity_api.py`, `test_medium_tasks_api.py` (585 lines), `test_mobile_pwa_api.py`, `test_narrative_model_api.py`, `test_portfolio_analytics_api.py`, `test_pwa_advanced_api.py`. These covered exactly the features that were gutted.

**F10 — 5 feature modules are 100% stubs, previously marked COMPLETE.**
Every function returns `{"status": "not_available"}`: `brokerage_sync_service.py` (52 lines, 9 stubs), `narrative_model_service.py` (52/9), `mobile_pwa_service.py` (52/9), `reddit_whale_service.py` (74/10), `pwa_advanced_service.py` (87/16), plus `mobile_native_service.py` (13) and `browser_extension_service.py` (6). Commits `1cd0f2b`, `416ee87`, `adc5043`, `8e1896e`, `2bf5d55` all claimed these "implemented"/"complete". **31 endpoints return stub responses.** Their frontend pages (`brokerage.js`, `narrative-model.js`, `pwa-settings.js`, `pwa-advanced.js`, `social.js`) are fully-built dead UI.

**F11 — Copy-paste evidence of automated gutting.**
`reddit_whale_service.py:45,59,64,69` return `details="Reddit API credentials not configured"` for `get_whale_transactions`, `get_top_whales`, `get_institutional_ownership`, `get_insider_sentiment` — none of which use Reddit (they're 13F/Form 4 data). The stub reason is wrong, proving the file was bulk-replaced without review. Worse: **13F data already exists in the DB** (`institutional_13f_position_cache` = 200 rows), so `get_institutional_ownership` could return real data today.

**F12 — `import random` still ships in a served endpoint; the CI guard misses it.**
`app/api/status.py:110-113`: `_calculate_uptime()` does `random.uniform(0, 0.09)` and returns a **fabricated 99.90%+ uptime** on the public status page. CI's guard only greps `apps/api/app/services/*.py`, so `app/api/` is unchecked. Also `experiments.py:13` imports random.

**F13 — Portfolio risk metrics return fake zeros presented as real values.**
`portfolio_service.py:605-635`: `# TODO: compute from real historical data via yfinance` → `sharpe_ratio = 0.0`, `sortino_ratio = 0.0`, `max_drawdown = None → 0.0`, `avg_correlation = None`. These are emitted in `RiskMetrics` as `0.0`, indistinguishable from a genuine zero. The HEAD commit claimed portfolio was made real; the *prices* were, the *risk math* was not.

**F14 — NaN crash in gov leaderboard search (regression the "fix" missed).**
`GET /market/gov-trading/leaderboard/search?name=Pelosi` → **500**. Reproduced: `politician_leaderboard_service.py:244` `official = (r.get("official") or r.get("name") or "").lower()` → `AttributeError: 'float' object has no attribute 'lower'` (a `NaN` float from the Excel import). Commit `61ec993` "fix: handle NaN values in politician leaderboard data" fixed other paths but not this one. `/leaderboard/rank/{name}` also 500s.

**F15 — 578 of 806 routes (72%) are never called by the frontend.**
Machine cross-check of every `fetch()` URL against the live route table. Entire subsystems are unreachable dead weight: all of `/ai-visibility/*`, `/editorial/*`, `/experiments/*`, `/export/*`, `/fact-scoring/*`, `/compliance/*`, `/freshness/*`, `/billing/*`, `/evidence/*`, `/registry/*`, most of `/consensus/*`, `/analysts/*`, `/benchmark/*`, `/corporate-ownership/*`.

**F16 — Persistent 500s unrelated to network (identical sandboxed and networked).**
`/filings/kpis` and `/filings/ontology` → `'list' object has no attribute 'get'`; `/filings/search` → 500; `/ontology/{t}` + 3 sub-routes → "Failed to build ontology"; `/persons/{id}` + 6 sub-routes → 500; `/registry/health`, `/registry/jurisdictions` → 500; `/search/recent`, `/search/saved`, `/searchos/` → 500; `/portfolio/compare` → 500; `/market/rss/*` (3) → 500. **~27 endpoints 5xx.**

**F17 — The scheduler cannot scale and persists nothing.**
`scheduler.py` runs 6 `daemon` threads inside the API process. Its own docstring: *"the fetched data lands in the connector's module-level cache."* So (a) all warmed data is lost on restart, (b) with N uvicorn workers you get N schedulers × 6 jobs hammering Finnhub/FINRA/SEC and N divergent caches, (c) `graph_ingestion` writes to the in-memory graph store, not the DB. `_refresh_global_indices` also has a bare `except: pass` per index.

**F18 — Entity graph is in-memory and loses everything on restart.**
`entity_graph_service.py:204-211`: `self._entities`, `self._edges`, `self._adjacency`, `self._reverse_adjacency` are plain dicts. 19 `/intelligence-graph/*` endpoints and the PayPal-Mafia seed (1,247 lines) all live in RAM. `/agent/graph/AAPL` returns data only because a seed loader repopulates it per-process.

**F19 — Docker deployment is misconfigured.**
`apps/web/Dockerfile:11` sets `ENV NEXT_PUBLIC_API_URL=http://api:8000` **after** `RUN npm run build` (line 9). Next.js inlines `NEXT_PUBLIC_*` at build time, so the value never reaches the bundle; and `http://api:8000` is a Docker-internal hostname a browser can never resolve. It only appears to work via the `lib/api.js` fallback `${window.location.hostname}:8000`, which breaks under HTTPS (Amplify/DuckDNS origins are in the CORS list) by generating `https://host:8000`.

**F20 — `apps/worker` is a phantom service.**
Contains only `Dockerfile` + `package.json`; `apps/worker/src/index.js` was deleted in HEAD. It is not in `docker-compose.yml`. `ecosystem.config.js` and the monorepo still reference a worker app.

**F21 — Production is configured for SQLite.**
`.env`: `DATABASE_URL=sqlite:///./local.db`. `docker-compose.yml` overrides to Postgres, but the Alembic migration set is a single `3dd8a2786cc5_initial_schema.py` created in `7568581` against the SQLite shape. No index review, and SQLite will not survive concurrent writes.

**F22 — Missing/empty credentials silently degrade to empty results.**
`SEC_API_KEY` is read by code but **absent from `.env`**. Empty in `.env`: `OPENSECRETS_API_KEY`, `REDDIT_CLIENT_ID/SECRET`, `OPENCORPORATES_API_TOKEN`, `SENATE_LDA_API_KEY`, `LDA_API_KEY`, `ALEPH_API_KEY`, `OIDC_CLIENT_ID/SECRET`, `REGISTRY_API_ADMIN_TOKEN`, `HIBP_API_KEY`, `CA_SOS_API_KEY`. Combined with ~120 `except: return []/pass` handlers, these produce **HTTP 200 + empty array** rather than an error — the single most dangerous pattern in the codebase for a data product.

**F23 — 197 endpoints returned all-empty arrays; 16 returned bare empty lists; 27 empty objects.**
Even on the real-network run, `/analysts/ranking` → `{"ranking": [], "total": 0}`, `/guidance/current` → `{"guidance": []}`, `/consensus/snapshot` → `mean: 0.0, high: 0.0, low: 0.0` while simultaneously reporting `num_analysts: 54` (partially-parsed Finnhub response presented as complete).

---

## 4. Critical Broken Workflows — exact break points

**W1. Sign up / log in — breaks at step 1.**
```
[ ] User reaches a login page        <- FAIL: no login/signup page exists in apps/web/pages
[ ] Credentials submitted            <- FAIL: no frontend code calls /auth/*
[ ] Token stored                     <- FAIL: zero localStorage/token handling
[ ] Token sent on requests           <- FAIL: zero Authorization headers in 74 files
```
Backend auth itself works (verified 200/200/200 register→login→me), so this is **pure missing wiring**, and it is the single highest-leverage fix in the repo.

**W2. Create a portfolio — breaks at the API call.**
```
UI control      OK   pages/portfolios.js:389 modal + button
frontend fn     OK   fetch(`${API_BASE}/portfolio?${params}`, {method:'POST'})
payload shape   OK   query params — correctly matches the backend signature
auth            FAIL 401 "Missing authentication token" (no header sent)
persistence     FAIL portfolios table = 0 rows
error surfaced  FAIL portfolios.js:394 `catch (err) { console.error(err) }` — user sees nothing
```
The modal closes on failure paths in sibling handlers and the list silently stays empty. This is the "fallback hides failure" pattern in the UI layer.

**W3. Estimate revision screener — breaks at router import.**
```
pages/revisions.js (543 lines) -> /revisions/screen -> 404
Cause: main.py:139 _safe_include fails: ImportError ConsensusMomentum
       (deleted from consensus_service.py by HEAD commit 2aa49ee)
Logged as a WARNING only; app boots green; CI passes.
```

**W4. Any social / whale / Reddit view — breaks at the service.**
`pages/social.js` → 10 `/social/*` endpoints → all return `{"status":"not_available","reason":"api_key_missing"}`. Not credential-blocked: the service body is a hardcoded stub with no real code path, so supplying Reddit keys would change nothing.

**W5. Brokerage linking — breaks at the service, with a fake token in the UI.**
`pages/brokerage.js:59` posts `access_token=simulated_token` to `/brokerage/link/complete` → stub 200. The UI simulates a successful Plaid link against a service that has no implementation.

**W6. Corporate ownership deep-dive — breaks by hanging.**
`/corporate-ownership/full-analysis/1` → 200 after **19,617s**. No user or load balancer waits 5.5 hours; in practice this is a guaranteed gateway timeout plus a leaked worker.

**W7. Government official search — breaks with a 500.**
`/market/gov-trading/leaderboard/search?name=Pelosi` → 500 (`AttributeError` on NaN). Note the frontend also builds a malformed URL at `gov-trading-leaderboard.js` — a template literal `/market/gov-trading/leaderboard/${activeTab === 'notable' ...}` leaks a raw JS expression into the path.

---

## 5. Last 50 Commits — claimed vs. actual

The 50 commits span **16 Jul → 22 Aug 2026** and fall into three distinct phases.

### Phase A — "Feature factory" (16–17 Aug, ~25 commits)
Pattern per commit: one API file + one service file + one test file + one 200–600 line Next.js page, then a follow-up `docs:` commit ticking boxes in `MASTER_TASK_STATUS.md`.

| Commit | Claimed | Actual |
|---|---|---|
| `2bf5d55` | "complete 10 MEDIUM tasks with full stack implementation" (7,864 lines) | Mixed. `workspace`/`team_permission`/`cost_basis`/`tax_lot` later became real; `reddit_whale` became a pure stub. Its 585-line test file was **deleted** in HEAD. |
| `1cd0f2b` | "brokerage sync API with Plaid/OAuth integration" | **No Plaid integration ever existed.** Now 52 lines of stubs. Test deleted. |
| `416ee87` | "narrative model training and deployment" | **No training code.** 52 lines of stubs. Test deleted. |
| `adc5043` | "Mobile PWA with push notifications" | **No push service.** 52 lines of stubs. Test deleted. |
| `8e1896e` | "PWA Advanced — offline caching, WebAuthn, screen sharing" | **None implemented.** 87 lines of stubs + 626-line dead UI. Test deleted. |
| `94943eb` | "complete portfolio analytics suite (D1–D11)" | Was fake; genuinely rewritten in HEAD (860 lines, real yfinance). Test deleted anyway. |
| `7148c03` | "Global Equity Coverage for international markets" | Test deleted; service later rewritten to 498 lines. |
| `224fdf1`/`15d91db` | "autonomous agent loop" / "recursive entity discovery" | Real code now exists, but backed by the **in-memory** graph (F18). |

**Assessment:** this phase generated ~25,000 lines and a wall of green checkboxes while adding roughly zero *usable* features. The tests written alongside were the ones later deleted as "impossible" — they were asserting on mock shapes.

### Phase B — "Real data push" (21 Aug, 8 commits)
This phase is **the most honest work in the audit window**.
- `226344f` — 38,277 lines of real gov-trading data (637 officials, parsed from Excel). Genuinely valuable; still the single most reliable feature.
- `6b98cda` — *"fix: resolve mock data exposure in investor-facing endpoints"* — an explicit admission that shipped features were serving mock data to investors. Added 4 real connectors (Finnhub earnings, FINRA short interest, FMP IPO, private company).
- `ab07733` — real FRED/gov/LinkedIn connectors. Verified working.
- `227846f`/`7d63a5d`/`82a7c0b` — graph store + ingestion, but in-memory (F18).
- `61ec993` — NaN fix that **missed** the `search_politician` path (F14, still 500s).
- `d27b69e` — 496-line `network-graph.js` page added with **no backend commit** alongside it.

### Phase C — "The great gutting + regutting" (22 Aug, 2 commits, both same day)
- **`7568581`** *"complete platform overhaul — real APIs, no fake data"*: net **−3,623 lines**. Deleted ~12,000 lines of mock generators across 30+ services, replacing them with `no_data` stubs. Added real infra: Alembic migrations, JWT `auth.py`, `no_data.py` contract, `scheduler.py`, CI, `NoDataCard.js`. Also rewrote `MASTER_TASK_STATUS.md` down to **"~25-30%"** — a self-audit contradicting all prior claims. **This commit is directionally correct and the most important in the window.** But it introduced F1 (the shadowed auth router) and left ~40 services as stubs.
- **`2aa49ee`** *"convert all remaining stubs to real services — 70%+ verified"*: +8,726/−3,401. **Genuinely converted ~21 services to real yfinance/Finnhub calls** — I verified 19 of them returning live data. However: it **broke 4 modules' public APIs** (`ConsensusMomentum`→F5 dead router, `AnalystTier`/`SurpriseType`/`PriceVolumePattern`→3 uncollectible test modules), **deleted 8 test files** instead of fixing them, and its "70%+ verified" claim is **unsupported** — the suite it left behind has 177 failures and CI runs none of it.

### Cross-cutting patterns
1. **Documentation-driven development** — 8 of 50 commits (16%) only edit `MASTER_TASK_STATUS.md`. Progress was tracked by editing a file, not by verifying behaviour.
2. **Tests as decoration** — written against mocks, deleted when mocks were removed, never run in CI.
3. **`_safe_include` hides structural breakage** — a `warning` log lets a dead router pass as a healthy boot (F5).
4. **The last two commits contradict all 48 before them** — and are right to.

---

## 6. Dead / Duplicate / Unnecessary Code

**Delete outright**
- `app/api/routes.py` auth block (lines ~37–60) — duplicate `/auth/register` + `/auth/login` shadowing `auth.py` (F1). Pick one; `auth.py` is the better implementation.
- `apps/worker/` — Dockerfile + package.json with no source (F20). Remove, or restore it as the scheduler host.
- `apps/api/app/services/*` macOS AppleDouble junk — `._*.py` / `.___init__.py` were binary files tracked in git until `7568581`. Verify `.gitignore` covers `._*`.
- `bloomberg-terminal-free` — committed as a **gitlink/submodule entry with no `.gitmodules`**; will break fresh clones.
- `apps/api/local.db` — a tracked SQLite DB in the repo.
- `apps/api/app/scripts/smoke_test_results.json` — committed test output.
- `reports/` (42 dirs) + `docs/*.xlsx` — build artifacts / binaries in VCS.

**Simplify (unnecessary complexity for actual requirements)**
- **95 services / 79 API modules / 849 endpoints for ~15 real features.** The one-service-per-ticket structure produced ~40 modules that only wrap a single connector call. Collapse into ~15 domain services.
- **`no_data_response()` is over-engineered.** An 11-value enum + message map, and the calling convention is already inconsistent: `{"status": "not_available", "reason": "...", **no_data_response(...)}` — the literal `reason` key is immediately **overwritten** by the enum value inside the spread, so the human-readable reason is silently lost at every one of ~70 call sites. Either fix the ordering or reduce to `{"no_data": True, "reason": str, "source": str}`.
- **266 pointless `async def`** (F7) — mechanically convert to `def` so FastAPI threadpools them. This is a one-line-per-handler change that removes the entire event-loop-blocking class of bug.
- **`_safe_include` × 48** — replace with a hard failure in dev/CI and a loud, surfaced health-check entry in prod.
- **4 frontend API clients** — `lib/api.js`, `lib/institutional.js`, `lib/intelligence.js`, `lib/institutional-models.js`, plus 74 files doing raw `fetch`. Consolidate into one client that injects auth and normalizes `no_data`.

**Keep (genuinely required)**
Alembic migrations, the connector layer (real and well-isolated), `NoDataCard.js`, JWT security in `auth/security.py`, the gov-trading static dataset.

---

## 7. Gap Analysis

| Area | Claimed State | Actual State | Evidence | Sev | Remaining Work |
|---|---|---|---|---|---|
| Auth wiring | "JWT auth complete" | Backend works; **frontend has none**; new router shadowed | 0 `Authorization` in 74 files; no login page; `/auth/register` JSON→422 | **P0** | Login page + token store + fetch wrapper; delete dup router |
| Write flows | Portfolios/alerts/teams "complete" | **6/8 return 401, 2/8 404** | Simulated FE calls | **P0** | Depends on auth wiring |
| Persistence | "DB integration done" | **13 business tables = 0 rows** | sqlite counts | **P0** | Verify after auth fix |
| Revision screener | "#37 complete" | **Router dead, 5 FE endpoints 404** | ImportError `ConsensusMomentum` | **P0** | Restore symbol or refactor |
| Concurrency | — | **266 blocking async handlers**; one 5.5h request | AST scan; 19,617s timing | **P0** | `async`→`def`; add timeouts |
| Test/CI | "tests added" per commit | **177 fail, 3 uncollectible, CI runs none** | pytest 904s | **P0** | Fix imports; run pytest in CI |
| Brokerage/PWA/Reddit/Narrative | "implemented"/"complete" | **7 services = pure stubs, 31 endpoints** | 52–87 line files | **P1** | Implement or remove UI |
| Portfolio risk | "risk metrics endpoint" | **Sharpe/Sortino/drawdown hardcoded 0.0** | `portfolio_service.py:605-635` | **P1** | Compute from yfinance history |
| Status page uptime | "status page" | **`random.uniform` fabricated uptime** | `status.py:110` | **P1** | Real monitoring or remove |
| Gov search | "leaderboard complete" | **500 on NaN** | reproduced AttributeError | **P1** | Coerce non-str at :244 |
| 5xx endpoints | — | **~27 endpoints 5xx** (filings/ontology/persons/search/registry) | both runs | **P1** | Fix or remove |
| Entity graph | "Graph Store + Recursion Engine" | **In-memory; lost on restart** | plain dicts :204-211 | **P1** | Persist to existing tables |
| Scheduler | "cron wiring complete" | **In-process threads, module-level cache, N× per worker** | `scheduler.py` | **P1** | Move out; persist to DB/Redis |
| FE↔BE coverage | "frontend wired" | **578/806 routes (72%) unused** | machine diff | **P2** | Delete or expose |
| Docker/web | "production infra" | **`NEXT_PUBLIC_API_URL` set after build; internal hostname** | `Dockerfile:9,11` | **P1** | Use build ARG + public URL |
| Empty results | "real APIs, no fake data" | **197 all-empty responses; ~120 silent excepts** | classification | **P1** | Distinguish empty vs. failed |
| Secrets | ".env.example all 55+ vars" | `SEC_API_KEY` absent; 20 empty | env diff | **P2** | Document required vs optional |
| DB target | "production infra" | **`.env` = SQLite**; single migration | `.env` | **P2** | Postgres + index review |

---

## 8. Remaining Work — fresh task list

### P0 — MUST FIX (product is unusable without these)

**P0-1. Delete the duplicate auth router shadowing the JWT implementation.**
- *Why:* `routes.py:37,47` registers `/auth/register` + `/auth/login` with **query params** and is included at `main.py:74`, before `auth_router` at line 75. FastAPI first-match-wins, so the documented JSON API returns 422 and `auth.py` is dead code. Response schemas also disagree (`token` vs `access_token`).
- *Files:* `app/api/routes.py` (remove auth block ~37–60), `app/api/auth.py`, `app/main.py`.
- *Fix:* Delete the `routes.py` auth endpoints. Keep `auth.py`. Port anything unique (refresh token, MFA, `AuditLog` write) into `auth.py`. Standardize on `access_token`.
- *Verify:* `curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' -d '{"email":"a@b.com","password":"x"}'` → **201 with `access_token`** (currently 422). Assert only one `/auth/register` in `openapi.json`.
- *Complexity:* S (2–4h).

**P0-2. Build frontend authentication: login page, token storage, authenticated fetch wrapper.**
- *Why:* Zero `Authorization` headers across 74 files, no login page, `USER_ID = 'demo_user'` hardcoded. Directly causes 6/8 write flows to 401 and all 13 business tables to be empty.
- *Files:* new `apps/web/pages/login.js`, `apps/web/lib/auth.js`, extend `apps/web/lib/api.js` with `apiFetch()`; `apps/web/pages/_app.js` (route guard); `Layout.js` (user menu/logout). Then replace hardcoded `user_id` in `pages/alerts.js:9`, `pages/pwa-advanced.js:12`, `benchmark.js` (`demo_user`).
- *Fix:* `apiFetch(path, opts)` reads the token, sets `Authorization: Bearer`, and on 401 redirects to `/login`. Migrate all 74 files off raw `fetch`. Derive `user_id` server-side from the JWT — **stop accepting it as a query param**, which is currently an authorization bypass on any endpoint not using `get_current_user`.
- *Verify:* Log in via UI → create a portfolio → `select count(*) from portfolios` returns 1 → reload shows it.
- *Complexity:* M (2–3d).

**P0-3. Restore `ConsensusMomentum` and un-break the `/revisions` router.**
- *Why:* `main.py:139` silently fails: `cannot import name 'ConsensusMomentum' from app.services.consensus_service` (deleted in `2aa49ee`). All 10 `/revisions/*` endpoints are absent; `pages/revisions.js` (543 lines) is 100% broken.
- *Files:* `app/services/consensus_service.py`, `app/services/revision_screener_service.py:22,197`, `app/api/revision_screener.py:27`.
- *Fix:* Re-add the `ConsensusMomentum` dataclass/enum (recover from `git show 7568581^:apps/api/app/services/consensus_service.py`) or refactor `_classify_trend` to consume the new return shape.
- *Verify:* `/revisions/screen`, `/top-upward`, `/top-downward`, `/alerts`, `/summary` all non-404; `test_revision_screener_api.py` 13 failures → 0.
- *Complexity:* S (2–4h).

**P0-4. Make `_safe_include` fail loudly instead of hiding dead routers.**
- *Why:* A `logger.warning` at `main.py:115-116` let P0-3 ship unnoticed and pass CI. This is the mechanism that allows silent structural breakage.
- *Files:* `app/main.py:107-166`, `.github/workflows/ci.yml`.
- *Fix:* Raise when `ENV in (local, ci)`; in prod, record failures in a module-level list and expose them via `/health` as a degraded status. Add a CI assertion that the failure list is empty.
- *Verify:* Temporarily break an import → app refuses to boot locally and CI goes red.
- *Complexity:* S (1–2h).

**P0-5. Convert the 266 no-await `async def` handlers to `def`, and add timeouts to every outbound call.**
- *Why:* Each does sync I/O on the event loop, so one slow call blocks all traffic. `/corporate-ownership/full-analysis/{name}` measured **19,617s (5.5h)** returning 200.
- *Files:* all of `app/api/*.py` (worst: `comments.py` 19, `intelligence_graph.py` 19, `pwa_advanced.py` 16, `corporate_ownership.py` 15, `portfolio.py` 14).
- *Fix:* (a) Change `async def`→`def` for handlers with no `await` — FastAPI then runs them in a threadpool. (b) In `corporate_ownership.py:240`, bound the fan-out: per-source timeout, cap `max_depth`, and return partial results with a `partial: true` flag. (c) Enforce a default `timeout=` on every `requests`/`httpx` call in `app/connectors/`.
- *Verify:* Re-run the endpoint sweep; **no endpoint exceeds ~30s**. Load-test 20 concurrent `/corporate-ownership/*` and confirm unrelated endpoints stay responsive.
- *Complexity:* M (1–2d, mostly mechanical).

**P0-6. Fix the 3 uncollectible test modules and make CI actually run pytest.**
- *Why:* `177 failed, 732 passed` in 904s, and `ci.yml` only does `python -c "from app.main import app"`. Three modules can't even import because `2aa49ee` deleted `AnalystTier`, `SurpriseType`, `PriceVolumePattern`.
- *Files:* `app/services/analyst_scoring_service.py`, `consensus_service.py`, `volume_screening_service.py`; `tests/test_analyst_service.py:15`, `test_consensus_service.py:17`, `test_volume_service.py:15`; `.github/workflows/ci.yml`.
- *Fix:* Re-export the three symbols (or update tests to the new API — but only after confirming the symbol isn't used elsewhere). Add `pytest` + `pytest-timeout` to CI with `--timeout=60`. Mark network tests so CI can run an offline subset fast. Extend the `import random` guard from `app/services/` to **all** of `app/`.
- *Verify:* `pytest --co` collects cleanly; CI fails on any regression; the random guard catches `status.py:110`.
- *Complexity:* M (1–2d).

### P1 — IMPORTANT

**P1-1. Replace fabricated status-page uptime.** `app/api/status.py:110-113` returns `99.90 + random.uniform(0, 0.09)`. Publishing invented uptime is a trust/compliance problem. Either compute from a real store or return `no_data`. *Verify:* no `random` import in `app/api/`. **S**

**P1-2. Compute real portfolio risk metrics.** `portfolio_service.py:605-635` emits `sharpe_ratio=0.0`, `sortino_ratio=0.0`, `max_drawdown=0.0`, `avg_correlation=None` behind three TODOs, indistinguishable from real zeros. Pull history via yfinance (already a dependency) and compute properly, or return `null` + `"metrics_unavailable"`. **M**

**P1-3. Fix the NaN crash in `search_politician`.** `politician_leaderboard_service.py:244` — `(r.get("official") or r.get("name") or "").lower()` raises `AttributeError` on a NaN float. Coerce with `str(... or "")` and sanitize NaN at JSON-load time. Also fixes `/leaderboard/rank/{name}`. *Verify:* `?name=Pelosi` → 200. **S**

**P1-4. Triage the ~27 persistently-5xx endpoints.** Same failures with and without network, so these are code bugs: `/filings/kpis` + `/filings/ontology` (`'list' object has no attribute 'get'`), `/filings/search`, `/ontology/{t}`(+3), `/persons/{id}`(+6), `/registry/health`, `/registry/jurisdictions`, `/search/recent`, `/search/saved`, `/searchos/`, `/portfolio/compare`, `/market/rss/*`(3). Fix or remove — a 500 is worse than a 404. **M**

**P1-5. Distinguish "no data" from "call failed".** ~120 handlers do `except: return []` / `pass`, yielding 197 all-empty 200s. For a data product this is the worst failure mode. Return `no_data` with the real reason, log the exception, and surface it in `NoDataCard.js`. Also fix the `no_data_response` key-collision bug (the literal `reason` is overwritten by the spread at ~70 call sites). **M**

**P1-6. Persist the entity graph.** `entity_graph_service.py:204-211` uses plain dicts; 19 `/intelligence-graph/*` endpoints plus the 1,247-line PayPal-Mafia seed vanish on restart. `entities`/`relationships` tables already exist (45/50 rows) and `_entity_db_pk`/`_edge_db_pk` hint at intent. Complete the write-through. **L**

**P1-7. Move the scheduler out of the API process.** `scheduler.py` runs 6 daemon threads writing to module-level caches — data lost on restart, and N uvicorn workers means N schedulers hammering Finnhub/FINRA/SEC with N divergent caches. Run as a separate process (restore `apps/worker`) writing to Postgres/Redis. Remove the bare `except: pass` in `_refresh_global_indices`. **M**

**P1-8. Fix the web Dockerfile build-time env bug.** `apps/web/Dockerfile:11` sets `ENV NEXT_PUBLIC_API_URL` **after** `RUN npm run build` (line 9), so Next.js never inlines it; and `http://api:8000` is unresolvable from a browser. Use `ARG NEXT_PUBLIC_API_URL` before build and pass a browser-reachable public URL. Note `lib/api.js:7` masks this with a `hostname:8000` fallback that breaks under HTTPS. **S**

**P1-9. Decide the fate of the 7 stub services.** 31 endpoints + 5 fully-built dead pages return `{"status":"not_available"}`: `brokerage_sync`, `narrative_model`, `mobile_pwa`, `pwa_advanced`, `reddit_whale`, `mobile_native`, `browser_extension`. Either implement, or remove the pages and endpoints so the UI stops advertising them. **Quick win inside this:** `reddit_whale_service.get_institutional_ownership` is blocked on a bogus "Reddit credentials" reason but `institutional_13f_position_cache` already holds 200 rows — wire it and delete `pages/brokerage.js:59`'s `access_token=simulated_token`. **M**

### P2 — CLEANUP / QUALITY

**P2-1.** Resolve the 578 unused endpoints (72%): delete dead subsystems (`/ai-visibility`, `/editorial`, `/experiments`, `/fact-scoring`, `/freshness`, `/compliance/content`) or expose them. Removing them shrinks the audit surface dramatically. **L**
**P2-2.** Consolidate 4 frontend API clients + 74 raw-`fetch` files into one client (pairs with P0-2). **M**
**P2-3.** Surface errors in the UI — replace `catch (err) { console.error(err) }` (e.g. `portfolios.js:307,394`) with visible error states. **M**
**P2-4.** Remove repo junk: `apps/worker/` shell, `local.db`, `smoke_test_results.json`, `reports/`, `docs/*.xlsx`, and the `bloomberg-terminal-free` gitlink with no `.gitmodules` (breaks fresh clones). Add `._*` to `.gitignore`. **S**
**P2-5.** Fix the malformed template literal in `gov-trading-leaderboard.js` leaking a JS expression into the URL path. **S**
**P2-6.** Move `DATABASE_URL` to Postgres, review indexes on `claims` (3,551) and `institutional_13f_position_cache`, and validate the single Alembic revision against the Postgres shape. **M**
**P2-7.** Document required vs. optional env vars: `SEC_API_KEY` is read by code but missing from `.env`; 20 vars are present-but-empty. Fail fast at startup on missing *required* keys. **S**
**P2-8.** Replace deprecated `@app.on_event("startup")` (`main.py:175`) with lifespan handlers; fix Pydantic v2 `class Config` warnings (`settings.py:8`, `auth.py:36`). **S**
**P2-9.** Collapse 95 services / 79 API modules into ~15 domain services (see §6). **L**

---

## 9. Recommended Fix Order

```
1 → P0-1  Delete duplicate auth router          (unblocks everything; 2-4h)
2 → P0-2  Frontend auth: login + token + fetch  (turns a demo into an app)
3 → P0-3  Restore ConsensusMomentum             (revives /revisions + 13 tests)
4 → P0-4  Make _safe_include fail loudly        (stops the next silent break)
5 → P0-6  Fix test imports + run pytest in CI   (locks in every fix above)
6 → P0-5  async→def + timeouts                  (removes the 5.5h endpoint)
7 → P1-3  NaN crash  ·  P1-1 fake uptime  ·  P1-8 Dockerfile   (quick, high-trust)
8 → P1-5  Real error semantics                  (stop 200-with-empty-array)
9 → P1-2  Real risk metrics  ·  P1-4 the 27 5xx endpoints
10→ P1-6  Persist graph  ·  P1-7 extract scheduler
11→ P1-9  Implement-or-delete the 7 stub features
12→ P2-*  Dead code, consolidation, Postgres, cleanup
```

Rationale: steps 1–2 convert the product from read-only-demo to usable application and are worth more than all remaining work combined. Steps 3–5 stop the bleeding — without CI actually running tests, every later fix can silently regress (exactly how P0-3 shipped). Refactoring (P2-9) is deliberately last.

---

## 10. Production Blockers

A paying customer cannot reliably use this product today because:

1. **They cannot create an account or log in** — no login page, no token handling (F2).
2. **They cannot save anything** — 6/8 writes 401; portfolios/watchlists/dashboards/comments tables are all empty (F3, F4).
3. **Multi-tenancy is unenforceable** — `roles`/`role_permissions` empty, and `user_id` arrives as a **spoofable query param** on endpoints lacking `get_current_user`.
4. **One request can take down the API** — 266 blocking handlers; a measured 5.5-hour request (F6, F7).
5. **Several pages are permanently broken** — `/revisions` 404s; 5 pages front pure stubs; ~27 endpoints 5xx (F5, F10, F16).
6. **Failures are invisible** — HTTP 200 + `[]` from ~120 silent excepts; the UI logs to console only (F22, F23).
7. **No safety net** — 177 failing tests, CI runs none (F8).
8. **SQLite in `.env`**, in-memory graph and scheduler caches lost on every restart, and a web image whose API URL never reaches the bundle (F17, F18, F19, F21).
9. **Published metrics are fabricated** — random uptime on the status page; `0.0` Sharpe/Sortino presented as real (F12, F13).

---

## 11. Final Verdict

```
Existing claimed completion:   90–95%   (historical claims in commits/checklists)
In-repo self-corrected claim:  25–30%   (MASTER_TASK_STATUS.md) / 70%+ (HEAD commit message)
Independently verified:        ~42%

Reason for the difference:
  The 90-95% figure counted endpoint and file existence — 849 endpoints, 95 services,
  73 pages. Weighted by product value, an endpoint no UI calls (578 of 806) and a write
  path that 401s into an empty table is worth ~0. Conversely, the HEAD commit's "70%+
  verified" is also wrong in the other direction: it is unverifiable, since the suite it
  left behind has 177 failures and CI executes none of them.

  My ~42% sits between the two because the split is unusually clean:
    - The READ half is genuinely real. I confirmed live external data from Finnhub,
      FINRA, yfinance, FRED, SEC EDGAR and Congress.gov across 19 core endpoints.
      The last two commits did real work and deserve credit.
    - The APPLICATION half does not exist in practice. No login, no persisted row in
      any of 13 business tables, 72% of the API unreachable from the UI.

The application should NOT be considered production-ready because:
  A user cannot sign up, cannot log in, and cannot save a single record. That is not a
  polish gap — it is the absence of the application layer. Add 266 event-loop-blocking
  handlers, a measured 5.5-hour request, ~27 endpoints returning 500, a router that is
  silently dead while its 543-line page 404s, fabricated uptime numbers, and a 19.5%
  test failure rate that CI never observes.

Most important structural insight:
  The bottleneck is NOT the data layer — that is now largely real. It is that ~48 of the
  last 50 commits optimised for closing tickets rather than shipping usable workflows,
  and the two mechanisms that should have caught this both failed by design:
  `_safe_include` downgrades a dead router to a warning, and CI asserts only that the
  app imports. Fix those two, wire authentication, and this becomes a credible product
  in roughly 2-3 focused weeks. Leave them, and the next regression ships just as quietly.
```

---

### Appendix — Reproducing this audit

```bash
# Live route table + router load failures (849 ops; 1 router dead)
cd apps/api && python -c "
from app.main import app; s=app.openapi()
print(sum(1 for p in s['paths'] for m in s['paths'][p] if m in ('get','post','put','patch','delete')))"

# Full test suite: 177 failed, 732 passed, 3 uncollectible
RATE_LIMIT=off RAG_PRELOAD=off python -m pytest tests/ -q

# The dead router (silent in normal boot)
python -c "import app.api.revision_screener"   # ImportError: ConsensusMomentum

# The NaN 500
python -c "from app.services.politician_leaderboard_service import search_politician as s; s('Pelosi')"

# Empty business tables
sqlite3 apps/api/local.db "select 'portfolios',count(*) from portfolios union all
  select 'users',count(*) from users union all select 'workspaces',count(*) from workspaces;"

# Blocking async handlers (266)
python - <<'PY'
import ast,glob
n=[f"{f}:{x.lineno}" for f in glob.glob("app/api/*.py")
   for x in ast.walk(ast.parse(open(f).read()))
   if isinstance(x,ast.AsyncFunctionDef) and not any(isinstance(y,ast.Await) for y in ast.walk(x))]
print(len(n))
PY

# Frontend has zero auth
rg -c "Authorization|Bearer" apps/web --glob '*.js'   # no matches
ls apps/web/pages | grep -iE "login|signup"           # nothing
```

> Audit scripts were run from `apps/api/` and removed afterwards; all E2E writes targeted a **copy** of the database (`/tmp/audit_copy.db`), so `local.db` and the working tree were left unmodified.

