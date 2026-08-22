Here's the fastest path from ~25% to 70-80%. The key insight: **connectors are real, frontend is wired, DB schema exists**. The bottleneck is purely the service layer. We're essentially doing a "swap fake for real" sprint.

---

## The 70% Sprint — Priority Order

### Phase 1: "Instant Wins" (2-3 days, gets you to ~40%)

These require minimal code because infrastructure already exists:

**1. Wire portfolio service to yfinance (already installed)**

```python
# Replace _get_market_data() in portfolio_service.py
# FROM: hashlib.md5(ticker) fake prices
# TO:
import yfinance as yf

def _get_market_data(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    data = yf.download(tickers, period="2d", progress=False)
    # ... parse real close/prev_close
```

Effort: 2-3 hours. Unlocks: portfolios, cost-basis, benchmark pages all show real prices.

**2. Complete earnings_calendar_service — remove all mock fallbacks**

Already has `finnhub_earnings_connector` imported. Just replace the 5 functions that still call `_generate_mock_earnings()` with real connector calls. The connector functions already exist.

Effort: 1-2 hours.

**3. Complete short_interest_service — remove mock fallbacks**

Same pattern. `finra_short_interest_connector` works. Wire the remaining 5 functions that use `random` to call the connector's real data.

Effort: 1-2 hours.

**4. Enforce no_data_response for ALL services that can't be made real yet**

For the ~20 services you can't fix immediately (reddit whale, narrative model, brokerage sync, etc.), replace `import random` + fake data with:

```python
from app.core.no_data import no_data_response, NoDataReason

def get_whale_flow(ticker: str):
    return no_data_response(ticker, "whale_flow", NoDataReason.API_UNAVAILABLE, source="Reddit")
```

This is honest — the frontend can render a "data unavailable" state instead of misleading random numbers.

Effort: 4-5 hours (mechanical, one service at a time).

**5. Remove `try/except: pass` in main.py — log failures**

```python
# FROM:
try:
    from app.api.portfolio import router as portfolio_router
    app.include_router(portfolio_router)
except Exception:
    pass

# TO:
try:
    from app.api.portfolio import router as portfolio_router
    app.include_router(portfolio_router)
except Exception as e:
    logger.warning(f"Failed to load portfolio router: {e}")
```

Effort: 30 minutes. Impact: Stops hiding failures.

---

### Phase 2: "Wire Real Data" (4-5 days, gets you to ~55%)

**6. Persist entity graph to PostgreSQL**

Tables `entities`, `relationships`, `entity_identifiers`, `relationship_evidence` already exist in the SQLite schema. The `EntityGraphStore` class just needs to write to them instead of in-memory dicts.

```python
# In entity_graph_service.py, replace:
self._entities: Dict[str, EntityNode] = {}

# With SQLAlchemy queries against existing tables
from app.db.session import get_db_context
```

Effort: 1-2 days. Impact: Graph data survives restarts, which is the product's core differentiator.

**7. Wire FRED connector for economics/macro dashboard**

`FRED_API_KEY` is already in `.env`. Create a simple FRED connector (the financial_news_connector already has a `fred_series()` function!). Wire it to the economics page.

Effort: 3-4 hours.

**8. Wire insider_activity_service to SEC EDGAR Form 4**

The `sec_edgar_connector` already has functions. The insider_activity_service currently uses `random`. Replace with real Form 4 parsing from SEC.

Effort: 1 day.

**9. Wire M&A rumors to news aggregation**

`financial_news_connector` already fetches from NewsAPI, Guardian, GDELT. Create a filtered news search for M&A keywords instead of the hardcoded rumor list.

Effort: 4-5 hours.

**10. Add Alembic migrations**

```bash
cd apps/api
pip install alembic
alembic init migrations
alembic revision --autogenerate -m "initial schema"
```

Effort: 2-3 hours. Impact: Safe deployments, schema versioning.

---

### Phase 3: "Core Product" (5-7 days, gets you to ~70-80%)

**11. Implement JWT auth middleware**

Models exist. Add a `get_current_user()` dependency that validates JWT. Apply to mutation endpoints first, read endpoints second.

Effort: 1-2 days.

**12. Build a simple scheduler/worker for data refresh**

Use APScheduler (Python) or a simple cron:
- Every 6h: Refresh gov trading data from Capitol Trades
- Every 1h: Refresh earnings calendar from Finnhub
- Every 4h: Refresh short interest from FINRA

Effort: 1 day.

**13. Wire graph ingestion service to scheduler**

The `graph_ingestion_service.py` already makes real SEC/FEC/USASpending calls. Just schedule it and persist results to DB.

Effort: 1 day.

**14. Switch to PostgreSQL for production**

SQLite → PostgreSQL. The `session.py` already supports this via `DATABASE_URL`. Just provision a PG instance and update `.env`.

Effort: 3-4 hours (infra setup).

**15. Frontend: Add proper error/no-data states**

Only 2 pages show errors to users. Add a shared `<NoDataCard>` component that renders when backend returns `{ "no_data": true }`.

Effort: 4-5 hours.

---

## Sprint Schedule (Fastest Path)

| Day | Tasks | Expected Result |
|-----|-------|-----------------|
| **Day 1** | #1 (yfinance), #2 (earnings real), #3 (short interest real), #5 (logging) | Portfolio/earnings/short show real data |
| **Day 2** | #4 (no_data for 20 fake services) | No more misleading random numbers |
| **Day 3** | #6 (entity graph to DB) | Graph persists across restarts |
| **Day 4** | #7 (FRED), #8 (insider from SEC), #10 (Alembic) | Economics + insider activity real |
| **Day 5** | #9 (M&A news), #12 (scheduler), #15 (NoData UI) | Automated refresh, honest UI |
| **Day 6-7** | #11 (auth), #13 (graph scheduler), #14 (PostgreSQL) | Production-capable |

---

## What NOT to do (time traps)

- **Don't try to make narrative model real** — needs GPU training infrastructure. Mark as "Coming Soon" and move on.
- **Don't implement real Plaid brokerage sync** — needs Plaid contract + compliance. Kill it or mark future.
- **Don't build the Reddit whale feature** — needs Reddit API approval. Kill or mark future.
- **Don't build real PWA push notifications** — low value. Kill.
- **Don't build global equity from scratch** — just wire yfinance for international tickers (it already supports them).

---

## After This Sprint

```
Revised completion:
Overall:                   ~70-75%
Frontend:                  ~65% (honest states, real data rendering)
Backend:                   ~70% (real services, persisted state)
Core product:              ~70% (graph + gov trading + earnings + SEC + macro)
External integrations:     ~60% (key ones working, others honestly marked unavailable)
Production readiness:      ~40% (auth, migrations, PG — still needs monitoring/CI)
```

The remaining 20-30% to get to production:
- CI/CD pipeline
- Monitoring/alerting (Sentry, metrics)
- Rate limiting on endpoints
- User management UI
- Proper deployment (Docker/ECS)
- Load testing
- Security audit

---

**TL;DR: The fastest ROI is Days 1-2 above.** Wire yfinance + complete the partially-real services + enforce `no_data_response` everywhere else. That alone takes you from "actively misleading" to "honest about what it can do" — which is the difference between a 25% product and a 45% product overnight.











INFRASTRUCTURE AUDIT REPORT:


## Comprehensive Infrastructure Audit Report

---

### 1. DATABASE / PERSISTENCE LAYER

**Configuration:** SQLAlchemy with connection pooling, defaults to `sqlite:///./local.db`, supports PostgreSQL via `DATABASE_URL` env var.

**Models defined** in `apps/api/app/models/models.py`:
- `Organization`, `Workspace`, `User`, `Role`, `Permission`, `RolePermission`, `Membership`, `Project`, `Case`, `Invitation`, `AuditLog`

These are proper SQLAlchemy ORM models with foreign keys and relationships — designed for multi-tenancy & RBAC.

**Is it actually used by services?** **No.** A grep for `get_db`, `SessionLocal`, and `from app.db` across `apps/api/app/services/` returned **zero matches**. The DB session is only injected at the **API route layer** (`apps/api/app/api/*.py` — 30+ files). Services (earnings, short interest, politician leaderboard, IPO calendar, etc.) operate purely on in-memory data fetched live from external APIs.

**Migrations?** None. No Alembic, no migration folders exist. Tables would only be created via `Base.metadata.create_all(engine)` (manual). This means the schema is never version-controlled.

**Verdict:** The database powers the multi-tenant RBAC/user management layer exposed by API routes. The core financial intelligence services are **entirely stateless** — they fetch data from external APIs on every request with in-memory TTL caches.

---

### 2. EXTERNAL INTEGRATIONS (Connector-by-Connector)

| Connector | Real HTTP Calls? | API Key Required? | Error/Rate Handling | Called from Services? |
|---|---|---|---|---|
| `finnhub_earnings_connector.py` | Yes — `requests.get` to `finnhub.io/api/v1` | `FINNHUB_API_KEY` | Graceful `None` return, 5-min TTL cache | Yes (earnings_calendar_service) |
| `finra_short_interest_connector.py` | Yes — `requests.post` to `api.finra.org` | **None** (free public API) | Graceful `None`, yfinance fallback, 15-min cache | Yes (short_interest_service) |
| `sec_edgar_connector.py` | Yes — `requests.get` to `data.sec.gov`, `efts.sec.gov`, `www.sec.gov` | **None** (SEC_USER_AGENT recommended) | Rate limiting (0.1s between calls), retries (3 attempts), disk-cached ticker map | Yes (multiple intelligence services) |
| `gov_trading_connector.py` | Yes — House Clerk ZIP, Senate GitHub JSON, CongressInvests API, Congress.gov API, SEC EDGAR | `CONGRESS_API_KEY` (optional, improves limits) | Module-level TTL caches (2h-4h), graceful empty lists | Yes (politician_leaderboard_service) |
| `financial_news_connector.py` | Yes — Finnhub, FMP, Alpha Vantage, FRED, NewsAPI, Guardian, NYT, GDELT, UK Companies House, ALEPH/OCCRP | 9 separate keys | Graceful `{}` / `[]` when key missing, 12s timeout | Yes (multiple services) |
| `private_company_connector.py` | Yes — OpenCorporates, GLEIF, FinCEN, FDIC, UK Companies House, SEC Form D | `OPENCORPORATES_API_TOKEN`, `UK_COMPANIES_HOUSE_KEY` (optional) | Graceful empty returns, 15s timeouts | Yes (deep intelligence) |
| `fmp_ipo_connector.py` | Yes — `requests.get` to `financialmodelingprep.com/api/v3` | `FMP_API_KEY` | Graceful `None`, 30-min cache | Yes (ipo_calendar_service) |
| `opensecrets_connector.py` | Yes — FEC API (`api.open.fec.gov/v1`), LDA Senate (`lda.gov/api/v1`) | `FEC_API_KEY`, `LDA_API_KEY`, `OPENSECRETS_API_KEY` (deprecated) | Circuit breaker for LDA, retry with backoff, host failover | Yes (political intelligence) |
| `linkedin_deep_connector.py` | Yes — Apify cloud actors (`api.apify.com/v2`) | `APIFY_API_TOKEN` | Async polling with timeout, graceful empty on missing token | Yes (deep personnel research) |

**Every single connector makes real HTTP calls.** None return synthetic/mock data. When API keys are missing or calls fail, they return empty results — never fabricated data.

---

### 3. CORE SETTINGS & ENV VARS

**`settings.py`** exposes 4 settings via Pydantic:
- `database_url` (default: `sqlite:///./local.db`)
- `jwt_secret` (default: `dev-secret-change`)
- `jwt_issuer` (default: `identity-api`)
- `env` (default: `local`)

**Critical env vars** (from `.env.example` and connector code):

| Priority | Variable | Used By |
|---|---|---|
| HIGH | `FINNHUB_API_KEY` | Earnings, quotes, news, IPO data |
| HIGH | `FMP_API_KEY` | IPO calendar, financials, M-Score, Z-Score |
| HIGH | `FRED_API_KEY` | Macro economic data dashboard |
| MEDIUM | `APIFY_API_TOKEN` | LinkedIn deep research |
| MEDIUM | `CONGRESS_API_KEY` | Congressional legislation (1000 req/hr vs 30) |
| MEDIUM | `FEC_API_KEY` | Political PAC contributions |
| MEDIUM | `LDA_API_KEY` | Lobbying data (prevents 403 throttling) |
| LOW | `NEWSAPI_KEY`, `GUARDIAN_API_KEY`, `NYT_KEY` | News aggregation |
| LOW | `UK_COMPANIES_HOUSE_KEY` | UK private company research |
| LOW | `OPENCORPORATES_API_TOKEN` | Global company registry |
| INFRA | `DATABASE_URL` | DB connection |
| INFRA | `JWT_SECRET` | Auth tokens |

**`no_data.py` — The "Mock Ban Contract":**
This is a project-wide policy enforcer. It provides standardized "no data available" responses with typed reasons (`API_UNAVAILABLE`, `API_KEY_MISSING`, `ENTITY_NOT_FOUND`, etc.). The file explicitly **bans** `import random`, `import faker`, and any `_generate_mock_*` functions. Services must return these structured no-data responses instead of ever fabricating synthetic data.

---

### 4. SMOKE TEST ANALYSIS

**What it actually tests:**
The smoke test (`apps/api/app/scripts/smoke_test.py`) exercises **12 real service/connector calls**:

1. `politician_leaderboard_service.get_statistics()` — asserts `total_politicians > 0`
2. `earnings_calendar_service.get_upcoming_earnings()` — calls Finnhub API
3. `short_interest_service.get_short_interest("AAPL")` — calls FINRA + yfinance
4. `ipo_calendar_service.get_upcoming_ipos()` — calls FMP API
5. `gov_trading_connector.get_recent_congress_trades()` — fetches House Clerk ZIP + CongressInvests
6. `politician_leaderboard_service.get_leaderboard_by_trades()` — asserts non-empty
7. `politician_leaderboard_service.get_leaderboard_by_volume()` — real aggregation
8. `politician_leaderboard_service.get_notable_cases()` — real data
9. `sec_edgar_connector.get_filer_cik("AAPL")` — real SEC lookup
10. `financial_news_connector.finnhub_quote("AAPL")` — real Finnhub quote
11. `quality.classifier.get_classifier()` — checks ML model loads
12. `rag.retriever.retrieve` — checks function is importable

**Verdict:** This is a **real integration test**, not a superficial import check. It makes live HTTP calls, measures latency, and distinguishes between PASS (data returned), FAIL (exception thrown), and NO_DATA (API responded but empty). Results are saved to `smoke_test_results.json`. It's designed as a "demo path lock" — ensuring the critical demo routes remain functional.












BACKEND SERVICE AGENT:

Here is my structured analysis of all 15 service files:

---

## Service Classification Summary

| # | Service | Classification | External API | Real DB | Real Logic |
|---|---------|---------------|-------------|---------|-----------|
| 1 | `portfolio_service.py` | **FAKE** | None | None | Simulated |
| 2 | `brokerage_sync_service.py` | **FAKE** | None | None | Simulated |
| 3 | `narrative_model_service.py` | **FAKE** | None | None | Simulated |
| 4 | `autonomous_agent_service.py` | **FAKE** | None | None | Simulated |
| 5 | `global_equity_service.py` | **FAKE** | None | None | Simulated |
| 6 | `mobile_pwa_service.py` | **FAKE** | None | None | Simulated |
| 7 | `litigation_service.py` | **REAL** | Yes (connectors) | None (connector-backed) | Real |
| 8 | `reddit_whale_service.py` | **FAKE** | None | None | Simulated |
| 9 | `benchmark_service.py` | **FAKE** | None | None | Simulated |
| 10 | `workspace_service.py` | **FAKE** | None | None | Simulated |
| 11 | `cost_basis_service.py` | **FAKE** | None | None | Simulated |
| 12 | `politician_leaderboard_service.py` | **REAL** | File-based (parsed JSON) | JSON file store | Real |
| 13 | `ipo_calendar_service.py` | **REAL** | Yes (Finnhub, FMP) | None | Real |
| 14 | `earnings_calendar_service.py` | **PARTIALLY_REAL** | Yes (Finnhub) | None | Mock fallback |
| 15 | `short_interest_service.py` | **PARTIALLY_REAL** | Yes (FINRA) | None | Mock fallback |

---

## Detailed File-by-File Report

### 1. `portfolio_service.py` — **FAKE**
- **External APIs:** None. Line 200 comment: `"simulated for demo"`. Uses `hashlib.md5` to generate deterministic fake prices.
- **Database:** None. No persistence.
- **Business logic:** Math is valid (P&L, sector allocation, weights) but operates on fabricated inputs. Risk metrics (line 558-568) use `random.uniform()` to produce drawdown/volatility.
- **Red flags:** `_SECTOR_MAP` hardcoded, `_BETA_MAP` hardcoded, `_PRICE_HISTORY` hardcoded, `random.uniform` for risk values.
- **Production-ready:** No.

### 2. `brokerage_sync_service.py` — **FAKE**
- **External APIs:** None. Fake Plaid URL string on line 39 (`https://api.plaid.com/link?token=`), never actually called.
- **Database:** `LINKED_ACCOUNTS: Dict[str, List[Dict]] = {}` — in-memory dict, resets on restart.
- **Business logic:** Fully simulated. `sync_account()` returns `random.randint(5, 20)` for positions synced. `get_account_positions()` returns 3 hardcoded positions.
- **Red flags:** All functions return canned data. No actual OAuth flow.
- **Production-ready:** No.

### 3. `narrative_model_service.py` — **FAKE**
- **External APIs:** None. No LLM calls, no GPU, no training infrastructure.
- **Database:** `TRAINING_JOBS: Dict[str, Dict] = {}` — in-memory.
- **Business logic:** `get_training_status()` uses `random.choice(["queued", "running", "completed"])`. `generate_narrative()` returns hardcoded template strings.
- **Red flags:** Model registry is static dict. Training metrics are `random.uniform()`. No actual model inference.
- **Production-ready:** No.

### 4. `autonomous_agent_service.py` — **FAKE**
- **External APIs:** None. No SEC filing access, no web scraping.
- **Database:** `DISCOVERED_ENTITIES` — hardcoded dict with NVDA/AAPL data.
- **Business logic:** `discover_subsidiaries()` generates random subsidiary names like `"{ticker} Subsidiary {i}"`. `get_job_status()` uses `random.choice()`.
- **Red flags:** Entity discovery generates `f"Portfolio Company {i}"`, `f"Director {i}"`. No real data source.
- **Production-ready:** No.

### 5. `global_equity_service.py` — **FAKE**
- **External APIs:** None. No market data API calls.
- **Database:** None.
- **Business logic:** `get_global_quote()` uses `hash(ticker) % 500` + `random.uniform`. Market status is `random.choice(["open", "closed"...])`. Currency rates are hardcoded.
- **Red flags:** 8 stocks hardcoded in `GLOBAL_STOCKS`. All prices/volumes are random.
- **Production-ready:** No.

### 6. `mobile_pwa_service.py` — **FAKE**
- **External APIs:** None. `send_push_notification()` just returns `{"status": "sent"}` without actually sending.
- **Database:** `SUBSCRIPTIONS: Dict = {}`, `NOTIFICATION_PREFERENCES: Dict = {}` — in-memory.
- **Business logic:** PWA manifest and config are valid JSON structures, but push notifications are not implemented.
- **Red flags:** No Web Push library (pywebpush), no VAPID keys, no actual push delivery.
- **Production-ready:** No.

### 7. `litigation_service.py` — **REAL**
- **External APIs:** Yes. Imports and calls `app.connectors.litigation_connector` (SEC, FTC, DOJ), `app.connectors.market_data_connector`, `app.services.docket_disclosure_service`. These are real connector calls to SEC EDGAR, FTC, DOJ, and CourtListener.
- **Database:** None directly, relies on connectors.
- **Business logic:** Real event study calculation (lines 413-483), real docket velocity calculation with date parsing and period filtering, real normalized exposure against actual fundamentals, proper risk classification logic.
- **Red flags:** Some `None` return values when data unavailable (lines 401-410), graceful degradation pattern. No hardcoded mock data anywhere.
- **Production-ready:** Yes (depends on connector availability).

### 8. `reddit_whale_service.py` — **FAKE**
- **External APIs:** None. No Reddit API (PRAW), no SEC EDGAR for Form 4/13F.
- **Database:** None.
- **Business logic:** `MOCK_POSTS` (5 hardcoded Reddit posts), `MOCK_WHALE_TXS` (6 hardcoded transactions). `get_sentiment_history()` generates 30 days of `random.uniform()`. `get_whale_flow()` uses `random.randint(0, 50000000)`.
- **Red flags:** Literally named `MOCK_POSTS`, `MOCK_WHALE_TXS`. All data is static or random.
- **Production-ready:** No.

### 9. `benchmark_service.py` — **FAKE**
- **External APIs:** None.
- **Database:** None.
- **Business logic:** `BENCHMARKS` dict with hardcoded return values. `MOCK_PORTFOLIO_RETURNS` with hardcoded user data. `get_historical_comparison()` generates data with `random.uniform(-5, 8)`. Attribution math is valid but on fake inputs.
- **Red flags:** Line 39 says `"# Mock benchmark data"`. `get_risk_contribution()` has comment `"# Mock risk contribution data"`. All historical data is generated with `random`.
- **Production-ready:** No.

### 10. `workspace_service.py` — **FAKE**
- **External APIs:** None.
- **Database:** `WORKSPACES: Dict[str, Workspace] = {}` — in-memory dict with 2 hardcoded workspaces.
- **Business logic:** CRUD logic is correct (create, add/remove members, role checks). But no persistence.
- **Red flags:** Hardcoded `"demo@example.com"`, `"analyst@example.com"`. Activity feed is hardcoded list. All data lost on restart.
- **Production-ready:** No.

### 11. `cost_basis_service.py` — **FAKE**
- **External APIs:** None.
- **Database:** `MOCK_POSITIONS: Dict[str, List[Position]] = {}` — in-memory with 12 hardcoded lots.
- **Business logic:** FIFO/LIFO/Average cost basis calculation logic is mathematically correct. Tax lot comparison works. But operates on hardcoded data.
- **Red flags:** Named `MOCK_POSITIONS`. Prices are static (never fetched). No real brokerage integration.
- **Production-ready:** No (logic is valid but data layer is fake).

### 12. `politician_leaderboard_service.py` — **REAL**
- **External APIs:** Reads from `apps/api/app/data/gov_trading/gov_trading_rankings.json` — real parsed data from Excel spreadsheet (Capitol Trades, Kapitol.ai, etc.).
- **Database:** JSON file persistence (parsed from actual government trading disclosure data).
- **Business logic:** Real search, ranking, filtering. Robust `_safe_float`/`_safe_int`/`_safe_str` handlers for messy data. No `random` anywhere.
- **Red flags:** None. Legitimate data pipeline output.
- **Production-ready:** Yes.

### 13. `ipo_calendar_service.py` — **REAL**
- **External APIs:** Yes. Imports `finnhub_ipo_calendar` and `fmp_ipo_connector` (Finnhub primary, FMP fallback). Explicitly states `"NO MOCK DATA"` and `"S0-C Mock Ban"`.
- **Database:** None.
- **Business logic:** Real API calls with proper error handling and fallback logic. Returns empty lists when data unavailable (not fake data).
- **Red flags:** None. Clean implementation following no-mock contract.
- **Production-ready:** Yes.

### 14. `earnings_calendar_service.py` — **PARTIALLY_REAL**
- **External APIs:** Yes. Imports `finnhub_earnings_connector` functions. `USE_REAL_DATA = True`.
- **Database:** None.
- **Business logic:** `get_upcoming_earnings()` tries Finnhub first, falls back to `_generate_mock_earnings()` with `random`. Other functions (`get_earnings_by_date`, `get_ticker_earnings_history`, `get_earnings_surprises`) only use mock data.
- **Red flags:** Most functions still return random mock data. Only `get_upcoming_earnings()` actually uses the real connector.
- **Production-ready:** Partially. Main listing endpoint works; detail/history endpoints are fake.

### 15. `short_interest_service.py` — **PARTIALLY_REAL**
- **External APIs:** Yes. Imports `finra_short_interest_connector` functions. `USE_REAL_DATA = True`.
- **Database:** None.
- **Business logic:** `get_short_interest()` and `get_most_shorted()` try FINRA first, fall back to mock. `get_short_interest_history()`, `get_short_squeeze_candidates()`, `get_short_changes()` only use mock data (`random`).
- **Red flags:** Squeeze indicators, history, and sector summary are fully simulated. Only 2 of 7 functions use real data.
- **Production-ready:** Partially. Core data works; analytics features are fake.

---

## Files Found:
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/portfolio_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/brokerage_sync_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/narrative_model_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/autonomous_agent_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/global_equity_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/mobile_pwa_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/litigation_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/reddit_whale_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/benchmark_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/workspace_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/cost_basis_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/politician_leaderboard_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/ipo_calendar_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/earnings_calendar_service.py`
- `/Users/anshumanparmar/Developer/Professional/OneTouch/Finance-Advanced-Research-Platform/apps/api/app/services/short_interest_service.py`




FRONTEND WIRING DOC:


Here is the structured report:

---

## Frontend Page Wiring Report

### API Client (`apps/web/lib/api.js`)

The shared API client is minimal — it only exports `getApiBaseUrl()` and `getAdminBaseUrl()`. It does **not** export a `fetch` wrapper or any endpoint-specific functions. Most pages define their own `const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'` inline instead of using this helper.

**Pages that DO import `lib/api.js`:** `gov-trading-leaderboard.js`, `earnings-calendar.js`
**Pages that define their own `API_BASE` constant:** All other 13 pages.

---

### Navigation (`Layout.js`) — Linked Pages

Pages from our list that ARE linked in the sidebar navigation:

| Nav Link | Page |
|---|---|
| `/portfolios` | portfolios.js |
| `/portfolio-analytics` | portfolio-analytics.js |
| `/recursive-discovery` | recursive-discovery.js |
| `/gov-trading-leaderboard` | gov-trading-leaderboard.js |
| `/insider-activity` | insider-activity.js |
| `/earnings-calendar` | earnings-calendar.js |
| `/ipo-calendar` | ipo-calendar.js |

Pages from our list that are **NOT** linked in navigation:
- `/brokerage`
- `/global-markets`
- `/entity-discovery`
- `/narrative-model`
- `/social`
- `/benchmark`
- `/workspaces`
- `/network-graph`

---

### Per-Page Classification

| # | Page | Classification | API Endpoints Called | Uses `lib/api.js`? | Loading/Error States | In Nav? |
|---|------|---------------|---------------------|-------------------|---------------------|---------|
| 1 | `portfolios.js` | **WIRED_TO_API** | `GET /portfolio`, `GET /portfolio/{id}`, `GET /portfolio/{id}/pnl`, `POST /portfolio`, `POST /portfolio/{id}/positions` | No (own `API_BASE`) | Loading state only, error to console | Yes |
| 2 | `brokerage.js` | **WIRED_TO_API** | `GET /brokerage/brokers`, `GET /brokerage/accounts`, `GET /brokerage/sync-status`, `POST /brokerage/link/initiate`, `POST /brokerage/link/complete`, `GET /brokerage/accounts/{id}/positions`, `GET /brokerage/accounts/{id}/transactions`, `POST /brokerage/accounts/{id}/sync`, `DELETE /brokerage/accounts/{id}` | No (own `API_BASE`) | Loading state only | **No** |
| 3 | `global-markets.js` | **WIRED_TO_API** | `GET /global/markets/status`, `GET /global/indices`, `GET /global/search`, `GET /global/quote/{ticker}` | No (own `API_BASE`) | Loading state only | **No** |
| 4 | `entity-discovery.js` | **WIRED_TO_API** | `POST /agent/discover`, `GET /agent/entities/{t}`, `GET /agent/graph/{t}`, `GET /agent/family-tree/{t}`, `GET /agent/subsidiaries/{t}`, `GET /agent/investments/{t}`, `GET /agent/board-connections/{t}` | No (own `API_BASE`) | Loading state only | **No** |
| 5 | `recursive-discovery.js` | **WIRED_TO_API** | `GET /recursive/graph/{t}`, `GET /recursive/clusters/{t}`, `GET /recursive/circular/{t}`, `GET /recursive/chain/{t}`, `GET /recursive/compare` | No (own `API_BASE`) | Loading state only | Yes |
| 6 | `narrative-model.js` | **WIRED_TO_API** | `GET /narrative-model/models`, `GET /narrative-model/datasets`, `GET /narrative-model/performance`, `POST /narrative-model/train`, `POST /narrative-model/generate` | No (own `API_BASE`) | Loading state only | **No** |
| 7 | `portfolio-analytics.js` | **WIRED_TO_API** | `GET /portfolio-analytics/{endpoint}` (10 sub-endpoints: factor-decomposition, rebalancing, model-portfolios, risk-parity, scenario-analysis, drawdown, correlation-matrix, sector-rotation, factor-timing, performance-attribution) | No (own `API_BASE`) | Loading state only | Yes |
| 8 | `social.js` | **WIRED_TO_API** | `GET /social/reddit/trending`, `GET /social/reddit/sentiment`, `GET /social/whales/flow/{ticker}`, `GET /social/momentum/{ticker}`, `GET /social/institutional/{ticker}` | No (own `API_BASE`) | Loading state only | **No** |
| 9 | `benchmark.js` | **WIRED_TO_API** | `GET /benchmark/available`, `GET /benchmark/compare`, `GET /benchmark/sector-attribution` | No (own `API_BASE`) | Loading state only | **No** |
| 10 | `workspaces.js` | **WIRED_TO_API** | `GET /workspaces/`, `GET /workspaces/{id}`, `GET /workspaces/{id}/activity`, `POST /workspaces/` | No (own `API_BASE`) | Loading state only | **No** |
| 11 | `gov-trading-leaderboard.js` | **WIRED_TO_API** | `GET /market/gov-trading/leaderboard/{tab}`, `GET /market/gov-trading/leaderboard/statistics`, `GET /market/gov-trading/leaderboard/rank/{name}` | **Yes** (`getApiBaseUrl`) | Loading + Error state (displays `err`) | Yes |
| 12 | `earnings-calendar.js` | **WIRED_TO_API** | `GET /earnings/stats`, `GET /earnings/upcoming`, `GET /earnings/week`, `GET /earnings/surprises`, `GET /earnings/ticker/{ticker}` | **Yes** (`getApiBaseUrl`) | Loading + Error state (displays `err`) | Yes |
| 13 | `ipo-calendar.js` | **WIRED_TO_API** | `GET /ipo/stats`, `GET /ipo/upcoming`, `GET /ipo/recent`, `GET /ipo/lockups`, `GET /ipo/week`, `GET /ipo/performance`, `GET /ipo/ticker/{ticker}` | No (own `API_BASE`) | Loading state only | Yes |
| 14 | `insider-activity.js` | **WIRED_TO_API** | `GET /insider/stats`, `GET /insider/screen`, `GET /insider/cluster-buys`, `GET /insider/cluster-sells`, `GET /insider/largest`, `GET /insider/ceo-cfo`, `GET /insider/sentiment/{ticker}` | No (own `API_BASE`) | Loading state only | Yes |
| 15 | `network-graph.js` | **WIRED_TO_API** | `GET /intelligence/graph/stats`, `POST /intelligence/graph/paypal-mafia/load`, `GET /intelligence/graph/explore/{id}`, `GET /intelligence/graph/paypal-mafia/explore`, `GET /intelligence/graph/connect` | No (own `API_BASE`) | Loading state, alerts on error | **No** |

---

### Summary

**Classification counts:**
- **WIRED_TO_API: 15/15** — Every single page makes real `fetch()` calls to backend endpoints with dynamic data rendering.
- **PARTIALLY_WIRED: 0**
- **STATIC_ONLY: 0**
- **BROKEN: 0**

**Key findings:**

1. All 15 pages are fully wired to backend APIs — no hardcoded/static data anywhere.
2. Only 2 pages (`gov-trading-leaderboard.js`, `earnings-calendar.js`) use the shared `lib/api.js` helper. The other 13 redundantly define `const API_BASE` locally.
3. Only `gov-trading-leaderboard.js` and `earnings-calendar.js` display error messages to users. The rest silently `console.error` on failure — the user sees only the loading state stuck or empty content.
4. 8 of the 15 pages are not reachable from the sidebar navigation (they exist as pages but require direct URL access).
5. `ipo-calendar.js` and `insider-activity.js` wrap themselves in `<Layout>` directly, while the others rely on `_app.js` or have no layout wrapper.
















Based on the conversation summary, I completed a comprehensive independent
   technical audit of the Finance Platform. Here's a summary of what was    
  accomplished:                                                             
                                                                            
  Audit Complete                                                            
                                                                            
  Key Finding: Verified completion is 35-40%, not 90-95% as previously      
  claimed.                                                                  
                                                                            
  Critical Issues Identified                                                
  Issue: 24 services use random.uniform() for all data                      
  Impact: Portfolio analytics (D1-D11) returns meaningless numbers          
  ────────────────────────────────────────                                  
  Issue: Portfolio prices use MD5 hash, not market data                     
  Impact: Valuations are completely fake                                    
  ────────────────────────────────────────                                  
  Issue: Zero database migrations exist                                     
  Impact: Cannot deploy or rollback reliably                                
  ────────────────────────────────────────                                  
  Issue: 381 mock/random references in services                             
  Impact: Data quality is unreliable                                        
  What's Actually Working (Real Data)                                       
                                                                            
  - Politician Leaderboard - 633 politicians from parsed Excel              
  - Government Trading - Real SEC Form 4 data                               
  - Earnings Calendar - Live Finnhub data                                   
  - Short Interest - Live FINRA data                                        
  - IPO Calendar - Live Finnhub data                                        
  - SEC Filings - Real SEC EDGAR API                                        
  - Company Deep Reports - Real SEC EDGAR data                              
                                                                            
  P0 Fixes Required (in order)                                              
                                                                            
  1. Replace fake portfolio prices - portfolio_service.py uses MD5 hash     
  instead of real market data                                               
  2. Replace fake analytics - portfolio_analytics_service.py uses           
  random.uniform() for all D1-D11 features                                  
  3. Replace consensus/estimates mock data - consensus_service.py,          
  whisper_estimates_service.py, guidance_service.py                         
  4. Add database migrations - Zero migrations exist for 75 models          
                                                                            
  The audit findings are now documented in MASTER_TASK_STATUS.md with the   
  full breakdown of fake vs real services, connector status, and recommended
   fix order. The document serves as the source of truth for actual project 
  completion rather than claimed completion.                                
                                           