# Question Generation Process & Reproducible Template

**Created:** 2026-02-17
**Author:** Claude (Opus 4) generating directly in main session
**Purpose:** Document the exact process for generating conceptual MCQs so it can be reproduced for future batches

## Overview

We generate deep conceptual multiple-choice questions for the Wikipedia Knowledge Map demo. Each domain gets 50 questions across 5 difficulty levels. Questions are generated in two batches:
- **Batch 1**: Q1-Q20 (4 per difficulty level)
- **Batch 2**: Q21-Q50 (6 per difficulty level)

## Why Claude Generates Directly (Not via API)

GPT-5-nano was tested and rejected — quality too low for conceptual questions. Delegating to subagents timed out (600s limit too short for 20+ questions). The highest quality comes from Claude (Opus-class) generating directly in the main session with web search fact-verification.

## Answer Distribution Pattern

### Batch 1 (20 questions)
```
Q1=A, Q2=B, Q3=C, Q4=D   (cycle 1)
Q5=A, Q6=B, Q7=C, Q8=D   (cycle 2)
Q9=A, Q10=B, Q11=C, Q12=D (cycle 3)
Q13=A, Q14=B, Q15=C, Q16=D (cycle 4)
Q17=A, Q18=B, Q19=C, Q20=D (cycle 5)
```
Totals: 5A, 5B, 5C, 5D = 20

### Batch 2 (30 questions)
```
Q21=A, Q22=B, Q23=C, Q24=D, Q25=A, Q26=B  (6 questions)
Q27=C, Q28=D, Q29=A, Q30=B, Q31=C, Q32=D  (6 questions)
Q33=A, Q34=B, Q35=C, Q36=D, Q37=A, Q38=B  (6 questions)
Q39=C, Q40=D, Q41=A, Q42=B, Q43=C, Q44=D  (6 questions)
Q45=A, Q46=B, Q47=C, Q48=D, Q49=A, Q50=B  (6 questions)
```
Totals: 8A, 8B, 7C, 7D = 30

### Combined (50 questions)
Totals: 13A, 13B, 12C, 12D = 50 ✓

## Difficulty Distribution Pattern

### Batch 1 (20 questions)
```
Q1-Q4:   Level 1 (4 questions)
Q5-Q8:   Level 2 (4 questions)
Q9-Q12:  Level 3 (4 questions)
Q13-Q16: Level 4 (4 questions)
Q17-Q20: Level 5 (4 questions)
```

### Batch 2 (30 questions)
```
Q21-Q26: Level 1 (6 questions)
Q27-Q32: Level 2 (6 questions)
Q33-Q38: Level 3 (6 questions)
Q39-Q44: Level 4 (6 questions)
Q45-Q50: Level 5 (6 questions)
```

### Combined: 10 per level × 5 levels = 50 ✓

## Difficulty Criteria (EXACT — from user)

- **Level 1**: Immediate answer if you know it, OR immediately know you don't. Answerable by someone who's spent some time learning about that area (lecture, book, documentary) but NOT by someone who has NEVER learned about it. NOT answerable by simple reading comprehension.
- **Level 2**: 10-15s thinking. High school graduate with one course in the domain.
- **Level 3**: ~30s thinking. College major in that area.
- **Level 4**: ~1min thinking. Masters/graduate student.
- **Level 5**: ~1.5-2min thinking. Domain expert only.

Specificity, detail, and complexity increase across levels. ALL levels focus on REASONING — identify the core logic and test THAT.

## Question Schema

```json
{
  "question_text": "The question itself — clear, self-contained, tests conceptual understanding",
  "options": {
    "A": "Option A text",
    "B": "Option B text",
    "C": "Option C text",
    "D": "Option D text"
  },
  "correct_answer": "A",
  "difficulty": 1,
  "concepts_tested": ["concept1", "concept2", "concept3"],
  "reasoning": "Why the correct answer is right AND why each distractor is wrong",
  "domain_id": "physics"
}
```

Notes:
- `x`, `y`, `z` coordinates are NOT included — computed later from text embeddings
- `id` and `source_article` are added during export, not generation
- `domain_ids` (plural, for cross-domain membership) is added during export

## Generation Process (Step by Step)

### 1. Review Existing Questions
Before generating batch 2 for any domain, read batch 1 to:
- Know which topics are already covered (avoid duplicates)
- Match the established quality bar
- Ensure new questions cover different conceptual territory

### 2. Plan Topics by Difficulty Level
For each level, brainstorm topics that match the difficulty criteria:
- L1: Core concepts anyone who's studied the field would recognize
- L2: Standard curriculum topics requiring some thought
- L3: Deeper connections, counter-intuitive results, synthesis
- L4: Graduate-level theory, experimental methodology, advanced frameworks
- L5: Cutting-edge research, deep theoretical insights, expert-only knowledge

### 3. Fact-Check Key Claims
Use web searches (Google Search tool) to verify:
- Specific dates, names, and attributions
- Numerical values and constants
- Experimental results and who discovered/measured them
- Theoretical frameworks and their exact predictions

### 4. Write Questions with Pre-Assigned Positions
For each question, the correct answer letter is PRE-DETERMINED by the position pattern. Write the question so the factually correct content naturally sits at the assigned position. If it's easier to write the correct answer first, do so, then construct the distractors, then place the correct content at the assigned letter.

### 5. Write Plausible Distractors
Each distractor should be:
- Plausible to someone who doesn't fully understand the concept
- Based on common misconceptions or adjacent knowledge
- Clearly wrong upon careful analysis
- Not obviously absurd (no joke answers)

### 6. Write Clean Reasoning
Reasoning must:
- Explain WHY the correct answer is right
- Explain WHY each distractor is wrong (briefly)
- Contain NO thinking artifacts ("Wait—", "Let me restructure", "swap", etc.)
- Be factually accurate and self-contained

### 7. Validate with Automated Script
Run the validation script after each batch:
```python
python3 -c "
import json
with open('/tmp/FILENAME.json') as f:
    qs = json.load(f)
print(f'Total: {len(qs)}')
# Check answer pattern
answers = [q['correct_answer'] for q in qs]
expected_b2 = ['A','B','C','D','A','B','C','D','A','B','C','D','A','B','C','D','A','B','C','D','A','B','C','D','A','B','C','D','A','B']
ok = all(a == e for a, e in zip(answers, expected_b2))
print(f'Answers OK: {ok}')
if not ok:
    for i, (a, e) in enumerate(zip(answers, expected_b2)):
        if a != e: print(f'  Q{i+21}: got={a} expected={e}')
from collections import Counter
diff = dict(sorted(Counter(q['difficulty'] for q in qs).items()))
print(f'Difficulty: {diff}')
print(f'Difficulty OK: {diff == {1:6,2:6,3:6,4:6,5:6}}')
bad = [(i+21) for i, q in enumerate(qs) if any(w in q.get('reasoning','') for w in ['Wait', 'Let me', 'reconsider', 'restructure', 'I need', 'swap', 'needs to be'])]
print(f'Artifacts: {bad}' if bad else 'No artifacts')
missing = [(i+21, f) for i, q in enumerate(qs) for f in ['question_text','options','correct_answer','difficulty','concepts_tested','reasoning','domain_id'] if f not in q]
print(f'Missing: {missing}' if missing else 'Schema OK')
"
```

### 8. Check for Cross-Domain Duplicates
After all domains are generated, run a comprehensive check:
- No duplicate question_text across any domains
- Minimal concept overlap (some overlap is natural for related domains)
- Each question is self-contained and unambiguous

## Common Pitfalls (CRITICAL)

1. **Answer position errors**: The #1 recurring error. When writing a question, the "natural" correct answer often lands at A or C. Must deliberately restructure options so correct content is at the pre-assigned position.

2. **Thinking artifacts in reasoning**: Text like "Wait —", "Let me restructure", "I need to swap" must NEVER appear in the final reasoning field. Always write clean reasoning from scratch.

3. **Wrong domain_id**: When generating many domains in sequence, easy to leave the previous domain's ID. Always verify.

4. **Missing Q16 pattern**: In batch 1, Q16 (D, L4) was consistently forgotten, resulting in 19 instead of 20 questions. Count carefully.

5. **Difficulty miscalibration**: L1 questions that require too much reasoning, or L5 questions that are just obscure trivia. L1 = recognition, L5 = deep expert reasoning.

6. **Reading comprehension questions**: Questions where the answer is embedded in the question text and can be found by careful reading alone. ALL questions must test knowledge beyond what's stated in the question.

## File Locations

### Batch 1 files (Q1-Q20, in /tmp/)
```
physics_batch1_questions.json
biology_batch1_questions.json
math_batch1_questions.json
neuro_batch1_questions.json
arthistory_batch1_questions.json
astrophysics_batch1_questions.json
quantum_physics_batch1_questions.json
molecular_cell_biology_batch1_questions.json
genetics_batch1_questions.json
cognitive_neuro_batch1_questions.json
computational_neuro_batch1_questions.json
neurobiology_batch1_questions.json
calculus_batch1_questions.json
linear_algebra_batch1_questions.json
number_theory_batch1_questions.json
probability_statistics_batch1_questions.json
european_art_history_batch1_questions.json
chinese_art_history_batch1_questions.json
```

### Batch 2 files (Q21-Q50, in /tmp/)
Same naming but with `_batch2_` instead of `_batch1_`

### Domain list (18 domains, excluding "all" which aggregates)
```
physics, biology, mathematics, neuroscience, art-history,
astrophysics, quantum-physics, molecular-cell-biology, genetics,
cognitive-neuroscience, computational-neuroscience, neurobiology,
calculus, linear-algebra, number-theory, probability-statistics,
european-art-history, chinese-art-history
```

## Merge Process (After Both Batches Complete)

To combine batch 1 and batch 2 into a single 50-question file per domain:
```python
import json
domain = "physics"  # Change per domain
with open(f'/tmp/{domain}_batch1_questions.json') as f:
    b1 = json.load(f)
with open(f'/tmp/{domain}_batch2_questions.json') as f:
    b2 = json.load(f)
combined = b1 + b2
assert len(combined) == 50
# Validate combined
answers = [q['correct_answer'] for q in combined]
expected_50 = ['A','B','C','D'] * 12 + ['A','B']
assert answers == expected_50
from collections import Counter
assert Counter(q['difficulty'] for q in combined) == {1:10, 2:10, 3:10, 4:10, 5:10}
# Save
with open(f'/tmp/{domain}_all_questions.json', 'w') as f:
    json.dump(combined, f, indent=2)
```

## Quality Standards (Non-Negotiable)

1. **100% factual accuracy** — every claim must be verifiable
2. **100% clarity** — no ambiguous wording
3. **Deep conceptual testing** — NOT trivia, NOT rote memorization
4. **Self-contained** — no external knowledge needed beyond the domain
5. **Calibrated difficulty** — matches the exact criteria above
6. **Excellent distractors** — plausible, based on real misconceptions
7. **Clean reasoning** — explains correct answer AND debunks each distractor
