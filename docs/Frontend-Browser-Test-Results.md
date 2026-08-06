# Frontend Browser Testing Results — Aug 6, 2026

## Test Target
**URL**: https://8th-july-sprint.d11ri08de55gmb.amplifyapp.com  
**API Backend**: https://financeintell.duckdns.org (EC2 via DuckDNS + nginx reverse proxy)

---

## ✅ WORKING (No Issues)

| Page | Status | Notes |
|------|--------|-------|
| Dashboard (`/`) | ✅ | All cards, stats render |
| Stock Analysis (`/stock`) | ✅ | AAPL loads ~15s, all data correct. **No 404 console errors** |
| Deep Company (`/company`) | ✅ | AAPL: full SEC filings, earnings, analyst consensus |
| Expert Analysis (`/expert-analysis`) | ✅ | Page loads, form works |
| Institutional (`/institutional`) | ✅ | Tabs, institution dropdown, data loads |
| Valuation (`/valuation`) | ✅ | Page loads |
| Saved Reports (`/saved`) | ✅ | Lists 25+ reports with PDF/Word/Excel/MD export buttons |
| Intelligence Generator (`/intelligence`) | ✅ | Form works, "Generating..." state shows |
| Global Search (`/search`) | ✅ | Page loads |
| Timeline (`/timeline`) | ✅ | Page loads |
| **🚀 Deep Report (Network/Group)** | ✅ | **WORKS** — PayPal Mafia completed in ~10 min, PDF downloads |
| PDF-Premium export | ✅ | Returns actual PDF (200) |
| Word/Excel exports | ✅ | Both return 200 |

## ❌ ISSUES FOUND (3 items)

### 1. Dynamic Route 404 (Amplify Routing)
**Affected**: `/intelligence/25`, `/intelligence/[any-id]`, `/entities/[id]`  
**Symptom**: Blank white page  
**Root Cause**: Amplify static hosting can't resolve dynamic routes  
**Fix**: Add Amplify Console Rewrite Rules:
```
/intelligence/<*>  →  /intelligence/[id].html  (200 Rewrite)
/entities/<*>      →  /entities/[id].html      (200 Rewrite)
```

### 2. Single-Entity "Generate Enhanced Report" Timeout (60s nginx limit)
**Affected**: "Generate Enhanced Report" and "Generate Intelligence Report" buttons  
**Symptom**: "Failed to fetch" after exactly 60 seconds  
**Root Cause**: nginx `proxy_read_timeout` = 60s (default). These endpoints are synchronous and take 30-120s.  
**Fix Option A**: Increase nginx timeout to 300s  
**Fix Option B** (better): Convert to async job pattern like the Deep Report already uses

### 3. PDF-Beautiful & Markdown Export 500 (code fix not deployed yet)
**Affected**: `★ PDF` and `MD` buttons in Saved Reports  
**Symptom**: HTTP 500 — "NoneType.__format__"  
**Fix**: Deploy latest code to EC2 (fix already in local repo)

---

## 🚀 Deep Report (Network/Group) — FULL TEST RESULT

| Step | Status | Details |
|------|--------|---------|
| Click "Generate Deep Report" | ✅ | Button → "⏳ Generating..." |
| API call | ✅ | POST `/generate-network-report?network=paypal_mafia&expanded=true` → 200 |
| Job polling | ✅ | Polls `/report-job/{id}` every 5s |
| Completion | ✅ | Completed in ~10 minutes |
| UI update | ✅ | Shows "✅ Report Ready" + Download PDF / Markdown / JSON links |
| PDF download | ✅ | `PayPal_Mafia_COMPLETE_20260806_162855.pdf` — HTTP 200, application/pdf |

**Conclusion**: Deep Report generation works correctly. It's slow (~10 min for 18 people) but that's expected for the full pipeline (expand_v2 → supplement_a → supplement_b → merge_final).

---

## Actions Required

| Priority | Action | Time | Who |
|----------|--------|------|-----|
| P1 | Increase nginx `proxy_read_timeout` to 300s for `/intelligence/generate*` | 2 min | EC2 SSH |
| P1 | Deploy latest code to EC2 (fixes pdf-beautiful + markdown 500) | 5 min | `git pull` + PM2 restart |
| P2 | Add Amplify rewrite rules for dynamic routes | 5 min | Amplify Console |
| P3 | Convert single-entity generate to async job pattern | 2-3 hrs | Code change |
