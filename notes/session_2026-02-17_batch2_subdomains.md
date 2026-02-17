# Session Notes: Batch 2 Sub-domain Generation
**Date:** 2026-02-17
**Task:** Generate batch2 (Q21-Q50) for remaining sub-domains

## Completed This Session

### Art-history batch2 fix
- Fixed duplicate Q50 (iconoclasm question appeared twice)
- Replaced with Clement Greenberg formalism question (L5)
- Length-balanced: {8,8,7,7} rank distribution
- File: `/tmp/arthistory_batch2_questions.json`

### Astrophysics batch2
- Generated 28 questions initially (missing Q49, Q50)
- Added 2 questions: light-year (L1), red giant (L2)
- Changed idx 27 from L5→L4 to fix difficulty distribution (6 per level)
- Position-fixed and length-balanced: {8,8,7,7}
- File: `/tmp/astrophysics_batch2_questions.json`

### Quantum-physics batch2
- Generated 26 questions initially (missing Q27-Q30)
- Added 4 questions: de Broglie wavelength (L1), infinite well (L2), angular momentum addition (L3), variational method (L4)
- Position-fixed and length-balanced: {8,8,7,7}
- File: `/tmp/quantum_physics_batch2_questions.json`

## Discovered Issue: Rank Formula
- The handoff described rank = 4 - longer_count, but this is INVERTED
- CORRECT formula: rank = longer_count + 1
  - Rank 1 = 0 distractors longer = correct is LONGEST
  - Rank 4 = 3 distractors longer = correct is SHORTEST
- All fix scripts updated to use correct formula

## Files Created
- `/tmp/originals/arthistory_batch2_questions.json` (updated with new Q50)
- `/tmp/originals/astrophysics_batch2_questions.json`
- `/tmp/originals/quantum_physics_batch2_questions.json`
- Fix scripts in /tmp/ (can be deleted after verification)

## Overall Batch2 Progress
| Domain | Status | File |
|--------|--------|------|
| physics | ✅ {8,8,7,7} | `/tmp/physics_batch2_questions.json` |
| biology | ✅ {8,8,7,7} | `/tmp/biology_batch2_questions.json` |
| mathematics | ✅ {8,8,7,7} | `/tmp/math_batch2_questions.json` |
| neuroscience | ✅ {8,8,7,7} | `/tmp/neuro_batch2_questions.json` |
| art-history | ✅ {8,8,7,7} | `/tmp/arthistory_batch2_questions.json` |
| astrophysics | ✅ {8,8,7,7} | `/tmp/astrophysics_batch2_questions.json` |
| quantum-physics | ✅ {8,8,7,7} | `/tmp/quantum_physics_batch2_questions.json` |
| european-art-history | ❌ pending | — |
| chinese-art-history | ❌ pending | — |
| molecular-cell-biology | ❌ pending | — |
| genetics | ❌ pending | — |
| cognitive-neuroscience | ❌ pending | — |
| computational-neuroscience | ❌ pending | — |
| neurobiology | ❌ pending | — |
| calculus | ❌ pending | — |
| linear-algebra | ❌ pending | — |
| number-theory | ❌ pending | — |
| probability-statistics | ❌ pending | — |

## Next Steps
1. Generate batch2 for 11 remaining sub-domains (30q each)
2. Generate "all" domain (50 interdisciplinary)
3. Merge batch1 + batch2 → 50q per domain
4. Compute embeddings → UMAP coords → PCA z-coords
5. Export domain bundles
6. Phases 10-13
