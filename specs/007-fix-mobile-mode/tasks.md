# Tasks: Fix Mobile Mode

**Input**: Design documents from `/specs/007-fix-mobile-mode/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Tests are included — spec requires Playwright verification and cross-device testing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Branch preparation and audit of current state

- [ ] T001 Audit current header HTML structure and button DOM order in index.html (lines 864-890)
- [ ] T002 Audit current drawer pull CSS and identify all padding/margin sources in index.html (lines 722-786)
- [ ] T003 Audit current colorbar mobile CSS and touch event handling in index.html (lines 831-837) and src/viz/renderer.js

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Structural HTML change that US1 depends on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Add `.header-actions` div between `.header-left` and `.header-right` in index.html (line ~871)
- [ ] T005 Add base CSS for `.header-actions` in index.html: `display: flex; align-items: center; overflow-x: auto; scrollbar-width: none; -webkit-overflow-scrolling: touch; flex-shrink: 1; min-width: 0;` and hide scrollbar with `::-webkit-scrollbar { display: none; }`

**Checkpoint**: New `.header-actions` container exists in DOM and CSS, ready for button insertion

---

## Phase 3: User Story 1 — Header Button Split Layout (Priority: P1) MVP

**Goal**: Reset/download/upload on left (in `.header-actions`), trophy/video/share/tutorial/info on right (in `.header-right`), independent scroll reveal, dropdown fixed.

**Independent Test**: On 375px viewport, verify button positions, swipe both directions, dropdown stays fixed.

### Implementation for User Story 1

- [ ] T006 [US1] Update src/app.js: change button insertion target from `.header-right` to `.header-actions` for reset/download/upload buttons (lines 179-191)
- [ ] T007 [US1] Update mobile CSS in index.html: set `.header-actions { flex: 1; gap: 0.25rem; min-width: 0; }` and `.header-right { flex: 1; gap: 0.25rem; min-width: 0; justify-content: flex-end; }` inside `@media (max-width: 480px)` (line ~710)
- [ ] T008 [US1] Update src/app.js: set initial scroll positions — `.header-actions` scrollLeft=0 (left buttons visible), `.header-right` scrollLeft=scrollWidth (right buttons visible) (line ~615)
- [ ] T009 [US1] Update welcome screen CSS in index.html: move `[aria-label="Import saved progress"]` rule from `.header-right` to `.header-actions` context; hide `.header-actions` buttons except upload on welcome screen (lines 601-606)
- [ ] T010 [US1] Verify dropdown remains fixed: ensure `.header-left` has `flex: 0 0 auto` on mobile so it never scrolls (already set line 710, confirm no regression)

### Tests for User Story 1

- [ ] T011 [US1] Create tests/visual/mobile-header.spec.js: test left-group button positions (reset/download/upload after dropdown)
- [ ] T012 [US1] Add test in mobile-header.spec.js: swipe right reveals hidden left-group buttons
- [ ] T013 [US1] Add test in mobile-header.spec.js: swipe left reveals hidden right-group buttons
- [ ] T014 [US1] Add test in mobile-header.spec.js: dropdown stays visible during header scroll
- [ ] T015 [US1] Add test in mobile-header.spec.js: welcome screen shows only upload (left) and share/info (right)

**Checkpoint**: Header buttons correctly split into two groups with independent scroll. All US1 tests pass.

---

## Phase 4: User Story 2 — Drawer Pull Centering (Priority: P1)

**Goal**: Grab bar perfectly centered horizontally at all times, through any number of open/close cycles.

**Independent Test**: Open/close drawer 10 times, measure pull bar offset each time — must be within 1px of center.

### Implementation for User Story 2

- [ ] T016 [US2] Add defensive CSS to `.drawer-pull` in index.html mobile section: `padding: 0 !important; margin: 0 !important; box-sizing: border-box;` (line ~765)
- [ ] T017 [US2] Audit and confirm `#quiz-panel` has `padding: 0` in BOTH open and closed mobile states in index.html (lines 722-747) — remove any padding that could affect drawer pull width
- [ ] T018 [US2] Verify `.drawer-pull-bar` absolute centering CSS is correct: `position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);` in index.html (line ~777)
- [ ] T019 [US2] Audit src/app.js and src/ui/progress.js for any JS that sets inline styles on `#quiz-panel` or `.drawer-pull` during open/close transitions — ensure no padding/margin is set inline

### Tests for User Story 2

- [ ] T020 [US2] Add centering verification test in tests/visual/mobile-drawer.spec.js: measure pull bar horizontal offset from panel center, assert within 1px
- [ ] T021 [US2] Add cycling test in tests/visual/mobile-drawer.spec.js: open/close drawer 10 times, measure centering after each cycle, assert no drift

**Checkpoint**: Drawer pull bar stays centered through all state transitions. All US2 tests pass.

---

## Phase 5: User Story 3 — Colorbar Visibility (Priority: P2)

**Goal**: Colorbar visible on mobile portrait, positioned top-right, touch-draggable.

**Independent Test**: On 375x667 viewport with heatmap visible, colorbar is visible and touch-draggable.

### Implementation for User Story 3

- [ ] T022 [US3] Verify colorbar mobile CSS in index.html (line ~831): `top: 8px; right: 8px; height: 80px; z-index: 16` — confirm no overlap with header (z-index 100) or quiz panel (z-index 20)
- [ ] T023 [US3] Verify touch drag events in src/viz/renderer.js: touchstart/touchmove/touchend handlers with `passive: false` and `touch-action: none` inline style on colorbar element
- [ ] T024 [US3] Test colorbar visibility when quiz panel is open (55vh) — ensure colorbar at top-right is above the panel area

### Tests for User Story 3

- [ ] T025 [P] [US3] Create tests/visual/mobile-colorbar.spec.js: test colorbar is visible on 375x667 viewport after answering a question
- [ ] T026 [P] [US3] Add test in mobile-colorbar.spec.js: colorbar remains visible when quiz panel is open
- [ ] T027 [US3] Add test in mobile-colorbar.spec.js: colorbar bounding box does not overlap with quiz panel or header

**Checkpoint**: Colorbar visible and functional on mobile. All US3 tests pass.

---

## Phase 6: User Story 4 — Cross-Device Verification (Priority: P2)

**Goal**: All fixes verified on Android emulator and iOS simulator with screenshot evidence.

**Independent Test**: Screenshots from both platforms confirm correct rendering for all three fix areas.

### Implementation for User Story 4

- [ ] T028 [US4] Run full Playwright test suite across Chromium, WebKit, Firefox with mobile viewports — capture results
- [ ] T029 [US4] Start Android emulator, set up adb port forwarding (`adb reverse tcp:5173 tcp:5173`), load app in Chrome, capture screenshots of: header layout, drawer pull open/closed, colorbar
- [ ] T030 [US4] Start iOS Simulator from Xcode, load app in Safari, capture screenshots of: header layout, drawer pull open/closed, colorbar
- [ ] T031 [US4] Compare Android and iOS screenshots — document any platform-specific rendering differences and fix if needed
- [ ] T032 [US4] Run existing test suites to confirm no regressions: `npm test` (unit) and `npx playwright test` (E2E)

**Checkpoint**: Cross-device verification complete with screenshot evidence. All existing tests pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and regression check

- [ ] T033 Run all existing Playwright tests (mobile-drawer, drawer-perf, core) and fix any regressions
- [ ] T034 Run `npm test` (Vitest unit tests) and fix any failures
- [ ] T035 Verify desktop layout is unaffected by mobile CSS changes — take desktop Playwright screenshot
- [ ] T036 Run quickstart.md manual verification steps and confirm all pass
- [ ] T037 Commit all changes with descriptive message and push to branch

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — audit only, no code changes
- **Foundational (Phase 2)**: No code dependencies — adds new HTML element
- **US1 Header Split (Phase 3)**: Depends on Phase 2 (needs `.header-actions` div)
- **US2 Drawer Pull (Phase 4)**: Independent of Phase 2/3 — CSS-only changes
- **US3 Colorbar (Phase 5)**: Independent of Phases 2/3/4 — CSS verification
- **US4 Cross-Device (Phase 6)**: Depends on Phases 3, 4, 5 (all fixes must be in place)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on Foundational (Phase 2) — needs `.header-actions` div
- **US2 (P1)**: No dependencies on other stories — can start immediately
- **US3 (P2)**: No dependencies on other stories — can start immediately
- **US4 (P2)**: Depends on US1 + US2 + US3 all being complete

### Parallel Opportunities

- **US2 and US3 can run in parallel** — they touch different CSS sections and different DOM elements
- **US2 can run in parallel with Phase 2** — drawer pull changes don't depend on header restructure
- T011-T015 (US1 tests) can be written in parallel
- T025-T027 (US3 tests) can be written in parallel

---

## Parallel Example: US2 + US3 Concurrent

```bash
# These two stories can run simultaneously:
# Agent A: Drawer Pull Centering (US2)
Task: "T016 Add defensive CSS to .drawer-pull in index.html"
Task: "T017 Audit #quiz-panel padding in both states"
Task: "T018 Verify .drawer-pull-bar absolute centering"
Task: "T020 Add centering verification test"
Task: "T021 Add cycling test"

# Agent B: Colorbar Visibility (US3)
Task: "T022 Verify colorbar mobile CSS"
Task: "T023 Verify touch drag events"
Task: "T025 Create mobile-colorbar.spec.js"
Task: "T026 Add colorbar visibility with panel open test"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Audit (T001-T003)
2. Complete Phase 2: Add `.header-actions` (T004-T005)
3. Complete Phase 3: Header Split US1 (T006-T015)
4. Complete Phase 4: Drawer Pull US2 (T016-T021) — can overlap with Phase 3
5. **STOP and VALIDATE**: Both P1 stories independently testable

### Full Delivery

6. Complete Phase 5: Colorbar US3 (T022-T027)
7. Complete Phase 6: Cross-Device US4 (T028-T032)
8. Complete Phase 7: Polish (T033-T037)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 (drawer pull) is the highest-risk item — multiple previous fix attempts failed due to padding inheritance
- The key architectural change is adding `.header-actions` (Phase 2) — all other changes are CSS/verification
- Commit after each phase checkpoint
- Take screenshots at each checkpoint for constitution compliance (Principle II)
