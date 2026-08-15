# Finance Platform Handoff Document

**Date:** 13 July 2026  
**Prepared by:** Abhishek Kulkarni  
**For:** New teammate / project continuation  
**Active Branch:** `8th-july-sprint`  
**GitHub:** https://github.com/1Touch-dev/Finance-Advanced-Research-Platform  
**Live Platform:** http://184.72.123.188:3003  
**Live API:** http://184.72.123.188:3001  
**API Docs:** http://184.72.123.188:3001/docs

---

## 1. What This Platform Is

The **Enterprise Intelligence & Investment Research Platform** is a full-stack financial intelligence system that combines:

- **Public-record OSINT** — SEC, FEC, FARA, lobbying, court records, sanctions, procurement
- **Financial markets** — Stock analysis, DCF valuation, technical indicators, earnings, cap tables
- **Institutional intelligence** — 13F filings, hedge fund flows, insider trading (Form 4)
- **Government trading** — STOCK Act PTR disclosures, politician portfolio tracking
- **Crypto intelligence** — CoinGecko market data, wallet lookup, whale alerts
- **News intelligence** — 50+ RSS feeds, entity-tagged articles, sentiment analysis
- **Multi-agent AI** — 4-agent investment consensus (Fundamentals + Technical + Sentiment + Risk)
- **OSINT enrichment** — Apollo.io org charts, social profiles, entity resolution

It is **not** a stock screener or a generic LLM tool. It is a research-grade intelligence workbench designed for deep investigation of companies, people, and networks.

**Primary contact:** James Thunder Marketing  
**Developer email:** abhishekk@kyma.world  
**Registration credential (for APIs):** abhishekk@kyma.world / Kulkarni@2002

---

## 2. System Architecture

```
Finance-Advanced-Research-Platform/
├── apps/
│   ├── api/          — FastAPI backend (Python 3.11), port 3001
│   │   └── app/
│   │       ├── api/          — Route handlers (20 files)
│   │       ├── connectors/   — External data connectors (17 files)
│   │       ├── services/     — Business logic (intelligence_service.py etc.)
│   │       ├── auth/         — JWT + bcrypt authentication
│   │       └── models.py     — SQLAlchemy ORM models
│   ├── web/          — Next.js 12 frontend (React 17), port 3003
│   │   ├── pages/    — 25+ page components
│   │   ├── src/
│   │   │   ├── components/Layout.js  — Sidebar nav + topbar
│   │   │   └── styles/globals.css    — Design system tokens
│   │   └── lib/api.js — API base URL helper
│   ├── admin/        — React admin dashboard, port 3002
│   └── worker/       — Node.js background jobs (Bull/Redis)
├── packages/
│   ├── finance/      — DCF, comps, technicals, market helpers
│   └── connectors/   — U.S. public-data connectors (17 federal + 51 state)
├── scripts/          — Start/stop/seed scripts
├── docs/             — Architecture docs, gap analysis
├── .env              — All secrets and API keys (see Section 5)
└── ecosystem.config.js — PM2 process definitions
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI + SQLAlchemy + PostgreSQL |
| Frontend | Next.js 12, React 17, Tailwind CSS v3 |
| Process Manager | PM2 (manages all 5 services) |
| Database | PostgreSQL (primary) + SQLite (local dev fallback) |
| Background Jobs | Node.js + Bull + Redis |
| AI / LLM | OpenAI GPT-4o (intelligence narratives), Anthropic Claude (skills) |
| Charts | Recharts (frontend) |
| Auth | JWT + native bcrypt |

---

## 3. Live Services (EC2: 184.72.123.188)

| PM2 Name | Port | Status | Description |
|----------|------|--------|-------------|
| `finance-api` | 3001 | Online | FastAPI Python backend |
| `finance-web` | 3003 | Online | Next.js frontend |
| `finance-admin` | 3002 | Online | React admin panel |
| `rss-poller` | — | Online | RSS feed ingestion (15-min cycle) |
| `daily-digest` | — | Stopped | Daily digest cron (6AM UTC) |

**Restart all:** `pm2 restart all`  
**Check logs:** `pm2 logs finance-api --lines 50`  
**Restart single:** `pm2 restart finance-web`

---

## 4. All Features Currently in the System

### 4.1 Intelligence Reports (Layer 1)

- **Entity dossier generator** — Enter any company/person name → 9-section cited intelligence report
- **Sections:** Entity Profile, Investors & Capital Structure, Government Contracts, Lobbying Activity, Political & Foreign Exposure, Sanctions, Litigation, Deep AI Narrative (GPT-4o)
- **Data sources per report:** Wikipedia, SEC EDGAR (CIK, 13G/13D, Form D), FEC, FARA, USASpending, LDA lobbying, OFAC sanctions, CourtListener, FundedAPI
- **Every claim tagged:** DOCUMENTED / REPORTED / ANALYTICAL
- **Export formats:** PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx)
- **Saved reports:** Stored in PostgreSQL, accessible at `/saved`
- **RAG Chat:** Per-report cited Q&A via `/chat/ask`
- **Demo seeds:** PayPal Mafia (Peter Thiel, Elon Musk, Reid Hoffman) + Thiel/Defense (Palantir, Anduril, Founders Fund)

**Key files:**
- `apps/api/app/api/intelligence.py` — API routes
- `apps/api/app/services/intelligence_service.py` — Orchestrator
- `apps/web/pages/intelligence.js` — Frontend

### 4.2 Stock Analysis (`/stock`)

- **Price + fundamentals** — currentPrice, P/E, forward P/E, EPS, beta, margins, ROE, debt/equity, revenue
- **15 technical indicators** — RSI, MACD, Bollinger Bands, SMA(10/20/50/200), EMA(12/26), ATR, OBV, Stochastic, Williams %R, ROC
- **4-agent AI consensus** — Fundamentals Agent + Technical Agent + Sentiment Agent + Risk Agent → BUY/HOLD/SELL with confidence score
- **Analyst consensus** — Rating bar (Strong Buy → Strong Sell), price targets, recent rating changes
- Quick ticker buttons: AAPL, MSFT, TSLA, NVDA, AMZN, GOOGL, META, BRK-B

**Key files:**
- `apps/api/app/connectors/yfinance_connector.py`
- `apps/api/app/connectors/technicals_connector.py`
- `apps/api/app/connectors/multi_agent_intelligence.py`
- `apps/web/pages/stock.js`

### 4.3 DCF Valuation (`/valuation`)

- **DCF model** — Intrinsic value per share, enterprise value, equity value, net debt
- **Inputs:** WACC, cost of equity, 5-year FCF growth, terminal growth rate, beta, risk-free rate (from FRED)
- **3 scenarios:** Bear / Base / Bull with per-scenario intrinsic values
- **Assessment:** Significantly Undervalued → Significantly Overvalued
- **Filing analysis** — Parses 10-K/10-Q MD&A text for guidance, key metrics, risks

**Key files:**
- `apps/api/app/connectors/valuation_connector.py`
- `apps/web/pages/valuation.js`

### 4.4 Deep Company Analysis (`/company`)

- **SEC EDGAR** — Company info, all filings list, XBRL financial statements (10-K/10-Q)
- **Cap table** — Top 10 institutional + mutual fund holders with % held
- **Insider trades** — Recent Form 4 transactions with dollar values
- **Analyst ratings** — Current recommendation + price targets
- **Earnings history** — Quarterly EPS actual vs. estimate + surprise %

**Key files:**
- `apps/api/app/connectors/company_deep_connector.py`
- `apps/web/pages/company.js`

### 4.5 Expert Analysis (`/expert-analysis`)

- **News sentiment** — Aggregated from NewsAPI + RSS feeds
- **Sentiment trend over time** — Daily bullish/bearish/neutral score chart
- **Key themes extraction** — Most common topics across recent articles
- **Analyst timeline** — Historical upgrades/downgrades with firm names and dates
- **Articles list** — Full article feed with sentiment scores

**Key files:**
- `apps/api/app/connectors/expert_analysis_connector.py`
- `apps/web/pages/expert-analysis.js`

### 4.6 Institutional Intelligence (`/institutional`)

- **Institutional holders** — Top holders with shares, % held, value
- **Mutual fund holders** — Fund-level breakdown
- **Mega positions** — Largest single positions across all institutions
- **13F Filers** — Recent 13F-HR filers from SEC EDGAR EFTS
- **Institution lookup** — Search a specific institution's portfolio from 13F XML

**Key files:**
- `apps/api/app/connectors/institutional_tracker.py`
- `apps/web/pages/institutional.js`

### 4.7 Government Trading (`/gov-trading`)

- **House PTR disclosures** — Parses annual House Clerk FD.ZIP for STOCK Act filings
- **Corporate insider trades** — SEC Form 4 via EDGAR EFTS
- **Politician tracker** — Named politicians (Pelosi, McConnell, MTG, etc.) with their PTR filings + sponsored legislation
- **Congress.gov integration** — Legislation data (now live on registered free key, F-05)

**Key files:**
- `apps/api/app/connectors/gov_trading_connector.py`
- `apps/web/pages/gov-trading.js`

### 4.8 Crypto Intelligence (`/crypto`)

- **Market dashboard** — CoinGecko global market stats + top 14 coins by market cap
- **Trending coins** — CoinGecko trending list
- **Whale alerts** — Large transactions (>$500M) via Etherscan
- **Coin detail** — Full coin profile from CoinGecko
- **Wallet lookup** — ETH wallet (Etherscan) + BTC wallet (Blockchain.info)
- **5-minute TTL cache** — Prevents CoinGecko rate limiting

**Key files:**
- `apps/api/app/connectors/crypto_connector.py`
- `apps/web/pages/crypto.js`

### 4.9 RSS News Intelligence

- **50 curated feeds** — Bloomberg, Reuters, FT, WSJ, CNBC, CoinDesk, Politico, etc.
- **Postgres tables:** `rss_sources` + `rss_articles`
- **Entity auto-tagging** — 15 entities tracked (Apple, Tesla, Fed Reserve, Bitcoin, etc.)
- **PM2 poller** — 15-minute ingestion cycle
- **Entity news feed** — Filter articles by entity on entity profile pages
- **Stats:** 2,000+ articles ingested so far

**Key files:**
- `apps/api/app/connectors/rss_worker.py`
- `ecosystem.config.js` (rss-poller process)

### 4.10 OSINT / Entity Registry (`/registry`)

- **Apollo.io** — Org enrichment (paid plan), people search, org chart (C-suite + VPs)
- **Username enumeration** — 40+ platforms via Sherlock-style checker
- **Domain intelligence** — WHOIS, DNS, subdomains, tech stack
- **LinkedIn signals** — Profile enrichment
- **OpenCorporates** — Global company registry
- **GLEIF** — LEI (Legal Entity Identifier) lookup
- **FinCEN** — Beneficial ownership data
- **ICIJ Offshore Leaks** — Panama/Paradise/Pandora Papers search
- **U.S. 50-State Registry** — 51 jurisdictions, normalized company records

**Key files:**
- `apps/api/app/connectors/apollo_connector.py`
- `apps/api/app/connectors/osint_connector.py`
- `apps/api/app/connectors/private_company_connector.py`

### 4.11 Economics (`/economics`)

- **FRED API** — GDP (NIPA), CPI, interest rates, unemployment
- **BEA API** — Regional personal income, industry GDP

### 4.12 Search, Graph, Tracking, Alerts

- **Global search** (`/search`) — Entities, documents, relationships
- **Relationship graph** (`/graph`) — Cytoscape network visualization, expand/pathfind
- **Tracking** (`/tracking`) — Watchlist, daily digest worker
- **Alerts** (`/tracking/alerts`) — Alert inbox, severity filter, acknowledge/snooze
- **Timeline** (`/timeline`) — Chronological event timeline per entity
- **Compare** (`/compare`) — Up to 5 entities, radar chart, KPI table

### 4.13 Authentication

- **JWT auth** with 24-hour tokens
- **Password hashing** — native bcrypt (NOT passlib — bcrypt version incompatibility fixed)
- **Register:** `POST /auth/register`
- **Login:** `POST /auth/login`

**Current login credentials (staging):**
- URL: http://184.72.123.188:3003
- Email: `abhishekk@kyma.world` / Password: `Kulkarni@2002` (or any account you register)


---

## 5. API Keys & Environment Variables

All keys are stored in `/home/ubuntu/Finance-Advanced-Research-Platform/.env`

### Currently Active / Live Keys

| Key Name | Service | Status | Notes |
|----------|---------|--------|-------|
| `OPENAI_API_KEY` | OpenAI GPT-4o | ✅ Live | Intelligence report narratives |
| `ANTHROPIC_API_KEY` | Anthropic Claude | ✅ Live | Skills gateway |
| `APOLLO_API_KEY` | Apollo.io | ✅ Live (Paid) | Org enrichment, people search |
| `APIFY_API_TOKEN` | Apify | ✅ Live | Social scraping, Google News, LinkedIn |
| `NEWSAPI_KEY` | NewsAPI | ✅ Live | News aggregation |
| `GUARDIAN_API_KEY` | The Guardian | ✅ Live | UK/international news |
| `NYT_API_KEY` | New York Times | ✅ Live | Article search |
| `FINNHUB_API_KEY` | Finnhub | ✅ Live | Market data |
| `FMP_API_KEY` | Financial Modeling Prep | ✅ Live | Financial statements |
| `ALPHA_VANTAGE_KEY` | Alpha Vantage | ✅ Live | Additional market data |
| `FRED_API_KEY` | St. Louis FRED | ✅ Live | Macroeconomic data, risk-free rate |
| `BEA_API_USER_ID` | BEA | ✅ Live | GDP, regional data |
| `ETHERSCAN_API_KEY` | Etherscan | ✅ Live | ETH wallet lookup |
| `UK_COMPANIES_HOUSE_KEY` | UK Companies House | ✅ Live | UK company search |
| `FEC_API_KEY` | FEC OpenData | ✅ Live | Political contributions |
| `COURTLISTENER_API_TOKEN` | CourtListener | ✅ Live | Litigation data |
| `CONGRESS_API_KEY` | Congress.gov | ✅ Live | 1,000 req/hr — **completely free API, no paid tier exists** (fixed F-05, was incorrectly hardcoded to DEMO_KEY) |
| `SENDGRID_API_KEY` | SendGrid | ✅ Configured | Email alerts |
| `TWILIO_*` | Twilio | ✅ Configured | SMS alerts |
| `GITHUB_TOKEN` | GitHub | ✅ Live | Code push/pull |

### Pending / Partial Keys

| Key Name | Service | Status | Action Needed |
|----------|---------|--------|--------------|
| `CA_SOS_API_KEY` | CA Secretary of State | ⏸ Pending | Approval at calicodev.sos.ca.gov |
| `ALEPH_API_KEY` | ALEPH/OCCRP | ⏸ Pending | Account approval required |
| `COBALT_API_KEY` | Cobalt SOS | ⏸ Deferred | Trial rate-limited; defer for now |
| `OIDC_CLIENT_ID/SECRET` | Google Workspace SSO | ⏸ Pending | Credentials from client (James) |

### How to Update a Key

```bash
nano /home/ubuntu/Finance-Advanced-Research-Platform/.env
# Edit the value
pm2 restart finance-api
```

---

## 6. All API Endpoints (Reference)

The full interactive API documentation is at: **http://184.72.123.188:3001/docs**

### Market & Finance Routes (`/market/*`)

```
GET  /market/yf/snapshot?ticker=         — Full snapshot (price + fundamentals)
GET  /market/yf/history?ticker=          — OHLCV price history
GET  /market/yf/fundamentals?ticker=     — 35+ financial ratios
GET  /market/yf/company?ticker=          — Company profile
GET  /market/yf/dividends?ticker=        — Dividend & split history
GET  /market/yf/options?ticker=          — Options chain
GET  /market/yf/holders?ticker=          — Top institutional holders
GET  /market/technicals?ticker=          — 15 technical indicators + signals
GET  /market/intelligence/report?ticker= — 4-agent AI consensus report
GET  /market/rss/sources                 — List all 50 RSS sources
GET  /market/rss/articles                — Filtered RSS articles
GET  /market/rss/entity-feed?entity=     — Articles for a specific entity
GET  /market/rss/digest                  — Top articles digest
POST /market/rss/poll                    — Trigger manual RSS poll

GET  /market/crypto/dashboard            — Global + top coins + trending + whales
GET  /market/crypto/coin/{id}            — Full CoinGecko coin profile
GET  /market/crypto/trending             — Trending coins
GET  /market/crypto/global               — Global market stats
GET  /market/crypto/wallet/eth/{addr}    — ETH wallet profile (Etherscan)
GET  /market/crypto/wallet/btc/{addr}    — BTC wallet profile (Blockchain.info)
GET  /market/crypto/whale-alerts         — Whale transactions
GET  /market/crypto/news                 — Crypto news

GET  /market/gov/ptr-filings             — House PTR disclosures
GET  /market/gov/insider-trades?q=       — SEC Form 4 insider trades
GET  /market/gov/politician/{name}       — Named politician profile + PTRs
GET  /market/gov/politicians             — All tracked politicians summary
GET  /market/gov/legislation/{name}      — Politician's sponsored legislation

GET  /market/company/deep-report?ticker= — Full company analysis
GET  /market/company/sec-filings?ticker= — SEC EDGAR filings list
GET  /market/company/financials?ticker=  — XBRL financial statements
GET  /market/company/cap-table?ticker=   — Institutional + mutual fund holders
GET  /market/company/insider-trades?t=   — Insider transactions
GET  /market/company/analyst-ratings/{t} — Analyst consensus + price targets
GET  /market/company/earnings?ticker=    — Earnings history

GET  /market/valuation/dcf?ticker=       — DCF intrinsic value model
GET  /market/valuation/filing?ticker=    — 10-K/10-Q text analysis
GET  /market/valuation/full?ticker=      — Combined DCF + filing report

GET  /market/expert/analysis?ticker=     — News sentiment + themes
GET  /market/expert/timeline?ticker=     — Analyst upgrade/downgrade timeline

GET  /market/institutional/holders?t=    — 13F institutional positions
GET  /market/institutional/13f-filers    — Recent 13F filers (SEC EDGAR)
GET  /market/institutional/lookup?inst=  — Institution portfolio lookup
```

### Intelligence Routes (`/intelligence/*`)

```
POST /intelligence/generate?entity_name=&entity_type=&ticker=  — Generate report
GET  /intelligence/                           — List all saved reports
GET  /intelligence/{id}                       — Get specific report
GET  /intelligence/{id}/pdf                   — Download PDF
GET  /intelligence/{id}/word                  — Download Word (.docx)
GET  /intelligence/{id}/excel                 — Download Excel (.xlsx)
GET  /intelligence/{id}/powerpoint            — Download PowerPoint (.pptx)
GET  /intelligence/apollo/org?name=           — Apollo org enrichment
POST /intelligence/apollo/enrich              — Full Apollo enrichment
GET  /intelligence/apollo/people?name=        — Apollo people search
GET  /intelligence/apollo/orgchart?domain=    — C-suite org chart
GET  /intelligence/apollo/health              — Apollo API key validation
GET  /intelligence/private-co/search?q=       — OpenCorporates + GLEIF + FinCEN
POST /intelligence/browser-research           — Browser research agent
```

### Auth Routes (`/auth/*`)

```
POST /auth/register    — Register new user
POST /auth/login       — Login → returns JWT token
GET  /auth/me          — Get current user (requires Bearer token)
```

### Other Routes

```
GET  /health                     — API health check
POST /bootstrap                  — Initialize DB tables
GET  /registry/search?q=&state=  — U.S. 50-state company registry
GET  /registry/health            — Registry source health
GET  /entities/{id}              — Entity profile
GET  /search?q=                  — Global search
GET  /graph/expand?entity_id=    — Graph expansion
GET  /economics/bea              — BEA economic data
POST /chat/ask                   — RAG chat Q&A
POST /tracking/watchlist         — Add entity to watchlist
GET  /tracking/watchlist         — List watchlist
```


---

## 7. Frontend Pages Map

| URL | Page | Status |
|-----|------|--------|
| `/` | Dashboard home — feature cards, stats bar, quick search | ✅ Redesigned 8 Jul |
| `/intelligence` | Report generator — PayPal Mafia / Thiel seeds | ✅ Live |
| `/intelligence/[id]` | Saved report viewer with all export buttons | ✅ Live |
| `/saved` | Saved reports library | ✅ Redesigned 8 Jul |
| `/search` | Global search | ✅ Redesigned 8 Jul |
| `/stock` | Stock analysis terminal | ✅ Redesigned 8 Jul |
| `/valuation` | DCF valuation + filing analysis | ✅ Live |
| `/company` | Deep company analysis (5 tabs) | ✅ Live |
| `/expert-analysis` | Expert sentiment + analyst timeline | ✅ Live |
| `/institutional` | 13F institutional intelligence | ✅ Live |
| `/gov-trading` | Gov PTR + Politician tracker | ✅ Live |
| `/crypto` | Crypto market / coin / wallet | ✅ Redesigned 8 Jul |
| `/economics` | FRED + BEA macro data | ✅ Live |
| `/timeline` | Entity event timeline | ✅ Live |
| `/compare` | Multi-entity comparison | ✅ Live |
| `/tracking` | Watchlist + digest | ✅ Live |
| `/tracking/alerts` | Alert inbox | ✅ Live |
| `/graph` | Relationship graph (Cytoscape) | ✅ Live |
| `/registry` | U.S. 50-state registry + OSINT | ✅ Live |
| `/skills` | AI skills runner | ✅ Live |
| `/entities/[id]` | Entity profile (9 tabs) | ✅ Live |
| `/alerts` | Alert events | ✅ Live |

**UI Design System (8th July sprint):**
- Dark theme with indigo brand (`#6366f1`)
- Collapsible left sidebar with grouped nav
- Design tokens in `apps/web/src/styles/globals.css`
- Tailwind CSS v3 installed; utility classes + custom CSS classes (`.card`, `.btn`, `.badge`, `.inp`, `.tabs-bar`)
- Layout: `apps/web/src/components/Layout.js`

---

## 8. Connectors Reference

| File | Purpose |
|------|---------|
| `yfinance_connector.py` | Price, fundamentals, holders, options |
| `technicals_connector.py` | 15 pure-Python technical indicators |
| `multi_agent_intelligence.py` | 4-agent BUY/HOLD/SELL consensus |
| `valuation_connector.py` | DCF model + 10-K/10-Q MD&A parsing |
| `company_deep_connector.py` | SEC EDGAR XBRL, cap table, earnings |
| `expert_analysis_connector.py` | News sentiment + analyst timeline |
| `institutional_tracker.py` | 13F filings + institutional holders |
| `gov_trading_connector.py` | House PTR + Form 4 + politician tracker |
| `crypto_connector.py` | CoinGecko + Etherscan + Blockchain.info |
| `rss_worker.py` | 50-feed RSS poller |
| `apollo_connector.py` | Apollo.io org/people (paid plan) |
| `osint_connector.py` | Username enum, domain intel |
| `private_company_connector.py` | OpenCorporates, GLEIF, FinCEN |
| `financial_news_connector.py` | NewsAPI, Guardian, NYT, GDELT |
| `apify_connector.py` | Social scrape + Google News |
| `browser_research_agent.py` | Browser research agent |

---

## 9. How to Run / Develop

### Staging (already running on EC2)

```bash
cd /home/ubuntu/Finance-Advanced-Research-Platform
pm2 list                          # check all services
pm2 restart finance-api           # after backend changes
pm2 restart finance-web           # after frontend changes
pm2 logs finance-api --lines 50   # debug API errors
```

### Local Development

```bash
# Backend
cd apps/api
pip install -e .
pip install -e ../../packages/finance
export DATABASE_URL="sqlite:///./local.db"
# Load .env from repo root
python -m uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload

# Frontend
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:3001 npm run start
# Opens on :3000 (or :3003 if configured in PM2)

# Bootstrap DB
curl -X POST http://localhost:3001/bootstrap
```

### Git Workflow

```bash
git checkout 8th-july-sprint      # ALWAYS work on this branch
git pull origin 8th-july-sprint
# ... make changes ...
git add -A
git commit -m "feat: description"
git push origin 8th-july-sprint
```

**Do NOT push to `main` directly.** Create PRs from feature/sprint branches.

---

## 10. What Still Needs to Be Built (Backlog)

### High Priority (James Explicit Requests)

| # | Feature | Notes |
|---|---------|-------|
| 1 | **LLM-powered 10-K/10-Q MD&A synthesis** | Phase 3 — needs OpenAI/Claude to summarize filings into investment thesis |
| 2 | **13F quarter-over-quarter position diff** | Compare two consecutive 13F filings → new/added/reduced/exited |
| 3 | **Big Trade detection + alerts** | Form 4 trades > $X threshold → email/SMS alert |
| 4 | **Congress.gov full legislation** | ✅ Done (F-05) — real key wired in, 8 new endpoints (search, bill detail/text/cosponsors, laws, committee, CRS reports, member votes) |
| 5 | **Deeper RSS Phase 2** | Event clustering, fact extraction, contradiction detection, perspective labeling (James's 500-source vision) |
| 6 | **Crawl4AI integration** | Replace Apify for long-term scraping (James preference) |

### Medium Priority

| # | Feature | Notes |
|---|---------|-------|
| 7 | Open-source TradingAgents / FinRobot / ai-hedge-fund deeper integration | Multi-agent frameworks James sent |
| 8 | OpenBB / FinceptTerminal market terminal features | Bloomberg-style terminal UX |
| 9 | Prediction market data | Jon-Becker/prediction-market-analysis |
| 10 | Fraud / AML crypto tracking enhancements | Marble, antifraud repos |
| 11 | ALEPH/OCCRP leaked docs (pending key) | Account approval still pending |
| 12 | CA SOS API (pending approval) | calicodev.sos.ca.gov |
| 13 | Google SSO (OIDC credentials from James) | Routes wired, credentials pending |
| 14 | Multi-entity network graph reports | PayPal Mafia cross-entity linking |
| 15 | Ownership tree crawler | OpenOwnership / FinCEN BOI |

### Lower Priority / Tech Debt

| # | Item |
|---|------|
| 16 | Automated test coverage (currently minimal) |
| 17 | OpenSearch full integration (currently stub) |
| 18 | Admin UI expansion (currently ops shell only) |
| 19 | OFAC name matching false-positive tuning |
| 20 | White flash on Next.js route change (minor UX) |

---

## 11. Known Bugs & Gotchas

1. **Technical indicators return arrays** — Frontend must take `.slice(-1)[0]` for RSI/MACD/BB/SMA (already fixed in `stock.js`)
2. **CoinGecko rate limits** — Dashboard has 300s TTL cache; empty `top_coins` means rate-limit hit, wait and retry
3. **passlib vs bcrypt** — NEVER use `passlib.hash.bcrypt`; use native `bcrypt` in `apps/api/app/auth/security.py`
4. **Apollo people names obfuscated** — Paid plan returns `first_name` + `last_name_obfuscated`; connector handles this
5. **Frontend API URL** — Use `${API}/market/...` NOT `${API}/api/market/...` (no `/api` prefix)
6. **yfinance NaN values** — Always sanitize with `_safe_num` / `_sanitize` before JSON response
7. **House stock-watcher S3** — Access Denied; use House Clerk FD.ZIP instead (already done)
8. **Next.js 12 Link** — Needs `<Link><a>...</a></Link>` pattern (not Next 13+ style)

---

## 12. Login Credentials (Staging)

| Field | Value |
|-------|-------|
| Platform URL | http://184.72.123.188:3003 |
| API Docs | http://184.72.123.188:3001/docs |
| Admin | http://184.72.123.188:3002 |
| Register new user | `POST /auth/register` with email + password |
| Existing account | Register via API or UI; bcrypt hashing is native |

API registration for new keys: use `abhishekk@kyma.world` / `Kulkarni@2002`

---

## 13. Daily Status Documents

| File | Content |
|------|---------|
| `5th_July.md` | Latest sprint: RSS, yfinance, multi-agent, crypto, gov trading, valuation, institutional |
| `Task/June task/25th_June.md` | RSS Phase 1 planning |
| `Task/June task/24th_June.md` | API keys integration |
| `Task/June task/23rd_June.md` | P1+P2+P3 entity tabs, exports |
| `Task/June task/22nd_June.md` | v2.0 features (Apollo, Apify, tracking, compare) |
| `james_requirements.md` | Full James requirements backlog |
| `docs/REQUIREMENT_GAP_ANALYSIS.md` | Spec vs implementation gaps |
| `SETUP.md` | Local + Docker setup |
| `api_credentials_audit.csv` | Audit trail of all API keys |

---

## 14. Product Principles

1. **Evidence first** — every claim traces to a source
2. **Official APIs first** — scrape only when necessary
3. **Human review** for sensitive outputs
4. **Multi-tenant governance** — permissions, audit, versioning
5. **Cost-aware** — right storage, cache aggressively (CoinGecko, Apollo credits)

---

## 15. Quick Start Checklist for New Teammate

- [ ] Clone repo, checkout `8th-july-sprint`
- [ ] Read this handoff + `5th_July.md` + `README.md`
- [ ] Confirm access to EC2 (`184.72.123.188`) and `.env`
- [ ] Run `pm2 list` — verify all services online
- [ ] Open http://184.72.123.188:3003 — walk through Dashboard, Stock, Crypto, Intelligence
- [ ] Open http://184.72.123.188:3001/docs — browse API
- [ ] Test: generate intelligence report for "Palantir Technologies"
- [ ] Test: Stock page → AAPL → Analyze
- [ ] Test: Crypto dashboard loads coins
- [ ] Read James's backlog in Section 10 — pick next priority with James
- [ ] Never commit `.env` or secrets

---

*End of Handoff — 13 July 2026*
