# Implementation Plan: Tutorial Mode, Data Fixes & UX Polish

**Branch**: `005-tutorial-and-polish` | **Date**: 2026-03-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-tutorial-and-polish/spec.md`

## Summary

Fix data integrity issues (broken questions, incorrect answers, missing metadata), add a guided tutorial mode for first-time users, and polish engagement features (milestones, progress display, video recommendations). Re-run persona testing to validate improvements reach 90%+ pass rate. The persona testing framework from spec 004 is preserved and augmented with tutorial-aware evaluation.

## Technical Context

**Language/Version**: JavaScript ES2022+ (ES modules), HTML5, CSS3
**Primary Dependencies**: nanostores 1.1, Vite 7.3, Canvas 2D API, KaTeX (CDN), @playwright/test 1.58+ (testing), Claude Code Task agents (persona evaluation)
**Storage**: File-based JSON (`data/domains/*.json`), localStorage (user progress + tutorial state)
**Testing**: Playwright (E2E/visual/persona), Vitest (unit)
**Target Platform**: Web browser (Chrome, Firefox, Safari, Edge) — desktop + mobile viewports
**Project Type**: Static client-side web application with AI-driven test framework
**Performance Goals**: Tutorial animations at 60fps desktop / 30fps+ mobile (SC-004). CSS-only animations, no JS animation libraries.
**Constraints**: All tutorial UI must use existing theme system. SVG animations must be inline (no external assets). `prefers-reduced-motion` respected. No new npm dependencies for animations.
**Scale/Scope**: ~4 broken questions to fix, ~20 questions with missing metadata, 7 tutorial steps, 4 engagement features, 18 persona re-tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Accuracy
- **PASS**: Phase A directly strengthens accuracy — fixing broken questions (A1), correcting answer keys (A2), verifying source articles via web search (A3), auditing weak distractors (A4). A3 explicitly requires Wikipedia article existence verification per constitution requirement. Phase B adds runtime validation guard (B1) to prevent broken questions from reaching users.

### Principle II: User Delight
- **PASS**: Tutorial mode (Phase C) is the primary user delight feature — guided onboarding with M3 motion principles, inline SVG animations, progressive disclosure of features. Phase D adds milestone celebrations, progress display, and proactive video recommendations. All animations target 60fps per constitution requirement. CSS-only approach avoids jank.

### Principle III: Compatibility
- **PASS**: Tutorial includes explicit mobile adaptation (≤480px) per clarification — bottom-sheet modals, skip minimap steps on mobile. Existing Playwright cross-browser tests preserved (SC-006). Tutorial disabled in test fixtures via localStorage to avoid breaking existing tests. `prefers-reduced-motion` respected for accessibility.

**Gate Result**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/005-tutorial-and-polish/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── app.js                    # Main orchestrator — milestone triggers, progress tracking
├── ui/
│   ├── quiz.js               # Question validation guard (B1), question count display (D3)
│   ├── tutorial.js            # NEW — Tutorial state machine, modal rendering, step logic
│   ├── tutorial-animations.js # NEW — Inline SVG animation components
│   ├── tutorial.css           # NEW — Tutorial modals, overlays, highlights, M3 easing
│   ├── milestones.js          # NEW — Milestone toast + CSS confetti
│   └── modes.js               # Existing — no changes expected
├── viz/
│   ├── renderer.js            # Existing — no changes expected
│   └── minimap.js             # Existing — no changes expected
├── learning/
│   └── estimator.js           # domainMappedPct fix (B2)
└── domain/
    └── loader.js              # Cross-domain filtering (B4)

data/domains/
├── index.json                 # Domain registry (reference for A3 domain ID validation)
├── physics.json               # Fix broken questions (A1), metadata (A3)
├── mathematics.json           # Fix primitive root question (A1)
└── *.json                     # Audit all for A3, A4

tests/
├── visual/
│   ├── personas/
│   │   ├── definitions.js     # Preserved from 004, augmented with tutorial eval dimensions
│   │   ├── runner.js          # Preserved, add "?" logging (B3), tutorial localStorage injection
│   │   ├── evaluator-prompts.js # Preserved, add tutorialClarity/Pacing/Completeness dimensions
│   │   └── report-compiler.js # Preserved, no changes
│   ├── persona-agents.spec.js # Preserved from 004
│   └── tutorial.spec.js       # NEW — Playwright tests for tutorial flow
└── unit/
    └── tutorial.test.js       # NEW — Unit tests for tutorial state machine
```

**Structure Decision**: Extends existing `src/ui/` with new tutorial module files. No new directories outside existing structure. Data fixes are in-place edits to existing JSON files.

## Phase 0: Research

Minimal research needed — tech stack is established, all dependencies are known.

### R1. M3 Motion Token Values

**Decision**: Use the following M3-aligned CSS custom properties throughout tutorial:
- `--ease-emphasized-decel: cubic-bezier(0.05, 0.7, 0.1, 1.0)` — entering elements
- `--ease-emphasized-accel: cubic-bezier(0.3, 0.0, 0.8, 0.15)` — exiting elements
- `--ease-standard: cubic-bezier(0.2, 0.0, 0.0, 1.0)` — continuous transitions
- Durations: `--dur-short: 150ms`, `--dur-medium: 300ms`, `--dur-long: 500ms`, `--dur-xlong: 800ms`

**Rationale**: M3 motion principles ensure animations feel natural and purposeful. CSS custom properties allow consistent application across all tutorial components.
**Alternatives**: Spring-based JS animations (rejected — adds dependency, risks jank), Web Animations API (rejected — less browser support than CSS transitions for simple cases).

### R2. Tutorial Overlay Pattern

**Decision**: Use a full-viewport overlay div with CSS `clip-path` to cut out the highlighted element. The highlighted element gets `position: relative; z-index` above the overlay.

**Rationale**: `clip-path` is well-supported, performant (GPU-composited), and avoids the complexity of multiple overlay panels. Works correctly with the Canvas-based map since the overlay sits in the DOM layer above.
**Alternatives**: `mix-blend-mode` (rejected — interacts poorly with canvas), multiple semi-transparent divs (rejected — complex positioning), pointer-events manipulation only (rejected — doesn't provide visual dimming).

### R3. SVG Animation Approach

**Decision**: Static SVG frames with CSS `opacity` crossfade transitions. Each animation is 2-3 inline SVG elements stacked, with keyframe-driven opacity to create frame-by-frame appearance. SVGs are authored as template literals in `tutorial-animations.js`.

**Rationale**: Inline SVGs render crisply at any resolution, inherit theme CSS custom properties via `currentColor`, and require no external asset loading. CSS opacity transitions are GPU-composited and reliable at 60fps.
**Alternatives**: Lottie/bodymovin (rejected — large dependency, overkill for simple animations), Canvas-drawn animations (rejected — conflicts with map canvas), animated GIFs (rejected — blurry at high DPI, can't theme).

### R4. domainMappedPct Investigation

**Decision**: Investigate the estimator's `domainMappedPct` calculation. The metric is reported in checkpoint data but stuck at 0% for most personas. Likely either: (a) the calculation references a property that's never set, (b) it's computed from a grid resolution that's too coarse, or (c) it's reading from the wrong estimator instance.

**Rationale**: Fixing this metric validates that the GP estimator is correctly tracking spatial coverage, which is important for the tutorial's "building your map" narrative.

### R5. Existing Persona Framework Inventory

**Decision**: Preserve all spec 004 persona testing files as-is. Augment rather than replace:
- `definitions.js` — add `tutorialEnabled` flag per persona (default: true for re-test, false for legacy comparison)
- `runner.js` — add localStorage injection for tutorial state before navigation, add "?" answer logging
- `evaluator-prompts.js` — add 3 new eval dimensions: `tutorialClarity`, `tutorialPacing`, `tutorialCompleteness`
- `report-compiler.js` — no changes needed (generic enough to handle new dimensions)
- `persona-agents.spec.js` — no changes needed (Phase 1 automation unchanged)
- `run_persona_phase2.mjs` — no changes needed

**Rationale**: The persona framework is working correctly (24/24 Phase 1 tests pass). Changes should be minimal and additive to avoid regressions.

## Phase 1: Design

### Data Model

#### TutorialState (localStorage)

```
{
  completed: boolean,          // true when user finishes Step 8c
  dismissed: boolean,          // true when user clicks "Skip Tutorial" or "×"
  step: number,                // current step (0-8, sub-steps as 1.1/1.2/1.3, 8.1/8.2/8.3)
  hasSkippedQuestion: boolean, // tracks whether user has ever pressed Skip
  skipToastShown: boolean,     // tracks whether the skip explanation toast has fired
  returningUser: boolean       // set to true if $responses.length > 0 at tutorial start
}
```

localStorage key: `mapper-tutorial`

#### TutorialStep (runtime)

```
{
  id: number,                  // 1-8
  title: string,               // display title
  message: string | function,  // static text or function(state) => text for dynamic content
  highlightSelector: string,   // CSS selector of element to highlight (null = no highlight)
  animation: string | null,    // animation component key ('map-evolution', 'minimap', 'feature-open')
  advanceOn: string,           // event that advances: 'answer', 'domain-change', 'dismiss', 'any'
  questionTarget: number,      // total questions needed before this step activates
  skipOnMobile: boolean,       // true = skip this step on ≤480px viewports
  subSteps: TutorialStep[],    // for Step 6 and Step 7 sub-sequences
}
```

#### MilestoneConfig (static)

```
{
  threshold: number,           // question count trigger (10, 25, 50)
  message: string,             // toast text
  hasConfetti: boolean,        // true for first milestone only
  shown: boolean               // runtime flag, persisted in localStorage
}
```

### Interface Contracts

No external APIs or public interfaces. All new code is internal UI modules consumed by `app.js`. The tutorial module exports:

```javascript
// src/ui/tutorial.js
export function initTutorial(appState)     // Initialize tutorial, check localStorage
export function advanceTutorial(event)      // Handle step progression
export function dismissTutorial()           // User dismisses tutorial
export function resetTutorial()             // Restart from Step 1
export function isTutorialActive()          // Query current state

// src/ui/milestones.js
export function checkMilestone(questionCount) // Show toast if threshold reached
```

### Quickstart

```bash
# 1. Create feature branch
git checkout -b 005-tutorial-and-polish

# 2. Fix data issues (Phase A)
# Edit data/domains/*.json to fix broken questions
# Run: node scripts/run_persona_phase2.mjs --all  (to verify fixes)

# 3. Implement tutorial (Phase C)
# Create src/ui/tutorial.js, tutorial-animations.js, tutorial.css
# Wire into src/app.js

# 4. Run tests
npm test                                    # Unit + existing Playwright
npx playwright test tests/visual/tutorial.spec.js  # Tutorial-specific

# 5. Re-run persona testing
npx playwright test tests/visual/persona-agents.spec.js
node scripts/run_persona_phase2.mjs --all   # Compile reports, check 90% target
```

## Post-Design Constitution Re-Check

### Principle I: Accuracy
- **PASS**: A1-A4 fix data integrity. A3 uses web search verification for source articles. B1 adds runtime guard. No new LLM-generated content introduced.

### Principle II: User Delight
- **PASS**: Tutorial uses M3 motion principles with CSS-only animations targeting 60fps. SVG animations are inline and theme-aware. Milestones add celebration moments. All visual changes will be verified via Playwright screenshots.

### Principle III: Compatibility
- **PASS**: Mobile adaptation documented (bottom-sheet modals, skip minimap steps). `prefers-reduced-motion` respected. Cross-browser testing via existing Playwright infrastructure. No browser-specific APIs used.

**Gate Result**: ALL PASS — proceed to task generation.
