# Product Features Documentation

**Platform:** Finance Advanced Research Platform  
**Document type:** Feature inventory — pages, APIs, schemas, dependencies, implementation status  
**Status baseline:** Independent audits 23–26 Aug 2026 + `MASTER_TASK_STATUS.md` (status-checked 26 Oct 2026)  
**Honest platform completion:** ~45% (weighted; do not use inflated commit-message %)  
**Pending work / path to 100%:** [`PENDING_TASKS_COMPLETION_PLAN.md`](./PENDING_TASKS_COMPLETION_PLAN.md) (task IDs per feature)

---

## How to read this document

### Status labels

| Label | Meaning |
|-------|---------|
| **IMPLEMENTED** | Page/route/file exists and is reachable |
| **PARTIAL** | Exists but incomplete, unstable, key-gated, or poorly wired |
| **STUB** | Registered but returns `no_data_response` / “not available” |
| **MISSING** | Required for the feature but not present |
| **BROKEN** | Implemented but confirmed failing (e.g. prod graph insert) |

### Percentage columns (per feature)

| Column | Meaning |
|--------|---------|
| **Page %** | Frontend page(s) exist and render |
| **API %** | Routes registered and return real data or honest no-data (not silent fake) |
| **Schema %** | DB models / Pydantic schemas needed for the feature exist |
| **Wiring %** | UI calls live API with auth when required; E2E usable |
| **Overall %** | Audit-aligned product completion for this feature (not file count) |

Scores prefer audit/`MASTER_TASK_STATUS` verified figures over README “complete” claims.

### Environment keys referenced

`DATABASE_URL`, `JWT_SECRET`, `FINNHUB_API_KEY`, `FRED_API_KEY`, `SEC_USER_AGENT`, `FMP_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `APOLLO_API_KEY`, `CONGRESS_API_KEY`, `FEC_API_KEY`, `SENDGRID_API_KEY`, `TWILIO_*`, `REDIS_URL`, `NEWSAPI_KEY`, and others in root `.env.example`.

---

## Executive summary

| Area | Overall | Notes |
|------|---------|-------|
| Auth & workspaces | ~90% / ~60% | Login + JWT work; workspaces/RBAC schema exists, usage uneven |
| Gov trading | ~85% | Live leaderboard + PTR feeds |
| Stock / market data | ~80% | yfinance + Finnhub; keys required for some paths |
| Intelligence reports | ~50–55% | Generates; fresh-DB / stability issues |
| Entity graph | ~50% | Schema + services; **prod insert bug** (`canonical` bool vs int) |
| Portfolio / alerts | ~65–70% | Real prices; auth/wiring gaps |
| Earnings / IPO / short / insider | ~85–90% | Verified with live APIs |
| RAG chat | ~75% | Hybrid search present |
| Quality gates | ~85% locally claimed; **prod classifier often not_trained** |
| Brokerage / narrative AI / PWA advanced | **0–25%** | Stubs |
| Platform weighted total | **~45%** | Per REQ matrix |

---

# Feature catalog

---

## 1. User Authentication (REQ-001)

**Purpose:** Register, login, JWT session, identity for protected writes.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/login` → `apps/web/pages/login.js` |
| **Client libs** | IMPLEMENTED | `apps/web/lib/auth.js`, `apps/web/lib/api.js` (Bearer from `localStorage`) |
| **APIs** | IMPLEMENTED | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` (`apps/api/app/api/auth.py`) |
| **Note** | PARTIAL | Legacy routes in `routes.py` may shadow/conflict with JWT auth shapes |
| **Schemas** | IMPLEMENTED | `User`, `AuditLog`; Pydantic `TokenResponse`, `UserResponse` |
| **Other** | JWT secret, bcrypt | `JWT_SECRET` |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 100% | 90% | 95% | 85% | **~90%** |

---

## 2. Workspaces, Teams & RBAC

**Purpose:** Multi-tenant org/workspace membership and permissions.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/workspaces`, `/teams` |
| **APIs** | IMPLEMENTED | `/workspaces/*` (`workspaces.py`), `/teams/*` (`team_permissions.py`) |
| **Schemas** | IMPLEMENTED | `Organization`, `Workspace`, `Role`, `Permission`, `RolePermission`, `Membership`, `Invitation`, `Project`, `Case` |
| **Other** | Auth required for writes | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 80% | 70% | 95% | 50% | **~60%** |

---

## 3. Government Trading Intelligence (REQ-002)

**Purpose:** Politician trades, leaderboards, STOCK Act / PTR disclosures.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/gov-trading`, `/gov-trading-leaderboard`, `/leaderboard`, `/docket` |
| **APIs** | IMPLEMENTED | `/market/gov-trading/*`, `/leaderboard/*`, `/government/*`, `/docket/*` |
| **Data** | IMPLEMENTED | Static JSON (~633–637 officials) + live House/Senate PTR connectors |
| **Schemas** | PARTIAL | Mostly file/JSON + cache; not a dedicated politician ORM set |
| **Other** | Optional `CONGRESS_API_KEY` | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 95% | 90% | 40% | 90% | **~85%** |

---

## 4. Stock Market Data & Analysis (REQ-003)

**Purpose:** Quotes, fundamentals, technicals, company deep dive.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/stock`, `/company`, `/metrics`, `/options`, `/expert-analysis`, `/compare` |
| **APIs** | IMPLEMENTED | `/market/quote`, `/market/yf/*`, `/market/technicals`, `/market/profile`, `/market/metrics`, financial statements, Beneish/Altman, news, OSINT helpers |
| **Connectors** | IMPLEMENTED | `yfinance_connector`, Finnhub, FMP (optional) |
| **Schemas** | N/A / cache | Mostly live API responses; no primary stock ORM |
| **Other** | `FINNHUB_API_KEY`, `FMP_API_KEY`, `SEC_USER_AGENT` | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 95% | 85% | 30% | 80% | **~80%** |

---

## 5. Valuation (DCF, comps, timeline)

**Purpose:** Intrinsic value, scenarios, historical valuation series.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/valuation` |
| **APIs** | IMPLEMENTED / PARTIAL | `/finance/*`, `/valuation/*` (`valuation_timeline.py`); many honest `no_data` fallbacks |
| **Packages** | IMPLEMENTED | `packages/finance` (DCF, comps, technicals) |
| **Schemas** | PARTIAL | Response models in services; limited persistence |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 70% | 40% | 65% | **~65%** |

---

## 6. Intelligence Dossiers & Reports (REQ-004)

**Purpose:** 9-section evidence-first entity dossiers; network reports; exports.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/intelligence`, `/intelligence/[id]`, `/intelligence/network`, `/intelligence/correlation`, `/intelligence/self-dealing`, `/intelligence/contract-probability`, `/intelligence/interactive-report`, `/intelligence/interactive/[reportId]`, `/reports`, `/private-company` |
| **APIs** | IMPLEMENTED | `POST /intelligence/generate`, `generate-enhanced`, `GET /intelligence/{id}`, PDF/Word/Excel/PPT exports, Apollo/private-co enrichment, self-dealing/network/correlation/contract-probability, interactive report |
| **Services** | IMPLEMENTED | `intelligence_service`, activation services, PDF (ReportLab); WeasyPrint paths optional/Windows-fragile |
| **Schemas** | IMPLEMENTED | `Report`, `ReportSection`, `EvidenceBundle`, `Claim`, `ClaimEvidence`, `RawDocument`, `EvidenceRef` |
| **Other** | LLM keys for narrative; may crash on fresh DB (P0) | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 95% | 75% | 90% | 55% | **~50–55%** |

---

## 7. Entity Graph & Relationships (REQ-006)

**Purpose:** People/org graph, evidence-backed edges, recursive discovery (PayPal Mafia style).

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/graph`, `/network-graph`, `/entity-discovery`, `/recursive-discovery`, `/entities/[id]`, `/entities/merge`, `/entity-analysis`, `/persons`, `/timeline` |
| **APIs** | IMPLEMENTED | `/graph/*`, `/entities/*`, `/entities/multi/*`, `/intelligence/graph/*`, `/recursive/*`, `/persons/*`, `/corporate-ownership/*` |
| **Schemas** | IMPLEMENTED | `Entity`, `EntityAlias`, `EntityIdentifier`, `Relationship`, `RelationshipEvidence`, `MergeCandidate`, `MergeAction`, `ResolutionQueue` |
| **Other** | **BROKEN in prod:** `canonical` boolean/integer mismatch on insert (5 Oct 2026) | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 70% | 95% | 40% | **~50%** (capped; prod broken) |

---

## 8. Portfolio Tracking (REQ-005)

**Purpose:** Portfolios, positions, P&L with live prices.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/portfolios`, `/portfolio/[id]`, `/portfolio-analytics`, `/cost-basis`, `/tax-lots`, `/benchmark` |
| **APIs** | IMPLEMENTED | `/portfolio/*`, `/portfolio-analytics/*`, `/cost-basis/*`, `/tax-lots/*`, `/benchmark/*` |
| **Schemas** | IMPLEMENTED | `Portfolio`, `Position` |
| **Other** | yfinance; auth on writes; some pages may bypass auth | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 80% | 85% | 60% | **~65–70%** |

---

## 9. Watchlists, Dashboards & Price Alerts

**Purpose:** Track tickers, dashboards, price/threshold alerts.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/dashboard`, `/alerts`, `/tracking`, `/tracking/alerts`, `/saved` |
| **APIs** | IMPLEMENTED | `/watchlist/*`, `/dashboard/*`, `/alerts/*` (price alerts), `/monitor/*`, `/tracking/*` |
| **Schemas** | IMPLEMENTED | `Watchlist`, `WatchlistItem`, `WatchlistShare`, `Dashboard`, `DashboardWidget`, `AlertRule`, `AlertEvent`, `DeliveryChannel`, `PriceAlertModel`, `AlertNotificationModel`, `InvestmentAlertSeen` |
| **Other** | SendGrid/Twilio for delivery; Redis optional | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 85% | 75% | 95% | 55% | **~65%** |

---

## 10. Trade Alerts — Form 4 / Investment Thresholds (F-03 / F-04)

**Purpose:** Scan big insider trades and watchlist investment thresholds; notify.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/tracking`, `/tracking/alerts`, `/insider-activity` |
| **APIs** | IMPLEMENTED | `/tracking/scan/*`, `/insider/*` |
| **Schemas** | IMPLEMENTED | `WatchlistItem` threshold fields, `InvestmentAlertSeen`, alert tables |
| **Other** | PM2 cron (staging), `SENDGRID_*`, `TWILIO_*`, `SEC_USER_AGENT` | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 85% | 80% | 90% | 60% | **~70%** |

---

## 11. Institutional Holdings & 13F Position-Diff

**Purpose:** 13F holders, quarter-over-quarter position changes.

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/institutional`, `/position-diff`, `/institutional/position-diff` |
| **APIs** | IMPLEMENTED | `/market/institutional/*`, `/market/13f/*` (and related market routes) |
| **Schemas** | IMPLEMENTED | `Institutional13FPeriodCache`, `Institutional13FSupplementalAmendmentCache`, `Institutional13FPositionCache`; Pydantic in `market_13f_schemas.py` (`PositionDiffRequest`, `PositionDiffResponse`, …) |
| **Other** | SEC EDGAR | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 85% | 95% | 80% | **~85%** |

---

## 12. Earnings Calendar (REQ-007)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/earnings-calendar`, `/calendar` |
| **APIs** | IMPLEMENTED | `/earnings/*` |
| **Schemas** | Live API | Finnhub payloads |
| **Other** | `FINNHUB_API_KEY` **required** | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 95% | 95% | 20% | 90% | **~90%** |

---

## 13. IPO Calendar (REQ-008)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/ipo-calendar` |
| **APIs** | IMPLEMENTED | `/ipo/*` |
| **Schemas** | Live API | Finnhub + FMP |
| **Other** | `FINNHUB_API_KEY`, optional `FMP_API_KEY` | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 95% | 95% | 20% | 90% | **~90%** |

---

## 14. Short Interest (REQ-009)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/short-interest` |
| **APIs** | IMPLEMENTED | `/short-interest/*` |
| **Schemas** | Live API | FINRA |
| **Other** | Network to FINRA | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 95% | 90% | 20% | 85% | **~85%** |

---

## 15. Insider Activity (REQ-010)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/insider-activity` |
| **APIs** | IMPLEMENTED | `/insider/*`, `/market/insider-transactions` |
| **Schemas** | Live / filing | SEC Form 4 |
| **Other** | `SEC_USER_AGENT` | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 95% | 95% | 25% | 90% | **~90%** |

---

## 16. Macro / Economics (FRED)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/economics`, `/macro-dashboard` |
| **APIs** | IMPLEMENTED | `/market/macro/*`, `/market/fred/*` |
| **Schemas** | Live API | FRED / BEA |
| **Other** | `FRED_API_KEY` **required** (400 without key) | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 80% | 20% | 70% | **~70%** (key-gated) |

---

## 17. Consensus, Guidance & Analysts

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/consensus`, `/guidance`, `/analysts`, `/analyst/[id]`, `/revisions` |
| **APIs** | PARTIAL | `/consensus/*`, `/guidance/*`, `/analysts/*`, `/revisions/*` — revisions historically import-broken |
| **Schemas** | Live API | Finnhub |
| **Other** | `FINNHUB_API_KEY` | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 70% | 25% | 60% | **~60–70%** |

---

## 18. Volume, Volatility, Formula, Visualizations

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/volume`, `/options` (IV), `/formula`, `/visualizations`, `/bubble-charts`, `/filing-compare` |
| **APIs** | IMPLEMENTED / PARTIAL | `/volume/*`, `/volatility/*`, `/formula/*`, `/visualizations/*`, `/bubble-charts/*`, `/filings/*` |
| **Schemas** | Live | yfinance / calculated |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 85% | 75% | 20% | 70% | **~70%** |

---

## 19. Crypto

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/crypto` |
| **APIs** | IMPLEMENTED | `/market/crypto/*` (via market connector routes) |
| **Schemas** | Live | CoinGecko / Etherscan |
| **Other** | Client priority: **low** | Optional `COINGECKO_API_KEY`, `ETHERSCAN_API_KEY` |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 70% | 15% | 65% | **~65%** |

---

## 20. Registry & Company Search (50-state + global)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/registry`, `/search`, `/private-company` |
| **APIs** | IMPLEMENTED | `/registry/*`, `/search/*`, `/searchos/*`, `/intelligence/private-co/*` |
| **Schemas** | IMPLEMENTED | `RegistryApiKey`, `RegistryApiUsage`; entity tables for resolution |
| **Other** | State connectors in `packages/connectors`; OpenCorporates/GLEIF keys optional | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 75% | 80% | 65% | **~70%** |

---

## 21. RAG Chat (REQ-016)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/chat` |
| **APIs** | IMPLEMENTED | `/chat/*`, `/health/rag`, documents/ingest related |
| **Services** | IMPLEMENTED | `app/services/rag/*` (embeddings, vector, hybrid, rerank) |
| **Schemas** | PARTIAL | Uses documents/evidence; vector often file/numpy store |
| **Other** | `OPENAI_API_KEY` for embeddings | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 85% | 50% | 75% | **~75%** |

---

## 22. Quality Gates (REQ-017)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | PARTIAL | Embedded in intelligence/report flows; `/status` may surface health |
| **APIs** | IMPLEMENTED | Quality on report jobs; `/health/*` |
| **Services** | IMPLEMENTED | `app/services/quality/*` (judge, classifier, decision, synthetic) |
| **Schemas** | Training artifacts | Model files / label logs (not full ORM) |
| **Other** | Staging often `quality_classifier: not_trained` (5 Oct 2026) | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 40% | 85% | 60% | 50% | **~85% code / ~40% prod** |

---

## 23. Review, Comments & Annotations

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/review`, `/review/[id]`, `/comments`, `/evidence` |
| **APIs** | IMPLEMENTED | `/review/*`, `/comments/*`, `/annotations/*`, `/evidence/*` |
| **Schemas** | IMPLEMENTED | `Comment` (report), `Suggestion`, `SectionVersion`, `ReviewerAssignment`, `ReviewTask`, `EntityComment`, `CommentReaction`, `Annotation`, `EvidenceRef`, `RawDocument` |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 85% | 75% | 95% | 50% | **~55%** |

---

## 24. Litigation, Legal, Compliance

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/litigation`, `/compliance` |
| **APIs** | IMPLEMENTED | `/litigation/*`, `/legal/*`, `/compliance/*`, `/compliance/content/*` |
| **Schemas** | IMPLEMENTED | `Policy`, `ExportApproval` |
| **Other** | CourtListener key optional | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 80% | 60% | 70% | 50% | **~55%** |

---

## 25. Sources, Skills, Export, Status

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/sources`, `/skills`, `/status`, `/billing`, `/support`, `/pricing` |
| **APIs** | IMPLEMENTED | `/sources/*`, `/skills/*`, `/export/*`, `/status/*`, `/billing/*`, `/support/*`, `/freshness/*`, `/seo/*`, `/editorial/*`, `/honesty/*`, `/fact-scoring/*` |
| **Schemas** | IMPLEMENTED | Source suite; Skill suite; Policy/ExportApproval |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 80% | 65% | 90% | 45% | **~50%** |

---

## 26. Multi-Entity Comparison (REQ-018)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/compare`, `/entity-analysis` |
| **APIs** | PARTIAL | Multi-entity + intelligence comparative services |
| **Schemas** | Entity / report | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 85% | 65% | 50% | 55% | **~60%** |

---

## 27. M&A Rumors, Whisper, Agent

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/ma-rumors`, `/whisper`, `/agent` |
| **APIs** | PARTIAL | `/ma-rumors/*`, `/whisper/*`, `/agent/*` |
| **Schemas** | Minimal | NewsAPI keys help M&A |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 80% | 50% | 20% | 40% | **~40%** |

---

## 28. Social / Whale Tracking (REQ-014)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/social` |
| **APIs** | STUB / PARTIAL | `/social/*` (`reddit_whale.py`) — Reddit paths stub; institutional yfinance partial |
| **Schemas** | None dedicated | |
| **Other** | Reddit API approval | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 40% | 10% | 30% | **~40%** |

---

## 29. Brokerage Sync (REQ-011) — STUB

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED (dead UI) | `/brokerage` |
| **APIs** | STUB | `/brokerage/*` — all `no_data` (Plaid) |
| **Schemas** | MISSING | No Plaid link tables |
| **Other** | Plaid contract required | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 100% | 0% | 0% | 0% | **0%** |

---

## 30. AI Narrative Model (REQ-012) — STUB

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED (dead UI) | `/narrative-model` |
| **APIs** | STUB | `/narrative-model/*` — GPU required |
| **Schemas** | MISSING | Training infra not in product DB |
| **Other** | RunPod / GPU | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 100% | 0% | 0% | 0% | **0%** |

---

## 31. Mobile / PWA (REQ-013) — STUB / PARTIAL

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/pwa-settings`, `/pwa-advanced` |
| **APIs** | STUB | `/pwa/*`, `/pwa-advanced/*` |
| **Schemas** | MISSING | Push subscription store not productized |
| **Other** | VAPID / Firebase | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 25% | 10% | 15% | **~25%** |

---

## 32. Global Markets

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/global-markets` |
| **APIs** | PARTIAL | `/global/*` |
| **Schemas** | Live | yfinance |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 85% | 70% | 15% | 60% | **~60%** |

---

## 33. Self-dealing (standalone page alias)

| Dimension | Status | Detail |
|-----------|--------|--------|
| **Pages** | IMPLEMENTED | `/self-dealing` (+ `/intelligence/self-dealing`) |
| **APIs** | IMPLEMENTED | `POST /intelligence/self-dealing` |
| **Schemas** | Report / entity | |

| Page % | API % | Schema % | Wiring % | **Overall** |
|--------|-------|----------|----------|-------------|
| 90% | 75% | 50% | 65% | **~65%** |

---

# Frontend page index (implementation)

| Route | File | Feature area | Page status |
|-------|------|--------------|-------------|
| `/` | `pages/index.js` | Home | IMPLEMENTED |
| `/login` | `login.js` | Auth | IMPLEMENTED |
| `/dashboard` | `dashboard.js` | Watchlists/dashboards | IMPLEMENTED |
| `/stock` | `stock.js` | Market | IMPLEMENTED |
| `/company` | `company.js` | Market | IMPLEMENTED |
| `/valuation` | `valuation.js` | Valuation | IMPLEMENTED |
| `/intelligence` | `intelligence.js` | Intelligence | IMPLEMENTED |
| `/intelligence/[id]` | `intelligence/[id].js` | Intelligence | IMPLEMENTED |
| `/intelligence/network` | `intelligence/network.js` | Intelligence | IMPLEMENTED |
| `/intelligence/correlation` | `intelligence/correlation.js` | Intelligence | IMPLEMENTED |
| `/intelligence/self-dealing` | `intelligence/self-dealing.js` | Intelligence | IMPLEMENTED |
| `/intelligence/contract-probability` | `intelligence/contract-probability.js` | Intelligence | IMPLEMENTED |
| `/intelligence/interactive-report` | `intelligence/interactive-report.js` | Intelligence | IMPLEMENTED |
| `/intelligence/interactive/[reportId]` | `intelligence/interactive/[reportId].js` | Intelligence | IMPLEMENTED |
| `/gov-trading` | `gov-trading.js` | Gov trading | IMPLEMENTED |
| `/gov-trading-leaderboard` | `gov-trading-leaderboard.js` | Gov trading | IMPLEMENTED |
| `/leaderboard` | `leaderboard.js` | Gov trading | IMPLEMENTED |
| `/institutional` | `institutional.js` | 13F | IMPLEMENTED |
| `/position-diff` | `position-diff.js` | 13F | IMPLEMENTED |
| `/institutional/position-diff` | `institutional/position-diff.js` | 13F | IMPLEMENTED |
| `/insider-activity` | `insider-activity.js` | Insider | IMPLEMENTED |
| `/earnings-calendar` | `earnings-calendar.js` | Earnings | IMPLEMENTED |
| `/ipo-calendar` | `ipo-calendar.js` | IPO | IMPLEMENTED |
| `/short-interest` | `short-interest.js` | Short interest | IMPLEMENTED |
| `/portfolios` | `portfolios.js` | Portfolio | IMPLEMENTED |
| `/portfolio/[id]` | `portfolio/[id].js` | Portfolio | IMPLEMENTED |
| `/portfolio-analytics` | `portfolio-analytics.js` | Portfolio | IMPLEMENTED |
| `/cost-basis` | `cost-basis.js` | Portfolio | IMPLEMENTED |
| `/tax-lots` | `tax-lots.js` | Portfolio | IMPLEMENTED |
| `/benchmark` | `benchmark.js` | Portfolio | IMPLEMENTED |
| `/alerts` | `alerts.js` | Alerts | IMPLEMENTED |
| `/tracking` | `tracking.js` | Tracking | IMPLEMENTED |
| `/tracking/alerts` | `tracking/alerts.js` | Tracking | IMPLEMENTED |
| `/chat` | `chat.js` | RAG | IMPLEMENTED |
| `/registry` | `registry.js` | Registry | IMPLEMENTED |
| `/graph` | `graph.js` | Entity graph | IMPLEMENTED |
| `/network-graph` | `network-graph.js` | Entity graph | IMPLEMENTED |
| `/recursive-discovery` | `recursive-discovery.js` | Entity graph | IMPLEMENTED |
| `/entity-discovery` | `entity-discovery.js` | Entity graph | IMPLEMENTED |
| `/entities/[id]` | `entities/[id].js` | Entity graph | IMPLEMENTED |
| `/entities/merge` | `entities/merge.js` | Entity graph | IMPLEMENTED |
| `/brokerage` | `brokerage.js` | Brokerage | IMPLEMENTED (STUB backend) |
| `/narrative-model` | `narrative-model.js` | Narrative AI | IMPLEMENTED (STUB backend) |
| `/pwa-settings` | `pwa-settings.js` | PWA | IMPLEMENTED (STUB backend) |
| `/pwa-advanced` | `pwa-advanced.js` | PWA | IMPLEMENTED (STUB backend) |
| `/social` | `social.js` | Social | IMPLEMENTED (PARTIAL/STUB) |
| `/crypto` | `crypto.js` | Crypto | IMPLEMENTED |
| `/economics` | `economics.js` | Macro | IMPLEMENTED |
| `/macro-dashboard` | `macro-dashboard.js` | Macro | IMPLEMENTED |
| `/consensus` | `consensus.js` | Analysts | IMPLEMENTED |
| `/guidance` | `guidance.js` | Analysts | IMPLEMENTED |
| `/analysts` | `analysts.js` | Analysts | IMPLEMENTED |
| `/revisions` | `revisions.js` | Analysts | IMPLEMENTED (API historically fragile) |
| `/litigation` | `litigation.js` | Legal | IMPLEMENTED |
| `/compliance` | `compliance.js` | Compliance | IMPLEMENTED |
| `/review` | `review.js` | Review | IMPLEMENTED |
| `/comments` | `comments.js` | Comments | IMPLEMENTED |
| `/workspaces` | `workspaces.js` | RBAC | IMPLEMENTED |
| `/teams` | `teams.js` | RBAC | IMPLEMENTED |
| `/billing` | `billing.js` | Billing | IMPLEMENTED |
| `/support` | `support.js` | Support | IMPLEMENTED |
| `/status` | `status.js` | Ops | IMPLEMENTED |
| `/sources` | `sources.js` | Sources | IMPLEMENTED |
| `/skills` | `skills.js` | Skills | IMPLEMENTED |
| `/reports` | `reports.js` | Reports | IMPLEMENTED |
| `/evidence` | `evidence.js` | Evidence | IMPLEMENTED |
| `/search` | `search.js` | Search | IMPLEMENTED |
| `/private-company` | `private-company.js` | OSINT | IMPLEMENTED |
| `/global-markets` | `global-markets.js` | Global | IMPLEMENTED |
| `/volume` | `volume.js` | Volume | IMPLEMENTED |
| `/formula` | `formula.js` | Formula | IMPLEMENTED |
| `/visualizations` | `visualizations.js` | Viz | IMPLEMENTED |
| `/bubble-charts` | `bubble-charts.js` | Viz | IMPLEMENTED |
| `/filing-compare` | `filing-compare.js` | Filings | IMPLEMENTED |
| `/ma-rumors` | `ma-rumors.js` | M&A | IMPLEMENTED |
| `/whisper` | `whisper.js` | Whisper | IMPLEMENTED |
| `/agent` | `agent.js` | Agent | IMPLEMENTED |
| `/self-dealing` | `self-dealing.js` | Intelligence | IMPLEMENTED |
| `/docket` | `docket.js` | Gov | IMPLEMENTED |
| `/persons` | `persons.js` | Persons | IMPLEMENTED |
| `/timeline` | `timeline.js` | Timeline | IMPLEMENTED |
| `/entity-analysis` | `entity-analysis.js` | Compare | IMPLEMENTED |
| `/compare` | `compare.js` | Compare | IMPLEMENTED |
| `/expert-analysis` | `expert-analysis.js` | Market | IMPLEMENTED |
| `/options` | `options.js` | Options | IMPLEMENTED |
| `/metrics` | `metrics.js` | Metrics | IMPLEMENTED |
| `/calendar` | `calendar.js` | Calendar | IMPLEMENTED |
| `/saved` | `saved.js` | Saved | IMPLEMENTED |
| `/pricing` | `pricing.js` | Marketing | IMPLEMENTED |

---

# API module index (registered prefixes)

| Prefix / module | File | Typical status |
|-----------------|------|----------------|
| `/auth` | `auth.py` | IMPLEMENTED |
| `/` core | `routes.py` | IMPLEMENTED (legacy overlap with auth) |
| `/market` | `market.py` | IMPLEMENTED |
| `/intelligence` | `intelligence.py` | IMPLEMENTED / PARTIAL |
| `/intelligence/graph` | `intelligence_graph.py` | PARTIAL |
| `/portfolio` | `portfolio.py` | IMPLEMENTED |
| `/portfolio-analytics` | `portfolio_analytics.py` | IMPLEMENTED |
| `/watchlist`, `/dashboard` | `dashboard.py` | IMPLEMENTED |
| `/alerts` | `price_alerts.py` | IMPLEMENTED |
| `/tracking` | `tracking.py` | IMPLEMENTED |
| `/earnings` | `earnings_calendar.py` | IMPLEMENTED |
| `/ipo` | `ipo_calendar.py` | IMPLEMENTED |
| `/short-interest` | `short_interest.py` | IMPLEMENTED |
| `/insider` | `insider_activity.py` | IMPLEMENTED |
| `/consensus` | `consensus.py` | PARTIAL |
| `/guidance` | `guidance.py` | PARTIAL |
| `/analysts` | `analysts.py` | PARTIAL |
| `/revisions` | `revision_screener.py` | PARTIAL / historically BROKEN import |
| `/chat` | `chat.py` | IMPLEMENTED |
| `/registry` | `registry.py` | IMPLEMENTED |
| `/entities`, `/entities/multi` | `entities.py`, `entities_multi.py` | IMPLEMENTED |
| `/graph` | `graph.py` | IMPLEMENTED |
| `/recursive` | `recursive_entity.py` | PARTIAL |
| `/corporate-ownership` | `corporate_ownership.py` | PARTIAL (slow/blocking risk) |
| `/brokerage` | `brokerage_sync.py` | **STUB** |
| `/narrative-model` | `narrative_model.py` | **STUB** |
| `/pwa`, `/pwa-advanced` | `mobile_pwa.py`, `pwa_advanced.py` | **STUB** |
| `/social` | `reddit_whale.py` | **STUB** / PARTIAL |
| `/government` | `government.py` | IMPLEMENTED |
| `/leaderboard` | `leaderboard.py` | IMPLEMENTED |
| `/litigation`, `/legal` | `litigation.py`, `legal_proceedings.py` | PARTIAL |
| `/compliance` | `compliance.py` | PARTIAL |
| `/review` | `review.py` | PARTIAL |
| `/comments`, `/annotations` | `comments.py` | PARTIAL |
| `/sources`, `/evidence`, `/documents`, `/filings` | various | PARTIAL |
| `/skills`, `/finance`, `/export` | various | PARTIAL |
| `/workspaces`, `/teams` | `workspaces.py`, `team_permissions.py` | PARTIAL |
| `/global` | `global_equity.py` | PARTIAL |
| `/volume`, `/volatility`, `/formula` | various | PARTIAL |
| `/valuation` | `valuation_timeline.py` | PARTIAL |
| `/cost-basis`, `/tax-lots`, `/benchmark` | various | PARTIAL |
| `/ma-rumors`, `/whisper`, `/agent` | various | PARTIAL |
| `/monitor`, `/demo`, `/status`, `/billing`, `/support` | various | PARTIAL |
| `/health` | `health_rag.py` + core | IMPLEMENTED |
| `/ontology`, `/docket`, `/persons` | various | PARTIAL |
| `/visualizations`, `/bubble-charts` | various | PARTIAL |
| `/fact-scoring`, `/honesty`, `/editorial`, `/seo`, `/freshness` | various | PARTIAL |
| `/experiments`, `/ai-visibility` | various | PARTIAL |

Many individual routes under these prefixes are never called by the frontend (~70% of routes unused historically).

---

# Appendix A — Full database schema inventory

Source files under `apps/api/app/models/`.

## A.1 Identity & tenancy (`models.py`)

### `organizations`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| name | String unique | |

### `workspaces`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| org_id | FK organizations | |
| name | String | |
| skill_budget_usd | Integer | default 100 |
| skill_spend_usd | Integer | default 0 |

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| email | String unique indexed | |
| name | String | |
| password_hash | String | |
| is_active | Boolean | |
| mfa_enabled | Boolean | |
| mfa_secret | String | |
| mfa_required | Boolean | |

### `roles` / `permissions` / `role_permissions` / `memberships`
| Table | Key columns |
|-------|-------------|
| roles | id, name, workspace_id (unique name per workspace) |
| permissions | id, name |
| role_permissions | role_id, permission_id |
| memberships | user_id, workspace_id, role_id |

### `projects` / `cases` / `invitations` / `audit_logs`
| Table | Key columns |
|-------|-------------|
| projects | workspace_id, name |
| cases | workspace_id, title |
| invitations | workspace_id, email, role_name, token, accepted |
| audit_logs | ts, user_id, org_id, workspace_id, action, entity_type, entity_id, meta |

---

## A.2 Entities & graph (`entities.py`)

### `entities`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| kind | String | person\|org\|fund\|… |
| name | String indexed | |
| canonical | **Boolean** | Prod bug when inserting int `1` |
| created_at / updated_at | DateTime | |
| meta | JSON | |

### `entity_aliases` / `entity_identifiers`
| Table | Key columns |
|-------|-------------|
| entity_aliases | entity_id, alias (unique pair) |
| entity_identifiers | entity_id, scheme (CIK\|LEI\|…), value (unique scheme+value) |

### `relationships`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| src_entity_id / dst_entity_id | FK entities | |
| kind | String | owns\|invested_in\|board_member\|… |
| as_of / valid_to | DateTime | temporal |
| confidence_tier | String | CONFIRMED\|REPORTED\|INFERRED\|SPECULATIVE |
| source_id / source_name / extracted_by | provenance | |
| meta | JSON | |

### `relationship_evidence` / merge tables
| Table | Key columns |
|-------|-------------|
| relationship_evidence | relationship_id, evidence_ref_id, meta |
| merge_candidates | a_entity_id, b_entity_id, score, reason, status |
| merge_actions | primary_id, secondary_id, action, meta |
| resolution_queue | entity_id, reason, created_at |

---

## A.3 Reports & claims (`reports.py`)

| Table | Key columns |
|-------|-------------|
| reports | title, kind, status (draft\|in_review\|approved\|published), meta |
| report_sections | report_id, name, content, order |
| evidence_bundles | report_id, name, items (JSON of evidence_ref ids) |
| claims | report_id, text, status, contradiction_note |
| claim_evidence | claim_id, evidence_ref_id, weight |

---

## A.4 Evidence (`evidence.py`)

| Table | Key columns |
|-------|-------------|
| raw_documents | sha256, content_type, size_bytes, storage_path, source_url, source_native_id, source_id, source_run_id, uploader_user_id, meta, legal_hold, retention_until |
| evidence_refs | raw_document_id, workspace_id, project_id, case_id, field_path, page/char ranges, excerpt, created_by_user_id |

---

## A.5 Monitoring & portfolios (`monitor.py`)

| Table | Key columns |
|-------|-------------|
| watchlists | name, meta |
| watchlist_items | watchlist_id, entity_id, ticker, notes, investment_threshold, notify_email/phone, alert_on_buy/sell |
| investment_alert_seen | watchlist_item_id, investor_name, ticker, txn_type, value_usd, trade_date |
| portfolios | user_id, name, base_ccy, thesis |
| positions | portfolio_id, entity_id, ticker, qty, cost_basis, notes |
| alert_rules | name, kind, params, watchlist_id, portfolio_id, enabled |
| alert_events | rule_id, entity_id, ticker, kind, payload, delivered |
| delivery_channels | rule_id, kind (inapp\|email\|…), target, meta |
| watchlist_shares | watchlist_id, shared_by, shared_with, permission |
| dashboards | user_id, name, is_default, layout |
| dashboard_widgets | dashboard_id, widget_type, title, config, position/size |
| entity_comments | user_id, entity_type, entity_id, content, parent_id, visibility |
| comment_reactions | comment_id, user_id, reaction_type |
| annotations | user_id, document_type/id, offsets, selected_text, note, color, tags, visibility |
| price_alerts | alert_id, user_id, ticker, alert_type, target_value, status, channels, recurring |
| alert_notifications | notification_id, alert_id, user_id, ticker, message, channel, read |

---

## A.6 Sources pipeline (`sources.py`)

| Table | Key columns |
|-------|-------------|
| sources | name, kind, workspace_id, config |
| source_credentials | source_id, kind, secret (JSON) |
| source_contracts | source_id, version, spec |
| source_runs | source_id, status, started/finished, error, metrics, checkpoint |
| source_record_meta | source_id, run_id, external_id, hash, normalized, evidence_ref_id |
| source_dead_letters | run_id, external_id, error, payload |
| source_checkpoints | source_id, cursor_key, state |

---

## A.7 Review workflow (`review.py`)

| Table | Key columns |
|-------|-------------|
| report_comments | report_id, section_id, text, author |
| suggestions | report_id, section_id, proposed, state |
| section_versions | section_id, content |
| review_assignments | report_id, reviewer, role |
| review_tasks | report_id, kind, payload, status |

---

## A.8 Compliance (`compliance.py`)

| Table | Key columns |
|-------|-------------|
| policies | name, rules (JSON), active |
| export_approvals | report_id, requested_by, status, notes |

---

## A.9 Skills (`skills.py`)

| Table | Key columns |
|-------|-------------|
| skill_registry | name, version, provider, allowlisted |
| skill_runs | skill_id, input/output JSON, adapter, status, review_required, cost_usd, token_count |
| skill_artifacts | run_id, kind, path, meta |

---

## A.10 Registry API (`registry.py`)

| Table | Key columns |
|-------|-------------|
| registry_api_keys | name, key_hash, key_prefix, revoked_at, rate_limit_per_min, notes |
| registry_api_usage | key_hash, endpoint, query_params, response_count, ip_address |

---

## A.11 13F cache (`market_13f_cache.py`)

| Table | Key columns |
|-------|-------------|
| institutional_13f_period_cache | institution_cik, report_period, institution_name, accession/form/filing fields, warnings_json, data_quality_json |
| institutional_13f_supplemental_amendment_cache | period_cache_id, sort_order, accession, form, filing_date, amendment fields |
| institutional_13f_position_cache | period_cache_id, position fields (cusip, ticker, value, shares, put/call, etc.) |

---

## A.12 13F position-diff Pydantic schemas (`market_13f_schemas.py`)

| Schema | Role |
|--------|------|
| `PositionDiffRequest` | Request body for QoQ diff |
| `PositionDiffWarning` | Warning records |
| `PositionDiffDataQuality` | Quality flags |
| `PositionSnapshotEntry` | Single-period position |
| `PositionDiffPosition` | Diffed position row |
| `PositionDiffHighlights` | Summary highlights |
| `PositionDiffSummary` | Aggregate stats |
| `PositionDiffPagination` | Page metadata |
| `PositionDiffInstitution` | Institution identity |
| `PositionDiffPeriods` | Period pair |
| `PositionDiffFilingRef` / `PositionDiffFilings` | Filing references |
| `PositionDiffResponse` | Full API response |
| Enums | `PositionDiffStatus`, `PositionDiffFilterStatus`, `PositionDiffSortField`, `SortDirection`, `PutCallValue` |

---

## A.13 Feature → schema map (quick)

| Feature | Primary schemas |
|---------|-----------------|
| Auth | User, AuditLog |
| Workspaces/RBAC | Organization, Workspace, Role, Permission, RolePermission, Membership, Invitation |
| Intelligence reports | Report, ReportSection, Claim, ClaimEvidence, EvidenceBundle, RawDocument, EvidenceRef |
| Entity graph | Entity, EntityAlias, EntityIdentifier, Relationship, RelationshipEvidence, Merge* |
| Portfolio | Portfolio, Position |
| Watchlists/alerts | Watchlist*, Alert*, PriceAlert*, InvestmentAlertSeen, Dashboard* |
| Comments/annotations | EntityComment, CommentReaction, Annotation, report Comment/Suggestion |
| 13F | Institutional13F* + PositionDiff* Pydantic |
| Sources/skills | Source*, Skill* |
| Registry API | RegistryApiKey, RegistryApiUsage |
| Compliance export | Policy, ExportApproval |
| Market calendars / quotes | Mostly **no DB schema** (live external APIs) |
| Brokerage / Narrative / PWA push | **No product schemas** (stubs) |

---

# Appendix B — Scoring methodology

Taken from `MASTER_TASK_STATUS.md` strict checklist. A feature is **not** complete unless:

1. Frontend page exists and is reachable  
2. API endpoint is registered and responds  
3. Service runs real logic (not stub `no_data` for the whole feature)  
4. DB persists when applicable  
5. Data survives restart when applicable  
6. External API actually called when applicable  
7. User can see real data in UI  
8. Errors handled honestly  

**Platform weighted total (REQ-001…020):** ~**45%** as of last honest audit cycle. Unverified post-audit commit claims of 85% should not be used.

---

# Appendix C — Related documents

| Document | Role |
|----------|------|
| `MASTER_TASK_STATUS.md` | Honest task / % source of truth |
| `docs/INDEPENDENT_AUDIT_2026-08-26.md` | Full REQ matrix & evidence |
| `docs/INDEPENDENT_AUDIT_2026-08-23.md` | Earlier route/wiring audit |
| `docs/AUDIT_2026-08-25.md` | Prior audit |
| `docs/requirements/FINANCE_PLATFORM_FEATURES_AND_STRATEGY.md` | Feature strategy |
| `.env.example` | Required/optional API keys |
| `apps/api/app/main.py` | Router registration |

---

*Generated for engineering handoff. Re-verify any % before claiming progress in commits.*
