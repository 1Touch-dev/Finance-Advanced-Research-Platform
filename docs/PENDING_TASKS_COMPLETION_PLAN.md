# Pending Tasks & Completion Plan — Path to 100%

**Companion to:** [`PRODUCT_FEATURES_DOCUMENTATION.md`](./PRODUCT_FEATURES_DOCUMENTATION.md)  
**Baselines:** `MASTER_TASK_STATUS.md`, audits 23–26 Aug 2026, KT handover 5 Oct 2026  
**Current verified completion:** ~45%  
**Target:** 100% honest E2E completion (checklist-backed, not file-count)

---

## How to use this document

| Field | Meaning |
|-------|---------|
| **Task ID** | Stable ID for tracking (e.g. `INTEL-003`) |
| **Priority** | P0 blocker → P1 major → P2 important → P3 polish / decision-gated |
| **What** | Work remaining |
| **How** | Concrete approach |
| **Page / API / Schema / Wiring / Other** | Artifacts to create or fix |
| **Depends on** | Blocking task IDs |
| **Done when** | Strict verification checklist passes |

### Strict “done” checklist (every task)

```
[ ] Page reachable (if UI)
[ ] API registered and responds
[ ] Real logic (not stub no_data for the whole feature)
[ ] DB persists when applicable + survives restart
[ ] External API called when applicable
[ ] User sees real data (or honest empty state)
[ ] Errors handled; no fake numbers
[ ] Tests or smoke script for the happy path
```

### ID prefix legend

| Prefix | Category |
|--------|----------|
| `PROD` | Production / staging ops |
| `INFRA` | Platform: DB, Redis, migrations, CI, Docker, monitoring |
| `AUTH` | Authentication |
| `WS` | Workspaces / teams / RBAC |
| `GOV` | Government trading |
| `MKT` | Stock / market data |
| `VAL` | Valuation |
| `INTEL` | Intelligence dossiers & reports |
| `GRAPH` | Entity graph & relationships |
| `PF` | Portfolios |
| `ALERT` | Watchlists, dashboards, price & trade alerts |
| `F13` | Institutional 13F / position-diff |
| `EARN` | Earnings calendar |
| `IPO` | IPO calendar |
| `SHORT` | Short interest |
| `INS` | Insider activity |
| `MACRO` | FRED / economics |
| `CONS` | Consensus / guidance / analysts / revisions |
| `VOL` | Volume / volatility / formula / viz |
| `CRYPTO` | Crypto |
| `REG` | Registry / OSINT search |
| `RAG` | RAG chat |
| `QG` | Quality gates |
| `REV` | Review / comments / annotations |
| `LIT` | Litigation / legal / compliance |
| `SRC` | Sources / skills / export / status / billing |
| `CMP` | Multi-entity comparison |
| `MA` | M&A / whisper / agent |
| `SOC` | Social / whale |
| `BRK` | Brokerage sync |
| `NAR` | Narrative AI model |
| `PWA` | Mobile PWA |
| `GLOB` | Global markets |
| `SELF` | Self-dealing analysis |
| `WIRE` | Cross-cutting FE↔BE wiring |
| `TEST` | Tests / CI / audit |
| `CEO` | Business decisions required |
| `UX` | UI/UX polish (finance dark-blue) |

---

## Master backlog summary

| Priority | Count (approx) | Focus |
|----------|----------------|-------|
| **P0** | ~15 | Prod broken, migrations, auth shadow, intelligence crash, graph insert |
| **P1** | ~40 | Feature completion, Redis, auth on all pages, persistence |
| **P2** | ~35 | Depth, unused routes, polish, optional integrations |
| **P3 / CEO-gated** | ~20 | Plaid, GPU narrative, Reddit, full PWA |

**Suggested phases to 100%**

| Phase | Goal | Moves completion |
|-------|------|------------------|
| **Phase A** | Production foundation + P0 fixes | ~45% → ~55% |
| **Phase B** | Core features E2E (intel, graph, portfolio, auth, keys) | → ~70% |
| **Phase C** | Depth + wiring + no stubs in UI | → ~85% |
| **Phase D** | CEO-gated + polish + dead-code cleanup | → **100%** |

---

# Category 0 — Production & platform (must run fine in prod)

## PROD — Staging / production operations

| ID | Pri | What | How | Page | API | Schema | Wiring | Other / setup |
|----|-----|------|-----|------|-----|--------|--------|---------------|
| **PROD-001** | P0 | Deploy local HEAD to staging (was ~10 commits behind) | Diff server `.bak`/backup files; deploy `76c066c`+; smoke `/health`, `/health/full` | — | `/health`, `/health/full` | — | Confirm web `NEXT_PUBLIC_API_URL` points at API | PM2 restart `finance-api`, `finance-web`; rollback plan |
| **PROD-002** | P0 | Dedicated Postgres for this platform | Create DB `finance_platform` (not shared `enterprise_claude_skills`); update `DATABASE_URL`; migrate; cut over | — | — | Run all Alembic | — | New PG user/password; backup old DB; no shared tenancy |
| **PROD-003** | P0 | Investigate API 339 restarts / 41 days | `pm2 logs finance-api --lines 500`; check OOM vs uncaught; fix root cause; memory limits | — | — | — | — | Increase EC2 RAM or fix leak; alerts on restart |
| **PROD-004** | P1 | Investigate web 70 restarts | Same as PROD-003 for `finance-web` | — | — | — | — | Node OOM / crash loops |
| **PROD-005** | P0 | Fix disk/RAM headroom | Clean logs/artifacts; resize instance if disk ≥79% | — | — | — | — | Target disk &lt;70%, ≥1GB free RAM idle |
| **PROD-006** | P1 | Production env secrets inventory | Fill all required keys on server; never commit `.env` | — | — | — | Frontend build-time `NEXT_PUBLIC_API_URL` | See § Production setup checklist below |
| **PROD-007** | P1 | Fix Docker build env order | Set `NEXT_PUBLIC_API_URL` **before** `next build` in Dockerfile/compose | Web build | — | — | Rebuild image | `INFRA-008` |
| **PROD-008** | P1 | HTTPS + domain | TLS cert, reverse proxy (nginx/Caddy), update CORS | — | CORS in FastAPI | — | Update API URL in web | DNS A records |
| **PROD-009** | P1 | Monitoring & alerting | Sentry DSN both apps; uptime check `/health`; PM2 restart alerts | `/status` | `/health/full` | — | Wire Sentry in web/api | Slack/email on fail |
| **PROD-010** | P2 | Backup & restore runbook | Nightly PG dump; restore drill | — | — | — | — | S3/local backup; document RTO/RPO |
| **PROD-011** | P2 | Rate limiting & Redis in prod | Ensure Redis up; enable rate limit + cache | — | All hot routes | — | — | `REDIS_URL`; `INFRA-004` |
| **PROD-012** | P1 | Load quality classifier model on prod | Copy trained joblib/model artifact; set path; verify `/health/full` → trained | — | `/health/full` | Model file path | — | `QG-002` |

### Production setup checklist (all required for “running fine”)

```
[ ] PROD-002 dedicated Postgres DATABASE_URL
[ ] INFRA-001 full Alembic migrations applied
[ ] JWT_SECRET strong (64+ char hex)
[ ] SEC_USER_AGENT set (name + email)
[ ] FINNHUB_API_KEY valid
[ ] FRED_API_KEY valid
[ ] OPENAI_API_KEY and/or ANTHROPIC_API_KEY (intelligence + RAG)
[ ] Redis running; REDIS_URL set
[ ] CORS allows web origin
[ ] NEXT_PUBLIC_API_URL set at build time
[ ] PM2 (or systemd) process list: api, web, optional worker
[ ] /health and /health/db and /health/rag return 200
[ ] Login → /auth/me works
[ ] Sample intelligence generate succeeds
[ ] Quality classifier status trained (or honest “not_trained” UI)
[ ] Monitoring (PROD-009)
[ ] Backups (PROD-010)
[ ] Disk/RAM headroom (PROD-005)
```

**Optional but needed for “100% of advertised features”:** Apollo, Congress, FEC, SendGrid, Twilio, FMP, NewsAPI, CourtListener, OpenCorporates, Plaid (CEO), Reddit (CEO), VAPID (CEO), GPU (CEO).

---

## INFRA — Platform engineering

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **INFRA-001** | P0 | Alembic migrations for all 50+ models | `alembic revision --autogenerate`; review; apply on SQLite+PG; CI check | — | — | All models in Appendix A of features doc | — | Fresh Postgres boot must succeed without `create_all` only |
| **INFRA-002** | P0 | Fix intelligence crash on fresh DB | Reproduce on empty DB; fix missing tables/columns/migration order | `/intelligence` | `POST /intelligence/generate` | Report/Claim/Entity tables | E2E generate | Depends INFRA-001 |
| **INFRA-003** | P1 | Remove reliance on `DB_AUTO_CREATE` in prod | Migrations only in prod | — | — | — | — | `DB_AUTO_CREATE=off` in prod |
| **INFRA-004** | P1 | Redis caching for hot GETs | Install redis py; cache Finnhub/FRED/yfinance responses with TTL | — | market/earnings/macro | — | — | Redis service; env |
| **INFRA-005** | P1 | Persist in-memory API modules to DB | Audit ~6 modules using dicts; add models + migrate | Affected pages | Affected routers | New tables as needed | Keep API shapes | Data survives restart |
| **INFRA-006** | P1 | Fix async endpoints that block event loop | Convert sync I/O to `run_in_executor` or sync routes; timeouts on ownership/intel | — | esp. `corporate-ownership`, intelligence | — | — | Cap depth/time |
| **INFRA-007** | P1 | Resolve duplicate `/auth` routers | Remove or rename legacy `routes.py` auth; single JWT JSON body API | `/login` | `/auth/*` | TokenResponse | Align FE to `access_token` | AUTH-001 |
| **INFRA-008** | P1 | Docker compose prod-ready | Postgres+Redis+api+web; build args for Next public URL; healthchecks | — | — | — | — | Docs in DEPLOYMENT |
| **INFRA-009** | P1 | CI runs pytest + smoke | GitHub Action: migrate, pytest, boot app, hit `/health` | — | — | — | — | Fail on test fail |
| **INFRA-010** | P2 | Fix `local-start.ps1` npm warn → fatal | Don’t treat npm stderr as terminating error; use Python 3.12 pin | — | — | — | — | Dev UX |
| **INFRA-011** | P2 | Windows WeasyPrint optional | Soft-import OSError; ReportLab default; document GTK for premium PDF | Intelligence PDF | markdown/premium PDF routes | — | — | Optional MSYS2 |
| **INFRA-012** | P2 | Dead route inventory | Machine-diff FE fetch URLs vs OpenAPI; mark or delete unused | — | Unused ~70% | — | Prefer wire useful ones | Maintainability |
| **INFRA-013** | P1 | Seed RBAC permissions/roles | Bootstrap default roles so RBAC grants work | `/teams` | `/teams/*` | Role, Permission, RolePermission | — | Empty roles = useless RBAC |

---

# Category 1 — Feature pending work (by feature)

---

## AUTH — User Authentication (~90% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **AUTH-001** | P0 | Dedupe auth API | Keep `auth.py`; remove conflicting register/login from `routes.py` | `/login` | `POST /auth/register`, `/login`, `GET /me` | User | FE uses `access_token` + Bearer | INFRA-007 |
| **AUTH-002** | P1 | Register UI | Add register form or link on login | `/login` or `/register` | register | User | apiFetch | — |
| **AUTH-003** | P1 | Logout + token refresh | Clear storage; optional refresh endpoint | All | logout/refresh if added | — | AuthProvider | — |
| **AUTH-004** | P1 | Protect all write pages | Redirect unauthenticated users | All CRUD pages | — | — | Auth gate HOC | WIRE-001 |
| **AUTH-005** | P2 | MFA optional path | Wire existing MFA fields | Settings page (create if missing) | MFA endpoints if missing | User.mfa_* | — | — |

---

## WS — Workspaces / Teams / RBAC (~60% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **WS-001** | P1 | E2E create workspace + membership | Service uses real DB; remove no_data paths | `/workspaces` | `/workspaces` CRUD | Workspace, Membership | apiFetch + auth | INFRA-013 |
| **WS-002** | P1 | Teams invite + role assign UI | Connect invite flow | `/teams` | `/teams/*`, invitations | Invitation, Role | — | Email optional |
| **WS-003** | P2 | Enforce RBAC on sensitive routes | Dependency checks role_permissions | — | Reports/export/compliance | RolePermission | — | — |
| **WS-004** | P2 | Replace workspace_service no_data | Implement remaining 33 honest-fallback paths with real logic or remove | `/workspaces` | matching | — | — | — |

---

## GOV — Government Trading (~85% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **GOV-001** | P2 | Persist politician trades cache | Optional DB table for PTR history | `/gov-trading` | gov-trading routes | New `PoliticianTrade` (create) | — | Faster leaderboard |
| **GOV-002** | P1 | Full Congress.gov depth | Use `CONGRESS_API_KEY`; bills + sponsors linked to entities | `/docket`, gov pages | `/government/*`, Congress connector | Entity links | — | Key in prod |
| **GOV-003** | P2 | ROI vs S&P refresh pipeline | Scheduled job refresh rankings JSON | `/gov-trading-leaderboard` | leaderboard APIs | — | PM2 cron | Source James spreadsheet process |
| **GOV-004** | P2 | Honest empty states | UI when feed empty | pages above | — | — | — | UX |

---

## MKT — Stock Market Data (~80% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **MKT-001** | P1 | Prod Finnhub key + error UX | Valid key; UI shows “configure FINNHUB” not silent fail | `/stock`, `/company` | `/market/*` | — | — | PROD-006 |
| **MKT-002** | P2 | Optional quote cache table | Cache last quote/TTL | — | quote endpoints | `MarketQuoteCache` (create) | — | INFRA-004 |
| **MKT-003** | P2 | Unify company deep analysis page | Ensure all panels call live connectors | `/company` | SEC/YF/FMP routes | — | Wire every tab | SEC_USER_AGENT |
| **MKT-004** | P2 | Options / technicals polish | Verify IV surface + technicals E2E | `/options`, `/stock` | `/volatility`, `/market/technicals` | — | — | — |

---

## VAL — Valuation (~65% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **VAL-001** | P1 | Reduce valuation_timeline no_data | Wire remaining functions to yfinance/FMP | `/valuation` | `/valuation/*`, `/finance/*` | Optional `ValuationRun` | — | packages/finance |
| **VAL-002** | P2 | Persist DCF runs | Save scenarios for history | `/valuation` | POST save | `ValuationRun` (create) | — | — |
| **VAL-003** | P2 | Bear/base/bull UI clarity | Present three scenarios consistently | `/valuation` | DCF APIs | — | — | — |

---

## INTEL — Intelligence Reports (~50% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **INTEL-001** | P0 | Fresh-DB generate works | Fix crash; migration; smoke test | `/intelligence` | `POST /intelligence/generate` | Report* | E2E | INFRA-002 |
| **INTEL-002** | P1 | Stable 9-section output | Each section filled or honest “no data” with source | `/intelligence/[id]` | GET report | ReportSection, Claim | Claim tags in UI | Connectors keys |
| **INTEL-003** | P1 | Export reliability | ReportLab PDF/Word/Excel/PPT without WeasyPrint required | download buttons | `/intelligence/{id}/pdf\|word\|excel\|powerpoint` | — | — | INFRA-011 |
| **INTEL-004** | P1 | Network report engine (not one-off seeds) | Generic group config → recursive entities | `/intelligence/network` | generate-network, available-networks | Entity, Relationship | Click-to-investigate | GRAPH-* |
| **INTEL-005** | P1 | Evidence on every claim | Enforce evidence_ref; show Confirmed/Reported/Inferred | report UI | claim APIs | ClaimEvidence, RelationshipEvidence | — | CEO accuracy moat |
| **INTEL-006** | P2 | Apollo/OpenCorporates enrichment | Keys in prod; graceful degrade | `/private-company` | `/intelligence/apollo/*`, private-co | — | — | APOLLO_API_KEY |
| **INTEL-007** | P2 | Job status UX | Poll report-job; progress bar | intelligence pages | `/intelligence/report-job/{id}` | — | — | Background jobs |
| **INTEL-008** | P2 | Quality gate before publish | Block publish if gates fail | report UI | quality-gates endpoint | — | QG-* | — |

---

## GRAPH — Entity Graph (~50% → 100%) — **prod broken**

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **GRAPH-001** | P0 | Fix `canonical` bool/int insert | Cast/bind boolean correctly for Postgres; deploy | graph pages | entity create/ingest | Entity.canonical | — | Stops silent drop of Apple/MSFT/NVDA |
| **GRAPH-002** | P0 | Verify persistence across restart | Insert → restart API → query same edges | `/graph` | `/graph`, `/entities` | Relationship* | — | Autotest |
| **GRAPH-003** | P1 | Evidence required on edges | Service rejects edges without evidence_ref | network UI | relationship create | RelationshipEvidence | Show source in UI | INTEL-005 |
| **GRAPH-004** | P1 | Recursion depth budget | Cap depth 3; cost ceiling; config | `/recursive-discovery` | `/recursive/*` | — | — | CEO spend decision |
| **GRAPH-005** | P1 | Timeout corporate-ownership | Hard timeout; sync off event loop | ownership UI if any | `/corporate-ownership/*` | — | — | INFRA-006 |
| **GRAPH-006** | P2 | Merge UI E2E | Approve/reject merge candidates | `/entities/merge` | merge APIs | MergeCandidate, MergeAction | — | — |
| **GRAPH-007** | P2 | Proxy family/trust extraction | Parse DEF 14A related-party sections (James ask) | entity/intel | new parser connector | Relationship kinds | — | Source depth |

---

## PF — Portfolio (~65% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **PF-001** | P1 | Auth on all portfolio writes | Bearer required; no demo_user | `/portfolios`, `/portfolio/[id]` | `/portfolio/*` | Portfolio, Position | apiFetch | AUTH-004 |
| **PF-002** | P1 | Persist user_id correctly | Align String user_id vs User.id int | — | create portfolio | Portfolio.user_id (migrate?) | — | Schema consistency |
| **PF-003** | P2 | Analytics E2E | Verify portfolio-analytics with real holdings | `/portfolio-analytics` | `/portfolio-analytics/*` | — | — | yfinance |
| **PF-004** | P2 | Cost basis / tax lots | Complete remaining no_data paths or honest UI | `/cost-basis`, `/tax-lots` | matching | — | — | BRK if Plaid |
| **PF-005** | P2 | Benchmark vs SPY | Working comparison chart | `/benchmark` | `/benchmark/*` | — | — | — |

---

## ALERT — Watchlists / Dashboards / Alerts / F-03/F-04 (~65–70% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **ALERT-001** | P1 | CRUD watchlist E2E with auth | Create/list/share | `/dashboard`, `/saved` | `/watchlist/*` | Watchlist* | — | — |
| **ALERT-002** | P1 | Price alerts fire + notify | Scanner job + SendGrid/Twilio | `/alerts` | `/alerts/*` | PriceAlert*, AlertNotification* | — | Keys; Redis/cron |
| **ALERT-003** | P1 | Form 4 big-trade scanner prod | PM2 every 4h; verify email/SMS | `/tracking` | `/tracking/scan/*` | InvestmentAlertSeen | — | SENDGRID, TWILIO |
| **ALERT-004** | P1 | Investment threshold alerts | Per-item thresholds from watchlist | `/tracking/alerts` | tracking + watchlist | WatchlistItem thresholds | — | — |
| **ALERT-005** | P2 | Dashboard widgets persist | Save layout | `/dashboard` | `/dashboard/*` | Dashboard, DashboardWidget | — | — |
| **ALERT-006** | P2 | Delivery channels UI | Configure email/SMS/webhook | alerts settings | delivery APIs | DeliveryChannel | — | — |

---

## F13 — Institutional 13F (~85% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **F13-001** | P2 | Cache warm job | Prefetch top institutions | `/institutional` | 13F routes | Institutional13F* | — | Cron |
| **F13-002** | P2 | Position-diff UX polish | Filters/sort match Pydantic schemas | `/position-diff` | position-diff API | PositionDiffResponse | Wire query params | — |
| **F13-003** | P2 | Mega-position alerts | Optional alert when 13F change &gt; N | tracking | new endpoint or tracking | — | ALERT | — |

---

## EARN / IPO / SHORT / INS (~85–90% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **EARN-001** | P1 | Enforce Finnhub in prod | Key + UI empty state | `/earnings-calendar` | `/earnings/*` | — | — | FINNHUB |
| **IPO-001** | P1 | Same for IPO + FMP fallback | Keys | `/ipo-calendar` | `/ipo/*` | — | — | FMP optional |
| **SHORT-001** | P2 | Extra analytics (days-to-cover trends) | Charts | `/short-interest` | `/short-interest/*` | optional cache | — | FINRA |
| **INS-001** | P2 | Insider feed filters + pagination | UX | `/insider-activity` | `/insider/*` | — | — | SEC_USER_AGENT |

---

## MACRO — Economics (~70% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **MACRO-001** | P1 | Valid FRED_API_KEY everywhere | Stop 400 spam | `/economics`, `/macro-dashboard` | `/market/macro/*` | — | — | PROD-006 |
| **MACRO-002** | P2 | Cache FRED series | Redis/DB | — | macro routes | optional MacroCache | — | INFRA-004 |
| **MACRO-003** | P2 | BEA regional panels | If connector exists, wire UI | economics | BEA routes | — | — | — |

---

## CONS — Consensus / Guidance / Analysts / Revisions (~60% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **CONS-001** | P0 | Fix revisions router import | Restore missing symbols or rewrite screener | `/revisions` | `/revisions/*` | — | Wire page | Was 404 |
| **CONS-002** | P1 | Guidance credibility E2E | Finnhub | `/guidance` | `/guidance/*` | — | — | Key |
| **CONS-003** | P1 | Consensus snapshot E2E | Finnhub | `/consensus` | `/consensus/*` | — | — | Key |
| **CONS-004** | P2 | Analyst scorecards | `/analysts`, `/analyst/[id]` | `/analysts/*` | — | — | — | |

---

## VOL — Volume / Volatility / Formula / Viz (~70% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **VOL-001** | P2 | Volume screen no_data cleanup | Real logic or remove dead UI | `/volume` | `/volume/*` | — | — | |
| **VOL-002** | P2 | Formula builder save | Persist formulas | `/formula` | `/formula/*` | FormulaSave (create) | — | |
| **VOL-003** | P2 | Viz/bubble charts live data | Wire to market APIs | `/visualizations`, `/bubble-charts` | viz APIs | — | — | |
| **VOL-004** | P2 | Filing compare E2E | SEC filings | `/filing-compare` | `/filings/*` | — | — | |

---

## CRYPTO (~65% → 100%) — low client priority

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **CRYPTO-001** | P3 | CoinGecko key + rate limits | Stable dashboard | `/crypto` | crypto market routes | — | — | Optional |
| **CRYPTO-002** | P3 | Whale/wallet honest states | No fake whales | `/crypto` | wallet APIs | — | — | Etherscan key |

---

## REG — Registry / OSINT (~70% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **REG-001** | P1 | Verify 50-state connectors depth | Per-jurisdiction smoke; document gaps | `/registry` | `/registry/*` | RegistryApi* | — | packages/connectors |
| **REG-002** | P2 | OpenCorporates/GLEIF keys | Enrich private-co | `/private-company` | private-co routes | — | — | Keys |
| **REG-003** | P2 | Registry API key productization | Issue keys for external consumers | admin or `/status` | registry key APIs | RegistryApiKey | — | Rate limits |

---

## RAG — Chat (~75% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **RAG-001** | P1 | Document ingest UI | Upload filings → chunk → embed | `/chat` + ingest page if needed | `/chat/*`, `/documents/*` | RawDocument | — | OPENAI embeddings |
| **RAG-002** | P1 | Persist vector index | PGVector or durable store (not only ephemeral numpy) | — | chat | pgvector / table | — | INFRA |
| **RAG-003** | P2 | Eval suite in CI | hit@k / MRR smoke | — | — | — | — | Offline fixtures |
| **RAG-004** | P2 | Guardrails visible | Show “no advice” + sources in UI | `/chat` | chat debug | — | — | |

---

## QG — Quality Gates (~85% code / ~40% prod → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **QG-001** | P1 | Train/load classifier artifact in repo or artifact store | Document path; load on startup | — | health | — | — | PROD-012 |
| **QG-002** | P1 | Prod health shows trained | Deploy model file | `/status` | `/health/full` | — | — | |
| **QG-003** | P2 | LLM judge cost controls | Cache; sample rate | intel publish | quality services | — | INTEL-008 | ANTHROPIC |
| **QG-004** | P2 | Label logging pipeline | Continue training data collection | — | — | label store | — | |

---

## REV — Review / Comments / Annotations (~55% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **REV-001** | P1 | Comments E2E with auth | Create/list/reply | `/comments` | `/comments/*` | EntityComment* | Bearer | Persist rows &gt; 0 |
| **REV-002** | P1 | Annotations on filings/reports | Highlight + note | report/filing viewers | `/annotations/*` | Annotation | — | |
| **REV-003** | P2 | Review workflow assign/approve | Tasks UI | `/review`, `/review/[id]` | `/review/*` | ReviewTask, assignments | — | |
| **REV-004** | P2 | Evidence browser | Link claims to docs | `/evidence` | `/evidence/*` | EvidenceRef | — | |

---

## LIT — Litigation / Compliance (~55% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **LIT-001** | P2 | CourtListener key + live cases | | `/litigation` | `/litigation/*`, `/legal/*` | — | — | COURTLISTENER_* |
| **LIT-002** | P2 | Export approval workflow | Policy gates | `/compliance` | `/compliance/*`, `/export` | Policy, ExportApproval | — | |
| **LIT-003** | P3 | Sanctions screening | Connector + UI panel | intel/compliance | sanctions | — | — | Optional key |

---

## SRC — Sources / Skills / Billing / Support / Status (~50% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **SRC-001** | P2 | Source run monitoring UI | Show runs/dead letters | `/sources` | `/sources/*` | SourceRun* | — | |
| **SRC-002** | P2 | Skills allowlist + budget | Enforce skill_budget_usd | `/skills` | `/skills/*` | Skill* | — | LLM keys |
| **SRC-003** | P3 | Stripe billing | Or hide billing until ready | `/billing`, `/pricing` | `/billing/*` | — | — | STRIPE_* |
| **SRC-004** | P2 | Support tickets real or remove | | `/support` | `/support/*` | optional | — | |
| **SRC-005** | P1 | Status page = true health | Surface classifier, redis, db | `/status` | `/status`, `/health/full` | — | — | |

---

## CMP — Multi-entity comparison (~60% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **CMP-001** | P1 | Side-by-side live metrics | Wire compare to market+intel APIs | `/compare`, `/entity-analysis` | multi + market | — | — | |
| **CMP-002** | P2 | Deep comparative service | Use deep comparative service in UI | pages above | intelligence comparative | — | — | |

---

## MA — M&A / Whisper / Agent (~40% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **MA-001** | P2 | NewsAPI for M&A rumors | Real headlines or honest empty | `/ma-rumors` | `/ma-rumors/*` | — | — | NEWSAPI_KEY |
| **MA-002** | P2 | Whisper feature define or remove | Product decision: implement or delete page | `/whisper` | `/whisper/*` | — | — | |
| **MA-003** | P3 | Autonomous agent scope | Cap tools; or hide `/agent` | `/agent` | `/agent/*` | — | — | Cost control |

---

## SOC — Social / Whale (~40% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **SOC-001** | P3 | Reddit API approval + implement | Replace stubs | `/social` | `/social/*` | optional | — | **CEO-003** |
| **SOC-002** | P2 | Institutional flow via yfinance only | Honest label “not Reddit” | `/social` | social routes | — | — | Until Reddit |

---

## BRK — Brokerage (0% → 100%) — **CEO-gated**

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **BRK-001** | P3 | Plaid contract decision | Sign or remove UI | `/brokerage` | — | — | — | **CEO-001** |
| **BRK-002** | P3 | Implement Plaid link + sync | Real service replacing no_data | `/brokerage` | `/brokerage/*` | `BrokerageItem`, `LinkedAccount` (create) | OAuth return | Secrets |
| **BRK-003** | P3 | Map holdings → Portfolio | Sync positions | portfolios | sync endpoint | Position | — | PF |

Until CEO-001: **hide `/brokerage`** or banner “Not available”.

---

## NAR — Narrative Model (0% → 100%) — **CEO-gated**

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **NAR-001** | P3 | GPU budget decision | RunPod etc. | `/narrative-model` | — | — | — | **CEO-002** |
| **NAR-002** | P3 | Training pipeline + deploy | Replace stubs | page | `/narrative-model/*` | model registry schema | — | Docs in AI training plans |
| **NAR-003** | P2 | Interim: use Claude/GPT narrative | Already partial in intel; hide dedicated stub page | intel | — | — | — | Until NAR-002 |

---

## PWA (~25% → 100%) — **CEO-gated**

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **PWA-001** | P3 | VAPID / Firebase decision | Configure or remove | `/pwa-settings` | `/pwa/*` | `PushSubscription` (create) | Service worker | **CEO-005** |
| **PWA-002** | P3 | Implement push + offline | Real pwa_advanced_service | `/pwa-advanced` | `/pwa-advanced/*` | — | — | |
| **PWA-003** | P2 | Hide stub pages until ready | Nav cleanup | — | — | — | — | Honest UX |

---

## GLOB — Global markets (~60% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **GLOB-001** | P2 | E2E non-US tickers | yfinance | `/global-markets` | `/global/*` | — | — | |
| **GLOB-002** | P3 | UK Companies House key | Enrich | registry/global | UK routes | — | — | UK_COMPANIES_HOUSE_KEY |

---

## SELF — Self-dealing (~65% → 100%)

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **SELF-001** | P2 | Genericize beyond NVIDIA demo | Any ticker/entity | `/self-dealing`, intel | `POST /intelligence/self-dealing` | — | — | |
| **SELF-002** | P2 | Cite SEC related-party footnotes | Parser | — | — | Relationship | GRAPH-007 | |

---

# Category 2 — Cross-cutting wiring & UX

## WIRE

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **WIRE-001** | P1 | Auth on every page that mutates | Audit all `fetch`/`apiFetch`; remove `demo_user` | All write pages | protected routes | — | AuthProvider | AUTH-004 |
| **WIRE-002** | P1 | Central API client only | No raw fetch without Bearer | all | — | — | `lib/api.js` | |
| **WIRE-003** | P1 | Machine FE↔BE URL audit | Fix 404 paths (watchlist/tracking mismatches) | broken pages | align paths | — | — | INFRA-012 |
| **WIRE-004** | P2 | Wire high-value unused APIs | Or delete dead routes | select pages | orphan routes | — | Prefer product value | |
| **WIRE-005** | P1 | Global no_data / error components | Consistent empty/error UI | all | — | — | — | |

## UX

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **UX-001** | P2 | Dark-blue finance theme | James request; clean layout | `_app`, global CSS | — | — | — | Design tokens |
| **UX-002** | P2 | Nav only shows working features | Hide stubs | layout/nav | — | — | — | BRK/NAR/PWA |
| **UX-003** | P2 | Money-flow visualization | Graph viz polish | `/network-graph` | graph APIs | — | — | Cytoscape |

---

# Category 3 — Tests, CI, verification

## TEST

| ID | Pri | What | How | Page | API | Schema | Wiring | Other |
|----|-----|------|-----|------|-----|--------|--------|-------|
| **TEST-001** | P0 | CI runs pytest | Fix failing tests or quarantine with ticket | — | — | — | — | INFRA-009 |
| **TEST-002** | P1 | E2E Playwright: login → portfolio → intel | Smoke against staging | key pages | — | — | — | |
| **TEST-003** | P1 | Re-audit after each phase | Re-run REQ matrix; update MASTER_TASK_STATUS | — | — | — | — | Honest % |
| **TEST-004** | P2 | Network-marked tests | `-m network` with keys in CI secrets | — | — | — | — | |
| **TEST-005** | P1 | Strict verification per feature | Checklist in this doc before closing IDs | — | — | — | — | |

---

# Category 4 — CEO / business decisions

## CEO

| ID | Pri | Decision | Blocks | Recommendation |
|----|-----|----------|--------|----------------|
| **CEO-001** | P3 | Plaid contract (~$500/mo?) | BRK-* | Defer until core 70%+ |
| **CEO-002** | P3 | GPU / RunPod budget | NAR-* | Defer; use hosted LLM in intel |
| **CEO-003** | P3 | Reddit API approval | SOC-001 | Apply now (free, slow) |
| **CEO-004** | P0 | Dedicated Postgres spend | PROD-002 | **Do immediately** |
| **CEO-005** | P3 | Push notifications (VAPID/Firebase) | PWA-* | Configure free VAPID or hide PWA |
| **CEO-006** | P1 | Recursion depth $ ceiling | GRAPH-004 | Depth 3 + monthly cap |
| **CEO-007** | P2 | People Data Labs / LinkedIn legal | OSINT depth | Prefer paid legal API over ToS-breaking scrapers |
| **CEO-008** | P2 | Private-market data (Caplight etc.) | Cap tables | After free source depth |

---

# Recommended execution order (task ID sequence)

## Phase A — Foundation (P0) → ~55%

1. **CEO-004** → **PROD-002** (own Postgres)  
2. **INFRA-001** (migrations)  
3. **INFRA-002** / **INTEL-001** (fresh DB intel)  
4. **GRAPH-001**, **GRAPH-002** (canonical + persist)  
5. **AUTH-001** / **INFRA-007** (auth dedupe)  
6. **CONS-001** (revisions import)  
7. **PROD-001**, **PROD-003**, **PROD-005** (deploy, restarts, disk)  
8. **PROD-012** / **QG-001**–**QG-002** (classifier)  
9. **TEST-001** (CI pytest)

## Phase B — Core product E2E → ~70%

10. **PROD-006** keys (Finnhub, FRED, SEC, LLM)  
11. **WIRE-001**, **WIRE-002**, **AUTH-004**  
12. **INTEL-002**–**INTEL-005**, **INTEL-003**  
13. **PF-001**, **ALERT-001**–**ALERT-004**  
14. **WS-001**, **INFRA-013**  
15. **RAG-001**, **RAG-002**  
16. **MACRO-001**, **EARN-001**, **IPO-001**  
17. **INFRA-004**, **INFRA-006**  
18. **TEST-002**, **TEST-003**

## Phase C — Depth & honesty → ~85%

19. **GOV-002**, **GRAPH-003**–**GRAPH-007**, **REG-001**  
20. **VAL-001**, **CMP-001**, **REV-001**–**REV-002**  
21. **WIRE-003**, **WIRE-005**, **UX-002** (hide stubs)  
22. **INFRA-005**, **INFRA-012**  
23. **SRC-005**, **PROD-008**, **PROD-009**  
24. **SELF-001**, **F13-*** polish  

## Phase D — 100% (includes CEO-gated)

25. **CEO-001**→**BRK-*** or permanently remove brokerage  
26. **CEO-002**→**NAR-*** or remove narrative-model page  
27. **CEO-003**→**SOC-001**; **CEO-005**→**PWA-***  
28. **UX-001**, **UX-003**  
29. **CRYPTO-*** if still in scope  
30. Final **TEST-003** audit: every REQ at 100% checklist  

---

# Connections & accounts to set up (inventory)

| Service | Env vars | Used by | Task |
|---------|----------|---------|------|
| PostgreSQL | `DATABASE_URL` | All persistence | PROD-002, INFRA-001 |
| Redis | `REDIS_URL` | Cache, worker, rate limit | INFRA-004, PROD-011 |
| Finnhub | `FINNHUB_API_KEY` | Earnings, IPO, consensus, guidance | MKT/EARN/IPO/CONS |
| FRED | `FRED_API_KEY` | Macro | MACRO-001 |
| SEC | `SEC_USER_AGENT` | Filings, Form 4, 13F | INS/F13/INTEL |
| OpenAI | `OPENAI_API_KEY` | RAG embeddings, some narrative | RAG/INTEL |
| Anthropic | `ANTHROPIC_API_KEY` | Judge / narrative | QG/INTEL |
| FMP | `FMP_API_KEY` | IPO fallback, comps | IPO/VAL |
| Congress.gov | `CONGRESS_API_KEY` | Legislation | GOV-002 |
| FEC | `FEC_API_KEY` | Political money | INTEL/GOV |
| Apollo | `APOLLO_API_KEY` | People/org enrich | INTEL-006 |
| SendGrid | `SENDGRID_API_KEY` | Email alerts | ALERT-002/003 |
| Twilio | `TWILIO_*` | SMS alerts | ALERT-002/003 |
| NewsAPI | `NEWSAPI_KEY` | M&A rumors | MA-001 |
| CourtListener | `COURTLISTENER_*` | Litigation | LIT-001 |
| Sentry | `SENTRY_*` / `NEXT_PUBLIC_SENTRY_DSN` | Monitoring | PROD-009 |
| Stripe | `STRIPE_*` | Billing | SRC-003 |
| Plaid | (future) | Brokerage | BRK-* |
| Reddit | (future) | Social | SOC-001 |
| VAPID/Firebase | (future) | Push | PWA-* |
| GPU/RunPod | (future) | Narrative model | NAR-* |

---

# Definition of 100%

Platform is **100%** only when:

1. Every feature in `PRODUCT_FEATURES_DOCUMENTATION.md` either:
   - passes the strict checklist at **Overall 100%**, **or**
   - is explicitly **removed from product nav** with CEO sign-off (stubs not counted as features).
2. Production checklist (Category 0) is all green.
3. Independent re-audit (TEST-003) confirms weighted REQ matrix = **100%** (or 100% of remaining in-scope REQs after CEO scope cuts).
4. No page advertises a capability that returns only stubs.
5. Migrations cover all models; dedicated DB; monitoring; backups.

---

# Quick ID index (all task IDs)

**PROD:** 001–012  
**INFRA:** 001–013  
**AUTH:** 001–005  
**WS:** 001–004  
**GOV:** 001–004  
**MKT:** 001–004  
**VAL:** 001–003  
**INTEL:** 001–008  
**GRAPH:** 001–007  
**PF:** 001–005  
**ALERT:** 001–006  
**F13:** 001–003  
**EARN:** 001 · **IPO:** 001 · **SHORT:** 001 · **INS:** 001  
**MACRO:** 001–003  
**CONS:** 001–004  
**VOL:** 001–004  
**CRYPTO:** 001–002  
**REG:** 001–003  
**RAG:** 001–004  
**QG:** 001–004  
**REV:** 001–004  
**LIT:** 001–003  
**SRC:** 001–005  
**CMP:** 001–002  
**MA:** 001–003  
**SOC:** 001–002  
**BRK:** 001–003  
**NAR:** 001–003  
**PWA:** 001–003  
**GLOB:** 001–002  
**SELF:** 001–002  
**WIRE:** 001–005  
**UX:** 001–003  
**TEST:** 001–005  
**CEO:** 001–008  

---

*Related: [`PRODUCT_FEATURES_DOCUMENTATION.md`](./PRODUCT_FEATURES_DOCUMENTATION.md) · `MASTER_TASK_STATUS.md` · [`guides/KT_HANDOVER_2026-10-05.md`](./guides/KT_HANDOVER_2026-10-05.md)*  
*Created for execution tracking. Update status in this file or link tickets to Task IDs.*
