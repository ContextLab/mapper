# Multi-Level Knowledge Map Implementation Plan

**Issue:** #13
**Date:** 2025-01-18
**Status:** In Progress

## Overview

This document outlines the complete implementation plan for generating a 5-level hierarchical knowledge map (levels 0-4) using OpenAI's GPT-5-nano Batch API. The goal is to create increasingly abstract conceptual questions by progressively broadening the article context at each level.

## Problem Statement

Current pipeline generates only level-0 questions from Wikipedia articles within an optimal rectangle. We need to:

1. Fit UMAP to ALL 250K Wikipedia articles (not just 25K)
2. Generate multi-level questions using GPT-5-nano (5 levels: 0-4)
3. Use batched and cached API calls for cost efficiency
4. Track parent relationships across levels
5. Merge all levels into final unified outputs

## Cost Analysis

**GPT-5-nano Pricing:**
- Input: $0.05 per 1M tokens
- Cached input: $0.005 per 1M tokens (90% savings)
- Output: $0.40 per 1M tokens

**Estimated Regeneration Cost:** $0.03-$0.05 (via estimate_gpt5nano_cost.py)

**Justification:** Fast regeneration with prompt caching is more cost-effective than 2-3 day UMAP rebuild from scratch.

## UMAP Verification Results

Ran `scripts/verify_umap_consistency.py`:

```
TEST 4: Coordinate Matching
================================================================================

  Maximum difference: 2.14e+00
  Mean difference: 6.88e-01

  ✗ CRITICAL ERROR: Coordinates drifted beyond tolerance
  Maximum drift: 2.14e+00 (tolerance: 1.00e-05)

  This means the UMAP reducer is NOT consistent with saved coordinates
```

**Conclusion:** UMAP rebuild is REQUIRED before proceeding with multi-level generation.

## Architecture

### Data Flow

```
data/wikipedia.pkl (250K articles)
    ↓
[Generate embeddings] (sentence-transformers: all-mpnet-base-v2)
    ↓
embeddings/wikipedia_embeddings.pkl (250K x 768-dim)
    ↓
[Fit UMAP] (n_neighbors=15, min_dist=0.1, metric=cosine)
    ↓
umap_coords.pkl (250K x 2-dim) + data/umap_reducer.pkl
    ↓
[Find optimal rectangle] (maximize article coverage)
    ↓
optimal_rectangle.json + wikipedia_articles_level_0.json
    ↓
[Level 0: Generate labels + questions]
    ↓
heatmap_cell_labels.json + level_0_concepts.json + cell_questions_level_0.json
    ↓
[Levels 1-4: Iterative broadening]
    ↓
wikipedia_articles_level_{1-4}.json + cell_questions_level_{1-4}.json
    ↓
[Merge all levels]
    ↓
wikipedia_articles.json (final) + cell_questions.json (final)
```

### Multi-Level Hierarchy

**Level 0 (Most Specific):**
- Source: Wikipedia articles within optimal rectangle
- Questions: About specific concepts in individual articles
- Example: "What organelle produces ATP in eukaryotic cells?"

**Level 1:**
- Source: Broader articles suggested by GPT-5-nano from level-0 concepts
- Questions: About broader themes connecting multiple level-0 concepts
- Example: "How do cellular energy pathways differ between prokaryotes and eukaryotes?"

**Level 2:**
- Source: Even broader articles from level-1 concepts
- Questions: About general principles and cross-domain connections
- Example: "What are the thermodynamic principles governing biological energy transfer?"

**Level 3:**
- Source: Broader articles from level-2 concepts
- Questions: About fundamental scientific principles
- Example: "How do energy conservation laws apply across biological systems?"

**Level 4 (Most Abstract):**
- Source: Broadest articles from level-3 concepts
- Questions: About universal concepts and interdisciplinary connections
- Example: "What are the universal principles of energy flow in complex systems?"

## Implementation Phases

### Phase 1: Infrastructure (✓ COMPLETED)

**Status:** ✓ Complete

**Outputs:**
- `.credentials/openai.key` - Secure API key storage
- `scripts/utils/api_utils.py` - API key loading and utilities
- `scripts/utils/openai_batch.py` - Batch API workflow
- `scripts/utils/wikipedia_utils.py` - Wikipedia article downloading

**Commit:** fa251b7 - "Add infrastructure for GPT-5-nano multi-level pipeline"

### Phase 2: UMAP Rebuild (IN PROGRESS)

**Goal:** Fit UMAP to ALL 250K articles (not just 25K)

**Tasks:**
1. ✓ Verify data/wikipedia.pkl contains 250K articles
2. ⏳ Generate embeddings for 250K articles (if not exists)
3. ⏳ Fit UMAP on complete dataset
4. ⏳ Save outputs and verify consistency

**Estimated Time:**
- Embedding generation: ~6-8 hours (250K articles @ 30-40 articles/sec)
- UMAP fitting: ~30-60 minutes (250K points)
- Total: ~7-9 hours

**Script:** `scripts/rebuild_umap.py` (modified for 250K articles)

**Outputs:**
- `embeddings/wikipedia_embeddings.pkl` (250K, 768-dim)
- `data/umap_reducer.pkl` (trained UMAP model)
- `data/umap_bounds.pkl` (coordinate bounds)
- `umap_coords.pkl` (250K x 2-dim coordinates)

### Phase 3: Level 0 Generation

**Goal:** Generate optimal rectangle, labels, and level-0 questions

**Tasks:**
1. Find optimal rectangle covering maximum articles
2. Export level-0 articles with metadata
3. Generate heatmap labels using GPT-5-nano (batched)
4. Extract concepts from articles (2-pass with GPT-5-nano)
5. Generate questions from concepts (batched)

**Scripts:**
- `scripts/find_optimal_coverage_rectangle.py`
- `scripts/export_wikipedia_articles.py` (modified)
- `scripts/generate_heatmap_labels_gpt5.py` (NEW - GPT-5-nano version)
- `scripts/generate_cell_questions_gpt5.py` (NEW - GPT-5-nano version)

**Outputs:**
- `optimal_rectangle.json`
- `wikipedia_articles_level_0.json`
- `heatmap_cell_labels.json`
- `level_0_concepts.json` (NEW - includes article titles and text)
- `cell_questions_level_0.json`

**Data Schema Changes:**

**wikipedia_articles_level_0.json:**
```json
{
  "title": "Mitochondria",
  "url": "https://en.wikipedia.org/wiki/Mitochondria",
  "text": "Full article text...",  // NEW
  "excerpt": "Mitochondria are...",
  "x": 0.5,
  "y": 0.7,
  "umap_x": -0.1,
  "umap_y": 8.4,
  "index": 42,
  "level": 0  // NEW
}
```

**level_0_concepts.json:**
```json
{
  "cell_gx": 0,
  "cell_gy": 0,
  "level": 0,
  "articles": [
    {
      "title": "Mitochondria",  // CRITICAL for question generation
      "text": "Full article text...",  // CRITICAL
      "excerpt": "Short excerpt...",
      "concepts": ["cellular respiration", "ATP production"],
      "umap_x": 0.5,
      "umap_y": 0.7,
      "embedding_x": 0.5,  // NEW
      "embedding_y": 0.7   // NEW
    }
  ]
}
```

**cell_questions_level_0.json:**
```json
{
  "cell": {"gx": 0, "gy": 0, "label": "Cellular Energy"},
  "questions": [
    {
      "question": "What organelle produces ATP?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "Mitochondria",
      "correct_index": 0,
      "source_article": "Mitochondria",
      "concepts_tested": ["ATP production"],
      "level": 0,  // NEW
      "embedding_x": 0.5,  // NEW (inherited)
      "embedding_y": 0.7,  // NEW (inherited)
      "umap_x": 0.5,  // NEW
      "umap_y": 0.7   // NEW
    }
  ]
}
```

### Phase 4: Multi-Level Generation (Levels 1-4)

**Goal:** Generate progressively broader articles and questions

**Algorithm (per level n = 1-4):**

```python
for level in range(1, 5):
    # Step 1: Suggest broader articles from previous level concepts
    previous_concepts = load(f'level_{level-1}_concepts.json')

    batch_requests = []
    for cell in previous_concepts:
        for article in cell['articles']:
            for concept in article['concepts']:
                # Request: Suggest 1-3 broader Wikipedia articles
                batch_requests.append({
                    'custom_id': f'level_{level}_suggest_{article["title"]}_{concept}',
                    'user_prompt': f'''
                        Concept: "{concept}"
                        Source article: "{article["title"]}"

                        Suggest 1-3 broader Wikipedia article titles that:
                        1. Cover "{concept}" from a more general perspective
                        2. Connect to broader themes/principles
                        3. Are more abstract than "{article["title"]}"
                    '''
                })

    # Submit batch to GPT-5-nano
    suggestions = batch_with_cache(client, batch_requests, system_prompt=...)

    # Step 2: Download suggested articles
    titles = extract_unique_titles(suggestions)
    articles = download_articles_batch(titles)

    # Step 3: Generate embeddings and project to UMAP
    embeddings = model.encode([a['text'] for a in articles])
    coords = umap_reducer.transform(embeddings)

    # Step 4: Save articles with level metadata
    for article, coord in zip(articles, coords):
        article['level'] = level
        article['embedding_x'] = coord[0]
        article['embedding_y'] = coord[1]
        article['parent_concepts'] = [...]  # Track which concepts led to this
        article['parent_articles'] = [...]  # Track source articles

    save(f'wikipedia_articles_level_{level}.json', articles)

    # Step 5: Extract concepts (batched GPT-5-nano)
    concepts = extract_concepts_batched(articles)
    save(f'level_{level}_concepts.json', concepts)

    # Step 6: Generate questions (batched GPT-5-nano)
    questions = generate_questions_batched(concepts)

    # Add level metadata
    for q in questions:
        q['level'] = level
        q['parent_questions'] = [...]  # Questions from parent concepts
        q['parent_concepts'] = [...]
        # Inherit coordinates from source article
        q['embedding_x'] = source_article['embedding_x']
        q['embedding_y'] = source_article['embedding_y']

    save(f'cell_questions_level_{level}.json', questions)
```

**Scripts:**
- `scripts/generate_level_n.py` (NEW - multi-level generation)
- Uses `scripts/utils/openai_batch.py` for all API calls
- Uses `scripts/utils/wikipedia_utils.py` for article downloads

**Outputs (per level 1-4):**
- `wikipedia_articles_level_{n}.json`
- `level_{n}_concepts.json`
- `cell_questions_level_{n}.json`

### Phase 5: Merging

**Goal:** Combine all levels into final unified outputs

**Algorithm:**

```python
# Merge articles
all_articles = []
for level in range(5):
    articles = load(f'wikipedia_articles_level_{level}.json')
    all_articles.extend(articles)

# Deduplicate by title (keep earliest level)
unique_articles = deduplicate_by_title(all_articles)

save('wikipedia_articles.json', unique_articles)

# Merge questions
all_questions = []
for level in range(5):
    questions = load(f'cell_questions_level_{level}.json')
    all_questions.extend(questions)

# Group by cell and merge
merged_cells = merge_questions_by_cell(all_questions)

save('cell_questions.json', merged_cells)
```

**Scripts:**
- `scripts/merge_multi_level_data.py` (NEW)

**Outputs:**
- `wikipedia_articles.json` (final - all levels merged)
- `cell_questions.json` (final - all levels merged)

### Phase 6: Testing & Validation

**Tests:**
1. Verify UMAP consistency (zero drift)
2. Check all level files exist and have correct schema
3. Validate parent/child relationships
4. Ensure coordinate inheritance
5. Test merged outputs load correctly
6. Verify question quality (manual spot checks)

**Scripts:**
- `scripts/verify_umap_consistency.py` (existing)
- `scripts/validate_multi_level_data.py` (NEW)

## GPT-5-nano Integration

### Prompt Caching Strategy

All batched API calls use consistent system prompts for maximum caching:

**Concept Extraction Prompt:**
```
You are an expert at extracting key concepts from Wikipedia articles.

For each article, identify 2-4 core concepts that could be tested in
multiple-choice questions. Concepts should be:
- Specific and well-defined
- Suitable for question generation
- Representative of the article's main topics

Return JSON with: {"suitable": bool, "concepts": [str], "reasoning": str}
```

**Question Generation Prompt:**
```
You are an expert at creating high-quality multiple-choice questions.

Given a concept and source article text, generate ONE multiple-choice question that:
- Tests understanding of the concept
- Has 4 plausible options
- Is unambiguous and fact-based
- Suitable for university-level students

Return JSON with question, options, correct_answer, and reasoning.
```

**Article Suggestion Prompt (Levels 1-4):**
```
You are an expert at identifying broader conceptual connections in Wikipedia.

Given a specific concept and source article, suggest 1-3 Wikipedia article titles that:
- Cover the concept from a more general/abstract perspective
- Connect to broader themes or principles
- Are more comprehensive than the source article

Return JSON with: {"suggestions": [{"title": str, "reasoning": str}]}
```

### Batch API Usage

**Benefits:**
- 50% cost reduction vs standard API
- Automatic rate limiting
- 24-hour completion window
- Prompt caching support

**Implementation:**
All API calls use `scripts/utils/openai_batch.py`:

```python
from scripts.utils.openai_batch import batch_with_cache
from scripts.utils.api_utils import create_openai_client

client = create_openai_client()

results = batch_with_cache(
    client=client,
    requests=[
        {'custom_id': 'req-1', 'user_prompt': '...'},
        {'custom_id': 'req-2', 'user_prompt': '...'}
    ],
    system_prompt="...",  # Cached across all requests
    model="gpt-5-nano",
    response_format={"type": "json_object"},  # Structured outputs
    description="Concept extraction batch",
    poll_interval=60,  # Check status every 60s
    timeout=3600  # 1 hour max wait
)
```

## File Organization

```
mapper.io/
├── .credentials/
│   └── openai.key                          # ✓ Created (not in git)
├── data/
│   ├── wikipedia.pkl                        # ✓ Exists (250K articles)
│   ├── umap_reducer.pkl                     # ⏳ To rebuild
│   ├── umap_bounds.pkl                      # ⏳ To rebuild
│   └── question_coordinates.pkl             # ⏳ To rebuild
├── embeddings/
│   └── wikipedia_embeddings.pkl             # ⏳ To generate (250K x 768)
├── scripts/
│   ├── utils/                               # ✓ Created
│   │   ├── __init__.py
│   │   ├── api_utils.py
│   │   ├── openai_batch.py
│   │   └── wikipedia_utils.py
│   ├── rebuild_umap.py                      # ⏳ To modify (250K)
│   ├── find_optimal_coverage_rectangle.py   # ✓ Exists
│   ├── export_wikipedia_articles.py         # ⏳ To modify (add level)
│   ├── generate_heatmap_labels_gpt5.py      # ⏳ To create
│   ├── generate_cell_questions_gpt5.py      # ⏳ To create
│   ├── generate_level_n.py                  # ⏳ To create
│   ├── merge_multi_level_data.py            # ⏳ To create
│   └── validate_multi_level_data.py         # ⏳ To create
├── optimal_rectangle.json                   # ⏳ To regenerate
├── wikipedia_articles_level_0.json          # ⏳ To create
├── wikipedia_articles_level_{1-4}.json      # ⏳ To create
├── level_0_concepts.json                    # ⏳ To create
├── level_{1-4}_concepts.json                # ⏳ To create
├── cell_questions_level_0.json              # ⏳ To create
├── cell_questions_level_{1-4}.json          # ⏳ To create
├── wikipedia_articles.json                  # ⏳ Final merged output
├── cell_questions.json                      # ⏳ Final merged output
└── notes/
    └── multi-level-pipeline-implementation.md  # This file
```

## Risks & Mitigation

### Risk 1: UMAP Rebuild Time (~7-9 hours)

**Mitigation:**
- Run overnight
- Use checkpointing for embeddings (save every 10K articles)
- If interrupted, resume from checkpoint

### Risk 2: GPT-5-nano Batch Failures

**Mitigation:**
- Implement retry logic in `openai_batch.py`
- Save batch IDs for manual recovery
- Checkpoint progress (save results incrementally)

### Risk 3: Article Download Rate Limits

**Mitigation:**
- Use conservative delay (0.1s between requests)
- Implement retry with exponential backoff
- Cache downloaded articles to avoid re-fetching

### Risk 4: Memory Usage (250K embeddings)

**Mitigation:**
- Use float32 instead of float64 (halves memory)
- Process in batches if needed
- Monitor memory during UMAP fitting

### Risk 5: Data Consistency

**Mitigation:**
- Validate schemas at each phase
- Run `validate_multi_level_data.py` after each level
- Keep backups of all intermediate outputs

## Timeline Estimate

| Phase | Estimated Time | Dependencies |
|-------|---------------|--------------|
| 1. Infrastructure | ✓ Complete | - |
| 2. UMAP Rebuild | 7-9 hours | Wikipedia.pkl |
| 3. Level 0 Generation | 2-4 hours | UMAP complete |
| 4. Levels 1-4 | 1-2 hours/level | Previous level |
| 5. Merging | 30 minutes | All levels |
| 6. Testing | 1-2 hours | Merged outputs |
| **TOTAL** | **15-22 hours** | - |

**Recommendation:** Run UMAP rebuild overnight, then complete remaining phases the next day.

## Success Criteria

- ✓ UMAP drift < 1e-5 (verified by `verify_umap_consistency.py`)
- ✓ All 5 levels generated successfully
- ✓ Parent/child relationships tracked correctly
- ✓ Coordinate inheritance working
- ✓ Final outputs merge correctly
- ✓ Question quality passes manual spot checks
- ✓ Total cost < $0.10 (GPT-5-nano API calls)

## Next Steps

1. ⏳ **Start UMAP rebuild** (`python scripts/rebuild_umap.py`)
2. ⏳ Monitor embedding generation progress
3. ⏳ Verify UMAP consistency
4. ⏳ Proceed with level 0 generation
5. ⏳ Iterate through levels 1-4
6. ⏳ Merge and validate
7. ⏳ Create pull request for review

## References

- Issue #13: https://github.com/user/mapper.io/issues/13
- UMAP verification: `scripts/verify_umap_consistency.py`
- Cost estimation: `scripts/estimate_gpt5nano_cost.py`
- GPT-5-nano pricing: https://openai.com/pricing
- Original paper: "Text embedding models yield high-resolution insights into conceptual knowledge"
