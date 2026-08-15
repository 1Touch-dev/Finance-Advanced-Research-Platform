# AI Model Training — Phases 2 & 4 Implementation Plan

**Created:** 13 August 2026
**Author:** Implementation planning
**Prerequisites:** Phase 1 (RAG) ✅ DONE, Phase 3 (Quality Layer) ✅ DONE (needs merge)

---

## Executive Summary

| Phase | What | Why | Effort | Blocker |
|-------|------|-----|--------|---------|
| **Phase 2** | Fine-tune embeddings on domain data | Domain-specific retrieval beats generic by 15-30% | 🟡 2-3 weeks | Need ~10K claim pairs |
| **Phase 4** | Distill narrative generator to owned model | Cut OpenAI cost 90%, own the IP | 🔴 4-6 weeks | Need ~1K report outputs |

**Current State:**
- Phase 1 (RAG) — ✅ Shipped, 38 tests passing
- Phase 3 (Quality) — ✅ Built on `feature/quality-gate-ml` (needs merge)
- Phase 2 — ❌ Not started (this plan)
- Phase 4 — ❌ Not started (this plan)

---

# PHASE 2: Fine-Tune Embeddings on Domain Data

## 2.1 Goal

Replace generic `text-embedding-3-small` with a **domain-tuned embedding model** that understands financial/regulatory language better.

**Expected outcome:**
- 15-30% improvement in retrieval accuracy (MRR, hit@k)
- Better semantic matching for finance terms (e.g., "dilution" ↔ "share issuance")
- Defensible proprietary model asset

## 2.2 Data Requirements

### What we need: ~10,000 claim pairs

| Data Type | Source | Count Today | Target |
|-----------|--------|-------------|--------|
| **Positive pairs** (semantically similar) | Report claims ↔ source excerpts | ~500 | 5,000 |
| **Hard negatives** (same topic, different meaning) | Same-section different claims | ~200 | 3,000 |
| **Cross-document pairs** | Same fact across filings | ~100 | 2,000 |

### Where the data exists

```
┌─────────────────────────────────────────────────────────────┐
│  DATA SOURCE                        │  LOCATION            │
├─────────────────────────────────────────────────────────────┤
│  Generated reports (39 in DB)       │  local.db            │
│  On-disk reports                    │  reports/*.json      │
│  RAG chat Q&A logs                  │  (to be added)       │
│  SEC filings (claim citations)      │  connectors output   │
│  Quality label judgments            │  exports/*.jsonl     │
└─────────────────────────────────────────────────────────────┘
```

## 2.3 Implementation Plan

### Task 2.1: Build the Claim-Pair Extraction Pipeline (🟢 3-5 days)

**File:** `apps/api/app/scripts/extract_embedding_pairs.py`

```python
"""
Extract (query, positive, hard_negative) triplets from existing reports
for contrastive fine-tuning of embedding model.
"""

from dataclasses import dataclass
from typing import List, Tuple
import json

@dataclass
class EmbeddingTriplet:
    anchor: str           # The claim or query
    positive: str         # Semantically similar (from cited source)
    hard_negative: str    # Same topic, different meaning
    source: str           # Where this came from

def extract_from_report(report_data: dict) -> List[EmbeddingTriplet]:
    """
    For each claim in the report:
    1. Anchor = the claim text
    2. Positive = the cited source excerpt (if available)
    3. Hard negative = another claim from same section (different meaning)
    """
    triplets = []
    # Implementation...
    return triplets

def extract_from_rag_logs(log_path: str) -> List[EmbeddingTriplet]:
    """
    For each RAG Q&A:
    1. Anchor = user query
    2. Positive = chunks that were retrieved and used in answer
    3. Hard negative = chunks retrieved but not used
    """
    pass

def main():
    # 1. Process all DB reports
    # 2. Process all on-disk reports
    # 3. Process RAG chat logs (if available)
    # 4. Write to exports/embedding_triplets.jsonl
    pass
```

**Output:** `exports/embedding_triplets.jsonl`
```jsonl
{"anchor": "NVIDIA's revenue grew 122% YoY in Q3 2024", "positive": "Revenue increased from $5.93B to $13.51B...", "hard_negative": "AMD reported Q3 revenue of $5.8B...", "source": "report:NVIDIA_Corp_20260804"}
```

### Task 2.2: Add RAG Query Logging (🟢 2-3 days)

**Modify:** `apps/api/app/services/rag/retriever.py`

```python
# Add to retrieve() function:
def _log_retrieval_for_training(
    query: str,
    retrieved_docs: List[ScoredDoc],
    used_in_answer: List[str],  # Which docs actually contributed
    answer: str,
):
    """
    Log retrieval events for future fine-tuning.
    Positive = docs used in answer
    Hard negative = docs retrieved but not used
    """
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "query": query,
        "positive_chunks": [d.content for d in retrieved_docs if d.id in used_in_answer],
        "hard_negative_chunks": [d.content for d in retrieved_docs if d.id not in used_in_answer],
        "answer_length": len(answer),
    }
    # Append to exports/rag_training_log.jsonl
```

### Task 2.3: Set Up Fine-Tuning Infrastructure (🟡 3-5 days)

**File:** `apps/api/app/scripts/finetune_embeddings.py`

```python
"""
Fine-tune embedding model on domain triplets using sentence-transformers.
Runs on RunPod GPU (already available via MCP).
"""

from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
import json

# Base model options (in order of preference):
# 1. BAAI/bge-base-en-v1.5 (smaller, faster)
# 2. BAAI/bge-large-en-v1.5 (better quality)
# 3. nomic-ai/nomic-embed-text-v1.5 (good balance)

BASE_MODEL = "BAAI/bge-base-en-v1.5"
OUTPUT_DIR = "models/finance-embed-v1"

def load_triplets(path: str) -> List[InputExample]:
    """Load triplets as sentence-transformers InputExamples."""
    examples = []
    with open(path) as f:
        for line in f:
            t = json.loads(line)
            # For MultipleNegativesRankingLoss:
            examples.append(InputExample(
                texts=[t["anchor"], t["positive"]]
            ))
    return examples

def train():
    model = SentenceTransformer(BASE_MODEL)

    train_examples = load_triplets("exports/embedding_triplets.jsonl")
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=32)

    # MultipleNegativesRankingLoss is standard for embedding fine-tuning
    train_loss = losses.MultipleNegativesRankingLoss(model)

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=3,
        warmup_steps=100,
        output_path=OUTPUT_DIR,
        show_progress_bar=True,
    )

    print(f"Model saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    train()
```

### Task 2.4: A/B Evaluation Framework (🟢 2-3 days)

**File:** `apps/api/app/scripts/eval_embeddings_ab.py`

```python
"""
A/B comparison: generic vs fine-tuned embeddings on our eval set.
"""

from app.services.rag.eval import evaluate_retrieval
from app.services.rag.embeddings import EmbeddingProvider

def run_ab_test(eval_set_path: str):
    """
    Run both models on the same eval set, compare:
    - hit@1, hit@5, hit@10
    - MRR (Mean Reciprocal Rank)
    - nDCG@10
    - Latency
    """

    # Model A: Generic (current production)
    generic_provider = EmbeddingProvider(model="text-embedding-3-small")

    # Model B: Fine-tuned (local)
    finetuned_provider = EmbeddingProvider(
        model="models/finance-embed-v1",
        provider="local"
    )

    results_a = evaluate_retrieval(eval_set_path, generic_provider)
    results_b = evaluate_retrieval(eval_set_path, finetuned_provider)

    print("\n=== A/B Comparison ===")
    print(f"{'Metric':<20} {'Generic':<15} {'Fine-tuned':<15} {'Delta':<10}")
    print("-" * 60)
    for metric in ["hit@5", "mrr", "ndcg@10"]:
        a = results_a[metric]
        b = results_b[metric]
        delta = ((b - a) / a) * 100
        print(f"{metric:<20} {a:.4f}         {b:.4f}         {delta:+.1f}%")
```

### Task 2.5: Production Swap (🟢 1-2 days)

**Modify:** `apps/api/app/services/rag/embeddings.py`

```python
# Add support for local fine-tuned model:

RAG_EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "text-embedding-3-small")
RAG_LOCAL_EMBED_PATH = os.getenv("RAG_LOCAL_EMBED_PATH", None)

def _get_embedder():
    if RAG_LOCAL_EMBED_PATH:
        # Use fine-tuned local model
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(RAG_LOCAL_EMBED_PATH)
    else:
        # Use OpenAI
        return OpenAIEmbedder(model=RAG_EMBED_MODEL)
```

**Environment variable to enable:**
```bash
RAG_LOCAL_EMBED_PATH=models/finance-embed-v1
```

## 2.4 Success Criteria

| Metric | Baseline (Generic) | Target (Fine-tuned) |
|--------|-------------------|---------------------|
| hit@5 | 1.0 | ≥1.0 (maintain) |
| MRR | 0.97 | ≥0.98 |
| Latency | ~200ms | ≤250ms (local model may be slower) |
| Domain queries (finance-specific) | ~0.85 | ≥0.95 |

## 2.5 Timeline

| Week | Task | Deliverable |
|------|------|-------------|
| 1 | Task 2.1 + 2.2 | Claim-pair extractor + RAG logging |
| 2 | Task 2.3 | Fine-tuning script + RunPod setup |
| 3 | Task 2.4 + 2.5 | A/B evaluation + production swap |

---

# PHASE 4: Distill Narrative Generator

## 4.1 Goal

Replace `gpt-4o-mini` API calls in `enhanced_narrative_service.py` with a **fine-tuned open model** (Llama 3.1 8B or Qwen2.5-7B).

**Expected outcome:**
- 90% reduction in per-report OpenAI cost
- Consistent "house style" for narratives
- Owned IP instead of API wrapper
- Faster inference (local GPU)

## 4.2 Current State

**File:** `apps/api/app/services/enhanced_narrative_service.py` (40KB)

```python
_MODEL = "gpt-4o-mini"  # Every call goes to OpenAI

# Generates:
# - Executive Summary
# - Investment Thesis (Buy/Hold/Sell)
# - SWOT Analysis
# - Risk Matrix
# - Financial Health Summary
# - Competitive Analysis
# - Bottom Line
# - Key Personnel
# - Network Mapping
# - Watch Items
# - Government Exposure
```

**Current cost per report:** ~$0.02-0.05 (500-2000 tokens per section × 11 sections)

## 4.3 Data Requirements

### What we need: ~1,000 high-quality report outputs

| Data Type | Source | Count Today | Target |
|-----------|--------|-------------|--------|
| **Full report outputs** | enhanced_narrative calls | ~39 | 500 |
| **Human-edited reports** | Manual review/edits | ~0 | 200 |
| **Quality-filtered outputs** | judge_publishable=True | ~18 | 300 |

### Collection Strategy

```python
# 1. Log every enhanced_narrative output
def _log_narrative_output(
    entity_name: str,
    section: str,
    prompt: str,
    output: str,
    model: str,
):
    """Log for fine-tuning dataset."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "entity": entity_name,
        "section": section,
        "prompt": prompt,
        "output": output,
        "model": model,
        "tokens": len(output.split()),
    }
    # Append to exports/narrative_training_log.jsonl

# 2. Collect human edits
# Add "Edit & Save" button to report UI
# Log: original → edited (the edited version is gold standard)
```

## 4.4 Implementation Plan

### Task 4.1: Build Narrative Logging Pipeline (🟢 2-3 days)

**Modify:** `apps/api/app/services/enhanced_narrative_service.py`

```python
import os
import json
from datetime import datetime

NARRATIVE_LOG_PATH = "exports/narrative_training_log.jsonl"
NARRATIVE_LOG_ENABLED = os.getenv("NARRATIVE_LOG_ENABLED", "true").lower() == "true"

def _log_narrative(entity: str, section: str, prompt: str, output: str):
    if not NARRATIVE_LOG_ENABLED:
        return

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "entity": entity,
        "section": section,
        "prompt": prompt,
        "output": output,
        "model": _MODEL,
        "token_count": len(output.split()),
    }

    with open(NARRATIVE_LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# Add to each generation function:
def generate_executive_summary(entity_name: str, report_data: dict) -> str:
    prompt = get_executive_summary_prompt(entity_name, report_data)
    output = _call_openai(prompt)
    _log_narrative(entity_name, "executive_summary", prompt, output)
    return output
```

### Task 4.2: Human Edit Collection (🟡 1 week)

**Frontend:** Add edit capability to report viewer

```javascript
// apps/web/pages/intelligence/[id].js

function EditableSection({ section, content, onSave }) {
  const [editing, setEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(content);

  const handleSave = async () => {
    await fetch(`/api/intelligence/${reportId}/edit`, {
      method: 'POST',
      body: JSON.stringify({
        section,
        original: content,
        edited: editedContent,
      })
    });
    setEditing(false);
  };

  return (
    <div>
      {editing ? (
        <textarea value={editedContent} onChange={e => setEditedContent(e.target.value)} />
      ) : (
        <div>{content}</div>
      )}
      <button onClick={() => editing ? handleSave() : setEditing(true)}>
        {editing ? 'Save Edit' : 'Edit'}
      </button>
    </div>
  );
}
```

**Backend:** Log edits

```python
# apps/api/app/api/intelligence.py

@router.post("/{report_id}/edit")
async def save_edit(report_id: str, edit: EditRequest):
    """Log human edits for fine-tuning."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "report_id": report_id,
        "section": edit.section,
        "original": edit.original,
        "edited": edit.edited,
        "is_human_edit": True,
    }
    with open("exports/narrative_edits.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    return {"status": "saved"}
```

### Task 4.3: Fine-Tuning Setup (🔴 2-3 weeks)

**File:** `apps/api/app/scripts/finetune_narrative.py`

```python
"""
Fine-tune Llama 3.1 8B or Qwen2.5-7B on narrative generation.
Runs on RunPod (A100 40GB recommended).
"""

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
)
from peft import LoraConfig, get_peft_model
from datasets import load_dataset
import json

# Model options:
# 1. meta-llama/Meta-Llama-3.1-8B-Instruct (best quality)
# 2. Qwen/Qwen2.5-7B-Instruct (good balance)
# 3. mistralai/Mistral-7B-Instruct-v0.3 (fast)

BASE_MODEL = "meta-llama/Meta-Llama-3.1-8B-Instruct"
OUTPUT_DIR = "models/finance-narrative-v1"

def prepare_dataset(log_path: str, edits_path: str):
    """
    Combine logged outputs + human edits into training format.
    Human edits are weighted higher.
    """
    examples = []

    # Regular outputs (lower weight)
    with open(log_path) as f:
        for line in f:
            entry = json.loads(line)
            examples.append({
                "prompt": entry["prompt"],
                "completion": entry["output"],
                "weight": 1.0,
            })

    # Human edits (higher weight — these are gold standard)
    with open(edits_path) as f:
        for line in f:
            entry = json.loads(line)
            examples.append({
                "prompt": entry["original"],  # What the model produced
                "completion": entry["edited"],  # What the human wanted
                "weight": 3.0,  # 3x weight
            })

    return examples

def train():
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    # LoRA for efficient fine-tuning
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)

    # Prepare data
    train_data = prepare_dataset(
        "exports/narrative_training_log.jsonl",
        "exports/narrative_edits.jsonl"
    )

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-5,
        warmup_steps=100,
        logging_steps=10,
        save_steps=500,
        fp16=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
    )

    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    print(f"Model saved to {OUTPUT_DIR}")

if __name__ == "__main__":
    train()
```

### Task 4.4: Evaluation Framework (🟡 1 week)

**File:** `apps/api/app/scripts/eval_narrative_ab.py`

```python
"""
A/B evaluation: GPT-4o-mini vs fine-tuned model.
Uses LLM-as-judge for quality comparison.
"""

def evaluate_narrative(prompt: str, model_a_output: str, model_b_output: str) -> dict:
    """
    Use GPT-4 as judge to compare outputs.
    Returns which is better on: accuracy, clarity, style, citations.
    """
    judge_prompt = f"""
    Compare these two financial analysis narratives.

    PROMPT: {prompt}

    OUTPUT A:
    {model_a_output}

    OUTPUT B:
    {model_b_output}

    Rate each on a scale of 1-5 for:
    1. Accuracy (factual correctness)
    2. Clarity (easy to understand)
    3. Professional style (reads like analyst report)
    4. Evidence use (cites sources appropriately)

    Return JSON: {{"a": {{...scores...}}, "b": {{...scores...}}, "winner": "A" or "B" or "tie"}}
    """

    # Call GPT-4 as judge
    result = call_openai(judge_prompt, model="gpt-4")
    return json.loads(result)

def run_ab_test(test_prompts: List[str]):
    """Run A/B test on sample prompts."""

    results = {"a_wins": 0, "b_wins": 0, "ties": 0}

    for prompt in test_prompts:
        output_a = call_openai(prompt, model="gpt-4o-mini")  # Current
        output_b = call_local(prompt, model="models/finance-narrative-v1")  # New

        eval_result = evaluate_narrative(prompt, output_a, output_b)

        if eval_result["winner"] == "A":
            results["a_wins"] += 1
        elif eval_result["winner"] == "B":
            results["b_wins"] += 1
        else:
            results["ties"] += 1

    print(f"\n=== A/B Results ===")
    print(f"GPT-4o-mini wins: {results['a_wins']}")
    print(f"Fine-tuned wins: {results['b_wins']}")
    print(f"Ties: {results['ties']}")
```

### Task 4.5: Production Integration (🟡 1 week)

**Modify:** `apps/api/app/services/enhanced_narrative_service.py`

```python
import os
from typing import Optional

# Model selection
NARRATIVE_MODEL = os.getenv("NARRATIVE_MODEL", "openai")  # "openai" or "local"
NARRATIVE_LOCAL_PATH = os.getenv("NARRATIVE_LOCAL_PATH", "models/finance-narrative-v1")

def _generate(prompt: str, max_tokens: int = 2000) -> str:
    """Generate narrative using configured model."""

    if NARRATIVE_MODEL == "local":
        return _generate_local(prompt, max_tokens)
    else:
        return _generate_openai(prompt, max_tokens)

def _generate_local(prompt: str, max_tokens: int) -> str:
    """Generate using local fine-tuned model."""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # Load model (cached after first call)
    if not hasattr(_generate_local, "_model"):
        _generate_local._tokenizer = AutoTokenizer.from_pretrained(NARRATIVE_LOCAL_PATH)
        _generate_local._model = AutoModelForCausalLM.from_pretrained(
            NARRATIVE_LOCAL_PATH,
            torch_dtype=torch.bfloat16,
            device_map="auto",
        )

    inputs = _generate_local._tokenizer(prompt, return_tensors="pt")
    outputs = _generate_local._model.generate(
        **inputs,
        max_new_tokens=max_tokens,
        do_sample=True,
        temperature=0.7,
    )

    return _generate_local._tokenizer.decode(outputs[0], skip_special_tokens=True)

def _generate_openai(prompt: str, max_tokens: int) -> str:
    """Generate using OpenAI API (current behavior)."""
    response = requests.post(
        _OPENAI_BASE,
        headers={"Authorization": f"Bearer {_OPENAI_KEY}"},
        json={
            "model": _MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
        timeout=_TIMEOUT,
    )
    return response.json()["choices"][0]["message"]["content"]
```

**Fallback mechanism:**

```python
def _generate(prompt: str, max_tokens: int = 2000) -> str:
    """Generate with automatic fallback."""

    if NARRATIVE_MODEL == "local":
        try:
            return _generate_local(prompt, max_tokens)
        except Exception as e:
            logger.warning(f"Local model failed, falling back to OpenAI: {e}")
            return _generate_openai(prompt, max_tokens)
    else:
        return _generate_openai(prompt, max_tokens)
```

## 4.5 Success Criteria

| Metric | Baseline (GPT-4o-mini) | Target (Fine-tuned) |
|--------|------------------------|---------------------|
| Quality score (LLM judge) | 4.2/5 | ≥4.0/5 |
| Style consistency | N/A | Measurable house style |
| Cost per report | $0.03 | $0.003 (10x reduction) |
| Latency | ~3s | ~5s (acceptable) |
| Fallback rate | N/A | <5% |

## 4.6 Timeline

| Week | Task | Deliverable |
|------|------|-------------|
| 1-2 | Task 4.1 + 4.2 | Logging + edit collection |
| 3-4 | Task 4.3 | Fine-tuning setup + training |
| 5 | Task 4.4 | Evaluation framework |
| 6 | Task 4.5 | Production integration |

---

# Combined Roadmap

```
                            PHASE 2                          PHASE 4
                    (Fine-tune Embeddings)          (Distill Narrative)

Week 1-2:           [Extract pairs]                 [Add logging]
                    [Add RAG logging]               [Add edit UI]
                           ↓                              ↓
Week 3:             [Fine-tune on RunPod]           [Collect data...]
                           ↓                              ↓
Week 4:             [A/B evaluation]                [Continue collecting]
                           ↓                              ↓
Week 5:             [SHIP TO PROD] ✅               [Fine-tune on RunPod]
                                                          ↓
Week 6:                                             [A/B evaluation]
                                                          ↓
Week 7:                                             [SHIP TO PROD] ✅
```

## Blockers & Dependencies

| Blocker | Impact | Resolution |
|---------|--------|------------|
| **Data volume** | Both phases need usage | Generate reports, enable logging |
| **RunPod GPU access** | Training requires A100 | Already available via MCP |
| **Human editors** | Phase 4 needs gold edits | Assign team to review reports |
| **Quality gate merge** | Phase 3 branch not merged | Merge `feature/quality-gate-ml` |

## Compute Requirements

| Phase | GPU | Time | Cost (RunPod) |
|-------|-----|------|---------------|
| Phase 2 | A100 40GB | ~2-4 hours | ~$10-20 |
| Phase 4 | A100 80GB | ~8-16 hours | ~$40-80 |

---

## Immediate Next Steps

1. **Merge `feature/quality-gate-ml`** — enables quality-filtered data collection
2. **Enable narrative logging** — add `_log_narrative()` calls to enhanced_narrative_service.py
3. **Create extraction script** — `extract_embedding_pairs.py`
4. **Start generating reports** — need volume for training data
5. **Add edit UI** — collect human corrections

---

*Plan created: 13 August 2026*
