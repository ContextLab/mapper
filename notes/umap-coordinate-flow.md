# UMAP Coordinate Flow Analysis

## Problem Statement

Questions and articles have 0% overlap in UMAP neighbor space, indicating the UMAP projection is broken. This document traces how coordinates are computed to identify where the mismatch occurs.

## Expected Flow (from build_wikipedia_knowledge_map_v2.py)

The UMAP coordinates SHOULD be computed as follows:

### Step 1: Load Precomputed Embeddings (Line 123-158)
```python
# Load Wikipedia embeddings
wiki_embeddings = load('embeddings/wikipedia_embeddings.pkl')  # Shape: (25000, 768)

# Load question embeddings
question_embeddings = load('embeddings/question_embeddings.pkl')  # Shape: (10, 768)

# COMBINE embeddings (articles FIRST, then questions)
combined_embeddings = np.vstack([wiki_embeddings, question_embeddings])  # Shape: (25010, 768)
```

**Key:** Articles occupy indices [0:25000], questions occupy indices [25000:25010]

### Step 2: Compute UMAP on Combined Data (Line 610-611)
```python
# Fit UMAP on ALL embeddings together
coords_2d, reducer = compute_umap_embeddings(combined_embeddings)  # Shape: (25010, 2)
```

This creates a SINGLE coordinate system where:
- coords_2d[0:25000] = article coordinates
- coords_2d[25000:25010] = question coordinates

All points are in the same UMAP space!

### Step 3: Extract Question Coordinates (Line 356-417)
```python
# Extract question coords from combined projection
question_coords = coords_2d[article_count:, :]  # indices 25000:25010

# Normalize to [0, 1] using GLOBAL bounds
x_min, x_max = coords_2d[:, 0].min(), coords_2d[:, 0].max()  # ALL points
y_min, y_max = coords_2d[:, 1].min(), coords_2d[:, 1].max()

coords_normalized[:, 0] = (question_coords[:, 0] - x_min) / (x_max - x_min)
coords_normalized[:, 1] = (question_coords[:, 1] - y_min) / (y_max - y_min)

# Save to data/question_coordinates.pkl
```

### Step 4: Save UMAP Bounds (Line 419-480)
```python
bounds_data = {
    'global': { x_min, x_max, y_min, y_max },  # ALL points
    'articles': { a_x_min, a_x_max, a_y_min, a_y_max },  # Articles only
    'questions': { q_x_min, q_x_max, q_y_min, q_y_max }  # Questions only
}

# Save to data/umap_bounds.pkl
```

### Step 5: Save UMAP Reducer (Line 337-353)
```python
# Save reducer for transforming NEW embeddings
with open('umap_coords.pkl', 'wb') as f:
    pickle.dump({
        'coords_2d': coords_2d,  # Full (25010, 2) array
        'reducer': reducer        # Trained UMAP model
    }, f)

# Also saved in data/umap_reducer.pkl
```

## Actual Flow (What's Happening Now)

### In Our Diagnostic Script

```python
# Load UMAP reducer
reducer = load('data/umap_reducer.pkl')

# Transform articles SEPARATELY
article_coords = reducer.transform(article_embeddings)  # (25000, 2)

# Transform questions SEPARATELY
question_coords = reducer.transform(question_embeddings)  # (10, 2)
```

**This is CORRECT** - using the same trained reducer on both should give consistent coordinates.

## The Mystery

Our diagnostic showed:
- Question UMAP coords: x ∈ [-9.695, -5.955], y ∈ [8.925, 12.419]
- Article UMAP coords: x ∈ [-10.575, -5.627], y ∈ [8.432, 13.560]
- 91.1% of articles (22,774 / 25,000) are within question bounding box ✓

**BUT:** Nearest neighbors in UMAP space are semantically WRONG
- Question 1 (mitochondria) → Nearest UMAP: "Kutsuki, Shiga", "Areius", "water polo"
- Question 1 (mitochondria) → Nearest Embedding: "Mir-186 microRNA", "Exopher", "DGUOK" ✓

## Root Cause Hypothesis

The UMAP reducer at [data/umap_reducer.pkl](../data/umap_reducer.pkl) was trained on a DIFFERENT dataset than our current embeddings!

### Evidence:
1. **0% overlap** between embedding and UMAP neighbors for ALL 10 questions
2. UMAP neighbors are semantically random (geography terms for biology questions)
3. Embedding neighbors are semantically correct

### Likely Scenario:

The UMAP was trained on OLD embeddings (possibly from a different model or different articles), then saved. When we:
1. Generated NEW embeddings with google/embeddinggemma-300m
2. Transformed them using the OLD UMAP reducer
3. The reducer mapped them to random locations (wrong semantic space)

## Solution

We need to retrain UMAP by running [build_wikipedia_knowledge_map_v2.py](../scripts/build_wikipedia_knowledge_map_v2.py) which will:

1. Load current embeddings (25,000 articles + 10 questions)
2. Stack them together
3. **Fit UMAP on the combined dataset** (creates new reducer)
4. Extract and save coordinates

This ensures the UMAP space matches the embedding space.

## Verification Checklist

After retraining UMAP, verify:
- [ ] UMAP neighbor overlap > 60% (at least 3/5 neighbors match embedding space)
- [ ] Question nearest neighbors are semantically related
- [ ] Articles are evenly distributed (not all clustered in one corner)
- [ ] Coordinate bounds are reasonable (not extreme values)

## Files to Check

**Input:**
- `embeddings/wikipedia_embeddings.pkl` - 25,000 articles (google/embeddinggemma-300m, 768-dim)
- `embeddings/question_embeddings.pkl` - 10 questions (google/embeddinggemma-300m, 768-dim)

**Output:**
- `umap_coords.pkl` - Full UMAP coordinates for 25,010 items
- `data/umap_reducer.pkl` - Trained UMAP model
- `data/umap_bounds.pkl` - Coordinate bounds
- `data/question_coordinates.pkl` - Extracted question coordinates
- `knowledge_map.pkl` - Final knowledge map

**Command to Run:**
```bash
python3 scripts/build_wikipedia_knowledge_map_v2.py
```

This will take 10-60 minutes but will create a proper UMAP projection.
