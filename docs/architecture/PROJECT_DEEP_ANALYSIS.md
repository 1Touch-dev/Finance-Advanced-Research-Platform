# Finance Advanced Research Platform - Complete Deep Analysis

> **Prepared for:** New Developer / Stakeholder with Zero Prior Knowledge
> **Source:** Finance_Platform_Handoff.md + Full Codebase Analysis
> **Date:** July 20, 2026
> **Active Branch:** `8th-july-sprint`
> **Live Platform:** http://184.72.123.188:3003
> **Live API:** http://184.72.123.188:3001
> **API Docs:** http://184.72.123.188:3001/docs

---

## Table of Contents

1. [What Is This Project?](#1-what-is-this-project)
2. [Why Does It Exist?](#2-why-does-it-exist)
3. [How Is It Built - Architecture](#3-how-is-it-built---architecture)
4. [Technology Stack](#4-technology-stack)
5. [All 13 Major Features Explained](#5-all-13-major-features-explained)
6. [All External API Integrations](#6-all-external-api-integrations)
7. [Repository Structure](#7-repository-structure)
8. [All API Endpoints Reference](#8-all-api-endpoints-reference)
9. [All Frontend Pages](#9-all-frontend-pages)
10. [What Is Done vs What Is Left](#10-what-is-done-vs-what-is-left)
11. [Project Timeline](#11-project-timeline)
12. [Known Bugs and Gotchas](#12-known-bugs-and-gotchas)
13. [How to Run Locally](#13-how-to-run-locally)
14. [Environment Variables](#14-environment-variables)
15. [Key People and Contacts](#15-key-people-and-contacts)

---

## 1. What Is This Project?

The **Enterprise Intelligence and Investment Research Platform** is a full-stack financial intelligence workbench built for James (Thunder Marketing). It is **not** a simple stock screener or chatbot. Think of it as three powerful tools merged into one:

| Tool | What It Does |
|------|-------------|
| Bloomberg Terminal | Real-time market data, financial ratios, stock technicals, DCF valuation |
| OSINT Investigator | Government records, court filings, lobbying disclosures, sanctions, crypto wallets |
| AI Research Analyst | GPT-4o automatically writes fully cited intelligence dossiers on any company or person |

### The One-Line Purpose

You type in a company name like **Palantir Technologies** or a person like **Peter Thiel** and the platform automatically pulls data from 20+ government databases and financial APIs, then produces a fully cited multi-section intelligence report in **20-45 seconds**.

### Who It Is For

| User Type | How They Use It |
|-----------|----------------|
| Hedge fund analysts | Research before investing - check government contracts, insider trades, institutional holder shifts |
| Due diligence firms | Investigate legal exposure, sanctions risk, political connections before acquisition |
| Investigative journalists | Find lobbying activity, foreign agent registrations, court records, offshore connections |
| Compliance teams | Run OFAC sanctions checks and FEC political donation searches |
| Investment bankers | Run DCF valuations, compare 13F positions, analyze analyst consensus |

### Current Status (July 13, 2026)

- Fully live on AWS EC2 at http://184.72.123.188:3003
- 60+ API endpoints, 22+ frontend pages
- 2,000+ RSS articles ingested and auto-tagged
- All major features production-ready

---

## 2. Why Does It Exist?

Researching a company manually takes days across 12+ government websites.
**This platform does all of it automatically in under a minute, with every claim citing its original source.**

| Step | Manual Task Replaced |
|------|---------------------|
| 1 | SEC.gov - company filings (10-K, 10-Q, Form 4, 13F) |
| 2 | FEC.gov - political donation records |
| 3 | CourtListener - federal court cases |
| 4 | LDA.gov - lobbying registrations |
| 5 | OFAC - sanctions list check |
| 6 | DOJ FARA - foreign agent registrations |
| 7 | USASpending.gov - government contract awards |
| 8 | Yahoo Finance - stock technicals and fundamentals |
| 9 | FRED + Excel - manual DCF valuation model |
| 10 | 50+ RSS feeds - news monitoring |
| 11 | Etherscan - crypto wallet activity |
| 12 | House Clerk ZIP files - congressional stock trades |

### Product Principles

| Principle | What It Means |
|-----------|--------------|
| **Evidence First** | Every claim traces to a primary source (SEC, FEC, courts) |
| **Official APIs First** | Use government APIs before scraping anything |
| **Human Review** | Sensitive outputs flagged for analyst review |
| **Multi-tenant Governance** | Permissions, audit trails, versioning for enterprise use |
| **Cost-Aware** | Aggressive caching on rate-limited APIs (CoinGecko, Apollo) |

---

## 3. How Is It Built - Architecture

5 services run on AWS EC2 (IP: 184.72.123.188) managed by **PM2**.

### The 5 Running Services

| PM2 Name | Port | Status | Description |
|----------|------|--------|-------------|
| `finance-api` | 3001 | Online | FastAPI Python backend - all data and AI logic |
| `finance-web` | 3003 | Online | Next.js 12 frontend - all 22+ pages users see |
| `finance-admin` | 3002 | Online | React admin panel - ops and source health |
| `rss-poller` | -- | Online | RSS worker - pulls 50 feeds every 15 minutes |
| `daily-digest` | -- | Stopped | Cron at 6AM UTC - email/SMS watchlist digest |

### How a Request Flows

`
User types Palantir on /intelligence
  --> POST /intelligence/generate?entity_name=Palantir
  --> intelligence_service.py fans out to 11 connectors IN PARALLEL
        Wikipedia, SEC EDGAR, USASpending, LDA, FEC, FARA
        OFAC, CourtListener, Apollo.io, Apify, GPT-4o
  --> 9-section report saved to PostgreSQL
  --> JSON returned to frontend in 20-45 seconds
`

### The 5 Code Layers

| Layer | Path | Purpose |
|-------|------|---------|
| Route Handlers | `apps/api/app/api/` | 20 Python files, one per domain. Each file = one set of endpoints |
| Services | `apps/api/app/services/` | Business logic. `intelligence_service.py` (1500+ lines) is the core |
| Connectors | `apps/api/app/connectors/` | 16 files, each talks to one external API |
| Shared Packages | `packages/` | DCF model, technical indicators, 17 federal + 51 state connectors |
| DB Models | `apps/api/app/models/` | SQLAlchemy ORM for all PostgreSQL tables |

---

## 4. Technology Stack

| Layer | Technology | Version | Why It Was Chosen |
|-------|-----------|---------|-------------------|
| Backend API | FastAPI | Python 3.11 | Fast async Python, auto-generates Swagger docs at /docs |
| Database (production) | PostgreSQL | 13 | Reliable relational DB with GIN indexes for arrays |
| Database (local dev) | SQLite | -- | Zero-setup local development, no install needed |
| ORM | SQLAlchemy | -- | Works with both Postgres and SQLite transparently |
| Frontend | Next.js | 12 | SSR-capable React framework, file-based routing |
| UI Library | React | 17 | Component-based UI |
| Styling | Tailwind CSS | v3 | Utility-first CSS, dark theme, responsive |
| Charts | Recharts | -- | React-native charting for stock and sentiment data |
| Process Manager | PM2 | -- | Keeps all 5 services alive, auto-restart on crash |
| Background Jobs | Node.js + Bull + Redis | -- | Redis-backed queue for RSS polling |
| AI / LLM | OpenAI GPT-4o | -- | Intelligence report narratives, multi-agent synthesis |
| AI / LLM | Anthropic Claude | -- | Skills gateway fallback |
| Authentication | JWT + native bcrypt | -- | Stateless token auth, 24-hour expiry |
| Graph Visualization | Cytoscape.js | -- | Network graph rendering for entity relationships |
| Deployment | AWS EC2 | Ubuntu | Always-on cloud server |
| CI/CD | AWS Amplify | -- | Auto-deploy frontend from GitHub on push |
| PDF Export | ReportLab (Python) | -- | Programmatic multi-page PDF generation |
| Word Export | python-docx | -- | .docx report export |
| Excel Export | openpyxl | -- | .xlsx report export |
| PowerPoint Export | python-pptx | -- | .pptx presentation export |
| HTTP Client | requests / httpx | -- | Python HTTP calls to external APIs |
| RSS Parsing | feedparser | -- | RSS/Atom feed parsing for news worker |
| Stock Data | yfinance | -- | Yahoo Finance wrapper for price and fundamentals |

---

## 5. All 13 Major Features Explained

---

### Feature 1 - Intelligence Reports (`/intelligence`)

**This is the flagship feature.** You enter any company or person name and the system builds a fully cited 9-section intelligence dossier.

**Step-by-step flow:**

`
1. User types company/person name and clicks Generate
2. intelligence_service.py starts 11 parallel threads
3. Each thread calls one external data source
4. Results merged into 9 report sections with source tags
5. GPT-4o writes a 5-section analytical narrative essay
6. Full report saved to PostgreSQL for future access
7. User sees the complete report in 20-45 seconds
`

**The 9 Report Sections:**

| # | Section | Data Source | What It Returns |
|---|---------|------------|----------------|
| 1 | Entity Profile | Wikipedia REST API | Company background, founders, founding date, key products |
| 2 | Investors and Capital | SEC 13G/13D, Form D, FundedAPI | Institutional owners, private placements, startup funding rounds |
| 3 | Government Contracts | USASpending.gov | All federal contract awards with dollar amounts and agencies |
| 4 | Lobbying Activity | LDA.gov | Lobbying firms representing the company and issue areas |
| 5 | Political and Foreign Exposure | FEC, FARA (DOJ) | Campaign donations and foreign agent registrations |
| 6 | Sanctions and Compliance | OFAC / OpenSanctions | Direct name match against global sanctions lists |
| 7 | Litigation and Legal | CourtListener | Federal court filings mentioning this entity |
| 8 | OSINT Enrichment | Apollo.io, Apify | Org chart, key people, LinkedIn, Google News |
| 9 | Deep AI Narrative | OpenAI GPT-4o | 5-section analytical essay written by AI |

**Claim tagging on every fact:**
- `DOCUMENTED` - from a primary government or financial source
- `REPORTED` - from news or secondary source
- `ANALYTICAL` - AI inference or calculated value

**Export formats:** PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx)

**Key files:**
- `apps/api/app/api/intelligence.py` - REST routes for generation and export
- `apps/api/app/services/intelligence_service.py` - Main orchestrator (1,500+ lines)
- `apps/web/pages/intelligence.js` - Frontend page with PayPal Mafia seeds

---

### Feature 2 - Stock Analysis (`/stock`)

A full stock terminal with live price data, 35+ fundamentals, 15 technical indicators, and a 4-agent AI consensus.

**15 Technical Indicators (pure Python, no C library needed):**

| Indicator | Parameters | What It Measures |
|-----------|-----------|-----------------|
| SMA | 10, 20, 50, 200 periods | Trend direction - is price above or below its average? |
| EMA | 12, 26 periods | Faster trend signals than SMA |
| RSI | 14 periods | Momentum - above 70 = overbought, below 30 = oversold |
| MACD | 12/26/9 | Trend momentum - line, signal, and histogram |
| Bollinger Bands | 20 periods, 2 stddev | Volatility - upper/lower price bands |
| ATR | 14 periods | Average True Range - absolute price volatility |
| OBV | On-Balance Volume | Does volume confirm the price trend? |
| Stochastic | %K(14) + %D(3) | Momentum oscillator |
| Williams %R | 14 periods | Overbought/oversold like RSI |
| Rate of Change | 12 periods | % price change over period |
| Support/Resistance | 20-period pivot | Key price levels to watch |
| Golden Cross | SMA50 vs SMA200 | Bullish when SMA50 crosses above SMA200 |
| Death Cross | SMA50 vs SMA200 | Bearish when SMA50 crosses below SMA200 |

**4-Agent AI Consensus System:**

`
FundamentalsAgent --> scores P/E, margins, ROE, revenue growth      [0-100]
TechnicalAgent    --> scores trend, RSI, MACD crossovers             [0-100]
SentimentAgent    --> scores bullish vs bearish news ratio           [0-100]
RiskAgent         --> Beneish M-Score + Altman Z-Score + beta        [0-100]
        |
        v
SynthesisAgent: Composite = average of all 4 scores
  >= 70  --> BUY
  55-69  --> HOLD
  40-54  --> HOLD / REDUCE
  < 40   --> SELL
`

When OPENAI_API_KEY is set, GPT-4o-mini writes a narrative investment thesis. Fully rule-based fallback if no key.

**Key files:**
- `apps/api/app/connectors/yfinance_connector.py`
- `apps/api/app/connectors/technicals_connector.py`
- `apps/api/app/connectors/multi_agent_intelligence.py`
- `apps/web/pages/stock.js`

---

### Feature 3 - DCF Valuation (`/valuation`)

A full Discounted Cash Flow model using **real SEC EDGAR data** to calculate intrinsic share value.

**How the DCF model works step by step:**

`
Step 1: Fetch real Free Cash Flow history from SEC EDGAR XBRL (10-K filings)
Step 2: Calculate historical FCF CAGR (compound annual growth rate)
Step 3: Project 5 years of future FCF using that CAGR
Step 4: Calculate WACC using CAPM formula
         Risk-free rate = current 10-year Treasury yield from FRED API
         WACC = risk-free rate + (beta x 5.5% equity risk premium)
Step 5: Discount all projected FCFs back to present value
Step 6: Add terminal value at 2.5% perpetual growth rate
Step 7: Subtract net debt to get equity value
Step 8: Divide by shares outstanding = intrinsic value per share
Step 9: Compare intrinsic value vs current market price
`

**Three Scenarios:**

| Scenario | FCF Growth | WACC |
|----------|-----------|------|
| Bear (pessimistic) | CAGR minus 5% | WACC plus 1% |
| Base (expected) | Historical CAGR | Calculated WACC |
| Bull (optimistic) | CAGR plus 5% | WACC minus 1% |

**Valuation labels:** SIGNIFICANTLY UNDERVALUED / UNDERVALUED / FAIRLY VALUED / OVERVALUED / SIGNIFICANTLY OVERVALUED

**Filing Analysis tab** also parses actual 10-K/10-Q MD&A text from SEC for guidance signals, risk factors, and management commentary.

**Real test (AAPL):** Intrinsic .24 vs Market .63 = SIGNIFICANTLY OVERVALUED. WACC: 10.41%, Beta: 1.1

**Key files:** `apps/api/app/connectors/valuation_connector.py`, `apps/web/pages/valuation.js`

---

### Feature 4 - Deep Company Analysis (`/company`)

5-tab deep dive into any public company.

| Tab | Data Source | What It Shows |
|-----|------------|--------------|
| Overview | SEC EDGAR | CIK number, SIC code, state of incorporation, fiscal year end |
| Filings | SEC EDGAR | All 10-K, 10-Q, 8-K, DEF 14A with direct SEC viewer links |
| Cap Table | yfinance | Top 20 institutional + top 15 mutual fund holders with % and dollar value |
| Analyst | yfinance | Buy/Hold/Sell consensus, mean/high/low price targets, upgrade history |
| Earnings | yfinance | 8 quarters of EPS actual vs estimate, surprise %, next earnings date |

Also shows insider trades (Form 4): name, title, buy/sell, shares, dollar value, date.

**Key files:** `apps/api/app/connectors/company_deep_connector.py`, `apps/web/pages/company.js`

---

### Feature 5 - Expert Analysis (`/expert-analysis`)

Aggregates news and analyst signals for any stock ticker to measure market sentiment.

- Pulls articles from NewsAPI + The Guardian + internal RSS database
- Scores each article bullish/bearish using 100+ keyword dictionary
- Generates 16-week rolling sentiment trend chart
- Extracts key themes: AI, earnings, acquisitions, layoffs, regulatory risk
- Shows analyst upgrade/downgrade timeline with firm name, action, and date
- Outputs trend direction: IMPROVING / DETERIORATING / STABLE

**Real test (AAPL):** 93 articles, BULLISH, 42 bullish / 9 bearish, top theme: AI (81 mentions)

**Key files:** `apps/api/app/connectors/expert_analysis_connector.py`, `apps/web/pages/expert-analysis.js`

---

### Feature 6 - Institutional Intelligence (`/institutional`)

Tracks where big institutional money is positioned using SEC 13F filings.

> U.S. law requires any institution managing more than  in assets to file a quarterly 13F report disclosing all equity holdings. This data is public.

**What it shows:**
- Current institutional holders with shares, % held, and dollar value
- Position classification: Mega (>), Large (-), Mid (less than )
- Ownership breakdown: % insiders, % institutions, % public float
- Downloads and parses actual 13F-HR XML from SEC EDGAR for specific institution portfolios

**Tracked institutions:** BlackRock, Vanguard, Berkshire Hathaway, State Street, Fidelity, T. Rowe Price, JP Morgan, Goldman Sachs, Morgan Stanley, ARK Invest, Pershing Square

**Real test (AAPL):** BlackRock 353B, Vanguard 294B, State Street 186B

**Key files:** `apps/api/app/connectors/institutional_tracker.py`, `apps/web/pages/institutional.js`

---

### Feature 7 - Government Trading (`/gov-trading`)

Tracks stock trades made by U.S. Congress members (STOCK Act PTR disclosures) and corporate insiders (SEC Form 4).

**Congressional Trading (House PTR):**
The STOCK Act requires Congress members to report stock trades within 45 days. The House Clerk publishes annual ZIP files containing all PTR (Periodic Transaction Report) filings.
This platform downloads and parses those ZIP files automatically.

**Politician Tracker (15 named politicians):**

| Politician | Party | Chamber |
|-----------|-------|---------|
| Nancy Pelosi | D | House |
| Mitch McConnell | R | Senate |
| Marjorie Taylor Greene | R | House |
| Elizabeth Warren | D | Senate |
| Tommy Tuberville | R | Senate |
| Marco Rubio | R | Senate |
| Ted Cruz | R | Senate |
| Mark Kelly | D | Senate |
| Dan Crenshaw | R | House |
| Michael McCaul | R | House |
| Chuck Schumer | D | Senate |

For each politician: all PTR filings + sponsored legislation from Congress.gov.
Flags financially relevant bills (finance, defense, tech, health, energy).

**Corporate Insider Trades (SEC Form 4):**
Corporate insiders must file Form 4 within 2 business days of any trade. Fetched from SEC EDGAR EFTS.

**Key files:** `apps/api/app/connectors/gov_trading_connector.py`, `apps/web/pages/gov-trading.js`

---

### Feature 8 - Crypto Intelligence (`/crypto`)

Full cryptocurrency market dashboard with 3 tabs.

| Tab | What It Shows |
|-----|--------------|
| Market Dashboard | Global market cap, BTC dominance, top 14 coins, trending coins, whale alerts |
| Coin Detail | Full CoinGecko profile: supply, ATH, ATL, 7d/30d/1y change, categories |
| Wallet Lookup | ETH wallet (Etherscan): balance, ERC-20 tokens, transactions. BTC wallet (Blockchain.info): balance, history |

**Whale Alerts:** Detects large ETH transactions (>) via Etherscan - useful for tracking large holder moves.

**IMPORTANT:** 5-minute TTL cache on all CoinGecko responses. If top_coins is empty, wait 5 minutes - do not add more calls.

**Key files:** `apps/api/app/connectors/crypto_connector.py`, `apps/web/pages/crypto.js`

---

### Feature 9 - RSS News Intelligence

Continuous financial news monitoring from 50 curated RSS feeds.

| Category | Example Sources |
|----------|----------------|
| Finance | Bloomberg, Reuters, Financial Times, Wall Street Journal |
| Macro | CNBC, MarketWatch, Seeking Alpha |
| Crypto | CoinDesk, Decrypt, The Block |
| Government | Politico, The Hill, Roll Call |
| Tech | TechCrunch, Wired, Ars Technica |
| Asia/MENA/LATAM | Nikkei Asia, Arab News, MercoPress |

- PM2 process `rss-poller` runs every 15 minutes
- Auto-tags each article with up to 15 entity keywords (Apple, Tesla, Fed, Bitcoin, etc.)
- Stores all articles in PostgreSQL tables `rss_sources` and `rss_articles`
- 2,000+ articles ingested since deployment
- Every entity profile page has a News tab showing filtered articles

**Key files:** `apps/api/app/connectors/rss_worker.py`, `ecosystem.config.js`

---

### Feature 10 - OSINT and Entity Registry (`/registry`)

Open Source Intelligence tools for corporate and personal investigation.

**Apollo.io (paid plan):**
- Organization enrichment: industry, employee count, revenue range, description
- People search: find contacts at any company with title and email signals
- Org chart: C-suite and VP level executives
- Note: Apollo returns first_name + last_name_obfuscated on paid plan

**Username Enumeration (40 platforms checked in parallel):**
GitHub, Twitter/X, Reddit, Instagram, LinkedIn, YouTube, TikTok, Pinterest, Twitch, Snapchat, Medium, Substack, Dev.to, HackerNews, AngelList, Crunchbase, Keybase, GitLab, Stack Overflow, Kaggle, Telegram, Spotify, Steam, Xbox, and 16 more.

**Domain Intelligence:** WHOIS via RDAP, DNS records (A/MX/TXT via Google DoH), tech stack fingerprinting.

**Corporate Registries:** OpenCorporates (190+ countries), GLEIF (LEI lookup), FinCEN (Beneficial Ownership), ICIJ Offshore Leaks (Panama/Paradise/Pandora Papers), U.S. 50-State Registry (all 51 Secretary of State jurisdictions).

**Key files:** `apps/api/app/connectors/apollo_connector.py`, `apps/api/app/connectors/osint_connector.py`, `packages/connectors/us/state_registry/`

---

### Feature 11 - Economics (`/economics`)

Macroeconomic data from official U.S. government APIs.

- **FRED API (St. Louis Federal Reserve):** GDP, CPI inflation, federal funds rate, unemployment, 10-year Treasury yield. The Treasury yield is also used as the risk-free rate in all DCF calculations.
- **BEA API (Bureau of Economic Analysis):** Regional personal income by state, industry-level GDP, NIPA national accounts.

---

### Feature 12 - Relationship Graph (`/graph`)

A visual network map of how companies, people, and organizations connect to each other.

**How edges are created automatically:**
Every time an intelligence report is generated, the service writes relationship edges to the database.
Example edges written for a Palantir report:

`
Palantir --> funded_by      --> Peter Thiel
Palantir --> gov_contract   --> U.S. Army
Palantir --> lobbying       --> Mehlman Castagnetti firm
Palantir --> listed_at      --> SEC (CIK 0001321655)
Peter Thiel --> founded     --> Founders Fund
`

**Frontend (Cytoscape.js):** Interactive force-directed graph. Click any node to expand connections. Find paths between two entities. Export as PNG or JSON.

---

### Feature 13 - Authentication, Tracking, and Alerts

**Authentication:**
- JWT tokens with 24-hour expiry
- Native bcrypt password hashing (NOT passlib - known version conflict that causes startup crash)
- `POST /auth/register` - create account
- `POST /auth/login` - returns JWT token
- `GET /auth/me` - get current user (pass token as Bearer header)

**Watchlist and Tracking:**
- Add any entity to your personal watchlist
- PM2 cron `daily-digest` runs at 6AM UTC
- Sends email digest via SendGrid and/or SMS via Twilio

**Alert Inbox:**
- Severity levels: high / medium / low
- Acknowledge alerts to mark as seen
- Snooze any alert for 24 hours

---

## 6. All External API Integrations

### Currently Live and Active

| API Service | Used For | Cost |
|-------------|---------|------|
| OpenAI GPT-4o | Intelligence report narratives, multi-agent synthesis | Paid per token |
| Anthropic Claude | Skills gateway | Paid per token |
| Apollo.io (Paid Plan) | Org charts, C-suite enrichment, people search | Paid subscription |
| Apify | Google News scraping, LinkedIn scraping, PitchBook | Paid per run |
| NewsAPI | Financial and general news aggregation | Paid subscription |
| The Guardian API | UK and international news | Free with key |
| New York Times API | Article search | Free tier |
| Finnhub | Real-time market data | Paid / free tier |
| Financial Modeling Prep (FMP) | Financial statements, Beneish/Altman scores | Paid |
| Alpha Vantage | Additional market data fallback | Free tier |
| FRED (St. Louis Fed) | GDP, CPI, interest rates, risk-free rate | Free |
| BEA | GDP and regional income data | Free |
| Etherscan | ETH wallet lookup, whale alerts | Free tier |
| yfinance | Yahoo Finance: price, fundamentals, options | Free, no key |
| CoinGecko | Crypto market data, coin profiles | Free, no key, rate limited |
| FEC OpenData | Political contribution records | Free |
| CourtListener | Federal court litigation records | Free with token |
| UK Companies House | UK company search and officers | Free with key |
| SEC EDGAR | All SEC filings, XBRL data, company info | Free with User-Agent |
| USASpending.gov | Federal contracts and grants | Free |
| LDA.gov | Lobbying Disclosure Act registrations | Free |
| FARA (DOJ) | Foreign Agents Registration Act | Free |
| OFAC / OpenSanctions | Sanctions list name matching | Free |
| Blockchain.info | BTC wallet lookup | Free, no key |
| Wikipedia REST API | Company and person background | Free, no key |
| FundedAPI | Startup funding rounds | Free, rate limited |
| ICIJ Offshore Leaks | Panama/Paradise/Pandora Papers | Free, no key |
| OpenCorporates | Global company registry (190+ countries) | Free, rate limited |
| GLEIF | Legal Entity Identifier lookup | Free |
| FinCEN | Beneficial Ownership Information | Free |
| Congress.gov | Legislation data (DEMO_KEY - limited) | Needs paid key |
| SendGrid | Email alerts for watchlist digest | Configured |
| Twilio | SMS alerts for watchlist digest | Configured |

### Pending or Blocked Keys

| Key | Service | Status | Action Needed |
|-----|---------|--------|--------------|
| CA_SOS_API_KEY | California Secretary of State CBC API | Pending approval | Wait for calicodev.sos.ca.gov approval |
| ALEPH_API_KEY | ALEPH/OCCRP leaked document search | Account approval pending | Wait for OCCRP approval |
| COBALT_API_KEY | Cobalt SOS API | Deferred | Trial rate limited - defer for now |
| OIDC_CLIENT_ID | Google Workspace SSO | Waiting | Need credentials from James |

---

## 7. Repository Structure

Every folder and file explained:

`
Finance-Advanced-Research-Platform/
|
|-- apps/                         All runnable applications
|   |
|   |-- api/                      FastAPI Python backend (port 3001)
|   |   |-- app/
|   |   |   |-- api/              20 route handler files (one domain per file)
|   |   |   |   |-- market.py     47+ endpoints: stock, crypto, gov-trading, RSS, valuation
|   |   |   |   |-- intelligence.py  Report generation + PDF/Word/Excel/PPT export
|   |   |   |   |-- routes.py     Auth (register/login/me) + health + bootstrap
|   |   |   |   |-- entities.py   Entity CRUD, resolve, merge queue
|   |   |   |   |-- graph.py      Graph expand, pathfind, related nodes
|   |   |   |   |-- search.py     Global full-text search
|   |   |   |   |-- registry.py   50-state company registry endpoints
|   |   |   |   |-- tracking.py   Watchlist and alert management
|   |   |   |   |-- chat.py       RAG chat Q&A against saved reports
|   |   |   |   |-- skills.py     AI skills gateway (Anthropic/OpenAI)
|   |   |   |
|   |   |   |-- connectors/       16 external data connector files
|   |   |   |   |-- yfinance_connector.py        Price, fundamentals, options, holders
|   |   |   |   |-- technicals_connector.py      15 pure-Python technical indicators
|   |   |   |   |-- multi_agent_intelligence.py  4-agent BUY/HOLD/SELL consensus
|   |   |   |   |-- valuation_connector.py       DCF model + 10-K/10-Q MD&A parsing
|   |   |   |   |-- company_deep_connector.py    SEC XBRL, cap table, earnings, analyst
|   |   |   |   |-- expert_analysis_connector.py News sentiment + analyst timeline
|   |   |   |   |-- institutional_tracker.py     13F filings + institutional holder analysis
|   |   |   |   |-- gov_trading_connector.py     House PTR + Form 4 + politician tracker
|   |   |   |   |-- crypto_connector.py          CoinGecko + Etherscan + Blockchain.info
|   |   |   |   |-- rss_worker.py                50-feed RSS poller + PostgreSQL storage
|   |   |   |   |-- apollo_connector.py          Apollo.io org/people (paid plan)
|   |   |   |   |-- osint_connector.py           Username enumeration + domain intel
|   |   |   |   |-- private_company_connector.py OpenCorporates + GLEIF + FinCEN
|   |   |   |   |-- financial_news_connector.py  NewsAPI + Guardian + NYT + GDELT
|   |   |   |   |-- apify_connector.py           Social scraping: LinkedIn, Google News
|   |   |   |   |-- browser_research_agent.py    Headless browser fallback for non-API sources
|   |   |   |
|   |   |   |-- services/          Business logic layer
|   |   |   |   |-- intelligence_service.py  Core report orchestrator (1,500+ lines)
|   |   |   |   |-- openai_client.py         OpenAI API wrapper
|   |   |   |   |-- anthropic_client.py      Anthropic Claude wrapper
|   |   |   |   |-- pdf_service.py           ReportLab PDF generation
|   |   |   |
|   |   |   |-- models/             SQLAlchemy ORM table definitions
|   |   |   |   |-- entities.py     Entity, EntityIdentifier, Relationship
|   |   |   |   |-- reports.py      Report, ReportSection, Claim, ClaimEvidence
|   |   |   |   |-- models.py       RSSSource, RSSArticle, Watchlist, Alert
|   |   |   |   |-- registry.py     StateRegistryRecord table
|   |   |   |
|   |   |   |-- auth/              Authentication logic
|   |   |   |   |-- security.py    JWT creation + bcrypt hashing (use native bcrypt only)
|   |   |   |   |-- oidc.py        Google SSO routes (wired, credentials pending)
|   |   |   |
|   |   |   |-- main.py            FastAPI app startup - mounts all 18+ routers
|
|   |-- web/                       Next.js 12 frontend (port 3003)
|   |   |-- pages/                 25+ page components (file = URL route)
|   |   |   |-- index.js           Dashboard: stats bar, feature cards, quick search
|   |   |   |-- intelligence.js    Report generator with PayPal Mafia seed buttons
|   |   |   |-- stock.js           Stock analysis terminal
|   |   |   |-- valuation.js       DCF valuation page
|   |   |   |-- company.js         Deep company analysis (5 tabs)
|   |   |   |-- crypto.js          Crypto market dashboard
|   |   |   |-- gov-trading.js     Government trading + politician tracker
|   |   |   |-- institutional.js   13F institutional intelligence
|   |   |   |-- expert-analysis.js Expert sentiment + analyst timeline
|   |   |   |-- registry.js        50-state company registry + OSINT
|   |   |   |-- graph.js           Cytoscape network visualization
|   |   |   |-- economics.js       FRED + BEA macroeconomic data
|   |   |   |-- entities/[id].js   Entity profile (9 tabs)
|   |   |
|   |   |-- src/
|   |   |   |-- components/
|   |   |   |   |-- Layout.js      Sidebar nav + topbar (used on every single page)
|   |   |   |-- styles/
|   |   |   |   |-- globals.css    Design tokens: colors, fonts, .card .btn .badge classes
|   |   |-- lib/
|   |   |   |-- api.js             getApiBaseUrl() helper used by every page
|
|   |-- admin/                     React admin panel (port 3002)
|   |-- worker/                    Node.js background job runner
|
|-- packages/
|   |-- finance/                   Reusable Python financial calculations
|   |   |-- dcf.py                 DCF model
|   |   |-- technicals.py          Technical indicator math
|   |   |-- fundamentals.py        Ratio helpers
|   |   |-- comps.py               Comparable company analysis
|   |
|   |-- connectors/                U.S. public records connectors
|   |   |-- us/
|   |   |   |-- sec/edgar.py       SEC EDGAR filing fetcher
|   |   |   |-- fec/fec.py         FEC political donations
|   |   |   |-- fara/fara.py       FARA foreign agent registrations
|   |   |   |-- ofac/ofac.py       OFAC sanctions list
|   |   |   |-- lda/lda.py         Lobbying Disclosure Act
|   |   |   |-- usaspending/       Federal contracts
|   |   |   |-- courtlistener/     Federal court records
|   |   |   |-- state_registry/    51 U.S. state SOS connectors
|   |   |   |   |-- bulk/          NY, CO, FL, OR (bulk download ingestion)
|   |   |   |   |-- api/           WA, TX, CA (direct API ingestion)
|   |   |   |   |-- states/        44 remaining states (Playwright scrape)
|
|-- scripts/                       Utility scripts
|   |-- local-start.ps1            Start API + web locally (Windows PowerShell)
|   |-- local-stop.ps1             Stop local services
|   |-- docker-up.ps1              Start with Docker (PostgreSQL + Redis)
|   |-- seed-state-registry.sh     Seed all 51 state registries
|
|-- tests/                         Pytest integration tests (minimal coverage currently)
|-- docs/                          Architecture and planning documents
|-- ecosystem.config.js            PM2 process definitions for all 5 services
|-- Finance_Platform_Handoff.md    Master handoff document for new teammates
|-- README.md                      Project overview and quick start
|-- 5th_July.md                    Latest sprint log
|-- .env.example                   Template for all environment variables
`

---

## 8. All API Endpoints Reference

Full interactive Swagger documentation: **http://184.72.123.188:3001/docs**

### Stock and Market Data (`/market/yf/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /market/yf/snapshot?ticker= | Full price + fundamentals + holders snapshot |
| GET | /market/yf/history?ticker= | OHLCV price history (period + interval params) |
| GET | /market/yf/fundamentals?ticker= | 35+ financial ratios |
| GET | /market/yf/company?ticker= | Company profile (sector, industry, employees) |
| GET | /market/yf/dividends?ticker= | Dividend and split history |
| GET | /market/yf/options?ticker= | Options chain (nearest expiry) |
| GET | /market/yf/holders?ticker= | Top institutional holders |
| GET | /market/technicals?ticker= | 15 technical indicators + buy/sell signals |
| GET | /market/intelligence/report?ticker= | 4-agent AI consensus BUY/HOLD/SELL |

### RSS News (`/market/rss/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /market/rss/sources | List all 50 RSS sources with status |
| GET | /market/rss/articles | Filtered articles (category/region/entity params) |
| GET | /market/rss/entity-feed?entity= | Articles auto-tagged to a specific entity |
| GET | /market/rss/digest | Top articles per category for last N hours |
| POST | /market/rss/poll | Manually trigger an RSS poll |

### Crypto (`/market/crypto/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /market/crypto/dashboard | Global stats + top 14 coins + trending + whale alerts |
| GET | /market/crypto/coin/{id} | Full CoinGecko coin profile |
| GET | /market/crypto/trending | Trending coins (24h) |
| GET | /market/crypto/global | Global market stats + DeFi |
| GET | /market/crypto/wallet/eth/{addr} | ETH wallet: balance, tokens, transactions |
| GET | /market/crypto/wallet/btc/{addr} | BTC wallet: balance, tx history |
| GET | /market/crypto/whale-alerts | Large ETH transactions detected |

### Government Trading (`/market/gov/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /market/gov/ptr-filings | House STOCK Act PTR disclosures |
| GET | /market/gov/insider-trades?q= | SEC Form 4 corporate insider trades |
| GET | /market/gov/politician/{name} | Named politician profile + PTRs + legislation |
| GET | /market/gov/politicians | All 15 tracked politicians summary |
| GET | /market/gov/legislation/{name} | Politician sponsored legislation |

### Deep Company Analysis (`/market/company/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /market/company/deep-report?ticker= | Full parallel company analysis |
| GET | /market/company/sec-filings?ticker= | All SEC filings with viewer links |
| GET | /market/company/financials?ticker= | XBRL quarterly financials (8 quarters) |
| GET | /market/company/cap-table?ticker= | Institutional + mutual fund holders |
| GET | /market/company/insider-trades?t= | Recent Form 4 insider transactions |
| GET | /market/company/analyst-ratings/{t} | Analyst consensus + price targets |
| GET | /market/company/earnings?ticker= | EPS history + next earnings date |

### Valuation (`/market/valuation/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /market/valuation/dcf?ticker= | Full DCF intrinsic value model |
| GET | /market/valuation/filing?ticker= | 10-K/10-Q MD&A text analysis |
| GET | /market/valuation/full?ticker= | Combined DCF + filing report |

### Institutional and Expert (`/market/institutional/*` and `/market/expert/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /market/institutional/holders?t= | 13F institutional positions |
| GET | /market/institutional/13f-filers | Recent 13F filers from SEC EDGAR |
| GET | /market/institutional/lookup?inst= | Institution portfolio from 13F XML |
| GET | /market/expert/analysis?ticker= | News sentiment + key themes |
| GET | /market/expert/timeline?ticker= | Analyst upgrade/downgrade timeline |

### Intelligence (`/intelligence/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /intelligence/generate?entity_name=&entity_type=&ticker= | Generate 9-section report |
| GET | /intelligence/ | List all saved reports |
| GET | /intelligence/{id} | Get a specific saved report |
| GET | /intelligence/{id}/pdf | Download as PDF |
| GET | /intelligence/{id}/word | Download as Word (.docx) |
| GET | /intelligence/{id}/excel | Download as Excel (.xlsx) |
| GET | /intelligence/{id}/powerpoint | Download as PowerPoint (.pptx) |
| GET | /intelligence/apollo/org?name= | Apollo org enrichment |
| POST | /intelligence/apollo/enrich | Full Apollo enrichment |
| GET | /intelligence/apollo/people?name= | Apollo people search |
| GET | /intelligence/apollo/orgchart?domain= | C-suite + VP org chart |
| GET | /intelligence/private-co/search?q= | OpenCorporates + GLEIF + FinCEN |

### Auth and Core (`/auth/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Register new user (email + password) |
| POST | /auth/login | Login - returns JWT token |
| GET | /auth/me | Get current user (requires Bearer token) |
| GET | /health | API health check |
| POST | /bootstrap | Initialize all database tables |
| POST | /demo/seed | Seed sample entities, reports, and graph data |
| GET | /registry/search?q=&state= | Search U.S. 50-state company registry |
| GET | /entities/{id} | Entity profile with all related data |
| GET | /search?q= | Global search across entities and documents |
| GET | /graph/expand?entity_id= | Expand entity in relationship graph |
| POST | /chat/ask | RAG chat Q&A against a saved report |
| POST | /tracking/watchlist | Add entity to watchlist |
| GET | /tracking/watchlist | List all watchlisted entities |
| GET | /economics/bea | BEA economic data |

---

## 9. All Frontend Pages

| URL | Page Name | Status | Description |
|-----|-----------|--------|-------------|
| `/` | Dashboard | Live | Homepage: feature cards, live stats bar, quick search |
| `/intelligence` | Intelligence Report Generator | Live | Enter entity name, click Generate, see 9-section report |
| `/intelligence/[id]` | Saved Report Viewer | Live | Full report + PDF/Word/Excel/PPT export buttons |
| `/saved` | Saved Reports Library | Live | Browse all reports, search, export directly |
| `/stock` | Stock Analysis Terminal | Live | Price, 35 fundamentals, 15 technicals, 4-agent AI consensus |
| `/valuation` | DCF Valuation | Live | DCF model, Bear/Base/Bull scenarios, filing analysis |
| `/company` | Deep Company Analysis | Live | 5 tabs: Overview, Filings, Cap Table, Analyst, Earnings |
| `/expert-analysis` | Expert Sentiment | Live | News sentiment trend, key themes, analyst timeline |
| `/institutional` | Institutional Intelligence | Live | 13F holder analysis, mega positions, institution lookup |
| `/gov-trading` | Government Trading | Live | House PTR, Form 4 insiders, politician profile tracker |
| `/crypto` | Crypto Intelligence | Live | Market dashboard, coin detail, wallet lookup |
| `/economics` | Economics | Live | FRED GDP/CPI/rates + BEA regional data |
| `/search` | Global Search | Live | Search entities, documents, relationships |
| `/graph` | Relationship Graph | Live | Cytoscape network visualization, expand nodes |
| `/registry` | U.S. 50-State Registry | Live | Search company records across 51 state jurisdictions |
| `/timeline` | Entity Timeline | Live | Chronological event view for any entity |
| `/compare` | Multi-Entity Compare | Live | Up to 5 entities: radar chart, KPI table, overlap |
| `/tracking` | Watchlist | Live | Add entities, daily digest management |
| `/tracking/alerts` | Alert Inbox | Live | Alert feed with severity filter, acknowledge, snooze |
| `/skills` | AI Skills | Live | Run Anthropic/OpenAI skill workflows |
| `/entities/[id]` | Entity Profile | Live | 9-tab profile: Overview, Financial, People, Social, News, Intelligence, OSINT, Timeline |
| `/alerts` | Alert Events | Live | Alert event history |

### UI Design System

| Property | Value |
|----------|-------|
| Theme | Dark mode throughout |
| Brand color | Indigo `#6366f1` |
| CSS framework | Tailwind CSS v3 + custom classes |
| Custom classes | `.card`, `.btn`, `.badge`, `.inp`, `.tabs-bar` |
| Design tokens | `apps/web/src/styles/globals.css` |
| Layout component | `apps/web/src/components/Layout.js` (used on every page) |
| Charts | Recharts |
| Graph | Cytoscape.js |

---

## 10. What Is Done vs What Is Left

### Fully Live and Working

| Feature | Status |
|---------|--------|
| Intelligence report generation (9 sections + GPT-4o) | Done |
| PDF / Word / Excel / PowerPoint export | Done |
| Stock analysis (35 fundamentals + 15 technicals) | Done |
| 4-agent AI consensus (BUY/HOLD/SELL) | Done |
| DCF valuation with Bear/Base/Bull scenarios | Done |
| 10-K/10-Q MD&A text parsing and filing analysis | Done |
| Deep company analysis (SEC XBRL, cap table, analyst, earnings) | Done |
| Institutional 13F tracker with institution portfolio lookup | Done |
| Government trading (Congress PTR + Form 4 + politician profiles) | Done |
| Crypto dashboard + wallet lookup + whale alerts | Done |
| RSS news poller (50 feeds, 15-min cycle, 2000+ articles) | Done |
| Expert sentiment analysis + analyst upgrade timeline | Done |
| OSINT: 40-platform username enum, domain intel, Apollo org charts | Done |
| U.S. 50-state company registry (51 jurisdictions) | Done |
| Relationship graph (Cytoscape visualization) | Done |
| RAG chat Q&A against saved reports | Done |
| Entity tracking watchlist + daily digest | Done |
| Alert inbox | Done |
| JWT authentication + native bcrypt | Done |
| Full dark-theme UI on all pages | Done |
| Deployed live on AWS EC2 | Done |

### High Priority Backlog (James Explicit Requests)

| # | Feature | Why It Matters |
|---|---------|----------------|
| 1 | **LLM-powered 10-K/10-Q MD&A synthesis** | AI summarizing full filing text into investment thesis |
| 2 | **13F quarter-over-quarter position diff** | See what institutions bought/added/reduced/exited between quarters |
| 3 | **Big Trade detection + alerts** | When Form 4 insider trade exceeds threshold, fire email/SMS alert |
| 4 | **Congress.gov full legislation** | Needs paid API key - DEMO_KEY is rate-limited |
| 5 | **RSS Phase 2** | Event clustering, fact extraction, contradiction detection |
| 6 | **Crawl4AI integration** | Replace Apify long-term (James preference for open-source) |

### Medium Priority Backlog

| # | Feature | Notes |
|---|---------|-------|
| 7 | TradingAgents / FinRobot / ai-hedge-fund integration | Multi-agent debate frameworks |
| 8 | OpenBB / FinceptTerminal features | Bloomberg-style terminal UX |
| 9 | Prediction market data | jon-becker/prediction-market-analysis |
| 10 | Fraud / AML crypto tracking | Marble, antifraud repos |
| 11 | ALEPH/OCCRP leaked documents | Account approval still pending |
| 12 | CA SOS API | calicodev.sos.ca.gov approval pending |
| 13 | Google SSO | Routes wired, credentials pending from James |
| 14 | Multi-entity network graph reports | PayPal Mafia cross-entity linking |
| 15 | Ownership tree crawler | OpenOwnership / FinCEN BOI |

### Technical Debt

| # | Item |
|---|------|
| 16 | Automated test coverage is minimal - only health stubs and connector samples |
| 17 | OpenSearch integration is a stub - returns empty results |
| 18 | Admin UI is an ops shell - not full tenant administration |
| 19 | OFAC name matching can produce false positives - needs tuning |
| 20 | White flash on Next.js route change (minor UX bug) |

---

## 11. Project Timeline

| Date | Branch | What Was Built |
|------|--------|----------------|
| June 1-2, 2026 | productionization/codex-roadmap | Monorepo scaffolding, SQLite/Postgres fixes, major UI redesign, EC2 deployment fix (blank page bug), host-aware API URLs. Platform at ~35-45% of full spec. |
| June 4, 2026 | productionization/codex-roadmap | Phase 0-9 master roadmap written, secret hygiene plan, EC2 PM2 process stabilization |
| June 10-11, 2026 | -- | Phase 2: U.S. 50-State Registry live (51 jurisdictions, 4 ingestion tiers). BEA connector added. |
| June 15-18, 2026 | -- | Layer 1 intelligence reports live (9 sections). SEC/FEC/FARA/OFAC connectors productionized. PayPal Mafia seed data. Lobbying client_name bug fixed (504 filings found vs 10 before). E2E verified. |
| June 22-25, 2026 | -- | v2.0 features: Apollo.io enrichment, Apify social scraping, RAG chat, entity tracking, compare page, timeline page, PDF/Word/Excel/PPT exports. 8/9 API keys live. |
| July 5, 2026 | 5th-July-sprint | Major sprint: RSS Phase 1 (50 feeds, PM2 worker, 882 articles first poll), yfinance connector, 15 pure-Python technical indicators, 4-agent AI engine, OSINT connector (40 platforms) |
| July 5-6, 2026 | 5th-July-sprint | Crypto intelligence, government trading tracker, deep company analysis, DCF valuation engine, expert sentiment tracker, institutional 13F tracker, politician profile tracker |
| July 8, 2026 | 8th-july-sprint | Full UI/UX overhaul: dark sidebar, Tailwind design system, indigo brand, all pages redesigned |
| July 13, 2026 | 8th-july-sprint | Handoff document written. Platform fully live, 60+ endpoints, 22+ pages, ready for new developer. |

---

## 12. Known Bugs and Gotchas

Every new developer must know these before touching the code.

| # | Bug / Gotcha | What Happens | The Fix |
|---|-------------|-------------|---------|
| 1 | **Technical indicators return arrays** | RSI, MACD, BB, SMA all return full historical arrays, not a single value | Frontend must call `.slice(-1)[0]` to get the latest value. Already fixed in `stock.js` |
| 2 | **CoinGecko rate limiting** | If `top_coins` is empty, CoinGecko rate limit was hit and cache expired | Dashboard has 300s TTL cache. Wait and retry. Never add more calls. |
| 3 | **passlib vs native bcrypt crash** | Using passlib for password hashing causes a version conflict crash at API startup | NEVER use `passlib.hash.bcrypt`. Always use native `bcrypt` library in `apps/api/app/auth/security.py` |
| 4 | **Apollo name obfuscation** | Apollo paid plan returns `last_name_obfuscated` - full last names are hidden | Connector in `apollo_connector.py` already handles this. Do not expect full last names. |
| 5 | **No /api prefix in URLs** | Frontend API calls must go to `/market/...` NOT `/api/market/...` | Always use `API_URL + /market/...`. There is no /api prefix anywhere in this codebase. |
| 6 | **yfinance returns NaN** | Yahoo Finance returns NaN for some financial fields, breaking JSON serialization | Always sanitize with `_safe_num()` helper before returning any JSON response |
| 7 | **House stock-watcher S3 Access Denied** | The popular GitHub project house-stock-watcher S3 bucket returns 403 | Use the official House Clerk FD.ZIP file directly. Already implemented in `gov_trading_connector.py` |
| 8 | **Next.js 12 Link syntax** | This project uses Next.js 12, NOT 13+ | Always use `<Link href=/page><a>text</a></Link>` - the old pattern with nested `<a>` tag required |
| 9 | **CoinGecko uses slugs not tickers** | CoinGecko uses slug IDs like `bitcoin`, `ethereum`, not symbols like BTC, ETH | Always pass the CoinGecko ID string, not the exchange ticker symbol |
| 10 | **SQLite vs PostgreSQL syntax** | PostgreSQL supports `WHERE id = ANY(:arr)` but SQLite does not | Use `WHERE id IN :arr` syntax for queries that must run on both databases locally and in production |

---

## 13. How to Run Locally

**Prerequisites:** Python 3.11+, Node.js 18+, Git. No PostgreSQL or Redis needed locally (SQLite by default).

`powershell
# 1. Clone and checkout active branch
git clone https://github.com/1Touch-dev/Finance-Advanced-Research-Platform
cd Finance-Advanced-Research-Platform
git checkout 8th-july-sprint

# 2. Start backend
cd apps/api
pip install -e .
pip install -e ../../packages/finance
python -m uvicorn app.main:app --host 127.0.0.1 --port 3001 --reload

# 3. Start frontend (new terminal)
cd apps/web
npm install
npm run dev

# 4. Bootstrap database (first run only)
curl.exe -X POST http://127.0.0.1:3001/bootstrap
`

**Service URLs:**

| Service | Local | Production |
|---------|-------|------------|
| Web UI | http://localhost:3000 | http://184.72.123.188:3003 |
| API + Docs | http://localhost:3001/docs | http://184.72.123.188:3001/docs |
| Admin | http://localhost:3002 | http://184.72.123.188:3002 |

**Shortcut scripts:**

`powershell
.\scripts\local-start.ps1    # Start API and web together
.\scripts\local-stop.ps1     # Stop all local services
.\scripts\docker-up.ps1      # Start with Docker
`

**EC2 server management:**

`ash
ssh ubuntu@184.72.123.188
pm2 list                         # See all 5 services
pm2 restart finance-api          # After backend changes
pm2 restart finance-web          # After frontend changes
pm2 logs finance-api --lines 50  # Debug errors
pm2 restart all                  # Restart everything
`

**Always work on `8th-july-sprint` branch -- never push directly to main.**

---

## 14. Environment Variables

All secrets live in `.env` at the repo root. Copy `.env.example` to `.env` and fill in your keys.

### Core (Always Required)

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | `sqlite:///./local.db` for local, Postgres URL for production |
| `JWT_SECRET` | Secret key for signing JWT tokens -- use a long random string |
| `NEXT_PUBLIC_API_URL` | Frontend to API base URL. Local: http://localhost:3001 |

### AI / LLM Keys

| Variable | Service |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI GPT-4o -- intelligence narratives, multi-agent synthesis |
| `ANTHROPIC_API_KEY` | Anthropic Claude -- skills gateway |

### Market Data Keys

| Variable | Service |
|----------|---------|
| `FINNHUB_API_KEY` | Finnhub real-time market data |
| `FMP_API_KEY` | Financial Modeling Prep -- statements, Beneish/Altman scores |
| `ALPHA_VANTAGE_KEY` | Alpha Vantage additional market data |
| `FRED_API_KEY` | FRED -- macroeconomic data and risk-free rate |
| `BEA_API_USER_ID` | BEA -- GDP and regional income |
| `ETHERSCAN_API_KEY` | Etherscan -- ETH wallet lookups |

### News and OSINT Keys

| Variable | Service |
|----------|---------|
| `NEWSAPI_KEY` | NewsAPI news aggregation |
| `GUARDIAN_API_KEY` | The Guardian UK news |
| `NYT_API_KEY` | New York Times article search |
| `APOLLO_API_KEY` | Apollo.io org and people enrichment (paid plan) |
| `APIFY_API_TOKEN` | Apify social scraping and Google News |

### Government Data Keys

| Variable | Service |
|----------|---------|
| `FEC_API_KEY` | FEC OpenData political contributions |
| `COURTLISTENER_API_TOKEN` | CourtListener federal courts |
| `CONGRESS_API_KEY` | Congress.gov legislation (currently DEMO_KEY -- limited) |
| `UK_COMPANIES_HOUSE_KEY` | UK Companies House |
| `SEC_USER_AGENT` | Required by SEC EDGAR -- format: YourName email@domain.com |

### Notification Keys

| Variable | Service |
|----------|---------|
| `SENDGRID_API_KEY` | SendGrid email alerts |
| `TWILIO_ACCOUNT_SID` | Twilio SMS alerts |
| `TWILIO_AUTH_TOKEN` | Twilio auth |
| `TWILIO_FROM_NUMBER` | Twilio sender number |

### Update a Key on the Live Server

`ash
nano /home/ubuntu/Finance-Advanced-Research-Platform/.env
# Edit the value, save, exit
pm2 restart finance-api
`

---

## 15. Key People and Contacts

| Role | Name | Contact |
|------|------|---------|
| Product Owner / Client | James | Thunder Marketing |
| Lead Developer | Abhishek Kulkarni | abhishekk@kyma.world |
| API registration credential | -- | abhishekk@kyma.world / Kulkarni@2002 |

### Staging Environment Access

| Resource | URL |
|----------|-----|
| Platform | http://184.72.123.188:3003 |
| API Docs | http://184.72.123.188:3001/docs |
| Admin Panel | http://184.72.123.188:3002 |
| GitHub Repo | https://github.com/1Touch-dev/Finance-Advanced-Research-Platform |
| Active Branch | `8th-july-sprint` |

---

## Quick Reference -- End to End Data Flow

`
User Input: Palantir Technologies
       |
       v
Next.js Frontend (port 3003)
POST /intelligence/generate?entity_name=Palantir+Technologies
       |
       v
FastAPI Backend (port 3001)
intelligence_service.py -- fans out to 11 parallel threads
       |
       +-- Wikipedia REST            --> entity background
       +-- SEC EDGAR (CIK)           --> company registration
       +-- SEC EDGAR (13G/13D)       --> institutional investors
       +-- USASpending.gov           --> contracts (.72B found)
       +-- LDA.gov                  --> lobbying (504 filings found)
       +-- FEC OpenData             --> political donations
       +-- DOJ FARA                 --> foreign agent registrations
       +-- OFAC / OpenSanctions     --> sanctions check
       +-- CourtListener            --> court records
       +-- Apollo.io (paid)         --> org chart + key people
       +-- Apify                    --> Google News + LinkedIn
       +-- OpenAI GPT-4o            --> deep narrative essay
       |
       v
Aggregate into 9 sections with DOCUMENTED/REPORTED/ANALYTICAL tags
Save to PostgreSQL
Return full JSON to frontend
       |
       v
Frontend renders:
- 9-section cited intelligence report
- Embedded Cytoscape relationship graph
- Export buttons: PDF, Word, Excel, PowerPoint
- Floating RAG chat panel
`

---

*Document generated: July 20, 2026*
*Based on: Finance_Platform_Handoff.md + Full Codebase Analysis*
*Active Branch: `8th-july-sprint`*
