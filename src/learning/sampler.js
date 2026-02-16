/** Active learning question selection via expected information gain. */

import { clamp } from '../utils/math.js';

export class Sampler {
  constructor() {
    this._gridSize = 0;
    this._region = null;
  }

  configure(gridSize, region) {
    this._gridSize = gridSize;
    this._region = region;
  }

  selectNext(questions, estimates, viewport, answeredIds) {
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
      const score = est ? est.uncertainty : 1.0;

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
      let bestScore = -Infinity;
      for (const q of pool) {
        const cell = this._questionToCell(q);
        const est = estimateMap.get(`${cell.gx},${cell.gy}`);
        const value = est ? est.value : 0.5;
        const score = value - (q.difficulty || 3) * 0.1;
        if (score > bestScore) {
          bestScore = score;
          selected = { questionId: q.id, score, cellGx: cell.gx, cellGy: cell.gy };
        }
      }
    } else if (mode === 'hardest-can-answer') {
      let bestDiff = -1;
      for (const q of pool) {
        const cell = this._questionToCell(q);
        const est = estimateMap.get(`${cell.gx},${cell.gy}`);
        const value = est ? est.value : 0.5;
        if (value > 0.6 && (q.difficulty || 3) > bestDiff) {
          bestDiff = q.difficulty || 3;
          selected = { questionId: q.id, score: bestDiff, cellGx: cell.gx, cellGy: cell.gy };
        }
      }
    } else if (mode === 'dont-know') {
      let bestDiff = -1;
      for (const q of pool) {
        const cell = this._questionToCell(q);
        const est = estimateMap.get(`${cell.gx},${cell.gy}`);
        const value = est ? est.value : 0.5;
        if (value < 0.3 && (q.difficulty || 3) > bestDiff) {
          bestDiff = q.difficulty || 3;
          selected = { questionId: q.id, score: bestDiff, cellGx: cell.gx, cellGy: cell.gy };
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
        score: est ? est.uncertainty : 1.0,
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
}
