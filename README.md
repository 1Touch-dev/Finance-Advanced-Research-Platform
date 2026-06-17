# Enterprise Intelligence & Investment Research Platform

A multi-service monorepo for **evidence-first** public-record intelligence, investment research, relationship graphs, report generation with review workflows, and portfolio monitoring.

This is **not** a stock screener or a generic LLM report tool alone. It combines market/financial analysis with U.S. public records (SEC, lobbying, procurement, litigation, sanctions, and more), entity resolution, graph intelligence, and enterprise-style collaboration.

---

## Current status

| Area | Status |
|------|--------|
| **Overall** | **Phase 3 Layer 1 Intelligence Reports (v1 shipped)** + Phase 2 registry foundation |
| **Active workstream** | Entity Network Intelligence Reports — cited dossiers from live federal sources + GPT narrative |
| **Daily log** | [16th_June.md](./16th_June.md) · [15th_June.md](./15th_June.md) · [12th_June.md](./12th_June.md) |
| **E2E report** | [E2E_LIVE_VERIFICATION_REPORT.md](./E2E_LIVE_VERIFICATION_REPORT.md) — 38 FULL / 8 PARTIAL / 0 FAIL (11 Jun) |
| **Branch** | `feature/us-50-state-registry-api` → [PR #2](https://github.com/1Touch-dev/Finance-Advanced-Research-Platform/pull/2) |
| **Last push** | `29ae9c7` — Layer 1 intelligence pipeline + UI + handoff docs |
| **Tests** | **79 passing** (`pytest tests/ -q`) |
| **Staging** | Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002` |
| **Layer 1 Intelligence** | ✅ Live — `POST /intelligence/generate` · UI at `/intelligence` |
| **Registry** | `GET /registry/search`, `GET /registry/jurisdictions`, `GET /registry/entity/{jur}/{eid}` — 202 records, 51 jurisdictions |
| **Connectors** | 17 federal gov connectors + 51 state registry + BEA = **69 total** |
| **BEA** | **Live** — 429 records; `/economics` page |
| **California** | BizFile scrape ✅ (~150/run); CA SOS API ⏸️ pending; Cobalt ⏸️ deferred |

For a detailed requirement-vs-implementation breakdown, see **[docs/REQUIREMENT_GAP_ANALYSIS.md](./docs/REQUIREMENT_GAP_ANALYSIS.md)**.

---

## Phase 3 — Layer 1 Entity Network Intelligence Reports (16 June 2026)

James confirmed **Type A — Entity Network Intelligence Report** as the first deliverable: ownership, investors, government contracts, officers, risk flags, and a cited AI narrative. Demo theme: **Peter Thiel / tech / AI / defense**. CA and Cobalt are deferred; Layer 1 runs on live federal sources.

### Try it on staging

| Resource | URL |
|----------|-----|
| **Intelligence UI** | http://184.72.123.188:3003/intelligence |
| **Home** | http://184.72.123.188:3003 |
| **API docs** | http://184.72.123.188:3001/docs |

Click **Palantir Technologies** → **Generate Intelligence Report** (~15–25 seconds).

### Intelligence API (`/intelligence/*`)

```
POST /intelligence/generate?entity_name=&entity_type=org&ticker=   # generate cited dossier
GET  /intelligence/                                               # list recent reports
GET  /intelligence/{report_id}                                    # retrieve saved report
```

**Pipeline:** entity name/ticker → live connectors (SEC, USASpending, FEC, FARA, LDA, OFAC, CourtListener) → relationship graph edges → 7-section report JSON → GPT-4o narrative (grounded in cited claims only) → persist to DB.

### Report sections (James-style)

| # | Section | Sources |
|---|---------|---------|
| 1 | Entity Profile | SEC EDGAR (CIK, SIC, exchange) |
| 2 | SEC Filings & Ownership Indicators | SEC EDGAR recent filings |
| 3 | Government Contracts & Procurement | USASpending.gov |
| 4 | Political & Regulatory Exposure | FEC, LDA, FARA |
| 5 | Sanctions & Compliance Check | OFAC / OpenSanctions |
| 6 | Litigation & Legal Exposure | CourtListener |
| 7 | Intelligence Narrative (AI-Generated) | GPT-4o — claims-only |

Every claim tagged **DOCUMENTED** / **REPORTED** / **ANALYTICAL**.

### First live demo — Palantir Technologies (PLTR)

| Metric | Result |
|--------|--------|
| SEC CIK | `0001321655` |
| Federal contracts | **$1.72B** across 10 awards (DoD, DHS, VA, USDA) |
| Lobbying (LDA) | 10 filings |
| FEC | 1 PAC |
| Graph edges | 11 relationships written |
| GPT narrative | Generated from cited evidence |

### Demo seeds (UI one-click)

Palantir Technologies · Anduril Industries · Peter Thiel · Founders Fund · HawkEye 360 · Redwire Corporation

### Layer 1 code

| File | Role |
|------|------|
| `apps/api/app/api/intelligence.py` | REST router |
| `apps/api/app/services/intelligence_service.py` | Orchestrator + entity-specific connectors |
| `apps/web/pages/intelligence.js` | Report generator UI |

### Still pending (Layer 1 v2)

- PDF export matching James doc style
- Full 10-node Thiel network graph report
- Ownership tree crawler (OpenOwnership / FinCEN BOI)
- Officer cross-entity matching
- Registry lookup as report entry point

Full handoff: **[16th_June.md](./16th_June.md)**

---

## Phase 2 — U.S. 50-State Registry + BEA (11 June 2026)

James Thunder Marketing's all-50-states registry program is now implemented.

### Registry API (`/registry/*`)

```
GET  /registry/health               # 51/51 live count + tier distribution
GET  /registry/jurisdictions        # all 51 with tier, SOS URL, record count
GET  /registry/search?q=&state=     # search normalized records
GET  /registry/entity/{jur}/{eid}   # single entity detail
POST /registry/keys                 # admin: create API key
```

Auth: `X-Registry-Api-Key` header or `?api_key=` query param. Rate limit: 100 req/min per key.

### Ingestion tiers

| Tier | States | Method | Status |
|------|--------|--------|--------|
| **A — Bulk** | NY, CO, FL, OR | data.ny.gov, data.colorado.gov, Sunbiz HTTP, data.oregon.gov | ✅ Live |
| **B — API** | WA, TX, CA | WA SOS API, TX Comptroller, CA SOS CBC API | ⏸️ CA key pending |
| **B2 — BizFile scrape** | CA (interim) | Playwright scrape of official BizFile Online | ✅ Live (~150/run) |
| **D — Scrape** | 44 remaining states + DC | GenericScrapedStateConnector + Playwright | ✅ Live |
| **E — Cobalt** | Scrape states + CA interim | `COBALT_API_KEY` | ⏸️ Deferred (trial 429) |

### BEA connector (#18)

```bash
# Signup: https://apps.bea.gov/API/signup/
BEA_API_USER_ID=your-uuid-here  # in .env
```

Fetches NIPA GDP, Regional personal income, industry data. Enriches `analyze_stock`.

### New env vars

```bash
BEA_API_USER_ID=          # free BEA API key (live on staging)
CA_SOS_API_KEY=           # CA SOS Primary key from calicodev.sos.ca.gov/profile (pending approval)
COBALT_API_KEY=           # Cobalt SOS API — trial at app.cobaltintelligence.com
COBALT_LIVE_DATA=false    # use cached SOS data (saves trial/paid credits)
REGISTRY_API_ADMIN_TOKEN= # optional bootstrap admin key for /registry/keys
REGISTRY_REQUIRE_AUTH=    # set to "true" to enforce API key auth
```

**CA SOS signup:** [calicodev.sos.ca.gov](https://calicodev.sos.ca.gov/) → Products → **CBC API Production** → Subscribe → Primary key when **Active**.

### Seeding

```bash
bash scripts/seed-state-registry.sh          # all 51 jurisdictions
bash scripts/seed-state-registry.sh us_ny us_co  # specific states
```

---

## What it does today

- **Generate Layer 1 intelligence reports** — enter entity/person → live SEC, USASpending, FEC, FARA, LDA, OFAC, CourtListener → 7-section cited dossier + GPT narrative (`/intelligence`)
- **Resolve & search** entities (companies, people, agencies) with aliases and identifiers
- **Store evidence** — raw documents, hashes, and `EvidenceRef` citations
- **Build relationship graphs** — expand, pathfind, related-party scoring; intelligence reports write edges per run
- **U.S. 50-state registry** — search 51 jurisdictions, 202 normalized records (`/registry`)
- **Run finance workflows** — stock analysis, DCF, comps, fundamentals (via `packages/finance`)
- **Draft & review reports** — sections, claims, claim verification, comments, exports (Markdown/HTML/JSON)
- **Monitor** — watchlists, portfolios (CSV import), alert rules, scan/deliver (webhook + email/SMS)
- **Ingest (production ETL)** — 17 U.S. connectors with live APIs; sample data only in `ENV=test`
- **Skills gateway** — Anthropic adapter (Claude) with OpenAI fallback; artifact persistence + cost logging
- **BEA economics** — GDP, regional income data on `/economics`
- **Exports** — PDF, Word, Markdown, HTML, JSON + evidence CSV appendix (legacy reports)
- **SSO** — Google OIDC routes wired (credentials pending from client)
- **Admin** — source health dashboard with per-source status and run history

---

## Architecture (high level)

```mermaid
flowchart LR
  subgraph clients [Clients]
    Web[Web Next.js :3000]
    Admin[Admin React :3002]
  end
  subgraph core [Core]
    API[FastAPI API :3001]
    Worker[Worker Bull/Redis]
  end
  subgraph data [Data]
    DB[(Postgres or SQLite)]
    Redis[(Redis)]
    Vault[Evidence files]
  end
  subgraph packages [Packages]
    Finance[packages/finance]
    Connectors[packages/connectors]
  end
  Web --> API
  Admin --> API
  Worker --> Redis
  API --> DB
  API --> Vault
  API --> Finance
  Connectors --> API
```

| Layer | Technology |
|-------|------------|
| API | FastAPI, SQLAlchemy, JWT auth, RBAC |
| Web | Next.js 12, React 17 |
| Admin | Create React App, React 17 |
| Worker | Node, Bull, Redis |
| DB (local default) | SQLite (`apps/api/local.db`) |
| DB (Docker) | PostgreSQL 13 |
| Queue | Redis 6 |

---

## Repository structure

```
Finance-Advanced-Research-Platform/
├── apps/
│   ├── api/          # FastAPI — all REST domains
│   │   └── app/
│   │       ├── api/intelligence.py      # Layer 1 intelligence API
│   │       └── services/intelligence_service.py  # Report orchestrator
│   ├── web/          # Next.js research UI (+ /intelligence page)
│   ├── admin/        # React ops / health dashboard
│   └── worker/       # Background jobs (Bull)
├── packages/
│   ├── finance/      # DCF, comps, technicals, market helpers
│   ├── connectors/   # U.S. public-data connectors + SDK (17 federal + 51 state + BEA)
│   └── reporting/    # Report templates (JSON)
├── scripts/
│   ├── local-start.ps1
│   ├── local-stop.ps1
│   ├── seed-state-registry.sh
│   └── docker-up.ps1
├── docs/             # Setup, gap analysis, demo data, Phase 1 readiness
├── memory/           # Project context & architecture notes
├── 16th_June.md      # Latest daily handoff (Layer 1 ship status)
├── tests/            # API + connector tests
├── docker-compose.yml
├── SETUP.md
└── .env.example
```

---

## Implemented modules (API)

| Module | Prefix | Notes |
|--------|--------|--------|
| **Intelligence (Layer 1)** | `/intelligence` | Entity network dossiers — generate, list, retrieve |
| Identity & workspace | `/`, `/auth`, `/orgs`, `/workspaces` | Orgs, roles, projects, cases, audit |
| **Registry** | `/registry` | 51 jurisdictions, search, entity detail, API keys |
| Evidence vault | `/evidence` | Raw upload, refs, file storage |
| Entities & resolution | `/entities` | CRUD, resolve, merge queue |
| Search | `/search` | Global search, entity profile, timeline |
| OpenSearch (stub) | `/searchos` | Index stub + hybrid fallback |
| Graph | `/graph` | Expand, path, related, edge evidence |
| Finance | `/finance` | Analyze stock, DCF, comps, fundamentals |
| Sources | `/sources` | Registry, runs, contracts |
| Reports | `/reports` | Reports, claims, bundles, verify (legacy CRUD) |
| Review | `/review` | Comments, suggestions, exports |
| Skills | `/skills` | Skill registry + runs (Anthropic/OpenAI) |
| Monitor | `/monitor` | Watchlists, portfolios, alerts |
| Compliance | `/compliance` | Policies, export approvals |
| Demo | `/demo` | `POST /demo/seed` — sample data for UI |

Interactive API docs (when API is running): **http://localhost:3001/docs**

---

## U.S. connectors (`packages/connectors`)

**17 federal connectors** — live on staging with real API ingestion:

SEC EDGAR, FEC, LDA, FARA, Congress.gov, GovInfo, Federal Register, Regulations.gov, eCFR, RegInfo/OIRA, USAspending, SAM.gov, IRS 990, CourtListener, OFAC, OpenCorporates, GLEIF.

**Layer 1 intelligence service** runs entity-specific queries against SEC, FEC, FARA, USASpending, LDA, OFAC, and CourtListener per report generation (see `apps/api/app/services/intelligence_service.py`).

**51 state registry connectors** + **BEA** — bulk/API/scrape tiers; CA BizFile Playwright scrape as interim free official source.

Source contracts (YAML) are under `packages/connectors/us/*/source_contract.yml` where defined.

---

## Web UI routes

| Route | Purpose |
|-------|---------|
| `/` | Home + navigation cards |
| **`/intelligence`** | **Layer 1 Entity Network Report generator** — demo seeds, 7-section cited dossier viewer |
| `/search` | Global search |
| `/graph` | Graph visualization (entity ID) |
| `/registry` | U.S. 50-state company registry search (51 jurisdictions) |
| `/economics` | BEA economic data — GDP, regional income (live connector) |
| `/stock` | Stock analysis |
| `/skills` | Skills runner (Anthropic/OpenAI) |
| `/entities/[id]` | Entity profile |
| `/entities/merge` | Entity merge queue |
| `/portfolio/[id]` | Portfolio exposure |
| `/review/[id]` | Report review workspace |
| `/alerts` | Alert inbox |

---

## Quick start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Redis** (optional — only for `apps/worker`)

### Option A — Local without Docker (recommended on Windows)

From this directory:

```powershell
.\scripts\local-start.ps1
```

Stop:

```powershell
.\scripts\local-stop.ps1
```

Uses **SQLite** by default (see `.env`). No PostgreSQL install required.

### Option B — Docker

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```powershell
.\scripts\docker-up.ps1
```

Or manually:

```powershell
docker compose up --build -d
curl.exe -X POST http://localhost:3001/bootstrap
```

### Service URLs

| Service | Local | Staging (EC2) |
|---------|-------|----------------|
| Web | http://localhost:3000 | http://184.72.123.188:3003 |
| **Intelligence UI** | http://localhost:3000/intelligence | http://184.72.123.188:3003/intelligence |
| API | http://localhost:3001 | http://184.72.123.188:3001 |
| API health | http://localhost:3001/health | http://184.72.123.188:3001/health |
| Admin | http://localhost:3002 | http://184.72.123.188:3002 |

---

## Demo data

Populate sample entities, graph links, a report, watchlist, and portfolio:

```powershell
curl.exe -X POST http://127.0.0.1:3001/demo/seed
```

Then try:

- http://localhost:3000/intelligence → click **Palantir Technologies** → **Generate Intelligence Report**
- http://localhost:3000/search → query `apple`
- http://localhost:3000/entities/1
- http://localhost:3000/graph → entity ID `1`
- http://localhost:3000/registry → search state registry records
- http://localhost:3000/portfolio/1
- http://localhost:3000/review/1

Details: **[docs/DEMO_DATA.md](./docs/DEMO_DATA.md)**

---

## Manual setup (API only)

```powershell
cd apps\api
pip install -e .
pip install -e "..\..\packages\finance"
$env:DATABASE_URL = "sqlite:///./local.db"
python -m uvicorn app.main:app --host 127.0.0.1 --port 3001
```

Bootstrap DB tables:

```powershell
curl.exe -X POST http://127.0.0.1:3001/bootstrap
```

Install web/admin per app (`npm install` inside `apps/web` and `apps/admin`). Root `npm install` can fail on some Windows setups — install per app instead.

Full instructions: **[SETUP.md](./SETUP.md)**

---

## Environment variables

Copy `.env.example` to `.env` at the repo root.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | `sqlite:///./local.db` (local) or Postgres URL (Docker) |
| `NEXT_PUBLIC_API_URL` | Web → API base (default `http://localhost:3001`) |
| `REACT_APP_API_URL` | Admin → API base |
| `REDIS_URL` | Worker queue |
| `JWT_SECRET` | API token signing |
| `OPENAI_API_KEY` | Layer 1 GPT-4o narrative generation |
| `FEC_API_KEY` | FEC OpenData (Layer 1 + connector) |
| `COURTLISTENER_API_TOKEN` | CourtListener litigation search |
| `SEC_USER_AGENT` | SEC EDGAR User-Agent header (required by SEC) |
| `BEA_API_USER_ID` | BEA economic data |
| `CA_SOS_API_KEY` | CA SOS CBC API (pending approval) |
| `COBALT_API_KEY` | Cobalt SOS API (deferred — trial capped) |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | Google Workspace SSO (pending from client) |

See `.env.example` for the full list of 17+ connector keys.

---

## Testing

```powershell
# From repo root (with API deps installed)
pytest tests/
```

Coverage is **minimal** today (health stubs + connector sample runs). See gap analysis for testing roadmap.

---

## Documentation

| Document | Description |
|----------|-------------|
| [16th_June.md](./16th_June.md) | **Latest** — Layer 1 ship status, Palantir demo, pending tasks |
| [15th_June.md](./15th_June.md) | Phase 3 planning, 15 intelligence PDF review, BizFile |
| [12th_June.md](./12th_June.md) | Cobalt + CA SOS registry work |
| [PHASE2_COMPLETION_REPORT.md](./PHASE2_COMPLETION_REPORT.md) | 50-state registry completion |
| [SETUP.md](./SETUP.md) | Local + Docker setup, troubleshooting |
| [docs/DEMO_DATA.md](./docs/DEMO_DATA.md) | Demo seed and UI tour |
| [docs/REQUIREMENT_GAP_ANALYSIS.md](./docs/REQUIREMENT_GAP_ANALYSIS.md) | Spec vs repo, priorities |
| [docs/PHASE1_READINESS.md](./docs/PHASE1_READINESS.md) | Phase 1 checklist |
| [memory/](./memory/) | Project context, architecture, progress |

---

## Known limitations

**Layer 1 (current)**
- No PDF export for intelligence dossiers yet (UI + JSON only)
- Single-entity reports only — full multi-node network (Thiel ecosystem) not wired
- No ownership tree crawler (OpenOwnership / FinCEN BOI)
- Officer cross-entity matching not implemented
- Registry not yet used as intelligence report entry point
- OFAC name matching can produce false positives (needs tuning)

**Platform (general)**
- Claim verification and legacy review flows are basic, not full enterprise governance
- OIDC/Google SSO wired but credentials pending from client
- OpenSearch integration is largely a stub
- Admin UI is an operations shell, not full tenant administration
- Cobalt and CA SOS API deferred per client direction

---

## Product principles (from spec)

1. **Evidence first** — conclusions should trace to sources  
2. **Official APIs first** — scraping only when necessary  
3. **Human review** for sensitive outputs  
4. **Multi-tenant governance** — permissions, audit, versioning  
5. **Cost-aware architecture** — right storage for the job  

---

## Contributing

1. Read [docs/REQUIREMENT_GAP_ANALYSIS.md](./docs/REQUIREMENT_GAP_ANALYSIS.md) for current gaps  
2. Follow existing patterns in `apps/api/app/api/` and `packages/`  
3. Prefer focused PRs per module (connectors, evidence, review, etc.)  

---

## License

See repository license file if present; otherwise treat as private/internal until specified.
