# Implementation Plan: Khan Academy Video Recommendation System

**Branch**: `002-video-recommendations` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification + 39 resolved clarifications + CL-016 PoC validation
**Blocked on**: New UMAP reducer (in progress in a separate session — see CL-034)

## Summary

Add personalized Khan Academy video recommendations to the mapper demo. The
system scrapes ~9,000 KA videos, downloads YouTube transcripts, creates
sliding-window embeddings using embeddinggemma-300m, and projects them into the
existing UMAP space via `transform()`. Client-side, it computes Theoretical
Learning Potential (TLP) from the user's knowledge map, tracks video completion
via the YouTube IFrame API, builds difference maps from observed learning, and
maintains a recency-weighted running average for adaptive recommendations.

## Technical Context

**Language/Version**: Python 3.10+ (pipeline), JavaScript ES2020+ (frontend)
**Primary Dependencies**:
- Pipeline: scrapetube, youtube-transcript-api, sentence-transformers
  (embeddinggemma-300m), umap-learn ≥ 0.5
- Frontend: existing deck.gl, Nano Stores, KaTeX stack + YouTube IFrame Player API

**Existing Infrastructure** (from spec-001):
- `src/learning/estimator.js` — Gaussian Process with Matérn 3/2 kernel, 50×50 grid
- `src/state/store.js` — Nano Stores atoms with localStorage persistence
- `src/state/persistence.js` — Schema-versioned persistence with `resetAll()`
- `src/domain/loader.js` — Lazy domain bundle loading with progress events
- `src/ui/modes.js` — Suggest button, insights modal

**Key Architectural Decisions** (from clarifications):
1. All video scoring uses `globalEstimator` (50×50 on [0,1]), not domain estimator
2. Flattening is visual-only; estimation operates in pre-flatten UMAP space
3. Video modal replaces the old concept knowledge list entirely
4. Per-domain video files, background-loaded during welcome screen
5. TLP formula: `(1-K) × U` — boost uncertainty (active learning strategy)
6. Diff maps computed after 1+ question, used for ranking after 5+
7. UMAP reducer will be retrained; pipeline blocked on this dependency

**Performance Budget**: All scoring operations <15ms client-side (SC-V006)
**Scale**: ~9,000 videos × ~150 windows each = ~1.35M total windows,
split into per-domain files of ~500–2,000 videos each

## Constitution Check

*GATE: Must pass before implementation begins.*

| Principle | Verification | Pass |
|-----------|--------------|------|
| **I. Accuracy** | CL-016 PoC validates transcript embeddings produce topic-separated clusters (gap = 0.111, 2× threshold). TLP formula mathematically grounded in GP uncertainty. Pipeline validates ≥7,500 videos with valid coordinates (SC-V001). No mock objects in tests. | [x] |
| **II. User Delight** | Video recommendations load <2s (SC-V002, background-loaded). Inline YouTube player with speed controls. Gain indicators color-coded for quick scanning. Responsive modal (desktop/tablet/mobile). Rankings improve observably after watching videos (SC-V005). | [x] |
| **III. Compatibility** | YouTube IFrame API works in all target browsers. Responsive modal layout (SC-V009). Privacy-enhanced embed via youtube-nocookie.com. CSP-compatible with GitHub Pages defaults. Watched state persists via localStorage (SC-V010). | [x] |

*Constitution gate PASSES. No violations.*

## Project Structure

### New Files (this feature)

```text
# Pipeline (Python)
scripts/
├── scrape_khan_videos.py          # scrapetube channel enumerator (no API key)
├── download_transcripts.py        # Transcript downloader with retry/rate-limit
├── embed_video_windows.py         # Sliding window → embeddinggemma-300m
├── project_video_coords.py        # UMAP transform + bounds normalization
├── export_video_bundles.py        # Per-domain JSON export with ≥20% threshold
└── run_video_pipeline.sh          # End-to-end pipeline orchestrator

# Video data output
data/videos/
├── index.json                     # Manifest: domain → video count, file size
└── {domain-id}.json               # Per-domain video files (~0.5-2 MB each)

# Frontend (JavaScript — extends existing src/)
src/learning/
└── video-recommender.js           # TLP, diff maps, expected gain, EMA

src/domain/
└── video-loader.js                # Background video data loading

src/ui/
└── video-modal.js                 # Video list + inline YouTube player

# Modified files
src/state/store.js                 # +5 atoms (1 persistent, 4 session-only)
src/state/persistence.js           # resetAll() updated
src/app.js                         # Wiring: suggest btn, background load, diff map flow
src/ui/controls.js                 # Suggest button rewiring
index.html                         # Mobile CSS: un-hide #suggest-btn; #video-modal markup
```

### Documentation (this feature)

```text
specs/002-video-recommendations/
├── spec.md                        # Feature specification (39 clarifications resolved)
├── plan.md                        # This file
├── tasks.md                       # Phased task breakdown (33 tasks, 7 phases)
└── checklists/
    └── requirements.md            # Spec quality checklist
```

## Complexity Tracking

> No Constitution Check violations. No justifications needed.

### External Dependencies

| Dependency | Risk | Mitigation |
|------------|------|------------|
| UMAP reducer regeneration | **HIGH** — Pipeline Phase 1 blocked | Write all scripts now; test T-V001–T-V003 with real data; run T-V004–T-V005 when reducer is ready |
| scrapetube stability | LOW — relies on YouTube internal browse API | yt-dlp as fallback; browse API stable for years |
| YouTube transcript availability | LOW — ~85-95% coverage | Exclude missing; ≥7,500 target is conservative |
| YouTube IFrame API stability | LOW — Widely used, Google-maintained | Fallback: direct YouTube link if embed fails |
