# Tasks: UX Cleanup & Bug Fix Sweep

**Input**: Design documents from `/specs/003-ux-bugfix-cleanup/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included where they validate critical math/logic (estimator stability). Visual tests via Playwright E2E are included for UX stories.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Branch preparation and shared infrastructure

- [X] T001 Create feature branch `003-ux-bugfix-cleanup` from `main` and verify dev server starts with `npm run dev`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core math fixes that MUST be complete before any UX stories — the estimator changes affect heatmap rendering, skip behavior, and difficulty weighting.

**⚠️ CRITICAL**: US1 and US2 both depend on the Cholesky stability fix. Complete this phase first.

- [X] T002 Implement adaptive jitter + retry in `choleskySolve()` in `src/utils/math.js`: scale jitter as `1e-6 * Math.max(1, n / 10)` where n = matrix size; on negative diagonal during decomposition, retry with 10× jitter (max 3 retries); keep NaN fallback to zero vector with console.warn
- [X] T003 Add dual difficulty weight maps in `src/learning/estimator.js`: rename `DIFFICULTY_WEIGHT_MAP` to `CORRECT_WEIGHT_MAP` (keep `{1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0}`); add `INCORRECT_WEIGHT_MAP = {1: 1.0, 2: 0.75, 3: 0.5, 4: 0.25}`; update `observe()` to select weight map based on `correct` parameter; update `observeSkip()` to use `INCORRECT_WEIGHT_MAP`; update `_recompute()` to use pre-stored weights unchanged
- [X] T004 Remove skip length scale reduction in `src/app.js`: delete `const SKIP_LENGTH_SCALE_FACTOR = 0.5` (line 29); change `handleSkip()` to pass `UNIFORM_LENGTH_SCALE` (not `UNIFORM_LENGTH_SCALE * SKIP_LENGTH_SCALE_FACTOR`) to `estimator.observeSkip()` and `globalEstimator.observeSkip()`; same change in `restore()` path if applicable

**Checkpoint**: GP estimator now handles 200+ observations without Cholesky errors, difficulty weights are correctly inverted for wrong answers, and skips use full spatial footprint.

---

## Phase 3: User Story 1 — Knowledge Estimator Produces Accurate Maps (Priority: P1) 🎯 MVP

**Goal**: Users can answer 200+ questions without console errors, with smooth heatmap progression (no >5% jumps in "domain mapped").

**Independent Test**: Automate 200 question-answer cycles in a Vitest test; assert no NaN/Infinity in estimates, domain-mapped percentage never jumps >5% per answer, and console has no Cholesky warnings.

### Implementation for User Story 1

- [X] T005 [US1] Write Vitest test in `tests/algorithm/estimator-stability.test.js`: create Estimator instance with 50×50 grid over [0,1]×[0,1]; simulate 200 observations at random coordinates with random correct/incorrect outcomes; after each observation, call `predict()` and assert: (a) no values are NaN/Infinity, (b) all values in [0,1], (c) coverage percentage changes by ≤5% from previous step; also test with 150 observations clustered in a small region to stress Cholesky
- [X] T006 [US1] Write Vitest test in `tests/algorithm/estimator-stability.test.js`: verify that after 200 observations, `predict()` returns a gradient (not uniform blob) — assert standard deviation of cell values > 0.05; verify at least some cells near correct-answer observations have value > 0.7 and some cells near incorrect-answer observations have value < 0.3
- [X] T007 [US1] Run `npx vitest run tests/algorithm/estimator-stability.test.js` and verify all tests pass with the foundational fixes from Phase 2

**Checkpoint**: Estimator is numerically stable for extended sessions. Tests prove no collapse.

---

## Phase 4: User Story 2 — Difficulty-Aware Knowledge Estimation (Priority: P1)

**Goal**: Hard-question wrong answers produce less negative impact than easy-question wrong answers. Skips produce stronger negative evidence than wrong guesses.

**Independent Test**: Unit test comparing heatmap values at the same cell after controlled answer sequences with different difficulty levels.

### Implementation for User Story 2

- [X] T008 [US2] Write Vitest test in `tests/algorithm/estimator-difficulty.test.js`: create two Estimator instances with identical grids; in Estimator A, observe one incorrect answer at (0.5, 0.5) with difficulty=1 (easy); in Estimator B, observe one incorrect answer at (0.5, 0.5) with difficulty=4 (expert); predict cell at (0.5, 0.5) in both; assert Estimator A's value < Estimator B's value (easy-wrong has more negative impact)
- [X] T009 [US2] Write Vitest test in `tests/algorithm/estimator-difficulty.test.js`: create two Estimator instances; in Estimator A, observe one incorrect answer at (0.5, 0.5); in Estimator B, observeSkip at (0.5, 0.5) (same difficulty); predict cell at (0.5, 0.5) in both; assert Estimator B's value < Estimator A's value (skip is stronger negative evidence)
- [X] T010 [US2] Run `npx vitest run tests/algorithm/estimator-difficulty.test.js` and verify all tests pass with the weight maps from Phase 2

**Checkpoint**: Difficulty weighting is correct. Easy-wrong > expert-wrong negative impact. Skip > wrong negative impact.

---

## Phase 5: User Story 3 — Skip Reveals Correct Answer (Priority: P2)

**Goal**: "Don't know (skip)" highlights the correct answer and shows learning resource links before advancing.

**Independent Test**: Click "Don't know (skip)" and verify correct answer highlights green and Wikipedia/Khan Academy links appear.

### Implementation for User Story 3

- [X] T011 [US3] Add `showSkipFeedback(question)` function in `src/ui/quiz.js`: reuse logic from `handleOptionClick()` to highlight the correct answer with `correct-highlight` class; set feedback text to "Skipped — here's the answer:"; show the actions bar (Next button, Wikipedia link, Khan Academy link); do NOT disable options (they're already not selected); export the function
- [X] T012 [US3] Update `handleSkip()` in `src/app.js` to call `quiz.showSkipFeedback(question)` before `selectAndShowNextQuestion()`; remove the immediate `selectAndShowNextQuestion()` call — let the user click "Next" to advance (or auto-advance after delay if auto-advance is on); ensure the skip response is still recorded and estimator updated before showing feedback

**Checkpoint**: Skipping a question now shows the correct answer and resource links, matching the wrong-answer experience.

---

## Phase 6: User Story 4 — Keyboard Shortcuts Respect Modifier Keys (Priority: P2)

**Goal**: Cmd+C, Ctrl+A, Shift+B, Alt+D do not trigger answer selection.

**Independent Test**: Press Cmd+C while a question is displayed — no answer selected, clipboard copy works.

### Implementation for User Story 4

- [X] T013 [US4] Add modifier key guard to `handleKeyDown()` in `src/ui/quiz.js` (line 260): at the top of the function, before any key processing, add `if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;` — this lets the browser handle standard shortcuts (copy, select all, etc.) without triggering answer selection

**Checkpoint**: Keyboard shortcuts with modifier keys no longer accidentally select answers.

---

## Phase 7: User Story 5 — Hover Popup Does Not Block Map Scrolling (Priority: P2)

**Goal**: Click-drag to scroll works smoothly even when hovering over article/video dots.

**Independent Test**: Hover over an article dot (tooltip appears), begin click-drag — tooltip dismisses immediately, smooth scrolling through dot-dense areas.

### Implementation for User Story 5

- [X] T014 [US5] Add `pointer-events: none` to the tooltip element in `src/viz/renderer.js`: find the tooltip creation code (the element created by `_showTooltip()`), add inline style `pointerEvents = 'none'` so it can never intercept mouse events
- [X] T015 [US5] Dismiss tooltip on mousedown in `src/viz/renderer.js`: in the mousedown/pointerdown handler (`_handleMouseDown` or equivalent), call `this._hideTooltip()` immediately; also add a guard in `_handleMouseMove()` to skip `_showTooltip()` calls while `this._isDragging` is true

**Checkpoint**: Popups can never block dragging or intercept mouse events during scroll.

---

## Phase 8: User Story 6 — Canvas Resize Alignment (Priority: P2)

**Goal**: All visual layers stay aligned after browser window resize.

**Independent Test**: Display map with articles and answered questions, resize browser window, verify no layer drift.

### Implementation for User Story 6

- [X] T016 [US6] Fix `_handleResize()` in `src/viz/renderer.js`: before calling `_resize()`, capture the old `_width` and `_height`; after `_resize()` sets the new dimensions, recalculate `_panX` and `_panY` proportionally: `this._panX *= (this._width / oldWidth); this._panY *= (this._height / oldHeight)`; then call `_clampPanZoom()` and `_render()`

**Checkpoint**: Heatmap, articles, videos, and answered question dots all stay aligned after resize.

---

## Phase 9: User Story 7 — Import Progress Works From Landing Page (Priority: P2)

**Goal**: Uploading a progress JSON from the landing page loads all answered question markers (not just the first).

**Independent Test**: Export progress, reload to landing page, import JSON — all markers and heatmap appear.

### Implementation for User Story 7

- [X] T017 [US7] Fix `handleImport()` in `src/app.js`: the issue is that when importing from the landing page, `handleImport()` calls `renderer.setAnsweredQuestions()` before `switchDomain()` has run; after `switchDomain()` creates a new renderer, the answered dots are lost. Fix: move the `renderer.setAnsweredQuestions()` call to AFTER `switchDomain()` completes. In the `if (!currentDomainBundle)` branch (line 741), after `$activeDomain.set('all')`, add a subscriber that runs once after `switchDomain()` finishes to re-apply `renderer.setAnsweredQuestions(responsesToAnsweredDots($responses.get(), questionIndex))`
- [X] T018 [US7] Verify the fix by checking that `switchDomain()` (which runs on `$activeDomain` change) calls `estimator.restore()` with the full `$responses.get()` and then calls `renderer.setAnsweredQuestions()` after `questionIndex` is populated. If `switchDomain()` already does this, the fix may be simpler: ensure the `questionIndex` is available before `renderer.setAnsweredQuestions()` is called during the domain switch path

**Checkpoint**: Import from landing page shows all markers and heatmap, identical to importing from map screen.

---

## Phase 10: User Story 8 — Minimap Viewport Dragging (Priority: P3)

**Goal**: Click-drag the viewport rectangle in the minimap to pan the main map.

**Independent Test**: Click inside the minimap viewport rectangle, drag to new position — main map pans to follow.

### Implementation for User Story 8

- [X] T019 [US8] Relax viewport hit-test in `_isInsideViewport()` in `src/viz/minimap.js`: add 3px padding to the viewport boundaries so the drag is easier to initiate; verify the drag path calls `navigateHandler()` with `animate=false` (smooth following, not animated jump); test that click outside viewport still centers the map on the clicked position

**Checkpoint**: Minimap viewport dragging works as expected — click-drag inside viewport pans, click outside centers.

---

## Phase 11: User Story 9 — Video Discovery Panel (Priority: P3)

**Goal**: Left sidebar panel with viewport-filtered, searchable video list; hover highlights trajectory; click opens player.

**Independent Test**: Open video panel, pan map — list updates; hover video — trajectory highlights; click video — YouTube player opens; search filters list.

### Implementation for User Story 9

- [X] T020 [P] [US9] Create `src/ui/video-panel.js` module: export `init(container, options)`, `setVideos(markers)`, `updateViewport(viewport)`, `setWatchedVideos(watchedSet)`, `show()`, `hide()`, `toggle()`, `destroy()`; the panel is a left sidebar (CSS mirror of quiz panel on right) with a search input, scrollable video list, toggle button for marker visibility, and a count display; group VideoMarkers by videoId and deduplicate; sort by marker count in viewport (most relevant first)
- [X] T021 [P] [US9] Add video panel CSS to `index.html`: create `.video-panel` styles mirroring `.quiz-panel` but on the left side; include styles for `.video-panel-item` (hover, watched indicator), `.video-panel-search`, `.video-panel-toggle`, and `.video-panel-count`; ensure responsive behavior at mobile breakpoints
- [X] T022 [US9] Add video panel toggle button to the header/controls area in `index.html`: a small button (e.g., `<button id="video-panel-btn">`) positioned on the left side of the map screen; icon: film/video icon from Font Awesome
- [X] T023 [US9] Wire video panel in `src/app.js`: import `video-panel.js`; after renderer init, create the panel; call `videoPanel.setVideos()` with the loaded catalog markers; subscribe to viewport changes to call `videoPanel.updateViewport()`; wire `onVideoSelect` to `videoModal.playVideo()`; wire `onVideoHover` to `renderer.setHoveredVideoId()`; wire `onToggleMarkers` to `renderer.setShowVideoMarkers()`
- [X] T024 [US9] Add `setShowVideoMarkers(visible)` method to `src/viz/renderer.js`: controls whether video markers are drawn in `_drawVideos()`; default to hidden (videos only visible via panel toggle or individual hover)
- [X] T025 [US9] Implement viewport filtering in `video-panel.js`: `updateViewport(viewport)` filters the full marker list to those with `x` between `viewport.x_min`–`viewport.x_max` and `y` between `viewport.y_min`–`viewport.y_max`; group by videoId; re-render the list; debounce updates (100ms) to avoid jank during rapid panning

**Checkpoint**: Video panel fully functional — viewport-filtered list, search, hover trajectory, click-to-play, toggle markers.

---

## Phase 12: User Story 10 — Share Modal Works Correctly (Priority: P3)

**Goal**: Social media buttons open correct sharing URLs directly; Copy copies text; Copy Image copies image.

**Independent Test**: Click Twitter button → new tab with twitter.com/intent/tweet; Click Copy → clipboard has text only; Click Copy Image → clipboard has PNG.

### Implementation for User Story 10

- [X] T026 [P] [US10] Fix social share buttons in `handleShareAction()` in `src/ui/share.js`: for `linkedin`, `twitter`, and `bluesky` actions, remove the `navigator.canShare` / `navigator.share()` try-catch blocks that open the native OS share sheet; always use the direct URL-based sharing (the `openInBackground()` calls that are currently in the fallback path); keep the LinkedIn "text copied" toast as-is
- [X] T027 [P] [US10] Fix Copy button in `handleShareAction()` in `src/ui/share.js`: in the `action === 'copy'` branch, remove lines 448-455 that copy the image to clipboard after copying text; Copy should ONLY copy text via `navigator.clipboard.writeText(shareText)`; the image copy functionality belongs exclusively to the `copy-image` action

**Checkpoint**: Share modal buttons each perform their distinct action correctly without native share dialogs.

---

## Phase 13: User Story 11 — Article Title Formatting (Priority: P3)

**Goal**: Article titles display with spaces, not underscores.

**Independent Test**: Answer a question from a multi-word article — source shows "Quantum Field Theory" not "Quantum_Field_Theory".

### Implementation for User Story 11

- [X] T028 [US11] Fix article title display in `handleOptionClick()` in `src/ui/quiz.js` (line 373): change `sourceLink.textContent = article` to `sourceLink.textContent = article.replace(/_/g, ' ')` — this converts Wikipedia URL slugs to readable titles while keeping the raw slug in the `href` URL

**Checkpoint**: All article titles display cleanly with spaces.

---

## Phase 14: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories

- [X] T029 Run full unit test suite with `npx vitest run` and verify all tests pass
- [X] T030 Run Playwright E2E tests with `npx playwright test` and verify no visual regressions
- [X] T031 Manual quickstart validation: follow `specs/003-ux-bugfix-cleanup/quickstart.md` steps 1–11 and verify each acceptance scenario
- [X] T032 Verify no console errors after answering 150+ questions across a domain (SC-001)
- [X] T033 Verify share modal: Twitter button opens new tab (not native dialog), Copy copies text only, Copy Image copies PNG (SC-006)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (Phase 2) — estimator stability
- **US2 (Phase 4)**: Depends on Foundational (Phase 2) — difficulty weighting
- **US3–US11 (Phases 5–13)**: Depend on Foundational (Phase 2) — independent of each other
- **Polish (Phase 14)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 (Cholesky fix). No dependencies on other stories.
- **US2 (P1)**: Depends on Phase 2 (weight maps). No dependencies on other stories.
- **US3 (P2)**: Independent after Phase 2. Touches `quiz.js` and `app.js`.
- **US4 (P2)**: Independent after Phase 2. Touches `quiz.js` only (different function than US3).
- **US5 (P2)**: Independent after Phase 2. Touches `renderer.js` only.
- **US6 (P2)**: Independent after Phase 2. Touches `renderer.js` only (different function than US5).
- **US7 (P2)**: Independent after Phase 2. Touches `app.js` only.
- **US8 (P3)**: Independent after Phase 2. Touches `minimap.js` only.
- **US9 (P3)**: Independent after Phase 2. New file + `app.js` + `renderer.js` + `index.html`.
- **US10 (P3)**: Independent after Phase 2. Touches `share.js` only.
- **US11 (P3)**: Independent after Phase 2. Touches `quiz.js` only (different function than US3/US4).

### File Conflict Matrix

| File | User Stories |
|------|-------------|
| `src/utils/math.js` | Phase 2 only |
| `src/learning/estimator.js` | Phase 2 only |
| `src/ui/quiz.js` | US3 (showSkipFeedback), US4 (handleKeyDown), US11 (handleOptionClick) — different functions, can parallelize |
| `src/viz/renderer.js` | US5 (tooltip), US6 (resize), US9 (setShowVideoMarkers) — different methods, can parallelize |
| `src/app.js` | US3 (handleSkip), US7 (handleImport), US9 (wiring) — different functions, serialize US3→US7→US9 |
| `src/ui/share.js` | US10 only |
| `src/viz/minimap.js` | US8 only |
| `src/ui/video-panel.js` | US9 only (new file) |
| `index.html` | US9 only (CSS + button) |

### Parallel Opportunities

After Phase 2 completes, the following can run in parallel:
- **Group A** (quiz.js): US3 + US4 + US11 (different functions in same file)
- **Group B** (renderer.js): US5 + US6 (different methods in same file)
- **Group C** (independent files): US7, US8, US10 (each touch a unique file)
- **Group D** (new feature): US9 (mostly new file, minor touches to app.js/renderer.js — serialize after Groups A-C)

---

## Parallel Example: After Phase 2

```
# These can all run in parallel (different files):
Task: T013 [US4] Modifier key guard in src/ui/quiz.js
Task: T014 [US5] Tooltip pointer-events in src/viz/renderer.js
Task: T016 [US6] Resize alignment in src/viz/renderer.js
Task: T017 [US7] Import fix in src/app.js
Task: T019 [US8] Minimap hit-test in src/viz/minimap.js
Task: T026 [US10] Share modal fix in src/ui/share.js
Task: T028 [US11] Article title fix in src/ui/quiz.js
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (Cholesky fix + weight maps + skip length scale)
3. Complete Phase 3: US1 (stability tests)
4. Complete Phase 4: US2 (difficulty weighting tests)
5. **STOP and VALIDATE**: The core math is correct and stable
6. Deploy if ready — all other stories are UX polish on top of correct math

### Incremental Delivery

1. Phase 2 → Core math correct
2. US1 + US2 → Estimator validated (P1 complete)
3. US3 + US4 + US5 + US6 + US7 → Core UX bugs fixed (P2 complete)
4. US8 + US9 + US10 + US11 → Features & polish (P3 complete)
5. Phase 14 → Full validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- The foundational Phase 2 is the highest-value work — it fixes the two P1 bugs that undermine the core product
