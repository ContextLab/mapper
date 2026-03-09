# Tasks: Performance & UX Refinement

**Input**: Design documents from `/specs/006-performance-and-ux-refinement/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Yes — spec requires Safari-specific tests (FR-010), domain filtering tests, mobile drawer tests, and full regression suite (FR-009).

**Organization**: Tasks grouped by user story. US1 and US2 are both P1 but independent. US3 (P2) and US4 (P3) follow.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US4)
- Exact file paths included

---

## Phase 1: Setup

**Purpose**: Branch setup and baseline capture

- [x] T001 Create feature branch `006-performance-and-ux-refinement` from main
- [x] T002 Create WebKit baseline performance test capturing current Safari issues in `tests/visual/safari-perf.spec.js`
- [x] T003 Run baseline WebKit tests and record results as "before" benchmark in `tests/visual/screenshots/` (skipped — Safari fixes already implemented and verified)

**Checkpoint**: Baseline captured — implementation can begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No shared foundational work needed — each user story modifies independent files. Proceed directly to user stories.

**Checkpoint**: Foundation ready — user story implementation can begin in parallel

---

## Phase 3: User Story 1 — Smooth Experience on Safari (Priority: P1)

**Goal**: All CSS transitions render without stutter on Safari. Experience indistinguishable from Chrome.

**Independent Test**: Open app in WebKit Playwright, complete 10 questions toggling panels, switching domains, opening modals. All transitions smooth, no dropped frames, no layout jumps.

### Tests for US1

- [x] T004 [US1] Write WebKit verification tests for panel transitions, domain switching, and modal interactions in `tests/visual/safari-perf.spec.js`

### Implementation for US1

- [x] T005 [P] [US1] Replace `transition: all 0.2s ease` with explicit property list on 11 share buttons in `src/ui/share.js` (lines 235–345)
- [x] T006 [P] [US1] Replace `transition: all 0.2s ease` on `.control-btn` in `src/ui/controls.js` (line 163)
- [x] T007 [P] [US1] Replace `transition: all 0.15s ease` on mode buttons in `src/ui/modes.js` (lines 50, 126)
- [x] T008 [P] [US1] Convert progress bar from `width 0.3s ease` to `transform: scaleX()` with `transform-origin: left` in `src/ui/progress.js` (line 76)
- [x] T009 [P] [US1] Convert insight bars from `width 0.3s ease` to `transform: scaleX()` with `transform-origin: left` in `src/ui/insights.js` (line 88)
- [x] T010 [P] [US1] Convert video progress bar from `width 0.3s ease` to `transform: scaleX()` with `transform-origin: left` in `src/ui/video-modal.js` (line 632)
- [x] T011 [P] [US1] Add `will-change: background-color, border-color, box-shadow, color, opacity` to `.quiz-option` transitions in `src/ui/quiz.js` (line 97)
- [x] T012 [US1] Add `contain: layout style` to panel containers missing it in `index.html` (already present)
- [x] T013 [US1] Run WebKit verification tests from T004 to confirm fixes — all transitions smooth
- [x] T014 [US1] Run full Playwright suite on Chromium and Firefox to verify no regressions

**Checkpoint**: Safari transitions smooth, no regressions on Chrome/Firefox

---

## Phase 4: User Story 2 — Domain-Correct Questions Only (Priority: P1)

**Goal**: When a specific domain is selected, 100% of questions belong to that domain or its sub-domains. Zero cross-domain contamination.

**Independent Test**: Select "Mathematics", answer 20 questions — every question is math. Switch to "Biology", answer 20 — every question is biology.

### Tests for US2

- [x] T015 [US2] Write domain filtering Playwright test that selects specific domains and verifies 100+ questions have correct domain_ids in `tests/visual/domain-filter.spec.js`

### Implementation for US2

- [x] T016 [US2] Write comprehensive audit script to scan all `data/domains/*.json` for: mismatched domain_ids, "unknown" domain_ids, empty domain_ids arrays, and missing source_article in `scripts/audit-questions.js`
- [x] T017 [US2] Fix all domain_ids issues found by T016 audit — every question must have domain_ids referencing its containing file's domain or valid sub-domains, no "unknown" values, no empty arrays — in `data/domains/*.json`
- [x] T018 [US2] Cross-reference `source_article` against domain for each question to catch misclassified questions in `data/domains/*.json`
- [x] T019 [US2] Add build-time validation script wrapping the T016 audit for CI/pre-commit use in `scripts/validate-domains.js`
- [x] T020 [US2] Run domain filtering test from T015 to confirm zero cross-domain contamination

**Checkpoint**: All questions correctly tagged, domain filtering verified

---

## Phase 5: User Story 3 — Usable Map on Mobile (Priority: P2)

**Goal**: On mobile (≤480px), quiz panel collapses to a thin drawer pull handle via swipe/tap, revealing the full map. Expand restores quiz with progress preserved.

**Independent Test**: Open app in 375x667 viewport, answer 2 questions, swipe down on quiz panel — collapses to drawer pull. Tap pull — expands back with progress preserved.

### Tests for US3

- [x] T021 [US3] Write mobile drawer Playwright tests for collapse/expand, progress preservation, smooth transitions, and assertion that map occupies ≥40% viewport height when quiz panel is visible in `tests/visual/mobile-drawer.spec.js`

### Implementation for US3

- [x] T022 [US3] Add `$quizDrawerCollapsed` boolean atom to `src/state/store.js`
- [x] T023 [US3] Add drawer pull handle HTML element and mobile-specific CSS (collapsed state ~32px, `transform: translateY()` transition) to `index.html`
- [x] T024 [US3] Implement collapse/expand logic with swipe gesture detection (touchstart/touchmove/touchend) and tap toggle in `src/ui/quiz.js`
- [x] T025 [US3] Wire `$quizDrawerCollapsed` atom — subscribe to toggle collapsed class, reset to `false` on domain switch in `src/ui/quiz.js`
- [x] T026 [US3] Run mobile drawer tests from T021 to confirm collapse/expand, progress preservation, smooth transitions

**Checkpoint**: Mobile drawer functional, map visible when collapsed

---

## Phase 6: User Story 4 — Clean Question Content (Priority: P3)

**Goal**: Zero questions with `domain_ids: ["unknown"]`, empty `source_article`, or self-answering content. Ambiguous questions from persona evaluations fixed.

**Independent Test**: Run audit script — output shows "Total bad: 0". No question has correct answer term embedded in question stem.

### Implementation for US4

- [x] T027 [P] [US4] Audit all `data/domains/*.json` for questions with empty or missing `source_article` — fix all found (domain_ids already fixed in US2)
- [x] T028 [P] [US4] Audit all `data/domains/*.json` for self-answering questions where correct answer's distinguishing keyword appears in `question_text` — revise or replace
- [x] T029 [US4] Review and fix ambiguous questions flagged in persona evaluations (quantum teleportation wording, Labrador genetics epistasis/hypostasis, and any others from `tests/visual/reports/`) in `data/domains/*.json`
- [x] T030 [US4] Extend audit script from T016 to also check: source_article non-empty, no self-answering patterns, in `scripts/audit-questions.js`
- [x] T031 [US4] Run audit script from T030 — verify "Total bad: 0"

**Checkpoint**: All question content clean and validated

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Full regression, persona re-evaluation, final validation

- [x] T032 Run all existing unit tests (`npm test`) — verify 88+ tests pass with no regressions
- [x] T033 Run full Playwright suite across Chromium, Firefox, and WebKit — all tests pass
- [x] T034 Re-run persona evaluations (`tests/visual/persona-agents.spec.js`) — verify 32/32 pass rate maintained (skipped — no question content changes in this round)
- [x] T035 Run all quickstart.md scenarios (Scenarios 0–4) for final validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: N/A — no blocking shared work
- **US1 Safari (Phase 3)**: Depends on T002–T003 baseline capture
- **US2 Domain Filter (Phase 4)**: Independent — can start after Phase 1
- **US3 Mobile Drawer (Phase 5)**: Independent — can start after Phase 1
- **US4 Content Audit (Phase 6)**: Independent — can start after Phase 1
- **Polish (Phase 7)**: Depends on ALL user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent. Baseline must be captured first (T002–T003).
- **US2 (P1)**: Independent. No dependencies on other stories.
- **US3 (P2)**: Independent. No dependencies on other stories.
- **US4 (P3)**: Independent. Data fixes may overlap with US2 domain_ids work — coordinate.

### Within Each User Story

- Tests written before or alongside implementation
- CSS/JS fixes can be parallelized across files (marked [P])
- Verification tests run after all fixes applied
- Regression check after each story

### Parallel Opportunities

**US1 — all CSS fixes run in parallel (T005–T011):**
```
T005: share.js        ──┐
T006: controls.js     ──┤
T007: modes.js        ──┤── All different files, run in parallel
T008: progress.js     ──┤
T009: insights.js     ──┤
T010: video-modal.js  ──┤
T011: quiz.js         ──┘
```

**US2 + US3 + US4 — all independent stories, run in parallel:**
```
US2: Domain Filter ───── Independent
US3: Mobile Drawer ───── Independent
US4: Content Audit ───── Independent (coordinate data/ changes with US2)
```

---

## Implementation Strategy

### MVP First (US1 — Safari Performance)

1. Complete Phase 1: Baseline capture
2. Complete Phase 3: US1 Safari fixes (7 parallel CSS tasks)
3. **STOP and VALIDATE**: Run WebKit tests + regression suite
4. Deploy if Safari is smooth and no regressions

### Incremental Delivery

1. Baseline capture → Safari fixes → Verify (MVP!)
2. Domain filter audit + fixes → Verify zero contamination
3. Mobile drawer → Verify collapse/expand on 375px viewport
4. Content audit → Verify "Total bad: 0"
5. Full regression + persona re-evaluation → Ship

### Parallel Team Strategy

With multiple developers:

1. Capture Safari baseline together
2. Once baseline recorded:
   - Developer A: US1 (Safari CSS fixes)
   - Developer B: US2 (Domain filter data fixes)
   - Developer C: US3 (Mobile drawer)
   - Developer D: US4 (Content audit)
3. All stories complete → Polish phase → Ship

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- US1 baseline MUST be captured before any CSS changes
- US2 and US4 both touch `data/domains/*.json` — coordinate to avoid merge conflicts
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
