# PROJECT KNOWLEDGE BASE

**Updated:** 2026-02-27
**Branch:** generate-astrophysics-questions (main development branch)

## OVERVIEW

Knowledge Mapper: interactive adaptive quiz that maps conceptual knowledge across 250K Wikipedia articles and 5,000+ Khan Academy video transcripts. Users answer domain-specific questions while a Bayesian estimator interpolates knowledge across a 2D UMAP projection, rendering a real-time heatmap. Videos are recommended based on knowledge gaps. Stack: Vite + vanilla JS (frontend), Python 3.11+ (data pipeline), SentenceTransformer embeddings, UMAP projection, density flattening via optimal transport.

**Live demo:** https://contextlab.github.io/mapper/

## STRUCTURE

```
mapper/
├── index.html              # HTML shell: layout, modals, styles (Vite entry point)
├── src/                    # Modular ES6+ application source
│   ├── app.js              # Entry point: init, routing, domain switching, event wiring
│   ├── domain/             # Domain data loading and registry
│   │   ├── registry.js     # Domain index + bounding box lookups
│   │   ├── loader.js       # Domain bundle fetching + caching
│   │   ├── questions.js    # Question management + coordinate lookups
│   │   └── video-loader.js # Video catalog loading + window extraction
│   ├── learning/           # Adaptive quiz + knowledge estimation
│   │   ├── estimator.js    # RBF-based Bayesian knowledge estimator
│   │   ├── sampler.js      # Adaptive question selection (info-gain maximization)
│   │   ├── curriculum.js   # Domain progression + difficulty management
│   │   └── video-recommender.js  # Knowledge-gap-based video recommendations
│   ├── state/              # Application state + persistence
│   │   ├── store.js        # Central state management
│   │   └── persistence.js  # localStorage save/load (versioned schema)
│   ├── ui/                 # UI components
│   │   ├── controls.js     # Domain dropdown, zoom controls, header
│   │   ├── quiz.js         # Question display + answer handling
│   │   ├── modes.js        # Quiz modes (auto-advance, easy, hardest, don't-know)
│   │   ├── insights.js     # Knowledge insights panel (strengths/weaknesses)
│   │   ├── share.js        # Screenshot generation + social sharing
│   │   ├── video-modal.js  # YouTube player modal + video list
│   │   └── progress.js     # Loading modal (centered spinner + progress bar)
│   ├── utils/              # Shared utilities
│   │   ├── math.js         # RBF kernel, distance calculations
│   │   ├── accessibility.js # ARIA, keyboard navigation
│   │   └── feature-detection.js  # WebGL/canvas capability checks
│   └── viz/                # Canvas rendering
│       ├── renderer.js     # Main heatmap renderer (articles, videos, trajectories)
│       ├── minimap.js      # Corner minimap with viewport indicator
│       ├── particles.js    # Welcome screen particle physics system
│       └── transitions.js  # Domain switch animations
├── data/
│   ├── domains/            # 50 domain JSON bundles + index.json
│   │   ├── index.json      # Domain registry (ids, regions, bounding boxes)
│   │   ├── all.json        # Combined bundle (all articles)
│   │   └── {domain}.json   # Per-domain: articles[], questions[], labels
│   └── videos/
│       ├── catalog.json    # 5,044 videos with window coordinates [{x,y}]
│       └── .working/       # Pipeline working directory
│           ├── transcripts/    # 5,400+ Whisper transcripts (.txt)
│           └── embeddings/     # Per-video sliding-window embeddings (.npy)
├── scripts/                # Python data pipeline (see below)
├── embeddings/             # Generated .pkl files (gitignored, multi-GB)
├── tests/
│   ├── algorithm/          # Vitest unit tests (estimator, sampler, recommender)
│   └── visual/             # Playwright E2E tests (quiz flow, video recs, sharing)
├── notes/                  # Session logs and implementation plans
├── public/                 # Static assets (logos, favicons)
└── .credentials/           # API keys + cluster passwords (gitignored)
```

## KEY DATA

| Metric | Value |
|--------|-------|
| Wikipedia articles | ~250,000 (48,259 with coordinates across domains) |
| Knowledge domains | 50 (flat hierarchy in index.json) |
| Quiz questions | 2,450 (50 per domain, Claude Opus 4.6 generated) |
| Khan Academy videos | 5,044 in catalog |
| Video transcript windows | 77,408 (512-word sliding windows, 50-word stride) |
| Transcripts on disk | 5,400+ (.txt files from Whisper) |
| Embedding model | google/embeddinggemma-300m (768-dim) |
| UMAP params | n_neighbors=15, min_dist=0.1 |
| Density flattening | mu=0.85 (optimal transport) |

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| **Frontend** | | |
| App entry point | `src/app.js` | Init, domain switching, event wiring |
| Heatmap rendering | `src/viz/renderer.js` | Canvas 2D, articles, videos, trajectories |
| Welcome particles | `src/viz/particles.js` | Spring physics + mouse repulsion |
| Quiz UI | `src/ui/quiz.js` + `src/ui/modes.js` | Question display, auto-advance modes |
| Video recommendations | `src/learning/video-recommender.js` | Gap-based scoring + ranking |
| Video player modal | `src/ui/video-modal.js` | YouTube embed, watched tracking |
| Knowledge estimator | `src/learning/estimator.js` | RBF Bayesian interpolation |
| Screenshot/sharing | `src/ui/share.js` | Canvas export with grid, colorbar |
| Domain registry | `src/domain/registry.js` | Bounding boxes from index.json |
| Loading modal | `src/ui/progress.js` | Centered modal with spinner |
| **Pipeline** | | |
| Embed articles | `scripts/generate_embeddings_local_full.py` | 250K articles → 768-dim |
| Generate questions | `scripts/generate_domain_questions.py` | Claude Opus 4.6, 50/domain |
| Embed questions | `scripts/embed_questions_v2.py` | Same model as articles |
| Embed transcripts (full) | `scripts/embed_transcripts.py` | One embedding per video |
| Embed transcripts (windows) | `scripts/embed_video_windows.py` | Sliding windows per video |
| Joint UMAP | `scripts/fit_umap_joint.py` | Articles + questions + transcripts |
| Density flattening | `scripts/flatten_coordinates.py` | Optimal transport, mu param |
| Apply flattened coords | `scripts/apply_flattened_coords.py` | Updates all domain JSONs + catalog |
| Export domain bundles | `scripts/export_domain_bundles.py` | JSON bundles for frontend |
| Export video catalog | `scripts/export_video_catalog.py` | Windows + metadata → catalog.json |
| Scrape Khan videos | `scripts/scrape_khan_videos.py` | YouTube Data API |
| Download transcripts | `scripts/download_transcripts_whisper.py` | Whisper on GPU cluster |
| **Tests** | | |
| Unit tests (vitest) | `tests/algorithm/` | Estimator, sampler, recommender |
| E2E tests (Playwright) | `tests/visual/` | Quiz flow, video recs, sharing |
| Run unit tests | `npx vitest run` | 75 tests |
| Run E2E tests | `npx playwright test` | 8 spec files |

## DATA FLOW

### Current Pipeline (2026-02-27)

```
wikipedia.pkl (250K articles, gitignored)
    ↓ generate_embeddings_local_full.py
embeddings/wikipedia_embeddings.pkl (250K × 768)
    ↓ generate_domain_questions.py (Claude Opus 4.6)
data/domains/.working/*-questions-batch*.json (50 per domain)
    ↓ embed_questions_v2.py
embeddings/question_embeddings_2500.pkl (2500 × 768)

data/videos/.working/transcripts/*.txt (5,400+ Whisper transcripts)
    ↓ embed_transcripts.py (full-document embeddings)
embeddings/transcript_embeddings.pkl (N × 768, one per video)
    ↓ embed_video_windows.py (sliding-window embeddings)
data/videos/.working/embeddings/*.npy (per-video, [N_windows, 768])

    ↓ fit_umap_joint.py (articles + questions + transcripts TOGETHER)
embeddings/umap_reducer.pkl + article_coords.pkl + question_coords.pkl + transcript_coords.pkl
    ↓ flatten_coordinates.py --mu 0.85 (optimal transport)
embeddings/*_coords.pkl (density-balanced [0,1] coordinates)
    ↓ apply_flattened_coords.py
data/domains/{domain}.json (articles + questions with flattened coords)
data/domains/index.json (bounding boxes from question 5th-95th percentile)
    ↓ project_video_coords.py + export_video_catalog.py
data/videos/catalog.json (5,044 videos × window coordinates)
```

**Key principles:**
- Articles, questions, and transcripts are projected TOGETHER in one UMAP
- Bounding boxes use question-only 5th-95th percentile (min_span=0.15, margin=0.05)
- Density flattening uses approximate optimal transport (Hungarian assignment on subsample)
- Video windows are projected through trained UMAP reducer via `transform()`

### Video Recommendation Flow

```
User answers question → estimator updates knowledge map
    → video-recommender computes difference map (estimated - ground truth)
    → scores each video's windows against knowledge gaps
    → ranks videos by expected learning gain
    → presents top recommendations in modal
    → user watches video → marks watched → map updates
```

## CONVENTIONS

- **Build system**: Vite (dev: `npm run dev`, build: `npm run build`)
- **Dev server**: http://localhost:5173/mapper/
- **No framework**: Vanilla JS with ES6 modules, no React/Vue/etc.
- **Credentials**: `.credentials/` directory (gitignored). `openai.key`, `tensor02.credentials`
- **macOS env vars**: Scripts set `TOKENIZERS_PARALLELISM=false`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`
- **Python venv**: Use `.venv/bin/python3` (not system python) for numpy 2.x compatibility
- **Embedding model**: `google/embeddinggemma-300m` everywhere (768-dim, SentenceTransformer)
- **LLM model**: `Claude Opus 4.6` via Anthropic API for question generation
- **localStorage**: Browser-side persistence, versioned schema. No server-side storage.
- **Domain bundles**: Background pre-loaded at boot for instant switching (no loading modal per switch)
- **Domain viewport**: Read from `registry.getDomain(id).region` (index.json), not from bundle

## ANTI-PATTERNS

- **Never commit `.pkl` files** — multi-GB embedding/UMAP files are gitignored
- **Never commit `.credentials/`** — API keys, cluster passwords
- **Never mock in tests** — project policy requires real calls, real models, real I/O
- **Never use system python** — always `.venv/bin/python3` for pipeline scripts
- **Never read bounding boxes from bundle** — use registry (index.json) as source of truth
- **Never show loading modal on domain switch** — bundles pre-loaded in background

## COMMANDS

```bash
# Development
npm run dev                 # Vite dev server on :5173
npm run build               # Production build to dist/
npm run preview             # Preview production build

# Tests
npx vitest run              # Unit tests (75 tests)
npx playwright test         # E2E tests (8 specs)

# Pipeline (use .venv/bin/python3)
.venv/bin/python3 scripts/embed_transcripts.py          # Full-doc transcript embeddings
.venv/bin/python3 scripts/embed_video_windows.py        # Sliding-window embeddings
.venv/bin/python3 scripts/fit_umap_joint.py             # Joint UMAP fitting
.venv/bin/python3 scripts/flatten_coordinates.py --mu 0.85  # Density flattening
.venv/bin/python3 scripts/apply_flattened_coords.py     # Apply to all domain JSONs
.venv/bin/python3 scripts/export_video_catalog.py       # Rebuild video catalog

# GPU cluster (tensor02)
sshpass -p 'PASSWORD' ssh f002d6b@tensor02.dartmouth.edu "command"
RSYNC_RSH="sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no" rsync -avz ...
```

## GPU CLUSTER

- **tensor02.dartmouth.edu**: 8x NVIDIA RTX A6000 (49GB VRAM each)
- Transcripts generated via Whisper on tensor02, synced to local via rsync
- Credentials in `.credentials/tensor02.credentials` (JSON format)
- Transcript path on tensor02: `~/khan-transcripts/data/videos/.working/transcripts/`

## NOTES

- Questions use LaTeX notation (`$x^2$`) rendered by KaTeX in the frontend
- Welcome screen has canvas particle system with spring-return + mouse-repulsion physics
- `pointer-events: none` on `.landing-content` with selective `auto` on interactive children
- Video markers render as subtle dots (alpha ~2%), with Catmull-Rom trajectory on hover
- Screenshots include grid lines, colorbar legend, article + video dots
- License: CC BY-NC-SA 4.0 (non-commercial)
