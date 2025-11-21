# Issue #15 Progress Notes - Session 2024-11-20

## What Has Been Completed

### 1. Feature Branch Created
- Branch: `feature/issue-15-simplify-questions`
- Commit: 0b906dd

### 2. Core Script Implementation (`scripts/simplify_questions.py`)
**Features Implemented:**
- Two-pass system:
  - Pass 1: Simplification attempt with validation
  - Pass 2: New question generation if Pass 1 fails
- Level-specific prompts for L0-L4
- GPT-5-mini API integration with retry logic
- Inline LaTeX conversion ($...$)
- Flesch-Kincaid readability validation (via textstat)
- Exclusion logging for failed questions
- CLI: --level, --all, --pilot flags

**Key Functions:**
- `simplify_question()`: Pass 1 simplification
- `generate_new_question()`: Pass 2 new generation  
- `validate_simplified_question()`: Content preservation checks
- `calculate_flesch_kincaid()`: Readability scoring

### 3. Dependencies Added
- textstat>=0.7.0 added to requirements.txt
- Already installed in environment

## Currently Running

**L4 Pilot Test (20 questions)**
- Command: `python scripts/simplify_questions.py --level 4 --pilot 20`
- Started: 2024-11-20 ~13:50
- Status: RUNNING (making real GPT-5-mini API calls)
- Background process ID: 6f5317
- Log file: notes/l4_pilot_run.log (currently empty due to buffering)

**Expected Behavior:**
- 20 questions × ~3-5 seconds/question = 1-2 minutes minimum
- With retries and two-pass system, could take 3-5 minutes
- Creates: `cell_questions_level_4_simplified.json` (pilot version)
- Creates: `notes/excluded_questions_level_4.json` (if any exclusions)

## Next Steps After Pilot Completes

1. **Manual Review** (CRITICAL):
   - Read all 20 simplified questions
   - Check content appropriateness for middle schoolers
   - Verify LaTeX formatting correct
   - Confirm factual accuracy
   - Validate correct answer preserved
   - Check readability (Flesch-Kincaid ≤8)
   - Document issues in notes/l4_pilot_review.md

2. **Prompt Iteration** (if needed):
   - Adjust prompts based on findings
   - Re-run pilot
   - Repeat until 90%+ quality

3. **Full L4 Run**:
   - Run all 326 L4 questions
   - Manual spot-check 50 random samples
   - Validate exclusion rate <15%

4. **Pipeline Integration**:
   - Update `merge_multi_level_data.py` (no fallback)
   - Create/update `run_full_pipeline.sh`
   - Add LaTeX rendering to `index.html`

5. **Remaining Levels** (L3, L2, L1, L0):
   - Pilot + iteration for each
   - Full run for each
   - Manual validation for each

## Key Decisions Made

1. ✅ Preserve originals in `cell_questions_level_{n}.json`
2. ✅ No fallback to originals in merge script
3. ✅ Inline LaTeX only (`$...$`)
4. ✅ Flesch-Kincaid for readability
5. ✅ Two-pass system with exclusions for total failures
6. ✅ Manual testing only (no automated integration tests)

## Important Notes

- All API calls are REAL (no mocks/simulations)
- Each question requires manual quality verification
- Exclusion rate must stay <15% per level
- Cost tracking: ~$0.0003 per question
- Log all issues and commit frequently

## Files Modified

1. `scripts/simplify_questions.py` (NEW) - 757 lines
2. `requirements.txt` - Added textstat

## Files To Be Modified Next

1. `scripts/merge_multi_level_data.py` - Remove fallback logic
2. `index.html` - Add KaTeX rendering
3. `run_full_pipeline.sh` - Add simplification step (or create if missing)

## Cost Tracking

- L4 pilot (20 questions): ~$0.006
- L4 full (326 questions): ~$0.10
- All levels: ~$0.78
- Expected total with iterations: ~$0.90

## GitHub Issue Comments

- Progress tracking comment posted
- Will update with commit hashes as work proceeds

