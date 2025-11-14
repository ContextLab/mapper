# Troubleshooting Guide - Wikipedia Embedding Generation

Quick reference for resolving common issues during execution.

---

## Table of Contents

1. [Pre-Flight Issues](#pre-flight-issues)
2. [Launch Issues](#launch-issues)
3. [Runtime Issues](#runtime-issues)
4. [Download Issues](#download-issues)
5. [Merge Issues](#merge-issues)
6. [Validation Issues](#validation-issues)

---

## Pre-Flight Issues

### Issue: "wikipedia.pkl not found"

**Symptoms:** File doesn't exist locally

**Diagnosis:**
```bash
ls -lh wikipedia.pkl
# Output: No such file or directory
```

**Solution:**
- BLOCKER: Must obtain wikipedia.pkl before proceeding
- Check if file exists elsewhere: `find ~ -name "wikipedia.pkl" 2>/dev/null`
- Download from source or regenerate
- Verify file: `python3 -c "import pickle; len(pickle.load(open('wikipedia.pkl','rb')))"`
- Should output: 250000

---

### Issue: "Credentials file invalid"

**Symptoms:** JSON parsing error when loading credentials

**Diagnosis:**
```bash
python3 -c "import json; json.load(open('.credentials/tensor01.credentials'))"
# Output: JSONDecodeError
```

**Solution:**
```bash
# Check file format
cat .credentials/tensor01.credentials

# Should be valid JSON:
# {"address": "hostname", "username": "user", "password": "pass"}

# Fix formatting if needed
# Ensure no trailing commas, proper quotes, etc.
```

---

### Issue: "Cannot connect to cluster"

**Symptoms:** SSH connection fails

**Diagnosis:**
```bash
ssh user@tensor01
# Output: Connection refused / timeout
```

**Solutions:**

**Option 1: Network Issue**
```bash
# Test connectivity
ping tensor01.example.com

# If ping fails, check:
# - VPN connection
# - Firewall settings
# - Hostname resolution: nslookup tensor01.example.com
```

**Option 2: Wrong Credentials**
```bash
# Verify credentials
cat .credentials/tensor01.credentials

# Test manually
ssh username@address
# If password prompt fails, credentials are wrong

# Update .credentials file with correct info
```

**Option 3: SSH Key Required**
```bash
# If cluster requires SSH key instead of password:
# Generate key
ssh-keygen -t rsa -f ~/.ssh/tensor_key

# Copy to cluster
ssh-copy-id -i ~/.ssh/tensor_key user@tensor01

# Update launch script to use key instead of password
# (Modify launch_distributed.sh to use ssh-agent)
```

---

### Issue: "paramiko not installed"

**Symptoms:** ImportError when running scripts

**Diagnosis:**
```bash
python3 -c "import paramiko"
# Output: ModuleNotFoundError
```

**Solution:**
```bash
pip install paramiko numpy

# If using conda:
conda install -c conda-forge paramiko numpy

# Verify installation
python3 -c "import paramiko; print(paramiko.__version__)"
```

---

## Launch Issues

### Issue: "Workers not starting"

**Symptoms:** launch_distributed.sh completes but no workers running

**Diagnosis:**
```bash
ssh user@tensor01
screen -ls
# Output: No Sockets found
```

**Solutions:**

**Check conda environment:**
```bash
ssh user@tensor01
conda env list | grep mapper_gpu
# If not found, environment creation failed

# Check logs from launch
cat ~/mapper_embeddings/logs/gpu0.log
```

**Recreate environment manually:**
```bash
ssh user@tensor01
cd ~/mapper_embeddings

# Remove old environment
conda env remove -n mapper_gpu -y

# Create fresh
conda create -y -n mapper_gpu python=3.10
conda activate mapper_gpu

# Install packages
pip install torch sentence-transformers numpy scikit-learn huggingface_hub

# Test
python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

**Restart workers:**
```bash
# Exit SSH
exit

# Re-run launch
./launch_distributed.sh --clusters "tensor01"
```

---

### Issue: "Only X/8 workers running"

**Symptoms:** Some workers failed to start

**Diagnosis:**
```bash
ssh user@tensor01
screen -ls | grep mapper_gpu | wc -l
# Output: 5 (expected 8)
```

**Solution:**
```bash
# Check which GPUs are missing
screen -ls | grep mapper_gpu
# Output shows: mapper_gpu0, mapper_gpu1, mapper_gpu4, mapper_gpu6, mapper_gpu7
# Missing: gpu2, gpu3, gpu5

# Check logs for failed workers
tail -50 ~/mapper_embeddings/logs/gpu2.log
tail -50 ~/mapper_embeddings/logs/gpu3.log
tail -50 ~/mapper_embeddings/logs/gpu5.log

# Common causes and fixes:

# Cause 1: GPU in use
nvidia-smi | grep python
# Kill other processes if found
kill -9 [PID]

# Cause 2: CUDA error
# GPU may have crashed, reset it (requires sudo)
sudo nvidia-smi --gpu-reset -i 2

# Cause 3: Permission denied
ls -la ~/mapper_embeddings/logs/
# Ensure logs directory is writable
chmod 755 ~/mapper_embeddings/logs/

# Restart failed workers
for gpu in 2 3 5; do
    export CUDA_VISIBLE_DEVICES=$gpu
    screen -dmS mapper_gpu$gpu bash -c "cd ~/mapper_embeddings && python generate_embeddings_gpu.py --cluster 0 --gpu $gpu --total-clusters 2 2>&1 | tee -a logs/gpu${gpu}.log"
done

# Verify
screen -ls | grep mapper_gpu | wc -l
# Should output: 8
```

---

### Issue: "Environment creation failed"

**Symptoms:** Launch script shows conda errors

**Diagnosis:**
```bash
# Error in launch output:
# "CondaError: Could not create environment"
```

**Solutions:**

**Check disk space:**
```bash
ssh user@tensor01
df -h ~
# If < 2GB free, clean up
```

**Check conda version:**
```bash
conda --version
# If too old, update
conda update conda
```

**Use system Python instead:**
```bash
# Edit generate_embeddings_gpu.py launch to use system python
ssh user@tensor01

# Install packages system-wide
pip3 install --user torch sentence-transformers numpy

# Modify launch script to use python3 instead of conda
# (Edit ~/mapper_embeddings/launch script)
```

---

## Runtime Issues

### Issue: "Worker stuck at 0 items/sec"

**Symptoms:** Worker appears in progress but not making progress

**Diagnosis:**
```bash
# Monitor shows:
# cluster0_gpu3: 150 items @ 0.0 items/sec (stuck for 5+ min)
```

**Solutions:**

**Attach to worker and check:**
```bash
ssh user@tensor01
screen -r mapper_gpu3
# Watch for 30 seconds
# Press Ctrl+A, D to detach

# If frozen (no output), worker is hung
```

**Kill and restart:**
```bash
# Kill screen session
screen -S mapper_gpu3 -X quit

# Check for hung Python process
ps aux | grep "gpu 3" | grep python
# Kill if found
kill -9 [PID]

# Restart worker (will resume from checkpoint)
cd ~/mapper_embeddings
export CUDA_VISIBLE_DEVICES=3
screen -dmS mapper_gpu3 bash -c "python generate_embeddings_gpu.py --cluster 0 --gpu 3 --total-clusters 2 2>&1 | tee -a logs/gpu3.log"

# Monitor for 2 minutes to verify it's working
tail -f logs/gpu3.log
# Press Ctrl+C to exit
```

---

### Issue: "CUDA out of memory"

**Symptoms:** Worker crashes with OOM error

**Diagnosis:**
```bash
ssh user@tensor01
tail -100 ~/mapper_embeddings/logs/gpu4.log
# Output: RuntimeError: CUDA out of memory
```

**Solutions:**

**Option 1: Reduce batch size**
```bash
# Edit generate_embeddings_gpu.py locally
# Line ~125: batch_size=32
# Change to: batch_size=16

# Re-upload script
scp generate_embeddings_gpu.py user@tensor01:~/mapper_embeddings/

# Restart worker
ssh user@tensor01
screen -S mapper_gpu4 -X quit
cd ~/mapper_embeddings
export CUDA_VISIBLE_DEVICES=4
screen -dmS mapper_gpu4 bash -c "python generate_embeddings_gpu.py --cluster 0 --gpu 4 --total-clusters 2 2>&1 | tee -a logs/gpu4.log"
```

**Option 2: Free GPU memory**
```bash
# Check what's using GPU
nvidia-smi

# Kill other processes
kill -9 [PID]

# Reset GPU if needed
sudo nvidia-smi --gpu-reset -i 4

# Restart worker
```

---

### Issue: "Model download timeout"

**Symptoms:** Worker stuck at "Loading model..."

**Diagnosis:**
```bash
ssh user@tensor01
tail -50 ~/mapper_embeddings/logs/gpu0.log
# Shows: Downloading model...
# No progress for 5+ minutes
```

**Solutions:**

**Pre-download model:**
```bash
ssh user@tensor01
cd ~/mapper_embeddings
conda activate mapper_gpu

# Download manually
python3 << 'EOF'
from sentence_transformers import SentenceTransformer
import os

# Set HF token if needed
token_file = os.path.expanduser('~/.credentials/hf.token')
if os.path.exists(token_file):
    with open(token_file) as f:
        token = f.read().strip()
    from huggingface_hub import login
    login(token=token)

print("Downloading model to cache...")
model = SentenceTransformer('google/embeddinggemma-300m')
print("✓ Model cached successfully")
print(f"Cache location: {model.cache_folder}")
EOF

# Model is now cached, workers will use cached version
# Restart workers
exit
./launch_distributed.sh --clusters "tensor01"
```

---

### Issue: "Worker disappeared"

**Symptoms:** Worker was in progress, now missing from monitor

**Diagnosis:**
```bash
ssh user@tensor01
screen -ls | grep mapper_gpu3
# Output: No screen session found
```

**Solutions:**

**Check if crashed:**
```bash
tail -100 ~/mapper_embeddings/logs/gpu3.log
# Look for error at end:
# - Segmentation fault
# - CUDA error
# - Python exception
```

**Restart from checkpoint:**
```bash
# Check if checkpoint exists
ls -lh ~/mapper_embeddings/embeddings/cluster0_gpu3_checkpoint_*.pkl
# If exists, worker can resume

cd ~/mapper_embeddings
export CUDA_VISIBLE_DEVICES=3
screen -dmS mapper_gpu3 bash -c "python generate_embeddings_gpu.py --cluster 0 --gpu 3 --total-clusters 2 2>&1 | tee -a logs/gpu3_restart.log"

# Monitor restart
tail -f logs/gpu3_restart.log
# Should show "Loading checkpoint..." if resuming
```

---

### Issue: "All workers slow (< 20 items/sec)"

**Symptoms:** All workers progressing but very slowly

**Diagnosis:**
```bash
ssh user@tensor01
nvidia-smi
# Check GPU utilization
```

**Possible Causes:**

**Cause 1: CPU bottleneck**
```bash
# Check CPU usage
top
# If CPU at 100%, bottleneck is data preprocessing

# Solution: Reduce batch size (counterintuitive but can help)
# Or ensure data is on fast SSD
```

**Cause 2: Network I/O**
```bash
# Check if reading from network mount
df -h ~/mapper_embeddings
# Ensure wikipedia.pkl is on local disk

# If on network mount, copy to local
cp ~/mapper_embeddings/wikipedia.pkl /tmp/wikipedia.pkl
# Update script to use /tmp/wikipedia.pkl
```

**Cause 3: Other jobs running**
```bash
# Check for other processes
nvidia-smi
ps aux | grep python

# If found, coordinate with other users
# Or wait for their jobs to complete
```

---

## Download Issues

### Issue: "Connection timeout during download"

**Symptoms:** sync script fails partway through download

**Diagnosis:**
```bash
python3 sync_and_merge_embeddings.py --sync-only
# Output: TimeoutError after downloading 5/16 files
```

**Solution:**
```bash
# Retry (script will skip already downloaded files)
python3 sync_and_merge_embeddings.py --sync-only

# Check which files are missing
ls embeddings/cluster*.pkl | wc -l
# If still < 16, manually download missing files

# Manual download example:
scp user@tensor01:~/mapper_embeddings/embeddings/cluster0_gpu5.pkl embeddings/

# Retry sync
python3 sync_and_merge_embeddings.py --sync-only
```

---

### Issue: "Downloaded file is corrupted"

**Symptoms:** File size is wrong or can't be loaded

**Diagnosis:**
```bash
ls -lh embeddings/cluster0_gpu3.pkl
# Output: 1.2K (should be ~150MB)

# Or
python3 -c "import pickle; pickle.load(open('embeddings/cluster0_gpu3.pkl', 'rb'))"
# Output: UnpicklingError
```

**Solution:**
```bash
# Delete corrupted file
rm embeddings/cluster0_gpu3.pkl

# Re-download
python3 sync_and_merge_embeddings.py --sync-only

# Or manual download:
scp user@tensor01:~/mapper_embeddings/embeddings/cluster0_gpu3.pkl embeddings/

# Verify size
ls -lh embeddings/cluster0_gpu3.pkl
# Should be 100-200MB
```

---

### Issue: "Some files not found on remote"

**Symptoms:** Remote cluster doesn't have all files

**Diagnosis:**
```bash
ssh user@tensor01 "ls ~/mapper_embeddings/embeddings/cluster*.pkl | wc -l"
# Output: 6 (expected 8)
```

**Solution:**
```bash
# Check which workers completed
ssh user@tensor01 "cat ~/mapper_embeddings/embeddings/progress.json | python3 -m json.tool"

# Look for workers with items_processed > 0
# But missing final .pkl file

# Check logs for failed workers
ssh user@tensor01 "tail -100 ~/mapper_embeddings/logs/gpu5.log"

# If worker completed but file not saved:
# Re-run that specific worker
ssh user@tensor01
cd ~/mapper_embeddings
export CUDA_VISIBLE_DEVICES=5
python generate_embeddings_gpu.py --cluster 0 --gpu 5 --total-clusters 2

# Wait for completion, then retry download
```

---

## Merge Issues

### Issue: "Gap detected in index ranges"

**Symptoms:** Merge fails with gap error

**Diagnosis:**
```bash
python3 sync_and_merge_embeddings.py --merge-only
# Output:
# ✗ ERROR: Gap detected!
#   Expected index: 125000
#   Got index: 125010
```

**Solution:**
```bash
# Identify which worker has wrong range
python3 << 'EOF'
import pickle
from pathlib import Path

for f in sorted(Path('embeddings').glob('cluster*.pkl')):
    data = pickle.load(open(f, 'rb'))
    print(f"{f.name}: {data['start_index']:,} - {data['end_index']:,}")
EOF

# Look for range that doesn't match expected
# Expected ranges (for 16 workers):
# cluster0_gpu0: 0 - 15,625
# cluster0_gpu1: 15,625 - 31,250
# ...
# cluster1_gpu7: 234,375 - 250,000

# If cluster1_gpu0 shows 125,010 - 140,635 instead of 125,000 - 140,625:
# That worker used wrong start index

# Fix: Re-generate that worker's embeddings
ssh user@tensor02
cd ~/mapper_embeddings
rm embeddings/cluster1_gpu0.pkl
export CUDA_VISIBLE_DEVICES=0
python generate_embeddings_gpu.py --cluster 1 --gpu 0 --total-clusters 2

# Wait for completion
exit

# Re-download
rm embeddings/cluster1_gpu0.pkl
python3 sync_and_merge_embeddings.py --sync-only --clusters "tensor02"

# Retry merge
python3 sync_and_merge_embeddings.py --merge-only
```

---

### Issue: "NaN or Inf values found"

**Symptoms:** Quality check fails due to invalid values

**Diagnosis:**
```bash
python3 sync_and_merge_embeddings.py --merge-only
# Output:
# ✗ ERROR: Found NaN or Inf values!
```

**Solution:**
```bash
# Identify which file has NaN/Inf
python3 << 'EOF'
import pickle
import numpy as np
from pathlib import Path

for f in sorted(Path('embeddings').glob('cluster*.pkl')):
    data = pickle.load(open(f, 'rb'))
    embeddings = data['embeddings']
    has_nan = np.isnan(embeddings).any()
    has_inf = np.isinf(embeddings).any()

    if has_nan or has_inf:
        print(f"{f.name}:")
        print(f"  Cluster {data['cluster_id']}, GPU {data['gpu_id']}")
        print(f"  NaN: {has_nan}, Inf: {has_inf}")

        # Find which embeddings
        if has_nan:
            nan_indices = np.where(np.isnan(embeddings).any(axis=1))[0]
            print(f"  NaN at indices: {nan_indices[:10]}")  # First 10

        if has_inf:
            inf_indices = np.where(np.isinf(embeddings).any(axis=1))[0]
            print(f"  Inf at indices: {inf_indices[:10]}")
EOF

# Re-generate corrupted file
# (Same as gap recovery above)
```

---

### Issue: "Out of memory during merge"

**Symptoms:** Merge script crashes with MemoryError

**Diagnosis:**
```bash
python3 sync_and_merge_embeddings.py --merge-only
# Output: MemoryError: Unable to allocate array
```

**Solutions:**

**Option 1: Close other applications**
```bash
# Free up RAM
# Close browser, editors, etc.

# Check available memory
free -h  # Linux
vm_stat  # macOS

# Retry merge
python3 sync_and_merge_embeddings.py --merge-only
```

**Option 2: Use machine with more RAM**
```bash
# Merge requires ~4GB RAM (2x file size)
# If local machine has < 8GB, use cluster

# Upload merge script to cluster
scp sync_and_merge_embeddings.py user@tensor01:~/mapper_embeddings/
scp wikipedia.pkl user@tensor01:~/mapper_embeddings/

# Run merge on cluster
ssh user@tensor01
cd ~/mapper_embeddings
python3 sync_and_merge_embeddings.py --merge-only

# Download merged file
exit
scp user@tensor01:~/mapper_embeddings/embeddings/wikipedia_merged.pkl embeddings/
```

**Option 3: Merge in chunks (advanced)**
```bash
# Modify sync_and_merge_embeddings.py to merge 8 files at a time
# Then combine the two halves
# (Requires code modification)
```

---

## Validation Issues

### Issue: "Embedding count is wrong"

**Symptoms:** Merged file has != 250,000 embeddings

**Diagnosis:**
```bash
python3 -c "import pickle; data=pickle.load(open('embeddings/wikipedia_merged.pkl','rb')); print(len(data['embeddings']))"
# Output: 248750 (expected 250000)
```

**Solution:**
```bash
# Calculate how many missing
# 250,000 - 248,750 = 1,250 missing

# Each worker should have ~15,625 items
# 1,250 / 15,625 = 0.08 = one worker incomplete

# Check which worker is incomplete
python3 << 'EOF'
import pickle
from pathlib import Path

total = 0
for f in sorted(Path('embeddings').glob('cluster*.pkl')):
    data = pickle.load(open(f, 'rb'))
    count = len(data['embeddings'])
    expected = data['end_index'] - data['start_index']

    total += count

    if count != expected:
        print(f"{f.name}: {count:,}/{expected:,} ({'✓' if count == expected else '✗ INCOMPLETE'})")

print(f"\nTotal: {total:,}/250,010")
EOF

# Re-generate incomplete worker
# (Same as previous recovery procedures)
```

---

### Issue: "Article metadata missing"

**Symptoms:** Articles list is empty or incomplete

**Diagnosis:**
```bash
python3 -c "import pickle; data=pickle.load(open('embeddings/wikipedia_merged.pkl','rb')); print(len(data['articles']))"
# Output: 0 (expected 250000)
```

**Solution:**
```bash
# This means wikipedia.pkl wasn't loaded during merge
# Check if wikipedia.pkl exists
ls -lh wikipedia.pkl

# Re-run merge (will reload wikipedia.pkl)
python3 sync_and_merge_embeddings.py --merge-only

# If still failing:
python3 -c "import pickle; articles=pickle.load(open('wikipedia.pkl','rb')); print(f'Articles: {len(articles):,}')"
# Should output: Articles: 250,000

# If wikipedia.pkl is corrupted, need to obtain fresh copy
```

---

### Issue: "Embedding norms are unusual"

**Symptoms:** Mean norm is very high or very low

**Diagnosis:**
```bash
python3 << 'EOF'
import pickle
import numpy as np
data = pickle.load(open('embeddings/wikipedia_merged.pkl', 'rb'))
norms = np.linalg.norm(data['embeddings'], axis=1)
print(f"Mean norm: {norms.mean():.4f}")
print(f"Std norm: {norms.std():.4f}")
print(f"Min norm: {norms.min():.4f}")
print(f"Max norm: {norms.max():.4f}")
EOF

# Output:
# Mean norm: 0.0123 (TOO LOW, expected ~1.2)
# or
# Mean norm: 123.4567 (TOO HIGH, expected ~1.2)
```

**Solutions:**

**If norms too low:**
- Embeddings may be unnormalized
- Check model output format
- May need to normalize manually

**If norms too high:**
- May have scaling issue
- Check for duplicated dimensions

**If norms vary widely (std > 5.0):**
- Some embeddings may be corrupted
- Check individual worker outputs

```bash
# Check individual worker norms
python3 << 'EOF'
import pickle
import numpy as np
from pathlib import Path

for f in sorted(Path('embeddings').glob('cluster*.pkl')):
    data = pickle.load(open(f, 'rb'))
    norms = np.linalg.norm(data['embeddings'], axis=1)
    print(f"{f.name}: mean={norms.mean():.4f}, std={norms.std():.4f}")
EOF

# If one worker has unusual norms, regenerate it
```

---

## Emergency Procedures

### Complete Restart

If multiple issues and unclear state:

```bash
echo "PERFORMING COMPLETE RESTART"
echo "This will:"
echo "  1. Kill all workers"
echo "  2. Delete all partial outputs"
echo "  3. Re-launch from scratch"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Kill workers
    ssh user@tensor01 "killall python3; screen -wipe; rm ~/mapper_embeddings/embeddings/*.pkl"
    ssh user@tensor02 "killall python3; screen -wipe; rm ~/mapper_embeddings/embeddings/*.pkl"

    # Delete local downloads
    rm embeddings/cluster*.pkl

    # Re-launch
    ./launch_distributed.sh --clusters "tensor01 tensor02"

    echo "✓ Restart complete. Monitor with:"
    echo "  python3 monitor_clusters.py --interval 30"
fi
```

---

### Partial Recovery

If some workers completed successfully:

```bash
# Download completed workers
python3 sync_and_merge_embeddings.py --sync-only

# Check which workers are missing
python3 << 'EOF'
from pathlib import Path

downloaded = set()
for f in Path('embeddings').glob('cluster*.pkl'):
    # Extract cluster and GPU from filename
    parts = f.stem.split('_')
    cluster_id = int(parts[0].replace('cluster', ''))
    gpu_id = int(parts[1].replace('gpu', ''))
    downloaded.add((cluster_id, gpu_id))

print("Downloaded workers:")
for cluster, gpu in sorted(downloaded):
    print(f"  Cluster {cluster}, GPU {gpu}")

print("\nMissing workers:")
for cluster in [0, 1]:
    for gpu in range(8):
        if (cluster, gpu) not in downloaded:
            print(f"  Cluster {cluster}, GPU {gpu}")
            if cluster == 0:
                print(f"    Re-run: ssh user@tensor01; cd ~/mapper_embeddings; export CUDA_VISIBLE_DEVICES={gpu}; python generate_embeddings_gpu.py --cluster 0 --gpu {gpu} --total-clusters 2")
            else:
                print(f"    Re-run: ssh user@tensor02; cd ~/mapper_embeddings; export CUDA_VISIBLE_DEVICES={gpu}; python generate_embeddings_gpu.py --cluster 1 --gpu {gpu} --total-clusters 2")
EOF

# Manually re-run missing workers as indicated
```

---

## Getting Help

If issue not covered here:

1. **Check logs:**
   ```bash
   ssh user@cluster "tail -200 ~/mapper_embeddings/logs/gpu*.log"
   ```

2. **Search session notes:**
   ```bash
   grep -r "error" /Users/jmanning/mapper.io/notes/
   ```

3. **Document the issue:**
   ```bash
   echo "$(date): [Issue description]" >> notes/issues.log
   ```

4. **Check existing session summaries:**
   - `/Users/jmanning/mapper.io/notes/2025-11-14_*.md`
   - May contain similar issues and solutions

---

**Last Updated:** 2025-11-14
