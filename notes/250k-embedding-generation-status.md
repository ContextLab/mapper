# 250K Embedding Generation Status

## Task Overview
Generating embeddings for all 250,000 Wikipedia articles to improve UMAP neighbor overlap for biology-focused questions.

## Current Status (2025-11-15 COMPLETED)

### Completed Tasks
1. ✅ Committed UMAP rebuild changes from 25K subset
2. ✅ Updated [scripts/diagnostics/check_question_neighbors.py](../scripts/diagnostics/check_question_neighbors.py:132-144) bounding box padding from 10% to 50%
3. ✅ Generated embeddings for all 250,000 Wikipedia articles
4. ✅ Rebuilt UMAP with full 250K dataset
5. ✅ Ran neighbor diagnostic analysis

### Final Embedding Generation Results
- **Status**: ✅ COMPLETED successfully
- **Total articles embedded**: 250,000
- **Embedding dimension**: 768
- **File size**: 794.47 MB
- **Total time**: 5 hours 11 minutes (18,668.95 seconds)
- **Processing rate**: 12.05 articles/sec
- **Batch size**: 32 (safe for MPS)
- **Checkpoints**: 225 total (every 1,000 articles)
- **Memory issues**: None with batch size 32
- **Log file**: [embeddings_250k_batch32.log](../embeddings_250k_batch32.log)

### Crash Resolution
- **Issue**: MPS out of memory after 7K articles with batch size 128
  - Error: "MPS allocated: 23.43 GiB, other allocations: 102.81 GiB, max allowed: 132.19 GiB"
  - Tried to allocate 6.00 GiB which exceeded limit
- **Solution**: Reduced batch size from 128 → 32 (4x smaller)
- **Recovery**: Checkpoint system worked correctly - resumed from 32,000 articles
- **Default updated**: Changed default batch size in generate_embeddings_checkpointed.py from 128 to 32 for MPS safety

## Results Summary

### 250K Article Results (Final)

**UMAP Rebuild** (completed in ~3.5 minutes):
- Total coordinates: 250,010 (250K articles + 10 questions)
- Question clustering: Very tight (x=[6.597, 6.942], y=[10.317, 10.444])
- Article spread: Full range (x=[-8.935, 14.374], y=[-3.624, 19.695])
- Articles in question bbox (50% padding): **470 / 250,000 (0.2%)**

**Neighbor Overlap Analysis**:
- Average overlap: **0.0/5 (0%)** - NO IMPROVEMENT from 25K
- For all 10 questions: 0% of top-5 neighbors match between embedding and UMAP space
- Target was >60% (at least 3/5 neighbors match)

**Example - Question 1 (Mitochondria)**:
- UMAP coord: (6.894, 10.412)
- Embedding neighbors: Macropinosome (0.35), Oxidative phosphorylation (0.35), Mir-186 (0.35)
- UMAP neighbors: Transducin (0.013), Ribosome-inactivating protein (0.014), Transcobalamin (0.021)
- **Overlap: 0/5**

**Key Observation**: UMAP neighbors ARE biology-related (Transducin, Ribosome-inactivating protein, Photosynthetic pigment, DNA shuffling), but they are NOT the same biology articles that the embedding space finds semantically closest.

### 25K Article Results (Previous)

**UMAP Rebuild Findings**:
- Neighbor overlap: **4%** (target: >60%)
- Question clustering: Very tight (x=[4.98, 5.01], y=[4.73, 4.77])
- Article spread: Wide (x=[-0.34, 15.52], y=[-2.60, 13.67])
- Articles in question bbox: **0%**

**Root Cause Hypothesis (REJECTED)**: Initially hypothesized that 25K random articles didn't have sufficient biology content. However, testing with all 250K articles shows this was NOT the problem.

## Analysis and Conclusions

### Root Cause: UMAP Dimensionality Reduction Limitation

The problem is **NOT** insufficient article coverage, but rather a fundamental limitation of UMAP's dimensionality reduction from 768-dim to 2-dim:

1. **Embedding space (768-dim)**: Questions correctly find semantically related articles
   - "Mitochondria" → Macropinosome, Oxidative phosphorylation (cosine similarity ~0.35)
   - "Photosynthesis" → Solar Power, Plant perception, Photosynthetic pigment (similarity ~0.39-0.40)
   - "DNA bonds" → Heavy strand, Molecular models of DNA, DNA-binding domain (similarity ~0.46)

2. **UMAP space (2-dim)**: Questions find different biology articles based purely on 2D proximity
   - "Mitochondria" → Transducin, Ribosome-inactivating protein (Euclidean distance ~0.01-0.02)
   - Both sets are biology-related, but UMAP cannot preserve the specific semantic relationships

3. **Information loss**: Reducing from 768 dimensions to 2 dimensions necessarily discards most of the semantic structure. UMAP optimizes for local structure preservation, but "local" in 768-dim space ≠ "local" in 2-dim space.

### Why 250K Articles Didn't Help

The hypothesis was that 25K articles lacked sufficient biology content. However:
- With 250K articles, only 470 (0.2%) fall within the question bounding box
- Questions cluster very tightly in 2D (x range: 0.345, y range: 0.127)
- Articles are spread across the full UMAP space (x range: 23.3, y range: 23.3)
- The ratio got WORSE: 0% in bbox with 250K vs 0% in bbox with 25K

### Potential Solutions

1. **Accept the limitation**: Use embeddings directly for search/retrieval, use UMAP only for visualization
2. **Increase UMAP dimensions**: Use 3D, 5D, or 10D instead of 2D (trades off visualization for accuracy)
3. **Different UMAP parameters**: Experiment with `n_neighbors`, `min_dist`, `metric`
4. **Alternative methods**: Try t-SNE, PaCMAP, TriMAP for better local structure preservation
5. **Supervised UMAP**: Use topic labels to guide the reduction (requires labeled data)

## Success Criteria Results

- [x] All 250K articles embedded successfully ✅
- [x] UMAP rebuilt with full dataset ✅
- [ ] Neighbor overlap >60% (at least 3/5 neighbors match) ❌ **Got 0%**
- [ ] Questions have semantically related nearest neighbors ❌ **Different articles in each space**
- [x] Articles evenly distributed (not all clustered) ✅

**Overall**: The experiment successfully generated all embeddings and rebuilt UMAP, but failed to achieve the target neighbor overlap, revealing that the issue is inherent to dimensionality reduction rather than data coverage.

## Key Files

**Data Files**:
- [embeddings/wikipedia_embeddings.pkl](../embeddings/wikipedia_embeddings.pkl) - 250K × 768 embeddings (794.47 MB)
- [embeddings/article_registry.pkl](../embeddings/article_registry.pkl) - Registry of embedded articles
- [data/umap_reducer.pkl](../data/umap_reducer.pkl) - Trained UMAP model
- [data/umap_bounds.pkl](../data/umap_bounds.pkl) - Coordinate normalization bounds
- [neighbor_analysis.json](../neighbor_analysis.json) - Detailed neighbor comparison
- [neighbor_diagnostic_250k.log](../neighbor_diagnostic_250k.log) - Full diagnostic output

**Scripts**:
- [scripts/rebuild_umap.py](../scripts/rebuild_umap.py) - Rebuild UMAP from embeddings
- [scripts/diagnostics/check_question_neighbors.py](../scripts/diagnostics/check_question_neighbors.py) - Verify neighbor overlap
- [scripts/utils/generate_embeddings_checkpointed.py](../scripts/utils/generate_embeddings_checkpointed.py) - Generate embeddings with checkpoints

**Log Files**:
- [embeddings_250k_batch32.log](../embeddings_250k_batch32.log) - Embedding generation log (5h 11min)
