# API Integrations Guide

**Project:** Finance Advanced Research Platform  
**Last updated:** 28 July 2026  
**Purpose:** Single reference for every external API / service used by this platform — name, why we use it, and how it helps.

> **Security note:** This document lists **API names and env var keys only**. Never paste live secrets, tokens, or keys into markdown docs. Real values live only in `.env` (local) / server secrets (staging/production).

---

## Quick index

| Category | APIs |
|----------|------|
| Trade / market data | yfinance, SEC EDGAR, Finnhub, FMP, Alpha Vantage, FRED, CoinGecko |
| Big Trade Alerts (F-03 / F-04) | yfinance (Form 4 + 13F), SendGrid, Twilio |
| Government / public records | Congress.gov, FEC, Regulations.gov, GovInfo, SAM.gov, CourtListener, Sanctions, BEA, GLEIF |
| Company registry / OSINT | Cobalt, CA SOS, OpenCorporates, UK Companies House, Aleph |
| News | NewsAPI, Guardian, NYT, RSS feeds |
| Enrichment | Apollo, Apify |
| AI | OpenAI, Anthropic |
| Notifications | SendGrid, Twilio |
| Identity / payments / CRM | Didit, Stripe, Twenty, NFe.io / Focus NFe |
| Infra | OpenSearch, S3/MinIO, Redis, OIDC (Google) |

**Live interactive platform API docs (our own routes):**  
- Local: `http://localhost:3001/docs`  
- Staging: `http://184.72.123.188:3001/docs`

---

## 1. Trade data & Big Trade Alerts (most relevant to F-03 / F-04)

### 1.1 yfinance (Yahoo Finance Python library)

| | |
|---|---|
| **Name** | yfinance |
| **Type** | Python library wrapping Yahoo Finance / SEC-linked market data |
| **Env vars** | None (no API key required) |
| **Used in** | `gov_trading_connector.py`, `institutional_tracker.py`, `yfinance_connector.py`, `company_deep_connector.py`, `big_trade_scanner.py`, `investment_alert_service.py` |

**Why we use it**  
Primary free source for stock prices, fundamentals, insider transactions, and institutional holders without buying a paid market-data terminal.

**How it helps us**  
- Powers **F-03 Big Trade Detection** via SEC Form 4 insider trades  
- Powers **F-04 Investment Alerts** via institutional holders (13F-style data)  
- Feeds stock pages, company deep reports, valuation, technicals  

**Related platform endpoints**  
- `POST /tracking/scan/insider-trades`  
- `POST /tracking/scan/investments`  
- `GET /market/yf/*`, `GET /market/gov/insider-trades`, `GET /market/institutional/*`

---

### 1.2 SEC EDGAR / EFTS

| | |
|---|---|
| **Name** | U.S. Securities and Exchange Commission — EDGAR |
| **Base URLs** | `https://data.sec.gov`, `https://efts.sec.gov`, `https://www.sec.gov` |
| **Env vars** | `SEC_USER_AGENT` (required polite identity string) |
| **Used in** | Government trading, company filings, 13F lookups |

**Why we use it**  
Official U.S. source for Form 4 (insiders), 13F (institutions), 10-K/10-Q, and other filings.

**How it helps us**  
Evidence-first research: every big trade / filing claim can be traced to a public SEC record.

---

### 1.3 SendGrid

| | |
|---|---|
| **Name** | SendGrid (Twilio SendGrid) |
| **Endpoint** | `https://api.sendgrid.com/v3/mail/send` |
| **Env vars** | `SENDGRID_API_KEY`, `ALERT_SENDER_EMAIL`, `ALERT_RECIPIENT_EMAIL` |
| **Used in** | `sendgrid_client.py`, F-03 / F-04 alert services, digests |

**Why we use it**  
Reliable transactional email for alerts (not marketing blasts).

**How it helps us**  
Delivers Big Trade and Investment Threshold alert emails to admins/users when scans find qualifying trades.

---

### 1.4 Twilio

| | |
|---|---|
| **Name** | Twilio SMS |
| **Endpoint** | `https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json` |
| **Env vars** | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, `ALERT_RECIPIENT_PHONE` |
| **Used in** | `twilio_client.py`, F-03 / F-04 scanners |

**Why we use it**  
Instant SMS when large insider / institutional activity crosses a threshold.

**How it helps us**  
Users get mobile alerts without opening the dashboard.  
F-03 uses global `ALERT_RECIPIENT_PHONE`; F-04 uses each watchlist item’s `notify_phone`.

---

### 1.5 Alert threshold settings (config, not third-party APIs)

| Env var | Purpose |
|---------|---------|
| `BIG_TRADE_THRESHOLD` | Minimum USD value for F-03 insider-trade alerts |
| `ALERT_SENDER_EMAIL` | Verified SendGrid **From** address |
| `ALERT_RECIPIENT_EMAIL` | F-03 global email recipient |
| `ALERT_RECIPIENT_PHONE` | F-03 global SMS recipient (E.164) |
| `DIGEST_RECIPIENT_EMAIL` / `DIGEST_RECIPIENT_PHONE` | Daily digest recipients |

---

## 2. Financial market data APIs

### 2.1 Finnhub

| | |
|---|---|
| **Name** | Finnhub |
| **Env vars** | `FINNHUB_API_KEY` |
| **Why** | Stock quotes, company news, earnings calendars |
| **Helps** | Enriches financial news and market context beyond yfinance |

### 2.2 Financial Modeling Prep (FMP)

| | |
|---|---|
| **Name** | Financial Modeling Prep |
| **Env vars** | `FMP_API_KEY` |
| **Why** | Fundamentals, ratios, financial statements |
| **Helps** | Deeper company analysis and valuation inputs |

### 2.3 Alpha Vantage

| | |
|---|---|
| **Name** | Alpha Vantage |
| **Env vars** | `ALPHA_VANTAGE_KEY` |
| **Why** | Time series, indicators, some fundamentals |
| **Helps** | Backup / complementary market series when other sources are limited |

### 2.4 FRED (Federal Reserve Economic Data)

| | |
|---|---|
| **Name** | FRED (St. Louis Fed) |
| **Env vars** | `FRED_API_KEY` |
| **Why** | Macro indicators (rates, inflation, employment) |
| **Helps** | Economic context for investment research |

### 2.5 CoinGecko

| | |
|---|---|
| **Name** | CoinGecko |
| **Env vars** | `COINGECKO_API_KEY` (optional; better rate limits with key) |
| **Why** | Crypto prices, trending coins, market stats |
| **Helps** | Crypto dashboard, whale-related crypto pages |

---

## 3. Government & public-record APIs

| API name | Env var | Why we use it | How it helps |
|----------|---------|---------------|--------------|
| **Congress.gov** | `CONGRESS_API_KEY` | Members, sponsored legislation | Politician profiles + gov-trading context |
| **FEC** | `FEC_API_KEY` | Campaign finance | Political funding / influence research |
| **Regulations.gov** | `REGULATIONS_GOV_API_KEY` | Federal rulemaking dockets | Regulatory risk signals |
| **GovInfo** | `GOVINFO_API_KEY` | Official publications / docs | Government document evidence |
| **SAM.gov** | `SAM_GOV_API_KEY` | Federal awards / contractors | Procurement / contract intelligence |
| **CourtListener** | `COURTLISTENER_API_TOKEN` | Court opinions / dockets | Litigation risk for entities |
| **OpenSanctions / Sanctions** | `SANCTIONS_API_KEY` | Sanctions screening | Compliance / risk flags |
| **GLEIF** | `GLEIF_API_BASE_URL` | Legal Entity Identifiers | Entity resolution for companies |
| **BEA** | `BEA_API_USER_ID` | U.S. economic accounts | Macro / industry data for registry phase |
| **House Clerk PTR** | (no key; public ZIP) | Congressional financial disclosures | Congress trading transparency |

---

## 4. Company registry & OSINT

| API name | Env var | Why we use it | How it helps |
|----------|---------|---------------|--------------|
| **Cobalt Intelligence SOS** | `COBALT_API_KEY`, `COBALT_LIVE_DATA` | 50-state SOS company lookup | Registry coverage when direct SOS is hard |
| **California SOS** | `CA_SOS_API_KEY` | Official CA business search | Primary CA registry source |
| **OpenCorporates** | `OPENCORPORATES_API_KEY` | Global company registry | Private-company / international enrichment |
| **UK Companies House** | `UK_COMPANIES_HOUSE_KEY` | UK company filings | International OSINT |
| **Aleph / OCCRP** | `ALEPH_API_KEY` | Investigative datasets | Deep OSINT / entity network research |

---

## 5. News APIs

| API name | Env var | Why we use it | How it helps |
|----------|---------|---------------|--------------|
| **NewsAPI** | `NEWSAPI_KEY` | Broad web/news search | Entity news + expert analysis inputs |
| **The Guardian** | `GUARDIAN_API_KEY` | Quality long-form news | Sentiment / timeline enrichment |
| **New York Times** | `NYT_API_KEY` | NYT article search | Premium news coverage |
| **RSS feeds** | (none) | Free publisher feeds | High-volume news ingest on `/market/rss/*` |

---

## 6. Enrichment (people / LinkedIn / scraping)

### 6.1 Apollo.io

| | |
|---|---|
| **Name** | Apollo |
| **Env vars** | `APOLLO_API_KEY` |
| **Why** | B2B people/org enrichment, org charts |
| **Helps** | Intelligence reports: executives, domains, people search |

### 6.2 Apify

| | |
|---|---|
| **Name** | Apify |
| **Env vars** | `APIFY_API_TOKEN` |
| **Why** | Actor-based scraping (LinkedIn, PitchBook, Google News, etc.) |
| **Helps** | Relationship / enrichment workflows where no clean public API exists |

---

## 7. AI APIs

| API name | Env vars | Why we use it | How it helps |
|----------|----------|---------------|--------------|
| **OpenAI** | `OPENAI_API_KEY` | GPT narratives, RAG chat, multi-agent summaries | Intelligence dossiers, chat Q&A, report writing |
| **Anthropic Claude** | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Alternative / complementary LLM | Deep narrative and analysis when configured |

---

## 8. Identity, payments, CRM, fiscal

| API name | Env vars | Why we use it | How it helps |
|----------|----------|---------------|--------------|
| **Didit** | `DIDIT_*`, `KYC_PROVIDER` | KYC / identity verification | Onboarding compliance |
| **Stripe** | `STRIPE_*` | Payments / subscriptions | Billing (test mode keys in local `.env`) |
| **Twenty CRM** | `TWENTY_*`, `CRM_PROVIDER` | CRM workspace | Customer / pipeline sync |
| **NFe.io** | `NFEIO_*` | Brazilian fiscal invoices | Fiscal compliance features |
| **Focus NFe** | `FOCUSNFE_API_BASE_URL` | NF-e homologation | Fiscal testing environment |

---

## 9. Auth / infra services

| Name | Env vars | Why | How it helps |
|------|----------|-----|--------------|
| **Google OIDC** | `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_ISSUER`, `OIDC_REDIRECT_URI` | SSO login | Enterprise sign-in |
| **OpenSearch** | `OPENSEARCH_URL`, `OPENSEARCH_INDEX` | Full-text search | Document / entity search |
| **S3 / MinIO** | `S3_*`, `EVIDENCE_VAULT_DIR` | Object storage | Evidence vault files |
| **Redis** | `REDIS_URL` | Cache / workers | Background jobs & speed |
| **Database** | `DATABASE_URL` | App persistence | Watchlists, alerts, reports |
| **JWT** | `JWT_SECRET` | API auth tokens | Secure user sessions |

---

## 10. Our own platform APIs (alert-related)

These are **internal FastAPI routes** (not third-party), documented live at `/docs`:

| Endpoint | Feature | Purpose |
|----------|---------|---------|
| `POST /tracking/scan/insider-trades` | F-03 | Manual big-trade scan → email/SMS |
| `POST /tracking/scan/investments` | F-04 | Manual watchlist investment scan |
| `GET/POST/PATCH/DELETE /tracking/alert-rules` | F-03 | Manage insider-trade alert rules |
| `GET/PATCH /tracking/watchlist/{ticker}/threshold` | F-04 | Per-ticker threshold + notify email/phone |
| `GET/POST/DELETE /tracking/watchlist` | Tracking | Watchlist CRUD |
| `GET /tracking/alerts` | Alerts UI | In-app alert inbox |

Supporting market APIs already in the product:

| Endpoint group | Purpose |
|----------------|---------|
| `/market/yf/*` | Stock snapshot, history, fundamentals |
| `/market/gov/*` | Congress / insider trading views |
| `/market/institutional/*` | 13F / holders |
| `/intelligence/*` | Entity network intelligence reports |

---

## 11. How F-03 / F-04 use APIs together

```text
┌─────────────────────┐
│  yfinance / SEC     │  ← real trade & holdings data
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Big Trade Scanner  │  F-03  (Form 4 above threshold)
│  Investment Alerts  │  F-04  (watchlist threshold)
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
 SendGrid     Twilio
 (email)      (SMS)
```

**Data APIs answer:** *What big trades / investments happened?*  
**SendGrid + Twilio answer:** *Tell the user right now.*

---

## 12. Related docs in this repo

| File | Contents |
|------|----------|
| `Finance_Platform_Handoff.md` §6 | Large written list of platform endpoints |
| `PROJECT_DEEP_ANALYSIS.md` §8 | Another full endpoint reference |
| `docs/FEATURE_BIG_TRADE_ALERTS_ARCHITECTURE.md` | F-03 / F-04 architecture + new routes |
| `docs/Technical_Knowledge_Transfer.md` | How routers/connectors are structured |
| `.env.example` | Template of all env keys (empty values) |
| Live Swagger | `http://localhost:3001/docs` |

---

## 13. Status snapshot (as of last verification)

| Integration | Status |
|-------------|--------|
| yfinance Form 4 / 13F trade scans | Working |
| SendGrid email alerts | Working |
| Twilio SMS alerts | Working (trial; verified recipient required) |
| F-03 scan + notify | Working |
| F-04 scan + email | Working |
| F-04 SMS | Needs watchlist `notify_phone` = verified Twilio number |

---

*Maintainer tip: when adding a new third-party API, update this file + `.env.example` in the same PR, and never commit real keys.*
