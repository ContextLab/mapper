# Session Notes: Physics Batch 2 Length-Balance Fix

**Date:** 2026-02-17
**Task:** Fix length bias in physics_batch2_questions.json (30 questions)

## What Was Done

Fixed the answer-length bias in the physics batch 2 file (30 questions, Q21-Q50). All 30 questions had the correct answer as the longest option (100% pick-longest accuracy). After the fix:

- **Rank distribution:** {1: 8, 2: 8, 3: 7, 4: 7} — perfect for 30 questions
- **Pick-longest accuracy:** 26.7% (near chance 25%)
- **Pick-shortest accuracy:** 23.3% (near chance 25%)
- **All correct answers unchanged** from originals
- **All question texts unchanged** from originals
- **All reasoning fields unchanged** from originals

## Critical Bug Found and Fixed

A systematic topic-mismatch bug was discovered during the fix. When writing expanded distractors, my mental mapping of question indices was shifted for questions Q33-Q48. This caused:

- Q33 (Noether's theorem) got displacement current distractors
- Q34 (equipartition) got Noether's theorem distractors
- Q35 (Wien's law) got equipartition distractors
- Q37 (displacement current) got airplane lift distractors
- Q38 (airplane lift) got renormalization distractors
- Q39 (renormalization) got Berry phase distractors
- Q41 (Berry phase) got Kolmogorov distractors
- Q42 (Kolmogorov) got BCS superconductivity distractors
- Q43 (BCS) got Landau order parameter distractors
- Q44 (Landau) got topological insulator distractors
- Q45 (topological insulators) got Kibble-Zurek distractors
- Q46 (Kibble-Zurek) got AdS/CFT distractors
- Q47 (AdS/CFT) got Kondo effect distractors
- Q48 (Kondo effect) got Casimir effect distractors

**Root cause:** Working from an incorrect mental index mapping rather than verifying each question's actual topic before writing distractors.

**Fix:** Created a verified index-to-topic mapping, then rewrote all mismatched distractors with topically appropriate content.

## Lesson Learned

ALWAYS verify `qs[index]['question_text']` before writing distractors for that index. Never rely on mental mapping or labels from a shifted sequence.

## Fix Script

`/tmp/fix_physics_batch2.py` — comprehensive fix script that:
1. Starts from `/tmp/originals/physics_batch2_questions.json`
2. Assigns rank targets: 8+8+7+7 for 30 questions
3. Rewrites distractors with topic-appropriate content
4. Verifies correct answers unchanged
5. Reports rank distribution and strategy accuracy

## Files

- `/tmp/originals/physics_batch2_questions.json` — original backup (DO NOT MODIFY)
- `/tmp/physics_batch2_questions.json` — fixed version (current)
- `/tmp/fix_physics_batch2.py` — fix script

## Next Steps

Generate batch 2 for remaining 17 domains (30 questions each = 510 total). Build length balance in from the start to avoid needing a separate fix pass.
