/** Mathematical utilities for RBF kernels, distance metrics, and interpolation. */

const SQRT3 = 1.7320508075688772;

/**
 * Matérn 3/2 kernel function.
 * k(d) = σ² (1 + √3·d/l) exp(-√3·d/l)
 *
 * @param {number} d - Distance between two points (>= 0)
 * @param {number} lengthScale - Length-scale parameter (> 0)
 * @param {number} [variance=1] - Signal variance σ²
 * @returns {number} Kernel value in [0, variance]
 */
export function matern32(d, lengthScale, variance = 1) {
  const r = (SQRT3 * d) / lengthScale;
  return variance * (1 + r) * Math.exp(-r);
}

/**
 * Squared exponential (RBF/Gaussian) kernel.
 * k(d) = σ² exp(-d² / (2l²))
 *
 * @param {number} d - Distance between two points
 * @param {number} lengthScale - Length-scale parameter
 * @param {number} [variance=1] - Signal variance σ²
 * @returns {number}
 */
export function rbfKernel(d, lengthScale, variance = 1) {
  const r = d / lengthScale;
  return variance * Math.exp(-0.5 * r * r);
}

/**
 * Euclidean distance between two 2D points.
 * @param {number} x1
 * @param {number} y1
 * @param {number} x2
 * @param {number} y2
 * @returns {number}
 */
export function euclidean(x1, y1, x2, y2) {
  const dx = x1 - x2;
  const dy = y1 - y2;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Numerically stable sigmoid: 1 / (1 + exp(-x)).
 * @param {number} x
 * @returns {number} Value in (0, 1)
 */
export function sigmoid(x) {
  if (x >= 0) {
    return 1 / (1 + Math.exp(-x));
  }
  const ex = Math.exp(x);
  return ex / (1 + ex);
}

/**
 * Linear interpolation between a and b.
 * @param {number} a - Start value
 * @param {number} b - End value
 * @param {number} t - Interpolation factor [0, 1]
 * @returns {number}
 */
export function lerp(a, b, t) {
  return a + (b - a) * t;
}

/**
 * Clamp value to [min, max].
 * @param {number} x
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
export function clamp(x, min, max) {
  return Math.max(min, Math.min(max, x));
}

/**
 * Standard normal CDF via Abramowitz & Stegun formula 26.2.17.
 * Maximum absolute error < 7.5e-8.
 *
 * @param {number} x
 * @returns {number} Φ(x) in [0, 1]
 */
export function normalCDF(x) {
  const p = 0.2316419;
  const b1 = 0.319381530;
  const b2 = -0.356563782;
  const b3 = 1.781477937;
  const b4 = -1.821255978;
  const b5 = 1.330274429;

  const absX = Math.abs(x);
  const t = 1 / (1 + p * absX);
  const pdf = Math.exp(-0.5 * absX * absX) / 2.5066282746310002; // √(2π)
  const poly = t * (b1 + t * (b2 + t * (b3 + t * (b4 + t * b5))));
  const cdf = 1 - pdf * poly;

  return x < 0 ? 1 - cdf : cdf;
}

// ============================================================
// Matrix utilities for Gaussian Process
// ============================================================

/**
 * Dot product of two vectors.
 * @param {Float64Array} a
 * @param {Float64Array} b
 * @returns {number}
 */
export function dot(a, b) {
  let sum = 0;
  for (let i = 0; i < a.length; i++) {
    sum += a[i] * b[i];
  }
  return sum;
}

/**
 * Matrix-vector multiplication: A·v.
 * @param {Float64Array[]} A - MxN matrix (array of rows)
 * @param {Float64Array} v - Length-N vector
 * @returns {Float64Array} Length-M result
 */
export function matvec(A, v) {
  const m = A.length;
  const result = new Float64Array(m);
  for (let i = 0; i < m; i++) {
    let sum = 0;
    const row = A[i];
    for (let j = 0; j < row.length; j++) {
      sum += row[j] * v[j];
    }
    result[i] = sum;
  }
  return result;
}

/**
 * Build NxN kernel (Gram) matrix from observation points.
 *
 * @param {Array<{x: number, y: number}>} points
 * @param {function} kernelFn - (distance) => value
 * @returns {Float64Array[]} NxN symmetric matrix
 */
export function kernelMatrix(points, kernelFn) {
  const n = points.length;
  const K = new Array(n);
  for (let i = 0; i < n; i++) {
    K[i] = new Float64Array(n);
  }
  for (let i = 0; i < n; i++) {
    for (let j = i; j < n; j++) {
      const d = euclidean(points[i].x, points[i].y, points[j].x, points[j].y);
      const val = kernelFn(d);
      K[i][j] = val;
      K[j][i] = val;
    }
  }
  return K;
}

/**
 * Build kernel vector between a test point and observation points.
 *
 * @param {{x: number, y: number}} testPoint
 * @param {Array<{x: number, y: number}>} obsPoints
 * @param {function} kernelFn - (distance) => value
 * @returns {Float64Array}
 */
export function kernelVector(testPoint, obsPoints, kernelFn) {
  const n = obsPoints.length;
  const kVec = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const d = euclidean(testPoint.x, testPoint.y, obsPoints[i].x, obsPoints[i].y);
    kVec[i] = kernelFn(d);
  }
  return kVec;
}

/**
 * Solve symmetric positive-definite linear system K·x = b
 * via Cholesky decomposition.
 *
 * @param {Float64Array[]} K - NxN SPD matrix
 * @param {Float64Array} b - Length-N right-hand side
 * @returns {Float64Array} Solution vector x
 */
export function choleskySolve(K, b) {
  const n = K.length;
  const MAX_RETRIES = 3;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    // Adaptive jitter: scales with matrix size to maintain stability for large N
    const jitter = 1e-6 * Math.max(1, n / 10) * Math.pow(10, attempt);

    // Cholesky: K = L·L^T
    const L = new Array(n);
    for (let i = 0; i < n; i++) {
      L[i] = new Float64Array(n);
    }

    let negativeDiag = false;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j <= i; j++) {
        let sum = 0;
        for (let k = 0; k < j; k++) {
          sum += L[i][k] * L[j][k];
        }
        if (i === j) {
          const diag = K[i][i] - sum + jitter;
          if (diag <= 0) {
            negativeDiag = true;
            break;
          }
          L[i][j] = Math.sqrt(diag);
        } else {
          L[i][j] = (K[i][j] - sum) / L[j][j];
        }
      }
      if (negativeDiag) break;
    }

    // Retry with larger jitter on negative diagonal
    if (negativeDiag) {
      if (attempt < MAX_RETRIES) {
        console.warn(`[choleskySolve] Negative diagonal at attempt ${attempt + 1}, retrying with 10× jitter`);
        continue;
      }
      console.warn('[choleskySolve] All retries exhausted — returning zero vector (prior mean fallback)');
      return new Float64Array(n);
    }

    // Forward substitution: L·y = b
    const y = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      let sum = 0;
      for (let k = 0; k < i; k++) {
        sum += L[i][k] * y[k];
      }
      y[i] = (b[i] - sum) / L[i][i];
    }

    // Back substitution: L^T·x = y
    const x = new Float64Array(n);
    for (let i = n - 1; i >= 0; i--) {
      let sum = 0;
      for (let k = i + 1; k < n; k++) {
        sum += L[k][i] * x[k];
      }
      x[i] = (y[i] - sum) / L[i][i];
    }

    // NaN safety: if decomposition produced NaN, return zero vector
    for (let i = 0; i < n; i++) {
      if (!isFinite(x[i])) {
        console.warn('[choleskySolve] NaN in solution — returning zero vector (prior mean fallback)');
        return new Float64Array(n);
      }
    }

    return x;
  }

  return new Float64Array(n);
}

/**
 * Cholesky decomposition: returns lower triangular L where K = L·L^T.
 * Used when we need L itself (not just a solve).
 *
 * @param {Float64Array[]} K - NxN SPD matrix
 * @returns {Float64Array[]} Lower triangular matrix L
 */
export function cholesky(K) {
  const n = K.length;
  const MAX_RETRIES = 3;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const jitter = 1e-6 * Math.max(1, n / 10) * Math.pow(10, attempt);
    const L = new Array(n);
    for (let i = 0; i < n; i++) {
      L[i] = new Float64Array(n);
    }

    let negativeDiag = false;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j <= i; j++) {
        let sum = 0;
        for (let k = 0; k < j; k++) {
          sum += L[i][k] * L[j][k];
        }
        if (i === j) {
          const diag = K[i][i] - sum + jitter;
          if (diag <= 0) {
            negativeDiag = true;
            break;
          }
          L[i][j] = Math.sqrt(diag);
        } else {
          L[i][j] = (K[i][j] - sum) / L[j][j];
        }
      }
      if (negativeDiag) break;
    }

    if (negativeDiag) {
      if (attempt < MAX_RETRIES) {
        console.warn(`[cholesky] Negative diagonal at attempt ${attempt + 1}, retrying with 10× jitter`);
        continue;
      }
      console.warn('[cholesky] All retries exhausted — returning identity-like L');
      const Lfallback = new Array(n);
      for (let i = 0; i < n; i++) {
        Lfallback[i] = new Float64Array(n);
        Lfallback[i][i] = 1;
      }
      return Lfallback;
    }

    return L;
  }

  const Lfallback = new Array(n);
  for (let i = 0; i < n; i++) {
    Lfallback[i] = new Float64Array(n);
    Lfallback[i][i] = 1;
  }
  return Lfallback;
}
