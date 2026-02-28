/**
 * Gaussian Process knowledge estimator with Matérn 3/2 kernel.
 *
 * Maintains a GP surrogate model over a domain's grid cells.
 * Uses Cholesky-based exact inference, recomputed after each observation.
 * Performance target: predict() for 1500 cells with N≤50 obs in <15ms.
 */

import {
  matern32,
  euclidean,
  kernelMatrix,
  kernelVector,
  choleskySolve,
  dot,
  clamp,
} from '../utils/math.js';

// GP hyperparameters — calibrated for cross-domain prediction in [0,1] embedding space.
// Matérn 3/2 correlation at key distances (l=0.15):
//   d=0.05 → k≈0.82  (same sub-domain: strong prediction)
//   d=0.10 → k≈0.56  (adjacent sub-domain: meaningful)
//   d=0.15 → k≈0.35  (related domain: visible, non-trivial)
//   d=0.20 → k≈0.21  (distant but related: faint but present)
//   d=0.30 → k≈0.07  (unrelated domain: negligible)
// These values satisfy SC-009: Math→Probability produces non-zero cross-domain estimates.
export const DEFAULT_LENGTH_SCALE = 0.15;
const DEFAULT_SIGNAL_VARIANCE = 1.0;
const NOISE_VARIANCE = 0.1;
const PRIOR_MEAN = 0.5;

// Skip observations use a much lower knowledge value than the prior mean.
// Skipping indicates uncertainty, not 50% knowledge — treated as near-zero evidence.
const SKIP_KNOWLEDGE_VALUE = 0.05;

// IRT constants for difficulty level estimation (FR-V050, CL-042, CL-043).
// GP value in [0,1] maps to IRT ability θ via: θ = 4 × value - 2 (range [-2, 2]).
// Thresholds in [0,1] space where mastery transitions between levels (L0→L1→L2→L3→L4).
export const IRT_THRESHOLDS = [0.125, 0.375, 0.625, 0.875];
export const IRT_DISCRIMINATION = 1.5;

// Difficulty-based weight modulation for RBF kernel (CL-047: independent of IRT layer).
// Two maps: correct answers reward harder questions more, incorrect/skip answers
// penalize easier questions more (getting a hard question wrong is expected).
const CORRECT_WEIGHT_MAP = {
  1: 0.25,  // Easy correct: weak positive evidence (expected)
  2: 0.5,   // Medium correct: moderate positive evidence
  3: 0.75,  // Hard correct: strong positive evidence
  4: 1.0,   // Expert correct: full positive evidence weight
};
const INCORRECT_WEIGHT_MAP = {
  1: 1.0,   // Easy wrong: full negative evidence (should know this)
  2: 0.75,  // Medium wrong: strong negative evidence
  3: 0.5,   // Hard wrong: moderate negative evidence
  4: 0.25,  // Expert wrong: weak negative evidence (expected to miss)
};

export class Estimator {
  constructor() {
    this._gridSize = 0;
    this._region = null;
    this._cells = [];
    this._observations = []; // [{x, y, value, lengthScale, difficultyWeight}]
    this._alpha = null;
    this._obsPoints = [];
    this._obsLengthScales = null; // Float64Array of per-observation length scales
    this._obsDifficultyWeights = null; // Float64Array of per-observation difficulty weights
    this._obsValues = null;
    this._lengthScale = DEFAULT_LENGTH_SCALE;
    this._signalVariance = DEFAULT_SIGNAL_VARIANCE;
  }

  /**
   * Initialize with domain grid dimensions and region.
   * Precomputes cell center coordinates.
   */
  init(gridSize, region) {
    this._gridSize = gridSize;
    this._region = region;
    this._observations = [];
    this._alpha = null;
    this._obsPoints = [];
    this._obsValues = null;

    // Precompute cell centers in normalized coordinates
    this._cells = [];
    const xSpan = region.x_max - region.x_min;
    const ySpan = region.y_max - region.y_min;
    const cellW = xSpan / gridSize;
    const cellH = ySpan / gridSize;

    for (let gy = 0; gy < gridSize; gy++) {
      for (let gx = 0; gx < gridSize; gx++) {
        this._cells.push({
          gx,
          gy,
          cx: region.x_min + (gx + 0.5) * cellW,
          cy: region.y_min + (gy + 0.5) * cellH,
        });
      }
    }
  }

  /**
   * Record a new observation and recompute GP posterior.
   * @param {number} x - Normalized x coordinate
   * @param {number} y - Normalized y coordinate
   * @param {boolean} correct - Whether the answer was correct
   * @param {number} [lengthScale] - Per-observation RBF width (defaults to DEFAULT_LENGTH_SCALE)
   * @param {number} [difficulty] - Question difficulty (1-4) for weight modulation
   */
  observe(x, y, correct, lengthScale, difficulty) {
    const value = correct ? 1.0 : 0.0;
    const weightMap = correct ? CORRECT_WEIGHT_MAP : INCORRECT_WEIGHT_MAP;
    const difficultyWeight = weightMap[difficulty] || weightMap[3];
    this._observations.push({
      x,
      y,
      value,
      lengthScale: lengthScale || this._lengthScale,
      difficultyWeight,
    });
    this._recompute();
  }

  /**
   * Record a skipped question — labels knowledge at 5% (near-zero) with reduced spatial influence.
   * Skipping indicates the user doesn't know the answer, so it's treated as weak negative evidence.
   * @param {number} x - Normalized x coordinate
   * @param {number} y - Normalized y coordinate
   * @param {number} lengthScale - Reduced RBF width for skip observations
   * @param {number} [difficulty] - Question difficulty (1-4) for weight modulation
   */
  observeSkip(x, y, lengthScale, difficulty) {
    const difficultyWeight = INCORRECT_WEIGHT_MAP[difficulty] || INCORRECT_WEIGHT_MAP[3];
    this._observations.push({
      x,
      y,
      value: SKIP_KNOWLEDGE_VALUE,
      lengthScale: lengthScale || this._lengthScale,
      difficultyWeight,
    });
    this._recompute();
  }

  /**
   * Get estimates for all cells (or viewport subset).
   * Returns CellEstimate[] per contracts/active-learner.md.
   */
  predict(viewport) {
    const cells = viewport ? this._cellsInViewport(viewport) : this._cells;
    const n = this._observations.length;

    if (n === 0) {
      return cells.map((c) => ({
        gx: c.gx,
        gy: c.gy,
        value: PRIOR_MEAN,
        uncertainty: 1.0,
        evidenceCount: 0,
        state: 'unknown',
        difficultyLevel: IRT_THRESHOLDS.reduce((lvl, t) => lvl + (PRIOR_MEAN >= t ? 1 : 0), 0),
      }));
    }

    const sv = this._signalVariance;
    const defaultLS = this._lengthScale;
    const results = new Array(cells.length);

    for (let i = 0; i < cells.length; i++) {
      const cell = cells[i];

      // k* with per-observation length scales and difficulty weights:
      // k*[j] = matern32(d, sqrt(l_default * l_j)) * w_j
      // Test points use the observation's difficulty weight directly (not sqrt)
      // since test points don't have their own difficulty.
      const kStar = new Float64Array(n);
      for (let j = 0; j < n; j++) {
        const d = euclidean(cell.cx, cell.cy, this._obsPoints[j].x, this._obsPoints[j].y);
        const lMerged = Math.sqrt(defaultLS * this._obsLengthScales[j]);
        const wj = this._obsDifficultyWeights ? this._obsDifficultyWeights[j] : 1.0;
        kStar[j] = matern32(d, lMerged, sv) * wj;
      }

      const meanShift = dot(kStar, this._alpha);
      const value = clamp(PRIOR_MEAN + meanShift, 0, 1);

      const kSelf = sv;
      const kSolve = choleskySolve(this._K_noisy, kStar);
      const variance = Math.max(0, kSelf - dot(kStar, kSolve));
      const uncertainty = clamp(Math.sqrt(variance) / Math.sqrt(sv), 0, 1);

      // Count nearby observations using each observation's own length scale
      let evidenceCount = 0;
      for (let j = 0; j < n; j++) {
        const d = euclidean(cell.cx, cell.cy, this._obsPoints[j].x, this._obsPoints[j].y);
        if (d <= this._obsLengthScales[j] * 2) evidenceCount++;
      }

      let state;
      if (evidenceCount === 0) {
        state = 'unknown';
      } else if (value > 0.3 && value < 0.7 && uncertainty < 0.2) {
        state = 'uncertain';
      } else {
        state = 'estimated';
      }

      // NaN safety: if numerical instability produced bad values, use prior
      const safeValue = isFinite(value) ? value : PRIOR_MEAN;
      const safeUncertainty = isFinite(uncertainty) ? uncertainty : 1.0;

      // IRT difficulty level: count of thresholds where GP value >= threshold (0–4)
      const difficultyLevel = IRT_THRESHOLDS.reduce((lvl, t) => lvl + (safeValue >= t ? 1 : 0), 0);

      results[i] = { gx: cell.gx, gy: cell.gy, value: safeValue, uncertainty: safeUncertainty, evidenceCount, state, difficultyLevel };
    }

    return results;
  }

  /**
   * Get estimate for a single cell.
   */
  predictCell(gx, gy) {
    const cell = this._cells.find((c) => c.gx === gx && c.gy === gy);
    if (!cell) return null;

    if (this._observations.length === 0) {
      return {
        gx, gy,
        value: PRIOR_MEAN,
        uncertainty: 1.0,
        evidenceCount: 0,
        state: 'unknown',
        difficultyLevel: IRT_THRESHOLDS.reduce((lvl, t) => lvl + (PRIOR_MEAN >= t ? 1 : 0), 0),
      };
    }

    const n = this._observations.length;
    const sv = this._signalVariance;
    const defaultLS = this._lengthScale;

    // k* with per-observation length scales and difficulty weights
    const kStar = new Float64Array(n);
    for (let j = 0; j < n; j++) {
      const d = euclidean(cell.cx, cell.cy, this._obsPoints[j].x, this._obsPoints[j].y);
      const lMerged = Math.sqrt(defaultLS * this._obsLengthScales[j]);
      const wj = this._obsDifficultyWeights ? this._obsDifficultyWeights[j] : 1.0;
      kStar[j] = matern32(d, lMerged, sv) * wj;
    }
    const meanShift = dot(kStar, this._alpha);
    const value = clamp(PRIOR_MEAN + meanShift, 0, 1);

    const kSelf = sv;
    const kSolve = choleskySolve(this._K_noisy, kStar);
    const variance = Math.max(0, kSelf - dot(kStar, kSolve));
    const uncertainty = clamp(Math.sqrt(variance) / Math.sqrt(sv), 0, 1);

    let evidenceCount = 0;
    for (let j = 0; j < n; j++) {
      const d = euclidean(cell.cx, cell.cy, this._obsPoints[j].x, this._obsPoints[j].y);
      if (d <= this._obsLengthScales[j] * 2) evidenceCount++;
    }

    let state;
    if (evidenceCount === 0) {
      state = 'unknown';
    } else if (value > 0.3 && value < 0.7 && uncertainty < 0.2) {
      state = 'uncertain';
    } else {
      state = 'estimated';
    }

    // NaN safety: if numerical instability produced bad values, use prior
    const safeValue = isFinite(value) ? value : PRIOR_MEAN;
    const safeUncertainty = isFinite(uncertainty) ? uncertainty : 1.0;

    const difficultyLevel = IRT_THRESHOLDS.reduce((lvl, t) => lvl + (safeValue >= t ? 1 : 0), 0);

    return { gx, gy, value: safeValue, uncertainty: safeUncertainty, evidenceCount, state, difficultyLevel };
  }

  /**
   * Reset all observations (FR-021).
   */
  reset() {
    this._observations = [];
    this._alpha = null;
    this._obsPoints = [];
    this._obsValues = null;
    this._obsLengthScales = null;
    this._obsDifficultyWeights = null;
    this._K_noisy = null;
  }

  /**
   * Restore from persisted UserResponse[].
   * Each response may include a `lengthScale` for per-observation RBF width.
   * @param {Array} responses - Array of UserResponse objects
   * @param {number} uniformLengthScale - Uniform length scale for all observations
   * @param {Map} [questionIndex] - Optional map of question_id -> question for difficulty lookup
   */
  restore(responses, uniformLengthScale, questionIndex) {
    this.reset();

    if (!this._region || !responses || responses.length === 0) return;

    // Use a uniform length scale for all restored observations to ensure
    // consistent smoothness. Any per-observation lengths from older exports
    // are intentionally ignored.
    const ls = uniformLengthScale || this._lengthScale;

    for (const r of responses) {
      if (r.x != null && r.y != null) {
        const isSkipped = !!r.is_skipped;
        const isCorrect = !!r.is_correct;
        // Look up difficulty from question index if available
        const question = questionIndex?.get(r.question_id);
        const difficulty = question?.difficulty;
        // Correct answers use CORRECT_WEIGHT_MAP; incorrect/skip use INCORRECT_WEIGHT_MAP
        const weightMap = (!isSkipped && isCorrect) ? CORRECT_WEIGHT_MAP : INCORRECT_WEIGHT_MAP;
        const difficultyWeight = weightMap[difficulty] || weightMap[3];
        this._observations.push({
          x: r.x,
          y: r.y,
          value: isSkipped ? SKIP_KNOWLEDGE_VALUE : (isCorrect ? 1.0 : 0.0),
          lengthScale: ls, // Full length scale for all observations (no skip reduction)
          difficultyWeight,
        });
      }
    }

    if (this._observations.length > 0) {
      this._recompute();
    }
  }

  // ---- Private methods ----

  /**
   * Recompute the GP posterior: build K, solve for α.
   * Called after any observation change.
   *
   * Difficulty-based weight modulation: Each observation's kernel contribution is
   * scaled by its difficulty weight. Higher difficulty questions (weight closer to 1.0)
   * have more influence on the GP posterior, while lower difficulty questions
   * (weight closer to 0.25) have reduced influence.
   */
  _recompute() {
    const n = this._observations.length;
    if (n === 0) {
      this._alpha = null;
      this._obsPoints = [];
      this._obsValues = null;
      this._obsLengthScales = null;
      this._obsDifficultyWeights = null;
      this._K_noisy = null;
      return;
    }

    this._obsPoints = this._observations.map((o) => ({ x: o.x, y: o.y }));
    this._obsValues = new Float64Array(n);
    this._obsLengthScales = new Float64Array(n);
    this._obsDifficultyWeights = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      this._obsValues[i] = this._observations[i].value - PRIOR_MEAN;
      this._obsLengthScales[i] = this._observations[i].lengthScale || this._lengthScale;
      this._obsDifficultyWeights[i] = this._observations[i].difficultyWeight || CORRECT_WEIGHT_MAP[3];
    }

    // Build K with per-observation length scales and difficulty weights:
    // K[i,j] = matern32(d, sqrt(l_i * l_j)) * sqrt(w_i * w_j)
    // The sqrt of product form ensures symmetric weighting between observations.
    const K = new Array(n);
    for (let i = 0; i < n; i++) {
      K[i] = new Float64Array(n);
    }
    const sv = this._signalVariance;
    for (let i = 0; i < n; i++) {
      const li = this._obsLengthScales[i];
      const wi = this._obsDifficultyWeights[i];
      for (let j = i; j < n; j++) {
        const lj = this._obsLengthScales[j];
        const wj = this._obsDifficultyWeights[j];
        const lMerged = Math.sqrt(li * lj);
        const wMerged = Math.sqrt(wi * wj); // Symmetric difficulty weight
        const d = euclidean(this._obsPoints[i].x, this._obsPoints[i].y,
                           this._obsPoints[j].x, this._obsPoints[j].y);
        const val = matern32(d, lMerged, sv) * wMerged;
        K[i][j] = val;
        K[j][i] = val;
      }
    }

    this._K_noisy = K.map((row) => new Float64Array(row));
    for (let i = 0; i < n; i++) {
      this._K_noisy[i][i] += NOISE_VARIANCE;
    }

    this._alpha = choleskySolve(this._K_noisy, this._obsValues);

    // Safety: if Cholesky returned a zero vector (NaN fallback), log a warning
    if (this._alpha.every(v => v === 0) && this._obsValues.some(v => v !== 0)) {
      console.warn('[estimator] Cholesky returned fallback zero vector — predictions will use prior mean');
    }
  }

  /**
   * Filter cells to those within a viewport region.
   */
  _cellsInViewport(viewport) {
    return this._cells.filter(
      (c) =>
        c.cx >= viewport.x_min &&
        c.cx <= viewport.x_max &&
        c.cy >= viewport.y_min &&
        c.cy <= viewport.y_max
    );
  }
}
