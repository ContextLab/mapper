# Session Notes: Phase 9 Completion
**Date**: 2026-02-17 ~17:20 EST
**Branch**: 001-demo-public-release

## Summary

Completed Phase 9 of the demo release pipeline:
1. Generated "all" domain Part 2 (Q26-Q50) — 25 interdisciplinary questions
2. Merged Part 1 + Part 2, saved originals, length-balanced (1 pass + 1 minor fix)
3. Merged batch1+batch2 for all 18 regular domains into 50q files
4. Computed embeddings with `google/embeddinggemma-300m` (768 dims)
5. Projected to 2D coordinates within each domain's region using PCA
6. Computed PCA-3 z-coordinates for 3D transitions
7. Exported all 19 domain bundles matching the contract schema

## Key Decisions

### PCA instead of UMAP for coordinate projection
- UMAP hung on first run (numba JIT compilation + threading issues with 50 points)
- PCA is fast (<1s per domain), deterministic, and produces meaningful 2D layouts
- For 50 points, PCA captures the main variance directions adequately
- Total processing: 13 seconds for all 19 domains (950 questions)

### Script: `scripts/generate_question_coords.py`
- New script that handles the full pipeline: embed → project → z-coords → save
- Uses `google/embeddinggemma-300m` on MPS device
- Embeds `question_text + " " + reasoning` for each question
- Generates deterministic IDs from question text (sha256[:16])
- Outputs to `data/domains/{domain_id}_questions.json`

## Final Stats

- **950 questions** across 19 domains (50 each)
- **All length-balanced**: pick-longest 22-26%, pick-shortest 22-26%
- **All within regions**: every question's x,y falls within its domain's defined region
- **All bundles exported**: `data/domains/{domain_id}.json` with questions, articles, labels
- **Contract compliance**: every bundle has domain info, question_ids, 50 questions with x/y/z, labels, articles

## Files Created/Modified

### New:
- `scripts/generate_question_coords.py` — coordinate generation pipeline
- `data/domains/*.json` — 19 domain bundle files (overwritten with new questions)
- `data/domains/*_questions.json` — 19 question files with coordinates

### Question files in /tmp/:
- `/tmp/merged_domains/*.json` — merged 50q files for all 19 domains
- `/tmp/all_domain_questions.json` — final "all" domain file
- `/tmp/all_domain_part1.json`, `/tmp/all_domain_part2.json` — parts
- `/tmp/originals/all_domain_questions.json` — pre-length-balance backup

## Remaining Work

Phases 10-13 from `specs/001-demo-public-release/tasks.md`:
- Phase 10: Responsive layout
- Phase 11: Accessibility (WCAG 2.1 AA)
- Phase 12: Compliance (licenses, credits)
- Phase 13: Deploy to contextlab.github.io/mapper
