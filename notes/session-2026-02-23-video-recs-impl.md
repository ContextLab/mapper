# Session: Video Recommendations Implementation
**Date**: 2026-02-23
**Branch**: `generate-astrophysics-questions` (work for `002-video-recommendations`)

## Completed Phases

### Phase 2: State Management (T-V010, T-V011) [DONE]
- Added 5 atoms to `src/state/store.js`: `$watchedVideos` (persistent Set), `$preVideoSnapshot`, `$questionsAfterVideo`, `$differenceMap`, `$runningDifferenceMap`
- Updated `src/state/persistence.js` `resetAll()` to clear all 5 atoms

### Phase 3: Video Data Loader (T-V020) [DONE]
- Created `src/domain/video-loader.js`: background loading with priority queue, reprioritization, caching, 404 handling

### Phase 4: Video Recommender Engine (T-V030–T-V038) [DONE]
- Created `src/learning/video-recommender.js` with all scoring functions:
  - `computeTLP()` — (1-K) x U active learning scoring
  - `filterByDomain()` — domain filtering
  - `applyWatchedPenalty()` — 0.1x penalty for watched videos
  - `computeRanking()` — full pipeline: filter -> score -> penalize -> sort -> top 10
  - `takeSnapshot()` — captures GP grid before video
  - `computeDifferenceMap()` — K_after - K_before
  - `computeRelevanceMap()` — Matern 3/2 kernel distance to windows
  - `updateRunningAverage()` — EMA with alpha=0.3
  - `computeExpectedGain()` — (1-K) x Transfer with fallback
  - `handlePostVideoQuestion()` — orchestrates post-video flow

### Phase 5: Video Modal UI (T-V040–T-V044) [DONE]
- Created `src/ui/video-modal.js`: list view + inline YouTube player
  - List: rank, play icon, title (ellipsis), gain bars (green/yellow/gray), duration, watched checkmark
  - Player: YouTube IFrame API (lazy-loaded, privacy-enhanced embed), speed controls, back button
  - Completion detection via onStateChange ENDED
  - Embed-blocked fallback: direct YouTube link
  - Responsive: mobile bottom sheet at 480px breakpoint

### Phase 6: Integration & Wiring (T-V050–T-V052) [DONE]
- Rewired suggest button to open video modal instead of concept suggestions
- Wired background video loading on app init (all domains)
- Wired domain reprioritization on $activeDomain change
- Wired post-video diff map flow in handleAnswer()
- Video modal in escape handler chain (before insights modal)
- Un-hid suggest button on mobile (was `display: none`)
- Reset clears mergedVideoWindows and hides video modal

## Build Status
- `npm run build` passes: 41 modules, 127KB bundle (was 112KB with 38 modules)
- All new modules tree-shaken in correctly

## Remaining Work

### Phase 1: Offline Pipeline Scripts (Python) — NOT STARTED
- T-V001 through T-V006: scrape, transcripts, embeddings, UMAP projection, export
- T-V004 BLOCKED on new UMAP reducer (CL-034)
- Can write scripts now, run when reducer is ready

### Phase 7: Validation & Testing — NOT STARTED
- T-V060–T-V063: Algorithm tests (depend on Phase 4 ✓)
- T-V064–T-V068, T-V070: UI/Playwright tests (depend on Phase 6 ✓)
- T-V069: Pipeline validation (depends on Phase 1 + UMAP reducer)

## Key Decisions
- All DOM construction uses safe DOM methods (createElement/textContent) — no innerHTML
- YouTube IFrame API loaded lazily on first video click
- 404 for missing video data cached as empty array (graceful degradation)
- mergedVideoWindows tracks accumulated windows across consecutive unwatched videos
