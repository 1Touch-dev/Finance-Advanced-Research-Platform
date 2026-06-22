# James Requirements — Master Document

**Last updated:** 22 June 2026  
**Purpose:** Single source of truth for everything James has asked for across all conversations, documents, and WhatsApp messages. Covers the Financial Intelligence Platform (this repo) AND future products James mentioned (Jarvis Nexus Dashboard, AI Agent Team, Centralised Management Suite).

**Staging:** http://184.72.123.188:3003 · API :3001 · Admin :3002  
**Repo:** https://github.com/1Touch-dev/Finance-Advanced-Research-Platform  
**Latest handoff:** [22nd_June.md](./22nd_June.md)

---

## 0) James's Three Products (22 Jun clarification)

James clarified on 22 Jun that he has been thinking about two different things and mixed them up:

| Product | What it is | Status |
|---------|-----------|--------|
| **1. Financial Intelligence Platform** | This repo — entity dossiers, graph, SEC/FEC/LDA, Apify enrichment | ✅ Live (Layer 1 v1.2) |
| **2. Jarvis Nexus Dashboard** | Executive operating system — KPIs, agents, businesses, approvals, costs | 📄 Spec written (Jarvis Nexus Dashboard UI Spec.docx) |
| **3. AI Agent Team + Central Suite** | Team of agents for GTM, B2B/B2C outreach, + central platform dashboard | 💬 Discussed 22 Jun — new requirement |

This document covers all three. KPIs James mentioned (22 Jun, 10:38) refer to the **Jarvis Nexus Dashboard**, not the Financial Intelligence Platform.

---

## 1) Financial Intelligence Platform — All Requirements

### 1.1 What is live now (Layer 1 v1.2 — 22 Jun)

| # | Feature | Status |
|---|---------|--------|
| 1 | 9–12 section intelligence dossier (SEC, FEC, FARA, USASpending, LDA, OFAC, Courts, Wikipedia, investors) | ✅ Live |
| 2 | Two-sided lobbying disclosure — `[CLIENT SIDE]` + `[REGISTRANT SIDE]` | ✅ Live |
| 3 | Embedded Cytoscape relationship graph on dossier page | ✅ Live |
| 4 | Graph node click → pre-fill new investigation | ✅ Live |
| 5 | Apify connector — Google News (81 articles/query), LinkedIn, PitchBook | ✅ Code live; news working |
| 6 | §6 People & Education (LinkedIn), §8 PitchBook, §9 News & Media | ✅ Code; LinkedIn/PitchBook needs actor permission |
| 7 | GPT-4o deep narrative (5-section format) | ✅ Live |
| 8 | PayPal Mafia + Thiel/Defense demo seeds | ✅ Live |
| 9 | US State Registry (51 jurisdictions) | ✅ Live |
| 10 | BEA Economics page | ✅ Live |
| 11 | LDA migrated to lda.gov | ✅ Live |

### 1.2 James's 18 Jun Layer 2 asks — status

| # | James said | Status | % |
|---|-----------|--------|---|
| 1 | Both sides on all factors (lobbying, contracts) | 🟡 Lobbying done; contracts/FEC pending | 75% |
| 2 | Relationship map / visualizers on dossier | ✅ Cytoscape embedded | 90% |
| 3 | Click any entity → profile + relationships | 🟡 Graph nodes work; claim text not clickable yet | 40% |
| 4 | LinkedIn / colleges / related parties | 🟡 Code ready; needs actor permission approval | 50% |
| 5 | PitchBook / investors | 🟡 Code ready; needs actor permission approval | 50% |
| 6 | News / articles / media | ✅ Google News live (47–81 articles per query) | 80% |
| 7 | Person timeline (career + news chronological) | 🔲 Not built | 10% |
| 8 | Key people → auto-expand network | 🔲 Not built | 20% |

### 1.3 James's 19–20 Jun asks

| # | James said | Status |
|---|-----------|--------|
| 9 | Browser agents for Argentina + uncovered jurisdictions | 🔲 Not built — highest priority |
| 10 | Use both connectors AND browser for deeper research (holdings, vehicles, financials) | 🔲 Not built |
| 11 | Deep research on public + private company financials via browser | 🔲 Not built |
| 12 | Follow-up research when new decision/report surfaces | 🔲 Not built |

### 1.4 James's 22 Jun asks (today — WhatsApp 10:38)

| # | James said | Interpretation | Status |
|---|-----------|----------------|--------|
| 13 | "Missing all insights, and KPIs, filters, labels, categories, more tables on all projects" | Add KPI metrics, filter bar, labels/tags, category breakdown, more data tables throughout the platform | 🔲 New requirement |
| 14 | Sent KPIs doc (Enterprise Intelligence Platform v2.0 Requirements.docx) | Full v2.0 feature set — see §1.5 below | 🔲 New |

### 1.5 Enterprise Intelligence Platform v2.0 Requirements (doc sent 22 Jun)

James sent the full v2.0 requirements document. Key additions on top of what's live:

**Feature Block A — Apollo Email Intelligence Pipeline**
- Use Apollo API to find all executives, directors, employees of any company
- Endpoints: `POST /api/v1/mixed_people/api_search` (free), `POST /api/v1/people/match` (email enrichment, 1 credit), `POST /api/v1/organizations/enrich`
- Downstream intel: reverse WHOIS by email, HIBP breach check, Holehe account finder, predict employee emails by pattern
- New route: `POST /intelligence/apollo?domain={domain}&entity_id={id}`
- New UI: "People & Contacts" tab on entity profile
- Free tier: 50 enrichments/month, 250 people searches/month

**Feature Block B — Apify Social Media Intelligence**
- Twitter/X timeline scraper (`apify~twitter-scraper`)
- LinkedIn profile + recent posts (already wired for education; expand to posts)
- Instagram posts + geotags (`apify~instagram-scraper`)
- YouTube channel search — interviews, speeches (`apify~youtube-scraper`)
- Cross-platform username finder (`apify~social-media-finder`)
- All-platform posts by hashtag/username
- New route: `POST /intelligence/social?entity_id={id}&handles={handles}`
- New UI: "Social Footprint" section with sentiment timeline chart

**Feature Block C — Per-Entity RAG Chat**
- Build vector knowledge base per entity from all collected evidence
- Stack: `text-embedding-3-large` → `pgvector` → Claude `claude-3-5-sonnet`
- Answer Q&A with citations tagged `[DOCUMENTED]` / `[REPORTED]` / `[ANALYTICAL]`
- Compare two entities in dual-pane chat
- New routes: `POST /entities/{id}/chat`, `POST /entities/compare-chat`, `POST /entities/{id}/generate-pdf-report`
- New UI: Chat sidebar on entity profile + Compare button

**Feature Block D — Comparison & Multi-Entity Analysis**
- Side-by-side comparison up to 5 entities
- Modes: Financial KPIs, Government Exposure, Legal Risk Matrix, Board Overlap, Co-investment Network, Social Sentiment
- Visualisations: Radar chart, grouped bar, timeline overlay, network overlap (Sigma.js), Sankey (D3)
- Maths: Jaccard board overlap score, co-investment index, regulatory cosine similarity, network centrality delta
- New route: `POST /compare`

**Feature Block E — Tracking Dashboard & Daily Digest**
- Monitor any entity; daily digest of new filings, contracts, lobbying, court cases, social mentions
- Digest job at 6:00 AM UTC — checks SEC, USASpending, LDA, CourtListener, OpenSanctions, Apify social
- Delivery: email (SendGrid), SMS (Twilio), in-app alert inbox
- New routes: `POST /tracking/entities`, `GET /tracking/digest`, `GET /tracking/alerts`
- New UI: Tracking dashboard card grid + alert inbox + "Add to Tracking" button

**Feature Block F — Private Company Intelligence**
- Full profiles for private companies using free public sources
- Sources: OpenCorporates, GLEIF LEI, FinCEN BOI, US State Registry (live), SEC Form D (live), Crunchbase free tier, IRS 990, UK Companies House
- Apify actor for global registry search (40+ countries) — covers Argentina, UK, EU etc.
- Report sections: Identity, Beneficial Ownership, Funding History, Officers & Directors, Related Entities, Financial Estimates

**Missing from v1.2 that v2.0 adds (James's 22 Jun "missing" comment):**
- KPI strips / metrics on every page and report
- Universal filter bar (scope, time lens, tags, status, department)
- Labels and categories on entities, reports, contracts, lobbying filings
- More data tables throughout — sortable, exportable CSV
- Comparison tables across entities
- Per-entity tracking with alert badges
- Insights panel (AI-generated recommendations per report)

### 1.6 Full pending build stack — Financial Intelligence Platform

**P0 — This week**
| # | Task |
|---|------|
| P0.1 | Approve Apify LinkedIn + PitchBook actor permissions (link sent — one-time) |
| P0.2 | Fix click-to-investigate in report claim text (wire EntityChip, auto-generate) |
| P0.3 | Contracts two-sided disclosure (agency + contractor) |

**P1 — Browser research layer (James 19–20 Jun)**
| # | Task |
|---|------|
| P1.1 | Build `browser_research_agent.py` — browse public registries, gov sites, courts, news for uncovered jurisdictions |
| P1.2 | Wire into `generate_intelligence_report` as fallback/enrichment |
| P1.3 | Argentina spike: Aeropuertos Argentina 2000 or Mercado Libre on staging |
| P1.4 | Deep-dive mode: holding companies, vehicle structures, articles, financials |

**P2 — KPIs, filters, tables (James 22 Jun)**
| # | Task |
|---|------|
| P2.1 | KPI metric strip on intelligence report (contracts value, lobbying spend, court cases, news volume) |
| P2.2 | Universal filter bar — entity type, time range, data sources, confidence tags |
| P2.3 | Labels / categories on entities and reports |
| P2.4 | More data tables — sortable, CSV export on all sections |
| P2.5 | Insights panel per report (AI recommendations) |

**P3 — Apify completion**
| # | Task |
|---|------|
| P3.1 | Company employees scraper → key people on org reports |
| P3.2 | Key people auto-expand → graph edges |
| P3.3 | Twitter/X + Instagram + YouTube social scraping (v2.0 Block B) |
| P3.4 | Cross-platform username finder |

**P4 — v2.0 new features**
| # | Task |
|---|------|
| P4.1 | Apollo email pipeline (`POST /intelligence/apollo`) |
| P4.2 | Per-entity RAG chat with pgvector + Claude |
| P4.3 | Comparison page (up to 5 entities, radar/Sankey/bar) |
| P4.4 | Tracking dashboard + daily digest job |
| P4.5 | Private company intelligence (OpenCorporates, GLEIF, FinCEN BOI) |
| P4.6 | PDF export from RAG chat answers |

**P5 — Timeline + network dossier**
| # | Task |
|---|------|
| P5.1 | Person timeline UI (career + filings + news chronologically) |
| P5.2 | Polished `/entities/[id]` profile page |
| P5.3 | Full PayPal Mafia network dossier (one linked report) |

**Deferred (waiting on James)**
| Item | Status |
|------|--------|
| CA SOS API key | ⏸️ Waiting |
| Cobalt Intelligence | ⏸️ Waiting |
| OIDC Google SSO | ⏸️ Waiting |
| KPIs doc for Financial Intelligence Platform | ⏸️ James hasn't sent yet (22 Jun 10:22) |

---

## 2) Jarvis Nexus Dashboard — All Requirements

**Source:** Jarvis Nexus Dashboard UI Spec (2).docx — sent by James

### 2.1 What it is

Executive operating system — the "single pane of glass" for the entire portfolio. Sits on top of: LangGraph agents + Postgres + Qdrant + Neo4j + PostHog + Metabase + NATS.

### 2.2 Information architecture

Five scopes switchable from a top-bar selector: Portfolio · Business · Department · Agent/Workforce · System/Tech  
Three time lenses always present: Today / 7-day / 30-day + custom range  
Six left-rail tabs: Overview · Businesses · Departments · Agents & Workforce · Tech & Systems · Approvals  
Global command palette (⌘K) — jumps to any business, agent, KPI, or action

### 2.3 Data model

**Core entities:** `business`, `department`, `agent`, `workforce_unit`, `service`, `integration`, `kpi_def`, `strategy`, `experiment`, `task`, `approval`, `incident`, `recommendation`

**Fact tables (ClickHouse):** `kpi_value`, `agent_run`, `service_event`, `cost_event`, `revenue_event`, `deploy_event`

**Business bundle per business:** mrr, arr, new_mrr, churn_mrr, net_new_mrr, customers, signups, activation_rate, retention_d7/d30, gross_margin, cac, ltv, ltv_cac, runway_months, traffic_sessions, conv_rate, north_star_value/delta

**Agent bundle:** runs, success_rate, p50/p95_latency_ms, tokens_total, cost_usd, retries, error_rate, approval_required_count, downstream_kpi_lift_pct

**Portfolio rollup:** total_mrr, mrr_growth_pct, total_costs, gross_profit, burn, runway_months, active_experiments, win_rate, decisions_pending, ai_cost_pct_of_revenue

### 2.4 Universal filter bar

Single `FilterBar` component, URL-synced:  
`?scope=business&id=acme&lens=7d&dept=growth&tag=worldcup`  
Filters: Scope · Entity picker (cascading) · Time lens · Compare (prev period / YoY / target) · Tags (free-form) · Status (healthy/watch/at-risk/critical) · Department · Owner/agent · Confidence threshold

### 2.5 Page specs

**Overview tab** — 6 bands:
- Band A: Headline KPI strip (6 cards — MRR, Net New MRR, Burn, Runway, Active Experiments, Win Rate). Each card: value + sparkline + delta + status dot + target progress
- Band B: AI Recommendations (left) + Concerns/errors (right) — infinite scroll
- Band C: Top 5 pending approvals (horizontal scroller, inline approve/deny)
- Band D: Business snapshot grid (status, MRR, north-star, open items, approvals)
- Band E: Departments snapshot grid (throughput, on-time %, KPI delta, blockers)
- Band F: Tech/systems heatmap (services × time, colored by error rate)

**Businesses tab** — Master sortable table. Click row → Business Detail with sub-tabs: Overview · Departments · Agents · Strategies (Kanban: Proposed → Approved → Running → Measuring → Won/Lost/Killed) · Stack · Concerns · Approvals

**Departments tab** — Sortable table + Department Detail: Pulse · Tasks · Agents · Playbooks · Concerns

**Agents & Workforce tab** — Agent cards (runs, success %, latency, cost, KPI lift) + Workforce capacity chart

**Tech & Systems tab** — Services status grid + APIs/models table + Deploy timeline

**Approvals tab** — Decision queue with risk score, payload, approve/deny/request-info. SLA timer on each item.

### 2.6 Concerns & error surfacing

Every error/concern tagged by: source · severity · scope · business · timestamp  
Surfaced in: Overview Band B + Businesses tab + Agent detail + global notification drawer  
Concern lifecycle: open → acknowledged → in progress → resolved

### 2.7 Build status

| Layer | Status |
|-------|--------|
| Data model design | ✅ Spec complete (Jarvis Nexus doc) |
| Postgres schema | 🔲 Not started |
| ClickHouse setup | 🔲 Not started |
| API routes | 🔲 Not started |
| Frontend shell | 🔲 Not started |
| KPI tracking + digests | 🔲 Not started |

**This is a separate product from the Financial Intelligence Platform.** Build sequence: Financial Intelligence Platform v2.0 first → Jarvis Nexus Dashboard second (shares some concepts like agent tracking).

---

## 3) AI Agent Team — Requirements (James 22 Jun 10:43)

**James said:**  
> "At some point I want you to think about two things. 1. Team of agents to manage: B2B outreach and response, B2C outreach and response, Founder mode in Claude, Different Skills, Agents to follow go to market, in order to help release all the SaaS we build."

### 3.1 What James wants

A coordinated team of AI agents that handles the full go-to-market and customer operation lifecycle for each SaaS product James builds and releases.

### 3.2 Agent roster (James's spec)

| Agent | Role | Skills needed |
|-------|------|---------------|
| **B2B Outreach Agent** | Find prospects, send personalised outreach, track responses, follow up | Apollo email pipeline, LinkedIn scraping, CRM sync (Twenty) |
| **B2C Outreach Agent** | Social media engagement, DMs, responses, community management | Twitter/X, Instagram, Reddit actors via Apify |
| **Founder Mode Agent** | Acts in Claude "founder mode" — strategic decisions, positioning, fundraising prep | Claude claude-3-5-sonnet, long-context, custom persona |
| **Skills Agents** | Specialist agents per skill: copywriting, SEO, content, financial modelling | Existing Skills Gateway + new Anthropic adapters |
| **GTM Agents** | Execute go-to-market strategy: launch sequences, pricing experiments, A/B tests | LangGraph workflows, strategy runner |
| **Release Manager Agent** | Coordinate SaaS release: checklist, announcements, landing pages, Product Hunt | Browser automation, Apify, email |

### 3.3 Infrastructure needed

- **Agent orchestrator** — LangGraph or similar, manages agent team coordination
- **Task queue** — Bull/Redis (already in `apps/worker`)
- **CRM integration** — Twenty CRM (client already exists at `apps/api/app/services/twenty_client.py`)
- **Comms integration** — SendGrid (email), Twilio (SMS), WhatsApp Business API
- **Approval workflow** — all outbound agent actions require human approval before send (Jarvis Nexus Approvals tab)
- **Memory** — per-agent context store (pgvector or Redis)
- **Toolset per agent** — Apollo (people search), Apify (social), OpenAI/Claude (reasoning), SendGrid (send)

### 3.4 Build status

| Layer | Status |
|-------|--------|
| Skills Gateway (run_skill, skills registry) | ✅ Live |
| Twenty CRM client | ✅ Code exists |
| SendGrid client | ✅ Code exists |
| Apollo email pipeline | 🔲 Planned in v2.0 Block A |
| Apify social scraping | 🔲 Planned in v2.0 Block B |
| LangGraph agent orchestrator | 🔲 Not started |
| B2B/B2C outreach agents | 🔲 Not started |
| GTM workflow agents | 🔲 Not started |
| Approval workflow (human-in-loop) | 🔲 Not started |

**Dependency:** Apollo email pipeline (v2.0 Block A) + Apify social (v2.0 Block B) must be built first.

---

## 4) Centralised Management Suite — Requirements (James 22 Jun 10:43)

**James said:**  
> "Having a centralized system to manage all of our software, websites, social medias, and integrate all of them into one central suite, where we can view, and integrate, for updates and continue working through all platforms. Centralizing everything."

### 4.1 What James wants

A single dashboard where James can see and control every business, product, website, social media account, and agent — all in one place with live data, actions, and integrations.

### 4.2 Scope of "everything"

| Category | Examples | Integration method |
|----------|----------|--------------------|
| **SaaS products** | Each built product — health, status, MRR, users | Internal API |
| **Websites** | Landing pages, SEO traffic, uptime | PostHog analytics, Uptime Robot |
| **Social media** | Twitter/X, LinkedIn, Instagram, YouTube, Reddit | Apify social actors |
| **CRM / outreach** | Contacts, pipelines, emails sent/received | Twenty CRM, Apollo |
| **Finance** | MRR, burn, invoices, Stripe/Paddle revenue | Stripe API, accounting |
| **AI agents** | Status, runs, cost, output quality | Agent tracking (Jarvis Nexus) |
| **Code repos** | GitHub status, open PRs, failing CI | GitHub API |
| **Communications** | WhatsApp business, email threads | WhatsApp Business API, Gmail |
| **Infra / tech** | Service uptime, API errors, DB health | Prometheus, Grafana, PM2 |

### 4.3 Relationship to Jarvis Nexus

This IS the Jarvis Nexus Dashboard extended across all products (not just one). The Jarvis spec covers the operating layer; this requirement adds the multi-product portfolio view at the top.

Jarvis "Portfolio" scope = this requirement.  
Both products feed the same top-bar Portfolio KPI strip.

### 4.4 Build status

| Layer | Status |
|-------|--------|
| Portfolio scope design | ✅ In Jarvis Nexus spec |
| Integrations (GitHub, Stripe, PostHog, etc.) | 🔲 Not started |
| Social media unified feed | 🔲 Not started |
| Multi-product MRR rollup | 🔲 Not started |
| Central notifications inbox | 🔲 Not started |

---

## 5) Build priority across all three products

James's stated priority is **Financial Intelligence Platform first** (22 Jun — he clarified he is talking about this, not the agent suite yet). The agent team and central suite are "at some point" asks.

### Immediate (this week — Financial Intelligence Platform)

1. Approve Apify actor permissions (LinkedIn, PitchBook) — 5 min action by James
2. Fix click-to-investigate in report text
3. Contracts two-sided disclosure
4. Start browser research agent (Argentina fallback)

### Short-term (this month — Financial Intelligence Platform v2.0)

5. KPIs, filters, labels, tables on intelligence reports (James 22 Jun "missing" ask)
6. Apollo email pipeline (Block A)
7. Apify social footprint (Block B) — expands existing Apify connector
8. Per-entity RAG chat (Block C)
9. Tracking dashboard + daily digest (Block E)
10. Private company intelligence (Block F) — covers Argentina and international

### Medium-term (next month — Financial Intelligence v2.0 complete + Jarvis begins)

11. Comparison page (Block D)
12. PDF export
13. PayPal Mafia network dossier
14. Start Jarvis Nexus data model + API routes

### Later — Agent Team + Central Suite

15. Apollo + Apify social wired to agent team
16. LangGraph agent orchestrator
17. B2B/B2C outreach agents
18. GTM + release agents
19. Portfolio rollup + central integrations

---

## 6) Pending from James (actions James needs to take)

| # | Action | Priority |
|---|--------|----------|
| J1 | **Approve Apify actor permissions** (LinkedIn + PitchBook) — link: https://console.apify.com/actors/lsfMbqR3SfAud3Cx9?approvePermissions=true | 🔴 Immediate |
| J2 | **Send KPIs doc** for Financial Intelligence Platform (said he hasn't sent it yet — 22 Jun 10:22) | 🟡 This week |
| J3 | CA SOS API key | ⏸️ Deferred |
| J4 | Cobalt Intelligence approval | ⏸️ Deferred |
| J5 | OIDC Google SSO credentials | ⏸️ Deferred |
| J6 | Confirm PayPal Mafia as Layer 2 sign-off demo | 🟡 This week |
| J7 | Apify scraping policy sign-off (LinkedIn + PitchBook public pages) | 🟡 This week |

---

## 7) KPIs — pending James's doc

James mentioned KPIs on 22 Jun but confirmed he hasn't sent the KPIs doc for the Financial Intelligence Platform yet. Once received, add here.

**What we know KPIs will likely cover (from v2.0 doc context):**
- Per-entity: contracts value (USD), lobbying spend (USD/year), court case count, social follower count, news volume (articles/month), investor count, employee count, revenue/funding (from PitchBook/Apollo)
- Report quality: data sources active, confidence distribution (DOCUMENTED vs REPORTED vs ANALYTICAL %)
- Platform: reports generated/day, entities in graph, relationships mapped, data freshness

---

*Document maintained by: Abhishek Kulkarni*  
*Covers: WhatsApp 18–22 Jun · Enterprise Intelligence Platform v2.0 Requirements.docx · Jarvis Nexus Dashboard UI Spec (2).docx · 22nd_June.md cross-verification*
