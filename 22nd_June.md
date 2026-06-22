# 22nd June 2026 — Project Status, James Comms Cross-Verification + Next Steps

**Purpose:** Consolidated handoff as of 22 Jun — all done/pending tasks, honest cross-verification of WhatsApp messages to James (19–22 Jun), updated priority stack including browser research fallback, and full v2.0 requirements from James's docs.

**Prior docs:** [18th_June.md](./18th_June.md) (v1.2 shipped) · [17th_June.md](./17th_June.md) · [README.md](./README.md)  
**Full requirements:** [james_requirements.md](./james_requirements.md) — all James asks in one place

**Staging:** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`  
**Branch:** `feature/layer2-kpi-filters-clickable-browser` (active, 5 commits) · base: `feature/us-50-state-registry-api` · **PR #2**  
**Last push:** `4eff7b7` — Layer 2 tasks 1–4 complete (KPI strip, filters, click-to-investigate, contracts two-sided, browser agent)

**Status:** 🟢 **Layer 2 tasks 1–4 SHIPPED today** · Apify ✅ all 3 connectors working · Layer 2 ~**65%** · v2.0 features (Apollo, RAG, social, tracking) next

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

**Apify status after top-up (all working 22 Jun):**
- ✅ Google News: 47–81 articles per query (Palantir, Peter Thiel tested)
- ✅ LinkedIn: Peter Thiel profile data (headline, experience, education)
- ✅ PitchBook: switched to `mdataset/pitchbook-realtime-scraper` — no permission needed, Palantir data confirmed (4,395 employees, description, founded 2003)

**Bug fixed (22 Jun):** `apify_connector.py` — `clean=True` (boolean) → `clean="true"` (string) in dataset fetch. Was causing HTTP 400 errors after every successful actor run.

---

## 1) Executive summary — 22 Jun (updated 1:25 PM)

| Area | Status |
|------|--------|
| **Layer 1 (US federal dossier)** | ✅ 100% — 9–12 sections, all free connectors, GPT narrative, PayPal Mafia seeds |
| **Layer 1 v1.2 (18 Jun)** | ✅ Shipped — two-sided LDA, Cytoscape embed, Apify connector |
| **Apify — Google News** | ✅ Live — 47–81 articles per query |
| **Apify — LinkedIn** | ✅ Live — headline, education, experience |
| **Apify — PitchBook** | ✅ Live — switched to realtime-scraper, no permission needed |
| **KPI strip on reports** | ✅ Shipped 22 Jun — contracts value, lobbying spend, court risk, sanctions, news, confidence |
| **Filter bar on reports** | ✅ Shipped 22 Jun — category / source / confidence / text search |
| **Section category labels** | ✅ Shipped 22 Jun — Financial / Government / Legal / Intelligence / Social |
| **Sortable tables + CSV export** | ✅ Shipped 22 Jun — pagination 10/page, CSV download per section |
| **Click-to-investigate (claim text)** | ✅ Shipped 22 Jun — any capitalized entity name clickable + auto-generates report |
| **Contracts two-sided disclosure** | ✅ Shipped 22 Jun — [RECIPIENT SIDE] + [AGENCY SIDE] |
| **Browser research agent** | ✅ Shipped 22 Jun — `POST /intelligence/browser-research`, 8 jurisdictions, Argentina spike tested |
| **Entity profile page** | 🟡 API exists; `/entities/[id]` still raw JSON — polish pending |
| **v2.0 requirements** | 📄 Received from James (Enterprise v2.0 doc + Jarvis Nexus spec) |
| **KPIs doc for platform** | ⏸️ James hasn't sent yet |
| **CA SOS / Cobalt / OIDC** | ⏸️ Deferred |

### Progress percentages (honest — updated 22 Jun 1:25 PM)

| Scope | Done | Pending |
|-------|------|---------|
| Layer 1 core dossier (US) | **100%** | — |
| Layer 1 v1.2 (two-sided LDA, graph, Apify) | **100%** | — |
| **Layer 2 — James 18 Jun asks** | **~65%** | See task table below |
| Phase 2.0 Apify (News + LinkedIn + PitchBook) | **✅ 90%** | Employees scraper + social actors |
| Phase 2.4 browser research | **✅ 70%** | Deep-dive mode, more jurisdiction coverage |
| KPIs / filters / tables / labels | **✅ 100%** | — |
| Click-to-investigate | **✅ 100%** | — |
| Contracts two-sided | **✅ 100%** | — |
| v2.0 new features (Apollo, RAG, social, tracking, comparison) | **0%** | Full build — next sprint |
| Jarvis Nexus Dashboard | **0%** | Separate product — after v2.0 |
| AI Agent Team + Central Suite | **0%** | Future — after Jarvis |

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

## 13) Full task tracker — 22 Jun

### ✅ Done today (22 Jun)

| # | Task | Commit | Notes |
|---|------|--------|-------|
| T1 | KPI strip (6 cards: contracts, lobbying spend, court risk, sanctions, news, confidence) | `0586ad2` | Live on staging |
| T2 | Filter bar (category / source / confidence / text search) | `0586ad2` | URL-synced filters, clear button |
| T3 | Section category labels (Financial / Government / Legal / Intelligence / Social) | `0586ad2` | Color-coded badges |
| T4 | Sortable tables + CSV export + pagination (10/page) per section | `0586ad2` | Download button on every section |
| T5 | Click-to-investigate in claim text (auto-generate, not just pre-fill) | `fbb48fa` | Any capitalized entity name clickable |
| T6 | Contracts two-sided: [RECIPIENT SIDE] + [AGENCY SIDE] | `4ab8dc7` | Same pattern as lobbying both-sides |
| T7 | Browser research agent (`POST /intelligence/browser-research`) | `2dd9537` | 8 jurisdictions, Argentina tested |
| T8 | PitchBook switched to `pitchbook-realtime-scraper` (no permissions needed) | `5442839` | Palantir 4,395 employees confirmed |
| T9 | Apify poll loop fix (READY→SUCCEEDED) | `5442839` | All 3 Apify connectors stable |
| T10 | `james_requirements.md` created | `7757083` | All 3 products documented |
| T11 | `22nd_June.md` + `README.md` updated | `4eff7b7` | Reflects full current state |

### 🔲 Pending — next sprint (v2.0 features)

| # | Task | Priority | Source |
|---|------|----------|--------|
| P1 | Apollo email pipeline — find employees, reverse WHOIS, breach check | P1 | v2.0 Block A |
| P2 | Apify social — Twitter/X, Instagram, YouTube, username finder | P1 | v2.0 Block B |
| P3 | Per-entity RAG chat (pgvector + Claude, cited Q&A, PDF export) | P1 | v2.0 Block C |
| P4 | Tracking dashboard + daily digest (6 AM UTC, email + SMS) | P1 | v2.0 Block E |
| P5 | Private company intelligence (OpenCorporates, GLEIF, FinCEN BOI) | P1 | v2.0 Block F |
| P6 | Comparison page — up to 5 entities, radar/Sankey/board overlap | P2 | v2.0 Block D |
| P7 | Apify company employees scraper → key people on org reports | P2 | Layer 2 |
| P8 | Key people auto-expand → graph edges | P2 | Layer 2 |
| P9 | Person timeline UI (career + filings + news chronologically) | P2 | Layer 2 |
| P10 | Polished `/entities/[id]` profile page (replace raw JSON) | P2 | Layer 2 |
| P11 | Full PayPal Mafia network dossier (one linked multi-entity report) | P3 | Demo |
| P12 | PDF export matching James's desired style | P3 | v2.0 |
| P13 | FEC/FARA two-sided disclosure | P3 | Layer 2 |
| P14 | Graph export (PNG/JSON) | P3 | Layer 2 |

### ⏸️ Waiting on James

| Item | Status |
|------|--------|
| KPIs doc for Financial Intelligence Platform | Not received yet (22 Jun 10:22) |
| CA SOS API key | Deferred |
| Cobalt Intelligence | Deferred |
| OIDC Google SSO credentials | Deferred |

### 🏗 Future products (not this sprint)

| Product | Status |
|---------|--------|
| Jarvis Nexus Dashboard (executive operating system) | Spec received, not started |
| AI Agent Team (B2B/B2C outreach, GTM, founder mode) | Concept discussed, not started |
| Centralised Management Suite (all software/websites/social) | Concept discussed, not started |

---

## 14) Recommended next actions

1. **Start v2.0 Block A** — Apollo email pipeline (`POST /intelligence/apollo`)
2. **Start v2.0 Block B** — Apify social footprint (Twitter, Instagram, YouTube)
3. **Start v2.0 Block C** — Per-entity RAG chat (pgvector + Claude)
4. **Merge PR** — `feature/layer2-kpi-filters-clickable-browser` → `feature/us-50-state-registry-api`
5. **Polish `/entities/[id]`** — replace raw JSON with proper profile page
6. **Person timeline UI** — career + filings + news chronologically

See [james_requirements.md](./james_requirements.md) for the full prioritised build stack.

---

*End of 22 June handoff — Layer 2 tasks 1–4 shipped; Apify all 3 connectors working; v2.0 features next*
