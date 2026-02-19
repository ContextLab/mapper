# scripts/ — Core Pipeline Scripts

## OVERVIEW

Python scripts implementing the 9-step knowledge map generation pipeline: UMAP projection, article export, LLM-based labeling/concept extraction/question generation across 5 difficulty levels, simplification, and merge.

## STRUCTURE

```
scripts/
├── run_full_pipeline.py              # 9-step orchestrator (idempotent, --force flags)
├── generate_level_n.py               # Hierarchical article expansion (1272 lines, most complex)
├── simplify_questions.py             # Two-pass LLM simplification (L2-L4 difficulty targeting)
├── merge_multi_level_data.py         # Deduplicates articles, merges questions by cell
├── generate_heatmap_labels_gpt5.py   # OpenAI Batch API cell labeling (production)
├── generate_heatmap_labels.py        # LM Studio alternative (dev only)
├── generate_cell_labels.py           # KNN interpolation + token recovery labeling
├── generate_cell_questions.py        # Concept extraction + MCQ generation
├── find_optimal_coverage_rectangle.py # Multi-objective 2D region optimization
├── rebuild_umap.py                   # Full 250K UMAP fit (30-60 min)
├── export_wikipedia_articles.py      # Filter articles within optimal rectangle
├── extract_level_0_concepts_gpt5.py  # Level-0 concept extraction via Batch API
├── generate_level_0_questions_gpt5.py # Level-0 question generation via Batch API
├── build_wikipedia_knowledge_map.py  # LEGACY — do not use (nvidia/nemotron)
├── estimate_gpt5nano_cost.py         # Cost estimator for Batch API runs
├── precompute_cell_distances.py      # Cell distance matrix generation
├── verify_umap_consistency.py        # UMAP coordinate validation
├── test_*.py                         # Standalone test/verification scripts
├── utils/                            # Shared utilities (see utils/AGENTS.md)
├── tests/                            # pytest tests + benchmarks
├── diagnostics/                      # Pipeline verification + debugging
├── embeddings/                       # Question embedding generation
├── launch_distributed.sh             # SSH launcher for GPU cluster workers
└── remove_large_files_from_history.sh # Git history cleanup for .pkl files
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Understand pipeline flow | `run_full_pipeline.py` | Read first — maps all 9 steps |
| Add a new difficulty level | `generate_level_n.py` | Uses `batch_with_cache()` from utils |
| Change simplification rules | `simplify_questions.py` | `LEVEL_CONFIG` dict defines per-level targets |
| Change merge/dedup logic | `merge_multi_level_data.py` | Handles article dedup + question cell assignment |
| Debug label quality | `diagnostics/verify_cell_labels.py` | Also `diagnostics/spot_check_labels.py` |
| Debug UMAP issues | `diagnostics/debug_umap_inverse.py` | Also `verify_umap_consistency.py` |
| Run benchmarks | `tests/benchmark_batch_sizes.py` | Results in `data/benchmarks/` |
| Repair embeddings | `tests/test_embedding_repair.py` | Also `test_repair_validation.py` |

## CONVENTIONS

- **Imports**: Use `sys.path.append(str(Path(__file__).parent.parent))` at top to import `scripts.utils.*`.
- **macOS env vars**: Set at module level: `TOKENIZERS_PARALLELISM=false`, `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.
- **LLM calls**: Always via `batch_with_cache()` from `utils/openai_batch.py` — handles caching, retries, Batch API.
- **System prompts**: Defined as module-level constants (e.g., `ARTICLE_SUGGESTION_SYSTEM_PROMPT`).
- **Output format**: LLM responses parsed as pipe-delimited lines (`TITLE|Reasoning`) or structured JSON.
- **Checkpointing**: Long scripts save `*_checkpoint.json` files; resume from checkpoint on restart.
- **LaTeX in questions**: Use `$...$` notation. Must handle `$` vs currency carefully.

## ANTI-PATTERNS

- **Never hardcode API keys** — always load via `utils/api_utils.py`.
- **Never skip simplification for L2-L4** — questions are graduate-level by default, inappropriate for target audiences.
- **Never call OpenAI directly** — always use `batch_with_cache()` for caching and retry handling.
- See also root `AGENTS.md` for project-wide anti-patterns (legacy scripts, `.pkl` commits, TF version).

## NOTES

- `generate_level_n.py` handles levels 0-4 via `--level N` flag. Level 0 processes existing articles; levels 1-4 suggest broader articles.
- `simplify_questions.py` uses two-pass approach: simplify first, generate new if simplification fails readability check.
- `tests/` here are module-specific (embedding repair, vec2text, KNN). Root `tests/` has integration tests.
- `diagnostics/` scripts produce output files (spot checks, neighbor analysis) — not traditional test assertions.
