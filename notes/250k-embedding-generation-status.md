# 250K Embedding Generation Status

## Task Overview
Generating embeddings for all 250,000 Wikipedia articles to improve UMAP neighbor overlap for biology-focused questions.

## Current Status (2025-11-15 Resumed)

### Completed Tasks
1. ✅ Committed UMAP rebuild changes from 25K subset
2. ✅ Updated [scripts/diagnostics/check_question_neighbors.py](../scripts/diagnostics/check_question_neighbors.py:132-144) bounding box padding from 10% to 50%
3. ✅ Embedded 7,000 additional articles (32,000 total: 25K + 7K)

### In Progress
- **Embedding Generation** (Resumed with smaller batch size):
  - Previous attempt: Crashed after 7 checkpoints with MPS OOM error (batch size 128)
  - Current run: Restarted with batch size 32
  - Checkpoint resume: Successfully loaded 32,000 articles
  - Target: 250,000 articles total
  - Remaining: 218,000 articles to generate
  - Checkpoints: Every 1,000 articles
  - Log file: [embeddings_250k_batch32.log](../embeddings_250k_batch32.log)

### Crash Resolution
- **Issue**: MPS out of memory after 7K articles with batch size 128
  - Error: "MPS allocated: 23.43 GiB, other allocations: 102.81 GiB, max allowed: 132.19 GiB"
  - Tried to allocate 6.00 GiB which exceeded limit
- **Solution**: Reduced batch size from 128 → 32 (4x smaller)
- **Recovery**: Checkpoint system worked correctly - resumed from 32,000 articles
- **Default updated**: Changed default batch size in generate_embeddings_checkpointed.py from 128 to 32 for MPS safety

## Previous Results (25K articles)

### UMAP Rebuild Findings
- Neighbor overlap: **4%** (target: >60%)
- Question clustering: Very tight (x=[4.98, 5.01], y=[4.73, 4.77])
- Article spread: Wide (x=[-0.34, 15.52], y=[-2.60, 13.67])
- Articles in question bbox: **0%**

### Root Cause Analysis
Questions are all cellular biology focused, while 25K random articles may not have sufficient biology content. Solution: Embed all 250K articles to increase biology coverage.

## Next Steps

### Pending Tasks
1. Monitor 250K embedding generation completion
2. Rebuild UMAP with full 250K article dataset
3. Re-run [check_question_neighbors](../scripts/diagnostics/check_question_neighbors.py) diagnostic
4. Verify >60% neighbor overlap
5. Document final findings

### Files to Monitor
- `embeddings/wikipedia_embeddings.pkl` - Should grow to 250K x 768
- `embeddings/article_registry.pkl` - Track which articles embedded
- `embeddings/current_checkpoint.pkl` - Checkpoint state
- `embeddings_250k.log` - Generation log

## Key Scripts
- [scripts/rebuild_umap.py](../scripts/rebuild_umap.py) - Rebuild UMAP from embeddings
- [scripts/diagnostics/check_question_neighbors.py](../scripts/diagnostics/check_question_neighbors.py) - Verify neighbor overlap
- [scripts/utils/generate_embeddings_checkpointed.py](../scripts/utils/generate_embeddings_checkpointed.py) - Generate embeddings with checkpoints
- [scripts/export_wikipedia_articles.py](../scripts/export_wikipedia_articles.py) - Export to JSON for visualization

## Estimated Timeline
- 250K embedding generation: ~2-4 hours (based on 25K taking ~X minutes)
- UMAP rebuild: ~30 seconds
- Diagnostic verification: ~10 seconds

## Success Criteria
- [ ] All 250K articles embedded successfully
- [ ] UMAP rebuilt with full dataset
- [ ] Neighbor overlap >60% (at least 3/5 neighbors match)
- [ ] Questions have semantically related nearest neighbors
- [ ] Articles evenly distributed (not all clustered)
