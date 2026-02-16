/** Canvas-based point cloud and heatmap rendering with smooth transitions. */

export class Renderer {
  init(config) {
    throw new Error('Not implemented: Renderer.init');
  }

  setPoints(points) {
    throw new Error('Not implemented: Renderer.setPoints');
  }

  setHeatmap(estimates, region) {
    throw new Error('Not implemented: Renderer.setHeatmap');
  }

  setLabels(labels) {
    throw new Error('Not implemented: Renderer.setLabels');
  }

  getViewport() {
    throw new Error('Not implemented: Renderer.getViewport');
  }

  transitionTo(region, duration) {
    throw new Error('Not implemented: Renderer.transitionTo');
  }

  destroy() {
    throw new Error('Not implemented: Renderer.destroy');
  }
}
