# Feature Architecture Plan
## Big Trade Detection + Alerts

| Field | Detail |
|-------|--------|
| **Platform** | Enterprise Intelligence & Investment Research Platform |
| **Feature ID** | F-03 |
| **Date** | July 20, 2026 |
| **Prepared by** | Developer |
| **Status** | Pending Lead Approval |
| **Est. Effort** | ~9 hours |
| **Branch** | `feature/big-trade-alerts` (branch from `8th-july-sprint`) |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State vs Target State](#2-current-state-vs-target-state)
3. [Impacted Files — Exact Change Map](#3-impacted-files--exact-change-map)
4. [Database Design](#4-database-design)
5. [Full Data Flow](#5-full-data-flow)
6. [API Endpoint Spec](#6-api-endpoint-spec)
7. [PM2 Process Definition](#7-pm2-process-definition)
8. [Environment Variables](#8-environment-variables)
9. [Email + SMS Template](#9-email--sms-template)
10. [Effort Estimate](#10-effort-estimate)
11. [Out of Scope](#11-out-of-scope)
12. [Risks & Mitigations](#12-risks--mitigations)

---

## 1. Executive Summary

This feature adds **real-time insider trade surveillance** to the platform.

It watches SEC Form 4 filings every 4 hours. When a corporate executive (CEO, CFO, Director, or 10%+ holder) buys or sells stock above a configurable dollar threshold (default **$500,000**), the system automatically:

1. Creates a typed alert record in the existing `alert_events` database table
2. Surfaces it in the existing `/tracking/alerts` inbox (already built and live)
3. Fires a formatted email via **SendGrid** (keys already in `.env`)
4. Fires an SMS via **Twilio** (keys already in `.env`)

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
     · Query params: threshold (float), dry_run (bool)
     · Calls big_trade_scanner.run_scan(db, threshold, dry_run)
     · Returns scan summary JSON

ecosystem.config.js
  └─ Add PM2 app entry: "big-trade-scanner"
     · cron_restart: every 4 hours
     · Calls run_big_trade_scan.py CLI script

.env  +  .env.example
  └─ Add 3 new variables (see Section 8)


NEW FILES — net new additions
─────────────────────────────

apps/api/app/services/big_trade_scanner.py
  └─ Core logic:
     fetch watchlist tickers → call Form 4 connector →
     filter by threshold → deduplicate → write AlertEvent →
     deliver via SendGrid + Twilio

apps/api/app/scripts/run_big_trade_scan.py
  └─ CLI entry point invoked by PM2 cron
     · Bootstraps DB session
     · Calls big_trade_scanner.run_scan()
     · Logs outcome


NO CHANGES NEEDED — already works as-is
────────────────────────────────────────
apps/web/pages/tracking/alerts.js        already renders alert_events from DB
apps/api/app/services/sendgrid_client.py already has send_email() — just call it
apps/api/app/services/twilio_client.py   already has send_sms()   — just call it
apps/api/app/models/monitor.py           AlertEvent, AlertRule, DeliveryChannel exist
apps/api/app/models/monitor.py           WatchlistItem.ticker column exists
```

---

## 4. Database Design

### No new tables required

The existing `AlertEvent` table (defined in `apps/api/app/models/monitor.py`) is used as-is.

```
AlertEvent  (already exists)
─────────────────────────────────────────────────────────
id           INTEGER  PK  AUTO
rule_id      INTEGER  FK → alert_rules.id
entity_id    INTEGER  nullable
ticker       VARCHAR  nullable       e.g. "AAPL"
kind         VARCHAR  NOT NULL       "insider_trade"   ← new value
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
  "source":         "SEC Form 4 via yfinance"
}
```

### One-time bootstrap row

Inserted automatically on first scan if not present:

```sql
INSERT INTO alert_rules (name, kind, params, enabled)
VALUES ('Big Trade Watch', 'insider_trade', '{"threshold": 500000}', true);
```

### Deduplication query (prevents re-alerting the same trade)

```sql
SELECT id FROM alert_events
WHERE kind = 'insider_trade'
  AND ticker = :ticker
  AND payload->>'date' = :trade_date
  AND payload->>'insider_name' = :insider_name
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
            · Read BIG_TRADE_THRESHOLD from env (default 500000)
            · Call big_trade_scanner.run_scan(db, threshold)
                            │
                            ▼
            apps/api/app/services/big_trade_scanner.py
                            │
            ┌───────────────┤
            │               │
            │   STEP 1      │  Load watchlisted tickers
            │               │  SELECT ticker FROM watchlist_items
            │               │  WHERE ticker IS NOT NULL
            │               │  → e.g. ["AAPL", "TSLA", "NVDA", ...]
            │               │
            │   STEP 2      │  For each ticker:
            │               │  gov_trading_connector.get_insider_trades(ticker)
            │               │  → hits yfinance → SEC Form 4 data
            │               │  → returns list of trade dicts
            │               │
            │   STEP 3      │  Filter: value_usd >= threshold
            │               │  → qualifying_trades = [t for t in trades
            │               │                         if t["value_usd"] >= threshold]
            │               │
            │   STEP 4      │  Deduplicate (7-day window)
            │               │  → skip if same trade already alerted this week
            │               │
            │   STEP 5      │  Write to DB
            │               │  INSERT INTO alert_events
            │               │  (rule_id, ticker, kind="insider_trade",
            │               │   payload=trade_dict, delivered=False)
            │               │
            │   STEP 6      │  Deliver each new alert
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
| `threshold` | `float` | `500000` | Minimum trade value (USD) to trigger an alert |
| `dry_run` | `bool` | `false` | If `true`: scan and return results but do NOT write to DB or send notifications |

**Response — 200 OK**

```json
{
  "scanned_tickers": 12,
  "trades_found": 47,
  "above_threshold": 3,
  "already_alerted": 1,
  "new_alerts_created": 2,
  "dry_run": false,
  "notifications_sent": {
    "email": 2,
    "sms": 2,
    "inapp": 2
  },
  "alerts": [
    {
      "ticker": "AAPL",
      "insider_name": "Timothy D. Cook",
      "title": "Chief Executive Officer",
      "transaction": "Sale",
      "shares": 511000,
      "value_usd": 85400000,
      "date": "2026-07-18"
    },
    {
      "ticker": "NVDA",
      "insider_name": "Jensen Huang",
      "title": "President and CEO",
      "transaction": "Sale",
      "shares": 120000,
      "value_usd": 14760000,
      "date": "2026-07-17"
    }
  ]
}
```

**Response — dry_run=true** (identical shape, `new_alerts_created: 0`, `notifications_sent` all zeros)

---

## 7. PM2 Process Definition

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

## 8. Environment Variables

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

## 9. Email + SMS Template

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

## 10. Effort Estimate

| # | Task | File | Est. Hours |
|---|------|------|-----------|
| 1 | `scan_big_trades()` function | `gov_trading_connector.py` | 2h |
| 2 | `big_trade_scanner.py` service (fetch → filter → dedup → write → deliver) | New file | 3h |
| 3 | `run_big_trade_scan.py` CLI entry point | New file | 0.5h |
| 4 | `POST /tracking/scan/insider-trades` endpoint | `tracking.py` | 1h |
| 5 | Email HTML template in `sendgrid_client.py` | `sendgrid_client.py` | 1h |
| 6 | PM2 cron entry | `ecosystem.config.js` | 0.25h |
| 7 | `.env` + `.env.example` additions | Config files | 0.25h |
| 8 | Manual QA: dry_run scan + live scan + inbox check | — | 1h |
| | **Total** | | **~9 hours** |

---

## 11. Out of Scope

| Item | Reason / Defer To |
|------|------------------|
| Per-user alert preferences (individual thresholds) | Requires full user settings page — Phase 2 |
| Slack / Teams delivery | `DeliveryChannel` model supports it but keys not configured — Phase 2 |
| Historical Form 4 backfill (pre-feature trades) | Scope: only new trades going forward |
| Congress PTR big trade alerts | Different data format — separate feature |
| Browser push notifications | Requires WebSocket / service worker — out of scope |
| Alert rules UI in frontend | Threshold managed via `.env` for now — Phase 2 |

---

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| yfinance Form 4 data incomplete (not all Form 4s appear in yfinance) | Medium | Some trades missed | Log missing tickers; label alerts "Source: yfinance (may be incomplete)" |
| Duplicate alerts if PM2 restarts mid-scan | Low | Noise | 7-day dedup window on (ticker + date + insider_name) |
| SendGrid sends one email per trade on large watchlist | Low | Email flood | Batch all trades from one scan run into a single digest email |
| Twilio SMS costs on international numbers | Low | Unexpected bill | SMS only fired if `ALERT_RECIPIENT_PHONE` is set; left blank by default |
| `alert_events` table missing on fresh SQLite dev DB | Low | Scan fails | Scanner checks table exists before INSERT; falls back gracefully |
| SEC EDGAR EFTS rate limit | Low | Slow scan | 1-second delay between ticker requests; 4-hour scan interval keeps volume low |

---

## 13. Testing Plan

| Test | Method | Expected Result |
|------|--------|----------------|
| Dry run scan | `POST /tracking/scan/insider-trades?dry_run=true` | Returns trades list, no DB writes, no notifications sent |
| Live scan with no watchlist | `POST /tracking/scan/insider-trades` (empty watchlist) | `scanned_tickers: 0`, no alerts |
| Live scan with AAPL watchlisted | Add AAPL to watchlist, run scan | Alerts created if any Form 4 trades exceed threshold |
| Deduplication | Run scan twice in a row | Second run: `already_alerted` count matches first run results |
| Email delivery | Set `ALERT_RECIPIENT_EMAIL`, trigger scan | Email received with correct trade details |
| SMS delivery | Set `ALERT_RECIPIENT_PHONE`, trigger scan | SMS received within 30 seconds |
| Inbox display | Open `/tracking/alerts` after scan | New alerts visible with `insider_trade` type, severity `warn` or `critical` |
| PM2 cron | Deploy to EC2, wait 4 hours | `pm2 logs big-trade-scanner` shows successful run |

---

## 14. Approval Checklist

- [ ] Architecture reviewed and approved by Lead
- [ ] Branch `feature/big-trade-alerts` created from `8th-july-sprint`
- [ ] `BIG_TRADE_THRESHOLD`, `ALERT_RECIPIENT_EMAIL`, `ALERT_RECIPIENT_PHONE` confirmed with James
- [ ] Implementation starts
- [ ] Dry-run QA passed
- [ ] Live scan QA passed (email + SMS received)
- [ ] Merged to `8th-july-sprint`
- [ ] Deployed to EC2, PM2 cron confirmed running

---

*Document prepared: July 20, 2026*
*Feature: Big Trade Detection + Alerts (F-03)*
*Codebase branch: `8th-july-sprint`*
*Implementation ready upon lead approval.*
