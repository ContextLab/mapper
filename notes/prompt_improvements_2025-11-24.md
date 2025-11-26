# Question Simplification Prompt Improvements

**Date:** 2025-11-24
**GitHub Issue:** [#17](https://github.com/simpleXknowledge/mapper.io/issues/17)
**Branch:** feature/issue-14-level-scaling

## Problem Statement

Current simplified questions have three main issues:

1. **LaTeX dollar sign ambiguity**: Currency symbols ($) are being interpreted as LaTeX delimiters during rendering, causing formatting issues. Post-processing disambiguation is expensive and inconsistent (~75% success rate).

2. **Reading level overshooting**: Generated questions are too complex for target audiences. Questions aimed at middle schoolers (L4) read at a higher level than intended.

3. **Verbosity**: Questions and answers are longer than needed, reducing accessibility for younger learners.

## Solution Implemented

Updated prompts in [scripts/simplify_questions.py](../scripts/simplify_questions.py) to fix these issues at generation time.

### 1. Reading Level Adjustments

Lowered target reading levels by ~2 grade levels to account for generation overshoot:

| Level | Old Target | New Target | Flesch-Kincaid Target |
|-------|------------|------------|----------------------|
| **L4** | Middle School (5th grade) | **Elementary School (3rd grade)** | 3-5 (was 6-8) |
| **L3** | High School (9th grade) | **Middle School (6th grade)** | 6-9 (was 10-12) |
| **L2** | Undergraduate (college) | **High School (9th grade)** | 9-12 (was 14-16) |

**Changed in code:**
- Lines 56-75: Updated `LEVEL_CONFIG` with new target audiences and max grade levels
- Lines 142-195 (simplification prompt): Updated readability targets and writing rules
- Lines 248-304 (generation prompt): Updated readability targets and writing rules

### 2. Brevity Constraints

Added explicit length requirements to writing rules:

**Level 4 (Elementary School):**
- Questions: **1-2 sentences maximum**
- Answer choices: **Short phrases or single sentences, max 2 sentences**
- Sentence length: Under 15 words

**Level 3 (Middle School):**
- Questions: **1-2 sentences maximum**
- Answer choices: **Short phrases or single sentences, max 2 sentences**
- Sentence length: Under 20 words

**Level 2 (High School):**
- Questions: **1-2 sentences when possible**
- Answer choices: **Concise, max 2 sentences**
- More flexibility for complex concepts

**Changed in code:**
- Lines 148-154: Added BREVITY rules to L4 simplification prompt
- Lines 256-263: Added BREVITY rules to L4 generation prompt
- Lines 179-184: Added BREVITY rules to L3 prompts
- Lines 288-293: Added BREVITY rules to L3 generation prompt
- Lines 191-195: Added BREVITY rules to L2 prompts
- Lines 300-304: Added BREVITY rules to L2 generation prompt

### 3. LaTeX Dollar Sign Escaping

Added explicit instructions to escape currency symbols during generation:

**New rule added to both simplification and generation prompts:**

```
CRITICAL - LaTeX Dollar Sign Escaping:
- When writing currency amounts, ALWAYS escape the dollar sign as \$ to prevent LaTeX rendering conflicts
- Examples: "$200 million" → "\$200 million", "GDP of $10,000" → "GDP of \$10,000"
- Only use unescaped $ for actual math expressions like $x^2$ or $\frac{1}{2}$
- Physical unit counts are NOT currency: "10,000 cars" stays as plain text
```

**Changed in code:**
- Lines 211-215: Added LaTeX escaping rule to simplification prompt (Pass 1)
- Lines 317-321: Added LaTeX escaping rule to generation prompt (Pass 2)

## Testing Plan

### Pilot Testing (Current)

Running pilot tests with 20 questions per level (L2, L3, L4) to verify:
1. Currency amounts are properly escaped with `\$`
2. Reading levels match targets (3rd grade for L4, 6th for L3, 9th for L2)
3. Questions and answers meet brevity requirements
4. Core concepts are preserved

**Commands running:**
```bash
python3 scripts/simplify_questions.py --level 4 --pilot 20
python3 scripts/simplify_questions.py --level 3 --pilot 20
python3 scripts/simplify_questions.py --level 2 --pilot 20
```

**Output files:**
- `cell_questions_level_4_simplified.json` (pilot mode, 20 questions)
- `cell_questions_level_3_simplified.json` (pilot mode, 20 questions)
- `cell_questions_level_2_simplified.json` (pilot mode, 20 questions)

### Manual Quality Review (Pending)

User will manually examine pilot questions for:
- Appropriate reading level
- Proper LaTeX escaping
- Brevity compliance
- Content preservation

### Iteration (As Needed)

Based on user feedback, prompts may be adjusted before running full production batches.

### Full Production Run (After Approval)

Once pilot questions are approved:
```bash
python3 scripts/simplify_questions.py --level 4  # Full L4 run
python3 scripts/simplify_questions.py --level 3  # Full L3 run
python3 scripts/simplify_questions.py --level 2  # Full L2 run
```

Then merge results into `cell_questions.json` following `run_full_pipeline.py`.

## Previous Approach (Abandoned)

**Post-processing LaTeX disambiguation** using `scripts/disambiguate_latex.py`:
- ✅ Fixed physical units detection (100% success)
- ✅ Fixed `\text{}` command handling (100% success)
- ⚠️ Mismatched delimiters (~75% success, temperature=1.0 variability)

**Why abandoned:** Fixing at generation time is more reliable and cost-effective than expensive post-processing with a smarter model.

## Related Files

- [scripts/simplify_questions.py](../scripts/simplify_questions.py) - Main script (updated)
- [scripts/disambiguate_latex.py](../scripts/disambiguate_latex.py) - Old post-processing approach (deprecated for this use case)
- [notes/latex_disambiguation_issues.md](latex_disambiguation_issues.md) - Documentation of post-processing approach
- [notes/latex_fix_verification.md](latex_fix_verification.md) - Verification of physical units fix

## Validation Metrics

Post-pilot, we will check:
1. **LaTeX escaping rate**: % of currency amounts correctly escaped with `\$`
2. **Reading level accuracy**: Flesch-Kincaid scores vs. targets
3. **Brevity compliance**: % of questions ≤2 sentences, % of answers ≤2 sentences
4. **Content preservation rate**: % of questions passing validation
5. **Pass 1 vs. Pass 2 ratio**: How many questions succeed in simplification vs. need regeneration

## Pilot Test Results (Round 1)

### Summary
- **Level 4**: 7/20 questions (35% success), **65% exclusion rate** - readability still too high
- **Level 3**: 18/20 questions (90% success), 10% exclusion rate - good performance
- **Level 2**: 16/20 questions (80% success), 20% exclusion rate - good performance

### Key Issues Identified

**Level 4 still failing readability targets:**
1. **Compound sentences persisting**: "Long-term structures set up opportunities and weak spots, and sudden events trigger changes past tipping points." (18 words, multiple clauses)
2. **Academic vocabulary not eliminated**: "systematic factor," "hierarchical taxonomy," "faceted classification," "contingent"
3. **Complex grammatical structures**: Parenthetical additions, multi-clause "which explains why" structures
4. **Flesch-Kincaid scores**: Ranging from 10.1 to 28.1 (target is ≤8)

**Root cause**: Model NOT following "under 15 words" rule or "no compound sentences" rule despite explicit instructions.

### Prompt Improvements (Round 2)

Updated Level 4 prompts with much stricter enforcement:

**New "CRITICAL BREVITY RULES" section:**
1. Each sentence MUST be under 15 words - count carefully!
2. Questions: 1 sentence only (max 2 if absolutely necessary)
3. Answer options: 1 short sentence each (under 15 words)
4. NO compound sentences with "and," "but," "so" connecting clauses
5. NO parenthetical additions like "(both known and unknown)"
6. NO multi-clause structures like "which explains why..."
7. Use ONLY simple subject-verb-object sentences

**Enhanced BAD examples showing actual pilot failures:**
- ❌ BAD (18 words, Grade 12): "Long-term structures set up opportunities and weak spots, and sudden events trigger changes past tipping points."
- ✅ GOOD (13 words, Grade 4): "Big events can cause change when conditions are right for it."

**Updated generation examples:**
- Broke long sentences into multiple short sentences (each under 15 words)
- Removed all compound sentence structures from examples
- Added LaTeX escaping examples with `\$` in currency amounts

**LaTeX improvements:**
- Added explicit rule: "The ENTIRE math expression must be enclosed"
- Example: "$x$^2" is WRONG, "$x^2$" is CORRECT
- Updated all examples to show properly escaped currency: `\$10`, `\$25`, `\$0`

### Changed Files
- [scripts/simplify_questions.py](../scripts/simplify_questions.py)
  - Lines 147-183: Updated Level 4 simplification prompt with stricter rules
  - Lines 266-299: Updated Level 4 generation prompt with stricter rules
  - Lines 216-224: Enhanced LaTeX math notation rules (both prompts)
  - Lines 220-226, 335-341: Enhanced LaTeX dollar sign escaping (both prompts)

## Next Steps

1. ✅ Create GitHub issue #17
2. ✅ Update prompts in `scripts/simplify_questions.py` (Round 1)
3. ✅ Run pilot tests (L2, L3, L4) - Round 1 complete
4. ✅ Analyze pilot results and improve prompts (Round 2)
5. ⏳ Wait for user's manual quality review of pilot questions
6. ⏳ Decision: Re-run pilot with improved prompts OR adjust approach
7. ⏳ Run full production batches (after approval)
8. ⏳ Merge into `cell_questions.json`
