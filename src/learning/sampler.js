/** Active learning question selection via BALD expected information gain. */

import { clamp, sigmoid } from '../utils/math.js';

// IRT difficulty parameters in θ-space: b[d] for L1–L4 (FR-V051, CL-045).
// These correspond to IRT_THRESHOLDS [0.125, 0.375, 0.625, 0.875] in GP [0,1] space
// via the mapping θ = 4 × value - 2.
const IRT_B = [-1.5, -0.5, 0.5, 1.5];
const IRT_A = 1.5; // discrimination parameter
const IRT_A_SQ = IRT_A * IRT_A; // 2.25, precomputed

// Phase transition thresholds (FR-V052, CL-046).
const CALIBRATE_MAX = 10;
const MAP_MAX = 30;
const COVERAGE_FLOOR = 0.15;

/**
 * Determine selection phase from answered count and coverage.
 * - 'calibrate' (N < 10): prefer middle difficulties in uncertain regions
 * - 'map' (10 ≤ N < 30, or coverage < 15%): BALD EIG
 * - 'learn' (N ≥ 30, coverage ≥ 15%): ZPD targeting
 *
 * @param {number} answeredCount - Total questions answered
 * @param {number} coverage - Fraction of occupied cells with uncertainty < 0.5
 * @returns {'calibrate'|'map'|'learn'}
 */
export function getPhase(answeredCount, coverage) {
  if (answeredCount < CALIBRATE_MAX) return 'calibrate';
  if (answeredCount < MAP_MAX || coverage < COVERAGE_FLOOR) return 'map';
  return 'learn';
}

export class Sampler {
  constructor() {
    this._gridSize = 0;
    this._region = null;
  }

  configure(gridSize, region) {
    this._gridSize = gridSize;
    this._region = region;
  }

  selectNext(questions, estimates, viewport, answeredIds, phase) {
    const candidates = this._filterCandidates(questions, answeredIds);
    if (candidates.length === 0) return null;

    const estimateMap = this._buildEstimateMap(estimates);

    const inViewport = viewport
      ? candidates.filter((q) => this._inRegion(q, viewport))
      : candidates;

    const pool = inViewport.length > 0 ? inViewport : candidates;
    let best = null;
    let bestScore = -Infinity;

    for (const q of pool) {
      const cell = this._questionToCell(q);
      const key = `${cell.gx},${cell.gy}`;
      const est = estimateMap.get(key);
      const score = this._scoreByPhase(q, est, phase);

      if (score > bestScore) {
        bestScore = score;
        best = { questionId: q.id, score, cellGx: cell.gx, cellGy: cell.gy };
      }
    }

    return best;
  }

  selectByMode(mode, questions, estimates, viewport, answeredIds) {
    const candidates = this._filterCandidates(questions, answeredIds);
    if (candidates.length === 0) return null;

    const estimateMap = this._buildEstimateMap(estimates);
    const inViewport = viewport
      ? candidates.filter((q) => this._inRegion(q, viewport))
      : candidates;
    const pool = inViewport.length > 0 ? inViewport : candidates;

    let selected = null;

    if (mode === 'easy') {
      // Prefer questions where IRT P(correct) > 0.8
      let bestScore = -Infinity;
      for (const q of pool) {
        const cell = this._questionToCell(q);
        const est = estimateMap.get(`${cell.gx},${cell.gy}`);
        const P = this._irtPCorrect(q, est);
        // Score: higher P is better, with small uncertainty bonus for tie-breaking
        const score = P > 0.8 ? P + (est ? est.uncertainty * 0.01 : 0) : P * 0.1;
        if (score > bestScore) {
          bestScore = score;
          selected = { questionId: q.id, score, cellGx: cell.gx, cellGy: cell.gy };
        }
      }
    } else if (mode === 'hardest-can-answer') {
      // Prefer highest difficulty where IRT P(correct) > 0.5
      let bestScore = -Infinity;
      for (const q of pool) {
        const cell = this._questionToCell(q);
        const est = estimateMap.get(`${cell.gx},${cell.gy}`);
        const P = this._irtPCorrect(q, est);
        const difficulty = q.difficulty || 3;
        if (P > 0.5) {
          const score = difficulty + P * 0.1; // Prefer harder questions, break ties by P
          if (score > bestScore) {
            bestScore = score;
            selected = { questionId: q.id, score, cellGx: cell.gx, cellGy: cell.gy };
          }
        }
      }
    } else if (mode === 'dont-know') {
      // Prefer questions where IRT P(correct) < 0.3
      let bestScore = -Infinity;
      for (const q of pool) {
        const cell = this._questionToCell(q);
        const est = estimateMap.get(`${cell.gx},${cell.gy}`);
        const P = this._irtPCorrect(q, est);
        const difficulty = q.difficulty || 3;
        if (P < 0.3) {
          const score = difficulty + (1 - P) * 0.1; // Prefer harder + lower P
          if (score > bestScore) {
            bestScore = score;
            selected = { questionId: q.id, score, cellGx: cell.gx, cellGy: cell.gy };
          }
        }
      }
    }

    return selected || this.selectNext(questions, estimates, viewport, answeredIds);
  }

  scoreAll(questions, estimates, viewport, answeredIds) {
    const candidates = this._filterCandidates(questions, answeredIds);
    const estimateMap = this._buildEstimateMap(estimates);

    const scored = candidates.map((q) => {
      const cell = this._questionToCell(q);
      const key = `${cell.gx},${cell.gy}`;
      const est = estimateMap.get(key);
      return {
        questionId: q.id,
        score: this._baldEIG(q, est),
        cellGx: cell.gx,
        cellGy: cell.gy,
      };
    });

    scored.sort((a, b) => b.score - a.score);
    return scored;
  }

  _filterCandidates(questions, answeredIds) {
    if (!questions) return [];
    return questions.filter((q) => !answeredIds.has(q.id));
  }

  _buildEstimateMap(estimates) {
    const map = new Map();
    if (!estimates) return map;
    for (const e of estimates) {
      map.set(`${e.gx},${e.gy}`, e);
    }
    return map;
  }

  _questionToCell(q) {
    if (!this._region || !this._gridSize) {
      return { gx: 0, gy: 0 };
    }
    const r = this._region;
    const gs = this._gridSize;
    const gx = clamp(Math.floor(((q.x - r.x_min) / (r.x_max - r.x_min)) * gs), 0, gs - 1);
    const gy = clamp(Math.floor(((q.y - r.y_min) / (r.y_max - r.y_min)) * gs), 0, gs - 1);
    return { gx, gy };
  }

  _inRegion(q, region) {
    return q.x >= region.x_min && q.x <= region.x_max &&
           q.y >= region.y_min && q.y <= region.y_max;
  }

  /**
   * IRT-predicted probability of answering correctly.
   * P(correct) = sigmoid(a × (θ - b[d]))
   *
   * @param {{difficulty?: number}} q
   * @param {{value?: number}|undefined} est
   * @returns {number} P(correct) in (0, 1)
   */
  _irtPCorrect(q, est) {
    const value = est ? est.value : 0.5;
    const difficulty = q.difficulty || 3;
    const b = IRT_B[difficulty - 1] || 0;
    const theta = 4 * value - 2;
    return sigmoid(IRT_A * (theta - b));
  }

  /**
   * Phase-based scoring strategy.
   * - calibrate: uncertainty × difficulty-centering (prefer L2-L3 in uncertain regions)
   * - map: BALD EIG (information-theoretic)
   * - learn: ZPD targeting (P ≈ 0.55–0.70), with BALD fallback when local uncertainty > 0.7
   *
   * @param {{difficulty?: number}} q
   * @param {{value?: number, uncertainty?: number}|undefined} est
   * @param {'calibrate'|'map'|'learn'|undefined} phase
   * @returns {number}
   */
  _scoreByPhase(q, est, phase) {
    if (phase === 'calibrate') {
      const uncertainty = est ? est.uncertainty : 1.0;
      const difficulty = q.difficulty || 3;
      // Prefer middle difficulties (2-3) in uncertain regions
      const centerPenalty = 1 - Math.abs(difficulty - 2.5) / 2;
      return uncertainty * centerPenalty;
    }

    if (phase === 'learn') {
      const uncertainty = est ? est.uncertainty : 1.0;
      // Fall back to BALD if local uncertainty is high (unexplored region)
      if (uncertainty > 0.7) return this._baldEIG(q, est);

      const value = est ? est.value : 0.5;
      const difficulty = q.difficulty || 3;
      const b = IRT_B[difficulty - 1] || 0;
      const theta = 4 * value - 2;
      const P = sigmoid(IRT_A * (theta - b));
      // ZPD targeting: prefer questions where P(correct) ≈ 0.6
      return 1 - Math.abs(P - 0.6);
    }

    // Default ('map' phase or undefined): BALD EIG
    return this._baldEIG(q, est);
  }

  /**
   * BALD Expected Information Gain for a question given a cell estimate.
   * EIG = a² × P(1-P) × σ²_irt
   *
   * When all questions share the same difficulty, P(1-P) is monotonic in |θ-b|,
   * so ranking reduces to uncertainty-based selection (backward-compatible).
   *
   * @param {{difficulty?: number}} q - Question with optional difficulty (1-4)
   * @param {{value?: number, uncertainty?: number}|undefined} est - Cell estimate
   * @returns {number} BALD EIG score
   */
  _baldEIG(q, est) {
    const value = est ? est.value : 0.5;
    const uncertainty = est ? est.uncertainty : 1.0;
    const difficulty = q.difficulty || 3;
    const b = IRT_B[difficulty - 1] || 0;
    const theta = 4 * value - 2;
    const sigmaIrt = 4 * uncertainty;
    const P = sigmoid(IRT_A * (theta - b));
    return IRT_A_SQ * P * (1 - P) * sigmaIrt * sigmaIrt;
  }
}
