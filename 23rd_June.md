# 23rd June 2026 — Full Platform Status, Pending Work & Roadmap

**Purpose:** Complete honest status of the Financial Intelligence Platform as of 23 Jun 2026.  
Cross-verified against:
- `Enterprise Intelligence Platform v2.0 Requirements.docx`
- `Jarvis Nexus Dashboard UI Spec (2).docx`
- All James WhatsApp messages (18–22 Jun)
- Actual code in the repository

**Staging:** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`  
**Repo:** https://github.com/semajkyma/coritiba-platform  
**Prior docs:** [22nd_June.md](./22nd_June.md) · [18th_June.md](./18th_June.md) · [README.md](./README.md)

---

## 0) What James Asked For (Master Reference)

### WhatsApp — 22 Jun 2026
- "you get where missing all insights, and kpis, filters, labels, categories, more tables on all projects correct?" → ✅ Built (KPI strip, filter bar, labels, tables, CSV export)
- "think about two things: 1. team of agents (B2B/B2C outreach, founder mode, GTM) 2. centralised system to manage all software, websites, social medias in one suite" → Documented. Future product sprint.
- James sent `Enterprise Intelligence Platform v2.0 Requirements.docx` + `Jarvis Nexus Dashboard UI Spec (2).docx` → These define everything below.

### Key documents received
- **v2.0 Requirements.docx** — defines 7 Feature Blocks (A–G) + full data source list + all credentials + OSINT toolkit + 10-agent swarm + UI spec
- **Jarvis Nexus Dashboard UI Spec** — defines a separate executive operating system product (6-tab dashboard, KPI bundles, approval engine, agent monitoring, recommendation engine)

---

## 1) ✅ DONE — Confirmed working on staging (23 Jun)

### Layer 1 — Core US Federal Dossier (100%)
| Feature | Status |
|---------|--------|
| 9–12 section intelligence reports | ✅ Live |
| SEC, FEC, FARA, LDA, USASpending, CourtListener, OFAC connectors | ✅ Live |
| Wikipedia + GPT-4o deep narrative | ✅ Live |
| PayPal Mafia demo seeds (Palantir, Anduril, Peter Thiel, Founders Fund, etc.) | ✅ Live |
| Two-sided lobbying disclosure (registrant + client side) | ✅ Live |
| Cytoscape.js relationship graph embedded in reports | ✅ Live |

### Layer 2 — KPIs, Filters, Tables (100%)
| Feature | Status |
|---------|--------|
| KPI strip (6 cards: entities, claims, sources, relationships, high-confidence, avg confidence) | ✅ |
| Filter bar — Category, Source, Confidence, Free-text search | ✅ |
| Section category labels (Financial, Government, Legal, etc.) | ✅ |
| Sortable tables + CSV export | ✅ |
| Click-to-investigate (click any entity name → auto-generate sub-report) | ✅ |
| Contracts two-sided (recipient + agency side) | ✅ |
| KPI Dashboard view mode toggle (📄 Report / 📊 Dashboard) | ✅ |

### v2.0 Features (shipped 22 Jun)
| Task | Feature | API / Page | Status |
|------|---------|------------|--------|
| T1–T4 | KPI strip, filter bar, labels, tables | `intelligence.js` | ✅ |
| T5 | Click-to-investigate | `intelligence.js` | ✅ |
| T6 | Contracts two-sided | `intelligence_service.py` | ✅ |
| T7 | Browser research agent (8 jurisdictions) | `POST /intelligence/browser-research` | ✅ |
| T8–T9 | PitchBook realtime-scraper + Apify poll fix | `apify_connector.py` | ✅ |
| T12 | KPI Dashboard view toggle | `intelligence.js` | ✅ |
| T13 | Apollo: org enrichment + org chart routes | `GET /intelligence/apollo/org` etc. | ✅ |
| T14 | Apify social footprint (Twitter, Instagram, YouTube) | `apify_connector.py` | ✅ |
| T15 | Private company intel (OpenCorporates, GLEIF, FinCEN, FDIC) | `private_company_connector.py` | ✅ |
| T16 | FEC/FARA two-sided disclosure | `intelligence_service.py` | ✅ |
| T17 | Apify key people scraper + auto graph edges | `apify_connector.py` | ✅ |
| T18 | Entity profile `/entities/[id]` — 5 tabs, KPI bar, badges | `pages/entities/[id].js` | ✅ |
| T19 | Person timeline page `/timeline` | `pages/timeline.js` | ✅ |
| T20 | Comparison page `/compare` — radar chart, KPI table, board overlap | `pages/compare.js` | ✅ |
| T21 | PDF export (`/intelligence/{id}/pdf`) | `pdf_service.py` | ✅ |
| T22 | Graph export PNG/JSON | `intelligence.js` | ✅ |
| T23 | Per-entity RAG chat (floating panel, TF-IDF retrieval) | `rag_chat_service.py` + `POST /chat/ask` | ✅ |
| T24 | Tracking dashboard + daily digest | `tracking_service.py` + `/tracking` | ✅ |

### Connectors live
| Connector | Status |
|-----------|--------|
| Apify — LinkedIn Profile Scraper | ✅ ($500 plan live) |
| Apify — PitchBook Realtime Scraper | ✅ |
| Apify — Google News Scraper | ✅ (47–81 articles/query) |
| Apify — Twitter/X Scraper | ✅ |
| Apify — Instagram Scraper | ✅ |
| Apify — YouTube Scraper | ✅ |
| Apollo.io — Org Enrichment (domain-based) | ✅ (free tier) |
| Apollo.io — People Search | ✅ endpoint exists; full data needs paid plan |
| OpenCorporates | ✅ |
| GLEIF LEI | ✅ |
| FinCEN | ✅ |
| FDIC | ✅ |

---

## 2) ⚠️ PARTIALLY DONE — Built but incomplete vs. spec

### P-A: Entity Profile — 5 tabs built, spec requires 9
**Current tabs:** Overview · Relationships · Evidence · Timeline · Related  
**Missing tabs (from v2.0 Requirements.docx Section 9.2):**

| Missing Tab | What it needs |
|-------------|---------------|
| **Financial** | 20-year revenue/margin/FCF charts (Recharts LineChart), Beneish M-Score gauge, Altman Z-Score trend, Insider transaction timeline, Peer comparison table |
| **Government Exposure** | Contract treemap by agency (clickable), Lobbying spend bar chart by year/issue, FEC contribution network (Sigma.js), Regulatory risk matrix |
| **Legal & Risk** | Case timeline (Vis.js), Case type breakdown (pie chart), Sanctions screening result card, Enforcement actions list |
| **People & Contacts** | Apollo-enriched executives with emails + titles + LinkedIn URLs; Board members from DEF 14A; cross-ref with SEC officers |
| **Social Footprint** | Platform presence cards (Twitter/LinkedIn/Instagram/YouTube), recent posts feed, sentiment trend chart, key quotes, geolocation map (Leaflet.js) |
| **Intelligence Report tab** | Full 7-section dossier embedded within entity profile (currently separate page) |
| **RAG Chat tab** | Dedicated chat panel per entity, suggested questions, "Generate PDF from chat" button |

> Note: Legal & Government Exposure tabs overlap with what's in the main report — the entity profile should embed these as dedicated tabs with charts, not just text.

### P-B: Intelligence Report — 2 of 4 view modes missing
**Current:** Report View ✅ · KPI Dashboard View ✅  
**Missing:**
- **Timeline View** — all events chronologically on a Vis.js Timeline component
- **Graph View** — Cytoscape graph embedded directly inside the report page view toggle

### P-C: Export formats — PDF/CSV done, Word/PPT/Excel missing
| Format | Status |
|--------|--------|
| PDF (ReportLab) | ✅ |
| CSV (source appendix) | ✅ |
| Graph PNG/JSON | ✅ |
| **Word (.docx)** | ❌ `python-docx` is in dependencies but no export route built |
| **PowerPoint (.pptx)** | ❌ Not built |
| **Excel (.xlsx)** | ❌ Not built |

### P-D: Comparison page — 3 of 5 spec'd visualisations missing
**Current:** Radar chart ✅ · KPI table ✅ · Board Overlap ✅  
**Missing:**
- Grouped Bar Chart (financial metrics by year — Recharts)
- Timeline Overlay (key events for all entities on same axis)
- Network Overlap Graph (shared nodes — Sigma.js)
- Sankey Diagram (money flows — D3.js)

### P-E: RAG Chat — TF-IDF only, not pgvector/embeddings
**Current:** TF-IDF keyword ranking (works, fast)  
**Spec:** `text-embedding-3-large → pgvector → similarity_search(top_k=20)` with Claude claude-3-5-sonnet  
**Gap:** Semantic similarity search not implemented; RAG quality lower than spec'd

### P-F: Tracking — alerts page missing
**Current:** `/tracking` page ✅ — watchlist CRUD + digest trigger  
**Missing:**
- `GET /tracking/alerts` API route
- `/tracking/alerts` dedicated page (alert inbox with severity, acknowledge, snooze)

---

## 3) ❌ NOT DONE — In spec, not yet built

### Priority 1 — High impact, Financial Intelligence Platform core

| # | Feature | Spec Reference | Notes |
|---|---------|---------------|-------|
| N1 | **Beneish M-Score + Altman Z-Score calculations** | v2.0 §4, Financial tab | Computed from XBRL data (SEC connector already pulls XBRL); display as gauges |
| N2 | **20-year financial charts on entity profile** | Section 9.2 Tab 2 | Revenue/margin/FCF from `data.sec.gov/api/xbrl/companyfacts` |
| N3 | **Insider transaction timeline** | Section 9.2 Tab 2 | Form 4 data via SEC connector |
| N4 | **API Status Panel component** | Feature Block G | Collapsible panel top-right of every report; green/yellow/red per source; credits remaining for Apollo/Apify |
| N5 | **Date-range filter on report claims** | Feature Block G | "Last 30d / 1yr / All time" filter chip in FilterBar |
| N6 | **`/intelligence/{id}` dedicated report page** | Section 9.1 | Each saved report should have its own URL; currently inline only |
| N7 | **`/entities/{id}/chat` dedicated page** | Section 9.1 | Full-page chat per entity (not just floating panel) |
| N8 | **`POST /entities/compare-chat` route** | Feature Block C | Compare two entities via RAG — entity_a, entity_b, question |
| N9 | **"Generate PDF from chat" button** | Feature Block C | On chat thread, export cited Q&A as PDF |
| N10 | **`/tracking/alerts` page + API** | Feature Block E | Alert inbox; `GET /tracking/alerts`; severity + acknowledge + snooze |
| N11 | **Search-within-report with highlight** | Feature Block G | Ctrl+F equivalent — free-text search with yellow highlight on matching claims |

### Priority 2 — New data connectors (all free APIs)

| # | Connector | API | Notes |
|---|-----------|-----|-------|
| N12 | **FINNHUB** | `finnhub.io` — free, 60 req/min | Real-time quotes, financial statements, earnings |
| N13 | **FMP (Financial Modeling Prep)** | `financialmodelingprep.com` — 250 req/day free | Full income statement / balance sheet / cash flow (feeds M-Score/Z-Score) |
| N14 | **Alpha Vantage** | free, 25 req/day | OHLCV + technicals |
| N15 | **FRED (Federal Reserve)** | free, unlimited | Macro data — inflation, rates, GDP |
| N16 | **NewsAPI** | free, 100 req/day | Breaking news by entity name |
| N17 | **The Guardian API** | free, unlimited (with attribution) | Global news search |
| N18 | **NYT Article Search** | free, 500 req/day | Historical news archive |
| N19 | **GDELT** | No key needed | Global news events with sentiment; `gdeltproject.org/api/v2` |
| N20 | **UK Companies House** | free, 600 req/min | UK officers, filings, PSC (persons with significant control) |
| N21 | **OpenSanctions** | Already in `.env` (`f13ceaf124...`) | 320+ sanctions/PEP lists — confirm it's being used |
| N22 | **ALEPH / OCCRP** | Free for non-commercial | Leaked document datasets (Panama Papers, etc.) |
| N23 | **ICIJ Offshore Leaks** | No key | `offshoreleaks.icij.org/api/search?q={name}` |

### Priority 3 — UX completeness

| # | Feature | Notes |
|---|---------|-------|
| N24 | **`/saved` reports library page** | List all saved reports with search, filter, delete |
| N25 | **`/admin` page in Next.js app** | Currently on port 3002 (CRA); integrate into main app |
| N26 | **`/portfolio/{id}` page** | Portfolio risk dashboard |
| N27 | **`/review/{id}` page** | Report review workspace |
| N28 | **Contract treemap (entity profile)** | By agency, clickable (Recharts Treemap) |
| N29 | **Lobbying spend bar chart (entity profile)** | By year + by issue |
| N30 | **"Add to Tracking" button on every entity/report page** | Spec: every entity card and report has this button |

### Priority 4 — Advanced / Future

| # | Feature | Notes |
|---|---------|-------|
| N31 | **pgvector upgrade for RAG** | Replace TF-IDF with `text-embedding-3-large` + pgvector; requires Postgres with pgvector extension |
| N32 | **10-Agent Research Swarm** | `asyncio.gather` 10 parallel agents with Redis shared context; orchestrator → synthesis |
| N33 | **Kimi K2.6 Swarm integration** | 300 parallel sub-agents for extreme-depth research |
| N34 | **OSINT toolkit integration** | Sherlock (400+ platforms), Holehe (email→accounts), theHarvester, GHunt, PhoneInfoga |
| N35 | **Document metadata extraction** | FOCA/Metagoofil — extract usernames, server paths from public PDFs |
| N36 | **Reverse WHOIS + subdomain enumeration** | ViewDNS, crt.sh, Amass, Subfinder integration |
| N37 | **FAA Aircraft + USCG Vessel registry** | Asset tracking for high-net-worth individuals |
| N38 | **Real estate lookup** | County assessor record search |

---

## 4) ❌ FUTURE PRODUCTS — Not started, separate sprints

### Jarvis Nexus Dashboard (`Jarvis Nexus Dashboard UI Spec (2).docx`)
A **separate product** — "single pane of glass" executive operating system.  
Sits on top of: LangGraph exec offices + Postgres + Qdrant + Neo4j + PostHog + Metabase + NATS.

**Estimated build: 6 weeks (per spec's build order)**

| Week | Build |
|------|-------|
| 1 | Top bar, ScopeSelector, FilterBar, KpiCard + KpiStrip, portfolio Overview Band A |
| 2 | Real KPI bundle from Postgres/ClickHouse materialized views. Businesses + Departments snapshot |
| 3 | Recommendations + Concerns feeds. Approval queue v1 |
| 4 | Business detail, Department detail, Agent grid + detail |
| 5 | Tech & Systems tab + Operations log drawer + Command Palette (⌘K) |
| 6 | Saved Views, date ranges, exports, polish |

**Key components needed:**
- 6 top-level tabs: Overview · Businesses · Departments · Agents & Workforce · Tech & Systems · Approvals
- KPI bundles: Business (MRR, ARR, churn, retention, LTV/CAC), Department, Agent, System, Portfolio rollup
- Recommendation engine (AI-generated, ranked by `est_impact * confidence / effort_weight`)
- Approval center with risk score, counterfactual, Approve/Deny/Counter-propose
- Unified Concerns feed (incidents + agent failures + KPI drifts + cost anomalies)
- Operations log (NATS events tail — every run, deploy, approval, config change)
- Command Palette (⌘K) — fuzzy search across all entities + actions

**Status: 0% — spec received, not started**

---

### AI Agent Team (James 22 Jun 10:43)
A team of AI agents to manage go-to-market across all products:
- B2B outreach + response agent
- B2C outreach + response agent
- Founder mode agent (Claude)
- GTM agents per product launch
- Agents with different skills per vertical

**Status: 0% — concept discussed, not started**

---

### Centralized Management Suite (James 22 Jun 10:43)
A single dashboard to manage all software, websites, and social media accounts:
- View + control all platforms in one place
- Integrate all SaaS products built
- Cross-platform updates and workflows
- Social media scheduling + analytics unified

**Status: 0% — concept discussed, not started**

---

## 5) Credentials Pending (need from James or team)

| Key | Purpose | Status |
|-----|---------|--------|
| `DIGEST_RECIPIENT_EMAIL` | Daily email digest — tracking alerts | ⏸️ Add to `.env` |
| `DIGEST_RECIPIENT_PHONE` | Daily SMS digest — Twilio | ⏸️ Add to `.env` |
| `CA_SOS_API_KEY` | California Secretary of State registry | ⏸️ James to provide (`calicodev.sos.ca.gov`) |
| `COBALT_API_KEY` | Cobalt Intelligence data | ⏸️ James to provide |
| `OIDC_GOOGLE_SSO` | Google SSO login | ⏸️ James to provide |
| `APOLLO_API_KEY` | ✅ Added 22 Jun — org enrichment live | Paid plan needed for people search |
| `FINNHUB_API_KEY` | Real-time financial data | ⏸️ Register at finnhub.io (free) |
| `FMP_API_KEY` | Financial statements | ⏸️ Register at financialmodelingprep.com (free) |
| `ALPHA_VANTAGE_KEY` | OHLCV + technicals | ⏸️ Register at alphavantage.co (free) |
| `FRED_API_KEY` | Macro data | ⏸️ Register at fred.stlouisfed.org (free) |
| `NEWSAPI_KEY` | Breaking news | ⏸️ Register at newsapi.org (free) |
| `GUARDIAN_API_KEY` | Guardian news | ⏸️ Register at open-platform.theguardian.com (free) |
| `NYT_API_KEY` | NYT archive | ⏸️ Register at developer.nytimes.com (free) |
| `UK_COMPANIES_HOUSE_KEY` | UK company data | ⏸️ Register at developer.company-information.service.gov.uk (free) |

**Already live:** OPENAI_API_KEY · ANTHROPIC_API_KEY · APIFY_API_TOKEN ($500 plan) · All federal connector keys (SEC, FEC, LDA, USASpending, FARA, CourtListener, OFAC, BEA)

---

## 6) PM2 Cron — Setup Pending

```bash
# Add to PM2 ecosystem config for daily digest at 6 AM UTC:
{
  "name": "daily-digest",
  "script": "curl -s -X POST http://localhost:3001/tracking/digest/run",
  "cron_restart": "0 6 * * *",
  "autorestart": false
}
```

**Status:** ⏸️ Not set up

---

## 7) Recommended Build Order — 23 Jun onwards

### This week (highest James impact):

1. **Financial tab on entity profile** — 20-yr charts, M-Score, Z-Score (needs FINNHUB/FMP keys first)
2. **People & Contacts tab** — Apollo executives + emails (uses existing Apollo connector)
3. **Social Footprint tab** — Apify platform cards + sentiment (uses existing Apify connector)
4. **RAG Chat tab on entity profile** — move floating panel into dedicated tab
5. **Word/Excel/PPT export routes** — `python-docx`/`openpyxl`/`python-pptx` already in deps
6. **API Status Panel** — collapsible per-source health + credits indicator
7. **Date-range filter** on report claims
8. **`/tracking/alerts` page** + API

### Next week:

9. Register + connect FINNHUB, FMP, FRED, NewsAPI, Guardian, UK Companies House
10. Timeline View toggle on reports (Vis.js)
11. Graph View toggle on reports
12. `/intelligence/{id}` dedicated report page
13. Search-within-report with highlight
14. Sankey + Timeline Overlay on compare page

### Sprint 3 (Jarvis Nexus):

15. Start Jarvis Nexus Dashboard — Week 1: Top bar + ScopeSelector + FilterBar + KpiCard + Overview Band A

---

## 8) Progress Summary Table

| Scope | % Done | Notes |
|-------|--------|-------|
| Layer 1 — US federal dossier | **100%** | All connectors live, GPT narrative, 9–12 sections |
| Layer 2 — KPIs / filters / tables | **100%** | Filter bar, labels, CSV, sortable tables |
| v2.0 Tasks (T1–T24) | **100%** | All 24 tasks shipped and E2E tested |
| v2.0 Full Spec (Requirements.docx) | **~40%** | Partial — deep features (financial tabs, exports, OSINT) pending |
| Entity Profile (9-tab spec) | **55%** | 5 of 9 tabs built |
| Intelligence Report view modes | **50%** | 2 of 4 view modes built |
| Export formats | **50%** | PDF+CSV+Graph done; Word/PPT/Excel pending |
| Comparison page | **60%** | 3 of 5 visualisations built |
| RAG Chat quality | **60%** | TF-IDF works; pgvector upgrade pending |
| New data connectors (financial APIs) | **0%** | FINNHUB/FMP/FRED not connected |
| New data connectors (news APIs) | **0%** | NewsAPI/Guardian/NYT not connected |
| Jarvis Nexus Dashboard | **0%** | Spec received, not started |
| AI Agent Team | **0%** | Concept discussed, not started |
| Centralised Management Suite | **0%** | Concept discussed, not started |

---

*23rd June 2026 — Cross-verified against v2.0 Requirements.docx, Jarvis Nexus Dashboard UI Spec (2).docx, James WhatsApp messages, and actual repository code.*
