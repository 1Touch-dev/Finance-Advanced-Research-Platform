# Finance Advanced Research Platform

**Enterprise-grade financial intelligence & investment research platform**

[![Status](https://img.shields.io/badge/Status-In_Progress-yellow)]()
[![Branch](https://img.shields.io/badge/Branch-8th--july--sprint-blue)]()
[![Python](https://img.shields.io/badge/Python-3.11+-green)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)]()
[![Next.js](https://img.shields.io/badge/Next.js-12-green)]()

A multi-service monorepo for **evidence-first** public-record intelligence, investment research, relationship graphs, report generation with review workflows, and portfolio monitoring.

**Live Staging:** http://184.72.123.188:3003 (Web) | http://184.72.123.188:3001 (API) | http://184.72.123.188:3001/docs (API Docs)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Current Status Summary](#current-status-summary)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Features Status](#features-status)
  - [Completed Features](#-completed-features-35-items)
  - [In Progress Features](#-in-progress-features-7-items)
  - [Remaining Features](#-remaining-features-72-items-prioritized)
- [API Endpoints](#api-endpoints)
- [External API Integrations](#external-api-integrations)
- [Database Models](#database-models)
- [Frontend Pages](#frontend-pages)
- [Setup & Installation](#setup--installation)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [AI Model Training Roadmap](#ai-model-training-roadmap)
- [Roadmap & Sprint Sequence](#roadmap--sprint-sequence)

---

## Project Overview

This is **not** a stock screener or a generic LLM report tool. It combines market/financial analysis with U.S. public records (SEC, lobbying, procurement, litigation, sanctions, and more), entity resolution, graph intelligence, and enterprise-style collaboration.

### Core Capabilities

| Capability | Description |
|------------|-------------|
| **9-Section Intelligence Dossiers** | Comprehensive entity reports covering profiles, investors, government contracts, lobbying, political exposure, sanctions, litigation, AI narratives, and data sources |
| **Market Analysis** | Stock analysis with 35+ ratios, 15 technical indicators, and 4-agent AI consensus (BUY/HOLD/SELL) |
| **Institutional Tracking** | 13F filings, position-diff analysis (1,805-line service, 45 tests pass), mega-positions tracking |
| **Government Trading Intelligence** | House PTR (STOCK Act), Form 4 insider trades, Congress.gov legislation, politician tracker |
| **Trade Alerts (F-03/F-04)** | Automated Form 4 + watchlist threshold scanning with email/SMS notifications |
| **RAG-Powered Chat** | Vector + keyword + hybrid search over ingested documents (Phase 1 complete) |
| **50-State Registry** | Company entity search across all US jurisdictions |
| **OSINT Enrichment** | Apollo.io, OpenCorporates, GLEIF, FinCEN integrations |

---

## Current Status Summary

| Metric | Count |
|--------|-------|
| **API Endpoints** | 447 routes |
| **Frontend Pages** | 42 pages |
| **Database Models** | 70 models |
| **Service Files** | 70 services |
| **Connector Files** | 43 connectors |
| **External APIs** | 20+ integrations |
| **Test Coverage** | 45/45 13F, 40/41 Congress, 10/10 RAG |
| **Commits Ahead** | 90+ (8th-july-sprint vs main) |

| Area | Status |
|------|--------|
| **Overall** | **10 Aug 2026 — RAG Phase 1 shipped, 13F position-diff merged, 7 orphan services pending activation** |
| **Active branch** | `8th-july-sprint` (90 commits ahead of `main`) |
| **Trade Alerts (F-03/F-04)** | Completed — PM2 every 4h, SendGrid/Twilio configured |
| **Congress.gov (F-05)** | Completed — 1,000 req/hr free API, live bills + Senate PTR |
| **RAG Chat** | Completed (Phase 1) — Vector + keyword + hybrid modes |
| **13F Position-Diff** | Completed — 45 tests pass, live Berkshire Hathaway diff verified |
| **7 Orphan Services** | In Progress — 4,794 lines of logic, needs router endpoints |

---

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Backend API** | FastAPI | 0.115+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Database (prod)** | PostgreSQL | 13+ |
| **Database (local)** | SQLite | Default fallback |
| **Python** | — | 3.11+ required |
| **Frontend** | Next.js | 12 |
| **UI Framework** | React | 17 |
| **Styling** | Tailwind CSS | v3 |
| **Charts** | Recharts | — |
| **Graph Visualization** | Cytoscape | — |
| **Job Queue** | Bull + Redis | — |
| **Process Manager** | PM2 | — |
| **Auth** | JWT + bcrypt | 24h tokens |
| **Export (PDF)** | ReportLab | 4.0+ |
| **Export (Word)** | python-docx | 1.1+ |
| **Export (Excel)** | openpyxl | 3.1+ |
| **Export (PPT)** | python-pptx | 0.6+ |
| **Embeddings** | text-embedding-3-small | OpenAI |
| **Vector Store** | Numpy cosine + HNSW | Fallback to TF-IDF |
| **Keyword Search** | rank-bm25 + TF-IDF | BM25 primary |
| **Package Manager** | pnpm + Turborepo | Monorepo |

---

## Project Structure

```
Finance-Advanced-Research-Platform/
├── apps/
│   ├── api/                 # FastAPI backend (Python 3.11), 40+ route files
│   │   ├── app/
│   │   │   ├── api/         # Route handlers (market, intelligence, tracking, etc.)
│   │   │   ├── connectors/  # External API connectors (43 files)
│   │   │   ├── models/      # SQLAlchemy ORM models (70 models)
│   │   │   ├── services/    # Business logic services (70 files)
│   │   │   │   └── rag/     # RAG system (embeddings, vector, hybrid, rerank)
│   │   │   └── scripts/     # CLI scripts (scanners, migrations)
│   │   └── tests/           # Backend tests
│   ├── web/                 # Next.js 12 frontend (42 pages)
│   │   ├── src/
│   │   │   ├── components/  # React components
│   │   │   ├── pages/       # Next.js pages
│   │   │   └── styles/      # Tailwind CSS
│   ├── admin/               # React admin dashboard
│   ├── worker/              # Node.js Bull/Redis background jobs
│   └── extension/           # Browser extension (6 files)
├── packages/
│   ├── finance/             # DCF, comps, technicals, market helpers
│   ├── connectors/          # US public-data connectors (17 federal + 51 state)
│   ├── shared-types/        # TypeScript interfaces
│   ├── config-typescript/   # Shared TS config
│   └── config-eslint/       # Shared ESLint config
├── docs/                    # Architecture, features, setup, handoff docs
├── tests/                   # Integration test suites
└── tooling/                 # Scripts & generators
```

---

## Features Status

### Completed Features (35+ items)

#### Core Intelligence Module

| Feature | Description | Evidence |
|---------|-------------|----------|
| **9-Section Intelligence Dossiers** | Entity Profile, Investors, Gov Contracts, Lobbying, Political Exposure, Sanctions, Litigation, AI Narrative, Data Sources | 10+ reports persisted |
| **Entity Claim Tagging** | Every claim tagged DOCUMENTED / REPORTED / ANALYTICAL | Live in all reports |
| **PDF/Word/Excel/PPT Export** | All formats downloadable via `/intelligence/{id}/pdf\|word\|excel\|powerpoint` | Verified |
| **PayPal Mafia Demo Seeds** | Peter Thiel, Elon Musk, Reid Hoffman + Thiel/Defense network | Live |
| **Click-to-Investigate** | Capitalized entity names in reports are clickable → new report | Live |

#### Market & Finance Analysis

| Feature | Description | Status |
|---------|-------------|--------|
| **Stock Analysis** | Price, 35+ ratios, 15 technicals, 4-agent AI consensus (BUY/HOLD/SELL) | Completed |
| **DCF Valuation** | Intrinsic value, Bear/Base/Bull scenarios, 10-K/10-Q MD&A parsing | Completed |
| **Deep Company Analysis** | SEC EDGAR, XBRL, cap table, insider trades, analyst ratings, earnings | Completed |
| **Expert Analysis** | News sentiment trends, themes, analyst upgrade timeline | Completed |
| **Crypto Dashboard** | CoinGecko market data, whale alerts, wallet lookup (ETH/BTC), TTL cache | Completed |
| **Economics Module** | FRED + BEA macroeconomic data (GDP, CPI, regional income) | Completed |

#### Institutional Holdings (13F)

| Feature | Description | Status |
|---------|-------------|--------|
| **13F Institutional Holdings** | Top holders, mutual funds, filer lookup | Completed |
| **13F Position-Diff** | Quarter-over-quarter position comparison | Completed (45/45 tests pass) |
| **Live SEC Query** | Real Berkshire Hathaway 2026-03-31 vs 2025-12-31 diff | Verified in ~8s |

#### Trade Alerts & Monitoring

| Feature | Description | Status |
|---------|-------------|--------|
| **F-03: Big Trade Scanner** | Form 4 insider trades above USD threshold → Email/SMS alerts | Completed |
| **F-04: Investment Threshold Alerts** | Per-watchlist thresholds → Form 4 + 13F triggers | Completed |
| **F-05: Congress.gov Integration** | Bills, legislation, sponsor tracking (1,000 req/hr free) | Completed |
| **Senate PTR** | Live Senate trading disclosures (1,301 lines gov connector) | Completed |
| **House PTR** | House Clerk annual FD.ZIP parsing | Completed |
| **Politician Tracker** | Pelosi, McConnell, etc. PTR + legislation tracking | Completed |
| **PM2 Cron Scheduling** | big-trade every 4h, investment +30min offset | Configured |
| **SendGrid + Twilio** | Email + SMS delivery wired | Configured |

#### RAG Chat System (Phase 1)

| Component | Description | Status |
|-----------|-------------|--------|
| **Vector Search** | OpenAI `text-embedding-3-small`, batched, disk-cached | Completed |
| **Keyword Search** | BM25 (`rank_bm25`) with TF-IDF fallback | Completed |
| **Hybrid Search** | BM25 + dense fused via Reciprocal Rank Fusion | Completed |
| **Reranking** | Optional cross-encoder rerank (fallback-safe) | Completed |
| **Chunking** | Recursive + semantic chunking (`RAG_CHUNK_STRATEGY`) | Completed |
| **Guardrails** | Input (prompt-injection), retrieval floor, output (no advice) | Completed |
| **Debug Trace** | Per-stage debug trace (`?debug=true`) | Completed |
| **Eval CLI** | hit@k / MRR / nDCG + before/after comparison | Completed |
| **Tests** | 10 passing tests (mocked embeddings → offline) | Verified |

#### News & Intelligence

| Feature | Description | Status |
|---------|-------------|--------|
| **50+ RSS Feeds** | Bloomberg, Reuters, FT, WSJ, CNBC, CoinDesk, Politico, etc. | Completed |
| **Entity Auto-tagging** | 15 entities tracked (Apple, Tesla, Bitcoin, Fed, etc.) | Completed |
| **15-min Polling** | PM2 rss-poller cycle | Running |
| **2,000+ Articles** | Indexed and searchable | Live |

#### OSINT & Entity Enrichment

| Feature | Description | Status |
|---------|-------------|--------|
| **Apollo.io** | Org enrichment, people search, org chart | Completed (Paid plan live) |
| **OpenCorporates** | Global company registry search | Completed |
| **GLEIF** | Legal Entity Identifier (LEI) lookup | Completed |
| **FinCEN** | Beneficial ownership data | Completed |
| **ICIJ Offshore Leaks** | Panama/Paradise/Pandora Papers search | Completed |
| **Username Enumeration** | 40+ platform checks (Sherlock-style) | Completed |
| **Domain Intelligence** | WHOIS, DNS, subdomains, tech stack | Completed |
| **UK Companies House** | Officers + company search | Completed |

#### Registry & Graph

| Feature | Description | Status |
|---------|-------------|--------|
| **50-State Registry** | All 51 jurisdictions searchable (~202 normalized records) | Completed |
| **Relationship Graph** | Cytoscape network visualization, expand/pathfind | Completed |
| **Entity Timeline** | Chronological event view per entity | Completed |
| **Multi-Entity Comparison** | Up to 5 entities, radar chart, KPI table, overlap | Completed |
| **Global Search** | Entities, documents, relationships | Completed |
| **Entity Profile (9 tabs)** | Financial, People, Social, RAG Chat, etc. | Completed |

#### Tracking & Alerts

| Feature | Description | Status |
|---------|-------------|--------|
| **Watchlist Management** | Add/remove entities, per-ticker configuration | Completed |
| **Alert Inbox** | Severity filter, acknowledge, snooze 24h | Completed |
| **Daily Digest** | 6AM UTC worker sends curated report | Completed |
| **Portfolio Import** | CSV-based portfolio tracking | Completed |

#### UI/UX

| Feature | Description | Status |
|---------|-------------|--------|
| **Dark UI Redesign** | 8 Jul sprint complete | Completed |
| **Tailwind Design System** | Dark sidebar, indigo brand (#6366f1) | Completed |
| **All Pages Redesigned** | 42 pages live | Completed |

---

### In Progress Features (7+ items)

| Feature | Description | Status | Next Steps |
|---------|-------------|--------|------------|
| **7 Orphan Services** | Self-dealing, co-investment, founder-correlation, deep-comparative, correlation, contract-probability, interactive-report | Logic complete (4,794 lines) | Need router endpoints + orchestrators |
| **AI Model Training Phase 2** | Fine-tune embeddings on domain data | Phase 1 done | Collect claim pairs, train on RunPod |
| **Quality Gates ML Classifier** | Replace regex gates with trained classifier | Regex exists | Export pass/fail labels, train classifier |
| **Page Regeneration System** | Scheduled freshness regeneration | Endpoint exists | Implement actual regeneration |
| **Interactive Report HTML** | Searchable HTML reports | Service written (598 lines) | Wire to router |
| **Subscription Notifications** | Status page subscriber alerts | Stub in `/status` | Wire persistence + delivery |
| **DB Migration for F-04** | Alembic migration for new columns | Columns added | Add migration for existing DBs |

#### Orphan Services Detail

| Service | Lines | Purpose | Entry Point |
|---------|-------|---------|-------------|
| `self_dealing_service.py` | 436 | NVIDIA self-dealing detection | `cross_reference_self_dealing(...)` |
| `coinvestment_network_service.py` | 400 | Find investors of same companies | `build_coinvestment_network(...)` |
| `founder_correlations_service.py` | 623 | PayPal-mafia / who-studied-together | `find_educational_overlaps(...)` |
| `deep_comparative_service.py` | 1,134 | Deep multi-company comparison | Has own SEC/FMP fetchers |
| `correlation_service.py` | 528 | Pattern / correlation finding | 17 functions |
| `contract_probability_service.py` | 675 | Probability of delivery on contracts | Consumes USASpending data |
| `interactive_report_service.py` | 598 | Interactive searchable reports | Renders HTML |

---

### Remaining Features (72 items prioritized)

#### Band A — Conversion & Retention Blockers (14 items) — DO FIRST

**Backend (8):**

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 3 | Reachable human support + escalation path | Low | Policy + ticketing |
| 5 | Internal linking across generated pages | Low | SEO optimization |
| 6 | Sitemaps and crawl management | Low | XML sitemap generation |
| 7 | Freshness engine | Medium | Scheduled re-generation |
| 9 | Compliance guardrails on generated content | Low | No projections, disclaimers |
| 11 | AI-answer visibility tracking | Low | Track Google AI Overview citations |
| 13 | Portable corpora — export, API, MCP | Low | User data export |
| 14 | 13F honesty layer | Low | Flag 45-day stale data |

**Frontend (3):**

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 1 | Published pricing page | Low | Static pricing |
| 2 | Renewal notice + one-click cancel | Low | No dark patterns |
| 12 | Browser extension overlay | Low | Provenance on EDGAR/news |

**Full-stack (3):**

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 4 | Honest status page with incident history | Low | BE: logging / FE: public UI |
| 8 | Editorial workflow for AI content | Low | BE: approval queue / FE: review |
| 10 | Experiment framework for templates | Medium | A/B assignment + rendering |

#### Band B — Differentiation Multipliers (17 items)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 15 | Filing redline + table-to-Excel + search | Medium | Diff engine + viewer |
| 16 | Company-specific ontology + KPI schema | High | Per-company RAG |
| 17 | Private document ingestion | Medium | Upload pipeline |
| 18 | Multi-entity and thematic corpora | Medium | Sector queries |
| 19 | Point-in-time rolling consensus | High | Consensus as-it-was |
| 31 | Docket-to-disclosure reconciliation | Medium | **KEY L-SERIES FEATURE** |

#### Band C — Table Stakes (25 items)

- Global equity coverage
- Forward multiples on consensus
- Cost basis and tax lots
- Brokerage sync
- Risk metrics (VaR, beta, drawdown)
- Team permission roles
- Litigation tracking and extraction
- Mobile PWA with push notifications
- Chart drawing tools with persistence

#### Not Done (Known Gaps — Waiting on Approvals)

| Feature | Gap | Reason |
|---------|-----|--------|
| Ownership tree crawler | Not implemented | FinCEN BOI / OpenOwnership pending |
| Officer cross-entity matching | Not implemented | Needs fuzzy name matching |
| Multi-entity network graph | Single-entity only | Full network deduplication not wired |
| PitchBook enrichment | Pending approval | Requires API key |
| LinkedIn people enrichment | Pending approval | Requires credential decision |
| CA SOS API | Pending approval | Interim Playwright scrape live |
| ALEPH/OCCRP leaked docs | Pending approval | Account approval required |
| Google OIDC/SSO | Pending credentials | Routes exist |

---

## API Endpoints

### Summary: 447 Routes

#### Market Routes (`/market/*` — 100+ endpoints)

```
GET  /market/yf/snapshot?ticker=          — Price + fundamentals
GET  /market/yf/history?ticker=           — OHLCV history
GET  /market/technicals?ticker=           — 15 technical indicators
GET  /market/intelligence/report?ticker=  — 4-agent AI consensus
GET  /market/crypto/*                     — CoinGecko + wallet data
GET  /market/gov/*                        — House PTR, Form 4, politician tracker
GET  /market/company/*                    — SEC EDGAR, cap table, earnings
GET  /market/valuation/*                  — DCF + filing analysis
GET  /market/expert/*                     — Sentiment + analyst timeline
GET  /market/institutional/*              — 13F positions + position-diff
GET  /market/rss/*                        — RSS feeds + articles
POST /market/rss/poll                     — Manual poll trigger
```

#### Intelligence Routes (`/intelligence/*` — 20+ endpoints)

```
POST /intelligence/generate               — Generate 9-section report
GET  /intelligence/                       — List saved reports
GET  /intelligence/{id}                   — Retrieve report
GET  /intelligence/{id}/pdf|word|excel    — Export formats
POST /intelligence/apollo/enrich          — Apollo enrichment
GET  /intelligence/private-co/search      — OpenCorporates/GLEIF/FinCEN
POST /intelligence/browser-research       — Browser research agent
```

#### Tracking & Monitoring (`/tracking/*`)

```
POST /tracking/watchlist                  — Add entity
GET  /tracking/watchlist                  — List
DELETE /tracking/watchlist/{name}         — Remove
POST /tracking/scan/insider-trades        — F-03 scan
POST /tracking/scan/investments           — F-04 scan
GET|POST|PATCH|DELETE /tracking/alert-rules  — F-03 rules CRUD
GET|PATCH /tracking/watchlist/{ticker}/threshold  — F-04 settings
```

#### RAG & Chat (`/chat/*`)

```
POST /chat/ask                            — Q&A (with ?mode=vector|keyword|hybrid)
POST /chat/summary/{id}                   — Executive summary
```

#### Registry (`/registry/*`)

```
GET  /registry/health                     — Source status
GET  /registry/jurisdictions              — All 51 with tier
GET  /registry/search?q=&state=           — Entity search
GET  /registry/entity/{jur}/{eid}         — Detail
POST /registry/keys                       — Admin API key creation
```

---

## External API Integrations

### Active Integrations (20+ services)

| API | Purpose | Status |
|-----|---------|--------|
| **OpenAI** | GPT-4o mini for intelligence narratives | Active |
| **Anthropic Claude** | Skills gateway, LLM fallback | Active |
| **Apollo.io** | Org enrichment + people search (Paid plan) | Active |
| **Apify** | Social scraping (Twitter/Instagram/YouTube) | Active |
| **yfinance** | Market data (free) | Active |
| **Finnhub** | Financial snapshots | Active |
| **FMP** | Financial Modeling Prep | Active |
| **Alpha Vantage** | Technical indicators | Active |
| **FRED** | St. Louis Fed macroeconomic data | Active |
| **BEA** | Bureau of Economic Analysis | Active |
| **NewsAPI** | News aggregation | Active |
| **Guardian / NYT / GDELT** | News sources | Active |
| **CoinGecko** | Crypto market data (free) | Active |
| **Etherscan** | ETH wallet data | Active |
| **Blockchain.info** | BTC wallet data | Active |
| **SEC EDGAR** | Company filings (User-Agent required) | Active |
| **FEC OpenData** | Political contributions | Active |
| **Congress.gov** | Legislation (1,000 req/hr free) | Active |
| **CourtListener** | Litigation data | Active |
| **OFAC** | Sanctions check (no key needed) | Active |
| **UK Companies House** | UK company registry | Active |
| **LDA.gov** | Lobbying disclosure | Active |
| **SendGrid** | Email delivery for alerts | Configured |
| **Twilio** | SMS delivery for alerts | Configured |

---

## Database Models

**70 SQLAlchemy ORM model classes** across 13 model files:

| Model File | Key Tables | Count |
|----------|-----------|-------|
| `models.py` | Organization, Workspace, User, Role, Permission, Membership, Project, Case | 8 |
| `entities.py` | Entity, EntityAlias, EntityIdentifier, Relationship, MergeCandidate | 6 |
| `evidence.py` | RawDocument, EvidenceRef | 2 |
| `market_13f_cache.py` | Institutional13FPeriodCache, PositionCache | 3 |
| `market_13f_schemas.py` | PositionDiff schemas | 12+ |
| `monitor.py` | Watchlist, WatchlistItem, PortfolioImport, AlertEvent, AlertRule | 5 |
| `registry.py` | RegistrySource, RegistryRecord, RegistrySchema | 3 |
| `reports.py` | Report, Claim, ClaimBundle, ClaimVerification | 4 |
| `review.py` | Comment, Suggestion | 2 |
| `skills.py` | SkillRun, SkillExecutionLog | 2 |
| `sources.py` | Source, SourceRun, SourceContract | 3 |
| `compliance.py` | Policy, ExportApproval | 2 |

**Authentication & RBAC:**
- JWT tokens (24h expiry)
- bcrypt password hashing
- Role-based access control per workspace

---

## Frontend Pages

**42 pages** across the web application:

| Route | Page | Status |
|-------|------|--------|
| `/` | Dashboard — stats, quick search | Live |
| `/intelligence` | Report generator + PayPal Mafia seeds | Live |
| `/intelligence/[id]` | Saved report + exports | Live |
| `/saved` | Reports library | Live |
| `/stock` | Stock terminal | Live |
| `/valuation` | DCF + filing analysis | Live |
| `/company` | Deep company (5+ tabs) | Live |
| `/expert-analysis` | Sentiment + analyst timeline | Live |
| `/institutional` | 13F + position-diff | Live |
| `/gov-trading` | House PTR + politician tracker | Live |
| `/crypto` | Market dashboard + wallet | Live |
| `/economics` | FRED + BEA | Live |
| `/search` | Global entity search | Live |
| `/graph` | Cytoscape network viz | Live |
| `/registry` | 50-state registry + OSINT | Live |
| `/timeline` | Entity event timeline | Live |
| `/compare` | Multi-entity comparison | Live |
| `/tracking` | Watchlist + digest + F-03/F-04 alerts | Live |
| `/tracking/alerts` | Alert inbox | Live |
| `/entities/[id]` | 9-tab entity profile | Live |
| `/skills` | Skills runner | Live |
| +20 more | Options, analysts, billing, consensus, guidance, filing-compare, etc. | Live |

---

## Setup & Installation

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **pnpm** (for monorepo)
- **Redis** (for Bull job queue)

### Backend Setup

```bash
# From repo root
cd apps/api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e .

# Set environment variables
export DATABASE_URL="sqlite:///./local.db"

# Run the server
python -m uvicorn app.main:app --host 127.0.0.1 --port 3001

# Bootstrap database
curl -X POST http://127.0.0.1:3001/bootstrap
```

### Frontend Setup

```bash
cd apps/web
pnpm install
pnpm dev  # Runs on :3000 or :3003
```

### Running Tests

```bash
# 13F tests (45 pass)
python -m pytest ../../tests/test_market_13f_api.py ../../tests/test_market_13f_position_diff.py -q

# Congress tests (40/41 pass)
python -m pytest ../../tests/connectors/test_congress_gov.py ../../tests/test_legislation_endpoints.py -q

# RAG tests (10 pass)
python -m pytest ../../tests/test_rag_vector.py -q

# Trade alert scanners (dry-run)
python -m app.scripts.run_big_trade_scan --dry-run
python -m app.scripts.run_investment_alert_scan --dry-run
```

### Environment Variables

Copy `.env.example` to `.env`. Key variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/finance_db

# OpenAI
OPENAI_API_KEY=sk-...

# Apollo.io
APOLLO_API_KEY=...

# Notifications
SENDGRID_API_KEY=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
ALERT_SENDER_EMAIL=...
ALERT_RECIPIENT_EMAIL=...
ALERT_RECIPIENT_PHONE=...
BIG_TRADE_THRESHOLD=100000

# SEC (required for EDGAR)
SEC_USER_AGENT=YourCompany contact@email.com

# Congress.gov
CONGRESS_API_KEY=...

# BEA Economics
BEA_API_USER_ID=...
```

---

## Deployment

### Staging (EC2: 184.72.123.188)

| Service | Port | Status |
|---------|------|--------|
| Web | 3003 | Online |
| API | 3001 | Online |
| Admin | 3002 | Online |
| API Docs | 3001/docs | Online |

### PM2 Process Manager

```
PM2 Name                  Status
finance-api               Online (FastAPI)
finance-web               Online (Next.js)
finance-admin             Online (React)
finance-worker            Online (Bull/Redis jobs)
rss-poller                Online (15-min cycle)
big-trade-scanner         Online (every 4h UTC)
investment-alert-scanner  Online (every 4h UTC + 30min)
daily-digest              Online (6AM UTC)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| **`docs/Finance_Platform_Handoff.md`** | Full handoff for new teammates — START HERE |
| `docs/AI-Model-Training-Roadmap.md` | Phase 1-4 AI roadmap (Phase 1 shipped 10 Aug) |
| `docs/RAG-Upgrade-Plan.md` | Vector RAG design & operations |
| `docs/Task-Assignment-Detailed.md` | Post-merge task breakdown + 7 orphan services |
| `docs/Feature-Roadmap-Prioritized.md` | Prioritized feature backlog (72 items) |
| `docs/CONTRIBUTING.md` | Contribution guidelines |
| `docs/api/` | API integration guides |
| `docs/architecture/` | System architecture decisions |

---

## AI Model Training Roadmap

### Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Vector search swap-in (no training) | **Completed** (10 Aug 2026) |
| **Phase 2** | Fine-tune embeddings on domain data | Pending |
| **Phase 3** | Quality-gate ML classifier | Pending |
| **Phase 4** | Distill narrative generator | Pending (gated on data volume) |

### Phase 1 Shipped Components

- `services/rag/embeddings.py` — Provider-agnostic, batched, disk-cached
- `services/rag/vector_store.py` — Numpy cosine + transparent HNSW
- `services/rag/keyword.py` — BM25 with TF-IDF fallback
- `services/rag/hybrid.py` — BM25 + dense via RRF
- `services/rag/rerank.py` — Optional cross-encoder
- `services/rag/chunking.py` — Recursive + semantic
- `services/rag/guardrails.py` — Input/retrieval/output guards
- `services/rag/trace.py` — Debug trace
- `services/rag/eval.py` — hit@k / MRR / nDCG CLI

### Sequencing

```
Phase 1 (days)   → vector search, no training          ✅ DONE
Phase 2 (weeks)  → fine-tuned embeddings, first model  → NEXT
Phase 3 (weeks)  → quality classifier, second model    → Parallel to Phase 2
Phase 4 (months) → narrative distillation              → Gated on volume
```

---

## Roadmap & Sprint Sequence

### Recommended Sprint Sequence

1. **Sprint 1-2:** Band A Backend (8 items) — Stop the bleeding
2. **Sprint 2-3:** Band A Frontend + Full-stack (6 items) — Complete churn-stopper set
3. **Sprint 4-6:** Band B Backend (12 items) — Start with #31 (docket-disclosure)
4. **Sprint 7-8:** Band B Full-stack (4 items) — Filing redline (#15)
5. **Sprint 9+:** Band C as needed based on user feedback

### Immediate Next Steps

1. **Activate 7 orphan services** — Wire self-dealing, co-investment, founder-correlation endpoints
2. **13F honesty layer** — Add "45-day stale" flag to position-diff + UI banner
3. **AI Model Training Phase 2** — Fine-tune embeddings
4. **Twilio upgrade + SendGrid domain auth** — Production-ready multi-user alerts
5. **DB migration** — Add Alembic migration for F-04 columns on existing databases

### Known Post-Merge Follow-ups

1. `package-lock.json` — Run `npm install` at repo root (new monorepo tooling)
2. SQLite migration gap — F-04 columns need `ALTER TABLE` for existing DBs
3. Test bug — `test_bill_detail_not_found_returns_error_payload` expects 200, gets 404

---

## Architecture

```mermaid
flowchart LR
  subgraph clients [Clients]
    Web[Web Next.js :3003]
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
  subgraph packages [Shared Packages]
    Finance[finance]
    Connectors[connectors]
    Types[shared-types]
  end
  Web --> API
  Admin --> API
  Worker --> Redis
  API --> DB
  API --> Vault
  API --> Finance
  Connectors --> API
```

---

## Product Principles

1. **Evidence first** — Conclusions trace to sources
2. **Official APIs first** — Scraping only when necessary
3. **Human review** for sensitive outputs
4. **Multi-tenant governance** — Permissions, audit, versioning
5. **Cost-aware architecture** — Right storage for the job

---

## Quick Links

- **Live Demo:** http://184.72.123.188:3003
- **API Docs:** http://184.72.123.188:3001/docs
- **Start Here:** `docs/Finance_Platform_Handoff.md`
- **Task Assignment:** `docs/Task-Assignment-Detailed.md`

---

## License

Proprietary. All rights reserved.

---

**Last Updated:** 11 August 2026
**Branch:** `8th-july-sprint`
**Project Status:** In Progress (90+ commits ahead of main)
