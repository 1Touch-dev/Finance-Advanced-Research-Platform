# Feature Architecture Plans
## Trade Alert Features — F-03 & F-04

> This document covers **two related but separate features** that must be built on **separate branches**.

| Feature | ID | Branch | What It Does |
|---------|-----|--------|-------------|
| Big Trade Detection + Alerts | **F-03** | `feature/big-trade-alerts` | Platform watches SEC Form 4 for large insider SELL trades above a global threshold. Admin-controlled. |
| Watchlist Investment Threshold Alert | **F-04** | `feature/watchlist-investment-alerts` | User adds a company (e.g. Apple) + sets their own `$5,000` threshold. When anyone invests that amount in that company, the user gets email/SMS. User-controlled. |

---

# F-03 — Big Trade Detection + Alerts

| Field | Detail |
|-------|--------|
| **Platform** | Enterprise Intelligence & Investment Research Platform |
| **Feature ID** | F-03 |
| **Date** | July 20, 2026 |
| **Prepared by** | Developer |
| **Status** | Pending Lead Approval |
| **Est. Effort** | ~11 hours |
| **Branch** | `feature/big-trade-alerts` (branch from `8th-july-sprint`) |

---

## F-03 Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State vs Target State](#2-current-state-vs-target-state)
3. [Impacted Files — Exact Change Map](#3-impacted-files--exact-change-map)
4. [Database Design](#4-database-design)
5. [Full Data Flow](#5-full-data-flow)
6. [API Endpoint Spec](#6-api-endpoint-spec)
7. [Alert Rule Management (User-Configurable)](#7-alert-rule-management-user-configurable)
8. [PM2 Process Definition](#8-pm2-process-definition)
9. [Environment Variables](#9-environment-variables)
10. [Email + SMS Template](#10-email--sms-template)
11. [Effort Estimate](#11-effort-estimate)
12. [Out of Scope](#12-out-of-scope)
13. [Risks & Mitigations](#13-risks--mitigations)
14. [Testing Plan](#14-testing-plan)
15. [Approval Checklist](#15-approval-checklist)

---

## 1. Executive Summary

This feature adds **real-time insider trade surveillance** to the platform.

It watches SEC Form 4 filings every 4 hours. When a corporate executive (CEO, CFO, Director, or 10%+ holder) buys or sells stock above a configurable dollar threshold (default **$500,000**), the system automatically:

1. Creates a typed alert record in the existing `alert_events` database table
2. Surfaces it in the existing `/tracking/alerts` inbox (already built and live)
3. Fires a formatted email via **SendGrid** (keys already in `.env`)
4. Fires an SMS via **Twilio** (keys already in `.env`)

**Users can configure both the dollar threshold AND which companies to watch — per alert rule:**

- Each `AlertRule` record (kind = `insider_trade`) stores its own `threshold` inside the `params` JSON column. Different rules can have different thresholds (e.g. $250k for high-priority tickers, $1M for general noise filter).
- Each `AlertRule` is optionally scoped to a `watchlist_id`. The scanner only checks tickers that belong to that watchlist. If no watchlist is linked, the rule applies to all watchlisted tickers globally.
- Users manage rules via a dedicated REST API (see Section 7). No direct DB or `.env` edits required.

> **No new infrastructure required.** All delivery, database, and UI components already exist. This feature is purely additive — a new scanner service + background cron job that plugs into what is already live.

---

## 2. Current State vs Target State

| Aspect | Current State | After This Feature |
|--------|--------------|-------------------|
| Form 4 data | Fetched on-demand via `get_insider_trades()` when user visits `/gov-trading` | Also auto-scanned every 4 hours in the background by PM2 |
| Alert triggers | Only manual digest run (`POST /tracking/digest/run`) | Auto-triggered whenever a qualifying trade exceeds threshold |
| Alert inbox `/tracking/alerts` | Shows only digest log entries as fallback | Shows real `insider_trade` typed alerts with full trade detail |
| SendGrid | Configured in `.env`, used only by daily digest | Also fires for real-time big trade notifications |
| Twilio | Configured in `.env`, used only by daily digest | Also fires SMS for real-time big trade notifications |
| `AlertRule` DB model | Exists in `monitor.py` — `kind` field supports arbitrary strings | One new seeded rule: `kind = "insider_trade"` |
| `AlertEvent` DB model | Exists in `monitor.py` — `payload` is JSON, `kind` is a string | New events written with `kind = "insider_trade"` |

---

## 3. Impacted Files — Exact Change Map

```
MODIFY — existing files (surgical additions only, nothing removed)
──────────────────────────────────────────────────────────────────

apps/api/app/connectors/gov_trading_connector.py
  └─ Add function: scan_big_trades(watchlist_tickers, threshold)
     · Loops over each ticker in the watchlist
     · Calls existing get_insider_trades(ticker) per ticker
     · Filters results where value_usd >= threshold
     · Returns list of qualifying trade dicts

apps/api/app/api/tracking.py
  └─ Add endpoint: POST /tracking/scan/insider-trades
     · Query params: rule_id (int, optional), threshold (float), dry_run (bool)
     · If rule_id provided → load threshold + ticker scope from that AlertRule
     · If no rule_id → fall back to query-param threshold, global watchlist
     · Calls big_trade_scanner.run_scan(db, rule, dry_run)
     · Returns scan summary JSON

  └─ Add CRUD endpoints for AlertRule management (see Section 7):
     · GET    /tracking/alert-rules
     · POST   /tracking/alert-rules
     · GET    /tracking/alert-rules/{rule_id}
     · PATCH  /tracking/alert-rules/{rule_id}
     · DELETE /tracking/alert-rules/{rule_id}

ecosystem.config.js
  └─ Add PM2 app entry: "big-trade-scanner"
     · cron_restart: every 4 hours
     · Calls run_big_trade_scan.py CLI script

.env  +  .env.example
  └─ Add 3 new variables (see Section 9)


NEW FILES — net new additions
─────────────────────────────

apps/api/app/services/big_trade_scanner.py
  └─ Core logic:
     load all enabled insider_trade AlertRules →
     for each rule: resolve ticker scope (watchlist_id or global) →
     call Form 4 connector per ticker →
     filter by rule.params["threshold"] →
     deduplicate → write AlertEvent →
     deliver via SendGrid + Twilio

apps/api/app/scripts/run_big_trade_scan.py
  └─ CLI entry point invoked by PM2 cron
     · Bootstraps DB session
     · Calls big_trade_scanner.run_scan_all_rules()
     · Logs outcome per rule


NO CHANGES NEEDED — already works as-is
────────────────────────────────────────
apps/web/pages/tracking/alerts.js        already renders alert_events from DB
apps/api/app/services/sendgrid_client.py already has send_email() — just call it
apps/api/app/services/twilio_client.py   already has send_sms()   — just call it
apps/api/app/models/monitor.py           AlertEvent, AlertRule (params JSON +
                                         watchlist_id), DeliveryChannel all exist
apps/api/app/models/monitor.py           WatchlistItem.ticker column exists
```

---

## 4. Database Design

### No new tables required

All models already exist in `apps/api/app/models/monitor.py`. The feature uses them as-is with no migrations needed.

---

### AlertRule — per-rule threshold + company scope

```
AlertRule  (already exists — used as-is)
─────────────────────────────────────────────────────────────────────
id           INTEGER  PK  AUTO
name         VARCHAR  NOT NULL       e.g. "Big Trade Watch — FAANG"
kind         VARCHAR  NOT NULL       "insider_trade"   ← new value used here
params       JSON     nullable       { "threshold": 500000 }
                                     ↑ user sets this per rule
watchlist_id INTEGER  FK → watchlists.id  nullable
                                     ↑ if set → only scan tickers in this watchlist
                                       if NULL → scan ALL watchlisted tickers
portfolio_id INTEGER  FK → portfolios.id  nullable  (not used for this feature)
enabled      BOOLEAN  default True   user can enable/disable without deleting
```

**How threshold resolution works:**
1. `rule.params["threshold"]` is the authoritative value per rule.
2. If `params` is null or threshold key missing → fall back to `BIG_TRADE_THRESHOLD` env var (default 500,000).

**How company (ticker) scope works:**
1. If `rule.watchlist_id` is set → load tickers from `watchlist_items WHERE watchlist_id = rule.watchlist_id`.
2. If `rule.watchlist_id` is NULL → load tickers from all `watchlist_items` (global scan).
3. A user can create a dedicated watchlist (e.g. "FAANG Watch") with only 5 tickers and link it to a low-threshold rule ($100k), while a global rule at $1M covers everything else.

---

### AlertEvent  (already exists)

```
AlertEvent
─────────────────────────────────────────────────────────
id           INTEGER  PK  AUTO
rule_id      INTEGER  FK → alert_rules.id    ← which rule fired this event
entity_id    INTEGER  nullable
ticker       VARCHAR  nullable       e.g. "AAPL"
kind         VARCHAR  NOT NULL       "insider_trade"
payload      JSON     nullable       full trade detail (schema below)
delivered    BOOLEAN  default False  flipped to True after send
created_at   TIMESTAMP server_default now()
```

### Payload JSON schema

```json
{
  "insider_name":   "Timothy D. Cook",
  "title":          "Chief Executive Officer",
  "transaction":    "Sale",
  "shares":         511000,
  "value_usd":      85400000,
  "date":           "2026-07-18",
  "ticker":         "AAPL",
  "threshold_used": 500000,
  "rule_id":        1,
  "rule_name":      "Big Trade Watch — FAANG",
  "source":         "SEC Form 4 via yfinance"
}
```

### Seed rows (auto-inserted on first scan if not present)

```sql
-- Default global rule — covers all watchlisted tickers at $500k
INSERT INTO alert_rules (name, kind, params, watchlist_id, enabled)
VALUES ('Big Trade Watch', 'insider_trade', '{"threshold": 500000}', NULL, true);
```

Users can add more rules via the API (Section 7) — e.g. a stricter rule for a specific company watchlist.

### Deduplication query (prevents re-alerting the same trade)

```sql
SELECT id FROM alert_events
WHERE kind = 'insider_trade'
  AND ticker = :ticker
  AND payload->>'date' = :trade_date
  AND payload->>'insider_name' = :insider_name
  AND rule_id = :rule_id
  AND created_at > NOW() - INTERVAL '7 days'
LIMIT 1;
```

If this returns a row → skip. Do not re-alert.

---

## 5. Full Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│              PM2 Process: "big-trade-scanner"                    │
│         cron_restart: "0 */4 * * *"  (every 4 hours)            │
│         Runs at: 00:00  04:00  08:00  12:00  16:00  20:00 UTC   │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
            apps/api/app/scripts/run_big_trade_scan.py
            · Bootstrap SQLAlchemy DB session from DATABASE_URL
            · Call big_trade_scanner.run_scan_all_rules(db)
                            │
                            ▼
            apps/api/app/services/big_trade_scanner.py
                            │
            ┌───────────────┤
            │               │
            │  STEP 0       │  Load all enabled insider_trade rules
            │               │  SELECT * FROM alert_rules
            │               │  WHERE kind = 'insider_trade' AND enabled = true
            │               │  → e.g. [Rule#1 (global, $500k),
            │               │          Rule#2 (FAANG watchlist, $100k)]
            │               │
            │               │  ──── FOR EACH RULE ────────────────────────────
            │               │
            │  STEP 1       │  Resolve ticker scope for this rule
            │               │  IF rule.watchlist_id IS NOT NULL:
            │               │    SELECT ticker FROM watchlist_items
            │               │    WHERE watchlist_id = rule.watchlist_id
            │               │  ELSE:
            │               │    SELECT ticker FROM watchlist_items
            │               │    (all tickers, global scope)
            │               │  → e.g. ["AAPL", "TSLA", "NVDA", ...]
            │               │
            │  STEP 2       │  Resolve threshold for this rule
            │               │  threshold = rule.params.get("threshold")
            │               │          or BIG_TRADE_THRESHOLD env var (500000)
            │               │
            │  STEP 3       │  For each ticker in scope:
            │               │  gov_trading_connector.get_insider_trades(ticker)
            │               │  → hits yfinance → SEC Form 4 data
            │               │  → returns list of trade dicts
            │               │
            │  STEP 4       │  Filter: value_usd >= threshold
            │               │  → qualifying_trades = [t for t in trades
            │               │                         if t["value_usd"] >= threshold]
            │               │
            │  STEP 5       │  Deduplicate (7-day window, scoped to this rule_id)
            │               │  → skip if same trade already alerted this week
            │               │    for this specific rule
            │               │
            │  STEP 6       │  Write to DB
            │               │  INSERT INTO alert_events
            │               │  (rule_id=rule.id, ticker, kind="insider_trade",
            │               │   payload={...trade_dict, rule_id, rule_name,
            │               │            threshold_used}, delivered=False)
            │               │
            │  STEP 7       │  Deliver each new alert
            └───────────────┤
                            │
              ┌─────────────┼──────────────────────────┐
              │             │                          │
              ▼             ▼                          ▼
         IN-APP           EMAIL                      SMS
    Already in DB     sendgrid_client           twilio_client
    /tracking/alerts  .send_email(              .send_sms(
    auto-shows it       to=ALERT_RECIPIENT_EMAIL  to=ALERT_RECIPIENT_PHONE
    on next page        subject="🚨 Big Trade…"   body="Big Trade: AAPL…"
    load (SWR 30s)      body_html=template      )
                      )
```

---

## 6. API Endpoint Spec

### `POST /tracking/scan/insider-trades`

Manually triggers a scan. Also called by the PM2 cron script.

**Query Parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `rule_id` | `int` | `null` | If provided → use that rule's threshold + watchlist scope. If omitted → run ALL enabled insider_trade rules. |
| `threshold` | `float` | `500000` | Override threshold (only used when `rule_id` is NOT provided and you want a one-off scan) |
| `dry_run` | `bool` | `false` | If `true`: scan and return results but do NOT write to DB or send notifications |

**Response — 200 OK**

```json
{
  "rules_run": 2,
  "results": [
    {
      "rule_id": 1,
      "rule_name": "Big Trade Watch",
      "threshold_used": 500000,
      "ticker_scope": "global",
      "scanned_tickers": 12,
      "trades_found": 47,
      "above_threshold": 3,
      "already_alerted": 1,
      "new_alerts_created": 2,
      "notifications_sent": { "email": 2, "sms": 2, "inapp": 2 },
      "alerts": [
        {
          "ticker": "AAPL",
          "insider_name": "Timothy D. Cook",
          "title": "Chief Executive Officer",
          "transaction": "Sale",
          "shares": 511000,
          "value_usd": 85400000,
          "date": "2026-07-18"
        }
      ]
    },
    {
      "rule_id": 2,
      "rule_name": "FAANG Watch — Strict",
      "threshold_used": 100000,
      "ticker_scope": "watchlist:3",
      "scanned_tickers": 5,
      "trades_found": 8,
      "above_threshold": 1,
      "already_alerted": 0,
      "new_alerts_created": 1,
      "notifications_sent": { "email": 1, "sms": 1, "inapp": 1 },
      "alerts": [ { "ticker": "NVDA", "insider_name": "Jensen Huang", "value_usd": 14760000, "date": "2026-07-17" } ]
    }
  ],
  "dry_run": false
}
```

---

## 7. Alert Rule Management (User-Configurable)

This is the core of the user-facing configuration. Users create/edit/delete `AlertRule` rows via API. No DB access or `.env` editing required.

All endpoints live in `apps/api/app/api/tracking.py`.

---

### `GET /tracking/alert-rules`

List all `insider_trade` alert rules.

**Response**
```json
[
  {
    "id": 1,
    "name": "Big Trade Watch",
    "kind": "insider_trade",
    "threshold": 500000,
    "watchlist_id": null,
    "ticker_scope": "global (all watchlisted tickers)",
    "enabled": true
  },
  {
    "id": 2,
    "name": "FAANG Watch — Strict",
    "kind": "insider_trade",
    "threshold": 100000,
    "watchlist_id": 3,
    "ticker_scope": "watchlist:3 — FAANG (5 tickers)",
    "enabled": true
  }
]
```

---

### `POST /tracking/alert-rules`

Create a new alert rule with a custom threshold and optional company scope.

**Request Body**
```json
{
  "name": "FAANG Watch — Strict",
  "threshold": 100000,
  "watchlist_id": 3
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `string` | Yes | Friendly rule name shown in alerts inbox |
| `threshold` | `float` | Yes | Minimum USD value to fire an alert for this rule |
| `watchlist_id` | `int` | No | If provided → only scan tickers in that watchlist. Omit for global scan. |
| `enabled` | `bool` | No | Default `true`. Set `false` to pause the rule without deleting it. |

**Response — 201 Created**
```json
{
  "id": 2,
  "name": "FAANG Watch — Strict",
  "kind": "insider_trade",
  "threshold": 100000,
  "watchlist_id": 3,
  "enabled": true
}
```

**Validation rules (enforced in endpoint):**
- `threshold` must be > 0
- If `watchlist_id` is provided → verify the watchlist exists in DB; return 404 if not
- `name` must be non-empty string ≤ 255 chars

---

### `GET /tracking/alert-rules/{rule_id}`

Fetch a single rule.

**Response — 200 OK** — same shape as single item from list above.
**Response — 404** if rule not found.

---

### `PATCH /tracking/alert-rules/{rule_id}`

Update threshold, name, watchlist scope, or enabled state. All fields optional.

**Request Body (partial update)**
```json
{
  "threshold": 250000,
  "watchlist_id": 5
}
```

**Use cases:**
- Change threshold: `{"threshold": 1000000}` → raise bar to $1M
- Swap company scope: `{"watchlist_id": 7}` → now watches a different list of tickers
- Remove company scope (go global): `{"watchlist_id": null}` → scan all watchlisted tickers
- Pause rule: `{"enabled": false}`
- Resume rule: `{"enabled": true}`

**Response — 200 OK** — updated rule object.

---

### `DELETE /tracking/alert-rules/{rule_id}`

Permanently delete a rule. Existing `alert_events` that were fired by this rule are kept (historical record).

**Response — 204 No Content**

---

### Example: setting up two rules for different companies

```
User creates Watchlist #3 "FAANG" with tickers: AAPL, AMZN, GOOGL, META, NVDA
User creates Watchlist #4 "Energy" with tickers: XOM, CVX, COP

POST /tracking/alert-rules
{ "name": "FAANG Watch — Strict",  "threshold": 100000, "watchlist_id": 3 }
→ Fires on any FAANG insider trade ≥ $100k

POST /tracking/alert-rules
{ "name": "Energy Watch",          "threshold": 2000000, "watchlist_id": 4 }
→ Fires on any Energy insider trade ≥ $2M (higher bar, less noise)

POST /tracking/alert-rules
{ "name": "Global High-Value",     "threshold": 10000000 }
→ No watchlist_id → scans ALL watchlisted tickers for trades ≥ $10M
```

---

## 8. PM2 Process Definition

Addition to `ecosystem.config.js`:

```js
{
  name: 'big-trade-scanner',
  cwd: './apps/api',
  script: '../../venv/bin/python3',
  args: '-m app.scripts.run_big_trade_scan',
  interpreter: 'none',
  env_file: '../../.env',
  autorestart: true,
  watch: false,
  cron_restart: '0 */4 * * *',   // runs at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
  log_file: './logs/big-trade-scanner.log',
  error_file: './logs/big-trade-scanner-error.log',
}
```

**To deploy on EC2:**

```bash
pm2 reload ecosystem.config.js   # picks up new entry without restarting other processes
pm2 list                          # verify big-trade-scanner appears
pm2 logs big-trade-scanner        # watch first run
```

---

## 9. Environment Variables

Additions to `.env` and `.env.example`:

```bash
# ── Big Trade Alert Settings ───────────────────────────────────────────────────
# Minimum USD transaction value that triggers an alert
BIG_TRADE_THRESHOLD=500000

# Who receives the alert notifications
ALERT_RECIPIENT_EMAIL=                  # e.g. james@thundermarketing.com
ALERT_RECIPIENT_PHONE=                  # e.g. +14155551234  (E.164 format, Twilio)
```

> **Note:** `SENDGRID_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER` are already set in `.env` from prior work. No changes needed for those.

---

## 10. Email + SMS Template

### Email (SendGrid HTML)

```
Subject:  🚨 Big Trade Alert — AAPL: Cook sold $85,400,000

┌──────────────────────────────────────────────────────────┐
│  🚨  Big Insider Trade Detected                          │
├──────────────────────────────────────────────────────────┤
│  Ticker       AAPL  (Apple Inc.)                         │
│  Insider      Timothy D. Cook                            │
│  Title        Chief Executive Officer                    │
│  Transaction  Sale                                       │
│  Shares       511,000                                    │
│  Value        $85,400,000                                │
│  Trade Date   2026-07-18                                 │
│  Source       SEC Form 4                                 │
│  Threshold    Exceeded $500,000 threshold                │
├──────────────────────────────────────────────────────────┤
│  [ View in Platform → localhost:3000/gov-trading ]       │
└──────────────────────────────────────────────────────────┘

Multiple trades in one scan are batched into a single email.
```

### SMS (Twilio — max 160 chars)

```
🚨 Big Trade: AAPL — Cook (CEO) sold $85.4M on 2026-07-18.
Source: SEC Form 4. View: localhost:3000/gov-trading
```

---

## 11. Effort Estimate

| # | Task | File | Est. Hours |
|---|------|------|-----------|
| 1 | `scan_big_trades()` function | `gov_trading_connector.py` | 2h |
| 2 | `big_trade_scanner.py` service (multi-rule loop, per-rule threshold + scope, dedup, write, deliver) | New file | 3.5h |
| 3 | `run_big_trade_scan.py` CLI entry point | New file | 0.5h |
| 4 | `POST /tracking/scan/insider-trades` endpoint (multi-rule aware) | `tracking.py` | 1h |
| 5 | CRUD endpoints for AlertRule management (GET/POST/PATCH/DELETE) | `tracking.py` | 1.5h |
| 6 | Email HTML template in `sendgrid_client.py` | `sendgrid_client.py` | 1h |
| 7 | PM2 cron entry | `ecosystem.config.js` | 0.25h |
| 8 | `.env` + `.env.example` additions | Config files | 0.25h |
| 9 | Manual QA: dry_run scan + live scan + inbox check + rule CRUD | — | 1h |
| | **Total** | | **~11 hours** |

---

## 12. Out of Scope

| Item | Reason / Defer To |
|------|------------------|
| ~~Per-user alert preferences (individual thresholds)~~ | **Now in scope** — implemented via AlertRule CRUD API (Section 7) |
| Slack / Teams delivery | `DeliveryChannel` model supports it but keys not configured — Phase 2 |
| Historical Form 4 backfill (pre-feature trades) | Scope: only new trades going forward |
| Congress PTR big trade alerts | Different data format — separate feature |
| Browser push notifications | Requires WebSocket / service worker — out of scope |
| Alert rules UI in frontend (settings page) | Phase 2 — threshold/scope managed via API for now |

---

## 13. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| yfinance Form 4 data incomplete (not all Form 4s appear in yfinance) | Medium | Some trades missed | Log missing tickers; label alerts "Source: yfinance (may be incomplete)" |
| Duplicate alerts if PM2 restarts mid-scan | Low | Noise | 7-day dedup window on (ticker + date + insider_name) |
| SendGrid sends one email per trade on large watchlist | Low | Email flood | Batch all trades from one scan run into a single digest email |
| Twilio SMS costs on international numbers | Low | Unexpected bill | SMS only fired if `ALERT_RECIPIENT_PHONE` is set; left blank by default |
| `alert_events` table missing on fresh SQLite dev DB | Low | Scan fails | Scanner checks table exists before INSERT; falls back gracefully |
| SEC EDGAR EFTS rate limit | Low | Slow scan | 1-second delay between ticker requests; 4-hour scan interval keeps volume low |

---

## 14. Testing Plan

| Test | Method | Expected Result |
|------|--------|----------------|
| Dry run scan | `POST /tracking/scan/insider-trades?dry_run=true` | Returns trades list, no DB writes, no notifications sent |
| Live scan with no watchlist | `POST /tracking/scan/insider-trades` (empty watchlist) | `scanned_tickers: 0`, no alerts |
| Live scan with AAPL watchlisted | Add AAPL to watchlist, run scan | Alerts created if any Form 4 trades exceed threshold |
| Deduplication | Run scan twice in a row | Second run: `already_alerted` count matches first run results |
| Per-rule threshold | Create rule with $100k threshold, run scan | Fires on trades ≥ $100k that the $500k rule would miss |
| Per-company scope | Create rule with watchlist_id set to 3-ticker list | Only those 3 tickers are scanned for that rule |
| Rule CRUD: create | `POST /tracking/alert-rules` with threshold + watchlist_id | 201, new rule in DB |
| Rule CRUD: update threshold | `PATCH /tracking/alert-rules/2` `{"threshold": 250000}` | 200, next scan uses new threshold |
| Rule CRUD: swap scope | `PATCH /tracking/alert-rules/2` `{"watchlist_id": 7}` | 200, next scan uses new watchlist |
| Rule CRUD: disable | `PATCH /tracking/alert-rules/2` `{"enabled": false}` | 200, PM2 cron skips disabled rule |
| Email delivery | Set `ALERT_RECIPIENT_EMAIL`, trigger scan | Email received with correct trade details + rule name |
| SMS delivery | Set `ALERT_RECIPIENT_PHONE`, trigger scan | SMS received within 30 seconds |
| Inbox display | Open `/tracking/alerts` after scan | New alerts visible with `insider_trade` type, severity `warn` or `critical` |
| PM2 cron | Deploy to EC2, wait 4 hours | `pm2 logs big-trade-scanner` shows successful run |

---

## 15. Approval Checklist

- [ ] Architecture reviewed and approved by Lead
- [ ] Branch `feature/big-trade-alerts` created from `8th-july-sprint`
- [ ] `BIG_TRADE_THRESHOLD`, `ALERT_RECIPIENT_EMAIL`, `ALERT_RECIPIENT_PHONE` confirmed with James
- [ ] AlertRule CRUD endpoints reviewed and approved
- [ ] Per-rule threshold + watchlist scoping logic confirmed
- [ ] Implementation starts
- [ ] Dry-run QA passed
- [ ] Rule CRUD QA passed (create, patch threshold, patch watchlist_id, disable)
- [ ] Live scan QA passed (email + SMS received)
- [ ] Merged to `8th-july-sprint`
- [ ] Deployed to EC2, PM2 cron confirmed running

---

*Document prepared: July 20, 2026*
*Feature: Big Trade Detection + Alerts (F-03)*
*Codebase branch: `8th-july-sprint`*
*Implementation ready upon lead approval.*

---
---

# F-04 — Watchlist Investment Threshold Alert
## *"Notify me when someone invests $X in companies I track"*

| Field | Detail |
|-------|--------|
| **Platform** | Enterprise Intelligence & Investment Research Platform |
| **Feature ID** | F-04 |
| **Date** | July 21, 2026 |
| **Prepared by** | Developer |
| **Status** | Pending Lead Approval |
| **Est. Effort** | ~11.75 hours |
| **Branch** | `feature/watchlist-investment-alerts` (branch from `8th-july-sprint`) |
| **Depends On** | Independent of F-03 — separate branch, can run in parallel |

---

## How F-04 Differs from F-03

| Aspect | F-03 Big Trade | F-04 This Feature |
|--------|---------------|-------------------|
| Who sets threshold | Admin via `.env` global variable | **Each user sets their own per company** |
| Threshold value | $500,000 (platform-wide default) | **User-defined** (e.g. $5,000) |
| Who gets notified | One global email/phone from `.env` | **The specific user who saved the watchlist item** |
| Transaction type watched | Insider SELL (executive offloading) | **Any BUY** — insider buy OR institutional new position |
| User interface | None (admin config only) | **Inline form on `/tracking` page** per company row |
| Company scope | All watchlisted tickers | **Per entity the user chose to watch** |

---

## F04 Table of Contents

1. [Executive Summary](#f04-1-executive-summary)
2. [User Journey](#f04-2-user-journey)
3. [Impacted Files](#f04-3-impacted-files)
4. [Database Changes](#f04-4-database-changes)
5. [Full Data Flow](#f04-5-full-data-flow)
6. [New API Endpoints](#f04-6-new-api-endpoints)
7. [UI Change on /tracking Page](#f04-7-ui-change)
8. [PM2 Process Definition](#f04-8-pm2)
9. [Email + SMS Templates](#f04-9-templates)
10. [Effort Estimate](#f04-10-effort)
11. [Out of Scope](#f04-11-out-of-scope)
12. [Risks & Mitigations](#f04-12-risks)
13. [Testing Plan](#f04-13-testing)
14. [Approval Checklist](#f04-14-approval)

---

## F04-1. Executive Summary

This feature lets each user track specific companies they care about and set a **personal dollar threshold**. When any investor — an insider buyer (SEC Form 4) or an institutional fund (13F filing) — puts money into that company above the user's threshold, the system sends that user a personal email and/or SMS.

**Example:**
> User adds "Apple (AAPL)" to their watchlist.
> They set threshold: **$5,000**.
> They enter their email: `james@thundermarketing.com`.
> Warren Buffett files a Form 4 showing a **$12,000,000 BUY** of AAPL.
> User receives:
> - Email: *"📈 New Investment in Apple — Berkshire bought $12M"*
> - SMS: *"Investment Alert: AAPL — Berkshire bought $12M on 2026-07-18"*
> - In-app: alert appears in `/tracking/alerts` inbox

> **No new infrastructure.** SendGrid, Twilio, the alert inbox, the watchlist DB — all already live. This feature adds per-item threshold + notification config, a scanner service, and a small UI update.

---

## F04-2. User Journey

```
Step 1 — User opens /tracking
         Sees their watchlist: [Apple] [Tesla] [Palantir]

Step 2 — User clicks "Set Alert" on the Apple row
         A form appears inline:
           Threshold:  [ $5,000      ]
           Email:      [ james@... ]
           Phone:      [ +1-415-... ]  (optional)
           Alert on:   [✓ BUY]  [  SELL]
         User clicks [Save Alert]

Step 3 — Platform stores threshold + contact on that WatchlistItem row

Step 4 — PM2 background process runs every 4 hours:
           Sees Apple has threshold $5,000 set by user
           Fetches Form 4 BUY transactions for AAPL
           Fetches 13F new institutional positions for AAPL
           Finds: Berkshire Hathaway new position $12,000,000
           $12M > $5,000 ✅ → alert fires

Step 5 — User receives email + SMS
         Alert appears in /tracking/alerts inbox
```

---

## F04-3. Impacted Files

```
MODIFY — existing files
───────────────────────
apps/api/app/models/monitor.py
  └─ WatchlistItem: add 5 new columns
       investment_threshold  FLOAT    nullable  (user's threshold, e.g. 5000.0)
       notify_email          VARCHAR  nullable  (user's personal email for this item)
       notify_phone          VARCHAR  nullable  (user's phone in E.164 format)
       alert_on_buy          BOOLEAN  default True
       alert_on_sell         BOOLEAN  default False
  └─ New table: investment_alert_seen (deduplication log)

apps/api/app/api/tracking.py
  └─ Add: PATCH /tracking/watchlist/{ticker}/threshold
  └─ Add: GET   /tracking/watchlist/{ticker}/threshold
  └─ Add: POST  /tracking/scan/investments

apps/api/app/connectors/institutional_tracker.py
  └─ Add: get_new_institutional_positions(ticker)
       Fetches latest 13F and compares to prior quarter
       Returns only NEW positions added this quarter

ecosystem.config.js
  └─ Add: "investment-alert-scanner" PM2 entry (cron every 4h, offset 30m from F-03)

.env + .env.example
  └─ No new variables required
     (user's email/phone stored in DB per watchlist item)


NEW FILES
─────────
apps/api/app/services/investment_alert_service.py
  └─ Core scan logic (see Data Flow section below)

apps/api/app/scripts/run_investment_alert_scan.py
  └─ PM2 CLI entry point


NO CHANGES NEEDED
─────────────────
apps/api/app/services/sendgrid_client.py   already works — just call it
apps/api/app/services/twilio_client.py     already works — just call it
apps/web/pages/tracking/alerts.js          already renders alert_events — no changes
apps/api/app/connectors/gov_trading_connector.py
   get_insider_trades(ticker) already exists — investment_alert_service calls it
```

---

## F04-4. Database Changes

### Modify `WatchlistItem` — add 5 columns

```
WatchlistItem  (existing table — ADD columns, nothing removed)
───────────────────────────────────────────────────────────────────
id                   INTEGER  PK         (already exists)
watchlist_id         INTEGER  FK         (already exists)
entity_id            INTEGER  nullable   (already exists)
ticker               VARCHAR  nullable   (already exists)
notes                TEXT     nullable   (already exists)
── NEW COLUMNS ───────────────────────────────────────────────────
investment_threshold FLOAT    default NULL
                              User's minimum USD value to trigger alert
                              NULL = no alert configured for this item

notify_email         VARCHAR  default NULL
                              User's personal email for alerts on this item

notify_phone         VARCHAR  default NULL
                              E.164 format: "+14155551234"
                              NULL = no SMS for this item

alert_on_buy         BOOLEAN  default True
                              Fire alert when someone BUYs this stock

alert_on_sell        BOOLEAN  default False
                              Fire alert when someone SELLs this stock
```

### New table `investment_alert_seen` — deduplication log

```
investment_alert_seen  (NEW TABLE)
────────────────────────────────────────────────────────────────
id                   INTEGER   PK AUTO
watchlist_item_id    INTEGER   FK → watchlist_items.id
investor_name        VARCHAR   e.g. "Berkshire Hathaway"
ticker               VARCHAR   e.g. "AAPL"
transaction          VARCHAR   "Buy" or "Sale"
value_usd            FLOAT
trade_date           VARCHAR   e.g. "2026-07-18"
alerted_at           TIMESTAMP server_default now()
```

**Deduplication query:**
```sql
SELECT id FROM investment_alert_seen
WHERE watchlist_item_id = :item_id
  AND ticker = :ticker
  AND investor_name = :investor
  AND trade_date = :date
  AND alerted_at > NOW() - INTERVAL '7 days'
LIMIT 1;
```

If this returns a row → skip. Never re-alert the same trade to the same user.

### `AlertEvent` payload (written to existing table)

```json
{
  "investor_name":      "Berkshire Hathaway",
  "investor_type":      "institutional",
  "transaction":        "Buy",
  "value_usd":          12000000,
  "date":               "2026-07-18",
  "ticker":             "AAPL",
  "company_name":       "Apple Inc.",
  "user_threshold":     5000,
  "source":             "SEC 13F Filing",
  "watchlist_item_id":  7
}
```

`kind` column value: `"investment_alert"` — distinct from F-03's `"insider_trade"`.

---

## F04-5. Full Data Flow

```
User saves: Apple (AAPL)
            investment_threshold = $5,000
            notify_email = "james@thunder.com"
            notify_phone = "+14155551234"
            alert_on_buy = True
                    │
                    │  stored in watchlist_items row
                    │
PM2 cron (every 4h, offset 30m)
run_investment_alert_scan.py
  → Bootstrap DB session
  → Call investment_alert_service.run_scan(db)
                    │
                    ▼
investment_alert_service.py
                    │
   STEP 1  Load all watchlist items where investment_threshold IS NOT NULL
           SELECT * FROM watchlist_items WHERE investment_threshold IS NOT NULL
                    │
   STEP 2  For each item — fetch from 2 sources:

           Source A — Insider BUY (Form 4 via yfinance)
             gov_trading_connector.get_insider_trades(ticker)
             filter: transaction="Buy" AND value_usd >= threshold AND alert_on_buy=True

           Source B — Institutional new position (13F)
             institutional_tracker.get_new_institutional_positions(ticker)
             filter: new_position_value >= threshold AND alert_on_buy=True
                    │
   STEP 3  Merge results from both sources
                    │
   STEP 4  Deduplicate per user per investment
           Query investment_alert_seen table (7-day window)
           Skip if already alerted
                    │
   STEP 5  For each new qualifying investment:
           → INSERT into investment_alert_seen
           → INSERT into alert_events (kind="investment_alert", payload={...})
                    │
   STEP 6  Deliver (personalized — each watchlist item has its own contact)
           │
           ├── EMAIL  → item.notify_email
           │           "📈 New Investment in Apple — Berkshire bought $12M"
           │
           ├── SMS    → item.notify_phone
           │           "Investment Alert: AAPL — Berkshire bought $12M on 2026-07-18"
           │
           └── IN-APP → alert_events row auto-shows in /tracking/alerts (SWR 30s)
```

---

## F04-6. New API Endpoints

### `PATCH /tracking/watchlist/{ticker}/threshold`

Save or update threshold + notification settings for a watchlist item.

**Request body:**
```json
{
  "threshold":    5000,
  "notify_email": "james@thundermarketing.com",
  "notify_phone": "+14155551234",
  "alert_on_buy":  true,
  "alert_on_sell": false
}
```

**Validation:**
- `threshold` must be ≥ 1000 (enforce minimum to prevent alert spam)
- `notify_phone` if provided must match E.164 regex: `^\+[1-9]\d{7,14}$`
- At least one of `notify_email` or `notify_phone` must be set

**Response — 200 OK:**
```json
{
  "ok": true,
  "ticker": "AAPL",
  "watchlist_item_id": 7,
  "threshold": 5000,
  "notify_email": "james@thundermarketing.com",
  "notify_phone": "+14155551234",
  "alert_on_buy": true,
  "alert_on_sell": false
}
```

---

### `GET /tracking/watchlist/{ticker}/threshold`

Fetch current threshold settings for a watchlist item (used by UI to pre-fill form).

**Response — 200 OK:** same shape as PATCH response above.
**Response — 404:** ticker not in any watchlist or no threshold set.

---

### `POST /tracking/scan/investments`

Manually trigger the investment alert scan (also called by PM2 cron script).

**Query params:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `ticker` | `string` | `null` | Scan only this ticker. Omit to scan all items with threshold set. |
| `dry_run` | `bool` | `false` | Return results without writing to DB or sending notifications. |

**Response — 200 OK:**
```json
{
  "scanned_items": 3,
  "investments_found": 12,
  "above_threshold": 2,
  "already_alerted": 0,
  "new_alerts_created": 2,
  "dry_run": false,
  "notifications_sent": { "email": 2, "sms": 2, "inapp": 2 },
  "alerts": [
    {
      "ticker": "AAPL",
      "investor_name": "Berkshire Hathaway",
      "investor_type": "institutional",
      "transaction": "Buy",
      "value_usd": 12000000,
      "date": "2026-07-18",
      "user_threshold": 5000,
      "notified_to": "james@thundermarketing.com"
    }
  ]
}
```

---

## F04-7. UI Change on `/tracking` Page

File: `apps/web/pages/tracking/index.js`

**Current:**
```
[ Apple Inc. (AAPL) ]                              [ Remove ]
```

**After F-04:**
```
[ Apple Inc. (AAPL) ]               [ Set Alert ▾ ]   [ Remove ]
  ┌──────────────────────────────────────────────────────────┐
  │  📬  Investment Alert for Apple                          │
  │  Alert me when someone invests ≥  [ $5,000      ]       │
  │  Email:  [ james@thundermarketing.com           ]        │
  │  Phone:  [ +1-415-555-1234          ] (optional)        │
  │  Alert on:  [✓ BUY]   [  SELL]                          │
  │                             [ Save Alert ]               │
  └──────────────────────────────────────────────────────────┘
```

- Clicking [Set Alert ▾] toggles the inline form
- On load: `GET /tracking/watchlist/{ticker}/threshold` pre-fills saved values
- On save: `PATCH /tracking/watchlist/{ticker}/threshold`
- If threshold is set, the row badge shows: `📬 Alert: ≥$5,000`

---

## F04-8. PM2 Process Definition

Addition to `ecosystem.config.js`:

```js
{
  name: 'investment-alert-scanner',
  cwd: './apps/api',
  script: '../../venv/bin/python3',
  args: '-m app.scripts.run_investment_alert_scan',
  interpreter: 'none',
  env_file: '../../.env',
  autorestart: true,
  watch: false,
  cron_restart: '30 */4 * * *',
  // ↑ offset 30 min from big-trade-scanner (which runs at :00)
  // runs at: 00:30, 04:30, 08:30, 12:30, 16:30, 20:30 UTC
  log_file: './logs/investment-alert-scanner.log',
  error_file: './logs/investment-alert-scanner-error.log',
}
```

---

## F04-9. Email + SMS Templates

### Email (SendGrid HTML)

```
Subject:  📈 Investment Alert — Apple: Berkshire bought $12,000,000

┌──────────────────────────────────────────────────────────┐
│  📈  New Investment Detected in Your Watchlist           │
├──────────────────────────────────────────────────────────┤
│  Company          Apple Inc. (AAPL)                      │
│  Your Threshold   $5,000                                 │
│  Investor         Berkshire Hathaway                     │
│  Type             Institutional (SEC 13F)                │
│  Transaction      BUY                                    │
│  Amount           $12,000,000                            │
│  Date             2026-07-18                             │
├──────────────────────────────────────────────────────────┤
│  [ View Apple on Platform → ]   [ Manage My Alerts → ]   │
└──────────────────────────────────────────────────────────┘
```

### SMS (Twilio — max 160 chars)

```
📈 Investment Alert: AAPL — Berkshire (institutional) bought
$12M on 2026-07-18. Your threshold: $5,000.
```

---

## F04-10. Effort Estimate

| # | Task | File | Est. Hours |
|---|------|------|-----------|
| 1 | DB: 5 new columns on `watchlist_items` + `investment_alert_seen` table | `monitor.py` | 1h |
| 2 | `get_new_institutional_positions(ticker)` | `institutional_tracker.py` | 1.5h |
| 3 | `investment_alert_service.py` core scan logic | New file | 3h |
| 4 | `run_investment_alert_scan.py` CLI entry | New file | 0.5h |
| 5 | `PATCH /tracking/watchlist/{ticker}/threshold` | `tracking.py` | 1h |
| 6 | `GET /tracking/watchlist/{ticker}/threshold` | `tracking.py` | 0.5h |
| 7 | `POST /tracking/scan/investments` | `tracking.py` | 0.5h |
| 8 | UI inline form on `/tracking` page | `tracking/index.js` | 2h |
| 9 | Email HTML template (investment variant) | `sendgrid_client.py` | 0.5h |
| 10 | PM2 cron entry | `ecosystem.config.js` | 0.25h |
| 11 | QA (threshold save + dry run + live scan + email + SMS + inbox) | — | 1h |
| | **Total** | | **~11.75 hours** |

---

## F04-11. Out of Scope

| Item | Reason |
|------|--------|
| Multiple alert tiers per company (e.g. $5K warning + $1M critical) | Phase 2 |
| Crypto wallet buy tracking | Different data source — separate feature |
| Real-time alerts under 1 hour | SEC Form 4 / 13F not real-time |
| Per-user authentication isolation | Requires full JWT user model — Phase 2 |
| Alert frequency cap (e.g. max 1 per day per company) | Phase 2 |
| Telegram / Slack delivery | Keys not configured yet — Phase 2 |

---

## F04-12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| 13F filings are quarterly — low sensitivity for institutional positions | High | Low | Label alert source clearly: "SEC 13F (quarterly update)" vs "SEC Form 4 (near real-time)" |
| yfinance may miss some Form 4 BUY filings | Medium | Some trades missed | Log per-ticker, add disclaimer in alert footer |
| User sets very low threshold ($1) → alert flood | Medium | Spam | Enforce minimum $1,000 in API. Show UI warning below $5,000. |
| Dedup table grows large | Low | Slow queries | Add index on `(watchlist_item_id, trade_date)`. Monthly purge of rows older than 90 days. |
| Invalid phone numbers cause Twilio errors | Low | SMS fails silently | Validate E.164 in `PATCH` endpoint — return 400 if invalid. |
| Overlap with F-03 alert for same trade | Low | Minor duplication in inbox | Different `kind` values in `alert_events` — user sees them as distinct alert types. |

---

## F04-13. Testing Plan

| Test | Method | Expected Result |
|------|--------|----------------|
| Save threshold | `PATCH /tracking/watchlist/AAPL/threshold` `{"threshold": 5000, "notify_email": "x@x.com"}` | 200, DB updated |
| Fetch threshold | `GET /tracking/watchlist/AAPL/threshold` | Returns saved values |
| Below minimum threshold | `PATCH` with `{"threshold": 0}` | 400 validation error |
| Invalid phone | `PATCH` with `{"notify_phone": "12345"}` | 400 — not E.164 |
| Missing contact | `PATCH` with no email and no phone | 400 — at least one required |
| Dry run scan | `POST /tracking/scan/investments?dry_run=true` | Returns found investments, 0 DB writes, 0 notifications |
| No threshold set | Watchlist item with NULL threshold | Skipped in scanner |
| Qualifying investment found | AAPL with $5,000 threshold | Alert created, email sent |
| Deduplication | Run scan twice | Second run: `already_alerted` matches first-run count |
| SMS delivery | Set `notify_phone`, trigger scan | SMS arrives within 30s |
| Inbox display | Open `/tracking/alerts` after scan | Alerts visible with `investment_alert` type |
| UI form save | Fill and save inline form on `/tracking` | Values persist on page reload |
| UI form pre-fill | Reload page after saving | Form pre-populated with saved values |
| PM2 cron | Deploy, wait 4.5h | `pm2 logs investment-alert-scanner` shows successful run |

---

## F04-14. Approval Checklist

- [ ] F-04 architecture reviewed and approved by Lead
- [ ] Branch `feature/watchlist-investment-alerts` created from `8th-july-sprint`
- [ ] Minimum threshold value confirmed with James (suggested: $1,000)
- [ ] Confirmed: alert on BUY only by default; SELL opt-in
- [ ] DB migration approach confirmed (SQLite local / Postgres prod)
- [ ] Implementation starts
- [ ] DB migration + bootstrap tested locally
- [ ] `PATCH /tracking/watchlist/{ticker}/threshold` QA passed
- [ ] Dry-run scan QA passed
- [ ] Live scan QA passed
- [ ] Email received by test recipient
- [ ] SMS received by test recipient
- [ ] UI form save/load tested
- [ ] Merged to `8th-july-sprint`
- [ ] Deployed to EC2, PM2 cron confirmed running

---

*Document updated: July 21, 2026*
*F-03: Big Trade Detection + Alerts — branch `feature/big-trade-alerts`*
*F-04: Watchlist Investment Threshold Alert — branch `feature/watchlist-investment-alerts`*
*Base branch: `8th-july-sprint`*
*Both features pending lead approval.*
