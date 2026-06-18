# 18th June 2026 — James Layer 2 Feedback + Apify Research + Sprint Plan

**Purpose:** Daily handoff after James reviewed Layer 1 v1.1 (17 Jun WhatsApp sent) and replied with **Layer 2 scope** — two-sided disclosure, relationship maps, media depth, LinkedIn/education, clickable entities, person timelines, visualizers, and a formal project plan. Apify researched as unified vendor for LinkedIn, PitchBook, news, and YouTube.

**Prior docs:** [17th_June.md](./17th_June.md) (v1.1 shipped) · [16th_June.md](./16th_June.md) · [README.md](./README.md)

**Staging:** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`  
**Branch:** `feature/us-50-state-registry-api` · **PR #2**  
**Last push:** `4dba953` — James cross-verification in 17th_June.md

**Status:** 🟡 **Layer 1 v1.1 live** — James 18 Jun feedback = **new Layer 2 backlog**. Apify token available locally; **no Apify integration coded yet**.

---

## 1) Executive summary — 18 Jun

| Area | Status |
|------|--------|
| **Layer 1 v1.1** | ✅ Shipped 17 Jun — lobbying fix, deep narrative, PayPal Mafia seeds, 9 sections, E2E verified |
| **James v1.1 review** | 🟡 Sent WhatsApp 17 Jun PM — James replied 18 Jun AM with **new requirements** |
| **Two-sided disclosure** | 🟡 Partial — lobbying claims name client+firm; contracts one-sided; no registrant-side LDA |
| **Relationship map / visualizers** | 🔲 Not on `/intelligence` — `/graph` exists separately, not wired |
| **Key people → auto-expand** | 🔲 Not built |
| **Media (interviews, YouTube, books)** | 🔲 Not built — Wikipedia only |
| **LinkedIn / education / colleges** | 🔲 Not built — **Apify path unblocked** (`APIFY_API_TOKEN` in `.env`) |
| **Click entity → profile** | 🟡 Backend `/entities/{id}` exists; not linked from intelligence reports |
| **Person timeline (news + social)** | 🔲 Not built — Apify news/YouTube actors identified |
| **PitchBook** | 🔲 Not integrated — **Apify `mdataset/pitchbook-scraper`** available (~$3.50/1K, no James key) |
| **Project plan for James** | 🟡 Drafted below — **send today** |
| **CA / Cobalt** | ⏸️ Still deferred |

---

## 2) James conversation — 18 Jun (WhatsApp, verbatim)

### 2.1 Context — what we sent James (17 Jun PM)

v1.1 update: LDA fix (504 filings), 5-section narrative, PayPal Mafia seeds, free enrichment (Wikipedia, SEC 13G, FundedAPI). Asked for PitchBook key + PDL approval for LinkedIn/education.

### 2.2 James replies — batch 1 (18 Jun ~9:56 AM)

> "For all factos like lobbying let's disclose both sides of contracts"

> "Key people should trigger additions investigation into all related parties  
> To create a detailed relationship map"

> "What about bios, interviews, books, articles, documentaries or YouTube videos various, etc…"

> "Did we add visualizers"

### 2.3 James replies — batch 2 (18 Jun ~10:01 AM)

> "Can we do LinkedIn  
> Try and track colleges and related parties."

> "Than deep research into a time line for each person any news social media, social media mentions, etc"

> "We need to be able to click on any entity company or person; and view their information.  
> And understand there relationship, with them and other people…"

> "Ok need project plan, timelines please…. And delivery output requirements or expectations"

---

## 3) James requirements cross-verification (18 Jun)

| James said | Interpretation | Status | Evidence / gap |
|------------|----------------|--------|----------------|
| **Both sides** (lobbying, contracts, etc.) | Every factor shows both parties explicitly | 🟡 **PARTIAL** | Lobbying claims: "X lobbied for Palantir" + `lobbies_for` edges. Contracts: agency → recipient only. No LDA query when entity is **registrant** (lobbying firm). No unified two-sided UI block. |
| **Key people → related parties → relationship map** | Auto-investigate named people; build graph | 🔲 **NOT DONE** | Narrative lists people from Wikipedia/SEC. Graph edges written to DB. No auto-expansion; no map on report page. |
| **Bios, interviews, books, articles, documentaries, YouTube** | Rich media / public record depth | 🔲 **NOT DONE** | Wikipedia summary only in §1. No news, YouTube, books, interviews pipeline. |
| **Visualizers** | Charts / relationship map on dossier | 🔲 **NOT DONE** | `/intelligence` = text sections + summary bar. `/graph` (Cytoscape) exists at separate URL, not embedded. |
| **LinkedIn — colleges, related parties** | Education + career + network | 🔲 **NOT DONE** | Proxycurl shut down. PDL evaluated 17 Jun. **Apify path now available** — see §6. |
| **Person timeline** (news, social mentions) | Chronological life/career + media | 🔲 **NOT DONE** | `/search/entities/{id}/timeline` exists for generic entities but not wired to intelligence person reports or news/social. |
| **Click any entity → profile + relationships** | Interactive entity explorer | 🟡 **PARTIAL** | `GET /search/entities/{id}` + `/entities/[id]` page (JSON). Names in intelligence report **not clickable**. |
| **Project plan, timelines, delivery expectations** | Formal Layer 2 roadmap | 🟡 **IN THIS DOC** | §8–§10 below — send to James today. |

### Overall verdict (18 Jun)

| Category | Items |
|----------|-------|
| ✅ Done (17 Jun, still valid) | LDA fix, deep narrative, 9-section report, PayPal Mafia seeds, free federal + Wikipedia enrichment, E2E verified |
| 🟡 Partial | Two-sided lobbying text; entity profile API exists but not linked; graph backend exists but not on dossier |
| 🔲 Not done (James 18 Jun) | Full two-sided disclosure, relationship map visualizer, key-people auto-expand, media layer, LinkedIn/education, person timeline, clickable entities, network dossier, PDF |
| 🔓 **Unblocked today** | Apify token in `.env` — can spike LinkedIn + PitchBook + news + YouTube without waiting on James for PDL/PitchBook keys |

---

## 4) What was done before 18 Jun (carry-forward)

See [17th_June.md](./17th_June.md) §1–§12. Key facts:

- **Palantir:** 504 lobbying filings, $1.72B contracts, 9 sections, 13 graph edges
- **Peter Thiel:** Person dossier works; Wikipedia + Founders Fund Form D + Palantir 13G
- **PayPal Mafia seeds:** Thiel, Musk, Hoffman, Levchin, Sacks + Thiel/Defense orgs
- **Tests:** 79 passing (17 Jun)
- **WhatsApp to James:** Sent 17 Jun PM with v1.1 summary

---

## 5) Honest gap analysis vs James's vision

James wants an **ARG / Asia Defense–style network dossier** — not just a single-entity federal pull:

```
James vision                          Today (v1.1)
─────────────────────────────────────────────────────────────
Click any name → full profile         Raw JSON at /entities/{id}, not linked
Relationship map on report            Separate /graph page only
Both parties on every factor          Partial on lobbying only
LinkedIn colleges + related parties   Not built
Person timeline + news + social       Not built
YouTube / interviews / books          Not built
PayPal Mafia as ONE network report    Individual seeds only
PDF export                            Not built
```

---

## 6) Apify research — unified vendor for Layer 2 (18 Jun)

**Decision:** Use **Apify** as primary enrichment vendor. `APIFY_API_TOKEN` is set locally in `.env` (not committed). One REST integration pattern for all actors.

### 6.1 Actor matrix (James requirements → Apify)

| James need | Apify actor | Pricing (approx) | Notes |
|------------|-------------|------------------|-------|
| **LinkedIn profiles** — education, experience | [`automation-lab/linkedin-profile-scraper`](https://apify.com/automation-lab/linkedin-profile-scraper) | ~**$0.003/profile** (~$5.20/1K); free tier ~50 profiles | No login; education array in output |
| **Company employees** | [`automation-lab/linkedin-company-employees-scraper`](https://apify.com/automation-lab/linkedin-company-employees-scraper) | ~**$0.005/employee**; cookie-free 50–100/company | Chain → profile scraper for education |
| **Bulk profile enrichment** (44 fields) | [`afanasenko/linkedin-profile-api-scraper`](https://apify.com/afanasenko/linkedin-profile-api-scraper) | **$0.03/profile** | Mode 3: decision-makers at company X |
| **PitchBook** — funding, investors, deals | [`mdataset/pitchbook-scraper`](https://apify.com/mdataset/pitchbook-scraper) | ~**$3.50/1K** (~$0.0035/lookup) | **No James API key needed** — public pages |
| **PitchBook investors** | [`crawlerbros/pitchbook-investors-scraper`](https://apify.com/crawlerbros/pitchbook-investors-scraper) | ~**$1.00/1K** | VC/PE fund profiles |
| **News / person timeline** | [`brilliant_gum/google-news-scraper`](https://apify.com/brilliant_gum/google-news-scraper) | **$0.03/article** | Person/company name queries |
| **YouTube** — interviews, documentaries | [`streamers/youtube-scraper`](https://apify.com/streamers/youtube-scraper) | ~**$5/1K videos** | Search by person name |
| **Social mentions** | [`magicfingers/social-listening-intelligence`](https://apify.com/magicfingers/social-listening-intelligence) | Pay-per-event | Reddit, HN, news, X mentions |

### 6.2 Integration pattern

```bash
POST https://api.apify.com/v2/acts/{actorId}/runs
Authorization: Bearer {APIFY_API_TOKEN}
# Poll run → GET /v2/datasets/{datasetId}/items
```

Python: `apify-client` package. Planned connector: `apps/api/app/connectors/apify_client.py`.

### 6.3 Cost estimate — PayPal Mafia demo spike

| Run | Items | Est. cost |
|-----|-------|-----------|
| 5 person LinkedIn profiles | 5 | ~$0.02 |
| Palantir employees (cookie-free) | ~100 | ~$0.50 |
| 5 PitchBook company lookups | 5 | ~$0.02 |
| 50 news articles × 5 people | 250 | ~$7.50 |
| 20 YouTube videos × 5 people | 100 | ~$0.50 |
| **Spike total** | | **~$8–10** |

Apify free tier: **$5/month** credit — enough for LinkedIn + PitchBook spike; news at scale needs paid plan (~$49/mo Personal).

### 6.4 Apify vs PDL (17 Jun recommendation)

| | **Apify** | **PDL** |
|---|-----------|---------|
| LinkedIn education | Live scrape ~$0.003/profile | Aggregated DB ~$0.28/lookup |
| PitchBook | ✅ Same platform | ❌ |
| News + YouTube | ✅ Same platform | ❌ |
| Legal posture | Scraping — James must sign off | Licensed API |
| **Status** | ✅ Token available — **start without James approval for spike** | Still valid fallback |

### 6.5 Legal / compliance (flag for James)

- LinkedIn actors scrape **public** profiles only; LinkedIn ToS restricts scraping — document use case and retention.
- PitchBook scrapers are community-maintained, not official PitchBook API.
- GDPR/CCPA applies to person data.

---

## 7) Revised technical approach (Apify-first)

```mermaid
flowchart LR
    A[Intelligence generate] --> B{entity_type}
    B -->|person| C[Apify LinkedIn Profile]
    B -->|org| D[Apify Company Employees]
    D --> E[Apify Profile batch]
    B --> F[Apify PitchBook]
    C --> G[Apify Google News]
    C --> H[Apify YouTube]
    E --> I[Merge + graph edges]
    F --> I
    G --> I
    H --> I
    I --> J[9+ section dossier + timeline + Cytoscape embed]
```

**Recommended actor picks:**
1. `automation-lab/linkedin-profile-scraper` — person seeds (education, experience)
2. `automation-lab/linkedin-company-employees-scraper` → profile scraper — company key people
3. `mdataset/pitchbook-scraper` — replaces blocked official PitchBook key
4. `brilliant_gum/google-news-scraper` + `streamers/youtube-scraper` — media + timeline

---

## 8) Project plan — phases & timelines

**Demo anchor throughout:** PayPal Mafia (Thiel, Musk, Hoffman, Levchin, Sacks, Palantir, Founders Fund, etc.)

| Phase | Dates (est.) | Deliverable | James sees |
|-------|--------------|-------------|------------|
| **1.2** | 18–24 Jun (~1 wk) | Two-sided disclosure; clickable entities in report; Cytoscape graph embed on dossier | Click Palantir → see agencies + lobbying firms on map |
| **2.0** | 25 Jun – 8 Jul (~2 wk) | Apify LinkedIn + PitchBook connectors; education/colleges; related parties; key-people auto-expand | Peter Thiel report shows Stanford, PayPal alumni, Founders Fund links |
| **2.1** | 9–22 Jul (~2 wk) | Person timeline service — career + filings + news + contracts chronologically | Thiel timeline: PayPal → Palantir → news hits |
| **2.2** | 23 Jul – 5 Aug (~2 wk) | Media layer — Apify news + YouTube; books/articles where public | § Media & Public Record with cited links |
| **2.3** | 6–26 Aug (~3 wk) | Full PayPal Mafia **network dossier** (one linked report); PDF export | Single multi-entity report matching ARG style |

**Total Layer 2 estimate:** ~10 weeks to James sign-off on full vision.

---

## 9) Delivery output expectations (for James)

| # | Output | Description | Target phase |
|---|--------|-------------|--------------|
| 1 | **Entity profile page** | Click any company/person → bio, IDs, education, contracts, lobbying, investors — polished UI | 1.2 + 2.0 |
| 2 | **Relationship map** | Interactive Cytoscape graph embedded on dossier; expand on click; export PNG/JSON | 1.2 |
| 3 | **Two-sided disclosure** | Lobbying (client + firm), contracts (agency + contractor), FEC/FARA both parties | 1.2 |
| 4 | **People & education** | Colleges, career history, related parties (Apify LinkedIn) | 2.0 |
| 5 | **Person timeline** | Dated events: career, news, filings, deals, social mentions — all cited | 2.1 |
| 6 | **Media section** | Articles, interviews, YouTube, books (where public) | 2.2 |
| 7 | **9+ section dossier** | Current Layer 1 + people + media sections; DOCUMENTED/REPORTED/ANALYTICAL tags | 2.2 |
| 8 | **Network dossier** | PayPal Mafia as one linked multi-entity report | 2.3 |
| 9 | **PDF export** | Downloadable, matching James's 15 PDF examples | 2.3 |

---

## 10) Pending tasks — priority stack

### P0 — This week (Phase 1.2)

| # | Task | Owner | Status |
|---|------|-------|--------|
| L2.1 | Two-sided disclosure — lobbying (client + registrant LDA), contracts, FEC | — | 🔲 |
| L2.2 | Clickable entity names in intelligence report → `/entities/{id}` | — | 🔲 |
| L2.3 | Embed Cytoscape relationship graph on `/intelligence` (reuse `/graph/export`) | — | 🔲 |
| L2.4 | Send James project plan + Apify approach WhatsApp | — | 🟡 **Today** |
| L2.5 | James sign-off on Apify scraping policy (LinkedIn + PitchBook) | James | 🔲 |

### P1 — Next 2 weeks (Phase 2.0 — Apify)

| # | Task | Owner | Status |
|---|------|-------|--------|
| L2.6 | `apify_client.py` connector + `APIFY_API_TOKEN` in `.env.example` | — | 🔲 |
| L2.7 | Apify LinkedIn profile scraper — education + experience for `entity_type=person` | — | 🔲 |
| L2.8 | Apify company employees → key people for org reports | — | 🔲 |
| L2.9 | Apify PitchBook scraper — funding rounds + investors | — | 🔲 |
| L2.10 | Key people extractor → auto-fetch related entities → graph edges | — | 🔲 |
| L2.11 | Spike: Peter Thiel LinkedIn URL on staging | — | 🔲 |

### P2 — Layer 2 media + network

| # | Task | Status |
|---|------|--------|
| L2.12 | Apify Google News — person/company timeline events | 🔲 |
| L2.13 | Apify YouTube — interviews, documentaries | 🔲 |
| L2.14 | Person timeline UI (merge career + filings + news) | 🔲 |
| L2.15 | Full PayPal Mafia multi-entity network report | 🔲 |
| L2.16 | PDF export matching James doc style | 🔲 |

### Done (17 Jun — do not regress)

| # | Task | Status |
|---|------|--------|
| L1.11 | LDA lobbying fix (`client_name`) | ✅ |
| L1.12 | Deep 5-section narrative | ✅ |
| L1.13 | PayPal Mafia seeds + 9-section report | ✅ |
| L1.14 | Wikipedia + FundedAPI + SEC 13G/Form D | ✅ |
| L1.18 | E2E Palantir + Peter Thiel on staging | ✅ |

### Deferred (unchanged)

| Item | Status |
|------|--------|
| CA SOS API (`calicodev.sos.ca.gov`) | ⏸️ Waiting on James |
| Cobalt Intelligence | ⏸️ Per James direction |
| OIDC Google SSO | ⏸️ Waiting on James |

---

## 11) Credentials & environment (18 Jun)

| Key | Status | Used for |
|-----|--------|----------|
| `OPENAI_API_KEY` | ✅ Set | Deep narrative |
| Federal connector keys | ✅ Set | SEC, FEC, LDA, USASpending, etc. |
| `ANTHROPIC_API_KEY` | ✅ Set | Skills (Claude) |
| `BEA_API_USER_ID` | ✅ Set | BEA economic data |
| **`APIFY_API_TOKEN`** | ✅ **Set locally** | LinkedIn, PitchBook, news, YouTube via Apify — **not wired in code yet** |
| `PITCHBOOK_API_KEY` | ❌ Not needed if Apify path | Official API optional |
| PDL API key | ❌ Not set | Fallback to Apify |
| `CA_SOS_API_KEY` | ⏸️ Deferred | James to provide |
| `COBALT_API_KEY` | ⏸️ Deferred | James to provide |
| `OIDC_*` | ❌ Missing | James to provide |

---

## 12) What we are doing today (18 Jun) — planning day

**No code today** — planning, documentation, alignment, James comms.

| # | Activity | Output |
|---|----------|--------|
| 1 | Create this handoff (`18th_June.md`) | ✅ |
| 2 | Consolidate all James 18 Jun messages + cross-verify vs codebase | ✅ §3 |
| 3 | Document Apify actor matrix + revised Layer 2 plan | ✅ §6–§9 |
| 4 | Prepare standup MOM + James WhatsApp (project plan + Apify) | §13–§14 |
| 5 | Get James sign-off on Apify scraping policy before production scale | 🔲 Send today |
| 6 | Update README pointer to `18th_June.md` as latest handoff | 🔲 Optional after James reply |

**Code starts next** (after today): Phase 1.2 — two-sided disclosure, clickable entities, graph embed — then Apify spike on Peter Thiel.

---

## 13) Standup MOM — 18 Jun

### Context
- v1.1 shipped and sent to James 17 Jun PM
- James replied 18 Jun AM with Layer 2 scope (8 new requirement areas)
- Apify token available — unblocks LinkedIn + PitchBook + media without waiting on James keys

### Done (carry from 17 Jun) ✅
- LDA fix — 504 Palantir filings
- Deep 5-section narrative
- PayPal Mafia seeds + 9-section report
- Wikipedia + FundedAPI + SEC 13G
- E2E verified on staging
- Apify Store research complete (LinkedIn, PitchBook, news, YouTube actors)

### Today (18 Jun) — planning & comms 📋
1. **`18th_June.md`** — full handoff with James messages, gaps, Apify plan, timelines
2. **Send James** — project plan + honest status on visualizers/media/LinkedIn + Apify proposal
3. **Align internally** — Phase 1.2 scope for rest of week (no code until plan approved)
4. **Legal flag** — Apify LinkedIn/PitchBook scraping needs James OK before production

### Next (19 Jun+) — build 🔨
1. Phase 1.2: two-sided disclosure + clickable entities + graph on dossier
2. Apify connector spike: Peter Thiel LinkedIn profile (education)
3. Apify PitchBook: Palantir funding history
4. Wire key-people → graph expansion

### Blockers
- James sign-off on Apify scraping policy (can spike on free tier meanwhile)
- CA SOS / Cobalt / OIDC — still deferred

---

## 14) Suggested WhatsApp to James (18 Jun — project plan)

> Hi James,
>
> Thanks for the detailed feedback this morning — we've mapped everything against what's live on staging. Honest status:
>
> *Already live (v1.1):* 9-section dossier, lobbying fix (504 Palantir filings), deep narrative, PayPal Mafia seeds, federal sources + Wikipedia + investors.
>
> *Your new asks — our plan:*
>
> **1. Both sides (lobbying, contracts)** — Partial today (client + firm in lobbying text). We'll add explicit two-sided blocks and registrant-side LDA queries this week.
>
> **2. Key people → relationship map + visualizers** — Graph backend exists; not on the report yet. This week: embed interactive relationship map on every dossier + auto-expand key people.
>
> **3. LinkedIn / colleges / related parties** — Researched Apify (we have API access). Can pull education, experience, and company employees without a separate LinkedIn API key. ~$0.003/profile. Need your OK on data-use policy (scraping vs official APIs).
>
> **4. Person timeline + news + YouTube** — Same Apify platform: Google News + YouTube scrapers for articles, interviews, documentaries. Building chronological timeline merging career + filings + news.
>
> **5. Click any entity** — Entity profile API exists; we'll make every name in reports clickable → profile + relationship view.
>
> **6. PitchBook** — Can use Apify PitchBook scraper (~$0.003/lookup) without your API key, or plug in official key if you prefer.
>
> *Timeline:* ~10 weeks to full vision; PayPal Mafia as demo throughout. Phase 1.2 (this week): two-sided disclosure + clickable entities + graph visualizer.
>
> *Need from you:* (1) OK on Apify for LinkedIn/PitchBook enrichment, (2) confirm PayPal Mafia as Layer 2 sign-off demo, (3) any budget cap on API spend (~$50–100/mo at demo scale).
>
> Full written plan available on request. Happy to jump on a call.

---

## 15) Files to create / change (upcoming — not today)

| File | Planned change |
|------|----------------|
| `apps/api/app/connectors/apify_client.py` | Apify REST wrapper |
| `apps/api/app/services/intelligence_service.py` | Apify fetchers; two-sided LDA; key-people expand |
| `apps/web/pages/intelligence.js` | Clickable entities; Cytoscape embed |
| `.env.example` | `APIFY_API_TOKEN` |
| `README.md` | Point to 18th_June.md; Layer 2 status |
| `tests/` | Apify mock tests; LDA registrant-side tests |

---

*End of 18 June handoff — Layer 2 planning; Apify path unblocked; awaiting James sign-off on scraping policy*
