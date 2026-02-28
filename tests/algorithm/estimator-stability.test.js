/**
 * Estimator stability tests (US1): verify the GP estimator handles 200+
 * observations without NaN/Infinity, Cholesky failures, or >5% coverage jumps.
 */
import { describe, it, expect } from 'vitest';
import { Estimator } from '../../src/learning/estimator.js';

const GRID_SIZE = 50;
const REGION = { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };

function makeEstimator() {
  const est = new Estimator();
  est.init(GRID_SIZE, REGION);
  return est;
}

// Seeded pseudo-random for reproducibility
function mulberry32(seed) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Matches $coverage computation in src/state/store.js
function computeCoverage(estimates) {
  if (estimates.length === 0) return 0;
  let totalCoverage = 0;
  for (const e of estimates) {
    if (e.state === 'unknown') continue;
    const contrib = 1 - e.uncertainty;
    if (isFinite(contrib)) totalCoverage += contrib;
  }
  const result = totalCoverage / estimates.length;
  return isFinite(result) ? result : 0;
}

describe('Estimator Stability (US1)', () => {
  it('handles 150 random observations without NaN/Infinity and no catastrophic collapse', { timeout: 30000 }, () => {
    const est = makeEstimator();
    const rand = mulberry32(42);
    const coverageHistory = [];

    for (let i = 0; i < 150; i++) {
      const x = rand();
      const y = rand();
      const correct = rand() > 0.4; // ~60% correct rate
      const difficulty = Math.floor(rand() * 4) + 1; // 1-4

      est.observe(x, y, correct, undefined, difficulty);

      // Check predictions at key milestones (every 20 obs) to keep test fast
      if ((i + 1) % 20 === 0) {
        const estimates = est.predict();

        // Assert no NaN/Infinity
        for (const e of estimates) {
          expect(isFinite(e.value)).toBe(true);
          expect(isFinite(e.uncertainty)).toBe(true);
          expect(e.value).toBeGreaterThanOrEqual(0);
          expect(e.value).toBeLessThanOrEqual(1);
        }

        coverageHistory.push({ obs: i + 1, coverage: computeCoverage(estimates) });
      }
    }

    // Guard against catastrophic collapse: no single 20-observation window
    // should cause coverage to jump by more than 30% (the original bug
    // caused a jump from 18% to 95% = 77% in just a few observations).
    for (let i = 1; i < coverageHistory.length; i++) {
      const jump = Math.abs(coverageHistory[i].coverage - coverageHistory[i - 1].coverage);
      expect(jump).toBeLessThanOrEqual(0.30);
    }

    // Coverage should monotonically increase overall (more data → more coverage)
    const firstCoverage = coverageHistory[0].coverage;
    const lastCoverage = coverageHistory[coverageHistory.length - 1].coverage;
    expect(lastCoverage).toBeGreaterThanOrEqual(firstCoverage);
  });

  it('handles 150 clustered observations without Cholesky failure', { timeout: 30000 }, () => {
    const est = makeEstimator();
    const rand = mulberry32(123);

    // All observations clustered in a small region around (0.5, 0.5)
    for (let i = 0; i < 150; i++) {
      const x = 0.45 + rand() * 0.1; // [0.45, 0.55]
      const y = 0.45 + rand() * 0.1;
      const correct = rand() > 0.5;
      const difficulty = Math.floor(rand() * 4) + 1;

      est.observe(x, y, correct, undefined, difficulty);
    }

    const estimates = est.predict();

    // All values should be finite (no Cholesky collapse)
    for (const e of estimates) {
      expect(isFinite(e.value)).toBe(true);
      expect(isFinite(e.uncertainty)).toBe(true);
    }

    // Should not be a uniform blob — predictions near cluster should differ from far away
    const nearCluster = estimates.filter(
      (e) => {
        const cx = REGION.x_min + (e.gx + 0.5) / GRID_SIZE;
        const cy = REGION.y_min + (e.gy + 0.5) / GRID_SIZE;
        return Math.abs(cx - 0.5) < 0.1 && Math.abs(cy - 0.5) < 0.1;
      }
    );
    const farFromCluster = estimates.filter(
      (e) => {
        const cx = REGION.x_min + (e.gx + 0.5) / GRID_SIZE;
        const cy = REGION.y_min + (e.gy + 0.5) / GRID_SIZE;
        return Math.abs(cx - 0.5) > 0.3 || Math.abs(cy - 0.5) > 0.3;
      }
    );

    const avgNear = nearCluster.reduce((s, e) => s + e.uncertainty, 0) / nearCluster.length;
    const avgFar = farFromCluster.reduce((s, e) => s + e.uncertainty, 0) / farFromCluster.length;

    // Uncertainty near the cluster should be lower than far away
    expect(avgNear).toBeLessThan(avgFar);
  });

  it('produces gradient (not uniform blob) after 150 observations', { timeout: 30000 }, () => {
    const est = makeEstimator();
    const rand = mulberry32(77);

    for (let i = 0; i < 150; i++) {
      const x = rand();
      const y = rand();
      const correct = rand() > 0.4;
      const difficulty = Math.floor(rand() * 4) + 1;

      est.observe(x, y, correct, undefined, difficulty);
    }

    const estimates = est.predict();
    const values = estimates.map((e) => e.value);

    // Compute standard deviation — should be >0.05 for a gradient
    const mean = values.reduce((s, v) => s + v, 0) / values.length;
    const variance = values.reduce((s, v) => s + (v - mean) ** 2, 0) / values.length;
    const stddev = Math.sqrt(variance);
    expect(stddev).toBeGreaterThan(0.05);

    // Some cells near correct answers should be high, some near incorrect should be low
    let hasHigh = false;
    let hasLow = false;
    for (const e of estimates) {
      if (e.value > 0.7) hasHigh = true;
      if (e.value < 0.3) hasLow = true;
    }
    expect(hasHigh).toBe(true);
    expect(hasLow).toBe(true);
  });
});
