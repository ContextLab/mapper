# Feature Specification: Khan Academy Video Recommendation System

**Feature Branch**: `002-video-recommendations`
**Created**: 2026-02-23
**Status**: Draft
**Input**: GitHub Issue #22 — https://github.com/ContextLab/mapper/issues/22

## User Scenarios & Testing *(mandatory)*

### User Story 1 — First Video Suggestions (Priority: P1)

A visitor has answered 5+ questions and clicks the graduation-cap button.
Instead of seeing concept names with Khan Academy search links, they see a
ranked list of 10 actual Khan Academy videos with estimated knowledge gain
indicators. The top video covers content in the region where the visitor's
knowledge is weakest. The visitor clicks a video and watches it inline
without leaving the page.

**Why this priority**: This is the core value proposition — personalized
video recommendations based on the knowledge map. Without this, the
feature has no foundation.

**Independent Test**: Answer 10 questions across a domain, click suggest,
verify the top video targets a low-knowledge region, click to play, and
confirm the video plays inline with controls.

**Acceptance Scenarios**:

1. **Given** a visitor has answered ≥5 questions, **When** they click the
   graduation-cap button, **Then** a modal displays 10 ranked Khan Academy
   videos with title, duration, and a gain indicator bar.
2. **Given** the visitor views the video list, **When** they examine the
   rankings, **Then** the top-ranked video covers content near the
   lowest-knowledge regions of the active domain's map.
3. **Given** a video in the list, **When** the visitor clicks it, **Then**
   the modal transitions to an inline YouTube player with native playback
   controls (scrubbing, volume, fullscreen) and supplemental speed buttons.
4. **Given** the inline player is showing, **When** the visitor clicks
   "Back to list", **Then** they return to the ranked video list.

---

### User Story 2 — Video Completion Tracking (Priority: P1)

A visitor watches a suggested video to completion. The system detects the
video has ended, marks it as "watched" with a checkmark in the list, and
prepares to measure the knowledge gain from watching. The watched status
persists across browser sessions.

**Why this priority**: Without completion tracking, the difference map
system (Story 3) cannot function, and recommendations cannot improve.

**Independent Test**: Play a short video to completion, verify the watched
indicator appears, refresh the page, reopen suggestions, and confirm the
video still shows as watched.

**Acceptance Scenarios**:

1. **Given** a visitor is watching a video inline, **When** the video
   reaches its natural end, **Then** the system marks it as "watched" and
   shows a checkmark indicator next to that video in the list.
2. **Given** a video is marked watched, **When** the visitor refreshes
   the page and reopens suggestions, **Then** the watched status persists.
3. **Given** a video is being watched, **When** the visitor closes the
   player before completion, **Then** the video is NOT marked as watched.
4. **Given** the visitor resets all progress, **When** they reopen
   suggestions, **Then** all watched indicators are cleared.

---

### User Story 3 — Adaptive Recommendations via Difference Maps (Priority: P2)

After watching a video and answering 5+ new questions, the system
computes a difference map showing where knowledge actually improved.
Subsequent recommendations use this observed data instead of just
theoretical gap estimates, producing better-targeted suggestions.

**Why this priority**: This is the learning loop that makes
recommendations improve over time. It depends on Stories 1-2 being
functional.

**Independent Test**: Watch a suggested video, answer 5 questions, reopen
the suggestions list, and verify the rankings have changed to reflect the
observed learning pattern.

**Acceptance Scenarios**:

1. **Given** a visitor has watched a video and answered 5+ new questions,
   **When** they reopen the suggestions list, **Then** the rankings
   reflect observed knowledge gain (not just theoretical gap).
2. **Given** the difference map is available, **When** computing expected
   gain for a candidate video, **Then** the system uses the observed
   transfer function weighted by how close the candidate's content is to
   previously observed gains.
3. **Given** the visitor watches multiple videos across sessions, **When**
   computing recommendations, **Then** the system uses a recency-weighted
   average of all difference maps, giving more weight to recent videos.

---

### User Story 4 — Domain-Scoped Recommendations (Priority: P2)

When the visitor has selected a specific domain from the dropdown (e.g.,
"Quantum Physics"), video recommendations are scoped to that domain's
region. Only videos whose sliding-window coordinates fall within the
domain's bounding rectangle are considered for ranking.

**Why this priority**: Without domain scoping, users exploring a specific
topic would get recommendations spanning the entire knowledge space.

**Independent Test**: Select "Quantum Physics" from the dropdown, open
suggestions, and verify all listed videos are relevant to quantum physics
(their window coordinates fall within the quantum physics bounding box).

**Acceptance Scenarios**:

1. **Given** a specific domain is selected, **When** the visitor opens
   suggestions, **Then** only videos with window coordinates inside the
   domain's bounding rectangle appear in the list.
2. **Given** "All (General)" is selected, **When** the visitor opens
   suggestions, **Then** videos from the entire [0,1] space are considered.
3. **Given** a domain with very few matching videos (<10), **When** the
   list is shown, **Then** all available videos for that domain are listed
   (even if fewer than 10).

---

### User Story 5 — Estimated Gain Display (Priority: P3)

Each video in the ranked list displays a visual indicator of estimated
knowledge gain, helping the visitor understand how much they might learn
from each video relative to others.

**Why this priority**: This provides transparency into the recommendation
algorithm and helps visitors make informed choices. It depends on the
ranking system from Stories 1 and 3.

**Independent Test**: Open the suggestions list, verify each video has a
gain indicator, and confirm the indicators decrease from top to bottom.

**Acceptance Scenarios**:

1. **Given** the video list is displayed, **When** the visitor examines
   each entry, **Then** a gain indicator bar and percentage are shown.
2. **Given** the gain indicators, **When** comparing them, **Then** they
   are color-coded: green (high gain ≥65%), yellow (moderate 35-64%),
   gray (low <35%).
3. **Given** the visitor has watched some videos, **When** the list is
   refreshed, **Then** watched videos have reduced gain indicators
   reflecting diminished expected benefit from rewatching.

---

### User Story 6 — Adaptive Difficulty Selection via GP-IRT (Priority: P2)

The system adaptively selects question difficulty based on the learner's
estimated ability at each spatial location. Instead of treating all
difficulty levels equally, it infers a "difficulty level map" from the
existing GP posterior, and uses information-theoretic selection (BALD) to
choose questions that are maximally informative — balancing spatial
exploration with difficulty-appropriate probing.

**Why this priority**: Without difficulty awareness, the system wastes
questions: too-easy questions provide no information, too-hard questions
are just guessing. Adaptive difficulty improves both assessment efficiency
(10–12% RMSE improvement) and learning experience (ZPD targeting).

**Independent Test**: Answer 10 questions, open the map, verify each cell
shows a difficulty level estimate (L1–L4). Confirm that the system
preferentially asks questions near the learner's difficulty boundary rather
than at random difficulties.

**Acceptance Scenarios**:

1. **Given** a learner has answered ≥5 questions, **When** they examine
   the GP estimate grid, **Then** each cell includes a `difficultyLevel`
   (0–4) derived from the GP posterior value via IRT thresholds.
2. **Given** the GP has estimated ability at a location, **When** a
   question is selected at that location, **Then** the system prefers
   difficulties where P(correct) is near 0.5 (maximally informative).
3. **Given** fewer than 10 questions have been answered (calibration
   phase), **When** selecting the next question, **Then** the system
   prefers L2–L3 questions in high-uncertainty regions.
4. **Given** more than 30 questions have been answered and coverage
   exceeds 15% (learning phase), **When** selecting the next question,
   **Then** the system targets the zone of proximal development (P(correct)
   ≈ 0.55–0.70) for optimal learning.
5. **Given** the learner switches to a new, unexplored domain region,
   **When** coverage drops below 15%, **Then** the system drops back
   to mapping phase (BALD acquisition) even if total answered > 30.

---

### Edge Cases

- What happens if the video database hasn't loaded yet when the user
  clicks suggest? Show a loading spinner within the modal, then display
  results when ready.
- What happens if no videos match the active domain? Display a message:
  "No recommended videos for this domain yet" with a fallback link to
  Khan Academy search.
- What happens if a video's transcript was unavailable? That video is
  excluded from the database entirely — it has no window coordinates.
- What happens if the YouTube embed is blocked (corporate network,
  content blockers)? Show the video title as a direct YouTube link that
  opens in a new tab. See T-V070 for test coverage.
- What happens if the user answers fewer than 5 questions after watching?
  The system waits. The pre-video snapshot is retained until 5 questions
  are answered, at which point the difference map is computed.
- What happens on a very slow connection? Per-domain video files are
  background-loaded during the welcome screen. Show download progress if
  the user opens suggestions before loading completes.
- What happens if the user watches a video that wasn't in the top 10?
  This shouldn't happen — only listed videos can be played inline. But if
  a user navigates to a video via external means, it has no effect on the
  recommendation system.

## Requirements *(mandatory)*

### Functional Requirements — Offline Pipeline

- **FR-V001**: Pipeline MUST enumerate all Khan Academy YouTube videos
  (~9,000) using `scrapetube` (no API key required), collecting: video
  ID, title, duration, and thumbnail URL. Duration strings (e.g.,
  "12:34") MUST be parsed to seconds.

- **FR-V002**: Pipeline MUST download the transcript for each video using
  `youtube-transcript-api`. Videos without available transcripts MUST be
  marked as unavailable and excluded from subsequent steps.

- **FR-V003**: Pipeline MUST split each transcript into overlapping
  sliding windows with window length = 512 words and stride = 50 words.

- **FR-V004**: Pipeline MUST embed each sliding window using
  `google/embeddinggemma-300m` (768-dimensional), the same model used for
  article and question embeddings.

- **FR-V005**: Pipeline MUST project each window embedding into the
  mapper's 2D space using the UMAP reducer via `reducer.transform()`,
  then normalize to [0,1] using the corresponding bounds file. **Note:**
  The UMAP reducer and bounds will be regenerated once the updated
  question set is finalized (in progress separately). The video pipeline
  must run *after* the new reducer is available. The pipeline script
  should accept reducer and bounds paths as CLI arguments.

- **FR-V006**: Pipeline MUST produce per-domain JSON files
  (`data/videos/{domain-id}.json`) containing, for each video assigned to
  that domain: `id` (YouTube video ID), `title`, `duration_s`,
  `thumbnail_url`, and `windows` (array of [x, y] coordinate pairs). A
  video appears in domain D's file if ≥20% of its windows fall inside D's
  bounding box. Videos may appear in multiple domain files. See CL-008,
  CL-009, CL-010, CL-025.

### Functional Requirements — Client-Side Ranking

- **FR-V010**: System MUST compute Theoretical Learning Potential (TLP)
  for each video using:
  ```
  TLP(v) = (1/N_v) × Σ_w [ (1 - K(x_w, y_w)) × U(x_w, y_w) ]
  ```
  where K is the GP predicted knowledge, U is uncertainty, and the sum
  is over all sliding windows w of video v. The `× U` factor boosts
  high-uncertainty regions (active learning strategy): areas where the GP
  has little data are prioritized for video recommendations. See CL-030.

- **FR-V011**: System MUST present the top 10 videos ranked by estimated
  knowledge gain (TLP in Phase 1, or expected gain in Phase 3+).

- **FR-V012**: System MUST filter candidate videos to those with at least
  20% of sliding window coordinates inside the active domain's bounding
  rectangle. If "All (General)" is selected, all videos are candidates.
  See CL-020.

- **FR-V013**: System MUST apply a penalty multiplier (0.1×) to already-
  watched videos so they rank lower but remain visible in the list.

### Functional Requirements — Difference Maps

- **FR-V020**: System MUST snapshot the global GP estimate grid (50×50 =
  2,500 cells via `globalEstimator`) when a video is marked as "watched,"
  but only if no pending snapshot already exists (from a prior unwatched
  video). If multiple videos are watched without questions between them,
  the snapshot from the first video is retained and all videos' window
  coordinates are merged for relevance weighting. See CL-004.

- **FR-V021**: System MUST count all questions answered after the most
  recent video completion (regardless of domain — see CL-015). After ≥1
  question, the system MUST compute a difference map:
  `D(x,y) = K_after(x,y) - K_before(x,y)` for all 2,500 grid cells. After
  ≥5 questions, the difference map is incorporated into the running average
  and used for ExpectedGain ranking. See CL-004.

- **FR-V022**: System MUST weight the difference map by a relevance
  function based on the watched video's window coordinates:
  ```
  relevance(x, y, V) = max_w matern32(dist((x,y), (x_w, y_w)), l)
  ```
  using the same Matérn 3/2 kernel and length scale as the GP estimator.

- **FR-V023**: System MUST maintain a recency-weighted running average of
  weighted difference maps using exponential moving average:
  ```
  D_running = α × D_new + (1 - α) × D_running_prev
  ```
  with α = 0.3 (giving recent videos ~3× the weight of videos 3 cycles
  ago).

- **FR-V024**: Once a difference map is available, the system MUST rank
  videos by expected gain using observed transfer rates:
  ```
  ExpectedGain(v) = (1/N_v) × Σ_w [ (1 - K(x_w, y_w)) × Transfer(x_w, y_w) ]
  ```
  where Transfer is derived from the running difference map at each
  window coordinate, falling back to a global average where the running
  map has insufficient coverage.

### Functional Requirements — Adaptive Difficulty (GP-IRT)

- **FR-V050**: System MUST compute a difficulty level estimate for each
  grid cell by mapping the GP posterior value to a 4-level ordinal scale
  via IRT thresholds. The mapping is:
  ```
  θ_irt(x,y) = 4 × GP_mean(x,y) - 2    // rescale [0,1] → [-2,2]
  P(correct | θ, d) = sigmoid(a × (θ - b[d]))
  ```
  where `a = 1.5` (discrimination) and `b = [-1.5, -0.5, 0.5, 1.5]`
  for L1–L4. The estimated mastery level is the highest d where
  `GP_mean > threshold[d]`, with thresholds in [0,1] space:
  `[0.125, 0.375, 0.625, 0.875]`. See Issue #23.

- **FR-V051**: System MUST select questions using BALD (Bayesian Active
  Learning by Disagreement) expected information gain instead of raw
  uncertainty. The BALD score for a question q at difficulty d is:
  ```
  EIG(q) = a² × P_q × (1 - P_q) × σ²_irt(x_q, y_q)
  ```
  where `P_q = sigmoid(a × (θ_irt - b[d]))` and `σ_irt = 4 × GP_std`.
  This naturally balances spatial uncertainty (high σ) with difficulty
  informativeness (P near 0.5). See Issue #23.

- **FR-V052**: System MUST implement three-phase question selection:
  - **Calibrate** (N < 10): Prefer L2–L3 questions in high-uncertainty
    regions to establish a rough ability baseline.
  - **Map** (10 ≤ N < 30, or coverage < 15%): Full BALD acquisition to
    refine the ability map and identify difficulty boundaries.
  - **Learn** (N ≥ 30 and coverage ≥ 15%): ZPD targeting — select
    questions where IRT-predicted P(correct) is near 0.55–0.70 for
    optimal learning. Fall back to BALD if local confidence is low.
  Phase transitions are soft: if coverage drops (e.g., new domain region),
  the system reverts to mapping phase.

- **FR-V053**: System MUST add `normalCDF()` to `src/utils/math.js`
  using the Abramowitz & Stegun polynomial approximation. This is used
  for computing the level posterior probability vector per cell.

- **FR-V054**: The IRT and BALD computation overhead MUST be less than
  1ms client-side, adding negligible cost to the existing ~10ms GP
  update cycle. See Issue #23 complexity analysis.

### Functional Requirements — UI

- **FR-V030**: System MUST display video recommendations in a modal
  dialog (separate from the existing insights modal) triggered by the
  graduation-cap suggest button.

- **FR-V031**: Each video entry in the list MUST display: rank number,
  play icon, video title (truncated with ellipsis), estimated gain
  indicator (progress bar + percentage), duration, and watched checkmark
  (if applicable).

- **FR-V032**: Clicking a video in the list MUST transition the modal to
  an inline YouTube player view using the YouTube IFrame Player API with
  privacy-enhanced mode (`youtube-nocookie.com`).

- **FR-V033**: The inline player MUST include: the YouTube iframe with
  native controls, supplemental playback speed buttons (0.5×, 0.75×, 1×,
  1.25×, 1.5×, 2×), a "Back to list" button, and the video's estimated
  gain percentage.

- **FR-V034**: System MUST detect video completion via the YouTube IFrame
  API `onStateChange` event (state === `YT.PlayerState.ENDED`) and mark
  the video as watched.

- **FR-V035**: The gain indicator bar MUST use color coding consistent
  with the existing palette: high gain (≥65%) uses `--color-correct`,
  moderate (35-64%) uses `--color-accent`, low (<35%) uses
  `--color-text-muted`.

- **FR-V036**: The video modal MUST be responsive: on mobile (≤480px),
  the list displays as a bottom sheet (80vh) and the player occupies the
  full viewport.

### Functional Requirements — State & Persistence

- **FR-V040**: System MUST persist watched video IDs across browser
  sessions using `persistentAtom` (localStorage key: `mapper:watchedVideos`).

- **FR-V041**: System MUST begin background-loading per-domain video files
  during the welcome screen, prioritizing the currently selected domain.
  When the user changes domain selection, the system MUST interrupt and
  reprioritize loading for the newly selected domain. Data is cached
  in-memory for the session. See CL-010.

- **FR-V042**: System MUST clear watched video history when the user
  triggers a full progress reset (existing `resetAll()` flow).

- **FR-V043**: Difference maps and running averages are session-only
  state (not persisted). They are recomputed as videos are watched
  within a session.

### Key Entities

- **Video**: A Khan Academy YouTube video with metadata (title, duration,
  id) and an array of 2D window coordinates representing its transcript
  content in the mapper's embedding space. The `id` field is the YouTube
  video ID (globally unique); see CL-025.

- **Sliding Window**: A 512-word excerpt from a video transcript, embedded
  and projected to a 2D coordinate. Each video has N windows (typically
  5-160, depending on video length).

- **Difference Map**: A 50×50 grid (2,500 cells) storing the observed
  change in GP knowledge estimates before vs. after watching a specific
  video and answering ≥5 questions.

- **Running Difference Map**: A recency-weighted exponential moving
  average of all difference maps, used to estimate how much knowledge
  transfers from watching videos covering different regions of the space.

- **Transfer Function**: A per-cell estimate of how much watching a video
  covering that region actually improves knowledge, derived from the
  running difference map.

- **Theoretical Learning Potential (TLP)**: The average knowledge gap
  across a video's window coordinates, uncertainty-weighted. Used for
  initial ranking before any videos have been watched.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-V001**: The offline pipeline produces a video database covering
  ≥7,500 Khan Academy videos with valid 2D window coordinates.

- **SC-V002**: Video recommendations load within 2 seconds of the first
  suggest-button click (video data is background-loaded during welcome
  screen; if not yet cached, the modal shows a spinner until ready).

- **SC-V003**: TLP-based ranking correctly identifies the weakest
  knowledge region as the top recommendation at least 80% of the time,
  as validated by comparing the top video's average window coordinates
  against the GP's minimum-knowledge cell.

- **SC-V004**: After watching one video and answering 5 questions, the
  difference map produces non-zero values in at least 10% of grid cells
  near the video's window coordinates.

- **SC-V005**: Expected gain scoring (Phase 3+) produces measurably
  different rankings from TLP-only scoring (Phase 1), demonstrating that
  observed difference maps influence recommendations.

- **SC-V006**: All video scoring operations complete in <15ms client-side,
  maintaining the existing GP performance budget.

- **SC-V007**: The inline YouTube player loads and begins playback within
  3 seconds of clicking a video in the list.

- **SC-V008**: Video completion detection fires correctly for ≥95% of
  videos played to natural end, as validated by Playwright tests.

- **SC-V009**: The video modal renders correctly on desktop (1024px+),
  tablet (768px), and mobile (320px) viewports with no visual overflow
  or broken layouts.

- **SC-V010**: Watched video state survives page refresh and browser
  restart via localStorage persistence.

- **SC-V011**: Every grid cell in `predict()` output includes a
  `difficultyLevel` (0–4) that correctly maps GP values to IRT
  thresholds: value < 0.125 → 0, [0.125, 0.375) → 1, [0.375, 0.625) → 2,
  [0.625, 0.875) → 3, ≥ 0.875 → 4.

- **SC-V012**: BALD-based question selection produces measurably different
  (and more informative) question orderings than pure uncertainty-based
  selection, verified by comparing EIG scores on synthetic GP states where
  ability varies across the grid.

- **SC-V013**: The IRT + BALD computation adds less than 1ms overhead to
  the existing GP predict/select cycle, verified by timing benchmarks.

- **SC-V014**: Phase transitions fire correctly: calibrate for N < 10,
  map for 10 ≤ N < 30, learn for N ≥ 30 with coverage ≥ 15%. Soft
  fallback to map phase when coverage drops below 15%.

## Assumptions

- The `scrapetube` library can enumerate the full Khan Academy YouTube
  channel (~9,000 videos) without an API key. No Google Cloud account
  or quota management is required.
- ~85-95% of Khan Academy videos have auto-generated or manual transcripts.
  Videos without transcripts are excluded.
- The UMAP reducer will be retrained once the updated question set is
  finalized (in progress in a separate session). The video pipeline
  depends on this new reducer. Transcript embeddings from
  embeddinggemma-300m are validated to produce semantically meaningful
  clusters (CL-016 PoC, gap = 0.111).
- The YouTube IFrame Player API is available in all target browsers and is
  not blocked by default content security policies on GitHub Pages.
- Khan Academy videos are freely available on YouTube and embedding them
  via the IFrame API is permitted under YouTube's Terms of Service.
- The video database is regenerated periodically (e.g., quarterly) as Khan
  Academy publishes new content, but this is a manual pipeline run, not an
  automated process.

## Clarifications

*Generated 2026-02-23 via spec-clarify analysis. 39 items across pipeline,
math, and UI domains. All 39 resolved. CL-016 (transcript embedding PoC)
validated experimentally — gap = 0.111, 2x success threshold.
Updated 2026-02-24: Added CL-040 through CL-048 for GP-IRT adaptive
difficulty selection (Issue #23). Total: 48 clarifications, all resolved.*

### Session 2026-02-24 (GP-IRT clarifications)

- Q: How should BALD handle L5 questions? → A: All domains are being
  revised to L1–L4 only. Assume only 4 difficulty levels exist. No L5
  handling needed.
- Q: How do DIFFICULTY_WEIGHT_MAP and IRT interact? → A: Independent
  layers — DIFFICULTY_WEIGHT_MAP modulates GP input weights, IRT
  reinterprets GP output. No changes needed.
- Q: Should video ranking use IRT difficultyLevel? → A: No. TLP is
  sufficient; IRT only affects question selection, not videos.

### Session 2026-02-23 (second pass)

- Q: How should the pipeline obtain the YouTube API key for FR-V001?
  → A: Replace YouTube Data API v3 with `scrapetube` (no API key required).
  Entire pipeline is now zero API keys: `scrapetube` (enumerate) →
  `youtube-transcript-api` (transcripts) → `embeddinggemma-300m` (embed) →
  UMAP (project). FR-V001, CL-027, assumptions, and plan updated.

### Critical — Must Resolve Before Implementation

**CL-001 — UMAP coordinate space mismatch (pipeline vs frontend)** [RESOLVED]

The existing pipeline is: embed → joint UMAP `fit_transform` → flatten
(optimal transport via `flatten_coordinates.py`) → normalize to [0,1]. The
spec proposes: embed → UMAP `transform()` → normalize via `umap_bounds.pkl`.

**Resolution: The flattening step is solely a visual transform for rendering
article dots on the map — it does not affect the coordinate space used by
the GP estimator. All knowledge estimation (TLP, difference maps,
ExpectedGain) operates in the pre-flatten UMAP space. Therefore,
`reducer.transform()` + `umap_bounds.pkl` normalization places video
windows in the correct coordinate space for estimation. No flattening
displacement needs to be applied to video coordinates.**

**CL-002 — "Stride = 50 words" ambiguity** [RESOLVED]

FR-V003 says "window length = 512 words and stride = 50 words."

**Resolution: Stride means 50-word step size — the window advances 50
words per step, giving 90% overlap (462/512). This produces ~150 windows
per average video and ~1.35M total windows across 9,000 videos. The high
overlap provides dense spatial coverage in UMAP space, making each video
a rich "trail" of points. Pipeline runtime: ~8-12 hrs for embedding.
Output is split into per-domain files (see CL-010) to manage size.**

**CL-003 — Which estimator instance for video scoring?** [RESOLVED]

The codebase has two estimator instances: `estimator` (domain-specific,
re-initialized on domain switch, variable grid sizes 50-120) and
`globalEstimator` (always 50×50 on [0,1]). Video window coordinates are
in the global [0,1] space. The domain estimator cannot evaluate coordinates
outside its region.

**Resolution: All video scoring (TLP, ExpectedGain, snapshots, difference
maps) MUST use `globalEstimator` with the 50×50 grid on [0,1] space.**

**CL-004 — Multiple videos watched before 5 questions answered** [RESOLVED]

**Resolution: Each time a video is watched and then at least ONE question
is answered, the system computes an estimated difference map. However,
the updated difference map is not USED for video recommendations until
5 questions have been answered after the most recently watched video.

Special case: if multiple videos are watched successively without answering
questions in between, treat all of them as a single "concatenated" video
for purposes of updating the maps and recommendations. The snapshot is
taken before the first video in the batch, and all videos' window
coordinates are merged into a single set for relevance weighting.**

**CL-005 — Transfer function: undefined bounds and fallback** [RESOLVED]

**Resolution: Clamp + global fallback.**
- Transfer = `max(0, D_running)` — negative values in D_running are
  preserved (honest signal for future use) but clamped to zero in Transfer
  so ExpectedGain is never negative.
- "Insufficient coverage" = cells where no observed video had a window
  within `2 × lengthScale` AND `|D_running| < 1e-4`.
- Global average = mean of `D_running` over all sufficient-coverage cells.
- Cells with insufficient coverage use the global average as fallback.

**CL-006 — Suggest button collision: one button, two features** [RESOLVED]

**Resolution: The video modal fully REPLACES the existing concept knowledge
list. The suggest button opens the video modal. The old "Suggested
Learning" tab in the insights modal is removed — video recommendations
are strictly superior since they link to actual learning content rather
than generic Khan Academy search links. The leaderboard tab remains in
the insights modal, accessible via the trophy button.**

**CL-007 — Mobile: suggest button hidden at ≤480px** [RESOLVED]

**Resolution: Remove the `display: none` rule for `#suggest-btn` at the
mobile breakpoint. The suggest button is visible on mobile and opens the
video modal as a bottom-sheet (80vh) per FR-V036.**

### High — Should Resolve Before Implementation

**CL-008 — `domain_ids` assignment algorithm** [RESOLVED]

**Resolution: Spatial assignment. A video is assigned to domain D if ≥20%
of its windows fall inside D's bounding box (from `data/domains/index.json`).
A video may be assigned to multiple domains. The pipeline produces
per-domain files, so domain assignment determines which files each video
appears in. See FR-V006.**

**CL-009 — `topics` field** [RESOLVED]

**Resolution: Drop the `topics` field for MVP. The client-side ranking
uses window coordinates, not topics. Topics are not referenced in any
user story or functional requirement. Can be added later from Khan Academy
playlist metadata if a future feature needs them.**

**CL-010 — Output file size and loading strategy** [RESOLVED]

**Resolution: Split into per-domain files (`data/videos/{domain-id}.json`)
matching the existing domain bundle pattern. With 50-word stride (CL-002),
total data is ~15-20 MB across all domains, but each per-domain file is
~0.5-2 MB. Files are background-loaded during the welcome screen in
parallel threads, prioritizing the currently selected domain. When the user
changes domain selection, loading is interrupted and reprioritized for the
newly selected domain. See FR-V041.**

**CL-011 — GP evaluation method for TLP scoring** [RESOLVED]

TLP requires evaluating K(x_w, y_w) at each video window coordinate.
The existing `predict()` returns values for grid cell centers only. With
400K windows (high-overlap) or 155K (low-overlap), per-window GP
evaluation is expensive.

**Resolution: Snap each window coordinate to its nearest 50×50 grid cell
and use the cached `predict()` output. This reduces 400K evaluations to
2,500 cached values with a grid cell lookup per window.**

**CL-012 — Difference map grid must be global** [RESOLVED]

The snapshot grid size depends on which domain is active at snapshot time
(50 for "all", 70 for sub-domains, 120 for general domains). Difference
maps must be comparable across sessions.

**Resolution: Snapshots always use `globalEstimator.predict()` (50×50 on
[0,1]) regardless of the currently active domain.**

**CL-013 — Negative difference map values** [RESOLVED]

**Resolution: Preserve negative values in D_running (honest signal for
future analysis). Clamp Transfer to `max(0, D_running)` so ExpectedGain
is never negative. Consistent with CL-005.**

**CL-014 — EMA initialization for first video** [RESOLVED]

FR-V023 defines D_running = α × D_new + (1 - α) × D_running_prev.
For the first video, no D_running_prev exists.

**Resolution: For the first difference map, D_running = D_new (equivalent
to α = 1.0). Subsequent updates use α = 0.3.**

**CL-015 — 5-question threshold: which questions count?** [RESOLVED]

**Resolution: All questions count, regardless of domain or proximity to
the video's windows. The difference map captures global GP changes, and
the relevance weighting (FR-V022) already handles spatial locality. If
the user watches a physics video then answers art history questions,
those questions still count toward the threshold.**

**CL-016 — UMAP `transform()` quality on transcript text** [RESOLVED]

**Resolution: PoC validated (2026-02-23). Tested 12 KA videos across 4
topics (physics, math, biology, history), 352 sliding windows embedded
with embeddinggemma-300m. Results:**
- Within-topic cosine similarity: 0.855
- Between-topic cosine similarity: 0.744
- Gap: 0.111 (>2x the 0.05 success threshold)

**Transcript embeddings show meaningful topic separation despite spoken
language style. UMAP `transform()` should produce semantically valid
coordinates. See `scripts/poc_transcript_embeddings.py` for details.**

**CL-017 — Inline player behavior on "Back to list"** [RESOLVED]

The spec does not define what happens to the YouTube iframe when navigating
back to the video list.

**Resolution: Navigating back destroys the iframe (stops buffering/playback).
Re-selecting the same video always starts from 0:00. No resume-from-position
state is maintained.**

**CL-018 — Video modal HTML structure** [RESOLVED]

**Resolution: Assign `#video-modal` as the element ID. Add it to the
`handleEscape()` chain in app.js. Escape while in the player view
navigates "back to list"; Escape from the list view closes the modal.**

**CL-019 — Session-only difference maps vs persistent watched state** [RESOLVED]

FR-V040 persists watched video IDs across sessions. FR-V043 makes
difference maps session-only. This means every new browser session starts
in Phase 1 (TLP-only) scoring, even when the user has a long watch history
with the 0.1× penalty applied. This is asymmetric but acceptable.

**Resolution: This is intentional. Document that each new session starts
with TLP-only scoring. The 0.1× penalty still applies from persisted watch
history, but ExpectedGain scoring (Phase 3+) requires at least one
in-session video watch + 5 questions.**

**CL-020 — Domain filtering threshold** [RESOLVED]

**Resolution: Require ≥20% of a video's windows inside the domain
bounding rectangle. This is enforced at pipeline time (determines which
per-domain files a video appears in) and at client time (FR-V012). See
CL-008.**

**CL-021 — Minimum transcript length for inclusion** [RESOLVED]

**Resolution: Exclude videos with transcripts shorter than 100 words.
These produce a single low-quality window insufficient for meaningful
spatial coverage.**

**CL-022 — Transcript language filtering** [RESOLVED]

Khan Academy has content in multiple languages. The embedding model's
behavior on non-English text is undefined.

**Resolution: Download only English transcripts (`en` language code).
Fall back to auto-generated English if manual English is unavailable.
Exclude videos with no English transcript.**

**CL-023 — Speed button set and unavailable rates** [RESOLVED]

FR-V033 specifies speed buttons 0.5×–2× but does not enumerate values
or define fallback for unsupported rates.

**Resolution: Buttons at 0.5×, 0.75×, 1×, 1.25×, 1.5×, 2×. Query
`getAvailablePlaybackRates()` on player ready and disable buttons for
unavailable rates.**

**CL-024 — FR-V042 reset scope incomplete** [RESOLVED]

The existing `resetAll()` does not include the new atoms. All new atoms
must be enumerated in the reset contract.

**Resolution: `resetAll()` must clear `$watchedVideos` (persistent),
`$preVideoSnapshot` (session), `$questionsAfterVideo` (session),
`$differenceMap` (session), and `$runningDifferenceMap` (session).**

### Medium — Resolve During Implementation

**CL-025 — `id` vs `youtube_id` in video schema** [RESOLVED]

FR-V006 lists both `id` and `youtube_id`. **Resolution: Use the YouTube
video ID as `id` (it is globally unique). Drop the separate `youtube_id`
field to avoid redundancy.**

**CL-026 — Thumbnail URL resolution** [RESOLVED]

YouTube provides multiple resolutions. **Resolution: Use `medium`
(320×180) via the URL pattern
`https://i.ytimg.com/vi/{id}/mqdefault.jpg` — no runtime API call needed.**

**CL-027 — YouTube API quota budget** [RESOLVED]

**Resolution: Replaced YouTube Data API v3 with `scrapetube` (no API key
required). Quota management is no longer applicable. `scrapetube` enumerates
the channel directly via YouTube's internal browse API. Use the `sleep`
parameter to rate-limit requests.**

**CL-028 — TLP-to-percentage mapping** [RESOLVED]

The TLP formula produces values in [0, 1]. FR-V035 uses percentage
thresholds. **Resolution: Display `TLP × 100` as the gain percentage.
This is the dynamically computed TLP from the user's current knowledge
state, not a static property.**

**CL-029 — Video completion definition** [RESOLVED]

**Resolution: A video is marked "watched" when and only when
`YT.PlayerState.ENDED` fires. Partial watches, manual seeking to end,
and closing the modal before completion do NOT mark the video as watched.
Rewatching a marked video does not change its state.**

**CL-030 — Uncertainty discount calibration** [RESOLVED]

**Resolution: Use `(1 - K) × U` — boost high-uncertainty regions instead
of penalizing them. This treats video recommendations as an active learning
strategy: areas where the GP has little data AND low estimated knowledge
get the highest TLP scores. FR-V010 has been updated accordingly.**

**CL-031 — Title truncation method** [RESOLVED]

**Resolution: CSS `overflow: hidden; text-overflow: ellipsis;
white-space: nowrap` on the title element. No JS character limit.**

**CL-032 — YouTube IFrame API and CSP compatibility** [RESOLVED]

**Resolution: The IFrame API script (`youtube.com/iframe_api`) is loaded
lazily via dynamic `<script>` injection on first video modal open, with a
guard to prevent double-loading. The iframe src uses `youtube-nocookie.com`.
Note: GitHub Pages does not set restrictive CSP headers by default, so no
CSP changes are needed for the current deployment target. If a CSP is added
in the future, it must include `script-src youtube.com` and `frame-src
youtube-nocookie.com`.**

**CL-033 — Pipeline retry and rate limiting** [RESOLVED]

**Resolution: Rate-limit transcript downloads to 5 requests/second.
Exponential backoff on 429 errors. Checkpoint progress every 500 videos.
Log failures for manual review.**

**CL-034 — Serialized model file availability and versioning** [RESOLVED]

**Resolution: The UMAP reducer and bounds files from `mapper.io/data/`
are from an outdated version of the pipeline and cannot be reused. Both
files will be regenerated in this repository once the updated question
set is finalized (in progress in a separate session). Expected paths:
`data/umap_reducer.pkl` and `data/umap_bounds.pkl`. If either file
exceeds 100 MB it must be added to `.gitignore`. The video pipeline is
blocked on this dependency. Requirements: Python 3.10+, umap-learn >=
0.5, matching numpy version.**

**CL-040 — Empirical claims in GP-IRT design are provisional** [RESOLVED]

**Resolution: The research synthesis (Issue #23) analyzed the CURRENT
question set and UMAP coordinates to derive empirical constraints (6.0%
cell occupancy, 46.3% multi-difficulty cells, ~13/13/12/12 difficulty
balance). These numbers are PROVISIONAL — the question set is actively
being regenerated (new domains, new questions, new difficulty calibration),
and the UMAP reducer will be retrained with the updated corpus. The
architectural decisions (GP-IRT, BALD, phase-based selection) are robust
to these numbers changing because they were chosen for theoretical
optimality, not tuned to specific empirical values. However, once the new
question set and UMAP coordinates are finalized, the following MUST be
verified:
- Cell occupancy (affects whether per-cell methods are feasible)
- Difficulty balance per domain (affects IRT threshold spacing)
- IRT threshold calibration (b values may need adjustment)
- BALD vs uncertainty improvement magnitude
All claims marked "provisional" in the synthesis report should be
re-validated against the final dataset.**

**CL-041 — All domains standardized to 4 difficulty levels** [RESOLVED]

**Resolution: All domains are being revised to use only L1–L4. The IRT
model's 4 thresholds (b = [-1.5, -0.5, 0.5, 1.5]) are sufficient. No L5
handling is needed. The existing `DIFFICULTY_WEIGHT_MAP` in estimator.js
(which only defines weights for levels 1–4) is already correct.**

**CL-042 — IRT parameters are theoretical defaults, not calibrated** [RESOLVED]


**Resolution: The IRT parameters (a = 1.5, b = [-1.5, -0.5, 0.5, 1.5])
are reasonable defaults from IRT literature. They are NOT empirically
calibrated to this specific question set. After collecting anonymized
response data, these should be fit via maximum likelihood. The evenly
spaced thresholds work because the current question difficulty balance
is approximately uniform (~13/13/12/12 per domain across L1–L4). See
Issue #23 Phase D.**

**CL-043 — GP value is not a true IRT ability parameter** [RESOLVED]

**Resolution: The GP posterior mean in [0,1] represents P(correct)
averaged across observed difficulties. The IRT rescaling (4×value - 2)
is an approximation that works when difficulty distribution is roughly
uniform, which holds for the current data. This approximation degrades
if a learner only answers L1 questions — their GP value would be high
but their true ability for L4 content would be overestimated. The BALD
acquisition function mitigates this by preferentially selecting
informative difficulty levels to correct such imbalances.**

**CL-044 — Why not per-cell staircase or BKT methods?** [RESOLVED]

**Resolution: Empirical analysis of the question distribution shows only
6.0% cell occupancy (149/2500 cells have questions) and only 46.3% of
occupied cells have multiple difficulty levels. Per-cell staircase or BKT
methods require multiple observations per cell per difficulty level —
impossible with 50 questions per domain. The GP-IRT approach avoids this
by using the GP's spatial interpolation to infer difficulty levels at
unobserved locations. See Issue #23 data findings.**

**CL-045 — BALD reduces to uncertainty-based when difficulty is uniform** [RESOLVED]

**Resolution: When all candidate questions have the same difficulty level,
BALD EIG = a² × P×(1-P) × σ². Since P is the same sigmoid transform
for all questions, the ranking is dominated by σ² (uncertainty), which
is identical to the current selection behavior. This means the BALD
change is backward-compatible — it only changes behavior when questions
of different difficulties are available at similar locations.**

**CL-046 — Phase transition thresholds** [RESOLVED]

**Resolution: N < 10 (calibrate), 10 ≤ N < 30 (map), N ≥ 30 (learn)
with coverage ≥ 15%. "Coverage" = fraction of occupied cells (cells
containing questions) where uncertainty < 0.5. The 15% coverage floor
triggers a soft fallback to mapping mode when the learner enters an
unexplored region. Thresholds should be tuned with real user data.**

**CL-047 — DIFFICULTY_WEIGHT_MAP and IRT are independent layers** [RESOLVED]

**Resolution: The existing `DIFFICULTY_WEIGHT_MAP` in `estimator.js`
operates at the GP *input* layer — it modulates kernel weights so that
easy-question observations carry less evidence (L1=0.25, L4=1.0). The
new IRT layer operates at the GP *output* layer — it reinterprets the
GP posterior mean as an IRT ability parameter to determine mastery at
each difficulty level. These two systems are complementary and do not
interact directly. No changes to `DIFFICULTY_WEIGHT_MAP` are needed
for the GP-IRT integration.**

**CL-048 — Video recommendations do not use IRT difficulty level** [RESOLVED]

**Resolution: Video ranking uses TLP = (1-K) × U, which targets areas
of low knowledge and high uncertainty. The IRT difficulty level output
is used only for question selection (BALD acquisition). Videos are not
difficulty-graded like questions, so adding difficulty-awareness to
video recommendations would add complexity without clear benefit. TLP
is sufficient for video ranking.**

### Low — Document but Do Not Block

**CL-035 — Incremental pipeline updates** [RESOLVED]

**Resolution: This is a one-shot offline pipeline. Adding new videos
requires re-running the full pipeline. Incremental updates are out of
scope for this feature.**

**CL-036 — Video deduplication** [RESOLVED]

**Resolution: No two entries may share the same YouTube video ID.
Near-duplicate detection (re-uploads, updated versions) is out of scope.**

**CL-037 — Videos removed between scrape and transcript download** [RESOLVED]

**Resolution: Log mismatches. The "mark unavailable" logic from FR-V002
already covers this. Record `scraped_at` timestamp in the output JSON.**

**CL-038 — Out-of-bounds coordinates from `transform()`** [RESOLVED]

**Resolution: Clip to [0.0, 1.0] after normalization. Log the count of
clipped windows. If >10% are clipped, flag the projection as suspect.**

**CL-039 — Timestamp-to-window mapping in transcripts** [RESOLVED]

**Resolution: Concatenate transcript segments into plain text for now.
Document that `youtube-transcript-api` returns timed segments, enabling
future "click window to seek to video position" functionality.**

## Architecture

### File Structure

```
scripts/
  scrape_khan_videos.py          # scrapetube channel enumerator (no API key)
  download_transcripts.py        # Transcript downloader with retry/caching
  embed_video_windows.py         # Sliding window (512w/50-stride) → embeddinggemma-300m
  project_video_coords.py        # UMAP transform + bounds normalization to [0,1]
  export_video_bundles.py        # Split into per-domain JSON files

data/videos/
  {domain-id}.json               # Per-domain video files (~0.5-2 MB each)
  index.json                     # Manifest: domain → video count, file size

src/learning/
  video-recommender.js           # TLP, difference maps, expected gain, EMA

src/ui/
  video-modal.js                 # Video list modal (#video-modal) + inline YouTube player

src/state/
  store.js                       # +5 atoms: $watchedVideos (persistent),
                                 #  $preVideoSnapshot, $differenceMap,
                                 #  $runningDifferenceMap, $questionsAfterVideo
                                 #  (all session-only)
```

### Data Flow

```
[Welcome screen loads]
  → begin background-loading per-domain video files
  → prioritize currently selected domain
  → on domain change: interrupt and reprioritize

[User clicks suggest-btn]
  → await video data for active domain (may already be cached)
  → computeRanking(globalEstimates, diffMap, runAvg, watchedIds)
  → showVideoList(top10) in #video-modal

[User clicks video]
  → renderPlayerScreen(videoId) (swap modal content)
  → load YouTube IFrame API lazily (if first time)

[Video ends → YT.PlayerState.ENDED]
  → markAsWatched(videoId)
  → if no pending snapshot: $preVideoSnapshot = globalEstimator.predict()
  → (if successive videos without questions: merge window coords)

[User answers question (in handleAnswer)]
  → existing estimator.observe() flow
  → if pending snapshot exists:
      → $questionsAfterVideo++
      → if ($questionsAfterVideo >= 1):
          → computeDifferenceMap(snapshot, globalEstimates)  // computed
      → if ($questionsAfterVideo >= 5):
          → updateRunningAverage(newDiffMap, $runningDiffMap) // used
          → enable ExpectedGain scoring (Phase 3+)
          → clear snapshot, reset counter
```

Note on CL-004: Difference maps are COMPUTED after 1+ question (for
internal state) but only USED for ranking after 5+ questions post-video.
If multiple videos are watched without questions between them, their
window coordinates are merged and treated as a single concatenated video.

### GP-IRT Adaptive Difficulty Layer

```
[Existing GP predict() output — value, uncertainty per cell]
  → IRT rescaling: θ_irt = 4×value - 2, σ_irt = 4×uncertainty
  → Difficulty level: L*(x,y) = max{d : value > threshold[d]}
      thresholds in [0,1] space: [0.125, 0.375, 0.625, 0.875]
  → Level posterior: P(level=d) via normalCDF on θ_irt ± σ_irt

[Question selection — replaces pure uncertainty scoring]
  → Phase detection: getPhase(answeredCount, coverage)
  → BALD EIG: a² × P(1-P) × σ²_irt  (map phase)
  → ZPD: 1 - |P - 0.6|              (learn phase)
  → Calibrate: uncertainty × middleDifficultyBonus  (cold start)
```

### Estimation Budget

| Operation | Time | When |
|-----------|------|------|
| TLP scoring (per-domain videos × ~150 windows) | ~1-3ms | Each suggest click |
| Relevance map (2,500 cells × ~150 windows) | ~5-8ms | After 5 post-video questions |
| EMA update (2,500 cells) | <0.01ms | After 5 post-video questions |
| Expected gain scoring (per-domain videos) | ~1-3ms | Each suggest click |
| IRT difficulty level computation (2,500 cells × 4 levels) | ~0.1ms | Each GP predict |
| BALD question scoring (candidates × 4 levels) | ~0.05ms | Each selectNext |

Per-domain files contain ~500-2,000 videos (not all 9,000). All operations
well within the 15ms client-side budget. Window coords are snapped to the
nearest 50×50 grid cell for lookup (CL-011). The IRT + BALD layers add
<1ms total overhead (SC-V013).

## Research References

- **scrapetube** (Python) — YouTube channel/playlist scraper using
  YouTube's internal browse API. No API key required. Used in FR-V001
  for one-time Khan Academy channel enumeration.
  https://github.com/dermasmid/scrapetube

- **youtube-transcript-api** (Python) — Lightweight transcript downloader
  without API key requirement. Used in FR-V002.

- **google/embeddinggemma-300m** — 768-dim text embedding model already
  used for articles and questions. Extended to video transcripts in FR-V004.

- **UMAP transform()** — Projects new points into an existing fitted
  manifold. Validated: 99.6% cluster placement accuracy on in-distribution
  data, <15 minutes for 400K points (FR-V005).

- **Gaussian Process Matérn 3/2 kernel** — Already implemented in
  `src/learning/estimator.js`. Reused for relevance weighting in
  difference maps (FR-V022).

- **YouTube IFrame Player API** — Browser-embedded video playback with
  state change detection. Used for video completion tracking (FR-V034).

- **Item Response Theory (IRT) 2PL Model** — Models P(correct) as a
  function of learner ability θ and item difficulty b via
  `sigmoid(a × (θ - b))`. Used in FR-V050 to map GP values to difficulty
  levels. See Duck-Mayr et al. (GPIRT, UAI 2020).

- **BALD (Bayesian Active Learning by Disagreement)** — Information-
  theoretic acquisition function that selects observations maximizing
  mutual information between predictions and model parameters. Simplifies
  to `a² × P(1-P) × σ²` for 2PL IRT with GP prior. Houlsby et al. 2011.
  Used in FR-V051.

- **QUEST+ (Watson 2017)** — Bayesian adaptive psychometric method for
  discrete stimulus sets. Theoretical basis for the phase-based selection
  strategy. The qCSF variant (Lesmes 2010) demonstrated adaptive
  estimation of structured functions over 2D domains with as few as 25
  trials — directly analogous to our 2D UMAP difficulty mapping.

- **Zone of Proximal Development (ZPD)** — Computationally formalized as
  regions where `0.25 < P(mastered) < 0.75` — identical to the maximum-
  information region under IRT. Used in FR-V052 Phase 3 (learn mode)
  targeting P(correct) ≈ 0.55–0.70.
