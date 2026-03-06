# Tasks: Tutorial Mode, Data Fixes & UX Polish

**Input**: Design documents from `/specs/005-tutorial-and-polish/`
**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: Persona re-testing (Phase E) serves as the integration test suite. Playwright tests added for tutorial flow. Existing tests must not regress (SC-006).

**Organization**: Tasks are grouped by spec phase (A-E). Phases A and B can run in parallel. Phase C depends on B1 (question validation guard). Phase D is independent. Phase E depends on all prior phases.

## Format: `[ID] [P?] [Phase] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Phase]**: Which spec phase this task belongs to (PA, PB, PC, PD, PE)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create branch, directory structure, and shared CSS infrastructure

- [ ] T001 Verify branch `005-tutorial-and-polish` exists and is checked out
- [ ] T002 Create placeholder files: `src/ui/tutorial.js`, `src/ui/tutorial-animations.js`, `src/ui/tutorial.css`, `src/ui/milestones.js`
- [ ] T003 [P] Add M3 motion CSS custom properties to `src/ui/tutorial.css`: `--ease-emphasized-decel`, `--ease-emphasized-accel`, `--ease-standard`, `--dur-short`, `--dur-medium`, `--dur-long`, `--dur-xlong`, `--tutorial-accent`, `--tutorial-success`, `--tutorial-gap`

**Checkpoint**: Branch ready, placeholder files exist, CSS variables defined

---

## Phase 2: Data Integrity Fixes (Phase A)

**Purpose**: Fix broken questions, incorrect answers, and missing metadata. Zero code changes to the app — only data file edits and one runtime guard.

- [ ] T004 [P] [PA] Locate and fix the Chern-Simons theory question in `data/domains/*.json` — ensure all 4 options are non-empty strings with valid LaTeX
- [ ] T005 [P] [PA] Locate and fix the perturbation theory E_0^(2) question in `data/domains/*.json` — ensure all 4 options are non-empty strings
- [ ] T006 [P] [PA] Locate and fix the primitive root modulo n question in `data/domains/*.json` — ensure all 4 options are non-empty strings
- [ ] T007 [P] [PA] Locate and fix the QCD asymptotic freedom (N_f) question in `data/domains/*.json` — ensure all 4 options are non-empty strings
- [ ] T008 [PA] Rewrite the Larmor theorem question in `data/domains/physics.json` to avoid rotation/precession ambiguity — test a different aspect (e.g., precession frequency formula or gyromagnetic ratio relationship)
- [ ] T009 [PA] Audit all `data/domains/*.json` files for questions with `domainId: "unknown"` or empty `sourceArticle`. For each: (1) verify source article exists via web search, (2) assign correct domainId matching `data/domains/index.json`, (3) remove questions that can't be properly categorized
- [ ] T010 [PA] Audit flagged weak distractors: fix "Persona" distractor in Freud question, "Drops to zero" in competitive inhibitor question, and any other implausible distractors identified in persona reports. Replace with domain-plausible alternatives.

**Checkpoint**: All broken questions fixed. Run `node -e "..."` to verify no questions have empty options or unknown domainId.

---

## Phase 3: Critical UX Fixes (Phase B)

**Purpose**: Add runtime guards and fix metrics. Can run in parallel with Phase 2.

- [ ] T011 [P] [PB] Add question validation guard in `src/ui/quiz.js` — before serving a question, reject if: fewer than 4 options have non-empty string values, `correctAnswer` is missing or doesn't match any option key, or `questionText` is empty/under 10 chars. Skip silently and serve next valid question.
- [ ] T012 [P] [PB] Investigate and fix `domainMappedPct` calculation in `src/learning/estimator.js` — it should reflect the fraction of the domain's coordinate space explored by answered questions. Currently stuck at 0% for all personas.
- [ ] T013 [P] [PB] Add defensive logging in `tests/visual/personas/runner.js` when a "?" answer is produced — log which code path triggered it (line 128 db-miss, line 219 mapping failure, or line 235 mapping error) to aid debugging
- [ ] T014 [PB] Fix cross-domain question filtering in `src/domain/loader.js` or `src/ui/quiz.js` — when `$activeDomain` is a specific domain, only serve questions whose `domainId` matches that domain or its ancestors/descendants. Prevent clinical-psychology questions appearing in Mathematics mode.

**Checkpoint**: Start dev server, verify no broken questions appear, domainMappedPct updates as questions are answered, domain-specific mode only shows relevant questions.

---

## Phase 4: Tutorial Mode (Phase C) — MVP

**Purpose**: Implement the guided tutorial with 8 steps, highlight overlay, inline SVG animations, and state management.

**Independent Test**: Start with fresh localStorage, verify tutorial auto-starts, walk through all 8 steps, verify it doesn't restart after completion.

### Tutorial Infrastructure

- [ ] T015 [PC] Implement tutorial state machine in `src/ui/tutorial.js` — export `initTutorial(appState)`, `advanceTutorial(event)`, `dismissTutorial()`, `resetTutorial()`, `isTutorialActive()`. Manage localStorage key `mapper-tutorial` with schema: `{ completed, dismissed, step, hasSkippedQuestion, skipToastShown, returningUser }`. Check `$responses` length to set `returningUser` flag.
- [ ] T016 [PC] Implement highlight overlay system in `src/ui/tutorial.js` — full-viewport semi-transparent overlay with CSS `clip-path` cutout for highlighted element. Highlighted element gets pulsing accent border ring (2px, 1.5s interval). Modal positioned near (not overlapping) highlighted element. On mobile ≤480px, modals use bottom-sheet positioning.
- [ ] T017 [PC] Implement tutorial modal component in `src/ui/tutorial.js` — themed modal (dark panel background, white text, accent colors). Include "×" dismiss button, "Skip Tutorial" link, and "Next" button. Enter/exit with M3 emphasized easing (300ms). Respect `prefers-reduced-motion`.

### Tutorial Steps

- [ ] T018 [PC] Implement Step 1: UI Orientation (3 sub-steps) in `src/ui/tutorial.js` — 1a: highlight main canvas, explain knowledge map concept (related concepts nearby, colors = knowledge). 1b: highlight quiz panel (right/bottom on mobile). 1c: highlight video panel (left side — skip on mobile ≤480px). Each sub-step is a separate modal with "Next" to advance.
- [ ] T019 [PC] Implement Step 2: First Questions in `src/ui/tutorial.js` — after Step 1 dismissed, show "Let's try it!" modal highlighting quiz panel. After first answer, show inline SVG map animation (before→after) and explain color meaning. Adapt text for returning users ("Your map already has some data — let's explore further!").
- [ ] T020 [PC] Implement Step 3: Building the Map in `src/ui/tutorial.js` — triggers after ~4 total questions. Show map development explanation. If user got one wrong, include encouraging message about wrong answers being valuable. Highlight heatmap canvas with inline SVG animation (3-frame progressive color development).
- [ ] T021 [PC] Implement Step 4: Skipping (conditional) in `src/ui/tutorial.js` — skip entirely if `hasSkippedQuestion` is true. Otherwise highlight Skip button, explain skipping, but do NOT require user to press it — any action (answer or skip) advances. On first skip during tutorial (at any step), show one-time toast: "Noted! The system now knows this topic might be unfamiliar." Set `skipToastShown` flag. No toast outside tutorial mode.
- [ ] T022 [PC] Implement Step 5: Switch Domains in `src/ui/tutorial.js` — highlight domain dropdown. Wait for user to select a domain. On selection, show confirmation with domain name. If viewport > 480px, also highlight minimap and explain navigation ("Drag to navigate!"). On mobile, skip minimap highlight.
- [ ] T023 [PC] Implement Step 6: Explore Another Domain in `src/ui/tutorial.js` — suggest the most distant domain from current selection. Wait for domain switch + 2-3 questions answered. Brief explanation of different map regions. On mobile, no minimap references.
- [ ] T024 [PC] Implement Step 7: Discover Features (3 sub-steps) in `src/ui/tutorial.js` — 7a: highlight "My Areas of Expertise" button, overlay text "Your estimated strongest topics, ranked. Tap to explore!" 7b: highlight "Suggested Learning" button, overlay text "Videos picked for your biggest knowledge gaps. Watching these gives you the largest boost!" 7c: highlight share button, overlay text "Share your knowledge map with friends!" User can click each or press "Next".
- [ ] T025 [PC] Implement Step 8: Completion in `src/ui/tutorial.js` — show simplified summary: strongest area (highest avg estimate) and most room to grow (lowest avg estimate). Include note about estimates improving with more answers. Footer with paper link, "replay tutorial" info. Set `completed: true` in localStorage.

### Tutorial Animations

- [ ] T026 [P] [PC] Create map evolution SVG animation in `src/ui/tutorial-animations.js` — 200×120px inline SVG with simplified grid. 3 frames: gray → green region → red/pink region. CSS opacity crossfade, 500ms standard easing. Colors match heatmap palette. Export as function returning SVG element.
- [ ] T027 [P] [PC] Create minimap SVG animation in `src/ui/tutorial-animations.js` — 80×80px inline SVG showing simplified minimap. Animated viewport rectangle sliding between regions via CSS transform, 500ms standard easing.
- [ ] T028 [P] [PC] Create feature highlight SVG animation in `src/ui/tutorial-animations.js` — small SVG showing button → panel opening. 2 frames with CSS transform:translateY + opacity, 300ms emphasized-decelerate.

### Tutorial CSS

- [ ] T029 [PC] Write all tutorial styles in `src/ui/tutorial.css` — overlay, modal, highlight ring, bottom-sheet mobile variant, animation keyframes, `prefers-reduced-motion` overrides. All using CSS custom properties from T003. Import in `src/app.js`.

### Tutorial Toggle & Integration

- [ ] T030 [PC] Add tutorial toggle to header menu in `src/app.js` or `src/ui/modes.js` — "Tutorial Mode" toggle that resets tutorial state and restarts from Step 1 when toggled ON, dismisses active tutorial when toggled OFF. Subtle dot/badge on menu icon when tutorial is active.
- [ ] T031 [PC] Wire tutorial into `src/app.js` — call `initTutorial()` after app initialization. Hook `advanceTutorial()` into question-answered events, domain-switch events, and skip events. Ensure tutorial doesn't interfere with normal app operation when inactive.

### Tutorial Tests

- [ ] T032 [PC] Create Playwright test `tests/visual/tutorial.spec.js` — test full tutorial flow: fresh start → auto-starts → walk through all 8 steps → verify completion state in localStorage. Test dismiss at Step 3 → verify doesn't restart. Test toggle restart. Test mobile viewport skips Step 1c and minimap highlights.
- [ ] T033 [PC] Create unit test `tests/unit/tutorial.test.js` — test state machine: step transitions, conditional skip logic (Step 4), returning user detection, localStorage persistence, `prefers-reduced-motion` handling.

**Checkpoint**: Tutorial completes end-to-end on desktop and mobile. All 8 steps work. Dismiss and restart work. Existing tests still pass.

---

## Phase 5: Engagement Features (Phase D)

**Purpose**: Add milestone celebrations, expertise button highlight, progress display, and video recommendations. Independent of tutorial (runs outside tutorial mode).

- [ ] T034 [P] [PD] Implement milestone toasts in `src/ui/milestones.js` — export `checkMilestone(questionCount)`. At 10/25/50 questions, show toast sliding in from bottom-right (3s display, M3 standard easing enter, emphasized-accelerate exit). At 10 questions, include CSS-only confetti burst (~12 colored elements, `@keyframes` burst + fade, 1s). Track shown state in localStorage to fire once per session.
- [ ] T035 [P] [PD] Implement expertise button highlight in `src/ui/milestones.js` or `src/app.js` — after 15+ questions answered (outside tutorial mode), add one-time pulsing animation to "My Areas of Expertise" button. Same highlight ring style as tutorial (2px accent border, soft glow, 1.5s pulse). Auto-stop after 6s or on user interaction. Track in localStorage.
- [ ] T036 [P] [PD] Add running progress display to quiz panel in `src/ui/quiz.js` — question count "Q12" in panel header. Streak indicator "3 in a row!" for consecutive correct answers (show inline, dismiss after next question).
- [ ] T037 [PD] Add proactive video recommendation in `src/ui/quiz.js` or `src/app.js` — after 3+ incorrect answers in a domain, show subtle suggestion between questions: "Want to learn more about [domain]? We have video recommendations." Link opens video panel. Don't interrupt quiz flow.
- [ ] T038 [PD] Wire milestones into `src/app.js` — call `checkMilestone()` after each question answered. Ensure milestones don't fire during tutorial mode (tutorial has its own pacing).

**Checkpoint**: Answer 10 questions → see milestone toast + confetti. Answer 15 → see expertise button pulse. Get 3 wrong in a domain → see video suggestion.

---

## Phase 6: Persona Re-Testing (Phase E)

**Purpose**: Augment persona framework and re-run all 18 personas to validate 90%+ pass rate.

### Framework Augmentation

- [ ] T039 [PE] Add `tutorialEnabled` flag to persona definitions in `tests/visual/personas/definitions.js` — default `true` for all personas. Add localStorage injection in `tests/visual/personas/runner.js` to set `mapper-tutorial` state before navigation: `{ completed: true, dismissed: true }` when `tutorialEnabled: false` (disables tutorial for non-tutorial test runs).
- [ ] T040 [PE] Add tutorial evaluation dimensions to `tests/visual/personas/evaluator-prompts.js` — extend `buildRegularEvalPrompt()` to include `tutorialClarity` (1-5), `tutorialPacing` (1-5), `tutorialCompleteness` (1-5) when tutorial was active for that persona's session.

### Re-Run Validation

- [ ] T041 [PE] Re-run Phase 1 Playwright tests for all 18 personas: `npx playwright test tests/visual/persona-agents.spec.js` — verify all 24 tests pass with fresh checkpoints
- [ ] T042 [PE] Run Phase 2 AI evaluations for all 18 personas using `node scripts/run_persona_phase2.mjs --all` — spawn evaluation agents, compile reports
- [ ] T043 [PE] Compile aggregate report and verify SC-001: pass rate >= 90%. If < 90%, identify failing personas and iterate on specific issues before declaring complete.

**Checkpoint**: Aggregate report shows 90%+ pass rate. All persona reports in `tests/visual/reports/`.

---

## Phase 7: Polish & Verification

**Purpose**: Final verification, cleanup, and commit

- [ ] T044 Run full test suite: `npm test && npx playwright test` — verify zero regressions (SC-006)
- [ ] T045 Verify SC-002: start dev server, answer 20+ questions across multiple domains — confirm zero broken questions served
- [ ] T046 Verify SC-003: time a fresh tutorial run end-to-end — must complete in under 4 minutes
- [ ] T047 Verify SC-004: check tutorial animations on desktop (60fps) and mobile emulation (30fps+) using DevTools Performance tab
- [ ] T048 [P] Update session notes in `notes/` with final status, pass rate, and any remaining issues
- [ ] T049 Commit all changes with descriptive message, push to remote

**Checkpoint**: All success criteria met. Branch ready for PR.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Data Fixes)**: Depends on Phase 1 — data-only changes, no code
- **Phase 3 (UX Fixes)**: Depends on Phase 1 — can run in parallel with Phase 2
- **Phase 4 (Tutorial)**: Depends on Phase 3 T011 (question validation guard) to ensure tutorial doesn't hit broken questions
- **Phase 5 (Engagement)**: Depends on Phase 1 — independent of Phases 2-4, can run in parallel
- **Phase 6 (Re-Testing)**: Depends on ALL of Phases 2-5 being complete
- **Phase 7 (Polish)**: Depends on Phase 6

### Parallel Opportunities

```
Phase 1 (Setup)
    ├── Phase 2 (Data Fixes) ──────────────────┐
    ├── Phase 3 (UX Fixes) ────────┐           │
    │                               ├── Phase 4 (Tutorial) ──┐
    └── Phase 5 (Engagement) ──────────────────────────────── ├── Phase 6 (Re-Test) → Phase 7
```

Within phases:
- T004-T007 (broken questions) can all run in parallel
- T011-T013 (UX fixes) can all run in parallel
- T026-T028 (SVG animations) can all run in parallel
- T034-T036 (engagement features) can all run in parallel

### Within Tutorial Phase (Phase 4)

- Infrastructure (T015-T017) must complete before Steps (T018-T025)
- Animations (T026-T028) can run in parallel with infrastructure
- CSS (T029) can run in parallel with animations
- Integration (T030-T031) depends on infrastructure + steps
- Tests (T032-T033) depend on full implementation

---

## Implementation Strategy

### MVP First (Phases 1-3 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Data Fixes (fix broken questions)
3. Complete Phase 3: UX Fixes (validation guard, domainMappedPct)
4. **STOP and VALIDATE**: Re-run 3 quick personas (P01, P02, P08) to verify data fixes work
5. This alone should raise pass rate from 56% to ~70%

### Full Delivery

1. MVP above
2. Phase 4: Tutorial Mode (the big feature)
3. Phase 5: Engagement Features (milestones, progress, video recs)
4. Phase 6: Full persona re-test (target 90%+)
5. Phase 7: Final polish and PR

---

## Notes

- [P] tasks = different files, no dependencies
- [Phase] label maps task to spec phase for traceability
- Phases 2+3 are quick wins (data edits + small code guards)
- Phase 4 is the bulk of the work (~18 tasks)
- Phase 5 is independent and can be deferred if needed
- Commit after each phase for safe checkpoints
