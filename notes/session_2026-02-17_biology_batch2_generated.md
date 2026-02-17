# Session Notes: Biology Batch 2 Generated

**Date:** 2026-02-17
**Task:** Generate biology batch 2 questions (30 questions, Q21-Q50)

## What Was Done

1. **Fixed physics batch2 length balance** — all 30 questions now have {1:8, 2:8, 3:7, 4:7} rank distribution with 26.7%/23.3% strategy accuracy. Fixed critical topic-mismatch bugs where shifted index mapping caused wrong-domain distractors for Q33-Q48.

2. **Generated biology batch2** — 30 questions across 5 difficulty levels (6 per level), covering:
   - L1: ATP synthase, osmosis, trophic efficiency, silent mutations, binary fission, convergent evolution
   - L2: Hardy-Weinberg, electron transport chain, neurotransmitter clearance, PCR, Hamilton's rule, r/K selection
   - L3: RNA splicing/introns, sympatric speciation, apoptosis/efferocytosis, telomere biology, microbiome tolerance, Red Queen hypothesis
   - L4: Histone acetylation, Hox gene collinearity, minimal genome project, island biogeography, LLPS/phase separation, evo-devo toolkit
   - L5: RNA world hypothesis, neutral theory/molecular clock, CRISPR adaptive immunity, transgenerational epigenetics, HGT phylogenetics, hydrogen hypothesis

3. **All schema/answer/difficulty validations pass** — but LENGTH BALANCE needs fixing (93.3% pick-longest, same bias as physics batch2 before fix).

## Current State

- `/tmp/biology_batch2_questions.json` — 30 questions, schema valid, needs length-balance fix
- `/tmp/originals/biology_batch2_questions.json` — backup of original

## What Needs To Be Done Next

### Immediate:
1. **Fix biology batch2 length balance** — same process as physics batch2 fix:
   - Assign ranks: 8+8+7+7 for 30 questions
   - Rewrite distractors to achieve target ranks
   - CRITICAL: Verify each distractor matches its question's topic (lesson from physics batch2)
   - Use `/tmp/fix_physics_batch2.py` as template

### After biology batch2 length fix:
2. Generate batch 2 for remaining 16 domains (30q each)
3. Generate "all" domain (50q)
4. Merge, embed, export, deploy

## Remaining Domains (batch 2 needed):
- mathematics, neuroscience, art-history
- astrophysics, quantum-physics
- european-art-history, chinese-art-history
- molecular-cell-biology, genetics
- cognitive-neuroscience, computational-neuroscience, neurobiology
- calculus, linear-algebra, number-theory, probability-statistics

## Key Lessons
- **Topic-mismatch bug is the #1 risk** during distractor expansion. ALWAYS verify `qs[index]['question_text']` before writing distractors.
- **Answer position errors are common** when generating questions without checking each one against the expected position pattern. Use a validation script immediately after generation.
- **Two missing questions** happened because I lost count — always verify question count matches 30 before proceeding.
- The option-swapping fix (for answer positions) works cleanly and doesn't introduce errors.
