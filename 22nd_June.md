# 22nd June 2026 — Project Status, James Comms Cross-Verification + Next Steps

**Purpose:** Consolidated handoff as of 22 Jun — all done/pending tasks, honest cross-verification of WhatsApp messages to James (19–22 Jun), updated priority stack including browser research fallback, and full v2.0 requirements from James's docs.

**Prior docs:** [18th_June.md](./18th_June.md) (v1.2 shipped) · [17th_June.md](./17th_June.md) · [README.md](./README.md)  
**Full requirements:** [james_requirements.md](./james_requirements.md) — all James asks in one place

**Staging:** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`  
**Branch:** `feature/us-50-state-registry-api` · **PR #2**  
**Last push:** `d2432f1` — Layer 1 v1.2 (Apify connector, two-sided LDA, graph embed)

**Status:** 🟢 **Apify UNBLOCKED** (22 Jun 10:30 — James topped up) · News ✅ working · LinkedIn ✅ working · PitchBook ⚠️ needs actor permission · Layer 2 ~**45%** · Browser research agent **not built yet** · v2.0 docs received from James

---

## 0) 22 Jun morning update — James conversation + new requirements

**10:20–10:43 AM WhatsApp (22 Jun):**

| Time | Who | Said |
|------|-----|------|
| 10:20 | James | Asked if he'd sent KPIs for financial intelligence |
| 10:21 | James | Clarified he's talking about Financial Intelligence Platform, not agent suite |
| 10:21 | James | "Send me doc, last updated" |
| 10:22 | Abhishek | Confirmed KPIs not received yet |
| 10:25 | Abhishek | Asked James to top up Apify |
| 10:28 | Abhishek | Explained $200 Starter plan cap |
| **10:30** | **James** | **"apify done"** ✅ |
| 10:30 | Abhishek | Confirmed it reflected |
| 10:38 | James | "You get where missing all insights, and KPIs, filters, labels, categories, more tables on all projects correct?" |
| 10:43 | James | Shared two future concepts: (1) AI Agent Team for GTM/outreach (2) Centralised Management Suite |

**Documents received from James (22 Jun):**
- `Enterprise Intelligence Platform v2.0 Requirements.docx` — full v2.0 feature spec (Apollo, Apify social, RAG chat, comparison, tracking, private companies)
- `Jarvis Nexus Dashboard UI Spec (2).docx` — executive operating system spec (KPIs, agents, businesses, approvals, costs dashboard)

**Key clarification:** James was confused between two products. The "KPIs and insights" comment (10:38) refers to the **Financial Intelligence Platform** reports. The Jarvis Nexus doc covers a separate executive dashboard product. Both are documented in [james_requirements.md](./james_requirements.md).

**Apify status after top-up (confirmed working):**
- ✅ Google News: 47–81 articles per query (Palantir, Peter Thiel tested)
- ✅ LinkedIn: Peter Thiel profile data (headline, experience, education)
- ⚠️ PitchBook: `full-permission-actor-not-approved` — needs one-time approval at https://console.apify.com/actors/lsfMbqR3SfAud3Cx9?approvePermissions=true

**Bug fixed (22 Jun):** `apify_connector.py` — `clean=True` (boolean) → `clean="true"` (string) in dataset fetch. Was causing HTTP 400 errors after every successful actor run.

---

## 1) Executive summary — 22 Jun

| Area | Status |
|------|--------|
| **Layer 1 (US federal dossier)** | ✅ ~100% — 9–12 sections, all free connectors, GPT narrative, PayPal Mafia seeds |
| **Layer 1 v1.2 (18 Jun)** | ✅ Shipped — two-sided LDA, Cytoscape embed, Apify connector code |
| **Layer 2 (James 18 Jun asks)** | 🟡 ~45% — see §4 for honest item-by-item |
| **Apify live enrichment** | ✅ **UNBLOCKED** — James topped up 22 Jun 10:30; News + LinkedIn working |
| **PitchBook (Apify)** | ⚠️ `full-permission-actor-not-approved` — one-time approval needed from James |
| **Browser research fallback** | 🔲 **Not built** — promised to James 19–20 Jun; high priority |
| **International (e.g. Argentina)** | 🔲 No connector, no browser agent — registry is US-only (51 jurisdictions) |
| **Click entity in report** | 🟡 **Partial** — graph nodes pre-fill form; claim text names NOT clickable (see §5) |
| **Entity profile page** | 🟡 API exists; `/entities/[id]` is raw JSON only |
| **v2.0 requirements received** | 📄 Enterprise Platform v2.0 doc + Jarvis Nexus UI spec — see [james_requirements.md](./james_requirements.md) |
| **KPIs doc (Platform)** | ⏸️ James said he hasn't sent it yet (22 Jun 10:22) |
| **CA SOS / Cobalt / OIDC** | ⏸️ Deferred |

### Progress percentages (honest — updated 22 Jun)

| Scope | Done | Pending |
|-------|------|---------|
| Layer 1 core dossier (US) | **~95–100%** | Minor polish |
| Layer 2 overall (James full vision) | **~45%** | ~55% |
| Phase 1.2 (two-sided LDA, graph) | **~90%** | Fix click-in-report gap |
| Phase 2.0 (Apify enrichment — News + LinkedIn) | **✅ ~75%** | PitchBook permission + employees scraper |
| Phase 2.4 (browser research — NEW) | **0%** | Full build |
| v2.0 new features (Apollo, RAG chat, social, comparison, tracking) | **0%** | Full build |
| 10-week Layer 2 roadmap | **~30%** | Phases 2.1–2.3 + browser layer + v2.0 features |

---

## 2) James conversation log (19–20 Jun)

### 2.1 Abhishek → James (19 Jun ~12:41 PM) — project status

Sent Layer 1 100% done, Layer 2 ~45%, item-by-item percentages, staging URL, Apify integration complete but credits exhausted.

### 2.2 James replies (19 Jun evening)

> "Can someone buy monthly credits"

> "You have my card right"

> "For; ex: Argentina. Can we have agents browse the public data websites and registry's, and try and find information. Using browser Or perplexity computer (which was how a large part of that report came in order). *for states or countries we don't have ?"

### 2.3 Abhishek replies (19–20 Jun)

- Confirmed browser-based research for countries/states without dedicated connectors
- Explained Perplexity-style approach: public registries, government DBs, court records, procurement portals, news
- Connectors preferred for scale; browser fallback where integrations don't exist
- James confirmed: **"Yeah exactly"**
- James expanded: use **both** connectors AND browser fallback to go deeper — holding companies, vehicle structures, articles, financials (public + private), decision/report follow-up research
- Abhishek: **"Yeah sure"**

### 2.4 Cross-verification verdict (22 Jun)

| What was said to James | Reality in code | Verdict |
|------------------------|-----------------|---------|
| Layer 1 100% done | 9–12 sections, federal sources live | ✅ Accurate |
| Layer 2 ~45% | Honest estimate ~40% | 🟡 Slightly optimistic |
| Two-sided lobbying done | `client_name` + `registrant_name` in `intelligence_service.py` | ✅ Accurate |
| Graph embedded on dossier | `EmbeddedGraph` in `intelligence.js` | ✅ Accurate |
| Click any entity ~80% | Graph nodes pre-fill form only; **claim text names not clickable**; no auto-generate; no link to profile page | ❌ **Overstated** |
| Apify integrated, credits exhausted | `apify_connector.py` wired; still `platform-feature-disabled` 22 Jun | ✅ Accurate |
| LinkedIn/PitchBook/News ~60% | Code yes, **zero live data** until credits | 🟡 Overstated — say "integrated, waiting on credits" |
| Browser agents for Argentina / uncovered jurisdictions | **No code** — only US state Playwright scraper exists for registry | ❌ **Promised, not built** |
| Use both connectors + browser for deeper research | **Not designed or implemented** | ❌ **Promised, not built** |
| James card for Apify top-up | James offered; **top-up not done** as of 22 Jun | 🔲 Pending action |

---

## 3) James requirements — full cross-verification (18 Jun asks + 19–20 Jun expansion)

| # | James requirement | Status | Evidence / gap |
|---|-------------------|--------|----------------|
| 1 | **Both sides** (lobbying, contracts, FEC) | 🟡 **75%** | Lobbying ✅ both `client_name` + `registrant_name`, `[CLIENT SIDE]` / `[REGISTRANT SIDE]` tags. Contracts/FEC still one-sided. |
| 2 | **Relationship map / visualizers** | ✅ **90%** | Cytoscape embedded on `/intelligence`. Missing: export PNG/JSON, auto-expand. |
| 3 | **Click any entity → profile + relationships** | 🟡 **40%** | Graph node click → pre-fills form (user must click Generate). `EntityChip` component exists but **unused** in claim text. `/entities/[id]` = raw JSON. |
| 4 | **LinkedIn / colleges / related parties** | 🟡 **50% code** | §6 People & Education via `apify_connector.py`. Empty until Apify credits. Company employees scraper 🔲. |
| 5 | **PitchBook / investors** | 🟡 **50% code** | §8 wired. Empty until Apify credits. |
| 6 | **News / articles / media** | 🟡 **30%** | §9 Google News wired. YouTube, books, interviews 🔲. |
| 7 | **Person timeline** | 🔲 **10%** | No chronological UI. News list only when Apify active. |
| 8 | **Key people → auto-expand network** | 🔲 **20%** | Graph shows DB edges only. No auto-investigate from narrative names. |
| 9 | **Browser research for uncovered jurisdictions** (Argentina, etc.) | 🔲 **0%** | **New ask 19 Jun.** Promised to James. Not started. |
| 10 | **Dual mode: connectors + browser deep dive** (holdings, vehicles, financials) | 🔲 **0%** | **New ask 20 Jun.** James confirmed. Not started. |
| 11 | **Project plan + timelines** | ✅ **100%** | Sent 18–19 Jun. |
| 12 | **PayPal Mafia network dossier + PDF** | 🔲 **0%** | Individual seeds only. |

---

## 4) What is DONE (do not regress)

### Layer 1 — shipped 16–17 Jun

| # | Item | Status |
|---|------|--------|
| L1.1 | 9-section intelligence report orchestrator | ✅ |
| L1.2 | SEC, FEC, FARA, USASpending, LDA, OFAC, CourtListener connectors | ✅ |
| L1.3 | LDA fix — `client_name` query (504 Palantir filings) | ✅ |
| L1.4 | Deep 5-section GPT narrative | ✅ |
| L1.5 | PayPal Mafia + Thiel/Defense demo seeds | ✅ |
| L1.6 | Wikipedia + FundedAPI + SEC 13G/13D/Form D enrichment | ✅ |
| L1.7 | Graph backend — entities, relationships, `/graph/export` | ✅ |
| L1.8 | E2E Palantir + Peter Thiel on staging | ✅ |
| L1.9 | 79 tests passing (17 Jun baseline) | ✅ |
| L1.10 | US registry — 51 jurisdictions, 202 records, Playwright scrape for states | ✅ |
| L1.11 | BEA economics — 429 records, `/economics` page | ✅ |

### Layer 1 v1.2 — shipped 18 Jun (`d2432f1`)

| # | Item | Status | File |
|---|------|--------|------|
| L2.1 | Two-sided LDA — `client_name` + `registrant_name` | ✅ | `intelligence_service.py` |
| L2.2 | `[CLIENT SIDE]` / `[REGISTRANT SIDE]` claim tags in §4 | ✅ | `intelligence_service.py` |
| L2.3 | Apify connector — LinkedIn, PitchBook, Google News | ✅ | `apify_connector.py` |
| L2.4 | §6 People & Education (LinkedIn) for person reports | ✅ code | `intelligence_service.py` |
| L2.5 | §8 PitchBook & Investor Intelligence | ✅ code | `intelligence_service.py` |
| L2.6 | §9 News & Media Timeline | ✅ code | `intelligence_service.py` |
| L2.7 | Cytoscape graph embedded on `/intelligence` | ✅ | `intelligence.js` |
| L2.8 | Graph node click → pre-fill investigate form | ✅ | `intelligence.js` |
| L2.9 | Summary bar — lobbying both sides, news, LinkedIn edu counts | ✅ | `intelligence.js` |
| L2.10 | `apify-client>=3.0` in pyproject.toml | ✅ | `pyproject.toml` |
| L2.11 | `APIFY_API_TOKEN` documented in `.env.example` | ✅ | `.env.example` |
| L2.12 | Graceful Apify fallback when credits exhausted | ✅ | `apify_connector.py` |
| L2.13 | WhatsApp status update to James (19 Jun) | ✅ | — |
| L2.14 | Cross-verification of comms vs codebase (22 Jun) | ✅ | this doc |

---

## 5) Known gaps — told James vs reality

These were communicated as done or mostly done but are **not fully implemented**:

| Gap | What James was told | Actual state | Fix |
|-----|---------------------|--------------|-----|
| **Clickable entity names in report text** | "Click any entity ~80%" | `EntityChip` defined but never used; `SmartText` only styles `[CLIENT SIDE]` tags | Wire `EntityChip` into claim parsing; auto-generate on click |
| **Click → profile page** | Implied in "click any entity" | No link to `/entities/[id]`; page is raw JSON | Polish profile UI + link from report |
| **Auto-investigate on click** | Implied | `investigate()` only sets form fields; user must click Generate | Call `generate()` automatically on entity click |
| **Browser research agent** | "Yeah we will do it" / "Yeah sure" (19–20 Jun) | Zero code in intelligence pipeline | Build `browser_research_agent` (see §8) |
| **Argentina / international** | Confirmed feasible via browser | No connector, no agent; Argentina only in old Perplexity docs (`15th_June.md`) | Argentina spike after agent MVP |
| **Apify live data** | "~60% on LinkedIn/PitchBook" | Sections empty — credits still exhausted 22 Jun | Top up with James's card |

---

## 6) PENDING tasks — priority stack (22 Jun)

### P0 — Immediate (James waiting)

| # | Task | Owner | Status | Notes |
|---|------|-------|--------|-------|
| P0.1 | **Apify credit top-up** — James offered card 19 Jun | James / ops | 🔲 **Blocker** | Still `platform-feature-disabled` 22 Jun. ~$50–100/mo demo scale. |
| P0.2 | Verify Peter Thiel + Palantir with live Apify data after top-up | Dev | 🔲 | §6 LinkedIn, §8 PitchBook, §9 News should populate |
| P0.3 | Reply James confirming Apify top-up status + browser agent timeline | Abhishek | 🔲 | Don't imply browser agent is built yet |
| P0.4 | **Fix clickable entities gap** — wire `EntityChip`, auto-generate on click | Dev | 🔲 | Closes gap between promise and code |

### P1 — James 19–20 Jun ask (NEW — highest build priority after Apify)

| # | Task | Status | Notes |
|---|------|--------|-------|
| P1.1 | Design **browser research agent** architecture | 🔲 | Connectors first, browser fallback when no integration |
| P1.2 | Build `browser_research_agent.py` (or Apify browser actor wrapper) | 🔲 | Target public registries, gov DBs, courts, procurement, news |
| P1.3 | Integrate into `generate_intelligence_report` as fallback/enrichment layer | 🔲 | Trigger when jurisdiction uncovered OR "deep dive" flag |
| P1.4 | Merge browser findings into report sections with DOCUMENTED/REPORTED tags | 🔲 | Cited sources required |
| P1.5 | **Argentina spike** — one entity (e.g. Aeropuertos Argentina 2000, Mercado Libre) | 🔲 | Prove Perplexity-style path on staging |
| P1.6 | Deep-dive mode: holding companies, vehicle structures, related articles | 🔲 | James 20 Jun expansion |
| P1.7 | Financial research for public + private companies via browser | 🔲 | James 20 Jun expansion |
| P1.8 | Follow-up research when new decision/report surfaces | 🔲 | James 20 Jun expansion |

### P2 — Layer 2 Apify completion (code partial)

| # | Task | Status |
|---|------|--------|
| P2.1 | Apify company employees scraper → key people for org reports | 🔲 |
| P2.2 | Key people extractor → auto-fetch related entities → graph edges | 🔲 |
| P2.3 | Apify YouTube — interviews, documentaries | 🔲 |
| P2.4 | James sign-off on Apify scraping policy (LinkedIn + PitchBook) | 🔲 |

### P3 — Layer 2 UI + disclosure

| # | Task | Status |
|---|------|--------|
| P3.1 | Contracts two-sided disclosure (agency + contractor explicit) | 🔲 |
| P3.2 | FEC/FARA two-sided blocks | 🔲 |
| P3.3 | Person timeline UI (career + filings + news chronologically) | 🔲 |
| P3.4 | Polished `/entities/[id]` profile page (not raw JSON) | 🔲 |
| P3.5 | Graph export PNG/JSON | 🔲 |

### P4 — Layer 2 network + export

| # | Task | Status |
|---|------|--------|
| P4.1 | Full PayPal Mafia multi-entity network dossier (one linked report) | 🔲 |
| P4.2 | PDF export matching James's 15 PDF examples | 🔲 |

### P5 — Housekeeping

| # | Task | Status |
|---|------|--------|
| P5.1 | Update `README.md` — v1.2, point to latest handoff | 🔲 |
| P5.2 | Apify mock tests + LDA registrant-side tests | 🔲 |
| P5.3 | Update `18th_June.md` click-entity status (was marked ✅ incorrectly) | 🔲 |

### Deferred (unchanged)

| Item | Status |
|------|--------|
| CA SOS API (`calicodev.sos.ca.gov`) | ⏸️ Waiting on James |
| Cobalt Intelligence | ⏸️ Per James direction |
| OIDC Google SSO | ⏸️ Waiting on James |

---

## 7) Revised architecture — connectors + browser fallback (James 20 Jun)

James confirmed: use **both** structured connectors AND browser research.

```
Intelligence generate
        │
        ├──► US federal connectors (SEC, FEC, LDA, USASpending, OFAC, courts…)  ✅ live
        │
        ├──► US state registry (51 jurisdictions)                                  ✅ live
        │
        ├──► Apify enrichment (LinkedIn, PitchBook, News, YouTube)               🟡 code live, credits blocked
        │
        └──► Browser research agent (NEW)                                        🔲 not built
                 │
                 ├── Trigger: no connector for jurisdiction (Argentina, etc.)
                 ├── Trigger: deep-dive flag (holdings, vehicles, related parties)
                 └── Sources: public registries, gov portals, courts, procurement, news
                              │
                              ▼
                 Merge into dossier sections + graph edges + cited claims
```

**Existing browser capability (not wired to intelligence):**
- Playwright headless scrape in `packages/connectors/us/state_registry/states/scrape_generic.py` — US state SOS sites only
- Cursor browser MCP used for E2E QA — not production pipeline

**Needed:**
- Production browser research service callable from `intelligence_service.py`
- Jurisdiction detection → connector vs browser routing
- Source citation + confidence tagging on all browser-sourced claims

---

## 8) Apify status (22 Jun — still blocked)

| Item | Detail |
|------|--------|
| **Account** | `james97deller` · STARTER plan |
| **Error (22 Jun)** | `platform-feature-disabled` — "Monthly usage hard limit exceeded" |
| **Integration** | ✅ `apps/api/app/connectors/apify_connector.py` — LinkedIn, PitchBook, Google News |
| **Actors wired** | `automation-lab/linkedin-profile-scraper`, `mdataset/pitchbook-scraper`, `brilliant_gum/google-news-scraper` |
| **Impact** | §6, §8, §9 sections present but empty; all free sources still work |
| **James action** | Offered card 19 Jun — **top-up not completed** |
| **After top-up** | Re-run Peter Thiel (person) + Palantir (org); confirm live data in report |

---

## 9) Delivery outputs — James roadmap (updated 22 Jun)

| # | Output | Target | Status |
|---|--------|--------|--------|
| 1 | 9+ section dossier | Layer 1 | ✅ Live |
| 2 | Relationship map on dossier | Phase 1.2 | ✅ ~90% |
| 3 | Two-sided lobbying | Phase 1.2 | ✅ Done |
| 4 | Two-sided contracts/FEC | Phase 1.2 | 🔲 Pending |
| 5 | Click entity → investigate | Phase 1.2 | 🟡 Partial — fix gap |
| 6 | Entity profile page (polished) | Phase 2.0 | 🔲 Raw JSON only |
| 7 | People & education (LinkedIn) | Phase 2.0 | 🟡 Code; ⏸️ credits |
| 8 | PitchBook / investors | Phase 2.0 | 🟡 Code; ⏸️ credits |
| 9 | News & media | Phase 2.2 | 🟡 Partial |
| 10 | Browser research fallback | **NEW Phase 2.4** | 🔲 Not started |
| 11 | International (Argentina demo) | Phase 2.4 | 🔲 Not started |
| 12 | Person timeline | Phase 2.1 | 🔲 Not started |
| 13 | YouTube / books / interviews | Phase 2.2 | 🔲 Not started |
| 14 | Network dossier (PayPal Mafia) | Phase 2.3 | 🔲 Not started |
| 15 | PDF export | Phase 2.3 | 🔲 Not started |

---

## 10) Phase timeline (updated)

| Phase | Original dates | Status | Deliverable |
|-------|------------------|--------|-------------|
| **1.2** | 18 Jun | ✅ ~90% | Two-sided LDA, graph embed, click flow (fix text-click gap) |
| **2.0** | 25 Jun – 8 Jul | 🟡 ~50% | Apify LinkedIn/PitchBook/News — code done, credits blocked, employees 🔲 |
| **2.4** | **NEW — 23 Jun – 6 Jul** | 🔲 0% | Browser research agent + Argentina spike + dual-mode routing |
| **2.1** | 9–22 Jul | 🔲 0% | Person timeline UI |
| **2.2** | 23 Jul – 5 Aug | 🔲 ~15% | YouTube, books, full media layer |
| **2.3** | 6–26 Aug | 🔲 0% | PayPal Mafia network dossier + PDF |

**Revised total:** ~10 weeks + browser layer (~2 wk inserted after Apify unblocked)

---

## 11) Credentials & environment (22 Jun)

| Key | Status | Used for |
|-----|--------|----------|
| `OPENAI_API_KEY` | ✅ Set | Deep narrative |
| Federal connector keys | ✅ Set | SEC, FEC, LDA, USASpending, etc. |
| `ANTHROPIC_API_KEY` | ✅ Set | Skills (Claude) |
| `BEA_API_USER_ID` | ✅ Set | BEA economic data |
| `APIFY_API_TOKEN` | ✅ Set · ✅ **WORKING** (topped up 22 Jun) | News + LinkedIn live; PitchBook needs permission |
| James credit card | ✅ Used 22 Jun 10:30 | Apify topped up — confirmed working |
| `CA_SOS_API_KEY` | ⏸️ Deferred | James to provide |
| `COBALT_API_KEY` | ⏸️ Deferred | James to provide |
| `OIDC_*` | ❌ Missing | James to provide |

---

## 12) Files reference

### Shipped (v1.2 — 18 Jun)

| File | Purpose |
|------|---------|
| `apps/api/app/connectors/apify_connector.py` | LinkedIn, PitchBook, Google News |
| `apps/api/app/services/intelligence_service.py` | Orchestrator, two-sided LDA, Apify sections |
| `apps/web/pages/intelligence.js` | Report UI, graph embed, investigate flow |
| `apps/web/src/styles/Intelligence.module.css` | entityChip, apifyBadge, graphEmbed styles |
| `apps/api/pyproject.toml` | `apify-client>=3.0` |
| `.env.example` | `APIFY_API_TOKEN` |

### To create (next)

| File | Purpose |
|------|---------|
| `apps/api/app/connectors/browser_research_agent.py` | Browser fallback for uncovered jurisdictions + deep dive |
| `apps/api/app/services/jurisdiction_router.py` | Route entity → connector vs browser vs Apify |
| `apps/web/pages/entities/[id].js` | Polished profile UI (replace raw JSON) |
| `tests/test_apify_connector.py` | Mock Apify responses |
| `tests/test_lda_both_sides.py` | Registrant-side LDA tests |

---

## 13) Recommended next actions — updated 22 Jun

1. ✅ **Apify topped up** — News and LinkedIn live
2. **Approve Apify PitchBook actor permissions** (James action — 5 min): https://console.apify.com/actors/lsfMbqR3SfAud3Cx9?approvePermissions=true
3. **KPI strip + filter bar + tables on intelligence reports** — James's "missing" 22 Jun ask
4. **Fix clickable entities** — wire `EntityChip`, auto-generate report on click
5. **Design + build browser research agent** — James's 19–20 Jun ask
6. **Argentina spike** — prove international fallback (Aeropuertos Argentina 2000 or Mercado Libre)
7. **Apify company employees** + key-people auto-expand
8. **Contracts two-sided** disclosure
9. **Apollo email pipeline** (v2.0 Block A)
10. **Apify social footprint** (Twitter, Instagram, YouTube — v2.0 Block B)
11. **Per-entity RAG chat** (pgvector + Claude — v2.0 Block C)
12. **Tracking dashboard + daily digest** (v2.0 Block E)
13. **Person timeline UI**
14. **Update README**

See [james_requirements.md](./james_requirements.md) for the full prioritised build stack.

---

## 14) New requirements received (22 Jun) — summary

**Enterprise Intelligence Platform v2.0 doc** added:
- Apollo email pipeline (employee discovery, reverse WHOIS, breach checks)
- Apify social media intelligence (Twitter, Instagram, YouTube, cross-platform username)
- Per-entity RAG chat (pgvector + Claude, cited answers, PDF export)
- Multi-entity comparison page (radar chart, Sankey, board overlap)
- Tracking dashboard + daily digest (6 AM UTC, email + SMS alerts)
- Private company intelligence (OpenCorporates, GLEIF, FinCEN BOI, global Apify registry)

**Jarvis Nexus Dashboard spec** — separate executive operating system:
- Portfolio / Business / Department / Agent / System scopes
- KPI strips (MRR, burn, runway, experiments, win rate)
- AI recommendations + concerns feed
- Approval queue with risk scores
- Agent grid with cost, latency, KPI attribution
- Services health heatmap

**Agent Team + Central Suite** (James 22 Jun 10:43 — future):
- B2B/B2C outreach agents
- Founder mode in Claude
- GTM + release agents
- Centralised view of all software, websites, social media, agents

All details in [james_requirements.md](./james_requirements.md).

---

*End of 22 June handoff — v1.2 live; Apify unblocked; v2.0 requirements received; browser agent next; click-in-report gap still open*
