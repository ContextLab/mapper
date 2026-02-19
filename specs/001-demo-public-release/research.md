# Research: Ready Demo for Public Release

**Date**: 2026-02-16
**Source**: Phase 0 research resolving NEEDS CLARIFICATION items from [plan.md](plan.md)

## Decision 1: WebGL Scatterplot Library

**Decision**: deck.gl (ScatterplotLayer + HeatmapLayer)

**Rationale**: For ~1000 points, raw performance differences are negligible.
deck.gl is the only library that provides all three requirements natively:
per-point attribute transitions (FR-020), 3D coordinate support with
OrbitView (FR-005), and a built-in HeatmapLayer (FR-003) sharing the same
camera and coordinate system. It turns complex animation and heatmap
requirements into simple prop updates.

**Alternatives considered**:
- **regl-scatterplot** (~35 KB): Excellent for 2D, but no native 3D
  camera/projection. Would require a separate canvas for heatmap and
  custom shaders for 3D rotation. Rejected: too much custom work.
- **Deepscatter / Embedding Atlas** (~120 KB): Designed for millions of
  points with tiling. Overkill for 1000 points, no 3D flexibility, no
  heatmap layer. Rejected: wrong scale.
- **Custom WebGL** (<20 KB): Total control, but 3–5 days to implement
  picking, pan/zoom, 3D rotation, and heatmap from scratch. Rejected:
  high effort for marginal bundle savings.

**Key details**:
- Bundle: ~180–250 KB gzipped (core + ScatterplotLayer + HeatmapLayer)
- Transitions: `transitions: { getPosition: 600 }` on data update
- 3D: `getPosition: d => [d.x, d.y, d.z]` + OrbitView
- CDN: `<script src="https://unpkg.com/deck.gl@latest/dist.min.js">`
- Touch: Industry-standard pan/zoom/interaction
- Compatibility: WebGL 2 with WebGL 1 fallback

---

## Decision 2: Active Learning Algorithm

**Decision**: Gaussian Process with multi-scale RBF kernel and
centrality-weighted acquisition function

**Rationale**: GP provides mathematically grounded uncertainty
quantification that natively distinguishes "unknown" (high predictive
variance σ², far from observations) from "uncertain" (mean μ ≈ 0.5 with
low σ², conflicting nearby answers) — directly satisfying FR-017 without
heuristics. With N=50 observations and M≈1500 prediction cells, GP runs
in ~15 ms in browser JS, well within the 50 ms budget.

**Alternatives considered**:
- **Beta-Binomial (per-cell)**: Simpler (<5 ms), but FR-017 handling is
  heuristic-based (sample size vs ratio). Less principled for
  distinguishing epistemic vs aleatoric uncertainty. Rejected: doesn't
  satisfy FR-017's requirement to distinguish unknown from uncertain with
  mathematical rigor.
- **Hybrid (Beta-Binomial + graph centrality)**: ~20 ms, adds graph-based
  curriculum. More complex without clear advantage over GP + centrality.
  Rejected: added complexity without proportional benefit.

**Key details**:
- **Kernel**: Matérn 3/2 (slightly less smooth than RBF, better for
  knowledge boundaries)
- **Curriculum (FR-018)**: Multi-scale kernel with adaptive length-scale ℓ.
  Start broad (landmark cells provide max coverage) → shrink ℓ as coverage
  increases (niche boundary refinement). Weight acquisition by precomputed
  semantic centrality scores.
- **Viewport restriction (FR-016)**: Compute acquisition scores only for
  cells within active viewport. Trivial filter before scoring loop.
- **Cell re-selection (FR-019)**: GP naturally handles this — answered cells
  retain nonzero variance and remain candidates when uncertainty warrants.
- **Implementation**: Custom ~100-line JS module. Cache K⁻¹ and update
  via Woodbury identity in O(N²) per new observation.
- **Benchmark (SC-011)**: Expected information gain acquisition provably
  outperforms random in spatial estimation tasks (Hübotter et al. 2025).

---

## Decision 3: 3D Transition Technique

**Decision**: Simulated 3D rotation using PCA-3 depth with deck.gl
attribute transitions

**Rationale**: Achieves the "turning the globe" visual effect (FR-005)
with 1–2 days implementation effort and 9/10 visual quality. Points are
assigned a synthetic Z-coordinate from the 3rd PCA component of their
embeddings. During transitions, deck.gl interpolates (x, y, z)
automatically, and the perspective camera creates a natural parallax
rotation effect as points move through depth.

**Alternatives considered**:
- **Geodesic interpolation (Stiefel manifold)**: Mathematically rigorous
  (10/10 quality) but 7–10 days effort, no JS libraries, overkill for
  1000 points. Rejected: disproportionate effort.
- **Camera orbit (deck.gl FlyTo)**: 0.5 days, 8/10 quality, but requires
  all data to exist in a single meaningful 3D space for both source and
  target domains. Rejected: doesn't work when domains have fundamentally
  different spatial structures.
- **Coordinate morphing with easing**: 0.5 days, 5/10 quality. Points
  cross in the middle creating visual noise. Rejected: violates FR-005's
  requirement that points not cross over each other in 2D.

**Key details**:
- Pipeline: precompute PCA-3 as z-coordinate per article/question
- Transition: Update `getPosition` accessor → deck.gl interpolates
- Fade: Update `getFillColor` opacity channel simultaneously
- Performance: 60fps trivial at 1000 points with GPU interpolation

---

## Decision 4: Build System

**Decision**: Vite (minimal configuration)

**Rationale**: deck.gl is ~180–250 KB gzipped. Without tree-shaking, the
full library download would degrade load times on mobile. Vite provides
tree-shaking (stripping unused deck.gl layers), HMR for development, and
trivial GitHub Pages deployment. The one-time `npm install` cost is
justified by the development workflow improvement and production bundle
size reduction.

**Alternatives considered**:
- **No build (native ES modules + CDN)**: Zero install, but deck.gl via
  CDN is multi-MB without tree-shaking. Version pinning is manual.
  Rejected: unacceptable load times on mobile networks.
- **esbuild (script-level)**: Fast bundling but no HMR, no dev server,
  less robust CSS handling. Rejected: worse DX for marginal simplicity.

**Key details**:
- Config: ~5 lines in `vite.config.js` (`base: '/mapper/'`, `outDir: 'dist'`)
- Dev: `npm run dev` → HMR, instant feedback on visual changes
- Build: `npm run build` → tree-shaken, minified output to `dist/`
- Deploy: GitHub Action on merge to main → build → push to gh-pages branch
- Onboarding: Contributors run `npm install` once, then `npm run dev`

---

## Decision 5: JS Testing Framework

**Decision**: Vitest (algorithmic tests) + Playwright (visual/cross-browser)

**Rationale**: Vitest has native ESM support, zero-config for vanilla JS,
and a built-in benchmarking suite (`vitest bench`) that directly produces
the comparison tables needed for SC-011. Playwright remains the visual
and cross-browser testing tool per the constitution.

**Alternatives considered**:
- **Playwright-only**: Possible but awkward for algorithmic unit tests —
  requires serializing data through `page.evaluate()`. Rejected: poor DX
  for math-heavy tests.
- **Node.js native test runner**: Zero dependencies but no built-in
  benchmarking for SC-011. Rejected: would require custom benchmark
  reporting code.
- **Jest**: ESM support still requires experimental flags in 2026.
  Rejected: configuration overhead.

**Key details**:
- Install: `npm install -D vitest`
- Run: `npx vitest run` (tests), `npx vitest bench` (SC-011 benchmark)
- Structure: `tests/algorithm/*.test.js` for unit, `tests/visual/*.spec.js`
  for Playwright

---

## Decision 6: State Management

**Decision**: Nano Stores (~286 bytes, atomic store pattern)

**Rationale**: Atomic design maps directly to the modular architecture —
each module owns its atoms (`$activeDomain`, `$responses`, `$estimates`).
Built-in `persistentAtom` handles localStorage sync with cross-tab
coordination, directly implementing FR-007. At 286 bytes gzipped, the
bundle impact is negligible.

**Alternatives considered**:
- **Simple pub/sub (EventTarget)**: Zero bytes but leads to "event soup"
  in 15+ modules. Hard to trace state changes. No built-in persistence.
  Rejected: poor debugging at scale.
- **Proxy-based (Valtio)**: ~1 KB, intuitive mutation-based API. Proxies
  can be harder to inspect in debuggers. No built-in persistence.
  Rejected: worse debugging story.
- **Signals (@preact/signals-core)**: ~1.6 KB, highest performance via
  fine-grained reactivity. Higher learning curve (dependency graph mental
  model). Rejected: overcomplicated for this use case.

**Key details**:
- Atoms: `$activeDomain`, `$responses`, `$estimates`, `$animationState`
- Persistence: `persistentAtom('responses', [], { encode: JSON.stringify,
  decode: JSON.parse })` — auto-syncs to localStorage
- Schema versioning: Store `$schemaVersion` atom; on load, compare with
  app constant; discard if mismatched (FR-007)
- Reset (FR-021): Set all atoms to initial values
- Export (FR-022): Serialize `$responses` atom to JSON download

---

## Updated Technical Context

All NEEDS CLARIFICATION items resolved:

| # | Item | Decision |
|---|------|----------|
| 1 | WebGL scatterplot library | deck.gl (ScatterplotLayer + HeatmapLayer) |
| 2 | Build system | Vite (minimal config, tree-shaking for deck.gl) |
| 3 | Active learning algorithm | GP with Matérn 3/2 kernel + centrality acquisition |
| 4 | 3D transition technique | Simulated 3D rotation via PCA-3 depth + deck.gl transitions |
| 5 | Frontend architecture | Vanilla JS ES modules + Nano Stores (atomic state) |
| 6 | JS testing | Vitest (algorithm) + Playwright (visual/cross-browser) |
