/** deck.gl renderer for point cloud, heatmap overlay, and grid labels. */

import {
  Deck,
  MapView,
  ScatterplotLayer,
  TextLayer,
  BitmapLayer,
} from 'deck.gl';
import { CollisionFilterExtension } from '@deck.gl/extensions';
import { mergeForTransition, buildTransitionFrames, needs3D } from './transitions.js';

// Viridis-inspired color-blind safe palette (FR-023)
// Maps knowledge value [0,1] → RGBA
const VIRIDIS = [
  [68, 1, 84],     // 0.0 — deep purple (unknown)
  [59, 82, 139],   // 0.25
  [33, 145, 140],  // 0.5 — teal
  [94, 201, 98],   // 0.75
  [253, 231, 37],  // 1.0 — yellow (mastered)
];

function valueToColor(value) {
  const t = Math.max(0, Math.min(1, value));
  const idx = t * (VIRIDIS.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, VIRIDIS.length - 1);
  const frac = idx - lo;
  return [
    Math.round(VIRIDIS[lo][0] + (VIRIDIS[hi][0] - VIRIDIS[lo][0]) * frac),
    Math.round(VIRIDIS[lo][1] + (VIRIDIS[hi][1] - VIRIDIS[lo][1]) * frac),
    Math.round(VIRIDIS[lo][2] + (VIRIDIS[hi][2] - VIRIDIS[lo][2]) * frac),
    180, // Semi-transparent overlay
  ];
}

const TRANSITION_DURATION = 600;
const CROSSFADE_DURATION = 400;
const POINT_RADIUS = 3;
const LABEL_SIZE = 12;

export class Renderer {
  constructor() {
    this._deck = null;
    this._points = [];
    this._heatmapData = [];
    this._heatmapCanvas = null;
    this._heatmapTexture = null;
    this._heatmapRegion = null;
    this._labels = [];
    this._answeredData = [];
    this._onReanswer = null;
    this._viewState = null;
    this._onViewportChange = null;
    this._onCellClick = null;
    this._transitionAbort = null;
  }

  /**
   * Initialize deck.gl with a DOM container.
   * @param {object} config - { container, onViewportChange, onCellClick }
   */
  init(config) {
    const { container, onViewportChange, onCellClick } = config;
    this._onViewportChange = onViewportChange;
    this._onCellClick = onCellClick;

    // Default view state: centered on [0.5, 0.5] with zoom to fit [0,1] space
    this._viewState = {
      longitude: 0.5,
      latitude: 0.5,
      zoom: 8,
      minZoom: 6,
      maxZoom: 14,
    };

    this._deck = new Deck({
      parent: container,
      views: new MapView({ id: 'map' }),
      initialViewState: this._viewState,
      controller: true,
      onViewStateChange: ({ viewState }) => {
        this._viewState = viewState;
        this._notifyViewport();
        return viewState;
      },
      layers: [],
    });

    // Custom tooltip element
    this._tooltip = document.createElement('div');
    this._tooltip.className = 'map-tooltip';
    this._tooltip.style.cssText = 'position:absolute;pointer-events:none;z-index:20;background:var(--color-surface-raised);color:var(--color-text);padding:6px 10px;border-radius:6px;font-size:0.75rem;font-family:var(--font-body);border:1px solid var(--color-border);box-shadow:0 2px 12px rgba(0,0,0,0.3);opacity:0;transition:opacity 0.15s ease;white-space:nowrap;max-width:300px;overflow:hidden;text-overflow:ellipsis;';
    container.style.position = 'relative';
    container.appendChild(this._tooltip);

    this._render();
  }

  /**
   * Update visible points with smooth position transitions.
   * @param {Array<object>} points - PointData[] per contracts/renderer.md
   */
  setPoints(points) {
    this._points = points || [];
    this._render();
  }

  /**
   * Update heatmap overlay from knowledge estimates.
   * @param {Array<object>} estimates - CellEstimate[]
   * @param {object} region - { x_min, x_max, y_min, y_max }
   */
  setHeatmap(estimates, region) {
    if (!estimates || estimates.length === 0) {
      this._heatmapTexture = null;
      this._heatmapRegion = null;
    } else {
      this._heatmapRegion = region;
      this._heatmapTexture = this._buildHeatmapTexture(estimates, region);
    }
    this._render();
  }

  _buildHeatmapTexture(estimates, region) {
    const gridSize = Math.round(Math.sqrt(estimates.length));
    if (gridSize === 0) return null;
    
    if (!this._heatmapCanvas) {
      this._heatmapCanvas = document.createElement('canvas');
    }
    const canvas = this._heatmapCanvas;
    canvas.width = gridSize;
    canvas.height = gridSize;
    const ctx = canvas.getContext('2d');
    const imageData = ctx.createImageData(gridSize, gridSize);
    const data = imageData.data;
    
    for (const e of estimates) {
      const idx = (e.gy * gridSize + e.gx) * 4;
      if (idx < 0 || idx + 3 >= data.length) continue;
      // Synthwave color: low=deep purple, mid=pink, high=cyan
      const v = e.value;
      let r, g, b;
      if (v < 0.5) {
        const t = v / 0.5;
        r = Math.round(60 + t * 195);   // 60 → 255
        g = Math.round(20 + t * 106);   // 20 → 126
        b = Math.round(100 + t * 119);  // 100 → 219
      } else {
        const t = (v - 0.5) / 0.5;
        r = Math.round(255 - t * 201);  // 255 → 54
        g = Math.round(126 + t * 123);  // 126 → 249
        b = Math.round(219 + t * 27);   // 219 → 246
      }
      const alpha = e.state === 'unknown' ? 0 : (e.evidenceCount === 0 ? 40 : 100);
      data[idx] = r;
      data[idx + 1] = g;
      data[idx + 2] = b;
      data[idx + 3] = alpha;
    }
    
    ctx.putImageData(imageData, 0, 0);
    return canvas;
  }

  _showTooltip(info) {
    if (!info.object || !this._tooltip) {
      this._hideTooltip();
      return;
    }
    const title = info.object.title || info.object.questionText || '';
    if (!title) { this._hideTooltip(); return; }
    this._tooltip.textContent = title;
    this._tooltip.style.left = (info.x + 12) + 'px';
    this._tooltip.style.top = (info.y - 8) + 'px';
    this._tooltip.style.opacity = '1';
  }

  _hideTooltip() {
    if (this._tooltip) this._tooltip.style.opacity = '0';
  }

  /**
   * Update grid labels.
   * @param {Array<object>} labels - GridLabel[]
   */
  setLabels(labels) {
    this._labels = labels || [];
    this._render();
  }

  /**
   * Update answered-question dot overlay.
   * @param {Array<object>} data - { x, y, questionId, title, color, isCorrect }
   */
  setAnsweredQuestions(data) {
    this._answeredData = data || [];
    this._render();
  }

  /**
   * Register callback for re-answer clicks on answered dots.
   * @param {function} handler - receives (questionId)
   */
  onReanswer(handler) {
    this._onReanswer = handler;
  }

  /**
   * Get current viewport in normalized coordinates.
   * @returns {{ x_min, x_max, y_min, y_max }}
   */
  getViewport() {
    if (!this._deck || !this._viewState) {
      return { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
    }

    // Approximate viewport from zoom + center
    const zoom = this._viewState.zoom || 8;
    const span = 1 / Math.pow(2, zoom - 8); // At zoom=8, span≈1 (full space)
    const cx = this._viewState.longitude || 0.5;
    const cy = this._viewState.latitude || 0.5;

    return {
      x_min: Math.max(0, cx - span / 2),
      x_max: Math.min(1, cx + span / 2),
      y_min: Math.max(0, cy - span / 2),
      y_max: Math.min(1, cy + span / 2),
    };
  }

  /**
   * Animate to a new region.
   * @param {object} region - { x_min, x_max, y_min, y_max }
   * @param {number} [duration=1000]
   * @returns {Promise<void>}
   */
  transitionTo(region, duration = TRANSITION_DURATION) {
    return new Promise((resolve) => {
      const cx = (region.x_min + region.x_max) / 2;
      const cy = (region.y_min + region.y_max) / 2;
      const xSpan = region.x_max - region.x_min;
      const ySpan = region.y_max - region.y_min;

      // Account for container aspect ratio
      const container = this._deck?.canvas?.parentElement;
      const aspect = container ? container.clientWidth / Math.max(container.clientHeight, 1) : 1;
      const effectiveSpan = Math.max(xSpan * 1.15, ySpan * aspect * 1.15); // 15% padding
      const zoom = Math.max(6, Math.min(14, 8 - Math.log2(effectiveSpan)));

      this._viewState = {
        ...this._viewState,
        longitude: cx,
        latitude: cy,
        zoom,
        transitionDuration: duration,
      };

      this._deck.setProps({
        initialViewState: this._viewState,
      });

      setTimeout(() => {
        this._notifyViewport();
        resolve();
      }, duration);
    });
  }

  /**
   * Abort any in-progress point transition.
   */
  abortTransition() {
    if (this._transitionAbort) {
      this._transitionAbort();
      this._transitionAbort = null;
    }
  }

  /**
   * Animate points from source set to target set with fade-in/fade-out.
   *
   * For nearby domains (IoU >= 0.3): merges point sets, fades leaving/entering
   * points, and pans the viewport simultaneously.
   *
   * For distant domains (IoU < 0.3): crossfade — fades out all source points
   * then fades in all target points, with a quick viewport jump.
   *
   * @param {Array<object>} sourcePoints - Currently displayed points
   * @param {Array<object>} targetPoints - Destination points
   * @param {{ x_min, x_max, y_min, y_max }} sourceRegion - Source domain region
   * @param {{ x_min, x_max, y_min, y_max }} targetRegion - Target domain region
   * @param {number} [duration=1000] - Transition duration in ms
   * @returns {Promise<void>} Resolves when transition completes (or is aborted)
   */
  transitionPoints(sourcePoints, targetPoints, sourceRegion, targetRegion, duration = TRANSITION_DURATION) {
    this.abortTransition();

    const useCrossfade = needs3D(sourceRegion, targetRegion);

    return new Promise((resolve) => {
      let aborted = false;
      let cleanupTimer = null;

      this._transitionAbort = () => {
        aborted = true;
        if (cleanupTimer) clearTimeout(cleanupTimer);
        resolve();
      };

      if (useCrossfade) {
        this._crossfadeTransition(sourcePoints, targetPoints, targetRegion, duration, () => aborted, resolve);
      } else {
        this._panFadeTransition(sourcePoints, targetPoints, targetRegion, duration, () => aborted, resolve);
      }
    });
  }

  _panFadeTransition(sourcePoints, targetPoints, targetRegion, duration, isAborted, resolve) {
    const { merged } = mergeForTransition(sourcePoints, targetPoints);
    const { startData, endData } = buildTransitionFrames(merged);

    // Set start state
    this._points = startData;
    this._render();

    requestAnimationFrame(() => {
      if (isAborted()) { resolve(); return; }

      // Compute viewport inline (same as transitionTo logic)
      const cx = (targetRegion.x_min + targetRegion.x_max) / 2;
      const cy = (targetRegion.y_min + targetRegion.y_max) / 2;
      const xSpan = targetRegion.x_max - targetRegion.x_min;
      const ySpan = targetRegion.y_max - targetRegion.y_min;
      const container = this._deck?.canvas?.parentElement;
      const aspect = container ? container.clientWidth / Math.max(container.clientHeight, 1) : 1;
      const effectiveSpan = Math.max(xSpan * 1.15, ySpan * aspect * 1.15);
      const zoom = Math.max(6, Math.min(14, 8 - Math.log2(effectiveSpan)));

      // Fire points + viewport TOGETHER on same frame
      this._points = endData;
      this._viewState = {
        ...this._viewState,
        longitude: cx,
        latitude: cy,
        zoom,
        transitionDuration: duration,
      };
      this._deck.setProps({
        initialViewState: this._viewState,
        layers: this._buildLayers(),
      });

      setTimeout(() => {
        if (isAborted()) { resolve(); return; }
        this._points = targetPoints;
        this._render();
        this._notifyViewport();
        this._transitionAbort = null;
        resolve();
      }, duration + 50);
    });
  }

  _crossfadeTransition(sourcePoints, targetPoints, targetRegion, duration, isAborted, resolve) {
    const half = Math.round(duration * 0.4);

    // Phase 1: fade out source points
    const fadedOut = sourcePoints.map((p) => ({
      ...p,
      color: [p.color?.[0] ?? 200, p.color?.[1] ?? 200, p.color?.[2] ?? 200, 0],
    }));
    this._points = fadedOut;
    this._render();

    setTimeout(() => {
      if (isAborted()) { resolve(); return; }

      // Compute viewport inline
      const cx = (targetRegion.x_min + targetRegion.x_max) / 2;
      const cy = (targetRegion.y_min + targetRegion.y_max) / 2;
      const xSpan = targetRegion.x_max - targetRegion.x_min;
      const ySpan = targetRegion.y_max - targetRegion.y_min;
      const container = this._deck?.canvas?.parentElement;
      const aspect = container ? container.clientWidth / Math.max(container.clientHeight, 1) : 1;
      const effectiveSpan = Math.max(xSpan * 1.15, ySpan * aspect * 1.15);
      const zoom = Math.max(6, Math.min(14, 8 - Math.log2(effectiveSpan)));

      // Set invisible target points + viewport TOGETHER
      const invisible = targetPoints.map((p) => ({
        ...p,
        color: [p.color?.[0] ?? 200, p.color?.[1] ?? 200, p.color?.[2] ?? 200, 0],
      }));
      this._points = invisible;
      this._viewState = {
        ...this._viewState,
        longitude: cx,
        latitude: cy,
        zoom,
        transitionDuration: 100,
      };
      this._deck.setProps({
        initialViewState: this._viewState,
        layers: this._buildLayers(),
      });

      requestAnimationFrame(() => {
        if (isAborted()) { resolve(); return; }

        this._points = targetPoints;
        this._render();

        setTimeout(() => {
          if (isAborted()) { resolve(); return; }
          this._notifyViewport();
          this._transitionAbort = null;
          resolve();
        }, half + 100);
      });
    }, half);
  }

  destroy() {
    this.abortTransition();
    if (this._deck) {
      this._deck.finalize();
      this._deck = null;
    }
  }

  // ---- Private ----

  _render() {
    if (!this._deck) return;
    this._deck.setProps({ layers: this._buildLayers() });
  }

  _buildLayers() {
    const layers = [];

    // Heatmap layer — knowledge estimates overlay
    if (this._heatmapTexture) {
      layers.push(new BitmapLayer({
        id: 'heatmap',
        image: this._heatmapTexture,
        bounds: [
          this._heatmapRegion.x_min, this._heatmapRegion.y_min,
          this._heatmapRegion.x_max, this._heatmapRegion.y_max,
        ],
        opacity: 0.55,
        pickable: false,
        textureParameters: {
          minFilter: 'linear',
          magFilter: 'linear',
        },
      }));
    }

    // Scatterplot layer — article/question points
    if (this._points.length > 0) {
      layers.push(
        new ScatterplotLayer({
          id: 'points',
          data: this._points,
          getPosition: (d) => [d.x, d.y],
          getFillColor: (d) => d.color || [200, 200, 200, 150],
          getRadius: (d) => d.radius || POINT_RADIUS,
          radiusUnits: 'meters',
          radiusMinPixels: 1,
          radiusMaxPixels: 6,
          opacity: 0.8,
          pickable: true,
          transitions: {
            getPosition: { duration: TRANSITION_DURATION, type: 'interpolation' },
            getFillColor: { duration: TRANSITION_DURATION },
          },
          onHover: (info) => {
            this._showTooltip(info);
            if (this._deck.parent) {
              this._deck.parent.style.cursor = info.object ? 'pointer' : '';
            }
          },
          onClick: (info) => {
            if (info.object?.url) {
              window.open(info.object.url, '_blank', 'noopener');
            }
          },
        })
      );
    }

    // Answered-question dots
    if (this._answeredData.length > 0) {
      layers.push(
        new ScatterplotLayer({
          id: 'answered-dots',
          data: this._answeredData,
          getPosition: (d) => [d.x, d.y],
          getFillColor: (d) => d.color,
          getRadius: 4,
          radiusUnits: 'meters',
          radiusMinPixels: 3,
          radiusMaxPixels: 10,
          opacity: 0.9,
          pickable: true,
          onHover: (info) => {
            this._showTooltip(info);
            if (this._deck?.parent) {
              this._deck.parent.style.cursor = info.object ? 'pointer' : '';
            }
          },
          onClick: (info) => {
            if (info.object?.questionId && this._onReanswer) {
              this._onReanswer(info.object.questionId);
            }
          },
        })
      );
    }

    // Text layer — grid cell labels
    if (this._labels.length > 0) {
      layers.push(
        new TextLayer({
          id: 'labels',
          data: this._labels,
          getPosition: (d) => [d.center_x, d.center_y],
          getText: (d) => d.label,
          getSize: 14,
          getColor: [255, 255, 255, 200],
          getTextAnchor: 'middle',
          getAlignmentBaseline: 'center',
          fontFamily: "'Space Mono', 'JetBrains Mono', monospace",
          fontWeight: 600,
          outlineWidth: 2,
          outlineColor: [0, 0, 0, 200],
          sizeUnits: 'pixels',
          sizeMaxPixels: 20,
          billboard: true,
          maxWidth: 192,
          wordBreak: 'break-word',
          extensions: [new CollisionFilterExtension()],
          collisionEnabled: true,
          collisionGroup: 'labels',
          getCollisionPriority: (d) => d.article_count || 0,
          collisionTestProps: {
            sizeScale: 4,
            sizeMaxPixels: 64,
          },
          parameters: { depthTest: false },
        })
      );
    }

    return layers;
  }

  _notifyViewport() {
    if (this._onViewportChange) {
      this._onViewportChange(this.getViewport());
    }
  }
}
