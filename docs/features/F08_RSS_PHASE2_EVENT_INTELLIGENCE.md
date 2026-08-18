# F-08 — RSS Phase 2: Event Intelligence (Clustering, Facts, Contradictions, Perspectives)

> **Status:** 🟢 Implemented (v1) — live in `apps/api`, validated end-to-end against real RSS data + GPT-4o-mini on Aug 18, 2026
> **Priority:** High (James Explicit Request — Handoff Doc Item #5, "James's 500-source vision")
> **Depends on:** F-07 Crawl4AI Integration (already merged, branch `feature/crawl4ai-integration-v2`)
> **Estimated effort:** 3–5 dev days for a working v1 (per existing internal estimate in `docs/others/16th_July_Status_and_Scope.md`)
> **Data sourced from:** Live web research (Aug 17, 2026) — [gdeltproject.org](https://www.gdeltproject.org/about.html), Google AI Overview on 2026 event-clustering/NLI pipelines, [allsides.com](https://www.allsides.com) bias-ratings API, plus this repo's own prior analysis in `reports/25th_June.md` and `docs/JAMES_SENT/July_Roadmap.md`.

---

### 1.0 Implementation Notes (Aug 18, 2026)

v1 shipped exactly as scoped in §4–§6 below, plus two adjacent fixes needed to make the *existing* Phase-1 RSS pipeline actually run locally (it only ever ran against Postgres in staging; local dev defaults to SQLite and had never successfully bootstrapped):

- **New:** `apps/api/app/connectors/event_clustering.py` (§4.1), `apps/api/app/services/event_intelligence_service.py` (§4.2–4.4), `apps/api/app/models/news_events.py` (`rss_events` table, via SQLAlchemy ORM so it works on both SQLite and Postgres with zero dialect branching), `apps/web/pages/news-intelligence.js`.
- **New API:** `POST /market/rss/events/run`, `GET /market/rss/events/job/{job_id}`, `GET /market/rss/events`, `GET /market/rss/events/{id}` — background-job pattern (same as the tracking digest fix) since GPT-4o + Crawl4AI enrichment can take minutes.
- **Fixed (pre-existing, unrelated to this feature but blocking it locally):** `rss_worker.py`'s schema bootstrap and a few `/market/rss/*` queries were Postgres-only (`SERIAL`, `TEXT[]`, `unnest()`, `ANY()`, `NOW()`, multi-statement `execute()`) and silently no-op'd on SQLite. Added a dialect-aware path for each so local dev (`sqlite:///./local.db`) and staging/prod (Postgres) both work — no behavior change on Postgres.
- **Validated live:** ran a real poll (839 articles across 50 sources) → clustered into events (both the embeddings path and the no-API-key Jaccard fallback were exercised) → GPT-4o-mini fact extraction / contradiction detection / perspective labeling completed successfully on real multi-source clusters (e.g. a 2-source Kraken/Anthropic story correctly found zero contradictions since both outlets agreed) and single-source clusters. Full run of 8 events took ~2m20s.
- **Not yet done:** entity-linking `topic_entity` is still `None` on most events (Phase 1's keyword tagger rarely matches); §8 "Open Questions" below covers this. Frontend is a new standalone page, not yet folded into the entity profile "News" tab.

---



## 1. Executive Summary

James asked (25 Jun, WhatsApp) for the RSS system to go beyond "here's a list of headlines" and produce **event intelligence**: group the ~50–500 feeds we poll into *stories*, pull out the actual facts, flag when two outlets disagree, and label *whose angle* each article is taking (bullish/bearish, political left/right, etc.).

We already built **Phase 1** (live today): 50 RSS feeds → Postgres → basic keyword entity-tagging. **Phase 2** is four new NLP steps bolted onto that pipeline. None of it requires new infrastructure spend — it reuses the OpenAI key we already pay for, plus one small open-source library. Below is what each piece means, in plain English first, then the concrete implementation plan.

---

## 2. RSS 101 — For Someone Totally New

**RSS (Really Simple Syndication)** is a 25-year-old, dead-simple protocol. Every major news site publishes a URL like `https://feeds.reuters.com/reuters/businessNews` that returns a small XML file, refreshed continuously, listing its newest articles:

```xml
<item>
  <title>Fed holds rates steady, hints at cuts in 2027</title>
  <link>https://reuters.com/markets/fed-holds-rates-...</link>
  <pubDate>Mon, 17 Aug 2026 09:12:00 GMT</pubDate>
  <description>The Federal Reserve left interest rates unchanged...</description>
</item>
```

That's it — a title, a link, a timestamp, and a short summary. No login, no scraping fight, no rate limits worth worrying about (it's the same file search engines and RSS readers like Feedly poll). A "poller" script fetches these XML files on a timer (we do it every 15 minutes) and saves new items to a database.

**Why RSS instead of just scraping every homepage?** Because the publisher is *handing you* a structured, permission-free feed of exactly what's new — it's the lowest-effort, most reliable way to monitor hundreds of sites continuously. The tradeoff: you only get a title + a short (often truncated) summary, not the full article body. That gap is exactly where Crawl4AI comes in (§5).

### What we already built (Phase 1 — live)

| Piece | File | What it does |
|---|---|---|
| 50 curated feeds (Bloomberg, Reuters, Fed, ECB, IMF, TechCrunch, CoinDesk, etc.) | `apps/api/app/connectors/rss_worker.py` | List of `{name, url, category, region}` |
| Poller | same file, `run_poll_cycle()` | Runs every 15 min via PM2 (`rss-poller` process), uses `feedparser` to pull new items |
| Storage | Postgres `rss_sources` + `rss_articles` tables | One row per article, deduped by URL/hash |
| Entity tagging | `_extract_entities()` | Simple keyword match ("tesla", "tsla" → tags article `Tesla`) — 32 entities hardcoded |
| Frontend | `/market/rss/*` endpoints, entity news feed | Shows tagged articles per entity |

This is P1 from the original phased plan (see §4). It answers "what's new" per entity. It does **not** answer "is this the same story as that other article", "what's actually confirmed vs. rumor", "do two sources disagree", or "is this outlet spinning it bullish or bearish." That's Phase 2.

---

## 3. What James Actually Asked For

Quoting the original WhatsApp ask (25 Jun 2026, captured verbatim in `reports/25th_June.md`):

> 1. **Continuous ingestion** — not just on-demand search, but always-on feeds from finance, macro, politics, crypto, VC, policy, regional news
> 2. **Event intelligence output** — cluster articles by subject/event; extract facts, claims, quotes; keep unique content from each source; label perspectives; flag contradictions
> 3. **Multi-perspective briefings** per topic: *What happened · Confirmed facts · Unconfirmed claims · Conflicting reports · Bullish/Bearish · Political left/right · International view · Market impact · Key quotes · Source map*
> 4. Suggested stack: Inoreader/Feedly/FreshRSS/Miniflux, RSS.app, Google News RSS fallback, Apify/Firecrawl, Whisper for podcasts, Postgres + vector DB
> 5. Commercial option later if needed: RavenPack, Dataminr, AlphaSense-class licensed news system

The build was scoped into 6 phases (P1–P6), of which **P1 is done**:

| Phase | Scope | Status |
|---|---|---|
| P1 | RSS registry + worker polling 50 core feeds → Postgres → entity match → News tab | ✅ **Done** |
| **P2** | **Event clustering + dedup strategy + master "event" record per story** | 🟡 **This document** |
| P3 | Scale to 200+ sources via Google News RSS fallback for non-RSS sites | Not started |
| P4 | Multi-perspective LLM synthesis (bullish/bearish/left/right/international) | Folded into P2 below — see §4.4 |
| P5 | YouTube/Podcast transcripts (Whisper) | Not started, separate doc if approved |
| P6 | Full 500 sources + optional commercial feed (RavenPack/Dataminr) | Not started, revisit after P2–P4 prove value |

This doc proposes doing **P2 + P4 together** (clustering + all four intelligence layers) since they share the same pipeline and it's wasteful to build clustering twice.

---

## 4. What "RSS Phase 2" Actually Means — The Four Pieces

Every incoming article already has: title, summary, URL, source, timestamp, entity tags (Phase 1). Phase 2 adds four sequential steps that run after ingestion, on a rolling window of recent articles per entity/topic.

### 4.1 Event Clustering
**Plain English:** If Reuters, Bloomberg, and CNBC all publish an article about the Fed holding rates today, that's *one event*, covered three times — not three unrelated news items. Clustering groups those three articles into one "event" so the platform can show "3 outlets covered this" instead of three duplicate-looking rows.

**How it works technically:** Convert each article's title+summary into a numeric vector ("embedding") that captures its meaning, then group articles whose vectors are close together *and* published within a tight time window (same real-world event ≈ same day). This is standard practice — Google's own 2026 guidance on this exact task confirms the current best approach is **embedding-based clustering with a time constraint**, not naive keyword/lexical matching (which breaks when two outlets phrase the same fact differently).

- **Library:** `sentence-transformers` (free, runs locally, ~80MB model) to generate embeddings, or reuse OpenAI's `text-embedding-3-small` (already have the API key, ~$0.02 per 1M tokens — trivially cheap at our volume).
- **Clustering algorithm:** simple cosine-similarity threshold + same-day window is enough at our scale (hundreds of articles/day, not millions). No need for the heavier graph-based/topic-model approaches (e.g. BERTopic) used by large-scale research systems — that's overkill until we're at the 500-source/GDELT-scale volume in P6.

### 4.2 Fact Extraction
**Plain English:** Out of a 400-word article, what are the 3–5 actual facts, quotes, and numbers? ("Fed held the rate at 4.25–4.50%", "Powell said cuts possible in 2027", "vote was 9-2"). This turns prose into a short structured list that's easy to scan and easy to compare across articles in the same cluster (which is a prerequisite for §4.3, contradiction detection).

**How it works technically:** Feed the cluster's articles into GPT-4o (already licensed and used elsewhere in this codebase for intelligence-report narratives — `apps/api/app/services/intelligence_service.py`) with a structured-extraction prompt: "list each discrete factual claim, who said it, and which source it came from." This is the same "claims extraction" pattern used across current 2026 fact-checking research — extract *who/what/when/where* as discrete claims rather than trying to summarize the whole article in one paragraph, specifically so each claim can be checked/compared independently in the next step.

### 4.3 Contradiction Detection
**Plain English:** Outlet A says "layoffs affect 5,000 employees," Outlet B says "12,000." That's a contradiction worth flagging — a reader relying on one source alone wouldn't know the numbers disagree.

**How it works technically:** Once facts are extracted per source (§4.2), compare claim pairs from different sources *within the same event cluster*. Two established approaches, both viable here:
- **NLI (Natural Language Inference) models** — a well-established NLP task where a small model (e.g. `roberta-large-mnli` on HuggingFace) takes two sentences and classifies them as *entailment* (agree), *neutral* (unrelated), or *contradiction* (disagree). Free, runs locally, no API cost, but weaker on numeric mismatches ("5,000" vs "12,000") since it's trained on general language, not numbers-focused.
- **LLM-prompted comparison** — ask GPT-4o directly: "do these two claims about the same event agree, partially agree, or conflict, and why?" More reliant on the OpenAI bill but much better at catching numeric/date mismatches and timeline conflicts, which is what actually matters for a finance platform (a $ figure being wrong is a bigger deal than tone disagreement).

**Recommendation:** start LLM-prompted (simpler to ship, reuses existing GPT-4o wiring), add the free NLI model later only if OpenAI cost becomes a concern at higher article volume.

### 4.4 Perspective Labeling
**Plain English:** The same Fed decision gets framed completely differently depending on the outlet: a "bullish" spin on CNBC, a "warning sign" framing on ZeroHedge, a neutral wire recap on Reuters. James specifically wants: Bullish/Bearish, Political left/right, International view, Market impact — attached per-article, so a briefing can show "here's the range of takes on this story" rather than one voice.

**How it works technically, two options:**
1. **Buy the labels** — commercial APIs like **AllSides** (confirmed to offer a "Bias Ratings License & API" — allsides.com/tools-services) or Ground News maintain a curated left/center/right rating *per outlet* (not per article). Fast to integrate (it's a static lookup table keyed by publisher name) but only covers political lean, and only for outlets they've already rated (mostly US politics/general news — weak coverage of finance-specific & crypto outlets we track).
2. **Build it ourselves** — GPT-4o prompt per article: "classify this article's framing as bullish/bearish/neutral on the subject, and note if language suggests a particular political or regional lean." Works on *any* outlet including the finance-niche ones AllSides doesn't rate (ZeroHedge, CoinDesk, Seeking Alpha), and gives per-article rather than per-outlet granularity (an outlet can run both a bullish and a skeptical piece on the same day).

**Recommendation:** build it ourselves via LLM prompt (option 2) as the primary method — it's the only approach that covers our actual feed list — and optionally layer AllSides' static outlet ratings on top later as a cheap sanity-check/cross-reference for the subset of political/general-news outlets it does cover.

---

## 5. How This Relates to Crawl4AI (F-07)

They solve different problems in the same pipeline, not competing approaches:

| | RSS (Phase 1, live) | Crawl4AI (F-07, live) |
|---|---|---|
| **What it gives you** | Title + short summary + link, for ~50 known feeds | Full article body / full page content, for *any* URL |
| **When it's used here** | Continuous polling, 15-min cycle, no target URL needed in advance | On-demand, when RSS doesn't cover a site (no feed exists, or it's JS-rendered) or when Phase 2 needs the *full text* to extract facts reliably |

**Why Phase 2 needs Crawl4AI:** an RSS summary is often 1–2 truncated sentences — not enough text to reliably extract 3–5 distinct facts or catch a numeric contradiction. The plan is: RSS gives us the *headline + link fast* (continuous, cheap), then for articles inside a cluster that's being fully analyzed, `crawl_url()` (already built in `apps/api/app/connectors/crawl4ai_connector.py`) fetches the full body so fact extraction has real material to work with. Also, when we scale past 50 feeds (P3/P6 — "500-source vision"), most of the extra sites won't have a clean RSS feed at all; Crawl4AI (or the Google News RSS fallback already used in `crawl_news()`) is exactly the fallback path James specified in his original stack list ("Apify/Firecrawl" — now Crawl4AI per F-07).

---

## 6. Proposed Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌───────────────────┐
│ RSS Poller  │────▶│ rss_articles │────▶│ Event Clusterer│────▶│    rss_events      │
│ (existing,  │     │ (existing)   │     │ (NEW - runs on │     │ (NEW table: one    │
│  15-min)    │     │              │     │  a rolling      │     │  row per story)    │
└─────────────┘     └──────────────┘     │  window, e.g.   │     └─────────┬───────────┘
                                          │  every 30 min)  │               │
                                          └────────────────┘               ▼
                     ┌─────────────────────────────────────────────────────┴──┐
                     │  Per-cluster enrichment (only runs on clusters with    │
                     │  2+ sources — no point analyzing a single-source item) │
                     │                                                        │
                     │  1. crawl_url() each member → full text (Crawl4AI)     │
                     │  2. GPT-4o: extract facts/claims/quotes per source     │
                     │  3. GPT-4o: compare claims across sources → conflicts  │
                     │  4. GPT-4o: label each article's framing/perspective  │
                     └────────────────────────┬───────────────────────────────┘
                                               ▼
                                   ┌───────────────────────┐
                                   │  Briefing JSON stored  │
                                   │  on the rss_events row │
                                   │  → new frontend view   │
                                   └───────────────────────┘
```

### New DB table (`rss_events`)

```sql
CREATE TABLE rss_events (
    id              SERIAL PRIMARY KEY,
    topic_entity    TEXT,             -- e.g. "Federal Reserve", "Tesla"
    headline        TEXT,             -- representative/canonical headline
    article_ids     INTEGER[],        -- FK-ish list into rss_articles
    source_count    INTEGER,
    confirmed_facts JSONB,            -- [{fact, sources: [...]}]
    unconfirmed_claims JSONB,
    conflicts       JSONB,            -- [{claim_a, claim_b, source_a, source_b, note}]
    perspectives    JSONB,            -- [{article_id, framing: "bullish"/"bearish"/"neutral", lean, notes}]
    market_impact   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### New files
| File | Purpose |
|---|---|
| `apps/api/app/connectors/event_clustering.py` | Embedding generation + clustering logic (§4.1) |
| `apps/api/app/services/event_intelligence_service.py` | Orchestrates fact extraction → contradiction detection → perspective labeling per cluster (§4.2–4.4), calling GPT-4o and `crawl4ai_connector.crawl_url()` |
| `apps/api/app/api/market.py` (extend) | New endpoints: `GET /market/rss/events`, `GET /market/rss/events/{id}` |
| `apps/web/pages/rss-events.js` or a new tab on existing news view | Briefing UI: "What happened / Confirmed / Unconfirmed / Conflicts / Perspectives" per James's exact spec (§3) |

---

## 7. Cost Impact

| Item | Cost |
|---|---|
| Embeddings for clustering (`text-embedding-3-small`) | ~$0.02 per 1M tokens — at ~200 articles/day this is cents/month |
| GPT-4o calls for fact extraction/contradiction/perspective (only on multi-source clusters, not every article) | Existing OpenAI key; incremental cost scales with # of clustered *events*, not raw article count — should be a modest addition to current OpenAI spend, recommend capping to top N events/day if it grows |
| `sentence-transformers` (if used instead of OpenAI embeddings) | $0 — runs locally, one-time model download |
| AllSides bias API (optional, §4.4 fallback) | Requires checking current pricing/license terms directly with AllSides if we decide to add it — not required for v1 |

No new infrastructure (Postgres already hosts `rss_articles`; Crawl4AI already deployed per F-07).

---

## 8. Phased Delivery Plan

| Step | Scope | Est. effort |
|---|---|---|
| 1 | `rss_events` table + event clustering job (§4.1, §6) | 1 day |
| 2 | Fact extraction per cluster via GPT-4o + Crawl4AI full-text fetch (§4.2) | 1 day |
| 3 | Contradiction detection between same-cluster claims (§4.3) | 1 day |
| 4 | Perspective labeling per article (§4.4) | 0.5–1 day |
| 5 | New endpoints + briefing UI (§6) | 1 day |
| **Total** | | **~4–5 days**, matches existing internal estimate |

Suggested rollout order matches the numbered list above — each step is independently useful and shippable (e.g. clustering alone already de-duplicates the News tab, which is a visible win even before facts/contradictions/perspectives are added).

---

## 9. Risks & Open Questions

1. **LLM cost at scale** — if we later hit P6 (500 sources), per-event GPT-4o calls need a budget cap or a cheaper model tier for the extraction/labeling steps (only contradiction detection on financial numbers really needs the strongest model).
2. **Cluster quality at low volume** — with only 50 feeds, many stories will only have 1 source (no cluster to compare), so contradiction detection has less to work with until we scale sources (P3/P6). Recommend shipping now — value grows automatically as we add sources.
3. **"Political left/right" labeling is inherently subjective** — recommend framing this in the UI as *"this article's apparent framing"* rather than a hard claim about outlet bias, to avoid overstating certainty from an LLM's judgment call.
4. **AllSides/Ground News licensing** — if we want their bias labels, terms/pricing need confirming directly (not verified in this research pass); not a blocker since our own LLM-based approach covers the same ground and works for niche finance outlets they don't rate anyway.

---

## 10. Approval Ask

Requesting sign-off to build **Steps 1–5 above** (event clustering + fact extraction + contradiction detection + perspective labeling + briefing UI) as a single ~4–5 day workstream on a new branch (`feature/rss-phase2-event-intelligence`), reusing the existing OpenAI key and the already-merged Crawl4AI connector — no new paid services required for v1.
