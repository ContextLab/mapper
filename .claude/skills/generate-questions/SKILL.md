---
name: generate-questions
description: "Generate high-quality multiple-choice questions for a Knowledge Mapper domain. Use when asked to generate or regenerate questions for a domain (e.g., 'generate questions for biology', 'regenerate the physics question set'). Accepts a domain name as $ARGUMENTS (e.g., /generate-questions quantum-physics). Runs a 5-step iterative pipeline: generate Q+A → review Q+A → generate distractors → review distractors → compile JSON."
---

# Skill: Generate Domain Questions

Generate high-quality multiple-choice questions for the Knowledge Mapper application using an iterative multi-agent pipeline.

## Arguments

This skill accepts a **domain ID** as `$ARGUMENTS` (e.g., `quantum-physics`, `astrophysics`, `biology`).

If no argument is provided, ask the user which domain to generate questions for.

## When to Use

Use this skill when asked to generate or regenerate questions for a domain (e.g., "generate questions for biology", "regenerate the physics question set").

## Context

Knowledge Mapper is a GP-based knowledge estimation app. Users answer multiple-choice questions positioned on a 2D map of Wikipedia articles. Question quality directly impacts the usefulness of knowledge estimation.

### Working Output Format (per question during generation)

```json
{
  "question_text": "...",
  "correct_answer": "...",
  "distractors": ["...", "...", "..."],
  "difficulty": 3,
  "source_article": "Photosynthesis",
  "domain_ids": ["biology"],
  "concepts_tested": ["photosynthesis", "light-dependent reactions"]
}
```

**Do NOT include during generation**: `id`, `x`, `y`, `z`, `options`, or `correct_answer` slot letter. These are assigned during Final Assembly.

### Formatting Rules
- Questions: **50 words or fewer**
- Responses (correct + distractors): **25 words or fewer** each
- Distractors must be **within 5 words** of the correct response length
- **LaTeX**: All math expressions enclosed in `$...$`
- **Dollar signs**: Literal dollar signs must be expressed as `$\$$` so the display parser handles them correctly (all `$` characters are parsed as LaTeX delimiters)

### Difficulty Levels

- **Level 1 — High-level vocabulary**: Tests knowledge of relevant high-level vocabulary. Can the person identify what this concept IS?
- **Level 2 — Low-level vocabulary**: Tests knowledge of relevant low-level vocabulary. Can the person identify specific technical terms, sub-components, or named results?
- **Level 3 — Basic working knowledge**: Tests working knowledge of the concept. Cannot be answered through logic alone, nor by rote memorization alone.
- **Level 4 — Deep knowledge**: Tests deep knowledge of the concept. Cannot be answered through logic alone, nor by rote memorization alone.

## Procedure

IMPORTANT: Use the **TodoWrite** tool throughout this entire process. Track:
- Each phase of the overall pipeline
- Each individual question through the 5-step generation process

This enables resuming from working files if context runs out.

### Prerequisites

The domain ID comes from `$ARGUMENTS`. The orchestrator provides each question generation with:
- A **CONCEPT** (e.g., "photosynthesis")
- A **WIKIPEDIA ARTICLE** (full text, fetched via WebFetch)
- A **DIFFICULTY LEVEL** (integer 1-4)
- A **DOMAIN ID** (from `$ARGUMENTS`, e.g., "biology")

### Step 1: Generate Question + Correct Answer

**Agent input**: CONCEPT, WIKIPEDIA ARTICLE (full text), DIFFICULTY LEVEL

**Instructions to agent**:

Generate a multiple-choice question and its correct answer for the given concept.

Difficulty level definitions:
- Level 1: Tests knowledge of relevant high-level vocabulary
- Level 2: Tests knowledge of relevant low-level vocabulary
- Level 3: Tests basic working knowledge (cannot answer through logic alone, nor by rote memorization alone)
- Level 4: Tests deep knowledge (cannot answer through logic alone, nor by rote memorization alone)

Constraints:
- Question: 50 words or fewer
- Correct answer: 25 words or fewer
- All LaTeX enclosed in `$...$`
- Literal dollar signs expressed as `$\$$`
- Verify factual accuracy by (a) reading the provided Wikipedia article text and (b) doing additional web searches to resolve ANY ambiguity
- It is CRITICAL to ensure 100% factual accuracy

**Agent output** (JSON):
```json
{
  "question_text": "...",
  "correct_answer": "...",
  "concept": "...",
  "difficulty": 3,
  "source_article": "..."
}
```

### Step 2: Review Question + Correct Answer

**Agent input**: QUESTION, CORRECT ANSWER, DIFFICULTY LEVEL

**Instructions to agent**:

Review this question for quality. Check ALL of the following:

1. Is the question 50 words or fewer?
2. Is the correct answer 25 words or fewer?
3. Are all LaTeX expressions enclosed in `$...$`?
4. Are literal dollar signs expressed as `$\$$`?
5. Does the question actually test at the requested difficulty level?
   - Level 1: Tests knowledge of relevant high-level vocabulary
   - Level 2: Tests knowledge of relevant low-level vocabulary
   - Level 3: Tests basic working knowledge (cannot answer through logic alone, nor by rote memorization alone)
   - Level 4: Tests deep knowledge (cannot answer through logic alone, nor by rote memorization alone)
6. Is the correct answer factually accurate? (Do web searches if unsure)
7. Could a smart person with NO domain knowledge answer this through logic alone? (If yes, revise)

Revise the question and/or answer as needed to pass all checks.

**Agent output** (JSON):
```json
{
  "question_text": "...",
  "correct_answer": "...",
  "revisions_made": ["shortened question from 62 to 48 words", "..."]
}
```

### Step 3: Generate Distractors

**Agent input**: QUESTION, CORRECT ANSWER

**Instructions to agent**:

Generate 3 distractor responses for this multiple-choice question.

Rules:
- Each distractor is created by **modifying the correct answer** so that it is no longer correct
- Distractors must NOT be immediately obviously wrong — they must be logically valid at least superficially and must "read" like a valid response
- Each distractor must be **within 5 words** of the correct answer's word count
- All LaTeX enclosed in `$...$`; literal dollar signs as `$\$$`
- Distractors must use real domain terminology, not made-up terms
- Distractors must be unambiguously wrong to a domain expert

**Agent output** (JSON):
```json
{
  "distractors": [
    "...",
    "...",
    "..."
  ]
}
```

### Step 4: Review Distractors

**Agent input**: QUESTION, CORRECT ANSWER, 3 DISTRACTORS

**Instructions to agent**:

Review the 3 distractor responses for quality. For EACH distractor, check:

1. Is the distractor unambiguously WRONG? (It must be — if there's any way to interpret it as correct, revise it)
2. Is the distractor within 5 words of the correct answer's word count?
3. Is LaTeX formatted correctly (`$...$` for math, `$\$$` for literal dollar signs)?
4. Does the distractor sound plausible to a non-expert? (It must — if it's obviously absurd, revise it)
5. Can the distractor be eliminated through logic alone without domain knowledge? (It must not be — if so, revise it)

Revise any distractors that fail checks.

**Agent output** (JSON):
```json
{
  "distractors": [
    "...",
    "...",
    "..."
  ],
  "revisions_made": ["distractor 2: made less obviously wrong by ...", "..."]
}
```

### Step 5: Compile Final JSON

**Agent input**: All outputs from steps 1-4, plus DOMAIN_ID and CONCEPTS_TESTED

**Instructions to agent**:

Compile the final question JSON for the working file. Do NOT include `id`, `x`, `y`, `z`, `options`, or `correct_answer` slot letter — these are assigned during Final Assembly.

**Agent output** (JSON):
```json
{
  "question_text": "...",
  "correct_answer": "...",
  "distractors": ["...", "...", "..."],
  "difficulty": 3,
  "source_article": "Photosynthesis",
  "domain_ids": ["biology"],
  "concepts_tested": ["photosynthesis", "light-dependent reactions"]
}
```

## TodoWrite Tracking

### Master Todo (created at start)

```
TodoWrite([
  { content: "Generate concepts for $ARGUMENTS", status: "in_progress", activeForm: "Generating concepts" },
  { content: "Questions: 0/50 complete", status: "pending", activeForm: "Generating questions" },
  { content: "Assemble final domain JSON", status: "pending", activeForm: "Assembling domain JSON" },
])
```

### Per-Question Tracking

For each question, update the master todo AND maintain per-question detail:

```
TodoWrite([
  { content: "Generate concepts for $ARGUMENTS", status: "completed", activeForm: "Generating concepts" },
  { content: "Questions: 12/50 complete", status: "in_progress", activeForm: "Generating questions" },
  { content: "Q13 '{concept}': Step 1 generate", status: "in_progress", activeForm: "Generating Q13 question+answer" },
  { content: "Q13 '{concept}': Step 2 review Q+A", status: "pending", activeForm: "Reviewing Q13" },
  { content: "Q13 '{concept}': Step 3 distractors", status: "pending", activeForm: "Generating Q13 distractors" },
  { content: "Q13 '{concept}': Step 4 review distractors", status: "pending", activeForm: "Reviewing Q13 distractors" },
  { content: "Q13 '{concept}': Step 5 compile", status: "pending", activeForm: "Compiling Q13" },
  { content: "Assemble final domain JSON", status: "pending", activeForm: "Assembling domain JSON" },
])
```

## Checkpointing

Write completed questions to `data/domains/.working/$ARGUMENTS-questions.json` after EVERY question completes Step 5. This file is an array of completed question JSONs. If context runs out, the next agent reads this file to know which questions are done and resumes from where it left off.

## Final Assembly (after all 50 questions complete)

After all questions are generated, assemble the final domain JSON file:

### Assembly Steps

1. **Read working file**: `data/domains/.working/$ARGUMENTS-questions.json`
2. **Read existing domain file**: `data/domains/$ARGUMENTS.json` to get the existing `domain`, `labels`, and `articles` arrays
3. **For each question**, assign:
   - **ID**: First 16 hex characters of SHA-256 hash of `question_text`
   - **Option slots**: Randomly assign correct answer and distractors to A/B/C/D slots:
     - Pick a random slot (A, B, C, or D) for the correct answer
     - Fill remaining slots with the 3 distractors in random order
     - Record which slot letter contains the correct answer
4. **Write final domain JSON** to `data/domains/$ARGUMENTS.json`

### Final Domain JSON Structure

```json
{
  "domain": {
    "id": "astrophysics",
    "name": "Astrophysics",
    "parent_id": "physics",
    "level": "sub",
    "region": {
      "x_min": 0.042179,
      "x_max": 0.295656,
      "y_min": 0.413276,
      "y_max": 0.67439
    },
    "grid_size": 70
  },
  "questions": [
    {
      "id": "04a772bcef67e50f",
      "question_text": "What is stellar parallax?",
      "options": {
        "A": "The gravitational bending of light from distant stars...",
        "B": "The redshift observed in a star's light spectrum...",
        "C": "The apparent shift in a nearby star's position against distant background stars...",
        "D": "The dimming of a star's brightness as it passes behind another celestial body..."
      },
      "correct_answer": "C",
      "difficulty": 1,
      "source_article": "Stellar parallax",
      "domain_ids": ["astrophysics"],
      "concepts_tested": ["stellar parallax"]
    }
  ],
  "labels": [...],
  "articles": [...]
}
```

### Assembly Notes

- **x, y, z coordinates** are NOT assigned by this skill — they come from the embedding pipeline
- **Preserve existing data**: Keep the `domain`, `labels`, and `articles` arrays from the existing domain file
- **Replace questions**: The `questions` array is fully replaced with the newly generated questions
- **Randomization**: Option slot assignment must be truly random to prevent position bias in answers

## Important Notes

- **Model**: Use Claude Opus (claude-opus-4-6) for all 5 steps. Question quality is paramount.
- **One domain at a time**: The caller invokes this skill per domain and can parallelize across domains.
- **Factual accuracy is non-negotiable**: Steps 1 and 2 MUST verify facts via the Wikipedia article and web searches. Any ambiguity must be resolved before proceeding.
- **TodoWrite is mandatory**: Every step transition and every completed question MUST be reflected in TodoWrite.
- **No coordinates**: This skill produces question content only. Spatial embedding (x, y, z coordinates) happens in a separate post-processing step.
