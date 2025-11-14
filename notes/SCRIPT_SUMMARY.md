# sync_and_merge_embeddings.py - Complete Script Summary

## File Location
```
/Users/jmanning/mapper.io/sync_and_merge_embeddings.py
```

## Script Size and Complexity
- **Lines of code:** 850+
- **Functions:** 10 main functions
- **Dependencies:** pickle, json, os, sys, argparse, subprocess, re, pathlib, datetime, typing, numpy, paramiko (optional)

## Architecture Overview

```
sync_and_merge_embeddings.py
├── Imports & Setup
├── CREDENTIAL MANAGEMENT (Section 1)
│   └── load_credentials() - Load cluster credentials
│
├── SYNC OPERATIONS (Section 2)
│   ├── extract_chunk_info() - Parse checkpoint filename metadata
│   ├── sync_from_cluster() - Main sync orchestrator
│   ├── sync_via_paramiko() - SFTP-based download (preferred)
│   └── sync_via_sshpass() - sshpass-based download (fallback)
│
├── MERGE OPERATIONS (Section 3)
│   ├── load_wikipedia_articles() - Load article metadata
│   ├── load_checkpoint() - Load individual checkpoint file
│   ├── verify_embedding_quality() - Quality checks on embeddings
│   └── merge_embeddings() - Main merge orchestrator
│
└── MAIN WORKFLOW (Section 4)
    └── main() - CLI entry point with argparse
```

## Function-by-Function Breakdown

### 1. CREDENTIAL MANAGEMENT

#### `load_credentials(cluster_name: str) -> Dict`
**Purpose:** Load and validate cluster credentials from JSON file

**Input:**
- `cluster_name`: Name of cluster (e.g., "tensor01", "tensor02")

**Output:**
- Dictionary with `address`, `username`, `password`

**Behavior:**
- Reads from `.credentials/{cluster_name}.credentials`
- Validates JSON format
- Verifies all required fields present
- Raises FileNotFoundError if file missing
- Raises JSONDecodeError if JSON invalid
- Raises ValueError if required fields missing

**Example:**
```python
creds = load_credentials("tensor01")
# Returns: {'address': '10.0.0.1', 'username': 'user', 'password': 'secret'}
```

---

### 2. SYNC OPERATIONS

#### `extract_chunk_info(filename: str) -> Optional[Dict]`
**Purpose:** Parse metadata from checkpoint filename using regex

**Input:**
- `filename`: Checkpoint filename (e.g., "cluster1_gpu0.pkl")

**Output:**
- Dictionary with `cluster_id` and `gpu_id`, or None if format invalid

**Regex Pattern:** `cluster(\d+)_gpu(\d+)\.pkl`

**Example:**
```python
info = extract_chunk_info("cluster1_gpu3.pkl")
# Returns: {'cluster_id': 1, 'gpu_id': 3}
```

---

#### `sync_from_cluster(cluster_name, output_dir, use_sshpass) -> Tuple[List[Path], List[str]]`
**Purpose:** High-level sync orchestrator for a single cluster

**Input:**
- `cluster_name`: Cluster identifier (e.g., "tensor01")
- `output_dir`: Local directory for downloads
- `use_sshpass`: Use sshpass instead of paramiko (default False)

**Output:**
- Tuple of (downloaded files list, warnings list)

**Process:**
1. Load credentials from `.credentials/{cluster_name}.credentials`
2. Try SFTP/SSH connection
3. List remote files matching `cluster*_gpu*.pkl`
4. Download each file with progress reporting
5. Return list of local file paths and any warnings

**Key Features:**
- Error handling with detailed messages
- Progress display for each file
- File size reporting in MB
- Graceful failure handling

---

#### `sync_via_paramiko(address, username, password, remote_dir, output_dir) -> Dict`
**Purpose:** Primary sync method using paramiko SFTP library

**Input:**
- `address`: Remote host address
- `username`: SSH username
- `password`: SSH password
- `remote_dir`: Remote directory path
- `output_dir`: Local output directory

**Output:**
- Dict with `files` (list of downloaded paths) and `warnings` (list of error messages)

**Process:**
1. Create paramiko SSH client
2. Connect with credentials and 30-second timeout
3. Open SFTP channel
4. List files in remote directory
5. Filter for embedding files (`cluster*_gpu*.pkl`)
6. Download each file sequentially
7. Handle exceptions gracefully

**Features:**
- Uses paramiko for more control
- Timeout handling
- Exception handling for each file
- Size reporting for each download

**Error Handling:**
- AuthException: Incorrect credentials
- SSHException: Connection issues
- FileNotFoundError: Remote directory doesn't exist
- Generic Exception: Catch-all for unexpected errors

---

#### `sync_via_sshpass(address, username, password, remote_dir, output_dir) -> Dict`
**Purpose:** Alternative sync using sshpass command-line tool

**Input:**
- `address`: Remote host address
- `username`: SSH username
- `password`: SSH password
- `remote_dir`: Remote directory path
- `output_dir`: Local output directory

**Output:**
- Dict with `files` and `warnings`

**Process:**
1. Check if sshpass is installed (`which sshpass`)
2. List remote files using `sshpass ssh ls -1 {remote_dir}`
3. Parse output and filter for embedding files
4. Download each using `sshpass scp`

**Use Case:**
- Fallback if paramiko not available
- Simpler for shell-based environments

**Requirements:**
- sshpass installed (`brew install sshpass` on macOS)

---

### 3. MERGE OPERATIONS

#### `load_wikipedia_articles() -> List[Dict]`
**Purpose:** Load Wikipedia article metadata from wikipedia.pkl

**Input:** None

**Output:**
- List of 250,000 article dictionaries

**Expected Structure:**
```python
[
    {
        'id': '41407254',
        'title': 'Nae Lăzărescu',
        'url': 'https://en.wikipedia.org/wiki/...',
        'text': 'Article text...'
    },
    ...  # 250,000 total
]
```

**Validation:**
- File exists at `./wikipedia.pkl`
- Is a valid pickle file
- Contains exactly 250,000 items
- Each item is a dictionary

**Errors:**
- FileNotFoundError: File doesn't exist
- UnpicklingError: Invalid pickle format
- ValueError: Wrong number of articles

---

#### `load_checkpoint(filepath: Path) -> Dict`
**Purpose:** Load and validate a single checkpoint file

**Input:**
- `filepath`: Path to checkpoint .pkl file

**Output:**
- Dictionary with checkpoint data

**Expected Structure:**
```python
{
    'embeddings': np.ndarray(shape=(N, 768)),
    'start_index': int,
    'end_index': int,
    'cluster_id': int,
    'gpu_id': int,
    ...other fields...
}
```

**Validation:**
- File exists
- Valid pickle format
- Has all required fields: `embeddings`, `start_index`, `end_index`, `cluster_id`, `gpu_id`
- `embeddings` is numpy array

**Errors:**
- FileNotFoundError: File missing
- UnpicklingError: Invalid pickle
- ValueError: Missing required fields or wrong types

---

#### `verify_embedding_quality(embeddings: np.ndarray) -> Dict`
**Purpose:** Perform quality checks on embedding array

**Input:**
- `embeddings`: Numpy array of shape (N, 768)

**Output:**
- Dictionary with quality metrics

**Metrics Computed:**
```python
{
    'shape': Tuple,           # (N, D)
    'dtype': str,            # 'float32', 'float64', etc.
    'min_norm': float,       # Min L2 norm
    'max_norm': float,       # Max L2 norm
    'mean_norm': float,      # Mean L2 norm
    'std_norm': float,       # Std L2 norm
    'has_nan': bool,         # Any NaN values?
    'has_inf': bool,         # Any Inf values?
}
```

**Process:**
1. Compute L2 norm for each embedding
2. Calculate norm statistics
3. Check for NaN/Inf values
4. Return metrics dictionary

---

#### `merge_embeddings(embedding_files, output_file, articles, embedding_dim, num_articles, model_name) -> bool`
**Purpose:** Main merge orchestrator - comprehensive 7-phase merge process

**Input:**
- `embedding_files`: List of checkpoint file paths
- `output_file`: Path to save merged file
- `articles`: List of 250,000 article dicts
- `embedding_dim`: Expected dimension (768)
- `num_articles`: Number of articles to include (250,000)
- `model_name`: Model name for metadata

**Output:**
- True if successful, False if any error

**Process (7 Phases):**

**Phase 1: LOAD CHECKPOINTS**
- Load each checkpoint file
- Extract embeddings, indices, cluster/GPU info
- Validate size matches expected range
- Store in memory

**Phase 2: VERIFY INDEX RANGES**
- Sort checkpoints by start_index
- Check for gaps: expected_idx == start_idx
- Check for overlaps: end_idx > start_idx
- Report continuous ranges

**Phase 3: CONCATENATE EMBEDDINGS**
- Use np.concatenate() to join all embeddings
- Extract only first 250,000 (exclude 10 questions)
- Verify dimension matches 768

**Phase 4: QUALITY CHECKS**
- Call verify_embedding_quality()
- Check for NaN/Inf values
- Verify shape and dimensions
- Print detailed metrics

**Phase 5: PREPARE ARTICLE METADATA**
- Extract titles from wikipedia.pkl articles
- Include id and url for reference
- Verify count matches embeddings

**Phase 6: SAVE MERGED FILE**
- Create output directory if needed
- Package all data in dictionary
- Save as pickle file
- Report file size

**Phase 7: VALIDATION**
- Verify saved file readable
- Check total items correct
- Report timestamp

**Output Dictionary:**
```python
{
    'embeddings': np.ndarray(250000, 768),
    'articles': List[Dict],            # 250,000 entries
    'total_articles': 250000,
    'embedding_dim': 768,
    'model': 'google/embeddinggemma-300m',
    'timestamp': '2024-11-14T...',
    'shape': (250000, 768),
    'quality_metrics': Dict,
    'chunk_info': List[Dict]           # Per-GPU metadata
}
```

**Error Handling:**
- Returns False immediately on first error
- Prints detailed error messages
- Validates at each phase
- Never partially completes merge

---

### 4. MAIN WORKFLOW

#### `main() -> int`
**Purpose:** CLI entry point with argparse command-line interface

**Input:**
- Command-line arguments parsed by argparse

**Output:**
- Exit code (0 for success, 1 for failure)

**Command-Line Arguments:**
```
--sync-only          Only download, skip merge
--merge-only         Only merge existing files, skip download
--clusters CLUSTERS  Space-separated cluster names (default: "tensor01 tensor02")
--output OUTPUT      Output file path (default: "embeddings/wikipedia_merged.pkl")
```

**Workflow:**

**Stage 1: INITIALIZATION**
- Print header and timestamp
- Create embeddings directory
- Validate output path

**Stage 2: SYNC (unless --merge-only)**
- Parse cluster list from args
- For each cluster:
  - Call sync_from_cluster()
  - Collect downloaded files and warnings
- Report total files and any warnings
- If --sync-only, exit here

**Stage 3: LOAD ARTICLES**
- Load wikipedia.pkl
- Validate 250,000 articles present

**Stage 4: MERGE (unless --sync-only)**
- Collect embedding files (either downloaded or existing)
- Call merge_embeddings()
- Wait for completion

**Stage 5: FINAL SUMMARY**
- Report success or failure
- Show output file path and size
- Print next steps
- Return appropriate exit code

**Exit Codes:**
- 0: Success (sync/merge completed)
- 1: Error (credentials, file not found, merge failed)

---

## Data Flow Diagram

```
Command Line Arguments
    ↓
main() - Parse arguments
    ├─→ [--sync-only flag?]
    │   ├─ YES → Skip merge phase
    │   └─ NO → Proceed to merge
    │
    ├─→ [--merge-only flag?]
    │   ├─ YES → Skip sync phase
    │   └─ NO → Proceed to sync
    │
    ├→ SYNC PHASE (unless --merge-only)
    │   ├─→ Parse --clusters argument
    │   ├─→ For each cluster:
    │   │   ├─→ load_credentials()
    │   │   ├─→ sync_from_cluster()
    │   │   │   ├─→ sync_via_paramiko() OR
    │   │   │   └─→ sync_via_sshpass()
    │   │   │       └─→ Download cluster*_gpu*.pkl files
    │   │   └─→ Collect file paths and warnings
    │   └─→ Return: List of downloaded files
    │
    └→ MERGE PHASE (unless --sync-only)
        ├─→ load_wikipedia_articles()
        │   └─→ Load 250,000 article dicts from wikipedia.pkl
        ├─→ merge_embeddings()
        │   ├─→ Load all checkpoint files
        │   ├─→ load_checkpoint() for each file
        │   ├─→ Verify index ranges (no gaps/overlaps)
        │   ├─→ Concatenate embeddings
        │   │   └─→ Extract only first 250,000 (no questions)
        │   ├─→ verify_embedding_quality()
        │   │   └─→ Check norms, NaN, Inf
        │   ├─→ Prepare article metadata
        │   └─→ Save merged file as pickle
        └─→ Return: True/False success

Output: embeddings/wikipedia_merged.pkl
```

---

## Key Features & Design Decisions

### 1. Two-Phase Architecture
- **SYNC Phase**: Download files independently from clusters
- **MERGE Phase**: Combine downloaded files deterministically
- Benefit: Can retry individual phases without repeating entire process

### 2. Dual Download Methods
- **Primary (paramiko)**: Better error handling, more control
- **Fallback (sshpass)**: Simpler, works in shell environments
- Benefit: Flexibility for different deployment scenarios

### 3. Comprehensive Validation
- Index range verification (no gaps/overlaps)
- Embedding dimension checks
- Quality metrics (norms, NaN, Inf)
- Article count validation
- Benefit: Prevents silent data corruption

### 4. Flexible CLI Interface
- `--sync-only`: Download without merge
- `--merge-only`: Merge without download
- `--clusters`: Specify which clusters to sync
- Benefit: Support recovery workflows and parallel processing

### 5. Rich Output Formatting
- Structured progress reporting
- Visual indicators (✓, ✗, ⚠)
- File sizes and counts formatted with thousands separator
- Benefit: Easy monitoring and debugging

### 6. Detailed Error Messages
- Context about what failed and why
- Suggestions for resolution
- Checkpoint data for debugging
- Benefit: Faster troubleshooting

### 7. Metadata Preservation
- Chunk information (cluster/GPU per file)
- Quality metrics
- Timestamp
- Model information
- Benefit: Reproducibility and auditing

---

## Performance Characteristics

### Time Complexity
- **Sync per file:** O(1) - constant time per file
- **Merge load:** O(N) where N = total checkpoints
- **Merge verify:** O(N) to check index ranges
- **Concatenate:** O(M) where M = total embeddings
- **Total:** O(N + M) linear in files and embeddings

### Space Complexity
- **Peak memory:** O(2M) = loaded embeddings + concatenated result
- **Disk:** O(2M) = checkpoint files + merged file
- For 250k × 768 embeddings: ~1.9 GB each

### Typical Performance
- Sync: 10-30 minutes (depends on network bandwidth)
- Merge: 2-3 minutes (local operations only)
- Total: 15-35 minutes

---

## Testing and Validation

### Unit Tests Needed
```python
# Test credential loading
def test_load_credentials_valid()
def test_load_credentials_missing()
def test_load_credentials_invalid_json()

# Test filename parsing
def test_extract_chunk_info_valid()
def test_extract_chunk_info_invalid()

# Test merge operations
def test_load_checkpoint_valid()
def test_load_checkpoint_invalid()
def test_verify_embedding_quality()
def test_merge_embeddings_valid()
def test_merge_embeddings_gaps()
def test_merge_embeddings_overlaps()
```

### Integration Tests Needed
```python
# End-to-end sync and merge with test data
def test_sync_and_merge_workflow()

# Merge with mock checkpoint files
def test_merge_with_mock_clusters()
```

---

## Extension Points

### 1. Add Cloud Storage Support
```python
def sync_from_s3(bucket, prefix, output_dir)
def sync_from_gcs(project, bucket, prefix, output_dir)
```

### 2. Add Progress Callbacks
```python
def merge_embeddings(..., progress_callback=None)
    # Notify callback at each phase
    progress_callback(phase='loading', progress=0.25)
```

### 3. Add Checkpointing
```python
def merge_embeddings_with_checkpoint(..., checkpoint_dir=None)
    # Save intermediate results
    # Resume from checkpoint if interrupted
```

### 4. Add Parallel Downloads
```python
def sync_from_cluster_parallel(cluster_name, output_dir, num_workers=4)
    # Download multiple files concurrently
```

### 5. Add Compression
```python
def save_compressed_embeddings(data, output_file)
    # Use zarr, h5py, or compression to reduce size
```

---

## Summary Statistics

| Aspect | Value |
|--------|-------|
| Total Lines | 850+ |
| Functions | 10 |
| Code Sections | 4 major |
| Error Handlers | 8+ |
| Input Validations | 12+ |
| Output Formats | 1 (pickle dict) |
| CLI Arguments | 4 |
| Dependencies | 6+ |
| Time Complexity | O(N + M) |
| Space Complexity | O(2M) |

