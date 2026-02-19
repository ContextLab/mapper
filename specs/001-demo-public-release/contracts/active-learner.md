# Contract: Active Learning Module

**Consumer**: `src/ui/quiz.js`, `src/ui/modes.js`
**Provider**: `src/learning/sampler.js`, `src/learning/estimator.js`, `src/learning/curriculum.js`

## Estimator Interface

Maintains a Gaussian Process surrogate model over the active domain's
grid cells. Recomputed after each response.

```typescript
// src/learning/estimator.js

interface CellEstimate {
  gx: number;
  gy: number;
  value: number;         // Estimated knowledge 0.0–1.0
  uncertainty: number;   // Predictive variance σ² (0.0–1.0)
  evidenceCount: number; // Number of nearby observations
  state: "unknown" | "uncertain" | "estimated";
}

interface Estimator {
  // Initialize with domain grid dimensions
  init(gridSize: number, region: Region): void;

  // Record a new observation (triggers GP update)
  // Uses Woodbury identity for O(N²) incremental update
  observe(x: number, y: number, correct: boolean): void;

  // Get estimates for all cells (or viewport subset)
  // Returns within 15ms for 1500 cells with N≤50 observations
  predict(viewport?: Region): CellEstimate[];

  // Get estimate for a single cell
  predictCell(gx: number, gy: number): CellEstimate;

  // Reset all observations (FR-021)
  reset(): void;

  // Restore from persisted responses
  restore(responses: UserResponse[]): void;
}
```

**State derivation rules (FR-017)**:
- `unknown`: `evidenceCount === 0` (high prior σ², no nearby data)
- `uncertain`: `evidenceCount >= 1` AND `0.3 < value < 0.7` AND
  `uncertainty < 0.2` (conflicting nearby answers)
- `estimated`: `evidenceCount >= 1` AND NOT uncertain

## Sampler Interface

Selects the next question using expected information gain, curriculum
weighting, and viewport restriction.

```typescript
// src/learning/sampler.js

interface SamplerConfig {
  viewportRestriction: boolean;  // FR-016: only visible cells
  curriculumWeight: number;      // FR-018: 0.0 (niche) to 1.0 (landmark)
}

interface QuestionScore {
  questionId: string;
  score: number;          // Expected information gain
  cellGx: number;
  cellGy: number;
}

interface Sampler {
  // Select best next question from available pool
  // Must complete in <50ms (typically ~15ms)
  selectNext(
    questions: Question[],         // Available unanswered questions
    estimates: CellEstimate[],     // Current knowledge estimates
    viewport: Region,              // Visible area (FR-016)
    answeredIds: Set<string>       // Already answered question IDs
  ): QuestionScore;

  // Select question matching a specific mode (FR-010)
  selectByMode(
    mode: "easy" | "hardest-can-answer" | "dont-know",
    questions: Question[],
    estimates: CellEstimate[],
    viewport: Region,
    answeredIds: Set<string>
  ): QuestionScore;

  // Get top-K scored questions (for debugging/insights)
  scoreAll(
    questions: Question[],
    estimates: CellEstimate[],
    viewport: Region,
    answeredIds: Set<string>
  ): QuestionScore[];
}
```

**Mode strategies (FR-010)**:
- `"easy"`: Lowest difficulty in highest-value cells
- `"hardest-can-answer"`: Highest difficulty in cells where `value > 0.6`
- `"dont-know"`: Highest difficulty in cells where `value < 0.3`

## Curriculum Interface

Controls the landmark → niche progression (FR-018).

```typescript
// src/learning/curriculum.js

interface Curriculum {
  // Compute current curriculum weight based on coverage
  // Returns 1.0 (landmark-heavy) early, trends toward 0.0 (niche-heavy)
  getWeight(answeredCount: number, coveragePercent: number): number;

  // Get centrality scores for cells (precomputed from article density)
  getCentrality(domainId: string): Map<string, number>;
}
```

**Adaptive transition rule (FR-018)**:
- NOT based on fixed question count
- Based on cumulative coverage: `coveragePercent = cells_with_evidence / total_cells`
- Weight = `1.0 - sigmoid((coveragePercent - 0.3) * 10)`
  (sharp transition around 30% coverage)
