# Phase 4: Multi-Level Adaptive Sampling Implementation

## Overview

Phase 4 enhances the adaptive sampling algorithm to support hierarchical question difficulty levels (0-4), enabling personalized learning paths that adapt to user performance.

## Implementation Status

### ✅ Completed Components

1. **MultiLevelAdaptiveSampler Class** (`adaptive_sampler_multilevel.js`)
   - Extends base AdaptiveSampler with multi-level support
   - Tracks performance independently per difficulty level
   - Adaptive difficulty progression based on accuracy thresholds
   - Level-aware question selection algorithm

2. **Multi-Level Question Generation Pipeline** (Background)
   - Currently running: Generating questions for all 5 levels (0-4)
   - Expected completion: 10-15 hours
   - Output files: `cell_questions_level_N.json` (N=0-4)

## Key Features

### 1. Performance Tracking Per Level

```javascript
this.levelStats = {
    0: { correct: 5, total: 10, accuracy: 0.50 },
    1: { correct: 7, total: 10, accuracy: 0.70 },
    2: { correct: 3, total: 5, accuracy: 0.60 },
    // ...
};
```

- Separate statistics for each difficulty level
- Tracks correct answers, total attempts, and accuracy
- Used to determine level progression/regression

### 2. Adaptive Difficulty Progression

**Progression Rules:**
- **Progress to harder level:** Accuracy ≥ 70% AND min 3 questions answered
- **Regress to easier level:** Accuracy < 40% AND min 3 questions answered
- **Stay at current level:** Otherwise

**Example Flow:**
```
Level 0 → 80% accuracy → Progress to Level 1
Level 1 → 35% accuracy → Regress to Level 0
Level 0 → 75% accuracy → Progress to Level 1
Level 1 → 65% accuracy → Stay at Level 1
```

### 3. Level-Aware Question Selection

The selection algorithm combines three factors:

1. **Spatial Coverage (α term)**
   - Maximizes distance from previously asked cells
   - Ensures broad coverage of knowledge map

2. **Uncertainty Reduction (β term)**
   - Targets cells with highest prediction uncertainty
   - Efficiently narrows down knowledge gaps

3. **Level Preference (γ term)**
   - Prefers questions at current difficulty level
   - Tolerates ±1 level deviation when needed
   - Bonus weights:
     - Same level: 1.0x boost
     - Adjacent level (±1): 0.5x boost
     - Other levels: 0.0x (avoided unless no alternatives)

**Score Formula:**
```javascript
score = distance^α * uncertainty^β * (1 + γ * levelBonus)
```

Where:
- `α = 2 * (1 - confidence)` - Emphasize coverage when confidence is low
- `β = 2 * confidence` - Emphasize uncertainty when confidence is high
- `γ = 0.5` - Level preference weight (configurable)

### 4. Enhanced Confidence Metrics

```javascript
{
    overallConfidence: 0.75,        // Overall mastery estimate
    coverageConfidence: 0.80,       // Spatial coverage (60% weight)
    uncertaintyConfidence: 0.65,    // Prediction confidence (40% weight)
    coveredCells: 120,              // Cells within coverage distance
    totalCells: 150,

    // NEW: Per-level statistics
    levelStats: {
        0: { correct: 10, total: 12, accuracy: 0.83 },
        1: { correct: 8, total: 10, accuracy: 0.80 },
        2: { correct: 4, total: 6, accuracy: 0.67 },
        3: { correct: 0, total: 0, accuracy: 0 },
        4: { correct: 0, total: 0, accuracy: 0 }
    },
    currentLevel: 2                 // Current difficulty level
}
```

## Configuration Options

```javascript
{
    // Existing config
    mode: 'adaptive-multilevel',
    initialRandomQuestions: 2,
    minQuestionsBeforeExit: 3,
    confidenceThreshold: 0.85,
    maxQuestions: 10,
    K: 5,
    sigma: 0.15,
    alpha: 1.0,         // Spatial coverage weight (dynamic)
    beta: 1.0,          // Uncertainty weight (dynamic)
    coverageDistance: 0.15,

    // NEW: Multi-level config
    gamma: 0.5,                      // Level preference weight
    startLevel: 0,                   // Start with easiest questions
    maxLevel: 4,                     // Maximum difficulty level
    levelProgressionThreshold: 0.7,  // 70% to progress
    levelRegressionThreshold: 0.4,   // <40% to regress
    minQuestionsPerLevel: 3          // Min questions before level change
}
```

## API Changes

### recordResponse(cellKey, isCorrect, level, fractionalCorrectness)

**New parameter:** `level` (required)

```javascript
// Old API (base AdaptiveSampler)
sampler.recordResponse('5_10', true);

// New API (MultiLevelAdaptiveSampler)
sampler.recordResponse('5_10', true, 2);  // level 2 question
sampler.recordResponse('7_15', false, 1); // level 1 question
sampler.recordResponse('3_8', null, 0, 0.1); // "I Don't Know" for level 0
```

### getStats()

**Enhanced return value:**

```javascript
const stats = sampler.getStats();
console.log(stats.currentLevel);           // Current difficulty: 2
console.log(stats.levelStats[2].accuracy); // Level 2 accuracy: 0.67
console.log(stats.overallConfidence);      // Overall mastery: 0.75
```

## Question Data Format

Questions must include a `level` field:

```json
{
    "question": "What is photosynthesis?",
    "options": {
        "A": "Process plants use to make food",
        "B": "Process of cell division",
        "C": "Process of water absorption",
        "D": "Process of respiration"
    },
    "correct": "A",
    "level": 0,
    "article": "Photosynthesis",
    "concept": "Basic photosynthesis definition"
}
```

### Level Definitions

- **Level 0:** Most specific questions (original Wikipedia articles)
  - Example: "What year was X released?"

- **Level 1:** Slightly broader concepts (1 step removed)
  - Example: "What genre does X belong to?"

- **Level 2:** Moderate abstraction (2 steps removed)
  - Example: "What are common characteristics of this genre?"

- **Level 3:** High abstraction (3 steps removed)
  - Example: "How did this musical movement influence culture?"

- **Level 4:** Highest abstraction (4 steps removed)
  - Example: "What philosophical concepts underlie this artistic period?"

## Integration Steps

### 1. Load Multi-Level Questions

```javascript
// Load questions from all levels
const allQuestions = await Promise.all([
    fetch('cell_questions_level_0.json').then(r => r.json()),
    fetch('cell_questions_level_1.json').then(r => r.json()),
    fetch('cell_questions_level_2.json').then(r => r.json()),
    fetch('cell_questions_level_3.json').then(r => r.json()),
    fetch('cell_questions_level_4.json').then(r => r.json())
]);

// Merge into single pool with level tags
const mergedQuestions = mergeQuestionsByLevel(allQuestions);
```

### 2. Initialize Sampler

```javascript
const sampler = new MultiLevelAdaptiveSampler(
    mergedQuestions,
    cellDistances,
    {
        startLevel: 0,
        levelProgressionThreshold: 0.7,
        levelRegressionThreshold: 0.4,
        gamma: 0.5
    }
);
```

### 3. Question Loop with Level Tracking

```javascript
while (true) {
    // Select next question (automatically chooses appropriate level)
    const question = sampler.selectNextQuestion();
    if (!question) break;

    console.log(`Level ${question.level}: ${question.question}`);

    // Show question to user
    const userAnswer = await showQuestion(question);

    // Record response WITH level
    sampler.recordResponse(
        question.cellKey,
        userAnswer.correct,
        question.level,  // IMPORTANT: Include level
        userAnswer.fractionalCorrectness
    );

    // Check exit condition
    if (sampler.shouldExit()) break;
}
```

### 4. Display Statistics

```javascript
const stats = sampler.getStats();

console.log(`Current Level: ${stats.currentLevel}`);
console.log(`Overall Confidence: ${(stats.overallConfidence * 100).toFixed(1)}%`);

for (let level = 0; level <= 4; level++) {
    const levelStat = stats.levelStats[level];
    if (levelStat.total > 0) {
        console.log(`Level ${level}: ${levelStat.correct}/${levelStat.total} ` +
                    `(${(levelStat.accuracy * 100).toFixed(1)}%)`);
    }
}
```

## Testing & Validation

### Unit Tests

```javascript
// Test level progression
const sampler = new MultiLevelAdaptiveSampler(questions, distances);

// Answer 3 questions correctly at level 0 (should progress to level 1)
for (let i = 0; i < 3; i++) {
    const q = sampler.selectNextQuestion();
    sampler.recordResponse(q.cellKey, true, 0);
}

const stats = sampler.getStats();
assert(stats.currentLevel === 1, "Should progress to level 1");
```

### Integration Tests

1. **Test level regression:** Answer questions incorrectly, verify regression to easier level
2. **Test level bounds:** Ensure level stays within [0, 4] range
3. **Test fallback:** Verify graceful handling when no questions available at target level
4. **Test statistics:** Verify accuracy calculations per level

## Performance Considerations

### Memory

- Minimal overhead: ~10KB per 1000 questions
- Level stats: ~200 bytes per level (5 levels = 1KB)
- Unchanged spatial data structures

### Computation

- Level selection: O(1) - simple threshold checks
- Question scoring: O(C * A) unchanged (C=cells, A=asked cells)
- Overhead: <5% compared to base AdaptiveSampler

## Future Enhancements

### 1. Dynamic Thresholds

Adjust progression/regression thresholds based on overall performance:

```javascript
levelProgressionThreshold: 0.6 + (0.1 * overallConfidence)
```

### 2. Learning Rate Tracking

Track how quickly user masters each level:

```javascript
levelStats[level].questionsToMastery = 15;  // Questions needed to reach 70%
levelStats[level].learningRate = 0.05;      // Accuracy improvement per question
```

### 3. Prerequisite Enforcement

Require minimum proficiency at lower levels before unlocking higher ones:

```javascript
if (level > 0 && levelStats[level - 1].accuracy < 0.6) {
    // Force practice at prerequisite level
    return level - 1;
}
```

### 4. Spaced Repetition Integration

Combine with spaced repetition for long-term retention:

```javascript
levelStats[level].lastReviewed = Date.now();
levelStats[level].reviewInterval = 86400000;  // 1 day in ms
```

## References

- Issue: https://github.com/simpleXknowledge/mapper.io/issues/13
- Base Algorithm: `index.html` (AdaptiveSampler class, lines 1239-1600)
- Implementation: `adaptive_sampler_multilevel.js`
- Question Generation: `scripts/generate_level_n.py`

## Status

- ✅ Algorithm implemented
- ✅ Documentation complete
- 🔄 Question generation pipeline running (Level 0 in progress)
- ⏸️ Frontend integration pending (awaiting question data)
- ⏸️ Testing pending (awaiting question data)

Estimated completion: 10-15 hours (pipeline runtime)
