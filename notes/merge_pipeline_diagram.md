# Multi-Level Data Merge Pipeline

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Level-Specific Processing                     │
└─────────────────────────────────────────────────────────────────┘

Level 0 (50 cells):
  export_wikipedia_articles.py --level 0
    ↓
  wikipedia_articles_level_0.json (200 articles)
    ↓
  generate_cell_questions.py --level 0
    ↓
  cell_questions_level_0.json (50 cells, 1000 questions)

Level 1 (100 cells):
  export_wikipedia_articles.py --level 1
    ↓
  wikipedia_articles_level_1.json (300 articles, 50 duplicates)
    ↓
  generate_cell_questions.py --level 1
    ↓
  cell_questions_level_1.json (100 cells, 2000 questions)

Level 2 (80 cells):
  export_wikipedia_articles.py --level 2
    ↓
  wikipedia_articles_level_2.json (280 articles, 100 duplicates)
    ↓
  generate_cell_questions.py --level 2
    ↓
  cell_questions_level_2.json (80 cells, 1600 questions)

Level 3 (40 cells):
  export_wikipedia_articles.py --level 3
    ↓
  wikipedia_articles_level_3.json (150 articles, 70 duplicates)
    ↓
  generate_cell_questions.py --level 3
    ↓
  cell_questions_level_3.json (40 cells, 800 questions)

Level 4 (30 cells):
  export_wikipedia_articles.py --level 4
    ↓
  wikipedia_articles_level_4.json (120 articles, 50 duplicates)
    ↓
  generate_cell_questions.py --level 4
    ↓
  cell_questions_level_4.json (30 cells, 600 questions)

┌─────────────────────────────────────────────────────────────────┐
│                        MERGE OPERATION                           │
│              merge_multi_level_data.py                           │
└─────────────────────────────────────────────────────────────────┘

Input Files:
  - wikipedia_articles_level_{0-4}.json (1050 articles total)
  - cell_questions_level_{0-4}.json (300 cells total)
    ↓
    ├─── Article Deduplication ───┐
    │    (Keep earliest level)     │
    │                              ↓
    │    780 unique articles → wikipedia_articles.json
    │
    └─── Question Merging ─────┐
         (Merge by cell coords) │
                                ↓
         250 unique cells → cell_questions.json
         6000 total questions

Validation:
  - Check for duplicates
  - Verify coordinates
  - Validate required fields
    ↓
  merge_validation_report.json

┌─────────────────────────────────────────────────────────────────┐
│                    Final Output for Visualization                │
└─────────────────────────────────────────────────────────────────┘

wikipedia_articles.json
  ↓
Used by: index.html, knowledge_map_heatmap.html
Purpose: Display article markers on map

cell_questions.json
  ↓
Used by: Quiz/interaction features
Purpose: Generate questions based on map region
```

## Article Deduplication Example

```
Level 0:
  - "Photosynthesis" (x=0.2, y=0.3) ✓ KEPT
  - "Cell Membrane" (x=0.5, y=0.6) ✓ KEPT

Level 1:
  - "Photosynthesis" (x=0.21, y=0.31) ✗ DUPLICATE (skip)
  - "DNA Replication" (x=0.7, y=0.4) ✓ KEPT

Level 2:
  - "Cell Membrane" (x=0.52, y=0.62) ✗ DUPLICATE (skip)
  - "Mitosis" (x=0.3, y=0.8) ✓ KEPT

Final wikipedia_articles.json:
  - "Photosynthesis" (from Level 0)
  - "Cell Membrane" (from Level 0)
  - "DNA Replication" (from Level 1)
  - "Mitosis" (from Level 2)
```

## Question Merging Example

```
Level 0:
  Cell (2, 3): 20 questions

Level 1:
  Cell (2, 3): 30 questions
  Cell (5, 7): 25 questions

Level 2:
  Cell (2, 3): 15 questions
  Cell (5, 7): 20 questions
  Cell (1, 1): 10 questions

Final cell_questions.json:
  Cell (2, 3): 65 questions (from levels 0, 1, 2)
  Cell (5, 7): 45 questions (from levels 1, 2)
  Cell (1, 1): 10 questions (from level 2)
```

## Cell Metadata Tracking

Each merged cell includes tracking information:

```json
{
  "cell": {
    "gx": 2,
    "gy": 3,
    "level": 0,
    "x_min": 0.2,
    "x_max": 0.3,
    "y_min": 0.3,
    "y_max": 0.4
  },
  "questions": [...],
  "num_questions": 65,
  "num_levels": 3,
  "source_levels": [0, 1, 2]
}
```

This allows you to:
- See which levels contributed questions
- Understand question density per cell
- Track multi-level coverage

## Coordinate Preservation

Articles keep their original coordinates from first occurrence:

```
"Photosynthesis" first appears at Level 0 with (x=0.2, y=0.3)
  → All future occurrences use these coordinates
  → Ensures consistent positioning across visualizations
```

## Performance Characteristics

### Article Merging
- Time Complexity: O(n) where n = total articles across all levels
- Space Complexity: O(m) where m = unique articles
- Deduplication: Hash-based (O(1) lookup)

### Question Merging
- Time Complexity: O(c) where c = total cells across all levels
- Space Complexity: O(u) where u = unique cells
- Lookup: Dictionary-based by (gx, gy) tuple

### Typical Processing Time
- 1000 articles, 5000 questions: < 3 seconds
- Dominated by JSON I/O, not computation

## Error Recovery

If merge fails midway:
1. Check validation report for specific errors
2. Fix source files (level-specific JSONs)
3. Re-run merge (idempotent operation)
4. No partial state - either completes or fails cleanly
