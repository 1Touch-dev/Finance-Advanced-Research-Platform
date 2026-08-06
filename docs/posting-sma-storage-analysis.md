# Server Storage Analysis: posting-sma

**Date:** August 6, 2026
**Server:** posting-sma (3.238.205.150)
**Instance Type:** EC2 with NVMe Instance Storage

---

## Current Disk Status

| Filesystem | Size | Used | Available | Use% | Mount Point |
|------------|------|------|-----------|------|-------------|
| /dev/root (EBS) | 77G | 66G | 11G | 87% | / |
| /dev/nvme1n1 (Instance) | 115G | 24K | 109G | 0% | /mnt/instance-storage |

**Total Available: 11GB + 109GB = 120GB free**

---

## Storage Breakdown

### What's Using Space on EBS

| Directory | Size | Owner/Purpose |
|-----------|------|---------------|
| Social_Media_Automations_Backend | 13GB | Main application |
| ├── venv | 7.4GB | Python virtual environment |
| ├── models/gguf | 3.7GB | GGUF AI models |
| ├── .git | 1.5GB | Git history |
| └── logs | 189MB | Application logs |
| .cache | 12GB | System caches |
| ├── pypoetry/virtualenvs | 7.7GB | Active Python env (needed) |
| └── huggingface | 4GB | Model cache |
| kohya_ss | 9.9GB | Ankur's LoRA training framework |
| ComfyUI | 8.5GB | Ankur's Image generation UI |
| snap packages | 8.4GB | System snap packages |
| mlx | 4.7GB | Ankur's remote desktop tool |
| /var | 4.4GB | System files |
| lora_training | 228MB | Ankur's LoRA training |

---

## Instance Storage Setup (Completed)

### What Was Done

1. ✅ Formatted `/dev/nvme1n1` with ext4 filesystem (label: `instance-storage`)
2. ✅ Mounted at `/mnt/instance-storage`
3. ✅ Owned by `ubuntu` user (no sudo needed to write)
4. ✅ Added to `/etc/fstab` with `nofail` option (auto-mounts on reboot)
5. ✅ Write test passed

### Directory Structure Created

```
/mnt/instance-storage/
├── models/
│   ├── sd-checkpoints/      # SD 1.5, SDXL, future base models
│   └── comfyui-checkpoints/ # Symlinked from ComfyUI
├── lora-temp/               # Scratch files during training
├── comfyui-output/          # Test/disposable images
└── docker-cache/            # Docker build cache
```

### Important Warning

> **This is EPHEMERAL storage!** Data will be lost if the instance is stopped or terminated.

| Event | What Happens to Data |
|-------|---------------------|
| Instance **Stop** | ❌ DATA LOST |
| Instance **Terminate** | ❌ DATA LOST |
| Instance **Reboot** | ✅ Data retained |
| Hardware Failure | ❌ DATA LOST |

---

## Storage Plan

### Move to Instance Storage (Ephemeral, Re-downloadable)

| What | Current Location | Size | Action |
|------|------------------|------|--------|
| SD 1.5 Base Model | `/home/ubuntu/kohya_ss/models/v1-5-pruned-emaonly.ckpt` | 4GB | Move + symlink |
| ComfyUI Checkpoints | `/home/ubuntu/ComfyUI/models/checkpoints/` | ~0 (empty now) | Symlink dir for future models |
| ComfyUI Test Outputs | `/home/ubuntu/ComfyUI/output/` | 30MB | Move + symlink |
| LoRA Training Temp | (create new) | varies | New dir for scratch files |
| Docker Build Cache | `/var/lib/docker` | ~0 now | Configure Docker daemon |

### Keep on EBS (Persistent, Irreplaceable)

| What | Location | Size | Reason |
|------|----------|------|--------|
| Trained LoRA files | `/home/ubuntu/lora_training/loras/` | varies | Your trained models |
| Curated Datasets | `/home/ubuntu/lora_training/datasets/` | varies | Training data |
| Raw Images | `/home/ubuntu/lora_training/raw_images/` | varies | Source images |
| Training Configs | `/home/ubuntu/lora_training/config/` | small | Your settings |

---

## Running Services

| Service | Memory | Description |
|---------|--------|-------------|
| Celery image worker | 430MB | Image generation queue |
| SD API (port 8002) | 162MB | Stable Diffusion API |
| Main API (port 8000) | 53MB | FastAPI application |
| GGUF API (port 8001) | 15MB | GGUF model API |
| Celery campaign worker | 37MB | Campaign management |
| OCR celery worker | 16MB | OCR processing |
| mlx desktop | 57MB | Remote desktop tool |
| Xvfb | 23MB | Virtual display (headless browser) |
| Docker daemon | 43MB | Container runtime |

---

## Cleanup Opportunities (~4-5GB recoverable)

| Item | Size | Action |
|------|------|--------|
| Old disabled snaps | ~2.8GB | `sudo snap set system refresh.retain=2` then cleanup |
| Old worker logs | ~150MB | Delete old `worker_campaign_*.log` files |
| Git repo cleanup | ~500MB | Run `git gc --aggressive` |
| Empty log files | ~0 | 50+ empty log files can be deleted |

---

## EBS Increase Recommendation

### **Verdict: NO EBS increase needed right now**

#### Reasoning:

| Storage | Available |
|---------|-----------|
| EBS (persistent) | 11GB free + 4GB (after moving base model) = ~15GB |
| Instance storage | 109GB |
| After cleanup | +3GB more on EBS |
| **Total usable** | **~125GB** |

#### What Actually Needs EBS (Persistent)?

| Item | Size | Growth |
|------|------|--------|
| Main app + venv | ~13GB | Slow |
| Trained LoRAs | ~100MB each | Occasional |
| Curated datasets | ~200MB | Occasional |
| System/snaps | ~12GB | Minimal |

**~15-18GB free on EBS is enough for irreplaceable data.**

#### Everything Heavy & Re-downloadable Goes to Instance Storage:
- Base models (4-12GB each) → Instance storage ✓
- Test outputs → Instance storage ✓
- Training scratch → Instance storage ✓

#### Revisit EBS Increase Only If:
- You accumulate 10+ trained LoRAs (unlikely to fill 15GB)
- You need large persistent datasets that can't be re-downloaded

---

## Pending Setup Tasks

- [ ] Move kohya_ss base models to instance storage + symlink
- [ ] Set up ComfyUI checkpoints on instance storage + symlink
- [ ] Move ComfyUI output to instance storage + symlink
- [ ] Set up Docker to use instance storage for build cache
- [ ] Create temp directory for LoRA training scratch files
- [ ] Verify all symlinks and show final setup

---

## How to Use Instance Storage

```bash
# Store files directly
cp large_file.zip /mnt/instance-storage/

# Create subdirectories
mkdir /mnt/instance-storage/models
mkdir /mnt/instance-storage/outputs

# Check disk space
df -h /mnt/instance-storage
```

---

## fstab Entry

```
# Instance storage - ephemeral, data lost on stop/terminate
/dev/nvme1n1 /mnt/instance-storage ext4 defaults,nofail 0 2
```

The `nofail` option ensures the server boots even if the instance storage disk is not present.
