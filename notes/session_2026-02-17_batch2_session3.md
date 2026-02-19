# Session Notes: Batch 2 Sub-domain Generation (Session 3)
**Date:** 2026-02-17
**Branch:** 001-demo-public-release

## Accomplished This Session

### 1. European-Art-History Batch2 — Length-Balanced ✅
- Fix script from previous session (`/tmp/fix_european_art_batch2.py`) was written but hadn't saved (had mismatches)
- Current file was identical to originals (all rank 1)
- Wrote comprehensive fix `/tmp/fix_european_art_comprehensive.py` handling all 22 questions
- Result: {8,8,7,7} ✅, 26.7% pick-longest, 23.3% pick-shortest

### 2. Chinese-Art-History Batch2 — Generated + Length-Balanced ✅
- Generated 30 questions covering: terracotta army, yipin, scroll formats, Huizong's academy, Guo Xi's three distances, lacquerware, Chan painting, Four Wang, silk vs paper, cloisonné, Yangzhou Eccentrics, shi, Wu Daozi, Gu Kaizhi, Dunhuang, cunfa, Bada Shanren, Shanghai School, Fan Kuan, Qingming scroll, garden design, Three Perfections, Huang Gongwang, gu/bone method, fanggu, Southern Song, Daoism, Xu Wei, seal carving, Lingnan School
- Fixed: positions (16 mismatches), difficulties (L1=4→6, L3=7→6, L4=7→6)
- Length-balanced with comprehensive fix script → {8,8,7,7} ✅

### 3. Molecular-Cell-Biology Batch2 — Generated + Length-Balanced ✅
- Generated 29 questions, added Q30 (lysosomes/V-ATPase)
- Topics: glycosylation, gap junctions, cytoskeleton, proteasome, coat proteins, Notch signaling, mitochondrial genome, apoptosis/MOMP, integrins, epigenetics, Hippo pathway, dynamin, telomeres, p53, autophagy, transcriptional bursting, UPR-to-apoptosis, Cajal bodies, R-loops, SAC, stress granules vs P-bodies, epigenome editing, condensin/cohesin, lipid rafts, pioneer factors, Hedgehog/cilium, kinetic proofreading, laminopathies, optogenetics
- Fixed: positions (16), difficulties (L1=4→6 via Q19 L3→L1, L3=7→6 via Q27 L3→L2, Q20 L5→L3)
- Length-balanced → {8,8,7,7} ✅ (1 minor fix for Q1 tie)

### 4. Genetics Batch2 — Generated + Length-Balanced ✅
- Generated 29 questions, added Q30 (autosomal dominant pedigree)
- Topics: epistasis, codominance, linkage/recombination, dihybrid cross, alternative splicing, genetic drift, retrotransposons, lac operon, balancing selection, ChIP-seq H3K27me3, CNV, central dogma/RT, miRNA, epigenetic inheritance, 2R hypothesis, anticipation, LD mapping, lncRNA, phase variation, inversions, DNA damage tolerance, paramutation, genetic heterogeneity, synteny, RNA editing, genetic rescue, CRISPR screens, mosaicism, fitness landscapes
- Fixed: positions (18), difficulties (L1=4→6 via Q11 L3→L1, L5→L3 via Q20)
- Length-balanced → {8,8,7,7} ✅ (4 minor fixes after first pass)

## Current Batch2 Status

| Domain | Status | File |
|--------|--------|------|
| physics | ✅ Complete | `/tmp/physics_batch2_questions.json` |
| biology | ✅ Complete | `/tmp/biology_batch2_questions.json` |
| mathematics | ✅ Complete | `/tmp/math_batch2_questions.json` |
| neuroscience | ✅ Complete | `/tmp/neuro_batch2_questions.json` |
| art-history | ✅ Complete | `/tmp/arthistory_batch2_questions.json` |
| astrophysics | ✅ Complete | `/tmp/astrophysics_batch2_questions.json` |
| quantum-physics | ✅ Complete | `/tmp/quantum_physics_batch2_questions.json` |
| european-art-history | ✅ Complete | `/tmp/european_art_history_batch2_questions.json` |
| chinese-art-history | ✅ Complete | `/tmp/chinese_art_history_batch2_questions.json` |
| molecular-cell-biology | ✅ Complete | `/tmp/molecular_cell_biology_batch2_questions.json` |
| genetics | ✅ Complete | `/tmp/genetics_batch2_questions.json` |
| cognitive-neuroscience | ❌ Pending | — |
| computational-neuroscience | ❌ Pending | — |
| neurobiology | ❌ Pending | — |
| calculus | ❌ Pending | — |
| linear-algebra | ❌ Pending | — |
| number-theory | ❌ Pending | — |
| probability-statistics | ❌ Pending | — |

**7 sub-domains remaining + "all" domain (50 interdisciplinary questions)**

## Proven Workflow Per Domain (Streamlined)

1. Check batch1 topics to avoid overlap
2. Generate 30 questions as JSON (6 per difficulty level)
3. Validate: count=30, no duplicates, domain_id correct
4. Fix answer positions to ABCDABCD... pattern
5. Fix difficulty distribution to exactly 6 per level
6. Save originals backup
7. Write comprehensive length-balance fix script
8. Run fix → verify {8,8,7,7} with 0 mismatches
9. Fix any remaining mismatches (usually 1-4)

## Key Patterns Observed

- Questions are ALWAYS generated with correct answer as longest (rank 1)
- Typical generation shortfall: 28-29 questions instead of 30
- Difficulty distribution typically has too many L4/L5, too few L1
- Position distribution heavily biased toward B (most common correct answer)
- Length-balance fix typically succeeds on first pass for 26-28 of 30 questions
- 1-4 questions usually need a second pass for ties or near-misses

## Remaining After All 950 Questions
- Merge batch1 + batch2 → 50q per domain
- Compute embedding coordinates (question_text + reasoning)  
- Export domain bundles
- Phases 10-13 (responsive, a11y, compliance, deploy)
