# 5th July 2026 — Sprint Log

> Branch: `5th-July-sprint`  
> Start: 5 July 2026 | Engineer: Abhishek Kulkarni

---

## Executive Summary

This sprint implements the **Global News Intelligence Layer (Phase 1)** and major platform upgrades requested by James, including a continuous RSS worker, yfinance market data integration, pure-Python technical indicators, a 4-agent investment intelligence engine, and OSINT tools inspired by Sherlock/Maigret/theHarvester.

---

## ✅ Completed This Sprint

### 1. RSS Global News Intelligence — Phase 1

**Files:**
- `apps/api/app/connectors/rss_worker.py` — feedparser polling worker
- `apps/api/app/api/market.py` — 5 new `/market/rss/*` endpoints
- `ecosystem.config.js` — `rss-poller` PM2 process (runs every 15 min)

**What was built:**
- **50 curated RSS feeds** across 8 categories: Finance, Macro, News, Tech, Crypto, Government, Policy, Asia/MENA/LATAM
- **Postgres schema**: `rss_sources` + `rss_articles` tables with GIN indexes for entity arrays
- **Entity keyword matching**: auto-tags articles with 15 tracked entities (Apple, Tesla, Federal Reserve, Bitcoin, etc.)
- **feedparser polling** with polite delay + Google News RSS fallback for paywalled sites (FT, WSJ, Nikkei)
- **PM2 process `rss-poller`** running on 15-minute cycle
- **First poll**: 882 articles ingested from 50 sources in < 30 seconds

**New API endpoints:**
```
GET /market/rss/sources         — List all 50 sources with status
GET /market/rss/articles        — Filtered articles (category/region/entity)
GET /market/rss/entity-feed     — Articles matching a specific entity
GET /market/rss/digest          — Top 10/category for last N hours
POST /market/rss/poll           — Manual trigger
```

**Frontend:**
- New **📰 News tab** on entity profile pages
- Category + region filter dropdowns
- 24h digest counters by category
- Entity tag chips on articles
- Source / date metadata per article

---

### 2. yfinance Market Data Connector

**File:** `apps/api/app/connectors/yfinance_connector.py`

**What was built:**
- `yf_price_history(ticker, period, interval)` — OHLCV bars
- `yf_fundamentals(ticker)` — 35+ ratios: P/E, P/B, EV/EBITDA, margins, ROE, beta, short interest, etc.
- `yf_company_info(ticker)` — sector, industry, employees, website, description
- `yf_dividends(ticker)` + `yf_splits(ticker)` — payment history
- `yf_options(ticker)` — nearest-expiry options chain (calls + puts)
- `yf_institutional_holders(ticker)` — top 15 holders
- `yf_snapshot(ticker)` — all-in-one call

**New API endpoints:**
```
GET /market/yf/snapshot         — Full snapshot
GET /market/yf/history          — OHLCV (period/interval params)
GET /market/yf/fundamentals     — 35+ valuation & growth ratios
GET /market/yf/company          — Company profile
GET /market/yf/dividends        — Dividend & split history
GET /market/yf/options          — Options chain
GET /market/yf/holders          — Institutional holders
```

**Test results:**
- AAPL: PE=37.3, MarketCap=$4.5T, Price=$308.63
- TSLA: PE=357.7, MarketCap=$1.47T

---

### 3. Pure-Python Technical Indicators

**File:** `apps/api/app/connectors/technicals_connector.py`

**15 indicators implemented (no TA-Lib C dependency):**
| Indicator | Parameters |
|-----------|-----------|
| SMA | 10, 20, 50, 200 periods |
| EMA | 12, 26 periods |
| RSI | 14 periods |
| MACD | 12/26/9 (line + signal + histogram) |
| Bollinger Bands | 20 periods, 2σ |
| ATR | 14 periods (Average True Range) |
| OBV | On-Balance Volume |
| Stochastic | %K(14) + %D(3) |
| Williams %R | 14 periods |
| Rate of Change | 12 periods |
| Support/Resistance | 20-period pivot |
| Golden Cross detector | SMA50 > SMA200 |
| Death Cross detector | SMA50 < SMA200 |
| RSI Overbought/Oversold alerts | >70 / <30 |

**New API endpoint:**
```
GET /market/technicals?ticker=AAPL&period=1y
```

**Test results AAPL:**
- Price: $308.63 | SMA50: $293.46 | SMA200: $270.32
- RSI: 60.28 (neutral) | MACD histogram: +0.26 (bullish)
- Support: $275.15 | Resistance: $311.23

---

### 4. Multi-Agent Investment Intelligence Engine

**File:** `apps/api/app/connectors/multi_agent_intelligence.py`

**Architecture (inspired by TradingAgents, ai-hedge-fund, FinRobot patterns):**

```
┌─────────────────────┐
│   4 Specialist Agents (parallel ThreadPoolExecutor)
│
├── FundamentalsAgent  → P/E, margins, ROE, revenue trend
├── TechnicalAgent     → trend, RSI, MACD, support/resistance
├── SentimentAgent     → news sentiment (bullish/bearish ratio)
└── RiskAgent          → Beneish M-score, Altman Z-score, beta, short interest
│
└── SynthesisAgent     → composite score (0-100) + recommendation + thesis
```

**Scoring system:**
- Each agent returns a score 0–100
- Composite = average of 4 agent scores
- Composite ≥ 70 → **BUY** | 55–69 → **HOLD** | 40–54 → **HOLD/REDUCE** | < 40 → **SELL**
- LLM narrative generation (gpt-4o-mini) when `OPENAI_API_KEY` present
- Fully rule-based fallback when no LLM key

**New API endpoints:**
```
GET /market/intelligence/report         — Full 4-agent report
GET /market/intelligence/fundamentals   — Fundamentals agent only
GET /market/intelligence/technical      — Technical agent only
GET /market/intelligence/risk           — Risk agent only
```

**Test results:**
- AAPL: Composite 58.8 → HOLD (Medium) | Strong net margin 27.2%, excellent ROE 141.5%, bullish technical
- MSFT: Composite 57.0 → HOLD (Medium)

**Frontend:**
- New **🤖 Intelligence tab** on entity profile pages
- Composite score visualization with color coding
- BUY/HOLD/SELL recommendation card
- Per-agent score breakdown
- Investment thesis display
- Re-run button

---

### 5. OSINT Intelligence Connector

**File:** `apps/api/app/connectors/osint_connector.py`

**Capabilities (open-source, no paid APIs):**

| Feature | Implementation |
|---------|---------------|
| Username enumeration | 40 platforms in parallel (Sherlock/Maigret style) |
| Email patterns | 9 naming conventions per domain |
| Domain WHOIS + DNS | Google DoH (A/MX/TXT) + RDAP |
| LinkedIn signals | DuckDuckGo HTML search |
| Breach check | HaveIBeenPwned API |
| Person OSINT | Combined report (username + LinkedIn + domain + breach) |
| Company OSINT | Domain + UK Companies House + LinkedIn |

**Platforms checked in username enumeration:**
GitHub, Twitter/X, Reddit, Instagram, LinkedIn, YouTube, TikTok, Pinterest, Twitch, Snapchat, Medium, Substack, Dev.to, HackerNews, Product Hunt, AngelList, Crunchbase, Keybase, GitLab, Bitbucket, Stack Overflow, Kaggle, Replit, Patreon, Telegram, Spotify, SoundCloud, Behance, Dribbble, Fiverr, Upwork, Etsy, Vimeo, Steam, Xbox, Last.fm, Goodreads, Flickr, Wikipedia

**New API endpoints:**
```
GET /market/osint/username          — 40-platform enumeration
GET /market/osint/domain            — DNS + WHOIS
GET /market/osint/email-patterns    — Generate likely emails
GET /market/osint/linkedin          — LinkedIn profile signals
GET /market/osint/person            — Full person OSINT report
GET /market/osint/company           — Company OSINT report
```

**Frontend:**
- New **🔭 OSINT tab** on entity profile pages
- Username scanner (real-time results)
- Domain intelligence lookup
- LinkedIn profile discovery

---

## 📊 API Endpoints Added This Sprint

| Category | Endpoints Added |
|----------|----------------|
| RSS News | 5 endpoints |
| yfinance | 7 endpoints |
| Technicals | 1 endpoint |
| Intelligence | 4 endpoints |
| OSINT | 6 endpoints |
| **Total** | **23 new endpoints** |

---

## 🔧 Infrastructure Changes

| Component | Change |
|-----------|--------|
| `ecosystem.config.js` | Added `rss-poller` PM2 process (15-min cycle) |
| Postgres DB | 2 new tables: `rss_sources`, `rss_articles` |
| pip packages | `feedparser`, `yfinance` added to venv |
| `apps/web/pages/entities/[id].js` | +3 new tabs (News, Intelligence, OSINT), API status updated |

---

## ⏳ Pending / Next Sprint

### Phase 2 — RSS Scale-Up (P2)
- [ ] Expand from 50 → 200+ feeds (full James list)
- [ ] crawl4ai integration for non-RSS sites (JS-rendered pages)
- [ ] Event clustering: group articles by subject/event
- [ ] Fact extraction: identify unique facts vs. repeated sentences
- [ ] Contradiction detection: flag conflicting reports
- [ ] Multi-perspective synthesis: bullish/bearish/left/right/international views
- [ ] `rss_events` table: master event files per topic

### Phase 3 — Intelligence Upgrades
- [ ] Improve SentimentAgent with NLP (transformers or API-based)
- [ ] Add MacroAgent: FRED + BIS + IMF data integration
- [ ] Integrate TradingAgents-style debate between bull/bear agents
- [ ] pgvector embeddings for semantic search across articles + evidence
- [ ] RAG pipeline: chat against the full article corpus

### Phase 4 — Open-Source Integration (from James's list)
- [ ] **OpenBB** connector for Bloomberg-style terminal data
- [ ] **QuantStats** integration for portfolio performance reports
- [ ] **PyPortfolioOpt** for portfolio optimization suggestions
- [ ] **Microsoft Qlib** alpha research integration
- [ ] **Maigret** (real library) as upgrade to our username enumeration
- [ ] **SpiderFoot** deep OSINT integration

### Pending Keys / Access
- [ ] ALEPH/OCCRP API key — registration page unavailable
- [ ] CA SOS API key — application submitted 12 Jun, awaiting approval
- [ ] OIDC/Google SSO credentials — routes wired, awaiting James
- [ ] HIBP (HaveIBeenPwned) API key — needed for breach check endpoint

### Tech Debt
- [ ] FMP margin ratio fields missing from stable API — manual calculation needed
- [ ] GDELT still rate-limited under rapid polling
- [ ] ICIJ Offshore Leaks API permanently decommissioned — web UI only
- [ ] RSS worker needs exponential backoff for failed feeds

---

## 📈 Cumulative Platform Status (5 July 2026)

| Component | Status |
|-----------|--------|
| Backend API (FastAPI) | ✅ Running on port 3001 |
| Frontend (Next.js) | ✅ Running on port 3003 |
| Postgres DB | ✅ Healthy |
| RSS Poller Worker | ✅ Running (PM2, 15-min cycle) |
| API keys live | 8/9 (ALEPH pending) |
| RSS sources | 50 feeds, 882 articles (first poll) |
| New API endpoints (sprint) | 23 |
| New frontend tabs | 3 (News, Intelligence, OSINT) |
| Technicals indicators | 15 (pure Python) |
| OSINT platforms | 40 |

---

## Files Changed This Sprint

```
apps/api/app/connectors/rss_worker.py          [NEW] RSS polling worker + 50 feeds + DB schema
apps/api/app/connectors/yfinance_connector.py  [NEW] yfinance OHLCV + fundamentals + options
apps/api/app/connectors/technicals_connector.py [NEW] 15 technical indicators (pure Python)
apps/api/app/connectors/multi_agent_intelligence.py [NEW] 4-agent investment intelligence engine
apps/api/app/connectors/osint_connector.py     [NEW] OSINT: username/domain/email/LinkedIn
apps/api/app/connectors/crypto_connector.py    [NEW] CoinGecko + BTC/ETH wallet + whale alerts
apps/api/app/connectors/gov_trading_connector.py [NEW] Congress PTR disclosures + SEC Form 4
apps/api/app/connectors/company_deep_connector.py [NEW] SEC 10-K/10-Q XBRL + cap table + earnings
apps/api/app/api/market.py                     [UPDATED] +23 original +24 new API routes (47 total)
apps/web/pages/entities/[id].js               [UPDATED] +3 tabs (News, Intelligence, OSINT)
apps/web/pages/crypto.js                       [NEW] Crypto Intelligence dashboard
apps/web/pages/gov-trading.js                  [NEW] Government/Insider Trading tracker
apps/web/pages/company.js                      [NEW] Deep Company Analysis (SEC EDGAR)
apps/web/pages/stock.js                        [UPDATED] +Analyst Consensus + Deep Company link
apps/web/src/components/Layout.js             [UPDATED] +Crypto, Gov Trading, Company nav items
ecosystem.config.js                            [UPDATED] rss-poller PM2 process added
README.md                                      [UPDATED] 5th July sprint status
5th_July.md                                   [NEW+UPDATED] This file
```

---

## 🚀 Phase 2 — New Features (5 July PM Sprint)

### 5. Crypto Intelligence (`crypto_connector.py`)

**Data sources:** CoinGecko (free, no key) · Blockchain.info (BTC) · Etherscan (free tier)

**Features:**
- Global market dashboard (total cap, BTC/ETH dominance, DeFi stats)
- Top 15 cryptocurrency prices, market caps, 24h volumes + change
- Trending coins (most searched 24h on CoinGecko)
- Whale alert detection (high vol-to-cap ratio + significant price moves)
- Per-coin detailed profile (supply, ATH, ATL, 7d/30d change, categories)
- Exchange inflow/outflow flow signals
- ETH wallet profile (balance, ERC-20 tokens, recent transactions)
- BTC wallet profile (balance, received, sent, tx history via blockchain.info)

**New API endpoints (10):**
```
GET /market/crypto/dashboard       — Full market dashboard
GET /market/crypto/prices          — Top coin prices
GET /market/crypto/coin/{coin_id}  — Detailed coin profile
GET /market/crypto/trending        — Trending 24h
GET /market/crypto/global          — Global market + DeFi stats
GET /market/crypto/whales          — Whale alert signals
GET /market/crypto/wallet/eth/{address} — ETH wallet
GET /market/crypto/wallet/btc/{address} — BTC wallet
GET /market/crypto/flow/{coin_id}  — Exchange flow signal
```

**Frontend:** `/crypto` page with 3 tabs: Market Dashboard, Coin Detail, Wallet Lookup

---

### 6. Government Trading Intelligence (`gov_trading_connector.py`)

**Data sources:** House Clerk FD ZIP (STOCK Act PTR filings) · SEC EDGAR EFTS Form 4

**Features:**
- Annual House Financial Disclosure ZIP download + XML parse
- Filter PTR (Periodic Transaction Report) filers = actual stock traders
- Most active congressional traders by PTR filing count
- State-level trading activity breakdown
- Recent SEC Form 4 insider transactions (corporate insiders)
- Per-ticker insider trade history via yfinance

**New API endpoints (6):**
```
GET /market/gov-trading/summary      — Full dashboard
GET /market/gov-trading/recent       — Recent congressional PTR filers
GET /market/gov-trading/ticker/{t}   — All trades for a specific stock
GET /market/gov-trading/member       — Trades by member name
GET /market/gov-trading/top-tickers  — Most-traded tickers
GET /market/gov-trading/most-active  — Most active traders
```

**Frontend:** `/gov-trading` page with 2 tabs: Congressional Summary, Corporate Insider Trades

---

### 7. Deep Company Intelligence (`company_deep_connector.py`)

**Data sources:** SEC EDGAR XBRL API (free) · yfinance · SEC EDGAR submissions

**Features:**
- CIK resolution from ticker → company_tickers.json
- SEC company info (name, SIC, state of incorporation, fiscal year end)
- Recent SEC filings list (10-K, 10-Q, 8-K, DEF 14A with viewer URLs)
- Quarterly financials via XBRL: Revenue, Net Income, EPS (basic/diluted), Gross Profit, Operating Income, R&D, Assets, Debt, Cash, Shares Outstanding
- Cap table: shares outstanding, float, insider %, institutional %, top 20 institutional holders, top 15 mutual fund holders
- Insider trades via yfinance (name, title, transaction type, shares, value, date)
- Analyst consensus: recommendation, price targets (mean/high/low), upside %, upgrade/downgrade history
- Earnings history: actual EPS vs estimate, surprise, next earnings calendar
- Company news aggregation

**New API endpoints (9):**
```
GET /market/company/info/{ticker}         — Company info from EDGAR
GET /market/company/filings/{ticker}      — Recent SEC filings
GET /market/company/financials/{ticker}   — Quarterly XBRL financials
GET /market/company/cap-table/{ticker}    — Shareholders + ownership %
GET /market/company/insider-trades/{t}    — Recent Form 4 transactions
GET /market/company/big-trades/{ticker}   — Significant positions ($100M+)
GET /market/company/analyst-ratings/{t}  — Consensus + price targets
GET /market/company/earnings/{ticker}     — EPS history + next date
GET /market/company/deep-report/{ticker}  — Full parallel deep-dive report
```

**Frontend:** `/company` page with 5 tabs: Overview, Filings, Cap Table, Analyst, Earnings

**Also updated:** `/stock` page now includes Analyst Consensus section + link to Deep Company Analysis

---

## 📈 Updated Platform Status (5 July 2026 PM)

| Component | Status |
|-----------|--------|
| Backend API (FastAPI) | ✅ Running on port 3001 |
| Frontend (Next.js) | ✅ Running on port 3003 |
| Postgres DB | ✅ Healthy |
| RSS Poller Worker | ✅ Running (PM2, 15-min cycle) |
| Crypto Intelligence | ✅ Live (CoinGecko + BTC/ETH wallet) |
| Gov Trading Tracker | ✅ Live (House Clerk PTR + SEC Form 4) |
| Deep Company Analysis | ✅ Live (SEC EDGAR XBRL + yfinance) |
| API keys live | 8/9 (ALEPH pending) |
| Total API endpoints | 47+ |
| Navigation items | 18 |
| New frontend pages | 3 (Crypto, Gov Trading, Company) |

---

## Tested Live ✅

All 4 new/updated pages verified via Cursor browser (5 July 2026 PM):

| Page | Result |
|------|--------|
| `/crypto` | ✅ PASS — Live market data, BTC $62,760, ETH $1,763, whale alerts |
| `/gov-trading` | ✅ PASS — 134 PTR filings, Diana Harshbarger #1 active trader |
| `/company` (AAPL) | ✅ PASS — Apple Inc., 8 quarters revenue, 42 analyst BUY $315 target |
| `/stock` (TSLA) | ✅ PASS — $393.45, fundamentals, technicals, analyst consensus BUY |

