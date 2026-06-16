# 11th June 2026 — Boss Direction, 50-State Registry Research & Action Plan

**Purpose:** Capture James’s latest WhatsApp decisions (10–11 June), research-backed plan for **all 50 U.S. states + DC**, BEA economic data addition, done vs pending work, and realistic timeline for the **licensable registry API** product.

**Prior docs:** `5th_june.md` (Phase 1 scope) · `10th_June.md` (first registry strategy) · `PHASE1_MVP_COMPLETION_REPORT.md`

**Staging (unchanged):** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`

---

## 1) James conversation log — decisions captured

| Date/time | James / team | Decision |
|-----------|--------------|----------|
| 10 Jun AM | James | Asked what Google Workspace credentials are for |
| 10 Jun PM | Abhishek | Explained OIDC = Sign in with Google (SSO), not data; OpenCorporates rejected; Wave 1 state plan documented in `10th_June.md` |
| 10 Jun 5:15 PM | **James** | **“We need all states!!! Pls should include all states.”** |
| 10 Jun 5:18 PM | **James** | **Build the tech stack so we can license all U.S. state registry data as our own API** |
| 10 Jun 5:20 PM | James | Asked timeline; confirmed same normalized schema OK |
| 10 Jun 5:25 PM | Abhishek | Same schema yes; framework first; quoted “by the weekend” for all 50 |
| 10 Jun 6:26 PM | **James** | Add **[BEA (Bureau of Economic Analysis)](https://www.bea.gov/resources/for-developers)** to roadmap — finance contact flagged it for complete U.S. tracking |
| 11 Jun AM | James | **“Please keep me updated”** |

### Confirmed product direction (non-negotiable from James)

1. **All 50 states + DC** — not Wave 1 only.
2. **Same normalized schema** across every jurisdiction.
3. **Free sources first** → scrape where needed → **Cobalt per-use** as third fallback only.
4. **Do not buy OpenCorporates** (£2,250/yr).
5. **End product:** our own **licensable U.S. registry API** (commercial upside).
6. **Add BEA** economic datasets alongside existing gov connectors.

---

## 2) Research summary — how to do all 50 states

Research sources: [NASS corporate registration directory](https://www.nass.org/business-services/corporate-registration), [OpenCorporates state registry analysis (Sep 2025)](https://blog.opencorporates.com/2025/09/15/sourcing-data-directly-from-us-state-registries/), [Florida Sunbiz SFTP](https://dos.fl.gov/sunbiz/other-services/data-downloads/), [California BE Public Search API guide](https://calicodev.sos.ca.gov/content/California%20SOS%20BE%20Public%20Search%20API%20Guide%20v1.0.4.pdf), [Cobalt SOS API](https://cobaltintelligence.stoplight.io/docs/cobalt-intelligence/0f51bcacc3743-secretary-of-state-api), James’s SOS URL list (9 Jun).

### 2.1 Core finding

There is **no single federal company register** in the U.S. Each state (and DC) runs its own Secretary of State (or equivalent) system. Access methods fall into **five tiers**:

| Tier | Method | States (approx.) | Cost | Engineering |
|------|--------|------------------|------|-------------|
| **A** | Free open-data bulk (CSV/JSON/SFTP) | ~12–15 | $0 | Low — scheduled download + parse |
| **B** | Official REST/search API (free or key) | ~5–8 | $0–low | Low — HTTP connector |
| **C** | Paid official bulk (one-time or subscription) | ~8–12 | $30–$9,500+ per state | Medium — procurement + parse |
| **D** | Public web search only (scrape) | ~25–35 | $0 cash | High — Playwright/Puppeteer per portal |
| **E** | Paid per-search portal (e.g. TX SOSDirect) | ~3–5 | Per lookup | Medium — automate carefully |

**James’s strategy is correct:** Tier A+B first, Tier D for coverage gaps, Tier C only where bulk is cheap enough or legally required for redistribution, Tier E + **Cobalt** as fallback.

OpenCorporates’ own analysis notes DIY nationwide coverage is **possible but expensive** in money, engineering, and ongoing maintenance ([source](https://blog.opencorporates.com/2025/09/15/sourcing-data-directly-from-us-state-registries/)). Our advantage: we already have connector framework, evidence vault, entity resolution, and James accepts scrape engineering.

### 2.2 Priority states — Tier A/B (free bulk/API — start here)

| State | Access method | URL / notes |
|-------|---------------|-------------|
| **New York** | Open data JSON/CSV bulk | [data.ny.gov active corporations](https://data.ny.gov/d/n9v6-gdp6) · [JSON download](https://data.ny.gov/api/views/n9v6-gdp6/rows.json?accessType=DOWNLOAD) |
| **Colorado** | Socrata API | [Business Entities](https://data.colorado.gov/Business/Business-Entities-in-Colorado/4ykn-tg5h) · [Transaction history](https://data.colorado.gov/Business/Business-Entity-Transaction-History/casm-dbbj) |
| **Florida** | Free SFTP daily/quarterly dumps | [Sunbiz downloads](https://dos.fl.gov/sunbiz/other-services/data-downloads/) — host `sftp.floridados.gov`, public credentials published |
| **Oregon** | Open data portal | [Active Businesses ALL](https://data.oregon.gov/business/Active-Businesses-ALL/tckn-sxa6/data) |
| **Washington** | Corporation search API | [finditconsumer.wa.gov corps API](https://finditconsumer.wa.gov/corps/searchapi.aspx) |
| **Texas** | Comptroller franchise tax API | [API docs](https://api-doc.comptroller.texas.gov/) (not full SOS registry but useful enrichment) |
| **California** | BE Public Search API (subscription key) | [API guide PDF](https://calicodev.sos.ca.gov/content/California%20SOS%20BE%20Public%20Search%20API%20Guide%20v1.0.4.pdf) — free registration, gated key |
| **Minnesota** | Cheap bulk ($30) | Active business data — affordable if officers not required |

### 2.3 States with expensive official bulk (Tier C — defer or negotiate)

| State | Typical cost | Notes |
|-------|--------------|-------|
| Indiana | $8,000–$9,500 | Bulk + monthly updates |
| Kentucky | ~$2,000/month | Good deltas (daily/weekly officers) |
| West Virginia | $12,000 + $1,750/mo updates | Formal purchase |
| Texas SOS | No open bulk | SOSDirect ~$1/search |
| California Master Unload | $100–$900 | Flat files; API may suffice for MVP |

For **licensable API product**, some states require **commercial license agreements** before redistribution (Minnesota, Kentucky called out in OpenCorporates analysis). Legal review needed before selling data derived from those states.

### 2.4 Scrape tier (Tier D) — remaining states

James provided all **50 SOS search URLs** (AL–WY + DC). NASS directory confirms each state link: [nass.org/business-services/corporate-registration](https://www.nass.org/business-services/corporate-registration).

**Approach:**
- Shared **Playwright scraper framework** with per-state adapters (selectors, pagination, CAPTCHA handling).
- Rate limiting + robots/ToS review per state.
- Store raw HTML/JSON in evidence vault (provenance).
- Normalize to unified `state_entity` schema.

**High-complexity scrape targets:** Delaware (ICIS), California BizFile, New Jersey, Pennsylvania — JS-heavy portals.

### 2.5 Cobalt Intelligence — Tier E fallback (James-approved)

- **API:** `GET https://apigateway.cobaltintelligence.com/v1/search/` with `state`, `searchQuery`, `x-api-key`
- **Coverage:** All 50 states + DC, live SOS data
- **Use when:** Free bulk/API/scrape miss or timeout; per-use billing
- **Docs:** [Cobalt SOS API](https://cobaltintelligence.stoplight.io/docs/cobalt-intelligence/0f51bcacc3743-secretary-of-state-api)
- **Not primary** — James explicitly wants free first

---

## 3) Unified schema (James-approved — same across all states)

```yaml
state_entity:
  jurisdiction_code: us_ny          # ISO-style: us_{state_abbrev}
  entity_id: string               # SOS registration / file number
  legal_name: string
  entity_type: string             # LLC, Corp, LP, etc. (normalized enum)
  status: string                  # active | dissolved | inactive | unknown
  formation_date: date | null
  registered_agent_name: string | null
  registered_agent_address: object | null
  principal_address: object | null
  mailing_address: object | null
  officers: array                 # {name, title, address} where available
  source_tier: bulk | api | scrape | cobalt
  source_url: string              # provenance
  retrieved_at: datetime
  raw_document_id: int            # evidence vault link
```

Maps cleanly to existing platform: `source_record_meta.normalized` → entity resolution → graph → **future `/registry/search` API**.

---

## 4) Tech stack to build (licensable registry API)

James wants the **infrastructure built first**, then populate state-by-state.

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — Ingestion (per state)                                │
│  bulk_downloader │ rest_api_client │ playwright_scraper │ cobalt│
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — Normalization (shared)                               │
│  state_entity schema │ status vocabulary │ entity_type mapping  │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3 — Platform (existing)                                  │
│  evidence vault │ source_record_meta │ OpenSearch │ Postgres    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4 — Entity intelligence (existing + extend)              │
│  merge w/ SEC CIK │ GLEIF LEI │ SAM UEI │ cross-state dedupe   │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5 — Licensable API (new — product)                       │
│  GET /registry/search?q=&state= │ GET /registry/entity/{id}    │
│  API keys │ rate limits │ usage billing │ audit log             │
└─────────────────────────────────────────────────────────────────┘
```

**Package layout (planned, not built yet):**
- `packages/connectors/us/state_registry/` — base + `{ny, co, fl, ...}.py`
- `packages/scrapers/` — Playwright runners + state configs
- `apps/api/app/api/registry.py` — public search API
- Replace/demote `opencorporates` connector

---

## 5) BEA connector — James’s new addition (11 Jun)

**Why finance cares:** BEA publishes official U.S. **GDP, regional income, industry, international trade, investment** statistics — macro context for stock analysis, sector exposure, and state-level economic tracking.

| Item | Detail |
|------|--------|
| Portal | [bea.gov/resources/for-developers](https://www.bea.gov/resources/for-developers) |
| Signup | [apps.bea.gov/API/signup/](https://apps.bea.gov/API/signup/) — free 36-char UserID |
| Endpoint | `https://apps.bea.gov/api/data` |
| Formats | JSON, XML |
| Key datasets | NIPA (GDP), RegionalIncome, RegionalProduct, GDPbyIndustry, ITA, IIP, MNE |
| Official tools | Python/R packages on [BEA GitHub](https://github.com/us-bea) |
| Env var | `BEA_API_USER_ID` (planned) |

**Platform fit:** New connector `#18` under gov/economic — enrich `analyze_stock`, sector reports, and state-level dashboards. Complements SEC/FEC/USAspending for “complete U.S. tracking.”

**Priority:** After registry framework kickoff, or parallel if James wants macro data first (lower effort — single API, one key).

---

## 6) Done vs pending (11 June)

### ✅ Done (Phase 1 core + recent fixes)

| Area | Status |
|------|--------|
| 17 U.S. gov connectors | ✅ All ingesting on staging |
| Anthropic Claude skills | ✅ Live (`claude-sonnet-4-6`) |
| OpenAI skills fallback | ✅ Live |
| Stock `ai_narrative` via Claude | ✅ Live |
| Evidence vault + OpenSearch | ✅ 128+ docs indexed |
| Entity merge UI, Cytoscape graph | ✅ Shipped |
| Alerts, portfolio, reports, admin | ✅ Operational |
| pytest | ✅ 33 passing |
| OpenCorporates | ✅ SEC fallback (no paid key) |
| Docs | ✅ `5th_june.md`, `10th_June.md` |

### ⏳ Pending — quick wins

| Item | Owner | Effort |
|------|-------|--------|
| Google OIDC SSO | James → `.env` | 15 min |
| Update `PHASE1_MVP_COMPLETION_REPORT.md` | Dev | 30 min |
| Commit `10th_June.md` + `11th_June.md` | Dev | 5 min |

### 🔴 Pending — James’s new program (main work)

| # | Work item | Priority |
|---|-----------|----------|
| 1 | **Registry framework** — schema, base connector, scraper runner | P0 |
| 2 | **Tier A bulk connectors** — NY, CO, FL, OR | P0 |
| 3 | **Tier B API connectors** — WA, TX Comptroller, CA (key signup) | P0 |
| 4 | **Playwright scrape framework** + 10 high-volume states | P1 |
| 5 | **Remaining ~35 states** scrape adapters | P1 |
| 6 | **Cobalt fallback adapter** (config-gated, per-use budget) | P2 |
| 7 | **`/registry/search` licensable API** + API keys + rate limits | P1 |
| 8 | **BEA economic connector** (#18) | P1 |
| 9 | Cross-link registry ↔ SEC / GLEIF / SAM entity resolution | P2 |
| 10 | Commercial redistribution legal review (paid-bulk states) | P2 — legal |

---

## 7) Realistic timeline (honest — for James updates)

Abhishek quoted “by the weekend” for all 50 on 10 Jun. Research shows that is **only achievable for initial framework + ~6–10 Tier A/B states**, not full nationwide coverage with freshness and officers.

| Milestone | Target | Deliverable |
|-----------|--------|-------------|
| **M0 — Framework** | Days 1–3 | Schema, base connector, scraper shell, registry API stub, first NY bulk ingest |
| **M1 — Tier A wave** | Week 1 | NY, CO, FL, OR live in platform + searchable |
| **M2 — Tier B wave** | Week 2 | WA, TX API, CA API key, MN bulk |
| **M3 — Scrape wave 1** | Weeks 2–3 | 15 states via Playwright (DE, NJ, PA, GA, IL, MA, VA, NC, OH, MI, AZ, MO, TN, WI, MD) |
| **M4 — All 50 + DC** | Weeks 4–6 | Every state returns ≥ basic entity search; Cobalt fallback wired |
| **M5 — Licensable API beta** | Week 6–8 | External `/registry/search` with API keys, docs, usage metering |
| **M6 — BEA connector** | Week 2 (parallel) | Regional GDP + industry data in analyze_stock |
| **M7 — Production hardening** | Ongoing | Daily refresh, delta sync, break-fix, legal agreements |

**Weekend (14–15 Jun) realistic commit:** Framework + NY + CO + FL bulk downloading and normalized in DB — **not** all 50 production-ready.

James asked to **keep updated** → recommend **twice-weekly** short status: states live count, blockers, Cobalt spend.

---

## 8) 50-state coverage matrix (research draft)

Legend: **B**=bulk free · **A**=API · **S**=scrape · **$**=paid bulk · **C**=Cobalt fallback

| ST | Primary | ST | Primary | ST | Primary | ST | Primary |
|----|---------|----|---------|----|---------|----|---------|
| AL | S | LA | S | OH | S | VT | S |
| AK | S | ME | S | OK | S | VA | S |
| AZ | S | MD | S | OR | **B** | WA | **A** |
| AR | S | MA | S | PA | S | WV | S / $ |
| CA | **A** / $ | MI | S | RI | S | WI | S |
| CO | **B** | MN | **$**30 | SC | S | WY | S |
| CT | S | MS | S | SD | S | DC | S |
| DE | S | MO | S | TN | S | | |
| FL | **B** | MT | S | TX | **A** / S / C | | |
| GA | S | NE | S | UT | S | | |
| HI | S | NV | S | VT | S | | |
| ID | S | NH | S | VA | S | | |
| IL | S | NJ | S | WA | **A** | | |
| IN | **$** | NM | S | WV | **$** | | |
| IA | S | NY | **B** | WI | S | | |
| KS | S | NC | S | | | | |
| KY | **$** | ND | S | | | | |

Every state gets **at least S (scrape) or C (Cobalt)** so James’s “all states” requirement is met; quality and officer depth vary by tier.

---

## 9) Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Portal HTML changes break scrapers | Per-state adapter tests; alerting; Cobalt fallback |
| State prohibits commercial redistribution | Legal review; exclude or license paid bulk states from external API |
| CAPTCHA / bot blocking | Rotate IPs carefully; prefer bulk/API; Cobalt for blocked states |
| Timeline slip vs “weekend” expectation | Set M0–M4 milestones; report state count weekly to James |
| Data quality varies (officers missing) | Schema nullable fields; confidence score per record |
| BEA rate limits | Cache responses; scheduled refresh not per-request |

---

## 10) Recommended immediate next steps (no code until James confirms)

1. **Reply to James** (see §11) — confirm all-50 plan, honest timeline, BEA added.
2. **James confirms:** scrape policy OK? Cobalt monthly budget? CA API key signup who owns it?
3. **Start M0 engineering:** registry framework + NY + CO (highest ROI free bulk).
4. **Register BEA API key** at [apps.bea.gov/API/signup/](https://apps.bea.gov/API/signup/) — free, 5 min.
5. **Optional:** Google OIDC for SSO (unchanged from 10 Jun).

---

## 11) Draft status reply to James (copy/paste)

> Hi James,
>
> Understood — **all 50 states + DC**, same schema, built so we can **license it as our own API**. Research is documented in `11th_June.md`.
>
> **Plan:** Free bulk/API first (NY, Colorado, Florida SFTP, Oregon, Washington, Texas, California API) → Playwright scrapers for remaining SOS portals → Cobalt only as paid per-use fallback when free paths miss.
>
> **Timeline (honest):** Framework + first bulk states this week; **all 50 searchable within ~4–6 weeks** with basic entity fields everywhere; licensable external API ~week 6–8. Weekend target covers foundation + first 3–4 states, not full nationwide depth.
>
> **BEA:** Added to roadmap as connector #18 — free API key at [bea.gov/developers](https://www.bea.gov/resources/for-developers) for GDP, regional, and industry data. Great call from your finance contact.
>
> **Google Workspace creds:** Still only for SSO login — separate from registry work.
>
> I’ll send updates **twice weekly** with a live state count (e.g. “23/51 states ingesting”).
>
> Need from you: (1) OK to scrape public SOS search pages? (2) Any monthly cap on Cobalt fallback spend?
>
> Thanks,  
> Abhishek

---

## 12) Changelog

| Date | Author | Change |
|------|--------|--------|
| 11 Jun 2026 | Dev team | Initial research doc: all-50 mandate, BEA, tier matrix, timeline, tech stack |

---

*Next file after engineering starts: `12th_June.md` or sprint board with per-state connector checklist.*
