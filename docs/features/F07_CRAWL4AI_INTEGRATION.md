# F-07 — Crawl4AI Integration (Replace Apify for Long-Term Scraping)

> **Status:** ✅ Approved with Modifications — Lead Reviewed Aug 3, 2026  
> **Priority:** High (James Preference — Handoff Doc Item #6)  
> **Branch:** `feature/crawl4ai-integration`  
> **Replaces:** Apify cloud platform (`apify_connector.py`) — LinkedIn/PitchBook kept as fallback for 60 days  
> **Cost Impact:** Saves **$49–$200/month**, minus optional **$20–$50/month** residential proxy if LinkedIn stays in scope  
> **Data sourced from:** [docs.crawl4ai.com](https://docs.crawl4ai.com), [GitHub: unclecode/crawl4ai](https://github.com/unclecode/crawl4ai), [PkgPulse 2026 Comparison](https://pkgpulse.com/guides/crawl4ai-vs-firecrawl-vs-apify-ai-web-scraping-2026)

---

## 0. Lead Review — Verdict & Modifications Applied

**Verdict:** Proceed with the plan, with 5 modifications (all applied below):

1. Extend Apify fallback for LinkedIn/PitchBook from 30 → **60 days** (§6, §12, §14)
2. Add the real orchestrator/service file to scope (§6.1) — see correction note below
3. Add Docker resource limits — `shm_size`, memory (§11.1)
4. Start with low-risk targets (news, IR pages) before LinkedIn/PitchBook (§10, corrected order)
5. Budget for proxy service (~$20–50/mo) if LinkedIn is critical (§11.2)

**Two corrections to the lead's review, verified against the actual codebase:**

| Lead's review said | Reality (verified) |
|---|---|
| `deep_research_orchestrator.py` (885 lines) is the master coordinator and must be updated | **This file does not exist anywhere in the repo.** The file that actually plays this role — importing `apify_connector.py` and running the Apify enrichment calls (`fetch_linkedin_by_name`, `fetch_pitchbook_company`, `fetch_news`, `fetch_social_footprint`, `fetch_key_people`) — is `apps/api/app/services/intelligence_service.py` (`generate_intelligence_report()`, ~line 750). **This is the file in scope, not the phantom orchestrator.** |
| `osint_connector.py` — MODIFIED, "uses Apify for some lookups" | Verified: `osint_connector.py` (behind `/osint/person`, `/osint/company`) has **zero** Apify imports or usage. Not in scope — dropped from the files-changed list. |

The rest of the review (graceful degradation pattern, import-wrapping pattern, anti-bot risk, Docker `shm_size`, proxy gap, implementation order) checks out and is incorporated below.

---

## 1. Executive Summary

The Finance Advanced Research Platform currently uses **Apify** (a paid cloud scraping service) to gather company data, people profiles, funding information, and news. This costs the client money every month and creates a vendor dependency.

**James has explicitly requested replacing Apify with Crawl4AI** — an open-source, self-hosted Python web crawler that is:
- **100% free forever** (Apache 2.0 licence)
- **AI-native** — outputs clean Markdown/JSON that LLMs can directly consume
- **Faster and more controllable** than Apify for custom pipelines
- **Already used by 75,700+ developers** on GitHub (#1 trending repo in 2024–2025)
- **Production-grade** with v0.9.x bringing Docker, JWT auth, MCP integration

---

## 2. What is Crawl4AI?

### Plain English

Imagine you want to scrape a company's investor relations page to extract their CEO name, revenue, and recent news. A regular scraper gives you a 500-line mess of HTML tags. **Crawl4AI gives you clean, readable text that an AI can immediately understand and analyse** — like this:

```
# Apple Inc — Investor Relations

## Q4 2025 Results
- Revenue: $124.3B (up 6% YoY)
- EPS: $1.64

## CEO
Tim Cook has served as CEO since 2011...

## Recent Filings
- [Form 10-K filed Jan 2026](https://...)
```

### Technical Definition

Crawl4AI is an open-source, Python-based, **LLM-friendly web crawler and scraper** that:
1. Launches a real browser (via Playwright/Chromium)
2. Navigates to any URL including JavaScript-heavy SPAs
3. Strips all noise (nav bars, ads, cookie banners, scripts)
4. Outputs **clean Markdown** — the exact format that GPT/Claude/Gemini can read
5. Optionally extracts **structured JSON** using CSS selectors or AI-driven schemas

### Key Stats (July 2026)
| Metric | Value |
|---|---|
| GitHub Stars | **75,700+** |
| Current Version | **v0.9.2** |
| Licence | Apache 2.0 (free forever including commercial) |
| Language | Python (async-first) |
| Created by | Hossein Tohidi (Unclecode), mid-2024 |
| Discord Community | 15,000+ members |
| Backing | Open-source + cloud beta launching |

---

## 3. Why We Need It (Problem with Current Setup)

### Current Pain Points with Apify

| Problem | Impact |
|---|---|
| Costs $49–$200/month | Ongoing client expense |
| Data flows through Apify's servers | Privacy concern for financial intelligence |
| Black box — limited control | Can't customise extraction logic |
| Rate limits on free tier | Fails during heavy research |
| Output is raw HTML | Needs post-processing before feeding to AI |
| Actor marketplace changes | Features can be deprecated without notice |

### Why Crawl4AI Solves This

| Solution | How |
|---|---|
| Zero cost | Self-hosted on existing server |
| Full data privacy | Never leaves your infrastructure |
| Complete control | Write exactly the extraction logic you need |
| No rate limits | Only limited by your own server resources |
| AI-ready output | Markdown out of the box, no post-processing |
| Stable open-source | Apache 2.0 — can't be taken away |

---

## 4. How Crawl4AI Works — Core Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CRAWL4AI PIPELINE                       │
│                                                              │
│  URL Input                                                   │
│     │                                                        │
│     ▼                                                        │
│  AsyncWebCrawler ──► Playwright Browser (headless Chromium)  │
│     │                     │                                  │
│     │                     ▼                                  │
│     │              Full Page Render (JS executed)            │
│     │                     │                                  │
│     │                     ▼                                  │
│     │              HTML Cleaning                             │
│     │              (remove nav, ads, scripts)                │
│     │                     │                                  │
│     ▼                     ▼                                  │
│  CrawlResult ◄──── Markdown Generator                        │
│     │              (headings, tables, code, links)           │
│     │                                                        │
│     ├── result.markdown        → Feed directly to LLM        │
│     ├── result.extracted_content → Structured JSON           │
│     ├── result.links           → Discover more URLs          │
│     ├── result.media           → Images, videos              │
│     └── result.metadata        → Title, OG tags, canonical   │
└─────────────────────────────────────────────────────────────┘
```

### Three Ways to Extract Data

#### Method 1: Simple Markdown (No AI needed)
```python
from crawl4ai import AsyncWebCrawler

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url="https://apple.com/investor")
    print(result.markdown)   # Clean text, ready for LLM
```

#### Method 2: CSS/XPath Schema (Fast, no LLM cost)
```python
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

schema = {
    "name": "Company Profile",
    "fields": [
        {"name": "company_name", "selector": "h1",        "type": "text"},
        {"name": "ceo",          "selector": ".ceo-name",  "type": "text"},
        {"name": "revenue",      "selector": ".revenue",   "type": "text"},
    ]
}

strategy = JsonCssExtractionStrategy(schema)
result = await crawler.arun(url=url, extraction_strategy=strategy)
data = json.loads(result.extracted_content)
```

#### Method 3: LLM-Driven Schema (Most powerful)
```python
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field

class CompanyProfile(BaseModel):
    name: str = Field(description="Company legal name")
    ceo: str = Field(description="Current CEO full name")
    revenue: str = Field(description="Latest annual revenue with currency")
    employees: str = Field(description="Employee count")
    founded: str = Field(description="Year founded")
    headquarters: str = Field(description="City, Country")

strategy = LLMExtractionStrategy(
    provider="openai/gpt-4o-mini",    # Or anthropic/claude-3-haiku
    api_token=os.getenv("OPENAI_API_KEY"),
    schema=CompanyProfile.model_json_schema(),
    extraction_type="schema",
    instruction="Extract the company profile from this investor relations page.",
)

result = await crawler.arun(url=url, extraction_strategy=strategy)
profile = CompanyProfile.model_validate_json(result.extracted_content)
```

---

## 5. Unique Features vs Any Other Scraper

### 5.1 Adaptive Crawling (Unique to Crawl4AI)

The biggest innovation in v0.9.x — **the crawler knows when to stop.**

Traditional crawlers blindly follow every link. Adaptive Crawling uses **information foraging theory** (same algorithm used by academic literature search engines) to:

1. **Coverage score** — how well pages collected cover your query terms
2. **Consistency score** — whether info is coherent across pages
3. **Saturation score** — detects when new pages add no new information

When these scores hit a threshold (default: 0.7), **crawling stops automatically** — saving time and compute.

```
Example: Crawling "What is Tesla's battery technology?"

Page 1: Tesla.com/powerwall  → coverage: 0.3
Page 2: Tesla.com/megapack  → coverage: 0.55
Page 3: Tesla.com/tech/battery → coverage: 0.72 ← STOP (threshold reached)

Result: 3 pages crawled instead of 50. 17x more efficient.
```

**Use case in our platform:** When researching a company for F-06 Network Intelligence, instead of crawling 200 pages of their site, Crawl4AI crawls only the ~10 pages needed to answer "who are the founders, investors, and board members."

### 5.2 Memory-Adaptive Dispatcher

Crawl4AI v0.9.x monitors RAM usage and automatically throttles concurrent crawl workers before the server runs out of memory. No more OOM crashes during bulk research jobs.

### 5.3 MCP Integration (Model Context Protocol)

Crawl4AI now natively integrates with **Claude Code, Cursor, and any MCP-compatible AI tool**. This means AI agents can call Crawl4AI as a native tool — scrape web pages as part of an agent reasoning loop, without writing separate API calls.

```
Claude Agent: "Research Apollo Global's latest acquisitions"
  → MCP call to Crawl4AI → Returns clean markdown
  → Claude analyses → Extracts structured data
  → Returns to platform
```

### 5.4 Anti-Bot & Stealth Mode

```python
from crawl4ai import BrowserConfig

browser_config = BrowserConfig(
    headless=True,
    stealth_mode=True,           # Patches navigator.webdriver
    user_agent_mode="random",    # Random real user-agent
    accept_downloads=False,
)
```

### 5.5 PDF Parsing (Critical for SEC Filings)

```python
result = await crawler.arun(
    url="https://sec.gov/Archives/edgar/data/.../10k.pdf",
    # Crawl4AI auto-detects PDF and extracts text
)
print(result.markdown)  # Full 10-K content as clean text
```

### 5.6 Identity-Based Crawling (Login-Protected Pages)

For sites requiring login (e.g., premium data portals):

```python
result = await crawler.arun(
    url="https://bloomberg.com/company/AAPL",
    session_id="bloomberg_session",   # Reuse authenticated session
    cookies=[{"name": "session", "value": "your_cookie"}],
)
```

---

## 6. What It Replaces in This Platform

### Current Apify Usage → Crawl4AI Replacement

| Current (Apify Actor) | Data It Fetches | Replace With |
|---|---|---|
| `apify/linkedin-company-scraper` | Company LinkedIn profiles | Crawl4AI + stealth mode |
| `apify/apollo-scraper` | People profiles, emails | Crawl4AI → Apollo direct pages |
| `apify/crunchbase-scraper` | Funding rounds, investors | Crawl4AI CSS extraction |
| `apify/news-scraper` | Company news articles | Crawl4AI multi-URL + Markdown |
| `apify/website-content-crawler` | General company pages | Crawl4AI (this is its core job) |
| `apify/google-search-scraper` | Search results | Crawl4AI + SERP pages |

### Files That Change

| File | Change |
|---|---|
| `apps/api/app/connectors/apify_connector.py` | **Keep** — fallback for LinkedIn/PitchBook only, for 60 days, then remove |
| `apps/api/app/connectors/crawl4ai_connector.py` | **NEW** — core connector, import-wrapped (see §6.1) |
| `apps/api/app/services/intelligence_service.py` | **MODIFIED** — this is the real integration point (not `deep_research_orchestrator.py`, which doesn't exist in this repo). Wire Crawl4AI in alongside the existing Apify try/except block, route news + IR-page fetches through Crawl4AI first, keep Apify as the LinkedIn/PitchBook fallback |
| `apps/api/app/api/market.py` | Update `/company/private-intel` endpoint |
| `apps/api/app/api/market.py` | Update `/osint/company`, `/osint/person` |
| `apps/api/requirements.txt` | Add `crawl4ai>=0.9.2` |
| `.env` / `.env.example` | Add `CRAWL4AI_API_TOKEN` (optional, Docker mode), `PROXY_URL`, `PROXY_ENABLED` (see §11.2) |

### 6.1 Required Pattern: Graceful Degradation + Import Wrapping

This codebase already uses this exact pattern for every optional connector (Apify, browser research agent, Apollo, private company intel) in `intelligence_service.py`. `crawl4ai_connector.py` must follow the same shape so it never breaks the pipeline if the package or Docker service is unavailable:

```python
# apps/api/app/services/intelligence_service.py — existing convention to replicate
try:
    from app.connectors.crawl4ai_connector import (
        crawl_company_intel,
        crawl_news,
    )
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    def crawl_company_intel(*args, **kwargs): return {}
    def crawl_news(*args, **kwargs): return []
```

And inside `crawl4ai_connector.py` itself, every fetch function follows the codebase's standard degrade-never-raise pattern:

```python
def crawl_company_intel(domain: str) -> dict:
    if not domain:
        return {}
    try:
        # ... actual crawl via AsyncWebCrawler ...
        return result
    except Exception as e:
        logger.warning(f"Crawl4AI error for {domain}: {e}")
        return {}  # Never raise, never break the report pipeline
```

---

## 7. Crawl4AI vs Apify — Deep Comparison

| Category | **Crawl4AI** | **Apify** |
|---|---|---|
| **Cost** | ✅ Free (Apache 2.0) | ❌ $49–$200/month |
| **Hosting** | Self-hosted (your server) | Apify's cloud |
| **Data privacy** | ✅ Data stays on your server | ❌ Passes through Apify servers |
| **AI-ready output** | ✅ Native Markdown/JSON | ⚠️ Mostly raw HTML |
| **LLM integration** | ✅ Native (Claude, GPT, Gemini) | ❌ Manual post-processing |
| **JS rendering** | ✅ Playwright built-in | ✅ Playwright/Puppeteer |
| **Adaptive crawling** | ✅ Unique feature | ❌ Not available |
| **PDF parsing** | ✅ Built-in | ⚠️ Actor-dependent |
| **MCP integration** | ✅ Claude/Cursor native | ❌ Not available |
| **Pre-built scrapers** | ❌ Write your own | ✅ 30,000+ actors |
| **Anti-bot / Proxies** | ⚠️ Stealth mode, DIY proxies | ✅ Built-in residential proxies |
| **Scheduling** | External (cron, APScheduler) | ✅ Built-in scheduler |
| **Control over logic** | ✅ Full Python control | ❌ Limited to Actor parameters |
| **GitHub Stars** | 75,700+ | ~4,000 (SDK) |
| **Community** | 15,000+ Discord | 8,000+ Discord |
| **Latest version** | v0.9.2 (July 2026) | Continuously updated |
| **Best for** | AI pipelines, finance intel, RAG | Pre-built website scrapers |

### When Apify Still Wins

Apify remains better when:
- You need to scrape **heavily anti-bot sites** (Cloudflare, PerimeterX) at scale
- You need a **pre-built scraper for a specific site** immediately (e.g., Amazon products)
- You have a **Node.js team** without Python infrastructure

For this platform (Python backend, financial intelligence, AI pipeline), **Crawl4AI is the clear winner.**

---

## 8. All Alternatives Considered

| Tool | Type | Cost | LLM-Ready | Self-Hosted | Verdict |
|---|---|---|---|---|---|
| **Crawl4AI** | Python library | **Free** | ✅ Native | ✅ Yes | **Recommended** |
| Apify | Cloud platform | $49–$200/mo | ⚠️ Limited | ❌ No | Current (replace) |
| **Firecrawl** | Managed API | $16/mo+ | ✅ Native | ❌ No | 2nd choice if no Python |
| Scrapy | Python framework | Free | ❌ No | ✅ Yes | No JS rendering |
| Playwright | Browser automation | Free | ❌ No | ✅ Yes | Low-level, manual |
| Crawlee | Node.js/Python | Free | ❌ No | ✅ Yes | No LLM output |
| ScrapeGraphAI | Python library | Free | ✅ AI-first | ✅ Yes | Newer, less stable |
| Bright Data | Cloud + Proxy | $500+/mo | ❌ No | ❌ No | Enterprise only |
| Jina Reader | API | Free tier | ✅ Yes | ❌ No | Limited features |

---

## 9. How We Use It In This Platform (Finance Use Cases)

### Use Case 1: Company Intelligence (`/company/private-intel`)

```python
# Current: Apify actor call (paid)
# New: Crawl4AI

async def get_company_intel(company_name: str, domain: str) -> dict:
    async with AsyncWebCrawler(config=BrowserConfig(stealth_mode=True)) as crawler:
        pages = [
            f"https://{domain}/about",
            f"https://{domain}/leadership",
            f"https://{domain}/investors",
        ]
        results = await crawler.arun_many(urls=pages, config=CrawlerRunConfig(
            word_count_threshold=100,
            exclude_external_links=True,
        ))
        combined_markdown = "\n\n".join(r.markdown for r in results if r.success)
        # Feed to LLM for structured extraction
        return extract_company_profile_with_llm(combined_markdown)
```

### Use Case 2: SEC 10-K/10-Q Filing Analysis

```python
async def analyse_sec_filing(sec_url: str) -> dict:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=sec_url)
        # result.markdown = full 10-K as clean text
        # Feed directly to GPT/Claude for financial analysis
        return await llm_extract_financials(result.markdown)
```

### Use Case 3: F-06 Network Intelligence (Board Members, Investors)

```python
async def map_company_network(domain: str) -> dict:
    from crawl4ai import AdaptiveCrawler, CrawlerRunConfig

    async with AdaptiveCrawler() as crawler:
        result = await crawler.arun(
            url=f"https://{domain}",
            query="board members investors founders executives team",
            threshold=0.75,   # Stop when 75% confident we have enough
            max_pages=15,
        )
        # Returns exactly the pages needed, nothing more
        return await extract_network_graph(result.knowledge_base)
```

### Use Case 4: Funding Data (Crunchbase / PitchBook public pages)

```python
schema = {
    "name": "Funding Rounds",
    "baseSelector": ".funding-round",
    "fields": [
        {"name": "round",    "selector": ".round-type",   "type": "text"},
        {"name": "amount",   "selector": ".round-amount", "type": "text"},
        {"name": "date",     "selector": ".round-date",   "type": "text"},
        {"name": "investors","selector": ".investors",    "type": "text"},
    ]
}
strategy = JsonCssExtractionStrategy(schema)
result = await crawler.arun(url=crunchbase_url, extraction_strategy=strategy)
```

### Use Case 5: News Aggregation (Replace Apify news actor)

```python
news_urls = [
    "https://reuters.com/companies/AAPL",
    "https://finance.yahoo.com/quote/AAPL/news",
    "https://seekingalpha.com/symbol/AAPL/news",
]
results = await crawler.arun_many(
    urls=news_urls,
    config=CrawlerRunConfig(word_count_threshold=200)
)
# Each result.markdown = clean article text for LLM summarisation
```

---

## 10. Implementation Plan (Corrected Order — Lead Reviewed)

Original proposal ordered this as Phase 1 (bulk replacement) → Phase 2 (advanced features). **Corrected order below de-risks by starting with no-anti-bot targets and pushing LinkedIn/proxy work later, once the pattern is validated.**

| Day | Task | File(s) | Why |
|---|---|---|---|
| 1 | Install `crawl4ai>=0.9.2` + `playwright install chromium`. Create `crawl4ai_connector.py` skeleton with import-wrapping + graceful degradation (§6.1) | `requirements.txt`, `crawl4ai_connector.py` | Foundation — nothing else can proceed without this |
| 2 | Replace **news scraping only** (`fetch_news` calls) — no anti-bot risk | `crawl4ai_connector.py`, `intelligence_service.py` | Quick win, validates the pattern end-to-end with zero blocking risk |
| 3 | Replace **company IR page scraping** (`/company/private-intel`, `/osint/company` domain intel) — no anti-bot risk | `market.py`, `crawl4ai_connector.py` | Expands coverage while still avoiding anti-bot sites |
| 4 | Add Docker service with correct resource limits (§11.1) | `docker-compose.yml` | Production readiness before touching harder targets |
| 5 | Test with residential proxy for LinkedIn (§11.2) — stealth mode alone will not work | `crawl4ai_connector.py`, `.env` | Reality check on the hardest target before committing to full replacement |
| 6 | Wire into `intelligence_service.py`'s Apify block — Crawl4AI first, Apify fallback for LinkedIn/PitchBook only | `intelligence_service.py` | Integration |
| 7 | E2E testing (pytest + manual). Keep Apify fallback active for LinkedIn/PitchBook per §6, §14 | Manual + `tests/` | Safety net — do not remove Apify import yet |

### Phase 2 — Advanced Features (post-Day 7, 2–3 days)

| Task | File | Effort |
|---|---|---|
| Adaptive crawling for F-06 network intel | `crawl4ai_connector.py` | 1 day |
| PDF parsing for SEC filings | `crawl4ai_connector.py` | 4 hrs |
| LLM extraction strategy for structured data | `crawl4ai_connector.py` | 1 day |
| Redis caching layer (§12.1) | `crawl4ai_connector.py` | 4 hrs |

### Total Effort: 7 days (Phase 1, corrected order) + 2–3 days (Phase 2) = 9–10 developer days

---

## 11. Installation & Setup

```bash
# Install
pip install "crawl4ai>=0.9.2"

# Install browser (one-time setup)
playwright install chromium

# Verify
python -c "import crawl4ai; print(crawl4ai.__version__)"
```

### Docker Self-Hosting (Production)

> **Lead-required addition:** Current `docker-compose.yml` has no service accounting for Playwright/Chromium's memory needs. Without `shm_size`, Chrome will crash on large pages — this is a well-known Docker+Chromium limitation, not optional.

```yaml
# docker-compose.yml addition
crawl4ai:
  image: unclecode/crawl4ai:latest
  environment:
    - CRAWL4AI_API_TOKEN=${CRAWL4AI_API_TOKEN}
  ports:
    - "11235:11235"
  volumes:
    - crawl4ai_data:/app/data
  shm_size: '2gb'       # CRITICAL: Chrome needs shared memory, default 64MB will crash
  deploy:
    resources:
      limits:
        memory: 4G      # Chromium is memory-hungry
        cpus: '2'
  restart: unless-stopped
```

### 11.1 Resource Management (Lead Gap #4)

Crawl4AI runs Playwright/Chromium instances per crawl. Without limits, bulk research jobs (e.g. F-06 network intelligence crawling 10+ pages per company) can spike memory unpredictably. Mitigations:
- `shm_size: '2gb'` on the Docker service (above) — non-negotiable
- `memory: 4G` limit prevents one runaway crawl job from starving Postgres/Redis/OpenSearch on the same host
- Crawl4AI v0.9.x's built-in `MemoryAdaptiveDispatcher` throttles concurrent workers automatically, but the container still needs a hard ceiling so Docker itself doesn't OOM-kill the wrong process

### 11.2 Proxy Strategy (Lead Gap — Proxy Strategy Gap)

The original proposal said "DIY proxies" without specifying how. LinkedIn and PitchBook need residential-proxy-grade IP reputation — stealth mode alone (patching `navigator.webdriver`, randomizing user-agent) will not bypass their bot detection. Budget **~$20–50/month** for a residential proxy provider (BrightData free tier to start, or similar) if LinkedIn stays in scope after the Day 5 test.

```bash
# Add to .env.example
PROXY_URL=http://user:pass@proxy.brightdata.com:22225  # Or similar residential proxy provider
PROXY_ENABLED=true   # Toggle for local dev (false) vs production (true)
```

```python
# In crawl4ai_connector.py
from crawl4ai import BrowserConfig

browser_config = BrowserConfig(
    headless=True,
    stealth_mode=True,
    proxy=os.getenv("PROXY_URL") if os.getenv("PROXY_ENABLED") == "true" else None,
)
```

If the Day 5 proxy test still fails reliably on LinkedIn/PitchBook, the fallback is: **do not force it** — leave those two sources on Apify permanently (or until Apify's contract is up for renewal) rather than burning more days chasing anti-bot arms races on lower-value data.

### Environment Variables Needed

```bash
# .env — only needed if using Docker server mode
CRAWL4AI_API_TOKEN=your_token_here   # Optional, for Docker API mode
PROXY_URL=http://user:pass@proxy.brightdata.com:22225   # Optional, only if LinkedIn/PitchBook proxy test (Day 5) is approved
PROXY_ENABLED=false                  # Default false for local dev
# APIFY_API_TOKEN stays in .env for the 60-day fallback window — do NOT remove yet
```

---

## 12. Caching & Rate Limiting (Lead Gap — "What to Add for Data Scraping")

### 12.1 Redis Caching Layer

Redis is already running in `docker-compose.yml` (used by the `worker` service). Reuse it to avoid re-crawling the same URL repeatedly within a research session:

```python
# crawl4ai_connector.py
from redis import Redis
import json

cache = Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379)

async def cached_crawl(url: str, ttl: int = 3600) -> str:
    cache_key = f"crawl4ai:{url}"
    cached = cache.get(cache_key)
    if cached:
        return cached.decode("utf-8")
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
    if result.success:
        cache.setex(cache_key, ttl, result.markdown)
    return result.markdown
```

### 12.2 Rate Limiting

Follow the existing `sec_http.py` pattern already used elsewhere in this codebase for per-domain throttling:

```python
# crawl4ai_connector.py
from time import time, sleep

_last_request: dict = {}

def _rate_limit(domain: str, delay: float = 1.0) -> None:
    global _last_request
    elapsed = time() - _last_request.get(domain, 0)
    if elapsed < delay:
        sleep(delay - elapsed)
    _last_request[domain] = time()
```

### 12.3 Schema Registry (Future — not required for Phase 1)

For structured extraction at scale (Crunchbase funding rounds, etc.), store CSS-selector schemas as JSON files rather than inlining them in Python:

```json
// schemas/crunchbase.json
{
    "name": "Funding Rounds",
    "baseSelector": ".funding-round",
    "fields": [
        {"name": "round", "selector": ".round-type", "type": "text"},
        {"name": "amount", "selector": ".round-amount", "type": "text"},
        {"name": "date", "selector": ".round-date", "type": "text"},
        {"name": "investors", "selector": ".investors", "type": "text"}
    ]
}
```

---

## 13. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Anti-bot blocks on LinkedIn/PitchBook | **High** (stealth mode alone is not enough per §11.2) | Medium | Residential proxy (BrightData, ~$20–50/mo) + keep Apify fallback for 60 days as safety net |
| Memory usage spikes on bulk crawls | Low | Medium | `MemoryAdaptiveDispatcher` (v0.9.x) + hard Docker `memory: 4G` limit (§11.1) |
| Chrome crashes on large pages (Docker) | Medium | Medium | `shm_size: '2gb'` on the crawl4ai service — required, not optional (§11.1) |
| Playwright browser crashes | Low | Low | Built-in retry logic + browser pool management |
| Site layout changes break CSS selectors | Medium | Low | Use LLM extraction instead of CSS selectors |
| API rate limits on target sites | Medium | Low | Built-in delay config + `_rate_limit()` per §12.2 + adaptive crawling |
| Proxy budget not approved, LinkedIn stays broken | Low | Low | Fallback is simply: keep Apify permanently for LinkedIn/PitchBook, no forced migration |

---

## 14. Business Value

| Benefit | Value |
|---|---|
| **Cost savings** | $49–$200/month saved = $588–$2,400/year, minus ~$20–50/mo proxy if LinkedIn stays in scope → net $0–$1,800/year saved |
| **Data ownership** | All scraped data stays on client's server (except the 60-day Apify fallback window for LinkedIn/PitchBook) |
| **AI pipeline quality** | Clean Markdown → better LLM analysis → better insights |
| **F-06 enablement** | Adaptive crawling is required for network intelligence graph |
| **Scalability** | No per-page API costs — can crawl 10,000 pages vs Apify's 50-page limit on free tier |
| **No vendor lock-in** | Open source, can fork, always available |

---

## 15. Files Changed Summary (Corrected)

| File | Change Type | Description |
|---|---|---|
| `apps/api/app/connectors/crawl4ai_connector.py` | **NEW** | Core connector, import-wrapped (§6.1) |
| `apps/api/app/connectors/apify_connector.py` | **KEEP (60-day fallback)** | LinkedIn/PitchBook only — remove after Day-5 proxy test proves Crawl4AI can replace it, or keep permanently if it can't |
| `apps/api/app/services/intelligence_service.py` | **MODIFIED** | Real integration point — wire Crawl4AI in next to the existing Apify try/except block (§6.1). *Corrects lead review's reference to the non-existent `deep_research_orchestrator.py`* |
| `apps/api/app/api/market.py` | **MODIFIED** | `/company/private-intel`, `/osint/*` endpoints |
| `apps/api/requirements.txt` | **MODIFIED** | Add `crawl4ai>=0.9.2`; keep `apify-client` until Apify is fully removed |
| `.env.example` | **MODIFIED** | Add `CRAWL4AI_API_TOKEN` (optional), `PROXY_URL`, `PROXY_ENABLED`; keep `APIFY_API_TOKEN` for 60-day window |
| `docker-compose.yml` | **MODIFIED** | Add `crawl4ai` service with `shm_size: '2gb'` and `memory: 4G` limit (§11.1) |
| `ecosystem.config.js` | **NO CHANGE** | PM2 config unchanged |

*Note: `osint_connector.py` was flagged in the lead's review as needing changes ("uses Apify for some lookups") — verified false, it has no Apify dependency. Dropped from scope.*

---

## 16. Approval Checklist (Corrected)

- [x] Lead review of this document — reviewed Aug 3, 2026, approved with modifications
- [ ] Approve corrected Phase 1 scope (7 days, news/IR-pages-first order — §10)
- [ ] Confirm self-hosting is acceptable (no cloud dependency)
- [ ] Confirm 60-day Apify fallback window for LinkedIn/PitchBook is acceptable (not immediate cancellation)
- [ ] Approve Docker addition to infrastructure, incl. `shm_size: '2gb'` + `memory: 4G` limits (§11.1)
- [ ] Approve proxy budget (~$20–50/mo) *if* Day-5 LinkedIn test requires it (§11.2) — or approve permanent Apify retention for LinkedIn/PitchBook if not
- [ ] Sign off on Phase 2 (adaptive crawling for F-06)

---

## 17. References

| Source | URL |
|---|---|
| Crawl4AI Official Docs | https://docs.crawl4ai.com |
| GitHub Repository | https://github.com/unclecode/crawl4ai |
| v0.9.2 Release Notes | https://github.com/unclecode/crawl4ai/blob/main/docs/blog/release-v0.9.2.md |
| Adaptive Crawling Docs | https://docs.crawl4ai.com/core/adaptive-crawling/ |
| Self-Hosting Guide | https://docs.crawl4ai.com/core/self-hosting/ |
| Crawl4AI vs Apify vs Firecrawl 2026 | https://pkgpulse.com/guides/crawl4ai-vs-firecrawl-vs-apify-ai-web-scraping-2026 |
| Finance Research with Crawl4AI | https://github.com/FlowLLM-AI/finance-mcp |
| Apify vs Crawl4AI (Apify's own comparison) | https://use-apify.com/docs/apify-vs-the-world/apify-vs-crawl4ai |

---

*Document created: July 31, 2026 | Updated Aug 3, 2026 with lead review modifications | Approved with modifications — ready for Day 1 implementation*
