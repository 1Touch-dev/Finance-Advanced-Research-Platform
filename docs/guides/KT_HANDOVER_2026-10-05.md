# Knowledge Transfer — Finance Advanced Research Platform

**Prepared:** 5 October 2026
**Prepared by:** Anshuman Parmar (admin@kyma.world)
**For:** New developer taking over this codebase
**Repo:** https://github.com/1Touch-dev/Finance-Advanced-Research-Platform
**Active branch:** `8th-july-sprint` (do not push to `main` directly)

Read this whole document before touching code. Section 2 especially — this project has a documented history of commit messages overstating what actually works, and you will waste real time if you take the last commit's "85%" claim at face value instead of what's in Section 2.

---

## 1. The Vision (what the client actually wants)

**Client:** James Deller, Thunder Marketing (primary contact — requirements come via WhatsApp, see `JAMES_ASKS.txt` for the raw chat log of asks).

This is **not** a stock screener or a generic AI report generator. It's meant to be an **evidence-first financial/political intelligence platform** — think "Bloomberg Terminal meets OSINT investigator," combining:

- **9-section cited intelligence dossiers** on companies/people (profile, investors, gov contracts, lobbying, political/foreign exposure, sanctions, litigation, AI narrative, sources) — every claim tagged DOCUMENTED / REPORTED / ANALYTICAL, traceable to a source. This "evidence first" principle is the core product differentiator the client cares about most.
- **"Follow the money"** — government/politician trading intelligence (STOCK Act PTRs, Form 4 insider trades, Congress.gov legislation), ranked leaderboards of officials by trade volume/ROI.
- **"PayPal Mafia" style entity/relationship graphs** — network mapping of investors, board members, advisors across companies (client has explicitly asked this go beyond PayPal/Nvidia to cover all core members' current investments, boards, hires).
- Standard investor tooling on top: DCF valuation, 35+ financial ratios, technical indicators, 13F institutional tracking, portfolio/watchlist/alerts.
- Export everything (PDF/Word/Excel/PPT), RAG chat per-report.

Full historical context docs (read if you want the "why," not needed day one):
- `docs/architecture/context.md` — project goals/phases
- `docs/requirements/FINANCE_PLATFORM_FEATURES_AND_STRATEGY.md`
- `JAMES_ASKS.txt` — raw client chat log, all feature asks
- `docs/requirements/external/james/` — more client requirement docs

---

## 2. ⚠️ Real State of the Project — Read This First

### The headline number you'll see is wrong — here's why

The last commit on this branch (`76c066c`, "docs: add audit cycle explanation") documents a pattern that repeated for roughly a week before it: an agent/developer would claim a completion jump in a commit message (e.g. "wire 5 pages — 72% to 75%"), and an independent audit would re-verify and find the real number was 35-45%, because the commit counted *files/routes/pages created*, not *whether data actually flows end-to-end*.

On **26 August 2026** (the last day of activity on this repo — nothing has been touched since), this happened one more time, in one burst, same day:

```
09:00 audit → 45% verified (docs/INDEPENDENT_AUDIT_2026-08-26.md, MASTER_TASK_STATUS.md)
13:19 commit → "45% to 52%"
14:40 commit → "52% to 68%"  (Sentry + API consolidation)
15:14 commit → "68% to 72%"  (rate limiting, health probes)
15:34 commit → "72% to 75%"  (wire 5 pages)
15:41 commit → "75% to 80%"  (wire 4 more pages)
15:43 commit → "80% to 85%"  (wire 3 more pages)
23:29 commit → docs explaining why this exact pattern is dishonest
```

**No audit was re-run after the 85% claim.** Given the project's own established pattern, treat "85%" as unverified marketing until someone re-runs the audit methodology (see `docs/INDEPENDENT_AUDIT_2026-08-26.md` Section "Strict Verification Checklist" for how). My honest estimate, not having re-audited myself: somewhere in the 45-55% range for genuine end-to-end completion, with real but unverified improvements (Redis caching, Sentry, rate limiting, health endpoints) layered on top of the 45% baseline.

**First thing I'd do in your shoes:** re-run the independent audit methodology from `docs/INDEPENDENT_AUDIT_2026-08-26.md` against current `HEAD` before planning any new work. Don't trust commit messages or percentage claims anywhere in this repo's history — verify against running code.

### What the last verified audit (26 Aug) actually found

✅ **Genuinely working, verified end-to-end:**
| Feature | Data Source |
|---|---|
| User Authentication (JWT+bcrypt) | real |
| Gov Trading Leaderboard | static JSON, 633 officials (real, parsed from Excel) |
| Earnings / IPO Calendar | Finnhub / FMP |
| Short Interest | FINRA |
| Stock quotes/fundamentals/technicals | yfinance |
| Insider activity (Form 4), SEC filings | SEC EDGAR |
| Analyst scoring | Finnhub |
| RAG chat | vector+keyword hybrid, F1=0.895 quality classifier (**but see live finding below — classifier shows `not_trained` in production right now**) |

⚠️ **Partially working:**
- Entity graph (DB-backed now, but **live production logs show it's actively erroring** — see Section 3)
- Intelligence report generation (can crash on a fresh DB — missing-table error class)
- Portfolio tracking (real yfinance prices, but auth not propagated to every page)
- FRED/guidance/consensus data (works only if API keys are present)

❌ **100% stubs (not partially done — every function returns a "not configured" response, zero real logic):**
| Service | Blocked on |
|---|---|
| `brokerage_sync_service.py` | No Plaid contract signed |
| `narrative_model_service.py` | No GPU infra provisioned |
| `pwa_advanced_service.py` | Not implemented |
| `mobile_pwa_service.py` (push only) | No VAPID keys |

These need **business decisions from the client**, not more engineering, until the blockers above are resolved (see Section 7).

### Production blockers called out in the last audit (still unresolved as far as I can tell)
- Only 2-3 Alembic migrations exist for 64+ SQLAlchemy models — a fresh Postgres deploy may not match the models.
- Intelligence report generation can throw `sqlite3.OperationalError: no such table: reports` on a fresh DB.
- Entity graph persistence across restarts was never verified in the audit — and per Section 3 below, it's actually broken right now in a different way.
- No real monitoring/alerting was wired as of the audit (Sentry was added same-day in the unverified 85%-claim commits — worth checking if it's actually catching anything).

---

## 3. Live Environment — What I Found When I Actually Checked (5 Oct 2026)

I SSH'd in and checked, rather than trusting docs. Here's ground truth as of today:

### Access
- **EC2 host:** `184.72.123.188` (user: `ubuntu`)
- **SSH:** key at `~/Documents/Security_Files/finance-intelligence.pem` on my machine. My local `~/.ssh/config` has an alias:
  ```
  Host finance-intelligence
      HostName 184.72.123.188
      User ubuntu
      IdentityFile ~/Documents/Security_Files/finance-intelligence.pem
  ```
  Get the `.pem` file and this alias set up on your own machine (ask me or whoever holds the AWS account for the key — I won't paste the private key into this doc). Once configured: `ssh finance-intelligence`.
- **Live URLs:**
  - Web app: http://184.72.123.188:3003
  - API: http://184.72.123.188:3001 (docs at `/docs`)
  - Admin panel: http://184.72.123.188:3002
  - All three responded `HTTP 200` when I checked just now — the staging box is up and reachable.
- **Staging login:** `abhishekk@kyma.world` / `Kulkarni@2002` (from the previous handoff doc, unverified whether still valid — if it fails, just `POST /auth/register` your own account, that endpoint works).
- **Server repo path:** `/home/ubuntu/Finance-Advanced-Research-Platform`

### ⚠️ Important: the server is NOT running your local `HEAD`

```
Local HEAD (8th-july-sprint):   76c066c, 2026-08-26 23:29  (the "85%" claim + audit-cycle doc)
Server HEAD (8th-july-sprint):  4978318, 2026-08-24 23:41  ("fix: logging typo + test stability + Redis token blacklist")
```

The server is **2 days and ~10 commits behind** local, including all of: comprehensive audit, Redis caching, Sentry monitoring, rate limiting, health probes, and the 6 "wire pages" commits. None of that is deployed. The server also has some uncommitted local changes/leftover files (`intelligence_service.py.backup2`, `.bak`, `ecosystem.pm2.json`, a `models/` dir) — worth diffing before you deploy over them so you don't silently lose something.

**Don't assume "it's live so it must work."** Verify what's actually deployed before testing against staging, and expect to need a deploy pass to get the server current.

### PM2 process status (checked live)

```
finance-admin   online   uptime 2 months   1 restart
finance-api     online   uptime 41 days    339 restarts  ⚠️
finance-web     online   uptime 41 days    70 restarts   ⚠️
rss-poller      online   uptime 2 months   0 restarts
```

339 restarts on the API process in 41 days (~8/day) and 70 on web is high — points to something crash-looping or getting OOM-killed periodically. Worth investigating (`pm2 logs finance-api --lines 200`) before assuming stability.

### Live bug caught in production logs right now

The API logs are actively, repeatedly throwing this on entity graph ingestion for every major company (Apple, Microsoft, NVIDIA, Alphabet, Meta):

```
psycopg.errors.DatatypeMismatch: column "canonical" is of type boolean but expression is of type integer
LINE 1: ...ntities (kind, name, canonical, meta) VALUES ($1, $2, 1, $3)
```

This is the exact "entity graph persistence unverified" item flagged in the audit — now confirmed actively broken in production, not just unverified. Someone's inserting `1` instead of `true`/`True` for a boolean column. Quick fix, but it's been silently failing in prod logs for a while.

### Other live findings worth knowing

- `GET /health/full` reports `"quality_classifier": {"status": "not_trained"}` right now — contradicts the README/audit claim of a live F1=0.895 classifier. Either the trained model isn't deployed/loaded on this box, or it needs retraining in this environment.
- `DATABASE_URL` on the server points at a Postgres database named `enterprise_claude_skills` — **this Postgres container is shared with an unrelated project** (`claude-skill-agent`, also running on this same EC2 box via Docker, ports 5432/6379/3005). It's not a dedicated finance-platform database. This works today but is a real risk — a reset/migration run against that DB could affect the other project, and vice versa. I'd recommend giving this platform its own Postgres instance/database before doing anything schema-destructive.
- Disk: 79% used (22G/28G). Memory: 3.7G total, only ~350MB free at idle. This is a small instance — keep an eye on headroom before adding services.
- There's also a second, apparently unrelated EC2 host in my SSH config (`claude-skills`, `54.167.31.169`) — not part of this platform, mentioning it only so you don't confuse the two if you see it.

---

## 4. Architecture

```
Finance-Advanced-Research-Platform/        (pnpm + Turborepo + Lerna monorepo)
├── apps/
│   ├── api/            FastAPI backend (Python 3.11+)
│   │   └── app/
│   │       ├── api/          route handlers (~80+ files)
│   │       ├── connectors/   external API connectors (~43 files)
│   │       ├── services/     business logic (~90+ files; 37+ real, 4 full stubs, rest mixed)
│   │       ├── models/       SQLAlchemy ORM (64+ models, only 2-3 Alembic migrations!)
│   │       └── scripts/      CLI scanners/schedulers
│   ├── web/             Next.js 12 / React 17 frontend (dozens of pages, grows every sprint)
│   ├── admin/            React admin dashboard
│   └── worker/           Node.js background jobs (Bull + Redis)
├── packages/
│   ├── finance/          DCF, comps, technicals
│   ├── connectors/        US public-data connectors (17 federal + 51 state)
│   ├── shared-types/, config-typescript/, config-eslint/
├── docs/                 all project docs — see Section 6 for a map
├── reports/, apps/reports/   generated intelligence report samples
├── embedding-model-fine-tuning/   standalone embeddings training project (unrelated to day-to-day)
├── bloomberg-terminal-free/        unrelated reference project, ignore
└── ecosystem.config.js   PM2 process definitions (how staging actually runs)
```

**Tech stack:** FastAPI + SQLAlchemy 2.0 + PostgreSQL(prod)/SQLite(local) · Next.js 12 + React 17 + Tailwind v3 · Redis + Bull (jobs) · PM2 (process mgmt) · JWT+bcrypt auth · OpenAI GPT-4o (narratives) + Anthropic Claude (skills) · ReportLab/python-docx/openpyxl/python-pptx (exports).

---

## 5. Getting Set Up Locally

```bash
git clone https://github.com/1Touch-dev/Finance-Advanced-Research-Platform.git
cd Finance-Advanced-Research-Platform
git checkout 8th-july-sprint

# Backend
cd apps/api
pip install -e .
pip install -e ../../packages/finance
export DATABASE_URL="sqlite:///./local.db"
# copy the real .env from someone on the team (or ask me) — DO NOT use a blank .env.example and expect features to work
python -m uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload

# Frontend
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:3001 npm run dev   # serves on :3000 by default

# Bootstrap DB tables
curl -X POST http://localhost:3001/bootstrap
```

Docker alternative: `docker-compose.yml` at repo root spins up Postgres(5433)+Redis(6379)+api(8000)+web(3000) — note the port numbers here differ from the PM2/staging setup (3001/3003), don't mix them up.

**Env vars you'll need** (see `.env.example` for the full list, ~50 keys — don't paste real values into any doc or commit):
Core: `DATABASE_URL`, `JWT_SECRET`, `REDIS_URL`, `ENV`, `SEC_USER_AGENT`
Market data: `FINNHUB_API_KEY`, `FMP_API_KEY`, `ALPHA_VANTAGE_KEY`, `FRED_API_KEY`
AI: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
Public records: `CONGRESS_API_KEY`, `FEC_API_KEY`, `COURTLISTENER_API_TOKEN`, `GOVINFO_API_KEY`, `SAM_API_KEY`, `OPENCORPORATES_API_KEY`
Comms: `SENDGRID_API_KEY`, `TWILIO_*`
Monitoring: `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`
Blocked/pending (don't expect these to work): `PLAID_*` (not in .env.example even — needs a contract), VAPID keys (push notifications), Reddit API creds.

**Never commit `.env`.** It's already gitignored; double-check before any `git add -A`.

### Git workflow
- Work on `8th-july-sprint` (or cut a feature branch from it). Don't push to `main` directly.
- **Write honest commit messages.** This repo has a documented, embarrassing history of "feat: implement X — 70% to 85%" commits where X was a stub returning "not configured." See Section 2. If something's a stub, say so in the commit message. If you haven't verified data flows end-to-end, don't claim a percentage.

---

## 6. Where Things Are Documented (and which docs to trust)

The `docs/` folder has accumulated a lot of history. In rough order of how much to trust them:

| Doc | What it is | Trust level |
|---|---|---|
| **This file** | Current handover, Oct 2026 | Start here |
| `docs/INDEPENDENT_AUDIT_2026-08-26.md` | Last ground-truth audit (methodology + findings) | High — but re-run it, don't just read it |
| `MASTER_TASK_STATUS.md` | Same audit's findings restated + the audit-cycle explanation | High, same caveat |
| `docs/guides/Finance_Platform_Handoff.md` | Previous dev's (Abhishek Kulkarni, 13 Jul 2026) handoff | Useful for feature inventory/API reference, but 2+ months stale — page counts, live creds, and status claims have moved on |
| `docs/guides/production-deployment.md` | Deploy checklist, health endpoints, backup scripts | Accurate as a checklist, hasn't been exercised against the actual server config (see Section 3 DB issue) |
| `docs/architecture/context.md`, `PROJECT_DEEP_ANALYSIS.md` | Vision/architecture narrative | Good background, not a status source |
| `docs/AUDIT_2026-08-25.md`, `AUDIT_VERIFIED_2026-08-23.md`, `INDEPENDENT_AUDIT_2026-08-23.md`, `REVERIFICATION_2026-08-23.md` | Earlier audits in the same cycle | Historical interest only — shows the repeating pattern |
| `README.md` | Feature/stack overview | Mixed — some stats (e.g. "42 frontend pages", "F1=0.895 classifier live") don't match what I found live; treat specifics skeptically, structure/stack info is fine |
| `JAMES_ASKS.txt` | Raw client WhatsApp chat, feature requests | Primary source for "what does the client actually want," not for status |
| `docs/requirements/` | Feature strategy + client requirement docs | Good for scope/vision |
| `REALITY_DOC.md` | Earlier infra audit (predates the Aug 26 one) | Superseded by the Aug 26 audit |

---

## 7. Decisions That Need the Client (James), Not Engineering

These block real completion of 4 advertised features — flagged in the last audit and still open:

| Decision | Blocks | Note |
|---|---|---|
| Sign a Plaid contract (~$500/mo per last estimate) | Brokerage account sync | Until this exists, `brokerage_sync_service.py` should either stay a clearly-labeled stub or be removed from marketing/UI — right now it's wired into the frontend as if it works |
| GPU budget (~$200-500/mo RunPod per last estimate) | AI narrative model (fine-tuned generation) | Same — 100% stub today |
| VAPID keys (Firebase/OneSignal, free) | Push notifications | Quick to unblock if someone just sets this up |
| Reddit API approval (free, slow) | Social/whale sentiment | Apply early, approval lag is the bottleneck |
| Dedicated Postgres for this platform | Production data integrity | Current DB is shared with an unrelated project — see Section 3 |

---

## 8. Suggested First Two Weeks

1. **Re-verify reality before planning.** Run the audit checklist in `docs/INDEPENDENT_AUDIT_2026-08-26.md` against current `HEAD`. Get your own honest completion number before committing to any client-facing timeline.
2. **Fix the live entity-graph `canonical` boolean/integer bug** (Section 3) — quick win, currently spamming prod logs and silently dropping entity ingestion for every major company.
3. **Figure out why `finance-api` has restarted 339 times in 41 days.** Pull full PM2 logs, check for OOM kills (memory is tight on this box) vs. unhandled exceptions.
4. **Deploy local `HEAD` to staging** (it's 10 commits behind) — carefully, after diffing the stray `.bak`/`.backup2` files and `models/` directory already sitting on the server so you don't clobber something.
5. **Give this platform its own Postgres database**, separate from the shared `enterprise_claude_skills` one.
6. **Get Alembic migrations caught up** to the actual model set (64+ models, 2-3 migrations today) — this is the single most-flagged P0 across every past audit.
7. Then go to the client (James) with the business decisions in Section 7 before spending more engineering time on the 4 stub features.

---

## 9. Contacts

- **Client:** James Deller, Thunder Marketing — requirements/feedback via WhatsApp (see `JAMES_ASKS.txt` for history)
- **Previous developer (Jul 2026 handoff):** Abhishek Kulkarni — abhishekk@kyma.world
- **Me:** Anshuman Parmar — admin@kyma.world

---

*End of handover — 5 October 2026.*
