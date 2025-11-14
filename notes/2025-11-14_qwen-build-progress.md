# Qwen Knowledge Map Build - November 14, 2025

## Current Status: RUNNING

**Started**: 2025-11-14 06:26 AM (local time)
**Model**: Qwen/Qwen3-Embedding-0.6B (1024-dim)
**Process ID**: 21821
**Log File**: build_qwen_cpu.log

## Build Progress

### Stage 1: Data Loading (In Progress)
- Process is using 98.1% CPU and 40GB memory
- Loading 250k Wikipedia articles from pickle file
- This stage can take 5-10 minutes for large pickle files

### Issues Resolved

1. **Memory Error with nvidia/llama-embed-nemotron-8b**
   - Error: `RuntimeError: Invalid buffer size: 64.00 GiB` (batch_size=32)
   - Error: `RuntimeError: Invalid buffer size: 128.00 GiB` (batch_size=8)
   - Root cause: 8B parameter model requires 40GB+ RAM for inference
   - Solution: Switched to Qwen/Qwen3-Embedding-0.6B (600M parameters)

2. **MPS Tensor Size Error with Qwen**
   - Error: `RuntimeError: MPSGaph does not support tensor dims larger than INT_MAX`
   - Root cause: Apple MPS (GPU) backend has tensor size limitations
   - Solution: Forced CPU execution with `device='cpu'` parameter

## Timeline Estimate

| Stage | Duration | Status |
|-------|----------|--------|
| Data Loading | 5-10 min | In progress |
| Model Loading | 1-2 min | Pending |
| Embedding Generation | 2-4 hours (CPU) | Pending |
| UMAP Projection | 10-60 min | Pending |
| Save Files | 2-5 min | Pending |
| **Total** | **~3-5 hours** | |

## Files Being Generated

1. **embeddings_checkpoint_*.pkl** - Checkpoints every 10k items
2. **embeddings.pkl** - Full embeddings cache (~1GB for 1024-dim)
3. **umap_coords.pkl** - UMAP 2D coordinates (~500MB)
4. **knowledge_map.pkl** - Final output (~2-4GB)

## Configuration

- Embedding model: Qwen/Qwen3-Embedding-0.6B
- Embedding dimension: 1024
- Batch size: 32
- Device: CPU (forced, due to MPS limitations)
- Checkpoint frequency: Every 10k items
- Total items: 250,011 (250k Wikipedia + 1 hypertools + 10 questions)

## Known Issues

- **Hypertools loading bug**: Only loading 1 article instead of 3,136
  - Impact: Minimal (1.2% of data missing)
  - Status: Documented, will fix in future run

## Next Steps (After Completion)

1. Verify output files exist and are valid
2. Load knowledge_map.pkl and inspect structure
3. Create KNN-based label generator
4. Update heatmap to zoom on question region

## Monitoring

Check progress with:
```bash
# View log output
tail -f build_qwen_cpu.log

# Check process status
ps aux | grep "build_wikipedia"

# Check generated files
ls -lh *.pkl
```

## Recovery Instructions

If process crashes during embedding generation:
```bash
# Find latest checkpoint
ls -t embeddings_checkpoint_*.pkl | head -1

# Copy to main cache file
cp embeddings_checkpoint_<N>.pkl embeddings.pkl

# Resume from checkpoint
python build_wikipedia_knowledge_map_v2.py
```

---

*Last updated: 2025-11-14 06:31 AM*
