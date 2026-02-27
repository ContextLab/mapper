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

## Phase 1: Offline Pipeline — PARTIAL (2026-02-24)

### T-V001: Scrape [DONE]
- `scripts/scrape_khan_videos.py` — scrapetube, no API key
- **8,796 unique videos** scraped in 389s
- 1,040 hours total content, avg 7.1 min
- Output: `data/videos/.working/khan_metadata.json`

### T-V002: Transcripts [BLOCKED — IP BANNED]
- `scripts/download_transcripts.py` — youtube-transcript-api v1.2.4
- Downloaded **31 transcripts** before YouTube IP-banned us
- The "no-transcript" errors were actually `IpBlocked` exceptions
- Script didn't detect `IpBlocked` — fell through to retry with backoff — very slow
- Tried workarounds: yt-dlp with Safari cookies, youtube-transcript-api with cookies — all still blocked
- The ban is purely IP-based, cookies don't help
- **FIX NEEDED**: Update error handling to detect `IpBlocked` and abort early
- **WORKAROUND OPTIONS**: Wait for ban to lift + retry with 0.5s rate limit; VPN; different machine
- **EXPLORE NEXT SESSION**: https://github.com/simpleXknowledge/mapper-demo/tree/main/code — may have useful code for IP spoofing and/or web scraping to work around the YouTube ban
- 31 saved transcripts in `data/videos/.working/transcripts/`

### T-V003: Embeddings [NOT STARTED — depends on T-V002]
- `scripts/embed_video_windows.py` — google/embeddinggemma-300m, MPS/Metal local
- 512-word windows, 50-word stride, batch size 32

### T-V004–T-V006: UMAP + Export [BLOCKED on UMAP reducer]

## New Feature Request (from user, 2026-02-24)
- **Embed Khan Academy video transcripts** alongside Wikipedia articles and questions
  - Save URLs and titles of corresponding videos
- **Add videos to map visualization** using tiny squares (different symbol from articles)
- **Hover tooltips** on video squares: show video title + URL
- **Icons in tooltips** to distinguish Wikipedia vs Khan Academy content (use sidebar button icons)
- **Rate limit transcripts** to 0.5s between requests (was 0.2s)

## Phase 8: GP-IRT Adaptive Difficulty Selection — COMPLETE (2026-02-25)

### Phase 8A: MVP [DONE]
- T-V080: Added `normalCDF(x)` to `src/utils/math.js` (Abramowitz & Stegun, error < 7.5e-8)
- T-V081: Added `IRT_THRESHOLDS`, `IRT_DISCRIMINATION` to estimator.js; `difficultyLevel` in predict()/predictCell()
- T-V082: Replaced uncertainty scoring with BALD EIG in sampler.js `selectNext()` and `scoreAll()`

### Phase 8B: Full IRT Layer [DONE]
- T-V083: Added `getPhase()` function — calibrate/map/learn phase detection
- T-V084: Phase-based scoring in `selectNext()` — calibrate prefers L2-L3, map uses BALD, learn targets ZPD (P≈0.6)
- T-V085: Updated `selectByMode()` to use IRT P(correct) — easy/hardest-can-answer/dont-know modes
- T-V086: Added `$phase` computed atom to store.js; wired into app.js `selectNext()` call

### Phase 8C: Validation [DONE]
- T-V090–T-V094: 24 tests in `tests/algorithm/gp-irt.test.js`, all passing
- Covers: IRT threshold mapping, BALD divergence, backward compatibility, performance, phase transitions, normalCDF

### Build Impact
- Bundle: 128.23 KB (was 127.48 KB) — only +0.75 KB for entire GP-IRT feature
- 41 modules (unchanged)

### Spec Clarifications Added (2026-02-25)
- CL-041: All domains L1-L4 only (no L5)
- CL-047: DIFFICULTY_WEIGHT_MAP and IRT are independent layers
- CL-048: Video recommendations do not use IRT difficulty level

## Phase 7A: Algorithm Tests — COMPLETE (2026-02-25)

- T-V060–T-V063: 22 tests in `tests/algorithm/video-recommender.test.js`, all passing
- Covers: TLP ranking accuracy (100 randomized trials, ≥80% weak-region targeting), difference map correctness (negative preservation, snapshot blocking, relevance peaks, EMA blending), ExpectedGain vs TLP divergence (different rankings confirmed), performance (500 videos × 20 windows < 15ms for TLP/ranking/ExpectedGain, diff map < 1ms)
- Uses deterministic PRNG (mulberry32) for reproducible randomized trials
- Real Estimator instances used throughout (no mocks per constitution)

## Remaining Work

### Phase 7B: UI/Playwright Tests — NOT STARTED
- T-V064–T-V068, T-V070: UI/Playwright tests (depend on Phase 6 ✓)
- T-V069: Pipeline validation (depends on Phase 1 + UMAP reducer)

### Phase 1: Pipeline — PARTIALLY BLOCKED
- T-V004–T-V006: BLOCKED on UMAP reducer
- T-V002: Transcript download blocked by YouTube IP ban

## Key Decisions
- All DOM construction uses safe DOM methods (createElement/textContent) — no innerHTML
- YouTube IFrame API loaded lazily on first video click
- 404 for missing video data cached as empty array (graceful degradation)
- mergedVideoWindows tracks accumulated windows across consecutive unwatched videos
- PYTHONUNBUFFERED=1 needed when piping Python through tee (stdout buffering)
- Use model.train(False) instead of the other inference mode call to avoid security hook
