# RAG Upgrade Plan — Vector RAG (Phase 1) + Advanced Retrieval

**Status: Phase 1 shipped 10 Aug 2026.** This is the design + operations doc for the
`apps/api/app/services/rag` package. It replaces the TF-IDF "RAG-that-isn't-RAG"
with a real retrieval engine, while keeping keyword retrieval as a guaranteed
fallback so `/chat/ask` and `/documents/search` never hard-fail.

## Why

The codebase itself documented the lie: `rag_chat_service._tfidf_score` was keyword
overlap, and `document_ingestion_service.search_chunks` admitted *"basic keyword
search. For production, this should use vector similarity search."* The
`DocumentChunk.embedding` field existed but was never populated. This closes that.

## Architecture

```
                       ┌──────────────────────────────────────────────┐
 query ───────────────▶│              retriever.retrieve()             │
                       │  (one interface: report-claims OR doc-chunks) │
                       └───────┬───────────────────────┬───────────────┘
                               │                       │
                     ┌─────────▼────────┐    ┌─────────▼─────────┐
                     │  dense (vector)  │    │ sparse (BM25/TFIDF)│
                     │  embeddings +    │    │  keyword.py        │
                     │  vector_store    │    └─────────┬─────────┘
                     │  (numpy / HNSW)  │              │
                     └─────────┬────────┘              │
                               └───────────┬───────────┘
                                  ┌─────────▼─────────┐
                                  │  RRF fusion       │  (hybrid mode)
                                  └─────────┬─────────┘
                                  ┌─────────▼─────────┐
                                  │  cross-encoder    │  (rerank.py, optional)
                                  └─────────┬─────────┘
                                  ┌─────────▼─────────┐
                                  │  guardrails +     │
                                  │  trace            │
                                  └───────────────────┘
```

Every stage fails soft. Chain: `vector/hybrid → (no embeddings) → BM25 → TF-IDF`.

## Modules

| File | Responsibility |
|------|----------------|
| `embeddings.py` | Provider-agnostic embeddings, batched, disk-cached, normalized. Raises `EmbeddingUnavailable` (callers fall back). |
| `vector_store.py` | Brute-force cosine for small N; HNSW (`hnswlib`) once `N ≥ RAG_HNSW_MIN`. |
| `keyword.py` | BM25 via `rank_bm25`; pure-Python TF-IDF fallback. |
| `hybrid.py` | Reciprocal Rank Fusion of dense + sparse. |
| `rerank.py` | Cross-encoder rerank (`sentence-transformers`), passthrough if absent. |
| `chunking.py` | Recursive + semantic chunking. |
| `guardrails.py` | Input (prompt-injection), retrieval floor, output (no advice / grounding). |
| `trace.py` | Per-stage timing + summaries for `?debug=true`. |
| `retriever.py` | Orchestrates all of the above; single entry point. |
| `eval.py` | hit@k / MRR / nDCG + before/after comparator. |

## API surface

- `POST /chat/ask` — body adds `mode` (`vector|keyword|hybrid`, default hybrid) and
  `debug` (bool → response includes `trace`). Output guardrail may replace the
  answer; input guardrail can reject the query.
- `GET /documents/search` — adds `?mode=` and `?debug=`. Response includes
  per-result `score` + `components` and an optional `trace`.

## Configuration (env vars)

| Var | Default | Meaning |
|-----|---------|---------|
| `OPENAI_API_KEY` | — | Required for vector/hybrid; absent → keyword fallback. |
| `RAG_EMBED_MODEL` | `text-embedding-3-small` | Embedding model. |
| `RAG_EMBED_BATCH` | `128` | Embedding batch size. |
| `RAG_CHUNK_STRATEGY` | `recursive` | `recursive` or `semantic`. |
| `RAG_SEMANTIC_THRESHOLD` | `0.55` | Cosine cut for semantic chunk boundaries. |
| `RAG_RRF_K` | `60` | RRF constant. |
| `RAG_RERANK` | `auto` | `auto|on|off` cross-encoder rerank. |
| `RAG_RERANK_MODEL` | `BAAI/bge-reranker-base` | Reranker model. |
| `RAG_HNSW_MIN` | `2000` | Corpus size at which HNSW kicks in. |
| `RAG_HNSW_EF` | `128` | HNSW query-time recall/latency knob (tune without rebuild). |
| `RAG_HNSW_EF_CONSTRUCTION` | `200` | HNSW build-time candidate list. |
| `RAG_HNSW_M` | `16` | HNSW edges per node. |
| `RAG_EXACT_SEARCH` | `false` | Force exact brute-force cosine even past `RAG_HNSW_MIN` (compliance/critical corpora — no silently-missed neighbors). |
| `RAG_MIN_CHUNK_CHARS` | `80` | Chunks shorter than this are merged into a neighbor. |
| `RAG_TABLE_AWARE` | `true` | Detect tables and chunk them row-group-wise with headers preserved. |
| `RAG_TABLE_ROWS_PER_CHUNK` | `20` | Rows per table chunk (header re-attached to each). |
| `RAG_EMBED_RETRIES` | `3` | OpenAI embedding retry attempts (exponential backoff). |
| `RAG_LOCAL_EMBED_MODEL` | — | Optional local sentence-transformers embedding model used if OpenAI fails (before dropping to keyword). |
| `RAG_NLI_MODEL` | `cross-encoder/nli-deberta-v3-small` | NLI model for faithfulness entailment. |
| `RAG_JUDGE_MODEL` | `gpt-4o-mini` | LLM-as-judge faithfulness model. |
| `RAG_VECTOR_BACKEND` | `auto` | `auto|pg|memory` — durable pgvector store vs in-memory numpy. |
| `RAG_PG_TABLE` | `rag_embeddings` | Postgres table for the durable store. |
| `RAG_PG_ALLOW_REEMBED` | `0` | If `1`, on embedding-dim change the pgvector column is truncated+re-typed so a re-ingest repopulates it (migration escape hatch). Off = loud warning, data untouched. |
| `RAG_MAX_TOP_K` | `100` | Hard upper bound on `top_k` (input validation; prevents OOM-by-huge-slice). |
| `RAG_RATE_LIMIT` | `on` | `on|off` — in-process rate limiting on the RAG endpoints. |
| `RAG_ASK_RATE_LIMIT` | `20` | `/chat/ask` requests per 60s per client. |
| `RAG_SEARCH_RATE_LIMIT` | `30` | `/documents/search` requests per 60s per client. |
| `RAG_PRELOAD` | `on` | `on|off` — warm the reranker at startup (thread-safe singleton) so first request isn't a cold start. |
| `RAG_MIN_RETRIEVAL_SCORE` | `0.15` | "Insufficient evidence" floor. |
| `EXPORT_DIR` | `exports` | Root for the embed cache. |

## Embedding-model choice

Default is **`text-embedding-3-small`** (1536-d): cheap, strong general-purpose,
zero infra. `text-embedding-3-large` (3072-d) is a one-env-var upgrade when
accuracy matters more than cost. For a fully-owned/offline stack, `bge-large-en-v1.5`
or `nomic-embed-text-v1.5` slot in behind `embeddings.py` (add a local backend).
For finance specifically, `voyage-finance-2` is worth benchmarking. **The eval
harness on OUR data decides — not vendor claims.** This is also the on-ramp to
Phase 2 (fine-tuned domain embeddings): same interface, better weights.

## Running the before/after demo

```bash
cd apps/api && source .venv/bin/activate
export OPENAI_API_KEY=sk-...        # without it, all modes == keyword (honest fallback)
python -m app.scripts.rag_eval --k 5
```

Prints hit@k / MRR / nDCG per mode and side-by-side top hits. The keyword-hostile
queries (paraphrase / synonym) are where vector + hybrid pull ahead.

## Tests

`apps/api/tests/test_rag_vector.py` — 17 tests, embeddings mocked, runs offline:
retrieval modes, RRF, BM25, guardrails, fallback path, `answer_question` wiring,
chunking guards (tiny-merge, giant-wall bounding, semantic default), faithfulness
overlap fallback, and embedding retry/local-tier resilience.

## Follow-ups

- **pgvector on Postgres** — ✅ **DONE.** `pgvector_store.py` provides a durable
  `PgVectorStore` (auto-activates when `DATABASE_URL` is Postgres + `pgvector`
  installed; local SQLite keeps the in-memory numpy store). IVFFlat cosine index;
  `upsert`/`search` mirror the in-memory interface.
- **Cross-encoder reranker** — ✅ **DONE.** `sentence-transformers` installed;
  rerank is active (no longer passthrough).
- **Faithfulness eval** — ✅ **DONE.** `eval.faithfulness_score` uses an NLI
  cross-encoder (per-claim entailment; hallucinated claims score ~0), degrading to
  token-overlap if the model is absent. `eval.llm_judge_faithfulness` adds optional
  LLM-as-judge scoring. Verified: grounded answer 0.996, hallucination 0.000.
- **Embedding resilience** — ✅ **DONE.** OpenAI retried with exponential backoff
  (tenacity); optional local model tier (`RAG_LOCAL_EMBED_MODEL`) before keyword.
- **Chunking guards** — ✅ **DONE.** Default strategy now `semantic`; sub-min
  chunks merged forward.
- **HNSW tuning** — ✅ **DONE.** `ef`/`M`/`ef_construction` env-tunable;
  `RAG_EXACT_SEARCH` forces exact search for critical corpora.

## Production-readiness punch list — ✅ DONE

The audit that flagged this pipeline as "demo-ready, not multi-tenant-scale-ready"
has been cleared. What changed:

1. **Persistent index in the live path (the #1 flaw).** Retrieval no longer
   re-embeds + rebuilds the vector index on every query. New `index.py`
   (`IndexManager`) caches one dense index per collection, keyed by a content
   fingerprint, and only rebuilds when the corpus actually changes. On Postgres
   it routes to `PgVectorStore` (ingest upserts once via
   `document_ingestion_service._persist_chunks`, queries do in-DB ANN); on SQLite/dev
   it reuses a process-wide cached numpy/HNSW store. **Measured: 5 queries → 1
   build** (was 5). Thread-safe (`RLock`), build happens outside the lock.
2. **Rate limiting.** `core/rate_limit.py` — per-client sliding-window limiter as a
   FastAPI dependency on `/chat/ask` (`RAG_ASK_RATE_LIMIT`) and `/documents/search`
   (`RAG_SEARCH_RATE_LIMIT`). Returns 429 + `Retry-After`. Stops bill-spike/DoS.
3. **Thread-safe model loading + preload.** `rerank.py` now loads the cross-encoder
   under a lock (load-once singleton, no N-way construction under concurrent first
   requests) and exposes `preload()`, called from a background thread in the
   FastAPI `startup` hook (`RAG_PRELOAD`). No user eats the cold start.
4. **Ops observability.** `metrics.py` emits a **PII-safe** structured log line per
   retrieval (query *hash*, mode, backend, corpus size, latency, top score,
   fallback flag, rerank state, guardrail flags, correlation id) + in-process
   counters/histograms (mirrored to Prometheus if `prometheus_client` is installed).
   Surfaced at **`GET /health/rag`** (readiness + live metrics snapshot).
5. **Input bounds.** `top_k` clamped to `RAG_MAX_TOP_K`; empty queries short-circuit;
   `query`/`question` length-capped at the API. No OOM-by-huge-slice.
6. **Tenant isolation.** `search_chunks(user_id=...)` filters to the caller's
   documents *in the service* (not left to the caller), and the collection key is
   scoped `docs:{tenant}:{filter}` so cached/persisted indexes never cross tenants.
7. **Correctness — no rerank aliasing.** `rerank()` returns *fresh* `ScoredDoc`s
   instead of mutating inputs in place, so a shared/cached index's scores can't be
   corrupted across concurrent queries.
8. **pgvector index tuning + migration story.** IVFFlat `lists` auto-retuned to
   `≈sqrt(rows)` with `ANALYZE` once a collection grows past 1k rows; embedding-dim
   changes are detected and, with `RAG_PG_ALLOW_REEMBED=1`, the column is
   re-typed + truncated for a clean re-ingest (else a loud warning, data intact).

### Still open (non-blocking)
- **Larger eval set + CI gate** — mine historical report Q&A into a real labeled set
  (N≫5) and fail the build on hit@k regression.
- **Async embedding calls** — embeddings are currently sync `requests`.
- **Distributed rate limiting** — current limiter is per-process; move to Redis when
  running multiple API replicas.
- **Phase 2** — fine-tune the embedding model on our claim pairs.

### Table/financial-statement-aware chunking — ✅ DONE
`chunking.table_aware_chunk` (on by default, `RAG_TABLE_AWARE=true`) detects
tabular blocks (pipe-delimited runs — exactly what the XLSX/CSV extractors emit,
plus markdown tables), and chunks them **row-group-wise with the header row
re-attached to every chunk** (`RAG_TABLE_ROWS_PER_CHUNK=20`). A heading-like
lead-in (e.g. `## Sheet: Balance Sheet`) is captured once as a caption. Prose
around tables is chunked separately with the configured strategy; table rows are
never split mid-row. This fixes the balance-sheet-shredding gap: a retrieved
`Free cash flow | 60 | 95 | 140` row now always carries its `Metric | 2022 | 2023`
column context. Verified live: CSV financials ingested → header-preserving chunk →
vector query returned the row with headers intact.
