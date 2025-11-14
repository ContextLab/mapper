# Wikipedia Embedding Generation - Execution Plan

**Date:** 2025-11-14
**Goal:** Generate 250K Wikipedia article embeddings on GPU cluster and save locally with metadata
**Infrastructure:** 2 clusters (tensor01, tensor02), 16 GPUs total (8 per cluster)
**Model:** google/embeddinggemma-300m (768 dimensions)
**Total Items:** 250,000 Wikipedia articles

---

## Table of Contents
1. [Pre-flight Checklist](#pre-flight-checklist)
2. [Launch Procedure](#launch-procedure)
3. [Monitoring Procedure](#monitoring-procedure)
4. [Failure Recovery](#failure-recovery)
5. [Download and Validation](#download-and-validation)
6. [Success Criteria](#success-criteria)

---

## Pre-flight Checklist

### 1. Local Environment Verification

**Command:**
```bash
cd /Users/jmanning/mapper.io
pwd
```

**Expected Output:**
```
/Users/jmanning/mapper.io
```

**What to Verify:**
- Current working directory is correct

**If Fails:**
- Navigate to correct directory before proceeding

---

**Command:**
```bash
ls -lh wikipedia.pkl
```

**Expected Output:**
```
-rw-r--r--  1 jmanning  staff   752M Nov 14 01:25 wikipedia.pkl
```

**What to Verify:**
- File exists and is ~752MB
- Contains 250,000 Wikipedia articles

**If Fails:**
```bash
# Check if file exists elsewhere
find /Users/jmanning -name "wikipedia.pkl" -type f 2>/dev/null

# If not found, this is a BLOCKER - must obtain wikipedia.pkl before proceeding
```

---

**Command:**
```bash
python3 -c "import pickle; articles = pickle.load(open('wikipedia.pkl', 'rb')); print(f'Articles: {len(articles):,}'); print(f'Sample: {articles[0].get(\"title\", \"NO TITLE\")}')"
```

**Expected Output:**
```
Articles: 250,000
Sample: [Some Wikipedia article title]
```

**What to Verify:**
- Exactly 250,000 articles
- Articles have structure (dict with 'title', 'text', etc.)

**If Fails:**
- BLOCKER: wikipedia.pkl is corrupted or wrong format
- Re-download or regenerate wikipedia.pkl

---

**Command:**
```bash
ls -la .credentials/
```

**Expected Output:**
```
total 24
drwxr-xr-x   5 jmanning  staff   160 Nov 14 11:25 .
-rw-r--r--   1 jmanning  staff    37 Nov 14 11:25 hf.token
-rw-r--r--   1 jmanning  staff   104 Nov 14 08:28 tensor01.credentials
-rw-r--r--   1 jmanning  staff   104 Nov 14 08:28 tensor02.credentials
```

**What to Verify:**
- .credentials directory exists
- tensor01.credentials exists
- tensor02.credentials exists
- hf.token exists (for HuggingFace authentication)

**If Fails:**
```bash
# Create .credentials directory if missing
mkdir -p .credentials

# BLOCKER: Must have valid credentials files
# Format for tensor01.credentials:
# {"address": "hostname", "username": "user", "password": "pass"}
```

---

**Command:**
```bash
python3 -c "import json; creds = json.load(open('.credentials/tensor01.credentials')); print('tensor01:', creds.get('address', 'MISSING ADDRESS'))"
python3 -c "import json; creds = json.load(open('.credentials/tensor02.credentials')); print('tensor02:', creds.get('address', 'MISSING ADDRESS'))"
```

**Expected Output:**
```
tensor01: [hostname or IP address]
tensor02: [hostname or IP address]
```

**What to Verify:**
- Credentials files are valid JSON
- Contains 'address', 'username', 'password' fields

**If Fails:**
- BLOCKER: Fix credentials format
- Test SSH connection manually

---

**Command:**
```bash
python3 -c "import paramiko; print(f'paramiko: {paramiko.__version__}')"
python3 -c "import numpy; print(f'numpy: {numpy.__version__}')"
python3 -c "import pickle; print('pickle: OK')"
```

**Expected Output:**
```
paramiko: 3.5.1
numpy: [version number]
pickle: OK
```

**What to Verify:**
- All required Python packages are installed

**If Fails:**
```bash
pip install paramiko numpy
```

---

**Command:**
```bash
which sshpass
```

**Expected Output:**
```
/opt/homebrew/bin/sshpass
```

**What to Verify:**
- sshpass is available (optional, fallback to paramiko)

**If Fails:**
- Not a blocker, paramiko will be used instead
- Optional: `brew install sshpass`

---

**Command:**
```bash
ls -la generate_embeddings_gpu.py launch_distributed.sh monitor_clusters.py sync_and_merge_embeddings.py
```

**Expected Output:**
```
-rwxr-xr-x  1 jmanning  staff  [size]  generate_embeddings_gpu.py
-rwxr-xr-x  1 jmanning  staff  [size]  launch_distributed.sh
-rwxr-xr-x  1 jmanning  staff  [size]  monitor_clusters.py
-rwxr-xr-x  1 jmanning  staff  [size]  sync_and_merge_embeddings.py
```

**What to Verify:**
- All required scripts exist
- Scripts are executable (chmod +x if needed)

**If Fails:**
```bash
# Make scripts executable
chmod +x generate_embeddings_gpu.py launch_distributed.sh monitor_clusters.py sync_and_merge_embeddings.py
```

---

### 2. Cluster Connectivity Test

**Command:**
```bash
python3 << 'EOF'
import json
from pathlib import Path
import paramiko

for cluster in ['tensor01', 'tensor02']:
    creds_file = Path('.credentials') / f'{cluster}.credentials'
    with open(creds_file) as f:
        creds = json.load(f)

    print(f"\nTesting {cluster} ({creds['address']})...")

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=creds['address'],
            username=creds['username'],
            password=creds['password'],
            timeout=10
        )

        # Test command execution
        stdin, stdout, stderr = ssh.exec_command('hostname && echo "SSH OK"')
        output = stdout.read().decode().strip()
        print(f"  ✓ Connected: {output}")

        ssh.close()

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        print(f"  BLOCKER: Cannot connect to {cluster}")

print("\nConnectivity test complete.")
EOF
```

**Expected Output:**
```
Testing tensor01 (hostname)...
  ✓ Connected: hostname
  SSH OK

Testing tensor02 (hostname)...
  ✓ Connected: hostname
  SSH OK

Connectivity test complete.
```

**What to Verify:**
- Can connect to both clusters via SSH
- Can execute commands remotely

**If Fails:**
- BLOCKER: Fix network connectivity
- Verify credentials
- Check firewall/VPN settings
- Test manual SSH: `ssh user@hostname`

---

### 3. Remote Cluster Environment Check

**Command:**
```bash
python3 << 'EOF'
import json
import paramiko
from pathlib import Path

for cluster in ['tensor01', 'tensor02']:
    creds_file = Path('.credentials') / f'{cluster}.credentials'
    with open(creds_file) as f:
        creds = json.load(f)

    print(f"\n{'='*60}")
    print(f"Checking {cluster}")
    print('='*60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=creds['address'],
        username=creds['username'],
        password=creds['password'],
        timeout=10
    )

    # Check working directory
    stdin, stdout, stderr = ssh.exec_command('ls -la ~/mapper_embeddings/ 2>&1 || echo "DIRECTORY NOT FOUND"')
    output = stdout.read().decode()
    print("Working directory check:")
    print(output[:500])

    # Check for wikipedia.pkl
    stdin, stdout, stderr = ssh.exec_command('ls -lh ~/mapper_embeddings/wikipedia.pkl 2>&1')
    output = stdout.read().decode()
    if 'No such file' in output:
        print("⚠ wikipedia.pkl: NOT FOUND (will upload)")
    else:
        print(f"✓ wikipedia.pkl: {output.strip()}")

    # Check GPU availability
    stdin, stdout, stderr = ssh.exec_command('nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader 2>&1')
    output = stdout.read().decode()
    print("\nGPU availability:")
    if 'command not found' in output or 'NVIDIA' not in output:
        print("✗ BLOCKER: No GPUs detected!")
    else:
        lines = output.strip().split('\n')
        print(f"  Found {len(lines)} GPUs:")
        for line in lines[:3]:
            print(f"    {line}")
        if len(lines) > 3:
            print(f"    ... and {len(lines)-3} more")

    # Check conda
    stdin, stdout, stderr = ssh.exec_command('which conda 2>&1')
    output = stdout.read().decode()
    if output.strip():
        print(f"\n✓ conda: {output.strip()}")
    else:
        print("\n⚠ conda: Not found (may need to source .bashrc)")

    ssh.close()

print("\nRemote environment check complete.")
EOF
```

**Expected Output (per cluster):**
```
============================================================
Checking tensor01
============================================================
Working directory check:
drwxr-xr-x 5 user user 4096 Nov 14 10:00 .
drwxr-xr-x 8 user user 4096 Nov 14 09:00 ..
drwxr-xr-x 2 user user 4096 Nov 14 10:00 embeddings
drwxr-xr-x 2 user user 4096 Nov 14 10:00 logs

✓ wikipedia.pkl: -rw-r--r-- 1 user user 752M Nov 14 09:00 wikipedia.pkl

GPU availability:
  Found 8 GPUs:
    0, NVIDIA A6000, 49140 MiB
    1, NVIDIA A6000, 49140 MiB
    2, NVIDIA A6000, 49140 MiB
    ... and 5 more

✓ conda: /home/user/miniconda3/bin/conda
```

**What to Verify:**
- Working directory exists (or will be created)
- wikipedia.pkl exists OR we can upload it
- 8 GPUs detected on each cluster
- conda is available

**If Fails:**
- No GPUs: BLOCKER - wrong cluster or driver issue
- No conda: May still work with system Python, or source conda in launch script
- No working directory: Will be created by launch script

---

### 4. Disk Space Check

**Command:**
```bash
python3 << 'EOF'
import json
import paramiko
from pathlib import Path

for cluster in ['tensor01', 'tensor02']:
    creds_file = Path('.credentials') / f'{cluster}.credentials'
    with open(creds_file) as f:
        creds = json.load(f)

    print(f"\nChecking disk space on {cluster}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=creds['address'],
        username=creds['username'],
        password=creds['password'],
        timeout=10
    )

    # Check disk space in home directory
    stdin, stdout, stderr = ssh.exec_command('df -h ~')
    output = stdout.read().decode()
    print(output)

    # Check available space
    stdin, stdout, stderr = ssh.exec_command('df -h ~ | tail -1 | awk \'{print $4}\'')
    available = stdout.read().decode().strip()
    print(f"  Available space: {available}")

    # Estimate required space
    # wikipedia.pkl: 752MB
    # 8 GPU outputs: ~150MB each = 1.2GB
    # Conda env: ~2GB
    # Total: ~4GB minimum
    print(f"  Required space: ~4GB minimum")

    ssh.close()

print("\nDisk space check complete.")
EOF
```

**Expected Output:**
```
Checking disk space on tensor01...
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       100G   20G   80G  20% /home

  Available space: 80G
  Required space: ~4GB minimum

Checking disk space on tensor02...
...
```

**What to Verify:**
- At least 4GB free space per cluster
- Preferably 10GB+ for safety

**If Fails:**
- BLOCKER if < 4GB: Clean up cluster or choose different location
- Check with: `ssh user@cluster "du -sh ~/mapper_embeddings/*"`

---

### 5. Create Local Embeddings Directory

**Command:**
```bash
mkdir -p embeddings
ls -la embeddings/
```

**Expected Output:**
```
total 0
drwxr-xr-x   2 jmanning  staff    64 Nov 14 15:30 .
drwxr-xr-x  89 jmanning  staff  2848 Nov 14 15:30 ..
```

**What to Verify:**
- Directory exists and is writable

**If Fails:**
```bash
# Check permissions
ls -la .
# Should show mapper.io directory is writable
```

---

### 6. Pre-flight Summary Check

**Run this to get a summary:**
```bash
echo "==================================================================="
echo "PRE-FLIGHT CHECKLIST SUMMARY"
echo "==================================================================="
echo ""
echo "Local Files:"
ls -lh wikipedia.pkl 2>/dev/null && echo "  ✓ wikipedia.pkl" || echo "  ✗ wikipedia.pkl MISSING"
ls .credentials/tensor01.credentials 2>/dev/null && echo "  ✓ tensor01.credentials" || echo "  ✗ tensor01.credentials MISSING"
ls .credentials/tensor02.credentials 2>/dev/null && echo "  ✓ tensor02.credentials" || echo "  ✗ tensor02.credentials MISSING"
ls .credentials/hf.token 2>/dev/null && echo "  ✓ hf.token" || echo "  ✗ hf.token MISSING"
echo ""
echo "Scripts:"
ls generate_embeddings_gpu.py 2>/dev/null && echo "  ✓ generate_embeddings_gpu.py" || echo "  ✗ MISSING"
ls launch_distributed.sh 2>/dev/null && echo "  ✓ launch_distributed.sh" || echo "  ✗ MISSING"
ls monitor_clusters.py 2>/dev/null && echo "  ✓ monitor_clusters.py" || echo "  ✗ MISSING"
ls sync_and_merge_embeddings.py 2>/dev/null && echo "  ✓ sync_and_merge_embeddings.py" || echo "  ✗ MISSING"
echo ""
echo "Python Packages:"
python3 -c "import paramiko" 2>/dev/null && echo "  ✓ paramiko" || echo "  ✗ paramiko MISSING"
python3 -c "import numpy" 2>/dev/null && echo "  ✓ numpy" || echo "  ✗ numpy MISSING"
echo ""
echo "==================================================================="
echo "If all items show ✓, proceed to Launch Procedure"
echo "If any show ✗, resolve issues before proceeding"
echo "==================================================================="
```

**Expected Output:**
```
===================================================================
PRE-FLIGHT CHECKLIST SUMMARY
===================================================================

Local Files:
  ✓ wikipedia.pkl
  ✓ tensor01.credentials
  ✓ tensor02.credentials
  ✓ hf.token

Scripts:
  ✓ generate_embeddings_gpu.py
  ✓ launch_distributed.sh
  ✓ monitor_clusters.py
  ✓ sync_and_merge_embeddings.py

Python Packages:
  ✓ paramiko
  ✓ numpy

===================================================================
If all items show ✓, proceed to Launch Procedure
If any show ✗, resolve issues before proceeding
===================================================================
```

**What to Verify:**
- ALL items show ✓

**If Fails:**
- BLOCKER: Go back and fix missing items
- DO NOT proceed to launch until all checks pass

---

## Launch Procedure

### Phase 1: Upload and Setup (Sequential)

#### Step 1: Launch Distributed Workers on Both Clusters

**Command:**
```bash
cd /Users/jmanning/mapper.io
./launch_distributed.sh --clusters "tensor01 tensor02"
```

**Expected Output:**
```
================================================================================
DISTRIBUTED GPU LAUNCHER
================================================================================
Clusters: tensor01 tensor02

Total active clusters: 2

================================================================================
LAUNCHING ON tensor01 (Cluster 0)
================================================================================
Address: [hostname]
Username: [username]

[1/5] Uploading files...
  ✓ wikipedia.pkl already exists, skipping upload
  ✓ Files uploaded

[2/5] Setting up conda environment...
  Removing existing mapper_gpu environment...
  Creating fresh mapper_gpu environment...
  ✓ Environment created

[3/5] Launching 8 GPU workers...
  ✓ Launched GPU 0
  ✓ Launched GPU 1
  ✓ Launched GPU 2
  ✓ Launched GPU 3
  ✓ Launched GPU 4
  ✓ Launched GPU 5
  ✓ Launched GPU 6
  ✓ Launched GPU 7

[4/5] Verifying workers...
  ✓ 8 workers running

[5/5] Initial log check...
GPU worker 0 starting at [date]

✓ tensor01 launch complete

[Same output repeated for tensor02]

================================================================================
✓ ALL CLUSTERS LAUNCHED
================================================================================

Monitor progress:
  python monitor_clusters.py
```

**What to Verify:**
- Both clusters show "✓ [cluster] launch complete"
- Each cluster shows "8 workers running"
- No error messages during setup
- Initial log shows "GPU worker 0 starting"

**How to Detect Failure:**
- "✗ Error" messages appear
- Worker count is not 8
- Connection timeout errors
- "Environment creation failed"

**What to Do If It Fails:**

**Issue: Connection Failed**
```bash
# Test SSH manually
ssh user@tensor01

# If password prompt, credentials may be wrong
# Check .credentials/tensor01.credentials
```

**Issue: Upload Failed**
```bash
# Manually upload wikipedia.pkl
scp wikipedia.pkl user@tensor01:~/mapper_embeddings/

# Then re-run launch_distributed.sh
```

**Issue: Conda Environment Failed**
```bash
# SSH to cluster and debug
ssh user@tensor01
cd ~/mapper_embeddings
conda create -y -n mapper_gpu python=3.10
conda activate mapper_gpu
pip install torch sentence-transformers numpy

# Then re-run launch_distributed.sh
```

**Issue: Workers Not Starting**
```bash
# SSH to cluster and check
ssh user@tensor01
screen -ls
# Should show 8 mapper_gpu* sessions

# Check logs
tail ~/mapper_embeddings/logs/gpu0.log

# If errors, kill and restart
screen -S mapper_gpu0 -X quit
cd ~/mapper_embeddings
screen -dmS mapper_gpu0 bash -c "export CUDA_VISIBLE_DEVICES=0; python generate_embeddings_gpu.py --cluster 0 --gpu 0 --total-clusters 2 2>&1 | tee logs/gpu0.log"
```

---

#### Step 2: Verify Workers Started Successfully

**Wait:** 30 seconds after launch

**Command:**
```bash
python3 << 'EOF'
import json
import paramiko
from pathlib import Path
import time

for cluster_id, cluster in enumerate(['tensor01', 'tensor02']):
    creds_file = Path('.credentials') / f'{cluster}.credentials'
    with open(creds_file) as f:
        creds = json.load(f)

    print(f"\n{'='*60}")
    print(f"Verifying {cluster} (Cluster {cluster_id})")
    print('='*60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=creds['address'],
        username=creds['username'],
        password=creds['password'],
        timeout=10
    )

    # Check screen sessions
    stdin, stdout, stderr = ssh.exec_command('screen -ls | grep mapper_gpu | wc -l')
    worker_count = int(stdout.read().decode().strip())
    print(f"Workers running: {worker_count}/8")

    if worker_count != 8:
        print(f"  ⚠ WARNING: Expected 8 workers, found {worker_count}")

    # Check each GPU log
    for gpu_id in range(8):
        stdin, stdout, stderr = ssh.exec_command(f'tail -3 ~/mapper_embeddings/logs/gpu{gpu_id}.log 2>&1')
        log_output = stdout.read().decode().strip()

        if 'GPU WORKER: Cluster' in log_output:
            print(f"  ✓ GPU {gpu_id}: Started")
        elif 'No such file' in log_output:
            print(f"  ⚠ GPU {gpu_id}: Log not created yet")
        elif 'error' in log_output.lower() or 'fail' in log_output.lower():
            print(f"  ✗ GPU {gpu_id}: ERROR in log")
            print(f"    {log_output[:200]}")
        else:
            print(f"  ? GPU {gpu_id}: Unknown state")
            print(f"    {log_output[:200]}")

    ssh.close()

print("\nWorker verification complete.")
EOF
```

**Expected Output:**
```
============================================================
Verifying tensor01 (Cluster 0)
============================================================
Workers running: 8/8
  ✓ GPU 0: Started
  ✓ GPU 1: Started
  ✓ GPU 2: Started
  ✓ GPU 3: Started
  ✓ GPU 4: Started
  ✓ GPU 5: Started
  ✓ GPU 6: Started
  ✓ GPU 7: Started

[Same for tensor02]

Worker verification complete.
```

**What to Verify:**
- All 16 workers (8 per cluster) show "Started"
- No ERROR messages in logs
- Worker count is 8/8 for each cluster

**How to Detect Failure:**
- Worker count < 8
- "ERROR in log" messages
- "Unknown state" for workers

**What to Do If It Fails:**

**Issue: Worker count is 0**
```bash
# Workers didn't start at all
# SSH to cluster and check
ssh user@tensor01
screen -ls
# If no sessions, launch script failed

# Check if conda environment exists
conda env list | grep mapper_gpu

# Re-run launch script
exit  # exit from SSH
./launch_distributed.sh --clusters "tensor01"
```

**Issue: Some workers not starting (e.g., 5/8)**
```bash
# Check which workers are missing
ssh user@tensor01
screen -ls | grep mapper_gpu
# Note which GPU IDs are missing (e.g., gpu3, gpu5, gpu7)

# Check their logs
tail ~/mapper_embeddings/logs/gpu3.log

# Manually restart missing workers
export CUDA_VISIBLE_DEVICES=3
screen -dmS mapper_gpu3 bash -c "cd ~/mapper_embeddings && python generate_embeddings_gpu.py --cluster 0 --gpu 3 --total-clusters 2 2>&1 | tee logs/gpu3.log"
```

**Issue: ERROR in log**
```bash
# SSH to cluster and inspect full log
ssh user@tensor01
cat ~/mapper_embeddings/logs/gpu0.log

# Common errors and fixes:

# "CUDA out of memory"
# -> GPU already in use, kill other processes
nvidia-smi
kill -9 [PID]
# Then restart worker

# "Module not found: sentence_transformers"
# -> Conda environment not activated
conda activate mapper_gpu
pip install sentence-transformers
# Then restart worker

# "FileNotFoundError: wikipedia.pkl"
# -> File not uploaded
# Upload from local machine:
exit
scp wikipedia.pkl user@tensor01:~/mapper_embeddings/
```

---

### Phase 2: Initial Progress Check

**Wait:** 2 minutes after workers start

**Command:**
```bash
python3 << 'EOF'
import json
import paramiko
from pathlib import Path

for cluster_id, cluster in enumerate(['tensor01', 'tensor02']):
    creds_file = Path('.credentials') / f'{cluster}.credentials'
    with open(creds_file) as f:
        creds = json.load(f)

    print(f"\n{'='*60}")
    print(f"Progress check: {cluster}")
    print('='*60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=creds['address'],
        username=creds['username'],
        password=creds['password'],
        timeout=10
    )

    # Check if progress.json exists
    stdin, stdout, stderr = ssh.exec_command('cat ~/mapper_embeddings/embeddings/progress.json 2>&1')
    output = stdout.read().decode()

    if 'No such file' in output:
        print("  ⚠ progress.json not created yet")
        print("  Workers may still be loading model...")

        # Check GPU memory usage as proxy
        stdin, stdout, stderr = ssh.exec_command('nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits')
        gpu_mem = stdout.read().decode()
        print("\n  GPU memory usage:")
        for line in gpu_mem.strip().split('\n'):
            gpu_id, mem_mb = line.split(',')
            mem_mb = int(mem_mb.strip())
            if mem_mb > 1000:  # > 1GB suggests model loaded
                print(f"    GPU {gpu_id.strip()}: {mem_mb}MB (model loaded)")
            else:
                print(f"    GPU {gpu_id.strip()}: {mem_mb}MB (loading...)")
    else:
        try:
            progress = json.loads(output)
            summary = progress.get('_summary', {})
            workers = summary.get('total_workers_completed', 0)
            items = summary.get('total_items_processed', 0)
            percent = summary.get('percent_complete', 0)

            print(f"  Workers completed: {workers}/8")
            print(f"  Items processed: {items:,}")
            print(f"  Progress: {percent:.2f}%")

            if workers > 0:
                print(f"\n  ✓ Workers are producing output!")
            else:
                print(f"\n  ⚠ Workers running but no output yet")

        except json.JSONDecodeError:
            print("  ✗ progress.json exists but is malformed")
            print(f"  Content: {output[:200]}")

    ssh.close()

print("\nInitial progress check complete.")
EOF
```

**Expected Output:**
```
============================================================
Progress check: tensor01
============================================================
  ⚠ progress.json not created yet
  Workers may still be loading model...

  GPU memory usage:
    GPU 0: 3421MB (model loaded)
    GPU 1: 3418MB (model loaded)
    GPU 2: 3415MB (model loaded)
    GPU 3: 3420MB (model loaded)
    GPU 4: 3419MB (model loaded)
    GPU 5: 3422MB (model loaded)
    GPU 6: 3417MB (model loaded)
    GPU 7: 3421MB (model loaded)

[Same for tensor02]

Initial progress check complete.
```

**OR (if fast startup):**
```
============================================================
Progress check: tensor01
============================================================
  Workers completed: 0/8
  Items processed: 0
  Progress: 0.00%

  ⚠ Workers running but no output yet

[After a few more minutes:]

  Workers completed: 0/8
  Items processed: 1,250
  Progress: 1.00%

  ✓ Workers are producing output!
```

**What to Verify:**
- GPU memory shows model loaded (>3GB per GPU)
- OR progress.json shows items being processed
- No errors about missing files

**How to Detect Failure:**
- All GPUs show < 500MB memory (model not loading)
- Error messages in output
- After 5 minutes, still no progress

**What to Do If It Fails:**

**Issue: Model not loading (GPU memory < 1GB)**
```bash
# SSH and check logs
ssh user@tensor01
tail -50 ~/mapper_embeddings/logs/gpu0.log

# Look for errors like:
# - "HuggingFace authentication failed" -> Check hf.token
# - "Connection timeout" -> Cluster may not have internet access
# - "CUDA initialization failed" -> GPU driver issue

# If HF token issue:
cat ~/mapper_embeddings/.credentials/hf.token
# Should contain valid HuggingFace token

# If missing:
exit
scp .credentials/hf.token user@tensor01:~/mapper_embeddings/.credentials/
```

**Issue: Workers running but no output after 5 minutes**
```bash
# Check if workers are actually running
ssh user@tensor01
ps aux | grep python | grep generate_embeddings_gpu

# If no processes, workers died
# Check logs for crash
tail -100 ~/mapper_embeddings/logs/gpu0.log

# Look for:
# - Out of memory errors
# - Python exceptions
# - CUDA errors

# Common fix: Reduce batch size
# Edit generate_embeddings_gpu.py:
# Change batch_size=32 to batch_size=16
```

---

## Monitoring Procedure

### Automated Monitoring (Recommended)

**Command:**
```bash
python3 monitor_clusters.py --interval 30
```

**Expected Output (every 30 seconds):**
```
================================================================================
Check #1 at 2025-11-14 15:35:00
================================================================================

Cluster 1 (tensor01):
  Workers: 0/8
  Items: 2,150/125,005 (1.7%)
  - cluster0_gpu0: 268 items @ 44.7 items/sec
  - cluster0_gpu1: 271 items @ 45.2 items/sec
  - cluster0_gpu2: 265 items @ 44.2 items/sec
  - cluster0_gpu3: 270 items @ 45.0 items/sec
  - cluster0_gpu4: 268 items @ 44.7 items/sec
  - cluster0_gpu5: 272 items @ 45.3 items/sec
  - cluster0_gpu6: 266 items @ 44.3 items/sec
  - cluster0_gpu7: 270 items @ 45.0 items/sec

Cluster 2 (tensor02):
  Workers: 0/8
  Items: 2,180/125,005 (1.7%)
  - cluster1_gpu0: 275 items @ 45.8 items/sec
  - cluster1_gpu1: 272 items @ 45.3 items/sec
  [... 6 more workers ...]

Combined Progress:
  Workers completed: 0/16
  Total items: 4,330/250,010 (1.7%)
  Combined rate: 722.3 items/sec
  ETA: 5.7m (at 15:40:42)

Next check in 30s...
```

**What to Monitor:**
- Combined rate should be 500-1000 items/sec (50-100 per GPU)
- ETA should be 3-10 minutes initially
- Worker count increases as GPUs finish
- No workers showing 0 items/sec for extended periods

**How to Detect Issues:**

1. **Stuck Workers (0 items/sec for >2 minutes)**
   - One or more workers not progressing

2. **Slow Progress (< 200 items/sec combined)**
   - All workers running but very slow

3. **Worker Disappears**
   - Worker was in list, now missing

4. **No Progress File After 3 Minutes**
   - Neither cluster showing progress

**What to Do If Issues Detected:**

**Issue: Stuck Worker (e.g., cluster0_gpu3 at 0 items/sec)**
```bash
# SSH to cluster
ssh user@tensor01

# Check if worker is alive
screen -ls | grep mapper_gpu3

# Attach to screen session to see live output
screen -r mapper_gpu3
# Press Ctrl+A, D to detach

# If frozen, kill and restart
screen -S mapper_gpu3 -X quit
cd ~/mapper_embeddings
export CUDA_VISIBLE_DEVICES=3
screen -dmS mapper_gpu3 bash -c "python generate_embeddings_gpu.py --cluster 0 --gpu 3 --total-clusters 2 2>&1 | tee logs/gpu3.log"
```

**Issue: All Workers Slow (< 20 items/sec per GPU)**
```bash
# Check GPU utilization
ssh user@tensor01
nvidia-smi

# Look for:
# - Low GPU utilization (< 50%)
# - High CPU usage (bottleneck)
# - Slow network I/O

# Check if other jobs running
nvidia-smi
ps aux | grep python | grep -v generate_embeddings

# If other jobs, may need to wait or kill them
```

**Issue: Worker Disappears from Progress**
```bash
# Worker crashed
ssh user@tensor01
screen -ls | grep mapper_gpu4
# If missing, worker died

# Check log for error
tail -100 ~/mapper_embeddings/logs/gpu4.log

# Common causes:
# - Out of memory -> Restart with lower batch size
# - CUDA error -> GPU may have failed, skip this GPU
# - Network timeout -> Temporary, restart worker

# Restart worker
export CUDA_VISIBLE_DEVICES=4
screen -dmS mapper_gpu4 bash -c "cd ~/mapper_embeddings && python generate_embeddings_gpu.py --cluster 0 --gpu 4 --total-clusters 2 2>&1 | tee logs/gpu4.log"
```

---

### Manual Progress Check (Alternative)

If automated monitoring fails, manually check progress:

**Command:**
```bash
# Check cluster 1
ssh user@tensor01 "cat ~/mapper_embeddings/embeddings/progress.json 2>&1" | python3 -m json.tool

# Check cluster 2
ssh user@tensor02 "cat ~/mapper_embeddings/embeddings/progress.json 2>&1" | python3 -m json.tool
```

**Expected Output:**
```json
{
  "cluster0_gpu0": {
    "start_index": 0,
    "end_index": 15625,
    "items_processed": 15625,
    "processing_time": 342.56,
    "rate": 45.6,
    "completed_at": "2025-11-14T15:38:22.123456",
    "output_file": "embeddings/cluster0_gpu0.pkl"
  },
  [... more workers ...],
  "_summary": {
    "total_workers_completed": 8,
    "total_items_processed": 125005,
    "target_items": 125005,
    "percent_complete": 100.0,
    "last_updated": "2025-11-14T15:42:15.654321"
  }
}
```

**What to Verify:**
- Items_processed increasing over time
- Rate is reasonable (40-100 items/sec)
- No workers stuck at same count

---

### Monitoring Checklist (Every 5 Minutes)

**Run this quick check:**
```bash
echo "=== Quick Status Check ==="
date
echo ""

# Check if monitor script is running
ps aux | grep monitor_clusters.py | grep -v grep && echo "✓ Monitor running" || echo "⚠ Monitor not running"

echo ""
echo "Recent monitor output:"
# If running monitor in background with tee, check log
tail -20 monitor.log 2>/dev/null || echo "(No monitor.log file)"

echo ""
echo "Expected completion time: 3-10 minutes from start"
echo "Current time: $(date +%H:%M:%S)"
```

---

### Completion Detection

**When monitor_clusters.py shows:**
```
================================================================================
✓ ALL WORKERS COMPLETE!
================================================================================
Total monitoring time: 5.3m

Next steps:
  1. Run merge_embeddings.py to download and combine results
  2. Continue with UMAP projection
```

**This means:**
- All 16 workers finished successfully
- Ready to proceed to Download and Validation phase

**If this message doesn't appear after 20 minutes:**
- Something is wrong
- Check "Failure Recovery" section

---

## Failure Recovery

### Common Failure Scenarios

#### Scenario 1: Single Worker Crashes

**Detection:**
- Monitor shows worker disappeared
- OR worker stuck at same count for >5 minutes

**Recovery:**
```bash
# Identify failed worker (e.g., cluster0_gpu5)
# SSH to cluster
ssh user@tensor01

# Check if checkpoint exists
ls -lh ~/mapper_embeddings/embeddings/cluster0_gpu5_checkpoint_*.pkl
# If exists, worker made some progress before crashing

# Check log for error
tail -100 ~/mapper_embeddings/logs/gpu5.log

# Kill any hung processes
ps aux | grep "gpu 5" | grep -v grep | awk '{print $2}' | xargs kill -9

# Restart worker (will resume from checkpoint)
cd ~/mapper_embeddings
export CUDA_VISIBLE_DEVICES=5
screen -dmS mapper_gpu5 bash -c "python generate_embeddings_gpu.py --cluster 0 --gpu 5 --total-clusters 2 2>&1 | tee -a logs/gpu5.log"

# Verify restart
screen -ls | grep mapper_gpu5
tail -f logs/gpu5.log
# Should show "Loading checkpoint..." if resuming
```

---

#### Scenario 2: Entire Cluster Loses Connection

**Detection:**
- Monitor shows "Error connecting to tensor01"
- All workers from one cluster disappear

**Recovery:**
```bash
# Test connection
ping tensor01.example.com

# Try SSH
ssh user@tensor01

# If connection restored:
# Check if workers still running
screen -ls | grep mapper_gpu
# Should show 8 sessions if they survived

# If no sessions, workers died during disconnection
# Check what progress was made
cat ~/mapper_embeddings/embeddings/progress.json

# Re-run launch script for this cluster only
exit  # Exit SSH
./launch_distributed.sh --clusters "tensor01"

# This will:
# - Upload scripts again
# - Restart all workers
# - Workers will resume from checkpoints
```

---

#### Scenario 3: Out of Memory Error

**Detection:**
- Worker log shows "CUDA out of memory" or "RuntimeError: out of memory"

**Recovery:**
```bash
# SSH to cluster
ssh user@tensor01

# Check GPU memory
nvidia-smi

# If GPU still has memory leak, reset it
sudo nvidia-smi --gpu-reset -i 3  # Reset GPU 3
# (May require sudo access)

# Or just kill the process
ps aux | grep "gpu 3" | awk '{print $2}' | xargs kill -9

# Restart with reduced batch size
# Edit local generate_embeddings_gpu.py:
# Change: batch_size=32
# To: batch_size=16

# Re-upload script
exit
scp generate_embeddings_gpu.py user@tensor01:~/mapper_embeddings/

# Restart worker
ssh user@tensor01
cd ~/mapper_embeddings
export CUDA_VISIBLE_DEVICES=3
screen -dmS mapper_gpu3 bash -c "python generate_embeddings_gpu.py --cluster 0 --gpu 3 --total-clusters 2 2>&1 | tee -a logs/gpu3.log"
```

---

#### Scenario 4: Model Download Timeout

**Detection:**
- Worker log shows "Connection timeout" or "Failed to download model"
- Workers stuck at "Loading model..."

**Recovery:**
```bash
# SSH to cluster
ssh user@tensor01

# Pre-download model manually
conda activate mapper_gpu
python3 << 'EOF'
from sentence_transformers import SentenceTransformer
print("Downloading model...")
model = SentenceTransformer('google/embeddinggemma-300m')
print("Model cached successfully")
EOF

# Model is now cached, workers will use cached version
# Restart workers
screen -S mapper_gpu0 -X quit
# ... repeat for all GPUs

# Re-launch
exit
./launch_distributed.sh --clusters "tensor01"
```

---

#### Scenario 5: Checkpointing Failure

**Detection:**
- Worker log shows "Failed to save checkpoint"
- Progress.json not updating

**Recovery:**
```bash
# SSH to cluster
ssh user@tensor01

# Check disk space
df -h ~/mapper_embeddings

# If disk full:
# Delete old checkpoints
rm ~/mapper_embeddings/embeddings/*_checkpoint_*.pkl

# Keep only final files
ls -lh ~/mapper_embeddings/embeddings/cluster0_gpu*.pkl

# If permissions issue:
ls -la ~/mapper_embeddings/embeddings/
# Should be writable by user

chmod 755 ~/mapper_embeddings/embeddings/

# Restart workers
```

---

#### Scenario 6: All Workers Complete But Count is Wrong

**Detection:**
- Monitor shows "ALL WORKERS COMPLETE"
- But total items != 250,010

**Recovery:**
```bash
# Check actual total from progress files
ssh user@tensor01 "cat ~/mapper_embeddings/embeddings/progress.json" | python3 -c "import json, sys; data=json.load(sys.stdin); print(f\"tensor01: {data['_summary']['total_items_processed']}\")"

ssh user@tensor02 "cat ~/mapper_embeddings/embeddings/progress.json" | python3 -c "import json, sys; data=json.load(sys.stdin); print(f\"tensor02: {data['_summary']['total_items_processed']}\")"

# If total < 250,010:
# Identify missing ranges
# Check which workers have gaps

# Example: If cluster0_gpu3 shows only 10,000 items but should have 15,625
# That worker didn't complete fully

# Re-run that specific worker
ssh user@tensor01
cd ~/mapper_embeddings
export CUDA_VISIBLE_DEVICES=3
screen -dmS mapper_gpu3 bash -c "python generate_embeddings_gpu.py --cluster 0 --gpu 3 --total-clusters 2 2>&1 | tee -a logs/gpu3_rerun.log"
```

---

### Recovery Checklist

When recovering from any failure:

1. **Document the failure**
   ```bash
   echo "$(date): [Failure description]" >> notes/failures.log
   ```

2. **Verify failure cause**
   - Check worker logs
   - Check system resources (GPU, disk, memory)
   - Check network connectivity

3. **Implement fix**
   - Follow scenario-specific recovery above
   - Or adapt based on error messages

4. **Verify fix worked**
   - Wait 2 minutes
   - Check worker is progressing
   - Monitor shows increasing items

5. **Update monitoring**
   - Restart monitor_clusters.py if needed
   - Note expected completion time adjusted

6. **If recovery fails**
   - Escalate: Manual intervention needed
   - Document issue in notes/failures.log
   - Consider alternative approaches

---

### Nuclear Option: Complete Restart

If multiple failures and unclear state:

```bash
# 1. Kill all workers on both clusters
for cluster in tensor01 tensor02; do
    ssh user@$cluster "killall python3; screen -wipe"
done

# 2. Clean up partial outputs
for cluster in tensor01 tensor02; do
    ssh user@$cluster "rm ~/mapper_embeddings/embeddings/*.pkl; rm ~/mapper_embeddings/embeddings/progress.json"
done

# 3. Re-launch from scratch
./launch_distributed.sh --clusters "tensor01 tensor02"

# 4. Monitor closely
python3 monitor_clusters.py --interval 30
```

**When to use this:**
- After 3+ individual recovery attempts failed
- Unclear which workers are in what state
- Corruption suspected in checkpoint files

**Cost:**
- Loses all progress (start from 0)
- But guarantees clean state

---

## Download and Validation

### Phase 1: Verify Completion

**Before downloading, verify all data is ready:**

**Command:**
```bash
python3 << 'EOF'
import json
import paramiko
from pathlib import Path

print("="*60)
print("FINAL VERIFICATION BEFORE DOWNLOAD")
print("="*60)

total_items = 0
total_files = 0
issues = []

for cluster_id, cluster in enumerate(['tensor01', 'tensor02']):
    creds_file = Path('.credentials') / f'{cluster}.credentials'
    with open(creds_file) as f:
        creds = json.load(f)

    print(f"\nCluster: {cluster}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=creds['address'],
        username=creds['username'],
        password=creds['password'],
        timeout=10
    )

    # Check progress
    stdin, stdout, stderr = ssh.exec_command('cat ~/mapper_embeddings/embeddings/progress.json 2>&1')
    progress_output = stdout.read().decode()

    if 'No such file' in progress_output:
        issues.append(f"{cluster}: No progress file")
        print(f"  ✗ No progress file found")
        ssh.close()
        continue

    progress = json.loads(progress_output)
    summary = progress.get('_summary', {})
    workers = summary.get('total_workers_completed', 0)
    items = summary.get('total_items_processed', 0)

    print(f"  Workers completed: {workers}/8")
    print(f"  Items processed: {items:,}")

    if workers < 8:
        issues.append(f"{cluster}: Only {workers}/8 workers completed")

    total_items += items

    # Check files exist
    stdin, stdout, stderr = ssh.exec_command('ls ~/mapper_embeddings/embeddings/cluster*.pkl 2>&1 | wc -l')
    file_count = int(stdout.read().decode().strip())
    print(f"  Files: {file_count}/8")

    if file_count < 8:
        issues.append(f"{cluster}: Only {file_count}/8 files found")

    total_files += file_count

    # Check file sizes
    stdin, stdout, stderr = ssh.exec_command('ls -lh ~/mapper_embeddings/embeddings/cluster*.pkl 2>&1')
    files_output = stdout.read().decode()
    print(f"\n  File sizes:")
    for line in files_output.strip().split('\n')[:3]:
        parts = line.split()
        if len(parts) >= 9:
            size = parts[4]
            filename = parts[8]
            print(f"    {filename}: {size}")
    if len(files_output.strip().split('\n')) > 3:
        print(f"    ... and {len(files_output.strip().split('\n')) - 3} more")

    ssh.close()

print(f"\n{'='*60}")
print("SUMMARY")
print("="*60)
print(f"Total items processed: {total_items:,}/250,010")
print(f"Total files: {total_files}/16")
print(f"Expected items: 250,010")
print(f"Expected files: 16")

if issues:
    print(f"\n⚠ ISSUES FOUND:")
    for issue in issues:
        print(f"  - {issue}")
    print(f"\n✗ NOT READY FOR DOWNLOAD")
    print("Resolve issues above before downloading.")
else:
    if total_items >= 250010 and total_files == 16:
        print(f"\n✓ READY FOR DOWNLOAD")
        print("All data verified. Proceed to download phase.")
    else:
        print(f"\n⚠ INCOMPLETE")
        print("Wait for more workers to complete.")

EOF
```

**Expected Output:**
```
============================================================
FINAL VERIFICATION BEFORE DOWNLOAD
============================================================

Cluster: tensor01
  Workers completed: 8/8
  Items processed: 125,005

  Files: 8/8

  File sizes:
    cluster0_gpu0.pkl: 152M
    cluster0_gpu1.pkl: 152M
    cluster0_gpu2.pkl: 152M
    ... and 5 more

Cluster: tensor02
  Workers completed: 8/8
  Items processed: 125,005

  Files: 8/8

  File sizes:
    cluster1_gpu0.pkl: 152M
    cluster1_gpu1.pkl: 152M
    cluster1_gpu2.pkl: 152M
    ... and 5 more

============================================================
SUMMARY
============================================================
Total items processed: 250,010/250,010
Total files: 16/16
Expected items: 250,010
Expected files: 16

✓ READY FOR DOWNLOAD
All data verified. Proceed to download phase.
```

**What to Verify:**
- Total items exactly 250,010
- Total files exactly 16
- All file sizes reasonable (100-200MB each)
- No issues listed

**If Not Ready:**
- Wait for workers to complete
- OR follow "Failure Recovery" for incomplete workers

---

### Phase 2: Download All Embedding Files

**Command:**
```bash
cd /Users/jmanning/mapper.io
python3 sync_and_merge_embeddings.py --sync-only
```

**Expected Output:**
```
================================================================================
EMBEDDING SYNC & MERGE
================================================================================
Started: 2025-11-14 15:45:30
Working directory: /Users/jmanning/mapper.io

Embeddings directory: /Users/jmanning/mapper.io/embeddings

================================================================================
SYNC PHASE
================================================================================

================================================================================
SYNCING FROM TENSOR01
================================================================================
Output directory: /Users/jmanning/mapper.io/embeddings
Remote directory: /home/user/mapper_embeddings/embeddings

Connecting to tensor01.example.com...
✓ Connected
Found 8 embedding files

  [1/8] cluster0_gpu0.pkl... ✓ (152.23 MB)
  [2/8] cluster0_gpu1.pkl... ✓ (152.18 MB)
  [3/8] cluster0_gpu2.pkl... ✓ (151.95 MB)
  [4/8] cluster0_gpu3.pkl... ✓ (152.31 MB)
  [5/8] cluster0_gpu4.pkl... ✓ (152.12 MB)
  [6/8] cluster0_gpu5.pkl... ✓ (152.27 MB)
  [7/8] cluster0_gpu6.pkl... ✓ (152.01 MB)
  [8/8] cluster0_gpu7.pkl... ✓ (152.34 MB)

✓ Downloaded 8 files from tensor01

================================================================================
SYNCING FROM TENSOR02
================================================================================
[Same output pattern for tensor02...]

✓ Downloaded 8 files from tensor02

================================================================================
SYNC SUMMARY
================================================================================
Total files downloaded: 16

✓ SYNC COMPLETE (merge skipped)
Downloaded files: /Users/jmanning/mapper.io/embeddings
```

**What to Verify:**
- All 16 files downloaded successfully
- Each file ~150MB
- No error messages
- "✓ SYNC COMPLETE" at end

**How to Detect Failure:**
- "✗ Error" messages during download
- "Connection refused"
- "Timeout" errors
- File count < 16

**What to Do If It Fails:**

**Issue: Connection timeout during download**
```bash
# Network may be unstable
# Retry sync (script will skip already downloaded files)
python3 sync_and_merge_embeddings.py --sync-only
```

**Issue: Some files failed to download**
```bash
# Check which files are missing
ls -lh embeddings/cluster*.pkl | wc -l
# If < 16, some missing

# Retry sync
python3 sync_and_merge_embeddings.py --sync-only

# If still failing, manual download:
scp user@tensor01:~/mapper_embeddings/embeddings/cluster0_gpu3.pkl embeddings/
```

**Issue: Downloaded files are corrupted (wrong size)**
```bash
# Check file sizes
ls -lh embeddings/cluster*.pkl

# If any file is < 50MB or > 500MB, likely corrupted
# Delete and re-download
rm embeddings/cluster0_gpu3.pkl
python3 sync_and_merge_embeddings.py --sync-only
```

---

**Verify downloads:**
```bash
echo "Verifying downloaded files..."
ls -lh embeddings/cluster*.pkl
echo ""
echo "File count:"
ls embeddings/cluster*.pkl | wc -l
echo "Expected: 16"
echo ""
echo "Total size:"
du -sh embeddings/
echo "Expected: ~2.4GB"
```

**Expected Output:**
```
Verifying downloaded files...
-rw-r--r--  1 jmanning  staff   152M Nov 14 15:47 cluster0_gpu0.pkl
-rw-r--r--  1 jmanning  staff   152M Nov 14 15:47 cluster0_gpu1.pkl
[... 14 more files ...]

File count:
16
Expected: 16

Total size:
2.4G    embeddings/
Expected: ~2.4GB
```

---

### Phase 3: Merge Embeddings

**Command:**
```bash
python3 sync_and_merge_embeddings.py --merge-only
```

**Expected Output:**
```
================================================================================
EMBEDDING SYNC & MERGE
================================================================================
Started: 2025-11-14 15:50:00
Working directory: /Users/jmanning/mapper.io

Embeddings directory: /Users/jmanning/mapper.io/embeddings

================================================================================
LOADING EXISTING FILES
================================================================================

Found 16 local embedding files

Loading Wikipedia articles...
✓ Loaded 250,000 Wikipedia articles

================================================================================
MERGE PHASE
================================================================================

================================================================================
MERGING EMBEDDINGS
================================================================================

Loading 16 checkpoint files...

  [1/16] cluster0_gpu0.pkl... ✓ (15,625 items, dim=768)
  [2/16] cluster0_gpu1.pkl... ✓ (15,625 items, dim=768)
  [3/16] cluster0_gpu2.pkl... ✓ (15,625 items, dim=768)
  [4/16] cluster0_gpu3.pkl... ✓ (15,625 items, dim=768)
  [5/16] cluster0_gpu4.pkl... ✓ (15,625 items, dim=768)
  [6/16] cluster0_gpu5.pkl... ✓ (15,625 items, dim=768)
  [7/16] cluster0_gpu6.pkl... ✓ (15,625 items, dim=768)
  [8/16] cluster0_gpu7.pkl... ✓ (15,625 items, dim=768)
  [9/16] cluster1_gpu0.pkl... ✓ (15,625 items, dim=768)
  [10/16] cluster1_gpu1.pkl... ✓ (15,625 items, dim=768)
  [11/16] cluster1_gpu2.pkl... ✓ (15,625 items, dim=768)
  [12/16] cluster1_gpu3.pkl... ✓ (15,625 items, dim=768)
  [13/16] cluster1_gpu4.pkl... ✓ (15,625 items, dim=768)
  [14/16] cluster1_gpu5.pkl... ✓ (15,625 items, dim=768)
  [15/16] cluster1_gpu6.pkl... ✓ (15,625 items, dim=768)
  [16/16] cluster1_gpu7.pkl... ✓ (15,625 items, dim=768)

================================================================================
VERIFYING INDEX RANGES
================================================================================

  ✓ Cluster 0, GPU 0: 0 - 15,625 (15,625 items)
  ✓ Cluster 0, GPU 1: 15,625 - 31,250 (15,625 items)
  ✓ Cluster 0, GPU 2: 31,250 - 46,875 (15,625 items)
  ✓ Cluster 0, GPU 3: 46,875 - 62,500 (15,625 items)
  ✓ Cluster 0, GPU 4: 62,500 - 78,125 (15,625 items)
  ✓ Cluster 0, GPU 5: 78,125 - 93,750 (15,625 items)
  ✓ Cluster 0, GPU 6: 93,750 - 109,375 (15,625 items)
  ✓ Cluster 0, GPU 7: 109,375 - 125,000 (15,625 items)
  ✓ Cluster 1, GPU 0: 125,000 - 140,625 (15,625 items)
  ✓ Cluster 1, GPU 1: 140,625 - 156,250 (15,625 items)
  ✓ Cluster 1, GPU 2: 156,250 - 171,875 (15,625 items)
  ✓ Cluster 1, GPU 3: 171,875 - 187,500 (15,625 items)
  ✓ Cluster 1, GPU 4: 187,500 - 203,125 (15,625 items)
  ✓ Cluster 1, GPU 5: 203,125 - 218,750 (15,625 items)
  ✓ Cluster 1, GPU 6: 218,750 - 234,375 (15,625 items)
  ✓ Cluster 1, GPU 7: 234,375 - 250,000 (15,625 items)

  ✓ No gaps or overlaps
  ✓ Total items across all chunks: 250,010

================================================================================
CONCATENATING EMBEDDINGS
================================================================================

  Shape: (250010, 768)
  Items: 250,010
  Dimensions: 768

  Extracting first 250,000 items (articles only, excluding questions)...
  ✓ Excluded 10 question embeddings

================================================================================
QUALITY CHECKS
================================================================================

  Shape: (250000, 768)
  Dtype: float32
  Embedding norms:
    Mean: 1.2347
    Std: 0.3421
    Min: 0.2156
    Max: 3.4521
  ✓ No NaN or Inf values
  ✓ Embedding count matches article count

================================================================================
PREPARING ARTICLE METADATA
================================================================================

  ✓ Extracted 250,000 article titles

================================================================================
SAVING MERGED EMBEDDINGS
================================================================================

Saving to /Users/jmanning/mapper.io/embeddings/wikipedia_merged.pkl...
  ✓ Saved 250,000 article embeddings
  File size: 1,907.35 MB
  Timestamp: 2025-11-14T15:52:34.123456

================================================================================
✓ MERGE COMPLETE!
================================================================================

Output file: /Users/jmanning/mapper.io/embeddings/wikipedia_merged.pkl
Total embeddings: 250,000
Shape: (250000, 768)
Completed: 2025-11-14 15:52:34

Next steps:
  1. Generate UMAP projections using the merged embeddings
  2. Create knowledge map visualization
```

**What to Verify:**
- All 16 files loaded successfully
- No gaps in index ranges (continuous 0 - 250,010)
- Extracted exactly 250,000 articles (excluded 10 questions)
- No NaN or Inf values
- Output file created (~1.9GB)
- "✓ MERGE COMPLETE!" at end

**How to Detect Failure:**
- "✗ ERROR" messages
- "Gap detected" in index ranges
- "Size mismatch" errors
- NaN or Inf values found
- File not created

**What to Do If It Fails:**

**Issue: Gap detected in index ranges**
```
✗ ERROR: Gap detected!
  Expected index: 125000
  Got index: 125010
```

**This means:** One worker's range doesn't match expected

**Recovery:**
```bash
# Identify which cluster/GPU has wrong range
# Worker should have processed indices 125,000-140,625
# But shows 125,010-140,635 instead

# Need to regenerate that worker's embeddings
# Or manually adjust indices (advanced)

# Simplest: Re-run that specific worker
ssh user@tensor02
cd ~/mapper_embeddings

# Delete bad output
rm embeddings/cluster1_gpu0.pkl

# Re-run worker
export CUDA_VISIBLE_DEVICES=0
python generate_embeddings_gpu.py --cluster 1 --gpu 0 --total-clusters 2

# Wait for completion, then re-download
exit
rm embeddings/cluster1_gpu0.pkl
python3 sync_and_merge_embeddings.py --sync-only --clusters "tensor02"
python3 sync_and_merge_embeddings.py --merge-only
```

**Issue: NaN or Inf values found**
```
✗ ERROR: Found NaN or Inf values!
  NaN: True
  Inf: False
```

**This means:** Some embeddings are corrupted

**Recovery:**
```bash
# Identify which file has NaN values
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
        print(f"{f.name}: NaN={has_nan}, Inf={has_inf}")
        print(f"  Cluster {data['cluster_id']}, GPU {data['gpu_id']}")
EOF

# Regenerate the corrupted file (same as gap recovery above)
```

**Issue: Merge runs out of memory**
```
MemoryError: Unable to allocate array
```

**Recovery:**
```bash
# Merge requires ~4GB RAM (2x file size)
# Close other applications
# Or use a machine with more RAM

# If still failing, merge in chunks (advanced):
# Split into 2 batches of 8 files each
# Merge separately, then combine
```

---

### Phase 4: Validate Merged File

**Command:**
```bash
python3 << 'EOF'
import pickle
import numpy as np
from pathlib import Path

print("="*60)
print("VALIDATING MERGED EMBEDDINGS")
print("="*60)

merged_file = Path('embeddings/wikipedia_merged.pkl')

if not merged_file.exists():
    print(f"✗ File not found: {merged_file}")
    exit(1)

print(f"\nFile: {merged_file}")
print(f"Size: {merged_file.stat().st_size / 1e9:.2f} GB")

print(f"\nLoading merged file...")
with open(merged_file, 'rb') as f:
    data = pickle.load(f)

print(f"✓ File loaded successfully")

# Check structure
print(f"\nFile structure:")
for key in data.keys():
    if key == 'embeddings':
        print(f"  - embeddings: shape {data[key].shape}")
    elif key == 'articles':
        print(f"  - articles: {len(data[key]):,} items")
    else:
        print(f"  - {key}: {str(data[key])[:50]}")

# Validate embeddings
embeddings = data['embeddings']
print(f"\nEmbedding validation:")
print(f"  Shape: {embeddings.shape}")
print(f"  Expected: (250000, 768)")
print(f"  Match: {'✓' if embeddings.shape == (250000, 768) else '✗'}")

# Validate norms
norms = np.linalg.norm(embeddings, axis=1)
print(f"\nNorm statistics:")
print(f"  Mean: {norms.mean():.4f}")
print(f"  Std: {norms.std():.4f}")
print(f"  Min: {norms.min():.4f}")
print(f"  Max: {norms.max():.4f}")

# Check for issues
has_nan = np.isnan(embeddings).any()
has_inf = np.isinf(embeddings).any()
print(f"\nQuality checks:")
print(f"  NaN values: {'✗ FOUND' if has_nan else '✓ None'}")
print(f"  Inf values: {'✗ FOUND' if has_inf else '✓ None'}")

# Validate articles
articles = data['articles']
print(f"\nArticle metadata:")
print(f"  Count: {len(articles):,}")
print(f"  Expected: 250,000")
print(f"  Match: {'✓' if len(articles) == 250000 else '✗'}")

# Sample articles
print(f"\nSample articles:")
for i in [0, 1000, 100000, 249999]:
    article = articles[i]
    title = article.get('title', 'NO TITLE')
    print(f"  [{i:6d}] {title[:50]}")

# Overall validation
print(f"\n{'='*60}")
if (embeddings.shape == (250000, 768) and
    len(articles) == 250000 and
    not has_nan and
    not has_inf):
    print("✓ VALIDATION PASSED")
    print("Merged file is ready for use.")
else:
    print("✗ VALIDATION FAILED")
    print("Issues detected above.")
print("="*60)

EOF
```

**Expected Output:**
```
============================================================
VALIDATING MERGED EMBEDDINGS
============================================================

File: embeddings/wikipedia_merged.pkl
Size: 1.91 GB

Loading merged file...
✓ File loaded successfully

File structure:
  - embeddings: shape (250000, 768)
  - articles: 250,000 items
  - total_articles: 250000
  - embedding_dim: 768
  - model: google/embeddinggemma-300m
  - timestamp: 2025-11-14T15:52:34.123456

Embedding validation:
  Shape: (250000, 768)
  Expected: (250000, 768)
  Match: ✓

Norm statistics:
  Mean: 1.2347
  Std: 0.3421
  Min: 0.2156
  Max: 3.4521

Quality checks:
  NaN values: ✓ None
  Inf values: ✓ None

Article metadata:
  Count: 250,000
  Expected: 250,000
  Match: ✓

Sample articles:
  [     0] Albert Einstein
  [  1000] Quantum mechanics
  [100000] Machine learning
  [249999] Neural networks

============================================================
✓ VALIDATION PASSED
Merged file is ready for use.
============================================================
```

**What to Verify:**
- File size ~1.9 GB
- Shape exactly (250000, 768)
- No NaN or Inf values
- Article count exactly 250,000
- Sample articles have reasonable titles

**If Validation Fails:**
- Check errors in output
- May need to re-merge
- Or regenerate specific workers

---

### Phase 5: Backup and Cleanup

**Create backup:**
```bash
# Create backup directory
mkdir -p embeddings/backups

# Backup merged file with timestamp
cp embeddings/wikipedia_merged.pkl "embeddings/backups/wikipedia_merged_$(date +%Y%m%d_%H%M%S).pkl"

echo "✓ Backup created"
ls -lh embeddings/backups/
```

**Optional: Clean up individual chunks**
```bash
# Keep individual GPU files for debugging
# Or delete to save space (after successful validation)

# To keep:
echo "Keeping individual GPU files in embeddings/"

# To delete (after backup):
# rm embeddings/cluster*.pkl
# echo "✓ Individual GPU files deleted (merged file backed up)"
```

**Optional: Clean up remote clusters**
```bash
# After successful download and validation
# Free up space on clusters

for cluster in tensor01 tensor02; do
    echo "Cleaning up $cluster..."
    ssh user@$cluster "rm ~/mapper_embeddings/embeddings/*.pkl; rm ~/mapper_embeddings/logs/*.log"
done

echo "✓ Remote clusters cleaned up"
```

---

## Success Criteria

### Final Checklist

Run this comprehensive verification:

```bash
cat << 'EOF' > /tmp/final_check.sh
#!/bin/bash

echo "=================================================================="
echo "FINAL SUCCESS CRITERIA CHECK"
echo "=================================================================="
echo ""

cd /Users/jmanning/mapper.io

PASS=0
FAIL=0

# Check 1: Merged file exists
if [ -f "embeddings/wikipedia_merged.pkl" ]; then
    echo "✓ 1. Merged file exists"
    ((PASS++))
else
    echo "✗ 1. Merged file MISSING"
    ((FAIL++))
fi

# Check 2: File size is correct
SIZE=$(stat -f%z "embeddings/wikipedia_merged.pkl" 2>/dev/null || echo 0)
if [ $SIZE -gt 1800000000 ] && [ $SIZE -lt 2100000000 ]; then
    echo "✓ 2. File size correct (~1.9 GB)"
    ((PASS++))
else
    echo "✗ 2. File size wrong: $SIZE bytes"
    ((FAIL++))
fi

# Check 3: File structure is valid
python3 << 'PYEOF'
import pickle
import sys
try:
    data = pickle.load(open('embeddings/wikipedia_merged.pkl', 'rb'))
    if isinstance(data, dict) and 'embeddings' in data and 'articles' in data:
        print("✓ 3. File structure valid")
        sys.exit(0)
    else:
        print("✗ 3. File structure invalid")
        sys.exit(1)
except Exception as e:
    print(f"✗ 3. Cannot load file: {e}")
    sys.exit(1)
PYEOF
if [ $? -eq 0 ]; then ((PASS++)); else ((FAIL++)); fi

# Check 4: Embedding count is 250,000
python3 << 'PYEOF'
import pickle
import sys
data = pickle.load(open('embeddings/wikipedia_merged.pkl', 'rb'))
count = len(data['embeddings'])
if count == 250000:
    print(f"✓ 4. Embedding count correct: {count:,}")
    sys.exit(0)
else:
    print(f"✗ 4. Embedding count wrong: {count:,} (expected 250,000)")
    sys.exit(1)
PYEOF
if [ $? -eq 0 ]; then ((PASS++)); else ((FAIL++)); fi

# Check 5: Embedding dimension is 768
python3 << 'PYEOF'
import pickle
import sys
data = pickle.load(open('embeddings/wikipedia_merged.pkl', 'rb'))
dim = data['embeddings'].shape[1]
if dim == 768:
    print(f"✓ 5. Embedding dimension correct: {dim}")
    sys.exit(0)
else:
    print(f"✗ 5. Embedding dimension wrong: {dim} (expected 768)")
    sys.exit(1)
PYEOF
if [ $? -eq 0 ]; then ((PASS++)); else ((FAIL++)); fi

# Check 6: No NaN or Inf values
python3 << 'PYEOF'
import pickle
import numpy as np
import sys
data = pickle.load(open('embeddings/wikipedia_merged.pkl', 'rb'))
has_nan = np.isnan(data['embeddings']).any()
has_inf = np.isinf(data['embeddings']).any()
if not has_nan and not has_inf:
    print("✓ 6. No NaN or Inf values")
    sys.exit(0)
else:
    print(f"✗ 6. Contains NaN ({has_nan}) or Inf ({has_inf})")
    sys.exit(1)
PYEOF
if [ $? -eq 0 ]; then ((PASS++)); else ((FAIL++)); fi

# Check 7: Article metadata complete
python3 << 'PYEOF'
import pickle
import sys
data = pickle.load(open('embeddings/wikipedia_merged.pkl', 'rb'))
articles = data['articles']
if len(articles) == 250000:
    # Check first few have titles
    has_titles = all('title' in articles[i] for i in range(10))
    if has_titles:
        print(f"✓ 7. Article metadata complete: {len(articles):,} articles")
        sys.exit(0)
    else:
        print("✗ 7. Article metadata missing titles")
        sys.exit(1)
else:
    print(f"✗ 7. Article count wrong: {len(articles):,}")
    sys.exit(1)
PYEOF
if [ $? -eq 0 ]; then ((PASS++)); else ((FAIL++)); fi

# Check 8: Embedding norms are reasonable
python3 << 'PYEOF'
import pickle
import numpy as np
import sys
data = pickle.load(open('embeddings/wikipedia_merged.pkl', 'rb'))
norms = np.linalg.norm(data['embeddings'], axis=1)
mean_norm = norms.mean()
if 0.5 < mean_norm < 5.0:  # Reasonable range
    print(f"✓ 8. Embedding norms reasonable (mean: {mean_norm:.4f})")
    sys.exit(0)
else:
    print(f"✗ 8. Embedding norms unusual (mean: {mean_norm:.4f})")
    sys.exit(1)
PYEOF
if [ $? -eq 0 ]; then ((PASS++)); else ((FAIL++)); fi

# Check 9: Backup exists
if ls embeddings/backups/wikipedia_merged_*.pkl 1> /dev/null 2>&1; then
    echo "✓ 9. Backup created"
    ((PASS++))
else
    echo "⚠ 9. No backup found (optional)"
    # Not a failure, just warning
fi

# Check 10: Metadata fields present
python3 << 'PYEOF'
import pickle
import sys
data = pickle.load(open('embeddings/wikipedia_merged.pkl', 'rb'))
required = ['model', 'timestamp', 'embedding_dim', 'total_articles']
present = all(k in data for k in required)
if present:
    print(f"✓ 10. Metadata fields present: {', '.join(required)}")
    sys.exit(0)
else:
    missing = [k for k in required if k not in data]
    print(f"✗ 10. Missing metadata: {', '.join(missing)}")
    sys.exit(1)
PYEOF
if [ $? -eq 0 ]; then ((PASS++)); else ((FAIL++)); fi

echo ""
echo "=================================================================="
echo "RESULTS"
echo "=================================================================="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✓✓✓ ALL CHECKS PASSED ✓✓✓"
    echo ""
    echo "SUCCESS: Wikipedia embedding generation complete!"
    echo ""
    echo "Output file: embeddings/wikipedia_merged.pkl"
    echo "  - 250,000 Wikipedia articles"
    echo "  - 768-dimensional embeddings"
    echo "  - Model: google/embeddinggemma-300m"
    echo "  - File size: ~1.9 GB"
    echo ""
    echo "Next steps:"
    echo "  1. Generate UMAP projections"
    echo "  2. Build knowledge map visualization"
    echo "  3. Deploy interactive demo"
    echo ""
    exit 0
else
    echo "✗✗✗ SOME CHECKS FAILED ✗✗✗"
    echo ""
    echo "Review failures above and fix issues."
    echo "Re-run this script to verify fixes."
    echo ""
    exit 1
fi
EOF

chmod +x /tmp/final_check.sh
/tmp/final_check.sh
```

**Expected Output (Success):**
```
==================================================================
FINAL SUCCESS CRITERIA CHECK
==================================================================

✓ 1. Merged file exists
✓ 2. File size correct (~1.9 GB)
✓ 3. File structure valid
✓ 4. Embedding count correct: 250,000
✓ 5. Embedding dimension correct: 768
✓ 6. No NaN or Inf values
✓ 7. Article metadata complete: 250,000 articles
✓ 8. Embedding norms reasonable (mean: 1.2347)
✓ 9. Backup created
✓ 10. Metadata fields present: model, timestamp, embedding_dim, total_articles

==================================================================
RESULTS
==================================================================
Passed: 10
Failed: 0

✓✓✓ ALL CHECKS PASSED ✓✓✓

SUCCESS: Wikipedia embedding generation complete!

Output file: embeddings/wikipedia_merged.pkl
  - 250,000 Wikipedia articles
  - 768-dimensional embeddings
  - Model: google/embeddinggemma-300m
  - File size: ~1.9 GB

Next steps:
  1. Generate UMAP projections
  2. Build knowledge map visualization
  3. Deploy interactive demo
```

---

### Project Completion Criteria

The project is considered **COMPLETE** when:

1. **All 10 checks pass** in final verification
2. **Backup created** in embeddings/backups/
3. **Documentation updated** with:
   - Actual execution time
   - Any issues encountered and resolved
   - Final file checksums for verification
4. **Ready for next phase**: UMAP projection

---

### Post-Completion Tasks

**Document execution:**
```bash
cat << EOF > notes/execution_report_$(date +%Y%m%d).md
# Execution Report - $(date +%Y-%m-%d)

## Summary
- **Start time:** [record from launch]
- **End time:** $(date +%H:%M:%S)
- **Total duration:** [calculate]
- **Output file:** embeddings/wikipedia_merged.pkl
- **File size:** $(ls -lh embeddings/wikipedia_merged.pkl | awk '{print $5}')
- **Status:** SUCCESS

## Metrics
- Wikipedia articles: 250,000
- Embedding dimension: 768
- Model: google/embeddinggemma-300m
- Clusters used: tensor01, tensor02
- GPUs used: 16 (8 per cluster)
- Items/sec: [record from monitor]

## Issues Encountered
[List any failures and how they were resolved]

## Next Steps
1. Generate UMAP projections
2. Build knowledge map visualization
3. Deploy demo

EOF

echo "✓ Execution report created: notes/execution_report_$(date +%Y%m%d).md"
```

**Commit to git (optional):**
```bash
# Add merged file to .gitignore (too large for git)
echo "embeddings/wikipedia_merged.pkl" >> .gitignore
echo "embeddings/backups/" >> .gitignore

# Commit documentation
git add notes/execution_report_*.md
git commit -m "Complete Wikipedia embedding generation

- Generated 250,000 article embeddings
- Used google/embeddinggemma-300m on 16 GPUs
- Output: embeddings/wikipedia_merged.pkl (1.9GB)
- Ready for UMAP projection phase"

git push
```

---

## Quick Reference Card

### Emergency Commands

**Stop everything:**
```bash
# Kill all workers on both clusters
ssh user@tensor01 "killall python3; screen -wipe"
ssh user@tensor02 "killall python3; screen -wipe"
```

**Restart everything:**
```bash
./launch_distributed.sh --clusters "tensor01 tensor02"
python3 monitor_clusters.py --interval 30
```

**Check cluster status:**
```bash
ssh user@tensor01 "screen -ls; tail -10 ~/mapper_embeddings/logs/gpu0.log"
```

**Download partial results:**
```bash
python3 sync_and_merge_embeddings.py --sync-only
```

---

### Contact Information

If critical issues arise:
- Check CLAUDE.md for project-specific instructions
- Review notes/ directory for session history
- Consult distributed-gpu-plan.md for architecture details

---

## Appendix: File Locations

```
/Users/jmanning/mapper.io/
├── wikipedia.pkl                      # Input: 250K articles (752MB)
├── .credentials/
│   ├── tensor01.credentials           # Cluster 1 SSH creds
│   ├── tensor02.credentials           # Cluster 2 SSH creds
│   └── hf.token                       # HuggingFace token
├── generate_embeddings_gpu.py         # GPU worker script
├── launch_distributed.sh              # Launch script
├── monitor_clusters.py                # Monitoring script
├── sync_and_merge_embeddings.py       # Download & merge script
├── embeddings/
│   ├── cluster0_gpu0.pkl              # Downloaded chunks (temporary)
│   ├── cluster0_gpu1.pkl
│   ├── ... (16 total)
│   ├── wikipedia_merged.pkl           # Final output (1.9GB)
│   └── backups/
│       └── wikipedia_merged_*.pkl     # Timestamped backups
└── notes/
    └── execution_report_*.md          # Execution documentation
```

---

## Appendix: Expected Timeline

With 16 GPUs (8 per cluster) @ 50-100 items/sec per GPU:

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Pre-flight checks | 5-10 min | 0:10 |
| Launch workers | 2-3 min | 0:13 |
| Model loading | 1-2 min | 0:15 |
| Embedding generation | 3-6 min | 0:21 |
| Download files | 5-10 min | 0:31 |
| Merge & validate | 2-3 min | 0:34 |
| **Total** | **~20-35 minutes** | **0:35** |

Actual time may vary based on:
- Network speed (affects upload/download)
- GPU performance (A6000 vs other models)
- Cluster load (other users)
- Model download time (first run)

---

**END OF EXECUTION PLAN**
