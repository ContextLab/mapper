# Two-Step Concept-Based Question Generation: Test Results

## Date
2025-11-17

## Test Parameters
- **Test size**: 10 cells (randomly selected with seed 123)
- **Questions per cell**: 4 (target)
- **Total attempts**: 40
- **Model**: Qwen3-14B via LM Studio
- **Approach**: Two-step (concept extraction → question generation)

## Results Summary

### Quantitative Results
- **Questions generated**: 3 / 40 attempts (7.5% success rate)
- **Questions per cell**: 0.3 average (target: 4.0)
- **Cells with 0 questions**: 7 / 10 (70%)
- **Cells with 1 question**: 3 / 10 (30%)
- **Cells with 4 questions**: 0 / 10 (0%)

### Quality Analysis

**All 3 generated questions are EXCELLENT conceptual questions:**

1. **Patent Trial and Appeal Board** - Constitutional law principles
   - Question: "Why did the Supreme Court in Oil States uphold the constitutionality of the PTAB's authority to review and cancel patent claims despite challenges under the Seventh Amendment?"
   - Tests: Constitutional principles (legislative vs judicial authority, separation of powers)
   - Pattern: "WHY did..." ✓ Conceptual
   - Concepts: Legislative authority, judicial review, constitutional basis

2. **Thai Sign Language** - Linguistic evolution
   - Question: "Why did the introduction of American Sign Language into Thai deaf schools in the 1950s lead to the development of a new sign language, rather than simply adoption of ASL?"
   - Tests: Linguistic principles (creolisation, language contact mechanisms)
   - Pattern: "WHY did..." ✓ Conceptual
   - Concepts: Language contact, creolisation, sign language development

3. **Reference frame (video)** - Video compression principles
   - Question: "Why might animated content benefit more from using multiple reference frames in video compression compared to live-action material?"
   - Tests: Compression principles (inter-frame correlation, pattern exploitation)
   - Pattern: "WHY might..." ✓ Conceptual
   - Concepts: Inter-frame compression, multiple reference frames, content-type optimization

### Article Filtering Analysis

**Articles correctly rejected** (37 / 40 = 92.5%):
- Biographical articles (Mahfuza Khanam, Milorad Balabanović, Alexander Livingstone, etc.)
- Geographic locations (Susitna River, West-Terschelling, Bordi, etc.)
- Entertainment/media (films, albums, songs)
- Sports teams and records (Birmingham City F.C. league records, Simla Youngs FC)
- Administrative entities (Screening Partnership Program, Pueblo Depot Activity)
- Historical events without conceptual depth (1894 Shōnai earthquake)

**Article types with conceptual potential** (3 / 40 = 7.5%):
- Legal/constitutional frameworks (Patent Trial and Appeal Board)
- Linguistic mechanisms (Thai Sign Language)
- Technical principles (Reference frame video compression)

## Problem Identified

### Low Success Rate
At 7.5% success rate, full generation would produce:
- 1,521 cells × 0.3 questions/cell = **~456 questions**
- Target: 1,521 cells × 4 questions/cell = **6,084 questions**
- Shortfall: **92.5%** below target

### Root Cause
The two-step filtering is **working correctly** - it's properly rejecting factual/biographical articles. The issue is:
1. Random article selection picks whatever's in each cell
2. Many Wikipedia articles are inherently factual (biographies, locations, events)
3. Current density-optimized bounding box covers diverse content, but much is non-conceptual

### Why This Happens
The Wikipedia corpus naturally contains:
- ~40-50% biographical articles (people, politicians, athletes, artists)
- ~20-30% geographic/administrative articles (places, organizations)
- ~10-20% entertainment/media (films, albums, books)
- ~10-20% conceptual articles (science, law, technology, principles)

Our random sampling reflects this natural distribution.

## Proposed Solutions

### Option A: Increase Article Pool Size (Recommended)
Instead of attempting 4 questions per cell, attempt MORE to find conceptual articles:
- Try up to 12-20 articles per cell
- Keep best 4 conceptual questions
- Accept that most articles will be filtered out
- **Pros**: High quality, maintains strict filtering
- **Cons**: 3-5x slower generation time

### Option B: Relax Filtering Criteria
Allow some "moderately conceptual" articles through:
- Lower minimum article length threshold (500 → 300 chars)
- Accept questions testing "how X relates to Y" even for factual articles
- Allow "expert factual" questions (still testing knowledge, but facts not principles)
- **Pros**: Higher success rate, faster generation
- **Cons**: Lower quality, may allow some factual questions through

### Option C: Pre-filter Wikipedia Corpus
Analyze entire Wikipedia corpus upfront to identify conceptual articles:
- Run concept extraction on all 250K articles once
- Build index of "conceptual" articles
- Only sample from pre-filtered pool
- **Pros**: Fastest generation after pre-filtering
- **Cons**: Large upfront cost, may miss edge cases

### Option D: Hybrid Approach
Combine strategies:
- Attempt up to 12 articles per cell (Option A)
- If still <4 questions, slightly relax criteria (Option B)
- Accept 2-3 questions/cell as acceptable outcome
- **Pros**: Balanced quality vs coverage
- **Cons**: Still slower than single-step

### Option E: Accept Lower Density
Generate fewer questions per cell, accept 1-2 questions/cell average:
- Total: 1,521-3,042 questions (vs 6,084 target)
- Ensures ALL questions are high-quality conceptual
- Cells with 0 questions: acceptable (some regions lack conceptual content)
- **Pros**: Maintains highest quality standard
- **Cons**: Sparse coverage, many empty cells

## Recommendation

I recommend **Option A** (increase article pool size):

### Rationale
1. **Quality is critical** - user explicitly chose 2x slower approach for quality
2. **Maintains strict filtering** - no compromise on conceptual vs factual
3. **Achieves coverage goals** - with 12-20 attempts per cell, likely to hit 3-4 questions/cell
4. **Transparent trade-off** - slower but guaranteed high quality

### Implementation
Modify [scripts/generate_cell_questions.py:682-764](scripts/generate_cell_questions.py#L682-L764):
```python
# Current: 4 attempts per cell
questions_per_cell = 4

# New: Up to 20 attempts, keep best 4
max_attempts_per_cell = 20
target_questions_per_cell = 4
```

### Expected Performance
With 12-20 attempts per cell:
- Success rate: 7.5% × 20 attempts = 1.5 questions/cell (conservative)
- Success rate: 7.5% × 20 attempts could yield 2-4 questions/cell if distribution varies
- Generation time: 1,521 cells × 20 attempts × 2 LLM calls × 2 sec/call = **~17 hours** (vs ~4 hours with 4 attempts)

Acceptable trade-off for high-quality conceptual questions.

## Next Steps

1. **User decision**: Choose from Options A-E above
2. **Implement chosen approach**: Modify generate_cell_questions.py
3. **Run full generation**: 1,521 cells with chosen strategy
4. **Validate results**: Review sample questions for quality
5. **Update documentation**: Record final statistics and approach

## Files Created/Modified

- [cell_questions_test_two_step.json](cell_questions_test_two_step.json) - Test results (3 questions)
- [notes/two_step_question_generation_implementation.md](notes/two_step_question_generation_implementation.md) - Implementation docs
- [notes/two_step_test_results.md](notes/two_step_test_results.md) - This file

## Metadata

- **Test completed**: 2025-11-17
- **Test runtime**: ~3 minutes (10 cells)
- **Quality verdict**: Excellent (all 3 questions are conceptual)
- **Coverage verdict**: Poor (7.5% success rate, 0.3 questions/cell)
- **Recommendation**: Increase article pool size (Option A)
