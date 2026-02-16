/** deck.gl renderer for point cloud, heatmap overlay, and grid labels. */

import {
  Deck,
  MapView,
  ScatterplotLayer,
  TextLayer,
} from 'deck.gl';
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

const TRANSITION_DURATION = 1000;
const CROSSFADE_DURATION = 600;
const POINT_RADIUS = 3;
const LABEL_SIZE = 12;

export class Renderer {
  constructor() {
    this._deck = null;
    this._points = [];
    this._heatmapData = [];
    this._labels = [];
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
      getTooltip: ({ object }) => object?.title || null,
    });

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
    if (!estimates || !region) {
      this._heatmapData = [];
      this._render();
      return;
    }

    const xSpan = region.x_max - region.x_min;
    const ySpan = region.y_max - region.y_min;

    this._heatmapData = estimates
      .filter((e) => e.state !== 'unknown')
      .map((e) => {
        const gridSize = Math.round(Math.sqrt(estimates.length));
        const cx = region.x_min + ((e.gx + 0.5) / gridSize) * xSpan;
        const cy = region.y_min + ((e.gy + 0.5) / gridSize) * ySpan;
        const color = valueToColor(e.value);
        // Cross-domain predictions (no direct evidence) get reduced opacity
        const isCrossDomain = e.evidenceCount === 0;
        if (isCrossDomain) {
          color[3] = Math.round(color[3] * 0.45);
        }
        return {
          position: [cx, cy],
          weight: e.value,
          color,
          gx: e.gx,
          gy: e.gy,
          isCrossDomain,
        };
      });

    this._render();
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
      const span = Math.max(region.x_max - region.x_min, region.y_max - region.y_min);
      const zoom = Math.max(6, Math.min(14, 8 - Math.log2(span)));

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

    this._points = startData;
    this._render();

    requestAnimationFrame(() => {
      if (isAborted()) { resolve(); return; }

      this._points = endData;
      this._render();
      this.transitionTo(targetRegion, duration);

      setTimeout(() => {
        if (isAborted()) { resolve(); return; }
        this._points = targetPoints;
        this._render();
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

      // Phase 2: jump viewport, set target points invisible, then fade in
      const invisible = targetPoints.map((p) => ({
        ...p,
        color: [p.color?.[0] ?? 200, p.color?.[1] ?? 200, p.color?.[2] ?? 200, 0],
      }));
      this._points = invisible;
      this._render();

      // Jump viewport to target region (fast)
      this.transitionTo(targetRegion, 100);

      requestAnimationFrame(() => {
        if (isAborted()) { resolve(); return; }

        this._points = targetPoints;
        this._render();

        setTimeout(() => {
          if (isAborted()) { resolve(); return; }
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

    const layers = [];

    // Heatmap layer — knowledge estimates overlay
    if (this._heatmapData.length > 0) {
      layers.push(
        new ScatterplotLayer({
          id: 'heatmap',
          data: this._heatmapData,
          getPosition: (d) => d.position,
          getFillColor: (d) => d.color,
          getRadius: 800,
          radiusUnits: 'meters',
          opacity: 0.6,
          pickable: true,
          onClick: (info) => {
            if (info.object && this._onCellClick) {
              this._onCellClick(info.object.gx, info.object.gy);
            }
          },
          updateTriggers: {
            getFillColor: this._heatmapData,
          },
        })
      );
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
          getTooltip: ({ object }) => object?.title,
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
          getSize: LABEL_SIZE,
          getColor: [255, 255, 255, 200],
          getTextAnchor: 'middle',
          getAlignmentBaseline: 'center',
          fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
          fontWeight: 600,
          outlineWidth: 2,
          outlineColor: [0, 0, 0, 180],
          sizeUnits: 'meters',
          sizeMinPixels: 8,
          sizeMaxPixels: 16,
          billboard: true,
        })
      );
    }

    this._deck.setProps({ layers });
  }

  _notifyViewport() {
    if (this._onViewportChange) {
      this._onViewportChange(this.getViewport());
    }
  }
}
