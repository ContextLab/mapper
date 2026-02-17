# Session Notes: All 18 Batch 1 Files Length-Balanced

**Date:** 2026-02-17
**Branch:** 001-demo-public-release

## Accomplishment

All 18 batch1 question files (360 total questions) are now perfectly length-balanced:

- Rank distribution: {1:5, 2:5, 3:5, 4:5} for every file
- "Pick longest" strategy accuracy: 25% (chance) for every file
- "Pick shortest" strategy accuracy: 25% (chance) for every file

## Files Fixed This Session (5 remaining from previous sessions)

| Domain | File | Passes | Special Notes |
|--------|------|--------|---------------|
| genetics | `/tmp/genetics_batch1_questions.json` | 3 passes | Standard fix |
| molecular-cell-biology | `/tmp/molecular_cell_biology_batch1_questions.json` | 2 passes | Standard fix |
| cognitive-neuroscience | `/tmp/cognitive_neuro_batch1_questions.json` | 3 passes | Very extreme ratios (2.2-9.7×), needed massive distractor expansion |
| computational-neuroscience | `/tmp/computational_neuro_batch1_questions.json` | 2 passes | Q18 (76 chars) and Q19 (77 chars) had very short correct answers — needed distractors TRIMMED for those |
| number-theory | `/tmp/number_theory_batch1_questions.json` | 3 passes | Q10 (75 chars) and Q18 (60 chars) had very short correct answers |

## Previously Fixed (13 files from earlier sessions)

physics, probability-statistics, european-art-history, linear-algebra, calculus, chinese-art-history, neurobiology, astrophysics, biology, math, neuro, arthistory, quantum-physics

## All 18 Verified Files Location

All in `/tmp/`:
- arthistory_batch1_questions.json
- astrophysics_batch1_questions.json
- biology_batch1_questions.json
- calculus_batch1_questions.json
- chinese_art_history_batch1_questions.json
- cognitive_neuro_batch1_questions.json
- computational_neuro_batch1_questions.json
- european_art_history_batch1_questions.json
- genetics_batch1_questions.json
- linear_algebra_batch1_questions.json
- math_batch1_questions.json
- molecular_cell_biology_batch1_questions.json
- neuro_batch1_questions.json
- neurobiology_batch1_questions.json
- number_theory_batch1_questions.json
- physics_batch1_questions.json
- probability_statistics_batch1_questions.json
- quantum_physics_batch1_questions.json

Originals preserved in `/tmp/originals/`

## Next Steps

1. Fix physics batch2 (30 questions) — needs ~8 per rank instead of 5
2. Generate batch 2 for remaining 17 domains (30q each)
3. Generate "all" domain (50 interdisciplinary questions)
4. Merge batches into 50-question files per domain
5. Compute embedding coordinates
6. Export domain bundles
7. Phases 10-13 (responsive, a11y, compliance, deploy)
