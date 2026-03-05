---
name: audit-questions
description: "Audit and improve existing multiple-choice questions for a Knowledge Mapper domain. Identifies and fixes quality problems: (1a) questions too long/complex, (1b) tests recognition not understanding, (2) distractors varying on non-critical dimensions, (3a) answers guessable from context, (3b) keyword leakage, (3c) cultural/common knowledge giveaway, (3d) definition-as-question. Includes adversarial non-expert test. Accepts a domain name as $ARGUMENTS (e.g., /audit-questions biology). Runs iterative flag-then-fix passes until all questions pass."
---

# Skill: Audit Domain Questions

Audit and improve existing multiple-choice questions for the Knowledge Mapper application. Identifies systematic quality problems across two major categories and rewrites questions to fix them.

## Arguments

This skill accepts a **domain ID** as `$ARGUMENTS` (e.g., `biology`, `physics`, `chinese-art-history`).

If no argument is provided, ask the user which domain to audit.

## When to Use

Use when asked to audit, improve, or fix question quality for a domain (e.g., "audit questions for biology", "fix question quality in physics", "improve chinese-art-history questions").

## Quality Problems to Detect

### Problem 1: Question Too Long or Complex

**Symptom**: Question includes extraneous detail beyond the core concept being tested. Tests reading comprehension instead of conceptual knowledge.

**Detection criteria**:
- Question text exceeds 50 words
- Question contains multiple clauses providing context that effectively gives away the answer
- Question embeds specific data (dates, numbers, names) that aren't essential to testing the concept

**Fix**: Rewrite to be short, simple, and direct. Focus on ONE concept. Maximum 50 words. Strip all extraneous context.

**Example**:
- BAD: "After a meal, rising blood glucose triggers insulin release from pancreatic beta cells. Meanwhile, falling glucose between meals triggers glucagon from alpha cells. How do insulin and glucagon function as an antagonistic hormone pair to maintain glucose homeostasis?" (43 words, but gives away the mechanism)
- GOOD: "How do insulin and glucagon maintain blood glucose homeostasis?" (10 words)

### Problem 1b: Tests Recognition Not Understanding

**Applies to: d2, d3, d4 only.** At d1, basic vocabulary IS the test — asking "what is X?" is appropriate. P1b only flags d1 questions in narrow cases (see below).

**Symptom**: Question asks for pure trivia (symbol lookup, acronym expansion, date, person's name) instead of testing whether the student knows the concept.

**Detection criteria (d2-d4)**:
- Question matches patterns like "What is the symbol for...?", "Who discovered/formulated...?", "What year did...?", "What does [acronym] stand for?"
- The correct answer is a proper noun, symbol, date, or vocabulary term that requires zero conceptual understanding
- A student could answer correctly by memorizing a glossary without understanding any relationships

**Detection criteria (d1 only — narrow)**:
- Only flag if the question is pure trivia with no conceptual content at all: symbol lookups ("What does $c$ stand for?"), acronym expansions ("What does tRNA stand for?"), date recall ("What year was X discovered?")
- Do NOT flag d1 vocabulary questions like "Which molecule stores hereditary information?" — that IS appropriate d1 content

**Fix (d2-d4)**: Rewrite to test understanding. Ask about mechanisms, implications, relationships, or applications.
**Fix (d1)**: Replace pure trivia with a clean vocabulary question that tests whether the student knows what the concept IS, not just its symbol/date/acronym.

**Example (d2+)**:
- BAD: "What does $F = ma$ represent?" → Newton's Second Law (name recall)
- GOOD: "A heavier shopping cart requires more force to accelerate at the same rate. Which law explains this?" → Newton's Second Law
- BAD: "Who formulated the theory of evolution?" → Darwin (person recall)
- GOOD: "Which mechanism causes beneficial traits to become more common over generations?" → Natural selection

**Example (d1 — what to flag vs. what to keep)**:
- FLAG: "What does $c$ stand for?" → Speed of light (pure symbol lookup)
- KEEP: "Which physical constant sets the universe's speed limit?" → Speed of light (clean vocabulary)
- FLAG: "What year was DNA's structure discovered?" → 1953 (date recall)
- KEEP: "Which molecule stores hereditary information?" → DNA (clean vocabulary)

### Problem 2: Distractors Vary on Non-Critical Dimensions

**Symptom**: Options share long common prefixes and differ only in minor details (e.g., "from the mausoleum of..." vs "from the burial complex of..."). This focuses the test on minor distinctions rather than the core concept.

**Detection criteria**:
- 3+ options share a common prefix of 5+ words
- Options differ only in a specific detail embedded in an otherwise identical sentence
- The distinguishing detail tests a narrower concept than the question asks about

**Fix**: Make options SHORT (1-5 words ideally, max 25 words). Each option should be a distinct concept, not a variation on the same sentence. Distractors should be created by modifying the correct answer to be wrong, not by embedding the correct answer in different sentence contexts.

**Example**:
- BAD options for "What ancient funerary sculpture was discovered near Xi'an?":
  - A: "The Terracotta Army, from the mausoleum of Qin Shi Huang"
  - B: "The Terracotta Army, from the funerary temple of Emperor Taizong"
  - C: "The Bronze Guardian Legion, from the mausoleum of Qin Shi Huang"
  - D: "The Terracotta Army, from the burial complex of Emperor Wu of Han"
- GOOD options:
  - A: "Terracotta Army"
  - B: "Jade Burial Suits"
  - C: "Bronze Ritual Vessels"
  - D: "Ceramic Tomb Guardians"

NOTE: Watch for **structural asymmetry** — if the correct answer has a different grammatical form than all distractors (e.g., missing "of LOCATION" suffix), that pattern leaks which option is correct. All options must share the same structure.

### Problem 3a: Answer Guessable from Context

**Symptom**: The correct answer can be identified through pattern-matching without domain expertise. Common patterns:
- A key term appears in 3+ options → it must be in the answer
- The correct option is the "most complete" or "most specific" one
- Eliminating obviously wrong options leaves only one plausible choice
- The question text contains terminology that directly matches only one option

**Detection criteria**:
- A 3-word phrase appears in 3+ options (the shared phrase reveals the answer)
- The correct answer is noticeably longer or more detailed than distractors
- Only the correct answer uses terminology from the question
- A non-expert could eliminate 2+ distractors through logic alone
- **Structural asymmetry**: The correct answer has a different grammatical form than all distractors (e.g., correct = 2 words, all distractors = "X of Y" pattern; or correct lacks a suffix/prefix that all distractors share). This makes the odd-one-out identifiable without domain knowledge.

**Fix**: Ensure all options are equally plausible to a non-expert. All options must share the same grammatical structure and similar length. No option should be distinguishable through pattern-matching.

### Problem 3b: Keyword Leakage

**Symptom**: A distinctive content word from the question text appears in exactly one option, creating an unconscious signal that draws non-experts to the correct answer.

**Detection criteria**:
- Extract content words from the question (excluding stop words like "the", "is", "of", "what", "which")
- Check if any content word appears in exactly 1 of the 4 options
- The leaking word is distinctive (not a generic domain term that would appear everywhere)

**Fix**: Either remove the leaking keyword from the question, or ensure it appears in 0 or 2+ options. Alternatively, restructure the question to avoid the overlap entirely.

**Example**:
- BAD: "What is conserved in an isolated system's *energy* transformations?" → only option A mentions "energy" → keyword leakage
- GOOD: "In an isolated system, which quantity remains constant despite internal changes?" → no keyword overlap with any single option

### Problem 3c: Cultural/Common Knowledge Giveaway

**Symptom**: The correct answer is identifiable through general cultural knowledge without ANY domain study.

**IMPORTANT — calibrate by difficulty**:
- **d1**: Most d1 vocabulary IS culturally familiar — that's fine. Only flag if testing the concept has **zero pedagogical value** because the answer is so universally known it would be pointless in ANY educational context. The test is NOT "could a non-expert guess this?" but "would an intro student learn something by being tested on this?"
  - PASS examples (culturally familiar but pedagogically valuable at d1): DNA, friction, photosynthesis, Newton's laws, cell, gravity, atom, chromosome, ecosystem, classical conditioning, natural selection, electromagnetic spectrum
  - FAIL examples (so universally known that testing has zero value): "What country is the Great Wall in?" → China; "What language is spoken in France?" → French; "What planet do we live on?" → Earth
- **d2-d4**: Flag if the answer is recognizable to someone who has not specifically studied this domain, even if they have general education.

**Detection criteria**:
- **d1**: Would testing this concept be pointless even in an intro course? Is the answer something literally everyone knows regardless of education level? If an intro student could learn from getting this wrong, the question PASSES P3c.
- **d2-d4**: Would someone who has NEVER taken a course in this domain recognize the correct answer through:
  - Pop culture (movies, TV, memes)
  - Everyday English (e.g., "motivation" is an everyday word, not a psychology term)
  - Universally famous names/landmarks (Great Wall, Mona Lisa, Einstein)
- **All levels**: The distractors are obviously fake or implausible compared to the correct answer

**Fix**: Strengthen distractors so all options are real domain terms equally unfamiliar to non-experts. If the concept itself is too famous for the difficulty level, test a less obvious aspect of it.

**Example**:
- BAD: "What ancient trade route connected East and West?" → "Silk Road" is universally known even without domain study
- GOOD: Test a less universally-known aspect, or choose a different topic entirely. If the concept is too famous for the difficulty level, don't just reframe the same concept — pick something that actually requires domain knowledge.
- BAD (d1): "What country is the Great Wall located in?" → "China" — zero pedagogical value, everyone knows this
- GOOD (d1): "What force opposes sliding motion between two surfaces?" → Friction / Drag / Tension / Normal force — culturally familiar concept, but distractors are real physics terms a non-expert cannot easily eliminate. An intro student learns by being tested on this.

### Problem 3d: Definition-as-Question

**Applies to: d2, d3, d4 strictly. At d1, definition-style questions are acceptable** — that is what d1 tests. Only flag d1 if the question is so over-specified that it self-answers (i.e., the definition in the question is so detailed that no domain knowledge is needed to match it to the correct option).

**Symptom (d2-d4)**: The question IS the textbook definition of exactly one option. This is a vocabulary lookup, not a test of understanding.

**Symptom (d1 — narrow)**: The question recites so many identifying details that a non-expert can pattern-match to the answer without knowing the domain term. The question effectively answers itself.

**Detection criteria (d2-d4)**:
- The question text describes a concept so specifically that only one option matches by definition
- Answering correctly requires only knowing what a term means
- The question could be answered by scanning a glossary

**Detection criteria (d1 — narrow)**:
- The question contains 3+ specific identifying details that all point to one option
- Example: "What natural protein fiber, composed mainly of fibroin, produced by Bombyx mori through sericulture, originated in China?" → so over-specified it self-answers

**Fix (d2-d4)**: Ask about the concept's behavior, implications, mechanisms, or applications.
**Fix (d1)**: Trim to 1-2 identifying details. Keep it a clean vocabulary question.

**Example (d1)**:
- BAD: "What natural protein fiber, composed of fibroin, produced by Bombyx mori through sericulture, originated in China?" → over-specified, self-answering
- GOOD: "Which material, produced through sericulture, was ancient China's most valuable export?" → clean d1 vocabulary
- BAD: "What study of heredity and variation uses Mendelian principles to track allele frequencies?" → over-specified for d1
- GOOD: "What is the study of heredity and genetic variation called?" → clean d1 vocabulary

## Adversarial Non-Expert Test

Apply this meta-test to EVERY question, both during audit and after rewriting. But **calibrate the non-expert persona by difficulty level**:

- **d1**: The non-expert has never taken an intro course in this domain. They may have general education and cultural awareness but zero domain-specific study. A d1 question SHOULD be answerable by someone who has completed intro coursework — that is the target audience.
- **d2**: The non-expert has taken an intro course but no further study.
- **d3-d4**: The non-expert has moderate familiarity but not deep expertise.

Test whether the non-expert could score >30% through ANY of these **structural** strategies (these are problems at ALL difficulty levels):

1. **Process of elimination** — obviously wrong distractors that anyone could rule out
2. **Keyword matching** — a distinctive word in the question matches exactly one option
3. **"Most complete" heuristic** — the correct option is noticeably longer, more specific, or more "academic-sounding"
4. **Grammatical cues** — only one option grammatically fits the question stem
5. **Logic alone** — the question's phrasing makes the answer deducible without any domain knowledge (e.g., "perfectly insulated" → energy is conserved)

Strategy 3 from the old list ("famous names/cultural references") is now handled by P3c with proper difficulty calibration. Do NOT double-flag cultural knowledge under the adversarial test — let P3c handle it.

If ANY structural strategy gives >30% success, flag the specific strategy and require a fix.

## Good-Question Examples by Difficulty Level

Use these as reference. **ALL questions must be 1-2 sentences, 50 words max. ALL options must be 1-3 words.**

**d1 (intro vocabulary)**: Clean, direct vocabulary questions. 1 sentence. Options are 1-3 words.
- GOOD: "Which molecule stores hereditary information?" → DNA / RNA / ATP / Protein
- GOOD: "What force opposes sliding between two surfaces?" → Friction / Drag / Tension / Normal force
- GOOD: "What is the study of heredity called?" → Genetics / Ecology / Anatomy / Pathology
- BAD: "What does tRNA stand for?" → Transfer RNA (pure acronym lookup — flag under P1b)
- BAD: "What natural protein fiber, composed of fibroin, produced by Bombyx mori..." → over-specified, self-answering
- BAD (round-2 overcorrection): "During DNA replication, the enzyme helicase unwinds the double helix. What problem does this create ahead of the replication fork?" → this is d3, not d1. Too long, too specific, options too technical.

**d2 (deeper vocabulary)**: Tests relationships between concepts. 1-2 sentences. Options 1-5 words.
- GOOD: "Which Chinese art tradition values the artist's inner character over visual realism?" → Literati painting / Court painting / Folk art / Buddhist sculpture
- BAD: "What is literati painting called in Chinese?" → Wenrenhua (name recall in a foreign language)

**d3 (working knowledge)**: Applies a concept to a scenario. 1-2 sentences. Options 1-3 words.
- GOOD: "A patient's blood pH drops below 7.35. Which organ system primarily compensates?" → Respiratory / Digestive / Endocrine / Immune
- BAD: "What is the normal blood pH range?" → 7.35-7.45 (fact recall, not application)

**d4 (deep knowledge)**: Synthesizes multiple concepts. 1-2 sentences. Options 1-3 words.
- GOOD: "Why do vortices in a Bose-Einstein condensate have quantized circulation?" → Wavefunction phase constraint / Low viscosity / Repulsive interactions / Angular momentum conservation
- BAD: "Who predicted Bose-Einstein condensates?" → Bose and Einstein (name recall)

## Absolute Format Constraints

These apply to ALL difficulty levels and MUST NOT be violated:

1. **Questions**: 1-2 sentences maximum. 50 words maximum. Clear, direct syntax. No multi-clause scenarios.
2. **Options (ALL levels)**: 1-3 words each. Never sentences. Never explanations.
4. **No difficulty creep**: A rewrite must stay at the same difficulty level. Do NOT turn a d1 vocabulary question into a d3 scenario question.
5. **No over-specification**: If the question contains 3+ clues that all point to one answer, it's self-answering regardless of difficulty level.

## Procedure

IMPORTANT: Use the **TodoWrite** tool throughout this process to track progress.

### Step 0: Load Domain Questions

1. Read `data/domains/$ARGUMENTS.json`
2. Extract the `questions` array
3. Count total questions (should be 50)
4. Create working file at `data/domains/.working/$ARGUMENTS-audit.json` to checkpoint progress

### Step 1: Audit Pass (Flag Issues)

For EACH question, use a Task agent (Opus) to evaluate:

**Agent prompt**: Given this question and its options, evaluate for SEVEN quality checks. **Calibrate each check by difficulty level** — d1 tests intro vocabulary; d2+ tests deeper understanding. For each, give a verdict of PASS or FAIL with a brief explanation.

```
Question: {question_text}
Correct answer: {correct_answer}
Options: {A, B, C, D}
Difficulty: {difficulty}

ABSOLUTE FORMAT CHECK (before all others):
- Is the question 1-2 sentences, under 50 words?
- Are ALL options 1-3 words each?
- If either fails, flag as P1a FAIL immediately.

P1a - Too Long/Complex: Is the question over 50 words? Does it include extraneous detail that gives away the answer or tests reading comprehension instead of conceptual knowledge? Are the options too long (sentences instead of short phrases)?

P1b - Tests Recognition Not Understanding:
- At d2-d4: Flag if the question asks for name recall, symbol lookup, date, acronym, or person identification instead of conceptual understanding.
- At d1: Only flag PURE TRIVIA — symbol lookups ("What does $c$ stand for?"), acronym expansions ("What does tRNA stand for?"), date recall ("What year was X discovered?"). Do NOT flag clean d1 vocabulary like "Which molecule stores hereditary information?" — that IS appropriate d1 content.

P2 - Non-Critical Variation: Do 3+ options share a long common prefix (5+ words)? Do options differ only in minor embedded details rather than being distinct concepts?

P3a - Guessable from Context: Can a non-expert identify the correct answer through pattern-matching? (shared phrases across options, correct answer is longest/most complete, question terminology matches only one option, logic alone makes answer obvious, structural asymmetry where correct answer has different grammatical form than all distractors)

P3b - Keyword Leakage: Extract content words from the question (excluding stop words). Does any content word appear in exactly 1 of the 4 options? If so, that option is unfairly signaled.

P3c - Cultural/Common Knowledge Giveaway:
- At d1: Most d1 vocabulary IS culturally familiar — that's fine. Only flag if testing the concept has ZERO PEDAGOGICAL VALUE because the answer is so universally known it would be pointless in ANY educational context (e.g., "What country is the Great Wall in?" → China). Canonical intro vocabulary like DNA, friction, photosynthesis, Newton's laws, ecosystem, classical conditioning PASSES P3c at d1 — these are culturally familiar but pedagogically valuable.
- At d2-d4: Flag if recognizable without domain-specific study.

P3d - Definition-as-Question:
- At d2-d4: Flag if the question IS the textbook definition of the answer (vocabulary lookup, not understanding).
- At d1: Definition-style questions are ACCEPTABLE — that is what d1 tests. Only flag if the question is so over-specified (3+ identifying details) that it self-answers without any domain knowledge.

ADVERSARIAL NON-EXPERT TEST: Simulate a non-expert attempting this question. Calibrate the persona:
- d1 non-expert: never taken an intro course in this domain
- d2 non-expert: taken intro but no further study
- d3-d4 non-expert: moderate familiarity, not deep expertise

Could this non-expert score >30% through ANY structural strategy: (1) process of elimination, (2) keyword matching, (3) "most complete" heuristic, (4) grammatical cues, (5) logic alone (question phrasing makes answer deducible)? If ANY strategy gives >30%, FAIL — specify which.

Note: Cultural knowledge giveaways are handled by P3c with difficulty calibration. Do NOT double-flag under the adversarial test.

For each FAIL, explain specifically what's wrong and how to fix it.
```

**Agent output**: JSON with verdicts and explanations for each problem.

Record results in the working file after each question.

### Step 2: Fix Pass (Rewrite Flagged Questions)

For each question that FAILED any check, use a Task agent (Opus) to rewrite:

**Agent prompt**:

```
Rewrite this question to fix the flagged problems. Keep the same concept, difficulty level, and source article.

Original question: {question_text}
Original options: {A, B, C, D}
Original correct answer: {correct_answer}
Difficulty: {difficulty}

Problems to fix:
{list of FAIL verdicts with explanations}

ABSOLUTE FORMAT RULES (violations = automatic reject):
- Question: 1-2 sentences MAXIMUM. 50 words or fewer. Clear, direct syntax.
- Options (ALL levels): 1-3 words each. NEVER sentences. NEVER explanations.
- All options must be distinct concepts, not variations on the same sentence
- All options must be real domain terminology, not made-up terms
- All options must be unambiguously wrong to a domain expert
- Distractors must be within 2 words of the correct answer's length
- LaTeX: All math in $...$, literal dollar signs as $\$$

DIFFICULTY PRESERVATION (violations = automatic reject):
- The rewrite MUST stay at the same difficulty level as the original.
- d1 = intro vocabulary. Clean "what is X?" questions are FINE. Do NOT turn d1 into d3 scenarios.
- d2 = deeper vocabulary, relationships between concepts.
- d3 = applying concepts to scenarios.
- d4 = synthesizing multiple concepts.
- If the original is d1, the rewrite must be a simple, direct vocabulary question.

FIX-SPECIFIC RULES:
- For P1a fixes: trim to 1 sentence, remove extraneous clauses
- For P1b fixes (d2+ only): test understanding instead of name recall
- For P2 fixes: make options short and structurally distinct
- For P3a fixes: ensure all options are equally plausible to non-experts
- For P3b fixes: ensure no content word from the question appears in exactly 1 option
- For P3c fixes: strengthen distractors so all are real domain terms; do NOT change the difficulty level
- For P3d fixes (d2+ only): ask about behavior/implications, not definitions
- Verify factual accuracy via web search if unsure

SELF-CHECK (mandatory):
1. Is the question 1-2 sentences, under 50 words?
2. Are ALL options 1-3 words?
3. Is the difficulty level the same as the original?
4. Could a non-expert score >30% through elimination, keyword matching, or logic alone?
5. Does any question keyword appear in exactly one option?
6. Is the correct option longer or more "academic" than the others?

If your rewrite fails ANY self-check, fix the specific issue. Do NOT escalate difficulty.

Return the rewritten question and options, plus your self-check results.
```

**Agent output**: Rewritten question JSON with self-check results.

### Step 3: Re-Audit (Verify Fixes)

Run Step 1 again on all rewritten questions. If any still FAIL:
- Go back to Step 2, but instruct the agent that a previous rewrite failed
- The agent must try a **fundamentally different question angle** — not just rewording the same approach
- For example: if the first rewrite tested a mechanism and still leaked keywords, try testing an application or implication instead
- Maximum 3 total passes. If a question still fails after 3 passes, flag it for manual human review.

### Step 4: Update Domain File

1. Replace the `questions` array in `data/domains/$ARGUMENTS.json` with the audited questions
2. Preserve all other fields (`domain`, `labels`, `articles`)
3. For rewritten questions, generate new IDs (first 16 hex of SHA-256 of new question_text)
4. Preserve existing `x`, `y`, `z` coordinates (the spatial position hasn't changed)
5. Preserve `domain_ids`, `source_article`, `difficulty`, `concepts_tested`
6. Ensure answer key distribution is roughly balanced (shuffle A/B/C/D assignments)

### Step 5: Verify and Report

1. Run `npx vitest run` to verify no test regressions
2. Report statistics broken down by problem category:
   - Total questions audited
   - Questions rewritten (and how many needed multiple passes)
   - Issues by category: P1a (too long), P1b (recognition not understanding), P2 (non-critical variation), P3a (guessable), P3b (keyword leakage), P3c (cultural giveaway), P3d (definition-as-question), adversarial test failures
   - Questions that still fail after 3 passes (flagged for manual review)
3. Write summary to `data/domains/.working/$ARGUMENTS-audit-report.md`

## Checkpointing

Write progress to `data/domains/.working/$ARGUMENTS-audit.json` after EVERY question is processed. Format:

```json
{
  "domain": "$ARGUMENTS",
  "totalQuestions": 50,
  "audited": 35,
  "flagged": 12,
  "fixed": 8,
  "pass": 2,
  "questions": [
    {
      "originalId": "...",
      "status": "pass|flagged|fixed|pending",
      "problems": ["P1a", "P1b", "P2", "P3a", "P3b", "P3c", "P3d", "adversarial"],
      "original": { ... },
      "rewritten": { ... }
    }
  ]
}
```

If context runs out, the next agent reads this file to resume from where it left off.

## TodoWrite Tracking

```
TodoWrite([
  { content: "Audit $ARGUMENTS: 0/50 flagged", status: "in_progress", activeForm: "Auditing $ARGUMENTS questions" },
  { content: "Fix flagged questions: 0/N rewritten", status: "pending", activeForm: "Rewriting flagged questions" },
  { content: "Re-audit pass 2", status: "pending", activeForm: "Re-auditing fixed questions" },
  { content: "Update domain file", status: "pending", activeForm: "Updating $ARGUMENTS.json" },
  { content: "Verify and report", status: "pending", activeForm: "Verifying changes" },
])
```

## Important Notes

- **Model**: Use Claude Opus (claude-opus-4-6) for audit and rewrite agents. Quality assessment requires the strongest model.
- **Factual accuracy**: When rewriting, verify facts via web search. Never introduce factual errors.
- **Preserve coordinates**: x, y, z coordinates come from the embedding pipeline and must not be changed.
- **One domain at a time**: Process domains individually. The caller can parallelize across domains.
- **Formatting rules from generate-questions apply**: 50 word max questions, 25 word max options, LaTeX in $...$, dollar signs as $\$$.
