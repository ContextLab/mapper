/** Video recommender engine algorithm tests (Phase 7, T-V060–T-V063). */
import { describe, it, expect, beforeEach } from 'vitest';
import { Estimator, DEFAULT_LENGTH_SCALE } from '../../src/learning/estimator.js';
import {
  computeTLP,
  filterByDomain,
  applyWatchedPenalty,
  computeRanking,
  takeSnapshot,
  computeDifferenceMap,
  computeRelevanceMap,
  updateRunningAverage,
  computeExpectedGain,
} from '../../src/learning/video-recommender.js';
import {
  $preVideoSnapshot,
  $questionsAfterVideo,
  $differenceMap,
  $runningDifferenceMap,
} from '../../src/state/store.js';

const GRID_SIZE = 50;
const REGION = { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };

function makeEstimator() {
  const est = new Estimator();
  est.init(GRID_SIZE, REGION);
  return est;
}

/** Create a video with windows clustered around a center point. */
function makeVideo(id, centerX, centerY, numWindows = 5, spread = 0.05) {
  const windows = [];
  for (let i = 0; i < numWindows; i++) {
    const angle = (2 * Math.PI * i) / numWindows;
    const r = spread * (i / numWindows);
    windows.push([
      Math.max(0, Math.min(1, centerX + r * Math.cos(angle))),
      Math.max(0, Math.min(1, centerY + r * Math.sin(angle))),
    ]);
  }
  return { id, title: `Video ${id}`, duration_s: 300, windows };
}

/** Reset all video-related atoms between tests. */
function resetAtoms() {
  $preVideoSnapshot.set(null);
  $questionsAfterVideo.set(0);
  $differenceMap.set(null);
  $runningDifferenceMap.set(null);
}

// ─── T-V060: TLP ranking accuracy (SC-V003) ────────────────────

describe('TLP ranking accuracy (SC-V003)', () => {
  beforeEach(resetAtoms);

  it('top-ranked video targets the weakest knowledge region', () => {
    const est = makeEstimator();

    // Create a GP with strong knowledge in bottom-left, weak in top-right.
    // Observe many correct answers near (0.2, 0.2) to build high K there.
    for (let i = 0; i < 5; i++) {
      est.observe(0.15 + i * 0.02, 0.15 + i * 0.02, true, undefined, 3);
    }

    const estimates = est.predict();

    // Three videos at different locations:
    // - v_strong: windows near the well-known region → low TLP
    // - v_middle: windows in moderate region → medium TLP
    // - v_weak: windows in the unknown region → high TLP
    const vStrong = makeVideo('v_strong', 0.2, 0.2, 5, 0.03);
    const vMiddle = makeVideo('v_middle', 0.5, 0.5, 5, 0.03);
    const vWeak = makeVideo('v_weak', 0.85, 0.85, 5, 0.03);

    const tlpStrong = computeTLP(vStrong, estimates);
    const tlpMiddle = computeTLP(vMiddle, estimates);
    const tlpWeak = computeTLP(vWeak, estimates);

    // Weak region should have highest TLP (most learning potential)
    expect(tlpWeak).toBeGreaterThan(tlpMiddle);
    expect(tlpMiddle).toBeGreaterThan(tlpStrong);
  });

  it('top-ranked video targets weakest region ≥80% across randomized trials', () => {
    let weakWins = 0;
    const trials = 100;

    for (let trial = 0; trial < trials; trial++) {
      const est = makeEstimator();
      const rng = mulberry32(trial); // Deterministic RNG per trial

      // Random cluster of correct answers in one quadrant
      const knownX = 0.15 + rng() * 0.2;
      const knownY = 0.15 + rng() * 0.2;
      for (let i = 0; i < 4; i++) {
        est.observe(
          knownX + (rng() - 0.5) * 0.1,
          knownY + (rng() - 0.5) * 0.1,
          true, undefined, 3
        );
      }

      const estimates = est.predict();

      // Video in the known region vs video in the opposite corner
      const vKnown = makeVideo('known', knownX, knownY, 5, 0.03);
      const vUnknown = makeVideo('unknown', 0.85, 0.85, 5, 0.03);

      const tlpKnown = computeTLP(vKnown, estimates);
      const tlpUnknown = computeTLP(vUnknown, estimates);

      if (tlpUnknown > tlpKnown) weakWins++;
    }

    expect(weakWins).toBeGreaterThanOrEqual(80);
  });

  it('TLP is zero for video with no windows', () => {
    const est = makeEstimator();
    const estimates = est.predict();
    const emptyVideo = { id: 'empty', windows: [] };
    expect(computeTLP(emptyVideo, estimates)).toBe(0);
  });

  it('TLP is bounded in [0, 1]', () => {
    const est = makeEstimator();
    // Extreme scenario: all wrong answers
    for (let i = 0; i < 5; i++) {
      est.observe(0.5 + i * 0.01, 0.5, false, undefined, 4);
    }
    const estimates = est.predict();
    const video = makeVideo('v1', 0.5, 0.5, 10, 0.1);
    const tlp = computeTLP(video, estimates);
    expect(tlp).toBeGreaterThanOrEqual(0);
    expect(tlp).toBeLessThanOrEqual(1);
  });

  it('watched penalty reduces score by 10x', () => {
    const scored = [
      { video: { id: 'v1' }, score: 0.8 },
      { video: { id: 'v2' }, score: 0.6 },
    ];
    const watchedIds = new Set(['v1']);
    applyWatchedPenalty(scored, watchedIds);

    expect(scored[0].score).toBeCloseTo(0.08, 5);
    expect(scored[1].score).toBeCloseTo(0.6, 5);
  });

  it('filterByDomain returns all videos when domainId is null', () => {
    const videos = [makeVideo('a', 0.1, 0.1), makeVideo('b', 0.9, 0.9)];
    expect(filterByDomain(videos, null)).toHaveLength(2);
  });

  it('computeRanking returns at most 10 videos', () => {
    const est = makeEstimator();
    const estimates = est.predict();

    // Create 20 videos
    const videos = [];
    for (let i = 0; i < 20; i++) {
      videos.push(makeVideo(`v${i}`, Math.random(), Math.random(), 3, 0.02));
    }

    const ranking = computeRanking(videos, estimates, new Set(), null, null);
    expect(ranking.length).toBeLessThanOrEqual(10);
    // Should be sorted descending
    for (let i = 1; i < ranking.length; i++) {
      expect(ranking[i].score).toBeLessThanOrEqual(ranking[i - 1].score);
    }
  });
});

// ─── T-V061: Difference map correctness (SC-V004) ──────────────

describe('Difference map correctness (SC-V004)', () => {
  beforeEach(resetAtoms);

  it('difference map has non-zero values near video windows after learning', () => {
    const est = makeEstimator();

    // Take a snapshot of the prior state
    const priorEstimates = est.predict();
    const snapshot = new Float32Array(GRID_SIZE * GRID_SIZE);
    for (let i = 0; i < priorEstimates.length; i++) {
      snapshot[i] = priorEstimates[i].value;
    }

    // Simulate answering 5 questions near the video's windows (around 0.4, 0.4)
    const videoCenter = [0.4, 0.4];
    for (let i = 0; i < 5; i++) {
      est.observe(
        videoCenter[0] + (i - 2) * 0.02,
        videoCenter[1] + (i - 2) * 0.02,
        true, undefined, 3
      );
    }

    const afterEstimates = est.predict();
    const diffMap = computeDifferenceMap(snapshot, afterEstimates);

    // Count non-zero cells near the video window area
    let nonZeroNearWindow = 0;
    const cellW = 1 / GRID_SIZE;
    for (let gy = 0; gy < GRID_SIZE; gy++) {
      for (let gx = 0; gx < GRID_SIZE; gx++) {
        const cx = (gx + 0.5) * cellW;
        const cy = (gy + 0.5) * cellW;
        const dist = Math.sqrt(
          (cx - videoCenter[0]) ** 2 + (cy - videoCenter[1]) ** 2
        );
        // "Near" = within 2x the default length scale
        if (dist <= DEFAULT_LENGTH_SCALE * 2) {
          if (Math.abs(diffMap[gy * GRID_SIZE + gx]) > 1e-6) {
            nonZeroNearWindow++;
          }
        }
      }
    }

    // SC-V004: ≥10% of grid cells near window coords have non-zero values
    const totalCells = GRID_SIZE * GRID_SIZE;
    expect(nonZeroNearWindow / totalCells).toBeGreaterThanOrEqual(0.1);
  });

  it('difference map preserves negative values (CL-013)', () => {
    const est = makeEstimator();

    // Create a snapshot where we already have some correct answers
    est.observe(0.5, 0.5, true, undefined, 3);
    est.observe(0.5, 0.5, true, undefined, 3);

    const priorEstimates = est.predict();
    const snapshot = new Float32Array(GRID_SIZE * GRID_SIZE);
    for (let i = 0; i < priorEstimates.length; i++) {
      snapshot[i] = priorEstimates[i].value;
    }

    // Now answer incorrectly — knowledge should decrease
    est.observe(0.5, 0.5, false, undefined, 3);
    est.observe(0.5, 0.5, false, undefined, 3);
    est.observe(0.5, 0.5, false, undefined, 3);

    const afterEstimates = est.predict();
    const diffMap = computeDifferenceMap(snapshot, afterEstimates);

    // Some cells near (0.5, 0.5) should have negative differences
    let hasNegative = false;
    for (let i = 0; i < diffMap.length; i++) {
      if (diffMap[i] < -1e-6) {
        hasNegative = true;
        break;
      }
    }
    expect(hasNegative).toBe(true);
  });

  it('takeSnapshot captures current GP values and blocks second snapshot', () => {
    const est = makeEstimator();
    est.observe(0.3, 0.3, true, undefined, 2);
    const estimates = est.predict();

    const taken1 = takeSnapshot(estimates);
    expect(taken1).toBe(true);
    expect($preVideoSnapshot.get()).not.toBeNull();
    expect($questionsAfterVideo.get()).toBe(0);

    // Second snapshot should be blocked (CL-004)
    const taken2 = takeSnapshot(estimates);
    expect(taken2).toBe(false);
  });

  it('relevance map peaks near video windows', () => {
    const windows = [[0.3, 0.3], [0.35, 0.35]];
    const relevance = computeRelevanceMap(windows, DEFAULT_LENGTH_SCALE);

    // Cell near (0.3, 0.3) should have high relevance
    const nearGx = Math.floor(0.3 * GRID_SIZE);
    const nearGy = Math.floor(0.3 * GRID_SIZE);
    const nearIdx = nearGy * GRID_SIZE + nearGx;

    // Cell far from windows should have low relevance
    const farGx = Math.floor(0.9 * GRID_SIZE);
    const farGy = Math.floor(0.9 * GRID_SIZE);
    const farIdx = farGy * GRID_SIZE + farGx;

    expect(relevance[nearIdx]).toBeGreaterThan(relevance[farIdx]);
    expect(relevance[nearIdx]).toBeGreaterThan(0.5);
  });

  it('EMA running average: first video uses alpha=1.0', () => {
    const size = GRID_SIZE * GRID_SIZE;
    const diffMap = new Float32Array(size);
    const relevance = new Float32Array(size);

    // Set known values at index 0
    diffMap[0] = 0.5;
    relevance[0] = 0.8;

    const result = updateRunningAverage(diffMap, relevance, null);

    // First video: result = diffMap * relevance (alpha = 1.0)
    expect(result[0]).toBeCloseTo(0.5 * 0.8, 5);
  });

  it('EMA running average: subsequent videos blend with alpha=0.3', () => {
    const size = GRID_SIZE * GRID_SIZE;
    const diffMap = new Float32Array(size);
    const relevance = new Float32Array(size);
    const prevRunning = new Float32Array(size);

    diffMap[0] = 1.0;
    relevance[0] = 1.0;
    prevRunning[0] = 0.5;

    const result = updateRunningAverage(diffMap, relevance, prevRunning);

    // result = 0.3 * (1.0 * 1.0) + 0.7 * 0.5 = 0.3 + 0.35 = 0.65
    expect(result[0]).toBeCloseTo(0.65, 5);
  });
});

// ─── T-V062: ExpectedGain vs TLP divergence (SC-V005) ──────────

describe('ExpectedGain vs TLP divergence (SC-V005)', () => {
  beforeEach(resetAtoms);

  it('ExpectedGain produces different ranking than TLP after diff map', () => {
    const est = makeEstimator();

    // Build initial GP state: observed some knowledge around (0.3, 0.3)
    for (let i = 0; i < 5; i++) {
      est.observe(0.25 + i * 0.02, 0.25 + i * 0.02, true, undefined, 3);
    }

    const estimatesBefore = est.predict();

    // Create a running diff map that shows strong learning near (0.3, 0.3)
    // and no learning near (0.8, 0.8)
    const size = GRID_SIZE * GRID_SIZE;
    const runningDiffMap = new Float32Array(size);
    const cellW = 1 / GRID_SIZE;
    for (let gy = 0; gy < GRID_SIZE; gy++) {
      for (let gx = 0; gx < GRID_SIZE; gx++) {
        const cx = (gx + 0.5) * cellW;
        const cy = (gy + 0.5) * cellW;
        const dist = Math.sqrt((cx - 0.3) ** 2 + (cy - 0.3) ** 2);
        // Strong positive transfer near (0.3, 0.3), none elsewhere
        runningDiffMap[gy * GRID_SIZE + gx] = Math.max(0, 0.3 - dist);
      }
    }

    // Create two videos:
    // vA: near the high-transfer region (0.3, 0.3) — ExpectedGain should boost this
    // vB: in the unknown region (0.8, 0.8) — TLP should prefer this (more uncertainty)
    const vA = makeVideo('vA', 0.35, 0.35, 8, 0.04);
    const vB = makeVideo('vB', 0.8, 0.8, 8, 0.04);
    const videos = [vA, vB];

    // TLP ranking (no diff map)
    const tlpRanking = computeRanking(videos, estimatesBefore, new Set(), null, null);

    // ExpectedGain ranking (with diff map)
    const egRanking = computeRanking(videos, estimatesBefore, new Set(), runningDiffMap, null);

    // TLP should prefer vB (unknown region, high uncertainty)
    expect(tlpRanking[0].video.id).toBe('vB');

    // ExpectedGain should prefer vA (high transfer from diff map)
    expect(egRanking[0].video.id).toBe('vA');

    // The two rankings should differ
    expect(tlpRanking[0].video.id).not.toBe(egRanking[0].video.id);
  });

  it('ExpectedGain with positive diff map produces positive gain', () => {
    const est = makeEstimator();
    const estimates = est.predict(); // All prior mean = 0.5

    // Create a diff map with uniform positive signal
    const size = GRID_SIZE * GRID_SIZE;
    const runningDiffMap = new Float32Array(size);
    for (let i = 0; i < size; i++) {
      runningDiffMap[i] = 0.2; // Consistent positive transfer everywhere
    }

    const video = makeVideo('v1', 0.5, 0.5, 5, 0.03);
    const gain = computeExpectedGain(video, estimates, runningDiffMap, DEFAULT_LENGTH_SCALE);

    // (1 - 0.5) × 0.2 = 0.1 expected per window
    expect(gain).toBeGreaterThan(0);
    expect(gain).toBeCloseTo(0.1, 1);
  });

  it('ExpectedGain global average fallback for sparse windows', () => {
    const est = makeEstimator();
    // Observe near (0.2, 0.2) to lower K there, raise K near (0.8, 0.8)
    for (let i = 0; i < 3; i++) {
      est.observe(0.2 + i * 0.01, 0.2, true, undefined, 3);
    }
    const estimates = est.predict();

    // Diff map with strong signal only near (0.2, 0.2), zero elsewhere
    const size = GRID_SIZE * GRID_SIZE;
    const runningDiffMap = new Float32Array(size);
    const cellW = 1 / GRID_SIZE;
    for (let gy = 0; gy < GRID_SIZE; gy++) {
      for (let gx = 0; gx < GRID_SIZE; gx++) {
        const cx = (gx + 0.5) * cellW;
        const cy = (gy + 0.5) * cellW;
        const dist = Math.sqrt((cx - 0.2) ** 2 + (cy - 0.2) ** 2);
        if (dist < 0.1) {
          runningDiffMap[gy * GRID_SIZE + gx] = 0.3;
        }
      }
    }

    // Video near the high-transfer region benefits from actual diff values
    const nearVideo = makeVideo('near', 0.2, 0.2, 5, 0.03);
    const gainNear = computeExpectedGain(nearVideo, estimates, runningDiffMap, DEFAULT_LENGTH_SCALE);

    // Video far from transfer region — windows land on zero-diff cells.
    // Its windows self-cover (hasCoverage=true), so transfer = max(0, 0) = 0
    const farVideo = makeVideo('far', 0.8, 0.8, 5, 0.02);
    const gainFar = computeExpectedGain(farVideo, estimates, runningDiffMap, DEFAULT_LENGTH_SCALE);

    // Near video should have meaningfully higher gain than far video
    expect(gainNear).toBeGreaterThan(gainFar);
    expect(gainNear).toBeGreaterThan(0);
  });

  it('ExpectedGain is zero for empty video', () => {
    const est = makeEstimator();
    const estimates = est.predict();
    const diffMap = new Float32Array(GRID_SIZE * GRID_SIZE);
    const emptyVideo = { id: 'empty', windows: [] };
    expect(computeExpectedGain(emptyVideo, estimates, diffMap, DEFAULT_LENGTH_SCALE)).toBe(0);
  });

  it('ExpectedGain clamps negative transfer to zero', () => {
    const est = makeEstimator();
    const estimates = est.predict();

    // All cells have negative diff (knowledge decreased)
    const size = GRID_SIZE * GRID_SIZE;
    const runningDiffMap = new Float32Array(size);
    for (let i = 0; i < size; i++) {
      runningDiffMap[i] = -0.5;
    }

    const video = makeVideo('v1', 0.5, 0.5, 5, 0.03);
    const gain = computeExpectedGain(video, estimates, runningDiffMap, DEFAULT_LENGTH_SCALE);

    // Transfer = max(0, D_running) → should clamp all negatives to 0
    expect(gain).toBe(0);
  });
});

// ─── T-V063: Performance (SC-V006) ─────────────────────────────

describe('Scoring performance (SC-V006)', () => {
  beforeEach(resetAtoms);

  it('computeTLP for 500 videos completes in <15ms', () => {
    const est = makeEstimator();
    for (let i = 0; i < 10; i++) {
      est.observe(Math.random(), Math.random(), Math.random() > 0.4, undefined, 3);
    }
    const estimates = est.predict();

    // Generate 500 videos with ~20 windows each (realistic count)
    const videos = [];
    for (let i = 0; i < 500; i++) {
      videos.push(makeVideo(`v${i}`, Math.random(), Math.random(), 20, 0.08));
    }

    // Warmup
    computeTLP(videos[0], estimates);

    const start = performance.now();
    for (const video of videos) {
      computeTLP(video, estimates);
    }
    const elapsed = performance.now() - start;

    expect(elapsed).toBeLessThan(15);
  });

  it('computeRanking for 500 videos completes in <15ms', () => {
    const est = makeEstimator();
    for (let i = 0; i < 10; i++) {
      est.observe(Math.random(), Math.random(), Math.random() > 0.4, undefined, 3);
    }
    const estimates = est.predict();

    const videos = [];
    for (let i = 0; i < 500; i++) {
      videos.push(makeVideo(`v${i}`, Math.random(), Math.random(), 20, 0.08));
    }

    // Warmup
    computeRanking(videos.slice(0, 10), estimates, new Set(), null, null);

    const start = performance.now();
    computeRanking(videos, estimates, new Set(), null, null);
    const elapsed = performance.now() - start;

    expect(elapsed).toBeLessThan(15);
  });

  it('computeExpectedGain for 500 videos completes in <15ms', () => {
    const est = makeEstimator();
    for (let i = 0; i < 10; i++) {
      est.observe(Math.random(), Math.random(), Math.random() > 0.4, undefined, 3);
    }
    const estimates = est.predict();

    const videos = [];
    for (let i = 0; i < 500; i++) {
      videos.push(makeVideo(`v${i}`, Math.random(), Math.random(), 20, 0.08));
    }

    // Create a realistic diff map
    const size = GRID_SIZE * GRID_SIZE;
    const runningDiffMap = new Float32Array(size);
    for (let i = 0; i < size; i++) {
      runningDiffMap[i] = Math.random() * 0.2 - 0.05;
    }

    // Warmup
    computeExpectedGain(videos[0], estimates, runningDiffMap, DEFAULT_LENGTH_SCALE);

    const start = performance.now();
    for (const video of videos) {
      computeExpectedGain(video, estimates, runningDiffMap, DEFAULT_LENGTH_SCALE);
    }
    const elapsed = performance.now() - start;

    expect(elapsed).toBeLessThan(15);
  });

  it('computeDifferenceMap for 2500 cells completes in <1ms', () => {
    const size = GRID_SIZE * GRID_SIZE;
    const snapshot = new Float32Array(size);
    const estimates = [];
    for (let i = 0; i < size; i++) {
      snapshot[i] = Math.random();
      estimates.push({ value: Math.random() });
    }

    // Warmup
    computeDifferenceMap(snapshot, estimates);
    resetAtoms();

    const start = performance.now();
    computeDifferenceMap(snapshot, estimates);
    const elapsed = performance.now() - start;

    expect(elapsed).toBeLessThan(1);
  });
});

// ─── Deterministic RNG for reproducible tests ──────────────────

/** Mulberry32: simple deterministic PRNG (returns values in [0, 1)). */
function mulberry32(seed) {
  let s = seed | 0;
  return function () {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
