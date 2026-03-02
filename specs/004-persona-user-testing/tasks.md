# Tasks: Persona-Based User Testing Framework

**Input**: Design documents from `/specs/004-persona-user-testing/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are integrated into the persona framework itself — each persona simulation IS a test. No separate test tasks needed.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure, persona definitions, and skill file

- [X] T001 Create directory structure: `tests/visual/personas/`, `tests/visual/.working/personas/`, `tests/visual/reports/`, `tests/visual/screenshots/personas/`, `tests/fixtures/expected-outcomes/`
- [X] T002 Add gitignore entries for generated output: `tests/visual/.working/`, `tests/visual/reports/`, `tests/visual/screenshots/personas/` in project `.gitignore`
- [X] T003 [P] Create all 21 persona definitions in `tests/visual/personas/definitions.js` — export array of persona objects with fields: id, name, category, device ({name, width, height}), browser, domain, numQuestions, aiModel, personality (system prompt string), expertiseDomains, weakDomains, getAccuracy(domainId) function, checkpointInterval
- [X] T004 [P] Create JSON mirror of persona definitions in `tests/fixtures/personas.json` — same data minus functions (getAccuracy replaced with accuracy profiles object: `{domainId: probability}`)
- [X] T005 [P] Create the Claude Code skill file at `.claude/skills/simulate-persona/SKILL.md` — define the 4-phase orchestration pipeline (Playwright automation → AI evaluation → Pedant web verification → Report assembly), TodoWrite tracking, working file conventions, resume-from-checkpoint logic. Include Phase 5: Issue Triage & Fix workflow — for each blocker/major issue discovered, create a GitHub issue, spawn a Task agent to implement the fix on the feature branch, verify with re-run, and submit as PR

**Checkpoint**: Directory structure exists, personas defined, skill registered

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core framework modules that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Implement Playwright runner engine in `tests/visual/personas/runner.js` — export functions: `runPersonaSession(page, persona, questionDb)` that automates question answering per persona profile, `captureCheckpoint(page, persona, checkpointNum)` that captures screenshot + DOM state + console errors, `selectDomain(page, domainName)` to pick domain from dropdown, `answerQuestion(page, persona, questionData)` with domain-based accuracy using persona's getAccuracy. Reuse patterns from existing `tests/visual/persona-simulation.spec.js` (questionDb Map, lookupQuestion fuzzy matcher, advanceToNext via keyboard 'n')
- [X] T007 [P] Implement evaluator prompt templates in `tests/visual/personas/evaluator-prompts.js` — export functions: `buildRegularEvalPrompt(persona, checkpointData, previousEvals)` that constructs the system+user prompt for Sonnet checkpoint evaluation, `buildPedantEvalPrompt(persona, questionData, checkpointData)` for Opus per-question evaluation, `buildPedantVerificationPrompt(question, agentAssessment)` for web-search verification prompt. Each prompt must instruct the agent to write JSON output matching the AgentEvaluation schema from data-model.md
- [X] T008 [P] Implement report compiler in `tests/visual/personas/report-compiler.js` — export functions: `compileReport(personaId, workingDir)` that reads all checkpoint and evaluation JSON files from `.working/personas/`, assembles a PersonaReport object per data-model.md schema, determines PASS/FAIL/AMBIGUOUS per criteria in spec.md, writes `{personaId}-report.json` and `{personaId}-report.md` to `tests/visual/reports/`
- [X] T009 Build question database loader utility in `tests/visual/personas/question-loader.js` — export `loadQuestionDb()` that reads `data/domains/index.json` + per-domain JSONs and returns a Map<questionId, questionObj> (reuse pattern from existing persona-simulation.spec.js lines 12-35). Also export `getQuestionsForDomain(domainId)` returning array of questions for a specific domain

**Checkpoint**: Foundation ready — framework can automate sessions, generate prompts, compile reports, and load questions

---

## Phase 3: User Story 1 — Reporter Quick Demo (Priority: P1) MVP

**Goal**: Simulate 3 reporter personas (P01 Alex, P02 Maya, P03 Raj) doing quick explorations. AI agents evaluate first impressions, question quality, and visual impact. All must produce positive experience summaries.

**Independent Test**: Run `/simulate-persona P01` and verify the report shows PASS with a positive experience narrative.

### Implementation for User Story 1

- [X] T010 [P] [US1] Write Playwright test entry for reporter personas in `tests/visual/persona-agents.spec.js` — define test cases for P01, P02, P03 that: start dev server, navigate to app, select domain, answer N questions per persona profile using runner.js, capture checkpoints at intervals (every 5 answers), write checkpoint JSON to `.working/personas/`. Use Playwright test.describe for grouping, `test.skip` for non-matching browser projects
- [X] T011 [P] [US1] Define expected outcomes for reporter personas in `tests/fixtures/expected-outcomes/reporters.json` — for each reporter (P01, P02, P03): expected map characteristics at each checkpoint (e.g., "after 5 correct physics answers, expect green region near physics cluster"), minimum engagement level (4/5), expected sentiment ("positive"), maximum acceptable issue severity ("minor")
- [X] T012 [US1] Add reporter persona evaluation logic to skill file `.claude/skills/simulate-persona/SKILL.md` — in Phase 2 section, document how to spawn Sonnet Task agent with reporter personality prompt, checkpoint data, and screenshot paths. Agent must evaluate: visual impact for press coverage, question quality for non-expert audience, whether demo feels polished enough for tech publication

**Checkpoint**: Reporter personas can be simulated end-to-end with AI evaluation and PASS/FAIL reports

---

## Phase 4: User Story 2 — Expert Scientist Deep Evaluation (Priority: P1)

**Goal**: Simulate 4 expert personas (P04-P07) answering 30-50 questions with genuine domain expertise. AI agents verify the map accurately reflects expertise patterns and evaluate question quality with real domain knowledge.

**Independent Test**: Run `/simulate-persona P04` and verify the report shows strong knowledge region (green) in neuroscience with clear differentiation from weak areas.

### Implementation for User Story 2

- [X] T013 [P] [US2] Add expert persona test cases to `tests/visual/persona-agents.spec.js` — P04 (neuroscience, 35q, Chrome desktop), P05 (physics, 40q, Safari desktop), P06 (biology, 30q, mobile Chrome), P07 (all, 50q, Firefox desktop). Each uses expert accuracy profiles (90%+ in specialty, 30-50% elsewhere). Checkpoint every 5 answers
- [X] T014 [P] [US2] Define expected outcomes for expert personas in `tests/fixtures/expected-outcomes/experts.json` — for each expert: specialty region coordinates on map, expected green region bounds, expected red/yellow region bounds, acceptable domain-mapped % range at completion, maximum question-quality flags (10% threshold)
- [X] T015 [US2] Add expert-specific evaluation guidance to skill file `.claude/skills/simulate-persona/SKILL.md` — document how expert persona agents should use real domain knowledge to: verify answer correctness, assess question difficulty calibration, compare map color distribution to their known expertise profile, flag questions that test trivia vs understanding

**Checkpoint**: Expert personas produce accurate question audits and map-accuracy assessments

---

## Phase 5: User Story 9 — Pedantic Content Audit (Priority: P1)

**Goal**: Simulate 3 pedant personas (P19-P21) auditing EVERY question in physics, biology, and "all" domains. Opus agents verify answer correctness via web search, rate every question on 4 dimensions, and track map changes per-answer.

**Independent Test**: Run `/simulate-persona P19` and verify the report includes a complete question-by-question audit with web-verified corrections for any flagged answers.

### Implementation for User Story 9

- [X] T016 [P] [US9] Write Playwright test entry for pedant personas in `tests/visual/persona-pedant.spec.js` — define test cases for P19, P20, P21 that answer ALL questions in their domain. Checkpoint after EVERY answer (checkpointInterval=1). Capture screenshot after each answer. Write per-question data (question text, all options, marked answer, selected answer, screenshot path) to `.working/personas/{personaId}-checkpoint-{N}.json`
- [X] T017 [P] [US9] Add pedant-specific prompt for per-question web verification in `tests/visual/personas/evaluator-prompts.js` — add `buildPedantQuestionAuditPrompt(persona, question, screenshotPath)` that instructs Opus agent to: (1) assess the marked answer using domain knowledge, (2) if disagreement, use WebSearch to verify, (3) cite source URL, (4) rate question on accuracy/clarity/difficulty/educational-value (1-5 each), (5) assess map change appropriateness
- [X] T018 [US9] Add pedant orchestration to skill file `.claude/skills/simulate-persona/SKILL.md` — document Phase 3 (Pedant Web Verification): for each question flagged by the Opus agent, spawn a follow-up Task agent with WebSearch tool to verify the correction. Write verified corrections to `.working/personas/{personaId}-corrections.json` with schema: `{questionId, currentAnswer, correctedAnswer, verdict, sourceUrl, evidence}`
- [X] T019 [US9] Implement correction applicator utility in `tests/visual/personas/correction-applicator.js` — export `applyVerifiedCorrections(correctionsPath, domainJsonPath)` that reads the corrections JSON, filters to CORRECTION_VERIFIED verdicts only, updates the domain's question JSON file with corrected answers, and writes a changelog to `tests/visual/reports/{personaId}-corrections-applied.md`

**Checkpoint**: Pedant personas produce complete question audits with web-verified corrections that can be applied to question banks

---

## Phase 6: User Story 3 — Scientist Exploring Unfamiliar Domain (Priority: P2)

**Goal**: Simulate an expert (physicist) exploring biology — mostly wrong answers. Verify map shows predominantly red/yellow without artifacts or estimator collapse.

**Independent Test**: Run a physics-expert persona on biology domain, verify heatmap shows red/yellow and estimator remains stable.

### Implementation for User Story 3

- [X] T020 [US3] Add unfamiliar-domain test variant to `tests/visual/persona-agents.spec.js` — create a test case using P05 (physicist) but overriding domain to "biology" with 20% accuracy. Checkpoint every 5 answers. Verify no console errors, no estimator collapse, map shows predominantly red/yellow

**Checkpoint**: Low-knowledge simulations complete gracefully without estimator artifacts

---

## Phase 7: User Story 4 — Genuine Learner Self-Discovery (Priority: P2)

**Goal**: Simulate 4 learner personas (P08-P11) answering 25-45 mixed-knowledge questions. AI agents track emotional arc, flag stale periods, evaluate question diversity, and identify "aha moments."

**Independent Test**: Run `/simulate-persona P08` and verify the report shows at least one "aha moment" and a positive engagement arc.

### Implementation for User Story 4

- [X] T021 [P] [US4] Add learner persona test cases to `tests/visual/persona-agents.spec.js` — P08 (all, 45q, mixed 50%), P09 (all, 40q, CS-strong/bio-weak 80/30% split), P10 (neuroscience, 35q, iPad, explores videos), P11 (mathematics, 25q, tired/noisy). Checkpoint every 5 answers
- [X] T022 [P] [US4] Define expected outcomes for learner personas in `tests/fixtures/expected-outcomes/learners.json` — expected regional differentiation on map, minimum 1 "aha moment" per persona, no sustained boredom (5+ consecutive questions), question diversity target (<30% same sub-topic within domain)
- [X] T023 [US4] Add learner-specific evaluation guidance to skill file — document how learner agents should track: emotional arc (excitement → curiosity → insight), question diversity within domains, map readability for non-experts, "would I show this to a friend?" assessment

**Checkpoint**: Learner personas produce engagement narratives with aha moments and question diversity assessments

---

## Phase 8: User Story 5 — Mobile Reporter Quick Glance (Priority: P2)

**Goal**: Verify mobile UX for reporter P02 (iPhone 390px) and expert P06 (Pixel 393px). Touch-friendly, no overflow, no clipping.

**Independent Test**: Mobile persona screenshots show complete UI within viewport bounds with no overflow.

### Implementation for User Story 5

- [X] T024 [US5] Add mobile-specific checkpoint assertions to `tests/visual/persona-agents.spec.js` — for P02 and P06 test cases, add after-checkpoint validation: verify no horizontal scrollbar (`document.documentElement.scrollWidth <= window.innerWidth`), quiz options have minimum 44px touch target height, no text clipping. Capture full-page screenshot for mobile-specific evaluation

**Checkpoint**: Mobile personas confirm touch-friendly UI with no layout issues

---

## Phase 9: User Story 6 — Cross-Browser Consistency (Priority: P3)

**Goal**: Run identical persona simulation on Chrome, Firefox, and Safari. Compare screenshots for visual equivalence.

**Independent Test**: Same persona answers produce visually equivalent maps across all 3 browsers — sampled colors differ by ≤10%.

### Implementation for User Story 6

- [X] T025 [US6] Add cross-browser comparison test in `tests/visual/persona-agents.spec.js` — create a dedicated test that runs P01 (reporter, 7 questions) on all three browser projects with identical answer sequence (seed deterministic answers, not probabilistic). After completion, save screenshots as `P01-cross-{browser}.png`. The AI evaluation agent compares the three screenshots and reports consistency
- [X] T026 [US6] Add cross-browser comparison prompt to `tests/visual/personas/evaluator-prompts.js` — export `buildCrossBrowserComparisonPrompt(screenshotPaths)` that instructs the agent to compare 3 screenshots and report: color distribution similarity, layout consistency, any browser-specific rendering artifacts

**Checkpoint**: Cross-browser screenshots show equivalent maps with ≤10% color variance

---

## Phase 10: User Story 7 — Power User Session (Priority: P3)

**Goal**: Simulate 3 stress-test personas (P12 marathoner 125q, P13 domain-hopper 60q, P14 speed-clicker 50q). Verify estimator stability, no collapse at 115-120 questions, smooth domain switching.

**Independent Test**: P12 completes 125 questions with no Cholesky errors and domain-mapped % never jumps >15 points.

### Implementation for User Story 7

- [X] T027 [P] [US7] Add power user test cases to `tests/visual/persona-agents.spec.js` — P12 (physics, 125q, checkpoint every 20), P13 (multiple domains, 60q, switches domain every 15 answers), P14 (biology, 50q, 1-2 second delays). Monitor console for Cholesky/NaN/divide-by-zero errors at every checkpoint
- [X] T028 [P] [US7] Define expected outcomes for power users in `tests/fixtures/expected-outcomes/power-users.json` — P12: domain-mapped% smooth progression (max 15pt jump), no console errors at 115-120 range. P13: clean domain switching (no state leakage). P14: stable under rapid input
- [X] T029 [US7] If P12 triggers estimator instability: investigate and fix `src/learning/estimator.js` — add jitter to kernel matrix diagonal before Cholesky decomposition (research.md R7), consider observation pruning beyond 100 observations, add condition number monitoring. Verify fix with re-run of P12 simulation

**Checkpoint**: Power user personas complete without estimator collapse or console errors

---

## Phase 11: User Story 8 — Video Discovery Journey (Priority: P3)

**Goal**: Simulate learner P10 (35q on neuroscience, iPad) opening video panel, browsing recommendations, simulating video watch, and verifying map update.

**Independent Test**: P10 answers 35 questions, opens video panel, recommendations appear, video trajectory highlights on hover.

### Implementation for User Story 8

- [X] T030 [US8] Add video discovery test case to `tests/visual/persona-agents.spec.js` — after P10 completes 35 questions: open video panel (click toggle), verify recommendations appear (wait for video list items), hover a video to see trajectory highlight on map, simulate video watch (trigger completion callback), capture screenshot showing map update. Write video-specific checkpoint data

**Checkpoint**: Video panel integration works end-to-end with persona simulation

---

## Phase 12: Edge Case Personas (Priority: P3)

**Goal**: Simulate 4 edge-case personas (P15-P18) testing import/export, window resize, keyboard shortcuts, and share modal.

**Independent Test**: Each edge-case persona exercises its specific feature and the AI agent evaluates correctness.

### Implementation for Edge Case Personas

- [X] T031 [P] [US6] Add P15 (import/export) edge-case test to `tests/visual/persona-agents.spec.js` — answer 20 physics questions, export progress JSON via share modal, navigate to landing page, import from file input, verify all 20 answers restored on map (count answered-question markers in screenshot)
- [X] T032 [P] [US6] Add P16 (window resize) edge-case test to `tests/visual/persona-agents.spec.js` — answer 15 mathematics questions at 1920px, resize browser to 800px, capture screenshot, verify canvas layers (heatmap, articles, grid) remain aligned after resize
- [X] T033 [P] [US6] Add P17 (keyboard shortcuts) edge-case test to `tests/visual/persona-agents.spec.js` — answer 20 biology questions using A/B/C/D keys, then press Cmd+C, Ctrl+A, and other modifier combos, verify no accidental answer selection triggered by modifier keys
- [X] T034 [P] [US6] Add P18 (share modal) edge-case test to `tests/visual/persona-agents.spec.js` — answer 25 physics questions, open share modal, verify social media buttons have correct URLs, copy text button copies to clipboard, copy image button copies map screenshot

**Checkpoint**: Edge-case personas verify niche functionality without regressions

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, report aggregation, and cleanup

- [X] T035 Create aggregate report generator in `tests/visual/personas/report-compiler.js` — add `compileAggregateReport(reportsDir)` that reads all individual `{personaId}-report.json` files, produces a summary table (persona, result, issues count by severity, question flags count), calculates overall pass rate (SC-010 target: 90%+), writes `tests/visual/reports/aggregate-report.md`
- [X] T036 [P] Add `.working/` cleanup utility to `tests/visual/personas/runner.js` — export `cleanWorkingFiles(personaId)` that removes stale checkpoint/eval files for a persona before starting a fresh simulation (prevents resume from stale data)
- [X] T037 [P] Update `tests/visual/persona-simulation.spec.js` (existing file) — add comment header noting it is superseded by the new framework in `persona-agents.spec.js` and `persona-pedant.spec.js` for AI-driven evaluation. Keep it functional as a fast mechanical smoke test
- [X] T038 Run all Playwright tests (`npx playwright test`) to verify no regressions from framework additions — existing 179+ tests must still pass
- [X] T039 Run unit tests (`npx vitest run`) to verify no regressions — existing 82 tests must still pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 Reporter (Phase 3)**: Depends on Foundational — MVP target
- **US2 Expert (Phase 4)**: Depends on Foundational — can run parallel to US1
- **US9 Pedant (Phase 5)**: Depends on Foundational — can run parallel to US1/US2
- **US3 Unfamiliar (Phase 6)**: Depends on Foundational — lightweight, can run parallel
- **US4 Learner (Phase 7)**: Depends on Foundational — can run parallel
- **US5 Mobile (Phase 8)**: Depends on US1 (P02 test case exists there)
- **US6 Cross-Browser (Phase 9)**: Depends on US1 (uses P01 as baseline)
- **US7 Power User (Phase 10)**: Depends on Foundational — may need estimator fix (T029)
- **US8 Video (Phase 11)**: Depends on Foundational + US4 (P10 defined there)
- **Edge Cases (Phase 12)**: Depends on Foundational
- **Polish (Phase 13)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational
- **US2 (P1)**: Independent after Foundational
- **US9 (P1)**: Independent after Foundational
- **US3 (P2)**: Independent (reuses expert profiles with different domain)
- **US4 (P2)**: Independent after Foundational
- **US5 (P2)**: Depends on US1 (mobile persona tests added to same spec file)
- **US6 (P3)**: Depends on US1 (cross-browser comparison uses P01)
- **US7 (P3)**: Independent, but T029 (estimator fix) blocks PASS result
- **US8 (P3)**: Depends on US4 (P10 persona)
- **Edge Cases**: Independent after Foundational

### Within Each User Story

- Playwright test entry before expected outcomes definitions
- Expected outcomes before evaluation guidance in skill file
- All implementation before running simulations

### Parallel Opportunities

- T003, T004, T005 can run in parallel (different files, no dependencies)
- T007, T008 can run in parallel (different files)
- T010, T011 can run in parallel within US1
- T013, T014 can run in parallel within US2
- T016, T017 can run in parallel within US9
- T021, T022 can run in parallel within US4
- T027, T028 can run in parallel within US7
- T031 sub-tasks (different personas) can run in parallel
- T035, T036, T037 can run in parallel in Polish
- T031, T032, T033, T034 can run in parallel (different edge-case personas)

---

## Parallel Example: P1 User Stories

```bash
# After Phase 2 (Foundational) completes, launch all P1 stories in parallel:

# US1: Reporter Quick Demo
Task: "Write reporter Playwright tests in tests/visual/persona-agents.spec.js"
Task: "Define reporter expected outcomes in tests/fixtures/expected-outcomes/reporters.json"

# US2: Expert Scientist (parallel with US1)
Task: "Write expert Playwright tests in tests/visual/persona-agents.spec.js"
Task: "Define expert expected outcomes in tests/fixtures/expected-outcomes/experts.json"

# US9: Pedantic Content Audit (parallel with US1 and US2)
Task: "Write pedant Playwright tests in tests/visual/persona-pedant.spec.js"
Task: "Add pedant verification prompts in tests/visual/personas/evaluator-prompts.js"
```

---

## Implementation Strategy

### MVP First (US1: Reporter Quick Demo)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T009) — CRITICAL
3. Complete Phase 3: US1 Reporter (T010-T012)
4. **STOP and VALIDATE**: Run `/simulate-persona P01` end-to-end
5. Verify PASS result with positive experience narrative

### Incremental Delivery

1. Setup + Foundational → Framework ready
2. US1 Reporter → Test P01 → First PASS report (MVP!)
3. US2 Expert → Test P04 → Expert accuracy verified
4. US9 Pedant → Test P19 → Question quality audit complete
5. US3-US8 → Remaining personas → Comprehensive coverage
6. Polish → Aggregate report → 90%+ pass rate

### Execution Estimate

- **Phase 1-2** (Setup + Foundational): Framework scaffolding — write code
- **Phase 3-5** (P1 stories): MVP — write tests, run simulations, evaluate
- **Phase 6-12** (P2/P3 stories): Breadth — extend test cases, fix discovered bugs
- **Phase 13** (Polish): Aggregate — compile cross-persona report, verify regressions

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- The skill file (T005) is iteratively refined as new story requirements are added (T012, T015, T018, T023). T005 also covers the issue→fix→PR workflow for discovered bugs
- Estimator fix (T029) may be needed before US7 can PASS — research.md R7 documents the probable fix approach
- Correction applicator (T019) is used after pedant simulations to update question banks — changes go to feature branch only
- All framework code goes in `tests/` — no production source changes unless bugs are discovered during simulation
