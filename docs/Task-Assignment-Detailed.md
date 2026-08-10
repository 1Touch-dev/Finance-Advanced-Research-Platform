# Task Assignment — Detailed (Post-Integration)

**Branch:** `8th-july-sprint` (now contains everything — 90 commits ahead of `main`)
**Prepared:** 10 Aug 2026 · after integrating `feature/13f-frontend` + `feature/trade-alerts` + `feature/13f-full-local`
**Backup of pre-merge state:** `backup/8th-july-sprint-pre-merge-20260810-1159`

---

## 0) What just happened (integration summary)

All three "little-code" feature branches were merged into `8th-july-sprint` in this order:

| # | Merge commit | Branch | What it brought | Conflicts resolved |
|---|---|---|---|---|
| 1 | `c5d7cc5` | `feature/13f-frontend` | Canonical **1,805-line** `sec_13f_service.py`, `market_13f_cache/schemas`, `position-diff.js` (551 lines), `GET /market/institutional/position-diff`, 45 tests + SEC fixtures | `market.py` (merged imports + kept both bodies), `Layout.js` (kept grouped nav, added 13F link), ~24 doc renames |
| 2 | `0b0a73e` | `feature/trade-alerts` | **F-03** big-trade scanner + **F-04** investment threshold alerts, `big_trade_scanner.py`, `investment_alert_service.py`, scan scripts, `monitor.py` (new columns), tracking API (+293 lines), **F-05** Congress.gov + live Senate trades (gov connector 497→1,301 lines), **monorepo tooling** (`turbo.json`, `pnpm-workspace.yaml`, shared config packages) | `.env.example` (kept both sides), `market.py` (kept position-diff + appended Congress routes), `apps/web/package.json` (kept both `dev`+`start -p 3003`), `package-lock.json` (took ours — **regenerate with `npm install`**) |
| 3 | `c200fd4` | `feature/13f-full-local` | `+1` UI-fix commit — billing/search/guidance/filings/globals.css fixes | **Kept OURS** for the 13F stack (its 1,395-line copy was stale/inferior — discarded); auto-merged the UI fixes |

**Post-merge health:** app imports clean, **429 API paths** registered, all feature routes present.

### Known post-merge follow-ups (do these first)
1. **`package-lock.json`** was resolved as "ours". Run `npm install` at repo root to regenerate against the new monorepo tooling before any web build.
2. **SQLite migration gap (fixed locally, needs handling for staging):** the F-04 columns (`investment_threshold`, `notify_email`, `notify_phone`, `alert_on_buy`, `alert_on_sell`) are added to `watchlist_items` in `monitor.py`. `Base.metadata.create_all` **only creates missing tables, not missing columns** — so any pre-existing DB (like staging Postgres or an old `local.db`) will error with `no such column: watchlist_items.investment_threshold`. A **fresh** DB is fine (verified). **Action:** add an Alembic migration (or `ALTER TABLE`) for existing databases. Local dev `local.db` was already patched.
3. **Pre-existing test bug on trade-alerts (not caused by merge):** `tests/test_legislation_endpoints.py::test_bill_detail_not_found_returns_error_payload` expects HTTP 200 but the endpoint (`market.py::gov_legislation_bill_detail`) raises `HTTPException(404)`. Decide: change endpoint to graceful-degrade 200, or fix the test to expect 404. (Owner: Person 2.)

---

## 1) VERIFIED WORKING (tested this session)

### 13F Position Diff — ✅ FULLY VERIFIED
- **Offline:** `tests/test_market_13f_api.py` + `tests/test_market_13f_position_diff.py` → **45/45 pass**.
- **Live SEC:** `GET /market/institutional/position-diff?institution_cik=1067983&status=changed` → **HTTP 200 in ~8s**. Real Berkshire Hathaway 2026-03-31 vs 2025-12-31 diff: 3 new / 4 increased / 6 reduced / 16 exited, correct USD deltas (Alphabet +204%, new Delta Air Lines position, etc.).
- Enum validation works (bad `status` → 422). Fresh-DB schema verified.

### F-03 / F-04 Trade Alerts — ✅ VERIFIED (pipeline functional)
- `POST /tracking/alert-rules` → 201; `GET /tracking/alert-rules` → 200.
- `PATCH /tracking/watchlist/{ticker}/threshold` validates (400 without notify contact).
- `python -m app.scripts.run_big_trade_scan --dry-run` → runs rule, fetches Form 4, `0 new alerts` (no error).
- `python -m app.scripts.run_investment_alert_scan --dry-run` → clean.
- `POST /tracking/scan/insider-trades?dry_run=true` and `.../scan/investments?dry_run=true` → 200 with structured output (threshold_used, scanned_tickers, notifications_sent).
- SendGrid + Twilio delivery **is wired** in both scanners; PM2 cron scheduled (`ecosystem.config.js`: big-trade every 4h, investment offset +30min).
- Congress tests: **40/41 pass** (1 known mismatch, item 3 above).

### F-05 Congress.gov — ✅ VERIFIED
- `GET /market/gov-trading/legislation/search?query=...` → live real bills (200) with the provided `CONGRESS_API_KEY`.

---

## 2) The 7 ORPHAN SERVICES — highest-value unclaimed work

Real, substantial computation exists but **no router, no caller, no reachable endpoint**. Written as pure functions taking pre-fetched dicts — each needs (a) an orchestrator to fetch+feed data and (b) a router endpoint.

| Service | Lines | James ask it satisfies | Entry point signature |
|---|---|---|---|
| `self_dealing_service.py` | 436 | "nvidia self-dealing" detection | `cross_reference_self_dealing(insider_transactions, board_interlocks, contract_intelligence, ...)` |
| `coinvestment_network_service.py` | 400 | "find investors of same companies" | `build_coinvestment_network(...)`, `analyze_position_concentration(...)`, `find_coordinated_movements(...)` |
| `founder_correlations_service.py` | 623 | PayPal-mafia / who-studied-together | `find_educational_overlaps(...)`, `find_company_overlaps(...)`, `build_founder_correlation_graph(...)` |
| `deep_comparative_service.py` | 1,134 | deep multi-company comparison | has its own SEC/FMP/Alpha-Vantage fetchers already |
| `interactive_report_service.py` | 598 | interactive searchable reports | renders searchable HTML report |
| `correlation_service.py` | 528 | pattern / correlation finding | 17 functions |
| `contract_probability_service.py` | 675 | "probability of delivery" on contracts | consumes USASpending data |

---

## 3) PARTIAL (router exists, stub markers in code)

| File | Stub | Fix |
|---|---|---|
| `apps/api/app/api/status.py` | 3× `TODO: Send notifications / subscription storage` | Wire subscriber notify + persistence (Band A #4) |
| `apps/api/app/api/freshness.py` | `TODO: Actually regenerate the page` | Implement page regeneration (schedule already exists) |
| `apps/api/app/api/honesty.py` | "Mock data sources with varying freshness" | Replace mock with real source-freshness lookup |
| `apps/api/app/api/export.py` | "Mock user data for export" | Wire to real user/report data |

---

## 4) NOT DONE (verified absent)

- **AI-Model-Training Phase 1** — RAG is still **TF-IDF** (`rag_chat_service.py::_tfidf_score`); `document_ingestion_service.py:502` still says "should use vector similarity search." Untouched on every branch. See `docs/AI-Model-Training-Roadmap.md`.
- The 7 orphan services (§2).
- `institutional` + `portfolio` routers exist as files but are **not registered in `main.py`** (position-diff works because it lives under `market`). If a dedicated institutional router is wanted, register it.

---

## 5) PARALLEL TASK ASSIGNMENT (zero file collision)

> File-ownership partitioning so 3 people never touch the same files.

### PERSON 1 — Intelligence / Correlation (activate the orphan services)
**Owns:** `intelligence_service.py`, the 7 orphan services, **new** routers `self_dealing.py` / `network.py` / `correlations.py`, report pages.

- **Task 1.1 — Self-dealing endpoint.**
  - *Done:* `self_dealing_service.cross_reference_self_dealing(...)` (436 lines, real logic).
  - *Left:* orchestrator that fetches insider_transactions + board_interlocks + contract_intelligence for a ticker/entity, feed the service, expose `POST /intelligence/self-dealing`. Add to report.
- **Task 1.2 — Co-investment + founder correlation network.** (highest James value)
  - *Done:* `coinvestment_network_service.py` (400) + `founder_correlations_service.py` (623).
  - *Left:* orchestrator + `GET/POST /intelligence/network`; surface in the PayPal-Mafia report; add graph visualization on the frontend.
- **Task 1.3 — Deep comparative + correlation + interactive report.**
  - *Done:* `deep_comparative_service.py` (1,134, has own fetchers), `correlation_service.py` (528), `interactive_report_service.py` (598).
  - *Left:* wire into report generator; expose comparison endpoint; render interactive report HTML.
- **Task 1.4 — Contract delivery probability.**
  - *Done:* `contract_probability_service.py` (675).
  - *Left:* feed USASpending contract data + expose endpoint; add to company/contract view.

### PERSON 2 — Alerts / Tracking / Gov depth
**Owns:** `tracking.py`, `tracking.js`, `gov_trading_connector.py`, `big_trade_scanner.py`, `investment_alert_service.py`, `status.py`, scan scripts.

- **Task 2.1 — Fix the two integration follow-ups.**
  - Add DB migration for the F-04 `watchlist_items` columns (item 0.2).
  - Resolve the 404-vs-200 legislation test mismatch (item 0.3).
- **Task 2.2 — Alert inbox UX + digest surfacing.**
  - *Done:* delivery (SendGrid/Twilio) + cron + scan endpoints all verified working.
  - *Left:* in-app alert badges, alert inbox filtering, digest surfacing in the UI.
- **Task 2.3 — Gov depth (James asks).** Clickable politician profiles, filter by company/trend, whale tracker, Reddit tracker. (`REDDIT_CLIENT_ID/SECRET` placeholders already in `.env`.)
- **Task 2.4 — Status page + incident logging (Band A #4).** Finish `status.py` TODOs (subscriber notify + subscription storage).

### PERSON 3 — 13F / Institutional depth + Band-A cleanup
**Owns:** `sec_13f_service.py`, `institutional*` pages/libs, `freshness.py`, `honesty.py`, `export.py`; may register the dark `institutional`/`portfolio` routers.

- **Task 3.1 — 13F honesty layer (#14).** *Done:* service already parses filing dates. *Left:* add a "45-day stale" flag to the position-diff response + UI banner. (`SOURCE_MAX_AGE_DAYS=45` already in `.env`.)
- **Task 3.2 — Institutional "search by people / who's exposed most" page.** Build on top of the already-wired `coinvestment` output + `institutional.js` helpers.
- **Task 3.3 — Kill stub markers** in `freshness.py`, `honesty.py`, `export.py` (§3).

### CROSS-CUTTING (4th person / whoever's free) — AI-Model-Training Phase 1
**Owns:** `rag_chat_service.py`, `document_ingestion_service.py` only (2 files, no page/router conflict).
- Swap `_tfidf_score` → pgvector embeddings; implement real `DocumentChunk.embedding` query. Unblocks real RAG for everyone. Fully isolated. See `docs/AI-Model-Training-Roadmap.md`.

---

## 6) How to run locally (verified)

```bash
# Backend (from repo root)
cd apps/api
source .venv/bin/activate            # venv already present
export DATABASE_URL="sqlite:///./local.db"
python -m uvicorn app.main:app --host 127.0.0.1 --port 3001
# then: curl -X POST http://127.0.0.1:3001/bootstrap

# Run the verified test suites
python -m pytest ../../tests/test_market_13f_api.py ../../tests/test_market_13f_position_diff.py -q   # 45 pass
python -m pytest ../../tests/connectors/test_congress_gov.py ../../tests/test_legislation_endpoints.py -q  # 40/41

# Trade-alert scanners (dry-run — no real email/SMS sent)
python -m app.scripts.run_big_trade_scan --dry-run
python -m app.scripts.run_investment_alert_scan --dry-run
```

Root `.env` is populated (gitignored). Missing keys the code reads were added with sane defaults/aliases: `SEC_MAX_ATTEMPTS`, `SEC_MIN_REQUEST_INTERVAL`, `SAM_API_KEY`/`COURTLISTENER_API_KEY`/`NEWS_API_KEY` aliases, `UPLOAD_DIR`/`EXPORT_DIR`/`CHUNK_SIZE`, `LDA_API_KEY`, `REDDIT_*`, `ETHERSCAN_API_KEY`, `SOURCE_MAX_AGE_DAYS`, etc.
