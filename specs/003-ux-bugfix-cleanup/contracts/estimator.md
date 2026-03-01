# Contract: GP Estimator Interface

**Module**: `src/learning/estimator.js`
**Date**: 2026-02-27

## Public API

### `constructor()`
Creates an uninitialized estimator. Must call `init()` before use.

### `init(gridSize: number, region: {x_min, x_max, y_min, y_max})`
Initialize with domain grid dimensions and bounding region. Precomputes cell centers. Resets all observations.

### `observe(x: number, y: number, correct: boolean, lengthScale?: number, difficulty?: number)`
Record a correct/incorrect answer observation.
- `x`, `y`: Normalized coordinates [0,1]
- `correct`: Whether the answer was correct
- `lengthScale`: Per-observation RBF width (default: `DEFAULT_LENGTH_SCALE`)
- `difficulty`: Question difficulty 1–4 (default: 3)

**Weight behavior** (post-fix):
- If `correct === true`: uses `CORRECT_WEIGHT_MAP[difficulty]` → `{1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0}`
- If `correct === false`: uses `INCORRECT_WEIGHT_MAP[difficulty]` → `{1: 1.0, 2: 0.75, 3: 0.5, 4: 0.25}`

### `observeSkip(x: number, y: number, lengthScale?: number, difficulty?: number)`
Record a skipped question. Uses `SKIP_KNOWLEDGE_VALUE = 0.05`.
- `lengthScale`: Should be same as normal observations (no 0.5× reduction)
- Weight uses `INCORRECT_WEIGHT_MAP[difficulty]` (same as wrong answers, since skip indicates lack of knowledge)

**Post-fix behavior**: Skip produces stronger negative evidence than wrong answers because:
1. Same spatial footprint (no length scale reduction)
2. Lower knowledge value (0.05 vs 0.0)
3. Same inverted difficulty weighting

### `predict(viewport?: {x_min, x_max, y_min, y_max}): CellEstimate[]`
Get estimates for all cells (or viewport subset).

**Returns**: Array of `CellEstimate` objects:
```
{
  gx: number,        // Grid x index (0–49)
  gy: number,        // Grid y index (0–49)
  value: number,     // [0, 1] predicted knowledge
  uncertainty: number, // [0, 1] posterior uncertainty
  evidenceCount: number,
  state: 'unknown' | 'uncertain' | 'estimated',
  difficultyLevel: number  // IRT level 0–4
}
```

**Post-fix guarantees**:
- Never returns NaN or Infinity values (falls back to prior mean 0.5)
- Handles up to 500 observations without Cholesky failure (adaptive jitter)
- Single observation changes `value` by at most ~0.15 (no discontinuous jumps)
- `predict()` completes in <15ms for N≤200 observations on mid-range hardware

### `predictCell(gx: number, gy: number): CellEstimate | null`
Get estimate for a single cell by grid coordinates.

### `reset()`
Clear all observations and cached matrices.

### `restore(responses: UserResponse[], uniformLengthScale?: number, questionIndex?: Map)`
Rebuild estimator state from persisted responses. Each response's difficulty is looked up from `questionIndex` if provided.

## Internal Stability Contract (choleskySolve)

**Module**: `src/utils/math.js`

### `choleskySolve(K: Float64Array[], b: Float64Array): Float64Array`

**Post-fix behavior**:
1. Adaptive jitter: `JITTER = 1e-6 * Math.max(1, n / 10)` where `n` is matrix size
2. On negative diagonal during decomposition: retry with 10× jitter (max 3 retries)
3. On any NaN in solution: return zero vector (caller falls back to prior mean)
4. Console warning on fallback (but no error thrown — never crashes)

**Performance**: O(n³) Cholesky decomposition. Acceptable for n ≤ 500.
