# Congress.gov Full Legislation Integration — Feature Proposal & Approval Document

**Date:** July 29, 2026  
**Prepared by:** Akash  
**Feature ID:** F-05  
**Status:** Awaiting Lead Approval  
**Branch:** `feature/congress-legislation` (to be created from `main`)

---

## 1. Executive Summary

The platform currently integrates Congress.gov using a **`DEMO_KEY`** — a public demo token with severe rate limits that make the feature unreliable in any real usage scenario. A registered **free API key** (`CONGRESS_API_KEY`) already exists in our `.env` file but is **not being used** — the connector still hardcodes `DEMO_KEY` in two places.

This feature proposal covers:
1. **Immediate fix:** Replace `DEMO_KEY` with our existing `CONGRESS_API_KEY` (2-line change, ~15 min effort).
2. **Full upgrade:** Add 5 new Congress.gov endpoints to the platform — bill search, vote records, committee tracking, upcoming laws tracker, and CRS policy reports.

---

## 2. What is Congress.gov?

Congress.gov is the **official public legislative database** of the United States, run by the Library of Congress. It contains every bill, law, vote, amendment, committee report, and congressional member's activity since the founding of Congress.

The **Congress.gov API v3** exposes all of this data as structured JSON. It is:

- **Completely free** — no paid tier exists. Everyone gets the same data.
- **Official government data** — not scraped, not third-party. Primary source.
- **Updated in near real-time** — new bills, votes, and actions appear within hours.
- **Covers history** — data going back to the 1970s for most collections.

**Sign-up:** https://api.congress.gov/sign-up/  
**Base URL:** `https://api.congress.gov/v3/`  
**Official Docs/GitHub:** https://github.com/LibraryOfCongress/api.congress.gov

---

## 3. Why It Matters for a Finance Research Platform

Congressional legislation **directly moves markets**. Every bill that gets introduced, advances through committee, or passes into law creates measurable price impacts:

| Market Event | Legislative Trigger | Example |
|---|---|---|
| Pharma stock drops 8% | Drug pricing bill introduced in Senate | IRA 2022 — Medicare drug negotiation |
| Defense contractor surges | Defense authorization bill passed | NDAA annual — LMT, RTX, NOC |
| Semiconductor stock moves | Chip export control bill | CHIPS Act 2022 — NVDA, AMD, INTC |
| Bank stock selloff | Banking regulation markup begins | SVB aftermath bills |
| Oil company rally | Energy permitting reform passes | Pipeline approval legislation |
| Tech regulation selloff | Antitrust bill scheduled for vote | META, GOOGL, AMZN |

**Without Congress.gov data, our platform is flying blind on one of the most important market-moving data sources.**

---

## 4. Current State — What Is Already Built

### 4.1 What Works Today

The platform already has a `get_politician_profile()` function in `gov_trading_connector.py` that calls Congress.gov to fetch a politician's sponsored legislation. This data is returned on the `/market/gov-trading/politician/{name}` API endpoint and displayed on the politician profile page.

**File:** `apps/api/app/connectors/gov_trading_connector.py`  
**Function:** `get_politician_profile()` — lines 376–521

The function:
1. Looks up a politician by name in our `TRACKED_POLITICIANS` dictionary
2. Fetches their PTR filings (STOCK Act trades) from House Clerk ZIP files
3. Calls Congress.gov to get their `bioguideId`
4. Calls Congress.gov to get their sponsored legislation (recent 10 bills)
5. Cross-references bill topics with their traded tickers (finance, defense, tech, health keywords)
6. Returns a combined `financially_relevant_legislation` list

### 4.2 The Problem — DEMO_KEY Hardcoded

The Congress.gov calls in the connector use `"DEMO_KEY"` hardcoded — **not the real key from `.env`**:

```python
# gov_trading_connector.py — Line 404 (BROKEN for production use)
r = req.get(
    "https://api.congress.gov/v3/member",
    params={"api_key": "DEMO_KEY", "format": "json", "limit": 250},  # ← DEMO_KEY
    ...
)

# gov_trading_connector.py — Line 420 (BROKEN for production use)
leg_r = req.get(
    f"https://api.congress.gov/v3/member/{bioguide_id}/sponsored-legislation",
    params={"api_key": "DEMO_KEY", "format": "json", "limit": 10},  # ← DEMO_KEY
    ...
)
```

### 4.3 The Real Key Already Exists

Our `.env` file (line 65) already has the real key:

```env
# .env — line 65
CONGRESS_API_KEY=Nucw7ny0IG6Y2EXAFQh4O2z7bCgMEPULvxqzD95g
```

It is just **not being read**. This is purely an oversight from initial development.

---

## 5. DEMO_KEY vs Real Key — Rate Limit Comparison

| | `DEMO_KEY` | Real `CONGRESS_API_KEY` |
|---|---|---|
| **Requests per hour** | **30 per IP** | **1,000 per hour** |
| **Requests per day** | **50 per IP** | No daily cap |
| **Shared across all users?** | Yes — all users on same IP share 30 req/hr | No — key-based, private |
| **HTTP error when exceeded** | `429 Too Many Requests` | `429` only after 1,000/hr |
| **Suitable for production?** | No | Yes |
| **Suitable for multi-user app?** | No — 2 simultaneous users breaks it | Yes |

**Impact on our platform today:** Every time a user opens a politician profile page AND Congress.gov has already been called 30 times that hour (by cron jobs, other users, or our own dev testing), the `legislation` field in the response returns empty `[]`. The user sees a politician profile with no legislation data — silently broken with no error shown.

---

## 6. Proposed Changes

### Phase 1 — Immediate Fix (Effort: 15 minutes)

**Change 1 of 3:** Read `CONGRESS_API_KEY` from environment in `gov_trading_connector.py`

**File:** `apps/api/app/connectors/gov_trading_connector.py`

**Current code (lines 401–407):**
```python
import requests as req
r = req.get(
    f"https://api.congress.gov/v3/member",
    params={"api_key": "DEMO_KEY", "format": "json", "limit": 250},
    headers={"User-Agent": "Finance-Platform/1.0"},
    timeout=10
)
```

**Proposed code:**
```python
import requests as req
congress_api_key = os.environ.get("CONGRESS_API_KEY", "DEMO_KEY")
r = req.get(
    "https://api.congress.gov/v3/member",
    params={"api_key": congress_api_key, "format": "json", "limit": 250},
    headers={"User-Agent": "Finance-Platform/1.0"},
    timeout=10
)
```

**Change 2 of 3:** Same fix for the `sponsored-legislation` call (line 418–423):

**Current code:**
```python
leg_r = req.get(
    f"https://api.congress.gov/v3/member/{bioguide_id}/sponsored-legislation",
    params={"api_key": "DEMO_KEY", "format": "json", "limit": 10},
    headers={"User-Agent": "Finance-Platform/1.0"},
    timeout=10
)
```

**Proposed code:**
```python
leg_r = req.get(
    f"https://api.congress.gov/v3/member/{bioguide_id}/sponsored-legislation",
    params={"api_key": congress_api_key, "format": "json", "limit": 10},
    headers={"User-Agent": "Finance-Platform/1.0"},
    timeout=10
)
```

**Change 3 of 3:** Update `Finance_Platform_Handoff.md` status table

**Current:**
```
| CONGRESS_API_KEY | Congress.gov | ✅ DEMO | Limited — needs paid key for full data |
```

**Proposed:**
```
| CONGRESS_API_KEY | Congress.gov | ✅ Live | 1,000 req/hr — politician legislation data |
```

---

### Phase 2 — Full Legislation Feature Upgrade (Effort: 2–3 days)

This phase adds new endpoints to expose the full power of Congress.gov data.

#### 6.2.1 New Connector Functions (gov_trading_connector.py)

| Function | Congress.gov Endpoint Called | Purpose |
|---|---|---|
| `search_bills(query, from_date, to_date, limit)` | `GET /v3/bill?query=...` | Free-text bill search — "AI regulation", "banking", "crypto" |
| `get_bill_details(congress, bill_type, bill_number)` | `GET /v3/bill/{congress}/{type}/{number}` | Full bill info — text versions, actions timeline, cosponsors |
| `get_bill_text(congress, bill_type, bill_number)` | `GET /v3/bill/{congress}/{type}/{number}/text` | Actual bill text versions (XML/PDF links) |
| `get_member_votes(bioguide_id, limit)` | `GET /v3/member/{bioguideId}/sponsored-legislation` + roll call cross-ref | How a member voted on specific bills |
| `get_committee_bills(chamber, committee_code)` | `GET /v3/committee/{chamber}/{code}/bills` | All bills under a specific committee (e.g., Senate Banking) |
| `get_recent_laws(congress)` | `GET /v3/law/{congress}` | Bills that became actual laws |
| `get_bill_cosponsors(congress, bill_type, bill_number)` | `GET /v3/bill/{congress}/{type}/{number}/cosponsors` | Members who co-signed a bill |
| `get_crs_reports(limit)` | `GET /v3/crsreport` | Congressional Research Service deep-dive policy reports |

#### 6.2.2 New API Endpoints (market.py)

| Method | Path | Description |
|---|---|---|
| `GET` | `/market/gov-trading/legislation/search` | Search bills by keyword/date range |
| `GET` | `/market/gov-trading/legislation/bill/{congress}/{type}/{number}` | Full bill detail |
| `GET` | `/market/gov-trading/legislation/laws/{congress}` | Recent enacted laws |
| `GET` | `/market/gov-trading/legislation/committee/{chamber}/{code}` | All bills in a committee |
| `GET` | `/market/gov-trading/legislation/crs-reports` | Policy research reports |
| `GET` | `/market/gov-trading/politician/{name}/votes` | How politician voted on bills |

#### 6.2.3 New UI Additions (apps/web)

| Component | Location | What it shows |
|---|---|---|
| `LegislationSearch` | `/gov-trading` page | Search box for bills — returns list with status badge (Introduced / Committee / Passed / Law) |
| `BillImpactBadge` | Company deep-report page | Shows pending bills that mention the company's sector |
| `PoliticianVoteRecord` | `/gov-trading/politician/{name}` | Voting history tab alongside existing trade history |
| `UpcomingLawsAlert` | Dashboard or Tracking page | Bills that passed committee — likely to become law soon |

---

## 7. Business Value & Benefits

### 7.1 For the Platform Users
- **Alpha signal:** Know what legislation is coming before it's priced in. A bill in committee is not yet market news — by the time it passes, the move is over.
- **Corruption cross-reference:** See if a politician bought a stock the same week they co-sponsored a bill benefiting that company.
- **Sector risk map:** Before investing in any sector, see what regulatory bills are in pipeline.
- **Policy research:** CRS reports are the most authoritative non-partisan analysis of legislation impacts. No subscription needed.

### 7.2 For the Platform Business
- **Competitive differentiation:** Most retail finance platforms show stock prices. We show the legislation that will move those prices before they move.
- **Data completeness:** Politician profile page today returns empty `legislation: []` for many users. This is a visible data gap that damages credibility.
- **No additional cost:** The API is entirely free. Only engineering time required.
- **Unique feature:** Very few platforms cross-reference stock trades with bills sponsored by the same politician who made the trade.

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Congress.gov API goes down | Low (government SLA) | Medium — legislation shows empty | Graceful fallback: return cached data or `{}` with no crash |
| Rate limit exceeded (1,000/hr) | Very Low — we make ~5–20 calls/hr currently | Medium | Add module-level TTL cache (already pattern used in connector) |
| Bill text too large to display | Medium | Low | Show summary + link to full text on congress.gov |
| Politician name matching fails (e.g., "MTG" vs "Marjorie Taylor Greene") | Medium | Low — only affects politician profile search | Normalize names using `bioguideId` lookup |

---

## 9. What Files Change

### Phase 1 (Immediate — 2 lines changed)

| File | Change | Lines Affected |
|---|---|---|
| `apps/api/app/connectors/gov_trading_connector.py` | Replace `"DEMO_KEY"` with `os.environ.get("CONGRESS_API_KEY", "DEMO_KEY")` | Lines 404, 420 |
| `Finance_Platform_Handoff.md` | Update status from `DEMO` to `Live` | Line 281 |

### Phase 2 (Full Feature — new endpoints + UI)

| File | Change Type | Description |
|---|---|---|
| `apps/api/app/connectors/gov_trading_connector.py` | Add functions | 8 new connector functions (see §6.2.1) |
| `apps/api/app/api/market.py` | Add endpoints | 6 new API routes (see §6.2.2) |
| `apps/web/pages/gov-trading/index.js` (or existing page) | Add component | `LegislationSearch` component |
| `apps/web/pages/gov-trading/[politician].js` | Add tab | `PoliticianVoteRecord` voting history tab |
| `apps/web/components/BillImpactBadge.js` | New component | Bill risk badge for company pages |
| `.env.example` | Update comment | Clarify `CONGRESS_API_KEY` is already sufficient — no paid key needed |
| `docs/API_INTEGRATIONS_GUIDE.md` | Update section | Add new Congress.gov endpoints detail |
| `Finance_Platform_Handoff.md` | Update feature status table | Mark F-05 progress |

---

## 10. Effort Estimate

| Phase | Task | Effort |
|---|---|---|
| **Phase 1** | Replace 2 hardcoded DEMO_KEY strings + test | **15 minutes** |
| **Phase 2** | Write 8 connector functions | 4 hours |
| **Phase 2** | Write 6 API endpoints | 2 hours |
| **Phase 2** | Frontend: LegislationSearch component | 3 hours |
| **Phase 2** | Frontend: Politician vote history tab | 2 hours |
| **Phase 2** | Frontend: BillImpactBadge on company page | 2 hours |
| **Phase 2** | Testing + edge cases + docs update | 2 hours |
| **Total Phase 1** | | **~15 min** |
| **Total Phase 2** | | **~2–3 days** |

---

## 11. Implementation Plan

```
Day 0 (today):
  ├── Phase 1 fix: replace DEMO_KEY → CONGRESS_API_KEY (15 min)
  ├── Create branch: feature/congress-legislation
  └── Verify politician profile returns legislation data

Day 1:
  ├── Add search_bills(), get_bill_details(), get_recent_laws() connector functions
  ├── Add /legislation/search and /legislation/laws API endpoints
  └── Manual test via curl / API docs

Day 2:
  ├── Add committee tracking and CRS report connector + endpoints
  ├── Add politician vote cross-reference connector
  ├── Build LegislationSearch UI component
  └── Wire up to /gov-trading page

Day 3:
  ├── Add PoliticianVoteRecord tab on politician page
  ├── Add BillImpactBadge on company deep-report
  ├── Full end-to-end test
  └── Update documentation + push PR for review
```

---

## 12. What Congress.gov API Can NOT Do

This is important to set correct expectations:

| Limitation | Detail |
|---|---|
| **No Senate PTR stock trades** | Stock trades by Senators use a separate system (eFD / Senate eFiling). Congress.gov does not expose trade data. |
| **No real-time vote alerts** | The API is updated periodically — not a live WebSocket feed. Votes appear within a few hours. |
| **No campaign finance** | PAC donations and contributions come from FEC, not Congress.gov. We have `FEC_API_KEY` for that. |
| **No lobbying data** | Lobbying disclosures come from Senate SOPR. Separate API. |
| **Bill text is PDF/XML links** | Full text is provided as external document links, not inline JSON. |

---

## 13. Approval Checklist

- [ ] Lead reviews and approves this document
- [ ] Phase 1 fix approved to merge immediately (2-line change, no new deps)
- [ ] Phase 2 scope confirmed (full feature or partial?)
- [ ] Timeline confirmed for Phase 2 sprint
- [ ] Any additional security review required?

---

## 14. Quick Reference — Congress.gov API Endpoints Used

| Endpoint | Method | What we call it for |
|---|---|---|
| `/v3/member` | GET | Find politician's `bioguideId` by name |
| `/v3/member/{bioguideId}/sponsored-legislation` | GET | Bills a politician introduced |
| `/v3/member/{bioguideId}/cosponsored-legislation` | GET | Bills a politician co-signed |
| `/v3/bill` | GET | Search bills by keyword / date |
| `/v3/bill/{congress}/{type}/{number}` | GET | Full bill details |
| `/v3/bill/{congress}/{type}/{number}/text` | GET | Bill text version links |
| `/v3/bill/{congress}/{type}/{number}/cosponsors` | GET | All co-signers of a bill |
| `/v3/law/{congress}` | GET | Laws enacted in a congress |
| `/v3/committee/{chamber}/{code}/bills` | GET | Bills assigned to a committee |
| `/v3/crsreport` | GET | Policy research reports |

---

*Document prepared for lead approval. All data sourced from Library of Congress official API documentation (https://github.com/LibraryOfCongress/api.congress.gov) and api.data.gov rate limit documentation. Rate limits verified as of July 2026.*
