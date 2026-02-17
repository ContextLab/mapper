# Session: Batch 2 Question Generation Progress
**Date:** 2026-02-17
**Status:** In Progress

## Completed This Session

### Biology Batch2 — DONE ✅
- `/tmp/biology_batch2_questions.json` — 30 questions, length-balanced {8,8,7,7}
- Pick-longest: 26.7%, Pick-shortest: 23.3%
- Two-pass fix was needed (first pass had 12 mismatches)

### Mathematics Batch2 — DONE ✅
- `/tmp/math_batch2_questions.json` — 30 questions, length-balanced {8,8,7,7}
- Pick-longest: 26.7%, Pick-shortest: 23.3%
- Required position fix script + two-pass length fix
- Added Q50 (abc conjecture)

### Neuroscience Batch2 — GENERATED, NEEDS LENGTH FIX ⏳
- `/tmp/neuro_batch2_questions.json` — 30 questions with correct positions
- `/tmp/originals/neuro_batch2_questions.json` — backup saved
- Current rank distribution: {1:19, 2:7, 3:3, 4:1} — VERY biased
- Needs comprehensive distractor rewriting

## Overall Batch2 Status

| Domain | Generated? | Position-Fixed? | Length-Balanced? |
|--------|-----------|----------------|-----------------|
| physics | ✅ | ✅ | ✅ {8,8,7,7} |
| biology | ✅ | ✅ | ✅ {8,8,7,7} |
| mathematics | ✅ | ✅ | ✅ {8,8,7,7} |
| neuroscience | ✅ | ✅ | ❌ needs fix |
| art-history | ❌ | — | — |
| astrophysics | ❌ | — | — |
| quantum-physics | ❌ | — | — |
| european-art-history | ❌ | — | — |
| chinese-art-history | ❌ | — | — |
| molecular-cell-biology | ❌ | — | — |
| genetics | ❌ | — | — |
| cognitive-neuroscience | ❌ | — | — |
| computational-neuroscience | ❌ | — | — |
| neurobiology | ❌ | — | — |
| calculus | ❌ | — | — |
| linear-algebra | ❌ | — | — |
| number-theory | ❌ | — | — |
| probability-statistics | ❌ | — | — |
| "all" (interdisciplinary) | ❌ | — | — |

## Workflow Pattern (Proven)

For each domain:
1. Generate 30 questions as JSON (Q21-Q50, 6 per difficulty level)
2. Validate count (30), positions (ABCDABCD...), difficulties (6×5), domain_id
3. Fix positions with swap script → save to `/tmp/originals/`
4. Run length-balance fix (target {8,8,7,7} rank distribution)
5. Run pass2 fix if needed for remaining mismatches
6. Verify: 0 mismatches, pick-longest ~27%, pick-shortest ~23%

## Common Issues

1. **Missing Q50**: I tend to generate only 29 questions. Always verify count = 30.
2. **Wrong answer positions**: Correct answer gravitates to A/B/C. Need position-swap script.
3. **Difficulty drift**: Questions at boundary levels get wrong difficulty assigned.
4. **Length bias**: Correct answers are ALWAYS longer initially. Need 2-pass fix minimum.
5. **Topic-mismatch**: ALWAYS verify question text before writing fix — never trust index comments.

## Pre-assigned Templates (Same for ALL Domains)

### Answer positions (Q21-Q50):
```
Q21=A Q22=B Q23=C Q24=D Q25=A Q26=B Q27=C Q28=D Q29=A Q30=B
Q31=C Q32=D Q33=A Q34=B Q35=C Q36=D Q37=A Q38=B Q39=C Q40=D
Q41=A Q42=B Q43=C Q44=D Q45=A Q46=B Q47=C Q48=D Q49=A Q50=B
```

### Difficulty levels:
Q21-26=L1, Q27-32=L2, Q33-38=L3, Q39-44=L4, Q45-50=L5

### Rank targets ({8,8,7,7}):
- Rank 1 (8): idx 12,17,19,22,24,27,28,29 → Q33,Q38,Q40,Q43,Q45,Q48,Q49,Q50
- Rank 2 (8): idx 1,5,10,13,15,16,25,26 → Q22,Q26,Q31,Q34,Q36,Q37,Q46,Q47
- Rank 3 (7): idx 2,4,8,9,11,14,23 → Q23,Q25,Q29,Q30,Q32,Q35,Q44
- Rank 4 (7): idx 0,3,6,7,18,20,21 → Q21,Q24,Q27,Q28,Q39,Q41,Q42

## Files Location
- All question files: `/tmp/` (not in repo)
- Originals backup: `/tmp/originals/`
- Fix scripts: `/tmp/fix_{domain}_batch2.py`
- Process doc: `/Users/jmanning/mapper/notes/question_generation_process.md`
