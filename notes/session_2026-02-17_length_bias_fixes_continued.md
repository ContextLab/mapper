# Session Notes: Length Bias Fixes (Continued)
**Date**: 2026-02-17
**Branch**: 001-demo-public-release

## Progress

### Batch 1 Length Fix Status (12/18 complete)

| # | Domain | Status | Notes |
|---|--------|--------|-------|
| 1 | physics | ✅ DONE | {5,5,5,5} |
| 2 | probability-statistics | ✅ DONE | {5,5,5,5} |
| 3 | european-art-history | ✅ DONE | {5,5,5,5} |
| 4 | linear-algebra | ✅ DONE | {5,5,5,5} |
| 5 | calculus | ✅ DONE | {5,5,5,5} |
| 6 | chinese-art-history | ✅ DONE | {5,5,5,5} |
| 7 | neurobiology | ✅ DONE | {5,5,5,5} - needed pass 1 + pass 2 + Q20 B tweak |
| 8 | astrophysics | ✅ DONE | {5,5,5,5} - needed pass 1 + Q1/Q8 fix |
| 9 | biology | ✅ DONE | {5,5,5,5} - needed pass 1 + Q1/Q10 fix |
| 10 | math | ✅ DONE | {5,5,5,5} - needed pass 1 + Q1 fix |
| 11 | neuro | ✅ DONE | {5,5,5,5} - perfect on first pass |
| 12 | arthistory | ✅ DONE | {5,5,5,5} - perfect on first pass |
| 13 | quantum-physics | ❌ TODO | |
| 14 | genetics | ❌ TODO | |
| 15 | molecular-cell-bio | ❌ TODO | |
| 16 | cognitive-neuro | ❌ TODO | |
| 17 | computational-neuro | ❌ TODO | Q18,Q19 already have short correct answers |
| 18 | number-theory | ❌ TODO | Q10,Q18 already have short correct answers |

## Key Process Notes

### Standard Rank Assignment Template (ALL files use this)
```
Rank 1 (correct longest):     Q3, Q7, Q11, Q16, Q17
Rank 2 (correct 2nd longest): Q1, Q5, Q9, Q13, Q19
Rank 3 (correct 3rd longest): Q2, Q6, Q10, Q14, Q18
Rank 4 (correct shortest):    Q4, Q8, Q12, Q15, Q20
```

### Process for each fix script
1. Read originals from `/tmp/originals/{domain}_batch1_questions.json`
2. Save correct answer text for verification
3. Write replacement dict expanding distractors to achieve target ranks
4. Apply, verify correct answers unchanged
5. Write output, report rank distribution
6. If 1-3 questions off, do a targeted second pass

### Common Issues
- Q1 is tricky: needs rank 2 (exactly 1 distractor above), easy to overshoot to rank 3 or 4
- When all distractors are very short vs correct, need to expand 1-3 distractors substantially
- Always verify distractor content matches question topic (avoid cross-domain mixups)

## Remaining Work After Length Fixes
1. Fix physics batch2 (30q)
2. Generate batch 2 for 17 remaining domains (30q each)
3. Generate "all" domain (50 interdisciplinary questions)
4. Merge batches, compute embeddings, export domain bundles
5. Phases 10-13
