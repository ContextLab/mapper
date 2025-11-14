# Session Summary - November 14, 2025

## Major Discovery and Fix

### Problem Identified
UMAP's `inverse_transform()` was **completely broken** for our use case:
- Cosine similarity: **-0.3381** (embeddings pointing in opposite direction!)
- Embedding norms: 12-30x too large (should be ~1.0)
- Result: Pipeline failures cascading through vec2text → nonsensical labels

### Solution Implemented
Replaced UMAP inverse with **K-nearest neighbors (KNN) interpolation**:
- Cosine similarity: **1.0000** ✅ (PERFECT!)
- Embedding norms: **1.0** ✅ (correct)
- Smooth interpolation between question embeddings ✅

### Remaining Issue
Vec2text still produces nonsensical output even with perfect embeddings, showing the problem is with vec2text itself, not our pipeline.

## New Direction - Wikipedia Knowledge Map

Per your request, we're now building a much better system:

### Architecture

**Data Sources:**
1. **Hypertools wiki dataset** (~hundreds of articles)
2. **Dropbox Wikipedia pickle** (250,000 articles - will sample 10,000)
3. **Quiz questions** (10 items)

**Embedding Model:**
- Switch from `gtr-t5-base` (768-dim) to `nvidia/llama-embed-nemotron-8b` (4096-dim)
- Much better semantic quality

**Label Generation:**
- Use KNN to find k-nearest Wikipedia articles for each grid cell
- Labels come from actual article titles (not vec2text nonsense!)
- Guarantees semantic relevance to nearby content

**Heatmap Zoom:**
- Compute bounding box around questions (with padding)
- Focus visualization on question region
- Much better UX than showing entire UMAP space

### Files Created

**Main Script:**
- [`build_wikipedia_knowledge_map.py`](../build_wikipedia_knowledge_map.py)
  - Loads Wikipedia articles + questions
  - Generates nemotron embeddings
  - Computes UMAP on combined dataset
  - Saves to `knowledge_map.pkl` for reuse

**Diagnostic Scripts:**
- [`debug_umap_inverse.py`](../debug_umap_inverse.py) - Diagnosed UMAP failures
- [`test_knn_interpolation.py`](../test_knn_interpolation.py) - Verified KNN fix
- [`diagnose_pipeline.py`](../diagnose_pipeline.py) - Original comprehensive diagnostic
- [`inspect_wikipedia_data.py`](../inspect_wikipedia_data.py) - Data structure inspection

**Progress Notes:**
- [`2025-11-14_knn-interpolation-fix.md`](2025-11-14_knn-interpolation-fix.md) - Detailed KNN analysis
- [`2025-11-14_pipeline-diagnostics.md`](2025-11-14_pipeline-diagnostics.md) - Diagnostic approach

### Current Status

**Completed:**
- ✅ Downloaded 751MB Wikipedia data (250k articles)
- ✅ Inspected data structure
- ✅ Created comprehensive build script
- ✅ Fixed critical UMAP inverse bug
- ✅ Implemented KNN interpolation
- ✅ hypertools installed and ready

**Next Steps:**

1. **Run the build script** (this will take time - large dataset):
   ```bash
   python build_wikipedia_knowledge_map.py
   ```
   - Loads ~10k Wikipedia articles + 10 questions
   - Generates nemotron embeddings (4096-dim)
   - Computes UMAP projection
   - Saves `knowledge_map.pkl` (~500MB estimated)

2. **Update cell label generation:**
   - Create new version that loads `knowledge_map.pkl`
   - Use KNN to find nearest articles for each cell
   - Generate labels from article titles
   - No more vec2text!

3. **Update heatmap visualization:**
   - Load question bounding box from `knowledge_map.pkl`
   - Zoom to question region (with padding)
   - Better focused visualization

4. **Test and verify:**
   - Spot check labels match nearby articles
   - Verify smooth transitions
   - Ensure questions are in correct positions

### Expected Results

**Label Quality:**
- Near "mitochondria" question → labels from biology articles
- Between "photosynthesis" and "mitochondria" → plant biology/cellular energy
- Peripheral cells → diverse topics from Wikipedia corpus

**Much better than:**
- Current vec2text: "skills and writing skills in a mammoth project at Gibraltar"
- New approach: Actual Wikipedia article titles like "Cellular respiration", "Mitochondrion", "ATP synthase"

## Technical Details

### Wikipedia Data Structure
```python
# Dropbox pickle (250k articles):
{
  'id': '41407254',
  'url': 'https://en.wikipedia.org/wiki/...',
  'title': 'Article Title',
  'text': 'Article content...'
}
```

### Knowledge Map Structure
```python
{
  'metadata': {
    'model': 'nvidia/llama-embed-nemotron-8b',
    'embedding_dim': 4096,
    'num_questions': 10,
    'num_articles': 10000,
    'question_region': {
      'x_min': 0.3, 'x_max': 0.7,
      'y_min': 0.2, 'y_max': 0.8
    }
  },
  'items': [
    {
      'text': '...',
      'title': '...',
      'source': 'question' | 'dropbox' | 'hypertools',
      'embedding': [4096-dim vector],
      'x': 0.5, 'y': 0.5  # Normalized [0,1]
    },
    ...
  ],
  'umap_reducer': <fitted UMAP model>
}
```

### Resource Requirements

**Memory:**
- 10k articles × 4096-dim embeddings = ~160MB
- UMAP model: ~50MB
- Total: ~500MB for pickle file

**Time:**
- Embedding generation: ~5-10 minutes (GPU) or ~30-60 minutes (CPU)
- UMAP fitting: ~2-5 minutes
- Total: ~15-65 minutes depending on hardware

### Benefits of New Approach

1. **Semantic Quality**: Labels from real Wikipedia articles
2. **Scalability**: Can sample more/fewer articles as needed
3. **Reproducibility**: Random seed for consistent results
4. **Flexibility**: Easy to tweak UMAP params and regenerate
5. **Speed**: Precompute once, reuse many times
6. **No vec2text**: Bypass the broken neural inversion entirely

## Files Modified

### Core Pipeline (with KNN fix):
- [`generate_cell_labels.py`](../generate_cell_labels.py)
  - Added `invert_umap_coordinates_knn()` function
  - Deprecated `invert_umap_coordinates()` (UMAP inverse)
  - Updated main pipeline to use KNN
  - Removed validation/repair steps (not needed with KNN)

### New Scripts:
- [`build_wikipedia_knowledge_map.py`](../build_wikipedia_knowledge_map.py) - Main build script
- [`inspect_wikipedia_data.py`](../inspect_wikipedia_data.py) - Data inspection

### Diagnostic Scripts:
- [`debug_umap_inverse.py`](../debug_umap_inverse.py)
- [`test_knn_interpolation.py`](../test_knn_interpolation.py)
- [`diagnose_pipeline.py`](../diagnose_pipeline.py)

## Recommendation

Run the build script now to generate the knowledge map, then we can update the label generation and visualization to use it:

```bash
# This will take 15-65 minutes depending on your hardware
python build_wikipedia_knowledge_map.py

# When complete, you'll have:
# - knowledge_map.pkl (~500MB)
# - Ready for KNN-based label generation
```

The new approach will give you **much better labels** that actually correspond to Wikipedia article titles near each grid cell, instead of vec2text's nonsensical output.
