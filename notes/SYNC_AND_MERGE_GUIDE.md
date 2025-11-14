# Sync and Merge Embeddings Guide

## Overview

The `sync_and_merge_embeddings.py` script automates the process of downloading embedding checkpoint files from remote GPU clusters and merging them into a single consolidated embeddings file for further processing (e.g., UMAP projection, visualization).

## Pipeline

```
Remote Clusters:
  tensor01: cluster1_gpu0.pkl, cluster1_gpu1.pkl, ..., cluster1_gpu7.pkl
  tensor02: cluster2_gpu0.pkl, cluster2_gpu1.pkl, ..., cluster2_gpu7.pkl
           ↓ (SFTP download)
Local Machine: embeddings/cluster*.pkl
           ↓ (merge & validate)
Output: embeddings/wikipedia_merged.pkl
```

## Prerequisites

### 1. Python Dependencies

```bash
pip install paramiko numpy scipy scikit-learn
```

- **paramiko**: SFTP/SSH connectivity (preferred method)
- **numpy**: Array operations and validation
- **scipy/scikit-learn**: Optional for any processing

### 2. Credentials Setup

Create credential files in `.credentials/` directory:

**File:** `.credentials/tensor01.credentials`
```json
{
  "address": "tensor01.example.com",
  "username": "myuser",
  "password": "mypassword"
}
```

**File:** `.credentials/tensor02.credentials`
```json
{
  "address": "tensor02.example.com",
  "username": "myuser",
  "password": "mypassword"
}
```

**Format:**
- `address`: Hostname or IP of the cluster (required)
- `username`: SSH username (required)
- `password`: SSH password (required)

### 3. Wikipedia Articles File

The script requires `wikipedia.pkl` (250,000 articles) to extract article metadata and titles.

- **Location:** Project root directory
- **Expected size:** ~250,000 article dictionaries
- **Each article contains:** `id`, `title`, `url`, `text`

## Usage

### Basic Syntax

```bash
python sync_and_merge_embeddings.py [OPTIONS]
```

### Command Examples

#### 1. Sync and Merge (Default)
Downloads all embedding files from both clusters and immediately merges them:

```bash
python sync_and_merge_embeddings.py
```

**What happens:**
- Connects to tensor01 and tensor02
- Downloads all `cluster*_gpu*.pkl` files
- Verifies index ranges
- Extracts article metadata
- Saves `embeddings/wikipedia_merged.pkl`

#### 2. Sync Only (No Merge)
Download files from clusters without merging:

```bash
python sync_and_merge_embeddings.py --sync-only
```

**Use case:** Download files for inspection or parallel processing

#### 3. Merge Only (Existing Files)
Merge already-downloaded embedding files:

```bash
python sync_and_merge_embeddings.py --merge-only
```

**Use case:** Retry merge if sync already completed or files were pre-downloaded

#### 4. Specific Clusters
Sync from only certain clusters:

```bash
# Only tensor01
python sync_and_merge_embeddings.py --clusters "tensor01"

# Only tensor02
python sync_and_merge_embeddings.py --clusters "tensor02"

# Both (default, explicit)
python sync_and_merge_embeddings.py --clusters "tensor01 tensor02"
```

#### 5. Custom Output Path
Save merged file to different location:

```bash
python sync_and_merge_embeddings.py --output "custom_path/my_embeddings.pkl"
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--sync-only` | Only download, skip merge | False |
| `--merge-only` | Only merge existing files, skip download | False |
| `--clusters CLUSTERS` | Space-separated cluster names | "tensor01 tensor02" |
| `--output OUTPUT` | Output file path | "embeddings/wikipedia_merged.pkl" |
| `-h, --help` | Show help message | - |

## Output Format

The merged embeddings file (`wikipedia_merged.pkl`) is a Python pickle containing a dictionary with:

```python
{
    # Core data (required)
    'embeddings': np.ndarray,        # Shape: (250000, 768)
    'articles': List[Dict],          # 250,000 article metadata
    'total_articles': int,           # 250,000
    'embedding_dim': int,            # 768
    'model': str,                    # 'google/embeddinggemma-300m'
    'timestamp': str,                # ISO format timestamp

    # Metadata & diagnostics
    'shape': Tuple[int, int],        # (250000, 768)
    'quality_metrics': Dict,         # Norm statistics
    'chunk_info': List[Dict]         # Per-GPU metadata
}
```

### Each Article Entry

```python
{
    'title': str,    # Wikipedia article title
    'id': str,       # Wikipedia article ID
    'url': str       # Wikipedia URL
}
```

### Quality Metrics

```python
{
    'shape': (250000, 768),
    'dtype': 'float32',
    'min_norm': 0.0523,
    'max_norm': 2.1847,
    'mean_norm': 1.2345,
    'std_norm': 0.3421,
    'has_nan': False,
    'has_inf': False
}
```

### Chunk Information

```python
[
    {
        'cluster_id': 1,
        'gpu_id': 0,
        'start_index': 0,
        'end_index': 15625,
        'filepath': 'cluster1_gpu0.pkl'
    },
    # ... one entry per GPU (16 total for 2 clusters × 8 GPUs)
]
```

## Loading and Using the Merged File

### Basic Loading

```python
import pickle
import numpy as np

# Load the merged embeddings
with open('embeddings/wikipedia_merged.pkl', 'rb') as f:
    data = pickle.load(f)

embeddings = data['embeddings']      # Shape: (250000, 768)
articles = data['articles']          # List of 250,000 dicts
timestamps = data['timestamp']       # When merged

print(f"Loaded {len(articles)} article embeddings")
print(f"Shape: {embeddings.shape}")
```

### Using with UMAP

```python
from umap import UMAP

# Load embeddings
with open('embeddings/wikipedia_merged.pkl', 'rb') as f:
    data = pickle.load(f)

embeddings = data['embeddings']

# Project to 2D using UMAP
reducer = UMAP(n_components=2, metric='cosine')
projected = reducer.fit_transform(embeddings)

print(f"Projected shape: {projected.shape}")  # (250000, 2)
```

### Accessing Metadata

```python
with open('embeddings/wikipedia_merged.pkl', 'rb') as f:
    data = pickle.load(f)

# Article information
articles = data['articles']
print(f"First article: {articles[0]['title']}")

# Quality metrics
metrics = data['quality_metrics']
print(f"Mean embedding norm: {metrics['mean_norm']:.4f}")

# Source information
chunks = data['chunk_info']
print(f"Downloaded from {len(chunks)} GPUs")
for chunk in chunks:
    print(f"  Cluster {chunk['cluster_id']}, GPU {chunk['gpu_id']}: "
          f"{chunk['start_index']:,} - {chunk['end_index']:,}")
```

## Data Processing Details

### Index Range Verification

During merge, the script validates that:
- No gaps exist between chunks (end_index of chunk N = start_index of chunk N+1)
- No overlaps exist (all ranges are disjoint)
- Total items equals expected count (250,010 items from workers)
- Only first 250,000 are kept (Wikipedia articles only)
- Last 10 are excluded (quiz questions)

Example verification output:
```
Cluster 1, GPU 0: 0 - 15625 (15625 items)
Cluster 1, GPU 1: 15625 - 31250 (15625 items)
Cluster 1, GPU 2: 31250 - 46875 (15625 items)
...
Cluster 2, GPU 7: 234375 - 250010 (15635 items)

Total items across all chunks: 250,010
✓ No gaps or overlaps
✓ Extracted first 250,000 embeddings (excluded 10 questions)
```

### Quality Checks

The merge process performs several quality checks:

1. **Index Continuity**: Ensures no gaps or overlaps
2. **Dimension Verification**: Confirms all embeddings are 768-dimensional
3. **Article Count**: Validates 250,000 articles included
4. **Embedding Norms**: Calculates min/max/mean/std of L2 norms
5. **Invalid Values**: Checks for NaN and Inf values
6. **Shape Consistency**: Verifies final shape is (250000, 768)

If any check fails, the merge is aborted with detailed error messages.

## Troubleshooting

### 1. Credentials Error

**Error:** `FileNotFoundError: Credentials file not found: .credentials/tensor01.credentials`

**Solution:**
```bash
# Create .credentials directory
mkdir -p .credentials

# Create credential files with correct format
echo '{"address": "hostname", "username": "user", "password": "pass"}' > .credentials/tensor01.credentials
```

### 2. Connection Timeout

**Error:** `Timeout connecting to address`

**Possible causes:**
- Network connectivity issue
- Hostname incorrect
- Credentials invalid
- Firewall blocking connection

**Solution:**
- Verify credentials in `.credentials/` file
- Test connection manually: `ssh user@hostname`
- Check network connectivity: `ping hostname`

### 3. Remote Directory Not Found

**Error:** `Remote directory not found: /home/username/mapper_embeddings/embeddings`

**Solution:**
- SSH to cluster and verify directory exists
- Check username in credentials is correct
- Verify remote directory path is correct

### 4. Missing Embedding Files

**Error:** `No embedding files found matching pattern 'cluster*_gpu*.pkl'`

**Possible causes:**
- Remote embeddings haven't been generated yet
- Files have different naming convention
- Wrong remote directory

**Solution:**
- SSH to cluster and list files: `ls ~/mapper_embeddings/embeddings/`
- Verify file naming matches `cluster{N}_gpu{N}.pkl` pattern

### 5. Wikipedia Articles File Missing

**Error:** `FileNotFoundError: Wikipedia articles file not found: wikipedia.pkl`

**Solution:**
- Ensure `wikipedia.pkl` exists in project root: `/Users/jmanning/mapper.io/wikipedia.pkl`
- File should contain exactly 250,000 Wikipedia article dictionaries

### 6. Merge Fails After Successful Sync

**Error:** Gap or overlap detected during merge

**Likely cause:** Worker processes had issues; some GPUs generated incorrect index ranges

**Solution:**
```bash
# Examine checkpoint files
python3 << 'EOF'
import pickle
from pathlib import Path

for f in sorted(Path('embeddings').glob('cluster*_gpu*.pkl')):
    with open(f, 'rb') as file:
        data = pickle.load(file)
    print(f"{f.name}: {data['start_index']:,} - {data['end_index']:,}")
EOF
```

## Performance Characteristics

### Download Speed

- Typical speed: 50-200 Mbps per file (depends on network)
- File sizes: ~150-200 MB per GPU (16 total files)
- Expected download time: 10-30 minutes for both clusters

### Merge Time

- Loading checkpoints: ~30-60 seconds
- Verifying indices: ~5 seconds
- Concatenating arrays: ~10-20 seconds
- Quality checks: ~5 seconds
- Writing output: ~30-60 seconds
- **Total merge time:** ~2-3 minutes

### Storage Requirements

- Raw checkpoint files: ~2.4 GB (16 × 150 MB average)
- Merged file: ~1.9 GB (250,000 × 768 float32 embeddings)
- Temporary space needed: ~4.3 GB (raw + merged)

## Advanced Usage

### Resume Failed Operations

If sync/merge fails partway through:

```bash
# Check which files were downloaded
ls embeddings/cluster*_gpu*.pkl

# If some clusters synced but not others, sync specific cluster
python sync_and_merge_embeddings.py --clusters "tensor02" --sync-only

# Once all files present, merge only
python sync_and_merge_embeddings.py --merge-only
```

### Verify File Integrity

```python
import pickle
import hashlib
from pathlib import Path

# Calculate checksum of merged file
with open('embeddings/wikipedia_merged.pkl', 'rb') as f:
    file_hash = hashlib.sha256(f.read()).hexdigest()
    print(f"SHA256: {file_hash}")

# Load and verify structure
with open('embeddings/wikipedia_merged.pkl', 'rb') as f:
    data = pickle.load(f)

required_keys = ['embeddings', 'articles', 'total_articles', 'embedding_dim', 'model', 'timestamp']
for key in required_keys:
    if key not in data:
        print(f"✗ Missing key: {key}")
    else:
        print(f"✓ {key}: OK")

# Verify dimensions
print(f"\nEmbeddings shape: {data['embeddings'].shape}")
print(f"Articles count: {len(data['articles'])}")
print(f"Quality metrics: {data['quality_metrics']}")
```

### Incremental Updates

If new articles need to be added:

```python
import pickle
import numpy as np

# Load current merged file
with open('embeddings/wikipedia_merged.pkl', 'rb') as f:
    data = pickle.load(f)

# Add new embeddings
new_embeddings = np.random.randn(100, 768).astype(np.float32)
new_articles = [{'title': f'Article {i}', 'id': str(i), 'url': ''} for i in range(100)]

data['embeddings'] = np.vstack([data['embeddings'], new_embeddings])
data['articles'].extend(new_articles)
data['total_articles'] = len(data['articles'])

# Save updated file
with open('embeddings/wikipedia_merged.pkl', 'wb') as f:
    pickle.dump(data, f)
```

## Next Steps After Merge

1. **UMAP Projection**: Project embeddings to 2D for visualization
   ```bash
   python build_wikipedia_knowledge_map_v2.py
   ```

2. **Knowledge Map Visualization**: Create interactive HTML visualization

3. **Quality Analysis**: Verify embedding quality and distribution

4. **Archive**: Back up merged file to permanent storage

## Security Considerations

- **Credentials**: Never commit `.credentials/` files to version control
- **SSH Key Auth**: Consider using SSH keys instead of passwords
  ```json
  {
    "address": "hostname",
    "username": "user",
    "key_file": "/home/user/.ssh/id_rsa"
  }
  ```
- **Temporary Files**: Downloaded checkpoint files are kept in `embeddings/` after sync
- **Network**: Use SSH (paramiko) instead of plain-text protocols

## Support and Debugging

### Enable Verbose Logging

Currently, logging is built into the script. For more detailed logs, modify:

```python
# In sync_via_paramiko() function, add:
ssh.get_missing_host_key_policy(paramiko.AutoAddPolicy())
logging.basicConfig(level=logging.DEBUG)
```

### Check Network Connectivity

```bash
# Test SSH connectivity
ssh -v user@hostname

# Test SFTP
sftp user@hostname

# Check bandwidth
scp -v large_file user@hostname:~
```

### Inspect Checkpoint File Structure

```python
import pickle

checkpoint_file = 'embeddings/cluster1_gpu0.pkl'

with open(checkpoint_file, 'rb') as f:
    data = pickle.load(f)

print("Keys:", list(data.keys()))
print("Embeddings shape:", data['embeddings'].shape)
print("Start index:", data['start_index'])
print("End index:", data['end_index'])
print("Cluster ID:", data['cluster_id'])
print("GPU ID:", data['gpu_id'])
```

## References

- **paramiko**: https://www.paramiko.org/
- **numpy**: https://numpy.org/
- **UMAP**: https://umap-learn.readthedocs.io/
- **pickle**: https://docs.python.org/3/library/pickle.html

---

**Last Updated:** November 2024
**Version:** 1.0
