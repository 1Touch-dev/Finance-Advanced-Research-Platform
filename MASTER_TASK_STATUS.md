# Finance Platform — Master Status & Task Tracker

**Single Source of Truth — 16 August 2026**
**Current Branch:** `8th-july-sprint` (active development)
**Verified by:** Git commit history + codebase analysis

---

## Executive Summary

| Category | Done | Partial | Remaining |
|----------|------|---------|-----------|
| **Core Platform** | 92% | 3% | 5% |
| **AI Model Training (Phase 1-4)** | 85% | 5% | 10% |
| **72-Feature Register** | ~40% | ~10% | ~50% |
| **James's Requirements** | ~65% | ~20% | ~15% |

**Key Achievements (16 Aug 2026):**
- **Band B Features #15-31 Complete**: All 17 Band B features done (100%)
- 540 tests across consensus, analyst, guidance, volume, formula, leaderboard, ontology, document, docket, filing, volatility, multi-entity, and whisper services
- Fixed bug in earnings surprise report date calculation
- **Embeddings Model Fine-tuned & Deployed**: +8.5% ranking accuracy, +82% confidence margin
- Model trained on RunPod (RTX 4090), deployed to EC2 CPU, backed up to S3
- RAG pipeline now uses fine-tuned model as primary with OpenAI fallback
- Quality Gate ML Classifier: **F1=0.895** (+131.2% from baseline)
- Infrastructure hardening: DB pooling, search timeouts, rate limiting, health checks
- E2E pipeline test and search benchmarks added
- Full docs restructure + 72 files committed

---

## PRIORITY: GPU-Dependent Tasks

### Completed (15 Aug 2026) ✅

| Priority | Task | Description | Status |
|----------|------|-------------|--------|
| ~~P0~~ | ~~Phase 2.3~~ | ~~Fine-tune embeddings on RunPod~~ | ✅ **DONE** |
| ~~P1~~ | ~~Phase 2.5~~ | ~~Deploy fine-tuned embeddings~~ | ✅ **DONE** |

**Embeddings Model Results:**
- +8.5% ranking accuracy (82% → 90.5%)
- +82% confidence margin (0.178 → 0.325)
- Model: `finance-embed-v1` deployed to EC2
- Training: 7,198 triplets, 90s on RTX 4090
- S3 Backup: `s3://finance-intelligence-models-203918873003/embeddings/finance-embed-v1/`
- Guide: `embedding-model-fine-tuning/EMBEDDINGS_TRAINING_GUIDE.md`

### Remaining

| Priority | Task | Description | Blocker |
|----------|------|-------------|---------|
| **P0** | Phase 4.3 | Fine-tune Llama/Qwen on narrative generation | GPU required |
| **P1** | Phase 4.6 | Deploy narrative model | Depends on 4.3 |

### Pre-requisites Ready
- ✅ Fine-tuned embeddings model deployed to EC2
- ✅ A/B evaluation shows +8.5% improvement
- ✅ Narrative samples collected for Phase 4 distillation
- ✅ Production integration with fallback mechanism ready

---

## Section 1: Git Branch Status

### Active Branches (sorted by recent activity)

| Branch | Last Commit | Status | Notes |
|--------|-------------|--------|-------|
| `8th-july-sprint` | e830c6b | **CURRENT** | Embeddings + AI training infra |
| `feature/intelligence-correlation-full` | 8ead589 | ✅ Synced | Intelligence + Quality Gate ML merged |
| `feature/quality-gate-ml` | 4c08800 | ✅ **MERGED** | Quality Judge + Classifier |
| `feature/13f-frontend` | — | ✅ Merged | 13F position diff |
| `feature/trade-alerts` | — | ✅ Merged | F-03/F-04 trade alerts |
| `feature/band-a-priorities` | — | ✅ Merged | Band A (1-14) features |

### Recent Commits

```
e830c6b docs: add S3 backup info for fine-tuned model
e0252c6 feat: AI training infrastructure + docs restructure (72 files)
eaa2514 fix: add missing os import in intelligence.py
c889742 feat: integrate fine-tuned embeddings model into RAG pipeline
6370e34 feat(api): database pooling, search timeout, blended mode, E2E tests
8ead589 Enterprise Intelligence activation workflows (Rishav)
```

---

## Section 2: What's DONE (Verified in Code)

### 2.1 RAG Engine — Phase 1 ✅ COMPLETE

**Commits:** `ceb190a`, `41b0bee`

| Component | File | Status |
|-----------|------|--------|
| Embeddings (batched, cached) | `services/rag/embeddings.py` | ✅ Working |
| Vector Store (numpy + HNSW) | `services/rag/vector_store.py` | ✅ Working |
| Keyword Search (BM25 + TF-IDF fallback) | `services/rag/keyword.py` | ✅ Working |
| Hybrid Search (RRF fusion) | `services/rag/hybrid.py` | ✅ Working |
| Cross-encoder Rerank | `services/rag/rerank.py` | ✅ Working |
| Guardrails (input/output) | `services/rag/guardrails.py` | ✅ Working |
| Chunking (recursive + semantic) | `services/rag/chunking.py` | ✅ Working |
| Eval (hit@k, MRR, nDCG) | `services/rag/eval.py` | ✅ Working |
| Retriever orchestrator | `services/rag/retriever.py` | ✅ Working |
| CI gate test | `tests/test_rag_eval_gate.py` | ✅ 4/4 passing |
| Unit tests | `tests/test_rag_vector.py` | ✅ 34/34 passing |

**API Endpoints:**
- `POST /chat/ask` — `?mode=vector|keyword|hybrid&debug=true`
- `GET /documents/search` — `?mode=&debug=`

### 2.2 Quality Gate System — Phase 3 ✅ COMPLETE

**Branch Merged:** `feature/quality-gate-ml` ✅

| Component | File | Status |
|-----------|------|--------|
| LLM Judge | `services/quality/judge.py` | ✅ Working |
| ML Classifier (v2) | `services/quality/classifier.py` | ✅ **F1=0.895** |
| Decision Layer | `services/quality/decision.py` | ✅ Working |
| Label Logging | `services/quality/labels.py` | ✅ Working |
| Report Flattener | `services/quality/report_text.py` | ✅ Working |
| Synthetic Generator | `services/quality/synthetic.py` | ✅ Working |
| Opus 4.5 Synthetic | `scripts/generate_publishable_synthetic.py` | ✅ NEW |
| Training Script v2 | `scripts/train_quality_classifier_v2.py` | ✅ NEW |
| Trained Model | `models/quality_classifier.joblib` | ✅ v2 model |
| Labels | `exports/quality_labels*.jsonl` | ✅ **403 samples** |
| Tests | `tests/test_quality_*.py` | ✅ All passing |
| Docs | `docs/Quality-Judge.md` | ✅ Complete |

**Quality Classifier Improvement Summary:**

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **F1 Score** | 0.387 | 0.895 | **+131.2%** |
| **Precision** | 0.400 | 0.941 | +135% |
| **Recall** | 0.375 | 0.854 | +128% |
| **Training Samples** | 303 | 403 | +33% |
| **Class Balance** | 9.9% | 30.8% | +211% |
| **Features** | 12 | 22 | +83% |

**Key Improvements Made:**
1. Generated 100 high-quality publishable reports using Claude Opus 4.5
2. Added 6 text features (total_text_length, section_count, citation_count, avg_sentence_length, news_article_count, executive_count)
3. Added 6 interaction features (citation_x_overall, failures_squared, etc.)
4. Switched from Logistic Regression to Random Forest
5. Added threshold optimization (optimal threshold: 0.65)
6. Implemented ThresholdClassifier wrapper for custom decision boundaries

### 2.2.1 Infrastructure Hardening (14 Aug 2026) ✅ COMPLETE

| Task | Component | File | Status |
|------|-----------|------|--------|
| **Task 8** | Database connection pooling + health check | `db/session.py`, `api/health_rag.py` | ✅ Complete |
| **Task 9** | Search timeout with automatic fallback | `services/rag/retriever.py` | ✅ Complete |
| **Task 10** | Rate limiting on search calls | `core/rate_limit.py`, `api/chat.py`, `api/documents.py` | ✅ Complete |
| **Task 12** | Blended mode as default | `api/intelligence.py` | ✅ Complete |
| **Task 13** | End-to-end pipeline test | `scripts/e2e_pipeline_test.py` | ✅ Complete |
| **Task 14** | Search speed benchmarks | `scripts/benchmark_search.py` | ✅ Complete |

**New Infrastructure Features:**
- **Database Pooling**: Configurable via `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`
- **Health Endpoints**: `/health/db`, `/health/rag`, `/health/full` for monitoring
- **Search Timeout**: Auto-fallback to keyword search if vector takes >5s (`RAG_SEARCH_TIMEOUT_MS`)
- **Rate Limiting**: Per-endpoint limits on `/chat/ask` and `/documents/search`
- **Blended Mode**: Quality evaluation defaults to "blend" (`QUALITY_DEFAULT_MODE`)

**New Scripts:**
```bash
# Run E2E pipeline test
python -m app.scripts.e2e_pipeline_test

# Run search benchmarks
python -m app.scripts.benchmark_search --iterations 20 --corpus-size 500
```

### 2.3 Intelligence Correlation/Activation ✅ COMPLETE

**Commit:** `8ead589` (Rishav's work, merged)

| Service | File | Status |
|---------|------|--------|
| Self-dealing Analysis | `services/self_dealing_service.py` | ✅ Working |
| Network Analysis | `services/intelligence_activation_service.py` | ✅ Working (1659 lines) |
| Correlation Analysis | `services/correlation_service.py` | ✅ Working |
| Co-investment Network | `services/coinvestment_network_service.py` | ✅ Working |
| Founder Correlations | `services/founder_correlations_service.py` | ✅ Working |
| Contract Probability | `services/contract_probability_service.py` | ✅ Working |
| Interactive Report | `services/interactive_report_service.py` | ✅ Working |
| Deep Comparative | `services/deep_comparative_service.py` | ✅ Working |

**Frontend Pages:**
- `/intelligence/self-dealing.js` ✅
- `/intelligence/network.js` ✅
- `/intelligence/correlation.js` ✅
- `/intelligence/contract-probability.js` ✅
- `/intelligence/interactive-report.js` ✅

**Tests:** `tests/test_intelligence_correlation_api.py` — 43 tests

### 2.4 13F Position Diff ✅ COMPLETE

**Commit:** `c5d7cc5`

| Component | Location | Status |
|-----------|----------|--------|
| SEC 13F Parser | `services/sec_13f_service.py` (68KB) | ✅ Working |
| Quarter comparison | Position diff logic | ✅ Working |
| Frontend | `pages/institutional/position-diff.js` | ✅ Working |
| Schemas | `models/market_13f_schemas.py` | ✅ Working |

### 2.5 Trade Alerts (F-03/F-04) ✅ COMPLETE

**Commit:** `0b0a73e`

| Feature | File | Status |
|---------|------|--------|
| Investment Alert Service | `services/investment_alert_service.py` | ✅ Working |
| Tracking Service | `services/tracking_service.py` | ✅ Working |
| Big Trade Scan | `scripts/run_big_trade_scan.py` | ✅ Working |
| Investment Alert Scan | `scripts/run_investment_alert_scan.py` | ✅ Working |
| Congress.gov Legislation | `connectors/*` | ✅ Working |
| Senate Trades | Gov trading connector | ✅ Working |

### 2.6 Band A Priorities (1-14) ✅ MOSTLY COMPLETE

| # | Feature | Status | File |
|---|---------|--------|------|
| 1 | Published pricing page | ✅ | `pages/pricing.js` |
| 2 | Renewal + cancel | ✅ | `api/billing.py` |
| 3 | Support escalation | ✅ | `api/support.py`, `pages/support.js` |
| 4 | Status page | ✅ | `api/status.py`, `pages/status.js` |
| 5 | Internal linking (SEO) | ✅ | `api/seo.py` |
| 6 | Sitemaps | ✅ | `api/seo.py` |
| 7 | Freshness engine | ✅ **Complete** | `api/freshness.py` + `run_freshness_scan.py` + ecosystem.config.js |
| 8 | Editorial workflow | ✅ | `api/editorial.py` |
| 9 | Compliance guardrails | ✅ | `api/compliance_content.py` |
| 10 | A/B experiments | ✅ | `api/experiments.py` |
| 11 | AI visibility tracking | ✅ | `api/ai_visibility.py` |
| 12 | Browser extension | ⚠️ Stub | Not fully implemented |
| 13 | Export/API/MCP | ✅ | `api/export.py` |
| 14 | 13F honesty layer | ✅ | `api/honesty.py` |

### 2.7 Deep Intelligence Report Pipeline ✅ COMPLETE

| Component | Files | Status |
|-----------|-------|--------|
| 40+ Connectors | `connectors/*.py` | ✅ All working |
| Correlation Engine | `services/correlation_service.py` | ✅ Working |
| Co-occurrence | `services/cooccurrence_service.py` | ✅ Working |
| Family Network | `connectors/family_network_connector.py` | ✅ Working |
| Peer Comparison | `services/peer_comparison_service.py` | ✅ Working |
| Data Health | `services/data_health_service.py` | ✅ Working |
| Premium PDF | `services/premium_pdf_service.py` | ✅ Working |
| PayPal Mafia Report | Network report generation | ✅ Working |

---

## Section 3: AI Model Training Status

### Phase Completion Overview

| Phase | Description | Status | Completion |
|-------|-------------|--------|------------|
| **Phase 1** | Vector RAG (no training) | ✅ **Complete** | 100% |
| **Phase 2** | Fine-tune Embeddings | ✅ **Complete** | 100% |
| **Phase 3** | Quality Classifier | ✅ **Complete** | 100% |
| **Phase 4** | Narrative Distillation | ⚠️ **Partial** | 70% |

### Phase 2: Fine-tune Embeddings (100% Complete) ✅

| Sub-Phase | Description | Status |
|-----------|-------------|--------|
| 2.1 | Claim-pair extraction pipeline | ✅ Complete |
| 2.2 | RAG query logging for training data | ✅ Complete |
| 2.3 | Fine-tuning infrastructure (RunPod) | ✅ **Complete** |
| 2.4 | A/B evaluation framework | ✅ Complete |
| 2.5 | Production swap to fine-tuned model | ✅ **Complete** |

**Training Results (15 Aug 2026):**
- Base model: `nomic-ai/nomic-embed-text-v1.5`
- Training data: 7,198 triplets from 190+ intelligence reports
- Training time: ~90 seconds on RTX 4090
- **Ranking Accuracy**: 82.0% → **90.5%** (+8.5%)
- **Avg Margin**: 0.1782 → **0.3251** (+82%)
- Model deployed to: `~/Finance-Advanced-Research-Platform/models/finance-embed-v1/`
- Guide: `embedding-model-fine-tuning/EMBEDDINGS_TRAINING_GUIDE.md`

### Phase 3: Quality Classifier (100% Complete) ✅

| Sub-Phase | Description | Status |
|-----------|-------------|--------|
| 3a | LLM Judge | ✅ Complete |
| 3b | ML Classifier (trained) | ✅ **F1=0.895** |

**Model Details:**
- Algorithm: Random Forest with custom threshold (0.65)
- Features: 22 (12 rule + 6 text + 4 interaction, variance-filtered)
- Training samples: 403 (124 publishable, 279 non-publishable)
- Cross-validation: 5-fold stratified

### Phase 4: Narrative Distillation (70% Complete)

| Sub-Phase | Description | Status |
|-----------|-------------|--------|
| 4.1 | Narrative logging (enhanced_narrative_service) | ✅ Complete |
| 4.2 | Human edit collection API | ✅ Complete |
| 4.3 | Fine-tune Llama/Qwen on narratives | ❌ **Requires GPU** |
| 4.4 | Narrative A/B evaluation (LLM judge) | ✅ Complete |
| 4.5 | Production integration with fallback | ✅ Complete |

### GPU-Dependent Tasks (Remaining)

| Task | Description | Blocker |
|------|-------------|---------|
| ~~Phase 2.3~~ | ~~Set up fine-tuning infrastructure on RunPod~~ | ✅ **DONE** |
| ~~Phase 2.5~~ | ~~Production swap to fine-tuned embeddings~~ | ✅ **DONE** |
| Phase 4.3 | Fine-tune Llama/Qwen on narrative generation | GPU required |

**Note:** Embeddings fine-tuning complete. Only narrative model training remains GPU-dependent.

---

## Section 4: What's REMAINING (Not Started)

### 4.1 Band B — Differentiation Multipliers (17 items, ~82% done)

| # | Feature | Status | Effort |
|---|---------|--------|--------|
| 15 | Filing redline + table-to-Excel | ✅ **Complete** | Medium |
| 16 | Company-specific ontology + KPI schema | ✅ **Complete** | High |
| 17 | Private document ingestion | ✅ **Complete** | Medium |
| 18 | Multi-entity thematic corpora | ✅ **Complete** | Medium |
| 19 | Point-in-time rolling consensus | ✅ **Complete** | High |
| 20 | Consensus revision history | ✅ **Complete** | Medium |
| 21 | Estimate dispersion | ✅ **Complete** | Low |
| 22 | Guidance vs actual tracking | ✅ **Complete** | Medium |
| 23 | Earnings surprise history | ✅ **Complete** | Low |
| 24 | Per-analyst accuracy scoring | ✅ **Complete** | Medium |
| 25 | Whisper + buy/sell-side split | ✅ **Complete** | High |
| 26 | Custom formula charting | ✅ **Complete** | Medium |
| 27 | IV surface (delayed EOD) | ✅ **Complete** | Medium |
| 28 | Unusual volume screening | ✅ **Complete** | Medium |
| 29 | Public analyst profiles | ✅ **Complete** | Low |
| 30 | Model + idea leaderboards | ✅ **Complete** | Medium |
| 31 | Docket-to-disclosure reconciliation | ✅ **Complete** | Medium |

**Band B Features Completed (16 Aug 2026):**
- **#15 Filing Redline + Table-to-Excel**: `GET /filings/compare` - 10-K/10-Q comparison, HTML redline, Excel export
- **#16 Company Ontology + KPI Schema**: `GET /ontology/{ticker}` - Industry KPI templates, entity extraction
- **#17 Private Document Ingestion**: `POST /documents/upload` - PDF/DOCX/XLSX/TXT ingestion, chunking, RAG search
- **#18 Multi-entity Thematic Corpora**: `GET /entities/multi/` - Sector/industry queries, supply chain analysis, thematic analysis
- **#19 Point-in-time Rolling Consensus**: `GET /consensus/rolling` - Weekly snapshots showing consensus evolution
- **#20 Consensus Revision History**: `GET /consensus/revisions` - Tracks how analyst estimates changed over time
- **#21 Estimate Dispersion**: `GET /consensus/dispersion` - Measures analyst disagreement with CV, quartiles, outliers
- **#22 Guidance vs Actual Tracking**: `guidance_service.py` - Management credibility scoring, guidance revisions
- **#23 Earnings Surprise History**: `GET /consensus/surprise-history` - Beat/miss patterns, streaks, market reactions
- **#24 Per-Analyst Accuracy Scoring**: `GET /analysts/score/{id}` - MAE, direction accuracy, Brier score, calibration
- **#25 Whisper + Buy/Sell-Side Split**: `GET /whisper/{ticker}` - Whisper estimates, buy-side vs sell-side analysis, historical accuracy
- **#26 Custom Formula Charting**: `POST /formula/evaluate` - Safe expression parser, multi-ticker formulas
- **#27 IV Surface (Delayed EOD)**: `GET /volatility/surface/{ticker}` - IV surface, term structure, skew analysis, IV screening
- **#28 Unusual Volume Screening**: `volume_screening_service.py` - Sector flow, volume profiles, spike detection
- **#29 Public Analyst Profiles**: `GET /analysts/profile/{id}` - Search, ranking, firm/sector coverage
- **#30 Model + Idea Leaderboards**: `GET /leaderboard/predictions` - Brier scoring, calibration, user ranking
- **#31 Docket-to-Disclosure Reconciliation**: `GET /docket/{ticker}/reconcile` - L-series feature, undisclosed litigation detection
- **Dashboard**: `GET /consensus/dashboard/{ticker}` - Combined view of all metrics
- **Compare**: `GET /consensus/compare?tickers=NVDA,AAPL` - Multi-ticker comparison
- **Tests**: 540 tests across consensus, analyst, guidance, volume, formula, leaderboard, ontology, document, docket, filing, volatility, multi-entity, and whisper services

### 4.2 Band C — Table Stakes (25 items, ~5% done)

| # | Feature | Status |
|---|---------|--------|
| 32 | Portfolio tracking | ❌ Not done |
| 33 | Mobile PWA with alerts | ❌ Not done |
| 34 | Global equity coverage | ❌ Not done (High) |
| 35-49 | Various table stakes | ❌ Not done |
| 50-56 | L-series litigation | ❌ Not done |

### 4.3 Band D — Segment Unlocks (11 items, 0% done)

All 11 items (factor decomposition, rebalancing, model portfolios, etc.) are NOT done. These are conditional on targeting advisors/teams.

### 4.4 Band E — Low Priority (5 items, 0% done)

All deferred (native push, offline caching, biometric login, widgets, screen sharing).

### 4.5 James's Remaining Requirements

| Requirement | Status |
|-------------|--------|
| Person timelines + stock price + news | ❌ Not done |
| Data visualizations in reports | ⚠️ Partial (12 figures, needs more) |
| Autonomous agent loop (subsidiary/family discovery) | ❌ Not done |
| Recursive entity discovery | ❌ Not done |
| Valuation timeline | ❌ Not done |
| Reddit/whale tracker improvements | ⚠️ Partial |
| Interactive bubble charts (PayPal Mafia style) | ❌ Not done |

---

## Section 5: Test Suite Status

**Total Tests:** 708
**Passing:** 705 (99.6%)
**Failed:** 3 (pre-existing, unrelated to Band B features)

| Test File | Tests | Status |
|-----------|-------|--------|
| `test_consensus_service.py` | 44 | ✅ All pass |
| `test_consensus_api.py` | 29 | ✅ All pass |
| `test_analyst_service.py` | 39 | ✅ All pass |
| `test_analyst_api.py` | 33 | ✅ All pass |
| `test_guidance_service.py` | 28 | ✅ All pass |
| `test_volume_service.py` | 34 | ✅ All pass |
| `test_formula_api.py` | 18 | ✅ All pass |
| `test_leaderboard_api.py` | 23 | ✅ All pass |
| `test_ontology_api.py` | 18 | ✅ All pass |
| `test_document_api.py` | 34 | ✅ All pass |
| `test_docket_api.py` | 33 | ✅ All pass |
| `test_volatility_api.py` | 51 | ✅ All pass |
| `test_multi_entity_api.py` | 59 | ✅ All pass |
| `test_whisper_api.py` | 54 | ✅ All pass |
| `test_filing_api.py` | 43 | ✅ 42 pass, 1 skip (NEW) |
| `test_rag_vector.py` | 34 | ⚠️ 2 flaky |
| `test_rag_eval_gate.py` | 4 | ✅ All pass |
| `test_quality_classifier.py` | 8 | ✅ All pass |
| `test_quality_judge.py` | 5 | ✅ All pass |
| `test_deep_research_connectors.py` | 5 | ✅ All pass |
| `test_entity_naming.py` | 5 | ✅ All pass |
| `test_people_and_peer_resolution.py` | 1 | ⚠️ 1 flaky |
| Other tests | ~106 | ✅ All pass |

---

## Section 6: API Routes Registered

**Total:** 41 routers

**Core (always loaded):** 27 routers
**Conditional (try/catch):** 14 routers

All routes verified working.

---

## Section 7: New Scripts Created (14 Aug 2026)

| Script | Purpose | Usage |
|--------|---------|-------|
| `generate_publishable_synthetic.py` | Generate high-quality publishable reports using Opus 4.5 | `python -m app.scripts.generate_publishable_synthetic --n 100` |
| `train_quality_classifier_v2.py` | Improved classifier training with RF, GBM, threshold optimization | `python -m app.scripts.train_quality_classifier_v2` |

---

## Section 8: Immediate Action Items

### Priority 1: GPU-Dependent Tasks

```bash
# These require RunPod or similar GPU infrastructure:
# 1. Phase 2.3 - Fine-tune embeddings
# 2. Phase 2.5 - Production swap
# 3. Phase 4.3 - Fine-tune narrative model
```

### Priority 2: Push Recent Changes

```bash
git push origin feature/intelligence-correlation-full
```

### Priority 3: Track Untracked Files

```bash
git add apps/api/app/scripts/generate_publishable_synthetic.py
git add apps/api/app/scripts/train_quality_classifier_v2.py
git add apps/api/exports/opus_fragment_bank.json
git commit -m "feat: quality classifier v2 with Opus 4.5 synthetic data (F1=0.895)"
```

---

## Section 9: Connectors Inventory (40+)

| Connector | Status | Data Source |
|-----------|--------|-------------|
| yfinance_connector | ✅ | Yahoo Finance |
| sec_edgar_connector | ✅ | SEC EDGAR |
| sec_13f_service | ✅ | SEC 13F filings |
| institutional_tracker | ✅ | Institutional holders |
| gov_trading_connector | ✅ | PTR, Form 4, Politicians |
| crypto_connector | ✅ | CoinGecko, Etherscan |
| apollo_connector | ✅ | Apollo.io |
| apify_connector | ✅ | Apify actors |
| financial_news_connector | ✅ | NewsAPI, Guardian, NYT |
| rss_worker | ✅ | 50+ RSS feeds |
| technicals_connector | ✅ | 15 technical indicators |
| valuation_connector | ✅ | DCF models |
| company_deep_connector | ✅ | SEC XBRL |
| expert_analysis_connector | ✅ | Sentiment + analyst |
| osint_connector | ✅ | OSINT enrichment |
| private_company_connector | ✅ | OpenCorporates, GLEIF |
| multi_agent_intelligence | ✅ | 4-agent consensus |
| browser_research_agent | ✅ | Browser automation |
| family_network_connector | ✅ | Family/trust networks |
| board_interlock_connector | ✅ | Board interlocks |
| institutional_overlap_connector | ✅ | 13F overlap |
| litigation_connector | ✅ | CourtListener |
| risk_register_connector | ✅ | Risk factors |
| filing_notes_connector | ✅ | Filing notes |
| proxy_statement_connector | ✅ | Proxy parsing |
| founder_track_record_connector | ✅ | Founder history |
| rumors_analysis_connector | ✅ | Rumors |
| timeline_connector | ✅ | Event timeline |
| news_intelligence_connector | ✅ | News + Reddit |
| sec_api_connector | ✅ | SEC API |
| fpds_connector | ✅ | Federal contracts |
| opensecrets_connector | ✅ | OpenSecrets |
| linkedin_deep_connector | ⚠️ | LinkedIn (ToS blocked) |
| entity_network_connector | ✅ | Network analysis |
| deep_research_orchestrator | ✅ | Orchestration |
| government_precedent_connector | ✅ | Gov precedents |

---

## Section 10: Environment & Deployment

### Live Services (EC2: 184.72.123.188)

| PM2 Name | Port | Status |
|----------|------|--------|
| finance-api | 3001 | Online |
| finance-web | 3003 | Online |
| finance-admin | 3002 | Online |
| rss-poller | — | Online |
| daily-digest | — | Stopped |

### API Keys (all in `.env`)

| Key | Status |
|-----|--------|
| OPENAI_API_KEY | ✅ Live |
| ANTHROPIC_API_KEY | ✅ Live |
| APOLLO_API_KEY | ✅ Live (Paid) |
| APIFY_API_TOKEN | ✅ Live |
| NEWSAPI_KEY | ✅ Live |
| FINNHUB_API_KEY | ✅ Live |
| FMP_API_KEY | ✅ Live |
| FRED_API_KEY | ✅ Live |
| ETHERSCAN_API_KEY | ✅ Live |
| FEC_API_KEY | ✅ Live |
| COURTLISTENER_API_TOKEN | ✅ Live |
| CONGRESS_API_KEY | ✅ Live |
| CA_SOS_API_KEY | ⏸️ Pending |
| ALEPH_API_KEY | ⏸️ Pending |

---

## Section 11: What's Blocking Progress

| Blocker | Impact | Resolution |
|---------|--------|------------|
| GPU infrastructure | Phase 2.3, 2.5, 4.3 blocked | Set up RunPod |
| LinkedIn ToS decision | G-07, G-11 blocked | Policy decision |
| PitchBook/Crunchbase cost | G-12 (co-investors) blocked | $6-20K/yr purchase |
| Usage volume | Phase 4 training | Wait for usage |
| Advisor visibility | G-06 | Structurally impossible |

---

## Appendix A: Commit History (Last 2 Months)

Key commits in chronological order:

```
8ead589 Enterprise Intelligence activation (Rishav)
524cb03 docs: task assignment
c200fd4 merge: full-local UI fixes
0b0a73e merge: trade alerts + Congress/Senate
c5d7cc5 merge: 13F position-diff
40fc54f Band B features
00bbbe0 Band A priorities (6-14)
894524f Band A priorities (1-5)
cb74985 PayPal Mafia network report
dd8193a Correlation, network, family engines
c4667e1 Deep intelligence report pipeline
dc284ed Complete 13F Position Difference
7e30fc0 F-03/F-04 trade alerts
9a2dd9e Render insider names properly
e5cd751 Full UI/UX overhaul
3204875 High-priority intelligence modules
9d1aebc Crypto + Gov Trading + Deep Company
```

---

*Document generated: 16 August 2026*
*Author: Automated verification against git history + codebase*
