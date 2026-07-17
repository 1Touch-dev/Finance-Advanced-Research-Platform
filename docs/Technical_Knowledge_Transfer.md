# Finance Intelligence Platform — Technical Knowledge Transfer

**Date:** 16th July 2026
**For:** Anshuman Parmar (New Developer)
**Project:** Enterprise Intelligence Platform

---

## Table of Contents

1. [The Big Picture — What This Platform Does](#1-the-big-picture)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure — The Complete Map](#4-project-structure)
5. [Backend Deep Dive (FastAPI)](#5-backend-deep-dive)
6. [Frontend Deep Dive (Next.js)](#6-frontend-deep-dive)
7. [Data Sources & Connectors](#7-data-sources--connectors)
8. [Database Schema](#8-database-schema)
9. [Background Workers](#9-background-workers)
10. [How Data Flows — The Complete Journey](#10-how-data-flows)
11. [Key Files Reference](#11-key-files-reference)
12. [Running the Platform](#12-running-the-platform)
13. [Common Tasks & Where to Look](#13-common-tasks)

---

## 1. The Big Picture

### What This Platform Does

Think of this as a **Bloomberg Terminal meets FBI Intelligence Database** for financial research. It answers questions like:

- "What stocks is Nancy Pelosi trading?"
- "Who are the biggest institutional holders of Apple?"
- "What's the intrinsic value of Tesla vs its market price?"
- "What government contracts does this company have?"
- "What's the sentiment around this stock in the news?"
- "Show me the corporate structure and key people of this entity"

### The Three Products

James (the client) has envisioned three connected products:

| Product | Description | Status |
|---------|-------------|--------|
| **Finance Intelligence Platform** | This repo — the one you're working on | Live |
| **Jarvis Nexus Dashboard** | Executive operating system for KPIs/agents | Spec written, not built |
| **AI Agent Team** | B2B/B2C outreach agents for SaaS products | Concept only |

You're working on Product #1.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER'S BROWSER                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌──────────┐    ┌──────────┐    ┌──────────┐
            │   WEB    │    │  ADMIN   │    │   API    │
            │  :3000   │    │  :3002   │    │  :3001   │
            │ Next.js  │    │  React   │    │ FastAPI  │
            └──────────┘    └──────────┘    └──────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────────────────────┐
            │                    BACKEND API                         │
            │                                                        │
            │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
            │  │   Routes    │  │  Services   │  │ Connectors  │   │
            │  │ (endpoints) │──│  (logic)    │──│ (data fetch)│   │
            │  └─────────────┘  └─────────────┘  └─────────────┘   │
            └───────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
    ┌──────────────┐       ┌──────────────┐       ┌──────────────┐
    │  PostgreSQL  │       │  OpenSearch  │       │    MinIO     │
    │   :5432      │       │    :9200     │       │ (S3) :9000   │
    │  (main db)   │       │ (full-text)  │       │   (files)    │
    └──────────────┘       └──────────────┘       └──────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────────────────────┐
            │                 EXTERNAL DATA SOURCES                  │
            │                                                        │
            │  SEC EDGAR · FEC · USASpending · LDA · OFAC · Courts  │
            │  CoinGecko · yfinance · NewsAPI · RSS Feeds (50+)     │
            │  Apify (LinkedIn/PitchBook) · Apollo · Wikipedia      │
            └───────────────────────────────────────────────────────┘
```

### How the Three Apps Talk

```
┌────────────┐     HTTP/JSON      ┌────────────┐
│    WEB     │ ───────────────▶   │    API     │
│  (Next.js) │ ◀───────────────   │  (FastAPI) │
└────────────┘                     └────────────┘
      │                                  │
      │ Uses lib/api.js                  │ Reads from
      │ getApiBaseUrl()                  │ PostgreSQL
      │                                  │
      ▼                                  ▼
   Renders UI                     Calls Connectors
```

---

## 3. Technology Stack

### Backend (Python)

| Library | Version | Purpose |
|---------|---------|---------|
| **FastAPI** | 0.115+ | Web framework — creates REST API endpoints |
| **Uvicorn** | 0.29+ | ASGI server — runs the FastAPI app |
| **SQLAlchemy** | 2.0+ | ORM — talks to PostgreSQL |
| **psycopg** | 3.2+ | PostgreSQL driver (binary) |
| **Pydantic** | v2 | Data validation and settings |
| **httpx** | 0.27+ | HTTP client for calling external APIs |
| **yfinance** | latest | Yahoo Finance data (stock prices, fundamentals) |
| **feedparser** | latest | RSS feed parsing |
| **boto3** | 1.34+ | AWS S3 client (used for MinIO) |
| **opensearch-py** | 2.4+ | OpenSearch client (full-text search) |
| **reportlab** | 4.0+ | PDF generation |
| **python-docx** | 1.1+ | Word document generation |
| **apify-client** | 3.0+ | Apify web scraping platform |

### Frontend (JavaScript)

| Library | Version | Purpose |
|---------|---------|---------|
| **Next.js** | 12.x | React framework with file-based routing |
| **React** | 17.x | UI library |
| **TailwindCSS** | 3.4+ | Utility-first CSS framework |
| **Recharts** | 3.8+ | Charting library (line charts, bar charts) |
| **SWR** | 2.4+ | Data fetching with caching |
| **Lucide React** | 1.23+ | Icon library |
| **Radix UI** | latest | Accessible UI primitives (tabs, tooltips) |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| **PostgreSQL 13** | Main database — stores entities, reports, relationships |
| **OpenSearch 2.11** | Full-text search across articles and reports |
| **Redis 6** | Job queue for background workers |
| **MinIO** | S3-compatible object storage for files/PDFs |
| **PM2** | Process manager for Node.js and Python processes |
| **Docker Compose** | Container orchestration for local dev |

---

## 4. Project Structure — The Complete Map

```
Finance-Advanced-Research-Platform/
│
├── apps/                          # All applications live here
│   │
│   ├── api/                       # THE BACKEND (FastAPI)
│   │   ├── app/
│   │   │   ├── main.py            # FastAPI entry point — all routers registered here
│   │   │   │
│   │   │   ├── api/               # API Route Files (endpoints)
│   │   │   │   ├── market.py      # /market/* — stock data, news, crypto, etc.
│   │   │   │   ├── intelligence.py # /intelligence/* — entity dossiers
│   │   │   │   ├── entities.py    # /entities/* — entity CRUD
│   │   │   │   ├── graph.py       # /graph/* — relationship network
│   │   │   │   ├── tracking.py    # /tracking/* — entity monitoring
│   │   │   │   ├── registry.py    # /registry/* — US state registries
│   │   │   │   ├── search.py      # /search/* — global search
│   │   │   │   └── ...            # 15+ more route files
│   │   │   │
│   │   │   ├── connectors/        # Data Fetchers (external API calls)
│   │   │   │   ├── yfinance_connector.py      # Yahoo Finance (prices, fundamentals)
│   │   │   │   ├── crypto_connector.py        # CoinGecko (crypto data)
│   │   │   │   ├── gov_trading_connector.py   # Congress trading (STOCK Act)
│   │   │   │   ├── rss_worker.py              # RSS feeds polling
│   │   │   │   ├── osint_connector.py         # OSINT tools (username search)
│   │   │   │   ├── multi_agent_intelligence.py # 4-agent investment analysis
│   │   │   │   ├── valuation_connector.py     # DCF valuation model
│   │   │   │   ├── institutional_tracker.py   # 13F filings
│   │   │   │   ├── company_deep_connector.py  # SEC EDGAR deep dive
│   │   │   │   ├── apify_connector.py         # LinkedIn/PitchBook scraping
│   │   │   │   └── ...
│   │   │   │
│   │   │   ├── services/          # Business Logic Layer
│   │   │   │   ├── intelligence_service.py   # HUGE file — generates entity reports
│   │   │   │   ├── tracking_service.py       # Entity monitoring logic
│   │   │   │   ├── rag_chat_service.py       # RAG chat with entities
│   │   │   │   ├── pdf_service.py            # PDF report generation
│   │   │   │   ├── openai_client.py          # OpenAI API wrapper
│   │   │   │   ├── anthropic_client.py       # Claude API wrapper
│   │   │   │   └── ...
│   │   │   │
│   │   │   ├── models/            # Database Models (SQLAlchemy)
│   │   │   │   ├── entities.py    # Entity, EntityIdentifier, Relationship
│   │   │   │   ├── reports.py     # Report, ReportSection, Claim
│   │   │   │   ├── evidence.py    # Evidence records
│   │   │   │   └── ...
│   │   │   │
│   │   │   ├── core/              # Core utilities
│   │   │   │   └── logging.py
│   │   │   │
│   │   │   ├── db/                # Database connection
│   │   │   │   └── session.py
│   │   │   │
│   │   │   └── auth/              # Authentication (JWT)
│   │   │
│   │   ├── pyproject.toml         # Python dependencies
│   │   └── Dockerfile
│   │
│   ├── web/                       # THE FRONTEND (Next.js)
│   │   ├── pages/                 # File-based routing (URL = filename)
│   │   │   ├── index.js           # / — Dashboard homepage
│   │   │   ├── stock.js           # /stock — Stock analysis
│   │   │   ├── valuation.js       # /valuation — DCF valuation
│   │   │   ├── company.js         # /company — Deep company analysis
│   │   │   ├── institutional.js   # /institutional — 13F tracker
│   │   │   ├── gov-trading.js     # /gov-trading — Congress trading
│   │   │   ├── crypto.js          # /crypto — Crypto intelligence
│   │   │   ├── expert-analysis.js # /expert-analysis — News sentiment
│   │   │   ├── intelligence.js    # /intelligence — Entity reports list
│   │   │   ├── intelligence/[id].js # /intelligence/123 — Single report
│   │   │   ├── search.js          # /search — Global search
│   │   │   ├── registry.js        # /registry — OSINT/entity registry
│   │   │   ├── graph.js           # /graph — Relationship graph
│   │   │   ├── economics.js       # /economics — FRED/BEA data
│   │   │   ├── _app.js            # App wrapper (Layout applied here)
│   │   │   └── _document.js       # HTML document wrapper
│   │   │
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   └── Layout.js      # Sidebar navigation + header
│   │   │   └── styles/
│   │   │       └── globals.css    # Global CSS (dark theme)
│   │   │
│   │   ├── lib/
│   │   │   └── api.js             # API base URL helper
│   │   │
│   │   ├── package.json
│   │   ├── tailwind.config.js
│   │   └── Dockerfile
│   │
│   ├── admin/                     # Admin Dashboard (React CRA)
│   │   ├── src/
│   │   │   ├── App.js
│   │   │   └── index.js
│   │   └── Dockerfile
│   │
│   └── worker/                    # Background Job Worker (Node.js)
│       └── src/
│           └── index.js           # Bull queue processor
│
├── packages/                      # Shared Packages
│   ├── connectors/                # Government data connectors
│   │   ├── us/                    # US-specific connectors
│   │   │   ├── sec/edgar.py       # SEC EDGAR filings
│   │   │   ├── fec/fec.py         # FEC campaign finance
│   │   │   ├── lda/lda.py         # Lobbying Disclosure Act
│   │   │   ├── fara/fara.py       # Foreign Agents Registration
│   │   │   ├── ofac/ofac.py       # OFAC sanctions
│   │   │   ├── courtlistener/     # Federal court cases
│   │   │   ├── usaspending/       # Government contracts
│   │   │   ├── state_registry/    # 51 US state business registries
│   │   │   └── ...
│   │   └── connectors/sdk.py      # Base connector SDK
│   │
│   └── finance/                   # Shared finance utilities
│
├── docs/                          # Documentation
├── reports/                       # Sprint reports
├── tests/                         # Test files
│
├── docker-compose.yml             # Local dev infrastructure
├── ecosystem.config.js            # PM2 process configuration
├── .env                           # Environment variables (API keys)
└── README.md
```

---

## 5. Backend Deep Dive (FastAPI)

### Entry Point: `apps/api/app/main.py`

This is where the FastAPI app is created and all routers are registered:

```python
app = FastAPI(title="Identity & Collaboration API")

# CORS middleware — allows frontend to call API
app.add_middleware(CORSMiddleware, allow_origins=[...])

# Register all routers (each file in api/ is a router)
app.include_router(core_router)        # /health, /
app.include_router(market_router)      # /market/*
app.include_router(intelligence_router) # /intelligence/*
app.include_router(entities_router)    # /entities/*
# ... 15+ more routers
```

### Router Pattern: `apps/api/app/api/*.py`

Each router file defines endpoints for a specific feature:

```python
# apps/api/app/api/market.py

from fastapi import APIRouter
from app.connectors.yfinance_connector import yf_fundamentals

router = APIRouter(prefix="/market")

@router.get("/yf/fundamentals")
def get_fundamentals(ticker: str):
    """GET /market/yf/fundamentals?ticker=AAPL"""
    return yf_fundamentals(ticker)
```

### Connector Pattern: `apps/api/app/connectors/*.py`

Connectors are pure functions that fetch data from external sources:

```python
# apps/api/app/connectors/yfinance_connector.py

import yfinance as yf

def yf_fundamentals(ticker: str) -> dict:
    """
    Fetch fundamentals from Yahoo Finance.
    Returns dict with P/E, EPS, revenue, etc.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "trailingPE": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "marketCap": info.get("marketCap"),
            # ... more fields
        }
    except Exception as e:
        return {"error": str(e)}
```

### Service Pattern: `apps/api/app/services/*.py`

Services contain complex business logic:

```python
# apps/api/app/services/intelligence_service.py

def generate_intelligence_report(entity_name: str, db: Session) -> dict:
    """
    Generates a full entity dossier by:
    1. Calling SEC connector
    2. Calling FEC connector
    3. Calling USASpending connector
    4. Calling Apify for LinkedIn/news
    5. Using GPT-4 to synthesize narrative
    6. Storing in database
    """
    # ... 2000+ lines of logic
```

### The Big Picture Flow

```
HTTP Request
    │
    ▼
┌───────────┐     ┌───────────┐     ┌───────────┐
│  Router   │────▶│  Service  │────▶│ Connector │
│ (endpoint)│     │  (logic)  │     │ (API call)│
└───────────┘     └───────────┘     └───────────┘
                        │
                        ▼
                ┌───────────────┐
                │   Database    │
                │  (PostgreSQL) │
                └───────────────┘
```

---

## 6. Frontend Deep Dive (Next.js)

### File-Based Routing

In Next.js, the URL structure matches the file structure:

| File | URL |
|------|-----|
| `pages/index.js` | `/` |
| `pages/stock.js` | `/stock` |
| `pages/intelligence/[id].js` | `/intelligence/123` |
| `pages/entities/[id].js` | `/entities/456` |

### Page Component Pattern

Every page follows this pattern:

```jsx
// pages/stock.js

import { useState } from 'react'
import { getApiBaseUrl } from '../lib/api'

const API = typeof window !== 'undefined' ? getApiBaseUrl() : ''

export default function StockPage() {
  const [ticker, setTicker] = useState('')
  const [data, setData] = useState(null)

  const fetchData = async () => {
    const res = await fetch(`${API}/market/yf/snapshot?ticker=${ticker}`)
    const json = await res.json()
    setData(json)
  }

  return (
    <div>
      <input value={ticker} onChange={e => setTicker(e.target.value)} />
      <button onClick={fetchData}>Analyze</button>
      {data && <pre>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  )
}
```

### Layout Component

`src/components/Layout.js` wraps every page:

```jsx
// Simplified
export default function Layout({ children }) {
  return (
    <div style={{ display: 'flex' }}>
      {/* Sidebar navigation */}
      <aside>
        <Link href="/stock">Stock</Link>
        <Link href="/crypto">Crypto</Link>
        {/* ... more links */}
      </aside>

      {/* Main content */}
      <main>{children}</main>
    </div>
  )
}
```

### API Base URL Helper

```javascript
// lib/api.js

export function getApiBaseUrl() {
  // If configured in env, use that
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }
  // Otherwise, use same hostname with port 3001
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:3001`
  }
  return 'http://localhost:3001'
}
```

### Styling

The app uses TailwindCSS + CSS variables for theming:

```css
/* src/styles/globals.css */

:root {
  --bg: #0a0e1a;          /* Main background */
  --bg-elev-1: #101828;   /* Card background */
  --text: #e2e8f0;        /* Primary text */
  --text-soft: #94a3b8;   /* Secondary text */
  --brand: #6366f1;       /* Indigo accent */
  --line: #1e293b;        /* Borders */
}
```

---

## 7. Data Sources & Connectors

### Government Data (Free, No API Key)

| Source | Connector | Data |
|--------|-----------|------|
| **SEC EDGAR** | `packages/connectors/us/sec/edgar.py` | Company filings (10-K, 10-Q, 8-K), insider trades |
| **FEC** | `packages/connectors/us/fec/fec.py` | Campaign contributions, PAC filings |
| **USASpending** | `packages/connectors/us/usaspending/` | Federal contracts, grants |
| **LDA.gov** | `packages/connectors/us/lda/lda.py` | Lobbying disclosures |
| **FARA** | `packages/connectors/us/fara/fara.py` | Foreign agent registrations |
| **OFAC** | `packages/connectors/us/ofac/ofac.py` | Sanctions lists |
| **CourtListener** | `packages/connectors/us/courtlistener/` | Federal court cases |
| **State Registries** | `packages/connectors/us/state_registry/` | 51 state business registries |

### Financial Data

| Source | Connector | Data |
|--------|-----------|------|
| **yfinance** | `yfinance_connector.py` | Stock prices, fundamentals, options |
| **CoinGecko** | `crypto_connector.py` | Crypto prices, market data |
| **FRED** | `financial_news_connector.py` | Economic indicators (GDP, CPI) |
| **House Clerk** | `gov_trading_connector.py` | Congress stock trades |

### News & Media

| Source | Connector | Data |
|--------|-----------|------|
| **RSS Feeds (50+)** | `rss_worker.py` | News from Bloomberg, Reuters, etc. |
| **NewsAPI** | `financial_news_connector.py` | News search |
| **Guardian** | `financial_news_connector.py` | UK news |
| **Google News** | `apify_connector.py` | News aggregation |

### Scraping & OSINT

| Source | Connector | Data |
|--------|-----------|------|
| **Apify** | `apify_connector.py` | LinkedIn, PitchBook |
| **Apollo** | `apollo_connector.py` | Company org charts, emails |
| **OSINT** | `osint_connector.py` | Username search (40 platforms) |

---

## 8. Database Schema

### Core Tables

```sql
-- Entities (people, companies, organizations)
entities
├── id (PK)
├── name
├── kind ('person', 'org', 'company')
├── canonical (boolean)
└── meta (JSON)

-- Relationships between entities
relationships
├── id (PK)
├── src_entity_id (FK → entities)
├── dst_entity_id (FK → entities)
├── kind ('works_for', 'invested_in', 'lobbied_for')
└── meta (JSON)

-- Intelligence reports
reports
├── id (PK)
├── entity_id (FK → entities)
├── kind ('entity_network_intel')
├── status ('draft', 'published')
└── created_at

-- Report sections (each section of a dossier)
report_sections
├── id (PK)
├── report_id (FK → reports)
├── title ('SEC Filings', 'Lobbying', etc.)
├── content (text)
└── order_index

-- RSS articles
rss_articles
├── id (PK)
├── source_id (FK → rss_sources)
├── title
├── url
├── published_at
├── content_hash (dedup)
└── matched_entities (array)
```

---

## 9. Background Workers

### PM2 Process Manager (`ecosystem.config.js`)

PM2 runs multiple processes simultaneously:

```javascript
module.exports = {
  apps: [
    {
      name: 'finance-api',          // FastAPI backend
      cwd: './apps/api',
      script: '../../venv/bin/uvicorn',
      args: 'app.main:app --host 0.0.0.0 --port 3001',
    },
    {
      name: 'finance-web',          // Next.js frontend
      cwd: './apps/web',
      script: 'npm',
      args: 'run dev -- -p 3003',
    },
    {
      name: 'rss-poller',           // RSS feed worker
      cwd: './apps/api',
      script: '../../venv/bin/python3',
      args: '-m app.connectors.rss_worker --loop',
    },
  ],
}
```

### RSS Worker (`rss_worker.py`)

Runs every 15 minutes via PM2:

```python
# Polls 50 RSS feeds
# Stores articles in PostgreSQL
# Tags articles with matched entities (Apple, Tesla, etc.)
```

### Bull Queue Worker (`apps/worker/src/index.js`)

Processes background jobs via Redis:

```javascript
const connectorQueue = new Queue('connector-runs', redisUrl)

connectorQueue.process(async (job) => {
  // Run Python connector script
  // e.g., SEC EDGAR refresh
})
```

---

## 10. How Data Flows — The Complete Journey

### Example: User Analyzes AAPL Stock

```
1. User visits /stock, enters "AAPL"
   │
   ▼
2. Frontend calls: GET http://localhost:3001/market/yf/snapshot?ticker=AAPL
   │
   ▼
3. market.py router receives request
   │
   ├── Calls yfinance_connector.yf_snapshot("AAPL")
   │   │
   │   └── yfinance library calls Yahoo Finance API
   │       └── Returns: price, P/E, market cap, etc.
   │
   ├── Calls technicals_connector.compute_all_technicals("AAPL")
   │   │
   │   └── Calculates: SMA, EMA, RSI, MACD, Bollinger Bands
   │
   └── Calls multi_agent_intelligence.get_investment_report("AAPL")
       │
       ├── FundamentalsAgent analyzes P/E, margins, ROE
       ├── TechnicalAgent analyzes trend, RSI, support/resistance
       ├── SentimentAgent analyzes news bullish/bearish ratio
       └── RiskAgent calculates Beneish M-score, Altman Z-score
           │
           └── SynthesisAgent combines scores → BUY/HOLD/SELL
   │
   ▼
4. JSON response sent to frontend
   │
   ▼
5. Frontend renders stock analysis UI
```

### Example: User Generates Entity Intelligence Report

```
1. User enters "Apple Inc" on /intelligence
   │
   ▼
2. Frontend calls: POST /intelligence/generate {"name": "Apple Inc"}
   │
   ▼
3. intelligence.py router calls intelligence_service.py
   │
   ▼
4. intelligence_service.py orchestrates:
   │
   ├── _fetch_sec() → SEC EDGAR filings
   ├── _fetch_fec() → Campaign contributions
   ├── _fetch_usaspending() → Government contracts
   ├── _fetch_lda() → Lobbying activity
   ├── _fetch_courts() → Lawsuits
   ├── fetch_linkedin_by_name() → People (via Apify)
   ├── fetch_pitchbook_company() → Investors (via Apify)
   ├── fetch_news() → Recent articles
   │
   └── GPT-4 synthesizes 9-section narrative
   │
   ▼
5. Report saved to PostgreSQL
   │
   ▼
6. Report ID returned to frontend → /intelligence/[id]
```

---

## 11. Key Files Reference

### Backend — Must Know Files

| File | What It Does | When to Edit |
|------|--------------|--------------|
| `apps/api/app/main.py` | App entry, router registration | Adding new routers |
| `apps/api/app/api/market.py` | All `/market/*` endpoints | Adding market features |
| `apps/api/app/connectors/yfinance_connector.py` | Stock data fetching | Fixing stock issues |
| `apps/api/app/connectors/crypto_connector.py` | Crypto data | Fixing crypto issues |
| `apps/api/app/connectors/rss_worker.py` | RSS polling | Adding news feeds |
| `apps/api/app/services/intelligence_service.py` | Report generation | Fixing reports |
| `ecosystem.config.js` | PM2 process config | Server setup |
| `.env` | API keys | Adding new keys |

### Frontend — Must Know Files

| File | What It Does | When to Edit |
|------|--------------|--------------|
| `apps/web/pages/*.js` | Page components | Adding/editing pages |
| `apps/web/src/components/Layout.js` | Sidebar nav | Adding nav items |
| `apps/web/lib/api.js` | API URL helper | API config |
| `apps/web/src/styles/globals.css` | Global styles | Theme changes |

---

## 12. Running the Platform

### Option 1: Docker Compose (Recommended for Local Dev)

```bash
# Start all services
docker-compose up -d

# Services:
# - web:        http://localhost:3000
# - api:        http://localhost:3001
# - admin:      http://localhost:3002
# - postgres:   localhost:5433
# - opensearch: localhost:9200
# - minio:      localhost:9000
```

### Option 2: PM2 (Production on Server)

```bash
# SSH into server
ssh finance-intelligence

# Start all processes
pm2 start ecosystem.config.js

# Check status
pm2 status

# View logs
pm2 logs finance-api
pm2 logs finance-web
```

### Option 3: Manual (Development)

```bash
# Terminal 1: Backend
cd apps/api
source ../../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload

# Terminal 2: Frontend
cd apps/web
npm run dev -- -p 3000
```

---

## 13. Common Tasks — Where to Look

### "Add a new API endpoint"

1. Create or edit a file in `apps/api/app/api/`
2. Add a router function with `@router.get()` or `@router.post()`
3. Import and register in `apps/api/app/main.py`

### "Add a new frontend page"

1. Create `apps/web/pages/mypage.js`
2. Add navigation link in `apps/web/src/components/Layout.js`

### "Integrate a new data source"

1. Create `apps/api/app/connectors/myconnector.py`
2. Write functions that return dicts
3. Import and call from a router

### "Fix a bug in stock analysis"

1. Check `apps/web/pages/stock.js` (frontend)
2. Check `apps/api/app/api/market.py` (endpoint)
3. Check `apps/api/app/connectors/yfinance_connector.py` (data)

### "Add a new API key"

1. Add to `.env` file: `MY_API_KEY=abc123`
2. Read in Python: `os.getenv("MY_API_KEY")`

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    QUICK REFERENCE                           │
├─────────────────────────────────────────────────────────────┤
│ Frontend:     apps/web/pages/*.js                           │
│ API Routes:   apps/api/app/api/*.py                         │
│ Connectors:   apps/api/app/connectors/*.py                  │
│ Services:     apps/api/app/services/*.py                    │
│ Models:       apps/api/app/models/*.py                      │
│ Layout:       apps/web/src/components/Layout.js             │
│ Styles:       apps/web/src/styles/globals.css               │
│ API URL:      apps/web/lib/api.js                           │
│ PM2 Config:   ecosystem.config.js                           │
│ Docker:       docker-compose.yml                             │
│ Env vars:     .env                                           │
├─────────────────────────────────────────────────────────────┤
│ Ports:                                                       │
│   Web:       3000 (Docker) / 3003 (PM2 prod)                │
│   API:       3001                                            │
│   Admin:     3002                                            │
│   Postgres:  5432 (Docker: 5433)                            │
│   OpenSearch: 9200                                           │
│   MinIO:     9000                                            │
│   Redis:     6379                                            │
└─────────────────────────────────────────────────────────────┘
```

---

*Document created: 16 July 2026*
*This is a living document — update as you learn more about the system.*
