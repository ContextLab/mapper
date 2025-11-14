# Critical Memory Issue - November 14, 2025

## Problem

The `nvidia/llama-embed-nemotron-8b` model is **too large** for the available system memory when processing even small batches.

### Error History

1. **First attempt** (batch_size=32): `RuntimeError: Invalid buffer size: 64.00 GiB`
2. **Second attempt** (batch_size=8): `RuntimeError: Invalid buffer size: 128.00 GiB`

## Root Cause

The model is an 8B parameter Llama-based model that requires substantial memory for:
- Model weights (~16GB for fp16)
- Activation memory during forward pass
- Batch processing overhead

Even with batch_size=1, processing 250k items would be extremely slow (potentially 10-20+ hours on CPU).

## Solutions

### Option 1: Use Smaller Embedding Model (RECOMMENDED)

Switch to a more memory-efficient model:

**Recommended**: `sentence-transformers/all-mpnet-base-v2`
- Dimensions: 768 (vs 4096 for nemotron)
- Memory: ~1GB (vs ~16GB+ for nemotron)
- Quality: Still excellent for semantic similarity
- Speed: Much faster

**Alternative**: `sentence-transformers/all-MiniLM-L12-v2`
- Dimensions: 384
- Memory: ~500MB
- Quality: Good for most tasks
- Speed: Very fast

### Option 2: Process with Batch Size 1 (NOT RECOMMENDED)

```python
actual_batch_size = 1
```

**Cons**:
- 10-20+ hours for 250k items on CPU
- Still might hit memory limits
- Not practical

### Option 3: Use Cloud/GPU Resources

- Run on Google Colab Pro (High RAM runtime)
- Use AWS/Azure with large memory instances
- Rent GPU with 40GB+ VRAM

## Recommended Path Forward

**Use `sentence-transformers/all-mpnet-base-v2`:**

1. **Quality**: Still produces high-quality embeddings suitable for KNN-based labeling
2. **Speed**: 10-50x faster than nemotron
3. **Memory**: Fits comfortably in typical system RAM
4. **Compatibility**: Works with existing pipeline

**Implementation**:
```python
model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
# 768-dim embeddings, much faster, lower memory
```

**Trade-offs**:
- Slightly lower semantic resolution (768-dim vs 4096-dim)
- For KNN-based label generation, 768-dim is more than sufficient
- The quality difference is minimal for this use case

## Updated Timeline with all-mpnet-base-v2

| Stage | Estimated Duration |
|-------|-------------------|
| Data Loading | 5-10 min |
| Model Download | 1-2 min |
| Embedding Generation | 30-90 min |
| UMAP Projection | 10-60 min |
| Saving Files | 2-5 min |
| **Total** | **~1-3 hours** |

## What Was Accomplished

✓ Downloaded Wikipedia data (250k articles)
✓ Loaded hypertools library
✓ Created comprehensive build script with caching
✓ Fixed hypertools loading bug (documented, needs implementation)
✓ Implemented memory-efficient batching
✓ Implemented checkpoint system

## What's Blocked

❌ Embedding generation with nvidia/llama-embed-nemotron-8b
  - Reason: Insufficient memory (requires 40GB+ RAM/VRAM)
  - Solution: Switch to smaller model

## Next Steps

1. **Modify `build_wikipedia_knowledge_map_v2.py`**:
   - Change model from `nvidia/llama-embed-nemotron-8b` to `sentence-transformers/all-mpnet-base-v2`
   - Keep all other logic the same

2. **Run the build** (should complete in 1-3 hours)

3. **Verify output** and continue with KNN label generation

4. **Optional**: Re-run with nemotron on cloud if higher dimensional embeddings are desired

## Files for Reference

- [build_wikipedia_knowledge_map_v2.py](../build_wikipedia_knowledge_map_v2.py) - Build script (needs model change)
- [build_knowledge_map_fixed.log](../build_knowledge_map_fixed.log) - Latest error log
- [notes/2025-11-14_overnight-build.md](2025-11-14_overnight-build.md) - Original build plan
- [AUTONOMOUS_PROGRESS.md](../AUTONOMOUS_PROGRESS.md) - Progress tracker

## Decision Point

**User should decide**:
1. Use smaller model (all-mpnet-base-v2) and proceed quickly
2. Provision cloud resources to use nemotron
3. Use batch_size=1 with nemotron (very slow, may still fail)

**My recommendation**: Use all-mpnet-base-v2. The 768-dim embeddings are more than adequate for KNN-based label generation, and we can always re-run with a larger model later if needed.
