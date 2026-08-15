# Finance Advanced Research Platform

**Enterprise-grade financial intelligence & investment research platform**

[![Status](https://img.shields.io/badge/Status-Active-brightgreen)]()
[![Branch](https://img.shields.io/badge/Branch-feature%2Fintelligence--correlation--full-blue)]()
[![Python](https://img.shields.io/badge/Python-3.11+-green)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)]()
[![Next.js](https://img.shields.io/badge/Next.js-12-green)]()
[![Quality Gate](https://img.shields.io/badge/Quality%20Gate%20ML-F1%3D0.895-success)]()

A multi-service monorepo for **evidence-first** public-record intelligence, investment research, relationship graphs, report generation with review workflows, and portfolio monitoring.

**Live Staging:** http://184.72.123.188:3003 (Web) | http://184.72.123.188:3001 (API) | http://184.72.123.188:3001/docs (API Docs)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Current Status Summary](#current-status-summary)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Features Status](#features-status)
  - [Completed Features](#-completed-features-40-items)
  - [In Progress Features](#-in-progress-features-3-items)
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
| **Quality Gate System** | LLM Judge + ML Classifier (F1=0.895) for automated report quality assurance |
| **50-State Registry** | Company entity search across all US jurisdictions |
| **OSINT Enrichment** | Apollo.io, OpenCorporates, GLEIF, FinCEN integrations |

---

## Current Status Summary

| Metric | Count |
|--------|-------|
| **API Endpoints** | 447 routes |
| **Frontend Pages** | 42 pages |
| **Database Models** | 70 models |
| **Service Files** | 75 services |
| **Connector Files** | 43 connectors |
| **External APIs** | 20+ integrations |
| **Test Coverage** | 120+ tests (99.2% passing) |
| **Quality Classifier** | F1=0.895 (403 training samples) |

| Area | Status |
|------|--------|
| **Overall** | **14 Aug 2026 — Quality Gate ML improved to F1=0.895 (+131%), all non-GPU phases complete** |
| **Active branch** | `feature/intelligence-correlation-full` (ahead of main) |
| **Trade Alerts (F-03/F-04)** | Completed — PM2 every 4h, SendGrid/Twilio configured |
| **Congress.gov (F-05)** | Completed — 1,000 req/hr free API, live bills + Senate PTR |
| **RAG Chat** | Completed (Phase 1) — Vector + keyword + hybrid modes |
| **Quality Gate ML** | **Completed** — F1=0.895 classifier with Opus 4.5 synthetic data |
| **13F Position-Diff** | Completed — 45 tests pass, live Berkshire Hathaway diff verified |
| **Intelligence Activation** | Completed — Self-dealing, correlation, network, 8 services activated |

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
| **Quality Classifier** | Random Forest | scikit-learn |
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
│   │   │   ├── services/    # Business logic services (75 files)
│   │   │   │   ├── rag/     # RAG system (embeddings, vector, hybrid, rerank)
│   │   │   │   └── quality/ # Quality gates (judge, classifier, decision)
│   │   │   └── scripts/     # CLI scripts (scanners, training, migrations)
│   │   └── tests/           # Backend tests (120+ tests)
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

### Completed Features (40+ items)

#### Core Intelligence Module

| Feature | Description | Evidence |
|---------|-------------|----------|
| **9-Section Intelligence Dossiers** | Entity Profile, Investors, Gov Contracts, Lobbying, Political Exposure, Sanctions, Litigation, AI Narrative, Data Sources | 10+ reports persisted |
| **Entity Claim Tagging** | Every claim tagged DOCUMENTED / REPORTED / ANALYTICAL | Live in all reports |
| **PDF/Word/Excel/PPT Export** | All formats downloadable via `/intelligence/{id}/pdf\|word\|excel\|powerpoint` | Verified |
| **PayPal Mafia Demo Seeds** | Peter Thiel, Elon Musk, Reid Hoffman + Thiel/Defense network | Live |
| **Click-to-Investigate** | Capitalized entity names in reports are clickable → new report | Live |

#### Quality Gate System (NEW - 14 Aug 2026)

| Feature | Description | Status |
|---------|-------------|--------|
| **LLM Judge** | Claude-powered quality evaluation with 5-dimension scoring | Completed |
| **ML Classifier** | Random Forest classifier (F1=0.895) for fast quality triage | **Completed** |
| **Synthetic Data Generator** | Opus 4.5-powered high-quality report generation | Completed |
| **Label Logging** | Automatic training data collection (403 samples) | Completed |
| **Decision Layer** | Mode=rules/judge/ml/blend with fallback chain | Completed |

**Quality Classifier Stats:**
- F1 Score: **0.895** (up from 0.387)
- Precision: **0.941**
- Recall: **0.854**
- Training Samples: **403** (124 publishable, 279 non-publishable)
- Features: **22** (12 rule + 6 text + 4 interaction)

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

#### Intelligence Activation Services (NEW)

| Service | Lines | Purpose | Status |
|---------|-------|---------|--------|
| **Self-dealing Analysis** | 436 | NVIDIA self-dealing detection | Completed |
| **Co-investment Network** | 400 | Find investors of same companies | Completed |
| **Founder Correlations** | 623 | PayPal-mafia / who-studied-together | Completed |
| **Deep Comparative** | 1,134 | Deep multi-company comparison | Completed |
| **Correlation Service** | 528 | Pattern / correlation finding | Completed |
| **Contract Probability** | 675 | Probability of delivery on contracts | Completed |
| **Interactive Report** | 598 | Interactive searchable reports | Completed |
| **Network Analysis** | 1,659 | Entity network intelligence | Completed |

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

### In Progress Features (3 items — GPU-Dependent)

| Feature | Description | Status | Blocker |
|---------|-------------|--------|---------|
| **Fine-tune Embeddings (Phase 2.3)** | Domain-specific embedding model | Data ready | GPU infrastructure |
| **Production Embedding Swap (Phase 2.5)** | Deploy fine-tuned embeddings | — | Depends on 2.3 |
| **Narrative Distillation (Phase 4.3)** | Fine-tune Llama/Qwen for report generation | Data ready | GPU infrastructure |

---

### Remaining Features (72 items prioritized)

#### Band A — Conversion & Retention Blockers (14 items) — MOSTLY DONE

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | Published pricing page | ✅ Done | `pages/pricing.js` |
| 2 | Renewal notice + one-click cancel | ✅ Done | `api/billing.py` |
| 3 | Reachable human support | ✅ Done | `api/support.py` |
| 4 | Honest status page | ✅ Done | `api/status.py` |
| 5 | Internal linking (SEO) | ✅ Done | `api/seo.py` |
| 6 | Sitemaps | ✅ Done | `api/seo.py` |
| 7 | Freshness engine | ⚠️ Partial | Cron not wired |
| 8 | Editorial workflow | ✅ Done | `api/editorial.py` |
| 9 | Compliance guardrails | ✅ Done | `api/compliance_content.py` |
| 10 | A/B experiments | ✅ Done | `api/experiments.py` |
| 11 | AI visibility tracking | ✅ Done | `api/ai_visibility.py` |
| 12 | Browser extension | ⚠️ Partial | Stub only |
| 13 | Portable corpora (export/API) | ✅ Done | `api/export.py` |
| 14 | 13F honesty layer | ✅ Done | `api/honesty.py` |

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
GET  /intelligence/self-dealing           — Self-dealing analysis
GET  /intelligence/network                — Network analysis
GET  /intelligence/correlation            — Correlation analysis
GET  /intelligence/contract-probability   — Contract probability
```

#### Quality Routes (`/quality/*` — NEW)

```
POST /quality/evaluate                    — Evaluate report quality
GET  /quality/stats                       — Classifier statistics
POST /quality/train                       — Trigger classifier retraining
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
| **OpenAI** | GPT-4o mini for intelligence narratives, embeddings | Active |
| **Anthropic Claude** | LLM Judge, Opus 4.5 synthetic data generation | Active |
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
| `/intelligence/self-dealing` | Self-dealing analysis | Live |
| `/intelligence/network` | Network analysis | Live |
| `/intelligence/correlation` | Correlation analysis | Live |
| `/intelligence/contract-probability` | Contract probability | Live |
| `/intelligence/interactive-report` | Interactive searchable reports | Live |
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
# All tests
python -m pytest tests/ -q

# Specific test suites
python -m pytest tests/test_rag_vector.py -q           # RAG tests (34 pass)
python -m pytest tests/test_quality_classifier.py -q   # Quality tests (8 pass)
python -m pytest tests/test_market_13f_*.py -q         # 13F tests (45 pass)

# Trade alert scanners (dry-run)
python -m app.scripts.run_big_trade_scan --dry-run
python -m app.scripts.run_investment_alert_scan --dry-run

# Quality classifier training
python -m app.scripts.train_quality_classifier_v2

# Generate synthetic training data
python -m app.scripts.generate_publishable_synthetic --n 100
```

### Environment Variables

Copy `.env.example` to `.env`. Key variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/finance_db

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic (for LLM Judge + Opus synthetic data)
ANTHROPIC_API_KEY=sk-ant-...

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

# Quality Gate
QUALITY_MODEL_PATH=app/models/quality_classifier.joblib
QUALITY_LABEL_LOG=on
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
| `docs/AI-Model-Training-Roadmap.md` | Phase 1-4 AI roadmap (Phase 1-3 complete) |
| `docs/Quality-Judge.md` | Quality Gate system design + classifier details |
| `docs/RAG-Upgrade-Plan.md` | Vector RAG design & operations |
| `docs/Task-Assignment-Detailed.md` | Post-merge task breakdown |
| `docs/Feature-Roadmap-Prioritized.md` | Prioritized feature backlog (72 items) |
| `MASTER_TASK_STATUS.md` | Single source of truth for project status |
| `docs/CONTRIBUTING.md` | Contribution guidelines |
| `docs/api/` | API integration guides |
| `docs/architecture/` | System architecture decisions |

---

## AI Model Training Roadmap

### Phase Status (as of 14 Aug 2026)

| Phase | Description | Status | Completion |
|-------|-------------|--------|------------|
| **Phase 1** | Vector search swap-in (no training) | **Completed** | 100% |
| **Phase 2** | Fine-tune embeddings on domain data | **Partial** | 60% |
| **Phase 3** | Quality-gate ML classifier | **Completed** | 100% |
| **Phase 4** | Distill narrative generator | **Partial** | 70% |

### Phase 2: Fine-tune Embeddings (60% Complete)

| Sub-Phase | Description | Status |
|-----------|-------------|--------|
| 2.1 | Claim-pair extraction pipeline | ✅ Complete |
| 2.2 | RAG query logging for training data | ✅ Complete |
| 2.3 | Fine-tuning infrastructure (RunPod) | ❌ **Requires GPU** |
| 2.4 | A/B evaluation framework | ✅ Complete |
| 2.5 | Production swap to fine-tuned model | ❌ **Requires trained model** |

### Phase 3: Quality Classifier (100% Complete)

| Metric | Value |
|--------|-------|
| **F1 Score** | 0.895 |
| **Precision** | 0.941 |
| **Recall** | 0.854 |
| **Algorithm** | Random Forest with threshold optimization |
| **Training Samples** | 403 (124 publishable, 279 non-publishable) |
| **Features** | 22 (12 rule + 6 text + 4 interaction) |

### Phase 4: Narrative Distillation (70% Complete)

| Sub-Phase | Description | Status |
|-----------|-------------|--------|
| 4.1 | Narrative logging | ✅ Complete |
| 4.2 | Human edit collection API | ✅ Complete |
| 4.3 | Fine-tune Llama/Qwen | ❌ **Requires GPU** |
| 4.4 | Narrative A/B evaluation | ✅ Complete |
| 4.5 | Production integration with fallback | ✅ Complete |

### Scripts for AI Training

```bash
# Train quality classifier (v2 with enhanced features)
python -m app.scripts.train_quality_classifier_v2

# Generate high-quality synthetic data using Opus 4.5
python -m app.scripts.generate_publishable_synthetic --n 100

# Evaluate RAG retrieval quality
python -m app.scripts.rag_eval

# Generate synthetic labels (original generator)
python -m app.scripts.generate_synthetic_labels --n 200
```

---

## Roadmap & Sprint Sequence

### Recommended Sprint Sequence

1. **Sprint 1-2:** Band A Backend (8 items) — ✅ DONE
2. **Sprint 2-3:** Band A Frontend + Full-stack (6 items) — ✅ MOSTLY DONE
3. **Sprint 4-6:** Band B Backend (12 items) — Start with #31 (docket-disclosure)
4. **Sprint 7-8:** Band B Full-stack (4 items) — Filing redline (#15)
5. **Sprint 9+:** Band C as needed based on user feedback

### Immediate Next Steps

1. **Set up GPU infrastructure (RunPod)** — Unblock Phases 2.3, 2.5, 4.3
2. **Fine-tune embeddings** — Domain-specific vector search
3. **Fine-tune narrative model** — Cheaper, faster report generation
4. **Band B features** — Filing redline, private document ingestion

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
    Quality[Quality Gate ML]
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
  API --> Quality
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
6. **Quality assurance** — ML-powered quality gates (F1=0.895)

---

## Quick Links

- **Live Demo:** http://184.72.123.188:3003
- **API Docs:** http://184.72.123.188:3001/docs
- **Start Here:** `docs/Finance_Platform_Handoff.md`
- **Task Status:** `MASTER_TASK_STATUS.md`

---

## License

Proprietary. All rights reserved.

---

**Last Updated:** 14 August 2026
**Branch:** `feature/intelligence-correlation-full`
**Project Status:** Active (Quality Gate ML F1=0.895, 60% AI training complete)
