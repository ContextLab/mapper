# Session Notes: Sub-domain Question Generation (Feb 17, 2026)

## Progress — 10 of 13 sub-domain batches complete
- Fixed quantum-physics Q16 artifact ✓
- molecular-cell-biology: 20q validated ✓
- genetics: 20q validated ✓ 
- cognitive-neuroscience: 20q validated ✓
- computational-neuroscience: 20q validated ✓
- neurobiology: 20q validated ✓
- calculus: 20q validated ✓
- linear-algebra: 20q validated ✓
- number-theory: 20q validated ✓
- **probability-statistics: IN PROGRESS**
- european-art-history: NOT STARTED
- chinese-art-history: NOT STARTED

## All Files (in /tmp/)
Previously completed (7 batches):
- physics_batch1_questions.json (20q ✓ APPROVED)
- biology_batch1_questions.json (20q ✓ APPROVED)
- math_batch1_questions.json (20q ✓ APPROVED)
- neuro_batch1_questions.json (20q ✓ APPROVED)
- arthistory_batch1_questions.json (20q ✓ APPROVED)
- astrophysics_batch1_questions.json (20q ✓ VALIDATED)
- quantum_physics_batch1_questions.json (20q ✓ VALIDATED, Q16 fixed)

This session (9 batches):
- molecular_cell_biology_batch1_questions.json (20q ✓)
- genetics_batch1_questions.json (20q ✓)
- cognitive_neuro_batch1_questions.json (20q ✓)
- computational_neuro_batch1_questions.json (20q ✓)
- neurobiology_batch1_questions.json (20q ✓)
- calculus_batch1_questions.json (20q ✓)
- linear_algebra_batch1_questions.json (20q ✓)
- number_theory_batch1_questions.json (20q ✓)

## Answer Position Assignment Pattern
Q1=A, Q2=B, Q3=C, Q4=D (repeating)
Q1-4=L1, Q5-8=L2, Q9-12=L3, Q13-16=L4, Q17-20=L5

## Key Lesson Learned
The #1 recurring error is placing correct content at the "natural" position (often A or C) instead of the pre-assigned position. This requires post-hoc swapping which is error-prone. Common failures:
- Q5 (should be A) often placed at B
- Q9 (should be A) often placed at D  
- Q13 (should be A) often placed at D
- Q17 (should be A) often placed at B or D
- Missing Q16 (D, L4) — consistently forget to include this question

## Remaining
1. probability-statistics (20 questions)
2. european-art-history (20 questions)
3. chinese-art-history (20 questions)
4. Final validation of all 13 sub-domain batches
