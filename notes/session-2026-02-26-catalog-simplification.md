# Session Notes: Video Catalog Simplification — 2026-02-26

## Key Decision

**Eliminated domain-based video assignment entirely.** The video recommendation
engine scores videos spatially using window coordinates against the GP grid.
Domain labels are never used in the math — `filterByDomain()` was a no-op.

## What Changed

### Removed
- `scripts/export_video_bundles.py` — domain assignment, per-domain JSON files
- `filterByDomain()` from `video-recommender.js`
- `domainId` parameter from `computeRanking()`
- Per-domain video loading queue in `video-loader.js`
- `$watchedVideos` unused import in `video-recommender.js`

### Added
- `scripts/export_video_catalog.py` — single `data/videos/catalog.json`
  - 3,120 videos, 42,151 windows, 1.5 MB (gzips to ~250KB)
  - No domain assignment logic needed

### Updated
- `src/domain/video-loader.js` — fetches single catalog.json
- `src/app.js` — simplified video loading (no domain IDs passed)
- `src/learning/video-recommender.js` — `computeRanking()` takes 4 args (no domainId)
- `tests/algorithm/video-recommender.test.js` — removed filterByDomain test, cleaned up args
- `scripts/run_video_pipeline.sh` — references new export script
- `.gitignore` — added `data/videos/catalog.json`

## Why This Is Better

1. **One fetch vs 50** — single catalog.json instead of per-domain files
2. **No spatial mismatch problem** — domain bounding boxes were misaligned with
   video coordinates (videos clustered in different UMAP region than articles)
3. **Simpler pipeline** — eliminated entire domain-assignment stage
4. **Recommendation engine unchanged** — it was already spatial-only

## Test Results
- Build: 41 modules, passes
- JS algorithm tests: 67 pass (removed 1 obsolete filterByDomain test)
- Python sliding-window tests: 30 pass
- Pipeline dry run: end-to-end success

## Pipeline Architecture (Final)
```
transcripts (tensor02)
    ↓
embed_video_windows.py  → .npy per video (512-word windows, 50-word stride)
    ↓
project_video_coords.py → .json per video ([x, y] pairs, UMAP projected)
    ↓
export_video_catalog.py → data/videos/catalog.json (single file, all videos)
    ↓
video-loader.js         → single fetch at startup
    ↓
video-recommender.js    → TLP/ExpectedGain scoring (spatial, no domain labels)
```

## Remaining Work
- Tensor02 transcripts still processing (~3,500 remaining, ~7-8 hours)
- Once complete: re-embed → re-fit UMAP → re-project → re-export catalog
- All scripts handle current data gracefully; just re-run pipeline
