# Implementation Plan: Performance & UX Refinement

**Branch**: `006-performance-and-ux-refinement` | **Date**: 2026-03-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-performance-and-ux-refinement/spec.md`

## Summary

Address Safari performance issues, fix cross-domain question contamination, improve mobile map visibility with a collapsible quiz drawer, and clean up orphaned question metadata. All changes must maintain 100% persona pass rate and pass existing tests across Chromium, Firefox, and WebKit.

## Technical Context

**Language/Version**: JavaScript ES2022+ (ES modules), HTML5, CSS3
**Primary Dependencies**: nanostores 1.1, Vite 7.3, Canvas 2D API, KaTeX (CDN), deck.gl 9.2
**Storage**: localStorage (user progress), file-based JSON (question banks in `data/domains/`)
**Testing**: Vitest (unit, 88 tests), Playwright 1.58+ (visual/E2E, Chromium + WebKit + Firefox)
**Target Platform**: Web (static site hosted on GitHub Pages at `/mapper/`)
**Project Type**: Single-page web application (vanilla JS, no framework)
**Performance Goals**: 60fps animations on Safari, panel transitions < 300ms, no dropped frames
**Constraints**: No build-time dependencies beyond Vite; CDN-loaded KaTeX and Font Awesome; must work offline after initial load
**Scale/Scope**: 2,500 questions across 50 domains, 32 test personas, single-user (no auth)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Accuracy
- **Status**: PASS
- Question content fixes (orphaned domainIds, self-answering questions) directly serve accuracy
- All question changes will be verified against source articles
- No mock tests — all testing uses real browser engines via Playwright

### Principle II: User Delight
- **Status**: PASS
- Safari performance fixes directly serve the "no jank, stutter, or layout shifts" requirement
- Mobile drawer pattern improves usability on mobile form factors
- Video recommendation indicator improves feature discoverability
- All visual changes verified via Playwright screenshots

### Principle III: Compatibility
- **Status**: PASS
- Safari fixes are the primary goal — directly addresses WebKit compatibility
- Mobile collapsible drawer addresses 320px-480px form factor requirements
- New WebKit-specific Playwright tests added to test suite
- Touch interactions (swipe to collapse/expand) serve mobile compatibility

### Gate Result: PASS — all three principles aligned with feature goals.

## Project Structure

### Documentation (this feature)

```text
specs/006-performance-and-ux-refinement/
├── plan.md              # This file
├── research.md          # Phase 0: Safari perf research, domain filter analysis
├── data-model.md        # Phase 1: Question metadata, domain hierarchy
├── quickstart.md        # Phase 1: Test scenarios
├── checklists/          # Quality validation
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── app.js               # Main orchestrator, domain switching, question flow
├── domain/
│   └── loader.js         # Domain bundle loading, question filtering [MODIFY: fix domain filter]
├── learning/
│   ├── estimator.js      # GP estimator
│   └── video-recommender.js  # Video ranking pipeline
├── ui/
│   ├── quiz.js           # Quiz panel rendering [MODIFY: collapsible drawer on mobile]
│   ├── video-panel.js    # Video panel
│   ├── video-modal.js    # Video detail modal
│   ├── insights.js       # Expertise modal
│   ├── share.js          # Share modal
│   └── tutorial.js       # Tutorial system
├── viz/
│   ├── renderer.js       # Canvas 2D heatmap rendering
│   └── minimap.js        # Minimap
├── state/
│   └── store.js          # nanostores state atoms
└── utils/
    └── math.js           # Kernel functions

index.html               # Main HTML + inline CSS [MODIFY: Safari CSS fixes, mobile drawer styles]

data/domains/
├── index.json            # Domain hierarchy [READ: for filter logic]
└── *.json                # Question banks [MODIFY: fix orphaned metadata]

tests/
├── algorithm/            # Vitest unit tests (88 tests)
├── visual/               # Playwright E2E tests
│   ├── safari-perf.spec.js      # [NEW: WebKit performance tests]
│   ├── domain-filter.spec.js    # [NEW: domain filtering verification]
│   └── mobile-drawer.spec.js    # [NEW: mobile collapsible quiz panel]
└── visual/personas/      # Persona testing framework
```

**Structure Decision**: Existing single-project structure. No new directories needed — only modifications to existing files and new test specs.
