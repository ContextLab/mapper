# Tasks: Fix Mobile Mode (Updated 2026-03-11)

**Input**: Design documents from `/specs/007-fix-mobile-mode/`
**Prerequisites**: plan.md (required), spec.md (required)

**Pivot**: Portrait phone mode abandoned. Force landscape on phone-sized map screen. Address GitHub issues #51-53.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup & Completed Work

**Purpose**: Track what's already done from prior implementation

- [X] T001 Add `.header-actions` div and CSS in index.html
- [X] T002 Move reset/download/upload buttons to `.header-actions` in src/app.js
- [X] T003 Fix drawer pull centering: change quiz-panel from position:absolute to position:fixed + width:100vw in index.html
- [X] T004 Add defensive CSS on .drawer-pull in index.html
- [X] T005 Add header constraint: max-width:100vw + box-sizing:border-box on #app-header in index.html
- [X] T006 Update border thickness to 1.5px and color opacity across all UI in index.html + src/ui/*.js
- [X] T007 Reset clears tutorial state (localStorage remove mapper-tutorial) in src/app.js
- [X] T008 Create tests/visual/mobile-header.spec.js (5 tests)
- [X] T009 Create tests/visual/mobile-colorbar.spec.js (3 tests)
- [X] T010 Add drawer pull centering + drift tests in tests/visual/mobile-drawer.spec.js

---

## Phase 2: Force Landscape on Phone Map Screen (US1, Priority: P1)

**Goal**: Phone-sized devices auto-lock to landscape when entering the map screen. Release lock on return to welcome screen.

**Independent Test**: On a phone viewport, entering map screen triggers landscape lock; reset returns to portrait-allowed.

- [X] T011 [US1] Add orientation lock utility: create src/ui/orientation.js with `lockLandscape()` and `unlockOrientation()` using Screen Orientation API with feature detection fallback
- [X] T012 [US1] Call `lockLandscape()` when transitioning to map screen in src/app.js (after switchDomain or landing-start-btn click)
- [X] T013 [US1] Call `unlockOrientation()` in handleReset() in src/app.js when returning to welcome screen
- [X] T014 [US1] Add phone detection: only lock if `screen.width <= 480 || screen.height <= 480` (catches both orientations) + touch check in src/ui/orientation.js
- [X] T015 [US1] Add CSS fallback: if orientation API unavailable, show "rotate device" overlay on phone portrait map screen in index.html
- [X] T016 [US1] Verify all header buttons visible without scrolling in landscape phone viewport (667x375) — tests updated to 667x375
- [X] T017 [US1] Test: mobile tests updated to landscape viewport (667x375) — all 35 tests passing

**Checkpoint**: Phone map screen locks to landscape. Welcome screen allows portrait.

---

## Phase 3: Colorbar Repositioning with Quiz Panel (US2, Priority: P1, GitHub #51)

**Goal**: Colorbar stays visible when quiz panel is expanded. Repositions automatically. Manual drag preserved.

**Independent Test**: With quiz panel open, colorbar is fully visible and not behind panel.

- [X] T018 [US2] Update colorbar positioning logic in src/viz/renderer.js: MutationObserver on quiz panel class changes, auto-reposition colorbar
- [X] T019 [US2] Ensure colorbar respects user-dragged position: _colorbarUserDragged flag skips auto-reposition
- [X] T020 [US2] Update tests/visual/mobile-colorbar.spec.js: added colorbar-within-viewport test + existing overlap test covers this
- [X] T021 [US2] Test colorbar on desktop too: added Desktop Colorbar Visibility test verifying no overlap with side quiz panel

**Checkpoint**: Colorbar always visible regardless of panel state. Drag preserved.

---

## Phase 4: Header Button Hover Fix (US3, Priority: P2, GitHub #52)

**Goal**: Remove scale transform on hover to prevent border clipping from overflow containers.

- [X] T022 [US3] Remove `transform: scale(1.05)` from `.btn-icon:hover:not(:disabled)` in index.html — done in prior session
- [X] T023 [US3] Verify hover effect still looks good (color change + border-color + box-shadow remain) — verified, no scale in CSS

**Checkpoint**: No border clipping on hover.

---

## Phase 5: Question Quality Fixes (US4, Priority: P2, GitHub #53)

**Goal**: Fix Born rule and t-statistic questions.

- [X] T024 [P] [US4] Fix Born rule question in data/domains/quantum-physics.json — rewritten to "what does |ψ(x)|² represent physically?"
- [X] T025 [P] [US4] Fix t-statistic question in data/domains/probability-statistics.json — rewritten to "why t-distribution rather than standard normal?"

**Checkpoint**: Both questions corrected.

---

## Phase 6: Cross-Device & Cross-Mode Verification (US6, Priority: P2)

**Goal**: Verify all fixes across phone landscape, tablet portrait/landscape, desktop.

- [ ] T026 [US6] Run full Playwright test suite at 667x375 (phone landscape), 768x1024 (tablet portrait), 1024x768 (tablet landscape), 1280x800 (desktop) — all must pass
- [ ] T027 [US6] Test on Android emulator: verify landscape lock, header layout, drawer pull, colorbar
- [ ] T028 [US6] Test on iOS simulator: verify landscape lock, header layout, drawer pull, colorbar
- [ ] T029 [US6] Verify desktop mode: no orientation lock, all UI elements render correctly, no regressions

**Checkpoint**: All viewports verified.

---

## Phase 7: Polish & Final

- [ ] T030 Run `npm test` (Vitest unit tests) — fix any failures
- [ ] T031 Run `npx playwright test` full suite — fix any failures
- [ ] T032 Update notes with final status
- [ ] T033 Commit and push all changes

---

## Dependencies

- **Phase 2 (US1 landscape)**: Independent — core new feature
- **Phase 3 (US2 colorbar)**: Independent — can parallel with Phase 2
- **Phase 4 (US3 hover)**: Independent — quick CSS fix
- **Phase 5 (US4 questions)**: Independent — data file edits only
- **Phase 6 (verification)**: Depends on Phases 2-5 complete
- **Phase 7 (polish)**: Depends on Phase 6

### Parallel Opportunities

- T024 + T025 (question fixes) can run in parallel with any other phase
- Phase 3 (colorbar) + Phase 4 (hover) can run in parallel with Phase 2 (landscape)
- T022 + T023 (hover fix) are quick and can be done anytime
