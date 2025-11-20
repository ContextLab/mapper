# Multi-Level Knowledge Map Pipeline - Complete

**Date:** 2025-11-19
**Status:** ✅ Successfully Completed

## Final Results

### Generated Data
- **Articles:** 49,430 unique articles across 5 levels (0-4)
  - Level 0: 46,156 articles (baseline from heatmap)
  - Level 1: 2,205 articles (broader concepts)
  - Level 2: 599 articles (even broader)
  - Level 3: 238 articles (more general)
  - Level 4: 232 articles (most abstract)

- **Questions:** 14,294 multi-choice questions
  - Distributed across 1,457 grid cells (39x39 grid)
  - Multiple difficulty levels per cell
  - Hierarchical parent tracking

- **Concepts:** 64,643 total concepts extracted
  - Level 0: 45,749 concepts
  - Level 1: 10,839 concepts
  - Level 2: 4,503 concepts
  - Level 3: 2,262 concepts
  - Level 4: 1,290 concepts

### Output Files
- `wikipedia_articles.json` (22MB) - Deduplicated articles with hierarchical coordinates
- `cell_questions.json` (28MB) - Questions organized by grid cell

### Key Features
1. **Hierarchical Coordinate Assignment**
   - Level 0 uses original UMAP coordinates (within heatmap)
   - Levels 1-4 inherit averaged coordinates from parent articles
   - Only uses parents within [0,1] heatmap range

2. **Smart Deduplication**
   - Prefers higher-level copies when articles appear in multiple levels
   - Merges duplicates within same level (combines parent references)
   - Removed 1,194 articles with no valid parent coordinates

3. **Question Inheritance**
   - Each question inherits coordinates from its source article
   - Removed 1,618 questions from articles outside heatmap
   - All questions mapped to grid cells for adaptive sampling

## Pipeline Statistics

### Article Generation
- Level 0: 46,185 articles → 46,156 kept (29 outside heatmap)
- Level 1: 4,247 generated → 2,205 kept (373 removed, 342 duplicates, 318 merged)
- Level 2: 1,744 generated → 599 kept (324 removed, 1,334 duplicates, 93 merged)
- Level 3: 884 generated → 238 kept (245 removed, 793 duplicates, 45 merged)
- Level 4: 499 generated → 232 kept (252 removed, 466 duplicates, 15 merged)

### Question Distribution
- Total questions: 15,912 generated → 14,294 kept
- Unique cells: 1,457 (out of 1,521 possible)
- Average questions per cell: ~9.8
- Coverage: 95.8% of heatmap cells have at least one question

## Technical Improvements

### Bug Fixes
1. **UMAP Segfault Fix**
   - Changed embedding model from `all-MiniLM-L6-v2` (384-dim) to `google/embeddinggemma-300m` (768-dim)
   - Implemented subprocess approach for UMAP projection to avoid library conflicts

2. **Checkpoint Resume Logic**
   - Added automatic checkpoint detection and resume
   - Skips completed steps when resuming from crash

3. **Git History Cleanup**
   - Removed 700MB+ of large checkpoint files from history
   - Files kept locally but excluded from commits

### Performance
- Level 0: ~3 hours (concept extraction + question generation)
- Level 1: ~3.5 hours (article suggestion + download + embedding + concepts + questions)
- Level 2: ~3 hours
- Level 3: ~2 hours
- Level 4: ~1.5 hours
- **Total pipeline time:** ~13 hours

## Next Steps

1. ✅ Test integration with `adaptive_sampler_multilevel.js`
2. ✅ Validate RBF-based knowledge estimation with real data
3. ✅ Deploy to production (index.html + demo pages)
4. Future: Generate additional levels if needed (pipeline is fully automated)

## Files

### Scripts
- `scripts/generate_level_n.py` - Multi-level pipeline with checkpoint resume
- `scripts/merge_multi_level_data.py` - Hierarchical merge with coordinate assignment
- `adaptive_sampler_multilevel.js` - RBF-based adaptive sampling

### Data
- `wikipedia_articles.json` - Final merged articles (stripped, deduplicated)
- `cell_questions.json` - Questions organized by grid cell
- `wikipedia_articles_level_{0-4}.json` - Per-level article files (excluded from git)
- `cell_questions_level_{0-4}.json` - Per-level question files (excluded from git)
- `level_{0-4}_concepts.json` - Per-level concept files (excluded from git)

### Validation
- `notes/merge_validation_report.json` - Merge validation details
- All validation checks passed ✓

---

**Pipeline Status:** Complete and ready for production deployment
