# 15th June 2026 — BizFile Live + Intelligence Report Layer (Phase 3) Planning

**Purpose:** Daily handoff for James — CA data infrastructure confirmed working + full brief on next major feature: the Advanced Intelligence Report layer requested by James in WhatsApp (12 Jun).

**Prior docs:** `12th_June.md` (Cobalt + CA SOS) · `PHASE2_COMPLETION_REPORT.md`

**Staging:** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`
**Branch:** `feature/us-50-state-registry-api` · **PR #2**

---

## 1) Executive summary — what is done vs pending

| Area | Status |
|------|--------|
| **CA Tier 1 — Official CA SOS API** | ⏳ Pending approval — subscriptions submitted at calicodev.sos.ca.gov |
| **CA Tier 2 — BizFile scrape (free, official)** | ✅ Working — Playwright on Ubuntu 26.04; **150 CA entities** per run |
| **CA Tier 3 — Cobalt Intelligence** | ⚠️ Trial cap exhausted (HTTP 429); code intact; DB has seeded data |
| **CA Tier 4 — Sample fallback** | ✅ Working |
| **Staging registry** | ✅ **202 records**, 51 jurisdictions, API healthy |
| **Bulk states (NY, CO, FL, OR)** | ✅ Live — 50 records each |
| **API states (WA, TX, CA)** | ✅ Live with fallback |
| **BEA connector** | ✅ Live |
| **17 federal connectors** | ✅ Live |
| **Tests** | ✅ 44/44 passed (fast suite) |
| **Phase 3 — Intelligence Reports** | 🆕 **NEXT — design starts this week** |

---

## 2) CA data waterfall — verified 15 Jun

```
1. Official CA SOS CBC API   ⏳  PENDING  — waiting on key
2. BizFile Online scrape     ✅  WORKING  — 150 live records per run, no cost
3. Cobalt Intelligence       ⚠️  CAPPED   — 429; upgrade plan or skip for now
4. Sample records            ✅  WORKING  — tests / offline
```

**CA is fully covered by tier 2 (BizFile) until tier 1 key arrives.**
Ubuntu 26.04 Playwright fix applied — no new server needed.

---

## 3) New requirement from James — Phase 3: Advanced Intelligence Reports

### 3.1 James's WhatsApp message (12 Jun, verbatim)

> "For actual advanced research to these records how are we gonna approach it"
> "They need to be advanced intelligence reports that try and find entities business holding companies, and try and dig deeper"
> "Find relationships of investors / businesses or investment vehicles / government contracts / owners / etc"
> "All examples of intelligence reports"
> "We would have layer 1. For future"

James also shared **2 example intelligence reports** (15th_June_docs):

---

### 3.2 Report A — Rockbridge Network / Scott Bessent / Japan (Japanese_Ties_Rockbridge_Bessent_Report.pdf)

**What it shows — the intelligence dimensions James wants:**

| Dimension | What the report does |
|-----------|---------------------|
| **Political donor networks** | Maps Rockbridge Network — private donor group, JD Vance co-founder, Peter Thiel allies, Winklevoss twins |
| **Cross-border entity relationships** | Connects US conservative political org → Japan branch → JBIC governor (Tadashi Maeda) |
| **Foreign government influence (FARA)** | Japan ranked top foreign spender under FARA — $500M+ since 2016 via JETRO, Embassy, corporations |
| **Investor / government linkage** | Scott Bessent: Treasury Secretary + Rockbridge insider — dual role bridging donor network and US-Japan policy |
| **Holding company / fund structure** | Key Square Group (Bessent's hedge fund) → Soros Fund Management background |
| **Entity disambiguation** | Same person in multiple capacities — political donor, public official, fund manager |

**Key data sources the report uses:**
FARA filings, OpenSecrets, FOIA-accessible government readouts, news, Wikipedia, organizational announcements.

---

### 3.3 Report B — LATAM Minerals & Energy (LATAM MINERALS AND ENERGY.pdf)

**What it shows — the intelligence dimensions James wants:**

| Dimension | What the report does |
|-----------|---------------------|
| **Corporate ownership trees** | Maps 5-6 Argentine capital groups across both mining AND energy: Techint/Rocca, PAE/Bulgheroni, Pampa/Mindlin, Manzano/Integra, Eurnekian |
| **Investment vehicles** | RIGI-registered SPVs, JV consortia (Southern Energy SA, Argentina LNG, VMOS), holding structures |
| **Government contracts / concessions** | RIGI pipeline ($50.7B approved); YPF state involvement; US-Argentina framework $130B |
| **Investor relationships** | BHP-Lundin (Vicuña JV), JP Morgan debt syndicates, IFC/IDB/JBIC multilateral stacks |
| **Cross-border capital flows** | Chinese stake mapping (CNOOC 25% PAE; Tianqi 22% SQM; Ganfeng in 13/47 Argentine lithium projects) |
| **Geopolitical / strategic framing** | Chancay port control (COSCO 60%/Volcan 40%); bi-oceanic railway; Pax Silica alliance |
| **Risk flags** | Manzano/Integra: Argentine mining player AND 40% indirect Chancay stake (Chinese-aligned port) |

**Key data sources the report uses:**
SEC filings, RIGI approvals, government readouts, trade data, FARA, Carnegie Endowment, Reuters, mining industry filings.

---

### 3.4 What James actually wants built

Based on both reports and his messages, James wants the platform to **automatically generate these types of reports** from the registry and enrichment data. The core feature set:

```
Phase 3 — Intelligence Report Layer

INPUT: An entity name, person, or topic
       e.g. "Apple Inc CA" / "Rockbridge Network" / "BHP copper Argentina"

OUTPUT: A structured intelligence report containing:

  1. ENTITY PROFILE
     - Legal name, registration number, state, status, entity type
     - Formation date, registered agent
     - All known aliases, prior names, successor entities

  2. OWNERSHIP & HOLDING STRUCTURE
     - Parent companies (1–5 layers deep)
     - Subsidiaries and sister entities
     - Beneficial owners (UBO identification)
     - Investment vehicles and SPVs

  3. INVESTOR & CAPITAL RELATIONSHIPS
     - Known investors and funding rounds
     - Debt syndicates, lenders
     - Equity partners in JVs
     - Private equity / hedge fund connections

  4. GOVERNMENT CONTRACTS & REGULATORY EXPOSURE
     - Federal contracts (USASpending.gov — already integrated)
     - State contracts
     - FARA registrations (already integrated)
     - OFAC / sanctions screening (already integrated)
     - Regulatory filings (SEC EDGAR — already integrated)
     - LDA lobbying registrations (already integrated)

  5. OFFICER & PERSON RELATIONSHIPS
     - Named directors, officers, registered agents
     - Cross-entity officer appearances (same person in multiple companies)
     - Political donor connections (FEC — already integrated)

  6. CROSS-BORDER & STRATEGIC CONNECTIONS
     - Foreign entity affiliations
     - FARA-registered foreign principals
     - Chinese state-owned exposure indicators
     - Geopolitical risk flags

  7. INTELLIGENCE NARRATIVE
     - AI-written 1-2 page summary of findings
     - Risk indicators highlighted
     - Source citations for every claim
```

---

### 3.5 Data sources already integrated vs still needed

| Data category | Sources available NOW | Sources to add for Phase 3 |
|---------------|-----------------------|---------------------------|
| Business registry (51 states) | ✅ All 51 jurisdictions | CA tier 1 key pending |
| Federal contracts | ✅ USASpending.gov connector | FPDS direct feed (richer) |
| FARA filings | ✅ Integrated | — |
| OFAC sanctions | ✅ Integrated | — |
| SEC EDGAR filings | ✅ Integrated | Ownership filings (13D/13G/SC 13) |
| FEC political donations | ✅ Integrated | — |
| LDA lobbying | ✅ Integrated | — |
| Federal regulations/notices | ✅ Integrated (ECFR, Federal Register) | — |
| Court records | ✅ CourtListener integrated | PACER direct (paid) |
| Global entity data | ✅ OpenCorporates, GLEIF | — |
| **Corporate ownership trees** | ❌ Not yet | OpenOwnership, OpenCorporates ownership API, Companies House (UK) |
| **Beneficial ownership (UBO)** | ❌ Not yet | FinCEN BOI registry (launched 2024), state UBO filings |
| **Trade/import-export data** | ❌ Not yet | Panjiva/ImportYeti, Census trade data |
| **News + narrative intelligence** | ❌ Not yet | NewsAPI, GDELT, OpenAlex |
| **Political connections / donors** | ⚠️ FEC data available | Cross-entity person matching needed |
| **Foreign government / FARA graph** | ⚠️ FARA data available | Graph traversal needed |
| **AI report generation** | ❌ Not yet | OpenAI GPT-4o (key already in .env) |
| **Graph / relationship DB** | ❌ Not yet | Neo4j, or PostgreSQL graph extension |

---

## 4) Pending tasks — prioritised

### Immediate (this week)
| # | Task | Why |
|---|------|-----|
| 1 | Wait for **CA SOS API key** | Emails to abhishekk@kyma.world — paste key when received |
| 2 | **Re-seed CA** from BizFile | Replace Cobalt DB rows with official free data (scripts/seed-state-registry.sh us_ca) |
| 3 | **Design Phase 3 data model** | Entity + relationship graph schema — needs decision before coding |
| 4 | **Cobalt plan** — discuss with James | Trial exhausted; decide upgrade or skip |

### Phase 3 — Intelligence Reports (next sprint)
| # | Task | Effort |
|---|------|--------|
| P3.1 | **Graph data model** — entities + relationships + evidence sources | Medium |
| P3.2 | **Entity resolution** — match same person/company across data sources | High |
| P3.3 | **Ownership tree crawler** — integrate OpenOwnership/OpenCorporates ownership API | Medium |
| P3.4 | **FinCEN BOI connector** — beneficial ownership registry (US, launched 2024) | Medium |
| P3.5 | **Cross-entity person matching** — director/officer appears in multiple entities | Medium |
| P3.6 | **Report template engine** — structured JSON → formatted intelligence report | Medium |
| P3.7 | **AI narrative writer** — GPT-4o generates 1-2 page summary from structured data | Low (key exists) |
| P3.8 | **Report UI** — render formatted report with source citations on frontend | Medium |
| P3.9 | **Report export** — PDF + Word output (reportlab + python-docx already in deps) | Low |
| P3.10 | **News enrichment connector** — NewsAPI / GDELT for entity mentions | Medium |

### Blocked on James
| # | Item | What's needed |
|---|------|---------------|
| B1 | **OIDC / Google Workspace SSO** | `OIDC_CLIENT_ID` + `OIDC_CLIENT_SECRET` from James |
| B2 | **Cobalt plan upgrade decision** | Discuss — $0.60–$1/lookup, needed for 44 scrape-tier states |
| B3 | **Phase 3 scope sign-off** | Which report types to build first: ownership tree? government contracts? cross-border? |

---

## 5) Files changed (15 Jun)

| File | Change |
|------|--------|
| `packages/connectors/us/state_registry/api/ca.py` | BizFile scraper, 4-tier waterfall |
| `packages/connectors/us/_common/http_helpers.py` | `ensure_playwright_platform()` for Ubuntu 26.04 |
| `packages/connectors/us/state_registry/states/scrape_generic.py` | Platform override before Playwright |
| `scripts/setup-playwright.sh` | One-time Playwright setup |
| `tests/connectors/test_state_registry.py` | 6 new BizFile tests |
| `15th_June.md` | This handoff |

---

## 6) Keys status

| Key | Status | Notes |
|-----|--------|-------|
| `CA_SOS_API_KEY` | ⏳ Pending | Subscriptions submitted at calicodev.sos.ca.gov |
| `COBALT_API_KEY` | ⚠️ Set, trial capped | HTTP 429 — upgrade needed for 44 states |
| `OPENAI_API_KEY` | ✅ Set | Ready for Phase 3 AI narrative generation |
| `BEA_API_USER_ID` | ✅ Set | Live |
| 17 federal gov keys | ✅ Set | All working |
| `OIDC_CLIENT_ID/SECRET` | ❌ Missing | Waiting on James |

---

## 7) Message to James (suggested)

> Hi James, today's update:
>
> **Infrastructure (done):** CA BizFile scrape is now live on the current server — no new deployment needed. We get fresh official CA data free via Playwright. CA official API key still pending from the state (we applied 12 Jun). Cobalt trial has run out but we don't need it for CA anymore.
>
> **Phase 3 (planning):** I've reviewed both reports you sent — the Rockbridge/Bessent report and the LATAM Minerals report. I understand exactly what you want: automated intelligence reports that map ownership structures, investors, government contracts, officers, cross-border connections, and write a narrative summary. We already have most of the data sources integrated (FARA, USASpending, SEC EDGAR, FEC, OFAC, 51-state registry, court records). What we need to build next is: (1) the graph/relationship layer to connect entities across sources, (2) the report template engine, and (3) the AI narrative writer (we already have the OpenAI key). Can we get 30 min this week to align on which report type to build first?

---

*End of 15 June handoff*
