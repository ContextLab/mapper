# Two-Step Concept-Based Question Generation Implementation

## Date
2025-11-17

## Summary
Successfully implemented two-step LLM-based question generation system to shift from factual/definitional questions to conceptual questions testing understanding of principles and mechanisms.

## Problem Identified
Previous single-step prompting produced questions testing memorized facts rather than conceptual understanding:

**Bad Example (OLD)**:
```
"What is the primary purpose of a 'hundred' in English administrative geography?"
```
This is definitional ("WHAT IS") - tests memorization, not understanding.

**Good Example (TARGET)**:
```
"Why does increasing temperature generally speed up chemical reactions?"
```
This is conceptual ("WHY DOES") - tests understanding of principles.

## Solution: Two-Step Process

### STEP 1: Concept Extraction
LLM analyzes article to determine:
1. Does it contain substantial conceptual content (vs. purely factual/lists)?
2. What are 1-3 core concepts/principles that could be tested?
3. Can we ask "why/how" questions about these concepts?

**Returns**: `{'suitable': bool, 'concepts': list, 'reasoning': str}` or `None` if unsuitable

### STEP 2: Conceptual Question Generation
LLM generates question testing understanding of extracted concepts:
- Focuses on "WHY does X work?" or "HOW does A relate to B?"
- Avoids "WHAT is X?", "WHEN did Y?", "WHO was Z?"
- Expert-level difficulty OK as long as it tests principles, not facts
- Completely self-contained (no references to source)

## Implementation Details

### New Functions in [scripts/generate_cell_questions.py](scripts/generate_cell_questions.py)

#### 1. `is_concept_question()` (lines 227-297)
Quality check function that filters out factual questions:

**Rejects** (factual starters):
- "What is the..."
- "When did..."
- "Who was..."
- "Where is..."
- "What does the term..."

**Accepts** (conceptual indicators):
- "Why does..."
- "How does..."
- "What explains..."
- "What principle..."
- "What mechanism..."
- "What causes..."

#### 2. `extract_concepts_from_article()` (lines 300-422)
STEP 1: Concept extraction with structured JSON output

**Prompt Strategy**:
- Identifies PRINCIPLES, MECHANISMS, RELATIONSHIPS vs. facts
- Examples of SUITABLE: cause-and-effect, theoretical frameworks
- Examples of UNSUITABLE: lists, timelines, pure definitions

**JSON Schema**:
```json
{
  "suitable": boolean,
  "concepts": [list of 1-3 core concepts],
  "reasoning": "explanation of suitability"
}
```

**Temperature**: 0.3 (lower for consistent analysis)

#### 3. `generate_question_for_article()` (lines 425-606)
STEP 2: Question generation using extracted concepts

**Revised Signature**:
```python
def generate_question_for_article(article, cell, concepts_data, ...):
```
Now requires `concepts_data` from Step 1.

**Prompt Strategy**:
- Presents extracted concepts for LLM to choose from
- Explicit examples of GOOD (conceptual) vs. BAD (factual) questions
- System message emphasizes "WHY and HOW, not WHAT or WHEN"

**Temperature**: 0.7 (creative question generation)

### Enhanced Filtering

#### Updated `is_suitable_article()` (lines 62-91)
- Minimum article length: 200 → **500 characters**
- New rejections: "List of", "Index of", "Timeline of", "Glossary of"

### Main Generation Loop Updates (lines 682-764)

**Two-Step Flow**:
```python
# STEP 1: Extract concepts
concepts_data = extract_concepts_from_article(article)
if not concepts_data:
    print("No conceptual content found, skipping article")
    continue

# STEP 2: Generate question
result = generate_question_for_article(article, cell, concepts_data)
```

**Three Quality Checks**:
1. `is_question_self_contained()` - No references to source
2. `is_mitochondria_placeholder()` - Not a generic placeholder
3. **NEW**: `is_concept_question()` - Conceptual, not factual

**Retry Logic**:
- Up to 3 attempts per question
- If all 3 fail any quality check, skip that question slot

## Expected Performance Impact

### Speed
- **2x slower** than single-step (2 LLM calls per question vs. 1)
- Acceptable trade-off for quality improvement

### Quality Improvements
1. **Conceptual focus**: Questions test "why/how" principles instead of "what/when" facts
2. **Better filtering**: Articles without conceptual depth are skipped entirely
3. **Expert-level OK**: Can require domain expertise as long as testing principles
4. **Multi-article synthesis**: Can combine related articles if very close

## Testing Status

**Test Command**:
```bash
python3 scripts/generate_cell_questions.py --num-cells 10 --random-seed 123 \
  --output cell_questions_test_two_step.json --no-resume
```

**Status**: Test running (loading Wikipedia data - large file)

**Expected Output**: 10 cells × 4 questions = ~40 conceptual questions

## Next Steps

1. **Review test results** - Verify questions are conceptual, not factual
2. **Adjust if needed** - Tweak prompts/filters based on test output
3. **Full generation** - Run on all 1,521 cells if test passes
4. **Performance monitoring** - Track generation time and quality metrics

## Key Design Decisions

### 1. Why Two-Step vs. Single-Step?
**Single-step limitations**:
- LLM often defaults to factual questions despite prompting
- Hard to reliably filter unsuitable articles in same prompt

**Two-step advantages**:
- Explicit concept identification forces LLM to think conceptually
- Clear separation: analysis (Step 1) vs. generation (Step 2)
- Better filtering: articles without concepts rejected early

### 2. Why Expert-Level is OK?
User clarified: "expert-level is OK as long as we are testing *conceptual* understanding"

The tool maps knowledge across very broad content. Questions should test:
- ✓ Understanding of core principles (even if expert domain)
- ✗ Memorization of specific facts or definitions

### 3. Why Skip Articles Without Concepts?
User specified: "if no good conceptual question can be asked, skip it."

Better to have fewer high-quality conceptual questions than many low-quality factual ones.

## Files Modified

- [scripts/generate_cell_questions.py](scripts/generate_cell_questions.py):
  - Added `is_concept_question()` (227-297)
  - Added `extract_concepts_from_article()` (300-422)
  - Revised `generate_question_for_article()` (425-606)
  - Updated `is_suitable_article()` (62-91)
  - Updated generation loop (682-764)

## Metadata

- **Implementation Date**: 2025-11-17
- **Approach**: Two-step LLM prompting with concept extraction
- **Model**: Qwen3-14B via LM Studio
- **Quality Checks**: 3 (self-contained, non-placeholder, conceptual)
- **Performance**: 2x slower, much higher quality
- **Test Size**: 10 cells
- **Production Target**: 1,521 cells (6,084 questions)
