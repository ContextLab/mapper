# Wikipedia Knowledge Map - Large-Scale Embedding Pipeline

A distributed GPU system for generating and visualizing semantic knowledge maps from 250,000 Wikipedia articles. This project implements the research from "Text embedding models yield high-resolution insights into conceptual knowledge" using distributed GPU computing and interactive web visualization.

## Project Overview

This system generates semantic embeddings for 250,000 Wikipedia articles using state-of-the-art transformer models, then visualizes them as interactive 2D knowledge maps. The pipeline supports both distributed GPU clusters (for production-scale processing) and local Metal-accelerated generation (for development/testing).

**Key Features:**
- Distributed embedding generation across multiple GPU clusters (up to 16 GPUs)
- Local Metal (Apple Silicon) acceleration for development
- Interactive heatmap visualization with Gaussian kernel density estimation
- Automatic synchronization and merging of distributed results
- Support for multiple embedding models (Qwen, Google EmbeddingGemma, etc.)

## Architecture

The system has two operational modes:

### 1. Distributed GPU Mode (Production)

For processing the full 250K article dataset using remote GPU clusters:

```
wikipedia.pkl (250K articles)
    ↓
launch_distributed.sh → SSH to clusters
    ↓
generate_embeddings_gpu.py (runs on each GPU)
    ↓
cluster*_gpu*.pkl (16 checkpoint files)
    ↓
sync_and_merge_embeddings.py
    ↓
embeddings/wikipedia_merged.pkl (1.9 GB)
    ↓
build_wikipedia_knowledge_map_v2.py
    ↓
index.html (interactive visualization)
```

**Cluster Configuration:**
- 2 clusters × 8 GPUs = 16 workers
- Each GPU processes ~15,625 articles independently
- Checkpoints saved separately, merged locally
- Model: Qwen/Qwen3-Embedding-0.6B or google/embeddinggemma-300m

### 2. Local Mode (Development/Testing)

For testing on smaller datasets or development on Apple Silicon:

```
wikipedia.pkl
    ↓
generate_embeddings_local.py (Metal acceleration)
    ↓
embeddings/local_embeddings.pkl
    ↓
build_wikipedia_knowledge_map_v2.py
    ↓
index.html
```

**Local Configuration:**
- Uses Metal Performance Shaders (MPS) on Apple Silicon
- Supports CPU fallback
- Can process full dataset (slower) or limited subsets
- Same embedding models as distributed mode

## Quick Start

### Prerequisites

```bash
# Core dependencies
pip install -r requirements.txt

# For distributed mode (optional)
pip install paramiko  # SSH/SFTP for cluster communication

# Verify GPU access (optional, for local mode)
python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

### Option A: Distributed GPU Processing

**1. Setup Cluster Credentials**

Create `.credentials/` directory with cluster configuration:

```bash
mkdir -p .credentials

# .credentials/tensor01.credentials
{
  "address": "tensor01.example.com",
  "username": "your_username",
  "password": "your_password"
}

# .credentials/tensor02.credentials
{
  "address": "tensor02.example.com",
  "username": "your_username",
  "password": "your_password"
}
```

**2. Launch Distributed Workers**

```bash
# Upload files and launch workers on both clusters
./launch_distributed.sh

# Or specify specific clusters
./launch_distributed.sh --clusters "tensor01 tensor02"
```

**3. Monitor Progress**

```bash
# Check status across all clusters
python monitor_clusters.py

# Manual checks
ssh tensor01 'tail -f ~/mapper_embeddings/logs/gpu0.log'
ssh tensor01 'cat ~/mapper_embeddings/embeddings/progress.json'
```

**4. Sync and Merge Results**

```bash
# Download all checkpoint files and merge
python sync_and_merge_embeddings.py

# Output: embeddings/wikipedia_merged.pkl (~1.9 GB)
```

**5. Build Knowledge Map**

```bash
# Generate UMAP projection and cell labels
python build_wikipedia_knowledge_map_v2.py

# Outputs:
# - knowledge_map.pkl (embeddings + UMAP coordinates)
# - heatmap_cell_labels.json (semantic labels for regions)
# - umap_reducer.pkl (trained UMAP model)
```

**6. View Interactive Visualization**

```bash
# Start local web server
python -m http.server 8000

# Open browser to:
# http://localhost:8000/index.html
```

### Option B: Local Processing (Development)

**1. Generate Embeddings Locally**

```bash
# Full dataset (250K articles, 2-6 hours on M1/M2 Ultra)
python generate_embeddings_local.py

# Limited dataset (testing, faster)
python generate_embeddings_local.py --num-articles 1000 --batch-size 64

# Include quiz questions in embeddings
python generate_embeddings_local.py --include-questions
```

**2. Build Knowledge Map**

```bash
python build_wikipedia_knowledge_map_v2.py
```

**3. View Visualization**

```bash
python -m http.server 8000
# Open: http://localhost:8000/index.html
```

## Main Scripts

### Embedding Generation

| Script | Purpose | Mode |
|--------|---------|------|
| `generate_embeddings_gpu.py` | Worker script for distributed GPU processing | Distributed |
| `generate_embeddings_local.py` | Local embedding generation with Metal acceleration | Local |
| `launch_distributed.sh` | SSH launcher for cluster workers | Distributed |

### Synchronization & Merging

| Script | Purpose |
|--------|---------|
| `sync_and_merge_embeddings.py` | Download checkpoint files and merge into single file |
| `merge_embeddings.py` | Legacy merge script (use sync_and_merge instead) |
| `monitor_clusters.py` | Real-time monitoring of distributed workers |

### Knowledge Map Building

| Script | Purpose |
|--------|---------|
| `build_wikipedia_knowledge_map.py` | Initial version (nvidia/nemotron) |
| `build_wikipedia_knowledge_map_v2.py` | Production version (recommended) |
| `generate_cell_labels.py` | Generate semantic labels for heatmap regions |

### Utilities & Testing

| Script | Purpose |
|--------|---------|
| `inspect_wikipedia_data.py` | Verify wikipedia.pkl structure and contents |
| `benchmark_batch_sizes.py` | Optimize batch size for your hardware |
| `test_embedding_speed.py` | Performance benchmarking |
| `verify_cell_labels.py` | Validate generated cell labels |
| `spot_check_labels.py` | Manual inspection of label quality |

## Data Files

### Input Data

| File | Size | Description |
|------|------|-------------|
| `wikipedia.pkl` | 752 MB | 250,000 Wikipedia articles (text, title, URL, ID) |
| `questions.json` | ~2 KB | 10 quiz questions with coordinates |

### Generated Data

| File | Size | Description |
|------|------|-------------|
| `embeddings/wikipedia_merged.pkl` | ~1.9 GB | Merged embeddings from all GPU workers |
| `knowledge_map.pkl` | ~2.5 GB | Embeddings + UMAP coordinates + metadata |
| `heatmap_cell_labels.json` | ~50 KB | Semantic labels for visualization grid |
| `umap_reducer.pkl` | ~37 KB | Trained UMAP model for inverse transforms |
| `umap_bounds.pkl` | ~84 B | Coordinate normalization parameters |

### Checkpoint Files (Temporary)

| Pattern | Count | Size Each | Description |
|---------|-------|-----------|-------------|
| `cluster*_gpu*.pkl` | 16 | ~150 MB | Individual GPU worker checkpoints |

## Command Reference

### Distributed Processing

```bash
# Launch workers on all configured clusters
./launch_distributed.sh

# Launch on specific clusters
./launch_distributed.sh --clusters "tensor01"

# Monitor progress
python monitor_clusters.py

# Sync and merge (full workflow)
python sync_and_merge_embeddings.py

# Sync only (download without merging)
python sync_and_merge_embeddings.py --sync-only

# Merge only (use existing downloaded files)
python sync_and_merge_embeddings.py --merge-only

# Specify clusters for sync
python sync_and_merge_embeddings.py --clusters "tensor01 tensor02"

# Custom output location
python sync_and_merge_embeddings.py --output "backups/embeddings_2024-11-14.pkl"
```

### Local Processing

```bash
# Full dataset with default settings
python generate_embeddings_local.py

# Limited dataset for testing
python generate_embeddings_local.py --num-articles 5000

# Use CPU instead of Metal
python generate_embeddings_local.py --use-mps false

# Custom batch size
python generate_embeddings_local.py --batch-size 256

# Include quiz questions in embeddings
python generate_embeddings_local.py --include-questions
```

### Knowledge Map Building

```bash
# Build knowledge map from merged embeddings
python build_wikipedia_knowledge_map_v2.py

# Generate cell labels for heatmap
python generate_cell_labels.py

# Verify cell labels
python verify_cell_labels.py

# Spot check specific labels
python spot_check_labels.py
```

### Utilities

```bash
# Inspect Wikipedia dataset
python inspect_wikipedia_data.py

# Benchmark batch sizes for your hardware
python benchmark_batch_sizes.py

# Test embedding generation speed
python test_embedding_speed.py
```

## Configuration

### Embedding Models

The system supports multiple embedding models. Edit the script to change models:

```python
# In generate_embeddings_gpu.py or generate_embeddings_local.py

# Option 1: Qwen (default for distributed)
model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")

# Option 2: Google EmbeddingGemma
model = SentenceTransformer("google/embeddinggemma-300m")

# Option 3: Sentence transformers
model = SentenceTransformer("all-MiniLM-L6-v2")
```

### Cluster Configuration

Edit `launch_distributed.sh` to configure clusters:

```bash
# Default: both clusters
CLUSTERS="tensor01 tensor02"

# Single cluster
CLUSTERS="tensor01"

# More clusters
CLUSTERS="tensor01 tensor02 tensor03"
```

### UMAP Parameters

Edit `build_wikipedia_knowledge_map_v2.py` for UMAP settings:

```python
# Dimensionality reduction
reducer = umap.UMAP(
    n_components=2,          # 2D projection
    n_neighbors=15,          # Local neighborhood size
    min_dist=0.1,           # Minimum distance between points
    metric='cosine',        # Distance metric
    random_state=42
)
```

### Heatmap Visualization

Edit `index.html` for visualization settings:

```javascript
// Gaussian kernel bandwidth
const sigma = 0.15;  // Smaller = more localized, Larger = smoother

// Heatmap resolution
const gridSize = 40;  // Higher = more detail (but slower)

// Cell label grid
const labelGridSize = 5;  // 5×5 grid of semantic labels
```

## Troubleshooting

### Distributed Mode Issues

**Connection Refused**
```bash
# Test SSH connectivity
ssh user@tensor01.example.com

# Verify credentials file
cat .credentials/tensor01.credentials
```

**Workers Not Starting**
```bash
# Check screen sessions on cluster
ssh tensor01 'screen -ls'

# View worker logs
ssh tensor01 'tail -f ~/mapper_embeddings/logs/gpu0.log'

# Kill and restart
ssh tensor01 'screen -S mapper_gpu0 -X quit'
./launch_distributed.sh
```

**Missing Checkpoint Files**
```bash
# List remote files
ssh tensor01 'ls -lh ~/mapper_embeddings/embeddings/'

# Check progress file
ssh tensor01 'cat ~/mapper_embeddings/embeddings/progress.json'

# Verify workers are running
ssh tensor01 'ps aux | grep generate_embeddings_gpu'
```

### Local Mode Issues

**macOS Mutex Blocking Error**
```
[mutex.cc : 452] RAW: Lock blocking
```

**Solution:** Use Docker (provides Ubuntu environment):
```bash
docker-compose build
docker-compose run --rm embeddings python generate_embeddings_local.py
```

**Out of Memory**
```bash
# Reduce batch size
python generate_embeddings_local.py --batch-size 32

# Limit dataset
python generate_embeddings_local.py --num-articles 10000
```

**Slow Performance**
```bash
# Check GPU availability
python -c "import torch; print(torch.backends.mps.is_available())"

# Benchmark batch sizes
python benchmark_batch_sizes.py

# Use optimal batch size
python generate_embeddings_local.py --batch-size 128
```

### Merge Issues

**Gap Detected in Embeddings**
```
ERROR: Gap detected at index 100000
```

**Solution:** Check which worker failed:
```bash
# Inspect checkpoint file
python -c "
import pickle
data = pickle.load(open('embeddings/cluster1_gpu4.pkl', 'rb'))
print(f'Range: {data[\"start_index\"]} - {data[\"end_index\"]}')
print(f'Items: {len(data[\"embeddings\"])}')
"
```

**Dimension Mismatch**
```
ERROR: Dimension mismatch: expected 768, got 384
```

**Solution:** All workers must use same embedding model. Check:
```bash
grep "model_name = " generate_embeddings_gpu.py
```

### Visualization Issues

**Heatmap Not Loading**
```
Failed to load questions.json
```

**Solution:** Serve via HTTP (not file://)
```bash
python -m http.server 8000
# Open: http://localhost:8000/index.html
```

**Blank Heatmap**
```bash
# Verify knowledge_map.pkl exists
ls -lh knowledge_map.pkl

# Check for coordinates
python -c "
import pickle
data = pickle.load(open('knowledge_map.pkl', 'rb'))
print(f'Has coordinates: {\"coordinates\" in data}')
print(f'Coordinate range: {data[\"coordinates\"].min()}, {data[\"coordinates\"].max()}')
"
```

## Performance Benchmarks

### Distributed Mode (16 GPUs)

| Component | Time | Hardware |
|-----------|------|----------|
| Embedding Generation | 30-45 min | 2 × 8 A100 GPUs |
| Download Checkpoints | 10-30 min | Network dependent |
| Merge Embeddings | 2-3 min | Local CPU |
| UMAP Projection | 15-25 min | Local CPU/GPU |
| **Total** | **~60-90 min** | Full pipeline |

### Local Mode (Single GPU)

| Component | Time | Hardware |
|-----------|------|----------|
| Embedding Generation (250K) | 2-4 hours | M1 Ultra (64 GPU cores) |
| Embedding Generation (10K) | 5-10 min | M1 Ultra |
| UMAP Projection | 15-25 min | M1 Ultra |

### Memory Requirements

| Component | RAM | VRAM |
|-----------|-----|------|
| Distributed Worker | 8 GB | 16 GB per GPU |
| Local Full Dataset | 32 GB | 8 GB |
| Local Limited (10K) | 8 GB | 4 GB |
| UMAP (250K points) | 16 GB | - |
| Merge Operation | 4 GB | - |

## Advanced Features

### Custom Wikipedia Dataset

Replace `wikipedia.pkl` with your own articles:

```python
import pickle

# Your articles (list of dicts)
articles = [
    {'text': '...', 'title': '...', 'url': '...', 'id': ...},
    # ... more articles
]

# Save in expected format
with open('wikipedia.pkl', 'wb') as f:
    pickle.dump(articles, f)

# Verify
with open('wikipedia.pkl', 'rb') as f:
    loaded = pickle.load(f)
    print(f"Loaded {len(loaded):,} articles")
```

### Custom Quiz Questions

Edit `questions.json`:

```json
[
  {
    "question": "Your question text?",
    "options": ["Choice A", "Choice B", "Choice C", "Choice D"],
    "correctIndex": 1,
    "x": 0.5,
    "y": 0.5,
    "topic": "optional_topic"
  }
]
```

### Export Knowledge Map Data

```python
import pickle
import json

# Load knowledge map
with open('knowledge_map.pkl', 'rb') as f:
    data = pickle.load(f)

# Export to JSON for other tools
export_data = {
    'articles': data['articles'][:100],  # First 100 for demo
    'coordinates': data['coordinates'][:100].tolist(),
    'labels': data.get('cell_labels', [])
}

with open('knowledge_map_export.json', 'w') as f:
    json.dump(export_data, f, indent=2)
```

## Citation

Based on the research paper:

```
"Text embedding models yield high-resolution insights into conceptual knowledge"
[Add paper citation when published]
```

## License

Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)

See [LICENSE](LICENSE) file for details.

## Contributing

This is a research project. For questions or collaboration inquiries, please open an issue.

## Support

- **Documentation:** See `CLAUDE.md` for project-specific guidelines
- **Quick Start:** See `QUICKSTART.md` for condensed instructions
- **Sync Guide:** See `SYNC_AND_MERGE_GUIDE.md` for detailed merge documentation
- **Script Reference:** See `SCRIPT_SUMMARY.md` for all script details

## Acknowledgments

- Sentence Transformers library for embedding generation
- UMAP for dimensionality reduction
- Qwen and Google for open-source embedding models
- Hypertools for knowledge map inspiration
