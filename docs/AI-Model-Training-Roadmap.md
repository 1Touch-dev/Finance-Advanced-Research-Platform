# AI Model Training Roadmap

**Goal: stop being a GPT-4o-mini wrapper. Ship 2-3 small, owned, trained models against gaps that already exist in this codebase.**

---

## Why this, why now

Every "AI" feature in this platform currently calls `gpt-4o-mini` with a prompt. Nothing is trained, nothing is proprietary. Three concrete gaps already exist in shipped code:

| Gap | File | Evidence |
|---|---|---|
| RAG is not RAG | `apps/api/app/services/rag_chat_service.py:10,36` | Retrieval is TF-IDF keyword overlap (`_tfidf_score`), not vector search |
| Vector search stubbed, never built | `apps/api/app/services/document_ingestion_service.py:502` | Docstring admits: *"basic keyword search. For production, this should use vector similarity search."* |
| Quality gates are regex, not ML | `apps/api/app/services/quality_gate_service.py` | 10 gates (citation coverage, dup detection, sensitive-claim flags) are pattern lists, e.g. `SENSITIVE_PATTERNS` |
| Narrative gen is a raw API call every time | `apps/api/app/services/enhanced_narrative_service.py:40` | `_MODEL = "gpt-4o-mini"`, no caching/distillation, full OpenAI cost per report |

This is not "build India's frontier finance model." It's: fix documented TODOs in our own code with small trained models, using data we already generate, and end up owning IP instead of renting a wrapper.

---

## Legend

- 🟢 Low effort — days
- 🟡 Medium effort — weeks
- 🔴 High effort — months
- No GPU needed unless noted — most of this runs on CPU or a single rented GPU (RunPod)

---

## Phase 1 — Vector search swap-in (no training required)

> **Priority: HIGHEST. Ships in days. Immediate quality + cost win.**

| # | Task | Effort | Notes |
|---|------|--------|-------|
| 1 | Deploy off-the-shelf embedding model (`bge-large-en` or `nomic-embed`) | 🟢 | No training — just inference serving |
| 2 | Replace `_tfidf_score` in `rag_chat_service.py` with vector similarity | 🟢 | Direct fix to the retrieval step |
| 3 | Implement real vector storage for `DocumentChunk.embedding` in `document_ingestion_service.py` | 🟡 | pgvector or equivalent; field already exists, just unused |
| 4 | Replace `_basic_keyword_search` (line 502) with vector query | 🟢 | Closes the documented TODO |

**Outcome:** better retrieval accuracy, sets up the data pipeline needed for Phase 2.

---

## Phase 2 — Fine-tune embeddings on our own domain data

> **Priority: HIGH. This is the first real "trained model."**

| # | Task | Effort | Notes |
|---|------|--------|-------|
| 5 | Collect claim pairs from existing reports (SEC filings, lobbying, dossiers) as training data | 🟡 | Data already exists in generated reports |
| 6 | Fine-tune base embedding model on domain pairs | 🟡 | Single GPU, hours not days — use RunPod |
| 7 | A/B against generic embeddings on retrieval accuracy | 🟢 | Clear before/after metric |
| 8 | Swap into production RAG pipeline | 🟢 | Same interface as Phase 1, better weights |

**Outcome:** domain-specific retrieval that beats generic embeddings — a defensible, owned artifact.

---

## Phase 3 — Quality-gate classifier

> **Priority: HIGH. Best "real ML" ROI — supervised learning on data we already own.**

| # | Task | Effort | Notes |
|---|------|--------|-------|
| 9 | Export historical pass/fail labels from `quality_gate_service.py` runs | 🟢 | Every report run already generates this label |
| 10 | Train baseline classifier (logistic regression → gradient-boosted) | 🟢 | CPU only, no GPU needed |
| 11 | Upgrade to small transformer classifier if baseline insufficient | 🟡 | Only if simple models plateau |
| 12 | Run in parallel with regex gates, compare false-positive rate on sensitive claims | 🟡 | Especially `SENSITIVE_PATTERNS` (fraud, insider trading, etc.) |
| 13 | Replace/augment regex gates once classifier outperforms | 🟡 | Keep regex as a hard-fail safety net |

**Outcome:** fewer false positives/negatives on report quality, second owned model, clear metric story for stakeholders.

---

## Phase 4 — Distill the narrative generator

> **Priority: MEDIUM. Needs volume first — don't start until Phase 1-2 are live and generating data.**

| # | Task | Effort | Notes |
|---|------|--------|-------|
| 14 | Accumulate `enhanced_narrative_service.py` outputs + human edits as ground truth | 🟡 | Needs real usage volume first |
| 15 | Fine-tune/distill small open model (Llama 3.1 8B or Qwen2.5-7B) on that data | 🔴 | GPU via RunPod |
| 16 | Evaluate house-style consistency vs. `gpt-4o-mini` baseline | 🟡 | Blind comparison on sample reports |
| 17 | Cut over narrative generation to owned model | 🟡 | Keep GPT fallback for edge cases |

**Outcome:** lower per-report cost, consistent house style, IP instead of a wrapper.

---

## Sequencing summary

```
Phase 1 (days)   → vector search, no training
Phase 2 (weeks)  → fine-tuned embeddings, first owned model
Phase 3 (weeks)  → quality classifier, second owned model, runs parallel to Phase 1-2
Phase 4 (months) → narrative distillation, gated on data volume from 1-2
```

Phases 1-3 can run concurrently once Phase 1's data pipeline exists. Phase 4 is strictly gated on volume.

---

## Compute

RunPod GPU access is already available in this environment (MCP: `user-runpod`) — no separate infra provisioning needed for Phase 2 or Phase 4 training runs. Phase 3 baseline classifier needs no GPU.

---

## The pitch (for CEO / stakeholder proposal)

> We're currently 100% dependent on OpenAI API calls for every AI feature, including a "RAG" search that's actually just keyword matching — our own code documents this as a known gap. Proposing to spend [X weeks] building vector-based retrieval and a trained quality-gate classifier using data we already generate. This cuts latency, cuts OpenAI cost per report, and gives us a proprietary model asset instead of a prompt wrapper — the exact distinction investors are now flagging when they evaluate Indian fintech AI companies (owned model vs. thin wrapper).

---

## Explicitly out of scope here

The larger "India frontier finance model" / RBI-FREE-AI compliance-intelligence wedge discussed separately is a distinct, bigger bet — a potential new product line, not a task on this platform's backlog. Not included in this roadmap; would need its own proposal, dataset, and design partner.
