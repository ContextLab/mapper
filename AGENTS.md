# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-16 13:54 UTC
**Commit:** d3cc534
**Branch:** main

## OVERVIEW

Wikipedia Knowledge Map: distributed GPU pipeline that generates semantic embeddings for 250K Wikipedia articles, projects them to 2D via UMAP, enriches cells with LLM-generated labels/questions across 5 difficulty levels, and serves an interactive adaptive quiz visualization. Stack: Python (sentence-transformers, UMAP, OpenAI Batch API, TensorFlow 2.19) + vanilla HTML/JS frontend.

## STRUCTURE

```
mapper/
├── index.html                  # 3591-line monolithic visualization (KaTeX, adaptive quiz UI)
├── adaptive_sampler_multilevel.js  # RBF-based adaptive testing algorithm (MultiLevelAdaptiveSampler)
├── run_full_pipeline.sh        # Shell orchestrator: L4→L3→L2 simplification + merge
├── scripts/                    # Core pipeline (see scripts/AGENTS.md)
│   ├── run_full_pipeline.py    # Python orchestrator: 9-step pipeline with idempotency
│   ├── generate_level_n.py     # Hierarchical article expansion (1272 lines, most complex)
│   ├── utils/                  # Shared API/embedding/Wikipedia utilities (see scripts/utils/AGENTS.md)
│   ├── tests/                  # Module tests + benchmarks (pytest)
│   └── diagnostics/            # Pipeline verification scripts
├── tests/                      # Root-level integration tests (embedding dims, UMAP, model loading)
├── notes/                      # 63 session notes, implementation plans, troubleshooting guides
├── data/benchmarks/            # Batch size benchmark results
├── embeddings/                 # Generated .pkl embedding files (gitignored, multi-GB)
├── backups/                    # Data backups
└── logos/                      # Logo assets
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Run full pipeline | `scripts/run_full_pipeline.py` | Idempotent; use `--force` flags to rerun steps |
| Simplify questions by level | `scripts/simplify_questions.py --level N` | Levels 2-4 need simplification |
| Shell pipeline (simplify+merge) | `run_full_pipeline.sh` | Only runs simplification + merge, not full generation |
| Generate new difficulty level | `scripts/generate_level_n.py --level N` | LLM-based article suggestion + embedding + questions |
| Heatmap labels (GPT-5-nano) | `scripts/generate_heatmap_labels_gpt5.py` | Uses OpenAI Batch API |
| Heatmap labels (LM Studio) | `scripts/generate_heatmap_labels.py` | Local LLM alternative |
| UMAP rebuild | `scripts/rebuild_umap.py` | 30-60 min for 250K articles |
| Merge levels into final JSON | `scripts/merge_multi_level_data.py` | Deduplicates articles, merges questions by cell |
| OpenAI API integration | `scripts/utils/api_utils.py` | Key in `.credentials/openai.key` |
| Batch API helpers | `scripts/utils/openai_batch.py` | `batch_with_cache()` for cached LLM calls |
| Wikipedia download | `scripts/utils/wikipedia_utils.py` | `download_articles_batch()` |
| Distributed GPU embeddings | `scripts/utils/sync_and_merge_embeddings.py` | SSH/SFTP via paramiko to tensor01/tensor02 |
| Frontend visualization | `index.html` | Served via `python -m http.server 8000` |
| Adaptive sampling logic | `adaptive_sampler_multilevel.js` | `MultiLevelAdaptiveSampler` class |
| Debug pipeline issues | `scripts/diagnostics/diagnose_pipeline.py` | General pipeline diagnostics |
| Verify labels | `scripts/diagnostics/verify_cell_labels.py` | Label quality checks |

## DATA FLOW

```
wikipedia.pkl (250K articles, 752MB, gitignored)
    ↓ rebuild_umap.py
umap_coords.pkl + umap_reducer.pkl + umap_bounds.pkl
    ↓ find_optimal_coverage_rectangle.py
optimal_rectangle.json
    ↓ export_wikipedia_articles.py
wikipedia_articles_level_0.json
    ↓ generate_heatmap_labels_gpt5.py (OpenAI Batch)
heatmap_cell_labels.json (1,521 labels)
    ↓ generate_level_n.py --level 0 (concepts + questions)
level_0_concepts.json + cell_questions_level_0.json
    ↓ generate_level_n.py --level 1..4 (broader articles + questions)
cell_questions_level_{1..4}.json + wikipedia_articles_level_{1..4}.json
    ↓ simplify_questions.py --level {2,3,4}
cell_questions_level_{2,3,4}_simplified.json
    ↓ merge_multi_level_data.py
wikipedia_articles.json + cell_questions.json → consumed by index.html
```

## CONVENTIONS

- **Credentials**: `.credentials/` directory (gitignored). `openai.key` for API, `tensor01.txt`/`tensor02.txt` for clusters.
- **API key validation**: Must start with `sk-` (enforced in `api_utils.py`).
- **macOS env vars**: Scripts set `TOKENIZERS_PARALLELISM=false`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1` to prevent Metal threading issues.
- **TensorFlow pinned**: `tensorflow==2.19.0` — 2.20 has macOS mutex blocking bug.
- **Imports**: Scripts in `scripts/` use `sys.path.append(str(Path(__file__).parent.parent))` to import from `scripts.utils.*`.
- **LLM model**: Pipeline uses `gpt-5-nano` via OpenAI Batch API (cost: ~$0.50/level).
- **Embedding model**: `Qwen/Qwen3-Embedding-0.6B` (distributed) or `google/embeddinggemma-300m` (local).
- **JSON data in root**: Pipeline outputs (`cell_questions*.json`, `wikipedia_articles.json`, etc.) live in project root, not `data/`.
- **Two pipeline scripts**: `run_full_pipeline.sh` (shell, simplification only) vs `scripts/run_full_pipeline.py` (Python, full 9-step pipeline). Use the Python one.
- **Idempotency**: Python pipeline checks for existing outputs and skips steps. Use `--force` to rerun.

## ANTI-PATTERNS (THIS PROJECT)

- **Never commit `.pkl` files** — multi-GB embedding/UMAP files are gitignored. `remove_large_files_from_history.sh` exists to clean mistakes.
- **Never commit `.credentials/`** — API keys, cluster passwords.
- **Never use TensorFlow >= 2.20** — macOS mutex blocking error.
- **Never mock in tests** — project policy requires real API calls, real models, real I/O (see CLAUDE.md instructions).
- **Never use `generate_heatmap_labels.py` in production** — use `generate_heatmap_labels_gpt5.py` (Batch API) instead.
- **Never run `build_wikipedia_knowledge_map.py`** — legacy (nvidia/nemotron). Use `build_wikipedia_knowledge_map_v2.py` or the pipeline.

## COMMANDS

```bash
# Full pipeline (idempotent, skips completed steps)
python scripts/run_full_pipeline.py

# Force rerun everything
python scripts/run_full_pipeline.py --force

# Simplification-only pipeline
./run_full_pipeline.sh

# Single level generation
python scripts/generate_level_n.py --level 2

# Simplify specific level
python scripts/simplify_questions.py --level 4

# Serve visualization
python -m http.server 8000

# Run tests
pytest tests/ scripts/tests/

# Distributed GPU (requires .credentials/)
scripts/launch_distributed.sh
python scripts/utils/sync_and_merge_embeddings.py
```

## NOTES

- `index.html` is a 3591-line monolith — all CSS, JS, and HTML inline. No build system.
- `adaptive_sampler_multilevel.js` is the only extracted JS module. Contains RBF uncertainty estimation math.
- Questions use **LaTeX notation** (`$x^2$`, `$\frac{1}{2}$`) rendered by KaTeX in the frontend.
- LaTeX `$` signs require careful handling to distinguish from currency `$` — see commits d3cc534, 7018ca3, 3ab088c.
- No CI/CD — all testing is manual. No GitHub Actions, no Makefile.
- `notes/` contains 63 implementation logs — useful for understanding decisions but not code reference.
- Cluster config: 2 clusters (tensor01, tensor02) x 8 GPUs = 16 workers. Uses `screen` sessions + `paramiko` SSH.
- License: CC BY-NC-SA 4.0 (non-commercial).

## Active Technologies
- JavaScript ES2020+ (frontend), Python 3.11+ (pipeline) (001-demo-public-release)
- localStorage (browser-side, versioned schema per FR-007 clarification). No server-side storage. (001-demo-public-release)

## Recent Changes
- 001-demo-public-release: Added JavaScript ES2020+ (frontend), Python 3.11+ (pipeline)
