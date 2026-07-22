# Finance Intelligence Platform — Roadmap (Week / Month / Lifetime)

**Date:** 20 July 2026
**Branch:** `8th-july-sprint`
**Ordering rule:** **Report improvements are priority #1** everywhere. Within each horizon, items are listed highest-priority first.
**Sources:** `docs/WhatsApp Chat - KYMA…/_chat.txt`, `docs/James_Tasks_Complete_Checklist.md`, `docs/16th_July_Status_and_Scope.md`, `docs/Technical_Knowledge_Transfer.md`, `docs/FINANCE_PLATFORM_FEATURES_AND_STRATEGY.md`, `reports/*`, `reports/Hemispheric Dollar Corridor Annex…pdf`, `memory/*` (treated as vision only — status is stale).

---

## 0. TL;DR

- The report **engine is real and broad** (15+ sections, 15+ connectors, GPT‑4o‑mini narrative, graph edges). The **Premium PDF is already ~70% to the Hemispheric bar on structure** (BOTTOM LINE, rated thesis, financial table, agency breakdown, risk matrix, watch items). The problems are (a) the **Enhanced PDF pipeline loses its data on reload** (KPIs zero, bodies drop to headings), (b) **Premium rendering bugs** (raw markdown/table pipes leaking, truncation, "Tesla ()" ticker, repeated footer, stale LLM financials), and (c) **no people/network/relationship depth** — the single biggest gap vs Hemispheric.
- **Root cause of "empty" Enhanced reports:** `summary` (KPIs), section `.data`, and enhanced structured fields (thesis/SWOT/risk/financial_health) are computed at generation time but **never persisted**; enhanced claim text is **truncated (~1000 chars)**. On reload/export it reads back zeros/stubs.
- **Fixed today:** export pipeline (Beautiful/Pro/MD/detailed all 200), missing Python deps (installed + `pyproject.toml` + Docker), two `list_*` 500 bugs, export-panel render bug, route-shadow bug, UI wiring for all export formats, Node pinned so web build survives.
- **Sequence:** THIS WEEK = make reports correct + P0 bugs → THIS MONTH = Hemispheric-depth narrative + **deep research agents** + report intelligence features → LIFETIME = autonomous global intelligence engine.

---

## 1. What was fixed today

| Area | Problem | Fix |
|------|---------|-----|
| Deps | `weasyprint`, `markdown`, `openpyxl`, `python-pptx`, `yfinance`, `matplotlib` used but **not in prod `venv`**; weasyprint/markdown not in `pyproject.toml` | Added to `pyproject.toml`; installed into `venv`; added WeasyPrint OS libs to `apps/api/Dockerfile` |
| List 500 | `list_intelligence_reports`/`list_enhanced_…` called `.isoformat()` on a string (SQLite) → Saved Reports 500 | Guarded (`intelligence_service.py:1626`, `:1919`) |
| Export panel | `intelligence.js` panel gated on `report.id` (object uses `report_id`) → never rendered | Fixed + wired all formats |
| Route shadow | `GET /intelligence/enhanced` caught by `/{report_id}` → 422 | Reordered |
| UI wiring | New export endpoints not surfaced | Added to `intelligence/[id].js`, `intelligence.js`, `saved.js` |
| Web build | Next 12 crashes on Node 25 | `.nvmrc=18` + `engines`; verified clean on Node 22 |
| Docker local | `api` didn't load `.env` → no keys → thin reports | `env_file: .env` added |

**Verified live:** all 9 export routes return 200 with valid files; markdown/PDF pipeline robust on empty/None/malformed reports.

---

## 2. Root cause of the quality gap (must-fix)

**Goal** (`reports/Hemispheric Dollar Corridor Annex…pdf`): analyst-grade — multi-track thesis w/ BOTTOM LINE, deep **personnel dossiers** (career/education/financial entanglements), **network mapping** (PayPal-mafia style), historical annexes, legal mechanics, inline citations, watch-items.

**There are two current PDF pipelines and they are in very different states** (both compared below against the goal, not the thin `Tesla_Intelligence_Report_20Jul2026.md`):

### 2A. Premium (`reports/Tesla_Premium_Intelligence_Report.pdf`) — the GOOD one, ~70% to goal on *structure*
Already produces analyst-grade scaffolding: **BOTTOM LINE** executive assessment, rated Investment Thesis (Buy/High/Overweight, bull case), Financial Health metrics table, Competitive Positioning w/ market share, Government Contracts w/ **agency-breakdown table + portfolio-share %**, Lobbying **issue-area/intensity table**, News table, **Risk Matrix (severity×likelihood)**, **Watch Items**, Monitoring Recommendation, citation markers. This is close to Hemispheric on format.

**But its blockers (all visible in the PDF):**
| Symptom (in the PDF) | Cause | Location |
|---|---|---|
| Raw markdown leaks — literal `#`, `##`, `####`, and `\| Metric \| Value \|` table pipes printed instead of rendered | AI section text passed through without full MD→HTML conversion | `markdown_pdf_service.py` render path + `report_prompts.py` output |
| Sections cut off mid-content (Bull Case ends abruptly; Competitor table cut mid-row) | claim/section text truncation | `intelligence_service.py` enhanced claim truncation (~1000 chars) |
| Ticker prints as **"Tesla ()"** in BOTTOM LINE | empty ticker interpolation | prompt/template var not populated |
| Footer "Prepared for internal use… Page 1 Page 2 …" repeated inline across every page | WeasyPrint running-element/footer misconfig | `markdown_pdf_service.py` CSS `@page` |
| Financials are **stale LLM figures** ("Revenue $81.46B (2022)") not live data | narrative uses model knowledge, not yfinance/section data | `enhanced_narrative_service.py` financial prompt |
| **No people / network / relationship section at all** | not generated — the biggest gap vs Hemispheric | new work (see §4) |

### 2B. Enhanced (`reports/Tesla_Enhanced_Intelligence_Report_20Jul2026.pdf`) — the BROKEN one
| Symptom (in the PDF) | Cause | Location |
|---|---|---|
| Executive Dashboard KPIs **all zero** (SEC 0, Contracts 0 ($0), Lobbying 0, News 0) — yet body lists $47M contracts + 8 news items | `summary{}` not persisted / not recomputed on reload | `intelligence_service.py:1511-1618`, `:1843-1910`; `intelligence.js:787` |
| Thesis / Exec Summary / Financial Health / Competitive render as **headings only** (body dropped) | enhanced structured fields dropped on reload; claim text truncated | `intelligence_service.py:1781-1783`, `:1843-1910`; `enhanced_narrative_service.py:354-515` |
| Contracts section header "Total Obligated: **$0** / Award Count: 0" but bullets list the real $47M awards | section `.data` aggregate not stored; export reads `sec.get('data')` | `intelligence_service.py:1482-1485`; `markdown_pdf_service.py:649-687`; `intelligence.js:785` |
| Lobbying "Total Filings: 0" + empty grids | same persistence gap + SWOT/Risk parse can fail | as above |

**Takeaway:** narrative bodies ARE generated in full (Premium proves it). The Enhanced hollow look is a **storage/retrieval + wiring** bug; the Premium gap is **rendering polish + missing people/network depth + live-data**. Fix Enhanced's persistence, then converge both onto the Premium generator and add the network layer.

---

# 3. THIS WEEK — make reports correct + unblock platform

### P1a — Fix the Enhanced pipeline (persistence + wiring) · highest priority
1. **Persist `summary` + section `.data` + enhanced structured fields** (JSON columns / `report_meta`); rehydrate in `get_intelligence_report` / `get_enhanced_intelligence_report`. → kills the "KPIs all zero / Total Obligated $0" while body shows $47M.
2. **Stop truncating enhanced claims** at ~1000 chars → full TEXT. → kills Bull-Case / competitor-table cut-off.
3. **Frontend: keep summary/data on historic load** (`intelligence.js:785,787`).
4. **Wire `/generate-enhanced` into the UI** — "Enhanced (AI)" toggle so thesis/SWOT/risk populate and carry into Pro/Beautiful PDF.
5. **KPI fallback** — recompute counts from section claims when `summary` absent (fixes old reports too).

### P1b — Fix the Premium PDF rendering bugs (it's ~70% to goal, don't waste it)
6. **Render markdown properly** — stop raw `#`/`##`/`####` and `| … |` table pipes leaking; run all AI section text through MD→HTML (`markdown_pdf_service.py`).
7. **Fix ticker interpolation** — "Tesla ()" → "Tesla (TSLA)".
8. **Fix the repeated inline footer** — WeasyPrint `@page` running-element so "Prepared for internal use… Page N" appears once per page, not inline ×9.
- **Exit:** a saved Tesla report re-opens/exports with real KPIs + real contract totals (Enhanced), and Premium PDF has clean typography, full un-truncated sections, correct ticker, single footer.

### P2 — Report content correctness
9. **Live financials, not LLM memory** — replace "Revenue $81.46B (2022)" style stale figures with yfinance/section data + as-of date.
10. **Two-sided contracts** (recipient ⇄ awarding-agency ⇄ subcontractor) — `_fetch_usaspending` `:310`.
11. **Inline citations** — every claim carries `source_url`, rendered as footnotes (Premium already shows markers; make them resolve).
12. **Robust SWOT/Risk parsing** so grids never blank when prose exists.

### P3 — P0 page bugs (parallel; James reported these broken)
13. Sentiment (`/expert-analysis` · `expert_analysis_connector.py`).
14. Earnings-growth buttons (`/company`).
15. Institutional "nothing appearing" (`institutional_tracker.py`).
16. "Reports not generating" (distinct from persistence — verify generate path end-to-end).
17. Apollo integration (`apollo_connector.py`, needs `APOLLO_API_KEY`).
18. Wrong-entity data (Citigroup showing no Apple info) — `/expert-analysis`.

### P4 — Ship
19. `docker compose up` locally (Docker Desktop on); `git pull` + venv deps + WeasyPrint OS libs + `pm2 reload` on EC2 (see §6).

---

# 4. THIS MONTH — Hemispheric-depth reports + agentic research

> Premium already has BOTTOM LINE / rated thesis / risk matrix / watch items. The Month gap vs Hemispheric is **people, network, and visuals** — that's what's entirely missing today.

### P1 — Add the people/network layer + visuals (converge on Premium generator)
1. **Personnel dossiers** — per key person: role, career history, **education**, board seats, financial entanglements, cross-company ties (Hemispheric-style). Premium currently has *no* people section.
2. **Network / relationship section in the report** — co-education + co-employment + co-investment edges (PayPal-mafia mapping), rendered as a diagram + narrative.
3. **Report-embedded visualizations / mapping** — network diagram, contract/lobbying charts, timeline graphic (toward Hemispheric visual quality).
4. **Deepen remaining prompts** (`templates/report_prompts.py`) — competing-structure analysis, historical annex, legal mechanics, Outlook.

### P2 — Deep Research Agents  ⟵ **NEW next-task (James 18 Jul)**
> *"We need to start interpreting and analyzing data, potentially running agents to do further research, find subsidiary companies, family details, everything we can find as well as all APIs."*

5. **Agentic research loop** that, given an entity, autonomously:
   - **Interprets & analyzes** pulled data (not just lists it) — synthesis + "so what".
   - **Subsidiary / parent / UBO discovery** (recursive via GLEIF, OpenCorporates, SEC) — `intelligence_service.py:1343-1352` today is one-shot.
   - **Family / associate / relationship discovery** (people ↔ people).
   - **Cross-source correlation** — reconcile SEC + FEC + FARA + lobbying + news + registries into one narrative.
   - **Uses all available APIs/connectors** + browser agent for gaps (`browser_research_agent.py`), with follow-up research when new leads surface.
   - Foundations exist (`skills.py` `/skills/run`, `multi_agent_intelligence.py`, browser agent) but are **not orchestrated into the report** — this task wires them into an entity-research agent.

### P3 — Report intelligence features (James 16 Jul vision)
6. **Shared-investor / co-investment overlap** — "who else invested (non-gov) in multiple of these companies" (SEC 13G/13D + PitchBook + FundedAPI).
7. **Entity similarity search** — "find similarities in entities, lobbying, all sources" (pgvector over entity profiles).
8. **Multi-company comparison depth** — by founders / directors / advisors / **investors (=clients)**; replace text-heuristic overlap in `compare.js:186-220` with graph-based.
9. **AI pattern detection** across entities; **decision interpretation** — "why specific people are making key decisions."
10. **Government / large-player connection synthesis** + relationship-**effect** typing (local / corporate / government / customer-acquisition).

### P4 — Timelines
11. **Person timelines** (meetings/purchases/trips) + **news overlay** + **stock price**, clickable (fix `timeline.js`, `search.py:77-100`).

### P5 — Platform / page features (14 Jul list, parallel workstream)
12. Entity registry cleanup (single enrich, names+details) · `/registry`.
13. Relationship visualizer clarity + add/compare people ("graph function not clear") · `/graph`.
14. Search autofill name→ticker · `/company`,`/stock`.
15. Financials: all years + filters + clickable + **editable table** · `/company`.
16. Valuation: filtered RSS per stock + perspectives summary · `/valuation`.
17. Institutional: search-by-people, exposure ("who's exposed most") · `/institutional`.
18. Gov-trading: clickable profiles, filter by investment/company, trends · `/gov-trading`.
19. Track **funds / PE / VC** as first-class entities.
20. Crypto: **whale + news + Reddit** trackers · `/crypto`.
21. Deeper LinkedIn (employees/key hires) + deep **private-company financials** (contracts/valuations/capital raised).

---

# 5. LIFETIME VISION & TASKS

The platform becomes an **autonomous global financial-intelligence engine** producing analyst-grade, interactive, continuously-updated dossiers on any entity or network.

- **Autonomous research at scale** — always-on agents that discover new entities, subsidiaries, people, and relationships, and refresh dossiers as the world changes.
- **Global knowledge graph** — people ↔ companies ↔ schools ↔ funds ↔ governments ↔ contracts, with provenance/citations on every edge; PayPal-mafia-scale network analysis on demand.
- **Interactive intelligence workspace** — per-entity RAG chat, compare-chat, PDF-from-chat, drill-down from any claim to sources, live graph exploration.
- **Global markets & news interpretation** — real-time ingestion (RSS Phase 2: 200+ feeds, event clustering, contradiction detection), pattern/anomaly detection, "why is this happening" synthesis.
- **Monitoring & alerting** — watchlists, daily digests, custom alert rules, Slack/email/SMS.
- **Similarity & pattern engine** — pgvector + graph analytics for "find similar / find the pattern / find the network."
- **Total data coverage** — all APIs + international registries (40+ countries), Crawl4AI migration off Apify, private-market financials.
- **Enterprise hardening** — SSO, multi-tenant/RBAC, audit trails, Amplify/ECS, autoscaling, cost controls.

**Out of scope of THIS product (separate programs, spec-only):** Jarvis Nexus Dashboard (`docs/Jarvis Nexus Dashboard UI Spec (2).docx`), AI Agent Team / GTM (`docs/Enterprise Intelligence Platform v2.0 Requirements.docx`). James (22 Jun): Financial Intelligence Platform first; those "at some point."

---

## 6. Deployment runbook

### Local — Docker (start Docker Desktop first)
```bash
docker compose build
docker compose up -d          # postgres:5433, redis, minio, opensearch, api:3001, web:3000, admin:3002, worker
docker compose logs -f api    # expect "Application startup complete"
curl http://localhost:3001/health
```

### EC2 — PM2 (`ssh finance-intelligence` → 184.72.123.188)
```bash
cd ~/Finance-Advanced-Research-Platform && git pull origin 8th-july-sprint
sudo apt-get update && sudo apt-get install -y \
  libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 libffi-dev fonts-dejavu-core
./venv/bin/pip install -e apps/api
cd apps/web && nvm use 18 && npm ci && npm run build && cd ../..
pm2 reload ecosystem.config.js && pm2 status
```
**Gotchas:** never build web on Node 25; Beautiful PDF 503s without WeasyPrint OS libs; Amplify → Node 18/20 + `NEXT_PUBLIC_API_URL` → EC2 API.

---

## 7. Open items needing James
- Approve Apify LinkedIn/PitchBook actor permissions + billing card ("brown") on paid APIs — blocks deep research agents + network depth.
- Google SSO OIDC creds; Congress.gov paid key; ALEPH/OCCRP + CA SOS approvals (CA SOS has BizFile workaround).
- Confirm saved-report **DB migration** can run on EC2 Postgres (brief downtime for schema change).
- Sign-off on "Enhanced (AI)" as the default report path.

---

## 8. Appendix — traceability (every James ask → horizon)

| James ask | Horizon |
|---|---|
| Interactive reports / similarity search | Month P3 #7 |
| Comparisons between companies | Month P3 #8 |
| Find investors of same companies / co-investment | Month P3 #6 |
| All stats / KPIs / complete data | **Week P1a** |
| AI find patterns/key factors | Month P3 #9 |
| PayPal-mafia schools/founders | Month P1 #1–2 |
| Report incl. company/people/employees/decisions/lobbying/all data | Week P1 + Month P1 |
| Relationship effect insights | Month P3 #10 |
| Interpret why people make key decisions | Month P3 #9 |
| Timelines + news + summaries | Month P4 #11 |
| Connections to governments/large players | Month P3 #10 |
| Detailed visualizations/mapping/graphics | Month P1 #3 (+ Week P1b render fixes) |
| Complete reports: investors/employees/contracts/lobbying analysis | Week P1 + Month P1 |
| Compare by founders/directors/advisors/clients(=investors) | Month P3 #8 |
| Contracts — all details + two-sided | Week P2 #10 |
| Interpret & analyze data + run agents (subsidiary/family/all APIs) | **Month P2 #5** |
| LinkedIn relationships / deeper (employees/key hires) | Month P5 #21 |
| Private company financials | Month P5 #21 |
| Entity registry cleanup | Month P5 #12 |
| Relationship visualizer / "graph unclear" | Month P5 #13 |
| Expert analysis perspectives / sentiment broken / wrong-entity | Week P3 #13,#18 + Month P5 |
| Earnings buttons broken | Week P3 #14 |
| Stock price on timeline + news | Month P4 #11 |
| Search autofill name→ticker | Month P5 #14 |
| All-years + editable financials | Month P5 #15 |
| Valuation filtered RSS + perspectives | Month P5 #16 |
| Track funds/PE/VC/institutional/whales | Month P5 #17,#19,#20 |
| Institutional search-by-people / exposure | Month P5 #17 (+ Month P3 #6) |
| Institutional "nothing appearing" | Week P3 #15 |
| Gov-trading clickable/filters/trends | Month P5 #18 |
| Whale + news + Reddit trackers | Month P5 #20 |
| Reports not generating | Week P1a + P3 #16 |
| Timeline meetings/purchases/trips | Month P4 #11 |
| Raw markdown / footer / ticker / truncation in PDF | Week P1b #6–8 |
| Stale LLM financials → live data | Week P2 #9 |
| API approvals / workarounds / billing card | §7 |

*Author: platform maintenance pass, 20 Jul 2026.*
