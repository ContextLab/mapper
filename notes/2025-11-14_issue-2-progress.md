# Issue #2 Progress - Cell Label Generation
Date: 2025-11-14
Branch: feature/cell-labels

## Summary

Successfully implemented heatmap cell label generation using vec2text neural inversion and LLM labeling. The system uses UMAP inverse transform to recover embeddings from 2D coordinates, then vec2text to recover semantic text, which is used for labeling.

## Key Accomplishments

### ✅ Completed Tasks

1. **UMAP Model Saving** (Commit: 4eaebef)
   - Modified generate_embeddings.py to save fitted UMAP reducer
   - Added `--save-reducer` flag
   - Saves umap_reducer.pkl (37KB) and umap_bounds.pkl (84B)

2. **gtr-base Model Migration** (Commits: cf94027, subagents)
   - Changed from all-MiniLM-L6-v2 (384-dim) to gtr-base (768-dim)
   - Reason: gtr-base is supported by vec2text for neural inversion
   - Fixed critical DataFrame truncation bug (.values conversion)
   - Regenerated questions.json with 768-dim embeddings (108KB)

3. **generate_cell_labels.py Implementation** (Commit: c4ef180)
   - Complete 5-phase pipeline:
     - Phase 1: UMAP inverse_transform (2D → 768D)
     - Phase 2: Embedding validation and repair
     - Phase 3: Vec2text token recovery (embedding → text)
     - Phase 4: Token filtering
     - Phase 5: LM Studio label generation
   - 5-step hybrid embedding repair strategy
   - Caching system with SHA256 validation
   - Quality scoring for inverted embeddings

4. **Vec2text Integration** (Commit: d1b4c59)
   - Fixed device compatibility (MPS vs CPU tensor mismatch)
   - Auto-detect model device and match embedding tensor
   - **Fixed prompt**: Now passes full recovered text to LLM instead of tokenized weights
   - Successfully tested with 3×3 grid - 100% cell completion

5. **HTML Integration** (Commit: f40436b)
   - Added loadCellLabels() function
   - Added calculateCellKnowledge() using same Gaussian kernel as heatmap
   - Updated showHeatmapTooltip() to display:
     - Cell label from vec2text
     - Inferred knowledge percentage
   - Graceful fallback for missing labels file

### 🔬 Testing Results

**3×3 Grid Test:**
- Total cells: 9
- Unique labels: 9 (100%)
- Avg quality score: 1.00
- Vec2text successfully recovered tokens for all cells
- Example recovered text:
  - "gimmicks of art at belco/patino. Write original chapter book at belco/patino (or"
  - "art/writing sample book projects atlain with beccoids.       (also"

### 🐛 Critical Bugs Fixed

1. **DataFrame Truncation** (cf94027)
   - datawrangler returns DataFrame, not numpy array
   - `.tolist()` was truncating embeddings to 10 values instead of 768
   - Fixed with `.values` conversion

2. **Device Mismatch** (d1b4c59)
   - Vec2text model loaded on MPS, embedding tensor on CPU
   - Fixed by auto-detecting model device and moving tensor to match

3. **Prompt Format** (d1b4c59)
   - Was passing tokenized word/weight pairs to LLM
   - Now passes full recovered text from vec2text

### 📁 Files Modified

- [generate_embeddings.py](generate_embeddings.py:215-239): UMAP saving, model change
- [generate_cell_labels.py](generate_cell_labels.py): Complete implementation
- [questions.json](questions.json): Regenerated with 768-dim gtr-base embeddings
- [umap_reducer.pkl](umap_reducer.pkl): Fitted UMAP model
- [umap_bounds.pkl](umap_bounds.pkl): Coordinate bounds for denormalization
- [index.html](index.html:598-639,1018-1039): Cell label loading and tooltip display
- [requirements.txt](requirements.txt:21-22): Added vec2text, requests
- [.gitignore](.gitignore): Added cache files

## Outstanding Tasks

### ⚠️ Pending

1. **LM Studio Integration Testing**
   - Current issue: Labels mostly empty (LM Studio not running)
   - Need to verify:
     - LM Studio running on port 1234
     - gpt-oss-20B model loaded
     - API endpoint `/v1/chat/completions` accessible
   - Prompt now fixed to use full recovered text

2. **Create test_cell_labels.py**
   - REAL tests (no mocks) for:
     - UMAP inverse_transform roundtrip
     - Vec2text token recovery
     - LM Studio API integration
     - Caching system

3. **Generate Full 40×40 Grid**
   - Run: `python generate_cell_labels.py --grid-size 40`
   - Manually verify label quality
   - Check for pain points from issue:
     - Strange/non-sensical tokens
     - GPT-oss-20B formatting issues
     - Label uniqueness

4. **Browser Testing**
   - Start server: `python -m http.server 8000`
   - Test tooltips with existing 3×3 labels
   - Verify knowledge percentage calculation

5. **Merge and Close Issue**
   - Final commit and push
   - Create pull request
   - Close issue #2

## Key Technical Details

### Vec2text Integration
- **Model**: gtr-base (768-dim)
- **Output**: Well-formed sentences, not just tokens
- **Example**: "gimmicks of art at belco/patino. Write original chapter book..."
- **API**: `vec2text.invert_embeddings(embeddings, corrector, num_steps=10, beam_width=2)`

### Embedding Repair Strategy
1. L2 normalization to reference mean
2. Clip outliers to ±3σ
3. PCA projection onto reference subspace
4. Re-normalization to target norm
5. Nearest neighbor blending for very low quality

### Caching System
- Hash: SHA256 of questions.json
- Invalidates cache when questions change
- Stores recovered embeddings and tokens

### HTML Knowledge Calculation
```javascript
const sigma = 0.15; // Same as heatmap
weight = exp(-(dist² / (2σ²)))
knowledge = Σ(weight × isCorrect) / Σ(weight)
```

## Commands for Next Session

```bash
# Continue from current branch
git checkout feature/cell-labels

# Test with LM Studio (if running)
python generate_cell_labels.py --grid-size 3 --verbose

# Generate full 40×40 grid
python generate_cell_labels.py --grid-size 40

# Test in browser
python -m http.server 8000
# Open http://localhost:8000/index.html

# Create real tests
# (create test_cell_labels.py with actual API calls)

# When ready to merge
git checkout main
git merge feature/cell-labels
git push
gh issue close 2
```

## Notes for Future Work

- Consider adding progress bars for large grids
- May need to adjust embedding repair thresholds for different datasets
- Could experiment with different vec2text parameters (num_steps, beam_width)
- Consider alternative labeling approaches if LM Studio proves unreliable
- Could add caching for LM Studio responses to avoid redundant API calls

## GitHub Issue Comments
- Posted vec2text success update: https://github.com/simpleXknowledge/mapper.io/issues/2#issuecomment-3530876925
- Clarified vec2text output format: https://github.com/simpleXknowledge/mapper.io/issues/2#issuecomment-3530879711
