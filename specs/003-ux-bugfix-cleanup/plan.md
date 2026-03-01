# Implementation Plan: UX Cleanup & Bug Fix Sweep

**Branch**: `003-ux-bugfix-cleanup` | **Date**: 2026-02-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-ux-bugfix-cleanup/spec.md`

## Summary

A 13-item bug fix and feature sweep addressing critical GP estimator numerical instability (Cholesky collapse at ~120 questions), difficulty-weighted evidence inversion, skip behavior, keyboard modifier collisions, hover popup scroll-blocking, canvas resize misalignment, import-from-landing-page regression, share modal Web Share API misuse, article title underscores, minimap viewport dragging, and a new video discovery panel. The fixes span 8 existing source files and add 1 new module.

## Technical Context

**Language/Version**: JavaScript ES2022+ (ES modules), HTML5, CSS3
**Primary Dependencies**: nanostores 1.1.0, Vite 7.3.1, Canvas 2D API, KaTeX (CDN)
**Storage**: localStorage via `@nanostores/persistent`
**Testing**: Vitest 4.0.18 (unit), Playwright 1.58.2 (E2E/visual)
**Target Platform**: Static web app (GitHub Pages), modern browsers (Chrome/FF/Safari/Edge latest 2)
**Project Type**: Single-page web application (vanilla JS, Canvas 2D visualization)
**Performance Goals**: 60fps pan/zoom, GP predict() <15ms for N≤200 observations
**Constraints**: No server-side; all computation client-side; localStorage only
**Scale/Scope**: ~257K embedded documents, ~5K videos, 50×50 GP grid, single HTML page

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Principle I (Accuracy)**: GP estimator fixes (adaptive jitter, difficulty weighting) will be validated with Vitest unit tests using controlled observation sequences. No LLM-generated content changes. Diagnostic assertions verify smooth progression and no NaN outputs.
- [x] **Principle II (User Delight)**: All visual changes (video panel, resize fix, tooltip fix, share screenshot) will be verified via Playwright screenshots. Quiz UX changes (skip feedback, keyboard guards) will be tested in E2E flows. No performance regression — GP predict() timing assertions included.
- [x] **Principle III (Compatibility)**: Keyboard modifier fix uses standard `e.metaKey/ctrlKey/altKey/shiftKey` (all browsers). Video panel uses CSS flexbox (universal support). Canvas resize fix is browser-agnostic. Share modal fix removes platform-specific Web Share API in favor of universal URL-based sharing.

**No violations.** All changes align with existing architecture patterns.

## Project Structure

### Documentation (this feature)

```text
specs/003-ux-bugfix-cleanup/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── estimator.md     # GP estimator interface contract
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── utils/math.js           # Cholesky solver stability fix (adaptive jitter + retry)
├── learning/estimator.js   # Difficulty weight inversion, skip weight fix
├── ui/quiz.js              # Modifier key guard, skip feedback, article title fix
├── ui/share.js             # Remove Web Share API, fix copy/copy-image separation
├── ui/video-panel.js       # NEW: Left sidebar video discovery panel
├── viz/renderer.js         # Tooltip pointer-events fix, resize alignment fix
├── viz/minimap.js          # Viewport drag hit-test relaxation
├── app.js                  # Wire skip feedback, import fix, video panel wiring
└── state/store.js          # (no changes expected)

tests/
├── unit/
│   └── estimator.test.js   # Stability, difficulty weighting, skip weight tests
└── visual/
    └── ux-fixes.spec.js    # Playwright E2E for keyboard, import, share, video panel
```

**Structure Decision**: All changes are within the existing `src/` and `tests/` directory structure. One new file (`src/ui/video-panel.js`) follows the established module pattern. No new directories needed.

## Complexity Tracking

No constitution violations. All changes fit within existing architecture.
