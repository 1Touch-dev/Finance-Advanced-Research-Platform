# 10th June 2026 — Status, Boss Direction & Next Engineering Phase

**Purpose:** Single handoff doc after James’s 9–10 June messages — what the system is today, what was completed since 5 June, what remains, and the **new company-registry strategy** (replace paid OpenCorporates with free U.S. state sources).

**Staging:** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`  
**Branch:** `feature/phase1-us-mvp-100pct` · PR [#1](https://github.com/1Touch-dev/Finance-Advanced-Research-Platform/pull/1)

---

## 1) Executive summary (10 June)

| Area | Status |
|------|--------|
| **Phase 1 U.S. MVP (core)** | **Operational on staging** — search, graph, stock analysis, skills, alerts, portfolio, admin, reports |
| **17 government connectors** | **17/17 success** with persisted records (as of 8 June) |
| **Anthropic / Claude skills** | **Live** — `claude-sonnet-4-6`, skills + stock `ai_narrative` verified |
| **OpenAI skills** | Live (fallback) |
| **Google SSO (OIDC)** | Code wired; **credentials still empty** in `.env` |
| **OpenCorporates** | **No paid key** — connector uses **SEC public registry fallback** today |
| **James’s new priority** | **Replace OpenCorporates** with **free U.S. state registry connectors** (bulk/API first, scrape where needed); **Cobalt Intelligence** only as **paid per-use third fallback**; eventual **paid API product** for registry data |

---

## 2) What James said (9–10 June) — captured requirements

### 2.1 Cheaper alternative to OpenCorporates

- OpenCorporates Essentials is **~£2,250/year** — too expensive for MVP.
- **Direction:** Use **free official U.S. sources** first; go **state by state**.
- Data shape is **similar across states** (entity name, ID, status, address, officers where available) — good for a unified normalized schema and a future **commercial registry API**.

### 2.2 Implementation strategy (James-approved)

1. **Primary:** Free bulk downloads / open data APIs / official search endpoints per state.
2. **Secondary:** Engineering **scrapers** (Puppeteer or similar) where no API exists — terms and rate limits must be respected.
3. **Tertiary fallback:** **Cobalt Intelligence** Secretary of State API — **per-use credits**, not primary ingestion.
4. **Product vision:** Ingest once, normalize, expose as **our own paid API** later (registry-as-a-service).

### 2.3 Priority states to start (best bulk/API coverage)

James flagged these as **first wave**:

| State | Why start here | James’s links |
|-------|----------------|---------------|
| **New York** | Active corporations bulk CSV/JSON on data.ny.gov | [Dataset](https://catalog.data.gov/dataset/active-corporations-beginning-1800) · [CSV](https://data.ny.gov/api/views/n9v6-gdp6/rows.csv?accessType=DOWNLOAD) · [JSON](https://data.ny.gov/api/views/n9v6-gdp6/rows.json?accessType=DOWNLOAD) |
| **Colorado** | Socrata bulk + transaction history | [Entities](https://data.colorado.gov/Business/Business-Entities-in-Colorado/4ykn-tg5h) · [Transactions](https://data.colorado.gov/Business/Business-Entity-Transaction-History/casm-dbbj) |
| **Florida** | Sunbiz data downloads | [Data downloads](https://dos.fl.gov/sunbiz/other-services/data-downloads/) |
| **Oregon** | Active businesses open data | [Active Businesses ALL](https://data.oregon.gov/business/Active-Businesses-ALL/tckn-sxa6/data) |
| **Washington** | Corporation search API | [Search API](https://finditconsumer.wa.gov/corps/searchapi.aspx) |
| **Texas** | Franchise tax account status + API docs | [Search](https://comptroller.texas.gov/taxes/franchise/account-status/search) · [API docs](https://api-doc.comptroller.texas.gov/) |

**National directory:** [NASS corporate registration hub](https://www.nass.org/business-services/corporate-registration) — index to all 50 SOS sites.

James also provided **all 50 state SOS search URLs** (AL–WY + DC) for scrape/API discovery — treat as the master checklist for Phase 1b registry expansion.

### 2.4 Free enrichment (already partially in platform)

| Source | Role | Platform today |
|--------|------|----------------|
| **GLEIF** | Global LEI / legal entity IDs | ✅ Connector live |
| **SEC EDGAR** | Public filers, CIK | ✅ Connector live |
| **SAM.gov Entity API** | Federal vendor UEI | ✅ SAM connector live |
| **IRS EO BMF** | Tax-exempt orgs | ✅ IRS 990 connector |
| **Wikidata / OpenSanctions** | Aliases, risk, enrichment | ❌ Not wired (Phase 2 / enrichment layer) |
| **UK Companies House** | UK-only free API | ❌ Phase 2 |

### 2.5 Paid fallback (use sparingly)

- **Cobalt Intelligence** — [SOS API docs](https://cobaltintelligence.stoplight.io/docs/cobalt-intelligence/0f51bcacc3743-secretary-of-state-api) — all 50 states + DC, ~1 credit/lookup; validate pricing before commit.

### 2.6 James’s question: “What is Google Workspace credentials for?”

**Answer:** Not a data API. **Google Workspace OIDC** enables **Sign in with Google** for enterprise users (Workspace accounts). Env vars: `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, redirect URI on the API. Without them, login returns “OIDC not configured”; email/JWT auth still works. **Free** to set up in Google Cloud Console — see §5 below.

---

## 3) System specs (current architecture)

### 3.1 Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI (`apps/api`) — port 3001 |
| Web | Next.js (`apps/web`) — port 3003 |
| Admin | React static (`apps/admin`) — port 3002 |
| Worker | Node/Bull (`apps/worker`) |
| OLTP | Postgres (Docker `:5433` on staging) |
| Object store | MinIO (`:9000`) — evidence vault |
| Search | OpenSearch (`:9200`) |
| Process manager | PM2 (`ecosystem.config.js`) |
| Connectors | Python (`packages/connectors`) — 17 U.S. sources |

### 3.2 Phase 1 modules (11) — status 10 June

| # | Module | Done | Pending / notes |
|---|--------|------|-----------------|
| 1 | Workspace & identity | JWT, MFA, audit | **Google OIDC keys** |
| 2 | Source registry & framework | Registry, runs, DLQ, seed script, admin health | Dedupe legacy source rows (cosmetic) |
| 3 | Evidence vault | MinIO, hashes, EvidenceRefs | — |
| 4 | U.S. connectors (17) | **All 17 ingesting** | **Replace OpenCorporates with state registry connectors** (new work) |
| 5 | Entity resolution | Merge API + UI | Broader fuzzy / graph match |
| 6 | Intelligence graph | Cytoscape UI, export | — |
| 7 | Investor intelligence | analyze_stock + live gov context + **Claude ai_narrative** | Ticker→entity linking for memo quality |
| 8 | Claude skills gateway | **Live Anthropic** + OpenAI fallback + artifacts | — |
| 9 | Report & review | Templates, verifier v2, PDF/Word export | — |
| 10 | Alerts & monitoring | Rules, scan, webhook delivery | Auto-scan on schedule (optional) |
| 11 | Storage / search / graph | Postgres + MinIO + OpenSearch | Neo4j / lakehouse = post-MVP |

### 3.3 Connector inventory (government / records)

| Connector | Status (10 Jun) | Records (typical seed) |
|-----------|-----------------|------------------------|
| SEC EDGAR | ✅ | 10 |
| FEC | ✅ | 10 |
| Congress.gov | ✅ | 10 |
| SAM.gov | ✅ | 10 |
| CourtListener | ✅ | 20 |
| USAspending | ✅ | 10 |
| OFAC | ✅ | 10 |
| GLEIF | ✅ | 10 |
| LDA | ✅ | 10 |
| FARA | ✅ | 10 |
| GovInfo | ✅ | 10 |
| Federal Register | ✅ | 10 |
| Regulations.gov | ✅ | 10 |
| eCFR | ✅ | 50 |
| RegInfo/OIRA | ✅ | 1 |
| IRS 990 | ✅ | 25 |
| OpenCorporates | ✅ (SEC fallback) | 10 |

### 3.4 AI / auth credentials (10 Jun)

| Variable | Status | Purpose |
|----------|--------|---------|
| `ANTHROPIC_API_KEY` | ✅ Set | Claude skills + stock AI narrative |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Must match Anthropic’s current model IDs |
| `OPENAI_API_KEY` | ✅ Set | Skills fallback |
| `OIDC_CLIENT_ID` / `SECRET` | ❌ Empty | Google Workspace SSO |
| `OPENCORPORATES_API_KEY` | ❌ Not used | **Deprioritized** per James — state connectors instead |

---

## 4) What was completed since 5 June report

1. **Connector fixes** — USAspending, SAM v2, CourtListener, FARA endpoint, `.env` loading in connector CLI → **17/17 green**.
2. **Anthropic integration** — model updated to `claude-sonnet-4-6`; duplicate empty `ANTHROPIC_API_KEY` removed; `/skills/status`; live runs on earnings, one_pager, etc.; `analyze_stock` → `investor_memo.ai_narrative`.
3. **Admin** — per-source health deduped by kind; records column.
4. **Alerts UI** — load retry on cold start.
5. **OpenCorporates** — SEC `company_tickers.json` fallback (no paid key).

**Tests:** 33 pytest passing (last full run 8 June).

---

## 5) What is still pending

### 5.1 From original Phase 1 close-out

| Item | Owner | Effort |
|------|-------|--------|
| Google OIDC (`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`) | James / ops | ~15 min setup in [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| Production domain + SSL | Ops | TBD |
| OIDC redirect for prod URL | Ops | When domain known |

### 5.2 New work from James (10 June) — **Company registry program**

This is the **largest new scope** after MVP stabilization.

#### Phase 1b — U.S. State Registry Connector Framework

| Step | Deliverable |
|------|-------------|
| A | **Unified schema** — `state_entity`: `jurisdiction`, `entity_id`, `legal_name`, `status`, `formation_date`, `address`, `registered_agent`, `officers[]`, `source_url`, `raw_hash` |
| B | **Connector types** — `bulk_download` (NY, CO, FL, OR), `open_api` (WA, TX), `html_scrape` (remaining SOS sites) |
| C | **Wave 1 connectors** — NY, CO, FL, OR, WA, TX |
| D | **Wave 2** — Remaining states using James’s SOS URL list + NASS directory |
| E | **Entity resolution** — Link state entities ↔ SEC CIK ↔ GLEIF LEI ↔ SAM UEI |
| F | **Deprecate OpenCorporates connector** or keep as optional enrichment only |
| G | **Cobalt adapter** — thin paid fallback when free path returns no hit (config flag + credit budget) |
| H | **Future API product** — REST search over normalized registry (`/registry/search?q=&state=`) |

#### Engineering notes (aligned with product principles)

- **Official APIs and bulk open data first** — matches Development Plan §principles.
- **Scraping** only where no bulk/API; respect robots/ToS; rate limit; store raw HTML/PDF in evidence vault.
- **Puppeteer/Playwright** for JS-heavy SOS portals (e.g. CA BizFile, DE ICIS).
- **Normalize once, serve many** — same pipeline as existing connectors (`fetch_records` → evidence → `source_record_meta`).

#### Suggested open-source stack (James referenced)

| Tool | Use |
|------|-----|
| FollowTheMoney | Entity schema |
| Yente | Entity search (if we adopt OpenSanctions components) |
| Nomenklatura | Cross-source entity matching |
| Our connectors | Per-state ingestion |

Not required for Wave 1 — consider for matching layer after NY+CO bulk is flowing.

---

## 6) Proposed registry roadmap (engineering estimate)

| Sprint | Scope | Outcome |
|--------|-------|---------|
| **R0** (1 week) | Schema + NY bulk connector + CO Socrata connector | 2 states searchable in platform |
| **R1** (1 week) | FL Sunbiz bulk + OR open data | 4 states |
| **R2** (1 week) | WA API + TX Comptroller API | 6 states |
| **R3** (2–3 weeks) | Scraper framework + 10 high-volume states (CA, DE, TX search, FL, NY web, etc.) | ~16 states |
| **R4** (ongoing) | Remaining states + Cobalt fallback + public `/registry` API | 50-state coverage + monetization path |

---

## 7) Risks & decisions needed from James

| # | Decision |
|---|----------|
| 1 | Confirm **Wave 1 state order** (NY, CO, FL, OR, WA, TX) — or reprioritize (e.g. DE + CA for corp law)? |
| 2 | **Scraping policy** — OK to scrape public SOS search pages where no API? Legal review? |
| 3 | **Cobalt budget** — monthly credit cap for fallback lookups? |
| 4 | **OIDC** — Internal (Workspace only) vs External (any Google account)? |
| 5 | **Registry API product** — target customers and pricing model (per lookup vs subscription)? |

---

## 8) Reference links (James’s list — condensed)

### Bulk / API priority

- NASS directory: https://www.nass.org/business-services/corporate-registration  
- Florida Sunbiz downloads: https://dos.fl.gov/sunbiz/other-services/data-downloads/  
- Colorado entities: https://data.colorado.gov/Business/Business-Entities-in-Colorado/4ykn-tg5h  
- NY active corps JSON: https://data.ny.gov/api/views/n9v6-gdp6/rows.json?accessType=DOWNLOAD  
- Oregon active businesses: https://data.oregon.gov/business/Active-Businesses-ALL/tckn-sxa6/data  
- Washington corps API: https://finditconsumer.wa.gov/corps/searchapi.aspx  
- Texas franchise API docs: https://api-doc.comptroller.texas.gov/  

### Global / enrichment (later)

- GLEIF API: https://api.gleif.org/api/v1/lei-records  
- OpenSanctions bulk: https://www.opensanctions.org/docs/bulk/  
- UK Companies House: https://developer.company-information.service.gov.uk/  

### Paid fallback

- Cobalt SOS API: https://cobaltintelligence.stoplight.io/docs/cobalt-intelligence/0f51bcacc3743-secretary-of-state-api  

### All 50 SOS search URLs

Stored in James’s 9 June chat — full list in §2.3 of this doc’s source messages; use as scrape discovery checklist per state.

---

## 9) Related repo documents

| File | Contents |
|------|----------|
| `5th_june.md` | Master Phase 1 scope & module checklist |
| `4th_june.md` | Standup notes |
| `PHASE1_MVP_COMPLETION_REPORT.md` | 5 Jun sign-off (~95%) — superseded on connectors/Anthropic by 8–10 Jun |
| `PHASE1_E2E_VERIFICATION_REPORT.md` | Browser verification |
| `docs/DEPLOYMENT.md` | Staging deploy |

---

## 10) Changelog

| Date | Update |
|------|--------|
| 10 Jun 2026 | Initial doc: James OpenCorporates replacement strategy, OIDC explanation, current MVP status, registry roadmap |

---

*Next action (no code yet per team): review this doc with James → confirm Wave 1 states + scraping policy → then implement `packages/connectors/us/state_registry/` framework.*
