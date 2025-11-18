# Merge Multi-Level Data Script

## Overview

The `scripts/merge_multi_level_data.py` script merges all level outputs (level_0 through level_4) into final unified files for the knowledge map visualization.

## Input Files

The script expects these files in the project root:

```
wikipedia_articles_level_0.json
wikipedia_articles_level_1.json
wikipedia_articles_level_2.json
wikipedia_articles_level_3.json
wikipedia_articles_level_4.json

cell_questions_level_0.json
cell_questions_level_1.json
cell_questions_level_2.json
cell_questions_level_3.json
cell_questions_level_4.json
```

## Output Files

Creates these merged files:

1. **wikipedia_articles.json** - Deduplicated articles from all levels
2. **cell_questions.json** - Merged questions organized by cell coordinates
3. **notes/merge_validation_report.json** - Validation results and statistics

## Usage

```bash
# Run the merge
python scripts/merge_multi_level_data.py

# Or make it executable and run directly
chmod +x scripts/merge_multi_level_data.py
./scripts/merge_multi_level_data.py
```

## Algorithm

### Article Merging

1. Load all `wikipedia_articles_level_{0-4}.json` files
2. Iterate through levels in order (0 → 4)
3. For each article, check if title already seen
4. Keep first occurrence (earliest level) and discard duplicates
5. Save unified list to `wikipedia_articles.json`

**Deduplication Strategy:**
- Articles are identified by `title` field
- First occurrence (lowest level) is kept
- Duplicates from higher levels are discarded
- Preserves all metadata from the kept article

### Question Merging

1. Load all `cell_questions_level_{0-4}.json` files
2. Group cells by coordinates `(gx, gy)`
3. For each unique cell:
   - Keep cell metadata from first occurrence
   - Merge questions from all levels
   - Track which levels contributed questions
4. Save to `cell_questions.json`

**Merging Strategy:**
- Cells are identified by `(gx, gy)` coordinates
- Questions are appended from all levels
- No deduplication of questions (each question may be unique)
- Adds metadata: `num_questions`, `num_levels`, `source_levels`

## Validation

The script performs comprehensive validation:

### Article Validation
- ✓ No duplicate titles
- ✓ Required fields present: `title`, `content`, `url`
- ✓ Valid coordinate ranges (if present): `0 <= x, y <= 1`

### Cell Question Validation
- ✓ No duplicate cells (same gx, gy)
- ✓ Valid coordinate ranges: `0 <= x_min <= x_max <= 1`
- ✓ Required cell fields: `gx`, `gy`, `x_min`, `x_max`, `y_min`, `y_max`
- ✓ Required question fields: `question`, `article_title`
- ✓ All questions have proper metadata

## Output Format

### wikipedia_articles.json

```json
[
  {
    "title": "Article Title",
    "content": "Article text content...",
    "url": "https://en.wikipedia.org/wiki/Article_Title",
    "x": 0.234,
    "y": 0.678,
    "cell_gx": 2,
    "cell_gy": 6,
    "level": 0,
    "parent_cells": [
      {"gx": 1, "gy": 3, "level": 0}
    ]
  }
]
```

### cell_questions.json

```json
{
  "cells": [
    {
      "cell": {
        "gx": 2,
        "gy": 6,
        "level": 1,
        "x_min": 0.2,
        "x_max": 0.3,
        "y_min": 0.6,
        "y_max": 0.7,
        "parent_gx": 1,
        "parent_gy": 3
      },
      "questions": [
        {
          "question": "What is the primary function of...",
          "options": ["A", "B", "C", "D"],
          "correct_index": 2,
          "article_title": "Article Title",
          "article_url": "https://en.wikipedia.org/wiki/..."
        }
      ],
      "num_questions": 15,
      "num_levels": 3,
      "source_levels": [1, 2, 3]
    }
  ],
  "metadata": {
    "merge_info": {
      "num_levels_merged": 5,
      "total_cells": 250,
      "total_questions": 5000,
      "level_stats": { ... }
    }
  }
}
```

## Validation Report

The validation report (`notes/merge_validation_report.json`) contains:

```json
{
  "articles": {
    "total_articles": 1000,
    "duplicate_titles": [],
    "missing_fields": [],
    "invalid_coordinates": [],
    "errors": []
  },
  "cell_questions": {
    "total_cells": 250,
    "total_questions": 5000,
    "duplicate_cells": [],
    "invalid_coordinates": [],
    "missing_cell_fields": [],
    "missing_question_fields": [],
    "errors": []
  },
  "merge_stats": {
    "articles": {
      "0": {"total": 200, "unique": 200, "duplicates": 0},
      "1": {"total": 300, "unique": 250, "duplicates": 50},
      ...
    },
    "cell_questions": {
      "0": {"cells": 50, "questions": 1000},
      ...
    }
  }
}
```

## Example Output

```
Multi-Level Data Merge
============================================================
Base path: /Users/jmanning/mapper.io
Merging levels: 0 to 4

=== Merging Wikipedia Articles ===
Level 0: 200 articles (200 unique, 0 duplicates)
Level 1: 300 articles (250 unique, 50 duplicates)
Level 2: 280 articles (180 unique, 100 duplicates)
Level 3: 150 articles (80 unique, 70 duplicates)
Level 4: 120 articles (70 unique, 50 duplicates)

Total unique articles: 780

=== Merging Cell Questions ===
Level 0: 50 cells, 1000 questions
Level 1: 100 cells, 2000 questions
Level 2: 80 cells, 1600 questions
Level 3: 40 cells, 800 questions
Level 4: 30 cells, 600 questions

Total cells: 250
Total questions: 6000

=== Validating Articles ===
✓ All articles valid

=== Validating Cell Questions ===
✓ All 250 cells and 6000 questions valid

=== Saving Merged Files ===
Saved: /Users/jmanning/mapper.io/wikipedia_articles.json
Saved: /Users/jmanning/mapper.io/cell_questions.json
Saved: /Users/jmanning/mapper.io/notes/merge_validation_report.json

============================================================
MERGE SUMMARY
============================================================

Articles by Level:
  Level 0:   200 total,   200 unique,     0 duplicates
  Level 1:   300 total,   250 unique,    50 duplicates
  Level 2:   280 total,   180 unique,   100 duplicates
  Level 3:   150 total,    80 unique,    70 duplicates
  Level 4:   120 total,    70 unique,    50 duplicates

Questions by Level:
  Level 0:  50 cells,  1000 questions
  Level 1: 100 cells,  2000 questions
  Level 2:  80 cells,  1600 questions
  Level 3:  40 cells,   800 questions
  Level 4:  30 cells,   600 questions

============================================================

✓ MERGE COMPLETED SUCCESSFULLY
   Articles: 780
   Cells: 250
   Questions: 6000
```

## Error Handling

The script handles:
- Missing level files (warns and skips)
- Malformed JSON (reports and skips)
- Missing required fields (validates and reports)
- Duplicate entries (deduplicates or merges as appropriate)
- Invalid coordinate ranges (validates and reports)

Exit codes:
- `0` - Success (no validation errors)
- `1` - Completed with validation errors

## Integration with Pipeline

This script should be run after all level processing is complete:

```bash
# 1. Generate embeddings and subdivide space
python scripts/generate_embeddings_adaptive.py

# 2. Export Wikipedia articles for all levels
for level in {0..4}; do
    python scripts/export_wikipedia_articles.py --level $level
done

# 3. Generate questions for all levels
for level in {0..4}; do
    python scripts/generate_cell_questions.py --level $level
done

# 4. Merge all levels into final files
python scripts/merge_multi_level_data.py

# 5. Use merged files in visualization
# Open index.html or knowledge_map_heatmap.html
```

## Troubleshooting

**Problem:** "Warning: wikipedia_articles_level_X.json not found"
- **Solution:** Run `export_wikipedia_articles.py` for that level first

**Problem:** "Found N duplicate cells"
- **Solution:** Check that each level file has unique cell coordinates

**Problem:** "Found N articles with invalid coordinates"
- **Solution:** Verify embedding generation produced valid normalized coordinates

**Problem:** Merge produces fewer articles than expected
- **Solution:** Check for duplicate titles across levels (expected behavior - duplicates are removed)

## Performance

Expected processing time (approximate):
- 1000 articles: < 1 second
- 5000 questions across 250 cells: < 2 seconds
- Validation: < 1 second

Memory usage scales linearly with data size.

## Future Enhancements

Potential improvements:
- [ ] Support custom output paths
- [ ] Add progress bars for large datasets
- [ ] Support incremental merging (add new levels without reprocessing all)
- [ ] Add article content similarity checking for duplicate detection
- [ ] Export merge statistics to CSV for analysis
- [ ] Support merging from different base directories
