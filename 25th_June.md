# 25th June 2026 — RSS Global News Intelligence + Status Handoff

**Purpose:** Daily handoff for 25 Jun 2026 — James RSS/news vision analysed; platform status updated.  
**Staging:** Web `http://184.72.123.188:3003` · API `http://184.72.123.188:3001` · Docs `http://184.72.123.188:3001/docs`  
**Prior docs:** [24th_June.md](./24th_June.md) · [23rd_June.md](./23rd_June.md) · [README.md](./README.md)

---

## Summary — 25 Jun

| Area | Status |
|------|--------|
| James RSS / 500-source global news vision — analysed | ✅ Complete |
| Phased build plan drafted (P1–P6) | ✅ Complete |
| WhatsApp reply drafted for James | ✅ Complete |
| RSS ingestion module | 🔲 Not started — next workstream |
| Event clustering + perspective synthesis | 🔲 Not started |
| `25th_June.md` created | ✅ This file |
| `README.md` updated | ✅ Complete |

---

## What James Asked For (25 Jun — WhatsApp)

James proposed using **RSS feeds at scale** (~500 global sources) as a news intelligence layer:

1. **Continuous ingestion** — not just on-demand search, but always-on feeds from finance, macro, politics, crypto, VC, policy, regional news
2. **Event intelligence output** — cluster articles by subject/event; extract facts, claims, quotes; keep unique content from each source; label perspectives; flag contradictions
3. **Multi-perspective briefings** per topic:
   - What happened · Confirmed facts · Unconfirmed claims · Conflicting reports
   - Bullish / Bearish · Political left / right · International view · Market impact · Key quotes · Source map
4. **Suggested stack:** Inoreader/Feedly/FreshRSS/Miniflux · RSS.app · Google News RSS fallback · Apify/Firecrawl · Whisper/AssemblyAI for podcasts · Postgres + vector DB
5. **Commercial option later** — buy a licensed global news system (RavenPack, Dataminr, AlphaSense class) if RSS + LLM pipeline isn't enough

### Analysis Conclusion

| Finding | Detail |
|---------|--------|
| RSS is the right foundation | ~120–150 of 500 URLs are direct RSS (Bloomberg, Fed, IMF, ECB, MarketWatch verified ✅) |
| Rest need tiered fallback | ~200 via Google News `site:DOMAIN` RSS · ~80 scrape · ~70 YouTube/podcast/reddit |
| Fits platform direction | Natural Layer 2 extension of news connectors built 24 Jun |
| Not a small add | New subsystem: feed registry + polling worker + clustering + LLM synthesis |
| Complements existing | NewsAPI/Guardian/NYT = search-on-demand; RSS = monitor-always; GDELT = free global events |

### Proposed Build Phases

| Phase | Scope | Status |
|-------|-------|--------|
| P1 | RSS registry + worker polling 50 core feeds → Postgres → entity match → News tab | 🔲 Pending James go-ahead |
| P2 | Event clustering + James dedup strategy + master event JSON | 🔲 Pending |
| P3 | Scale to 200 sources + Google News RSS fallback | 🔲 Pending |
| P4 | Multi-perspective LLM synthesis (bullish/bearish/left/right/intl) | 🔲 Pending |
| P5 | YouTube/Podcast transcripts (Whisper) | 🔲 Pending |
| P6 | Full 500 sources + optional commercial feed | 🔲 Pending |

---

## Platform Status — What's Done (cumulative through 25 Jun)

### ✅ Live on Staging

| Area | Status |
|------|--------|
| Intelligence reports (12 sections + GPT narrative) | ✅ Live |
| Entity profile (9 tabs: Overview, Financial, People, Social, Chat, etc.) | ✅ Live |
| Financial tab — live AAPL data (price, P/E, M-Score, Z-Score, insiders) | ✅ Live (24 Jun) |
| News aggregation — NewsAPI + Guardian + NYT + Finnhub + GDELT | ✅ Live (24 Jun) |
| UK Companies House — search + officers | ✅ Live (24 Jun) |
| API Status panel — 11 sources on entity profile | ✅ Live (24 Jun) |
| Apify — Google News, LinkedIn, PitchBook, Twitter/IG/YouTube | ✅ Live |
| Apollo org enrichment | ✅ Live |
| Tracking watchlist + daily digest | ✅ Live |
| Export — PDF, Word, Excel, PowerPoint | ✅ Live |
| 51-state registry + BEA economics | ✅ Live |
| 79 tests passing | ✅ |

### ✅ API Keys — 8/9 Active

| API | Status |
|-----|--------|
| Finnhub | ✅ Active |
| FMP (stable endpoints) | ✅ Active |
| Alpha Vantage | ✅ Active |
| FRED | ✅ Active |
| NewsAPI | ✅ Active |
| The Guardian | ✅ Active |
| NYT Article Search | ✅ Active |
| UK Companies House | ✅ Active |
| GDELT / OpenSanctions / ICIJ | ✅ No key / graceful |

### ⏳ Pending

| Item | Status | Notes |
|------|--------|-------|
| ALEPH/OCCRP API key | ❌ | Registration unavailable |
| CA SOS API key | ⏳ | Subscriptions submitted 12 Jun — awaiting Active |
| RSS global news module | 🔲 | James request 25 Jun — awaiting go-ahead |
| Event clustering + perspectives | 🔲 | Part of RSS module |
| pgvector embeddings (full RAG) | 🔲 | TF-IDF works today |
| OIDC/Google SSO credentials | ⏳ | Routes wired, keys pending from James |
| FMP margin ratio fields | ⚠️ | Not in stable API; manual calc possible |
| GDELT rate limits | ⚠️ | Intermittent under rapid polling |
| ICIJ Offshore Leaks API | ⚠️ | Decommissioned; web UI only |

---

## Staging URLs

| Resource | URL |
|----------|-----|
| Web | http://184.72.123.188:3003 |
| Intelligence | http://184.72.123.188:3003/intelligence |
| Entity profile (Apple) | http://184.72.123.188:3003/entities/1 |
| API docs | http://184.72.123.188:3001/docs |
| Admin | http://184.72.123.188:3002 |

---

## Git

| Commit | Description |
|--------|-------------|
| `b1e4f12` | README updated to 24 Jun status |
| `3d34f96` | 8 API keys integrated + connector fixes + 24th_June.md |

**Branch:** `main` · synced with `origin/main`
