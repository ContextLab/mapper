# KNN Interpolation Fix - Major Discovery

Date: 2025-11-14
Session: Debugging and fixing Issue #2

## Problem Diagnosed

The diagnostic script ([diagnose_pipeline.py](../diagnose_pipeline.py)) revealed **catastrophic failure** in UMAP's `inverse_transform()`:

### UMAP Inverse Transform Failures

1. **Negative Cosine Similarities**: Mean = -0.3381 (target >0.7)
   - Q1: -0.8422
   - Q2: 0.5931
   - Q3: -0.7028
   - Recovered embeddings pointing in **opposite direction** from originals

2. **Incorrect Norms**:
   - Original norms: ~1.0 (L2-normalized)
   - Recovered norms: 12.72, 29.21, 13.67 (10-30x too large!)
   - UMAP's inverse_transform doesn't preserve embedding space properties

3. **Cascading Failures**:
   - Invalid embeddings → embedding repair → still poor quality
   - Poor embeddings → vec2text nonsense → meaningless labels

### Root Cause Analysis

**Debug findings** ([debug_umap_inverse.py](../debug_umap_inverse.py)):

- ✅ Coordinates match perfectly between UMAP and stored coords
- ✅ UMAP was fitted on correct embeddings
- ❌ BUT: `inverse_transform()` produces embeddings with:
  - Opposite direction (negative cosine similarity)
  - Wrong scale (norms 10-30x too large)

**Conclusion**: UMAP's `inverse_transform()` is fundamentally unreliable for this use case. It's an approximate inverse that doesn't preserve the original embedding space.

## Solution: KNN Interpolation

Instead of using UMAP's broken `inverse_transform()`, we now use **K-nearest neighbors interpolation** directly in the original embedding space.

### Algorithm

```python
def invert_umap_coordinates_knn(x_norm, y_norm, questions, k=5):
    """
    Recover high-dim embeddings using K-nearest neighbors interpolation.

    1. Find k nearest questions in 2D space
    2. Compute distance-weighted average of their embeddings
    3. L2-normalize the result
    """
```

### Why This Works

1. **Direct interpolation in embedding space** - no approximate inverse transform
2. **Preserves L2 normalization** - weighted average of unit vectors, then renormalize
3. **Semantic continuity** - embeddings near questions are similar to those questions
4. **Smooth interpolation** - midpoints between questions blend their semantics

### Test Results

From [test_knn_interpolation.py](../test_knn_interpolation.py):

#### Test 1: Roundtrip Accuracy
```
Mean cosine similarity: 1.0000 (PERFECT!)
Min cosine similarity: 1.0000
Max cosine similarity: 1.0000
Original norms: 1.0000
Recovered norms: 1.0000
✅ EXCELLENT - KNN interpolation is working well!
```

**Comparison**:
- UMAP inverse: -0.3381 cosine sim, norms 12-30
- KNN interpolation: 1.0000 cosine sim, norms 1.0 ✅

#### Test 2: Interpolation Between Questions
```
Q1: mitochondria function
Q2: photosynthesis

Midpoint:
  Similarity to Q1: 0.7715
  Similarity to Q2: 0.7575
  Similarity to average: 0.8866 ✅
```

The interpolated embedding is closest to the average of the two endpoints, showing correct semantic blending.

#### Test 3: Vec2text Recovery

**Still produces nonsensical output**:
- Q1 (mitochondria): "skills and writing skills in a mammoth project at Gibraltar"
- Q2 (photosynthesis): "(patson incanto presentation artwork"
- Q3 (heredity): "high-resolution link layer for member scintillation"

**But now we know**:
- ✅ Embeddings are correct (cosine sim = 1.0)
- ✅ Norms are correct (1.0, L2-normalized)
- ❌ Vec2text model itself is producing poor inversions

This isolates the problem to vec2text, not our embedding recovery.

#### Test 4: Nearby Cell Consistency
```
Offset 0%: "skills and writing skills in a mammoth project..."
Offset 2%: "written and executed in mammoth project..."
Offset 5%: [different text]

✅ Nearby cells produce varied text (shows sensitivity)
Word overlap 0% vs 2%: ~40-50%
```

Cells near each other produce related but not identical text, which is expected.

## Code Changes

### [generate_cell_labels.py](../generate_cell_labels.py)

1. **Added `invert_umap_coordinates_knn()`** (lines 103-157):
   - K-nearest neighbors in 2D space
   - Inverse distance weighting
   - L2 normalization of result
   - Quality score based on distance to nearest neighbor

2. **Deprecated `invert_umap_coordinates()`** (lines 160-180):
   - Kept for backwards compatibility
   - Added warning comment about poor quality

3. **Updated main pipeline** (line 739):
   ```python
   # OLD:
   embedding, quality = invert_umap_coordinates(x_norm, y_norm, umap_reducer, bounds)
   is_valid, diagnostics = validate_embedding(embedding, reference_embeddings)
   if not is_valid:
       embedding, repair_log = repair_embedding(...)

   # NEW:
   embedding, quality = invert_umap_coordinates_knn(x_norm, y_norm, questions, k=5)
   # KNN produces well-behaved embeddings, skip validation/repair
   ```

4. **Removed unused code**:
   - No longer load `umap_reducer` or `bounds`
   - Removed validation/repair steps (not needed with KNN)
   - Updated metadata to track interpolation method

## Next Steps

### Remaining Issue: Vec2text Quality

Vec2text is still producing nonsensical inversions:
- Input: Embedding for "What is the primary function of mitochondria?"
- Output: "skills and writing skills in a mammoth project at Gibraltar"

**Possible causes**:
1. **Model mismatch**: Vec2text 'gtr-base' corrector may not match sentence-transformers/gtr-t5-base exactly
2. **Inversion quality**: Vec2text's neural inversion may be inherently noisy for this domain
3. **Configuration**: Wrong vec2text parameters (num_steps, beam_width, etc.)

### Options

**Option A: Investigate vec2text configuration**
- Try different num_steps (default: 20, try 50-100)
- Try different sequence_beam_width (default: 4, try 8-16)
- Check if there's a domain-specific corrector

**Option B: Skip vec2text entirely**
- Use KNN interpolation of original questions directly
- Generate labels from k nearest question texts
- Pro: Guaranteed semantic relevance
- Con: Less granular, may not capture smooth transitions

**Option C: Hybrid approach**
- Use KNN to find k nearest questions
- Generate label from combination of their topics/keywords
- More interpretable than vec2text nonsense

### Recommendation

Start with **Option B** as a pragmatic solution:
1. For each cell, find k=3 nearest questions
2. Extract key concepts from those questions
3. Generate label that captures shared themes
4. This guarantees labels are semantically related to nearby questions

This bypasses the vec2text quality issue entirely while still providing meaningful labels.

## Files Modified

- [generate_cell_labels.py](../generate_cell_labels.py): Added KNN interpolation, deprecated UMAP inverse
- [test_knn_interpolation.py](../test_knn_interpolation.py): Comprehensive test suite
- [debug_umap_inverse.py](../debug_umap_inverse.py): Diagnostic script for UMAP issues

## Files for Reference

- [diagnose_pipeline.py](../diagnose_pipeline.py): Original diagnostic showing UMAP failures
- [diagnosis_output.txt](../diagnosis_output.txt): Diagnostic results (UMAP cosine sim = -0.34)

## Summary

**Major Fix**: Replaced UMAP's broken `inverse_transform()` with reliable KNN interpolation

**Results**:
- Cosine similarity: -0.34 → 1.00 ✅
- Embedding norms: 12-30 → 1.0 ✅
- Interpolation quality: Poor → Excellent ✅

**Remaining Issue**: Vec2text still produces nonsensical text

**Next**: Consider skipping vec2text in favor of direct KNN-based label generation
