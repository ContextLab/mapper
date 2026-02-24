/**
 * Video recommendation engine — TLP scoring, difference maps, expected gain, EMA.
 *
 * All operations use globalEstimator (50×50 on [0,1] space).
 * Two ranking phases:
 *   Phase 1 (TLP): (1-K) × U — active learning, prioritizes uncertainty
 *   Phase 3+ (ExpectedGain): (1-K) × Transfer — exploits observed learning
 *
 * See FR-V010 through FR-V024, CL-003, CL-011.
 */

import { matern32, euclidean } from '../utils/math.js';
import { DEFAULT_LENGTH_SCALE } from './estimator.js';
import {
  $watchedVideos,
  $preVideoSnapshot,
  $questionsAfterVideo,
  $differenceMap,
  $runningDifferenceMap,
} from '../state/store.js';

const GRID_SIZE = 50;
const EMA_ALPHA = 0.3;
const WATCHED_PENALTY = 0.1;
const TOP_N = 10;

// ─── Grid helpers ───────────────────────────────────────────

/**
 * Snap a [0,1] coordinate to the nearest grid cell index.
 * Cell centers are at (i + 0.5) / GRID_SIZE.
 */
function snapToCell(coord) {
  const idx = Math.floor(coord * GRID_SIZE);
  return Math.max(0, Math.min(GRID_SIZE - 1, idx));
}

/**
 * Convert (gx, gy) to a flat index into the 2,500-cell array.
 * Estimator returns cells ordered gy * GRID_SIZE + gx.
 */
function cellIndex(gx, gy) {
  return gy * GRID_SIZE + gx;
}

// ─── T-V030: TLP scoring ────────────────────────────────────

/**
 * Compute Theoretical Learning Potential for a single video.
 * TLP(v) = (1/N_v) × Σ_w [ (1 - K(x_w, y_w)) × U(x_w, y_w) ]
 *
 * @param {object} video - Video with `windows` array of [x, y] pairs
 * @param {Array} globalEstimates - CellEstimate[] from globalEstimator.predict()
 * @returns {number} TLP score in [0, 1]
 */
export function computeTLP(video, globalEstimates) {
  const windows = video.windows;
  if (!windows || windows.length === 0) return 0;

  let sum = 0;
  for (let i = 0; i < windows.length; i++) {
    const gx = snapToCell(windows[i][0]);
    const gy = snapToCell(windows[i][1]);
    const cell = globalEstimates[cellIndex(gx, gy)];
    const K = cell.value;
    const U = cell.uncertainty;
    sum += (1 - K) * U;
  }

  return sum / windows.length;
}

// ─── T-V031: Domain filtering ───────────────────────────────

/**
 * Filter videos to those belonging to the active domain.
 * For "All (General)" (domainId is null/undefined), return all videos.
 *
 * @param {Array} videos - All loaded videos for the domain
 * @param {string|null} domainId - Active domain ID, or null for all
 * @returns {Array} Filtered video list
 */
export function filterByDomain(videos, domainId) {
  if (!domainId) return videos;
  return videos;
}

// ─── T-V032: Watched penalty ────────────────────────────────

/**
 * Apply 0.1× penalty to already-watched videos.
 *
 * @param {Array<{video: object, score: number}>} scored - Scored video entries
 * @param {Set} watchedIds - Set of watched video IDs
 * @returns {Array<{video: object, score: number}>} Same array, mutated with penalties
 */
export function applyWatchedPenalty(scored, watchedIds) {
  for (let i = 0; i < scored.length; i++) {
    if (watchedIds.has(scored[i].video.id)) {
      scored[i].score *= WATCHED_PENALTY;
    }
  }
  return scored;
}

// ─── T-V033: Full ranking pipeline ──────────────────────────

/**
 * Compute full ranking: filter → score → penalize → sort → top 10.
 *
 * Uses ExpectedGain if a running difference map exists, otherwise TLP.
 *
 * @param {Array} videos - All loaded videos for the domain
 * @param {Array} globalEstimates - CellEstimate[] from globalEstimator.predict()
 * @param {Set} watchedIds - Set of watched video IDs
 * @param {Float32Array|null} runningDiffMap - Running EMA difference map (2,500 cells) or null
 * @param {string|null} domainId - Active domain ID
 * @returns {Array<{video: object, score: number}>} Top 10 ranked videos
 */
export function computeRanking(videos, globalEstimates, watchedIds, runningDiffMap, domainId) {
  const candidates = filterByDomain(videos, domainId);
  if (candidates.length === 0) return [];

  const useExpectedGain = runningDiffMap !== null;
  const scoreFn = useExpectedGain
    ? (v) => computeExpectedGain(v, globalEstimates, runningDiffMap, DEFAULT_LENGTH_SCALE)
    : (v) => computeTLP(v, globalEstimates);

  const scored = candidates.map((video) => ({
    video,
    score: scoreFn(video),
  }));

  applyWatchedPenalty(scored, watchedIds);

  scored.sort((a, b) => b.score - a.score);

  return scored.slice(0, TOP_N);
}

// ─── T-V034: Snapshot ───────────────────────────────────────

/**
 * Capture the current GP prediction grid as a pre-video snapshot.
 * Only captures if no pending snapshot already exists (CL-004).
 *
 * @param {Array} globalEstimates - CellEstimate[] from globalEstimator.predict()
 * @returns {boolean} True if snapshot was taken, false if one already existed
 */
export function takeSnapshot(globalEstimates) {
  if ($preVideoSnapshot.get() !== null) return false;

  const snapshot = new Float32Array(GRID_SIZE * GRID_SIZE);
  for (let i = 0; i < globalEstimates.length; i++) {
    snapshot[i] = globalEstimates[i].value;
  }
  $preVideoSnapshot.set(snapshot);
  $questionsAfterVideo.set(0);
  return true;
}

// ─── T-V035: Difference map ─────────────────────────────────

/**
 * Compute difference map: D(x,y) = K_after - K_before for all 2,500 cells.
 * Preserves negative values (CL-013).
 *
 * @param {Float32Array} snapshot - Pre-video K values (2,500 cells)
 * @param {Array} currentEstimates - CellEstimate[] from globalEstimator.predict()
 * @returns {Float32Array} Difference map (2,500 cells)
 */
export function computeDifferenceMap(snapshot, currentEstimates) {
  const diff = new Float32Array(GRID_SIZE * GRID_SIZE);
  for (let i = 0; i < currentEstimates.length; i++) {
    diff[i] = currentEstimates[i].value - snapshot[i];
  }
  $differenceMap.set(diff);
  return diff;
}

// ─── T-V036: Relevance map ──────────────────────────────────

/**
 * Compute relevance map: for each grid cell, max Matérn 3/2 kernel distance
 * to any video window coordinate.
 *
 * relevance(x, y) = max_w matern32(dist((x,y), (x_w, y_w)), lengthScale)
 *
 * @param {Array<Array<number>>} videoWindows - Merged [x, y] pairs from watched videos
 * @param {number} lengthScale - Matérn 3/2 length scale
 * @returns {Float32Array} Relevance map (2,500 cells)
 */
export function computeRelevanceMap(videoWindows, lengthScale) {
  const relevance = new Float32Array(GRID_SIZE * GRID_SIZE);
  const cellW = 1 / GRID_SIZE;

  for (let gy = 0; gy < GRID_SIZE; gy++) {
    for (let gx = 0; gx < GRID_SIZE; gx++) {
      const cx = (gx + 0.5) * cellW;
      const cy = (gy + 0.5) * cellW;
      let maxK = 0;
      for (let w = 0; w < videoWindows.length; w++) {
        const d = euclidean(cx, cy, videoWindows[w][0], videoWindows[w][1]);
        const k = matern32(d, lengthScale);
        if (k > maxK) maxK = k;
      }
      relevance[gy * GRID_SIZE + gx] = maxK;
    }
  }

  return relevance;
}

// ─── T-V037: Running average (EMA) ──────────────────────────

/**
 * Update the running EMA difference map.
 * D_running = α × (D_new × relevance) + (1 - α) × D_running_prev
 * For first video: D_running = D_new × relevance (α = 1.0).
 *
 * @param {Float32Array} newDiffMap - Latest difference map (2,500 cells)
 * @param {Float32Array} relevanceMap - Relevance weighting (2,500 cells)
 * @param {Float32Array|null} runningDiffMap - Previous running average, or null for first
 * @returns {Float32Array} Updated running difference map
 */
export function updateRunningAverage(newDiffMap, relevanceMap, runningDiffMap) {
  const size = GRID_SIZE * GRID_SIZE;
  const result = new Float32Array(size);

  if (runningDiffMap === null) {
    // First video: α = 1.0
    for (let i = 0; i < size; i++) {
      result[i] = newDiffMap[i] * relevanceMap[i];
    }
  } else {
    for (let i = 0; i < size; i++) {
      const weighted = newDiffMap[i] * relevanceMap[i];
      result[i] = EMA_ALPHA * weighted + (1 - EMA_ALPHA) * runningDiffMap[i];
    }
  }

  $runningDifferenceMap.set(result);
  return result;
}

// ─── T-V038: Expected gain ──────────────────────────────────

/**
 * Compute expected gain for a video using observed transfer rates.
 * ExpectedGain(v) = (1/N_v) × Σ_w [ (1 - K(x_w, y_w)) × Transfer(x_w, y_w) ]
 *
 * Transfer = max(0, D_running) — clamped so ExpectedGain is never negative.
 * For insufficient-coverage cells (no window within 2×lengthScale AND
 * |D_running| < 1e-4), uses global average of sufficient-coverage cells.
 *
 * @param {object} video - Video with `windows` array of [x, y] pairs
 * @param {Array} globalEstimates - CellEstimate[] from globalEstimator.predict()
 * @param {Float32Array} runningDiffMap - Running EMA difference map (2,500 cells)
 * @param {number} lengthScale - Matérn 3/2 length scale
 * @returns {number} Expected gain score
 */
export function computeExpectedGain(video, globalEstimates, runningDiffMap, lengthScale) {
  const windows = video.windows;
  if (!windows || windows.length === 0) return 0;

  // Precompute global average of sufficient-coverage cells.
  // "Sufficient coverage" = |D_running| >= 1e-4 at that cell.
  let sufficientSum = 0;
  let sufficientCount = 0;
  for (let i = 0; i < runningDiffMap.length; i++) {
    if (Math.abs(runningDiffMap[i]) >= 1e-4) {
      sufficientSum += Math.max(0, runningDiffMap[i]);
      sufficientCount++;
    }
  }
  const globalAvgTransfer = sufficientCount > 0 ? sufficientSum / sufficientCount : 0;

  let sum = 0;
  const twiceLS = 2 * lengthScale;

  for (let i = 0; i < windows.length; i++) {
    const gx = snapToCell(windows[i][0]);
    const gy = snapToCell(windows[i][1]);
    const idx = cellIndex(gx, gy);
    const K = globalEstimates[idx].value;

    const rawDiff = runningDiffMap[idx];
    let transfer;

    if (Math.abs(rawDiff) < 1e-4) {
      // Check if any video window is close enough to provide coverage
      const cx = (gx + 0.5) / GRID_SIZE;
      const cy = (gy + 0.5) / GRID_SIZE;
      let hasCoverage = false;
      for (let w = 0; w < windows.length; w++) {
        if (euclidean(cx, cy, windows[w][0], windows[w][1]) <= twiceLS) {
          hasCoverage = true;
          break;
        }
      }
      transfer = hasCoverage ? Math.max(0, rawDiff) : globalAvgTransfer;
    } else {
      transfer = Math.max(0, rawDiff);
    }

    sum += (1 - K) * transfer;
  }

  return sum / windows.length;
}

// ─── Flow orchestration helpers ─────────────────────────────

/**
 * Handle the post-video question flow (called from handleAnswer in app.js).
 * Increments counter, computes diff map after 1+ questions,
 * updates running average after 5+ questions.
 *
 * @param {Array} globalEstimates - Current CellEstimate[]
 * @param {Array<Array<number>>} mergedWindows - Merged window coords from recent videos
 * @returns {{ diffMap: Float32Array|null, runningMap: Float32Array|null, phaseComplete: boolean }}
 */
export function handlePostVideoQuestion(globalEstimates, mergedWindows) {
  const snapshot = $preVideoSnapshot.get();
  if (!snapshot) return { diffMap: null, runningMap: null, phaseComplete: false };

  const count = $questionsAfterVideo.get() + 1;
  $questionsAfterVideo.set(count);

  // Compute difference map after 1+ questions (FR-V021)
  const diffMap = computeDifferenceMap(snapshot, globalEstimates);

  // After 5+ questions, incorporate into running average
  if (count >= 5) {
    const relevanceMap = computeRelevanceMap(mergedWindows, DEFAULT_LENGTH_SCALE);
    const prevRunning = $runningDifferenceMap.get();
    const runningMap = updateRunningAverage(diffMap, relevanceMap, prevRunning);

    // Clear snapshot and counter — phase complete
    $preVideoSnapshot.set(null);
    $questionsAfterVideo.set(0);

    return { diffMap, runningMap, phaseComplete: true };
  }

  return { diffMap, runningMap: null, phaseComplete: false };
}
