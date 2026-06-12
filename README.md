# Enterprise Intelligence & Investment Research Platform

A multi-service monorepo for **evidence-first** public-record intelligence, investment research, relationship graphs, report generation with review workflows, and portfolio monitoring.

This is **not** a stock screener or a generic LLM report tool alone. It combines market/financial analysis with U.S. public records (SEC, lobbying, procurement, litigation, sanctions, and more), entity resolution, graph intelligence, and enterprise-style collaboration.

---

## Current status

| Area | Status |
|------|--------|
| **Overall** | **Phase 2 U.S. 50-State Registry + BEA + Cobalt** — 51/51 jurisdictions, **202 registry records**, Cobalt live, CA API pending |
| **Daily log** | [12th_June.md](./12th_June.md) · [11th_June.md](./11th_June.md) |
| **E2E report** | [E2E_LIVE_VERIFICATION_REPORT.md](./E2E_LIVE_VERIFICATION_REPORT.md) — 38 FULL / 8 PARTIAL / 0 FAIL (11 Jun) |
| **Branch** | `feature/us-50-state-registry-api` → [PR #2](https://github.com/1Touch-dev/Finance-Advanced-Research-Platform/pull/2) |
| **Tests** | **74 passing** (`pytest tests/ -q`) |
| **Staging** | Web `:3003` · API `:3001` · Admin `:3002` on `184.72.123.188` |
| **Registry** | `GET /registry/search`, `GET /registry/jurisdictions`, `GET /registry/entity/{jur}/{eid}`, API key auth |
| **Connectors** | 17 gov connectors + 51 state registry + BEA (#18) = **69 total connectors** |
| **BEA** | **Live** — 429 records (`source_tier: live`); `/economics` page |
| **Cobalt** | **Live** — trial key integrated; scrape-tier + CA interim fallback |
| **California** | **96 live records** (Cobalt interim); official CA SOS API subscription **submitted** |

For a detailed requirement-vs-implementation breakdown, see **[docs/REQUIREMENT_GAP_ANALYSIS.md](./docs/REQUIREMENT_GAP_ANALYSIS.md)**.

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

| Tier | States | Method |
|------|--------|--------|
| **A — Bulk** | NY, CO, FL, OR | data.ny.gov, data.colorado.gov, Sunbiz HTTP, data.oregon.gov |
| **B — API** | WA, TX, CA | WA SOS API, TX Comptroller, CA SOS CBC APIs Prod (`calico.sos.ca.gov`) |
| **D — Scrape** | 44 remaining states + DC | GenericScrapedStateConnector with Playwright + **Cobalt fallback (live)** |
| **E — Cobalt** | Scrape states + CA interim | `COBALT_API_KEY` — trial 20 lookups; `COBALT_LIVE_DATA=false` for cached |

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

- **Resolve & search** entities (companies, people, agencies) with aliases and identifiers
- **Store evidence** — raw documents, hashes, and `EvidenceRef` citations
- **Build relationship graphs** — expand, pathfind, related-party scoring
- **Run finance workflows** — stock analysis, DCF, comps, fundamentals (via `packages/finance`)
- **Draft & review reports** — sections, claims, claim verification, comments, exports (Markdown/HTML/JSON)
- **Monitor** — watchlists, portfolios (CSV import), alert rules, scan/deliver (webhook + stubs)
- **Ingest (production ETL)** — 17 U.S. connectors with live APIs; sample data only in `ENV=test`; runner persists raw + EvidenceRef
- **Skills gateway** — live Anthropic adapter (Claude) with OpenAI fallback; artifact persistence + cost logging
- **Alerts** — real connector-delta scan, SendGrid email + Twilio SMS delivery, alert inbox UI
- **Exports** — PDF, Word, Markdown, HTML, JSON + evidence CSV appendix
- **SSO** — Google OIDC routes + JWT refresh/revocation
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
│   ├── web/          # Next.js research UI
│   ├── admin/        # React ops / health dashboard
│   └── worker/       # Background jobs (Bull)
├── packages/
│   ├── finance/      # DCF, comps, technicals, market helpers
│   ├── connectors/   # U.S. public-data connectors + SDK
│   └── reporting/    # Report templates (JSON)
├── scripts/
│   ├── local-start.ps1
│   ├── local-stop.ps1
│   └── docker-up.ps1
├── docs/             # Setup, gap analysis, demo data, Phase 1 readiness
├── memory/           # Project context & architecture notes
├── tests/            # API + connector tests (minimal today)
├── docker-compose.yml
├── SETUP.md
└── .env.example
```

---

## Implemented modules (API)

| Module | Prefix | Notes |
|--------|--------|--------|
| Identity & workspace | `/`, `/auth`, `/orgs`, `/workspaces` | Orgs, roles, projects, cases, audit |
| Evidence vault | `/evidence` | Raw upload, refs, file storage |
| Entities & resolution | `/entities` | CRUD, resolve, merge queue |
| Search | `/search` | Global search, entity profile, timeline |
| OpenSearch (stub) | `/searchos` | Index stub + hybrid fallback |
| Graph | `/graph` | Expand, path, related, edge evidence |
| Finance | `/finance` | Analyze stock, DCF, comps, fundamentals |
| Sources | `/sources` | Registry, runs, contracts |
| Reports | `/reports` | Reports, claims, bundles, verify |
| Review | `/review` | Comments, suggestions, exports |
| Skills | `/skills` | Skill registry + runs (internal/Anthropic stub) |
| Monitor | `/monitor` | Watchlists, portfolios, alerts |
| Compliance | `/compliance` | Policies, export approvals |
| Demo | `/demo` | `POST /demo/seed` — sample data for UI |

Interactive API docs (when API is running): **http://localhost:3001/docs**

---

## U.S. connectors (`packages/connectors`)

Connector skeletons and tests exist for:

SEC EDGAR, FEC, LDA, FARA, Congress.gov, GovInfo, Federal Register, Regulations.gov, eCFR, RegInfo/OIRA, USAspending, SAM.gov, IRS 990, CourtListener, OFAC, OpenCorporates, GLEIF.

Source contracts (YAML) are under `packages/connectors/us/*/source_contract.yml` where defined.

---

## Web UI routes

| Route | Purpose |
|-------|---------|
| `/` | Home + navigation cards |
| `/search` | Global search |
| `/graph` | Graph visualization (entity ID) |
| `/registry` | U.S. 50-state company registry search (51 jurisdictions) |
| `/economics` | BEA economic data — GDP, regional income (live connector) |
| `/stock` | Stock analysis |
| `/skills` | Skills runner (Anthropic live) |
| `/entities/[id]` | Entity profile |
| `/portfolio/[id]` | Portfolio exposure |
| `/review/[id]` | Report review workspace |

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

| Service | URL |
|---------|-----|
| Web | http://localhost:3000 |
| API | http://localhost:3001 |
| API health | http://localhost:3001/health |
| Admin | http://localhost:3002 |

---

## Demo data

Populate sample entities, graph links, a report, watchlist, and portfolio:

```powershell
curl.exe -X POST http://127.0.0.1:3001/demo/seed
```

Then try:

- http://localhost:3000/search → query `apple`
- http://localhost:3000/entities/1
- http://localhost:3000/graph → entity ID `1`
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
| [SETUP.md](./SETUP.md) | Local + Docker setup, troubleshooting |
| [docs/DEMO_DATA.md](./docs/DEMO_DATA.md) | Demo seed and UI tour |
| [docs/REQUIREMENT_GAP_ANALYSIS.md](./docs/REQUIREMENT_GAP_ANALYSIS.md) | Spec vs repo, priorities |
| [docs/PHASE1_READINESS.md](./docs/PHASE1_READINESS.md) | Phase 1 checklist |
| [memory/](./memory/) | Project context, architecture, progress |

---

## Known limitations (Phase 1)

- Many connectors return **sample/fixture** data, not live production ingestion
- Claim verification and review flows are **basic**, not full enterprise governance
- No SSO/SCIM/MFA yet
- OpenSearch integration is largely a **stub**
- Alert delivery (email/Slack/Teams) are **placeholders**
- Admin UI is an **operations shell**, not full tenant administration

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
