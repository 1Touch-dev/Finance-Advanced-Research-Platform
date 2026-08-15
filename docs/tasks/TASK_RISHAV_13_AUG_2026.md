# Task Assignment — Rishav (13 August 2026)

**Branch:** `feature/entity-timeline-stock-overlay`  
**Base from:** `8th-july-sprint` (after merging your `feature/intelligence-correlation-full`)  
**Effort:** 2–3 days  
**Type:** Full-stack (Backend + Frontend) — No AI/ML

---

## Previous Work — VERIFIED ✅

Your `feature/intelligence-correlation-full` branch (commit `8ead589`) is verified complete:
- `intelligence_activation_service.py` — 1659 lines, full orchestrator
- 5 frontend pages (self-dealing, network, correlation, contract-probability, interactive-report)
- Shared component library (`ActivationShared.js`)
- 39 regression tests (`test_intelligence_correlation_api.py`)
- Connector hardening (FPDS, OpenSecrets, SEC EDGAR, timeline)
- +6300 / -379 lines across 23 files

**Status:** Ready to merge into `8th-july-sprint`.

---

## New Task: Interactive Entity Timeline with Stock Price Overlay

### What James Asked (multiple times)

> *"need stock price during timeline"* (14 Jul)  
> *"should be clickable to view what happened or why, and news regarding"* (14 Jul)  
> *"timelines, and find all news related to them during that time. Come up with summaries"* (16 Jul)  
> *"a timeline would be great on news, valuations, etc. Adding tables graphs visualization"* (29 Jul)  

### What Exists Today

| Component | Status | Location |
|-----------|--------|----------|
| `timeline_connector.py` | ✅ Backend logic exists (you just hardened it) | `apps/api/app/connectors/timeline_connector.py` |
| `generate_entity_timeline()` | ✅ Aggregates SEC, insider, stock, 8-K events | Same file, line 522 |
| `generate_event_chronology()` | ✅ Date-range filtering | Same file |
| `timeline.js` (frontend) | ⚠️ **DEMO DATA ONLY** — hardcoded Peter Thiel/Palantir events, NOT wired to backend | `apps/web/pages/timeline.js` |
| `GET /entities/{entity_id}/timeline` | ⚠️ Exists but reads from DB `evidence_refs` only (no connector data) | `apps/api/app/api/search.py:88` |
| `GET /company/analyst-timeline/{ticker}` | ✅ Works (analyst upgrades/downgrades only) | `apps/api/app/api/market.py:1033` |
| Stock price history | ✅ `yfinance` available, used in `market_data_connector.py`, `valuation_connector.py` | Multiple connectors |
| Recharts | ✅ Installed, used in `stock.js` and `entities/[id].js` | `apps/web/pages/stock.js` |

### The Gap

The backend timeline engine (`timeline_connector.py`) is never called from a dedicated API route that the frontend can consume. The frontend page (`timeline.js`) is a hardcoded demo. **This task wires them together and adds the stock price chart overlay.**

---

## Deliverables (in order)

### 1. Backend — New API Route `GET /intelligence/timeline/{ticker}`

**File:** `apps/api/app/api/intelligence.py` (add to existing router)

**Spec:**
```
GET /intelligence/timeline/{ticker}?years=2&categories=financial,insider,legal&include_price=true
```

**Response shape:**
```json
{
  "ticker": "NVDA",
  "entity_name": "NVIDIA Corporation",
  "period": { "start": "2024-08-13", "end": "2026-08-13" },
  "events": [
    {
      "id": "evt_001",
      "date": "2026-07-15",
      "category": "insider",
      "title": "Form 4 — Jensen Huang sold 240,000 shares",
      "description": "CEO sold shares under 10b5-1 plan at avg $135.20",
      "significance": 7,
      "source": "SEC EDGAR",
      "source_url": "https://www.sec.gov/cgi-bin/...",
      "related_price": { "close": 134.50, "change_pct": -2.1 }
    }
  ],
  "price_series": [
    { "date": "2024-08-13", "close": 109.21, "volume": 312000000 },
    { "date": "2024-08-14", "close": 110.45, "volume": 285000000 }
  ],
  "summary": {
    "total_events": 47,
    "by_category": { "financial": 12, "insider": 18, "legal": 3, ... },
    "most_significant": [ /* top 5 by significance score */ ]
  }
}
```

**Implementation notes:**
- Call `generate_entity_timeline(ticker, years=years, include_price=include_price, include_insider=True)` from `timeline_connector.py`
- For `price_series`: use `yfinance.download(ticker, period=f"{years}y", interval="1d")` — daily OHLCV, return only `date` + `close` + `volume` (keep payload small)
- Add `categories` query param to filter event types
- Add `significance_min` query param (default 0) to filter noise
- Timeout: wrap in `_call_with_timeout` pattern (you already know this from your activation service)
- Return partial results if some sources fail (same fail-soft you did for correlation)

### 2. Backend — New API Route `GET /intelligence/timeline/{ticker}/compare`

**Spec:**
```
GET /intelligence/timeline/{ticker}/compare?against=AMD,INTC&years=1
```

**Response:** Same shape but `events` merged from all tickers, each tagged with `ticker` field. `price_series` becomes array of series per ticker (for overlay chart).

**Implementation:** Call `compare_entity_timelines([ticker, *against], years=years)` from `timeline_connector.py` (already exists!).

### 3. Frontend — Rewrite `apps/web/pages/timeline.js`

**Replace the hardcoded demo with a real page. Structure:**

```
┌─────────────────────────────────────────────────────────────┐
│  [Search: ticker/company name]  [Years: 1/2/5]  [Compare+]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─ STOCK PRICE CHART (Recharts AreaChart) ────────────┐  │
│   │  Line: daily close price                            │  │
│   │  Markers: event dots on the price line (colored     │  │
│   │           by category, sized by significance)       │  │
│   │  Hover: tooltip with event title + price change     │  │
│   └─────────────────────────────────────────────────────┘  │
│                                                             │
│   [Filter pills: All | Financial | Insider | Legal | ...]   │
│                                                             │
│   ┌─ EVENT LIST (chronological, newest first) ──────────┐  │
│   │  📊 2026-07-15 | INSIDER | Form 4 — Jensen Huang..  │  │
│   │     CEO sold 240K shares @ $135.20 (10b5-1 plan)    │  │
│   │     Stock: $134.50 (-2.1%)  [View Source →]          │  │
│   │                                                      │  │
│   │  📄 2026-07-01 | FINANCIAL | 10-Q Filed (Q2 2026)   │  │
│   │     Revenue $30.04B (+122% YoY)                      │  │
│   │     Stock: $128.00 (+4.3%)  [View Source →]          │  │
│   └──────────────────────────────────────────────────────┘  │
│                                                             │
│   [Load More]                                               │
└─────────────────────────────────────────────────────────────┘
```

**Key requirements:**
- **Recharts `ComposedChart`** with `Area` (price) + `Scatter` (events as dots)
- **Category filter pills** (same `CATEGORIES` config that already exists in the current `timeline.js`)
- **Clickable events** — click an event dot on the chart → scrolls to that event in the list below
- **Click event card** → opens `source_url` in new tab
- **Compare mode** — toggle to add a second ticker, shows two price lines
- **Responsive** — works on mobile (your `ActivationShared` patterns are fine to reuse)
- **Loading/empty states** — reuse your `EmptyState`, `Notice` from `ActivationShared.js`
- **URL state** — `?ticker=NVDA&years=2` so links are shareable

**Styling:** Use your existing `IntelligenceActivation.module.css` patterns or extend `Timeline.module.css` (already exists at `apps/web/src/styles/Timeline.module.css`).

### 4. Frontend — Wire into Layout Navigation

**File:** `apps/web/src/components/Layout.js`

Add "Timeline" to the Intelligence section in the sidebar nav (you know where — you just modified this file in your correlation commit).

### 5. Tests

**File:** `tests/test_timeline_api.py`

Write 8-12 tests covering:
- Happy path: returns events + price series for valid ticker
- Category filtering works
- `years` parameter respected
- Compare endpoint merges events from multiple tickers
- Invalid ticker returns 404 or empty
- Timeout handling (mock a slow connector)
- `significance_min` filtering
- Partial results when one source fails

---

## What NOT to Do

- ❌ No AI/ML work
- ❌ No new external API integrations (all data sources already exist)
- ❌ Don't touch the RAG or quality-gate code
- ❌ Don't modify `intelligence_activation_service.py` (it's done)
- ❌ Don't spend time on the "deep research agent" orchestration (that's a separate task)

---

## Files You'll Touch

| File | Action |
|------|--------|
| `apps/api/app/api/intelligence.py` | Add 2 new route handlers |
| `apps/web/pages/timeline.js` | **Rewrite** (replace demo data with real API calls + chart) |
| `apps/web/src/styles/Timeline.module.css` | Extend with chart + event card styles |
| `apps/web/src/components/Layout.js` | Add nav link |
| `apps/web/lib/intelligence.js` | Add `fetchTimeline()` and `fetchTimelineCompare()` helpers |
| `tests/test_timeline_api.py` | New file, 8-12 tests |

---

## Existing Code to Reuse

| What | Where | How |
|------|-------|-----|
| Timeline aggregation engine | `apps/api/app/connectors/timeline_connector.py` → `generate_entity_timeline()` | Call directly from new route |
| Compare timelines | Same file → `compare_entity_timelines()` | Call from compare route |
| Stock price data | `yfinance` (already in deps) or `market_data_connector.py` | Import and use |
| Recharts (charting) | Already installed, see `apps/web/pages/stock.js` for usage pattern | Copy the `AreaChart` pattern |
| Event categories + colors | Already defined in current `timeline.js` lines 14-22 (`CATEGORIES` array) | Keep them |
| Shared UI components | Your own `ActivationShared.js` (EmptyState, Notice, SectionCard, etc.) | Import |
| Timeout + partial results | Your `_call_with_timeout` / `_run_bounded_source_jobs` pattern from `intelligence_activation_service.py` | Same pattern |
| Insider transactions | `sec_edgar_connector.py` → `get_insider_transactions()` | Already called by timeline_connector |
| News | `apify_connector.py` → `fetch_news()` | Already called by timeline_connector |

---

## Definition of Done

- [ ] `GET /intelligence/timeline/NVDA?years=2` returns real aggregated events + daily price series
- [ ] `GET /intelligence/timeline/NVDA/compare?against=AMD` returns merged multi-ticker data
- [ ] `/timeline?ticker=NVDA` page shows interactive stock chart with event markers
- [ ] Clicking an event marker highlights the event card below
- [ ] Category filter pills work (toggle categories on/off)
- [ ] Compare mode works (2 tickers overlaid)
- [ ] Empty/loading/error states handled
- [ ] Nav sidebar links to `/timeline`
- [ ] 8+ tests pass
- [ ] No linter errors
- [ ] Works on mobile (responsive)

---

## Estimated Time Breakdown

| Step | Hours |
|------|-------|
| Backend routes (2 endpoints + wiring) | 3-4h |
| Frontend rewrite (chart + event list + filters) | 6-8h |
| Compare mode (frontend + backend) | 3-4h |
| Tests + polish + responsive | 3-4h |
| **Total** | **~16-20h (2-3 days)** |

---

*Assigned by: Anshuman Parmar*  
*Date: 13 August 2026*
