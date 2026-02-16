/** 3D transition detection, point-set merging, and easing for smooth domain navigation. */

/**
 * Compute intersection-over-union of two axis-aligned regions.
 * @param {{ x_min: number, x_max: number, y_min: number, y_max: number }} a
 * @param {{ x_min: number, x_max: number, y_min: number, y_max: number }} b
 * @returns {number} IoU in [0, 1]
 */
export function computeIoU(a, b) {
  const xOverlap = Math.max(0, Math.min(a.x_max, b.x_max) - Math.max(a.x_min, b.x_min));
  const yOverlap = Math.max(0, Math.min(a.y_max, b.y_max) - Math.max(a.y_min, b.y_min));
  const intersection = xOverlap * yOverlap;
  const areaA = (a.x_max - a.x_min) * (a.y_max - a.y_min);
  const areaB = (b.x_max - b.x_min) * (b.y_max - b.y_min);
  const union = areaA + areaB - intersection;
  return union > 0 ? intersection / union : 0;
}

/**
 * Determine if crossfade is needed between two domain regions.
 * Regions with < 30% spatial overlap (IoU < 0.3) benefit from crossfade
 * rather than simple viewport pan, since intermediate frames would show
 * mostly empty space.
 *
 * @param {{ x_min: number, x_max: number, y_min: number, y_max: number }} sourceRegion
 * @param {{ x_min: number, x_max: number, y_min: number, y_max: number }} targetRegion
 * @returns {boolean}
 */
export function needs3D(sourceRegion, targetRegion) {
  if (!sourceRegion || !targetRegion) return false;
  return computeIoU(sourceRegion, targetRegion) < 0.3;
}

/**
 * Cubic ease-in-out.
 * @param {number} t - Progress in [0, 1]
 * @returns {number} Eased value in [0, 1]
 */
export function cubicInOut(t) {
  return t < 0.5
    ? 4 * t * t * t
    : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/**
 * Build a merged point set for animated transitions between two domains.
 *
 * Creates a single array containing all points from both source and target,
 * each tagged with a transition type and start/end opacity. During animation,
 * the renderer interpolates between startAlpha and endAlpha for each point.
 *
 * - 'stay':  present in both sets -> full opacity throughout
 * - 'enter': only in target -> fades from 0 to full
 * - 'leave': only in source -> fades from full to 0
 *
 * Points are matched by `id` (falling back to `title`). The returned array
 * has a stable ordering that is consistent between start and end states,
 * enabling deck.gl index-based attribute interpolation.
 *
 * @param {Array<object>} sourcePoints - Current visible points (PointData[])
 * @param {Array<object>} targetPoints - Destination points (PointData[])
 * @returns {{ merged: Array<object>, stats: { staying: number, entering: number, leaving: number } }}
 */
export function mergeForTransition(sourcePoints, targetPoints) {
  const sourceMap = new Map();
  for (const p of sourcePoints) {
    sourceMap.set(p.id || p.title, p);
  }

  const targetMap = new Map();
  for (const p of targetPoints) {
    targetMap.set(p.id || p.title, p);
  }

  const merged = [];
  let staying = 0;
  let entering = 0;
  let leaving = 0;

  // Shared points first (stable during transition)
  for (const [key, tp] of targetMap) {
    if (sourceMap.has(key)) {
      staying++;
      const sp = sourceMap.get(key);
      merged.push({
        ...tp,
        _transition: 'stay',
        _startAlpha: getAlpha(sp),
        _endAlpha: getAlpha(tp),
        _startX: sp.x,
        _startY: sp.y,
      });
    }
  }

  // Entering points (new in target, fade in)
  for (const [key, tp] of targetMap) {
    if (!sourceMap.has(key)) {
      entering++;
      merged.push({
        ...tp,
        _transition: 'enter',
        _startAlpha: 0,
        _endAlpha: getAlpha(tp),
        _startX: tp.x,
        _startY: tp.y,
      });
    }
  }

  // Leaving points (gone from target, fade out)
  for (const [key, sp] of sourceMap) {
    if (!targetMap.has(key)) {
      leaving++;
      merged.push({
        ...sp,
        _transition: 'leave',
        _startAlpha: getAlpha(sp),
        _endAlpha: 0,
        _startX: sp.x,
        _startY: sp.y,
      });
    }
  }

  return { merged, stats: { staying, entering, leaving } };
}

/**
 * Build two parallel arrays (same length, same indices) for deck.gl transition:
 * - startData: initial state (leaving visible, entering invisible)
 * - endData: final state (leaving invisible, entering visible)
 *
 * Setting startData then endData on the next frame triggers deck.gl
 * attribute interpolation.
 *
 * @param {Array<object>} merged - Output of mergeForTransition().merged
 * @returns {{ startData: Array<object>, endData: Array<object> }}
 */
export function buildTransitionFrames(merged) {
  const startData = [];
  const endData = [];

  for (const p of merged) {
    const baseColor = p.color || [200, 200, 200];
    const r = baseColor[0];
    const g = baseColor[1];
    const b = baseColor[2];

    startData.push({
      ...p,
      x: p._startX,
      y: p._startY,
      color: [r, g, b, p._startAlpha],
    });

    endData.push({
      ...p,
      // Entering/staying points use their target position;
      // leaving points keep their source position
      x: p._transition === 'leave' ? p._startX : p.x,
      y: p._transition === 'leave' ? p._startY : p.y,
      color: [r, g, b, p._endAlpha],
    });
  }

  return { startData, endData };
}

/**
 * Prepare 3D positions for a rotation-style transition.
 * Uses PCA-3 z-coordinates already present on point data.
 *
 * @param {Array<object>} points - Source PointData[] with z field
 * @param {Array<object>} targetPoints - Target PointData[] with z field
 * @returns {{ source: Array<object>, target: Array<object> }}
 */
export function prepare3DPositions(points, targetPoints) {
  const source = points.map((p) => ({
    ...p,
    z: p.z || 0,
  }));

  const target = targetPoints.map((p) => ({
    ...p,
    z: p.z || 0,
  }));

  return { source, target };
}

// ---- Helpers ----

function getAlpha(point) {
  if (point.color && point.color.length >= 4) return point.color[3];
  return 150; // default semi-transparent
}
