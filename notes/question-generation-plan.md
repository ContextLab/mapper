# Question Generation Plan

## How to Generate Questions for a Domain

Use the `/generate-questions` skill:

```
/generate-questions <domain-id>
```

For example: `/generate-questions biology`

This runs a 5-step iterative pipeline per question:
1. **Generate Q+A** — Fetch Wikipedia article, create question + correct answer
2. **Review Q+A** — Verify factual accuracy, difficulty level, formatting constraints
3. **Generate Distractors** — Create 3 plausible-but-wrong alternatives
4. **Review Distractors** — Ensure distractors aren't eliminable by logic, check word counts
5. **Compile JSON** — Assemble final question object

After all 50 questions complete, **Final Assembly** assigns SHA-256 hash IDs, randomizes A/B/C/D option slots, and writes to `data/domains/<domain-id>.json`.

### Key Details
- Uses Claude Opus for all steps (quality is paramount)
- Questions checkpoint to `data/domains/.working/<domain-id>-questions.json` after each Step 5
- Pipeline can resume from checkpoints if context runs out
- Concepts list is generated first and saved to `data/domains/.working/<domain-id>-concepts.json`
- Output format: **50 questions per domain**, 4 difficulty levels (L1-L4), ~13/13/12/12 distribution
- Questions do NOT get x/y/z coordinates — those come from a separate embedding pipeline

### How Question Aggregation Works
- Every domain file (general, sub, or "all") contains exactly **50 unique questions**
- When a user selects a **general domain** (e.g., "Biology"), they see that domain's 50 questions **plus** questions from all its sub-domains (e.g., genetics, molecular-cell-biology)
- The **"all"** domain has 50 additional questions of its own, plus questions from every domain below it
- This means concepts in a parent domain should NOT overlap with concepts in its children — each level tests distinct knowledge

### Typical Session Cost
- Each domain takes 2-3 sessions (context windows) to complete
- Parallelizing pipeline steps across batches helps throughput

---

## Domain Status

### Already Regenerated (new 4-level format, 50 questions each)
| Domain | Type | Parent | Completed |
|--------|------|--------|-----------|
| `quantum-physics` | sub | physics | 2026-02-20 |
| `astrophysics` | sub | physics | 2026-02-20 |
| `art-history` | general | — | 2026-02-23 |
| `physics` | general | — | 2026-02-23 |
| `biology` | general | — | 2026-02-23 |
| `neuroscience` | general | — | 2026-02-23 |
| `mathematics` | general | — | 2026-02-23 |

### Remaining Domains (old 5-level format, need regeneration)

#### Recommended Order

**Batch 1 — General domains first** (do parents before children so sub-domain concepts don't overlap with parent):

| # | Domain | Old Qs | New Qs | Type | Rationale |
|---|--------|--------|--------|------|-----------|
| ~~1~~ | ~~`neuroscience`~~ | ~~199 (5-level)~~ | ~~→ 50 (4-level)~~ | ~~general~~ | **DONE 2026-02-23** |
| ~~2~~ | ~~`mathematics`~~ | ~~250 (5-level)~~ | ~~→ 50 (4-level)~~ | ~~general~~ | **DONE 2026-02-23** |

**Batch 2 — Biology sub-domains** (parent already done):

| # | Domain | Old format | Type | Rationale |
|---|--------|-----------|------|-----------|
| ~~3~~ | ~~`genetics`~~ | ~~50 (5-level) → 50 (4-level)~~ | ~~sub~~ | **DONE 2026-02-23** |
| ~~4~~ | ~~`molecular-cell-biology`~~ | ~~50 (5-level) → 50 (4-level)~~ | ~~sub~~ | **DONE 2026-02-23** |

**Batch 3 — Neuroscience sub-domains** (parent done; can start anytime):

| # | Domain | Old format | Type | Rationale |
|---|--------|-----------|------|-----------|
| ~~5~~ | ~~`cognitive-neuroscience`~~ | ~~50 (5-level) → 50 (4-level)~~ | ~~sub~~ | **DONE 2026-02-24** |
| 6 | `neurobiology` | 50 (5-level) → 50 (4-level) | sub | Neuroscience sub-domain |
| ~~7~~ | ~~`computational-neuroscience`~~ | ~~50 (5-level) → 50 (4-level)~~ | ~~sub~~ | **DONE 2026-02-24** |

**Batch 4 — Mathematics sub-domains** (after mathematics parent is done):

| # | Domain | Old format | Type | Rationale |
|---|--------|-----------|------|-----------|
| 8 | `calculus` | 50 (5-level) → 50 (4-level) | sub | Mathematics sub-domain |
| 9 | `linear-algebra` | 50 (5-level) → 50 (4-level) | sub | Mathematics sub-domain |
| 10 | `number-theory` | 50 (5-level) → 50 (4-level) | sub | Mathematics sub-domain |
| 11 | `probability-statistics` | 50 (5-level) → 50 (4-level) | sub | Mathematics sub-domain |

**Batch 5 — Art history sub-domains** (parent already done):

| # | Domain | Old format | Type | Rationale |
|---|--------|-----------|------|-----------|
| 12 | `european-art-history` | 50 (5-level) → 50 (4-level) | sub | Parent already regenerated; can start anytime |
| 13 | `chinese-art-history` | 50 (5-level) → 50 (4-level) | sub | Parent already regenerated; can start anytime |

### Why This Order?

1. **Parents before children**: Since selecting a general domain also draws from its sub-domains, concepts must NOT overlap between parent and children. Doing parents first establishes the "taken" concepts so sub-domain generation can avoid them.

2. **Physics, biology, and neuroscience done**: Their sub-domains can be regenerated at any time.

3. **Art-history subs can also start now**: Since `art-history` parent is done.

4. **Within each batch, sub-domains are independent**: Sub-domains under the same parent don't aggregate each other's questions, so they can be generated in any order (or in parallel across sessions).

---

## Total Work Remaining

- **11 domains** to regenerate (all from 5-level → 4-level format)
- **550 questions** to generate (11 × 50)
- **~24-36 sessions** estimated (2-3 sessions per domain)
- After regeneration, the `all.json` domain also needs rebuilding to aggregate all questions
