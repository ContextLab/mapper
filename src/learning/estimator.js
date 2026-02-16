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

// GP hyperparameters — tuned for normalized [0,1] embedding space
const DEFAULT_LENGTH_SCALE = 0.15;
const DEFAULT_SIGNAL_VARIANCE = 1.0;
const NOISE_VARIANCE = 0.1; // Observation noise σ²_n (accounts for guessing)
const PRIOR_MEAN = 0.5; // Uninformative prior: 50% knowledge

export class Estimator {
  constructor() {
    this._gridSize = 0;
    this._region = null;
    this._cells = []; // [{gx, gy, cx, cy}] — grid cell centers
    this._observations = []; // [{x, y, value}] — raw observations
    this._alpha = null; // Precomputed (K + σ²I)^{-1} · (y - μ)
    this._obsPoints = []; // [{x, y}] for kernel vector computation
    this._obsValues = null; // Float64Array of observation values
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
   * correct=true → value=1, correct=false → value=0.
   */
  observe(x, y, correct) {
    const value = correct ? 1.0 : 0.0;
    this._observations.push({ x, y, value });
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
      }));
    }

    const kernelFn = (d) => matern32(d, this._lengthScale, this._signalVariance);
    const results = new Array(cells.length);

    for (let i = 0; i < cells.length; i++) {
      const cell = cells[i];
      const testPt = { x: cell.cx, y: cell.cy };

      // k* = kernel vector between test point and observations
      const kStar = kernelVector(testPt, this._obsPoints, kernelFn);

      // Posterior mean: μ* = μ_prior + k*^T · α
      const meanShift = dot(kStar, this._alpha);
      const value = clamp(PRIOR_MEAN + meanShift, 0, 1);

      // Posterior variance: σ²* = k** - k*^T · (K+σ²I)^{-1} · k*
      const kSelf = this._signalVariance; // k(x*, x*) = σ²
      const kSolve = choleskySolve(this._K_noisy, kStar);
      const variance = Math.max(0, kSelf - dot(kStar, kSolve));
      const uncertainty = clamp(Math.sqrt(variance) / Math.sqrt(this._signalVariance), 0, 1);

      // Count nearby observations (within 2x length-scale)
      const evidenceRadius = this._lengthScale * 2;
      let evidenceCount = 0;
      for (let j = 0; j < n; j++) {
        const d = euclidean(cell.cx, cell.cy, this._obsPoints[j].x, this._obsPoints[j].y);
        if (d <= evidenceRadius) evidenceCount++;
      }

      // State derivation per FR-017
      let state;
      if (evidenceCount === 0) {
        state = 'unknown';
      } else if (value > 0.3 && value < 0.7 && uncertainty < 0.2) {
        state = 'uncertain';
      } else {
        state = 'estimated';
      }

      results[i] = { gx: cell.gx, gy: cell.gy, value, uncertainty, evidenceCount, state };
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
      };
    }

    const kernelFn = (d) => matern32(d, this._lengthScale, this._signalVariance);
    const testPt = { x: cell.cx, y: cell.cy };
    const kStar = kernelVector(testPt, this._obsPoints, kernelFn);
    const meanShift = dot(kStar, this._alpha);
    const value = clamp(PRIOR_MEAN + meanShift, 0, 1);

    const kSelf = this._signalVariance;
    const kSolve = choleskySolve(this._K_noisy, kStar);
    const variance = Math.max(0, kSelf - dot(kStar, kSolve));
    const uncertainty = clamp(Math.sqrt(variance) / Math.sqrt(this._signalVariance), 0, 1);

    const evidenceRadius = this._lengthScale * 2;
    let evidenceCount = 0;
    for (let j = 0; j < this._observations.length; j++) {
      const d = euclidean(cell.cx, cell.cy, this._obsPoints[j].x, this._obsPoints[j].y);
      if (d <= evidenceRadius) evidenceCount++;
    }

    let state;
    if (evidenceCount === 0) {
      state = 'unknown';
    } else if (value > 0.3 && value < 0.7 && uncertainty < 0.2) {
      state = 'uncertain';
    } else {
      state = 'estimated';
    }

    return { gx, gy, value, uncertainty, evidenceCount, state };
  }

  /**
   * Reset all observations (FR-021).
   */
  reset() {
    this._observations = [];
    this._alpha = null;
    this._obsPoints = [];
    this._obsValues = null;
    this._K_noisy = null;
  }

  /**
   * Restore from persisted UserResponse[].
   * Filters responses to those within this domain's region,
   * then rebuilds the GP posterior.
   */
  restore(responses) {
    this.reset();

    if (!this._region || !responses || responses.length === 0) return;

    for (const r of responses) {
      // Use question coordinates if available, otherwise skip
      if (r.x != null && r.y != null) {
        this._observations.push({
          x: r.x,
          y: r.y,
          value: r.is_correct ? 1.0 : 0.0,
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
   */
  _recompute() {
    const n = this._observations.length;
    if (n === 0) {
      this._alpha = null;
      this._obsPoints = [];
      this._obsValues = null;
      this._K_noisy = null;
      return;
    }

    this._obsPoints = this._observations.map((o) => ({ x: o.x, y: o.y }));
    this._obsValues = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      this._obsValues[i] = this._observations[i].value - PRIOR_MEAN;
    }

    const kernelFn = (d) => matern32(d, this._lengthScale, this._signalVariance);
    const K = kernelMatrix(this._obsPoints, kernelFn);

    // Add noise variance to diagonal: K_noisy = K + σ²_n · I
    this._K_noisy = K.map((row) => new Float64Array(row));
    for (let i = 0; i < n; i++) {
      this._K_noisy[i][i] += NOISE_VARIANCE;
    }

    // α = (K + σ²_n·I)^{-1} · (y - μ)
    this._alpha = choleskySolve(this._K_noisy, this._obsValues);
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
