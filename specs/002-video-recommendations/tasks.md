# Tasks: Khan Academy Video Recommendation System

**Input**: Design documents from `/specs/002-video-recommendations/`
**Prerequisites**: spec.md (with 39 resolved clarifications), CL-016 PoC validated
**Branch**: `002-video-recommendations`
**Blocked on**: New UMAP reducer (in progress in separate session — see CL-034)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5, PIPE, INFRA)

---

## Phase 1: Offline Pipeline Scripts (Python)

**Purpose**: Build the 5-stage pipeline that scrapes Khan Academy, downloads
transcripts, creates sliding-window embeddings, projects into UMAP space, and
exports per-domain video bundles.

**IMPORTANT**: Scripts in T-V001 through T-V003 can be written and tested
immediately. T-V004 (UMAP projection) is BLOCKED until the new reducer is
generated. T-V005 (export) depends on T-V004 output. Write all scripts now;
run the full pipeline end-to-end once the reducer is available.

### Stage 1: Metadata Scrape

- [x] T-V001 [PIPE] Implement `scripts/scrape_khan_videos.py`: Enumerate all
  Khan Academy YouTube videos via `scrapetube` (no API key required). Use
  `scrapetube.get_channel(channel_url="https://www.youtube.com/@khanacademy")`.
  Collect: video ID, title, duration (parse "HH:MM:SS" → seconds), thumbnail
  URL. Use `sleep` parameter to rate-limit. Output:
  `data/videos/.working/khan_metadata.json`. See FR-V001, CL-027.

### Stage 2: Transcript Download

- [x] T-V002 [PIPE] Implement `scripts/download_transcripts.py`: Download
  English transcripts for all scraped videos via `youtube-transcript-api`.
  Rate-limit to 5 requests/second with exponential backoff on 429 errors.
  Checkpoint progress every 500 videos. Exclude videos with no English
  transcript or transcripts shorter than 100 words. Output:
  `data/videos/.working/transcripts/{video_id}.txt`. See FR-V002, CL-021,
  CL-022, CL-033.

### Stage 3: Sliding Windows + Embedding

- [x] T-V003 [PIPE] Implement `scripts/embed_video_windows.py`: Split each
  transcript into sliding windows (512 words, 50-word stride per CL-002).
  Embed each window using `google/embeddinggemma-300m` (768-dim). Batch
  processing with GPU (MPS/CUDA) support. Checkpoint every 100 videos.
  Output: `data/videos/.working/embeddings/{video_id}.npy` (one file per
  video, shape [N_windows, 768]). See FR-V003, FR-V004, CL-002.

### Stage 4: UMAP Projection ← BLOCKED on new reducer

- [ ] T-V004 [PIPE] Implement `scripts/project_video_coords.py`: Load UMAP
  reducer and bounds from paths provided as CLI arguments (default:
  `data/umap_reducer.pkl`, `data/umap_bounds.pkl`). Call
  `reducer.transform()` on all window embeddings. Normalize to [0,1] using
  bounds. Clip out-of-bounds coordinates to [0.0, 1.0]; log count of clipped
  windows and flag if >10% are clipped. Output:
  `data/videos/.working/coordinates/{video_id}.json` (array of [x, y] pairs).
  See FR-V005, CL-001, CL-034, CL-038.

### Stage 5: Per-Domain Export

- [ ] T-V005 [PIPE] Implement `scripts/export_video_bundles.py`: Assign each
  video to domains where ≥20% of its windows fall inside the domain bounding
  box (from `data/domains/index.json`). Produce per-domain files
  `data/videos/{domain-id}.json` containing for each video: `id` (YouTube
  video ID), `title`, `duration_s`, `thumbnail_url`
  (`https://i.ytimg.com/vi/{id}/mqdefault.jpg`), `windows` (array of [x, y]
  coordinate pairs). Also produce `data/videos/index.json` manifest with
  domain → video count and file size. Enforce no duplicate video IDs.
  See FR-V006, CL-008, CL-009, CL-010, CL-025, CL-026, CL-036, CL-037.

### Stage 6: Pipeline Runner

- [ ] T-V006 [PIPE] Implement `scripts/run_video_pipeline.sh`: Shell script
  that runs T-V001 through T-V005 in sequence with error checking between
  stages. Accept `--reducer` and `--bounds` CLI arguments passed through to
  T-V004. Log total runtime and per-stage statistics.

**Checkpoint**: All 5 pipeline scripts exist and are individually testable.
`run_video_pipeline.sh` orchestrates them end-to-end. Cannot produce final
output until UMAP reducer is available.

---

## Phase 2: State Management Extensions

**Purpose**: Add new atoms to the existing state management system for video
tracking, snapshots, and difference maps.

- [x] T-V010 [INFRA] Add video-related atoms to `src/state/store.js`:
  - `$watchedVideos` — `persistentAtom` (localStorage key:
    `mapper:watchedVideos`), Set of watched video IDs
  - `$preVideoSnapshot` — session-only atom, 50×50 Float32Array or null
  - `$questionsAfterVideo` — session-only atom, integer counter
  - `$differenceMap` — session-only atom, 50×50 Float32Array or null
  - `$runningDifferenceMap` — session-only atom, 50×50 Float32Array or null
  See FR-V040, FR-V043, CL-024.

- [x] T-V011 [P] [INFRA] Update `src/state/persistence.js` `resetAll()` to
  clear all 5 new atoms: `$watchedVideos` (persistent), plus all 4 session
  atoms. See FR-V042, CL-024.

**Checkpoint**: New atoms exist, `resetAll()` clears them, `$watchedVideos`
persists across page refreshes.

---

## Phase 3: Video Data Loader

**Purpose**: Background-load per-domain video files during the welcome screen
with priority interruption on domain change.

- [x] T-V020 [INFRA] Implement `src/domain/video-loader.js`:
  - `startBackgroundLoad(domainIds)` — begins fetching per-domain video JSON
    files in parallel, prioritizing the currently selected domain.
  - `reprioritize(domainId)` — interrupts in-progress lower-priority fetches,
    promotes the given domain to load next.
  - `getVideos(domainId)` — returns cached video data for the domain, or null
    if not yet loaded (with a Promise for when it completes).
  - `isLoaded(domainId)` — boolean check.
  - Cache loaded data in-memory for session duration.
  See FR-V041, CL-010.

**Checkpoint**: Video data loads in background during welcome screen. Domain
switch reprioritizes correctly. Cache avoids redundant fetches.

---

## Phase 4: Video Recommender Engine

**Purpose**: Core ranking algorithms — TLP scoring, difference maps, expected
gain, and EMA running averages. All operations use `globalEstimator` (50×50
on [0,1] space).

### TLP Scoring (Phase 1 ranking — before any videos watched)

- [x] T-V030 [US1] Implement `computeTLP(video, globalEstimates)` in
  `src/learning/video-recommender.js`: For each window coordinate, snap to
  nearest 50×50 grid cell, look up cached K and U values, compute
  `(1 - K) × U`. Return the mean across all windows. See FR-V010, CL-003,
  CL-011, CL-030.

- [x] T-V031 [P] [US4] Implement `filterByDomain(videos, domain)` in
  `src/learning/video-recommender.js`: Return only videos from the
  per-domain file matching the active domain. For "All (General)", return
  all loaded videos. See FR-V012, CL-020.

- [x] T-V032 [P] [US1] Implement `applyWatchedPenalty(scores, watchedIds)` in
  `src/learning/video-recommender.js`: Multiply scores of watched videos
  by 0.1. See FR-V013.

- [x] T-V033 [US1] Implement `computeRanking(videos, globalEstimates,
  watchedIds, runningDiffMap)` in `src/learning/video-recommender.js`:
  Orchestrate: filter by domain → score each video (TLP or ExpectedGain
  depending on whether a running diff map exists) → apply watched penalty
  → sort descending → return top 10. See FR-V011.

### Difference Maps (Phase 2 ranking — after watching videos)

- [x] T-V034 [US3] Implement `takeSnapshot(globalEstimator)` in
  `src/learning/video-recommender.js`: Copy the 50×50 prediction grid from
  `globalEstimator.predict()` into `$preVideoSnapshot`. Only if no pending
  snapshot already exists. See FR-V020, CL-004, CL-012.

- [x] T-V035 [US3] Implement `computeDifferenceMap(snapshot,
  currentEstimates)` in `src/learning/video-recommender.js`: D(x,y) =
  K_after(x,y) - K_before(x,y) for all 2,500 grid cells. Preserve negative
  values. See FR-V021, CL-013.

- [x] T-V036 [US3] Implement `computeRelevanceMap(videoWindows, lengthScale)`
  in `src/learning/video-recommender.js`: For each grid cell, compute
  `max_w matern32(dist(cell, window_w), lengthScale)` across the merged
  window coordinates of all videos in the current batch. See FR-V022.

- [x] T-V037 [US3] Implement `updateRunningAverage(newDiffMap, relevanceMap,
  runningDiffMap)` in `src/learning/video-recommender.js`: Weight newDiffMap
  by relevanceMap, then apply EMA: `D_running = 0.3 × weighted_new + 0.7 ×
  D_running_prev`. For first video, D_running = weighted_new (α = 1.0).
  See FR-V023, CL-014.

- [x] T-V038 [US3] Implement `computeExpectedGain(video, globalEstimates,
  runningDiffMap, lengthScale)` in `src/learning/video-recommender.js`:
  For each window, snap to grid cell, compute `(1 - K) × Transfer(cell)`.
  Transfer = `max(0, D_running(cell))`. For insufficient-coverage cells
  (no window within 2×lengthScale AND |D_running| < 1e-4), use global
  average of sufficient-coverage cells. Return mean across windows.
  See FR-V024, CL-005.

**Checkpoint**: `computeRanking()` returns correct top-10 videos. TLP scores
reflect knowledge gaps weighted by uncertainty. After watching a video and
answering 5 questions, ExpectedGain produces different rankings from TLP.

---

## Phase 5: Video Modal UI

**Purpose**: The video list modal and inline YouTube player, triggered by the
suggest button. Replaces the existing concept knowledge list.

### List View

- [x] T-V040 [US1] Implement list view in `src/ui/video-modal.js`:
  - Create `#video-modal` element with list view as default.
  - Each entry shows: rank number, play icon, video title (CSS ellipsis
    truncation), gain indicator bar + percentage, duration, watched checkmark.
  - Loading spinner state for when video data hasn't arrived yet.
  - "No recommended videos for this domain yet" message with fallback KA
    search link for empty results.
  - Modal opens via `showVideoModal()`, closes on backdrop click or Escape.
  - Add to `handleEscape()` chain: Escape from list view closes modal.
  See FR-V030, FR-V031, CL-006, CL-018, CL-031.

- [x] T-V041 [P] [US5] Implement gain indicator display in
  `src/ui/video-modal.js`: Color-coded progress bars — green (≥65%), yellow
  (35-64%), gray (<35%). Use existing CSS custom properties:
  `--color-correct`, `--color-accent`, `--color-text-muted`. Display as
  `TLP × 100` percentage. See FR-V035, CL-028.

### Player View

- [x] T-V042 [US1] Implement inline YouTube player in `src/ui/video-modal.js`:
  - Swap modal content to player view on video click.
  - Load YouTube IFrame API lazily via dynamic `<script>` injection on first
    use (guard against double-loading).
  - Use `youtube-nocookie.com` for privacy-enhanced mode.
  - Include: YouTube iframe, speed buttons (0.5×, 0.75×, 1×, 1.25×, 1.5×,
    2×), "Back to list" button, gain percentage display.
  - Query `getAvailablePlaybackRates()` on player ready; disable unavailable
    speed buttons.
  - Escape from player view navigates "Back to list" (not close modal).
  - "Back to list" destroys the iframe (no resume-from-position).
  - Fallback: if embed is blocked, show title as direct YouTube link.
  See FR-V032, FR-V033, CL-017, CL-023, CL-032.

- [x] T-V043 [US2] Implement video completion detection in
  `src/ui/video-modal.js`: Listen for `onStateChange` with
  `YT.PlayerState.ENDED`. On end: mark video as watched (add to
  `$watchedVideos`), show checkmark, trigger snapshot flow. Partial
  watches and manual seek-to-end do NOT trigger completion. Rewatching
  does not change state. See FR-V034, CL-029.

### Responsive Layout

- [x] T-V044 [P] [US1] Implement responsive video modal: On mobile (≤480px),
  list displays as bottom sheet (80vh); player occupies full viewport. On
  tablet/desktop, centered modal with max-width. See FR-V036.

**Checkpoint**: Video modal opens from suggest button, shows ranked list,
plays videos inline, detects completion, works on all viewports.

---

## Phase 6: Integration & Wiring

**Purpose**: Connect all components: suggest button → video modal → ranking
engine → completion → snapshot → difference maps → improved rankings.

### Suggest Button Rewiring

- [x] T-V050 [US1] Rewire suggest button in `src/app.js` / `src/ui/controls.js`:
  Remove the old "Suggested Learning" concept list. The graduation-cap button
  now opens `#video-modal` via `showVideoModal()`. Remove the suggest tab
  from the insights modal. The leaderboard tab remains via the trophy button.
  Un-hide the suggest button at mobile breakpoint (remove `display: none`
  for `#suggest-btn` at ≤480px). See CL-006, CL-007.

### Background Loading

- [x] T-V051 [INFRA] Wire background video loading in `src/app.js`: On app
  initialization (welcome screen), call
  `videoLoader.startBackgroundLoad(allDomainIds)`. On `$activeDomain` change,
  call `videoLoader.reprioritize(newDomainId)`. When suggest button is
  clicked: if video data for active domain is loaded, compute ranking
  immediately; if not, show spinner in modal until loaded. See FR-V041.

### Video → Snapshot → Questions → Diff Map Flow

- [x] T-V052 [US3] Wire the video-watching flow in `src/app.js`:
  1. On video completion (from T-V043): call `takeSnapshot()` if no pending
     snapshot exists. If successive videos without questions, merge window
     coords per CL-004.
  2. In `handleAnswer()` (existing): if `$preVideoSnapshot` exists, increment
     `$questionsAfterVideo`. If count ≥ 1, compute difference map. If count
     ≥ 5, update running average, enable ExpectedGain scoring, clear snapshot
     and reset counter.
  3. On next suggest-button click: `computeRanking()` uses ExpectedGain if
     running diff map exists, otherwise TLP.
  See FR-V020, FR-V021, CL-004, CL-015.

**Checkpoint**: Full end-to-end flow works — suggest → watch → answer → improved
recommendations. Session state resets correctly. Persist watched IDs only.

---

## Phase 7: Validation & Testing

**Purpose**: Verify all success criteria. Tests use real function calls (no
mocks per project constitution).

### Algorithm Tests

- [x] T-V060 [P] Test TLP ranking accuracy (SC-V003): Create synthetic GP
  estimates with a known minimum-knowledge region. Generate mock video data
  with windows in various locations. Verify top-ranked video targets the
  weakest region ≥80% of the time across 100 randomized trials.

- [x] T-V061 [P] Test difference map correctness (SC-V004): Simulate a
  video watch + 5 questions answered near the video's windows. Verify the
  difference map has non-zero values in ≥10% of grid cells near the
  video's window coordinates.

- [x] T-V062 [P] Test ExpectedGain vs TLP divergence (SC-V005): After
  computing a difference map, verify that `computeRanking()` with
  ExpectedGain produces a different top-10 ordering than TLP-only.

- [x] T-V063 [P] Performance test (SC-V006): Time all scoring operations
  with realistic video counts (500-2000 videos, ~150 windows each). Verify
  all operations complete in <15ms.

### UI & Integration Tests (Playwright)

- [x] T-V064 Test video completion detection (SC-V008): Playwright test
  that opens the video modal, plays a short video to completion, and
  verifies the watched checkmark appears. Test across Chromium, Firefox,
  WebKit.

- [x] T-V065 [P] Visual regression — modal viewports (SC-V009): Playwright
  screenshots of video modal on desktop (1024px+), tablet (768px), and
  mobile (320px). Verify no visual overflow or broken layouts.

- [x] T-V066 [P] Test localStorage persistence (SC-V010): Playwright test
  that watches a video, refreshes the page, reopens suggestions, and
  confirms the watched indicator persists.

- [x] T-V067 [P] Test recommendation load time (SC-V002): Playwright test
  measuring time from suggest-button click to video list rendered. Verify
  <2 seconds (with background-loaded data).

- [x] T-V068 Test player load time (SC-V007): Playwright test measuring
  time from video click to playback start. Verify <3 seconds.

- [x] T-V070 [P] Test embed-blocked fallback: Playwright test that
  simulates a blocked YouTube embed (e.g., via route interception to
  block `youtube-nocookie.com`) and verifies the video title renders as
  a direct YouTube link that opens in a new tab. See edge case in spec.

### Pipeline Validation (after UMAP reducer is available)

- [x] T-V069 Pipeline validation (SC-V001): Run full pipeline. Verify output
  covers ≥7,500 videos with valid 2D window coordinates. Verify per-domain
  file integrity: no duplicate IDs, all coordinates in [0, 1], ≥20% window
  threshold enforced.

**Checkpoint**: All SC-V* success criteria pass. Algorithm tests use real
estimator instances. Playwright tests cover all viewports and browsers.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Pipeline)**: Can start immediately. T-V004 BLOCKED on UMAP reducer.
  T-V005 depends on T-V004. T-V001→T-V002→T-V003 are sequential (each stage
  consumes prior stage's output). All scripts can be WRITTEN in parallel.
- **Phase 2 (State)**: No dependencies — start immediately, parallel with Phase 1.
- **Phase 3 (Video Loader)**: Depends on Phase 2 (needs atoms).
- **Phase 4 (Recommender Engine)**: Depends on Phase 2 (needs atoms). Can run
  parallel with Phase 3.
- **Phase 5 (Video Modal UI)**: Depends on Phase 4 (needs ranking output format).
- **Phase 6 (Integration)**: Depends on Phases 3, 4, 5 all complete.
- **Phase 7 (Validation)**: Algorithm tests (T-V060–T-V063) depend on Phase 4.
  UI tests (T-V064–T-V068) depend on Phase 6. Pipeline validation (T-V069)
  depends on Phase 1 complete + UMAP reducer available.

### Dependency Graph

```
Phase 1 (Pipeline)                    Phase 2 (State)
  T-V001 → T-V002 → T-V003             T-V010, T-V011
  T-V004 ← BLOCKED on reducer              ↓
  T-V005 → T-V006                  ┌────────┴────────┐
       ↓                           ↓                  ↓
  T-V069 (validation)        Phase 3 (Loader)   Phase 4 (Engine)
                              T-V020             T-V030→T-V033
                                  ↓              T-V034→T-V038
                                  ↓                  ↓
                                  ↓              Phase 5 (Modal UI)
                                  ↓              T-V040→T-V044
                                  ↓                  ↓
                                  └──────┬───────────┘
                                         ↓
                                   Phase 6 (Integration)
                                   T-V050, T-V051, T-V052
                                         ↓
                                   Phase 7 (UI Tests)
                                   T-V064→T-V068
```

### Parallel Opportunities

- T-V010, T-V011 can run in parallel (different files)
- T-V030, T-V031, T-V032 can run in parallel (independent functions)
- T-V040, T-V041, T-V044 can run in parallel (independent UI pieces)
- T-V060, T-V061, T-V062, T-V063 can run in parallel (independent tests)
- T-V065, T-V066, T-V067 can run in parallel (independent Playwright tests)
- All Phase 1 scripts can be WRITTEN in parallel (though execution is sequential)
- Phase 1 (Python pipeline) is fully independent of Phases 2–6 (JavaScript)

### Critical Path

```
Phase 2 → Phase 4 → Phase 5 → Phase 6 → Phase 7 (UI tests)
```

The pipeline (Phase 1) runs on a separate track, blocked on the UMAP reducer.
Pipeline validation (T-V069) is the last task to complete.

---

## Implementation Strategy

### Immediate Work (no blockers)

1. **Phase 2** (State): Add atoms to store.js — small, fast, unblocks everything
2. **Phase 4** (Recommender Engine): Implement all scoring functions with unit tests
3. **Phase 1** (Pipeline Scripts): Write all 5 scripts; test T-V001–T-V003 with real data
4. **Phase 3** (Video Loader): Implement background loading

### After Recommender Engine

5. **Phase 5** (Video Modal UI): Build the modal and player
6. **Phase 6** (Integration): Wire everything together

### After UMAP Reducer Available

7. **Phase 1** (Pipeline): Run T-V004 and T-V005 to produce final video data
8. **Phase 7** (Validation): Run all tests with real data

### Development with Mock Data

Before the pipeline produces real data, frontend development can use a mock
`data/videos/` directory with synthetic video entries (randomized window
coordinates in [0,1] space, real YouTube video IDs for player testing).

---

---

## Phase 8: GP-IRT Adaptive Difficulty Selection

**Purpose**: Add IRT difficulty-level estimation and BALD information-theoretic
question selection on top of the existing GP posterior. Replaces pure
uncertainty-based question selection with difficulty-aware adaptive selection.

**Input**: GitHub Issue #23, research synthesis from 5 parallel investigations.
**Dependencies**: Extends existing `estimator.js`, `sampler.js`, `math.js`.
No dependency on video recommendation phases (can be implemented independently).

### Phase 8A: MVP — IRT Level Estimation + BALD Selection

- [x] T-V080 [P] [US6] Add `normalCDF(x)` to `src/utils/math.js`: Abramowitz &
  Stegun polynomial approximation for the standard normal CDF. Used for
  computing level posterior probabilities. See FR-V053.

- [x] T-V081 [US6] Add IRT difficulty level to `predict()` output in
  `src/learning/estimator.js`: Add constants `IRT_THRESHOLDS = [0.125,
  0.375, 0.625, 0.875]` and `IRT_DISCRIMINATION = 1.5`. For each cell in
  predict() results, compute `difficultyLevel = count of thresholds where
  value >= threshold` (0–4). Return as part of the cell estimate object.
  See FR-V050, SC-V011.

- [x] T-V082 [US6] Replace uncertainty-based scoring with BALD EIG in
  `src/learning/sampler.js` `selectNext()`: Compute IRT-predicted P(correct)
  for each candidate question using `sigmoid(1.5 × (4×value - 2 - b[d]))`,
  then score with `EIG = 1.5² × P × (1-P) × (4×uncertainty)²`. Also update
  `scoreAll()` to use the same BALD scoring. See FR-V051, SC-V012.
  Note: When all questions have the same difficulty, BALD reduces to
  uncertainty-based scoring (backward-compatible per CL-043).

### Phase 8B: Full IRT Layer — Phase-Based Selection

- [x] T-V083 [US6] Add phase detection to `src/learning/sampler.js`: Add
  `getPhase(answeredCount, coverage)` function returning 'calibrate' (N<10),
  'map' (10≤N<30 or coverage<0.15), or 'learn' (N≥30 and coverage≥0.15).
  Coverage = fraction of question-occupied cells with uncertainty < 0.5.
  See FR-V052, SC-V014.

- [x] T-V084 [US6] Implement phase-based scoring in `selectNext()`: In
  'calibrate' phase, score = `uncertainty × (1 - |difficulty - 2.5| / 2)`
  (prefer middle difficulties in uncertain regions). In 'map' phase, use
  BALD EIG. In 'learn' phase, score = `1 - |P_correct - 0.6|` (ZPD
  targeting). Fall back to BALD if local uncertainty > 0.7. See FR-V052.

- [x] T-V085 [P] [US6] Update `selectByMode()` in `src/learning/sampler.js`
  to use IRT-predicted P(correct) for mode strategies. 'easy' mode: prefer
  questions where IRT P(correct) > 0.8. 'hardest-can-answer': prefer highest
  difficulty where IRT P(correct) > 0.5. 'dont-know': prefer questions where
  IRT P(correct) < 0.3.

- [x] T-V086 [P] [US6] Add `$phase` computed atom to `src/state/store.js`:
  Derive phase from answered count and coverage metrics. Export for use in
  sampler and potential UI display.

### Phase 8C: Validation

- [x] T-V090 [P] Test IRT difficulty level mapping (SC-V011): Create GP
  states with known values at specific cells. Verify difficultyLevel matches
  expected IRT thresholds exactly for boundary values (0.124→0, 0.126→1,
  0.374→1, 0.376→2, etc.).

- [x] T-V091 [P] Test BALD vs uncertainty divergence (SC-V012): Create a GP
  state where ability varies across the grid. Compare BALD-selected questions
  against uncertainty-selected questions. Verify BALD preferentially selects
  questions at the learner's difficulty boundary (P near 0.5).

- [x] T-V092 [P] Test BALD backward compatibility (CL-043): When all
  candidate questions have the same difficulty, verify BALD produces the
  same ranking as pure uncertainty scoring.

- [x] T-V093 [P] Performance test (SC-V013): Time IRT + BALD computation
  with realistic grid size (2500 cells) and question count (50 per domain).
  Verify total overhead < 1ms.

- [x] T-V094 [P] Test phase transitions (SC-V014): Simulate answering
  sequences with varying coverage. Verify phase transitions fire at correct
  thresholds and soft fallback works when coverage drops.

**Checkpoint**: All SC-V011–SC-V014 pass. BALD scoring produces measurably
better question selection than pure uncertainty. Phase transitions work
correctly. Performance overhead is negligible.

---

## Dependencies & Execution Order (Updated)

### Phase Dependencies (Updated)

- **Phase 8 (GP-IRT)**: Depends on existing `estimator.js` and `sampler.js`
  only — no dependency on Phases 1–7. Can be implemented in parallel with
  video recommendation work. Phase 8A (MVP) is independent of Phase 8B.
  Phase 8C tests depend on Phase 8A + 8B.

### Updated Dependency Graph

```
Phase 1 (Pipeline)                    Phase 2 (State)
  T-V001 → T-V002 → T-V003             T-V010, T-V011
  T-V004 ← BLOCKED on reducer              ↓
  T-V005 → T-V006                  ┌────────┴────────┐
       ↓                           ↓                  ↓
  T-V069 (validation)        Phase 3 (Loader)   Phase 4 (Engine)
                              T-V020             T-V030→T-V033
                                  ↓              T-V034→T-V038
                                  ↓                  ↓
                                  ↓              Phase 5 (Modal UI)
                                  ↓              T-V040→T-V044
                                  ↓                  ↓
                                  └──────┬───────────┘
                                         ↓
                                   Phase 6 (Integration)
                                   T-V050, T-V051, T-V052
                                         ↓
                                   Phase 7 (UI Tests)
                                   T-V064→T-V068

Phase 8 (GP-IRT) — INDEPENDENT TRACK
  T-V080 ─┐
  T-V081 ──┤→ T-V082 → T-V083 → T-V084
  T-V085 ──┘              ↓
  T-V086 ─────────────────┘
                          ↓
                   T-V090→T-V094 (validation)
```

---

## Notes

- Total task count: 49 tasks across 8 phases (T-V001–T-V094, non-contiguous IDs)
- [P] tasks = different files, no dependencies between them
- [Story] label maps tasks to user stories for traceability
- The entire pipeline (Phase 1) is Python; all other phases are JavaScript
- All scoring uses `globalEstimator` (50×50, [0,1] space) — never the domain estimator
- Window coordinates are snapped to nearest grid cell for GP lookup (CL-011)
- The existing `src/learning/estimator.js` and its Matérn 3/2 kernel are reused
  for relevance weighting — no new kernel implementation needed
- Phase 8 (GP-IRT) is independent of the video recommendation pipeline and
  can be implemented and tested without video data
- Commit after each task or logical group
- Stop at any checkpoint to validate current state
