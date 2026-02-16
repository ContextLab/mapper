# Tasks: Ready Demo for Public Release

**Input**: Design documents from `/specs/001-demo-public-release/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Branch**: `001-demo-public-release`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US6, INFRA, CONST)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization — Vite build system, dependency installation, project skeleton

- [x] T001 [INFRA] Initialize npm project: `package.json` with `name`, `version`, `scripts` (`dev`, `build`, `preview`, `test`, `bench`), `type: "module"`
- [x] T002 [INFRA] Install core dependencies: `deck.gl` 9+, `nanostores`, `@nanostores/persistent`
- [x] T003 [P] [INFRA] Install dev dependencies: `vite`, `vitest`, `@playwright/test`
- [x] T004 [INFRA] Create `vite.config.js`: `base: '/mapper/'`, `outDir: 'dist'`, input: `index.html`
- [x] T005 [P] [INFRA] Create empty module skeleton — all `src/` directories and files from plan.md Project Structure, each exporting stub functions matching their contract interfaces
- [x] T006 [P] [INFRA] Create `tests/algorithm/` and `tests/visual/` directory structure with empty spec files
- [x] T007 [INFRA] Replace `index.html` monolith with slim Vite shell: HTML structure only, `<script type="module" src="/src/app.js">`, CDN links for KaTeX + Font Awesome with integrity hashes, `<div id="map-container">`, `<div id="quiz-panel">`, `<div id="minimap-container">`
- [x] T008 [INFRA] Verify `npm run dev` starts Vite dev server and loads the slim `index.html` without errors
- [x] T009 [P] [INFRA] Create `data/domains/` directory with a placeholder `index.json` (empty domains array, `schema_version: "1.0.0"`) to unblock loader development

**Checkpoint**: `npm run dev` serves a blank page with no console errors. All `src/` modules exist as stubs.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core modules that ALL user stories depend on — state management, domain loading, knowledge estimator, renderer shell

**CRITICAL**: No user story work can begin until this phase is complete.

### State Management (src/state/)

- [ ] T010 [INFRA] Implement `src/state/store.js`: All atoms from contracts/state.md — `$responses` (persistentAtom), `$schemaVersion` (persistentAtom), `$activeDomain`, `$domainCache`, `$estimates`, `$transitionState`, `$questionMode`, `$answeredIds` (computed), `$coverage` (computed), `$insightsAvailable` (computed)
- [ ] T011 [INFRA] Implement `src/state/persistence.js`: `validateSchema()` with version check + discard-on-mismatch, `exportResponses()` returning Blob, `resetAll()` clearing all atoms, `isAvailable()` detecting localStorage support. Follow contracts/state.md exactly.

### Domain Data Loading (src/domain/)

- [ ] T012 [P] [INFRA] Implement `src/domain/registry.js`: Load `data/domains/index.json` at startup, expose `getDomains()`, `getDomain(id)`, `getChildren(parentId)`, `getHierarchy()` returning the 19-domain tree. Validate `domains.length === 19` in dev mode.
- [ ] T013 [P] [INFRA] Implement `src/domain/loader.js`: Lazy-load `data/domains/{id}.json` with `onProgress` / `onComplete` / `onError` callbacks per contracts/domain-data.md. Cache loaded bundles in `$domainCache`. Use `fetch()` with `Content-Length` header for progress calculation. Emit progress events at minimum every 100ms.
- [ ] T014 [INFRA] Implement `src/domain/questions.js`: `getAvailableQuestions(domainBundle, answeredIds)` returning unanswered questions, `getQuestionById(id)` lookup, domain-overlap logic for questions appearing in multiple domains.

### Knowledge Estimator (src/learning/)

- [ ] T015 [INFRA] Implement `src/learning/estimator.js`: Gaussian Process with Matern 3/2 kernel per contracts/active-learner.md — `init(gridSize, region)`, `observe(x, y, correct)` with Woodbury incremental update, `predict(viewport?)` returning CellEstimate[], `predictCell(gx, gy)`, `reset()`, `restore(responses)`. State derivation: unknown/uncertain/estimated per FR-017.
- [ ] T016 [INFRA] Implement `src/utils/math.js`: Matern 3/2 kernel function, Euclidean distance, matrix inversion utilities (Woodbury identity), sigmoid, linear interpolation, RBF kernel.

### Renderer Shell (src/viz/)

- [ ] T017 [INFRA] Implement `src/viz/renderer.js` shell: Initialize deck.gl DeckGL instance with MapView, `setPoints(points)` using ScatterplotLayer with transition config (`getPosition: { duration: 1000 }`), `setHeatmap(estimates, region)` using HeatmapLayer with color-blind safe palette (viridis), `setLabels(labels)` using TextLayer, `getViewport()`, `transitionTo(region, duration)`, `destroy()`. Wire `onViewportChange` callback on viewState changes.
- [ ] T018 [P] [INFRA] Implement `src/utils/accessibility.js`: Focus trap utility, ARIA live region announcer, keyboard navigation helpers (arrow keys for grid, Enter for selection, Escape for close), skip-to-content link setup.

### App Entry Point

- [ ] T019 [INFRA] Implement `src/app.js`: Initialize persistence (validateSchema), load domain registry, render domain selector, wire up state subscriptions ($activeDomain → load domain → render, $estimates → update heatmap, $responses → re-predict). Handle localStorage unavailable case (session-only mode with notice).

**Checkpoint**: Foundation ready — `npm run dev` shows domain selector (from index.json), selecting a domain triggers a fetch (404 expected until pipeline runs), state atoms work, estimator can be called from console.

---

## Phase 3: User Story 1 — First Visit: Explore a Knowledge Domain (Priority: P1)

**Goal**: Visitor selects a domain, answers questions, watches heatmap fill in real time.

**Independent Test**: Load page → select domain → answer 5–10 questions → heatmap updates with each answer.

### Implementation for User Story 1

- [ ] T020 [US1] Implement `src/ui/controls.js` — Domain selector: Hierarchical dropdown/menu showing all 19 domains organized by parent→children. Selecting a domain sets `$activeDomain`, triggers loader, shows progress bar during fetch. Style responsive for mobile (full-width on <768px).
- [ ] T021 [US1] Implement `src/ui/progress.js` — Download progress bar (FR-012): Subscribes to loader progress events, shows percentage + bytes, auto-hides on complete. Also implements confidence indicator (FR-008): subscribes to `$coverage`, displays proportion of domain mapped as a visual bar.
- [ ] T022 [US1] Implement `src/ui/quiz.js` — Question display panel: Shows current question with LaTeX rendering (KaTeX), 4 answer buttons (A/B/C/D), handles answer submission (creates UserResponse, calls `estimator.observe()`, updates `$responses` and `$estimates`). Question transitions under 300ms. Keyboard navigable: Tab between options, Enter to select.
- [ ] T023 [US1] Implement `src/learning/sampler.js` — Active learning question selection per contracts/active-learner.md: `selectNext()` computing expected information gain over viewport cells (FR-016), viewport restriction, cell re-selection allowed (FR-019). Must complete in <50ms.
- [ ] T024 [US1] Implement `src/learning/curriculum.js` — Landmark→niche progression per FR-018: `getWeight(answeredCount, coveragePercent)` with sigmoid transition at ~30% coverage. `getCentrality(domainId)` returning precomputed centrality scores from article density in each cell. Weight modulates acquisition function in sampler.
- [ ] T025 [US1] Wire quiz flow end-to-end in `src/app.js`: On domain select → load bundle → init estimator → select first question via sampler → display in quiz panel → on answer → observe → re-predict → update heatmap → select next question → loop. Show "Domain fully mapped" message when 50 questions answered (edge case).
- [ ] T026 [US1] Implement introduction/landing state: Before first domain selection, show brief explanation of what the demo does (~200–300 words, plain language), link to preprint (https://psyarxiv.com/dh3q2), and domain selector prompting the visitor to choose a domain. No domain data loads until selection — initial payload is app code + domain registry (~5 KB) only. Landing content hidden after first domain select.

**Checkpoint**: A visitor can load the page, read the intro, select a domain, answer questions, and watch the heatmap update in real time. SC-001 (first question within 60s), SC-002 (heatmap update <500ms) should be achievable.

---

## Phase 4: User Story 2 — Navigate Between Domains (Priority: P2)

**Goal**: Smooth animated transitions when switching domains, cross-domain prediction persistence, navigation minimap.

**Independent Test**: Answer 5 questions in one domain → switch to related sub-domain → (a) smooth animation, (b) prior answers persist, (c) minimap updates, (d) no point teleportation.

### Implementation for User Story 2

- [ ] T027 [US2] Implement `src/viz/transitions.js` — 3D rotation logic: `needs3D(source, target)` using IoU < 0.3 threshold, `prepare3DPositions(points, targetPoints)` assigning PCA-3 z-coordinates. When 3D is needed, set deck.gl to OrbitView during transition, interpolate (x,y,z) → (x',y',z'), then return to MapView. When not needed, simple pan/zoom with per-point interpolation.
- [ ] T028 [US2] Implement fade-in/fade-out for entering/leaving points: Points not in target domain get opacity animated 1→0 over transition duration. Points new in target domain get opacity animated 0→1. Merge source + target point sets during transition, each tagged with fade direction.
- [ ] T029 [US2] Implement domain switch orchestration in `src/app.js`: On `$activeDomain` change → load new domain bundle (with progress bar) → compute merged point set → call `transitions.needs3D()` → execute transition → after animation completes, call `estimator.restore()` with ALL `$responses` (not just current domain's) to ensure cross-domain knowledge persistence → update heatmap. The GP kernel smoothly interpolates across embedding space, so answered questions in "Physics" produce non-zero estimates in related cells of "Quantum Physics." Handle rapid switching: cancel pending transitions, most recent selection wins (US2 acceptance scenario 4).
- [ ] T030 [US2] Implement `src/viz/minimap.js` — Navigation overview per FR-009: Canvas-based minimap showing full embedding space (0–1 both axes), all 19 domain regions as labeled rectangles, active domain highlighted, current viewport rectangle overlaid. Click on a domain region to switch. Subscribe to `$activeDomain` for highlight updates.

**Checkpoint**: Domain switching animates smoothly (SC-003: 60fps, <1s), prior answers persist across switches, minimap reflects active domain. SC-012 (no point jumps >5% viewport) should pass.

---

## Phase 5: User Story 3 — Smart Question Modes (Priority: P3)

**Goal**: Question mode menu with strategy-based selection: easy, hardest-can-answer, don't-know.

**Independent Test**: Answer 15+ questions → select each mode → verify selected question matches strategy.

### Implementation for User Story 3

- [ ] T032 [US3] Implement `src/ui/modes.js` — Question mode menu: Dropdown/panel with modes from FR-010 ("Ask me an easy question", "Ask me the hardest question I can answer", "Ask me something I don't know"). Selecting a mode sets `$questionMode` and triggers `sampler.selectByMode()`. Modes requiring coverage (>5 questions) disabled with tooltip when insufficient (FR-011).
- [ ] T033 [US3] Implement `selectByMode()` in `src/learning/sampler.js`: Mode strategies per contracts/active-learner.md — `easy`: lowest difficulty in highest-value cells, `hardest-can-answer`: highest difficulty where value > 0.6, `dont-know`: highest difficulty where value < 0.3. Falls back to `selectNext()` if no candidate matches mode criteria.

**Checkpoint**: All 3 question modes select appropriate questions. Disabled modes show explanatory tooltips. SC-010 (90% strategy match) should be achievable.

---

## Phase 6: User Story 4 — Knowledge Insights (Priority: P4)

**Goal**: Insight panels showing areas of expertise, weakness, and suggested learning topics.

**Independent Test**: Answer 20+ questions → view each insight panel → listed topics match answer pattern.

### Implementation for User Story 4

- [ ] T034 [US4] Implement `src/ui/insights.js` — Insight panels: "Areas of expertise" (top 5 highest-value cells with labels), "Areas of weakness" (5 lowest-value cells with evidence), "Suggested learning" (5 medium-value cells where learning effort would be most productive). Uses `$estimates` and GridLabel data. Shows "Answer more questions" message when `$insightsAvailable` is false (<10 responses).
- [ ] T035 [US4] Extend `src/ui/modes.js` to include insight modes from FR-010: "List my areas of expertise", "List my areas of weakness", "Suggest something to learn". These open the insights panel rather than selecting a question.

**Checkpoint**: Insight panels display meaningful results after 20+ questions. Topics match answer patterns.

---

## Phase 7: User Story 5 — Cross-Domain Predictions (Priority: P5)

**Goal**: Demonstrate that embeddings capture conceptual relationships — answering Math questions produces non-zero estimates in Probability & Statistics.

**Independent Test**: Answer 15+ questions in Mathematics → switch to Probability and Statistics (never visited) → map shows non-zero estimates in related regions.

### Implementation for User Story 5

- [ ] T036 [US5] Verify and tune GP kernel parameters in `src/learning/estimator.js`: Ensure the Matern 3/2 length-scale is calibrated so that questions answered in "Mathematics" produce visible (non-trivial) predictions in "Probability and Statistics" cells that are spatially close in embedding space. If predictions are too weak or too diffuse, adjust length-scale. Document the calibration values.
- [ ] T037 [US5] Add visual indicator for cross-domain predictions: Cells with predictions derived entirely from other domains (no direct evidence in current domain) should be visually distinguishable from cells with direct evidence — e.g., slightly different opacity or a dotted border pattern in the heatmap.

**Checkpoint**: SC-009 (non-zero cross-domain estimates in related regions) validated manually for Math→Probability and Neuroscience→Biology.

---

## Phase 8: User Story 6 — Self-Contained Documentation (Priority: P6)

**Goal**: About/documentation modal accessible from main interface.

**Independent Test**: Click "About" → documentation explains the approach, links work, citation present.

### Implementation for User Story 6

- [ ] T038 [US6] Implement About modal in `index.html` + `src/ui/controls.js`: "About" / "Learn More" button in header. Modal content: what the demo does, how embedding-based knowledge mapping works (plain language), link to preprint (https://psyarxiv.com/dh3q2), link to GitHub repo (https://github.com/ContextLab/efficient-learning-khan). Keyboard accessible (Escape to close, focus trap). Style matches overall design.
- [ ] T039 [US6] Implement Reset Progress (FR-021) in `src/ui/controls.js`: "Reset Progress" button, confirmation dialog ("Are you sure? This will clear all progress."), calls `persistence.resetAll()`, returns to initial landing state.
- [ ] T040 [US6] Implement Export (FR-022) in `src/ui/controls.js`: "Export Progress" button, calls `persistence.exportResponses()`, triggers download of JSON file with timestamp in filename.

**Checkpoint**: About modal, Reset, and Export all work. Links verified manually.

---

## Phase 9: Data Pipeline Extensions (Python)

**Purpose**: Generate the 19 domain definitions, ~750–800 questions, per-domain JSON bundles for lazy loading.

- [ ] T040b [P] [INFRA] Implement `scripts/compute_pca3.py`: Run PCA on the full embedding matrix (from `wikipedia.pkl` or merged embeddings), extract the 3rd principal component, normalize to [0, 1], and store as a `z` coordinate on every article and question. Output: `embeddings/pca3_coordinates.pkl` mapping article/question IDs to z-values. This is consumed by T041 and T043 to populate the `z` field required by contracts/domain-data.md for 3D transitions.
- [ ] T041 [P] [INFRA] Implement `scripts/define_domains.py`: Define 19 domain regions in embedding space using existing UMAP coordinates. For each domain, find the bounding rectangle of relevant articles and compute an appropriate `grid_size` based on region area (larger regions → finer grids). Output: `data/domains/index.json` per contracts/domain-data.md. Use existing `wikipedia_articles.json` and `heatmap_cell_labels.json` as input.
- [ ] T042 [P] [INFRA] Implement `scripts/generate_domain_questions.py`: Generate 50 questions per domain using OpenAI Batch API (gpt-5-nano). For sub-domains: unique questions. For general domains: mix of child questions + unique general questions. For "All": draw from all. Target ~750–800 unique questions total. Include difficulty levels 1–5 spread per domain (minimum 5 questions at each level per domain). Output: per-domain question lists with embedding coordinates, PCA-3 z-coordinate, source article, concepts tested. **Accuracy requirement (Constitution §I, SC-004)**: For every generated question, the script MUST perform a web search (Wikipedia API + search engine) to verify: (a) the source article exists and is current, (b) the correct answer is factually accurate per the article, (c) all distractor options are plausible but definitively incorrect. Questions failing verification MUST be regenerated or discarded — zero tolerance for inaccurate questions in the final output.
- [ ] T043 [INFRA] Implement `scripts/export_domain_data.py`: Read domain definitions + questions + articles + labels → produce `data/domains/{id}.json` per contracts/domain-data.md for all 19 domains. Validate invariants: 50 questions per domain, coordinates within region, grid labels cover full grid, PCA-3 z-coordinate present on all points.
- [ ] T044 [INFRA] Run full domain pipeline: `define_domains.py` → `generate_domain_questions.py` → `export_domain_data.py`. Verify all 19 domain bundles are valid. T042's inline verification covers 100% of questions automatically.
- [ ] T044b [INFRA] Implement `scripts/validate_article_existence.py`: For every unique `source_article` referenced across all ~750–800 questions, query the Wikipedia REST API (`https://en.wikipedia.org/api/rest_v1/page/summary/{title}`) and confirm a 200 response. Log any missing or redirected articles. Script MUST achieve 100% existence confirmation — any failures block deployment. Run as part of pipeline after T042 and before T043.

**Checkpoint**: `data/domains/index.json` + 19 `{id}.json` bundles exist, all valid per contracts. 100% of questions verified for factual accuracy during generation (T042). 100% of source articles confirmed to exist on Wikipedia (T044b).

---

## Phase 10: Responsive Layout & Touch (Cross-Cutting)

**Purpose**: Mobile/tablet layout and touch interaction support.

- [ ] T045 [P] [INFRA] Implement responsive CSS: Mobile-first layout with breakpoints at 480px (phone), 768px (tablet), 1280px+ (desktop). On mobile: stacked layout (map on top, quiz panel below), full-width domain selector, larger touch targets (min 44px). On tablet: side-by-side with collapsible quiz panel. On desktop: current side-by-side layout. Minimap repositions to bottom-right on mobile.
- [ ] T046 [P] [INFRA] Implement touch event handling in `src/viz/renderer.js`: deck.gl handles touch pan/zoom natively. Add touch-friendly answer selection in quiz panel (larger buttons, prevent double-tap zoom on answer buttons). Test pinch-to-zoom on heatmap.
- [ ] T047 [INFRA] Add CDN fallback handling: KaTeX and Font Awesome loaded via CDN with integrity hashes. If CDN fails (onerror handler), fall back to plain text for LaTeX and text labels for icons. Show non-blocking degradation notice.

**Checkpoint**: Usable on 320px phone viewport, 768px tablet, and 1280px desktop. Touch controls work for pan, zoom, answer selection. SC-008 validated.

---

## Phase 11: Accessibility (FR-023 / WCAG 2.1 AA)

**Purpose**: Keyboard navigation, screen reader support, color contrast, color-blind safety.

- [ ] T048 [P] [INFRA] Keyboard navigation: All interactive controls (domain menu, answer buttons, mode menu, reset, export, about, minimap) keyboard-navigable. Visible focus indicators (2px solid outline). Tab order follows logical reading order. Escape closes modals/menus.
- [ ] T049 [P] [INFRA] Screen reader support: ARIA labels on all interactive elements. ARIA live region for quiz question changes and heatmap updates ("You answered correctly. Knowledge map updated. 15% of domain mapped."). Alt text for heatmap visualization describing knowledge distribution pattern.
- [ ] T050 [P] [INFRA] Color contrast verification: All text meets 4.5:1 contrast ratio. All graphical elements meet 3:1. Heatmap palette (viridis/cividis) distinguishable with deuteranopia and protanopia. Test with simulated color blindness filter.

**Checkpoint**: All interactive controls keyboard-navigable. WCAG AA contrast ratios met. SC-013 prerequisites in place.

---

## Phase 12: Constitution Compliance Validation

**Purpose**: Verify compliance with all 3 Constitution principles before polish.

### Principle I: Accuracy

- [ ] T051 Verify question accuracy (SC-004, Constitution §I): Run `scripts/validate_question_accuracy.py` — an independent verification script (separate from T042's inline checks) that re-verifies 100% of questions against primary sources via web search. For each question: fetch the Wikipedia source article, confirm the correct answer is supported by article content, confirm distractors are incorrect. Output a verification report with pass/fail per question. **100% pass rate required** — any failures must be fixed before deployment.
- [ ] T052 Run pipeline diagnostics: `scripts/diagnostics/diagnose_pipeline.py` and `scripts/diagnostics/verify_cell_labels.py` on generated domain data. All checks pass.
- [ ] T053 Validate active learning benchmark (SC-011): Run `npx vitest bench` — GP+EIG achieves lower MAE than random baseline over 50-question simulated sessions across all 19 domains. Document results table.
- [ ] T054 Confirm no mock objects in any test file. Grep for `mock`, `jest.fn`, `vi.fn`, `stub` across `tests/` — zero results (excluding this documentation).
- [ ] T054b Validate SC-005 (zero server calls after load): Playwright test that intercepts all network requests, completes initial page load, then performs a full quiz flow (select domain, answer 5 questions, switch domain, answer 3 more, view insights). Assert zero non-cached network requests after initial static asset loading. Any XHR/fetch/WebSocket calls = failure.
- [ ] T054c Validate SC-010 (smart modes match strategy >=90%): Vitest test that creates synthetic estimate states (high-knowledge region, low-knowledge region, mixed), runs each mode selection (`easy`, `hardest-can-answer`, `dont-know`) 100 times with randomized question pools, and asserts >=90% of selections match the documented strategy (easy → lowest difficulty in highest-value cells, etc.).

### Principle II: User Delight

- [ ] T055 Playwright screenshot capture: `tests/visual/quiz-flow.spec.js` — capture map view, quiz active, results panel, about modal. Store as baseline in `tests/visual/screenshots/`.
- [ ] T056 Playwright animation smoothness: `tests/visual/transitions.spec.js` — frame-by-frame capture during domain transition, verify no point jumps >5% viewport dimension (SC-012).
- [ ] T057 Verify KaTeX rendering: Playwright test loading each domain, checking no raw `$` symbols visible, no broken equations. Cover >=5 LaTeX-containing questions per domain.
- [ ] T058 Performance check: Verify heatmap update <500ms (SC-002), domain transition <1s at 60fps (SC-003), first question within 60s of page load (SC-001). Use Playwright with `performance.now()` instrumentation.

### Principle III: Compatibility

- [ ] T059 Cross-browser test: `tests/visual/responsive.spec.js` — run full quiz flow (select domain, answer 3 questions, switch domain) in Playwright across Chromium, Firefox, WebKit. No rendering differences. SC-007 validated.
- [ ] T060 Mobile/tablet viewport test: Playwright viewport emulation at 375×667 (iPhone SE), 768×1024 (iPad), 1280×800 (laptop). All breakpoints usable. SC-008 validated.
- [ ] T061 Accessibility audit: `tests/visual/accessibility.spec.js` — Run Lighthouse accessibility audit via Playwright on all primary flows (domain selection, question answering, mode switching, reset/export). Zero critical violations. SC-013 validated.
- [ ] T062 Touch interaction test: Playwright touch emulation — verify pinch-zoom on map, tap on answer buttons, swipe on domain selector (if applicable). FR-014 validated.

**Checkpoint**: All Constitution principles validated. All SC-* success criteria pass or have documented exceptions.

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements, edge cases, deployment.

- [ ] T063 [P] Edge case: localStorage unavailable — detect and operate in session-only mode. Show non-blocking notice "Progress won't be saved across visits." Test in Playwright with `context.grantPermissions` disabled.
- [ ] T064 [P] Edge case: Schema version mismatch — test by setting old version in localStorage, reloading, confirming data discarded with notice shown.
- [ ] T065 [P] Edge case: Slow connection — test domain loading with Playwright network throttling (3G profile), verify progress bar appears and interface remains responsive.
- [ ] T066 [P] Edge case: Unsupported browser — detect missing features (WebGL, ES modules) and show fallback message recommending Chrome/Firefox/Safari/Edge.
- [ ] T067 [P] Edge case: CDN failure — test with blocked CDN URLs, verify degraded but functional state.
- [ ] T068 Edge case: Rapid domain switching — test switching 5 domains within 2 seconds, verify only final domain renders, no visual glitches.
- [ ] T069 [P] GitHub Pages deployment: GitHub Action workflow (`.github/workflows/deploy.yml`) — on push to main, run `npm run build`, deploy `dist/` to gh-pages branch. Configure repository for GitHub Pages from gh-pages branch.
- [ ] T070 Run `quickstart.md` validation: Fresh clone, follow every step, confirm everything works as documented.
- [ ] T071 Final visual regression: Re-capture all Playwright screenshots, compare with Phase 12 baselines, confirm <0.1% pixel diff.
- [ ] T072 Code cleanup: Remove any console.log debugging, ensure consistent code style, verify no TODO/FIXME comments remain in shipped code.
- [ ] T073 [P] Archive old data files: Remove or move legacy root-level data files (`cell_questions.json`, `wikipedia_articles.json`, `heatmap_cell_labels.json`, `question_coordinates.json`, `cell_questions_level_*.json`, `wikipedia_articles_level_*.json`) that are superseded by `data/domains/` bundles. Update `.gitignore` if needed. Update any documentation referencing old paths. Preserve old files in git history — do not rewrite history.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion — BLOCKS all user stories
- **Phases 3–8 (User Stories)**: All depend on Phase 2 completion
  - US1 (Phase 3) MUST complete before US3 (Phase 5) and US4 (Phase 6)
  - US2 (Phase 4) depends on Phase 2 only (can run parallel with US1 after foundation)
  - US5 (Phase 7) depends on US1 + US2 (needs working GP + domain switching)
  - US6 (Phase 8) depends on Phase 2 only (independent from other stories)
- **Phase 9 (Pipeline)**: Can start in parallel with Phase 2 (Python, independent of frontend)
  - MUST complete before end-to-end testing (Phase 12)
- **Phase 10–11 (Responsive + A11y)**: Depend on US1 being functional
- **Phase 12 (Constitution)**: Depends on ALL user stories + pipeline complete
- **Phase 13 (Polish)**: Depends on Phase 12 passing

### User Story Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundation)  ←──────────── Phase 9 (Pipeline: T040b→T041→T042→T044b→T043→T044) [parallel]
    ↓                                     ↓
Phase 3 (US1) + Phase 4 (US2) ──→ Phase 9 must complete for real data
    ↓              ↓
Phase 5 (US3) Phase 7 (US5)
    ↓
Phase 6 (US4)
    ↓
Phase 8 (US6) [can also start after Phase 2]
    ↓
Phase 10 (Responsive) + Phase 11 (A11y) [parallel]
    ↓
Phase 12 (Constitution: T051→T054b→T054c + visual + compat) [100% verification]
    ↓
Phase 13 (Polish + Deploy + T073 old file cleanup)
```

### Within Each User Story

- Models/data before services
- Services before UI
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T003, T005, T006, T009 can run in parallel (Phase 1)
- T012, T013 can run in parallel (domain loading modules)
- T017, T018 can run in parallel (renderer + accessibility utils)
- Phase 9 (Python pipeline) can run entirely in parallel with Phases 2–4
- T045, T046 can run in parallel (responsive CSS + touch)
- T048, T049, T050 can run in parallel (a11y tasks)
- T063–T067 can run in parallel (edge case testing)

---

## Implementation Strategy

### MVP First (US1 Only — Phase 1→2→3)

1. Complete Phase 1: Setup (Vite + skeleton)
2. Complete Phase 2: Foundation (state, loader, estimator, renderer)
3. Complete Phase 3: User Story 1 (domain select → answer → heatmap)
4. **STOP and VALIDATE**: Test US1 independently with placeholder domain data
5. Begin Phase 9 (pipeline) in parallel if not already started

### Incremental Delivery

1. Setup + Foundation → skeleton running
2. US1 → core quiz loop functional (MVP!)
3. US2 → domain transitions + minimap
4. US3 → smart question modes
5. US4 → knowledge insights
6. US5 → cross-domain prediction tuning
7. US6 → about/reset/export
8. Responsive + A11y → cross-platform support
9. Constitution Validation → quality gates
10. Polish + Deploy → ship to GitHub Pages

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Pipeline (Phase 9) is Python-only and can run in parallel with all frontend work
- Commit after each task or logical group
- Stop at any checkpoint to validate current state
- The old `index.html` monolith (3591 lines) is replaced in T007 — ensure the old version is preserved in git history
- The old `adaptive_sampler_multilevel.js` is superseded by `src/learning/sampler.js` + `src/learning/estimator.js` + `src/learning/curriculum.js`
- deck.gl CDN is NOT used — it's bundled via Vite for tree-shaking (research.md Decision 4)
- Total task count: 77 tasks across 13 phases (T001–T073 including T040b, T044b, T054b, T054c)
