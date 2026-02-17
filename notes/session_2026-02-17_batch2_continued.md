# Session: Batch 2 Question Generation - Continued
**Date:** 2026-02-17
**Status:** 4/18 parent+sub domains complete, 14 remaining

## Completed Batch 2 Domains (All Verified ✅)

| Domain | File | Rank Distribution | Pick-longest | Pick-shortest |
|--------|------|-------------------|-------------|---------------|
| physics | `/tmp/physics_batch2_questions.json` | {8,8,7,7} | 26.7% | 23.3% |
| biology | `/tmp/biology_batch2_questions.json` | {8,8,7,7} | 26.7% | 23.3% |
| mathematics | `/tmp/math_batch2_questions.json` | {8,8,7,7} | 26.7% | 23.3% |
| neuroscience | `/tmp/neuro_batch2_questions.json` | {8,8,7,7} | 26.7% | 23.3% |

## Remaining 14 Domains (+ "all" interdisciplinary)

### Parent domain remaining:
- art-history

### Sub-domains:
- astrophysics (parent: physics)
- quantum-physics (parent: physics)
- european-art-history (parent: art-history)
- chinese-art-history (parent: art-history)
- molecular-cell-biology (parent: biology)
- genetics (parent: biology)
- cognitive-neuroscience (parent: neuroscience)
- computational-neuroscience (parent: neuroscience)
- neurobiology (parent: neuroscience)
- calculus (parent: mathematics)
- linear-algebra (parent: mathematics)
- number-theory (parent: mathematics)
- probability-statistics (parent: mathematics)

### Plus "all" domain:
- 50 interdisciplinary questions (different format)

## Proven Workflow Per Domain

### Step 1: Generate 30 questions as JSON
- Write directly to `/tmp/{domain}_batch2_questions.json`
- Use schema: question_text, options{A,B,C,D}, correct_answer, difficulty, concepts_tested, reasoning, domain_id
- **COMMON ERROR**: Generating only 29 questions (forgetting Q50). ALWAYS verify count=30.
- **COMMON ERROR**: Wrong answer positions. Many questions naturally get correct=A or correct=B.
- **COMMON ERROR**: Wrong difficulty assignments at boundaries (L3 leaking into L4, etc.)

### Step 2: Fix positions & validate
Run position-fix script that:
1. Swaps option content to put correct answer at pre-assigned letter
2. Sets correct difficulty level
3. Adds Q50 if missing (idx=29, correct=B, difficulty=5)
4. Saves to originals backup: `/tmp/originals/{domain}_batch2_questions.json`

### Step 3: Length-balance fix (typically 2-4 passes)
- Target rank distribution: {8,8,7,7} for 30 questions
- Rank 1 (correct longest, 8): idx 12,17,19,22,24,27,28,29
- Rank 2 (correct 2nd longest, 8): idx 1,5,10,13,15,16,25,26
- Rank 3 (correct 3rd longest, 7): idx 2,4,8,9,11,14,23
- Rank 4 (correct shortest, 7): idx 0,3,6,7,18,20,21

For each rank target:
- **Rank 1**: ALL 3 distractors must be SHORTER than correct answer
- **Rank 2**: Exactly 1 distractor must be LONGER than correct
- **Rank 3**: Exactly 2 distractors must be LONGER than correct
- **Rank 4**: ALL 3 distractors must be LONGER than correct

Strategy for trimming/expanding distractors:
- To TRIM: Replace with shorter, punchier text that still sounds plausible
- To EXPAND: Add qualifiers, extra clauses, unnecessary detail that sounds authoritative
- NEVER modify the correct answer text
- ALWAYS verify against originals that correct answer hasn't changed

### Step 4: Verify final state
- 0 mismatches
- Rank distribution = {8,8,7,7}
- Pick-longest ≈ 26.7%
- Pick-shortest ≈ 23.3%

## Key Metrics

So far:
- **Batch 1**: 18 domains × 20 questions = 360 questions ✅
- **Batch 2**: 4 domains × 30 questions = 120 questions ✅
- **Total so far**: 480 questions
- **Remaining**: 14 domains × 30 = 420 batch2 + 50 "all" = 470 questions
- **Grand total needed**: 950 questions (19 domains × 50)

## Next Steps (in order)
1. art-history batch2 (30 questions)
2. Sub-domains in order: astrophysics, quantum-physics, calculus, linear-algebra, number-theory, probability-statistics, molecular-cell-biology, genetics, cognitive-neuroscience, computational-neuroscience, neurobiology, european-art-history, chinese-art-history
3. "all" domain (50 interdisciplinary questions)
4. Merge batch1+batch2 → 50q per domain
5. Compute embeddings → UMAP coords → PCA z-coords
6. Export domain bundles
7. Phases 10-13
