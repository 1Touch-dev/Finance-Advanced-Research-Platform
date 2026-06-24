# 24th June 2026 — API Keys Integration & Full Verification

**Purpose:** Daily handoff and status document for 24 Jun 2026.  
**Staging:** Web `http://184.72.123.188:3003` · API `http://184.72.123.188:3001` · Docs `http://184.72.123.188:3001/docs`  
**Prior docs:** [23rd_June.md](./23rd_June.md) · [README.md](./README.md)

---

## Summary of Today's Work

| Area | Status |
|------|--------|
| All 8 financial/news/OSINT API keys registered | ✅ Complete |
| `.env` updated with all keys | ✅ Complete |
| FMP connector migrated to `/stable/` endpoints | ✅ Fixed |
| ICIJ endpoint deprecated — graceful empty return | ✅ Fixed |
| GDELT rate-limit guard added | ✅ Fixed |
| API Status Panel on entity profile updated (5→11 sources) | ✅ Complete |
| 19/19 API endpoint tests passing | ✅ Verified |
| `api_credentials_audit.csv` updated | ✅ Complete |
| `.env.example` updated with all API key sections | ✅ Complete |
| `README.md` workstream status updated | ✅ Complete |
| Full E2E browser test of staging | ✅ Complete |
| Committed and pushed to GitHub main | ✅ Complete |

---

## API Keys — Final Status

### Financial Data APIs

| API | Env Variable | Key | Status |
|-----|-------------|-----|--------|
| **Finnhub** | `FINNHUB_API_KEY` | `d8tpr69r01qhcnk5fgd0...` | ✅ Active — 60 req/min free |
| **FMP** | `FMP_API_KEY` | `O0kK4OYKtScxKoTpX7E6...` | ✅ Active — 250 req/day, stable endpoints |
| **Alpha Vantage** | `ALPHA_VANTAGE_KEY` | `C0JJYC3S2HM1BCIR` | ✅ Active — 25 req/day |
| **FRED** | `FRED_API_KEY` | `66e456b8683432e58fed...` | ✅ Active — unlimited |

### News APIs

| API | Env Variable | Key | Status |
|-----|-------------|-----|--------|
| **NewsAPI** | `NEWSAPI_KEY` | `2a7a8512e97a4873b947...` | ✅ Active — 100 req/day dev |
| **The Guardian** | `GUARDIAN_API_KEY` | `775515da-a760-4c76-b717...` | ✅ Active — 500 calls/day |
| **NYT Article Search** | `NYT_API_KEY` | `dM1PKHOrmkwvoHMvjGz7...` | ✅ Active — 500 req/day |

### OSINT / International

| API | Env Variable | Key | Status |
|-----|-------------|-----|--------|
| **UK Companies House** | `UK_COMPANIES_HOUSE_KEY` | `9c857e85-acc1-423c-8c25...` | ✅ Active — 600 req/5min |
| **ALEPH/OCCRP** | `ALEPH_API_KEY` | (empty) | ❌ Registration unavailable |
| **GDELT** | (none) | No key needed | ✅ Working — public API |
| **ICIJ Offshore Leaks** | (none) | No key needed | ⚠️ API decommissioned — returns graceful empty |
| **OpenSanctions** | `SANCTIONS_API_KEY` | (existing key) | ✅ Active |

### Pending / Waiting

| API | Env Variable | Status |
|-----|-------------|--------|
| **CA SOS BE API** | `CA_SOS_API_KEY` | ⏳ Subscriptions submitted — awaiting state approval |

---

## Connector Changes (24 Jun)

### `apps/api/app/connectors/financial_news_connector.py`

1. **FMP — migrated to `/stable/` endpoints** (v3 legacy deprecated Aug 31 2025 for new accounts):
   - `fmp_income_statement` → `https://financialmodelingprep.com/stable/income-statement`
   - `fmp_balance_sheet` → `https://financialmodelingprep.com/stable/balance-sheet-statement`
   - `fmp_cash_flow` → `https://financialmodelingprep.com/stable/cash-flow-statement`
   - `fmp_key_metrics` → `https://financialmodelingprep.com/stable/key-metrics-ttm`
   - Field mappings updated: `netIncome`, `grossProfit`, `operatingIncome`, `investmentsInPropertyPlantAndEquipment`, `commonDividendsPaid`

2. **GDELT** — added 1s polite delay + `isinstance(data, dict)` guard to handle rate-limit plaintext responses

3. **ICIJ Offshore Leaks** — API fully decommissioned; now returns graceful `[]` with a log message

### `apps/web/pages/entities/[id].js`

- `ApiStatusPanel` expanded from 5 → 11 sources:
  - Added: Alpha Vantage, FRED, NewsAPI, Guardian, NYT, UK Companies House

---

## 19/19 API Endpoint Tests — All Passing

```
✅ Finnhub quote         price=294.3  source=Finnhub
✅ Finnhub profile       name=Apple Inc  exchange=NASDAQ
✅ Finnhub metrics       pe_ratio=39.05  source=Finnhub
✅ Finnhub insiders      30 transactions
✅ FMP income            date=2025-09-27  revenue=416B
✅ FMP balance           total_assets=359B  total_debt=112B
✅ FMP cash-flow         operating_cf data present
✅ FMP key-metrics       ev_ebitda=27.26  roe=1.47
✅ Beneish M-Score       m_score=-0.953  risk=HIGH RISK
✅ Altman Z-Score        z_score=2.771  zone=Grey Zone
✅ FRED macro GDP        latest=31819 (Jan 2026)
✅ NewsAPI               articles returned
✅ The Guardian          articles returned
✅ NYT Article Search    articles returned
✅ UK Companies House    HSBC, Barclays returned
✅ UK Officers           35 Barclays officers returned
✅ ICIJ (graceful)       empty list — decommissioned
✅ ALEPH (no key)        empty list — key pending
✅ Aggregate news        10 articles from NewsAPI+Guardian+NYT+Finnhub
```

---

## Files Changed Today

| File | Change |
|------|--------|
| `.env` | Added NEWSAPI_KEY, GUARDIAN_API_KEY, NYT_API_KEY, UK_COMPANIES_HOUSE_KEY; previously added FRED_API_KEY, FMP_API_KEY |
| `.env.example` | Added Financial/News/OSINT API key section |
| `.gitignore` | `api_credentials_audit.csv` excluded |
| `README.md` | Workstream status updated — 8/9 keys obtained |
| `api_credentials_audit.csv` | Full credentials audit (gitignored) |
| `apps/api/app/connectors/financial_news_connector.py` | FMP `/stable/` migration, GDELT guard, ICIJ graceful stub |
| `apps/web/pages/entities/[id].js` | ApiStatusPanel expanded to 11 sources |

---

## Pending Items (carry-forward)

| Item | Status | Notes |
|------|--------|-------|
| ALEPH/OCCRP API key | ❌ | Registration unavailable; connector stub is live |
| CA SOS API key | ⏳ | State-approval pending at `calicodev.sos.ca.gov` |
| FMP margin fields | ⚠️ | `grossProfitRatio`, `operatingIncomeRatio`, `netIncomeRatio` not in stable endpoint; use manual calculation from revenue/profit fields if needed |
| GDELT reliability | ⚠️ | Rate-limited; returns 0 articles intermittently during rapid testing |
| ICIJ search | ⚠️ | API decommissioned — no replacement found; use web at `offshoreleaks.icij.org` |

---

## Staging Health Check

| Service | URL | Status |
|---------|-----|--------|
| Finance API | `http://184.72.123.188:3001` | ✅ Online |
| Finance Web | `http://184.72.123.188:3003` | ✅ Online |
| Finance Admin | `http://184.72.123.188:3002` | ✅ Online |
| OpenSearch | `http://127.0.0.1:9200` | ✅ Online |
| Postgres | `127.0.0.1:5433` | ✅ Online |
| Redis | `127.0.0.1:6379` | ✅ Online |
