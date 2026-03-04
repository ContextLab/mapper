/**
 * Numerical equivalence tests: verify incremental Cholesky updates produce
 * the same results as full batch recomputation.
 */
import { describe, it, expect } from 'vitest';
import { Estimator } from '../../src/learning/estimator.js';

const GRID_SIZE = 50;
const REGION = { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };

// Tolerance for floating-point comparison.
// Incremental Cholesky does identical arithmetic for existing rows, so the only
// divergence comes from the α re-solve (forward/backward substitution accumulates
// tiny differences). 1e-10 is conservative for n ≤ 50.
const ALPHA_TOL = 1e-10;
const PREDICT_TOL = 1e-8;

function mulberry32(seed) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Create a "batch" estimator that does full recomputation on every observe().
 * We achieve this by replaying all observations from scratch each time.
 */
function batchObserve(observations) {
  const est = new Estimator();
  est.init(GRID_SIZE, REGION);
  // restore() does a single _recompute at the end — batch mode
  const responses = observations.map((o) => ({
    x: o.x,
    y: o.y,
    is_correct: o.value === 1.0,
    is_skipped: o.value === 0.05,
    difficulty: o.difficulty,
  }));
  est.restore(responses);
  return est;
}

describe('Incremental GP Equivalence', () => {
  it('incremental α matches batch α after each observation (spread observations)', () => {
    const rand = mulberry32(42);
    const incEst = new Estimator();
    incEst.init(GRID_SIZE, REGION);

    const allObs = [];

    for (let i = 0; i < 30; i++) {
      const x = rand();
      const y = rand();
      const correct = rand() > 0.4;
      const difficulty = Math.floor(rand() * 4) + 1;

      incEst.observe(x, y, correct, undefined, difficulty);
      allObs.push({
        x, y,
        value: correct ? 1.0 : 0.0,
        difficulty,
      });

      // Compare α with batch recomputation
      const batchEst = batchObserve(allObs);

      expect(incEst._alpha.length).toBe(batchEst._alpha.length);
      for (let j = 0; j < incEst._alpha.length; j++) {
        expect(Math.abs(incEst._alpha[j] - batchEst._alpha[j])).toBeLessThan(ALPHA_TOL);
      }
    }
  });

  it('incremental predict() matches batch predict() (full grid)', () => {
    const rand = mulberry32(99);
    const incEst = new Estimator();
    incEst.init(GRID_SIZE, REGION);

    const allObs = [];

    // Add 20 observations incrementally
    for (let i = 0; i < 20; i++) {
      const x = rand();
      const y = rand();
      const correct = rand() > 0.4;
      const difficulty = Math.floor(rand() * 4) + 1;

      incEst.observe(x, y, correct, undefined, difficulty);
      allObs.push({ x, y, value: correct ? 1.0 : 0.0, difficulty });
    }

    // Compare full grid predictions
    const batchEst = batchObserve(allObs);
    const incPred = incEst.predict();
    const batchPred = batchEst.predict();

    expect(incPred.length).toBe(batchPred.length);
    for (let i = 0; i < incPred.length; i++) {
      expect(Math.abs(incPred[i].value - batchPred[i].value)).toBeLessThan(PREDICT_TOL);
      expect(Math.abs(incPred[i].uncertainty - batchPred[i].uncertainty)).toBeLessThan(PREDICT_TOL);
    }
  });

  it('incremental matches batch with clustered observations (near-singular kernel)', () => {
    const rand = mulberry32(777);
    const incEst = new Estimator();
    incEst.init(GRID_SIZE, REGION);

    const allObs = [];

    // Clustered observations — stress test for numerical stability
    for (let i = 0; i < 25; i++) {
      const x = 0.48 + rand() * 0.04; // [0.48, 0.52]
      const y = 0.48 + rand() * 0.04;
      const correct = rand() > 0.5;
      const difficulty = Math.floor(rand() * 4) + 1;

      incEst.observe(x, y, correct, undefined, difficulty);
      allObs.push({ x, y, value: correct ? 1.0 : 0.0, difficulty });
    }

    const batchEst = batchObserve(allObs);

    // α comparison (may be slightly looser for clustered case)
    for (let j = 0; j < incEst._alpha.length; j++) {
      expect(Math.abs(incEst._alpha[j] - batchEst._alpha[j])).toBeLessThan(1e-8);
    }

    // Prediction comparison
    const incPred = incEst.predict();
    const batchPred = batchEst.predict();
    for (let i = 0; i < incPred.length; i++) {
      expect(Math.abs(incPred[i].value - batchPred[i].value)).toBeLessThan(1e-6);
      expect(Math.abs(incPred[i].uncertainty - batchPred[i].uncertainty)).toBeLessThan(1e-6);
    }
  });

  it('incremental matches batch with skip observations', () => {
    const rand = mulberry32(55);
    const incEst = new Estimator();
    incEst.init(GRID_SIZE, REGION);

    const allObs = [];

    for (let i = 0; i < 15; i++) {
      const x = rand();
      const y = rand();
      const difficulty = Math.floor(rand() * 4) + 1;

      if (rand() < 0.3) {
        // Skip
        incEst.observeSkip(x, y, undefined, difficulty);
        allObs.push({ x, y, value: 0.05, difficulty });
      } else {
        const correct = rand() > 0.4;
        incEst.observe(x, y, correct, undefined, difficulty);
        allObs.push({ x, y, value: correct ? 1.0 : 0.0, difficulty });
      }
    }

    const batchEst = batchObserve(allObs);

    for (let j = 0; j < incEst._alpha.length; j++) {
      expect(Math.abs(incEst._alpha[j] - batchEst._alpha[j])).toBeLessThan(ALPHA_TOL);
    }

    const incPred = incEst.predict();
    const batchPred = batchEst.predict();
    for (let i = 0; i < incPred.length; i++) {
      expect(Math.abs(incPred[i].value - batchPred[i].value)).toBeLessThan(PREDICT_TOL);
      expect(Math.abs(incPred[i].uncertainty - batchPred[i].uncertainty)).toBeLessThan(PREDICT_TOL);
    }
  });

  it('L is not recomputed from scratch on each observe() (incremental path taken)', () => {
    const est = new Estimator();
    est.init(GRID_SIZE, REGION);

    // First observation — must do full recompute (no existing L)
    est.observe(0.5, 0.5, true, undefined, 2);
    const L_after_1 = est._L;
    expect(L_after_1).not.toBeNull();
    expect(L_after_1.length).toBe(1);

    // Second observation — should extend L, not replace it
    // If incremental works, L[0] (first row) should be the exact same Float64Array object
    const firstRow = L_after_1[0];
    est.observe(0.3, 0.7, false, undefined, 3);
    expect(est._L.length).toBe(2);
    expect(est._L[0]).toBe(firstRow); // Same object reference — not rebuilt
  });

  it('handles 50 observations without divergence', { timeout: 30000 }, () => {
    const rand = mulberry32(2024);
    const incEst = new Estimator();
    incEst.init(GRID_SIZE, REGION);

    const allObs = [];

    for (let i = 0; i < 50; i++) {
      const x = rand();
      const y = rand();
      const correct = rand() > 0.35;
      const difficulty = Math.floor(rand() * 4) + 1;

      incEst.observe(x, y, correct, undefined, difficulty);
      allObs.push({ x, y, value: correct ? 1.0 : 0.0, difficulty });
    }

    const batchEst = batchObserve(allObs);

    // α comparison at n=50
    for (let j = 0; j < incEst._alpha.length; j++) {
      expect(Math.abs(incEst._alpha[j] - batchEst._alpha[j])).toBeLessThan(1e-7);
    }

    // Full prediction comparison
    const incPred = incEst.predict();
    const batchPred = batchEst.predict();
    let maxValDiff = 0;
    let maxUncDiff = 0;
    for (let i = 0; i < incPred.length; i++) {
      maxValDiff = Math.max(maxValDiff, Math.abs(incPred[i].value - batchPred[i].value));
      maxUncDiff = Math.max(maxUncDiff, Math.abs(incPred[i].uncertainty - batchPred[i].uncertainty));
    }

    expect(maxValDiff).toBeLessThan(1e-6);
    expect(maxUncDiff).toBeLessThan(1e-6);
  });
});
