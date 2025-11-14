# Execution Plan - Quick Summary

**Full details:** See EXECUTION_PLAN.md

---

## Goal
Generate 250,000 Wikipedia article embeddings using 16 GPUs across 2 clusters

---

## Pre-Flight (Must Complete First)

```bash
cd /Users/jmanning/mapper.io

# 1. Verify local files exist
ls -lh wikipedia.pkl                    # Should be 752MB
ls .credentials/*.credentials           # tensor01, tensor02
ls .credentials/hf.token                # HuggingFace token

# 2. Test connectivity
python3 -c "import paramiko; print('✓ paramiko OK')"

# 3. Run pre-flight summary
./notes/EXECUTION_PLAN.md  # See "Pre-flight Summary Check" section
```

**STOP if any checks fail. Fix issues before launching.**

---

## Launch Procedure

### Step 1: Launch Workers (2-3 min)
```bash
./launch_distributed.sh --clusters "tensor01 tensor02"
```

**Expected:** 16 workers launch (8 per cluster)

### Step 2: Start Monitoring (continuous)
```bash
python3 monitor_clusters.py --interval 30
```

**Expected:** Progress updates every 30 seconds, ~500-1000 items/sec combined

### Step 3: Wait for Completion (3-10 min)
Monitor will show:
```
✓ ALL WORKERS COMPLETE!
```

---

## Download & Validate

### Step 1: Download (5-10 min)
```bash
python3 sync_and_merge_embeddings.py --sync-only
```

**Expected:** 16 files downloaded (~150MB each, 2.4GB total)

### Step 2: Merge (2-3 min)
```bash
python3 sync_and_merge_embeddings.py --merge-only
```

**Expected:** `embeddings/wikipedia_merged.pkl` created (1.9GB)

### Step 3: Validate
```bash
# Run final check script from EXECUTION_PLAN.md
# Look for: "✓✓✓ ALL CHECKS PASSED ✓✓✓"
```

---

## Success Criteria

✓ File exists: `embeddings/wikipedia_merged.pkl`
✓ File size: ~1.9 GB
✓ Embeddings: 250,000 articles × 768 dimensions
✓ No NaN or Inf values
✓ Article metadata complete

---

## If Something Goes Wrong

### Worker Crashes
```bash
# SSH to cluster
ssh user@tensor01

# Check logs
tail -100 ~/mapper_embeddings/logs/gpu0.log

# Restart worker
export CUDA_VISIBLE_DEVICES=0
screen -dmS mapper_gpu0 bash -c "cd ~/mapper_embeddings && python generate_embeddings_gpu.py --cluster 0 --gpu 0 --total-clusters 2 2>&1 | tee -a logs/gpu0.log"
```

### Download Fails
```bash
# Retry (skips already downloaded files)
python3 sync_and_merge_embeddings.py --sync-only
```

### Merge Fails
```bash
# Check which file has issues
python3 << 'EOF'
import pickle
import numpy as np
from pathlib import Path

for f in sorted(Path('embeddings').glob('cluster*.pkl')):
    data = pickle.load(open(f, 'rb'))
    embeddings = data['embeddings']
    has_nan = np.isnan(embeddings).any()
    print(f"{f.name}: NaN={has_nan}, shape={embeddings.shape}")
EOF

# Re-download problematic file, then retry merge
```

### Nuclear Option (Start Over)
```bash
# Kill everything
ssh user@tensor01 "killall python3; screen -wipe"
ssh user@tensor02 "killall python3; screen -wipe"

# Re-launch
./launch_distributed.sh --clusters "tensor01 tensor02"
```

---

## Timeline

| Phase | Duration |
|-------|----------|
| Pre-flight | 5-10 min |
| Launch | 2-3 min |
| Generation | 3-10 min |
| Download | 5-10 min |
| Merge | 2-3 min |
| **Total** | **~20-35 min** |

---

## Emergency Commands

**Stop all workers:**
```bash
ssh user@tensor01 "killall python3; screen -wipe"
ssh user@tensor02 "killall python3; screen -wipe"
```

**Check status:**
```bash
ssh user@tensor01 "screen -ls; tail ~/mapper_embeddings/logs/gpu0.log"
```

**Quick progress check:**
```bash
ssh user@tensor01 "cat ~/mapper_embeddings/embeddings/progress.json | python3 -m json.tool"
```

---

## Next Steps After Success

1. Generate UMAP projections
2. Build knowledge map visualization
3. Deploy interactive demo

---

## Files Created

- `embeddings/wikipedia_merged.pkl` - Main output (1.9GB)
- `embeddings/cluster*.pkl` - Individual GPU files (can delete after merge)
- `embeddings/backups/wikipedia_merged_*.pkl` - Timestamped backup

---

**For complete details, troubleshooting, and recovery procedures:**
→ See `/Users/jmanning/mapper.io/notes/EXECUTION_PLAN.md`
