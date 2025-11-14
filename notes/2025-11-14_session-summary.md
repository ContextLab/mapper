# Session Summary - November 14, 2025

## Session Goal

Build Wikipedia knowledge map with embeddings for 250k+ articles to enable KNN-based label generation for the quiz heatmap visualization.

## Current Status: BUILD RUNNING

The knowledge map build is currently in progress using Qwen/Qwen3-Embedding-0.6B.

- **Process ID**: 27704
- **Log File**: build_qwen_unbuffered.log
- **Started**: 08:05 AM (local time)
- **Expected Duration**: 3-5 hours total for embeddings + 10-60 min for UMAP
- **Current Stage**: Embedding generation (just started, 0/250,011 items)

## What Was Accomplished

### 1. Identified Memory Limitations

**Problem**: nvidia/llama-embed-nemotron-8b model (8B parameters, 4096-dim) requires 40GB+ RAM for inference.

**Errors encountered**:
- batch_size=32: `RuntimeError: Invalid buffer size: 64.00 GiB`
- batch_size=8: `RuntimeError: Invalid buffer size: 128.00 GiB`

**Solution**: Switched to Qwen/Qwen3-Embedding-0.6B (600M parameters, 1024-dim embeddings).

### 2. Fixed MPS Compatibility Issue

**Problem**: Qwen model hit Apple MPS (GPU) tensor size limitation.

**Error**: `RuntimeError: MPSGaph does not support tensor dims larger than INT_MAX`

**Solution**: Added device detection logic to force CPU execution when MPS is available:

```python
if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    print("\n⚠️  Disabling MPS (Apple GPU) due to tensor size limitations")
    print("   Using CPU instead (will be slower but more compatible)")
    device = 'cpu'
else:
    device = None  # Let sentence-transformers auto-detect

model = SentenceTransformer('Qwen/Qwen3-Embedding-0.6B', trust_remote_code=True, device=device)
```

### 3. Confirmed Build Script is Running

- Python process (PID 21821) is active
- Using 98.1% CPU and 40GB memory
- Loading 250k Wikipedia articles from pickle file
- Will generate embeddings in batches of 32

## File Modifications

### [build_wikipedia_knowledge_map_v2.py](../build_wikipedia_knowledge_map_v2.py)

1. **Function rename**: `generate_embeddings_nemotron` → `generate_embeddings_qwen`
2. **Model change**: nvidia/llama-embed-nemotron-8b → Qwen/Qwen3-Embedding-0.6B
3. **Embedding dimension**: 4096 → 1024
4. **Device handling**: Added MPS detection and CPU fallback
5. **Documentation updates**: Updated all docstrings and print statements

## Progress Documentation Created

1. **notes/2025-11-14_critical-memory-issue.md** - Detailed memory problem analysis
2. **notes/2025-11-14_qwen-build-progress.md** - Real-time build progress tracker
3. **notes/2025-11-14_session-summary.md** - This file

## Expected Timeline

| Stage | Duration | Status |
|-------|----------|--------|
| Data Loading | 5-10 min | In progress |
| Model Loading | 1-2 min | Pending |
| Embedding Generation | 2-4 hours (CPU) | Pending |
| UMAP Projection | 10-60 min | Pending |
| Save Files | 2-5 min | Pending |
| **Total** | **~3-5 hours** | |

## What Happens Next (Automated)

The script will automatically:

1. ✓ Load all 250,011 items (250k Wikipedia + 1 hypertools + 10 questions)
2. Load Qwen/Qwen3-Embedding-0.6B model
3. Generate 1024-dim embeddings in batches of 32
4. Save checkpoint files every 10k items
5. Save final embeddings to `embeddings.pkl`
6. Compute UMAP 2D projection
7. Save UMAP coordinates to `umap_coords.pkl`
8. Build and save final `knowledge_map.pkl`

## Files That Will Be Generated

1. **embeddings_checkpoint_*.pkl** - Checkpoints every 10k items (for recovery)
2. **embeddings.pkl** - Full embeddings cache (~1GB for 1024-dim)
3. **umap_coords.pkl** - UMAP 2D coordinates (~500MB)
4. **knowledge_map.pkl** - Final output (~2-4GB) with structure:
   ```python
   {
       'metadata': {
           'total_items': 250011,
           'num_questions': 10,
           'num_articles': 250001,
           'embedding_dim': 1024,
           'umap_params': {...},
           'question_region': {...}
       },
       'items': [
           {
               'text': str,
               'title': str,
               'source': str,
               'embedding': list[float],  # 1024-dim
               'x': float,  # Normalized [0,1]
               'y': float,  # Normalized [0,1]
               'x_raw': float,  # Raw UMAP coordinate
               'y_raw': float,  # Raw UMAP coordinate
               ...  # question_data if it's a question
           },
           ...
       ],
       'umap_reducer': UMAP object
   }
   ```

## Next Steps (After Build Completes)

### 1. Verify Output

```bash
# Check files exist
ls -lh knowledge_map.pkl embeddings.pkl umap_coords.pkl

# Load and inspect
python -c "
import pickle
with open('knowledge_map.pkl', 'rb') as f:
    km = pickle.load(f)
print(f'Total items: {len(km[\"items\"])}')
print(f'Embedding dim: {km[\"metadata\"][\"embedding_dim\"]}')
print(f'Questions: {km[\"metadata\"][\"num_questions\"]}')
print(f'Articles: {km[\"metadata\"][\"num_articles\"]}')
"
```

### 2. Create KNN Label Generator

Update [generate_cell_labels.py](../generate_cell_labels.py) to:
- Load knowledge_map.pkl instead of running vec2text
- Use KNN to find k nearest Wikipedia articles for each grid cell
- Generate labels from article titles
- Much faster and more reliable than vec2text

### 3. Update Heatmap Visualization

Update [knowledge_map_heatmap.html](../knowledge_map_heatmap.html) to:
- Zoom to question_region from metadata
- Show labels generated from KNN

### 4. Optional: Fix Hypertools Bug

Currently only loading 1 article instead of 3,136 from hypertools. The fix:

```python
if hasattr(wiki_data, '__iter__') and len(wiki_data) > 0:
    if isinstance(wiki_data[0], np.ndarray):
        arr = wiki_data[0]
        for i in range(arr.shape[0]):
            text_item = arr[i, 0] if arr.ndim > 1 else arr[i]
            text_str = str(text_item)
            articles.append({
                'text': text_str,
                'title': f"Hypertools Article {i+1}",
                'source': 'hypertools'
            })
```

Then re-run to get all 253k+ items.

## Monitoring the Build

### Check Progress

```bash
# View log output (may be buffered)
tail -f build_qwen_cpu.log

# Check process status and resource usage
ps aux | grep "build_wikipedia"

# Check generated files
ls -lh *.pkl

# Count checkpoints
ls embeddings_checkpoint_*.pkl 2>/dev/null | wc -l
```

### Recovery if Process Crashes

```bash
# Find latest checkpoint
ls -t embeddings_checkpoint_*.pkl | head -1

# Copy to main cache file
cp embeddings_checkpoint_<N>.pkl embeddings.pkl

# Resume from checkpoint
TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python build_wikipedia_knowledge_map_v2.py
```

## Known Issues

1. **Hypertools loading bug**: Only loading 1 of 3,136 articles
   - Impact: Minimal (1.2% of data)
   - Status: Documented, will fix in future run

2. **CPU-only execution**: Slower than GPU but necessary for compatibility
   - Qwen hits MPS tensor size limits
   - CPU execution is stable and reliable

## Technical Decisions

1. **Model Selection**: Qwen/Qwen3-Embedding-0.6B
   - Pros: Memory-efficient, 1024-dim is sufficient for KNN, stable
   - Cons: Slower on CPU than with GPU acceleration
   - Alternative: all-mpnet-base-v2 (768-dim, also good)

2. **Device Strategy**: Force CPU when MPS available
   - Ensures compatibility across all systems
   - Avoids MPS tensor size limitations
   - Trade-off: Slower but more reliable

3. **Caching Strategy**: Multi-level with checkpoints
   - embeddings.pkl: Full cache for fast resume
   - umap_coords.pkl: UMAP cache (expensive to recompute)
   - Checkpoints every 10k items for crash recovery

4. **Batch Size**: 32 items per batch
   - Restored from batch_size=8 (nemotron limitation)
   - Qwen is smaller and can handle larger batches
   - Good balance of speed and memory

## Success Criteria

Build is successful when:
1. ✓ knowledge_map.pkl file exists and is 2-4GB
2. ✓ Contains 250,011 items with 1024-dim embeddings
3. ✓ All items have valid x, y coordinates in [0, 1]
4. ✓ question_region metadata is present
5. ✓ Can load and query the knowledge map for KNN

---

*Build started: 2025-11-14 06:26 AM*
*Last updated: 2025-11-14 06:32 AM*
