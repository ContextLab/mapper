# Session Notes: Question Generation Batch 1 — All 5 Domains
**Date:** 2026-02-17
**Branch:** 001-demo-public-release

## Summary
Generated 100 high-quality MCQs across 5 general domains (20 each):
- Physics: `/tmp/physics_batch1_questions.json` (pre-existing from previous session)
- Biology: `/tmp/biology_batch1_questions.json`
- Mathematics: `/tmp/math_batch1_questions.json`
- Neuroscience: `/tmp/neuro_batch1_questions.json`
- Art History: `/tmp/arthistory_batch1_questions.json`

## Quality Standards Applied
- Answer distribution: exactly 5A/5B/5C/5D per batch
- Difficulty distribution: exactly 4 per level (1-5) per batch
- All questions self-contained, conceptual, reasoning-focused
- No "excerpt" references, no trivia, no definitional questions
- Reasoning field explains why correct answer is right AND why each distractor is wrong
- Multiple factual claims verified via Google search

## Fact Checks Performed
- Panofsky's three levels of analysis ✓
- Mongillo et al. 2008 activity-silent working memory ✓
- Bi & Poo 1998 STDP timing rule ✓
- Le Corbusier five points of architecture (1927) ✓
- Vander Heiden et al. 2009 Warburg effect biosynthetic advantage ✓
- Hume-Rothery 59% threshold (verified previous session) ✓
- U-Pb zircon closure ~900°C, K-Ar biotite ~280-340°C (verified previous session) ✓

## Issues Encountered & Fixed
1. **Agent timeout**: task() calls with 20 questions timed out at 600s. All 4 agents failed. Generated directly instead.
2. **Answer placement constraint**: Pre-assigned answers (Q1=A, Q2=B, Q3=C, Q4=D, repeating) required careful option arrangement. Several questions needed restructuring when the naturally correct answer didn't fall at the assigned position.
3. **Thinking artifacts**: Some questions initially had "Wait — I need to restructure..." text in reasoning fields. All cleaned up.
4. **Physics Q20**: Missing `domain_id` field — fixed.
5. **Art History**: Initially only 19 questions — inserted Le Corbusier question as Q16 to reach 20.

## Next Steps
1. Generate sub-domain questions (14 sub-domains × ~20-30 each)
2. Fill each domain to 50 questions
3. Cross-domain consistency review
4. Compute question coordinates from embeddings
5. Export domain bundles
6. User manual review of ALL questions
