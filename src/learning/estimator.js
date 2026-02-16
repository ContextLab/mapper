/** RBF-based spatial learning estimate model with Matérn-3/2 kernel. */

export class Estimator {
  init(gridSize, region) {
    throw new Error('Not implemented: Estimator.init');
  }

  observe(x, y, correct) {
    throw new Error('Not implemented: Estimator.observe');
  }

  predict(viewport) {
    throw new Error('Not implemented: Estimator.predict');
  }

  predictCell(gx, gy) {
    throw new Error('Not implemented: Estimator.predictCell');
  }

  reset() {
    throw new Error('Not implemented: Estimator.reset');
  }

  restore(responses) {
    throw new Error('Not implemented: Estimator.restore');
  }
}
