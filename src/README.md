# Source Code

The frontend is a vanilla JavaScript application built with Vite. No framework — just ES modules, Canvas 2D rendering, and DOM manipulation.

## Architecture

```
src/
├── app.js              ← Entry point: initialization, routing, event wiring
├── domain/             ← Domain data loading and registry
│   ├── loader.js       ← Fetch and cache domain JSON bundles
│   ├── questions.js    ← Question pool management per domain
│   └── registry.js     ← Domain hierarchy lookups and metadata
├── learning/           ← Adaptive quiz engine
│   ├── curriculum.js   ← Difficulty progression and topic sequencing
│   ├── estimator.js    ← Bayesian knowledge estimation (per-concept)
│   └── sampler.js      ← Weighted question selection based on knowledge gaps
├── state/              ← Application state
│   ├── persistence.js  ← LocalStorage save/restore of quiz progress
│   └── store.js        ← Centralized state (scores, current domain, mode)
├── ui/                 ← UI components and interactions
│   ├── controls.js     ← Domain dropdown, toolbar buttons, settings
│   ├── insights.js     ← Knowledge insights panel with concept suggestions
│   ├── modes.js        ← Explore/Quiz mode toggling
│   ├── progress.js     ← Score display, progress indicators
│   ├── quiz.js         ← Question display, answer handling, feedback
│   └── share.js        ← Social sharing modal (Twitter, copy link, etc.)
├── utils/              ← Shared utilities
│   ├── accessibility.js ← ARIA labels, keyboard navigation, screen reader support
│   ├── feature-detection.js ← Browser capability checks (WebGL, touch, etc.)
│   └── math.js         ← Coordinate transforms, interpolation, distance functions
└── viz/                ← Canvas visualization
    ├── minimap.js      ← Corner minimap showing global position
    ├── particles.js    ← Floating particle effects in explore mode
    ├── renderer.js     ← Main canvas: heatmap, articles, questions, zoom/pan
    └── transitions.js  ← Animated camera transitions between domains
```

## Key Concepts

- **Domains** are rectangular regions in a 2D UMAP embedding space. Each domain has articles, quiz questions, and grid cell labels. Domain bundles are loaded on demand from `data/domains/{id}.json`.

- **Knowledge estimation** uses a Bayesian model that tracks per-concept mastery. Answering questions updates concept posteriors, which drive the heatmap coloring (red = weak, green = strong).

- **The renderer** draws everything on a single `<canvas>`: a colored heatmap grid, article dots, question markers, labels, and the minimap. Zoom/pan is handled via affine transforms.

- **Modes**: Explore mode allows free navigation; Quiz mode presents adaptive questions and updates the knowledge map in real time.

## Build

```bash
npm install
npm run dev    # Dev server at localhost:5173
npm run build  # Production build → dist/
```
