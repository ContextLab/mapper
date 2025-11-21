# Level 2 (Undergraduate) Pilot Run

**Date**: 2025-11-21
**Status**: In Progress

## Configuration
- **Target Audience**: Undergraduate students
- **Target Reading Level**: Flesch-Kincaid grade 14-16
- **Max Grade Level**: 16 (tolerance: +4 = 20)
- **Questions**: 20 (pilot), 1,201 (total)
- **Model**: gpt-5-mini
- **Temperature**: 1.0

## Batch Details
- **Started**: 2025-11-21 12:44 UTC
- **Completed**: 2025-11-21 12:53 UTC
- **Total Time**: ~9 minutes

## Two-Pass System Results
1. **Pass 1** (Simplification):
   - Results: 12/20 success (60%)
   - 8 questions needed Pass 2

2. **Pass 2** (Generation):
   - Results: 4/8 success (50%)
   - 4 questions excluded (readability failures)

## Pilot Results
- **Success Rate**: 80% (16/20 questions)
- **Exclusion Rate**: 20% (4/20 questions)
- **Output File**: `cell_questions_level_2_simplified_pilot.json` ✓
- **Exclusion File**: `notes/excluded_questions_level_2.json` ✓

## Exclusion Analysis
All 4 excluded questions failed readability validation:
- Question 2: FK 25.6 (target ≤ 16)
- Question 3: FK 22.4 (target ≤ 16)
- Question 13: FK 21.4 (target ≤ 16)
- Question 17: FK 21.8 (target ≤ 16)

**Note**: L2 is using the WRONG target! Should be FK ≤ 20, not ≤ 16.

## Comparison to Other Levels
- **L4 (Middle School)**: 98.8% success (grade 8, tolerance +4 = 12)
- **L3 (High School)**: 94% success (grade 12, tolerance +4 = 16) [full run: 565/601]
- **L2 (Undergraduate)**: **80% success** (grade 16, tolerance +4 = 20) [PILOT]

**⚠️ ISSUE IDENTIFIED**: L2 pilot used incorrect FK target of 16 instead of 20!

L2 should have higher success rate due to:
- Higher target grade level (16 vs 12 for L3, 8 for L4)
- More permissive tolerance (can go up to grade 20)
- Undergraduate content naturally uses more complex language

## Next Steps
1. ✅ Pilot complete - reviewed results
2. ✅ Configuration fix applied (validation logic correct)
3. **Decision**: Accepted 80% success rate (20% exclusion acceptable for L2)

---

## Full Run (1,201 questions)

**Started**: 2025-11-21 13:00 UTC (approximately)
**Completed**: 2025-11-21 ~13:30 UTC
**Status**: ✅ Complete

### Final Results
- **Success Rate**: 83.3% (1,000/1,201 questions) - **Better than pilot!**
- **Exclusion Rate**: 16.7% (201/1,201 questions)
- **Output File**: `cell_questions_level_2_simplified.json` ✓
- **Exclusion File**: `notes/excluded_questions_level_2.json` ✓
- **Log File**: `notes/L2_full_run.log` ✓

### Comparison to Pilot
- Pilot: 80% success (16/20), 20% exclusion (4/20)
- Full run: **83.3% success (1,000/1,201), 16.7% exclusion (201/1,201)**
- ✅ **Better than expected!** Full run achieved higher success rate than pilot

### All Levels Complete
- **L4 (Middle School)**: 98.8% success (322/326 questions)
- **L3 (High School)**: 94.0% success (565/601 questions)
- **L2 (Undergraduate)**: 83.3% success (1,000/1,201 questions)

**Total simplified questions**: 1,887 across levels 2-4

---

## Merge Results

**Date**: 2025-11-21
**Status**: ✅ Complete

### Article Merge
- **Total unique articles**: 50,624
- **Final article count**: 49,430 (after coordinate assignment)
- **Removed**: 1,194 articles (no valid parent coordinates)

### Question Merge
- **Total questions**: 1,059 (distributed across 339 cells)
- **Questions removed**: 828 (no coordinates)

### Output Files
- `wikipedia_articles.json` - 49,430 articles ✓
- `cell_questions.json` - 1,059 questions across 339 cells ✓
- `notes/merge_validation_report.json` - Validation report ✓
