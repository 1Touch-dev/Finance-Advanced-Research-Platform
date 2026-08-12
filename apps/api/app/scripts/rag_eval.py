#!/usr/bin/env python
"""
RAG before/after evaluation CLI — the demo money-shot.

Runs a small labeled query set against a document corpus and prints, side by side,
keyword (TF-IDF/BM25) vs vector vs hybrid retrieval, plus retrieval metrics
(hit@k, MRR, nDCG@k). If OPENAI_API_KEY is unset, vector/hybrid transparently
degrade to keyword and the script still runs (showing they're identical) — set the
key to see the real before/after gap.

Usage:
  python -m app.scripts.rag_eval                 # built-in finance sample set
  python -m app.scripts.rag_eval --k 5
"""
from __future__ import annotations

import argparse
import json

from app.services.rag.eval import evaluate_retrieval, compare_modes
from app.services.rag.types import Document, RetrievalMode


# Small finance-flavored corpus + labeled queries. The keyword-hostile queries
# (synonyms / paraphrase) are where vector retrieval should win.
CORPUS = [
    Document(id="c1", text="Berkshire Hathaway raised its Apple position by 12% in Q1, its largest single holding."),
    Document(id="c2", text="The fund trimmed its exposure to financial institutions, selling Bank of America shares."),
    Document(id="c3", text="Nvidia's CEO sits on the board of a supplier that received a large government contract."),
    Document(id="c4", text="Lobbying disclosures show sharply higher spending on artificial-intelligence regulation."),
    Document(id="c5", text="A cluster of former PayPal executives co-invested in three defense-tech startups."),
    Document(id="c6", text="Quarterly revenue climbed to $1.2B, beating guidance issued the prior quarter."),
    Document(id="c7", text="Insider Form 4 filings revealed the chief executive purchased 50,000 shares."),
]

QUERIES = [
    {"query": "which stock did Buffett buy more of", "relevant_ids": ["c1"]},
    {"query": "conflict of interest with a chip maker", "relevant_ids": ["c3"]},
    {"query": "self-dealing among founders network", "relevant_ids": ["c5", "c3"]},
    {"query": "did the company beat its forecast", "relevant_ids": ["c6"]},
    {"query": "executive bought company stock", "relevant_ids": ["c7"]},
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    print("=" * 72)
    print("RETRIEVAL METRICS (higher is better)")
    print("=" * 72)
    for mode in (RetrievalMode.KEYWORD, RetrievalMode.VECTOR, RetrievalMode.HYBRID):
        m = evaluate_retrieval(QUERIES, CORPUS, mode, k=args.k)
        print(f"  {mode.value:8s}  {json.dumps(m)}")

    print("\n" + "=" * 72)
    print("SIDE-BY-SIDE TOP RESULTS")
    print("=" * 72)
    for q in QUERIES:
        print(f"\nQ: {q['query']}   (relevant: {q['relevant_ids']})")
        comp = compare_modes(q["query"], CORPUS, k=3)
        for mode, hits in comp.items():
            top = hits[0] if hits else {"id": "-", "text": "(none)"}
            marker = "✓" if top.get("id") in q["relevant_ids"] else "✗"
            print(f"  {marker} {mode:8s} → [{top['id']}] {top['text']}")

    print("\n" + "=" * 72)
    print("FAITHFULNESS (generation quality — NLI entailment if available)")
    print("=" * 72)
    from app.services.rag.eval import faithfulness_score, citation_rate, llm_judge_faithfulness
    from app.services.rag import retriever
    from app.services.rag.types import RetrievalMode as _RM
    samples = [
        ("Berkshire raised its Apple position, its largest holding [1].", "which stock did Buffett buy more of"),
        ("The company will definitely double next quarter.", "did the company beat its forecast"),  # unsupported
    ]
    for answer, q in samples:
        ctx = retriever.retrieve(q, CORPUS, mode=_RM.HYBRID, top_k=3)
        f = faithfulness_score(answer, ctx)
        line = f"  faithfulness={f['faithfulness']:.3f} ({f['method']}, unsupported={f['unsupported']}) | cited={citation_rate(answer):.0f} | answer={answer[:60]!r}"
        print(line)
        judge = llm_judge_faithfulness(answer, ctx)
        if judge:
            print(f"     LLM-judge: {judge}")


if __name__ == "__main__":
    main()
