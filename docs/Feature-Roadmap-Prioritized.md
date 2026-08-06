# Feature Roadmap — 72 Missing Features

**Prioritized by value. Frontend/Backend split for sprint planning.**

---

## Quick Stats

| Band | Total | Frontend | Backend | Full-stack |
|------|-------|----------|---------|------------|
| A — Blockers (DO FIRST) | 14 | 3 | 8 | 3 |
| B — Differentiators | 17 | 1 | 12 | 4 |
| C — Table Stakes | 25 | 4 | 13 | 8 |
| D — Segment Unlocks | 11 | 0 | 3 | 8 |
| E — Low Priority | 5 | 4 | 0 | 1 |
| **Total** | **72** | **12** | **36** | **24** |

---

## Legend

- 🟢 **Low effort** — days
- 🟡 **Medium effort** — weeks
- 🔴 **High effort** — months
- `FE` — Frontend only
- `BE` — Backend only
- `FS` — Full-stack (both)

---

## Band A — Conversion & Retention Blockers (14)

> **Priority: HIGHEST. Do all of these first.**
> Mostly cheap. Addresses documented churn drivers.

### Backend (8)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 3 | Reachable human support + escalation path | 🟢 | Policy + ticketing system integration |
| 5 | Internal linking across generated pages | 🟢 | SEO — link orphan pages to hubs |
| 6 | Sitemaps and crawl management | 🟢 | SEO — XML sitemap generation |
| 7 | Freshness engine | 🟡 | Scheduled re-generation of stale pages |
| 9 | Compliance guardrails on generated content | 🟢 | No projections, no recommendations, disclaimers |
| 11 | AI-answer visibility tracking | 🟢 | Track Google AI Overview citations |
| 13 | Portable corpora — export, API, MCP | 🟢 | Let users export their data |
| 14 | 13F honesty layer | 🟢 | Flag that 13F data is 45-day stale |

### Frontend (3)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 1 | Published pricing (all tiers + limits) | 🟢 | Static pricing page |
| 2 | Renewal notice + one-click cancel | 🟢 | Billing UI, no dark patterns |
| 12 | Browser extension | 🟢 | Overlay provenance on EDGAR/news sites |

### Full-stack (3)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 4 | Honest status page with incident history | 🟢 | BE: incident logging / FE: public status UI |
| 8 | Editorial workflow for AI content | 🟢 | BE: approval queue / FE: review interface |
| 10 | Experiment framework for templates | 🟡 | BE: A/B assignment / FE: variant rendering |

---

## Band B — Differentiation Multipliers (17)

> **Priority: HIGH. This is where pricing power comes from.**
> More expensive, but leverages Phase 2 infrastructure.

### Backend (12)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 16 | Company-specific ontology + KPI schema | 🔴 | Per-company RAG understanding |
| 18 | Multi-entity and thematic corpora | 🟡 | Sector/supply-chain queries |
| 19 | Point-in-time rolling consensus | 🔴 | Consensus as-it-was, not revised |
| 20 | Consensus revision history + momentum | 🟡 | Falls out of #19 |
| 21 | Estimate dispersion | 🟢 | Falls out of #19 |
| 22 | Guidance vs actual tracking | 🟡 | Management credibility scoring |
| 23 | Earnings surprise history | 🟢 | With correct as-of consensus |
| 24 | Per-analyst accuracy scoring | 🟡 | Apply M15 calibration to analysts |
| 25 | Whisper + buy-side vs sell-side split | 🔴 | Data acquisition problem |
| 27 | Implied volatility surface (delayed EOD) | 🟡 | No OPRA license needed |
| 28 | Unusual volume screening (delayed) | 🟡 | Honest delayed > wrong live |
| 31 | Docket-to-disclosure reconciliation | 🟡 | **THE KEY L-SERIES FEATURE** — flag lawsuit vs 10-K divergence |

### Frontend (1)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 29 | Public analyst profile pages | 🟢 | Display track records + calibration |

### Full-stack (4)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 15 | Filing redline + table-to-Excel + search | 🟡 | BE: diff engine / FE: redline viewer |
| 17 | Private document ingestion | 🟡 | BE: ingestion pipeline / FE: upload UI |
| 26 | Custom formula + expression charting | 🟡 | BE: expression parser / FE: formula builder |
| 30 | Model + idea leaderboards | 🟡 | BE: Brier scoring / FE: leaderboard UI |

---

## Band C — Table Stakes (25)

> **Priority: MEDIUM. Absence loses deals in first 10 minutes.**
> Nothing here wins deals, but missing them loses them.

### Backend (13)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 34 | Global equity coverage | 🔴 | EODHD ($99/mo) + Brazil CVM |
| 35 | Forward multiples on consensus | 🟢 | Trivial once #19 exists |
| 36 | Analyst rating changes + PT history | 🟢 | With as-of dates |
| 42 | Cost basis and tax lots | 🟡 | Portfolio data model |
| 43 | Brokerage sync | 🟡 | Third-party aggregator (buy not build) |
| 44 | Benchmark attribution | 🟡 | Portfolio vs benchmark breakdown |
| 45 | Risk metrics (VaR, beta, drawdown) | 🟢 | Wire up existing M8 models |
| 49 | Team permission roles | 🟡 | RBAC system |
| 50 | Legal proceedings extraction | 🟡 | Item 103 + contingency notes → structured |
| 51 | Litigation reserve tracking | 🟡 | Feeds M11 Sloan accruals |
| 52 | Enforcement action event studies | 🟢 | M2 with SEC/DOJ/OFAC events |
| 53 | Docket velocity indicator | 🟢 | New filings before disclosure |
| 54 | Exposure normalized (revenue/equity/cash) | 🟢 | Makes litigation screenable |
| 55 | Point-in-time litigation panel | 🟢 | C2 applied to legal exposure |

### Frontend (4)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 33 | Mobile PWA with working alerts | 🟡 | Responsive + push notifications |
| 38 | Multi-security overlay + normalization | 🟢 | Comparison charting |
| 39 | Drawing tools with persistence | 🟡 | Chart annotations |
| 40 | Chart templates (one-click apply) | 🟢 | Save/load chart configs |

### Full-stack (8)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 32 | Portfolio tracking | 🟡 | BE: holdings model / FE: portfolio UI |
| 37 | Estimate revision screener | 🟡 | BE: filter logic / FE: screener UI |
| 41 | Position-level P&L | 🟢 | BE: calculations / FE: display |
| 46 | Shared watchlists + dashboards | 🟢 | BE: sharing model / FE: share UI |
| 47 | Comments + annotations | 🟡 | BE: comment storage / FE: annotation UI |
| 48 | Shared workspaces | 🟡 | BE: workspace model / FE: workspace UI |
| 56 | Litigation fields in screener + alerts | 🟢 | BE: filter fields / FE: UI controls |

---

## Band D — Segment Unlocks (11)

> **Priority: CONDITIONAL. Worth $0 or 10x depending on segment decision.**
> Only build if targeting advisors or research teams.

### Backend (3)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 58 | Rebalancing engine | 🔴 | Compliance surface attached |
| 61 | Multi-account households | 🔴 | Deep data model change — decide before Phase 3 |
| 64 | Team activity audit log | 🟢 | Leverages G13 replay log |

### Full-stack (8)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 57 | Factor exposure decomposition | 🟡 | M13 hierarchical models |
| 59 | Model portfolios | 🟡 | Advisor workflows |
| 60 | Client reporting | 🟡 | Reuses V6 report builder |
| 62 | Branded proposal export | 🟡 | White-label outputs |
| 63 | Notebook + memo co-authoring | 🔴 | Extend V4 finding object |
| 65 | Curated newsletters | 🟢 | Content marketing channel |
| 66 | Education + tutorials library | 🟡 | Reduces support load |
| 67 | Earnings-day live blog | 🟡 | Ongoing editorial cost |

---

## Band E — Low Priority (5)

> **Priority: LOWEST. Build only when forced.**

### Frontend (4)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 68 | Native push notifications | 🟡 | Requires native app |
| 69 | Offline caching | 🟢 | Users are always online |
| 70 | Biometric login | 🟢 | Nice, not critical |
| 71 | Home screen widgets | 🟡 | Requires native app first |

### Full-stack (1)

| # | Feature | Effort | Notes |
|---|---------|--------|-------|
| 72 | User-generated screen sharing | 🟡 | Moderation nightmare |

---

## Deliberately Declined (13 items, not in the 72)

Do not re-add these:

- Real-time options flow (OPRA license)
- Premium/exchange tagging
- Multi-leg tagging
- Flow sentiment
- Greeks filters
- Gamma exposure aggregates
- Dark pool attribution
- Expert-call transcripts
- Channel-check networks
- Broker research aggregation
- Licensed voice-of-customer
- Investor podcasts
- Group chat

---

## Recommended Sprint Sequence

### Sprint 1-2: Band A Backend (8 items)
All low effort. Stops the bleeding.

### Sprint 2-3: Band A Frontend + Full-stack (6 items)
Complete the churn-stopper set.

### Sprint 4-6: Band B Backend (12 items)
Start with #31 (docket-disclosure) + its L-series dependencies (#50-55 from Band C).

### Sprint 7-8: Band B Full-stack (4 items)
Filing redline (#15) is the competitive gap to close.

### Sprint 9+: Band C as needed
Fill table-stakes gaps based on user feedback.

### Band D: Only after segment decision
Do not speculatively build.

### Band E: Never proactively
Build only if something forces it.

---

## Infrastructure Already Built (Phase 2)

These enable cheaper implementation of the above:

| Component | Enables |
|-----------|---------|
| Metric registry (F7) | #26 custom formulas inherit provenance |
| Bitemporal storage | #19, #20, #55 point-in-time queries |
| Calibration machinery (M15) | #24 analyst scoring, #30 leaderboards |
| Volatility models (M8) | #45 risk metrics |
| Report builder (V6) | #60 client reporting |
| Finding object (V4) | #63 notebook co-authoring |
| Replay log (G13) | #64 audit log |
| Cox hazard (M10) | L-series time-to-resolution |
| Sloan accruals (M11) | #51 litigation reserves |
| Event studies (M2) | #52 enforcement events |
| 48 integrations | SEC, OFAC, SAM.gov ready |
