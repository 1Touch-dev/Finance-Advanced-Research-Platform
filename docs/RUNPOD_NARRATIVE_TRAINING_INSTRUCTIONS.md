# RunPod Narrative Model Training — Complete Instructions

**Created:** 21 August 2026
**Purpose:** Step-by-step guide to train the Finance Narrative Distillation Model on RunPod GPU

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Data Inventory — What We Have vs Need](#2-data-inventory)
3. [RunPod Account Setup](#3-runpod-account-setup)
4. [GPU Pod Configuration](#4-gpu-pod-configuration)
5. [Environment Setup on Pod](#5-environment-setup-on-pod)
6. [Data Upload to Pod](#6-data-upload-to-pod)
7. [Training Script Configuration](#7-training-script-configuration)
8. [Running Training](#8-running-training)
9. [Model Evaluation](#9-model-evaluation)
10. [Model Download & Deployment](#10-model-download--deployment)
11. [Common Errors & Solutions](#11-common-errors--solutions)
12. [Cost Estimation](#12-cost-estimation)
13. [Checklist Before Training](#13-checklist-before-training)

---

## 1. Executive Summary

### Goal
Fine-tune Llama 3.1 8B (or Qwen2.5-7B) to generate financial analysis narratives, reducing OpenAI API dependency by 90%.

### Current State
| Component | Status | Notes |
|-----------|--------|-------|
| Base model selected | ✅ | meta-llama/Meta-Llama-3.1-8B-Instruct |
| Training script | ✅ | `finetune_narrative.py` exists (mock) |
| RunPod account | ❓ | Need to verify/create |
| Training data | 🟡 | Have some, need more (see Section 2) |
| Evaluation framework | ✅ | A/B comparison using LLM-as-judge |

### Expected Outcome
- Model that generates consistent "house style" narratives
- Cost reduction: $0.03/report → $0.003/report
- Owned IP instead of API wrapper

---

## 2. Data Inventory

### Current Training Data Available

Location: `apps/api/exports/`

| File | Records | Size | Status | Usage |
|------|---------|------|--------|-------|
| `embedding_triplets.jsonl` | 1,656 | 787KB | ✅ Have | Embedding fine-tuning |
| `rag_training_log.jsonl` | 150 | 153KB | ✅ Have | RAG retrieval pairs |
| `quality_labels_synthetic.jsonl` | 380 | 334KB | ✅ Have | Quality scoring |
| `quality_labels.jsonl` | 24 | 19KB | ✅ Have | Quality scoring |
| `narrative_training_log.jsonl` | **0** | 0KB | ❌ Missing | **CRITICAL FOR NARRATIVE TRAINING** |
| `narrative_edits.jsonl` | **0** | 0KB | ❌ Missing | Human-edited gold standard |

### Data Requirements for Narrative Training

| Data Type | Current Count | Target Count | Gap | Priority |
|-----------|---------------|--------------|-----|----------|
| Narrative outputs (prompt→response) | 0 | 500 | -500 | 🔴 CRITICAL |
| Human-edited narratives | 0 | 200 | -200 | 🟡 HIGH |
| Quality-filtered outputs | 0 | 300 | -300 | 🟡 HIGH |
| **Total training samples needed** | **0** | **1,000** | **-1,000** | |

### ⚠️ BLOCKING ISSUE: No Narrative Training Data

Before running on RunPod, you MUST collect narrative training data:

```bash
# Check if narrative logging is enabled
grep -r "NARRATIVE_LOG" apps/api/app/services/enhanced_narrative_service.py

# If not, the logging must be added (see Section 2.1)
```

### 2.1 How to Collect Narrative Training Data

**Step 1: Enable Narrative Logging**

Add to `apps/api/app/services/enhanced_narrative_service.py`:

```python
import os
import json
from datetime import datetime

NARRATIVE_LOG_PATH = "exports/narrative_training_log.jsonl"
NARRATIVE_LOG_ENABLED = os.getenv("NARRATIVE_LOG_ENABLED", "true").lower() == "true"

def _log_narrative(entity: str, section: str, prompt: str, output: str):
    """Log narrative generation for fine-tuning."""
    if not NARRATIVE_LOG_ENABLED:
        return

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "entity": entity,
        "section": section,
        "prompt": prompt,
        "output": output,
        "model": "gpt-4o-mini",
        "token_count": len(output.split()),
    }

    os.makedirs(os.path.dirname(NARRATIVE_LOG_PATH), exist_ok=True)
    with open(NARRATIVE_LOG_PATH, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
```

**Step 2: Generate Reports**

Generate ~50-100 intelligence reports to collect data:

```bash
# Generate reports for various companies
curl -X POST "http://localhost:8001/api/v1/intelligence" \
  -H "Content-Type: application/json" \
  -d '{"entity": "NVIDIA", "report_type": "full"}'

# Repeat for: AAPL, MSFT, GOOGL, AMZN, TSLA, META, etc.
```

**Step 3: Verify Data Collection**

```bash
# Check data is being logged
wc -l apps/api/exports/narrative_training_log.jsonl
# Target: 500+ records

# Check data format
head -1 apps/api/exports/narrative_training_log.jsonl | python -m json.tool
```

---

## 3. RunPod Account Setup

### 3.1 Create Account

1. Go to https://www.runpod.io/
2. Click "Sign Up"
3. Verify email
4. Add payment method (credit card required)

### 3.2 Add Credits

- Minimum recommended: $50 (covers ~10-20 hours of A100)
- For full training run: $100

### 3.3 Generate API Key

1. Go to Settings → API Keys
2. Click "Create API Key"
3. Save the key securely (you'll need it for programmatic access)

```bash
# Store in environment
export RUNPOD_API_KEY="your_key_here"
```

### 3.4 Verify Hugging Face Token

You need a Hugging Face token with access to Llama 3.1:

1. Go to https://huggingface.co/settings/tokens
2. Create token with "Read" access
3. Accept Llama 3.1 license at https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct

```bash
export HF_TOKEN="your_huggingface_token"
```

---

## 4. GPU Pod Configuration

### 4.1 Recommended GPU Selection

| Model | GPU Required | VRAM Needed | RunPod Instance | Cost/hr |
|-------|-------------|-------------|-----------------|---------|
| Llama 3.1 8B (LoRA) | A100 40GB | 35GB | RTX A6000 or A100 PCIe | $0.79-1.89 |
| Llama 3.1 8B (Full) | A100 80GB | 70GB | A100 80GB SXM | $2.49 |
| Qwen2.5 7B (LoRA) | A100 40GB | 30GB | RTX A6000 | $0.79 |

**Recommended:** A100 40GB PCIe ($1.89/hr) for LoRA fine-tuning

### 4.2 Create Pod via Web UI

1. Go to https://www.runpod.io/console/pods
2. Click "Deploy"
3. Select GPU: **A100 40GB PCIe** (or A6000 for budget option)
4. Select Template: **RunPod Pytorch 2.1**
5. Container Image: `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`
6. Volume: 100GB (for model + data)
7. Click "Deploy"

### 4.3 Create Pod via CLI (Alternative)

```bash
# Install runpodctl
pip install runpod

# Create pod
python -c "
import runpod
runpod.api_key = 'YOUR_RUNPOD_API_KEY'

pod = runpod.create_pod(
    name='narrative-training',
    image_name='runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04',
    gpu_type_id='NVIDIA A100 80GB PCIe',  # or 'NVIDIA RTX A6000'
    volume_in_gb=100,
    ports='8888/http,22/tcp',
    env={
        'HF_TOKEN': 'your_hf_token',
        'JUPYTER_PASSWORD': 'your_jupyter_password'
    }
)
print(f'Pod ID: {pod[\"id\"]}')
print(f'SSH: ssh root@{pod[\"machine\"][\"publicIp\"]} -p {pod[\"sshPorts\"][0][\"publicPort\"]}')
"
```

---

## 5. Environment Setup on Pod

### 5.1 Connect to Pod

```bash
# Via SSH (get IP and port from RunPod console)
ssh root@<POD_IP> -p <SSH_PORT>

# Or use Jupyter (open the pod's Jupyter URL)
```

### 5.2 Install Dependencies

```bash
# Update system
apt-get update && apt-get install -y git vim htop nvtop

# Create working directory
mkdir -p /workspace/narrative-training
cd /workspace/narrative-training

# Install Python packages
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers==4.42.0
pip install datasets==2.19.0
pip install peft==0.11.0
pip install accelerate==0.30.0
pip install bitsandbytes==0.43.0
pip install scipy
pip install trl==0.8.0
pip install wandb  # optional, for logging
```

### 5.3 Verify GPU Access

```bash
# Check CUDA
nvidia-smi

# Check PyTorch sees GPU
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0)}'); print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')"
```

Expected output:
```
CUDA available: True
GPU: NVIDIA A100-PCIE-40GB
VRAM: 40.0 GB
```

### 5.4 Login to Hugging Face

```bash
# Set token
export HF_TOKEN="your_huggingface_token"

# Or login interactively
huggingface-cli login
```

---

## 6. Data Upload to Pod

### 6.1 Prepare Data Locally

```bash
# On your local machine, create training data package
cd /path/to/Finance-Advanced-Research-Platform/apps/api

# Check data exists
ls -la exports/narrative_training_log.jsonl

# Create tarball of training data
tar -czvf narrative_training_data.tar.gz exports/
```

### 6.2 Upload to Pod

```bash
# Via SCP
scp -P <SSH_PORT> narrative_training_data.tar.gz root@<POD_IP>:/workspace/narrative-training/

# Or via rsync (faster for large files)
rsync -avz -e "ssh -p <SSH_PORT>" narrative_training_data.tar.gz root@<POD_IP>:/workspace/narrative-training/
```

### 6.3 Extract on Pod

```bash
# On the pod
cd /workspace/narrative-training
tar -xzvf narrative_training_data.tar.gz

# Verify
ls -la exports/
wc -l exports/narrative_training_log.jsonl
```

---

## 7. Training Script Configuration

### 7.1 Create Training Script

Create `/workspace/narrative-training/train.py`:

```python
#!/usr/bin/env python3
"""
Finance Narrative Model Fine-Tuning Script
Target: Fine-tune Llama 3.1 8B with LoRA for narrative generation
"""

import os
import json
import torch
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import Dataset
from trl import SFTTrainer

# ============================================================================
# CONFIGURATION - MODIFY THESE
# ============================================================================

@dataclass
class TrainingConfig:
    # Model
    base_model: str = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    output_dir: str = "/workspace/narrative-training/output/finance-narrative-v1"

    # Data
    train_data_path: str = "/workspace/narrative-training/exports/narrative_training_log.jsonl"
    max_seq_length: int = 2048

    # Training
    num_epochs: int = 3
    batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-5
    warmup_steps: int = 100

    # LoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: List[str] = None

    # Quantization (for memory efficiency)
    use_4bit: bool = True
    use_8bit: bool = False

    # Logging
    logging_steps: int = 10
    save_steps: int = 500
    eval_steps: int = 500

    def __post_init__(self):
        if self.lora_target_modules is None:
            self.lora_target_modules = [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"
            ]


config = TrainingConfig()

# ============================================================================
# DATA LOADING
# ============================================================================

def load_training_data(path: str) -> Dataset:
    """Load JSONL training data and convert to Dataset."""

    print(f"Loading training data from {path}...")

    examples = []
    with open(path) as f:
        for line in f:
            entry = json.loads(line)

            # Format as instruction-following conversation
            # Llama 3.1 uses special tokens for chat format
            text = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

You are a financial analyst writing professional investment narratives. Generate clear, accurate, and well-structured financial analysis.<|eot_id|><|start_header_id|>user<|end_header_id|>

{entry['prompt']}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{entry['output']}<|eot_id|>"""

            examples.append({"text": text, "entity": entry.get("entity", ""), "section": entry.get("section", "")})

    print(f"Loaded {len(examples)} training examples")

    if len(examples) < 100:
        print("⚠️  WARNING: Less than 100 training examples. Consider collecting more data!")

    return Dataset.from_list(examples)


# ============================================================================
# MODEL SETUP
# ============================================================================

def setup_model_and_tokenizer(config: TrainingConfig):
    """Load base model with quantization and prepare for LoRA."""

    print(f"Loading base model: {config.base_model}")

    # Quantization config for memory efficiency
    if config.use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    elif config.use_8bit:
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)
    else:
        bnb_config = None

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(config.base_model)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        config.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )

    # Prepare for k-bit training
    if config.use_4bit or config.use_8bit:
        model = prepare_model_for_kbit_training(model)

    # LoRA configuration
    lora_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        target_modules=config.lora_target_modules,
        lora_dropout=config.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # Apply LoRA
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model, tokenizer


# ============================================================================
# TRAINING
# ============================================================================

def train(config: TrainingConfig):
    """Main training function."""

    print("=" * 60)
    print("Finance Narrative Model Training")
    print("=" * 60)
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"Base model: {config.base_model}")
    print(f"Output dir: {config.output_dir}")
    print("=" * 60)

    # Load data
    dataset = load_training_data(config.train_data_path)

    # Split into train/eval
    dataset = dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = dataset["train"]
    eval_dataset = dataset["test"]

    print(f"Train samples: {len(train_dataset)}")
    print(f"Eval samples: {len(eval_dataset)}")

    # Load model
    model, tokenizer = setup_model_and_tokenizer(config)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.num_epochs,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_steps=config.warmup_steps,
        logging_steps=config.logging_steps,
        save_steps=config.save_steps,
        eval_steps=config.eval_steps,
        evaluation_strategy="steps",
        save_total_limit=3,
        load_best_model_at_end=True,
        fp16=False,
        bf16=True,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        lr_scheduler_type="cosine",
        report_to="none",  # or "wandb" if configured
    )

    # SFT Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        args=training_args,
        dataset_text_field="text",
        max_seq_length=config.max_seq_length,
        packing=False,
    )

    # Train
    print("\nStarting training...")
    trainer.train()

    # Save final model
    print(f"\nSaving model to {config.output_dir}")
    trainer.save_model(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)

    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"End time: {datetime.now().isoformat()}")
    print(f"Model saved to: {config.output_dir}")
    print("=" * 60)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Verify CUDA
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available! Make sure you're running on a GPU pod.")

    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Check data exists
    if not os.path.exists(config.train_data_path):
        raise FileNotFoundError(
            f"Training data not found at {config.train_data_path}\n"
            "Please upload narrative_training_log.jsonl first!"
        )

    # Start training
    train(config)
```

### 7.2 Training Configuration Options

Modify the `TrainingConfig` class based on your needs:

| Parameter | Default | Description | Adjust If |
|-----------|---------|-------------|-----------|
| `num_epochs` | 3 | Training epochs | Increase for more data, decrease if overfitting |
| `batch_size` | 4 | Per-device batch | Decrease if OOM, increase if GPU underutilized |
| `learning_rate` | 2e-5 | Learning rate | Lower if unstable, higher if slow convergence |
| `lora_r` | 16 | LoRA rank | Higher = more capacity, more VRAM |
| `lora_alpha` | 32 | LoRA alpha | Usually 2x lora_r |
| `use_4bit` | True | 4-bit quantization | Set False for better quality, more VRAM |
| `max_seq_length` | 2048 | Max sequence length | Match your narrative length distribution |

---

## 8. Running Training

### 8.1 Start Training

```bash
cd /workspace/narrative-training

# Optional: Use tmux to persist session
tmux new -s training

# Run training
python train.py 2>&1 | tee training.log
```

### 8.2 Monitor Training

```bash
# In another terminal/tmux window

# GPU utilization
watch -n 1 nvidia-smi

# Or use nvtop for visual monitoring
nvtop

# Check training log
tail -f /workspace/narrative-training/training.log
```

### 8.3 Expected Training Time

| Data Size | GPU | Estimated Time |
|-----------|-----|----------------|
| 500 samples | A100 40GB | 1-2 hours |
| 1,000 samples | A100 40GB | 2-4 hours |
| 5,000 samples | A100 40GB | 8-12 hours |

---

## 9. Model Evaluation

### 9.1 Quick Inference Test

After training, test the model:

```python
# test_inference.py
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

MODEL_PATH = "/workspace/narrative-training/output/finance-narrative-v1"

# Load model
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Test generation
test_prompt = """Generate an executive summary for NVIDIA Corporation based on the following data:
- Q3 2024 Revenue: $18.1B (up 206% YoY)
- Data Center Revenue: $14.5B (up 279% YoY)
- Gross Margin: 74.0%
- EPS: $4.02 (beat estimates by 15%)"""

messages = [
    {"role": "system", "content": "You are a financial analyst writing professional investment narratives."},
    {"role": "user", "content": test_prompt},
]

input_ids = tokenizer.apply_chat_template(messages, return_tensors="pt").to("cuda")

output = model.generate(
    input_ids,
    max_new_tokens=500,
    temperature=0.7,
    do_sample=True,
)

response = tokenizer.decode(output[0], skip_special_tokens=True)
print(response)
```

### 9.2 Comparison Evaluation

See `docs/AI_TRAINING_PHASES_2_AND_4_PLAN.md` Task 4.4 for full A/B evaluation framework using LLM-as-judge.

---

## 10. Model Download & Deployment

### 10.1 Download Model from Pod

```bash
# On local machine
scp -P <SSH_PORT> -r root@<POD_IP>:/workspace/narrative-training/output/finance-narrative-v1 ./models/

# Or compress first on pod
ssh root@<POD_IP> -p <SSH_PORT> "cd /workspace/narrative-training/output && tar -czvf finance-narrative-v1.tar.gz finance-narrative-v1"
scp -P <SSH_PORT> root@<POD_IP>:/workspace/narrative-training/output/finance-narrative-v1.tar.gz ./models/
```

### 10.2 Deploy to Production

1. Copy model to production server:
```bash
scp -r ./models/finance-narrative-v1 production:/path/to/models/
```

2. Update environment variables:
```bash
export NARRATIVE_MODEL=local
export NARRATIVE_LOCAL_PATH=/path/to/models/finance-narrative-v1
```

3. Restart API service

---

## 11. Common Errors & Solutions

### 11.1 Out of Memory (OOM)

**Error:** `CUDA out of memory`

**Solutions:**
1. Reduce `batch_size` (try 2 or 1)
2. Increase `gradient_accumulation_steps` to compensate
3. Enable gradient checkpointing (already enabled in script)
4. Use smaller `max_seq_length`
5. Switch to 4-bit quantization if using 8-bit

### 11.2 Model Not Found

**Error:** `OSError: meta-llama/Meta-Llama-3.1-8B-Instruct is not a valid model identifier`

**Solutions:**
1. Verify HF_TOKEN is set: `echo $HF_TOKEN`
2. Accept Llama 3.1 license at https://huggingface.co/meta-llama/Meta-Llama-3.1-8B-Instruct
3. Login: `huggingface-cli login`

### 11.3 Training Loss Not Decreasing

**Solutions:**
1. Check data quality - bad data = bad training
2. Reduce learning rate (try 1e-5)
3. Check for data leakage between train/eval
4. Ensure prompts are properly formatted

### 11.4 Pod Disconnects Mid-Training

**Solutions:**
1. Use `tmux` or `screen` to persist sessions
2. Enable checkpointing (every 500 steps by default)
3. Can resume from checkpoint: `trainer.train(resume_from_checkpoint=True)`

### 11.5 Slow Training

**Solutions:**
1. Enable `bf16=True` (already in script)
2. Use `paged_adamw_8bit` optimizer (already set)
3. Enable `packing=True` for shorter sequences
4. Reduce `logging_steps` to avoid frequent disk writes

### 11.6 ImportError: No module named 'bitsandbytes'

**Solution:**
```bash
pip install bitsandbytes
# If still fails:
pip install bitsandbytes --force-reinstall
```

---

## 12. Cost Estimation

### RunPod Pricing (as of Aug 2026)

| GPU | $/hour | Est. Training Time | Total Cost |
|-----|--------|-------------------|------------|
| RTX A6000 (48GB) | $0.79 | 4-6 hours | $3-5 |
| A100 40GB PCIe | $1.89 | 2-4 hours | $4-8 |
| A100 80GB SXM | $2.49 | 2-3 hours | $5-8 |

**Recommended budget:** $10-20 for initial training + iterations

### Cost Optimization Tips

1. **Develop locally first** - debug with small data subset on CPU
2. **Start with A6000** - cheaper, sufficient for LoRA
3. **Stop pod when not training** - charges continue while running
4. **Use spot instances** - 50-70% cheaper (may terminate unexpectedly)

---

## 13. Checklist Before Training

### Pre-Training Checklist

- [ ] **Data Collection Complete**
  - [ ] `narrative_training_log.jsonl` has 500+ records
  - [ ] Data format verified (JSONL with prompt/output fields)
  - [ ] No PII or sensitive data in training set

- [ ] **RunPod Setup**
  - [ ] RunPod account created and funded ($50+)
  - [ ] API key saved
  - [ ] Pod deployed with A100 40GB

- [ ] **Hugging Face Access**
  - [ ] HF account with token
  - [ ] Llama 3.1 license accepted
  - [ ] Token tested: `huggingface-cli whoami`

- [ ] **Environment Verified**
  - [ ] CUDA working: `nvidia-smi`
  - [ ] PyTorch with CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
  - [ ] All packages installed

- [ ] **Data Uploaded**
  - [ ] Training data on pod at expected path
  - [ ] Data readable: `head exports/narrative_training_log.jsonl`

- [ ] **Training Script Ready**
  - [ ] `train.py` uploaded to pod
  - [ ] Config parameters reviewed and adjusted
  - [ ] Output directory exists and is writable

### Post-Training Checklist

- [ ] Training completed without errors
- [ ] Final loss is reasonable (<0.5 for LoRA)
- [ ] Model saved to output directory
- [ ] Quick inference test passed
- [ ] Model downloaded from pod
- [ ] Pod terminated to stop billing

---

## Appendix A: Alternative Models

If Llama 3.1 8B is too large or restricted:

| Model | Size | VRAM Needed | License | Notes |
|-------|------|-------------|---------|-------|
| Qwen2.5-7B-Instruct | 7B | 30GB | Apache 2.0 | No license required |
| Mistral-7B-Instruct-v0.3 | 7B | 28GB | Apache 2.0 | Fast, good quality |
| Llama 3.2 3B | 3B | 12GB | Llama | Smaller, faster |
| Phi-3-medium | 14B | 40GB | MIT | Microsoft, very capable |

To switch models, just change `base_model` in the config:
```python
base_model: str = "Qwen/Qwen2.5-7B-Instruct"
```

---

## Appendix B: Data Format Reference

### narrative_training_log.jsonl

Each line should be valid JSON with these fields:

```json
{
  "timestamp": "2026-08-21T10:30:00.000000+00:00",
  "entity": "NVIDIA",
  "section": "executive_summary",
  "prompt": "Generate an executive summary for NVIDIA based on: Revenue $18.1B...",
  "output": "NVIDIA delivered exceptional Q3 2024 results...",
  "model": "gpt-4o-mini",
  "token_count": 245
}
```

### Minimum fields required:
- `prompt`: The input text (what user/system asked for)
- `output`: The generated narrative (what model should produce)

### Optional but helpful:
- `entity`: Company/ticker being analyzed
- `section`: Type of narrative (summary, risk, thesis, etc.)
- `timestamp`: When generated (for filtering recent data)

---

*Last updated: 21 August 2026*
