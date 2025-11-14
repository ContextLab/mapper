# Quick Start Guide - sync_and_merge_embeddings.py

## Installation

```bash
# Install required dependencies
pip install paramiko numpy

# Or with all optional dependencies
pip install paramiko numpy scipy scikit-learn
```

## Setup (One-time)

### 1. Create Credentials Directory

```bash
mkdir -p .credentials
```

### 2. Add Cluster Credentials

Create `.credentials/tensor01.credentials`:
```json
{
  "address": "tensor01.example.com",
  "username": "your_username",
  "password": "your_password"
}
```

Create `.credentials/tensor02.credentials`:
```json
{
  "address": "tensor02.example.com",
  "username": "your_username",
  "password": "your_password"
}
```

### 3. Verify Wikipedia Articles File

```bash
ls -lh wikipedia.pkl
# Should be present with ~250,000 articles
```

## Common Workflows

### Full Sync & Merge (Recommended)

```bash
python sync_and_merge_embeddings.py
```

**Time:** 15-35 minutes
**Output:** `embeddings/wikipedia_merged.pkl`

### Two-Phase Workflow (Parallel Processing)

Phase 1 - Download (can run in background):
```bash
python sync_and_merge_embeddings.py --sync-only
# Takes 10-30 minutes
```

Phase 2 - Merge (on same or different machine):
```bash
python sync_and_merge_embeddings.py --merge-only
# Takes 2-3 minutes
```

### Selective Sync

Sync from specific cluster:
```bash
# Sync only tensor01
python sync_and_merge_embeddings.py --clusters "tensor01" --sync-only

# Then merge
python sync_and_merge_embeddings.py --merge-only
```

### Custom Output Location

```bash
python sync_and_merge_embeddings.py --output "backups/embeddings_2024-11-14.pkl"
```

## Monitoring Progress

### During Sync
```
SYNCING FROM TENSOR01
Output directory: /path/to/embeddings
Remote directory: /home/user/mapper_embeddings/embeddings

Connecting to tensor01.example.com...
✓ Connected
Found 8 embedding files

  [1/8] cluster1_gpu0.pkl... ✓ (150.23 MB)
  [2/8] cluster1_gpu1.pkl... ✓ (150.18 MB)
  ...
```

### During Merge
```
MERGING EMBEDDINGS
Loading 16 checkpoint files...
  [1/16] cluster1_gpu0.pkl... ✓ (15625 items, dim=768)
  [2/16] cluster1_gpu1.pkl... ✓ (15625 items, dim=768)
  ...

VERIFYING INDEX RANGES
  ✓ Cluster 1, GPU 0: 0 - 15625 (15625 items)
  ✓ Cluster 1, GPU 1: 15625 - 31250 (15625 items)
  ...
  ✓ All chunks are continuous
  ✓ Total items: 250,010

CONCATENATING EMBEDDINGS
  ✓ Extracted first 250,000 embeddings (excluded 10 questions)
  Shape: (250000, 768)
  Items: 250,000

QUALITY CHECKS
  Mean norm: 1.2345
  Std norm: 0.3421
  ✓ No NaN or Inf values

SAVING MERGED EMBEDDINGS
✓ Saved 250,000 article embeddings
File size: 1,907.35 MB
```

## Verification After Merge

### Check File Size
```bash
ls -lh embeddings/wikipedia_merged.pkl
# Should be ~1.9 GB
```

### Inspect Content
```python
import pickle

with open('embeddings/wikipedia_merged.pkl', 'rb') as f:
    data = pickle.load(f)

print(f"Embeddings shape: {data['embeddings'].shape}")        # (250000, 768)
print(f"Number of articles: {len(data['articles'])}")         # 250000
print(f"Model: {data['model']}")                              # google/embeddinggemma-300m
print(f"First article: {data['articles'][0]['title']}")       # Article title
print(f"Timestamp: {data['timestamp']}")                      # When merged

# Check quality metrics
print(f"\nQuality Metrics:")
print(f"  Mean norm: {data['quality_metrics']['mean_norm']:.4f}")
print(f"  Has NaN: {data['quality_metrics']['has_nan']}")
print(f"  Has Inf: {data['quality_metrics']['has_inf']}")
```

## Troubleshooting

### Connection Refused
```
✗ Error: Connection refused
```

**Solution:**
1. Check hostname in credentials: `ping tensor01.example.com`
2. Verify SSH is accessible: `ssh user@tensor01.example.com`
3. Confirm username/password are correct

### Remote Directory Not Found
```
✗ Remote directory not found: /home/username/mapper_embeddings/embeddings
```

**Solution:**
1. SSH to cluster: `ssh user@tensor01.example.com`
2. Check if directory exists: `ls ~/mapper_embeddings/embeddings/`
3. Create directory if needed: `mkdir -p ~/mapper_embeddings/embeddings`

### No Embedding Files Found
```
No embedding files found matching pattern 'cluster*_gpu*.pkl'
```

**Solution:**
- Embeddings generation on cluster not complete yet
- Files have different naming convention
- Check: `ls ~/mapper_embeddings/embeddings/`

### Wikipedia.pkl Missing
```
FileNotFoundError: Wikipedia articles file not found
```

**Solution:**
- Ensure `wikipedia.pkl` exists in project root
- File should have 250,000 articles: 
  ```python
  import pickle
  articles = pickle.load(open('wikipedia.pkl', 'rb'))
  print(len(articles))  # Should be 250,000
  ```

### Gap Detected During Merge
```
✗ ERROR: Gap detected!
  Expected index: 100000
  Got index: 100010
```

**Solution:**
- Worker process had issue generating embeddings
- Investigate checkpoint file on cluster:
  ```bash
  ssh user@tensor01.example.com
  python3 << 'EOF'
  import pickle
  data = pickle.load(open('~/mapper_embeddings/embeddings/cluster1_gpu4.pkl', 'rb'))
  print(f"Range: {data['start_index']} - {data['end_index']}")
  EOF
  ```

## Performance Tips

### Speed Up Sync
1. Check network bandwidth: `iperf3 -c tensor01.example.com`
2. Consider using SSH key instead of password
3. Run sync during off-peak hours

### Reduce Memory Usage During Merge
- If getting out of memory: close other applications
- Peak memory: ~4 GB (2 × 1.9 GB)
- Can't reduce further without reimplementing merge

### Parallelize
```bash
# Terminal 1 - Sync from tensor01
python sync_and_merge_embeddings.py --clusters "tensor01" --sync-only

# Terminal 2 - Sync from tensor02 (while Terminal 1 is running)
python sync_and_merge_embeddings.py --clusters "tensor02" --sync-only

# Then merge both
python sync_and_merge_embeddings.py --merge-only
```

## Next Steps After Merge

1. **Build Knowledge Map**
   ```bash
   python build_wikipedia_knowledge_map_v2.py
   ```

2. **Generate Visualizations**
   - Open `knowledge_map_heatmap.html` in browser
   - Use interactive 2D heatmap for exploration

3. **Analyze Quality**
   - Check embedding norm distributions
   - Verify coverage across topics

4. **Archive**
   ```bash
   # Backup merged file
   cp embeddings/wikipedia_merged.pkl embeddings/backups/wikipedia_merged_2024-11-14.pkl
   ```

## File Locations

```
Project Root/
├── sync_and_merge_embeddings.py    # Main script
├── wikipedia.pkl                   # Input: 250k articles
├── SYNC_AND_MERGE_GUIDE.md         # Full documentation
├── SCRIPT_SUMMARY.md               # Technical details
├── QUICKSTART.md                   # This file
├── .credentials/
│   ├── tensor01.credentials        # Cluster 1 login
│   └── tensor02.credentials        # Cluster 2 login
└── embeddings/
    ├── cluster1_gpu0.pkl           # Downloaded (temporary)
    ├── cluster1_gpu1.pkl
    ├── ... (16 total)
    └── wikipedia_merged.pkl        # Output (final)
```

## Command Reference

| Command | Purpose |
|---------|---------|
| `python sync_and_merge_embeddings.py` | Full sync + merge |
| `python sync_and_merge_embeddings.py --sync-only` | Download only |
| `python sync_and_merge_embeddings.py --merge-only` | Merge existing files |
| `python sync_and_merge_embeddings.py --clusters "tensor01"` | Sync single cluster |
| `python sync_and_merge_embeddings.py --output "path/file.pkl"` | Custom output |
| `python sync_and_merge_embeddings.py -h` | Show help |

## Expected Output Files

After successful merge:
- **Location:** `embeddings/wikipedia_merged.pkl`
- **Size:** ~1.9 GB
- **Format:** Python pickle with dict containing:
  - `embeddings`: (250000, 768) float32 array
  - `articles`: List of 250,000 dicts with title, id, url
  - `model`: 'google/embeddinggemma-300m'
  - `timestamp`: ISO format merge timestamp
  - `quality_metrics`: Norm statistics
  - `chunk_info`: Per-GPU source metadata

## Key Metrics to Monitor

During execution, watch for:
- Download speeds (MB/s per file)
- File sizes (should be ~150-200 MB each)
- Embedding norms (should have reasonable mean ~1.2)
- No NaN or Inf values in embeddings
- Correct article count (250,000)
- Final file size ~1.9 GB

