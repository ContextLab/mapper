/** Canvas 2D renderer for point cloud, heatmap overlay, and answered-question dots. */

import { mergeForTransition, buildTransitionFrames, needs3D, cubicInOut } from './transitions.js';

function valueToColor(v) {
  const val = Math.max(0, Math.min(1, v));
  let r, g, b;
  if (val < 0.5) {
    const t = val / 0.5;
    r = Math.round(157 + t * (245 - 157));
    g = Math.round(22 + t * (220 - 22));
    b = Math.round(46 + t * (105 - 46));
  } else {
    const t = (val - 0.5) / 0.5;
    r = Math.round(245 + t * (0 - 245));
    g = Math.round(220 + t * (105 - 220));
    b = Math.round(105 + t * (62 - 105));
  }
  return [r, g, b];
}

const TRANSITION_DURATION = 600;

export class Renderer {
  constructor() {
    this._container = null;
    this._canvas = null;
    this._ctx = null;
    this._dpr = 1;
    this._width = 0;   // CSS pixels
    this._height = 0;  // CSS pixels

    this._points = [];
    this._heatmapEstimates = [];
    this._heatmapRegion = null;
    this._answeredData = [];
    this._questions = [];
    this._questionMap = new Map();
    this._estimateGrid = null; // Float64Array or null, 50*50 flat grid for O(1) lookup
    this._estimateEvidence = null; // Uint8Array, evidence counts per cell
    this._labels = [];
    this._labelRegion = null;
    this._labelGridSize = 0;
    this._labelMap = new Map();
    this._colorbarEl = null;
    this._cbMouseMove = null;
    this._cbMouseUp = null;

    this._resizeObserver = null;

    this._onReanswer = null;
    this._onViewportChange = null;
    this._onCellClick = null;

    // Pan/zoom state (identity = full [0,1] view)
    this._panX = 0;
    this._panY = 0;
    this._zoom = 1;

    // Tooltip element
    this._tooltip = null;

    // Transition state
    this._transitionAbort = null;
    this._animFrame = null;

    // Interaction state
    this._hoveredPoint = null;
    this._isDragging = false;
    this._dragMoved = false;
    this._lastMouse = null;

    this._isSelecting = false;
    this._selectionStart = null;
    this._selectionEnd = null;
    this._suppressNextClick = false;

    // Bound handlers (for removal)
    this._onMouseMove = this._handleMouseMove.bind(this);
    this._onMouseDown = this._handleMouseDown.bind(this);
    this._onMouseUp = this._handleMouseUp.bind(this);
    this._onMouseLeave = this._handleMouseLeave.bind(this);
    this._onWheel = this._handleWheel.bind(this);
    this._onResize = this._handleResize.bind(this);
    this._onClick = this._handleClick.bind(this);

    // Touch handlers
    this._onTouchStart = this._handleTouchStart.bind(this);
    this._onTouchMove = this._handleTouchMove.bind(this);
    this._onTouchEnd = this._handleTouchEnd.bind(this);
    this._lastTouchDist = null;
    this._lastTouchCenter = null;
  }

  /**
   * Initialize with a DOM container.
   * @param {object} config - { container, onViewportChange, onCellClick }
   */
  init(config) {
    const { container, onViewportChange, onCellClick } = config;
    this._container = container;
    this._onViewportChange = onViewportChange;
    this._onCellClick = onCellClick;

    // Create canvas
    this._canvas = document.createElement('canvas');
    this._canvas.style.display = 'block';
    this._canvas.style.width = '100%';
    this._canvas.style.height = '100%';
    container.appendChild(this._canvas);
    this._ctx = this._canvas.getContext('2d');

    this._tooltip = document.createElement('div');
    this._tooltip.className = 'map-tooltip';
    this._tooltip.style.cssText =
      'position:absolute;pointer-events:none;z-index:20;' +
      'background:var(--color-surface);color:var(--color-text);' +
      'padding:8px 12px;border-radius:8px;font-size:0.78rem;' +
      'font-family:var(--font-body);border:1px solid var(--color-border);' +
      'box-shadow:0 4px 16px rgba(0,0,0,0.35);opacity:0;transition:opacity 0.15s ease;' +
      'white-space:normal;max-width:340px;overflow:hidden;line-height:1.5;' +
      'border-left:3px solid var(--color-border);';
    container.style.position = 'relative';
    container.appendChild(this._tooltip);

    // DOM colorbar (draggable)
    this._colorbarEl = document.createElement('div');
    this._colorbarEl.style.cssText =
      'position:absolute;bottom:16px;right:16px;z-index:15;' +
      'width:12px;height:120px;border-radius:6px;cursor:grab;' +
      'background:linear-gradient(to bottom, rgb(0,105,62), rgb(245,220,105) 50%, rgb(157,22,46));' +
      'box-shadow:0 2px 8px rgba(0,0,0,0.15);border:1px solid rgba(0,0,0,0.1);' +
      'display:none;user-select:none;';
    const topLabel = document.createElement('div');
    topLabel.style.cssText = 'position:absolute;top:-16px;left:50%;transform:translateX(-50%);font-size:9px;color:rgba(0,0,0,0.55);font-family:var(--font-body);white-space:nowrap;';
    topLabel.textContent = 'High';
    const bottomLabel = document.createElement('div');
    bottomLabel.style.cssText = 'position:absolute;bottom:-16px;left:50%;transform:translateX(-50%);font-size:9px;color:rgba(0,0,0,0.55);font-family:var(--font-body);white-space:nowrap;';
    bottomLabel.textContent = 'Low';
    const sideLabel = document.createElement('div');
    sideLabel.style.cssText = 'position:absolute;left:-58px;top:50%;transform:translateY(-50%) rotate(-90deg);font-size:9px;color:rgba(0,0,0,0.55);font-family:var(--font-body);white-space:nowrap;transform-origin:center center;';
    sideLabel.textContent = 'Estimated Knowledge';
    this._colorbarEl.appendChild(topLabel);
    this._colorbarEl.appendChild(bottomLabel);
    this._colorbarEl.appendChild(sideLabel);
    container.appendChild(this._colorbarEl);
    this._initColorbarDrag();

    // Size canvas
    this._resize();

    // ResizeObserver for flex layout changes
    this._resizeObserver = new ResizeObserver(() => {
      this._resize();
      this._render();
      this._notifyViewport();
    });
    this._resizeObserver.observe(this._container);

    // Event listeners
    this._canvas.addEventListener('mousemove', this._onMouseMove);
    this._canvas.addEventListener('mousedown', this._onMouseDown);
    this._canvas.addEventListener('mouseup', this._onMouseUp);
    this._canvas.addEventListener('mouseleave', this._onMouseLeave);
    this._canvas.addEventListener('wheel', this._onWheel, { passive: false });
    this._canvas.addEventListener('click', this._onClick);
    this._canvas.addEventListener('touchstart', this._onTouchStart, { passive: false });
    this._canvas.addEventListener('touchmove', this._onTouchMove, { passive: false });
    this._canvas.addEventListener('touchend', this._onTouchEnd);
    window.addEventListener('resize', this._onResize);

    this._render();
  }

  /**
   * Update visible points.
   * @param {Array<object>} points - PointData[]
   */
  setPoints(points) {
    this._points = points || [];
    if (this._colorbarEl) {
      this._colorbarEl.style.display = this._points.length > 0 ? 'block' : 'none';
    }
    this._render();
  }

  /**
   * Update heatmap overlay from knowledge estimates.
   * @param {Array<object>} estimates - CellEstimate[]
   * @param {object} region - { x_min, x_max, y_min, y_max }
   */
  setHeatmap(estimates, region) {
    this._heatmapEstimates = estimates || [];
    this._heatmapRegion = region || null;

    // Determine grid size from max gx/gy in estimates
    let n = 50;
    for (const e of this._heatmapEstimates) {
      if (e.gx >= n) n = e.gx + 1;
      if (e.gy >= n) n = e.gy + 1;
    }
    this._heatmapGridSize = n;
    this._estimateGrid = new Float64Array(n * n).fill(0.5);
    this._estimateEvidence = new Uint8Array(n * n);
    for (const e of this._heatmapEstimates) {
      if (e.gx >= 0 && e.gx < n && e.gy >= 0 && e.gy < n) {
        this._estimateGrid[e.gy * n + e.gx] = e.value;
        this._estimateEvidence[e.gy * n + e.gx] = e.evidenceCount || 0;
      }
    }
    this._render();
  }

  setLabels(labels, region, gridSize) {
    this._labels = labels || [];
    this._labelRegion = region || null;
    this._labelGridSize = gridSize || 0;
    // Build O(1) lookup map: "gx,gy" → label
    this._labelMap = new Map();
    for (const l of this._labels) {
      this._labelMap.set(`${l.gx},${l.gy}`, l);
    }
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

  addQuestions(questions) {
    for (const q of questions) {
      if (!this._questionMap.has(q.id)) {
        this._questionMap.set(q.id, q);
        this._questions.push(q);
      }
    }
  }

  clearQuestions() {
    this._questions = [];
    this._questionMap = new Map();
  }



  /**
   * Get current viewport in normalized [0,1] coordinates.
   * @returns {{ x_min, x_max, y_min, y_max }}
   */
  getViewport() {
    if (!this._width || !this._height) {
      return { x_min: 0, x_max: 1, y_min: 0, y_max: 1 };
    }
    // Invert the transform: screen coords [0, width] → normalized coords
    // Screen x = panX + normX * zoom * width  →  normX = (screenX - panX) / (zoom * width)
    const x_min = Math.max(0, -this._panX / (this._zoom * this._width));
    const y_min = Math.max(0, -this._panY / (this._zoom * this._height));
    const x_max = Math.min(1, (this._width - this._panX) / (this._zoom * this._width));
    const y_max = Math.min(1, (this._height - this._panY) / (this._zoom * this._height));
    return { x_min, x_max, y_min, y_max };
  }

  /**
   * Animate to a new region.
   * @param {object} region - { x_min, x_max, y_min, y_max }
   * @param {number} [duration=600]
   * @returns {Promise<void>}
   */
  jumpTo(region) {
    this.abortTransition();
    const target = this._computePanZoomForRegion(region);
    this._panX = target.panX;
    this._panY = target.panY;
    this._zoom = target.zoom;
    this._clampPanZoom();
    this._render();
    this._notifyViewport();
  }

  transitionTo(region, duration = TRANSITION_DURATION) {
    this.abortTransition();
    return new Promise((resolve) => {
      if (duration <= 0) { this.jumpTo(region); resolve(); return; }

      const target = this._computePanZoomForRegion(region);
      const startPanX = this._panX;
      const startPanY = this._panY;
      const startZoom = this._zoom;
      const startTime = performance.now();

      let aborted = false;
      this._transitionAbort = () => { aborted = true; resolve(); };

      const animate = (now) => {
        if (aborted) return;
        const elapsed = now - startTime;
        const t = Math.min(1, elapsed / duration);
        const e = cubicInOut(t);

        this._panX = startPanX + (target.panX - startPanX) * e;
        this._panY = startPanY + (target.panY - startPanY) * e;
        this._zoom = startZoom + (target.zoom - startZoom) * e;
        this._render();

        if (t < 1) {
          this._animFrame = requestAnimationFrame(animate);
        } else {
          this._panX = target.panX;
          this._panY = target.panY;
          this._zoom = target.zoom;
          this._clampPanZoom();
          this._render();
          this._notifyViewport();
          this._transitionAbort = null;
          resolve();
        }
      };

      this._animFrame = requestAnimationFrame(animate);
    });
  }

  /**
   * Abort any in-progress transition.
   */
  abortTransition() {
    if (this._transitionAbort) {
      this._transitionAbort();
      this._transitionAbort = null;
    }
    if (this._animFrame) {
      cancelAnimationFrame(this._animFrame);
      this._animFrame = null;
    }
  }

  /**
   * Animate points from source set to target set.
   * For nearby domains (IoU >= 0.3): merge + pan-fade.
   * For distant domains (IoU < 0.3): crossfade.
   */
  transitionPoints(sourcePoints, targetPoints, sourceRegion, targetRegion, duration = TRANSITION_DURATION) {
    this.abortTransition();
    const useCrossfade = needs3D(sourceRegion, targetRegion);

    return new Promise((resolve) => {
      let aborted = false;
      this._transitionAbort = () => { aborted = true; resolve(); };

      if (useCrossfade) {
        this._crossfadeTransition(sourcePoints, targetPoints, sourceRegion, targetRegion, duration, () => aborted, resolve);
      } else {
        this._panFadeTransition(sourcePoints, targetPoints, targetRegion, duration, () => aborted, resolve);
      }
    });
  }

  destroy() {
    this.abortTransition();
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    if (this._colorbarEl) {
      this._colorbarEl.remove();
      this._colorbarEl = null;
    }
    if (this._cbMouseMove) window.removeEventListener('mousemove', this._cbMouseMove);
    if (this._cbMouseUp) window.removeEventListener('mouseup', this._cbMouseUp);
    if (this._canvas) {
      this._canvas.removeEventListener('mousemove', this._onMouseMove);
      this._canvas.removeEventListener('mousedown', this._onMouseDown);
      this._canvas.removeEventListener('mouseup', this._onMouseUp);
      this._canvas.removeEventListener('mouseleave', this._onMouseLeave);
      this._canvas.removeEventListener('wheel', this._onWheel);
      this._canvas.removeEventListener('click', this._onClick);
      this._canvas.removeEventListener('touchstart', this._onTouchStart);
      this._canvas.removeEventListener('touchmove', this._onTouchMove);
      this._canvas.removeEventListener('touchend', this._onTouchEnd);
      this._canvas.remove();
      this._canvas = null;
    }
    if (this._tooltip) {
      this._tooltip.remove();
      this._tooltip = null;
    }
    window.removeEventListener('resize', this._onResize);
    this._ctx = null;
    this._container = null;
  }

  // ======== PRIVATE: Rendering ========

  _resize() {
    if (!this._container || !this._canvas) return;
    const rect = this._container.getBoundingClientRect();
    this._dpr = window.devicePixelRatio || 1;
    this._width = rect.width;
    this._height = rect.height;
    this._canvas.width = rect.width * this._dpr;
    this._canvas.height = rect.height * this._dpr;
  }

  _render() {
    if (!this._ctx || !this._width || !this._height) return;

    const ctx = this._ctx;
    const dpr = this._dpr;
    const w = this._width;
    const h = this._height;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, w, h);

    this._drawHeatmap(ctx, w, h);

    ctx.save();
    ctx.translate(this._panX, this._panY);
    ctx.scale(this._zoom, this._zoom);

    this._drawPoints(ctx, w, h);
    this._drawAnsweredDots(ctx, w, h);

    ctx.restore();

    if (this._isSelecting && this._selectionStart && this._selectionEnd) {
      ctx.save();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const sx = Math.min(this._selectionStart.x, this._selectionEnd.x);
      const sy = Math.min(this._selectionStart.y, this._selectionEnd.y);
      const sw = Math.abs(this._selectionEnd.x - this._selectionStart.x);
      const sh = Math.abs(this._selectionEnd.y - this._selectionStart.y);
      ctx.fillStyle = 'rgba(0, 105, 62, 0.1)';
      ctx.fillRect(sx, sy, sw, sh);
      ctx.strokeStyle = '#00693e';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(sx, sy, sw, sh);
      ctx.setLineDash([]);
      ctx.restore();
    }
  }

  _drawHeatmap(ctx, w, h) {
    if (!this._estimateGrid || this._heatmapEstimates.length === 0) return;

    const N = this._heatmapGridSize || 50;
    const grid = this._estimateGrid;
    const evidence = this._estimateEvidence;
    const region = this._heatmapRegion;
    if (!region) return;

    // The heatmap grid covers the domain region in world space.
    // We draw fixed-size screen cells and look up which grid cell each maps to.
    // Screen pixel (sx, sy) → world coord → grid cell (gx, gy).
    //
    // World coords: point.x * w = panX + normX * zoom * w
    //   normX = (screenX - panX) / (zoom * w)
    const SCREEN_CELLS = 50; // fixed number of screen cells
    const cellW = w / SCREEN_CELLS;
    const cellH = h / SCREEN_CELLS;

    const rXMin = region.x_min;
    const rYMin = region.y_min;
    const rXSpan = region.x_max - region.x_min;
    const rYSpan = region.y_max - region.y_min;

    ctx.globalAlpha = 0.45;

    for (let sy = 0; sy < SCREEN_CELLS; sy++) {
      for (let sx = 0; sx < SCREEN_CELLS; sx++) {
        // Center of this screen cell → world normalized coordinate
        const centerSX = (sx + 0.5) * cellW;
        const centerSY = (sy + 0.5) * cellH;
        const wx = (centerSX - this._panX) / (this._zoom * w);
        const wy = (centerSY - this._panY) / (this._zoom * h);

        // Map world coord to grid cell within domain region
        const gx = Math.floor(((wx - rXMin) / rXSpan) * N);
        const gy = Math.floor(((wy - rYMin) / rYSpan) * N);

        if (gx < 0 || gx >= N || gy < 0 || gy >= N) {
          // Outside domain region — draw neutral prior
          ctx.fillStyle = 'rgba(245, 220, 105, 0.25)';
          ctx.fillRect(sx * cellW, sy * cellH, cellW + 0.5, cellH + 0.5);
          continue;
        }

        const idx = gy * N + gx;
        const val = grid[idx];
        const ev = evidence[idx];
        const [r, g, b] = valueToColor(val);
        const a = ev === 0 ? 0.5 : 0.75;
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${a})`;
        ctx.fillRect(sx * cellW, sy * cellH, cellW + 0.5, cellH + 0.5);
      }
    }

    ctx.globalAlpha = 1;
    // Only draw grid lines if cells are large enough to be visible
    if (cellW > 4 && cellH > 4) {
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.06)';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      for (let i = 0; i <= SCREEN_CELLS; i++) {
        const x = i * cellW;
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        const y = i * cellH;
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
      }
      ctx.stroke();
    }

    ctx.globalAlpha = 1;
  }

  _drawPoints(ctx, w, h) {
    if (this._points.length === 0) return;

    const defaultColor = [100, 116, 139, 80];
    for (const p of this._points) {
      const px = p.x * w;
      const py = p.y * h;
      const r = (p.radius || 2) / this._zoom;
      const color = p.color || defaultColor;
      const alpha = (color[3] ?? 100) / 255;

      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha})`;
      ctx.fill();
    }
  }


  _drawAnsweredDots(ctx, w, h) {
    if (this._answeredData.length === 0) return;

    for (const d of this._answeredData) {
      const px = d.x * w;
      const py = d.y * h;
      const r = 5 / this._zoom;

      ctx.beginPath();
      ctx.arc(px, py, r + 1.5 / this._zoom, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
      ctx.fill();

      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      const c = d.color || [200, 200, 200, 200];
      ctx.fillStyle = `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${(c[3] ?? 200) / 255})`;
      ctx.fill();
    }
  }

  _initColorbarDrag() {
    let dragging = false;
    let offsetX = 0;
    let offsetY = 0;

    this._colorbarEl.addEventListener('mousedown', (e) => {
      dragging = true;
      offsetX = e.clientX - this._colorbarEl.offsetLeft;
      offsetY = e.clientY - this._colorbarEl.offsetTop;
      this._colorbarEl.style.cursor = 'grabbing';
      e.stopPropagation();
    });

    this._cbMouseMove = (e) => {
      if (!dragging) return;
      const rect = this._container.getBoundingClientRect();
      const x = e.clientX - offsetX;
      const y = e.clientY - offsetY;
      this._colorbarEl.style.left = Math.max(0, Math.min(rect.width - 30, x)) + 'px';
      this._colorbarEl.style.top = Math.max(0, Math.min(rect.height - 150, y)) + 'px';
      this._colorbarEl.style.right = 'auto';
      this._colorbarEl.style.bottom = 'auto';
    };

    this._cbMouseUp = () => {
      if (dragging) {
        dragging = false;
        this._colorbarEl.style.cursor = 'grab';
      }
    };

    window.addEventListener('mousemove', this._cbMouseMove);
    window.addEventListener('mouseup', this._cbMouseUp);
  }

  // ======== Pan/Zoom ========

  _computePanZoomForRegion(region) {
    const w = this._width;
    const h = this._height;
    const rw = region.x_max - region.x_min;
    const rh = region.y_max - region.y_min;

    // 30% padding gives context around the domain
    const padding = 1.3;
    const zoomX = 1 / (rw * padding);
    const zoomY = 1 / (rh * padding);
    const zoom = Math.max(1, Math.min(10, Math.min(zoomX, zoomY)));

    const cx = (region.x_min + region.x_max) / 2;
    const cy = (region.y_min + region.y_max) / 2;
    let panX = w / 2 - cx * zoom * w;
    let panY = h / 2 - cy * zoom * h;

    // Clamp so content always fills screen
    const contentW = zoom * w;
    const contentH = zoom * h;
    panX = Math.max(w - contentW, Math.min(0, panX));
    panY = Math.max(h - contentH, Math.min(0, panY));

    return { panX, panY, zoom };
  }

  _clampPanZoom() {
    this._zoom = Math.max(1, Math.min(10, this._zoom));

    // Prevent panning beyond the [0,1] content
    const w = this._width;
    const h = this._height;
    const contentW = this._zoom * w;
    const contentH = this._zoom * h;

    // panX: left edge can't go right of 0, right edge can't go left of w
    this._panX = Math.max(w - contentW, Math.min(0, this._panX));
    this._panY = Math.max(h - contentH, Math.min(0, this._panY));
  }

  // ======== PRIVATE: Event handlers ========

  _handleResize() {
    this._resize();
    this._render();
  }

  _handleWheel(e) {
    e.preventDefault();

    const rect = this._canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left; // Mouse position in CSS pixels
    const my = e.clientY - rect.top;

    const zoomFactor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    const newZoom = Math.max(1, Math.min(10, this._zoom * zoomFactor));

    if (newZoom === this._zoom) return;

    // Zoom centered on cursor
    const scale = newZoom / this._zoom;
    this._panX = mx - scale * (mx - this._panX);
    this._panY = my - scale * (my - this._panY);
    this._zoom = newZoom;

    this._clampPanZoom();
    this._render();
    this._notifyViewport();
  }

  _handleMouseDown(e) {
    if (e.button !== 0) return;

    if (e.shiftKey) {
      const rect = this._canvas.getBoundingClientRect();
      this._isSelecting = true;
      this._selectionStart = { x: e.clientX - rect.left, y: e.clientY - rect.top };
      this._selectionEnd = { ...this._selectionStart };
      this._canvas.style.cursor = 'crosshair';
      e.preventDefault();
      return;
    }

    this._isDragging = true;
    this._dragMoved = false;
    this._lastMouse = { x: e.clientX, y: e.clientY };
    this._canvas.style.cursor = 'grabbing';
  }

  _handleMouseUp() {
    if (this._isSelecting && this._selectionStart && this._selectionEnd) {
      const s = this._selectionStart;
      const en = this._selectionEnd;
      const dx = Math.abs(en.x - s.x);
      const dy = Math.abs(en.y - s.y);

      if (dx > 10 && dy > 10) {
        const x1 = (Math.min(s.x, en.x) - this._panX) / (this._zoom * this._width);
        const y1 = (Math.min(s.y, en.y) - this._panY) / (this._zoom * this._height);
        const x2 = (Math.max(s.x, en.x) - this._panX) / (this._zoom * this._width);
        const y2 = (Math.max(s.y, en.y) - this._panY) / (this._zoom * this._height);
        this.transitionTo({
          x_min: Math.max(0, x1), x_max: Math.min(1, x2),
          y_min: Math.max(0, y1), y_max: Math.min(1, y2),
        });
      }

      this._isSelecting = false;
      this._selectionStart = null;
      this._selectionEnd = null;
      this._suppressNextClick = true;
      this._canvas.style.cursor = '';
      this._render();
      return;
    }

    this._isDragging = false;
    this._lastMouse = null;
    this._canvas.style.cursor = this._hoveredPoint ? 'pointer' : '';
  }

  _handleMouseLeave() {
    this._isDragging = false;
    this._lastMouse = null;
    this._hideTooltip();
    this._canvas.style.cursor = '';
  }

  _handleMouseMove(e) {
    const rect = this._canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    if (this._isSelecting && this._selectionStart) {
      this._selectionEnd = { x: mx, y: my };
      this._render();
      return;
    }

    if (this._isDragging && this._lastMouse) {
      const dx = e.clientX - this._lastMouse.x;
      const dy = e.clientY - this._lastMouse.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) this._dragMoved = true;
      this._panX += dx;
      this._panY += dy;
      this._lastMouse = { x: e.clientX, y: e.clientY };

      this._clampPanZoom();
      this._render();
      this._notifyViewport();
      return;
    }

    const hit = this._hitTest(mx, my);
    if (hit) {
      this._hoveredPoint = hit;
      this._canvas.style.cursor = 'pointer';
      this._showTooltip(this._buildTooltipHTML(hit), e.clientX - rect.left, e.clientY - rect.top);
    } else {
      this._hoveredPoint = null;
      this._canvas.style.cursor = '';
      this._hideTooltip();
    }
  }

  _handleClick(e) {
    // Don't treat shift+drag selection release as a click
    if (this._suppressNextClick) {
      this._suppressNextClick = false;
      return;
    }
    // Don't treat drag-release as a click
    if (this._dragMoved) {
      this._dragMoved = false;
      return;
    }

    const rect = this._canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const hit = this._hitTest(mx, my);

    if (!hit) return;

    if (hit.questionId) return;

    if (hit.url) {
      this._openInBackground(hit.url);
      return;
    }

    if (hit.type === 'cell' && hit.label && hit.label.source_article) {
      const url = 'https://en.wikipedia.org/wiki/' + encodeURIComponent(hit.label.source_article);
      this._openInBackground(url);
    }
  }

  _openInBackground(url) {
    const w = window.open(url, '_blank', 'noopener');
    if (w) {
      w.blur();
      window.focus();
    }
  }

  _hitTest(mx, my) {
    // Convert screen coords to normalized [0,1] coords
    const normX = (mx - this._panX) / (this._zoom * this._width);
    const normY = (my - this._panY) / (this._zoom * this._height);
    const hitRadius = 8 / (this._zoom * this._width); // 8px hit area

    // Check answered dots first (on top)
    for (const d of this._answeredData) {
      const dx = d.x - normX;
      const dy = d.y - normY;
      if (Math.sqrt(dx * dx + dy * dy) < hitRadius * 1.5) {
        return { ...d, title: d.title };
      }
    }

    for (const p of this._points) {
      const dx = p.x - normX;
      const dy = p.y - normY;
      if (Math.sqrt(dx * dx + dy * dy) < hitRadius) {
        return p;
      }
    }

    {
      const N = 50;
      const cellW = this._width / N;
      const cellH = this._height / N;
      const sgx = Math.floor(mx / cellW);
      const sgy = Math.floor(my / cellH);

      if (sgx >= 0 && sgx < N && sgy >= 0 && sgy < N) {
        const centerSX = (sgx + 0.5) * cellW;
        const centerSY = (sgy + 0.5) * cellH;
        const wx = (centerSX - this._panX) / (this._zoom * this._width);
        const wy = (centerSY - this._panY) / (this._zoom * this._height);

        let estimateValue = 0.5;
        if (this._estimateGrid && wx >= 0 && wx < 1 && wy >= 0 && wy < 1) {
          const egx = Math.min(N - 1, Math.floor(wx * N));
          const egy = Math.min(N - 1, Math.floor(wy * N));
          estimateValue = this._estimateGrid[egy * N + egx];
        }

        // Look up pre-computed bundle label for this world coordinate
        let bundleLabel = null;
        if (this._labelMap && this._labelMap.size > 0 && this._labelRegion) {
          const r = this._labelRegion;
          const gs = this._labelGridSize || Math.round(Math.sqrt(this._labels.length));
          if (wx >= r.x_min && wx <= r.x_max && wy >= r.y_min && wy <= r.y_max) {
            const lgx = Math.min(gs - 1, Math.floor((wx - r.x_min) / (r.x_max - r.x_min) * gs));
            const lgy = Math.min(gs - 1, Math.floor((wy - r.y_min) / (r.y_max - r.y_min) * gs));
            bundleLabel = this._labelMap.get(`${lgx},${lgy}`) || null;
          }
        }

        // Also find nearest question for concepts/source info
        let nearestQ = null;
        let nearestDist = Infinity;
        for (const q of this._questions) {
          const dx = q.x - wx;
          const dy = q.y - wy;
          const d2 = dx * dx + dy * dy;
          if (d2 < nearestDist) {
            nearestDist = d2;
            nearestQ = q;
          }
        }

        const label = {
          // Use bundle label title when available, fall back to question source_article
          title: (bundleLabel && bundleLabel.label) || null,
          article_count: bundleLabel ? bundleLabel.article_count : 0,
          concepts: nearestQ
            ? (nearestQ.concepts_tested || [])
                .map(c => c.replace(/^Concept\s+\d+:\s*/i, '').trim()).filter(Boolean)
            : [],
          source_article: nearestQ ? nearestQ.source_article || null : null,
        };

        return {
          type: 'cell',
          gx: sgx,
          gy: sgy,
          label,
          estimateValue,
        };
      }
    }

    return null;
  }

  // Touch handling for pinch-zoom
  _handleTouchStart(e) {
    if (e.touches.length === 2) {
      e.preventDefault();
      const t0 = e.touches[0];
      const t1 = e.touches[1];
      this._lastTouchDist = Math.hypot(t1.clientX - t0.clientX, t1.clientY - t0.clientY);
      this._lastTouchCenter = {
        x: (t0.clientX + t1.clientX) / 2,
        y: (t0.clientY + t1.clientY) / 2,
      };
    } else if (e.touches.length === 1) {
      this._isDragging = true;
      this._dragMoved = false;
      this._lastMouse = { x: e.touches[0].clientX, y: e.touches[0].clientY };
    }
  }

  _handleTouchMove(e) {
    if (e.touches.length === 2 && this._lastTouchDist != null) {
      e.preventDefault();
      const t0 = e.touches[0];
      const t1 = e.touches[1];
      const dist = Math.hypot(t1.clientX - t0.clientX, t1.clientY - t0.clientY);
      const center = {
        x: (t0.clientX + t1.clientX) / 2,
        y: (t0.clientY + t1.clientY) / 2,
      };

      const rect = this._canvas.getBoundingClientRect();
      const mx = center.x - rect.left;
      const my = center.y - rect.top;

      const scale = dist / this._lastTouchDist;
      const newZoom = Math.max(1, Math.min(10, this._zoom * scale));

      if (newZoom !== this._zoom) {
        const s = newZoom / this._zoom;
        this._panX = mx - s * (mx - this._panX);
        this._panY = my - s * (my - this._panY);
        this._zoom = newZoom;
        this._clampPanZoom();
        this._render();
        this._notifyViewport();
      }

      this._lastTouchDist = dist;
      this._lastTouchCenter = center;
    } else if (e.touches.length === 1 && this._isDragging && this._lastMouse) {
      const t = e.touches[0];
      const dx = t.clientX - this._lastMouse.x;
      const dy = t.clientY - this._lastMouse.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) this._dragMoved = true;
      this._panX += dx;
      this._panY += dy;
      this._lastMouse = { x: t.clientX, y: t.clientY };
      this._clampPanZoom();
      this._render();
      this._notifyViewport();
    }
  }

  _handleTouchEnd() {
    this._isDragging = false;
    this._lastMouse = null;
    this._lastTouchDist = null;
    this._lastTouchCenter = null;
  }

  // ======== PRIVATE: Tooltip ========

  _buildTooltipHTML(hit) {
    if (hit.questionId) {
      const q = this._questionMap.get(hit.questionId);
      const isCorrect = hit.isCorrect;
      const borderColor = isCorrect ? '#00693e' : '#9d162e';
      const icon = isCorrect
        ? '<i class="fa-solid fa-check" style="font-size:0.85em;"></i>'
        : '<i class="fa-solid fa-xmark" style="font-size:0.85em;"></i>';
      const text = hit.title || 'Question';
      const truncated = text.length > 160 ? text.slice(0, 160) + '…' : text;

      let html = `<div style="font-weight:600;margin-bottom:4px;"><span style="color:${borderColor}">${icon}</span> ${this._escapeHtml(truncated)}</div>`;
      if (q) {
        if (q.source_article) {
          const wikiUrl = 'https://en.wikipedia.org/wiki/' + encodeURIComponent(q.source_article);
          html += `<div style="font-size:0.73rem;margin-top:4px;"><b>Source:</b> <a href="${wikiUrl}" target="_blank" rel="noopener" style="color:#00693e;text-decoration:underline;">${this._escapeHtml(q.source_article)}</a></div>`;
        }
        if (q.concepts_tested && q.concepts_tested.length > 0) {
          const concepts = q.concepts_tested.map(c => c.replace(/^Concept\s+\d+:\s*/i, '').trim()).filter(Boolean);
          html += `<div style="font-size:0.73rem;color:var(--color-text-muted);margin-top:2px;"><b>Concepts:</b> ${this._escapeHtml(concepts.join(', '))}</div>`;
        }
      }
      return { html, borderColor, interactive: !!q?.source_article };
    }

    if (hit.type === 'cell') {
      const label = hit.label;
      const level = this._knowledgeLevelLabel(hit.estimateValue);
      const [cr, cg, cb] = valueToColor(hit.estimateValue);
      const borderColor = `rgb(${cr},${cg},${cb})`;

      let html = '';
      // Show the grid cell's article title (from bundle labels)
      if (label && label.title) {
        html += `<div style="font-weight:600;margin-bottom:2px;">${this._escapeHtml(label.title)}</div>`;
      }
      if (label && label.concepts && label.concepts.length > 0) {
        html += `<div style="font-size:0.73rem;color:var(--color-text-muted);margin-bottom:2px;">${this._escapeHtml(label.concepts.join(', '))}</div>`;
      }
      if (label && label.source_article) {
        html += `<div style="font-size:0.73rem;margin-top:2px;">Click to open <a href="https://en.wikipedia.org/wiki/${encodeURIComponent(label.source_article)}" style="color:#00693e;text-decoration:underline;pointer-events:auto;">${this._escapeHtml(label.source_article)}</a></div>`;
      }
      html += `<div style="font-size:0.68rem;margin-top:3px;color:var(--color-text-muted);opacity:0.7;">Estimated knowledge: ${level}</div>`;
      return { html, borderColor, interactive: !!(label && label.source_article) };
    }

    const title = hit.title || '';
    const excerpt = hit.excerpt || '';
    if (excerpt) {
      const truncExcerpt = excerpt.length > 150 ? excerpt.slice(0, 150) + '…' : excerpt;
      return { html: `<div style="font-weight:600;margin-bottom:2px;">${this._escapeHtml(title)}</div><div style="font-size:0.73rem;color:var(--color-text-muted);">${this._escapeHtml(truncExcerpt)}</div>`, borderColor: '#00693e' };
    }

    return { html: `<div style="font-weight:600;">${this._escapeHtml(title)}</div>`, borderColor: 'var(--color-border)' };
  }

  _knowledgeLevelLabel(value) {
    if (value < 0.15) return 'Low';
    if (value < 0.30) return 'Medium-Low';
    if (value < 0.70) return 'Medium';
    if (value < 0.85) return 'Medium-High';
    return 'High';
  }

  _escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  _showTooltip(tooltipData, x, y) {
    if (!tooltipData || !this._tooltip) return;
    this._tooltip.innerHTML = tooltipData.html;
    this._tooltip.style.borderLeftColor = tooltipData.borderColor;
    this._tooltip.style.pointerEvents = tooltipData.interactive ? 'auto' : 'none';

    const containerW = this._width;
    const containerH = this._height;
    let left = x + 14;
    let top = y - 8;

    if (left + 340 > containerW) left = x - 350;
    if (top + 100 > containerH) top = containerH - 110;
    if (left < 0) left = 4;
    if (top < 0) top = 4;

    this._tooltip.style.left = left + 'px';
    this._tooltip.style.top = top + 'px';
    this._tooltip.style.opacity = '1';
  }

  _hideTooltip() {
    if (this._tooltip) {
      this._tooltip.style.opacity = '0';
      this._tooltip.style.pointerEvents = 'none';
    }
  }

  // ======== PRIVATE: Transitions ========

  _panFadeTransition(sourcePoints, targetPoints, targetRegion, duration, isAborted, resolve) {
    const { merged } = mergeForTransition(sourcePoints, targetPoints);
    const { startData, endData } = buildTransitionFrames(merged);

    const targetPanZoom = this._computePanZoomForRegion(targetRegion);
    const startPanX = this._panX;
    const startPanY = this._panY;
    const startZoom = this._zoom;
    const startTime = performance.now();

    // Set initial points
    this._points = startData;
    this._render();

    const animate = (now) => {
      if (isAborted()) return;

      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      const e = cubicInOut(t);

      // Interpolate points
      const interpolated = startData.map((sp, i) => {
        const ep = endData[i];
        const color = sp.color || [200, 200, 200, 100];
        const endColor = ep.color || [200, 200, 200, 100];
        return {
          ...ep,
          x: sp.x + (ep.x - sp.x) * e,
          y: sp.y + (ep.y - sp.y) * e,
          color: [
            Math.round(color[0] + (endColor[0] - color[0]) * e),
            Math.round(color[1] + (endColor[1] - color[1]) * e),
            Math.round(color[2] + (endColor[2] - color[2]) * e),
            Math.round(color[3] + (endColor[3] - color[3]) * e),
          ],
        };
      });

      // Interpolate viewport
      this._panX = startPanX + (targetPanZoom.panX - startPanX) * e;
      this._panY = startPanY + (targetPanZoom.panY - startPanY) * e;
      this._zoom = startZoom + (targetPanZoom.zoom - startZoom) * e;

      this._points = interpolated;
      this._render();

      if (t < 1) {
        this._animFrame = requestAnimationFrame(animate);
      } else {
        this._points = targetPoints;
        this._panX = targetPanZoom.panX;
        this._panY = targetPanZoom.panY;
        this._zoom = targetPanZoom.zoom;
        this._clampPanZoom();
        this._render();
        this._notifyViewport();
        this._transitionAbort = null;
        resolve();
      }
    };

    this._animFrame = requestAnimationFrame(animate);
  }

  // Smooth crossfade: viewport pans throughout, points fade at midpoint
  _crossfadeTransition(sourcePoints, targetPoints, _sourceRegion, targetRegion, duration, isAborted, resolve) {
    const startTime = performance.now();
    const targetPanZoom = this._computePanZoomForRegion(targetRegion);
    const startPanX = this._panX;
    const startPanY = this._panY;
    const startZoom = this._zoom;

    const animate = (now) => {
      if (isAborted()) return;
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      const e = cubicInOut(t);

      this._panX = startPanX + (targetPanZoom.panX - startPanX) * e;
      this._panY = startPanY + (targetPanZoom.panY - startPanY) * e;
      this._zoom = startZoom + (targetPanZoom.zoom - startZoom) * e;

      if (t < 0.5) {
        const fadeOut = 1 - (t / 0.5);
        this._points = sourcePoints.map((p) => ({
          ...p,
          color: [p.color?.[0] ?? 200, p.color?.[1] ?? 200, p.color?.[2] ?? 200,
            Math.round((p.color?.[3] ?? 150) * fadeOut)],
        }));
      } else {
        const fadeIn = (t - 0.5) / 0.5;
        this._points = targetPoints.map((p) => ({
          ...p,
          color: [p.color?.[0] ?? 200, p.color?.[1] ?? 200, p.color?.[2] ?? 200,
            Math.round((p.color?.[3] ?? 150) * fadeIn)],
        }));
      }

      this._render();

      if (t < 1) {
        this._animFrame = requestAnimationFrame(animate);
      } else {
        this._points = targetPoints;
        this._panX = targetPanZoom.panX;
        this._panY = targetPanZoom.panY;
        this._zoom = targetPanZoom.zoom;
        this._clampPanZoom();
        this._render();
        this._notifyViewport();
        this._transitionAbort = null;
        resolve();
      }
    };

    this._animFrame = requestAnimationFrame(animate);
  }

  _notifyViewport() {
    if (this._onViewportChange) {
      this._onViewportChange(this.getViewport());
    }
  }
}
