# Hierarchical Level System

## Overview

The knowledge map uses a hierarchical level system to progressively expand from specific concepts to broader, more abstract topics. Each level builds on the previous level by identifying conceptually broader Wikipedia articles.

## Level Structure

### Level 0 (Base Level)
- **Source**: Original dataset (cell questions from grid)
- **Concepts**: Extracted from Wikipedia articles near grid cells
- **Questions**: Generated from cell-specific articles
- **Files**:
  - `cell_questions.json` (contains level 0 data)
  - `wikipedia_articles.json` (base articles)

### Level 1 (First Expansion)
- **Source**: Level 0 concepts
- **Process**:
  1. For each level 0 concept, GPT-5-nano suggests 1-3 broader Wikipedia articles
  2. Download suggested articles
  3. Extract concepts from new articles
  4. Generate questions testing conceptual understanding
- **Files**:
  - `wikipedia_articles_level_1.json`
  - `level_1_concepts.json`
  - `cell_questions_level_1.json`

### Level 2 (Second Expansion)
- **Source**: Level 1 concepts
- **Process**: Same as Level 1, but starting from Level 1 concepts
- **Files**:
  - `wikipedia_articles_level_2.json`
  - `level_2_concepts.json`
  - `cell_questions_level_2.json`

### Level 3 (Third Expansion)
- **Source**: Level 2 concepts
- **Files**:
  - `wikipedia_articles_level_3.json`
  - `level_3_concepts.json`
  - `cell_questions_level_3.json`

### Level 4 (Fourth Expansion)
- **Source**: Level 3 concepts
- **Files**:
  - `wikipedia_articles_level_4.json`
  - `level_4_concepts.json`
  - `cell_questions_level_4.json`

## Data Schemas

### Article Schema (Level N)
```json
{
  "title": "Article Title",
  "url": "https://en.wikipedia.org/wiki/...",
  "text": "Full article text...",
  "excerpt": "Brief excerpt...",
  "x": 0.234,
  "y": 0.678,
  "umap_x": -0.108,
  "umap_y": 8.483,
  "embedding": [...],
  "index": 7,
  "parent_concepts": ["concept 1", "concept 2"],
  "parent_articles": ["Source Article 1", "Source Article 2"],
  "parent_reasoning": ["Why this is broader...", "Why this is broader..."]
}
```

### Concept Schema (Level N)
```json
{
  "concept": "Conceptual principle or mechanism",
  "source_article": "Article Title",
  "level": 1,
  "x": 0.234,
  "y": 0.678,
  "parent_concepts": ["level 0 concept 1", "level 0 concept 2"],
  "parent_articles": ["Level 0 Article 1", "Level 0 Article 2"],
  "reasoning": "Why this concept is suitable for testing"
}
```

### Question Schema (Level N)
```json
{
  "question": "Why does X work?",
  "options": {
    "A": "Option A",
    "B": "Option B",
    "C": "Option C",
    "D": "Option D"
  },
  "correct_answer": "B",
  "source_article": "Article Title",
  "x": 0.234,
  "y": 0.678,
  "concepts_tested": ["concept 1", "concept 2"],
  "parent_concepts": ["level N-1 concept 1"],
  "parent_articles": ["Level N-1 Article 1"]
}
```

## Parent Tracking

Each level maintains complete lineage tracking:

1. **Articles** track which concepts/articles from the previous level suggested them
2. **Concepts** track which concepts/articles from the previous level they descended from
3. **Questions** track the full chain of parent concepts and articles

This allows:
- Tracing any question back to its conceptual roots
- Understanding conceptual hierarchies
- Analyzing breadth vs. depth in knowledge expansion

## Usage

### Generate Level 1
```bash
python scripts/generate_level_n.py --level 1
```

### Generate Level 2 (requires Level 1)
```bash
python scripts/generate_level_n.py --level 2
```

### Generate Level 3 (requires Level 2)
```bash
python scripts/generate_level_n.py --level 3
```

### Generate Level 4 (requires Level 3)
```bash
python scripts/generate_level_n.py --level 4
```

## Checkpointing

The script saves checkpoints at key stages:
- `checkpoints/level_{N}_after_download.json` - After downloading articles
- `checkpoints/level_{N}_after_umap.json` - After UMAP projection
- `checkpoints/level_{N}_after_concepts.json` - After concept extraction
- `checkpoints/level_{N}_final.json` - Final state

To resume from checkpoint:
```bash
python scripts/generate_level_n.py --level 1
```

To start fresh (ignore checkpoints):
```bash
python scripts/generate_level_n.py --level 1 --no-resume
```

## Algorithm Details

### Article Suggestion (Step 1)
- **Input**: Level N-1 concepts + source articles
- **Process**: GPT-5-nano batch API suggests 1-3 broader articles per concept
- **Output**: Deduplicated list of article titles with parent tracking

### Article Download (Step 2)
- **Input**: Article titles
- **Process**: Wikipedia API downloads with validation (min 500 chars)
- **Output**: Articles with parent_concepts and parent_articles fields

### Embedding & Projection (Step 3)
- **Input**: Article texts
- **Process**:
  1. Generate embeddings using sentence-transformers
  2. Project to UMAP space using pre-fitted reducer
  3. Normalize coordinates to [0, 1]
- **Output**: Articles with x, y, embedding fields

### Concept Extraction (Step 4)
- **Input**: Articles
- **Process**: GPT-5-nano batch API extracts 1-3 testable concepts per article
- **Output**: Concept list with parent tracking

### Question Generation (Step 5)
- **Input**: Articles + extracted concepts
- **Process**: GPT-5-nano batch API generates conceptual questions
- **Output**: Questions testing "why/how" understanding (not "what/when" facts)

### Save (Step 6)
- **Input**: Articles, concepts, questions
- **Output**: Three JSON files per level

## Quality Criteria

### Articles
- Minimum 500 characters
- Not disambiguation pages
- Not lists/indices
- Contains conceptual content

### Concepts
- Tests principles/mechanisms (not facts)
- Supports "why/how" questions
- Has clear reasoning

### Questions
- Completely self-contained (no references to source)
- Tests conceptual understanding (not memorization)
- Has 4 plausible options with clear correct answer
- Expert-level OK if testing principles

## Cost Estimates

Using GPT-5-nano batch API (50% discount):

**Level 1 (from 513 level 0 concepts)**:
- Article suggestions: ~513 requests × 500 tokens = 256K tokens
- Concept extraction: ~1,500 articles × 400 tokens = 600K tokens
- Question generation: ~500 suitable articles × 500 tokens = 250K tokens
- **Total**: ~1.1M tokens (~$0.55 with batch discount)

**Subsequent levels**: Costs scale with number of concepts generated at previous level

## Notes

- All API calls use batch processing with prompt caching for efficiency
- Checkpoints enable resuming from failures
- Parent tracking maintains full conceptual lineage
- UMAP projection uses pre-fitted model to maintain consistency with base map
