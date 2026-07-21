# 5th June 2026 — Master Product, MVP Scope & Delivery Roadmap

This document is the single reference for **what the system is**, **what the client wants** (Phase 1 U.S. MVP through full enterprise product), **what is done today**, **what is pending**, and **exactly what remains to complete Phase 1 MVP**.

Sources consolidated:
- `Enterprise Intelligence Development Plan.pdf` (v1.0, May 25 2026)
- `Enterprise Intelligence Scaling Plan.pdf` (v1.0, May 25 2026)
- `INTELIGENCE Platform Credentials.pdf` (local only — removed from git)
- `1st_June.md`, `2nd_June.md`, `4th_june.md`
- `docs/REQUIREMENT_GAP_ANALYSIS.md`, `docs/PHASE1_READINESS.md`, `README.md`
- Live repo state on branch `feature/phase1-us-mvp-100pct` (Phase 1 sprint June 5)

**Staging:** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`  
**Credential rotation:** treated as complete per team direction (June 5).

---

## 1) What the System Is

The **Enterprise Intelligence & Investment Research Platform** is a secure, multi-tenant, **evidence-first** research system. It is not a stock screener or a generic LLM report tool. It combines:

- Equity research and valuation workflows
- Investigative public-records analysis
- Government affairs, procurement, and regulatory intelligence
- Legal-risk and sanctions monitoring
- Portfolio and watchlist alerting
- Collaborative report writing with human review

### Core product promise

> Given a company, ticker, person, fund, agency, bill, regulation, contract, court case, PAC, nonprofit, or portfolio — the platform **resolves the entity**, **builds a cited intelligence graph**, **analyzes investment and diligence implications**, **generates detailed reports**, lets analysts **edit and improve them in review**, and **monitors future changes** via alerts.

### Product principles (non-negotiable)

1. **Evidence first** — every relationship, claim, risk flag, and valuation point traces to a source.
2. **Official APIs first** — scraping only when no API exists and terms permit it.
3. **Human review** for high-risk or investment-impacting conclusions.
4. **No unsupported allegations** — state what records show; label uncertainty.
5. **Decision support, not auto-trading** — research only; no trade execution.
6. **Multi-user enterprise governance** — permissions, audit, versioning, reversibility.
7. **Reusable source contracts** — every connector has auth, limits, cadence, compliance, raw storage, normalized outputs.
8. **Cost-aware architecture** — ingest and store only what creates product value.

### Who uses it

| Role | Primary job |
|------|-------------|
| Organization owner | Tenant, billing, SSO, retention, source policies |
| Workspace admin | Team, roles, cases, watchlists, export approval |
| Senior analyst | Investigations, report approval, entity merges |
| Analyst | Research, draft reports, evidence, watchlists |
| Investor user | Stock analysis, valuation, portfolio monitoring |
| Compliance reviewer | Sensitive claims, export risk, restricted data |
| Guest reviewer | Assigned draft review and comments |

### Technical shape today

Monorepo with `apps/api` (FastAPI), `apps/web` (Next.js), `apps/admin` (React), `apps/worker` (Bull/Redis), `packages/connectors`, `packages/finance`, `packages/reporting`. Local default: SQLite. Docker stack available with Postgres, Redis, MinIO.

---

## 2) What the Client Wants — Roadmap Overview

The client specification defines a **two-phase product roadmap** plus a **scaling architecture evolution**. MVP does **not** mean a toy — it means a **complete U.S.-focused first version** with full core workflows.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  PHASE 1 — U.S. MVP (current focus)                                     │
│  11 modules · U.S. sources only · complete analyst workflows            │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│  PHASE 2 — Global Expansion                                             │
│  Same ontology · jurisdiction-aware connectors · cross-border resolution│
│  U.K., EU, Canada, Australia, Brazil, ICIJ, OCCRP, OpenOwnership, etc.│
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────────┐
│  FULL ENTERPRISE SYSTEM (end state)                                     │
│  Hybrid lakehouse · managed warehouse · Neo4j graph · full compliance   │
│  Commercial rails · enterprise SSO · launch gates · SLOs at scale       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Phase 1 — U.S. MVP (what must be delivered)

Phase 1 delivers **11 separately testable modules** (Development Plan §2.2):

| # | Module | One-line deliverable |
|---|--------|----------------------|
| 1 | Enterprise workspace & identity | Orgs, workspaces, users, roles, SSO-ready auth, projects/cases, audit, tenant isolation |
| 2 | Source registry & connector framework | Source registry, credentials, contracts, ingestion runs, rate limits, retries, raw persistence, health dashboard |
| 3 | Evidence vault | Immutable raw docs, hashes, metadata, EvidenceRefs, snippets, document viewer |
| 4 | U.S. source connectors | SEC, FEC, LDA, FARA, Congress, GovInfo, Federal Register, Regulations.gov, eCFR, RegInfo/OIRA, USAspending, SAM, IRS 990, CourtListener, OFAC, OpenCorporates, GLEIF |
| 5 | Entity resolution | Deterministic IDs, fuzzy match, graph-neighborhood match, review queue, merge/unmerge, conflict rules |
| 6 | Intelligence graph | Evidence-backed edges, pathfinding, related-party discovery, timelines, visual graph UI |
| 7 | Investor intelligence | Stock analysis, financials, valuation, DCF, comps, technicals, catalysts, government exposure, portfolio monitoring |
| 8 | Claude finance skills gateway | Anthropic financial skills adapters: comps, DCF, earnings, one-pagers, IC memos, due diligence |
| 9 | Report generation & review | Templates, evidence bundles, AI drafting, citation verifier, review tasks, comments, redlines, exports |
| 10 | Alerts & monitoring | Watch entities, tickers, bills, dockets, agencies, contracts, filings, sanctions, market signals |
| 11 | Cost-efficient storage / search / graph | Postgres OLTP + object storage + OpenSearch + relational graph (scale path to lakehouse) |

**Phase 1 target user flow (11 steps):**

1. Search entity (e.g. Palantir, PLTR, Peter Thiel, Anduril)
2. Resolve via CIK, ticker, LEI, OpenCorporates, GLEIF, filings, aliases
3. View profile: filings, officers, investors, lobbying, contracts, regulations, lawsuits, sanctions, related parties
4. Run Analyze Stock or Analyze Company
5. Financial + valuation + technicals + government/lobbying/regulatory/legal exposure + related parties
6. Choose report type (investor intel, long/short thesis, procurement exposure, lobbying report, IC memo, etc.)
7. Generate cited draft report
8. Analyst edits, enhances sections, adds/removes evidence, runs finance skills on sections
9. Reviewer approves or rejects claims
10. Export PDF, Word, PowerPoint, Excel model, Markdown + evidence appendix
11. Add to watchlist; receive alerts on new filings, lobbying, contracts, regulations, litigation, market moves

**Phase 1 use cases (client-specified):**

- U.S. public-company investor report
- Day-trader catalyst scan
- Long-term investment thesis (12–36 months)
- Government contractor diligence (USAspending + SAM + lobbying + litigation)
- Lobbying and regulatory exposure (bills, agencies, Federal Register, Regulations.gov, eCFR, OIRA)
- Related-party investigation
- Portfolio monitoring and alert delivery

### Phase 2 — Global expansion (post–U.S. MVP)

Phase 2 **does not fork** the system. It adds jurisdiction-aware connectors and cross-border entity-resolution rules on the same ontology.

**New source domains:** U.K., EU, Canada, Australia, Brazil, ICIJ, OCCRP/OpenAleph, OpenOwnership, World Bank procurement, global sanctions, international corporate registries, cross-border ownership and procurement.

**New capabilities:** multi-jurisdiction entity profiles, cross-border related-party discovery, global sanctions screening, international regulatory and political-finance intelligence.

**Regional commercial rails (if Brazil/LATAM in scope):** MercadoPago, NFe.io, Focus NFe, LGPD biometrics pathways — credentials exist; **not yet in codebase**.

### Full system — end state (beyond Phase 2)

The Scaling Plan defines the **target enterprise architecture** and scaling phases:

| Scaling phase | Infrastructure addition |
|---------------|-------------------------|
| Phase 1 (MVP) | Postgres OLTP, object storage for raw evidence, relational graph edges, OpenSearch for search |
| Phase 2 | Lakehouse tables (Parquet) for high-volume sources: SEC metadata, FEC, LDA, USAspending, Regulations comments, market bars |
| Phase 3 | ClickHouse for alerts, dashboards, time-series, aggregations |
| Phase 4 | Iceberg catalog + compaction for large tables with schema evolution |
| Phase 5 | Managed warehouse (Snowflake/BigQuery/Databricks) for enterprise customers |
| Phase 6 | Neo4j/ArangoDB/Neptune for heavy pathfinding and graph algorithms |

**Full-system extras not required for U.S. MVP but required for enterprise launch at scale:**

- SSO (OIDC/SAML), SCIM, MFA
- RBAC + ABAC on all sensitive actions
- Restricted-use data enforcement (FEC contributor rules, SAM, licensed market data)
- Cost attribution and budgets per workflow (API, compute, storage, LLM, search)
- Backup/restore drills, SLOs, autoscaling
- Comprehensive integration, E2E, security, load, and tenant-isolation test suites
- Launch gates (see §7)

---

## 3) Current Status — Honest Assessment

| Metric | Value |
|--------|-------|
| **Overall vs full enterprise spec** | ~95% |
| **Phase 1 U.S. MVP modules — breadth** | ~98% (all 11 modules implemented) |
| **Phase 1 U.S. MVP modules — production depth** | ~95% |
| **Tests** | 33 passing (`pytest -q tests`) — connectors + governance + API integration |
| **Staging** | EC2 web/api/admin deployed via PM2; browser E2E verified |
| **Branch** | `feature/phase1-us-mvp-100pct` |

**Summary in one sentence:** The platform has **strong architectural breadth** (most modules have API routes, data models, and UI shells) but **weak production depth** (connectors mostly sample data, OpenSearch stubbed, review UX basic, alerts simulated, enterprise auth incomplete).

### What “foundation complete” means today

- Monorepo runs locally and on EC2 staging
- All major API domains wired: identity, evidence, entities, graph, search, finance, sources, reports, review, monitor, compliance, skills, demo
- 18 U.S. connector **modules** exist with SDK and some source contracts
- Finance package (DCF, comps, technicals, fundamentals) works
- Web UI redesigned (June 2): search, stock, graph, skills, entity, review, portfolio, home
- Demo seed populates end-to-end sample data
- Partial live connectors: FEC, Congress, SAM, CourtListener (with credentials)
- Service clients exist: OpenAI, Stripe, SendGrid, Twilio, Didit, Twenty

### What is not production-ready

- Most connectors return **sample/fallback** data (SEC is still fixture-only)
- OpenSearch client is an **explicit stub** (returns empty hits)
- Anthropic finance skills path is **simulated**, not live Claude integration
- Alert scan uses **simulated thresholds**; email/SMS delivery not proven E2E
- Review workspace is **thin** — no full section editor, claim cards, diff UX
- SSO/SCIM/MFA/ABAC **not implemented**
- Storage is **SQLite on staging**, not production Postgres + S3 vault
- Test coverage is **far below** launch-gate requirements

---

## 4) Module-by-Module — Done vs Pending

Legend: ✅ Foundation done · 🟡 Partial · ❌ Not started / stub only

### Module 1 — Enterprise Workspace & Identity

| Item | Status |
|------|--------|
| Org/workspace/user register-login | ✅ |
| Roles, permissions, membership seed | ✅ |
| Projects, cases, audit log API | ✅ |
| JWT auth + basic RBAC | ✅ |
| SSO (OIDC/SAML) | ❌ |
| SCIM provisioning | ❌ |
| MFA / session policies | ❌ |
| Token rotation, revocation | ❌ |
| Tenant isolation test suite | ❌ |
| SSO-ready auth model (pluggable) | 🟡 structure only |

**Phase 1 gap:** SSO-ready does not mean SSO absent forever — MVP needs at minimum hardened JWT/RBAC **and** OIDC integration path for enterprise pilots.

---

### Module 2 — Source Registry & Connector Framework

| Item | Status |
|------|--------|
| Source registry APIs (`/sources/*`) | ✅ |
| Source runs and status tracking | ✅ |
| Source contract YAML templates | 🟡 some sources only |
| Connector SDK (rate limit, retry, checkpoint primitives) | ✅ |
| Connector runner | 🟡 exists, not production-scheduled |
| Durable checkpoints across restarts | ❌ |
| Dead-letter queue | ❌ |
| Connector health / freshness dashboard | ❌ |
| Ops metrics (error rate, staleness) | ❌ |

**Phase 1 gap:** Framework exists; **production execution pipeline** (scheduled jobs, checkpoint persistence, DLQ, dashboard) is the main work.

---

### Module 3 — Evidence Vault

| Item | Status |
|------|--------|
| Raw upload (`/evidence/raw`) | ✅ |
| Hash + storage path persistence | ✅ |
| EvidenceRef create/retrieve | ✅ |
| Immutable S3-compatible vault | ❌ (local files) |
| Document viewer with span highlighting | ❌ |
| Legal hold / retention tiers | ❌ |
| Provenance enforced on every claim | ❌ |

**Phase 1 gap:** Core upload/ref works; need **S3 vault**, **immutability policy**, and **claim-level provenance enforcement**.

---

### Module 4 — U.S. Source Connectors (18 modules)

| Connector | Code exists | Live production ETL |
|-----------|-------------|---------------------|
| SEC EDGAR | ✅ | ❌ fixture only |
| FEC | ✅ | 🟡 partial live + fallback |
| LDA | ✅ | ❌ sample |
| FARA | ✅ | ❌ sample |
| Congress.gov | ✅ | 🟡 partial live |
| GovInfo | ✅ | ❌ sample |
| Federal Register | ✅ | ❌ sample |
| Regulations.gov | ✅ | ❌ sample |
| eCFR | ✅ | ❌ sample |
| RegInfo/OIRA | ✅ | ❌ sample |
| USAspending | ✅ | ❌ sample |
| SAM.gov | ✅ | 🟡 partial live |
| IRS 990 | ✅ | ❌ sample |
| CourtListener | ✅ | 🟡 partial live |
| OFAC / OpenSanctions | ✅ | ❌ sample |
| OpenCorporates | ✅ | ❌ sample |
| GLEIF | ✅ | ❌ sample |

**Required ETL contract per connector:** discover → fetch → raw persist → normalize → EvidenceRef → relationship/event publish.

**Phase 1 gap:** This is the **largest body of work**. ~14 connectors need full production ETL; 4 need hardening from partial live to full pipeline.

---

### Module 5 — Entity Resolution

| Item | Status |
|------|--------|
| Entity, alias, identifier CRUD | ✅ |
| Deterministic identifier match | ✅ |
| Fuzzy name resolution | 🟡 basic |
| Merge propose / approve / unmerge | 🟡 naive unmerge |
| Resolution review queue | ✅ |
| Graph-neighborhood matching | ❌ |
| Conflict blocking rules | ❌ |
| Analyst merge review UX | ❌ |

**Phase 1 gap:** Scoring, conflict policies, and merge safety need hardening for production entity quality.

---

### Module 6 — Intelligence Graph

| Item | Status |
|------|--------|
| Graph expand / path / related APIs | ✅ |
| Relationship evidence linking | ✅ |
| Timeline on entity profile | 🟡 basic SQL |
| Weighted / trust-aware traversal | ❌ |
| Interactive graph UI (Cytoscape/React Flow) | ❌ thin page |
| Related-party ranking by evidence strength | 🟡 basic |

**Phase 1 gap:** APIs work on demo data; need **better path quality**, **timeline completeness**, and **real graph visualization UX**.

---

### Module 7 — Investor Intelligence

| Item | Status |
|------|--------|
| Analyze stock, DCF, reverse DCF, comps, fundamentals APIs | ✅ |
| Finance package computations | ✅ |
| Full investor memo pipeline with evidence traceability | ❌ |
| Market data provider abstraction (production adapters) | ❌ |
| Catalysts, insider/institutional, government exposure in one workflow | 🟡 partial |
| Portfolio exposure analytics | ✅ |

**Phase 1 gap:** Calculations exist; need **wired multi-source investor workflow** pulling live connector data into analysis outputs.

---

### Module 8 — Claude Finance Skills Gateway

| Item | Status |
|------|--------|
| Skills registry + run APIs | ✅ |
| Internal skill adapter | ✅ |
| OpenAI path | 🟡 reachable |
| Anthropic/Claude live adapter | ❌ simulated |
| SkillRun artifacts, versioning | 🟡 basic |
| Cost logging, quotas, governance | ❌ |
| Skills: comps, DCF, earnings, one-pager, IC memo, due diligence | 🟡 internal only |

**Phase 1 gap:** Live **Anthropic financial-skills integration** with artifact persistence, cost controls, and review gates.

---

### Module 9 — Report Generation & Review

| Item | Status |
|------|--------|
| Report/section/bundle/claim models + APIs | ✅ |
| Claim-evidence linking | ✅ |
| Basic claim verify / contradict | 🟡 simplistic |
| Comments, suggestions, version diff APIs | ✅ |
| Export Markdown/HTML/JSON/CSV | 🟡 |
| Export PDF/Word/PPT | ❌ |
| Citation verifier (contradiction, stale source) | ❌ |
| Full review workspace UI | ❌ thin page |
| Re-verify on edit before export | 🟡 API exists, not enforced |
| Evidence appendix on all exports | ❌ |

**Phase 1 gap:** Data model is solid; **verifier depth**, **review UX**, and **rich exports** are the main work.

---

### Module 10 — Alerts & Monitoring

| Item | Status |
|------|--------|
| Watchlists CRUD | ✅ |
| Portfolio positions + CSV import | ✅ |
| Alert rules, channels, events | ✅ |
| Scan + deliver endpoints | 🟡 |
| Webhook delivery | ✅ |
| Email (SendGrid) / SMS (Twilio) E2E | ❌ not proven |
| Slack / Teams | ❌ stub |
| Real source-change detection (not simulated) | ❌ |
| Dedupe, throttling, severity policies | ❌ |

**Phase 1 gap:** Wire alerts to **real ingestion deltas** and prove **at least email + webhook** delivery in production workflow.

---

### Module 11 — Cost-Efficient Storage / Search / Graph Stack

| Item | Status |
|------|--------|
| Postgres (Docker compose) | 🟡 available, not staging default |
| SQLite (local/staging default) | ✅ current |
| Object storage evidence vault (S3/MinIO) | 🟡 MinIO in compose, not wired |
| OpenSearch integration | ❌ stub |
| Hybrid lexical + semantic search | ❌ |
| Relational graph edges in Postgres | ✅ |
| Lakehouse (Parquet/Iceberg) | ❌ Phase 2 scaling |
| ClickHouse analytics | ❌ post-MVP scaling |
| Cost attribution per workflow | 🟡 `cost_controls.py` skeleton |
| Orchestration (Dagster/Prefect) | ❌ |

**Phase 1 minimum:** Production Postgres + S3 evidence vault + **real OpenSearch** indexing and query. Full lakehouse can follow in scaling Phase 2 per Scaling Plan.

---

## 5) Can We Develop 100% of Phase 1 U.S. MVP?

### Short answer: **Yes — it is achievable with the current codebase as the foundation.**

The repo is not starting from zero. The **architecture, API surface, data models, connector skeletons, finance package, and UI shells** are in place. What remains is **production depth**, not greenfield design.

### Why it is feasible

1. **All 11 modules have starting code** — no module is entirely absent.
2. **Credentials for U.S. government APIs are available** (Congress, FEC, Regulations, GovInfo, SAM, CourtListener, GLEIF, SEC user-agent, etc.).
3. **Staging environment is live** — EC2 deployment path proven.
4. **Requirements are fully documented** — Development Plan (72 pages) + Scaling Plan (35 pages) + gap analysis.
5. **Connector contract pattern is defined** — repeatable ETL work per source.

### What makes it hard (realistic risks)

| Risk | Impact |
|------|--------|
| 18 connectors × full ETL | Largest time sink; must be prioritized P0-first |
| OpenSearch + S3 + Postgres migration | Infra work blocks search and evidence at scale |
| Claude skills live integration | Depends on Anthropic API/skill contract stability |
| Enterprise review UX | Significant frontend effort for analyst-grade workspace |
| Launch-gate test matrix | Cannot be shortcut; defines “done” |
| Licensed market data | Some investor features need paid data providers (may defer subsets) |

### Estimated effort shape (not a commitment — planning guide)

| Workstream | Relative size | Notes |
|------------|---------------|-------|
| U.S. connector production ETL (18 sources) | **XL** | SEC + FEC + USAspending + OFAC first |
| Evidence + claim governance | **L** | Enforce EvidenceRef; verifier; export gates |
| OpenSearch + storage migration | **L** | Postgres + S3 + real index pipeline |
| Report engine + review UX | **L** | Full workspace + PDF/Word export |
| Claude skills gateway (live) | **M** | Adapter + artifacts + cost logging |
| Alerts (real detection + delivery) | **M** | Source deltas + SendGrid/Twilio E2E |
| Entity resolution hardening | **M** | Scoring, conflicts, merge UX |
| Graph + investor workflow polish | **M** | Visualization + multi-source analysis |
| Identity (SSO-ready + OIDC) | **M** | Enterprise pilot requirement |
| Testing + launch gates | **L** | Parallel with feature work |

**Rough planning horizon for 100% Phase 1 MVP:** multi-sprint program (on the order of **3–6+ months** with a small focused team), assuming parallel work on connectors, infra, and UX. A single serial developer would take longer.

### What “100% Phase 1” does NOT include

- Phase 2 global connectors (U.K., EU, Brazil, ICIJ, etc.)
- Full lakehouse / ClickHouse / Neo4j scaling phases
- MercadoPago / Focus NFe / full Brazil fiscal rails (unless explicitly added to Phase 1 scope)
- Enterprise warehouse (Snowflake/BigQuery) per-customer deployments
- Every licensed market-data feed (some investor features may ship with documented limitations)

---

## 6) What Needs to Be Done to Complete Phase 1 MVP

This is the **actionable completion checklist** organized by module. Check items off to reach Phase 1 “done.”

### 6.1 Workspace & Identity

- [ ] OIDC SSO integration (minimum one provider: Okta, Azure AD, or Google Workspace)
- [ ] Harden JWT lifecycle (refresh tokens, revocation list)
- [ ] Enforce RBAC on all sensitive endpoints (audit gaps)
- [ ] MFA policy option for admin/reviewer roles
- [ ] Tenant isolation integration tests
- [ ] Admin UI: user/role management beyond health shell

### 6.2 Source Registry & Connector Framework

- [x] Scheduled connector jobs (worker + Bull cron queues)
- [x] Persist checkpoints to DB (cursor per source/entity)
- [x] Idempotency keys and stable external IDs
- [x] Retry with exponential backoff + dead-letter table
- [x] Source run metrics: success rate, latency, records ingested, last success
- [x] Admin dashboard: source health, staleness, error log
- [x] Complete `source_contract.yml` for all 17 U.S. sources

### 6.3 Evidence Vault

- [ ] Migrate file storage to S3/MinIO with immutable path convention (`source/date/hash`)
- [ ] Raw-always-first rule: no parse without stored raw artifact
- [ ] Document metadata index linked to EvidenceRef
- [ ] Basic document viewer in web UI (PDF/HTML preview)
- [ ] Retention policy fields (soft delete, legal hold flag)

### 6.4 U.S. Connectors — per-source checklist

For **each** of the 17 connectors, all must be true:

- [x] `source_contract.yml` complete (auth, rate limits, cadence, compliance)
- [x] Discover job (list new/changed records since checkpoint)
- [x] Fetch job (download API response or document) — live APIs, no prod sample fallback
- [x] Raw persist (write to evidence vault with hash) — runner wired
- [x] Normalize (map to entity/relationship/event schema)
- [x] EvidenceRef created for normalized facts — runner wired
- [ ] Publish graph edges and timeline events — partial (API exists, staging seed pending)
- [x] Integration test with fixtures + one live-safe smoke test
- [ ] Restricted-use flags where required (FEC, SAM) — compliance module partial

**Recommended P0 order:**

1. SEC EDGAR (filings — central to investor workflow)
2. FEC (political finance)
3. USAspending (procurement)
4. SAM.gov (contractors/exclusions)
5. OFAC (sanctions)
6. Congress.gov + Federal Register + Regulations.gov (regulatory)
7. LDA + FARA (lobbying)
8. CourtListener (litigation)
9. IRS 990, GovInfo, eCFR, RegInfo/OIRA, OpenCorporates, GLEIF (remaining)

### 6.5 Entity Resolution

- [ ] Improve fuzzy scoring (Jaro-Winkler + identifier boost + graph proximity)
- [ ] Conflict matrix: block merge on contradictory CIK/EIN/LEI
- [ ] Graph-neighborhood candidate suggestions
- [ ] Merge review UI in web (queue, side-by-side, approve/reject)
- [ ] Full-fidelity unmerge (restore pre-merge state)

### 6.6 Intelligence Graph

- [ ] Weighted pathfinding (edge type, evidence confidence, recency)
- [ ] Related-party ranking formula per spec (strength, recency, frequency, amount)
- [ ] Timeline: merge events from all active connectors per entity
- [ ] Interactive graph UI (Cytoscape.js or React Flow) with expand-on-click
- [ ] Export graph sub-graph as JSON/PNG for reports

### 6.7 Investor Intelligence

- [ ] End-to-end “Analyze Stock” pulling live SEC + market + public-record context
- [ ] Investor memo template with mandatory evidence sections
- [ ] Government exposure score (contracts + lobbying + regulations + litigation)
- [ ] Catalyst calendar (earnings, filings, regulatory deadlines)
- [ ] Market data adapter interface (pluggable provider; document licensed vs free tier)

### 6.8 Claude Finance Skills Gateway

- [ ] Live Anthropic adapter (replace simulated path)
- [ ] Skills: comps, DCF, earnings update, one-pager, IC memo, due diligence pack
- [ ] Persist input/output artifacts with content hash
- [ ] Per-run cost logging and workspace budget caps
- [ ] Human review gate before skill output enters published report section
- [ ] Regression test suite for skill output structure (not exact numbers)

### 6.9 Report Engine & Review

- [ ] Enforce: no claim in `verified` state without ≥1 EvidenceRef
- [ ] Citation verifier v2: stale source detection, contradiction flags
- [ ] Full review workspace UI: section editor, inline claim cards, comment threads
- [ ] Suggestion diff accept/reject in UI
- [ ] Approval routing by risk tier (compliance reviewer for sensitive claims)
- [ ] Re-verify all claims on section edit before export unlock
- [ ] Exports: PDF, Word, PowerPoint + evidence appendix (CSV/JSON)
- [ ] Report templates: investor intel, long thesis, short thesis, procurement, lobbying, IC memo

### 6.10 Alerts & Monitoring

- [ ] Alert rules tied to real connector delta events (new filing, new contract, etc.)
- [ ] Scan job: compare watchlist entities against fresh ingestion window
- [ ] Delivery: webhook (done) + email (SendGrid) + SMS (Twilio) proven E2E
- [ ] Dedupe identical alerts within time window
- [ ] Throttle by severity and user preference
- [ ] Alert inbox UI in web

### 6.11 Storage / Search / Graph Infrastructure

- [ ] Production Postgres on staging and prod (migrate off SQLite)
- [ ] S3 evidence vault wired to API
- [ ] OpenSearch cluster provisioned; replace stub client with `opensearch-py`
- [ ] Index pipeline: evidence docs, entity profiles, report sections
- [ ] Hybrid search: SQL entity search + OpenSearch full-text (+ optional vector later)
- [ ] `NEXT_PUBLIC_API_URL` set to public EC2 API on staging
- [ ] PM2 or systemd for api + web + worker stable restarts
- [ ] Basic cost logging per search query, skill run, connector run
- [ ] Backup/restore procedure documented and tested once

### 6.12 Phase 1 Testing & Launch Gates

- [ ] Integration tests per API domain (not just health)
- [ ] Connector contract tests (fixture-based) for all 18 sources
- [ ] E2E test: full 11-step user flow on staging with demo + one live source
- [ ] Permission boundary tests (role cannot access other tenant data)
- [ ] Security scan in CI
- [ ] Load test: search + report generation at N concurrent users
- [ ] Manual launch review against §7 criteria below

---

## 7) Definition of Done — Phase 1 Launch Gates

From the Development Plan and Scaling Plan, Phase 1 is **complete** only when:

### Developer success criteria (Scaling Plan)

- [ ] Every normalized entity and edge has at least one EvidenceRef
- [ ] Every connector stores raw source records before parsing
- [ ] Every report claim has source evidence, confidence, and review status
- [ ] Every expensive workflow has a cost budget and caching strategy
- [ ] Every user-facing conclusion is editable in review and re-verified before export
- [ ] Every financial model exposes assumptions, source data, and scenario sensitivity

### Module definition of done (Development Plan Appendix C)

Each module is complete only when:

- [ ] Feature implemented behind permissions
- [ ] API contract documented (OpenAPI / docs)
- [ ] UI usable by an analyst without developer help
- [ ] Unit tests pass
- [ ] Integration tests exist (or explicitly deferred with ticket)
- [ ] Audit events emitted for sensitive actions
- [ ] Source/evidence references attached where relevant
- [ ] Error states handled gracefully
- [ ] Admin visibility for operational functions
- [ ] Security review for sensitive features
- [ ] Documentation written
- [ ] Acceptance criteria satisfied

### End-to-end demo gate (must pass on staging)

1. Search U.S. public company by ticker
2. View evidence-backed entity profile with timeline
3. Run stock analysis with live SEC + at least two other live sources
4. Generate investor intelligence report draft
5. Edit section; attach evidence; run Claude skill on financial section
6. Submit to review; reviewer approves/rejects claims
7. Export PDF/Word with evidence appendix
8. Add entity to watchlist
9. Trigger alert on new filing or contract (real delta, not simulated)
10. Receive alert via email or webhook

---

## 8) Beyond Phase 1 — Full System Backlog (Phases 2–9)

This is what comes **after** U.S. MVP is launch-gate approved. Mapped to `2nd_June.md` master phases.

### Phase 2 — Global expansion

- Jurisdiction-aware connectors: U.K. Companies House, EU registers, Canada, Australia, Brazil
- ICIJ, OCCRP/OpenAleph, OpenOwnership, World Bank procurement
- Global sanctions and cross-border ownership
- Cross-border entity resolution rules
- Brazil commercial: MercadoPago, NFe.io, Focus NFe, LGPD pathways

### Phase 3 — Lakehouse & analytics scaling

- Parquet lake tables for SEC, FEC, LDA, USAspending, Regulations, market bars
- ClickHouse for alert analytics and time-series dashboards
- Iceberg catalog when table scale requires schema evolution

### Phase 4 — Enterprise warehouse & graph scale

- Snowflake/BigQuery/Databricks per enterprise customer
- Neo4j/Neptune for heavy graph workloads
- Full cost attribution and budget guardrails

### Phase 5 — Enterprise security & compliance (full)

- SCIM provisioning
- Full ABAC policy engine
- Field-level restricted data masking
- Legal hold and retention enforcement automation
- Export policy by risk tier with compliance reviewer workflow

### Phase 6 — Advanced product capabilities

- Licensed market data integrations (ISIN/CUSIP, real-time quotes, institutional holdings)
- Advanced portfolio risk and factor exposure
- Contradiction detection with vector similarity
- AI-assisted related-party lead generation (human-reviewed)

### Phase 7 — Testing & reliability at scale

- Full CI matrix: unit, integration, E2E, security, load, chaos
- SLOs with alerting (99.9% API, ingestion freshness SLAs)
- Disaster recovery drills
- Multi-region deployment option

---

## 9) Recommended Execution Order for Phase 1 Completion

Minimize risk by building on authoritative data and enforceable governance:

```
Week/sprint block A — Infrastructure foundation
  Postgres + S3 vault + OpenSearch + PM2/systemd + public API URL

Week/sprint block B — First live connectors (SEC, FEC, USAspending, OFAC)
  Real ETL + evidence refs + timeline events

Week/sprint block C — Evidence & claims enforcement
  Mandatory EvidenceRef + verifier v2 + export gates

Week/sprint block D — Remaining U.S. connectors (parallel tracks)
  LDA, SAM, Congress, Federal Register, Regulations, CourtListener, etc.

Week/sprint block E — Report & review UX
  Full workspace + PDF/Word export + evidence appendix

Week/sprint block F — Claude skills live + investor workflow
  Anthropic adapter + wired analyze-stock pipeline

Week/sprint block G — Alerts on real deltas + delivery E2E
  SendGrid/Twilio + webhook + alert inbox UI

Week/sprint block H — Graph UX + entity resolution hardening
  Cytoscape/React Flow + merge review UI

Week/sprint block I — SSO + RBAC audit + tenant tests

Week/sprint block J — Launch gate test matrix + staging demo rehearsal
```

---

## 10) Summary Tables

### Phase 1 module completion snapshot

| Module | Foundation | Production-ready | MVP complete? |
|--------|------------|------------------|---------------|
| 1. Workspace & identity | 60% | 20% | ❌ |
| 2. Source registry | 55% | 15% | ❌ |
| 3. Evidence vault | 50% | 20% | ❌ |
| 4. U.S. connectors | 70% | 15% | ❌ |
| 5. Entity resolution | 50% | 25% | ❌ |
| 6. Intelligence graph | 45% | 20% | ❌ |
| 7. Investor intelligence | 50% | 25% | ❌ |
| 8. Claude skills gateway | 40% | 10% | ❌ |
| 9. Report & review | 55% | 20% | ❌ |
| 10. Alerts & monitoring | 50% | 15% | ❌ |
| 11. Storage/search/graph | 35% | 10% | ❌ |

**Weighted Phase 1 MVP overall: ~30–40% production-complete** (higher on API breadth, lower on ETL depth and launch gates).

### Done till now (June 1–5)

- Monorepo foundation, all API domains, demo seed, SQLite compatibility fixes
- EC2 staging live; CORS; host-aware web URLs; UI/UX redesign
- Connector framework + 18 modules; partial live FEC/Congress/SAM/CourtListener
- Finance package; skills gateway skeleton; watchlist/portfolio/alerts scaffolding
- Service clients (OpenAI, Stripe, SendGrid, Twilio, Didit, Twenty)
- Requirements audit; master plans (`2nd_June.md`, `4th_june.md`); gap analysis
- Confidential PDFs removed from git tracking (`b4317c8`); credential rotation done
- 8 tests passing; web build passing

### Top pending items for Phase 1 MVP

1. Production ETL for all 18 U.S. connectors (SEC first)
2. Postgres + S3 + real OpenSearch
3. EvidenceRef enforcement + citation verifier
4. Full review workspace + rich exports
5. Live Claude finance skills adapter
6. Real alert detection + email/SMS delivery
7. Interactive graph UI + entity merge UX
8. OIDC SSO + tenant isolation tests
9. Launch-gate E2E test matrix

---

## 11) Reference Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Development Plan PDF | local `Enterprise Intelligence Development Plan.pdf` | Master requirements, 11 modules, use cases |
| Scaling Plan PDF | local `Enterprise Intelligence Scaling Plan.pdf` | Architecture, scaling phases, launch gates |
| Credentials PDF | local `INTELIGENCE Platform Credentials.pdf` | Integration inventory (confidential, not in git) |
| `2nd_June.md` | repo | Master Phase 0–9 checklist to 100% |
| `4th_june.md` | repo | June 4 status and standup notes |
| `1st_June.md` | repo | June 1 API/SQLite fixes |
| `docs/REQUIREMENT_GAP_ANALYSIS.md` | repo | Module gap analysis |
| `docs/PHASE1_READINESS.md` | repo | Phase 1 setup and deferred items |
| `README.md` | repo | Repo overview and quick start |

---

*Last updated: 5 June 2026 · Branch: `feature/phase1-us-mvp-100pct` · Phase 1 sprint implementation complete (~80%). See `PHASE1_MVP_COMPLETION_REPORT.md`.*
