# Confidence Formula Fix

## Problem

The original confidence formula was producing negative values (e.g., -867% after 1 question).

**Original (broken) formula:**
```javascript
confidence = 1 - (X / Y)
where:
  X = max distance from any cell to nearest ASKED question
  Y = max distance from any cell to ANY question (all available)
```

**Issue:** When few questions are asked, X (distance to nearest asked) can be much larger than Y (distance when all questions are available), causing negative confidence.

## Solution

Implemented a new formula that compares current coverage to best/worst case scenarios:

**New formula:**
```javascript
confidence = (Y - Z) / (Y - X)
where:
  X = best case (max dist when ALL questions answered)
  Y = worst case (max dist when 1 corner question answered)
  Z = current max dist to nearest asked question
```

**Interpretation:**
- When Z = Y (worst case), confidence = 0%
- When Z = X (best case), confidence = 100%
- Confidence represents "what percentage of the way are we from worst to best coverage?"

## Simulation Results

Tested with 1000 random questions on 39×39 grid:

| Questions Asked | Z (current) | Confidence |
|----------------|-------------|------------|
| 1              | 1.0918      | 22.9%      |
| 10             | 0.4707      | 69.6%      |
| 50             | 0.1733      | 92.0%      |
| 100            | 0.1457      | 94.1%      |
| 500            | 0.0754      | 99.4%      |
| 1000           | 0.0672      | 100.0%     |

Where:
- X (best case) = 0.0672
- Y (worst case) = 1.3961

## Files Modified

1. **index.html**:
   - Lines 1435-1500: Rewrote `_computeConfidence()` method with new formula
   - Lines 1503-1512: Updated `getStats()` to use new field names (`maxDistCurrent`, `maxDistBest`, `maxDistWorst`)
   - Lines 1925-1928: Updated console logging to show all three distances
   - Line 1415-1419: Removed `askedQuestionIndices.push()` from `selectNextQuestion()` (questions shouldn't be marked as "asked" until answered)
   - Line 1427-1430: Added `askedQuestionIndices.push()` to `recordResponse()` (mark questions as asked when answered)
   - Line 1705: Added `index` property to question object in `startNewQuizRound()` (preserve question index for tracking)
   - Line 1983: Added `updateConfidenceDisplay()` call in `handleNext()` after recording response
   - Line 2021: Added `updateConfidenceDisplay()` call in `handleDontKnow()` after recording response
   - Line 1904: Added `updateConfidenceDisplay()` call in `startQuiz()` to initialize display at 0%

2. **scripts/test_confidence_formula.py**:
   - Created simulation to test different formula approaches
   - Validated Formula 5 gives correct behavior

## Bugs Fixed

### Bug 1: Wrong Formula
The original formula `1 - (X/Y)` produced negative values because X could exceed Y.

### Bug 2: Questions Marked as "Asked" Too Early
Questions were added to `askedQuestionIndices` in `selectNextQuestion()`, which ran during quiz setup. This meant all 10 questions were marked as "asked" before the user saw the first question, resulting in 82% confidence at start.

**Fix:** Moved `askedQuestionIndices.push()` from `selectNextQuestion()` to `recordResponse()`, so questions are only marked as "asked" when the user actually answers them.

### Bug 3: Missing `index` Property
When questions were added to `questionsData` in `startNewQuizRound()`, the `index` property wasn't copied from `selectedQuestion`. This meant `recordResponse()` received `undefined` for `questionIndex`, so questions were never added to `askedQuestionIndices`.

**Fix:** Added `index: selectedQuestion.index` to the question object (line 1705).

### Bug 4: Display Not Updating During Quiz
`updateConfidenceDisplay()` was never called, so the display stayed at 0% until the quiz ended.

**Fix:** Added `updateConfidenceDisplay()` calls in `handleNext()`, `handleDontKnow()`, and `startQuiz()`.

### Bug 5: Duplicate Questions in Same Round
When `startNewQuizRound()` called `selectNextQuestion()` 10 times in a loop, each call would see the same available questions (since they weren't marked as "asked" yet), so the same question could be selected multiple times.

**Fix:** Added `pendingQuestionIndices` array to track questions that have been selected but not yet answered. Questions are:
1. Added to `pendingQuestionIndices` when selected (`selectNextQuestion()`)
2. Moved from `pendingQuestionIndices` to `askedQuestionIndices` when answered (`recordResponse()`)
3. Cleared at the start of each new round (`clearPendingQuestions()`)
4. Excluded by `_getAvailableQuestions()` filter

## Display Updates

The confidence display now:
- Shows 0% when quiz starts (no questions answered)
- Updates in real-time after each question is answered
- Updates when user clicks "I Don't Know"
- Displays correctly during quiz (not just at the end on the map)

## Benefits

1. **Never negative** - Clamped to [0, 1] range
2. **Intuitive** - 0% at start, 100% when all questions answered
3. **Linear scaling** - Progress is proportional to coverage improvement
4. **Mathematically sound** - Compares current state to defined best/worst cases
5. **Real-time feedback** - Updates visible during quiz, not just at the end
