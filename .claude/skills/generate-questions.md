# Skill: Generate Domain Questions

Generate high-quality multiple-choice questions for the Knowledge Mapper application.

## When to Use

Use this skill when asked to generate or regenerate questions for a domain (e.g., "generate questions for biology", "regenerate the physics question set").

## Context

Knowledge Mapper is a GP-based knowledge estimation app. Users answer multiple-choice questions positioned on a 2D map of Wikipedia articles. Question quality directly impacts the usefulness of knowledge estimation.

### Current Problems with Questions
- Questions are too long and verbose (avg ~190 chars, options up to 1000 chars)
- Many questions can be answered by logic alone rather than actual knowledge
- Difficulty levels don't clearly separate vocabulary knowledge from deep understanding
- Distractors are often obviously wrong or implausibly long compared to the correct answer

### Target Question Format

```json
{
  "id": "<16-char hex>",
  "question_text": "...",
  "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
  "correct_answer": "A",
  "difficulty": 3,
  "x": 0.224806,
  "y": 0.56408,
  "z": 0.0,
  "source_article": "photosynthesis",
  "domain_ids": ["biology"],
  "concepts_tested": ["photosynthesis", "cellular respiration"]
}
```

### Length Targets
- **Question text**: 50-100 words (roughly 250-600 characters). Concise but specific.
- **Each answer option**: 25-50 words (roughly 125-300 characters). All four options should be similar in length and style.
- **All options must be plausible** to someone without domain expertise.

### Difficulty Levels (1-4)

Assign each of the 50 concepts a difficulty level (roughly equal distribution: ~12-13 per level):

- **Level 1 — High-level vocabulary**: Can someone identify what this concept IS? Tests recognition of major terms and their basic definitions. Someone who has heard of the field can likely answer these.
- **Level 2 — Low-level vocabulary**: Can someone identify specific technical terms, sub-components, or named results within this concept? Tests familiarity with the detailed terminology that practitioners use.
- **Level 3 — Basic working knowledge**: Can someone apply or reason about this concept? Tests understanding that goes beyond definitions — requires knowing how things relate, why they matter, or what happens when you combine them. Cannot be answered through logic alone or rote memorization alone.
- **Level 4 — Deep knowledge**: Can someone handle nuance, edge cases, or cross-cutting implications of this concept? Tests expert-level understanding — subtle distinctions, historical context of discoveries, common misconceptions among practitioners, or non-obvious connections to other concepts. Cannot be answered through logic alone or rote memorization alone.

### Critical Quality Rules

1. **Logic-proof**: A smart person with NO domain knowledge should NOT be able to answer correctly through reasoning alone. Avoid options that are self-contradictory, obviously absurd, or eliminable by logic.
2. **Uniform option length**: All 4 options for a given question must be approximately the same length (within ~30% of each other). The correct answer must NOT be systematically longer or shorter.
3. **Uniform option style**: All 4 options should use the same grammatical structure, level of specificity, and tone. No option should stand out stylistically.
4. **Plausible distractors**: Each distractor must sound reasonable to a non-expert. It should contain real terminology from the domain, not made-up terms.
5. **LaTeX formatting**: Use `$...$` for inline math expressions. Escape dollar signs in non-math contexts. Use proper LaTeX for equations, variables, and mathematical notation.
6. **No giveaways**: Avoid "all of the above", "none of the above", absolute qualifiers ("always", "never") that signal incorrectness, or hedging language ("sometimes", "may") that signals correctness.

## Procedure

IMPORTANT: Use the TodoWrite tool throughout this entire process to track every step and every question. This allows resuming if context runs out.

### Phase 1: Concept Generation

**Step 1.1**: Create the master todo list:

```
TodoWrite([
  { content: "Phase 1: Generate 50 core concepts for {domain}", status: "in_progress", activeForm: "Generating core concepts" },
  { content: "Phase 2: Curate and deduplicate concept list", status: "pending", activeForm: "Curating concept list" },
  { content: "Phase 3: Generate questions (0/50 complete)", status: "pending", activeForm: "Generating questions" },
  { content: "Phase 4: Quality review and validation", status: "pending", activeForm: "Reviewing question quality" },
  { content: "Phase 5: Assemble domain JSON file", status: "pending", activeForm: "Assembling domain JSON" },
])
```

**Step 1.2**: Generate 60 candidate concepts that are central to the domain. For each concept, note:
- The concept name
- A 1-sentence description of why it's central to this domain
- The most relevant Wikipedia article title

**Step 1.3**: Write the candidate list to a working file: `data/domains/.working/{domain-id}-concepts.json`

### Phase 2: Concept Curation

**Step 2.1**: Review the 60 candidates. Remove:
- Duplicates or near-duplicates (e.g., "DNA replication" and "replication of DNA")
- Concepts that are too broad (e.g., "science") or too narrow (e.g., "Figure 3 in Smith et al. 2019")
- Concepts that heavily overlap (keep the more central one)

**Step 2.2**: Rank remaining concepts by centrality to the domain. Keep the top 50.

**Step 2.3**: Assign difficulty levels to the 50 concepts:
- ~12-13 concepts at Level 1 (high-level vocabulary)
- ~12-13 concepts at Level 2 (low-level vocabulary)
- ~12-13 concepts at Level 3 (basic working knowledge)
- ~12-13 concepts at Level 4 (deep knowledge)

Level assignment should reflect how specialized the concept is, NOT how hard the question will be to write. Central, well-known concepts get Level 1-2. Specialized, nuanced concepts get Level 3-4.

**Step 2.4**: Update the working file with the curated, ranked, leveled list.

### Phase 3: Question Generation (per concept)

For EACH of the 50 concepts, follow this sub-procedure. Update TodoWrite after EVERY question:

**Step 3.1 — Research**: Use WebFetch to read the Wikipedia article for this concept:
```
WebFetch({ url: "https://en.wikipedia.org/wiki/{article_title}", prompt: "Summarize the key facts, definitions, relationships, and nuances of {concept}. Focus on what distinguishes expert knowledge from surface knowledge." })
```

**Step 3.2 — Generate question**: Based on the Wikipedia content and the assigned difficulty level, write the question text. Follow the level definitions:
- Level 1: Test recognition of what this concept IS
- Level 2: Test knowledge of specific technical terms within the concept
- Level 3: Test ability to reason about or apply the concept
- Level 4: Test expert-level nuance, edge cases, or cross-cutting connections

The question must be 50-100 words. It must be impossible to answer through logic alone.

**Step 3.3 — Generate correct answer**: Write the correct answer (25-50 words). It must be factually accurate per the Wikipedia article.

**Step 3.4 — Generate distractors**: Generate 3 incorrect options. For EACH distractor:
1. Start from the correct answer
2. Change ONE specific factual claim to make it incorrect
3. Verify the distractor:
   - Uses real domain terminology (not made-up words)
   - Is approximately the same length as the correct answer (within ~30%)
   - Uses the same grammatical structure as the correct answer
   - Would sound plausible to a non-expert
   - Cannot be eliminated through logic alone
4. If the distractor fails any check, regenerate it

**Step 3.5 — Assign option slots**: Randomly assign the correct answer and 3 distractors to slots A, B, C, D. Use a different random arrangement for each question (do NOT always put the correct answer in slot A). Record which slot contains the correct answer.

**Step 3.6 — Self-check**: Before finalizing, verify:
- [ ] Question is 50-100 words
- [ ] Each option is 25-50 words
- [ ] All options are within ~30% length of each other
- [ ] No option is eliminable through logic alone
- [ ] LaTeX is properly formatted (if applicable)
- [ ] The correct answer is factually accurate
- [ ] Each distractor contains exactly one changed factual claim
- [ ] Correct answer slot varies across questions

**Step 3.7 — Update progress**: Update the TodoWrite with current progress:
```
{ content: "Phase 3: Generate questions ({N}/50 complete)", ... }
```

Also write each completed question to the working file incrementally:
`data/domains/.working/{domain-id}-questions.json`

### Phase 4: Quality Review

**Step 4.1**: Read through ALL 50 questions and check for:
- Option length uniformity within each question
- Correct answer position distribution (should be ~even across A/B/C/D)
- No repeated patterns in distractor construction
- LaTeX consistency
- No two questions testing the exact same knowledge

**Step 4.2**: Fix any issues found. Log fixes in TodoWrite.

**Step 4.3**: Verify the correct answer position distribution:
- Count how many times each slot (A/B/C/D) contains the correct answer
- If any slot has fewer than 9 or more than 16, reassign some correct answer slots to balance

### Phase 5: Assembly

**Step 5.1**: Read the existing domain file to preserve the `domain`, `labels`, and `articles` sections:
```
Read({ file_path: "data/domains/{domain-id}.json" })
```

**Step 5.2**: Determine spatial coordinates for each question. Each question needs `x`, `y` coordinates within the domain's region (from index.json). Use the source article's coordinates if available in the articles array, otherwise distribute evenly within the region.

**Step 5.3**: Generate a unique 16-character hex ID for each question:
```python
import hashlib
id = hashlib.md5(f"{domain_id}:{concept}:{question_text[:50]}".encode()).hexdigest()[:16]
```

**Step 5.4**: Assemble the complete domain JSON file with the new questions replacing the old ones. Write to `data/domains/{domain-id}.json`.

**Step 5.5**: Update `data/domains/all.json` — replace the old questions for this domain with the new ones, preserving questions from other domains.

**Step 5.6**: Update `data/domains/index.json` — update the `question_count` for this domain if it changed.

**Step 5.7**: Clean up working files in `data/domains/.working/`.

## Important Notes

- **Checkpointing**: Write progress to `data/domains/.working/` after EVERY question. If context runs out, the next agent can resume from the working files.
- **Model quality**: This skill should be run with Claude Opus for highest question quality. Do NOT use a smaller model.
- **One domain at a time**: Generate questions for one domain per invocation. The caller can invoke this skill in parallel for multiple domains.
- **Preserve coordinates**: If the existing questions have well-placed coordinates near their source articles, try to reuse those coordinates for questions about the same articles.
- **TodoWrite is mandatory**: Every phase transition and every completed question MUST be reflected in TodoWrite. This is non-negotiable for resumability.
