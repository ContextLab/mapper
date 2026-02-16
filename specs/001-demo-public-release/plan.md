# Implementation Plan: Ready Demo for Public Release

**Branch**: `001-demo-public-release` | **Date**: 2026-02-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-demo-public-release/spec.md`

## Summary

Transform the existing Wikipedia Knowledge Map from a 3591-line monolithic
prototype into a production-quality public demo at contextlab.github.io/mapper.
The demo enables visitors to select knowledge domains, answer quiz questions
via active learning, and watch a 2D heatmap knowledge map fill in with smooth
3D-capable domain transitions. Requires: decomposing the monolith into
modules, implementing a principled active learning algorithm (replacing the
flawed RBF heuristic), building per-point WebGL transitions with 3D rotation,
adding 19 domain hierarchies with ~750–800 verified questions, and ensuring
cross-platform/WCAG AA accessibility.

## Technical Context

**Language/Version**: JavaScript ES2020+ (frontend), Python 3.11+ (pipeline)
**Primary Dependencies**:
- Frontend: deck.gl 9+ (WebGL scatterplot + heatmap + 3D transitions), KaTeX 0.16+ (LaTeX), Font Awesome 6 (icons), Nano Stores ~286B (atomic state management)
- Build: Vite (tree-shaking, HMR, GitHub Pages deploy)
- Pipeline: sentence-transformers, UMAP, OpenAI Batch API (gpt-5-nano), TensorFlow 2.19

**Storage**: localStorage (browser-side, versioned schema per FR-007 clarification). No server-side storage.
**Testing**:
- Algorithm unit tests + SC-011 benchmark: Vitest (native ESM, built-in benchmarking)
- Visual/cross-browser: Playwright (Chromium, Firefox, WebKit)
- Pipeline: pytest (real calls, no mocks per constitution)

**Target Platform**: Static web (GitHub Pages), browsers: Chrome/Firefox/Safari/Edge latest 2 versions, mobile 320px+
**Project Type**: Web application (static frontend + offline Python preprocessing pipeline)
**Performance Goals**: 60fps animations (SC-003), <500ms heatmap update (SC-002), <1s domain transition (SC-003), <60s first question (SC-001)
**Constraints**: Client-only post-load (FR-012), WCAG 2.1 AA (FR-023), lazy-load per domain (FR-012 clarification), no TF >= 2.20 (macOS bug)
**Scale/Scope**: 19 domains, ~750–800 unique questions, ~1000 visible articles per domain, 39×39 grid cells per domain heatmap

**Resolved decisions** (see [research.md](research.md) for full rationale):
1. WebGL scatterplot: **deck.gl** (native 3D + transitions + heatmap)
2. Build system: **Vite** (tree-shaking for deck.gl, HMR)
3. Active learning: **Gaussian Process** (Matérn 3/2 kernel + centrality acquisition)
4. 3D transitions: **Simulated 3D rotation** via PCA-3 depth + deck.gl attribute transitions
5. State management: **Nano Stores** (~286B atomic stores + localStorage persistence)
6. JS testing: **Vitest** (ESM native + built-in benchmarking for SC-011)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Verification | Pass |
|-----------|--------------|------|
| **I. Accuracy** | All ~750–800 questions verified against primary sources (SC-004). LLM-generated labels validated via spot-check scripts. Embedding coordinates validated for spatial coherence. Active learning benchmark proves superiority over random (SC-011). Tests use real calls — no mocks. | [x] |
| **II. User Delight** | Every visual change inspected via Playwright screenshots (constitution §II). 60fps animations on mid-range hardware (SC-003). KaTeX rendering verified across browsers. Progress bars for slow loads (FR-012). <500ms heatmap update (SC-002). | [x] |
| **III. Compatibility** | Playwright cross-browser tests: Chromium, Firefox, WebKit (SC-007). Mobile 320px+ and tablet 768px+ layouts (SC-008). Touch pan/zoom/selection (FR-014). WCAG 2.1 AA with zero critical Lighthouse violations (SC-013, FR-023). Color-blind safe palette. | [x] |

*Pre-research assessment: All three principles have concrete verification methods defined in the spec's success criteria. No violations requiring justification. Gate PASSES.*

**Post-design re-check (Phase 1 complete)**:
- **I. Accuracy**: GP-based active learning is mathematically grounded (not a heuristic). Question verification via web search is unchanged. Pipeline diagnostic scripts remain. Vitest ensures algorithm correctness with real function calls (no mocks). ✅
- **II. User Delight**: deck.gl provides 60fps GPU-accelerated transitions out of the box. Simulated 3D rotation via PCA-3 gives "turning the globe" effect. Nano Stores + Vite HMR enable rapid visual iteration. Playwright screenshots verify rendering quality. ✅
- **III. Compatibility**: deck.gl falls back to WebGL 1 for older browsers. Vite produces standard ES module bundles. Nano Stores is framework-agnostic. Playwright tests across Chromium/Firefox/WebKit. Color-blind safe palette (viridis/cividis) in heatmap contract. WCAG AA checked via Lighthouse in Playwright. ✅

*Post-design gate PASSES. No violations. No complexity tracking entries needed.*

## Project Structure

### Documentation (this feature)

```text
specs/001-demo-public-release/
├── plan.md              # This file
├── research.md          # Phase 0: technology decisions
├── data-model.md        # Phase 1: entity schemas
├── quickstart.md        # Phase 1: developer setup guide
├── contracts/           # Phase 1: module interfaces
│   ├── domain-data.md   # Domain data file format contracts
│   ├── active-learner.md # Active learning module interface
│   ├── renderer.md      # Scatterplot/heatmap rendering interface
│   └── state.md         # State management + localStorage contract
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created here)
```

### Source Code (repository root)

```text
# Frontend (static web app — decomposed from index.html monolith)
index.html                        # Slim shell: HTML structure + script imports
src/
├── app.js                        # Entry point: init, routing, orchestration
├── state/
│   ├── store.js                  # Central state (responses, active domain, estimates)
│   └── persistence.js            # localStorage read/write with version tag
├── domain/
│   ├── loader.js                 # Lazy-load domain JSON with progress events
│   ├── registry.js               # Domain hierarchy (19 domains, parent/child)
│   └── questions.js              # Question selection, filtering, overlap logic
├── learning/
│   ├── sampler.js                # Active learning: expected information gain
│   ├── estimator.js              # Knowledge estimation (GP/Bayesian surrogate)
│   └── curriculum.js             # Landmark→niche progression (FR-018)
├── viz/
│   ├── renderer.js               # WebGL scatterplot (points, heatmap, labels)
│   ├── transitions.js            # Per-point animation + 3D rotation (FR-005/020)
│   └── minimap.js                # Navigation overview graphic (FR-009)
├── ui/
│   ├── quiz.js                   # Question display, answer handling, LaTeX
│   ├── modes.js                  # Smart question modes menu (FR-010/011)
│   ├── insights.js               # Knowledge insights panels (US4)
│   ├── controls.js               # Reset, export, domain selector
│   └── progress.js               # Download progress bar, confidence indicator
└── utils/
    ├── math.js                   # RBF kernels, distance, interpolation
    └── accessibility.js          # Focus management, ARIA, keyboard nav

# Pipeline (Python — existing scripts, extended for domain generation)
scripts/
├── generate_domain_questions.py  # NEW: generate 50 questions per domain
├── define_domains.py             # NEW: define 19 domain regions in embedding space
├── export_domain_data.py         # NEW: export per-domain JSON bundles for lazy-load
└── [existing pipeline scripts unchanged]

# Tests
tests/
├── visual/                       # Playwright visual regression + cross-browser
│   ├── screenshots/              # Baseline screenshots
│   ├── quiz-flow.spec.js         # US1: domain select → answer → heatmap update
│   ├── transitions.spec.js       # US2: domain switch animation smoothness
│   ├── modes.spec.js             # US3: smart question mode selection
│   ├── accessibility.spec.js     # FR-023: WCAG AA Lighthouse audit
│   └── responsive.spec.js        # SC-008: mobile/tablet layouts
├── algorithm/                    # Active learning algorithm tests
│   ├── sampler.test.js           # Information gain computation correctness
│   ├── estimator.test.js         # Knowledge estimation accuracy
│   └── benchmark.test.js         # SC-011: active learning vs random baseline
└── [existing pytest tests unchanged]
```

**Structure Decision**: Hybrid web application. The frontend decomposes the
3591-line `index.html` monolith into ES modules under `src/` with a slim
`index.html` shell. No framework — vanilla JS with ES module imports
(pending build system research). The Python pipeline under `scripts/` is
extended with 3 new scripts for domain definition, question generation,
and per-domain data export. Playwright tests under `tests/visual/` cover
all constitution verification requirements.

## Complexity Tracking

> No Constitution Check violations. No justifications needed.
