# F-06 — Network Intelligence & Graph Analysis
## Future Enhancement — High Priority

**Date:** July 30, 2026  
**Prepared by:** Akash  
**Feature ID:** F-06  
**Priority:** 🔴 High — Direct client requirement  
**Status:** Awaiting Sprint Assignment  
**Estimated Effort:** 5–7 days  
**Branch:** `feature/network-intelligence` (to be created from `main`)

---

## 1. Client Request (Verbatim)

> *"I need you to get all data. Doesn't matter how long it is. Get all data. And then let's start analyzing it with other companies other investments that company has done, or the other investors in that round of investment; and see if there are any trends between investors, founder, employees, board seats etc."*

---

## 2. What the Client Wants — Plain English

The client wants a **relationship network analysis** feature. When you research any company on the platform, it should:

1. **Fetch everything** — no pagination limits, no truncation, pull ALL funding rounds, ALL investors, ALL employees, ALL board members
2. **Traverse connections** — for every investor found, look up what else they've invested in; for every board member, see what other boards they sit on
3. **Find patterns / trends** across:
   - Co-investors who repeatedly fund the same companies together
   - Founders who came from the same previous employer
   - Employees who moved between companies in the same investor's portfolio
   - Board members who hold seats at competing or complementary companies
   - Capital flows — same investor backing companies across the same sector

**Think of it like:** LinkedIn + Crunchbase + SEC filings merged into a network graph that answers: *"Who are the real power brokers connecting these companies, and what patterns exist between them?"*

---

## 3. Real-World Example of What This Produces

**Input:** Research "Palantir Technologies"

**What F-06 returns:**

```
Palantir Technologies (PLTR)
│
├── Investors
│   ├── Peter Thiel (also founder of: PayPal, Founders Fund, Palantir)
│   │       └── Also invested in: Facebook, SpaceX, Airbnb, Stripe, Anduril
│   │               → TREND: Thiel consistently backs defense-tech + fintech founders
│   ├── In-Q-Tel (CIA venture arm)
│   │       └── Also invested in: Keyhole (→ became Google Maps), Recorded Future
│   │               → TREND: Government intelligence pipeline — same LP (CIA) funds same thesis
│   └── Founders Fund
│           └── Portfolio overlaps with Peter Thiel personal investments in 8 companies
│                   → PATTERN: GP co-investing with own fund — potential conflict of interest signal
│
├── Board Members
│   ├── Alex Karp (CEO) — no outside board seats (founder-led)
│   ├── Peter Thiel — sits on board of: Palantir, Valar Ventures portfolio cos, Founders Fund
│   └── Alexandra Wolfe Schiff — board seat: Palantir, previously at Goldman Sachs
│           → PATTERN: Goldman → Palantir pipeline (board recruitment from big banks)
│
├── Founder Alumni Network
│   ├── Former Palantir employees who founded new companies:
│   │   ├── Anduril Industries (Palmer Luckey — Palantir investor Peter Thiel backed this too)
│   │   ├── Samsara (Sanjit Biswas — co-invested by same LP as Palantir Series A)
│   │   └── Skydio (ex-Palantir engineers)
│   │           → TREND: Palantir alumni consistently get backed by Thiel/Founders Fund network
│
└── Co-Investment Patterns
    ├── Thiel + In-Q-Tel appear together in: 4 companies
    ├── Thiel + Founders Fund appear together in: 12 companies
    └── → SIGNAL: When both Thiel + In-Q-Tel back a company, it correlates with
                  US government contract wins within 24 months (defense-tech pattern)
```

---

## 4. Why This is High Priority

| Reason | Detail |
|---|---|
| **Direct client ask** | Client explicitly asked for this in a message |
| **Differentiator** | No free platform does this. PitchBook charges $30k/year for this data |
| **Existing Graph page** | Platform already has `⬡ Graph` in the sidebar — this feature populates it with meaningful data |
| **APIs already in `.env`** | Apollo (`APOLLO_API_KEY`), Apify (`APIFY_API_TOKEN`), SEC EDGAR, GLEIF, FEC — all already configured |
| **Feeds multiple existing pages** | Company page, Politician page, Institutional page, Graph page all benefit |

---

## 5. What's Already Built That We Can Use

### 5.1 Existing APIs in `.env` (No new keys needed for MVP)

| Key in `.env` | What it provides for this feature |
|---|---|
| `APOLLO_API_KEY` | Person search — find founders, employees, their career history, current/past companies |
| `APIFY_API_TOKEN` | Web scraping — Crunchbase, LinkedIn, news — funding round data |
| `GLEIF_API_BASE_URL` | Global Legal Entity Identifier — company → subsidiary/parent relationships |
| `FEC_API_KEY` | Campaign contributions — who is donating to politicians, follow the money |
| `SEC_USER_AGENT` | EDGAR proxy filings (DEF 14A) — board member lists, executive compensation |
| `OPENCORPORATES_API_KEY` | (empty — free tier available) Company registry — directorship cross-refs |
| `UK_COMPANIES_HOUSE_KEY` | UK company directors — board cross-references for UK entities |
| `COBALT_API_KEY` | Cobalt Intelligence — business filings, registered agents |
| `COURTLISTENER_API_TOKEN` | Litigation graph — lawsuits connecting companies and people |

### 5.2 Existing Platform Pages That Benefit

| Page | What F-06 adds to it |
|---|---|
| `/graph` | Fully populate the network graph with real investor/founder/board relationships |
| `/market/company/deep-report` | Add "Network" tab — co-investors, board interlocks, alumni companies |
| `/market/gov-trading/politician/{id}` | Show which companies the politician's donors also invested in |
| `/institutional` | Show co-investment clusters — funds that consistently invest together |
| `/tracking` | Watchlist items: show which of your watched companies share investors/board members |

---

## 6. Feature Breakdown — What Needs to Be Built

### Module 1 — Full Data Fetch (No Truncation)
**Problem today:** Most connector functions use `limit=10` or `limit=20`. Client said "get ALL data."

**Files to change:**
- `apps/api/app/connectors/gov_trading_connector.py` — remove `limit=10` on legislation calls, paginate through all results
- `apps/api/app/connectors/institutional_tracker.py` — fetch all 13F positions, not just top holders
- Any new connectors built for this feature — must implement pagination loop

**Pattern to implement:**
```python
def fetch_all_paginated(url, params, key, api_key):
    """Loop through all pages and return complete dataset."""
    results = []
    offset = 0
    while True:
        params.update({"offset": offset, "limit": 250})
        r = requests.get(url, params=params)
        items = r.json().get(key, [])
        if not items:
            break
        results.extend(items)
        offset += len(items)
        if len(items) < 250:
            break
    return results
```

---

### Module 2 — Investor Network Connector
**New file:** `apps/api/app/connectors/investor_network_connector.py`

| Function | Data Source | What it returns |
|---|---|---|
| `get_company_investors(company_name)` | Apollo API + Apify/Crunchbase scrape | All investors by round with amounts |
| `get_investor_portfolio(investor_name)` | Apollo API | All companies that investor has backed |
| `get_coinvestors(company_name)` | Cross-ref from funding rounds | Other investors who appeared in same rounds |
| `get_coinvestment_patterns(investor_list)` | Internal cross-reference | Which investors repeatedly co-invest |
| `get_board_members(company_name)` | SEC EDGAR DEF 14A proxy filings | Full board with other seats held |
| `get_board_interlocks(board_member_name)` | SEC EDGAR + Apollo | All boards this person sits on |
| `get_founder_alumni(company_name)` | Apollo people search | Ex-employees who founded other companies |
| `get_employee_flow(company_a, company_b)` | Apollo career history | Employees who moved between two companies |

---

### Module 3 — Trend / Pattern Detection Engine
**New file:** `apps/api/app/services/network_analysis_service.py`

| Analysis | How it works | Output |
|---|---|---|
| **Co-investment clustering** | Find investors who appear together in ≥2 rounds | "Thiel + In-Q-Tel co-invested in 4 companies" |
| **Board interlock detection** | Person appears on boards of ≥2 companies | "John Smith sits on 3 boards in the same sector" |
| **Founder alumni tracking** | Ex-employee at Company A → founded Company B → funded by Company A's investor | "Alumni pipeline: Palantir → Anduril → Thiel" |
| **Sector concentration** | % of an investor's portfolio in one sector | "Sequoia: 38% of portfolio in SaaS B2B" |
| **Capital flow timeline** | When investor entered/exited positions | "A16Z led all 3 rounds at 12-month intervals" |
| **Conflict of interest flag** | Board member at company + investor in competitor | "⚠ Board member X also invested in direct competitor Y" |

---

### Module 4 — Graph Data API Endpoints
**File to update:** `apps/api/app/api/market.py`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/market/network/company/{name}` | Full network for a company — investors + board + alumni |
| `GET` | `/market/network/investor/{name}` | Investor's full portfolio + co-investor map |
| `GET` | `/market/network/person/{name}` | Person's full career + board seats + investment activity |
| `GET` | `/market/network/coinvestors/{company}` | All co-investors in any round for a company |
| `GET` | `/market/network/board-interlocks/{company}` | Board members and their other seats |
| `GET` | `/market/network/trends?companies=X,Y,Z` | Cross-company trend analysis |
| `GET` | `/market/network/graph/{entity}` | Graph format (nodes + edges) for frontend visualization |

**Response format for graph endpoint:**
```json
{
  "nodes": [
    {"id": "palantir", "type": "company", "label": "Palantir Technologies", "sector": "Defense Tech"},
    {"id": "thiel", "type": "person", "label": "Peter Thiel", "role": "investor+founder"},
    {"id": "anduril", "type": "company", "label": "Anduril Industries", "sector": "Defense Tech"}
  ],
  "edges": [
    {"from": "thiel", "to": "palantir", "type": "investor", "amount": "$10M", "round": "Series A"},
    {"from": "thiel", "to": "anduril", "type": "investor", "amount": "undisclosed"},
    {"from": "palantir", "to": "anduril", "type": "alumni_pipeline", "count": 12}
  ],
  "trends": [
    {"type": "co_investment_cluster", "label": "Thiel backs Palantir alumni companies", "confidence": 0.87},
    {"type": "board_interlock", "label": "3 board members overlap with In-Q-Tel portfolio", "confidence": 0.92}
  ]
}
```

---

### Module 5 — Frontend Graph Visualization
**File:** `apps/web/pages/graph.js` (already exists — needs data wired in)

| Component | What it shows |
|---|---|
| `NetworkGraph` | Force-directed graph using D3.js or Vis.js — nodes are people/companies, edges are relationships |
| `TrendPanel` | Right sidebar — list of detected patterns and what they mean |
| `EntitySearch` | Input: type any company/person name → loads their full network |
| `FilterControls` | Toggle: show/hide investors, board members, employees, alumni |
| `TimelineSlider` | Scrub through time — see how the network evolved across funding rounds |
| `ConflictHighlighter` | Red highlight on edges where conflict of interest is detected |

---

## 7. Data Flow — How It All Connects

```
User searches: "Palantir" on /graph page
        │
        ▼
GET /market/network/graph/palantir
        │
        ▼
network_analysis_service.build_graph("palantir")
        │
        ├── investor_network_connector.get_company_investors("palantir")
        │       → Apollo API: funding rounds + investors
        │
        ├── investor_network_connector.get_board_members("palantir")
        │       → SEC EDGAR DEF 14A proxy filing parser
        │
        ├── investor_network_connector.get_founder_alumni("palantir")
        │       → Apollo people search: past employees + their current companies
        │
        ├── For each investor found:
        │       → investor_network_connector.get_investor_portfolio(investor)
        │               → Apollo: all their other portfolio companies
        │
        ├── network_analysis_service.detect_patterns(all_data)
        │       → Co-investment clustering
        │       → Board interlock detection
        │       → Alumni pipeline detection
        │
        └── Returns: { nodes[], edges[], trends[] }
                │
                ▼
        Frontend: renders force-directed graph
        + highlights detected patterns in sidebar
```

---

## 8. Effort Estimate

| Task | Effort |
|---|---|
| Module 1: Fix pagination in existing connectors | 0.5 day |
| Module 2: `investor_network_connector.py` — all 8 functions | 1.5 days |
| Module 3: `network_analysis_service.py` — pattern detection | 1 day |
| Module 4: 7 new API endpoints in `market.py` | 0.5 day |
| Module 5: Frontend graph visualization on `/graph` page | 2 days |
| Testing + edge cases + documentation | 0.5 day |
| **Total** | **~6 days** |

---

## 9. Implementation Plan (Day by Day)

```
Day 1 — Backend Foundations
  ├── Fix pagination in existing connectors (no more limit=10)
  ├── Create investor_network_connector.py skeleton
  └── Implement get_company_investors() + get_board_members() using Apollo + SEC EDGAR

Day 2 — Relationship Data
  ├── Implement get_investor_portfolio() + get_coinvestors()
  ├── Implement get_founder_alumni() using Apollo people search
  └── Write unit tests for each function

Day 3 — Pattern Detection
  ├── Create network_analysis_service.py
  ├── Implement co-investment clustering algorithm
  ├── Implement board interlock detection
  └── Implement conflict of interest flagging

Day 4 — API Endpoints
  ├── Add all 7 new endpoints to market.py
  ├── Add /market/network/graph/{entity} with node/edge/trend response
  └── Test all endpoints manually via API docs

Day 5 — Frontend
  ├── Wire /graph page to new endpoints
  ├── Add D3.js / Vis.js force-directed graph component
  └── Add TrendPanel sidebar for pattern display

Day 6 — Polish + Docs
  ├── Add FilterControls and ConflictHighlighter
  ├── Handle edge cases (unknown entities, API timeouts)
  ├── Update API_INTEGRATIONS_GUIDE.md
  └── Update README and this document with final status
```

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Apollo API rate limits on bulk people searches | Medium | Medium | Cache results in DB, TTL 24h |
| Crunchbase funding data behind paywall | High | Medium | Use Apify scrape + fallback to SEC EDGAR filings |
| Graph gets too large to render in browser | Medium | Low | Limit to 2-hop traversal, add pagination in graph view |
| SEC EDGAR DEF 14A parsing is complex XML | Medium | Medium | Use existing EDGAR connector pattern already in codebase |
| Person name matching ambiguity (multiple "John Smith") | High | Low | Match on company + role + date to disambiguate |

---

## 11. APIs Used — Already in `.env`

| API | Key in `.env` | Used For |
|---|---|---|
| Apollo.io | `APOLLO_API_KEY` | People search, career history, current/past employers |
| Apify | `APIFY_API_TOKEN` | Crunchbase + LinkedIn scraping for funding round data |
| SEC EDGAR | `SEC_USER_AGENT` | DEF 14A proxy filings for board member lists |
| GLEIF | `GLEIF_API_BASE_URL` | Parent/subsidiary company relationships |
| FEC | `FEC_API_KEY` | Campaign donations — money flow from investors to politicians |
| CourtListener | `COURTLISTENER_API_TOKEN` | Litigation connections between companies/people |
| UK Companies House | `UK_COMPANIES_HOUSE_KEY` | Director cross-references for UK entities |
| OpenCorporates | `OPENCORPORATES_API_KEY` | *(empty — free tier available)* Global company directorships |

**New keys needed:** None for MVP. OpenCorporates free tier covers basic directorship data.

---

## 12. Competitive Landscape — Why This Matters

| Platform | Cost | What it does |
|---|---|---|
| PitchBook | $30,000/year | Funding rounds, investors, board members, network graph |
| Crunchbase Pro | $5,000/year | Funding data, investor portfolios, founder tracking |
| LinkedIn Premium | $1,200/year | Career history, board seats (but no investment data) |
| Bloomberg Terminal | $24,000/year | Everything — but siloed, no cross-platform graph |
| **Our platform (F-06)** | **Free to user** | Same network graph, cross-referenced with gov trading, legislation, and SEC filings |

**Our unique angle:** No other platform cross-references investor networks WITH congressional stock trades AND legislation sponsorship AND litigation history in one view. That's the moat.

---

## 13. Approval Checklist

- [ ] Lead reviews and approves this document
- [ ] Sprint date assigned for F-06
- [ ] Confirm: Apollo API key has sufficient quota for bulk people searches
- [ ] Confirm: D3.js or Vis.js approved for frontend graph library
- [ ] Confirm: 2-hop traversal limit is acceptable (or client wants deeper)
- [ ] Confirm: Should conflict-of-interest flags trigger email alerts (F-03/F-04 style)?

---

## 14. Related Documents

| Document | Location |
|---|---|
| F-03/F-04 Architecture (Big Trade Alerts) | `docs/features/FEATURE_BIG_TRADE_ALERTS_ARCHITECTURE.md` |
| Congress.gov Upgrade Plan (F-05) | `docs/api/CONGRESS_GOV_LEGISLATION_UPGRADE.md` |
| API Integrations Guide | `docs/api/API_INTEGRATIONS_GUIDE.md` |
| Project Deep Analysis | `docs/architecture/PROJECT_DEEP_ANALYSIS.md` |
| Platform Handoff Document | `docs/handoff/Finance_Platform_Handoff.md` |

---

*This feature was identified from a direct client request on July 30, 2026. Priority classification: High — client-driven requirement with clear business value and no additional API costs required for MVP.*
