# Session 064: Phase 9 Python Data Pipeline — Complete

**Date**: 2026-02-16
**Branch**: 001-demo-public-release

## What Was Done

### Fixed Question Generation Pipeline (T042)

**Root cause of previous failures (2 issues):**

1. **GPT-5-nano reasoning tokens**: The model uses internal reasoning tokens that consume `max_completion_tokens`. With `max_tokens=2000`, the model would use all tokens for reasoning and return empty `content`. **Fix**: Increased to `max_tokens=8000` for both curation and question generation.

2. **Curation returning too few results**: Sending 500 articles in one prompt overwhelmed the model. **Fix**: Two-stage approach:
   - **Stage 1 (keyword pre-filter)**: Domain-specific keyword lists score articles by relevance. Removed overly generic keywords ("energy", "force", "mass", "field", "wave", "charge", "spin", "decay", "radiation", "nuclear", "particle") that caused false positives.
   - **Stage 2 (batched LLM curation)**: Send keyword-matched articles in batches of 50 to GPT-5-nano for LLM curation. Always run LLM curation (even for <120 candidates) to filter keyword false positives.

### Completed Embedding Generation

- `embeddings/wikipedia_embeddings.pkl`: 250,000 x 768 (google/embeddinggemma-300m)
- 53,582 NaN rows (articles that failed embedding) excluded from PCA
- 196,418 valid embeddings used for PCA z-coordinate computation

### PCA Z-Coordinates

- `data/pca_z_coordinates.json`: 250K title→z mappings
- PC3 explains 1.8% of variance (PC1=2.9%, PC2=1.9%)
- Questions patched: articles found in embedding set get real z; others default to 0.5

### Article Validation

- Fixed `validate_article_existence.py` to retry on HTTP 429 with exponential backoff
- Increased request delay from 50ms to 200ms
- Result: 862 valid, 0 invalid (after removing 5 truly non-existent articles)

### Domain Bundle Export

- All 19 domains exported as JSON bundles to `data/domains/{domain_id}.json`
- Each bundle contains: domain metadata, questions, articles, heatmap labels

## Results

| Domain | Questions | Status |
|--------|-----------|--------|
| all | 50 | ✓ |
| physics | 35 | ✓ |
| neuroscience | 50 | ✓ |
| mathematics | 50 | ✓ |
| art-history | 50 | ✓ |
| biology | 50 | ✓ |
| astrophysics | 50 | ✓ |
| quantum-physics | 50 | ✓ |
| european-art-history | 50 | ✓ |
| chinese-art-history | 50 | ✓ |
| molecular-cell-biology | 49 | ✓ |
| genetics | 43 | ✓ |
| cognitive-neuroscience | 36 | ✓ |
| computational-neuroscience | 42 | ✓ |
| neurobiology | 37 | ✓ |
| calculus | 23 | ✓ |
| linear-algebra | 50 | ✓ |
| number-theory | 49 | ✓ |
| probability-statistics | 48 | ✓ |
| **TOTAL** | **862** | |

## Remaining Work

### Phase 9 (Wrap-up)
- T044: Full pipeline verification (may want to spot-check question quality)
- User review of question quality before proceeding

### Later Phases
- Phase 10 (T045-T047): Responsive + touch
- Phase 11 (T048-T050): Accessibility (WCAG 2.1 AA)
- Phase 12 (T051-T062): Constitution compliance validation
- Phase 13 (T063-T073): Polish + deploy

## Key Technical Learnings

1. **GPT-5-nano is a reasoning model** — always set `max_completion_tokens` to at least 4x your expected output size to account for reasoning tokens.
2. **UMAP regions are NOT topically clustered** — random articles in any region are 95%+ irrelevant to the domain name. Keyword pre-filtering + LLM curation is essential.
3. **Wikipedia rate limits** — 50ms delay triggers 429s. Use 200ms+ with exponential backoff retries.
4. **Embedding NaN values** — ~21% of 250K embeddings had NaN (likely from failed model inference). PCA needs explicit NaN handling.
