# Quickstart: Ready Demo for Public Release

## Prerequisites

- **Node.js** 18+ (for Vite build system, Vitest, Playwright)
- **Python** 3.11+ (for pipeline scripts)
- **npm** 9+ (comes with Node.js)

## Setup

```bash
# Clone and switch to feature branch
git clone https://github.com/ContextLab/mapper.git
cd mapper
git checkout 001-demo-public-release

# Install frontend dependencies
npm install

# Install Python pipeline dependencies (if running pipeline)
pip install -r requirements.txt
```

## Development

```bash
# Start dev server with hot module replacement
npm run dev
# → Opens http://localhost:5173/mapper/

# Run algorithm tests
npx vitest run

# Run algorithm benchmark (SC-011: active vs random)
npx vitest bench

# Run visual/cross-browser tests (requires browsers installed)
npx playwright install  # One-time browser download
npx playwright test
```

## Build & Deploy

```bash
# Production build (tree-shaken, minified)
npm run build
# → Output: dist/

# Preview production build locally
npm run preview
# → http://localhost:4173/mapper/

# Deploy happens automatically via GitHub Action on merge to main
```

## Project Layout

```
mapper/
├── index.html              # Slim HTML shell (Vite entry point)
├── vite.config.js          # Build config (~5 lines)
├── package.json            # npm dependencies + scripts
├── src/                    # Frontend ES modules
│   ├── app.js              # Entry: init, routing, orchestration
│   ├── state/              # Nano Stores atoms + localStorage persistence
│   ├── domain/             # Domain registry, lazy loader, question logic
│   ├── learning/           # GP estimator, active sampler, curriculum
│   ├── viz/                # deck.gl renderer, transitions, minimap
│   ├── ui/                 # Quiz panel, modes menu, insights, controls
│   └── utils/              # Math helpers, accessibility utilities
├── data/domains/           # Per-domain JSON bundles (pipeline output)
│   ├── index.json          # Domain registry (~5 KB, loaded at startup)
│   └── {domain-id}.json    # Domain bundle (100–500 KB, lazy-loaded)
├── scripts/                # Python pipeline (existing + 3 new scripts)
├── tests/
│   ├── visual/             # Playwright specs (cross-browser, a11y)
│   └── algorithm/          # Vitest specs (GP, sampler, benchmark)
└── specs/001-demo-public-release/  # This planning documentation
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start Vite dev server with HMR |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview production build |
| `npx vitest run` | Run algorithm unit tests |
| `npx vitest bench` | Run SC-011 benchmark (active vs random) |
| `npx playwright test` | Run visual + cross-browser tests |
| `python scripts/run_full_pipeline.py` | Run full data pipeline |
| `python scripts/export_domain_data.py` | Export per-domain JSON bundles |

## Data Pipeline (Pre-processing)

The pipeline generates static JSON files consumed by the frontend.
Run once (or when domain/question changes are needed):

```bash
# Full pipeline (idempotent)
python scripts/run_full_pipeline.py

# Export per-domain bundles for lazy loading
python scripts/export_domain_data.py

# Define 19 domain regions in embedding space
python scripts/define_domains.py

# Generate domain-specific questions
python scripts/generate_domain_questions.py
```

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Rendering | deck.gl | Native 3D transitions, heatmap layer, per-point animation |
| State | Nano Stores (286 bytes) | Atomic stores, built-in localStorage sync |
| Build | Vite | Tree-shaking for deck.gl, HMR, GitHub Pages deploy |
| Algorithm tests | Vitest | Native ESM, built-in benchmarking |
| Visual tests | Playwright | Cross-browser, screenshot regression, WCAG audit |
| Pipeline | Python 3.11+ | Existing scripts + 3 new domain-generation scripts |
