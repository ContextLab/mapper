# Session Notes — 2026-02-23 Biology Question Generation COMPLETE

## Status: DONE

---

## Result

- **50 biology questions** generated through the full 5-step pipeline
- Written to `data/domains/biology.json` (replacing old 150-question/5-level format)
- Domain metadata, labels (12,769), and articles (3,078) preserved from existing file

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
| A | 16 |
| B | 10 |
| C | 12 |
| D | 12 |

### Pipeline Summary
- Completed in 1 session (2026-02-23), continued from physics completion
- All 50 questions went through: Generate Q+A → Review Q+A → Generate Distractors → Review Distractors → Compile
- Cascading parallel pipeline used throughout for efficiency
- Final Assembly: SHA-256 hash IDs, randomized A/B/C/D slots

### Key Review Catches

#### Step 2 (Q+A Review)
- **Q8**: Plain English definition too guessable without domain knowledge; revised with domain-specific framing
- **Q9**: "predator" and "prey" in question etymologically give away "predation"; neutralized wording
- **Q11**: "become better suited" is dictionary definition of "adapt"; revised with technical framing
- **Q14**: Etymology hint removed
- **Q17**: "zoologist" → "ecologist" (Paine was primarily an ecologist)
- **Q19**: Mechanistically inaccurate — afterhyperpolarization is because K+ channels are slow to close
- **Q20**: Year 1911 → 1909 (Johannsen introduced terms in 1909 book)
- **Q23**: Added "described" to clarify species count scope
- **Q25**: Pattern "primary producers → primary consumers → ?" too obvious; removed hint
- **Q28**: Pure algebra plug-in → replaced with conceptual question about WHY relatedness matters
- **Q29**: Self-answering (stated outcome in setup); revised scenario
- **Q33**: Etymology hint removed; revised as scenario-based
- **Q34**: Logically derivable from shared bones → revised to require distinguishing homology from analogy
- **Q37**: Negative feedback loop described in question making answer trivial; revised
- **Q38**: N=K trivially deducible; revised to ask about overshoot (N>K)
- **Q44**: "negative frequency-dependent selection" term gives away answer; removed

#### Step 4 (Distractor Review)
- **Q8 D2**: "temporary" contradicts "irreversible" in question → revised to subtle lineage error
- **Q9 D3**: "Mutualism" root word contradicts "killing" → replaced with "Commensalism"
- **Q10 D1**: "unranked" contradicts "hierarchical" → kept "ranked" but with wrong group names
- **Q11 D1**: "acquired" contradicts "inherited" → kept "heritable" with subtle Lamarckian error
- **Q13 D3**: "acquired"+"preconfigured" transparent contradiction → replaced with "humoral immunity"
- **Q14 D2**: "Mutualistic commensalism" self-contradictory → replaced with "Intracellular parasitism"
- **Q18 D3**: Beige adipose tissue IS thermogenic → replaced with "Hepatic thermogenic tissue"
- **Q19 D3**: "depolarization" contradicts "negative shift" → replaced with "Hyperpolarization rebound"
- **Q20 D3**: Mendel obviously predates 1909 → replaced with "Carl Correns"
- **Q22 D1**: "Single" contradicts "two sperm cells" → replaced with "Pseudogamy"
- **Q24 D2**: "Bacterio-" prefix links to bacteria → replaced with "Mycoplasmas"
- **Q25 D2**: "Primary consumers" already defined as level 2 in question → replaced with "Apex predators"
- **Q31 D3**: "Runaway sexual selection" IS a form of intersexual selection → replaced with "Disruptive selection"
- **Q38 D2**: Negative × positive = negative is basic arithmetic → revised biological explanation instead

### Concept Overlap Avoidance
- 50 biology concepts verified to have zero overlap with:
  - 189 genetics sub-domain concepts
  - 192 molecular-cell-biology sub-domain concepts

### Files
- Final output: `data/domains/biology.json`
- Working checkpoint: `data/domains/.working/biology-questions.json` (50 questions, pre-assembly format)
- Concepts list: `data/domains/.working/biology-concepts.json`

### Next Steps
- Questions do NOT have x/y/z coordinates yet — need embedding pipeline
- Next domains to generate: `neuroscience` (Batch 1, #1 remaining) or biology sub-domains (genetics, molecular-cell-biology — parent now done)
- Updated plan: `notes/question-generation-plan.md` — 13 domains remaining
