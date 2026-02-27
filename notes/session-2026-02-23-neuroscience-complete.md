# Session Notes — 2026-02-23 Neuroscience Question Generation COMPLETE

## Status: DONE

---

## Result

- **50 neuroscience questions** generated through the full 5-step pipeline
- Written to `data/domains/neuroscience.json` (replacing old 199-question/5-level format)
- Domain metadata, labels (12,100), and articles (3,093) preserved from existing file

### Difficulty Distribution
| Level | Count | Description |
|-------|-------|-------------|
| 1 | 13 | High-level vocabulary |
| 2 | 13 | Low-level vocabulary |
| 3 | 12 | Basic working knowledge |
| 4 | 12 | Deep knowledge |

### Answer Slot Distribution
| Slot | Count |
|------|-------|
| A | 10 |
| B | 10 |
| C | 17 |
| D | 13 |

### Pipeline Summary
- Completed across 2 sessions (2026-02-23), continued from biology completion
- Session 1: Generated concepts (50), completed Step 1 (Generate Q+A) for all 50 questions
- Session 2: Steps 2-5 for all 50, plus Final Assembly
- Cascading parallel pipeline used throughout for efficiency
- Final Assembly: SHA-256 hash IDs, randomized A/B/C/D slots (Fisher-Yates shuffle)

### Key Review Catches

#### Step 2 (Q+A Review)
- **Q2,3,5,6,7,12,13 (L1)**: "Describe X, what's it called?" format was self-answering — flipped to "What is X?" format
- **Q11**: 5-HT chemical name in question served as distinguishing clue — moved to answer
- **Q16**: "almond-shaped" is direct Greek translation of "amygdala" — removed
- **Q17**: "below the thalamus" maps to "hypo-thalamus" — replaced with "diencephalic region"
- **Q22**: "positrons" appeared verbatim in answer — replaced with "matter-antimatter annihilation"
- **Q23**: "huntingtin protein" gives away "Huntington's" — replaced with clinical description
- **Q24**: Etymology clause "grave muscle weakness" spells out myasthenia gravis — removed
- **Q33**: Original answerable by logic alone — completely revised to ACA/MCA vascular territory question
- **Q34**: "vagus" etymology matched description — revised to vagal pharmacology (ACh/M2)
- **Q39**: Etymology in tract name — restructured around Vicq d'Azyr
- **Q42**: "2-3 segments" factual imprecision — broadened to "1-3 segments"
- **Q44**: "fewer than 5%" factually wrong (Penfield & Perot reported 7.7%) — corrected to "about 8%"
- **Q46**: Smoothing question answerable with general statistics — revised to GRF theory
- **Q47**: "7,000 synaptic connections" inaccurate (White 1986: ~5,000 chemical) — corrected

#### Step 4 (Distractor Review)
- **Q4 D2**: "provoked" contradicts "unprovoked" in stem → "recurrent muscle spasms"
- **Q6 D1**: "voluntary" contradicts "reflex" → "learned autonomic responses"
- **Q8 D1**: "excessive" contradicts "interrupted" → replaced with "migraine"
- **Q12 D2**: "magnetic" eliminable via "electro-" prefix → wrong historical purpose
- **Q13 D2**: "muscular" contradicts "brain" in BCI → "amplifying" wrong mechanism
- **Q20 D1**: "Interneurons" contains "neurons" contradicting "non-neuronal" → "Stromal cells (pericytes)"
- **Q24 D3**: Fake-sounding disease name → "Isaac syndrome" (real)
- **Q25 D1**: Golgi literally named in question stem → "Heinrich Wilhelm von Waldeyer"
- **Q30 D1**: "week 8" eliminable (question says 6 weeks too late) → "week 3"
- **Q33 D2**: Foot on lateral contradicts stem's "medial surface" → fixed
- **Q35 D2**: SSRI acronym reveals "dopamine" error → changed approach
- **Q36 D2/D3**: Logic contradictions in split-brain scenario → revised
- **Q39 D2/D3**: Etymology issues in Papez circuit tract naming → fixed
- **Q40 D2**: Stem mentions AQP4, distractor allowed stem-cue matching → NMDAR-IgG
- **Q44 D1/D2**: "experiential/psychical" may be actual Penfield terms → "associative/perceptual"
- **Q45 D1/D2**: Sulcal contradiction and etymology issue → fixed
- **Q50 D2**: "T2" contradicts "T1-weighted" in stem → "T1 hypointensity"

### Concept Overlap Avoidance
- 50 neuroscience concepts verified to have zero overlap with:
  - 182 cognitive-neuroscience sub-domain concepts
  - 168 neurobiology sub-domain concepts
  - 161 computational-neuroscience sub-domain concepts

### Files
- Final output: `data/domains/neuroscience.json`
- Working checkpoint: `data/domains/.working/neuroscience-questions.json` (50 questions, pre-assembly format)
- Concepts list: `data/domains/.working/neuroscience-concepts.json`

### Next Steps
- Questions do NOT have x/y/z coordinates yet — need embedding pipeline
- Next domains to generate: `mathematics` (Batch 1 remaining), or sub-domains for biology/neuroscience/art-history (parents all done)
- Updated plan: `notes/question-generation-plan.md` — 12 domains remaining
