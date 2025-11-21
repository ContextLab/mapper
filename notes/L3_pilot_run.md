# Level 3 (High School) Simplification

**Date**: 2025-11-21
**Status**: Full run in progress

## Configuration
- **Target Audience**: High school students (ages 14-18)
- **Target Reading Level**: Flesch-Kincaid grade 10-12
- **Max Grade Level**: 12 (tolerance: +4 = 16)
- **Questions**: 20 (pilot)
- **Model**: gpt-5-mini
- **Temperature**: 1.0

## Batch Details
- **Batch ID**: batch_69200a062578819091058d73176aa846
- **Started**: 2025-11-21 06:43 UTC
- **Status**: Validating → In Progress
- **Estimated Completion**: 10-20 minutes

## Two-Pass System
1. **Pass 1** (Simplification):
   - Simplify existing questions
   - Validate readability (FK grade ≤ 16)
   - Keep correct answer the same

2. **Pass 2** (Generation - if needed):
   - Generate new questions for validation failures
   - Test same concepts
   - Validate readability again

## Expected Outcomes
- **Success Rate**: ~90-95% (based on L4 results: 98.8%)
- **Output File**: `cell_questions_level_3_simplified_pilot.json`
- **Exclusion File**: `notes/excluded_questions_level_3_pilot.json`

## Pilot Results (20 questions)
- **Success Rate**: 90% (18/20 questions)
- **Exclusion Rate**: 10% (2/20 questions)
- **Pass 1 Success**: 50% (10/20)
- **Pass 2 Success**: 80% (8/10)
- **Decision**: Accepted 10% exclusion rate, proceeding with full run

---

## Full Run (601 questions)

**Started**: 2025-11-21 12:42 UTC
**Status**: Pass 1 uploading batch file
**ETA**: 20-30 minutes

### Expected Results
Based on pilot (90% success rate):
- **Expected simplified**: ~541 questions
- **Expected excluded**: ~60 questions (10%)

### Timeline
1. **Pass 1** (Simplification): 15-20 minutes ✓ Complete
   - Processing: 601 requests via OpenAI Batch API
   - Validation: Check readability (FK ≤ 16)
   - Results: 248/601 success (41%)

2. **Pass 2** (Generation): 10-15 minutes ✓ Complete
   - Processed 353 questions needing Pass 2
   - Results: 317/353 success (90%)

3. **Total Time**: ~20-25 minutes

### Final Results
- **Total simplified**: 565 questions (94.0% success)
- **Total excluded**: 36 questions (6.0% exclusion)
- **Exclusion reason**: content_loss_both_passes (readability failures)

### Output Files
- `cell_questions_level_3_simplified.json` - 565 simplified questions ✓
- `notes/excluded_questions_level_3.json` - 36 excluded with details ✓
- `notes/L3_full_run.log` - Complete execution log ✓

### Comparison to Pilot
- Pilot: 90% success (18/20), 10% exclusion (2/20)
- Full run: **94% success (565/601), 6% exclusion (36/601)**
- ✅ **Better than pilot!** Full run achieved lower exclusion rate
