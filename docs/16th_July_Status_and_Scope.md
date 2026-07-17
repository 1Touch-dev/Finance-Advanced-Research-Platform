# Finance Intelligence Platform — Status & Next Scope

**Date:** 16th July 2026
**Author:** Anshuman Parmar
**Branch:** `8th-july-sprint`
**Staging:** http://184.72.123.188:3003 (Web) | :3001 (API) | :3002 (Admin)

---

## 1. Executive Summary

This document consolidates the current platform state, James's requirements from WhatsApp (13-16 July 2026), documentation review, and recommended next scope of work. The platform is live with 60+ API endpoints covering stock analysis, valuation, institutional tracking, government trading, crypto intelligence, and OSINT tools.

---

## 2. Current Platform State (as of 8th July 2026)

### 2.1 Live Services

| Service | Port | Technology | Status |
|---------|------|------------|--------|
| Backend API | 3001 | FastAPI (Python 3.11) | Running |
| Frontend | 3003 | Next.js 12 (React 17) | Running |
| Admin Dashboard | 3002 | React (CRA) | Running |
| RSS Poller | PM2 | Python worker | Running (15-min cycle) |
| PostgreSQL | 5432 | Database | Healthy |

### 2.2 Live Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Stock Analysis** | Price, 15 technical indicators (pure Python), AI consensus | Live |
| **DCF Valuation** | Intrinsic value vs market price, Bull/Base/Bear scenarios | Live |
| **Expert Analysis** | Multi-source news sentiment, weekly trend, analyst timeline | Live |
| **13F Institutional** | BlackRock, Vanguard, Berkshire flows, mega positions (>$1B) | Live |
| **Government Trading** | STOCK Act PTR filings, 15 tracked politicians, SEC Form 4 | Live |
| **Crypto Intelligence** | CoinGecko market data, whale alerts, BTC/ETH wallet lookup | Live |
| **RSS News** | 50 feeds, 882+ articles, entity tagging, category filters | Live |
| **OSINT Tools** | 40-platform username enumeration, domain WHOIS, LinkedIn signals | Live |
| **4-Agent Intelligence** | Fundamentals, Technical, Sentiment, Risk agents with composite score | Live |
| **Deep Company Analysis** | SEC EDGAR XBRL, cap table, insider trades, earnings | Live |

### 2.3 API Endpoints Summary

| Category | Endpoints |
|----------|-----------|
| RSS News | 5 |
| yfinance Market Data | 7 |
| Technical Indicators | 1 |
| Multi-Agent Intelligence | 4 |
| OSINT | 6 |
| Crypto | 10 |
| Government Trading | 6 |
| Deep Company | 9 |
| Valuation | 3 |
| Expert Analysis | 2 |
| Institutional | 3 |
| **Total** | **60+** |

### 2.4 API Keys Status

| API Key | Status | Notes |
|---------|--------|-------|
| SEC EDGAR | Live | Free, no key needed |
| FEC | Live | Free |
| USASpending | Live | Free |
| LDA.gov | Live | Free |
| OFAC | Live | Free |
| CourtListener | Live | Free |
| CoinGecko | Live | Free (5-min cache) |
| NewsAPI | Live | Free tier |
| Guardian | Live | Free tier |
| **ALEPH/OCCRP** | Pending | Account approval pending |
| **CA Secretary of State** | Pending | Application submitted |
| **Congress.gov Full** | Limited | DEMO_KEY only (paid key needed) |
| **Google SSO** | Pending | Routes ready, awaiting OIDC credentials |
| **Cobalt SOS** | Deferred | Trial rate-limited (429) |

### 2.5 Workarounds in Place

| Original Source | Workaround | Status |
|-----------------|------------|--------|
| House/Senate Stock Watcher | House Clerk + SEC Form 4 | Working |
| FT/WSJ/Nikkei | Google News RSS fallback | Working |
| FinCEN BOI | OpenCorporates fallback | Working |
| CA SOS | BizFile Playwright scrape | Working |
| Congress Legislation | DEMO_KEY (partial data) | Working |

---

## 3. James's Requirements (WhatsApp 13-16 July 2026)

### 3.1 Critical Bugs Reported

| # | Bug | Page | Priority |
|---|-----|------|----------|
| 1 | Sentiment not working | `/expert-analysis` | P0 |
| 2 | Earnings growth buttons not working | `/company` financials | P0 |
| 3 | Institutional data showing nothing | `/institutional` | P0 |
| 4 | Reports not generating | Intelligence reports | P0 |
| 5 | Apollo not integrated | LinkedIn scraping broken | P0 |

### 3.2 Feature Requests

#### High Priority (Explicit from James)

| # | Request | Details | Source |
|---|---------|---------|--------|
| 1 | **LinkedIn relationship scraping** | Find connections: studied together, worked together, trends | 14 Jul 9:01 |
| 2 | **Private company financials** | Contracts, valuations, capital raised for non-public companies | 14 Jul 9:02 |
| 3 | **Relationship visualizer** | Clear network graph with ability to add/compare people | 14 Jul 9:05 |
| 4 | **Stock price on timeline** | Clickable to view what happened + news at that time | 14 Jul 9:08 |
| 5 | **Public company search autofill** | Dropdown with ticker suggestions when typing | 14 Jul 9:09 |
| 6 | **All years in financials + editable tables** | All years data; filters; make clickable; **make table editable to add/edit fields** | 14 Jul 9:12 |
| 7 | **Expert analysis multiple perspectives** | Different analysis styles and investment profiles | 14 Jul 9:07 |
| 8 | **Whale tracker + News + Reddit** | Crypto whale tracker, news tracker, Reddit sentiment | 14 Jul 9:16 |
| 9 | **LinkedIn deeper scraping** | Employees, key hires, not just company level | 14 Jul 9:17 |
| 10 | **Timeline with meetings, purchases, trips** | Full event history for people | 14 Jul 9:18 |
| 11 | **Track Funds/PE/VC** | Track private equity, venture capitals, institutional investors separately | 14 Jul 9:13 |
| 12 | **Cross-company investor analysis** | Who else invested (non-gov) in multiple of same companies in large amounts | 14 Jul 9:14 |
| 13 | **Investment exposure analysis** | Analyze investments with most people, highest quantity, who is exposed most | 14 Jul 9:14 |
| 14 | **Decision interpretation** | Interpret why specific people are making key decisions (global markets/news) | 16 Jul 7:15 |

#### Report Generation Improvements (James 16 July)

| # | Requirement | Details |
|---|-------------|---------|
| 1 | **Interactive reports** | Search for similarities in entities, lobbying, all sources |
| 2 | **Multi-company comparison** | Compare multiple companies and their investors |
| 3 | **Find shared investors** | What funds invest in same companies |
| 4 | **PayPal Mafia style analysis** | Find schools, work connections, how they evolved |
| 5 | **Complete data reports** | Company, people, employees, key decisions, lobbying, contracts |
| 6 | **Relationship insights** | Corporate effect, government effect, customer acquisition effect |
| 7 | **Timelines with news** | All news related during timeline, summaries |
| 8 | **Government connections** | Links to governments or large investors/players |
| 9 | **Better visualizations** | Mapping, graphics, concise points, perspectives (see example PDF James sent) |
| 10 | **AI pattern detection** | Find key factors, elements, patterns, similarities |
| 11 | **Director/Advisor comparison** | Compare companies by directors, advisors, related founders |
| 12 | **Client relationship analysis** | Find patterns in client relationships across entities |

### 3.3 Entity Registry UI Issues

James noted on 14 Jul 9:05:
- "This flow seems unnecessary"
- "There should be one enrich"
- "Entity should have names and details"
- "Enrich should go on other slide"

### 3.4 Specific Page Issues

| Page | Issue | James Said |
|------|-------|------------|
| `/expert-analysis` | Sentiment section empty | "sentiment not working" |
| `/company` | Earnings buttons non-functional | "buttons for earnings growth etc not working" |
| `/institutional` | No data appearing | "institutional nothing appearing for me" |
| `/valuation` | Missing RSS feed | "add rss feed, filtered to only articles about each stock" |
| `/graph` | Unclear function | "graph function not clear" |
| `/institutional` | Missing features | "search by people, list of people, track all investments" |
| `/gov-trading` | Need more interactivity | "click on specific profiles, search/filter by investments" |
| `/expert-analysis` | Wrong company data showing | "Citigroup has nothing related to Apple. Should include info regarding Apple" |
| `/company` | Missing years of data | "should include all years, company is older" |

---

## 4. Pending API Approvals & Keys

### 4.1 Needs Action from James

| Item | Action Required | Priority |
|------|-----------------|----------|
| Google SSO | Provide OIDC client ID/secret | Medium |
| Congress.gov Full | Decide on paid API key | Medium |
| Cobalt SOS | Decide paid vs free scrapers | Low |

### 4.2 Waiting on External Approval

| Item | Status | Submitted |
|------|--------|-----------|
| CA Secretary of State API | Application pending | 12 Jun |
| ALEPH/OCCRP | Account approval pending | Jun |

### 4.3 Planned Migrations

| Current | Target | Status |
|---------|--------|--------|
| Apify scraping | Crawl4AI | Planned |
| RSS Phase 1 (50 feeds) | RSS Phase 2 (200+ feeds) | Planned |

---

## 5. Next Scope — Recommended Priority Order

### P0 — Bug Fixes (Immediate)

| # | Task | File(s) | Est. Effort |
|---|------|---------|-------------|
| 1 | Fix sentiment endpoint | `expert_analysis_connector.py` | 2-4 hrs |
| 2 | Fix earnings growth buttons | `apps/web/pages/company.js` | 1-2 hrs |
| 3 | Fix institutional data | `institutional_tracker.py` | 2-4 hrs |
| 4 | Fix report generation | `intelligence_report.py` | 4-8 hrs |

### P1 — James's Explicit Requests (This Week)

| # | Task | Details | Est. Effort |
|---|------|---------|-------------|
| 1 | **Apollo/LinkedIn integration** | Scrape relationships, education, work history | 1-2 days |
| 2 | **Stock price on timeline** | Clickable events with price context | 4-8 hrs |
| 3 | **Search autofill dropdown** | Ticker suggestions on company search | 4-6 hrs |
| 4 | **Entity registry UI cleanup** | Single enrich flow, names on details | 4-8 hrs |
| 5 | **Relationship visualizer improvements** | Clearer graph, add/compare people | 1 day |

### P2 — Report Enhancements (Next 2 Weeks)

| # | Task | Details | Est. Effort |
|---|------|---------|-------------|
| 1 | **Interactive reports** | Click-to-drill-down on any entity mentioned | 2-3 days |
| 2 | **Cross-entity comparison** | Find shared investors, employees, connections | 2-3 days |
| 3 | **PayPal Mafia style network analysis** | School connections, career evolution | 2-3 days |
| 4 | **AI pattern detection** | Find trends, similarities across entities | 1-2 days |
| 5 | **Timeline + stock price overlay** | Price movements + news correlation | 1 day |

### P3 — Data Gaps (Ongoing)

| # | Task | Details | Est. Effort |
|---|------|---------|-------------|
| 1 | **Deeper 10-K/10-Q LLM synthesis** | MD&A summarization with GPT-4o | 2-3 days |
| 2 | **13F quarter-over-quarter diff** | New/added/reduced/exited positions | 1-2 days |
| 3 | **Private company intelligence** | OpenCorporates, GLEIF, FinCEN BOI | 2-3 days |
| 4 | **Whale tracker + Reddit** | Crypto whale alerts, Reddit sentiment | 1-2 days |
| 5 | **RSS Phase 2** | Event clustering, fact extraction, contradiction detection | 3-5 days |

### P4 — Platform v2.0 Features (Backlog)

| # | Task | Details |
|---|------|---------|
| 1 | Per-entity RAG chat | pgvector + Claude for Q&A with citations |
| 2 | Tracking dashboard + daily digest | Monitor entities, email/SMS alerts |
| 3 | Comparison page | Up to 5 entities, radar/Sankey/bar charts |
| 4 | PDF export | Generate reports from RAG chat |
| 5 | Apollo email pipeline | Find executives, employees, email patterns |
| 6 | Apify social footprint | Twitter/X, Instagram, YouTube scraping |

---

## 6. Architecture Reference

### 6.1 Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11) |
| Frontend | Next.js 12 (React 17) |
| Admin | React (CRA) |
| Database | PostgreSQL |
| Search | OpenSearch (optional) |
| Storage | MinIO (S3-compatible) |
| Process Manager | PM2 |
| Containerization | Docker Compose |

### 6.2 Key Files

| Purpose | Path |
|---------|------|
| API entry point | `apps/api/app/main.py` |
| Market routes | `apps/api/app/api/market.py` |
| RSS worker | `apps/api/app/connectors/rss_worker.py` |
| yfinance connector | `apps/api/app/connectors/yfinance_connector.py` |
| Technical indicators | `apps/api/app/connectors/technicals_connector.py` |
| Multi-agent intelligence | `apps/api/app/connectors/multi_agent_intelligence.py` |
| OSINT connector | `apps/api/app/connectors/osint_connector.py` |
| Crypto connector | `apps/api/app/connectors/crypto_connector.py` |
| Government trading | `apps/api/app/connectors/gov_trading_connector.py` |
| Deep company | `apps/api/app/connectors/company_deep_connector.py` |
| Valuation | `apps/api/app/connectors/valuation_connector.py` |
| Expert analysis | `apps/api/app/connectors/expert_analysis_connector.py` |
| Institutional tracker | `apps/api/app/connectors/institutional_tracker.py` |
| PM2 config | `ecosystem.config.js` |
| Docker Compose | `docker-compose.yml` |

### 6.3 Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| Home | `/` | Dashboard with feature cards |
| Stock Analysis | `/stock` | Price, technicals, AI consensus |
| DCF Valuation | `/valuation` | Intrinsic value analysis |
| Expert Analysis | `/expert-analysis` | Sentiment tracking |
| Deep Company | `/company` | SEC filings, cap table |
| Institutional | `/institutional` | 13F holdings tracker |
| Government Trading | `/gov-trading` | Congressional + insider trading |
| Crypto | `/crypto` | Market dashboard, wallet lookup |
| Intelligence Reports | `/intelligence` | Entity dossiers |
| Search | `/search` | Global article search |
| Timeline | `/timeline` | Event chronology |
| Entity Registry | `/registry` | OSINT enrichment |
| Relationship Graph | `/graph` | Network visualization |

---

## 7. Contacts & Resources

| Resource | Link/Info |
|----------|-----------|
| Staging Server | http://184.72.123.188 |
| SSH | `ssh finance-intelligence` |
| GitHub Repo | https://github.com/1Touch-dev/Finance-Advanced-Research-Platform |
| WhatsApp Group | Finance Intelligence Platform |
| Previous Handoff | `docs/Finance_Platform_Handoff.md` |
| Sprint Reports | `reports/*.md` |
| Requirements | `docs/james_requirements.md` |

---

## 8. Appendix: WhatsApp Chat Log Summary (13-16 July 2026)

### 13 July 2026
- **5:04 PM** — James: "Hi; was any work done on this"
- **5:07 PM** — Anshuman: Got handoff today, what's next milestone?
- **5:08 PM** — James: "Can someone resend the full roadmap please"
- **5:11 PM** — James: "For any api we need an approval let's find an alternative"
- **5:17 PM** — Abhishek: Sent API access status update
- **5:21 PM** — James: "Ca secretary api; have we found any alternatives"
- **5:23 PM** — Abhishek: BizFile Playwright scrape works

### 14 July 2026
- **9:01 AM** — James: LinkedIn scraping needed for relationships, trends
- **9:02 AM** — James: Private company financial data needed
- **9:05 AM** — James: Entity registry flow issues, need visualizer
- **9:06 AM** — James: Lobbying info, government tracking, crypto
- **9:07 AM** — James: Expert analysis needs multiple perspectives
- **9:08 AM** — James: Sentiment not working, earnings buttons broken
- **9:09 AM** — James: Need stock price on timeline, search autofill
- **9:12 AM** — James: All years in financials, institutional not showing
- **9:13 AM** — James: Track funds, PE, VC, institutional investors, crypto whales
- **9:15 AM** — James: Government trading needs click profiles, filters
- **9:16 AM** — James: Need whale tracker, news tracker, Reddit
- **9:17 AM** — James: LinkedIn needs employees, key hires
- **9:18 AM** — James: Reports not generating, timeline needs events
- **9:49 AM** — Abhishek: Noted all issues, will implement

### 15 July 2026
- **8:49 AM** — James: "please let me know who is gonna work on these changes"
- **11:20 AM** — Anshuman: "I will work on these changes along with Akash or might be Jitu"

### 16 July 2026
- **7:15 AM** — James: Reports need to be interactive, find similarities, lobbying, comparisons, PayPal Mafia style analysis, timelines with news, government connections, better visualizations
- **7:17 AM** — James: Sent example PDF report for reference
- **8:51 AM** — Anshuman: Working on aligning frontend, understanding platform
- **9:44 AM** — James: "writing complete reports, with detailed analysis"
- **12:57 PM** — Anshuman: Got the flow, starting validation

---

*Document created: 16 July 2026*
*Next review: After P0 bug fixes completed*
